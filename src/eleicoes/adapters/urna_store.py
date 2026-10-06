"""Writes one urna file only after the body is complete."""

from pathlib import Path
from typing import Final

from eleicoes.domain.errors import TransportError
from eleicoes.ports.http import BinaryBody

_CHUNK_SIZE: Final = 256 * 1024


class PartialUrnaStore:
    def is_complete(self, path: Path) -> bool:
        return path.is_file() and path.stat().st_size > 0

    def write(self, body: BinaryBody, target: Path) -> int:
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise TransportError("falha ao criar a pasta de destino") from exc
        partial = target.with_name(f".{target.name}.partial")
        try:
            size = _write_chunks(body, partial)
            partial.replace(target)
        except OSError as exc:
            _discard(partial)
            raise TransportError("falha ao gravar o arquivo") from exc
        except Exception:
            _discard(partial)
            raise
        return size


def _write_chunks(body: BinaryBody, partial: Path) -> int:
    written = 0
    with partial.open("wb") as handle:
        for chunk in body.iter_chunks(_CHUNK_SIZE):
            handle.write(chunk)
            written += len(chunk)
    return written


def _discard(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except OSError:
        return
