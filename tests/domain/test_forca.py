"""Party strength scoreboard. Hand-built cells; no database."""

import pytest

from eleicoes.domain.errors import InvalidCargoError
from eleicoes.domain.forca import (
    LIMIARES,
    MUNICIPAL_VAZIO,
    BaseMunicipal,
    BaseRecorte,
    FontesForca,
    ForcaUnidade,
    Municipal,
    Presenca,
    cidades,
    lider,
    placar_forca,
    require_cargo_referencia,
    resumo_municipal,
    uf_do_nome,
)
from eleicoes.domain.stored_grade import StoredCell


def _cell(
    nivel: str,
    codigo: str,
    nome: str,
    partido: int,
    votos: int,
    legenda: int = 0,
) -> StoredCell:
    return StoredCell(nivel, codigo, nome, 1000, partido, votos, legenda)


CIDADES = (
    _cell("municipio", "1", "RIO BRANCO (AC)", 13, 50, 10),
    _cell("municipio", "1", "RIO BRANCO (AC)", 22, 40),
    _cell("municipio", "2", "XAPURI (AC)", 13, 5),
    _cell("municipio", "2", "XAPURI (AC)", 22, 95),
    _cell("municipio", "3", "MANAUS (AM)", 13, 50),
    _cell("municipio", "3", "MANAUS (AM)", 22, 50),
    _cell("municipio", "4", "JURUA (AM)", 13, 0),
    _cell("municipio", "4", "JURUA (AM)", 22, 0),
    _cell("municipio", "5", "ABU DHABI (ZZ)", 13, 10),
    _cell("municipio", "5", "ABU DHABI (ZZ)", 22, 0),
)


def _presenca(*contagens: int) -> tuple[Presenca, ...]:
    return tuple(Presenca(limiar, n) for limiar, n in zip(LIMIARES, contagens, strict=True))


def test_uf_comes_from_the_name_suffix_only() -> None:
    assert uf_do_nome("RIO BRANCO (AC)") == "AC"
    assert uf_do_nome("ABU DHABI (ZZ)") == "ZZ"
    assert uf_do_nome("Brasília") is None
    assert uf_do_nome("Xapuri (ac)") is None


def test_leader_needs_a_single_positive_top() -> None:
    assert lider({"13": 5, "22": 3}) == "13"
    assert lider({"13": 5, "22": 5}) is None
    assert lider({"13": 0, "22": 0}) is None
    assert lider({}) is None


def test_reference_office_is_one_of_the_five_stored() -> None:
    assert require_cargo_referencia("deputadoEstadual") == "deputadoEstadual"
    with pytest.raises(InvalidCargoError):
        require_cargo_referencia("deputadoDistrital")


def test_cities_skip_abroad_and_other_levels_and_add_party_votes() -> None:
    found = cidades((*CIDADES, _cell("uf", "AC", "Acre", 13, 9)))
    assert [(cidade.codigo, cidade.uf) for cidade in found] == [
        ("1", "AC"),
        ("2", "AC"),
        ("3", "AM"),
        ("4", "AM"),
    ]
    assert found[0].votos == (("13", 60), ("22", 40))
    assert found[0].validos == 100


def test_municipal_summary_counts_leaders_ties_and_inclusive_thresholds() -> None:
    base, por_chave = resumo_municipal(cidades(CIDADES))
    assert base == BaseMunicipal(municipios=3, validos=300, empates=1)
    assert por_chave["13"] == Municipal(1, 100, _presenca(3, 3, 3, 2, 2))
    assert por_chave["22"] == Municipal(1, 100, _presenca(3, 3, 3, 3, 3))
    assert Municipal(0, 0, _presenca(0, 0, 0, 0, 0)) == MUNICIPAL_VAZIO


def test_party_without_votes_in_valid_cities_is_left_out() -> None:
    zero = (*CIDADES, _cell("municipio", "1", "RIO BRANCO (AC)", 65, 0))
    _base, por_chave = resumo_municipal(cidades(zero))
    assert "65" not in por_chave


PRES = (
    _cell("pais", "BR", "Brasil", 13, 60),
    _cell("pais", "BR", "Brasil", 22, 40),
    _cell("uf", "AC", "Acre", 13, 10),
    _cell("uf", "AC", "Acre", 22, 20),
    _cell("uf", "ZZ", "Exterior", 13, 1),
    _cell("uf", "ZZ", "Exterior", 22, 0),
)
FED = (
    _cell("pais", "BR", "Brasil", 13, 30),
    _cell("pais", "BR", "Brasil", 22, 50),
    _cell("pais", "BR", "Brasil", 65, 20),
    _cell("uf", "AC", "Acre", 13, 5),
    _cell("uf", "AC", "Acre", 22, 5),
    _cell("uf", "AC", "Acre", 65, 0),
    _cell("uf", "AM", "Amazonas", 13, 7),
    _cell("uf", "AM", "Amazonas", 22, 3),
    _cell("uf", "AM", "Amazonas", 65, 0),
)
EST = (
    _cell("uf", "AC", "Acre", 13, 10),
    _cell("uf", "AC", "Acre", 22, 30),
    _cell("uf", "AC", "Acre", 65, 0),
    _cell("uf", "AM", "Amazonas", 13, 20),
    _cell("uf", "AM", "Amazonas", 22, 20),
    _cell("uf", "AM", "Amazonas", 65, 0),
    *CIDADES,
)


def test_country_cut_uses_country_rows_and_sums_state_rows() -> None:
    placar = placar_forca(2026, 1, "deputadoEstadual", FontesForca(PRES, FED, EST, EST))
    assert placar.faltando == ()
    assert placar.limiares == LIMIARES
    assert (placar.pais.codigo, placar.pais.nome) == ("BR", "Brasil")
    assert placar.pais.base == BaseRecorte(100, 100, 80, 2, BaseMunicipal(3, 300, 1))
    assert placar.pais.unidades == (
        ForcaUnidade("13", (13,), 60, 30, 30, 0, Municipal(1, 100, _presenca(3, 3, 3, 2, 2))),
        ForcaUnidade("22", (22,), 40, 50, 50, 1, Municipal(1, 100, _presenca(3, 3, 3, 3, 3))),
        ForcaUnidade("65", (65,), None, 20, 0, 0, MUNICIPAL_VAZIO),
    )


def test_state_cuts_leave_abroad_out_and_mark_missing_places() -> None:
    placar = placar_forca(2026, 1, "deputadoEstadual", FontesForca(PRES, FED, EST, EST))
    assert [recorte.codigo for recorte in placar.ufs] == ["AC", "AM"]
    acre, amazonas = placar.ufs
    assert acre.nome == "Acre"
    assert acre.base == BaseRecorte(30, 10, 40, 1, BaseMunicipal(2, 200, 0))
    assert acre.unidades == (
        ForcaUnidade("13", (13,), 10, 5, 10, 0, Municipal(1, 100, _presenca(2, 2, 2, 1, 1))),
        ForcaUnidade("22", (22,), 20, 5, 30, 1, Municipal(1, 100, _presenca(2, 2, 2, 2, 2))),
    )
    assert amazonas.base == BaseRecorte(None, 10, 40, 1, BaseMunicipal(1, 100, 1))
    assert amazonas.unidades[0] == ForcaUnidade(
        "13", (13,), None, 7, 20, 0, Municipal(0, 0, _presenca(1, 1, 1, 1, 1))
    )


def test_state_without_state_deputies_shows_no_state_columns() -> None:
    sem_df = (
        *FED,
        _cell("uf", "DF", "Distrito Federal", 13, 9),
        _cell("uf", "DF", "Distrito Federal", 22, 1),
    )
    placar = placar_forca(2026, 1, "deputadoEstadual", FontesForca(PRES, sem_df, EST, EST))
    distrito = next(recorte for recorte in placar.ufs if recorte.codigo == "DF")
    assert distrito.base == BaseRecorte(None, 10, None, None, None)
    assert distrito.unidades[0] == ForcaUnidade("13", (13,), None, 9, None, None, None)


def test_missing_sources_become_dashes_and_are_listed_in_office_order() -> None:
    placar = placar_forca(2026, 1, "governador", FontesForca(None, FED, EST, None))
    assert placar.faltando == ("presidente", "governador")
    assert placar.pais.base.validos_presidente is None
    assert placar.pais.base.municipal is None
    assert placar.pais.unidades[0].presidente is None
    assert placar.pais.unidades[0].municipal is None
    assert placar.pais.unidades[0].deputado_federal == 30


GOV = (
    _cell("municipio", "1", "RIO BRANCO (AC)", 13, 10),
    _cell("municipio", "1", "RIO BRANCO (AC)", 22, 20),
    _cell("municipio", "1", "RIO BRANCO (AC)", 45, 70),
    _cell("municipio", "2", "XAPURI (AC)", 13, 50),
    _cell("municipio", "2", "XAPURI (AC)", 22, 50),
)


def test_municipal_columns_come_from_the_reference_office_only() -> None:
    placar = placar_forca(2026, 1, "governador", FontesForca(PRES, FED, EST, GOV))
    assert placar.faltando == ()
    assert placar.pais.base.municipal == BaseMunicipal(2, 200, 1)
    por_chave = {unidade.chave: unidade for unidade in placar.pais.unidades}
    assert list(por_chave) == ["13", "22", "45", "65"]
    assert por_chave["13"].municipal == Municipal(0, 0, _presenca(2, 2, 2, 2, 1))
    assert por_chave["22"].municipal == Municipal(0, 0, _presenca(2, 2, 2, 2, 2))
    assert por_chave["45"] == ForcaUnidade(
        "45", (45,), None, None, None, None, Municipal(1, 100, _presenca(1, 1, 1, 1, 1))
    )
    assert por_chave["65"].municipal is None


def test_missing_state_source_leaves_every_state_column_empty() -> None:
    placar = placar_forca(2026, 1, "deputadoFederal", FontesForca(PRES, FED, None, FED))
    assert placar.faltando == ("deputadoEstadual",)
    assert placar.pais.base.validos_deputado_estadual is None
    assert placar.pais.base.ufs_deputado_estadual is None
    primeiro = placar.pais.unidades[0]
    assert (primeiro.deputado_estadual, primeiro.ufs_lider_estadual) == (None, None)


def test_state_source_without_valid_votes_counts_zero_states() -> None:
    zerado = (_cell("uf", "AC", "Acre", 13, 0), _cell("uf", "AC", "Acre", 22, 0))
    placar = placar_forca(2026, 1, "deputadoEstadual", FontesForca(PRES, FED, zerado, zerado))
    assert placar.pais.base.validos_deputado_estadual is None
    assert placar.pais.base.ufs_deputado_estadual == 0
    primeiro = placar.pais.unidades[0]
    assert (primeiro.deputado_estadual, primeiro.ufs_lider_estadual) == (None, 0)
    acre = next(recorte for recorte in placar.ufs if recorte.codigo == "AC")
    assert acre.base.ufs_deputado_estadual is None
