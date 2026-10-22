// Partidos registrados no TSE em 2026. O 14 é o Missão desde 4/11/2025 e o 35 virou Democrata em 2/12/2025.
export const SIGLAS_PARTIDOS: Readonly<Record<number, string>> = {
  10: "REPUBLICANOS",
  11: "PP",
  12: "PDT",
  13: "PT",
  14: "MISSÃO",
  15: "MDB",
  16: "PSTU",
  18: "REDE",
  20: "PODE",
  21: "PCB",
  22: "PL",
  23: "CIDADANIA",
  25: "PRD",
  27: "DC",
  28: "PRTB",
  29: "PCO",
  30: "NOVO",
  33: "MOBILIZA",
  35: "DEMOCRATA",
  36: "AGIR",
  40: "PSB",
  43: "PV",
  44: "UNIÃO",
  45: "PSDB",
  50: "PSOL",
  55: "PSD",
  65: "PCdoB",
  70: "AVANTE",
  77: "SOLIDARIEDADE",
  80: "UP",
};

export function siglaPartido(numero: number): string | null {
  return Object.hasOwn(SIGLAS_PARTIDOS, numero) ? (SIGLAS_PARTIDOS[numero] ?? null) : null;
}

export function rotuloPartido(numero: number): string {
  const sigla = siglaPartido(numero);
  return sigla === null ? `Partido ${numero}` : `${sigla} ${numero}`;
}
