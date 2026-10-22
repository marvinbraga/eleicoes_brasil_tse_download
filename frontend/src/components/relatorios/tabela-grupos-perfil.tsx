"use client";

import { useMemo, useState } from "react";

import {
  colunasDeGrupo,
  maiorFatia,
  ordenarGrupos,
  relativoDe,
  type ColunaGrupo,
} from "@/components/relatorios/modelo-grupos-perfil";
import { RotuloColunaPartido, tinta } from "@/components/relatorios/tabela-poder";
import {
  Table,
  TableBody,
  TableCaption,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { formatarInteiro, TRACO } from "@/lib/fracao";
import type { Direcao } from "@/lib/ordem";
import type { GrupoPerfil } from "@/lib/relatorios";

type TabelaGruposPerfisProps = {
  partidos: readonly number[];
  comCedula: boolean;
  grupos: readonly GrupoPerfil[];
};

type Ordem = "none" | "ascending" | "descending";

export function TabelaGruposPerfis({ partidos, comCedula, grupos }: TabelaGruposPerfisProps) {
  const colunas = useMemo(() => colunasDeGrupo(partidos, comCedula), [partidos, comCedula]);
  const quantidade = partidos.length + (comCedula ? 2 : 0);
  const maximo = useMemo(() => maiorFatia(grupos, quantidade), [grupos, quantidade]);
  const [coluna, setColuna] = useState<string | null>(null);
  const [direcao, setDirecao] = useState<Direcao>("asc");
  const ordenados = useMemo(
    () => ordenarGrupos(grupos, coluna, direcao),
    [grupos, coluna, direcao],
  );

  function alternar(proxima: string) {
    if (coluna !== proxima) {
      setColuna(proxima);
      setDirecao("asc");
      return;
    }
    setDirecao((atual) => (atual === "asc" ? "desc" : "asc"));
  }

  return (
    <Table containerClassName="folha">
      <TableCaption className="sr-only">Grupos</TableCaption>
      <TableHeader>
        <TableRow>
          {colunas.map((item) => (
            <Cabecalho
              key={item.id}
              coluna={item}
              ordem={aria(coluna, direcao, item.id)}
              onClick={() => alternar(item.id)}
            />
          ))}
        </TableRow>
      </TableHeader>
      <TableBody>
        {ordenados.length === 0 ? (
          <TableRow>
            <TableCell colSpan={colunas.length}>Nenhum grupo neste recorte.</TableCell>
          </TableRow>
        ) : (
          ordenados.map((grupo) => (
            <TableRow key={`${grupo.numero}:${grupo.centro.join("|")}`}>
              <TableCell scope="row">{`Grupo ${grupo.numero}`}</TableCell>
              <TableCell className="text-right tabular-nums">
                {formatarInteiro(grupo.municipios)}
              </TableCell>
              <TableCell className="text-right tabular-nums">
                {formatarInteiro(grupo.comparecimento)}
              </TableCell>
              {colunas.slice(3).map((item) => {
                const indice = Number(item.id.slice("centro:".length));
                const texto = grupo.centro[indice] ?? TRACO;
                const relativo = relativoDe(grupo.centro[indice], maximo);
                return (
                  <TableCell
                    key={item.id}
                    className="text-right tabular-nums"
                    style={relativo > 0 ? tinta(relativo) : undefined}
                  >
                    {texto}
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

function Cabecalho({
  coluna,
  ordem,
  onClick,
}: {
  coluna: ColunaGrupo;
  ordem: Ordem;
  onClick: () => void;
}) {
  const alinhado = coluna.numerica ? "text-right" : "text-left";
  return (
    <TableHead scope="col" aria-sort={ordem} className={alinhado} title={coluna.titulo}>
      <button type="button" className={`w-full bg-transparent ${alinhado}`} onClick={onClick}>
        {coluna.partido === undefined ? (
          coluna.rotulo
        ) : (
          <RotuloColunaPartido partido={coluna.partido} />
        )}
      </button>
    </TableHead>
  );
}

function aria(coluna: string | null, direcao: Direcao, id: string): Ordem {
  if (coluna !== id) {
    return "none";
  }
  return direcao === "asc" ? "ascending" : "descending";
}
