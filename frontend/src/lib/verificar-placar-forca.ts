import assert from "node:assert/strict";
import { lerPlacarForca } from "./forca.ts";
import {
  COLUNA_PADRAO,
  colunasPlacar,
  linhasPlacar,
  linhasPorUf,
  ordenarPlacar,
  ROTULOS_ESFERA,
  type LinhaPlacar,
} from "./placar-forca.ts";

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
const colunas = colunasPlacar(5, "pais");
assert.deepEqual(colunas.map((c) => c.chave), [
  "presidente", "deputado_federal", "deputado_estadual", "ufs_lider_estadual",
  "municipios_lidera", "eleitorado_liderado", "presenca",
]);
assert.deepEqual(colunas.map((c) => c.esfera), [
  "nacional", "nacional", "estados", "estados", "municipios", "municipios", "municipios",
]);
assert.equal(colunas[3].titulo, "UFs em 1º (dep. estadual)");
assert.equal(colunas[3].curto, "UFs em 1º");
assert.equal(colunas[6].titulo, "Presença (≥ 5%)");
assert.equal(colunas[6].curto, "Presença ≥ 5%");
assert.equal(colunasPlacar(10, "pais")[6].titulo, "Presença (≥ 10%)");
assert.equal(colunasPlacar(5, "uf")[3].titulo, "1º em dep. estadual");
assert.equal(colunasPlacar(5, "uf")[3].curto, "1º na UF");
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
console.log("ok");
