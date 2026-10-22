import assert from "node:assert/strict";
import {
  ALTURA_LINHA,
  BASE,
  DIREITA,
  ESQUERDA,
  LARGURA,
  TOPO,
  fatiasPoder,
  layoutBarras,
  leituraPoder,
  liderancasPoder,
  resumoBarras,
  MEDIDAS_ESTREITO,
  MEDIDAS_PADRAO,
} from "./grafico-poder.ts";
import { larguraTexto } from "./largura-texto.ts";
import { SIGLAS_PARTIDOS } from "./partidos.ts";
import type { LinhaGrade } from "./relatorios.ts";

function linha(nome: string, votos: Record<number, number>): LinhaGrade {
  return {
    codigo: nome,
    nome,
    comparecimento: 0,
    celulas: Object.entries(votos).map(([partido, valor]) => ({
      partido: Number(partido),
      votos_nominais: valor,
      votos_legenda: 0,
      comparecimento: 0,
      votos: valor,
      fatia: "0",
    })),
  };
}

const alfa = linha("Alfa", { 22: 600, 13: 300, 55: 100 });
const beta = linha("Beta", { 22: 400, 13: 390, 55: 210 });
const gama = linha("Gama", { 13: 500, 22: 250, 55: 250 });
const delta = linha("Delta", { 22: 100, 13: 100 });
const vazio = linha("Épsilon", { 22: 0, 13: 0 });
const recorte = [alfa, beta, gama, delta, vazio];

// fatias: soma das linhas, ordem decrescente, sem Outros com poucos partidos
const fatias = fatiasPoder(recorte);
assert.deepEqual(fatias.map((item) => [item.rotulo, item.texto]), [
  ["PL 22", "42,19%"],
  ["PT 13", "40,31%"],
  ["PSD 55", "17,50%"],
]);
assert.equal(fatias[0].valor, 1350);
assert.equal(fatias[0].detalhe, "1.350 votos");

// Outros: 10 partidos com votos e 1 zerado
const muitos: Record<number, number> = { 99: 0 };
for (let indice = 0; indice < 10; indice += 1) {
  muitos[10 + indice] = 100 - indice * 10;
}
const comOutros = fatiasPoder([linha("Muitos", muitos)]);
assert.equal(comOutros.length, 9);
assert.deepEqual(comOutros.slice(0, 2).map((item) => item.rotulo), ["REPUBLICANOS 10", "PP 11"]);
assert.deepEqual(comOutros[8], {
  chave: "outros",
  rotulo: "Outros",
  valor: 30,
  texto: "5,45%",
  detalhe: "2 partidos, 30 votos",
});
delete muitos[19];
const nove = fatiasPoder([linha("Nove", muitos)]);
assert.equal(nove.length, 9);
assert.ok(nove.every((item) => item.chave !== "outros"));

// Outros fica por último mesmo maior que uma barra; empate de votos pelo menor número
const outrosGrande = fatiasPoder([
  linha("X", { 1: 50, 2: 50, 3: 50, 4: 50, 5: 50, 6: 50, 7: 50, 8: 50, 9: 40, 11: 40 }),
]);
assert.equal(outrosGrande[8].rotulo, "Outros");
assert.equal(outrosGrande[8].valor, 80);
assert.equal(outrosGrande[0].rotulo, "Partido 1");

// layout
const layout = layoutBarras(fatias)!;
assert.equal(layout.largura, LARGURA);
assert.equal(layout.altura, TOPO + 3 * ALTURA_LINHA + BASE);
assert.equal(layout.barras[0].y, TOPO + ALTURA_LINHA / 2);
assert.equal(ESQUERDA + layout.barras[0].largura, LARGURA - DIREITA);
assert.ok(Math.abs(layout.barras[2].largura - (560 / 1350) * (LARGURA - ESQUERDA - DIREITA)) < 1e-9);
const cheio = layoutBarras(fatiasPoder([linha("Só", { 22: 500 })]))!;
assert.equal(cheio.barras[0].texto, "100,00%");
assert.ok(ESQUERDA + cheio.barras[0].largura + 6 + 7 * 7 <= LARGURA);
assert.equal(layoutBarras([]), null);
assert.equal(layoutBarras(fatiasPoder([vazio])), null);

// lideranças: peso pelos votos válidos dos lugares liderados; empate não conta, linha sem votos não conta
const liderancas = liderancasPoder(recorte);
assert.equal(liderancas.lugares, 4);
assert.equal(liderancas.empates, 1);
assert.deepEqual(liderancas.itens.map((item) => [item.rotulo, item.texto, item.detalhe]), [
  ["PL 22", "62,50%", "2.000 votos válidos\n2 de 4 lugares"],
  ["PT 13", "31,25%", "1.000 votos válidos\n1 de 4 lugares"],
]);
assert.deepEqual(liderancas.itens.map((item) => item.lugares), [2, 1]);
const pequenos = liderancasPoder([linha("Grande", { 13: 900, 22: 100 }), linha("P1", { 22: 10 }), linha("P2", { 22: 10 })]);
assert.deepEqual(pequenos.itens.map((item) => [item.rotulo, item.texto]), [["PT 13", "98,04%"], ["PL 22", "1,96%"]]);

// resumo
assert.equal(
  resumoBarras("Fatia de cada partido.", fatias),
  "Fatia de cada partido. PL 22: 42,19%; PT 13: 40,31%; PSD 55: 17,50%.",
);

// leitura: líder, empates e disputa mais apertada
assert.deepEqual(leituraPoder(recorte), [
  "PL 22 lidera em lugares que somam 62,50% dos votos válidos do recorte (2 de 4 lugares).",
  "Em 1 lugar, os dois primeiros empatam.",
  "A disputa mais apertada é em Delta, com empate entre PT 13 e PL 22.",
]);
assert.deepEqual(leituraPoder([alfa, beta, gama]), [
  "PL 22 lidera em lugares que somam 66,67% dos votos válidos do recorte (2 de 3 lugares).",
  "A disputa mais apertada é em Beta: PL 22 tem 40,00% e PT 13 tem 39,00%, uma diferença de 1,00% dos votos válidos.",
]);
assert.deepEqual(leituraPoder([alfa, gama]), [
  "PT 13 e PL 22 lideram em lugares que somam 50,00% dos votos válidos do recorte cada.",
  "A disputa mais apertada é em Gama: PT 13 tem 50,00% e PL 22 tem 25,00%, uma diferença de 25,00% dos votos válidos.",
]);

// um lugar só
assert.deepEqual(leituraPoder([linha("Acre", { 10: 300, 13: 200, 22: 0 })]), [
  "Em Acre, REPUBLICANOS 10 lidera com 60,00% dos votos válidos.",
  "O segundo é PT 13, com 40,00%, uma diferença de 20,00% dos votos válidos.",
]);
assert.deepEqual(leituraPoder([linha("Acre", { 10: 300 })]), [
  "Em Acre, REPUBLICANOS 10 lidera com 100,00% dos votos válidos.",
]);
assert.deepEqual(leituraPoder([linha("Acre", { 10: 300, 13: 300 })]), [
  "Em Acre, REPUBLICANOS 10 e PT 13 empatam no primeiro lugar.",
]);

// recorte vazio
assert.deepEqual(fatiasPoder([]), []);
assert.deepEqual(leituraPoder([]), []);
assert.deepEqual(leituraPoder([vazio]), []);
assert.equal(liderancasPoder([]).lugares, 0);
// variante estreita: rótulo acima da barra, valor no fim sem passar da borda
const CONTENTOR = 300;
const estreito = layoutBarras(comOutros, MEDIDAS_ESTREITO)!;
const me = estreito.medidas;
assert.equal(estreito.largura, 340);
assert.equal(layout.medidas, MEDIDAS_PADRAO);
assert.ok((me.fonte * CONTENTOR) / estreito.largura >= 11);
assert.equal(estreito.altura, me.topo + 9 * me.alturaLinha + me.base);
const rotulosPartidos = [
  ...Object.entries(SIGLAS_PARTIDOS).map(([numero, sigla]) => `${sigla} ${numero}`),
  "Partido 999",
  "Outros",
];
const maiorPartido = Math.max(...rotulosPartidos.map((r) => larguraTexto(r, me.fonte)));
assert.ok(me.rotuloAcima);
assert.ok(me.esquerda + 4 + maiorPartido <= estreito.largura);
const cheioEstreito = layoutBarras(fatiasPoder([linha("Só", { 22: 500 })]), MEDIDAS_ESTREITO)!;
assert.ok(me.esquerda + cheioEstreito.barras[0].largura + 6 + larguraTexto("100,00%", me.fonte) <= estreito.largura);
const primeira = estreito.barras[0];
assert.ok(primeira.y - me.alturaBarra / 2 - 5 - me.fonte >= 0);
for (const [indice, barra] of estreito.barras.entries()) {
  const topoLinha = me.topo + indice * me.alturaLinha;
  assert.ok(barra.y - me.alturaBarra / 2 - 5 - me.fonte >= topoLinha);
  assert.ok(barra.y + me.alturaBarra / 2 <= topoLinha + me.alturaLinha);
}
assert.equal(layout.barras[0].y, TOPO + ALTURA_LINHA / 2);
console.log("ok");
