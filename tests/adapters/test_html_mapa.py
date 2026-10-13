"""HTML of the leader choropleth. Libraries stay inline and braces stay single."""

import json
from dataclasses import replace

from eleicoes.adapters.html_mapa import html_do_mapa
from eleicoes.domain.mapa import PaginaDoMapa, Pintura, RecortePintado

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
    "ol.style.Icon",
    "ol.geom.Point",
    "declutter: false",
    "overflow: true",
    "function soBrasil",
    "camada(mundo, estiloMundo, null, null)",
    "camada(brasil, estilo, null, 4)",
    "camada(colecao(ufs, pintura.ufsObjeto), estilo, 4, 6)",
    "camada(colecao(municipios, pintura.municipiosObjeto), estilo, 6, 28)",
    "properties.logo = pintura.logos[item.numero]",
    'var centroide = feature.get("centroide");',
    "new ol.geom.Point(centroide)",
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
    assert pintura["pais"] == {"codigo": "076", "cor": "#112233", "numero": "22"}
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
