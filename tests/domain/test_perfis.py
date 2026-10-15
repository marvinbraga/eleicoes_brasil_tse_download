"""Profile vectors and group order. No model and no database."""

from fractions import Fraction

import pytest

from eleicoes.domain.errors import (
    CargoSemCelulasError,
    EmptyStoredCellsError,
    FewMunicipalitiesError,
    InconsistentCellError,
    InvalidCargoError,
    InvalidGroupSpanError,
)
from eleicoes.domain.perfis import (
    GroupSpan,
    ProfileDataset,
    ProfileLine,
    ProfilePlace,
    assemble_profile,
    dataset_from_lines,
    parse_group_span,
    require_profile_cargo,
    winning_k,
)


def test_party_columns_are_ascending_and_absent_share_is_zero() -> None:
    dataset = dataset_from_lines("presidente", _lines())

    assert dataset.parties == (13, 22)
    assert dataset.places[0].codigo == "1"
    assert dataset.places[0].shares()[:2] == (0, 1)
    assert dataset.places[0].shares()[2:] == (Fraction(1, 100), Fraction(2, 100))


def test_valid_zero_comparecimento_zero_and_missing_ballot_are_dropped() -> None:
    lines = _lines() + (
        ProfileLine("9", "Vazio", 40, 13, 0, 0, 1, 1),
        ProfileLine("8", "Sem urna", 0, 13, 5, 0, 1, 1),
        ProfileLine("7", "Sem cédula", 30, 13, 5, 0, None, None),
    )

    dataset = dataset_from_lines("presidente", lines)

    assert tuple(place.codigo for place in dataset.places) == ("1", "2", "3")


def test_senador_vector_has_no_blank_or_null_slot() -> None:
    lines = tuple(
        ProfileLine(codigo, nome, 100, 13, votos, 0, 9, 8)
        for codigo, nome, votos in (("1", "A", 4), ("2", "B", 8), ("3", "C", 2))
    )

    dataset = dataset_from_lines("senador", lines)

    assert dataset.with_ballot is False
    assert all(place.branco is None and place.nulo is None for place in dataset.places)
    assert all(len(place.features()) == 1 for place in dataset.places)
    assert dataset.places[0].features() == dataset.places[1].features()


def test_comparecimento_is_not_a_feature() -> None:
    lines = tuple(
        ProfileLine(codigo, codigo, turnout, 13, 10, 0)
        for codigo, turnout in (("1", 10), ("2", 200), ("3", 900))
    )

    dataset = dataset_from_lines("senador", lines)

    assert dataset.places[0].features() == dataset.places[2].features()
    assert dataset.places[0].comparecimento != dataset.places[2].comparecimento


def test_duplicate_join_does_not_double_votes() -> None:
    duplicated = (
        ProfileLine("1", "A", 100, 13, 10, 1, 2, 3),
        ProfileLine("1", "A", 100, 13, 10, 1, 2, 3),
    )

    dataset = dataset_from_lines("presidente", duplicated + _lines()[1:])

    assert dataset.places[0].votes[0] == 11


def test_fewer_than_three_places_is_rejected() -> None:
    with pytest.raises(FewMunicipalitiesError, match="Menos de 3 municípios com votos válidos."):
        dataset_from_lines("governador", _lines()[:2])


def test_empty_store_is_rejected_before_a_fit() -> None:
    with pytest.raises(EmptyStoredCellsError, match="Não há células gravadas para este cargo."):
        dataset_from_lines("senador", ())


@pytest.mark.parametrize(
    ("cargo", "sentence"),
    [
        ("deputadoFederal", "O cargo deputado federal não tem células gravadas."),
        ("deputadoEstadual", "O cargo deputado estadual não tem células gravadas."),
        ("deputadoDistrital", "O cargo deputado distrital não tem células gravadas."),
    ],
)
def test_deputy_cargos_have_no_stored_cells(cargo: str, sentence: str) -> None:
    with pytest.raises(CargoSemCelulasError, match=sentence):
        require_profile_cargo(cargo)


def test_unknown_cargo_uses_the_cargo_error() -> None:
    with pytest.raises(InvalidCargoError):
        require_profile_cargo("vereador")
    with pytest.raises(InvalidCargoError):
        require_profile_cargo("  ")
    with pytest.raises(InvalidCargoError):
        require_profile_cargo(13)


def test_inconsistent_cells_are_rejected() -> None:
    with pytest.raises(InconsistentCellError):
        dataset_from_lines("presidente", (_renamed(),) + _lines())
    with pytest.raises(InconsistentCellError):
        dataset_from_lines(
            "presidente",
            (ProfileLine("1", "A", 90, 22, 4, 0, 1, 1),) + _lines(),
        )
    with pytest.raises(InconsistentCellError):
        dataset_from_lines(
            "presidente",
            (ProfileLine("1", "A", 100, 22, 9, 0, 1, 1),) + _lines(),
        )
    with pytest.raises(InconsistentCellError):
        ProfileLine("1", "A", 100, 13, 1, 0, 1, None)


def test_ballot_mismatch_is_rejected() -> None:
    clash = (
        ProfileLine("1", "A", 100, 22, 4, 0, 1, 1),
        ProfileLine("1", "A", 100, 13, 4, 0, 2, 1),
    )
    with pytest.raises(InconsistentCellError):
        dataset_from_lines("presidente", clash + _lines()[1:])


def test_group_span_accepts_a_fixed_k_and_a_range() -> None:
    fixed = parse_group_span(" 4 ")
    ranged = parse_group_span("2-6")
    assert fixed == GroupSpan(4, 4, False)
    assert fixed.values() == (4,)
    assert ranged == GroupSpan(2, 6, True)
    assert ranged.values() == (2, 3, 4, 5, 6)
    assert parse_group_span("2-2").searched is True


@pytest.mark.parametrize("text", ["", "1", "0-3", "6-2", "2-", "2-6-8", "a-4", "-2"])
def test_invalid_group_span(text: str) -> None:
    with pytest.raises(InvalidGroupSpanError, match="A faixa de grupos é inválida."):
        parse_group_span(text)


def test_equal_silhouette_keeps_the_smaller_k() -> None:
    assert winning_k(((4, 0.5), (2, 0.5), (3, 0.4))) == 2
    assert winning_k(((2, 0.2), (5, 0.9))) == 5
    assert winning_k(((3, 0.4),)) == 3
    with pytest.raises(InvalidGroupSpanError):
        winning_k(())


def test_group_order_uses_count_then_turnout_then_party() -> None:
    places = (
        ProfilePlace("1", "Zed", 10, (5,), None, None),
        ProfilePlace("2", "Ana", 10, (5,), None, None),
        ProfilePlace("3", "Bia", 100, (5,), None, None),
    )
    dataset = ProfileDataset("senador", (13,), places)

    report = assemble_profile(
        2026,
        1,
        dataset,
        (0, 0, 1),
        ((1.0,), (0.2,)),
        searched=False,
        silhouette=None,
    )

    assert report.k == 2
    assert report.groups[0].municipios == 2
    assert report.groups[0].comparecimento == 20
    assert tuple(city.nome for city in report.cities if city.grupo == 1) == ("Ana", "Zed")
    assert report.searched is False
    assert report.silhouette is None


def test_tied_groups_break_on_the_smallest_dominant_party() -> None:
    places = (
        ProfilePlace("1", "A", 50, (2, 8), 1, 1),
        ProfilePlace("2", "B", 50, (9, 1), 1, 1),
        ProfilePlace("3", "C", 10, (5, 5), 1, 1),
    )
    dataset = ProfileDataset("presidente", (13, 22), places)
    centers = (
        (0.2, 0.8, 0.0, 0.0),
        (0.9, 0.1, 0.0, 0.0),
        (0.5, 0.5, 0.0, 0.0),
    )

    report = assemble_profile(
        2026,
        1,
        dataset,
        (0, 1, 2),
        centers,
        searched=True,
        silhouette=0.5,
    )

    assert tuple(city.nome for city in report.cities) == ("B", "A", "C")
    assert tuple(city.grupo for city in report.cities) == (1, 2, 3)
    assert report.groups[0].center == centers[1]


def test_fit_shape_must_match_the_places() -> None:
    dataset = dataset_from_lines("senador", _senador())
    with pytest.raises(InconsistentCellError):
        assemble_profile(
            2026,
            1,
            dataset,
            (0, 1),
            ((1.0,), (0.0,)),
            searched=False,
            silhouette=None,
        )
    with pytest.raises(InconsistentCellError):
        assemble_profile(
            2026,
            1,
            dataset,
            (0, 0, 0),
            ((1.0, 0.0),),
            searched=False,
            silhouette=None,
        )
    with pytest.raises(InconsistentCellError):
        assemble_profile(2026, 1, dataset, (0, 0, 4), ((1.0,),), searched=False, silhouette=None)


def test_dataset_rejects_a_short_sample_and_a_ballot_mismatch() -> None:
    place = ProfilePlace("1", "A", 10, (4,), None, None)
    with pytest.raises(FewMunicipalitiesError):
        ProfileDataset("senador", (13,), (place, place))
    with pytest.raises(FewMunicipalitiesError):
        ProfileDataset("senador", (), (place, place, place))
    ballots = tuple(ProfilePlace(str(i), "A", 10, (4,), 1, 1) for i in range(3))
    with pytest.raises(InconsistentCellError):
        ProfileDataset("senador", (13,), ballots)
    blank = tuple(ProfilePlace(str(i), "A", 10, (4,), None, None) for i in range(3))
    with pytest.raises(InconsistentCellError):
        ProfileDataset("presidente", (13,), blank)


def _lines() -> tuple[ProfileLine, ...]:
    return (
        ProfileLine("1", "A", 100, 22, 10, 0, 1, 2),
        ProfileLine("2", "B", 80, 13, 8, 0, 0, 1),
        ProfileLine("3", "C", 50, 13, 4, 0, 1, 0),
        ProfileLine("3", "C", 50, 22, 6, 0, 1, 0),
    )


def _senador() -> tuple[ProfileLine, ...]:
    return tuple(ProfileLine(str(i), "N", 10, 13, 4, 0) for i in range(1, 4))


def _renamed() -> ProfileLine:
    return ProfileLine("1", "Outro", 100, 13, 3, 0, 1, 2)
