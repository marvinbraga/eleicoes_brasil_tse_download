import { lerFatia } from "./fatia.ts";
import { formatarInteiro, formatarPercentualContagem, TRACO } from "./fracao.ts";
import { rotuloPartido } from "./partidos.ts";
import type { GrupoPerfil } from "./relatorios.ts";

export const LARGURA = 680,
  ESQUERDA = 112,
  LARGURA_MISTURA = 220,
  X_PESO_ROTULO = 412,
  X_PESO = 476,
  LARGURA_PESO = 140,
  TOPO = 28,
  CABECA = 22,
  PASSO = 18,
  ALTURA_BARRA = 12,
  ESPACO = 14,
  BASE = 8,
  ALTURA_BLOCO_BASE = 2,
  MAXIMO_PARTIDOS = 5;

export const TONS = [100, 78, 56, 36, 18] as const;

export type MedidasPerfis = {
  largura: number;
  esquerda: number;
  larguraMistura: number;
  xPesoRotulo: number;
  xPeso: number;
  larguraPeso: number;
  topo: number;
  cabeca: number;
  passo: number;
  alturaBarra: number;
  espaco: number;
  base: number;
  vaoPeso: number;
  pesoAbaixo: boolean;
  fonte: number;
  fonteGrupo: number;
  cabecalhos: readonly [{ x: number; y: number }, { x: number; y: number }];
  alvoMistura: number;
  alvoPeso: { x: number; largura: number };
};

export const MEDIDAS_PADRAO: MedidasPerfis = {
  largura: LARGURA,
  esquerda: ESQUERDA,
  larguraMistura: LARGURA_MISTURA,
  xPesoRotulo: X_PESO_ROTULO,
  xPeso: X_PESO,
  larguraPeso: LARGURA_PESO,
  topo: TOPO,
  cabeca: CABECA,
  passo: PASSO,
  alturaBarra: ALTURA_BARRA,
  espaco: ESPACO,
  base: BASE,
  vaoPeso: 0,
  pesoAbaixo: false,
  fonte: 11,
  fonteGrupo: 13,
  cabecalhos: [
    { x: ESQUERDA, y: 14 },
    { x: X_PESO_ROTULO, y: 14 },
  ],
  alvoMistura: X_PESO_ROTULO - 8,
  alvoPeso: { x: X_PESO_ROTULO - 4, largura: X_PESO + LARGURA_PESO + 60 - X_PESO_ROTULO },
};

export const MEDIDAS_ESTREITO: MedidasPerfis = {
  largura: 340,
  esquerda: 134,
  larguraMistura: 144,
  xPesoRotulo: 0,
  xPeso: 134,
  larguraPeso: 144,
  topo: 44,
  cabeca: 24,
  passo: 20,
  alturaBarra: 13,
  espaco: 18,
  base: 8,
  vaoPeso: 8,
  pesoAbaixo: true,
  fonte: 13,
  fonteGrupo: 14,
  cabecalhos: [
    { x: 0, y: 14 },
    { x: 0, y: 31 },
  ],
  alvoMistura: 340,
  alvoPeso: { x: 0, largura: 340 },
};

export type EntradaPerfis = {
  partidos: readonly number[];
  grupos: readonly GrupoPerfil[];
};

export type BarraMistura = {
  chave: string;
  rotulo: string;
  titulo: string;
  texto: string;
  fracao: number;
  y: number;
  largura: number;
  tom: number | null;
};

export type BarraPeso = {
  rotulo: "Municípios" | "Votantes";
  texto: string;
  contagem: number;
  fracao: number;
  y: number;
  largura: number;
};

export type BlocoPerfil = {
  numero: number;
  y: number;
  municipios: number;
  comparecimento: number;
  barras: BarraMistura[];
  peso: BarraPeso[];
};

export type LayoutPerfis = {
  medidas: MedidasPerfis;
  largura: number;
  altura: number;
  teto: number;
  tetoTexto: string;
  restantes: number;
  blocos: BlocoPerfil[];
};

type Fatia = { texto: string; fracao: number };

export function principaisPerfis(entrada: EntradaPerfis): number[] {
  return indicesPrincipais(entrada).map((indice) => entrada.partidos[indice] ?? 0);
}

export function layoutPerfis(
  entrada: EntradaPerfis,
  medidas: MedidasPerfis = MEDIDAS_PADRAO,
): LayoutPerfis | null {
  const { partidos, grupos } = entrada;
  if (partidos.length === 0 || grupos.length === 0) {
    return null;
  }
  const principais = indicesPrincipais(entrada);
  const escolhidos = new Set(principais);
  const resto = partidos.map((_, indice) => indice).filter((indice) => !escolhidos.has(indice));
  const somasResto = grupos.map((grupo) =>
    resto.reduce((soma, indice) => soma + fatiaDe(grupo, indice).fracao, 0),
  );
  const comOutros = somasResto.some((soma) => soma > 0);
  const linhas = principais.length + (comOutros ? 1 : 0);
  const { topo, cabeca, passo, espaco } = medidas;
  const alturaBloco = medidas.pesoAbaixo
    ? cabeca + (linhas + 2) * passo + medidas.vaoPeso
    : cabeca + Math.max(linhas, ALTURA_BLOCO_BASE) * passo;
  const totalMunicipios = grupos.reduce((soma, grupo) => soma + grupo.municipios, 0);
  const totalComparecimento = grupos.reduce((soma, grupo) => soma + grupo.comparecimento, 0);

  const brutos = grupos.map((grupo, posicao) => {
    const fatias: Omit<BarraMistura, "y" | "largura">[] = principais.map((indice, tom) => {
      const partido = partidos[indice] ?? 0;
      return {
        chave: `p${partido}`,
        rotulo: rotuloPartido(partido),
        titulo: rotuloPartido(partido),
        ...fatiaDe(grupo, indice),
        tom,
      };
    });
    if (comOutros) {
      const soma = somasResto[posicao] ?? 0;
      fatias.push({
        chave: "outros",
        rotulo: "Outros",
        titulo: `Outros ${resto.length} ${resto.length === 1 ? "partido" : "partidos"}`,
        texto: percentual(soma),
        fracao: soma,
        tom: null,
      });
    }
    return fatias;
  });
  const maior = Math.max(0, ...brutos.flat().map((barra) => barra.fracao));
  const teto = Math.min(1, Math.max(0.1, Math.ceil(Math.round(maior * 1e6) / 1e5) / 10));

  const blocos = grupos.map((grupo, posicao) => {
    const y = topo + posicao * (alturaBloco + espaco);
    const linhaY = (linha: number) => y + cabeca + linha * passo;
    const barras = (brutos[posicao] ?? []).map((barra, linha) => ({
      ...barra,
      y: linhaY(linha),
      largura: (barra.fracao / teto) * medidas.larguraMistura,
    }));
    const yPeso = medidas.pesoAbaixo ? linhaY(linhas) + medidas.vaoPeso : linhaY(0);
    const peso: BarraPeso[] = [
      pesoDe("Municípios", grupo.municipios, totalMunicipios, yPeso, medidas.larguraPeso),
      pesoDe("Votantes", grupo.comparecimento, totalComparecimento, yPeso + passo, medidas.larguraPeso),
    ];
    return {
      numero: grupo.numero,
      y,
      municipios: grupo.municipios,
      comparecimento: grupo.comparecimento,
      barras,
      peso,
    };
  });

  return {
    medidas,
    largura: medidas.largura,
    altura: topo + grupos.length * alturaBloco + (grupos.length - 1) * espaco + medidas.base,
    teto,
    tetoTexto: `${Math.round(teto * 100)}%`,
    restantes: resto.length,
    blocos,
  };
}

export function resumoPerfis(entrada: EntradaPerfis): string {
  if (entrada.grupos.length === 0) {
    return "Nenhum grupo.";
  }
  const frases = [
    `${entrada.grupos.length} ${entrada.grupos.length === 1 ? "grupo" : "grupos"}.`,
    `Partidos no gráfico: ${juntar(principaisPerfis(entrada).map(rotuloPartido))}.`,
  ];
  for (const grupo of entrada.grupos) {
    const lider = liderDe(entrada.partidos, grupo);
    const base = `Grupo ${grupo.numero}: ${formatarInteiro(grupo.municipios)} municípios`;
    frases.push(lider === null ? `${base}.` : `${base}, lidera o ${rotuloPartido(lider.partido)} com ${lider.texto}.`);
  }
  return frases.join(" ");
}

export function leituraSeparacao(silhueta: string | null): string | null {
  if (silhueta === null) {
    return null;
  }
  const corpo = silhueta.trim().replace(",", ".");
  if (!/^-?\d+(?:\.\d+)?$/.test(corpo)) {
    return null;
  }
  const valor = Math.round(Number(corpo) * 100) / 100;
  if (!Number.isFinite(valor)) {
    return null;
  }
  const texto = Math.abs(valor).toFixed(2).replace(".", ",");
  if (valor < 0) {
    return `A separação entre os grupos é −${texto}, abaixo de zero: os grupos se confundem.`;
  }
  return `A separação entre os grupos é ${texto}, numa escala de 0 a 1: ${faixaSeparacao(valor)}.`;
}

export function liderDe(
  partidos: readonly number[],
  grupo: GrupoPerfil,
): { partido: number; texto: string } | null {
  let melhor: { partido: number; texto: string } | null = null;
  let maior = -1;
  for (let indice = 0; indice < partidos.length; indice += 1) {
    const texto = grupo.centro[indice];
    const fracao = texto === undefined ? null : lerFatia(texto);
    if (texto !== undefined && fracao !== null && fracao > maior) {
      melhor = { partido: partidos[indice] ?? 0, texto };
      maior = fracao;
    }
  }
  return melhor;
}

function faixaSeparacao(valor: number): string {
  if (valor < 0.25) {
    return "os grupos quase não se distinguem";
  }
  if (valor < 0.5) {
    return "os grupos se parecem em parte";
  }
  if (valor < 0.7) {
    return "os grupos são bem diferentes entre si";
  }
  return "os grupos são muito diferentes entre si";
}

function indicesPrincipais(entrada: EntradaPerfis): number[] {
  const lideres = new Set(
    entrada.grupos.flatMap((grupo) => {
      const lider = liderDe(entrada.partidos, grupo);
      return lider === null ? [] : [lider.partido];
    }),
  );
  const limite = Math.max(MAXIMO_PARTIDOS, lideres.size);
  const ordenados = entrada.partidos
    .map((partido, indice) => ({
      partido,
      indice,
      peso: entrada.grupos.reduce(
        (soma, grupo) => soma + fatiaDe(grupo, indice).fracao * grupo.comparecimento,
        0,
      ),
    }))
    .sort((a, b) => b.peso - a.peso || a.partido - b.partido);
  const vagas = limite - lideres.size;
  let extras = 0;
  return ordenados
    .filter((item) => {
      if (lideres.has(item.partido)) {
        return true;
      }
      extras += 1;
      return extras <= vagas;
    })
    .map((item) => item.indice);
}

function fatiaDe(grupo: GrupoPerfil, indice: number): Fatia {
  const texto = grupo.centro[indice];
  const fracao = texto === undefined ? null : lerFatia(texto);
  if (texto === undefined || fracao === null) {
    return { texto: TRACO, fracao: 0 };
  }
  return { texto, fracao };
}

function pesoDe(
  rotulo: BarraPeso["rotulo"],
  contagem: number,
  total: number,
  y: number,
  larguraPeso: number,
): BarraPeso {
  const fracao = total > 0 ? contagem / total : 0;
  return {
    rotulo,
    texto: formatarPercentualContagem(contagem, total),
    contagem,
    fracao,
    y,
    largura: fracao * larguraPeso,
  };
}

function percentual(fracao: number): string {
  return `${(Math.round(fracao * 10000) / 100).toFixed(2).replace(".", ",")}%`;
}

function juntar(nomes: readonly string[]): string {
  if (nomes.length <= 1) {
    return nomes[0] ?? "";
  }
  return `${nomes.slice(0, -1).join(", ")} e ${nomes[nomes.length - 1] ?? ""}`;
}
