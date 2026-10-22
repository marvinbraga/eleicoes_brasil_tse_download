"""Senate and governor from first-round votes."""

import pytest

from eleicoes.domain.errors import InvalidSeatRuleError
from eleicoes.domain.majoritario import (
    SITUACAO_ELEITO,
    SITUACAO_SEGUNDO_TURNO,
    SITUACAO_SEM_VOTOS,
    VotoCandidato,
    apurar_governo,
    eleger_senado,
)


def _voto(numero: int, votos: int) -> VotoCandidato:
    return VotoCandidato(numero, numero // 10 if numero > 99 else numero, votos)


def test_senate_elects_the_two_most_voted() -> None:
    resultado = eleger_senado("AC", [_voto(100, 157), _voto(222, 223), _voto(111, 145)])
    assert [eleito.numero for eleito in resultado.eleitos] == [222, 100]
    assert resultado.votos_validos == 525
    assert resultado.empate is False


def test_senate_keeps_the_seat_left_without_a_candidate() -> None:
    resultado = eleger_senado("AC", [_voto(222, 9)])
    assert [eleito.numero for eleito in resultado.eleitos] == [222]
    assert (resultado.vagas, resultado.vagas_sem_candidato) == (2, 1)


def test_senate_flags_a_tie_for_the_second_seat() -> None:
    resultado = eleger_senado("AC", [_voto(222, 9), _voto(111, 5), _voto(100, 5)])
    assert [eleito.numero for eleito in resultado.eleitos] == [222, 100]
    assert resultado.empate is True


def test_governor_needs_more_than_half_of_the_valid_votes() -> None:
    eleito = apurar_governo("SE", [_voto(13, 51), _voto(22, 49)])
    assert eleito.situacao == SITUACAO_ELEITO
    assert eleito.eleito == _voto(13, 51)
    assert eleito.finalistas == ()
    metade = apurar_governo("SE", [_voto(13, 50), _voto(22, 30), _voto(45, 20)])
    assert metade.situacao == SITUACAO_SEGUNDO_TURNO
    assert metade.eleito is None
    assert [item.numero for item in metade.finalistas] == [13, 22]


def test_governor_without_votes_and_tied_runoff() -> None:
    assert apurar_governo("SE", []).situacao == SITUACAO_SEM_VOTOS
    empate = apurar_governo("SE", [_voto(13, 40), _voto(45, 30), _voto(22, 30)])
    assert [item.numero for item in empate.finalistas] == [13, 22]
    assert empate.empate is True


def test_repeated_number_is_rejected() -> None:
    with pytest.raises(InvalidSeatRuleError):
        eleger_senado("AC", [_voto(222, 1), _voto(222, 2)])
    with pytest.raises(InvalidSeatRuleError):
        VotoCandidato(222, 22, -1)
