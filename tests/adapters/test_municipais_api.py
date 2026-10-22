"""GET /relatorios/dados/municipais-2024 with a fake reader."""

import asyncio
from datetime import UTC, date, datetime

import httpx
from fastapi import FastAPI
from tests.adapters.test_read_api import _ports

from eleicoes.adapters.http.bundle import ReadPorts
from eleicoes.composition.api import create_app
from eleicoes.domain.forca_municipal import (
    MunicipalCountsByUf,
    MunicipalTotals,
    PartyCouncil,
    PartyMayors,
    StoredCouncil,
    StoredMayor,
    StoredMunicipality,
    StoredMunicipalResults,
)

_CORTE = datetime(2026, 10, 22, 2, 17)
_IMPORTADO = datetime(2026, 10, 22, 13, 5, 11, 120000, tzinfo=UTC)
_TOP = {
    "ano",
    "uf",
    "data_corte",
    "importado_em",
    "equivalencia_versao",
    "totais",
    "partidos",
    "municipios",
    "notas",
}


class _Reader:
    def __init__(self, stored: StoredMunicipalResults | None) -> None:
        self.stored = stored
        self.calls: list[tuple[int, str | None]] = []

    async def load(self, ano: int, uf: str | None) -> StoredMunicipalResults | None:
        self.calls.append((ano, uf))
        return self.stored

    async def party_counts_by_uf(self, ano: int) -> MunicipalCountsByUf | None:
        del ano
        return None


def _stored(municipios: tuple[StoredMunicipality, ...] = ()) -> StoredMunicipalResults:
    return StoredMunicipalResults(
        ano=2024,
        corte=_CORTE,
        importado_em=_IMPORTADO,
        totais=MunicipalTotals(2, 1, 1, 1, 21000, 4, 18, 1),
        prefeitos=(PartyMayors(35, "PMB", 1, 12000),),
        vereadores=(PartyCouncil(22, "PL", 4, 1),),
        municipios=municipios,
    )


def _guape() -> StoredMunicipality:
    mayor = StoredMayor(35, "PMB", "DR PEDRO", 1, True, date(2025, 7, 6))
    return StoredMunicipality("MG", "45616", "GUAPÉ", 12000, mayor, (StoredCouncil(22, "PL", 4),))


def _merces() -> StoredMunicipality:
    return StoredMunicipality("MG", "48313", "MERCÊS", 9000, None, ())


def _app(reader: _Reader | None) -> FastAPI:
    base = _ports()
    ports = ReadPorts(
        boletim=base.boletim,
        names=base.names,
        power_store=base.power_store,
        cross_store=base.cross_store,
        municipais=reader,
    )
    return create_app(ports=ports)


def _get(application: FastAPI, path: str) -> httpx.Response:
    async def fetch() -> httpx.Response:
        transport = httpx.ASGITransport(app=application, raise_app_exceptions=False)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get(path)

    return asyncio.run(fetch())


def test_national_json_has_the_contract_keys_and_no_municipalities() -> None:
    reader = _Reader(_stored())
    response = _get(_app(reader), "/relatorios/dados/municipais-2024")
    assert response.status_code == 200
    body = response.json()
    assert set(body) == _TOP
    assert reader.calls == [(2024, None)]
    assert (body["ano"], body["uf"], body["equivalencia_versao"]) == (2024, None, "2026-10-22")
    assert body["data_corte"] == "2026-10-22T02:17:00"
    assert body["importado_em"] == "2026-10-22T13:05:11.120000Z"
    assert body["totais"] == {
        "municipios": 2,
        "com_prefeito": 1,
        "sem_prefeito": 1,
        "suplementares": 1,
        "eleitorado": 21000,
        "vereadores": 4,
        "vagas_vereador": 18,
        "divergencias_vagas": 1,
    }
    assert body["partidos"] == [
        {
            "numero": 35,
            "sigla_2024": "PMB",
            "numero_2026": 35,
            "sigla_2026": "DEMOCRATA",
            "equivalencia": "renomeado",
            "nota": "O PMB passou a se chamar Democrata em 2/12/2025.",
            "prefeitos": 1,
            "eleitorado_governado": 12000,
            "vereadores": 0,
            "municipios_com_vereador": 0,
        },
        {
            "numero": 22,
            "sigla_2024": "PL",
            "numero_2026": 22,
            "sigla_2026": "PL",
            "equivalencia": "mesmo",
            "nota": "",
            "prefeitos": 0,
            "eleitorado_governado": 0,
            "vereadores": 4,
            "municipios_com_vereador": 1,
        },
    ]
    assert body["municipios"] == []
    assert body["notas"] == [
        "Situação divulgada pelo TSE em 22/10/2026 às 02:17. Cassações e eleições suplementares "
        "posteriores a 2024 já estão refletidas.",
        "Eleitorado governado é o eleitorado apto do 1º turno de 2024 nos municípios onde o "
        "partido tem o prefeito; não é população.",
        "Vereadores contam pelo partido do candidato, não pela federação ou coligação.",
        "1 município(s) sem prefeito eleito nos dados do TSE.",
        "1 município(s) com número de vereadores eleitos diferente das vagas.",
        "O PMB passou a se chamar Democrata em 2/12/2025.",
    ]


def test_uf_json_lists_the_municipalities() -> None:
    reader = _Reader(_stored((_guape(), _merces())))
    response = _get(_app(reader), "/relatorios/dados/municipais-2024?uf=mg")
    assert response.status_code == 200
    body = response.json()
    assert set(body) == _TOP
    assert reader.calls == [(2024, "MG")]
    assert body["uf"] == "MG"
    assert body["municipios"] == [
        {
            "uf": "MG",
            "codigo_tse": "45616",
            "nome": "GUAPÉ",
            "eleitorado": 12000,
            "prefeito": {
                "numero_partido": 35,
                "sigla_2024": "PMB",
                "sigla_2026": "DEMOCRATA",
                "nome_urna": "DR PEDRO",
                "turno": 1,
                "suplementar": True,
                "data_eleicao": "2025-07-06",
            },
            "vereadores": [{"numero": 22, "sigla_2024": "PL", "eleitos": 4}],
        },
        {
            "uf": "MG",
            "codigo_tse": "48313",
            "nome": "MERCÊS",
            "eleitorado": 9000,
            "prefeito": None,
            "vereadores": [],
        },
    ]


def test_federal_district_and_abroad_are_rejected() -> None:
    reader = _Reader(_stored())
    for uf in ("DF", "ZZ", "XX"):
        response = _get(_app(reader), f"/relatorios/dados/municipais-2024?uf={uf}")
        assert response.status_code == 422
        assert response.json() == {"detail": "UF inválida."}
    assert reader.calls == []


def test_missing_import_is_409_with_the_commands() -> None:
    response = _get(_app(_Reader(None)), "/relatorios/dados/municipais-2024")
    assert response.status_code == 409
    detail = response.json()["detail"]
    assert detail.startswith("Os resultados municipais de 2024 ainda não foram importados.")
    assert "import-municipais --ano 2024" in detail


def test_ports_without_the_reader_are_a_generic_error() -> None:
    response = _get(_app(None), "/relatorios/dados/municipais-2024")
    assert response.status_code == 500
    assert response.json() == {"detail": "Não foi possível consultar os dados."}


def test_openapi_lists_the_route() -> None:
    spec = _get(_app(_Reader(None)), "/openapi.json").json()
    assert "/relatorios/dados/municipais-2024" in spec["paths"]
