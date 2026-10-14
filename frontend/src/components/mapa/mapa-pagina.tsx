import { Suspense } from "react";

import { MapaFiltro, MapaQuadro } from "@/components/mapa/mapa-filtro";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  lerCargoMapa,
  type ConsultaRelatorio,
  type CargoMapa,
} from "@/lib/eleicoes";
import { mapaExiste } from "@/lib/mapas";

type MapaPaginaProps = {
  searchParams: Promise<ConsultaRelatorio>;
};

export function MapaPagina({ searchParams }: MapaPaginaProps) {
  return (
    <Suspense fallback={<MapaFallback />}>
      <MapaConteudo searchParams={searchParams} />
    </Suspense>
  );
}

function MapaFallback() {
  return (
    <div className="flex min-h-0 flex-1 flex-col gap-4 p-4" aria-busy="true">
      <p className="sr-only">Carregando mapa…</p>
      <Skeleton className="h-14 w-44" />
      <Skeleton className="min-h-0 w-full flex-1" />
    </div>
  );
}

function mensagemMapaAusente(cargo: CargoMapa): string {
  return `O mapa ainda não foi gravado. Rode uv run python scripts/relatorio_mapa.py --ano 2026 --turno 1 --cargo ${cargo} --sem-navegador.`;
}

async function MapaConteudo({ searchParams }: MapaPaginaProps) {
  const consulta = await searchParams;
  const cargo = lerCargoMapa(consulta.cargo);
  const existe = await mapaExiste(cargo);

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-4 p-4">
      <h1 className="sr-only">Mapa eleitoral</h1>
      <MapaFiltro cargo={cargo} />
      {existe ? (
        <MapaQuadro cargo={cargo} />
      ) : (
        <Card>
          <CardContent>
            <p>{mensagemMapaAusente(cargo)}</p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
