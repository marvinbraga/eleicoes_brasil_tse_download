"""Cells kept for a party-power report. Shares and HTML are derived later."""

from dataclasses import dataclass
from typing import Final

from eleicoes.domain.errors import InvalidBoletimConsultaError, InvalidStoredReportError
from eleicoes.domain.grade import (
    CelulaGrade,
    GradeDePoder,
    GradeLevel,
    LinhaGrade,
    ordered_parties,
    place_sort_key,
)

_LEVELS: Final[tuple[str, ...]] = ("municipio", "uf", "regiao", "pais")


@dataclass(frozen=True, slots=True)
class StoredCell:
    nivel: str
    codigo: str
    nome: str
    comparecimento: int
    partido: int
    votos_nominais: int
    votos_legenda: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "nivel", GradeLevel(self.nivel).value)
        object.__setattr__(self, "codigo", _text(self.codigo, "codigo"))
        object.__setattr__(self, "nome", _text(self.nome, "nome"))
        checked = CelulaGrade(
            self.partido,
            self.votos_nominais,
            self.votos_legenda,
            self.comparecimento,
        )
        object.__setattr__(self, "partido", checked.partido)
        object.__setattr__(self, "votos_nominais", checked.votos_nominais)
        object.__setattr__(self, "votos_legenda", checked.votos_legenda)
        object.__setattr__(self, "comparecimento", checked.comparecimento)


@dataclass(frozen=True, slots=True)
class _Place:
    codigo: str
    nome: str
    comparecimento: int
    cells: tuple[StoredCell, ...]


def cells_from_grades(grades: tuple[GradeDePoder, ...]) -> tuple[StoredCell, ...]:
    return tuple(
        _stored(grade, line, item)
        for grade in grades
        for line in grade.linhas
        for item in line.celulas
    )


def grades_from_cells(
    ano: int,
    turno: int,
    uf: str,
    cargo: str,
    cells: tuple[StoredCell, ...],
) -> tuple[GradeDePoder, ...]:
    grouped = _by_level(cells)
    return tuple(_grade(ano, turno, uf, cargo, nivel, grouped.get(nivel, ())) for nivel in _LEVELS)


def _stored(grade: GradeDePoder, line: LinhaGrade, item: CelulaGrade) -> StoredCell:
    return StoredCell(
        grade.nivel,
        line.codigo,
        line.nome,
        line.comparecimento,
        item.partido,
        item.votos_nominais,
        item.votos_legenda,
    )


def _by_level(cells: tuple[StoredCell, ...]) -> dict[str, tuple[StoredCell, ...]]:
    grouped: dict[str, list[StoredCell]] = {}
    for cell in cells:
        grouped.setdefault(cell.nivel, []).append(cell)
    return {nivel: tuple(items) for nivel, items in grouped.items()}


def _grade(
    ano: int,
    turno: int,
    uf: str,
    cargo: str,
    nivel: str,
    cells: tuple[StoredCell, ...],
) -> GradeDePoder:
    places = _places(cells)
    columns = ordered_parties(_totals(places))
    rows = tuple(sorted((_linha(place, columns) for place in places), key=_row_key))
    return GradeDePoder(ano, turno, uf, cargo, nivel, columns, rows)


def _places(cells: tuple[StoredCell, ...]) -> tuple[_Place, ...]:
    grouped: dict[str, list[StoredCell]] = {}
    for cell in cells:
        grouped.setdefault(cell.codigo, []).append(cell)
    return tuple(_place(codigo, tuple(items)) for codigo, items in grouped.items())


def _place(codigo: str, cells: tuple[StoredCell, ...]) -> _Place:
    first = cells[0]
    _same_turnout(cells, first.comparecimento)
    _same_name(cells, first.nome)
    return _Place(codigo, first.nome, first.comparecimento, cells)


def _same_turnout(cells: tuple[StoredCell, ...], comparecimento: int) -> None:
    if any(cell.comparecimento != comparecimento for cell in cells):
        raise InvalidStoredReportError("comparecimento")


def _same_name(cells: tuple[StoredCell, ...], nome: str) -> None:
    if any(cell.nome != nome for cell in cells):
        raise InvalidStoredReportError("nome")


def _totals(places: tuple[_Place, ...]) -> dict[int, int]:
    totals: dict[int, int] = {}
    for place in places:
        _add_place(totals, place)
    return totals


def _add_place(totals: dict[int, int], place: _Place) -> None:
    for cell in place.cells:
        votos = cell.votos_nominais + cell.votos_legenda
        totals[cell.partido] = totals.get(cell.partido, 0) + votos


def _linha(place: _Place, columns: tuple[int, ...]) -> LinhaGrade:
    indexed = _index(place.cells)
    built = tuple(_at(indexed, party, place.comparecimento) for party in columns)
    return LinhaGrade(place.codigo, place.nome, place.comparecimento, built)


def _index(cells: tuple[StoredCell, ...]) -> dict[int, StoredCell]:
    indexed: dict[int, StoredCell] = {}
    for cell in cells:
        if cell.partido in indexed:
            raise InvalidBoletimConsultaError("partido")
        indexed[cell.partido] = cell
    return indexed


def _at(indexed: dict[int, StoredCell], party: int, comparecimento: int) -> CelulaGrade:
    cell = indexed.get(party)
    if cell is None:
        raise InvalidBoletimConsultaError("partido")
    return CelulaGrade(party, cell.votos_nominais, cell.votos_legenda, comparecimento)


def _row_key(line: LinhaGrade) -> tuple[str, str]:
    return place_sort_key(line.nome, line.codigo)


def _text(value: object, field: str) -> str:
    if not isinstance(value, str) or value.strip() == "":
        raise InvalidBoletimConsultaError(field)
    return value.strip()
