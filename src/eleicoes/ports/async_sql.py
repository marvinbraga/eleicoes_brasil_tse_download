"""Async SQL session used by read adapters. The pool is owned by the HTTP edge."""

from collections.abc import Sequence
from contextlib import AbstractAsyncContextManager
from types import TracebackType
from typing import Protocol, Self


class AsyncSqlCursor(Protocol):
    async def execute(self, query: str, params: Sequence[object] | None = None) -> object: ...

    async def fetchall(self) -> Sequence[Sequence[object]]: ...

    async def __aenter__(self) -> Self: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool | None: ...


class AsyncSqlTransaction(Protocol):
    async def __aenter__(self) -> object: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool | None: ...


class AsyncSqlConnection(Protocol):
    def cursor(self) -> AsyncSqlCursor: ...

    def transaction(self) -> AsyncSqlTransaction: ...


class AsyncPool(Protocol):
    async def open(self, wait: bool = False, timeout: float = 30.0) -> None: ...

    async def close(self, timeout: float = 5.0) -> None: ...

    def connection(self) -> AbstractAsyncContextManager[AsyncSqlConnection]: ...
