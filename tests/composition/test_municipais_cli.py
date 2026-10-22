import csv
from datetime import date
from pathlib import Path

import pytest

from eleicoes.composition.cli import main
from eleicoes.domain.command import DownloadCommand
from eleicoes.domain.errors import (
    DuplicateMayorError,
    ElectionError,
    InvalidMunicipalRowError,
    SchemaOutdatedError,
)
from eleicoes.domain.importing import ImportCommand, ImportReport, ImportStatus, MemberOutcome
from eleicoes.domain.municipais import (
    Mayor,
    MunicipalBuild,
    MunicipalImportReport,
    MunicipalityResult,
)
from eleicoes.domain.report import FileOutcome, RunReport, TransferStatus
from eleicoes.domain.values import DiscoveryRequest, ElectionYear, RemoteZip
from eleicoes.use_cases.download_municipais import DownloadMunicipalArchives

_ZIPS = ("consulta_cand_2024.zip", "consulta_vagas_2024.zip", "detalhe_votacao_munzona_2024.zip")


class _Downloader:
    def __init__(self, report: RunReport) -> None:
        self.report = report
        self.command: DownloadCommand | None = None

    def execute(self, command: DownloadCommand) -> RunReport:
        self.command = command
        return self.report


class _Factory:
    def __init__(self, downloader: _Downloader) -> None:
        self.downloader = downloader
        self.overwrite: list[bool] = []

    def __call__(self, overwrite: bool) -> _Downloader:
        self.overwrite.append(overwrite)
        return self.downloader


class _Importer:
    def __init__(
        self, report: MunicipalImportReport | None = None, error: Exception | None = None
    ) -> None:
        self.report = report
        self.error = error
        self.command: ImportCommand | None = None
        self.closed = False

    def execute(self, command: ImportCommand) -> MunicipalImportReport:
        self.command = command
        if self.error is not None:
            raise self.error
        assert self.report is not None
        return self.report

    def close(self) -> None:
        self.closed = True


def _downloaded() -> _Factory:
    outcomes = tuple(FileOutcome(name, TransferStatus.DOWNLOADED) for name in _ZIPS)
    return _Factory(_Downloader(RunReport(outcomes)))


def _tables(status: ImportStatus = ImportStatus.LOADED) -> ImportReport:
    linhas = 1 if status is ImportStatus.LOADED else 0
    member = MemberOutcome(_ZIPS[1], "consulta_vagas_2024_AC.csv", status, linhas, "consulta_vagas")
    return ImportReport((member,))


def _built() -> MunicipalBuild:
    mayor = Mayor(22, "PL", "DR PEDRO", "13", date(2024, 10, 6), 1, False)
    return MunicipalBuild(
        "221020260217",
        (
            MunicipalityResult("MG", "45616", "GUAPÉ", 12000, 9, mayor),
            MunicipalityResult("MG", "48313", "MERCÊS", 9000, 9, None),
        ),
        (),
        (),
    )


def test_download_rejects_a_general_election_year(capsys: pytest.CaptureFixture[str]) -> None:
    factory = _downloaded()
    code = main(["download-municipais", "--ano", "2026"], environ={}, municipal_download=factory)
    assert code == 1
    assert "Ano sem eleição municipal. Informe um ano como 2024." in capsys.readouterr().err
    assert factory.downloader.command is None


def test_download_writes_the_index_and_prints_the_summary(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    factory = _downloaded()
    code = main(
        ["download-municipais", "--ano", "2024", "--destino", str(tmp_path)],
        environ={},
        municipal_download=factory,
    )
    out = capsys.readouterr().out
    assert code == 0
    assert "Arquivos encontrados: 3" in out
    assert factory.overwrite == [False]
    command = factory.downloader.command
    assert command is not None
    assert command.request.year == ElectionYear(2024)
    assert command.destination == tmp_path
    with (tmp_path / "indice.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert [(row["conjunto"], row["arquivo"], row["situacao"]) for row in rows] == [
        ("municipais", name, "baixado") for name in _ZIPS
    ]


def test_download_ignores_the_dataset_variables(tmp_path: Path) -> None:
    factory = _downloaded()
    main(
        ["download-municipais", "--ano", "2024", "--destino", str(tmp_path)],
        environ={"TSE_DATASET_URL": "candidatos-2024", "TSE_URL": "https://x"},
        municipal_download=factory,
    )
    command = factory.downloader.command
    assert command is not None
    assert command.request.dataset_ref is None
    assert command.request.cdn_directory is None


def test_atualizar_reaches_the_factory_as_overwrite(tmp_path: Path) -> None:
    factory = _downloaded()
    main(
        ["download-municipais", "--ano", "2024", "--destino", str(tmp_path), "--atualizar"],
        environ={},
        municipal_download=factory,
    )
    assert factory.overwrite == [True]


def test_download_with_nothing_listed_does_not_write_an_index(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    factory = _Factory(_Downloader(RunReport(())))
    code = main(
        ["download-municipais", "--ano", "2024", "--destino", str(tmp_path)],
        environ={},
        municipal_download=factory,
    )
    assert code == 2
    assert not (tmp_path / "indice.csv").exists()
    assert "Nenhum arquivo publicado" in capsys.readouterr().out


def test_import_prints_the_municipal_summary(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    importer = _Importer(MunicipalImportReport(_tables(), _built()))
    code = main(
        ["import-municipais", "--ano", "2024", "--origem", str(tmp_path)],
        environ={},
        municipal_import=importer,
    )
    assert code == 0
    assert importer.command == ImportCommand(ElectionYear(2024), tmp_path)
    assert importer.closed is True
    assert capsys.readouterr().out == (
        "Importação concluída: 1 tabelas, 1 linhas, 0 ignorados.\n"
        "Falhas: 0\n"
        "Municípios: 2. Prefeitos eleitos: 1. Sem prefeito eleito: 1. Suplementares: 0.\n"
        "Vereadores eleitos: 0. Divergências entre eleitos e vagas: 0.\n"
        "Dados do TSE gerados em 22/10/2026 às 02:17.\n"
    )


def test_import_with_failures_does_not_rebuild(capsys: pytest.CaptureFixture[str]) -> None:
    importer = _Importer(MunicipalImportReport(_tables(ImportStatus.FAILED), None))
    code = main(["import-municipais", "--ano", "2024"], environ={}, municipal_import=importer)
    assert code == 1
    assert capsys.readouterr().out == (
        "Importação concluída: 0 tabelas, 0 linhas, 0 ignorados.\n"
        "Falhas: 1\n"
        "A análise municipal não foi reconstruída por causa das falhas.\n"
    )


def test_import_without_files_points_to_the_download(capsys: pytest.CaptureFixture[str]) -> None:
    importer = _Importer(MunicipalImportReport(ImportReport(()), None))
    code = main(["import-municipais", "--ano", "2024"], environ={}, municipal_import=importer)
    assert code == 2
    assert capsys.readouterr().out == (
        "Nenhum arquivo municipal para importar. Rode download-municipais antes.\n"
    )


@pytest.mark.parametrize(
    ("error", "message"),
    [
        (
            DuplicateMayorError("MG", "45616"),
            "Há mais de um prefeito eleito em MG 45616. Confira o consulta_cand.",
        ),
        (
            InvalidMunicipalRowError("nr_partido"),
            "Valor inesperado no campo nr_partido dos dados municipais.",
        ),
        (SchemaOutdatedError(("0004",), "0005"), "make migrate"),
        (ElectionError("boom"), "Não foi possível concluir a importação."),
        (RuntimeError("connection refused"), "Não foi possível concluir a importação."),
    ],
)
def test_import_errors_are_translated(
    error: Exception, message: str, capsys: pytest.CaptureFixture[str]
) -> None:
    importer = _Importer(error=error)
    code = main(["import-municipais", "--ano", "2024"], environ={}, municipal_import=importer)
    err = capsys.readouterr().err
    assert code == 1
    assert message in err
    assert "connection refused" not in err
    assert importer.closed is True


def test_import_rejects_a_general_election_year(capsys: pytest.CaptureFixture[str]) -> None:
    importer = _Importer(MunicipalImportReport(_tables(), _built()))
    code = main(["import-municipais", "--ano", "2026"], environ={}, municipal_import=importer)
    assert code == 1
    assert importer.command is None
    assert "Ano sem eleição municipal. Informe um ano como 2024." in capsys.readouterr().err


def test_import_with_missing_members_names_them_and_fails(
    capsys: pytest.CaptureFixture[str],
) -> None:
    faltando = tuple(f"consulta_cand_2024_{uf}.csv" for uf in ("AC", "AL", "AM", "AP"))
    importer = _Importer(MunicipalImportReport(_tables(), None, faltando))
    code = main(["import-municipais", "--ano", "2024"], environ={}, municipal_import=importer)
    assert code == 1
    assert capsys.readouterr().out.splitlines()[-1] == (
        "A análise municipal não foi reconstruída: faltam 4 arquivos por UF "
        "(consulta_cand_2024_AC.csv, consulta_cand_2024_AL.csv, consulta_cand_2024_AM.csv, …). "
        "Rode download-municipais --atualizar e importe de novo."
    )


class _OneZipCatalog:
    def discover(self, request: DiscoveryRequest) -> tuple[RemoteZip, ...]:
        del request
        return (RemoteZip("https://cdn.tse.jus.br/x/consulta_cand_2024.zip", _ZIPS[0]),)


class _Transfer:
    def transfer(self, archive: RemoteZip, destination: Path) -> TransferStatus:
        del archive, destination
        return TransferStatus.DOWNLOADED


def test_download_with_zips_missing_from_the_catalog_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    def factory(overwrite: bool) -> DownloadMunicipalArchives:
        del overwrite
        return DownloadMunicipalArchives(_OneZipCatalog(), _Transfer())

    code = main(
        ["download-municipais", "--ano", "2024", "--destino", str(tmp_path)],
        environ={},
        municipal_download=factory,
    )
    captured = capsys.readouterr()
    assert code == 1
    assert "Ausentes: 2" in captured.out
    assert "não listou todos os zips municipais" in captured.err
    assert (tmp_path / "indice.csv").is_file()
