"""Class HTML states the held-out quarter and is not a forecast."""

from fractions import Fraction

from eleicoes.adapters.html_classe_governador import html_classe_governador, texto_regra
from eleicoes.domain.classe_governador import ClassOutcome, ClassReport, RuleCut


def test_page_shows_the_test_rate_beside_the_baseline() -> None:
    report = ClassReport(
        2026,
        1,
        (13,),
        Fraction(3, 4),
        Fraction(1, 2),
        (
            ClassOutcome("consolidacao", 4, ((RuleCut(13, 0.4, True),),)),
            ClassOutcome("em_aberto", 2, ()),
        ),
        ("sem_governador",),
    )

    html = html_classe_governador(report)

    assert "Classe do governador a partir do presidente" in html
    assert "75,00%" in html
    assert "50,00%" in html
    assert "Acerto no teste" in html
    assert "Linha de base da maioria" in html
    assert "não ajustou a árvore" in html
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
        (ClassOutcome("consolidacao", 3, ((RuleCut(13, 0.2, True),),)),),
        (),
    )

    html = html_classe_governador(report)

    assert "Não separadas" not in html
