import { Suspense } from "react";

import { MapaQuadro } from "@/components/mapa/mapa-quadro";
import { SeletorTurnoMapa } from "@/components/mapa/seletor-turno-mapa";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  CARGO_DO_ARQUIVO_DO_MAPA,
  lerCargoMapa,
  lerTurno,
  type ConsultaRelatorio,
  type CargoMapa,
  type Turno,
} from "@/lib/eleicoes";
import { mapaExiste, turnoDoMapa } from "@/lib/mapas";

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
      <Skeleton className="min-h-0 w-full flex-1" />
    </div>
  );
}

function mensagemMapaAusente(cargo: CargoMapa, turno: Turno): string {
  return `O mapa do ${turno}º turno ainda não foi gravado. Rode uv run python scripts/relatorio_mapa.py --ano 2026 --turno ${turno} --cargo ${cargo} --sem-navegador.`;
}

async function MapaConteudo({ searchParams }: MapaPaginaProps) {
  const consulta = await searchParams;
  const cargo = lerCargoMapa(consulta.cargo);
  const turno = turnoDoMapa(cargo, lerTurno(consulta.turno));
  const existe = await mapaExiste(CARGO_DO_ARQUIVO_DO_MAPA, turno);

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-4 p-4">
      <h1 className="sr-only">Mapa eleitoral</h1>
      <SeletorTurnoMapa cargo={cargo} turno={turno} />
      {existe ? (
        <MapaQuadro cargo={cargo} turno={turno} />
      ) : (
        <Card>
          <CardContent>
            <p>{mensagemMapaAusente(CARGO_DO_ARQUIVO_DO_MAPA, turno)}</p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
