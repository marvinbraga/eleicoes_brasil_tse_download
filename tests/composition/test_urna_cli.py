from pathlib import Path

import pytest
from tests.urna_fakes import QueueHttp

from eleicoes.composition.cli import main
from eleicoes.composition.wiring import build_urna_download
from eleicoes.domain.errors import (
    TransportError,
    TseBlockedError,
    UnexpectedTsePayloadError,
)
from eleicoes.domain.report import EXIT_NOT_PUBLISHED, EXIT_SUCCESS
from eleicoes.domain.urna_models import UrnaDownloadCommand, UrnaRunReport
from eleicoes.domain.values import ElectionYear, Turno, Uf


class _RecordingUrna:
    def __init__(self, report: UrnaRunReport) -> None:
        self.report = report
        self.command: UrnaDownloadCommand | None = None

    def execute(self, command: UrnaDownloadCommand) -> UrnaRunReport:
        self.command = command
        return self.report


def test_urnas_defaults_match_the_download_scope(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    app = _RecordingUrna(UrnaRunReport(0, 0, 0, (1, 2)))
    code = main(["urnas", "--ano", "2026"], environ={"DIRETORIO_SAIDA": str(tmp_path)}, urnas=app)
    captured = capsys.readouterr()
    assert code == EXIT_NOT_PUBLISHED
    assert app.command is not None
    assert app.command.year == ElectionYear(2026)
    assert app.command.destination == tmp_path
    assert len(app.command.turnos) == 2
    assert len(app.command.ufs) == 28
    assert "O TSE ainda não publicou os arquivos de urna deste turno." in captured.out


def test_urnas_accepts_turno_uf_and_destination(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    app = _RecordingUrna(UrnaRunReport(1, 2, 0, (2,)))
    code = main(
        ["urnas", "--ano", "2026", "--turno", "1", "--uf", "ac", "--destino", str(tmp_path)],
        environ={},
        urnas=app,
    )
    captured = capsys.readouterr()
    assert code == EXIT_SUCCESS
    assert app.command is not None
    assert app.command.turnos == (Turno(1),)
    assert app.command.ufs == (Uf("AC"),)
    assert app.command.destination == tmp_path
    assert "Baixados: 1" in captured.out
    assert "Ignorados: 2" in captured.out
    assert "O TSE ainda não publicou os arquivos de urna deste turno." in captured.out


def test_urnas_translates_year_turno_block_and_payload(
    capsys: pytest.CaptureFixture[str],
) -> None:
    idle = _RecordingUrna(UrnaRunReport(0, 0, 0, ()))
    year = main(["urnas", "--ano", "1800"], environ={}, urnas=idle)
    assert year == 1
    assert "Ano inválido" in capsys.readouterr().err

    turno = main(["urnas", "--ano", "2026", "--turno", "9"], environ={}, urnas=idle)
    assert turno == 1
    assert "Turno inválido" in capsys.readouterr().err

    class _Blocked:
        def execute(self, command: UrnaDownloadCommand) -> UrnaRunReport:
            del command
            raise TseBlockedError()

    blocked = main(["urnas", "--ano", "2026"], environ={}, urnas=_Blocked())
    assert blocked == 1
    assert "excesso de requisições" in capsys.readouterr().err

    class _Payload:
        def execute(self, command: UrnaDownloadCommand) -> UrnaRunReport:
            del command
            raise UnexpectedTsePayloadError()

    payload = main(["urnas", "--ano", "2026"], environ={}, urnas=_Payload())
    assert payload == 1
    assert "Resposta do TSE fora do formato esperado." in capsys.readouterr().err

    class _Offline:
        def execute(self, command: UrnaDownloadCommand) -> UrnaRunReport:
            del command
            raise TransportError("x")

    offline = main(["urnas", "--ano", "2026"], environ={}, urnas=_Offline())
    assert offline == 1
    assert "Falha de rede" in capsys.readouterr().err


def test_invalid_uf_is_portuguese(capsys: pytest.CaptureFixture[str]) -> None:
    code = main(
        ["urnas", "--ano", "2026", "--uf", "XX"],
        environ={},
        urnas=_RecordingUrna(UrnaRunReport(0, 0, 0, ())),
    )
    assert code == 1
    assert "UF inválida" in capsys.readouterr().err


def test_factory_wires_a_fake_http_client(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "eleicoes.composition.wiring.RequestsHttpClient",
        lambda: (_ for _ in ()).throw(AssertionError("socket")),
    )
    app = build_urna_download(QueueHttp({}))
    assert app.__class__.__name__ == "DownloadUrnaFiles"


def test_factory_without_a_client_builds_the_requests_adapter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("eleicoes.composition.wiring.RequestsHttpClient", lambda: QueueHttp({}))
    app = build_urna_download()
    assert app.__class__.__name__ == "DownloadUrnaFiles"
