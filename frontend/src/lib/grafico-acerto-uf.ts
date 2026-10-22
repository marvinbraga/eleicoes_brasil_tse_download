import { lerFatia } from "./fatia.ts";
import { ancorarRotulo } from "./largura-texto.ts";
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

export type MedidasAcertoUf = {
  largura: number;
  esquerda: number;
  direita: number;
  topo: number;
  base: number;
  alturaLinha: number;
  alturaFaixa: number;
  primeiraFaixa: number;
  distanciaRotulo: number;
  limiteAncoraFim: number | null;
  descidaMarca: number;
  fonte: number;
  fonteMenor: number;
};

export const MEDIDAS_PADRAO: MedidasAcertoUf = {
  largura: LARGURA,
  esquerda: ESQUERDA,
  direita: DIREITA,
  topo: TOPO,
  base: BASE,
  alturaLinha: ALTURA_LINHA,
  alturaFaixa: ALTURA_FAIXA,
  primeiraFaixa: 12,
  distanciaRotulo: DISTANCIA_ROTULO,
  limiteAncoraFim: LARGURA - 120,
  descidaMarca: 16,
  fonte: 12,
  fonteMenor: 11,
};

export const MEDIDAS_ESTREITO: MedidasAcertoUf = {
  largura: 340,
  esquerda: 34,
  direita: 18,
  topo: 60,
  base: 30,
  alturaLinha: 24,
  alturaFaixa: 17,
  primeiraFaixa: 14,
  distanciaRotulo: 340,
  limiteAncoraFim: null,
  descidaMarca: 18,
  fonte: 13,
  fonteMenor: 13,
};

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
  xTexto: number;
};

export type Marca = { x: number; rotulo: string };

export type LayoutAcertoUf = {
  medidas: MedidasAcertoUf;
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

export function layoutAcertoUf(
  entrada: EntradaGrafico,
  medidas: MedidasAcertoUf = MEDIDAS_PADRAO,
): LayoutAcertoUf | null {
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
    x: posicaoX(linha.fracao, medidas),
    y: medidas.topo + indice * medidas.alturaLinha + medidas.alturaLinha / 2,
    raio: raioDe(linha.municipios, nMax),
  }));
  return {
    medidas,
    largura: medidas.largura,
    altura: medidas.topo + pontos.length * medidas.alturaLinha + medidas.base,
    pontos,
    linhas: linhasDeReferencia(entrada, medidas),
    marcas: FRACOES_MARCAS.map((fracao) => ({
      x: posicaoX(fracao, medidas),
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

function posicaoX(fracao: number, medidas: MedidasAcertoUf): number {
  return medidas.esquerda + fracao * (medidas.largura - medidas.esquerda - medidas.direita);
}

function raioDe(municipios: number, nMax: number): number {
  if (nMax <= 0) {
    return RAIO_MIN;
  }
  return RAIO_MIN + (RAIO_MAX - RAIO_MIN) * Math.sqrt(Math.max(0, municipios) / nMax);
}

function linhasDeReferencia(entrada: EntradaGrafico, medidas: MedidasAcertoUf): LinhaReferencia[] {
  const candidatas = [
    { chave: "acerto", rotulo: "Acerto geral", valorTexto: entrada.acerto },
    { chave: "base", rotulo: "Maioria", valorTexto: entrada.base },
    { chave: "base_lider", rotulo: "Líder presidencial", valorTexto: entrada.baseLider },
  ] as const;
  const posicionadas = candidatas
    .flatMap((candidata) => {
      const fracao = lerFatia(candidata.valorTexto);
      return fracao === null ? [] : [{ ...candidata, x: posicaoX(fracao, medidas) }];
    })
    .sort((a, b) => a.x - b.x);
  const ultimasPorFaixa: (number | null)[] = [null, null, null];
  return posicionadas.map((linha) => {
    const faixa = escolherFaixa(ultimasPorFaixa, linha.x, medidas.distanciaRotulo);
    ultimasPorFaixa[faixa] = linha.x;
    return { ...linha, faixa, ...ancorar(linha, medidas) };
  });
}

function ancorar(
  linha: { rotulo: string; valorTexto: string; x: number },
  medidas: MedidasAcertoUf,
): { ancora: "start" | "end"; xTexto: number } {
  if (medidas.limiteAncoraFim === null) {
    return ancorarRotulo(linha.x, medidas.largura, `${linha.rotulo} ${linha.valorTexto}`, medidas.fonteMenor);
  }
  return linha.x > medidas.limiteAncoraFim
    ? { ancora: "end", xTexto: linha.x - 4 }
    : { ancora: "start", xTexto: linha.x + 4 };
}

function escolherFaixa(
  ultimasPorFaixa: readonly (number | null)[],
  x: number,
  distancia: number,
): 0 | 1 | 2 {
  const faixas = [0, 1, 2] as const;
  for (const faixa of faixas) {
    const ultima = ultimasPorFaixa[faixa];
    if (ultima === null || ultima === undefined || x - ultima >= distancia) {
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
