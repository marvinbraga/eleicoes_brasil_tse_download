"""HTML da classe do governador a partir da mistura presidencial."""

from fractions import Fraction
from html import escape
from typing import Final

from eleicoes.adapters.html_tema import render_page
from eleicoes.domain.classe_governador import ClassOutcome, ClassReport, RuleCut, UfScore
from eleicoes.domain.percentual import format_decimal, format_percent, format_ratio, round_half_up
from eleicoes.domain.presidente_governador import CLASS_LABELS

NOTES: Final[tuple[str, ...]] = (
    "O acerto vem de deixar cada UF de fora e prever seus municípios com a árvore das outras.",
    "As regras mostradas são da árvore ajustada com todos os municípios.",
    "Isto não é uma previsão do segundo turno.",
    "As fatias são só do presidente, sobre os votos válidos.",
    "O governador entra apenas na classe, não nas contas da árvore.",
)
_BELOW_BASELINE: Final = (
    "Num estado que o modelo não viu, as condições não acertam mais que as linhas de base. "
    "Elas descrevem esta eleição; não servem para prever outro estado."
)
_SORT_SCALE: Final = 1_000_000_000
_TABLE_OPEN: Final = (
    '<div class="table-responsive grade-scroll"><table class="table table-sm grade">'
)
_TABLE_CLOSE: Final = "</table></div>"


def html_classe_governador(report: ClassReport) -> str:
    subtitle = f"{report.ano} · turno {report.turno}"
    body = (
        _rates(report)
        + _warning(report)
        + _without_uf(report)
        + _held(report)
        + _states(report)
        + _table(report)
    )
    return render_page("Classe do governador a partir do presidente", subtitle, body, NOTES)


def texto_regra(cuts: tuple[RuleCut, ...]) -> str:
    if not cuts:
        return "A árvore não cortou esta classe."
    return "Se " + " e ".join(_clausula(cut) for cut in cuts) + "."


def _rates(report: ClassReport) -> str:
    hit = format_percent(report.hit_rate)
    base = format_percent(report.baseline)
    lider = format_percent(report.leader_baseline)
    f1 = format_decimal(float(report.macro_f1))
    return (
        f"<p>Acerto em UF não vista: <strong>{hit}</strong>. "
        f"Linha de base da maioria: <strong>{base}</strong>. "
        f"Linha de base do líder presidencial: <strong>{lider}</strong>. "
        f"F1 macro: <strong>{f1}</strong>.</p>"
    )


def _warning(report: ClassReport) -> str:
    if not report.below_baseline:
        return ""
    return f"<p>{escape(_BELOW_BASELINE)}</p>"


def _without_uf(report: ClassReport) -> str:
    if report.without_uf == 0:
        return ""
    if report.without_uf == 1:
        return "<p>1 município ficou de fora por não ter UF no relatório cruzado.</p>"
    return (
        f"<p>{report.without_uf} municípios ficaram de fora "
        "por não terem UF no relatório cruzado.</p>"
    )


def _held(report: ClassReport) -> str:
    if not report.held_out:
        return ""
    names = ", ".join(CLASS_LABELS[label] for label in report.held_out)
    return f"<p>Não separadas, com menos de 2 municípios: {escape(names)}.</p>"


def _states(report: ClassReport) -> str:
    head = (
        "<thead><tr>"
        '<th class="lugar" scope="col" aria-sort="none">UF</th>'
        '<th class="num" scope="col" aria-sort="none">Municípios</th>'
        '<th class="num" scope="col" aria-sort="none">Acerto</th>'
        "</tr></thead>"
    )
    body = "".join(_state(score) for score in report.by_uf)
    return f"{_TABLE_OPEN}{head}<tbody>{body}</tbody>{_TABLE_CLOSE}"


def _state(score: UfScore) -> str:
    uf = escape(score.uf)
    return (
        "<tr>"
        f'<td class="lugar" data-ord="{uf}">{uf}</td>'
        f'<td class="num" data-ord="{score.municipios}">{score.municipios}</td>'
        f"{_rate_cell(score.hit_rate)}"
        "</tr>"
    )


def _table(report: ClassReport) -> str:
    head = (
        "<thead><tr>"
        '<th class="lugar" scope="col" aria-sort="none">Classe</th>'
        '<th class="num" scope="col" aria-sort="none">Municípios</th>'
        '<th class="num" scope="col" aria-sort="none">Recall</th>'
        '<th class="lugar" scope="col" aria-sort="none">Regras</th>'
        "</tr></thead>"
    )
    body = "".join(_row(item) for item in report.rows)
    return f"{_TABLE_OPEN}{head}<tbody>{body}</tbody>{_TABLE_CLOSE}"


def _row(item: ClassOutcome) -> str:
    label = escape(CLASS_LABELS[item.classe])
    rules = _rules(item.rules)
    return (
        "<tr>"
        f'<td class="lugar" data-ord="{label}">{label}</td>'
        f'<td class="num" data-ord="{item.support}">{item.support}</td>'
        f"{_rate_cell(item.recall)}"
        f"<td>{rules}</td>"
        "</tr>"
    )


def _rate_cell(rate: Fraction) -> str:
    order = round_half_up(rate * _SORT_SCALE)
    return f'<td class="num" data-ord="{order}">{format_percent(rate)}</td>'


def _rules(rules: tuple[tuple[RuleCut, ...], ...]) -> str:
    if not rules:
        return escape("A árvore não cortou esta classe.")
    items = "".join(f"<li>{escape(texto_regra(cuts))}</li>" for cuts in rules)
    return f"<ul>{items}</ul>"


def _clausula(cut: RuleCut) -> str:
    relation = "menor ou igual a" if cut.at_most else "maior que"
    percent = format_ratio(cut.threshold)
    return f"a fatia do partido {cut.party} for {relation} {percent}"
