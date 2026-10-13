"""Mesh read port. Later tasks import these names from this module."""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol

from eleicoes.domain.mapa import Marca, PonteTseIbge


@dataclass(frozen=True, slots=True)
class Manifesto:
    municipios_objeto: str
    ufs_objeto: str
    paises_objeto: str
    brasil_id: str


@dataclass(frozen=True, slots=True)
class MalhaCarregada:
    manifesto: Manifesto
    municipios: str
    ufs: str
    paises: str
    ol_js: str
    ol_css: str
    topojson_js: str
    ponte: PonteTseIbge
    marcas: Mapping[int, Marca]
    codigos_municipio: frozenset[str]
    codigos_uf: frozenset[str]
    ids_pais: frozenset[str]


class MeshAssets(Protocol):
    def load(self) -> MalhaCarregada: ...
