import assert from "node:assert/strict";
import {
  ALTURA_BLOCO_BASE,
  BASE,
  CABECA,
  ESPACO,
  LARGURA_MISTURA,
  LARGURA_PESO,
  PASSO,
  TOPO,
  layoutPerfis,
  leituraSeparacao,
  principaisPerfis,
  resumoPerfis,
} from "./grafico-perfis.ts";

const partidos = [10, 13, 22, 30, 40, 50, 70];
const grupos = [
  { numero: 1, municipios: 300, comparecimento: 9000, centro: ["5,00%", "60,00%", "20,00%", "4,00%", "3,00%", "2,00%", "6,00%", "3,00%", "5,00%"] },
  { numero: 2, municipios: 100, comparecimento: 1000, centro: ["70,00%", "1,00%", "10,00%", "4,00%", "5,00%", "8,00%", "2,00%", "2,00%", "4,00%"] },
];
const entrada = { partidos, grupos };

// peso total: 10 → 0,05·9000+0,70·1000 = 1150; 13 → 5410; 22 → 1900; 30 → 400; 40 → 320; 50 → 260; 70 → 560
assert.deepEqual(principaisPerfis(entrada), [13, 22, 10, 70, 30]);
assert.deepEqual(principaisPerfis({ partidos: [5, 3], grupos: [{ numero: 1, municipios: 1, comparecimento: 10, centro: ["50,00%", "50,00%"] }] }), [3, 5]);

// o líder de cada grupo sempre entra, mesmo fora dos 5 de maior peso
const comLider = { partidos: [1, 2, 3, 4, 5, 6, 7], grupos: [
  { numero: 1, municipios: 10, comparecimento: 1000, centro: ["40,00%", "20,00%", "15,00%", "10,00%", "8,00%", "7,00%", "0,00%"] },
  { numero: 2, municipios: 1, comparecimento: 10, centro: ["0,00%", "0,00%", "0,00%", "0,00%", "0,00%", "10,00%", "90,00%"] },
] };
assert.deepEqual(principaisPerfis(comLider), [1, 2, 3, 4, 7]);
const seisLideres = { partidos: [1, 2, 3, 4, 5, 6, 7], grupos: [1, 2, 3, 4, 5, 6].map((n) => ({
  numero: n, municipios: 1, comparecimento: 100 * n, centro: [1, 2, 3, 4, 5, 6, 7].map((p) => (p === n ? "90,00%" : p === 7 ? "9,00%" : "0,00%")) })) };
assert.deepEqual(principaisPerfis(seisLideres), [6, 5, 4, 3, 2, 1]);
assert.deepEqual(layoutPerfis(seisLideres)!.blocos[0].barras.map((b) => b.tom), [0, 1, 2, 3, 4, 5, null]);

const l = layoutPerfis(entrada)!;
assert.equal(l.blocos.length, 2);
assert.equal(l.restantes, 2);
const [b1, b2] = l.blocos;
assert.deepEqual(b1.barras.map((b) => b.rotulo), ["13", "22", "10", "70", "30", "Outros"]);
assert.deepEqual(b1.barras.map((b) => b.tom), [0, 1, 2, 3, 4, null]);
assert.deepEqual(b1.barras.map((b) => b.texto), ["60,00%", "20,00%", "5,00%", "6,00%", "4,00%", "5,00%"]);
assert.equal(b2.barras[5].texto, "13,00%");
assert.equal(b1.barras[5].titulo, "Outros 2 partidos");
assert.equal(l.teto, 0.7);
assert.equal(l.tetoTexto, "70%");
assert.ok(Math.abs(b2.barras[2].largura - LARGURA_MISTURA) < 1e-9);
assert.ok(Math.abs(b1.barras[0].largura - (0.6 / 0.7) * LARGURA_MISTURA) < 1e-9);
assert.equal(b1.y, TOPO);
assert.equal(b1.barras[1].y, TOPO + CABECA + PASSO);
assert.equal(b2.y, TOPO + CABECA + 6 * PASSO + ESPACO);
assert.equal(l.altura, TOPO + 2 * (CABECA + 6 * PASSO) + ESPACO + BASE);

// peso: parte do total num eixo 0–100%
assert.deepEqual(b1.peso.map((p) => [p.rotulo, p.texto]), [["Municípios", "75,00%"], ["Votantes", "90,00%"]]);
assert.ok(Math.abs(b2.peso[1].largura - 0.1 * LARGURA_PESO) < 1e-9);
assert.equal(b1.peso[1].y, b1.barras[1].y);

// branco e nulo fora; sem resto, sem "Outros"; uma barra só ainda cabe o peso
const dois = layoutPerfis({ partidos: [13, 22], grupos: [{ numero: 1, municipios: 5, comparecimento: 50, centro: ["40,00%", "60,00%", "3,00%", "4,00%"] }] })!;
assert.deepEqual(dois.blocos[0].barras.map((b) => b.rotulo), ["22", "13"]);
assert.equal(dois.restantes, 0);
assert.equal(dois.teto, 0.6);
const um = layoutPerfis({ partidos: [13], grupos: [{ numero: 1, municipios: 5, comparecimento: 50, centro: ["100,00%"] }] })!;
assert.equal(um.teto, 1);
assert.equal(um.altura, TOPO + CABECA + ALTURA_BLOCO_BASE * PASSO + BASE);
const restoZero = layoutPerfis({ partidos: [1, 2, 3, 4, 5, 6], grupos: [{ numero: 1, municipios: 1, comparecimento: 1, centro: ["50,00%", "20,00%", "10,00%", "10,00%", "10,00%", "0,00%"] }] })!;
assert.equal(restoZero.blocos[0].barras.length, 5);
const ruim = layoutPerfis({ partidos: [1, 2], grupos: [{ numero: 1, municipios: 1, comparecimento: 1, centro: ["—", "10,00%"] }] })!;
assert.deepEqual(ruim.blocos[0].barras.map((b) => [b.rotulo, b.texto, b.fracao]), [["2", "10,00%", 0.1], ["1", "—", 0]]);

// entradas vazias
assert.equal(layoutPerfis({ partidos, grupos: [] }), null);
assert.equal(layoutPerfis({ partidos: [], grupos }), null);
assert.equal(layoutPerfis({ partidos: [1], grupos: [{ numero: 1, municipios: 0, comparecimento: 0, centro: ["0,00%"] }] })!.blocos[0].peso[0].texto, "—");

// resumo
assert.equal(
  resumoPerfis(entrada),
  "2 grupos. Partidos no gráfico: 13, 22, 10, 70 e 30. Grupo 1: 300 municípios, lidera o 13 com 60,00%. Grupo 2: 100 municípios, lidera o 10 com 70,00%.",
);
assert.equal(resumoPerfis({ partidos, grupos: [] }), "Nenhum grupo.");

// separação
assert.equal(leituraSeparacao("0,6410"), "A separação entre os grupos é 0,64, numa escala de 0 a 1: os grupos são bem diferentes entre si.");
assert.equal(leituraSeparacao("0,5330"), "A separação entre os grupos é 0,53, numa escala de 0 a 1: os grupos são bem diferentes entre si.");
assert.equal(leituraSeparacao("0,4999"), "A separação entre os grupos é 0,50, numa escala de 0 a 1: os grupos são bem diferentes entre si.");
assert.equal(leituraSeparacao("0,31"), "A separação entre os grupos é 0,31, numa escala de 0 a 1: os grupos se parecem em parte.");
assert.equal(leituraSeparacao("0,1"), "A separação entre os grupos é 0,10, numa escala de 0 a 1: os grupos quase não se distinguem.");
assert.equal(leituraSeparacao("0,7200"), "A separação entre os grupos é 0,72, numa escala de 0 a 1: os grupos são muito diferentes entre si.");
assert.equal(leituraSeparacao("-0,0500"), "A separação entre os grupos é −0,05, abaixo de zero: os grupos se confundem.");
assert.equal(leituraSeparacao(null), null);
assert.equal(leituraSeparacao("x"), null);
console.log("ok");
