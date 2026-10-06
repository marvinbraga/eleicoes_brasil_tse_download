"""Always-valid boletim consultation records."""

import pytest

from eleicoes.domain.boletim_consulta import (
    BrancosNulos,
    Comparativo,
    ComparisonLevel,
    IndicioBoletim,
    LinhaVoto,
    Participacao,
    PartyLevel,
    PartyScope,
    PlaceLevel,
    PoderPartido,
    PrimeiroColocado,
    RankingOrder,
    TotalCargo,
    VotosMunicipio,
    VotosZona,
    partido_do_numero,
    require_cargo,
    require_numero,
)
from eleicoes.domain.correspondencia.indicio import Gravidade
from eleicoes.domain.errors import (
    InvalidBoletimConsultaError,
    InvalidCargoError,
    InvalidNivelError,
    InvalidNumeroError,
    InvalidOrdemError,
    InvalidUfError,
)


def test_order_and_level_accept_only_the_public_tokens() -> None:
    assert RankingOrder("mais").value == "mais"
    assert RankingOrder("menos").value == "menos"
    assert ComparisonLevel("municipio").value == "municipio"
    assert ComparisonLevel("zona").value == "zona"
    assert ComparisonLevel("secao").value == "secao"
    with pytest.raises(InvalidOrdemError):
        RankingOrder("pior")
    with pytest.raises(InvalidNivelError):
        ComparisonLevel("bairro")


def test_records_reject_impossible_votes() -> None:
    assert TotalCargo("branco", None, None, 0).quantidade == 0
    assert VotosMunicipio(1, 0, 10).comparecimento == 10
    assert VotosZona(1, 3, 4).zona == 1
    line = LinhaVoto("presidente", 1, "nominal", 22, 22, 9)
    assert line.numero == 22
    with pytest.raises(InvalidBoletimConsultaError):
        TotalCargo("nominal", None, 22, 1)
    with pytest.raises(InvalidBoletimConsultaError):
        TotalCargo("branco", 22, None, 1)
    with pytest.raises(InvalidBoletimConsultaError):
        TotalCargo("outro", None, None, 1)
    with pytest.raises(InvalidBoletimConsultaError):
        TotalCargo("nominal", 22, 22, -1)
    with pytest.raises(InvalidBoletimConsultaError):
        VotosMunicipio(True, 1, 1)  # type: ignore[arg-type]
    with pytest.raises(InvalidBoletimConsultaError):
        LinhaVoto("", 1, "nulo", None, None, 0)
    with pytest.raises(InvalidBoletimConsultaError):
        Comparativo(1, None, 2, 0, 0, 1)


def test_finding_normalizes_the_uf_and_rejects_a_section_without_a_zone() -> None:
    found = IndicioBoletim(
        codigo="soma_diverge",
        descricao="A soma diverge.",
        gravidade=Gravidade.ALTA,
        uf="ac",
        municipio=1,
        zona=2,
        secao=3,
        medida="sum 1; expected 2",
    )
    assert found.uf == "AC"
    with pytest.raises(InvalidUfError):
        IndicioBoletim(
            codigo="soma_diverge",
            descricao="A soma diverge.",
            gravidade=Gravidade.ALTA,
            uf="XX",
            municipio=1,
            zona=None,
            secao=None,
            medida="sum 1; expected 2",
        )
    with pytest.raises(InvalidBoletimConsultaError):
        IndicioBoletim(
            codigo="concentracao",
            descricao="Fora do padrão.",
            gravidade=Gravidade.MEDIA,
            uf="AC",
            municipio=1,
            zona=None,
            secao=4,
            medida="number 22; share 0.5000; z 4.0",
        )
    with pytest.raises(InvalidBoletimConsultaError):
        IndicioBoletim(
            codigo=" ",
            descricao="Fora do padrão.",
            gravidade=Gravidade.MEDIA,
            uf="AC",
            municipio=1,
            zona=None,
            secao=None,
            medida="share 0.1; z 4.0",
        )


def test_place_level_rejects_a_section() -> None:
    assert PlaceLevel("municipio").value == "municipio"
    assert PlaceLevel("zona").value == "zona"
    with pytest.raises(InvalidNivelError):
        PlaceLevel("secao")
    with pytest.raises(InvalidNivelError):
        PlaceLevel("bairro")
    with pytest.raises(InvalidNivelError):
        PlaceLevel("uf")
    with pytest.raises(InvalidNivelError):
        PlaceLevel("regiao")
    with pytest.raises(InvalidNivelError):
        PlaceLevel("pais")


def test_party_level_accepts_aggregate_levels_and_rejects_a_section() -> None:
    assert PartyLevel("uf").value == "uf"
    assert PartyLevel("regiao").scope("AC").regiao == "Norte"
    assert PartyLevel("pais").scope("ZZ").regiao is None
    with pytest.raises(InvalidNivelError):
        PartyLevel("secao")
    with pytest.raises(InvalidNivelError):
        PartyLevel("bairro")
    with pytest.raises(InvalidBoletimConsultaError):
        PartyLevel("regiao").scope("ZZ")
    with pytest.raises(InvalidBoletimConsultaError):
        PartyScope(())
    with pytest.raises(InvalidBoletimConsultaError):
        PartyScope(("AC", "ac"))
    with pytest.raises(InvalidBoletimConsultaError):
        PartyScope(("AC",), regiao="Atlantis")


def test_party_number_follows_the_candidate_width() -> None:
    assert partido_do_numero("legenda", 15) == 15
    assert partido_do_numero("nominal", 1512) == 15
    assert partido_do_numero("nominal", 15123) == 15
    assert partido_do_numero("nominal", 555) == 55
    assert partido_do_numero("nominal", 222) == 22
    assert partido_do_numero("nominal", 100) == 10
    assert partido_do_numero("nominal", 22) == 22
    with pytest.raises(InvalidNumeroError):
        partido_do_numero("nominal", 999999)
    with pytest.raises(InvalidNumeroError):
        partido_do_numero("nominal", -1)
    with pytest.raises(InvalidNumeroError):
        partido_do_numero("legenda", 100)
    with pytest.raises(InvalidNumeroError):
        partido_do_numero("branco", 0)
    with pytest.raises(InvalidNumeroError):
        partido_do_numero("nulo", 0)
    with pytest.raises(InvalidNumeroError):
        partido_do_numero("cargoSemCandidato", 0)
    with pytest.raises(InvalidNumeroError):
        partido_do_numero("nominal", True)  # type: ignore[arg-type]
    with pytest.raises(InvalidNumeroError):
        partido_do_numero("nominal", "22")  # type: ignore[arg-type]


def test_party_power_sums_votes_and_keeps_zone_optional() -> None:
    city = PoderPartido(1120, None, 15, 10, 3, 40)
    assert city.zona is None
    assert city.votos == 13
    zone = PoderPartido(1120, 8, 0, 0, 0, 0)
    assert zone.zona == 8
    assert zone.votos == 0
    state = PoderPartido(None, None, 11, 10, 3, 40)
    assert state.municipio is None
    assert state.zona is None
    assert state.regiao is None
    assert state.votos == 13
    named = PoderPartido(None, None, 11, 1, 0, 1, "Norte")
    assert named.regiao == "Norte"
    with pytest.raises(InvalidBoletimConsultaError):
        PoderPartido(None, 8, 15, 1, 0, 1)
    with pytest.raises(InvalidBoletimConsultaError):
        PoderPartido(None, None, 15, 1, 0, 1, regiao="Atlantis")
    with pytest.raises(InvalidBoletimConsultaError):
        PoderPartido(0, None, 15, 1, 0, 1)
    with pytest.raises(InvalidBoletimConsultaError):
        PoderPartido(1, 0, 15, 1, 0, 1)
    with pytest.raises(InvalidBoletimConsultaError):
        PoderPartido(1, 10000, 15, 1, 0, 1)
    with pytest.raises(InvalidBoletimConsultaError):
        PoderPartido(1, None, 100, 1, 0, 1)
    with pytest.raises(InvalidBoletimConsultaError):
        PoderPartido(1, None, -1, 1, 0, 1)
    with pytest.raises(InvalidBoletimConsultaError):
        PoderPartido(1, None, 15, -1, 0, 1)
    with pytest.raises(InvalidBoletimConsultaError):
        PoderPartido(1, None, 15, 1, -1, 1)
    with pytest.raises(InvalidBoletimConsultaError):
        PoderPartido(1, None, 15, 1, 0, -1)
    with pytest.raises(InvalidBoletimConsultaError):
        PoderPartido(True, None, 15, 1, 0, 1)  # type: ignore[arg-type]


def test_participation_abstention_is_apt_minus_turnout() -> None:
    city = Participacao(1120, None, 100, 80)
    assert city.zona is None
    assert city.abstencao == 20
    assert Participacao(1120, 8, 10, 10).abstencao == 0
    with pytest.raises(InvalidBoletimConsultaError):
        Participacao(1120, None, 10, 11)
    with pytest.raises(InvalidBoletimConsultaError):
        Participacao(1120, 0, 10, 9)
    with pytest.raises(InvalidBoletimConsultaError):
        Participacao(1120, None, -1, 0)


def test_blank_and_null_votes_are_the_sum() -> None:
    city = BrancosNulos(1120, None, 2, 3, 20)
    assert city.zona is None
    assert city.votos == 5
    assert BrancosNulos(1120, 4, 0, 0, 0).votos == 0
    with pytest.raises(InvalidBoletimConsultaError):
        BrancosNulos(1120, None, -1, 0, 1)
    with pytest.raises(InvalidBoletimConsultaError):
        BrancosNulos(1120, None, 0, -1, 1)


def test_leading_candidate_requires_the_runner_up_together() -> None:
    alone = PrimeiroColocado(1120, None, 22, 22, 10, None, None, None, 30)
    assert alone.segundo_numero is None
    assert alone.segundo_partido is None
    assert alone.segundo_votos is None
    paired = PrimeiroColocado(1120, 8, 15123, 15, 10, 13000, 13, 4, 30)
    assert (paired.segundo_numero, paired.segundo_partido, paired.segundo_votos) == (13000, 13, 4)
    with pytest.raises(InvalidBoletimConsultaError):
        PrimeiroColocado(1120, None, 22, 22, 10, 13, None, None, 30)
    with pytest.raises(InvalidBoletimConsultaError):
        PrimeiroColocado(1120, None, 22, 22, 10, None, 13, None, 30)
    with pytest.raises(InvalidBoletimConsultaError):
        PrimeiroColocado(1120, None, 22, 22, 10, None, None, 4, 30)
    with pytest.raises(InvalidBoletimConsultaError):
        PrimeiroColocado(1120, None, 22, 22, 10, 13, 13, None, 30)


def test_query_arguments_reject_blank_cargo_and_a_bool_number() -> None:
    assert require_cargo("deputadoFederal") == "deputadoFederal"
    assert require_numero(22) == 22
    with pytest.raises(InvalidCargoError):
        require_cargo("  ")
    with pytest.raises(InvalidNumeroError):
        require_numero(True)  # type: ignore[arg-type]
    with pytest.raises(InvalidNumeroError):
        require_numero(-1)
