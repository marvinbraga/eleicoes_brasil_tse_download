import assert from "node:assert/strict";
import { lerPlacarForca, RespostaForcaInvalidaError } from "./forca.ts";

const municipal = { lidera: 1, validos_liderados: 100, presenca: [{ limiar: 5, municipios: 3 }] };
const unidade = {
  chave: "22", tipo: "partido", nome: null, partidos: [22], presidente: 40, deputado_federal: null,
  deputado_estadual: 50, ufs_lider_estadual: 1, municipal,
};
const recorte = {
  codigo: "BR", nome: "Brasil", unidades: [unidade],
  base: { validos_presidente: 100, validos_deputado_federal: null, validos_deputado_estadual: 80,
    ufs_deputado_estadual: 2, municipal: { municipios: 3, validos: 300, empates: 1 } },
};
const json = { ano: 2026, turno: 1, cargo_referencia: "deputadoEstadual", limiares: [1, 2, 5, 10, 20],
  faltando: [{ cargo: "deputadoFederal", comando: "uv run x" }], pais: recorte, ufs: [] };

const lido = lerPlacarForca(json);
assert.equal(lido.pais.unidades[0].deputado_federal, null);
assert.equal(lido.pais.unidades[0].municipal?.presenca[0].municipios, 3);
assert.equal(lido.faltando[0].cargo, "deputadoFederal");

// campo ausente vira null (fases B e C acrescentam campos)
const semCampo = structuredClone(json);
delete (semCampo.pais.unidades[0] as Record<string, unknown>).ufs_lider_estadual;
assert.equal(lerPlacarForca(semCampo).pais.unidades[0].ufs_lider_estadual, null);

// entradas ruins
assert.throws(() => lerPlacarForca({ ...json, ano: "2026" }), RespostaForcaInvalidaError);
assert.throws(() => lerPlacarForca({ ...json, pais: { ...recorte, unidades: [{ ...unidade, tipo: "bloco" }] } }),
  RespostaForcaInvalidaError);
assert.throws(() => lerPlacarForca({ ...json, pais: { ...recorte, unidades: [{ ...unidade, presidente: 1.5 }] } }),
  RespostaForcaInvalidaError);
// bloco municipal ausente (base e unidade) vira null
const semMunicipal = structuredClone(json);
delete (semMunicipal.pais.base as Record<string, unknown>).municipal;
(semMunicipal.pais.unidades[0] as Record<string, unknown>).municipal = null;
assert.equal(lerPlacarForca(semMunicipal).pais.base.municipal, null);
assert.equal(lerPlacarForca(semMunicipal).pais.unidades[0].municipal, null);
assert.equal(lerPlacarForca({ ...json, ufs: [{ codigo: "AC", nome: "Acre", base: {}, unidades: [] }] }).ufs[0].base
  .validos_presidente, null);

// mais entradas ruins, e a mensagem mostrada ao usuário
assert.throws(() => lerPlacarForca({ ...json, pais: { ...recorte, unidades: [{ ...unidade, presidente: -1 }] } }),
  RespostaForcaInvalidaError);
assert.throws(() => lerPlacarForca({ ...json, pais: { ...recorte, unidades: "x" } }), RespostaForcaInvalidaError);
assert.throws(() => lerPlacarForca({ ...json, pais: { ...recorte, unidades: [{ ...unidade, nome: 3 }] } }),
  RespostaForcaInvalidaError);
assert.throws(() => lerPlacarForca(null), {
  name: "RespostaForcaInvalidaError",
  message: "A API devolveu um JSON que não confere com o placar de força.",
});

// fase B: bloco de cadeiras no topo, totais por recorte e cadeiras por unidade
const totais = { camara: 513, senado: 54, governadores: 27, assembleias: 1059 };
const comCadeiras = structuredClone(json) as Record<string, unknown>;
comCadeiras.cadeiras = { disponivel: true, comando: null, totais };
const recorteB = comCadeiras.pais as { base: Record<string, unknown>; unidades: Record<string, unknown>[] };
recorteB.base.cadeiras = totais;
Object.assign(recorteB.unidades[0], { camara: 119, senado: 14, governador_1t: 3, governador_2t: 5, assembleia: 200 });
const lidoB = lerPlacarForca(comCadeiras);
assert.deepEqual(lidoB.cadeiras, { disponivel: true, comando: null, totais });
assert.deepEqual(lidoB.pais.base.cadeiras, totais);
const u = lidoB.pais.unidades[0];
assert.deepEqual([u.camara, u.senado, u.governador_1t, u.governador_2t, u.assembleia], [119, 14, 3, 5, 200]);
// visão com federações: lista própria e base própria por recorte
const federacaoJson = { ...unidade, chave: "fed:fe", tipo: "federacao", nome: "Federação" };
const comFederadas = lerPlacarForca({ ...json, pais: { ...recorte, federadas: [federacaoJson],
  base_federada: { ...recorte.base, municipal: { municipios: 3, validos: 300, empates: 0 } } } });
assert.equal(comFederadas.pais.federadas[0].tipo, "federacao");
assert.equal(comFederadas.pais.base_federada?.municipal?.empates, 0);
assert.deepEqual(lido.pais.federadas, []);
assert.equal(lido.pais.base_federada, null);
// fase C: bloco de 2024, totais por recorte e contagens por unidade
const totais2024 = { municipios: 5569, com_prefeito: 5560, eleitorado: 155912680, vereadores: 58000 };
const com2024 = structuredClone(json) as Record<string, unknown>;
com2024.municipal_2024 = { disponivel: true, comando: null, data_corte: "2026-10-01T08:30:00Z", totais: totais2024 };
const recorteC = com2024.pais as { base: Record<string, unknown>; unidades: Record<string, unknown>[] };
recorteC.base.municipal_2024 = totais2024;
Object.assign(recorteC.unidades[0], { prefeitos: 500, eleitorado_governado: 2000, vereadores: 4000 });
const lidoC = lerPlacarForca(com2024);
assert.deepEqual(lidoC.municipal_2024, {
  disponivel: true, comando: null, data_corte: "2026-10-01T08:30:00Z", totais: totais2024,
});
assert.deepEqual(lidoC.pais.base.municipal_2024, totais2024);
const uC = lidoC.pais.unidades[0];
assert.deepEqual([uC.prefeitos, uC.eleitorado_governado, uC.vereadores], [500, 2000, 4000]);
assert.equal(lido.municipal_2024, null);
assert.equal(lido.pais.base.municipal_2024, null);
assert.equal(lido.pais.unidades[0].prefeitos, null);
assert.equal(lido.pais.unidades[0].legenda_federal, null);
const comLegenda = structuredClone(json);
Object.assign(comLegenda.pais.unidades[0], { legenda_federal: 7, legenda_estadual: 3 });
assert.deepEqual(
  [lerPlacarForca(comLegenda).pais.unidades[0].legenda_federal, lerPlacarForca(comLegenda).pais.unidades[0].legenda_estadual],
  [7, 3],
);
assert.throws(() => lerPlacarForca({ ...json, municipal_2024: { disponivel: true, comando: null, data_corte: 3, totais: null } }),
  RespostaForcaInvalidaError);
// fase A: sem bloco e sem campos, tudo null
assert.equal(lido.cadeiras, null);
assert.equal(lido.pais.base.cadeiras, null);
assert.equal(lido.pais.unidades[0].camara, null);
// bloco indisponível, com comando
const indisponivel = lerPlacarForca({ ...json, cadeiras: { disponivel: false, comando: "uv run c", totais: null } });
assert.deepEqual(indisponivel.cadeiras, { disponivel: false, comando: "uv run c", totais: null });
assert.throws(() => lerPlacarForca({ ...json, cadeiras: { disponivel: "sim", comando: null, totais: null } }),
  RespostaForcaInvalidaError);
assert.throws(() => lerPlacarForca({ ...json, cadeiras: { disponivel: true, comando: null, totais: { camara: 1 } } }),
  RespostaForcaInvalidaError);
console.log("ok");
