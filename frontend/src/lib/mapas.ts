import { access } from "node:fs/promises";

import type { CargoMapa } from "@/lib/eleicoes";

export const ARQUIVOS_MAPA: Record<CargoMapa, string> = {
  presidente:
    "/run/media/marvinbraga/dados/marvin/eleicoes_brasil_tse_download/relatorios/mapa-presidente-2026-turno-1.html",
  governador:
    "/run/media/marvinbraga/dados/marvin/eleicoes_brasil_tse_download/relatorios/mapa-governador-2026-turno-1.html",
  cruzamento:
    "/run/media/marvinbraga/dados/marvin/eleicoes_brasil_tse_download/relatorios/mapa-cruzamento-2026-turno-1.html",
  // Os comparativos entre turnos vivem dentro do arquivo de presidente do 1º turno.
  turnos:
    "/run/media/marvinbraga/dados/marvin/eleicoes_brasil_tse_download/relatorios/mapa-presidente-2026-turno-1.html",
  turnosgov:
    "/run/media/marvinbraga/dados/marvin/eleicoes_brasil_tse_download/relatorios/mapa-presidente-2026-turno-1.html",
};

export function arquivoMapa(cargo: string): string | null {
  if (Object.hasOwn(ARQUIVOS_MAPA, cargo)) {
    return ARQUIVOS_MAPA[cargo as CargoMapa];
  }
  return null;
}

export async function mapaExiste(cargo: CargoMapa): Promise<boolean> {
  try {
    await access(ARQUIVOS_MAPA[cargo]);
    return true;
  } catch {
    return false;
  }
}
