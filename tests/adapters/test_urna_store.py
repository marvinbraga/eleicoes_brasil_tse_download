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
