"""Async party-share grid. Grouping matches consultas.grade; only the reads await."""

from eleicoes.consultas.grade import _active_siglas, _by_city, _lugar_municipio
from eleicoes.domain.boletim_consulta import PoderPartido, require_cargo
from eleicoes.domain.grade import GradeDePoder, GradeLevel, LugarVotos
from eleicoes.domain.regiao import REGIONS
from eleicoes.domain.values import ElectionYear, Turno, Uf, uf_name
from eleicoes.ports.boletim_consulta import AsyncBoletimReader
from eleicoes.ports.grade import AsyncMunicipalityNames
from eleicoes.use_cases.boletim_async import ListPartyPower
from eleicoes.use_cases.grade import BuildPartyShareGrid

_MUNICIPIO = "municipio"
_LEVELS = ("municipio", "uf", "regiao", "pais")


async def build_party_share_grid(
    reader: AsyncBoletimReader,
    names: AsyncMunicipalityNames,
    ano: int,
    turno: int,
    uf: str,
    cargo: str,
    *,
    nivel: str = "municipio",
) -> GradeDePoder:
    level = GradeLevel(nivel).value
    year = ElectionYear(ano).value
    turn = Turno(turno).value
    code = Uf(uf).code
    office = require_cargo(cargo)
    places = await _places(reader, names, year, turn, code, office, level)
    return BuildPartyShareGrid().execute(year, turn, code, office, level, places)


async def build_all_grades(
    reader: AsyncBoletimReader,
    names: AsyncMunicipalityNames,
    ano: int,
    turno: int,
    uf: str,
    cargo: str,
) -> tuple[GradeDePoder, ...]:
    built: list[GradeDePoder] = []
    for nivel in _LEVELS:
        grade = await build_party_share_grid(reader, names, ano, turno, uf, cargo, nivel=nivel)
        built.append(grade)
    return tuple(built)


async def _places(
    reader: AsyncBoletimReader,
    names: AsyncMunicipalityNames,
    ano: int,
    turno: int,
    uf: str,
    cargo: str,
    nivel: str,
) -> tuple[LugarVotos, ...]:
    if nivel == _MUNICIPIO:
        return await _municipalities(reader, names, ano, turno, cargo)
    if nivel == "uf":
        return await _states(reader, ano, turno, cargo)
    if nivel == "regiao":
        return await _regions(reader, ano, turno, cargo)
    return await _country(reader, ano, turno, uf, cargo)


async def _municipalities(
    reader: AsyncBoletimReader,
    names: AsyncMunicipalityNames,
    ano: int,
    turno: int,
    cargo: str,
) -> tuple[LugarVotos, ...]:
    places: list[LugarVotos] = []
    for code in await reader.present_ufs(ano, turno, cargo):
        state = Uf(code).code
        found = await _cities(reader, names, ano, turno, state, cargo)
        places.extend(found)
    return tuple(places)


async def _cities(
    reader: AsyncBoletimReader,
    names: AsyncMunicipalityNames,
    ano: int,
    turno: int,
    state: str,
    cargo: str,
) -> tuple[LugarVotos, ...]:
    rows = await _power(reader, ano, turno, state, cargo, _MUNICIPIO)
    if not rows:
        return ()
    found = await names.names(state)
    grouped = _by_city(rows)
    return tuple(_lugar_municipio(code, lines, found, state) for code, lines in grouped.items())


async def _states(
    reader: AsyncBoletimReader,
    ano: int,
    turno: int,
    cargo: str,
) -> tuple[LugarVotos, ...]:
    places: list[LugarVotos] = []
    for state in await reader.present_ufs(ano, turno, cargo):
        code = Uf(state).code
        rows = await _power(reader, ano, turno, code, cargo, "uf")
        if rows:
            places.append(LugarVotos(code, uf_name(code), rows))
    return tuple(places)


async def _regions(
    reader: AsyncBoletimReader,
    ano: int,
    turno: int,
    cargo: str,
) -> tuple[LugarVotos, ...]:
    active = _active_siglas(await reader.present_ufs(ano, turno, cargo))
    places: list[LugarVotos] = []
    for region in REGIONS:
        if region.sigla not in active:
            continue
        rows = await _power(reader, ano, turno, region.ufs[0], cargo, "regiao")
        if rows:
            places.append(LugarVotos(region.sigla, region.name, rows))
    return tuple(places)


async def _country(
    reader: AsyncBoletimReader,
    ano: int,
    turno: int,
    uf: str,
    cargo: str,
) -> tuple[LugarVotos, ...]:
    rows = await _power(reader, ano, turno, uf, cargo, "pais")
    if not rows:
        return ()
    return (LugarVotos("BR", "Brasil", rows),)


async def _power(
    reader: AsyncBoletimReader,
    ano: int,
    turno: int,
    uf: str,
    cargo: str,
    nivel: str,
) -> tuple[PoderPartido, ...]:
    return await ListPartyPower(reader).execute(ano, turno, uf, cargo, nivel)
