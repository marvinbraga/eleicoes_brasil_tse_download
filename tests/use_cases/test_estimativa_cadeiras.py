"""The scoreboard port: rows per party and federation, per UF and for Brazil."""

import asyncio
from datetime import UTC, datetime

from eleicoes.domain.cadeiras import CARGOS_GRAVADOS
from eleicoes.domain.simulacao_cadeiras import VotoApurado
from eleicoes.ports.cadeiras import CadeirasUnidade, TotaisCadeiras
from eleicoes.ports.relatorio_cadeiras import StoredSeatVotes
from eleicoes.use_cases.estimativa_cadeiras import StoredSeatEstimates

_MOMENT = datetime(2026, 10, 22, tzinfo=UTC)
_VOTOS = {
    "deputadoFederal": (
        VotoApurado("deputadoFederal", "AC", "nominal", 1301, 250),
        VotoApurado("deputadoFederal", "AC", "nominal", 6501, 150),
        VotoApurado("deputadoFederal", "AC", "nominal", 2201, 390),
    ),
    "senador": (
        VotoApurado("senador", "AC", "nominal", 222, 300),
        VotoApurado("senador", "AC", "nominal", 131, 200),
        VotoApurado("senador", "AC", "nominal", 100, 100),
    ),
    "governador": (
        VotoApurado("governador", "AC", "nominal", 13, 600),
        VotoApurado("governador", "AC", "nominal", 22, 400),
        VotoApurado("governador", "SE", "nominal", 22, 45),
        VotoApurado("governador", "SE", "nominal", 65, 35),
        VotoApurado("governador", "SE", "nominal", 15, 20),
    ),
}


class _Store:
    def __init__(self, cargos: tuple[str, ...]) -> None:
        self.cargos = cargos

    async def load(self, _ano: int, _turno: int) -> tuple[StoredSeatVotes, ...]:
        return tuple(StoredSeatVotes(c, _VOTOS.get(c, ()), _MOMENT) for c in self.cargos)


def test_rows_cover_parties_federations_ufs_and_brazil() -> None:
    found = asyncio.run(StoredSeatEstimates(_Store(CARGOS_GRAVADOS)).load(2026, 1))
    assert found is not None
    assert found.gerado_em == _MOMENT
    assert found.totais == TotaisCadeiras(camara=8, senado=2, governadores=2, assembleias=0)
    assert [f.sigla for f in found.federacoes][0] == "fe-brasil"
    rows = {(row.chave, row.uf): row for row in found.linhas}
    assert rows[("13", "AC")] == CadeirasUnidade("13", "AC", 1, 1, 1, 0, 0)
    assert rows[("65", "SE")].governador_2t == 1
    assert rows[("fed:fe-brasil", "AC")] == CadeirasUnidade("fed:fe-brasil", "AC", 2, 1, 1, 0, 0)
    assert rows[("fed:fe-brasil", "BR")] == CadeirasUnidade("fed:fe-brasil", "BR", 2, 1, 1, 1, 0)
    assert rows[("22", "BR")] == CadeirasUnidade("22", "BR", 1, 1, 0, 1, 0)
    assert {uf for _chave, uf in rows} == {"AC", "SE", "BR"}


def test_senate_total_is_the_seats_of_the_simulated_ufs() -> None:
    class _OneSenator(_Store):
        async def load(self, _ano: int, _turno: int) -> tuple[StoredSeatVotes, ...]:
            senado = (VotoApurado("senador", "SE", "nominal", 151, 40),)
            return tuple(
                StoredSeatVotes(c, senado if c == "senador" else (), _MOMENT) for c in self.cargos
            )

    found = asyncio.run(StoredSeatEstimates(_OneSenator(CARGOS_GRAVADOS)).load(2026, 1))
    assert found is not None
    assert found.totais.senado == 2
    assert sum(row.senado or 0 for row in found.linhas if row.chave == "15" and row.uf == "BR") == 1


def test_missing_cargo_is_none_for_the_scoreboard() -> None:
    assert asyncio.run(StoredSeatEstimates(_Store(("governador",))).load(2026, 1)) is None


def test_year_without_registry_is_none_for_the_scoreboard() -> None:
    # alinhado em 2026-10-22: o placar (plano 1) nunca recebe o 422 do registro
    assert asyncio.run(StoredSeatEstimates(_Store(CARGOS_GRAVADOS)).load(2022, 1)) is None


def test_second_round_is_none_for_the_scoreboard() -> None:
    assert asyncio.run(StoredSeatEstimates(_Store(CARGOS_GRAVADOS)).load(2026, 2)) is None
