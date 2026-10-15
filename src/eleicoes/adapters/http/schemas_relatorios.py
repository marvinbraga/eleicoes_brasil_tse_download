"""JSON for the numbers behind the HTML reports."""

from typing import Self

from pydantic import BaseModel

from eleicoes.adapters.html_classe_governador import NOTES as CLASS_NOTES
from eleicoes.adapters.html_classe_governador import texto_regra
from eleicoes.adapters.html_perfis import NOTES as PROFILE_NOTES
from eleicoes.domain.classe_governador import ClassOutcome, ClassReport, RuleCut
from eleicoes.domain.grade import CelulaGrade, GradeDePoder, LinhaGrade
from eleicoes.domain.percentual import format_decimal, format_percent, format_ratio
from eleicoes.domain.perfis import ProfileCity, ProfileGroup, ProfileReport
from eleicoes.domain.presidente_governador import (
    CLASS_LABELS,
    CargoReading,
    ClassSlice,
    Composition,
    CrossReportView,
    PlaceReading,
    RankedParty,
)


class CelulaJson(BaseModel):
    partido: int
    votos_nominais: int
    votos_legenda: int
    comparecimento: int
    votos: int
    fatia: str

    @classmethod
    def from_domain(cls, cell: CelulaGrade) -> Self:
        return cls(
            partido=cell.partido,
            votos_nominais=cell.votos_nominais,
            votos_legenda=cell.votos_legenda,
            comparecimento=cell.comparecimento,
            votos=cell.votos,
            fatia=str(cell.fatia),
        )


class LinhaJson(BaseModel):
    codigo: str
    nome: str
    comparecimento: int
    celulas: list[CelulaJson]

    @classmethod
    def from_domain(cls, row: LinhaGrade) -> Self:
        return cls(
            codigo=row.codigo,
            nome=row.nome,
            comparecimento=row.comparecimento,
            celulas=[CelulaJson.from_domain(cell) for cell in row.celulas],
        )


class GradeJson(BaseModel):
    ano: int
    turno: int
    uf: str
    cargo: str
    nivel: str
    colunas: list[int]
    linhas: list[LinhaJson]

    @classmethod
    def from_domain(cls, grade: GradeDePoder) -> Self:
        return cls(
            ano=grade.ano,
            turno=grade.turno,
            uf=grade.uf,
            cargo=grade.cargo,
            nivel=grade.nivel,
            colunas=list(grade.colunas),
            linhas=[LinhaJson.from_domain(row) for row in grade.linhas],
        )


class RankedPartyJson(BaseModel):
    partido: int
    votos: int

    @classmethod
    def from_domain(cls, party: RankedParty) -> Self:
        return cls(partido=party.partido, votos=party.votos)


class CargoReadingJson(BaseModel):
    leader: RankedPartyJson | None
    runner_up: RankedPartyJson | None
    valid: int
    branco: int
    nulo: int

    @classmethod
    def from_domain(cls, reading: CargoReading) -> Self:
        leader = None if reading.leader is None else RankedPartyJson.from_domain(reading.leader)
        if reading.runner_up is None:
            runner = None
        else:
            runner = RankedPartyJson.from_domain(reading.runner_up)
        return cls(
            leader=leader,
            runner_up=runner,
            valid=reading.valid,
            branco=reading.branco,
            nulo=reading.nulo,
        )


class PlaceReadingJson(BaseModel):
    codigo: str
    nome: str
    classe: str
    margin: str
    presidente: CargoReadingJson
    governador: CargoReadingJson | None

    @classmethod
    def from_domain(cls, reading: PlaceReading) -> Self:
        governor = reading.governador
        return cls(
            codigo=reading.codigo,
            nome=reading.nome,
            classe=reading.classe,
            margin=str(reading.margin),
            presidente=CargoReadingJson.from_domain(reading.presidente),
            governador=None if governor is None else CargoReadingJson.from_domain(governor),
        )


class ClassSliceJson(BaseModel):
    classe: str
    cidades: int
    votos_validos: int

    @classmethod
    def from_domain(cls, item: ClassSlice) -> Self:
        return cls(classe=item.classe, cidades=item.cidades, votos_validos=item.votos_validos)


class CompositionJson(BaseModel):
    classes: list[ClassSliceJson]
    votos_validos: int
    branco: int
    nulo: int

    @classmethod
    def from_domain(cls, composition: Composition) -> Self:
        return cls(
            classes=[ClassSliceJson.from_domain(item) for item in composition.classes],
            votos_validos=composition.votos_validos,
            branco=composition.branco,
            nulo=composition.nulo,
        )


class UfPlacesJson(BaseModel):
    uf: str
    places: list[PlaceReadingJson]


class CrossReportJson(BaseModel):
    ano: int
    turno: int
    composition: CompositionJson
    municipalities: list[UfPlacesJson]
    states: list[PlaceReadingJson]
    regions: list[PlaceReadingJson]
    country: PlaceReadingJson | None

    @classmethod
    def from_domain(cls, view: CrossReportView) -> Self:
        country = None if view.country is None else PlaceReadingJson.from_domain(view.country)
        return cls(
            ano=view.ano,
            turno=view.turno,
            composition=CompositionJson.from_domain(view.composition),
            municipalities=[_uf_places(code, rows) for code, rows in view.municipalities],
            states=[PlaceReadingJson.from_domain(row) for row in view.states],
            regions=[PlaceReadingJson.from_domain(row) for row in view.regions],
            country=country,
        )


def _uf_places(code: str, rows: tuple[PlaceReading, ...]) -> UfPlacesJson:
    return UfPlacesJson(uf=code, places=[PlaceReadingJson.from_domain(row) for row in rows])


class GrupoPerfilJson(BaseModel):
    numero: int
    municipios: int
    comparecimento: int
    centro: list[str]

    @classmethod
    def from_domain(cls, group: ProfileGroup) -> Self:
        return cls(
            numero=group.numero,
            municipios=group.municipios,
            comparecimento=group.comparecimento,
            centro=[format_ratio(value) for value in group.center],
        )


class MunicipioPerfilJson(BaseModel):
    codigo: str
    nome: str
    grupo: int

    @classmethod
    def from_domain(cls, city: ProfileCity) -> Self:
        return cls(codigo=city.codigo, nome=city.nome, grupo=city.grupo)


class ProfileJson(BaseModel):
    ano: int
    turno: int
    cargo: str
    partidos: list[int]
    com_cedula: bool
    buscou: bool
    silhueta: str | None
    grupos: list[GrupoPerfilJson]
    municipios: list[MunicipioPerfilJson]
    notas: list[str]

    @classmethod
    def from_domain(cls, report: ProfileReport) -> Self:
        return cls(
            ano=report.ano,
            turno=report.turno,
            cargo=report.cargo,
            partidos=list(report.parties),
            com_cedula=report.with_ballot,
            buscou=report.searched,
            silhueta=_silhueta(report),
            grupos=[GrupoPerfilJson.from_domain(group) for group in report.groups],
            municipios=[MunicipioPerfilJson.from_domain(city) for city in report.cities],
            notas=list(PROFILE_NOTES),
        )


class LinhaClasseJson(BaseModel):
    classe: str
    rotulo: str
    apoio: int
    regras: list[str]

    @classmethod
    def from_domain(cls, row: ClassOutcome) -> Self:
        return cls(
            classe=row.classe,
            rotulo=CLASS_LABELS[row.classe],
            apoio=row.support,
            regras=_regras(row.rules),
        )


class ClassJson(BaseModel):
    ano: int
    turno: int
    acerto: str
    base: str
    linhas: list[LinhaClasseJson]
    retidas: list[str]
    notas: list[str]

    @classmethod
    def from_domain(cls, report: ClassReport) -> Self:
        return cls(
            ano=report.ano,
            turno=report.turno,
            acerto=format_percent(report.hit_rate),
            base=format_percent(report.baseline),
            linhas=[LinhaClasseJson.from_domain(row) for row in report.rows],
            retidas=[CLASS_LABELS[label] for label in report.held_out],
            notas=list(CLASS_NOTES),
        )


def _silhueta(report: ProfileReport) -> str | None:
    if report.searched and report.silhouette is not None:
        return format_decimal(report.silhouette)
    return None


def _regras(rules: tuple[tuple[RuleCut, ...], ...]) -> list[str]:
    if not rules:
        return [texto_regra(())]
    return [texto_regra(cuts) for cuts in rules]
