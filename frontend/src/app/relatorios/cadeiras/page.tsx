import type { Metadata } from "next";
import { Suspense } from "react";

import { DadosCadeiras } from "@/components/relatorios/dados-cadeiras";
import { EsqueletoDados, EsqueletoFiltros } from "@/components/relatorios/esqueleto-relatorio";
import { FerramentasApresentacao } from "@/components/relatorios/ferramentas-apresentacao";
import { FiltrosCurtos } from "@/components/relatorios/filtros-curtos";
import { consultaPedida, lerAno, type ConsultaRelatorio, type Turno } from "@/lib/eleicoes";

export const metadata: Metadata = {
  title: "Simulação de cadeiras",
};

const CHAVES_FILTRO = ["ano"];
// As cadeiras se decidem no 1º turno; a API responde 422 para outro turno.
const TURNO_CADEIRAS: Turno = "1";

export default function CadeirasPage({
  searchParams,
}: {
  searchParams: Promise<ConsultaRelatorio>;
}) {
  return (
    <div className="leitura flex min-h-0 flex-1 flex-col gap-6 overflow-auto p-4 md:p-6">
      <h1 className="leitura-titulo text-3xl">Simulação de cadeiras</h1>
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
  return <FiltrosCurtos ano={lerAno(consulta.ano)} />;
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
  return <DadosCadeiras ano={lerAno(consulta.ano)} turno={TURNO_CADEIRAS} />;
}
