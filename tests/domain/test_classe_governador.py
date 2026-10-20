"""Presidential shares and the existing governor class rule. No model."""

from dataclasses import replace
from fractions import Fraction

import pytest
from tests.support import hand_class_dataset

from eleicoes.domain.classe_governador import (
    ClassDataset,
    ClassLine,
    ClassOutcome,
    ClassPlace,
    ClassReport,
    ClassRule,
    RuleCut,
    UfScore,
    class_places,
    class_report,
    majority_label,
    prepare_class_dataset,
)
from eleicoes.domain.errors import (
    FewClassesError,
    FewMunicipalitiesError,
    FewStatesError,
    InconsistentCellError,
    MissingCrossReportError,
)


def test_labels_follow_classify() -> None:
    assert _label(13, 8) == "consolidacao"
    assert _label(22, 9) == "terreno_de_virada"
    assert _label(44, 9) == "em_aberto"
    assert _label(13, 0) == "sem_governador"


def test_features_are_presidential_shares_only() -> None:
    lines = _pair("1", "A", 44, 1000)
    place = class_places(lines, _ufs("SP", lines=lines))[0]

    assert place.vector((13, 22)) == (Fraction(10, 14), Fraction(4, 14))
    assert dict(place.votes) == {13: 10, 22: 4}
    assert place.vector((13, 22, 55))[2] == 0


def test_missing_governor_line_is_not_a_place() -> None:
    lines = _president("1", "A")
    assert class_places(lines, (("1", "SP"),)) == ()


def test_comparecimento_and_governor_votes_stay_out_of_the_vector() -> None:
    low = class_places(_pair("1", "A", 13, 3, turnout=10), (("1", "SP"),))[0]
    high = class_places(_pair("2", "B", 13, 90, turnout=400), (("2", "MG"),))[0]
    assert low.vector((13, 22)) == high.vector((13, 22))
    assert low.comparecimento != high.comparecimento


def test_fewer_than_three_places_is_rejected() -> None:
    lines = _pair("1", "A", 13, 4) + _pair("2", "B", 13, 4)
    with pytest.raises(FewMunicipalitiesError, match="Menos de 3 municípios com votos válidos."):
        prepare_class_dataset(lines, _ufs("SP", "MG", lines=lines))


def test_one_class_cannot_be_separated() -> None:
    lines = _pair("1", "A", 13, 4) + _pair("2", "B", 13, 4) + _pair("3", "C", 13, 4)
    with pytest.raises(FewClassesError, match="Não há classes suficientes para separar."):
        prepare_class_dataset(lines, _ufs("SP", "MG", lines=lines))


def test_three_singleton_classes_cannot_be_separated() -> None:
    lines = _pair("1", "A", 13, 4) + _pair("2", "B", 22, 4) + _pair("3", "C", 44, 4)
    with pytest.raises(FewClassesError, match="Não há classes suficientes para separar."):
        prepare_class_dataset(lines, _ufs("SP", "MG", lines=lines))


def test_a_singleton_class_is_listed_and_left_out_of_the_split() -> None:
    lines = (
        _block("consolidacao", 3) + _block("aberto", 2) + _pair("9", "Solo", 22, 4, extra=(55, 1))
    )

    dataset = prepare_class_dataset(lines, _ufs("SP", "MG", lines=lines))

    assert dataset.held_out == ("terreno_de_virada",)
    assert {place.label for place in dataset.places} == {"consolidacao", "em_aberto"}
    assert 55 not in dataset.parties
    assert len(dataset.places) == 5


def test_held_out_follows_class_order() -> None:
    lines = (
        _pair("1", "A", 13, 1) + _block("aberto", 3) + _block("virada", 3) + _pair("8", "H", 13, 0)
    )

    dataset = prepare_class_dataset(lines, _ufs("SP", "MG", lines=lines))

    assert dataset.held_out == ("consolidacao", "sem_governador")


def test_majority_tie_keeps_class_order() -> None:
    assert majority_label(("em_aberto", "consolidacao", "em_aberto", "consolidacao")) == (
        "consolidacao"
    )
    assert majority_label(("em_aberto", "em_aberto", "consolidacao")) == "em_aberto"
    with pytest.raises(FewClassesError):
        majority_label(())


def test_report_scores_out_of_fold_predictions() -> None:
    dataset = hand_class_dataset()
    predicted = ("consolidacao", "em_aberto", "consolidacao", "em_aberto", "em_aberto", "em_aberto")
    report = class_report(2026, 1, dataset, predicted, ())
    assert report.hit_rate == Fraction(5, 6)
    assert [(s.uf, s.municipios, s.hit_rate) for s in report.by_uf] == [
        ("AC", 2, Fraction(1, 2)),
        ("BA", 3, Fraction(1)),
        ("DF", 1, Fraction(1)),
    ]
    assert {row.classe: row.recall for row in report.rows} == {
        "consolidacao": Fraction(2, 3),
        "em_aberto": Fraction(1),
    }
    assert report.macro_f1 == Fraction(1, 2) * (Fraction(4, 5) + Fraction(6, 7))


def test_state_scores_come_back_in_uf_order() -> None:
    dataset = hand_class_dataset()
    places = (dataset.places[-1],) + dataset.places[:-1]
    shuffled = ClassDataset(dataset.parties, places, (), 0)
    report = class_report(2026, 1, shuffled, _all("em_aberto", 6), ())
    assert [score.uf for score in report.by_uf] == ["AC", "BA", "DF"]


def test_majority_baseline_is_learned_without_the_held_out_state() -> None:
    report = class_report(2026, 1, hand_class_dataset(), _all("em_aberto", 6), ())
    # without AC: c=1, a=3 -> a; without BA: c=2, a=1 -> c; without DF: c=3, a=2 -> c
    assert report.baseline == Fraction(0 + 1 + 0, 6)


def test_leader_baseline_maps_each_leader_to_its_training_majority() -> None:
    report = class_report(2026, 1, hand_class_dataset(), _all("em_aberto", 6), ())
    assert report.leader_baseline == Fraction(6, 6)


def test_unseen_leader_falls_back_to_the_training_majority() -> None:
    dataset = hand_class_dataset(df_leader=44)
    report = class_report(2026, 1, dataset, _all("em_aberto", 6), ())
    # without AC: 13 -> c, AC 2/2; without BA: 22 unseen -> c, BA 1/3; without DF: 44 unseen -> c
    assert report.leader_baseline == Fraction(3, 6)


def test_rate_under_the_best_baseline_is_below_baseline() -> None:
    predicted = ("consolidacao", "em_aberto", "consolidacao", "em_aberto", "em_aberto", "em_aberto")
    report = class_report(2026, 1, hand_class_dataset(), predicted, ())
    # hit 5/6, majority 1/6, leader 6/6
    assert report.below_baseline is True


def test_rate_matching_the_best_baseline_is_not_below_it() -> None:
    expected = hand_class_dataset().labels()
    report = class_report(2026, 1, hand_class_dataset(), expected, ())
    # hit 6/6 equals the leader baseline 6/6
    assert report.below_baseline is False


def test_rate_under_the_majority_but_over_the_leader_is_below_baseline() -> None:
    report = _rated(hit=Fraction(1, 2), majority=Fraction(2, 3), leader=Fraction(1, 3))
    assert report.below_baseline is True


def test_rate_tied_with_the_majority_is_not_below_baseline() -> None:
    report = _rated(hit=Fraction(2, 3), majority=Fraction(2, 3), leader=Fraction(1, 3))
    assert report.below_baseline is False


def test_misaligned_prediction_is_inconsistent() -> None:
    with pytest.raises(InconsistentCellError):
        class_report(2026, 1, hand_class_dataset(), ("consolidacao",), ())


def test_prediction_outside_the_class_order_is_inconsistent() -> None:
    with pytest.raises(InconsistentCellError):
        class_report(2026, 1, hand_class_dataset(), _all("vitoria", 6), ())


def test_report_rows_count_every_place_and_keep_the_rules() -> None:
    rules = (
        ClassRule("consolidacao", (RuleCut(13, 0.5, True),)),
        ClassRule("em_aberto", (RuleCut(13, 0.5, False),)),
    )
    dataset = ClassDataset((13, 22, 44), hand_class_dataset().places, ("sem_governador",), 2)
    report = class_report(2026, 1, dataset, _all("em_aberto", 6), rules)
    assert [(row.classe, row.support) for row in report.rows] == [
        ("consolidacao", 3),
        ("em_aberto", 3),
    ]
    assert report.rows[0].rules[0][0].at_most is True
    assert report.held_out == ("sem_governador",)
    assert report.without_uf == 2


def test_never_predicted_class_scores_zero_f1() -> None:
    report = class_report(2026, 1, hand_class_dataset(), _all("consolidacao", 6), ())
    assert {row.classe: row.recall for row in report.rows} == {
        "consolidacao": Fraction(1),
        "em_aberto": Fraction(0),
    }
    assert report.macro_f1 == Fraction(1, 2) * Fraction(2, 3)


def test_report_needs_two_states() -> None:
    places = tuple(replace(place, uf="AC") for place in hand_class_dataset().places)
    with pytest.raises(FewStatesError):
        class_report(2026, 1, ClassDataset((13, 22, 44), places, (), 0), _all("em_aberto", 6), ())


def test_state_score_needs_municipalities() -> None:
    with pytest.raises(InconsistentCellError):
        UfScore("AC", 0, Fraction(0))


def test_inconsistent_party_row_is_rejected() -> None:
    lines = _president("1", "A") + (ClassLine("presidente", "1", "A", 100, 13, 9, 0),)
    with pytest.raises(InconsistentCellError):
        class_places(lines, (("1", "SP"),))


def test_place_carries_its_uf_and_presidential_leader() -> None:
    ufs = (
        ("aberto-0", "SP"),
        ("aberto-1", "RJ"),
        ("consolidacao-0", "MG"),
        ("consolidacao-1", "SP"),
        ("virada-0", "BA"),
        ("virada-1", "MG"),
    )
    dataset = prepare_class_dataset(_three_classes(), ufs)
    kept = {place.codigo for place in dataset.places}
    assert {place.codigo: place.uf for place in dataset.places} == {
        codigo: uf for codigo, uf in ufs if codigo in kept
    }
    assert dataset.groups() == ("SP", "RJ", "MG", "SP", "BA", "MG")
    assert all(place.leader in dataset.parties for place in dataset.places)
    assert {place.leader for place in dataset.places} == {13}
    assert dataset.without_uf == 0


def test_place_without_uf_is_dropped_and_counted() -> None:
    lines = _three_classes() + _pair("99", "Órfã", 13, 4)
    dataset = prepare_class_dataset(lines, _ufs("SP", "MG"))
    assert "99" not in {place.codigo for place in dataset.places}
    assert dataset.without_uf == 1


def test_only_orphans_that_would_be_places_are_counted() -> None:
    lines = (
        _three_classes()
        + _pair("95", "Sem comparecimento", 13, 4, turnout=0)
        + (
            ClassLine("presidente", "96", "Sem votos", 100, 13, 0, 0),
            ClassLine("governador", "96", "Sem votos", 100, 13, 4, 0),
        )
        + _president("97", "Só presidente")
        + _pair("99", "Órfã", 13, 4)
    )
    dataset = prepare_class_dataset(lines, _ufs("SP", "MG"))
    assert dataset.without_uf == 1


def test_place_without_presidential_votes_is_not_a_place() -> None:
    lines = (
        ClassLine("presidente", "1", "A", 100, 13, 0, 0),
        ClassLine("governador", "1", "A", 100, 13, 4, 0),
    )
    assert class_places(lines, (("1", "SP"),)) == ()


def test_presidential_leader_is_the_most_voted_party() -> None:
    lines = (
        ClassLine("presidente", "1", "A", 100, 13, 4, 0),
        ClassLine("presidente", "1", "A", 100, 22, 10, 0),
        ClassLine("governador", "1", "A", 100, 22, 6, 0),
    )
    assert class_places(lines, (("1", "SP"),))[0].leader == 22


def test_presidential_tie_goes_to_the_lowest_party() -> None:
    lines = (
        ClassLine("presidente", "1", "A", 100, 22, 7, 0),
        ClassLine("presidente", "1", "A", 100, 13, 7, 0),
        ClassLine("governador", "1", "A", 100, 13, 6, 0),
    )
    assert class_places(lines, (("1", "SP"),))[0].leader == 13


def test_empty_uf_map_asks_for_the_cross_report() -> None:
    with pytest.raises(
        MissingCrossReportError, match="Gere o relatório presidente × governador antes."
    ):
        prepare_class_dataset(_three_classes(), ())


def test_code_under_two_ufs_is_inconsistent() -> None:
    with pytest.raises(InconsistentCellError):
        prepare_class_dataset(_three_classes(), _ufs("SP", "MG") + (("aberto-0", "RJ"),))


def test_uf_pairs_are_compared_without_padding() -> None:
    ufs = _ufs("SP", "MG")
    padded = tuple((f" {codigo} ", f"{uf} ") for codigo, uf in ufs)
    dataset = prepare_class_dataset(_three_classes(), padded + ufs[:1])
    assert dataset.groups() == tuple(uf for _codigo, uf in ufs)
    with pytest.raises(InconsistentCellError):
        prepare_class_dataset(_three_classes(), ufs + ((" aberto-0", "RJ"),))


def test_repeated_code_and_uf_pair_is_accepted() -> None:
    ufs = _ufs("SP", "MG")
    dataset = prepare_class_dataset(_three_classes(), ufs + ufs)
    assert len(dataset.places) == len(ufs)


def test_no_code_matches_leaves_too_few_places() -> None:
    with pytest.raises(FewMunicipalitiesError):
        prepare_class_dataset(_three_classes(), (("zzz", "SP"),))


def test_single_state_cannot_be_validated() -> None:
    with pytest.raises(FewStatesError, match="Menos de 2 UFs para validar."):
        prepare_class_dataset(_three_classes(), _ufs("SP"))


def test_states_are_counted_on_the_kept_places() -> None:
    lines = (
        _block("consolidacao", 3) + _block("aberto", 2) + _pair("9", "Solo", 22, 4, extra=(55, 1))
    )
    ufs = tuple(
        (codigo, "MG" if codigo == "9" else "SP") for codigo, _uf in _ufs("SP", lines=lines)
    )
    with pytest.raises(FewStatesError, match="Menos de 2 UFs para validar."):
        prepare_class_dataset(lines, ufs)


def test_place_needs_a_uf() -> None:
    with pytest.raises(InconsistentCellError):
        ClassPlace("1", "A", 10, "consolidacao", ((13, 4),), " ", 13)


def _three_classes() -> tuple[ClassLine, ...]:
    return _block("consolidacao", 2) + _block("aberto", 2) + _block("virada", 2)


def _ufs(*names: str, lines: tuple[ClassLine, ...] | None = None) -> tuple[tuple[str, str], ...]:
    source = _three_classes() if lines is None else lines
    codes = sorted({line.codigo for line in source})
    return tuple((codigo, names[index % len(names)]) for index, codigo in enumerate(codes))


def _label(party: int, votes: int) -> str:
    return class_places(_pair("1", "A", party, votes), (("1", "SP"),))[0].label


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


def _rated(*, hit: Fraction, majority: Fraction, leader: Fraction) -> ClassReport:
    return ClassReport(
        2026,
        1,
        (13,),
        hit,
        majority,
        (ClassOutcome("consolidacao", 3, (), Fraction(1)),),
        (),
        leader,
        Fraction(1),
        (UfScore("SP", 3, hit),),
        0,
    )


def _all(label: str, count: int) -> tuple[str, ...]:
    return (label,) * count
