"""Wires municipality names. The grid entry point lives in eleicoes.consultas."""

from collections.abc import Mapping

from eleicoes.adapters.postgres_municipio import PostgresMunicipalityNames
from eleicoes.adapters.postgres_sink import connect_postgres
from eleicoes.composition.correspondencia import _host_settings


def build_municipality_names(env: Mapping[str, str]) -> PostgresMunicipalityNames:
    settings = _host_settings(env)
    return PostgresMunicipalityNames(lambda: connect_postgres(settings))
