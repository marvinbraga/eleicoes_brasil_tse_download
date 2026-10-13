"""Stored grade cells rebuild the grid; the anchor UF is not part of the cells."""

from typing import cast

import pytest

from eleicoes.domain.boletim_consulta import PoderPartido
from eleicoes.domain.errors import (
    InvalidBoletimConsultaError,
    InvalidNivelError,
    InvalidStoredReportError,
)
from eleicoes.domain.grade import LugarVotos
from eleicoes.domain.stored_grade import StoredCell, cells_from_grades, grades_from_cells
from eleicoes.use_cases.grade import BuildPartyShareGrid


def test_cells_round_trip_keeps_zeros_and_replaces_only_the_anchor() -> None:
    original = BuildPartyShareGrid().execute(
        2026,
        1,
        "AC",
        "deputadoFederal",
        "municipio",
        _places(),
    )
    cells = cells_from_grades((original,))
    assert _identity(cells) == {
        ("municipio", "2710", "BELEM", 50, 15, 3, 0),
        ("municipio", "2710", "BELEM", 50, 13, 0, 0),
        ("municipio", "1392", "RIO BRANCO", 80, 15, 10, 1),
        ("municipio", "1392", "RIO BRANCO", 80, 13, 0, 0),
    }
    rebuilt = grades_from_cells(2026, 1, "PA", original.cargo, cells)
    assert original.uf == "AC"
    assert rebuilt[0].uf == "PA"
    assert rebuilt[0].linhas == original.linhas
    assert rebuilt[0].colunas == original.colunas
    assert all(grade.linhas == () and grade.colunas == () for grade in rebuilt[1:])


def test_empty_cells_become_four_empty_grades() -> None:
    grades = grades_from_cells(2026, 1, "rj", "presidente", ())
    assert tuple(grade.uf for grade in grades) == ("RJ",) * 4
    assert tuple(grade.nivel for grade in grades) == ("municipio", "uf", "regiao", "pais")
    assert all(grade.colunas == () and grade.linhas == () for grade in grades)


def test_columns_follow_votes_and_rows_follow_the_place_name() -> None:
    cells = (
        StoredCell("municipio", "2", "Zeta", 10, 22, 1, 0),
        StoredCell("municipio", "1", "alfa", 30, 13, 9, 0),
        StoredCell("municipio", "1", "alfa", 30, 22, 0, 0),
        StoredCell("municipio", "2", "Zeta", 10, 13, 0, 0),
    )
    grade = grades_from_cells(2026, 1, "AC", "presidente", cells)[0]
    assert grade.colunas == (13, 22)
    assert [line.nome for line in grade.linhas] == ["alfa", "Zeta"]
    assert grade.linhas[0].celulas[1].votos_nominais == 0
    assert grade.linhas[1].celulas[0].votos_nominais == 0


def test_the_same_code_on_two_levels_stays_two_grades() -> None:
    cells = (
        StoredCell("municipio", "AC", "ACRE", 10, 15, 1, 0),
        StoredCell("uf", "AC", "Acre", 10, 15, 4, 0),
    )
    grades = grades_from_cells(2026, 1, "PA", "presidente", cells)
    assert [line.nome for line in grades[0].linhas] == ["ACRE"]
    assert [line.nome for line in grades[1].linhas] == ["Acre"]
    assert grades[2].linhas == ()
    assert grades[3].linhas == ()


def test_disagreement_inside_one_place_is_rejected() -> None:
    turnout = (
        StoredCell("municipio", "1", "ALFA", 10, 13, 1, 0),
        StoredCell("municipio", "1", "ALFA", 11, 15, 1, 0),
    )
    with pytest.raises(InvalidStoredReportError) as caught:
        grades_from_cells(2026, 1, "AC", "presidente", turnout)
    assert caught.value.field == "comparecimento"
    names = (
        StoredCell("municipio", "1", "ALFA", 10, 13, 1, 0),
        StoredCell("municipio", "1", "BETA", 10, 15, 1, 0),
    )
    with pytest.raises(InvalidStoredReportError) as caught:
        grades_from_cells(2026, 1, "AC", "presidente", names)
    assert caught.value.field == "nome"


def test_repeated_or_missing_parties_follow_the_grade_rule() -> None:
    repeated = (
        StoredCell("municipio", "1", "ALFA", 10, 13, 1, 0),
        StoredCell("municipio", "1", "ALFA", 10, 13, 2, 0),
    )
    with pytest.raises(InvalidBoletimConsultaError):
        grades_from_cells(2026, 1, "AC", "presidente", repeated)
    missing = (
        StoredCell("municipio", "1", "ALFA", 10, 13, 5, 0),
        StoredCell("municipio", "2", "BETA", 10, 13, 1, 0),
        StoredCell("municipio", "2", "BETA", 10, 15, 1, 0),
    )
    with pytest.raises(InvalidBoletimConsultaError):
        grades_from_cells(2026, 1, "AC", "presidente", missing)


def test_stored_cell_strips_text_and_rejects_invalid_values() -> None:
    cell = StoredCell("municipio", " 12 ", "  Alfa ", 0, 13, 0, 0)
    assert cell.codigo == "12"
    assert cell.nome == "Alfa"
    assert cell.comparecimento == 0
    assert cell.votos_nominais == 0
    with pytest.raises(InvalidBoletimConsultaError):
        StoredCell("municipio", " ", "Alfa", 1, 13, 0, 0)
    with pytest.raises(InvalidBoletimConsultaError):
        StoredCell("municipio", "1", "  ", 1, 13, 0, 0)
    with pytest.raises(InvalidNivelError):
        StoredCell("zona", "1", "Alfa", 1, 13, 0, 0)
    with pytest.raises(InvalidBoletimConsultaError):
        StoredCell("municipio", "1", "Alfa", 1, 13, -1, 0)
    with pytest.raises(InvalidBoletimConsultaError):
        StoredCell("municipio", cast(str, None), "Alfa", 1, 13, 0, 0)
    with pytest.raises(InvalidBoletimConsultaError):
        StoredCell("municipio", "1", "Alfa", 1, 13, cast(int, True), 0)


def _places() -> tuple[LugarVotos, ...]:
    return (
        LugarVotos(
            "2710",
            "BELEM",
            (
                PoderPartido(2710, None, 15, 3, 0, 50),
                PoderPartido(2710, None, 13, 0, 0, 50),
            ),
        ),
        LugarVotos(
            "1392",
            "RIO BRANCO",
            (
                PoderPartido(1392, None, 15, 10, 1, 80),
                PoderPartido(1392, None, 13, 0, 0, 80),
            ),
        ),
    )


def _identity(
    cells: tuple[StoredCell, ...],
) -> set[tuple[str, str, str, int, int, int, int]]:
    return {
        (
            cell.nivel,
            cell.codigo,
            cell.nome,
            cell.comparecimento,
            cell.partido,
            cell.votos_nominais,
            cell.votos_legenda,
        )
        for cell in cells
    }
