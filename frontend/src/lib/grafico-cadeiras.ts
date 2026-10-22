import { formatarInteiro } from "./fracao.ts";
import { MEDIDAS_PADRAO, type ItemBarra, type MedidasBarras } from "./grafico-poder.ts";
import { larguraTexto } from "./largura-texto.ts";
import { rotuloPartido } from "./partidos.ts";
import type {
  CasaCadeiras,
  ContagemPartido,
  LegendaCadeiras,
  SimulacaoCadeiras,
} from "./relatorios.ts";

// "RENOVAÇÃO SOLIDÁRIA" tem 19 caracteres: 0,6 × 12 × 19 ≈ 137 px, mais 8 px de folga.
export const MEDIDAS_CADEIRAS: MedidasBarras = { ...MEDIDAS_PADRAO, esquerda: 152 };

const FASES: Record<string, string> = {
  quociente: "Quociente partidário",
  media: "Média (80% e 20%)",
  media_livre: "Média (todas as legendas)",
};

const SITUACOES: Record<string, string> = {
  eleito: "Eleito no 1º turno",
  segundo_turno: "2º turno",
  sem_votos: "Sem votos",
};

export function rotuloFase(fase: string): string {
  return FASES[fase] ?? fase;
}

export function rotuloSituacao(situacao: string): string {
  return SITUACOES[situacao] ?? situacao;
}

export function rotuloLegenda(codigo: string, legendas: readonly LegendaCadeiras[]): string {
  const legenda = legendas.find((item) => item.codigo === codigo);
  if (legenda?.federacao) {
    return legenda.sigla;
  }
  const numero = Number(codigo);
  return Number.isSafeInteger(numero) ? rotuloPartido(numero) : codigo;
}

export function rotuloCabe(rotulo: string, medidas: MedidasBarras = MEDIDAS_CADEIRAS): boolean {
  return larguraTexto(rotulo, medidas.fonte) + 8 <= medidas.esquerda;
}

export function cadeiras(n: number): string {
  return `${formatarInteiro(n)} ${n === 1 ? "cadeira" : "cadeiras"}`;
}

export function itensCasa(
  casa: CasaCadeiras,
  legendas: readonly LegendaCadeiras[],
): ItemBarra[] {
  return casa.legendas
    .filter((item) => item.cadeiras > 0)
    .map((item) => {
      const legenda = legendas.find((linha) => linha.codigo === item.legenda);
      const membros = legenda?.federacao ? detalheFederacao(legenda, casa.partidos) : "";
      const fatia = `${formatarInteiro(item.cadeiras)} de ${formatarInteiro(casa.vagas_simuladas)} vagas simuladas`;
      return {
        chave: item.legenda,
        rotulo: rotuloLegenda(item.legenda, legendas),
        valor: item.cadeiras,
        texto: formatarInteiro(item.cadeiras),
        detalhe: membros === "" ? fatia : `${fatia}\n${membros}`,
      };
    })
    .sort((a, b) => b.valor - a.valor || a.rotulo.localeCompare(b.rotulo, "pt-BR"));
}

export function itensSenado(simulacao: SimulacaoCadeiras): ItemBarra[] {
  return simulacao.senado.partidos
    .filter((item) => item.cadeiras > 0)
    .map((item) => ({
      chave: String(item.partido),
      rotulo: rotuloPartido(item.partido),
      valor: item.cadeiras,
      texto: formatarInteiro(item.cadeiras),
      detalhe: `${formatarInteiro(item.cadeiras)} de ${formatarInteiro(simulacao.senado.vagas_simuladas)} vagas simuladas`,
    }));
}

export function frasesCadeiras(simulacao: SimulacaoCadeiras): string[] {
  const frases: string[] = [];
  for (const casa of simulacao.casas) {
    const itens = itensCasa(casa, simulacao.legendas);
    const maior = itens[0];
    if (maior === undefined) {
      continue;
    }
    const empatadas = itens.filter((item) => item.valor === maior.valor).map((item) => item.rotulo);
    const quem = empatadas.length > 1 ? `empatam ${juntar(empatadas)}` : `a maior bancada é ${maior.rotulo}`;
    frases.push(
      `${casa.nome}: ${quem}, com ${cadeiras(maior.valor)} de ${formatarInteiro(casa.vagas_simuladas)}.`,
    );
    if (casa.ufs_sem_votos.length > 0) {
      frases.push(
        `${casa.nome}: faltam votos gravados de ${juntar(casa.ufs_sem_votos)}; ${formatarInteiro(casa.vagas - casa.vagas_simuladas)} vagas ficaram fora da conta.`,
      );
    }
  }
  const governo = simulacao.governo.ufs;
  const eleitos = governo.filter((uf) => uf.situacao === "eleito").length;
  const segundo = governo.filter((uf) => uf.situacao === "segundo_turno").length;
  if (governo.length > 0) {
    frases.push(
      `Governador: ${formatarInteiro(eleitos)} ${eleitos === 1 ? "UF elegeria" : "UFs elegeriam"} no 1º turno e ${formatarInteiro(segundo)} ${segundo === 1 ? "iria" : "iriam"} ao 2º turno.`,
    );
  }
  const empates = contarEmpates(simulacao);
  if (empates > 0) {
    frases.push(
      `${formatarInteiro(empates)} ${empates === 1 ? "resultado depende" : "resultados dependem"} de um desempate que os boletins não resolvem (idade do candidato).`,
    );
  }
  return frases;
}

function detalheFederacao(legenda: LegendaCadeiras, partidos: readonly ContagemPartido[]): string {
  return legenda.partidos
    .map((numero) => {
      const n = partidos.find((item) => item.partido === numero)?.cadeiras ?? 0;
      return `${rotuloPartido(numero)}: ${formatarInteiro(n)}`;
    })
    .join("\n");
}

function contarEmpates(simulacao: SimulacaoCadeiras): number {
  const proporcionais = simulacao.casas.reduce(
    (soma, casa) =>
      soma + casa.ufs.reduce((parcial, uf) => parcial + uf.eleitos.filter((e) => e.empate).length, 0),
    0,
  );
  const senado = simulacao.senado.ufs.filter((uf) => uf.empate).length;
  const governo = simulacao.governo.ufs.filter((uf) => uf.empate).length;
  return proporcionais + senado + governo;
}

function juntar(itens: readonly string[]): string {
  if (itens.length <= 1) {
    return itens.join("");
  }
  return `${itens.slice(0, -1).join(", ")} e ${itens[itens.length - 1]}`;
}
