import type { Metadata } from "next";
import { connection } from "next/server";
import { Suspense } from "react";

import { QuadroEstados } from "@/components/estados/quadro-estados";
import { SeletorTurnoEstados } from "@/components/estados/seletor-turno-estados";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import type { ConsultaRelatorio } from "@/lib/eleicoes";
import { comandoEstados, estadosExiste, lerTurnoEstados } from "@/lib/estados";

export const metadata: Metadata = {
  title: "Como votou cada estado",
};

type EstadosProps = {
  searchParams: Promise<ConsultaRelatorio>;
};

export default function EstadosPage({ searchParams }: EstadosProps) {
  return (
    <Suspense fallback={<EstadosFallback />}>
      <EstadosConteudo searchParams={searchParams} />
    </Suspense>
  );
}

function EstadosFallback() {
  return (
    <div className="flex min-h-0 flex-1 flex-col gap-4 p-4" aria-busy="true">
      <p className="sr-only">Carregando relatório…</p>
      <Skeleton className="min-h-0 w-full flex-1" />
    </div>
  );
}

async function EstadosConteudo({ searchParams }: EstadosProps) {
  await connection();
  const turno = lerTurnoEstados((await searchParams).turno);
  const existe = await estadosExiste(turno);

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-4 p-4">
      <h1 className="sr-only">Como votou cada estado</h1>
      <SeletorTurnoEstados turno={turno} />
      {existe ? (
        <QuadroEstados turno={turno} />
      ) : (
        <Card>
          <CardContent>
            <p>
              O relatório do {turno}º turno ainda não foi gravado. Rode {comandoEstados(turno)}.
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
