"""Within-state coherence: weighted Pearson on shares centred per UF."""

import math
from collections.abc import Iterator
from dataclasses import dataclass
from fractions import Fraction
from typing import Final

from eleicoes.domain.verticalizacao import (
    DEPUTADO_ESTADUAL,
    DEPUTADO_FEDERAL,
    MAJORITARIOS,
    PROPORCIONAIS,
    MunicipioVertical,
    VerticalBase,
)

MINIMO_MUNICIPIOS: Final = 10
_EPS: Final = 1e-12
PARES_COERENCIA: Final[tuple[tuple[str, str], ...]] = (
    *((prop, maj) for maj in MAJORITARIOS for prop in PROPORCIONAIS),
    (DEPUTADO_FEDERAL, DEPUTADO_ESTADUAL),
)


@dataclass(frozen=True, slots=True)
class Coherence:
    cargo_x: str
    cargo_y: str
    r: float | None
    municipios: int


@dataclass(frozen=True, slots=True)
class ScatterPoint:
    codigo: str
    nome: str
    uf: str
    comparecimento: int
    x: Fraction
    y: Fraction


def coherence(base: VerticalBase, ufs: tuple[str, ...], partido: int, x: str, y: str) -> Coherence:
    sxy = sxx = syy = 0.0
    n = 0
    for cities in _paired(base, ufs, partido, x, y):
        if len(cities) < 2:
            continue
        part = _within(cities, partido, x, y)
        sxy += part[0]
        sxx += part[1]
        syy += part[2]
        n += len(cities)
    if n < MINIMO_MUNICIPIOS or sxx <= _EPS or syy <= _EPS:
        return Coherence(x, y, None, n)
    r = sxy / math.sqrt(sxx * syy)
    return Coherence(x, y, max(-1.0, min(1.0, r)), n)


def scatter_points(
    base: VerticalBase, ufs: tuple[str, ...], partido: int, x: str, y: str
) -> tuple[ScatterPoint, ...]:
    return tuple(
        ScatterPoint(
            city.codigo,
            city.nome,
            city.uf,
            city.comparecimento,
            Fraction(city.votos[x].get(partido, 0), city.validos[x]),
            Fraction(city.votos[y].get(partido, 0), city.validos[y]),
        )
        for cities in _paired(base, ufs, partido, x, y)
        for city in cities
    )


def _paired(
    base: VerticalBase, ufs: tuple[str, ...], partido: int, x: str, y: str
) -> Iterator[tuple[MunicipioVertical, ...]]:
    for uf in ufs:
        if not (base.concorreu(uf, x, partido) and base.concorreu(uf, y, partido)):
            continue
        cities = tuple(
            city
            for city in base.municipios.get(uf, ())
            if city.validos.get(x, 0) > 0 and city.validos.get(y, 0) > 0 and city.comparecimento > 0
        )
        if cities:
            yield cities


def _within(
    cities: tuple[MunicipioVertical, ...], partido: int, x: str, y: str
) -> tuple[float, float, float]:
    weights = [float(city.comparecimento) for city in cities]
    xs = [city.votos[x].get(partido, 0) / city.validos[x] for city in cities]
    ys = [city.votos[y].get(partido, 0) / city.validos[y] for city in cities]
    total = math.fsum(weights)
    mx = math.fsum(w * v for w, v in zip(weights, xs, strict=True)) / total
    my = math.fsum(w * v for w, v in zip(weights, ys, strict=True)) / total
    dx = [v - mx for v in xs]
    dy = [v - my for v in ys]
    return (
        math.fsum(w * a * b for w, a, b in zip(weights, dx, dy, strict=True)),
        math.fsum(w * a * a for w, a in zip(weights, dx, strict=True)),
        math.fsum(w * b * b for w, b in zip(weights, dy, strict=True)),
    )
