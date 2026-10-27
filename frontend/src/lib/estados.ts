import { access } from "node:fs/promises";

import { TURNOS, escolher, type Turno, type ValorConsulta } from "@/lib/eleicoes";

const RELATORIOS =
  "/run/media/marvinbraga/dados/marvin/eleicoes_brasil_tse_download/relatorios";

export const ARQUIVOS_ESTADOS: Record<Turno, string> = {
  "1": `${RELATORIOS}/estados-2026-turno-1.html`,
  "2": `${RELATORIOS}/estados-2026-turno-2.html`,
};

// O 2º turno é a leitura principal; o 1º fica a um clique.
export function lerTurnoEstados(valor: ValorConsulta): Turno {
  return escolher(valor, TURNOS, "2");
}

export function comandoEstados(turno: Turno): string {
  return `uv run python scripts/relatorio_estados.py --ano 2026 --turno ${turno} --sem-navegador`;
}

export function arquivoEstados(turno: string | null): string | null {
  if (turno === null || !TURNOS.includes(turno as Turno)) {
    return null;
  }
  return ARQUIVOS_ESTADOS[turno as Turno];
}

export async function estadosExiste(turno: Turno): Promise<boolean> {
  try {
    await access(ARQUIVOS_ESTADOS[turno]);
    return true;
  } catch {
    return false;
  }
}

// O HTML segue o tema do sistema; `data-tema` faz ele seguir o tema escolhido no app.
export function htmlComTema(html: string, tema: string | null): string {
  if (tema !== "dark" && tema !== "light") {
    return html;
  }
  return html.replace('<html lang="pt-BR">', `<html lang="pt-BR" data-tema="${tema}">`);
}
