"""Tiny sklearn fits. Centers are checked with a tolerance, not an exact score."""

import pytest

from eleicoes.adapters.sklearn_ajuste import (
    SklearnGovernorTree,
    SklearnProfileClusterer,
    _count_row,
    _silhouette,
    _tolist,
    limit_omp_threads,
)
from eleicoes.domain.errors import (
    FewClassesError,
    FewStatesError,
    InconsistentCellError,
    UnusableGroupCountError,
)
from eleicoes.domain.perfis import GroupSpan


def test_range_separates_two_blobs_and_centers_stay_near_the_means() -> None:
    left, right = _blobs()
    rows = tuple(left + right)
    fit = SklearnProfileClusterer().fit(rows, GroupSpan(2, 4, True))
    left_labels = set(fit.assignments[: len(left)])
    right_labels = set(fit.assignments[len(left) :])

    assert fit.silhouette is not None
    assert -1.0 <= fit.silhouette <= 1.0
    assert left_labels.isdisjoint(right_labels)
    assert left_labels
    assert right_labels
    _assert_near(fit.centers, fit.assignments, _mean(left), _mean(right))


def test_fixed_k_does_not_search(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(*_args: object, **_kwargs: object) -> float:
        raise AssertionError("silhouette")

    monkeypatch.setattr("eleicoes.adapters.sklearn_ajuste.silhouette_score", boom)
    rows = tuple(_blobs()[0] + _blobs()[1])
    fit = SklearnProfileClusterer().fit(rows, GroupSpan(2, 2, False))

    assert fit.silhouette is None
    assert len(fit.centers) == 2
    assert set(fit.assignments) == {0, 1}


def test_too_many_groups_for_the_sample() -> None:
    rows = ((0.0, 0.0), (1.0, 1.0), (0.2, 0.2))
    with pytest.raises(UnusableGroupCountError, match="não cabe"):
        SklearnProfileClusterer().fit(rows, GroupSpan(4, 4, False))


def test_tree_predicts_every_row_out_of_its_state() -> None:
    rows, labels = _separable()
    groups = tuple(("SP", "MG", "RJ", "DF")[i % 4] for i in range(len(rows)))
    fit = SklearnGovernorTree().fit(tuple(rows), tuple(labels), (13,), groups)

    assert len(fit.predicted) == len(rows)
    assert fit.predicted == tuple(labels)
    assert {cut.party for rule in fit.rules for cut in rule.cuts} == {13}
    assert {cut.at_most for rule in fit.rules for cut in rule.cuts} == {True, False}
    assert all(len(rule.cuts) <= 3 for rule in fit.rules)
    assert any(0.2 < cut.threshold < 0.8 for rule in fit.rules for cut in rule.cuts)


def test_class_only_in_the_held_out_state_is_not_an_error() -> None:
    rows = [[0.1]] * 20 + [[0.9]] * 20 + [[0.5]] * 2
    labels = ("consolidacao",) * 20 + ("em_aberto",) * 20 + ("sem_governador",) * 2
    groups = ("SP",) * 20 + ("MG",) * 20 + ("DF",) * 2
    fit = SklearnGovernorTree().fit(tuple(map(tuple, rows)), labels, (13,), groups)
    assert fit.predicted == ("em_aberto",) * 20 + ("consolidacao",) * 20 + ("em_aberto",) * 2


def test_single_row_state_is_predicted_by_the_other_states() -> None:
    rows = ((0.1,),) * 20 + ((0.9,),) * 20 + ((0.1,),)
    labels = ("consolidacao",) * 20 + ("em_aberto",) * 21
    groups = ("SP",) * 20 + ("MG",) * 20 + ("DF",)
    fit = SklearnGovernorTree().fit(rows, labels, (13,), groups)
    assert len(fit.predicted) == len(labels)
    assert fit.predicted[-1] == "consolidacao"


def test_one_state_is_a_state_error() -> None:
    with pytest.raises(FewStatesError, match="Menos de 2 UFs"):
        SklearnGovernorTree().fit(
            ((0.0,), (1.0,)), ("consolidacao", "em_aberto"), (13,), ("SP", "SP")
        )


def test_groups_out_of_step_with_the_rows_are_inconsistent() -> None:
    with pytest.raises(InconsistentCellError):
        SklearnGovernorTree().fit(
            ((0.0,), (1.0,), (0.5,)),
            ("consolidacao", "em_aberto", "em_aberto"),
            (13,),
            ("SP", "MG"),
        )


def test_tree_failure_is_a_class_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def broken(*_args: object, **_kwargs: object) -> object:
        raise ValueError("bad fold")

    monkeypatch.setattr("eleicoes.adapters.sklearn_ajuste.cross_val_predict", broken)
    rows, labels = _separable()
    groups = ("SP", "MG") * 40
    with pytest.raises(FewClassesError, match="Não há classes suficientes"):
        SklearnGovernorTree().fit(tuple(rows), tuple(labels), (13,), groups)


def test_omp_is_set_only_when_missing() -> None:
    unset: dict[str, str] = {}
    limit_omp_threads(unset)
    assert unset["OMP_NUM_THREADS"] == "1"
    kept = {"OMP_NUM_THREADS": "4"}
    limit_omp_threads(kept)
    assert kept["OMP_NUM_THREADS"] == "4"


def test_bad_silhouette_and_unreadable_arrays() -> None:
    with pytest.raises(UnusableGroupCountError):
        _silhouette([[0.0, 0.0], [1.0, 1.0], [0.0, 1.0], [1.0, 0.0]], (0, 0, 0, 0))
    with pytest.raises(UnusableGroupCountError):
        _tolist(object())
    assert _tolist((1, 2)) == [1, 2]
    assert _count_row([1.0, 2.0]) == (1.0, 2.0)
    assert _count_row([[3.0, 4.0]]) == (3.0, 4.0)


def test_nan_silhouette_does_not_win(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "eleicoes.adapters.sklearn_ajuste.silhouette_score",
        lambda *_args, **_kwargs: float("nan"),
    )
    assert _silhouette([[0.0], [1.0], [0.2], [0.8]], (0, 0, 1, 1)) == -1.0


def test_tiny_bimodal_feature_does_not_drive_the_split() -> None:
    offsets = (-0.16, -0.08, 0.0, 0.08, 0.16)
    rows = tuple(
        (base + offsets[i % 5], 0.001 * (i % 2))
        for base, start in ((0.1, 0), (0.9, 10))
        for i in range(start, start + 10)
    )
    fit = SklearnProfileClusterer().fit(rows, GroupSpan(2, 2, False))
    assert len(set(fit.assignments[:10])) == 1
    assert len(set(fit.assignments[10:])) == 1
    assert fit.assignments[0] != fit.assignments[10]


def test_search_on_raw_shares_keeps_the_wide_split() -> None:
    offsets = (-0.16, -0.08, 0.0, 0.08, 0.16)
    rows = tuple(
        (base + offsets[i % 5], 0.001 * (i % 2))
        for base, start in ((0.1, 0), (0.9, 10))
        for i in range(start, start + 10)
    )
    fit = SklearnProfileClusterer().fit(rows, GroupSpan(2, 3, True))
    assert len(set(fit.assignments[:10])) == 1
    assert len(set(fit.assignments[10:])) == 1
    assert fit.assignments[0] != fit.assignments[10]
    assert fit.silhouette is not None and fit.silhouette > 0.7


def test_large_sample_scores_on_a_seeded_subsample(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, object] = {}

    def spy(_x: object, _labels: object, **kwargs: object) -> float:
        seen.update(kwargs)
        return 0.5

    monkeypatch.setattr("eleicoes.adapters.sklearn_ajuste.silhouette_score", spy)
    rows = [[float(i % 2), float(i % 3)] for i in range(2001)]
    assert _silhouette(rows, tuple(i % 2 for i in range(2001))) == 0.5
    assert seen == {"sample_size": 2000, "random_state": 0}


def test_small_sample_scores_exactly(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, object] = {}

    def spy(_x: object, _labels: object, **kwargs: object) -> float:
        seen.update(kwargs)
        return 0.5

    monkeypatch.setattr("eleicoes.adapters.sklearn_ajuste.silhouette_score", spy)
    rows = [[float(i % 2)] for i in range(2000)]
    assert _silhouette(rows, tuple(i % 2 for i in range(2000))) == 0.5
    assert seen == {}


def _blobs() -> tuple[list[tuple[float, float]], list[tuple[float, float]]]:
    left = [(0.0, 0.0), (0.2, 0.0), (0.0, 0.2), (0.2, 0.2), (0.1, 0.1), (0.1, 0.0)]
    right = [(20.0, 20.0), (20.2, 20.0), (20.0, 20.2), (20.2, 20.2), (20.1, 20.1), (20.1, 20.0)]
    return left, right


def _mean(points: list[tuple[float, float]]) -> tuple[float, float]:
    count = len(points)
    return (sum(point[0] for point in points) / count, sum(point[1] for point in points) / count)


def _assert_near(
    centers: tuple[tuple[float, ...], ...],
    assignments: tuple[int, ...],
    left: tuple[float, float],
    right: tuple[float, float],
) -> None:
    used = set(assignments)
    for index, center in enumerate(centers):
        if index not in used:
            continue
        assert _close(center, left) or _close(center, right)


def _close(center: tuple[float, ...], mean: tuple[float, float]) -> bool:
    return abs(center[0] - mean[0]) <= 0.5 and abs(center[1] - mean[1]) <= 0.5


def _separable() -> tuple[list[tuple[float, ...]], list[str]]:
    rows: list[tuple[float, ...]] = []
    labels: list[str] = []
    for _index in range(40):
        rows.append((0.1,))
        labels.append("consolidacao")
    for _index in range(40):
        rows.append((0.9,))
        labels.append("em_aberto")
    return rows, labels
