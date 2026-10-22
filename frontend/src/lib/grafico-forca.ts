// Layout do gráfico do placar de força: um painel por esfera, um grupo por partido
// e uma barra por indicador, cada uma como fração do total da esfera (escala fixa, F14).
import type { Coluna, Esfera, LinhaPlacar } from "./placar-forca.ts";

export type MedidasGrupos = {
  largura: number;
  esquerda: number;
  direita: number;
  topo: number;
  base: number;
  alturaCabeca: number;
  alturaBarra: number;
  passo: number;
  espaco: number;
  rotuloAcima: boolean;
  fonte: number;
};

export const MEDIDAS_PADRAO: MedidasGrupos = {
  largura: 640,
  esquerda: 132,
  direita: 112,
  topo: 4,
  base: 4,
  alturaCabeca: 22,
  alturaBarra: 12,
  passo: 18,
  espaco: 10,
  rotuloAcima: false,
  fonte: 12,
};

export const MEDIDAS_ESTREITO: MedidasGrupos = {
  largura: 340,
  esquerda: 2,
  direita: 96,
  topo: 4,
  base: 4,
  alturaCabeca: 22,
  alturaBarra: 10,
  passo: 30,
  espaco: 10,
  rotuloAcima: true,
  fonte: 13,
};

export const LIMITE_GRUPOS = 8;

export const OPACIDADES = [1, 0.7, 0.45, 0.3] as const;

// Com o rótulo acima, a barra desce dentro do passo para dar lugar ao texto.
export const DESCIDA_ROTULO_ACIMA = 14;

export type Metrica = { chave: string; curto: string; fracao: number; texto: string; detalhe: string };

export type Grupo = { chave: string; rotulo: string; metricas: Metrica[] };

export type BarraDesenhada = Metrica & { y: number; largura: number; opacidade: number };

export type GrupoDesenhado = { chave: string; rotulo: string; yCabeca: number; barras: BarraDesenhada[] };

export type LayoutGrupos = { medidas: MedidasGrupos; largura: number; altura: number; grupos: GrupoDesenhado[] };

export function gruposEsfera(
  linhas: readonly LinhaPlacar[],
  colunas: readonly Coluna[],
  esfera: Esfera,
  limite: number = LIMITE_GRUPOS,
): Grupo[] {
  const daEsfera = colunas.filter((coluna) => coluna.esfera === esfera);
  return linhas
    .map((linha) => ({
      chave: linha.chave,
      rotulo: linha.rotulo,
      metricas: daEsfera.flatMap((coluna): Metrica[] => {
        const valor = linha.valores[coluna.chave];
        return valor.fracao === null
          ? []
          : [
              {
                chave: coluna.chave,
                curto: coluna.curto,
                fracao: valor.fracao,
                texto: valor.texto,
                detalhe: valor.detalhe,
              },
            ];
      }),
    }))
    .filter((grupo) => grupo.metricas.length > 0)
    .slice(0, limite);
}

export function layoutGrupos(
  grupos: readonly Grupo[],
  medidas: MedidasGrupos = MEDIDAS_PADRAO,
): LayoutGrupos | null {
  if (grupos.length === 0) {
    return null;
  }
  const util = medidas.largura - medidas.esquerda - medidas.direita;
  const descida = medidas.rotuloAcima ? DESCIDA_ROTULO_ACIMA : 0;
  let cursor = medidas.topo;
  const desenhados = grupos.map((grupo) => {
    const yCabeca = cursor;
    cursor += medidas.alturaCabeca + grupo.metricas.length * medidas.passo + medidas.espaco;
    return {
      chave: grupo.chave,
      rotulo: grupo.rotulo,
      yCabeca,
      barras: grupo.metricas.map((metrica, indice) => ({
        ...metrica,
        y: yCabeca + medidas.alturaCabeca + indice * medidas.passo + descida,
        largura: limitar(metrica.fracao) * util,
        opacidade: OPACIDADES[Math.min(indice, OPACIDADES.length - 1)],
      })),
    };
  });
  return { medidas, largura: medidas.largura, altura: cursor + medidas.base, grupos: desenhados };
}

export function resumoGrupos(titulo: string, grupos: readonly Grupo[]): string {
  const partes = grupos
    .map((grupo) => `${grupo.rotulo}: ${grupo.metricas.map((m) => `${m.curto} ${m.texto}`).join(", ")}`)
    .join("; ");
  return partes === "" ? `${titulo}.` : `${titulo}. ${partes}.`;
}

function limitar(fracao: number): number {
  if (!Number.isFinite(fracao) || fracao <= 0) {
    return 0;
  }
  return Math.min(1, fracao);
}
