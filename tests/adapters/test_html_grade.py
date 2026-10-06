"""HTML grid: one decimal, escaped text, and a scale per grade."""

import re

from eleicoes.adapters.html_grade import html_da_grade, html_das_grades
from eleicoes.domain.boletim_consulta import PoderPartido
from eleicoes.domain.grade import GradeDePoder, LugarVotos
from eleicoes.use_cases.grade import BuildPartyShareGrid


def test_share_uses_two_decimals_over_valid_votes_and_escapes_names() -> None:
    place = LugarVotos(
        "1392",
        "Rio <Branco>",
        (
            PoderPartido(1392, None, 22, 42407, 308, 215223),
            PoderPartido(1392, None, 13, 0, 0, 215223),
        ),
    )
    grade = BuildPartyShareGrid().execute(2026, 1, "AC", "dep<utado>", "municipio", (place,))
    page = html_da_grade(grade)
    assert "100,00%" in page
    assert "0,00%" in page
    assert "background-color:rgb(13,111,110);color:rgb(255,255,255)" in page
    assert "background-color:rgb(255,255,255)" in page
    assert "Rio &lt;Branco&gt;" in page
    assert "Rio <Branco>" not in page
    assert "dep&lt;utado&gt;" in page
    assert "nominais 42407, legenda 308, votos 42715, votos válidos 42715" in page
    assert '<th class="validos">Votos válidos</th>' in page
    assert '<td class="validos">42.715</td>' in page
    assert page.index("Votos válidos") < page.index(">22<")
    assert "<h1>Poder do partido</h1>" in page
    assert "Por município — 2026, turno 1, dep&lt;utado&gt;" in page
    assert "nominais e de legenda são somados" in page
    assert "Brancos e nulos ficam de fora" in page
    assert "sobre os votos válidos" in page
    assert "sem candidato a presidente conta como nulo" in page
    assert "<script" not in page
    assert "http://" not in page
    assert "https://" not in page
    assert 'charset="utf-8"' in page


def test_each_grade_keeps_its_own_color_scale() -> None:
    small = _grade("municipio", (LugarVotos("1", "A", (_party(1, 13, 10, 100),)),))
    mixed = _grade(
        "uf",
        (
            LugarVotos(
                "AC",
                "Acre",
                (_party(None, 10, 80, 100), _party(None, 20, 10, 100)),
            ),
        ),
    )
    page = html_das_grades((small, mixed))
    assert page.index("Por município") < page.index("Por estado")
    first, second = page.split("<section>")[1:]
    assert "rgb(13,111,110)" in _style(first, "100,00%")
    assert "rgb(13,111,110)" in _style(second, "88,89%")
    assert "rgb(13,111,110)" not in _style(second, "11,11%")


def test_text_turns_white_only_above_the_relative_threshold() -> None:
    grade = _grade(
        "pais",
        (
            LugarVotos(
                "BR",
                "Brasil",
                (
                    _party(None, 10, 80, 100),
                    _party(None, 20, 50, 100),
                    _party(None, 30, 40, 100),
                ),
            ),
        ),
    )
    page = html_da_grade(grade)
    assert "color:rgb(255,255,255)" in _style(page, "47,06%")
    assert "color:rgb(255,255,255)" in _style(page, "29,41%")
    assert "rgb(13,111,110)" not in _style(page, "29,41%")
    assert "color:rgb(20,20,20)" in _style(page, "23,53%")
    assert "No país" in page
    assert "AC" not in page


def test_estado_and_pais_headings_do_not_claim_the_passed_uf() -> None:
    state = _grade(
        "uf",
        (
            LugarVotos("AC", "Acre", (_party(None, 13, 1, 10),)),
            LugarVotos("SP", "São Paulo", (_party(None, 13, 1, 10),)),
        ),
        uf="RJ",
    )
    region = _grade(
        "regiao",
        (
            LugarVotos("NO", "Norte", (_party(None, 13, 1, 10),)),
            LugarVotos("SE", "Sudeste", (_party(None, 13, 1, 10),)),
        ),
    )
    page = html_das_grades((state, region))
    assert "Por estado — 2026, turno 1, presidente" in page
    assert "RJ" not in page
    assert "Por região — NO Norte, NE Nordeste, CO Centro-Oeste, SE Sudeste, S Sul" in page


def test_zero_turnout_stays_white() -> None:
    grade = _grade("municipio", (LugarVotos("1", "A", (_party(1, 13, 0, 0),)),))
    page = html_da_grade(grade)
    assert 'background-color:rgb(255,255,255);color:rgb(20,20,20)">0,00%' in page
    assert '<td class="validos">0</td>' in page


def _grade(
    nivel: str,
    places: tuple[LugarVotos, ...],
    *,
    uf: str = "AC",
) -> GradeDePoder:
    return BuildPartyShareGrid().execute(2026, 1, uf, "presidente", nivel, places)


def _party(municipio: int | None, partido: int, votos: int, comparecimento: int) -> PoderPartido:
    return PoderPartido(municipio, None, partido, votos, 0, comparecimento)


def _style(page: str, percent: str) -> str:
    found = re.search(rf'style="([^"]+)">{re.escape(percent)}', page)
    assert found is not None
    return found.group(1)
