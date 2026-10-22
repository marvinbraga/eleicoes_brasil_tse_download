// Tipos e constantes do relatório de capilaridade. Sem import de runtime, para os
// scripts de verificação carregarem este módulo com node --experimental-strip-types.

export const CHAVES_FAIXA = [
  "zero",
  "ate_metade",
  "metade_a_media",
  "media_a_1_5",
  "1_5_a_2",
  "2_a_3",
  "3_ou_mais",
] as const;

export const CLASSES_CAPILARIDADE = [
  "pouco_voto",
  "sem_base",
  "capitais",
  "regional",
  "poucos_municipios",
  "espalhado",
] as const;

export type ChaveFaixa = (typeof CHAVES_FAIXA)[number];

export type ClasseCapilaridade = (typeof CLASSES_CAPILARIDADE)[number];

export const NAO_RANQUEADAS: ReadonlySet<ClasseCapilaridade> = new Set<ClasseCapilaridade>([
  "pouco_voto",
  "sem_base",
]);

export type TipoRecorte = "pais" | "regiao" | "uf";

export type Recorte = { tipo: TipoRecorte; codigo: string; nome: string };

export type ParteCapilaridade = {
  municipios: number;
  votos: number;
  parte: string;
  parte_texto: string;
  eleitorado: string;
  eleitorado_texto: string;
  vezes: string;
};

export type SubdivisaoCapilaridade = ParteCapilaridade & { codigo: string; nome: string };

export type FaixaCapilaridade = {
  chave: ChaveFaixa;
  municipios: number;
  votos_validos: number;
  votos: number;
};

export type LugarCapilaridade = {
  codigo: string;
  nome: string;
  votos: number;
  votos_validos: number;
  fatia: string;
  fatia_texto: string;
};

export type PresencaCapilaridade = { municipios: number; parte: string; parte_texto: string };

export type PartidoCapilaridade = {
  partido: number;
  votos: number;
  votos_validos: number;
  votos_validos_recorte: number;
  fatia: string;
  fatia_texto: string;
  fatia_recorte_texto: string;
  ufs_com_voto: number;
  municipios: number;
  indice: string;
  indice_texto: string;
  indice_100: number;
  top10: ParteCapilaridade;
  presenca: PresencaCapilaridade;
  capitais: ParteCapilaridade | null;
  subdivisoes: SubdivisaoCapilaridade[];
  faixas: FaixaCapilaridade[];
  fortes: LugarCapilaridade[];
  maiores: LugarCapilaridade[];
  classe: ClasseCapilaridade;
  rotulo_classe: string;
  motivo: string;
};

export type ResumoCapilaridade = {
  partido: number;
  votos: number;
  fatia: string;
  fatia_texto: string;
  indice: string;
  indice_100: number;
  presenca: string;
  presenca_texto: string;
  ufs_com_voto: number;
  classe: ClasseCapilaridade;
  rotulo_classe: string;
};

export type RelatorioCapilaridade = {
  ano: number;
  turno: number;
  cargo: string;
  recorte: Recorte;
  municipios: number;
  ufs: number;
  sem_validos: number;
  votos_validos: number;
  exterior: number;
  limites: Record<string, string | number>;
  partidos: PartidoCapilaridade[];
  resumo: ResumoCapilaridade[];
  notas: string[];
};
