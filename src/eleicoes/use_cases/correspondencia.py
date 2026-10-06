"""Correspondence consultations. Each class is one question, not a shared facade."""

from eleicoes.domain.correspondencia import (
    Contingencia,
    CorrespondenciasNovas,
    Indicio,
    MapaDeIndicios,
    MudancaGeracao,
    ResumoUf,
    Secao,
    StatusCorrespondencia,
    nomes_equivalentes,
)
from eleicoes.domain.values import Uf
from eleicoes.ports.correspondencia import CorrespondenciaReader


class ListSectionsOfMunicipality:
    def __init__(self, reader: CorrespondenciaReader) -> None:
        self._reader = reader

    def execute(self, uf: str, municipio: str) -> tuple[Secao, ...]:
        code = Uf(uf).code
        rows = self._reader.secoes(code, None)
        return tuple(row for row in rows if nomes_equivalentes(row.municipio, municipio))


class ListAlteredSections:
    def __init__(self, reader: CorrespondenciaReader) -> None:
        self._reader = reader

    def execute(self, uf: str | None = None) -> tuple[Secao, ...]:
        return self._reader.secoes(_optional_uf(uf), StatusCorrespondencia.ALTERADA)


class ListNewCorrespondences:
    def __init__(self, reader: CorrespondenciaReader) -> None:
        self._reader = reader

    def execute(self, uf: str | None = None) -> CorrespondenciasNovas:
        code = _optional_uf(uf)
        return CorrespondenciasNovas(
            secoes=self._reader.secoes(code, StatusCorrespondencia.NOVA),
            contingencias=self._reader.contingencias(code, StatusCorrespondencia.NOVA),
        )


class SummarizeByUf:
    def __init__(self, reader: CorrespondenciaReader) -> None:
        self._reader = reader

    def execute(self) -> tuple[ResumoUf, ...]:
        return tuple(sorted(self._reader.resumos(), key=lambda item: item.uf))


class ListContingencies:
    def __init__(self, reader: CorrespondenciaReader) -> None:
        self._reader = reader

    def execute(self, uf: str, municipio: str | None = None) -> tuple[Contingencia, ...]:
        rows = self._reader.contingencias(Uf(uf).code, None)
        if municipio is None:
            return rows
        return tuple(row for row in rows if nomes_equivalentes(row.municipio, municipio))


class ListGenerationChanges:
    def __init__(self, reader: CorrespondenciaReader) -> None:
        self._reader = reader

    def execute(self, uf: str | None = None) -> tuple[MudancaGeracao, ...]:
        return self._reader.mudancas(_optional_uf(uf))


class TraceSectionMedia:
    def __init__(self, reader: CorrespondenciaReader) -> None:
        self._reader = reader

    def execute(self, uf: str, municipio: str, zona: int, secao: int) -> tuple[Secao, ...]:
        rows = self._reader.geracoes(Uf(uf).code, zona, secao)
        matched = [row for row in rows if nomes_equivalentes(row.municipio, municipio)]
        return tuple(sorted(matched, key=lambda row: row.geracao_em))


class ListarIndicios:
    def __init__(self, reader: CorrespondenciaReader) -> None:
        self._reader = reader
        self._mapa = MapaDeIndicios()

    def execute(self, uf: str | None = None) -> tuple[Indicio, ...]:
        code = _optional_uf(uf)
        return self._mapa.avaliar(
            self._reader.projecoes(code),
            self._reader.projecoes_contingencia(code),
        )


def _optional_uf(uf: str | None) -> str | None:
    if uf is None:
        return None
    return Uf(uf).code
