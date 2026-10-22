// Leitura do JSON de capilaridade, opções de recorte e leitura da consulta da página.
import {
  CHAVES_FAIXA,
  CLASSES_CAPILARIDADE,
  type ClasseCapilaridade,
  type FaixaCapilaridade,
  type LugarCapilaridade,
  type ParteCapilaridade,
  type PartidoCapilaridade,
  type PresencaCapilaridade,
  type Recorte,
  type RelatorioCapilaridade,
  type ResumoCapilaridade,
  type SubdivisaoCapilaridade,
  type TipoRecorte,
} from "./capilaridade";
import { UFS, escolher, nomeUf, type ConsultaRelatorio, type ValorConsulta } from "@/lib/eleicoes";
import {
  RespostaInvalidaError,
  exigirInteiro,
  exigirLista,
  exigirRegistro,
  exigirTexto,
} from "@/lib/relatorios";

export const RECORTE_BRASIL = "brasil";

const REGIOES = [
  { sigla: "NO", nome: "Norte" },
  { sigla: "NE", nome: "Nordeste" },
  { sigla: "CO", nome: "Centro-Oeste" },
  { sigla: "SE", nome: "Sudeste" },
  { sigla: "S", nome: "Sul" },
] as const;

const PREFIXO_REGIAO = "regiao-";
const PREFIXO_UF = "uf-";
const EXTERIOR = "ZZ";

export const RECORTES: readonly { value: string; label: string }[] = [
  { value: RECORTE_BRASIL, label: "Brasil" },
  ...REGIOES.map((regiao) => ({
    value: `${PREFIXO_REGIAO}${regiao.sigla}`,
    label: `Região ${regiao.nome}`,
  })),
  ...UFS.filter((uf) => uf.value !== EXTERIOR).map((uf) => ({
    value: `${PREFIXO_UF}${uf.value}`,
    label: nomeUf(uf.value),
  })),
];

const VALORES_RECORTE: readonly string[] = RECORTES.map((item) => item.value);

export type ConsultaCapilaridade = ConsultaRelatorio & {
  recorte?: ValorConsulta;
  partido?: ValorConsulta;
};

export function lerRecorte(valor: ValorConsulta): string {
  return escolher(valor, VALORES_RECORTE, RECORTE_BRASIL);
}

export function paramsRecorte(recorte: string): Record<string, string> {
  if (recorte.startsWith(PREFIXO_REGIAO)) {
    return { regiao: recorte.slice(PREFIXO_REGIAO.length) };
  }
  if (recorte.startsWith(PREFIXO_UF)) {
    return { uf: recorte.slice(PREFIXO_UF.length) };
  }
  return {};
}

// D16: sem partido na consulta, ou com um que não está na resposta, abre no de mais votos.
export function partidoEscolhido(
  dados: RelatorioCapilaridade,
  valor: ValorConsulta,
): PartidoCapilaridade | null {
  const bruto = Array.isArray(valor) ? valor[0] : valor;
  const numero = bruto === undefined ? Number.NaN : Number(bruto);
  const pedido = dados.partidos.find((item) => item.partido === numero);
  if (pedido !== undefined) {
    return pedido;
  }
  let melhor: PartidoCapilaridade | null = null;
  for (const item of dados.partidos) {
    if (
      melhor === null ||
      item.votos > melhor.votos ||
      (item.votos === melhor.votos && item.partido < melhor.partido)
    ) {
      melhor = item;
    }
  }
  return melhor;
}

export function lerCapilaridade(valor: unknown): RelatorioCapilaridade {
  const registro = exigirRegistro(valor);
  const partidos = exigirLista(registro.partidos, lerPartido);
  const resumo = exigirLista(registro.resumo, lerResumo);
  if (resumo.length !== partidos.length) {
    throw new RespostaInvalidaError();
  }
  return {
    ano: exigirInteiro(registro.ano),
    turno: exigirInteiro(registro.turno),
    cargo: exigirTexto(registro.cargo),
    recorte: lerRecorteJson(registro.recorte),
    municipios: exigirInteiro(registro.municipios),
    ufs: exigirInteiro(registro.ufs),
    sem_validos: exigirInteiro(registro.sem_validos),
    votos_validos: exigirInteiro(registro.votos_validos),
    exterior: exigirInteiro(registro.exterior),
    limites: lerLimites(registro.limites),
    partidos,
    resumo,
    notas: exigirLista(registro.notas, exigirTexto),
  };
}

function lerRecorteJson(valor: unknown): Recorte {
  const registro = exigirRegistro(valor);
  const tipo = exigirTexto(registro.tipo);
  if (tipo !== "pais" && tipo !== "regiao" && tipo !== "uf") {
    throw new RespostaInvalidaError();
  }
  return {
    tipo: tipo satisfies TipoRecorte,
    codigo: exigirTexto(registro.codigo),
    nome: exigirTexto(registro.nome),
  };
}

function lerLimites(valor: unknown): Record<string, string | number> {
  const registro = exigirRegistro(valor);
  const limites: Record<string, string | number> = {};
  for (const [chave, item] of Object.entries(registro)) {
    limites[chave] = typeof item === "number" ? exigirInteiro(item) : exigirTexto(item);
  }
  return limites;
}

function lerClasse(valor: unknown): ClasseCapilaridade {
  const texto = exigirTexto(valor);
  const classe = CLASSES_CAPILARIDADE.find((item) => item === texto);
  if (classe === undefined) {
    throw new RespostaInvalidaError();
  }
  return classe;
}

function lerParte(valor: unknown): ParteCapilaridade {
  const registro = exigirRegistro(valor);
  return {
    municipios: exigirInteiro(registro.municipios),
    votos: exigirInteiro(registro.votos),
    parte: exigirTexto(registro.parte),
    parte_texto: exigirTexto(registro.parte_texto),
    eleitorado: exigirTexto(registro.eleitorado),
    eleitorado_texto: exigirTexto(registro.eleitorado_texto),
    vezes: exigirTexto(registro.vezes),
  };
}

function lerParteOuNula(valor: unknown): ParteCapilaridade | null {
  return valor === null ? null : lerParte(valor);
}

function lerSubdivisao(valor: unknown): SubdivisaoCapilaridade {
  const registro = exigirRegistro(valor);
  return {
    ...lerParte(registro),
    codigo: exigirTexto(registro.codigo),
    nome: exigirTexto(registro.nome),
  };
}

function lerPresenca(valor: unknown): PresencaCapilaridade {
  const registro = exigirRegistro(valor);
  return {
    municipios: exigirInteiro(registro.municipios),
    parte: exigirTexto(registro.parte),
    parte_texto: exigirTexto(registro.parte_texto),
  };
}

function lerFaixas(valor: unknown): FaixaCapilaridade[] {
  const faixas = exigirLista(valor, (item): FaixaCapilaridade => {
    const registro = exigirRegistro(item);
    const chave = CHAVES_FAIXA.find((candidata) => candidata === registro.chave);
    if (chave === undefined) {
      throw new RespostaInvalidaError();
    }
    return {
      chave,
      municipios: exigirInteiro(registro.municipios),
      votos_validos: exigirInteiro(registro.votos_validos),
      votos: exigirInteiro(registro.votos),
    };
  });
  const ordem = faixas.map((faixa) => faixa.chave).join(",");
  if (ordem !== CHAVES_FAIXA.join(",")) {
    throw new RespostaInvalidaError();
  }
  return faixas;
}

function lerLugar(valor: unknown): LugarCapilaridade {
  const registro = exigirRegistro(valor);
  return {
    codigo: exigirTexto(registro.codigo),
    nome: exigirTexto(registro.nome),
    votos: exigirInteiro(registro.votos),
    votos_validos: exigirInteiro(registro.votos_validos),
    fatia: exigirTexto(registro.fatia),
    fatia_texto: exigirTexto(registro.fatia_texto),
  };
}

function lerPartido(valor: unknown): PartidoCapilaridade {
  const registro = exigirRegistro(valor);
  return {
    partido: exigirInteiro(registro.partido),
    votos: exigirInteiro(registro.votos),
    votos_validos: exigirInteiro(registro.votos_validos),
    votos_validos_recorte: exigirInteiro(registro.votos_validos_recorte),
    fatia: exigirTexto(registro.fatia),
    fatia_texto: exigirTexto(registro.fatia_texto),
    fatia_recorte_texto: exigirTexto(registro.fatia_recorte_texto),
    ufs_com_voto: exigirInteiro(registro.ufs_com_voto),
    municipios: exigirInteiro(registro.municipios),
    indice: exigirTexto(registro.indice),
    indice_texto: exigirTexto(registro.indice_texto),
    indice_100: exigirInteiro(registro.indice_100),
    top10: lerParte(registro.top10),
    presenca: lerPresenca(registro.presenca),
    capitais: lerParteOuNula(registro.capitais),
    subdivisoes: exigirLista(registro.subdivisoes, lerSubdivisao),
    faixas: lerFaixas(registro.faixas),
    fortes: exigirLista(registro.fortes, lerLugar),
    maiores: exigirLista(registro.maiores, lerLugar),
    classe: lerClasse(registro.classe),
    rotulo_classe: exigirTexto(registro.rotulo_classe),
    motivo: exigirTexto(registro.motivo),
  };
}

function lerResumo(valor: unknown): ResumoCapilaridade {
  const registro = exigirRegistro(valor);
  return {
    partido: exigirInteiro(registro.partido),
    votos: exigirInteiro(registro.votos),
    fatia: exigirTexto(registro.fatia),
    fatia_texto: exigirTexto(registro.fatia_texto),
    indice: exigirTexto(registro.indice),
    indice_100: exigirInteiro(registro.indice_100),
    presenca: exigirTexto(registro.presenca),
    presenca_texto: exigirTexto(registro.presenca_texto),
    ufs_com_voto: exigirInteiro(registro.ufs_com_voto),
    classe: lerClasse(registro.classe),
    rotulo_classe: exigirTexto(registro.rotulo_classe),
  };
}
