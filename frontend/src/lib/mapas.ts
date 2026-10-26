import { access } from "node:fs/promises";

import { TURNOS, type CargoMapa, type Turno } from "@/lib/eleicoes";

const RELATORIOS =
  "/run/media/marvinbraga/dados/marvin/eleicoes_brasil_tse_download/relatorios";

export const ARQUIVOS_MAPA: Record<CargoMapa, string> = {
  presidente: `${RELATORIOS}/mapa-presidente-2026-turno-1.html`,
  governador: `${RELATORIOS}/mapa-governador-2026-turno-1.html`,
  cruzamento: `${RELATORIOS}/mapa-cruzamento-2026-turno-1.html`,
  // Os comparativos entre turnos vivem dentro do arquivo de presidente do 1º turno.
  turnos: `${RELATORIOS}/mapa-presidente-2026-turno-1.html`,
  turnosgov: `${RELATORIOS}/mapa-presidente-2026-turno-1.html`,
};

// Cada turno tem um arquivo com as visões de presidente, governador e cruzamento.
const ARQUIVO_DO_SEGUNDO_TURNO = `${RELATORIOS}/mapa-presidente-2026-turno-2.html`;

const SO_NO_PRIMEIRO_TURNO: readonly CargoMapa[] = ["turnos", "turnosgov"];

// Os comparativos 1º × 2º ficam no arquivo do 1º turno, qualquer que seja o turno pedido.
export function turnoDoMapa(cargo: CargoMapa, turno: Turno): Turno {
  return SO_NO_PRIMEIRO_TURNO.includes(cargo) ? "1" : turno;
}

export function arquivoMapa(cargo: string, turno = "1"): string | null {
  if (!Object.hasOwn(ARQUIVOS_MAPA, cargo) || !TURNOS.includes(turno as Turno)) {
    return null;
  }
  const visao = cargo as CargoMapa;
  if (turnoDoMapa(visao, turno as Turno) === "2") {
    return ARQUIVO_DO_SEGUNDO_TURNO;
  }
  return ARQUIVOS_MAPA[visao];
}

export async function mapaExiste(cargo: CargoMapa, turno: Turno = "1"): Promise<boolean> {
  const arquivo = arquivoMapa(cargo, turno);
  if (arquivo === null) {
    return false;
  }
  try {
    await access(arquivo);
    return true;
  } catch {
    return false;
  }
}
