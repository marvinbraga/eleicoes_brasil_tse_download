import assert from "node:assert/strict";
import {
  frasesClasse,
  layoutAcertoClasse,
  resumoAcertoClasse,
  ALTURA_BARRA,
  ALTURA_LINHA,
  BASE,
  DIREITA,
  ESQUERDA,
  LARGURA,
  TOPO,
} from "./grafico-acerto-classe.ts";

const linha = (classe: string, rotulo: string, apoio: number, recall: string) => ({
  classe,
  rotulo,
  apoio,
  recall,
  regras: [],
});
const base = { acerto: "50,48%", base: "62,61%", baseLider: "51,75%" };
const real = {
  ...base,
  linhas: [
    linha("consolidacao", "Consolidação", 2011, "7,51%"),
    linha("terreno_de_virada", "Terreno de virada", 72, "0,00%"),
    linha("em_aberto", "Em aberto", 3488, "76,29%"),
  ],
};
const PLOTAGEM = LARGURA - ESQUERDA - DIREITA;

// ordem, coordenadas e alturas
const l = layoutAcertoClasse(real)!;
assert.deepEqual(l.barras.map((b) => b.classe), ["em_aberto", "consolidacao", "terreno_de_virada"]);
assert.equal(l.barras[0].x, ESQUERDA);
assert.ok(Math.abs(l.barras[0].largura - 0.7629 * PLOTAGEM) < 1e-9);
assert.equal(l.barras[2].largura, 0);
assert.equal(l.barras[0].y, TOPO + ALTURA_LINHA / 2 - ALTURA_BARRA / 2);
assert.equal(l.barras[1].y, TOPO + ALTURA_LINHA + ALTURA_LINHA / 2 - ALTURA_BARRA / 2);
assert.equal(l.altura, TOPO + 3 * ALTURA_LINHA + BASE);
assert.equal(l.largura, LARGURA);
assert.deepEqual([l.barras[0].municipios, l.barras[0].acertoTexto], [3488, "76,29%"]);
assert.deepEqual(l.marcas.map((m) => m.rotulo), ["0%", "25%", "50%", "75%", "100%"]);
assert.equal(l.marcas[4].x, LARGURA - DIREITA);
assert.ok(Math.abs(l.referencia!.x - (ESQUERDA + 0.5048 * PLOTAGEM)) < 1e-9);
assert.deepEqual([l.referencia!.valorTexto, l.referencia!.ancora], ["50,48%", "start"]);
assert.equal(layoutAcertoClasse({ ...real, acerto: "95,00%" })!.referencia!.ancora, "end");
assert.equal(layoutAcertoClasse({ ...real, acerto: "—" })!.referencia, null);

// quatro situações, 100% na borda e empate estável
const quatro = layoutAcertoClasse({
  ...base,
  linhas: [
    linha("consolidacao", "Consolidação", 10, "40,00%"),
    linha("terreno_de_virada", "Terreno de virada", 5, "40,00%"),
    linha("em_aberto", "Em aberto", 7, "100,00%"),
    linha("sem_governador", "Sem governador", 3, "12,50%"),
  ],
})!;
assert.deepEqual(quatro.barras.map((b) => b.classe), ["em_aberto", "consolidacao", "terreno_de_virada", "sem_governador"]);
assert.equal(quatro.barras[0].x + quatro.barras[0].largura, LARGURA - DIREITA);
assert.equal(quatro.altura, TOPO + 4 * ALTURA_LINHA + BASE);

// entradas ruins
assert.equal(layoutAcertoClasse({ ...base, linhas: [] }), null);
assert.equal(layoutAcertoClasse({ ...base, linhas: [linha("em_aberto", "Em aberto", 0, "—")] }), null);
const ruim = layoutAcertoClasse({ ...real, linhas: [...real.linhas, linha("sem_governador", "Sem governador", 0, "—")] })!;
assert.equal(ruim.descartadas, 1);
assert.equal(ruim.barras.length, 3);

// frases com os dados reais: abaixo das duas bases
assert.deepEqual(frasesClasse(real), [
  "No geral, o modelo acertou 50,48% dos municípios. Cada estado foi testado sem que o modelo tivesse visto os municípios dele.",
  "Isso é menos do que dois chutes simples: marcar sempre a situação mais comum acertaria 62,61%, e seguir o partido que lidera para presidente acertaria 51,75%.",
  "Onde mais acerta: dos 3.488 municípios que eram de fato “Em aberto”, o modelo acertou 76,29%.",
  "Onde mais erra: dos 72 municípios que eram de fato “Terreno de virada”, o modelo não acertou nenhum.",
]);
assert.equal(resumoAcertoClasse(real),
  "Acerto geral 50,48%. Em aberto: acertou 76,29% de 3.488 municípios; Consolidação: acertou 7,51% de 2.011 municípios; Terreno de virada: acertou 0,00% de 72 municípios.");

// acima das duas, entre elas, base inválida
assert.equal(frasesClasse({ ...real, acerto: "70,00%" })[1],
  "Isso é mais do que dois chutes simples: marcar sempre a situação mais comum acertaria 62,61%, e seguir o partido que lidera para presidente acertaria 51,75%.");
assert.equal(frasesClasse({ ...real, acerto: "55,00%" })[1],
  "Isso é menos do que marcar sempre a situação mais comum (62,61%), mas mais do que seguir o partido que lidera para presidente (51,75%).");
assert.equal(frasesClasse({ ...real, acerto: "62,61%" })[1],
  "Isso é o mesmo que marcar sempre a situação mais comum (62,61%), mas mais do que seguir o partido que lidera para presidente (51,75%).");
assert.equal(frasesClasse({ ...real, baseLider: "—" })[1],
  "Isso é menos do que marcar sempre a situação mais comum, que acertaria 62,61%.");
const semBases = frasesClasse({ ...real, base: "x", baseLider: "—" });
assert.equal(semBases.length, 3);
assert.ok(semBases[1].startsWith("Onde mais acerta"));
assert.equal(frasesClasse({ ...real, acerto: "—" })[0], "Não há acerto geral neste recorte.");
assert.ok(frasesClasse({ ...real, acerto: "—" })[1].startsWith("Onde mais acerta"));

// pior com acerto, único município, todas iguais, uma só
assert.equal(frasesClasse({ ...real, linhas: [real.linhas[0], real.linhas[2]] })[3],
  "Onde mais erra: dos 2.011 municípios que eram de fato “Consolidação”, o modelo acertou só 7,51%.");
assert.deepEqual(frasesClasse({ ...real, linhas: [linha("em_aberto", "Em aberto", 1, "100,00%"), linha("consolidacao", "Consolidação", 1, "0,00%")] }).slice(2), [
  "Onde mais acerta: do único município que era de fato “Em aberto”, o modelo acertou 100,00%.",
  "Onde mais erra: do único município que era de fato “Consolidação”, o modelo não acertou.",
]);
assert.equal(frasesClasse({ ...real, linhas: [linha("em_aberto", "Em aberto", 4, "50,00%"), linha("consolidacao", "Consolidação", 2, "50,00%")] })[2],
  "O modelo acertou 50,00% em todas as situações.");
assert.equal(frasesClasse({ ...real, linhas: [real.linhas[2]] }).length, 3);
assert.equal(frasesClasse({ ...real, linhas: [] }).length, 2);
console.log("ok");
