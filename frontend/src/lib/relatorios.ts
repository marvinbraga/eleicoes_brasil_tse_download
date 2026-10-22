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

export type LegendaCadeiras = {
  codigo: string;
  sigla: string;
  nome: string;
  federacao: boolean;
  partidos: number[];
};

export type ListaCadeiras = {
  legenda: string;
  votos: number;
  votos_legenda: number;
  quociente_partidario: number;
  cadeiras_quociente: number;
  cadeiras_media: number;
  cadeiras_media_livre: number;
  cadeiras: number;
};

export type EleitoCadeiras = {
  numero: number;
  partido: number;
  legenda: string;
  votos: number;
  fase: string;
  empate: boolean;
};

export type CasaUfCadeiras = {
  uf: string;
  cargo: string;
  vagas: number;
  votos_validos: number;
  quociente_eleitoral: number;
  vagas_sem_candidato: number;
  listas: ListaCadeiras[];
  eleitos: EleitoCadeiras[];
};

export type ContagemLegenda = { legenda: string; cadeiras: number };
export type ContagemPartido = { partido: number; cadeiras: number };

export type CasaCadeiras = {
  casa: string;
  nome: string;
  vagas: number;
  vagas_simuladas: number;
  ufs_sem_votos: string[];
  legendas: ContagemLegenda[];
  partidos: ContagemPartido[];
  ufs: CasaUfCadeiras[];
};

export type CandidatoMajoritario = {
  numero: number;
  partido: number;
  votos: number;
  fatia: string;
};

export type SenadoUf = {
  uf: string;
  votos_validos: number;
  eleitos: CandidatoMajoritario[];
  empate: boolean;
};

export type SenadoCadeiras = {
  vagas: number;
  vagas_simuladas: number;
  ufs_sem_votos: string[];
  partidos: ContagemPartido[];
  ufs: SenadoUf[];
};

export type GovernoUf = {
  uf: string;
  situacao: string;
  votos_validos: number;
  candidatos: CandidatoMajoritario[];
  empate: boolean;
};

export type GovernoCadeiras = {
  ufs_sem_votos: string[];
  partidos: { partido: number; eleitos: number; segundo_turno: number }[];
  ufs: GovernoUf[];
};

export type ForcaPartido = {
  partido: number;
  legenda: string;
  camara: number;
  assembleias: number;
  senado: number;
  governadores: number;
  governadores_segundo_turno: number;
};

export type SimulacaoCadeiras = {
  ano: number;
  turno: number;
  gerado_em: string;
  estimativa: boolean;
  legendas: LegendaCadeiras[];
  casas: CasaCadeiras[];
  senado: SenadoCadeiras;
  governo: GovernoCadeiras;
  partidos: ForcaPartido[];
  descartados: number;
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

export function lerCadeiras(valor: unknown): SimulacaoCadeiras {
  const registro = exigirRegistro(valor);
  return {
    ano: exigirInteiro(registro.ano),
    turno: exigirInteiro(registro.turno),
    gerado_em: exigirTexto(registro.gerado_em),
    estimativa: exigirBooleano(registro.estimativa),
    legendas: exigirLista(registro.legendas, lerLegendaCadeiras),
    casas: exigirLista(registro.casas, lerCasaCadeiras),
    senado: lerSenadoCadeiras(registro.senado),
    governo: lerGovernoCadeiras(registro.governo),
    partidos: exigirLista(registro.partidos, lerForcaPartido),
    descartados: exigirInteiro(registro.descartados),
    notas: exigirLista(registro.notas, exigirTexto),
  };
}

function lerLegendaCadeiras(valor: unknown): LegendaCadeiras {
  const registro = exigirRegistro(valor);
  return {
    codigo: exigirTexto(registro.codigo),
    sigla: exigirTexto(registro.sigla),
    nome: exigirTexto(registro.nome),
    federacao: exigirBooleano(registro.federacao),
    partidos: exigirLista(registro.partidos, exigirInteiro),
  };
}

function lerCasaCadeiras(valor: unknown): CasaCadeiras {
  const registro = exigirRegistro(valor);
  return {
    casa: exigirTexto(registro.casa),
    nome: exigirTexto(registro.nome),
    vagas: exigirInteiro(registro.vagas),
    vagas_simuladas: exigirInteiro(registro.vagas_simuladas),
    ufs_sem_votos: exigirLista(registro.ufs_sem_votos, exigirTexto),
    legendas: exigirLista(registro.legendas, lerContagemLegenda),
    partidos: exigirLista(registro.partidos, lerContagemPartido),
    ufs: exigirLista(registro.ufs, lerCasaUf),
  };
}

function lerContagemLegenda(valor: unknown): ContagemLegenda {
  const registro = exigirRegistro(valor);
  return { legenda: exigirTexto(registro.legenda), cadeiras: exigirInteiro(registro.cadeiras) };
}

function lerContagemPartido(valor: unknown): ContagemPartido {
  const registro = exigirRegistro(valor);
  return { partido: exigirInteiro(registro.partido), cadeiras: exigirInteiro(registro.cadeiras) };
}

function lerCasaUf(valor: unknown): CasaUfCadeiras {
  const registro = exigirRegistro(valor);
  return {
    uf: exigirTexto(registro.uf),
    cargo: exigirTexto(registro.cargo),
    vagas: exigirInteiro(registro.vagas),
    votos_validos: exigirInteiro(registro.votos_validos),
    quociente_eleitoral: exigirInteiro(registro.quociente_eleitoral),
    vagas_sem_candidato: exigirInteiro(registro.vagas_sem_candidato),
    listas: exigirLista(registro.listas, lerListaCadeiras),
    eleitos: exigirLista(registro.eleitos, lerEleitoCadeiras),
  };
}

function lerListaCadeiras(valor: unknown): ListaCadeiras {
  const registro = exigirRegistro(valor);
  return {
    legenda: exigirTexto(registro.legenda),
    votos: exigirInteiro(registro.votos),
    votos_legenda: exigirInteiro(registro.votos_legenda),
    quociente_partidario: exigirInteiro(registro.quociente_partidario),
    cadeiras_quociente: exigirInteiro(registro.cadeiras_quociente),
    cadeiras_media: exigirInteiro(registro.cadeiras_media),
    cadeiras_media_livre: exigirInteiro(registro.cadeiras_media_livre),
    cadeiras: exigirInteiro(registro.cadeiras),
  };
}

function lerEleitoCadeiras(valor: unknown): EleitoCadeiras {
  const registro = exigirRegistro(valor);
  return {
    numero: exigirInteiro(registro.numero),
    partido: exigirInteiro(registro.partido),
    legenda: exigirTexto(registro.legenda),
    votos: exigirInteiro(registro.votos),
    fase: exigirTexto(registro.fase),
    empate: exigirBooleano(registro.empate),
  };
}

function lerCandidatoMajoritario(valor: unknown): CandidatoMajoritario {
  const registro = exigirRegistro(valor);
  return {
    numero: exigirInteiro(registro.numero),
    partido: exigirInteiro(registro.partido),
    votos: exigirInteiro(registro.votos),
    fatia: exigirTexto(registro.fatia),
  };
}

function lerSenadoCadeiras(valor: unknown): SenadoCadeiras {
  const registro = exigirRegistro(valor);
  return {
    vagas: exigirInteiro(registro.vagas),
    vagas_simuladas: exigirInteiro(registro.vagas_simuladas),
    ufs_sem_votos: exigirLista(registro.ufs_sem_votos, exigirTexto),
    partidos: exigirLista(registro.partidos, lerContagemPartido),
    ufs: exigirLista(registro.ufs, (item) => {
      const uf = exigirRegistro(item);
      return {
        uf: exigirTexto(uf.uf),
        votos_validos: exigirInteiro(uf.votos_validos),
        eleitos: exigirLista(uf.eleitos, lerCandidatoMajoritario),
        empate: exigirBooleano(uf.empate),
      };
    }),
  };
}

function lerGovernoCadeiras(valor: unknown): GovernoCadeiras {
  const registro = exigirRegistro(valor);
  return {
    ufs_sem_votos: exigirLista(registro.ufs_sem_votos, exigirTexto),
    partidos: exigirLista(registro.partidos, (item) => {
      const linha = exigirRegistro(item);
      return {
        partido: exigirInteiro(linha.partido),
        eleitos: exigirInteiro(linha.eleitos),
        segundo_turno: exigirInteiro(linha.segundo_turno),
      };
    }),
    ufs: exigirLista(registro.ufs, (item) => {
      const uf = exigirRegistro(item);
      return {
        uf: exigirTexto(uf.uf),
        situacao: exigirTexto(uf.situacao),
        votos_validos: exigirInteiro(uf.votos_validos),
        candidatos: exigirLista(uf.candidatos, lerCandidatoMajoritario),
        empate: exigirBooleano(uf.empate),
      };
    }),
  };
}

function lerForcaPartido(valor: unknown): ForcaPartido {
  const registro = exigirRegistro(valor);
  return {
    partido: exigirInteiro(registro.partido),
    legenda: exigirTexto(registro.legenda),
    camara: exigirInteiro(registro.camara),
    assembleias: exigirInteiro(registro.assembleias),
    senado: exigirInteiro(registro.senado),
    governadores: exigirInteiro(registro.governadores),
    governadores_segundo_turno: exigirInteiro(registro.governadores_segundo_turno),
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

export function exigirLista<T>(valor: unknown, ler: (item: unknown) => T): T[] {
  if (!Array.isArray(valor)) {
    throw new RespostaInvalidaError();
  }
  return valor.map(ler);
}

function ehRegistro(valor: unknown): valor is Record<string, unknown> {
  return typeof valor === "object" && valor !== null && !Array.isArray(valor);
}

export function exigirRegistro(valor: unknown): Record<string, unknown> {
  if (!ehRegistro(valor)) {
    throw new RespostaInvalidaError();
  }
  return valor;
}

export function exigirTexto(valor: unknown): string {
  if (typeof valor !== "string") {
    throw new RespostaInvalidaError();
  }
  return valor;
}

export function exigirTextoOuNulo(valor: unknown): string | null {
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

export function exigirInteiro(valor: unknown): number {
  if (typeof valor !== "number" || !Number.isSafeInteger(valor) || valor < 0) {
    throw new RespostaInvalidaError();
  }
  return valor;
}
