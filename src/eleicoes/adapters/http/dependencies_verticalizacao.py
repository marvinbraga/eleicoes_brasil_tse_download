"""Cached verticalization job: one base per election, one report per scope."""

from collections.abc import Callable
from functools import lru_cache
from typing import Final, TypeAlias

from eleicoes.domain.values import ElectionYear, Turno, Uf
from eleicoes.domain.verticalizacao import VerticalBase
from eleicoes.domain.verticalizacao_relatorio import (
    VerticalReport,
    VerticalView,
    require_scatter,
    scatter_view,
    vertical_report,
)

# The base holds every stored line of one election; the report caches one scope each.
_BASES: Final = 2
_REPORTS: Final = 32
VerticalJob: TypeAlias = Callable[[int, int, str | None, int | None, str, str], VerticalView]


def get_vertical_job() -> VerticalJob:
    return _stored_vertical


def clear_vertical_caches() -> None:
    _vertical_base.cache_clear()
    _vertical_report.cache_clear()


def _stored_vertical(
    ano: int,
    turno: int,
    uf: str | None,
    partido: int | None,
    cargo_x: str,
    cargo_y: str,
) -> VerticalView:
    year = ElectionYear(ano).value
    turn = Turno(turno).value
    code = None if uf is None else Uf(uf).code
    require_scatter(partido, cargo_x, cargo_y)
    report = _vertical_report(year, turn, code)
    scatter = scatter_view(_vertical_base(year, turn), report, partido, cargo_x, cargo_y)
    return VerticalView(report, scatter)


@lru_cache(maxsize=_BASES)
def _vertical_base(ano: int, turno: int) -> VerticalBase:
    from eleicoes.use_cases.verticalizacao import _production_reader, build_vertical_base

    reader = _production_reader()
    try:
        return build_vertical_base(reader, ano, turno)
    finally:
        reader.close()


@lru_cache(maxsize=_REPORTS)
def _vertical_report(ano: int, turno: int, uf: str | None) -> VerticalReport:
    return vertical_report(_vertical_base(ano, turno), uf)
