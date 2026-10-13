"""The power report stores grade cells and renders HTML on every presentation."""

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from eleicoes.domain.boletim_consulta import PoderPartido
from eleicoes.domain.errors import ElectionError, InvalidStoredReportError
from eleicoes.domain.grade import GradeDePoder, LugarVotos
from eleicoes.domain.stored_grade import StoredCell, cells_from_grades, grades_from_cells
from eleicoes.ports.relatorio_poder import StoredReport
from eleicoes.use_cases.apresentar_grade import PresentPartyGrades, _parser, main
from eleicoes.use_cases.apresentar_relatorio_poder import PresentedPowerReport, PresentPowerReport
from eleicoes.use_cases.grade import BuildPartyShareGrid

_KEY = (2026, 1, "deputadoFederal")
_MOMENT = datetime(2026, 10, 8, 17, 30, tzinfo=timezone(timedelta(hours=3)))
_LEVELS = ("municipio", "uf", "regiao", "pais")
_RELOADED = "\n".join(
    (
        "Por município: 1 lugar, 1 partido.",
        "Por estado: 0 lugares, 0 partidos.",
        "Por região: 0 lugares, 0 partidos.",
        "No país: 0 lugares, 0 partidos.",
    )
)


def test_missing_row_calculates_then_rerenders_without_ballots(tmp_path: Path) -> None:
    store = MemoryStore()
    seen: list[str] = []
    rendered = {"html": "version-1"}
    presenter = _presenter(seen, rendered)
    case = PresentPowerReport(presenter, store)
    destino = tmp_path / "saida" / "grade.html"

    case.execute(2026, 1, "AC", "deputadoFederal", destino, atualizar=False)

    assert seen == list(_LEVELS)
    assert destino.read_text(encoding="utf-8") == "version-1"
    assert store.saves == [(*_KEY, cells_from_grades(_four()))]
    rebuilt = grades_from_cells(2026, 1, "AC", "deputadoFederal", store.saves[0][3])
    assert tuple(len(grade.linhas) for grade in rebuilt) == (1, 1, 1, 1)
    seen.clear()
    rendered["html"] = "version-2"
    destino.write_text("tampered", encoding="utf-8")

    case.execute(2026, 1, "AC", "deputadoFederal", destino, atualizar=False)

    assert seen == []
    assert store.saves == [(*_KEY, cells_from_grades(_four()))]
    assert destino.read_text(encoding="utf-8") == "version-2"


def test_atualizar_recalculates_and_replaces_the_stored_cells(tmp_path: Path) -> None:
    nominal = {"value": 10}
    seen: list[str] = []

    def load(_ano: int, _turno: int, _uf: str, _cargo: str, nivel: str) -> GradeDePoder:
        seen.append(nivel)
        return _grade(nivel, nominal["value"])

    rendered = {"html": "version-1"}
    presenter = PresentPartyGrades(load, lambda _grades: rendered["html"], lambda _path: True)
    store = MemoryStore()
    case = PresentPowerReport(presenter, store)
    destino = tmp_path / "grade.html"
    case.execute(2026, 1, "AC", "deputadoFederal", destino)

    seen.clear()
    nominal["value"] = 40
    rendered["html"] = "version-2"
    case.execute(2026, 1, "AC", "deputadoFederal", destino, atualizar=True)

    assert seen == list(_LEVELS)
    assert destino.read_text(encoding="utf-8") == "version-2"
    assert {cell.votos_nominais for cell in store.rows[_KEY].cells} == {40}
    assert len(store.saves) == 2


def test_reloaded_summary_is_printed_with_the_stored_clock(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    store = MemoryStore()
    store.rows[_KEY] = StoredReport(_one_cell(), _MOMENT)
    destino = tmp_path / "grade.html"
    code = main(
        [*_args(destino), "--sem-navegador"],
        presenter=_presenter([], {"html": "from-renderer"}, fail=True),
        store=store,
    )
    captured = capsys.readouterr()
    stamp = _MOMENT.astimezone().strftime("%Y-%m-%d %H:%M")
    assert code == 0
    assert f"Relatório carregado do banco, gerado em {stamp}." in captured.out
    assert _RELOADED in captured.out
    assert str(destino.resolve()) in captured.out
    assert "Relatório gravado no banco." not in captured.out
    assert destino.read_text(encoding="utf-8") == "from-renderer"
    assert store.closed is True
    assert store.saves == []


def test_cached_open_failure_keeps_the_browser_sentence(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    store = MemoryStore()
    store.rows[_KEY] = StoredReport(_one_cell(), _MOMENT)
    destino = tmp_path / "grade.html"
    code = main(
        _args(destino),
        presenter=_presenter([], {"html": "from-renderer"}, opened=False),
        store=store,
    )
    captured = capsys.readouterr()
    assert code == 0
    assert "Relatório carregado do banco, gerado em " in captured.out
    assert captured.out.endswith("Não foi possível abrir o navegador.\n")
    assert destino.read_text(encoding="utf-8") == "from-renderer"


def test_fresh_report_appends_the_saved_sentence(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    store = MemoryStore()
    destino = tmp_path / "grade.html"
    code = main(
        _args(destino),
        presenter=_presenter([], {"html": "<html></html>"}, opened=False),
        store=store,
    )
    captured = capsys.readouterr()
    assert code == 0
    assert "Por município: 1 lugar, 1 partido." in captured.out
    assert captured.out.endswith(
        "Não foi possível abrir o navegador.\nRelatório gravado no banco.\n",
    )
    assert "Relatório carregado do banco" not in captured.out
    assert store.saves == [(*_KEY, cells_from_grades(_four()))]


def test_atualizar_flag_exists_and_main_saves_again(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    defaults = _parser().parse_args([])
    assert (defaults.ano, defaults.turno, defaults.uf, defaults.cargo) == _KEY[:2] + ("AC", _KEY[2])
    assert defaults.sem_navegador is False
    assert defaults.atualizar is False
    assert _parser().parse_args(["--atualizar"]).atualizar is True

    store = MemoryStore()
    store.rows[_KEY] = StoredReport(_one_cell(), _MOMENT)
    seen: list[str] = []
    destino = tmp_path / "grade.html"
    code = main(
        [*_args(destino), "--sem-navegador", "--atualizar"],
        presenter=_presenter(seen, {"html": "<new>"}),
        store=store,
    )
    captured = capsys.readouterr()
    assert code == 0
    assert seen == list(_LEVELS)
    assert destino.read_text(encoding="utf-8") == "<new>"
    assert store.saves == [(*_KEY, cells_from_grades(_four()))]
    assert "Relatório gravado no banco." in captured.out
    assert "Relatório carregado do banco" not in captured.out
    assert store.closed is True


def test_database_failure_stays_a_portuguese_message_without_traceback(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    store = BrokenStore()
    destino = tmp_path / "grade.html"
    code = main(_args(destino), presenter=_presenter([], {"html": "x"}), store=store)
    captured = capsys.readouterr()
    assert code == 1
    assert captured.err == "Não foi possível apresentar os relatórios.\n"
    assert captured.out == ""
    assert "Traceback" not in captured.err
    assert store.closed is True
    assert not destino.exists()


def test_inconsistent_turnout_stays_a_portuguese_message(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    store = MemoryStore()
    store.rows[_KEY] = StoredReport(
        (
            StoredCell("municipio", "1", "ALFA", 10, 13, 1, 0),
            StoredCell("municipio", "1", "ALFA", 11, 15, 1, 0),
        ),
        _MOMENT,
    )
    destino = tmp_path / "grade.html"
    code = main(
        _args(destino),
        presenter=_presenter([], {"html": "x"}, fail=True),
        store=store,
    )
    captured = capsys.readouterr()
    assert code == 1
    assert captured.err == "Não foi possível apresentar os relatórios.\n"
    assert "Traceback" not in captured.err
    assert store.closed is True
    assert not destino.exists()


def test_uf_is_the_render_anchor_and_does_not_filter_stored_places(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = {"n": 0}

    def load(ano: int, turno: int, uf: str, cargo: str, nivel: str) -> GradeDePoder:
        calls["n"] += 1
        return _anchored(ano, turno, uf, cargo, nivel)

    def render(grades: tuple[GradeDePoder, ...]) -> str:
        codes = ",".join(line.codigo for line in grades[0].linhas)
        return f"{grades[0].uf}:{codes}"

    monkeypatch.setattr("eleicoes.use_cases.apresentar_grade._load_grade", load)
    monkeypatch.setattr("eleicoes.use_cases.apresentar_grade.html_das_grades", render)
    store = MemoryStore()
    first = tmp_path / "pa.html"
    second = tmp_path / "ac.html"
    assert main([*_args(first), "--uf", "PA", "--sem-navegador"], store=store) == 0
    assert calls["n"] == len(_LEVELS)
    calls["n"] = 0
    assert main([*_args(second), "--uf", "AC", "--sem-navegador"], store=store) == 0
    assert calls["n"] == 0
    assert first.read_text(encoding="utf-8") == "PA:2710,1392"
    assert second.read_text(encoding="utf-8") == "AC:2710,1392"
    assert list(store.rows) == [_KEY]
    assert len(store.saves) == 1
    saved = store.saves[0][3]
    assert {cell.codigo for cell in saved} == {"1392", "2710"}
    assert any(cell.votos_nominais == 0 and cell.votos_legenda == 0 for cell in saved)
    assert len(saved) == 16


def test_cache_hit_uses_the_live_renderer_without_ballots(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = {"n": 0}

    def load(*args: object) -> GradeDePoder:
        calls["n"] += 1
        return _grade(str(args[-1]))

    rendered = {"html": "pagina-1"}
    monkeypatch.setattr("eleicoes.use_cases.apresentar_grade._load_grade", load)
    monkeypatch.setattr(
        "eleicoes.use_cases.apresentar_grade.html_das_grades",
        lambda _grades: rendered["html"],
    )
    store = MemoryStore()
    destino = tmp_path / "grade.html"
    assert main([*_args(destino), "--sem-navegador"], store=store) == 0
    assert destino.read_text(encoding="utf-8") == "pagina-1"
    assert calls["n"] == len(_LEVELS)
    rendered["html"] = "pagina-2"
    calls["n"] = 0
    assert main([*_args(destino), "--sem-navegador"], store=store) == 0
    assert calls["n"] == 0
    assert destino.read_text(encoding="utf-8") == "pagina-2"
    assert len(store.saves) == 1


def test_injected_store_is_used_when_the_presenter_comes_from_production(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "eleicoes.use_cases.apresentar_grade._load_grade",
        lambda *_args: _grade(str(_args[-1])),
    )
    store = MemoryStore()
    destino = tmp_path / "grade.html"
    code = main([*_args(destino), "--sem-navegador"], store=store)
    assert code == 0
    assert destino.read_text(encoding="utf-8")
    assert store.saves
    assert store.closed is True


def test_presented_report_rejects_a_blank_summary_and_a_naive_clock(tmp_path: Path) -> None:
    with pytest.raises(InvalidStoredReportError):
        PresentedPowerReport(tmp_path / "a.html", " ", True, False, _MOMENT)
    naive = datetime(2026, 10, 8, 14, 30)
    summary = "Por município: 1 lugar, 1 partido."
    with pytest.raises(InvalidStoredReportError):
        PresentedPowerReport(tmp_path / "a.html", summary, True, False, naive)


def test_stored_report_rejects_a_naive_clock() -> None:
    with pytest.raises(InvalidStoredReportError):
        StoredReport((), datetime(2026, 10, 8, 14, 30))
    assert StoredReport((), _MOMENT).cells == ()


def test_script_documents_grades_rendered_on_each_presentation() -> None:
    root = Path(__file__).resolve().parents[2]
    text = (root / "scripts" / "relatorio_poder.py").read_text(encoding="utf-8")
    assert "--atualizar" in text
    assert "O banco guarda as grades" in text
    assert "O HTML é montado em cada apresentação" in text
    assert "O HTML pronto fica no banco" not in text


class MemoryStore:
    def __init__(self) -> None:
        self.rows: dict[tuple[int, int, str], StoredReport] = {}
        self.saves: list[tuple[int, int, str, tuple[StoredCell, ...]]] = []
        self.closed = False

    def load(self, ano: int, turno: int, cargo: str) -> StoredReport | None:
        return self.rows.get((ano, turno, cargo))

    def save(
        self,
        ano: int,
        turno: int,
        cargo: str,
        cells: tuple[StoredCell, ...],
    ) -> datetime:
        self.saves.append((ano, turno, cargo, cells))
        self.rows[(ano, turno, cargo)] = StoredReport(cells, _MOMENT)
        return _MOMENT

    def close(self) -> None:
        self.closed = True


class BrokenStore:
    def __init__(self) -> None:
        self.closed = False

    def load(self, _ano: int, _turno: int, _cargo: str) -> StoredReport | None:
        raise ElectionError("database unavailable")

    def save(
        self,
        _ano: int,
        _turno: int,
        _cargo: str,
        _cells: tuple[StoredCell, ...],
    ) -> datetime:
        raise ElectionError("database unavailable")

    def close(self) -> None:
        self.closed = True


def _presenter(
    seen: list[str],
    rendered: dict[str, str],
    *,
    opened: bool = True,
    fail: bool = False,
) -> PresentPartyGrades:
    def load(_ano: int, _turno: int, _uf: str, _cargo: str, nivel: str) -> GradeDePoder:
        if fail:
            raise AssertionError("loader should not run")
        seen.append(nivel)
        return _grade(nivel)

    return PresentPartyGrades(load, lambda _grades: rendered["html"], lambda _path: opened)


def _grade(nivel: str, nominal: int = 10) -> GradeDePoder:
    place = LugarVotos(
        "1392",
        "RIO BRANCO",
        (PoderPartido(1392, None, 15, nominal, 0, 100),),
    )
    return BuildPartyShareGrid().execute(2026, 1, "AC", "deputadoFederal", nivel, (place,))


def _four(nominal: int = 10) -> tuple[GradeDePoder, ...]:
    return tuple(_grade(nivel, nominal) for nivel in _LEVELS)


def _one_cell() -> tuple[StoredCell, ...]:
    return (StoredCell("municipio", "1392", "RIO BRANCO", 100, 15, 10, 0),)


def _anchored(ano: int, turno: int, uf: str, cargo: str, nivel: str) -> GradeDePoder:
    return BuildPartyShareGrid().execute(ano, turno, uf, cargo, nivel, _two_places())


def _two_places() -> tuple[LugarVotos, ...]:
    return (
        LugarVotos(
            "2710",
            "BELEM",
            (
                PoderPartido(2710, None, 15, 3, 0, 50),
                PoderPartido(2710, None, 13, 0, 0, 50),
            ),
        ),
        LugarVotos(
            "1392",
            "RIO BRANCO",
            (
                PoderPartido(1392, None, 15, 10, 1, 100),
                PoderPartido(1392, None, 13, 0, 0, 100),
            ),
        ),
    )


def _args(destino: Path) -> list[str]:
    return [
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
    ]
