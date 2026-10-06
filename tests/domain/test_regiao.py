"""Macro-regions partition the geographic UF codes. ZZ stays outside."""

import pytest

from eleicoes.domain.errors import InvalidBoletimConsultaError
from eleicoes.domain.regiao import REGIONS, MacroRegion, _index, region_of
from eleicoes.domain.values import UF_CODES

_NORTE: tuple[str, ...] = ("AC", "AP", "AM", "PA", "RO", "RR", "TO")


def test_acre_belongs_to_norte_with_seven_codes() -> None:
    region = region_of("ac")
    assert region.name == "Norte"
    assert region.sigla == "NO"
    assert region.ufs == _NORTE


def test_sao_paulo_belongs_to_sudeste() -> None:
    assert region_of("SP").name == "Sudeste"
    assert region_of("SP").sigla == "SE"
    assert region_of("sp").ufs == ("ES", "MG", "RJ", "SP")


def test_official_siglas_follow_the_region_order() -> None:
    assert [(region.sigla, region.name) for region in REGIONS] == [
        ("NO", "Norte"),
        ("NE", "Nordeste"),
        ("CO", "Centro-Oeste"),
        ("SE", "Sudeste"),
        ("S", "Sul"),
    ]


def test_zz_has_no_region() -> None:
    with pytest.raises(InvalidBoletimConsultaError):
        region_of("ZZ")


def test_geographic_codes_plus_zz_equal_uf_codes_without_overlap() -> None:
    grouped = [region.ufs for region in REGIONS]
    flat = [code for codes in grouped for code in codes]
    assert len(flat) == len(set(flat)) == 27
    assert "ZZ" not in flat
    assert set(flat) | {"ZZ"} == set(UF_CODES)


def test_macro_region_rejects_blank_duplicate_and_zz() -> None:
    with pytest.raises(InvalidBoletimConsultaError):
        MacroRegion(" ", ("AC",), "NO")
    with pytest.raises(InvalidBoletimConsultaError):
        MacroRegion("Norte", ("AC", "AC"), "NO")
    with pytest.raises(InvalidBoletimConsultaError):
        MacroRegion("Norte", ("ZZ",), "NO")
    with pytest.raises(InvalidBoletimConsultaError):
        MacroRegion("Norte", (), "NO")
    with pytest.raises(InvalidBoletimConsultaError):
        MacroRegion("Norte", ("AC",), " ")
    with pytest.raises(InvalidBoletimConsultaError):
        _index(
            (
                MacroRegion("Norte", ("AC",), "NO"),
                MacroRegion("Sul", ("PR",), "no"),
            )
        )
