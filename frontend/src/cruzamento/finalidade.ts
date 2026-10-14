import { formatarPercentualContagem } from "../lib/fracao.ts";
import type { Composicao, FatiaClasse } from "../lib/relatorios.ts";

export const ORDEM_CLASSE = [
  "consolidacao",
  "terreno_de_virada",
  "em_aberto",
  "sem_governador",
] as const;

export type ClasseCruzada = (typeof ORDEM_CLASSE)[number];

export const DEFINICOES: Record<ClasseCruzada, string> = {
  consolidacao:
    "O governador é do mesmo partido que lidera a presidência nesse lugar.",
  terreno_de_virada:
    "O governador é do partido que ficou em segundo na presidência nesse lugar.",
  em_aberto:
    "O governador é de um partido que não lidera nem fica em segundo na presidência nesse lugar.",
  sem_governador:
    "Há líder na presidência e não há líder de governador nesse lugar.",
};

export const INTENSIDADE: Record<ClasseCruzada, number> = {
  consolidacao: 1,
  terreno_de_virada: 0.72,
  em_aberto: 0.48,
  sem_governador: 0.28,
};

export const FRASE_FINALIDADE =
  "Este relatório mostra se o governador de cada lugar segue o líder da presidência, o segundo colocado, um terceiro partido, ou se não há governador.";

export const FRASE_RECORTE =
  "A UF escolhe somente a lista de municípios. A composição, os estados, as regiões e o país reúnem todos os lugares apurados.";

export const FRASE_MARGEM =
  "A margem é o líder menos o segundo, sobre os votos válidos de presidente. Brancos e nulos ficam de fora do percentual, da margem e da classe.";

const FECHO: Record<ClasseCruzada, string> = {
  consolidacao: "municípios em consolidação",
  terreno_de_virada: "municípios em terreno de virada",
  em_aberto: "municípios em aberto",
  sem_governador: "municípios sem governador",
};

export function estiloDaBarra(classe: string, votos: number): {
  flexGrow: number;
  backgroundColor: string;
  opacity?: number;
  minWidth?: number;
} {
  if (votos <= 0) {
    return { flexGrow: votos, backgroundColor: "transparent", minWidth: 0 };
  }
  const intensidade = eClasse(classe) ? INTENSIDADE[classe] : 1;
  return {
    flexGrow: votos,
    backgroundColor: "rgb(13, 111, 110)",
    opacity: intensidade,
  };
}

export function definicaoDaClasse(classe: string): string {
  if (eClasse(classe)) {
    return DEFINICOES[classe];
  }
  return classe;
}

export function fraseDoAchado(composicao: Composicao): string | null {
  if (composicao.votos_validos <= 0) {
    return null;
  }
  const vencedora = maiorFatia(composicao.classes);
  if (vencedora === null || !eClasse(vencedora.classe)) {
    return null;
  }
  const percentual = formatarPercentualContagem(
    vencedora.votos_validos,
    composicao.votos_validos,
  );
  const definicao = definicaoDaClasse(vencedora.classe);
  const continuacao = definicao.charAt(0).toLowerCase() + definicao.slice(1);
  return `A maior parte dos votos válidos de presidente, ${percentual}, está em ${FECHO[vencedora.classe]}: ${continuacao}`;
}

function maiorFatia(classes: readonly FatiaClasse[]): FatiaClasse | null {
  let escolhida: FatiaClasse | null = null;
  let posicao: number = ORDEM_CLASSE.length;
  for (const fatia of classes) {
    if (!eClasse(fatia.classe) || fatia.votos_validos <= 0) {
      continue;
    }
    const indice = ORDEM_CLASSE.indexOf(fatia.classe);
    if (
      escolhida === null ||
      fatia.votos_validos > escolhida.votos_validos ||
      (fatia.votos_validos === escolhida.votos_validos && indice < posicao)
    ) {
      escolhida = fatia;
      posicao = indice;
    }
  }
  return escolhida;
}

function eClasse(classe: string): classe is ClasseCruzada {
  return (ORDEM_CLASSE as readonly string[]).includes(classe);
}
