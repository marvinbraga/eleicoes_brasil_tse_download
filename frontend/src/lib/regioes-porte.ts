import { access } from "node:fs/promises";

export const ARQUIVO_REGIOES_PORTE =
  "/run/media/marvinbraga/dados/marvin/eleicoes_brasil_tse_download/relatorios/regioes-porte-2026.html";

export const COMANDO_REGIOES_PORTE =
  "uv run python scripts/relatorio_regioes_porte.py --ano 2026 --sem-navegador";

export async function regioesPorteExiste(): Promise<boolean> {
  try {
    await access(ARQUIVO_REGIOES_PORTE);
    return true;
  } catch {
    return false;
  }
}
