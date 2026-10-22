import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

import { MEDIDAS_ESTREITO, layoutBarras } from "./grafico-poder.ts";
import { larguraTexto } from "./largura-texto.ts";
import {
  MEDIDAS_MUNICIPAIS,
  RespostaMunicipaisInvalidaError,
  formatarCorte,
  itensEleitorado,
  itensPrefeituras,
  itensVereadores,
  leituraMunicipais,
  lerMunicipais2024,
  rotuloBarra,
  rotuloComEquivalencia,
  type PartidoMunicipal,
  type RelatorioMunicipais,
} from "./municipais-2024.ts";

// JSON de exemplo do contrato (Task 11), com um município por UF.
const exemplo = {
  ano: 2024,
  uf: null,
  data_corte: "2026-10-22T02:17:00",
  importado_em: "2026-10-22T13:05:11.120000+00:00",
  equivalencia_versao: "2026-10-22",
  totais: {
    municipios: 5569, com_prefeito: 5568, sem_prefeito: 1, suplementares: 47,
    eleitorado: 155912680, vereadores: 58435, vagas_vereador: 58435, divergencias_vagas: 0,
  },
  partidos: [
    {
      numero: 55, sigla_2024: "PSD", numero_2026: 55, sigla_2026: "PSD",
      equivalencia: "mesmo", nota: "",
      prefeitos: 887, eleitorado_governado: 12345678,
      vereadores: 6600, municipios_com_vereador: 3100,
    },
  ],
  municipios: [
    {
      uf: "MG", codigo_tse: "45616", nome: "GUAPÉ", eleitorado: 12000,
      prefeito: {
        numero_partido: 22, sigla_2024: "PL", sigla_2026: "PL", nome_urna: "DR PEDRO",
        turno: 1, suplementar: true, data_eleicao: "2025-07-06",
      },
      vereadores: [{ numero: 22, sigla_2024: "PL", eleitos: 4 }],
    },
    { uf: "MG", codigo_tse: "48313", nome: "MERCÊS", eleitorado: 9000, prefeito: null, vereadores: [] },
  ],
  notas: ["..."],
};

// leitura do JSON válido
const lido = lerMunicipais2024(exemplo);
assert.equal(lido.ano, 2024);
assert.equal(lido.uf, null);
assert.equal(lido.totais.eleitorado, 155912680);
assert.equal(lido.partidos[0]!.sigla_2026, "PSD");
assert.equal(lido.municipios[0]!.prefeito!.nome_urna, "DR PEDRO");
assert.equal(lido.municipios[0]!.prefeito!.suplementar, true);
assert.equal(lido.municipios[1]!.prefeito, null);
assert.deepEqual(lido.municipios[0]!.vereadores, [{ numero: 22, sigla_2024: "PL", eleitos: 4 }]);
assert.deepEqual(lido.notas, ["..."]);
assert.equal(lerMunicipais2024({ ...exemplo, uf: "MG" }).uf, "MG");
assert.equal(
  lerMunicipais2024({ ...exemplo, partidos: [{ ...exemplo.partidos[0], numero_2026: null, sigla_2026: null }] })
    .partidos[0]!.numero_2026,
  null,
);

// JSON inválido
function invalido(valor: unknown): void {
  assert.throws(
    () => lerMunicipais2024(valor),
    (erro: unknown) =>
      erro instanceof RespostaMunicipaisInvalidaError &&
      erro instanceof Error &&
      erro.message === "A API devolveu um JSON que não confere com o relatório.",
  );
}
invalido({ ...exemplo, partidos: [{ ...exemplo.partidos[0], prefeitos: "1" }] });
invalido({ ...exemplo, totais: { ...exemplo.totais, eleitorado: -1 } });
invalido({ ...exemplo, municipios: [{ ...exemplo.municipios[0], prefeito: { suplementar: "sim" } }] });
invalido({ ...exemplo, notas: "..." });
invalido(null);
invalido([]);

// fábrica de relatórios para os gráficos e as frases
function partido(numero: number, sigla: string, prefeitos: number, extra: Partial<PartidoMunicipal> = {}): PartidoMunicipal {
  return {
    numero, sigla_2024: sigla, numero_2026: numero, sigla_2026: sigla, equivalencia: "mesmo", nota: "",
    prefeitos, eleitorado_governado: prefeitos * 1000, vereadores: prefeitos * 10, municipios_com_vereador: prefeitos,
    ...extra,
  };
}

function relatorio(partidos: PartidoMunicipal[], totais: Partial<RelatorioMunicipais["totais"]> = {}): RelatorioMunicipais {
  return {
    ...lido,
    partidos,
    totais: { ...lido.totais, ...totais },
  };
}

// 10 partidos → 8 maiores + "Outros", sempre por último; empate vai para o menor número
const dez = Array.from({ length: 10 }, (_, i) => partido(i + 10, `P${i + 10}`, 100 - i * 10));
dez.push(partido(9, "P9", 70));
const comOutros = itensPrefeituras(relatorio(dez, { com_prefeito: 1000 }));
assert.equal(comOutros.length, 9);
assert.deepEqual(
  comOutros.map((item) => item.chave),
  ["10", "11", "12", "9", "13", "14", "15", "16", "outros"],
);
assert.equal(comOutros[8]!.rotulo, "Outros");
assert.equal(comOutros[8]!.valor, 30 + 20 + 10);
assert.equal(comOutros[8]!.detalhe, "3 partidos, 60 prefeituras");
assert.equal(comOutros[0]!.texto, "10,00%");
assert.equal(comOutros[0]!.detalhe, "100 prefeituras");

// exatamente 10 partidos → 8 + "Outros" com os 2 menores
const exatos = itensPrefeituras(relatorio(dez.slice(0, 10)));
assert.equal(exatos.length, 9);
assert.equal(exatos[8]!.chave, "outros");
assert.equal(exatos[8]!.detalhe, "2 partidos, 30 prefeituras");

// 9 partidos → todos, sem "Outros"
const nove = dez.slice(0, 9);
assert.ok(!itensPrefeituras(relatorio(nove)).some((item) => item.chave === "outros"));
assert.equal(itensPrefeituras(relatorio(nove)).length, 9);

// partido zerado some (em cada gráfico pelo seu próprio valor)
const soVereador = partido(50, "PSOL", 0, { vereadores: 12 });
const mistos = relatorio([partido(55, "PSD", 3), soVereador], { com_prefeito: 3, eleitorado: 3000, vereadores: 42 });
assert.deepEqual(itensPrefeituras(mistos).map((item) => item.chave), ["55"]);
assert.deepEqual(itensEleitorado(mistos).map((item) => item.chave), ["55"]);
assert.deepEqual(itensVereadores(mistos).map((item) => item.chave), ["55", "50"]);
assert.equal(itensVereadores(mistos)[1]!.texto, "28,57%");
assert.equal(itensVereadores(mistos)[1]!.detalhe, "12 vereadores");
assert.equal(itensEleitorado(mistos)[0]!.texto, "100,00%");
assert.equal(itensEleitorado(mistos)[0]!.detalhe, "3.000 eleitores");

// PMB 35 → rótulo de 2024 e "Em 2026: DEMOCRATA" no detalhe
const pmb = partido(35, "PMB", 887, { numero_2026: 35, sigla_2026: "DEMOCRATA", equivalencia: "renomeado" });
assert.equal(rotuloBarra(pmb), "PMB 35");
assert.equal(rotuloComEquivalencia(pmb), "PMB 35 (em 2026: DEMOCRATA)");
assert.equal(rotuloComEquivalencia(partido(55, "PSD", 1)), "PSD 55");
const comPmb = relatorio([pmb], { com_prefeito: 5568 });
assert.equal(itensPrefeituras(comPmb)[0]!.rotulo, "PMB 35");
assert.equal(itensPrefeituras(comPmb)[0]!.detalhe, "887 prefeituras\nEm 2026: DEMOCRATA");
assert.ok(itensEleitorado(comPmb)[0]!.detalhe.endsWith("\nEm 2026: DEMOCRATA"));
assert.ok(itensVereadores(comPmb)[0]!.detalhe.endsWith("\nEm 2026: DEMOCRATA"));
assert.equal(itensPrefeituras(relatorio([partido(1, "X", 1)], { com_prefeito: 1 }))[0]!.detalhe, "1 prefeitura");

// barras: o rótulo mais longo de 2024 cabe na margem; a variante estreita existe
for (const rotulo of ["SOLIDARIEDADE 77", "REPUBLICANOS 10", "PC do B 65", "Outros"]) {
  assert.ok(larguraTexto(rotulo, MEDIDAS_MUNICIPAIS.fonte) + 8 <= MEDIDAS_MUNICIPAIS.esquerda, rotulo);
}
assert.ok(layoutBarras(comOutros, MEDIDAS_MUNICIPAIS) !== null);
assert.ok(layoutBarras(comOutros, MEDIDAS_ESTREITO) !== null);

// data de corte
assert.equal(formatarCorte("2026-10-22T02:17:00"), "22/10/2026 às 02:17");

// frases, plural
const psd = partido(55, "PSD", 887, { eleitorado_governado: 12345678 });
const frases = leituraMunicipais(
  relatorio([psd], { municipios: 5569, com_prefeito: 5568, sem_prefeito: 3, suplementares: 47, eleitorado: 155912680 }),
);
assert.deepEqual(frases, [
  "Até 22/10/2026 às 02:17, o TSE registra 5.568 prefeitos eleitos em 5.569 municípios.",
  "PSD tem mais prefeituras: 887 (15,93%), com 7,92% do eleitorado.",
  "3 municípios estão sem prefeito eleito.",
  "47 prefeitos vieram de eleição suplementar.",
]);

// frases, singular
assert.deepEqual(
  leituraMunicipais(relatorio([psd], { municipios: 5569, com_prefeito: 5568, sem_prefeito: 1, suplementares: 1 })).slice(2),
  ["1 município está sem prefeito eleito.", "1 prefeito veio de eleição suplementar."],
);

// sem sem_prefeito nem suplementares: só as duas primeiras
assert.equal(leituraMunicipais(relatorio([psd], { sem_prefeito: 0, suplementares: 0 })).length, 2);

// relatório sem partidos → uma frase só
assert.deepEqual(leituraMunicipais(relatorio([], { sem_prefeito: 0, suplementares: 0 })), [
  "Até 22/10/2026 às 02:17, o TSE registra 5.568 prefeitos eleitos em 5.569 municípios.",
]);

// D14: o módulo nunca usa os rótulos de 2026 de partidos.ts
const fonte = readFileSync(new URL("./municipais-2024.ts", import.meta.url), "utf8");
assert.ok(!fonte.includes("rotuloPartido"));
assert.ok(!fonte.includes("SIGLAS_PARTIDOS"));
const pagina = readFileSync(
  new URL("../components/relatorios/dados-municipais-2024.tsx", import.meta.url),
  "utf8",
);
assert.ok(!pagina.includes("rotuloPartido"));
assert.ok(!pagina.includes("SIGLAS_PARTIDOS"));

console.log("ok");
