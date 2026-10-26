"""Seções no 1º × 2º turno: pareamento, grupo do z, piso e verificações."""

from fractions import Fraction
from math import isclose

import pytest

from eleicoes.domain.anomalia_secao import (
    ACIMA_DOS_APTOS,
    APTOS_MUDARAM,
    CEDULAS_DESTOANTES,
    GRUPO_MUNICIPIO,
    GRUPO_NENHUM,
    GRUPO_UF,
    GRUPO_ZONA,
    ContagemCenario,
    SecaoTurnos,
    _limites_das_faixas,
    alertas_da_secao,
    analisar_secoes,
    apuracao_da_secao,
    cauda_normal,
    com_alerta,
    destaques,
)
from eleicoes.domain.boletim_consulta import VotosSecao
from eleicoes.domain.errors import InvalidBoletimConsultaError
from eleicoes.domain.mapa_turnos import FORA_B, SEM_BASE, FinalistsMissingError

_PROPORCIONAL = 3


def _secao(
    municipio: int,
    zona: int,
    secao: int,
    votos: tuple[int, int, int],
    *,
    aptos: int = 400,
    branco: int = 5,
    nulo: int = 5,
) -> VotosSecao:
    a, b, outros = votos
    nominais = tuple(
        (numero, total) for numero, total in ((13, b), (22, a), (30, outros)) if total > 0
    )
    return VotosSecao(municipio, zona, secao, aptos, 0, branco, nulo, nominais)


def _cidade(municipio: int, zona: int, quantas: int, primeira: int = 1) -> list[VotosSecao]:
    return [_secao(municipio, zona, primeira + i, (120, 100, 20)) for i in range(quantas)]


def _segundo(municipio: int, zona: int, quantas: int, primeira: int = 1) -> list[VotosSecao]:
    return [
        _secao(municipio, zona, primeira + i, (130 + i % 4, 110 - i % 3, 0)) for i in range(quantas)
    ]


def _por_chave(secoes: tuple[SecaoTurnos, ...]) -> dict[tuple[int, int, int], SecaoTurnos]:
    return {(secao.municipio, secao.zona, secao.secao): secao for secao in secoes}


def test_sections_pair_by_place_and_unmatched_ones_are_only_counted() -> None:
    primeiro = {"AC": [*_cidade(1, 1, 10), _secao(1, 1, 99, (120, 100, 20))]}
    segundo = {"AC": [*_segundo(1, 1, 10), _secao(1, 1, 77, (130, 110, 0))]}
    analise = analisar_secoes(primeiro, segundo, {"AC": {1: "Rio Branco"}})
    resumo = analise.resumos[0]
    assert (resumo.pareadas, resumo.so_no_primeiro, resumo.so_no_segundo) == (10, 1, 1)
    assert analise.total.pareadas == 10
    assert analise.secoes[0].nome == "Rio Branco"
    assert (analise.a, analise.b) == (22, 13)


def test_supported_finalist_comes_first_and_missing_finalists_fail() -> None:
    primeiro = {"AC": _cidade(1, 1, 10)}
    segundo = {"AC": _segundo(1, 1, 10)}
    analise = analisar_secoes(primeiro, segundo, {}, apoiado=13)
    assert (analise.a, analise.b) == (13, 22)
    assert analise.secoes[0].nome == "1"
    sozinho = {"AC": [VotosSecao(1, 1, 1, 300, 0, 0, 0, ((22, 200),))]}
    with pytest.raises(FinalistsMissingError):
        analisar_secoes(sozinho, sozinho, {})


def test_outlier_is_measured_within_its_municipality() -> None:
    primeiro = {"AC": _cidade(1, 1, 12)}
    segundo = {"AC": [*_segundo(1, 1, 11), _secao(1, 1, 12, (60, 180, 0))]}
    analise = analisar_secoes(primeiro, segundo, {})
    secoes = _por_chave(analise.secoes)
    fora = secoes[(1, 1, 12)]
    leitura = fora.leituras[_PROPORCIONAL]
    assert fora.grupo == GRUPO_MUNICIPIO
    assert leitura.classe == FORA_B
    assert leitura.z is not None and leitura.z < -3.5
    assert leitura.esperado == Fraction(120, 220)
    assert leitura.real == Fraction(60, 240)
    assert leitura.votos_de_diferenca == round((Fraction(60, 240) - Fraction(120, 220)) * 240)
    contagem = analise.total.cenarios[_PROPORCIONAL]
    assert contagem.com_z == 12
    assert contagem.fora_b >= 1
    assert destaques(analise, _PROPORCIONAL)[0] is fora


def test_small_municipality_falls_back_to_zone_then_to_uf() -> None:
    primeiro = {
        "AC": [*_cidade(1, 5, 10), *_cidade(2, 5, 3, 50), *_cidade(3, 9, 2, 80)],
    }
    segundo = {
        "AC": [*_segundo(1, 5, 10), *_segundo(2, 5, 3, 50), *_segundo(3, 9, 2, 80)],
    }
    analise = analisar_secoes(primeiro, segundo, {})
    secoes = _por_chave(analise.secoes)
    assert secoes[(1, 5, 1)].grupo == GRUPO_MUNICIPIO
    assert secoes[(2, 5, 50)].grupo == GRUPO_ZONA
    assert secoes[(3, 9, 80)].grupo == GRUPO_UF
    assert secoes[(2, 5, 50)].leituras[_PROPORCIONAL].z is not None
    assert analise.resumos[0].por_grupo == (10, 3, 2, 0)


def test_sections_below_the_floor_get_no_z_and_tiny_states_have_no_base() -> None:
    primeiro = {"AC": [*_cidade(1, 1, 10), _secao(1, 1, 50, (40, 30, 5))]}
    segundo = {"AC": [*_segundo(1, 1, 10), _secao(1, 1, 50, (40, 30, 0))]}
    analise = analisar_secoes(primeiro, segundo, {})
    pequena = _por_chave(analise.secoes)[(1, 1, 50)]
    assert not pequena.comparavel
    assert pequena.leituras[0].z is None
    assert pequena.leituras[0].classe == SEM_BASE
    assert analise.total.abaixo_do_piso == 1
    assert analise.total.comparaveis == 10

    poucas = analisar_secoes({"AP": _cidade(1, 1, 3)}, {"AP": _segundo(1, 1, 3)}, {})
    assert {secao.grupo for secao in poucas.secoes} == {GRUPO_NENHUM}
    assert all(secao.leituras[0].z is None for secao in poucas.secoes)


def test_identical_sections_have_no_scale() -> None:
    iguais = [_secao(1, 1, i, (130, 110, 0)) for i in range(1, 11)]
    analise = analisar_secoes({"AC": _cidade(1, 1, 10)}, {"AC": iguais}, {})
    assert all(secao.leituras[0].z is None for secao in analise.secoes)


def test_hard_checks_are_independent_of_the_scenario() -> None:
    normal = _secao(1, 1, 1, (120, 100, 20))
    assert alertas_da_secao(normal, normal) == ()
    acima = _secao(1, 1, 1, (120, 100, 20), aptos=200)
    assert ACIMA_DOS_APTOS in alertas_da_secao(normal, acima)
    caiu = _secao(1, 1, 1, (50, 40, 0))
    assert alertas_da_secao(normal, caiu) == (CEDULAS_DESTOANTES,)
    pouco = _secao(1, 1, 1, (5, 5, 0), branco=0, nulo=0)
    pouquissimo = _secao(1, 1, 1, (2, 1, 0), branco=0, nulo=0)
    assert alertas_da_secao(pouco, pouquissimo) == ()
    mudou = _secao(1, 1, 1, (120, 100, 20), aptos=460)
    assert alertas_da_secao(normal, mudou) == (APTOS_MUDARAM,)
    quase = _secao(1, 1, 1, (120, 100, 20), aptos=405)
    assert alertas_da_secao(normal, quase) == ()

    primeiro = {"AC": _cidade(1, 1, 10)}
    segundo = {"AC": [*_segundo(1, 1, 9), _secao(1, 1, 10, (50, 40, 0), aptos=460)]}
    analise = analisar_secoes(primeiro, segundo, {})
    marcadas = com_alerta(analise)
    assert len(marcadas) == 1
    assert marcadas[0].alertas == (CEDULAS_DESTOANTES, APTOS_MUDARAM)
    assert analise.total.alertas == (0, 1, 1)


def test_expected_counts_follow_the_normal_tail() -> None:
    assert isclose(cauda_normal(3.5), 4.6525e-4, rel_tol=1e-3)
    contagem = ContagemCenario(100_000, 30, 20, 4000)
    assert contagem.fora == 50
    assert isclose(contagem.fora_esperado, 46.5, rel_tol=1e-2)
    assert contagem.acima_de_dois == 4050
    assert isclose(contagem.acima_de_dois_esperado, 4550, rel_tol=1e-2)


def test_vote_bands_start_at_the_floor() -> None:
    assert _limites_das_faixas(150) == ((150, 249), (250, 399), (400, None))
    assert _limites_das_faixas(300) == ((300, 399), (400, None))
    analise = analisar_secoes({"AC": _cidade(1, 1, 10)}, {"AC": _segundo(1, 1, 10)}, {})
    faixa = analise.faixas[0][0]
    assert (faixa.minimo, faixa.maximo, faixa.secoes) == (150, 249, 10)


def test_highlights_keep_a_limit_per_state() -> None:
    primeiro = {"AC": _cidade(1, 1, 10), "AL": _cidade(2, 1, 10)}
    segundo = {"AC": _segundo(1, 1, 10), "AL": _segundo(2, 1, 10)}
    analise = analisar_secoes(primeiro, segundo, {})
    escolhidas = destaques(analise, 0, por_uf=2)
    assert len(escolhidas) == 4
    assert {secao.uf for secao in escolhidas} == {"AC", "AL"}
    assert [resumo.uf for resumo in analise.resumos] == ["AC", "AL"]


def test_apuracao_splits_finalists_and_others() -> None:
    votos = _secao(1, 1, 1, (120, 100, 20))
    conta = apuracao_da_secao(votos, 22, 13)
    assert (conta.a, conta.b, conta.outros, conta.cedulas) == (120, 100, 20, 250)


def test_section_votes_reject_repeated_or_bad_numbers() -> None:
    with pytest.raises(InvalidBoletimConsultaError):
        VotosSecao(1, 1, 1, 300, 0, 0, 0, ((22, 1), (13, 1)))
    with pytest.raises(InvalidBoletimConsultaError):
        VotosSecao(1, 1, 1, 300, 0, 0, 0, ((22, 1), (22, 1)))
    with pytest.raises(InvalidBoletimConsultaError):
        VotosSecao(1, 1, 1, -1, 0, 0, 0, ())


def test_numbers_without_a_candidate_count_as_null() -> None:
    votos = VotosSecao(1, 1, 1, 400, 0, 2, 3, ((13, 100), (22, 120), (28, 7), (70, 20)))

    conta = apuracao_da_secao(votos, 22, 13)

    assert (conta.a, conta.b, conta.outros, conta.nulo) == (120, 100, 20, 10)
    assert conta.cedulas == votos.cedulas
