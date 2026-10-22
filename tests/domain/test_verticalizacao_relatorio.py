"""Vertical report: party order, profile, median coherence and the requested scatter."""

from fractions import Fraction

import pytest
from tests.domain.test_verticalizacao import city_lines, uf_lines

from eleicoes.domain.errors import InvalidCargoError, InvalidNumeroError, InvalidUfError
from eleicoes.domain.verticalizacao import (
    CARGOS,
    DEPUTADO_ESTADUAL,
    DEPUTADO_FEDERAL,
    GOVERNADOR,
    PRESIDENTE,
    VerticalLine,
    vertical_base,
)
from eleicoes.domain.verticalizacao_coerencia import PARES_COERENCIA, Coherence
from eleicoes.domain.verticalizacao_regras import (
    ALINHADO,
    BASE,
    PARES_CANONICOS,
    PUXADOR,
    SEM_CANDIDATO,
    Comparison,
)
from eleicoes.domain.verticalizacao_relatorio import (
    NOTES,
    PERFIL_MISTO,
    SEM_COMPARACAO,
    PartyVertical,
    profile,
    scatter_view,
    vertical_report,
)


def _comparison(classe: str | None) -> Comparison:
    return Comparison(GOVERNADOR, DEPUTADO_ESTADUAL, None, None, classe, (), ())


def _profile(*classes: str | None) -> str:
    return profile(tuple(_comparison(classe) for classe in classes))


def test_profile_rules() -> None:
    assert _profile(PUXADOR, ALINHADO, None) == PUXADOR
    assert _profile(PUXADOR, BASE, ALINHADO) == PERFIL_MISTO
    assert _profile(SEM_CANDIDATO, None, None) == SEM_COMPARACAO
    assert _profile(ALINHADO, SEM_CANDIDATO) == ALINHADO
    assert _profile(BASE, ALINHADO) == BASE
    assert _profile() == SEM_COMPARACAO


def _party(rs: tuple[float | None, ...]) -> PartyVertical:
    coerencia = tuple(Coherence(x, y, r, 20) for (x, y), r in zip(PARES_COERENCIA, rs, strict=True))
    return PartyVertical(13, (), coerencia, ())


def test_median_coherence_ignores_the_reference_and_blanks() -> None:
    assert _party((None, None, None, None, None, None, 0.9)).coerencia_mediana is None
    assert _party((0.1, None, 0.5, 0.3, None, None, 0.9)).coerencia_mediana == pytest.approx(0.3)
    assert _party((0.2, 0.4, None, None, None, None, None)).coerencia_mediana == pytest.approx(0.3)


def _two_states() -> tuple[VerticalLine, ...]:
    def state(uf: str) -> tuple[VerticalLine, ...]:
        other = (PRESIDENTE, GOVERNADOR, "senador")
        return (
            *(line for cargo in other for line in uf_lines(cargo, uf, {13: 10, 22: 10, 45: 50})),
            *uf_lines(DEPUTADO_FEDERAL, uf, {13: 30, 22: 30, 45: 5}),
            *uf_lines(DEPUTADO_ESTADUAL, uf, {13: 10, 22: 40, 45: 5}),
        )

    cities = (
        *city_lines(PRESIDENTE, "1", "CAMPINAS (SP)", 100, {13: 10}),
        *city_lines(PRESIDENTE, "2", "SANTOS (SP)", 100, {13: 10}),
        *city_lines(PRESIDENTE, "3", "BELO HORIZONTE (MG)", 100, {13: 10}),
    )
    return (*state("SP"), *state("MG"), *cities)


def test_parties_follow_d14_order_with_state_deputies_breaking_ties() -> None:
    base = vertical_base(2026, 1, _two_states())
    report = vertical_report(base, None)
    assert [party.partido for party in report.partidos] == [22, 13, 45]
    assert report.uf is None
    assert report.municipios == 3
    assert (report.ano, report.turno, report.sem_uf) == (2026, 1, 0)
    first = report.partidos[0]
    assert [share.cargo for share in first.cargos] == list(CARGOS)
    assert [(item.cargo_x, item.cargo_y) for item in first.coerencia] == list(PARES_COERENCIA)
    assert [(item.majoritario, item.proporcional) for item in first.comparacoes] == list(
        PARES_CANONICOS
    )


def test_report_for_one_state() -> None:
    base = vertical_base(2026, 1, _two_states())
    report = vertical_report(base, "sp")
    assert report.uf == "SP"
    assert report.municipios == 2
    with pytest.raises(InvalidUfError):
        vertical_report(base, "ZZ")


def test_scatter_view_defaults_to_the_first_party_and_validates() -> None:
    base = vertical_base(2026, 1, _two_states())
    report = vertical_report(base, "SP")
    view = scatter_view(base, report, None, DEPUTADO_FEDERAL, GOVERNADOR)
    assert (view.partido, view.cargo_x, view.cargo_y) == (22, DEPUTADO_FEDERAL, GOVERNADOR)
    assert view.coerencia.cargo_x == DEPUTADO_FEDERAL
    assert view.pontos == ()
    chosen = scatter_view(base, report, 13, PRESIDENTE, GOVERNADOR)
    assert chosen.partido == 13
    for x, y in ((GOVERNADOR, GOVERNADOR), ("vereador", GOVERNADOR), (GOVERNADOR, "vereador")):
        with pytest.raises(InvalidCargoError):
            scatter_view(base, report, None, x, y)
    for partido in (100, -1, True):
        with pytest.raises(InvalidNumeroError):
            scatter_view(base, report, partido, DEPUTADO_FEDERAL, GOVERNADOR)


def test_scatter_points_come_from_the_report_scope() -> None:
    lines = (
        *_two_states(),
        *city_lines(DEPUTADO_FEDERAL, "1", "CAMPINAS (SP)", 100, {13: 30, 22: 70}),
        *city_lines(DEPUTADO_FEDERAL, "3", "BELO HORIZONTE (MG)", 100, {13: 30}),
    )
    base = vertical_base(2026, 1, lines)
    view = scatter_view(base, vertical_report(base, "SP"), 13, DEPUTADO_FEDERAL, PRESIDENTE)
    assert [(point.nome, point.x, point.y) for point in view.pontos] == [
        ("CAMPINAS (SP)", Fraction(30, 100), Fraction(1))
    ]


def test_notes_are_portuguese_and_ordered() -> None:
    assert len(NOTES) == 8
    assert NOTES[0] == "Lê só as células gravadas do relatório de poder; não lê os boletins."
    assert NOTES[3] == "O exterior só vota para presidente e fica fora de todas as comparações."
    assert NOTES[7].startswith("O Distrito Federal não tem deputado estadual gravado.")
