"""Seats per UF in 2026 and the cargo that fills each house.

Câmara: 513 seats (LC 78/1993; CF art. 45, § 1). The STF kept the 1993 distribution for
2026 after the veto to the 531-seat bill (decision of Min. Luiz Fux, 29/09/2025).
Assembleias: CF art. 27 — three times the federal seats up to 36, then one more per
federal seat above 12. The Câmara Legislativa do DF follows the same rule (CF art. 32,
§ 3) and its cargo in the urna is deputadoDistrital.
"""

from typing import Final

from eleicoes.domain.errors import InvalidSeatRuleError, UnsupportedSeatTurnError
from eleicoes.domain.values import Turno, Uf

CARGO_CAMARA: Final = "deputadoFederal"
CARGO_ESTADUAL: Final = "deputadoEstadual"
CARGO_DISTRITAL: Final = "deputadoDistrital"
CARGO_SENADO: Final = "senador"
CARGO_GOVERNO: Final = "governador"
CARGOS_GRAVADOS: Final[tuple[str, ...]] = (
    CARGO_GOVERNO,
    CARGO_SENADO,
    CARGO_CAMARA,
    CARGO_ESTADUAL,
    CARGO_DISTRITAL,
)
TURNO_SIMULADO: Final = 1
_DF: Final = "DF"
_LIMIAR_TRIPLO: Final = 12
_TRIPLO: Final = 3

VAGAS_CAMARA_2026: Final[dict[str, int]] = {
    "AC": 8,
    "AL": 9,
    "AM": 8,
    "AP": 8,
    "BA": 39,
    "CE": 22,
    "DF": 8,
    "ES": 10,
    "GO": 17,
    "MA": 18,
    "MG": 53,
    "MS": 8,
    "MT": 8,
    "PA": 17,
    "PB": 12,
    "PE": 25,
    "PI": 10,
    "PR": 30,
    "RJ": 46,
    "RN": 8,
    "RO": 8,
    "RR": 8,
    "RS": 31,
    "SC": 16,
    "SE": 8,
    "SP": 70,
    "TO": 8,
}


def turno_simulado(turno: int) -> int:
    """Seats are decided in the first round; only governor has a second one."""
    turn = Turno(turno).value
    if turn != TURNO_SIMULADO:
        raise UnsupportedSeatTurnError(turn)
    return turn


def vagas_camara(uf: str) -> int:
    code = Uf(uf).code
    found = VAGAS_CAMARA_2026.get(code)
    if found is None:
        raise InvalidSeatRuleError("uf")
    return found


def vagas_assembleia(uf: str) -> int:
    federais = vagas_camara(uf)
    if federais <= _LIMIAR_TRIPLO:
        return _TRIPLO * federais
    return _TRIPLO * _LIMIAR_TRIPLO + (federais - _LIMIAR_TRIPLO)


def cargo_assembleia(uf: str) -> str:
    return CARGO_DISTRITAL if Uf(uf).code == _DF else CARGO_ESTADUAL


def ufs_com_vagas() -> tuple[str, ...]:
    return tuple(sorted(VAGAS_CAMARA_2026))
