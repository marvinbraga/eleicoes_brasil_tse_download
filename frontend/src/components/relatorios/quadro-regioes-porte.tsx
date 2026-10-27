"use client";

import { useTheme } from "next-themes";

import { Skeleton } from "@/components/ui/skeleton";
import { useMounted } from "@/hooks/use-mounted";

export function QuadroRegioesPorte() {
  const { resolvedTheme } = useTheme();
  const montado = useMounted();

  if (!montado) {
    return <Skeleton className="min-h-0 w-full flex-1" />;
  }

  const tema = resolvedTheme === "light" ? "light" : "dark";
  return (
    <iframe
      key={tema}
      title="Regiões e porte dos municípios no 1º × 2º turno"
      src={`/relatorios/regioes-porte/arquivo?tema=${tema}`}
      className="min-h-0 w-full flex-1 rounded-lg border border-border bg-background"
    />
  );
}
