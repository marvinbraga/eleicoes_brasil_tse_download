"""Session doubles for the ORM stores. Unit tests do not open a Postgres socket."""

import sqlite3
import weakref
from collections.abc import Callable
from typing import Protocol

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.exc import MultipleResultsFound, NoResultFound
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from sqlalchemy.sql.dml import Delete
from sqlalchemy.sql.elements import TextClause


class ScriptedSession:
    """Records statements and returns queued rows. DDL and deletes do not consume rows."""

    def __init__(self, dialect: str = "postgresql") -> None:
        self.dialect_name = dialect
        self.executed: list[tuple[int, object]] = []
        self.added: list[tuple[int, object]] = []
        self.batches: list[list[object]] = []
        self.closed = 0
        self.begins = 0
        self.fail: BaseException | None = None
        self.fixed: list[object] | None = None

    def push(self, *rows: object) -> None:
        self.batches.append(list(rows))

    def get_bind(self) -> "_Bind":
        return _Bind(self.dialect_name)

    def begin(self) -> "_Begin":
        return _Begin(self)

    def execute(self, statement: object) -> "_Result":
        if self.fail is not None:
            raise self.fail
        self.executed.append((self.begins, statement))
        return _Result(self._rows(statement))

    def add(self, entity: object) -> None:
        self.added.append((self.begins, entity))

    def close(self) -> None:
        self.closed += 1

    def _rows(self, statement: object) -> list[object]:
        if isinstance(statement, (TextClause, Delete)):
            return []
        if self.fixed is not None:
            return list(self.fixed)
        if not self.batches:
            return []
        return self.batches.pop(0)


class _Bind:
    def __init__(self, name: str) -> None:
        self.dialect = _Dialect(name)


class _Dialect:
    def __init__(self, name: str) -> None:
        self.name = name


class _Begin:
    def __init__(self, session: ScriptedSession) -> None:
        self._session = session

    def __enter__(self) -> ScriptedSession:
        if self._session.fail is not None:
            raise self._session.fail
        self._session.begins += 1
        return self._session

    def __exit__(self, *_args: object) -> None:
        return None


class _Scalars:
    def __init__(self, rows: list[object]) -> None:
        self._rows = rows

    def all(self) -> list[object]:
        return list(self._rows)


class _Result:
    def __init__(self, rows: list[object]) -> None:
        self._rows = rows

    def scalars(self) -> _Scalars:
        return _Scalars(self._rows)

    def all(self) -> list[object]:
        return list(self._rows)

    def scalar_one(self) -> object:
        if not self._rows:
            raise NoResultFound()
        if len(self._rows) != 1:
            raise MultipleResultsFound()
        return self._rows[0]


class _SyncLike(Protocol):
    def begin(self) -> object: ...

    def close(self) -> None: ...


class SyncSessionBridge:
    """Async begin/run_sync over a sync session. Avoids an async SQLite driver."""

    def __init__(self, session: _SyncLike) -> None:
        self._session = session

    def begin(self) -> "_AsyncBegin":
        return _AsyncBegin(self._session.begin())

    async def run_sync(
        self,
        work: Callable[..., object],
        *args: object,
        **kwargs: object,
    ) -> object:
        return work(self._session, *args, **kwargs)

    async def close(self) -> None:
        self._session.close()


class _AsyncBegin:
    def __init__(self, inner: object) -> None:
        self._inner = inner

    async def __aenter__(self) -> object:
        return self._inner.__enter__()

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> object:
        return self._inner.__exit__(exc_type, exc, tb)


def memory_sessions() -> Callable[[], Session]:
    """One SQLite connection with the raw and analise schema names the models use."""
    connection = sqlite3.connect(":memory:", check_same_thread=False)
    connection.execute("ATTACH DATABASE ':memory:' AS analise")
    connection.execute("ATTACH DATABASE ':memory:' AS raw")
    connection.execute("PRAGMA foreign_keys=ON")
    connection.commit()
    engine = create_engine("sqlite://", creator=lambda: connection, poolclass=StaticPool)

    def open_session() -> Session:
        return Session(engine, expire_on_commit=False)

    weakref.finalize(open_session, _close_memory, engine, connection)
    return open_session


def _close_memory(engine: Engine, connection: sqlite3.Connection) -> None:
    engine.dispose()
    try:
        connection.close()
    except sqlite3.ProgrammingError:
        return
