import type { Metadata } from "next";
import { connection } from "next/server";
import { Suspense } from "react";

import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { COMANDO_ORIGEM_VOTOS, origemVotosExiste } from "@/lib/origem-votos";

export const metadata: Metadata = {
  title: "De onde vieram os votos",
};

export default function OrigemVotosPage() {
  return (
    <Suspense fallback={<OrigemFallback />}>
      <OrigemConteudo />
    </Suspense>
  );
}

function OrigemFallback() {
  return (
    <div className="flex min-h-0 flex-1 flex-col gap-4 p-4" aria-busy="true">
      <p className="sr-only">Carregando relatório…</p>
      <Skeleton className="min-h-0 w-full flex-1" />
    </div>
  );
}

async function OrigemConteudo() {
  await connection();
  const existe = await origemVotosExiste();

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-4 p-4">
      <h1 className="sr-only">De onde vieram os votos</h1>
      {existe ? (
        <iframe
          title="De onde vieram os votos"
          src="/relatorios/origem-votos/arquivo"
          className="min-h-0 w-full flex-1 rounded-lg border border-border bg-background"
        />
      ) : (
        <Card>
          <CardContent>
            <p>
              O relatório ainda não foi gravado. Rode {COMANDO_ORIGEM_VOTOS}.
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
