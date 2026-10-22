"""Alembic environment. migrate.py passes an open connection; the alembic CLI reads .env."""

import os
from logging.config import fileConfig
from typing import Final

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import Connection
from sqlalchemy.pool import NullPool

from eleicoes.adapters.orm.models import Base
from eleicoes.adapters.orm.sessions import sqlalchemy_url
from eleicoes.composition.correspondencia import _host_settings

_OFFLINE_URL: Final = "postgresql+psycopg://"
_SCHEMAS: Final = frozenset({"raw", "analise"})

config = context.config


def include_name(name: str | None, type_: str, _parents: object) -> bool:
    return type_ != "schema" or name in _SCHEMAS


def include_object(
    _object: object,
    _name: str | None,
    _type: str,
    reflected: bool,
    compare_to: object | None,
) -> bool:
    """The models map only part of the schema. Autogenerate must never propose a drop."""
    return not (reflected and compare_to is None)


def _run_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url") or _OFFLINE_URL,
        target_metadata=Base.metadata,
        literal_binds=True,
        include_schemas=True,
        include_name=include_name,
        include_object=include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


def _run_online(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=Base.metadata,
        include_schemas=True,
        include_name=include_name,
        include_object=include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


def _run_from_environment() -> None:
    load_dotenv()
    engine = create_engine(sqlalchemy_url(_host_settings(os.environ)), poolclass=NullPool)
    try:
        with engine.connect() as connection:
            _run_online(connection)
    finally:
        engine.dispose()


def _run() -> None:
    if config.config_file_name is not None:
        fileConfig(config.config_file_name, disable_existing_loggers=False)
    if context.is_offline_mode():
        _run_offline()
        return
    given = config.attributes.get("connection")
    if isinstance(given, Connection):
        _run_online(given)
        return
    _run_from_environment()


_run()
