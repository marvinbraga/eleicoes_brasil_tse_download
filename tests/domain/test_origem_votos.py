"""Origem dos votos novos dos finalistas: identidade, resíduo, viradas e correlações."""

import math
from fractions import Fraction

import pytest

from eleicoes.domain.mapa_turnos import FinalistsMissingError
from eleicoes.domain.origem_votos import (
    Balanco,
    VotosDoTurno,
    analisar_origem,
    pearson_ponderado,
    reta_ponderada,
    spearman_ponderado,
)
from eleicoes.domain.presidente_governador import CargoTally, MunicipalPlace, PartyTally


def _place(
    uf: str, codigo: str, nome: str, votos: dict[int, int], bn: tuple[int, int]
) -> MunicipalPlace:
    parties = tuple(PartyTally(numero, total, 0) for numero, total in votos.items() if total > 0)
    return MunicipalPlace(uf, codigo, nome, CargoTally(parties, bn[0], bn[1]), None)


def _cedulas(votos: dict[int, int], bn: tuple[int, int]) -> int:
    return sum(votos.values()) + sum(bn)


def _cenario() -> tuple[
    list[MunicipalPlace], list[MunicipalPlace], dict[tuple[int, str, str], tuple[int, int]]
]:
    """Três municípios do AC (um de código com quatro dígitos) e um de AL. Rio Branco tem
    comparecimento diferente das cédulas só no 2º turno."""
    primeiro_votos = {
        ("AC", "1007"): ({13: 400, 22: 500, 30: 100}, (30, 20)),
        ("AC", "01392"): ({13: 3000, 22: 2000, 30: 1000}, (200, 100)),
        ("AC", "01120"): ({13: 1500, 22: 1700, 30: 300}, (60, 40)),
        ("AL", "27000"): ({13: 1200, 22: 900, 30: 500}, (100, 50)),
    }
    segundo_votos = {
        ("AC", "01007"): ({13: 450, 22: 610}, (20, 10)),
        ("AC", "01392"): ({13: 3700, 22: 2500}, (150, 100)),
        ("AC", "01120"): ({13: 1600, 22: 2000}, (60, 30)),
        ("AL", "27000"): ({13: 1300, 22: 1500}, (80, 30)),
    }
    nomes = {
        "1007": "Bujari",
        "01007": "Bujari",
        "01392": "Rio Branco",
        "01120": "Xapuri",
        "27000": "Maceió",
    }
    primeiro = [_place(uf, cod, nomes[cod], v, bn) for (uf, cod), (v, bn) in primeiro_votos.items()]
    segundo = [_place(uf, cod, nomes[cod], v, bn) for (uf, cod), (v, bn) in segundo_votos.items()]
    participacoes: dict[tuple[int, str, str], tuple[int, int]] = {}
    for turno, tabela in ((1, primeiro_votos), (2, segundo_votos)):
        for (uf, cod), (v, bn) in tabela.items():
            participacoes[(turno, uf, cod.zfill(5))] = (_cedulas(v, bn) + 500, _cedulas(v, bn))
    participacoes[(2, "AC", "01392")] = (7000, _cedulas(*segundo_votos[("AC", "01392")]) + 7)
    return primeiro, segundo, participacoes


def test_identity_holds_when_ballots_match_turnout() -> None:
    primeiro, segundo, participacoes = _cenario()
    origem = analisar_origem(primeiro, segundo, participacoes, minimo=0)
    bujari = next(m for m in origem.municipios if m.nome == "Bujari")
    b = bujari.balanco
    assert (origem.a, origem.b) == (13, 22)
    assert (b.delta_a, b.delta_b) == (50, 110)
    assert b.eliminados == 100
    assert b.delta_branco_nulo == -20
    assert b.brancos_nulos_liberados == 20
    assert b.delta_comparecimento == 1090 - 1050
    assert b.novos == b.eliminados - b.delta_branco_nulo + b.delta_comparecimento
    assert b.fecha
    assert b.delta_aptos == 40


def test_four_digit_codes_join_the_padded_participation_key() -> None:
    primeiro, segundo, participacoes = _cenario()
    origem = analisar_origem(primeiro, segundo, participacoes)
    assert [m.codigo for m in origem.municipios if m.nome == "Bujari"] == ["01007"]
    assert origem.sem_comparecimento == ()


def test_residual_isolates_a_turnout_mismatch_in_one_round() -> None:
    primeiro, segundo, participacoes = _cenario()
    origem = analisar_origem(primeiro, segundo, participacoes)
    rio = next(m for m in origem.municipios if m.nome == "Rio Branco").balanco
    assert rio.primeiro.sobra == 0
    assert rio.segundo.sobra == -7
    assert rio.residuo == rio.segundo.sobra - rio.primeiro.sobra - rio.segundo.outros == -7
    assert [m.nome for m in origem.falhas] == ["Rio Branco"]
    assert [(u.uf, u.municipios, u.falhas) for u in origem.ufs] == [("AC", 3, 1), ("AL", 1, 0)]


def test_residual_counts_votes_outside_the_finalists_in_round_two() -> None:
    um = VotosDoTurno(10, 10, 5, 5, 40, 30)
    dois = VotosDoTurno(14, 14, 2, 2, 40, 32)
    balanco = Balanco(um, dois)
    assert balanco.residuo == dois.sobra - um.sobra - dois.outros == -2
    assert not balanco.fecha


def test_totals_add_up_the_municipalities() -> None:
    primeiro, segundo, participacoes = _cenario()
    origem = analisar_origem(primeiro, segundo, participacoes)
    total = origem.total
    assert total.delta_a == sum(m.balanco.delta_a for m in origem.municipios)
    assert total.eliminados == 100 + 1000 + 300 + 500
    assert total.residuo == -7
    assert sum(u.balanco.novos for u in origem.ufs) == total.novos


def test_swing_is_the_change_in_the_first_finalist_share() -> None:
    primeiro, segundo, participacoes = _cenario()
    origem = analisar_origem(primeiro, segundo, participacoes)
    maceio = next(m for m in origem.municipios if m.nome == "Maceió").balanco
    assert maceio.virada == Fraction(1300, 2800) - Fraction(1200, 2100)


def test_top_lists_order_by_swing_and_respect_the_floor() -> None:
    primeiro, segundo, participacoes = _cenario()
    origem = analisar_origem(primeiro, segundo, participacoes, minimo=1000, topo=2)
    assert [m.nome for m in origem.topo_a] == ["Rio Branco", "Xapuri"]
    assert [m.nome for m in origem.topo_b] == ["Maceió", "Xapuri"]
    assert all(m.nome != "Bujari" for m in origem.topo_a + origem.topo_b)


def test_places_missing_in_one_round_or_without_turnout_are_listed() -> None:
    primeiro, segundo, participacoes = _cenario()
    primeiro.append(_place("AL", "27100", "Arapiraca", {13: 10, 22: 10}, (1, 1)))
    primeiro.append(_place("SP", "71072", "São Paulo", {13: 10, 22: 10}, (1, 1)))
    segundo.append(_place("AC", "01570", "Tarauacá", {13: 10, 22: 10}, (1, 1)))
    del participacoes[(1, "AL", "27000")]
    origem = analisar_origem(primeiro, segundo, participacoes)
    assert [lugar.nome for lugar in origem.so_no_primeiro] == ["Arapiraca"]
    assert [lugar.nome for lugar in origem.so_no_segundo] == ["Tarauacá"]
    assert [lugar.nome for lugar in origem.sem_comparecimento] == ["Maceió"]
    assert origem.ufs_sem_segundo_turno == ("SP",)


def test_scatters_carry_one_point_per_municipality() -> None:
    primeiro, segundo, participacoes = _cenario()
    origem = analisar_origem(primeiro, segundo, participacoes)
    pontos = origem.por_eliminados.pontos
    assert len(pontos) == 4
    bujari = next(p for p in pontos if p.nome == "Bujari")
    assert bujari.x == pytest.approx(10.0)
    assert bujari.peso == 1050
    assert bujari.regiao == "Norte"
    assert origem.por_comparecimento.pearson is not None


def test_round_two_without_two_finalists_fails() -> None:
    primeiro, _, participacoes = _cenario()
    with pytest.raises(FinalistsMissingError):
        analisar_origem(primeiro, [], participacoes)


def test_weighted_pearson_and_line_on_a_perfect_line() -> None:
    xs, ys, ws = [0.0, 1.0, 2.0, 3.0], [1.0, 3.0, 5.0, 7.0], [1.0, 2.0, 3.0, 4.0]
    assert pearson_ponderado(xs, ys, ws) == pytest.approx(1.0)
    assert reta_ponderada(xs, ys, ws) == pytest.approx((1.0, 2.0))
    assert pearson_ponderado(xs, [-y for y in ys], ws) == pytest.approx(-1.0)


def test_weights_change_the_pearson() -> None:
    xs, ys = [0.0, 1.0, 2.0], [0.0, 1.0, 0.0]
    leve = pearson_ponderado(xs, ys, [1.0, 1.0, 1.0])
    pesado = pearson_ponderado(xs, ys, [1.0, 1.0, 100.0])
    assert leve == pytest.approx(0.0)
    assert pesado is not None and pesado < -0.1


def test_spearman_sees_monotone_but_curved_data_as_perfect() -> None:
    xs = [1.0, 2.0, 3.0, 4.0, 5.0]
    ys = [math.exp(x) for x in xs]
    ws = [3.0, 1.0, 2.0, 5.0, 1.0]
    assert spearman_ponderado(xs, ys, ws) == pytest.approx(1.0)
    pearson = pearson_ponderado(xs, ys, ws)
    assert pearson is not None and pearson < 1.0


def test_spearman_handles_ties_with_the_mid_rank() -> None:
    assert spearman_ponderado([1.0, 1.0, 2.0], [1.0, 2.0, 3.0], [1.0, 1.0, 1.0]) == pytest.approx(
        math.sqrt(3) / 2
    )


def test_degenerate_inputs_return_none() -> None:
    assert pearson_ponderado([1.0], [1.0], [1.0]) is None
    assert pearson_ponderado([1.0, 1.0], [1.0, 2.0], [1.0, 1.0]) is None
    assert reta_ponderada([1.0, 1.0], [1.0, 2.0], [1.0, 1.0]) is None
    assert reta_ponderada([1.0, 2.0], [1.0, 2.0], [0.0, 0.0]) is None
    assert spearman_ponderado([1.0], [1.0], [1.0]) is None


def test_empty_shares_have_no_swing() -> None:
    vazio = VotosDoTurno(0, 0, 5, 5, 10, 10)
    cheio = VotosDoTurno(3, 2, 0, 5, 10, 10)
    assert vazio.parte_de_a is None
    assert Balanco(vazio, cheio).virada is None
