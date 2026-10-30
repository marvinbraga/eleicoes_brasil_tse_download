import { access } from "node:fs/promises";

export const ARQUIVO_PL_POUCO_PT_MUITO =
  "/run/media/marvinbraga/dados/marvin/eleicoes_brasil_tse_download/relatorios/pl-pouco-pt-muito-2026.html";

export const COMANDO_PL_POUCO_PT_MUITO =
  "uv run python scripts/relatorio_pl_pouco_pt_muito.py --ano 2026 --sem-navegador";

export async function plPoucoPtMuitoExiste(): Promise<boolean> {
  try {
    await access(ARQUIVO_PL_POUCO_PT_MUITO);
    return true;
  } catch {
    return false;
  }
}
