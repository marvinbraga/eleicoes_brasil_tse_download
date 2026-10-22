// Layout e frases da página de capilaridade. Só posiciona e escreve o que o backend
// já calculou: índice, partes, faixas e classes vêm prontos do JSON.
import {
  NAO_RANQUEADAS,
  type ChaveFaixa,
  type FaixaCapilaridade,
  type PartidoCapilaridade,
  type Recorte,
} from "./capilaridade.ts";
import { formatarInteiro, formatarPercentualContagem, TRACO } from "./fracao.ts";
import { larguraTexto } from "./largura-texto.ts";
import { rotuloPartido } from "./partidos.ts";

export type MedidasRanking = {
  largura: number;
  esquerda: number;
  direita: number;
  topo: number;
  base: number;
  alturaLinha: number;
  alturaBarra: number;
  descida: number;
  rotuloAcima: boolean;
  fonte: number;
};

// Largo: rótulo à esquerda; valor e classe à direita da barra.
export const MEDIDAS_RANKING: MedidasRanking = {
  largura: 640,
  esquerda: 120,
  direita: 220,
  topo: 22,
  base: 4,
  alturaLinha: 26,
  alturaBarra: 14,
  descida: 0,
  rotuloAcima: false,
  fonte: 12,
};

// Estreito (375 px): rótulo e classe acima da barra; só o valor à direita.
export const MEDIDAS_RANKING_ESTREITO: MedidasRanking = {
  largura: 340,
  esquerda: 2,
  direita: 40,
  topo: 22,
  base: 4,
  alturaLinha: 40,
  alturaBarra: 12,
  descida: 18,
  rotuloAcima: true,
  fonte: 13,
};

const ESCALA_INDICE = 100;
const MARCAS_INDICE = [0, 25, 50, 75, 100] as const;
const FOLGA_TEXTO = 8;

export type BarraRanking = {
  partido: number;
  rotulo: string;
  classe: string;
  valor: number;
  y: number;
  largura: number;
  selecionado: boolean;
  href: string;
  dica: string[];
};

export type LayoutRanking = {
  medidas: MedidasRanking;
  largura: number;
  altura: number;
  marcas: { x: number; texto: string }[];
  barras: BarraRanking[];
};

export function ranqueaveis(partidos: readonly PartidoCapilaridade[]): PartidoCapilaridade[] {
  return partidos.filter((item) => !NAO_RANQUEADAS.has(item.classe));
}

export function layoutRanking(
  partidos: readonly PartidoCapilaridade[],
  selecionado: number,
  href: (partido: number) => string,
  medidas: MedidasRanking = MEDIDAS_RANKING,
): LayoutRanking | null {
  const lista = ranqueaveis(partidos);
  if (lista.length === 0) {
    return null;
  }
  const util = medidas.largura - medidas.esquerda - medidas.direita;
  const barras = lista.map((item, indice) => ({
    partido: item.partido,
    rotulo: rotuloPartido(item.partido),
    classe: item.rotulo_classe,
    valor: item.indice_100,
    y: medidas.topo + indice * medidas.alturaLinha + medidas.descida,
    largura: (limitar(item.indice_100) / ESCALA_INDICE) * util,
    selecionado: item.partido === selecionado,
    href: href(item.partido),
    dica: dicaRanking(item),
  }));
  const marcas = MARCAS_INDICE.map((valor) => ({
    x: medidas.esquerda + (valor / ESCALA_INDICE) * util,
    texto: String(valor),
  }));
  return {
    medidas,
    largura: Math.max(medidas.largura, larguraNecessaria(barras, medidas, util)),
    altura: medidas.topo + lista.length * medidas.alturaLinha + medidas.base,
    marcas,
    barras,
  };
}

export function textoDireita(barra: BarraRanking, medidas: MedidasRanking): string {
  return medidas.rotuloAcima ? String(barra.valor) : `${barra.valor}  ${barra.classe}`;
}

// A escala é fixa; se a classe não couber à direita, o desenho ganha largura.
function larguraNecessaria(
  barras: readonly BarraRanking[],
  medidas: MedidasRanking,
  util: number,
): number {
  const maior = Math.max(...barras.map((barra) => larguraTexto(textoDireita(barra, medidas), medidas.fonte)));
  return medidas.esquerda + util + maior + FOLGA_TEXTO;
}

function dicaRanking(item: PartidoCapilaridade): string[] {
  return [
    `Índice ${item.indice_100} de 100`,
    item.rotulo_classe,
    `Fatia ${item.fatia_texto}`,
    `10% mais fortes: ${item.top10.parte_texto} dos votos, ${item.top10.eleitorado_texto} do eleitorado`,
  ];
}

function limitar(valor: number): number {
  if (!Number.isFinite(valor) || valor <= 0) {
    return 0;
  }
  return Math.min(ESCALA_INDICE, valor);
}

export type MedidasFaixas = {
  largura: number;
  altura: number;
  esquerda: number;
  direita: number;
  topo: number;
  base: number;
  vao: number;
  fonte: number;
};

export const MEDIDAS_FAIXAS: MedidasFaixas = {
  largura: 300,
  altura: 180,
  esquerda: 4,
  direita: 4,
  topo: 18,
  base: 38,
  vao: 2,
  fonte: 11,
};

export const MEDIDAS_FAIXAS_ESTREITO: MedidasFaixas = {
  largura: 340,
  altura: 170,
  esquerda: 4,
  direita: 4,
  topo: 18,
  base: 38,
  vao: 2,
  fonte: 12,
};

export const ROTULOS_FAIXA: Record<ChaveFaixa, { curto: string; longo: string }> = {
  zero: { curto: "0", longo: "Sem voto" },
  ate_metade: { curto: "<½", longo: "Menos da metade da média" },
  metade_a_media: { curto: "½–1", longo: "Da metade até a média" },
  media_a_1_5: { curto: "1–1,5", longo: "Da média até 1,5 vez" },
  "1_5_a_2": { curto: "1,5–2", longo: "De 1,5 a 2 vezes a média" },
  "2_a_3": { curto: "2–3", longo: "De 2 a 3 vezes a média" },
  "3_ou_mais": { curto: "3+", longo: "3 vezes a média ou mais" },
};

export type MedidaFaixa = "municipios" | "votos";

export type ColunaFaixa = {
  chave: ChaveFaixa;
  x: number;
  y: number;
  largura: number;
  altura: number;
  valor: string;
  neutra: boolean;
  dica: string[];
};

export type LayoutFaixas = {
  medidas: MedidasFaixas;
  largura: number;
  altura: number;
  colunas: ColunaFaixa[];
};

function valorFaixa(faixa: FaixaCapilaridade, medida: MedidaFaixa): number {
  if (medida === "municipios") {
    return faixa.municipios;
  }
  return faixa.chave === "zero" ? 0 : faixa.votos;
}

export function layoutFaixas(
  faixas: readonly FaixaCapilaridade[],
  medida: MedidaFaixa,
  medidas: MedidasFaixas = MEDIDAS_FAIXAS,
): LayoutFaixas | null {
  const totalMunicipios = soma(faixas.map((faixa) => faixa.municipios));
  const totalVotos = soma(faixas.map((faixa) => faixa.votos));
  const total = medida === "municipios" ? totalMunicipios : totalVotos;
  if (faixas.length === 0 || totalMunicipios === 0 || total === 0) {
    return null;
  }
  const maior = Math.max(...faixas.map((faixa) => valorFaixa(faixa, medida)));
  const util = medidas.largura - medidas.esquerda - medidas.direita;
  const largura = (util - medidas.vao * (faixas.length - 1)) / faixas.length;
  const area = medidas.altura - medidas.topo - medidas.base;
  const colunas = faixas.map((faixa, indice) => {
    const valor = valorFaixa(faixa, medida);
    const altura = maior > 0 ? (valor / maior) * area : 0;
    const semVoto = medida === "votos" && faixa.chave === "zero";
    return {
      chave: faixa.chave,
      x: medidas.esquerda + indice * (largura + medidas.vao),
      y: medidas.topo + area - altura,
      largura,
      altura,
      valor: semVoto ? TRACO : formatarPercentualContagem(valor, total),
      neutra: faixa.chave === "zero",
      dica: [
        `${formatarInteiro(faixa.municipios)} municípios (${formatarPercentualContagem(faixa.municipios, totalMunicipios)})`,
        `${formatarInteiro(faixa.votos)} votos do partido (${formatarPercentualContagem(faixa.votos, totalVotos)})`,
      ],
    };
  });
  return { medidas, largura: medidas.largura, altura: medidas.altura, colunas };
}

function soma(valores: readonly number[]): number {
  return valores.reduce((total, valor) => total + valor, 0);
}

export function resumoRanking(partidos: readonly PartidoCapilaridade[]): string {
  const lista = ranqueaveis(partidos);
  if (lista.length === 0) {
    return "Nenhum partido teve voto bastante para entrar no ranking.";
  }
  const partes = lista.map(
    (item) => `${rotuloPartido(item.partido)}: ${item.indice_100} (${item.rotulo_classe})`,
  );
  return `Índice de concentração de 0 a 100 por partido. ${partes.join("; ")}.`;
}

export function resumoFaixas(partido: PartidoCapilaridade, medida: MedidaFaixa): string {
  const layout = layoutFaixas(partido.faixas, medida);
  const rotulo = rotuloPartido(partido.partido);
  const titulo =
    medida === "municipios"
      ? `Municípios de ${rotulo} por faixa de fatia, em vezes a fatia média do partido`
      : `Votos de ${rotulo} por faixa de fatia, em vezes a fatia média do partido`;
  if (layout === null) {
    return `${titulo}: sem dados.`;
  }
  const partes = layout.colunas.map((coluna) => `${ROTULOS_FAIXA[coluna.chave].longo}: ${coluna.valor}`);
  return `${titulo}. ${partes.join("; ")}.`;
}

export function leituraCapilaridade(
  partido: PartidoCapilaridade,
  recorte: Recorte,
  ufs: number,
): string[] {
  const rotulo = rotuloPartido(partido.partido);
  const base = `${rotulo} teve ${partido.fatia_texto} dos votos válidos no recorte ${recorte.nome}`;
  const primeira =
    partido.ufs_com_voto < ufs
      ? `${base}, contando só as ${partido.ufs_com_voto} UFs onde recebeu voto.`
      : `${base}.`;
  const top = partido.top10;
  return [
    primeira,
    `Os ${formatarInteiro(top.municipios)} municípios onde é mais forte deram ${top.parte_texto} dos votos dele. Eles têm ${top.eleitorado_texto} do eleitorado.`,
    `Teve pelo menos 5% dos votos em ${formatarInteiro(partido.presenca.municipios)} de ${formatarInteiro(partido.municipios)} municípios (${partido.presenca.parte_texto}).`,
    `Índice de concentração: ${partido.indice_100} de 100. ${partido.motivo}`,
  ];
}
