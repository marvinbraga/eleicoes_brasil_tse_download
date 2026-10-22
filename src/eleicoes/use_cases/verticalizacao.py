"""Build the verticalization base from the stored power lines of the five offices."""

import os
from collections.abc import Mapping

from dotenv import load_dotenv

from eleicoes.domain.values import ElectionYear, Turno
from eleicoes.domain.verticalizacao import VerticalBase, vertical_base
from eleicoes.ports.verticalizacao import VerticalSource


def build_vertical_base(source: VerticalSource, ano: int, turno: int) -> VerticalBase:
    year = ElectionYear(ano).value
    turn = Turno(turno).value
    return vertical_base(year, turn, source.vertical_lines(year, turn))


def _production_reader() -> VerticalSource:
    from eleicoes.adapters.orm.sessions import open_sync_session
    from eleicoes.adapters.postgres_verticalizacao import PostgresVerticalLines
    from eleicoes.composition.correspondencia import _host_settings

    settings = _host_settings(_environment())
    return PostgresVerticalLines(lambda: open_sync_session(settings))


def _environment() -> Mapping[str, str]:
    load_dotenv()
    return os.environ
