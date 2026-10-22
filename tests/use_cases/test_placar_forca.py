"""Strength scoreboard use case. An in-memory store stands in for Postgres."""

import asyncio
from datetime import UTC, datetime

import pytest

from eleicoes.domain.errors import (
    InvalidCargoError,
    InvalidElectionYearError,
    MissingStrengthSourcesError,
)
from eleicoes.domain.stored_grade import StoredCell
from eleicoes.ports.relatorio_poder import StoredReport
from eleicoes.use_cases.placar_forca import MontarPlacarForca

_MOMENT = datetime(2026, 10, 22, tzinfo=UTC)
_UF = StoredCell("uf", "AC", "Acre", 100, 22, 30, 0)
_PAIS = StoredCell("pais", "BR", "Brasil", 100, 22, 30, 0)
_CITY = StoredCell("municipio", "1", "RIO BRANCO (AC)", 100, 22, 30, 0)


class _Store:
    def __init__(self, stored: dict[str, StoredReport | None]) -> None:
        self.stored = stored
        self.calls: list[tuple[str, tuple[str, ...]]] = []

    async def load(self, _ano: int, _turno: int, _cargo: str) -> StoredReport | None:
        raise AssertionError("the scoreboard reads levels only")

    async def save(
        self,
        _ano: int,
        _turno: int,
        _cargo: str,
        _cells: tuple[StoredCell, ...],
    ) -> datetime:
        raise AssertionError("the scoreboard never writes")

    async def load_levels(
        self,
        _ano: int,
        _turno: int,
        cargo: str,
        niveis: tuple[str, ...],
    ) -> StoredReport | None:
        self.calls.append((cargo, niveis))
        found = self.stored.get(cargo)
        if found is None:
            return None
        kept = tuple(cell for cell in found.cells if cell.nivel in niveis)
        return StoredReport(kept, found.gerado_em)


_CARGOS = ("presidente", "governador", "senador", "deputadoFederal", "deputadoEstadual")


def _all() -> dict[str, StoredReport | None]:
    cells = (_UF, _PAIS, _CITY)
    return {cargo: StoredReport(cells, _MOMENT) for cargo in _CARGOS}


def test_default_reference_reads_one_municipal_level() -> None:
    store = _Store(_all())
    placar = asyncio.run(MontarPlacarForca(store).execute(2026, 1, "deputadoEstadual"))
    assert store.calls == [
        ("presidente", ("pais", "uf")),
        ("deputadoFederal", ("pais", "uf")),
        ("deputadoEstadual", ("uf", "municipio")),
    ]
    assert placar.faltando == ()
    assert placar.pais.base.municipal is not None


def test_governor_reference_adds_a_fourth_read() -> None:
    store = _Store(_all())
    asyncio.run(MontarPlacarForca(store).execute(2026, 1, "governador"))
    assert store.calls[-1] == ("governador", ("municipio",))
    assert len(store.calls) == 4


def test_president_reference_reads_its_cities_in_the_same_call() -> None:
    store = _Store(_all())
    asyncio.run(MontarPlacarForca(store).execute(2026, 1, "presidente"))
    assert store.calls[0] == ("presidente", ("pais", "uf", "municipio"))
    assert len(store.calls) == 3


def test_empty_or_absent_reports_degrade_per_office() -> None:
    stored = _all()
    stored["presidente"] = None
    stored["deputadoFederal"] = StoredReport((), _MOMENT)
    placar = asyncio.run(MontarPlacarForca(_Store(stored)).execute(2026, 1, "deputadoEstadual"))
    assert placar.faltando == ("presidente", "deputadoFederal")


def test_nothing_stored_is_a_conflict_with_every_command() -> None:
    with pytest.raises(MissingStrengthSourcesError) as caught:
        asyncio.run(MontarPlacarForca(_Store({})).execute(2026, 1, "deputadoEstadual"))
    assert caught.value.cargos == ("presidente", "deputadoFederal", "deputadoEstadual")
    assert "--cargo deputadoFederal --sem-navegador" in str(caught.value)


def test_bad_input_fails_before_any_read() -> None:
    store = _Store(_all())
    with pytest.raises(InvalidCargoError):
        asyncio.run(MontarPlacarForca(store).execute(2026, 1, "deputadoDistrital"))
    with pytest.raises(InvalidElectionYearError):
        asyncio.run(MontarPlacarForca(store).execute(1900, 1, "deputadoEstadual"))
    assert store.calls == []
