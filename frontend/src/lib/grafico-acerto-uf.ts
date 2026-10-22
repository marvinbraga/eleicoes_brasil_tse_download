import { lerFatia } from "./fatia.ts";
import type { AcertoUf } from "./relatorios.ts";

export const LARGURA = 640,
  ALTURA_LINHA = 24,
  RAIO_MIN = 4,
  RAIO_MAX = 10,
  ESQUERDA = 44,
  DIREITA = 16,
  TOPO = 50,
  BASE = 28,
  DISTANCIA_ROTULO = 96,
  ALTURA_FAIXA = 14;

const LIMITE_ANCORA_FIM = LARGURA - 120;
const FRACOES_MARCAS = [0, 0.25, 0.5, 0.75, 1];

export type EntradaGrafico = {
  porUf: readonly AcertoUf[];
  acerto: string;
  base: string;
  baseLider: string;
};

export type PontoUf = {
  uf: string;
  municipios: number;
  acertoTexto: string;
  x: number;
  y: number;
  raio: number;
};

export type LinhaReferencia = {
  chave: "acerto" | "base" | "base_lider";
  rotulo: string;
  valorTexto: string;
  x: number;
  faixa: 0 | 1 | 2;
  ancora: "start" | "end";
};

export type Marca = { x: number; rotulo: string };

export type LayoutAcertoUf = {
  largura: number;
  altura: number;
  pontos: PontoUf[];
  linhas: LinhaReferencia[];
  marcas: Marca[];
  descartadas: number;
  menorMunicipios: number;
  maiorMunicipios: number;
};

type UfValida = { uf: string; municipios: number; acertoTexto: string; fracao: number };

export function layoutAcertoUf(entrada: EntradaGrafico): LayoutAcertoUf | null {
  const validas = ufsValidas(entrada.porUf);
  if (validas.length === 0) {
    return null;
  }
  const municipios = validas.map((linha) => linha.municipios);
  const nMax = Math.max(...municipios);
  const pontos = validas.map((linha, indice) => ({
    uf: linha.uf,
    municipios: linha.municipios,
    acertoTexto: linha.acertoTexto,
    x: posicaoX(linha.fracao),
    y: TOPO + indice * ALTURA_LINHA + ALTURA_LINHA / 2,
    raio: raioDe(linha.municipios, nMax),
  }));
  return {
    largura: LARGURA,
    altura: TOPO + pontos.length * ALTURA_LINHA + BASE,
    pontos,
    linhas: linhasDeReferencia(entrada),
    marcas: FRACOES_MARCAS.map((fracao) => ({
      x: posicaoX(fracao),
      rotulo: `${fracao * 100}%`,
    })),
    descartadas: entrada.porUf.length - validas.length,
    menorMunicipios: Math.min(...municipios),
    maiorMunicipios: nMax,
  };
}

export function resumoAcertoUf(entrada: EntradaGrafico): string {
  const validas = ufsValidas(entrada.porUf);
  const primeira = validas[0];
  const ultima = validas[validas.length - 1];
  if (primeira === undefined || ultima === undefined) {
    return "Nenhuma UF com acerto.";
  }
  const total = validas.length;
  const topo = validas.filter((linha) => linha.fracao === primeira.fracao).map((linha) => linha.uf);
  const fundo = validas.filter((linha) => linha.fracao === ultima.fracao).map((linha) => linha.uf);
  const frases = [
    `${total} UFs.`,
    `Maior acerto: ${juntar(topo)} com ${primeira.acertoTexto}.`,
    `Menor: ${juntar(fundo)} com ${ultima.acertoTexto}.`,
  ];
  const base = lerFatia(entrada.base);
  if (base !== null) {
    const abaixo = validas.filter((linha) => linha.fracao < base).length;
    frases.push(`${abaixo} de ${total} UFs ficam abaixo da base da maioria (${entrada.base}).`);
  }
  return frases.join(" ");
}

function ufsValidas(porUf: readonly AcertoUf[]): UfValida[] {
  const validas: UfValida[] = [];
  for (const linha of porUf) {
    const fracao = lerFatia(linha.acerto);
    if (fracao !== null) {
      validas.push({
        uf: linha.uf,
        municipios: linha.municipios,
        acertoTexto: linha.acerto,
        fracao,
      });
    }
  }
  return validas.sort((a, b) => b.fracao - a.fracao || a.uf.localeCompare(b.uf, "pt-BR"));
}

function posicaoX(fracao: number): number {
  return ESQUERDA + fracao * (LARGURA - ESQUERDA - DIREITA);
}

function raioDe(municipios: number, nMax: number): number {
  if (nMax <= 0) {
    return RAIO_MIN;
  }
  return RAIO_MIN + (RAIO_MAX - RAIO_MIN) * Math.sqrt(Math.max(0, municipios) / nMax);
}

function linhasDeReferencia(entrada: EntradaGrafico): LinhaReferencia[] {
  const candidatas = [
    { chave: "acerto", rotulo: "Acerto geral", valorTexto: entrada.acerto },
    { chave: "base", rotulo: "Maioria", valorTexto: entrada.base },
    { chave: "base_lider", rotulo: "Líder presidencial", valorTexto: entrada.baseLider },
  ] as const;
  const posicionadas = candidatas
    .flatMap((candidata) => {
      const fracao = lerFatia(candidata.valorTexto);
      return fracao === null ? [] : [{ ...candidata, x: posicaoX(fracao) }];
    })
    .sort((a, b) => a.x - b.x);
  const ultimasPorFaixa: (number | null)[] = [null, null, null];
  return posicionadas.map((linha) => {
    const faixa = escolherFaixa(ultimasPorFaixa, linha.x);
    ultimasPorFaixa[faixa] = linha.x;
    return {
      ...linha,
      faixa,
      ancora: linha.x > LIMITE_ANCORA_FIM ? "end" : "start",
    };
  });
}

function escolherFaixa(ultimasPorFaixa: readonly (number | null)[], x: number): 0 | 1 | 2 {
  const faixas = [0, 1, 2] as const;
  for (const faixa of faixas) {
    const ultima = ultimasPorFaixa[faixa];
    if (ultima === null || ultima === undefined || x - ultima >= DISTANCIA_ROTULO) {
      return faixa;
    }
  }
  return 2;
}

function juntar(nomes: readonly string[]): string {
  if (nomes.length <= 1) {
    return nomes[0] ?? "";
  }
  const ultimo = nomes[nomes.length - 1] ?? "";
  return `${nomes.slice(0, -1).join(", ")} e ${ultimo}`;
}
