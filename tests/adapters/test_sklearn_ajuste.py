"""Tiny sklearn fits. Centers are checked with a tolerance, not an exact score."""

import pytest

from eleicoes.adapters.sklearn_ajuste import (
    SklearnGovernorTree,
    SklearnProfileClusterer,
    _count_row,
    _silhouette,
    _tolist,
    _unpack,
    limit_omp_threads,
)
from eleicoes.domain.errors import FewClassesError, UnusableGroupCountError
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


def test_tree_rules_are_portuguese_cuts_on_the_held_out_quarter() -> None:
    rows, labels = _separable()
    fit = SklearnGovernorTree().fit(tuple(rows), tuple(labels), (13,))

    assert len(fit.expected) == 20
    assert fit.predicted == fit.expected
    assert fit.majority == "consolidacao"
    assert {cut.party for rule in fit.rules for cut in rule.cuts} == {13}
    assert {cut.at_most for rule in fit.rules for cut in rule.cuts} == {True, False}
    assert all(len(rule.cuts) <= 3 for rule in fit.rules)
    assert any(0.2 < cut.threshold < 0.8 for rule in fit.rules for cut in rule.cuts)


def test_unstratifiable_sample_is_a_class_error() -> None:
    with pytest.raises(FewClassesError, match="Não há classes suficientes"):
        SklearnGovernorTree().fit(((0.0,), (1.0,)), ("consolidacao", "em_aberto"), (13,))


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
    with pytest.raises(FewClassesError):
        _unpack([1, 2, 3])
    assert _tolist((1, 2)) == [1, 2]
    assert _count_row([1.0, 2.0]) == (1.0, 2.0)
    assert _count_row([[3.0, 4.0]]) == (3.0, 4.0)


def test_nan_silhouette_does_not_win(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "eleicoes.adapters.sklearn_ajuste.silhouette_score",
        lambda *_args, **_kwargs: float("nan"),
    )
    assert _silhouette([[0.0], [1.0], [0.2], [0.8]], (0, 0, 1, 1)) == -1.0


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
