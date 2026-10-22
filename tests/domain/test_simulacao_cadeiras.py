"""Whole simulation from stored votes. Two small UFs keep the numbers readable."""

import pytest

from eleicoes.domain.errors import InvalidSeatRuleError, UnsupportedSeatTurnError
from eleicoes.domain.federacoes import REGISTRO_2026
from eleicoes.domain.simulacao_cadeiras import ForcaPartido, VotoApurado, simular_cadeiras


def _v(cargo: str, uf: str, tipo: str, numero: int, votos: int) -> VotoApurado:
    return VotoApurado(cargo, uf, tipo, numero, votos)


_VOTOS = (
    # Câmara AC, 8 vagas, 800 válidos, QE 100. PT + PCdoB somam como Fe Brasil.
    _v("deputadoFederal", "AC", "nominal", 1301, 250),
    _v("deputadoFederal", "AC", "nominal", 6501, 150),
    _v("deputadoFederal", "AC", "legenda", 65, 10),
    _v("deputadoFederal", "AC", "nominal", 2201, 200),
    _v("deputadoFederal", "AC", "nominal", 2202, 90),
    _v("deputadoFederal", "AC", "nominal", 4401, 60),
    _v("deputadoFederal", "AC", "nominal", 1101, 40),
    # Prefixo 99 não é partido: vira nulo.
    _v("deputadoFederal", "AC", "nominal", 9901, 7),
    _v("deputadoDistrital", "DF", "nominal", 1501, 100),
    _v("senador", "AC", "nominal", 222, 300),
    _v("senador", "AC", "nominal", 131, 200),
    _v("senador", "AC", "nominal", 100, 100),
    _v("governador", "AC", "nominal", 13, 600),
    _v("governador", "AC", "nominal", 22, 400),
    _v("governador", "DF", "nominal", 22, 450),
    _v("governador", "DF", "nominal", 15, 350),
    _v("governador", "DF", "nominal", 13, 200),
    # O exterior não elege ninguém.
    _v("governador", "ZZ", "nominal", 13, 5),
)


def test_federation_is_one_list_and_seats_go_to_each_candidate_party() -> None:
    simulacao = simular_cadeiras(2026, 1, _VOTOS, REGISTRO_2026)
    ac = simulacao.camara.ufs[0]
    assert ac.uf == "AC"
    assert ac.resultado.votos_validos == 800
    assert ac.resultado.quociente_eleitoral == 100
    # QP: Fe Brasil 4, PL 2, UP 1. Fe Brasil só tem 2 candidatos; UP leva 1 média (100/2);
    # as 2 vagas restantes ficam sem candidato.
    assert simulacao.camara.cadeiras_por_legenda() == {
        "fe-brasil": 2,
        "22": 2,
        "uniao-progressista": 2,
    }
    assert simulacao.camara.cadeiras_por_partido() == {13: 1, 65: 1, 22: 2, 44: 1, 11: 1}
    assert ac.resultado.vagas_sem_candidato == 2
    assert simulacao.descartados == 12


def test_missing_ufs_are_listed_and_df_assembly_reads_distrital() -> None:
    simulacao = simular_cadeiras(2026, 1, _VOTOS, REGISTRO_2026)
    assert simulacao.camara.vagas == 513
    assert simulacao.camara.vagas_simuladas == 8
    assert len(simulacao.camara.ufs_sem_votos) == 26
    assert [item.uf for item in simulacao.assembleias.ufs] == ["DF"]
    assert simulacao.assembleias.ufs[0].cargo == "deputadoDistrital"
    assert simulacao.assembleias.vagas == 1059


def test_senate_and_governor_feed_the_party_contract() -> None:
    simulacao = simular_cadeiras(2026, 1, _VOTOS, REGISTRO_2026)
    assert simulacao.senado.cadeiras_por_partido() == {22: 1, 13: 1}
    assert simulacao.governo.eleitos_por_partido() == {13: 1}
    assert simulacao.governo.segundo_turno_por_partido() == {22: 1, 15: 1}
    linhas = {linha.partido: linha for linha in simulacao.partidos()}
    assert linhas[13] == ForcaPartido(13, "fe-brasil", 1, 0, 1, 1, 0)
    assert linhas[22] == ForcaPartido(22, "22", 2, 0, 1, 0, 1)
    assert linhas[15] == ForcaPartido(15, "15", 0, 1, 0, 0, 1)
    assert [linha.partido for linha in simulacao.partidos()][:2] == [22, 13]


def test_senate_counts_both_seats_of_a_uf_even_without_a_second_candidate() -> None:
    votos = (*_VOTOS, _v("senador", "SE", "nominal", 151, 40))
    senado = simular_cadeiras(2026, 1, votos, REGISTRO_2026).senado
    assert [item.uf for item in senado.ufs] == ["AC", "SE"]
    assert senado.vagas_simuladas == 4
    assert sum(senado.cadeiras_por_partido().values()) == 3
    assert senado.vagas == 54


def test_only_the_first_round_is_simulated() -> None:
    with pytest.raises(UnsupportedSeatTurnError):
        simular_cadeiras(2026, 2, _VOTOS, REGISTRO_2026)


def test_registry_year_must_match() -> None:
    with pytest.raises(InvalidSeatRuleError):
        simular_cadeiras(2030, 1, (), REGISTRO_2026)


@pytest.mark.parametrize(
    ("tipo", "numero", "votos"),
    [("branco", 0, 1), ("nominal", -1, 1), ("nominal", 1301, -1)],
)
def test_stored_vote_rejects_bad_rows(tipo: str, numero: int, votos: int) -> None:
    with pytest.raises(InvalidSeatRuleError):
        VotoApurado("deputadoFederal", "AC", tipo, numero, votos)


def test_stored_vote_rejects_a_cargo_the_simulation_does_not_read() -> None:
    with pytest.raises(InvalidSeatRuleError):
        VotoApurado("presidente", "SP", "nominal", 13, 100)
