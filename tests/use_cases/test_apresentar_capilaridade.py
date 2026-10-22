"""Capillarity use case: validates first, reads once, 409 without stored cells."""

import pytest

from eleicoes.domain.errors import InvalidCargoError, InvalidTurnoError, MissingPowerReportError
from eleicoes.domain.stored_grade import StoredCell
from eleicoes.use_cases.apresentar_capilaridade import build_capillarity


class _Cells:
    def __init__(self, cells: tuple[StoredCell, ...]) -> None:
        self.cells = cells
        self.calls: list[tuple[int, int, str]] = []

    def municipal_cells(self, ano: int, turno: int, cargo: str) -> tuple[StoredCell, ...]:
        self.calls.append((ano, turno, cargo))
        return self.cells

    def close(self) -> None:
        return None


def _cells() -> tuple[StoredCell, ...]:
    return tuple(
        StoredCell("municipio", str(i), f"M{i} (AC)", 100, partido, votos, 0)
        for i in range(25)
        for partido, votos in ((13, 10 + i), (22, 90 - i))
    )


def test_builds_every_scope_from_one_read() -> None:
    reader = _Cells(_cells())
    report = build_capillarity(reader, 2026, 1, "governador")
    assert reader.calls == [(2026, 1, "governador")]
    assert report.view(None, None).municipios == 25
    assert report.view(None, "AC").scope.nome == "Acre"


def test_without_cells_is_missing_power_report() -> None:
    with pytest.raises(MissingPowerReportError):
        build_capillarity(_Cells(()), 2026, 1, "senador")


def test_validates_before_reading() -> None:
    reader = _Cells(_cells())
    with pytest.raises(InvalidCargoError):
        build_capillarity(reader, 2026, 1, "prefeito")
    with pytest.raises(InvalidTurnoError):
        build_capillarity(reader, 2026, 9, "senador")
    assert reader.calls == []
