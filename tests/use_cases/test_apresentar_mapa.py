"""The map command paints the leading party and reuses stored municipal votes."""

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from eleicoes.domain.errors import ElectionError, InvalidStoredReportError
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

    def close(self) -> None:
        self.closed = True


class _QuietNames:
    def __init__(self) -> None:
        self.closed = False

    def names(self, _uf: str) -> dict[int, str]:
        return {}

    def close(self) -> None:
        self.closed = True
