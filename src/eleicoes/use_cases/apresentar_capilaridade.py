"""Capillarity report from the stored municipal cells. No ballot is read."""

import os
from collections.abc import Mapping

from dotenv import load_dotenv

from eleicoes.domain.capilaridade import places_from_cells, require_capillarity_cargo
from eleicoes.domain.capilaridade_classe import CapillarityReport, build_report
from eleicoes.domain.errors import MissingPowerReportError
from eleicoes.domain.values import ElectionYear, Turno
from eleicoes.ports.capilaridade import MunicipalCellSource


def build_capillarity(
    reader: MunicipalCellSource,
    ano: int,
    turno: int,
    cargo: str,
) -> CapillarityReport:
    year = ElectionYear(ano).value
    turn = Turno(turno).value
    office = require_capillarity_cargo(cargo)
    cells = reader.municipal_cells(year, turn, office)
    if not cells:
        raise MissingPowerReportError(office)
    return build_report(year, turn, office, places_from_cells(cells))


def _production_reader() -> MunicipalCellSource:
    from eleicoes.adapters.orm.sessions import open_sync_session
    from eleicoes.adapters.postgres_perfis import PostgresStoredLines
    from eleicoes.composition.correspondencia import _host_settings

    settings = _host_settings(_environment())
    return PostgresStoredLines(lambda: open_sync_session(settings))


def _environment() -> Mapping[str, str]:
    load_dotenv()
    return os.environ
