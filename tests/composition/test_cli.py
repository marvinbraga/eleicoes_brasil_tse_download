from pathlib import Path

import pytest
from tests.support import FakeCatalog, FakePublication, FakeTransfer, MemoryGateway, RecordingApp

from eleicoes.adapters.ckan_catalog import CkanExplicitCatalog
from eleicoes.composition.cli import main
from eleicoes.domain.errors import ElectionError
from eleicoes.domain.report import FileOutcome, RunReport, TransferStatus
from eleicoes.domain.values import ElectionYear
from eleicoes.use_cases.download_election import DownloadElectionArchives


def test_cli_argument_overrides_environment_year(capsys: pytest.CaptureFixture[str]) -> None:
    app = RecordingApp(RunReport(()))
    code = main(["download", "--ano", "2024"], environ={"ANO_ELEICAO": "2022"}, app=app)
    captured = capsys.readouterr()
    assert code == 2
    assert app.command is not None
    assert app.command.request.year == ElectionYear(2024)
    assert app.command.destination == Path("downloads/2024")
    assert "Nenhum arquivo publicado" in captured.out


def test_cli_reports_counts_in_portuguese(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    report = RunReport(
        (
            FileOutcome("bu_imgbu_logjez_rdv_vscmr_2022_1t_AC.zip", TransferStatus.DOWNLOADED),
            FileOutcome("b.zip", TransferStatus.SKIPPED),
            FileOutcome("c.zip", TransferStatus.MISSING),
        )
    )
    code = main(
        ["download", "--ano", "2022", "--destino", str(tmp_path)],
        environ={},
        app=RecordingApp(report),
    )
    captured = capsys.readouterr()
    assert code == 0
    assert "Arquivos encontrados: 3" in captured.out
    assert "Baixados: 1" in captured.out
    assert "Ignorados: 1" in captured.out
    assert "Ausentes: 1" in captured.out
    assert f"Índice: {tmp_path / 'indice.csv'}" in captured.out
    index = (tmp_path / "indice.csv").read_text(encoding="utf-8")
    assert "totalizacao,1,AC,bu_imgbu_logjez_rdv_vscmr_2022_1t_AC.zip" in index


def test_cli_rejects_a_year_outside_the_guard(capsys: pytest.CaptureFixture[str]) -> None:
    app = RecordingApp(RunReport(()))
    code = main(["download", "--ano", "1800"], environ={"ANO_ELEICAO": "2022"}, app=app)
    captured = capsys.readouterr()
    assert code == 1
    assert app.command is None
    assert "Ano inválido" in captured.err


def test_cli_requires_a_year_somewhere(capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["download"], environ={}, app=RecordingApp(RunReport(())))
    captured = capsys.readouterr()
    assert code == 1
    assert "ANO_ELEICAO" in captured.err


def test_cli_translates_transport_and_generic_failures(capsys: pytest.CaptureFixture[str]) -> None:
    class Boom:
        def __init__(self, error: Exception) -> None:
            self.error = error

        def execute(self, command: object) -> RunReport:
            del command
            raise self.error

    code = main(["download", "--ano", "2022"], environ={}, app=Boom(ElectionError("x")))
    assert code == 1
    assert "Não foi possível concluir" in capsys.readouterr().err


def test_invalid_dataset_ref_does_not_traceback(capsys: pytest.CaptureFixture[str]) -> None:
    use_case = DownloadElectionArchives(
        publication=FakePublication(True),
        classic_catalog=FakeCatalog(()),
        year_catalog=FakeCatalog(()),
        dataset_catalog=CkanExplicitCatalog(MemoryGateway()),
        transfer=FakeTransfer(),
    )
    code = main(
        ["download", "--ano", "2022"],
        environ={"TSE_DATASET_URL": "https://example.com/"},
        app=use_case,
    )
    captured = capsys.readouterr()
    assert code == 1
    assert "TSE_DATASET_URL" in captured.err


def test_usage_error_reserves_exit_code_2_for_an_empty_catalog() -> None:
    with pytest.raises(SystemExit) as caught:
        main(["sem-comando"])
    assert caught.value.code == 1


def test_main_reads_the_process_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("eleicoes.composition.cli.load_dotenv", lambda: False)
    monkeypatch.setenv("ANO_ELEICAO", "2024")
    monkeypatch.delenv("TSE_URL", raising=False)
    monkeypatch.delenv("TSE_DATASET_URL", raising=False)
    monkeypatch.delenv("DIRETORIO_SAIDA", raising=False)
    app = RecordingApp(RunReport(()))
    code = main(["download"], app=app)
    assert code == 2
    assert app.command is not None
    assert app.command.request.year == ElectionYear(2024)
    assert app.command.request.dataset_ref is None
