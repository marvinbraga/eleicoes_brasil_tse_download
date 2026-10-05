from eleicoes.domain.command import DownloadCommand
from eleicoes.domain.report import FileOutcome, RunReport
from eleicoes.domain.values import DiscoveryRequest, RemoteZip
from eleicoes.ports.catalog import Catalog
from eleicoes.ports.publication import TotalizacaoPublication
from eleicoes.ports.transfer import FileTransfer


class DownloadElectionArchives:
    """Descobre os zips de uma eleição e transfere cada um para o destino."""

    def __init__(
        self,
        publication: TotalizacaoPublication,
        classic_catalog: Catalog,
        year_catalog: Catalog,
        dataset_catalog: Catalog,
        transfer: FileTransfer,
    ) -> None:
        self._publication = publication
        self._classic_catalog = classic_catalog
        self._year_catalog = year_catalog
        self._dataset_catalog = dataset_catalog
        self._transfer = transfer

    def execute(self, command: DownloadCommand) -> RunReport:
        archives = self._discover(command.request)
        outcomes = tuple(self._transfer_one(archive, command) for archive in archives)
        return RunReport(outcomes)

    def _discover(self, request: DiscoveryRequest) -> tuple[RemoteZip, ...]:
        # The classic template always emits URLs, including for files TSE has not
        # published. Prefer it only when the totalização package exists; otherwise
        # those 404s would hide the zip bundles CKAN has actually listed.
        if request.dataset_ref is not None:
            return self._dataset_catalog.discover(request)
        if self._publication.is_published(request.year):
            return self._classic_catalog.discover(request)
        return self._year_catalog.discover(request)

    def _transfer_one(self, archive: RemoteZip, command: DownloadCommand) -> FileOutcome:
        status = self._transfer.transfer(archive, command.destination)
        return FileOutcome(filename=archive.filename, status=status)
