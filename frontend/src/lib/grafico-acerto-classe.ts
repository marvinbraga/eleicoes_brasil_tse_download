import { lerFatia } from "./fatia.ts";
import { formatarInteiro } from "./fracao.ts";
import { ancorarRotulo } from "./largura-texto.ts";
import type { LinhaClasseGovernador } from "./relatorios.ts";

export const LARGURA = 640,
  ESQUERDA = 150,
  DIREITA = 64,
  TOPO = 36,
  BASE = 28,
  ALTURA_LINHA = 44,
  ALTURA_BARRA = 18;

export type MedidasAcertoClasse = {
  largura: number;
  esquerda: number;
  direita: number;
  topo: number;
  base: number;
  alturaLinha: number;
  alturaBarra: number;
  limiteAncoraFim: number | null;
  fracoesMarcas: readonly number[];
  descidaMarca: number;
  deslocRotulo: number;
  deslocContagem: number;
  fonte: number;
  fonteMenor: number;
};

export const MEDIDAS_PADRAO: MedidasAcertoClasse = {
  largura: LARGURA,
  esquerda: ESQUERDA,
  direita: DIREITA,
  topo: TOPO,
  base: BASE,
  alturaLinha: ALTURA_LINHA,
  alturaBarra: ALTURA_BARRA,
  limiteAncoraFim: LARGURA - DIREITA - 110,
  fracoesMarcas: [0, 0.25, 0.5, 0.75, 1],
  descidaMarca: 16,
  deslocRotulo: -7,
  deslocContagem: 8,
  fonte: 12,
  fonteMenor: 11,
};

export const MEDIDAS_ESTREITO: MedidasAcertoClasse = {
  largura: 340,
  esquerda: 144,
  direita: 62,
  topo: 40,
  base: 30,
  alturaLinha: 50,
  alturaBarra: 18,
  limiteAncoraFim: null,
  fracoesMarcas: [0, 0.5, 1],
  descidaMarca: 18,
  deslocRotulo: -8,
  deslocContagem: 9,
  fonte: 13,
  fonteMenor: 13,
};

const MAIORIA = "marcar sempre a situação mais comum";
const LIDER = "seguir o partido que lidera para presidente";

export type EntradaGraficoClasse = {
  linhas: readonly LinhaClasseGovernador[];
  acerto: string;
  base: string;
  baseLider: string;
};

export type BarraClasse = {
  classe: string;
  rotulo: string;
  municipios: number;
  acertoTexto: string;
  fracao: number;
  x: number;
  largura: number;
  y: number;
};

export type ReferenciaClasse = {
  x: number;
  valorTexto: string;
  ancora: "start" | "end";
  xTexto: number;
};

export type LayoutAcertoClasse = {
  medidas: MedidasAcertoClasse;
  largura: number;
  altura: number;
  barras: BarraClasse[];
  referencia: ReferenciaClasse | null;
  marcas: { x: number; rotulo: string }[];
  descartadas: number;
};

type ClasseValida = Omit<BarraClasse, "x" | "largura" | "y">;
type Relacao = "menos do que" | "o mesmo que" | "mais do que";

export function layoutAcertoClasse(
  entrada: EntradaGraficoClasse,
  medidas: MedidasAcertoClasse = MEDIDAS_PADRAO,
): LayoutAcertoClasse | null {
  const validas = classesValidas(entrada.linhas);
  if (validas.length === 0) {
    return null;
  }
  const { esquerda, topo, alturaLinha, alturaBarra } = medidas;
  const geral = lerFatia(entrada.acerto);
  return {
    medidas,
    largura: medidas.largura,
    altura: topo + validas.length * alturaLinha + medidas.base,
    barras: validas.map((linha, indice) => ({
      ...linha,
      x: esquerda,
      largura: posicaoX(linha.fracao, medidas) - esquerda,
      y: topo + indice * alturaLinha + alturaLinha / 2 - alturaBarra / 2,
    })),
    referencia:
      geral === null
        ? null
        : {
            x: posicaoX(geral, medidas),
            valorTexto: entrada.acerto,
            ...ancorar(posicaoX(geral, medidas), `Acerto geral ${entrada.acerto}`, medidas),
          },
    marcas: medidas.fracoesMarcas.map((fracao) => ({
      x: posicaoX(fracao, medidas),
      rotulo: `${fracao * 100}%`,
    })),
    descartadas: entrada.linhas.length - validas.length,
  };
}

function ancorar(
  x: number,
  texto: string,
  medidas: MedidasAcertoClasse,
): { ancora: "start" | "end"; xTexto: number } {
  if (medidas.limiteAncoraFim === null) {
    return ancorarRotulo(x, medidas.largura, texto, medidas.fonteMenor);
  }
  return x > medidas.limiteAncoraFim ? { ancora: "end", xTexto: x - 4 } : { ancora: "start", xTexto: x + 4 };
}

export function frasesClasse(entrada: EntradaGraficoClasse): string[] {
  const frases: string[] = [];
  const geral = lerFatia(entrada.acerto);
  if (geral === null) {
    frases.push("Não há acerto geral neste recorte.");
  } else {
    frases.push(
      `No geral, o modelo acertou ${entrada.acerto} dos municípios. Cada estado foi testado sem que o modelo tivesse visto os municípios dele.`,
    );
    const comparacao = fraseBases(geral, entrada);
    if (comparacao !== null) {
      frases.push(comparacao);
    }
  }
  const validas = classesValidas(entrada.linhas);
  const melhor = validas[0];
  const pior = validas[validas.length - 1];
  if (melhor === undefined || pior === undefined) {
    return frases;
  }
  if (validas.length > 1 && melhor.fracao === pior.fracao) {
    frases.push(`O modelo acertou ${melhor.acertoTexto} em todas as situações.`);
    return frases;
  }
  frases.push(`Onde mais acerta: ${daSituacao(melhor)}, o modelo acertou ${melhor.acertoTexto}.`);
  if (validas.length > 1) {
    frases.push(`Onde mais erra: ${daSituacao(pior)}, ${erro(pior)}.`);
  }
  return frases;
}

export function resumoAcertoClasse(entrada: EntradaGraficoClasse): string {
  const partes = classesValidas(entrada.linhas).map(
    (linha) => `${linha.rotulo}: acertou ${linha.acertoTexto} de ${contagem(linha.municipios)}`,
  );
  if (partes.length === 0) {
    return "Nenhuma situação com acerto.";
  }
  return `Acerto geral ${entrada.acerto}. ${partes.join("; ")}.`;
}

function classesValidas(linhas: readonly LinhaClasseGovernador[]): ClasseValida[] {
  const validas: ClasseValida[] = [];
  for (const linha of linhas) {
    const fracao = lerFatia(linha.recall);
    if (fracao !== null) {
      validas.push({
        classe: linha.classe,
        rotulo: linha.rotulo,
        municipios: linha.apoio,
        acertoTexto: linha.recall,
        fracao: Math.min(1, fracao),
      });
    }
  }
  return validas
    .map((linha, indice) => ({ linha, indice }))
    .sort((a, b) => b.linha.fracao - a.linha.fracao || a.indice - b.indice)
    .map((item) => item.linha);
}

function posicaoX(fracao: number, medidas: MedidasAcertoClasse): number {
  const { esquerda, largura, direita } = medidas;
  return esquerda + Math.min(1, Math.max(0, fracao)) * (largura - esquerda - direita);
}

function fraseBases(geral: number, entrada: EntradaGraficoClasse): string | null {
  const bases = [
    { nome: MAIORIA, texto: entrada.base, fracao: lerFatia(entrada.base) },
    { nome: LIDER, texto: entrada.baseLider, fracao: lerFatia(entrada.baseLider) },
  ].flatMap((item) => (item.fracao === null ? [] : [{ ...item, relacao: relacao(geral, item.fracao) }]));
  const [primeira, segunda] = bases;
  if (primeira === undefined) {
    return null;
  }
  if (segunda === undefined) {
    return `Isso é ${primeira.relacao} ${primeira.nome}, que acertaria ${primeira.texto}.`;
  }
  if (primeira.relacao === segunda.relacao && primeira.relacao !== "o mesmo que") {
    return `Isso é ${primeira.relacao} dois chutes simples: ${primeira.nome} acertaria ${primeira.texto}, e ${segunda.nome} acertaria ${segunda.texto}.`;
  }
  const ligacao = primeira.relacao === segunda.relacao ? "e" : "mas";
  return `Isso é ${primeira.relacao} ${primeira.nome} (${primeira.texto}), ${ligacao} ${segunda.relacao} ${segunda.nome} (${segunda.texto}).`;
}

function relacao(geral: number, base: number): Relacao {
  if (Math.abs(geral - base) < 1e-9) {
    return "o mesmo que";
  }
  return geral < base ? "menos do que" : "mais do que";
}

function daSituacao(linha: ClasseValida): string {
  if (linha.municipios === 1) {
    return `do único município que era de fato “${linha.rotulo}”`;
  }
  return `dos ${formatarInteiro(linha.municipios)} municípios que eram de fato “${linha.rotulo}”`;
}

function erro(linha: ClasseValida): string {
  if (linha.fracao === 0) {
    return linha.municipios === 1 ? "o modelo não acertou" : "o modelo não acertou nenhum";
  }
  return `o modelo acertou só ${linha.acertoTexto}`;
}

function contagem(municipios: number): string {
  return `${formatarInteiro(municipios)} ${municipios === 1 ? "município" : "municípios"}`;
}
