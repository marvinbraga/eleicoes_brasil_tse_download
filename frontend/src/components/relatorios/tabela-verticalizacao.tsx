import {
  Table,
  TableBody,
  TableCaption,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { TRACO } from "@/lib/fracao";
import { formatarRazao } from "@/lib/grafico-verticalizacao";
import { rotuloPartido } from "@/lib/partidos";
import {
  ROTULO_CARGO,
  type Classe,
  type Comparacao,
  type PartidoVertical,
} from "@/lib/verticalizacao";

const ROTULO_CLASSE: Record<Classe, string> = {
  puxador: "Puxador",
  base: "Base sem cabeça forte",
  alinhado: "Alinhado",
  sem_candidato: "Sem candidato",
};

const COLUNAS = [
  { rotulo: "Partido", alinhado: "text-left" },
  { rotulo: "Cargo", alinhado: "text-left" },
  { rotulo: "Onde concorreu", alinhado: "text-right" },
  { rotulo: "Esperado", alinhado: "text-right" },
  { rotulo: "Razão", alinhado: "text-right" },
  { rotulo: "Classe", alinhado: "text-left" },
  { rotulo: "UFs puxador", alinhado: "text-left" },
  { rotulo: "UFs base", alinhado: "text-left" },
  { rotulo: "Sem candidato (UFs)", alinhado: "text-left" },
] as const;

export function TabelaVerticalizacao({ partidos }: { partidos: readonly PartidoVertical[] }) {
  return (
    <Table containerClassName="folha">
      <TableCaption className="sr-only">
        Comparação entre a majoritária e o esperado pela força na proporcional
      </TableCaption>
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
        {partidos.length === 0 ? (
          <TableRow>
            <TableCell colSpan={COLUNAS.length}>Nenhum partido neste recorte.</TableCell>
          </TableRow>
        ) : (
          partidos.flatMap((partido) =>
            partido.comparacoes.map((comparacao) => (
              <Linha
                key={`${partido.partido}-${comparacao.majoritario}`}
                partido={partido.partido}
                comparacao={comparacao}
              />
            )),
          )
        )}
      </TableBody>
    </Table>
  );
}

function Linha({ partido, comparacao }: { partido: number; comparacao: Comparacao }) {
  return (
    <TableRow>
      <TableHead scope="row" className="h-auto p-2 text-left font-normal">
        {rotuloPartido(partido)}
      </TableHead>
      <TableCell>
        {ROTULO_CARGO[comparacao.majoritario]} × {ROTULO_CARGO[comparacao.proporcional]}
      </TableCell>
      <TableCell className="text-right tabular-nums">{comparacao.majoritaria ?? TRACO}</TableCell>
      <TableCell className="text-right tabular-nums">{comparacao.esperada ?? TRACO}</TableCell>
      <TableCell className="text-right tabular-nums">{formatarRazao(comparacao.razao)}</TableCell>
      <TableCell>{comparacao.classe === null ? TRACO : ROTULO_CLASSE[comparacao.classe]}</TableCell>
      <TableCell>{ufsDaClasse(comparacao, "puxador")}</TableCell>
      <TableCell>{ufsDaClasse(comparacao, "base")}</TableCell>
      <TableCell className="whitespace-normal">
        {comparacao.sem_candidato.length === 0
          ? TRACO
          : comparacao.sem_candidato.map((item) => `${item.uf} (${item.proporcional})`).join(", ")}
      </TableCell>
    </TableRow>
  );
}

function ufsDaClasse(comparacao: Comparacao, classe: Classe): string {
  const ufs = comparacao.por_uf.filter((item) => item.classe === classe).map((item) => item.uf);
  return ufs.length === 0 ? TRACO : ufs.join(", ");
}
