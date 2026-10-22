"""Strength scoreboard from the stored power cells. Reads only the levels it needs.

The optional seat port (plano 2) adds federations and seats; it is asked only where the
simulation applies (first round, a year with a party registry), so None from it means the
simulation was not stored. Its other errors are not swallowed. The optional 2024 port
(plano 6) adds mayors, governed electorate and councillors, in 2026 party numbers, so only
for a year with a party registry. The power and seat reads run one after another because
they share one session per request; the 2024 port borrows its own pooled connection.
"""

import asyncio

from eleicoes.domain.cadeiras import TURNO_SIMULADO
from eleicoes.domain.errors import MissingStrengthSourcesError
from eleicoes.domain.federacoes import REGISTROS
from eleicoes.domain.forca import (
    BaseCadeiras,
    BaseMunicipal2024,
    Cadeiras,
    FederacaoForca,
    FontesForca,
    Municipal2024Forca,
    PlacarForca,
    placar_com_federacoes,
    require_cargo_referencia,
)
from eleicoes.domain.forca_blocos import (
    com_cadeiras,
    com_municipal_2024,
    sem_cadeiras,
    sem_municipal_2024,
)
from eleicoes.domain.stored_grade import StoredCell
from eleicoes.domain.values import ElectionYear, Turno
from eleicoes.ports.cadeiras import AsyncEstimativaCadeiras, EstimativaCadeiras
from eleicoes.ports.municipal_2024 import AsyncMunicipal2024, Municipal2024
from eleicoes.ports.relatorio_poder import AsyncRelatorioPoderStore

_BASE: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("presidente", ("pais", "uf")),
    ("deputadoFederal", ("pais", "uf")),
    ("deputadoEstadual", ("uf",)),
)
_MUNICIPIO = "municipio"
Cells = tuple[StoredCell, ...] | None


class MontarPlacarForca:
    def __init__(
        self,
        store: AsyncRelatorioPoderStore,
        cadeiras: AsyncEstimativaCadeiras | None = None,
        municipal_2024: AsyncMunicipal2024 | None = None,
    ) -> None:
        self._store = store
        self._cadeiras = cadeiras
        self._municipal_2024 = municipal_2024

    async def execute(self, ano: int, turno: int, cargo_referencia: str) -> PlacarForca:
        year = ElectionYear(ano).value
        turn = Turno(turno).value
        referencia = require_cargo_referencia(cargo_referencia)
        loaded: dict[str, Cells] = {}
        for cargo, niveis in _plano(referencia):
            loaded[cargo] = await self._cells(year, turn, cargo, niveis)
        if all(cells is None for cells in loaded.values()):
            raise MissingStrengthSourcesError(tuple(loaded))
        fontes = FontesForca(
            loaded["presidente"],
            loaded["deputadoFederal"],
            loaded["deputadoEstadual"],
            loaded[referencia],
        )
        cadeiras = self._cadeiras if _simula(year, turn) else None
        estimativa = None if cadeiras is None else await cadeiras.load(year, turn)
        municipal = self._municipal_2024 if year in REGISTROS else None
        de_2024 = None if municipal is None else await municipal.load()
        federacoes = _federacoes(estimativa)
        placar = await asyncio.to_thread(
            placar_com_federacoes, year, turn, referencia, fontes, federacoes
        )
        # 2024 first: it may add rows (parties without 2026 votes in a cut) that need seats.
        if municipal is not None:
            placar = _com_2024(placar, de_2024, federacoes)
        if cadeiras is not None:
            placar = _com_estimativa(placar, estimativa)
        return placar

    async def _cells(self, ano: int, turno: int, cargo: str, niveis: tuple[str, ...]) -> Cells:
        report = await self._store.load_levels(ano, turno, cargo, niveis)
        if report is None or not report.cells:
            return None
        return report.cells


def _plano(referencia: str) -> tuple[tuple[str, tuple[str, ...]], ...]:
    plano = tuple((cargo, _niveis(cargo, niveis, referencia)) for cargo, niveis in _BASE)
    if any(cargo == referencia for cargo, _base in _BASE):
        return plano
    return (*plano, (referencia, (_MUNICIPIO,)))


def _niveis(cargo: str, niveis: tuple[str, ...], referencia: str) -> tuple[str, ...]:
    return (*niveis, _MUNICIPIO) if cargo == referencia else niveis


def _federacoes(estimativa: EstimativaCadeiras | None) -> tuple[FederacaoForca, ...]:
    if estimativa is None:
        return ()
    # The port's sigla holds the federation code ("fe-brasil"), the key in "fed:<codigo>".
    return tuple(
        FederacaoForca(codigo=item.sigla, nome=item.nome, partidos=item.partidos)
        for item in estimativa.federacoes
    )


def _simula(ano: int, turno: int) -> bool:
    return turno == TURNO_SIMULADO and ano in REGISTROS


def _com_estimativa(placar: PlacarForca, estimativa: EstimativaCadeiras | None) -> PlacarForca:
    if estimativa is None:
        return sem_cadeiras(placar)
    linhas = {
        (linha.chave, linha.uf): Cadeiras(
            camara=linha.camara,
            senado=linha.senado,
            governador_1t=linha.governador_1t,
            governador_2t=linha.governador_2t,
            assembleia=linha.assembleia,
        )
        for linha in estimativa.linhas
    }
    totais = estimativa.totais
    base = BaseCadeiras(totais.camara, totais.senado, totais.governadores, totais.assembleias)
    return com_cadeiras(placar, linhas, base)


def _com_2024(
    placar: PlacarForca,
    dados: Municipal2024 | None,
    federacoes: tuple[FederacaoForca, ...],
) -> PlacarForca:
    if dados is None:
        return sem_municipal_2024(placar)
    linhas = {
        (linha.partido, linha.uf): Municipal2024Forca(
            prefeitos=linha.prefeitos,
            eleitorado_governado=linha.eleitorado_governado,
            vereadores=linha.vereadores,
        )
        for linha in dados.linhas
    }
    totais = {
        item.uf: BaseMunicipal2024(
            municipios=item.municipios,
            com_prefeito=item.com_prefeito,
            eleitorado=item.eleitorado,
            vereadores=item.vereadores,
        )
        for item in dados.totais
    }
    return com_municipal_2024(placar, linhas, totais, dados.data_corte, federacoes=federacoes)
