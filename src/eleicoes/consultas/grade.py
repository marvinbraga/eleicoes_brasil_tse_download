"""Party-share grid. Places come from poder_dos_partidos; the use case does not query."""

import os
from collections.abc import Callable, Mapping
from typing import Final, TypeVar

from dotenv import load_dotenv

from eleicoes.composition.boletim import build_boletim_reader
from eleicoes.composition.grade import build_municipality_names
from eleicoes.consultas.boletim import poder_dos_partidos
from eleicoes.domain.boletim_consulta import PoderPartido, require_cargo
from eleicoes.domain.errors import InvalidBoletimConsultaError
from eleicoes.domain.grade import GradeDePoder, GradeLevel, LugarVotos
from eleicoes.domain.regiao import REGIONS, region_of
from eleicoes.domain.values import ElectionYear, Turno, Uf, uf_name
from eleicoes.ports.boletim_consulta import BoletimReader
from eleicoes.ports.grade import MunicipalityNames
from eleicoes.use_cases.grade import BuildPartyShareGrid

_T = TypeVar("_T")
_ABROAD: Final = "ZZ"
_MUNICIPIO: Final = "municipio"


def grade_de_poder(
    ano: int,
    turno: int,
    uf: str,
    cargo: str,
    *,
    nivel: str = "municipio",
    reader: BoletimReader | None = None,
    names: MunicipalityNames | None = None,
) -> GradeDePoder:
    level = GradeLevel(nivel).value
    year = ElectionYear(ano).value
    turn = Turno(turno).value
    code = Uf(uf).code
    office = require_cargo(cargo)
    return _opening(reader, names, year, turn, code, office, level)


def _opening(
    reader: BoletimReader | None,
    names: MunicipalityNames | None,
    ano: int,
    turno: int,
    uf: str,
    cargo: str,
    nivel: str,
) -> GradeDePoder:
    if nivel == _MUNICIPIO:
        return _with_both(
            reader,
            names,
            lambda opened, nomes: _finish(
                ano,
                turno,
                uf,
                cargo,
                nivel,
                _municipios(ano, turno, uf, cargo, opened, nomes),
            ),
        )
    collect = _OTHER[nivel]
    return _with_reader(
        reader,
        lambda opened: _finish(
            ano, turno, uf, cargo, nivel, collect(ano, turno, uf, cargo, opened)
        ),
    )


def _with_both(
    reader: BoletimReader | None,
    names: MunicipalityNames | None,
    work: Callable[[BoletimReader, MunicipalityNames], _T],
) -> _T:
    def run(opened: BoletimReader) -> _T:
        return _with_names(names, lambda nomes: work(opened, nomes))

    return _with_reader(reader, run)


def _with_reader(reader: BoletimReader | None, work: Callable[[BoletimReader], _T]) -> _T:
    if reader is not None:
        return work(reader)
    opened = build_boletim_reader(_environment())
    try:
        return work(opened)
    finally:
        opened.close()


def _with_names(
    names: MunicipalityNames | None,
    work: Callable[[MunicipalityNames], _T],
) -> _T:
    if names is not None:
        return work(names)
    opened = build_municipality_names(_environment())
    try:
        return work(opened)
    finally:
        opened.close()


def _finish(
    ano: int,
    turno: int,
    uf: str,
    cargo: str,
    nivel: str,
    lugares: tuple[LugarVotos, ...],
) -> GradeDePoder:
    return BuildPartyShareGrid().execute(ano, turno, uf, cargo, nivel, lugares)


def _municipios(
    ano: int,
    turno: int,
    _uf: str,
    cargo: str,
    reader: BoletimReader,
    names: MunicipalityNames,
) -> tuple[LugarVotos, ...]:
    places: list[LugarVotos] = []
    for code in reader.present_ufs(ano, turno, cargo):
        places.extend(_cities_of(ano, turno, Uf(code).code, cargo, reader, names))
    return tuple(places)


def _cities_of(
    ano: int,
    turno: int,
    state: str,
    cargo: str,
    reader: BoletimReader,
    names: MunicipalityNames,
) -> tuple[LugarVotos, ...]:
    rows = poder_dos_partidos(ano, turno, state, cargo, nivel="municipio", reader=reader)
    if not rows:
        return ()
    found = names.names(state)
    grouped = _by_city(rows)
    return tuple(_lugar_municipio(code, lines, found, state) for code, lines in grouped.items())


def _estados(
    ano: int,
    turno: int,
    _uf: str,
    cargo: str,
    reader: BoletimReader,
) -> tuple[LugarVotos, ...]:
    places: list[LugarVotos] = []
    for state in reader.present_ufs(ano, turno, cargo):
        rows = poder_dos_partidos(ano, turno, state, cargo, nivel="uf", reader=reader)
        if not rows:
            continue
        places.append(LugarVotos(state, uf_name(state), rows))
    return tuple(places)


def _regioes(
    ano: int,
    turno: int,
    _uf: str,
    cargo: str,
    reader: BoletimReader,
) -> tuple[LugarVotos, ...]:
    active = _active_siglas(reader.present_ufs(ano, turno, cargo))
    places: list[LugarVotos] = []
    for region in REGIONS:
        if region.sigla not in active:
            continue
        rows = poder_dos_partidos(ano, turno, region.ufs[0], cargo, nivel="regiao", reader=reader)
        if not rows:
            continue
        places.append(LugarVotos(region.sigla, region.name, rows))
    return tuple(places)


def _pais(
    ano: int,
    turno: int,
    uf: str,
    cargo: str,
    reader: BoletimReader,
) -> tuple[LugarVotos, ...]:
    rows = poder_dos_partidos(ano, turno, uf, cargo, nivel="pais", reader=reader)
    if not rows:
        return ()
    return (LugarVotos("BR", "Brasil", rows),)


def _by_city(rows: tuple[PoderPartido, ...]) -> dict[int, tuple[PoderPartido, ...]]:
    grouped: dict[int, list[PoderPartido]] = {}
    for row in rows:
        code = row.municipio
        if code is None:
            raise InvalidBoletimConsultaError("municipio")
        grouped.setdefault(code, []).append(row)
    return {code: tuple(lines) for code, lines in grouped.items()}


def _lugar_municipio(
    code: int,
    lines: tuple[PoderPartido, ...],
    found: Mapping[int, str],
    state: str,
) -> LugarVotos:
    nome = found.get(code, str(code))
    if not nome.strip():
        nome = str(code)
    return LugarVotos(str(code), f"{nome} ({state})", lines)


def _active_siglas(codes: tuple[str, ...]) -> frozenset[str]:
    siglas: set[str] = set()
    for code in codes:
        normalized = Uf(code).code
        if normalized == _ABROAD:
            continue
        siglas.add(region_of(normalized).sigla)
    return frozenset(siglas)


def _environment() -> Mapping[str, str]:
    load_dotenv()
    return os.environ


_Collect = Callable[[int, int, str, str, BoletimReader], tuple[LugarVotos, ...]]
_OTHER: Final[Mapping[str, _Collect]] = {
    "uf": _estados,
    "regiao": _regioes,
    "pais": _pais,
}
