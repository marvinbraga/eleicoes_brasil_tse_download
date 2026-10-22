"""Wires the schema upgrade. It is the only code path that runs Alembic against Postgres."""

from collections.abc import Mapping

from eleicoes.adapters.orm.migrate import head_revision, upgrade_database
from eleicoes.composition.correspondencia import _host_settings


def migrate_database(env: Mapping[str, str]) -> str:
    upgrade_database(_host_settings(env))
    return head_revision()
