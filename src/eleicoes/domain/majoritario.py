"""Senate and governor races from first-round nominal votes.

Senado 2026: two seats per UF (renewal of two thirds), the two most voted candidates.
Governador: more than half of the valid votes wins in the first round (CF art. 28 with
art. 77, § 2); otherwise the two most voted go to the second round. A tie the data cannot
break (age, art. 77, § 5) goes to the smaller number and is flagged.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Final

from eleicoes.domain.errors import InvalidSeatRuleError

SITUACAO_ELEITO: Final = "eleito"
SITUACAO_SEGUNDO_TURNO: Final = "segundo_turno"
SITUACAO_SEM_VOTOS: Final = "sem_votos"
VAGAS_SENADO_2026: Final = 2
_FINALISTAS: Final = 2


@dataclass(frozen=True, slots=True)
class VotoCandidato:
    numero: int
    partido: int
    votos: int

    def __post_init__(self) -> None:
        for value, field in (
            (self.numero, "numero"),
            (self.partido, "partido"),
            (self.votos, "votos"),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise InvalidSeatRuleError(field)


@dataclass(frozen=True, slots=True)
class ResultadoSenado:
    uf: str
    vagas: int
    votos_validos: int
    eleitos: tuple[VotoCandidato, ...]
    empate: bool

    @property
    def vagas_sem_candidato(self) -> int:
        return self.vagas - len(self.eleitos)


@dataclass(frozen=True, slots=True)
class ResultadoGoverno:
    uf: str
    votos_validos: int
    situacao: str
    candidatos: tuple[VotoCandidato, ...]
    empate: bool

    @property
    def eleito(self) -> VotoCandidato | None:
        if self.situacao != SITUACAO_ELEITO:
            return None
        return self.candidatos[0]

    @property
    def finalistas(self) -> tuple[VotoCandidato, ...]:
        if self.situacao != SITUACAO_SEGUNDO_TURNO:
            return ()
        return self.candidatos[:_FINALISTAS]


def eleger_senado(
    uf: str, votos: Sequence[VotoCandidato], vagas: int = VAGAS_SENADO_2026
) -> ResultadoSenado:
    ordered = _ordered(votos)
    eleitos = ordered[:vagas]
    return ResultadoSenado(uf, vagas, _validos(ordered), eleitos, _tie_at(ordered, vagas))


def apurar_governo(uf: str, votos: Sequence[VotoCandidato]) -> ResultadoGoverno:
    ordered = _ordered(votos)
    validos = _validos(ordered)
    if validos == 0:
        return ResultadoGoverno(uf, 0, SITUACAO_SEM_VOTOS, ordered, False)
    if 2 * ordered[0].votos > validos:
        return ResultadoGoverno(uf, validos, SITUACAO_ELEITO, ordered, False)
    return ResultadoGoverno(
        uf, validos, SITUACAO_SEGUNDO_TURNO, ordered, _tie_at(ordered, _FINALISTAS)
    )


def _ordered(votos: Sequence[VotoCandidato]) -> tuple[VotoCandidato, ...]:
    numbers = [voto.numero for voto in votos]
    if len(numbers) != len(set(numbers)):
        raise InvalidSeatRuleError("numero")
    return tuple(sorted(votos, key=lambda voto: (-voto.votos, voto.numero)))


def _validos(votos: Sequence[VotoCandidato]) -> int:
    return sum(voto.votos for voto in votos)


def _tie_at(ordered: tuple[VotoCandidato, ...], cut: int) -> bool:
    """True when the last one in and the first one out have the same votes."""
    if len(ordered) <= cut or cut == 0:
        return False
    return ordered[cut - 1].votos == ordered[cut].votos
