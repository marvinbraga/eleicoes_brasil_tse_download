import { lerFatia } from "@/lib/fatia";
import { compararNumero, type Direcao } from "@/lib/ordem";
import type { GrupoPerfil } from "@/lib/relatorios";

export type ColunaGrupo = {
  id: string;
  rotulo: string;
  titulo?: string;
  numerica: boolean;
};

export function colunasDeGrupo(partidos: readonly number[], comCedula: boolean): ColunaGrupo[] {
  const colunas: ColunaGrupo[] = [
    { id: "grupo", rotulo: "Grupo", numerica: false },
    { id: "municipios", rotulo: "Municípios", numerica: true },
    { id: "comparecimento", rotulo: "Comparecimento", numerica: true },
  ];
  partidos.forEach((partido, indice) => {
    colunas.push({
      id: `centro:${indice}`,
      rotulo: String(partido),
      titulo: `Partido ${partido}`,
      numerica: true,
    });
  });
  if (comCedula) {
    colunas.push(
      { id: `centro:${partidos.length}`, rotulo: "Branco", numerica: true },
      { id: `centro:${partidos.length + 1}`, rotulo: "Nulo", numerica: true },
    );
  }
  return colunas;
}

export function maiorFatia(grupos: readonly GrupoPerfil[], quantidade: number): number {
  let maximo = 0;
  for (const grupo of grupos) {
    for (let indice = 0; indice < quantidade; indice += 1) {
      const fatia = lerFatia(grupo.centro[indice] ?? "");
      if (fatia !== null && fatia > maximo) {
        maximo = fatia;
      }
    }
  }
  return maximo;
}

export function relativoDe(texto: string | undefined, maximo: number): number {
  if (texto === undefined || maximo <= 0) {
    return 0;
  }
  const fatia = lerFatia(texto);
  if (fatia === null || fatia <= 0) {
    return 0;
  }
  return fatia / maximo;
}

export function ordenarGrupos(
  grupos: readonly GrupoPerfil[],
  coluna: string | null,
  direcao: Direcao,
): GrupoPerfil[] {
  if (coluna === null) {
    return [...grupos];
  }
  return grupos
    .map((grupo, indice) => ({ grupo, indice }))
    .sort((esquerda, direita) => {
      const comparado = compararNumero(valor(esquerda.grupo, coluna), valor(direita.grupo, coluna), direcao);
      return comparado === 0 ? esquerda.indice - direita.indice : comparado;
    })
    .map((item) => item.grupo);
}

function valor(grupo: GrupoPerfil, coluna: string): number | null {
  if (coluna === "grupo") {
    return grupo.numero;
  }
  if (coluna === "municipios") {
    return grupo.municipios;
  }
  if (coluna === "comparecimento") {
    return grupo.comparecimento;
  }
  if (coluna.startsWith("centro:")) {
    const indice = Number(coluna.slice("centro:".length));
    const texto = grupo.centro[indice];
    return texto === undefined ? null : lerFatia(texto);
  }
  return null;
}
