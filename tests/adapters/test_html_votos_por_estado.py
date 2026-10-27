"""HTML de "Como votou cada estado". Sem banco nem rede."""

import re
from datetime import UTC, datetime

import pytest

from eleicoes.adapters.html_votos_por_estado import TITULO, html_dos_estados, subtitulo
from eleicoes.domain.mapa import Marca, MarkMissingError
from eleicoes.domain.presidente_governador import CargoTally, MunicipalPlace, PartyTally
from eleicoes.domain.votos_por_estado import (
    Cobertura,
    CoberturaUrnas,
    SecoesIndice,
    VotosPorEstado,
    cobertura_do_turno,
    votos_por_estado,
)

_AGORA = datetime(2026, 10, 26, 22, 0, tzinfo=UTC)
_DADOS = datetime(2026, 10, 26, 21, 0, tzinfo=UTC)
_MARCAS = {
    13: Marca("#e15759", "data:image/png;base64,AAAA", "PT"),
    22: Marca("#4e79a7", "data:image/png;base64,BBBB", "PL"),
}
_CONTAGEM = {
    (1, "PI"): SecoesIndice(100, 100),
    (1, "SP"): SecoesIndice(100, 100),
    (1, "ZZ"): SecoesIndice(10, 10),
    (2, "PI"): SecoesIndice(100, 90),
    (2, "SP"): SecoesIndice(100, 100),
}


def _place(uf: str, codigo: str, votos: dict[int, int]) -> MunicipalPlace:
    parties = tuple(PartyTally(numero, total, 0) for numero, total in votos.items())
    return MunicipalPlace(uf, codigo, f"{codigo} ({uf})", CargoTally(parties, 0, 0), None)


def _segundo(*extra: MunicipalPlace) -> VotosPorEstado:
    places = (
        _place("PI", "1", {13: 1_653_989, 22: 525_859}),
        _place("SP", "2", {13: 12_119_274, 22: 14_139_178}),
        *extra,
    )
    return votos_por_estado(2026, 2, places, cobertura_do_turno(_CONTAGEM, 2))


def _texto(html: str) -> str:
    sem_estilo = re.sub(r"<style>.*?</style>", "", html, flags=re.S)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", sem_estilo))


def test_page_has_title_finalists_rows_and_footer() -> None:
    html = html_dos_estados(_segundo(), _MARCAS, _AGORA, _DADOS)
    texto = _texto(html)
    assert html.startswith("<!DOCTYPE html>")
    assert f"<h1>{TITULO}</h1>" in html
    assert "Em % dos votos válidos e na diferença de votos, com 90,47% das urnas" in texto
    assert "PT · 13" in texto and "PL · 22" in texto
    assert texto.count("venceu em 1 estado ") == 2
    assert "+1,13 mi" in texto and "+2,02 mi" in texto
    assert "13: 1.653.989 · 22: 525.859" in texto
    assert "75,9%" in texto and "24,1%" in texto
    assert "Brasil: 13 48,43% × 22 51,57%, diferença de 891.774 votos" in texto
    assert "(só os lugares já importados)" in texto
    assert "Ainda sem 2º turno:" in texto and "TO." in texto
    assert "O Exterior (ZZ) ainda não tem 2º turno importado." in texto
    assert "190 de 210 seções" in texto
    assert "seções do 1º turno no índice de download" in texto
    assert 'src="data:image/png;base64,AAAA"' in html
    assert "parcial: 90,00% das urnas" in texto


def test_rows_follow_the_reference_share_and_winner_side() -> None:
    html = html_dos_estados(_segundo(), _MARCAS, _AGORA, _DADOS)
    assert html.index('data-uf="PI"') < html.index('data-uf="SP"')
    piaui = html[html.index('data-uf="PI"') : html.index('data-uf="SP"')]
    lado_a = piaui[piaui.index("lado-a") : piaui.index("lado-b")]
    assert "+1,13 mi" in lado_a and "#e15759" in lado_a
    sao_paulo = html[html.index('data-uf="SP"') :]
    lado_b = sao_paulo[sao_paulo.index("lado-b") :]
    assert "+2,02 mi" in lado_b and "#4e79a7" in lado_b
    assert "--w: 1.00000" in sao_paulo


def test_exterior_row_comes_after_the_states() -> None:
    votos = _segundo(_place("ZZ", "9", {13: 10, 22: 30}))
    html = html_dos_estados(votos, _MARCAS, _AGORA, _DADOS)
    assert html.index('data-uf="SP"') < html.index('<p class="secao">Exterior</p>')
    assert html.index("Exterior</p>") < html.index('data-uf="ZZ"')
    assert "não tem 2º turno importado" not in html


def test_first_round_shows_the_other_candidates_as_grey() -> None:
    places = (_place("BA", "1", {13: 500, 22: 300, 30: 200}),)
    votos = votos_por_estado(2026, 1, places, CoberturaUrnas(Cobertura(5, None), {}, None))
    texto = _texto(html_dos_estados(votos, _MARCAS, _AGORA, _DADOS))
    assert "demais candidatos omitidos" in texto
    assert "Os demais candidatos ficam fora das barras" in texto
    assert 'class="outros"' in html_dos_estados(votos, _MARCAS, _AGORA, _DADOS)
    assert "com 5 urnas com boletim baixado (o índice de download não informa" in texto
    assert "não dá o total esperado" in texto


def test_tie_and_narrow_segments() -> None:
    places = (
        _place("AC", "1", {13: 50, 22: 50}),
        _place("BA", "2", {13: 970, 22: 30}),
    )
    cobertura = cobertura_do_turno({(2, "AC"): SecoesIndice(1, 1)}, 2)
    votos = votos_por_estado(2026, 2, places, cobertura)
    html = html_dos_estados(votos, _MARCAS, _AGORA, _DADOS)
    assert 'aria-label="empate"' in html
    assert 'class="estreito"' in html


def test_first_round_coverage_names_its_own_round() -> None:
    places = (_place("PI", "1", {13: 2, 22: 1}),)
    votos = votos_por_estado(2026, 1, places, cobertura_do_turno(_CONTAGEM, 1))
    assert "seções do 1º turno no índice de download)" in _texto(
        html_dos_estados(votos, _MARCAS, _AGORA, _DADOS)
    )
    assert subtitulo(votos).endswith("com 100% das urnas")


def test_text_color_contrasts_with_the_party_color() -> None:
    marcas = {13: Marca("#ffff00", "data:,", ""), 22: Marca("#000080", "data:,", "")}
    html = html_dos_estados(_segundo(), marcas, _AGORA, _DADOS)
    assert "background: #ffff00; color: #111111" in html
    assert "background: #000080; color: #ffffff" in html
    assert "13 · 13" in _texto(html)


def test_theme_follows_the_system_and_can_be_forced() -> None:
    html = html_dos_estados(_segundo(), _MARCAS, _AGORA, _DADOS)
    assert "@media (prefers-color-scheme: dark)" in html
    assert ":root[data-tema='dark']" in html
    assert "<script" not in html
    assert "https://" not in html


def test_missing_mark_names_the_party() -> None:
    with pytest.raises(MarkMissingError) as error:
        html_dos_estados(_segundo(), {13: _MARCAS[13]}, _AGORA, _DADOS)
    assert error.value.partidos == (22,)


def test_coverage_never_rounds_up_to_a_full_hundred() -> None:
    from fractions import Fraction

    from eleicoes.adapters.html_votos_por_estado import _cobertura

    assert _cobertura(Fraction(499_178, 499_207)) == "99,99%"
    assert _cobertura(Fraction(1)) == "100%"
    assert _cobertura(Fraction(905, 1000)) == "90,50%"
