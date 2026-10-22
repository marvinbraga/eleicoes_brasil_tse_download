"""Proportional seats. Every expected number was worked out by hand."""

from collections.abc import Callable

import pytest

from eleicoes.domain.errors import InvalidSeatRuleError
from eleicoes.domain.proporcional import (
    FASE_MEDIA,
    FASE_MEDIA_LIVRE,
    FASE_QUOCIENTE,
    Candidato,
    Lista,
    ResultadoProporcional,
    distribuir,
    quociente_eleitoral,
)


def _lista(legenda: str, votos_legenda: int, *votos: tuple[int, int]) -> Lista:
    candidatos = tuple(Candidato(numero, numero // 100, qtd) for numero, qtd in votos)
    return Lista(legenda, votos_legenda, candidatos)


def _eleitos(resultado: ResultadoProporcional) -> list[tuple[int, str, bool]]:
    return [(eleito.numero, eleito.fase, eleito.empate) for eleito in resultado.eleitos]


def _por_lista(resultado: ResultadoProporcional) -> dict[str, tuple[int, int]]:
    return {item.legenda: (item.quociente_partidario, item.cadeiras) for item in resultado.listas}


def test_quociente_drops_one_half_and_rounds_up_above_it() -> None:
    assert quociente_eleitoral(1000, 8) == 125
    assert quociente_eleitoral(1004, 8) == 125
    assert quociente_eleitoral(1005, 8) == 126
    assert quociente_eleitoral(1010, 4) == 252
    assert quociente_eleitoral(3, 8) == 0


@pytest.mark.parametrize("vagas", [0, -1, True])
def test_quociente_needs_at_least_one_seat(vagas: int) -> None:
    with pytest.raises(InvalidSeatRuleError):
        quociente_eleitoral(10, vagas)


def test_list_without_a_twenty_percent_candidate_skips_the_second_phase() -> None:
    # 999 válidos, 4 vagas, QE 250. A tem a maior média (519/3), mas o 1003 tem 49 < 50.
    resultado = distribuir(
        4,
        [
            _lista("A", 20, (1001, 300), (1002, 150), (1003, 49)),
            _lista("B", 0, (2001, 200), (2002, 100)),
            _lista("C", 0, (3001, 180)),
        ],
    )
    assert resultado.quociente_eleitoral == 250
    assert _eleitos(resultado) == [
        (1001, FASE_QUOCIENTE, False),
        (1002, FASE_QUOCIENTE, False),
        (2001, FASE_QUOCIENTE, False),
        (2002, FASE_MEDIA, False),
    ]
    assert _por_lista(resultado) == {"A": (2, 2), "B": (1, 2), "C": (0, 0)}


def test_third_phase_opens_the_averages_to_every_list() -> None:
    # 700 válidos, 3 vagas, QE 233. Ninguém cumpre 80% + 20% depois do QP de A.
    resultado = distribuir(
        3,
        [
            _lista("A", 0, (1001, 400), (1002, 10)),
            _lista("B", 0, (2001, 150)),
            _lista("C", 0, (3001, 140)),
        ],
    )
    assert resultado.quociente_eleitoral == 233
    assert _eleitos(resultado) == [
        (1001, FASE_QUOCIENTE, False),
        (1002, FASE_MEDIA_LIVRE, False),
        (2001, FASE_MEDIA_LIVRE, False),
    ]


def test_no_list_reaching_the_quotient_still_uses_the_averages() -> None:
    # 400 válidos, 3 vagas, QE 133. Art. 111 caiu (ADI 7228): não elege os mais votados.
    resultado = distribuir(
        3,
        [
            _lista("A", 0, (1001, 90), (1002, 40)),
            _lista("B", 0, (2001, 110)),
            _lista("C", 0, (3001, 100)),
            _lista("D", 0, (4001, 60)),
        ],
    )
    assert resultado.quociente_eleitoral == 133
    assert _eleitos(resultado) == [
        (1001, FASE_MEDIA, False),
        (2001, FASE_MEDIA, False),
        (1002, FASE_MEDIA, False),
    ]
    assert _por_lista(resultado) == {"A": (0, 2), "B": (0, 1), "C": (0, 0), "D": (0, 0)}


def test_equal_averages_go_to_the_list_with_more_votes() -> None:
    # QE 100. Média de A = 180/2 = 90 e de B = 90/1 = 90; A tem mais votos (art. 11, § 6).
    resultado = distribuir(
        3,
        [
            _lista("A", 0, (1001, 100), (1002, 80)),
            _lista("B", 0, (2001, 90)),
            _lista("C", 0, (3001, 30)),
        ],
    )
    assert _eleitos(resultado) == [
        (1001, FASE_QUOCIENTE, False),
        (1002, FASE_MEDIA, False),
        (2001, FASE_MEDIA, False),
    ]


def test_candidate_with_exactly_ten_percent_takes_the_quotient_seat() -> None:
    # 200 válidos, 2 vagas, QE 100. A tem QP 1 e o 1001 tem 10 votos: 10% exatos bastam.
    resultado = distribuir(2, [_lista("A", 90, (1001, 10)), _lista("B", 0, (2001, 100))])
    assert resultado.quociente_eleitoral == 100
    assert _eleitos(resultado) == [(1001, FASE_QUOCIENTE, False), (2001, FASE_QUOCIENTE, False)]


def test_list_with_exactly_eighty_percent_and_a_twenty_percent_candidate_enters_phase_two() -> None:
    # 200 válidos, 2 vagas, QE 100. A tem 80 votos (80% exatos) e o 1001 tem 20 (20% exatos).
    # Na 2ª fase, A (80/1) vence B (120/2). Com limiar estrito, a vaga iria ao 2002 ou à 3ª fase.
    resultado = distribuir(
        2,
        [
            _lista("A", 60, (1001, 20)),
            _lista("B", 0, (2001, 100), (2002, 20)),
        ],
    )
    assert resultado.quociente_eleitoral == 100
    assert _eleitos(resultado) == [(2001, FASE_QUOCIENTE, False), (1001, FASE_MEDIA, False)]


def test_equal_average_and_votes_go_to_the_list_whose_next_candidate_has_more_votes() -> None:
    # 100 válidos, 1 vaga, QE 100. A e B têm 50 votos e média 50; o próximo de B tem 40 e o
    # de A, 30 (art. 11, § 7º). B ganha mesmo com o código maior, e não há empate a marcar.
    resultado = distribuir(1, [_lista("A", 20, (1001, 30)), _lista("B", 10, (2001, 40))])
    assert resultado.quociente_eleitoral == 100
    assert _eleitos(resultado) == [(2001, FASE_MEDIA_LIVRE, False)]


def test_full_tie_goes_to_the_smaller_code_and_is_flagged() -> None:
    resultado = distribuir(1, [_lista("B", 0, (2001, 50)), _lista("A", 0, (1001, 50))])
    assert _eleitos(resultado) == [(1001, FASE_MEDIA_LIVRE, True)]


def test_tied_candidates_go_to_the_smaller_number_and_are_flagged() -> None:
    resultado = distribuir(1, [_lista("A", 0, (1002, 60), (1001, 60))])
    assert _eleitos(resultado) == [(1001, FASE_QUOCIENTE, True)]


def test_average_divisor_counts_the_quotient_seat_left_empty() -> None:
    # 1010 válidos, 4 vagas, QE 252. A tem QP 2 e só o 1001 passa dos 10% (25,2).
    # Divisor de A = QP + médias + 1: 550/3 leva a 3ª vaga e 550/4 < 160 dá a 4ª a C.
    resultado = distribuir(
        4,
        [
            _lista("A", 480, (1001, 40), (1002, 20), (1003, 10)),
            _lista("B", 0, (2001, 300)),
            _lista("C", 0, (3001, 160)),
        ],
    )
    assert _eleitos(resultado) == [
        (1001, FASE_QUOCIENTE, False),
        (2001, FASE_QUOCIENTE, False),
        (1002, FASE_MEDIA_LIVRE, False),
        (3001, FASE_MEDIA_LIVRE, False),
    ]


def test_elected_candidate_keeps_the_party_of_the_candidate() -> None:
    # Federação: uma lista, dois partidos. Cada eleito leva o partido do próprio candidato.
    lista = Lista("fed", 0, (Candidato(1301, 13, 300), Candidato(6501, 65, 200)))
    resultado = distribuir(2, [lista])
    assert [(eleito.numero, eleito.partido) for eleito in resultado.eleitos] == [
        (1301, 13),
        (6501, 65),
    ]


def test_seats_without_candidates_stay_empty() -> None:
    resultado = distribuir(3, [_lista("A", 0, (1001, 300))])
    assert _eleitos(resultado) == [(1001, FASE_QUOCIENTE, False)]
    assert resultado.vagas_sem_candidato == 2


def test_no_valid_votes_fills_nothing() -> None:
    resultado = distribuir(8, [])
    assert resultado.quociente_eleitoral == 0
    assert resultado.eleitos == ()
    assert resultado.vagas_sem_candidato == 8


def test_legend_votes_count_for_the_list_and_candidates_are_sorted() -> None:
    lista = _lista("A", 7, (1002, 5), (1001, 9))
    assert lista.votos == 21
    assert [candidato.numero for candidato in lista.candidatos] == [1001, 1002]


@pytest.mark.parametrize(
    "build",
    [
        lambda: Lista(" ", 0, ()),
        lambda: Lista("A", -1, ()),
        lambda: Lista("A", 0, (Candidato(1001, 10, 1), Candidato(1001, 10, 2))),
        lambda: Candidato(1001, 10, -1),
        lambda: Candidato(1001, -1, 1),
        lambda: distribuir(1, [Lista("A", 0, ()), Lista("A", 0, ())]),
    ],
)
def test_bad_input_is_rejected(build: Callable[[], object]) -> None:
    with pytest.raises(InvalidSeatRuleError):
        build()


def test_quotient_phase_never_fills_more_than_the_seats() -> None:
    # 10 válidos, 4 vagas: QE 2 (resto 2 = metade, desprezado) e QP 5 > 4 vagas.
    resultado = distribuir(4, [_lista("A", 0, *((1001 + i, 2) for i in range(5)))])
    assert resultado.quociente_eleitoral == 2
    assert len(resultado.eleitos) == 4
    assert resultado.vagas_sem_candidato == 0


def test_zero_quotient_with_votes_keeps_the_lists_visible() -> None:
    # 3 válidos e 8 vagas: QE 0, ninguém se elege, mas a lista continua no resultado.
    resultado = distribuir(8, [_lista("A", 1, (1001, 2))])
    assert resultado.quociente_eleitoral == 0
    assert resultado.eleitos == ()
    assert _por_lista(resultado) == {"A": (0, 0)}
    assert resultado.listas[0].votos == 3
