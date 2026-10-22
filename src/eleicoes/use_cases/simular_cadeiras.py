"""Seat estimate for the API: stored votes in, pure simulation out. Never scans boletins."""

from dataclasses import dataclass
from datetime import datetime

from eleicoes.domain.cadeiras import CARGOS_GRAVADOS, turno_simulado
from eleicoes.domain.errors import MissingSeatReportError
from eleicoes.domain.federacoes import RegistroPartidario, registro_partidario
from eleicoes.domain.simulacao_cadeiras import SimulacaoCadeiras, simular_cadeiras
from eleicoes.domain.values import ElectionYear
from eleicoes.ports.relatorio_cadeiras import AsyncSeatVoteStore


@dataclass(frozen=True, slots=True)
class SimulacaoGravada:
    simulacao: SimulacaoCadeiras
    gerado_em: datetime


async def stored_simulation(
    store: AsyncSeatVoteStore,
    ano: int,
    turno: int,
    registro: RegistroPartidario | None = None,
) -> SimulacaoGravada:
    year = ElectionYear(ano).value
    turn = turno_simulado(turno)
    rules = registro if registro is not None else registro_partidario(year)
    stored = await store.load(year, turn)
    found = {item.cargo for item in stored}
    missing = tuple(cargo for cargo in CARGOS_GRAVADOS if cargo not in found)
    if missing:
        raise MissingSeatReportError(missing)
    votos = tuple(voto for item in stored for voto in item.votos)
    oldest = min(item.gerado_em for item in stored)
    return SimulacaoGravada(simular_cadeiras(year, turn, votos, rules), oldest)
