"""Abre um zip local e entrega cada membro sem extrair a pasta inteira."""

from collections.abc import Iterator
from pathlib import Path
from zipfile import BadZipFile, ZipFile

from eleicoes.domain.errors import ArchiveUnreadableError


class _ZipMember:
    name: str

    def __init__(self, name: str, archive: ZipFile) -> None:
        self.name = name
        self._archive = archive

    def read_bytes(self) -> bytes:
        return self._archive.read(self.name)


class _OpenedZip:
    def __init__(self, archive: ZipFile) -> None:
        self._archive = archive
        self._members = tuple(
            _ZipMember(info.filename, archive) for info in archive.infolist() if not info.is_dir()
        )

    def __iter__(self) -> Iterator[_ZipMember]:
        return iter(self._members)

    def close(self) -> None:
        self._archive.close()


class ZipArchiveReader:
    def open(self, path: Path) -> _OpenedZip:
        if not path.is_file():
            raise ArchiveUnreadableError(str(path))
        try:
            archive = ZipFile(path)
        except (OSError, BadZipFile) as exc:
            raise ArchiveUnreadableError(str(path)) from exc
        return _OpenedZip(archive)
