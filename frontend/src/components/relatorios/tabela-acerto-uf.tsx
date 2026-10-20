import {
  Table,
  TableBody,
  TableCaption,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { formatarInteiro } from "@/lib/fracao";
import type { AcertoUf } from "@/lib/relatorios";

const COLUNAS = [
  { rotulo: "UF", alinhado: "text-left" },
  { rotulo: "Municípios", alinhado: "text-right" },
  { rotulo: "Acerto", alinhado: "text-right" },
] as const;

export function TabelaAcertoUf({ linhas }: { linhas: readonly AcertoUf[] }) {
  return (
    <Table containerClassName="folha">
      <TableCaption className="sr-only">Acerto por UF</TableCaption>
      <TableHeader>
        <TableRow>
          {COLUNAS.map((coluna) => (
            <TableHead key={coluna.rotulo} scope="col" className={coluna.alinhado}>
              {coluna.rotulo}
            </TableHead>
          ))}
        </TableRow>
      </TableHeader>
      <TableBody>
        {linhas.length === 0 ? (
          <TableRow>
            <TableCell colSpan={COLUNAS.length}>Nenhuma UF neste recorte.</TableCell>
          </TableRow>
        ) : (
          linhas.map((linha) => (
            <TableRow key={linha.uf}>
              <TableHead scope="row" className="h-auto p-2 text-left font-normal">
                {linha.uf}
              </TableHead>
              <TableCell className="text-right tabular-nums">
                {formatarInteiro(linha.municipios)}
              </TableCell>
              <TableCell className="text-right tabular-nums">{linha.acerto}</TableCell>
            </TableRow>
          ))
        )}
      </TableBody>
    </Table>
  );
}
