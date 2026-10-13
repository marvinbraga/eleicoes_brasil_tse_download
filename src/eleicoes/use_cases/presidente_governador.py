"""Load municipal president and governor ballots. Higher levels are derived later."""

from collections.abc import Mapping
from typing import Final

from eleicoes.domain.boletim_consulta import BrancosNulos, PoderPartido, partido_tem_candidato
from eleicoes.domain.errors import InvalidBoletimConsultaError
from eleicoes.domain.presidente_governador import CargoTally, MunicipalPlace, PartyTally
from eleicoes.domain.values import UF_CODES, ElectionYear, Turno, Uf
from eleicoes.ports.boletim_consulta import BoletimReader
from eleicoes.ports.grade import MunicipalityNames
from eleicoes.use_cases.boletim import ListBlankAndNull, ListPartyPower

_PRESIDENT: Final = "presidente"
_GOVERNOR: Final = "governador"
_MUNICIPIO: Final = "municipio"
_BlankMap = dict[int, tuple[int, int]]


def collect_places(
    reader: BoletimReader,
    names: MunicipalityNames,
    ano: int,
    turno: int,
) -> tuple[MunicipalPlace, ...]:
    year = ElectionYear(ano).value
    turn = Turno(turno).value
    places: list[MunicipalPlace] = []
    for state in _states(reader, year, turn):
        places.extend(_state_places(reader, names, year, turn, state))
    return tuple(places)


def _states(reader: BoletimReader, ano: int, turno: int) -> tuple[str, ...]:
    found: set[str] = set()
    for cargo in (_PRESIDENT, _GOVERNOR):
        for code in reader.present_ufs(ano, turno, cargo):
            found.add(Uf(code).code)
    return tuple(code for code in UF_CODES if code in found)


def _state_places(
    reader: BoletimReader,
    names: MunicipalityNames,
    ano: int,
    turno: int,
    state: str,
) -> tuple[MunicipalPlace, ...]:
    president = _by_city(_power(reader, ano, turno, state, _PRESIDENT))
    if not president:
        return ()
    governor = _by_city(_power(reader, ano, turno, state, _GOVERNOR))
    rejected = _rejected(reader, ano, turno, state)
    blanks = _blank_maps(reader, ano, turno, state)
    return _assemble(state, president, governor, rejected, blanks, names.names(state))


def _power(
    reader: BoletimReader,
    ano: int,
    turno: int,
    state: str,
    cargo: str,
) -> tuple[PoderPartido, ...]:
    return ListPartyPower(reader).execute(ano, turno, state, cargo, _MUNICIPIO)


def _by_city(rows: tuple[PoderPartido, ...]) -> dict[int, tuple[PoderPartido, ...]]:
    grouped: dict[int, list[PoderPartido]] = {}
    for row in rows:
        code = row.municipio
        if code is None:
            raise InvalidBoletimConsultaError("municipio")
        grouped.setdefault(code, []).append(row)
    return {code: tuple(items) for code, items in grouped.items()}


def _rejected(reader: BoletimReader, ano: int, turno: int, state: str) -> dict[int, int]:
    rows = reader.party_power(ano, turno, (state,), _PRESIDENT, _MUNICIPIO)
    totals: dict[int, int] = {}
    for row in rows:
        _add_rejected(totals, row)
    return totals


def _add_rejected(totals: dict[int, int], row: PoderPartido) -> None:
    if partido_tem_candidato(_PRESIDENT, row.partido) or row.votos == 0:
        return
    code = row.municipio
    if code is None:
        raise InvalidBoletimConsultaError("municipio")
    totals[code] = totals.get(code, 0) + row.votos


def _blank_maps(
    reader: BoletimReader,
    ano: int,
    turno: int,
    state: str,
) -> dict[str, _BlankMap]:
    return {
        _PRESIDENT: _blank_map(_blanks(reader, ano, turno, state, _PRESIDENT)),
        _GOVERNOR: _blank_map(_blanks(reader, ano, turno, state, _GOVERNOR)),
    }


def _blanks(
    reader: BoletimReader,
    ano: int,
    turno: int,
    state: str,
    cargo: str,
) -> tuple[BrancosNulos, ...]:
    return ListBlankAndNull(reader).execute(ano, turno, state, cargo, _MUNICIPIO)


def _blank_map(rows: tuple[BrancosNulos, ...]) -> _BlankMap:
    found: _BlankMap = {}
    for row in rows:
        branco, nulo = found.get(row.municipio, (0, 0))
        found[row.municipio] = (branco + row.branco, nulo + row.nulo)
    return found


def _assemble(
    state: str,
    president: dict[int, tuple[PoderPartido, ...]],
    governor: dict[int, tuple[PoderPartido, ...]],
    rejected: dict[int, int],
    blanks: dict[str, _BlankMap],
    labels: Mapping[int, str],
) -> tuple[MunicipalPlace, ...]:
    built = (
        _one(state, code, rows, governor, rejected, blanks, labels)
        for code, rows in sorted(president.items())
    )
    return tuple(place for place in built if place is not None)


def _one(
    state: str,
    code: int,
    rows: tuple[PoderPartido, ...],
    governor: dict[int, tuple[PoderPartido, ...]],
    rejected: dict[int, int],
    blanks: dict[str, _BlankMap],
    labels: Mapping[int, str],
) -> MunicipalPlace | None:
    parties = _parties(rows)
    if not parties:
        return None
    branco, nulo = _counts(blanks[_PRESIDENT], code, rejected.get(code, 0))
    tally = CargoTally(parties, branco, nulo)
    governor_tally = _governor(governor.get(code), blanks[_GOVERNOR], code)
    return MunicipalPlace(state, str(code), _label(labels, code, state), tally, governor_tally)


def _governor(
    rows: tuple[PoderPartido, ...] | None,
    blanks: _BlankMap,
    code: int,
) -> CargoTally | None:
    if rows is None:
        return None
    parties = _parties(rows)
    if not parties:
        return None
    branco, nulo = _counts(blanks, code, 0)
    return CargoTally(parties, branco, nulo)


def _parties(rows: tuple[PoderPartido, ...]) -> tuple[PartyTally, ...]:
    nominais: dict[int, int] = {}
    legenda: dict[int, int] = {}
    for row in rows:
        if row.votos == 0:
            continue
        nominais[row.partido] = nominais.get(row.partido, 0) + row.votos_nominais
        legenda[row.partido] = legenda.get(row.partido, 0) + row.votos_legenda
    return tuple(
        PartyTally(partido, nominais[partido], legenda[partido]) for partido in sorted(nominais)
    )


def _counts(found: _BlankMap, code: int, extra_nulo: int) -> tuple[int, int]:
    branco, nulo = found.get(code, (0, 0))
    return branco, nulo + extra_nulo


def _label(found: Mapping[int, str], code: int, state: str) -> str:
    nome = found.get(code, "")
    if nome.strip() == "":
        nome = str(code)
    return f"{nome.strip()} ({state})"
