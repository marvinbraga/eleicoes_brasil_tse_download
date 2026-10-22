"""Alembic upgrades for the Postgres schema. Only the migrar command changes the schema."""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Final, Protocol

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool

from eleicoes.adapters.orm.sessions import sqlalchemy_url
from eleicoes.domain.errors import ElectionError, SchemaOutdatedError

MIGRATIONS: Final = Path(__file__).resolve().parent / "migrations"
BASE_REVISION: Final = "0001"
HEAD: Final = "head"
BASELINE_TABLES: Final = frozenset(
    {
        ("raw", "csec"),
        ("raw", "ccont"),
        ("raw", "carga"),
        ("raw", "boletim"),
        ("analise", "relatorio_presidente_governador"),
        ("analise", "relatorio_presidente_governador_linha"),
        ("analise", "relatorio_presidente_governador_cedula"),
        ("analise", "relatorio_poder"),
        ("analise", "relatorio_poder_linha"),
    }
)
_VERSION_TABLE: Final = "alembic_version"
_LOCK_KEY: Final = 2_026_102_100_001
_LOCK: Final = text("SELECT pg_advisory_xact_lock(:key)")
_POSTGRES: Final = "postgresql"


@dataclass(frozen=True, slots=True)
class SchemaState:
    versioned: bool
    tables: frozenset[tuple[str, str]]

    @property
    def baseline_complete(self) -> bool:
        return self.tables >= BASELINE_TABLES


class MigrationRunner(Protocol):
    def stamp(self, revision: str) -> None: ...

    def upgrade(self, revision: str) -> None: ...


@dataclass(frozen=True, slots=True)
class MigrationPlan:
    """An unversioned database that already has every base table is marked as 0001."""

    stamp_base: bool

    def apply(self, runner: MigrationRunner) -> None:
        if self.stamp_base:
            runner.stamp(BASE_REVISION)
        runner.upgrade(HEAD)


class SchemaCheck(Protocol):
    def __call__(self, session: Session) -> None: ...


class AlembicRunner:
    def __init__(self, connection: Connection) -> None:
        self._config = migration_config(connection)

    def stamp(self, revision: str) -> None:
        command.stamp(self._config, revision)

    def upgrade(self, revision: str) -> None:
        command.upgrade(self._config, revision)


RunnerFactory = Callable[[Connection], MigrationRunner]
StateProbe = Callable[[Connection], SchemaState]


def plan_migration(state: SchemaState) -> MigrationPlan:
    return MigrationPlan(stamp_base=not state.versioned and state.baseline_complete)


def read_state(connection: Connection) -> SchemaState:
    inspector = inspect(connection)
    found = frozenset(
        (schema, name)
        for schema, name in BASELINE_TABLES
        if inspector.has_table(name, schema=schema)
    )
    return SchemaState(versioned=inspector.has_table(_VERSION_TABLE), tables=found)


def upgrade_schema(
    engine: Engine,
    runners: RunnerFactory = AlembicRunner,
    probe: StateProbe = read_state,
) -> None:
    """One transaction under an advisory lock, so two processes never migrate together."""
    with engine.begin() as connection:
        if connection.dialect.name == _POSTGRES:
            connection.execute(_LOCK, {"key": _LOCK_KEY})
        plan_migration(probe(connection)).apply(runners(connection))


def upgrade_database(env: Mapping[str, str]) -> None:
    engine = create_engine(sqlalchemy_url(env), poolclass=NullPool)
    try:
        upgrade_schema(engine)
    finally:
        engine.dispose()


def migration_config(connection: Connection | None = None) -> Config:
    config = Config()
    config.set_main_option("script_location", str(MIGRATIONS))
    config.attributes["connection"] = connection
    return config


@cache
def head_revision() -> str:
    head = ScriptDirectory.from_config(migration_config()).get_current_head()
    if head is None:
        raise ElectionError("no schema migration was found")
    return head


def current_revisions(connection: Connection) -> tuple[str, ...]:
    return tuple(MigrationContext.configure(connection).get_current_heads())


def require_revisions(current: tuple[str, ...]) -> None:
    expected = head_revision()
    if current != (expected,):
        raise SchemaOutdatedError(current, expected)


def require_current_schema(session: Session) -> None:
    require_revisions(current_revisions(session.connection()))
