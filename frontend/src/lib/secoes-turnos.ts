import { access } from "node:fs/promises";

export const ARQUIVO_SECOES_TURNOS =
  "/run/media/marvinbraga/dados/marvin/eleicoes_brasil_tse_download/relatorios/secoes-turnos-2026.html";

export const COMANDO_SECOES_TURNOS =
  "uv run python scripts/relatorio_secoes_turnos.py --ano 2026 --sem-navegador";

export async function secoesTurnosExiste(): Promise<boolean> {
  try {
    await access(ARQUIVO_SECOES_TURNOS);
    return true;
  } catch {
    return false;
  }
}
