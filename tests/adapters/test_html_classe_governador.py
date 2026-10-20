"""Class HTML states the leave-one-state-out validation and is not a forecast."""

from fractions import Fraction

from tests.support import hand_class_report

from eleicoes.adapters.html_classe_governador import html_classe_governador, texto_regra
from eleicoes.domain.classe_governador import ClassOutcome, ClassReport, RuleCut, UfScore

_WARNING = (
    "Num estado que o modelo não viu, as condições não acertam mais que as linhas de base. "
    "Elas descrevem esta eleição; não servem para prever outro estado."
)


def test_page_shows_the_test_rate_beside_the_baseline() -> None:
    report = ClassReport(
        2026,
        1,
        (13,),
        Fraction(3, 4),
        Fraction(1, 2),
        (
            ClassOutcome("consolidacao", 4, ((RuleCut(13, 0.4, True),),), Fraction(3, 4)),
            ClassOutcome("em_aberto", 2, (), Fraction(1, 2)),
        ),
        ("sem_governador",),
        Fraction(1, 2),
        Fraction(2, 3),
        (UfScore("SP", 6, Fraction(3, 4)),),
        0,
    )

    html = html_classe_governador(report)

    assert "Classe do governador a partir do presidente" in html
    assert "75,00%" in html
    assert "50,00%" in html
    assert "Acerto em UF não vista" in html
    assert "Linha de base da maioria" in html
    assert "deixar cada UF de fora" in html
    assert "árvore ajustada com todos os municípios" in html
    assert "Acerto no teste" not in html
    assert "Municípios no teste" not in html
    assert "não é uma previsão do segundo turno" in html
    assert "Se a fatia do partido 13 for menor ou igual a 40,00%." in html
    assert "Consolidação" in html
    assert "Em aberto" in html
    assert "A árvore não cortou esta classe." in html
    assert "Sem governador" in html
    assert "Não separadas" in html


def test_rule_text_covers_both_sides_of_a_cut() -> None:
    assert texto_regra(()) == "A árvore não cortou esta classe."
    text = texto_regra((RuleCut(22, 0.1, False), RuleCut(13, 0.5, True)))
    assert text == (
        "Se a fatia do partido 22 for maior que 10,00% e "
        "a fatia do partido 13 for menor ou igual a 50,00%."
    )


def test_page_without_held_out_classes_omits_that_sentence() -> None:
    report = ClassReport(
        2026,
        1,
        (13,),
        Fraction(1, 1),
        Fraction(1, 1),
        (ClassOutcome("consolidacao", 3, ((RuleCut(13, 0.2, True),),), Fraction(1)),),
        (),
        Fraction(1),
        Fraction(1),
        (UfScore("SP", 3, Fraction(1)),),
        0,
    )

    html = html_classe_governador(report)

    assert "Não separadas" not in html


def test_page_explains_the_state_validation_and_lists_each_state() -> None:
    page = html_classe_governador(hand_class_report())
    assert "Acerto em UF não vista" in page
    assert "Linha de base do líder presidencial" in page
    assert "F1 macro" in page
    assert '<th class="num" scope="col" aria-sort="none">Recall</th>' in page
    assert '<td class="lugar" data-ord="AC">AC</td>' in page


def test_rates_sentence_lists_both_baselines_and_the_macro_f1() -> None:
    page = html_classe_governador(hand_class_report())
    assert (
        "<p>Acerto em UF não vista: <strong>83,33%</strong>. "
        "Linha de base da maioria: <strong>16,67%</strong>. "
        "Linha de base do líder presidencial: <strong>100,00%</strong>. "
        "F1 macro: <strong>0,8286</strong>.</p>"
    ) in page
    assert '<th class="num" scope="col" aria-sort="none">Municípios</th>' in page
    assert '<td class="num" data-ord="666666667">66,67%</td>' in page


def test_state_table_comes_before_the_rules_table() -> None:
    page = html_classe_governador(hand_class_report())
    states = page.index('aria-sort="none">UF</th>')
    rules = page.index('scope="col" aria-sort="none">Regras</th>')
    assert states < rules
    assert '<td class="lugar" data-ord="BA">BA</td><td class="num" data-ord="3">3</td>' in page
    assert '<td class="num" data-ord="500000000">50,00%</td>' in page


def test_rate_below_a_baseline_warns_right_after_the_rates() -> None:
    page = html_classe_governador(hand_class_report())
    assert f"<p>{_WARNING}</p>" in page
    states = page.index('aria-sort="none">UF</th>')
    assert page.index("F1 macro") < page.index(_WARNING) < states


def test_rate_at_the_baselines_has_no_warning() -> None:
    report = ClassReport(
        2026,
        1,
        (13,),
        Fraction(1),
        Fraction(1),
        (ClassOutcome("consolidacao", 3, (), Fraction(1)),),
        (),
        Fraction(1),
        Fraction(1),
        (UfScore("SP", 3, Fraction(1)),),
        0,
    )
    assert _WARNING not in html_classe_governador(report)


def test_places_without_uf_are_counted_in_a_sentence() -> None:
    sentence = "2 municípios ficaram de fora por não terem UF no relatório cruzado."
    assert f"<p>{sentence}</p>" in html_classe_governador(hand_class_report(without_uf=2))
    assert "ficaram de fora" not in html_classe_governador(hand_class_report())


def test_one_place_without_uf_is_counted_in_the_singular() -> None:
    sentence = "1 município ficou de fora por não ter UF no relatório cruzado."
    page = html_classe_governador(hand_class_report(without_uf=1))
    assert f"<p>{sentence}</p>" in page
    assert "ficaram de fora" not in page
