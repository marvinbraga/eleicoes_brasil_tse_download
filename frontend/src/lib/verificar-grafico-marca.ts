import assert from "node:assert/strict";
import {
  MEDIDAS_HALTERES_ESTREITO,
  MEDIDAS_HALTERES_PADRAO,
  MINIMO_VOTOS_RANKING,
  classeMarca,
  comparacaoCargos,
  estadoCelula,
  fatiaLegendaNacional,
  formatarVezes,
  itensRanking,
  layoutHalteres,
  layoutRanking,
  leituraMarca,
  marcaDoCargo,
  resumoHalteres,
  resumoRanking,
  type LayoutHalteres,
  type LayoutRanking,
  type MarcaCargo,
} from "./grafico-marca.ts";
import { MEDIDAS_ESTREITO, MEDIDAS_PADRAO } from "./grafico-poder.ts";
import { larguraTexto } from "./largura-texto.ts";
import type { GradeRelatorio, LinhaGrade } from "./relatorios.ts";

type Par = [nominais: number, legenda: number];

function linha(codigo: string, nome: string, votos: Record<number, Par>): LinhaGrade {
  return {
    codigo,
    nome,
    comparecimento: 0,
    celulas: Object.entries(votos).map(([partido, [nominais, legenda]]) => ({
      partido: Number(partido),
      votos_nominais: nominais,
      votos_legenda: legenda,
      comparecimento: 0,
      votos: nominais + legenda,
      fatia: "0",
    })),
  };
}

function grade(cargo: string, linhas: LinhaGrade[]): GradeRelatorio {
  return { ano: 2026, turno: 1, uf: "AC", cargo, nivel: "uf", colunas: [], linhas };
}

const gradeFederal = grade("deputadoFederal", [
  linha("AC", "Acre", { 12: [40_000, 10_000], 13: [90_000, 10_000], 16: [1_000, 1_000], 18: [0, 2_000], 20: [49_500, 500] }),
  linha("BA", "Bahia", { 12: [60_000, 40_000], 13: [180_000, 20_000], 16: [0, 0], 18: [3_000, 1_000], 20: [99_000, 1_000] }),
  linha("DF", "Distrito Federal", { 12: [0, 0], 13: [27_000, 3_000], 16: [0, 0], 18: [0, 0], 20: [19_800, 200] }),
]);
const gradeEstadual = grade("deputadoEstadual", [
  linha("AC", "Acre", { 12: [45_000, 5_000], 13: [80_000, 20_000], 16: [0, 0], 18: [500, 500], 20: [58_800, 1_200] }),
  linha("BA", "Bahia", { 12: [90_000, 10_000], 13: [160_000, 40_000], 16: [0, 0], 18: [0, 0], 20: [117_600, 2_400] }),
]);
const federal = marcaDoCargo("deputadoFederal", gradeFederal) as MarcaCargo;
const estadual = marcaDoCargo("deputadoEstadual", gradeEstadual) as MarcaCargo;

// total do cargo: soma das UFs, inclusive os partidos fora do ranking
assert.equal(federal.rotulo, "deputado federal");
assert.equal(federal.legenda, 88_700);
assert.equal(federal.votos, 658_000);
assert.equal(federal.texto, "13,48%");
assert.equal(estadual.texto, "12,54%");

// ranking: ordem, parte, múltiplo e classe relativos à média do cargo
const resumir = (marca: MarcaCargo) =>
  marca.ranking.map((item) => [item.rotulo, item.texto, item.vezes, item.classe]);
assert.deepEqual(resumir(federal), [
  ["PDT 12", "33,33%", "2,47×", "forte"],
  ["PT 13", "10,00%", "0,74×", "media"],
  ["PODE 20", "1,00%", "0,07×", "pessoa"],
]);
assert.deepEqual(resumir(estadual), [
  ["PT 13", "20,00%", "1,60×", "media"],
  ["PDT 12", "10,00%", "0,80×", "media"],
  ["PODE 20", "2,00%", "0,16×", "pessoa"],
]);
assert.ok(Math.abs(federal.ranking[0].indice - (50_000 / 150_000) / (88_700 / 658_000)) < 1e-12);

// fora do ranking: listados, nunca descartados; partido zerado não aparece
assert.deepEqual(federal.fora.map((item) => [item.rotulo, item.texto, item.votos]), [
  ["REDE 18", "50,00%", 6_000],
  ["PSTU 16", "50,00%", 2_000],
]);
assert.deepEqual(estadual.fora.map((item) => item.rotulo), ["REDE 18"]);
assert.ok(![...estadual.ranking, ...estadual.fora].some((item) => item.partido === 16));

// limiares exatos: 2× é forte, 0,5× é pessoa; empate pelo número
const limiar = marcaDoCargo("deputadoFederal", grade("deputadoFederal", [
  linha("SP", "São Paulo", { 10: [80_000, 20_000], 11: [95_000, 5_000], 15: [95_000, 5_000] }),
])) as MarcaCargo;
assert.equal(limiar.texto, "10,00%");
assert.deepEqual(resumir(limiar), [
  ["REPUBLICANOS 10", "20,00%", "2,00×", "forte"],
  ["PP 11", "5,00%", "0,50×", "pessoa"],
  ["MDB 15", "5,00%", "0,50×", "pessoa"],
]);
assert.equal(classeMarca(1, 100, 1, 50), "pessoa");
assert.equal(classeMarca(2, 100, 1, 50), "media");
assert.equal(classeMarca(4, 100, 1, 50), "forte");
assert.equal(classeMarca(5, 100, 0, 50), "media");
assert.equal(formatarVezes(5, 100, 0, 50), "—");
assert.equal(formatarVezes(1, 3, 1, 1), "0,33×");
assert.equal(formatarVezes(2, 3, 1, 1), "0,67×");

// mínimo de votos: 99.999 fica fora, 100.000 entra; sem legenda no cargo, tudo "media"
const minimo = marcaDoCargo("deputadoFederal", grade("deputadoFederal", [
  linha("SP", "São Paulo", { 55: [MINIMO_VOTOS_RANKING - 1, 0], 70: [MINIMO_VOTOS_RANKING, 0] }),
])) as MarcaCargo;
assert.deepEqual(minimo.ranking.map((item) => [item.rotulo, item.classe, item.vezes]), [["AVANTE 70", "media", "—"]]);
assert.deepEqual(minimo.fora.map((item) => item.rotulo), ["PSD 55"]);

// empate de parte: mais votos primeiro, depois o menor número
const empate = marcaDoCargo("deputadoFederal", grade("deputadoFederal", [
  linha("RJ", "Rio de Janeiro", { 50: [90_000, 10_000], 22: [180_000, 20_000], 40: [90_000, 10_000], 13: [90_000, 10_000] }),
])) as MarcaCargo;
assert.deepEqual(empate.ranking.map((item) => item.rotulo), ["PL 22", "PT 13", "PSB 40", "PSOL 50"]);

// cargo sem votos
assert.equal(marcaDoCargo("deputadoFederal", grade("deputadoFederal", [linha("AC", "Acre", { 13: [0, 0] })])), null);
assert.equal(marcaDoCargo("deputadoFederal", grade("deputadoFederal", [])), null);

// estado da célula UF × partido
assert.equal(estadoCelula(0, 0), "sem-votos");
assert.equal(estadoCelula(0, 2_287), "sem-candidato");
assert.equal(estadoCelula(4_000, 999), "poucos");
assert.equal(estadoCelula(4_000, 1_000), "ok");

// UFs: média por UF e células só dos partidos do ranking, na ordem do ranking
assert.deepEqual(federal.ufs.map((uf) => [uf.uf, uf.nome, uf.texto]), [
  ["AC", "Acre", "11,52%"],
  ["BA", "Bahia", "15,35%"],
  ["DF", "Distrito Federal", "6,40%"],
]);
assert.deepEqual(federal.ufs[2].celulas.map((celula) => [celula.partido, celula.texto, celula.estado]), [
  [12, "—", "sem-votos"],
  [13, "10,00%", "ok"],
  [20, "1,00%", "ok"],
]);
assert.deepEqual(federal.ufs[1].celulas.map((celula) => celula.texto), ["40,00%", "10,00%", "1,00%"]);
assert.deepEqual(estadual.ufs.map((uf) => [uf.uf, uf.texto]), [["AC", "12,65%"], ["BA", "12,48%"]]);

// contrato do Placar: todo partido com votos, sem mínimo, em ordem de número
assert.deepEqual(
  [...fatiaLegendaNacional(gradeFederal).entries()].map(([partido, item]) => [partido, item.legenda, item.votos, item.texto]),
  [
    [12, 50_000, 150_000, "33,33%"],
    [13, 33_000, 330_000, "10,00%"],
    [16, 1_000, 2_000, "50,00%"],
    [18, 3_000, 6_000, "50,00%"],
    [20, 1_700, 170_000, "1,00%"],
  ],
);

// comparação federal × estadual pelo múltiplo da média de cada cargo
const comparacao = comparacaoCargos(federal, estadual);
assert.deepEqual(comparacao.pares.map((par) => par.rotulo), ["PDT 12", "PT 13", "PODE 20"]);
assert.equal(comparacao.maisMuda?.rotulo, "PDT 12");
assert.equal(comparacaoCargos(minimo, minimo).maisMuda, null);

// leitura com os dois cargos
assert.deepEqual(leituraMarca(federal, estadual), [
  "No Brasil, 13,48% dos votos para deputado federal foram só no número do partido. Para deputado estadual, foram 12,54% (sem o DF, que elege deputados distritais).",
  "Marca forte para deputado federal: PDT 12, com 33,33% de voto de legenda, pelo menos o dobro da média do cargo (13,48%).",
  "Voto na pessoa para deputado federal: PODE 20, com 1,00% de voto de legenda, no máximo a metade da média do cargo (13,48%).",
  "Para deputado estadual, nenhum partido do ranking chega ao dobro da média do cargo (12,54%).",
  "Voto na pessoa para deputado estadual: PODE 20, com 2,00% de voto de legenda, no máximo a metade da média do cargo (12,54%).",
  "PDT 12 é o partido cuja marca mais muda entre os cargos: para deputado federal, tem 33,33% de voto de legenda (2,47× a média do cargo); para deputado estadual, 10,00% (0,80× a média do cargo).",
  "Para deputado federal, a UF com mais voto de legenda é Bahia (15,35%) e a com menos é Distrito Federal (6,40%).",
  "Para deputado estadual, a UF com mais voto de legenda é Acre (12,65%) e a com menos é Bahia (12,48%).",
  "Fora do ranking de deputado federal, por terem menos de 100.000 votos: REDE 18 (50,00% de legenda em 6.000 votos) e PSTU 16 (50,00% de legenda em 2.000 votos).",
  "Fora do ranking de deputado estadual, por terem menos de 100.000 votos: REDE 18 (50,00% de legenda em 1.000 votos).",
]);

// um cargo só, vários "pessoa" e UF única
assert.deepEqual(leituraMarca(limiar, null), [
  "No Brasil, 10,00% dos votos para deputado federal foram só no número do partido.",
  "Marca forte para deputado federal: REPUBLICANOS 10, com 20,00% de voto de legenda, pelo menos o dobro da média do cargo (10,00%).",
  "Voto na pessoa para deputado federal: PP 11 (5,00%) e MDB 15 (5,00%), cada um com no máximo a metade da média do cargo (10,00%).",
  "Para deputado federal, a única UF é São Paulo, com 10,00% de voto de legenda.",
]);
assert.equal(
  leituraMarca(null, estadual)[0],
  "No Brasil, 12,54% dos votos para deputado estadual foram só no número do partido (sem o DF, que elege deputados distritais).",
);
assert.deepEqual(leituraMarca(null, null), []);

// ranking: barras da grafico-poder, escala que inclui a média e linha de referência
const itens = itensRanking(federal);
assert.equal(itens[0].detalhe, "50.000 de 150.000 votos foram de legenda\nMarca forte (2,47× a média do cargo)");
const ranking = layoutRanking(federal) as LayoutRanking;
const util = MEDIDAS_PADRAO.largura - MEDIDAS_PADRAO.esquerda - MEDIDAS_PADRAO.direita;
assert.equal(ranking.barras.length, 3);
assert.ok(Math.abs(ranking.barras[0].largura - util) < 1e-9);
assert.deepEqual(ranking.barras.map((barra) => barra.classe), ["forte", "media", "pessoa"]);
assert.ok(Math.abs(ranking.xReferencia - (MEDIDAS_PADRAO.esquerda + ((88_700 / 658_000) / (1 / 3)) * util)) < 1e-9);
// média acima de todas as barras (fora do ranking puxa a média): a escala passa a ser a média
const puxada = marcaDoCargo("deputadoFederal", grade("deputadoFederal", [
  linha("SP", "São Paulo", { 13: [100_000, 1_000], 16: [10_000, 80_000] }),
])) as MarcaCargo;
const layoutPuxado = layoutRanking(puxada) as LayoutRanking;
assert.equal(layoutPuxado.xReferencia, MEDIDAS_PADRAO.largura - MEDIDAS_PADRAO.direita);
assert.ok(layoutPuxado.barras[0].largura < util);
assert.equal(layoutRanking({ ...federal, ranking: [] }), null);
const rankingEstreito = layoutRanking(federal, MEDIDAS_ESTREITO) as LayoutRanking;
assert.ok(rankingEstreito.xReferencia <= MEDIDAS_ESTREITO.largura - MEDIDAS_ESTREITO.direita);
assert.equal(
  resumoRanking(federal),
  "Voto de legenda por partido, deputado federal, média do cargo 13,48%. PDT 12: 33,33%; PT 13: 10,00%; PODE 20: 1,00%.",
);

// halteres: múltiplo da média de cada cargo
const halteres = layoutHalteres(comparacao.pares) as LayoutHalteres;
const mh = MEDIDAS_HALTERES_PADRAO;
const utilH = mh.largura - mh.esquerda - mh.direita;
assert.ok(Math.abs(halteres.escala - (50_000 / 150_000) / (88_700 / 658_000)) < 1e-12);
assert.ok(Math.abs(halteres.halteres[0].xFederal - (mh.largura - mh.direita)) < 1e-9);
assert.equal(halteres.halteres[0].y, mh.topo + mh.alturaLinha / 2);
assert.equal(halteres.altura, mh.topo + 3 * mh.alturaLinha + mh.base);
assert.equal(halteres.halteres[0].dica, "Deputado federal: 33,33% (2,47× a média)\nDeputado estadual: 10,00% (0,80× a média)");
assert.deepEqual(halteres.referencias.map((ref) => ref.rotulo), ["0,5×", "1×", "2×"]);
assert.ok(Math.abs(halteres.referencias[1].x - (mh.esquerda + utilH / halteres.escala)) < 1e-9);
assert.equal(layoutHalteres([]), null);
// escala mínima 2: com múltiplos pequenos, 2× continua dentro do desenho
const pequenos = layoutHalteres(comparacaoCargos(estadual, estadual).pares) as LayoutHalteres;
assert.equal(pequenos.escala, 2);
assert.equal(pequenos.referencias[2].x, mh.largura - mh.direita);
// estreito: rótulo acima da linha, nada passa da borda, rótulos de referência não se sobrepõem
const me = MEDIDAS_HALTERES_ESTREITO;
const estreito = layoutHalteres(comparacao.pares, me) as LayoutHalteres;
for (const [indice, haltere] of estreito.halteres.entries()) {
  const topoLinha = me.topo + indice * me.alturaLinha;
  assert.ok(haltere.y - me.raio - 5 - me.fonte >= topoLinha);
  assert.ok(haltere.y + me.raio <= topoLinha + me.alturaLinha);
  assert.ok(Math.max(haltere.xFederal, haltere.xEstadual) + me.raio <= me.largura);
}
const visiveis = estreito.referencias.filter((ref) => ref.rotulo !== "");
for (let indice = 1; indice < visiveis.length; indice += 1) {
  assert.ok(visiveis[indice].x - visiveis[indice - 1].x >= larguraTexto(visiveis[indice].rotulo, me.fonte) + 4);
}
assert.equal(
  resumoHalteres(comparacao.pares),
  "Voto de legenda como múltiplo da média de cada cargo. PDT 12: federal 2,47×, estadual 0,80×; PT 13: federal 0,74×, estadual 1,60×; PODE 20: federal 0,07×, estadual 0,16×.",
);

console.log("ok");
