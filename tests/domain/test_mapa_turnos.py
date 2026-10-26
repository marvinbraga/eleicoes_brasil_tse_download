"""1º × 2º turno: transfer scenarios, residual and the robust local deviation."""

from fractions import Fraction

import pytest

from eleicoes.domain.mapa import PonteTseIbge, ponte_de_linhas
from eleicoes.domain.mapa_turnos import (
    DEMAIS,
    DENTRO,
    FORA_A,
    FORA_B,
    GOVERNADOR,
    MODERADO,
    SEM_BASE,
    Apuracao,
    FinalistsMissingError,
    GrupoEliminado,
    apuracao,
    cenarios,
    cenarios_de_governador,
    classe_do_z,
    comparar_turnos,
    finalistas,
    finalistas_de_governador,
    grupos_eliminados,
    leituras,
)
from eleicoes.domain.presidente_governador import CargoTally, MunicipalPlace, PartyTally

_HEADER = (
    "DT_GERACAO",
    "HH_GERACAO",
    "CD_UF_TSE",
    "CD_UF_IBGE",
    "SG_UF",
    "NM_UF",
    "CD_MUNICIPIO_TSE",
    "NM_MUNICIPIO_TSE",
    "CD_MUNICIPIO_IBGE",
    "NM_MUNICIPIO_IBGE",
)


def test_all_to_the_supported_finalist_moves_every_eliminated_vote() -> None:
    primeiro = Apuracao(a=400, b=500, outros=100, branco=10, nulo=10)
    segundo = Apuracao(a=500, b=500, outros=0, branco=10, nulo=10)

    (lida,) = leituras(((primeiro, segundo),), cenarios(22, 13)[0], minimo=1, piso=0)

    assert lida.esperado == Fraction(1, 2)
    assert lida.real == Fraction(1, 2)
    assert lida.residuo == 0
    assert lida.votos_de_diferenca == 0


def test_proportional_scenario_keeps_the_first_round_split() -> None:
    primeiro = Apuracao(a=300, b=600, outros=100, branco=0, nulo=0)
    segundo = Apuracao(a=400, b=600, outros=0, branco=0, nulo=0)
    proporcional = next(item for item in cenarios(22, 13) if item.chave == "proporcional")

    (lida,) = leituras(((primeiro, segundo),), proporcional, minimo=1, piso=0)

    assert lida.esperado == Fraction(1, 3)
    assert lida.residuo == Fraction(2, 5) - Fraction(1, 3)
    assert lida.votos_de_diferenca == 67


def test_scenarios_name_the_supported_finalist_first() -> None:
    found = cenarios(22, 13)

    assert [item.chave for item in found] == [
        "todosa",
        "maioriaa",
        "dividido",
        "proporcional",
        "maioriab",
    ]
    assert found[0].rotulo == "Todos apoiam o 22"
    assert all(item.chave.isalpha() and item.chave.islower() for item in found)


def test_outlier_is_measured_against_the_group_median() -> None:
    comum = (Apuracao(500, 500, 0, 0, 0), Apuracao(500, 500, 0, 0, 0))
    leve = (Apuracao(500, 500, 0, 0, 0), Apuracao(510, 490, 0, 0, 0))
    estranho = (Apuracao(500, 500, 0, 0, 0), Apuracao(800, 200, 0, 0, 0))
    grupo = (comum, leve, comum, leve, comum, leve, comum, estranho)

    found = leituras(grupo, cenarios(22, 13)[0], piso=1000, minimo=8)

    assert found[-1].classe == FORA_A
    assert found[-1].z is not None and found[-1].z > 3.5
    assert {item.classe for item in found[:-1]} == {DENTRO}


def test_small_places_and_small_groups_get_no_deviation() -> None:
    pequeno = (Apuracao(50, 50, 0, 0, 0), Apuracao(60, 40, 0, 0, 0))
    grande = (Apuracao(500, 500, 0, 0, 0), Apuracao(600, 400, 0, 0, 0))

    poucos = leituras((grande,) * 3, cenarios(22, 13)[0], piso=1000, minimo=8)
    com_pequeno = leituras((grande,) * 8 + (pequeno,), cenarios(22, 13)[0])

    assert {item.classe for item in poucos} == {SEM_BASE}
    assert all(item.z is None for item in poucos)
    assert com_pequeno[-1].classe == SEM_BASE


def test_identical_residuals_have_no_scale() -> None:
    igual = (Apuracao(500, 500, 0, 0, 0), Apuracao(500, 500, 0, 0, 0))

    found = leituras((igual,) * 8, cenarios(22, 13)[0])

    assert {item.classe for item in found} == {SEM_BASE}


@pytest.mark.parametrize(
    ("z", "classe"),
    [(0.0, DENTRO), (2.5, MODERADO), (-2.5, MODERADO), (3.6, FORA_A), (-3.6, FORA_B)],
)
def test_z_thresholds(z: float, classe: str) -> None:
    assert classe_do_z(z) == classe


def test_finalists_put_the_supported_candidate_first() -> None:
    segundo = (_place("AC", "01007", "BUJARI (AC)", {13: 60, 22: 40}),)

    assert finalistas(segundo) == (13, 22)
    assert finalistas(segundo, 22) == (22, 13)
    assert finalistas(segundo, 99) == (13, 22)


def test_finalists_need_two_candidates() -> None:
    with pytest.raises(FinalistsMissingError):
        finalistas((_place("AC", "01007", "BUJARI (AC)", {13: 60}),))


def test_absent_party_counts_as_zero() -> None:
    tally = CargoTally((PartyTally(22, 10, 0), PartyTally(30, 5, 0)), 1, 2)

    assert apuracao(tally, 22, 13) == Apuracao(10, 0, 5, 1, 2, ((30, 5),))


def test_comparison_joins_rounds_and_maps_mesh_codes() -> None:
    primeiro = (
        _place("AC", "1007", "BUJARI (AC)", {22: 400, 13: 500, 30: 100}),
        _place("AC", "01015", "CAPIXABA (AC)", {22: 10, 13: 10}),
        _place("ZZ", "29262", "ABU DHABI (ZZ)", {22: 5, 13: 5}),
    )
    segundo = (
        _place("AC", "01007", "BUJARI (AC)", {22: 520, 13: 480}),
        _place("ZZ", "29262", "ABU DHABI (ZZ)", {22: 6, 13: 4}),
    )

    found = comparar_turnos(
        primeiro,
        segundo,
        _ponte(),
        frozenset({"1200138"}),
        frozenset({"12"}),
        "076",
        exterior={"29262": (54.4, 24.4)},
        apoiado=22,
    )

    assert (found.a, found.b) == (22, 13)
    assert found.ufs_com_segundo == ("AC", "ZZ")
    assert found.sem_comparacao == 1
    assert [item.codigo for item in found.municipios] == ["1200138"]
    assert found.municipios[0].primeiro == Apuracao(400, 500, 100, 0, 0, ((30, 100),))
    assert found.municipios[0].leituras[0].esperado == Fraction(1, 2)
    assert [item.codigo for item in found.ufs] == ["12"]
    assert found.pais is not None and found.pais.codigo == "076"
    assert found.pais.segundo.a == 526
    assert [(ponto.lugar.codigo, ponto.lon) for ponto in found.exterior] == [("29262", 54.4)]
    assert found.sem_poligono == ("Exterior (ZZ)",)


def test_places_without_polygon_are_listed() -> None:
    primeiro = (_place("AC", "01007", "BUJARI (AC)", {22: 40, 13: 60}),)
    segundo = (_place("AC", "01007", "BUJARI (AC)", {22: 45, 13: 55}),)

    found = comparar_turnos(primeiro, segundo, _ponte(), frozenset(), frozenset(), "076")

    assert found.municipios == ()
    assert found.ufs == ()
    assert found.sem_poligono == ("Acre (AC)", "BUJARI (AC)")


def test_sum_keeps_the_eliminated_breakdown() -> None:
    um = Apuracao(1, 2, 7, 0, 0, ((30, 3), (70, 4)))
    outro = Apuracao(1, 2, 5, 0, 0, ((14, 1), (70, 4)))

    soma = um + outro

    assert soma.eliminados == ((14, 1), (30, 3), (70, 8))
    assert sum(votos for _, votos in soma.eliminados) == soma.outros
    assert soma.votos_do_grupo(frozenset({70, 14})) == 9


def test_big_eliminated_parties_stand_alone_and_the_rest_are_grouped() -> None:
    primeiro = (
        _place("AC", "01007", "BUJARI (AC)", {22: 480, 13: 470, 70: 30, 14: 15, 30: 4, 80: 1}),
    )

    found = grupos_eliminados(primeiro, 22, 13)

    assert found == (
        GrupoEliminado(70, frozenset({70}), Fraction(3, 100)),
        GrupoEliminado(14, frozenset({14}), Fraction(15, 1000)),
        GrupoEliminado(DEMAIS, frozenset({30, 80}), Fraction(5, 1000)),
    )


def test_no_eliminated_party_means_no_group() -> None:
    primeiro = (_place("AC", "01007", "BUJARI (AC)", {22: 480, 13: 470}),)

    assert grupos_eliminados(primeiro, 22, 13) == ()


def test_governor_scenarios_follow_the_first_round_order() -> None:
    found = cenarios_de_governador()

    assert [(item.chave, item.parte_de_a) for item in found] == [
        ("dividido", Fraction(1, 2)),
        ("proporcional", None),
        ("todosa", Fraction(1)),
        ("todosb", Fraction(0)),
    ]
    assert found[2].rotulo == "Todos para o 1º colocado do 1º turno"


def test_governor_finalists_are_per_uf_and_led_by_the_first_round_winner() -> None:
    primeiro = (
        _gov("AC", "01007", {10: 50, 11: 40, 45: 9}),
        _gov("AM", "02003", {55: 60, 22: 30, 15: 20}),
        _gov("AL", "27001", {40: 70, 15: 10}),
    )
    segundo = (
        _gov("AC", "01007", {11: 70, 10: 30}),
        _gov("AM", "02003", {55: 65, 22: 45}),
        _place("AL", "27001", "MACEIO (AL)", {22: 5, 13: 5}),
    )

    assert finalistas_de_governador(primeiro, segundo) == {"AC": (10, 11), "AM": (55, 22)}


def test_governor_comparison_skips_ufs_without_a_runoff_and_the_country() -> None:
    primeiro = (
        _gov("AC", "1007", {10: 500, 11: 400, 45: 100}),
        _gov("AL", "27001", {40: 70, 15: 10}),
    )
    segundo = (
        _gov("AC", "01007", {11: 520, 10: 480}),
        _place("AL", "27001", "MACEIO (AL)", {22: 5, 13: 5}),
    )

    found = comparar_turnos(
        primeiro,
        segundo,
        _ponte(),
        frozenset({"1200138"}),
        frozenset({"12"}),
        "076",
        cargo=GOVERNADOR,
    )

    assert found.cargo == GOVERNADOR
    assert found.finalistas_por_uf == {"AC": (10, 11)}
    assert found.pais is None
    assert found.exterior == ()
    assert found.ufs_com_segundo == ("AC",)
    assert found.eliminados == ()
    assert found.municipios[0].primeiro == Apuracao(500, 400, 100, 0, 0, ((45, 100),))
    assert found.municipios[0].segundo.a == 480
    assert [item.codigo for item in found.ufs] == ["12"]


def test_governor_comparison_needs_a_runoff() -> None:
    primeiro = (_gov("AC", "01007", {10: 50, 11: 40}),)
    segundo = (_place("AC", "01007", "BUJARI (AC)", {22: 5, 13: 5}),)

    with pytest.raises(FinalistsMissingError):
        comparar_turnos(
            primeiro, segundo, _ponte(), frozenset(), frozenset(), "076", cargo=GOVERNADOR
        )


def _gov(uf: str, codigo: str, votos: dict[int, int]) -> MunicipalPlace:
    parties = tuple(PartyTally(numero, total, 0) for numero, total in votos.items())
    presidente = CargoTally((PartyTally(22, 1, 0), PartyTally(13, 1, 0)), 0, 0)
    return MunicipalPlace(uf, codigo, f"{codigo} ({uf})", presidente, CargoTally(parties, 0, 0))


def _place(uf: str, codigo: str, nome: str, votos: dict[int, int]) -> MunicipalPlace:
    parties = tuple(PartyTally(numero, total, 0) for numero, total in votos.items())
    return MunicipalPlace(uf, codigo, nome, CargoTally(parties, 0, 0), None)


def _ponte() -> PonteTseIbge:
    values = ("04/10/2026", "09:00:06", "1", "12", "AC", "Acre", "01007", "Bujari", "1200138", "X")
    return ponte_de_linhas((dict(zip(_HEADER, values, strict=True)),))
