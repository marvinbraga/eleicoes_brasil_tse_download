"""Party columns follow votos, never a sum of comparecimento."""

from fractions import Fraction

import pytest

from eleicoes.domain.boletim_consulta import PoderPartido
from eleicoes.domain.errors import InvalidBoletimConsultaError
from eleicoes.domain.grade import LugarVotos
from eleicoes.use_cases.grade import BuildPartyShareGrid


def test_columns_follow_total_votes_and_missing_parties_are_zero() -> None:
    places = (
        LugarVotos("A", "Alfa", (PoderPartido(1, None, 1, 1, 0, 1000),)),
        LugarVotos("B", "Beta", (PoderPartido(2, None, 2, 40, 10, 10),)),
    )
    grade = BuildPartyShareGrid().execute(2026, 1, "ac", "presidente", "municipio", places)
    assert grade.colunas == (2, 1)
    assert grade.uf == "AC"
    alfa, beta = grade.linhas
    assert (alfa.codigo, beta.codigo) == ("A", "B")
    assert alfa.celulas[0].partido == 2
    assert alfa.celulas[0].votos == 0
    assert alfa.celulas[0].fatia == Fraction(0)
    assert alfa.celulas[1].votos == 1
    assert beta.celulas[1].votos == 0
    assert beta.celulas[0].fatia == Fraction(50, 10)
    assert alfa.comparecimento == 1000
    assert beta.comparecimento == 10


def test_rows_are_ordered_by_name_then_code() -> None:
    places = (
        LugarVotos("2", "Rio", (PoderPartido(2, None, 13, 1, 0, 5),)),
        LugarVotos("A", "Zeta", (PoderPartido(9, None, 13, 1, 0, 5),)),
        LugarVotos("1", "Rio", (PoderPartido(1, None, 13, 1, 0, 5),)),
        LugarVotos("B", "alfa", (PoderPartido(8, None, 13, 4, 0, 5),)),
    )
    grade = BuildPartyShareGrid().execute(2026, 1, "AC", "presidente", "uf", places)
    assert [(row.nome, row.codigo) for row in grade.linhas] == [
        ("alfa", "B"),
        ("Rio", "1"),
        ("Rio", "2"),
        ("Zeta", "A"),
    ]


def test_empty_places_yield_an_empty_grade() -> None:
    grade = BuildPartyShareGrid().execute(2026, 1, "AC", "presidente", "pais", ())
    assert grade.linhas == ()
    assert grade.colunas == ()
    assert grade.nivel == "pais"


def test_duplicate_party_in_one_place_is_rejected() -> None:
    place = LugarVotos(
        "1",
        "A",
        (
            PoderPartido(1, None, 13, 1, 0, 10),
            PoderPartido(1, None, 13, 2, 0, 10),
        ),
    )
    with pytest.raises(InvalidBoletimConsultaError):
        BuildPartyShareGrid().execute(2026, 1, "AC", "presidente", "municipio", (place,))
