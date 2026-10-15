"""Presidential shares and the existing governor class rule. No model."""

from fractions import Fraction

import pytest

from eleicoes.domain.classe_governador import (
    ClassDataset,
    ClassLine,
    ClassPlace,
    ClassRule,
    RuleCut,
    class_places,
    class_report,
    majority_label,
    prepare_class_dataset,
)
from eleicoes.domain.errors import FewClassesError, FewMunicipalitiesError, InconsistentCellError


def test_labels_follow_classify() -> None:
    assert _label(13, 8) == "consolidacao"
    assert _label(22, 9) == "terreno_de_virada"
    assert _label(44, 9) == "em_aberto"
    assert _label(13, 0) == "sem_governador"


def test_features_are_presidential_shares_only() -> None:
    place = class_places(_pair("1", "A", 44, 1000))[0]

    assert place.vector((13, 22)) == (Fraction(10, 14), Fraction(4, 14))
    assert dict(place.votes) == {13: 10, 22: 4}
    assert place.vector((13, 22, 55))[2] == 0


def test_missing_governor_line_is_not_a_place() -> None:
    lines = _president("1", "A")
    assert class_places(lines) == ()


def test_comparecimento_and_governor_votes_stay_out_of_the_vector() -> None:
    low = class_places(_pair("1", "A", 13, 3, turnout=10))[0]
    high = class_places(_pair("2", "B", 13, 90, turnout=400))[0]
    assert low.vector((13, 22)) == high.vector((13, 22))
    assert low.comparecimento != high.comparecimento


def test_fewer_than_three_places_is_rejected() -> None:
    lines = _pair("1", "A", 13, 4) + _pair("2", "B", 13, 4)
    with pytest.raises(FewMunicipalitiesError, match="Menos de 3 municípios com votos válidos."):
        prepare_class_dataset(lines)


def test_one_class_cannot_be_separated() -> None:
    lines = _pair("1", "A", 13, 4) + _pair("2", "B", 13, 4) + _pair("3", "C", 13, 4)
    with pytest.raises(FewClassesError, match="Não há classes suficientes para separar."):
        prepare_class_dataset(lines)


def test_three_singleton_classes_cannot_be_separated() -> None:
    lines = _pair("1", "A", 13, 4) + _pair("2", "B", 22, 4) + _pair("3", "C", 44, 4)
    with pytest.raises(FewClassesError, match="Não há classes suficientes para separar."):
        prepare_class_dataset(lines)


def test_a_singleton_class_is_listed_and_left_out_of_the_split() -> None:
    lines = (
        _block("consolidacao", 3) + _block("aberto", 2) + _pair("9", "Solo", 22, 4, extra=(55, 1))
    )

    dataset = prepare_class_dataset(lines)

    assert dataset.held_out == ("terreno_de_virada",)
    assert {place.label for place in dataset.places} == {"consolidacao", "em_aberto"}
    assert 55 not in dataset.parties
    assert len(dataset.places) == 5


def test_held_out_follows_class_order() -> None:
    lines = (
        _pair("1", "A", 13, 1) + _block("aberto", 3) + _block("virada", 3) + _pair("8", "H", 13, 0)
    )

    dataset = prepare_class_dataset(lines)

    assert dataset.held_out == ("consolidacao", "sem_governador")


def test_majority_tie_keeps_class_order() -> None:
    assert majority_label(("em_aberto", "consolidacao", "em_aberto", "consolidacao")) == (
        "consolidacao"
    )
    assert majority_label(("em_aberto", "em_aberto", "consolidacao")) == "em_aberto"
    with pytest.raises(FewClassesError):
        majority_label(())


def test_report_rates_use_the_untouched_fold() -> None:
    places = (
        ClassPlace("1", "A", 10, "consolidacao", ((13, 4),)),
        ClassPlace("2", "B", 10, "em_aberto", ((13, 4),)),
    )
    dataset = ClassDataset((13,), places, ("sem_governador",))
    rules = (
        ClassRule("consolidacao", (RuleCut(13, 0.5, True),)),
        ClassRule("em_aberto", (RuleCut(13, 0.5, False),)),
    )

    report = class_report(
        2026,
        1,
        dataset,
        "consolidacao",
        ("consolidacao", "em_aberto"),
        ("consolidacao", "consolidacao"),
        rules,
    )

    assert report.hit_rate == Fraction(1, 2)
    assert report.baseline == Fraction(1, 2)
    assert report.rows[0].support == 1
    assert report.rows[0].rules[0][0].at_most is True
    assert report.held_out == ("sem_governador",)


def test_report_rejects_a_broken_fold() -> None:
    place = ClassPlace("1", "A", 10, "consolidacao", ((13, 4),))
    dataset = ClassDataset((13,), (place,), ())
    with pytest.raises(InconsistentCellError):
        class_report(2026, 1, dataset, "consolidacao", (), (), ())
    with pytest.raises(InconsistentCellError):
        class_report(2026, 1, dataset, "consolidacao", ("consolidacao",), (), ())


def test_inconsistent_party_row_is_rejected() -> None:
    lines = _president("1", "A") + (ClassLine("presidente", "1", "A", 100, 13, 9, 0),)
    with pytest.raises(InconsistentCellError):
        class_places(lines)


def _label(party: int, votes: int) -> str:
    return class_places(_pair("1", "A", party, votes))[0].label


def _pair(
    codigo: str,
    nome: str,
    governor: int,
    votes: int,
    *,
    turnout: int = 100,
    extra: tuple[int, int] | None = None,
) -> tuple[ClassLine, ...]:
    lines = list(_president(codigo, nome, turnout))
    if extra is not None:
        lines.append(ClassLine("presidente", codigo, nome, turnout, extra[0], extra[1], 0))
    lines.append(ClassLine("governador", codigo, nome, turnout, governor, votes, 0))
    return tuple(lines)


def _president(codigo: str, nome: str, turnout: int = 100) -> tuple[ClassLine, ...]:
    return (
        ClassLine("presidente", codigo, nome, turnout, 13, 10, 0),
        ClassLine("presidente", codigo, nome, turnout, 22, 4, 0),
    )


def _block(kind: str, count: int) -> tuple[ClassLine, ...]:
    governor = {"consolidacao": 13, "virada": 22, "aberto": 44}[kind]
    found: list[ClassLine] = []
    for index in range(count):
        found.extend(_pair(f"{kind}-{index}", kind, governor, 6))
    return tuple(found)
