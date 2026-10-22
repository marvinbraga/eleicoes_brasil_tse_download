// Linhas, colunas e ordenação do placar de força partidária (módulo puro).
import type {
  BaseCadeirasForca,
  BaseMunicipal2024Forca,
  BlocoMunicipal2024Forca,
  PlacarForca, RecorteForca, TipoUnidadeForca, UnidadeForca } from "./forca.ts";
import { formatarInteiro, formatarPercentualContagem, TRACO } from "./fracao.ts";
import { formatarCorte } from "./municipais-2024.ts";
import { compararNumero, compararTexto, type Direcao } from "./ordem.ts";
import { rotuloPartido } from "./partidos.ts";

export type Esfera = "nacional" | "estados" | "municipios";

export const ESFERAS: readonly Esfera[] = ["nacional", "estados", "municipios"];

export const ROTULOS_ESFERA: Record<Esfera, string> = {
  nacional: "Nacional",
  estados: "Estados",
  municipios: "Municípios",
};

// Grupos de colunas da tabela: as três esferas (que também viram painéis do gráfico) e o
// "Perfil do voto" (fase D), que fica fora do gráfico e de qualquer índice.
export type GrupoColuna = Esfera | "perfil";

export const GRUPOS_COLUNA: readonly GrupoColuna[] = [...ESFERAS, "perfil"];

export const ROTULOS_GRUPO: Record<GrupoColuna, string> = { ...ROTULOS_ESFERA, perfil: "Perfil do voto" };

// Fonte do tipo ChaveColuna: as fases B e C acrescentam colunas aqui.
export const CHAVES_COLUNA = [
  "presidente",
  "deputado_federal",
  "deputado_estadual",
  "ufs_lider_estadual",
  "municipios_lidera",
  "eleitorado_liderado",
  "presenca",
  "camara",
  "senado",
  "governador_1t",
  "governador_2t",
  "assembleia",
  "prefeitos",
  "eleitorado_governado",
  "vereadores",
  "legenda_federal",
  "legenda_estadual",
] as const;

export type ChaveColuna = (typeof CHAVES_COLUNA)[number];

export type Coluna = { chave: ChaveColuna; esfera: GrupoColuna; titulo: string; curto: string; explicacao: string };

export type Valor = { ordem: number | null; fracao: number | null; texto: string; detalhe: string };

export type LinhaPlacar = {
  chave: string;
  tipo: TipoUnidadeForca;
  rotulo: string;
  partidos: number[];
  valores: Record<ChaveColuna, Valor>;
};

export type NivelPlacar = "pais" | "uf";

// Blocos opcionais da resposta que decidem quais colunas aparecem (F20).
export type BlocosPlacar = Pick<PlacarForca, "cadeiras" | "municipal_2024">;

export type ModoUnidades = "partidos" | "federacoes";

export const MODOS_UNIDADES: readonly { value: ModoUnidades; label: string }[] = [
  { value: "partidos", label: "Partidos" },
  { value: "federacoes", label: "Federações e partidos fora delas" },
];

// Contagens aditivas: a linha de totais soma estas, e só nas linhas de partido. O 2º turno de
// governador fica fora: a soma seria o dobro das UFs com 2º turno (F14). O eleitorado governado
// também, porque a célula mostra a parte do eleitorado, não a contagem.
const CHAVES_SOMAVEIS = ["camara", "senado", "governador_1t", "assembleia", "prefeitos", "vereadores"] as const satisfies readonly (ChaveColuna & keyof UnidadeForca)[];

export const COLUNA_PADRAO: ChaveColuna = "deputado_federal";

const SEM_DADOS: Readonly<Valor> = Object.freeze({ ordem: null, fracao: null, texto: TRACO, detalhe: "Sem dados" });

export function colunasPlacar(blocos: BlocosPlacar, limiar: number, nivel: NivelPlacar): Coluna[] {
  const cadeiras = blocos.cadeiras !== null;
  return [
    ...colunasNacional(cadeiras),
    ...colunasEstados(cadeiras, nivel),
    ...colunasMunicipios(limiar),
    ...colunas2024(blocos.municipal_2024),
    ...COLUNAS_PERFIL,
  ];
}

const COLUNAS_PERFIL: readonly Coluna[] = [
  {
    chave: "legenda_federal",
    esfera: "perfil",
    titulo: "Voto de legenda (dep. federal)",
    curto: "Legenda federal",
    explicacao:
      "Parte dos votos do partido para deputado federal que foi só no número do partido, sem escolher candidato.",
  },
  {
    chave: "legenda_estadual",
    esfera: "perfil",
    titulo: "Voto de legenda (dep. estadual)",
    curto: "Legenda estadual",
    explicacao:
      "Parte dos votos do partido para deputado estadual que foi só no número do partido, sem escolher candidato.",
  },
];

function colunas2024(bloco: BlocoMunicipal2024Forca | null): Coluna[] {
  if (bloco === null) {
    return [];
  }
  const corte =
    bloco.data_corte === null
      ? ""
      : ` Situação divulgada pelo TSE em ${formatarCorte(bloco.data_corte)}; inclui cassações e suplementares.`;
  return [
    {
      chave: "prefeitos",
      esfera: "municipios",
      titulo: "Prefeituras (2024)",
      curto: "Prefeituras",
      explicacao: `Municípios com prefeito do partido, eleito em 2024 e no cargo na data de corte.${corte}`,
    },
    {
      chave: "eleitorado_governado",
      esfera: "municipios",
      titulo: "Eleitorado governado (2024)",
      curto: "Eleitorado governado",
      explicacao: `Parte do eleitorado apto de 2024 que vive nos municípios com prefeito do partido.${corte}`,
    },
    {
      chave: "vereadores",
      esfera: "municipios",
      titulo: "Vereadores (2024)",
      curto: "Vereadores",
      explicacao: `Vereadores eleitos pelo partido em 2024, no número de partido de 2026.${corte}`,
    },
  ];
}

function colunasNacional(cadeiras: boolean): Coluna[] {
  const votos: Coluna[] = [
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
  ];
  if (!cadeiras) {
    return votos;
  }
  return [
    ...votos,
    {
      chave: "camara",
      esfera: "nacional",
      titulo: "Câmara (cadeiras estimadas)",
      curto: "Câmara",
      explicacao: "Cadeiras de deputado federal que a simulação de cadeiras dá ao partido (513 no país).",
    },
    {
      chave: "senado",
      esfera: "nacional",
      titulo: "Senado (vagas estimadas)",
      curto: "Senado",
      explicacao: "Vagas de senador em disputa em 2026 que a simulação dá ao partido (54 no país; não é a bancada de 81).",
    },
  ];
}

function colunasEstados(cadeiras: boolean, nivel: NivelPlacar): Coluna[] {
  const votos: Coluna[] = [
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
  ];
  if (!cadeiras) {
    return votos;
  }
  return [
    ...votos,
    {
      chave: "governador_1t",
      esfera: "estados",
      titulo: "Governadores no 1º turno",
      curto: "Governadores",
      explicacao: "UFs em que o candidato do partido a governador se elegeu no 1º turno.",
    },
    {
      chave: "governador_2t",
      esfera: "estados",
      titulo: "No 2º turno de governador (disputa)",
      curto: "2º turno",
      explicacao:
        "UFs em que o candidato do partido está entre os dois finalistas de governador. Conta a disputa, sem vencedor projetado.",
    },
    {
      chave: "assembleia",
      esfera: "estados",
      titulo: "Assembleias (cadeiras estimadas)",
      curto: "Assembleias",
      explicacao:
        "Cadeiras de deputado estadual que a simulação dá ao partido, com as 24 da Câmara Legislativa do DF (1.059 no país).",
    },
  ];
}

function colunasMunicipios(limiar: number): Coluna[] {
  return [
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
    tipo: unidade.tipo,
    rotulo: rotuloUnidade(unidade),
    partidos: unidade.partidos,
    valores: valoresUnidade(recorte, unidade, limiar, nivel),
  }));
}

export function linhasPorUf(
  placar: PlacarForca,
  chave: string,
  limiar: number,
  modo: ModoUnidades = "partidos",
): LinhaPlacar[] {
  const tipo = tipoDaChave(placar, chave, modo);
  return placar.ufs.map((uf) => {
    const recorte = recorteDoModo(uf, modo);
    const unidade = recorte.unidades.find((item) => item.chave === chave);
    return {
      chave: uf.codigo,
      tipo,
      rotulo: uf.nome,
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

export type LinkRelatorio = { rotulo: string; href: string };

type ContextoLink = Pick<PlacarForca, "ano" | "turno" | "cargo_referencia">;

// Relatórios irmãos por partido (fase D, Task 19). Para retirar um link, apague a entrada.
// As linhas de federação não têm link: os três relatórios são por partido.
export const LINKS_RELATORIOS: readonly { rotulo: string; montar: (placar: ContextoLink, partido: number) => string }[] = [
  {
    rotulo: "Capilaridade",
    montar: (placar, partido) =>
      `/relatorios/capilaridade?${consulta({
        ano: placar.ano,
        turno: placar.turno,
        cargo: placar.cargo_referencia,
        recorte: "brasil",
        partido,
        consultar: 1,
      })}`,
  },
  {
    rotulo: "Verticalização",
    montar: (placar, partido) =>
      `/relatorios/verticalizacao?${consulta({ ano: placar.ano, turno: placar.turno, uf: "TODAS", partido, consultar: 1 })}`,
  },
  { rotulo: "Força da marca", montar: () => "/relatorios/marca" },
];

export function linksPartido(placar: ContextoLink, partido: number): LinkRelatorio[] {
  return LINKS_RELATORIOS.map((link) => ({ rotulo: link.rotulo, href: link.montar(placar, partido) }));
}

// Detalhe "Partido por UF": só linhas de partido têm link (os três relatórios são por partido).
export function linksUnidade(placar: ContextoLink, unidade: UnidadeForca | undefined): LinkRelatorio[] {
  const numero = unidade?.tipo === "partido" ? unidade.partidos[0] : undefined;
  return numero === undefined ? [] : linksPartido(placar, numero);
}

function consulta(campos: Record<string, string | number>): string {
  return new URLSearchParams(Object.entries(campos).map(([chave, valor]) => [chave, String(valor)])).toString();
}

export function temFederacoes(placar: PlacarForca): boolean {
  return placar.pais.federadas.length > 0;
}

// "federacoes" troca o recorte pela visão com federações, com a base dela (empates recalculados).
// O tipo vem da própria unidade, no Brasil ou na primeira UF em que ela aparece.
function tipoDaChave(placar: PlacarForca, chave: string, modo: ModoUnidades): TipoUnidadeForca {
  for (const recorte of [placar.pais, ...placar.ufs]) {
    const achada = recorteDoModo(recorte, modo).unidades.find((item) => item.chave === chave);
    if (achada !== undefined) {
      return achada.tipo;
    }
  }
  return "partido";
}

export function recorteDoModo(recorte: RecorteForca, modo: ModoUnidades): RecorteForca {
  if (modo === "partidos" || recorte.federadas.length === 0) {
    return recorte;
  }
  return { ...recorte, base: recorte.base_federada ?? recorte.base, unidades: recorte.federadas };
}

// Rodapé da tabela: soma só as linhas de partido, para não contar federação em dobro.
export function totaisPlacar(recorte: RecorteForca): Partial<Record<ChaveColuna, string>> {
  const partidos = recorte.unidades.filter((unidade) => unidade.tipo === "partido");
  const totais: Partial<Record<ChaveColuna, string>> = {};
  for (const chave of CHAVES_SOMAVEIS) {
    const valores = partidos.map((unidade) => unidade[chave]).filter((n) => n !== null);
    if (valores.length > 0) {
      totais[chave] = formatarInteiro(valores.reduce((soma, n) => soma + n, 0));
    }
  }
  // Média do cargo (D4 do plano 5): Σ legenda dos partidos ÷ válidos do recorte.
  const legendas = [
    ["legenda_federal", recorte.base.validos_deputado_federal],
    ["legenda_estadual", recorte.base.validos_deputado_estadual],
  ] as const;
  for (const [chave, base] of legendas) {
    const valores = partidos.map((unidade) => unidade[chave]).filter((n) => n !== null);
    if (valores.length > 0 && temBase(base)) {
      totais[chave] = formatarPercentualContagem(valores.reduce((soma, n) => soma + n, 0), base);
    }
  }
  return totais;
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
    camara: SEM_DADOS,
    senado: SEM_DADOS,
    governador_1t: SEM_DADOS,
    governador_2t: SEM_DADOS,
    assembleia: SEM_DADOS,
    prefeitos: SEM_DADOS,
    eleitorado_governado: SEM_DADOS,
    vereadores: SEM_DADOS,
    legenda_federal: SEM_DADOS,
    legenda_estadual: SEM_DADOS,
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
    ...valoresCadeiras(unidade, base.cadeiras),
    ...valores2024(unidade, base.municipal_2024),
    legenda_federal: votoDeLegenda(unidade.legenda_federal, unidade.deputado_federal),
    legenda_estadual: votoDeLegenda(unidade.legenda_estadual, unidade.deputado_estadual),
  };
}

// D17 do plano 5: legenda ÷ (nominais + legenda) do próprio partido.
function votoDeLegenda(legenda: number | null, votos: number | null): Valor {
  if (legenda === null || !temBase(votos)) {
    return SEM_DADOS;
  }
  return {
    ordem: legenda / votos,
    fracao: legenda / votos,
    texto: formatarPercentualContagem(legenda, votos),
    detalhe: `${formatarInteiro(legenda)} de ${formatarInteiro(votos)} votos só no número do partido`,
  };
}

type Valores2024 = Pick<Record<ChaveColuna, Valor>, "prefeitos" | "eleitorado_governado" | "vereadores">;

// Denominadores do recorte (totais do plano 6), nunca a soma das linhas (F8: sem totais, traço).
function valores2024(unidade: UnidadeForca, base: BaseMunicipal2024Forca | null): Valores2024 {
  return {
    prefeitos: contagem(unidade.prefeitos, base?.municipios ?? null, (n) => `de ${formatarInteiro(n)} municípios`),
    eleitorado_governado: eleitoradoGovernado(unidade.eleitorado_governado, base?.eleitorado ?? null),
    vereadores: contagem(unidade.vereadores, base?.vereadores ?? null, (n) => `de ${formatarInteiro(n)} vereadores`),
  };
}

function eleitoradoGovernado(valor: number | null, base: number | null): Valor {
  if (valor === null || !temBase(base)) {
    return SEM_DADOS;
  }
  return {
    ordem: valor / base,
    fracao: valor / base,
    texto: formatarPercentualContagem(valor, base),
    detalhe: `${formatarInteiro(valor)} ${valor === 1 ? "eleitor apto" : "eleitores aptos"} em 2024`,
  };
}

type ValoresCadeiras = Pick<Record<ChaveColuna, Valor>, "camara" | "senado" | "governador_1t" | "governador_2t" | "assembleia">;

function valoresCadeiras(unidade: UnidadeForca, base: BaseCadeirasForca | null): ValoresCadeiras {
  const de = (n: number) => `de ${formatarInteiro(n)}`;
  return {
    camara: contagem(unidade.camara, base?.camara ?? null, de),
    senado: contagem(unidade.senado, base?.senado ?? null, (n) => `de ${formatarInteiro(n)} vagas em 2026`),
    governador_1t: contagem(unidade.governador_1t, base?.governadores ?? null, (n) => `de ${formatarInteiro(n)} UFs`),
    governador_2t: disputa(unidade.governador_2t, base),
    assembleia: contagem(unidade.assembleia, base?.assembleias ?? null, de),
  };
}

// Presença entre os finalistas: só contagem, sem fração nem barra (F14).
function disputa(valor: number | null, base: BaseCadeirasForca | null): Valor {
  if (valor === null || base === null) {
    return SEM_DADOS;
  }
  return { ordem: valor, fracao: null, texto: formatarInteiro(valor), detalhe: "UFs em disputa, sem vencedor projetado" };
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
