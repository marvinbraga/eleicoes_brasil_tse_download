from collections.abc import Sequence
from pathlib import Path

import pytest
from tests.boletim_fakes import bulletin

from eleicoes.adapters.asn1.boletim_reader import Asn1BoletimReader
from eleicoes.composition.cli import main
from eleicoes.composition.wiring import build_boletim_import
from eleicoes.domain.boletim import Boletim, BoletimImportReport, ImportBoletinsCommand
from eleicoes.domain.errors import DatabaseConfigError, ElectionError, InvalidBoletimError
from eleicoes.domain.report import EXIT_NOT_PUBLISHED, EXIT_SUCCESS
from eleicoes.domain.values import ElectionYear, Turno, Uf


def test_boletins_prints_the_portuguese_summary(capsys: pytest.CaptureFixture[str]) -> None:
    app = _Boletins(BoletimImportReport(2, 15))
    code = main(
        ["boletins", "--ano", "2026", "--turno", "1", "--uf", "ac"],
        environ={},
        boletins=app,
    )
    captured = capsys.readouterr()
    assert code == EXIT_SUCCESS
    assert app.command == ImportBoletinsCommand(
        ElectionYear(2026),
        Turno(1),
        Uf("AC"),
        Path("downloads/2026/arquivo-urna/turno-1/AC"),
    )
    assert "Boletins gravados: 2. Votos: 15." in captured.out
    assert "[ausente]" not in captured.out
    assert app.closed is True


def test_boletins_lists_absent_files_before_the_summary(
    capsys: pytest.CaptureFixture[str],
) -> None:
    app = _Boletins(BoletimImportReport(1, 4, ("imgbu.dat",)))
    code = main(
        ["boletins", "--ano", "2026", "--turno", "1", "--uf", "AC"],
        environ={},
        boletins=app,
    )
    assert code == EXIT_SUCCESS
    assert capsys.readouterr().out == "[ausente] imgbu.dat\nBoletins gravados: 1. Votos: 4.\n"


def test_boletins_without_files_exits_2(capsys: pytest.CaptureFixture[str]) -> None:
    code = main(
        ["boletins", "--ano", "2026", "--turno", "1", "--uf", "AC"],
        environ={},
        boletins=_Boletins(BoletimImportReport(0, 0)),
    )
    assert code == EXIT_NOT_PUBLISHED
    assert "Nenhum boletim de urna encontrado." in capsys.readouterr().out


def test_boletins_uses_the_output_directory_and_any_election_year(tmp_path: Path) -> None:
    app = _Boletins(BoletimImportReport(1, 1))
    main(
        ["boletins", "--turno", "2", "--uf", "AL"],
        environ={"ANO_ELEICAO": "2024", "DIRETORIO_SAIDA": str(tmp_path)},
        boletins=app,
    )
    assert app.command is not None
    assert app.command.year == ElectionYear(2024)
    assert app.command.origin == tmp_path / "arquivo-urna" / "turno-2" / "AL"


def test_boletins_requires_turno_and_uf_in_portuguese(capsys: pytest.CaptureFixture[str]) -> None:
    app = _Boletins(BoletimImportReport(0, 0))
    missing_turno = main(["boletins", "--ano", "2026", "--uf", "AC"], environ={}, boletins=app)
    assert missing_turno == 1
    assert "Turno inválido" in capsys.readouterr().err
    assert app.command is None

    invalid_turno = main(
        ["boletins", "--ano", "2026", "--turno", "9", "--uf", "AC"],
        environ={},
        boletins=app,
    )
    assert invalid_turno == 1

    missing_uf = main(["boletins", "--ano", "2026", "--turno", "1"], environ={}, boletins=app)
    assert missing_uf == 1
    assert "UF inválida" in capsys.readouterr().err

    invalid_year = main(
        ["boletins", "--ano", "1800", "--turno", "1", "--uf", "AC"],
        environ={},
        boletins=app,
    )
    assert invalid_year == 1
    assert "Ano inválido" in capsys.readouterr().err


def test_boletins_names_the_invalid_file(capsys: pytest.CaptureFixture[str]) -> None:
    app = _Boletins(
        BoletimImportReport(0, 0),
        error=InvalidBoletimError("01104/0005/0028/o-bu.dat"),
    )
    code = main(
        ["boletins", "--ano", "2026", "--turno", "1", "--uf", "AC"],
        environ={},
        boletins=app,
    )
    assert code == 1
    assert "Boletim inválido: 01104/0005/0028/o-bu.dat." in capsys.readouterr().err
    assert app.closed is True


def test_boletins_hides_driver_errors(capsys: pytest.CaptureFixture[str]) -> None:
    database = _Boletins(BoletimImportReport(0, 0), error=DatabaseConfigError(("POSTGRES_HOST",)))
    code = main(
        ["boletins", "--ano", "2026", "--turno", "1", "--uf", "AC"],
        environ={},
        boletins=database,
    )
    assert code == 1
    assert "Postgres" in capsys.readouterr().err

    unexpected = _Boletins(BoletimImportReport(0, 0), error=RuntimeError("connection refused"))
    code = main(
        ["boletins", "--ano", "2026", "--turno", "1", "--uf", "AC"],
        environ={},
        boletins=unexpected,
    )
    captured = capsys.readouterr()
    assert code == 1
    assert "Não foi possível concluir a importação dos boletins." in captured.err
    assert "connection refused" not in captured.err
    assert unexpected.closed is True


def test_boletins_generic_domain_error_stays_in_portuguese(
    capsys: pytest.CaptureFixture[str],
) -> None:
    app = _Boletins(BoletimImportReport(0, 0), error=ElectionError("boom"))
    code = main(
        ["boletins", "--ano", "2026", "--turno", "1", "--uf", "AC"],
        environ={},
        boletins=app,
    )
    assert code == 1
    assert "Não foi possível concluir a importação dos boletins." in capsys.readouterr().err


def test_factory_reports_an_empty_directory(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    code = main(
        ["boletins", "--ano", "2026", "--turno", "1", "--uf", "AC"],
        environ={"DIRETORIO_SAIDA": str(tmp_path)},
    )
    assert code == EXIT_NOT_PUBLISHED
    assert "Nenhum boletim de urna encontrado." in capsys.readouterr().out


def test_factory_rejects_a_bad_file_without_rewriting_it(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    section = tmp_path / "arquivo-urna" / "turno-1" / "AC" / "01104" / "0005" / "0028"
    section.mkdir(parents=True)
    target = section / "x-bu.dat"
    target.write_bytes(b"not-asn1")
    code = main(
        ["boletins", "--ano", "2026", "--turno", "1", "--uf", "AC"],
        environ={"DIRETORIO_SAIDA": str(tmp_path)},
    )
    captured = capsys.readouterr()
    assert code == 1
    assert "Boletim inválido: 01104/0005/0028/x-bu.dat." in captured.err
    assert "not-asn1" not in captured.err
    assert target.read_bytes() == b"not-asn1"


def test_factory_uses_the_published_port_when_compose_host_is_hidden(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: dict[str, str] = {}

    def connect(env: object) -> _QuietConnection:
        assert isinstance(env, dict)
        seen.update(env)
        return _QuietConnection()

    def skip_compile(self: Asn1BoletimReader) -> None:
        del self

    def read_empty(self: Asn1BoletimReader, arquivo: str, payload: bytes) -> Boletim:
        del self, payload
        return bulletin(arquivo, votos=())

    monkeypatch.setattr("eleicoes.composition.wiring.connect_postgres", connect)
    monkeypatch.setattr("eleicoes.composition.correspondencia._resolves", lambda _host: False)
    monkeypatch.setattr(Asn1BoletimReader, "__init__", skip_compile)
    monkeypatch.setattr(Asn1BoletimReader, "read", read_empty)
    section = tmp_path / "arquivo-urna" / "turno-1" / "AC" / "01104" / "0005" / "0028"
    section.mkdir(parents=True)
    (section / "x-bu.dat").write_bytes(b"x")
    app = build_boletim_import(
        {
            "POSTGRES_HOST": "postgres",
            "POSTGRES_PORT": "5432",
            "POSTGRES_PUBLISH_PORT": "25432",
            "POSTGRES_DB": "eleicoes",
            "POSTGRES_USER": "eleicoes",
            "POSTGRES_PASSWORD": "secret",
            "DIRETORIO_SAIDA": str(tmp_path),
        }
    )
    report = app.execute(
        ImportBoletinsCommand(
            ElectionYear(2026),
            Turno(1),
            Uf("AC"),
            tmp_path / "arquivo-urna" / "turno-1" / "AC",
        )
    )
    app.close()
    assert report == BoletimImportReport(1, 0)
    assert seen["POSTGRES_HOST"] == "127.0.0.1"
    assert seen["POSTGRES_PORT"] == "25432"


class _QuietCursor:
    rowcount = 0

    def execute(self, query: str, params: Sequence[object] | None = None) -> None:
        del query, params

    def fetchall(self) -> tuple[()]:
        return ()

    def copy(self, statement: str) -> object:
        del statement
        raise AssertionError("empty boletim does not copy")

    def __enter__(self) -> "_QuietCursor":
        return self

    def __exit__(self, *args: object) -> None:
        return None


class _QuietConnection:
    def cursor(self) -> _QuietCursor:
        return _QuietCursor()

    def transaction(self) -> _QuietCursor:
        return _QuietCursor()

    def close(self) -> None:
        return None


class _Boletins:
    def __init__(self, report: BoletimImportReport, error: Exception | None = None) -> None:
        self.report = report
        self.error = error
        self.command: ImportBoletinsCommand | None = None
        self.closed = False

    def execute(self, command: ImportBoletinsCommand) -> BoletimImportReport:
        self.command = command
        if self.error is not None:
            raise self.error
        return self.report

    def close(self) -> None:
        self.closed = True
