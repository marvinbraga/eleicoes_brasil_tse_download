"""Use case and command line of the regions and size report. No database."""

from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path

import pytest

from eleicoes.domain.boletim_consulta import Participacao
from eleicoes.domain.errors import ElectionError, SchemaOutdatedError
from eleicoes.domain.mapa import Marca, MeshMissingError
from eleicoes.domain.presidente_governador import CargoTally, MunicipalPlace, PartyTally
from eleicoes.ports.relatorio_presidente_governador import StoredCrossReport
from eleicoes.use_cases import apresentar_regioes_porte
from eleicoes.use_cases.apresentar_regioes_porte import (
    PresentRegionsAndSize,
    StoredRoundMissingError,
    main,
)

_MOMENTO = datetime(2026, 10, 26, 22, 0, tzinfo=UTC)


def _place(uf: str, codigo: str, votos: dict[int, int]) -> MunicipalPlace:
    parties = tuple(PartyTally(numero, total, 0) for numero, total in votos.items() if total)
    return MunicipalPlace(uf, codigo, f"M{codigo} ({uf})", CargoTally(parties, 1, 1), None)


class _Store:
    def __init__(self, segundo: bool = True, segundo_votos: dict[int, int] | None = None) -> None:
        votos = {13: 600, 22: 400} if segundo_votos is None else segundo_votos
        self._rounds: dict[int, tuple[MunicipalPlace, ...]] = {
            1: (
                _place("AC", "1007", {13: 400, 22: 400, 30: 200}),
                _place("RS", "88536", {13: 100, 22: 300}),
                _place("SE", "31054", {13: 50, 22: 50}),
            ),
        }
        if segundo:
            self._rounds[2] = (
                _place("AC", "1007", votos),
                _place("RS", "88536", segundo_votos or {13: 150, 22: 250}),
            )

    def load(self, ano: int, turno: int) -> StoredCrossReport | None:
        assert ano == 2026
        places = self._rounds.get(turno)
        return None if places is None else StoredCrossReport(places, _MOMENTO)


class _Reader:
    def __init__(self, fail: Exception | None = None) -> None:
        self._fail = fail
        self.calls: list[tuple[int, int, str, str, str]] = []
        self.closed = 0

    def participation(
        self, ano: int, turno: int, uf: str, cargo: str, nivel: str
    ) -> tuple[Participacao, ...]:
        self.calls.append((ano, turno, uf, cargo, nivel))
        if self._fail is not None:
            raise self._fail
        municipio = 1007 if uf == "AC" else 88536
        aptos = 9_000 if uf == "AC" else 300_000
        return (Participacao(municipio, None, aptos, aptos - 100),)

    def present_ufs(self, ano: int, turno: int, cargo: str) -> tuple[str, ...]:
        assert (ano, turno, cargo) == (2026, 2, "presidente")
        return ("AC", "RS", "SE")


def _marks() -> Mapping[int, Marca]:
    return {13: Marca("#e15759", "", "PT")}


def test_execute_reads_turnout_once_per_state_and_writes_the_page(tmp_path: Path) -> None:
    reader = _Reader()
    opened: list[Path] = []
    use_case = PresentRegionsAndSize(
        _Store(),
        reader,  # type: ignore[arg-type]
        _marks,
        lambda path: opened.append(path) or True,
        clock=lambda: _MOMENTO,
    )
    destino = tmp_path / "sub" / "regioes.html"

    report = use_case.execute(2026, destino)
    use_case.execute(2026, destino)

    assert [call[2] for call in reader.calls] == ["AC", "RS"]
    assert all(call[1] == 1 and call[4] == "municipio" for call in reader.calls)
    assert report.opened
    assert opened == [destino, destino]
    html = destino.read_text(encoding="utf-8")
    assert "13 PT" in html
    leitura = report.leitura
    assert leitura.fora_do_relatorio == ("SE",)
    assert [linha.municipios for linha in leitura.portes] == [1, 0, 0, 1, 0]


def test_missing_round_is_an_error(tmp_path: Path) -> None:
    use_case = PresentRegionsAndSize(
        _Store(segundo=False),
        _Reader(),  # type: ignore[arg-type]
        _marks,
        lambda _path: True,
    )
    with pytest.raises(StoredRoundMissingError) as error:
        use_case.execute(2026, tmp_path / "x.html")
    assert error.value.turno == 2


def _run(tmp_path: Path, store: _Store, reader: _Reader, **extra: object) -> int:
    return main(
        ["--ano", "2026", "--destino", str(tmp_path / "r.html"), "--sem-navegador"],
        store=store,
        reader=reader,  # type: ignore[arg-type]
        clock=lambda: _MOMENTO,
        **extra,  # type: ignore[arg-type]
    )


def test_main_prints_groups(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert _run(tmp_path, _Store(), _Reader(), marks=_marks) == 0

    out = capsys.readouterr().out
    assert "Regiões e porte gravados em" in out
    assert "Sem 2º turno no relatório gravado:" in out
    assert "fora do relatório gravado: SE." in out
    assert "Norte (1): 13 60,00%" in out
    assert "virada +" in out
    assert (tmp_path / "r.html").is_file()


def test_main_without_marks_uses_numbers(tmp_path: Path) -> None:
    assert _run(tmp_path, _Store(), _Reader()) == 0
    assert "22 × 13" in (tmp_path / "r.html").read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("store", "reader", "message"),
    [
        (_Store(segundo=False), _Reader(), "Não há 2º turno de presidente gravado para 2026"),
        (_Store(segundo_votos={13: 10}), _Reader(), "não tem dois finalistas"),
        (_Store(), _Reader(MeshMissingError("downloads/malha/marcas.json")), "Falta downloads"),
        (_Store(), _Reader(SchemaOutdatedError((), "x")), "esquema do banco"),
        (_Store(), _Reader(ElectionError("x")), "Não foi possível apresentar"),
    ],
)
def test_main_maps_errors_to_messages(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    store: _Store,
    reader: _Reader,
    message: str,
) -> None:
    assert _run(tmp_path, store, reader) == 1
    assert message in capsys.readouterr().err


def test_default_destination_and_openers() -> None:
    args = apresentar_regioes_porte._parser().parse_args(["--ano", "2022"])
    assert apresentar_regioes_porte._destino(args) == Path("relatorios/regioes-porte-2022.html")
    assert apresentar_regioes_porte._choose_opener(args, None) is (
        apresentar_regioes_porte._open_browser
    )
    quiet = apresentar_regioes_porte._parser().parse_args(["--sem-navegador"])
    assert apresentar_regioes_porte._choose_opener(quiet, None) is (
        apresentar_regioes_porte._skip_browser
    )
    assert apresentar_regioes_porte._skip_browser(Path("x"))
