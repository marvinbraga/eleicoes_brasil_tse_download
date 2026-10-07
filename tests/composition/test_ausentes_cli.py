from pathlib import Path

import pytest

from eleicoes.composition.cli import main
from eleicoes.domain.report import EXIT_FAILURE, EXIT_SUCCESS

_LINE = "arquivo-urna/turno-1/MA/08435/0050/0102/o03220ma0843500500102-imgbu.dat"


def test_ausentes_writes_the_relative_report(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    destination = tmp_path / "saida"
    work = tmp_path / "trabalho"
    work.mkdir()
    monkeypatch.chdir(work)
    _touch(destination, f"{_LINE}.ausente")

    code = main(
        ["ausentes", "--ano", "2026", "--turno", "1", "--uf", "MA"],
        environ={"DIRETORIO_SAIDA": str(destination)},
    )

    captured = capsys.readouterr()
    report = work / "relatorios" / "ausentes-2026-turno-1-ma.txt"
    assert code == EXIT_SUCCESS
    assert report.read_text(encoding="utf-8") == f"{_LINE}\n"
    assert "Arquivos ausentes: 1." in captured.out
    assert "Relatório: relatorios/ausentes-2026-turno-1-ma.txt" in captured.out


def test_ausentes_writes_an_empty_report_when_nothing_is_marked(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    destination = tmp_path / "saida"
    destination.mkdir()
    work = tmp_path / "trabalho"
    work.mkdir()
    monkeypatch.chdir(work)

    code = main(
        ["ausentes", "--ano", "2026", "--turno", "1"],
        environ={"DIRETORIO_SAIDA": str(destination)},
    )

    captured = capsys.readouterr()
    report = work / "relatorios" / "ausentes-2026-turno-1.txt"
    assert code == EXIT_SUCCESS
    assert report.is_file()
    assert report.read_text(encoding="utf-8") == ""
    assert "Nenhum arquivo ausente." in captured.out
    assert "Relatório: relatorios/ausentes-2026-turno-1.txt" in captured.out


def test_ausentes_requires_turno_in_portuguese(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    code = main(["ausentes", "--ano", "2026"], environ={})
    assert code == EXIT_FAILURE
    assert "Turno inválido" in capsys.readouterr().err


def test_ausentes_rejects_an_invalid_uf_in_portuguese(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    code = main(
        ["ausentes", "--ano", "2026", "--turno", "1", "--uf", "XX"],
        environ={},
    )
    assert code == EXIT_FAILURE
    assert "UF inválida." in capsys.readouterr().err


def test_ausentes_rejects_an_invalid_year_in_portuguese(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    code = main(["ausentes", "--ano", "1800", "--turno", "1"], environ={})
    assert code == EXIT_FAILURE
    assert "Ano inválido" in capsys.readouterr().err


def _touch(root: Path, relative: str) -> None:
    path = root.joinpath(*relative.split("/"))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"")
