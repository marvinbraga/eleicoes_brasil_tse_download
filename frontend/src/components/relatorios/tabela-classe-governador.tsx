"use client";

import { useMemo, useState } from "react";

import {
  Table,
  TableBody,
  TableCaption,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { lerFatia } from "@/lib/fatia";
import { formatarInteiro, TRACO } from "@/lib/fracao";
import { compararNumero, compararTexto, textoOrdenavel, type Direcao } from "@/lib/ordem";
import type { LinhaClasseGovernador } from "@/lib/relatorios";

type Coluna = "classe" | "apoio" | "recall" | "regras";
type Ordem = "none" | "ascending" | "descending";

const COLUNAS: { id: Coluna; rotulo: string; alinhado: string }[] = [
  { id: "classe", rotulo: "Situação", alinhado: "text-left" },
  { id: "apoio", rotulo: "Municípios", alinhado: "text-right" },
  { id: "recall", rotulo: "Reconhecidos", alinhado: "text-right" },
  { id: "regras", rotulo: "Condições", alinhado: "text-left" },
];

type Explicacao = {
  id: string;
  texto: string;
};

type TabelaClasseGovernadorProps = {
  linhas: readonly LinhaClasseGovernador[];
  reconhecidos: Explicacao;
};

export function TabelaClasseGovernador({ linhas, reconhecidos }: TabelaClasseGovernadorProps) {
  const [coluna, setColuna] = useState<Coluna | null>(null);
  const [direcao, setDirecao] = useState<Direcao>("asc");
  const ordenadas = useMemo(() => ordenar(linhas, coluna, direcao), [linhas, coluna, direcao]);

  function alternar(proxima: Coluna) {
    if (coluna !== proxima) {
      setColuna(proxima);
      setDirecao("asc");
      return;
    }
    setDirecao((atual) => (atual === "asc" ? "desc" : "asc"));
  }

  return (
    <Table containerClassName="folha">
      <TableCaption className="sr-only">Classe do governador</TableCaption>
      <TableHeader>
        <TableRow>
          {COLUNAS.map((item) => (
            <TableHead
              key={item.id}
              scope="col"
              aria-sort={aria(coluna, direcao, item.id)}
              className={item.alinhado}
              title={item.id === "recall" ? reconhecidos.texto : undefined}
            >
              <button
                type="button"
                className={`w-full bg-transparent ${item.alinhado}`}
                aria-describedby={item.id === "recall" ? reconhecidos.id : undefined}
                onClick={() => alternar(item.id)}
              >
                {item.rotulo}
              </button>
            </TableHead>
          ))}
        </TableRow>
      </TableHeader>
      <TableBody>
        {ordenadas.length === 0 ? (
          <TableRow>
            <TableCell colSpan={COLUNAS.length}>Nenhuma classe neste recorte.</TableCell>
          </TableRow>
        ) : (
          ordenadas.map((linha) => (
            <TableRow key={`${linha.classe}:${linha.rotulo}`}>
              <TableHead scope="row" className="h-auto p-2 align-top font-normal">
                {linha.rotulo}
              </TableHead>
              <TableCell className="text-right align-top tabular-nums">
                {formatarInteiro(linha.apoio)}
              </TableCell>
              <TableCell className="text-right align-top tabular-nums">{linha.recall}</TableCell>
              <TableCell className="align-top whitespace-normal text-left">
                {linha.regras.length === 0 ? (
                  TRACO
                ) : (
                  <ul className="list-disc pl-5">
                    {linha.regras.map((regra, indice) => (
                      <li key={`${indice}:${regra}`}>{regra}</li>
                    ))}
                  </ul>
                )}
              </TableCell>
            </TableRow>
          ))
        )}
      </TableBody>
    </Table>
  );
}

function aria(coluna: Coluna | null, direcao: Direcao, alvo: Coluna): Ordem {
  if (coluna !== alvo) {
    return "none";
  }
  return direcao === "asc" ? "ascending" : "descending";
}

function ordenar(
  linhas: readonly LinhaClasseGovernador[],
  coluna: Coluna | null,
  direcao: Direcao,
): LinhaClasseGovernador[] {
  if (coluna === null) {
    return [...linhas];
  }
  return linhas
    .map((linha, indice) => ({ linha, indice }))
    .sort((esquerda, direita) => {
      const comparado = comparar(esquerda.linha, direita.linha, coluna, direcao);
      return comparado === 0 ? esquerda.indice - direita.indice : comparado;
    })
    .map((item) => item.linha);
}

function comparar(
  a: LinhaClasseGovernador,
  b: LinhaClasseGovernador,
  coluna: Coluna,
  direcao: Direcao,
): number {
  if (coluna === "apoio") {
    return compararNumero(a.apoio, b.apoio, direcao);
  }
  if (coluna === "recall") {
    return compararNumero(lerFatia(a.recall), lerFatia(b.recall), direcao);
  }
  if (coluna === "regras") {
    return compararTexto(textoOrdenavel(a.regras.join(" ")), textoOrdenavel(b.regras.join(" ")), direcao);
  }
  return compararTexto(textoOrdenavel(a.rotulo), textoOrdenavel(b.rotulo), direcao);
}
