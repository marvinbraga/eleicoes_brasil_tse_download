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
} from "./grafico-poder.ts";
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
  ["Partido 22", "42,19%"],
  ["Partido 13", "40,31%"],
  ["Partido 55", "17,50%"],
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
assert.deepEqual(comOutros.slice(0, 2).map((item) => item.rotulo), ["Partido 10", "Partido 11"]);
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

// lideranças: empate não conta, linha sem votos não conta
const liderancas = liderancasPoder(recorte);
assert.equal(liderancas.lugares, 4);
assert.equal(liderancas.empates, 1);
assert.deepEqual(liderancas.itens.map((item) => [item.rotulo, item.texto, item.detalhe]), [
  ["Partido 22", "2", "2 de 4 lugares"],
  ["Partido 13", "1", "1 de 4 lugares"],
]);

// resumo
assert.equal(
  resumoBarras("Fatia de cada partido.", fatias),
  "Fatia de cada partido. Partido 22: 42,19%; Partido 13: 40,31%; Partido 55: 17,50%.",
);

// leitura: líder, empates e disputa mais apertada
assert.deepEqual(leituraPoder(recorte), [
  "Partido 22 lidera em 2 dos 4 lugares do recorte.",
  "Em 1 lugar, os dois primeiros empatam.",
  "A disputa mais apertada é em Delta, com empate entre Partido 13 e Partido 22.",
]);
assert.deepEqual(leituraPoder([alfa, beta, gama]), [
  "Partido 22 lidera em 2 dos 3 lugares do recorte.",
  "A disputa mais apertada é em Beta: Partido 22 tem 40,00% e Partido 13 tem 39,00%, uma diferença de 1,00% dos votos válidos.",
]);
assert.deepEqual(leituraPoder([alfa, gama]), [
  "Partido 13 e Partido 22 lideram em 1 dos 2 lugares do recorte cada.",
  "A disputa mais apertada é em Gama: Partido 13 tem 50,00% e Partido 22 tem 25,00%, uma diferença de 25,00% dos votos válidos.",
]);

// um lugar só
assert.deepEqual(leituraPoder([linha("Acre", { 10: 300, 13: 200, 22: 0 })]), [
  "Em Acre, Partido 10 lidera com 60,00% dos votos válidos.",
  "O segundo é Partido 13, com 40,00%, uma diferença de 20,00% dos votos válidos.",
]);
assert.deepEqual(leituraPoder([linha("Acre", { 10: 300 })]), [
  "Em Acre, Partido 10 lidera com 100,00% dos votos válidos.",
]);
assert.deepEqual(leituraPoder([linha("Acre", { 10: 300, 13: 300 })]), [
  "Em Acre, Partido 10 e Partido 13 empatam no primeiro lugar.",
]);

// recorte vazio
assert.deepEqual(fatiasPoder([]), []);
assert.deepEqual(leituraPoder([]), []);
assert.deepEqual(leituraPoder([vazio]), []);
assert.equal(liderancasPoder([]).lugares, 0);
console.log("ok");
