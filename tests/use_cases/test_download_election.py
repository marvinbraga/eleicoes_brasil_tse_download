from pathlib import Path

from tests.support import FakeCatalog, FakeHttp, FakePublication, FakeTransfer, command_for, zip_at

from eleicoes.adapters.streaming_transfer import StreamingFileTransfer
from eleicoes.domain.report import EXIT_NOT_PUBLISHED, EXIT_SUCCESS
from eleicoes.domain.values import RemoteZip
from eleicoes.use_cases.download_election import DownloadElectionArchives


def _use_case(
    *,
    published: bool,
    classic: tuple[RemoteZip, ...] = (),
    searched: tuple[RemoteZip, ...] = (),
    explicit: tuple[RemoteZip, ...] = (),
    transfer: FakeTransfer | StreamingFileTransfer | None = None,
) -> tuple[
    DownloadElectionArchives,
    FakeCatalog,
    FakeCatalog,
    FakeTransfer | StreamingFileTransfer,
]:
    classic_catalog = FakeCatalog(classic)
    year_catalog = FakeCatalog(searched)
    mover = transfer if transfer is not None else FakeTransfer()
    use_case = DownloadElectionArchives(
        publication=FakePublication(published),
        classic_catalog=classic_catalog,
        year_catalog=year_catalog,
        dataset_catalog=FakeCatalog(explicit),
        transfer=mover,
    )
    return use_case, classic_catalog, year_catalog, mover


def test_published_classic_bundle_ignores_unrelated_datasets(tmp_path: Path) -> None:
    classic = (zip_at("https://cdn.example/bu_imgbu_logjez_rdv_vscmr_2022_1t_AC.zip"),)
    searched = (
        zip_at("https://cdn.example/log_gedai.zip"),
        zip_at("https://cdn.example/outro.zip"),
    )
    use_case, classic_catalog, year_catalog, transfer = _use_case(
        published=True,
        classic=classic,
        searched=searched,
    )
    report = use_case.execute(command_for(2022, tmp_path))
    assert classic_catalog.calls == 1
    assert year_catalog.calls == 0
    assert isinstance(transfer, FakeTransfer)
    assert transfer.requested == ["bu_imgbu_logjez_rdv_vscmr_2022_1t_AC.zip"]
    assert report.downloaded == 1
    assert report.exit_code == EXIT_SUCCESS


def test_absent_classic_package_uses_the_search_catalog(tmp_path: Path) -> None:
    searched = (zip_at("https://cdn.example/log_gedai_1t_AC.zip"),)
    use_case, classic_catalog, year_catalog, transfer = _use_case(
        published=False,
        searched=searched,
    )
    report = use_case.execute(command_for(2026, tmp_path))
    assert classic_catalog.calls == 0
    assert year_catalog.calls == 1
    assert isinstance(transfer, FakeTransfer)
    assert transfer.requested == ["log_gedai_1t_AC.zip"]
    assert report.discovered == 1


def test_explicit_dataset_wins_over_a_published_classic_bundle(tmp_path: Path) -> None:
    explicit = (zip_at("https://cdn.example/only.zip"),)
    use_case, classic_catalog, year_catalog, transfer = _use_case(
        published=True,
        classic=(zip_at("https://cdn.example/classic.zip"),),
        explicit=explicit,
    )
    report = use_case.execute(
        command_for(
            2022,
            tmp_path,
            dataset_ref="resultados-2022-arquivos-transmitidos-para-totalizacao",
        )
    )
    assert classic_catalog.calls == 0
    assert year_catalog.calls == 0
    assert isinstance(transfer, FakeTransfer)
    assert transfer.requested == ["only.zip"]
    assert report.downloaded == 1


def test_empty_catalog_means_nothing_was_published(tmp_path: Path) -> None:
    use_case, _, year_catalog, transfer = _use_case(published=False)
    report = use_case.execute(command_for(2032, tmp_path))
    assert year_catalog.calls == 1
    assert isinstance(transfer, FakeTransfer)
    assert transfer.requested == []
    assert report.discovered == 0
    assert report.downloaded == 0
    assert report.skipped == 0
    assert report.missing == 0
    assert report.exit_code == EXIT_NOT_PUBLISHED


def test_http_404_is_counted_as_missing_and_does_not_abort(tmp_path: Path) -> None:
    archive = zip_at("https://cdn.example/ausente.zip")
    http = FakeHttp({archive.url: (404, b"<html>404</html>")})
    use_case, _, _, _transfer = _use_case(
        published=True,
        classic=(archive,),
        transfer=StreamingFileTransfer(http),
    )
    report = use_case.execute(command_for(2022, tmp_path))
    assert report.discovered == 1
    assert report.missing == 1
    assert report.downloaded == 0
    assert report.exit_code == EXIT_SUCCESS
    assert not (tmp_path / archive.filename).exists()
    assert list(tmp_path.iterdir()) == []
