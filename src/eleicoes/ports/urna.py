"""Ports for reading divulgação JSON and storing one urna file."""

from collections.abc import Callable
from pathlib import Path
from typing import Protocol

from eleicoes.domain.urna_models import (
    BallotSection,
    DivulgacaoConfig,
    SelectedHash,
    UrnaDownloadCommand,
    UrnaLedgerRow,
    UrnaRunReport,
)
from eleicoes.domain.values import Uf
from eleicoes.ports.http import BinaryBody


class UrnaDocuments(Protocol):
    def read_config(self, payload: bytes) -> DivulgacaoConfig: ...

    def read_sections(self, payload: bytes, uf: Uf) -> tuple[BallotSection, ...]: ...

    def read_auxiliary(self, payload: bytes) -> SelectedHash | None: ...


class UrnaFileStore(Protocol):
    def is_complete(self, path: Path) -> bool: ...

    def write(
        self,
        body: BinaryBody,
        path: Path,
        *,
        on_chunk: Callable[[int], None] | None = None,
    ) -> int: ...


class UrnaLedger(Protocol):
    def append(self, destination: Path, row: UrnaLedgerRow) -> None: ...


class UrnaDownloader(Protocol):
    def execute(self, command: UrnaDownloadCommand) -> UrnaRunReport: ...
