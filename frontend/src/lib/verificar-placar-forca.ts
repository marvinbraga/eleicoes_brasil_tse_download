import assert from "node:assert/strict";
import { lerPlacarForca } from "./forca.ts";
import {
  COLUNA_PADRAO,
  GRUPOS_COLUNA,
  ROTULOS_GRUPO,
  colunasPlacar,
  linhasPlacar,
  linhasPorUf,
  LINKS_RELATORIOS,
  linksPartido,
  linksUnidade,
  recorteDoModo,
  ordenarPlacar,
  ROTULOS_ESFERA,
  temFederacoes,
  totaisPlacar,
  type LinhaPlacar,
} from "./placar-forca.ts";
import type { PlacarForca, RecorteForca, UnidadeForca } from "./forca.ts";

// Saída do domínio Python da Task 2 no formato de ForcaJson.
const PLACAR = lerPlacarForca(JSON.parse(String.raw`{"ano":2026,"turno":1,"cargo_referencia":"deputadoEstadual","limiares":[1,2,5,10,20],"faltando":[],"pais":{"codigo":"BR","nome":"Brasil","base":{"validos_presidente":100,"validos_deputado_federal":100,"validos_deputado_estadual":80,"ufs_deputado_estadual":2,"municipal":{"municipios":3,"validos":300,"empates":1}},"unidades":[{"chave":"13","tipo":"partido","nome":null,"partidos":[13],"presidente":60,"deputado_federal":30,"deputado_estadual":30,"ufs_lider_estadual":0,"municipal":{"lidera":1,"validos_liderados":100,"presenca":[{"limiar":1,"municipios":3},{"limiar":2,"municipios":3},{"limiar":5,"municipios":3},{"limiar":10,"municipios":2},{"limiar":20,"municipios":2}]}},{"chave":"22","tipo":"partido","nome":null,"partidos":[22],"presidente":40,"deputado_federal":50,"deputado_estadual":50,"ufs_lider_estadual":1,"municipal":{"lidera":1,"validos_liderados":100,"presenca":[{"limiar":1,"municipios":3},{"limiar":2,"municipios":3},{"limiar":5,"municipios":3},{"limiar":10,"municipios":3},{"limiar":20,"municipios":3}]}},{"chave":"65","tipo":"partido","nome":null,"partidos":[65],"presidente":null,"deputado_federal":20,"deputado_estadual":0,"ufs_lider_estadual":0,"municipal":{"lidera":0,"validos_liderados":0,"presenca":[{"limiar":1,"municipios":0},{"limiar":2,"municipios":0},{"limiar":5,"municipios":0},{"limiar":10,"municipios":0},{"limiar":20,"municipios":0}]}}]},"ufs":[{"codigo":"AC","nome":"Acre","base":{"validos_presidente":30,"validos_deputado_federal":10,"validos_deputado_estadual":40,"ufs_deputado_estadual":1,"municipal":{"municipios":2,"validos":200,"empates":0}},"unidades":[{"chave":"13","tipo":"partido","nome":null,"partidos":[13],"presidente":10,"deputado_federal":5,"deputado_estadual":10,"ufs_lider_estadual":0,"municipal":{"lidera":1,"validos_liderados":100,"presenca":[{"limiar":1,"municipios":2},{"limiar":2,"municipios":2},{"limiar":5,"municipios":2},{"limiar":10,"municipios":1},{"limiar":20,"municipios":1}]}},{"chave":"22","tipo":"partido","nome":null,"partidos":[22],"presidente":20,"deputado_federal":5,"deputado_estadual":30,"ufs_lider_estadual":1,"municipal":{"lidera":1,"validos_liderados":100,"presenca":[{"limiar":1,"municipios":2},{"limiar":2,"municipios":2},{"limiar":5,"municipios":2},{"limiar":10,"municipios":2},{"limiar":20,"municipios":2}]}}]},{"codigo":"AM","nome":"Amazonas","base":{"validos_presidente":null,"validos_deputado_federal":10,"validos_deputado_estadual":40,"ufs_deputado_estadual":1,"municipal":{"municipios":1,"validos":100,"empates":1}},"unidades":[{"chave":"13","tipo":"partido","nome":null,"partidos":[13],"presidente":null,"deputado_federal":7,"deputado_estadual":20,"ufs_lider_estadual":0,"municipal":{"lidera":0,"validos_liderados":0,"presenca":[{"limiar":1,"municipios":1},{"limiar":2,"municipios":1},{"limiar":5,"municipios":1},{"limiar":10,"municipios":1},{"limiar":20,"municipios":1}]}},{"chave":"22","tipo":"partido","nome":null,"partidos":[22],"presidente":null,"deputado_federal":3,"deputado_estadual":20,"ufs_lider_estadual":0,"municipal":{"lidera":0,"validos_liderados":0,"presenca":[{"limiar":1,"municipios":1},{"limiar":2,"municipios":1},{"limiar":5,"municipios":1},{"limiar":10,"municipios":1},{"limiar":20,"municipios":1}]}}]}]}`));

function porChave(linhas: readonly LinhaPlacar[], chave: string): LinhaPlacar {
  const linha = linhas.find((item) => item.chave === chave);
  assert.ok(linha, `linha ${chave} ausente`);
  return linha;
}

assert.equal(COLUNA_PADRAO, "deputado_federal");
assert.deepEqual(ROTULOS_ESFERA, { nacional: "Nacional", estados: "Estados", municipios: "Municípios" });

// colunas: sete, na ordem das esferas, com o limiar no título da presença
const colunas = colunasPlacar(PLACAR, 5, "pais");
assert.deepEqual(colunas.map((c) => c.chave), [
  "presidente", "deputado_federal", "deputado_estadual", "ufs_lider_estadual",
  "municipios_lidera", "eleitorado_liderado", "presenca", "legenda_federal", "legenda_estadual",
]);
assert.deepEqual(colunas.map((c) => c.esfera), [
  "nacional", "nacional", "estados", "estados", "municipios", "municipios", "municipios", "perfil", "perfil",
]);
assert.equal(colunas[3].titulo, "UFs em 1º (dep. estadual)");
assert.equal(colunas[3].curto, "UFs em 1º");
assert.equal(colunas[6].titulo, "Presença (≥ 5%)");
assert.equal(colunas[6].curto, "Presença ≥ 5%");
assert.equal(colunasPlacar(PLACAR, 10, "pais")[6].titulo, "Presença (≥ 10%)");
assert.equal(colunasPlacar(PLACAR, 5, "uf")[3].titulo, "1º em dep. estadual");
assert.equal(colunasPlacar(PLACAR, 5, "uf")[3].curto, "1º na UF");
for (const coluna of colunas) {
  assert.ok(coluna.explicacao.length > 20, `explicação curta em ${coluna.chave}`);
}

// país, limiar 5
const pais = linhasPlacar(PLACAR.pais, 5, "pais");
const pl = porChave(pais, "22");
const pt = porChave(pais, "13");
const pcdob = porChave(pais, "65");
assert.equal(pl.rotulo, "PL 22");
assert.deepEqual(pl.partidos, [22]);
assert.equal(pl.valores.presidente.texto, "40,00%");
assert.equal(pl.valores.presidente.ordem, 0.4);
assert.equal(pl.valores.presidente.fracao, 0.4);
assert.equal(pl.valores.presidente.detalhe, "40 votos");
assert.equal(pcdob.valores.presidente.texto, "—");
assert.equal(pcdob.valores.presidente.ordem, null);
assert.equal(pcdob.valores.presidente.fracao, null);
assert.equal(pcdob.valores.presidente.detalhe, "Sem dados");
// concorreu e teve 0 voto: 0,00%, não traço (F8)
assert.equal(pcdob.valores.deputado_estadual.texto, "0,00%");
assert.equal(pcdob.valores.deputado_estadual.ordem, 0);
assert.equal(pl.valores.ufs_lider_estadual.texto, "1 de 2");
assert.equal(pl.valores.ufs_lider_estadual.ordem, 1);
assert.equal(pl.valores.ufs_lider_estadual.fracao, 0.5);
assert.equal(pl.valores.ufs_lider_estadual.detalhe, "1 de 2 UFs com deputado estadual");
assert.equal(pt.valores.municipios_lidera.texto, "1");
assert.equal(pt.valores.municipios_lidera.detalhe, "de 3 municípios");
assert.equal(pt.valores.municipios_lidera.fracao, 1 / 3);
assert.equal(pt.valores.eleitorado_liderado.texto, "33,33%");
assert.equal(pt.valores.eleitorado_liderado.detalhe, "100 votos válidos");
assert.equal(pt.valores.presenca.texto, "3");
assert.equal(pt.valores.presenca.detalhe, "de 3 municípios com ao menos 5% dos válidos");
assert.equal(linhasPlacar(PLACAR.pais, 10, "pais").find((l) => l.chave === "13")?.valores.presenca.texto, "2");
// limiar fora da lista do backend: traço
assert.equal(porChave(linhasPlacar(PLACAR.pais, 3, "pais"), "13").valores.presenca.texto, "—");

// recorte AC, nível UF
const acre = PLACAR.ufs.find((uf) => uf.codigo === "AC");
assert.ok(acre);
const linhasAcre = linhasPlacar(acre, 5, "uf");
assert.equal(porChave(linhasAcre, "22").valores.ufs_lider_estadual.texto, "Sim");
assert.equal(porChave(linhasAcre, "13").valores.ufs_lider_estadual.texto, "Não");
assert.equal(porChave(linhasAcre, "22").valores.ufs_lider_estadual.detalhe, "");

// ordenação
assert.deepEqual(ordenarPlacar(pais, "deputado_federal", "desc").map((l) => l.chave), ["22", "13", "65"]);
assert.deepEqual(ordenarPlacar(pais, "deputado_federal", "asc").map((l) => l.chave), ["65", "13", "22"]);
assert.equal(ordenarPlacar(pais, "presidente", "asc").at(-1)?.chave, "65");
assert.equal(ordenarPlacar(pais, "presidente", "desc").at(-1)?.chave, "65");
// empate (municípios em 1º: 13 e 22 com 1): vence o menor número nas duas direções
assert.deepEqual(ordenarPlacar(pais, "municipios_lidera", "desc").map((l) => l.chave), ["13", "22", "65"]);
assert.deepEqual(ordenarPlacar(pais, "unidade", "asc").map((l) => l.rotulo), ["PCdoB 65", "PL 22", "PT 13"]);
// não muda a lista recebida
assert.deepEqual(pais.map((l) => l.chave), ["13", "22", "65"]);

// detalhe do partido por UF
const pt13 = linhasPorUf(PLACAR, "13", 5);
assert.deepEqual(pt13.map((l) => l.rotulo), ["Acre", "Amazonas"]);
assert.deepEqual(pt13.map((l) => l.chave), ["AC", "AM"]);
assert.equal(pt13[1].valores.presidente.texto, "—");
assert.equal(pt13[0].valores.ufs_lider_estadual.texto, "Não");
// partido sem célula nas UFs: tudo traço
const ausente = linhasPorUf(PLACAR, "65", 5);
assert.equal(ausente.length, 2);
for (const linha of ausente) {
  assert.ok(Object.values(linha.valores).every((v) => v.texto === "—" && v.ordem === null));
}
// empate também na direção crescente: o menor número vem antes
assert.deepEqual(ordenarPlacar(pais, "municipios_lidera", "asc").map((l) => l.chave), ["65", "13", "22"]);

// base 0 ou nula com valor presente: traço (F8), sem divisão por zero
const semBase = {
  ...PLACAR.pais,
  base: { ...PLACAR.pais.base, validos_presidente: 0, validos_deputado_federal: null },
};
const plSemBase = porChave(linhasPlacar(semBase, 5, "pais"), "22");
assert.deepEqual(plSemBase.valores.presidente, { ordem: null, fracao: null, texto: "—", detalhe: "Sem dados" });
assert.deepEqual(plSemBase.valores.deputado_federal, { ordem: null, fracao: null, texto: "—", detalhe: "Sem dados" });
// base municipal 0: as três colunas municipais viram traço
const semMunicipios = {
  ...PLACAR.pais,
  base: { ...PLACAR.pais.base, municipal: { municipios: 0, validos: 0, empates: 0 } },
};
const plSemMunicipios = porChave(linhasPlacar(semMunicipios, 5, "pais"), "22");
for (const chave of ["municipios_lidera", "eleitorado_liderado", "presenca"] as const) {
  assert.equal(plSemMunicipios.valores[chave].texto, "—", chave);
}

// bloco municipal ausente na unidade ou na base: traço nas três colunas
const pl22 = PLACAR.pais.unidades.find((u) => u.chave === "22");
assert.ok(pl22);
const semBlocoUnidade = { ...PLACAR.pais, unidades: [{ ...pl22, municipal: null }] };
const semBlocoBase = { ...PLACAR.pais, base: { ...PLACAR.pais.base, municipal: null } };
for (const recorte of [semBlocoUnidade, semBlocoBase]) {
  const linha = porChave(linhasPlacar(recorte, 5, "pais"), "22");
  for (const chave of ["municipios_lidera", "eleitorado_liderado", "presenca"] as const) {
    assert.equal(linha.valores[chave].ordem, null, chave);
  }
  assert.equal(linha.valores.presidente.texto, "40,00%");
}

// UF: Sim/Não também ordena e vira fração
assert.equal(porChave(linhasAcre, "22").valores.ufs_lider_estadual.ordem, 1);
assert.equal(porChave(linhasAcre, "22").valores.ufs_lider_estadual.fracao, 1);
assert.equal(porChave(linhasAcre, "13").valores.ufs_lider_estadual.ordem, 0);

// rótulo de federação: nome, ou a chave quando não há nome
const federacoes = {
  ...PLACAR.pais,
  unidades: [
    { ...pl22, chave: "fed:brasil", tipo: "federacao" as const, nome: "Brasil da Esperança", partidos: [13, 65, 43] },
    { ...pl22, chave: "fed:x", tipo: "federacao" as const, nome: null, partidos: [45, 23] },
  ],
};
assert.deepEqual(linhasPlacar(federacoes, 5, "pais").map((l) => l.rotulo), ["Brasil da Esperança", "fed:x"]);

// explicação da presença: o texto do plano (repetido em explicacao-forca.tsx)
assert.equal(
  colunas[6].explicacao,
  "Quantos municípios deram ao partido pelo menos o limiar escolhido dos votos válidos do cargo de referência.",
);

// fase B: cadeiras e federações
const SEM_ASSENTO = { camara: null, senado: null, governador_1t: null, governador_2t: null, assembleia: null };
const TOTAIS = { camara: 513, senado: 54, governadores: 27, assembleias: 1059 };
function assentos(camara: number, senado: number, g1: number, g2: number, assembleia: number) {
  return { camara, senado, governador_1t: g1, governador_2t: g2, assembleia };
}
function comAssentos(recorte: RecorteForca, por: Record<string, ReturnType<typeof assentos>>, base: typeof TOTAIS): RecorteForca {
  return {
    ...recorte,
    base: { ...recorte.base, cadeiras: base },
    unidades: recorte.unidades.map((u): UnidadeForca => ({ ...u, ...(por[u.chave] ?? SEM_ASSENTO) })),
    federadas: recorte.federadas.map((u): UnidadeForca => ({ ...u, ...(por[u.chave] ?? SEM_ASSENTO) })),
    base_federada: recorte.base_federada === null ? null : { ...recorte.base_federada, cadeiras: base },
  };
}
const unidadePt = PLACAR.pais.unidades[0];
const unidadePl = PLACAR.pais.unidades[1];
// Visão com federações (recalculada no backend): a federação e o 22, que perde liderança para ela.
const fe: UnidadeForca = {
  ...unidadePt, chave: "fed:fe-brasil", tipo: "federacao", nome: "Federação Brasil da Esperança", partidos: [13, 65],
};
const plFederado: UnidadeForca = {
  ...unidadePl, municipal: unidadePl.municipal === null ? null : { ...unidadePl.municipal, lidera: 0 },
};
const paisB = comAssentos({
  ...PLACAR.pais,
  federadas: [fe, plFederado],
  base_federada: { ...PLACAR.pais.base, municipal: { municipios: 3, validos: 300, empates: 0 } },
}, {
  "13": assentos(68, 9, 4, 6, 120),
  "22": assentos(119, 14, 3, 5, 200),
  "65": assentos(8, 0, 0, 0, 10),
  "fed:fe-brasil": assentos(76, 9, 4, 6, 130),
}, TOTAIS);
const acreB = comAssentos(PLACAR.ufs[0], { "13": assentos(2, 1, 1, 0, 8), "22": assentos(6, 1, 0, 0, 16) },
  { camara: 8, senado: 2, governadores: 1, assembleias: 24 });
const PLACAR_B: PlacarForca = {
  ...PLACAR,
  pais: paisB,
  ufs: [acreB, PLACAR.ufs[1]],
  cadeiras: { disponivel: true, comando: null, totais: TOTAIS },
};

// sem bloco (fase A): sete colunas; com bloco: cadeiras em cada esfera, na ordem
assert.equal(colunasPlacar(PLACAR, 5, "pais").length, 9);
const colunasB = colunasPlacar(PLACAR_B, 5, "pais");
assert.deepEqual(colunasB.map((c) => c.chave), [
  "presidente", "deputado_federal", "camara", "senado",
  "deputado_estadual", "ufs_lider_estadual", "governador_1t", "governador_2t", "assembleia",
  "municipios_lidera", "eleitorado_liderado", "presenca", "legenda_federal", "legenda_estadual",
]);
assert.deepEqual(colunasB.map((c) => c.titulo).slice(2, 4), ["Câmara (cadeiras estimadas)", "Senado (vagas estimadas)"]);
assert.deepEqual(colunasB.map((c) => c.titulo).slice(6, 9), [
  "Governadores no 1º turno", "No 2º turno de governador (disputa)", "Assembleias (cadeiras estimadas)",
]);
assert.ok(colunasB[8].explicacao.includes("24 da Câmara Legislativa do DF"));
// bloco indisponível: colunas aparecem (F20)
const indisponivel = { ...PLACAR, cadeiras: { disponivel: false, comando: "uv run c", totais: null } };
assert.equal(colunasPlacar(indisponivel, 5, "pais").length, 14);

const linhasB = linhasPlacar(PLACAR_B.pais, 5, "pais");
const plB = porChave(linhasB, "22");
assert.equal(plB.tipo, "partido");
assert.deepEqual(plB.valores.camara, { ordem: 119, fracao: 119 / 513, texto: "119", detalhe: "de 513" });
assert.deepEqual(plB.valores.senado, { ordem: 14, fracao: 14 / 54, texto: "14", detalhe: "de 54 vagas em 2026" });
assert.deepEqual(plB.valores.governador_1t, { ordem: 3, fracao: 3 / 27, texto: "3", detalhe: "de 27 UFs" });
// 2º turno: só a contagem, sem fração (fica fora do gráfico, F14)
assert.deepEqual(plB.valores.governador_2t, {
  ordem: 5, fracao: null, texto: "5", detalhe: "UFs em disputa, sem vencedor projetado",
});
assert.deepEqual(plB.valores.assembleia, { ordem: 200, fracao: 200 / 1059, texto: "200", detalhe: "de 1.059" });
// 0 é "não elegeu", não traço (F8)
assert.equal(porChave(linhasPlacar(acreB, 5, "uf"), "13").valores.governador_2t.texto, "0");
assert.equal(porChave(linhasPlacar(acreB, 5, "uf"), "22").valores.camara.detalhe, "de 8");
// fase A (sem bloco): traço
const linhasInd = linhasPlacar(PLACAR.pais, 5, "pais");
assert.equal(porChave(linhasInd, "22").valores.camara.texto, "—");
assert.equal(porChave(linhasInd, "22").valores.governador_2t.ordem, null);

// mostrar: partidos, ou a visão com federações (federações e partidos fora delas, recalculados)
assert.equal(temFederacoes(PLACAR), false);
assert.equal(temFederacoes(PLACAR_B), true);
assert.equal(recorteDoModo(PLACAR_B.pais, "partidos"), PLACAR_B.pais);
const federado = recorteDoModo(PLACAR_B.pais, "federacoes");
assert.deepEqual(federado.unidades.map((u) => u.chave), ["fed:fe-brasil", "22"]);
assert.equal(federado.base.municipal?.empates, 0);
const linhasFed = linhasPlacar(federado, 5, "pais");
assert.equal(porChave(linhasFed, "fed:fe-brasil").rotulo, "Federação Brasil da Esperança");
assert.equal(porChave(linhasFed, "fed:fe-brasil").tipo, "federacao");
// o 22 da visão com federações vem do cálculo junto, não da linha por partido
assert.equal(porChave(linhasFed, "22").valores.municipios_lidera.texto, "0");
assert.equal(porChave(linhasB, "22").valores.municipios_lidera.texto, "1");
// sem visão com federações: o modo não muda nada
assert.equal(recorteDoModo(PLACAR.pais, "federacoes"), PLACAR.pais);
// detalhe por UF de uma federação: procura na visão com federações das UFs
const acreFed = { ...acreB, federadas: [{ ...fe, ...assentos(3, 1, 1, 0, 9) }], base_federada: acreB.base };
const porUfFed = linhasPorUf({ ...PLACAR_B, ufs: [acreFed, PLACAR.ufs[1]] }, "fed:fe-brasil", 5, "federacoes");
assert.deepEqual(porUfFed.map((l) => l.valores.camara.texto), ["3", "—"]);
assert.equal(porUfFed[0].tipo, "federacao");
assert.equal(porUfFed[1].tipo, "federacao");

// linha de totais: soma só as linhas de partido, nunca as de federação
const totaisB = totaisPlacar(PLACAR_B.pais);
assert.deepEqual(
  [totaisB.camara, totaisB.senado, totaisB.governador_1t, totaisB.assembleia],
  ["195", "23", "7", "330"],
);
// 2º turno não soma: daria o dobro das UFs com 2º turno (F14)
assert.equal(totaisB.governador_2t, undefined);
// soma parcial: unidade sem cadeira não conta
const parcial = { ...PLACAR_B.pais, unidades: PLACAR_B.pais.unidades.map((u) => (u.chave === "65" ? { ...u, camara: null } : u)) };
assert.equal(totaisPlacar(parcial).camara, "187");
assert.equal(totaisB.presidente, undefined);
assert.deepEqual(totaisPlacar(PLACAR.pais), {});
// fase C: prefeitos, eleitorado governado e vereadores de 2024 na esfera Municípios
const TOTAIS_2024 = { municipios: 5569, com_prefeito: 5560, eleitorado: 155912680, vereadores: 58000 };
const BLOCO_2024 = { disponivel: true, comando: null, data_corte: "2026-10-01T08:30:00Z", totais: TOTAIS_2024 };
const colunasC = colunasPlacar({ cadeiras: null, municipal_2024: BLOCO_2024 }, 5, "pais");
assert.deepEqual(colunasC.slice(4, 10).map((c) => [c.chave, c.esfera, c.titulo]), [
  ["municipios_lidera", "municipios", "Municípios em 1º"],
  ["eleitorado_liderado", "municipios", "Eleitorado dos municípios em 1º"],
  ["presenca", "municipios", "Presença (≥ 5%)"],
  ["prefeitos", "municipios", "Prefeituras (2024)"],
  ["eleitorado_governado", "municipios", "Eleitorado governado (2024)"],
  ["vereadores", "municipios", "Vereadores (2024)"],
]);
// a data de corte usa o mesmo formato da página Municipais 2024 (formatarCorte)
for (const coluna of colunasC.slice(7, 10)) {
  assert.ok(coluna.explicacao.includes("Situação divulgada pelo TSE em 01/10/2026 às 08:30; inclui cassações e suplementares"));
}
const semCorte = colunasPlacar({ cadeiras: null, municipal_2024: { ...BLOCO_2024, data_corte: null } }, 5, "pais");
assert.ok(!semCorte[7].explicacao.includes("Situação"));
assert.equal(colunasPlacar({ cadeiras: null, municipal_2024: null }, 5, "pais").length, 9);
const indisponivel2024 = { disponivel: false, comando: "make x", data_corte: null, totais: null };
assert.equal(colunasPlacar({ cadeiras: null, municipal_2024: indisponivel2024 }, 5, "pais").length, 12);
const pais2024 = {
  ...PLACAR.pais,
  base: { ...PLACAR.pais.base, municipal_2024: TOTAIS_2024 },
  unidades: PLACAR.pais.unidades.map((u): UnidadeForca => (
    u.chave === "22" ? { ...u, prefeitos: 500, eleitorado_governado: 15591268, vereadores: 4000 }
      : { ...u, prefeitos: 0, eleitorado_governado: 0, vereadores: 0 }
  )),
};
const pl2024 = porChave(linhasPlacar(pais2024, 5, "pais"), "22");
assert.deepEqual(pl2024.valores.prefeitos, { ordem: 500, fracao: 500 / 5569, texto: "500", detalhe: "de 5.569 municípios" });
assert.deepEqual(pl2024.valores.eleitorado_governado, {
  ordem: 15591268 / 155912680, fracao: 15591268 / 155912680, texto: "10,00%", detalhe: "15.591.268 eleitores aptos em 2024",
});
assert.deepEqual(pl2024.valores.vereadores, { ordem: 4000, fracao: 4000 / 58000, texto: "4.000", detalhe: "de 58.000 vereadores" });
// 0 é "não elegeu"; sem totais no recorte (DF), traço
assert.equal(porChave(linhasPlacar(pais2024, 5, "pais"), "13").valores.prefeitos.texto, "0");
assert.equal(porChave(linhasPlacar(PLACAR.pais, 5, "pais"), "22").valores.prefeitos.texto, "—");
// recorte por UF com os totais da UF; na visão com federações, a base dela; UF sem totais (DF): traço
const acre2024 = {
  ...PLACAR.ufs[0],
  base: { ...PLACAR.ufs[0].base, municipal_2024: { municipios: 22, com_prefeito: 22, eleitorado: 600, vereadores: 230 } },
  unidades: PLACAR.ufs[0].unidades.map((u): UnidadeForca => ({ ...u, prefeitos: 9, eleitorado_governado: 300, vereadores: 40 })),
};
assert.equal(porChave(linhasPlacar(acre2024, 5, "uf"), "22").valores.prefeitos.detalhe, "de 22 municípios");
assert.equal(porChave(linhasPlacar(acre2024, 5, "uf"), "22").valores.eleitorado_governado.texto, "50,00%");
const distrito = { ...acre2024, codigo: "DF", base: { ...acre2024.base, municipal_2024: null } };
assert.equal(porChave(linhasPlacar(distrito, 5, "uf"), "22").valores.vereadores.texto, "—");
const acreFed2024 = {
  ...acre2024,
  federadas: [{ ...fe, prefeitos: 5, eleitorado_governado: 60, vereadores: 25 }],
  base_federada: acre2024.base,
};
const fed2024 = porChave(linhasPlacar(recorteDoModo(acreFed2024, "federacoes"), 5, "uf"), "fed:fe-brasil");
assert.equal(fed2024.valores.prefeitos.texto, "5");
assert.equal(fed2024.valores.eleitorado_governado.texto, "10,00%");

// rodapé: prefeitos e vereadores somam; o eleitorado governado não (a célula é parte do total)
const totais2024 = totaisPlacar(pais2024);
assert.deepEqual([totais2024.prefeitos, totais2024.vereadores, totais2024.eleitorado_governado], ["500", "4.000", undefined]);

// fase D: links do partido para os relatórios irmãos (constante do módulo)
assert.deepEqual(LINKS_RELATORIOS.map((l) => l.rotulo), ["Capilaridade", "Verticalização", "Força da marca"]);
assert.deepEqual(linksPartido(PLACAR, 22), [
  {
    rotulo: "Capilaridade",
    href: "/relatorios/capilaridade?ano=2026&turno=1&cargo=deputadoEstadual&recorte=brasil&partido=22&consultar=1",
  },
  { rotulo: "Verticalização", href: "/relatorios/verticalizacao?ano=2026&turno=1&uf=TODAS&partido=22&consultar=1" },
  { rotulo: "Força da marca", href: "/relatorios/marca" },
]);
assert.equal(
  linksPartido({ ...PLACAR, ano: 2022, turno: 2, cargo_referencia: "governador" }, 13)[0].href,
  "/relatorios/capilaridade?ano=2022&turno=2&cargo=governador&recorte=brasil&partido=13&consultar=1",
);

// fase D: voto de legenda, num grupo próprio fora das esferas e do gráfico
assert.deepEqual(GRUPOS_COLUNA, ["nacional", "estados", "municipios", "perfil"]);
assert.equal(ROTULOS_GRUPO.perfil, "Perfil do voto");
const colunasD = colunasPlacar(PLACAR, 5, "pais");
assert.deepEqual(colunasD.slice(-2).map((c) => [c.chave, c.esfera, c.titulo]), [
  ["legenda_federal", "perfil", "Voto de legenda (dep. federal)"],
  ["legenda_estadual", "perfil", "Voto de legenda (dep. estadual)"],
]);
const paisLegenda = {
  ...PLACAR.pais,
  unidades: PLACAR.pais.unidades.map((u): UnidadeForca => ({ ...u, legenda_federal: u.chave === "22" ? 5 : 1, legenda_estadual: 0 })),
};
const plLegenda = porChave(linhasPlacar(paisLegenda, 5, "pais"), "22");
assert.deepEqual(plLegenda.valores.legenda_federal, {
  ordem: 0.1, fracao: 0.1, texto: "10,00%", detalhe: "5 de 50 votos só no número do partido",
});
assert.equal(plLegenda.valores.legenda_estadual.texto, "0,00%");
// sem a fonte (null) ou federação: traço
assert.equal(plB.valores.legenda_federal.texto, "—");
assert.equal(porChave(linhasFed, "fed:fe-brasil").valores.legenda_estadual.texto, "—");
// a esfera Nacional do gráfico não leva o voto de legenda
assert.ok(colunasD.filter((c) => c.esfera === "nacional").every((c) => !c.chave.startsWith("legenda")));

// teste cruzado com o plano 5 (D4/D17): média do cargo = Σ legenda ÷ Σ válidos, no rodapé
const cruzado = {
  ...PLACAR.pais,
  base: { ...PLACAR.pais.base, validos_deputado_federal: 114107982, validos_deputado_estadual: 111662018 },
  unidades: [
    { ...PLACAR.pais.unidades[0], legenda_federal: 3000000, legenda_estadual: 7000000 },
    { ...PLACAR.pais.unidades[1], legenda_federal: 438422, legenda_estadual: 204172 },
    { ...fe, legenda_federal: null, legenda_estadual: null },
  ],
};
const totaisCruzados = totaisPlacar(cruzado);
assert.equal(totaisCruzados.legenda_federal, "3,01%");
assert.equal(totaisCruzados.legenda_estadual, "6,45%");
assert.equal(totaisPlacar(PLACAR.pais).legenda_federal, undefined);

// links só para linhas de partido: federação e unidade ausente não têm link
assert.deepEqual(linksUnidade(PLACAR, PLACAR.pais.unidades[1]).map((l) => l.href), linksPartido(PLACAR, 22).map((l) => l.href));
assert.deepEqual(linksUnidade(PLACAR, fe), []);
assert.deepEqual(linksUnidade(PLACAR, undefined), []);
// tipo do detalhe por UF vem da própria unidade, não do formato da chave
const fedSemPrefixo = { ...fe, chave: "frente" };
const comFrente = { ...PLACAR_B, ufs: [{ ...acreB, federadas: [fedSemPrefixo], base_federada: acreB.base }, PLACAR.ufs[1]] };
assert.deepEqual(linhasPorUf(comFrente, "frente", 5, "federacoes").map((l) => l.tipo), ["federacao", "federacao"]);

// colunas de cadeiras também no detalhe por UF
assert.equal(colunasPlacar(PLACAR_B, 5, "uf").length, 14);
console.log("ok");
