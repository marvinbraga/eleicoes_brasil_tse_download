"""One-line CLI failure reasons."""

from eleicoes.domain.errors import ElectionError
from eleicoes.use_cases.failure import failure_line

_HEADLINE = "Não foi possível apresentar os relatórios."


def test_reason_without_cause_is_the_error_message() -> None:
    assert failure_line(_HEADLINE, ElectionError("database unavailable")) == (
        f"{_HEADLINE} Motivo: database unavailable"
    )


def test_cause_adds_only_its_first_line() -> None:
    try:
        try:
            raise ValueError("first line\nsecond line")
        except ValueError as cause:
            raise ElectionError("store failed") from cause
    except ElectionError as exc:
        line = failure_line(_HEADLINE, exc)
    assert line == f"{_HEADLINE} Motivo: store failed (first line)"


def test_blank_cause_adds_nothing() -> None:
    exc = ElectionError("store failed")
    exc.__cause__ = ValueError("")
    assert failure_line(_HEADLINE, exc) == f"{_HEADLINE} Motivo: store failed"


def test_cause_starting_with_blank_lines_uses_the_first_text() -> None:
    exc = ElectionError("store failed")
    exc.__cause__ = ValueError("\n  \nreal reason\nmore")
    assert failure_line(_HEADLINE, exc) == f"{_HEADLINE} Motivo: store failed (real reason)"


def test_implicit_context_is_not_reported() -> None:
    try:
        try:
            raise ValueError("hidden")
        except ValueError:
            raise ElectionError("store failed") from None
    except ElectionError as exc:
        line = failure_line(_HEADLINE, exc)
    assert line == f"{_HEADLINE} Motivo: store failed"
