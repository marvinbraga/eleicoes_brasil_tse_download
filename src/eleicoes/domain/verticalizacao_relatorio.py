"""Vertical report: per-party shares, coherence, comparisons and the requested scatter."""

import statistics
from dataclasses import dataclass
from typing import Final

from eleicoes.domain.errors import EmptyStoredCellsError, InvalidCargoError, InvalidNumeroError
from eleicoes.domain.verticalizacao import (
    CARGOS,
    DEPUTADO_ESTADUAL,
    DEPUTADO_FEDERAL,
    MAX_PARTIDO,
    CargoShare,
    VerticalBase,
    cargo_share,
)
from eleicoes.domain.verticalizacao_coerencia import (
    PARES_COERENCIA,
    Coherence,
    ScatterPoint,
    coherence,
    scatter_points,
)
from eleicoes.domain.verticalizacao_regras import (
    ALINHADO,
    BASE,
    PARES_CANONICOS,
    PUXADOR,
    Comparison,
    compare,
)

PERFIL_MISTO: Final = "misto"
SEM_COMPARACAO: Final = "sem_comparacao"
_CROSS_PAIRS: Final = len(PARES_COERENCIA) - 1
_COMPARABLE: Final = frozenset({PUXADOR, BASE, ALINHADO})
NOTES: Final[tuple[str, ...]] = (
    "Lê só as células gravadas do relatório de poder; não lê os boletins.",
    "Votos válidos são os nominais mais os de legenda. Brancos e nulos não entram.",
    "Um partido concorreu a um cargo numa UF quando teve votos nesse cargo na UF. "
    "Onde não concorreu, a fatia não vale zero: aquela UF fica fora das contas do cargo "
    "para esse partido.",
    "O exterior só vota para presidente e fica fora de todas as comparações.",
    "Em 2026 cada eleitor tem dois votos para senador. A fatia de senador divide pelos "
    "votos dados, por isso um candidato raramente passa de 50%.",
    "A coerência é a correlação de Pearson dentro de cada UF, ponderada pelo comparecimento "
    "do município. Com menos de 10 municípios, fica em branco.",
    "O esperado é a fatia que o partido teria na majoritária se os votos seguissem a força "
    "dele na proporcional, entre os partidos que lançaram candidato.",
    "O Distrito Federal não tem deputado estadual gravado. Por isso fica fora do par "
    "governador e deputado estadual e da coerência com deputado estadual.",
)


@dataclass(frozen=True, slots=True)
class PartyVertical:
    partido: int
    cargos: tuple[CargoShare, ...]
    coerencia: tuple[Coherence, ...]
    comparacoes: tuple[Comparison, ...]

    @property
    def perfil(self) -> str:
        return profile(self.comparacoes)

    @property
    def coerencia_mediana(self) -> float | None:
        values = [item.r for item in self.coerencia[:_CROSS_PAIRS] if item.r is not None]
        if not values:
            return None
        return statistics.median(values)


@dataclass(frozen=True, slots=True)
class VerticalReport:
    ano: int
    turno: int
    uf: str | None
    municipios: int
    sem_uf: int
    partidos: tuple[PartyVertical, ...]


@dataclass(frozen=True, slots=True)
class ScatterView:
    partido: int
    cargo_x: str
    cargo_y: str
    coerencia: Coherence
    pontos: tuple[ScatterPoint, ...]


@dataclass(frozen=True, slots=True)
class VerticalView:
    report: VerticalReport
    dispersao: ScatterView


def profile(comparisons: tuple[Comparison, ...]) -> str:
    classes = {item.classe for item in comparisons if item.classe in _COMPARABLE}
    if not classes:
        return SEM_COMPARACAO
    if PUXADOR in classes and BASE in classes:
        return PERFIL_MISTO
    if PUXADOR in classes:
        return PUXADOR
    if BASE in classes:
        return BASE
    return ALINHADO


def vertical_report(base: VerticalBase, uf: str | None) -> VerticalReport:
    ufs = base.scope(uf)
    parties = tuple(_party(base, ufs, partido) for partido in _parties(base, ufs))
    ordered = tuple(sorted(parties, key=_order))
    municipios = sum(len(base.municipios.get(code, ())) for code in ufs)
    scope = None if uf is None else ufs[0]
    return VerticalReport(base.ano, base.turno, scope, municipios, base.sem_uf, ordered)


def scatter_view(
    base: VerticalBase,
    report: VerticalReport,
    partido: int | None,
    cargo_x: str,
    cargo_y: str,
) -> ScatterView:
    require_scatter(partido, cargo_x, cargo_y)
    chosen = _chosen_party(report, partido)
    ufs = base.scope(report.uf)
    return ScatterView(
        chosen,
        cargo_x,
        cargo_y,
        coherence(base, ufs, chosen, cargo_x, cargo_y),
        scatter_points(base, ufs, chosen, cargo_x, cargo_y),
    )


def _parties(base: VerticalBase, ufs: tuple[str, ...]) -> set[int]:
    return {
        partido
        for uf in ufs
        for cargo in CARGOS
        for partido, votos in base.votos_uf(uf, cargo).items()
        if votos > 0
    }


def _party(base: VerticalBase, ufs: tuple[str, ...], partido: int) -> PartyVertical:
    return PartyVertical(
        partido,
        tuple(cargo_share(base, ufs, cargo, partido) for cargo in CARGOS),
        tuple(coherence(base, ufs, partido, x, y) for x, y in PARES_COERENCIA),
        tuple(compare(base, ufs, partido, maj, prop) for maj, prop in PARES_CANONICOS),
    )


def _order(party: PartyVertical) -> tuple[int, int, int, int]:
    votes = {share.cargo: share.votos for share in party.cargos}
    return (
        -votes[DEPUTADO_FEDERAL],
        -votes[DEPUTADO_ESTADUAL],
        -sum(votes.values()),
        party.partido,
    )


def require_scatter(partido: int | None, cargo_x: str, cargo_y: str) -> None:
    if cargo_x not in CARGOS:
        raise InvalidCargoError(cargo_x)
    if cargo_y not in CARGOS or cargo_y == cargo_x:
        raise InvalidCargoError(cargo_y)
    if partido is None:
        return
    if isinstance(partido, bool) or not isinstance(partido, int):
        raise InvalidNumeroError(partido)
    if not 0 <= partido <= MAX_PARTIDO:
        raise InvalidNumeroError(partido)


def _chosen_party(report: VerticalReport, partido: int | None) -> int:
    if partido is not None:
        return partido
    if not report.partidos:
        raise EmptyStoredCellsError()
    return report.partidos[0].partido
