"""Construction checks shared by correspondence records."""

from eleicoes.domain.errors import InvalidCorrespondenceRecordError
from eleicoes.domain.values import Uf


def checked_place(uf: str, codigo_municipio: str, municipio: str, zona: int) -> str:
    require_text(codigo_municipio, "codigo_municipio")
    require_text(municipio, "municipio")
    require_int(zona, "zona")
    return Uf(uf).code


def require_text(value: str, field: str) -> None:
    if value.strip() == "":
        raise InvalidCorrespondenceRecordError(field)


def require_int(value: int, field: str) -> None:
    if isinstance(value, bool) or value < 0:
        raise InvalidCorrespondenceRecordError(field)
