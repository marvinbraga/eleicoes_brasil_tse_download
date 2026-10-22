import { formatarInteiro, formatarPercentualContagem } from "./fracao.ts";
import { LIMITE_PARTIDOS, MEDIDAS_PADRAO, type ItemBarra, type MedidasBarras } from "./grafico-poder.ts";

// Os rótulos são "<sigla de 2024> <número>" (D14). "SOLIDARIEDADE 77" tem 16 caracteres:
// 0,6 × 12 × 16 ≈ 115 px, mais 8 px de folga; 136 px deixam espaço para siglas um pouco maiores.
export const MEDIDAS_MUNICIPAIS: MedidasBarras = { ...MEDIDAS_PADRAO, esquerda: 136 };

export type PartidoMunicipal = {
  numero: number;
  sigla_2024: string;
  numero_2026: number | null;
  sigla_2026: string | null;
  equivalencia: string;
  nota: string;
  prefeitos: number;
  eleitorado_governado: number;
  vereadores: number;
  municipios_com_vereador: number;
};

export type TotaisMunicipais = {
  municipios: number;
  com_prefeito: number;
  sem_prefeito: number;
  suplementares: number;
  eleitorado: number;
  vereadores: number;
  vagas_vereador: number;
  divergencias_vagas: number;
};

export type PrefeitoMunicipal = {
  numero_partido: number;
  sigla_2024: string;
  sigla_2026: string | null;
  nome_urna: string;
  turno: number;
  suplementar: boolean;
  data_eleicao: string;
};

export type VereadoresMunicipio = { numero: number; sigla_2024: string; eleitos: number };

export type MunicipioMunicipal = {
  uf: string;
  codigo_tse: string;
  nome: string;
  eleitorado: number;
  prefeito: PrefeitoMunicipal | null;
  vereadores: VereadoresMunicipio[];
};

export type RelatorioMunicipais = {
  ano: number;
  uf: string | null;
  data_corte: string;
  importado_em: string;
  equivalencia_versao: string;
  totais: TotaisMunicipais;
  partidos: PartidoMunicipal[];
  municipios: MunicipioMunicipal[];
  notas: string[];
};

export class RespostaMunicipaisInvalidaError extends Error {
  constructor() {
    super("A API devolveu um JSON que não confere com o relatório.");
    this.name = "RespostaMunicipaisInvalidaError";
  }
}

export function lerMunicipais2024(valor: unknown): RelatorioMunicipais {
  const r = registro(valor);
  return {
    ano: inteiro(r.ano),
    uf: textoOuNulo(r.uf),
    data_corte: texto(r.data_corte),
    importado_em: texto(r.importado_em),
    equivalencia_versao: texto(r.equivalencia_versao),
    totais: lerTotais(r.totais),
    partidos: lista(r.partidos, lerPartido),
    municipios: lista(r.municipios, lerMunicipio),
    notas: lista(r.notas, texto),
  };
}

export function rotuloBarra(partido: PartidoMunicipal): string {
  return `${partido.sigla_2024} ${partido.numero}`;
}

export function rotuloComEquivalencia(partido: PartidoMunicipal): string {
  const em2026 = sigla2026Diferente(partido);
  return em2026 === null ? rotuloBarra(partido) : `${rotuloBarra(partido)} (em 2026: ${em2026})`;
}

export function formatarCorte(iso: string): string {
  const partes = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})/.exec(iso);
  if (partes === null) {
    return iso;
  }
  const [, ano, mes, dia, hora, minuto] = partes;
  return `${dia}/${mes}/${ano} às ${hora}:${minuto}`;
}

export function itensPrefeituras(relatorio: RelatorioMunicipais): ItemBarra[] {
  return itens(relatorio.partidos, (p) => p.prefeitos, relatorio.totais.com_prefeito, (n) =>
    contar(n, "prefeitura", "prefeituras"),
  );
}

export function itensEleitorado(relatorio: RelatorioMunicipais): ItemBarra[] {
  return itens(relatorio.partidos, (p) => p.eleitorado_governado, relatorio.totais.eleitorado, (n) =>
    contar(n, "eleitor", "eleitores"),
  );
}

export function itensVereadores(relatorio: RelatorioMunicipais): ItemBarra[] {
  return itens(relatorio.partidos, (p) => p.vereadores, relatorio.totais.vereadores, (n) =>
    contar(n, "vereador", "vereadores"),
  );
}

export function leituraMunicipais(relatorio: RelatorioMunicipais): string[] {
  const { totais } = relatorio;
  const frases = [
    `Até ${formatarCorte(relatorio.data_corte)}, o TSE registra ` +
      `${contar(totais.com_prefeito, "prefeito eleito", "prefeitos eleitos")} em ` +
      `${contar(totais.municipios, "município", "municípios")}.`,
  ];
  const lider = ordenar(relatorio.partidos, (p) => p.prefeitos)[0];
  if (lider !== undefined) {
    frases.push(
      `${lider.sigla_2024} tem mais prefeituras: ${formatarInteiro(lider.prefeitos)} ` +
        `(${formatarPercentualContagem(lider.prefeitos, totais.com_prefeito)}), com ` +
        `${formatarPercentualContagem(lider.eleitorado_governado, totais.eleitorado)} do eleitorado.`,
    );
  }
  if (totais.sem_prefeito > 0) {
    frases.push(
      totais.sem_prefeito === 1
        ? "1 município está sem prefeito eleito."
        : `${formatarInteiro(totais.sem_prefeito)} municípios estão sem prefeito eleito.`,
    );
  }
  if (totais.suplementares > 0) {
    frases.push(
      totais.suplementares === 1
        ? "1 prefeito veio de eleição suplementar."
        : `${formatarInteiro(totais.suplementares)} prefeitos vieram de eleição suplementar.`,
    );
  }
  return frases;
}

function itens(
  partidos: readonly PartidoMunicipal[],
  valorDe: (partido: PartidoMunicipal) => number,
  total: number,
  quantidade: (n: number) => string,
): ItemBarra[] {
  const ordenados = ordenar(partidos, valorDe);
  const visiveis = ordenados.length > LIMITE_PARTIDOS + 1 ? ordenados.slice(0, LIMITE_PARTIDOS) : ordenados;
  const resultado: ItemBarra[] = visiveis.map((partido) => {
    const valor = valorDe(partido);
    const em2026 = sigla2026Diferente(partido);
    return {
      chave: String(partido.numero),
      rotulo: rotuloBarra(partido),
      valor,
      texto: formatarPercentualContagem(valor, total),
      detalhe: em2026 === null ? quantidade(valor) : `${quantidade(valor)}\nEm 2026: ${em2026}`,
    };
  });
  const resto = ordenados.slice(visiveis.length);
  if (resto.length > 0) {
    const valor = resto.reduce((soma, partido) => soma + valorDe(partido), 0);
    resultado.push({
      chave: "outros",
      rotulo: "Outros",
      valor,
      texto: formatarPercentualContagem(valor, total),
      detalhe: `${formatarInteiro(resto.length)} partidos, ${quantidade(valor)}`,
    });
  }
  return resultado;
}

function ordenar(
  partidos: readonly PartidoMunicipal[],
  valorDe: (partido: PartidoMunicipal) => number,
): PartidoMunicipal[] {
  return partidos
    .filter((partido) => valorDe(partido) > 0)
    .sort((a, b) => valorDe(b) - valorDe(a) || a.numero - b.numero);
}

function sigla2026Diferente(partido: PartidoMunicipal): string | null {
  if (partido.sigla_2026 === partido.sigla_2024) {
    return null;
  }
  return partido.sigla_2026 ?? "sem correspondência";
}

function contar(n: number, singular: string, plural: string): string {
  return `${formatarInteiro(n)} ${n === 1 ? singular : plural}`;
}

function lerTotais(valor: unknown): TotaisMunicipais {
  const r = registro(valor);
  return {
    municipios: inteiro(r.municipios),
    com_prefeito: inteiro(r.com_prefeito),
    sem_prefeito: inteiro(r.sem_prefeito),
    suplementares: inteiro(r.suplementares),
    eleitorado: inteiro(r.eleitorado),
    vereadores: inteiro(r.vereadores),
    vagas_vereador: inteiro(r.vagas_vereador),
    divergencias_vagas: inteiro(r.divergencias_vagas),
  };
}

function lerPartido(valor: unknown): PartidoMunicipal {
  const r = registro(valor);
  return {
    numero: inteiro(r.numero),
    sigla_2024: texto(r.sigla_2024),
    numero_2026: inteiroOuNulo(r.numero_2026),
    sigla_2026: textoOuNulo(r.sigla_2026),
    equivalencia: texto(r.equivalencia),
    nota: texto(r.nota),
    prefeitos: inteiro(r.prefeitos),
    eleitorado_governado: inteiro(r.eleitorado_governado),
    vereadores: inteiro(r.vereadores),
    municipios_com_vereador: inteiro(r.municipios_com_vereador),
  };
}

function lerMunicipio(valor: unknown): MunicipioMunicipal {
  const r = registro(valor);
  return {
    uf: texto(r.uf),
    codigo_tse: texto(r.codigo_tse),
    nome: texto(r.nome),
    eleitorado: inteiro(r.eleitorado),
    prefeito: r.prefeito === null ? null : lerPrefeito(r.prefeito),
    vereadores: lista(r.vereadores, lerVereadores),
  };
}

function lerPrefeito(valor: unknown): PrefeitoMunicipal {
  const r = registro(valor);
  return {
    numero_partido: inteiro(r.numero_partido),
    sigla_2024: texto(r.sigla_2024),
    sigla_2026: textoOuNulo(r.sigla_2026),
    nome_urna: texto(r.nome_urna),
    turno: inteiro(r.turno),
    suplementar: booleano(r.suplementar),
    data_eleicao: texto(r.data_eleicao),
  };
}

function lerVereadores(valor: unknown): VereadoresMunicipio {
  const r = registro(valor);
  return { numero: inteiro(r.numero), sigla_2024: texto(r.sigla_2024), eleitos: inteiro(r.eleitos) };
}

function registro(valor: unknown): Record<string, unknown> {
  if (typeof valor !== "object" || valor === null || Array.isArray(valor)) {
    throw new RespostaMunicipaisInvalidaError();
  }
  return valor as Record<string, unknown>;
}

function inteiro(valor: unknown): number {
  if (typeof valor !== "number" || !Number.isSafeInteger(valor) || valor < 0) {
    throw new RespostaMunicipaisInvalidaError();
  }
  return valor;
}

function inteiroOuNulo(valor: unknown): number | null {
  return valor === null ? null : inteiro(valor);
}

function texto(valor: unknown): string {
  if (typeof valor !== "string") {
    throw new RespostaMunicipaisInvalidaError();
  }
  return valor;
}

function textoOuNulo(valor: unknown): string | null {
  return valor === null ? null : texto(valor);
}

function booleano(valor: unknown): boolean {
  if (typeof valor !== "boolean") {
    throw new RespostaMunicipaisInvalidaError();
  }
  return valor;
}

function lista<T>(valor: unknown, ler: (item: unknown) => T): T[] {
  if (!Array.isArray(valor)) {
    throw new RespostaMunicipaisInvalidaError();
  }
  return valor.map(ler);
}
