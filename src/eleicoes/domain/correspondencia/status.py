"""Official correspondence-change codes from the TSE leiame."""

from enum import Enum

from eleicoes.domain.errors import UnknownCorrespondenceStatusError


class StatusCorrespondencia(Enum):
    NAO_ALTERADA = "N"
    ALTERADA = "S"
    NOVA = "*"

    @classmethod
    def from_code(cls, code: str) -> "StatusCorrespondencia":
        try:
            return cls(code)
        except ValueError as exc:
            raise UnknownCorrespondenceStatusError(code) from exc
