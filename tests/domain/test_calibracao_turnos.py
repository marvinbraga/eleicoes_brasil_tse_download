"""Calibrating the round-comparison thresholds: same z as the map, plus the tail statistics."""

import json
from fractions import Fraction

import pytest

from eleicoes.domain.calibracao_turnos import (
    calibrar,
    como_json,
    fracao_normal_acima,
    leituras_por_uf,
    limiar_para_fracao,
    parear,
    quantil,
)
from eleicoes.domain.mapa import PonteTseIbge, ponte_de_linhas
from eleicoes.domain.mapa_turnos import Apuracao, cenarios, comparar_turnos
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
_SEGUNDO_A = (520, 530, 515, 525, 540, 510, 535, 700, 600)


def test_linear_quantile_interpolates_between_ranks() -> None:
    valores = (1.0, 2.0, 3.0, 4.0)

    assert quantil(valores, 0.5) == 2.5
    assert quantil(valores, 0.9) == pytest.approx(3.7)
    assert quantil(valores, 1.0) == 4.0
    assert quantil((7.0,), 0.99) == 7.0


def test_threshold_flags_at_most_the_target_share_with_a_strict_comparison() -> None:
    valores = tuple(indice / 100 for indice in range(1, 1001))

    um_por_cento = limiar_para_fracao(valores, 0.01)
    um_por_mil = limiar_para_fracao(valores, 0.001)

    assert (um_por_cento.abs_z, um_por_cento.marcados) == (9.9, 10)
    assert (um_por_mil.abs_z, um_por_mil.marcados) == (9.99, 1)


def test_ties_at_the_cut_flag_fewer_places() -> None:
    valores = (1.0,) * 95 + (5.0,) * 5

    found = limiar_para_fracao(valores, 0.01)

    assert (found.abs_z, found.marcados) == (5.0, 0)


def test_normal_reference_tails() -> None:
    assert fracao_normal_acima(2.0) == pytest.approx(0.0455, abs=1e-4)
    assert fracao_normal_acima(3.5) == pytest.approx(0.000465, abs=1e-6)


def test_pairing_pads_tse_codes_and_counts_the_unpaired() -> None:
    primeiro = (
        _place("AC", "1007", {22: 400, 13: 500, 30: 100}),
        _place("AC", "1015", {22: 10, 13: 10}),
    )
    segundo = (_place("AC", "01007", {22: 520, 13: 480}), _place("ZZ", "29262", {22: 6}))

    pares, sem_par = parear(primeiro, segundo, 22, 13)

    assert [(par.uf, par.codigo) for par in pares] == [("AC", "01007")]
    assert pares[0].primeiro == Apuracao(400, 500, 100, 0, 0)
    assert sem_par == 2


def test_z_matches_the_map_for_every_municipality() -> None:
    primeiro, segundo = _eleicao()
    mapa = comparar_turnos(
        primeiro,
        segundo,
        _ponte(),
        frozenset(_ibge(indice) for indice in range(len(_SEGUNDO_A))),
        frozenset({"12"}),
        "076",
        apoiado=22,
    )
    pares, _ = parear(primeiro, segundo, 22, 13)

    for posicao, cenario in enumerate(cenarios(22, 13)):
        nossos = [lida.z for _, lida in leituras_por_uf(pares, cenario)]
        do_mapa = [lugar.leituras[posicao].z for lugar in mapa.municipios]
        assert nossos == do_mapa
        assert any(z is not None for z in nossos)


def test_calibration_counts_flags_and_picks_the_closest_national_fit() -> None:
    primeiro, segundo = _eleicao()

    found = calibrar(primeiro, segundo, 22, 13)

    assert (found.a, found.b, found.pareados, found.sem_par) == (22, 13, 10, 0)
    todos = found.cenarios[0]
    assert todos.municipios.lugares == len(_SEGUNDO_A)
    assert todos.municipios.com_base == len(_SEGUNDO_A)
    assert todos.municipios.fora_a == 2
    assert todos.fora_por_uf == (("AC", 2),)
    assert todos.exterior.lugares == 1
    assert todos.exterior.sem_base == 1
    assert [p for p, _ in todos.quantis] == [0.9, 0.95, 0.99, 0.995, 0.999]
    assert todos.nacional.esperado == Fraction(4060 + 900, 9019)
    assert found.melhor_ajuste.cenario.chave == "todosa"


def test_json_is_documented_and_serializable() -> None:
    primeiro, segundo = _eleicao()
    calibracao = calibrar(primeiro, segundo, 22, 13)

    found = como_json(calibracao, 2022, ["https://example.org/a.zip"])
    texto = json.dumps(found, ensure_ascii=False)

    assert json.loads(texto) == found
    assert found["melhor_ajuste"] == "todosa"
    primeiro_cenario = found["cenarios"][0]  # type: ignore[index]
    assert primeiro_cenario["municipios"]["fracao_fora"] == pytest.approx(2 / 9, abs=1e-6)
    assert set(primeiro_cenario["limiares_por_fracao"]) == {"0.01", "0.001"}
    assert primeiro_cenario["parte_de_a"] == 1.0
    assert found["cenarios"][3]["parte_de_a"] is None  # type: ignore[index]


def test_empty_groups_have_no_tail_statistics() -> None:
    primeiro = (_place("ZZ", "29262", {22: 5, 13: 5}),)
    segundo = (_place("ZZ", "29262", {22: 6, 13: 4}),)

    found = calibrar(primeiro, segundo, 22, 13)

    assert found.cenarios[0].quantis == ()
    assert found.cenarios[0].limiares == ()
    assert como_json(found, 2022, [])["cenarios"][0]["municipios"]["fracao_fora"] is None  # type: ignore[index]


def _eleicao() -> tuple[tuple[MunicipalPlace, ...], tuple[MunicipalPlace, ...]]:
    primeiro = tuple(
        _place("AC", _tse(indice), {22: 450, 13: 450, 30: 100}) for indice in range(len(_SEGUNDO_A))
    ) + (_place("ZZ", "29262", {22: 10, 13: 9}),)
    segundo = tuple(
        _place("AC", _tse(indice), {22: votos, 13: 1000 - votos})
        for indice, votos in enumerate(_SEGUNDO_A)
    ) + (_place("ZZ", "29262", {22: 10, 13: 10}),)
    return primeiro, segundo


def _place(uf: str, codigo: str, votos: dict[int, int]) -> MunicipalPlace:
    parties = tuple(PartyTally(numero, total, 0) for numero, total in votos.items())
    return MunicipalPlace(uf, codigo, f"LUGAR {codigo}", CargoTally(parties, 0, 0), None)


def _tse(indice: int) -> str:
    return f"{1007 + indice:05d}"


def _ibge(indice: int) -> str:
    return f"{1200100 + indice}"


def _ponte() -> PonteTseIbge:
    rows = (
        dict(
            zip(
                _HEADER,
                ("04/10/2026", "09:00:06", "1", "12", "AC", "Acre", _tse(i), "X", _ibge(i), "X"),
                strict=True,
            )
        )
        for i in range(len(_SEGUNDO_A))
    )
    return ponte_de_linhas(tuple(rows))
