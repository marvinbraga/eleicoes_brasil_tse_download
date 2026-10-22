// Tipos e leitura do JSON de /relatorios/dados/verticalizacao.
// As funções exigir* ficam locais de propósito: os planos paralelos não mexem em relatorios.ts.
// Follow-up: extrair lib/ler-json.ts depois que os planos de 2026-10-22 entrarem.

export const CARGOS_VERTICAIS = [
  "presidente",
  "governador",
  "senador",
  "deputadoFederal",
  "deputadoEstadual",
] as const;
export type CargoVertical = (typeof CARGOS_VERTICAIS)[number];

export const ROTULO_CARGO: Record<CargoVertical, string> = {
  presidente: "Presidente",
  governador: "Governador",
  senador: "Senador",
  deputadoFederal: "Dep. federal",
  deputadoEstadual: "Dep. estadual",
};

export const CURTO_CARGO: Record<CargoVertical, string> = {
  presidente: "Pres.",
  governador: "Gov.",
  senador: "Sen.",
  deputadoFederal: "Fed.",
  deputadoEstadual: "Est.",
};

export const CLASSES = ["puxador", "base", "alinhado", "sem_candidato"] as const;
export type Classe = (typeof CLASSES)[number];
export const PERFIS = ["puxador", "base", "alinhado", "misto", "sem_comparacao"] as const;
export type Perfil = (typeof PERFIS)[number];

export type CargoVerticalDados = {
  cargo: CargoVertical;
  votos: number;
  validos: number;
  validos_onde: number;
  fatia: string | null;
  fatia_onde: string | null;
  ufs_concorreu: number;
  ufs_total: number;
};
export type Coerencia = {
  cargo_x: CargoVertical;
  cargo_y: CargoVertical;
  r: string | null;
  municipios: number;
};
export type ComparacaoUf = { uf: string; majoritaria: string; esperada: string; classe: Classe };
export type SemCandidato = { uf: string; proporcional: string };
export type Comparacao = {
  majoritario: CargoVertical;
  proporcional: CargoVertical;
  majoritaria: string | null;
  esperada: string | null;
  razao: string | null;
  classe: Classe | null;
  por_uf: ComparacaoUf[];
  sem_candidato: SemCandidato[];
};
export type PartidoVertical = {
  partido: number;
  perfil: Perfil;
  coerencia_mediana: string | null;
  cargos: CargoVerticalDados[];
  coerencia: Coerencia[];
  comparacoes: Comparacao[];
};
export type PontoDispersao = {
  codigo: string;
  nome: string;
  uf: string;
  comparecimento: number;
  x: string;
  y: string;
};
export type Limiares = {
  razao: string;
  diferenca: string;
  base_relevante: string;
  minimo_municipios: number;
};
export type DispersaoVertical = {
  partido: number;
  cargo_x: CargoVertical;
  cargo_y: CargoVertical;
  coerencia: Coerencia;
  pontos: PontoDispersao[];
};
export type RelatorioVerticalizacao = {
  ano: number;
  turno: number;
  uf: string | null;
  municipios: number;
  sem_uf: number;
  cargos: CargoVertical[];
  limiares: Limiares;
  partidos: PartidoVertical[];
  dispersao: DispersaoVertical;
  notas: string[];
};

// Mesma mensagem de RespostaInvalidaError (relatorios.ts). Uma classe própria evita importar
// relatorios.ts, que usa o alias "@/" e quebra os scripts verificar-*.ts.
export class RespostaVerticalizacaoInvalidaError extends Error {
  constructor() {
    super("A API devolveu um JSON que não confere com o relatório.");
    this.name = "RespostaVerticalizacaoInvalidaError";
  }
}

export function ehCargoVertical(valor: unknown): valor is CargoVertical {
  return typeof valor === "string" && (CARGOS_VERTICAIS as readonly string[]).includes(valor);
}

export function lerDecimal(texto: string | null): number | null {
  if (texto === null) {
    return null;
  }
  // O contrato manda vírgula decimal; o ponto é só separador de milhar ("1.234,5000").
  const corpo = texto.trim().replace(/\./g, "").replace(",", ".");
  if (!/^-?\d+(?:\.\d+)?$/.test(corpo)) {
    return null;
  }
  const valor = Number(corpo);
  return Number.isFinite(valor) ? valor : null;
}

const PARES_COERENCIA = 7;
const PARES_CANONICOS = 3;

export function lerVerticalizacao(valor: unknown): RelatorioVerticalizacao {
  const relatorio = lerRelatorio(valor);
  const ordem = relatorio.cargos.join(",");
  for (const partido of relatorio.partidos) {
    if (
      partido.cargos.map((item) => item.cargo).join(",") !== ordem ||
      partido.coerencia.length !== PARES_COERENCIA ||
      partido.comparacoes.length !== PARES_CANONICOS
    ) {
      throw new RespostaVerticalizacaoInvalidaError();
    }
  }
  return relatorio;
}

function lerRelatorio(valor: unknown): RelatorioVerticalizacao {
  const dados = exigirRegistro(valor);
  return {
    ano: exigirInteiro(dados.ano),
    turno: exigirInteiro(dados.turno),
    uf: exigirTextoOuNulo(dados.uf),
    municipios: exigirInteiro(dados.municipios),
    sem_uf: exigirInteiro(dados.sem_uf),
    cargos: exigirLista(dados.cargos, exigirCargo),
    limiares: lerLimiares(dados.limiares),
    partidos: exigirLista(dados.partidos, lerPartido),
    dispersao: lerDispersao(dados.dispersao),
    notas: exigirLista(dados.notas, exigirTexto),
  };
}

function lerLimiares(valor: unknown): Limiares {
  const dados = exigirRegistro(valor);
  return {
    razao: exigirTexto(dados.razao),
    diferenca: exigirTexto(dados.diferenca),
    base_relevante: exigirTexto(dados.base_relevante),
    minimo_municipios: exigirInteiro(dados.minimo_municipios),
  };
}

function lerPartido(valor: unknown): PartidoVertical {
  const dados = exigirRegistro(valor);
  return {
    partido: exigirInteiro(dados.partido),
    perfil: exigirOpcao(dados.perfil, PERFIS),
    coerencia_mediana: exigirTextoOuNulo(dados.coerencia_mediana),
    cargos: exigirLista(dados.cargos, lerCargo),
    coerencia: exigirLista(dados.coerencia, lerCoerencia),
    comparacoes: exigirLista(dados.comparacoes, lerComparacao),
  };
}

function lerCargo(valor: unknown): CargoVerticalDados {
  const dados = exigirRegistro(valor);
  return {
    cargo: exigirCargo(dados.cargo),
    votos: exigirInteiro(dados.votos),
    validos: exigirInteiro(dados.validos),
    validos_onde: exigirInteiro(dados.validos_onde),
    fatia: exigirTextoOuNulo(dados.fatia),
    fatia_onde: exigirTextoOuNulo(dados.fatia_onde),
    ufs_concorreu: exigirInteiro(dados.ufs_concorreu),
    ufs_total: exigirInteiro(dados.ufs_total),
  };
}

function lerCoerencia(valor: unknown): Coerencia {
  const dados = exigirRegistro(valor);
  return {
    cargo_x: exigirCargo(dados.cargo_x),
    cargo_y: exigirCargo(dados.cargo_y),
    r: exigirTextoOuNulo(dados.r),
    municipios: exigirInteiro(dados.municipios),
  };
}

function lerComparacao(valor: unknown): Comparacao {
  const dados = exigirRegistro(valor);
  return {
    majoritario: exigirCargo(dados.majoritario),
    proporcional: exigirCargo(dados.proporcional),
    majoritaria: exigirTextoOuNulo(dados.majoritaria),
    esperada: exigirTextoOuNulo(dados.esperada),
    razao: exigirTextoOuNulo(dados.razao),
    classe: dados.classe === null ? null : exigirOpcao(dados.classe, CLASSES),
    por_uf: exigirLista(dados.por_uf, lerComparacaoUf),
    sem_candidato: exigirLista(dados.sem_candidato, lerSemCandidato),
  };
}

function lerComparacaoUf(valor: unknown): ComparacaoUf {
  const dados = exigirRegistro(valor);
  return {
    uf: exigirTexto(dados.uf),
    majoritaria: exigirTexto(dados.majoritaria),
    esperada: exigirTexto(dados.esperada),
    classe: exigirOpcao(dados.classe, CLASSES),
  };
}

function lerSemCandidato(valor: unknown): SemCandidato {
  const dados = exigirRegistro(valor);
  return { uf: exigirTexto(dados.uf), proporcional: exigirTexto(dados.proporcional) };
}

function lerDispersao(valor: unknown): DispersaoVertical {
  const dados = exigirRegistro(valor);
  return {
    partido: exigirInteiro(dados.partido),
    cargo_x: exigirCargo(dados.cargo_x),
    cargo_y: exigirCargo(dados.cargo_y),
    coerencia: lerCoerencia(dados.coerencia),
    pontos: exigirLista(dados.pontos, lerPonto),
  };
}

function lerPonto(valor: unknown): PontoDispersao {
  const dados = exigirRegistro(valor);
  return {
    codigo: exigirTexto(dados.codigo),
    nome: exigirTexto(dados.nome),
    uf: exigirTexto(dados.uf),
    comparecimento: exigirInteiro(dados.comparecimento),
    x: exigirTexto(dados.x),
    y: exigirTexto(dados.y),
  };
}

function exigirLista<T>(valor: unknown, ler: (item: unknown) => T): T[] {
  if (!Array.isArray(valor)) {
    throw new RespostaVerticalizacaoInvalidaError();
  }
  return valor.map(ler);
}

function exigirRegistro(valor: unknown): Record<string, unknown> {
  if (typeof valor !== "object" || valor === null || Array.isArray(valor)) {
    throw new RespostaVerticalizacaoInvalidaError();
  }
  return valor as Record<string, unknown>;
}

function exigirTexto(valor: unknown): string {
  if (typeof valor !== "string") {
    throw new RespostaVerticalizacaoInvalidaError();
  }
  return valor;
}

function exigirTextoOuNulo(valor: unknown): string | null {
  return valor === null ? null : exigirTexto(valor);
}

function exigirInteiro(valor: unknown): number {
  if (typeof valor !== "number" || !Number.isSafeInteger(valor) || valor < 0) {
    throw new RespostaVerticalizacaoInvalidaError();
  }
  return valor;
}

function exigirCargo(valor: unknown): CargoVertical {
  if (!ehCargoVertical(valor)) {
    throw new RespostaVerticalizacaoInvalidaError();
  }
  return valor;
}

function exigirOpcao<T extends string>(valor: unknown, opcoes: readonly T[]): T {
  if (typeof valor !== "string" || !(opcoes as readonly string[]).includes(valor)) {
    throw new RespostaVerticalizacaoInvalidaError();
  }
  return valor as T;
}
