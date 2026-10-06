"""Correspondence consultations. Each function builds one use case."""

import os
from collections.abc import Callable, Mapping
from typing import TypeVar

from dotenv import load_dotenv

from eleicoes.composition.correspondencia import build_correspondencia_reader
from eleicoes.domain.correspondencia import (
    Contingencia,
    CorrespondenciasNovas,
    Indicio,
    MudancaGeracao,
    ResumoUf,
    Secao,
)
from eleicoes.ports.correspondencia import CorrespondenciaReader
from eleicoes.use_cases.correspondencia import (
    ListAlteredSections,
    ListarIndicios,
    ListContingencies,
    ListGenerationChanges,
    ListNewCorrespondences,
    ListSectionsOfMunicipality,
    SummarizeByUf,
    TraceSectionMedia,
)

_T = TypeVar("_T")


def secoes_do_municipio(
    uf: str,
    municipio: str,
    *,
    reader: CorrespondenciaReader | None = None,
) -> tuple[Secao, ...]:
    return _using(reader, lambda opened: ListSectionsOfMunicipality(opened).execute(uf, municipio))


def secoes_alteradas(
    uf: str | None = None,
    *,
    reader: CorrespondenciaReader | None = None,
) -> tuple[Secao, ...]:
    return _using(reader, lambda opened: ListAlteredSections(opened).execute(uf))


def correspondencias_novas(
    uf: str | None = None,
    *,
    reader: CorrespondenciaReader | None = None,
) -> CorrespondenciasNovas:
    return _using(reader, lambda opened: ListNewCorrespondences(opened).execute(uf))


def resumo_por_uf(*, reader: CorrespondenciaReader | None = None) -> tuple[ResumoUf, ...]:
    return _using(reader, lambda opened: SummarizeByUf(opened).execute())


def contingencias(
    uf: str,
    municipio: str | None = None,
    *,
    reader: CorrespondenciaReader | None = None,
) -> tuple[Contingencia, ...]:
    return _using(reader, lambda opened: ListContingencies(opened).execute(uf, municipio))


def mudancas_entre_geracoes(
    uf: str | None = None,
    *,
    reader: CorrespondenciaReader | None = None,
) -> tuple[MudancaGeracao, ...]:
    return _using(reader, lambda opened: ListGenerationChanges(opened).execute(uf))


def rastro_da_midia(
    uf: str,
    municipio: str,
    zona: int,
    secao: int,
    *,
    reader: CorrespondenciaReader | None = None,
) -> tuple[Secao, ...]:
    return _using(
        reader,
        lambda opened: TraceSectionMedia(opened).execute(uf, municipio, zona, secao),
    )


def indicios(
    uf: str | None = None,
    *,
    reader: CorrespondenciaReader | None = None,
) -> tuple[Indicio, ...]:
    return _using(reader, lambda opened: ListarIndicios(opened).execute(uf))


def _using(reader: CorrespondenciaReader | None, work: Callable[[CorrespondenciaReader], _T]) -> _T:
    if reader is not None:
        return work(reader)
    opened = build_correspondencia_reader(_environment())
    try:
        return work(opened)
    finally:
        opened.close()


def _environment() -> Mapping[str, str]:
    load_dotenv()
    return os.environ
