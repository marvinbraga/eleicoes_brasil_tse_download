"""The map command paints the leading party and reuses stored municipal votes."""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from eleicoes.domain.boletim_consulta import Participacao
from eleicoes.domain.errors import (
    SCHEMA_OUTDATED_HINT,
    ElectionError,
    InvalidStoredReportError,
    SchemaOutdatedError,
)
from eleicoes.domain.mapa import (
    Marca,
    MeshMissingError,
    PaginaDoMapa,
    PonteTseIbge,
    ponte_de_linhas,
)
from eleicoes.domain.presidente_governador import CargoTally, MunicipalPlace, PartyTally
from eleicoes.ports.malha import MalhaCarregada, Manifesto
from eleicoes.ports.relatorio_presidente_governador import StoredCrossReport
from eleicoes.use_cases.apresentar_mapa import PresentedMap, main

_MOMENT = datetime(2026, 10, 8, 18, 5, tzinfo=timezone(timedelta(hours=-3)))
_HEADER = (
    "DT_GERACAO",
    "HH_GERACAO",
    "CD_UF_TSE",
    "CD_UF_IBGE",
    "SG_UF",
    "NM_UF",
    "CD_MUNICIPIO_TSE",
    "NM_MUNICIPIO_TSE",
    "CD_MUNICIPIO_IBGE",
    "NM_MUNICIPIO_IBGE",
)
_GENERIC = "Não foi possível apresentar o mapa.\n"


def test_command_writes_the_president_map_without_a_browser(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    destino = tmp_path / "mapa.html"
    code = main(
        [
            "--ano",
            "2026",
            "--turno",
            "1",
            "--cargo",
            "presidente",
            "--destino",
            str(destino),
            "--sem-navegador",
        ],
        store=_Memory(),
        assets=_Assets(),
        collect=lambda _ano, _turno: (_bujari(),),
    )
    text = destino.read_text(encoding="utf-8")
    assert code == 0
    assert destino.is_file()
    assert "Mapa de presidente — 2026, turno 1" in text
    assert '"numero": "22"' in text
    assert capsys.readouterr().out == (f"Mapa gravado em {destino}.\nVotos gravados no banco.\n")


def test_injected_opener_records_the_path(tmp_path: Path) -> None:
    destino = tmp_path / "mapa.html"
    opened: list[Path] = []
    main(
        ["--ano", "2026", "--turno", "1", "--cargo", "presidente", "--destino", str(destino)],
        store=_Memory(),
        assets=_Assets(),
        collect=lambda _ano, _turno: (_bujari(),),
        open_report=opened.append,
    )
    assert opened == [destino]


def test_injected_opener_wins_when_the_browser_is_disabled(tmp_path: Path) -> None:
    destino = tmp_path / "mapa.html"
    opened: list[Path] = []
    code = main(
        [
            "--ano",
            "2026",
            "--turno",
            "1",
            "--cargo",
            "presidente",
            "--destino",
            str(destino),
            "--sem-navegador",
        ],
        store=_Memory(),
        assets=_Assets(),
        collect=lambda _ano, _turno: (_bujari(),),
        open_report=opened.append,
    )
    assert code == 0
    assert opened == [destino]


def test_missing_mesh_exits_1(capsys: pytest.CaptureFixture[str]) -> None:
    code = main(
        ["--cargo", "presidente", "--sem-navegador"],
        store=_Memory(),
        assets=_BrokenAssets(),
        collect=lambda _ano, _turno: (),
        open_report=lambda _path: True,
    )
    assert code == 1
    assert "Falta downloads/malha/manifesto.json." in capsys.readouterr().err


def test_governor_page_uses_the_governor_number(tmp_path: Path) -> None:
    destino = tmp_path / "mapa.html"
    main(
        ["--cargo", "governador", "--destino", str(destino), "--sem-navegador"],
        store=_Memory(),
        assets=_Assets(),
        collect=lambda _ano, _turno: (_bujari(),),
        open_report=lambda _path: True,
    )
    text = destino.read_text(encoding="utf-8")
    assert "Mapa de governador — 2026, turno 1" in text
    assert '"numero": "13"' in text


def test_reload_does_not_collect_again(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    destino = tmp_path / "mapa.html"
    store = _Memory()
    store.save(2026, 1, (_bujari(),))
    calls: list[tuple[int, int]] = []

    def collect(ano: int, turno: int) -> tuple[MunicipalPlace, ...]:
        calls.append((ano, turno))
        return (_bujari(),)

    code = main(
        _command(destino),
        store=store,
        assets=_Assets(),
        collect=collect,
    )
    stamp = _MOMENT.astimezone().strftime("%Y-%m-%d %H:%M")
    assert code == 0
    assert calls == []
    assert capsys.readouterr().out == (
        f"Mapa gravado em {destino}.\nVotos carregados do banco, gerados em {stamp}.\n"
    )
    code = main(
        [*_command(destino), "--atualizar"],
        store=store,
        assets=_Assets(),
        collect=collect,
    )
    assert code == 0
    assert calls == [(2026, 1)]
    assert capsys.readouterr().out == (f"Mapa gravado em {destino}.\nVotos gravados no banco.\n")


def test_missing_bridge_exits_1(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    destino = tmp_path / "mapa.html"
    code = main(
        _command(destino),
        store=_Memory(),
        assets=_Assets(),
        collect=lambda _ano, _turno: (_place("AC", "99999", "Ausente", 22, 13),),
    )
    assert code == 1
    assert capsys.readouterr().err == ("Não há código IBGE para o município 99999 (AC).\n")
    assert not destino.is_file()


def test_missing_mark_exits_1(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    destino = tmp_path / "mapa.html"
    code = main(
        _command(destino),
        store=_Memory(),
        assets=_Assets(marcas={}),
        collect=lambda _ano, _turno: (_bujari(),),
    )
    assert code == 1
    assert capsys.readouterr().err == "Falta a cor ou a logomarca do partido 22.\n"
    assert not destino.is_file()


def test_brasil_outside_the_country_ids_is_generic(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    destino = tmp_path / "mapa.html"
    code = main(
        _command(destino),
        store=_Memory(),
        assets=_Assets(ids_pais=frozenset({"032"})),
        collect=lambda _ano, _turno: (_bujari(),),
    )
    captured = capsys.readouterr()
    assert code == 1
    assert captured.err == _GENERIC
    assert captured.out == ""
    assert not destino.is_file()


def test_invalid_cargo_never_exits_2(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    destino = tmp_path / "mapa.html"
    code = main(
        ["--cargo", "senador", "--destino", str(destino), "--sem-navegador"],
        store=_Memory(),
        assets=_Assets(),
        collect=lambda _ano, _turno: (_bujari(),),
    )
    captured = capsys.readouterr()
    assert code == 1
    assert captured.err == _GENERIC
    assert "Traceback" not in captured.err
    assert not destino.is_file()


def test_missing_cargo_flag_returns_1(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    destino = tmp_path / "mapa.html"
    code = main(
        ["--destino", str(destino), "--sem-navegador"],
        store=_Memory(),
        assets=_Assets(),
        collect=lambda _ano, _turno: (_bujari(),),
    )
    assert code == 1
    assert capsys.readouterr().err == _GENERIC
    assert not destino.is_file()


def test_store_failure_stays_portuguese_and_closes(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    destino = tmp_path / "mapa.html"
    store = _BrokenStore()
    code = main(
        _command(destino),
        store=store,
        assets=_Assets(),
        collect=lambda _ano, _turno: (_bujari(),),
    )
    captured = capsys.readouterr()
    assert code == 1
    assert captured.err == _GENERIC
    assert captured.out == ""
    assert store.closed is True
    assert not destino.is_file()


def test_default_path_uses_cargo_year_and_turn(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    code = main(
        ["--ano", "2026", "--turno", "1", "--cargo", "governador", "--sem-navegador"],
        store=_Memory(),
        assets=_Assets(),
        collect=lambda _ano, _turno: (_bujari(),),
    )
    destino = tmp_path / "relatorios" / "mapa-governador-2026-turno-1.html"
    assert code == 0
    assert destino.is_file()
    assert '"numero": "13"' in destino.read_text(encoding="utf-8")


def test_cross_map_default_path_uses_the_cargo_name(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    code = main(
        ["--ano", "2026", "--turno", "1", "--cargo", "cruzamento", "--sem-navegador"],
        store=_Memory(),
        assets=_Assets(),
        collect=lambda _ano, _turno: (_bujari(),),
    )
    destino = tmp_path / "relatorios" / "mapa-cruzamento-2026-turno-1.html"
    assert code == 0
    assert destino.is_file()


def test_default_opener_uses_the_file_uri(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[str] = []
    monkeypatch.setattr(
        "eleicoes.use_cases.apresentar_mapa.webbrowser.open",
        lambda url: seen.append(url) or True,
    )
    destino = tmp_path / "mapa.html"
    code = main(
        ["--ano", "2026", "--turno", "1", "--cargo", "presidente", "--destino", str(destino)],
        store=_Memory(),
        assets=_Assets(),
        collect=lambda _ano, _turno: (_bujari(),),
    )
    assert code == 0
    assert seen == [destino.resolve().as_uri()]


def test_missing_store_uses_the_production_store(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    created: list[_Memory] = []

    def build(_env: object = None) -> _Memory:
        store = _Memory()
        created.append(store)
        return store

    monkeypatch.setattr(
        "eleicoes.composition.presidente_governador.build_cross_report_store",
        build,
    )
    destino = tmp_path / "mapa.html"
    code = main(
        _command(destino),
        assets=_Assets(),
        collect=lambda _ano, _turno: (_bujari(),),
    )
    assert code == 0
    assert len(created) == 1
    assert created[0].closed is True
    assert created[0].saves != []


def test_missing_assets_use_the_local_mesh(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[tuple[Path, Path | None]] = []
    assets = _Assets()

    class _Wrap:
        def __init__(self, raiz: Path, exterior: Path | None = None) -> None:
            seen.append((raiz, exterior))

        def load(self) -> MalhaCarregada:
            return assets.load()

    monkeypatch.setattr("eleicoes.adapters.malha_local.LocalMeshAssets", _Wrap)
    destino = tmp_path / "mapa.html"
    code = main(
        _command(destino),
        store=_Memory(),
        collect=lambda _ano, _turno: (_bujari(),),
    )
    assert code == 0
    assert seen == [(Path("downloads/malha"), Path("dados/exterior.csv"))]


def test_abroad_coordinates_reach_the_painted_cut(tmp_path: Path) -> None:
    pages: list[PaginaDoMapa] = []

    def render(page: PaginaDoMapa) -> str:
        pages.append(page)
        return ""

    code = main(
        _command(tmp_path / "mapa.html"),
        store=_Memory(),
        assets=_Assets(exterior={"29386": (-9.14, 38.72)}),
        collect=lambda _ano, _turno: (_bujari(), _place("ZZ", "29386", "Lisboa", 13, 13)),
        render=render,
    )
    assert code == 0
    [ponto] = pages[0].recorte.exterior
    assert (ponto.pintura.codigo, ponto.pintura.numero) == ("29386", "13")
    assert (ponto.lon, ponto.lat) == (-9.14, 38.72)
    assert "Lisboa" not in pages[0].recorte.sem_poligono


def test_president_page_carries_both_painted_cuts(tmp_path: Path) -> None:
    pages, code = _render_pages(tmp_path, "presidente", _Assets())
    assert code == 0
    [page] = pages
    assert set(page.recortes) == {"presidente", "governador"}
    assert page.recortes["presidente"] is page.recorte
    assert page.recortes["governador"].municipios[0].numero == "13"


def test_governor_page_reuses_its_cut_and_adds_the_president(tmp_path: Path) -> None:
    pages, code = _render_pages(tmp_path, "governador", _Assets())
    assert code == 0
    [page] = pages
    assert page.recortes["governador"] is page.recorte
    assert page.recortes["presidente"].municipios[0].numero == "22"


def test_cross_page_carries_both_painted_cuts(tmp_path: Path) -> None:
    pages, code = _render_pages(tmp_path, "cruzamento", _Assets())
    assert code == 0
    [page] = pages
    assert set(page.recortes) == {"presidente", "governador"}
    assert page.recortes["presidente"].municipios[0].numero == "22"
    assert page.recortes["governador"].municipios[0].numero == "13"


def test_extra_view_without_a_governor_mark_is_left_out(tmp_path: Path) -> None:
    only_president = {22: Marca("#112233", "data:image/png;base64,QQ==")}
    pages, code = _render_pages(tmp_path, "presidente", _Assets(marcas=only_president))
    assert code == 0
    [page] = pages
    assert set(page.recortes) == {"presidente"}
    assert page.recorte.municipios[0].numero == "22"


def test_requested_governor_without_its_mark_still_fails(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    only_president = {22: Marca("#112233", "data:image/png;base64,QQ==")}
    pages, code = _render_pages(tmp_path, "governador", _Assets(marcas=only_president))
    assert code == 1
    assert pages == []
    assert capsys.readouterr().err == "Falta a cor ou a logomarca do partido 13.\n"


def test_injected_reader_collects_without_production(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(ano: int, turno: int) -> tuple[MunicipalPlace, ...]:
        raise AssertionError((ano, turno))

    monkeypatch.setattr("eleicoes.use_cases.apresentar_mapa._production_collect", fail)
    reader = _QuietReader()
    destino = tmp_path / "mapa.html"
    code = main(
        _command(destino),
        reader=reader,
        names=_QuietNames(),
        store=_Memory(),
        assets=_Assets(),
    )
    assert code == 0
    assert reader.calls != []
    assert reader.closed is False
    assert destino.is_file()


def test_production_collect_closes_the_opened_ports(monkeypatch: pytest.MonkeyPatch) -> None:
    from eleicoes.use_cases.apresentar_mapa import _production_collect

    reader = _QuietReader()
    names = _QuietNames()
    monkeypatch.setattr("eleicoes.composition.boletim.build_boletim_reader", lambda _env: reader)
    monkeypatch.setattr("eleicoes.composition.grade.build_municipality_names", lambda _env: names)
    assert _production_collect(2026, 1) == ()
    assert reader.closed is True
    assert names.closed is True


def test_main_without_collect_uses_the_production_adapter(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reader = _QuietReader()
    names = _QuietNames()
    monkeypatch.setattr("eleicoes.composition.boletim.build_boletim_reader", lambda _env: reader)
    monkeypatch.setattr("eleicoes.composition.grade.build_municipality_names", lambda _env: names)
    destino = tmp_path / "mapa.html"
    code = main(_command(destino), store=_Memory(), assets=_Assets())
    assert code == 0
    assert reader.closed is True
    assert names.closed is True
    assert destino.is_file()


def test_presented_map_rejects_a_naive_clock(tmp_path: Path) -> None:
    with pytest.raises(InvalidStoredReportError):
        PresentedMap(tmp_path / "mapa.html", True, False, datetime(2026, 10, 1))


def test_presenter_does_not_download_the_mesh() -> None:
    root = Path(__file__).resolve().parents[2]
    text = (root / "src/eleicoes/use_cases/apresentar_mapa.py").read_text(encoding="utf-8")
    script = (root / "scripts/relatorio_mapa.py").read_text(encoding="utf-8")
    assert "requests" not in text
    assert "baixar_malha" not in text
    assert "RAIZ = Path(__file__).resolve().parents[1]" in script
    assert 'sys.path.insert(0, str(RAIZ / "src"))' in script
    assert "from eleicoes.use_cases.apresentar_mapa import main" in script
    assert "raise SystemExit(main())" in script


def test_readme_explains_the_map_command() -> None:
    root = Path(__file__).resolve().parents[2]
    text = (root / "README.md").read_text(encoding="utf-8")
    cross = text.index("## Cruzar presidente e governador")
    section = text.index("## Abrir o mapa de presidente ou de governador")
    files = text.index("## Entender os arquivos da seção")
    assert cross < section < files
    assert "uv run python scripts/baixar_malha.py" in text[section:files]
    assert "downloads/malha/marcas.json" in text[section:files]
    president = "uv run python scripts/relatorio_mapa.py --ano 2026 --turno 1 --cargo presidente"
    governor = (
        "uv run python scripts/relatorio_mapa.py --ano 2026 --turno 1 "
        "--cargo governador --sem-navegador"
    )
    assert president in text
    assert governor in text


def _render_pages(
    tmp_path: Path,
    cargo: str,
    assets: "_Assets",
) -> tuple[list[PaginaDoMapa], int]:
    pages: list[PaginaDoMapa] = []

    def render(page: PaginaDoMapa) -> str:
        pages.append(page)
        return ""

    code = main(
        ["--cargo", cargo, "--destino", str(tmp_path / "mapa.html"), "--sem-navegador"],
        store=_Memory(),
        assets=assets,
        collect=lambda _ano, _turno: (_bujari(),),
        render=render,
    )
    return pages, code


def _command(destino: Path) -> list[str]:
    return [
        "--ano",
        "2026",
        "--turno",
        "1",
        "--cargo",
        "presidente",
        "--destino",
        str(destino),
        "--sem-navegador",
    ]


def _bujari() -> MunicipalPlace:
    return _place("AC", "01007", "Bujari", 22, 13)


def _place(uf: str, codigo: str, nome: str, presidente: int, governador: int) -> MunicipalPlace:
    return MunicipalPlace(
        uf,
        codigo,
        nome,
        _tally(presidente),
        _tally(governador),
    )


def _tally(partido: int) -> CargoTally:
    return CargoTally((PartyTally(partido, 10, 0),), 0, 0)


def _row() -> dict[str, str]:
    values = (
        "04/10/2026",
        "09:00:06",
        "1",
        "12",
        "AC",
        "Bujari",
        "01007",
        "Bujari",
        "1200138",
        "Bujari",
    )
    return dict(zip(_HEADER, values, strict=True))


def _ponte() -> PonteTseIbge:
    return ponte_de_linhas((_row(),))


def _marks() -> dict[int, Marca]:
    return {
        22: Marca("#112233", "data:image/png;base64,QQ=="),
        13: Marca("#AABBCC", "data:image/png;base64,Ug=="),
    }


class _Assets:
    def __init__(
        self,
        *,
        ids_pais: frozenset[str] | None = None,
        marcas: dict[int, Marca] | None = None,
        exterior: dict[str, tuple[float, float]] | None = None,
    ) -> None:
        self._ids = frozenset({"076"}) if ids_pais is None else ids_pais
        self._marcas = _marks() if marcas is None else marcas
        self._exterior = {} if exterior is None else exterior

    def load(self) -> MalhaCarregada:
        return MalhaCarregada(
            manifesto=Manifesto("foo", "BRUF", "countries", "076"),
            municipios="{}",
            ufs="{}",
            paises="{}",
            ol_js="var ol=1;",
            ol_css=".ol{}",
            topojson_js="var topojson=1;",
            ponte=_ponte(),
            marcas=self._marcas,
            codigos_municipio=frozenset({"1200138"}),
            codigos_uf=frozenset({"12"}),
            ids_pais=self._ids,
            exterior=self._exterior,
        )


class _BrokenAssets:
    def load(self) -> MalhaCarregada:
        raise MeshMissingError("downloads/malha/manifesto.json")


class _Memory:
    def __init__(self) -> None:
        self.rows: dict[tuple[int, int], StoredCrossReport] = {}
        self.saves: list[tuple[MunicipalPlace, ...]] = []
        self.closed = False

    def load(self, ano: int, turno: int) -> StoredCrossReport | None:
        return self.rows.get((ano, turno))

    def save(self, ano: int, turno: int, places: tuple[MunicipalPlace, ...]) -> datetime:
        self.saves.append(places)
        self.rows[(ano, turno)] = StoredCrossReport(places, _MOMENT)
        return _MOMENT

    def close(self) -> None:
        self.closed = True


class _BrokenStore:
    def __init__(self) -> None:
        self.closed = False

    def load(self, _ano: int, _turno: int) -> StoredCrossReport | None:
        raise ElectionError("database unavailable")

    def save(self, _ano: int, _turno: int, _places: tuple[MunicipalPlace, ...]) -> datetime:
        raise ElectionError("database unavailable")

    def close(self) -> None:
        self.closed = True


class _QuietReader:
    def __init__(self) -> None:
        self.calls: list[tuple[int, int, str]] = []
        self.closed = False

    def present_ufs(self, ano: int, turno: int, cargo: str) -> tuple[str, ...]:
        self.calls.append((ano, turno, cargo))
        return ()

    def last_load(self, _ano: int, _turno: int) -> datetime | None:
        return None

    def close(self) -> None:
        self.closed = True


class _QuietNames:
    def __init__(self) -> None:
        self.closed = False

    def names(self, _uf: str) -> dict[int, str]:
        return {}

    def close(self) -> None:
        self.closed = True


class _OutdatedStore(_BrokenStore):
    def load(self, _ano: int, _turno: int) -> StoredCrossReport | None:
        raise SchemaOutdatedError((), "0002")


def test_outdated_schema_asks_for_the_migration(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    code = main(
        _command(tmp_path / "mapa.html"),
        store=_OutdatedStore(),
        assets=_Assets(),
        collect=lambda _ano, _turno: (_bujari(),),
    )
    assert code == 1
    assert capsys.readouterr().err == SCHEMA_OUTDATED_HINT + "\n"


def _second_round_place(votos_22: int, votos_13: int) -> MunicipalPlace:
    tally = CargoTally((PartyTally(22, votos_22, 0), PartyTally(13, votos_13, 0)), 0, 0)
    return MunicipalPlace("AC", "01007", "Bujari", tally, None)


def test_second_round_adds_the_turnos_view(tmp_path: Path) -> None:
    destino = tmp_path / "mapa.html"
    collected: list[int] = []

    def collect(_ano: int, turno: int) -> tuple[MunicipalPlace, ...]:
        collected.append(turno)
        return (_bujari(),) if turno == 1 else (_second_round_place(6, 4),)

    store = _Memory()
    code = main(
        ["--cargo", "presidente", "--destino", str(destino), "--sem-navegador"],
        store=store,
        assets=_Assets(),
        collect=collect,
        present=lambda _ano, _turno: ("AC",),
    )
    text = destino.read_text(encoding="utf-8")

    assert code == 0
    assert collected == [1, 2]
    assert store.rows[(2026, 2)].places == (_second_round_place(6, 4),)
    assert '"turnos": {"cargo": "presidente", "a": "22", "b": "13"' in text
    assert "Mapa de presidente — 2026, 1º × 2º turno" in text


def test_stored_second_round_is_reused_while_it_covers_the_same_ufs(tmp_path: Path) -> None:
    store = _Memory()
    store.save(2026, 1, (_bujari(),))
    store.save(2026, 2, (_second_round_place(6, 4),))
    collected: list[int] = []

    def collect(_ano: int, turno: int) -> tuple[MunicipalPlace, ...]:
        collected.append(turno)
        return (_second_round_place(7, 3),)

    main(
        ["--cargo", "presidente", "--destino", str(tmp_path / "a.html"), "--sem-navegador"],
        store=store,
        assets=_Assets(),
        collect=collect,
        present=lambda _ano, _turno: ("AC",),
    )
    assert collected == []

    main(
        ["--cargo", "presidente", "--destino", str(tmp_path / "b.html"), "--sem-navegador"],
        store=store,
        assets=_Assets(),
        collect=collect,
        present=lambda _ano, _turno: ("AC", "AL"),
    )
    assert collected == [2]


def test_no_second_round_keeps_the_page_without_turnos(tmp_path: Path) -> None:
    destino = tmp_path / "mapa.html"
    main(
        ["--cargo", "presidente", "--destino", str(destino), "--sem-navegador"],
        store=_Memory(),
        assets=_Assets(),
        collect=lambda _ano, _turno: (_bujari(),),
        present=lambda _ano, _turno: (),
    )

    assert '"turnos": null' in destino.read_text(encoding="utf-8")


def _reuse_run(
    tmp_path: Path,
    last_load: datetime | None,
    ufs: tuple[str, ...] = ("AC",),
) -> list[int]:
    """Grava o 2º turno em _MOMENT e roda o mapa com a marca de carga pedida."""
    store = _Memory()
    store.save(2026, 1, (_bujari(),))
    store.save(2026, 2, (_second_round_place(6, 4),))
    collected: list[int] = []
    asked: list[tuple[int, int]] = []

    def collect(_ano: int, turno: int) -> tuple[MunicipalPlace, ...]:
        collected.append(turno)
        return (_second_round_place(7, 3),)

    def load(ano: int, turno: int) -> datetime | None:
        asked.append((ano, turno))
        return last_load

    code = main(
        ["--cargo", "presidente", "--destino", str(tmp_path / "mapa.html"), "--sem-navegador"],
        store=store,
        assets=_Assets(),
        collect=collect,
        present=lambda _ano, _turno: ufs,
        last_load=load,
    )
    assert code == 0
    if collected:
        assert store.rows[(2026, 2)].places == (_second_round_place(7, 3),)
    if ufs == ("AC",):
        assert asked == [(2026, 2)]
    return collected


def test_reimport_after_the_store_was_saved_collects_again(tmp_path: Path) -> None:
    assert _reuse_run(tmp_path, _MOMENT + timedelta(minutes=5)) == [2]


def test_load_mark_older_than_the_store_keeps_the_stored_round(tmp_path: Path) -> None:
    assert _reuse_run(tmp_path, _MOMENT - timedelta(minutes=5)) == []


def test_load_mark_equal_to_the_store_collects_again(tmp_path: Path) -> None:
    assert _reuse_run(tmp_path, _MOMENT) == [2]


def test_round_without_load_marks_falls_back_to_the_uf_check(tmp_path: Path) -> None:
    assert _reuse_run(tmp_path, None) == []


def test_new_uf_collects_again_even_with_an_old_mark(tmp_path: Path) -> None:
    assert _reuse_run(tmp_path, _MOMENT - timedelta(minutes=5), ("AC", "AL")) == [2]


class _RoundReader(_QuietReader):
    def __init__(self, carga: datetime | None) -> None:
        super().__init__()
        self._carga = carga
        self.loads: list[tuple[int, int]] = []

    def present_ufs(self, ano: int, turno: int, cargo: str) -> tuple[str, ...]:
        self.calls.append((ano, turno, cargo))
        return ("AC",) if turno == 2 else ()

    def last_load(self, ano: int, turno: int) -> datetime | None:
        self.loads.append((ano, turno))
        return self._carga

    def participation(
        self, ano: int, turno: int, uf: str, cargo: str, nivel: str
    ) -> tuple[Participacao, ...]:
        self.calls.append((ano, turno, f"{uf}/{cargo}/{nivel}"))
        return (Participacao(1007, None, 100, 80 if turno == 1 else 70),)


def test_injected_reader_answers_the_load_mark(tmp_path: Path) -> None:
    store = _Memory()
    store.save(2026, 1, (_bujari(),))
    store.save(2026, 2, (_second_round_place(6, 4),))
    reader = _RoundReader(_MOMENT + timedelta(seconds=1))
    collected: list[int] = []

    def collect(_ano: int, turno: int) -> tuple[MunicipalPlace, ...]:
        collected.append(turno)
        return (_second_round_place(7, 3),)

    code = main(
        _command(tmp_path / "mapa.html"),
        reader=reader,
        store=store,
        assets=_Assets(),
        collect=collect,
    )
    assert code == 0
    assert reader.loads == [(2026, 2)]
    assert collected == [2]


def test_production_last_load_closes_the_reader(monkeypatch: pytest.MonkeyPatch) -> None:
    from eleicoes.use_cases.apresentar_mapa import _production_last_load

    reader = _RoundReader(_MOMENT)
    monkeypatch.setattr("eleicoes.composition.boletim.build_boletim_reader", lambda _env: reader)
    assert _production_last_load(2026, 2) == _MOMENT
    assert reader.loads == [(2026, 2)]
    assert reader.closed is True


def _governor_runoff_place() -> MunicipalPlace:
    presidente = CargoTally((PartyTally(22, 6, 0), PartyTally(13, 4, 0)), 0, 0)
    governador = CargoTally((PartyTally(11, 7, 0), PartyTally(10, 3, 0)), 0, 0)
    return MunicipalPlace("AC", "01007", "Bujari", presidente, governador)


def test_governor_runoff_adds_the_turnosgov_view(tmp_path: Path) -> None:
    destino = tmp_path / "mapa.html"
    primeiro = MunicipalPlace(
        "AC",
        "01007",
        "Bujari",
        _tally(22),
        CargoTally((PartyTally(10, 50, 0), PartyTally(11, 40, 0), PartyTally(45, 9, 0)), 0, 0),
    )

    main(
        ["--cargo", "presidente", "--destino", str(destino), "--sem-navegador"],
        store=_Memory(),
        assets=_Assets(),
        collect=lambda _ano, turno: (primeiro,) if turno == 1 else (_governor_runoff_place(),),
        present=lambda _ano, _turno: ("AC",),
    )
    text = destino.read_text(encoding="utf-8")

    assert '"turnosgov": {"cargo": "governador", "a": null, "b": null' in text
    assert '"finalistas": {"AC": ["10", "11"]}' in text
    assert "Mapa de governador — 2026, 1º × 2º turno" in text


def test_president_only_runoff_has_no_turnosgov(tmp_path: Path) -> None:
    destino = tmp_path / "mapa.html"
    main(
        ["--cargo", "presidente", "--destino", str(destino), "--sem-navegador"],
        store=_Memory(),
        assets=_Assets(),
        collect=lambda _ano, turno: (_bujari(),) if turno == 1 else (_second_round_place(6, 4),),
        present=lambda _ano, _turno: ("AC",),
    )

    assert '"turnosgov": null' in destino.read_text(encoding="utf-8")


def test_reader_turnout_reaches_both_rounds_of_the_comparison(tmp_path: Path) -> None:
    destino = tmp_path / "mapa.html"
    reader = _RoundReader(None)
    store = _Memory()
    store.save(2026, 1, (_bujari(),))

    main(
        _command(destino),
        reader=reader,
        store=store,
        assets=_Assets(),
        collect=lambda _ano, _turno: (_second_round_place(6, 4),),
    )
    turnos = json.loads(_pintura(destino.read_text(encoding="utf-8")))["turnos"]

    assert (2026, 1, "AC/presidente/municipio") in reader.calls
    assert (2026, 2, "AC/presidente/municipio") in reader.calls
    assert turnos["municipios"][0]["participacao"] == [100, 80, 100, 70]


def test_map_without_enough_places_has_no_estimated_scenario(tmp_path: Path) -> None:
    destino = tmp_path / "mapa.html"
    main(
        _command(destino),
        store=_Memory(),
        assets=_Assets(),
        collect=lambda _ano, turno: (_bujari(),) if turno == 1 else (_second_round_place(6, 4),),
        present=lambda _ano, _turno: ("AC",),
        participation=lambda _ano, _turno, _ufs: {},
    )
    turnos = json.loads(_pintura(destino.read_text(encoding="utf-8")))["turnos"]

    assert "estimado" not in [item["chave"] for item in turnos["cenarios"]]
    assert "participacao" not in turnos["municipios"][0]


def _pintura(html: str) -> str:
    inicio = html.index('<script type="application/json" id="pintura">') + len(
        '<script type="application/json" id="pintura">'
    )
    return html[inicio : html.index("</script>", inicio)].replace("<\\/", "</")


def test_calibration_summary_reads_the_tracked_2022_file(tmp_path: Path) -> None:
    from eleicoes.use_cases.apresentar_mapa import ler_calibracao

    resumo = ler_calibracao(Path("dados/calibracao_turnos_2022.json"))
    quebrado = tmp_path / "quebrado.json"
    quebrado.write_text("{}", encoding="utf-8")

    assert resumo is not None
    assert resumo["ano"] == 2022
    assert set(resumo["fora"]) >= {"todosa", "proporcional"}  # type: ignore[arg-type]
    assert ler_calibracao(quebrado) is None
    assert ler_calibracao(tmp_path / "ausente.json") is None
