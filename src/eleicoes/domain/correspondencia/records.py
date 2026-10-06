"""Always-valid correspondence records. They describe urns, not votes."""

from dataclasses import dataclass
from datetime import datetime

from eleicoes.domain.correspondencia.checks import checked_place, require_int
from eleicoes.domain.correspondencia.status import StatusCorrespondencia
from eleicoes.domain.values import Uf


@dataclass(frozen=True, slots=True)
class Secao:
    uf: str
    codigo_municipio: str
    municipio: str
    zona: int
    numero: int
    local_votacao: str
    urna_esperada: str
    codigo_carga: str
    flashcard: str
    carga_em: datetime | None
    status: StatusCorrespondencia
    maquina_geracao: str
    tpm_geracao: str
    instalacao_geracao: str
    maquina_transmissao: str
    tpm_transmissao: str
    instalacao_transmissao: str
    geracao_em: datetime

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "uf",
            checked_place(self.uf, self.codigo_municipio, self.municipio, self.zona),
        )
        require_int(self.numero, "numero")


@dataclass(frozen=True, slots=True)
class Contingencia:
    uf: str
    codigo_municipio: str
    municipio: str
    zona: int
    urna_esperada: str
    codigo_carga: str
    flashcard: str
    carga_em: datetime | None
    status: StatusCorrespondencia
    maquina_geracao: str
    tpm_geracao: str
    instalacao_geracao: str
    maquina_transmissao: str
    tpm_transmissao: str
    instalacao_transmissao: str
    geracao_em: datetime

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "uf",
            checked_place(self.uf, self.codigo_municipio, self.municipio, self.zona),
        )


@dataclass(frozen=True, slots=True)
class CorrespondenciasNovas:
    secoes: tuple[Secao, ...]
    contingencias: tuple[Contingencia, ...]


@dataclass(frozen=True, slots=True)
class ResumoUf:
    uf: str
    secoes: int
    municipios: int
    zonas: int
    locais: int
    alteradas: int
    novas: int
    urnas_contingencia: int
    contingencias_novas: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "uf", Uf(self.uf).code)
        require_int(self.secoes, "secoes")
        require_int(self.municipios, "municipios")
        require_int(self.zonas, "zonas")
        require_int(self.locais, "locais")
        require_int(self.alteradas, "alteradas")
        require_int(self.novas, "novas")
        require_int(self.urnas_contingencia, "urnas_contingencia")
        require_int(self.contingencias_novas, "contingencias_novas")


@dataclass(frozen=True, slots=True)
class MudancaGeracao:
    uf: str
    codigo_municipio: str
    municipio: str
    zona: int
    secao: int
    geracao_anterior: datetime
    geracao_atual: datetime
    urna_anterior: str
    urna_atual: str
    carga_anterior: str
    carga_atual: str
    flashcard_anterior: str
    flashcard_atual: str
    local_anterior: str
    local_atual: str
    maquina_anterior: str
    maquina_atual: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "uf",
            checked_place(self.uf, self.codigo_municipio, self.municipio, self.zona),
        )
        require_int(self.secao, "secao")
        if not self.campos_alterados:
            raise ValueError("generation change must differ in at least one field")

    @property
    def campos_alterados(self) -> tuple[str, ...]:
        pairs = (
            ("urna", self.urna_anterior, self.urna_atual),
            ("carga", self.carga_anterior, self.carga_atual),
            ("flashcard", self.flashcard_anterior, self.flashcard_atual),
            ("local", self.local_anterior, self.local_atual),
            ("maquina", self.maquina_anterior, self.maquina_atual),
        )
        return tuple(name for name, before, after in pairs if before != after)


@dataclass(frozen=True, slots=True)
class Referencia:
    uf: str
    codigo_municipio: str
    municipio: str
    zona: int
    secao: int | None
    urna: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "uf",
            checked_place(self.uf, self.codigo_municipio, self.municipio, self.zona),
        )
        if self.secao is not None:
            require_int(self.secao, "secao")
