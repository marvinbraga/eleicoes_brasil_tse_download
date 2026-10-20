export type Direcao = "asc" | "desc";

export function textoOrdenavel(texto: string): string | null {
  const limpo = texto.trim();
  if (limpo.length === 0 || limpo === "—" || limpo === "-" || limpo === "–") {
    return null;
  }
  return limpo;
}

export function compararTexto(
  esquerda: string | null,
  direita: string | null,
  direcao: Direcao,
): number {
  if (esquerda === null && direita === null) {
    return 0;
  }
  if (esquerda === null) {
    return 1;
  }
  if (direita === null) {
    return -1;
  }
  const sinal = direcao === "asc" ? 1 : -1;
  return sinal * esquerda.localeCompare(direita, "pt-BR", { numeric: true, sensitivity: "base" });
}

export function compararNumero(
  esquerda: number | null,
  direita: number | null,
  direcao: Direcao,
): number {
  if (esquerda === null && direita === null) {
    return 0;
  }
  if (esquerda === null) {
    return 1;
  }
  if (direita === null) {
    return -1;
  }
  const sinal = direcao === "asc" ? 1 : -1;
  return sinal * (esquerda - direita);
}
