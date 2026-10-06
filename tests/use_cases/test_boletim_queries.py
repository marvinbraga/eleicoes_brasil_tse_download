"""Use cases over an in-memory boletim reader."""

import pytest

from eleicoes.domain.boletim_consulta import (
    BlankNullProjection,
    BrancosNulos,
    Comparativo,
    LinhaVoto,
    NominalProjection,
    Participacao,
    PoderPartido,
    PrimeiroColocado,
    SectionProjection,
    TotalCargo,
    VotosMunicipio,
    VotosZona,
)
from eleicoes.domain.boletim_indicio import evaluate_findings
from eleicoes.domain.errors import (
    InvalidBoletimConsultaError,
    InvalidNivelError,
    InvalidOrdemError,
    InvalidUfError,
)
from eleicoes.domain.values import UF_CODES
from eleicoes.use_cases.boletim import (
    CompareCandidates,
    ListBlankAndNull,
    ListBulletinFindings,
    ListLeadingCandidate,
    ListParticipation,
    ListPartyPower,
    ListSectionVotes,
    ListVotesByZone,
    RankMunicipalities,
    SummarizeCargo,
)


def test_ranking_orders_most_votes_first_and_least_votes_first() -> None:
    reader = _Reader()
    reader.municipality_rows = (
        VotosMunicipio(1, 5, 10),
        VotosMunicipio(2, 10, 20),
        VotosMunicipio(3, 1, 8),
    )
    most = RankMunicipalities(reader).execute(2026, 1, "ac", "presidente", 22, ordem="mais")
    least = RankMunicipalities(reader).execute(2026, 1, "AC", "presidente", 22, ordem="menos")
    assert [item.municipio for item in most] == [2, 1, 3]
    assert [item.municipio for item in least] == [3, 1, 2]
    assert reader.calls[0] == ("municipalities", 2026, 1, "AC", "presidente", 22)


def test_comparison_keeps_a_zero_and_sorts_by_the_place() -> None:
    reader = _Reader()
    zero = Comparativo(2, None, None, 10, 0, 40)
    other = Comparativo(1, None, None, 3, 4, 20)
    reader.comparison_rows = (zero, other)
    found = CompareCandidates(reader).execute(2026, 1, "AC", "presidente", 22, 13)
    assert found == (other, zero)
    assert found[1].votos_segundo == 0
    assert reader.calls == [("comparison", 2026, 1, "AC", "presidente", 22, 13, "municipio")]


def test_unknown_order_and_level_fail_before_the_reader_is_used() -> None:
    reader = _Reader()
    with pytest.raises(InvalidOrdemError):
        RankMunicipalities(reader).execute(2026, 1, "AC", "presidente", 22, ordem="pior")
    with pytest.raises(InvalidNivelError):
        CompareCandidates(reader).execute(2026, 1, "AC", "presidente", 22, 13, nivel="bairro")
    with pytest.raises(InvalidUfError):
        SummarizeCargo(reader).execute(2026, 1, "XX", "presidente")
    assert reader.calls == []


def test_section_lines_come_back_sorted_and_zone_rows_follow_the_zone() -> None:
    reader = _Reader()
    later = LinhaVoto("presidente", 2, "nominal", 22, 22, 8)
    earlier = LinhaVoto("presidente", 1, "nominal", 13, 13, 4)
    blank = LinhaVoto("governador", 1, "branco", None, None, 1)
    reader.line_rows = (later, earlier, blank)
    reader.zone_rows = (VotosZona(8, 3, 10), VotosZona(2, 0, 5))
    lines = ListSectionVotes(reader).execute(2026, 1, "AC", 1120, 8, 3)
    zones = ListVotesByZone(reader).execute(2026, 1, "AC", 1120, "senador", 100)
    assert lines == (blank, earlier, later)
    assert [item.zona for item in zones] == [2, 8]
    assert reader.calls[0] == ("section_lines", 2026, 1, "AC", 1120, 8, 3)


def test_party_power_lists_the_strongest_party_first_inside_each_place() -> None:
    reader = _Reader()
    reader.party_rows = (
        PoderPartido(1, None, 22, 4, 1, 30),
        PoderPartido(2, None, 13, 1, 0, 10),
        PoderPartido(1, None, 13, 8, 1, 30),
        PoderPartido(1, None, 15, 9, 0, 30),
    )
    found = ListPartyPower(reader).execute(2026, 1, "ac", "deputadoFederal")
    assert [(row.municipio, row.partido, row.votos) for row in found] == [
        (1, 13, 9),
        (1, 15, 9),
        (1, 22, 5),
        (2, 13, 1),
    ]
    assert reader.calls == [("party_power", 2026, 1, ("AC",), "deputadoFederal", "municipio")]

    reader.calls.clear()
    reader.party_rows = (
        PoderPartido(1, 8, 22, 5, 0, 12),
        PoderPartido(1, 2, 13, 1, 0, 9),
        PoderPartido(1, 2, 22, 4, 2, 9),
    )
    zoned = ListPartyPower(reader).execute(2026, 1, "AC", "senador", nivel="zona")
    assert [(row.zona, row.partido) for row in zoned] == [(2, 22), (2, 13), (8, 22)]
    assert reader.calls == [("party_power", 2026, 1, ("AC",), "senador", "zona")]


def test_presidential_power_drops_a_number_with_no_candidate() -> None:
    reader = _Reader()
    reader.party_rows = (
        PoderPartido(None, None, 22, 302807, 0, 488330),
        PoderPartido(None, None, 28, 23, 0, 488330),
        PoderPartido(None, None, 13, 134770, 0, 488330),
    )
    found = ListPartyPower(reader).execute(2026, 1, "AC", "presidente", nivel="uf")
    assert [row.partido for row in found] == [22, 13]


def test_party_power_uf_asks_only_for_that_state() -> None:
    reader = _Reader()
    reader.party_rows = (PoderPartido(None, None, 11, 4, 1, 9),)
    found = ListPartyPower(reader).execute(2026, 1, "ac", "deputadoFederal", nivel="uf")
    assert found[0].municipio is None
    assert found[0].zona is None
    assert found[0].regiao is None
    assert reader.calls == [("party_power", 2026, 1, ("AC",), "deputadoFederal", "uf")]


def test_party_power_regiao_passes_every_state_and_stamps_the_name() -> None:
    reader = _Reader()
    reader.party_rows = (
        PoderPartido(None, None, 13, 1, 0, 10),
        PoderPartido(None, None, 11, 4, 1, 10),
    )
    found = ListPartyPower(reader).execute(2026, 1, "AC", "senador", nivel="regiao")
    assert reader.calls == [
        (
            "party_power",
            2026,
            1,
            ("AC", "AP", "AM", "PA", "RO", "RR", "TO"),
            "senador",
            "regiao",
        )
    ]
    assert [(row.partido, row.regiao) for row in found] == [(11, "Norte"), (13, "Norte")]


def test_party_power_pais_passes_every_uf_code() -> None:
    reader = _Reader()
    reader.party_rows = (PoderPartido(None, None, 22, 1, 0, 3),)
    found = ListPartyPower(reader).execute(2026, 1, "sp", "presidente", nivel="pais")
    passed = reader.calls[0][3]
    assert reader.calls == [("party_power", 2026, 1, UF_CODES, "presidente", "pais")]
    assert passed == UF_CODES
    assert len(passed) > 1
    assert "ZZ" in passed
    assert found[0].regiao is None
    assert found[0].municipio is None


def test_party_power_rejects_zz_region_before_the_reader_is_used() -> None:
    reader = _Reader()
    with pytest.raises(InvalidBoletimConsultaError):
        ListPartyPower(reader).execute(2026, 1, "ZZ", "presidente", nivel="regiao")
    assert reader.calls == []


def test_party_power_rejects_a_section_before_the_reader_is_used() -> None:
    reader = _Reader()
    with pytest.raises(InvalidNivelError):
        ListPartyPower(reader).execute(2026, 1, "AC", "presidente", nivel="secao")
    assert reader.calls == []


def test_participation_sorts_by_city_then_zone() -> None:
    reader = _Reader()
    reader.participation_rows = (
        Participacao(3, None, 10, 9),
        Participacao(1, None, 8, 1),
        Participacao(2, None, 4, 4),
    )
    found = ListParticipation(reader).execute(2026, 1, "ac", "deputadoFederal")
    assert [row.municipio for row in found] == [1, 2, 3]
    assert found[0].abstencao == 7
    assert reader.calls == [("participation", 2026, 1, "AC", "deputadoFederal", "municipio")]

    reader.calls.clear()
    reader.participation_rows = (
        Participacao(1, 8, 10, 9),
        Participacao(2, 1, 10, 9),
        Participacao(1, 2, 10, 8),
    )
    zoned = ListParticipation(reader).execute(2026, 1, "AC", "presidente", nivel="zona")
    assert [(row.municipio, row.zona) for row in zoned] == [(1, 2), (1, 8), (2, 1)]
    assert reader.calls == [("participation", 2026, 1, "AC", "presidente", "zona")]


def test_blank_and_null_sorts_by_descending_share_then_place() -> None:
    reader = _Reader()
    reader.blank_rows = (
        BrancosNulos(2, None, 1, 0, 10),
        BrancosNulos(4, None, 1, 1, 4),
        BrancosNulos(1, None, 5, 0, 0),
        BrancosNulos(3, None, 1, 1, 4),
    )
    found = ListBlankAndNull(reader).execute(2026, 1, "ac", "presidente")
    assert [(row.municipio, row.votos) for row in found] == [(3, 2), (4, 2), (2, 1), (1, 5)]
    assert reader.calls == [("blank_and_null", 2026, 1, "AC", "presidente", "municipio")]

    reader.calls.clear()
    reader.blank_rows = (
        BrancosNulos(1, 9, 1, 0, 2),
        BrancosNulos(1, 2, 1, 0, 2),
        BrancosNulos(1, 5, 0, 0, 4),
    )
    zoned = ListBlankAndNull(reader).execute(2026, 1, "AC", "senador", nivel="zona")
    assert [row.zona for row in zoned] == [2, 9, 5]
    assert reader.calls == [("blank_and_null", 2026, 1, "AC", "senador", "zona")]


def test_leading_candidate_sorts_by_votes_then_place() -> None:
    reader = _Reader()
    reader.leader_rows = (
        PrimeiroColocado(3, None, 13, 13, 4, None, None, None, 10),
        PrimeiroColocado(1, None, 22, 22, 9, 13, 13, 2, 20),
        PrimeiroColocado(2, None, 45, 45, 9, None, None, None, 15),
    )
    found = ListLeadingCandidate(reader).execute(2026, 1, "ac", "deputadoFederal")
    assert [(row.municipio, row.numero, row.votos) for row in found] == [
        (1, 22, 9),
        (2, 45, 9),
        (3, 13, 4),
    ]
    assert found[0].segundo_numero == 13
    assert reader.calls == [("leading_candidate", 2026, 1, "AC", "deputadoFederal", "municipio")]

    reader.calls.clear()
    reader.leader_rows = (
        PrimeiroColocado(1, 4, 22, 22, 5, None, None, None, 8),
        PrimeiroColocado(1, 1, 13, 13, 5, 10, 10, 1, 8),
        PrimeiroColocado(2, 1, 22, 22, 7, None, None, None, 9),
    )
    zoned = ListLeadingCandidate(reader).execute(2026, 1, "AC", "senador", nivel="zona")
    assert [(row.municipio, row.zona, row.votos) for row in zoned] == [
        (2, 1, 7),
        (1, 1, 5),
        (1, 4, 5),
    ]
    assert reader.calls == [("leading_candidate", 2026, 1, "AC", "senador", "zona")]


def test_place_queries_reject_a_section_before_the_reader_is_used() -> None:
    reader = _Reader()
    with pytest.raises(InvalidNivelError):
        ListParticipation(reader).execute(2026, 1, "AC", "presidente", nivel="secao")
    with pytest.raises(InvalidNivelError):
        ListBlankAndNull(reader).execute(2026, 1, "AC", "presidente", nivel="bairro")
    with pytest.raises(InvalidNivelError):
        ListLeadingCandidate(reader).execute(2026, 1, "AC", "presidente", nivel="secao")
    with pytest.raises(InvalidNivelError):
        ListParticipation(reader).execute(2026, 1, "AC", "presidente", nivel="uf")
    with pytest.raises(InvalidNivelError):
        ListBlankAndNull(reader).execute(2026, 1, "AC", "presidente", nivel="regiao")
    with pytest.raises(InvalidNivelError):
        ListLeadingCandidate(reader).execute(2026, 1, "AC", "presidente", nivel="pais")
    assert reader.calls == []


def test_summary_sorts_by_vote_kind_then_number() -> None:
    reader = _Reader()
    reader.total_rows = (
        TotalCargo("nominal", 22, 22, 10),
        TotalCargo("nulo", None, None, 2),
        TotalCargo("nominal", 13, 13, 7),
        TotalCargo("branco", None, None, 1),
    )
    found = SummarizeCargo(reader).execute(2026, 1, "AC", "presidente")
    assert [(item.tipo_voto, item.numero) for item in found] == [
        ("branco", None),
        ("nominal", 13),
        ("nominal", 22),
        ("nulo", None),
    ]


def test_findings_delegate_to_the_domain_rules() -> None:
    reader = _Reader()
    section = SectionProjection(1, 1, 1, 10, 9)
    reader.sections = (section,)
    reader.nominal = (NominalProjection(1, 22, 4),)
    reader.blanks = (BlankNullProjection(1, 1),)
    found = ListBulletinFindings(reader).execute(2026, 1, "ac", "presidente")
    expected = evaluate_findings("AC", "presidente", reader.sections, reader.nominal, reader.blanks)
    assert found == expected
    assert found[0].codigo == "soma_diverge"
    assert reader.calls == [
        ("section_projections", 2026, 1, "AC", "presidente"),
        ("nominal_projections", 2026, 1, "AC", "presidente"),
        ("blank_projections", 2026, 1, "AC", "presidente"),
    ]


class _Reader:
    def __init__(self) -> None:
        self.calls: list[tuple[object, ...]] = []
        self.total_rows: tuple[TotalCargo, ...] = ()
        self.municipality_rows: tuple[VotosMunicipio, ...] = ()
        self.comparison_rows: tuple[Comparativo, ...] = ()
        self.party_rows: tuple[PoderPartido, ...] = ()
        self.participation_rows: tuple[Participacao, ...] = ()
        self.blank_rows: tuple[BrancosNulos, ...] = ()
        self.leader_rows: tuple[PrimeiroColocado, ...] = ()
        self.line_rows: tuple[LinhaVoto, ...] = ()
        self.zone_rows: tuple[VotosZona, ...] = ()
        self.sections: tuple[SectionProjection, ...] = ()
        self.nominal: tuple[NominalProjection, ...] = ()
        self.blanks: tuple[BlankNullProjection, ...] = ()

    def totals(self, ano: int, turno: int, uf: str, cargo: str) -> tuple[TotalCargo, ...]:
        self.calls.append(("totals", ano, turno, uf, cargo))
        return self.total_rows

    def municipalities(
        self, ano: int, turno: int, uf: str, cargo: str, numero: int
    ) -> tuple[VotosMunicipio, ...]:
        self.calls.append(("municipalities", ano, turno, uf, cargo, numero))
        return self.municipality_rows

    def comparison(
        self,
        ano: int,
        turno: int,
        uf: str,
        cargo: str,
        primeiro: int,
        segundo: int,
        nivel: str,
    ) -> tuple[Comparativo, ...]:
        self.calls.append(("comparison", ano, turno, uf, cargo, primeiro, segundo, nivel))
        return self.comparison_rows

    def party_power(
        self, ano: int, turno: int, ufs: tuple[str, ...], cargo: str, nivel: str
    ) -> tuple[PoderPartido, ...]:
        self.calls.append(("party_power", ano, turno, ufs, cargo, nivel))
        return self.party_rows

    def participation(
        self, ano: int, turno: int, uf: str, cargo: str, nivel: str
    ) -> tuple[Participacao, ...]:
        self.calls.append(("participation", ano, turno, uf, cargo, nivel))
        return self.participation_rows

    def blank_and_null(
        self, ano: int, turno: int, uf: str, cargo: str, nivel: str
    ) -> tuple[BrancosNulos, ...]:
        self.calls.append(("blank_and_null", ano, turno, uf, cargo, nivel))
        return self.blank_rows

    def leading_candidate(
        self, ano: int, turno: int, uf: str, cargo: str, nivel: str
    ) -> tuple[PrimeiroColocado, ...]:
        self.calls.append(("leading_candidate", ano, turno, uf, cargo, nivel))
        return self.leader_rows

    def section_lines(
        self, ano: int, turno: int, uf: str, municipio: int, zona: int, secao: int
    ) -> tuple[LinhaVoto, ...]:
        self.calls.append(("section_lines", ano, turno, uf, municipio, zona, secao))
        return self.line_rows

    def zones(
        self, ano: int, turno: int, uf: str, municipio: int, cargo: str, numero: int
    ) -> tuple[VotosZona, ...]:
        self.calls.append(("zones", ano, turno, uf, municipio, cargo, numero))
        return self.zone_rows

    def section_projections(
        self, ano: int, turno: int, uf: str, cargo: str
    ) -> tuple[SectionProjection, ...]:
        self.calls.append(("section_projections", ano, turno, uf, cargo))
        return self.sections

    def nominal_projections(
        self, ano: int, turno: int, uf: str, cargo: str
    ) -> tuple[NominalProjection, ...]:
        self.calls.append(("nominal_projections", ano, turno, uf, cargo))
        return self.nominal

    def blank_projections(
        self, ano: int, turno: int, uf: str, cargo: str
    ) -> tuple[BlankNullProjection, ...]:
        self.calls.append(("blank_projections", ano, turno, uf, cargo))
        return self.blanks

    def close(self) -> None:
        self.calls.append(("close",))
