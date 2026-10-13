"""JSON published for boletim consultations. Field names follow the domain records."""

from typing import Self

from pydantic import BaseModel

from eleicoes.domain.boletim_consulta import (
    BrancosNulos,
    Comparativo,
    IndicioBoletim,
    LinhaVoto,
    Participacao,
    PoderPartido,
    PrimeiroColocado,
    TotalCargo,
    VotosMunicipio,
    VotosZona,
)


class TotalCargoJson(BaseModel):
    tipo_voto: str
    partido: int | None
    numero: int | None
    quantidade: int

    @classmethod
    def from_domain(cls, row: TotalCargo) -> Self:
        return cls(
            tipo_voto=row.tipo_voto,
            partido=row.partido,
            numero=row.numero,
            quantidade=row.quantidade,
        )


class VotosMunicipioJson(BaseModel):
    municipio: int
    quantidade: int
    comparecimento: int

    @classmethod
    def from_domain(cls, row: VotosMunicipio) -> Self:
        return cls(
            municipio=row.municipio,
            quantidade=row.quantidade,
            comparecimento=row.comparecimento,
        )


class ComparativoJson(BaseModel):
    municipio: int
    zona: int | None
    secao: int | None
    votos_primeiro: int
    votos_segundo: int
    comparecimento: int

    @classmethod
    def from_domain(cls, row: Comparativo) -> Self:
        return cls(
            municipio=row.municipio,
            zona=row.zona,
            secao=row.secao,
            votos_primeiro=row.votos_primeiro,
            votos_segundo=row.votos_segundo,
            comparecimento=row.comparecimento,
        )


class PoderPartidoJson(BaseModel):
    municipio: int | None
    zona: int | None
    partido: int
    votos_nominais: int
    votos_legenda: int
    comparecimento: int
    regiao: str | None
    votos: int

    @classmethod
    def from_domain(cls, row: PoderPartido) -> Self:
        return cls(
            municipio=row.municipio,
            zona=row.zona,
            partido=row.partido,
            votos_nominais=row.votos_nominais,
            votos_legenda=row.votos_legenda,
            comparecimento=row.comparecimento,
            regiao=row.regiao,
            votos=row.votos,
        )


class ParticipacaoJson(BaseModel):
    municipio: int
    zona: int | None
    eleitores_aptos: int
    comparecimento: int
    abstencao: int

    @classmethod
    def from_domain(cls, row: Participacao) -> Self:
        return cls(
            municipio=row.municipio,
            zona=row.zona,
            eleitores_aptos=row.eleitores_aptos,
            comparecimento=row.comparecimento,
            abstencao=row.abstencao,
        )


class BrancosNulosJson(BaseModel):
    municipio: int
    zona: int | None
    branco: int
    nulo: int
    comparecimento: int
    votos: int

    @classmethod
    def from_domain(cls, row: BrancosNulos) -> Self:
        return cls(
            municipio=row.municipio,
            zona=row.zona,
            branco=row.branco,
            nulo=row.nulo,
            comparecimento=row.comparecimento,
            votos=row.votos,
        )


class PrimeiroColocadoJson(BaseModel):
    municipio: int
    zona: int | None
    numero: int
    partido: int
    votos: int
    segundo_numero: int | None
    segundo_partido: int | None
    segundo_votos: int | None
    comparecimento: int

    @classmethod
    def from_domain(cls, row: PrimeiroColocado) -> Self:
        return cls(
            municipio=row.municipio,
            zona=row.zona,
            numero=row.numero,
            partido=row.partido,
            votos=row.votos,
            segundo_numero=row.segundo_numero,
            segundo_partido=row.segundo_partido,
            segundo_votos=row.segundo_votos,
            comparecimento=row.comparecimento,
        )


class LinhaVotoJson(BaseModel):
    cargo: str
    ordem_impressao: int
    tipo_voto: str
    partido: int | None
    numero: int | None
    quantidade: int

    @classmethod
    def from_domain(cls, row: LinhaVoto) -> Self:
        return cls(
            cargo=row.cargo,
            ordem_impressao=row.ordem_impressao,
            tipo_voto=row.tipo_voto,
            partido=row.partido,
            numero=row.numero,
            quantidade=row.quantidade,
        )


class VotosZonaJson(BaseModel):
    zona: int
    quantidade: int
    comparecimento: int

    @classmethod
    def from_domain(cls, row: VotosZona) -> Self:
        return cls(zona=row.zona, quantidade=row.quantidade, comparecimento=row.comparecimento)


class IndicioBoletimJson(BaseModel):
    codigo: str
    descricao: str
    gravidade: str
    uf: str
    municipio: int
    zona: int | None
    secao: int | None
    medida: str

    @classmethod
    def from_domain(cls, row: IndicioBoletim) -> Self:
        return cls(
            codigo=row.codigo,
            descricao=row.descricao,
            gravidade=row.gravidade.value,
            uf=row.uf,
            municipio=row.municipio,
            zona=row.zona,
            secao=row.secao,
            medida=row.medida,
        )
