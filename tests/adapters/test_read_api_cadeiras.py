"""GET /relatorios/dados/cadeiras with fake ports."""

import asyncio
from datetime import UTC, datetime

import httpx
from fastapi import FastAPI
from tests.adapters.test_read_api import _ports

from eleicoes.adapters.http.bundle import ReadPorts
from eleicoes.composition.api import create_app
from eleicoes.domain.cadeiras import CARGOS_GRAVADOS
from eleicoes.domain.simulacao_cadeiras import VotoApurado
from eleicoes.ports.relatorio_cadeiras import StoredSeatVotes

_MOMENT = datetime(2026, 10, 22, tzinfo=UTC)
_FEDERAL = (
    VotoApurado("deputadoFederal", "AC", "nominal", 1301, 250),
    VotoApurado("deputadoFederal", "AC", "nominal", 6501, 150),
    VotoApurado("deputadoFederal", "AC", "legenda", 65, 10),
    VotoApurado("deputadoFederal", "AC", "nominal", 2201, 390),
)


class _SeatStore:
    def __init__(self, stored: tuple[StoredSeatVotes, ...]) -> None:
        self.stored = stored

    async def load(self, _ano: int, _turno: int) -> tuple[StoredSeatVotes, ...]:
        return self.stored


def _app(stored: tuple[StoredSeatVotes, ...]) -> FastAPI:
    base = _ports()
    ports = ReadPorts(
        boletim=base.boletim,
        names=base.names,
        power_store=base.power_store,
        cross_store=base.cross_store,
        seat_store=_SeatStore(stored),
    )
    return create_app(ports=ports)


def _get(application: FastAPI, path: str) -> httpx.Response:
    async def fetch() -> httpx.Response:
        transport = httpx.ASGITransport(app=application, raise_app_exceptions=False)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get(path)

    return asyncio.run(fetch())


_SENADO = (VotoApurado("senador", "AC", "nominal", 131, 90),)


def _stored() -> tuple[StoredSeatVotes, ...]:
    votos = {"deputadoFederal": _FEDERAL, "senador": _SENADO}
    return tuple(StoredSeatVotes(cargo, votos.get(cargo, ()), _MOMENT) for cargo in CARGOS_GRAVADOS)


def test_cadeiras_json_has_houses_federations_and_the_party_contract() -> None:
    response = _get(_app(_stored()), "/relatorios/dados/cadeiras?ano=2026&turno=1")
    assert response.status_code == 200
    body = response.json()
    assert body["estimativa"] is True
    assert body["gerado_em"] == "2026-10-22T00:00:00+00:00"
    camara = body["casas"][0]
    assert (camara["casa"], camara["vagas"], camara["vagas_simuladas"]) == ("camara", 513, 8)
    assert camara["legendas"] == [
        {"legenda": "fe-brasil", "cadeiras": 2},
        {"legenda": "22", "cadeiras": 1},
    ]
    ac = camara["ufs"][0]
    assert (ac["uf"], ac["quociente_eleitoral"], ac["vagas_sem_candidato"]) == ("AC", 100, 5)
    assert ac["eleitos"][0] == {
        "numero": 2201,
        "partido": 22,
        "legenda": "22",
        "votos": 390,
        "fase": "quociente",
        "empate": False,
    }
    assert body["partidos"][0]["partido"] in {13, 22, 65}
    assert {
        "codigo": "fe-brasil",
        "sigla": "FE BRASIL",
        "nome": "Federação Brasil da Esperança",
        "federacao": True,
        "partidos": [13, 65, 43],
    } in body["legendas"]
    assert body["casas"][1]["ufs_sem_votos"][0] == "AC"
    assert len(body["notas"]) == 6


def test_senate_simulated_seats_count_the_seat_left_without_a_candidate() -> None:
    senado = _get(_app(_stored()), "/relatorios/dados/cadeiras?ano=2026&turno=1").json()["senado"]
    assert (senado["vagas"], senado["vagas_simuladas"]) == (54, 2)
    assert senado["partidos"] == [{"partido": 13, "cadeiras": 1}]


def test_cadeiras_without_every_cargo_is_409_with_the_command() -> None:
    response = _get(_app(_stored()[:2]), "/relatorios/dados/cadeiras?ano=2026&turno=1")
    assert response.status_code == 409
    assert "uv run python scripts/relatorio_cadeiras.py" in response.json()["detail"]


def test_cadeiras_for_a_year_without_registry_is_422() -> None:
    response = _get(_app(_stored()), "/relatorios/dados/cadeiras?ano=2022&turno=1")
    assert response.status_code == 422
    assert response.json()["detail"] == "Não há partidos e federações cadastrados para 2022."


def test_cadeiras_for_the_second_round_is_422() -> None:
    response = _get(_app(_stored()), "/relatorios/dados/cadeiras?ano=2026&turno=2")
    assert response.status_code == 422
    assert response.json()["detail"] == (
        "A simulação de cadeiras usa só os votos do 1º turno; o turno 2 não se aplica."
    )


def test_ports_without_a_seat_store_hide_the_internal_error() -> None:
    response = _get(create_app(ports=_ports()), "/relatorios/dados/cadeiras?ano=2026&turno=1")
    assert response.status_code == 500
    assert response.json()["detail"] == "Não foi possível consultar os dados."
