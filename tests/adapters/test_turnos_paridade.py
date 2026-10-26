"""The page's custom-scenario math must read places exactly like mapa_turnos.leituras."""

import json
import shutil
import subprocess
from statistics import median

import pytest

from eleicoes.adapters.html_mapa import _PAGE_SCRIPT
from eleicoes.domain.mapa_turnos import (
    LIMIAR_FORA,
    LIMIAR_MODERADO,
    Apuracao,
    Leitura,
    cenarios,
    leituras,
)

_INICIO = "// <matematica-dos-turnos>"
_FIM = "// </matematica-dos-turnos>"
_HARNESS = """
var entrada = JSON.parse(require("fs").readFileSync(0, "utf8"));
var saida = entrada.grupos.map(function (itens) {
  var esperados = itens.map(function (item) {
    return esperadoDoCenario(item.primeiro, item.eliminados, entrada.partes);
  });
  return lerGrupo(itens, esperados, entrada.regras);
});
process.stdout.write(JSON.stringify(saida));
"""
_GRUPOS = (frozenset({70}), frozenset({14}), frozenset({30, 80}))
_PRESETS = {
    "todosa": 1.0,
    "maioriaa": 0.75,
    "dividido": 0.5,
    "proporcional": None,
    "maioriab": 0.25,
}


def _matematica() -> str:
    inicio = _PAGE_SCRIPT.index(_INICIO)
    fim = _PAGE_SCRIPT.index(_FIM)
    return _PAGE_SCRIPT[inicio:fim]


def _par(
    a1: int, b1: int, e70: int, e14: int, e30: int, a2: int, b2: int
) -> tuple[Apuracao, Apuracao]:
    eliminados = ((14, e14), (30, e30), (70, e70))
    primeiro = Apuracao(a1, b1, e70 + e14 + e30, 10, 20, eliminados)
    return primeiro, Apuracao(a2, b2, 0, 5, 7)


def _grupo_comum() -> tuple[tuple[Apuracao, Apuracao], ...]:
    # Nove comparáveis (contagem par depois do piso) e um abaixo do piso.
    return (
        _par(400, 500, 60, 30, 10, 540, 470),
        _par(450, 420, 70, 40, 20, 560, 450),
        _par(300, 650, 30, 15, 5, 380, 640),
        _par(500, 380, 80, 25, 15, 600, 420),
        _par(420, 430, 90, 45, 15, 540, 480),
        _par(380, 520, 50, 35, 15, 470, 560),
        _par(610, 300, 60, 20, 10, 700, 330),
        _par(350, 480, 100, 50, 20, 520, 500),
        _par(700, 250, 30, 10, 10, 760, 260),
        _par(40, 30, 5, 3, 2, 45, 35),
    )


def _grupo_sem_mad() -> tuple[tuple[Apuracao, Apuracao], ...]:
    # Cinco resíduos iguais em oito: MAD zero, desvio médio positivo.
    igual = _par(500, 400, 60, 30, 10, 600, 400)
    return (igual,) * 5 + (
        _par(500, 400, 60, 30, 10, 650, 350),
        _par(500, 400, 60, 30, 10, 560, 440),
        _par(500, 400, 60, 30, 10, 700, 300),
    )


def _item(par: tuple[Apuracao, Apuracao]) -> dict[str, list[int]]:
    primeiro, segundo = par
    return {
        "primeiro": [primeiro.a, primeiro.b, primeiro.outros, primeiro.branco, primeiro.nulo],
        "segundo": [segundo.a, segundo.b, segundo.outros, segundo.branco, segundo.nulo],
        "eliminados": [primeiro.votos_do_grupo(grupo) for grupo in _GRUPOS],
    }


def _no_node(
    grupos: tuple[tuple[tuple[Apuracao, Apuracao], ...], ...], parte: float | None
) -> list[list[list[object]]]:
    entrada = {
        "grupos": [[_item(par) for par in grupo] for grupo in grupos],
        "partes": [parte] * len(_GRUPOS),
        "regras": {
            "piso": 1000,
            "minimo": 8,
            "limiares": {"moderado": LIMIAR_MODERADO, "fora": LIMIAR_FORA},
        },
    }
    node = shutil.which("node")
    assert node is not None
    feito = subprocess.run(
        [node, "-e", _matematica() + _HARNESS],
        input=json.dumps(entrada),
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    resultado: list[list[list[object]]] = json.loads(feito.stdout)
    return resultado


def _confere(js: list[object], py: Leitura) -> None:
    esperado, votos, z, classe = js
    assert esperado == pytest.approx(float(py.esperado), abs=1e-12)
    assert votos == py.votos_de_diferenca
    assert classe == py.classe
    if py.z is None:
        assert z is None
    else:
        assert z == pytest.approx(py.z, abs=1e-9)


@pytest.mark.skipif(shutil.which("node") is None, reason="node não está instalado")
@pytest.mark.parametrize("chave", sorted(_PRESETS))
def test_custom_math_matches_every_preset(chave: str) -> None:
    cenario = next(item for item in cenarios(22, 13) if item.chave == chave)
    grupos = (_grupo_comum(), _grupo_sem_mad())

    no_node = _no_node(grupos, _PRESETS[chave])

    for grupo, lidas_js in zip(grupos, no_node, strict=True):
        lidas_py = leituras(grupo, cenario)
        assert len(lidas_js) == len(lidas_py)
        for js, py in zip(lidas_js, lidas_py, strict=True):
            _confere(js, py)


@pytest.mark.skipif(shutil.which("node") is None, reason="node não está instalado")
def test_fixture_covers_the_edge_cases() -> None:
    comum = leituras(_grupo_comum(), cenarios(22, 13)[0])
    sem_mad = leituras(_grupo_sem_mad(), cenarios(22, 13)[0])

    assert comum[-1].classe == "sem_base"
    assert all(item.z is not None for item in comum[:-1])
    assert {item.classe for item in sem_mad} != {"sem_base"}
    residuos = [item.residuo for item in sem_mad]
    centro = median(residuos)
    assert median(abs(valor - centro) for valor in residuos) == 0
