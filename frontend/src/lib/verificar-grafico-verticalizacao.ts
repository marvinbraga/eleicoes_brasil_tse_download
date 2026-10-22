import assert from "node:assert/strict";
import {
  corFatia,
  corR,
  faixaFatia,
  faixaR,
  formatarR,
  formatarRazao,
  frasesVerticalizacao,
  layoutDispersao,
  LIMITES_FATIA,
  LIMITES_R,
  matrizCoerencia,
  matrizFatias,
  MEDIDAS_COERENCIA_ESTREITO,
  MEDIDAS_DISPERSAO,
  MEDIDAS_DISPERSAO_ESTREITO,
  MEDIDAS_MATRIZ,
  MEDIDAS_MATRIZ_ESTREITO,
  resumoMatriz,
} from "./grafico-verticalizacao.ts";
import { larguraTexto } from "./largura-texto.ts";
import {
  CARGOS_VERTICAIS,
  lerDecimal,
  lerVerticalizacao,
  type CargoVertical,
  type CargoVerticalDados,
  type Classe,
  type Comparacao,
  type Coerencia,
  type PartidoVertical,
  type RelatorioVerticalizacao,
} from "./verticalizacao.ts";

// faixas: bordas contam para a faixa de cima
assert.deepEqual(LIMITES_FATIA, [0.05, 0.1, 0.2, 0.35]);
assert.deepEqual(LIMITES_R, [0.2, 0.4, 0.6, 0.8]);
assert.equal(faixaFatia(0.05), 1);
assert.equal(faixaFatia(0.0499), 0);
assert.equal(faixaFatia(0.35), 4);
assert.equal(faixaFatia(0), 0);
assert.equal(faixaFatia(null), null);
assert.equal(faixaR(0.2), 1);
assert.equal(faixaR(-0.2), -1);
assert.equal(faixaR(0.19), 0);
assert.equal(faixaR(-0.19), 0);
assert.equal(faixaR(0.8), 4);
assert.equal(faixaR(-1), -4);
assert.equal(faixaR(null), null);
assert.deepEqual(corFatia(2), { fundo: "var(--vz-seq-2)", tinta: "var(--vz-seq-tinta-2)" });
assert.deepEqual(corR(-3), { fundo: "var(--vz-div-n3)", tinta: "var(--vz-div-tinta-n3)" });
assert.deepEqual(corR(0), { fundo: "var(--vz-div-0)", tinta: "var(--vz-div-tinta-0)" });
assert.deepEqual(corR(4), { fundo: "var(--vz-div-p4)", tinta: "var(--vz-div-tinta-p4)" });

// leitura de decimais com vírgula
assert.equal(lerDecimal("0,6213"), 0.6213);
assert.equal(lerDecimal("-0,1200"), -0.12);
assert.equal(lerDecimal("1.234,5000"), 1234.5);
assert.equal(lerDecimal(null), null);
assert.equal(lerDecimal("abc"), null);

type CargoParcial = Partial<CargoVerticalDados>;

function cargo(nome: CargoVertical, parcial: CargoParcial = {}): CargoVerticalDados {
  return {
    cargo: nome,
    votos: 100,
    validos: 1000,
    validos_onde: 800,
    fatia: "10,00%",
    fatia_onde: "12,50%",
    ufs_concorreu: 20,
    ufs_total: 27,
    ...parcial,
  };
}

const PARES: [CargoVertical, CargoVertical][] = [
  ["deputadoFederal", "presidente"],
  ["deputadoEstadual", "presidente"],
  ["deputadoFederal", "governador"],
  ["deputadoEstadual", "governador"],
  ["deputadoFederal", "senador"],
  ["deputadoEstadual", "senador"],
  ["deputadoFederal", "deputadoEstadual"],
];

function coerencias(rs: (string | null)[], municipios: number[] = []): Coerencia[] {
  return PARES.map(([x, y], indice) => ({
    cargo_x: x,
    cargo_y: y,
    r: rs[indice] ?? null,
    municipios: municipios[indice] ?? 1830,
  }));
}

const CANONICOS: [CargoVertical, CargoVertical][] = [
  ["governador", "deputadoEstadual"],
  ["senador", "deputadoFederal"],
  ["presidente", "deputadoFederal"],
];

function comparacoes(parciais: Partial<Comparacao>[] = []): Comparacao[] {
  return CANONICOS.map(([majoritario, proporcional], indice) => ({
    majoritario,
    proporcional,
    majoritaria: "20,00%",
    esperada: "18,00%",
    razao: "1,1111",
    classe: "alinhado" as Classe,
    por_uf: [],
    sem_candidato: [],
    ...(parciais[indice] ?? {}),
  }));
}

function partido(
  numero: number,
  parcial: {
    cargos?: Partial<Record<CargoVertical, CargoParcial>>;
    coerencia?: Coerencia[];
    comparacoes?: Comparacao[];
  } = {},
): PartidoVertical {
  return {
    partido: numero,
    perfil: "alinhado",
    coerencia_mediana: null,
    cargos: CARGOS_VERTICAIS.map((nome) => cargo(nome, parcial.cargos?.[nome])),
    coerencia: parcial.coerencia ?? coerencias(["0,5000"]),
    comparacoes: parcial.comparacoes ?? comparacoes(),
  };
}

const pl = partido(22, {
  cargos: {
    presidente: { fatia_onde: "41,05%", fatia: "26,97%", ufs_concorreu: 9, ufs_total: 27 },
    governador: { fatia_onde: null, fatia: "0,00%", votos: 0, validos_onde: 0, ufs_concorreu: 0 },
    deputadoEstadual: { fatia_onde: null, fatia: null, validos: 0, ufs_concorreu: 0, ufs_total: 0 },
  },
  coerencia: coerencias(
    ["0,6213", "-0,1500", null, null, "-0,0012", "0,8000", "0,7000"],
    [1830, 1830, 5, 50, 1830, 1830, 1830],
  ),
  comparacoes: comparacoes([
    { majoritaria: "41,00%", esperada: "15,20%", razao: "2,6974", classe: "puxador" },
  ]),
});
const pt = partido(13, {
  comparacoes: comparacoes([
    {},
    { majoritaria: "12,00%", esperada: "0,00%", razao: null, classe: "puxador" },
  ]),
});
const republicanos = partido(10, {
  comparacoes: comparacoes([
    {},
    {},
    { majoritaria: "31,00%", esperada: "10,00%", razao: "3,1000", classe: "puxador" },
  ]),
});
const psd = partido(55, {
  comparacoes: comparacoes([
    { majoritaria: "21,00%", esperada: "10,00%", razao: "2,1000", classe: "puxador" },
  ]),
});
const mdb = partido(15, {
  comparacoes: comparacoes([
    { majoritaria: "6,00%", esperada: "20,00%", razao: "0,3000", classe: "base" },
  ]),
});
const psdb = partido(45, {
  comparacoes: comparacoes([
    {
      majoritaria: null,
      esperada: null,
      razao: null,
      classe: "sem_candidato",
      sem_candidato: [
        { uf: "SP", proporcional: "7,10%" },
        { uf: "BA", proporcional: "4,99%" },
      ],
    },
  ]),
});
const psol = partido(50, {
  comparacoes: comparacoes([
    {},
    {},
    {
      majoritaria: null,
      esperada: null,
      razao: null,
      classe: "sem_candidato",
      sem_candidato: [
        { uf: "RJ", proporcional: "6,00%" },
        { uf: "MG", proporcional: "5,00%" },
        { uf: "AC", proporcional: "1,00%" },
      ],
    },
  ]),
});
const solidariedade = partido(77, {
  cargos: { senador: { ufs_concorreu: 1, ufs_total: 1 }, governador: { ufs_concorreu: 0, ufs_total: 1, fatia_onde: null } },
});

const dados: RelatorioVerticalizacao = {
  ano: 2026,
  turno: 1,
  uf: null,
  municipios: 5570,
  sem_uf: 0,
  cargos: [...CARGOS_VERTICAIS],
  limiares: { razao: "2", diferenca: "10,00%", base_relevante: "5,00%", minimo_municipios: 10 },
  partidos: [pl, pt, republicanos, psd, mdb, psdb, psol, solidariedade],
  dispersao: {
    partido: 22,
    cargo_x: "deputadoFederal",
    cargo_y: "governador",
    coerencia: { cargo_x: "deputadoFederal", cargo_y: "governador", r: "0,6213", municipios: 1830 },
    pontos: [
      { codigo: "1", nome: "PEQUENA (AC)", uf: "AC", comparecimento: 100, x: "12,30%", y: "40,10%" },
      { codigo: "2", nome: "GRANDE (SP)", uf: "SP", comparecimento: 210000, x: "22,00%", y: "8,00%" },
      { codigo: "3", nome: "MEDIA (MG)", uf: "MG", comparecimento: 52500, x: "5,00%", y: "30,00%" },
    ],
  },
  notas: ["Nota."],
};

// a leitura do JSON aceita o próprio formato e recusa campos errados
assert.deepEqual(lerVerticalizacao(JSON.parse(JSON.stringify(dados))), dados);
assert.throws(() => lerVerticalizacao({ ...dados, cargos: ["vereador"] }));
assert.throws(() =>
  lerVerticalizacao({ ...dados, partidos: [{ ...pl, perfil: "outro" }] }),
);

// matriz de fatias
const fatias = matrizFatias(dados);
assert.ok(fatias !== null);
assert.equal(fatias.colunas.length, 5);
assert.equal(fatias.linhas.length, 8);
assert.equal(fatias.altura, MEDIDAS_MATRIZ.topo + 8 * MEDIDAS_MATRIZ.alturaLinha);
assert.deepEqual(
  fatias.colunas.map((coluna) => coluna.linhas),
  [["Presidente"], ["Governador"], ["Senador"], ["Dep. federal"], ["Dep. estadual"]],
);
const celula = (layout: NonNullable<typeof fatias>, chave: string) => {
  const achada = layout.celulas.find((item) => item.chave === chave);
  assert.ok(achada !== undefined, chave);
  return achada;
};
const presidentePl = celula(fatias, "22-presidente");
assert.equal(presidentePl.texto, "41,1");
assert.equal(presidentePl.faixa, 4);
assert.equal(presidentePl.dicaTitulo, "PL 22 · Presidente");
assert.deepEqual(presidentePl.dicaLinhas, [
  "Onde concorreu: 41,05%",
  "No recorte todo: 26,97%",
  "Concorreu em 9 de 27 UFs",
]);
const governadorPl = celula(fatias, "22-governador");
assert.equal(governadorPl.texto, "—");
assert.equal(governadorPl.faixa, null);
assert.equal(governadorPl.semEleicao, false);
assert.deepEqual(governadorPl.dicaLinhas, ["Não concorreu em nenhuma das 27 UFs"]);
const estadualPl = celula(fatias, "22-deputadoEstadual");
assert.equal(estadualPl.texto, "n/a");
assert.equal(estadualPl.faixa, null);
assert.equal(estadualPl.semEleicao, true);
assert.deepEqual(estadualPl.dicaLinhas, ["Sem eleição gravada para este cargo no recorte"]);
assert.equal(celula(fatias, "13-senador").texto, "12,5");
assert.equal(celula(fatias, "13-senador").faixa, 2);
assert.deepEqual(celula(fatias, "77-senador").dicaLinhas.at(-1), "Concorreu na UF");
assert.deepEqual(celula(fatias, "77-governador").dicaLinhas, ["Não concorreu na UF"]);
assert.equal(fatias.linhas[0].rotulo, "PL 22");
for (const item of fatias.celulas) {
  assert.ok(item.x >= MEDIDAS_MATRIZ.esquerda);
  assert.ok(item.x + item.largura <= MEDIDAS_MATRIZ.largura + 0.001);
}

// variante estreita: cabe em 340 px e nenhum rótulo passa da margem
for (const medidas of [MEDIDAS_MATRIZ_ESTREITO, MEDIDAS_COERENCIA_ESTREITO]) {
  assert.ok(medidas.largura <= 340);
}
const estreita = matrizFatias(dados, MEDIDAS_MATRIZ_ESTREITO);
assert.ok(estreita !== null);
assert.ok(estreita.largura <= 340);
assert.deepEqual(
  estreita.linhas.map((linha) => linha.rotulo),
  ["PL", "PT", "REPUBLICA…", "PSD", "MDB", "PSDB", "PSOL", "SOLIDARIE…"],
);
assert.equal(estreita.linhas[2].nome, "REPUBLICANOS 10");
for (const linha of estreita.linhas) {
  assert.ok(larguraTexto(linha.rotulo, MEDIDAS_MATRIZ_ESTREITO.fonte) <= MEDIDAS_MATRIZ_ESTREITO.esquerda - 6);
}
assert.deepEqual(estreita.colunas.map((coluna) => coluna.linhas), [["Pres."], ["Gov."], ["Sen."], ["Fed."], ["Est."]]);
for (const layout of [estreita]) {
  const largura = layout.celulas[0].largura;
  for (const coluna of layout.colunas) {
    for (const texto of coluna.linhas) {
      assert.ok(larguraTexto(texto, layout.medidas.fonteCabeca) <= largura + layout.medidas.vao);
    }
  }
}

// matriz de coerência: 7 colunas, a referência com vão extra e "Ref."
const coerencia = matrizCoerencia(dados);
assert.ok(coerencia !== null);
assert.equal(coerencia.colunas.length, 7);
assert.equal(coerencia.colunas[0].rotulo, "Fed.×Pres.");
assert.equal(coerencia.colunas[6].rotulo, "Fed.×Est.");
assert.equal(coerencia.colunas[6].referencia, true);
assert.equal(coerencia.colunas[5].referencia, false);
const passo = coerencia.colunas[1].x - coerencia.colunas[0].x;
assert.ok(Math.abs(coerencia.colunas[6].x - coerencia.colunas[5].x - (passo + 8)) < 0.001);
assert.ok(Math.abs(coerencia.colunas[5].x - coerencia.colunas[4].x - passo) < 0.001);
const forte = celula(coerencia, "22-deputadoFederal-presidente");
assert.equal(forte.texto, "0,62");
assert.equal(forte.faixa, 3);
assert.equal(forte.dicaTitulo, "PL 22 · Dep. federal × Presidente");
assert.deepEqual(forte.dicaLinhas, ["r = 0,6213", "1.830 municípios"]);
const negativa = celula(coerencia, "22-deputadoEstadual-presidente");
assert.equal(negativa.texto, "−0,15");
assert.equal(negativa.faixa, 0);
assert.equal(celula(coerencia, "22-deputadoFederal-senador").texto, "0,00");
assert.equal(celula(coerencia, "22-deputadoEstadual-senador").faixa, 4);
const pouca = celula(coerencia, "22-deputadoFederal-governador");
assert.equal(pouca.texto, "—");
assert.equal(pouca.faixa, null);
assert.deepEqual(pouca.dicaLinhas, ["Menos de 10 municípios para medir", "5 municípios"]);
const plana = celula(coerencia, "22-deputadoEstadual-governador");
assert.deepEqual(plana.dicaLinhas, ["Sem variação para medir", "50 municípios"]);
for (const item of coerencia.celulas) {
  assert.ok(item.x + item.largura <= MEDIDAS_MATRIZ.largura + 0.001);
}
const coerenciaEstreita = matrizCoerencia(dados, MEDIDAS_COERENCIA_ESTREITO);
assert.ok(coerenciaEstreita !== null);
assert.ok(coerenciaEstreita.largura <= 340);
const larguraCelula = coerenciaEstreita.celulas[0].largura;
for (const item of coerenciaEstreita.celulas) {
  assert.ok(larguraTexto(item.texto, MEDIDAS_COERENCIA_ESTREITO.fonte) <= larguraCelula, item.texto);
}
for (const coluna of coerenciaEstreita.colunas) {
  for (const texto of coluna.linhas) {
    assert.ok(larguraTexto(texto, MEDIDAS_COERENCIA_ESTREITO.fonteCabeca) <= larguraCelula + MEDIDAS_COERENCIA_ESTREITO.vao, texto);
  }
}
assert.equal(matrizFatias({ ...dados, partidos: [] }), null);
assert.equal(matrizCoerencia({ ...dados, partidos: [] }), null);

// <desc>: todos os valores, linha por linha
const resumo = resumoMatriz(fatias);
for (const item of fatias.celulas) {
  assert.ok(resumo.includes(item.texto));
}
assert.ok(resumo.startsWith("PL 22: Presidente 41,1; Governador —; Senador 12,5; Dep. federal 12,5; Dep. estadual n/a."));
assert.ok(resumoMatriz(coerencia).includes("Dep. federal × Dep. estadual 0,70"));

// dispersão
const dispersao = layoutDispersao(dados);
assert.ok(dispersao !== null);
assert.deepEqual(dispersao.marcasX.map((marca) => marca.texto), ["0%", "10%", "20%", "30%"]);
assert.deepEqual(dispersao.marcasY.map((marca) => marca.texto), ["0%", "20%", "40%", "60%"]);
const { esquerda, direita, topo, base, largura, altura } = MEDIDAS_DISPERSAO;
assert.equal(dispersao.marcasX[0].x, esquerda);
assert.equal(dispersao.marcasX.at(-1)?.x, largura - direita);
assert.equal(dispersao.marcasY[0].y, altura - base);
assert.equal(dispersao.marcasY.at(-1)?.y, topo);
// diagonal recortada no menor teto (30% no x, 60% no y)
assert.ok(dispersao.diagonal !== null);
assert.equal(dispersao.diagonal.x1, esquerda);
assert.equal(dispersao.diagonal.y1, altura - base);
assert.equal(dispersao.diagonal.x2, largura - direita);
assert.ok(Math.abs(dispersao.diagonal.y2 - ((altura - base) - (0.3 / 0.6) * (altura - base - topo))) < 0.001);
// ordem por raio decrescente: os pequenos ficam por cima
assert.deepEqual(dispersao.pontos.map((ponto) => ponto.chave), ["2", "3", "1"]);
assert.equal(dispersao.pontos[0].raio, MEDIDAS_DISPERSAO.raioMax);
assert.ok(Math.abs(dispersao.pontos[1].raio - (1.5 + 6.5 * 0.5)) < 0.001);
assert.equal(dispersao.pontos[2].dicaTitulo, "PEQUENA (AC)");
assert.deepEqual(dispersao.pontos[0].dicaLinhas, ["Dep. federal: 22,00%", "Governador: 8,00%", "Comparecimento: 210.000"]);
assert.equal(dispersao.rotuloX, "Dep. federal (% dos válidos)");
assert.equal(dispersao.rotuloY, "Governador (% dos válidos)");
const estreitaDispersao = layoutDispersao(dados, MEDIDAS_DISPERSAO_ESTREITO);
assert.ok(estreitaDispersao !== null);
assert.ok(estreitaDispersao.medidas.largura <= 340);
assert.ok(larguraTexto(estreitaDispersao.rotuloX, MEDIDAS_DISPERSAO_ESTREITO.fonte) <= 340);
for (const ponto of estreitaDispersao.pontos) {
  assert.ok(ponto.raio <= MEDIDAS_DISPERSAO_ESTREITO.raioMax);
}
assert.equal(layoutDispersao({ ...dados, dispersao: { ...dados.dispersao, pontos: [] } }), null);
// teto mínimo de 5% e diagonal até o menor dos tetos
const baixa = layoutDispersao({
  ...dados,
  dispersao: { ...dados.dispersao, pontos: [{ codigo: "9", nome: "ZERO (AC)", uf: "AC", comparecimento: 0, x: "0,00%", y: "0,00%" }] },
});
assert.ok(baixa !== null);
assert.deepEqual(baixa.marcasX.map((marca) => marca.texto), ["0%", "5%"]);
assert.equal(baixa.pontos[0].raio, MEDIDAS_DISPERSAO.raioMin);
const cheia = layoutDispersao({
  ...dados,
  dispersao: { ...dados.dispersao, pontos: [{ codigo: "9", nome: "TUDO (AC)", uf: "AC", comparecimento: 10, x: "100,00%", y: "23,00%" }] },
});
assert.ok(cheia !== null);
assert.deepEqual(cheia.marcasX.map((marca) => marca.texto), ["0%", "25%", "50%", "75%", "100%"]);
assert.deepEqual(cheia.marcasY.map((marca) => marca.texto), ["0%", "10%", "20%", "30%"]);

// frases
assert.deepEqual(frasesVerticalizacao(dados), [
  "Dentro de cada UF, onde o PL 22 vai melhor para deputado federal ele também vai melhor para governador? A coerência é forte (r = 0,62, 1.830 municípios).",
  "PT 13 puxa em senador: teve 12,00% onde concorreu sem base em deputado federal.",
  "REPUBLICANOS 10 puxa em presidente: teve 31,00% onde concorreu, 3,1 vezes o esperado pela força em deputado federal (10,00%).",
  "PL 22 puxa em governador: teve 41,00% onde concorreu, 2,7 vezes o esperado pela força em deputado estadual (15,20%).",
  "MDB 15 tem base sem cabeça de chapa forte em governador: a força em deputado estadual indicaria 20,00%, e veio 6,00%.",
  "PSOL 50 não lançou presidente em 2 UFs onde tem 5,00% ou mais em deputado federal (RJ, MG). Pode ter apoiado um aliado; isso não conta como fraqueza.",
  "PSDB 45 não lançou governador em 1 UF onde tem 5,00% ou mais em deputado estadual (SP). Pode ter apoiado um aliado; isso não conta como fraqueza.",
  "Mais 1 caso na tabela.",
]);

const comDispersao = (coerenciaPar: Coerencia, uf: string | null = null): string =>
  frasesVerticalizacao({
    ...dados,
    uf,
    partidos: [],
    dispersao: { ...dados.dispersao, partido: 13, cargo_x: "deputadoEstadual", cargo_y: "senador", coerencia: coerenciaPar },
  })[0];
assert.equal(
  comDispersao({ cargo_x: "deputadoEstadual", cargo_y: "senador", r: "-0,4500", municipios: 645 }, "SP"),
  "Em São Paulo, onde o PT 13 vai melhor para deputado estadual ele também vai melhor para senador? A coerência é moderada e inversa (r = −0,45, 645 municípios).",
);
assert.equal(
  comDispersao({ cargo_x: "deputadoEstadual", cargo_y: "senador", r: "0,1000", municipios: 30 }),
  "Dentro de cada UF, onde o PT 13 vai melhor para deputado estadual ele também vai melhor para senador? A coerência é fraca (r = 0,10, 30 municípios).",
);
assert.equal(
  comDispersao({ cargo_x: "deputadoEstadual", cargo_y: "senador", r: null, municipios: 9 }),
  "Não há municípios suficientes para medir a coerência do PT 13 entre deputado estadual e senador.",
);
assert.equal(
  comDispersao({ cargo_x: "deputadoEstadual", cargo_y: "senador", r: null, municipios: 40 }),
  "Não há variação suficiente para medir a coerência do PT 13 entre deputado estadual e senador.",
);
// sem casos além dos mostrados, nenhuma frase de "Mais"
const poucos = frasesVerticalizacao({ ...dados, partidos: [pl, mdb] });
assert.equal(poucos.length, 3);
assert.ok(!poucos.some((frase) => frase.startsWith("Mais")));
const doisMais = frasesVerticalizacao({ ...dados, partidos: [pl, pt, republicanos, psd, partido(20, { comparacoes: comparacoes([{ razao: "2,0000", classe: "puxador" }]) })] });
assert.equal(doisMais.at(-1), "Mais 2 casos na tabela.");

assert.equal(formatarRazao("2,6974"), "2,7");
assert.equal(formatarRazao("1.234,5600"), "1.234,6");
assert.equal(formatarRazao(null), "—");
assert.equal(formatarR("-0,0049"), "0,00");
assert.equal(formatarR("-0,0050"), "\u22120,01");
assert.equal(formatarR("1,0000"), "1,00");

// força, sentido e faixa seguem o r arredondado que o leitor vê
assert.equal(
  comDispersao({ cargo_x: "deputadoEstadual", cargo_y: "senador", r: "0,2996", municipios: 30 }),
  "Dentro de cada UF, onde o PT 13 vai melhor para deputado estadual ele também vai melhor para senador? A coerência é moderada (r = 0,30, 30 municípios).",
);
assert.equal(
  comDispersao({ cargo_x: "deputadoEstadual", cargo_y: "senador", r: "-0,0012", municipios: 30 }),
  "Dentro de cada UF, onde o PT 13 vai melhor para deputado estadual ele também vai melhor para senador? A coerência é fraca (r = 0,00, 30 municípios).",
);
const borda = matrizCoerencia({ ...dados, partidos: [partido(13, { coerencia: coerencias(["0,1996"]) })] });
assert.ok(borda !== null);
assert.equal(borda.celulas[0].texto, "0,20");
assert.equal(borda.celulas[0].faixa, 1);
assert.ok(resumo.endsWith("Valores em %."));
// a leitura recusa cargos fora de ordem ou listas incompletas
assert.throws(() =>
  lerVerticalizacao({ ...dados, partidos: [{ ...pl, cargos: [...pl.cargos].reverse() }] }),
);
assert.throws(() =>
  lerVerticalizacao({ ...dados, partidos: [{ ...pl, coerencia: pl.coerencia.slice(1) }] }),
);

console.log("ok");
