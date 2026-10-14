import type { Metadata } from "next";

import { MapaPagina } from "@/components/mapa/mapa-pagina";
import type { ConsultaRelatorio } from "@/lib/eleicoes";

export const metadata: Metadata = {
  title: "Mapa",
};

export default function MapaPage({
  searchParams,
}: {
  searchParams: Promise<ConsultaRelatorio>;
}) {
  return <MapaPagina searchParams={searchParams} />;
}
