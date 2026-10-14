"""HTML do mapa coroplético. O JavaScript é colado; as chaves não passam por format."""

import json
from html import escape
from typing import Final

from eleicoes.domain.mapa import PaginaDoMapa, Pintura, RecortePintado

_IBGE: Final = "Malha municipal e de estados: IBGE. Licença compatível com CC BY 4.0."
_REGIONS: Final = (
    "O recorte das regiões não entra neste mapa. A malha desse recorte ainda não foi medida."
)
_BSD: Final = (
    "Copyright (c) 2005-present, OpenLayers Contributors. All rights reserved. "
    "Redistribution and use in source and binary forms, with or without "
    "modification, are permitted provided that the following conditions are met: "
    "1. Redistributions of source code must retain the above copyright notice, this "
    "list of conditions and the following disclaimer. "
    "2. Redistributions in binary form must reproduce the above copyright notice, "
    "this list of conditions and the following disclaimer in the documentation "
    "and/or other materials provided with the distribution. "
    'THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" '
    "AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE "
    "IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE "
    "DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE "
    "FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL "
    "DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR "
    "SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER "
    "CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, "
    "OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE "
    "OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE."
)
_ISC: Final = (
    "Copyright (c) 2012-2019, Michael Bostock. "
    "Permission to use, copy, modify, and/or distribute this software for any "
    "purpose with or without fee is hereby granted, provided that the above "
    "copyright notice and this permission notice appear in all copies. "
    'THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH '
    "REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY AND "
    "FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY SPECIAL, DIRECT, "
    "INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM "
    "LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR "
    "OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR "
    "PERFORMANCE OF THIS SOFTWARE."
)
_PAGE_CSS: Final = "body { background: #ffffff; } #mapa { background: #ffffff; height: 80vh; }"
_PAGE_SCRIPT: Final = """\
(function () {
  var pintura = JSON.parse(document.getElementById("pintura").textContent);
  var municipios = JSON.parse(document.getElementById("municipios").textContent);
  var ufs = JSON.parse(document.getElementById("ufs").textContent);
  var paises = JSON.parse(document.getElementById("paises").textContent);

  function aplicar(topology, objectName, itens) {
    var porCodigo = {};
    for (var i = 0; i < itens.length; i++) {
      porCodigo[String(itens[i].codigo)] = itens[i];
    }
    var geometries = topology.objects[objectName].geometries;
    for (var j = 0; j < geometries.length; j++) {
      var geometry = geometries[j];
      var properties = geometry.properties || {};
      var code = properties.codarea;
      if (code === undefined || code === null) {
        code = geometry.id;
      }
      var item = porCodigo[String(code)];
      geometry.properties = properties;
      if (!item) {
        continue;
      }
      properties.cor = item.cor;
      properties.peso = item.peso;
      properties.numero = item.numero;
      properties.logo = pintura.logos[item.numero];
      properties.codigo = String(item.codigo);
    }
  }

  function colecao(topology, objectName) {
    return topojson.feature(topology, topology.objects[objectName]);
  }

  function soBrasil(collection, brasilId) {
    return {
      type: "FeatureCollection",
      features: collection.features.filter(function (feature) {
        return String(feature.id) === String(brasilId);
      })
    };
  }

  function estiloMundo() {
    return new ol.style.Style({
      fill: new ol.style.Fill({color: "#f7f7f7"}),
      stroke: new ol.style.Stroke({color: "#cccccc", width: 1})
    });
  }

  function estilo(feature) {
    var cor = feature.get("cor");
    if (!cor) {
      return estiloMundo();
    }
    var tinta = misturar(cor, feature.get("peso"));
    return new ol.style.Style({
      fill: new ol.style.Fill({color: tinta.fill}),
      stroke: new ol.style.Stroke({color: "#222222", width: 1}),
      text: new ol.style.Text({
        text: rotulo(feature.get("peso")),
        font: "12px sans-serif",
        overflow: true,
        fill: new ol.style.Fill({color: tinta.ink})
      })
    });
  }

  function misturar(cor, peso) {
    var fundo = document.body.getAttribute("data-fundo") || "#ffffff";
    var origem = canais(cor);
    var base = canais(fundo);
    var parte = fracao(peso);
    if (!origem || !base) {
      return {fill: cor, ink: "#111111"};
    }
    var rgb = [0, 1, 2].map(function (indice) {
      return Math.round(base[indice] + (origem[indice] - base[indice]) * parte);
    });
    var luma = (0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]) / 255;
    return {fill: "rgb(" + rgb.join(",") + ")", ink: luma > 0.62 ? "#111111" : "#f4f4f5"};
  }

  function rotulo(peso) {
    var partes = String(peso == null ? "" : peso).split("/");
    if (partes.length !== 2) {
      return "—";
    }
    var numerador = Number(partes[0]);
    var denominador = Number(partes[1]);
    if (!eInteiro(numerador) || !eInteiro(denominador) || denominador <= 0 || numerador < 0) {
      return "—";
    }
    var produto = numerador * 10000;
    var quociente = Math.floor(produto / denominador);
    var resto = produto % denominador;
    var arredondado = resto * 2 >= denominador ? quociente + 1 : quociente;
    var inteiro = Math.floor(arredondado / 100);
    var centesimos = String(arredondado % 100);
    if (centesimos.length < 2) {
      centesimos = "0" + centesimos;
    }
    return milhar(inteiro) + "," + centesimos + "%";
  }

  function eInteiro(valor) {
    return typeof valor === "number" && isFinite(valor) && Math.floor(valor) === valor;
  }

  function milhar(valor) {
    var texto = String(valor);
    var grupos = [];
    var indice = texto.length;
    while (indice > 0) {
      var inicio = Math.max(0, indice - 3);
      grupos.push(texto.slice(inicio, indice));
      indice = inicio;
    }
    return grupos.reverse().join(".");
  }

  function fracao(valor) {
    if (valor === undefined || valor === null || valor === "") {
      return 1;
    }
    var partes = String(valor).split("/");
    var numerador = Number(partes[0]);
    var denominador = partes.length === 2 ? Number(partes[1]) : 1;
    if (!isFinite(numerador) || !isFinite(denominador) || denominador === 0) {
      return 1;
    }
    return Math.min(1, Math.max(0, numerador / denominador));
  }

  function canais(cor) {
    var hex = String(cor).trim();
    if (hex.charAt(0) !== "#") {
      return null;
    }
    hex = hex.slice(1);
    if (hex.length === 3) {
      hex = hex[0] + hex[0] + hex[1] + hex[1] + hex[2] + hex[2];
    }
    if (hex.length !== 6 || /[^0-9a-fA-F]/.test(hex)) {
      return null;
    }
    return [
      parseInt(hex.slice(0, 2), 16),
      parseInt(hex.slice(2, 4), 16),
      parseInt(hex.slice(4, 6), 16)
    ];
  }

  function camada(geojson, style, minZoom, maxZoom) {
    var opcoes = {
      source: new ol.source.Vector({features: new ol.format.GeoJSON({
        dataProjection: "EPSG:4326",
        featureProjection: "EPSG:4326"
      }).readFeatures(geojson)}),
      declutter: false,
      style: style
    };
    if (minZoom !== null) {
      opcoes.minZoom = minZoom;
    }
    if (maxZoom !== null) {
      opcoes.maxZoom = maxZoom;
    }
    return new ol.layer.Vector(opcoes);
  }

  var mundo = colecao(paises, pintura.paisesObjeto);
  var itensPais = pintura.pais ? [pintura.pais] : [];
  aplicar(paises, pintura.paisesObjeto, itensPais);
  aplicar(ufs, pintura.ufsObjeto, pintura.ufs);
  aplicar(municipios, pintura.municipiosObjeto, pintura.municipios);
  var brasil = soBrasil(colecao(paises, pintura.paisesObjeto), pintura.brasilId);

  new ol.Map({
    target: "mapa",
    layers: [
      camada(mundo, estiloMundo, null, null),
      camada(brasil, estilo, null, 4),
      camada(colecao(ufs, pintura.ufsObjeto), estilo, 4, 6),
      camada(colecao(municipios, pintura.municipiosObjeto), estilo, 6, 28)
    ],
    view: new ol.View({projection: "EPSG:4326", center: [-54, -14], zoom: 3})
  });
})();
"""


def html_do_mapa(pagina: PaginaDoMapa) -> str:
    title = escape(_title(pagina))
    return (
        "<!DOCTYPE html>\n"
        '<html lang="pt-BR">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        f"<title>{title}</title>\n"
        f"{_style(pagina)}\n"
        "</head>\n"
        '<body data-fundo="#ffffff">\n'
        f"<h1>{title}</h1>\n"
        '<div id="mapa"></div>\n'
        f"{_footer(pagina)}\n"
        f"{_scripts(pagina)}\n"
        "</body>\n"
        "</html>\n"
    )


def _title(pagina: PaginaDoMapa) -> str:
    return f"Mapa de {pagina.cargo} — {pagina.ano}, turno {pagina.turno}"


def _style(pagina: PaginaDoMapa) -> str:
    return f"<style>{pagina.ol_css}{_PAGE_CSS}</style>"


def _footer(pagina: PaginaDoMapa) -> str:
    notes = "".join(f"<p>{escape(note)}</p>" for note in (_IBGE, _BSD, _ISC, _REGIONS))
    return f"<footer>{notes}{_holes(pagina.recorte.sem_poligono)}</footer>"


def _holes(lines: tuple[str, ...]) -> str:
    if not lines:
        return "<p>Nenhum lugar com líder ficou fora da malha.</p>"
    items = "".join(f"<li>{escape(line)}</li>" for line in lines)
    return f"<h2>Sem polígono</h2><ul>{items}</ul>"


def _scripts(pagina: PaginaDoMapa) -> str:
    payload = json.dumps(_payload(pagina), ensure_ascii=False)
    parts = (
        _json_tag("pintura", payload),
        _json_tag("municipios", pagina.municipios),
        _json_tag("ufs", pagina.ufs),
        _json_tag("paises", pagina.paises),
        _script_tag(pagina.topojson_js),
        _script_tag(pagina.ol_js),
        _script_tag(_PAGE_SCRIPT),
    )
    return "\n".join(parts)


def _json_tag(ident: str, text: str) -> str:
    body = _escape_close(text)
    return f'<script type="application/json" id="{ident}">{body}</script>'


def _script_tag(text: str) -> str:
    return f"<script>{_escape_close(text)}</script>"


def _escape_close(text: str) -> str:
    return text.replace("</", "<\\/")


def _payload(pagina: PaginaDoMapa) -> dict[str, object]:
    recorte = pagina.recorte
    country = None if recorte.pais is None else _item(recorte.pais)
    return {
        "logos": _logos(recorte),
        "pais": country,
        "ufs": [_item(item) for item in recorte.ufs],
        "municipios": [_item(item) for item in recorte.municipios],
        "brasilId": pagina.brasil_id,
        "ufsObjeto": pagina.ufs_objeto,
        "municipiosObjeto": pagina.municipios_objeto,
        "paisesObjeto": pagina.paises_objeto,
    }


def _logos(recorte: RecortePintado) -> dict[str, str]:
    logos: dict[str, str] = {}
    for painting in _paintings(recorte):
        logos.setdefault(painting.numero, painting.logo)
    return logos


def _paintings(recorte: RecortePintado) -> tuple[Pintura, ...]:
    country = () if recorte.pais is None else (recorte.pais,)
    return country + recorte.ufs + recorte.municipios


def _item(pintura: Pintura) -> dict[str, str]:
    return {
        "codigo": pintura.codigo,
        "cor": pintura.cor,
        "numero": pintura.numero,
        "peso": pintura.peso,
    }
