"""Party strength scoreboard. Hand-built cells; no database."""

from datetime import datetime

import pytest

from eleicoes.domain.errors import InvalidCargoError
from eleicoes.domain.forca import (
    LIMIARES,
    MUNICIPAL_2024_VAZIO,
    MUNICIPAL_VAZIO,
    BaseCadeiras,
    BaseMunicipal,
    BaseMunicipal2024,
    BaseRecorte,
    BlocoCadeiras,
    BlocoMunicipal2024,
    Cadeiras,
    FederacaoForca,
    FontesForca,
    ForcaUnidade,
    Municipal,
    Municipal2024Forca,
    PlacarForca,
    Presenca,
    cidades,
    lider,
    placar_com_federacoes,
    placar_forca,
    require_cargo_referencia,
    resumo_municipal,
    uf_do_nome,
)
from eleicoes.domain.forca_blocos import (
    com_cadeiras,
    com_municipal_2024,
    sem_cadeiras,
    sem_municipal_2024,
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
        ForcaUnidade(
            "13",
            (13,),
            60,
            30,
            30,
            0,
            Municipal(1, 100, _presenca(3, 3, 3, 2, 2)),
            legenda_federal=0,
            legenda_estadual=0,
        ),
        ForcaUnidade(
            "22",
            (22,),
            40,
            50,
            50,
            1,
            Municipal(1, 100, _presenca(3, 3, 3, 3, 3)),
            legenda_federal=0,
            legenda_estadual=0,
        ),
        ForcaUnidade(
            "65", (65,), None, 20, 0, 0, MUNICIPAL_VAZIO, legenda_federal=0, legenda_estadual=0
        ),
    )


def test_state_cuts_leave_abroad_out_and_mark_missing_places() -> None:
    placar = placar_forca(2026, 1, "deputadoEstadual", FontesForca(PRES, FED, EST, EST))
    assert [recorte.codigo for recorte in placar.ufs] == ["AC", "AM"]
    acre, amazonas = placar.ufs
    assert acre.nome == "Acre"
    assert acre.base == BaseRecorte(30, 10, 40, 1, BaseMunicipal(2, 200, 0))
    assert acre.unidades == (
        ForcaUnidade(
            "13",
            (13,),
            10,
            5,
            10,
            0,
            Municipal(1, 100, _presenca(2, 2, 2, 1, 1)),
            legenda_federal=0,
            legenda_estadual=0,
        ),
        ForcaUnidade(
            "22",
            (22,),
            20,
            5,
            30,
            1,
            Municipal(1, 100, _presenca(2, 2, 2, 2, 2)),
            legenda_federal=0,
            legenda_estadual=0,
        ),
    )
    assert amazonas.base == BaseRecorte(None, 10, 40, 1, BaseMunicipal(1, 100, 1))
    assert amazonas.unidades[0] == ForcaUnidade(
        "13",
        (13,),
        None,
        7,
        20,
        0,
        Municipal(0, 0, _presenca(1, 1, 1, 1, 1)),
        legenda_federal=0,
        legenda_estadual=0,
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
    assert distrito.unidades[0] == ForcaUnidade(
        "13", (13,), None, 9, None, None, None, legenda_federal=0
    )


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


FE_13_43 = FederacaoForca("fe-teste", "Federação Teste", (13, 43))
FEDERADAS = (
    _cell("municipio", "1", "RIO BRANCO (AC)", 13, 30),
    _cell("municipio", "1", "RIO BRANCO (AC)", 43, 30),
    _cell("municipio", "1", "RIO BRANCO (AC)", 22, 50),
    _cell("municipio", "2", "XAPURI (AC)", 13, 10),
    _cell("municipio", "2", "XAPURI (AC)", 43, 1),
    _cell("municipio", "2", "XAPURI (AC)", 22, 89),
    _cell("municipio", "3", "BRASILEIA (AC)", 13, 4),
    _cell("municipio", "3", "BRASILEIA (AC)", 43, 4),
    _cell("municipio", "3", "BRASILEIA (AC)", 22, 92),
    # Members tie at the top: no leader by party, the federation leads when joined.
    _cell("municipio", "4", "FEIJO (AC)", 13, 20),
    _cell("municipio", "4", "FEIJO (AC)", 43, 20),
    _cell("municipio", "4", "FEIJO (AC)", 22, 10),
)


def _placar_federado() -> PlacarForca:
    fontes = FontesForca(None, None, None, FEDERADAS)
    return placar_com_federacoes(2026, 1, "governador", fontes, (FE_13_43,))


def _por_chave(unidades: tuple[ForcaUnidade, ...]) -> dict[str, ForcaUnidade]:
    return {unidade.chave: unidade for unidade in unidades}


def _lideres(unidades: tuple[ForcaUnidade, ...]) -> dict[str, int | None]:
    return {u.chave: (u.municipal.lidera if u.municipal else None) for u in unidades}


def test_federation_row_is_recomputed_not_summed_from_members() -> None:
    pais = _placar_federado().pais
    partidos = _lideres(pais.unidades)
    federadas = _lideres(pais.federadas)
    assert partidos == {"13": 0, "22": 3, "43": 0}
    assert federadas == {"fed:fe-teste": 2, "22": 2}
    assert partidos["13"] + partidos["43"] != federadas["fed:fe-teste"]


def test_joined_view_recomputes_rivals_and_ties_so_leads_add_up() -> None:
    pais = _placar_federado().pais
    assert pais.base.municipal == BaseMunicipal(municipios=4, validos=360, empates=1)
    assert pais.base_federada is not None
    assert pais.base_federada.municipal == BaseMunicipal(municipios=4, validos=360, empates=0)
    federadas = _por_chave(pais.federadas)
    # 22 leads three cities against split members, two against the federation.
    assert _por_chave(pais.unidades)["22"].municipal == Municipal(3, 310, _presenca(4, 4, 4, 4, 4))
    assert federadas["22"].municipal == Municipal(2, 200, _presenca(4, 4, 4, 4, 4))
    leads = sum(u.municipal.lidera for u in pais.federadas if u.municipal is not None)
    assert leads + pais.base_federada.municipal.empates == pais.base_federada.municipal.municipios


def test_federation_row_is_typed_and_named_and_party_rows_are_the_party_run() -> None:
    placar = _placar_federado()
    federacao = _por_chave(placar.pais.federadas)["fed:fe-teste"]
    assert (federacao.tipo, federacao.nome, federacao.partidos) == (
        "federacao",
        "Federação Teste",
        (13, 43),
    )
    assert [u.chave for u in placar.pais.federadas] == ["fed:fe-teste", "22"]
    assert all(u.tipo == "partido" and u.nome is None for u in placar.pais.unidades)
    alone = placar_forca(2026, 1, "governador", FontesForca(None, None, None, FEDERADAS))
    assert placar.pais.unidades == alone.pais.unidades
    assert alone.pais.federadas == ()
    assert alone.pais.base_federada is None


def test_federation_presence_uses_the_joined_votes() -> None:
    pais = _placar_federado().pais
    # 13 alone: 27%, 10%, 4%, 40% -> present at 5% in 3 cities; joined: 55%, 11%, 8%, 80% -> 4.
    assert _por_chave(pais.unidades)["13"].municipal == Municipal(0, 0, _presenca(4, 4, 3, 3, 2))
    joined = _por_chave(pais.federadas)["fed:fe-teste"].municipal
    assert joined == Municipal(2, 160, _presenca(4, 4, 4, 3, 2))


def test_state_cuts_carry_the_joined_view_too() -> None:
    (acre,) = _placar_federado().ufs
    assert [u.chave for u in acre.unidades] == ["13", "22", "43"]
    assert [u.chave for u in acre.federadas] == ["fed:fe-teste", "22"]
    assert acre.federadas[0].tipo == "federacao"
    assert acre.base_federada is not None
    assert acre.base_federada.municipal == BaseMunicipal(4, 360, 0)


def test_without_federations_the_scoreboard_is_the_party_one() -> None:
    fontes = FontesForca(None, None, None, FEDERADAS)
    expected = placar_forca(2026, 1, "governador", fontes)
    assert placar_com_federacoes(2026, 1, "governador", fontes, ()) == expected


def _assentos(camara: int, senado: int, g1: int, g2: int, assembleia: int) -> Cadeiras:
    return Cadeiras(camara, senado, g1, g2, assembleia)


ASSENTOS = {
    ("13", "AC"): _assentos(3, 1, 1, 0, 10),
    ("22", "AC"): _assentos(5, 1, 0, 0, 14),
    ("65", "AC"): _assentos(0, 0, 0, 0, 0),
    ("fed:fe", "AC"): _assentos(3, 1, 1, 0, 10),
    ("13", "AM"): _assentos(4, 0, 0, 1, 12),
    ("22", "AM"): _assentos(4, 2, 0, 1, 12),
    ("65", "AM"): _assentos(0, 0, 0, 0, 0),
    ("13", "BR"): _assentos(7, 1, 1, 1, 22),
    ("22", "BR"): _assentos(9, 3, 0, 1, 26),
    ("65", "BR"): _assentos(0, 0, 0, 0, 0),
}
TOTAIS_ASSENTOS = BaseCadeiras(camara=16, senado=4, governadores=2, assembleias=48)


def test_seats_join_by_key_and_place_with_totals_per_cut() -> None:
    placar = placar_forca(2026, 1, "deputadoEstadual", FontesForca(PRES, FED, EST, EST))
    juntado = com_cadeiras(placar, ASSENTOS, TOTAIS_ASSENTOS)
    assert juntado.cadeiras == BlocoCadeiras(disponivel=True, totais=TOTAIS_ASSENTOS)
    assert juntado.pais.base.cadeiras == TOTAIS_ASSENTOS
    por_chave = {unidade.chave: unidade for unidade in juntado.pais.unidades}
    assert por_chave["22"].cadeiras == _assentos(9, 3, 0, 1, 26)
    assert por_chave["65"].cadeiras == _assentos(0, 0, 0, 0, 0)
    acre, amazonas = juntado.ufs
    # Party rows only: the federation row would count its members twice.
    assert acre.base.cadeiras == BaseCadeiras(camara=8, senado=2, governadores=1, assembleias=24)
    # Second round in AM: nobody won in the first, two finalists, still one governorship.
    assert amazonas.base.cadeiras == BaseCadeiras(
        camara=8, senado=2, governadores=1, assembleias=24
    )
    assert acre.unidades[0].cadeiras == _assentos(3, 1, 1, 0, 10)


def test_unit_without_a_seat_row_and_cut_without_rows_show_no_seats() -> None:
    placar = placar_forca(2026, 1, "deputadoEstadual", FontesForca(PRES, FED, EST, EST))
    juntado = com_cadeiras(placar, {("22", "BR"): _assentos(1, 0, 0, 0, 0)}, TOTAIS_ASSENTOS)
    por_chave = {unidade.chave: unidade for unidade in juntado.pais.unidades}
    assert por_chave["13"].cadeiras is None
    assert juntado.ufs[0].base.cadeiras is None
    assert juntado.ufs[0].unidades[0].cadeiras is None


def test_missing_estimate_flags_the_block_and_leaves_units_untouched() -> None:
    placar = placar_forca(2026, 1, "deputadoEstadual", FontesForca(PRES, FED, EST, EST))
    sem = sem_cadeiras(placar)
    assert sem.cadeiras == BlocoCadeiras(disponivel=False, totais=None)
    assert sem.pais.unidades == placar.pais.unidades
    assert placar.cadeiras is None


def test_seats_reach_the_joined_view_and_its_base() -> None:
    linhas = {
        ("fed:fe-teste", "AC"): _assentos(2, 1, 1, 0, 9),
        ("22", "AC"): _assentos(6, 1, 0, 0, 15),
        ("13", "AC"): _assentos(1, 0, 1, 0, 4),
        ("43", "AC"): _assentos(1, 1, 0, 0, 5),
        ("fed:fe-teste", "BR"): _assentos(2, 1, 1, 0, 9),
        ("22", "BR"): _assentos(6, 1, 0, 0, 15),
    }
    totais = BaseCadeiras(camara=8, senado=2, governadores=1, assembleias=24)
    juntado = com_cadeiras(_placar_federado(), linhas, totais)
    (acre,) = juntado.ufs
    assert [u.cadeiras for u in acre.federadas] == [
        _assentos(2, 1, 1, 0, 9),
        _assentos(6, 1, 0, 0, 15),
    ]
    assert acre.base_federada is not None
    assert acre.base_federada.cadeiras == acre.base.cadeiras == totais
    assert juntado.pais.base_federada is not None
    assert juntado.pais.base_federada.cadeiras == totais


CORTE = datetime(2026, 10, 1, 8, 30)
TOTAIS_2024 = {
    "AC": BaseMunicipal2024(municipios=22, com_prefeito=22, eleitorado=600, vereadores=230),
    "BR": BaseMunicipal2024(municipios=5569, com_prefeito=5560, eleitorado=9000, vereadores=58000),
}
LINHAS_2024 = {
    (13, "AC"): Municipal2024Forca(prefeitos=3, eleitorado_governado=50, vereadores=20),
    (43, "AC"): Municipal2024Forca(prefeitos=1, eleitorado_governado=10, vereadores=5),
    (22, "AC"): Municipal2024Forca(prefeitos=9, eleitorado_governado=300, vereadores=40),
    (13, "BR"): Municipal2024Forca(prefeitos=250, eleitorado_governado=900, vereadores=3000),
    (43, "BR"): Municipal2024Forca(prefeitos=10, eleitorado_governado=20, vereadores=200),
    (22, "BR"): Municipal2024Forca(prefeitos=500, eleitorado_governado=2000, vereadores=4000),
}


def test_2024_counts_join_by_party_and_cut_and_federations_add_members() -> None:
    placar = com_municipal_2024(
        _placar_federado(), LINHAS_2024, TOTAIS_2024, CORTE, federacoes=(FE_13_43,)
    )
    assert placar.municipal_2024 == BlocoMunicipal2024(True, CORTE, TOTAIS_2024["BR"])
    pais = placar.pais
    assert pais.base.municipal_2024 == TOTAIS_2024["BR"]
    assert pais.base_federada is not None
    assert pais.base_federada.municipal_2024 == TOTAIS_2024["BR"]
    assert _por_chave(pais.unidades)["22"].municipal_2024 == LINHAS_2024[(22, "BR")]
    federacao = _por_chave(pais.federadas)["fed:fe-teste"]
    # Additive counts: the federation sums its members (unlike leaderships, F18).
    assert federacao.municipal_2024 == Municipal2024Forca(260, 920, 3200)
    (acre,) = placar.ufs
    assert _por_chave(acre.unidades)["43"].municipal_2024 == LINHAS_2024[(43, "AC")]
    assert _por_chave(acre.federadas)["fed:fe-teste"].municipal_2024 == Municipal2024Forca(
        4, 60, 25
    )


def test_2024_party_without_a_row_elected_nobody_and_cut_without_totals_is_blank() -> None:
    sem_acre = {"BR": TOTAIS_2024["BR"]}
    linhas = {(22, "BR"): LINHAS_2024[(22, "BR")]}
    placar = com_municipal_2024(_placar_federado(), linhas, sem_acre, CORTE, federacoes=(FE_13_43,))
    assert _por_chave(placar.pais.unidades)["13"].municipal_2024 == Municipal2024Forca(0, 0, 0)
    (acre,) = placar.ufs
    assert acre.base.municipal_2024 is None
    assert all(unidade.municipal_2024 is None for unidade in acre.unidades)


def test_missing_2024_import_flags_the_block() -> None:
    placar = placar_forca(2026, 1, "deputadoEstadual", FontesForca(PRES, FED, EST, EST))
    sem = sem_municipal_2024(placar)
    assert sem.municipal_2024 == BlocoMunicipal2024(False, None, None)
    assert sem.pais.unidades == placar.pais.unidades
    assert placar.municipal_2024 is None


def test_2024_counts_of_a_party_without_2026_votes_in_the_cut_get_their_own_row() -> None:
    linhas = {
        **LINHAS_2024,
        (10, "AC"): Municipal2024Forca(prefeitos=5, eleitorado_governado=40, vereadores=62),
        (43, "AC"): Municipal2024Forca(prefeitos=1, eleitorado_governado=10, vereadores=5),
        (99, "AC"): MUNICIPAL_2024_VAZIO,
    }
    placar = com_municipal_2024(
        _placar_federado(), linhas, TOTAIS_2024, CORTE, federacoes=(FE_13_43,)
    )
    (acre,) = placar.ufs
    novo = _por_chave(acre.unidades)["10"]
    assert novo == ForcaUnidade(
        "10", (10,), None, None, None, None, None, municipal_2024=linhas[(10, "AC")]
    )
    assert [u.chave for u in acre.unidades] == ["10", "13", "22", "43"]
    # Joined view: 10 is outside every federation; 43 is already inside fed:fe-teste.
    assert [u.chave for u in acre.federadas] == ["10", "fed:fe-teste", "22"]
    assert "99" not in _por_chave(acre.unidades)


FED_LEGENDA = (
    _cell("pais", "BR", "Brasil", 13, 90, 10),
    _cell("pais", "BR", "Brasil", 22, 180, 20),
    _cell("uf", "AC", "Acre", 13, 40, 5),
    _cell("uf", "AC", "Acre", 22, 50, 5),
)
EST_LEGENDA = (
    _cell("uf", "AC", "Acre", 13, 20, 10),
    _cell("uf", "AC", "Acre", 22, 60, 0),
    _cell("uf", "AM", "Amazonas", 13, 10, 0),
    _cell("uf", "AM", "Amazonas", 22, 5, 5),
)


def test_party_label_votes_come_from_the_same_row_as_the_total() -> None:
    fontes = FontesForca(None, FED_LEGENDA, EST_LEGENDA, EST_LEGENDA)
    placar = placar_forca(2026, 1, "deputadoEstadual", fontes)
    pais = _por_chave(placar.pais.unidades)
    # Country: federal from the "pais" row; state from the sum of the UF rows (no abroad vote).
    assert (pais["13"].deputado_federal, pais["13"].legenda_federal) == (100, 10)
    assert (pais["13"].deputado_estadual, pais["13"].legenda_estadual) == (40, 10)
    assert (pais["22"].legenda_federal, pais["22"].legenda_estadual) == (20, 5)
    acre, amazonas = placar.ufs
    assert (
        _por_chave(acre.unidades)["13"].legenda_federal,
        _por_chave(acre.unidades)["13"].legenda_estadual,
    ) == (5, 10)
    # No federal row for AM: the federal label share is blank there, the state one is 0.
    am13 = _por_chave(amazonas.unidades)["13"]
    assert (am13.legenda_federal, am13.legenda_estadual) == (None, 0)


def test_party_label_votes_are_blank_without_the_source_and_on_federation_rows() -> None:
    sem = placar_forca(
        2026, 1, "deputadoFederal", FontesForca(None, FED_LEGENDA, None, FED_LEGENDA)
    )
    assert _por_chave(sem.pais.unidades)["13"].legenda_estadual is None
    federado = placar_com_federacoes(
        2026,
        1,
        "deputadoEstadual",
        FontesForca(None, FED_LEGENDA, EST_LEGENDA, EST_LEGENDA),
        (FederacaoForca("fe", "Fe", (13, 43)),),
    )
    fed = _por_chave(federado.pais.federadas)["fed:fe"]
    assert (fed.legenda_federal, fed.legenda_estadual) == (None, None)
    assert _por_chave(federado.pais.federadas)["22"].legenda_federal == 20


FE_TRES = FederacaoForca("fe-teste", "Federação Teste", (13, 43, 65))


def _placar_tres() -> PlacarForca:
    fontes = FontesForca(None, None, None, FEDERADAS)
    return placar_com_federacoes(2026, 1, "governador", fontes, (FE_TRES,))


def test_federation_rows_carry_their_declared_members() -> None:
    federacao = _por_chave(_placar_tres().pais.federadas)["fed:fe-teste"]
    # 65 has no 2026 cell, but it is a member: the row lists it.
    assert federacao.partidos == (13, 43, 65)


def test_2024_counts_of_a_member_without_2026_votes_join_its_federation() -> None:
    linhas = {**LINHAS_2024, (65, "AC"): Municipal2024Forca(7, 70, 7)}
    placar = com_municipal_2024(_placar_tres(), linhas, TOTAIS_2024, CORTE, federacoes=(FE_TRES,))
    (acre,) = placar.ufs
    assert [u.chave for u in acre.federadas] == ["fed:fe-teste", "22"]
    assert _por_chave(acre.federadas)["fed:fe-teste"].municipal_2024 == Municipal2024Forca(
        11, 130, 32
    )
    # Party view: 65 gets its own row there (votes blank), as any 2024-only party.
    assert _por_chave(acre.unidades)["65"].municipal_2024 == Municipal2024Forca(7, 70, 7)


def test_2024_counts_of_a_federation_absent_from_the_cut_form_its_row() -> None:
    sem_federacao = tuple(c for c in FEDERADAS if c.partido == 22)
    fontes = FontesForca(None, None, None, sem_federacao)
    base = placar_com_federacoes(2026, 1, "governador", fontes, (FE_TRES,))
    placar = com_municipal_2024(base, LINHAS_2024, TOTAIS_2024, CORTE, federacoes=(FE_TRES,))
    (acre,) = placar.ufs
    federacao = _por_chave(acre.federadas)["fed:fe-teste"]
    assert (federacao.tipo, federacao.nome, federacao.partidos) == (
        "federacao",
        "Federação Teste",
        (13, 43, 65),
    )
    assert federacao.municipal_2024 == Municipal2024Forca(4, 60, 25)
    assert federacao.municipal is None
    assert "13" not in _por_chave(acre.federadas)


def test_2024_without_federations_keeps_the_joined_view_empty() -> None:
    linhas = {**LINHAS_2024, (10, "AC"): Municipal2024Forca(5, 40, 62)}
    plain = placar_forca(2026, 1, "governador", FontesForca(None, None, None, FEDERADAS))
    placar = com_municipal_2024(plain, linhas, TOTAIS_2024, CORTE, federacoes=())
    assert placar.pais.federadas == ()
    assert all(uf.federadas == () for uf in placar.ufs)
    assert "10" in _por_chave(placar.ufs[0].unidades)


def test_label_votes_are_blank_on_federation_rows_in_state_cuts_too() -> None:
    federado = placar_com_federacoes(
        2026,
        1,
        "deputadoEstadual",
        FontesForca(None, FED_LEGENDA, EST_LEGENDA, EST_LEGENDA),
        (FederacaoForca("fe", "Fe", (13, 43)),),
    )
    for uf in federado.ufs:
        fed = _por_chave(uf.federadas)["fed:fe"]
        assert (fed.legenda_federal, fed.legenda_estadual) == (None, None)
