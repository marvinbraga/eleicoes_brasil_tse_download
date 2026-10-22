import { formatarInteiro, formatarPercentualContagem } from "./fracao.ts";
import { rotuloPartido } from "./partidos.ts";
import type { LinhaGrade } from "./relatorios.ts";

export const LARGURA = 640,
  ALTURA_LINHA = 28,
  ALTURA_BARRA = 16,
  ESQUERDA = 120,
  DIREITA = 72,
  TOPO = 4,
  BASE = 4,
  LIMITE_PARTIDOS = 8;

export type ItemBarra = {
  chave: string;
  rotulo: string;
  valor: number;
  texto: string;
  detalhe: string;
  lugares?: number;
};

export type Barra = ItemBarra & { y: number; largura: number };

export type LayoutBarras = { largura: number; altura: number; barras: Barra[] };

type Contagem = { partido: number; valor: number };

type Disputa = {
  nome: string;
  validos: number;
  primeiro: Contagem;
  segundo: Contagem | undefined;
};

export function fatiasPoder(linhas: readonly LinhaGrade[]): ItemBarra[] {
  const somas = new Map<number, number>();
  for (const linha of linhas) {
    for (const celula of linha.celulas) {
      somas.set(celula.partido, (somas.get(celula.partido) ?? 0) + celula.votos);
    }
  }
  const contagens = ordenarContagens(somas);
  const total = contagens.reduce((soma, item) => soma + item.valor, 0);
  return agrupar(contagens).map((grupo) => ({
    chave: grupo.chave,
    rotulo: grupo.rotulo,
    valor: grupo.valor,
    texto: formatarPercentualContagem(grupo.valor, total),
    detalhe:
      grupo.partidos > 1
        ? `${formatarInteiro(grupo.partidos)} partidos, ${votos(grupo.valor)}`
        : votos(grupo.valor),
  }));
}

export function liderancasPoder(linhas: readonly LinhaGrade[]): {
  itens: ItemBarra[];
  lugares: number;
  empates: number;
} {
  const disputas = disputasDe(linhas);
  const votosLiderados = new Map<number, number>();
  const lugaresLiderados = new Map<number, number>();
  let empates = 0;
  for (const disputa of disputas) {
    if (empatada(disputa)) {
      empates += 1;
    } else {
      const partido = disputa.primeiro.partido;
      votosLiderados.set(partido, (votosLiderados.get(partido) ?? 0) + disputa.validos);
      lugaresLiderados.set(partido, (lugaresLiderados.get(partido) ?? 0) + 1);
    }
  }
  const lugares = disputas.length;
  const total = disputas.reduce((soma, disputa) => soma + disputa.validos, 0);
  const contagens = ordenarContagens(votosLiderados);
  const grupos = agrupar(contagens);
  const visiveis = grupos.filter((grupo) => grupo.chave !== "outros").length;
  const itens = grupos.map((grupo) => {
    const liderados =
      grupo.chave === "outros"
        ? contagens.slice(visiveis).reduce((soma, item) => soma + (lugaresLiderados.get(item.partido) ?? 0), 0)
        : (lugaresLiderados.get(Number(grupo.chave)) ?? 0);
    return {
      chave: grupo.chave,
      rotulo: grupo.rotulo,
      valor: grupo.valor,
      texto: formatarPercentualContagem(grupo.valor, total),
      detalhe: `${votos(grupo.valor)} válidos\n${formatarInteiro(liderados)} de ${formatarInteiro(lugares)} ${lugares === 1 ? "lugar" : "lugares"}`,
      lugares: liderados,
    };
  });
  return { itens, lugares, empates };
}

export function layoutBarras(itens: readonly ItemBarra[]): LayoutBarras | null {
  const maior = Math.max(0, ...itens.map((item) => item.valor));
  if (itens.length === 0 || maior <= 0) {
    return null;
  }
  const util = LARGURA - ESQUERDA - DIREITA;
  return {
    largura: LARGURA,
    altura: TOPO + itens.length * ALTURA_LINHA + BASE,
    barras: itens.map((item, indice) => ({
      ...item,
      y: TOPO + indice * ALTURA_LINHA + ALTURA_LINHA / 2,
      largura: (Math.max(0, item.valor) / maior) * util,
    })),
  };
}

export function resumoBarras(introducao: string, itens: readonly ItemBarra[]): string {
  const partes = itens.map((item) => `${item.rotulo}: ${item.texto}`).join("; ");
  return partes === "" ? introducao : `${introducao} ${partes}.`;
}

export function leituraPoder(linhas: readonly LinhaGrade[]): string[] {
  const disputas = disputasDe(linhas);
  const unica = disputas[0];
  if (unica === undefined) {
    return [];
  }
  if (disputas.length === 1) {
    return leituraUnica(unica);
  }
  const frases: string[] = [];
  const { itens, lugares, empates } = liderancasPoder(linhas);
  const primeiro = itens[0];
  if (primeiro !== undefined && primeiro.chave !== "outros") {
    const lideres = itens.filter((item) => item.chave !== "outros" && item.valor === primeiro.valor);
    const parte = `lugares que somam ${primeiro.texto} dos votos válidos do recorte`;
    frases.push(
      lideres.length === 1
        ? `${primeiro.rotulo} lidera em ${parte} (${formatarInteiro(primeiro.lugares ?? 0)} de ${formatarInteiro(lugares)} lugares).`
        : `${juntar(lideres.map((item) => item.rotulo))} lideram em ${parte} cada.`,
    );
  }
  if (empates > 0) {
    frases.push(
      `Em ${formatarInteiro(empates)} ${empates === 1 ? "lugar" : "lugares"}, os dois primeiros empatam.`,
    );
  }
  const apertada = maisApertada(disputas);
  if (apertada?.segundo !== undefined) {
    frases.push(fraseApertada(apertada, apertada.segundo));
  }
  return frases;
}

function leituraUnica(disputa: Disputa): string[] {
  const { nome, validos, primeiro, segundo } = disputa;
  if (segundo !== undefined && empatada(disputa)) {
    return [
      `Em ${nome}, ${rotuloPartido(primeiro.partido)} e ${rotuloPartido(segundo.partido)} empatam no primeiro lugar.`,
    ];
  }
  const frases = [
    `Em ${nome}, ${rotuloPartido(primeiro.partido)} lidera com ${formatarPercentualContagem(primeiro.valor, validos)} dos votos válidos.`,
  ];
  if (segundo !== undefined) {
    frases.push(
      `O segundo é ${rotuloPartido(segundo.partido)}, com ${formatarPercentualContagem(segundo.valor, validos)}, ` +
        `uma diferença de ${formatarPercentualContagem(primeiro.valor - segundo.valor, validos)} dos votos válidos.`,
    );
  }
  return frases;
}

function fraseApertada(disputa: Disputa, segundo: Contagem): string {
  const { nome, validos, primeiro } = disputa;
  if (primeiro.valor === segundo.valor) {
    return `A disputa mais apertada é em ${nome}, com empate entre ${rotuloPartido(primeiro.partido)} e ${rotuloPartido(segundo.partido)}.`;
  }
  return (
    `A disputa mais apertada é em ${nome}: ` +
    `${rotuloPartido(primeiro.partido)} tem ${formatarPercentualContagem(primeiro.valor, validos)} e ` +
    `${rotuloPartido(segundo.partido)} tem ${formatarPercentualContagem(segundo.valor, validos)}, ` +
    `uma diferença de ${formatarPercentualContagem(primeiro.valor - segundo.valor, validos)} dos votos válidos.`
  );
}

function maisApertada(disputas: readonly Disputa[]): Disputa | undefined {
  let melhor: { disputa: Disputa; margem: number } | undefined;
  for (const disputa of disputas) {
    if (disputa.segundo === undefined) {
      continue;
    }
    const margem = (disputa.primeiro.valor - disputa.segundo.valor) / disputa.validos;
    if (
      melhor === undefined ||
      margem < melhor.margem ||
      (margem === melhor.margem && disputa.nome.localeCompare(melhor.disputa.nome, "pt-BR") < 0)
    ) {
      melhor = { disputa, margem };
    }
  }
  return melhor?.disputa;
}

function disputasDe(linhas: readonly LinhaGrade[]): Disputa[] {
  const disputas: Disputa[] = [];
  for (const linha of linhas) {
    const contagens = linha.celulas
      .filter((celula) => celula.votos > 0)
      .map((celula) => ({ partido: celula.partido, valor: celula.votos }))
      .sort(compararContagens);
    const primeiro = contagens[0];
    if (primeiro === undefined) {
      continue;
    }
    disputas.push({
      nome: linha.nome,
      validos: contagens.reduce((soma, item) => soma + item.valor, 0),
      primeiro,
      segundo: contagens[1],
    });
  }
  return disputas;
}

function empatada(disputa: Disputa): boolean {
  return disputa.segundo !== undefined && disputa.segundo.valor === disputa.primeiro.valor;
}

function ordenarContagens(mapa: ReadonlyMap<number, number>): Contagem[] {
  return [...mapa.entries()]
    .map(([partido, valor]) => ({ partido, valor }))
    .filter((item) => item.valor > 0)
    .sort(compararContagens);
}

function compararContagens(a: Contagem, b: Contagem): number {
  return b.valor - a.valor || a.partido - b.partido;
}

function agrupar(
  contagens: readonly Contagem[],
): { chave: string; rotulo: string; valor: number; partidos: number }[] {
  const visiveis = contagens.length > LIMITE_PARTIDOS + 1 ? contagens.slice(0, LIMITE_PARTIDOS) : contagens;
  const grupos = visiveis.map((item) => ({
    chave: String(item.partido),
    rotulo: rotuloPartido(item.partido),
    valor: item.valor,
    partidos: 1,
  }));
  const resto = contagens.slice(visiveis.length);
  if (resto.length > 0) {
    grupos.push({
      chave: "outros",
      rotulo: "Outros",
      valor: resto.reduce((soma, item) => soma + item.valor, 0),
      partidos: resto.length,
    });
  }
  return grupos;
}

function votos(valor: number): string {
  return `${formatarInteiro(valor)} ${valor === 1 ? "voto" : "votos"}`;
}

function juntar(nomes: readonly string[]): string {
  if (nomes.length <= 1) {
    return nomes[0] ?? "";
  }
  const ultimo = nomes[nomes.length - 1] ?? "";
  return `${nomes.slice(0, -1).join(", ")} e ${ultimo}`;
}
