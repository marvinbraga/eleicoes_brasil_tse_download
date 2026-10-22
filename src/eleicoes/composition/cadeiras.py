"""Wires the candidate-vote scan and the stored seat votes."""

import os
from collections.abc import Mapping

from dotenv import load_dotenv

from eleicoes.adapters.orm.sessions import open_sync_session
from eleicoes.adapters.postgres_relatorio_cadeiras import PostgresSeatVoteStore
from eleicoes.adapters.postgres_sink import connect_postgres
from eleicoes.adapters.postgres_votos_candidato import PostgresCandidateVotes
from eleicoes.composition.correspondencia import _host_settings


def build_candidate_votes(env: Mapping[str, str] | None = None) -> PostgresCandidateVotes:
    settings = _host_settings(_settings(env))
    return PostgresCandidateVotes(lambda: connect_postgres(settings))


def build_seat_vote_store(env: Mapping[str, str] | None = None) -> PostgresSeatVoteStore:
    settings = _host_settings(_settings(env))
    return PostgresSeatVoteStore(lambda: open_sync_session(settings))


def _settings(env: Mapping[str, str] | None) -> Mapping[str, str]:
    if env is not None:
        return env
    load_dotenv()
    return os.environ
