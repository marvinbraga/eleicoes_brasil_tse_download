import assert from "node:assert/strict";

import type { Composicao } from "../lib/relatorios.ts";
import {
  DEFINICOES,
  FRASE_FINALIDADE,
  FRASE_MARGEM,
  FRASE_RECORTE,
  estiloDaBarra,
  fraseDoAchado,
  INTENSIDADE,
  ORDEM_CLASSE,
} from "./finalidade.ts";

const cheia: Composicao = {
  votos_validos: 119299501,
  branco: 2300777,
  nulo: 3674209,
  classes: [
    { classe: "consolidacao", cidades: 1, votos_validos: 34682119 },
    { classe: "terreno_de_virada", cidades: 1, votos_validos: 1249978 },
    { classe: "em_aberto", cidades: 1, votos_validos: 83037291 },
    { classe: "sem_governador", cidades: 1, votos_validos: 330113 },
  ],
};

assert.equal(
  FRASE_FINALIDADE,
  "Este relatório mostra se o governador de cada lugar segue o líder da presidência, o segundo colocado, um terceiro partido, ou se não há governador.",
);
assert.equal(
  fraseDoAchado(cheia),
  "A maior parte dos votos válidos de presidente, 69,60%, está em municípios em aberto: o governador é de um partido que não lidera nem fica em segundo na presidência nesse lugar.",
);
assert.equal(fraseDoAchado(zerada()), null);
assert.match(fraseDoAchado(empate()) ?? "", /consolidação/i);
assert.equal(fraseDoAchado(desconhecida()), null);
assert.deepEqual(ORDEM_CLASSE.length, 4);
assert.deepEqual(
  ORDEM_CLASSE.map((classe) => INTENSIDADE[classe]),
  [1, 0.72, 0.48, 0.28],
);
assert.equal(FRASE_RECORTE.includes("lista de municípios"), true);
assert.equal(FRASE_MARGEM.includes("Brancos e nulos"), true);
assert.equal(Object.keys(DEFINICOES).length, 4);
assert.deepEqual(estiloDaBarra("consolidacao", 0), {
  flexGrow: 0,
  backgroundColor: "transparent",
  minWidth: 0,
});
assert.deepEqual(estiloDaBarra("em_aberto", 10), {
  flexGrow: 10,
  backgroundColor: "rgb(13, 111, 110)",
  opacity: 0.48,
});
assert.equal(estiloDaBarra("outra", 4).opacity, 1);

function zerada(): Composicao {
  return {
    votos_validos: 0,
    branco: 0,
    nulo: 0,
    classes: ORDEM_CLASSE.map((classe) => ({
      classe,
      cidades: 0,
      votos_validos: 0,
    })),
  };
}

function empate(): Composicao {
  return {
    votos_validos: 20,
    branco: 0,
    nulo: 0,
    classes: [
      { classe: "em_aberto", cidades: 1, votos_validos: 10 },
      { classe: "consolidacao", cidades: 1, votos_validos: 10 },
      { classe: "terreno_de_virada", cidades: 0, votos_validos: 0 },
      { classe: "sem_governador", cidades: 0, votos_validos: 0 },
    ],
  };
}

function desconhecida(): Composicao {
  return {
    votos_validos: 10,
    branco: 0,
    nulo: 0,
    classes: [{ classe: "outra", cidades: 1, votos_validos: 10 }],
  };
}

console.log("finalidade ok");
