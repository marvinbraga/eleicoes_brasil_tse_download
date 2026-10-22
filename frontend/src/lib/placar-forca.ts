// Linhas, colunas e ordenação do placar de força partidária (módulo puro).
import type { PlacarForca, RecorteForca, UnidadeForca } from "./forca.ts";
import { formatarInteiro, formatarPercentualContagem, TRACO } from "./fracao.ts";
import { compararNumero, compararTexto, type Direcao } from "./ordem.ts";
import { rotuloPartido } from "./partidos.ts";

export type Esfera = "nacional" | "estados" | "municipios";

export const ESFERAS: readonly Esfera[] = ["nacional", "estados", "municipios"];

export const ROTULOS_ESFERA: Record<Esfera, string> = {
  nacional: "Nacional",
  estados: "Estados",
  municipios: "Municípios",
};

// Fonte do tipo ChaveColuna: as fases B e C acrescentam colunas aqui.
export const CHAVES_COLUNA = [
  "presidente",
  "deputado_federal",
  "deputado_estadual",
  "ufs_lider_estadual",
  "municipios_lidera",
  "eleitorado_liderado",
  "presenca",
] as const;

export type ChaveColuna = (typeof CHAVES_COLUNA)[number];

export type Coluna = { chave: ChaveColuna; esfera: Esfera; titulo: string; curto: string; explicacao: string };

export type Valor = { ordem: number | null; fracao: number | null; texto: string; detalhe: string };

export type LinhaPlacar = { chave: string; rotulo: string; partidos: number[]; valores: Record<ChaveColuna, Valor> };

export type NivelPlacar = "pais" | "uf";

export const COLUNA_PADRAO: ChaveColuna = "deputado_federal";

const SEM_DADOS: Readonly<Valor> = Object.freeze({ ordem: null, fracao: null, texto: TRACO, detalhe: "Sem dados" });

export function colunasPlacar(limiar: number, nivel: NivelPlacar): Coluna[] {
  return [
    {
      chave: "presidente",
      esfera: "nacional",
      titulo: "Presidente (% válidos)",
      curto: "Presidente",
      explicacao: "Parte dos votos válidos para presidente que foi para o candidato do partido.",
    },
    {
      chave: "deputado_federal",
      esfera: "nacional",
      titulo: "Deputado federal (% válidos)",
      curto: "Dep. federal",
      explicacao: "Parte dos votos válidos para deputado federal (nominais mais legenda) que foi para o partido.",
    },
    {
      chave: "deputado_estadual",
      esfera: "estados",
      titulo: "Deputado estadual (% válidos)",
      curto: "Dep. estadual",
      explicacao: "Parte dos votos válidos para deputado estadual (nominais mais legenda) que foi para o partido.",
    },
    nivel === "pais"
      ? {
          chave: "ufs_lider_estadual",
          esfera: "estados",
          titulo: "UFs em 1º (dep. estadual)",
          curto: "UFs em 1º",
          explicacao: "Em quantas UFs o partido teve mais votos para deputado estadual do que qualquer outro.",
        }
      : {
          chave: "ufs_lider_estadual",
          esfera: "estados",
          titulo: "1º em dep. estadual",
          curto: "1º na UF",
          explicacao: "Se o partido teve mais votos para deputado estadual nesta UF do que qualquer outro.",
        },
    {
      chave: "municipios_lidera",
      esfera: "municipios",
      titulo: "Municípios em 1º",
      curto: "Municípios em 1º",
      explicacao: "Em quantos municípios o partido teve mais votos no cargo de referência do que qualquer outro.",
    },
    {
      chave: "eleitorado_liderado",
      esfera: "municipios",
      titulo: "Eleitorado dos municípios em 1º",
      curto: "Eleitorado em 1º",
      explicacao:
        "Parte dos votos válidos do cargo de referência que vem dos municípios onde o partido ficou em 1º.",
    },
    {
      chave: "presenca",
      esfera: "municipios",
      titulo: `Presença (≥ ${limiar}%)`,
      curto: `Presença ≥ ${limiar}%`,
      explicacao:
        "Quantos municípios deram ao partido pelo menos o limiar escolhido dos votos válidos do cargo de referência.",
    },
  ];
}

export function linhasPlacar(recorte: RecorteForca, limiar: number, nivel: NivelPlacar): LinhaPlacar[] {
  return recorte.unidades.map((unidade) => ({
    chave: unidade.chave,
    rotulo: rotuloUnidade(unidade),
    partidos: unidade.partidos,
    valores: valoresUnidade(recorte, unidade, limiar, nivel),
  }));
}

export function linhasPorUf(placar: PlacarForca, chave: string, limiar: number): LinhaPlacar[] {
  return placar.ufs.map((recorte) => {
    const unidade = recorte.unidades.find((item) => item.chave === chave);
    return {
      chave: recorte.codigo,
      rotulo: recorte.nome,
      partidos: unidade?.partidos ?? [],
      valores: unidade === undefined ? semDados() : valoresUnidade(recorte, unidade, limiar, "uf"),
    };
  });
}

export function ordenarPlacar(
  linhas: readonly LinhaPlacar[],
  coluna: ChaveColuna | "unidade",
  direcao: Direcao,
): LinhaPlacar[] {
  return [...linhas].sort((a, b) => {
    const principal =
      coluna === "unidade"
        ? compararTexto(a.rotulo, b.rotulo, direcao)
        : compararNumero(a.valores[coluna].ordem, b.valores[coluna].ordem, direcao);
    if (principal !== 0) {
      return principal;
    }
    const numero = (a.partidos[0] ?? Number.MAX_SAFE_INTEGER) - (b.partidos[0] ?? Number.MAX_SAFE_INTEGER);
    return numero !== 0 ? numero : compararTexto(a.rotulo, b.rotulo, "asc");
  });
}

export function rotuloUnidade(unidade: UnidadeForca): string {
  const primeiro = unidade.partidos[0];
  if (unidade.tipo === "partido" && primeiro !== undefined) {
    return rotuloPartido(primeiro);
  }
  return unidade.nome ?? unidade.chave;
}

// Literal completo: uma coluna nova em CHAVES_COLUNA sem entrada aqui é erro de compilação.
function semDados(): Record<ChaveColuna, Valor> {
  return {
    presidente: SEM_DADOS,
    deputado_federal: SEM_DADOS,
    deputado_estadual: SEM_DADOS,
    ufs_lider_estadual: SEM_DADOS,
    municipios_lidera: SEM_DADOS,
    eleitorado_liderado: SEM_DADOS,
    presenca: SEM_DADOS,
  };
}

function valoresUnidade(
  recorte: RecorteForca,
  unidade: UnidadeForca,
  limiar: number,
  nivel: NivelPlacar,
): Record<ChaveColuna, Valor> {
  const { base } = recorte;
  const municipal = unidade.municipal;
  const totalMunicipal = base.municipal;
  const presenca = municipal?.presenca.find((item) => item.limiar === limiar)?.municipios ?? null;
  return {
    presidente: percentualVotos(unidade.presidente, base.validos_presidente),
    deputado_federal: percentualVotos(unidade.deputado_federal, base.validos_deputado_federal),
    deputado_estadual: percentualVotos(unidade.deputado_estadual, base.validos_deputado_estadual),
    ufs_lider_estadual: lideraUfs(unidade.ufs_lider_estadual, base.ufs_deputado_estadual, nivel),
    municipios_lidera: contagem(
      municipal?.lidera ?? null,
      totalMunicipal?.municipios ?? null,
      (n) => `de ${formatarInteiro(n)} municípios`,
    ),
    eleitorado_liderado: eleitorado(municipal?.validos_liderados ?? null, totalMunicipal?.validos ?? null),
    presenca: contagem(
      presenca,
      totalMunicipal?.municipios ?? null,
      (n) => `de ${formatarInteiro(n)} municípios com ao menos ${limiar}% dos válidos`,
    ),
  };
}

function temBase(base: number | null): base is number {
  return base !== null && base > 0;
}

function percentualVotos(valor: number | null, base: number | null): Valor {
  if (valor === null || !temBase(base)) {
    return SEM_DADOS;
  }
  return {
    ordem: valor / base,
    fracao: valor / base,
    texto: formatarPercentualContagem(valor, base),
    detalhe: `${formatarInteiro(valor)} ${valor === 1 ? "voto" : "votos"}`,
  };
}

function lideraUfs(valor: number | null, base: number | null, nivel: NivelPlacar): Valor {
  if (valor === null || !temBase(base)) {
    return SEM_DADOS;
  }
  if (nivel === "uf") {
    return { ordem: valor, fracao: valor / base, texto: valor > 0 ? "Sim" : "Não", detalhe: "" };
  }
  const texto = `${formatarInteiro(valor)} de ${formatarInteiro(base)}`;
  return { ordem: valor, fracao: valor / base, texto, detalhe: `${texto} UFs com deputado estadual` };
}

function contagem(valor: number | null, base: number | null, detalhe: (base: number) => string): Valor {
  if (valor === null || !temBase(base)) {
    return SEM_DADOS;
  }
  return { ordem: valor, fracao: valor / base, texto: formatarInteiro(valor), detalhe: detalhe(base) };
}

function eleitorado(valor: number | null, base: number | null): Valor {
  if (valor === null || !temBase(base)) {
    return SEM_DADOS;
  }
  return {
    ordem: valor / base,
    fracao: valor / base,
    texto: formatarPercentualContagem(valor, base),
    detalhe: `${formatarInteiro(valor)} ${valor === 1 ? "voto válido" : "votos válidos"}`,
  };
}
