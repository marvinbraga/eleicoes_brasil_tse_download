"""Reads municipality names from raw.csec. User values are bound, never interpolated."""

from collections.abc import Mapping, Sequence
from typing import Final

from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.sql import Select

from eleicoes.adapters.orm.models import CorrespondenceSection
from eleicoes.adapters.orm.sessions import SyncSessionFactory
from eleicoes.domain.errors import InvalidBoletimConsultaError
from eleicoes.domain.values import Uf

_WIDTH: Final = 2


class PostgresMunicipalityNames:
    def __init__(self, sessions: SyncSessionFactory) -> None:
        self._sessions = sessions
        self._session: Session | None = None

    def names(self, uf: str) -> Mapping[int, str]:
        with self._open().begin():
            return read_names(self._open(), uf)

    def close(self) -> None:
        session = self._session
        self._session = None
        if session is not None:
            session.close()

    def _open(self) -> Session:
        if self._session is None:
            self._session = self._sessions()
        return self._session


def read_names(session: Session, uf: str) -> Mapping[int, str]:
    fetched = session.execute(name_query(Uf(uf).code)).all()
    return _names(tuple(_pair(row) for row in fetched))


def name_query(uf: str) -> Select[str | None, str | None]:
    return select(CorrespondenceSection.cd_municipio, CorrespondenceSection.nm_municipio).where(
        CorrespondenceSection.sg_uf == uf
    )


def _pair(row: Sequence[object]) -> tuple[object, ...]:
    return tuple(row)


def _names(rows: tuple[tuple[object, ...], ...]) -> dict[int, str]:
    found: dict[int, str] = {}
    for row in rows:
        if len(row) != _WIDTH:
            raise InvalidBoletimConsultaError("municipio")
        code = _code(row[0])
        label = _label(row[1])
        if label is None:
            continue
        previous = found.get(code)
        if previous is not None and previous != label:
            raise InvalidBoletimConsultaError("municipio")
        found[code] = label
    return found


def _code(value: object) -> int:
    if isinstance(value, bool):
        raise InvalidBoletimConsultaError("municipio")
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    raise InvalidBoletimConsultaError("municipio")


def _label(value: object) -> str | None:
    if not isinstance(value, str):
        raise InvalidBoletimConsultaError("municipio")
    stripped = value.strip()
    if stripped == "":
        return None
    return stripped
