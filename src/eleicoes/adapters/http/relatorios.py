"""Report numbers and the HTML the presenters already build."""

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse

from eleicoes.adapters.http.dependencies import (
    get_boletim_reader,
    get_cross_store,
    get_municipality_names,
    get_power_store,
)
from eleicoes.adapters.http.schemas_relatorios import CrossReportJson, GradeJson
from eleicoes.ports.boletim_consulta import AsyncBoletimReader
from eleicoes.ports.grade import AsyncMunicipalityNames
from eleicoes.ports.relatorio_poder import AsyncRelatorioPoderStore
from eleicoes.ports.relatorio_presidente_governador import AsyncRelatorioPresidenteGovernadorStore
from eleicoes.use_cases.render_reports import RenderPowerReport, RenderPresidentGovernorReport

router = APIRouter(tags=["Relatórios"])
Reader = Annotated[AsyncBoletimReader, Depends(get_boletim_reader)]
Names = Annotated[AsyncMunicipalityNames, Depends(get_municipality_names)]
PowerStore = Annotated[AsyncRelatorioPoderStore, Depends(get_power_store)]
CrossStore = Annotated[AsyncRelatorioPresidenteGovernadorStore, Depends(get_cross_store)]
_GRADE = (
    "Exige ano, turno, uf e cargo. nivel admite municipio, uf, regiao ou pais. "
    "A UF ancora o relatório, como na linha de comando, e não recorta um único estado "
    "quando o nível percorre as UF apuradas. "
    "Se o relatório estiver gravado, devolve essas células; senão, lê os boletins."
)
_CROSS_SCOPE = (
    "Exige ano, turno e uf. A UF valida o recorte, como no apresentador; "
    "o cruzamento reúne os municípios apurados."
)
_CROSS = (
    f"{_CROSS_SCOPE} Sem atualizar, devolve o relatório gravado; "
    "com atualizar=true, relê os boletins."
)
_HTML = (
    "Sem atualizar, devolve o HTML gravado; com atualizar=true, relê os boletins. "
    "Não abre navegador."
)
_HTML_OK = {200: {"content": {"text/html": {}}, "description": "Documento HTML."}}


@router.get("/relatorios/dados/grade", summary="Grade de poder", description=_GRADE)
async def grade(
    ano: int,
    turno: int,
    uf: str,
    cargo: str,
    reader: Reader,
    names: Names,
    store: PowerStore,
    nivel: str = "municipio",
) -> GradeJson:
    built = await RenderPowerReport(reader, names, store).grade(ano, turno, uf, cargo, nivel)
    return GradeJson.from_domain(built)


@router.get(
    "/relatorios/dados/presidente-governador",
    summary="Cruzamento presidente e governador",
    description=_CROSS,
)
async def presidente_governador(
    ano: int,
    turno: int,
    uf: str,
    reader: Reader,
    names: Names,
    store: CrossStore,
    atualizar: bool = False,
) -> CrossReportJson:
    report = await RenderPresidentGovernorReport(reader, names, store).view(
        ano,
        turno,
        uf,
        atualizar=atualizar,
    )
    return CrossReportJson.from_domain(report)


@router.get(
    "/relatorios/poder",
    summary="Relatório de poder em HTML",
    description=_HTML,
    response_class=HTMLResponse,
    responses=_HTML_OK,  # type: ignore[arg-type]  # FastAPI types this map with Any
)
async def poder_html(
    ano: int,
    turno: int,
    uf: str,
    cargo: str,
    reader: Reader,
    names: Names,
    store: PowerStore,
    atualizar: bool = False,
) -> HTMLResponse:
    html = await RenderPowerReport(reader, names, store).execute(
        ano,
        turno,
        uf,
        cargo,
        atualizar=atualizar,
    )
    return HTMLResponse(content=html)


@router.get(
    "/relatorios/presidente-governador",
    summary="Relatório presidente e governador em HTML",
    description=f"{_CROSS_SCOPE} {_HTML}",
    response_class=HTMLResponse,
    responses=_HTML_OK,  # type: ignore[arg-type]  # FastAPI types this map with Any
)
async def presidente_governador_html(
    ano: int,
    turno: int,
    uf: str,
    reader: Reader,
    names: Names,
    store: CrossStore,
    atualizar: bool = False,
) -> HTMLResponse:
    html = await RenderPresidentGovernorReport(reader, names, store).execute(
        ano,
        turno,
        uf,
        atualizar=atualizar,
    )
    return HTMLResponse(content=html)
