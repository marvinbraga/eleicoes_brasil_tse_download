import type { Metadata } from "next";

import { RelatorioPagina } from "@/components/relatorios/relatorio-pagina";
import type { ConsultaRelatorio } from "@/lib/eleicoes";

export const metadata: Metadata = {
  title: "Presidente e governador",
};

export const maxDuration = 600;

export default function PresidenteGovernadorPage({
  searchParams,
}: {
  searchParams: Promise<ConsultaRelatorio>;
}) {
  return (
    <RelatorioPagina
      tipo="presidente-governador"
      searchParams={searchParams}
    />
  );
}
