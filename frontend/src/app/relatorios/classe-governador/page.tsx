import type { Metadata } from "next";
import { Suspense } from "react";

import { DadosClasseGovernador } from "@/components/relatorios/dados-classe-governador";
import { EsqueletoDados, EsqueletoFiltros } from "@/components/relatorios/esqueleto-relatorio";
import { FerramentasApresentacao } from "@/components/relatorios/ferramentas-apresentacao";
import { FiltrosCurtos } from "@/components/relatorios/filtros-curtos";
import { consultaPedida, lerAno, lerTurno, type ConsultaRelatorio } from "@/lib/eleicoes";

export const metadata: Metadata = {
  title: "Classe do governador",
};

export const maxDuration = 600;

const CHAVES_FILTRO = ["ano", "turno"];

export default function ClasseGovernadorPage({
  searchParams,
}: {
  searchParams: Promise<ConsultaRelatorio>;
}) {
  return (
    <div className="leitura flex min-h-0 flex-1 flex-col gap-6 overflow-auto p-4 md:p-6">
      <h1 className="leitura-titulo text-3xl">Classe do governador</h1>
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
  const ano = lerAno(consulta.ano);
  const turno = lerTurno(consulta.turno);
  return <FiltrosCurtos ano={ano} turno={turno} />;
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
  return <DadosClasseGovernador ano={lerAno(consulta.ano)} turno={lerTurno(consulta.turno)} />;
}
