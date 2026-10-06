"""Grid consultation. Injected readers are not closed and never open Postgres."""

from collections.abc import Mapping

import pytest

from eleicoes.composition.grade import build_municipality_names
from eleicoes.consultas.grade import grade_de_poder
from eleicoes.domain.boletim_consulta import PoderPartido
from eleicoes.domain.errors import InvalidBoletimConsultaError, InvalidNivelError, InvalidUfError
from eleicoes.domain.regiao import region_of
from eleicoes.domain.values import UF_CODES


def test_missing_municipality_name_falls_back_to_the_decimal_code() -> None:
    reader = _Reader()
    reader.present = ("AC",)
    reader.by_level[("municipio", ("AC",))] = (
        PoderPartido(1392, None, 22, 10, 0, 100),
        PoderPartido(1007, None, 22, 3, 0, 40),
    )
    names = _Names({1007: "Xapuri"})
    grade = grade_de_poder(2026, 1, "ac", "presidente", reader=reader, names=names)
    assert [(row.codigo, row.nome) for row in grade.linhas] == [
        ("1392", "1392 (AC)"),
        ("1007", "Xapuri (AC)"),
    ]
    assert names.calls == ["AC"]
    assert names.closed == 0
    assert reader.closed == 0
    assert _called(reader, "present_ufs")


def test_blank_municipality_name_also_falls_back_to_the_code() -> None:
    reader = _Reader()
    reader.present = ("AC",)
    reader.by_level[("municipio", ("AC",))] = (PoderPartido(1392, None, 22, 1, 0, 10),)
    grade = grade_de_poder(2026, 1, "AC", "presidente", reader=reader, names=_Names({1392: "  "}))
    assert grade.linhas[0].nome == "1392 (AC)"


def test_municipality_grid_lists_cities_of_every_present_uf() -> None:
    reader = _Reader()
    reader.present = ("AL", "AM", "AC")
    reader.by_level[("municipio", ("AL",))] = (PoderPartido(27855, None, 13, 4, 0, 20),)
    reader.by_level[("municipio", ("AC",))] = (PoderPartido(1392, None, 22, 7, 0, 30),)
    names = _Names({27855: "Maceió", 1392: "Rio Branco"})
    grade = grade_de_poder(2026, 1, "AC", "presidente", reader=reader, names=names)
    assert grade.uf == "AC"
    assert [(row.codigo, row.nome) for row in grade.linhas] == [
        ("27855", "Maceió (AL)"),
        ("1392", "Rio Branco (AC)"),
    ]
    assert names.calls == ["AL", "AC"]
    assert ("party_power", 2026, 1, ("AM",), "presidente", "municipio") in reader.calls
    assert reader.closed == 0


def test_state_grid_lists_acre_and_sao_paulo_without_limiting_to_the_argument() -> None:
    reader = _Reader()
    reader.present = ("SP", "AC", "AM")
    reader.by_level[("uf", ("AC",))] = (
        PoderPartido(None, None, 13, 10, 0, 100),
        PoderPartido(None, None, 22, 1, 0, 100),
    )
    reader.by_level[("uf", ("SP",))] = (PoderPartido(None, None, 13, 3, 0, 50),)
    grade = grade_de_poder(2026, 1, "rj", "presidente", nivel="uf", reader=reader)
    assert grade.uf == "RJ"
    assert [(row.codigo, row.nome) for row in grade.linhas] == [
        ("AC", "Acre"),
        ("SP", "São Paulo"),
    ]
    assert grade.colunas == (13, 22)
    assert grade.linhas[1].celulas[1].votos == 0
    assert ("present_ufs", 2026, 1, "presidente") in reader.calls
    assert ("party_power", 2026, 1, ("AM",), "presidente", "uf") in reader.calls
    assert not any(call[3] == ("RJ",) for call in reader.calls if call[0] == "party_power")
    assert reader.closed == 0


def test_region_grid_calls_each_region_once_from_its_first_uf(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    norte = region_of("AC")
    sudeste = region_of("SP")
    asked: list[tuple[str, str]] = []

    def track(
        _ano: int,
        _turno: int,
        uf: str,
        _cargo: str,
        *,
        nivel: str = "municipio",
        reader: object = None,
    ) -> tuple[PoderPartido, ...]:
        asked.append((uf, nivel))
        del reader
        if uf == norte.ufs[0]:
            return (PoderPartido(None, None, 11, 5, 0, 20),)
        if uf == sudeste.ufs[0]:
            return (PoderPartido(None, None, 11, 7, 1, 30),)
        return ()

    monkeypatch.setattr("eleicoes.consultas.grade.poder_dos_partidos", track)
    reader = _Reader()
    reader.present = ("zz", "SP", "AC")
    grade = grade_de_poder(2026, 1, "RJ", "presidente", nivel="regiao", reader=reader)
    assert [(row.codigo, row.nome) for row in grade.linhas] == [
        ("NO", "Norte"),
        ("SE", "Sudeste"),
    ]
    assert asked == [("AC", "regiao"), ("ES", "regiao")]
    assert norte.ufs[0] == "AC"
    assert sudeste.ufs[0] == "ES"
    assert ("present_ufs", 2026, 1, "presidente") in reader.calls


def test_region_without_parties_is_skipped() -> None:
    reader = _Reader()
    reader.present = ("AC", "SP")
    reader.by_level[("regiao", region_of("AC").ufs)] = (PoderPartido(None, None, 22, 5, 0, 20),)
    grade = grade_de_poder(2026, 1, "AC", "presidente", nivel="regiao", reader=reader)
    assert [row.codigo for row in grade.linhas] == ["NO"]
    assert ("party_power", 2026, 1, region_of("SP").ufs, "presidente", "regiao") in reader.calls
    assert [call[3] for call in reader.calls if call[0] == "party_power"] == [
        region_of("AC").ufs,
        region_of("SP").ufs,
    ]


def test_country_row_is_brasil_and_does_not_list_ufs() -> None:
    reader = _Reader()
    reader.present = ("AC",)
    reader.by_level[("pais", UF_CODES)] = (PoderPartido(None, None, 13, 4, 1, 9),)
    grade = grade_de_poder(2026, 1, "AC", "presidente", nivel="pais", reader=reader)
    assert grade.uf == "AC"
    assert [(row.codigo, row.nome) for row in grade.linhas] == [("BR", "Brasil")]
    assert grade.linhas[0].celulas[0].votos == 5
    assert not _called(reader, "present_ufs")
    assert ("party_power", 2026, 1, UF_CODES, "presidente", "pais") in reader.calls


def test_country_without_parties_is_empty() -> None:
    reader = _Reader()
    grade = grade_de_poder(2026, 1, "AC", "presidente", nivel="pais", reader=reader)
    assert grade.linhas == ()
    assert not _called(reader, "present_ufs")


def test_rejected_nivel_does_not_query() -> None:
    reader = _Reader()
    names = _Names()
    for nivel in ("zona", "secao", "bairro"):
        with pytest.raises(InvalidNivelError):
            grade_de_poder(2026, 1, "AC", "presidente", nivel=nivel, reader=reader, names=names)
    assert reader.calls == []
    assert names.calls == []


def test_invalid_uf_does_not_query() -> None:
    reader = _Reader()
    with pytest.raises(InvalidUfError):
        grade_de_poder(2026, 1, "XX", "presidente", reader=reader)
    assert reader.calls == []


def test_conflicting_comparecimento_and_a_place_without_a_city_are_rejected() -> None:
    reader = _Reader()
    reader.present = ("AC",)
    reader.by_level[("municipio", ("AC",))] = (
        PoderPartido(1392, None, 22, 1, 0, 10),
        PoderPartido(1392, None, 13, 1, 0, 11),
    )
    with pytest.raises(InvalidBoletimConsultaError):
        grade_de_poder(2026, 1, "AC", "presidente", reader=reader, names=_Names())
    reader.by_level[("municipio", ("AC",))] = (PoderPartido(None, None, 13, 1, 0, 10),)
    with pytest.raises(InvalidBoletimConsultaError):
        grade_de_poder(2026, 1, "AC", "presidente", reader=reader, names=_Names())


def test_composition_closes_omitted_readers_only(monkeypatch: pytest.MonkeyPatch) -> None:
    events: list[str] = []

    class Reader:
        def present_ufs(self, _ano: int, _turno: int, _cargo: str) -> tuple[str, ...]:
            return ()

        def party_power(
            self,
            _ano: int,
            _turno: int,
            _ufs: tuple[str, ...],
            _cargo: str,
            _nivel: str,
        ) -> tuple[PoderPartido, ...]:
            events.append("party")
            return ()

        def close(self) -> None:
            events.append("reader-close")

    class Names:
        def names(self, uf: str) -> dict[int, str]:
            events.append(f"names:{uf}")
            return {}

        def close(self) -> None:
            events.append("names-close")

    monkeypatch.setattr("eleicoes.consultas.grade.load_dotenv", lambda: events.append("dotenv"))
    monkeypatch.setattr("eleicoes.consultas.grade.build_boletim_reader", lambda _env: Reader())
    monkeypatch.setattr("eleicoes.consultas.grade.build_municipality_names", lambda _env: Names())

    grade_de_poder(2026, 1, "AC", "presidente")
    assert events[-2:] == ["names-close", "reader-close"]

    injected = _Reader()
    given = _Names()
    grade_de_poder(2026, 1, "AC", "presidente", reader=injected, names=given)
    assert injected.closed == 0
    assert given.closed == 0

    passed = _Reader()
    grade_de_poder(2026, 1, "AC", "presidente", reader=passed)
    assert passed.closed == 0
    assert events[-1] == "names-close"

    given = _Names()
    grade_de_poder(2026, 1, "AC", "presidente", names=given)
    assert given.closed == 0
    assert events[-1] == "reader-close"


def test_failure_closes_only_the_readers_that_were_opened(monkeypatch: pytest.MonkeyPatch) -> None:
    events: list[str] = []

    class Reader:
        def present_ufs(self, _ano: int, _turno: int, _cargo: str) -> tuple[str, ...]:
            return ("AC",)

        def party_power(
            self,
            _ano: int,
            _turno: int,
            _ufs: tuple[str, ...],
            _cargo: str,
            _nivel: str,
        ) -> tuple[PoderPartido, ...]:
            raise RuntimeError("boom")

        def close(self) -> None:
            events.append("reader-close")

    class Names:
        def names(self, _uf: str) -> dict[int, str]:
            return {}

        def close(self) -> None:
            events.append("names-close")

    monkeypatch.setattr("eleicoes.consultas.grade.load_dotenv", lambda: None)
    monkeypatch.setattr("eleicoes.consultas.grade.build_boletim_reader", lambda _env: Reader())
    monkeypatch.setattr("eleicoes.consultas.grade.build_municipality_names", lambda _env: Names())
    with pytest.raises(RuntimeError):
        grade_de_poder(2026, 1, "AC", "presidente")
    assert events == ["names-close", "reader-close"]


def test_other_levels_do_not_build_municipality_names(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(_env: object) -> object:
        raise AssertionError("names")

    monkeypatch.setattr("eleicoes.consultas.grade.build_municipality_names", boom)
    reader = _Reader()
    grade_de_poder(2026, 1, "AC", "presidente", nivel="uf", reader=reader)
    grade_de_poder(2026, 1, "AC", "presidente", nivel="regiao", reader=reader)
    grade_de_poder(2026, 1, "AC", "presidente", nivel="pais", reader=reader)


def test_municipality_names_follow_the_published_port(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, str] = {}

    def connect(env: object) -> _Link:
        assert isinstance(env, dict)
        seen.update(env)
        return _Link()

    monkeypatch.setattr("eleicoes.composition.grade.connect_postgres", connect)
    monkeypatch.setattr("eleicoes.composition.correspondencia._resolves", lambda _host: False)
    names = build_municipality_names(
        {
            "POSTGRES_HOST": "postgres",
            "POSTGRES_PORT": "5432",
            "POSTGRES_PUBLISH_PORT": "25432",
            "POSTGRES_DB": "eleicoes",
        }
    )
    assert names.names("AC") == {}
    names.close()
    assert seen["POSTGRES_HOST"] == "127.0.0.1"
    assert seen["POSTGRES_PORT"] == "25432"


def test_rejected_nivel_does_not_open_a_reader(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(_env: object) -> object:
        raise AssertionError("opened")

    monkeypatch.setattr("eleicoes.consultas.grade.build_boletim_reader", boom)
    with pytest.raises(InvalidNivelError):
        grade_de_poder(2026, 1, "AC", "presidente", nivel="zona")


class _Reader:
    def __init__(self) -> None:
        self.calls: list[tuple[object, ...]] = []
        self.by_level: dict[tuple[str, tuple[str, ...]], tuple[PoderPartido, ...]] = {}
        self.present: tuple[str, ...] = ()
        self.closed = 0

    def present_ufs(self, ano: int, turno: int, cargo: str) -> tuple[str, ...]:
        self.calls.append(("present_ufs", ano, turno, cargo))
        return self.present

    def party_power(
        self,
        ano: int,
        turno: int,
        ufs: tuple[str, ...],
        cargo: str,
        nivel: str,
    ) -> tuple[PoderPartido, ...]:
        self.calls.append(("party_power", ano, turno, ufs, cargo, nivel))
        return self.by_level.get((nivel, ufs), ())

    def close(self) -> None:
        self.closed += 1


class _Names:
    def __init__(self, found: Mapping[int, str] | None = None) -> None:
        self.found = dict(found or {})
        self.calls: list[str] = []
        self.closed = 0

    def names(self, uf: str) -> Mapping[int, str]:
        self.calls.append(uf)
        return self.found

    def close(self) -> None:
        self.closed += 1


def _called(reader: _Reader, name: str) -> bool:
    return any(call[0] == name for call in reader.calls)


class _Cursor:
    def execute(self, _query: str, _params: object = None) -> None:
        return None

    def fetchall(self) -> list[tuple[object, ...]]:
        return []

    def __enter__(self) -> "_Cursor":
        return self

    def __exit__(self, *_args: object) -> None:
        return None


class _Link:
    def cursor(self) -> _Cursor:
        return _Cursor()

    def transaction(self) -> "_Link":
        return self

    def close(self) -> None:
        return None

    def __enter__(self) -> "_Link":
        return self

    def __exit__(self, *_args: object) -> None:
        return None
