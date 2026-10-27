"""Use case and CLI of "Como votou cada estado". No database, mesh or index on disk."""

from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path

import pytest

from eleicoes.adapters.indice_urnas_secoes import UrnaIndexMismatchError, UrnaIndexMissingError
from eleicoes.domain.errors import ElectionError, SchemaOutdatedError
from eleicoes.domain.mapa import Marca, MeshMissingError
from eleicoes.domain.presidente_governador import CargoTally, MunicipalPlace, PartyTally
from eleicoes.domain.votos_por_estado import ContagemIndice, SecoesIndice
from eleicoes.ports.relatorio_presidente_governador import StoredCrossReport
from eleicoes.use_cases import apresentar_votos_por_estado
from eleicoes.use_cases.apresentar_votos_por_estado import CountSections, PresentStates, main

_AGORA = datetime(2026, 10, 26, 22, 0, tzinfo=UTC)
_DADOS = datetime(2026, 10, 26, 21, 0, tzinfo=UTC)
_MARCAS = {
    13: Marca("#e15759", "data:image/png;base64,AAAA", "PT"),
    22: Marca("#4e79a7", "data:image/png;base64,BBBB", "PL"),
}


def _place(uf: str, codigo: str, votos: dict[int, int]) -> MunicipalPlace:
    parties = tuple(PartyTally(numero, total, 0) for numero, total in votos.items())
    return MunicipalPlace(uf, codigo, f"{codigo} ({uf})", CargoTally(parties, 0, 0), None)


class _Store:
    def __init__(self, places: tuple[MunicipalPlace, ...] | None = None, fail: bool = False):
        self._places = places
        self._fail = fail
        self.asked: list[tuple[int, int]] = []
        self.closed = 0

    def load(self, ano: int, turno: int) -> StoredCrossReport | None:
        self.asked.append((ano, turno))
        if self._fail:
            raise SchemaOutdatedError(("a",), "b")
        if self._places is None:
            return None
        return StoredCrossReport(self._places, _DADOS)

    def save(self, _ano: int, _turno: int, _places: tuple[MunicipalPlace, ...]) -> datetime:
        raise AssertionError("the report never writes to the store")

    def close(self) -> None:
        self.closed += 1


def _places() -> tuple[MunicipalPlace, ...]:
    return (
        _place("PI", "1", {13: 700, 22: 300}),
        _place("SP", "2", {13: 400, 22: 600}),
        _place("RJ", "3", {13: 300, 22: 600}),
    )


def _count(ano: int) -> ContagemIndice:
    assert ano == 2026
    return {(1, "PI"): SecoesIndice(4, 4), (2, "PI"): SecoesIndice(4, 3)}


def _marks() -> Mapping[int, Marca]:
    return _MARCAS


def _clock() -> datetime:
    return _AGORA


def test_execute_writes_the_page_and_opens_it(tmp_path: Path) -> None:
    opened: list[Path] = []
    store = _Store(_places())

    def opener(path: Path) -> bool:
        opened.append(path)
        return True

    destino = tmp_path / "saida" / "estados.html"
    report = PresentStates(store, _marks, _count, opener, clock=_clock).execute(2026, 2, destino)
    assert report.opened
    assert opened == [destino]
    assert store.asked == [(2026, 2)]
    assert (report.votos.vitorias_a, report.votos.vitorias_b) == (1, 2)
    html = destino.read_text(encoding="utf-8")
    assert "Como votou cada estado" in html
    assert "com 75,00% das urnas" in html
    assert "26/10/2026" in html


@pytest.mark.parametrize("places", [None, ()])
def test_execute_without_stored_votes_fails(tmp_path: Path, places: tuple[()] | None) -> None:
    use_case = PresentStates(_Store(places), _marks, _count, lambda _p: True)
    with pytest.raises(ElectionError):
        use_case.execute(2026, 2, tmp_path / "x.html")


def test_main_prints_wins_brasil_coverage_and_missing_states(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    store = _Store(_places())
    destino = tmp_path / "estados.html"
    code = main(
        ["--turno", "2", "--destino", str(destino), "--sem-navegador"],
        store=store,
        load_marks=_marks,
        count_sections=_count,
        clock=_clock,
    )
    out = capsys.readouterr().out
    assert code == 0
    assert store.closed == 1
    assert destino.is_file()
    assert "13 venceu em 1 estados; 22, em 2." in out
    assert "Brasil: 13 48,28% × 22 51,72%, diferença de 100 votos." in out
    assert "Urnas com boletim: 3 de 4 (75,00%)." in out
    assert "Ainda sem 2º turno: AC" in out


def test_main_without_expected_sections_says_so(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code = main(
        ["--turno", "1", "--destino", str(tmp_path / "e.html")],
        store=_Store(_places()),
        load_marks=_marks,
        count_sections=lambda _ano: {},
        open_report=lambda _p: False,
        clock=_clock,
    )
    assert code == 0
    assert "esperadas: desconhecidas" in capsys.readouterr().out


def _failing(error: Exception) -> CountSections:
    def count(_ano: int) -> ContagemIndice:
        raise error

    return count


@pytest.mark.parametrize(
    ("store", "count", "message"),
    [
        (_Store(None), _count, "Não há votos de presidente gravados para o 2º turno de 2026."),
        (_Store((_place("PI", "1", {13: 1}),)), _count, "não têm dois candidatos"),
        (_Store(_places()), _failing(UrnaIndexMissingError(Path("i.csv"))), "Falta i.csv."),
        (_Store(_places()), _failing(UrnaIndexMismatchError(Path("i.csv"))), "não é o do índice"),
        (_Store(_places()), _failing(MeshMissingError("m.json")), "Falta m.json."),
        (_Store(_places(), fail=True), _count, "make migrate"),
        (_Store(_places()), _failing(ElectionError("x")), "Não foi possível apresentar"),
    ],
)
def test_main_reports_failures(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    store: _Store,
    count: CountSections,
    message: str,
) -> None:
    code = main(
        ["--destino", str(tmp_path / "e.html"), "--sem-navegador"],
        store=store,
        load_marks=_marks,
        count_sections=count,
    )
    assert code == 1
    assert message in capsys.readouterr().err
    assert store.closed == 1


def test_main_names_a_missing_mark(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code = main(
        ["--destino", str(tmp_path / "e.html"), "--sem-navegador"],
        store=_Store(_places()),
        load_marks=lambda: {13: _MARCAS[13]},
        count_sections=_count,
    )
    assert code == 1
    assert "Falta a cor ou a logomarca do partido 22." in capsys.readouterr().err


def test_default_destination_and_production_wiring(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = _Store(_places())
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(apresentar_votos_por_estado, "_production_store", lambda: store)
    monkeypatch.setattr(apresentar_votos_por_estado, "_production_marks", _marks)
    monkeypatch.setattr(apresentar_votos_por_estado, "_production_count", _count)
    opened: list[Path] = []
    monkeypatch.setattr(apresentar_votos_por_estado, "_open_browser", opened.append)
    assert main(["--ano", "2026", "--turno", "1"]) == 0
    assert (tmp_path / "relatorios" / "estados-2026-turno-1.html").is_file()
    assert opened == [Path("relatorios") / "estados-2026-turno-1.html"]
    assert store.closed == 1
