"""Join of a cross-report leader to mesh codes. No file and no geometry."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Final

from eleicoes.domain.errors import ElectionError
from eleicoes.domain.presidente_governador import CargoReading, CrossReportView, PlaceReading

_COLUMNS: Final = (
    "DT_GERACAO",
    "HH_GERACAO",
    "CD_UF_TSE",
    "CD_UF_IBGE",
    "SG_UF",
    "NM_UF",
    "CD_MUNICIPIO_TSE",
    "NM_MUNICIPIO_TSE",
    "CD_MUNICIPIO_IBGE",
    "NM_MUNICIPIO_IBGE",
)
_CARGOS: Final = frozenset({"presidente", "governador"})
_EXTERIOR: Final = "ZZ"


class InvalidPonteError(ElectionError):
    def __init__(self) -> None:
        super().__init__("invalid TSE-IBGE bridge")


class InvalidCargoError(ElectionError):
    def __init__(self, value: object) -> None:
        self.value = value
        super().__init__(f"invalid cargo: {value}")


class BridgeMissingError(ElectionError):
    def __init__(self, ausentes: tuple[tuple[str, str], ...]) -> None:
        self.ausentes = ausentes
        super().__init__(f"missing IBGE code: {ausentes}")


class MarkMissingError(ElectionError):
    def __init__(self, partidos: tuple[int, ...]) -> None:
        self.partidos = partidos
        super().__init__(f"missing party mark: {partidos}")


class MeshMissingError(ElectionError):
    def __init__(self, nome: str) -> None:
        self.nome = nome
        super().__init__(f"missing mesh: {nome}")


class MarkInvalidError(ElectionError):
    def __init__(self, partido: int) -> None:
        self.partido = partido
        super().__init__(f"invalid party mark: {partido}")


class MeshMismatchError(ElectionError):
    def __init__(self, nome: str) -> None:
        self.nome = nome
        super().__init__(f"mesh mismatch: {nome}")


@dataclass(frozen=True, slots=True)
class Marca:
    cor: str
    logo: str


@dataclass(frozen=True, slots=True)
class Pintura:
    codigo: str
    cor: str
    numero: str
    logo: str


@dataclass(frozen=True, slots=True)
class PonteTseIbge:
    municipio_por_tse: Mapping[str, str]
    uf_por_sigla: Mapping[str, str]


@dataclass(frozen=True, slots=True)
class RecortePintado:
    pais: Pintura | None
    ufs: tuple[Pintura, ...]
    municipios: tuple[Pintura, ...]
    sem_poligono: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class PaginaDoMapa:
    ano: int
    turno: int
    cargo: str
    recorte: RecortePintado
    municipios: str
    ufs: str
    paises: str
    municipios_objeto: str
    ufs_objeto: str
    paises_objeto: str
    brasil_id: str
    ol_js: str
    ol_css: str
    topojson_js: str


def ponte_de_linhas(linhas: Sequence[Mapping[str, str]]) -> PonteTseIbge:
    municipios: dict[str, str] = {}
    ufs: dict[str, str] = {}
    ibges: set[str] = set()
    for linha in linhas:
        if tuple(linha) != _COLUMNS:
            raise InvalidPonteError
        tse = linha["CD_MUNICIPIO_TSE"]
        ibge = linha["CD_MUNICIPIO_IBGE"]
        sigla = linha["SG_UF"]
        uf_ibge = linha["CD_UF_IBGE"]
        if len(tse) != 5 or len(ibge) != 7 or len(uf_ibge) != 2 or sigla == _EXTERIOR:
            raise InvalidPonteError
        if tse in municipios or ibge in ibges:
            raise InvalidPonteError
        municipios[tse] = ibge
        ibges.add(ibge)
        anterior = ufs.setdefault(sigla, uf_ibge)
        if anterior != uf_ibge:
            raise InvalidPonteError
    return PonteTseIbge(municipios, ufs)


def recorte_pintado(
    view: CrossReportView,
    cargo: str,
    ponte: PonteTseIbge,
    marcas: Mapping[int, Marca],
    codigos_municipio: frozenset[str],
    codigos_uf: frozenset[str],
    brasil_id: str,
) -> RecortePintado:
    if cargo not in _CARGOS:
        raise InvalidCargoError(cargo)
    faltando = _marcas_faltando(view, cargo, marcas)
    if faltando:
        raise MarkMissingError(faltando)
    ausentes = _sem_ponte(view, ponte)
    if ausentes:
        raise BridgeMissingError(ausentes)
    municipios, buracos = _municipios(view, cargo, ponte, marcas, codigos_municipio)
    ufs, buracos_uf = _ufs(view, cargo, ponte, marcas, codigos_uf)
    return RecortePintado(
        _pais(view, cargo, marcas, brasil_id),
        ufs,
        municipios,
        tuple(sorted(buracos + buracos_uf)),
    )


def _marcas_faltando(
    view: CrossReportView, cargo: str, marcas: Mapping[int, Marca]
) -> tuple[int, ...]:
    found: set[int] = set()
    for reading in _leituras(view):
        leader = _lider(reading, cargo)
        if leader is not None and leader not in marcas:
            found.add(leader)
    return tuple(sorted(found))


def _chave_tse(codigo: str) -> str:
    if codigo.isdigit() and len(codigo) < 5:
        return codigo.zfill(5)
    return codigo


def _sem_ponte(view: CrossReportView, ponte: PonteTseIbge) -> tuple[tuple[str, str], ...]:
    found: list[tuple[str, str]] = []
    for uf, places in view.municipalities:
        if uf == _EXTERIOR:
            continue
        for place in places:
            if _chave_tse(place.codigo) not in ponte.municipio_por_tse:
                found.append((uf, place.codigo))
    return tuple(found)


def _municipios(
    view: CrossReportView,
    cargo: str,
    ponte: PonteTseIbge,
    marcas: Mapping[int, Marca],
    codigos: frozenset[str],
) -> tuple[tuple[Pintura, ...], tuple[str, ...]]:
    painted: list[Pintura] = []
    holes: list[str] = []
    for uf, places in view.municipalities:
        for place in places:
            if _lider(place, cargo) is None:
                continue
            if uf == _EXTERIOR:
                holes.append(place.nome)
                continue
            ibge = ponte.municipio_por_tse[_chave_tse(place.codigo)]
            if ibge not in codigos:
                holes.append(place.nome)
                continue
            painted.append(_pintura(ibge, place, cargo, marcas))
    return tuple(painted), tuple(holes)


def _ufs(
    view: CrossReportView,
    cargo: str,
    ponte: PonteTseIbge,
    marcas: Mapping[int, Marca],
    codigos: frozenset[str],
) -> tuple[tuple[Pintura, ...], tuple[str, ...]]:
    painted: list[Pintura] = []
    holes: list[str] = []
    for state in view.states:
        if _lider(state, cargo) is None:
            continue
        ibge = ponte.uf_por_sigla.get(state.codigo)
        if state.codigo == _EXTERIOR or ibge is None or ibge not in codigos:
            holes.append(f"{state.nome} ({state.codigo})")
            continue
        painted.append(_pintura(ibge, state, cargo, marcas))
    return tuple(painted), tuple(holes)


def _pais(
    view: CrossReportView, cargo: str, marcas: Mapping[int, Marca], brasil_id: str
) -> Pintura | None:
    country = view.country
    if country is None or _lider(country, cargo) is None:
        return None
    return _pintura(brasil_id, country, cargo, marcas)


def _pintura(codigo: str, place: PlaceReading, cargo: str, marcas: Mapping[int, Marca]) -> Pintura:
    leader = _lider(place, cargo)
    if leader is None:
        raise MarkMissingError(())
    marca = marcas[leader]
    return Pintura(codigo, marca.cor, str(leader), marca.logo)


def _leituras(view: CrossReportView) -> tuple[PlaceReading, ...]:
    cities = tuple(place for _, places in view.municipalities for place in places)
    country = () if view.country is None else (view.country,)
    return cities + view.states + country


def _lider(place: PlaceReading, cargo: str) -> int | None:
    reading: CargoReading | None = place.presidente if cargo == "presidente" else place.governador
    if reading is None or reading.leader is None:
        return None
    return reading.leader.partido
