"""HTML da classe do governador a partir da mistura presidencial."""

from html import escape
from typing import Final

from eleicoes.adapters.html_tema import render_page
from eleicoes.domain.classe_governador import ClassOutcome, ClassReport, RuleCut
from eleicoes.domain.percentual import format_percent, format_ratio
from eleicoes.domain.presidente_governador import CLASS_LABELS

NOTES: Final[tuple[str, ...]] = (
    "A taxa de acerto é o quarto dos municípios que não ajustou a árvore.",
    "Isto não é uma previsão do segundo turno.",
    "As fatias são só do presidente, sobre os votos válidos.",
    "O governador entra apenas na classe, não nas contas da árvore.",
)


def html_classe_governador(report: ClassReport) -> str:
    subtitle = f"{report.ano} · turno {report.turno}"
    body = _rates(report) + _held(report) + _table(report)
    return render_page("Classe do governador a partir do presidente", subtitle, body, NOTES)


def texto_regra(cuts: tuple[RuleCut, ...]) -> str:
    if not cuts:
        return "A árvore não cortou esta classe."
    return "Se " + " e ".join(_clausula(cut) for cut in cuts) + "."


def _rates(report: ClassReport) -> str:
    hit = format_percent(report.hit_rate)
    base = format_percent(report.baseline)
    return (
        "<p>Acerto no teste: "
        f"<strong>{hit}</strong>. Linha de base da maioria: <strong>{base}</strong>.</p>"
    )


def _held(report: ClassReport) -> str:
    if not report.held_out:
        return ""
    names = ", ".join(CLASS_LABELS[label] for label in report.held_out)
    return f"<p>Não separadas, com menos de 2 municípios: {escape(names)}.</p>"


def _table(report: ClassReport) -> str:
    head = (
        "<thead><tr>"
        '<th class="lugar" scope="col" aria-sort="none">Classe</th>'
        '<th class="num" scope="col" aria-sort="none">Municípios no teste</th>'
        '<th class="lugar" scope="col" aria-sort="none">Regras</th>'
        "</tr></thead>"
    )
    body = "".join(_row(item) for item in report.rows)
    return (
        '<div class="table-responsive grade-scroll">'
        f'<table class="table table-sm grade">{head}<tbody>{body}</tbody></table>'
        "</div>"
    )


def _row(item: ClassOutcome) -> str:
    label = escape(CLASS_LABELS[item.classe])
    rules = _rules(item.rules)
    return (
        "<tr>"
        f'<td class="lugar" data-ord="{label}">{label}</td>'
        f'<td class="num" data-ord="{item.support}">{item.support}</td>'
        f"<td>{rules}</td>"
        "</tr>"
    )


def _rules(rules: tuple[tuple[RuleCut, ...], ...]) -> str:
    if not rules:
        return escape("A árvore não cortou esta classe.")
    items = "".join(f"<li>{escape(texto_regra(cuts))}</li>" for cuts in rules)
    return f"<ul>{items}</ul>"


def _clausula(cut: RuleCut) -> str:
    relation = "menor ou igual a" if cut.at_most else "maior que"
    percent = format_ratio(cut.threshold)
    return f"a fatia do partido {cut.party} for {relation} {percent}"
