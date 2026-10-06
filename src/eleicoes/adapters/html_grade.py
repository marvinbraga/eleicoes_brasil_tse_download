"""HTML da grade de poder. O visual usa Bootstrap e a escala de cor local."""

import re
from collections.abc import Callable, Mapping
from fractions import Fraction
from html import escape
from typing import Final

from eleicoes.domain.grade import CelulaGrade, GradeDePoder, LinhaGrade
from eleicoes.domain.regiao import REGIONS
from eleicoes.domain.values import UF_CODES, UF_NAMES, uf_name

_TEAL: Final[tuple[int, int, int]] = (13, 111, 110)
_WHITE: Final[tuple[int, int, int]] = (255, 255, 255)
_INK: Final[tuple[int, int, int]] = (20, 20, 20)
_TEXT_LIMIT: Final[Fraction] = Fraction(3, 5)
_PERCENT_SCALE: Final = 10000
_TWO_DECIMALS: Final = 100
_SORT_SCALE: Final = 1_000_000_000
_STATE_SUFFIX: Final = re.compile(r"\(([A-Z]{2})\)\Z")
_BOOTSTRAP: Final = "https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css"
_BOOTSTRAP_HASH: Final = "sha384-QWTKZyjpPEjISv5WaRU9OFeRpok6YctnYmDr5pNlyT2bRjXh0JMhjY6hW+ALEwIH"
_FOOTER: Final = (
    "Os votos nominais e de legenda são somados. "
    "Brancos e nulos ficam de fora. "
    "O percentual é o voto do partido sobre os votos válidos do lugar. "
    "Número sem candidato a presidente conta como nulo. "
    "Clique no título da coluna para ordenar."
)
_STYLE: Final = """
body { color: #141414; }
table.grade th, table.grade td { text-align: right; vertical-align: middle; }
table.grade > :not(caption) > * > * { box-shadow: none; }
table.grade td.lugar, table.grade th.lugar { text-align: left; white-space: nowrap; }
table.grade td.validos, table.grade th.validos { white-space: nowrap; }
table.grade small { font-size: smaller; }
.grade-scroll { max-height: 70vh; }
table.grade thead th {
  position: sticky; top: 0; z-index: 2; cursor: pointer; user-select: none;
  background-color: #fff; --bs-table-bg: #fff;
}
table.grade thead th[aria-sort="ascending"]::after { content: " ▲"; }
table.grade thead th[aria-sort="descending"]::after { content: " ▼"; }
table.grade thead th[aria-sort="none"]::after { content: " ↕"; }
"""
_SCRIPT: Final = """
<script>
(function () {
  document.querySelectorAll("table.grade").forEach(function (table) {
    table.querySelectorAll("thead th").forEach(function (header, index) {
      header.tabIndex = 0;
      header.addEventListener("click", function () { reorder(table, header, index); });
      header.addEventListener("keydown", function (event) {
        if (event.key !== "Enter" && event.key !== " ") return;
        event.preventDefault();
        reorder(table, header, index);
      });
    });
  });

  function reorder(table, header, index) {
    var ascending = header.getAttribute("aria-sort") !== "ascending";
    table.querySelectorAll("thead th").forEach(function (item) {
      item.setAttribute("aria-sort", "none");
    });
    header.setAttribute("aria-sort", ascending ? "ascending" : "descending");
    var body = table.tBodies[0];
    var rows = Array.prototype.slice.call(body.rows);
    var sign = ascending ? 1 : -1;
    rows.sort(function (left, right) {
      return sign * compare(left.cells[index], right.cells[index], index);
    });
    rows.forEach(function (row) { body.appendChild(row); });
  }

  function compare(left, right, index) {
    var a = left.getAttribute("data-ord") || "";
    var b = right.getAttribute("data-ord") || "";
    if (index === 0) {
      return a.localeCompare(b, "pt-BR", {numeric: true, sensitivity: "base"});
    }
    return Number(a) - Number(b);
  }
})();
</script>
"""


def html_da_grade(grade: GradeDePoder) -> str:
    return html_das_grades((grade,))


def html_das_grades(grades: tuple[GradeDePoder, ...]) -> str:
    sections = "".join(_section(grade) for grade in grades)
    return f"{_prefix()}{sections}{_suffix()}"


def _prefix() -> str:
    link = (
        f'<link rel="stylesheet" href="{_BOOTSTRAP}" '
        f'integrity="{_BOOTSTRAP_HASH}" crossorigin="anonymous">'
    )
    return (
        '<!DOCTYPE html>\n<html lang="pt-BR">\n<head>\n<meta charset="utf-8">\n'
        "<title>Poder do partido</title>\n"
        f"{link}\n<style>{_STYLE}</style>\n</head>\n"
        '<body>\n<main class="container-fluid py-4">\n'
        '<h1 class="h3 mb-4">Poder do partido</h1>\n'
    )


def _suffix() -> str:
    return (
        f'<footer class="text-secondary small mt-4">{_FOOTER}</footer>\n'
        f"</main>\n{_SCRIPT}</body>\n</html>\n"
    )


def _section(grade: GradeDePoder) -> str:
    body = _municipio_tables(grade) if grade.nivel == "municipio" else _table(grade, grade.linhas)
    return f'<section class="mb-5"><h2 class="h4">{_heading(grade)}</h2>{body}</section>\n'


def _heading(grade: GradeDePoder) -> str:
    return _HEADINGS[grade.nivel](grade)


def _municipio_heading(grade: GradeDePoder) -> str:
    return f"Por município — {grade.ano}, turno {grade.turno}, {escape(grade.cargo)}"


def _estado_heading(grade: GradeDePoder) -> str:
    return f"Por estado — {grade.ano}, turno {grade.turno}, {escape(grade.cargo)}"


def _regiao_heading(_grade: GradeDePoder) -> str:
    legend = ", ".join(f"{escape(region.sigla)} {escape(region.name)}" for region in REGIONS)
    return f"Por região — {legend}"


def _pais_heading(grade: GradeDePoder) -> str:
    return f"No país — {grade.ano}, turno {grade.turno}, {escape(grade.cargo)}"


def _municipio_tables(grade: GradeDePoder) -> str:
    # A escala de cor continua a da grade inteira, para os estados serem comparáveis.
    named, loose = _split_states(grade.linhas)
    blocks = [_state_table(grade, code, rows) for code, rows in named]
    if loose:
        blocks.append(_table(grade, loose))
    return "".join(blocks)


def _split_states(
    rows: tuple[LinhaGrade, ...],
) -> tuple[tuple[tuple[str, tuple[LinhaGrade, ...]], ...], tuple[LinhaGrade, ...]]:
    grouped = _grouped(rows)
    named = tuple((code, tuple(grouped[code])) for code in UF_CODES if code in grouped)
    return named, tuple(grouped.get(None, ()))


def _grouped(rows: tuple[LinhaGrade, ...]) -> dict[str | None, list[LinhaGrade]]:
    grouped: dict[str | None, list[LinhaGrade]] = {}
    for row in rows:
        grouped.setdefault(_state_code(row.nome), []).append(row)
    return grouped


def _state_code(nome: str) -> str | None:
    found = _STATE_SUFFIX.search(nome)
    if found is None:
        return None
    code = found.group(1)
    if code not in UF_NAMES:
        return None
    return code


def _state_table(grade: GradeDePoder, code: str, rows: tuple[LinhaGrade, ...]) -> str:
    title = f"{escape(uf_name(code))} ({escape(code)})"
    return f'<h3 class="h5 mt-4 mb-2">{title}</h3>{_table(grade, rows)}'


def _table(grade: GradeDePoder, rows: tuple[LinhaGrade, ...]) -> str:
    largest = _largest(grade)
    parties = "".join(f'<th aria-sort="none">{party}</th>' for party in grade.colunas)
    body = "".join(_row(row, largest) for row in rows)
    head = (
        '<thead><tr><th class="lugar" aria-sort="none">Lugar</th>'
        f'<th class="validos" aria-sort="none">Votos válidos</th>{parties}</tr></thead>'
    )
    return (
        '<div class="table-responsive grade-scroll">'
        '<table class="table table-sm table-bordered grade mb-4">'
        f"{head}<tbody>{body}</tbody></table></div>"
    )


def _row(row: LinhaGrade, largest: Fraction) -> str:
    validos = _votos_validos(row)
    place = (
        f'<td class="lugar" data-ord="{escape(row.nome)}">'
        f"{escape(row.nome)} <small>{escape(row.codigo)}</small></td>"
    )
    valid = f'<td class="validos" data-ord="{validos}">{_inteiro(validos)}</td>'
    cells = "".join(_cell(cell, validos, largest) for cell in row.celulas)
    return f"<tr>{place}{valid}{cells}</tr>"


def _votos_validos(row: LinhaGrade) -> int:
    return sum(cell.votos for cell in row.celulas)


def _inteiro(value: int) -> str:
    return f"{value:,}".replace(",", ".")


def _cell(cell: CelulaGrade, validos: int, largest: Fraction) -> str:
    share = _sobre_validos(cell.votos, validos)
    title = escape(_title(cell, validos))
    order = _round_half_up(share * _SORT_SCALE)
    return (
        f'<td class="fatia" data-ord="{order}" title="{title}" '
        f'style="{_style(share, largest)}">{_percent(share)}</td>'
    )


def _title(cell: CelulaGrade, validos: int) -> str:
    return (
        f"nominais {cell.votos_nominais}, legenda {cell.votos_legenda}, "
        f"votos {cell.votos}, votos válidos {validos}, "
        f"comparecimento {cell.comparecimento}"
    )


def _sobre_validos(votos: int, validos: int) -> Fraction:
    if validos == 0:
        return Fraction(0)
    return Fraction(votos, validos)


def _largest(grade: GradeDePoder) -> Fraction:
    largest = Fraction(0)
    for row in grade.linhas:
        validos = _votos_validos(row)
        for cell in row.celulas:
            share = _sobre_validos(cell.votos, validos)
            if share > largest:
                largest = share
    return largest


def _style(share: Fraction, largest: Fraction) -> str:
    relative = Fraction(0) if largest == 0 else share / largest
    paint = _rgb(_mix(_WHITE, _TEAL, relative))
    ink = _WHITE if relative > _TEXT_LIMIT else _INK
    return f"background-color:{paint};color:{_rgb(ink)}"


def _mix(
    origin: tuple[int, int, int],
    target: tuple[int, int, int],
    relative: Fraction,
) -> tuple[int, int, int]:
    return (
        _channel(origin[0], target[0], relative),
        _channel(origin[1], target[1], relative),
        _channel(origin[2], target[2], relative),
    )


def _channel(origin: int, target: int, relative: Fraction) -> int:
    mixed = Fraction(origin) + Fraction(target - origin) * relative
    return _round_half_up(mixed)


def _rgb(color: tuple[int, int, int]) -> str:
    red, green, blue = color
    return f"rgb({red},{green},{blue})"


def _percent(share: Fraction) -> str:
    whole, frac = divmod(_round_half_up(share * _PERCENT_SCALE), _TWO_DECIMALS)
    return f"{whole},{frac:02d}%"


def _round_half_up(value: Fraction) -> int:
    quotient, remainder = divmod(value.numerator, value.denominator)
    if remainder * 2 >= value.denominator:
        return quotient + 1
    return quotient


_HEADINGS: Final[Mapping[str, Callable[[GradeDePoder], str]]] = {
    "municipio": _municipio_heading,
    "uf": _estado_heading,
    "regiao": _regiao_heading,
    "pais": _pais_heading,
}
