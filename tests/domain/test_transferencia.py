"""Transfer matrix between rounds: recovery, constraints, bootstrap and degenerate inputs."""

from fractions import Fraction

import numpy as np
import pytest

from eleicoes.domain.presidente_governador import CargoTally, MunicipalPlace, PartyTally
from eleicoes.domain.transferencia import (
    BRANCO_NULO,
    OUTROS,
    Grupos,
    InvalidConfidenceLevelError,
    InvalidResampleCountError,
    Observacao,
    TooFewPlacesError,
    _parte,
    ajustar,
    estimar_por_uf,
    estimar_transferencia,
    grupos_do_primeiro,
    observacoes,
    parte_estimada_de_a,
    projetar_no_simplex,
)

GRUPOS = Grupos(22, 13, (70, 14))
# Linhas: 22, 13, 70, 14, outros, branco+nulo. Colunas: 22, 13, branco+nulo.
VERDADE = np.array(
    [
        [0.95, 0.02, 0.03],
        [0.03, 0.94, 0.03],
        [0.70, 0.20, 0.10],
        [0.20, 0.70, 0.10],
        [0.40, 0.40, 0.20],
        [0.10, 0.20, 0.70],
    ]
)


def _sinteticas(
    n: int,
    *,
    semente: int = 7,
    ruido: float = 0.0,
    uf: str = "AL",
    verdade: np.ndarray = VERDADE,
) -> tuple[Observacao, ...]:
    gerador = np.random.default_rng(semente)
    fatias = gerador.dirichlet(np.array([8.0, 8.0, 2.0, 2.0, 1.0, 1.5]), n)
    cedulas = gerador.integers(20_000, 200_000, n)
    found: list[Observacao] = []
    for indice in range(n):
        primeiro = tuple(int(v) for v in np.round(fatias[indice] * cedulas[indice]))
        destino = np.array(primeiro, dtype=float) @ verdade
        if ruido:
            destino = destino * np.exp(gerador.normal(0.0, ruido, 3))
        segundo = tuple(int(v) for v in np.round(destino))
        found.append(Observacao(uf, f"{indice:05d}", f"M{indice}", primeiro, segundo))  # type: ignore[arg-type]
    return tuple(found)


def _parte_verdadeira(lista: tuple[Observacao, ...]) -> float:
    votos = np.array([obs.primeiro for obs in lista], dtype=float).sum(axis=0)
    eliminados = [2, 3, 4]
    para_a = votos[eliminados] @ VERDADE[eliminados, 0]
    para_b = votos[eliminados] @ VERDADE[eliminados, 1]
    return float(para_a / (para_a + para_b))


def test_known_matrix_is_recovered() -> None:
    lista = _sinteticas(200)

    estimativa = estimar_transferencia(lista, GRUPOS, "AL", reamostras=50)

    estimada = np.array([[taxa.estimada for taxa in linha.taxas] for linha in estimativa.linhas])
    assert np.abs(estimada - VERDADE).max() < 0.01
    assert [linha.grupo for linha in estimativa.linhas] == [
        "22",
        "13",
        "70",
        "14",
        OUTROS,
        BRANCO_NULO,
    ]
    assert estimativa.parte_de_a.estimada == pytest.approx(_parte_verdadeira(lista), abs=0.01)
    assert estimativa.r2_de_a > 0.99
    assert estimativa.rmse < 0.001
    assert estimativa.municipios == 200
    assert not estimativa.amostra_pequena


def test_noisy_data_stay_inside_the_constraints() -> None:
    lista = _sinteticas(60, ruido=0.08)

    estimativa = estimar_transferencia(lista, GRUPOS, "AL", reamostras=40)

    for linha in estimativa.linhas:
        assert sum(taxa.estimada for taxa in linha.taxas) == pytest.approx(1.0, abs=1e-6)
        for taxa in linha.taxas:
            assert -1e-12 <= taxa.inferior <= taxa.estimada + 1e-9
            assert taxa.estimada <= taxa.superior + 1e-9 <= 1.0 + 1e-9
    assert 0.0 <= estimativa.parte_de_a.inferior <= estimativa.parte_de_a.superior <= 1.0


def test_bootstrap_rows_also_sum_to_one() -> None:
    gerador = np.random.default_rng(3)
    x = gerador.dirichlet(np.ones(4), 30)
    y = gerador.dirichlet(np.ones(3), 30)

    beta = ajustar(x, y, np.ones(30))

    assert beta.shape == (4, 3)
    assert np.allclose(beta.sum(axis=1), 1.0)
    assert (beta >= 0).all()


def test_noisy_recovery_is_close_to_the_truth() -> None:
    lista = _sinteticas(300, ruido=0.02, semente=11)

    estimativa = estimar_transferencia(lista, GRUPOS, "AL", reamostras=0)

    principais = np.array(
        [[taxa.estimada for taxa in linha.taxas] for linha in estimativa.linhas[:2]]
    )
    assert np.abs(principais - VERDADE[:2]).max() < 0.05
    assert estimativa.parte_de_a.estimada == pytest.approx(_parte_verdadeira(lista), abs=0.1)


def test_same_seed_gives_the_same_intervals() -> None:
    lista = _sinteticas(40, ruido=0.05)

    primeira = estimar_transferencia(lista, GRUPOS, "AL", reamostras=30, semente=5)
    segunda = estimar_transferencia(lista, GRUPOS, "AL", reamostras=30, semente=5)
    outra = estimar_transferencia(lista, GRUPOS, "AL", reamostras=30, semente=6)

    assert primeira == segunda
    assert primeira.parte_de_a != outra.parte_de_a


def test_too_few_places_raise() -> None:
    lista = _sinteticas(5)

    with pytest.raises(TooFewPlacesError) as erro:
        estimar_transferencia(lista, GRUPOS, "AP", minimo=12)

    assert (erro.value.uf, erro.value.found, erro.value.minimum) == ("AP", 5, 12)


def test_places_without_ballots_do_not_count_for_the_minimum() -> None:
    vazias = tuple(
        Observacao("AP", f"9{indice:04d}", "Vazio", (0, 0, 0, 0, 0, 0), (1, 1, 1))
        for indice in range(10)
    )

    with pytest.raises(TooFewPlacesError):
        estimar_transferencia(vazias + _sinteticas(3), GRUPOS, "AP", minimo=5)


def test_states_below_the_minimum_are_skipped() -> None:
    lista = _sinteticas(30, uf="AL") + _sinteticas(4, uf="AP")

    estimadas, puladas = estimar_por_uf(lista, GRUPOS, minimo=10, reamostras=5)

    assert [estimativa.uf for estimativa in estimadas] == ["AL"]
    assert puladas == ("AP",)


def test_group_without_votes_in_the_state_is_reported_absent() -> None:
    lista = tuple(
        Observacao(
            obs.uf, obs.codigo, obs.nome, (*obs.primeiro[:3], 0, *obs.primeiro[4:]), obs.segundo
        )
        for obs in _sinteticas(40, ruido=0.02)
    )

    estimativa = estimar_transferencia(lista, GRUPOS, "AL", reamostras=10)

    assert estimativa.ausentes == ("14",)
    assert "14" not in [linha.grupo for linha in estimativa.linhas]


def test_identical_places_still_return_valid_rows() -> None:
    um = Observacao("AL", "00001", "Igual", (500, 400, 50, 30, 10, 10), (560, 420, 20))
    lista = tuple(Observacao("AL", f"{i:05d}", "Igual", um.primeiro, um.segundo) for i in range(15))

    estimativa = estimar_transferencia(lista, GRUPOS, "AL", reamostras=10)

    for linha in estimativa.linhas:
        assert sum(taxa.estimada for taxa in linha.taxas) == pytest.approx(1.0, abs=1e-6)
    assert estimativa.r2_de_a == 0.0


def test_no_resamples_give_a_point_interval() -> None:
    estimativa = estimar_transferencia(_sinteticas(20), GRUPOS, "AL", reamostras=0)

    taxa = estimativa.linhas[0].taxas[0]
    assert taxa.inferior == taxa.estimada == taxa.superior
    assert estimativa.reamostras == 0


@pytest.mark.parametrize("nivel", [0.0, 1.0, -0.1, 1.5])
def test_invalid_confidence_level_raises(nivel: float) -> None:
    with pytest.raises(InvalidConfidenceLevelError):
        estimar_transferencia(_sinteticas(20), GRUPOS, "AL", nivel=nivel)


def test_negative_resample_count_raises() -> None:
    with pytest.raises(InvalidResampleCountError):
        estimar_transferencia(_sinteticas(20), GRUPOS, "AL", reamostras=-1)


def test_estimated_share_is_a_fraction_for_the_map() -> None:
    estimativa = estimar_transferencia(_sinteticas(100), GRUPOS, "AL", reamostras=0)

    parte = parte_estimada_de_a(estimativa)

    assert isinstance(parte, Fraction)
    assert parte.denominator <= 10_000
    assert float(parte) == pytest.approx(estimativa.parte_de_a.estimada, abs=1e-4)


def test_share_is_half_when_no_eliminated_vote_reaches_a_finalist() -> None:
    beta = VERDADE.copy()
    beta[2:5] = [0.0, 0.0, 1.0]

    assert _parte(beta, np.array([10.0, 10.0, 5.0, 5.0, 5.0, 1.0]), (2, 3, 4)) == 0.5


def test_share_is_half_without_eliminated_groups() -> None:
    grupos = Grupos(22, 13, ())
    gerador = np.random.default_rng(2)
    lista = tuple(
        Observacao("AL", f"{i:05d}", "M", (int(a), int(b), 0, 10), (int(a), int(b), 10))
        for i, (a, b) in enumerate(gerador.integers(100, 1000, (15, 2)))
    )

    estimativa = estimar_transferencia(lista, grupos, "AL", reamostras=0)

    assert estimativa.ausentes == (OUTROS,)
    assert estimativa.parte_de_a.estimada == 0.5


def test_zero_weights_return_an_even_split() -> None:
    beta = ajustar(np.ones((3, 2)) / 2, np.ones((3, 3)) / 3, np.zeros(3))

    assert np.allclose(beta, 1 / 3)


def test_simplex_projection() -> None:
    projetadas = projetar_no_simplex(np.array([[0.5, 0.5, 0.5], [2.0, 0.0, -1.0], [0.2, 0.3, 0.5]]))

    assert np.allclose(projetadas, [[1 / 3, 1 / 3, 1 / 3], [1.0, 0.0, 0.0], [0.2, 0.3, 0.5]])


def _place(uf: str, codigo: str, votos: dict[int, int], branco: int, nulo: int) -> MunicipalPlace:
    parties = tuple(PartyTally(numero, total, 0) for numero, total in votos.items() if total)
    return MunicipalPlace(uf, codigo, f"Cidade {codigo}", CargoTally(parties, branco, nulo), None)


def test_eliminated_parties_above_the_threshold_get_their_own_row() -> None:
    primeiro = (
        _place("AL", "1", {22: 4500, 13: 4400, 70: 600, 14: 100, 30: 49, 80: 1}, 5, 5),
        _place("AC", "2", {22: 100}, 0, 0),
    )

    grupos = grupos_do_primeiro(primeiro, 22, 13)

    assert grupos == Grupos(22, 13, (70, 14))
    assert grupos.chaves == ("22", "13", "70", "14", OUTROS, BRANCO_NULO)
    assert grupos.eliminados == (2, 3, 4)


def test_no_votes_means_no_highlighted_party() -> None:
    assert grupos_do_primeiro((), 22, 13) == Grupos(22, 13, ())


def test_observations_join_the_rounds_by_padded_tse_code() -> None:
    primeiro = (
        _place("AL", "1007", {22: 50, 13: 40, 70: 6, 14: 3, 30: 1}, 2, 3),
        _place("AL", "2000", {22: 10, 13: 10}, 0, 0),
        _place("ZZ", "29998", {22: 10, 13: 10}, 0, 0),
    )
    segundo = (
        _place("AL", "01007", {22: 55, 13: 45, 30: 4}, 1, 2),
        _place("AM", "3000", {22: 5, 13: 5}, 0, 0),
        _place("ZZ", "29998", {22: 10, 13: 10}, 0, 0),
    )

    (obs,) = observacoes(primeiro, segundo, GRUPOS)

    assert (obs.uf, obs.codigo, obs.nome) == ("AL", "01007", "Cidade 01007")
    assert obs.primeiro == (50, 40, 6, 3, 1, 5)
    assert obs.segundo == (55, 45, 3)
    assert obs.cedulas_primeiro == 105
    assert obs.cedulas_segundo == 103
