import assert from "node:assert/strict";
import {
  gruposEsfera,
  layoutGrupos,
  LIMITE_GRUPOS,
  MEDIDAS_ESTREITO,
  MEDIDAS_PADRAO,
  OPACIDADES,
  resumoGrupos,
  type Grupo,
} from "./grafico-forca.ts";
import { CHAVES_COLUNA, colunasPlacar, type ChaveColuna, type LinhaPlacar, type Valor } from "./placar-forca.ts";

const NULO: Valor = { ordem: null, fracao: null, texto: "—", detalhe: "Sem dados" };

function valor(fracao: number | null, texto = "x"): Valor {
  return fracao === null ? NULO : { ordem: fracao, fracao, texto, detalhe: `d ${texto}` };
}

function linha(chave: string, fracoes: Partial<Record<ChaveColuna, number | null>>): LinhaPlacar {
  const valores = {} as Record<ChaveColuna, Valor>;
  for (const c of CHAVES_COLUNA) {
    valores[c] = valor(fracoes[c] ?? null, `${Math.round((fracoes[c] ?? 0) * 100)}%`);
  }
  return { chave, rotulo: `P ${chave}`, partidos: [Number(chave)], valores };
}

const colunas = colunasPlacar(5, "pais");
const UTIL = MEDIDAS_PADRAO.largura - MEDIDAS_PADRAO.esquerda - MEDIDAS_PADRAO.direita;
assert.equal(UTIL, 396);

// grupos: ordem das linhas, colunas da esfera em ordem, métrica nula sai, linha toda nula sai
const linhas = [
  linha("22", { presidente: 1, deputado_federal: 0 }),
  linha("13", { presidente: null, deputado_federal: 1.2 }),
  linha("65", { deputado_estadual: 0.5 }),
];
const nacional = gruposEsfera(linhas, colunas, "nacional");
assert.deepEqual(nacional.map((g) => g.chave), ["22", "13"]);
assert.deepEqual(nacional[0].metricas.map((m) => m.chave), ["presidente", "deputado_federal"]);
assert.deepEqual(nacional[1].metricas.map((m) => m.chave), ["deputado_federal"]);
assert.equal(nacional[0].metricas[0].curto, "Presidente");
assert.equal(nacional[0].metricas[0].detalhe, "d 100%");
assert.deepEqual(gruposEsfera(linhas, colunas, "estados").map((g) => g.chave), ["65"]);
assert.deepEqual(gruposEsfera(linhas, colunas, "municipios"), []);

// limite padrão de 8 e limite explícito
const dez = Array.from({ length: 10 }, (_, i) => linha(String(10 + i), { presidente: 0.1 }));
assert.equal(LIMITE_GRUPOS, 8);
assert.deepEqual(gruposEsfera(dez, colunas, "nacional").map((g) => g.chave), ["10", "11", "12", "13", "14", "15", "16", "17"]);
assert.deepEqual(gruposEsfera(dez, colunas, "nacional", 3).map((g) => g.chave), ["10", "11", "12"]);
// filtra antes de cortar: linhas nulas na frente não ocupam lugar
const comNulas = [linha("1", {}), linha("2", {}), ...dez];
assert.deepEqual(gruposEsfera(comNulas, colunas, "nacional").map((g) => g.chave), ["10", "11", "12", "13", "14", "15", "16", "17"]);

// escala fixa: 1 ocupa a largura útil, 0 dá 0, 1,2 é cortada
const layout = layoutGrupos(nacional);
assert.ok(layout);
assert.equal(layout.grupos[0].barras[0].largura, 396);
assert.equal(layout.grupos[0].barras[1].largura, 0);
assert.equal(layout.grupos[1].barras[0].largura, 396);
// fração negativa é cortada em 0
const negativa = layoutGrupos([{ chave: "n", rotulo: "N", metricas: [
  { chave: "presidente", curto: "Presidente", fracao: -0.1, texto: "x", detalhe: "" },
] }]);
assert.equal(negativa?.grupos[0].barras[0].largura, 0);

// posições e altura: 2 grupos × 2 barras = 4 + 2·(22 + 2·18 + 10) + 4 = 144
const dois: Grupo[] = [
  { chave: "a", rotulo: "A", metricas: [
    { chave: "presidente", curto: "Presidente", fracao: 0.5, texto: "50,00%", detalhe: "" },
    { chave: "deputado_federal", curto: "Dep. federal", fracao: 0.25, texto: "25,00%", detalhe: "" },
  ] },
  { chave: "b", rotulo: "B", metricas: [
    { chave: "presidente", curto: "Presidente", fracao: 0.1, texto: "10,00%", detalhe: "" },
    { chave: "deputado_federal", curto: "Dep. federal", fracao: 0.2, texto: "20,00%", detalhe: "" },
  ] },
];
const doisLayout = layoutGrupos(dois);
assert.ok(doisLayout);
assert.equal(doisLayout.altura, 144);
assert.equal(doisLayout.largura, 640);
assert.deepEqual(doisLayout.grupos.map((g) => g.yCabeca), [4, 72]);
assert.deepEqual(doisLayout.grupos[1].barras.map((b) => b.y), [94, 112]);
assert.deepEqual(doisLayout.grupos[0].barras.map((b) => b.opacidade), [1, 0.7]);
assert.equal(doisLayout.grupos[0].barras[0].largura, 198);

// opacidade: a última se o índice passar do fim
const cinco: Grupo = { chave: "c", rotulo: "C", metricas: Array.from({ length: 5 }, (_, i) => (
  { chave: `m${i}`, curto: `M${i}`, fracao: 0.1, texto: "10,00%", detalhe: "" }
)) };
assert.deepEqual(layoutGrupos([cinco])?.grupos[0].barras.map((b) => b.opacidade), [...OPACIDADES, 0.3]);

// variante estreita: 340 px, rótulo acima, barra desce 14 px dentro do passo
const estreito = layoutGrupos(dois, MEDIDAS_ESTREITO);
assert.ok(estreito);
assert.equal(estreito.largura, 340);
assert.equal(estreito.medidas.rotuloAcima, true);
assert.deepEqual(estreito.grupos[0].barras.map((b) => b.y), [4 + 22 + 14, 4 + 22 + 30 + 14]);
assert.equal(estreito.grupos[0].barras[0].largura, 0.5 * (340 - 2 - 96));
assert.equal(estreito.altura, 4 + 2 * (22 + 2 * 30 + 10) + 4);

// sem grupos
assert.equal(layoutGrupos([]), null);

// resumo
assert.equal(
  resumoGrupos("Nacional", dois),
  "Nacional. A: Presidente 50,00%, Dep. federal 25,00%; B: Presidente 10,00%, Dep. federal 20,00%.",
);
assert.equal(resumoGrupos("Municípios", []), "Municípios.");
console.log("ok");
