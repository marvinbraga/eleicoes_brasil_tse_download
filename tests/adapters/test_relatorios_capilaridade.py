"""Capillarity route and job: contract fields, exact labels, scopes and the cache."""

import pytest

from eleicoes.adapters.http.dependencies import clear_report_caches, get_capillarity_job
from eleicoes.domain.errors import ElectionError
from eleicoes.domain.stored_grade import StoredCell


class _Cells:
    def __init__(self, cells: tuple[StoredCell, ...]) -> None:
        self.cells = cells
        self.calls: list[tuple[int, int, str]] = []
        self.closed = False

    def municipal_cells(self, ano: int, turno: int, cargo: str) -> tuple[StoredCell, ...]:
        self.calls.append((ano, turno, cargo))
        return self.cells

    def close(self) -> None:
        self.closed = True


def _uf_cells(uf: str, start: int, partido: int, votos: int) -> tuple[StoredCell, ...]:
    return tuple(
        cell
        for i in range(start, start + 25)
        for cell in (
            StoredCell("municipio", str(i), f"M{i} ({uf})", 1000, partido, votos + i % 7, 0),
            StoredCell("municipio", str(i), f"M{i} ({uf})", 1000, 22, 90 - i % 7, 0),
        )
    )


def _counting(monkeypatch: pytest.MonkeyPatch) -> list[_Cells]:
    opened: list[_Cells] = []

    def fresh() -> _Cells:
        reader = _Cells(_uf_cells("AC", 0, 13, 10))
        opened.append(reader)
        return reader

    monkeypatch.setattr("eleicoes.use_cases.apresentar_capilaridade._production_reader", fresh)
    return opened


def test_capillarity_job_builds_once_per_key_and_closes_the_reader(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    opened = _counting(monkeypatch)
    first = get_capillarity_job()(2026, 1, "governador")
    assert get_capillarity_job()(2026, 1, "governador") is first
    assert len(opened) == 1
    assert opened[0].closed is True
    get_capillarity_job()(2026, 1, "senador")
    assert len(opened) == 2


def test_capillarity_job_does_not_cache_an_error(monkeypatch: pytest.MonkeyPatch) -> None:
    attempts: list[int] = []

    def failing() -> _Cells:
        attempts.append(1)
        raise ElectionError("database session is not configured")

    monkeypatch.setattr("eleicoes.use_cases.apresentar_capilaridade._production_reader", failing)
    for _attempt in range(2):
        with pytest.raises(ElectionError):
            get_capillarity_job()(2026, 1, "governador")
    assert len(attempts) == 2


def test_clear_report_caches_drops_the_capillarity_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    opened = _counting(monkeypatch)
    first = get_capillarity_job()(2026, 1, "governador")
    clear_report_caches()
    assert get_capillarity_job()(2026, 1, "governador") is not first
    assert len(opened) == 2
