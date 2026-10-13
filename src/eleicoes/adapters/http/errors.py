"""Domain and validation failures become Portuguese HTTP errors, without tracebacks."""

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from eleicoes.domain.errors import (
    DatabaseConfigError,
    ElectionError,
    InvalidBoletimConsultaError,
    InvalidCargoError,
    InvalidElectionYearError,
    InvalidNivelError,
    InvalidNumeroError,
    InvalidOrdemError,
    InvalidStoredReportError,
    InvalidTurnoError,
    InvalidUfError,
)

_HTTP: tuple[tuple[type[ElectionError], int, str], ...] = (
    (InvalidElectionYearError, 422, "Ano inválido."),
    (InvalidTurnoError, 422, "Turno inválido."),
    (InvalidUfError, 422, "UF inválida."),
    (InvalidCargoError, 422, "Cargo inválido."),
    (InvalidNumeroError, 422, "Número inválido."),
    (InvalidNivelError, 422, "Nível inválido."),
    (InvalidOrdemError, 422, "Ordem inválida."),
    (InvalidBoletimConsultaError, 422, "Consulta de boletim inválida."),
    (InvalidStoredReportError, 422, "Relatório armazenado inválido."),
    (DatabaseConfigError, 500, "Configuração do banco ausente."),
)
_GENERIC = "Não foi possível consultar os dados."


def http_error(exc: ElectionError) -> tuple[int, str]:
    for kind, status, message in _HTTP:
        if isinstance(exc, kind):
            return status, message
    return 500, _GENERIC


async def election_error(_request: Request, exc: ElectionError) -> JSONResponse:
    status, message = http_error(exc)
    return JSONResponse(status_code=status, content={"detail": message})


async def invalid_request(_request: Request, _exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": "Parâmetros inválidos."})


async def http_exception(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
    detail = _STATUS.get(exc.status_code, _GENERIC)
    return JSONResponse(status_code=exc.status_code, content={"detail": detail})


async def unexpected(_request: Request, _exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=500, content={"detail": _GENERIC})


_STATUS = {
    404: "Recurso não encontrado.",
    405: "Método não permitido.",
}
