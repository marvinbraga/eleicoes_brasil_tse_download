"""Vertical base: stored lines become per-UF and per-city votes. No ballot is read."""

from fractions import Fraction

import pytest

from eleicoes.domain.errors import InvalidUfError, MissingPowerReportError
from eleicoes.domain.verticalizacao import (
    CARGOS,
    GOVERNADOR,
    VerticalLine,
    cargo_share,
    municipal_uf,
    vertical_base,
)


def uf_lines(cargo: str, uf: str, votos: dict[int, int]) -> tuple[VerticalLine, ...]:
    return tuple(VerticalLine(cargo, "uf", uf, uf, 1000, p, v) for p, v in votos.items())


def city_lines(
    cargo: str, codigo: str, nome: str, comparecimento: int, votos: dict[int, int]
) -> tuple[VerticalLine, ...]:
    return tuple(
        VerticalLine(cargo, "municipio", codigo, nome, comparecimento, p, v)
        for p, v in votos.items()
    )


def every_cargo(uf: str = "SP", skip: tuple[str, ...] = ()) -> tuple[VerticalLine, ...]:
    return tuple(
        line for cargo in CARGOS if cargo not in skip for line in uf_lines(cargo, uf, {13: 1})
    )


def test_municipal_uf_reads_the_suffix() -> None:
    assert municipal_uf("RIO BRANCO (AC)") == "AC"
    assert municipal_uf("LISBOA (ZZ)") == "ZZ"
    assert municipal_uf("SEM UF") is None
    assert municipal_uf("ERRADO (XX)") is None


def test_missing_cargo_is_the_power_report_error_in_cargo_order() -> None:
    lines = tuple(
        line for line in every_cargo() if line.cargo not in {"senador", "deputadoEstadual"}
    )
    with pytest.raises(MissingPowerReportError) as caught:
        vertical_base(2026, 1, lines)
    assert caught.value.cargo == "senador"


def test_zero_votes_exterior_and_orphans_are_dropped() -> None:
    lines = (
        *every_cargo(),
        *uf_lines("presidente", "ZZ", {13: 50}),
        *uf_lines(GOVERNADOR, "SP", {22: 0}),
        *city_lines("presidente", "1", "LISBOA (ZZ)", 60, {13: 50}),
        *city_lines("presidente", "2", "SEM UF", 10, {13: 5}),
        *city_lines("presidente", "3", "CAMPINAS (SP)", 100, {13: 40, 22: 0}),
    )
    base = vertical_base(2026, 1, lines)
    assert set(base.estados) == {"SP"}
    assert base.concorreu("SP", GOVERNADOR, 22) is False
    assert base.sem_uf == 1
    [campinas] = base.municipios["SP"]
    assert campinas.votos["presidente"] == {13: 40}
    assert campinas.validos["presidente"] == 40


def test_cargo_share_ignores_states_where_the_party_did_not_run() -> None:
    lines = (
        *every_cargo("SP"),
        *every_cargo("MG"),
        *uf_lines(GOVERNADOR, "SP", {22: 30}),
        *uf_lines(GOVERNADOR, "MG", {15: 99}),
    )
    base = vertical_base(2026, 1, lines)
    share = cargo_share(base, base.scope(None), GOVERNADOR, 22)
    assert share.fatia == Fraction(30, 1 + 30 + 1 + 99)
    assert share.fatia_onde == Fraction(30, 31)
    assert (share.ufs_concorreu, share.ufs_total) == (1, 2)
    absent = cargo_share(base, base.scope(None), GOVERNADOR, 45)
    assert absent.fatia == Fraction(0) and absent.fatia_onde is None


def test_scope_rejects_exterior_and_unknown_states() -> None:
    base = vertical_base(2026, 1, every_cargo("SP"))
    assert base.scope("sp") == ("SP",)
    for uf in ("ZZ", "MG"):
        with pytest.raises(InvalidUfError):
            base.scope(uf)
