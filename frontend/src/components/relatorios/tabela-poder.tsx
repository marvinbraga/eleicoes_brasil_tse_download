"use client";

import { useMemo, useState, type ReactNode } from "react";

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
  alfaFracao,
  formatarInteiro,
  formatarPercentualContagem,
  fracaoMaior,
  TRACO,
  type Fracao,
} from "@/lib/fracao";
import { rotuloPartido, siglaPartido } from "@/lib/partidos";
import type { CelulaGrade, LinhaGrade } from "@/lib/relatorios";

type TabelaPoderProps = {
  titulo: string;
  apoio: string;
  colunas: readonly number[];
  linhas: readonly LinhaGrade[];
  escala: readonly LinhaGrade[];
};

type CelulaVista = {
  texto: string;
  titulo: string | undefined;
  relativo: number;
};

type Coluna = "lugar" | "validos" | number;
type Direcao = "asc" | "desc";

const FRACAO_ZERO: Fracao = { numerador: BigInt(0), denominador: BigInt(1) };
const LIMITE_TEXTO = 3 / 5;

export function TabelaPoder({ titulo, apoio, colunas, linhas, escala }: TabelaPoderProps) {
  const [coluna, setColuna] = useState<Coluna | null>(null);
  const [direcao, setDirecao] = useState<Direcao>("asc");
  const maximo = useMemo(() => maiorParticipacao(escala), [escala]);
  const ordenadas = useMemo(
    () => ordenar(linhas, coluna, direcao),
    [linhas, coluna, direcao],
  );
  const largura = 2 + colunas.length;

  function alternar(proxima: Coluna) {
    if (coluna !== proxima) {
      setColuna(proxima);
      setDirecao("asc");
      return;
    }
    setDirecao((atual) => (atual === "asc" ? "desc" : "asc"));
  }

  return (
    <section className="flex flex-col gap-3">
      <div className="flex flex-col gap-1">
        <h2 className="leitura-titulo text-2xl">{titulo}</h2>
        <p className="text-sm text-muted-foreground">{apoio}</p>
      </div>
      <Table containerClassName="folha">
      <TableCaption className="sr-only">
        {titulo}. {apoio}
      </TableCaption>
      <TableHeader>
        <TableRow>
          <Cabecalho
            rotulo="Lugar"
            alinhado="text-left"
            ariaOrdem={aria(coluna, direcao, "lugar")}
            onClick={() => alternar("lugar")}
          />
          <Cabecalho
            rotulo="Votos válidos"
            alinhado="text-right"
            ariaOrdem={aria(coluna, direcao, "validos")}
            onClick={() => alternar("validos")}
          />
          {colunas.map((partido) => (
            <Cabecalho
              key={partido}
              rotulo={<RotuloColunaPartido partido={partido} />}
              alinhado="text-right"
              titulo={rotuloPartido(partido)}
              ariaOrdem={aria(coluna, direcao, partido)}
              onClick={() => alternar(partido)}
            />
          ))}
        </TableRow>
      </TableHeader>
      <TableBody>
        {ordenadas.length === 0 ? (
          <TableRow>
            <TableCell colSpan={largura}>Nenhum lugar neste recorte.</TableCell>
          </TableRow>
        ) : (
          ordenadas.map((linha) => {
            const validos = votosValidos(linha);
            return (
              <TableRow key={`${linha.codigo}:${linha.nome}`}>
                <TableCell scope="row">{linha.nome}</TableCell>
                <TableCell className="text-right tabular-nums">
                  {formatarInteiro(validos)}
                </TableCell>
                {colunas.map((partido) => {
                  const celula = vista(linha, partido, validos, maximo);
                  return (
                    <TableCell
                      key={partido}
                      className="text-right tabular-nums"
                      title={celula.titulo}
                      style={celula.relativo > 0 ? tinta(celula.relativo) : undefined}
                    >
                      {celula.texto}
                    </TableCell>
                  );
                })}
              </TableRow>
            );
          })
        )}
      </TableBody>
      </Table>
    </section>
  );
}

function Cabecalho({
  rotulo,
  alinhado,
  titulo,
  ariaOrdem,
  onClick,
}: {
  rotulo: ReactNode;
  alinhado: string;
  titulo?: string;
  ariaOrdem: "none" | "ascending" | "descending";
  onClick: () => void;
}) {
  return (
    <TableHead scope="col" aria-sort={ariaOrdem} className={alinhado} title={titulo}>
      <button type="button" className={`w-full bg-transparent ${alinhado}`} onClick={onClick}>
        {rotulo}
      </button>
    </TableHead>
  );
}

export function RotuloColunaPartido({ partido }: { partido: number }) {
  const sigla = siglaPartido(partido);
  if (sigla === null) {
    return <>{partido}</>;
  }
  return (
    <span className="inline-flex flex-col items-end text-xs leading-tight">
      <span>{sigla}</span>
      <span className="font-normal text-muted-foreground tabular-nums">{partido}</span>
    </span>
  );
}

function aria(
  coluna: Coluna | null,
  direcao: Direcao,
  alvo: Coluna,
): "none" | "ascending" | "descending" {
  if (coluna !== alvo) {
    return "none";
  }
  return direcao === "asc" ? "ascending" : "descending";
}

function vista(
  linha: LinhaGrade,
  partido: number,
  validos: number,
  maximo: Fracao,
): CelulaVista {
  const celula = linha.celulas.find((item) => item.partido === partido);
  if (celula === undefined) {
    return { texto: TRACO, titulo: undefined, relativo: 0 };
  }
  const fracao = participacao(celula.votos, validos);
  return {
    texto: validos > 0 ? formatarPercentualContagem(celula.votos, validos) : TRACO,
    titulo: titulo(celula, validos),
    relativo: alfaFracao(fracao, maximo),
  };
}

function titulo(celula: CelulaGrade, validos: number): string {
  return (
    `nominais ${formatarInteiro(celula.votos_nominais)}, ` +
    `legenda ${formatarInteiro(celula.votos_legenda)}, ` +
    `votos ${formatarInteiro(celula.votos)}, ` +
    `votos válidos ${formatarInteiro(validos)}, ` +
    `comparecimento ${formatarInteiro(celula.comparecimento)}`
  );
}

function votosValidos(linha: LinhaGrade): number {
  return linha.celulas.reduce((soma, celula) => soma + celula.votos, 0);
}

function votosDoPartido(linha: LinhaGrade, partido: number): number | null {
  const celula = linha.celulas.find((item) => item.partido === partido);
  return celula === undefined ? null : celula.votos;
}

function participacao(votos: number, validos: number): Fracao {
  if (validos <= 0) {
    return FRACAO_ZERO;
  }
  return { numerador: BigInt(votos), denominador: BigInt(validos) };
}

function maiorParticipacao(linhas: readonly LinhaGrade[]): Fracao {
  return linhas.reduce<Fracao>((maximo, linha) => {
    const validos = votosValidos(linha);
    return linha.celulas.reduce(
      (atual, celula) => fracaoMaior(atual, participacao(celula.votos, validos)),
      maximo,
    );
  }, FRACAO_ZERO);
}

export function tinta(relativo: number): { backgroundColor: string; color: string } {
  const limitado = relativo < 0 ? 0 : Math.min(relativo, 1);
  const parte = Math.round(limitado * 1000) / 10;
  return {
    backgroundColor: `color-mix(in srgb, var(--tinta-quente) ${parte}%, var(--tinta-frio))`,
    color: limitado > LIMITE_TEXTO ? "var(--tinta-texto-quente)" : "var(--tinta-texto)",
  };
}

function ordenar(
  linhas: readonly LinhaGrade[],
  coluna: Coluna | null,
  direcao: Direcao,
): LinhaGrade[] {
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

function comparar(a: LinhaGrade, b: LinhaGrade, coluna: Coluna, direcao: Direcao): number {
  if (coluna === "lugar") {
    const sinal = direcao === "asc" ? 1 : -1;
    return sinal * a.nome.localeCompare(b.nome, "pt-BR", { numeric: true, sensitivity: "base" });
  }
  const esquerda = coluna === "validos" ? votosValidos(a) : votosDoPartido(a, coluna);
  const direita = coluna === "validos" ? votosValidos(b) : votosDoPartido(b, coluna);
  return compararNumero(esquerda, direita, direcao);
}

function compararNumero(
  esquerda: number | null,
  direita: number | null,
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
  return sinal * (esquerda - direita);
}
