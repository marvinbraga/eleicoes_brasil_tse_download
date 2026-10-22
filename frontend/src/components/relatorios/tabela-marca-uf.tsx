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
import { MINIMO_VOTOS_UF, type EstadoCelula, type MarcaCargo } from "@/lib/grafico-marca";

const MOTIVOS: Record<Exclude<EstadoCelula, "ok">, string> = {
  "sem-votos": "sem votos",
  "sem-candidato": "sem candidato",
  poucos: `menos de ${formatarInteiro(MINIMO_VOTOS_UF)} votos`,
};

export function TabelaMarcaUf({ marca }: { marca: MarcaCargo }) {
  if (marca.ranking.length === 0 || marca.ufs.length === 0) {
    return null;
  }
  return (
    <Table containerClassName="folha">
      <TableCaption className="caption-top text-left">
        <span className="block font-medium text-foreground">
          Voto de legenda por UF, {marca.rotulo}
        </span>
        <span className="block">
          Cada célula é a parte do voto do partido na UF que foi de legenda. Só partidos do
          ranking.
        </span>
      </TableCaption>
      <TableHeader>
        <TableRow>
          <TableHead scope="col" className="text-left">
            UF
          </TableHead>
          <TableHead scope="col" className="text-right">
            Média da UF
          </TableHead>
          {marca.ranking.map((item) => (
            <TableHead key={item.partido} scope="col" className="text-right">
              {item.rotulo}
            </TableHead>
          ))}
        </TableRow>
      </TableHeader>
      <TableBody>
        {marca.ufs.map((uf) => (
          <TableRow key={uf.uf}>
            <TableHead scope="row" className="h-auto p-2 text-left font-normal">
              {uf.nome}
            </TableHead>
            <TableCell className="text-right tabular-nums">{uf.texto}</TableCell>
            {uf.celulas.map((celula) => (
              <TableCell key={celula.partido} className="text-right tabular-nums">
                {celula.texto}
                {celula.estado === "ok" ? null : (
                  <span className="sr-only"> ({MOTIVOS[celula.estado]})</span>
                )}
              </TableCell>
            ))}
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
