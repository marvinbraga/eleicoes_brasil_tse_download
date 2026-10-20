"""Governor-class CLI with a fake reader and a fake tree."""

from fractions import Fraction
from pathlib import Path

import pytest
from tests.support import alternating_states

from eleicoes.domain.classe_governador import ClassLine, ClassRule, RuleCut
from eleicoes.domain.errors import InconsistentCellError
from eleicoes.ports.classe_governador import ClassFit
from eleicoes.use_cases.apresentar_classe_governador import build_governor_class, main


class _Reader:
    def __init__(
        self,
        lines: tuple[ClassLine, ...],
        ufs: tuple[tuple[str, str], ...] | None = None,
    ) -> None:
        self.lines = lines
        self.ufs = alternating_states(lines) if ufs is None else ufs
        self.uf_calls: list[tuple[int, int]] = []
        self.calls = 0
        self.closed = False

    def class_lines(self, ano: int, turno: int) -> tuple[ClassLine, ...]:
        self.calls += 1
        self.seen = (ano, turno)
        return self.lines

    def municipal_ufs(self, ano: int, turno: int) -> tuple[tuple[str, str], ...]:
        self.uf_calls.append((ano, turno))
        return self.ufs

    def close(self) -> None:
        self.closed = True


class _Model:
    def __init__(self, rules: tuple[ClassRule, ...], guess: str | None = None) -> None:
        self.rules = rules
        self.guess = guess
        self.matrix: tuple[tuple[float, ...], ...] = ()
        self.labels: tuple[str, ...] = ()
        self.parties: tuple[int, ...] = ()
        self.groups: tuple[str, ...] = ()

    def fit(
        self,
        matrix: tuple[tuple[float, ...], ...],
        labels: tuple[str, ...],
        parties: tuple[int, ...],
        groups: tuple[str, ...],
    ) -> ClassFit:
        self.matrix = matrix
        self.labels = labels
        self.parties = parties
        self.groups = groups
        predicted = labels if self.guess is None else (self.guess,) * len(labels)
        return ClassFit(predicted, self.rules)


def test_report_uses_only_presidential_shares(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    model = _Model(_rules())
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
    assert model.groups == ("SP", "MG") * 3
    assert "100,00%" in html
    assert "Linha de base da maioria: <strong>33,33%</strong>" in html
    assert "Se a fatia do partido 13 for menor ou igual a 50,00%." in html
    assert "maior que 50,00%" in html
    assert "não é uma previsão do segundo turno" in html
    assert (
        "Acerto em UF não vista: 100,00%. Linha de base da maioria: 33,33%. "
        "Linha de base do líder presidencial: 33,33%."
    ) in captured.out
    assert "Acerto no teste" not in captured.out
    assert reader.closed is True
    assert reader.seen == (2026, 1)
    assert reader.uf_calls == [(2026, 1)]


def test_report_scores_the_model_predictions_not_the_labels() -> None:
    model = _Model(_rules(), guess="consolidacao")
    report = build_governor_class(_Reader(_sample()), model, 2026, 1)
    assert report.hit_rate == Fraction(1, 2)
    assert [(s.uf, s.municipios, s.hit_rate) for s in report.by_uf] == [
        ("MG", 3, Fraction(1, 3)),
        ("SP", 3, Fraction(2, 3)),
    ]
    assert {row.classe: row.recall for row in report.rows} == {
        "consolidacao": Fraction(1),
        "em_aberto": Fraction(0),
    }


def test_fewer_than_three_municipalities(capsys: pytest.CaptureFixture[str]) -> None:
    reader = _Reader(_city("1", "A", 13))
    code = main(["--sem-navegador"], reader=reader, model=_Model(_rules()))
    assert code == 1
    assert capsys.readouterr().err.strip() == "Menos de 3 municípios com votos válidos."
    assert reader.calls == 1
    assert reader.closed is True


def test_missing_cross_report_is_reported(capsys: pytest.CaptureFixture[str]) -> None:
    reader = _Reader(_sample(), ufs=())
    code = main(["--sem-navegador"], reader=reader, model=_Model(_rules()))
    assert code == 1
    assert capsys.readouterr().err.strip() == "Gere o relatório presidente × governador antes."
    assert reader.closed is True


def test_too_few_classes(capsys: pytest.CaptureFixture[str]) -> None:
    lines = _city("1", "A", 13) + _city("2", "B", 13) + _city("3", "C", 13)
    code = main(["--sem-navegador"], reader=_Reader(lines), model=_Model(_rules()))
    assert code == 1
    assert capsys.readouterr().err.strip() == "Não há classes suficientes para separar."


def test_invalid_turno_does_not_read(capsys: pytest.CaptureFixture[str]) -> None:
    reader = _Reader(())
    code = main(["--turno", "9", "--sem-navegador"], reader=reader, model=_Model(_rules()))
    assert code == 1
    assert "Turno inválido" in capsys.readouterr().err
    assert reader.calls == 0
    assert reader.closed is True


def test_closed_browser_keeps_the_file(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    destino = tmp_path / "classe.html"
    code = main(
        ["--destino", str(destino)],
        reader=_Reader(_sample()),
        model=_Model(_rules()),
        open_report=lambda _path: False,
    )
    assert code == 0
    assert destino.is_file()
    assert "Não foi possível abrir o navegador." in capsys.readouterr().out


def _rules() -> tuple[ClassRule, ...]:
    return (
        ClassRule("consolidacao", (RuleCut(13, 0.5, True),)),
        ClassRule("em_aberto", (RuleCut(13, 0.5, False),)),
    )


def test_fit_rejects_empty_or_unknown_predictions() -> None:
    with pytest.raises(InconsistentCellError):
        ClassFit((), _rules())
    with pytest.raises(InconsistentCellError):
        ClassFit(("vitoria",), _rules())


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
