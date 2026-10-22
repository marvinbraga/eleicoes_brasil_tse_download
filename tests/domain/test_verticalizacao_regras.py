"""Puxador / base rules. Thresholds count at the boundary."""

from fractions import Fraction

from tests.domain.test_verticalizacao import every_cargo, uf_lines

from eleicoes.domain.verticalizacao import (
    DEPUTADO_ESTADUAL,
    GOVERNADOR,
    VerticalLine,
    vertical_base,
)
from eleicoes.domain.verticalizacao_regras import (
    ALINHADO,
    BASE,
    PUXADOR,
    SEM_CANDIDATO,
    classify,
    compare,
)


def test_classify_boundaries() -> None:
    assert classify(Fraction(40, 100), Fraction(20, 100)) == PUXADOR
    assert classify(Fraction(39, 100), Fraction(20, 100)) == ALINHADO
    assert classify(Fraction(12, 100), Fraction(1, 100)) == PUXADOR
    assert classify(Fraction(8, 100), Fraction(0)) == ALINHADO
    assert classify(Fraction(10, 100), Fraction(30, 100)) == BASE
    assert classify(Fraction(10, 100), Fraction(19, 100)) == ALINHADO


def test_classify_counts_exactly_twice_and_exactly_ten_points() -> None:
    assert classify(Fraction(20, 100), Fraction(10, 100)) == PUXADOR
    assert classify(Fraction(10, 100), Fraction(20, 100)) == BASE
    assert classify(Fraction(1999, 10000), Fraction(10, 100)) == ALINHADO
    assert classify(Fraction(10, 100), Fraction(1999, 10000)) == ALINHADO
    assert classify(Fraction(30, 100), Fraction(20, 100)) == ALINHADO


_PAIR = (GOVERNADOR, DEPUTADO_ESTADUAL)


def _state(
    uf: str, governador: dict[int, int], estadual: dict[int, int]
) -> tuple[VerticalLine, ...]:
    return (
        *every_cargo(uf, skip=_PAIR),
        *uf_lines(GOVERNADOR, uf, governador),
        *uf_lines(DEPUTADO_ESTADUAL, uf, estadual),
    )


def test_compare_uses_the_running_parties_as_the_pool() -> None:
    base = vertical_base(2026, 1, _state("SP", {13: 70, 22: 30}, {13: 10, 22: 30, 45: 60}))
    ufs = base.scope(None)
    pt = compare(base, ufs, 13, *_PAIR)
    assert (pt.majoritaria, pt.esperada, pt.classe) == (
        Fraction(70, 100),
        Fraction(10, 40),
        PUXADOR,
    )
    assert pt.razao == Fraction(14, 5)
    pl = compare(base, ufs, 22, *_PAIR)
    assert (pl.majoritaria, pl.esperada, pl.classe) == (Fraction(30, 100), Fraction(30, 40), BASE)
    psdb = compare(base, ufs, 45, *_PAIR)
    assert psdb.classe == SEM_CANDIDATO and psdb.majoritaria is None
    assert [(item.uf, item.proporcional) for item in psdb.sem_candidato] == [
        ("SP", Fraction(60, 100))
    ]
    assert compare(base, ufs, 99, *_PAIR).classe is None


def test_pooled_share_weights_states_by_majoritarian_valid_votes() -> None:
    lines = (
        *_state("SP", {13: 60, 22: 40}, {13: 20, 22: 20}),
        *_state("MG", {13: 10, 15: 90}, {13: 10, 15: 30}),
    )
    base = vertical_base(2026, 1, lines)
    pt = compare(base, base.scope(None), 13, *_PAIR)
    assert pt.majoritaria == Fraction(70, 200)
    assert pt.esperada == (Fraction(1, 2) * 100 + Fraction(1, 4) * 100) / 200
    assert [(row.uf, row.classe) for row in pt.por_uf] == [("MG", BASE), ("SP", ALINHADO)]


def test_running_only_where_the_proportional_is_missing_is_not_sem_candidato() -> None:
    lines = (
        *every_cargo("DF", skip=_PAIR),
        *uf_lines(GOVERNADOR, "DF", {13: 50, 22: 50}),
        *_state("SP", {22: 100}, {13: 40, 22: 60}),
    )
    base = vertical_base(2026, 1, lines)
    pt = compare(base, base.scope(None), 13, *_PAIR)
    assert pt.classe is None
    assert [item.uf for item in pt.sem_candidato] == ["SP"]
    assert compare(base, ("SP",), 13, *_PAIR).classe == SEM_CANDIDATO


def test_state_without_the_majoritarian_is_not_sem_candidato() -> None:
    lines = (
        *_state("SP", {13: 60, 22: 40}, {13: 50, 22: 50}),
        *every_cargo("DF", skip=_PAIR),
        *uf_lines(DEPUTADO_ESTADUAL, "DF", {13: 50, 22: 50}),
    )
    base = vertical_base(2026, 1, lines)
    pt = compare(base, base.scope(None), 13, *_PAIR)
    assert pt.sem_candidato == ()
    assert [row.uf for row in pt.por_uf] == ["SP"]
