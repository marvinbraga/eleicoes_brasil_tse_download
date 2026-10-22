"""Baixa os três zips municipais. O que o catálogo não listar entra como ausente."""

from eleicoes.domain.command import DownloadCommand
from eleicoes.domain.municipal_contract import municipal_archives
from eleicoes.domain.report import FileOutcome, RunReport, TransferStatus
from eleicoes.ports.catalog import Catalog
from eleicoes.ports.transfer import FileTransfer


class DownloadMunicipalArchives:
    def __init__(self, catalog: Catalog, transfer: FileTransfer) -> None:
        self._catalog = catalog
        self._transfer = transfer

    def execute(self, command: DownloadCommand) -> RunReport:
        listed = {item.filename: item for item in self._catalog.discover(command.request)}
        outcomes: list[FileOutcome] = []
        for wanted in municipal_archives(command.request.year):
            archive = listed.get(wanted.filename)
            if archive is None:
                outcomes.append(FileOutcome(wanted.filename, TransferStatus.MISSING))
                continue
            status = self._transfer.transfer(archive, command.destination)
            outcomes.append(FileOutcome(wanted.filename, status))
        return RunReport(tuple(outcomes))
