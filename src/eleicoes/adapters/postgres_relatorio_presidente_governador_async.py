"""Async cache of president × governor places. Statements are the sync ORM writes."""

from collections.abc import Callable
from datetime import datetime
from typing import TypeVar

import psycopg
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from eleicoes.adapters.postgres_relatorio_presidente_governador import read_cross, write_cross
from eleicoes.domain.errors import ElectionError
from eleicoes.domain.presidente_governador import MunicipalPlace
from eleicoes.ports.relatorio_presidente_governador import StoredCrossReport

_FAILED = "cross report store failed"
_T = TypeVar("_T")


class AsyncPostgresPresidentGovernorStore:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def load(self, ano: int, turno: int) -> StoredCrossReport | None:
        def work(sync: Session) -> StoredCrossReport | None:
            return read_cross(sync, ano, turno)

        return await self._run(work)

    async def save(
        self,
        ano: int,
        turno: int,
        places: tuple[MunicipalPlace, ...],
    ) -> datetime:
        def work(sync: Session) -> datetime:
            return write_cross(sync, ano, turno, places)

        return await self._run(work)

    async def _run(self, work: Callable[[Session], _T]) -> _T:
        try:
            async with self._session.begin():
                return await self._session.run_sync(work)
        except ElectionError:
            raise
        except (SQLAlchemyError, psycopg.Error) as exc:
            raise ElectionError(_FAILED) from exc
