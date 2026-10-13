"""President × governor classes, margins, and geography. No database."""

from datetime import UTC, datetime
from fractions import Fraction

import pytest

from eleicoes.domain.errors import InvalidBoletimConsultaError, InvalidStoredReportError
from eleicoes.domain.presidente_governador import (
    CLASS_LABELS,
    CLASS_ORDER,
    CargoReading,
    CargoTally,
    MunicipalPlace,
    PartyTally,
    aggregate_places,
    classify,
    composition_of,
    country_reading,
    rank_parties,
    read_place,
    readings_by_uf,
    region_readings,
    state_readings,
)
from eleicoes.ports.relatorio_presidente_governador import StoredCrossReport

_MOMENT = datetime(2026, 10, 8, 17, 30, tzinfo=UTC)


def test_tie_takes_the_smaller_party_number_and_legend_counts() -> None:
    ranked = rank_parties((PartyTally(22, 100, 0), PartyTally(13, 90, 10)))
    assert [item.partido for item in ranked] == [13, 22]
    assert ranked[0].votos == 100
    majority = rank_parties((PartyTally(13, 10, 0), PartyTally(22, 11, 0)))
    assert majority[0].partido == 22


def test_no_runner_up_keeps_matching_governor_in_consolidacao() -> None:
    matched = read_place(_city("AC", "1", "Rio Branco (AC)", ((13, 80, 0),), ((13, 5, 0),)))
    other = read_place(_city("AC", "2", "Cruzeiro (AC)", ((13, 80, 0),), ((22, 5, 0),)))
    assert matched is not None
    assert other is not None
    assert matched.presidente.runner_up is None
    assert matched.classe == "consolidacao"
    assert matched.margin == Fraction(1)
    assert other.classe == "em_aberto"
    assert other.classe != "terreno_de_virada"


def test_four_classes_use_the_fixed_labels() -> None:
    assert CLASS_ORDER == (
        "consolidacao",
        "terreno_de_virada",
        "em_aberto",
        "sem_governador",
    )
    assert CLASS_LABELS["consolidacao"] == "Consolidação"
    assert CLASS_LABELS["terreno_de_virada"] == "Terreno de virada"
    assert CLASS_LABELS["em_aberto"] == "Em aberto"
    assert CLASS_LABELS["sem_governador"] == "Sem governador"
    places = (
        _city("AC", "1", "A (AC)", ((13, 100, 0), (22, 40, 0)), ((13, 10, 0),)),
        _city("AC", "2", "B (AC)", ((13, 100, 0), (22, 40, 0)), ((22, 10, 0),)),
        _city("AC", "3", "C (AC)", ((13, 100, 0), (22, 40, 0)), ((55, 10, 0),)),
        _city("ZZ", "4", "D (ZZ)", ((13, 80, 0),), None),
    )
    assert _classes(places) == (
        "consolidacao",
        "terreno_de_virada",
        "em_aberto",
        "sem_governador",
    )
    composition = composition_of(places)
    assert tuple(item.classe for item in composition.classes) == CLASS_ORDER
    assert composition.classes[3].cidades == 1
    assert composition.classes[3].votos_validos == 80


def test_margin_stays_a_fraction_until_display() -> None:
    wide = read_place(
        _city(
            "AC",
            "1",
            "Rio Branco (AC)",
            ((13, 400, 0), (22, 350, 0), (14, 250, 0)),
            ((13, 1, 0),),
        ),
    )
    half = read_place(
        _city(
            "AC",
            "2",
            "Cruzeiro (AC)",
            ((13, 10500, 0), (22, 9499, 0), (14, 1, 0)),
            ((13, 1, 0),),
        ),
    )
    assert wide is not None and wide.margin == Fraction(50, 1000)
    assert half is not None and half.margin == Fraction(1001, 20000)
    assert wide.presidente.party_share(400) == Fraction(400, 1000)


def test_blanks_stay_out_of_share_margin_and_class() -> None:
    reading = read_place(
        _city(
            "AC",
            "1",
            "Rio Branco (AC)",
            ((13, 60, 0), (22, 40, 0)),
            ((13, 10, 0),),
            branco=100,
            nulo=25,
            gov_branco=7,
            gov_nulo=3,
        ),
    )
    assert reading is not None
    assert reading.presidente.party_share(60) == Fraction(60, 100)
    assert reading.margin == Fraction(20, 100)
    assert reading.classe == "consolidacao"
    assert reading.presidente.ballot_share(100) == Fraction(100, 225)
    assert reading.governador is not None
    assert reading.governador.ballot_share(3) == Fraction(3, 20)


def test_composition_counts_cities_not_the_state_class() -> None:
    places = (
        _city(
            "AC",
            "1",
            "Apertada (AC)",
            ((13, 100, 0), (22, 40, 0)),
            ((22, 10, 0),),
            branco=4,
            nulo=1,
        ),
        _city(
            "AC",
            "2",
            "Folga (AC)",
            ((13, 30, 0), (22, 100, 0)),
            ((22, 10, 0),),
            branco=6,
            nulo=2,
        ),
    )
    composition = composition_of(places)
    assert _slice(composition, "terreno_de_virada") == (1, 140)
    assert _slice(composition, "consolidacao") == (1, 130)
    assert _slice(composition, "em_aberto") == (0, 0)
    assert _slice(composition, "sem_governador") == (0, 0)
    assert composition.votos_validos == 270
    assert composition.share_of("terreno_de_virada") == Fraction(140, 270)
    assert composition.branco == 10
    assert composition.nulo == 3
    states = state_readings(places)
    assert len(states) == 1
    assert states[0].classe == "consolidacao"
    assert states[0].nome == "Acre"
    assert states[0].presidente.valid == 270


def test_region_skips_zz_and_country_includes_it() -> None:
    places = (
        _city("AC", "1", "Rio Branco (AC)", ((13, 10, 0),), ((13, 4, 0),), branco=1, nulo=2),
        _city("PA", "2", "Belem (PA)", ((22, 100, 0),), ((22, 8, 0),), branco=3, nulo=4),
        _city("ZZ", "3", "Lisboa (ZZ)", ((13, 1000, 0),), None, branco=8, nulo=9),
    )
    regions = region_readings(places)
    country = country_reading(places)
    states = state_readings(places)
    assert [item.codigo for item in regions] == ["NO"]
    assert regions[0].presidente.valid == 110
    assert regions[0].presidente.branco == 4
    assert regions[0].presidente.nulo == 6
    assert regions[0].presidente.leader is not None
    assert regions[0].presidente.leader.partido == 22
    assert country is not None
    assert country.nome == "Brasil"
    assert country.presidente.leader is not None
    assert country.presidente.leader.partido == 13
    assert country.presidente.valid == 1110
    assert country.presidente.branco == 12
    assert country.presidente.nulo == 15
    assert country.classe == "terreno_de_virada"
    exterior = next(item for item in states if item.codigo == "ZZ")
    assert exterior.nome == "Exterior"
    assert exterior.classe == "sem_governador"
    assert exterior.presidente.branco == 8
    assert exterior.governador is None
    composition = composition_of(places)
    assert composition.classes[3].votos_validos == 1000
    assert composition.votos_validos == 1110


def test_tighter_margin_comes_first_inside_the_state() -> None:
    places = (
        _city("PA", "9", "Folga (PA)", ((13, 90, 0), (22, 10, 0)), ((13, 1, 0),)),
        _city("AC", "2", "Folga (AC)", ((13, 90, 0), (22, 10, 0)), ((13, 1, 0),)),
        _city("AC", "1", "Apertada (AC)", ((13, 51, 0), (22, 49, 0)), ((13, 1, 0),)),
        _city("AC", "4", "Beta (AC)", ((13, 10, 0),), ((13, 1, 0),)),
        _city("AC", "3", "alfa (AC)", ((13, 10, 0),), ((13, 1, 0),)),
    )
    blocks = readings_by_uf(places)
    assert [code for code, _rows in blocks] == ["AC", "PA"]
    names = [item.nome for item in blocks[0][1]]
    assert names[:2] == ["Apertada (AC)", "Folga (AC)"]
    assert names[2:] == ["alfa (AC)", "Beta (AC)"]


def test_missing_presidential_leader_is_not_a_class() -> None:
    empty = CargoReading(None, None, 0, 0, 0)
    assert classify(empty, None) is None


def test_rejects_invalid_tallies_and_a_naive_clock() -> None:
    with pytest.raises(InvalidBoletimConsultaError):
        PartyTally(13, 0, 0)
    with pytest.raises(InvalidBoletimConsultaError):
        CargoTally((), 0, 0)
    with pytest.raises(InvalidBoletimConsultaError):
        CargoTally((PartyTally(13, 1, 0), PartyTally(13, 2, 0)), 0, 0)
    with pytest.raises(InvalidStoredReportError):
        StoredCrossReport((), datetime(2026, 10, 8, 14, 30))
    assert StoredCrossReport((), _MOMENT).places == ()
    summed = aggregate_places(
        (
            _city("AC", "1", "A (AC)", ((13, 10, 1),), ((22, 4, 0),)),
            _city("AC", "2", "B (AC)", ((13, 4, 2),), ((22, 1, 3),)),
        ),
        "AC",
        "Acre",
    )
    assert summed.presidente.leader is not None
    assert summed.presidente.leader.votos == 17
    assert summed.governador is not None
    assert summed.governador.leader is not None
    assert summed.governador.leader.votos == 8


def _city(
    uf: str,
    code: str,
    nome: str,
    president: tuple[tuple[int, int, int], ...],
    governor: tuple[tuple[int, int, int], ...] | None,
    *,
    branco: int = 0,
    nulo: int = 0,
    gov_branco: int = 0,
    gov_nulo: int = 0,
) -> MunicipalPlace:
    governor_tally = None if governor is None else _tally(governor, gov_branco, gov_nulo)
    return MunicipalPlace(uf, code, nome, _tally(president, branco, nulo), governor_tally)


def _tally(
    parties: tuple[tuple[int, int, int], ...],
    branco: int,
    nulo: int,
) -> CargoTally:
    rows = tuple(PartyTally(party, nominal, legend) for party, nominal, legend in parties)
    return CargoTally(rows, branco, nulo)


def _classes(places: tuple[MunicipalPlace, ...]) -> tuple[str, ...]:
    found: list[str] = []
    for place in places:
        reading = read_place(place)
        assert reading is not None
        found.append(reading.classe)
    return tuple(found)


def _slice(composition: object, classe: str) -> tuple[int, int]:
    from eleicoes.domain.presidente_governador import Composition

    assert isinstance(composition, Composition)
    item = next(row for row in composition.classes if row.classe == classe)
    return item.cidades, item.votos_validos
