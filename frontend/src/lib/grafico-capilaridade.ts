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
import type { TextoSvg } from "./texto-svg.ts";

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
  // Números da escala (0, 25, …, 100) no topo.
  fonteMarca: number;
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
  fonteMarca: 11,
};

// Estreito (375 px): rótulo e classe acima da barra; só o valor à direita. O viewBox fica em
// 340 (fonte 13 → 11,5 px em ~301 px): a classe que não cabe na linha do rótulo desce para
// linhas próprias em vez de alargar o desenho. A esquerda deixa a metade do "0" da escala.
export const MEDIDAS_RANKING_ESTREITO: MedidasRanking = {
  largura: 340,
  esquerda: 6,
  direita: 40,
  topo: 22,
  base: 4,
  alturaLinha: 40,
  alturaBarra: 12,
  descida: 18,
  rotuloAcima: true,
  fonte: 13,
  fonteMarca: 13,
};

const ESCALA_INDICE = 100;
const MARCAS_INDICE = [0, 25, 50, 75, 100] as const;
const FOLGA_TEXTO = 8;

export type BarraRanking = {
  partido: number;
  rotulo: string;
  classe: string;
  // Estreito: classe na linha do rótulo ("PL 22 · Nacional / espalhado") ou em linhas abaixo dele.
  classeNaLinha: boolean;
  linhasClasse: string[];
  valor: number;
  // Topo e altura da faixa clicável da linha; y é o topo da barra.
  topoLinha: number;
  alturaLinha: number;
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
  const passo = passoRotulo(medidas);
  let topoLinha = medidas.topo;
  const barras = lista.map((item) => {
    const rotulo = rotuloPartido(item.partido);
    const linhasClasse = medidas.rotuloAcima ? classeAbaixo(rotulo, item.rotulo_classe, medidas) : [];
    const extra = linhasClasse.length * passo;
    const barra = {
      partido: item.partido,
      rotulo,
      classe: item.rotulo_classe,
      classeNaLinha: linhasClasse.length === 0,
      linhasClasse,
      valor: item.indice_100,
      topoLinha,
      alturaLinha: medidas.alturaLinha + extra,
      y: topoLinha + extra + medidas.descida,
      largura: (limitar(item.indice_100) / ESCALA_INDICE) * util,
      selecionado: item.partido === selecionado,
      href: href(item.partido),
      dica: dicaRanking(item),
    };
    topoLinha += barra.alturaLinha;
    return barra;
  });
  const marcas = MARCAS_INDICE.map((valor) => ({
    x: medidas.esquerda + (valor / ESCALA_INDICE) * util,
    texto: String(valor),
  }));
  return {
    medidas,
    largura: Math.max(medidas.largura, larguraNecessaria(barras, medidas, util)),
    altura: topoLinha + medidas.base,
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

function passoRotulo(medidas: MedidasRanking): number {
  return medidas.fonte + 2;
}

// Estreito: [] se "rótulo · classe" cabe numa linha; senão a classe quebrada por palavras.
function classeAbaixo(rotulo: string, classe: string, medidas: MedidasRanking): string[] {
  const cabe = medidas.largura - medidas.esquerda - FOLGA_TEXTO;
  if (larguraTexto(`${rotulo} · ${classe}`, medidas.fonte) <= cabe) {
    return [];
  }
  const linhas: string[] = [];
  for (const palavra of classe.split(" ")) {
    const atual = linhas.at(-1);
    if (atual !== undefined && larguraTexto(`${atual} ${palavra}`, medidas.fonte) <= cabe) {
      linhas[linhas.length - 1] = `${atual} ${palavra}`;
    } else {
      linhas.push(palavra);
    }
  }
  return linhas;
}

// Linhas acima da barra no estreito: o rótulo (com a classe, se couber) e as linhas da classe.
export function linhasAcima(
  barra: BarraRanking,
  medidas: MedidasRanking,
): { texto: string; y: number; classe: boolean }[] {
  const passo = passoRotulo(medidas);
  const ultima = barra.y - 5;
  const total = 1 + barra.linhasClasse.length;
  const rotulo = barra.classeNaLinha ? `${barra.rotulo} · ${barra.classe}` : barra.rotulo;
  return [rotulo, ...barra.linhasClasse].map((texto, indice) => ({
    texto,
    y: ultima - (total - 1 - indice) * passo,
    classe: indice > 0,
  }));
}

// Todos os textos do ranking, na posição em que o componente os desenha.
export function textosRanking(layout: LayoutRanking): TextoSvg[] {
  const { medidas, marcas, barras } = layout;
  const marcasTexto = marcas.map(
    (marca): TextoSvg => ({
      chave: `marca-${marca.texto}`,
      texto: marca.texto,
      x: marca.x,
      y: medidas.topo - 8,
      fonte: medidas.fonteMarca,
      ancora: "middle",
      tom: "suave",
      tabular: true,
    }),
  );
  const porBarra = barras.flatMap((barra): TextoSvg[] => {
    const meio = barra.y + medidas.alturaBarra / 2;
    const valor: TextoSvg = {
      chave: `valor-${barra.partido}`,
      texto: textoDireita(barra, medidas),
      x: medidas.esquerda + barra.largura + 6,
      y: meio,
      fonte: medidas.fonte,
      ancora: "start",
      centrado: true,
      tom: "forte",
      tabular: true,
    };
    if (!medidas.rotuloAcima) {
      return [
        {
          chave: `rotulo-${barra.partido}`,
          texto: barra.rotulo,
          x: medidas.esquerda - 8,
          y: meio,
          fonte: medidas.fonte,
          ancora: "end",
          centrado: true,
          tom: "forte",
        },
        valor,
      ];
    }
    const acima = linhasAcima(barra, medidas).map(
      (linha, indice): TextoSvg => ({
        chave: `rotulo-${barra.partido}-${indice}`,
        texto: linha.texto,
        x: medidas.esquerda,
        y: linha.y,
        fonte: medidas.fonte,
        ancora: "start",
        tom: linha.classe ? "suave" : "forte",
      }),
    );
    return [...acima, valor];
  });
  return [...marcasTexto, ...porBarra];
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
  // Rótulos das faixas embaixo ("<½", "3+").
  fonte: number;
  // Valor sobre a coluna e título do eixo.
  fonteValor: number;
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
  fonteValor: 10,
};

// Estreito: fonte 13 no viewBox de 340 dá 11,5 px em ~301 px; a base cresce com a fonte e as
// margens laterais deixam caber "100,00%" centrado na primeira e na última coluna.
export const MEDIDAS_FAIXAS_ESTREITO: MedidasFaixas = {
  largura: 340,
  altura: 176,
  esquerda: 6,
  direita: 6,
  topo: 18,
  base: 42,
  vao: 2,
  fonte: 13,
  fonteValor: 13,
};

export const TITULO_EIXO_FAIXAS = "vezes a fatia média do partido";

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

// Todos os textos de um painel de faixas, na posição em que o componente os desenha.
export function textosFaixas(layout: LayoutFaixas): TextoSvg[] {
  const { medidas, largura, altura, colunas } = layout;
  const chao = altura - medidas.base;
  const porColuna = colunas.flatMap((coluna): TextoSvg[] => {
    const centro = coluna.x + coluna.largura / 2;
    return [
      {
        chave: `valor-${coluna.chave}`,
        texto: coluna.valor,
        x: centro,
        y: coluna.y - 4,
        fonte: medidas.fonteValor,
        ancora: "middle",
        tom: "forte",
        tabular: true,
      },
      {
        chave: `faixa-${coluna.chave}`,
        texto: ROTULOS_FAIXA[coluna.chave].curto,
        x: centro,
        y: chao + medidas.fonte + 3,
        fonte: medidas.fonte,
        ancora: "middle",
        tom: "suave",
      },
    ];
  });
  return [
    ...porColuna,
    {
      chave: "eixo",
      texto: TITULO_EIXO_FAIXAS,
      x: largura / 2,
      y: altura - 6,
      fonte: medidas.fonteValor,
      ancora: "middle",
      tom: "suave",
    },
  ];
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
