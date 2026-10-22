"""Async read of the stored seat votes. Same ORM statements as the sync store, no DDL."""

import psycopg
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from eleicoes.adapters.postgres_relatorio_cadeiras import read_seat_votes
from eleicoes.domain.errors import ElectionError
from eleicoes.ports.relatorio_cadeiras import StoredSeatVotes

_FAILED = "seat vote store failed"


class AsyncPostgresSeatVoteStore:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def load(self, ano: int, turno: int) -> tuple[StoredSeatVotes, ...]:
        def work(sync: Session) -> tuple[StoredSeatVotes, ...]:
            return read_seat_votes(sync, ano, turno)

        try:
            async with self._session.begin():
                return await self._session.run_sync(work)
        except ElectionError:
            raise
        except (SQLAlchemyError, psycopg.Error) as exc:
            raise ElectionError(_FAILED) from exc
