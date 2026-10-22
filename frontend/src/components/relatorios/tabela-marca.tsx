import {
  Table,
  TableBody,
  TableCaption,
  TableCell,
  TableFooter,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { formatarInteiro } from "@/lib/fracao";
import {
  MINIMO_VOTOS_RANKING,
  ROTULOS_CLASSE_MARCA,
  type MarcaCargo,
  type PartidoMarca,
} from "@/lib/grafico-marca";

const COLUNAS = [
  { rotulo: "Partido", alinhado: "text-left" },
  { rotulo: "Votos", alinhado: "text-right" },
  { rotulo: "Legenda", alinhado: "text-right" },
  { rotulo: "% de legenda", alinhado: "text-right" },
  { rotulo: "Vezes a média", alinhado: "text-right" },
  { rotulo: "Leitura", alinhado: "text-left" },
] as const;

const LEITURA_FORA = `Fora do ranking (menos de ${formatarInteiro(MINIMO_VOTOS_RANKING)} votos)`;

export function TabelaMarca({ marca }: { marca: MarcaCargo }) {
  return (
    <Table containerClassName="folha">
      <TableCaption className="sr-only">Voto de legenda, {marca.rotulo}</TableCaption>
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
        {marca.ranking.map((item) => (
          <Linha key={item.partido} item={item} leitura={ROTULOS_CLASSE_MARCA[item.classe]} />
        ))}
        {marca.fora.map((item) => (
          <Linha key={item.partido} item={item} leitura={LEITURA_FORA} />
        ))}
      </TableBody>
      <TableFooter>
        <TableRow>
          <TableHead scope="row" className="h-auto p-2 text-left">
            Todos os partidos
          </TableHead>
          <TableCell className="text-right tabular-nums">{formatarInteiro(marca.votos)}</TableCell>
          <TableCell className="text-right tabular-nums">{formatarInteiro(marca.legenda)}</TableCell>
          <TableCell className="text-right tabular-nums">{marca.texto}</TableCell>
          <TableCell className="text-right tabular-nums">1,00×</TableCell>
          <TableCell>Média do cargo</TableCell>
        </TableRow>
      </TableFooter>
    </Table>
  );
}

function Linha({ item, leitura }: { item: PartidoMarca; leitura: string }) {
  return (
    <TableRow>
      <TableHead scope="row" className="h-auto p-2 text-left font-normal">
        {item.rotulo}
      </TableHead>
      <TableCell className="text-right tabular-nums">{formatarInteiro(item.votos)}</TableCell>
      <TableCell className="text-right tabular-nums">{formatarInteiro(item.legenda)}</TableCell>
      <TableCell className="text-right tabular-nums">{item.texto}</TableCell>
      <TableCell className="text-right tabular-nums">{item.vezes}</TableCell>
      <TableCell>{leitura}</TableCell>
    </TableRow>
  );
}
