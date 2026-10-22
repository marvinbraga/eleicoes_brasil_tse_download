import assert from "node:assert/strict";
import { layoutAcertoUf, resumoAcertoUf, LARGURA, RAIO_MAX, RAIO_MIN, TOPO, ALTURA_LINHA } from "./grafico-acerto-uf.ts";

const base = { acerto: "50,48%", base: "62,61%", baseLider: "51,75%" };
const tres = { ...base, porUf: [
  { uf: "BA", municipios: 417, acerto: "9,83%" },
  { uf: "AC", municipios: 22, acerto: "100,00%" },
  { uf: "MG", municipios: 853, acerto: "95,08%" },
] };

// ordem, coordenadas e raios
const l = layoutAcertoUf(tres)!;
assert.deepEqual(l.pontos.map((p) => p.uf), ["AC", "MG", "BA"]);
assert.equal(l.pontos[0].x, 624);
assert.ok(Math.abs(l.pontos[2].x - (44 + 0.0983 * 580)) < 1e-9);
assert.equal(l.pontos[0].y, TOPO + ALTURA_LINHA / 2);
assert.equal(l.pontos[1].raio, RAIO_MAX);
assert.ok(Math.abs(l.pontos[0].raio - (RAIO_MIN + 6 * Math.sqrt(22 / 853))) < 1e-9);
assert.ok(l.pontos[0].x + RAIO_MAX <= LARGURA);
assert.equal(l.altura, TOPO + 3 * ALTURA_LINHA + 28);
assert.deepEqual([l.menorMunicipios, l.maiorMunicipios], [22, 853]);
assert.deepEqual(l.marcas.map((m) => m.rotulo), ["0%", "25%", "50%", "75%", "100%"]);

// faixas dos rótulos: 50,48 e 51,75 não dividem faixa; 62,61 também não cabe nas duas primeiras
assert.deepEqual(l.linhas.map((r) => [r.chave, r.faixa]), [["acerto", 0], ["base_lider", 1], ["base", 2]]);
assert.ok(l.linhas.every((r) => r.ancora === "start"));
assert.equal(layoutAcertoUf({ ...tres, base: "98,00%" })!.linhas.find((r) => r.chave === "base")!.ancora, "end");

// entradas ruins
assert.equal(layoutAcertoUf({ ...base, porUf: [] }), null);
const ruim = layoutAcertoUf({ ...base, porUf: [...tres.porUf, { uf: "PI", municipios: 224, acerto: "—" }] })!;
assert.equal(ruim.descartadas, 1);
assert.equal(ruim.pontos.length, 3);
assert.equal(layoutAcertoUf({ ...base, baseLider: "x", porUf: tres.porUf })!.linhas.length, 2);
const zero = layoutAcertoUf({ ...base, porUf: [{ uf: "DF", municipios: 0, acerto: "100,00%" }] })!;
assert.equal(zero.pontos[0].raio, RAIO_MIN);
const empate = layoutAcertoUf({ ...base, porUf: [
  { uf: "TO", municipios: 1, acerto: "100,00%" }, { uf: "AL", municipios: 1, acerto: "100,00%" }] })!;
assert.deepEqual(empate.pontos.map((p) => p.uf), ["AL", "TO"]);

// resumo
assert.equal(resumoAcertoUf(tres),
  "3 UFs. Maior acerto: AC com 100,00%. Menor: BA com 9,83%. 1 de 3 UFs ficam abaixo da base da maioria (62,61%).");
assert.equal(resumoAcertoUf({ ...base, porUf: [
  { uf: "TO", municipios: 1, acerto: "100,00%" }, { uf: "AL", municipios: 1, acerto: "100,00%" },
  { uf: "AP", municipios: 1, acerto: "100,00%" }, { uf: "PI", municipios: 1, acerto: "1,34%" }] }),
  "4 UFs. Maior acerto: AL, AP e TO com 100,00%. Menor: PI com 1,34%. 1 de 4 UFs ficam abaixo da base da maioria (62,61%).");
console.log("ok");
