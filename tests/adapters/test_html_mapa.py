"""HTML of the leader choropleth. Libraries stay inline and braces stay single."""

import json
from dataclasses import replace
from fractions import Fraction

from eleicoes.adapters.html_mapa import html_do_mapa
from eleicoes.domain.mapa import Marca, PaginaDoMapa, Pintura, PontoPintado, RecortePintado
from eleicoes.domain.mapa_turnos import Apuracao, Leitura, LugarTurnos

_LOGO = "data:image/png;base64,QQ=="
_MUNICIPIOS = (
    '{"type":"Topology","objects":{"malha":{"type":"GeometryCollection",'
    '"geometries":[{"type":"Polygon","id":"1200138","arcs":[],"properties":'
    '{"codarea":"1200138","nome":"</script>","centroide":[-67.8,-9.8]}}]}},'
    '"arcs":[]}'
)
_UFS = (
    '{"type":"Topology","objects":{"ufs":{"type":"GeometryCollection",'
    '"geometries":[{"type":"Polygon","id":"12","arcs":[],'
    '"properties":{"codarea":"12"}}]}},"arcs":[]}'
)
_PAISES = (
    '{"type":"Topology","objects":{"countries":{"type":"GeometryCollection",'
    '"geometries":['
    '{"type":"Polygon","id":"076","arcs":[],"properties":{"codarea":"076"}},'
    '{"type":"Polygon","id":"242","arcs":[],"properties":{"codarea":"242"}}'
    ']}},"arcs":[]}'
)
_BANNED = (
    'type="module"',
    "fromlonlat",
    "epsg:3857",
    "openstreetmap",
    "natural earth",
    "maplibre",
    "leaflet",
    "dt_geracao",
    "cd_municipio_tse",
)
_REQUIRED = (
    "EPSG:4326",
    "topojson.feature",
    "ol.format.GeoJSON",
    "ol.style.Fill",
    "ol.style.Text",
    "declutter: declutter === true",
    "overflow: true",
    "function soBrasil",
    "camada(mundo, estiloMundo, null, null)",
    "camada(brasil, estilo, null, 4)",
    "camada(colecao(ufs, pintura.ufsObjeto), estilo, 4, 6)",
    "camada(colecao(municipios, pintura.municipiosObjeto), estilo, 6, 28, true)",
    "properties.logo = pintura.logos[item.numero]",
    "IBGE",
    "OpenLayers Contributors",
    "Redistributions in binary form",
    "Michael Bostock",
    "Permission to use, copy, modify",
    "O recorte das regiões não entra neste mapa.",
    "Sem polígono",
    "Boa Esperança do Norte (MT)",
    "Lisboa (ZZ)",
    "AS IS",
)


def _paint(codigo: str) -> Pintura:
    return Pintura(codigo, "#112233", "22", _LOGO)


def _page(
    holes: tuple[str, ...] = ("Boa Esperança do Norte (MT)", "Lisboa (ZZ)"),
    cargo: str = "presidente",
) -> PaginaDoMapa:
    return PaginaDoMapa(
        2026,
        1,
        cargo,
        RecortePintado(_paint("076"), (_paint("12"),), (_paint("1200138"),), holes),
        _MUNICIPIOS,
        _UFS,
        _PAISES,
        "malha",
        "ufs",
        "countries",
        "076",
        "var ol=1;",
        ".ol{}",
        "var topojson=1;",
    )


def _block(html: str, ident: str) -> str:
    return html.split(f'id="{ident}">', 1)[1].split("</script>", 1)[0]


def test_page_renders_the_leader_choropleth() -> None:
    html = html_do_mapa(_page())
    folded = html.casefold()
    style = html.split("<style>", 1)[1].split("</style>", 1)[0]
    mundo = html.split("function estiloMundo()", 1)[1].split("function estilo(", 1)[0]
    pintura = json.loads(_block(html, "pintura"))
    municipios = _block(html, "municipios")
    geometry = json.loads(municipios)["objects"]["malha"]["geometries"][0]
    body_rule = style.split("body", 1)[1].split("}", 1)[0]
    mapa_rule = style.split("#mapa", 1)[1].split("}", 1)[0]

    assert html.startswith("<!DOCTYPE html>")
    assert '<html lang="pt-BR">' in html
    assert "<title>Mapa de presidente — 2026, turno 1</title>" in html
    assert "var ol=1;" in html
    assert "var topojson=1;" in html
    assert ".ol{}" in style
    assert "background: #ffffff" in body_rule
    assert "background: #ffffff" in mapa_rule
    assert "height: 80vh" in mapa_rule
    assert 'get("cor")' not in mundo
    assert html.count("QQ==") == 1
    assert pintura["logos"] == {"22": _LOGO}
    assert pintura["pais"] == {
        "codigo": "076",
        "cor": "#112233",
        "numero": "22",
        "peso": "1/1",
        "nome": "",
        "segundo": "",
        "votosSegundo": 0,
        "branco": 0,
        "nulo": 0,
        "classe": "",
        "governador": "",
        "pesoGovernador": "",
    }
    assert "properties.peso = item.peso" in html
    assert "properties.nome = item.nome" in html
    assert 'data-fundo="#ffffff"' in html
    assert 'rotulo(feature.get("nome"), feature.get("numero"), feature.get("peso"));' in html
    assert "var texto = CRUZAMENTO ? rotuloCruzado(feature) :" in html
    assert "function rotulo(nome, numero, peso)" in html
    assert "if (numerador === 0)" in html
    assert "milhar(denominador)" in html
    assert 'linhas.join("\\n")' in html
    assert "resto * 2 >= denominador" in html
    assert 'return milhar(inteiro) + "," + centesimos + "%"' in html
    assert "logo" not in pintura["pais"]
    assert "242" not in _block(html, "pintura")
    assert "242" in _block(html, "paises")
    assert "</script>" not in municipios
    assert "<\\/script>" in municipios
    assert geometry["properties"]["nome"] == "</script>"
    assert geometry["properties"]["centroide"] == [-67.8, -9.8]
    assert "camada(brasil, estilo, 0, 4)" not in html
    assert "minZoom: 0" not in html
    assert "{{" not in html
    assert html.index("var topojson=1;") < html.index("var ol=1;")
    assert html.index("var ol=1;") < html.index("function soBrasil")
    for banned in _BANNED:
        assert banned not in folded
    for required in _REQUIRED:
        assert required in html


def test_municipal_label_follows_zoom_and_valid_votes() -> None:
    html = html_do_mapa(_page())

    assert "var ZOOM_MUNICIPIOS = 6;" in html
    assert "var ZOOM_TODOS = 11;" in html
    assert "var PISO_INICIAL = 800000;" in html
    assert "function rotuloVisivel(feature, resolution, geometria, texto)" in html
    assert "function ehMunicipio(feature)" in html
    assert "codigo.length >= 6" in html
    assert "function minimoDeVotos(zoom)" in html
    assert "function votosValidos(peso)" in html
    assert "function maiorParte(feature)" in html
    assert "!(zoom >= ZOOM_MUNICIPIOS) || zoom >= ZOOM_TODOS" in html
    assert "vista.getZoomForResolution(resolution)" in html
    assert (
        "var FAIXAS_DE_ROTULO = [[6.5, 400000], [7, 150000], [7.5, 60000], "
        "[8, 25000], [8.5, 10000]];"
    ) in html
    assert "zoom >= FAIXAS_DE_ROTULO[i][0]" in html
    assert "function cabeNaTela(geometria, texto, resolution)" in html
    assert "cabeNaTela(geometria, texto, resolution)" in html
    assert "maisLonga * LARGURA_DO_CARACTERE" in html
    assert "linhas.length * ALTURA_DA_LINHA" in html
    assert 'zIndex: emDestaque ? Z_DESTAQUE : votosValidos(feature.get("peso"))' in html
    assert 'geometria.getType() !== "MultiPolygon"' in html
    assert "view: vista" in html


def test_page_shows_current_zoom() -> None:
    html = html_do_mapa(_page())

    assert '<div id="mapa"><div id="zoom" aria-live="polite"></div>' in html
    assert "#zoom {" in html
    assert "function mostrarZoom()" in html
    assert 'vista.on("change:resolution", mostrarZoom);' in html
    assert "minimoDeVotos(zoom)" in html
    assert 'detalhe += " · só nomes";' in html


def test_low_zoom_municipal_label_shows_only_the_name() -> None:
    html = html_do_mapa(_page())

    assert "var ZOOM_ROTULO_COMPLETO = 9;" in html
    assert "function textoDoRotulo(feature, resolution, completo)" in html
    assert (
        "vista.getZoomForResolution(resolution) >= ZOOM_ROTULO_COMPLETO ? texto : String(nome)"
    ) in html


def test_abroad_places_become_points_on_top() -> None:
    page = _page()
    lisboa = replace(Pintura("29955", "#445566", "13", "data:image/png;base64,Qg=="), nome="LISBOA")
    ponto = PontoPintado(lisboa, -9.1393, 38.7223)
    html = html_do_mapa(replace(page, recorte=replace(page.recorte, exterior=(ponto,))))
    pintura = json.loads(_block(html, "pintura"))

    assert pintura["exterior"] == [
        {
            "codigo": "29955",
            "cor": "#445566",
            "numero": "13",
            "peso": "1/1",
            "nome": "LISBOA",
            "segundo": "",
            "votosSegundo": 0,
            "branco": 0,
            "nulo": 0,
            "classe": "",
            "governador": "",
            "pesoGovernador": "",
            "lon": -9.1393,
            "lat": 38.7223,
        }
    ]
    assert pintura["logos"]["13"] == "data:image/png;base64,Qg=="
    assert "function estiloPonto(feature, resolution)" in html
    assert 'declutterMode: "obstacle"' in html
    assert "var VOTOS_DO_RAIO_MAXIMO = 30000;" in html
    assert 'geometry: {type: "Point", coordinates: [item.lon, item.lat]}' in html
    assert "camada(colecaoDePontos(pintura.exterior || []), estiloPonto, null, null, true)" in html
    assert "{hitTolerance: 4}" in html
    assert r'.replace(/ \(ZZ\)$/, "")' in html
    mundo = html.split("function estiloMundo()", 1)[1].split("function estilo(", 1)[0]
    assert "estiloPonto" not in mundo


def test_legend_lists_parties_with_marks_and_acronyms() -> None:
    page = _page()
    marcas = {
        "22": Marca("#112233", _LOGO, "PL"),
        "13": Marca("#e15759", "data:image/png;base64,Qw==", "PT"),
        "55": Marca("#aabbcc", "data:image/png;base64,RA==", ""),
    }
    html = html_do_mapa(replace(page, recorte=replace(page.recorte, marcas=marcas)))
    pintura = json.loads(_block(html, "pintura"))

    assert pintura["siglas"] == {"22": "PL", "13": "PT"}
    assert pintura["logos"] == {
        "22": _LOGO,
        "13": "data:image/png;base64,Qw==",
        "55": "data:image/png;base64,RA==",
    }
    assert '<div id="legenda" class="ol-unselectable">' in html
    assert 'aria-controls="legenda-itens">Partidos</button>' in html
    assert "Tom mais forte: fatia maior dos votos válidos do líder." in html
    assert "#legenda {" in html
    assert "function montarLegenda()" in html
    assert "function resumoDaLideranca(linha)" in html
    assert "new ol.control.Control({element: painelLegenda})" in html
    assert 'var TELA_ESTREITA = window.matchMedia("(max-width: 640px)").matches;' in html
    assert "alternarLegenda(!TELA_ESTREITA);" in html
    assert 'return sigla ? sigla + " " + numero : String(numero);' in html
    assert 'posicao + " · " + nomeDoPartido(numero)' in html
    assert "amostra.style.background = linha.cor;" in html


def test_cross_map_paints_by_class_and_explains_it() -> None:
    page = _page(cargo="cruzamento")
    city = replace(
        _paint("1200138"), classe="terreno_de_virada", governador="13", peso_governador="5/9"
    )
    html = html_do_mapa(replace(page, recorte=replace(page.recorte, municipios=(city,))))
    pintura = json.loads(_block(html, "pintura"))

    assert "<title>Mapa de presidente × governador — 2026, turno 1</title>" in html
    assert pintura["cargo"] == "cruzamento"
    item = pintura["municipios"][0]
    assert (item["classe"], item["governador"], item["pesoGovernador"]) == (
        "terreno_de_virada",
        "13",
        "5/9",
    )
    assert 'var CRUZAMENTO = visaoAtual === "cruzamento";' in html
    assert 'cor: "#d95f02"' in html
    assert 'cor: "#3a5fcd"' in html
    assert 'cor: "#7570b3"' not in html
    assert 'return CRUZAMENTO && classe ? classe.cor : feature.get("cor");' in html
    assert "function rotuloCruzado(feature)" in html
    assert "function detalharClasse(feature)" in html
    assert "function detalharGovernador(feature)" in html
    assert "function montarLegendaCruzada()" in html
    assert "properties.pesoGovernador = item.pesoGovernador;" in html
    mundo = html.split("function estiloMundo()", 1)[1].split("function estilo(", 1)[0]
    assert "CLASSES" not in mundo


def test_leader_map_keeps_the_leader_title() -> None:
    html = html_do_mapa(_page())

    assert "<title>Mapa de presidente — 2026, turno 1</title>" in html
    assert json.loads(_block(html, "pintura"))["cargo"] == "presidente"


def test_page_carries_the_other_views_for_the_switcher() -> None:
    page = _page(cargo="cruzamento")
    governor = replace(
        page.recorte,
        municipios=(replace(_paint("1200138"), numero="45", logo="data:image/png;base64,RQ=="),),
    )
    marcas = {"45": Marca("#abcdef", "data:image/png;base64,RQ==", "PSDB")}
    governor = replace(governor, marcas=marcas)
    html = html_do_mapa(
        replace(page, recortes={"presidente": page.recorte, "governador": governor})
    )
    pintura = json.loads(_block(html, "pintura"))

    assert pintura["cargo"] == "cruzamento"
    assert list(pintura["visoes"]) == ["governador"]
    assert pintura["visoes"]["governador"]["municipios"][0]["numero"] == "45"
    assert set(pintura["visoes"]["governador"]) == {"pais", "ufs", "municipios", "exterior"}
    assert pintura["logos"]["45"] == "data:image/png;base64,RQ=="
    assert pintura["siglas"] == {"45": "PSDB"}
    assert pintura["titulos"] == {
        "presidente": "Mapa de presidente — 2026, turno 1",
        "governador": "Mapa de governador — 2026, turno 1",
        "cruzamento": "Mapa de presidente × governador — 2026, turno 1",
    }
    assert '<div id="visoes" class="ol-unselectable" role="group"' in html
    assert "#visoes {" in html
    assert "function trocarVisao(nome)" in html
    assert "function repintar(camadaAlvo, itens)" in html
    assert "window.location.replace(enderecoDaVisao(nome));" in html
    assert 'return "#visao=" + nome;' in html
    assert 'window.addEventListener("hashchange", function () {' in html
    assert "new ol.control.Control({element: painelVisoes})" in html
    assert 'if (nome === "governador" || ehComparativo(nome)) {' in html


def test_page_without_extra_views_has_no_other_views() -> None:
    assert json.loads(_block(html_do_mapa(_page()), "pintura"))["visoes"] == {}


def test_page_without_marks_has_no_acronyms() -> None:
    assert json.loads(_block(html_do_mapa(_page()), "pintura"))["siglas"] == {}


def test_page_without_abroad_points_has_empty_list() -> None:
    assert json.loads(_block(html_do_mapa(_page()), "pintura"))["exterior"] == []


def test_hover_highlights_and_details_the_place() -> None:
    page = _page()
    city = replace(_paint("1200138"), segundo="13", votos_segundo=7, branco=2, nulo=1)
    html = html_do_mapa(replace(page, recorte=replace(page.recorte, municipios=(city,))))
    pintura = json.loads(_block(html, "pintura"))

    assert '<div id="detalhe" role="tooltip" hidden></div>' in html
    assert "#detalhe {" in html
    assert "pointer-events: none" in html
    assert pintura["municipios"][0]["segundo"] == "13"
    assert pintura["municipios"][0]["votosSegundo"] == 7
    assert pintura["municipios"][0]["branco"] == 2
    assert pintura["municipios"][0]["nulo"] == 1
    assert "properties.votosSegundo = item.votosSegundo;" in html
    assert "var emDestaque = feature === destacado;" in html
    assert 'misturar(corDoLugar(feature), emDestaque ? "1/1" : feature.get("peso"))' in html
    assert 'font: emDestaque ? "bold 14px sans-serif" : "12px sans-serif"' in html
    assert 'zIndex: emDestaque ? Z_DESTAQUE : votosValidos(feature.get("peso"))' in html
    assert "new ol.Overlay({element: painelDetalhe, stopEvent: false})" in html
    assert 'mapa.on("pointermove"' in html
    assert 'mapa.on("singleclick"' in html
    assert 'addEventListener("pointerleave"' in html
    assert "novo.textContent = texto;" in html
    assert "innerHTML" not in html.split("(function () {", 1)[1]
    assert '"Margem: " + margem' in html


def test_hostile_hole_is_escaped() -> None:
    html = html_do_mapa(_page(holes=("<script>",)))
    assert "<li>&lt;script&gt;</li>" in html
    assert "<li><script>" not in html


def test_empty_holes_and_governor_title() -> None:
    html = html_do_mapa(_page(holes=(), cargo="governador"))
    assert "Mapa de governador — 2026, turno 1" in html
    assert "Nenhum lugar com líder ficou fora da malha." in html


def test_missing_country_is_json_null() -> None:
    base = _page(holes=())
    recorte = RecortePintado(None, base.recorte.ufs, base.recorte.municipios, ())
    html = html_do_mapa(replace(base, recorte=recorte))
    assert json.loads(_block(html, "pintura"))["pais"] is None


def test_turnos_view_carries_scenarios_counts_and_readings() -> None:
    from eleicoes.domain.mapa_turnos import Apuracao, Leitura, LugarTurnos, cenarios
    from eleicoes.domain.mapa_turnos import ComparativoTurnos as Comparativo

    lugar = LugarTurnos(
        "1200138",
        "BUJARI (AC)",
        "AC",
        Apuracao(400, 500, 100, 1, 2),
        Apuracao(520, 480, 0, 3, 4),
        tuple(
            Leitura(Fraction(1, 2), Fraction(13, 25), 20, 1.23456, "dentro")
            for _ in cenarios(22, 13)
        ),
    )
    comparativo = Comparativo(
        22, 13, cenarios(22, 13), lugar, (lugar,), (lugar,), (), ("AC",), 0, ()
    )
    html = html_do_mapa(replace(_page(), turnos=comparativo))
    pintura = json.loads(_block(html, "pintura"))
    turnos = pintura["turnos"]

    assert turnos["a"] == "22"
    assert turnos["padrao"] == "todosa"
    assert turnos["cobertura"] == ["AC"]
    assert turnos["municipios"][0]["primeiro"] == [400, 500, 100, 1, 2]
    assert turnos["municipios"][0]["leituras"][0] == [0.5, 20, 1.235, "dentro"]
    assert pintura["titulos"]["turnos"] == "Mapa de presidente — 2026, 1º × 2º turno"
    assert '<div id="turnos-controles" class="ol-unselectable" hidden></div>' in html
    assert 'turnos: "1º × 2º turno"' in html
    assert 'return String(item.codigo).length < 6 && item.uf !== "ZZ";' in html


def test_page_without_second_round_has_no_turnos() -> None:
    pintura = json.loads(_block(html_do_mapa(_page()), "pintura"))

    assert pintura["turnos"] is None
    assert "turnos" not in pintura["titulos"]


def _lugar_de_bujari(primeiro: Apuracao) -> LugarTurnos:
    leitura = Leitura(Fraction(1, 2), Fraction(13, 25), 20, None, "sem_base")
    return LugarTurnos(
        "1200138",
        "BUJARI (AC)",
        "AC",
        primeiro,
        Apuracao(520, 480, 0, 3, 4),
        (leitura,) * 5,
    )


def test_turnos_payload_carries_the_eliminated_groups_per_place() -> None:
    from eleicoes.domain.mapa_turnos import ComparativoTurnos as Comparativo
    from eleicoes.domain.mapa_turnos import GrupoEliminado, cenarios

    lugar = _lugar_de_bujari(Apuracao(400, 500, 100, 1, 2, ((30, 20), (70, 70), (80, 10))))
    grupos = (
        GrupoEliminado(70, frozenset({70}), Fraction(289, 10000)),
        GrupoEliminado(0, frozenset({30, 80}), Fraction(37, 10000)),
    )
    comparativo = Comparativo(
        22, 13, cenarios(22, 13), None, (), (lugar,), (), ("AC",), 0, (), grupos
    )
    html = html_do_mapa(replace(_page(), turnos=comparativo))
    turnos = json.loads(_block(html, "pintura"))["turnos"]

    assert turnos["eliminados"] == [
        {"numero": "70", "fatia": 0.0289},
        {"numero": "0", "fatia": 0.0037},
    ]
    assert turnos["municipios"][0]["eliminados"] == [70, 30]
    assert [item["parte"] for item in turnos["cenarios"]] == [1.0, 0.75, 0.5, None, 0.25]
    assert 'opcoes.push([PERSONALIZADO, "Personalizado"]);' in html
    assert '"&personalizado=" + codigoDosDestinos()' in html


def test_turnos_without_groups_omit_the_breakdown() -> None:
    from eleicoes.domain.mapa_turnos import ComparativoTurnos as Comparativo
    from eleicoes.domain.mapa_turnos import cenarios

    lugar = _lugar_de_bujari(Apuracao(400, 500, 0, 1, 2))
    comparativo = Comparativo(22, 13, cenarios(22, 13), None, (), (lugar,), (), ("AC",), 0, ())
    turnos = json.loads(_block(html_do_mapa(replace(_page(), turnos=comparativo)), "pintura"))[
        "turnos"
    ]

    assert turnos["eliminados"] == []
    assert "eliminados" not in turnos["municipios"][0]


def test_governor_turnos_carry_the_finalists_of_each_uf() -> None:
    from eleicoes.domain.mapa_turnos import GOVERNADOR, cenarios_de_governador
    from eleicoes.domain.mapa_turnos import ComparativoTurnos as Comparativo

    lugar = replace(
        _lugar_de_bujari(Apuracao(400, 500, 0, 1, 2)),
        leituras=(Leitura(Fraction(1, 2), Fraction(13, 25), 20, None, "sem_base"),) * 4,
    )
    comparativo = Comparativo(
        0,
        0,
        cenarios_de_governador(),
        None,
        (),
        (lugar,),
        (),
        ("AC",),
        0,
        (),
        cargo=GOVERNADOR,
        finalistas_por_uf={"AC": (10, 11)},
    )
    html = html_do_mapa(replace(_page(), turnos_governador=comparativo))
    pintura = json.loads(_block(html, "pintura"))

    assert pintura["turnos"] is None
    assert pintura["turnosgov"]["finalistas"] == {"AC": ["10", "11"]}
    assert pintura["turnosgov"]["a"] is None
    assert pintura["turnosgov"]["padrao"] == "dividido"
    assert pintura["titulos"]["turnosgov"] == "Mapa de governador — 2026, 1º × 2º turno"
    assert 'turnosgov: "Governador 1º × 2º"' in html
    assert 'var chave = TURNOS.cargo + "|" + metrica + "|" + estadoTurnos.cenario +' in html


def test_turnos_controls_export_a_csv_for_excel() -> None:
    html = html_do_mapa(_page())

    assert 'var baixar = elemento("button", "Baixar CSV");' in html
    assert 'new Blob(["\\uFEFF" + linhas.join("\\r\\n") + "\\r\\n"],' in html
    assert 'return campos.map(campoDoCsv).join(";");' in html
    assert 'return valor.toFixed(casas).replace(".", ",");' in html


def test_narrow_screens_fold_the_turnos_controls_and_scroll_the_views_bar() -> None:
    html = html_do_mapa(_page())

    assert " @media (max-width: 640px) {" in html
    assert " #visoes { left: 2.6em; right: .5em; transform: none; overflow-x: auto;" in html
    assert " #turnos-controles .alternar { display: block; } }" in html
    assert 'var alternar = elemento("button", "Cenário e pintura");' in html
    assert "var controlesAbertos = !TELA_ESTREITA;" in html
    assert "painelVisoes.scrollLeft = botoes[i].offsetLeft -" in html
