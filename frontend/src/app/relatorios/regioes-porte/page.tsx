import type { Metadata } from "next";
import { connection } from "next/server";
import { Suspense } from "react";

import { QuadroRegioesPorte } from "@/components/relatorios/quadro-regioes-porte";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { COMANDO_REGIOES_PORTE, regioesPorteExiste } from "@/lib/regioes-porte";

export const metadata: Metadata = {
  title: "Regiões e porte",
};

export default function RegioesPortePage() {
  return (
    <Suspense fallback={<RegioesPorteFallback />}>
      <RegioesPorteConteudo />
    </Suspense>
  );
}

function RegioesPorteFallback() {
  return (
    <div className="flex min-h-0 flex-1 flex-col gap-4 p-4" aria-busy="true">
      <p className="sr-only">Carregando relatório…</p>
      <Skeleton className="min-h-0 w-full flex-1" />
    </div>
  );
}

async function RegioesPorteConteudo() {
  await connection();
  const existe = await regioesPorteExiste();

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-4 p-4">
      <h1 className="sr-only">Regiões e porte dos municípios</h1>
      {existe ? (
        <QuadroRegioesPorte />
      ) : (
        <Card>
          <CardContent>
            <p>O relatório ainda não foi gravado. Rode {COMANDO_REGIOES_PORTE}.</p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
