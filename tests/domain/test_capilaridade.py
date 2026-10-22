"""Capillarity: municipalities, scopes and exact concentration metrics."""

from fractions import Fraction

import pytest

from eleicoes.domain.capilaridade import (
    BRASIL,
    PRESENCA,
    Municipality,
    Scope,
    all_scopes,
    concentration_index,
    contains,
    party_metrics,
    places_from_cells,
    require_capillarity_cargo,
    scope_of,
    subdivision_of,
    uf_of,
)
from eleicoes.domain.errors import (
    InconsistentCellError,
    InvalidCargoError,
    InvalidRecorteError,
    InvalidUfError,
)
from eleicoes.domain.stored_grade import StoredCell


def _cell(codigo: str, nome: str, partido: int, nominais: int, legenda: int = 0) -> StoredCell:
    return StoredCell("municipio", codigo, nome, 1000, partido, nominais, legenda)


def test_places_sum_nominal_and_legenda_and_drop_the_abroad() -> None:
    cells = (
        _cell("71072", "SÃO PAULO (SP)", 13, 30, 5),
        _cell("71072", "SÃO PAULO (SP)", 22, 65),
        _cell("29999", "LISBOA (ZZ)", 13, 4),
    )
    found = places_from_cells(cells)
    assert found.exterior == 1
    assert len(found.places) == 1
    place = found.places[0]
    assert (place.codigo, place.uf, place.validos) == ("71072", "SP", 100)
    assert place.of(13) == 35
    assert place.of(99) == 0


def test_places_reject_a_name_without_uf_a_repeated_party_and_other_levels() -> None:
    with pytest.raises(InconsistentCellError):
        places_from_cells((_cell("1", "SEM UF", 13, 1),))
    with pytest.raises(InconsistentCellError):
        places_from_cells((_cell("1", "A (AC)", 13, 1), _cell("1", "A (AC)", 13, 2)))
    with pytest.raises(InconsistentCellError):
        places_from_cells((StoredCell("uf", "AC", "Acre", 10, 13, 1, 0),))


def test_uf_of_reads_the_suffix() -> None:
    assert uf_of("BELÉM (PA)") == "PA"
    with pytest.raises(InconsistentCellError):
        uf_of("BELÉM PA")
    with pytest.raises(InconsistentCellError):
        uf_of("BELÉM (QQ)")


def test_scope_of_defaults_to_brasil_and_keeps_sudeste_apart_from_sergipe() -> None:
    assert scope_of(None, None) == BRASIL
    assert scope_of("se", None) == Scope("regiao", "SE", "Sudeste")
    assert scope_of(None, "se") == Scope("uf", "SE", "Sergipe")


def test_scope_of_rejects_both_unknown_region_and_abroad() -> None:
    with pytest.raises(InvalidRecorteError):
        scope_of("NE", "PE")
    with pytest.raises(InvalidRecorteError):
        scope_of("XX", None)
    with pytest.raises(InvalidRecorteError):
        scope_of(None, "ZZ")
    with pytest.raises(InvalidUfError):
        scope_of(None, "QQ")


def test_all_scopes_are_brasil_five_regions_and_27_ufs() -> None:
    scopes = all_scopes()
    assert scopes[0] == BRASIL
    assert [s.tipo for s in scopes].count("regiao") == 5
    assert [s.tipo for s in scopes].count("uf") == 27
    assert all(s.codigo != "ZZ" for s in scopes)


def test_contains_and_subdivision_follow_the_scope() -> None:
    recife = Municipality("25313", "RECIFE (PE)", "PE", {13: 1})
    assert contains(BRASIL, recife)
    assert contains(Scope("regiao", "NE", "Nordeste"), recife)
    assert not contains(Scope("regiao", "SE", "Sudeste"), recife)
    assert contains(Scope("uf", "PE", "Pernambuco"), recife)
    assert subdivision_of(BRASIL, recife) == ("NE", "Nordeste")
    assert subdivision_of(Scope("regiao", "NE", "Nordeste"), recife) == ("PE", "Pernambuco")
    assert subdivision_of(Scope("uf", "PE", "Pernambuco"), recife) is None


def test_cargo_must_be_one_of_the_five() -> None:
    assert require_capillarity_cargo("deputadoEstadual") == "deputadoEstadual"
    with pytest.raises(InvalidCargoError):
        require_capillarity_cargo("prefeito")


def test_index_is_zero_when_the_share_is_the_same_everywhere() -> None:
    assert concentration_index(((100, 10), (300, 30))) == 0


def test_index_is_one_minus_one_over_n_when_one_equal_place_has_every_vote() -> None:
    assert concentration_index(((100, 0), (100, 0), (100, 0), (100, 40))) == Fraction(3, 4)


def test_index_of_a_mixed_case_matches_the_hand_count() -> None:
    # sorted by share: (100, 0), (200, 20), (100, 50); C = 0, 20, 70
    # area = 100*(0+0) + 200*(0+20) + 100*(20+70) = 13000; T*P = 400*70
    assert concentration_index(((100, 50), (200, 20), (100, 0))) == Fraction(15, 28)


def test_index_without_votes_is_zero() -> None:
    assert concentration_index(((100, 0),)) == 0
    assert concentration_index(()) == 0


def _sp(codigo: str, a: int, b: int) -> Municipality:
    return Municipality(codigo, f"M{codigo} (SP)", "SP", {13: a, 22: b})


def test_metrics_of_the_mixed_case() -> None:
    members = (_sp("1", 50, 50), _sp("2", 20, 180), _sp("3", 0, 100))
    found = party_metrics(13, Scope("uf", "SP", "São Paulo"), members)
    assert (found.votos, found.validos, found.municipios, found.ufs_com_voto) == (70, 400, 3, 1)
    assert found.indice == Fraction(15, 28)
    assert found.top10.municipios == 1
    assert found.top10.parte == Fraction(5, 7)
    assert found.top10.eleitorado == Fraction(1, 4)
    assert found.top10.vezes == Fraction(20, 7)
    assert found.presenca == 2
    assert found.presenca_parte == Fraction(2, 3)
    assert [(b.chave, b.municipios, b.validos, b.votos) for b in found.faixas] == [
        ("zero", 1, 100, 0),
        ("ate_metade", 0, 0, 0),
        ("metade_a_media", 1, 200, 20),
        ("media_a_1_5", 0, 0, 0),
        ("1_5_a_2", 0, 0, 0),
        ("2_a_3", 1, 100, 50),
        ("3_ou_mais", 0, 0, 0),
    ]
    assert [p.codigo for p in found.fortes] == ["1", "2", "3"]
    assert [p.codigo for p in found.maiores] == ["1", "2"]
    assert found.capitais is None
    assert found.subdivisoes == ()


def test_band_edge_is_inclusive_at_the_mean() -> None:
    members = (_sp("1", 10, 90), _sp("2", 10, 90))
    found = party_metrics(13, Scope("uf", "SP", "São Paulo"), members)
    assert found.faixas[3].municipios == 2  # exactly 1x the mean falls in media_a_1_5


def test_presence_threshold_is_inclusive() -> None:
    members = (_sp("1", 5, 95), _sp("2", 4, 96))
    found = party_metrics(13, Scope("uf", "SP", "São Paulo"), members)
    assert Fraction(5, 100) == PRESENCA
    assert found.presenca == 1


def test_universe_keeps_only_the_ufs_where_the_party_had_votes() -> None:
    members = (
        Municipality("71072", "SÃO PAULO (SP)", "SP", {13: 10, 22: 90}),
        Municipality("60011", "RIO DE JANEIRO (RJ)", "RJ", {22: 100}),
        Municipality("9", "VAZIO (RJ)", "RJ", {22: 0}),
    )
    found = party_metrics(13, BRASIL, members)
    assert (found.ufs_com_voto, found.municipios, found.validos) == (1, 1, 100)
    assert found.validos_recorte == 200
    assert found.fatia == Fraction(1, 10)
    assert found.fatia_recorte == Fraction(1, 20)
    assert found.capitais is not None
    assert (found.capitais.municipios, found.capitais.parte) == (1, Fraction(1))
    sudeste = found.subdivisoes[0]
    assert (sudeste.codigo, sudeste.share.parte, sudeste.share.eleitorado) == (
        "SE",
        Fraction(1),
        Fraction(1),
    )


def test_top_count_rounds_up_and_is_at_least_one() -> None:
    members = tuple(_sp(str(i), i + 1, 100) for i in range(11))
    found = party_metrics(13, Scope("uf", "SP", "São Paulo"), members)
    assert found.top10.municipios == 2
    assert [p.codigo for p in found.fortes][:2] == ["10", "9"]
