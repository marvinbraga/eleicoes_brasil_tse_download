from pathlib import Path

import pytest

from eleicoes.domain.errors import ElectionError, InvalidGenerationError
from eleicoes.domain.importing import (
    Generation,
    ImportCommand,
    ImportReport,
    ImportStatus,
    MemberOutcome,
)
from eleicoes.domain.report import EXIT_FAILURE, EXIT_NOT_PUBLISHED, EXIT_SUCCESS
from eleicoes.domain.values import ElectionYear


def test_later_calendar_day_is_a_newer_generation() -> None:
    older = Generation.from_filename("CESP_1t_AC_031020261534.zip")
    newer = Generation.from_filename("csec_1t_AC_041020261259.csv")
    assert newer.at > older.at
    assert newer.stamp == "041020261259"


def test_september_is_older_than_october_even_though_the_text_sorts_the_other_way() -> None:
    september = Generation.from_filename("CESP_1t_AC_300920261200.zip")
    october = Generation.from_filename("CESP_1t_AC_041020261200.zip")
    assert september.at < october.at


def test_filename_without_a_stamp_is_rejected() -> None:
    with pytest.raises(InvalidGenerationError):
        Generation.from_filename("leiame.pdf")
    with pytest.raises(ElectionError):
        Generation.from_filename("CESP_1t_AC_321320261200.zip")


def test_report_exit_code_follows_loaded_and_failed() -> None:
    ignored = _outcome(ImportStatus.IGNORED)
    loaded = _outcome(ImportStatus.LOADED)
    failed = _outcome(ImportStatus.FAILED)
    assert ImportReport((ignored,)).exit_code == EXIT_NOT_PUBLISHED
    assert ImportReport(()).exit_code == EXIT_NOT_PUBLISHED
    assert ImportReport((loaded, ignored)).exit_code == EXIT_SUCCESS
    assert ImportReport((loaded, failed)).exit_code == EXIT_FAILURE


def test_import_command_keeps_year_and_origin() -> None:
    command = ImportCommand(year=ElectionYear(2026), origin=Path("downloads/2026"))
    assert command.year.value == 2026
    assert command.origin == Path("downloads/2026")


def _outcome(status: ImportStatus) -> MemberOutcome:
    return MemberOutcome("a.zip", "a.csv", status, 1, "csec")
