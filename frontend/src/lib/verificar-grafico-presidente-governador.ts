import assert from "node:assert/strict";
import { COR_CLASSE } from "../cruzamento/finalidade.ts";
import {
  ALTURA_LINHA,
  BASE,
  ESQUERDA_UF,
  MEDIDAS_ESTREITO,
  MEDIDAS_PADRAO,
  TOPO,
  composicaoPorRegiao,
  composicaoPorUf,
  frasesComposicao,
  layoutComposicao,
  resumoComposicao,
} from "./grafico-presidente-governador.ts";
import { larguraTexto } from "./largura-texto.ts";
import type { GrupoMunicipios, LeituraLugar } from "./relatorios.ts";

function lugar(classe: string, valid: number): LeituraLugar {
  const cargo = { leader: null, runner_up: null, valid, branco: 0, nulo: 0 };
  return { codigo: "1", nome: "X", classe, margin: "0/1", presidente: cargo, governador: cargo };
}

function grupo(uf: string, votos: Record<string, number>): GrupoMunicipios {
  return { uf, places: Object.entries(votos).map(([classe, valid]) => lugar(classe, valid)) };
}

const grupos = [
  grupo("AC", { em_aberto: 50 }),
  grupo("BA", { consolidacao: 300, terreno_de_virada: 300, em_aberto: 400 }),
  grupo("ZZ", { sem_governador: 10 }),
  grupo("PI", { consolidacao: 0 }),
  grupo("SC", { consolidacao: 900, em_aberto: 100 }),
  grupo("AL", { em_aberto: 20 }),
];

// agregação e ordem
const porUf = composicaoPorUf(grupos);
assert.deepEqual(porUf.map((l) => l.codigo), ["SC", "BA", "AC", "AL"]);
assert.deepEqual(porUf[1].votos, { consolidacao: 300, terreno_de_virada: 300, em_aberto: 400, sem_governador: 0 });
assert.equal(porUf[1].total, 1000);
const porRegiao = composicaoPorRegiao(porUf);
assert.deepEqual(porRegiao.map((l) => [l.codigo, l.total]), [["Sul", 1000], ["Nordeste", 1020], ["Norte", 50]]);
assert.equal(porRegiao[1].votos.em_aberto, 420);

// layout
const l = layoutComposicao(porUf, ESQUERDA_UF)!;
assert.equal(l.altura, TOPO + 4 * ALTURA_LINHA + BASE);
assert.equal(l.barras[0].y, TOPO + 5);
const sc = l.barras[0].fatias;
assert.deepEqual(sc.map((f) => f.classe), ["consolidacao", "terreno_de_virada", "em_aberto", "sem_governador"]);
assert.deepEqual(sc.map((f) => [f.x, f.largura]), [[44, 521], [566, 0], [566, 58], [624, 0]]);
assert.deepEqual(sc.map((f) => f.fatiaTexto), ["90,00%", "0,00%", "10,00%", "0,00%"]);
assert.equal(sc[0].cor, COR_CLASSE.consolidacao);
assert.deepEqual(l.barras[1].fatias.map((f) => [f.x, f.largura]), [[44, 173], [218, 173], [392, 232], [624, 0]]);
const ultima = l.barras[1].fatias[2];
assert.equal(ultima.x + ultima.largura, 640 - 16);
assert.deepEqual(l.marcas.map((m) => [m.x, m.rotulo]), [[44, "0%"], [189, "25%"], [334, "50%"], [479, "75%"], [624, "100%"]]);
const minima = layoutComposicao(composicaoPorUf([grupo("SP", { consolidacao: 1, em_aberto: 99999 })]), ESQUERDA_UF)!;
assert.equal(minima.barras[0].fatias[0].largura, 1);
assert.equal(minima.barras[0].fatias[0].fatiaTexto, "0,00%");
const [miuda, , depois] = minima.barras[0].fatias;
assert.equal(depois.x, miuda.x + miuda.largura + 1);
assert.equal(depois.x + depois.largura, 640 - 16);
assert.equal(layoutComposicao([], ESQUERDA_UF), null);

// frases
assert.deepEqual(frasesComposicao(porUf, "UFs"), [
  "Em 3 de 4 UFs a maior parte dos votos válidos de presidente está em municípios em aberto. Na outra, está em municípios em consolidação.",
  "Maior fatia de consolidação: SC, com 90,00%. Em 2 de 4 UFs nenhum voto está em municípios em consolidação; entre as demais, a menor é BA, com 30,00%.",
]);
assert.deepEqual(frasesComposicao(porRegiao, "regiões"), [
  "Em 2 de 3 regiões a maior parte dos votos válidos de presidente está em municípios em aberto. Na outra, está em municípios em consolidação.",
  "Maior fatia de consolidação: Sul, com 90,00%. Em 1 de 3 regiões nenhum voto está em municípios em consolidação; entre as demais, a menor é Nordeste, com 29,41%.",
]);
const variadas = composicaoPorUf([
  grupo("SC", { consolidacao: 9, em_aberto: 1 }),
  grupo("RN", { consolidacao: 10, terreno_de_virada: 20 }),
  grupo("PR", { consolidacao: 9, em_aberto: 1 }),
  grupo("AM", { consolidacao: 1, em_aberto: 3 }),
  grupo("MG", { consolidacao: 2, em_aberto: 98 }),
  grupo("RS", { consolidacao: 5, terreno_de_virada: 5 }),
]);
assert.deepEqual(frasesComposicao(variadas, "UFs"), [
  "Em 3 de 6 UFs a maior parte dos votos válidos de presidente está em municípios em consolidação. Nas outras 3, a maior fatia é Em aberto (2) ou Terreno de virada (1).",
  "Maior fatia de consolidação: PR e SC, com 90,00%. Menor: MG, com 2,00%.",
]);
assert.deepEqual(frasesComposicao(composicaoPorUf([grupo("AC", { em_aberto: 5 })]), "UFs"), [
  "Em 1 de 1 UFs a maior parte dos votos válidos de presidente está em municípios em aberto.",
  "Nenhuma UF tem voto em municípios em consolidação.",
]);
assert.deepEqual(frasesComposicao([], "UFs"), []);
assert.equal(
  resumoComposicao(porUf, "UFs"),
  `4 UFs, da maior para a menor fatia de consolidação. ${frasesComposicao(porUf, "UFs").join(" ")}`,
);
// variante estreita
const CONTENTOR = 300;
const me = MEDIDAS_ESTREITO;
const eUf = layoutComposicao(porUf, me.esquerdaUf, me)!;
const eRegiao = layoutComposicao(porRegiao, me.esquerdaRegiao, me)!;
assert.equal(eUf.largura, 340);
assert.equal(l.medidas, MEDIDAS_PADRAO);
assert.ok((Math.min(me.fonte, me.fonteMenor) * CONTENTOR) / eUf.largura >= 11);
assert.ok(me.esquerdaUf - 8 >= larguraTexto("AC", me.fonte));
const regioes = ["Norte", "Nordeste", "Centro-Oeste", "Sudeste", "Sul"];
assert.ok(me.esquerdaRegiao - 8 >= Math.max(...regioes.map((r) => larguraTexto(r, me.fonte))));
for (const layout of [eUf, eRegiao]) {
  const fim = layout.marcas[layout.marcas.length - 1];
  assert.ok(fim.x + larguraTexto(fim.rotulo, me.fonteMenor) / 2 <= layout.largura);
  assert.ok(layout.marcas[0].x - larguraTexto(layout.marcas[0].rotulo, me.fonteMenor) / 2 >= 0);
  for (const barra of layout.barras) {
    const ultimaFatia = barra.fatias.filter((f) => f.largura > 0).at(-1)!;
    assert.equal(ultimaFatia.x + ultimaFatia.largura, layout.largura - me.direita);
  }
}
assert.equal(eUf.altura, me.topo + 4 * me.alturaLinha + me.base);
assert.equal(eUf.barras[0].y, me.topo + (me.alturaLinha - me.alturaBarra) / 2);
console.log("ok");
