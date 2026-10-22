"""The seat stores use the same Postgres settings as the other reports, without a socket."""

from collections.abc import Mapping

import pytest

from eleicoes.composition.cadeiras import build_candidate_votes, build_seat_vote_store

_ENV = {
    "POSTGRES_HOST": "127.0.0.1",
    "POSTGRES_PORT": "25432",
    "POSTGRES_USER": "eleicoes",
    "POSTGRES_PASSWORD": "secret",
    "POSTGRES_DB": "eleicoes",
}


def test_builders_bind_the_given_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[dict[str, str]] = []

    def remember(settings: Mapping[str, str]) -> object:
        seen.append(dict(settings))
        return object()

    monkeypatch.setattr("eleicoes.composition.cadeiras.open_sync_session", remember)
    monkeypatch.setattr("eleicoes.composition.cadeiras.connect_postgres", remember)
    store = build_seat_vote_store(_ENV)
    source = build_candidate_votes(_ENV)
    store._open()  # noqa: SLF001
    source._open()  # noqa: SLF001
    assert [item["POSTGRES_PORT"] for item in seen] == ["25432", "25432"]


def test_builders_read_the_process_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for key, value in _ENV.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setattr("eleicoes.composition.cadeiras.load_dotenv", lambda: None)
    assert build_seat_vote_store() is not None
    assert build_candidate_votes() is not None
