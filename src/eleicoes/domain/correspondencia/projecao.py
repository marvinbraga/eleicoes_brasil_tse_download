"""Fields a correspondence rule needs. Adapters project rows into these values."""

from dataclasses import dataclass

from eleicoes.domain.correspondencia.checks import checked_place, require_int
from eleicoes.domain.correspondencia.status import StatusCorrespondencia


@dataclass(frozen=True, slots=True)
class ProjecaoSecao:
    uf: str
    codigo_municipio: str
    municipio: str
    zona: int
    secao: int
    urna: str
    carga: str
    flashcard: str
    status: StatusCorrespondencia
    maquina_geracao: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "uf",
            checked_place(self.uf, self.codigo_municipio, self.municipio, self.zona),
        )
        require_int(self.secao, "secao")


@dataclass(frozen=True, slots=True)
class ProjecaoContingencia:
    uf: str
    codigo_municipio: str
    municipio: str
    zona: int
    urna: str
    status: StatusCorrespondencia

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "uf",
            checked_place(self.uf, self.codigo_municipio, self.municipio, self.zona),
        )
