"""Voting JSON. Each route is one boletim question."""

from typing import Annotated

from fastapi import APIRouter, Depends

from eleicoes.adapters.http.dependencies import get_boletim_reader
from eleicoes.adapters.http.schemas_votos import (
    BrancosNulosJson,
    ComparativoJson,
    IndicioBoletimJson,
    LinhaVotoJson,
    ParticipacaoJson,
    PoderPartidoJson,
    PrimeiroColocadoJson,
    TotalCargoJson,
    VotosMunicipioJson,
    VotosZonaJson,
)
from eleicoes.ports.boletim_consulta import AsyncBoletimReader
from eleicoes.use_cases.boletim_async import (
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

router = APIRouter(tags=["Votos"])
Reader = Annotated[AsyncBoletimReader, Depends(get_boletim_reader)]
_SECAO = (
    "Exige ano, turno, uf, municipio, zona e secao. "
    "A consulta fica numa seção; não varre as seções do Brasil."
)
_UF = "Exige ano, turno, uf e cargo. O recorte é a UF informada, não o país inteiro."


@router.get("/votos/cargos", summary="Totais do cargo", description=_UF)
async def cargos(ano: int, turno: int, uf: str, cargo: str, reader: Reader) -> list[TotalCargoJson]:
    rows = await SummarizeCargo(reader).execute(ano, turno, uf, cargo)
    return [TotalCargoJson.from_domain(row) for row in rows]


@router.get("/votos/municipios", summary="Ranking de municípios", description=_UF)
async def municipios(
    ano: int,
    turno: int,
    uf: str,
    cargo: str,
    numero: int,
    reader: Reader,
    ordem: str = "mais",
) -> list[VotosMunicipioJson]:
    rows = await RankMunicipalities(reader).execute(ano, turno, uf, cargo, numero, ordem)
    return [VotosMunicipioJson.from_domain(row) for row in rows]


@router.get("/votos/comparar", summary="Comparar dois candidatos", description=_UF)
async def comparar(
    ano: int,
    turno: int,
    uf: str,
    cargo: str,
    primeiro: int,
    segundo: int,
    reader: Reader,
    nivel: str = "municipio",
) -> list[ComparativoJson]:
    rows = await CompareCandidates(reader).execute(ano, turno, uf, cargo, primeiro, segundo, nivel)
    return [ComparativoJson.from_domain(row) for row in rows]


@router.get(
    "/votos/poder",
    summary="Poder do partido",
    description=f"{_UF} nivel admite municipio, zona, uf, regiao ou pais.",
)
async def poder(
    ano: int,
    turno: int,
    uf: str,
    cargo: str,
    reader: Reader,
    nivel: str = "municipio",
) -> list[PoderPartidoJson]:
    rows = await ListPartyPower(reader).execute(ano, turno, uf, cargo, nivel)
    return [PoderPartidoJson.from_domain(row) for row in rows]


@router.get("/votos/participacao", summary="Participação", description=_UF)
async def participacao(
    ano: int,
    turno: int,
    uf: str,
    cargo: str,
    reader: Reader,
    nivel: str = "municipio",
) -> list[ParticipacaoJson]:
    rows = await ListParticipation(reader).execute(ano, turno, uf, cargo, nivel)
    return [ParticipacaoJson.from_domain(row) for row in rows]


@router.get("/votos/brancos-nulos", summary="Brancos e nulos", description=_UF)
async def brancos_nulos(
    ano: int,
    turno: int,
    uf: str,
    cargo: str,
    reader: Reader,
    nivel: str = "municipio",
) -> list[BrancosNulosJson]:
    rows = await ListBlankAndNull(reader).execute(ano, turno, uf, cargo, nivel)
    return [BrancosNulosJson.from_domain(row) for row in rows]


@router.get("/votos/lideres", summary="Primeiro colocado", description=_UF)
async def lideres(
    ano: int,
    turno: int,
    uf: str,
    cargo: str,
    reader: Reader,
    nivel: str = "municipio",
) -> list[PrimeiroColocadoJson]:
    rows = await ListLeadingCandidate(reader).execute(ano, turno, uf, cargo, nivel)
    return [PrimeiroColocadoJson.from_domain(row) for row in rows]


@router.get("/votos/secoes", summary="Votos de uma seção", description=_SECAO)
async def secoes(
    ano: int,
    turno: int,
    uf: str,
    municipio: int,
    zona: int,
    secao: int,
    reader: Reader,
) -> list[LinhaVotoJson]:
    rows = await ListSectionVotes(reader).execute(ano, turno, uf, municipio, zona, secao)
    return [LinhaVotoJson.from_domain(row) for row in rows]


@router.get(
    "/votos/zonas",
    summary="Votos por zona",
    description="Exige ano, turno, uf, municipio, cargo e numero. Não lista zonas de outra UF.",
)
async def zonas(
    ano: int,
    turno: int,
    uf: str,
    municipio: int,
    cargo: str,
    numero: int,
    reader: Reader,
) -> list[VotosZonaJson]:
    rows = await ListVotesByZone(reader).execute(ano, turno, uf, municipio, cargo, numero)
    return [VotosZonaJson.from_domain(row) for row in rows]


@router.get(
    "/votos/indicios",
    summary="Indícios do boletim",
    description=f"{_UF} Percorre as seções dessa UF.",
)
async def indicios(
    ano: int,
    turno: int,
    uf: str,
    cargo: str,
    reader: Reader,
) -> list[IndicioBoletimJson]:
    rows = await ListBulletinFindings(reader).execute(ano, turno, uf, cargo)
    return [IndicioBoletimJson.from_domain(row) for row in rows]
