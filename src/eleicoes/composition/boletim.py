"""Wires the boletim reader. Query functions live in eleicoes.consultas."""

from collections.abc import Mapping

from eleicoes.adapters.postgres_boletim_consulta import PostgresBoletimReader
from eleicoes.adapters.postgres_sink import connect_postgres
from eleicoes.composition.correspondencia import _host_settings


def build_boletim_reader(env: Mapping[str, str]) -> PostgresBoletimReader:
    settings = _host_settings(env)
    return PostgresBoletimReader(lambda: connect_postgres(settings))
