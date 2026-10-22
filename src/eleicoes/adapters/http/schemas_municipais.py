"""JSON de GET /relatorios/dados/municipais-2024. As notas ficam aqui, em português."""

from datetime import date, datetime
from typing import Self

from pydantic import BaseModel

from eleicoes.domain.forca_municipal import (
    MunicipalReport,
    MunicipalTotals,
    PartyStrength,
    StoredCouncil,
    StoredMayor,
    StoredMunicipality,
)
from eleicoes.domain.partido_equivalencia import (
    VERSAO_EQUIVALENCIA,
    Correspondencia,
    equivalente_2026,
)


class TotaisMunicipaisJson(BaseModel):
    municipios: int
    com_prefeito: int
    sem_prefeito: int
    suplementares: int
    eleitorado: int
    vereadores: int
    vagas_vereador: int
    divergencias_vagas: int

    @classmethod
    def from_domain(cls, item: MunicipalTotals) -> Self:
        return cls(
            municipios=item.municipios,
            com_prefeito=item.com_prefeito,
            sem_prefeito=item.sem_prefeito,
            suplementares=item.suplementares,
            eleitorado=item.eleitorado,
            vereadores=item.vereadores,
            vagas_vereador=item.vagas_vereador,
            divergencias_vagas=item.divergencias_vagas,
        )


class PartidoMunicipalJson(BaseModel):
    numero: int
    sigla_2024: str
    numero_2026: int | None
    sigla_2026: str | None
    equivalencia: str
    nota: str
    prefeitos: int
    eleitorado_governado: int
    vereadores: int
    municipios_com_vereador: int

    @classmethod
    def from_domain(cls, item: PartyStrength) -> Self:
        equivalente = item.equivalente
        return cls(
            numero=equivalente.numero_2024,
            sigla_2024=equivalente.sigla_2024,
            numero_2026=equivalente.numero_2026,
            sigla_2026=equivalente.sigla_2026,
            equivalencia=equivalente.correspondencia.value,
            nota=equivalente.nota,
            prefeitos=item.prefeitos,
            eleitorado_governado=item.eleitorado_governado,
            vereadores=item.vereadores,
            municipios_com_vereador=item.municipios_com_vereador,
        )


class PrefeitoMunicipalJson(BaseModel):
    numero_partido: int
    sigla_2024: str
    sigla_2026: str | None
    nome_urna: str
    turno: int
    suplementar: bool
    data_eleicao: date

    @classmethod
    def from_domain(cls, item: StoredMayor) -> Self:
        return cls(
            numero_partido=item.partido,
            sigla_2024=item.sigla,
            sigla_2026=equivalente_2026(item.partido, item.sigla).sigla_2026,
            nome_urna=item.nome_urna,
            turno=item.turno,
            suplementar=item.suplementar,
            data_eleicao=item.data_eleicao,
        )


class VereadoresMunicipioJson(BaseModel):
    numero: int
    sigla_2024: str
    eleitos: int

    @classmethod
    def from_domain(cls, item: StoredCouncil) -> Self:
        return cls(numero=item.partido, sigla_2024=item.sigla, eleitos=item.eleitos)


class MunicipioMunicipalJson(BaseModel):
    uf: str
    codigo_tse: str
    nome: str
    eleitorado: int
    prefeito: PrefeitoMunicipalJson | None
    vereadores: list[VereadoresMunicipioJson]

    @classmethod
    def from_domain(cls, item: StoredMunicipality) -> Self:
        prefeito = item.prefeito
        return cls(
            uf=item.uf,
            codigo_tse=item.ue,
            nome=item.nome,
            eleitorado=item.eleitorado,
            prefeito=None if prefeito is None else PrefeitoMunicipalJson.from_domain(prefeito),
            vereadores=[VereadoresMunicipioJson.from_domain(seat) for seat in item.vereadores],
        )


class MunicipaisJson(BaseModel):
    ano: int
    uf: str | None
    data_corte: datetime
    importado_em: datetime
    equivalencia_versao: str
    totais: TotaisMunicipaisJson
    partidos: list[PartidoMunicipalJson]
    municipios: list[MunicipioMunicipalJson]
    notas: list[str]

    @classmethod
    def from_domain(cls, report: MunicipalReport) -> Self:
        return cls(
            ano=report.ano,
            uf=report.uf,
            data_corte=report.corte,
            importado_em=report.importado_em,
            equivalencia_versao=VERSAO_EQUIVALENCIA,
            totais=TotaisMunicipaisJson.from_domain(report.totais),
            partidos=[PartidoMunicipalJson.from_domain(item) for item in report.partidos],
            municipios=[MunicipioMunicipalJson.from_domain(item) for item in report.municipios],
            notas=_notas(report),
        )


def _notas(report: MunicipalReport) -> list[str]:
    totais = report.totais
    notas = [
        f"Situação divulgada pelo TSE em {report.corte:%d/%m/%Y às %H:%M}. "
        "Cassações e eleições suplementares posteriores a 2024 já estão refletidas.",
        "Eleitorado governado é o eleitorado apto do 1º turno de 2024 nos municípios onde o "
        "partido tem o prefeito; não é população.",
        "Vereadores contam pelo partido do candidato, não pela federação ou coligação.",
    ]
    if totais.sem_prefeito > 0:
        notas.append(f"{totais.sem_prefeito} município(s) sem prefeito eleito nos dados do TSE.")
    if totais.divergencias_vagas > 0:
        notas.append(
            f"{totais.divergencias_vagas} município(s) com número de vereadores eleitos "
            "diferente das vagas."
        )
    notas.extend(
        _nota_equivalencia(item)
        for item in report.partidos
        if item.equivalente.correspondencia is not Correspondencia.MESMO
    )
    return notas


def _nota_equivalencia(item: PartyStrength) -> str:
    equivalente = item.equivalente
    if equivalente.correspondencia is Correspondencia.SEM_CORRESPONDENCIA:
        return (
            f"O número {equivalente.numero_2024} ({equivalente.sigla_2024}) de 2024 não tem "
            "correspondente no registro de 2026."
        )
    return equivalente.nota
