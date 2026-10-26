import type { Metadata } from "next";
import { connection } from "next/server";
import { Suspense } from "react";

import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { COMANDO_SECOES_TURNOS, secoesTurnosExiste } from "@/lib/secoes-turnos";

export const metadata: Metadata = {
  title: "Seções 1º × 2º turno",
};

export default function SecoesTurnosPage() {
  return (
    <Suspense fallback={<SecoesFallback />}>
      <SecoesConteudo />
    </Suspense>
  );
}

function SecoesFallback() {
  return (
    <div className="flex min-h-0 flex-1 flex-col gap-4 p-4" aria-busy="true">
      <p className="sr-only">Carregando relatório…</p>
      <Skeleton className="min-h-0 w-full flex-1" />
    </div>
  );
}

async function SecoesConteudo() {
  await connection();
  const existe = await secoesTurnosExiste();

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-4 p-4">
      <h1 className="sr-only">Seções 1º × 2º turno</h1>
      {existe ? (
        <iframe
          title="Seções no 1º × 2º turno"
          src="/relatorios/secoes-turnos/arquivo"
          className="min-h-0 w-full flex-1 rounded-lg border border-border bg-background"
        />
      ) : (
        <Card>
          <CardContent>
            <p>O relatório ainda não foi gravado. Rode {COMANDO_SECOES_TURNOS}.</p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
