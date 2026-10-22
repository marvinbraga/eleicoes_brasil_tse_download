// Leitura do placar de força partidária (GET /relatorios/dados/forca).
// Só caminhos relativos com `.ts`: os scripts `verificar-*.ts` rodam direto no Node.

export const LIMIAR_PADRAO = 5;

export type Presenca = { limiar: number; municipios: number };

export type MunicipalForca = { lidera: number; validos_liderados: number; presenca: Presenca[] };

export type BaseMunicipalForca = { municipios: number; validos: number; empates: number };

// Cadeiras do recorte (fase B): no Brasil, os totais da simulação; na UF, a soma das linhas de partido.
export type BaseCadeirasForca = { camara: number; senado: number; governadores: number; assembleias: number };

// Denominadores de 2024 do recorte (fase C): "BR" no Brasil, a UF no recorte; o DF não tem.
export type BaseMunicipal2024Forca = { municipios: number; com_prefeito: number; eleitorado: number; vereadores: number };

export type BaseForca = {
  validos_presidente: number | null;
  validos_deputado_federal: number | null;
  validos_deputado_estadual: number | null;
  ufs_deputado_estadual: number | null;
  municipal: BaseMunicipalForca | null;
  cadeiras: BaseCadeirasForca | null;
  municipal_2024: BaseMunicipal2024Forca | null;
};

export type TipoUnidadeForca = "partido" | "federacao";

export type UnidadeForca = {
  chave: string;
  tipo: TipoUnidadeForca;
  nome: string | null;
  partidos: number[];
  presidente: number | null;
  deputado_federal: number | null;
  deputado_estadual: number | null;
  ufs_lider_estadual: number | null;
  municipal: MunicipalForca | null;
  camara: number | null;
  senado: number | null;
  governador_1t: number | null;
  governador_2t: number | null;
  assembleia: number | null;
  prefeitos: number | null;
  eleitorado_governado: number | null;
  vereadores: number | null;
  // Voto só no número do partido, nas mesmas linhas do total (fase D); null nas federações.
  legenda_federal: number | null;
  legenda_estadual: number | null;
};

// unidades: uma linha por partido. federadas: a visão com federações (F18), em que as federações
// e os partidos fora delas são reclassificados juntos; vazia sem federações.
export type RecorteForca = {
  codigo: string;
  nome: string;
  base: BaseForca;
  unidades: UnidadeForca[];
  federadas: UnidadeForca[];
  base_federada: BaseForca | null;
};

export type FaltandoForca = { cargo: string; comando: string };

export type BlocoCadeirasForca = { disponivel: boolean; comando: string | null; totais: BaseCadeirasForca | null };

export type BlocoMunicipal2024Forca = {
  disponivel: boolean;
  comando: string | null;
  data_corte: string | null;
  totais: BaseMunicipal2024Forca | null;
};

export type PlacarForca = {
  ano: number;
  turno: number;
  cargo_referencia: string;
  limiares: number[];
  faltando: FaltandoForca[];
  pais: RecorteForca;
  ufs: RecorteForca[];
  // null: a API não tem a porta de cadeiras (fase A); as colunas ficam ocultas (F20).
  cadeiras: BlocoCadeirasForca | null;
  // null: a API não tem a porta de 2024; as colunas ficam ocultas.
  municipal_2024: BlocoMunicipal2024Forca | null;
};

export class RespostaForcaInvalidaError extends Error {
  constructor() {
    super("A API devolveu um JSON que não confere com o placar de força.");
    this.name = "RespostaForcaInvalidaError";
  }
}

export function lerPlacarForca(valor: unknown): PlacarForca {
  const registro = exigirRegistro(valor);
  return {
    ano: exigirInteiro(registro.ano),
    turno: exigirInteiro(registro.turno),
    cargo_referencia: exigirTexto(registro.cargo_referencia),
    limiares: exigirLista(registro.limiares, exigirInteiro),
    faltando: exigirLista(registro.faltando, lerFaltando),
    pais: lerRecorte(registro.pais),
    ufs: exigirLista(registro.ufs, lerRecorte),
    cadeiras: ausente(registro.cadeiras) ? null : lerBlocoCadeiras(registro.cadeiras),
    municipal_2024: ausente(registro.municipal_2024) ? null : lerBloco2024(registro.municipal_2024),
  };
}

function lerBloco2024(valor: unknown): BlocoMunicipal2024Forca {
  const registro = exigirRegistro(valor);
  return {
    disponivel: exigirBooleano(registro.disponivel),
    comando: exigirTextoOuNulo(registro.comando),
    data_corte: exigirTextoOuNulo(registro.data_corte),
    totais: ausente(registro.totais) ? null : lerBase2024(registro.totais),
  };
}

function lerBase2024(valor: unknown): BaseMunicipal2024Forca {
  const registro = exigirRegistro(valor);
  return {
    municipios: exigirInteiro(registro.municipios),
    com_prefeito: exigirInteiro(registro.com_prefeito),
    eleitorado: exigirInteiro(registro.eleitorado),
    vereadores: exigirInteiro(registro.vereadores),
  };
}

function lerBlocoCadeiras(valor: unknown): BlocoCadeirasForca {
  const registro = exigirRegistro(valor);
  return {
    disponivel: exigirBooleano(registro.disponivel),
    comando: exigirTextoOuNulo(registro.comando),
    totais: ausente(registro.totais) ? null : lerBaseCadeiras(registro.totais),
  };
}

function lerBaseCadeiras(valor: unknown): BaseCadeirasForca {
  const registro = exigirRegistro(valor);
  return {
    camara: exigirInteiro(registro.camara),
    senado: exigirInteiro(registro.senado),
    governadores: exigirInteiro(registro.governadores),
    assembleias: exigirInteiro(registro.assembleias),
  };
}

function lerFaltando(valor: unknown): FaltandoForca {
  const registro = exigirRegistro(valor);
  return { cargo: exigirTexto(registro.cargo), comando: exigirTexto(registro.comando) };
}

function lerRecorte(valor: unknown): RecorteForca {
  const registro = exigirRegistro(valor);
  return {
    codigo: exigirTexto(registro.codigo),
    nome: exigirTexto(registro.nome),
    base: lerBase(registro.base),
    unidades: exigirLista(registro.unidades, lerUnidade),
    federadas: ausente(registro.federadas) ? [] : exigirLista(registro.federadas, lerUnidade),
    base_federada: ausente(registro.base_federada) ? null : lerBase(registro.base_federada),
  };
}

function lerBase(valor: unknown): BaseForca {
  const registro = exigirRegistro(valor);
  return {
    validos_presidente: exigirInteiroOuNulo(registro.validos_presidente),
    validos_deputado_federal: exigirInteiroOuNulo(registro.validos_deputado_federal),
    validos_deputado_estadual: exigirInteiroOuNulo(registro.validos_deputado_estadual),
    ufs_deputado_estadual: exigirInteiroOuNulo(registro.ufs_deputado_estadual),
    municipal: ausente(registro.municipal) ? null : lerBaseMunicipal(registro.municipal),
    cadeiras: ausente(registro.cadeiras) ? null : lerBaseCadeiras(registro.cadeiras),
    municipal_2024: ausente(registro.municipal_2024) ? null : lerBase2024(registro.municipal_2024),
  };
}

function lerBaseMunicipal(valor: unknown): BaseMunicipalForca {
  const registro = exigirRegistro(valor);
  return {
    municipios: exigirInteiro(registro.municipios),
    validos: exigirInteiro(registro.validos),
    empates: exigirInteiro(registro.empates),
  };
}

function lerUnidade(valor: unknown): UnidadeForca {
  const registro = exigirRegistro(valor);
  return {
    chave: exigirTexto(registro.chave),
    tipo: exigirTipo(registro.tipo),
    nome: exigirTextoOuNulo(registro.nome),
    partidos: exigirLista(registro.partidos, exigirInteiro),
    presidente: exigirInteiroOuNulo(registro.presidente),
    deputado_federal: exigirInteiroOuNulo(registro.deputado_federal),
    deputado_estadual: exigirInteiroOuNulo(registro.deputado_estadual),
    ufs_lider_estadual: exigirInteiroOuNulo(registro.ufs_lider_estadual),
    municipal: ausente(registro.municipal) ? null : lerMunicipal(registro.municipal),
    camara: exigirInteiroOuNulo(registro.camara),
    senado: exigirInteiroOuNulo(registro.senado),
    governador_1t: exigirInteiroOuNulo(registro.governador_1t),
    governador_2t: exigirInteiroOuNulo(registro.governador_2t),
    assembleia: exigirInteiroOuNulo(registro.assembleia),
    prefeitos: exigirInteiroOuNulo(registro.prefeitos),
    eleitorado_governado: exigirInteiroOuNulo(registro.eleitorado_governado),
    vereadores: exigirInteiroOuNulo(registro.vereadores),
    legenda_federal: exigirInteiroOuNulo(registro.legenda_federal),
    legenda_estadual: exigirInteiroOuNulo(registro.legenda_estadual),
  };
}

function lerMunicipal(valor: unknown): MunicipalForca {
  const registro = exigirRegistro(valor);
  return {
    lidera: exigirInteiro(registro.lidera),
    validos_liderados: exigirInteiro(registro.validos_liderados),
    presenca: exigirLista(registro.presenca, lerPresenca),
  };
}

function lerPresenca(valor: unknown): Presenca {
  const registro = exigirRegistro(valor);
  return { limiar: exigirInteiro(registro.limiar), municipios: exigirInteiro(registro.municipios) };
}

function exigirTipo(valor: unknown): TipoUnidadeForca {
  if (valor !== "partido" && valor !== "federacao") {
    throw new RespostaForcaInvalidaError();
  }
  return valor;
}

function ausente(valor: unknown): boolean {
  return valor === null || valor === undefined;
}

function exigirLista<T>(valor: unknown, ler: (item: unknown) => T): T[] {
  if (!Array.isArray(valor)) {
    throw new RespostaForcaInvalidaError();
  }
  return valor.map(ler);
}

function ehRegistro(valor: unknown): valor is Record<string, unknown> {
  return typeof valor === "object" && valor !== null && !Array.isArray(valor);
}

function exigirRegistro(valor: unknown): Record<string, unknown> {
  if (!ehRegistro(valor)) {
    throw new RespostaForcaInvalidaError();
  }
  return valor;
}

function exigirTexto(valor: unknown): string {
  if (typeof valor !== "string") {
    throw new RespostaForcaInvalidaError();
  }
  return valor;
}

function exigirBooleano(valor: unknown): boolean {
  if (typeof valor !== "boolean") {
    throw new RespostaForcaInvalidaError();
  }
  return valor;
}

function exigirTextoOuNulo(valor: unknown): string | null {
  return ausente(valor) ? null : exigirTexto(valor);
}

function exigirInteiro(valor: unknown): number {
  if (typeof valor !== "number" || !Number.isSafeInteger(valor) || valor < 0) {
    throw new RespostaForcaInvalidaError();
  }
  return valor;
}

function exigirInteiroOuNulo(valor: unknown): number | null {
  return ausente(valor) ? null : exigirInteiro(valor);
}
