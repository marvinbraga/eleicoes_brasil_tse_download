"""Report numbers and the HTML the presenters already build."""

import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse

from eleicoes.adapters.http.dependencies import (
    ClassJob,
    ProfileJob,
    clear_report_caches,
    get_boletim_reader,
    get_class_job,
    get_cross_store,
    get_municipal_reader,
    get_municipality_names,
    get_power_store,
    get_profile_job,
    get_seat_store,
)
from eleicoes.adapters.http.schemas_cadeiras import CadeirasJson
from eleicoes.adapters.http.schemas_municipais import MunicipaisJson
from eleicoes.adapters.http.schemas_relatorios import (
    ClassJson,
    CrossReportJson,
    ForcaJson,
    GradeJson,
    ProfileJson,
)
from eleicoes.ports.boletim_consulta import AsyncBoletimReader
from eleicoes.ports.grade import AsyncMunicipalityNames
from eleicoes.ports.municipais import AsyncMunicipalResultsReader
from eleicoes.ports.relatorio_cadeiras import AsyncSeatVoteStore
from eleicoes.ports.relatorio_poder import AsyncRelatorioPoderStore
from eleicoes.ports.relatorio_presidente_governador import AsyncRelatorioPresidenteGovernadorStore
from eleicoes.use_cases.apresentar_municipais import MUNICIPAL_REPORT_YEAR, RenderMunicipalReport
from eleicoes.use_cases.placar_forca import MontarPlacarForca
from eleicoes.use_cases.render_reports import RenderPowerReport, RenderPresidentGovernorReport
from eleicoes.use_cases.simular_cadeiras import stored_simulation

router = APIRouter(tags=["Relatórios"])
Reader = Annotated[AsyncBoletimReader, Depends(get_boletim_reader)]
Names = Annotated[AsyncMunicipalityNames, Depends(get_municipality_names)]
PowerStore = Annotated[AsyncRelatorioPoderStore, Depends(get_power_store)]
CrossStore = Annotated[AsyncRelatorioPresidenteGovernadorStore, Depends(get_cross_store)]
ProfileBuild = Annotated[ProfileJob, Depends(get_profile_job)]
ClassBuild = Annotated[ClassJob, Depends(get_class_job)]
SeatStore = Annotated[AsyncSeatVoteStore, Depends(get_seat_store)]
MunicipalReader = Annotated[AsyncMunicipalResultsReader, Depends(get_municipal_reader)]
_GRADE = (
    "Exige ano, turno, uf e cargo. nivel admite municipio, uf, regiao ou pais. "
    "A UF ancora o relatório, como na linha de comando, e não recorta um único estado "
    "quando o nível percorre as UF apuradas. "
    "Se o relatório estiver gravado, devolve essas células; senão, lê os boletins. "
    "Com somente_gravado=true, não lê os boletins: sem relatório gravado, responde 409."
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
_PERFIS = (
    "Exige ano, turno e cargo. grupos admite um número ou uma faixa, como 2-6. "
    "Lê as células gravadas; não relê os boletins."
)
_CLASSE = (
    "Exige ano e turno. Estima a classe do governador a partir do perfil do presidente, "
    "lendo só as células gravadas."
)


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
    somente_gravado: bool = False,
) -> GradeJson:
    built = await RenderPowerReport(reader, names, store).grade(
        ano,
        turno,
        uf,
        cargo,
        nivel,
        somente_gravado=somente_gravado,
    )
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
    if atualizar:
        clear_report_caches()
    return CrossReportJson.from_domain(report)


@router.get("/relatorios/dados/perfis", summary="Perfis municipais", description=_PERFIS)
async def perfis(
    ano: int,
    turno: int,
    cargo: str,
    build: ProfileBuild,
    grupos: str = "2-6",
) -> ProfileJson:
    report = await asyncio.to_thread(build, ano, turno, cargo, grupos)
    return ProfileJson.from_domain(report)


@router.get(
    "/relatorios/dados/classe-governador",
    summary="Classe do governador",
    description=_CLASSE,
)
async def classe_governador(ano: int, turno: int, build: ClassBuild) -> ClassJson:
    report = await asyncio.to_thread(build, ano, turno)
    return ClassJson.from_domain(report)


_FORCA = (
    "Exige ano e turno. cargo_referencia escolhe o cargo dos indicadores municipais "
    "(padrão deputadoEstadual). Lê só as células gravadas do relatório de poder. "
    "Cargos sem gravação voltam em faltando, com o comando para gerar; "
    "sem nenhum cargo gravado, responde 409."
)


@router.get("/relatorios/dados/forca", summary="Placar de força partidária", description=_FORCA)
async def forca(
    ano: int,
    turno: int,
    store: PowerStore,
    cargo_referencia: str = "deputadoEstadual",
) -> ForcaJson:
    placar = await MontarPlacarForca(store).execute(ano, turno, cargo_referencia)
    return ForcaJson.from_domain(placar)


_CADEIRAS = (
    "Exige ano e turno; só o turno 1 vale, outro turno responde 422. Estima as "
    "cadeiras da Câmara, das Assembleias e do Senado e o "
    "resultado de governador com os votos do 1º turno gravados por candidato. "
    "É uma estimativa, não o resultado oficial. Não lê os boletins: sem os votos "
    "gravados, responde 409 com o comando que os grava."
)


@router.get(
    "/relatorios/dados/cadeiras",
    summary="Simulação de cadeiras",
    description=_CADEIRAS,
)
async def cadeiras(ano: int, turno: int, store: SeatStore) -> CadeirasJson:
    return CadeirasJson.from_domain(await stored_simulation(store, ano, turno))


_MUNICIPAIS = (
    "Prefeitos e vereadores eleitos em 2024 por partido, com o eleitorado apto dos municípios "
    "governados e a sigla equivalente em 2026. uf é opcional; com uf, traz também os municípios. "
    "Lê só as tabelas analise.municipal_*; sem importação, responde 409."
)


@router.get(
    "/relatorios/dados/municipais-2024",
    summary="Resultados municipais de 2024",
    description=_MUNICIPAIS,
)
async def municipais_2024(reader: MunicipalReader, uf: str | None = None) -> MunicipaisJson:
    report = await RenderMunicipalReport(reader).view(MUNICIPAL_REPORT_YEAR, uf)
    return MunicipaisJson.from_domain(report)


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
    if atualizar:
        clear_report_caches()
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
    if atualizar:
        clear_report_caches()
    return HTMLResponse(content=html)
