from collections.abc import Iterator
from pathlib import Path

import pytest
from tests.support import FakeBody

from eleicoes.adapters.urna_store import PartialUrnaStore
from eleicoes.domain.errors import TransportError


def test_partial_marker_is_not_a_finished_file(tmp_path: Path) -> None:
    target = tmp_path / "bu.dat"
    partial = target.with_name(f".{target.name}.partial")
    partial.write_bytes(b"half")
    store = PartialUrnaStore()
    assert store.is_complete(target) is False
    assert store.is_complete(partial) is True


class _ExplodingBody:
    def iter_chunks(self, chunk_size: int) -> Iterator[bytes]:
        del chunk_size
        yield b"parcial"
        raise OSError("disco cheio")

    def read_bytes(self) -> bytes:
        return b""

    def close(self) -> None:
        return None


def test_failed_write_removes_the_partial_and_a_later_body_lands(tmp_path: Path) -> None:
    target = tmp_path / "zona" / "bu.dat"
    store = PartialUrnaStore()
    with pytest.raises(TransportError):
        store.write(_ExplodingBody(), target)
    assert not target.exists()
    assert list(tmp_path.rglob("*.partial")) == []
    assert store.write(FakeBody(b"abc"), target) == 3
    assert target.read_bytes() == b"abc"


def test_empty_file_is_not_complete(tmp_path: Path) -> None:
    target = tmp_path / "bu.dat"
    target.write_bytes(b"")
    assert PartialUrnaStore().is_complete(target) is False


def test_absent_marker_is_an_empty_sibling_and_a_second_call_keeps_it(tmp_path: Path) -> None:
    target = tmp_path / "zona" / "o03220ma0843500500102-imgbu.dat"
    store = PartialUrnaStore()
    assert store.is_marked_absent(target) is False
    marker = store.mark_absent(target)
    assert marker == target.with_name("o03220ma0843500500102-imgbu.dat.ausente")
    assert marker.read_bytes() == b""
    assert not target.exists()
    assert store.is_complete(target) is False
    assert store.is_marked_absent(target) is True
    marker.write_bytes(b"keep")
    assert store.mark_absent(target) == marker
    assert marker.read_bytes() == b"keep"
    assert not target.exists()
    assert list(tmp_path.rglob("*.partial")) == []


def test_write_reports_cumulative_bytes_after_every_chunk(tmp_path: Path) -> None:
    seen: list[int] = []
    body = FakeBody(b"abcdef")
    target = tmp_path / "zona" / "bu.dat"
    size = PartialUrnaStore().write(body, target, on_chunk=seen.append)
    assert size == 6
    assert seen == [3, 6]
    assert body.chunk_size == 256 * 1024
    assert target.read_bytes() == b"abcdef"


def test_empty_body_does_not_require_a_chunk_callback(tmp_path: Path) -> None:
    seen: list[int] = []
    target = tmp_path / "bu.dat"
    assert PartialUrnaStore().write(FakeBody(b""), target, on_chunk=seen.append) == 0
    assert seen == []
    assert target.read_bytes() == b""
