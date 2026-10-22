import { nomeUf } from "./eleicoes.ts";
import { lerFatia } from "./fatia.ts";
import { formatarInteiro, TRACO } from "./fracao.ts";
import { rotuloPartido, siglaPartido } from "./partidos.ts";
import {
  CURTO_CARGO,
  lerDecimal,
  ROTULO_CARGO,
  type CargoVertical,
  type CargoVerticalDados,
  type Comparacao,
  type Coerencia,
  type PartidoVertical,
  type RelatorioVerticalizacao,
} from "./verticalizacao.ts";

// Faixas 0..4: <5%, 5–10%, 10–20%, 20–35%, ≥35%. A borda conta para a faixa de cima.
export const LIMITES_FATIA = [0.05, 0.1, 0.2, 0.35] as const;
// |r| < 0,2 é neutro; depois 1..4 de cada lado.
export const LIMITES_R = [0.2, 0.4, 0.6, 0.8] as const;
const MENOS = "−";
const SEM_ELEICAO = "n/a";
const VAO_REFERENCIA = 8;
const EM_POR_CARACTERE = 0.6;
const MAXIMO_FRASES = 3;
const PASSOS_EIXO = [5, 10, 20, 25] as const;
const MAXIMO_MARCAS = 5;

const MINUSCULO_CARGO: Record<CargoVertical, string> = {
  presidente: "presidente",
  governador: "governador",
  senador: "senador",
  deputadoFederal: "deputado federal",
  deputadoEstadual: "deputado estadual",
};

export function faixaFatia(fatia: number | null): number | null {
  if (fatia === null) {
    return null;
  }
  return LIMITES_FATIA.filter((limite) => fatia >= limite).length;
}

export function faixaR(r: number | null): number | null {
  if (r === null) {
    return null;
  }
  const faixa = LIMITES_R.filter((limite) => Math.abs(r) >= limite).length;
  return r < 0 && faixa > 0 ? -faixa : faixa;
}

export function corFatia(faixa: number): { fundo: string; tinta: string } {
  return { fundo: `var(--vz-seq-${faixa})`, tinta: `var(--vz-seq-tinta-${faixa})` };
}

export function corR(faixa: number): { fundo: string; tinta: string } {
  const sufixo = faixa === 0 ? "0" : faixa < 0 ? `n${-faixa}` : `p${faixa}`;
  return { fundo: `var(--vz-div-${sufixo})`, tinta: `var(--vz-div-tinta-${sufixo})` };
}

export type MedidasMatriz = {
  largura: number;
  esquerda: number;
  topo: number;
  alturaLinha: number;
  vao: number;
  fonte: number;
  fonteCabeca: number;
  rotuloCurto: boolean;
};

export const MEDIDAS_MATRIZ: MedidasMatriz = {
  largura: 640,
  esquerda: 132,
  topo: 40,
  alturaLinha: 24,
  vao: 2,
  fonte: 12,
  fonteCabeca: 12,
  rotuloCurto: false,
};

export const MEDIDAS_MATRIZ_ESTREITO: MedidasMatriz = {
  largura: 340,
  esquerda: 84,
  topo: 44,
  alturaLinha: 26,
  vao: 2,
  fonte: 12,
  fonteCabeca: 11,
  rotuloCurto: true,
};

// Sete colunas em 340 px deixam células de 33 px: "−0,15" só cabe com fonte 11.
export const MEDIDAS_COERENCIA_ESTREITO: MedidasMatriz = {
  ...MEDIDAS_MATRIZ_ESTREITO,
  fonte: 11,
  fonteCabeca: 10,
};

export type CelulaMatriz = {
  chave: string;
  linha: number;
  coluna: number;
  x: number;
  y: number;
  largura: number;
  altura: number;
  faixa: number | null;
  texto: string;
  semEleicao: boolean;
  dicaTitulo: string;
  dicaLinhas: string[];
};

export type ColunaMatriz = {
  rotulo: string;
  nome: string;
  linhas: string[];
  x: number;
  referencia: boolean;
};

export type LinhaMatriz = { rotulo: string; nome: string; y: number };

export type LayoutMatriz = {
  medidas: MedidasMatriz;
  largura: number;
  altura: number;
  canto: string;
  colunas: ColunaMatriz[];
  linhas: LinhaMatriz[];
  celulas: CelulaMatriz[];
};

type ConteudoCelula = Pick<CelulaMatriz, "faixa" | "texto" | "semEleicao" | "dicaTitulo" | "dicaLinhas"> & {
  chave: string;
};

type Grade = {
  canto: string;
  colunas: Omit<ColunaMatriz, "x">[];
  conteudo: (partido: PartidoVertical, coluna: number) => ConteudoCelula;
};

export function matrizFatias(
  dados: RelatorioVerticalizacao,
  medidas: MedidasMatriz = MEDIDAS_MATRIZ,
): LayoutMatriz | null {
  const cargos = dados.partidos[0]?.cargos.map((item) => item.cargo) ?? [];
  return montarMatriz(dados, medidas, {
    canto: "em %",
    colunas: cargos.map((cargo) => {
      const rotulo = medidas.rotuloCurto ? CURTO_CARGO[cargo] : ROTULO_CARGO[cargo];
      return { rotulo, nome: ROTULO_CARGO[cargo], linhas: [rotulo], referencia: false };
    }),
    conteudo: (partido, coluna) => celulaFatia(partido, partido.cargos[coluna]),
  });
}

export function matrizCoerencia(
  dados: RelatorioVerticalizacao,
  medidas: MedidasMatriz = MEDIDAS_MATRIZ,
): LayoutMatriz | null {
  const pares = dados.partidos[0]?.coerencia ?? [];
  const minimo = dados.limiares.minimo_municipios;
  return montarMatriz(dados, medidas, {
    canto: "r",
    colunas: pares.map((par, indice) => ({
      rotulo: `${CURTO_CARGO[par.cargo_x]}×${CURTO_CARGO[par.cargo_y]}`,
      nome: `${ROTULO_CARGO[par.cargo_x]} × ${ROTULO_CARGO[par.cargo_y]}`,
      linhas: [`${CURTO_CARGO[par.cargo_x]}×`, CURTO_CARGO[par.cargo_y]],
      referencia: indice === pares.length - 1,
    })),
    conteudo: (partido, coluna) => celulaCoerencia(partido, partido.coerencia[coluna], minimo),
  });
}

export function resumoMatriz(layout: LayoutMatriz): string {
  return layout.linhas
    .map((linha, indice) => {
      const valores = layout.celulas
        .filter((celula) => celula.linha === indice)
        .map((celula) => `${layout.colunas[celula.coluna]?.nome ?? ""} ${celula.texto}`);
      return `${linha.nome}: ${valores.join("; ")}.`;
    })
    .join(" ")
    .concat(layout.canto === "r" ? " Valores de r de Pearson." : " Valores em %.");
}

function montarMatriz(
  dados: RelatorioVerticalizacao,
  medidas: MedidasMatriz,
  grade: Grade,
): LayoutMatriz | null {
  if (dados.partidos.length === 0 || grade.colunas.length === 0) {
    return null;
  }
  const temReferencia = grade.colunas.some((coluna) => coluna.referencia);
  const extra = temReferencia ? VAO_REFERENCIA : 0;
  const passo = (medidas.largura - medidas.esquerda - extra) / grade.colunas.length;
  const larguraCelula = passo - medidas.vao;
  const alturaCelula = medidas.alturaLinha - medidas.vao;
  const inicio = (indice: number, referencia: boolean): number =>
    medidas.esquerda + indice * passo + (referencia ? VAO_REFERENCIA : 0);
  const colunas = grade.colunas.map((coluna, indice) => ({
    ...coluna,
    x: inicio(indice, coluna.referencia) + larguraCelula / 2,
  }));
  const linhas = dados.partidos.map((partido, indice) => ({
    rotulo: rotuloLinha(partido.partido, medidas),
    nome: rotuloPartido(partido.partido),
    y: medidas.topo + indice * medidas.alturaLinha + alturaCelula / 2,
  }));
  const celulas = dados.partidos.flatMap((partido, linha) =>
    grade.colunas.map((coluna, indice) => ({
      ...grade.conteudo(partido, indice),
      linha,
      coluna: indice,
      x: inicio(indice, coluna.referencia),
      y: medidas.topo + linha * medidas.alturaLinha,
      largura: larguraCelula,
      altura: alturaCelula,
    })),
  );
  return {
    medidas,
    largura: medidas.largura,
    altura: medidas.topo + dados.partidos.length * medidas.alturaLinha,
    canto: grade.canto,
    colunas,
    linhas,
    celulas,
  };
}

function rotuloLinha(numero: number, medidas: MedidasMatriz): string {
  if (!medidas.rotuloCurto) {
    return rotuloPartido(numero);
  }
  const sigla = siglaPartido(numero) ?? String(numero);
  const cabe = Math.floor((medidas.esquerda - 6) / (EM_POR_CARACTERE * medidas.fonte));
  return sigla.length <= cabe ? sigla : `${sigla.slice(0, cabe - 1)}…`;
}

function celulaFatia(partido: PartidoVertical, dados: CargoVerticalDados | undefined): ConteudoCelula {
  const cargo = dados?.cargo ?? "presidente";
  const base = {
    chave: `${partido.partido}-${cargo}`,
    dicaTitulo: `${rotuloPartido(partido.partido)} · ${ROTULO_CARGO[cargo]}`,
  };
  if (dados === undefined || dados.ufs_total === 0) {
    return {
      ...base,
      faixa: null,
      texto: SEM_ELEICAO,
      semEleicao: true,
      dicaLinhas: ["Sem eleição gravada para este cargo no recorte"],
    };
  }
  const fatia = dados.fatia_onde === null ? null : lerFatia(dados.fatia_onde);
  if (dados.fatia_onde === null || fatia === null) {
    return {
      ...base,
      faixa: null,
      texto: TRACO,
      semEleicao: false,
      dicaLinhas: [
        dados.ufs_total === 1
          ? "Não concorreu na UF"
          : `Não concorreu em nenhuma das ${formatarInteiro(dados.ufs_total)} UFs`,
      ],
    };
  }
  return {
    ...base,
    faixa: faixaFatia(fatia),
    texto: arredondarTexto(dados.fatia_onde, 1) ?? TRACO,
    semEleicao: false,
    dicaLinhas: [
      `Onde concorreu: ${dados.fatia_onde}`,
      `No recorte todo: ${dados.fatia ?? TRACO}`,
      dados.ufs_total === 1
        ? "Concorreu na UF"
        : `Concorreu em ${formatarInteiro(dados.ufs_concorreu)} de ${formatarInteiro(dados.ufs_total)} UFs`,
    ],
  };
}

function celulaCoerencia(
  partido: PartidoVertical,
  par: Coerencia | undefined,
  minimo: number,
): ConteudoCelula {
  const x = par?.cargo_x ?? "deputadoFederal";
  const y = par?.cargo_y ?? "presidente";
  const r = par === undefined || par.r === null ? null : rExibido(par.r);
  const municipios = par?.municipios ?? 0;
  const contagem = `${formatarInteiro(municipios)} ${municipios === 1 ? "município" : "municípios"}`;
  const base = {
    chave: `${partido.partido}-${x}-${y}`,
    dicaTitulo: `${rotuloPartido(partido.partido)} · ${ROTULO_CARGO[x]} × ${ROTULO_CARGO[y]}`,
    semEleicao: false,
  };
  if (par?.r === null || par === undefined || r === null) {
    const motivo =
      municipios < minimo ? `Menos de ${minimo} municípios para medir` : "Sem variação para medir";
    return { ...base, faixa: null, texto: TRACO, dicaLinhas: [motivo, contagem] };
  }
  return {
    ...base,
    faixa: faixaR(r),
    texto: formatarR(par.r),
    dicaLinhas: [`r = ${par.r}`, contagem],
  };
}

export type MedidasDispersao = {
  largura: number;
  altura: number;
  esquerda: number;
  direita: number;
  topo: number;
  base: number;
  raioMin: number;
  raioMax: number;
  fonte: number;
};

export const MEDIDAS_DISPERSAO: MedidasDispersao = {
  largura: 640,
  altura: 400,
  esquerda: 52,
  direita: 16,
  topo: 16,
  base: 44,
  raioMin: 1.5,
  raioMax: 8,
  fonte: 12,
};

export const MEDIDAS_DISPERSAO_ESTREITO: MedidasDispersao = {
  largura: 340,
  altura: 320,
  esquerda: 44,
  direita: 12,
  topo: 16,
  base: 44,
  raioMin: 1.5,
  raioMax: 6,
  fonte: 13,
};

export type PontoLayout = {
  chave: string;
  cx: number;
  cy: number;
  raio: number;
  dicaTitulo: string;
  dicaLinhas: string[];
};

export type LayoutDispersao = {
  medidas: MedidasDispersao;
  marcasX: { x: number; texto: string }[];
  marcasY: { y: number; texto: string }[];
  diagonal: { x1: number; y1: number; x2: number; y2: number } | null;
  pontos: PontoLayout[];
  rotuloX: string;
  rotuloY: string;
};

export function layoutDispersao(
  dados: RelatorioVerticalizacao,
  medidas: MedidasDispersao = MEDIDAS_DISPERSAO,
): LayoutDispersao | null {
  const { cargo_x: cargoX, cargo_y: cargoY } = dados.dispersao;
  const lidos = dados.dispersao.pontos.flatMap((ponto) => {
    const x = centesimos(ponto.x);
    const y = centesimos(ponto.y);
    return x === null || y === null ? [] : [{ ponto, x, y }];
  });
  if (lidos.length === 0) {
    return null;
  }
  const tetoX = tetoEixo(Math.max(...lidos.map((item) => item.x)));
  const tetoY = tetoEixo(Math.max(...lidos.map((item) => item.y)));
  const x0 = medidas.esquerda;
  const x1 = medidas.largura - medidas.direita;
  const y0 = medidas.altura - medidas.base;
  const y1 = medidas.topo;
  const sx = (pp: number): number => x0 + (pp / tetoX.teto) * (x1 - x0);
  const sy = (pp: number): number => y0 - (pp / tetoY.teto) * (y0 - y1);
  const maior = Math.max(...lidos.map((item) => item.ponto.comparecimento));
  const raio = (comparecimento: number): number =>
    maior <= 0
      ? medidas.raioMin
      : medidas.raioMin + (medidas.raioMax - medidas.raioMin) * Math.sqrt(comparecimento / maior);
  const pontos = lidos
    .map(({ ponto, x, y }) => ({
      chave: ponto.codigo,
      cx: sx(x / 100),
      cy: sy(y / 100),
      raio: raio(ponto.comparecimento),
      dicaTitulo: ponto.nome,
      dicaLinhas: [
        `${ROTULO_CARGO[cargoX]}: ${ponto.x}`,
        `${ROTULO_CARGO[cargoY]}: ${ponto.y}`,
        `Comparecimento: ${formatarInteiro(ponto.comparecimento)}`,
      ],
    }))
    .sort((a, b) => b.raio - a.raio || a.chave.localeCompare(b.chave));
  const encontro = Math.min(tetoX.teto, tetoY.teto);
  return {
    medidas,
    marcasX: tetoX.marcas.map((pp) => ({ x: sx(pp), texto: `${pp}%` })),
    marcasY: tetoY.marcas.map((pp) => ({ y: sy(pp), texto: `${pp}%` })),
    diagonal: encontro > 0 ? { x1: sx(0), y1: sy(0), x2: sx(encontro), y2: sy(encontro) } : null,
    pontos,
    rotuloX: `${ROTULO_CARGO[cargoX]} (% dos válidos)`,
    rotuloY: `${ROTULO_CARGO[cargoY]} (% dos válidos)`,
  };
}

// O teto é o primeiro múltiplo "redondo" (5, 10, 20 ou 25 pp) que cabe em até 5 marcas.
function tetoEixo(maximoCentesimos: number): { teto: number; marcas: number[] } {
  for (const passo of PASSOS_EIXO) {
    const intervalos = Math.max(1, Math.ceil(maximoCentesimos / (passo * 100)));
    if (intervalos + 1 <= MAXIMO_MARCAS) {
      return {
        teto: intervalos * passo,
        marcas: Array.from({ length: intervalos + 1 }, (_item, indice) => indice * passo),
      };
    }
  }
  // Fatias não passam de 100%, e 100% cabe em 4 passos de 25 pp.
  return { teto: 100, marcas: [0, 25, 50, 75, 100] };
}

type Caso = { partido: PartidoVertical; comparacao: Comparacao };
type CasoSemCandidato = Caso & { ufs: string[] };

export function frasesVerticalizacao(dados: RelatorioVerticalizacao): string[] {
  const casos: Caso[] = dados.partidos.flatMap((partido) =>
    partido.comparacoes.map((comparacao) => ({ partido, comparacao })),
  );
  const puxadores = casos
    .filter((caso) => caso.comparacao.classe === "puxador")
    .sort((a, b) => ordemRazao(b, a, Number.POSITIVE_INFINITY));
  const bases = casos
    .filter((caso) => caso.comparacao.classe === "base")
    .sort((a, b) => ordemRazao(a, b, Number.POSITIVE_INFINITY));
  const ausentes = semCandidatoRelevante(casos, dados.limiares.base_relevante);
  const frases = [
    fraseCoerencia(dados),
    ...puxadores.slice(0, MAXIMO_FRASES).map(frasePuxador),
    ...bases.slice(0, MAXIMO_FRASES).map(fraseBase),
    ...ausentes.slice(0, MAXIMO_FRASES).map((caso) => fraseSemCandidato(caso, dados.limiares.base_relevante)),
  ];
  const sobra = [puxadores, bases, ausentes].reduce(
    (soma, lista) => soma + Math.max(0, lista.length - MAXIMO_FRASES),
    0,
  );
  if (sobra > 0) {
    frases.push(`Mais ${sobra} ${sobra === 1 ? "caso" : "casos"} na tabela.`);
  }
  return frases;
}

// Razão nula (sem base na proporcional) vale como a maior possível.
function ordemRazao(a: Caso, b: Caso, nula: number): number {
  const ra = lerDecimal(a.comparacao.razao) ?? nula;
  const rb = lerDecimal(b.comparacao.razao) ?? nula;
  return ra === rb ? 0 : ra < rb ? -1 : 1;
}

function fraseCoerencia(dados: RelatorioVerticalizacao): string {
  const { partido, cargo_x: x, cargo_y: y, coerencia } = dados.dispersao;
  const rotulo = rotuloPartido(partido);
  const r = coerencia.r === null ? null : rExibido(coerencia.r);
  const entre = `${MINUSCULO_CARGO[x]} e ${MINUSCULO_CARGO[y]}`;
  if (coerencia.r === null || r === null) {
    return coerencia.municipios < dados.limiares.minimo_municipios
      ? `Não há municípios suficientes para medir a coerência do ${rotulo} entre ${entre}.`
      : `Não há variação suficiente para medir a coerência do ${rotulo} entre ${entre}.`;
  }
  const absoluto = Math.abs(r);
  const forca = absoluto >= 0.6 ? "forte" : absoluto >= 0.3 ? "moderada" : "fraca";
  const sentido = r < 0 ? " e inversa" : "";
  const onde = dados.uf === null ? "Dentro de cada UF" : `Em ${nomeUf(dados.uf)}`;
  return (
    `${onde}, onde o ${rotulo} vai melhor para ${MINUSCULO_CARGO[x]} ele também vai melhor ` +
    `para ${MINUSCULO_CARGO[y]}? A coerência é ${forca}${sentido} ` +
    `(r = ${formatarR(coerencia.r)}, ${formatarInteiro(coerencia.municipios)} municípios).`
  );
}

function frasePuxador({ partido, comparacao }: Caso): string {
  const rotulo = rotuloPartido(partido.partido);
  const cargo = MINUSCULO_CARGO[comparacao.majoritario];
  const prop = MINUSCULO_CARGO[comparacao.proporcional];
  const maj = comparacao.majoritaria ?? TRACO;
  const razao = comparacao.razao === null ? null : arredondarTexto(comparacao.razao, 1);
  if (razao === null) {
    return `${rotulo} puxa em ${cargo}: teve ${maj} onde concorreu sem base em ${prop}.`;
  }
  return (
    `${rotulo} puxa em ${cargo}: teve ${maj} onde concorreu, ${razao} vezes o esperado ` +
    `pela força em ${prop} (${comparacao.esperada ?? TRACO}).`
  );
}

function fraseBase({ partido, comparacao }: Caso): string {
  return (
    `${rotuloPartido(partido.partido)} tem base sem cabeça de chapa forte em ` +
    `${MINUSCULO_CARGO[comparacao.majoritario]}: a força em ` +
    `${MINUSCULO_CARGO[comparacao.proporcional]} indicaria ${comparacao.esperada ?? TRACO}, ` +
    `e veio ${comparacao.majoritaria ?? TRACO}.`
  );
}

function semCandidatoRelevante(casos: readonly Caso[], baseRelevante: string): CasoSemCandidato[] {
  const piso = centesimos(baseRelevante) ?? 0;
  return casos
    .map((caso) => ({
      ...caso,
      ufs: caso.comparacao.sem_candidato
        .filter((item) => (centesimos(item.proporcional) ?? -1) >= piso)
        .map((item) => item.uf),
    }))
    .filter((caso) => caso.ufs.length > 0)
    .sort((a, b) => b.ufs.length - a.ufs.length);
}

function fraseSemCandidato(caso: CasoSemCandidato, baseRelevante: string): string {
  const n = caso.ufs.length;
  return (
    `${rotuloPartido(caso.partido.partido)} não lançou ${MINUSCULO_CARGO[caso.comparacao.majoritario]} ` +
    `em ${n} ${n === 1 ? "UF" : "UFs"} onde tem ${baseRelevante} ou mais em ` +
    `${MINUSCULO_CARGO[caso.comparacao.proporcional]} (${caso.ufs.join(", ")}). ` +
    "Pode ter apoiado um aliado; isso não conta como fraqueza."
  );
}

// "42,19%" → 4219 (centésimos de ponto percentual); texto fora do formato → null.
function centesimos(texto: string): number | null {
  const lido = lerNumeroTexto(texto);
  if (lido === null || lido.negativo) {
    return null;
  }
  return arredondarEscala(lido, 2);
}

// A força, o sentido e a faixa saem do r como o leitor o vê (2 casas): 0,2996 é "0,30".
function rExibido(texto: string): number | null {
  return lerDecimal(formatarR(texto).replace(MENOS, "-"));
}

// r com 2 casas e o sinal de menos U+2212: "-0,1500" → "−0,15"; "-0,0012" → "0,00".
export function formatarR(texto: string): string {
  return arredondarTexto(texto, 2) ?? TRACO;
}

// Razão com 1 casa: "2,6974" → "2,7"; null → "—".
export function formatarRazao(texto: string | null): string {
  return texto === null ? TRACO : (arredondarTexto(texto, 1) ?? TRACO);
}

type NumeroTexto = { negativo: boolean; digitos: number; casas: number };

function lerNumeroTexto(texto: string): NumeroTexto | null {
  const encontrado = /^(-?)([\d.]+)(?:,(\d+))?%?$/.exec(texto.trim());
  if (encontrado === null) {
    return null;
  }
  const inteiro = (encontrado[2] ?? "").replace(/\./g, "");
  const fracao = encontrado[3] ?? "";
  if (inteiro === "") {
    return null;
  }
  return {
    negativo: encontrado[1] === "-",
    digitos: Number(`${inteiro}${fracao}`),
    casas: fracao.length,
  };
}

// Arredonda meio para cima no valor absoluto, só com inteiros.
function arredondarEscala(lido: NumeroTexto, casas: number): number {
  if (lido.casas <= casas) {
    return lido.digitos * 10 ** (casas - lido.casas);
  }
  const divisor = 10 ** (lido.casas - casas);
  return Math.floor((lido.digitos + divisor / 2) / divisor);
}

function arredondarTexto(texto: string, casas: number): string | null {
  const lido = lerNumeroTexto(texto);
  if (lido === null) {
    return null;
  }
  const escalado = arredondarEscala(lido, casas);
  const escala = 10 ** casas;
  const inteiro = Math.floor(escalado / escala);
  const fracao = String(escalado % escala).padStart(casas, "0");
  const sinal = lido.negativo && escalado > 0 ? MENOS : "";
  return `${sinal}${formatarInteiro(inteiro)},${fracao}`;
}
