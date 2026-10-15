"""HTML dos perfis municipais. Os percentuais usam o meio para cima da grade."""

from fractions import Fraction
from html import escape
from typing import Final

from eleicoes.adapters.html_tema import render_page
from eleicoes.domain.percentual import format_decimal, format_integer, format_ratio, round_half_up
from eleicoes.domain.perfis import ProfileGroup, ProfileReport

_CARGO: Final = {
    "presidente": "Presidente",
    "governador": "Governador",
    "senador": "Senador",
}
NOTES: Final[tuple[str, ...]] = (
    "A fatia do partido é o voto do partido sobre os votos válidos do município.",
    "Branco e nulo são a parte deles sobre o comparecimento.",
    "Senador não tem branco nem nulo neste relatório.",
    "Os lugares do exterior permanecem no perfil de presidente.",
    "Os grupos são um ajuste desta eleição, não uma previsão.",
)
_SORT_SCALE: Final = 1_000_000_000


def html_perfis(report: ProfileReport) -> str:
    body = _section("grupos", "Grupos", _group_table(report))
    body += _section("municipios", "Municípios", _city_table(report))
    return render_page("Perfis municipais", _subtitle(report), body, NOTES)


def _subtitle(report: ProfileReport) -> str:
    cargo = escape(_CARGO[report.cargo])
    base = f"{cargo} · {report.ano} · turno {report.turno} · {report.k} grupos"
    if report.searched and report.silhouette is not None:
        return f"{base} · silhueta {format_decimal(report.silhouette)}"
    return f"{base} escolhidos"


def _group_table(report: ProfileReport) -> str:
    head = _head(("Grupo", "Municípios", "Comparecimento"), report)
    body = "".join(_group_row(group) for group in report.groups)
    return _table(head, body)


def _city_table(report: ProfileReport) -> str:
    head = (
        "<thead><tr>"
        '<th class="lugar" scope="col" aria-sort="none">Lugar</th>'
        '<th class="num" scope="col" aria-sort="none">Grupo</th>'
        "</tr></thead>"
    )
    body = "".join(_city_row(city.nome, city.codigo, city.grupo) for city in report.cities)
    return _table(head, body)


def _head(labels: tuple[str, str, str], report: ProfileReport) -> str:
    fixed = (
        f'<th class="lugar" scope="col" aria-sort="none">{labels[0]}</th>'
        f'<th class="num" scope="col" aria-sort="none">{labels[1]}</th>'
        f'<th class="num" scope="col" aria-sort="none">{labels[2]}</th>'
    )
    parties = "".join(
        f'<th class="num" scope="col" aria-sort="none" title="Partido {party}">{party}</th>'
        for party in report.parties
    )
    ballot = ""
    if report.with_ballot:
        ballot = (
            '<th class="num" scope="col" aria-sort="none">Branco</th>'
            '<th class="num" scope="col" aria-sort="none">Nulo</th>'
        )
    return f"<thead><tr>{fixed}{parties}{ballot}</tr></thead>"


def _group_row(group: ProfileGroup) -> str:
    cells = (
        _text_cell(f"Grupo {group.numero}", str(group.numero)),
        _num_cell(group.municipios, format_integer(group.municipios)),
        _num_cell(group.comparecimento, format_integer(group.comparecimento)),
    )
    shares = "".join(_share_cell(value) for value in group.center)
    return f"<tr>{''.join(cells)}{shares}</tr>"


def _city_row(nome: str, codigo: str, grupo: int) -> str:
    place = (
        f'<td class="lugar" data-ord="{escape(nome)}">{escape(nome)} '
        f"<small>{escape(codigo)}</small></td>"
    )
    return f"<tr>{place}{_num_cell(grupo, str(grupo))}</tr>"


def _share_cell(value: float) -> str:
    order = round_half_up(Fraction(value).limit_denominator(1_000_000_000) * _SORT_SCALE)
    return f'<td class="num" data-ord="{order}">{format_ratio(value)}</td>'


def _text_cell(label: str, order: str) -> str:
    return f'<td class="lugar" data-ord="{escape(order)}">{escape(label)}</td>'


def _num_cell(order: int, label: str) -> str:
    return f'<td class="num" data-ord="{order}">{label}</td>'


def _section(section_id: str, title: str, table: str) -> str:
    return f'<section id="{section_id}"><h2>{title}</h2>{table}</section>'


def _table(head: str, body: str) -> str:
    return (
        '<div class="table-responsive grade-scroll">'
        f'<table class="table table-sm grade">{head}<tbody>{body}</tbody></table>'
        "</div>"
    )
