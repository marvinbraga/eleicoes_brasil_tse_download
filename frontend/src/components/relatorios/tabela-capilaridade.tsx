import {
  Table,
  TableBody,
  TableCaption,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { NAO_RANQUEADAS, type PartidoCapilaridade } from "@/lib/capilaridade";
import { rotuloPartido } from "@/lib/partidos";

type TabelaCapilaridadeProps = {
  partidos: readonly PartidoCapilaridade[];
  selecionado: number | null;
  hrefs: Readonly<Record<number, string>>;
};

export function TabelaCapilaridade({ partidos, selecionado, hrefs }: TabelaCapilaridadeProps) {
  return (
    <Table containerClassName="folha">
      <TableCaption>Todos os partidos do recorte, na ordem do ranking</TableCaption>
      <TableHeader>
        <TableRow>
          <TableHead scope="col">Partido</TableHead>
          <TableHead scope="col">Classe</TableHead>
          <TableHead scope="col" className="text-right">
            Índice
          </TableHead>
          <TableHead scope="col" className="text-right">
            Fatia
          </TableHead>
          <TableHead scope="col" className="text-right">
            10% mais fortes (votos / eleitorado)
          </TableHead>
          <TableHead scope="col" className="text-right">
            Presença
          </TableHead>
          <TableHead scope="col" className="text-right">
            UFs com voto
          </TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {partidos.map((item) => {
          const fora = NAO_RANQUEADAS.has(item.classe);
          const atual = item.partido === selecionado;
          return (
            <TableRow
              key={item.partido}
              className={fora ? "text-muted-foreground" : undefined}
              aria-current={atual ? "true" : undefined}
            >
              <TableCell className={atual ? "font-semibold" : undefined}>
                <a href={hrefs[item.partido] ?? "#"} className="underline-offset-4 hover:underline">
                  {rotuloPartido(item.partido)}
                </a>
              </TableCell>
              <TableCell>{item.rotulo_classe}</TableCell>
              <TableCell className="text-right tabular-nums">{item.indice_100}</TableCell>
              <TableCell className="text-right tabular-nums">{item.fatia_texto}</TableCell>
              <TableCell className="text-right tabular-nums">
                {item.top10.parte_texto} / {item.top10.eleitorado_texto}
              </TableCell>
              <TableCell className="text-right tabular-nums">{item.presenca.parte_texto}</TableCell>
              <TableCell className="text-right tabular-nums">{item.ufs_com_voto}</TableCell>
            </TableRow>
          );
        })}
      </TableBody>
    </Table>
  );
}
