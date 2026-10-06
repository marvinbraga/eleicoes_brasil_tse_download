"""Boletim findings are decided in the domain, from projections."""

from eleicoes.domain.boletim_consulta import (
    BlankNullProjection,
    NominalProjection,
    SectionProjection,
)
from eleicoes.domain.boletim_indicio import evaluate_findings
from eleicoes.domain.correspondencia.indicio import Gravidade

_CLUSTER = (40, 42, 44, 46, 48, 50, 52, 54, 56, 99)


def test_a_section_whose_sum_mismatches_is_high_and_a_match_is_not() -> None:
    mismatch = SectionProjection(municipio=5, zona=2, secao=9, comparecimento=10, quantidade=9)
    match = SectionProjection(municipio=1, zona=1, secao=1, comparecimento=10, quantidade=10)
    found = evaluate_findings("ac", "presidente", (match, mismatch), (), ())
    assert len(found) == 1
    indicio = found[0]
    assert indicio.codigo == "soma_diverge"
    assert indicio.gravidade is Gravidade.ALTA
    assert indicio.uf == "AC"
    assert indicio.municipio == 5
    assert indicio.zona == 2
    assert indicio.secao == 9
    assert indicio.medida == "sum 9; expected 10"
    assert indicio.descricao.endswith(".")


def test_senator_with_exactly_twice_the_attendance_is_not_a_finding() -> None:
    exact = SectionProjection(municipio=1, zona=1, secao=1, comparecimento=40, quantidade=80)
    assert evaluate_findings("AC", "senador", (exact,), (), ()) == ()
    short = SectionProjection(municipio=2, zona=3, secao=4, comparecimento=40, quantidade=40)
    found = evaluate_findings("AC", "senador", (short,), (), ())
    assert len(found) == 1
    assert found[0].codigo == "soma_diverge"
    assert found[0].gravidade is Gravidade.ALTA
    assert found[0].medida == "sum 40; expected 80"
    assert found[0].zona == 3
    assert found[0].secao == 4


def test_a_leader_share_far_from_a_population_of_ten_is_medium() -> None:
    sections = _sections()
    diverging = SectionProjection(municipio=5, zona=1, secao=1, comparecimento=100, quantidade=90)
    sections = tuple(diverging if item.municipio == 5 else item for item in sections)
    nominal = tuple(
        NominalProjection(municipio=index, numero=22 if votes == 99 else 13, quantidade=votes)
        for index, votes in enumerate(_CLUSTER, start=1)
    )
    nominal = (
        *nominal,
        NominalProjection(municipio=1, numero=99, quantidade=1),
        NominalProjection(municipio=10, numero=30, quantidade=99),
        NominalProjection(municipio=11, numero=22, quantidade=9),
    )
    found = evaluate_findings("AC", "presidente", sections, nominal, ())
    assert [item.codigo for item in found] == ["soma_diverge", "concentracao"]
    assert found[0].gravidade is Gravidade.ALTA
    concentration = found[1]
    assert concentration.gravidade is Gravidade.MEDIA
    assert concentration.municipio == 10
    assert concentration.zona is None
    assert concentration.secao is None
    assert "number 22" in concentration.medida
    assert "share" in concentration.medida
    assert "z " in concentration.medida
    assert "inf" not in concentration.medida
    assert all(item.municipio != 11 for item in found)


def test_blank_and_null_share_uses_the_same_population_rule() -> None:
    nominal = tuple(
        NominalProjection(municipio=index, numero=13, quantidade=50) for index in range(1, 11)
    )
    blanks = tuple(
        BlankNullProjection(municipio=index, quantidade=votes)
        for index, votes in enumerate(_CLUSTER, start=1)
    )
    found = evaluate_findings("AC", "presidente", _sections(), nominal, blanks)
    assert [item.codigo for item in found] == ["brancos_nulos"]
    assert found[0].gravidade is Gravidade.MEDIA
    assert found[0].municipio == 10
    assert found[0].zona is None
    assert "share" in found[0].medida
    assert "z " in found[0].medida
    assert "inf" not in found[0].medida


def test_a_zero_mad_produces_no_infinite_z_and_no_concentration_finding() -> None:
    sections = tuple(
        SectionProjection(municipio=index, zona=1, secao=1, comparecimento=20, quantidade=20)
        for index in range(1, 7)
    )
    nominal = tuple(
        NominalProjection(municipio=index, numero=13, quantidade=10) for index in range(1, 6)
    )
    spike = NominalProjection(municipio=6, numero=22, quantidade=19)
    found = evaluate_findings("AC", "presidente", sections, (*nominal, spike), ())
    assert found == ()
    assert all("inf" not in item.medida for item in found)


def _sections() -> tuple[SectionProjection, ...]:
    ordinary = tuple(
        SectionProjection(municipio=index, zona=1, secao=1, comparecimento=100, quantidade=100)
        for index in range(1, 11)
    )
    small = SectionProjection(municipio=11, zona=1, secao=1, comparecimento=9, quantidade=9)
    return (*ordinary, small)
