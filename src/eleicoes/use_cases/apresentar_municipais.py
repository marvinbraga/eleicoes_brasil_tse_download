"""Relatório municipal de 2024 lido das tabelas analise.municipal_*."""

from typing import Final

from eleicoes.domain.errors import MissingMunicipalResultsError
from eleicoes.domain.forca_municipal import MunicipalReport, municipal_report, require_municipal_uf
from eleicoes.ports.municipais import AsyncMunicipalResultsReader

MUNICIPAL_REPORT_YEAR: Final = 2024


class RenderMunicipalReport:
    def __init__(self, reader: AsyncMunicipalResultsReader) -> None:
        self._reader = reader

    async def view(self, year: int, uf: str | None) -> MunicipalReport:
        chosen = require_municipal_uf(uf)
        stored = await self._reader.load(year, chosen)
        if stored is None:
            raise MissingMunicipalResultsError(year)
        return municipal_report(stored, chosen)
