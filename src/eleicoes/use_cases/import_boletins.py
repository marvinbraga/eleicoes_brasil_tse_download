"""Lê os bu.dat de uma UF e só então substitui essa UF no destino."""

from pathlib import Path
from typing import Final

from eleicoes.domain.boletim import Boletim, BoletimImportReport, ImportBoletinsCommand
from eleicoes.domain.errors import ElectionError, InvalidBoletimError
from eleicoes.ports.boletim import BoletimReader, BoletimSink

_SECTION_BULLETIN: Final = "*/*/*/*-bu.dat"


class ImportBoletins:
    """Chama o leitor e o destino direto. Um arquivo inválido não grava a UF."""

    def __init__(self, reader: BoletimReader, sink: BoletimSink) -> None:
        self._reader = reader
        self._sink = sink

    def execute(self, command: ImportBoletinsCommand) -> BoletimImportReport:
        paths = _bulletin_paths(command.origin)
        if not paths:
            return BoletimImportReport(0, 0)
        parsed = tuple(self._read(command.origin, path) for path in paths)
        self._sink.ensure_model()
        votos = self._sink.replace_uf(command.year, command.turno, command.uf, parsed)
        return BoletimImportReport(len(parsed), votos)

    def close(self) -> None:
        self._sink.close()

    def _read(self, origin: Path, path: Path) -> Boletim:
        arquivo = path.relative_to(origin).as_posix()
        payload = _payload(arquivo, path)
        try:
            return self._reader.read(arquivo, payload)
        except InvalidBoletimError:
            raise
        except ElectionError as exc:
            raise InvalidBoletimError(arquivo) from exc


def _bulletin_paths(origin: Path) -> tuple[Path, ...]:
    if not origin.is_dir():
        return ()
    found = [path for path in origin.glob(_SECTION_BULLETIN) if path.is_file()]
    return tuple(sorted(found))


def _payload(arquivo: str, path: Path) -> bytes:
    try:
        return path.read_bytes()
    except OSError as exc:
        raise InvalidBoletimError(arquivo) from exc
