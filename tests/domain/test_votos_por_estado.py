"""Como votou cada estado: finalistas, ordem, vitórias, cobertura e números compactos."""

from fractions import Fraction

import pytest

from eleicoes.domain.mapa_turnos import FinalistsMissingError
from eleicoes.domain.presidente_governador import CargoTally, MunicipalPlace, PartyTally
from eleicoes.domain.votos_por_estado import (
    Cobertura,
    CoberturaUrnas,
    InvalidCoverageError,
    LinhaEstado,
    SecoesIndice,
    StatesMissingError,
    cobertura_do_turno,
    votos_compactos,
    votos_por_estado,
)

_SEM_INDICE = CoberturaUrnas(Cobertura(0, None), {}, None)


def _place(uf: str, codigo: str, votos: dict[int, int]) -> MunicipalPlace:
    parties = tuple(PartyTally(numero, total, 0) for numero, total in votos.items())
    return MunicipalPlace(uf, codigo, f"{codigo} ({uf})", CargoTally(parties, 3, 4), None)


def _segundo_turno() -> tuple[MunicipalPlace, ...]:
    return (
        _place("PI", "1", {13: 700, 22: 300}),
        _place("PI", "2", {13: 80, 22: 20}),
        _place("SP", "3", {13: 400, 22: 600}),
        _place("AC", "4", {13: 50, 22: 50}),
        _place("ZZ", "5", {13: 10, 22: 30}),
    )


def test_rows_follow_the_reference_share_and_exterior_stays_apart() -> None:
    votos = votos_por_estado(2026, 2, _segundo_turno(), _SEM_INDICE)
    assert (votos.a, votos.b) == (13, 22)
    assert [linha.uf for linha in votos.estados] == ["PI", "AC", "SP"]
    pi = votos.estados[0]
    assert (pi.nome, pi.votos_a, pi.votos_b, pi.validos) == ("Piauí", 780, 320, 1100)
    assert pi.fatia_a == Fraction(780, 1100)
    assert pi.diferenca == 460
    assert votos.exterior is not None
    assert votos.exterior.nome == "Exterior"
    assert (votos.brasil.votos_a, votos.brasil.votos_b) == (1240, 1000)
    assert not votos.demais_omitidos


def test_wins_skip_ties_and_exterior() -> None:
    votos = votos_por_estado(2026, 2, _segundo_turno(), _SEM_INDICE)
    assert (votos.vitorias_a, votos.vitorias_b) == (1, 1)
    assert votos.estados[1].vencedor(13, 22) is None


def test_missing_states_are_listed_in_code_order() -> None:
    votos = votos_por_estado(2026, 2, _segundo_turno(), _SEM_INDICE)
    assert "SE" in votos.faltando and "TO" in votos.faltando
    assert "PI" not in votos.faltando and "ZZ" not in votos.faltando
    assert len(votos.faltando) == 24


def test_first_round_keeps_other_candidates_in_the_denominator() -> None:
    places = (
        _place("BA", "1", {22: 300, 13: 500, 30: 200}),
        _place("SC", "2", {22: 600, 13: 200, 30: 200}),
    )
    votos = votos_por_estado(2026, 1, places, _SEM_INDICE)
    assert (votos.a, votos.b) == (13, 22)
    assert votos.estados[0].fatia_a == Fraction(1, 2)
    assert votos.demais_omitidos
    assert votos.exterior is None


def test_without_the_reference_the_leader_comes_first() -> None:
    places = (_place("BA", "1", {22: 300, 30: 500, 12: 200}),)
    votos = votos_por_estado(2026, 1, places, _SEM_INDICE)
    assert (votos.a, votos.b) == (30, 22)


def test_empty_store_and_single_candidate_are_rejected() -> None:
    with pytest.raises(StatesMissingError) as error:
        votos_por_estado(2026, 2, (), _SEM_INDICE)
    assert (error.value.ano, error.value.turno) == (2026, 2)
    with pytest.raises(FinalistsMissingError):
        votos_por_estado(2026, 2, (_place("BA", "1", {13: 10}),), _SEM_INDICE)


def test_empty_row_has_zero_shares() -> None:
    linha = LinhaEstado("BA", "Bahia", 0, 0, 0)
    assert linha.fatia_a == 0
    assert linha.fatia_b == 0


def test_second_round_coverage_uses_the_first_round_sections() -> None:
    contagem = {
        (1, "PI"): SecoesIndice(10, 10),
        (1, "SE"): SecoesIndice(5, 5),
        (2, "PI"): SecoesIndice(10, 8),
        (2, "XX"): SecoesIndice(0, 0),
    }
    cobertura = cobertura_do_turno(contagem, 2)
    assert cobertura.base == 1
    assert cobertura.total == Cobertura(8, 15)
    assert cobertura.total.fatia == Fraction(8, 15)
    assert cobertura.por_uf["SE"] == Cobertura(0, 5)
    assert cobertura.por_uf["XX"] == Cobertura(0, None)


def test_partial_badge_only_when_the_index_shows_missing_sections() -> None:
    contagem = {(1, "PI"): SecoesIndice(10, 10), (1, "SP"): SecoesIndice(4, 4)}
    contagem |= {(2, "PI"): SecoesIndice(10, 9), (2, "SP"): SecoesIndice(4, 4)}
    votos = votos_por_estado(2026, 2, _segundo_turno(), cobertura_do_turno(contagem, 2))
    assert votos.parcial("PI") == Fraction(9, 10)
    assert votos.parcial("SP") is None
    assert votos.parcial("AC") is None


def test_coverage_without_a_first_round_has_no_expected_count() -> None:
    cobertura = cobertura_do_turno({(2, "PI"): SecoesIndice(10, 8)}, 2)
    assert cobertura.base is None
    assert cobertura.total == Cobertura(8, None)
    assert cobertura.total.fatia is None
    assert cobertura.por_uf["PI"].fatia is None


@pytest.mark.parametrize(
    ("listadas", "com_boletim", "campo"),
    [(-1, 0, "listadas"), (2, 3, "com_boletim"), (2, -1, "com_boletim")],
)
def test_invalid_index_counts_are_rejected(listadas: int, com_boletim: int, campo: str) -> None:
    with pytest.raises(InvalidCoverageError) as error:
        SecoesIndice(listadas, com_boletim)
    assert error.value.field == campo


def test_invalid_coverage_is_rejected() -> None:
    with pytest.raises(InvalidCoverageError):
        Cobertura(-1, None)
    with pytest.raises(InvalidCoverageError):
        Cobertura(1, -1)
    assert Cobertura(0, 0).fatia is None


@pytest.mark.parametrize(
    ("votos", "texto"),
    [
        (0, "0"),
        (999, "999"),
        (1000, "1 mil"),
        (24_400, "24 mil"),
        (929_400, "929 mil"),
        (999_499, "999 mil"),
        (999_600, "1,00 mi"),
        (1_130_000, "1,13 mi"),
        (3_875_000, "3,88 mi"),
        (12_345_678_901, "12.345,68 mi"),
    ],
)
def test_compact_votes(votos: int, texto: str) -> None:
    assert votos_compactos(votos) == texto


def test_compact_votes_reject_negatives() -> None:
    with pytest.raises(InvalidCoverageError):
        votos_compactos(-1)
