import { TRACO, formatarInteiro, formatarPercentualContagem } from "./fracao.ts";
import {
  MEDIDAS_PADRAO,
  layoutBarras,
  resumoBarras,
  type Barra,
  type ItemBarra,
  type LayoutBarras,
  type MedidasBarras,
} from "./grafico-poder.ts";
import { larguraTexto } from "./largura-texto.ts";
import { rotuloPartido } from "./partidos.ts";
import type { GradeRelatorio, LinhaGrade } from "./relatorios.ts";

export const MINIMO_VOTOS_RANKING = 100_000,
  MINIMO_VOTOS_UF = 5_000,
  FATOR_LIMIAR = 2;

export type CargoMarca = "deputadoFederal" | "deputadoEstadual";

export const CARGOS_MARCA: readonly CargoMarca[] = ["deputadoFederal", "deputadoEstadual"];

export const ROTULOS_CARGO_MARCA: Record<CargoMarca, string> = {
  deputadoFederal: "deputado federal",
  deputadoEstadual: "deputado estadual",
};

export type ClasseMarca = "forte" | "media" | "pessoa";

export const ROTULOS_CLASSE_MARCA: Record<ClasseMarca, string> = {
  forte: "Marca forte",
  media: "Perto da média",
  pessoa: "Voto na pessoa",
};

export type EstadoCelula = "ok" | "poucos" | "sem-candidato" | "sem-votos";

export type PartidoMarca = {
  partido: number;
  rotulo: string;
  nominais: number;
  legenda: number;
  votos: number;
  texto: string;
  vezes: string;
  // Float, geometry only: never used to decide a class, an order or a sentence.
  indice: number;
  classe: ClasseMarca;
};

export type CelulaMarca = {
  partido: number;
  nominais: number;
  legenda: number;
  votos: number;
  texto: string;
  estado: EstadoCelula;
};

export type UfMarca = {
  uf: string;
  nome: string;
  legenda: number;
  votos: number;
  texto: string;
  celulas: CelulaMarca[];
};

export type MarcaCargo = {
  cargo: CargoMarca;
  rotulo: string;
  legenda: number;
  votos: number;
  texto: string;
  ranking: PartidoMarca[];
  fora: PartidoMarca[];
  ufs: UfMarca[];
};

type Contagem = { nominais: number; legenda: number };

const ZERO = BigInt(0);
const UM = BigInt(1);
const DOIS = BigInt(2);
const CEM = BigInt(100);
const FATOR = BigInt(FATOR_LIMIAR);

export function estadoCelula(nominais: number, legenda: number): EstadoCelula {
  const votos = nominais + legenda;
  if (votos === 0) {
    return "sem-votos";
  }
  if (nominais === 0) {
    return "sem-candidato";
  }
  if (votos < MINIMO_VOTOS_UF) {
    return "poucos";
  }
  return "ok";
}

export function classeMarca(
  legenda: number,
  votos: number,
  legendaCargo: number,
  votosCargo: number,
): ClasseMarca {
  if (legendaCargo === 0 || votos === 0) {
    return "media";
  }
  const parte = BigInt(legenda) * BigInt(votosCargo);
  const media = BigInt(legendaCargo) * BigInt(votos);
  if (parte >= FATOR * media) {
    return "forte";
  }
  if (FATOR * parte <= media) {
    return "pessoa";
  }
  return "media";
}

export function formatarVezes(
  legenda: number,
  votos: number,
  legendaCargo: number,
  votosCargo: number,
): string {
  if (legendaCargo === 0 || votos === 0) {
    return TRACO;
  }
  const num = BigInt(legenda) * BigInt(votosCargo) * CEM;
  const den = BigInt(votos) * BigInt(legendaCargo);
  const quociente = num / den;
  const q = (num % den) * DOIS >= den ? quociente + UM : quociente;
  return `${q / CEM},${String(q % CEM).padStart(2, "0")}×`;
}

export function marcaDoCargo(cargo: CargoMarca, grade: GradeRelatorio): MarcaCargo | null {
  const somas = somarPorPartido(grade.linhas);
  let legendaCargo = 0;
  let votosCargo = 0;
  for (const contagem of somas.values()) {
    legendaCargo += contagem.legenda;
    votosCargo += contagem.nominais + contagem.legenda;
  }
  if (votosCargo === 0) {
    return null;
  }
  const partidos = [...somas.entries()]
    .map(([partido, contagem]) => partidoMarca(partido, contagem, legendaCargo, votosCargo))
    .filter((item) => item.votos > 0)
    .sort(compararMarca);
  const ranking = partidos.filter((item) => item.votos >= MINIMO_VOTOS_RANKING);
  const fora = partidos.filter((item) => item.votos < MINIMO_VOTOS_RANKING);
  return {
    cargo,
    rotulo: ROTULOS_CARGO_MARCA[cargo],
    legenda: legendaCargo,
    votos: votosCargo,
    texto: formatarPercentualContagem(legendaCargo, votosCargo),
    ranking,
    fora,
    ufs: grade.linhas.map((linha) => ufMarca(linha, ranking)),
  };
}

function somarPorPartido(linhas: readonly LinhaGrade[]): Map<number, Contagem> {
  const somas = new Map<number, Contagem>();
  for (const linha of linhas) {
    for (const celula of linha.celulas) {
      const atual = somas.get(celula.partido) ?? { nominais: 0, legenda: 0 };
      somas.set(celula.partido, {
        nominais: atual.nominais + celula.votos_nominais,
        legenda: atual.legenda + celula.votos_legenda,
      });
    }
  }
  return somas;
}

function partidoMarca(
  partido: number,
  contagem: Contagem,
  legendaCargo: number,
  votosCargo: number,
): PartidoMarca {
  const { nominais, legenda } = contagem;
  const votos = nominais + legenda;
  return {
    partido,
    rotulo: rotuloPartido(partido),
    nominais,
    legenda,
    votos,
    texto: formatarPercentualContagem(legenda, votos),
    vezes: formatarVezes(legenda, votos, legendaCargo, votosCargo),
    indice:
      legendaCargo === 0 || votos === 0 ? 0 : legenda / votos / (legendaCargo / votosCargo),
    classe: classeMarca(legenda, votos, legendaCargo, votosCargo),
  };
}

function compararMarca(a: PartidoMarca, b: PartidoMarca): number {
  const cruz = BigInt(b.legenda) * BigInt(a.votos) - BigInt(a.legenda) * BigInt(b.votos);
  if (cruz !== ZERO) {
    return cruz > ZERO ? 1 : -1;
  }
  return b.votos - a.votos || a.partido - b.partido;
}

function ufMarca(linha: LinhaGrade, ranking: readonly PartidoMarca[]): UfMarca {
  const porPartido = new Map(linha.celulas.map((celula) => [celula.partido, celula]));
  let legenda = 0;
  let votos = 0;
  for (const celula of linha.celulas) {
    legenda += celula.votos_legenda;
    votos += celula.votos_nominais + celula.votos_legenda;
  }
  return {
    uf: linha.codigo,
    nome: linha.nome,
    legenda,
    votos,
    texto: votos === 0 ? TRACO : formatarPercentualContagem(legenda, votos),
    celulas: ranking.map((item) => {
      const celula = porPartido.get(item.partido);
      const nominais = celula?.votos_nominais ?? 0;
      const legendaCelula = celula?.votos_legenda ?? 0;
      const votosCelula = nominais + legendaCelula;
      const estado = estadoCelula(nominais, legendaCelula);
      return {
        partido: item.partido,
        nominais,
        legenda: legendaCelula,
        votos: votosCelula,
        texto: estado === "ok" ? formatarPercentualContagem(legendaCelula, votosCelula) : TRACO,
        estado,
      };
    }),
  };
}

export type LegendaPartido = { legenda: number; votos: number; texto: string };

// Official definition of the national party-vote share (shared with the strength scoreboard):
// legenda / (nominais + legenda), summed over the UF rows of the grade.
export function fatiaLegendaNacional(grade: GradeRelatorio): Map<number, LegendaPartido> {
  const somas = somarPorPartido(grade.linhas);
  const fatias = new Map<number, LegendaPartido>();
  for (const partido of [...somas.keys()].sort((a, b) => a - b)) {
    const contagem = somas.get(partido) ?? { nominais: 0, legenda: 0 };
    const votos = contagem.nominais + contagem.legenda;
    if (votos > 0) {
      fatias.set(partido, {
        legenda: contagem.legenda,
        votos,
        texto: formatarPercentualContagem(contagem.legenda, votos),
      });
    }
  }
  return fatias;
}

export type ParCargos = {
  partido: number;
  rotulo: string;
  federal: PartidoMarca;
  estadual: PartidoMarca;
};

export type ComparacaoCargos = { pares: ParCargos[]; maisMuda: ParCargos | null };

export function comparacaoCargos(federal: MarcaCargo, estadual: MarcaCargo): ComparacaoCargos {
  const estaduais = new Map(estadual.ranking.map((item) => [item.partido, item]));
  const pares: ParCargos[] = [];
  for (const item of federal.ranking) {
    const par = estaduais.get(item.partido);
    if (par !== undefined) {
      pares.push({ partido: item.partido, rotulo: item.rotulo, federal: item, estadual: par });
    }
  }
  if (federal.legenda === 0 || estadual.legenda === 0) {
    return { pares, maisMuda: null };
  }
  let melhor: { par: ParCargos; n: bigint; d: bigint } | null = null;
  for (const par of pares) {
    const { n, d } = mudanca(par, federal, estadual);
    if (
      melhor === null ||
      n * melhor.d > melhor.n * d ||
      (n * melhor.d === melhor.n * d && par.partido < melhor.par.partido)
    ) {
      melhor = { par, n, d };
    }
  }
  return { pares, maisMuda: melhor === null || melhor.n === ZERO ? null : melhor.par };
}

// |state multiple − federal multiple| as an exact fraction n/d, with n ≥ 0 and d > 0.
function mudanca(
  par: ParCargos,
  federal: MarcaCargo,
  estadual: MarcaCargo,
): { n: bigint; d: bigint } {
  const lf = BigInt(par.federal.legenda);
  const tf = BigInt(par.federal.votos);
  const le = BigInt(par.estadual.legenda);
  const te = BigInt(par.estadual.votos);
  const legendaFederal = BigInt(federal.legenda);
  const votosFederal = BigInt(federal.votos);
  const legendaEstadual = BigInt(estadual.legenda);
  const votosEstadual = BigInt(estadual.votos);
  const n = le * votosEstadual * tf * legendaFederal - lf * votosFederal * te * legendaEstadual;
  return { n: n < ZERO ? -n : n, d: te * legendaEstadual * tf * legendaFederal };
}

export function leituraMarca(federal: MarcaCargo | null, estadual: MarcaCargo | null): string[] {
  const frases: string[] = [];
  const marcas = [federal, estadual].filter((marca): marca is MarcaCargo => marca !== null);
  if (federal !== null && estadual !== null) {
    frases.push(
      `No Brasil, ${federal.texto} dos votos para deputado federal foram só no número do partido. ` +
        `Para deputado estadual, foram ${estadual.texto} (sem o DF, que elege deputados distritais).`,
    );
  } else if (federal !== null) {
    frases.push(
      `No Brasil, ${federal.texto} dos votos para deputado federal foram só no número do partido.`,
    );
  } else if (estadual !== null) {
    frases.push(
      `No Brasil, ${estadual.texto} dos votos para deputado estadual foram só no número do partido ` +
        "(sem o DF, que elege deputados distritais).",
    );
  }
  for (const marca of marcas) {
    frases.push(fraseForte(marca), frasePessoa(marca));
  }
  if (federal !== null && estadual !== null) {
    const { maisMuda } = comparacaoCargos(federal, estadual);
    if (maisMuda !== null) {
      const { federal: f, estadual: e } = maisMuda;
      frases.push(
        `${maisMuda.rotulo} é o partido cuja marca mais muda entre os cargos: ` +
          `para deputado federal, tem ${f.texto} de voto de legenda (${f.vezes} a média do cargo); ` +
          `para deputado estadual, ${e.texto} (${e.vezes} a média do cargo).`,
      );
    }
  }
  for (const marca of marcas) {
    const frase = fraseUf(marca);
    if (frase !== null) {
      frases.push(frase);
    }
  }
  for (const marca of marcas) {
    if (marca.fora.length > 0) {
      const itens = marca.fora.map(
        (item) => `${item.rotulo} (${item.texto} de legenda em ${votosTexto(item.votos)})`,
      );
      frases.push(
        `Fora do ranking de ${marca.rotulo}, por terem menos de ${formatarInteiro(MINIMO_VOTOS_RANKING)} votos: ${juntar(itens)}.`,
      );
    }
  }
  return frases;
}

export function itensRanking(marca: MarcaCargo): ItemBarra[] {
  return marca.ranking.map((item) => ({
    chave: String(item.partido),
    rotulo: item.rotulo,
    valor: item.votos === 0 ? 0 : item.legenda / item.votos,
    texto: item.texto,
    detalhe:
      `${formatarInteiro(item.legenda)} de ${formatarInteiro(item.votos)} votos foram de legenda\n` +
      `${ROTULOS_CLASSE_MARCA[item.classe]} (${item.vezes} a média do cargo)`,
  }));
}

export type BarraMarca = Barra & { classe: ClasseMarca };

export type LayoutRanking = Omit<LayoutBarras, "barras"> & {
  barras: BarraMarca[];
  xReferencia: number;
};

export function layoutRanking(
  marca: MarcaCargo,
  medidas: MedidasBarras = MEDIDAS_PADRAO,
): LayoutRanking | null {
  const itens = itensRanking(marca);
  // Rows come from layoutBarras; a unit value keeps it from bailing out when every share is 0.
  const base = layoutBarras(
    itens.map((item) => ({ ...item, valor: 1 })),
    medidas,
  );
  const media = marca.votos === 0 ? 0 : marca.legenda / marca.votos;
  const escala = Math.max(media, ...itens.map((item) => item.valor));
  if (base === null || escala <= 0) {
    return null;
  }
  const util = medidas.largura - medidas.esquerda - medidas.direita;
  return {
    ...base,
    barras: base.barras.map((barra, indice) => {
      const item = itens[indice] ?? barra;
      return {
        ...barra,
        valor: item.valor,
        largura: (Math.max(0, item.valor) / escala) * util,
        classe: marca.ranking[indice]?.classe ?? "media",
      };
    }),
    xReferencia: medidas.esquerda + (media / escala) * util,
  };
}

export function resumoRanking(marca: MarcaCargo): string {
  return resumoBarras(
    `Voto de legenda por partido, ${marca.rotulo}, média do cargo ${marca.texto}.`,
    itensRanking(marca),
  );
}

export type MedidasHalteres = {
  largura: number;
  esquerda: number;
  direita: number;
  topo: number;
  base: number;
  alturaLinha: number;
  raio: number;
  descida: number;
  rotuloAcima: boolean;
  fonte: number;
};

export const MEDIDAS_HALTERES_PADRAO: MedidasHalteres = {
  largura: 640,
  esquerda: 120,
  direita: 24,
  topo: 24,
  base: 4,
  alturaLinha: 28,
  raio: 5,
  descida: 0,
  rotuloAcima: false,
  fonte: 12,
};

export const MEDIDAS_HALTERES_ESTREITO: MedidasHalteres = {
  largura: 340,
  esquerda: 8,
  direita: 16,
  topo: 24,
  base: 4,
  alturaLinha: 42,
  raio: 5,
  descida: 8,
  rotuloAcima: true,
  fonte: 13,
};

export type Haltere = {
  chave: string;
  rotulo: string;
  y: number;
  xFederal: number;
  xEstadual: number;
  dica: string;
};

export type ReferenciaHalteres = { valor: number; x: number; rotulo: string };

export type LayoutHalteres = {
  medidas: MedidasHalteres;
  largura: number;
  altura: number;
  escala: number;
  halteres: Haltere[];
  referencias: ReferenciaHalteres[];
};

const REFERENCIAS_HALTERES = [
  { valor: 0.5, rotulo: "0,5×" },
  { valor: 1, rotulo: "1×" },
  { valor: FATOR_LIMIAR, rotulo: `${FATOR_LIMIAR}×` },
] as const;

export function layoutHalteres(
  pares: readonly ParCargos[],
  medidas: MedidasHalteres = MEDIDAS_HALTERES_PADRAO,
): LayoutHalteres | null {
  if (pares.length === 0) {
    return null;
  }
  const { largura, esquerda, direita, topo, alturaLinha, descida, fonte } = medidas;
  const escala = Math.max(
    FATOR_LIMIAR,
    ...pares.flatMap((par) => [par.federal.indice, par.estadual.indice]),
  );
  const util = largura - esquerda - direita;
  const x = (valor: number) => esquerda + (Math.max(0, valor) / escala) * util;
  const referencias: ReferenciaHalteres[] = [];
  let ultimoVisivel: number | null = null;
  for (const referencia of REFERENCIAS_HALTERES) {
    const posicao = x(referencia.valor);
    const cabe =
      ultimoVisivel === null ||
      posicao - ultimoVisivel >= larguraTexto(referencia.rotulo, fonte) + 4;
    if (cabe) {
      ultimoVisivel = posicao;
    }
    referencias.push({ valor: referencia.valor, x: posicao, rotulo: cabe ? referencia.rotulo : "" });
  }
  return {
    medidas,
    largura,
    altura: topo + pares.length * alturaLinha + medidas.base,
    escala,
    halteres: pares.map((par, indice) => ({
      chave: String(par.partido),
      rotulo: par.rotulo,
      y: topo + indice * alturaLinha + alturaLinha / 2 + descida,
      xFederal: x(par.federal.indice),
      xEstadual: x(par.estadual.indice),
      dica:
        `Deputado federal: ${par.federal.texto} (${par.federal.vezes} a média)\n` +
        `Deputado estadual: ${par.estadual.texto} (${par.estadual.vezes} a média)`,
    })),
    referencias,
  };
}

export function resumoHalteres(pares: readonly ParCargos[]): string {
  const introducao = "Voto de legenda como múltiplo da média de cada cargo.";
  const partes = pares
    .map((par) => `${par.rotulo}: federal ${par.federal.vezes}, estadual ${par.estadual.vezes}`)
    .join("; ");
  return partes === "" ? introducao : `${introducao} ${partes}.`;
}

function fraseForte(marca: MarcaCargo): string {
  const { rotulo: cargo, texto: media } = marca;
  const fortes = marca.ranking.filter((item) => item.classe === "forte");
  const [unico] = fortes;
  if (unico === undefined) {
    return `Para ${cargo}, nenhum partido do ranking chega ao dobro da média do cargo (${media}).`;
  }
  if (fortes.length === 1) {
    return `Marca forte para ${cargo}: ${unico.rotulo}, com ${unico.texto} de voto de legenda, pelo menos o dobro da média do cargo (${media}).`;
  }
  return `Marca forte para ${cargo}: ${juntar(fortes.map(comParte))}, cada um com pelo menos o dobro da média do cargo (${media}).`;
}

function frasePessoa(marca: MarcaCargo): string {
  const { rotulo: cargo, texto: media } = marca;
  const pessoas = marca.ranking.filter((item) => item.classe === "pessoa");
  const [unico] = pessoas;
  if (unico === undefined) {
    return `Para ${cargo}, nenhum partido do ranking fica abaixo da metade da média do cargo (${media}).`;
  }
  if (pessoas.length === 1) {
    return `Voto na pessoa para ${cargo}: ${unico.rotulo}, com ${unico.texto} de voto de legenda, no máximo a metade da média do cargo (${media}).`;
  }
  return `Voto na pessoa para ${cargo}: ${juntar(pessoas.map(comParte))}, cada um com no máximo a metade da média do cargo (${media}).`;
}

function fraseUf(marca: MarcaCargo): string | null {
  const ufs = marca.ufs.filter((uf) => uf.votos > 0);
  const [primeira] = ufs;
  if (primeira === undefined) {
    return null;
  }
  if (ufs.length === 1) {
    return `Para ${marca.rotulo}, a única UF é ${primeira.nome}, com ${primeira.texto} de voto de legenda.`;
  }
  let maior = primeira;
  let menor = primeira;
  for (const uf of ufs.slice(1)) {
    const contraMaior = compararParte(uf, maior);
    if (contraMaior > 0 || (contraMaior === 0 && uf.nome.localeCompare(maior.nome, "pt-BR") < 0)) {
      maior = uf;
    }
    const contraMenor = compararParte(uf, menor);
    if (contraMenor < 0 || (contraMenor === 0 && uf.nome.localeCompare(menor.nome, "pt-BR") < 0)) {
      menor = uf;
    }
  }
  return `Para ${marca.rotulo}, a UF com mais voto de legenda é ${maior.nome} (${maior.texto}) e a com menos é ${menor.nome} (${menor.texto}).`;
}

// Sign of a.legenda/a.votos − b.legenda/b.votos, computed exactly.
function compararParte(
  a: { legenda: number; votos: number },
  b: { legenda: number; votos: number },
): number {
  const cruz = BigInt(a.legenda) * BigInt(b.votos) - BigInt(b.legenda) * BigInt(a.votos);
  return cruz > ZERO ? 1 : cruz < ZERO ? -1 : 0;
}

function comParte(item: PartidoMarca): string {
  return `${item.rotulo} (${item.texto})`;
}

function votosTexto(votos: number): string {
  return `${formatarInteiro(votos)} ${votos === 1 ? "voto" : "votos"}`;
}

function juntar(nomes: readonly string[]): string {
  if (nomes.length <= 1) {
    return nomes[0] ?? "";
  }
  const ultimo = nomes[nomes.length - 1] ?? "";
  return `${nomes.slice(0, -1).join(", ")} e ${ultimo}`;
}
