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
console.log("ok");
