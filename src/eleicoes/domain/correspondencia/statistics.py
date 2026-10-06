"""Modified z-score of Iglewicz and Hoaglin."""

import math
from collections.abc import Sequence
from typing import Final

MODIFIED_Z_COEFFICIENT: Final = 0.6745


def modified_z(value: float, median: float, mad: float) -> float:
    if mad == 0:
        return 0.0 if value == median else math.inf
    return MODIFIED_Z_COEFFICIENT * (value - median) / mad


def median(values: Sequence[float]) -> float:
    ordered = sorted(values)
    count = len(ordered)
    middle = count // 2
    if count % 2 == 1:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2


def median_absolute_deviation(values: Sequence[float], center: float) -> float:
    return median([abs(value - center) for value in values])
