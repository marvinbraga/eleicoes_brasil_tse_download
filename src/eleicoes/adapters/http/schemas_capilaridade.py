"""JSON of the capillarity report. Exact ratios go as str(Fraction) next to ready text."""

from collections.abc import Callable
from fractions import Fraction
from typing import Final, Self

from pydantic import BaseModel

from eleicoes.domain.capilaridade import (
    PAIS,
    PRESENCA,
    UF,
    Band,
    PartyMetrics,
    PlaceStrength,
    Scope,
    Share,
    Subdivision,
)
from eleicoes.domain.capilaridade_classe import (
    CAPITAIS_VEZES,
    MIN_MUNICIPIOS,
    POUCO_VOTO,
    POUCOS_PARTE,
    POUCOS_VEZES,
    REGIONAL_PARTE,
    REGIONAL_VEZES,
    CapillarityReport,
    CapillarityView,
    ClassifiedParty,
    PartySummary,
    summarize,
)
from eleicoes.domain.percentual import format_integer, format_percent, round_half_up

NOTES: Final[tuple[str, ...]] = (
    "Os votos do partido somam votos nominais e de legenda; "
    "votos válidos não incluem brancos e nulos.",
    "Cada partido é medido só nas UFs onde recebeu voto, "
    "para não confundir falta de candidato com fraqueza.",
    "O exterior fica fora do cálculo; os municípios são os que têm células gravadas para o cargo.",
    "Os limites das classes foram calibrados com os dados de 2026 e podem mudar.",
)
_HUNDREDTHS: Final = 100
_TEN_THOUSANDTHS: Final = 10_000
_ONE_TIMES_PREFIX: Final = "1,"
_FIXED_LABELS: Final[dict[str, str]] = {
    "pouco_voto": "Pouco voto",
    "sem_base": "Poucos municípios para classificar",
    "poucos_municipios": "Concentrado em poucos municípios",
}
_SPREAD_LABELS: Final[dict[str, str]] = {
    PAIS: "Nacional / espalhado",
    "regiao": "Espalhado pela região",
    UF: "Espalhado pelo estado",
}


def format_times(value: Fraction) -> str:
    """Two decimals, half-up, Brazilian comma: 7/4 -> "1,75"."""
    whole, cents = divmod(round_half_up(value * _HUNDREDTHS), _HUNDREDTHS)
    return f"{format_integer(whole)},{cents:02d}"


def _four_places(value: Fraction) -> str:
    whole, rest = divmod(round_half_up(value * _TEN_THOUSANDTHS), _TEN_THOUSANDTHS)
    return f"{format_integer(whole)},{rest:04d}"


def _times_word(formatted: str) -> str:
    return "vez" if formatted.startswith(_ONE_TIMES_PREFIX) else "vezes"


def rotulo_classe(classe: str, scope: Scope, subdivisao: Subdivision | None) -> str:
    fixed = _FIXED_LABELS.get(classe)
    if fixed is not None:
        return fixed
    if classe == "capitais":
        return "Concentrado na capital" if scope.tipo == UF else "Concentrado nas capitais"
    if classe == "regional":
        return _regional_label(scope, subdivisao)
    return _SPREAD_LABELS[scope.tipo]


def _regional_label(scope: Scope, subdivisao: Subdivision | None) -> str:
    if subdivisao is None:
        return "Regional"
    if scope.tipo == PAIS:
        return f"Regional ({subdivisao.nome})"
    return f"Concentrado em uma UF ({subdivisao.nome})"


def _weighted(share: Share) -> tuple[str, str, str]:
    vezes = format_times(share.vezes)
    return format_percent(share.parte), f"{vezes} {_times_word(vezes)}", _electorate_text(share)


def _electorate_text(share: Share) -> str:
    return format_percent(share.eleitorado)


def _motivo_pouco_voto(party: ClassifiedParty) -> str:
    fatia = format_percent(party.metrics.fatia)
    limite = format_percent(POUCO_VOTO)
    return f"Teve {fatia} dos votos válidos onde recebeu voto, abaixo de {limite}."


def _motivo_sem_base(party: ClassifiedParty) -> str:
    municipios = format_integer(party.metrics.municipios)
    minimo = format_integer(MIN_MUNICIPIOS)
    return f"Só {municipios} municípios com voto; são precisos {minimo} para classificar."


def _motivo_capitais(party: ClassifiedParty) -> str:
    capitals = party.metrics.capitais
    if capitals is None:
        return _motivo_espalhado(party)
    parte, vezes, eleitorado = _weighted(capitals)
    return (
        f"As capitais deram {parte} dos votos do partido, "
        f"{vezes} o peso delas no eleitorado ({eleitorado})."
    )


def _motivo_regional(party: ClassifiedParty) -> str:
    found = party.classificacao.subdivisao
    if found is None:
        return _motivo_espalhado(party)
    parte, vezes, eleitorado = _weighted(found.share)
    return (
        f"{found.nome} deu {parte} dos votos do partido, "
        f"{vezes} o peso no eleitorado ({eleitorado})."
    )


def _motivo_poucos(party: ClassifiedParty) -> str:
    top = party.metrics.top10
    parte, vezes, eleitorado = _weighted(top)
    return (
        f"Os {format_integer(top.municipios)} municípios onde é mais forte deram {parte} "
        f"dos votos, {vezes} o peso deles no eleitorado ({eleitorado})."
    )


def _motivo_espalhado(party: ClassifiedParty) -> str:
    top = party.metrics.top10
    return (
        "Nenhuma regra de concentração se aplicou. "
        f"Os {format_integer(top.municipios)} municípios onde é mais forte deram "
        f"{format_percent(top.parte)} dos votos e têm {_electorate_text(top)} do eleitorado."
    )


_MOTIVOS: Final[dict[str, Callable[[ClassifiedParty], str]]] = {
    "pouco_voto": _motivo_pouco_voto,
    "sem_base": _motivo_sem_base,
    "capitais": _motivo_capitais,
    "regional": _motivo_regional,
    "poucos_municipios": _motivo_poucos,
    "espalhado": _motivo_espalhado,
}


def motivo(party: ClassifiedParty) -> str:
    return _MOTIVOS[party.classificacao.classe](party)


class RecorteJson(BaseModel):
    tipo: str
    codigo: str
    nome: str


class LimitesJson(BaseModel):
    presenca: str
    pouco_voto: str
    minimo_municipios: int
    capitais_vezes: str
    regional_parte: str
    regional_vezes: str
    poucos_parte: str
    poucos_vezes: str

    @classmethod
    def current(cls) -> Self:
        return cls(
            presenca=format_percent(PRESENCA),
            pouco_voto=format_percent(POUCO_VOTO),
            minimo_municipios=MIN_MUNICIPIOS,
            capitais_vezes=format_times(CAPITAIS_VEZES),
            regional_parte=format_percent(REGIONAL_PARTE),
            regional_vezes=format_times(REGIONAL_VEZES),
            poucos_parte=format_percent(POUCOS_PARTE),
            poucos_vezes=format_times(POUCOS_VEZES),
        )


class ParteJson(BaseModel):
    municipios: int
    votos: int
    parte: str
    parte_texto: str
    eleitorado: str
    eleitorado_texto: str
    vezes: str

    @classmethod
    def from_domain(cls, share: Share) -> Self:
        return cls(
            municipios=share.municipios,
            votos=share.votos,
            parte=str(share.parte),
            parte_texto=format_percent(share.parte),
            eleitorado=str(share.eleitorado),
            eleitorado_texto=format_percent(share.eleitorado),
            vezes=format_times(share.vezes),
        )


class SubdivisaoJson(ParteJson):
    codigo: str
    nome: str

    @classmethod
    def from_subdivision(cls, item: Subdivision) -> Self:
        base = ParteJson.from_domain(item.share)
        return cls(codigo=item.codigo, nome=item.nome, **base.model_dump())


class PresencaJson(BaseModel):
    municipios: int
    parte: str
    parte_texto: str

    @classmethod
    def from_domain(cls, metrics: PartyMetrics) -> Self:
        return cls(
            municipios=metrics.presenca,
            parte=str(metrics.presenca_parte),
            parte_texto=format_percent(metrics.presenca_parte),
        )


class FaixaJson(BaseModel):
    chave: str
    municipios: int
    votos_validos: int
    votos: int

    @classmethod
    def from_domain(cls, band: Band) -> Self:
        return cls(
            chave=band.chave,
            municipios=band.municipios,
            votos_validos=band.validos,
            votos=band.votos,
        )


class LugarJson(BaseModel):
    codigo: str
    nome: str
    votos: int
    votos_validos: int
    fatia: str
    fatia_texto: str

    @classmethod
    def from_domain(cls, place: PlaceStrength) -> Self:
        return cls(
            codigo=place.codigo,
            nome=place.nome,
            votos=place.votos,
            votos_validos=place.validos,
            fatia=str(place.fatia),
            fatia_texto=format_percent(place.fatia),
        )


class PartidoCapilaridadeJson(BaseModel):
    partido: int
    votos: int
    votos_validos: int
    votos_validos_recorte: int
    fatia: str
    fatia_texto: str
    fatia_recorte_texto: str
    ufs_com_voto: int
    municipios: int
    indice: str
    indice_texto: str
    indice_100: int
    top10: ParteJson
    presenca: PresencaJson
    capitais: ParteJson | None
    subdivisoes: list[SubdivisaoJson]
    faixas: list[FaixaJson]
    fortes: list[LugarJson]
    maiores: list[LugarJson]
    classe: str
    rotulo_classe: str
    motivo: str

    @classmethod
    def from_domain(cls, party: ClassifiedParty, scope: Scope) -> Self:
        metrics = party.metrics
        capitals = metrics.capitais
        return cls(
            partido=metrics.partido,
            votos=metrics.votos,
            votos_validos=metrics.validos,
            votos_validos_recorte=metrics.validos_recorte,
            fatia=str(metrics.fatia),
            fatia_texto=format_percent(metrics.fatia),
            fatia_recorte_texto=format_percent(metrics.fatia_recorte),
            ufs_com_voto=metrics.ufs_com_voto,
            municipios=metrics.municipios,
            indice=str(metrics.indice),
            indice_texto=_four_places(metrics.indice),
            indice_100=round_half_up(metrics.indice * _HUNDREDTHS),
            top10=ParteJson.from_domain(metrics.top10),
            presenca=PresencaJson.from_domain(metrics),
            capitais=None if capitals is None else ParteJson.from_domain(capitals),
            subdivisoes=[SubdivisaoJson.from_subdivision(item) for item in metrics.subdivisoes],
            faixas=[FaixaJson.from_domain(band) for band in metrics.faixas],
            fortes=[LugarJson.from_domain(place) for place in metrics.fortes],
            maiores=[LugarJson.from_domain(place) for place in metrics.maiores],
            classe=party.classificacao.classe,
            rotulo_classe=_label_of(party, scope),
            motivo=motivo(party),
        )


def _label_of(party: ClassifiedParty, scope: Scope) -> str:
    found = party.classificacao
    return rotulo_classe(found.classe, scope, found.subdivisao)


class ResumoCapilaridadeJson(BaseModel):
    partido: int
    votos: int
    fatia: str
    fatia_texto: str
    indice: str
    indice_100: int
    presenca: str
    presenca_texto: str
    ufs_com_voto: int
    classe: str
    rotulo_classe: str

    @classmethod
    def from_domain(cls, item: PartySummary, rotulo: str) -> Self:
        return cls(
            partido=item.partido,
            votos=item.votos,
            fatia=str(item.fatia),
            fatia_texto=format_percent(item.fatia),
            indice=str(item.indice),
            indice_100=item.indice_100,
            presenca=str(item.presenca),
            presenca_texto=format_percent(item.presenca),
            ufs_com_voto=item.ufs_com_voto,
            classe=item.classe,
            rotulo_classe=rotulo,
        )


class CapilaridadeJson(BaseModel):
    ano: int
    turno: int
    cargo: str
    recorte: RecorteJson
    municipios: int
    ufs: int
    sem_validos: int
    votos_validos: int
    exterior: int
    limites: LimitesJson
    partidos: list[PartidoCapilaridadeJson]
    resumo: list[ResumoCapilaridadeJson]
    notas: list[str]

    @classmethod
    def from_domain(cls, report: CapillarityReport, view: CapillarityView) -> Self:
        scope = view.scope
        resumo = zip(summarize(view), view.partidos, strict=True)
        return cls(
            ano=report.ano,
            turno=report.turno,
            cargo=report.cargo,
            recorte=RecorteJson(tipo=scope.tipo, codigo=scope.codigo, nome=scope.nome),
            municipios=view.municipios,
            ufs=view.ufs,
            sem_validos=view.sem_validos,
            votos_validos=view.validos,
            exterior=report.exterior,
            limites=LimitesJson.current(),
            partidos=[PartidoCapilaridadeJson.from_domain(item, scope) for item in view.partidos],
            resumo=[
                ResumoCapilaridadeJson.from_domain(item, _label_of(party, scope))
                for item, party in resumo
            ],
            notas=list(NOTES),
        )
