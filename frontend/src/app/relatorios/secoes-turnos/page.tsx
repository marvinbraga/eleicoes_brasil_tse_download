import type { Metadata } from "next";

import { Card, CardContent } from "@/components/ui/card";
import { COMANDO_SECOES_TURNOS, secoesTurnosExiste } from "@/lib/secoes-turnos";

export const metadata: Metadata = {
  title: "Seções 1º × 2º turno",
};

export const dynamic = "force-dynamic";

export default async function SecoesTurnosPage() {
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
