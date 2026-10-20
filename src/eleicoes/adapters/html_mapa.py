"""HTML do mapa coroplético. O JavaScript é colado; as chaves não passam por format."""

import json
from html import escape
from typing import Final

from eleicoes.domain.mapa import PaginaDoMapa, Pintura, PontoPintado, RecortePintado

_IBGE: Final = "Malha municipal e de estados: IBGE. Licença compatível com CC BY 4.0."
_CARGO_NO_TITULO: Final = {"cruzamento": "presidente × governador"}
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
_PAGE_CSS: Final = (
    "body { background: #ffffff; } #mapa { background: #ffffff; height: 80vh; }"
    " #zoom { position: absolute; left: .5em; bottom: .5em; padding: .25em .5em;"
    " background: rgba(255,255,255,.85); border: 1px solid #cccccc; border-radius: 4px;"
    " font: 12px sans-serif; color: #111111; }"
    " #detalhe { background: #ffffff; color: #111111; border: 1px solid #888888;"
    " border-radius: 6px; padding: .5em .75em; font: 13px/1.5 sans-serif;"
    " box-shadow: 0 2px 8px rgba(0,0,0,.25); pointer-events: none; white-space: nowrap; }"
    " #detalhe strong { display: block; font-size: 14px; margin-bottom: .25em; }"
    " #detalhe .partido { display: flex; align-items: center; gap: .4em; }"
    " #detalhe img { height: 20px; width: auto; }"
    " #detalhe .secao { margin-top: .4em; font-weight: bold; }"
    " #detalhe .classe { display: flex; align-items: center; gap: .4em; font-weight: bold; }"
    " #detalhe .amostra { width: 12px; height: 12px; border-radius: 2px; flex: none; }"
    " #detalhe small { display: block; max-width: 22em; white-space: normal; opacity: .8; }"
    " #legenda { position: absolute; top: .5em; right: .5em; max-height: calc(100% - 1em);"
    " max-width: min(20em, calc(100% - 4em)); box-sizing: border-box;"
    " overflow: auto; background: rgba(255,255,255,.92); border: 1px solid #cccccc;"
    " border-radius: 6px; padding: .4em .6em; font: 12px/1.4 sans-serif; color: #111111; }"
    " #legenda button { font: bold 12px sans-serif; background: none; border: 0; padding: 0;"
    " color: inherit; cursor: pointer; }"
    " #legenda button::after { content: ' ▾'; }"
    " #legenda button[aria-expanded='false']::after { content: ' ▸'; }"
    " #legenda ul { list-style: none; margin: .4em 0 0; padding: 0; }"
    " #legenda li { display: flex; align-items: center; gap: .45em; margin: .3em 0; }"
    " #legenda .amostra { width: 12px; height: 12px; border-radius: 2px; flex: none;"
    " border: 1px solid rgba(0,0,0,.35); }"
    " #legenda .logo { width: 40px; height: 20px; flex: none; object-fit: contain; }"
    " #legenda small { display: block; opacity: .75; }"
    " #legenda .nota { margin: .4em 0 0; max-width: 16em; opacity: .75; }"
)
_PAGE_SCRIPT: Final = """\
(function () {
  var pintura = JSON.parse(document.getElementById("pintura").textContent);
  var municipios = JSON.parse(document.getElementById("municipios").textContent);
  var ufs = JSON.parse(document.getElementById("ufs").textContent);
  var paises = JSON.parse(document.getElementById("paises").textContent);
  var CRUZAMENTO = pintura.cargo === "cruzamento";
  var ORDEM_DAS_CLASSES = ["consolidacao", "terreno_de_virada", "em_aberto", "sem_governador"];
  var CLASSES = {
    consolidacao: {
      rotulo: "Consolidação",
      cor: "#1b9e77",
      definicao: "O governador é do mesmo partido que lidera a presidência aqui."
    },
    terreno_de_virada: {
      rotulo: "Terreno de virada",
      cor: "#d95f02",
      definicao: "O governador é do partido que ficou em segundo na presidência aqui."
    },
    em_aberto: {
      rotulo: "Em aberto",
      cor: "#7570b3",
      definicao: "O governador é de um partido fora dos dois primeiros da presidência aqui."
    },
    sem_governador: {
      rotulo: "Sem governador",
      cor: "#8c8c8c",
      definicao: "Há votação para presidente e não há para governador."
    }
  };

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
      if (item.nome) {
        properties.nome = item.nome;
      }
      properties.logo = pintura.logos[item.numero];
      properties.codigo = String(item.codigo);
      properties.segundo = item.segundo;
      properties.votosSegundo = item.votosSegundo;
      properties.branco = item.branco;
      properties.nulo = item.nulo;
      properties.classe = item.classe;
      properties.governador = item.governador;
      properties.pesoGovernador = item.pesoGovernador;
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

  var ZOOM_MUNICIPIOS = 6;
  var ZOOM_TODOS = 11;
  var PISO_INICIAL = 800000;
  var FAIXAS_DE_ROTULO = [[6.5, 400000], [7, 150000], [7.5, 60000], [8, 25000], [8.5, 10000]];
  var LARGURA_DO_CARACTERE = 6.6;
  var ALTURA_DA_LINHA = 14;
  var ZOOM_ROTULO_COMPLETO = 9;
  var Z_DESTAQUE = Number.MAX_SAFE_INTEGER;
  var destacado = null;

  function estilo(feature, resolution) {
    var cor = feature.get("cor");
    if (!cor) {
      return estiloMundo();
    }
    var emDestaque = feature === destacado;
    var tinta = misturar(corDoLugar(feature), emDestaque ? "1/1" : feature.get("peso"));
    var estilos = [new ol.style.Style({
      zIndex: emDestaque ? Z_DESTAQUE : 0,
      fill: new ol.style.Fill({color: tinta.fill}),
      stroke: new ol.style.Stroke({
        color: emDestaque ? "#000000" : "#222222",
        width: emDestaque ? 3 : 1
      })
    })];
    var geometria = maiorParte(feature);
    var texto = textoDoRotulo(feature, resolution, emDestaque);
    if (emDestaque || rotuloVisivel(feature, resolution, geometria, texto)) {
      estilos.push(new ol.style.Style({
        geometry: geometria,
        zIndex: emDestaque ? Z_DESTAQUE : votosValidos(feature.get("peso")),
        text: new ol.style.Text({
          text: texto,
          font: emDestaque ? "bold 14px sans-serif" : "12px sans-serif",
          overflow: true,
          fill: new ol.style.Fill({color: tinta.ink}),
          stroke: emDestaque ? new ol.style.Stroke({color: tinta.fill, width: 3}) : undefined
        })
      }));
    }
    return estilos;
  }

  function corDoLugar(feature) {
    var classe = CLASSES[feature.get("classe")];
    return CRUZAMENTO && classe ? classe.cor : feature.get("cor");
  }

  function rotuloCruzado(feature) {
    var linhas = [];
    if (feature.get("nome")) {
      linhas.push(String(feature.get("nome")));
    }
    var classe = CLASSES[feature.get("classe")];
    linhas.push(classe ? classe.rotulo : "—");
    var governador = feature.get("governador");
    linhas.push("Pres. " + feature.get("numero") + (governador ? " · Gov. " + governador : ""));
    return linhas.join("\\n");
  }

  function textoDoRotulo(feature, resolution, completo) {
    var texto = CRUZAMENTO ? rotuloCruzado(feature) :
      rotulo(feature.get("nome"), feature.get("numero"), feature.get("peso"));
    var nome = feature.get("nome");
    if (completo || !ehMunicipio(feature) || nome == null || String(nome) === "") {
      return texto;
    }
    if (typeof resolution !== "number" || !isFinite(resolution) || resolution <= 0) {
      return texto;
    }
    return vista.getZoomForResolution(resolution) >= ZOOM_ROTULO_COMPLETO ? texto : String(nome);
  }

  function rotuloVisivel(feature, resolution, geometria, texto) {
    if (!ehMunicipio(feature)) {
      return true;
    }
    if (typeof resolution !== "number" || !isFinite(resolution) || resolution <= 0) {
      return true;
    }
    var zoom = vista.getZoomForResolution(resolution);
    if (!(zoom >= ZOOM_MUNICIPIOS) || zoom >= ZOOM_TODOS) {
      return true;
    }
    return votosValidos(feature.get("peso")) >= minimoDeVotos(zoom) ||
      cabeNaTela(geometria, texto, resolution);
  }

  function cabeNaTela(geometria, texto, resolution) {
    if (!geometria) {
      return false;
    }
    var linhas = String(texto).split("\\n");
    var maisLonga = 0;
    for (var i = 0; i < linhas.length; i++) {
      maisLonga = Math.max(maisLonga, linhas[i].length);
    }
    var extensao = geometria.getExtent();
    var largura = (extensao[2] - extensao[0]) / resolution;
    var altura = (extensao[3] - extensao[1]) / resolution;
    return largura >= maisLonga * LARGURA_DO_CARACTERE && altura >= linhas.length * ALTURA_DA_LINHA;
  }

  function ehMunicipio(feature) {
    var codigo = String(feature.get("codigo") == null ? "" : feature.get("codigo"));
    return codigo.length >= 6;
  }

  function minimoDeVotos(zoom) {
    var piso = PISO_INICIAL;
    for (var i = 0; i < FAIXAS_DE_ROTULO.length; i++) {
      if (zoom >= FAIXAS_DE_ROTULO[i][0]) {
        piso = FAIXAS_DE_ROTULO[i][1];
      }
    }
    return piso;
  }

  function votosValidos(peso) {
    var partes = String(peso == null ? "" : peso).split("/");
    if (partes.length !== 2) {
      return 0;
    }
    var denominador = Number(partes[1]);
    if (!eInteiro(denominador) || denominador <= 0) {
      return 0;
    }
    return denominador;
  }

  var RAIO_MINIMO = 4;
  var RAIO_MAXIMO = 16;
  var VOTOS_DO_RAIO_MAXIMO = 30000;
  var ZOOM_NOMES_DO_EXTERIOR = 4;

  function estiloPonto(feature, resolution) {
    var emDestaque = feature === destacado;
    var tinta = misturar(corDoLugar(feature), emDestaque ? "1/1" : feature.get("peso"));
    var votos = votosValidos(feature.get("peso"));
    var raio = raioDoPonto(votos) + (emDestaque ? 2 : 0);
    var estilos = [new ol.style.Style({
      zIndex: emDestaque ? Z_DESTAQUE : votos,
      image: new ol.style.Circle({
        radius: raio,
        declutterMode: "obstacle",
        fill: new ol.style.Fill({color: tinta.fill}),
        stroke: new ol.style.Stroke({
          color: emDestaque ? "#000000" : "#222222",
          width: emDestaque ? 3 : 1
        })
      })
    })];
    if (emDestaque || nomesDoExteriorVisiveis(resolution)) {
      estilos.push(new ol.style.Style({
        zIndex: emDestaque ? Z_DESTAQUE : votos,
        text: new ol.style.Text({
          text: String(feature.get("nome") || "").replace(/ \\(ZZ\\)$/, ""),
          font: emDestaque ? "bold 13px sans-serif" : "11px sans-serif",
          offsetY: raio + 9,
          fill: new ol.style.Fill({color: "#111111"}),
          stroke: new ol.style.Stroke({color: "#ffffff", width: 3})
        })
      }));
    }
    return estilos;
  }

  function raioDoPonto(votos) {
    var parte = Math.sqrt(Math.min(votos, VOTOS_DO_RAIO_MAXIMO) / VOTOS_DO_RAIO_MAXIMO);
    return RAIO_MINIMO + (RAIO_MAXIMO - RAIO_MINIMO) * parte;
  }

  function nomesDoExteriorVisiveis(resolution) {
    if (typeof resolution !== "number" || !isFinite(resolution) || resolution <= 0) {
      return true;
    }
    return vista.getZoomForResolution(resolution) >= ZOOM_NOMES_DO_EXTERIOR;
  }

  function colecaoDePontos(itens) {
    return {
      type: "FeatureCollection",
      features: itens.map(function (item) {
        return {
          type: "Feature",
          geometry: {type: "Point", coordinates: [item.lon, item.lat]},
          properties: {
            codigo: String(item.codigo),
            cor: item.cor,
            peso: item.peso,
            numero: item.numero,
            nome: item.nome,
            logo: pintura.logos[item.numero],
            segundo: item.segundo,
            votosSegundo: item.votosSegundo,
            branco: item.branco,
            nulo: item.nulo,
            classe: item.classe,
            governador: item.governador,
            pesoGovernador: item.pesoGovernador
          }
        };
      })
    };
  }

  function maiorParte(feature) {
    var geometria = feature.getGeometry();
    if (!geometria || geometria.getType() !== "MultiPolygon") {
      return geometria;
    }
    var partes = geometria.getPolygons();
    var escolhida = geometria;
    var maior = -1;
    for (var i = 0; i < partes.length; i++) {
      var area = partes[i].getArea();
      if (area > maior) {
        maior = area;
        escolhida = partes[i];
      }
    }
    return escolhida;
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

  function rotulo(nome, numero, peso) {
    var partes = String(peso == null ? "" : peso).split("/");
    if (partes.length !== 2) {
      return "—";
    }
    var numerador = Number(partes[0]);
    var denominador = Number(partes[1]);
    if (!eInteiro(numerador) || !eInteiro(denominador) || denominador <= 0 || numerador < 0) {
      return "—";
    }
    if (numerador === 0) {
      return "0";
    }
    var linhas = [percentual(numerador, denominador), milhar(denominador)];
    if (numero !== undefined && numero !== null && String(numero) !== "") {
      linhas.unshift(String(numero));
    }
    if (nome !== undefined && nome !== null && String(nome) !== "") {
      linhas.unshift(String(nome));
    }
    return linhas.join("\\n");
  }

  function percentual(numerador, denominador) {
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

  function camada(geojson, style, minZoom, maxZoom, declutter) {
    var opcoes = {
      source: new ol.source.Vector({features: new ol.format.GeoJSON({
        dataProjection: "EPSG:4326",
        featureProjection: "EPSG:4326"
      }).readFeatures(geojson)}),
      declutter: declutter === true,
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

  function mostrarZoom() {
    var zoom = vista.getZoom();
    if (typeof zoom !== "number" || !isFinite(zoom)) {
      return;
    }
    var nivel = zoom.toFixed(1).replace(".", ",");
    var detalhe;
    if (zoom <= 4) {
      detalhe = "país";
    } else if (zoom <= 6) {
      detalhe = "UFs";
    } else if (zoom >= ZOOM_TODOS) {
      detalhe = "municípios, todos os rótulos";
    } else {
      detalhe = "municípios, rótulos ≥ " + milhar(minimoDeVotos(zoom)) +
        " votos válidos ou que cabem na tela";
    }
    if (zoom > 6 && zoom < ZOOM_ROTULO_COMPLETO) {
      detalhe += " · só nomes";
    }
    painelZoom.textContent = "Zoom " + nivel + " · " + detalhe;
  }

  function destacar(feature, pixel, coordenada) {
    if (feature !== destacado) {
      var anterior = destacado;
      destacado = feature;
      if (anterior) {
        anterior.changed();
      }
      if (feature) {
        feature.changed();
      }
    }
    mapa.getTargetElement().style.cursor = feature ? "pointer" : "";
    if (!feature) {
      painelDetalhe.hidden = true;
      cartao.setPosition(undefined);
      return;
    }
    preencherDetalhe(feature);
    painelDetalhe.hidden = false;
    var tamanho = mapa.getSize();
    var direita = pixel[0] > tamanho[0] / 2;
    var baixo = pixel[1] > tamanho[1] / 2;
    cartao.setPositioning((baixo ? "bottom-" : "top-") + (direita ? "right" : "left"));
    cartao.setOffset([direita ? -16 : 16, baixo ? -16 : 16]);
    cartao.setPosition(coordenada);
  }

  function pintadoNoPixel(pixel) {
    var achado = mapa.forEachFeatureAtPixel(pixel, function (feature) {
      return feature.get("cor") ? feature : undefined;
    }, {hitTolerance: 4});
    return achado || null;
  }

  function preencherDetalhe(feature) {
    painelDetalhe.textContent = "";
    var nome = feature.get("nome");
    painelDetalhe.appendChild(elemento("strong", nome ? String(nome) : "—"));
    var partes = String(feature.get("peso") == null ? "" : feature.get("peso")).split("/");
    var lider = Number(partes[0]);
    var validos = partes.length === 2 ? Number(partes[1]) : NaN;
    if (CRUZAMENTO) {
      detalharClasse(feature);
    }
    if (!eInteiro(lider) || !eInteiro(validos) || validos <= 0) {
      return;
    }
    if (CRUZAMENTO) {
      painelDetalhe.appendChild(elemento("div", "Presidente")).className = "secao";
    }
    painelDetalhe.appendChild(linhaDePartido("1º", feature.get("numero"), lider, validos));
    var segundo = feature.get("segundo");
    var votosSegundo = Number(feature.get("votosSegundo"));
    if (segundo && eInteiro(votosSegundo)) {
      painelDetalhe.appendChild(linhaDePartido("2º", segundo, votosSegundo, validos));
      var margem = percentual(lider - votosSegundo, validos).replace("%", " p.p.");
      painelDetalhe.appendChild(elemento("div", "Margem: " + margem));
    }
    painelDetalhe.appendChild(elemento("div", "Votos válidos: " + milhar(validos)));
    var branco = Number(feature.get("branco"));
    var nulo = Number(feature.get("nulo"));
    if (eInteiro(branco) && eInteiro(nulo) && branco + nulo > 0) {
      painelDetalhe.appendChild(
        elemento("div", "Brancos: " + milhar(branco) + " · Nulos: " + milhar(nulo))
      );
    }
    if (CRUZAMENTO) {
      detalharGovernador(feature);
    }
  }

  function detalharClasse(feature) {
    var classe = CLASSES[feature.get("classe")];
    if (!classe) {
      return;
    }
    var linha = elemento("div", "");
    linha.className = "classe";
    var amostra = elemento("span", "");
    amostra.className = "amostra";
    amostra.style.background = classe.cor;
    linha.appendChild(amostra);
    linha.appendChild(document.createTextNode(classe.rotulo));
    painelDetalhe.appendChild(linha);
    painelDetalhe.appendChild(elemento("small", classe.definicao));
  }

  function detalharGovernador(feature) {
    painelDetalhe.appendChild(elemento("div", "Governador")).className = "secao";
    var governador = feature.get("governador");
    var partes = String(feature.get("pesoGovernador") || "").split("/");
    var votos = Number(partes[0]);
    var validos = partes.length === 2 ? Number(partes[1]) : NaN;
    if (!governador || !eInteiro(votos) || !eInteiro(validos) || validos <= 0) {
      painelDetalhe.appendChild(elemento("div", "Sem votação para governador"));
      return;
    }
    painelDetalhe.appendChild(linhaDePartido("1º", governador, votos, validos));
  }

  function linhaDePartido(posicao, numero, votos, validos) {
    var linha = elemento("div", "");
    linha.className = "partido";
    var logo = pintura.logos[numero];
    if (logo) {
      var imagem = document.createElement("img");
      imagem.src = logo;
      imagem.alt = "";
      linha.appendChild(imagem);
    }
    linha.appendChild(document.createTextNode(
      posicao + " · " + nomeDoPartido(numero) + " · " + percentual(votos, validos) +
        " (" + milhar(votos) + ")"
    ));
    return linha;
  }

  function nomeDoPartido(numero) {
    var sigla = (pintura.siglas || {})[numero];
    return sigla ? sigla + " " + numero : String(numero);
  }

  function montarLegendaCruzada() {
    var contagem = {};
    var total = 0;
    function somar(itens, campo) {
      for (var i = 0; i < itens.length; i++) {
        var votos = votosValidos(itens[i].peso);
        var linha = contagem[itens[i].classe] || {municipios: 0, exterior: 0, votos: 0};
        linha[campo] += 1;
        linha.votos += votos;
        contagem[itens[i].classe] = linha;
        total += votos;
      }
    }
    somar(pintura.municipios, "municipios");
    somar(pintura.exterior || [], "exterior");
    var lista = painelLegenda.querySelector("ul");
    ORDEM_DAS_CLASSES.forEach(function (chave) {
      var classe = CLASSES[chave];
      var linha = contagem[chave] || {municipios: 0, exterior: 0, votos: 0};
      var item = document.createElement("li");
      var amostra = elemento("span", "");
      amostra.className = "amostra";
      amostra.style.background = classe.cor;
      item.appendChild(amostra);
      var texto = elemento("span", classe.rotulo);
      var partes = [];
      if (linha.municipios || !linha.exterior) {
        partes.push(milhar(linha.municipios) +
          (linha.municipios === 1 ? " município" : " municípios"));
      }
      if (linha.exterior) {
        partes.push(milhar(linha.exterior) +
          (linha.exterior === 1 ? " cidade no exterior" : " cidades no exterior"));
      }
      var resumo = partes.join(" · ");
      if (total > 0) {
        resumo += " · " + percentual(linha.votos, total) + " dos votos";
      }
      texto.appendChild(elemento("small", resumo));
      texto.appendChild(elemento("small", classe.definicao));
      item.appendChild(texto);
      lista.appendChild(item);
    });
    painelLegenda.querySelector(".nota").textContent =
      "Tom mais forte: fatia maior do líder de presidente. Os votos são os válidos de presidente.";
    botaoLegenda.textContent = "Classes";
  }

  function montarLegenda() {
    if (CRUZAMENTO) {
      montarLegendaCruzada();
      return;
    }
    var contagem = {};
    function contar(itens, campo) {
      for (var i = 0; i < itens.length; i++) {
        var numero = String(itens[i].numero);
        var linha = contagem[numero] || {numero: numero, cor: itens[i].cor,
          pais: 0, ufs: 0, municipios: 0, exterior: 0};
        linha[campo] += 1;
        contagem[numero] = linha;
      }
    }
    contar(pintura.pais ? [pintura.pais] : [], "pais");
    contar(pintura.ufs, "ufs");
    contar(pintura.municipios, "municipios");
    contar(pintura.exterior || [], "exterior");
    var linhas = Object.keys(contagem).map(function (numero) {
      return contagem[numero];
    });
    linhas.sort(function (a, b) {
      return b.municipios - a.municipios || b.ufs - a.ufs || b.exterior - a.exterior ||
        Number(a.numero) - Number(b.numero);
    });
    var lista = painelLegenda.querySelector("ul");
    for (var i = 0; i < linhas.length; i++) {
      lista.appendChild(itemDaLegenda(linhas[i]));
    }
  }

  function itemDaLegenda(linha) {
    var item = document.createElement("li");
    var amostra = elemento("span", "");
    amostra.className = "amostra";
    amostra.style.background = linha.cor;
    item.appendChild(amostra);
    var logo = pintura.logos[linha.numero];
    var imagem = document.createElement(logo ? "img" : "span");
    imagem.className = "logo";
    if (logo) {
      imagem.src = logo;
      imagem.alt = "";
    }
    item.appendChild(imagem);
    var texto = elemento("span", nomeDoPartido(linha.numero));
    texto.appendChild(elemento("small", resumoDaLideranca(linha)));
    item.appendChild(texto);
    return item;
  }

  function resumoDaLideranca(linha) {
    var partes = [];
    if (linha.pais) {
      partes.push("Brasil");
    }
    if (linha.ufs) {
      partes.push(linha.ufs + (linha.ufs === 1 ? " UF" : " UFs"));
    }
    if (linha.municipios) {
      var rotuloMunicipio = linha.municipios === 1 ? " município" : " municípios";
      partes.push(milhar(linha.municipios) + rotuloMunicipio);
    }
    if (linha.exterior) {
      partes.push(linha.exterior + " no exterior");
    }
    return "lidera: " + partes.join(" · ");
  }

  function alternarLegenda(aberta) {
    botaoLegenda.setAttribute("aria-expanded", aberta ? "true" : "false");
    itensDaLegenda.hidden = !aberta;
  }

  function elemento(tag, texto) {
    var novo = document.createElement(tag);
    novo.textContent = texto;
    return novo;
  }

  var vista = new ol.View({projection: "EPSG:4326", center: [-54, -14], zoom: 3});
  var painelZoom = document.getElementById("zoom");
  var painelDetalhe = document.getElementById("detalhe");
  var cartao = new ol.Overlay({element: painelDetalhe, stopEvent: false});
  var painelLegenda = document.getElementById("legenda");
  var botaoLegenda = painelLegenda.querySelector("button");
  var itensDaLegenda = document.getElementById("legenda-itens");
  montarLegenda();
  alternarLegenda(painelLegenda.parentElement.clientWidth >= 640);
  botaoLegenda.addEventListener("click", function () {
    alternarLegenda(botaoLegenda.getAttribute("aria-expanded") !== "true");
  });

  var mapa = new ol.Map({
    target: "mapa",
    layers: [
      camada(mundo, estiloMundo, null, null),
      camada(brasil, estilo, null, 4),
      camada(colecao(ufs, pintura.ufsObjeto), estilo, 4, 6),
      camada(colecao(municipios, pintura.municipiosObjeto), estilo, 6, 28, true),
      camada(colecaoDePontos(pintura.exterior || []), estiloPonto, null, null, true)
    ],
    controls: ol.control.defaults.defaults().extend([
      new ol.control.Control({element: painelZoom}),
      new ol.control.Control({element: painelLegenda})
    ]),
    overlays: [cartao],
    view: vista
  });
  vista.on("change:resolution", mostrarZoom);
  mostrarZoom();
  mapa.on("pointermove", function (evento) {
    if (evento.dragging) {
      return;
    }
    destacar(pintadoNoPixel(evento.pixel), evento.pixel, evento.coordinate);
  });
  mapa.on("singleclick", function (evento) {
    destacar(pintadoNoPixel(evento.pixel), evento.pixel, evento.coordinate);
  });
  mapa.getViewport().addEventListener("pointerleave", function () {
    destacar(null, null, null);
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
        '<div id="mapa"><div id="zoom" aria-live="polite"></div>'
        '<div id="detalhe" role="tooltip" hidden></div>'
        '<div id="legenda" class="ol-unselectable"><button type="button" aria-expanded="true"'
        ' aria-controls="legenda-itens">Partidos</button><div id="legenda-itens">'
        '<ul></ul><p class="nota">Tom mais forte: fatia maior dos votos válidos do líder.</p>'
        "</div></div></div>\n"
        f"{_footer(pagina)}\n"
        f"{_scripts(pagina)}\n"
        "</body>\n"
        "</html>\n"
    )


def _title(pagina: PaginaDoMapa) -> str:
    cargo = _CARGO_NO_TITULO.get(pagina.cargo, pagina.cargo)
    return f"Mapa de {cargo} — {pagina.ano}, turno {pagina.turno}"


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
        "siglas": _siglas(recorte),
        "cargo": pagina.cargo,
        "pais": country,
        "ufs": [_item(item) for item in recorte.ufs],
        "municipios": [_item(item) for item in recorte.municipios],
        "exterior": [_ponto(ponto) for ponto in recorte.exterior],
        "brasilId": pagina.brasil_id,
        "ufsObjeto": pagina.ufs_objeto,
        "municipiosObjeto": pagina.municipios_objeto,
        "paisesObjeto": pagina.paises_objeto,
    }


def _logos(recorte: RecortePintado) -> dict[str, str]:
    logos: dict[str, str] = {}
    for painting in _paintings(recorte):
        logos.setdefault(painting.numero, painting.logo)
    for numero, marca in recorte.marcas.items():
        logos.setdefault(numero, marca.logo)
    return logos


def _siglas(recorte: RecortePintado) -> dict[str, str]:
    return {numero: marca.sigla for numero, marca in recorte.marcas.items() if marca.sigla}


def _paintings(recorte: RecortePintado) -> tuple[Pintura, ...]:
    country = () if recorte.pais is None else (recorte.pais,)
    abroad = tuple(ponto.pintura for ponto in recorte.exterior)
    return country + recorte.ufs + recorte.municipios + abroad


def _item(pintura: Pintura) -> dict[str, str | int]:
    return {
        "codigo": pintura.codigo,
        "cor": pintura.cor,
        "numero": pintura.numero,
        "peso": pintura.peso,
        "nome": pintura.nome,
        "segundo": pintura.segundo,
        "votosSegundo": pintura.votos_segundo,
        "branco": pintura.branco,
        "nulo": pintura.nulo,
        "classe": pintura.classe,
        "governador": pintura.governador,
        "pesoGovernador": pintura.peso_governador,
    }


def _ponto(ponto: PontoPintado) -> dict[str, str | int | float]:
    return {**_item(ponto.pintura), "lon": ponto.lon, "lat": ponto.lat}
