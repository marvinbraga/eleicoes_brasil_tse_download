"""HTML of regions and municipality size: self-contained, both themes, party marks."""

import re
from datetime import UTC, datetime

from eleicoes.adapters.html_regioes_porte import TITULO, html_de_regioes_e_porte, notas
from eleicoes.domain.mapa import Marca
from eleicoes.domain.presidente_governador import CargoTally, MunicipalPlace, PartyTally
from eleicoes.domain.regioes_porte import RegioesEPorte, regioes_e_porte

_MOMENTO = datetime(2026, 10, 26, 22, 0, tzinfo=UTC)
_LOGO = "data:image/png;base64,iVBORw0KGgo="
_MARCAS = {
    13: Marca("#e15759", _LOGO, "PT"),
    22: Marca("#4e79a7", _LOGO, "PL"),
}


def _place(uf: str, codigo: str, votos: dict[int, int]) -> MunicipalPlace:
    parties = tuple(PartyTally(numero, total, 0) for numero, total in votos.items() if total)
    return MunicipalPlace(uf, codigo, f"M{codigo} ({uf})", CargoTally(parties, 1, 1), None)


def _leitura(*, sem_eleitorado: bool = False) -> RegioesEPorte:
    primeiro = [
        _place("AC", "1007", {13: 300, 22: 500, 30: 100}),
        _place("BA", "35599", {13: 700, 22: 200}),
        _place("SP", "71072", {13: 10, 22: 10}),
    ]
    segundo = [
        _place("AC", "1007", {13: 450, 22: 450}),
        _place("BA", "35599", {13: 600, 22: 300}),
    ]
    eleitores = {("AC", "01007"): 9_000}
    if not sem_eleitorado:
        eleitores[("BA", "35599")] = 1_500_000
    return regioes_e_porte(2026, primeiro, segundo, eleitores, ufs_no_boletim=("SP",))


def test_page_is_self_contained_with_light_and_dark_tokens() -> None:
    html = html_de_regioes_e_porte(2026, _MOMENTO, _leitura(), _MARCAS)

    assert html.startswith("<!DOCTYPE html>")
    assert f"<title>{TITULO}</title>" in html
    assert re.search(r"https?://", html) is None
    assert "prefers-color-scheme: dark" in html
    assert ':root[data-tema="dark"]' in html
    assert 'get("tema")' in html
    assert html.count(_LOGO) == 2
    assert "--cor-a: #e15759; --cor-b: #4e79a7;" in html


def test_page_shows_groups_votes_and_the_swing() -> None:
    html = html_de_regioes_e_porte(2026, _MOMENTO, _leitura(), _MARCAS)

    assert "22 PL × 13 PT" in html
    assert "Norte" in html and "Nordeste" in html
    assert "Até 10 mil eleitores" in html and "Acima de 1 milhão" in html
    assert "1 município</span>" in html
    assert "+300 votos · 13 à frente" in html
    assert "0 votos</div>" in html
    assert "+150 (+50,00%)" in html
    assert "p.p." in html
    assert "São Paulo (SP)" in html
    assert "--atualizar" in html


def test_missing_marks_fall_back_to_numbers_and_neutral_colors() -> None:
    html = html_de_regioes_e_porte(2026, _MOMENTO, _leitura(), {})

    assert "22 × 13" in html
    assert 'class="amostra"' in html
    assert "--cor-a: #b8505a" in html


def test_notes_mention_size_edges_and_missing_electorate() -> None:
    leitura = _leitura(sem_eleitorado=True)

    texto = " ".join(notas(leitura, "13 PT", "22 PL"))

    assert "10.001" in texto
    assert "sem eleitorado apto nos boletins, fora do porte: 1." in texto
    assert "exterior ainda não tem 2º turno" in texto
