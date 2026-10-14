"use client";

import { useTheme } from "next-themes";
import { usePathname, useRouter } from "next/navigation";

import { FiltroSelect } from "@/components/filtros/filtro-select";
import { Skeleton } from "@/components/ui/skeleton";
import { useMounted } from "@/hooks/use-mounted";
import { CARGOS_MAPA, type CargoMapa } from "@/lib/eleicoes";

type MapaFiltroProps = {
  cargo: CargoMapa;
};

export function MapaFiltro({ cargo }: MapaFiltroProps) {
  const router = useRouter();
  const pathname = usePathname();

  return (
    <div role="group" aria-label="Filtro do mapa">
      <FiltroSelect
        id="cargo-mapa"
        label="Cargo"
        value={cargo}
        options={CARGOS_MAPA}
        onChange={(valor) => {
          const params = new URLSearchParams();
          params.set("cargo", valor);
          router.replace(`${pathname}?${params.toString()}`, { scroll: false });
        }}
      />
    </div>
  );
}

export function MapaQuadro({ cargo }: { cargo: CargoMapa }) {
  const { resolvedTheme } = useTheme();
  const montado = useMounted();

  if (!montado) {
    return <Skeleton className="min-h-0 w-full flex-1" />;
  }

  const tema = resolvedTheme === "light" ? "light" : "dark";
  return (
    <iframe
      key={tema}
      title="Mapa eleitoral"
      src={`/mapa/arquivo?cargo=${cargo}&tema=${tema}`}
      className="min-h-0 w-full flex-1 rounded-lg border border-border bg-background"
    />
  );
}
