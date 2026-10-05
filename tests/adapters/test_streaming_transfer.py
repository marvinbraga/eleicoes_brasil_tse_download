from collections.abc import Iterator
from pathlib import Path

import pytest
from tests.support import FakeHttp

from eleicoes.adapters.streaming_transfer import CHUNK_SIZE, StreamingFileTransfer
from eleicoes.domain.errors import TransportError, UnexpectedHttpStatusError
from eleicoes.domain.layout import locate
from eleicoes.domain.report import TransferStatus
from eleicoes.domain.values import RemoteZip


def _archive() -> RemoteZip:
    return RemoteZip(url="https://cdn.example/urna.zip", filename="urna.zip")


def _stored(root: Path, archive: RemoteZip) -> Path:
    return root / locate(archive.filename).relative_path


def test_http_404_does_not_create_a_file_and_is_missing(tmp_path: Path) -> None:
    archive = _archive()
    http = FakeHttp({archive.url: (404, b"<html>nao encontrado</html>")})
    status = StreamingFileTransfer(http).transfer(archive, tmp_path)
    assert status is TransferStatus.MISSING
    assert list(tmp_path.iterdir()) == []
    assert http.responses[0].body.closed is True
    assert http.responses[0].body.reads == 0


def test_http_200_streams_chunks_to_disk(tmp_path: Path) -> None:
    archive = _archive()
    payload = b"abc123xyz"
    http = FakeHttp({archive.url: (200, payload)})
    nested = tmp_path / "downloads" / "2022"
    status = StreamingFileTransfer(http).transfer(archive, nested)
    body = http.responses[0].body
    assert status is TransferStatus.DOWNLOADED
    assert _stored(nested, archive).read_bytes() == payload
    assert _stored(nested, archive) == nested / "outros" / "urna.zip"
    assert body.chunk_reads == 1
    assert body.chunk_size == CHUNK_SIZE
    assert body.reads == 0
    assert body.closed is True


def test_existing_non_empty_file_is_skipped_and_not_requested(tmp_path: Path) -> None:
    archive = _archive()
    target = _stored(tmp_path, archive)
    target.parent.mkdir(parents=True)
    target.write_bytes(b"already")
    http = FakeHttp({})
    status = StreamingFileTransfer(http).transfer(archive, tmp_path)
    assert status is TransferStatus.SKIPPED
    assert http.urls == []
    assert target.read_bytes() == b"already"


def test_empty_file_is_downloaded_again(tmp_path: Path) -> None:
    archive = _archive()
    target = _stored(tmp_path, archive)
    target.parent.mkdir(parents=True)
    target.write_bytes(b"")
    http = FakeHttp({archive.url: (200, b"PK")})
    status = StreamingFileTransfer(http).transfer(archive, tmp_path)
    assert status is TransferStatus.DOWNLOADED
    assert target.read_bytes() == b"PK"


def test_http_500_does_not_create_a_file(tmp_path: Path) -> None:
    archive = _archive()
    http = FakeHttp({archive.url: (500, b"erro interno")})
    with pytest.raises(UnexpectedHttpStatusError):
        StreamingFileTransfer(http).transfer(archive, tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_disk_error_removes_the_partial_file(tmp_path: Path) -> None:
    archive = _archive()
    blocker = tmp_path / "nao-e-pasta"
    blocker.write_text("x", encoding="utf-8")
    http = FakeHttp({archive.url: (200, b"PK")})
    with pytest.raises(TransportError):
        StreamingFileTransfer(http).transfer(archive, blocker / "filho")
    assert not (tmp_path / ".urna.zip.partial").exists()


class _ExplodingBody:
    def iter_chunks(self, chunk_size: int) -> Iterator[bytes]:
        del chunk_size
        yield b"parcial"
        raise OSError("disco cheio")

    def read_bytes(self) -> bytes:
        return b""

    def close(self) -> None:
        return None


class _ExplodingResponse:
    status_code = 200

    def __init__(self) -> None:
        self.body = _ExplodingBody()


class _ExplodingHttp:
    def get(self, url: str) -> _ExplodingResponse:
        del url
        return _ExplodingResponse()


def test_os_error_during_write_discards_partial(tmp_path: Path) -> None:
    with pytest.raises(TransportError):
        StreamingFileTransfer(_ExplodingHttp()).transfer(_archive(), tmp_path)
    assert list(tmp_path.rglob("*.partial")) == []
    assert list(tmp_path.rglob("*.zip")) == []


class _BoomBody:
    def iter_chunks(self, chunk_size: int) -> Iterator[bytes]:
        del chunk_size
        raise TransportError("rede caiu")

    def read_bytes(self) -> bytes:
        return b""

    def close(self) -> None:
        return None


class _BoomResponse:
    status_code = 200
    body = _BoomBody()


class _BoomHttp:
    def get(self, url: str) -> _BoomResponse:
        del url
        return _BoomResponse()


def test_unexpected_stream_error_discards_partial(tmp_path: Path) -> None:
    with pytest.raises(TransportError):
        StreamingFileTransfer(_BoomHttp()).transfer(_archive(), tmp_path)
    assert list(tmp_path.rglob("*.partial")) == []
    assert list(tmp_path.rglob("*.zip")) == []
