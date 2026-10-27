import { access } from "node:fs/promises";

export const ARQUIVO_ORIGEM_VOTOS =
  "/run/media/marvinbraga/dados/marvin/eleicoes_brasil_tse_download/relatorios/origem-votos-2026.html";

export const COMANDO_ORIGEM_VOTOS =
  "uv run python scripts/relatorio_origem_votos.py --ano 2026 --sem-navegador";

export async function origemVotosExiste(): Promise<boolean> {
  try {
    await access(ARQUIVO_ORIGEM_VOTOS);
    return true;
  } catch {
    return false;
  }
}
