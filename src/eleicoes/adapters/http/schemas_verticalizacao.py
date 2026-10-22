"""JSON for the verticalization report. Shares as "42,19%", r and ratios as "0,6213"."""

from fractions import Fraction
from typing import Self

from pydantic import BaseModel

from eleicoes.domain.percentual import format_decimal, format_percent
from eleicoes.domain.verticalizacao import CARGOS, CargoShare
from eleicoes.domain.verticalizacao_coerencia import MINIMO_MUNICIPIOS, Coherence, ScatterPoint
from eleicoes.domain.verticalizacao_regras import (
    BASE_RELEVANTE,
    DIFERENCA,
    RAZAO,
    AbsentState,
    Comparison,
    UfComparison,
)
from eleicoes.domain.verticalizacao_relatorio import (
    NOTES,
    PartyVertical,
    ScatterView,
    VerticalView,
)


class CargoVerticalJson(BaseModel):
    cargo: str
    votos: int
    validos: int
    validos_onde: int
    fatia: str | None
    fatia_onde: str | None
    ufs_concorreu: int
    ufs_total: int

    @classmethod
    def from_domain(cls, share: CargoShare) -> Self:
        return cls(
            cargo=share.cargo,
            votos=share.votos,
            validos=share.validos,
            validos_onde=share.validos_onde,
            fatia=_percent(share.fatia),
            fatia_onde=_percent(share.fatia_onde),
            ufs_concorreu=share.ufs_concorreu,
            ufs_total=share.ufs_total,
        )


class CoerenciaJson(BaseModel):
    cargo_x: str
    cargo_y: str
    r: str | None
    municipios: int

    @classmethod
    def from_domain(cls, item: Coherence) -> Self:
        return cls(
            cargo_x=item.cargo_x,
            cargo_y=item.cargo_y,
            r=None if item.r is None else format_decimal(item.r),
            municipios=item.municipios,
        )


class UfComparacaoJson(BaseModel):
    uf: str
    majoritaria: str
    esperada: str
    classe: str

    @classmethod
    def from_domain(cls, row: UfComparison) -> Self:
        return cls(
            uf=row.uf,
            majoritaria=format_percent(row.majoritaria),
            esperada=format_percent(row.esperada),
            classe=row.classe,
        )


class SemCandidatoJson(BaseModel):
    uf: str
    proporcional: str

    @classmethod
    def from_domain(cls, item: AbsentState) -> Self:
        return cls(uf=item.uf, proporcional=format_percent(item.proporcional))


class ComparacaoJson(BaseModel):
    majoritario: str
    proporcional: str
    majoritaria: str | None
    esperada: str | None
    razao: str | None
    classe: str | None
    por_uf: list[UfComparacaoJson]
    sem_candidato: list[SemCandidatoJson]

    @classmethod
    def from_domain(cls, item: Comparison) -> Self:
        razao = item.razao
        return cls(
            majoritario=item.majoritario,
            proporcional=item.proporcional,
            majoritaria=_percent(item.majoritaria),
            esperada=_percent(item.esperada),
            razao=None if razao is None else format_decimal(float(razao)),
            classe=item.classe,
            por_uf=[UfComparacaoJson.from_domain(row) for row in item.por_uf],
            sem_candidato=[SemCandidatoJson.from_domain(row) for row in item.sem_candidato],
        )


class PartidoVerticalJson(BaseModel):
    partido: int
    perfil: str
    coerencia_mediana: str | None
    cargos: list[CargoVerticalJson]
    coerencia: list[CoerenciaJson]
    comparacoes: list[ComparacaoJson]

    @classmethod
    def from_domain(cls, party: PartyVertical) -> Self:
        mediana = party.coerencia_mediana
        return cls(
            partido=party.partido,
            perfil=party.perfil,
            coerencia_mediana=None if mediana is None else format_decimal(mediana),
            cargos=[CargoVerticalJson.from_domain(share) for share in party.cargos],
            coerencia=[CoerenciaJson.from_domain(item) for item in party.coerencia],
            comparacoes=[ComparacaoJson.from_domain(item) for item in party.comparacoes],
        )


class PontoJson(BaseModel):
    codigo: str
    nome: str
    uf: str
    comparecimento: int
    x: str
    y: str

    @classmethod
    def from_domain(cls, point: ScatterPoint) -> Self:
        return cls(
            codigo=point.codigo,
            nome=point.nome,
            uf=point.uf,
            comparecimento=point.comparecimento,
            x=format_percent(point.x),
            y=format_percent(point.y),
        )


class DispersaoJson(BaseModel):
    partido: int
    cargo_x: str
    cargo_y: str
    coerencia: CoerenciaJson
    pontos: list[PontoJson]

    @classmethod
    def from_domain(cls, view: ScatterView) -> Self:
        return cls(
            partido=view.partido,
            cargo_x=view.cargo_x,
            cargo_y=view.cargo_y,
            coerencia=CoerenciaJson.from_domain(view.coerencia),
            pontos=[PontoJson.from_domain(point) for point in view.pontos],
        )


class LimiaresJson(BaseModel):
    razao: str
    diferenca: str
    base_relevante: str
    minimo_municipios: int

    @classmethod
    def from_domain(cls) -> Self:
        return cls(
            razao=str(RAZAO),
            diferenca=format_percent(DIFERENCA),
            base_relevante=format_percent(BASE_RELEVANTE),
            minimo_municipios=MINIMO_MUNICIPIOS,
        )


class VerticalJson(BaseModel):
    ano: int
    turno: int
    uf: str | None
    municipios: int
    sem_uf: int
    cargos: list[str]
    limiares: LimiaresJson
    partidos: list[PartidoVerticalJson]
    dispersao: DispersaoJson
    notas: list[str]

    @classmethod
    def from_domain(cls, view: VerticalView) -> Self:
        report = view.report
        return cls(
            ano=report.ano,
            turno=report.turno,
            uf=report.uf,
            municipios=report.municipios,
            sem_uf=report.sem_uf,
            cargos=list(CARGOS),
            limiares=LimiaresJson.from_domain(),
            partidos=[PartidoVerticalJson.from_domain(party) for party in report.partidos],
            dispersao=DispersaoJson.from_domain(view.dispersao),
            notas=list(NOTES),
        )


def _percent(value: Fraction | None) -> str | None:
    if value is None:
        return None
    return format_percent(value)
