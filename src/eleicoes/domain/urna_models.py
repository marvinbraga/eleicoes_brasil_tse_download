"""Value objects for one ballot-box file announced by the divulgação index."""

import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from eleicoes.domain.errors import ElectionError, InvalidUrnaCodeError
from eleicoes.domain.report import EXIT_NOT_PUBLISHED, EXIT_SUCCESS
from eleicoes.domain.values import ElectionYear, Turno, Uf

URNA_COLLECTION: Final = "arquivo-urna"
_MUNICIPIO_WIDTH: Final = 5
_ZONA_WIDTH: Final = 4
_SECAO_WIDTH: Final = 4
_SITUACOES: Final = frozenset({"baixado", "ignorado", "ausente"})
_DOWNLOADABLE: Final = frozenset({"totalizado", "recebido"})


def _padded(value: object, width: int) -> str:
    if isinstance(value, bool):
        raise InvalidUrnaCodeError(value)
    if isinstance(value, int):
        if value < 0:
            raise InvalidUrnaCodeError(value)
        text = str(value)
    elif isinstance(value, str):
        text = value.strip()
    else:
        raise InvalidUrnaCodeError(value)
    if not text.isdigit():
        raise InvalidUrnaCodeError(value)
    if len(text) > width:
        return text
    return text.zfill(width)


def _require_leaf(value: str) -> None:
    if not value or value in {".", ".."} or "/" in value or "\\" in value:
        raise InvalidUrnaCodeError(value)


def _status_key(label: str) -> str:
    decomposed = unicodedata.normalize("NFD", label.strip().casefold())
    marks = unicodedata.category
    without_marks = (character for character in decomposed if marks(character) != "Mn")
    return "".join(without_marks)


@dataclass(frozen=True, slots=True)
class MunicipioCode:
    value: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", _padded(self.value, _MUNICIPIO_WIDTH))


@dataclass(frozen=True, slots=True)
class ZonaCode:
    value: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", _padded(self.value, _ZONA_WIDTH))


@dataclass(frozen=True, slots=True)
class SecaoCode:
    value: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", _padded(self.value, _SECAO_WIDTH))


@dataclass(frozen=True, slots=True)
class PleitoCode:
    value: str

    def __post_init__(self) -> None:
        if not self.value.isdigit() or not 1 <= len(self.value) <= 6:
            raise InvalidUrnaCodeError(self.value)

    @property
    def filename_digits(self) -> str:
        return f"{int(self.value):06d}"


@dataclass(frozen=True, slots=True)
class UrnaAddress:
    uf: Uf
    municipio: MunicipioCode
    zona: ZonaCode
    secao: SecaoCode


@dataclass(frozen=True, slots=True)
class BallotSection:
    address: UrnaAddress
    generated_on: str | None
    generated_at: str | None

    @property
    def has_auxiliary(self) -> bool:
        return _filled(self.generated_on) and _filled(self.generated_at)


def _filled(value: str | None) -> bool:
    return value is not None and bool(value.strip())


@dataclass(frozen=True, slots=True)
class UrnaHash:
    digest: str
    status: str
    filenames: tuple[str, ...]

    def __post_init__(self) -> None:
        _require_leaf(self.digest)
        for name in self.filenames:
            _require_leaf(name)

    def is_downloadable(self) -> bool:
        return _status_key(self.status) in _DOWNLOADABLE


@dataclass(frozen=True, slots=True)
class SelectedHash:
    digest: str
    filenames: tuple[str, ...]

    def __post_init__(self) -> None:
        _require_leaf(self.digest)
        for name in self.filenames:
            _require_leaf(name)


def select_download(hashes: tuple[UrnaHash, ...]) -> SelectedHash | None:
    selected: UrnaHash | None = None
    for item in hashes:
        if item.is_downloadable():
            selected = item
    if selected is None:
        return None
    return SelectedHash(selected.digest, selected.filenames)


@dataclass(frozen=True, slots=True)
class UrnaTemplates:
    section_config: str
    auxiliary: str

    def __post_init__(self) -> None:
        if not self.section_config or not self.auxiliary:
            raise InvalidUrnaCodeError(self.section_config or self.auxiliary)


@dataclass(frozen=True, slots=True)
class PublishedPleito:
    code: PleitoCode
    cycle: str
    turnos: tuple[Turno, ...]

    def __post_init__(self) -> None:
        if not self.cycle or not self.turnos:
            raise InvalidUrnaCodeError(self.cycle)

    def matches(self, year: ElectionYear, turno: Turno) -> bool:
        return self.cycle == f"ele{year.value}" and any(item == turno for item in self.turnos)


@dataclass(frozen=True, slots=True)
class DivulgacaoConfig:
    templates: UrnaTemplates
    pleitos: tuple[PublishedPleito, ...]

    def find(self, year: ElectionYear, turno: Turno) -> PublishedPleito | None:
        for pleito in self.pleitos:
            if pleito.matches(year, turno):
                return pleito
        return None


def urna_relative_path(turno: Turno, address: UrnaAddress, filename: str) -> Path:
    _require_leaf(filename)
    return (
        Path(URNA_COLLECTION)
        / f"turno-{turno.value}"
        / address.uf.code
        / address.municipio.value
        / address.zona.value
        / address.secao.value
        / filename
    )


@dataclass(frozen=True, slots=True)
class UrnaLedgerRow:
    turno: int
    uf: str
    municipio: str
    zona: str
    secao: str
    arquivo: str
    caminho: str
    situacao: str
    tamanho_bytes: int | None

    def __post_init__(self) -> None:
        Turno(self.turno)
        if self.situacao not in _SITUACOES:
            raise ElectionError(f"invalid urna situacao: {self.situacao}")
        if self.tamanho_bytes is not None and self.tamanho_bytes < 0:
            raise ElectionError(f"invalid urna size: {self.tamanho_bytes}")


@dataclass(frozen=True, slots=True)
class UrnaDownloadCommand:
    year: ElectionYear
    turnos: tuple[Turno, ...]
    ufs: tuple[Uf, ...]
    destination: Path

    def __post_init__(self) -> None:
        if not self.turnos:
            raise ElectionError("election scope requires at least one turno")
        if not self.ufs:
            raise ElectionError("election scope requires at least one UF")


@dataclass(frozen=True, slots=True)
class UrnaRunReport:
    downloaded: int
    skipped: int
    missing: int
    unpublished_turnos: tuple[int, ...]

    def __post_init__(self) -> None:
        for value in (self.downloaded, self.skipped, self.missing):
            if isinstance(value, bool) or value < 0:
                raise ElectionError(f"invalid urna counter: {value}")
        for turno in self.unpublished_turnos:
            Turno(turno)

    @property
    def discovered(self) -> int:
        return self.downloaded + self.skipped + self.missing

    @property
    def exit_code(self) -> int:
        if self.downloaded > 0 or self.skipped > 0 or self.missing > 0:
            return EXIT_SUCCESS
        return EXIT_NOT_PUBLISHED
