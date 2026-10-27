"use client";

import { useTheme } from "next-themes";

import { Skeleton } from "@/components/ui/skeleton";
import { useMounted } from "@/hooks/use-mounted";
import type { Turno } from "@/lib/eleicoes";

export function QuadroEstados({ turno }: { turno: Turno }) {
  const { resolvedTheme } = useTheme();
  const montado = useMounted();

  if (!montado) {
    return <Skeleton className="min-h-0 w-full flex-1" />;
  }

  const tema = resolvedTheme === "light" ? "light" : "dark";
  return (
    <iframe
      key={`${tema}-${turno}`}
      title={`Como votou cada estado no ${turno}º turno`}
      src={`/relatorios/estados/arquivo?turno=${turno}&tema=${tema}`}
      className="min-h-0 w-full flex-1 rounded-lg border border-border bg-background"
    />
  );
}
