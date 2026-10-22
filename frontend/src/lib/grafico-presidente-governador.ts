import { INTENSIDADE, ORDEM_CLASSE, type ClasseCruzada } from "../cruzamento/finalidade.ts";
import { formatarPercentualContagem } from "./fracao.ts";
import type { GrupoMunicipios } from "./relatorios.ts";

export const LARGURA = 640,
  ALTURA_LINHA = 24,
  ALTURA_BARRA = 14,
  ESQUERDA_UF = 44,
  ESQUERDA_REGIAO = 96,
  DIREITA = 16,
  TOPO = 8,
  BASE = 28,
  VAO = 1;

const FRACOES_MARCAS = [0, 0.25, 0.5, 0.75, 1];

export const ROTULOS: Record<ClasseCruzada, string> = {
  consolidacao: "Consolidação",
  terreno_de_virada: "Terreno de virada",
  em_aberto: "Em aberto",
  sem_governador: "Sem governador",
};

const FECHO: Record<ClasseCruzada, string> = {
  consolidacao: "municípios em consolidação",
  terreno_de_virada: "municípios em terreno de virada",
  em_aberto: "municípios em aberto",
  sem_governador: "municípios sem governador",
};

const REGIOES: Record<string, readonly string[]> = {
  Norte: ["AC", "AM", "AP", "PA", "RO", "RR", "TO"],
  Nordeste: ["AL", "BA", "CE", "MA", "PB", "PE", "PI", "RN", "SE"],
  "Centro-Oeste": ["DF", "GO", "MS", "MT"],
  Sudeste: ["ES", "MG", "RJ", "SP"],
  Sul: ["PR", "RS", "SC"],
};

const REGIAO_DA_UF = new Map(
  Object.entries(REGIOES).flatMap(([regiao, ufs]) => ufs.map((uf) => [uf, regiao] as const)),
);

type Unidade = "UFs" | "regiões";

const SINGULAR: Record<Unidade, string> = { UFs: "UF", "regiões": "região" };

export type ComposicaoLugar = {
  codigo: string;
  votos: Record<ClasseCruzada, number>;
  total: number;
};

export type FatiaBarra = {
  classe: ClasseCruzada;
  votos: number;
  fatiaTexto: string;
  x: number;
  largura: number;
  opacidade: number;
};

export type BarraLugar = { codigo: string; total: number; y: number; fatias: FatiaBarra[] };

export type LayoutComposicao = {
  largura: number;
  altura: number;
  esquerda: number;
  barras: BarraLugar[];
  marcas: { x: number; rotulo: string }[];
};

export function composicaoPorUf(grupos: readonly GrupoMunicipios[]): ComposicaoLugar[] {
  const lugares: ComposicaoLugar[] = [];
  for (const grupo of grupos) {
    if (!REGIAO_DA_UF.has(grupo.uf)) {
      continue;
    }
    const lugar = vazio(grupo.uf);
    for (const municipio of grupo.places) {
      if (eClasse(municipio.classe)) {
        lugar.votos[municipio.classe] += municipio.presidente.valid;
        lugar.total += municipio.presidente.valid;
      }
    }
    if (lugar.total > 0) {
      lugares.push(lugar);
    }
  }
  return ordenar(lugares);
}

export function composicaoPorRegiao(porUf: readonly ComposicaoLugar[]): ComposicaoLugar[] {
  const regioes = new Map<string, ComposicaoLugar>();
  for (const uf of porUf) {
    const nome = REGIAO_DA_UF.get(uf.codigo);
    if (nome === undefined) {
      continue;
    }
    const regiao = regioes.get(nome) ?? vazio(nome);
    for (const classe of ORDEM_CLASSE) {
      regiao.votos[classe] += uf.votos[classe];
    }
    regiao.total += uf.total;
    regioes.set(nome, regiao);
  }
  return ordenar([...regioes.values()]);
}

export function layoutComposicao(
  lugares: readonly ComposicaoLugar[],
  esquerda: number,
): LayoutComposicao | null {
  if (lugares.length === 0) {
    return null;
  }
  const plotagem = LARGURA - esquerda - DIREITA;
  const barras = lugares.map((lugar, indice) => ({
    codigo: lugar.codigo,
    total: lugar.total,
    y: TOPO + indice * ALTURA_LINHA + (ALTURA_LINHA - ALTURA_BARRA) / 2,
    fatias: fatiasDe(lugar, esquerda, plotagem),
  }));
  return {
    largura: LARGURA,
    altura: TOPO + barras.length * ALTURA_LINHA + BASE,
    esquerda,
    barras,
    marcas: FRACOES_MARCAS.map((fracao) => ({
      x: esquerda + fracao * plotagem,
      rotulo: `${fracao * 100}%`,
    })),
  };
}

export function frasesComposicao(lugares: readonly ComposicaoLugar[], unidade: Unidade): string[] {
  const n = lugares.length;
  if (n === 0) {
    return [];
  }
  return [frasePluralidade(lugares, unidade), fraseConsolidacao(lugares, unidade)];
}

export function resumoComposicao(lugares: readonly ComposicaoLugar[], unidade: Unidade): string {
  return [
    `${lugares.length} ${unidade}, da maior para a menor fatia de consolidação.`,
    ...frasesComposicao(lugares, unidade),
  ].join(" ");
}

function frasePluralidade(lugares: readonly ComposicaoLugar[], unidade: Unidade): string {
  const contagem = new Map<ClasseCruzada, number>();
  for (const lugar of lugares) {
    const classe = maiorClasse(lugar);
    contagem.set(classe, (contagem.get(classe) ?? 0) + 1);
  }
  const ranking = ORDEM_CLASSE.flatMap((classe) => {
    const total = contagem.get(classe) ?? 0;
    return total > 0 ? [{ classe, total }] : [];
  }).sort((a, b) => b.total - a.total);
  const [primeira, ...outras] = ranking;
  if (primeira === undefined) {
    return "";
  }
  const n = lugares.length;
  const frase = `Em ${primeira.total} de ${n} ${unidade} a maior parte dos votos válidos de presidente está em ${FECHO[primeira.classe]}.`;
  const resto = n - primeira.total;
  const abertura = resto === 1 ? "Na outra" : `Nas outras ${resto}`;
  const [unica] = outras;
  if (unica === undefined) {
    return frase;
  }
  if (outras.length === 1) {
    return `${frase} ${abertura}, está em ${FECHO[unica.classe]}.`;
  }
  const lista = outras.map((outra) => `${ROTULOS[outra.classe]} (${outra.total})`);
  return `${frase} ${abertura}, a maior fatia é ${juntar(lista, "ou")}.`;
}

function fraseConsolidacao(lugares: readonly ComposicaoLugar[], unidade: Unidade): string {
  const comVoto = lugares.filter((lugar) => lugar.votos.consolidacao > 0);
  const topo = comVoto[0];
  const fundo = comVoto[comVoto.length - 1];
  if (topo === undefined || fundo === undefined) {
    return `Nenhuma ${SINGULAR[unidade]} tem voto em municípios em consolidação.`;
  }
  const empatadas = (alvo: ComposicaoLugar) =>
    juntar(
      comVoto.filter((lugar) => comparar(lugar, alvo) === 0).map((lugar) => lugar.codigo),
      "e",
    );
  const frase = `Maior fatia de consolidação: ${empatadas(topo)}, com ${fatiaConsolidacao(topo)}.`;
  const zeros = lugares.length - comVoto.length;
  const unicaFaixa = comparar(topo, fundo) === 0;
  if (zeros > 0) {
    const nenhum = `Em ${zeros} de ${lugares.length} ${unidade} nenhum voto está em municípios em consolidação`;
    if (unicaFaixa) {
      return `${frase} ${nenhum}.`;
    }
    return `${frase} ${nenhum}; entre as demais, a menor é ${empatadas(fundo)}, com ${fatiaConsolidacao(fundo)}.`;
  }
  if (unicaFaixa) {
    return frase;
  }
  return `${frase} Menor: ${empatadas(fundo)}, com ${fatiaConsolidacao(fundo)}.`;
}

function fatiasDe(lugar: ComposicaoLugar, esquerda: number, plotagem: number): FatiaBarra[] {
  const ultimaComVoto = ORDEM_CLASSE.reduce<ClasseCruzada | null>(
    (ultima, classe) => (lugar.votos[classe] > 0 ? classe : ultima),
    null,
  );
  let acumulado = 0;
  let fimAnterior: number | null = null;
  return ORDEM_CLASSE.map((classe) => {
    const votos = lugar.votos[classe];
    const natural = esquerda + (acumulado * plotagem) / lugar.total;
    acumulado += votos;
    const borda = esquerda + (acumulado * plotagem) / lugar.total;
    const vao = votos > 0 ? VAO : 0;
    const x = fimAnterior === null ? natural : Math.max(natural, fimAnterior + vao);
    let largura = 0;
    if (votos > 0) {
      largura = classe === ultimaComVoto ? Math.max(1, borda - x) : Math.max(1, borda - x - VAO);
      fimAnterior = x + largura;
    }
    return {
      classe,
      votos,
      fatiaTexto: formatarPercentualContagem(votos, lugar.total),
      x,
      largura,
      opacidade: INTENSIDADE[classe],
    };
  });
}

function maiorClasse(lugar: ComposicaoLugar): ClasseCruzada {
  return ORDEM_CLASSE.reduce((melhor, classe) =>
    lugar.votos[classe] > lugar.votos[melhor] ? classe : melhor,
  );
}

function ordenar(lugares: ComposicaoLugar[]): ComposicaoLugar[] {
  return lugares.sort(
    (a, b) => comparar(b, a) || a.codigo.localeCompare(b.codigo, "pt-BR"),
  );
}

function comparar(a: ComposicaoLugar, b: ComposicaoLugar): number {
  const esquerda = BigInt(a.votos.consolidacao) * BigInt(b.total);
  const direita = BigInt(b.votos.consolidacao) * BigInt(a.total);
  return esquerda === direita ? 0 : esquerda > direita ? 1 : -1;
}

function fatiaConsolidacao(lugar: ComposicaoLugar): string {
  return formatarPercentualContagem(lugar.votos.consolidacao, lugar.total);
}

function vazio(codigo: string): ComposicaoLugar {
  return {
    codigo,
    votos: { consolidacao: 0, terreno_de_virada: 0, em_aberto: 0, sem_governador: 0 },
    total: 0,
  };
}

function eClasse(classe: string): classe is ClasseCruzada {
  return (ORDEM_CLASSE as readonly string[]).includes(classe);
}

function juntar(nomes: readonly string[], conector: string): string {
  if (nomes.length <= 1) {
    return nomes[0] ?? "";
  }
  const ultimo = nomes[nomes.length - 1] ?? "";
  return `${nomes.slice(0, -1).join(", ")} ${conector} ${ultimo}`;
}
