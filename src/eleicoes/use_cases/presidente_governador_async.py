"""Async municipal president × governor load. Assembly stays in the sync module."""

from eleicoes.domain.boletim_consulta import BrancosNulos, PoderPartido
from eleicoes.domain.presidente_governador import MunicipalPlace
from eleicoes.domain.values import UF_CODES, ElectionYear, Turno, Uf
from eleicoes.ports.boletim_consulta import AsyncBoletimReader
from eleicoes.ports.grade import AsyncMunicipalityNames
from eleicoes.use_cases.boletim_async import ListBlankAndNull, ListPartyPower
from eleicoes.use_cases.presidente_governador import (
    _GOVERNOR,
    _MUNICIPIO,
    _PRESIDENT,
    _add_rejected,
    _assemble,
    _blank_map,
    _by_city,
)

_BlankMap = dict[int, tuple[int, int]]


async def collect_places(
    reader: AsyncBoletimReader,
    names: AsyncMunicipalityNames,
    ano: int,
    turno: int,
) -> tuple[MunicipalPlace, ...]:
    year = ElectionYear(ano).value
    turn = Turno(turno).value
    places: list[MunicipalPlace] = []
    for state in await _states(reader, year, turn):
        places.extend(await _state_places(reader, names, year, turn, state))
    return tuple(places)


async def _states(reader: AsyncBoletimReader, ano: int, turno: int) -> tuple[str, ...]:
    found: set[str] = set()
    for cargo in (_PRESIDENT, _GOVERNOR):
        for code in await reader.present_ufs(ano, turno, cargo):
            found.add(Uf(code).code)
    return tuple(code for code in UF_CODES if code in found)


async def _state_places(
    reader: AsyncBoletimReader,
    names: AsyncMunicipalityNames,
    ano: int,
    turno: int,
    state: str,
) -> tuple[MunicipalPlace, ...]:
    president = _by_city(await _power(reader, ano, turno, state, _PRESIDENT))
    if not president:
        return ()
    governor = _by_city(await _power(reader, ano, turno, state, _GOVERNOR))
    rejected = await _rejected(reader, ano, turno, state)
    blanks = await _blank_maps(reader, ano, turno, state)
    labels = await names.names(state)
    return _assemble(state, president, governor, rejected, blanks, labels)


async def _power(
    reader: AsyncBoletimReader,
    ano: int,
    turno: int,
    state: str,
    cargo: str,
) -> tuple[PoderPartido, ...]:
    return await ListPartyPower(reader).execute(ano, turno, state, cargo, _MUNICIPIO)


async def _rejected(
    reader: AsyncBoletimReader,
    ano: int,
    turno: int,
    state: str,
) -> dict[int, int]:
    rows = await reader.party_power(ano, turno, (state,), _PRESIDENT, _MUNICIPIO)
    totals: dict[int, int] = {}
    for row in rows:
        _add_rejected(totals, row)
    return totals


async def _blank_maps(
    reader: AsyncBoletimReader,
    ano: int,
    turno: int,
    state: str,
) -> dict[str, _BlankMap]:
    president = await _blanks(reader, ano, turno, state, _PRESIDENT)
    governor = await _blanks(reader, ano, turno, state, _GOVERNOR)
    return {_PRESIDENT: _blank_map(president), _GOVERNOR: _blank_map(governor)}


async def _blanks(
    reader: AsyncBoletimReader,
    ano: int,
    turno: int,
    state: str,
    cargo: str,
) -> tuple[BrancosNulos, ...]:
    return await ListBlankAndNull(reader).execute(ano, turno, state, cargo, _MUNICIPIO)
