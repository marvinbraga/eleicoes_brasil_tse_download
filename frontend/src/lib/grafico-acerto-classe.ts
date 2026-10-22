import { lerFatia } from "./fatia.ts";
import { formatarInteiro } from "./fracao.ts";
import type { LinhaClasseGovernador } from "./relatorios.ts";

export const LARGURA = 640,
  ESQUERDA = 150,
  DIREITA = 64,
  TOPO = 36,
  BASE = 28,
  ALTURA_LINHA = 44,
  ALTURA_BARRA = 18;

const LIMITE_ANCORA_FIM = LARGURA - DIREITA - 110;
const FRACOES_MARCAS = [0, 0.25, 0.5, 0.75, 1];
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

export type ReferenciaClasse = { x: number; valorTexto: string; ancora: "start" | "end" };

export type LayoutAcertoClasse = {
  largura: number;
  altura: number;
  barras: BarraClasse[];
  referencia: ReferenciaClasse | null;
  marcas: { x: number; rotulo: string }[];
  descartadas: number;
};

type ClasseValida = Omit<BarraClasse, "x" | "largura" | "y">;
type Relacao = "menos do que" | "o mesmo que" | "mais do que";

export function layoutAcertoClasse(entrada: EntradaGraficoClasse): LayoutAcertoClasse | null {
  const validas = classesValidas(entrada.linhas);
  if (validas.length === 0) {
    return null;
  }
  const geral = lerFatia(entrada.acerto);
  return {
    largura: LARGURA,
    altura: TOPO + validas.length * ALTURA_LINHA + BASE,
    barras: validas.map((linha, indice) => ({
      ...linha,
      x: ESQUERDA,
      largura: posicaoX(linha.fracao) - ESQUERDA,
      y: TOPO + indice * ALTURA_LINHA + ALTURA_LINHA / 2 - ALTURA_BARRA / 2,
    })),
    referencia:
      geral === null
        ? null
        : {
            x: posicaoX(geral),
            valorTexto: entrada.acerto,
            ancora: posicaoX(geral) > LIMITE_ANCORA_FIM ? "end" : "start",
          },
    marcas: FRACOES_MARCAS.map((fracao) => ({ x: posicaoX(fracao), rotulo: `${fracao * 100}%` })),
    descartadas: entrada.linhas.length - validas.length,
  };
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

function posicaoX(fracao: number): number {
  return ESQUERDA + Math.min(1, Math.max(0, fracao)) * (LARGURA - ESQUERDA - DIREITA);
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
