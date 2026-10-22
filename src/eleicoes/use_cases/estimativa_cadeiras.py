"""Adapts the seat simulation to the scoreboard port: one row per (chave, uf), plus BR.

A party row counts its own candidates. A federation row (chave "fed:<codigo>") sums its
members, which is exact for seats and governors because they are additive counts.
"""

from collections import Counter
from collections.abc import Iterable
from typing import Final

from eleicoes.domain.errors import (
    MissingSeatReportError,
    UnknownPartyRegistryError,
    UnsupportedSeatTurnError,
)
from eleicoes.domain.forca import chave_federacao
from eleicoes.domain.simulacao_cadeiras import CasaSimulada
from eleicoes.ports.cadeiras import (
    CadeirasUnidade,
    EstimativaCadeiras,
    Federacao,
    TotaisCadeiras,
)
from eleicoes.ports.relatorio_cadeiras import AsyncSeatVoteStore
from eleicoes.use_cases.simular_cadeiras import SimulacaoGravada, stored_simulation

PAIS: Final = "BR"
_Key = tuple[int, str]


class StoredSeatEstimates:
    """AsyncEstimativaCadeiras over the stored votes.

    Missing cargos, a year without a party registry or the second round give None, never
    409 or 422.
    """

    def __init__(self, store: AsyncSeatVoteStore) -> None:
        self._store = store

    async def load(self, ano: int, turno: int) -> EstimativaCadeiras | None:
        try:
            gravada = await stored_simulation(self._store, ano, turno)
        except (MissingSeatReportError, UnknownPartyRegistryError, UnsupportedSeatTurnError):
            return None
        return estimativa_de(gravada)


def estimativa_de(gravada: SimulacaoGravada) -> EstimativaCadeiras:
    simulacao = gravada.simulacao
    registro = simulacao.registro
    contagens = {
        "camara": _casa(simulacao.camara),
        "assembleia": _casa(simulacao.assembleias),
        "senado": _counts((e.partido, uf.uf) for uf in simulacao.senado.ufs for e in uf.eleitos),
        "governador_1t": _counts(
            (uf.eleito.partido, uf.uf) for uf in simulacao.governo.ufs if uf.eleito is not None
        ),
        "governador_2t": _counts(
            (item.partido, uf.uf) for uf in simulacao.governo.ufs for item in uf.finalistas
        ),
    }
    ufs = sorted({uf for counter in contagens.values() for _p, uf in counter})
    lugares = (*ufs, PAIS)
    linhas = [
        _linha(str(partido), (partido,), uf, contagens)
        for partido in sorted(registro.partidos)
        for uf in lugares
    ]
    linhas.extend(
        _linha(chave_federacao(federacao.codigo), federacao.partidos, uf, contagens)
        for federacao in registro.federacoes
        for uf in lugares
    )
    return EstimativaCadeiras(
        ano=simulacao.ano,
        turno=simulacao.turno,
        gerado_em=gravada.gerado_em,
        federacoes=tuple(
            Federacao(federacao.codigo, federacao.nome, federacao.partidos)
            for federacao in registro.federacoes
        ),
        totais=TotaisCadeiras(
            camara=simulacao.camara.vagas_simuladas,
            senado=simulacao.senado.vagas_simuladas,
            governadores=len(simulacao.governo.ufs),
            assembleias=simulacao.assembleias.vagas_simuladas,
        ),
        linhas=tuple(linhas),
    )


def _casa(casa: CasaSimulada) -> Counter[_Key]:
    return _counts(
        (eleito.partido, item.uf) for item in casa.ufs for eleito in item.resultado.eleitos
    )


def _counts(pairs: Iterable[_Key]) -> Counter[_Key]:
    return Counter(pairs)


def _linha(
    chave: str,
    partidos: tuple[int, ...],
    uf: str,
    contagens: dict[str, Counter[_Key]],
) -> CadeirasUnidade:
    def soma(nome: str) -> int:
        counter = contagens[nome]
        if uf == PAIS:
            return sum(n for (partido, _uf), n in counter.items() if partido in partidos)
        return sum(counter[(partido, uf)] for partido in partidos)

    return CadeirasUnidade(
        chave=chave,
        uf=uf,
        camara=soma("camara"),
        senado=soma("senado"),
        governador_1t=soma("governador_1t"),
        governador_2t=soma("governador_2t"),
        assembleia=soma("assembleia"),
    )
