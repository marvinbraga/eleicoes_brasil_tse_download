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
import { rotuloFase, rotuloLegenda, rotuloSituacao } from "@/lib/grafico-cadeiras";
import { rotuloPartido } from "@/lib/partidos";
import type {
  CandidatoMajoritario,
  CasaCadeiras,
  CasaUfCadeiras,
  GovernoCadeiras,
  LegendaCadeiras,
  SenadoCadeiras,
} from "@/lib/relatorios";

const MARCA_EMPATE = " *";

function candidato(item: CandidatoMajoritario | undefined): string {
  if (item === undefined) {
    return "—";
  }
  return `Nº ${item.numero} (${rotuloPartido(item.partido)}), ${item.fatia}`;
}

export function TabelaLegendasCasa({
  casa,
  legendas,
}: {
  casa: CasaCadeiras;
  legendas: readonly LegendaCadeiras[];
}) {
  return (
    <Table containerClassName="folha">
      <TableCaption className="sr-only">Cadeiras estimadas por legenda — {casa.nome}</TableCaption>
      <TableHeader>
        <TableRow>
          <TableHead scope="col">Partido ou federação</TableHead>
          <TableHead scope="col" className="text-right">
            Cadeiras
          </TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {casa.legendas.map((item) => {
          const legenda = legendas.find((linha) => linha.codigo === item.legenda);
          const membros = legenda?.federacao
            ? legenda.partidos
                .map(
                  (numero) =>
                    `${rotuloPartido(numero)}: ${formatarInteiro(
                      casa.partidos.find((linha) => linha.partido === numero)?.cadeiras ?? 0,
                    )}`,
                )
                .join(" · ")
            : null;
          return (
            <TableRow key={item.legenda}>
              <TableHead scope="row" className="h-auto p-2 text-left font-normal">
                {rotuloLegenda(item.legenda, legendas)}
                {membros ? (
                  <span className="block text-xs text-muted-foreground">{membros}</span>
                ) : null}
              </TableHead>
              <TableCell className="text-right tabular-nums">
                {formatarInteiro(item.cadeiras)}
              </TableCell>
            </TableRow>
          );
        })}
      </TableBody>
    </Table>
  );
}

export function DetalheUf({
  uf,
  legendas,
}: {
  uf: CasaUfCadeiras;
  legendas: readonly LegendaCadeiras[];
}) {
  const listas = uf.listas.filter((lista) => lista.cadeiras > 0 || lista.quociente_partidario > 0);
  return (
    <details className="rounded-md border border-border px-3 py-2">
      <summary className="cursor-pointer">
        {uf.uf}: {formatarInteiro(uf.vagas)} vagas, quociente eleitoral{" "}
        {formatarInteiro(uf.quociente_eleitoral)}
        {uf.vagas_sem_candidato > 0
          ? `, ${formatarInteiro(uf.vagas_sem_candidato)} sem candidato`
          : ""}
      </summary>
      <div className="mt-3 flex flex-col gap-3">
        <Table containerClassName="folha">
          <TableCaption className="sr-only">Legendas em {uf.uf}</TableCaption>
          <TableHeader>
            <TableRow>
              <TableHead scope="col">Legenda</TableHead>
              <TableHead scope="col" className="text-right">Votos</TableHead>
              <TableHead scope="col" className="text-right">QP</TableHead>
              <TableHead scope="col" className="text-right">Pelo QP</TableHead>
              <TableHead scope="col" className="text-right">Média 80/20</TableHead>
              <TableHead scope="col" className="text-right">Média livre</TableHead>
              <TableHead scope="col" className="text-right">Total</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {listas.map((lista) => (
              <TableRow key={lista.legenda}>
                <TableHead scope="row" className="h-auto p-2 text-left font-normal">
                  {rotuloLegenda(lista.legenda, legendas)}
                </TableHead>
                <TableCell className="text-right tabular-nums">{formatarInteiro(lista.votos)}</TableCell>
                <TableCell className="text-right tabular-nums">{lista.quociente_partidario}</TableCell>
                <TableCell className="text-right tabular-nums">{lista.cadeiras_quociente}</TableCell>
                <TableCell className="text-right tabular-nums">{lista.cadeiras_media}</TableCell>
                <TableCell className="text-right tabular-nums">{lista.cadeiras_media_livre}</TableCell>
                <TableCell className="text-right tabular-nums">{lista.cadeiras}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
        <Table containerClassName="folha">
          <TableCaption className="sr-only">Eleitos estimados em {uf.uf}</TableCaption>
          <TableHeader>
            <TableRow>
              <TableHead scope="col">Número</TableHead>
              <TableHead scope="col">Partido</TableHead>
              <TableHead scope="col" className="text-right">Votos</TableHead>
              <TableHead scope="col">Como entrou</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {uf.eleitos.map((eleito) => (
              <TableRow key={eleito.numero}>
                <TableHead scope="row" className="h-auto p-2 text-left font-normal tabular-nums">
                  {eleito.numero}
                  {eleito.empate ? MARCA_EMPATE : ""}
                </TableHead>
                <TableCell>{rotuloPartido(eleito.partido)}</TableCell>
                <TableCell className="text-right tabular-nums">{formatarInteiro(eleito.votos)}</TableCell>
                <TableCell>{rotuloFase(eleito.fase)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </details>
  );
}

export function TabelaSenado({ senado }: { senado: SenadoCadeiras }) {
  return (
    <Table containerClassName="folha">
      <TableCaption className="sr-only">Senadores estimados por UF</TableCaption>
      <TableHeader>
        <TableRow>
          <TableHead scope="col">UF</TableHead>
          <TableHead scope="col">1ª vaga</TableHead>
          <TableHead scope="col">2ª vaga</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {senado.ufs.map((uf) => (
          <TableRow key={uf.uf}>
            <TableHead scope="row" className="h-auto p-2 text-left font-normal">
              {uf.uf}
              {uf.empate ? MARCA_EMPATE : ""}
            </TableHead>
            <TableCell>{candidato(uf.eleitos[0])}</TableCell>
            <TableCell>{candidato(uf.eleitos[1])}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

export function TabelaGoverno({ governo }: { governo: GovernoCadeiras }) {
  return (
    <Table containerClassName="folha">
      <TableCaption className="sr-only">Governador por UF</TableCaption>
      <TableHeader>
        <TableRow>
          <TableHead scope="col">UF</TableHead>
          <TableHead scope="col">Situação</TableHead>
          <TableHead scope="col">1º colocado</TableHead>
          <TableHead scope="col">2º colocado</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {governo.ufs.map((uf) => (
          <TableRow key={uf.uf}>
            <TableHead scope="row" className="h-auto p-2 text-left font-normal">
              {uf.uf}
              {uf.empate ? MARCA_EMPATE : ""}
            </TableHead>
            <TableCell>{rotuloSituacao(uf.situacao)}</TableCell>
            <TableCell>{candidato(uf.candidatos[0])}</TableCell>
            <TableCell>{candidato(uf.candidatos[1])}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
