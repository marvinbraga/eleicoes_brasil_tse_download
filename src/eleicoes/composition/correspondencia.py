"""Wires the correspondence reader. Query functions live in eleicoes.consultas."""

import socket
from collections.abc import Mapping

from eleicoes.adapters.postgres_correspondencia import PostgresCorrespondenciaReader
from eleicoes.adapters.postgres_sink import connect_postgres

_COMPOSE_HOST = "postgres"


def build_correspondencia_reader(env: Mapping[str, str]) -> PostgresCorrespondenciaReader:
    settings = _host_settings(env)
    return PostgresCorrespondenciaReader(lambda: connect_postgres(settings))


def _host_settings(env: Mapping[str, str]) -> Mapping[str, str]:
    """Use the published port when the Compose DNS name is not visible."""
    host = env.get("POSTGRES_HOST", "")
    published = env.get("POSTGRES_PUBLISH_PORT", "").strip()
    if host != _COMPOSE_HOST or not published or _resolves(host):
        return env
    adjusted = dict(env)
    adjusted["POSTGRES_HOST"] = "127.0.0.1"
    adjusted["POSTGRES_PORT"] = published
    return adjusted


def _resolves(host: str) -> bool:
    try:
        socket.getaddrinfo(host, None)
    except OSError:
        return False
    return True
