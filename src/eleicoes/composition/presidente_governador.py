"""Wires the stored president × governor report. The password stays in the factory."""

import os
from collections.abc import Mapping

from dotenv import load_dotenv

from eleicoes.adapters.postgres_relatorio_presidente_governador import (
    PostgresPresidentGovernorStore,
)
from eleicoes.adapters.postgres_sink import connect_postgres
from eleicoes.composition.correspondencia import _host_settings


def build_cross_report_store(
    env: Mapping[str, str] | None = None,
) -> PostgresPresidentGovernorStore:
    settings = _host_settings(_settings(env))
    return PostgresPresidentGovernorStore(lambda: connect_postgres(settings))


def _settings(env: Mapping[str, str] | None) -> Mapping[str, str]:
    if env is not None:
        return env
    load_dotenv()
    return os.environ
