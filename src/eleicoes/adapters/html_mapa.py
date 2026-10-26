"""HTML do mapa coroplético. O JavaScript é colado; as chaves não passam por format."""

import json
from collections.abc import Callable
from html import escape
from typing import Final

from eleicoes.domain.mapa import PaginaDoMapa, Pintura, PontoPintado, RecortePintado
from eleicoes.domain.mapa_turnos import (
    LIMIAR_FORA,
    LIMIAR_MODERADO,
    MINIMO_NO_GRUPO,
    PISO_DE_VOTOS,
    Apuracao,
    ComparativoTurnos,
    GrupoEliminado,
    LugarTurnos,
)

_IBGE: Final = "Malha municipal e de estados: IBGE. Licença compatível com CC BY 4.0."
_CARGO_NO_TITULO: Final = {"cruzamento": "presidente × governador"}
_VIEWS: Final = ("presidente", "governador", "cruzamento")
_TURNOS: Final = "turnos"
_BASE_VIEW: Final = {"cruzamento": "presidente"}
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
    " #visoes { position: absolute; top: .5em; left: 50%; transform: translateX(-50%);"
    " display: flex; background: rgba(255,255,255,.92); border: 1px solid #cccccc;"
    " border-radius: 6px; padding: 2px; gap: 2px; }"
    " #visoes button { font: 12px sans-serif; color: #111111; background: none; border: 0;"
    " border-radius: 4px; padding: .3em .7em; cursor: pointer; white-space: nowrap; }"
    " #visoes button[aria-pressed='true'] { background: #111111; color: #ffffff; }"
    " #legenda { position: absolute; top: 2.8em; right: .5em; max-height: calc(100% - 3.3em);"
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
    " #legenda .escala { height: 10px; border-radius: 2px; margin: .5em 0 .2em;"
    " border: 1px solid rgba(0,0,0,.35); }"
    " #legenda .marcas { display: flex; justify-content: space-between; }"
    " #turnos-controles { position: absolute; left: .5em; bottom: 2.4em; display: flex;"
    " flex-direction: column; gap: .35em; max-width: min(19em, calc(100% - 1em));"
    " box-sizing: border-box; background: rgba(255,255,255,.92); border: 1px solid #cccccc;"
    " border-radius: 6px; padding: .45em .6em; font: 12px/1.4 sans-serif; color: #111111; }"
    " #turnos-controles[hidden] { display: none; }"
    " #turnos-controles label { display: flex; flex-direction: column; gap: .15em;"
    " font-weight: bold; }"
    " #turnos-controles select { font: 12px sans-serif; color: #111111; background: #ffffff;"
    " border: 1px solid #888888; border-radius: 4px; padding: .2em; max-width: 100%; }"
    " #turnos-controles small { opacity: .8; }"
    " #turnos-controles .personalizado { display: flex; flex-direction: column; gap: .3em;"
    " padding-left: .5em; border-left: 2px solid #cccccc; }"
    " #turnos-controles .personalizado[hidden] { display: none; }"
    " #turnos-controles .personalizado label { font-weight: normal; }"
    " #detalhe table { border-collapse: collapse; margin-top: .2em; }"
    " #detalhe th, #detalhe td { padding: 0 .5em 0 0; text-align: right; font-weight: normal; }"
    " #detalhe th:first-child { text-align: left; }"
    " #detalhe thead th { opacity: .7; }"
)
_PAGE_SCRIPT: Final = """\
(function () {
  var base = JSON.parse(document.getElementById("pintura").textContent);
  var municipios = JSON.parse(document.getElementById("municipios").textContent);
  var ufs = JSON.parse(document.getElementById("ufs").textContent);
  var paises = JSON.parse(document.getElementById("paises").textContent);
  var VISOES = ["presidente", "governador", "cruzamento", "turnos"];
  var NOMES_DAS_VISOES = {
    presidente: "Presidente",
    governador: "Governador",
    cruzamento: "Presidente × governador",
    turnos: "1º × 2º turno"
  };
  var CLASSES_DOS_TURNOS = ["fora_a", "moderado_a", "dentro", "moderado_b", "fora_b", "sem_base"];
  var METRICAS = ["desvio", "residuo", "a", "b", "branco", "nulo", "cedulas"];
  var CORES_DAS_CLASSES = {
    fora_a: "#2c5aa0",
    moderado_a: "#9dc0e8",
    dentro: "#efefef",
    moderado_b: "#f2a37f",
    fora_b: "#b2182b",
    sem_base: "#a6a6a6"
  };
  var INDICE_DA_METRICA = {a: 0, b: 1, branco: 3, nulo: 4};
  var LIMITES_DAS_METRICAS = {};
  var COR_NEUTRA = [247, 247, 247];
  var COR_POSITIVA = [27, 120, 55];
  var COR_NEGATIVA = [118, 42, 131];
  var LIMITE_DO_MODELO = "O modelo só move os votos dos eliminados; quem votou em branco ou " +
    "nulo no 1º turno, faltou a um dos turnos ou trocou de finalista fica fora dele. ";
  var PERSONALIZADO = "personalizado";
  var DEMAIS = "0";
  var DESTINOS = [
    {letra: "a", parte: 1},
    {letra: "q", parte: 0.75},
    {letra: "m", parte: 0.5},
    {letra: "u", parte: 0.25},
    {letra: "b", parte: 0},
    {letra: "p", parte: null}
  ];

  // <matematica-dos-turnos>
  // Espelha leituras() de mapa_turnos.py para o cenário personalizado. Não toca no DOM:
  // o teste de paridade recorta este trecho e o roda no node.
  var K_MAD = 0.6745;
  var K_MEDIA = 0.7979;

  function esperadoDoCenario(primeiro, porGrupo, partes) {
    var validos = primeiro[0] + primeiro[1] + primeiro[2];
    if (validos === 0) {
      return 0.5;
    }
    var finalistas = primeiro[0] + primeiro[1];
    var proporcional = finalistas === 0 ? 0.5 : primeiro[0] / finalistas;
    var movidos = 0;
    for (var i = 0; i < partes.length; i++) {
      movidos += (partes[i] === null ? proporcional : partes[i]) * porGrupo[i];
    }
    return (primeiro[0] + movidos) / validos;
  }

  function mediana(valores) {
    var ordem = valores.slice().sort(function (x, y) {
      return x - y;
    });
    var meio = Math.floor(ordem.length / 2);
    return ordem.length % 2 ? ordem[meio] : (ordem[meio - 1] + ordem[meio]) / 2;
  }

  function escalaRobusta(valores) {
    var centro = mediana(valores);
    var desvios = valores.map(function (valor) {
      return Math.abs(valor - centro);
    });
    var mad = mediana(desvios);
    if (mad > 0) {
      return mad / K_MAD;
    }
    var soma = 0;
    for (var i = 0; i < desvios.length; i++) {
      soma += desvios[i];
    }
    var media = soma / desvios.length;
    return media > 0 ? media / K_MEDIA : null;
  }

  function arredondarParaPar(valor) {
    var piso = Math.floor(valor);
    if (Math.abs(valor - piso - 0.5) < 1e-9) {
      return piso % 2 === 0 ? piso : piso + 1;
    }
    return Math.round(valor);
  }

  function classeDoZ(z, limiares) {
    if (z > limiares.fora) {
      return "fora_a";
    }
    if (z < -limiares.fora) {
      return "fora_b";
    }
    return Math.abs(z) > limiares.moderado ? "moderado" : "dentro";
  }

  function lerGrupo(itens, esperados, regras) {
    var reais = [];
    var comparaveis = [];
    var base = [];
    for (var i = 0; i < itens.length; i++) {
      var primeiro = itens[i].primeiro;
      var finalistas = itens[i].segundo[0] + itens[i].segundo[1];
      reais.push(finalistas > 0 ? itens[i].segundo[0] / finalistas : 0.5);
      comparaveis.push(primeiro[0] + primeiro[1] + primeiro[2] >= regras.piso &&
        finalistas >= regras.piso);
      if (comparaveis[i]) {
        base.push(reais[i] - esperados[i]);
      }
    }
    var escala = base.length >= regras.minimo ? escalaRobusta(base) : null;
    var centro = escala !== null ? mediana(base) : 0;
    return itens.map(function (item, indice) {
      var residuo = reais[indice] - esperados[indice];
      var votos = arredondarParaPar(residuo * (item.segundo[0] + item.segundo[1]));
      if (escala === null || !comparaveis[indice]) {
        return [esperados[indice], votos, null, "sem_base"];
      }
      var z = (residuo - centro) / escala;
      return [esperados[indice], votos, z, classeDoZ(z, regras.limiares)];
    });
  }
  // </matematica-dos-turnos>

  var TURNOS = base.turnos || null;
  var estadoTurnos = lerEstadoTurnos();
  var BASES = {};
  BASES[baseDaVisao(base.cargo)] = base;
  Object.keys(base.visoes || {}).forEach(function (nome) {
    BASES[nome] = Object.assign({}, base, base.visoes[nome]);
  });
  if (TURNOS) {
    recalcularPersonalizado();
    BASES.turnos = pinturaDosTurnos();
  }
  var visaoAtual = visaoDoEndereco() || base.cargo;
  var pintura = dadosDaVisao(visaoAtual);
  var CRUZAMENTO = visaoAtual === "cruzamento";
  var COMPARATIVO = visaoAtual === "turnos";
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
      cor: "#3a5fcd",
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
      properties.turnos = item.turnos;
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
      COMPARATIVO ? rotuloDosTurnos(feature) :
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
            pesoGovernador: item.pesoGovernador,
            turnos: item.turnos
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
    if (COMPARATIVO) {
      detalharTurnos(feature.get("turnos"));
      return;
    }
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
    painelLegenda.querySelector("ul").textContent = "";
    painelLegenda.querySelector(".nota").textContent = NOTA_DA_LEGENDA;
    botaoLegenda.textContent = "Partidos";
    if (CRUZAMENTO) {
      montarLegendaCruzada();
      return;
    }
    if (COMPARATIVO) {
      montarLegendaDosTurnos();
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

  function rotuloDaClasse(chave) {
    var a = TURNOS ? TURNOS.a : "A";
    var b = TURNOS ? TURNOS.b : "B";
    return {
      fora_a: "Fora do esperado: " + a + " acima",
      moderado_a: "Desvio moderado: " + a + " acima",
      dentro: "Dentro do esperado",
      moderado_b: "Desvio moderado: " + b + " acima",
      fora_b: "Fora do esperado: " + b + " acima",
      sem_base: "Sem base de comparação"
    }[chave];
  }

  function nomeDaMetrica(chave) {
    var a = TURNOS ? nomeDoPartido(TURNOS.a) : "A";
    var b = TURNOS ? nomeDoPartido(TURNOS.b) : "B";
    return {
      desvio: "Anomalia no cenário",
      residuo: "Diferença do cenário (p.p.)",
      a: "Votos do " + a,
      b: "Votos do " + b,
      branco: "Brancos",
      nulo: "Nulos",
      cedulas: "Total de cédulas"
    }[chave];
  }

  function lerEstadoTurnos() {
    var estado = {cenario: "", metrica: "desvio", destinos: {}};
    if (!TURNOS) {
      return estado;
    }
    estado.cenario = TURNOS.padrao;
    semearDestinos(estado, TURNOS.cenarios[0].parte);
    var hash = window.location.hash;
    var cenario = /(?:^|[#&])cenario=([a-z]+)/.exec(hash);
    if (cenario && (indiceDoCenario(cenario[1]) >= 0 ||
        cenario[1] === PERSONALIZADO && temPersonalizado())) {
      estado.cenario = cenario[1];
    }
    var escolhas = /(?:^|[#&])personalizado=([a-z0-9]+)/.exec(hash);
    if (escolhas) {
      lerDestinos(estado, escolhas[1]);
    }
    var metrica = /(?:^|[#&])pintar=([a-z]+)/.exec(hash);
    if (metrica && METRICAS.indexOf(metrica[1]) >= 0) {
      estado.metrica = metrica[1];
    }
    return estado;
  }

  function temPersonalizado() {
    return Boolean(TURNOS && TURNOS.eliminados && TURNOS.eliminados.length);
  }

  function destinoDaLetra(letra) {
    for (var i = 0; i < DESTINOS.length; i++) {
      if (DESTINOS[i].letra === letra) {
        return DESTINOS[i];
      }
    }
    return null;
  }

  function letraDaParte(parte) {
    for (var i = 0; i < DESTINOS.length; i++) {
      if (DESTINOS[i].parte === parte) {
        return DESTINOS[i].letra;
      }
    }
    return "p";
  }

  function semearDestinos(estado, parte) {
    (TURNOS.eliminados || []).forEach(function (grupo) {
      estado.destinos[grupo.numero] = letraDaParte(parte);
    });
  }

  function lerDestinos(estado, codigo) {
    var par = /([0-9]+)([a-z])/g;
    var achado = par.exec(codigo);
    while (achado) {
      if (estado.destinos.hasOwnProperty(achado[1]) && destinoDaLetra(achado[2])) {
        estado.destinos[achado[1]] = achado[2];
      }
      achado = par.exec(codigo);
    }
  }

  function codigoDosDestinos() {
    return (TURNOS.eliminados || []).map(function (grupo) {
      return grupo.numero + estadoTurnos.destinos[grupo.numero];
    }).join("");
  }

  function partesEscolhidas() {
    return TURNOS.eliminados.map(function (grupo) {
      return destinoDaLetra(estadoTurnos.destinos[grupo.numero]).parte;
    });
  }

  function recalcularPersonalizado() {
    if (estadoTurnos.cenario !== PERSONALIZADO) {
      return;
    }
    var partes = partesEscolhidas();
    var regras = {piso: TURNOS.piso, minimo: TURNOS.minimo, limiares: TURNOS.limiares};
    var porUf = {};
    TURNOS.municipios.forEach(function (item) {
      (porUf[item.uf] = porUf[item.uf] || []).push(item);
    });
    var grupos = Object.keys(porUf).map(function (uf) {
      return porUf[uf];
    });
    grupos.push(TURNOS.exterior, TURNOS.ufs, TURNOS.pais ? [TURNOS.pais] : []);
    grupos.forEach(function (itens) {
      var esperados = itens.map(function (item) {
        return esperadoDoCenario(item.primeiro, item.eliminados, partes);
      });
      var lidas = lerGrupo(itens, esperados, regras);
      itens.forEach(function (item, indice) {
        item.personalizada = lidas[indice];
      });
    });
  }

  function indiceDoCenario(chave) {
    for (var i = 0; i < TURNOS.cenarios.length; i++) {
      if (TURNOS.cenarios[i].chave === chave) {
        return i;
      }
    }
    return -1;
  }

  function cenarioAtual() {
    if (estadoTurnos.cenario === PERSONALIZADO) {
      return {
        chave: PERSONALIZADO,
        rotulo: "Personalizado",
        descricao: "Cada eliminado segue o destino escolhido: " +
          TURNOS.eliminados.map(function (grupo) {
            return nomeDoGrupo(grupo) + ", " +
              nomeDoDestino(estadoTurnos.destinos[grupo.numero]).toLowerCase();
          }).join("; ") + "."
      };
    }
    return TURNOS.cenarios[indiceDoCenario(estadoTurnos.cenario)];
  }

  function nomeDoGrupo(grupo) {
    return grupo.numero === DEMAIS ? "Demais" : nomeDoPartido(grupo.numero);
  }

  function nomeDoDestino(letra) {
    return {
      a: "Todos para o " + TURNOS.a,
      q: "75% para o " + TURNOS.a,
      m: "Metade para cada",
      u: "25% para o " + TURNOS.a,
      b: "Todos para o " + TURNOS.b,
      p: "Como no 1º turno"
    }[letra];
  }

  function cedulas(contas) {
    return contas[0] + contas[1] + contas[2] + contas[3] + contas[4];
  }

  function leituraAtual(item) {
    var lida = estadoTurnos.cenario === PERSONALIZADO ? item.personalizada :
      item.leituras[indiceDoCenario(estadoTurnos.cenario)];
    var finalistas = item.segundo[0] + item.segundo[1];
    return {
      esperado: lida[0],
      real: finalistas > 0 ? item.segundo[0] / finalistas : 0.5,
      votos: lida[1],
      z: lida[2],
      classe: lida[3]
    };
  }

  function classeVisivel(lida) {
    if (lida.classe === "moderado") {
      return lida.z >= 0 ? "moderado_a" : "moderado_b";
    }
    return lida.classe;
  }

  function valorDaMetrica(item, metrica) {
    if (metrica === "residuo") {
      var lida = leituraAtual(item);
      return (lida.real - lida.esperado) * 100;
    }
    if (metrica === "cedulas") {
      var antes = cedulas(item.primeiro);
      return antes > 0 ? (cedulas(item.segundo) - antes) / antes * 100 : 0;
    }
    var indice = INDICE_DA_METRICA[metrica];
    var total1 = cedulas(item.primeiro);
    var total2 = cedulas(item.segundo);
    if (total1 <= 0 || total2 <= 0) {
      return 0;
    }
    return (item.segundo[indice] / total2 - item.primeiro[indice] / total1) * 100;
  }

  function unidadeDaMetrica(metrica) {
    return metrica === "cedulas" ? "%" : " p.p.";
  }

  function limiteDaMetrica(metrica) {
    var chave = metrica + "|" + estadoTurnos.cenario +
      (estadoTurnos.cenario === PERSONALIZADO ? "|" + codigoDosDestinos() : "");
    if (LIMITES_DAS_METRICAS[chave]) {
      return LIMITES_DAS_METRICAS[chave];
    }
    var valores = TURNOS.municipios.map(function (item) {
      return Math.abs(valorDaMetrica(item, metrica));
    }).sort(function (x, y) {
      return x - y;
    });
    var p95 = valores.length ? valores[Math.floor((valores.length - 1) * 0.95)] : 1;
    var limite = Math.max(0.5, Math.ceil(p95 * 2) / 2);
    LIMITES_DAS_METRICAS[chave] = limite;
    return limite;
  }

  function corDivergente(valor, limite) {
    var t = Math.max(-1, Math.min(1, valor / limite));
    var alvo = t >= 0 ? COR_POSITIVA : COR_NEGATIVA;
    var parte = Math.abs(t);
    var rgb = [0, 1, 2].map(function (i) {
      return Math.round(COR_NEUTRA[i] + (alvo[i] - COR_NEUTRA[i]) * parte);
    });
    return "#" + rgb.map(function (canal) {
      var hex = canal.toString(16);
      return hex.length < 2 ? "0" + hex : hex;
    }).join("");
  }

  function agregado(item) {
    return String(item.codigo).length < 6 && item.uf !== "ZZ";
  }

  function semGrupo(item) {
    return estadoTurnos.metrica === "desvio" && agregado(item) && leituraAtual(item).z === null;
  }

  function corDosTurnos(item) {
    var metrica = estadoTurnos.metrica;
    if (semGrupo(item)) {
      return corDivergente(valorDaMetrica(item, "residuo"), limiteDaMetrica("residuo"));
    }
    if (metrica === "desvio") {
      return CORES_DAS_CLASSES[classeVisivel(leituraAtual(item))];
    }
    return corDivergente(valorDaMetrica(item, metrica), limiteDaMetrica(metrica));
  }

  function itemDosTurnos(item) {
    var validos = item.segundo[0] + item.segundo[1];
    var pintado = {
      codigo: item.codigo,
      nome: item.nome,
      cor: corDosTurnos(item),
      peso: validos + "/" + validos,
      numero: "",
      turnos: item
    };
    if (item.lon !== undefined) {
      pintado.lon = item.lon;
      pintado.lat = item.lat;
    }
    return pintado;
  }

  function pinturaDosTurnos() {
    return Object.assign({}, base, {
      cargo: "turnos",
      pais: TURNOS.pais ? itemDosTurnos(TURNOS.pais) : null,
      ufs: TURNOS.ufs.map(itemDosTurnos),
      municipios: TURNOS.municipios.map(itemDosTurnos),
      exterior: TURNOS.exterior.map(itemDosTurnos)
    });
  }

  function decimal(valor, casas) {
    var sinal = valor > 0 ? "+" : valor < 0 ? "−" : "";
    var partes = Math.abs(valor).toFixed(casas).split(".");
    return sinal + milhar(Number(partes[0])) + (partes.length > 1 ? "," + partes[1] : "");
  }

  function comSinal(valor) {
    return (valor > 0 ? "+" : valor < 0 ? "−" : "") + milhar(Math.abs(valor));
  }

  function fatia(valor) {
    return decimal(valor * 100, 2).replace("+", "") + "%";
  }

  function textoDaMetrica(item) {
    var metrica = estadoTurnos.metrica;
    if (semGrupo(item)) {
      return decimal(valorDaMetrica(item, "residuo"), 1) + " p.p. do cenário";
    }
    if (metrica === "desvio") {
      var lida = leituraAtual(item);
      return lida.z === null ? "sem base" : "z " + decimal(lida.z, 1);
    }
    return decimal(valorDaMetrica(item, metrica), 1) + unidadeDaMetrica(metrica);
  }

  function rotuloDosTurnos(feature) {
    var item = feature.get("turnos");
    if (!item) {
      return String(feature.get("nome") || "—");
    }
    return String(item.nome) + "\\n" + textoDaMetrica(item);
  }

  function detalharTurnos(item) {
    if (!item) {
      return;
    }
    var tabela = document.createElement("table");
    var cabeca = tabela.createTHead().insertRow();
    ["", "1º turno", "2º turno", "Variação"].forEach(function (texto) {
      var celula = document.createElement("th");
      celula.textContent = texto;
      cabeca.appendChild(celula);
    });
    var corpo = tabela.createTBody();
    var linhas = [
      [nomeDoPartido(TURNOS.a), 0],
      [nomeDoPartido(TURNOS.b), 1],
      ["Eliminados", 2],
      ["Brancos", 3],
      ["Nulos", 4]
    ];
    linhas.forEach(function (linha) {
      linhaDaTabela(corpo, linha[0], item.primeiro[linha[1]], item.segundo[linha[1]]);
    });
    linhaDaTabela(corpo, "Cédulas", cedulas(item.primeiro), cedulas(item.segundo));
    painelDetalhe.appendChild(tabela);
    var cenario = cenarioAtual();
    var lida = leituraAtual(item);
    painelDetalhe.appendChild(elemento("div", "Cenário: " + cenario.rotulo)).className = "secao";
    painelDetalhe.appendChild(elemento("div",
      "Esperado para o " + TURNOS.a + ": " + fatia(lida.esperado) +
        " dos votos dos finalistas · real: " + fatia(lida.real)));
    painelDetalhe.appendChild(elemento("div",
      "Diferença: " + decimal((lida.real - lida.esperado) * 100, 2) + " p.p. (≈ " +
        comSinal(lida.votos) + " votos para o " + TURNOS.a + ")"));
    var classe = classeVisivel(lida);
    var linha = elemento("div", "");
    linha.className = "classe";
    var amostra = elemento("span", "");
    amostra.className = "amostra";
    amostra.style.background = CORES_DAS_CLASSES[classe];
    linha.appendChild(amostra);
    linha.appendChild(document.createTextNode(
      rotuloDaClasse(classe) + (lida.z === null ? "" : " · z " + decimal(lida.z, 2))));
    painelDetalhe.appendChild(linha);
    painelDetalhe.appendChild(elemento("small", explicacaoDoDesvio(item, lida)));
  }

  function linhaDaTabela(corpo, rotulo, antes, depois) {
    var linha = corpo.insertRow();
    var nome = document.createElement("th");
    nome.textContent = rotulo;
    linha.appendChild(nome);
    [milhar(antes), milhar(depois), comSinal(depois - antes)].forEach(function (texto) {
      linha.insertCell().textContent = texto;
    });
  }

  function explicacaoDoDesvio(item, lida) {
    var grupo = String(item.codigo).length >= 6 ? "dos municípios da mesma UF" :
      item.uf === "ZZ" ? "das cidades do exterior" : "das UFs";
    if (lida.z !== null) {
      return "z robusto: a diferença deste lugar comparada com a mediana " + grupo +
        ". Acima de " + decimal(TURNOS.limiares.fora, 1).replace("+", "") +
        " em módulo, o cenário explica mal o voto aqui. Não é prova de irregularidade.";
    }
    if (agregado(item)) {
      return "País e UFs sem grupo de comparação (menos de " + TURNOS.minimo +
        " UFs importadas) são pintados pela diferença do cenário: verde, o " + TURNOS.a +
        " acima do esperado; roxo, abaixo.";
    }
    return "Fica sem z quando o lugar tem menos de " + milhar(TURNOS.piso) +
      " votos dos finalistas ou quando o grupo tem menos de " + TURNOS.minimo + " lugares.";
  }

  function montarLegendaDosTurnos() {
    botaoLegenda.textContent = "1º × 2º turno";
    var lista = painelLegenda.querySelector("ul");
    var metrica = estadoTurnos.metrica;
    if (metrica === "desvio") {
      var contagem = {};
      TURNOS.municipios.forEach(function (item) {
        var classe = classeVisivel(leituraAtual(item));
        contagem[classe] = (contagem[classe] || 0) + 1;
      });
      CLASSES_DOS_TURNOS.forEach(function (chave) {
        var item = document.createElement("li");
        var amostra = elemento("span", "");
        amostra.className = "amostra";
        amostra.style.background = CORES_DAS_CLASSES[chave];
        item.appendChild(amostra);
        var texto = elemento("span", rotuloDaClasse(chave));
        var total = contagem[chave] || 0;
        texto.appendChild(elemento("small", milhar(total) +
          (total === 1 ? " município" : " municípios")));
        item.appendChild(texto);
        lista.appendChild(item);
      });
    } else {
      var limite = limiteDaMetrica(metrica);
      var faixa = elemento("li", "");
      faixa.style.display = "block";
      var escala = elemento("div", "");
      escala.className = "escala";
      escala.style.background = "linear-gradient(to right, " + corDivergente(-limite, limite) +
        ", " + corDivergente(0, limite) + ", " + corDivergente(limite, limite) + ")";
      faixa.appendChild(escala);
      var marcas = elemento("div", "");
      marcas.className = "marcas";
      [-limite, 0, limite].forEach(function (valor) {
        marcas.appendChild(elemento("span", decimal(valor, 1) + unidadeDaMetrica(metrica)));
      });
      faixa.appendChild(marcas);
      lista.appendChild(faixa);
    }
    painelLegenda.querySelector(".nota").textContent = notaDosTurnos(metrica);
  }

  function notaDosTurnos(metrica) {
    var cobertura = "2º turno importado em " + TURNOS.cobertura.length + " de 28 recortes (" +
      TURNOS.cobertura.join(", ") + "). ";
    var pais = TURNOS.pais ? resumoDoPais() : "";
    if (metrica === "desvio") {
      return nomeDaMetrica(metrica) + ". Cenário: " + cenarioAtual().descricao + " " + pais +
        "Cada município é comparado com a mediana da sua UF (z robusto; |z| > " +
        decimal(TURNOS.limiares.moderado, 1).replace("+", "") + " moderado, > " +
        decimal(TURNOS.limiares.fora, 1).replace("+", "") + " fora do esperado). " +
        "Desvio aponta onde o cenário explica mal o voto; não prova irregularidade. " +
        "País e UFs sem grupo usam a diferença do cenário (verde: " + TURNOS.a +
        " acima; roxo: abaixo). " + LIMITE_DO_MODELO + cobertura;
    }
    if (metrica === "residuo") {
      return "Fatia real do " + TURNOS.a + " entre os finalistas menos a esperada no cenário. " +
        cenarioAtual().descricao + " " + pais + LIMITE_DO_MODELO + cobertura;
    }
    if (metrica === "cedulas") {
      return "Variação do total de cédulas de presidente (válidos, brancos e nulos) do 1º " +
        "para o 2º turno. " + cobertura;
    }
    return nomeDaMetrica(metrica) + ": variação da fatia nas cédulas de presidente do 1º para " +
      "o 2º turno, em pontos percentuais. A tabela do lugar mostra os votos. " + cobertura;
  }

  function resumoDoPais() {
    var lida = leituraAtual(TURNOS.pais);
    return "No total importado, o " + TURNOS.a + " teve " + fatia(lida.real) +
      " dos votos dos finalistas contra " + fatia(lida.esperado) + " esperados (" +
      comSinal(lida.votos) + " votos). ";
  }

  function montarControlesDosTurnos() {
    if (!TURNOS) {
      painelTurnos.hidden = true;
      return;
    }
    var opcoes = TURNOS.cenarios.map(function (item) {
      return [item.chave, item.rotulo];
    });
    if (temPersonalizado()) {
      opcoes.push([PERSONALIZADO, "Personalizado"]);
    }
    var cenario = seletor("Cenário de apoio no 2º turno", opcoes, estadoTurnos.cenario,
      function (valor) {
        var anterior = TURNOS.cenarios[indiceDoCenario(estadoTurnos.cenario)];
        if (valor === PERSONALIZADO && anterior) {
          semearDestinos(estadoTurnos, anterior.parte);
          marcarDestinos(personalizado);
        }
        estadoTurnos.cenario = valor;
        personalizado.hidden = valor !== PERSONALIZADO;
        atualizarTurnos();
        descricao.textContent = cenarioAtual().descricao;
      });
    var metrica = seletor("Pintar por", METRICAS.map(function (chave) {
      return [chave, nomeDaMetrica(chave)];
    }), estadoTurnos.metrica, function (valor) {
      estadoTurnos.metrica = valor;
      atualizarTurnos();
    });
    var descricao = elemento("small", cenarioAtual().descricao);
    var personalizado = seletoresDosDestinos(function () {
      atualizarTurnos();
      descricao.textContent = cenarioAtual().descricao;
    });
    personalizado.hidden = estadoTurnos.cenario !== PERSONALIZADO;
    painelTurnos.appendChild(cenario);
    painelTurnos.appendChild(personalizado);
    painelTurnos.appendChild(descricao);
    painelTurnos.appendChild(metrica);
    painelTurnos.hidden = !COMPARATIVO;
  }

  function seletoresDosDestinos(aoMudar) {
    var caixa = elemento("div", "");
    caixa.className = "personalizado";
    (TURNOS.eliminados || []).forEach(function (grupo) {
      var rotulo = nomeDoGrupo(grupo) + " · " + fatia(grupo.fatia) + " no país";
      var campo = seletor(rotulo, DESTINOS.map(function (destino) {
        return [destino.letra, nomeDoDestino(destino.letra)];
      }), estadoTurnos.destinos[grupo.numero], function (valor) {
        estadoTurnos.destinos[grupo.numero] = valor;
        aoMudar();
      });
      campo.querySelector("select").setAttribute("data-grupo", grupo.numero);
      caixa.appendChild(campo);
    });
    return caixa;
  }

  function marcarDestinos(caixa) {
    var listas = caixa.querySelectorAll("select");
    for (var i = 0; i < listas.length; i++) {
      listas[i].value = estadoTurnos.destinos[listas[i].getAttribute("data-grupo")];
    }
  }

  function seletor(rotulo, opcoes, atual, aoMudar) {
    var campo = elemento("label", rotulo);
    var lista = document.createElement("select");
    opcoes.forEach(function (opcao) {
      var item = elemento("option", opcao[1]);
      item.value = opcao[0];
      item.selected = opcao[0] === atual;
      lista.appendChild(item);
    });
    lista.addEventListener("change", function () {
      aoMudar(lista.value);
    });
    campo.appendChild(lista);
    return campo;
  }

  function atualizarTurnos() {
    destacar(null, null, null);
    recalcularPersonalizado();
    BASES.turnos = pinturaDosTurnos();
    pintura = dadosDaVisao("turnos");
    repintarTudo();
    window.location.replace(enderecoDaVisao("turnos"));
  }

  function baseDaVisao(nome) {
    if (nome === "governador" || nome === "turnos") {
      return nome;
    }
    return "presidente";
  }

  function dadosDaVisao(nome) {
    var dados = BASES[baseDaVisao(nome)];
    return dados ? Object.assign({}, dados, {cargo: nome}) : null;
  }

  function visaoDoEndereco() {
    var achado = /(?:^|[#&])visao=([a-z]+)/.exec(window.location.hash);
    if (!achado || VISOES.indexOf(achado[1]) < 0 || !BASES[baseDaVisao(achado[1])]) {
      return null;
    }
    return achado[1];
  }

  var CAMPOS_DA_PINTURA = [
    "cor", "peso", "numero", "logo", "codigo", "segundo", "votosSegundo", "branco", "nulo",
    "classe", "governador", "pesoGovernador", "turnos"
  ];

  function codigoDaFeicao(feature) {
    var codigo = feature.get("codarea");
    return String(codigo === undefined || codigo === null ? feature.getId() : codigo);
  }

  function repintar(camadaAlvo, itens) {
    var porCodigo = {};
    for (var i = 0; i < itens.length; i++) {
      porCodigo[String(itens[i].codigo)] = itens[i];
    }
    camadaAlvo.getSource().getFeatures().forEach(function (feature) {
      var item = porCodigo[codigoDaFeicao(feature)];
      var valores = {};
      CAMPOS_DA_PINTURA.forEach(function (campo) {
        valores[campo] = item ? item[campo] : undefined;
      });
      if (item) {
        valores.codigo = String(item.codigo);
        valores.logo = pintura.logos[item.numero];
        if (item.nome) {
          valores.nome = item.nome;
        }
      }
      feature.setProperties(valores, true);
      feature.changed();
    });
  }

  function lerPontos() {
    return new ol.format.GeoJSON({
      dataProjection: "EPSG:4326",
      featureProjection: "EPSG:4326"
    }).readFeatures(colecaoDePontos(pintura.exterior || []));
  }

  function trocarVisao(nome) {
    if (nome === visaoAtual || !dadosDaVisao(nome)) {
      return;
    }
    destacar(null, null, null);
    visaoAtual = nome;
    pintura = dadosDaVisao(nome);
    CRUZAMENTO = nome === "cruzamento";
    COMPARATIVO = nome === "turnos";
    repintarTudo();
    marcarVisao();
    if (visaoDoEndereco() !== nome) {
      window.location.replace(enderecoDaVisao(nome));
    }
  }

  function repintarTudo() {
    repintar(camadaBrasil, pintura.pais ? [pintura.pais] : []);
    repintar(camadaUfs, pintura.ufs);
    repintar(camadaMunicipios, pintura.municipios);
    camadaPontos.getSource().clear();
    camadaPontos.getSource().addFeatures(lerPontos());
    montarLegenda();
    painelTurnos.hidden = !COMPARATIVO;
  }

  function enderecoDaVisao(nome) {
    if (nome !== "turnos") {
      return "#visao=" + nome;
    }
    var escolhas = estadoTurnos.cenario === PERSONALIZADO ?
      "&personalizado=" + codigoDosDestinos() : "";
    return "#visao=turnos&cenario=" + estadoTurnos.cenario + escolhas +
      "&pintar=" + estadoTurnos.metrica;
  }

  function montarSeletor() {
    VISOES.forEach(function (nome) {
      if (!dadosDaVisao(nome)) {
        return;
      }
      var botao = elemento("button", NOMES_DAS_VISOES[nome]);
      botao.type = "button";
      botao.setAttribute("data-visao", nome);
      botao.addEventListener("click", function () {
        trocarVisao(nome);
      });
      painelVisoes.appendChild(botao);
    });
  }

  function marcarVisao() {
    var botoes = painelVisoes.querySelectorAll("button");
    for (var i = 0; i < botoes.length; i++) {
      var ativo = botoes[i].getAttribute("data-visao") === visaoAtual;
      botoes[i].setAttribute("aria-pressed", ativo ? "true" : "false");
    }
    var titulo = (base.titulos || {})[visaoAtual];
    if (titulo) {
      document.title = titulo;
      var cabecalho = document.querySelector("h1");
      if (cabecalho) {
        cabecalho.textContent = titulo;
      }
    }
  }

  var vista = new ol.View({projection: "EPSG:4326", center: [-54, -14], zoom: 3});
  var painelZoom = document.getElementById("zoom");
  var painelDetalhe = document.getElementById("detalhe");
  var cartao = new ol.Overlay({element: painelDetalhe, stopEvent: false});
  var painelLegenda = document.getElementById("legenda");
  var botaoLegenda = painelLegenda.querySelector("button");
  var itensDaLegenda = document.getElementById("legenda-itens");
  var NOTA_DA_LEGENDA = painelLegenda.querySelector(".nota").textContent;
  var painelVisoes = document.getElementById("visoes");
  var painelTurnos = document.getElementById("turnos-controles");
  montarLegenda();
  montarSeletor();
  montarControlesDosTurnos();
  alternarLegenda(painelLegenda.parentElement.clientWidth >= 640);
  botaoLegenda.addEventListener("click", function () {
    alternarLegenda(botaoLegenda.getAttribute("aria-expanded") !== "true");
  });

  var camadaBrasil = camada(brasil, estilo, null, 4);
  var camadaUfs = camada(colecao(ufs, pintura.ufsObjeto), estilo, 4, 6);
  var camadaMunicipios = camada(colecao(municipios, pintura.municipiosObjeto), estilo, 6, 28, true);
  var camadaPontos = camada(colecaoDePontos(pintura.exterior || []), estiloPonto, null, null, true);

  var mapa = new ol.Map({
    target: "mapa",
    layers: [
      camada(mundo, estiloMundo, null, null),
      camadaBrasil,
      camadaUfs,
      camadaMunicipios,
      camadaPontos
    ],
    controls: ol.control.defaults.defaults().extend([
      new ol.control.Control({element: painelZoom}),
      new ol.control.Control({element: painelLegenda}),
      new ol.control.Control({element: painelVisoes}),
      new ol.control.Control({element: painelTurnos})
    ]),
    overlays: [cartao],
    view: vista
  });
  vista.on("change:resolution", mostrarZoom);
  mostrarZoom();
  marcarVisao();
  window.addEventListener("hashchange", function () {
    var nome = visaoDoEndereco();
    if (nome) {
      trocarVisao(nome);
    }
  });
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
        '<div id="visoes" class="ol-unselectable" role="group" aria-label="Visão do mapa"></div>'
        '<div id="turnos-controles" class="ol-unselectable" hidden></div>'
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
    return _title_for(pagina, pagina.cargo)


def _title_for(pagina: PaginaDoMapa, cargo: str) -> str:
    name = _CARGO_NO_TITULO.get(cargo, cargo)
    return f"Mapa de {name} — {pagina.ano}, turno {pagina.turno}"


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
    recortes = (pagina.recorte, *pagina.recortes.values())
    return {
        "logos": _merged(_logos, recortes),
        "siglas": _merged(_siglas, recortes),
        "cargo": pagina.cargo,
        **_view(pagina.recorte),
        "visoes": _other_views(pagina),
        "titulos": _titles(pagina),
        "turnos": None if pagina.turnos is None else _turnos(pagina.turnos),
        "brasilId": pagina.brasil_id,
        "ufsObjeto": pagina.ufs_objeto,
        "municipiosObjeto": pagina.municipios_objeto,
        "paisesObjeto": pagina.paises_objeto,
    }


def _titles(pagina: PaginaDoMapa) -> dict[str, str]:
    titles = {cargo: _title_for(pagina, cargo) for cargo in _VIEWS}
    if pagina.turnos is not None:
        titles[_TURNOS] = f"Mapa de presidente — {pagina.ano}, 1º × 2º turno"
    return titles


def _turnos(comparativo: ComparativoTurnos) -> dict[str, object]:
    grupos = comparativo.eliminados
    return {
        "a": str(comparativo.a),
        "b": str(comparativo.b),
        "padrao": comparativo.cenarios[0].chave,
        "cenarios": [
            {
                "chave": item.chave,
                "rotulo": item.rotulo,
                "descricao": item.descricao,
                "parte": None if item.parte_de_a is None else float(item.parte_de_a),
            }
            for item in comparativo.cenarios
        ],
        "eliminados": [
            {"numero": str(grupo.numero), "fatia": round(float(grupo.fatia), 4)} for grupo in grupos
        ],
        "cobertura": list(comparativo.ufs_com_segundo),
        "semComparacao": comparativo.sem_comparacao,
        "piso": PISO_DE_VOTOS,
        "minimo": MINIMO_NO_GRUPO,
        "limiares": {"moderado": LIMIAR_MODERADO, "fora": LIMIAR_FORA},
        "pais": None if comparativo.pais is None else _lugar(comparativo.pais, grupos),
        "ufs": [_lugar(item, grupos) for item in comparativo.ufs],
        "municipios": [_lugar(item, grupos) for item in comparativo.municipios],
        "exterior": [
            {**_lugar(ponto.lugar, grupos), "lon": ponto.lon, "lat": ponto.lat}
            for ponto in comparativo.exterior
        ],
    }


def _lugar(lugar: LugarTurnos, grupos: tuple[GrupoEliminado, ...]) -> dict[str, object]:
    found: dict[str, object] = {
        "codigo": lugar.codigo,
        "nome": lugar.nome,
        "uf": lugar.uf,
        "primeiro": _contas(lugar.primeiro),
        "segundo": _contas(lugar.segundo),
        "leituras": [
            [
                round(float(leitura.esperado), 6),
                leitura.votos_de_diferenca,
                None if leitura.z is None else round(leitura.z, 3),
                leitura.classe,
            ]
            for leitura in lugar.leituras
        ],
    }
    if grupos:
        # Votos de cada grupo de eliminados no 1º turno, na ordem de "eliminados" do comparativo.
        found["eliminados"] = [lugar.primeiro.votos_do_grupo(grupo.numeros) for grupo in grupos]
    return found


def _contas(apuracao: Apuracao) -> list[int]:
    return [apuracao.a, apuracao.b, apuracao.outros, apuracao.branco, apuracao.nulo]


def _view(recorte: RecortePintado) -> dict[str, object]:
    country = None if recorte.pais is None else _item(recorte.pais)
    return {
        "pais": country,
        "ufs": [_item(item) for item in recorte.ufs],
        "municipios": [_item(item) for item in recorte.municipios],
        "exterior": [_ponto(ponto) for ponto in recorte.exterior],
    }


def _other_views(pagina: PaginaDoMapa) -> dict[str, dict[str, object]]:
    base = _BASE_VIEW.get(pagina.cargo, pagina.cargo)
    return {cargo: _view(cut) for cargo, cut in pagina.recortes.items() if cargo != base}


def _merged(
    read: Callable[[RecortePintado], dict[str, str]],
    recortes: tuple[RecortePintado, ...],
) -> dict[str, str]:
    found: dict[str, str] = {}
    for recorte in recortes:
        for numero, valor in read(recorte).items():
            found.setdefault(numero, valor)
    return found


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
