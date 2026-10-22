export const ANOS = ["2026"] as const;
export const TURNOS = ["1", "2"] as const;

export const UFS = [
  { value: "AC", label: "AC" },
  { value: "AL", label: "AL" },
  { value: "AM", label: "AM" },
  { value: "AP", label: "AP" },
  { value: "BA", label: "BA" },
  { value: "CE", label: "CE" },
  { value: "DF", label: "DF" },
  { value: "ES", label: "ES" },
  { value: "GO", label: "GO" },
  { value: "MA", label: "MA" },
  { value: "MG", label: "MG" },
  { value: "MS", label: "MS" },
  { value: "MT", label: "MT" },
  { value: "PA", label: "PA" },
  { value: "PB", label: "PB" },
  { value: "PE", label: "PE" },
  { value: "PI", label: "PI" },
  { value: "PR", label: "PR" },
  { value: "RJ", label: "RJ" },
  { value: "RN", label: "RN" },
  { value: "RO", label: "RO" },
  { value: "RR", label: "RR" },
  { value: "RS", label: "RS" },
  { value: "SC", label: "SC" },
  { value: "SE", label: "SE" },
  { value: "SP", label: "SP" },
  { value: "TO", label: "TO" },
  { value: "ZZ", label: "Exterior" },
] as const;

export const UF_TODAS = "TODAS" as const;

export const OPCOES_UF = [
  { value: UF_TODAS, label: "Todas" },
  ...UFS,
] as const;

export const CARGOS_PODER = [
  { value: "presidente", label: "Presidente" },
  { value: "governador", label: "Governador" },
  { value: "senador", label: "Senador" },
  { value: "deputadoFederal", label: "Deputado federal" },
  { value: "deputadoEstadual", label: "Deputado estadual" },
] as const;

export const CARGOS_PERFIL = [
  { value: "presidente", label: "Presidente" },
  { value: "governador", label: "Governador" },
  { value: "senador", label: "Senador" },
] as const;

export const GRUPOS_PERFIL = [
  { value: "2-6", label: "2 a 6" },
  { value: "2", label: "2" },
  { value: "3", label: "3" },
  { value: "4", label: "4" },
  { value: "5", label: "5" },
  { value: "6", label: "6" },
] as const;

export const NIVEIS = [
  { value: "municipio", label: "Município" },
  { value: "uf", label: "UF" },
  { value: "regiao", label: "Região" },
  { value: "pais", label: "País" },
] as const;

export const CARGOS_MAPA = [
  { value: "presidente", label: "Presidente" },
  { value: "governador", label: "Governador" },
  { value: "cruzamento", label: "Presidente × governador" },
] as const;

export type Ano = (typeof ANOS)[number];
export type Turno = (typeof TURNOS)[number];
export type Uf = (typeof UFS)[number]["value"];
export type UfFiltro = Uf | typeof UF_TODAS;
export type CargoPoder = (typeof CARGOS_PODER)[number]["value"];
export type CargoPerfil = (typeof CARGOS_PERFIL)[number]["value"];
export type GruposPerfil = (typeof GRUPOS_PERFIL)[number]["value"];
export type Nivel = (typeof NIVEIS)[number]["value"];
export type CargoMapa = (typeof CARGOS_MAPA)[number]["value"];

// Cada arquivo do mapa traz todas as visões; o quadro carrega este e escolhe a visão pelo hash.
export const CARGO_DO_ARQUIVO_DO_MAPA: CargoMapa = "presidente";

export type ValorConsulta = string | string[] | undefined;

export type ConsultaRelatorio = {
  ano?: ValorConsulta;
  turno?: ValorConsulta;
  uf?: ValorConsulta;
  cargo?: ValorConsulta;
  nivel?: ValorConsulta;
  grupos?: ValorConsulta;
  consultar?: ValorConsulta;
};

export function consultaPedida(valor: ValorConsulta): boolean {
  const bruto = Array.isArray(valor) ? valor[0] : valor;
  return bruto === "1";
}

const VALORES_UF: readonly Uf[] = UFS.map((uf) => uf.value);
const VALORES_UF_FILTRO: readonly UfFiltro[] = [UF_TODAS, ...VALORES_UF];
const VALORES_CARGO_PODER: readonly CargoPoder[] = CARGOS_PODER.map(
  (cargo) => cargo.value,
);
const VALORES_CARGO_PERFIL: readonly CargoPerfil[] = CARGOS_PERFIL.map(
  (cargo) => cargo.value,
);
const VALORES_GRUPOS_PERFIL: readonly GruposPerfil[] = GRUPOS_PERFIL.map(
  (item) => item.value,
);
const VALORES_NIVEL: readonly Nivel[] = NIVEIS.map((nivel) => nivel.value);
const VALORES_CARGO_MAPA: readonly CargoMapa[] = CARGOS_MAPA.map(
  (cargo) => cargo.value,
);

export function escolher<T extends string>(
  valor: ValorConsulta,
  permitidos: readonly T[],
  padrao: T,
): T {
  const bruto = Array.isArray(valor) ? valor[0] : valor;
  if (bruto !== undefined && permitidos.includes(bruto as T)) {
    return bruto as T;
  }
  return padrao;
}

export function lerAno(valor: ValorConsulta): Ano {
  return escolher(valor, ANOS, "2026");
}

export function lerTurno(valor: ValorConsulta): Turno {
  return escolher(valor, TURNOS, "1");
}

export function lerUf(valor: ValorConsulta): UfFiltro {
  return escolher(valor, VALORES_UF_FILTRO, "AC");
}

export function ufDeConsulta(uf: UfFiltro): Uf {
  return uf === UF_TODAS ? "AC" : uf;
}

export function lerCargoPoder(valor: ValorConsulta): CargoPoder {
  return escolher(valor, VALORES_CARGO_PODER, "presidente");
}

export function lerCargoPerfil(valor: ValorConsulta): CargoPerfil {
  return escolher(valor, VALORES_CARGO_PERFIL, "presidente");
}

export function lerGruposPerfil(valor: ValorConsulta): GruposPerfil {
  return escolher(valor, VALORES_GRUPOS_PERFIL, "2-6");
}

export function lerNivel(valor: ValorConsulta): Nivel {
  return escolher(valor, VALORES_NIVEL, "municipio");
}

export function rotuloCargoPoder(cargo: CargoPoder): string {
  const encontrado = CARGOS_PODER.find((item) => item.value === cargo);
  return encontrado === undefined ? cargo : encontrado.label;
}

export function rotuloCargoPerfil(cargo: string): string {
  const encontrado = CARGOS_PERFIL.find((item) => item.value === cargo);
  return encontrado === undefined ? cargo : encontrado.label;
}

const NOMES_UF = {
  AC: "Acre",
  AL: "Alagoas",
  AM: "Amazonas",
  AP: "Amapá",
  BA: "Bahia",
  CE: "Ceará",
  DF: "Distrito Federal",
  ES: "Espírito Santo",
  GO: "Goiás",
  MA: "Maranhão",
  MG: "Minas Gerais",
  MS: "Mato Grosso do Sul",
  MT: "Mato Grosso",
  PA: "Pará",
  PB: "Paraíba",
  PE: "Pernambuco",
  PI: "Piauí",
  PR: "Paraná",
  RJ: "Rio de Janeiro",
  RN: "Rio Grande do Norte",
  RO: "Rondônia",
  RR: "Roraima",
  RS: "Rio Grande do Sul",
  SC: "Santa Catarina",
  SE: "Sergipe",
  SP: "São Paulo",
  TO: "Tocantins",
  ZZ: "Exterior",
} as const;

export function nomeUf(sigla: string): string {
  if (sigla in NOMES_UF) {
    return NOMES_UF[sigla as keyof typeof NOMES_UF];
  }
  return sigla;
}

export function rotuloNivel(nivel: Nivel): string {
  const encontrado = NIVEIS.find((item) => item.value === nivel);
  return encontrado === undefined ? nivel : encontrado.label;
}

export function lerCargoMapa(valor: ValorConsulta): CargoMapa {
  return escolher(valor, VALORES_CARGO_MAPA, "presidente");
}

export function urlApi(): string {
  const configurada = process.env.NEXT_PUBLIC_API_URL?.trim();
  const base =
    configurada && configurada.length > 0
      ? configurada
      : "http://localhost:15000";
  return base.replace(/\/+$/, "");
}
