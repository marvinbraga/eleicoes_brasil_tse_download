"""Appends one flushed row to indice-urnas.csv. Does not touch indice.csv."""

import csv
import threading
from pathlib import Path
from typing import Final

from eleicoes.domain.errors import TransportError
from eleicoes.domain.urna_models import URNA_COLLECTION, UrnaLedgerRow

_FIELDS: Final = (
    "conjunto",
    "turno",
    "uf",
    "municipio",
    "zona",
    "secao",
    "arquivo",
    "caminho",
    "situacao",
    "tamanho_bytes",
)
_INDEX_NAME: Final = "indice-urnas.csv"


class CsvUrnaLedger:
    def __init__(self) -> None:
        self._lock = threading.Lock()

    def append(self, destination: Path, row: UrnaLedgerRow) -> None:
        with self._lock:
            self._append(destination, row)

    def _append(self, destination: Path, row: UrnaLedgerRow) -> None:
        try:
            destination.mkdir(parents=True, exist_ok=True)
            path = destination / _INDEX_NAME
            write_header = not path.is_file() or path.stat().st_size == 0
            with path.open("a", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=_FIELDS)
                if write_header:
                    writer.writeheader()
                writer.writerow(_cells(row))
                handle.flush()
        except OSError as exc:
            raise TransportError("falha ao gravar o arquivo") from exc


def _cells(row: UrnaLedgerRow) -> dict[str, object]:
    size: object = "" if row.tamanho_bytes is None else row.tamanho_bytes
    return {
        "conjunto": URNA_COLLECTION,
        "turno": row.turno,
        "uf": row.uf,
        "municipio": row.municipio,
        "zona": row.zona,
        "secao": row.secao,
        "arquivo": row.arquivo,
        "caminho": row.caminho,
        "situacao": row.situacao,
        "tamanho_bytes": size,
    }
