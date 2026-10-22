"""Building the vertical base validates the election before reading."""

import pytest
from tests.domain.test_verticalizacao import every_cargo

from eleicoes.domain.errors import InvalidElectionYearError, InvalidTurnoError
from eleicoes.domain.verticalizacao import VerticalLine
from eleicoes.use_cases import verticalizacao
from eleicoes.use_cases.verticalizacao import build_vertical_base


class _Source:
    def __init__(self, lines: tuple[VerticalLine, ...]) -> None:
        self.lines = lines
        self.calls: list[tuple[int, int]] = []

    def vertical_lines(self, ano: int, turno: int) -> tuple[VerticalLine, ...]:
        self.calls.append((ano, turno))
        return self.lines

    def close(self) -> None:
        return None


def test_invalid_election_fails_before_reading() -> None:
    source = _Source(every_cargo())
    with pytest.raises(InvalidTurnoError):
        build_vertical_base(source, 2026, 9)
    with pytest.raises(InvalidElectionYearError):
        build_vertical_base(source, 1800, 1)
    assert source.calls == []


def test_valid_source_builds_the_base() -> None:
    source = _Source(every_cargo("SP"))
    base = build_vertical_base(source, 2026, 1)
    assert base.ano == 2026
    assert base.scope(None) == ("SP",)
    assert source.calls == [(2026, 1)]


def test_production_reader_is_lazy_and_closes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(verticalizacao, "_environment", lambda: {})
    reader = verticalizacao._production_reader()
    assert type(reader).__name__ == "PostgresVerticalLines"
    reader.close()
