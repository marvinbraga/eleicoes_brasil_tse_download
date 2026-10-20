export function lerFatia(texto: string): number | null {
  let corpo = texto.trim();
  if (corpo.endsWith("%")) {
    corpo = corpo.slice(0, -1).trim();
  }
  corpo = corpo.replace(",", ".");
  if (!/^\d+(?:\.\d+)?$/.test(corpo)) {
    return null;
  }
  const valor = Number(corpo);
  if (!Number.isFinite(valor)) {
    return null;
  }
  return valor / 100;
}
