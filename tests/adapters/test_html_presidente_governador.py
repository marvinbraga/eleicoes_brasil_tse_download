"""HTML of the president × governor page. Bootstrap, theme, and escaped text."""

from tests.domain.test_presidente_governador import _city

from eleicoes.adapters.html_presidente_governador import html_presidente_governador
from eleicoes.domain.presidente_governador import (
    MunicipalPlace,
    view_from_places,
)


def test_margin_displays_half_up_percentage_points() -> None:
    wide = _city(
        "AC",
        "1",
        "Rio Branco (AC)",
        ((13, 400, 0), (22, 350, 0), (14, 250, 0)),
        ((13, 1, 0),),
    )
    half = _city(
        "AC",
        "2",
        "Cruzeiro (AC)",
        ((13, 10500, 0), (22, 9499, 0), (14, 1, 0)),
        ((22, 1, 0),),
    )
    shares = _city(
        "AC",
        "3",
        "Brasiléia (AC)",
        ((13, 550, 0), (22, 450, 0)),
        ((13, 1, 0),),
    )
    wide_html = html_presidente_governador(view_from_places(2026, 1, (wide,)))
    half_html = html_presidente_governador(view_from_places(2026, 1, (half,)))
    share_html = html_presidente_governador(view_from_places(2026, 1, (shares,)))
    assert ">5,00</td>" in wide_html
    assert ">40,00%</td>" in wide_html
    assert ">5,01</td>" in half_html
    assert ">5,00</td>" not in half_html
    assert ">45,00%</td>" in share_html
    assert ">55,00%</td>" in share_html


def test_page_escapes_a_hostile_name_and_states_the_rules() -> None:
    hostile = 'Rio <Branco> & "Norte"'
    place = _city("AC", "1", hostile, ((13, 10, 0),), ((13, 1, 0),))
    html = html_presidente_governador(view_from_places(2026, 1, (place,)))
    assert hostile not in html
    assert "Rio &lt;Branco&gt; &amp; &quot;Norte&quot;" in html
    assert "<script>alert" not in html
    bootstrap = "https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css"
    assert html.count(bootstrap) == 1
    assert 'data-bs-theme="dark"' in html
    assert ">Claro</button>" in html
    assert ">Escuro</button>" in html
    assert "aria-sort" in html
    assert "function reorder" in html or "reorder(table" in html
    margin = (
        "A margem é o líder menos o segundo, sobre os votos válidos de presidente, "
        "em pontos percentuais."
    )
    governor_rule = (
        "A classe compara o partido do governador com esses dois partidos da presidência."
    )
    assert margin in html
    assert governor_rule in html
    assert "Brancos e nulos ficam de fora do percentual, da margem e da classe." in html
    assert "Número sem candidato a presidente conta como nulo." in html
    assert "Presidente e governador" in html


def test_missing_runner_up_and_governor_render_an_em_dash() -> None:
    place = _city("ZZ", "1", "Lisboa (ZZ)", ((13, 10, 0),), None, branco=2, nulo=3)
    html = html_presidente_governador(view_from_places(2026, 1, (place,)))
    row = html.split(">Lisboa (ZZ)</td>", 1)[1].split("</tr>", 1)[0]
    assert row.count("—") == 6
    assert "Sem governador" in row
    assert "2 (" in row
    assert "3 (" in row


def test_two_municipal_tables_follow_uf_order_and_the_tightest_margin() -> None:
    places = (
        _city("PA", "9", "Folga (PA)", ((13, 90, 0), (22, 10, 0)), ((13, 1, 0),)),
        _city("AC", "2", "Folga (AC)", ((13, 90, 0), (22, 10, 0)), ((13, 1, 0),)),
        _city("AC", "1", "Apertada (AC)", ((13, 51, 0), (22, 49, 0)), ((13, 1, 0),)),
    )
    html = html_presidente_governador(view_from_places(2026, 1, places))
    assert html.index("Acre (AC)") < html.index("Pará (PA)")
    municipal = html.split('id="municipio"', 1)[1].split('id="estado"', 1)[0]
    assert municipal.index("Apertada (AC)") < municipal.index("Folga (AC)")
    assert html.count("<h3") == 2


def test_composition_keeps_city_counts_and_presidential_blank_totals() -> None:
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
    html = html_presidente_governador(view_from_places(2026, 1, places))
    composition = html.split('id="composicao"', 1)[1].split('id="municipio"', 1)[0]
    state = html.split('id="estado"', 1)[1].split('id="regiao"', 1)[0]
    assert composition.index("Consolidação") < composition.index("Terreno de virada")
    assert composition.index("Terreno de virada") < composition.index("Em aberto")
    assert composition.index("Em aberto") < composition.index("Sem governador")
    assert ">140</td>" in composition or ">140<" in composition
    assert ">130</td>" in composition or ">130<" in composition
    assert "Brancos de presidente: 10." in composition
    assert "Nulos de presidente: 3." in composition
    assert "Terreno de virada" not in state
    assert "Consolidação" in state
    assert 'id="pais"' in html
    assert "Por região" in html
    assert "No país" in html


def test_headers_name_the_two_readings() -> None:
    place = MunicipalPlace(
        "AC",
        "1",
        "Rio Branco (AC)",
        _cargo(),
        _cargo(),
    )
    html = html_presidente_governador(view_from_places(2026, 1, (place,)))
    for label in (
        "Lugar",
        "Líder presidente",
        "Segundo",
        "Margem",
        "Brancos presidente",
        "Nulos presidente",
        "Líder governador",
        "Brancos governador",
        "Nulos governador",
        "Classe",
    ):
        assert label in html


def _cargo() -> object:
    from eleicoes.domain.presidente_governador import CargoTally, PartyTally

    return CargoTally((PartyTally(13, 10, 0),), 1, 2)
