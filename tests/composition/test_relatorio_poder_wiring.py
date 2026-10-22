"""The power-report store is wired with the same Postgres settings as the boletim reader."""

from collections.abc import Mapping

import pytest
from sqlalchemy.engine import Connection
from tests.adapters.orm_fakes import empty_catalog_connection

from eleicoes.composition.grade import build_power_report_store


def test_builder_binds_the_given_settings_without_a_socket(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[dict[str, str]] = []

    def connect(settings: Mapping[str, str]) -> _Session:
        seen.append(dict(settings))
        return _Session()

    monkeypatch.setattr("eleicoes.composition.grade.open_sync_session", connect)
    env = {
        "POSTGRES_HOST": "127.0.0.1",
        "POSTGRES_PORT": "25432",
        "POSTGRES_USER": "eleicoes",
        "POSTGRES_PASSWORD": "secret",
        "POSTGRES_DB": "eleicoes",
    }
    store = build_power_report_store(env)
    store.ensure_model()
    store.close()
    assert seen[0]["POSTGRES_HOST"] == "127.0.0.1"
    assert seen[0]["POSTGRES_PORT"] == "25432"
    assert seen[0]["POSTGRES_DB"] == "eleicoes"


def test_builder_without_arguments_reads_the_process_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[dict[str, str]] = []

    def connect(settings: Mapping[str, str]) -> _Session:
        seen.append(dict(settings))
        return _Session()

    monkeypatch.setattr("eleicoes.composition.grade.open_sync_session", connect)
    monkeypatch.setattr("eleicoes.composition.grade.load_dotenv", lambda: None)
    monkeypatch.setenv("POSTGRES_HOST", "127.0.0.1")
    monkeypatch.setenv("POSTGRES_PORT", "25432")
    monkeypatch.setenv("POSTGRES_DB", "eleicoes")
    store = build_power_report_store()
    store.ensure_model()
    assert seen[0]["POSTGRES_HOST"] == "127.0.0.1"
    assert seen[0]["POSTGRES_PORT"] == "25432"
    store.close()


class _Dialect:
    name = "postgresql"


class _Bind:
    dialect = _Dialect()


class _Session:
    def __init__(self) -> None:
        self.closed = False

    def get_bind(self) -> _Bind:
        return _Bind()

    def begin(self) -> "_Session":
        return self

    def execute(self, _statement: object) -> None:
        return None

    def connection(self) -> Connection:
        return empty_catalog_connection()

    def close(self) -> None:
        self.closed = True

    def __enter__(self) -> "_Session":
        return self

    def __exit__(self, *_args: object) -> None:
        return None
