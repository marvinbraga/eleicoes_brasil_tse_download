import assert from "node:assert/strict";
import {
  CHAVES_FAIXA,
  type ClasseCapilaridade,
  type FaixaCapilaridade,
  type PartidoCapilaridade,
  type Recorte,
} from "./capilaridade.ts";
import {
  MEDIDAS_FAIXAS,
  MEDIDAS_FAIXAS_ESTREITO,
  MEDIDAS_RANKING,
  MEDIDAS_RANKING_ESTREITO,
  ROTULOS_FAIXA,
  layoutFaixas,
  layoutRanking,
  leituraCapilaridade,
  resumoFaixas,
  resumoRanking,
  textosFaixas,
  textosRanking,
} from "./grafico-capilaridade.ts";
import { problemasEstreito } from "./texto-svg.ts";

function faixas(municipios: number[], votos: number[]): FaixaCapilaridade[] {
  return CHAVES_FAIXA.map((chave, i) => ({
    chave,
    municipios: municipios[i] ?? 0,
    votos_validos: (municipios[i] ?? 0) * 100,
    votos: votos[i] ?? 0,
  }));
}

function partido(
  numero: number,
  indice: number,
  classe: ClasseCapilaridade,
  rotulo: string,
  extra: Partial<PartidoCapilaridade> = {},
): PartidoCapilaridade {
  return {
    partido: numero,
    votos: 1000 * numero,
    votos_validos: 100_000,
    votos_validos_recorte: 120_000,
    fatia: "1/10",
    fatia_texto: "10,00%",
    fatia_recorte_texto: "8,33%",
    ufs_com_voto: 27,
    municipios: 5571,
    indice: `${indice}/100`,
    indice_texto: `0,${String(indice).padStart(2, "0")}00`,
    indice_100: indice,
    top10: {
      municipios: 558,
      votos: 3130,
      parte: "313/1000",
      parte_texto: "31,30%",
      eleitorado: "73/1000",
      eleitorado_texto: "7,30%",
      vezes: "4,29",
    },
    presenca: { municipios: 4000, parte: "4000/5571", parte_texto: "71,80%" },
    capitais: null,
    subdivisoes: [],
    faixas: faixas([100, 900, 1500, 1500, 800, 500, 271], [0, 50, 300, 400, 100, 100, 50]),
    fortes: [],
    maiores: [],
    classe,
    rotulo_classe: rotulo,
    motivo: "Nenhuma regra de concentração se aplicou.",
    ...extra,
  };
}

const PARTIDOS = [
  partido(50, 62, "capitais", "Concentrado nas capitais"),
  partido(22, 50, "espalhado", "Nacional / espalhado"),
  partido(13, 20, "espalhado", "Nacional / espalhado"),
  partido(80, 90, "pouco_voto", "Pouco voto"),
];
const href = (numero: number) => `?partido=${numero}`;

// Ranking: order from the backend, pouco_voto out, fixed 0-100 scale.
const ranking = layoutRanking(PARTIDOS, 22, href);
assert.ok(ranking !== null);
assert.deepEqual(
  ranking.barras.map((barra) => barra.partido),
  [50, 22, 13],
);
const util = MEDIDAS_RANKING.largura - MEDIDAS_RANKING.esquerda - MEDIDAS_RANKING.direita;
const meio = ranking.barras.find((barra) => barra.partido === 22);
assert.ok(meio !== undefined);
assert.equal(meio.largura, util / 2);
assert.equal(ranking.barras.filter((barra) => barra.selecionado).length, 1);
assert.equal(meio.selecionado, true);
assert.equal(meio.href, "?partido=22");
assert.equal(meio.rotulo, "PL 22");
assert.equal(meio.classe, "Nacional / espalhado");
assert.deepEqual(meio.dica, [
  "Índice 50 de 100",
  "Nacional / espalhado",
  "Fatia 10,00%",
  "10% mais fortes: 31,30% dos votos, 7,30% do eleitorado",
]);
assert.deepEqual(
  ranking.marcas.map((marca) => marca.texto),
  ["0", "25", "50", "75", "100"],
);
assert.equal(ranking.marcas[0]?.x, MEDIDAS_RANKING.esquerda);
assert.equal(ranking.marcas[4]?.x, MEDIDAS_RANKING.esquerda + util);
assert.ok(ranking.barras[1] !== undefined && ranking.barras[0] !== undefined);
assert.ok(ranking.barras[1].y > ranking.barras[0].y);
assert.equal(layoutRanking([PARTIDOS[3] as PartidoCapilaridade], 80, href), null);
assert.equal(layoutRanking([], 0, href), null);

const estreito = layoutRanking(PARTIDOS, 22, href, MEDIDAS_RANKING_ESTREITO);
assert.ok(estreito !== null);
assert.equal(estreito.largura, 340);
assert.equal(MEDIDAS_RANKING_ESTREITO.rotuloAcima, true);
const utilEstreito =
  MEDIDAS_RANKING_ESTREITO.largura -
  MEDIDAS_RANKING_ESTREITO.esquerda -
  MEDIDAS_RANKING_ESTREITO.direita;
assert.equal(estreito.barras[1]?.largura, utilEstreito / 2);

// Telefone (~301 px de desenho): ≥ 11 px CSS, nada fora do viewBox, nada sobreposto. A classe
// longa desce para linhas próprias em vez de alargar o viewBox (o que encolheria a fonte).
const LONGOS = [
  partido(77, 100, "poucos_municipios", "Concentrado em poucos municípios"),
  partido(10, 0, "regional", "Concentrado em uma UF (Rio Grande do Norte)"),
  partido(36, 55, "poucos_municipios", "Concentrado em poucos municípios"),
  ...PARTIDOS,
];
for (const [nome, lista] of [["ranking", PARTIDOS], ["ranking com classes longas", LONGOS]] as const) {
  const layout = layoutRanking(lista, 22, href, MEDIDAS_RANKING_ESTREITO);
  assert.ok(layout !== null);
  assert.equal(layout.largura, 340, nome);
  assert.deepEqual(problemasEstreito(textosRanking(layout), layout.largura, layout.altura), [], nome);
}
const longos = layoutRanking(LONGOS, 22, href, MEDIDAS_RANKING_ESTREITO);
assert.ok(longos !== null);
const solidariedade = longos.barras[0];
assert.ok(solidariedade !== undefined);
assert.equal(solidariedade.classeNaLinha, false);
assert.equal(solidariedade.linhasClasse.join(" "), "Concentrado em poucos municípios");
assert.equal(solidariedade.alturaLinha, MEDIDAS_RANKING_ESTREITO.alturaLinha + 15 * solidariedade.linhasClasse.length);
longos.barras.slice(1).forEach((barra, i) => {
  const anterior = longos.barras[i];
  assert.ok(anterior !== undefined);
  assert.equal(barra.topoLinha, anterior.topoLinha + anterior.alturaLinha);
});
assert.equal(estreito.barras.every((barra) => barra.classeNaLinha), true);
// o "0" da escala inteiro dentro do desenho
const zero = textosRanking(estreito).find((texto) => texto.chave === "marca-0");
assert.ok(zero !== undefined && zero.x - (0.6 * zero.fonte) / 2 >= 0);
// largo sem mudança: escala com fonte 11, rótulo à esquerda da barra, sem linhas de classe
const textosLargos = textosRanking(ranking);
assert.equal(textosLargos.find((texto) => texto.chave === "marca-0")?.fonte, 11);
assert.equal(textosLargos.find((texto) => texto.chave === "rotulo-22")?.x, MEDIDAS_RANKING.esquerda - 8);
assert.equal(ranking.barras[1]?.y, MEDIDAS_RANKING.topo + MEDIDAS_RANKING.alturaLinha);
assert.equal(ranking.altura, MEDIDAS_RANKING.topo + 3 * MEDIDAS_RANKING.alturaLinha + MEDIDAS_RANKING.base);

const resumo = resumoRanking(PARTIDOS);
for (const texto of ["PSOL 50", "62", "PL 22", "50", "PT 13", "20", "Concentrado nas capitais"]) {
  assert.ok(resumo.includes(texto), `resumo sem ${texto}: ${resumo}`);
}
assert.ok(!resumo.includes("UP 80"));

// Faixas.
const base = PARTIDOS[1] as PartidoCapilaridade;
const municipios = layoutFaixas(base.faixas, "municipios");
assert.ok(municipios !== null);
assert.equal(municipios.colunas.length, 7);
assert.equal(municipios.colunas[0]?.neutra, true);
assert.equal(municipios.colunas.filter((coluna) => coluna.neutra).length, 1);
assert.equal(municipios.colunas[0]?.valor, "1,80%");
const area = MEDIDAS_FAIXAS.altura - MEDIDAS_FAIXAS.topo - MEDIDAS_FAIXAS.base;
const maisAlta = Math.max(...municipios.colunas.map((coluna) => coluna.altura));
assert.equal(maisAlta, area);
for (const coluna of municipios.colunas) {
  assert.ok(coluna.altura >= 0 && coluna.altura <= area);
  assert.ok(coluna.y >= MEDIDAS_FAIXAS.topo);
  assert.ok(coluna.x + coluna.largura <= MEDIDAS_FAIXAS.largura - MEDIDAS_FAIXAS.direita + 1e-9);
}
const votos = layoutFaixas(base.faixas, "votos");
assert.ok(votos !== null);
assert.equal(votos.colunas[0]?.valor, "—");
assert.equal(votos.colunas[0]?.altura, 0);
assert.equal(votos.colunas[3]?.valor, "40,00%");
assert.equal(votos.colunas[3]?.altura, area);
assert.equal(layoutFaixas(faixas([], []), "municipios"), null);
assert.equal(layoutFaixas(faixas([3], []), "votos"), null);
const faixasEstreito = layoutFaixas(base.faixas, "municipios", MEDIDAS_FAIXAS_ESTREITO);
assert.equal(faixasEstreito?.largura, 340);
for (const [nome, lista] of [
  ["faixas", base.faixas],
  ["faixas com 100%", faixas([0, 0, 0, 0, 0, 0, 5571], [0, 0, 0, 0, 0, 0, 999])],
  ["faixas com valores longos", faixas([1111, 1111, 1111, 1111, 1, 1, 1125], [333, 333, 333, 1, 0, 0, 0])],
] as const) {
  for (const medida of ["municipios", "votos"] as const) {
    const layout = layoutFaixas(lista, medida, MEDIDAS_FAIXAS_ESTREITO);
    assert.ok(layout !== null, `${nome} ${medida}`);
    assert.deepEqual(problemasEstreito(textosFaixas(layout), layout.largura, layout.altura), [], `${nome} ${medida}`);
  }
}
// largo sem mudança: valor e título do eixo com fonte 10, rótulo da faixa 14 abaixo do chão
const faixasLargas = layoutFaixas(base.faixas, "municipios");
assert.ok(faixasLargas !== null);
const textosFaixasLargas = textosFaixas(faixasLargas);
assert.equal(textosFaixasLargas.find((texto) => texto.chave === "eixo")?.fonte, 10);
assert.equal(textosFaixasLargas.find((texto) => texto.chave === "valor-zero")?.fonte, 10);
assert.equal(textosFaixasLargas.find((texto) => texto.chave === "faixa-zero")?.y, MEDIDAS_FAIXAS.altura - MEDIDAS_FAIXAS.base + 14);
assert.equal(ROTULOS_FAIXA["3_ou_mais"].curto, "3+");
assert.equal(ROTULOS_FAIXA.zero.longo, "Sem voto");
const resumoMunicipios = resumoFaixas(base, "municipios");
assert.ok(resumoMunicipios.includes("PL 22"));
assert.ok(resumoMunicipios.includes("Sem voto: 1,80%"));
assert.ok(resumoFaixas(base, "votos").includes("Sem voto: —"));

// Frases.
const BRASIL: Recorte = { tipo: "pais", codigo: "BR", nome: "Brasil" };
const NORDESTE: Recorte = { tipo: "regiao", codigo: "NE", nome: "Nordeste" };
const SAO_PAULO: Recorte = { tipo: "uf", codigo: "SP", nome: "São Paulo" };
const esperadas = (nome: string) => [
  `PL 22 teve 10,00% dos votos válidos no recorte ${nome}.`,
  "Os 558 municípios onde é mais forte deram 31,30% dos votos dele. Eles têm 7,30% do eleitorado.",
  "Teve pelo menos 5% dos votos em 4.000 de 5.571 municípios (71,80%).",
  "Índice de concentração: 50 de 100. Nenhuma regra de concentração se aplicou.",
];
assert.deepEqual(leituraCapilaridade(base, BRASIL, 27), esperadas("Brasil"));
assert.deepEqual(leituraCapilaridade(base, NORDESTE, 9), esperadas("Nordeste"));
assert.deepEqual(leituraCapilaridade(base, SAO_PAULO, 1), esperadas("São Paulo"));
const doze = partido(55, 40, "regional", "Regional (Sul)", { ufs_com_voto: 12 });
assert.equal(
  leituraCapilaridade(doze, BRASIL, 27)[0],
  "PSD 55 teve 10,00% dos votos válidos no recorte Brasil, contando só as 12 UFs onde recebeu voto.",
);
const estadual = partido(13, 30, "espalhado", "Nacional / espalhado", { ufs_com_voto: 26 });
assert.equal(
  leituraCapilaridade(estadual, BRASIL, 26)[0],
  "PT 13 teve 10,00% dos votos válidos no recorte Brasil.",
);

console.log("ok");
