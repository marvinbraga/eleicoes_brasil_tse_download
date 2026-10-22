import type { Metadata } from "next";
import { Suspense } from "react";

import { DadosMarca } from "@/components/relatorios/dados-marca";
import { EsqueletoDados } from "@/components/relatorios/esqueleto-relatorio";
import { FerramentasApresentacao } from "@/components/relatorios/ferramentas-apresentacao";

export const metadata: Metadata = {
  title: "Força da marca",
};

export const maxDuration = 600;

export default function MarcaPage() {
  return (
    <div className="leitura flex min-h-0 flex-1 flex-col gap-6 overflow-auto p-4 md:p-6">
      <h1 className="leitura-titulo text-3xl">Força da marca</h1>
      <p className="text-sm text-muted-foreground">
        Eleição geral de 2026, 1º turno. Deputado federal e deputado estadual.
      </p>
      <FerramentasApresentacao />
      <Suspense fallback={<EsqueletoDados />}>
        <DadosMarca />
      </Suspense>
    </div>
  );
}
