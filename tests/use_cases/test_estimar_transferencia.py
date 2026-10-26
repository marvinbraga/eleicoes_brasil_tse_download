"""Transfer estimate CLI: table, skipped states and failures, with injected loaders."""

import numpy as np
import pytest

from eleicoes.domain.presidente_governador import CargoTally, MunicipalPlace, PartyTally
from eleicoes.use_cases.estimar_transferencia import Collect, FirstRoundMissingError, main

_VERDADE = np.array(
    [
        [0.95, 0.02, 0.03],
        [0.03, 0.94, 0.03],
        [0.70, 0.20, 0.10],
        [0.40, 0.40, 0.20],
        [0.10, 0.20, 0.70],
    ]
)


def _place(uf: str, codigo: str, votos: dict[int, int], branco: int, nulo: int) -> MunicipalPlace:
    parties = tuple(PartyTally(numero, total, 0) for numero, total in votos.items() if total)
    return MunicipalPlace(uf, codigo, f"Cidade {codigo}", CargoTally(parties, branco, nulo), None)


def _rodadas(
    uf: str, n: int, *, semente: int = 1, encolhe: int = 1
) -> tuple[list[MunicipalPlace], list[MunicipalPlace]]:
    gerador = np.random.default_rng(semente)
    primeiro: list[MunicipalPlace] = []
    segundo: list[MunicipalPlace] = []
    for indice in range(n):
        fatias = gerador.dirichlet(np.array([8.0, 8.0, 2.0, 1.0, 1.5]))
        contas = np.round(fatias * gerador.integers(5_000, 50_000)).astype(int)
        a, b, eliminado, outro, brancos = (int(v) for v in contas)
        codigo = str(1000 + indice)
        primeiro.append(_place(uf, codigo, {22: a, 13: b, 70: eliminado, 30: outro}, brancos, 0))
        destino = np.round(contas @ _VERDADE).astype(int) // (encolhe if indice == 0 else 1)
        segundo.append(
            _place(uf, codigo, {22: int(destino[0]), 13: int(destino[1])}, 0, int(destino[2]))
        )
    return primeiro, segundo


def _fixo(places: list[MunicipalPlace]) -> Collect:
    def collect(_ano: int, _turno: int) -> tuple[MunicipalPlace, ...]:
        return tuple(places)

    return collect


def test_prints_the_table_for_each_state(capsys: pytest.CaptureFixture[str]) -> None:
    primeiro, segundo = _rodadas("AL", 40)
    extra_1, extra_2 = _rodadas("AP", 4, semente=2)

    code = main(
        ["--reamostras", "20", "--minimo", "10"],
        primeiro=_fixo(primeiro + extra_1),
        segundo=_fixo(segundo + extra_2),
    )

    out = capsys.readouterr().out
    assert code == 0
    assert "Finalistas: 22 (A) e 13 (B)." in out
    assert "Eliminados com pelo menos 1% no país: 70, 30" in out
    assert "AL: 40 municípios. R² ponderado da fatia do 22:" in out
    assert "→ branco+nulo" in out
    assert "Dos votos dos eliminados que foram a um finalista, para o 22:" in out
    assert "Sem estimativa (menos de 10 municípios comparáveis): AP." in out
    assert "Intervalos de 90% por bootstrap dos municípios (20 reamostras, semente 0)." in out


def test_small_state_and_odd_ballot_ratio_are_flagged(capsys: pytest.CaptureFixture[str]) -> None:
    primeiro, segundo = _rodadas("AC", 14, encolhe=4)

    code = main(
        ["--reamostras", "5"],
        primeiro=_fixo(primeiro),
        segundo=_fixo(segundo),
    )

    out = capsys.readouterr().out
    assert code == 0
    assert "AC: 14 municípios (amostra pequena: intervalos instáveis)." in out
    assert "Atenção: 1 municípios com cédulas do 2º turno fora de 50% a 150%" in out


def test_many_odd_places_are_summarised(capsys: pytest.CaptureFixture[str]) -> None:
    primeiro, segundo = _rodadas("AC", 14)
    metade = [
        _place(
            p.uf, p.codigo, {party.partido: party.votos * 3 for party in p.presidente.parties}, 0, 1
        )
        for p in segundo[:7]
    ]

    main(
        ["--reamostras", "0"],
        primeiro=_fixo(primeiro),
        segundo=_fixo(metade + segundo[7:]),
    )

    assert "e mais 2." in capsys.readouterr().out


def test_without_common_places_says_so(capsys: pytest.CaptureFixture[str]) -> None:
    primeiro, _ = _rodadas("AL", 3)
    _, segundo = _rodadas("AM", 3)

    code = main([], primeiro=_fixo(primeiro), segundo=_fixo(segundo))

    assert code == 0
    assert "Nenhum município aparece nos dois turnos." in capsys.readouterr().out


def test_missing_second_round_fails(capsys: pytest.CaptureFixture[str]) -> None:
    code = main([], primeiro=_fixo([]), segundo=_fixo([]))

    assert code == 1
    assert "O 2º turno de presidente ainda não tem votos importados." in capsys.readouterr().err


def test_missing_first_round_fails(capsys: pytest.CaptureFixture[str]) -> None:
    def ausente(ano: int, _turno: int) -> tuple[MunicipalPlace, ...]:
        raise FirstRoundMissingError(ano)

    code = main([], primeiro=ausente, segundo=_fixo([]))

    assert code == 1
    assert "O 1º turno deste ano não está guardado no banco." in capsys.readouterr().err


def test_invalid_year_fails(capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["--ano", "1900"], primeiro=_fixo([]), segundo=_fixo([]))

    assert code == 1
    assert "Ano inválido" in capsys.readouterr().err


def test_invalid_level_fails(capsys: pytest.CaptureFixture[str]) -> None:
    primeiro, segundo = _rodadas("AL", 20)

    code = main(["--nivel", "2"], primeiro=_fixo(primeiro), segundo=_fixo(segundo))

    assert code == 1
    assert "Nível de confiança inválido" in capsys.readouterr().err
