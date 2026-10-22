"""Força municipal por partido: prefeituras, eleitorado governado e vereadores. Sem IO."""

from dataclasses import dataclass
from datetime import date, datetime

from eleicoes.domain.errors import InvalidUfError
from eleicoes.domain.municipal_contract import MUNICIPAL_UFS
from eleicoes.domain.partido_equivalencia import PartidoEquivalente, equivalente_2026


@dataclass(frozen=True, slots=True)
class PartyMayors:
    partido: int
    sigla: str
    prefeitos: int
    eleitorado: int


@dataclass(frozen=True, slots=True)
class PartyCouncil:
    partido: int
    sigla: str
    vereadores: int
    municipios: int


@dataclass(frozen=True, slots=True)
class MunicipalTotals:
    municipios: int
    com_prefeito: int
    sem_prefeito: int
    suplementares: int
    eleitorado: int
    vereadores: int
    vagas_vereador: int
    divergencias_vagas: int


@dataclass(frozen=True, slots=True)
class StoredMayor:
    partido: int
    sigla: str
    nome_urna: str
    turno: int
    suplementar: bool
    data_eleicao: date


@dataclass(frozen=True, slots=True)
class StoredCouncil:
    partido: int
    sigla: str
    eleitos: int


@dataclass(frozen=True, slots=True)
class StoredMunicipality:
    uf: str
    ue: str
    nome: str
    eleitorado: int
    prefeito: StoredMayor | None
    vereadores: tuple[StoredCouncil, ...]


@dataclass(frozen=True, slots=True)
class StoredMunicipalResults:
    ano: int
    corte: datetime
    importado_em: datetime
    totais: MunicipalTotals
    prefeitos: tuple[PartyMayors, ...]
    vereadores: tuple[PartyCouncil, ...]
    municipios: tuple[StoredMunicipality, ...]


@dataclass(frozen=True, slots=True)
class PartyStrength:
    equivalente: PartidoEquivalente
    prefeitos: int
    eleitorado_governado: int
    vereadores: int
    municipios_com_vereador: int


@dataclass(frozen=True, slots=True)
class MunicipalReport:
    ano: int
    uf: str | None
    corte: datetime
    importado_em: datetime
    totais: MunicipalTotals
    partidos: tuple[PartyStrength, ...]
    municipios: tuple[StoredMunicipality, ...]


def require_municipal_uf(uf: str | None) -> str | None:
    """None é o país inteiro. DF e ZZ não têm eleição municipal."""
    if uf is None:
        return None
    normalized = uf.strip().upper()
    if normalized not in MUNICIPAL_UFS:
        raise InvalidUfError(uf)
    return normalized


def municipal_report(stored: StoredMunicipalResults, uf: str | None) -> MunicipalReport:
    mayors = {item.partido: item for item in stored.prefeitos}
    council = {item.partido: item for item in stored.vereadores}
    partidos = tuple(
        sorted(
            (
                _strength(numero, mayors.get(numero), council.get(numero))
                for numero in {*mayors, *council}
            ),
            key=_order,
        )
    )
    return MunicipalReport(
        ano=stored.ano,
        uf=uf,
        corte=stored.corte,
        importado_em=stored.importado_em,
        totais=stored.totais,
        partidos=partidos,
        municipios=stored.municipios,
    )


def _strength(
    numero: int, mayors: PartyMayors | None, council: PartyCouncil | None
) -> PartyStrength:
    sigla = mayors.sigla if mayors is not None else council.sigla if council is not None else ""
    return PartyStrength(
        equivalente=equivalente_2026(numero, sigla),
        prefeitos=mayors.prefeitos if mayors is not None else 0,
        eleitorado_governado=mayors.eleitorado if mayors is not None else 0,
        vereadores=council.vereadores if council is not None else 0,
        municipios_com_vereador=council.municipios if council is not None else 0,
    )


def _order(item: PartyStrength) -> tuple[int, int, int, int]:
    return (
        -item.prefeitos,
        -item.eleitorado_governado,
        -item.vereadores,
        item.equivalente.numero_2024,
    )


@dataclass(frozen=True, slots=True)
class UfPartyCount:
    uf: str
    partido: int
    sigla: str
    prefeitos: int
    eleitorado: int
    vereadores: int


@dataclass(frozen=True, slots=True)
class UfTotals:
    uf: str
    municipios: int
    com_prefeito: int
    eleitorado: int
    vereadores: int


@dataclass(frozen=True, slots=True)
class MunicipalCountsByUf:
    corte: datetime
    importado_em: datetime
    totais: tuple[UfTotals, ...]
    linhas: tuple[UfPartyCount, ...]
