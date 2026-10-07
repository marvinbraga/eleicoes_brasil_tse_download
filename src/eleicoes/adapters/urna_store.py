"""Writes one urna file only after the body is complete."""

from collections.abc import Callable
from pathlib import Path
from typing import Final

from eleicoes.domain.errors import TransportError
from eleicoes.ports.http import BinaryBody

_CHUNK_SIZE: Final = 256 * 1024
_ABSENT_SUFFIX: Final = ".ausente"


class PartialUrnaStore:
    def is_complete(self, path: Path) -> bool:
        return path.is_file() and path.stat().st_size > 0

    def is_marked_absent(self, path: Path) -> bool:
        return _absent_marker(path).is_file()

    def mark_absent(self, path: Path) -> Path:
        marker = _absent_marker(path)
        if marker.is_file():
            return marker
        try:
            marker.parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise TransportError("falha ao criar a pasta de destino") from exc
        partial = marker.with_name(f".{marker.name}.partial")
        try:
            partial.write_bytes(b"")
            partial.replace(marker)
        except OSError as exc:
            _discard(partial)
            raise TransportError("falha ao gravar o arquivo") from exc
        return marker

    def write(
        self,
        body: BinaryBody,
        target: Path,
        *,
        on_chunk: Callable[[int], None] | None = None,
    ) -> int:
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise TransportError("falha ao criar a pasta de destino") from exc
        partial = target.with_name(f".{target.name}.partial")
        try:
            size = _write_chunks(body, partial, on_chunk)
            partial.replace(target)
        except OSError as exc:
            _discard(partial)
            raise TransportError("falha ao gravar o arquivo") from exc
        except Exception:
            _discard(partial)
            raise
        return size


def _absent_marker(path: Path) -> Path:
    return path.with_suffix(path.suffix + _ABSENT_SUFFIX)


def _write_chunks(
    body: BinaryBody,
    partial: Path,
    on_chunk: Callable[[int], None] | None,
) -> int:
    written = 0
    with partial.open("wb") as handle:
        for chunk in body.iter_chunks(_CHUNK_SIZE):
            handle.write(chunk)
            written += len(chunk)
            if on_chunk is not None:
                on_chunk(written)
    return written


def _discard(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except OSError:
        return
