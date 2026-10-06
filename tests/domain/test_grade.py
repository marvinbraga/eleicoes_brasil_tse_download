"""Always-valid party-share records."""

from fractions import Fraction

import pytest

from eleicoes.domain.boletim_consulta import PoderPartido
from eleicoes.domain.errors import InvalidBoletimConsultaError, InvalidNivelError
from eleicoes.domain.grade import CelulaGrade, GradeDePoder, LinhaGrade, LugarVotos


def test_lugar_rejects_empty_lines_and_conflicting_comparecimento() -> None:
    with pytest.raises(InvalidBoletimConsultaError):
        LugarVotos("1", "A", ())
    with pytest.raises(InvalidBoletimConsultaError):
        LugarVotos(
            "1",
            "A",
            (
                PoderPartido(1, None, 13, 1, 0, 10),
                PoderPartido(1, None, 22, 1, 0, 11),
            ),
        )


def test_fatia_is_votes_over_turnout_and_zero_when_turnout_is_zero() -> None:
    cell = CelulaGrade(22, 42407, 308, 215223)
    assert cell.votos == 42715
    assert cell.fatia == Fraction(42715, 215223)
    assert CelulaGrade(13, 0, 0, 0).fatia == Fraction(0)


def test_line_rejects_a_cell_with_a_different_comparecimento() -> None:
    with pytest.raises(InvalidBoletimConsultaError):
        LinhaGrade("1", "A", 10, (CelulaGrade(13, 1, 0, 11),))


def test_grade_rejects_zona_and_columns_that_ignore_vote_totals() -> None:
    with pytest.raises(InvalidNivelError):
        GradeDePoder(2026, 1, "AC", "presidente", "zona", (), ())
    row = LinhaGrade(
        "1",
        "Alfa",
        1000,
        (CelulaGrade(1, 1, 0, 1000), CelulaGrade(2, 50, 0, 1000)),
    )
    with pytest.raises(InvalidBoletimConsultaError):
        GradeDePoder(2026, 1, "AC", "presidente", "municipio", (1, 2), (row,))


def test_grade_rejects_rows_that_are_not_ordered_by_name() -> None:
    first = LinhaGrade("A", "Zeta", 10, (CelulaGrade(1, 1, 0, 10),))
    second = LinhaGrade("B", "alfa", 10, (CelulaGrade(1, 1, 0, 10),))
    with pytest.raises(InvalidBoletimConsultaError):
        GradeDePoder(2026, 1, "AC", "presidente", "uf", (1,), (first, second))
