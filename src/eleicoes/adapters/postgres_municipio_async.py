"""Async municipality names. The query is the sync ORM select."""

from collections.abc import Callable, Mapping
from typing import TypeVar

import psycopg
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from eleicoes.adapters.postgres_municipio import read_names
from eleicoes.domain.errors import ElectionError

_FAILED = "database read failed"
_T = TypeVar("_T")


class AsyncPostgresMunicipalityNames:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def names(self, uf: str) -> Mapping[int, str]:
        def work(sync: Session) -> Mapping[int, str]:
            return read_names(sync, uf)

        return await self._run(work)

    async def _run(self, work: Callable[[Session], _T]) -> _T:
        try:
            async with self._session.begin():
                return await self._session.run_sync(work)
        except ElectionError:
            raise
        except (SQLAlchemyError, psycopg.Error) as exc:
            raise ElectionError(_FAILED) from exc
