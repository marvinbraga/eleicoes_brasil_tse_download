"""Within-state coherence: offsets between states never count, absences never become zero."""

from fractions import Fraction

import numpy
import pytest
from tests.domain.test_verticalizacao import city_lines, every_cargo, uf_lines

from eleicoes.domain.verticalizacao import (
    DEPUTADO_ESTADUAL,
    DEPUTADO_FEDERAL,
    GOVERNADOR,
    VerticalLine,
    vertical_base,
)
from eleicoes.domain.verticalizacao_coerencia import (
    MINIMO_MUNICIPIOS,
    PARES_COERENCIA,
    coherence,
    scatter_points,
)

_X = DEPUTADO_FEDERAL
_Y = GOVERNADOR
_PT = 13
_REST = 99


def _city(
    uf: str, index: int, x: int, y: int, comparecimento: int = 1000
) -> tuple[VerticalLine, ...]:
    codigo = f"{uf}{index}"
    nome = f"CIDADE {index} ({uf})"
    return (
        *city_lines(_X, codigo, nome, comparecimento, {_PT: x, _REST: 100 - x}),
        *city_lines(_Y, codigo, nome, comparecimento, {_PT: y, _REST: 100 - y}),
    )


def _cities(
    uf: str, pairs: list[tuple[int, int]], weights: list[int] | None = None
) -> tuple[VerticalLine, ...]:
    sizes = weights or [1000] * len(pairs)
    return tuple(
        line
        for index, ((x, y), w) in enumerate(zip(pairs, sizes, strict=True))
        for line in _city(uf, index, x, y, w)
    )


def test_pairs_follow_d8_with_the_reference_last() -> None:
    assert PARES_COERENCIA == (
        (DEPUTADO_FEDERAL, "presidente"),
        (DEPUTADO_ESTADUAL, "presidente"),
        (DEPUTADO_FEDERAL, GOVERNADOR),
        (DEPUTADO_ESTADUAL, GOVERNADOR),
        (DEPUTADO_FEDERAL, "senador"),
        (DEPUTADO_ESTADUAL, "senador"),
        (DEPUTADO_FEDERAL, DEPUTADO_ESTADUAL),
    )
    assert MINIMO_MUNICIPIOS == 10


def test_offsets_between_states_do_not_count() -> None:
    xs = [5, 10, 15, 20, 25]
    sp = [(x, 2 * x) for x in xs]
    mg = [(x, 2 * x + 30) for x in xs]
    lines = (*every_cargo("SP"), *every_cargo("MG"), *_cities("SP", sp), *_cities("MG", mg))
    base = vertical_base(2026, 1, lines)
    result = coherence(base, base.scope(None), _PT, _X, _Y)
    assert result.r == pytest.approx(1.0)
    assert result.municipios == 10
    pooled = numpy.corrcoef([x for x, _ in sp + mg], [y for _, y in sp + mg])[0, 1]
    assert pooled < 0.9


def test_inverse_relation_is_minus_one() -> None:
    pairs = [(x, 60 - x) for x in range(5, 55, 5)]
    base = vertical_base(2026, 1, (*every_cargo("SP"), *_cities("SP", pairs)))
    assert coherence(base, ("SP",), _PT, _X, _Y).r == pytest.approx(-1.0)


def _reference(groups: list[tuple[list[float], list[float], list[float]]]) -> float:
    dxs: list[float] = []
    dys: list[float] = []
    ws: list[float] = []
    for xs, ys, weights in groups:
        mx = numpy.average(xs, weights=weights)
        my = numpy.average(ys, weights=weights)
        dxs.extend(x - mx for x in xs)
        dys.extend(y - my for y in ys)
        ws.extend(weights)
    matrix = numpy.cov(dxs, dys, aweights=ws)
    return float(matrix[0, 1] / numpy.sqrt(matrix[0, 0] * matrix[1, 1]))


def test_weights_follow_turnout_within_each_state() -> None:
    sp = [(12, 30), (40, 41), (7, 20), (22, 18), (35, 60), (18, 25)]
    mg = [(3, 9), (50, 30), (28, 33), (9, 14), (44, 70), (15, 11)]
    w_sp = [100, 9000, 400, 2500, 700, 1200]
    w_mg = [5000, 300, 800, 4100, 150, 2600]
    lines = (
        *every_cargo("SP"),
        *every_cargo("MG"),
        *_cities("SP", sp, w_sp),
        *_cities("MG", mg, w_mg),
    )
    base = vertical_base(2026, 1, lines)
    result = coherence(base, base.scope(None), _PT, _X, _Y)
    expected = _reference(
        [
            ([x / 100 for x, _ in sp], [y / 100 for _, y in sp], [float(w) for w in w_sp]),
            ([x / 100 for x, _ in mg], [y / 100 for _, y in mg], [float(w) for w in w_mg]),
        ]
    )
    assert result.r == pytest.approx(expected)
    assert result.municipios == 12
    unweighted = coherence(
        vertical_base(
            2026,
            1,
            (*every_cargo("SP"), *every_cargo("MG"), *_cities("SP", sp), *_cities("MG", mg)),
        ),
        ("MG", "SP"),
        _PT,
        _X,
        _Y,
    )
    assert unweighted.r != pytest.approx(expected)


def test_small_sample_is_blank_not_zero() -> None:
    pairs = [(x, 2 * x) for x in range(1, 10)]
    base = vertical_base(2026, 1, (*every_cargo("SP"), *_cities("SP", pairs)))
    result = coherence(base, ("SP",), _PT, _X, _Y)
    assert result.r is None
    assert result.municipios == 9


def test_single_city_state_is_out_of_n_but_in_the_scatter() -> None:
    pairs = [(x, x + 3) for x in range(1, 11)]
    lines = (
        *every_cargo("SP"),
        *every_cargo("DF"),
        *_cities("SP", pairs),
        *_city("DF", 0, 30, 40),
    )
    base = vertical_base(2026, 1, lines)
    result = coherence(base, base.scope(None), _PT, _X, _Y)
    assert result.municipios == 10
    assert result.r == pytest.approx(1.0)
    points = scatter_points(base, base.scope(None), _PT, _X, _Y)
    assert len(points) == 11
    [df] = [point for point in points if point.uf == "DF"]
    assert (df.x, df.y, df.comparecimento) == (Fraction(30, 100), Fraction(40, 100), 1000)
    alone = coherence(base, ("DF",), _PT, _X, _Y)
    assert (alone.r, alone.municipios) == (None, 0)
    assert len(scatter_points(base, ("DF",), _PT, _X, _Y)) == 1


def test_state_where_the_party_did_not_run_is_left_out() -> None:
    sp = [(x, 2 * x) for x in range(1, 11)]
    mg = [(x, 90 - x) for x in range(1, 11)]
    lines = (
        *every_cargo("SP"),
        *every_cargo("MG", skip=(GOVERNADOR,)),
        *uf_lines(GOVERNADOR, "MG", {_REST: 500}),
        *_cities("SP", sp),
        *_cities("MG", mg),
    )
    base = vertical_base(2026, 1, lines)
    assert base.concorreu("MG", GOVERNADOR, _PT) is False
    result = coherence(base, base.scope(None), _PT, _X, _Y)
    assert result.municipios == 10
    assert result.r == pytest.approx(1.0)
    points = scatter_points(base, base.scope(None), _PT, _X, _Y)
    assert {point.uf for point in points} == {"SP"}


def test_zero_variance_is_blank() -> None:
    pairs = [(10, y) for y in range(1, 13)]
    base = vertical_base(2026, 1, (*every_cargo("SP"), *_cities("SP", pairs)))
    result = coherence(base, ("SP",), _PT, _X, _Y)
    assert result.r is None
    assert result.municipios == 12


def test_state_without_the_cargo_stays_out_of_the_pair() -> None:
    sp = [(x, 2 * x) for x in range(1, 11)]
    estadual = tuple(
        line
        for index, (x, _) in enumerate(sp)
        for line in city_lines(
            DEPUTADO_ESTADUAL, f"SP{index}", f"CIDADE {index} (SP)", 1000, {_PT: x, _REST: 100 - x}
        )
    )
    lines = (
        *every_cargo("SP"),
        *every_cargo("DF", skip=(DEPUTADO_ESTADUAL,)),
        *_cities("SP", sp),
        *estadual,
        *_city("DF", 0, 30, 40),
    )
    base = vertical_base(2026, 1, lines)
    result = coherence(base, base.scope(None), _PT, DEPUTADO_ESTADUAL, GOVERNADOR)
    assert result.municipios == 10
    points = scatter_points(base, base.scope(None), _PT, DEPUTADO_ESTADUAL, GOVERNADOR)
    assert {point.uf for point in points} == {"SP"}
