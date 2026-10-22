"""Verticalization route: does a party's strength hold across offices?"""

import asyncio
from typing import Annotated, Final

from fastapi import APIRouter, Depends

from eleicoes.adapters.http.dependencies_verticalizacao import VerticalJob, get_vertical_job
from eleicoes.adapters.http.schemas_verticalizacao import VerticalJson
from eleicoes.domain.verticalizacao import DEPUTADO_FEDERAL, GOVERNADOR

router = APIRouter(tags=["Relatórios"])
VerticalBuild = Annotated[VerticalJob, Depends(get_vertical_job)]
_ALL_STATES: Final = "todas"
_VERTICAL: Final = (
    "Exige ano e turno. uf é opcional: sem ela, o recorte é o Brasil, e a coerência é "
    "calculada dentro de cada UF. partido, cargo_x e cargo_y escolhem a dispersão. "
    "Lê só as células gravadas dos cinco cargos; sem algum deles, responde 409."
)


@router.get(
    "/relatorios/dados/verticalizacao",
    summary="Verticalização",
    description=_VERTICAL,
)
async def verticalizacao(
    ano: int,
    turno: int,
    build: VerticalBuild,
    uf: str | None = None,
    partido: int | None = None,
    cargo_x: str = DEPUTADO_FEDERAL,
    cargo_y: str = GOVERNADOR,
) -> VerticalJson:
    view = await asyncio.to_thread(build, ano, turno, _uf(uf), partido, cargo_x, cargo_y)
    return VerticalJson.from_domain(view)


def _uf(uf: str | None) -> str | None:
    if uf is None or uf.strip() == "" or uf.strip().casefold() == _ALL_STATES:
        return None
    return uf
