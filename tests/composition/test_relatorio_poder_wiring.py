"""The power-report store is wired with the same Postgres settings as the boletim reader."""

from collections.abc import Mapping, Sequence

import pytest

from eleicoes.composition.grade import build_power_report_store


def test_builder_binds_the_given_settings_without_a_socket(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[dict[str, str]] = []

    def connect(settings: Mapping[str, str]) -> _Connection:
        seen.append(dict(settings))
        return _Connection()

    monkeypatch.setattr("eleicoes.composition.grade.connect_postgres", connect)
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

    def connect(settings: Mapping[str, str]) -> _Connection:
        seen.append(dict(settings))
        return _Connection()

    monkeypatch.setattr("eleicoes.composition.grade.connect_postgres", connect)
    monkeypatch.setattr("eleicoes.composition.grade.load_dotenv", lambda: None)
    monkeypatch.setenv("POSTGRES_HOST", "127.0.0.1")
    monkeypatch.setenv("POSTGRES_PORT", "25432")
    monkeypatch.setenv("POSTGRES_DB", "eleicoes")
    store = build_power_report_store()
    store.ensure_model()
    assert seen[0]["POSTGRES_HOST"] == "127.0.0.1"
    assert seen[0]["POSTGRES_PORT"] == "25432"
    store.close()


class _Cursor:
    def execute(self, _query: str, _params: Sequence[object] | None = None) -> None:
        return None

    def __enter__(self) -> "_Cursor":
        return self

    def __exit__(self, *_args: object) -> None:
        return None


class _Connection:
    def __init__(self) -> None:
        self.closed = False

    def cursor(self) -> _Cursor:
        return _Cursor()

    def transaction(self) -> "_Connection":
        return self

    def close(self) -> None:
        self.closed = True

    def __enter__(self) -> "_Connection":
        return self

    def __exit__(self, *_args: object) -> None:
        return None
