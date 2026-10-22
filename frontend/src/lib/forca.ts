// Leitura do placar de força partidária (GET /relatorios/dados/forca).
// Só caminhos relativos com `.ts`: os scripts `verificar-*.ts` rodam direto no Node.

export const LIMIAR_PADRAO = 5;

export type Presenca = { limiar: number; municipios: number };

export type MunicipalForca = { lidera: number; validos_liderados: number; presenca: Presenca[] };

export type BaseMunicipalForca = { municipios: number; validos: number; empates: number };

export type BaseForca = {
  validos_presidente: number | null;
  validos_deputado_federal: number | null;
  validos_deputado_estadual: number | null;
  ufs_deputado_estadual: number | null;
  municipal: BaseMunicipalForca | null;
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
};

export type RecorteForca = { codigo: string; nome: string; base: BaseForca; unidades: UnidadeForca[] };

export type FaltandoForca = { cargo: string; comando: string };

export type PlacarForca = {
  ano: number;
  turno: number;
  cargo_referencia: string;
  limiares: number[];
  faltando: FaltandoForca[];
  pais: RecorteForca;
  ufs: RecorteForca[];
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
