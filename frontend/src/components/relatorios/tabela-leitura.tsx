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
import {
  analisarFracao,
  formatarInteiro,
  formatarPercentualContagem,
  formatarPercentualTexto,
  TRACO,
  type Fracao,
} from "@/lib/fracao";
import {
  rotuloClasse,
  type LeituraCargo,
  type LeituraLugar,
  type PartidoRanqueado,
} from "@/lib/relatorios";

const COLUNAS = [
  "Lugar",
  "Líder presidente",
  "%",
  "Segundo",
  "%",
  "Margem",
  "Brancos presidente",
  "Nulos presidente",
  "Líder governador",
  "%",
  "Segundo",
  "%",
  "Brancos governador",
  "Nulos governador",
  "Classe",
] as const;

type TabelaLeituraProps = {
  rotulo: string;
  lugares: readonly LeituraLugar[];
};

type Direcao = "asc" | "desc";
type Valor = string | number | null;

export function TabelaLeitura({ rotulo, lugares }: TabelaLeituraProps) {
  const [coluna, setColuna] = useState<number | null>(null);
  const [direcao, setDirecao] = useState<Direcao>("asc");
  const ordenados = useMemo(
    () => ordenar(lugares, coluna, direcao),
    [lugares, coluna, direcao],
  );

  function alternar(indice: number) {
    if (coluna !== indice) {
      setColuna(indice);
      setDirecao("asc");
      return;
    }
    setDirecao((atual) => (atual === "asc" ? "desc" : "asc"));
  }

  return (
    <Table containerClassName="folha">
      <TableCaption className="sr-only">{rotulo}</TableCaption>
      <TableHeader>
        <TableRow>
          {COLUNAS.map((nome, indice) => (
            <TableHead
              key={nome + String(indice)}
              scope="col"
              aria-sort={aria(coluna, direcao, indice)}
              className={alinhamento(indice)}
            >
              <button
                type="button"
                className={`w-full bg-transparent ${alinhamento(indice)}`}
                onClick={() => alternar(indice)}
              >
                {nome}
              </button>
            </TableHead>
          ))}
        </TableRow>
      </TableHeader>
      <TableBody>
        {ordenados.map((lugar) => (
          <TableRow key={`${lugar.codigo}:${lugar.nome}`}>
            {valores(lugar).map((valor, indice) => (
              <TableCell
                key={`${lugar.codigo}-${indice}`}
                scope={indice === 0 ? "row" : undefined}
                className={alinhamento(indice)}
              >
                {valor}
              </TableCell>
            ))}
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

function alinhamento(indice: number): string {
  if (indice === 0 || indice === COLUNAS.length - 1) {
    return "text-left";
  }
  return "text-right tabular-nums";
}

function aria(
  coluna: number | null,
  direcao: Direcao,
  indice: number,
): "none" | "ascending" | "descending" {
  if (coluna !== indice) {
    return "none";
  }
  return direcao === "asc" ? "ascending" : "descending";
}

function ordenar(
  lugares: readonly LeituraLugar[],
  coluna: number | null,
  direcao: Direcao,
): LeituraLugar[] {
  if (coluna === null) {
    return [...lugares];
  }
  return lugares
    .map((lugar, indice) => ({ lugar, indice }))
    .sort((esquerda, direita) => {
      const comparado = comparar(esquerda.lugar, direita.lugar, coluna, direcao);
      return comparado === 0 ? esquerda.indice - direita.indice : comparado;
    })
    .map((item) => item.lugar);
}

function comparar(a: LeituraLugar, b: LeituraLugar, coluna: number, direcao: Direcao): number {
  if (coluna === 5) {
    return compararMargem(a.margin, b.margin, direcao);
  }
  return compararValor(chave(a, coluna), chave(b, coluna), coluna === 0 || coluna === 14, direcao);
}

function compararMargem(esquerda: string, direita: string, direcao: Direcao): number {
  return compararFracao(analisarFracao(esquerda), analisarFracao(direita), direcao);
}

function compararFracao(esquerda: Fracao | null, direita: Fracao | null, direcao: Direcao): number {
  if (esquerda === null && direita === null) {
    return 0;
  }
  if (esquerda === null) {
    return 1;
  }
  if (direita === null) {
    return -1;
  }
  const sinal = direcao === "asc" ? 1 : -1;
  const a = esquerda.numerador * direita.denominador;
  const b = direita.numerador * esquerda.denominador;
  if (a < b) {
    return -sinal;
  }
  if (a > b) {
    return sinal;
  }
  return 0;
}

function compararValor(
  esquerda: Valor,
  direita: Valor,
  textual: boolean,
  direcao: Direcao,
): number {
  if (esquerda === null && direita === null) {
    return 0;
  }
  if (esquerda === null) {
    return 1;
  }
  if (direita === null) {
    return -1;
  }
  const sinal = direcao === "asc" ? 1 : -1;
  if (textual && typeof esquerda === "string" && typeof direita === "string") {
    return sinal * esquerda.localeCompare(direita, "pt-BR", { numeric: true, sensitivity: "base" });
  }
  if (typeof esquerda === "number" && typeof direita === "number") {
    return sinal * (esquerda - direita);
  }
  return 0;
}

function chave(lugar: LeituraLugar, coluna: number): Valor {
  const presidente = lugar.presidente;
  const governador = lugar.governador;
  switch (coluna) {
    case 0:
      return lugar.nome;
    case 1:
      return presidente.leader?.partido ?? null;
    case 2:
      return razao(presidente.leader, presidente.valid);
    case 3:
      return presidente.runner_up?.partido ?? null;
    case 4:
      return razao(presidente.runner_up, presidente.valid);
    case 6:
      return presidente.branco;
    case 7:
      return presidente.nulo;
    case 8:
      return governador?.leader?.partido ?? null;
    case 9:
      return governador === null ? null : razao(governador.leader, governador.valid);
    case 10:
      return governador?.runner_up?.partido ?? null;
    case 11:
      return governador === null ? null : razao(governador.runner_up, governador.valid);
    case 12:
      return governador?.branco ?? null;
    case 13:
      return governador?.nulo ?? null;
    case 14:
      return rotuloClasse(lugar.classe);
    default:
      return null;
  }
}

function razao(partido: PartidoRanqueado | null, validos: number): number | null {
  if (partido === null || validos <= 0) {
    return null;
  }
  return partido.votos / validos;
}

function valores(lugar: LeituraLugar): string[] {
  const presidente = lugar.presidente;
  const governador = lugar.governador;
  return [
    lugar.nome,
    ...par(presidente.leader, presidente.valid),
    ...par(presidente.runner_up, presidente.valid),
    formatarPercentualTexto(lugar.margin),
    formatarInteiro(presidente.branco),
    formatarInteiro(presidente.nulo),
    ...cargoGovernador(governador),
    rotuloClasse(lugar.classe),
  ];
}

function cargoGovernador(cargo: LeituraCargo | null): string[] {
  if (cargo === null) {
    return [TRACO, TRACO, TRACO, TRACO, TRACO, TRACO];
  }
  return [
    ...par(cargo.leader, cargo.valid),
    ...par(cargo.runner_up, cargo.valid),
    formatarInteiro(cargo.branco),
    formatarInteiro(cargo.nulo),
  ];
}

function par(partido: PartidoRanqueado | null, validos: number): [string, string] {
  if (partido === null) {
    return [TRACO, TRACO];
  }
  return [String(partido.partido), formatarPercentualContagem(partido.votos, validos)];
}
