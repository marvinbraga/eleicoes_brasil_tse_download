"""Pool factory and lifespan. No database socket."""

import asyncio
from collections.abc import Mapping

import pytest

from eleicoes.composition.api import (
    _pool_from_environment,
    build_pool,
    create_app,
    postgres_conninfo,
)
from eleicoes.domain.errors import DatabaseConfigError


class _RecordingPool:
    def __init__(self, conninfo: str, *, open: bool, min_size: int, max_size: int) -> None:
        self.conninfo = conninfo
        self.constructor_open = open
        self.min_size = min_size
        self.max_size = max_size
        self.opened = False
        self.closed = False

    async def open(self, wait: bool = False, timeout: float = 30.0) -> None:
        self.opened = wait and timeout > 0

    async def close(self, timeout: float = 5.0) -> None:
        self.closed = timeout >= 0

    def connection(self) -> object:
        raise AssertionError("lifespan does not check out a connection")


def _env() -> dict[str, str]:
    return {
        "POSTGRES_HOST": "127.0.0.1",
        "POSTGRES_PORT": "15432",
        "POSTGRES_USER": "eleicoes",
        "POSTGRES_PASSWORD": "secret",
        "POSTGRES_DB": "eleicoes",
    }


def test_conninfo_rejects_missing_and_invalid_values() -> None:
    with pytest.raises(DatabaseConfigError) as missing:
        postgres_conninfo({})
    assert "POSTGRES_HOST" in missing.value.missing
    blank = _env()
    blank["POSTGRES_PASSWORD"] = "  "
    with pytest.raises(DatabaseConfigError) as empty:
        postgres_conninfo(blank)
    assert empty.value.missing == ("POSTGRES_PASSWORD",)
    invalid = _env()
    invalid["POSTGRES_PORT"] = "x"
    with pytest.raises(DatabaseConfigError) as port:
        postgres_conninfo(invalid)
    assert port.value.missing == ("POSTGRES_PORT",)


def test_build_pool_rewrites_an_unresolved_compose_host(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("eleicoes.composition.api.AsyncConnectionPool", _RecordingPool)
    monkeypatch.setattr("eleicoes.composition.correspondencia._resolves", lambda _host: False)
    env = _env()
    env["POSTGRES_HOST"] = "postgres"
    env["POSTGRES_PORT"] = "5432"
    env["POSTGRES_PUBLISH_PORT"] = "15432"
    pool = build_pool(env)
    assert isinstance(pool, _RecordingPool)
    assert pool.constructor_open is False
    assert pool.min_size == 1
    assert pool.max_size == 4
    assert "host=127.0.0.1" in pool.conninfo
    assert "port=15432" in pool.conninfo


def test_build_pool_keeps_a_resolvable_compose_host(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("eleicoes.composition.api.AsyncConnectionPool", _RecordingPool)
    monkeypatch.setattr("eleicoes.composition.correspondencia._resolves", lambda _host: True)
    env = _env()
    env["POSTGRES_HOST"] = "postgres"
    env["POSTGRES_PORT"] = "5432"
    env["POSTGRES_PUBLISH_PORT"] = "15432"
    pool = build_pool(env)
    assert isinstance(pool, _RecordingPool)
    assert "host=postgres" in pool.conninfo
    assert "port=5432" in pool.conninfo


def test_environment_factory_loads_dotenv(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[bool] = []
    monkeypatch.setattr("eleicoes.composition.api.AsyncConnectionPool", _RecordingPool)
    monkeypatch.setattr("eleicoes.composition.api.load_dotenv", lambda: calls.append(True))
    for key, value in _env().items():
        monkeypatch.setenv(key, value)
    pool = _pool_from_environment()
    assert calls == [True]
    assert isinstance(pool, _RecordingPool)
    assert "host=127.0.0.1" in pool.conninfo


def test_lifespan_opens_and_closes_the_injected_factory() -> None:
    created: list[_RecordingPool] = []

    def factory() -> _RecordingPool:
        pool = _RecordingPool("host=127.0.0.1", open=False, min_size=1, max_size=4)
        created.append(pool)
        return pool

    application = create_app(pool_factory=factory)

    async def run() -> None:
        async with application.router.lifespan_context(application):
            assert application.state.pool is created[0]
            assert created[0].opened
        assert created[0].closed

    asyncio.run(run())


def test_conninfo_quotes_the_database_name() -> None:
    env: Mapping[str, str] = _env()
    info = postgres_conninfo(env)
    assert "dbname=eleicoes" in info
    assert "user=eleicoes" in info
