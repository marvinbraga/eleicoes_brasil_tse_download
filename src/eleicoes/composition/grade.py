"""Wires municipality names and the stored power report."""

import os
from collections.abc import Mapping

from dotenv import load_dotenv

from eleicoes.adapters.postgres_municipio import PostgresMunicipalityNames
from eleicoes.adapters.postgres_relatorio_poder import PostgresPowerReportStore
from eleicoes.adapters.postgres_sink import connect_postgres
from eleicoes.composition.correspondencia import _host_settings


def build_municipality_names(env: Mapping[str, str]) -> PostgresMunicipalityNames:
    settings = _host_settings(env)
    return PostgresMunicipalityNames(lambda: connect_postgres(settings))


def build_power_report_store(env: Mapping[str, str] | None = None) -> PostgresPowerReportStore:
    settings = _host_settings(_settings(env))
    return PostgresPowerReportStore(lambda: connect_postgres(settings))


def _settings(env: Mapping[str, str] | None) -> Mapping[str, str]:
    if env is not None:
        return env
    load_dotenv()
    return os.environ
