import type { Metadata } from "next";
import { Suspense } from "react";

import { DadosMunicipais2024 } from "@/components/relatorios/dados-municipais-2024";
import { EsqueletoDados, EsqueletoFiltros } from "@/components/relatorios/esqueleto-relatorio";
import { FerramentasApresentacao } from "@/components/relatorios/ferramentas-apresentacao";
import { FiltrosMunicipais2024 } from "@/components/relatorios/filtros-municipais-2024";
import {
  UFS,
  UF_TODAS,
  consultaPedida,
  escolher,
  type ConsultaRelatorio,
  type ValorConsulta,
} from "@/lib/eleicoes";

export const metadata: Metadata = {
  title: "Municipais 2024",
};

const CHAVES_FILTRO = ["uf"];

// "TODAS" ou uma UF com eleição municipal; DF e exterior ficam de fora (D15).
const UFS_MUNICIPAIS: readonly string[] = [
  UF_TODAS,
  ...UFS.map((uf) => uf.value).filter((uf) => uf !== "DF" && uf !== "ZZ"),
];

function lerUfMunicipal(valor: ValorConsulta): string {
  return escolher(valor, UFS_MUNICIPAIS, UF_TODAS);
}

export default function Municipais2024Page({
  searchParams,
}: {
  searchParams: Promise<ConsultaRelatorio>;
}) {
  return (
    <div className="leitura flex min-h-0 flex-1 flex-col gap-6 overflow-auto p-4 md:p-6">
      <h1 className="leitura-titulo text-3xl">Prefeitos e vereadores de 2024</h1>
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
  return <FiltrosMunicipais2024 uf={lerUfMunicipal(consulta.uf)} />;
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
  const uf = lerUfMunicipal(consulta.uf);
  return <DadosMunicipais2024 uf={uf === UF_TODAS ? null : uf} />;
}
