from typing import Protocol

from eleicoes.domain.command import DownloadCommand
from eleicoes.domain.report import RunReport


class ElectionDownloader(Protocol):
    def execute(self, command: DownloadCommand) -> RunReport: ...
