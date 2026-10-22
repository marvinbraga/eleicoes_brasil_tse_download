"""Capillarity classes: ordered rules, one boundary test per threshold."""

from dataclasses import replace
from fractions import Fraction

import pytest

from eleicoes.domain.capilaridade import (
    BRASIL,
    Municipality,
    MunicipalSet,
    PartyMetrics,
    Share,
    Subdivision,
)
from eleicoes.domain.capilaridade_classe import (
    build_report,
    build_view,
    classify,
    summarize,
)
from eleicoes.domain.errors import (
    EmptyRecorteError,
    InvalidRecorteError,
    MissingPowerReportError,
)
from eleicoes.domain.percentual import round_half_up


def _share(parte: Fraction, eleitorado: Fraction) -> Share:
    return Share(1, 1, 1, parte, eleitorado)


_BASE = PartyMetrics(
    partido=13,
    votos=10,
    validos=100,
    validos_recorte=100,
    ufs_com_voto=27,
    municipios=100,
    indice=Fraction(1, 5),
    top10=_share(Fraction(1, 5), Fraction(1, 10)),
    presenca=50,
    capitais=_share(Fraction(1, 4), Fraction(1, 4)),
    subdivisoes=(Subdivision("SE", "Sudeste", _share(Fraction(2, 5), Fraction(2, 5))),),
    faixas=(),
    fortes=(),
    maiores=(),
)


def test_spread_party_is_espalhado() -> None:
    assert classify(_BASE).classe == "espalhado"


def test_pouco_voto_boundary() -> None:
    assert classify(replace(_BASE, votos=99, validos=10_000)).classe == "pouco_voto"
    assert classify(replace(_BASE, votos=100, validos=10_000)).classe == "espalhado"


def test_sem_base_boundary() -> None:
    assert classify(replace(_BASE, municipios=19)).classe == "sem_base"
    assert classify(replace(_BASE, municipios=20)).classe == "espalhado"


def test_capitais_boundary_and_missing_capitals() -> None:
    at = replace(_BASE, capitais=_share(Fraction(7, 20), Fraction(1, 5)))
    below = replace(_BASE, capitais=_share(Fraction(34, 100), Fraction(1, 5)))
    assert classify(at).classe == "capitais"
    assert classify(below).classe == "espalhado"
    assert classify(replace(_BASE, capitais=None)).classe == "espalhado"


def test_regional_needs_half_of_the_votes_and_one_and_a_half_times_the_weight() -> None:
    nordeste = Subdivision("NE", "Nordeste", _share(Fraction(1, 2), Fraction(1, 3)))
    found = classify(replace(_BASE, subdivisoes=(nordeste,)))
    assert (found.classe, found.subdivisao) == ("regional", nordeste)
    short = Subdivision("NE", "Nordeste", _share(Fraction(49, 100), Fraction(1, 5)))
    assert classify(replace(_BASE, subdivisoes=(short,))).classe == "espalhado"
    light = Subdivision("SE", "Sudeste", _share(Fraction(3, 5), Fraction(41, 100)))
    assert classify(replace(_BASE, subdivisoes=(light,))).classe == "espalhado"


def test_poucos_municipios_needs_half_of_the_votes_and_twice_the_weight() -> None:
    at = replace(_BASE, top10=_share(Fraction(1, 2), Fraction(1, 4)))
    heavy = replace(_BASE, top10=_share(Fraction(1, 2), Fraction(26, 100)))
    assert classify(at).classe == "poucos_municipios"
    assert classify(heavy).classe == "espalhado"


def test_capitais_wins_over_regional_and_regional_over_poucos() -> None:
    nordeste = Subdivision("NE", "Nordeste", _share(Fraction(3, 5), Fraction(1, 4)))
    both = replace(
        _BASE,
        capitais=_share(Fraction(1, 2), Fraction(1, 4)),
        subdivisoes=(nordeste,),
        top10=_share(Fraction(3, 5), Fraction(1, 10)),
    )
    assert classify(both).classe == "capitais"
    assert classify(replace(both, capitais=None)).classe == "regional"


def _ac(codigo: str, a: int, b: int) -> Municipality:
    return Municipality(codigo, f"M{codigo} (AC)", "AC", {13: a, 22: b})


def test_view_ranks_classifiable_parties_first_then_by_index() -> None:
    places = tuple(_ac(str(i), 1 + (i % 2) * 50, 100) for i in range(30))
    places += (Municipality("99", "M99 (AC)", "AC", {44: 1, 22: 5_000}),)
    view = build_view(BRASIL, places)
    assert view is not None
    assert (view.municipios, view.ufs) == (31, 1)
    order = [item.metrics.partido for item in view.partidos]
    assert order[-1] == 44  # pouco_voto stays last
    assert view.partidos[-1].classificacao.classe == "pouco_voto"
    summary = summarize(view)
    assert [s.partido for s in summary] == order
    assert summary[0].indice_100 == round_half_up(view.partidos[0].metrics.indice * 100)


def test_report_picks_the_scope_and_reports_missing_ones() -> None:
    places = tuple(_ac(str(i), 10, 90) for i in range(25))
    report = build_report(2026, 1, "governador", MunicipalSet(places, 0))
    assert report.view(None, "AC").scope.codigo == "AC"
    assert report.view("NO", None).scope.nome == "Norte"
    with pytest.raises(EmptyRecorteError):
        report.view(None, "SP")
    with pytest.raises(InvalidRecorteError):
        report.view("NO", "AC")


def test_report_without_places_is_missing() -> None:
    with pytest.raises(MissingPowerReportError):
        build_report(2026, 1, "senador", MunicipalSet((), 3))


def test_poucos_municipios_needs_half_of_the_votes_even_when_heavy() -> None:
    short = replace(_BASE, top10=_share(Fraction(49, 100), Fraction(1, 10)))
    assert classify(short).classe == "espalhado"


def test_scope_whose_places_have_no_valid_vote_has_no_view() -> None:
    empty = (Municipality("1", "M1 (AC)", "AC", {13: 0}),)
    assert build_view(BRASIL, empty) is None
