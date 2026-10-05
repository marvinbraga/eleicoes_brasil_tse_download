from collections.abc import Iterator
from pathlib import Path
from typing import Protocol


class ArchiveMember(Protocol):
    name: str

    def read_bytes(self) -> bytes: ...


class OpenedArchive(Protocol):
    def __iter__(self) -> Iterator[ArchiveMember]: ...

    def close(self) -> None: ...


class ArchiveReader(Protocol):
    def open(self, path: Path) -> OpenedArchive: ...
