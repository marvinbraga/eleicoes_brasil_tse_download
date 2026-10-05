from pathlib import Path
from typing import Protocol

from eleicoes.domain.report import TransferStatus
from eleicoes.domain.values import RemoteZip


class FileTransfer(Protocol):
    def transfer(self, archive: RemoteZip, destination: Path) -> TransferStatus: ...
