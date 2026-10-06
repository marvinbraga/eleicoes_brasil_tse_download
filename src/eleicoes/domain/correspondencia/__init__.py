"""Correspondence between the expected urn and the voting section.

This package does not count votes. Apuração, when it exists, will be another
domain with its own objects.
"""

from eleicoes.domain.correspondencia.indicio import Gravidade, Indicio, MapaDeIndicios
from eleicoes.domain.correspondencia.nomes import nomes_equivalentes
from eleicoes.domain.correspondencia.projecao import ProjecaoContingencia, ProjecaoSecao
from eleicoes.domain.correspondencia.records import (
    Contingencia,
    CorrespondenciasNovas,
    MudancaGeracao,
    Referencia,
    ResumoUf,
    Secao,
)
from eleicoes.domain.correspondencia.statistics import modified_z
from eleicoes.domain.correspondencia.status import StatusCorrespondencia

__all__ = [
    "Contingencia",
    "CorrespondenciasNovas",
    "Gravidade",
    "Indicio",
    "MapaDeIndicios",
    "MudancaGeracao",
    "ProjecaoContingencia",
    "ProjecaoSecao",
    "Referencia",
    "ResumoUf",
    "Secao",
    "StatusCorrespondencia",
    "modified_z",
    "nomes_equivalentes",
]
