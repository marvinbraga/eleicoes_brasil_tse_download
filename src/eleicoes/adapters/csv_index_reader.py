"""Lê o indice.csv gravado pelo download e devolve só o que está no disco."""

import csv
from pathlib import Path

from eleicoes.domain.errors import ElectionError, MissingIndexError
from eleicoes.domain.importing import IndexEntry

_DOWNLOADED = "baixado"


class CsvIndexReader:
    def __init__(self, accepted: frozenset[str] = frozenset({_DOWNLOADED})) -> None:
        self._accepted = accepted

    def downloaded(self, origin: Path) -> tuple[IndexEntry, ...]:
        index = origin / "indice.csv"
        if not index.is_file():
            raise MissingIndexError(str(index))
        entries: list[IndexEntry] = []
        with index.open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                entry = _entry(origin, row, self._accepted)
                if entry is not None:
                    entries.append(entry)
        return tuple(entries)


def _entry(origin: Path, row: dict[str, str], accepted: frozenset[str]) -> IndexEntry | None:
    if row.get("situacao") not in accepted:
        return None
    arquivo = row.get("arquivo") or ""
    caminho = row.get("caminho") or ""
    if arquivo == "" or caminho == "":
        raise ElectionError("index row is missing arquivo or caminho")
    path = Path(caminho)
    if not path.is_absolute():
        path = origin / path
    return IndexEntry(
        conjunto=row.get("conjunto") or "",
        turno=row.get("turno") or "",
        uf=row.get("uf") or "",
        arquivo=arquivo,
        path=path,
    )
