"""HTTP read API. Fakes stand in for Postgres; no Docker and no network."""

import asyncio
from datetime import UTC, datetime

import httpx
from fastapi import FastAPI

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
        "/relatorios/dados/presidente-governador",
        "/relatorios/poder",
        "/relatorios/presidente-governador",
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
    assert place["classe"] == "consolidacao"
    assert place["margin"]
    assert place["presidente"]["leader"]["partido"] == 13
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

    async def load(self, _ano: int, _turno: int, _cargo: str) -> StoredReport | None:
        if self.saves:
            return None
        return self.stored

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
    application = create_app(ports=_ports(reader))
    for nivel in ("municipio", "uf", "regiao", "pais"):
        grade = _get(application, f"/relatorios/dados/grade?{_SCOPE}&nivel={nivel}")
        assert grade.status_code == 200
        assert grade.json()["linhas"] == []
    cross = _get(application, "/relatorios/dados/presidente-governador?ano=2026&turno=1&uf=SE")
    assert cross.status_code == 200
    assert cross.json()["municipalities"] == []
    assert cross.json()["country"] is None


def test_missing_cached_html_is_computed_and_stored() -> None:
    reader = _Reader()
    power = _PowerStore()
    power.stored = None
    application = create_app(ports=_ports(reader, power=power))
    page = _get(application, f"/relatorios/poder?{_SCOPE}")
    assert page.status_code == 200
    assert "Aracaju" in page.text
    assert power.saves


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
