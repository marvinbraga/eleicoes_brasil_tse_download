"""Profile CLI. Deputy cargos fail before any reader call."""

from pathlib import Path

import pytest

from eleicoes.domain.perfis import GroupSpan, ProfileLine
from eleicoes.ports.perfis import RawClusterFit
from eleicoes.use_cases.apresentar_perfis import main


class _Reader:
    def __init__(self, lines: tuple[ProfileLine, ...] = ()) -> None:
        self.lines = lines
        self.calls = 0
        self.closed = False

    def profile_lines(self, ano: int, turno: int, cargo: str) -> tuple[ProfileLine, ...]:
        self.calls += 1
        self.seen = (ano, turno, cargo)
        return self.lines

    def close(self) -> None:
        self.closed = True


class _Cluster:
    def fit(
        self,
        matrix: tuple[tuple[float, ...], ...],
        span: GroupSpan,
    ) -> RawClusterFit:
        width = len(matrix[0])
        k = span.values()[0]
        centers = tuple(tuple(0.0 for _column in range(width)) for _group in range(k))
        labels = tuple(index % k for index in range(len(matrix)))
        return RawClusterFit(labels, centers, 0.25 if span.searched else None)


def test_deputado_refuses_before_the_reader(
    capsys: pytest.CaptureFixture[str],
) -> None:
    reader = _Reader()
    code = main(
        ["--cargo", "deputadoFederal", "--sem-navegador"],
        reader=reader,
        clusterer=_Cluster(),
    )
    captured = capsys.readouterr()
    assert code == 1
    assert captured.err.strip() == "O cargo deputado federal não tem células gravadas."
    assert reader.calls == 0
    assert reader.closed is True


@pytest.mark.parametrize(
    ("cargo", "sentence"),
    [
        ("deputadoEstadual", "O cargo deputado estadual não tem células gravadas."),
        ("deputadoDistrital", "O cargo deputado distrital não tem células gravadas."),
    ],
)
def test_other_deputy_sentences(
    cargo: str,
    sentence: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    reader = _Reader()
    code = main(["--cargo", cargo, "--sem-navegador"], reader=reader, clusterer=_Cluster())
    assert code == 1
    assert capsys.readouterr().err.strip() == sentence
    assert reader.calls == 0


def test_unknown_cargo_uses_the_cargo_error(capsys: pytest.CaptureFixture[str]) -> None:
    reader = _Reader()
    code = main(["--cargo", "vereador", "--sem-navegador"], reader=reader, clusterer=_Cluster())
    assert code == 1
    assert capsys.readouterr().err.strip() == "Cargo inválido."
    assert reader.calls == 0


def test_missing_cells_return_the_portuguese_sentence(capsys: pytest.CaptureFixture[str]) -> None:
    reader = _Reader(())
    code = main(
        ["--cargo", "senador", "--sem-navegador", "--grupos", "2"],
        reader=reader,
        clusterer=_Cluster(),
    )
    assert code == 1
    assert capsys.readouterr().err.strip() == "Não há células gravadas para este cargo."
    assert reader.calls == 1
    assert reader.closed is True


def test_invalid_group_span_does_not_query(capsys: pytest.CaptureFixture[str]) -> None:
    reader = _Reader(_lines())
    code = main(
        ["--cargo", "senador", "--grupos", "6-2", "--sem-navegador"],
        reader=reader,
        clusterer=_Cluster(),
    )
    assert code == 1
    assert capsys.readouterr().err.strip() == "A faixa de grupos é inválida."
    assert reader.calls == 0


def test_report_is_written_without_opening_a_browser(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def boom(_url: str) -> bool:
        raise AssertionError("browser")

    monkeypatch.setattr("eleicoes.use_cases.apresentar_perfis.webbrowser.open", boom)
    destino = tmp_path / "perfis.html"
    reader = _Reader(_lines())
    code = main(
        ["--cargo", "senador", "--grupos", "2", "--sem-navegador", "--destino", str(destino)],
        reader=reader,
        clusterer=_Cluster(),
    )
    captured = capsys.readouterr()
    assert code == 0
    assert "Perfis municipais" in destino.read_text(encoding="utf-8")
    assert "Senador" in destino.read_text(encoding="utf-8")
    assert "grupos escolhidos" in destino.read_text(encoding="utf-8")
    assert "Alpha" in destino.read_text(encoding="utf-8")
    assert str(destino.resolve()) in captured.out
    assert reader.closed is True


def test_searched_summary_and_closed_browser(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    destino = tmp_path / "perfis.html"
    code = main(
        ["--cargo", "senador", "--grupos", "2-2", "--destino", str(destino)],
        reader=_Reader(_lines()),
        clusterer=_Cluster(),
        open_report=lambda _path: False,
    )
    captured = capsys.readouterr()
    assert code == 0
    assert "Silhueta" in captured.out
    assert "Não foi possível abrir o navegador." in captured.out
    assert "silhueta" in destino.read_text(encoding="utf-8")


def test_invalid_year_and_turno(capsys: pytest.CaptureFixture[str]) -> None:
    reader = _Reader()
    assert main(["--ano", "1800", "--sem-navegador"], reader=reader, clusterer=_Cluster()) == 1
    assert "Ano inválido" in capsys.readouterr().err
    assert main(["--turno", "3", "--sem-navegador"], reader=reader, clusterer=_Cluster()) == 1
    assert "Turno inválido" in capsys.readouterr().err
    assert reader.calls == 0


def _lines() -> tuple[ProfileLine, ...]:
    return (
        ProfileLine("1", "Alpha", 10, 13, 4, 0),
        ProfileLine("2", "Beta", 10, 13, 4, 0),
        ProfileLine("3", "Gama", 12, 22, 5, 0),
    )
