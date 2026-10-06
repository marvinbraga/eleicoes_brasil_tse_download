"""Boletim consultations. Each function builds one use case."""

import os
from collections.abc import Callable, Mapping
from typing import TypeVar

from dotenv import load_dotenv

from eleicoes.composition.boletim import build_boletim_reader
from eleicoes.domain.boletim_consulta import (
    BrancosNulos,
    Comparativo,
    IndicioBoletim,
    LinhaVoto,
    Participacao,
    PoderPartido,
    PrimeiroColocado,
    TotalCargo,
    VotosMunicipio,
    VotosZona,
)
from eleicoes.ports.boletim_consulta import BoletimReader
from eleicoes.use_cases.boletim import (
    CompareCandidates,
    ListBlankAndNull,
    ListBulletinFindings,
    ListLeadingCandidate,
    ListParticipation,
    ListPartyPower,
    ListSectionVotes,
    ListVotesByZone,
    RankMunicipalities,
    SummarizeCargo,
)

_T = TypeVar("_T")


def resumo_do_cargo(
    ano: int,
    turno: int,
    uf: str,
    cargo: str,
    *,
    reader: BoletimReader | None = None,
) -> tuple[TotalCargo, ...]:
    return _using(reader, lambda opened: SummarizeCargo(opened).execute(ano, turno, uf, cargo))


def ranking_municipios(
    ano: int,
    turno: int,
    uf: str,
    cargo: str,
    numero: int,
    *,
    ordem: str = "mais",
    reader: BoletimReader | None = None,
) -> tuple[VotosMunicipio, ...]:
    return _using(
        reader,
        lambda opened: RankMunicipalities(opened).execute(ano, turno, uf, cargo, numero, ordem),
    )


def comparar(
    ano: int,
    turno: int,
    uf: str,
    cargo: str,
    primeiro: int,
    segundo: int,
    *,
    nivel: str = "municipio",
    reader: BoletimReader | None = None,
) -> tuple[Comparativo, ...]:
    return _using(
        reader,
        lambda opened: CompareCandidates(opened).execute(
            ano, turno, uf, cargo, primeiro, segundo, nivel
        ),
    )


def poder_dos_partidos(
    ano: int,
    turno: int,
    uf: str,
    cargo: str,
    *,
    nivel: str = "municipio",
    reader: BoletimReader | None = None,
) -> tuple[PoderPartido, ...]:
    return _using(
        reader,
        lambda opened: ListPartyPower(opened).execute(ano, turno, uf, cargo, nivel),
    )


def participacao(
    ano: int,
    turno: int,
    uf: str,
    cargo: str,
    *,
    nivel: str = "municipio",
    reader: BoletimReader | None = None,
) -> tuple[Participacao, ...]:
    return _using(
        reader,
        lambda opened: ListParticipation(opened).execute(ano, turno, uf, cargo, nivel),
    )


def brancos_e_nulos(
    ano: int,
    turno: int,
    uf: str,
    cargo: str,
    *,
    nivel: str = "municipio",
    reader: BoletimReader | None = None,
) -> tuple[BrancosNulos, ...]:
    return _using(
        reader,
        lambda opened: ListBlankAndNull(opened).execute(ano, turno, uf, cargo, nivel),
    )


def primeiro_colocado(
    ano: int,
    turno: int,
    uf: str,
    cargo: str,
    *,
    nivel: str = "municipio",
    reader: BoletimReader | None = None,
) -> tuple[PrimeiroColocado, ...]:
    return _using(
        reader,
        lambda opened: ListLeadingCandidate(opened).execute(ano, turno, uf, cargo, nivel),
    )


def votos_da_secao(
    ano: int,
    turno: int,
    uf: str,
    municipio: int,
    zona: int,
    secao: int,
    *,
    reader: BoletimReader | None = None,
) -> tuple[LinhaVoto, ...]:
    return _using(
        reader,
        lambda opened: ListSectionVotes(opened).execute(ano, turno, uf, municipio, zona, secao),
    )


def votos_por_zona(
    ano: int,
    turno: int,
    uf: str,
    municipio: int,
    cargo: str,
    numero: int,
    *,
    reader: BoletimReader | None = None,
) -> tuple[VotosZona, ...]:
    return _using(
        reader,
        lambda opened: ListVotesByZone(opened).execute(ano, turno, uf, municipio, cargo, numero),
    )


def indicios(
    ano: int,
    turno: int,
    uf: str,
    cargo: str,
    *,
    reader: BoletimReader | None = None,
) -> tuple[IndicioBoletim, ...]:
    return _using(
        reader,
        lambda opened: ListBulletinFindings(opened).execute(ano, turno, uf, cargo),
    )


def _using(reader: BoletimReader | None, work: Callable[[BoletimReader], _T]) -> _T:
    if reader is not None:
        return work(reader)
    opened = build_boletim_reader(_environment())
    try:
        return work(opened)
    finally:
        opened.close()


def _environment() -> Mapping[str, str]:
    load_dotenv()
    return os.environ
