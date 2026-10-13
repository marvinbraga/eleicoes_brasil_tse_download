"""Portuguese HTTP mapping. No database socket."""

import asyncio
import json
from typing import cast

import httpx
from fastapi import FastAPI
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.requests import Request

from eleicoes.adapters.http.bundle import ReadPorts
from eleicoes.adapters.http.errors import http_error, http_exception
from eleicoes.adapters.http.schemas_votos import IndicioBoletimJson
from eleicoes.composition.api import create_app
from eleicoes.domain.boletim_consulta import IndicioBoletim
from eleicoes.domain.correspondencia.indicio import Gravidade
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
from eleicoes.ports.boletim_consulta import AsyncBoletimReader
from eleicoes.ports.grade import AsyncMunicipalityNames
from eleicoes.ports.relatorio_poder import AsyncRelatorioPoderStore
from eleicoes.ports.relatorio_presidente_governador import AsyncRelatorioPresidenteGovernadorStore

_GENERIC = "Não foi possível consultar os dados."


def test_each_domain_error_has_a_portuguese_status() -> None:
    cases = (
        (InvalidElectionYearError(1800), 422, "Ano inválido."),
        (InvalidTurnoError(3), 422, "Turno inválido."),
        (InvalidUfError("XX"), 422, "UF inválida."),
        (InvalidCargoError(""), 422, "Cargo inválido."),
        (InvalidNumeroError(-1), 422, "Número inválido."),
        (InvalidNivelError("bairro"), 422, "Nível inválido."),
        (InvalidOrdemError("lado"), 422, "Ordem inválida."),
        (InvalidBoletimConsultaError("campo"), 422, "Consulta de boletim inválida."),
        (InvalidStoredReportError("gerado_em"), 422, "Relatório armazenado inválido."),
        (DatabaseConfigError(("POSTGRES_HOST",)), 500, "Configuração do banco ausente."),
        (ElectionError("database read failed"), 500, _GENERIC),
    )
    for exc, status, detail in cases:
        assert http_error(exc) == (status, detail)


def test_finding_json_publishes_the_severity_code() -> None:
    row = IndicioBoletim(
        codigo="soma_diverge",
        descricao="A soma diverge.",
        gravidade=Gravidade.ALTA,
        uf="ac",
        municipio=1,
        zona=2,
        secao=3,
        medida="sum 1; expected 2",
    )
    assert IndicioBoletimJson.from_domain(row).gravidade == "ALTA"


def test_unmapped_http_status_stays_generic() -> None:
    scope = {"type": "http", "method": "GET", "path": "/", "headers": [], "query_string": b""}
    request = Request(scope)
    response = asyncio.run(http_exception(request, StarletteHTTPException(401)))
    assert response.status_code == 401
    assert json.loads(response.body)["detail"] == _GENERIC


def test_post_is_rejected_in_portuguese() -> None:
    application = create_app(ports=_empty_ports())
    response = asyncio.run(_post(application, "/health"))
    assert response.status_code == 405
    assert response.json()["detail"] == "Método não permitido."


class _Unused:
    def __getattr__(self, name: str) -> object:
        raise AssertionError(name)


def _empty_ports() -> ReadPorts:
    unused = _Unused()
    return ReadPorts(
        boletim=cast(AsyncBoletimReader, unused),
        names=cast(AsyncMunicipalityNames, unused),
        power_store=cast(AsyncRelatorioPoderStore, unused),
        cross_store=cast(AsyncRelatorioPresidenteGovernadorStore, unused),
    )


async def _post(application: FastAPI, path: str) -> httpx.Response:
    transport = httpx.ASGITransport(app=application)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.post(path)
