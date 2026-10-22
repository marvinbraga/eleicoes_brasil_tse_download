import type { Metadata } from "next";
import { Suspense } from "react";

import { DadosCapilaridade } from "@/components/relatorios/dados-capilaridade";
import { EsqueletoDados, EsqueletoFiltros } from "@/components/relatorios/esqueleto-relatorio";
import { FerramentasApresentacao } from "@/components/relatorios/ferramentas-apresentacao";
import { FiltrosCapilaridade } from "@/components/relatorios/filtros-capilaridade";
import { consultaPedida, lerAno, lerCargoPoder, lerTurno } from "@/lib/eleicoes";
import { lerRecorte, type ConsultaCapilaridade } from "@/lib/ler-capilaridade";

export const metadata: Metadata = {
  title: "Capilaridade partidária",
};

export const maxDuration = 600;

const CHAVES_FILTRO = ["ano", "turno", "cargo", "recorte"];

export default function CapilaridadePage({
  searchParams,
}: {
  searchParams: Promise<ConsultaCapilaridade>;
}) {
  return (
    <div className="leitura flex min-h-0 flex-1 flex-col gap-6 overflow-auto p-4 md:p-6">
      <h1 className="leitura-titulo text-3xl">Capilaridade partidária</h1>
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
  searchParams: Promise<ConsultaCapilaridade>;
}) {
  const consulta = await searchParams;
  return (
    <FiltrosCapilaridade
      ano={lerAno(consulta.ano)}
      turno={lerTurno(consulta.turno)}
      cargo={lerCargoPoder(consulta.cargo)}
      recorte={lerRecorte(consulta.recorte)}
    />
  );
}

async function DadosComConsulta({
  searchParams,
}: {
  searchParams: Promise<ConsultaCapilaridade>;
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
    <DadosCapilaridade
      ano={lerAno(consulta.ano)}
      turno={lerTurno(consulta.turno)}
      cargo={lerCargoPoder(consulta.cargo)}
      recorte={lerRecorte(consulta.recorte)}
      partido={consulta.partido}
    />
  );
}
