"""Puxador / base: the majoritarian share against what the proportional base predicts."""

from dataclasses import dataclass
from fractions import Fraction
from typing import Final

from eleicoes.domain.verticalizacao import (
    DEPUTADO_ESTADUAL,
    DEPUTADO_FEDERAL,
    GOVERNADOR,
    PRESIDENTE,
    SENADOR,
    VerticalBase,
)

RAZAO: Final = 2
DIFERENCA: Final = Fraction(1, 10)
BASE_RELEVANTE: Final = Fraction(1, 20)
PUXADOR: Final = "puxador"
BASE: Final = "base"
ALINHADO: Final = "alinhado"
SEM_CANDIDATO: Final = "sem_candidato"
PARES_CANONICOS: Final[tuple[tuple[str, str], ...]] = (
    (GOVERNADOR, DEPUTADO_ESTADUAL),
    (SENADOR, DEPUTADO_FEDERAL),
    (PRESIDENTE, DEPUTADO_FEDERAL),
)


@dataclass(frozen=True, slots=True)
class UfComparison:
    uf: str
    majoritaria: Fraction
    esperada: Fraction
    classe: str


@dataclass(frozen=True, slots=True)
class AbsentState:
    uf: str
    proporcional: Fraction


@dataclass(frozen=True, slots=True)
class Comparison:
    majoritario: str
    proporcional: str
    majoritaria: Fraction | None
    esperada: Fraction | None
    classe: str | None
    por_uf: tuple[UfComparison, ...]
    sem_candidato: tuple[AbsentState, ...]

    @property
    def razao(self) -> Fraction | None:
        if self.majoritaria is None or self.esperada is None or self.esperada == 0:
            return None
        return self.majoritaria / self.esperada


def classify(majoritaria: Fraction, esperada: Fraction) -> str:
    if majoritaria >= RAZAO * esperada and majoritaria - esperada >= DIFERENCA:
        return PUXADOR
    if esperada >= RAZAO * majoritaria and esperada - majoritaria >= DIFERENCA:
        return BASE
    return ALINHADO


def compare(
    base: VerticalBase,
    ufs: tuple[str, ...],
    partido: int,
    majoritario: str,
    proporcional: str,
) -> Comparison:
    rows: list[UfComparison] = []
    absent: list[AbsentState] = []
    for uf in ufs:
        row = _uf_row(base, uf, partido, majoritario, proporcional)
        if row is not None:
            rows.append(row)
            continue
        missing = _absent(base, uf, partido, majoritario, proporcional)
        if missing is not None:
            absent.append(missing)
    if not rows:
        ran = any(base.concorreu(uf, majoritario, partido) for uf in ufs)
        classe = SEM_CANDIDATO if absent and not ran else None
        return Comparison(majoritario, proporcional, None, None, classe, (), tuple(absent))
    weights = [base.validos_uf(row.uf, majoritario) for row in rows]
    total = sum(weights)
    maj = sum((row.majoritaria * w for row, w in zip(rows, weights, strict=True)), Fraction(0))
    esp = sum((row.esperada * w for row, w in zip(rows, weights, strict=True)), Fraction(0))
    majoritaria = maj / total
    esperada = esp / total
    return Comparison(
        majoritario,
        proporcional,
        majoritaria,
        esperada,
        classify(majoritaria, esperada),
        tuple(rows),
        tuple(absent),
    )


def _uf_row(
    base: VerticalBase,
    uf: str,
    partido: int,
    majoritario: str,
    proporcional: str,
) -> UfComparison | None:
    running = base.votos_uf(uf, majoritario)
    own = running.get(partido, 0)
    valid_m = sum(running.values())
    prop = base.votos_uf(uf, proporcional)
    if own == 0 or valid_m == 0 or not prop:
        return None
    pool = sum(prop.get(party, 0) for party in running)
    esperada = Fraction(0) if pool == 0 else Fraction(prop.get(partido, 0), pool)
    majoritaria = Fraction(own, valid_m)
    return UfComparison(uf, majoritaria, esperada, classify(majoritaria, esperada))


def _absent(
    base: VerticalBase,
    uf: str,
    partido: int,
    majoritario: str,
    proporcional: str,
) -> AbsentState | None:
    if base.concorreu(uf, majoritario, partido) or not base.concorreu(uf, proporcional, partido):
        return None
    valid = base.validos_uf(uf, proporcional)
    return AbsentState(uf, Fraction(base.votos_uf(uf, proporcional)[partido], valid))
