"""Sklearn fits. One thread, and the domain only receives plain floats."""

import os
from collections.abc import MutableMapping
from typing import Final, Protocol, SupportsFloat, SupportsInt, cast

from eleicoes.domain.classe_governador import ClassRule, RuleCut
from eleicoes.domain.errors import (
    FewClassesError,
    FewStatesError,
    InconsistentCellError,
    UnusableGroupCountError,
)
from eleicoes.domain.perfis import GroupSpan, winning_k
from eleicoes.ports.classe_governador import ClassFit
from eleicoes.ports.perfis import RawClusterFit

_N_INIT: Final = 10
_RANDOM_STATE: Final = 0
_MAX_DEPTH: Final = 3
_MIN_LEAF: Final = 20
_LEAF: Final = -1
_MIN_GROUPS: Final = 2
_SILHOUETTE_SAMPLE: Final = 2000


def limit_omp_threads(environ: MutableMapping[str, str]) -> None:
    if environ.get("OMP_NUM_THREADS") is None:
        environ["OMP_NUM_THREADS"] = "1"


limit_omp_threads(os.environ)

# isort: split
import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.model_selection import LeaveOneGroupOut, cross_val_predict
from sklearn.tree import DecisionTreeClassifier
from threadpoolctl import threadpool_limits


class SklearnProfileClusterer:
    def fit(
        self,
        matrix: tuple[tuple[float, ...], ...],
        span: GroupSpan,
    ) -> RawClusterFit:
        rows = _matrix(matrix)
        if span.searched:
            return _search(rows, span.values())
        return _once(rows, span.lower)


class SklearnGovernorTree:
    def fit(
        self,
        matrix: tuple[tuple[float, ...], ...],
        labels: tuple[str, ...],
        parties: tuple[int, ...],
        groups: tuple[str, ...],
    ) -> ClassFit:
        if len(groups) != len(matrix):
            raise InconsistentCellError()
        if len(set(groups)) < _MIN_GROUPS:
            raise FewStatesError()
        try:
            return _tree(matrix, labels, parties, groups)
        except ValueError as exc:
            raise FewClassesError() from exc


def _search(rows: list[list[float]], ks: tuple[int, ...]) -> RawClusterFit:
    scored: list[tuple[int, float]] = []
    fits: dict[int, RawClusterFit] = {}
    for k in ks:
        fitted, score = _scored(rows, k)
        scored.append((k, score))
        fits[k] = fitted
    return fits[winning_k(tuple(scored))]


def _once(rows: list[list[float]], k: int) -> RawClusterFit:
    _guard_k(rows, k)
    with threadpool_limits(limits=1):
        labels, centers = _kmeans(rows, k)
    return RawClusterFit(labels, centers, None)


def _scored(rows: list[list[float]], k: int) -> tuple[RawClusterFit, float]:
    _guard_k(rows, k)
    with threadpool_limits(limits=1):
        labels, centers = _kmeans(rows, k)
        score = _silhouette(rows, labels)
    return RawClusterFit(labels, centers, score), score


def _guard_k(rows: list[list[float]], k: int) -> None:
    if k >= len(rows):
        raise UnusableGroupCountError()


def _kmeans(
    rows: list[list[float]],
    k: int,
) -> tuple[tuple[int, ...], tuple[tuple[float, ...], ...]]:
    model = KMeans(n_clusters=k, n_init=_N_INIT, random_state=_RANDOM_STATE)
    model.fit(rows)
    return _ints(model.labels_), _rows(model.cluster_centers_)


def _tree(
    matrix: tuple[tuple[float, ...], ...],
    labels: tuple[str, ...],
    parties: tuple[int, ...],
    groups: tuple[str, ...],
) -> ClassFit:
    x = np.asarray(matrix, dtype=float)
    y = np.asarray(labels)
    with threadpool_limits(limits=1):
        predicted = cross_val_predict(_classifier(), x, y, groups=groups, cv=LeaveOneGroupOut())
        rules = _rules(_classifier().fit(x, y), parties)
    return ClassFit(tuple(_texts(predicted)), rules)


def _classifier() -> DecisionTreeClassifier:
    return DecisionTreeClassifier(
        max_depth=_MAX_DEPTH,
        min_samples_leaf=_MIN_LEAF,
        random_state=_RANDOM_STATE,
    )


def _rules(model: object, parties: tuple[int, ...]) -> tuple[ClassRule, ...]:
    spec = _spec(model)
    found: list[ClassRule] = []
    _walk(spec, 0, (), parties, found)
    return tuple(found)


def _walk(
    spec: "_Tree",
    node: int,
    path: tuple[RuleCut, ...],
    parties: tuple[int, ...],
    found: list[ClassRule],
) -> None:
    if spec.left[node] == _LEAF:
        found.append(ClassRule(spec.classes[_class_index(spec.counts[node])], path))
        return
    party = parties[spec.feature[node]]
    threshold = spec.threshold[node]
    _walk(spec, spec.left[node], path + (RuleCut(party, threshold, True),), parties, found)
    _walk(spec, spec.right[node], path + (RuleCut(party, threshold, False),), parties, found)


def _class_index(counts: tuple[float, ...]) -> int:
    best_at = 0
    best = counts[0]
    for index, count in enumerate(counts):
        if count > best:
            best_at = index
            best = count
    return best_at


class _Tree:
    def __init__(
        self,
        left: tuple[int, ...],
        right: tuple[int, ...],
        feature: tuple[int, ...],
        threshold: tuple[float, ...],
        counts: tuple[tuple[float, ...], ...],
        classes: tuple[str, ...],
    ) -> None:
        self.left = left
        self.right = right
        self.feature = feature
        self.threshold = threshold
        self.counts = counts
        self.classes = classes


class _NodeArrays(Protocol):
    children_left: object
    children_right: object
    feature: object
    threshold: object
    value: object


class _FittedClassifier(Protocol):
    tree_: _NodeArrays
    classes_: object


def _spec(model: object) -> _Tree:
    fitted = cast(_FittedClassifier, model)
    tree = fitted.tree_
    return _Tree(
        _ints(tree.children_left),
        _ints(tree.children_right),
        _ints(tree.feature),
        _floats(tree.threshold),
        _counts(tree.value),
        tuple(_texts(fitted.classes_)),
    )


def _silhouette(rows: list[list[float]], labels: tuple[int, ...]) -> float:
    try:
        value = silhouette_score(rows, list(labels), **_sampling(len(rows)))
    except ValueError as exc:
        raise UnusableGroupCountError() from exc
    score = float(value)
    if score != score:
        return -1.0
    return score


def _sampling(count: int) -> dict[str, int]:
    if count > _SILHOUETTE_SAMPLE:
        return {"sample_size": _SILHOUETTE_SAMPLE, "random_state": _RANDOM_STATE}
    return {}


def _matrix(matrix: tuple[tuple[float, ...], ...]) -> list[list[float]]:
    return [list(row) for row in matrix]


def _ints(values: object) -> tuple[int, ...]:
    return tuple(_as_int(item) for item in _tolist(values))


def _floats(values: object) -> tuple[float, ...]:
    return tuple(_as_float(item) for item in _tolist(values))


def _texts(values: object) -> list[str]:
    return [str(item) for item in _tolist(values)]


def _rows(values: object) -> tuple[tuple[float, ...], ...]:
    return tuple(_number_row(row) for row in _tolist(values))


def _counts(values: object) -> tuple[tuple[float, ...], ...]:
    rows: list[tuple[float, ...]] = []
    for node in _tolist(values):
        rows.append(_count_row(node))
    return tuple(rows)


def _count_row(node: object) -> tuple[float, ...]:
    row = _tolist(node)
    if row and isinstance(row[0], list):
        return _number_row(row[0])
    return _number_row(row)


def _number_row(row: object) -> tuple[float, ...]:
    return tuple(_as_float(item) for item in _tolist(row))


def _as_int(item: object) -> int:
    if isinstance(item, bool) or not isinstance(item, SupportsInt):
        raise UnusableGroupCountError()
    return int(item)


def _as_float(item: object) -> float:
    if isinstance(item, bool) or not isinstance(item, SupportsFloat):
        raise UnusableGroupCountError()
    return float(item)


def _tolist(values: object) -> list[object]:
    if isinstance(values, list):
        return values
    if isinstance(values, tuple):
        return list(values)
    method = getattr(values, "tolist", None)
    if not callable(method):
        raise UnusableGroupCountError()
    raw = method()
    if not isinstance(raw, list):
        raise UnusableGroupCountError()
    return raw
