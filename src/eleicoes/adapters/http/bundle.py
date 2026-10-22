"""Readers injected into one request. Tests pass these instead of a pool."""

from dataclasses import dataclass

from eleicoes.ports.boletim_consulta import AsyncBoletimReader
from eleicoes.ports.cadeiras import AsyncEstimativaCadeiras
from eleicoes.ports.grade import AsyncMunicipalityNames
from eleicoes.ports.municipais import AsyncMunicipalResultsReader
from eleicoes.ports.municipal_2024 import AsyncMunicipal2024
from eleicoes.ports.relatorio_cadeiras import AsyncSeatVoteStore
from eleicoes.ports.relatorio_poder import AsyncRelatorioPoderStore
from eleicoes.ports.relatorio_presidente_governador import AsyncRelatorioPresidenteGovernadorStore


@dataclass(frozen=True, slots=True)
class ReadPorts:
    boletim: AsyncBoletimReader
    names: AsyncMunicipalityNames
    power_store: AsyncRelatorioPoderStore
    cross_store: AsyncRelatorioPresidenteGovernadorStore
    seat_store: AsyncSeatVoteStore | None = None
    municipais: AsyncMunicipalResultsReader | None = None
    seat_estimates: AsyncEstimativaCadeiras | None = None
    municipal_2024: AsyncMunicipal2024 | None = None
