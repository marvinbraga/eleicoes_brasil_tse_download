import {
  Table,
  TableBody,
  TableCaption,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { Direcao } from "@/lib/ordem";
import {
  ESFERAS,
  ROTULOS_ESFERA,
  type ChaveColuna,
  type Coluna,
  type LinhaPlacar,
} from "@/lib/placar-forca";

export type ColunaOrdem = ChaveColuna | "unidade";

type TabelaForcaProps = {
  titulo: string;
  colunas: readonly Coluna[];
  linhas: readonly LinhaPlacar[];
  coluna: ColunaOrdem;
  direcao: Direcao;
  aoOrdenar: (coluna: ColunaOrdem) => void;
  aoEscolher?: (chave: string) => void;
  rotuloUnidade?: string;
};

type AriaOrdem = "none" | "ascending" | "descending";

// Apresentação pura: a ordem e os callbacks vêm de PlacarForcaVista.
export function TabelaForca({
  titulo,
  colunas,
  linhas,
  coluna,
  direcao,
  aoOrdenar,
  aoEscolher,
  rotuloUnidade = "Partido",
}: TabelaForcaProps) {
  const esferas = ESFERAS.map((esfera) => ({
    esfera,
    total: colunas.filter((item) => item.esfera === esfera).length,
  })).filter((item) => item.total > 0);
  return (
    <Table containerClassName="folha">
      <TableCaption>{titulo}</TableCaption>
      <TableHeader>
        <TableRow>
          <TableHead
            rowSpan={2}
            scope="col"
            aria-sort={aria(coluna, direcao, "unidade")}
            className="align-bottom"
          >
            <button type="button" className="w-full bg-transparent text-left" onClick={() => aoOrdenar("unidade")}>
              {rotuloUnidade}
            </button>
          </TableHead>
          {esferas.map(({ esfera, total }) => (
            <TableHead key={esfera} colSpan={total} scope="colgroup" className="border-l text-center">
              {ROTULOS_ESFERA[esfera]}
            </TableHead>
          ))}
        </TableRow>
        <TableRow>
          {colunas.map((item, indice) => (
            <TableHead
              key={item.chave}
              scope="col"
              aria-sort={aria(coluna, direcao, item.chave)}
              title={item.explicacao}
              className={`text-right ${inicioDeEsfera(colunas, indice) ? "border-l" : ""}`}
            >
              <button
                type="button"
                className="w-full bg-transparent text-right whitespace-normal"
                onClick={() => aoOrdenar(item.chave)}
              >
                {item.titulo}
              </button>
            </TableHead>
          ))}
        </TableRow>
      </TableHeader>
      <TableBody>
        {linhas.length === 0 ? (
          <TableRow>
            <TableCell colSpan={1 + colunas.length}>Nenhum partido neste recorte.</TableCell>
          </TableRow>
        ) : (
          linhas.map((linha) => (
            <TableRow key={linha.chave}>
              <TableCell scope="row" className="font-medium">
                {aoEscolher === undefined ? (
                  linha.rotulo
                ) : (
                  <button
                    type="button"
                    className="bg-transparent text-left underline-offset-4 hover:underline"
                    title={`Ver ${linha.rotulo} por UF`}
                    onClick={() => aoEscolher(linha.chave)}
                  >
                    {linha.rotulo}
                  </button>
                )}
              </TableCell>
              {colunas.map((item, indice) => {
                const valor = linha.valores[item.chave];
                return (
                  <TableCell
                    key={item.chave}
                    className={`text-right tabular-nums ${inicioDeEsfera(colunas, indice) ? "border-l" : ""}`}
                    title={valor.detalhe === "" ? undefined : valor.detalhe}
                  >
                    {valor.texto}
                    {valor.ordem === null ? <span className="sr-only"> (sem dados)</span> : null}
                  </TableCell>
                );
              })}
            </TableRow>
          ))
        )}
      </TableBody>
    </Table>
  );
}

function inicioDeEsfera(colunas: readonly Coluna[], indice: number): boolean {
  return indice === 0 || colunas[indice - 1]?.esfera !== colunas[indice]?.esfera;
}

function aria(coluna: ColunaOrdem, direcao: Direcao, alvo: ColunaOrdem): AriaOrdem {
  if (coluna !== alvo) {
    return "none";
  }
  return direcao === "asc" ? "ascending" : "descending";
}
