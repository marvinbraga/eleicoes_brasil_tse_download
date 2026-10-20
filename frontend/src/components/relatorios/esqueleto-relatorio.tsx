import { Skeleton } from "@/components/ui/skeleton";

const FILTROS_BASE = ["ano", "turno", "uf"] as const;
const FILTROS_PODER = ["cargo", "nivel"] as const;

export function EsqueletoFiltros({
  comCargo = false,
  chaves,
}: {
  comCargo?: boolean;
  chaves?: readonly string[];
}) {
  const lista = chaves ?? (comCargo ? [...FILTROS_BASE, ...FILTROS_PODER] : FILTROS_BASE);
  return (
    <div className="flex flex-wrap items-end gap-3" aria-busy="true">
      <p className="sr-only">Carregando filtros…</p>
      {lista.map((chave) => (
        <div key={chave} className="flex min-w-36 flex-1 basis-0 flex-col gap-1.5">
          <Skeleton className="h-5 w-16" />
          <Skeleton className="h-8 w-full" />
        </div>
      ))}
      <div className="flex min-w-36 flex-1 basis-0 flex-col gap-1.5">
        <span className="h-5" aria-hidden="true" />
        <Skeleton className="h-8 w-full" />
      </div>
    </div>
  );
}

export function EsqueletoDados() {
  return (
    <div
      className="flex min-h-48 items-center justify-center gap-3 text-sm text-muted-foreground"
      role="status"
      aria-busy="true"
    >
      <span
        className="girar inline-block size-5 shrink-0"
        style={{
          borderRadius: "9999px",
          border: "2px solid currentColor",
          borderTopColor: "transparent",
        }}
        aria-hidden="true"
      />
      Consultando o relatório…
    </div>
  );
}
