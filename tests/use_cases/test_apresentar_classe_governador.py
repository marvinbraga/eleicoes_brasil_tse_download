"""Governor-class CLI with a fake reader and a fake tree."""

from fractions import Fraction
from pathlib import Path

import pytest

from eleicoes.domain.classe_governador import ClassLine, ClassRule, RuleCut
from eleicoes.ports.classe_governador import ClassFit
from eleicoes.use_cases.apresentar_classe_governador import main


class _Reader:
    def __init__(self, lines: tuple[ClassLine, ...]) -> None:
        self.lines = lines
        self.calls = 0
        self.closed = False

    def class_lines(self, ano: int, turno: int) -> tuple[ClassLine, ...]:
        self.calls += 1
        self.seen = (ano, turno)
        return self.lines

    def close(self) -> None:
        self.closed = True


class _Model:
    def __init__(self, result: ClassFit) -> None:
        self.result = result
        self.matrix: tuple[tuple[float, ...], ...] = ()
        self.labels: tuple[str, ...] = ()
        self.parties: tuple[int, ...] = ()

    def fit(
        self,
        matrix: tuple[tuple[float, ...], ...],
        labels: tuple[str, ...],
        parties: tuple[int, ...],
    ) -> ClassFit:
        self.matrix = matrix
        self.labels = labels
        self.parties = parties
        return self.result


def test_report_uses_only_presidential_shares(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    model = _Model(_fit())
    reader = _Reader(_sample())
    destino = tmp_path / "classe.html"
    code = main(
        ["--ano", "2026", "--turno", "1", "--sem-navegador", "--destino", str(destino)],
        reader=reader,
        model=model,
    )
    html = destino.read_text(encoding="utf-8")
    captured = capsys.readouterr()

    assert code == 0
    assert model.parties == (13, 22)
    assert model.matrix[0] == (float(Fraction(10, 14)), float(Fraction(4, 14)))
    assert set(model.labels) == {"consolidacao", "em_aberto"}
    assert "100,00%" in html
    assert "50,00%" in html
    assert "Se a fatia do partido 13 for menor ou igual a 50,00%." in html
    assert "maior que 50,00%" in html
    assert "não é uma previsão do segundo turno" in html
    assert "Acerto no teste: 100,00%" in captured.out
    assert reader.closed is True
    assert reader.seen == (2026, 1)


def test_fewer_than_three_municipalities(capsys: pytest.CaptureFixture[str]) -> None:
    reader = _Reader(_city("1", "A", 13))
    code = main(["--sem-navegador"], reader=reader, model=_Model(_fit()))
    assert code == 1
    assert capsys.readouterr().err.strip() == "Menos de 3 municípios com votos válidos."
    assert reader.calls == 1
    assert reader.closed is True


def test_too_few_classes(capsys: pytest.CaptureFixture[str]) -> None:
    lines = _city("1", "A", 13) + _city("2", "B", 13) + _city("3", "C", 13)
    code = main(["--sem-navegador"], reader=_Reader(lines), model=_Model(_fit()))
    assert code == 1
    assert capsys.readouterr().err.strip() == "Não há classes suficientes para separar."


def test_invalid_turno_does_not_read(capsys: pytest.CaptureFixture[str]) -> None:
    reader = _Reader(())
    code = main(["--turno", "9", "--sem-navegador"], reader=reader, model=_Model(_fit()))
    assert code == 1
    assert "Turno inválido" in capsys.readouterr().err
    assert reader.calls == 0
    assert reader.closed is True


def test_closed_browser_keeps_the_file(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    destino = tmp_path / "classe.html"
    code = main(
        ["--destino", str(destino)],
        reader=_Reader(_sample()),
        model=_Model(_fit()),
        open_report=lambda _path: False,
    )
    assert code == 0
    assert destino.is_file()
    assert "Não foi possível abrir o navegador." in capsys.readouterr().out


def _fit() -> ClassFit:
    return ClassFit(
        "consolidacao",
        ("consolidacao", "em_aberto"),
        ("consolidacao", "em_aberto"),
        (
            ClassRule("consolidacao", (RuleCut(13, 0.5, True),)),
            ClassRule("em_aberto", (RuleCut(13, 0.5, False),)),
        ),
    )


def _sample() -> tuple[ClassLine, ...]:
    found: list[ClassLine] = []
    for index, governor in enumerate((13, 13, 13, 44, 44, 44)):
        found.extend(_city(str(index), f"C{index}", governor))
    return tuple(found)


def _city(codigo: str, nome: str, governor: int) -> tuple[ClassLine, ...]:
    return (
        ClassLine("presidente", codigo, nome, 100, 13, 10, 0),
        ClassLine("presidente", codigo, nome, 100, 22, 4, 0),
        ClassLine("governador", codigo, nome, 80, governor, 9, 0),
    )
