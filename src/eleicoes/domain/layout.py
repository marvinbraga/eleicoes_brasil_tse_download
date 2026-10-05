"""Organiza cada zip por conjunto, turno e UF para a análise posterior."""

import csv
from dataclasses import dataclass
from pathlib import Path
from re import Pattern
from re import compile as compile_pattern

from eleicoes.domain.report import FileOutcome, TransferStatus
from eleicoes.domain.values import UF_CODES

_UF_SET = frozenset(UF_CODES)
_CLASSIC: Pattern[str] = compile_pattern(
    r"^bu_imgbu_logjez_rdv_vscmr_\d{4}_(?P<turno>[12])t_(?P<uf>[A-Za-z]{2})\.zip$"
)
_GEDAI: Pattern[str] = compile_pattern(
    r"^log_gedai_(?P<turno>[12])t_(?P<uf>[A-Za-z]{2})(?:_.*)?\.zip$"
)
_CORRESPONDENCIA: Pattern[str] = compile_pattern(
    r"^CESP_(?P<turno>[12])t_(?P<uf>[A-Za-z]{2})(?:_.*)?\.zip$"
)
_STATUS_LABEL = {
    TransferStatus.DOWNLOADED: "baixado",
    TransferStatus.SKIPPED: "ignorado",
    TransferStatus.MISSING: "ausente",
}


@dataclass(frozen=True, slots=True)
class ArchiveLocation:
    collection: str
    turno: str
    uf: str
    filename: str

    @property
    def relative_path(self) -> Path:
        if self.collection == "":
            return Path("outros") / self.filename
        return Path(self.collection) / f"turno-{self.turno}" / self.uf / self.filename


def locate(filename: str) -> ArchiveLocation:
    classic = _CLASSIC.fullmatch(filename)
    if classic is not None:
        return _located("totalizacao", classic.group("turno"), classic.group("uf"), filename)
    gedai = _GEDAI.fullmatch(filename)
    if gedai is not None:
        return _located("logs-gedai", gedai.group("turno"), gedai.group("uf"), filename)
    correspondencia = _CORRESPONDENCIA.fullmatch(filename)
    if correspondencia is not None:
        return _located(
            "correspondencias",
            correspondencia.group("turno"),
            correspondencia.group("uf"),
            filename,
        )
    return ArchiveLocation("", "", "", filename)


def write_index(destination: Path, outcomes: tuple[FileOutcome, ...]) -> Path:
    destination.mkdir(parents=True, exist_ok=True)
    index = destination / "indice.csv"
    with index.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=(
                "conjunto",
                "turno",
                "uf",
                "arquivo",
                "caminho",
                "situacao",
                "tamanho_bytes",
            ),
        )
        writer.writeheader()
        for outcome in outcomes:
            location = locate(outcome.filename)
            stored = destination / location.relative_path
            size = stored.stat().st_size if stored.is_file() else ""
            writer.writerow(
                {
                    "conjunto": location.collection,
                    "turno": location.turno,
                    "uf": location.uf,
                    "arquivo": outcome.filename,
                    "caminho": location.relative_path.as_posix(),
                    "situacao": _STATUS_LABEL[outcome.status],
                    "tamanho_bytes": size,
                }
            )
    return index


def _located(collection: str, turno: str, uf: str, filename: str) -> ArchiveLocation:
    normalized = uf.upper()
    if normalized not in _UF_SET:
        return ArchiveLocation("", "", "", filename)
    return ArchiveLocation(collection, turno, normalized, filename)
