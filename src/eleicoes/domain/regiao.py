"""Official macro-regions. ZZ is a UF code and belongs to none of them."""

from dataclasses import dataclass
from typing import Final

from eleicoes.domain.errors import InvalidBoletimConsultaError
from eleicoes.domain.values import Uf

_NORTE: Final[tuple[str, ...]] = ("AC", "AP", "AM", "PA", "RO", "RR", "TO")
_NORDESTE: Final[tuple[str, ...]] = ("AL", "BA", "CE", "MA", "PB", "PE", "PI", "RN", "SE")
_CENTRO_OESTE: Final[tuple[str, ...]] = ("DF", "GO", "MT", "MS")
_SUDESTE: Final[tuple[str, ...]] = ("ES", "MG", "RJ", "SP")
_SUL: Final[tuple[str, ...]] = ("PR", "RS", "SC")
_ABROAD: Final = "ZZ"


@dataclass(frozen=True, slots=True)
class MacroRegion:
    name: str
    ufs: tuple[str, ...]
    sigla: str

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or self.name.strip() == "":
            raise InvalidBoletimConsultaError("regiao")
        if not isinstance(self.sigla, str) or self.sigla.strip() == "":
            raise InvalidBoletimConsultaError("regiao")
        if len(self.ufs) == 0 or len(set(self.ufs)) != len(self.ufs):
            raise InvalidBoletimConsultaError("regiao")
        object.__setattr__(self, "name", self.name.strip())
        object.__setattr__(self, "sigla", self.sigla.strip().upper())
        object.__setattr__(self, "ufs", tuple(_geographic(code) for code in self.ufs))


def _geographic(code: str) -> str:
    normalized = Uf(code).code
    if normalized == _ABROAD:
        raise InvalidBoletimConsultaError("regiao")
    return normalized


REGIONS: Final[tuple[MacroRegion, ...]] = (
    MacroRegion("Norte", _NORTE, "NO"),
    MacroRegion("Nordeste", _NORDESTE, "NE"),
    MacroRegion("Centro-Oeste", _CENTRO_OESTE, "CO"),
    MacroRegion("Sudeste", _SUDESTE, "SE"),
    MacroRegion("Sul", _SUL, "S"),
)

REGION_NAMES: Final[frozenset[str]] = frozenset(region.name for region in REGIONS)


def _index(regions: tuple[MacroRegion, ...]) -> dict[str, MacroRegion]:
    found: dict[str, MacroRegion] = {}
    siglas: set[str] = set()
    for region in regions:
        if region.sigla in siglas:
            raise InvalidBoletimConsultaError("regiao")
        siglas.add(region.sigla)
        for code in region.ufs:
            if code in found:
                raise InvalidBoletimConsultaError("regiao")
            found[code] = region
    return found


_BY_UF: Final[dict[str, MacroRegion]] = _index(REGIONS)


def region_of(uf: str) -> MacroRegion:
    region = _BY_UF.get(Uf(uf).code)
    if region is None:
        raise InvalidBoletimConsultaError("regiao")
    return region
