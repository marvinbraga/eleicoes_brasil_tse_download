"""Public boletim consultations. An injected reader never opens Postgres."""

from collections.abc import Sequence

import pytest

from eleicoes.composition.boletim import build_boletim_reader
from eleicoes.consultas.boletim import (
    brancos_e_nulos,
    comparar,
    indicios,
    participacao,
    poder_dos_partidos,
    primeiro_colocado,
    ranking_municipios,
    resumo_do_cargo,
    votos_da_secao,
    votos_por_zona,
)
from eleicoes.domain.boletim_consulta import (
    BrancosNulos,
    Comparativo,
    LinhaVoto,
    Participacao,
    PoderPartido,
    PrimeiroColocado,
    SectionProjection,
    TotalCargo,
    VotosMunicipio,
    VotosZona,
)
from eleicoes.domain.errors import InvalidNivelError, InvalidUfError


def test_injected_reader_answers_without_postgres(monkeypatch: pytest.MonkeyPatch) -> None:
    events: list[str] = []
    monkeypatch.setattr(
        "eleicoes.consultas.boletim.load_dotenv",
        lambda: events.append("dotenv"),
    )
    reader = _Reader()
    reader.total_rows = (TotalCargo("nominal", 22, 22, 3),)
    reader.municipality_rows = (VotosMunicipio(2, 1, 4), VotosMunicipio(1, 5, 9))
    reader.comparison_rows = (Comparativo(1, None, None, 5, 0, 9),)
    reader.line_rows = (LinhaVoto("presidente", 1, "nulo", None, None, 1),)
    reader.zone_rows = (VotosZona(4, 2, 8),)
    reader.sections = (SectionProjection(1, 1, 1, 10, 10),)

    assert resumo_do_cargo(2026, 1, "AC", "presidente", reader=reader)[0].quantidade == 3
    ranking = ranking_municipios(2026, 1, "ac", "presidente", 22, ordem="menos", reader=reader)
    assert [item.municipio for item in ranking] == [2, 1]
    compared = comparar(2026, 1, "AC", "presidente", 22, 13, reader=reader)
    assert compared[0].votos_segundo == 0
    assert votos_da_secao(2026, 1, "AC", 1, 1, 1, reader=reader) == reader.line_rows
    assert votos_por_zona(2026, 1, "AC", 1, "presidente", 22, reader=reader)[0].zona == 4
    assert indicios(2026, 1, "AC", "presidente", reader=reader) == ()
    assert ("close",) not in reader.calls
    assert events == []


def test_invalid_uf_raises_before_the_injected_reader_is_used() -> None:
    reader = _Reader()
    with pytest.raises(InvalidUfError):
        resumo_do_cargo(2026, 1, "XX", "presidente", reader=reader)
    assert reader.calls == []


def test_omitted_reader_loads_the_environment_and_closes_on_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[object] = []

    class Reader:
        def totals(self, ano: int, turno: int, uf: str, cargo: str) -> tuple[TotalCargo, ...]:
            events.append(("totals", ano, turno, uf, cargo))
            raise RuntimeError("boom")

        def close(self) -> None:
            events.append("close")

    monkeypatch.setattr(
        "eleicoes.consultas.boletim.load_dotenv",
        lambda: events.append("dotenv"),
    )
    monkeypatch.setattr(
        "eleicoes.consultas.boletim.build_boletim_reader",
        lambda _env: Reader(),
    )
    with pytest.raises(RuntimeError):
        resumo_do_cargo(2026, 1, "AC", "presidente")
    assert events == ["dotenv", ("totals", 2026, 1, "AC", "presidente"), "close"]


def test_invalid_uf_still_closes_the_reader_it_opened(monkeypatch: pytest.MonkeyPatch) -> None:
    events: list[str] = []

    class Reader:
        def close(self) -> None:
            events.append("close")

    monkeypatch.setattr(
        "eleicoes.consultas.boletim.load_dotenv",
        lambda: events.append("dotenv"),
    )
    monkeypatch.setattr(
        "eleicoes.consultas.boletim.build_boletim_reader",
        lambda _env: Reader(),
    )
    with pytest.raises(InvalidUfError):
        ranking_municipios(2026, 1, "XX", "presidente", 22)
    assert events == ["dotenv", "close"]


def test_omitted_reader_closes_after_a_successful_read(monkeypatch: pytest.MonkeyPatch) -> None:
    events: list[object] = []

    class Reader:
        def totals(self, ano: int, turno: int, uf: str, cargo: str) -> tuple[TotalCargo, ...]:
            events.append(("totals", ano, turno, uf, cargo))
            return (TotalCargo("nominal", 22, 22, 3),)

        def close(self) -> None:
            events.append("close")

    monkeypatch.setattr("eleicoes.consultas.boletim.load_dotenv", lambda: events.append("dotenv"))
    monkeypatch.setattr(
        "eleicoes.consultas.boletim.build_boletim_reader",
        lambda _env: Reader(),
    )
    found = resumo_do_cargo(2026, 1, "AC", "presidente")
    assert found[0].quantidade == 3
    assert events == ["dotenv", ("totals", 2026, 1, "AC", "presidente"), "close"]


def test_party_power_forwards_nivel_to_the_injected_reader() -> None:
    reader = _Reader()
    reader.party_rows = (
        PoderPartido(1, 2, 22, 1, 0, 10),
        PoderPartido(1, 2, 15, 4, 1, 10),
    )
    found = poder_dos_partidos(2026, 1, "ac", "senador", nivel="zona", reader=reader)
    assert [(item.partido, item.votos) for item in found] == [(15, 5), (22, 1)]
    assert reader.calls == [("party_power", 2026, 1, ("AC",), "senador", "zona")]
    assert ("close",) not in reader.calls


def test_omitted_reader_closes_after_party_power(monkeypatch: pytest.MonkeyPatch) -> None:
    events: list[object] = []

    class Reader:
        def party_power(
            self, ano: int, turno: int, ufs: tuple[str, ...], cargo: str, nivel: str
        ) -> tuple[PoderPartido, ...]:
            events.append(("party_power", ano, turno, ufs, cargo, nivel))
            return (PoderPartido(1, None, 22, 4, 1, 9),)

        def close(self) -> None:
            events.append("close")

    monkeypatch.setattr("eleicoes.consultas.boletim.load_dotenv", lambda: events.append("dotenv"))
    monkeypatch.setattr(
        "eleicoes.consultas.boletim.build_boletim_reader",
        lambda _env: Reader(),
    )
    found = poder_dos_partidos(2026, 1, "AC", "presidente")
    assert found[0].votos == 5
    assert found[0].zona is None
    assert events == [
        "dotenv",
        ("party_power", 2026, 1, ("AC",), "presidente", "municipio"),
        "close",
    ]


def test_party_power_uf_forwards_and_closes(monkeypatch: pytest.MonkeyPatch) -> None:
    events: list[object] = []

    class Reader:
        def party_power(
            self, ano: int, turno: int, ufs: tuple[str, ...], cargo: str, nivel: str
        ) -> tuple[PoderPartido, ...]:
            events.append(("party_power", ano, turno, ufs, cargo, nivel))
            return (PoderPartido(None, None, 22, 4, 1, 9),)

        def close(self) -> None:
            events.append("close")

    monkeypatch.setattr("eleicoes.consultas.boletim.load_dotenv", lambda: events.append("dotenv"))
    monkeypatch.setattr(
        "eleicoes.consultas.boletim.build_boletim_reader",
        lambda _env: Reader(),
    )
    found = poder_dos_partidos(2026, 1, "AC", "presidente", nivel="uf")
    assert found[0].partido == 22
    assert found[0].municipio is None
    assert found[0].regiao is None
    assert events == ["dotenv", ("party_power", 2026, 1, ("AC",), "presidente", "uf"), "close"]


def test_participation_rejects_uf_before_using_the_reader() -> None:
    reader = _Reader()
    with pytest.raises(InvalidNivelError):
        participacao(2026, 1, "AC", "presidente", nivel="uf", reader=reader)
    with pytest.raises(InvalidNivelError):
        brancos_e_nulos(2026, 1, "AC", "presidente", nivel="regiao", reader=reader)
    with pytest.raises(InvalidNivelError):
        primeiro_colocado(2026, 1, "AC", "presidente", nivel="pais", reader=reader)
    assert reader.calls == []


def test_new_consultations_forward_nivel_and_do_not_close() -> None:
    reader = _Reader()
    reader.participation_rows = (Participacao(1, 2, 10, 7),)
    reader.blank_rows = (
        BrancosNulos(1, 2, 0, 1, 7),
        BrancosNulos(1, 1, 3, 1, 7),
    )
    reader.leader_rows = (
        PrimeiroColocado(1, 2, 22, 22, 4, None, None, None, 7),
        PrimeiroColocado(1, 1, 13, 13, 6, 22, 22, 1, 7),
    )
    turnout = participacao(2026, 1, "ac", "presidente", nivel="zona", reader=reader)
    blanks = brancos_e_nulos(2026, 1, "ac", "presidente", nivel="zona", reader=reader)
    leaders = primeiro_colocado(2026, 1, "ac", "presidente", nivel="zona", reader=reader)
    assert turnout[0].abstencao == 3
    assert [(row.zona, row.votos) for row in blanks] == [(1, 4), (2, 1)]
    assert [row.numero for row in leaders] == [13, 22]
    assert reader.calls == [
        ("participation", 2026, 1, "AC", "presidente", "zona"),
        ("blank_and_null", 2026, 1, "AC", "presidente", "zona"),
        ("leading_candidate", 2026, 1, "AC", "presidente", "zona"),
    ]
    assert ("close",) not in reader.calls


def test_omitted_reader_closes_after_each_new_consultation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[object] = []

    class Reader:
        def participation(
            self, ano: int, turno: int, uf: str, cargo: str, nivel: str
        ) -> tuple[Participacao, ...]:
            events.append(("participation", ano, turno, uf, cargo, nivel))
            return (Participacao(1, None, 10, 8),)

        def blank_and_null(
            self, ano: int, turno: int, uf: str, cargo: str, nivel: str
        ) -> tuple[BrancosNulos, ...]:
            events.append(("blank_and_null", ano, turno, uf, cargo, nivel))
            return (BrancosNulos(1, None, 1, 2, 8),)

        def leading_candidate(
            self, ano: int, turno: int, uf: str, cargo: str, nivel: str
        ) -> tuple[PrimeiroColocado, ...]:
            events.append(("leading_candidate", ano, turno, uf, cargo, nivel))
            return (PrimeiroColocado(1, None, 22, 22, 5, None, None, None, 9),)

        def close(self) -> None:
            events.append("close")

    monkeypatch.setattr("eleicoes.consultas.boletim.load_dotenv", lambda: events.append("dotenv"))
    monkeypatch.setattr(
        "eleicoes.consultas.boletim.build_boletim_reader",
        lambda _env: Reader(),
    )
    turnout = participacao(2026, 1, "AC", "presidente")
    blanks = brancos_e_nulos(2026, 1, "AC", "presidente")
    leaders = primeiro_colocado(2026, 1, "AC", "presidente")
    assert turnout[0].abstencao == 2
    assert blanks[0].votos == 3
    assert leaders[0].numero == 22
    assert leaders[0].zona is None
    assert events == [
        "dotenv",
        ("participation", 2026, 1, "AC", "presidente", "municipio"),
        "close",
        "dotenv",
        ("blank_and_null", 2026, 1, "AC", "presidente", "municipio"),
        "close",
        "dotenv",
        ("leading_candidate", 2026, 1, "AC", "presidente", "municipio"),
        "close",
    ]


def test_compose_host_uses_the_published_port_outside_the_stack(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: dict[str, str] = {}

    def connect(env: object) -> _Connection:
        assert isinstance(env, dict)
        seen.update(env)
        return _Connection()

    monkeypatch.setattr("eleicoes.composition.boletim.connect_postgres", connect)
    monkeypatch.setattr("eleicoes.composition.correspondencia._resolves", lambda _host: False)
    reader = build_boletim_reader(
        {
            "POSTGRES_HOST": "postgres",
            "POSTGRES_PORT": "5432",
            "POSTGRES_PUBLISH_PORT": "25432",
            "POSTGRES_DB": "eleicoes",
        }
    )
    assert reader.totals(2026, 1, "AC", "presidente") == ()
    reader.close()
    assert seen["POSTGRES_HOST"] == "127.0.0.1"
    assert seen["POSTGRES_PORT"] == "25432"


class _Reader:
    def __init__(self) -> None:
        self.calls: list[tuple[object, ...]] = []
        self.total_rows: tuple[TotalCargo, ...] = ()
        self.municipality_rows: tuple[VotosMunicipio, ...] = ()
        self.comparison_rows: tuple[Comparativo, ...] = ()
        self.party_rows: tuple[PoderPartido, ...] = ()
        self.participation_rows: tuple[Participacao, ...] = ()
        self.blank_rows: tuple[BrancosNulos, ...] = ()
        self.leader_rows: tuple[PrimeiroColocado, ...] = ()
        self.line_rows: tuple[LinhaVoto, ...] = ()
        self.zone_rows: tuple[VotosZona, ...] = ()
        self.sections: tuple[SectionProjection, ...] = ()

    def totals(self, ano: int, turno: int, uf: str, cargo: str) -> tuple[TotalCargo, ...]:
        self.calls.append(("totals", ano, turno, uf, cargo))
        return self.total_rows

    def municipalities(
        self, ano: int, turno: int, uf: str, cargo: str, numero: int
    ) -> tuple[VotosMunicipio, ...]:
        self.calls.append(("municipalities", ano, turno, uf, cargo, numero))
        return self.municipality_rows

    def comparison(
        self,
        ano: int,
        turno: int,
        uf: str,
        cargo: str,
        primeiro: int,
        segundo: int,
        nivel: str,
    ) -> tuple[Comparativo, ...]:
        self.calls.append(("comparison", ano, turno, uf, cargo, primeiro, segundo, nivel))
        return self.comparison_rows

    def party_power(
        self, ano: int, turno: int, ufs: tuple[str, ...], cargo: str, nivel: str
    ) -> tuple[PoderPartido, ...]:
        self.calls.append(("party_power", ano, turno, ufs, cargo, nivel))
        return self.party_rows

    def participation(
        self, ano: int, turno: int, uf: str, cargo: str, nivel: str
    ) -> tuple[Participacao, ...]:
        self.calls.append(("participation", ano, turno, uf, cargo, nivel))
        return self.participation_rows

    def blank_and_null(
        self, ano: int, turno: int, uf: str, cargo: str, nivel: str
    ) -> tuple[BrancosNulos, ...]:
        self.calls.append(("blank_and_null", ano, turno, uf, cargo, nivel))
        return self.blank_rows

    def leading_candidate(
        self, ano: int, turno: int, uf: str, cargo: str, nivel: str
    ) -> tuple[PrimeiroColocado, ...]:
        self.calls.append(("leading_candidate", ano, turno, uf, cargo, nivel))
        return self.leader_rows

    def section_lines(
        self, ano: int, turno: int, uf: str, municipio: int, zona: int, secao: int
    ) -> tuple[LinhaVoto, ...]:
        self.calls.append(("section_lines", ano, turno, uf, municipio, zona, secao))
        return self.line_rows

    def zones(
        self, ano: int, turno: int, uf: str, municipio: int, cargo: str, numero: int
    ) -> tuple[VotosZona, ...]:
        self.calls.append(("zones", ano, turno, uf, municipio, cargo, numero))
        return self.zone_rows

    def section_projections(
        self, ano: int, turno: int, uf: str, cargo: str
    ) -> tuple[SectionProjection, ...]:
        self.calls.append(("section_projections", ano, turno, uf, cargo))
        return self.sections

    def nominal_projections(self, ano: int, turno: int, uf: str, cargo: str) -> tuple[object, ...]:
        self.calls.append(("nominal_projections", ano, turno, uf, cargo))
        return ()

    def blank_projections(self, ano: int, turno: int, uf: str, cargo: str) -> tuple[object, ...]:
        self.calls.append(("blank_projections", ano, turno, uf, cargo))
        return ()

    def close(self) -> None:
        self.calls.append(("close",))


class _Cursor:
    def execute(self, _query: str, _params: Sequence[object] | None = None) -> None:
        return None

    def fetchall(self) -> list[tuple[object, ...]]:
        return []

    def __enter__(self) -> "_Cursor":
        return self

    def __exit__(self, *args: object) -> None:
        return None


class _Connection:
    def cursor(self) -> _Cursor:
        return _Cursor()

    def transaction(self) -> "_Connection":
        return self

    def close(self) -> None:
        return None

    def __enter__(self) -> "_Connection":
        return self

    def __exit__(self, *args: object) -> None:
        return None
