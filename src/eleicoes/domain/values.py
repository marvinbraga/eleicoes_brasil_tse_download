"""Objetos de valor sempre válidos. A faixa de ano é um limite de negócio, não de IO."""

from dataclasses import dataclass
from typing import Final
from urllib.parse import parse_qsl, urlsplit

from eleicoes.domain.errors import (
    EmptyElectionScopeError,
    InvalidElectionYearError,
    InvalidPackageRefError,
    InvalidRemoteZipError,
    InvalidTurnoError,
    InvalidUfError,
)

MIN_ELECTION_YEAR: Final = 1994
MAX_ELECTION_YEAR: Final = 2100
FIRST_TURN: Final = 1
SECOND_TURN: Final = 2
UF_CODES: Final[tuple[str, ...]] = (
    "AC",
    "AL",
    "AM",
    "AP",
    "BA",
    "CE",
    "DF",
    "ES",
    "GO",
    "MA",
    "MT",
    "MS",
    "MG",
    "PA",
    "PB",
    "PE",
    "PI",
    "PR",
    "RJ",
    "RN",
    "RS",
    "RO",
    "RR",
    "SC",
    "SP",
    "SE",
    "TO",
    "ZZ",
)
UF_NAMES: Final[dict[str, str]] = {
    "AC": "Acre",
    "AL": "Alagoas",
    "AM": "Amazonas",
    "AP": "Amapá",
    "BA": "Bahia",
    "CE": "Ceará",
    "DF": "Distrito Federal",
    "ES": "Espírito Santo",
    "GO": "Goiás",
    "MA": "Maranhão",
    "MT": "Mato Grosso",
    "MS": "Mato Grosso do Sul",
    "MG": "Minas Gerais",
    "PA": "Pará",
    "PB": "Paraíba",
    "PE": "Pernambuco",
    "PI": "Piauí",
    "PR": "Paraná",
    "RJ": "Rio de Janeiro",
    "RN": "Rio Grande do Norte",
    "RS": "Rio Grande do Sul",
    "RO": "Rondônia",
    "RR": "Roraima",
    "SC": "Santa Catarina",
    "SP": "São Paulo",
    "SE": "Sergipe",
    "TO": "Tocantins",
    "ZZ": "Exterior",
}
_UF_SET: Final[frozenset[str]] = frozenset(UF_CODES)
_ZIP_SUFFIX: Final = ".zip"
_SHA512_SUFFIX: Final = ".zip.sha512"


def _reject_bool(value: object) -> None:
    if isinstance(value, bool):
        raise InvalidElectionYearError(value)


@dataclass(frozen=True, slots=True)
class ElectionYear:
    value: int

    def __post_init__(self) -> None:
        _reject_bool(self.value)
        if self.value < MIN_ELECTION_YEAR or self.value > MAX_ELECTION_YEAR:
            raise InvalidElectionYearError(self.value)


@dataclass(frozen=True, slots=True)
class Turno:
    value: int

    def __post_init__(self) -> None:
        if isinstance(self.value, bool) or self.value not in (FIRST_TURN, SECOND_TURN):
            raise InvalidTurnoError(self.value)


@dataclass(frozen=True, slots=True)
class Uf:
    code: str

    def __post_init__(self) -> None:
        normalized = self.code.strip().upper()
        if normalized not in _UF_SET:
            raise InvalidUfError(self.code)
        object.__setattr__(self, "code", normalized)


def uf_name(code: str) -> str:
    return UF_NAMES[Uf(code).code]


def default_turnos() -> tuple[Turno, ...]:
    return (Turno(FIRST_TURN), Turno(SECOND_TURN))


def default_ufs() -> tuple[Uf, ...]:
    return tuple(Uf(code) for code in UF_CODES)


@dataclass(frozen=True, slots=True)
class RemoteZip:
    url: str
    filename: str

    def __post_init__(self) -> None:
        if not self.url.startswith(("https://", "http://")):
            raise InvalidRemoteZipError(self.url)
        lowered = self.filename.lower()
        if (
            not self.filename
            or "/" in self.filename
            or "\\" in self.filename
            or self.filename in {".", ".."}
            or lowered.endswith(_SHA512_SUFFIX)
            or not lowered.endswith(_ZIP_SUFFIX)
        ):
            raise InvalidRemoteZipError(self.filename)


@dataclass(frozen=True, slots=True)
class DiscoveryRequest:
    year: ElectionYear
    turnos: tuple[Turno, ...]
    ufs: tuple[Uf, ...]
    cdn_directory: str | None = None
    dataset_ref: str | None = None

    def __post_init__(self) -> None:
        if not self.turnos:
            raise EmptyElectionScopeError("turno")
        if not self.ufs:
            raise EmptyElectionScopeError("UF")
        object.__setattr__(self, "cdn_directory", _blank_to_none(self.cdn_directory))
        object.__setattr__(self, "dataset_ref", _blank_to_none(self.dataset_ref))


@dataclass(frozen=True, slots=True)
class PackageRef:
    package_id: str

    @classmethod
    def parse(cls, raw: str) -> "PackageRef":
        text = raw.strip()
        if not text:
            raise InvalidPackageRefError(raw)
        if "://" not in text:
            return cls(_require_package_id(text))
        parts = urlsplit(text)
        query_id = dict(parse_qsl(parts.query)).get("id")
        if query_id:
            return cls(_require_package_id(query_id))
        segment = parts.path.rstrip("/").split("/")[-1]
        return cls(_require_package_id(segment))


def _require_package_id(package_id: str) -> str:
    if not package_id or "/" in package_id or "\\" in package_id or package_id in {".", ".."}:
        raise InvalidPackageRefError(package_id)
    return package_id


def _blank_to_none(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip().strip('"').strip("'")
    if not stripped:
        return None
    return stripped.rstrip("/")
