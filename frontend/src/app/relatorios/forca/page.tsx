import type { Metadata } from "next";
import { Suspense } from "react";

import { DadosForca } from "@/components/relatorios/dados-forca";
import { EsqueletoDados, EsqueletoFiltros } from "@/components/relatorios/esqueleto-relatorio";
import { FerramentasApresentacao } from "@/components/relatorios/ferramentas-apresentacao";
import { FiltrosForca } from "@/components/relatorios/filtros-forca";
import {
  CARGOS_PODER,
  consultaPedida,
  escolher,
  lerAno,
  lerTurno,
  type CargoPoder,
  type ConsultaRelatorio,
} from "@/lib/eleicoes";

export const metadata: Metadata = {
  title: "Força partidária",
};

export const maxDuration = 600;

const CHAVES_FILTRO = ["ano", "turno", "cargo"];

const VALORES_CARGO: readonly CargoPoder[] = CARGOS_PODER.map((c) => c.value);

function lerCargoReferencia(consulta: ConsultaRelatorio): CargoPoder {
  return escolher(consulta.cargo, VALORES_CARGO, "deputadoEstadual");
}

export default function ForcaPage({
  searchParams,
}: {
  searchParams: Promise<ConsultaRelatorio>;
}) {
  return (
    <div className="leitura flex min-h-0 flex-1 flex-col gap-6 overflow-auto p-4 md:p-6">
      <h1 className="leitura-titulo text-3xl">Força partidária</h1>
      <FerramentasApresentacao />
      <Suspense fallback={<EsqueletoFiltros chaves={CHAVES_FILTRO} />}>
        <FiltrosComConsulta searchParams={searchParams} />
      </Suspense>
      <Suspense fallback={<EsqueletoDados />}>
        <DadosComConsulta searchParams={searchParams} />
      </Suspense>
    </div>
  );
}

async function FiltrosComConsulta({
  searchParams,
}: {
  searchParams: Promise<ConsultaRelatorio>;
}) {
  const consulta = await searchParams;
  return (
    <FiltrosForca
      ano={lerAno(consulta.ano)}
      turno={lerTurno(consulta.turno)}
      cargo={lerCargoReferencia(consulta)}
    />
  );
}

async function DadosComConsulta({
  searchParams,
}: {
  searchParams: Promise<ConsultaRelatorio>;
}) {
  const consulta = await searchParams;
  if (!consultaPedida(consulta.consultar)) {
    return (
      <p className="text-sm text-muted-foreground">
        Selecione os filtros e clique em Consultar.
      </p>
    );
  }
  return (
    <DadosForca
      ano={lerAno(consulta.ano)}
      turno={lerTurno(consulta.turno)}
      cargo={lerCargoReferencia(consulta)}
    />
  );
}
