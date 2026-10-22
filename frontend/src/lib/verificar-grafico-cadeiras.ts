import assert from "node:assert/strict";
import {
  MEDIDAS_CADEIRAS,
  frasesCadeiras,
  itensCasa,
  itensSenado,
  rotuloCabe,
  rotuloFase,
  rotuloLegenda,
  rotuloSituacao,
} from "./grafico-cadeiras.ts";
import { MEDIDAS_ESTREITO, layoutBarras } from "./grafico-poder.ts";
import type { SimulacaoCadeiras } from "./relatorios.ts";

const legendas = [
  { codigo: "fe-brasil", sigla: "FE BRASIL", nome: "Federação Brasil da Esperança", federacao: true, partidos: [13, 65, 43] },
  { codigo: "renovacao-solidaria", sigla: "RENOVAÇÃO SOLIDÁRIA", nome: "Federação Renovação Solidária", federacao: true, partidos: [25, 77] },
  { codigo: "uniao-progressista", sigla: "UNIÃO PROGRESSISTA", nome: "Federação União Progressista", federacao: true, partidos: [44, 11] },
  { codigo: "22", sigla: "22", nome: "Partido 22", federacao: false, partidos: [22] },
];

function casa(nome: string, sem: string[] = []): SimulacaoCadeiras["casas"][number] {
  return {
    casa: nome === "Câmara dos Deputados" ? "camara" : "assembleias",
    nome,
    vagas: 513,
    vagas_simuladas: sem.length > 0 ? 505 : 513,
    ufs_sem_votos: sem,
    legendas: [
      { legenda: "22", cadeiras: 90 },
      { legenda: "fe-brasil", cadeiras: 90 },
      { legenda: "renovacao-solidaria", cadeiras: 0 },
    ],
    partidos: [{ partido: 22, cadeiras: 90 }, { partido: 13, cadeiras: 80 }, { partido: 65, cadeiras: 10 }],
    ufs: [{
      uf: "AC", cargo: "deputadoFederal", vagas: 8, votos_validos: 800, quociente_eleitoral: 100,
      vagas_sem_candidato: 0, listas: [],
      eleitos: [{ numero: 1301, partido: 13, legenda: "fe-brasil", votos: 250, fase: "quociente", empate: true }],
    }],
  };
}

const simulacao: SimulacaoCadeiras = {
  ano: 2026, turno: 1, gerado_em: "2026-10-22T00:00:00+00:00", estimativa: true, legendas,
  casas: [casa("Câmara dos Deputados", ["AC"])],
  senado: { vagas: 54, vagas_simuladas: 2, ufs_sem_votos: [], partidos: [{ partido: 22, cadeiras: 2 }, { partido: 13, cadeiras: 0 }],
    ufs: [{ uf: "AC", votos_validos: 10, eleitos: [], empate: false }] },
  governo: { ufs_sem_votos: [], partidos: [], ufs: [
    { uf: "AC", situacao: "segundo_turno", votos_validos: 10, candidatos: [], empate: false },
    { uf: "SE", situacao: "eleito", votos_validos: 10, candidatos: [], empate: false },
    { uf: "SP", situacao: "eleito", votos_validos: 10, candidatos: [], empate: true },
  ] },
  partidos: [], descartados: 0, notas: [],
};

// rótulos
assert.equal(rotuloLegenda("fe-brasil", legendas), "FE BRASIL");
assert.equal(rotuloLegenda("22", legendas), "PL 22");
assert.equal(rotuloLegenda("xx", legendas), "xx");
assert.equal(rotuloFase("media_livre"), "Média (todas as legendas)");
assert.equal(rotuloSituacao("segundo_turno"), "2º turno");
for (const legenda of legendas) {
  assert.ok(rotuloCabe(rotuloLegenda(legenda.codigo, legendas)), legenda.codigo);
}
assert.equal(rotuloCabe("X".repeat(30)), false);

// itens: sem zeros, ordenados por cadeiras e depois por rótulo; federação detalha os membros
const itens = itensCasa(simulacao.casas[0]!, legendas);
assert.deepEqual(itens.map((item) => item.rotulo), ["FE BRASIL", "PL 22"]);
assert.equal(itens[0]!.detalhe, "90 de 505 vagas simuladas\nPT 13: 80\nPCdoB 65: 10\nPV 43: 0");
assert.equal(itens[1]!.detalhe, "90 de 505 vagas simuladas");
assert.deepEqual(itensSenado(simulacao).map((item) => [item.rotulo, item.texto]), [["PL 22", "2"]]);

// layout com a margem própria e na tela estreita
const layout = layoutBarras(itens, MEDIDAS_CADEIRAS)!;
assert.equal(layout.barras[0]!.largura, 640 - 152 - 72);
assert.ok(layoutBarras(itens, MEDIDAS_ESTREITO) !== null);
assert.equal(layoutBarras([], MEDIDAS_CADEIRAS), null);

// frases
assert.deepEqual(frasesCadeiras(simulacao), [
  "Câmara dos Deputados: empatam FE BRASIL e PL 22, com 90 cadeiras de 505.",
  "Câmara dos Deputados: faltam votos gravados de AC; 8 vagas ficaram fora da conta.",
  "Governador: 2 UFs elegeriam no 1º turno e 1 iria ao 2º turno.",
  "2 resultados dependem de um desempate que os boletins não resolvem (idade do candidato).",
]);
console.log("ok");
