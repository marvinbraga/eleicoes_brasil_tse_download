"""HTML do cruzamento presidente × governador. O mesmo cromado da grade de poder."""

from fractions import Fraction
from html import escape
from typing import Final

from eleicoes.adapters.html_grade import (
    _BOOTSTRAP,
    _BOOTSTRAP_HASH,
    _SCRIPT,
    _STYLE,
    _THEME_BOOT,
    _inteiro,
    _percent,
    _round_half_up,
)
from eleicoes.domain.presidente_governador import (
    CLASS_LABELS,
    CLASS_ORDER,
    CargoReading,
    ClassSlice,
    Composition,
    CrossReportView,
    PlaceReading,
    RankedParty,
)
from eleicoes.domain.values import uf_name

_SORT_SCALE: Final = 1_000_000_000
_MARGIN: Final = 5
_MISSING: Final = "—"
_HEADERS: Final[tuple[str, ...]] = (
    "Lugar",
    "Líder presidente",
    "%",
    "Segundo",
    "%",
    "Margem",
    "Brancos presidente",
    "Nulos presidente",
    "Líder governador",
    "%",
    "Brancos governador",
    "Nulos governador",
    "Classe",
)
_NOTES: Final[tuple[str, ...]] = (
    (
        "A margem é o líder menos o segundo, sobre os votos válidos de presidente, "
        "em pontos percentuais."
    ),
    "A classe compara o partido do governador com esses dois partidos da presidência.",
    "Brancos e nulos ficam de fora do percentual, da margem e da classe.",
    "Número sem candidato a presidente conta como nulo.",
    "Clique no título da coluna para ordenar.",
)


def html_presidente_governador(view: CrossReportView) -> str:
    body = "".join(
        (
            _composition(view.composition),
            _municipalities(view),
            _level(view, "estado", "Por estado", view.states),
            _level(view, "regiao", "Por região", view.regions),
            _level(view, "pais", "No país", _country_rows(view)),
        ),
    )
    return f"{_prefix(view)}{body}{_suffix()}"


def _country_rows(view: CrossReportView) -> tuple[PlaceReading, ...]:
    if view.country is None:
        return ()
    return (view.country,)


def _prefix(view: CrossReportView) -> str:
    link = (
        f'<link rel="stylesheet" href="{_BOOTSTRAP}" '
        f'integrity="{_BOOTSTRAP_HASH}" crossorigin="anonymous">'
    )
    title = f"Presidente e governador — {view.ano}, turno {view.turno}"
    return (
        '<!DOCTYPE html>\n<html lang="pt-BR" data-bs-theme="dark">\n<head>\n'
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>{escape(title)}</title>\n"
        f"{_THEME_BOOT}{link}\n<style>{_STYLE}</style>\n</head>\n"
        "<body>\n"
        '<a class="pular" href="#conteudo">Ir para o conteúdo</a>\n'
        '<main id="conteudo" class="container-fluid py-4">\n'
        '<header class="masthead">\n<div>\n'
        f'<h1 class="h3 mb-4">{escape(title)}</h1>\n'
        "</div>\n</header>\n"
        '<nav class="indice" aria-label="Recortes"></nav>\n'
    )


def _suffix() -> str:
    items = "".join(f"<li>{escape(note)}</li>" for note in _NOTES)
    return f'<ul class="notas">{items}</ul>\n</main>\n{_SCRIPT}</body>\n</html>\n'


def _composition(composition: Composition) -> str:
    rows = "".join(_class_row(composition, item) for item in composition.classes)
    totals = (
        f'<p id="cedulas-presidente">Brancos de presidente: {_inteiro(composition.branco)}. '
        f"Nulos de presidente: {_inteiro(composition.nulo)}.</p>"
    )
    table = (
        '<table class="table table-sm grade mb-3"><thead><tr>'
        "<th>Classe</th><th>Municípios</th>"
        "<th>Votos válidos de presidente</th><th>Participação</th>"
        f"</tr></thead><tbody>{rows}</tbody></table>{totals}"
    )
    return _section("composicao", "Composição dos municípios", table)


def _class_row(composition: Composition, item: ClassSlice) -> str:
    share = _percent(composition.share_of(item.classe))
    label = escape(CLASS_LABELS[item.classe])
    votes = _inteiro(item.votos_validos)
    return (
        f'<tr data-classe="{escape(item.classe)}">'
        f"<td>{label}</td>"
        f'<td data-ord="{item.cidades}">{_inteiro(item.cidades)}</td>'
        f'<td data-ord="{item.votos_validos}">{votes}</td>'
        f"<td>{share}</td></tr>"
    )


def _municipalities(view: CrossReportView) -> str:
    blocks = "".join(_state_block(code, rows) for code, rows in view.municipalities)
    title = f"Por município — {view.ano}, turno {view.turno}"
    return _section("municipio", title, blocks)


def _state_block(code: str, rows: tuple[PlaceReading, ...]) -> str:
    title = f"{escape(uf_name(code))} ({escape(code)})"
    return f'<h3 class="h5 mt-4 mb-2">{title}</h3>{_table(rows)}'


def _level(
    view: CrossReportView,
    ident: str,
    title: str,
    rows: tuple[PlaceReading, ...],
) -> str:
    heading = f"{title} — {view.ano}, turno {view.turno}"
    return _section(ident, heading, _table(rows))


def _section(ident: str, title: str, body: str) -> str:
    return (
        f'<section class="mb-5" id="{ident}">'
        f'<h2 class="h4">{escape(title)}</h2>{body}</section>\n'
    )


def _table(rows: tuple[PlaceReading, ...]) -> str:
    body = "".join(_row(row) for row in rows)
    return (
        '<div class="table-responsive grade-scroll">'
        '<table class="table table-sm grade mb-4">'
        f"{_head()}<tbody>{body}</tbody></table></div>"
    )


def _head() -> str:
    cells = tuple(_header(index, label) for index, label in enumerate(_HEADERS))
    return "<thead><tr>" + "".join(cells) + "</tr></thead>"


def _header(index: int, label: str) -> str:
    sort = "ascending" if index == _MARGIN else "none"
    css = ' class="lugar"' if index == 0 else ""
    return f'<th{css} aria-sort="{sort}">{escape(label)}</th>'


def _row(reading: PlaceReading) -> str:
    cells = "".join(
        (
            _place_cell(reading),
            _named(reading.presidente.leader, reading.presidente),
            _named(reading.presidente.runner_up, reading.presidente),
            _margin_cell(reading),
            _cedula_cells(reading.presidente),
            _governor_cells(reading.governador),
            _class_cell(reading.classe),
        ),
    )
    return f"<tr>{cells}</tr>"


def _place_cell(reading: PlaceReading) -> str:
    nome = escape(reading.nome)
    return f'<td class="lugar" data-ord="{nome}">{nome}</td>'


def _named(party: RankedParty | None, cargo: CargoReading) -> str:
    if party is None:
        return _missing() + _missing()
    share = cargo.party_share(party.votos)
    return _text_cell(str(party.partido), party.partido) + _percent_cell(share)


def _governor_cells(cargo: CargoReading | None) -> str:
    if cargo is None or cargo.leader is None:
        return _missing() * 4
    share = cargo.party_share(cargo.leader.votos)
    leader = _text_cell(str(cargo.leader.partido), cargo.leader.partido)
    return leader + _percent_cell(share) + _cedula_cells(cargo)


def _cedula_cells(cargo: CargoReading) -> str:
    branco = _amount(cargo.branco, cargo.ballot_share(cargo.branco))
    nulo = _amount(cargo.nulo, cargo.ballot_share(cargo.nulo))
    return branco + nulo


def _margin_cell(reading: PlaceReading) -> str:
    share = reading.margin
    return f'<td class="margem" data-ord="{_order(share)}">{_points(share)}</td>'


def _class_cell(classe: str) -> str:
    label = escape(CLASS_LABELS[classe])
    return f'<td data-ord="{CLASS_ORDER.index(classe)}">{label}</td>'


def _text_cell(text: str, order: int) -> str:
    return f'<td data-ord="{order}">{escape(text)}</td>'


def _percent_cell(share: Fraction) -> str:
    return f'<td data-ord="{_order(share)}">{_percent(share)}</td>'


def _amount(value: int, share: Fraction) -> str:
    text = f"{_inteiro(value)} ({_percent(share)})"
    return f'<td data-ord="{_order(share)}">{text}</td>'


def _missing() -> str:
    return f'<td data-ord="-1">{_MISSING}</td>'


def _points(share: Fraction) -> str:
    return _percent(share).removesuffix("%")


def _order(share: Fraction) -> int:
    return _round_half_up(share * _SORT_SCALE)
