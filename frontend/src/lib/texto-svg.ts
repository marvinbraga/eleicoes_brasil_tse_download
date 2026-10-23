// Textos de um gráfico SVG com posição, fonte e âncora, para desenhar e para medir.
// A medida é uma estimativa (larguraTexto: 0,6 em por caractere), de propósito folgada.
import { larguraTexto } from "./largura-texto.ts";

// Largura útil do gráfico num telefone de 375 px, descontados margens e respiro do cartão.
export const CONTEINER_ESTREITO = 301;
// Menor corpo de texto aceito no desenho, em px CSS.
export const FONTE_MINIMA = 11;

// Números como "−0,15" e "12,5" medem ~0,51 em por caractere no navegador (algarismos
// tabulares, vírgula estreita); "%" e letras ficam na estimativa geral de 0,6 em.
const EM_POR_CARACTERE_NUMERO = 0.56;
const NUMERO = /^[−\-\d.,]+$/;

const SUBIDA = 0.8;
const DESCIDA = 0.2;
const MEIO = 0.35;
// Sobreposição abaixo disto é arredondamento da estimativa, não colisão visível.
const TOLERANCIA = 1;

export type Ancora = "start" | "middle" | "end";

export type TextoSvg = {
  chave: string;
  texto: string;
  x: number;
  y: number;
  fonte: number;
  ancora: Ancora;
  // dy="0.35em": y é o meio da linha, não a base.
  centrado?: boolean;
  // Girado −90° em torno de (x, y), como o título de um eixo vertical.
  vertical?: boolean;
  // Só desenho: tinta do texto ("suave" = muted) e algarismos de largura fixa.
  tom: "forte" | "suave";
  tabular?: boolean;
};

export type Caixa = { x0: number; x1: number; y0: number; y1: number };

export function larguraEstimada(texto: string, fonte: number): number {
  return NUMERO.test(texto) ? EM_POR_CARACTERE_NUMERO * fonte * texto.length : larguraTexto(texto, fonte);
}

export function caixaTexto(texto: TextoSvg): Caixa {
  const largura = larguraEstimada(texto.texto, texto.fonte);
  const inicio = texto.ancora === "start" ? 0 : texto.ancora === "middle" ? -largura / 2 : -largura;
  const base = texto.centrado === true ? texto.y + MEIO * texto.fonte : texto.y;
  if (texto.vertical === true) {
    // rotate(−90): o sentido da leitura vira "para cima" e o topo das letras vira "para a esquerda".
    return {
      x0: texto.x - SUBIDA * texto.fonte,
      x1: texto.x + DESCIDA * texto.fonte,
      y0: texto.y - inicio - largura,
      y1: texto.y - inicio,
    };
  }
  return {
    x0: texto.x + inicio,
    x1: texto.x + inicio + largura,
    y0: base - SUBIDA * texto.fonte,
    y1: base + DESCIDA * texto.fonte,
  };
}

// Corpo do texto em px CSS quando o viewBox de largura `largura` é desenhado em `conteiner` px.
export function fonteEfetiva(fonte: number, largura: number, conteiner: number = CONTEINER_ESTREITO): number {
  return (fonte * conteiner) / largura;
}

export function menorFonteEfetiva(
  textos: readonly TextoSvg[],
  largura: number,
  conteiner: number = CONTEINER_ESTREITO,
): number {
  return Math.min(...textos.map((texto) => fonteEfetiva(texto.fonte, largura, conteiner)));
}

export function foraDoQuadro(textos: readonly TextoSvg[], largura: number, altura: number): TextoSvg[] {
  return textos.filter((texto) => {
    const caixa = caixaTexto(texto);
    return caixa.x0 < 0 || caixa.y0 < 0 || caixa.x1 > largura || caixa.y1 > altura;
  });
}

export function colisoes(textos: readonly TextoSvg[]): [string, string][] {
  const caixas = textos.map((texto) => ({ chave: texto.chave, caixa: caixaTexto(texto) }));
  const achadas: [string, string][] = [];
  caixas.forEach((a, indice) => {
    for (const b of caixas.slice(indice + 1)) {
      const largura = Math.min(a.caixa.x1, b.caixa.x1) - Math.max(a.caixa.x0, b.caixa.x0);
      const altura = Math.min(a.caixa.y1, b.caixa.y1) - Math.max(a.caixa.y0, b.caixa.y0);
      if (largura > TOLERANCIA && altura > TOLERANCIA) {
        achadas.push([a.chave, b.chave]);
      }
    }
  });
  return achadas;
}

// Tudo o que a variante estreita não pode ter, em frases; lista vazia = desenho aceito.
export function problemasEstreito(textos: readonly TextoSvg[], largura: number, altura: number): string[] {
  const menor = menorFonteEfetiva(textos, largura);
  return [
    ...(menor < FONTE_MINIMA ? [`menor fonte efetiva ${menor.toFixed(2)} px`] : []),
    ...foraDoQuadro(textos, largura, altura).map((texto) => `fora do viewBox: ${texto.chave}`),
    ...colisoes(textos).map(([a, b]) => `sobrepostos: ${a} e ${b}`),
  ];
}
