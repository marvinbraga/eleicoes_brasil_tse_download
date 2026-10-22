"""Capillarity route and job: contract fields, exact labels, scopes and the cache."""

import asyncio
from fractions import Fraction
from typing import cast

import httpx
import pytest
from fastapi import FastAPI
from tests.adapters.test_read_api import _ports as _read_ports

from eleicoes.adapters.http.dependencies import clear_report_caches, get_capillarity_job
from eleicoes.adapters.http.schemas_capilaridade import NOTES, format_times, motivo
from eleicoes.composition.api import create_app
from eleicoes.domain.capilaridade import PartyMetrics, Share
from eleicoes.domain.capilaridade_classe import (
    CapillarityReport,
    Classification,
    ClassifiedParty,
)
from eleicoes.domain.errors import ElectionError, InvalidRecorteError, MissingPowerReportError
from eleicoes.domain.stored_grade import StoredCell
from eleicoes.use_cases.apresentar_capilaridade import build_capillarity


class _Cells:
    def __init__(self, cells: tuple[StoredCell, ...]) -> None:
        self.cells = cells
        self.calls: list[tuple[int, int, str]] = []
        self.closed = False

    def municipal_cells(self, ano: int, turno: int, cargo: str) -> tuple[StoredCell, ...]:
        self.calls.append((ano, turno, cargo))
        return self.cells

    def close(self) -> None:
        self.closed = True


def _uf_cells(uf: str, start: int, partido: int, votos: int) -> tuple[StoredCell, ...]:
    return tuple(
        cell
        for i in range(start, start + 25)
        for cell in (
            StoredCell("municipio", str(i), f"M{i} ({uf})", 1000, partido, votos + i % 7, 0),
            StoredCell("municipio", str(i), f"M{i} ({uf})", 1000, 22, 90 - i % 7, 0),
        )
    )


def _counting(monkeypatch: pytest.MonkeyPatch) -> list[_Cells]:
    opened: list[_Cells] = []

    def fresh() -> _Cells:
        reader = _Cells(_uf_cells("AC", 0, 13, 10))
        opened.append(reader)
        return reader

    monkeypatch.setattr("eleicoes.use_cases.apresentar_capilaridade._production_reader", fresh)
    return opened


def test_capillarity_job_builds_once_per_key_and_closes_the_reader(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    opened = _counting(monkeypatch)
    first = get_capillarity_job()(2026, 1, "governador")
    assert get_capillarity_job()(2026, 1, "governador") is first
    assert len(opened) == 1
    assert opened[0].closed is True
    get_capillarity_job()(2026, 1, "senador")
    assert len(opened) == 2


def test_capillarity_job_does_not_cache_an_error(monkeypatch: pytest.MonkeyPatch) -> None:
    attempts: list[int] = []

    def failing() -> _Cells:
        attempts.append(1)
        raise ElectionError("database session is not configured")

    monkeypatch.setattr("eleicoes.use_cases.apresentar_capilaridade._production_reader", failing)
    for _attempt in range(2):
        with pytest.raises(ElectionError):
            get_capillarity_job()(2026, 1, "governador")
    assert len(attempts) == 2


def test_clear_report_caches_drops_the_capillarity_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    opened = _counting(monkeypatch)
    first = get_capillarity_job()(2026, 1, "governador")
    clear_report_caches()
    assert get_capillarity_job()(2026, 1, "governador") is not first
    assert len(opened) == 2


_RIO_BRANCO = "1392"
_TOP_KEYS = {
    "ano",
    "turno",
    "cargo",
    "recorte",
    "municipios",
    "ufs",
    "sem_validos",
    "votos_validos",
    "exterior",
    "limites",
    "partidos",
    "resumo",
    "notas",
}
_BAND_ORDER = [
    "zero",
    "ate_metade",
    "metade_a_media",
    "media_a_1_5",
    "1_5_a_2",
    "2_a_3",
    "3_ou_mais",
]
_BASE_QUERY = "ano=2026&turno=1&cargo=governador"


def _place(codigo: str, nome: str, votos: dict[int, int]) -> tuple[StoredCell, ...]:
    return tuple(
        StoredCell("municipio", codigo, nome, 1000, partido, count, 0)
        for partido, count in votos.items()
    )


def _sample() -> tuple[StoredCell, ...]:
    """25 places in AC and 25 in PE; 77 votes only in AC; 50 only in Rio Branco."""
    acre = tuple(
        cell
        for i in range(25)
        for cell in _place(f"{100 + i}", f"A{i} (AC)", {13: 10 + i % 7, 22: 90 - i % 7, 77: 20})
    )
    capital = _place(_RIO_BRANCO, "RIO BRANCO (AC)", {13: 10, 22: 90, 77: 20, 50: 300})
    pernambuco = tuple(
        cell
        for i in range(25)
        for cell in _place(f"{200 + i}", f"P{i} (PE)", {13: 10 + i % 7, 22: 90 - i % 7})
    )
    abroad = _place("29999", "LISBOA (ZZ)", {13: 4})
    return acre + capital + pernambuco + abroad


def _app(cells: tuple[StoredCell, ...]) -> FastAPI:
    application = create_app(ports=_read_ports())

    def job(ano: int, turno: int, cargo: str) -> CapillarityReport:
        return build_capillarity(_Cells(cells), ano, turno, cargo)

    application.dependency_overrides[get_capillarity_job] = lambda: job
    return application


def _get(application: FastAPI, query: str) -> httpx.Response:
    return asyncio.run(_fetch(application, f"/relatorios/dados/capilaridade?{query}"))


async def _fetch(application: FastAPI, path: str) -> httpx.Response:
    transport = httpx.ASGITransport(app=application, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.get(path)


def _party(body: dict[str, object], partido: int) -> dict[str, object]:
    rows = body["partidos"]
    assert isinstance(rows, list)
    found = [row for row in rows if row["partido"] == partido]
    assert len(found) == 1
    return cast(dict[str, object], found[0])


def test_capilaridade_brasil_has_the_contract_fields() -> None:
    response = _get(_app(_sample()), _BASE_QUERY)
    assert response.status_code == 200
    body = response.json()
    assert set(body) == _TOP_KEYS
    assert body["recorte"] == {"tipo": "pais", "codigo": "BR", "nome": "Brasil"}
    assert (body["municipios"], body["ufs"], body["exterior"]) == (51, 2, 1)
    assert all([b["chave"] for b in p["faixas"]] == _BAND_ORDER for p in body["partidos"])
    assert [r["partido"] for r in body["resumo"]] == [p["partido"] for p in body["partidos"]]
    assert body["limites"] == {
        "presenca": "5,00%",
        "pouco_voto": "1,00%",
        "minimo_municipios": 20,
        "capitais_vezes": "1,75",
        "regional_parte": "50,00%",
        "regional_vezes": "1,50",
        "poucos_parte": "50,00%",
        "poucos_vezes": "2,00",
    }
    assert body["notas"] == list(NOTES)
    capital = _party(body, 50)
    assert capital["classe"] == "capitais"
    assert capital["rotulo_classe"] == "Concentrado nas capitais"
    assert (capital["ufs_com_voto"], capital["municipios"]) == (1, 26)


def test_capilaridade_regional_label_and_reason_are_exact() -> None:
    body = _get(_app(_sample()), _BASE_QUERY).json()
    acre_only = _party(body, 77)
    assert acre_only["classe"] == "regional"
    assert acre_only["rotulo_classe"] == "Regional (Norte)"
    assert str(acre_only["motivo"]).startswith("Norte deu 100,00% dos votos do partido, ")


def test_capilaridade_uf_scope_has_no_subdivisions_and_uf_labels() -> None:
    body = _get(_app(_sample()), f"{_BASE_QUERY}&uf=ac").json()
    assert body["recorte"] == {"tipo": "uf", "codigo": "AC", "nome": "Acre"}
    assert all(p["subdivisoes"] == [] for p in body["partidos"])
    assert _party(body, 22)["rotulo_classe"] == "Espalhado pelo estado"
    assert _party(body, 50)["rotulo_classe"] == "Concentrado na capital"


def test_capilaridade_region_scope_uses_region_labels() -> None:
    body = _get(_app(_sample()), f"{_BASE_QUERY}&regiao=NE").json()
    assert body["recorte"] == {"tipo": "regiao", "codigo": "NE", "nome": "Nordeste"}
    assert _party(body, 22)["rotulo_classe"] == "Espalhado pela região"


def test_capilaridade_both_scopes_is_422() -> None:
    response = _get(_app(_sample()), f"{_BASE_QUERY}&regiao=NE&uf=PE")
    assert response.status_code == 422
    assert response.json() == {"detail": str(InvalidRecorteError())}


def test_capilaridade_abroad_is_422_and_unknown_uf_is_422() -> None:
    abroad = _get(_app(_sample()), f"{_BASE_QUERY}&uf=ZZ")
    assert (abroad.status_code, abroad.json()["detail"]) == (422, str(InvalidRecorteError()))
    unknown = _get(_app(_sample()), f"{_BASE_QUERY}&uf=QQ")
    assert (unknown.status_code, unknown.json()["detail"]) == (422, "UF inválida.")


def test_capilaridade_missing_scope_is_409() -> None:
    response = _get(_app(_sample()), f"{_BASE_QUERY}&uf=SP")
    assert response.status_code == 409
    assert response.json() == {
        "detail": "Não há municípios gravados para governador no recorte São Paulo."
    }


def test_capilaridade_without_cells_is_409_with_the_power_hint() -> None:
    response = _get(_app(()), _BASE_QUERY)
    assert response.status_code == 409
    assert response.json() == {"detail": str(MissingPowerReportError("governador"))}


def test_capilaridade_bad_cargo_is_422() -> None:
    response = _get(_app(_sample()), "ano=2026&turno=1&cargo=prefeito")
    assert (response.status_code, response.json()) == (422, {"detail": "Cargo inválido."})


def test_format_times_rounds_half_up() -> None:
    assert format_times(Fraction(2175, 1000)) == "2,18"
    assert format_times(Fraction(7, 4)) == "1,75"
    assert format_times(Fraction(0)) == "0,00"


def _classified(capitais: Share, classe: str) -> ClassifiedParty:
    metrics = PartyMetrics(
        partido=50,
        votos=10,
        validos=100,
        validos_recorte=100,
        ufs_com_voto=27,
        municipios=100,
        indice=Fraction(1, 5),
        top10=Share(10, 2, 10, Fraction(1, 5), Fraction(1, 10)),
        presenca=50,
        capitais=capitais,
        subdivisoes=(),
        faixas=(),
        fortes=(),
        maiores=(),
    )
    return ClassifiedParty(metrics, Classification(classe))


def test_motivo_uses_vez_below_two() -> None:
    below = _classified(Share(27, 7, 20, Fraction(7, 10), Fraction(2, 5)), "capitais")
    assert "1,75 vez o peso" in motivo(below)
    twice = _classified(Share(27, 8, 20, Fraction(4, 5), Fraction(2, 5)), "capitais")
    assert motivo(twice) == (
        "As capitais deram 80,00% dos votos do partido, "
        "2,00 vezes o peso delas no eleitorado (40,00%)."
    )


def test_other_reasons_are_exact() -> None:
    capitals = Share(27, 1, 20, Fraction(1, 10), Fraction(1, 5))
    assert motivo(_classified(capitals, "espalhado")) == (
        "Nenhuma regra de concentração se aplicou. Os 10 municípios onde é mais forte "
        "deram 20,00% dos votos e têm 10,00% do eleitorado."
    )
    assert motivo(_classified(capitals, "poucos_municipios")) == (
        "Os 10 municípios onde é mais forte deram 20,00% dos votos, "
        "2,00 vezes o peso deles no eleitorado (10,00%)."
    )
    assert motivo(_classified(capitals, "pouco_voto")) == (
        "Teve 10,00% dos votos válidos onde recebeu voto, abaixo de 1,00%."
    )
    assert motivo(_classified(capitals, "sem_base")) == (
        "Só 100 municípios com voto; são precisos 20 para classificar."
    )
