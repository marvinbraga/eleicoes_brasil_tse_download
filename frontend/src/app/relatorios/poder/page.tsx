import type { Metadata } from "next";

import { RelatorioPagina } from "@/components/relatorios/relatorio-pagina";
import type { ConsultaRelatorio } from "@/lib/eleicoes";

export const metadata: Metadata = {
  title: "Poder",
};

export const maxDuration = 600;

export default function PoderPage({
  searchParams,
}: {
  searchParams: Promise<ConsultaRelatorio>;
}) {
  return <RelatorioPagina tipo="poder" searchParams={searchParams} />;
}
