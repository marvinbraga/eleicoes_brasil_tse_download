"use client";

import { useMemo, useState } from "react";

import { FiltroSelect } from "@/components/filtros/filtro-select";
import {
  Table,
  TableBody,
  TableCaption,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { OPCOES_UF, UF_TODAS, type UfFiltro } from "@/lib/eleicoes";
import { formatarInteiro } from "@/lib/fracao";
import { compararNumero, compararTexto, textoOrdenavel, type Direcao } from "@/lib/ordem";
import type { MunicipioPerfil } from "@/lib/relatorios";

type Coluna = "lugar" | "grupo";
type Ordem = "none" | "ascending" | "descending";

export function MunicipiosPerfis({ municipios }: { municipios: readonly MunicipioPerfil[] }) {
  const [uf, setUf] = useState<UfFiltro>(UF_TODAS);
  const [coluna, setColuna] = useState<Coluna | null>(null);
  const [direcao, setDirecao] = useState<Direcao>("asc");
  const visiveis = useMemo(
    () => municipios.filter((municipio) => daUf(municipio.nome, uf)),
    [municipios, uf],
  );
  const ordenados = useMemo(
    () => ordenar(visiveis, coluna, direcao),
    [visiveis, coluna, direcao],
  );

  function alternar(proxima: Coluna) {
    if (coluna !== proxima) {
      setColuna(proxima);
      setDirecao("asc");
      return;
    }
    setDirecao((atual) => (atual === "asc" ? "desc" : "asc"));
  }

  function escolherUf(valor: string) {
    const proxima = OPCOES_UF.find((opcao) => opcao.value === valor);
    if (proxima !== undefined) {
      setUf(proxima.value);
    }
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-end gap-3">
        <div className="w-full max-w-xs">
          <FiltroSelect id="uf-municipios" label="UF" value={uf} options={OPCOES_UF} onChange={escolherUf} />
        </div>
      </div>
      <Table containerClassName="folha">
        <TableCaption className="sr-only">Municípios</TableCaption>
        <TableHeader>
          <TableRow>
            <Cabecalho
              rotulo="Lugar"
              alinhado="text-left"
              ordem={aria(coluna, direcao, "lugar")}
              onClick={() => alternar("lugar")}
            />
            <Cabecalho
              rotulo="Grupo"
              alinhado="text-right"
              ordem={aria(coluna, direcao, "grupo")}
              onClick={() => alternar("grupo")}
            />
          </TableRow>
        </TableHeader>
        <TableBody>
          {ordenados.length === 0 ? (
            <TableRow>
              <TableCell colSpan={2}>Nenhum lugar neste recorte.</TableCell>
            </TableRow>
          ) : (
            ordenados.map((municipio) => (
              <TableRow key={`${municipio.codigo}:${municipio.nome}`}>
                <TableCell scope="row">
                  <span className="block">{municipio.nome}</span>
                  {municipio.codigo.trim().length > 0 ? (
                    <span className="block font-sans text-xs text-muted-foreground">
                      {municipio.codigo}
                    </span>
                  ) : null}
                </TableCell>
                <TableCell className="text-right tabular-nums">
                  {formatarInteiro(municipio.grupo)}
                </TableCell>
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>
    </div>
  );
}

function Cabecalho({
  rotulo,
  alinhado,
  ordem,
  onClick,
}: {
  rotulo: string;
  alinhado: string;
  ordem: Ordem;
  onClick: () => void;
}) {
  return (
    <TableHead scope="col" aria-sort={ordem} className={alinhado}>
      <button type="button" className={`w-full bg-transparent ${alinhado}`} onClick={onClick}>
        {rotulo}
      </button>
    </TableHead>
  );
}

function aria(coluna: Coluna | null, direcao: Direcao, alvo: Coluna): Ordem {
  if (coluna !== alvo) {
    return "none";
  }
  return direcao === "asc" ? "ascending" : "descending";
}

function daUf(nome: string, uf: UfFiltro): boolean {
  if (uf === UF_TODAS) {
    return true;
  }
  return nome.includes(` (${uf})`);
}

function ordenar(
  municipios: readonly MunicipioPerfil[],
  coluna: Coluna | null,
  direcao: Direcao,
): MunicipioPerfil[] {
  if (coluna === null) {
    return [...municipios];
  }
  return municipios
    .map((municipio, indice) => ({ municipio, indice }))
    .sort((esquerda, direita) => {
      const comparado = comparar(esquerda.municipio, direita.municipio, coluna, direcao);
      return comparado === 0 ? esquerda.indice - direita.indice : comparado;
    })
    .map((item) => item.municipio);
}

function comparar(a: MunicipioPerfil, b: MunicipioPerfil, coluna: Coluna, direcao: Direcao): number {
  if (coluna === "lugar") {
    return compararTexto(textoOrdenavel(a.nome), textoOrdenavel(b.nome), direcao);
  }
  return compararNumero(a.grupo, b.grupo, direcao);
}
