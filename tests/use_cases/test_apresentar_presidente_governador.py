"""The cross report stores municipal cells and renders HTML on every presentation."""

from collections.abc import Mapping
from datetime import datetime, timedelta, timezone
from fractions import Fraction
from pathlib import Path

import pytest

from eleicoes.domain.boletim_consulta import BrancosNulos, PoderPartido
from eleicoes.domain.errors import ElectionError, InvalidStoredReportError
from eleicoes.domain.presidente_governador import (
    CargoTally,
    CrossReportView,
    MunicipalPlace,
    PartyTally,
    read_place,
)
from eleicoes.ports.relatorio_presidente_governador import StoredCrossReport
from eleicoes.use_cases.apresentar_presidente_governador import (
    PresentedCrossReport,
    PresentPresidentGovernor,
    _open_browser,
    _parser,
    _production_collect,
    main,
)
from eleicoes.use_cases.presidente_governador import collect_places

_REASON = "Não foi possível apresentar os relatórios. Motivo: "

_MOMENT = datetime(2026, 10, 8, 18, 5, tzinfo=timezone(timedelta(hours=-3)))


def test_non_candidate_number_cannot_lead_and_joins_presidential_nulls() -> None:
    reader = _Reader()
    reader.ufs = {"presidente": ("AC",), "governador": ("AC",)}
    reader.rows[("AC", "presidente")] = (
        PoderPartido(10, None, 13, 10, 0, 999),
        PoderPartido(10, None, 22, 40, 0, 999),
        PoderPartido(10, None, 28, 40, 10, 999),
    )
    reader.rows[("AC", "governador")] = (
        PoderPartido(10, None, 28, 30, 20, 999),
        PoderPartido(10, None, 13, 10, 0, 999),
    )
    reader.blanks[("AC", "presidente")] = (BrancosNulos(10, None, 5, 7, 999),)
    reader.blanks[("AC", "governador")] = (BrancosNulos(10, None, 2, 3, 999),)
    places = collect_places(reader, _Names({"AC": {10: "Rio Branco"}}), 2026, 1)
    assert len(places) == 1
    place = places[0]
    assert place.nome == "Rio Branco (AC)"
    assert [item.partido for item in place.presidente.parties] == [13, 22]
    assert 28 not in [item.partido for item in place.presidente.parties]
    assert place.presidente.nulo == 57
    assert place.presidente.branco == 5
    reading = read_place(place)
    assert reading is not None
    assert reading.presidente.leader is not None
    assert reading.presidente.leader.partido == 22
    assert reading.presidente.runner_up is not None
    assert reading.presidente.runner_up.partido == 13
    assert reading.presidente.valid == 50
    assert reading.classe == "em_aberto"
    assert place.governador is not None
    governor = next(item for item in place.governador.parties if item.partido == 28)
    assert (governor.votos_nominais, governor.votos_legenda) == (30, 20)
    assert place.governador.nulo == 3
    assert reading.governador is not None
    assert reading.governador.leader is not None
    assert reading.governador.leader.partido == 28
    assert reading.presidente.ballot_share(57) == Fraction(57, 112)


def test_blank_denominator_is_ballots_not_comparecimento() -> None:
    reader = _Reader()
    reader.ufs = {"presidente": ("AC",), "governador": ("AC",)}
    reader.rows[("AC", "presidente")] = (
        PoderPartido(10, None, 13, 60, 0, 999),
        PoderPartido(10, None, 22, 40, 0, 999),
    )
    reader.rows[("AC", "governador")] = (PoderPartido(10, None, 13, 10, 0, 999),)
    reader.blanks[("AC", "presidente")] = (BrancosNulos(10, None, 10, 0, 999),)
    places = collect_places(reader, _Names({"AC": {}}), 2026, 1)
    reading = read_place(places[0])
    assert reading is not None
    assert reading.presidente.party_share(60) == Fraction(60, 100)
    assert reading.margin == Fraction(20, 100)
    assert reading.classe == "consolidacao"
    assert reading.presidente.ballot_share(10) == Fraction(10, 110)
    assert places[0].nome == "10 (AC)"


def test_two_ufs_and_a_place_without_governor() -> None:
    reader = _Reader()
    reader.ufs = {"presidente": ("PA", "ZZ"), "governador": ("AC", "PA")}
    reader.rows[("PA", "presidente")] = (PoderPartido(20, None, 13, 8, 0, 10),)
    reader.rows[("PA", "governador")] = (PoderPartido(20, None, 13, 3, 1, 10),)
    reader.rows[("ZZ", "presidente")] = (PoderPartido(30, None, 22, 15, 0, 20),)
    reader.rows[("AC", "governador")] = (PoderPartido(40, None, 13, 100, 0, 100),)
    names = _Names({"PA": {20: "Belem"}, "ZZ": {30: ""}, "AC": {40: "Rio Branco"}})
    places = collect_places(reader, names, 2026, 1)
    assert [(place.uf, place.codigo, place.nome) for place in places] == [
        ("PA", "20", "Belem (PA)"),
        ("ZZ", "30", "30 (ZZ)"),
    ]
    zz = places[1]
    assert zz.governador is None
    reading = read_place(zz)
    assert reading is not None
    assert reading.classe == "sem_governador"
    assert reading.presidente.valid == 15


def test_zero_vote_party_is_not_stored_and_missing_cedula_is_zero() -> None:
    reader = _Reader()
    reader.ufs = {"presidente": ("ac",), "governador": ()}
    reader.rows[("AC", "presidente")] = (
        PoderPartido(7, None, 13, 4, 0, 4),
        PoderPartido(7, None, 22, 0, 0, 4),
    )
    places = collect_places(reader, _Names({"AC": {7: "Xapuri"}}), 2026, 1)
    assert len(places) == 1
    assert [item.partido for item in places[0].presidente.parties] == [13]
    assert (places[0].presidente.branco, places[0].presidente.nulo) == (0, 0)
    assert places[0].governador is None


def test_cache_hit_does_not_call_the_reader_and_renderer_can_change(
    tmp_path: Path,
) -> None:
    reader = _Reader()
    _prime(reader, nominal=10)
    names = _Names({"AC": {10: "Rio Branco"}})
    seen: list[str] = []

    def collect(ano: int, turno: int) -> tuple[MunicipalPlace, ...]:
        seen.append("reader")
        return collect_places(reader, names, ano, turno)

    rendered = {"html": "pagina-1"}
    store = _Memory()
    case = PresentPresidentGovernor(
        collect,
        store,
        lambda _view: rendered["html"],
        lambda _path: True,
    )
    destino = tmp_path / "saida" / "cruzado.html"
    case.execute(2026, 1, "AC", destino, atualizar=False)
    assert seen == ["reader"]
    assert destino.read_text(encoding="utf-8") == "pagina-1"
    assert store.saves[0][0].presidente.parties[0].votos_nominais == 10
    rendered["html"] = "pagina-2"
    case.execute(2026, 1, "PA", destino, atualizar=False)
    assert seen == ["reader"]
    assert destino.read_text(encoding="utf-8") == "pagina-2"
    assert len(store.saves) == 1


def test_atualizar_replaces_the_stored_cells(tmp_path: Path) -> None:
    reader = _Reader()
    _prime(reader, nominal=10)
    names = _Names({"AC": {10: "Rio Branco"}})
    store = _Memory()
    case = PresentPresidentGovernor(
        lambda ano, turno: collect_places(reader, names, ano, turno),
        store,
        lambda _view: "html",
        lambda _path: True,
    )
    destino = tmp_path / "cruzado.html"
    case.execute(2026, 1, "AC", destino)
    reader.rows[("AC", "presidente")] = (PoderPartido(10, None, 13, 40, 0, 40),)
    case.execute(2026, 1, "AC", destino, atualizar=True)
    assert store.loads == 1
    assert store.saves[-1][0].presidente.parties[0].votos_nominais == 40
    assert len(store.saves) == 2


def test_uf_changes_the_filename_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    reader = _Reader()
    reader.ufs = {"presidente": ("PA", "AC"), "governador": ("PA", "AC")}
    reader.rows[("AC", "presidente")] = (PoderPartido(10, None, 13, 5, 0, 5),)
    reader.rows[("AC", "governador")] = (PoderPartido(10, None, 13, 2, 0, 2),)
    reader.rows[("PA", "presidente")] = (PoderPartido(20, None, 22, 9, 0, 9),)
    reader.rows[("PA", "governador")] = (PoderPartido(20, None, 22, 4, 0, 4),)
    names = _Names({"AC": {10: "Rio Branco"}, "PA": {20: "Belem"}})
    store = _Memory()
    before = len(reader.calls)
    assert (
        main(
            ["--ano", "2026", "--turno", "1", "--uf", "PA", "--sem-navegador"],
            reader=reader,
            names=names,
            store=store,
        )
        == 0
    )
    first = tmp_path / "relatorios" / "pa-2026-turno-1-presidente-governador.html"
    assert first.is_file()
    calls = len(reader.calls)
    assert calls > before
    assert (
        main(
            ["--ano", "2026", "--turno", "1", "--sem-navegador"],
            reader=reader,
            names=names,
            store=store,
        )
        == 0
    )
    second = tmp_path / "relatorios" / "ac-2026-turno-1-presidente-governador.html"
    assert second.is_file()
    assert first.read_text(encoding="utf-8") == second.read_text(encoding="utf-8")
    assert "Rio Branco (AC)" in first.read_text(encoding="utf-8")
    assert "Belem (PA)" in first.read_text(encoding="utf-8")
    assert len(reader.calls) == calls
    assert _parser().parse_args([]).uf == "AC"


def test_stdout_matches_the_power_report_shape(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    store = _Memory()
    place = MunicipalPlace(
        "AC",
        "10",
        "Rio Branco (AC)",
        CargoTally((PartyTally(13, 4, 0),), 0, 0),
        None,
    )
    store.rows[(2026, 1)] = StoredCrossReport((place,), _MOMENT)
    destino = tmp_path / "cruzado.html"
    code = main(
        ["--destino", str(destino), "--sem-navegador"],
        reader=_Reader(),
        names=_Names({}),
        store=store,
        render=lambda _view: "from-renderer",
    )
    captured = capsys.readouterr()
    stamp = _MOMENT.astimezone().strftime("%Y-%m-%d %H:%M")
    assert code == 0
    assert f"Relatório carregado do banco, gerado em {stamp}." in captured.out
    assert "Relatório gravado no banco." not in captured.out
    assert str(destino.resolve()) in captured.out
    assert "Por município:" in captured.out
    assert destino.read_text(encoding="utf-8") == "from-renderer"
    assert store.closed is True
    assert store.saves == []


def test_fresh_report_says_it_was_stored(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    reader = _Reader()
    _prime(reader, nominal=4)
    destino = tmp_path / "cruzado.html"
    code = main(
        ["--destino", str(destino)],
        reader=reader,
        names=_Names({"AC": {10: "Rio Branco"}}),
        store=_Memory(),
        open_report=lambda _path: False,
        render=lambda _view: "<html></html>",
    )
    captured = capsys.readouterr()
    assert code == 0
    ending = "Não foi possível abrir o navegador.\nRelatório gravado no banco.\n"
    assert captured.out.endswith(ending)
    assert "Relatório carregado do banco" not in captured.out


def test_failure_is_a_portuguese_message_without_traceback(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    destino = tmp_path / "cruzado.html"
    code = main(
        ["--destino", str(destino), "--uf", "XX"],
        reader=_Reader(),
        names=_Names({}),
        store=_Broken(),
    )
    captured = capsys.readouterr()
    assert code == 1
    assert captured.err == f"{_REASON}invalid UF: XX\n"
    assert captured.out == ""
    assert "Traceback" not in captured.err
    assert not destino.exists()


def test_database_failure_stays_portuguese(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    store = _Broken()
    destino = tmp_path / "cruzado.html"
    code = main(["--destino", str(destino)], reader=_Reader(), names=_Names({}), store=store)
    captured = capsys.readouterr()
    assert code == 1
    assert captured.err == f"{_REASON}database unavailable\n"
    assert store.closed is True
    assert not destino.exists()


def test_presented_report_rejects_a_blank_summary_and_a_naive_clock(tmp_path: Path) -> None:
    with pytest.raises(InvalidStoredReportError):
        PresentedCrossReport(tmp_path / "a.html", " ", True, False, _MOMENT)
    with pytest.raises(InvalidStoredReportError):
        PresentedCrossReport(
            tmp_path / "a.html",
            "Por município: 1 lugar.",
            True,
            False,
            datetime(2026, 10, 8),
        )


def test_script_documents_municipal_votes_and_html_on_each_presentation() -> None:
    root = Path(__file__).resolve().parents[2]
    text = (root / "scripts" / "relatorio_presidente_governador.py").read_text(encoding="utf-8")
    assert "uv run python scripts/relatorio_presidente_governador.py --ano 2026 --turno 1" in text
    assert "--sem-navegador" in text
    assert "--atualizar" in text
    assert "votos municipais" in text
    assert "O HTML é montado em cada apresentação" in text


def test_open_browser_uses_the_file_uri(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[str] = []
    monkeypatch.setattr(
        "eleicoes.use_cases.apresentar_presidente_governador.webbrowser.open",
        lambda url: seen.append(url) or True,
    )
    path = tmp_path / "a.html"
    path.write_text("x", encoding="utf-8")
    assert _open_browser(path) is True
    assert seen == [path.resolve().as_uri()]


def test_production_collect_closes_the_opened_ports(monkeypatch: pytest.MonkeyPatch) -> None:
    reader = _Reader()
    names = _Names({})
    monkeypatch.setattr("eleicoes.composition.boletim.build_boletim_reader", lambda _env: reader)
    monkeypatch.setattr("eleicoes.composition.grade.build_municipality_names", lambda _env: names)
    assert _production_collect(2026, 1) == ()
    assert reader.closed is True
    assert names.closed is True


def test_main_wires_the_store_only_when_it_is_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    created: list[object] = []

    def build(_env: object = None) -> _Memory:
        store = _Memory()
        created.append(store)
        return store

    monkeypatch.setattr(
        "eleicoes.composition.presidente_governador.build_cross_report_store",
        build,
    )
    destino = tmp_path / "cruzado.html"
    code = main(
        ["--destino", str(destino), "--sem-navegador"],
        reader=_Reader(),
        names=_Names({}),
    )
    assert code == 0
    assert len(created) == 1
    assert destino.is_file()


def test_render_receives_the_derived_view(tmp_path: Path) -> None:
    reader = _Reader()
    _prime(reader, nominal=10)
    seen: list[CrossReportView] = []

    def render(view: CrossReportView) -> str:
        seen.append(view)
        return "ok"

    store = _Memory()
    main(
        ["--destino", str(tmp_path / "a.html"), "--sem-navegador", "--atualizar"],
        reader=reader,
        names=_Names({"AC": {10: "Rio Branco"}}),
        store=store,
        render=render,
    )
    assert seen[0].municipalities[0][0] == "AC"
    assert seen[0].country is not None
    assert seen[0].country.nome == "Brasil"


class _Reader:
    def __init__(self) -> None:
        self.calls: list[tuple[object, ...]] = []
        self.ufs: dict[str, tuple[str, ...]] = {}
        self.rows: dict[tuple[str, str], tuple[PoderPartido, ...]] = {}
        self.blanks: dict[tuple[str, str], tuple[BrancosNulos, ...]] = {}
        self.closed = False

    def present_ufs(self, ano: int, turno: int, cargo: str) -> tuple[str, ...]:
        self.calls.append(("present_ufs", ano, turno, cargo))
        return self.ufs.get(cargo, ())

    def party_power(
        self,
        ano: int,
        turno: int,
        ufs: tuple[str, ...],
        cargo: str,
        nivel: str,
    ) -> tuple[PoderPartido, ...]:
        self.calls.append(("party_power", ano, turno, ufs, cargo, nivel))
        found: list[PoderPartido] = []
        for uf in ufs:
            found.extend(self.rows.get((uf, cargo), ()))
        return tuple(found)

    def blank_and_null(
        self,
        ano: int,
        turno: int,
        uf: str,
        cargo: str,
        nivel: str,
    ) -> tuple[BrancosNulos, ...]:
        self.calls.append(("blank_and_null", ano, turno, uf, cargo, nivel))
        return self.blanks.get((uf, cargo), ())

    def close(self) -> None:
        self.closed = True


class _Names:
    def __init__(self, found: dict[str, dict[int, str]]) -> None:
        self._found = found
        self.closed = False

    def names(self, uf: str) -> Mapping[int, str]:
        return self._found.get(uf, {})

    def close(self) -> None:
        self.closed = True


class _Memory:
    def __init__(self) -> None:
        self.rows: dict[tuple[int, int], StoredCrossReport] = {}
        self.saves: list[tuple[MunicipalPlace, ...]] = []
        self.loads = 0
        self.closed = False

    def load(self, ano: int, turno: int) -> StoredCrossReport | None:
        self.loads += 1
        return self.rows.get((ano, turno))

    def save(self, ano: int, turno: int, places: tuple[MunicipalPlace, ...]) -> datetime:
        self.saves.append(places)
        self.rows[(ano, turno)] = StoredCrossReport(places, _MOMENT)
        return _MOMENT

    def close(self) -> None:
        self.closed = True


class _Broken:
    def __init__(self) -> None:
        self.closed = False

    def load(self, _ano: int, _turno: int) -> StoredCrossReport | None:
        raise ElectionError("database unavailable")

    def save(self, _ano: int, _turno: int, _places: tuple[MunicipalPlace, ...]) -> datetime:
        raise ElectionError("database unavailable")

    def close(self) -> None:
        self.closed = True


def _prime(reader: _Reader, nominal: int) -> None:
    reader.ufs = {"presidente": ("AC",), "governador": ("AC",)}
    reader.rows[("AC", "presidente")] = (PoderPartido(10, None, 13, nominal, 0, nominal),)
    reader.rows[("AC", "governador")] = (PoderPartido(10, None, 13, 1, 0, 1),)


class _Chained(_Broken):
    def load(self, _ano: int, _turno: int) -> StoredCrossReport | None:
        cause = RuntimeError('null value in column "html"\nDETAIL:  row')
        raise ElectionError("cross report store failed") from cause


def test_database_failure_names_the_chained_cause(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    store = _Chained()
    destino = tmp_path / "cruzado.html"
    code = main(["--destino", str(destino)], reader=_Reader(), names=_Names({}), store=store)
    captured = capsys.readouterr()
    assert code == 1
    assert captured.err == (f'{_REASON}cross report store failed (null value in column "html")\n')
    assert store.closed is True
