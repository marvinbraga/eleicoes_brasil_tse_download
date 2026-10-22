"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import { FiltroSelect } from "@/components/filtros/filtro-select";
import { GraficoForca } from "@/components/relatorios/grafico-forca";
import { TabelaForca, type ColunaOrdem } from "@/components/relatorios/tabela-forca";
import { Button } from "@/components/ui/button";
import { CARGOS_PODER } from "@/lib/eleicoes";
import { LIMIAR_PADRAO, type PlacarForca } from "@/lib/forca";
import { formatarInteiro } from "@/lib/fracao";
import { gruposEsfera } from "@/lib/grafico-forca";
import type { Direcao } from "@/lib/ordem";
import {
  COLUNA_PADRAO,
  ESFERAS,
  ROTULOS_ESFERA,
  colunasPlacar,
  linhasPlacar,
  linhasPorUf,
  ordenarPlacar,
  rotuloUnidade,
} from "@/lib/placar-forca";

const BRASIL = "BR";

const LEGENDA_GRAFICO =
  "Os 8 primeiros da tabela, na ordem atual. Cada barra é a parte do total da esfera: " +
  "votos válidos, UFs ou municípios. A escala vai de 0 a 100%.";

type Ordem = { coluna: ColunaOrdem; direcao: Direcao };

const ORDEM_PADRAO: Ordem = { coluna: COLUNA_PADRAO, direcao: "desc" };

export function PlacarForcaVista({ placar }: { placar: PlacarForca }) {
  const [limiar, setLimiar] = useState(() => limiarInicial(placar.limiares));
  const [recorte, setRecorte] = useState(BRASIL);
  const [ordem, setOrdem] = useState<Ordem>(ORDEM_PADRAO);
  const [partido, setPartido] = useState<string | null>(null);
  const [ordemUf, setOrdemUf] = useState<Ordem>(ORDEM_PADRAO);
  const tituloDetalhe = useRef<HTMLHeadingElement>(null);

  const escolhido = placar.ufs.find((uf) => uf.codigo === recorte) ?? placar.pais;
  const nivel = escolhido === placar.pais ? "pais" : "uf";
  const colunas = useMemo(() => colunasPlacar(limiar, nivel), [limiar, nivel]);
  const brutas = useMemo(() => linhasPlacar(escolhido, limiar, nivel), [escolhido, limiar, nivel]);
  const linhas = useMemo(() => ordenarPlacar(brutas, ordem.coluna, ordem.direcao), [brutas, ordem]);
  const colunasUf = useMemo(() => colunasPlacar(limiar, "uf"), [limiar]);
  const brutasUf = useMemo(
    () => (partido === null ? [] : linhasPorUf(placar, partido, limiar)),
    [placar, partido, limiar],
  );
  const linhasUf = useMemo(
    () => ordenarPlacar(brutasUf, ordemUf.coluna, ordemUf.direcao),
    [brutasUf, ordemUf],
  );
  const unidadeDetalhe = placar.pais.unidades.find((unidade) => unidade.chave === partido);
  const rotuloDetalhe = unidadeDetalhe === undefined ? (partido ?? "") : rotuloUnidade(unidadeDetalhe);
  const empates = escolhido.base.municipal?.empates ?? 0;

  useEffect(() => {
    if (partido !== null) {
      tituloDetalhe.current?.focus();
    }
  }, [partido]);

  const opcoesRecorte = [
    { value: BRASIL, label: "Brasil" },
    ...placar.ufs.map((uf) => ({ value: uf.codigo, label: uf.nome })),
  ];
  const opcoesLimiar = placar.limiares.map((n) => ({ value: String(n), label: `${n}%` }));
  const contexto = `municípios por ${rotuloCargo(placar.cargo_referencia)} · ${placar.ano}, turno ${placar.turno}`;

  return (
    <div className="flex flex-col gap-6">
      <div className="flex max-w-xl flex-wrap items-end gap-3">
        <FiltroSelect
          id="recorte-forca"
          label="Recorte"
          value={recorte}
          options={opcoesRecorte}
          onChange={setRecorte}
        />
        <FiltroSelect
          id="limiar-forca"
          label="Presença a partir de"
          value={String(limiar)}
          options={opcoesLimiar}
          onChange={(valor) => setLimiar(Number(valor))}
        />
      </div>
      <TabelaForca
        titulo={`${escolhido.nome} · ${contexto}`}
        colunas={colunas}
        linhas={linhas}
        coluna={ordem.coluna}
        direcao={ordem.direcao}
        aoOrdenar={(coluna) => setOrdem((atual) => alternar(atual, coluna))}
        aoEscolher={setPartido}
      />
      {empates > 0 ? (
        <p className="text-sm text-muted-foreground">
          {empates === 1
            ? "1 município com empate no topo não conta para nenhum partido."
            : `${formatarInteiro(empates)} municípios com empate no topo não contam para nenhum partido.`}
        </p>
      ) : null}
      {partido !== null ? (
        <section aria-labelledby="detalhe-forca" className="flex flex-col gap-3">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 id="detalhe-forca" ref={tituloDetalhe} tabIndex={-1} className="text-xl font-semibold">
              {rotuloDetalhe} por UF
            </h2>
            <Button type="button" variant="outline" size="sm" onClick={() => setPartido(null)}>
              Fechar
            </Button>
          </div>
          <TabelaForca
            titulo={`${rotuloDetalhe} por UF · ${contexto}`}
            colunas={colunasUf}
            linhas={linhasUf}
            coluna={ordemUf.coluna}
            direcao={ordemUf.direcao}
            aoOrdenar={(coluna) => setOrdemUf((atual) => alternar(atual, coluna))}
            rotuloUnidade="UF"
          />
        </section>
      ) : null}
      <div className="flex flex-col gap-4">
        {ESFERAS.map((esfera) => (
          <GraficoForca
            key={esfera}
            id={`grafico-forca-${esfera}`}
            titulo={ROTULOS_ESFERA[esfera]}
            legenda={LEGENDA_GRAFICO}
            grupos={gruposEsfera(linhas, colunas, esfera)}
          />
        ))}
      </div>
    </div>
  );
}

function limiarInicial(limiares: readonly number[]): number {
  return limiares.includes(LIMIAR_PADRAO) ? LIMIAR_PADRAO : (limiares[0] ?? LIMIAR_PADRAO);
}

// Mesma coluna inverte a direção; coluna nova começa do maior (números) ou de A a Z (nome).
function alternar(atual: Ordem, coluna: ColunaOrdem): Ordem {
  if (atual.coluna === coluna) {
    return { coluna, direcao: atual.direcao === "asc" ? "desc" : "asc" };
  }
  return { coluna, direcao: coluna === "unidade" ? "asc" : "desc" };
}

function rotuloCargo(cargo: string): string {
  const encontrado = CARGOS_PODER.find((item) => item.value === cargo);
  return encontrado === undefined ? cargo : encontrado.label.toLowerCase();
}
