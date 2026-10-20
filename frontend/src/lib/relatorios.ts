import { UF_TODAS, type Nivel } from "@/lib/eleicoes";

export type PartidoRanqueado = {
  partido: number;
  votos: number;
};

export type LeituraCargo = {
  leader: PartidoRanqueado | null;
  runner_up: PartidoRanqueado | null;
  valid: number;
  branco: number;
  nulo: number;
};

export type LeituraLugar = {
  codigo: string;
  nome: string;
  classe: string;
  margin: string;
  presidente: LeituraCargo;
  governador: LeituraCargo | null;
};

export type FatiaClasse = {
  classe: string;
  cidades: number;
  votos_validos: number;
};

export type Composicao = {
  classes: FatiaClasse[];
  votos_validos: number;
  branco: number;
  nulo: number;
};

export type GrupoMunicipios = {
  uf: string;
  places: LeituraLugar[];
};

export type RelatorioCruzado = {
  ano: number;
  turno: number;
  composition: Composicao;
  municipalities: GrupoMunicipios[];
  states: LeituraLugar[];
  regions: LeituraLugar[];
  country: LeituraLugar | null;
};

export type CelulaGrade = {
  partido: number;
  votos_nominais: number;
  votos_legenda: number;
  comparecimento: number;
  votos: number;
  fatia: string;
};

export type LinhaGrade = {
  codigo: string;
  nome: string;
  comparecimento: number;
  celulas: CelulaGrade[];
};

export type GradeRelatorio = {
  ano: number;
  turno: number;
  uf: string;
  cargo: string;
  nivel: string;
  colunas: number[];
  linhas: LinhaGrade[];
};

export type GrupoPerfil = {
  numero: number;
  municipios: number;
  comparecimento: number;
  centro: string[];
};

export type MunicipioPerfil = {
  codigo: string;
  nome: string;
  grupo: number;
};

export type RelatorioPerfis = {
  ano: number;
  turno: number;
  cargo: string;
  partidos: number[];
  com_cedula: boolean;
  buscou: boolean;
  silhueta: string | null;
  grupos: GrupoPerfil[];
  municipios: MunicipioPerfil[];
  notas: string[];
};

export type LinhaClasseGovernador = {
  classe: string;
  rotulo: string;
  apoio: number;
  recall: string;
  regras: string[];
};

export type AcertoUf = {
  uf: string;
  municipios: number;
  acerto: string;
};

export type RelatorioClasseGovernador = {
  ano: number;
  turno: number;
  acerto: string;
  base: string;
  base_lider: string;
  f1_macro: string;
  abaixo_da_base: boolean;
  por_uf: AcertoUf[];
  sem_uf: number;
  linhas: LinhaClasseGovernador[];
  retidas: string[];
  notas: string[];
};

const ROTULOS_CLASSE: Record<string, string> = {
  consolidacao: "Consolidação",
  terreno_de_virada: "Terreno de virada",
  em_aberto: "Em aberto",
  sem_governador: "Sem governador",
};

export class RespostaInvalidaError extends Error {
  constructor() {
    super("A API devolveu um JSON que não confere com o relatório.");
    this.name = "RespostaInvalidaError";
  }
}

export function rotuloClasse(classe: string): string {
  return ROTULOS_CLASSE[classe] ?? classe;
}

export function linhasVisiveis(
  linhas: readonly LinhaGrade[],
  nivel: Nivel,
  uf: string,
): LinhaGrade[] {
  if (nivel !== "municipio" || uf === UF_TODAS) {
    return [...linhas];
  }
  const sufixo = ` (${uf})`;
  const daUf = linhas.filter((linha) => linha.nome.endsWith(sufixo));
  return daUf.length > 0 ? daUf : [...linhas];
}

export function lerRelatorioCruzado(valor: unknown): RelatorioCruzado {
  const registro = exigirRegistro(valor);
  const pais = registro.country;
  return {
    ano: exigirInteiro(registro.ano),
    turno: exigirInteiro(registro.turno),
    composition: lerComposicao(registro.composition),
    municipalities: exigirLista(registro.municipalities, lerGrupo),
    states: exigirLista(registro.states, lerLugar),
    regions: exigirLista(registro.regions, lerLugar),
    country: pais === null ? null : lerLugar(pais),
  };
}

export function lerGrade(valor: unknown): GradeRelatorio {
  const registro = exigirRegistro(valor);
  return {
    ano: exigirInteiro(registro.ano),
    turno: exigirInteiro(registro.turno),
    uf: exigirTexto(registro.uf),
    cargo: exigirTexto(registro.cargo),
    nivel: exigirTexto(registro.nivel),
    colunas: exigirLista(registro.colunas, exigirInteiro),
    linhas: exigirLista(registro.linhas, lerLinha),
  };
}

export function lerRelatorioPerfis(valor: unknown): RelatorioPerfis {
  const registro = exigirRegistro(valor);
  return {
    ano: exigirInteiro(registro.ano),
    turno: exigirInteiro(registro.turno),
    cargo: exigirTexto(registro.cargo),
    partidos: exigirLista(registro.partidos, exigirInteiro),
    com_cedula: exigirBooleano(registro.com_cedula),
    buscou: exigirBooleano(registro.buscou),
    silhueta: exigirTextoOuNulo(registro.silhueta),
    grupos: exigirLista(registro.grupos, lerGrupoPerfil),
    municipios: exigirLista(registro.municipios, lerMunicipioPerfil),
    notas: exigirLista(registro.notas, exigirTexto),
  };
}

export function lerClasseGovernador(valor: unknown): RelatorioClasseGovernador {
  const registro = exigirRegistro(valor);
  return {
    ano: exigirInteiro(registro.ano),
    turno: exigirInteiro(registro.turno),
    acerto: exigirTexto(registro.acerto),
    base: exigirTexto(registro.base),
    base_lider: exigirTexto(registro.base_lider),
    f1_macro: exigirTexto(registro.f1_macro),
    abaixo_da_base: exigirBooleano(registro.abaixo_da_base),
    por_uf: exigirLista(registro.por_uf, lerAcertoUf),
    sem_uf: exigirInteiro(registro.sem_uf),
    linhas: exigirLista(registro.linhas, lerLinhaClasse),
    retidas: exigirLista(registro.retidas, exigirTexto),
    notas: exigirLista(registro.notas, exigirTexto),
  };
}

function lerComposicao(valor: unknown): Composicao {
  const registro = exigirRegistro(valor);
  return {
    classes: exigirLista(registro.classes, lerFatia),
    votos_validos: exigirInteiro(registro.votos_validos),
    branco: exigirInteiro(registro.branco),
    nulo: exigirInteiro(registro.nulo),
  };
}

function lerFatia(valor: unknown): FatiaClasse {
  const registro = exigirRegistro(valor);
  return {
    classe: exigirTexto(registro.classe),
    cidades: exigirInteiro(registro.cidades),
    votos_validos: exigirInteiro(registro.votos_validos),
  };
}

function lerGrupo(valor: unknown): GrupoMunicipios {
  const registro = exigirRegistro(valor);
  return {
    uf: exigirTexto(registro.uf),
    places: exigirLista(registro.places, lerLugar),
  };
}

function lerLugar(valor: unknown): LeituraLugar {
  const registro = exigirRegistro(valor);
  const governador = registro.governador;
  return {
    codigo: exigirTexto(registro.codigo),
    nome: exigirTexto(registro.nome),
    classe: exigirTexto(registro.classe),
    margin: exigirTexto(registro.margin),
    presidente: lerCargo(registro.presidente),
    governador: governador === null ? null : lerCargo(governador),
  };
}

function lerCargo(valor: unknown): LeituraCargo {
  const registro = exigirRegistro(valor);
  return {
    leader: registro.leader === null ? null : lerPartido(registro.leader),
    runner_up:
      registro.runner_up === null ? null : lerPartido(registro.runner_up),
    valid: exigirInteiro(registro.valid),
    branco: exigirInteiro(registro.branco),
    nulo: exigirInteiro(registro.nulo),
  };
}

function lerPartido(valor: unknown): PartidoRanqueado {
  const registro = exigirRegistro(valor);
  return {
    partido: exigirInteiro(registro.partido),
    votos: exigirInteiro(registro.votos),
  };
}

function lerGrupoPerfil(valor: unknown): GrupoPerfil {
  const registro = exigirRegistro(valor);
  return {
    numero: exigirInteiro(registro.numero),
    municipios: exigirInteiro(registro.municipios),
    comparecimento: exigirInteiro(registro.comparecimento),
    centro: exigirLista(registro.centro, exigirTexto),
  };
}

function lerMunicipioPerfil(valor: unknown): MunicipioPerfil {
  const registro = exigirRegistro(valor);
  return {
    codigo: exigirTexto(registro.codigo),
    nome: exigirTexto(registro.nome),
    grupo: exigirInteiro(registro.grupo),
  };
}

function lerLinhaClasse(valor: unknown): LinhaClasseGovernador {
  const registro = exigirRegistro(valor);
  return {
    classe: exigirTexto(registro.classe),
    rotulo: exigirTexto(registro.rotulo),
    apoio: exigirInteiro(registro.apoio),
    recall: exigirTexto(registro.recall),
    regras: exigirLista(registro.regras, exigirTexto),
  };
}

function lerAcertoUf(valor: unknown): AcertoUf {
  const registro = exigirRegistro(valor);
  return {
    uf: exigirTexto(registro.uf),
    municipios: exigirInteiro(registro.municipios),
    acerto: exigirTexto(registro.acerto),
  };
}

function lerLinha(valor: unknown): LinhaGrade {
  const registro = exigirRegistro(valor);
  return {
    codigo: exigirTexto(registro.codigo),
    nome: exigirTexto(registro.nome),
    comparecimento: exigirInteiro(registro.comparecimento),
    celulas: exigirLista(registro.celulas, lerCelula),
  };
}

function lerCelula(valor: unknown): CelulaGrade {
  const registro = exigirRegistro(valor);
  return {
    partido: exigirInteiro(registro.partido),
    votos_nominais: exigirInteiro(registro.votos_nominais),
    votos_legenda: exigirInteiro(registro.votos_legenda),
    comparecimento: exigirInteiro(registro.comparecimento),
    votos: exigirInteiro(registro.votos),
    fatia: exigirTexto(registro.fatia),
  };
}

function exigirLista<T>(valor: unknown, ler: (item: unknown) => T): T[] {
  if (!Array.isArray(valor)) {
    throw new RespostaInvalidaError();
  }
  return valor.map(ler);
}

function ehRegistro(valor: unknown): valor is Record<string, unknown> {
  return typeof valor === "object" && valor !== null && !Array.isArray(valor);
}

function exigirRegistro(valor: unknown): Record<string, unknown> {
  if (!ehRegistro(valor)) {
    throw new RespostaInvalidaError();
  }
  return valor;
}

function exigirTexto(valor: unknown): string {
  if (typeof valor !== "string") {
    throw new RespostaInvalidaError();
  }
  return valor;
}

function exigirTextoOuNulo(valor: unknown): string | null {
  if (valor === null) {
    return null;
  }
  return exigirTexto(valor);
}

function exigirBooleano(valor: unknown): boolean {
  if (typeof valor !== "boolean") {
    throw new RespostaInvalidaError();
  }
  return valor;
}

function exigirInteiro(valor: unknown): number {
  if (typeof valor !== "number" || !Number.isSafeInteger(valor) || valor < 0) {
    throw new RespostaInvalidaError();
  }
  return valor;
}
