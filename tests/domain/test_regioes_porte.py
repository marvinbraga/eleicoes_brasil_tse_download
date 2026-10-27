"""Regiões e porte: paired municipalities, size bands, round changes and the swing."""

from fractions import Fraction

import pytest

from eleicoes.domain.errors import InvalidBoletimConsultaError
from eleicoes.domain.mapa_turnos import FinalistsMissingError
from eleicoes.domain.presidente_governador import CargoTally, MunicipalPlace, PartyTally
from eleicoes.domain.regioes_porte import (
    FAIXAS_DE_PORTE,
    FaixaDePorte,
    LinhaGrupo,
    VotosTurno,
    faixa_de_porte,
    parte_do_ganho_de_a,
    regioes_e_porte,
    ufs_com_os_dois_turnos,
)


def _place(uf: str, codigo: str, votos: dict[int, int]) -> MunicipalPlace:
    parties = tuple(PartyTally(numero, total, 0) for numero, total in votos.items() if total)
    return MunicipalPlace(uf, codigo, f"M{codigo} ({uf})", CargoTally(parties, 5, 5), None)


def _turnos() -> tuple[list[MunicipalPlace], list[MunicipalPlace]]:
    primeiro = [
        _place("AC", "1007", {13: 300, 22: 500, 30: 200}),
        _place("BA", "35599", {13: 700, 22: 200, 30: 100}),
        _place("BA", "35600", {13: 100, 22: 100}),
        _place("SP", "71072", {13: 900, 22: 1000, 30: 100}),
        _place("RS", "88536", {13: 100, 22: 300}),
        _place("ZZ", "29505", {13: 40, 22: 60}),
    ]
    segundo = [
        _place("AC", "1007", {13: 450, 22: 550}),
        _place("BA", "35599", {13: 760, 22: 240}),
        _place("RS", "88536", {13: 150, 22: 250}),
        _place("ZZ", "29505", {13: 45, 22: 55}),
    ]
    return primeiro, segundo


_ELEITORES = {
    ("AC", "01007"): 10_000,
    ("BA", "35599"): 10_001,
    ("RS", "88536"): 2_000_000,
}


def test_size_band_edges_are_inclusive_at_the_top() -> None:
    assert faixa_de_porte(1).chave == "ate_10_mil"
    assert faixa_de_porte(10_000).chave == "ate_10_mil"
    assert faixa_de_porte(10_001).chave == "10_a_50_mil"
    assert faixa_de_porte(50_000).chave == "10_a_50_mil"
    assert faixa_de_porte(200_000).chave == "50_a_200_mil"
    assert faixa_de_porte(1_000_000).chave == "200_mil_a_1_milhao"
    assert faixa_de_porte(1_000_001).chave == "acima_de_1_milhao"
    assert len(FAIXAS_DE_PORTE) == 5


def test_size_band_rejects_negative_counts_and_bad_ceilings() -> None:
    with pytest.raises(InvalidBoletimConsultaError):
        faixa_de_porte(-1)
    with pytest.raises(InvalidBoletimConsultaError):
        FaixaDePorte("x", "x", 0)
    with pytest.raises(InvalidBoletimConsultaError):
        faixa_de_porte(20, (FaixaDePorte("x", "x", 10),))


def test_votes_reject_negative_and_impossible_totals() -> None:
    with pytest.raises(InvalidBoletimConsultaError):
        VotosTurno(-1, 0, 0)
    with pytest.raises(InvalidBoletimConsultaError):
        VotosTurno(3, 3, 5)
    vazio = VotosTurno(0, 0, 0)
    assert vazio.fatia_a == 0
    assert vazio.fatia_a_no_par == 0


def test_regions_pair_municipalities_and_keep_the_abroad_row() -> None:
    primeiro, segundo = _turnos()

    leitura = regioes_e_porte(2026, primeiro, segundo, _ELEITORES, ufs_no_boletim=("AC", "SP"))

    assert (leitura.a, leitura.b) == (13, 22)
    assert [linha.rotulo for linha in leitura.regioes] == ["Norte", "Nordeste", "Sul", "Exterior"]
    nordeste = leitura.regioes[1]
    assert nordeste.municipios == 1
    assert nordeste.primeiro == VotosTurno(700, 200, 1000)
    assert nordeste.segundo == VotosTurno(760, 240, 1000)
    assert nordeste.diferenca == 520
    assert nordeste.segundo.fatia_a == Fraction(76, 100)
    assert nordeste.variacao_a == 60
    assert nordeste.variacao_relativa_a == Fraction(60, 700)
    assert nordeste.variacao_b == 40
    assert nordeste.variacao_relativa_b == Fraction(40, 200)
    assert nordeste.virada == Fraction(76, 100) - Fraction(7, 9)
    assert leitura.brasil.municipios == 4
    assert leitura.brasil_sem_exterior.municipios == 3


def test_missing_rounds_and_report_gaps_are_listed() -> None:
    primeiro, segundo = _turnos()
    segundo.append(_place("AC", "1104", {13: 10, 22: 10}))

    leitura = regioes_e_porte(2026, primeiro, segundo, _ELEITORES, ufs_no_boletim=("AC", "SP"))

    assert "SP" in leitura.sem_segundo_turno
    assert "ZZ" not in leitura.sem_segundo_turno
    assert "BA" not in leitura.sem_segundo_turno
    assert leitura.fora_do_relatorio == ("SP",)
    assert leitura.so_no_primeiro == 1
    assert leitura.so_no_segundo == 1


def test_sizes_skip_abroad_and_count_municipalities_without_electorate() -> None:
    primeiro, segundo = _turnos()
    eleitores = {chave: valor for chave, valor in _ELEITORES.items() if chave[0] != "RS"}

    leitura = regioes_e_porte(2026, primeiro, segundo, eleitores)

    contagem = {linha.chave: linha.municipios for linha in leitura.portes}
    assert contagem == {
        "ate_10_mil": 1,
        "10_a_50_mil": 1,
        "50_a_200_mil": 0,
        "200_mil_a_1_milhao": 0,
        "acima_de_1_milhao": 0,
    }
    assert leitura.sem_eleitorado == 1
    vazia = leitura.portes[2]
    assert vazia.variacao_relativa_a is None
    assert vazia.virada == 0


def test_share_of_the_gain_and_reference_order() -> None:
    primeiro, segundo = _turnos()

    leitura = regioes_e_porte(2026, primeiro, segundo, _ELEITORES, referencia=22)

    assert (leitura.a, leitura.b) == (22, 13)
    total = leitura.brasil
    soma = sum(
        (parte_do_ganho_de_a(linha, total) or Fraction(0) for linha in leitura.regioes),
        Fraction(0),
    )
    assert soma == 1
    parado = LinhaGrupo("x", "x", 1, VotosTurno(1, 1, 2), VotosTurno(1, 1, 2))
    assert parte_do_ganho_de_a(parado, parado) is None


def test_finalists_are_required() -> None:
    primeiro, _ = _turnos()
    with pytest.raises(FinalistsMissingError):
        regioes_e_porte(2026, primeiro, [_place("AC", "1007", {13: 1})], {})


def test_states_with_both_rounds_leave_abroad_out() -> None:
    primeiro, segundo = _turnos()

    assert ufs_com_os_dois_turnos(primeiro, segundo) == ("AC", "BA", "RS")
