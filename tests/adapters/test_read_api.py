"""HTTP read API. Fakes stand in for Postgres; no Docker and no network."""

import asyncio
from dataclasses import replace
from datetime import UTC, datetime
from typing import Any

import httpx
from fastapi import FastAPI

from eleicoes.adapters.html_poder_lido import cells_from_power_html
from eleicoes.adapters.http.bundle import ReadPorts
from eleicoes.composition.api import create_app
from eleicoes.domain.boletim_consulta import (
    BrancosNulos,
    Comparativo,
    LinhaVoto,
    Participacao,
    PoderPartido,
    PrimeiroColocado,
    TotalCargo,
    VotosMunicipio,
    VotosZona,
)
from eleicoes.domain.errors import ElectionError
from eleicoes.domain.presidente_governador import CargoTally, MunicipalPlace, PartyTally
from eleicoes.domain.stored_grade import StoredCell
from eleicoes.ports.cadeiras import (
    CadeirasUnidade,
    EstimativaCadeiras,
    Federacao,
    TotaisCadeiras,
)
from eleicoes.ports.municipal_2024 import Municipal2024, MunicipalPartido2024, TotaisMunicipal2024
from eleicoes.ports.relatorio_poder import StoredReport
from eleicoes.ports.relatorio_presidente_governador import StoredCrossReport

_SCOPE = "ano=2026&turno=1&uf=SE&cargo=presidente"


def test_health_and_openapi_advertise_the_read_routes() -> None:
    application = create_app(ports=_ports())
    health = _get(application, "/health")
    assert health.status_code == 200
    assert health.json() == {"status": "ok"}
    spec = _get(application, "/openapi.json").json()
    paths = spec["paths"]
    expected = {
        "/health",
        "/votos/cargos",
        "/votos/municipios",
        "/votos/comparar",
        "/votos/poder",
        "/votos/participacao",
        "/votos/brancos-nulos",
        "/votos/lideres",
        "/votos/secoes",
        "/votos/zonas",
        "/votos/indicios",
        "/relatorios/dados/grade",
        "/relatorios/dados/perfis",
        "/relatorios/dados/classe-governador",
        "/relatorios/dados/presidente-governador",
        "/relatorios/poder",
        "/relatorios/presidente-governador",
        "/relatorios/dados/cadeiras",
        "/relatorios/dados/forca",
    }
    assert expected <= set(paths)
    assert paths["/votos/cargos"]["get"]["summary"] == "Totais do cargo"
    assert "seção" in paths["/votos/secoes"]["get"]["description"]
    assert paths["/relatorios/poder"]["get"]["responses"]["200"]["content"]["text/html"]


def test_voting_routes_publish_the_domain_field_names() -> None:
    application = create_app(ports=_ports())
    cargos = _get(application, f"/votos/cargos?{_SCOPE}")
    assert cargos.status_code == 200
    assert cargos.json() == [
        {"tipo_voto": "nominal", "partido": 13, "numero": 13, "quantidade": 8},
    ]
    cities = _get(application, f"/votos/municipios?{_SCOPE}&numero=13")
    assert [row["municipio"] for row in cities.json()] == [1, 2]
    assert cities.json()[0]["quantidade"] == 9
    compared = _get(application, f"/votos/comparar?{_SCOPE}&primeiro=13&segundo=22")
    assert compared.json()[0]["votos_primeiro"] == 8
    power = _get(application, f"/votos/poder?{_SCOPE}")
    assert power.json()[0]["votos"] == 6
    participation = _get(application, f"/votos/participacao?{_SCOPE}")
    assert participation.json()[0]["abstencao"] == 4
    blanks = _get(application, f"/votos/brancos-nulos?{_SCOPE}")
    assert blanks.json()[0]["votos"] == 1
    leaders = _get(application, f"/votos/lideres?{_SCOPE}")
    assert leaders.json()[0]["numero"] == 13
    section = _get(
        application,
        "/votos/secoes?ano=2026&turno=1&uf=SE&municipio=1120&zona=1&secao=2",
    )
    assert section.json()[0]["cargo"] == "presidente"
    zones = _get(application, f"/votos/zonas?{_SCOPE}&municipio=1120&numero=13")
    assert zones.json()[0]["zona"] == 1
    findings = _get(application, f"/votos/indicios?{_SCOPE}")
    assert findings.json() == []


def test_missing_or_invalid_scope_is_portuguese_and_hides_internals() -> None:
    reader = _Reader()
    reader.fail = RuntimeError("secret-token")
    application = create_app(ports=_ports(reader))
    missing = _get(application, "/votos/cargos?ano=2026&turno=1&uf=SE")
    assert missing.status_code == 422
    assert missing.json()["detail"] == "Parâmetros inválidos."
    invalid = _get(application, "/votos/cargos?ano=2026&turno=1&uf=XX&cargo=presidente")
    assert invalid.status_code == 422
    assert invalid.json()["detail"] == "UF inválida."
    section = _get(application, "/votos/secoes?ano=2026&turno=1&uf=SE")
    assert section.status_code == 422
    exploded = _get(application, f"/votos/cargos?{_SCOPE}")
    assert exploded.status_code == 500
    body = exploded.text
    assert "secret-token" not in body
    assert "Traceback" not in body
    assert exploded.json()["detail"] == "Não foi possível consultar os dados."


def test_grade_json_uses_one_level_and_html_reuses_the_store() -> None:
    reader = _Reader()
    power = _PowerStore()
    application = create_app(ports=_ports(reader, power=power))
    grade = _get(application, f"/relatorios/dados/grade?{_SCOPE}&nivel=uf")
    assert grade.status_code == 200
    payload = grade.json()
    assert payload["nivel"] == "uf"
    assert payload["linhas"][0]["codigo"] == "SE"
    assert payload["linhas"][0]["celulas"][0]["fatia"]
    reader.calls.clear()
    cached = _get(application, f"/relatorios/poder?{_SCOPE}")
    assert cached.status_code == 200
    assert "text/html" in cached.headers["content-type"]
    assert "Poder do partido" in cached.text
    assert reader.calls == []
    assert power.saves == []
    refreshed = _get(application, f"/relatorios/poder?{_SCOPE}&atualizar=true")
    assert refreshed.status_code == 200
    assert "Aracaju" in refreshed.text
    assert power.saves
    assert any(name == "party_power" for name, *_rest in reader.calls)


def test_cross_report_json_and_cached_html() -> None:
    reader = _Reader()
    cross = _CrossStore()
    application = create_app(ports=_ports(reader, cross=cross))
    data = _get(application, "/relatorios/dados/presidente-governador?ano=2026&turno=1&uf=SE")
    assert data.status_code == 200
    place = data.json()["municipalities"][0]["places"][0]
    assert place["nome"] == "Rio Branco (AC)"
    assert place["presidente"]["leader"]["partido"] == 13
    assert reader.calls == []
    page = _get(application, "/relatorios/presidente-governador?ano=2026&turno=1&uf=SE")
    assert page.status_code == 200
    assert "text/html" in page.headers["content-type"]
    assert "Rio Branco" in page.text
    assert cross.saves == []
    recomputed = _get(
        application,
        "/relatorios/presidente-governador?ano=2026&turno=1&uf=SE&atualizar=true",
    )
    assert recomputed.status_code == 200
    assert "Aracaju" in recomputed.text
    assert cross.saves


def test_missing_pool_does_not_leak_the_driver() -> None:
    response = _get(create_app(), f"/votos/cargos?{_SCOPE}")
    assert response.status_code == 500
    assert "Traceback" not in response.text
    assert response.json()["detail"] == "Não foi possível consultar os dados."


def test_injected_ports_do_not_open_a_pool() -> None:
    application = create_app(ports=_ports())

    async def run() -> None:
        async with application.router.lifespan_context(application):
            assert getattr(application.state, "pool", None) is None

    asyncio.run(run())


def test_unknown_path_is_portuguese() -> None:
    response = _get(create_app(ports=_ports()), "/votos/inexistente")
    assert response.status_code == 404
    assert response.json()["detail"] == "Recurso não encontrado."


class _Reader:
    def __init__(self) -> None:
        self.calls: list[tuple[object, ...]] = []
        self.fail: BaseException | None = None
        self.empty_power = False

    async def totals(self, ano: int, turno: int, uf: str, cargo: str) -> tuple[TotalCargo, ...]:
        self._touch("totals", ano, turno, uf, cargo)
        return (TotalCargo("nominal", 13, 13, 8),)

    async def municipalities(
        self, ano: int, turno: int, uf: str, cargo: str, numero: int
    ) -> tuple[VotosMunicipio, ...]:
        self._touch("municipalities", ano, turno, uf, cargo, numero)
        return (VotosMunicipio(2, 5, 10), VotosMunicipio(1, 9, 10))

    async def comparison(
        self,
        ano: int,
        turno: int,
        uf: str,
        cargo: str,
        primeiro: int,
        segundo: int,
        nivel: str,
    ) -> tuple[Comparativo, ...]:
        self._touch("comparison", ano, turno, uf, cargo, primeiro, segundo, nivel)
        return (Comparativo(1120, None, None, 8, 3, 20),)

    async def party_power(
        self, ano: int, turno: int, ufs: tuple[str, ...], cargo: str, nivel: str
    ) -> tuple[PoderPartido, ...]:
        self._touch("party_power", ano, turno, ufs, cargo, nivel)
        if self.empty_power:
            return ()
        if nivel == "municipio":
            return (PoderPartido(1120, None, 13, 5, 1, 20),)
        return (PoderPartido(None, None, 13, 5, 1, 20),)

    async def participation(
        self, ano: int, turno: int, uf: str, cargo: str, nivel: str
    ) -> tuple[Participacao, ...]:
        self._touch("participation", ano, turno, uf, cargo, nivel)
        return (Participacao(1120, None, 20, 16),)

    async def blank_and_null(
        self, ano: int, turno: int, uf: str, cargo: str, nivel: str
    ) -> tuple[BrancosNulos, ...]:
        self._touch("blank_and_null", ano, turno, uf, cargo, nivel)
        return (BrancosNulos(1120, None, 1, 0, 20),)

    async def leading_candidate(
        self, ano: int, turno: int, uf: str, cargo: str, nivel: str
    ) -> tuple[PrimeiroColocado, ...]:
        self._touch("leading", ano, turno, uf, cargo, nivel)
        return (PrimeiroColocado(1120, None, 13, 13, 8, None, None, None, 20),)

    async def section_lines(
        self, ano: int, turno: int, uf: str, municipio: int, zona: int, secao: int
    ) -> tuple[LinhaVoto, ...]:
        self._touch("section_lines", ano, turno, uf, municipio, zona, secao)
        return (LinhaVoto("presidente", 1, "nominal", 13, 13, 8),)

    async def zones(
        self, ano: int, turno: int, uf: str, municipio: int, cargo: str, numero: int
    ) -> tuple[VotosZona, ...]:
        self._touch("zones", ano, turno, uf, municipio, cargo, numero)
        return (VotosZona(1, 8, 20),)

    async def section_projections(
        self, ano: int, turno: int, uf: str, cargo: str
    ) -> tuple[object, ...]:
        self._touch("section_projections", ano, turno, uf, cargo)
        return ()

    async def nominal_projections(
        self, ano: int, turno: int, uf: str, cargo: str
    ) -> tuple[object, ...]:
        self._touch("nominal_projections", ano, turno, uf, cargo)
        return ()

    async def blank_projections(
        self, ano: int, turno: int, uf: str, cargo: str
    ) -> tuple[object, ...]:
        self._touch("blank_projections", ano, turno, uf, cargo)
        return ()

    async def present_ufs(self, ano: int, turno: int, cargo: str) -> tuple[str, ...]:
        self._touch("present_ufs", ano, turno, cargo)
        return ("SE",)

    def _touch(self, name: str, *args: object) -> None:
        self.calls.append((name, *args))
        if self.fail is not None:
            raise self.fail


class _Names:
    def __init__(self) -> None:
        self.calls: list[str] = []

    async def names(self, uf: str) -> dict[int, str]:
        self.calls.append(uf)
        return {1120: "Aracaju"}


class _PowerStore:
    def __init__(self) -> None:
        self.saves: list[tuple[object, ...]] = []
        self.stored: StoredReport | None = StoredReport((), datetime(2026, 10, 4, tzinfo=UTC))
        self.by_cargo: dict[str, StoredReport | None] = {}
        self.level_calls: list[tuple[str, tuple[str, ...]]] = []

    async def load(self, _ano: int, _turno: int, _cargo: str) -> StoredReport | None:
        if self.saves:
            return None
        return self.stored

    async def load_levels(
        self,
        _ano: int,
        _turno: int,
        cargo: str,
        niveis: tuple[str, ...],
    ) -> StoredReport | None:
        self.level_calls.append((cargo, niveis))
        found = self.by_cargo.get(cargo, self.stored)
        if found is None:
            return None
        kept = tuple(cell for cell in found.cells if cell.nivel in niveis)
        return StoredReport(kept, found.gerado_em)

    async def save(
        self,
        ano: int,
        turno: int,
        cargo: str,
        cells: tuple[object, ...],
    ) -> datetime:
        self.saves.append((ano, turno, cargo, cells))
        return datetime(2026, 10, 8, tzinfo=UTC)


class _CrossStore:
    def __init__(self) -> None:
        self.saves: list[tuple[object, ...]] = []
        self.stored: StoredCrossReport | None = StoredCrossReport(
            (_cached_place(),),
            datetime(2026, 10, 4, tzinfo=UTC),
        )

    async def load(self, _ano: int, _turno: int) -> StoredCrossReport | None:
        if self.saves:
            return None
        return self.stored

    async def save(
        self,
        ano: int,
        turno: int,
        places: tuple[MunicipalPlace, ...],
    ) -> datetime:
        self.saves.append((ano, turno, places))
        return datetime(2026, 10, 8, tzinfo=UTC)


_POWER_HTML = """
<section><h2>Por estado — 2026, turno 1, presidente</h2>
<table><thead><tr>
<th>Lugar</th><th>Votos válidos</th><th>22</th><th>13</th>
</tr></thead><tbody><tr>
<td class="lugar" data-ord="Sergipe">Sergipe <small>SE</small></td>
<td class="validos" data-ord="10">10</td>
<td class="fatia" title="nominais 4, legenda 1, votos 5, votos válidos 10, comparecimento 12">
50,00%</td>
<td class="fatia" title="nominais 3, legenda 0, votos 3, votos válidos 10, comparecimento 12">
30,00%</td>
</tr></tbody></table></section>
<section><h2>Por município — 2026, turno 1, presidente</h2>
<table><thead><tr><th>Lugar</th><th>Votos válidos</th><th>13</th></tr></thead>
<tbody><tr>
<td class="lugar" data-ord="SANTA ROSA DO PURUS (AC)">
SANTA ROSA DO PURUS (AC) <small>1031</small></td>
<td class="validos">2.742</td>
<td class="fatia"
title="nominais 1384, legenda 0, votos 1384, votos válidos 2742, comparecimento 2884">
50,47%</td>
</tr></tbody></table></section>
"""


def _cached_place() -> MunicipalPlace:
    president = CargoTally((PartyTally(13, 10, 0),), 1, 2)
    governor = CargoTally((PartyTally(22, 4, 1),), 0, 0)
    return MunicipalPlace("AC", "10", "Rio Branco (AC)", president, governor)


def _ports(
    reader: _Reader | None = None,
    power: _PowerStore | None = None,
    cross: _CrossStore | None = None,
) -> ReadPorts:
    return ReadPorts(
        boletim=reader or _Reader(),
        names=_Names(),
        power_store=power or _PowerStore(),
        cross_store=cross or _CrossStore(),
    )


def _get(application: FastAPI, path: str) -> httpx.Response:
    return asyncio.run(_fetch(application, path))


async def _fetch(application: FastAPI, path: str) -> httpx.Response:
    transport = httpx.ASGITransport(app=application, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.get(path)


def test_validation_messages_follow_the_domain_rules() -> None:
    application = create_app(ports=_ports())
    scope = "ano=2026&turno=1&uf=SE&cargo=presidente"
    cases = (
        ("/votos/cargos?ano=1800&turno=1&uf=SE&cargo=presidente", "Ano inválido."),
        ("/votos/cargos?ano=2026&turno=3&uf=SE&cargo=presidente", "Turno inválido."),
        ("/votos/cargos?ano=2026&turno=1&uf=SE&cargo=", "Cargo inválido."),
        (f"/votos/municipios?{scope}&numero=-1", "Número inválido."),
        (f"/votos/municipios?{scope}&numero=13&ordem=lado", "Ordem inválida."),
        (f"/votos/poder?{scope}&nivel=bairro", "Nível inválido."),
    )
    for path, detail in cases:
        response = _get(application, path)
        assert response.status_code == 422
        assert response.json()["detail"] == detail


def test_empty_power_returns_an_empty_grid_and_cross_view() -> None:
    reader = _Reader()
    reader.empty_power = True
    cross = _CrossStore()
    cross.stored = None
    application = create_app(ports=_ports(reader, cross=cross))
    for nivel in ("municipio", "uf", "regiao", "pais"):
        grade = _get(application, f"/relatorios/dados/grade?{_SCOPE}&nivel={nivel}")
        assert grade.status_code == 200
        assert grade.json()["linhas"] == []
    cross = _get(application, "/relatorios/dados/presidente-governador?ano=2026&turno=1&uf=SE")
    assert cross.status_code == 200
    assert cross.json()["municipalities"] == []
    assert cross.json()["country"] is None


def test_grade_json_reads_stored_cells_without_the_reader() -> None:
    reader = _Reader()
    power = _PowerStore()
    power.stored = StoredReport(
        (StoredCell("uf", "SE", "Do cache", 20, 13, 5, 1),),
        datetime(2026, 10, 4, tzinfo=UTC),
    )
    application = create_app(ports=_ports(reader, power=power))
    grade = _get(application, f"/relatorios/dados/grade?{_SCOPE}&nivel=uf")
    assert grade.status_code == 200
    row = grade.json()["linhas"][0]
    assert row["codigo"] == "SE"
    assert row["nome"] == "Do cache"
    assert row["celulas"][0]["partido"] == 13
    assert row["celulas"][0]["votos"] == 6
    assert reader.calls == []
    assert power.saves == []


def test_power_html_cells_keep_nominal_and_legend_votes() -> None:
    cells = cells_from_power_html(_POWER_HTML)
    assert [(cell.nivel, cell.codigo, cell.partido, cell.votos_nominais) for cell in cells] == [
        ("uf", "SE", 22, 4),
        ("uf", "SE", 13, 3),
        ("municipio", "1031", 13, 1384),
    ]
    city = cells[2]
    assert city.nome == "SANTA ROSA DO PURUS (AC)"
    assert city.votos_legenda == 0
    assert city.comparecimento == 2884


def test_missing_cached_html_is_computed_and_stored() -> None:
    reader = _Reader()
    power = _PowerStore()
    power.stored = None
    application = create_app(ports=_ports(reader, power=power))
    page = _get(application, f"/relatorios/poder?{_SCOPE}")
    assert page.status_code == 200
    assert "Aracaju" in page.text
    assert power.saves


def test_missing_cross_json_is_computed_and_stored() -> None:
    reader = _Reader()
    cross = _CrossStore()
    cross.stored = None
    application = create_app(ports=_ports(reader, cross=cross))
    data = _get(application, "/relatorios/dados/presidente-governador?ano=2026&turno=1&uf=SE")
    assert data.status_code == 200
    place = data.json()["municipalities"][0]["places"][0]
    assert place["classe"] == "consolidacao"
    assert place["margin"]
    assert place["nome"] == "Aracaju (SE)"
    assert place["presidente"]["leader"]["partido"] == 13
    assert cross.saves


def test_missing_cross_html_is_computed_and_stored() -> None:
    reader = _Reader()
    cross = _CrossStore()
    cross.stored = None
    application = create_app(ports=_ports(reader, cross=cross))
    page = _get(application, "/relatorios/presidente-governador?ano=2026&turno=1&uf=SE")
    assert page.status_code == 200
    assert "Aracaju" in page.text
    assert cross.saves


def test_database_error_stays_a_client_message() -> None:
    reader = _Reader()
    reader.fail = ElectionError("database read failed")
    response = _get(create_app(ports=_ports(reader)), f"/votos/poder?{_SCOPE}")
    assert response.status_code == 500
    assert "database" not in response.text


_MISSING_POWER = (
    "O relatório de poder de presidente ainda não foi gravado. "
    "Gere com: uv run python scripts/relatorio_poder.py --cargo presidente --sem-navegador"
)


def test_grade_somente_gravado_returns_the_stored_cells() -> None:
    reader = _Reader()
    power = _PowerStore()
    power.stored = StoredReport(
        (StoredCell("uf", "SE", "Do cache", 20, 13, 5, 1),),
        datetime(2026, 10, 4, tzinfo=UTC),
    )
    application = create_app(ports=_ports(reader, power=power))
    grade = _get(application, f"/relatorios/dados/grade?{_SCOPE}&nivel=uf&somente_gravado=true")
    assert grade.status_code == 200
    assert grade.json()["linhas"][0]["nome"] == "Do cache"
    assert reader.calls == []


def test_grade_somente_gravado_without_a_row_is_409_and_skips_the_reader() -> None:
    for stored in (None, StoredReport((), datetime(2026, 10, 4, tzinfo=UTC))):
        reader = _Reader()
        power = _PowerStore()
        power.stored = stored
        application = create_app(ports=_ports(reader, power=power))
        grade = _get(application, f"/relatorios/dados/grade?{_SCOPE}&somente_gravado=true")
        assert grade.status_code == 409
        assert grade.json()["detail"] == _MISSING_POWER
        assert reader.calls == []
        assert power.saves == []


def test_grade_without_somente_gravado_still_reads_the_ballots() -> None:
    reader = _Reader()
    power = _PowerStore()
    power.stored = None
    application = create_app(ports=_ports(reader, power=power))
    grade = _get(application, f"/relatorios/dados/grade?{_SCOPE}&somente_gravado=false")
    assert grade.status_code == 200
    assert grade.json()["linhas"][0]["codigo"] == "1120"
    assert any(name == "party_power" for name, *_rest in reader.calls)
    assert power.saves == []


_FORCA = "/relatorios/dados/forca?ano=2026&turno=1"


def _forca_power() -> _PowerStore:
    power = _PowerStore()
    moment = datetime(2026, 10, 22, tzinfo=UTC)
    power.by_cargo = {
        "presidente": StoredReport(
            (
                StoredCell("pais", "BR", "Brasil", 100, 22, 60, 0),
                StoredCell("uf", "AC", "Acre", 100, 22, 60, 0),
            ),
            moment,
        ),
        "deputadoFederal": None,
        "deputadoEstadual": StoredReport(
            (
                StoredCell("uf", "AC", "Acre", 100, 22, 30, 5),
                StoredCell("municipio", "1", "RIO BRANCO (AC)", 100, 22, 30, 5),
            ),
            moment,
        ),
    }
    return power


def test_forca_returns_integer_counts_and_lists_missing_offices() -> None:
    power = _forca_power()
    application = create_app(ports=_ports(power=power))
    response = _get(application, _FORCA)
    assert response.status_code == 200
    body = response.json()
    assert body["cargo_referencia"] == "deputadoEstadual"
    assert body["limiares"] == [1, 2, 5, 10, 20]
    assert body["faltando"] == [
        {
            "cargo": "deputadoFederal",
            "comando": (
                "uv run python scripts/relatorio_poder.py --cargo deputadoFederal --sem-navegador"
            ),
        }
    ]
    unidade = body["pais"]["unidades"][0]
    assert unidade["chave"] == "22"
    assert unidade["tipo"] == "partido"
    assert unidade["presidente"] == 60
    assert unidade["deputado_federal"] is None
    assert unidade["deputado_estadual"] == 35
    assert unidade["ufs_lider_estadual"] == 1
    # Party-label votes: from the same rows as the totals; no federal source, so null.
    assert (unidade["legenda_federal"], unidade["legenda_estadual"]) == (None, 5)
    assert unidade["municipal"]["lidera"] == 1
    assert unidade["municipal"]["presenca"] == [
        {"limiar": limiar, "municipios": 1} for limiar in (1, 2, 5, 10, 20)
    ]
    assert body["pais"]["base"] == {
        "validos_presidente": 60,
        "validos_deputado_federal": None,
        "validos_deputado_estadual": 35,
        "ufs_deputado_estadual": 1,
        "municipal": {"municipios": 1, "validos": 35, "empates": 0},
        "cadeiras": None,
        "municipal_2024": None,
    }
    assert body["ufs"][0]["codigo"] == "AC"
    assert power.level_calls == [
        ("presidente", ("pais", "uf")),
        ("deputadoFederal", ("pais", "uf")),
        ("deputadoEstadual", ("uf", "municipio")),
    ]
    assert power.saves == []


def test_forca_without_any_stored_office_is_409() -> None:
    power = _PowerStore()
    power.stored = None
    response = _get(create_app(ports=_ports(power=power)), _FORCA)
    assert response.status_code == 409
    assert "placar de força" in response.json()["detail"]


def test_forca_rejects_an_unknown_reference_office() -> None:
    response = _get(create_app(ports=_ports()), f"{_FORCA}&cargo_referencia=deputadoDistrital")
    assert response.status_code == 422
    assert response.json()["detail"] == "Cargo inválido."


class _SeatEstimates:
    def __init__(self, estimate: EstimativaCadeiras | None) -> None:
        self.estimate = estimate

    async def load(self, _ano: int, _turno: int) -> EstimativaCadeiras | None:
        return self.estimate


def _seat_estimate() -> EstimativaCadeiras:
    moment = datetime(2026, 10, 22, tzinfo=UTC)
    return EstimativaCadeiras(
        ano=2026,
        turno=1,
        gerado_em=moment,
        federacoes=(Federacao("pl-x", "Federação PL X", (22, 99)),),
        totais=TotaisCadeiras(camara=513, senado=54, governadores=27, assembleias=1059),
        linhas=(
            CadeirasUnidade("22", "AC", 4, 1, 1, 0, 9),
            CadeirasUnidade("fed:pl-x", "AC", 4, 1, 1, 0, 9),
            CadeirasUnidade("22", "BR", 119, 14, 3, 5, 200),
            CadeirasUnidade("fed:pl-x", "BR", 119, 14, 3, 5, 200),
        ),
    )


def _forca_with_seats(estimate: EstimativaCadeiras | None) -> Any:
    ports = replace(_ports(power=_forca_power()), seat_estimates=_SeatEstimates(estimate))
    response = _get(create_app(ports=ports), _FORCA)
    assert response.status_code == 200
    return response.json()


def test_forca_with_seat_estimates_adds_seats_and_federation_rows() -> None:
    body = _forca_with_seats(_seat_estimate())
    assert body["cadeiras"] == {
        "disponivel": True,
        "comando": None,
        "totais": {"camara": 513, "senado": 54, "governadores": 27, "assembleias": 1059},
    }
    pais = body["pais"]
    (partido,) = pais["unidades"]
    (federacao,) = pais["federadas"]
    assert (partido["chave"], partido["tipo"], partido["nome"]) == ("22", "partido", None)
    assert (federacao["chave"], federacao["tipo"]) == ("fed:pl-x", "federacao")
    assert federacao["nome"] == "Federação PL X"
    assert federacao["partidos"] == [22, 99]
    assert federacao["camara"] == 119
    assert pais["base_federada"]["cadeiras"] == body["cadeiras"]["totais"]
    assert body["ufs"][0]["federadas"][0]["camara"] == 4
    seats = ("camara", "senado", "governador_1t", "governador_2t", "assembleia")
    assert [partido[campo] for campo in seats] == [119, 14, 3, 5, 200]
    assert pais["base"]["cadeiras"] == body["cadeiras"]["totais"]
    assert body["ufs"][0]["base"]["cadeiras"] == {
        "camara": 4,
        "senado": 1,
        "governadores": 1,
        "assembleias": 9,
    }


def test_forca_without_a_stored_estimate_flags_seats_unavailable() -> None:
    body = _forca_with_seats(None)
    assert body["cadeiras"] == {
        "disponivel": False,
        "comando": "uv run python scripts/relatorio_cadeiras.py",
        "totais": None,
    }
    pais = body["pais"]
    unidade = pais["unidades"][0]
    assert unidade["camara"] is None
    assert unidade["assembleia"] is None
    assert pais["base"]["cadeiras"] is None


def test_forca_without_the_seat_port_has_no_seat_block() -> None:
    response = _get(create_app(ports=_ports(power=_forca_power())), _FORCA)
    assert response.status_code == 200
    body = response.json()
    assert body["cadeiras"] is None
    assert body["pais"]["unidades"][0]["camara"] is None
    assert body["pais"]["federadas"] == []
    assert body["pais"]["base_federada"] is None
    assert body["municipal_2024"] is None


class _Municipal2024Port:
    def __init__(self, found: Municipal2024 | None) -> None:
        self.found = found

    async def load(self) -> Municipal2024 | None:
        return self.found


def _forca_with_2024(found: Municipal2024 | None) -> Any:
    ports = replace(_ports(power=_forca_power()), municipal_2024=_Municipal2024Port(found))
    response = _get(create_app(ports=ports), _FORCA)
    assert response.status_code == 200
    return response.json()


def test_forca_with_2024_results_adds_mayors_and_councillors() -> None:
    moment = datetime(2026, 10, 1, 8, 30, tzinfo=UTC)
    found = Municipal2024(
        data_corte=moment,
        importado_em=moment,
        equivalencia_versao="v1",
        totais=(
            TotaisMunicipal2024("AC", 22, 22, 600, 230),
            TotaisMunicipal2024("BR", 5569, 5560, 155912680, 58000),
        ),
        linhas=(
            MunicipalPartido2024(22, "AC", 9, 300, 40),
            MunicipalPartido2024(22, "BR", 500, 2000, 4000),
        ),
        sem_correspondencia=(),
    )
    body = _forca_with_2024(found)
    totais_br = {
        "municipios": 5569,
        "com_prefeito": 5560,
        "eleitorado": 155912680,
        "vereadores": 58000,
    }
    assert body["municipal_2024"] == {
        "disponivel": True,
        "comando": None,
        "data_corte": "2026-10-01T08:30:00Z",
        "totais": totais_br,
    }
    pais = body["pais"]
    unidade = pais["unidades"][0]
    assert [unidade[k] for k in ("prefeitos", "eleitorado_governado", "vereadores")] == [
        500,
        2000,
        4000,
    ]
    assert pais["base"]["municipal_2024"] == totais_br
    acre = body["ufs"][0]
    assert acre["base"]["municipal_2024"] == {
        "municipios": 22,
        "com_prefeito": 22,
        "eleitorado": 600,
        "vereadores": 230,
    }
    uf_unit = acre["unidades"][0]
    assert [uf_unit[k] for k in ("prefeitos", "eleitorado_governado", "vereadores")] == [9, 300, 40]


def test_forca_without_2024_import_flags_the_block() -> None:
    body = _forca_with_2024(None)
    assert body["municipal_2024"] == {
        "disponivel": False,
        "comando": "make download-municipais && make import-municipais",
        "data_corte": None,
        "totais": None,
    }
    assert body["pais"]["unidades"][0]["prefeitos"] is None
    assert body["pais"]["base"]["municipal_2024"] is None
