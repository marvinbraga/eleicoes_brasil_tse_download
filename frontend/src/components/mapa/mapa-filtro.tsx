"use client";

import { useEffect, useRef, useState } from "react";
import { useTheme } from "next-themes";
import { usePathname, useRouter } from "next/navigation";

import { FiltroSelect } from "@/components/filtros/filtro-select";
import { Button } from "@/components/ui/button";
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
  const dialogo = useRef<HTMLDialogElement>(null);
  const botao = useRef<HTMLButtonElement>(null);
  const jaAbriu = useRef(false);
  const [ampliado, setAmpliado] = useState(false);

  useEffect(() => {
    const quadro = dialogo.current;
    if (!quadro) {
      return;
    }
    if (ampliado) {
      jaAbriu.current = true;
      if (!quadro.open) {
        quadro.showModal();
      }
      return;
    }
    if (quadro.open) {
      quadro.close();
    }
    if (jaAbriu.current) {
      botao.current?.focus();
    }
  }, [ampliado]);

  useEffect(() => {
    if (!ampliado) {
      return;
    }
    const janela = dialogo.current?.querySelector("iframe")?.contentWindow;
    if (!janela) {
      return;
    }
    const fechar = (evento: KeyboardEvent) => {
      if (evento.key !== "Escape") {
        return;
      }
      evento.preventDefault();
      setAmpliado(false);
    };
    janela.addEventListener("keydown", fechar);
    return () => janela.removeEventListener("keydown", fechar);
  }, [ampliado]);

  if (!montado) {
    return <Skeleton className="min-h-0 w-full flex-1" />;
  }

  const tema = resolvedTheme === "light" ? "light" : "dark";
  return (
    <dialog
      ref={dialogo}
      aria-label="Mapa ampliado"
      onClose={() => setAmpliado(false)}
      className="m-0 w-full max-w-none border-0 bg-transparent p-0 backdrop:bg-background [&:not([open])]:relative [&:not([open])]:flex [&:not([open])]:min-h-0 [&:not([open])]:flex-1 [&:not([open])]:flex-col open:fixed open:inset-0 open:z-50 open:flex open:h-dvh open:max-h-none open:flex-col open:gap-2 open:bg-background open:p-3"
    >
      <Button
        ref={botao}
        type="button"
        variant="outline"
        size="sm"
        className={ampliado ? "self-end" : "mb-2 self-end"}
        aria-expanded={ampliado}
        onClick={() => setAmpliado((valor) => !valor)}
      >
        {ampliado ? "Fechar" : "Ampliar"}
      </Button>
      <iframe
        key={tema}
        title="Mapa eleitoral"
        src={`/mapa/arquivo?cargo=${cargo}&tema=${tema}`}
        className="min-h-0 w-full flex-1 rounded-lg border border-border bg-background"
      />
    </dialog>
  );
}
