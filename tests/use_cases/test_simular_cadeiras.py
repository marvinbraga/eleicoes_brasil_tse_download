"""The API use case: stored votes in, simulation out, 409 when a cargo is missing."""

import asyncio
from datetime import UTC, datetime

import pytest

from eleicoes.domain.cadeiras import CARGOS_GRAVADOS
from eleicoes.domain.errors import (
    MissingSeatReportError,
    UnknownPartyRegistryError,
    UnsupportedSeatTurnError,
)
from eleicoes.domain.simulacao_cadeiras import VotoApurado
from eleicoes.ports.relatorio_cadeiras import StoredSeatVotes
from eleicoes.use_cases.simular_cadeiras import stored_simulation

_OLD = datetime(2026, 10, 20, tzinfo=UTC)
_NEW = datetime(2026, 10, 22, tzinfo=UTC)


class _Store:
    def __init__(self, stored: tuple[StoredSeatVotes, ...]) -> None:
        self.stored = stored

    async def load(self, _ano: int, _turno: int) -> tuple[StoredSeatVotes, ...]:
        return self.stored


def _all() -> tuple[StoredSeatVotes, ...]:
    rows = [StoredSeatVotes(cargo, (), _NEW) for cargo in CARGOS_GRAVADOS]
    rows[0] = StoredSeatVotes(
        "governador", (VotoApurado("governador", "SE", "nominal", 13, 9),), _OLD
    )
    return tuple(rows)


def test_simulation_uses_the_oldest_timestamp() -> None:
    found = asyncio.run(stored_simulation(_Store(_all()), 2026, 1))
    assert found.gerado_em == _OLD
    assert found.simulacao.governo.eleitos_por_partido() == {13: 1}


def test_missing_cargos_are_named_with_the_command() -> None:
    with pytest.raises(MissingSeatReportError) as caught:
        asyncio.run(stored_simulation(_Store(_all()[:3]), 2026, 1))
    assert caught.value.cargos == ("deputadoEstadual", "deputadoDistrital")
    assert "scripts/relatorio_cadeiras.py" in str(caught.value)


def test_year_without_registry_fails_before_reading() -> None:
    with pytest.raises(UnknownPartyRegistryError):
        asyncio.run(stored_simulation(_Store(()), 2022, 1))


def test_second_round_is_rejected_before_reading() -> None:
    class _Unread(_Store):
        async def load(self, _ano: int, _turno: int) -> tuple[StoredSeatVotes, ...]:
            raise AssertionError("the store must not be read")

    with pytest.raises(UnsupportedSeatTurnError) as caught:
        asyncio.run(stored_simulation(_Unread(_all()), 2026, 2))
    assert caught.value.turno == 2
