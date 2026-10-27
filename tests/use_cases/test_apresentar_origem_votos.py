"""Use case, HTML and CSV of "De onde vieram os votos". No database."""

import csv
import io
import json
import re
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path

import pytest

from eleicoes.adapters.csv_origem_votos import csv_da_origem
from eleicoes.adapters.html_origem_votos import (
    COR_PADRAO,
    LIMITE_DE_FALHAS,
    TITULO,
    PaginaDaOrigem,
    html_da_origem,
)
from eleicoes.domain.boletim_consulta import Participacao
from eleicoes.domain.errors import ElectionError
from eleicoes.domain.origem_votos import analisar_origem
from eleicoes.domain.presidente_governador import CargoTally, MunicipalPlace, PartyTally
from eleicoes.ports.relatorio_presidente_governador import StoredCrossReport
from eleicoes.use_cases import apresentar_origem_votos
from eleicoes.use_cases.apresentar_origem_votos import (
    PresentOrigin,
    bound_participation,
    ler_marcas,
    main,
)

_MOMENTO = datetime(2026, 10, 26, 15, 0, tzinfo=UTC)
_ANTES = datetime(2026, 10, 26, 12, 0, tzinfo=UTC)
_CARGA = datetime(2026, 10, 26, 14, 0, tzinfo=UTC)


def _place(uf: str, codigo: str, nome: str, votos: dict[int, int], bn: int) -> MunicipalPlace:
    parties = tuple(PartyTally(numero, total, 0) for numero, total in votos.items() if total)
    return MunicipalPlace(uf, codigo, nome, CargoTally(parties, bn, bn), None)


def _rounds() -> tuple[tuple[MunicipalPlace, ...], tuple[MunicipalPlace, ...]]:
    primeiro: list[MunicipalPlace] = []
    segundo: list[MunicipalPlace] = []
    for indice in range(1, 13):
        codigo = f"{1000 + indice}"
        nome = f"Cidade <{indice}>"
        uf = "AC" if indice <= 6 else "SP"
        primeiro.append(
            _place(uf, codigo, nome, {13: 1000 + 40 * indice, 22: 1200, 30: 300 + 10 * indice}, 50)
        )
        segundo.append(_place(uf, codigo, nome, {13: 1200 + 70 * indice, 22: 1400}, 40))
    primeiro.append(_place("ZZ", "29262", "Lisboa", {13: 10, 22: 10}, 1))
    return tuple(primeiro), tuple(segundo)


def _cedulas(place: MunicipalPlace) -> int:
    return place.presidente.valid + place.presidente.branco + place.presidente.nulo


class _Store:
    def __init__(self, vazio: int | None = None) -> None:
        self._vazio = vazio
        self.asked: list[tuple[int, int]] = []

    def load(self, ano: int, turno: int) -> StoredCrossReport | None:
        self.asked.append((ano, turno))
        if turno == self._vazio:
            return None
        primeiro, segundo = _rounds()
        return StoredCrossReport(primeiro if turno == 1 else segundo, _ANTES)


class _Participation:
    def __init__(self, desvio: int = 0) -> None:
        self._desvio = desvio
        self.calls: list[tuple[int, int, tuple[str, ...]]] = []

    def __call__(
        self, ano: int, turno: int, ufs: tuple[str, ...]
    ) -> dict[tuple[str, str], tuple[int, int]]:
        self.calls.append((ano, turno, ufs))
        primeiro, segundo = _rounds()
        places = primeiro if turno == 1 else segundo
        found: dict[tuple[str, str], tuple[int, int]] = {}
        for place in places:
            if place.uf not in ufs:
                continue
            extra = self._desvio if (turno == 2 and place.uf == "SP") else 0
            found[(place.uf, place.codigo)] = (5000, _cedulas(place) + extra)
        return found


def _executar(tmp_path: Path, participation: _Participation | None = None) -> tuple[Path, object]:
    opened: list[Path] = []
    destino = tmp_path / "relatorios" / "origem.html"
    report = PresentOrigin(
        _Store().load,
        participation if participation is not None else _Participation(),
        lambda path: opened.append(path) is None,
        last_load=lambda _ano, _turno: _CARGA,
        cores={13: "#e15759", 22: "#4e79a7"},
        siglas={13: "PT", 22: "PL"},
        clock=lambda: _MOMENTO,
    ).execute(2026, destino)
    assert opened == [destino]
    return destino, report


def test_use_case_writes_html_and_csv_and_reads_turnout_once_per_round(tmp_path: Path) -> None:
    participation = _Participation()
    destino, report = _executar(tmp_path, participation)
    assert destino.is_file()
    assert destino.with_suffix(".csv").is_file()
    assert [(turno, ufs) for _, turno, ufs in participation.calls] == [
        (1, ("AC", "SP")),
        (2, ("AC", "SP")),
    ]
    origem = report.origem  # type: ignore[attr-defined]
    assert len(origem.municipios) == 12
    assert origem.falhas == ()
    assert origem.ufs_sem_segundo_turno == ("ZZ",)


def test_html_is_self_contained_with_both_themes_and_party_colors(tmp_path: Path) -> None:
    destino, _ = _executar(tmp_path)
    html = destino.read_text(encoding="utf-8")
    assert f"<title>{TITULO}</title>" in html
    assert "prefers-color-scheme: dark" in html
    assert ':root[data-theme="dark"]' in html
    assert "<script src" not in html
    assert "<link" not in html
    assert "#e15759" in html and "#4e79a7" in html
    assert "13 (PT)" in html
    assert "Cidade &lt;3&gt;" in html
    assert "Cidade <3>" not in html
    assert html.count('<svg class="dispersao"') == 2
    assert html.count("<circle") == 24
    assert "Pearson ponderado" in html and "Spearman ponderado" in html
    assert "Nada aqui prova ou descarta fraude" in html
    assert "Boletins chegaram depois" in html
    assert "Não fecha em <strong>0</strong>" in html
    assert "Sem 2º turno gravado, fora da comparação: ZZ" in html


def test_html_lists_identity_failures_by_uf(tmp_path: Path) -> None:
    destino, report = _executar(tmp_path, _Participation(desvio=5))
    html = destino.read_text(encoding="utf-8")
    assert len(report.origem.falhas) == 6  # type: ignore[attr-defined]
    assert "Não fecha em <strong>6</strong>" in html
    assert "Por UF: SP (6)." in html
    assert 'class="num falha" data-ord="-5"' in html


def test_csv_has_one_row_per_municipality_and_closes_the_identity(tmp_path: Path) -> None:
    destino, _ = _executar(tmp_path)
    linhas = destino.with_suffix(".csv").read_text(encoding="utf-8").splitlines()
    assert linhas[0] == "# a = 13; b = 22"
    rows = list(csv.DictReader(io.StringIO("\n".join(linhas[1:]))))
    assert len(rows) == 12
    for row in rows:
        novos = int(row["delta_a"]) + int(row["delta_b"])
        fontes = (
            int(row["eliminados_1"])
            - int(row["delta_branco_nulo"])
            + int(row["delta_comparecimento"])
        )
        assert novos == fontes == int(row["fontes"])
        assert row["residuo"] == "0"
    assert rows[0]["municipio"] == "01001"


def test_page_without_colors_or_dates_falls_back() -> None:
    primeiro, segundo = _rounds()
    participacoes = {
        (turno, place.uf, place.codigo.zfill(5)): (5000, _cedulas(place))
        for turno, places in ((1, primeiro), (2, segundo))
        for place in places
    }
    origem = analisar_origem(primeiro, segundo, participacoes)
    html = html_da_origem(PaginaDaOrigem(2026, _MOMENTO, origem, cores={13: "red;x"}, siglas={}))
    assert COR_PADRAO in html
    assert "red;x" not in html
    assert "Dados:" not in html
    assert "finalistas 13 e 22" in html
    assert csv_da_origem(origem).count("\n") == 14


def test_failure_table_is_capped() -> None:
    primeiro: list[MunicipalPlace] = []
    segundo: list[MunicipalPlace] = []
    participacoes: dict[tuple[int, str, str], tuple[int, int]] = {}
    for indice in range(LIMITE_DE_FALHAS + 5):
        codigo = f"{10000 + indice}"
        um = _place("MG", codigo, f"M{indice}", {13: 100, 22: 100, 30: 10}, 5)
        dois = _place("MG", codigo, f"M{indice}", {13: 110, 22: 105}, 5)
        primeiro.append(um)
        segundo.append(dois)
        participacoes[(1, "MG", codigo)] = (500, _cedulas(um))
        participacoes[(2, "MG", codigo)] = (500, _cedulas(dois) + 1)
    origem = analisar_origem(primeiro, segundo, participacoes)
    html = html_da_origem(PaginaDaOrigem(2026, _MOMENTO, origem))
    assert f"Mostrando {LIMITE_DE_FALHAS} de" in html


def test_marks_reader_keeps_colors_and_acronyms(tmp_path: Path) -> None:
    caminho = tmp_path / "marcas.json"
    caminho.write_text(
        json.dumps({"13": {"cor": "#e15759", "sigla": "PT"}, "x": {}, "22": {"cor": 1}}),
        encoding="utf-8",
    )
    assert ler_marcas(caminho) == ({13: "#e15759"}, {13: "PT"})
    assert ler_marcas(tmp_path / "nada.json") == ({}, {})
    caminho.write_text("[1]", encoding="utf-8")
    assert ler_marcas(caminho) == ({}, {})


def test_bound_participation_pads_codes_per_uf() -> None:
    class _Reader:
        def __init__(self) -> None:
            self.calls: list[tuple[int, int, str, str, str]] = []

        def participation(
            self, _ano: int, turno: int, uf: str, _cargo: str, _nivel: str
        ) -> tuple[Participacao, ...]:
            self.calls.append((_ano, turno, uf, _cargo, _nivel))
            return (Participacao(1007, None, 100, 80),)

    reader = _Reader()
    found = bound_participation(reader)(2026, 2, ("AC", "AL"))  # type: ignore[arg-type]
    assert found == {("AC", "01007"): (100, 80), ("AL", "01007"): (100, 80)}
    assert [call[2] for call in reader.calls] == ["AC", "AL"]
    assert reader.calls[0][3:] == ("presidente", "municipio")


def test_main_prints_the_pools_and_correlations(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    marcas = tmp_path / "marcas.json"
    marcas.write_text(json.dumps({"13": {"cor": "#e15759", "sigla": "PT"}}), encoding="utf-8")
    destino = tmp_path / "saida.html"
    code = main(
        ["--ano", "2026", "--destino", str(destino), "--sem-navegador"],
        load=_Store().load,
        participation=_Participation(),
        clock=lambda: _MOMENTO,
        marcas=marcas,
    )
    out = capsys.readouterr().out
    assert code == 0
    assert "Votos novos:" in out
    assert "(resíduo 0)" in out
    assert re.search(r"Eliminados × virada: Pearson -?\d", out)
    assert "Sem 2º turno gravado: ZZ." in out
    assert "Identidade: não fecha em 0 de 12 municípios." in out
    assert "13 (PT)" in destino.read_text(encoding="utf-8")


@pytest.mark.parametrize("turno", [1, 2])
def test_main_reports_a_missing_round(
    turno: int, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code = main(
        ["--destino", str(tmp_path / "x.html"), "--sem-navegador"],
        load=_Store(vazio=turno).load,
        participation=_Participation(),
    )
    assert code == 1
    assert f"Não há lugares gravados do {turno}º turno de 2026" in capsys.readouterr().err


def test_main_reports_round_two_without_finalists(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    def load(_ano: int, turno: int) -> StoredCrossReport | None:
        primeiro, _ = _rounds()
        if turno == 1:
            return StoredCrossReport(primeiro, _ANTES)
        return StoredCrossReport((_place("AC", "1001", "Só um", {13: 10}, 1),), _ANTES)

    code = main(
        ["--destino", str(tmp_path / "x.html"), "--sem-navegador"],
        load=load,
        participation=_Participation(),
    )
    assert code == 1
    assert "dois finalistas" in capsys.readouterr().err


def test_main_reports_generic_and_schema_errors(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    from eleicoes.domain.errors import SchemaOutdatedError

    def falha(_ano: int, _turno: int) -> StoredCrossReport | None:
        raise ElectionError("boom")

    def velho(_ano: int, _turno: int) -> StoredCrossReport | None:
        raise SchemaOutdatedError(("a",), "b")

    args = ["--destino", str(tmp_path / "x.html"), "--sem-navegador"]
    assert main(args, load=falha, participation=_Participation()) == 1
    assert "Não foi possível apresentar a origem dos votos." in capsys.readouterr().err
    assert main(args, load=velho, participation=_Participation()) == 1
    assert capsys.readouterr().err.strip() != ""


def test_default_destination_and_openers(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    abertos: list[str] = []
    monkeypatch.setattr(
        apresentar_origem_votos.webbrowser, "open", lambda uri: abertos.append(uri) or True
    )
    monkeypatch.chdir(tmp_path)
    assert main([], load=_Store().load, participation=_Participation()) == 0
    assert (tmp_path / "relatorios" / "origem-votos-2026.html").is_file()
    assert abertos and abertos[0].startswith("file://")


def test_production_wires_store_and_reader(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from eleicoes.composition import boletim, presidente_governador

    closed: list[str] = []

    class _Reader:
        def participation(
            self, _ano: int, turno: int, uf: str, _cargo: str, _nivel: str
        ) -> tuple[Participacao, ...]:
            primeiro, segundo = _rounds()
            places = primeiro if turno == 1 else segundo
            return tuple(
                Participacao(int(place.codigo), None, 5000, _cedulas(place))
                for place in places
                if place.uf == uf
            )

        def last_load(self, _ano: int, _turno: int) -> datetime | None:
            return _CARGA

        def close(self) -> None:
            closed.append("reader")

    class _ProductionStore(_Store):
        def close(self) -> None:
            closed.append("store")

    def build_reader(_env: Mapping[str, str]) -> _Reader:
        return _Reader()

    def build_store(_env: Mapping[str, str] | None = None) -> _ProductionStore:
        return _ProductionStore()

    monkeypatch.setattr(boletim, "build_boletim_reader", build_reader)
    monkeypatch.setattr(presidente_governador, "build_cross_report_store", build_store)
    monkeypatch.setattr(apresentar_origem_votos, "load_dotenv", lambda: None)
    destino = tmp_path / "prod.html"
    assert main(["--destino", str(destino), "--sem-navegador"]) == 0
    assert sorted(closed) == ["reader", "store"]
    assert "Boletins chegaram depois" in destino.read_text(encoding="utf-8")
