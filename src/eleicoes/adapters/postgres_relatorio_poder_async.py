"""Async cache of party-power cells. Statements are the sync ORM writes, without DDL."""

from collections.abc import Callable
from datetime import datetime
from typing import TypeVar

import psycopg
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from eleicoes.adapters.postgres_relatorio_poder import read_power, write_power
from eleicoes.domain.errors import ElectionError
from eleicoes.domain.stored_grade import StoredCell
from eleicoes.ports.relatorio_poder import StoredReport

_FAILED = "power report store failed"
_T = TypeVar("_T")


class AsyncPostgresPowerReportStore:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def load(self, ano: int, turno: int, cargo: str) -> StoredReport | None:
        def work(sync: Session) -> StoredReport | None:
            return read_power(sync, ano, turno, cargo)

        return await self._run(work)

    async def save(
        self,
        ano: int,
        turno: int,
        cargo: str,
        cells: tuple[StoredCell, ...],
    ) -> datetime:
        def work(sync: Session) -> datetime:
            return write_power(sync, ano, turno, cargo, cells)

        return await self._run(work)

    async def _run(self, work: Callable[[Session], _T]) -> _T:
        try:
            async with self._session.begin():
                return await self._session.run_sync(work)
        except ElectionError:
            raise
        except (SQLAlchemyError, psycopg.Error) as exc:
            raise ElectionError(_FAILED) from exc
