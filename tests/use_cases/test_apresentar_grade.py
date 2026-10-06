"""The party-power report writes one HTML file and asks for it to be opened."""

from pathlib import Path

import pytest

from eleicoes.domain.boletim_consulta import PoderPartido
from eleicoes.domain.grade import LugarVotos
from eleicoes.use_cases.apresentar_grade import PresentPartyGrades, main
from eleicoes.use_cases.grade import BuildPartyShareGrid

_LEVELS = ("municipio", "uf", "regiao", "pais")


def test_four_grids_are_written_and_opened(tmp_path: Path) -> None:
    seen: list[str] = []
    opened: list[Path] = []

    def load(ano: int, turno: int, uf: str, cargo: str, nivel: str) -> object:
        seen.append(nivel)
        assert (ano, turno, uf, cargo) == (2026, 1, "AC", "deputadoFederal")
        return _grade(nivel)

    def open_report(path: Path) -> bool:
        opened.append(path)
        return True

    destino = tmp_path / "saida" / "grade.html"
    report = PresentPartyGrades(load, lambda grades: f"grades:{len(grades)}", open_report).execute(
        2026,
        1,
        "AC",
        "deputadoFederal",
        destino,
    )
    assert seen == list(_LEVELS)
    assert destino.read_text(encoding="utf-8") == "grades:4"
    assert opened == [destino]
    assert report.aberto is True
    assert report.caminho == destino


def test_script_prints_the_path_and_skips_the_browser(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    destino = tmp_path / "grade.html"

    def load(_ano: int, _turno: int, _uf: str, _cargo: str, nivel: str) -> object:
        return _grade(nivel)

    presenter = PresentPartyGrades(load, lambda _grades: "<html></html>", lambda _path: False)
    code = main(
        [
            "--ano",
            "2026",
            "--turno",
            "1",
            "--uf",
            "AC",
            "--cargo",
            "deputadoFederal",
            "--destino",
            str(destino),
        ],
        presenter=presenter,
    )
    captured = capsys.readouterr()
    assert code == 0
    assert "Relatórios apresentados:" in captured.out
    assert str(destino) in captured.out
    assert "Por município: 1 lugar, 1 partido." in captured.out
    assert "Não foi possível abrir o navegador." in captured.out


def test_defaults_write_under_relatorios_and_open_the_browser(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "eleicoes.use_cases.apresentar_grade._load_grade",
        lambda *_args: _grade(_args[-1]),
    )
    opened: list[str] = []
    monkeypatch.setattr(
        "eleicoes.use_cases.apresentar_grade.webbrowser.open",
        lambda uri: opened.append(uri) or True,
    )
    code = main([])
    captured = capsys.readouterr()
    destino = tmp_path / "relatorios" / "ac-2026-turno-1-deputadoFederal.html"
    assert code == 0
    assert destino.is_file()
    assert opened == [destino.resolve().as_uri()]
    assert "Não foi possível abrir o navegador." not in captured.out


def test_sem_navegador_still_writes_the_report(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "eleicoes.use_cases.apresentar_grade._load_grade",
        lambda *_args: _grade(_args[-1]),
    )
    code = main(["--sem-navegador"])
    destino = tmp_path / "relatorios" / "ac-2026-turno-1-deputadoFederal.html"
    assert code == 0
    assert destino.is_file()


def test_invalid_uf_is_a_portuguese_failure(capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["--uf", "XX", "--sem-navegador", "--destino", "relatorios/nao-grava.html"])
    captured = capsys.readouterr()
    assert code == 1
    assert captured.err == "Não foi possível apresentar os relatórios.\n"
    assert not Path("relatorios/nao-grava.html").exists()


def _grade(nivel: str) -> object:
    place = LugarVotos("1392", "RIO BRANCO", (PoderPartido(1392, None, 15, 10, 0, 100),))
    return BuildPartyShareGrid().execute(2026, 1, "AC", "deputadoFederal", nivel, (place,))
