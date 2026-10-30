import type { Metadata } from "next";
import { connection } from "next/server";
import { Suspense } from "react";

import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { COMANDO_PL_POUCO_PT_MUITO, plPoucoPtMuitoExiste } from "@/lib/pl-pouco-pt-muito";

export const metadata: Metadata = {
  title: "PL com poucos e PT com muitos",
};

export default function PlPoucoPtMuitoPage() {
  return (
    <Suspense fallback={<RelatorioFallback />}>
      <RelatorioConteudo />
    </Suspense>
  );
}

function RelatorioFallback() {
  return (
    <div className="flex min-h-0 flex-1 flex-col gap-4 p-4" aria-busy="true">
      <p className="sr-only">Carregando relatório…</p>
      <Skeleton className="min-h-0 w-full flex-1" />
    </div>
  );
}

async function RelatorioConteudo() {
  await connection();
  const existe = await plPoucoPtMuitoExiste();

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-4 p-4">
      <h1 className="sr-only">PL com poucos e PT com muitos</h1>
      {existe ? (
        <iframe
          title="PL com poucos votos e PT com muitos"
          src="/relatorios/pl-pouco-pt-muito/arquivo"
          className="min-h-0 w-full flex-1 rounded-lg border border-border bg-background"
        />
      ) : (
        <Card>
          <CardContent>
            <p>O relatório ainda não foi gravado. Rode {COMANDO_PL_POUCO_PT_MUITO}.</p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
