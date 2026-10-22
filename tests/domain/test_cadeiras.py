"""Seats per UF in 2026."""

import pytest

from eleicoes.domain.cadeiras import (
    VAGAS_CAMARA_2026,
    cargo_assembleia,
    ufs_com_vagas,
    vagas_assembleia,
    vagas_camara,
)
from eleicoes.domain.errors import InvalidSeatRuleError


def test_camara_has_513_seats_and_assemblies_1059() -> None:
    assert sum(VAGAS_CAMARA_2026.values()) == 513
    assert sum(vagas_assembleia(uf) for uf in ufs_com_vagas()) == 1059
    assert len(ufs_com_vagas()) == 27


@pytest.mark.parametrize(
    ("uf", "federais", "estaduais"),
    [("AC", 8, 24), ("PB", 12, 36), ("MA", 18, 42), ("SP", 70, 94), ("DF", 8, 24)],
)
def test_assembly_is_three_times_up_to_36_then_one_per_federal_seat(
    uf: str,
    federais: int,
    estaduais: int,
) -> None:
    assert vagas_camara(uf) == federais
    assert vagas_assembleia(uf) == estaduais


def test_df_fills_the_camara_legislativa_with_deputado_distrital() -> None:
    assert cargo_assembleia("df") == "deputadoDistrital"
    assert cargo_assembleia("SP") == "deputadoEstadual"


def test_abroad_has_no_seats() -> None:
    with pytest.raises(InvalidSeatRuleError):
        vagas_camara("ZZ")
