from pathlib import Path

import pytest

from eleicoes.composition.cli import main
from eleicoes.domain.errors import DatabaseConfigError, ElectionError
from eleicoes.domain.importing import ImportCommand, ImportReport, ImportStatus, MemberOutcome
from eleicoes.domain.values import ElectionYear


def test_import_uses_origem_and_prints_the_summary(capsys: pytest.CaptureFixture[str]) -> None:
    report = ImportReport((_loaded(), _ignored()))
    importer = _Importer(report)
    code = main(
        ["import", "--ano", "2026", "--origem", "downloads/2026"],
        environ={},
        importer=importer,
    )
    captured = capsys.readouterr()
    assert code == 0
    assert importer.command == ImportCommand(ElectionYear(2026), Path("downloads/2026"))
    assert "Importação concluída: 1 tabelas, 3 linhas, 1 ignorados." in captured.out
    assert importer.closed is True


def test_import_without_tabular_files_exits_2(capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["import", "--ano", "2026"], environ={}, importer=_Importer(ImportReport(())))
    assert code == 2
    assert "Nenhum arquivo tabular" in capsys.readouterr().out


def test_import_origin_falls_back_to_the_output_directory(tmp_path: Path) -> None:
    importer = _Importer(ImportReport((_loaded(),)))
    main(["import", "--ano", "2026"], environ={"DIRETORIO_SAIDA": str(tmp_path)}, importer=importer)
    assert importer.command is not None
    assert importer.command.origin == tmp_path


def test_import_rejects_a_year_outside_the_guard(capsys: pytest.CaptureFixture[str]) -> None:
    importer = _Importer(ImportReport(()))
    code = main(["import", "--ano", "1800"], environ={}, importer=importer)
    assert code == 1
    assert importer.command is None
    assert "Ano inválido" in capsys.readouterr().err


def test_import_translates_database_configuration(capsys: pytest.CaptureFixture[str]) -> None:
    importer = _Importer(ImportReport(()), error=DatabaseConfigError(("POSTGRES_HOST",)))
    code = main(["import", "--ano", "2026"], environ={}, importer=importer)
    assert code == 1
    assert "Postgres" in capsys.readouterr().err
    assert importer.closed is True


def test_import_hides_unexpected_driver_errors(capsys: pytest.CaptureFixture[str]) -> None:
    importer = _Importer(ImportReport(()), error=RuntimeError("connection refused"))
    code = main(["import", "--ano", "2026"], environ={}, importer=importer)
    assert code == 1
    assert "Não foi possível concluir a importação." in capsys.readouterr().err
    assert "connection refused" not in capsys.readouterr().err
    assert importer.closed is True


def test_generic_domain_error_stays_in_portuguese(capsys: pytest.CaptureFixture[str]) -> None:
    importer = _Importer(ImportReport(()), error=ElectionError("boom"))
    code = main(["import", "--ano", "2026"], environ={}, importer=importer)
    assert code == 1
    assert "Não foi possível concluir a importação." in capsys.readouterr().err


class _Importer:
    def __init__(self, report: ImportReport, error: Exception | None = None) -> None:
        self.report = report
        self.error = error
        self.command: ImportCommand | None = None
        self.closed = False

    def execute(self, command: ImportCommand) -> ImportReport:
        self.command = command
        if self.error is not None:
            raise self.error
        return self.report

    def close(self) -> None:
        self.closed = True


def _loaded() -> MemberOutcome:
    return MemberOutcome("a.zip", "csec.csv", ImportStatus.LOADED, 3, "csec")


def _ignored() -> MemberOutcome:
    return MemberOutcome("a.zip", "leiame.pdf", ImportStatus.IGNORED, 0, "")
