"""Self-contained HTML for a party-share grid. No remote assets."""

from collections.abc import Callable, Mapping
from fractions import Fraction
from html import escape
from typing import Final

from eleicoes.domain.grade import CelulaGrade, GradeDePoder, LinhaGrade
from eleicoes.domain.regiao import REGIONS

_TEAL: Final[tuple[int, int, int]] = (13, 111, 110)
_WHITE: Final[tuple[int, int, int]] = (255, 255, 255)
_INK: Final[tuple[int, int, int]] = (20, 20, 20)
_TEXT_LIMIT: Final[Fraction] = Fraction(3, 5)
_PERCENT_SCALE: Final = 10000
_TWO_DECIMALS: Final = 100
_FOOTER: Final = (
    "Os votos nominais e de legenda são somados. "
    "Brancos e nulos ficam de fora. "
    "O percentual é o voto do partido sobre os votos válidos do lugar. "
    "Número sem candidato a presidente conta como nulo."
)
_PREFIX: Final = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<title>Poder do partido</title>
<style>
body { font-family: sans-serif; color: #141414; }
table { border-collapse: collapse; margin-bottom: 1.5rem; }
th, td { border: 1px solid #ccc; padding: 0.35rem 0.5rem; text-align: right; }
td.lugar, th.lugar { text-align: left; }
td.validos, th.validos { white-space: nowrap; }
small { font-size: smaller; }
</style>
</head>
<body>
<h1>Poder do partido</h1>
"""
_SUFFIX: Final = f"<footer>{_FOOTER}</footer>\n</body>\n</html>\n"


def html_da_grade(grade: GradeDePoder) -> str:
    return html_das_grades((grade,))


def html_das_grades(grades: tuple[GradeDePoder, ...]) -> str:
    sections = "".join(_section(grade) for grade in grades)
    return f"{_PREFIX}{sections}{_SUFFIX}"


def _section(grade: GradeDePoder) -> str:
    return f"<section><h2>{_heading(grade)}</h2>{_table(grade)}</section>\n"


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


def _table(grade: GradeDePoder) -> str:
    largest = _largest(grade)
    parties = "".join(f"<th>{party}</th>" for party in grade.colunas)
    body = "".join(_row(row, largest) for row in grade.linhas)
    return (
        '<table><thead><tr><th class="lugar">Lugar</th>'
        f'<th class="validos">Votos válidos</th>{parties}</tr></thead>'
        f"<tbody>{body}</tbody></table>"
    )


def _row(row: LinhaGrade, largest: Fraction) -> str:
    validos = _votos_validos(row)
    place = f'<td class="lugar">{escape(row.nome)} <small>{escape(row.codigo)}</small></td>'
    valid = f'<td class="validos">{_inteiro(validos)}</td>'
    cells = "".join(_cell(cell, validos, largest) for cell in row.celulas)
    return f"<tr>{place}{valid}{cells}</tr>"


def _votos_validos(row: LinhaGrade) -> int:
    return sum(cell.votos for cell in row.celulas)


def _inteiro(value: int) -> str:
    return f"{value:,}".replace(",", ".")


def _cell(cell: CelulaGrade, validos: int, largest: Fraction) -> str:
    share = _sobre_validos(cell.votos, validos)
    title = escape(_title(cell, validos))
    return f'<td title="{title}" style="{_style(share, largest)}">{_percent(share)}</td>'


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
