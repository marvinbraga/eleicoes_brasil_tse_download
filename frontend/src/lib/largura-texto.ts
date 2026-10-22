const EM_POR_CARACTERE = 0.6;

export function larguraTexto(texto: string, fonte: number): number {
  return EM_POR_CARACTERE * fonte * texto.length;
}

export function ancorarRotulo(
  x: number,
  largura: number,
  texto: string,
  fonte: number,
): { ancora: "start" | "end"; xTexto: number } {
  const ocupa = larguraTexto(texto, fonte);
  if (x + 4 + ocupa <= largura) {
    return { ancora: "start", xTexto: x + 4 };
  }
  if (x - 4 - ocupa >= 0) {
    return { ancora: "end", xTexto: x - 4 };
  }
  return { ancora: "end", xTexto: largura };
}
