"""Use case, HTML and CSV of the section-level round comparison. No database."""

import csv
import io
import re
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path

import pytest

from eleicoes.adapters.csv_secoes_turnos import csv_das_secoes
from eleicoes.adapters.html_secoes_turnos import TITULO, html_das_secoes
from eleicoes.domain.anomalia_secao import analisar_secoes
from eleicoes.domain.boletim_consulta import VotosSecao
from eleicoes.domain.errors import ElectionError
from eleicoes.use_cases import apresentar_secoes_turnos
from eleicoes.use_cases.apresentar_secoes_turnos import PresentSections, main

_MOMENTO = datetime(2026, 10, 26, 15, 0, tzinfo=UTC)


def _secao(secao: int, a: int, b: int, outros: int, *, aptos: int = 400) -> VotosSecao:
    nominais = tuple((n, v) for n, v in ((13, b), (22, a), (30, outros)) if v > 0)
    return VotosSecao(1392, 1, secao, aptos, 0, 5, 5, nominais)


def _turnos() -> tuple[list[VotosSecao], list[VotosSecao]]:
    primeiro = [_secao(i, 120, 100, 20) for i in range(1, 13)]
    segundo = [_secao(i, 130 + i % 4, 110 - i % 3, 0) for i in range(1, 12)]
    segundo.append(_secao(12, 60, 180, 0, aptos=470))
    return primeiro, segundo


class _Reader:
    def __init__(self, ufs: tuple[str, ...] = ("AC",), fail: bool = False) -> None:
        self._ufs = ufs
        self._fail = fail
        self.calls: list[tuple[int, int, str, str]] = []
        self.asked: list[tuple[int, int, str]] = []
        self.closed = 0

    def present_ufs(self, ano: int, turno: int, cargo: str) -> tuple[str, ...]:
        self.asked.append((ano, turno, cargo))
        if self._fail:
            raise ElectionError("boom")
        return self._ufs

    def section_votes(self, ano: int, turno: int, uf: str, cargo: str) -> tuple[VotosSecao, ...]:
        self.calls.append((ano, turno, uf, cargo))
        primeiro, segundo = _turnos()
        return tuple(primeiro if turno == 1 else segundo)

    def close(self) -> None:
        self.closed += 1


class _Names:
    def __init__(self) -> None:
        self.asked: list[str] = []

    def names(self, uf: str) -> Mapping[int, str]:
        self.asked.append(uf)
        return {1392: "Rio <Branco>"}

    def close(self) -> None:
        return None


def test_use_case_writes_html_and_csv_side_by_side(tmp_path: Path) -> None:
    reader = _Reader()
    opened: list[Path] = []
    destino = tmp_path / "relatorios" / "secoes.html"
    report = PresentSections(
        reader,  # type: ignore[arg-type]
        _Names(),
        lambda path: opened.append(path) is None,
        clock=lambda: _MOMENTO,
    ).execute(2026, destino)
    assert report.opened
    assert opened == [destino]
    assert report.tabela == tmp_path / "relatorios" / "secoes.csv"
    assert reader.calls == [(2026, 1, "AC", "presidente"), (2026, 2, "AC", "presidente")]
    assert reader.asked == [(2026, 2, "presidente")]
    html = destino.read_text(encoding="utf-8")
    assert "Rio &lt;Branco&gt;" in html
    linhas = list(csv.DictReader(io.StringIO(report.tabela.read_text(encoding="utf-8"))))
    assert len(linhas) == 12
    assert linhas[-1]["verificacoes"] == "aptos_mudaram"


def test_html_has_scenarios_filter_sortable_rows_and_valid_script() -> None:
    primeiro, segundo = _turnos()
    analise = analisar_secoes({"AC": primeiro}, {"AC": segundo}, {"AC": {1392: "Rio Branco"}})
    html = html_das_secoes(2026, _MOMENTO, analise)
    assert f"<title>{TITULO}</title>" in html
    assert html.count('<option value="proporcional" selected>') == 1
    assert '<select id="uf"' in html
    assert '<option value="AC">Acre (AC)</option>' in html
    for cenario in analise.cenarios:
        assert f'data-cenario="{cenario.chave}"' in html
    assert 'data-uf="AC" data-destaque' in html
    assert "Verificações objetivas" in html
    assert "Aptos mudaram" in html
    assert "fraude" in html
    numeric = re.findall(r'<td class="num" data-ord="([^"]*)"', html)
    assert numeric
    assert all(re.fullmatch(r"-?\d+", value) for value in numeric)


def test_html_says_when_no_section_fails_a_check() -> None:
    primeiro = [_secao(i, 120, 100, 20) for i in range(1, 11)]
    segundo = [_secao(i, 130 + i % 4, 110 - i % 3, 0) for i in range(1, 11)]
    analise = analisar_secoes({"AC": primeiro}, {"AC": segundo}, {})
    assert "Nenhuma seção falhou" in html_das_secoes(2026, _MOMENTO, analise)


def test_csv_has_one_column_set_per_scenario() -> None:
    primeiro, segundo = _turnos()
    analise = analisar_secoes({"AC": primeiro}, {"AC": segundo}, {})
    linhas = list(csv.DictReader(io.StringIO(csv_das_secoes(analise))))
    assert {"z_proporcional", "esperado_a_todosa", "classe_maioriab"} <= set(linhas[0])
    assert linhas[-1]["classe_proporcional"] == "fora_b"
    assert linhas[0]["comparavel"] == "1"


def test_main_prints_counts_and_reports_failures(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    destino = tmp_path / "secoes.html"
    argv = ["--destino", str(destino), "--sem-navegador"]
    code = main(argv, reader=_Reader(), names=_Names(), clock=lambda: _MOMENTO)  # type: ignore[arg-type]
    out = capsys.readouterr().out
    assert code == 0
    assert "Pareadas: 12" in out
    assert "a normal esperaria" in out
    assert destino.exists()

    code = main(argv, reader=_Reader(ufs=()), names=_Names())  # type: ignore[arg-type]
    assert code == 1
    assert "Não há 2º turno" in capsys.readouterr().err

    code = main(argv, reader=_Reader(fail=True), names=_Names())  # type: ignore[arg-type]
    assert code == 1
    assert "Não foi possível" in capsys.readouterr().err


def test_main_reports_a_round_without_two_finalists(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    class _Alone(_Reader):
        def section_votes(
            self, ano: int, turno: int, uf: str, cargo: str
        ) -> tuple[VotosSecao, ...]:
            self.calls.append((ano, turno, uf, cargo))
            return (VotosSecao(1392, 1, 1, 300, 0, 0, 0, ((22, 200),)),)

    argv = ["--destino", str(tmp_path / "x.html"), "--sem-navegador"]
    assert main(argv, reader=_Alone(), names=_Names()) == 1  # type: ignore[arg-type]
    assert "dois finalistas" in capsys.readouterr().err

    def _outdated(*_args: object) -> object:
        raise apresentar_secoes_turnos.SchemaOutdatedError((), "r0001")

    monkeypatch.setattr(apresentar_secoes_turnos, "_production", _outdated)
    assert main(argv) == 1
