"""JSON for the numbers behind the HTML reports."""

from datetime import datetime
from typing import Self

from pydantic import BaseModel

from eleicoes.adapters.html_classe_governador import NOTES as CLASS_NOTES
from eleicoes.adapters.html_classe_governador import texto_regra
from eleicoes.adapters.html_perfis import NOTES as PROFILE_NOTES
from eleicoes.domain.classe_governador import ClassOutcome, ClassReport, RuleCut, UfScore
from eleicoes.domain.errors import (
    comando_municipais_2024,
    comando_relatorio_cadeiras,
    comando_relatorio_poder,
)
from eleicoes.domain.forca import (
    BaseCadeiras,
    BaseMunicipal,
    BaseMunicipal2024,
    BaseRecorte,
    BlocoCadeiras,
    BlocoMunicipal2024,
    ForcaUnidade,
    Municipal,
    PlacarForca,
    Recorte,
)
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
    recall: str

    @classmethod
    def from_domain(cls, row: ClassOutcome) -> Self:
        return cls(
            classe=row.classe,
            rotulo=CLASS_LABELS[row.classe],
            apoio=row.support,
            regras=_regras(row.rules),
            recall=format_percent(row.recall),
        )


class AcertoUfJson(BaseModel):
    uf: str
    municipios: int
    acerto: str

    @classmethod
    def from_domain(cls, score: UfScore) -> Self:
        return cls(uf=score.uf, municipios=score.municipios, acerto=format_percent(score.hit_rate))


class ClassJson(BaseModel):
    ano: int
    turno: int
    acerto: str
    base: str
    base_lider: str
    f1_macro: str
    por_uf: list[AcertoUfJson]
    sem_uf: int
    abaixo_da_base: bool
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
            base_lider=format_percent(report.leader_baseline),
            f1_macro=format_decimal(float(report.macro_f1)),
            por_uf=[AcertoUfJson.from_domain(score) for score in report.by_uf],
            sem_uf=report.without_uf,
            abaixo_da_base=report.below_baseline,
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


class PresencaJson(BaseModel):
    limiar: int
    municipios: int


class MunicipalForcaJson(BaseModel):
    lidera: int
    validos_liderados: int
    presenca: list[PresencaJson]

    @classmethod
    def from_domain(cls, item: Municipal) -> Self:
        presenca = [PresencaJson(limiar=p.limiar, municipios=p.municipios) for p in item.presenca]
        return cls(
            lidera=item.lidera,
            validos_liderados=item.validos_liderados,
            presenca=presenca,
        )


class BaseMunicipalJson(BaseModel):
    municipios: int
    validos: int
    empates: int

    @classmethod
    def from_domain(cls, base: BaseMunicipal) -> Self:
        return cls(municipios=base.municipios, validos=base.validos, empates=base.empates)


class BaseCadeirasJson(BaseModel):
    camara: int
    senado: int
    governadores: int
    assembleias: int

    @classmethod
    def from_domain(cls, base: BaseCadeiras) -> Self:
        return cls(
            camara=base.camara,
            senado=base.senado,
            governadores=base.governadores,
            assembleias=base.assembleias,
        )


def _base_cadeiras(base: BaseCadeiras | None) -> BaseCadeirasJson | None:
    return None if base is None else BaseCadeirasJson.from_domain(base)


class BaseMunicipal2024Json(BaseModel):
    municipios: int
    com_prefeito: int
    eleitorado: int
    vereadores: int

    @classmethod
    def from_domain(cls, base: BaseMunicipal2024) -> Self:
        return cls(
            municipios=base.municipios,
            com_prefeito=base.com_prefeito,
            eleitorado=base.eleitorado,
            vereadores=base.vereadores,
        )


def _base_2024(base: BaseMunicipal2024 | None) -> BaseMunicipal2024Json | None:
    return None if base is None else BaseMunicipal2024Json.from_domain(base)


class BaseForcaJson(BaseModel):
    validos_presidente: int | None
    validos_deputado_federal: int | None
    validos_deputado_estadual: int | None
    ufs_deputado_estadual: int | None
    municipal: BaseMunicipalJson | None
    cadeiras: BaseCadeirasJson | None
    municipal_2024: BaseMunicipal2024Json | None

    @classmethod
    def from_domain(cls, base: BaseRecorte) -> Self:
        found = base.municipal
        municipal = None if found is None else BaseMunicipalJson.from_domain(found)
        return cls(
            validos_presidente=base.validos_presidente,
            validos_deputado_federal=base.validos_deputado_federal,
            validos_deputado_estadual=base.validos_deputado_estadual,
            ufs_deputado_estadual=base.ufs_deputado_estadual,
            municipal=municipal,
            cadeiras=_base_cadeiras(base.cadeiras),
            municipal_2024=_base_2024(base.municipal_2024),
        )


class UnidadeForcaJson(BaseModel):
    chave: str
    tipo: str
    nome: str | None
    partidos: list[int]
    presidente: int | None
    deputado_federal: int | None
    deputado_estadual: int | None
    ufs_lider_estadual: int | None
    municipal: MunicipalForcaJson | None
    camara: int | None
    senado: int | None
    governador_1t: int | None
    governador_2t: int | None
    assembleia: int | None
    prefeitos: int | None
    eleitorado_governado: int | None
    vereadores: int | None
    legenda_federal: int | None
    legenda_estadual: int | None

    @classmethod
    def from_domain(cls, item: ForcaUnidade) -> Self:
        found = item.municipal
        municipal = None if found is None else MunicipalForcaJson.from_domain(found)
        seats = item.cadeiras
        de_2024 = item.municipal_2024
        return cls(
            chave=item.chave,
            tipo=item.tipo,
            nome=item.nome,
            partidos=list(item.partidos),
            presidente=item.presidente,
            deputado_federal=item.deputado_federal,
            deputado_estadual=item.deputado_estadual,
            ufs_lider_estadual=item.ufs_lider_estadual,
            municipal=municipal,
            camara=None if seats is None else seats.camara,
            senado=None if seats is None else seats.senado,
            governador_1t=None if seats is None else seats.governador_1t,
            governador_2t=None if seats is None else seats.governador_2t,
            assembleia=None if seats is None else seats.assembleia,
            prefeitos=None if de_2024 is None else de_2024.prefeitos,
            eleitorado_governado=None if de_2024 is None else de_2024.eleitorado_governado,
            vereadores=None if de_2024 is None else de_2024.vereadores,
            legenda_federal=item.legenda_federal,
            legenda_estadual=item.legenda_estadual,
        )


class RecorteForcaJson(BaseModel):
    codigo: str
    nome: str
    base: BaseForcaJson
    unidades: list[UnidadeForcaJson]
    federadas: list[UnidadeForcaJson]
    base_federada: BaseForcaJson | None

    @classmethod
    def from_domain(cls, recorte: Recorte) -> Self:
        federada = recorte.base_federada
        return cls(
            codigo=recorte.codigo,
            nome=recorte.nome,
            base=BaseForcaJson.from_domain(recorte.base),
            unidades=[UnidadeForcaJson.from_domain(item) for item in recorte.unidades],
            federadas=[UnidadeForcaJson.from_domain(item) for item in recorte.federadas],
            base_federada=None if federada is None else BaseForcaJson.from_domain(federada),
        )


class FaltandoJson(BaseModel):
    cargo: str
    comando: str


class BlocoCadeirasJson(BaseModel):
    disponivel: bool
    comando: str | None
    totais: BaseCadeirasJson | None

    @classmethod
    def from_domain(cls, bloco: BlocoCadeiras) -> Self:
        return cls(
            disponivel=bloco.disponivel,
            comando=None if bloco.disponivel else comando_relatorio_cadeiras(),
            totais=_base_cadeiras(bloco.totais),
        )


class BlocoMunicipal2024Json(BaseModel):
    disponivel: bool
    comando: str | None
    data_corte: datetime | None
    totais: BaseMunicipal2024Json | None

    @classmethod
    def from_domain(cls, bloco: BlocoMunicipal2024) -> Self:
        return cls(
            disponivel=bloco.disponivel,
            comando=None if bloco.disponivel else comando_municipais_2024(),
            data_corte=bloco.data_corte,
            totais=_base_2024(bloco.totais),
        )


class ForcaJson(BaseModel):
    ano: int
    turno: int
    cargo_referencia: str
    limiares: list[int]
    faltando: list[FaltandoJson]
    pais: RecorteForcaJson
    ufs: list[RecorteForcaJson]
    cadeiras: BlocoCadeirasJson | None
    municipal_2024: BlocoMunicipal2024Json | None

    @classmethod
    def from_domain(cls, placar: PlacarForca) -> Self:
        faltando = [
            FaltandoJson(cargo=cargo, comando=comando_relatorio_poder(cargo))
            for cargo in placar.faltando
        ]
        return cls(
            ano=placar.ano,
            turno=placar.turno,
            cargo_referencia=placar.cargo_referencia,
            limiares=list(placar.limiares),
            faltando=faltando,
            pais=RecorteForcaJson.from_domain(placar.pais),
            ufs=[RecorteForcaJson.from_domain(item) for item in placar.ufs],
            cadeiras=None
            if placar.cadeiras is None
            else BlocoCadeirasJson.from_domain(placar.cadeiras),
            municipal_2024=None
            if placar.municipal_2024 is None
            else BlocoMunicipal2024Json.from_domain(placar.municipal_2024),
        )
