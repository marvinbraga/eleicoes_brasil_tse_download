"use client";

import { useEffect, useRef, useState } from "react";
import { useTheme } from "next-themes";
import { usePathname, useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useMounted } from "@/hooks/use-mounted";
import {
  CARGO_DO_ARQUIVO_DO_MAPA,
  CARGOS_MAPA,
  type CargoMapa,
  type Turno,
} from "@/lib/eleicoes";

const VISAO_NO_ENDERECO = /(?:^|[#&])visao=([a-z]+)/;

function visaoDoQuadro(janela: Window): CargoMapa | null {
  const achado = VISAO_NO_ENDERECO.exec(janela.location.hash);
  const visao = achado?.[1];
  return CARGOS_MAPA.some((item) => item.value === visao) ? (visao as CargoMapa) : null;
}

export function MapaQuadro({ cargo, turno }: { cargo: CargoMapa; turno: Turno }) {
  const { resolvedTheme } = useTheme();
  const montado = useMounted();
  const router = useRouter();
  const pathname = usePathname();
  const dialogo = useRef<HTMLDialogElement>(null);
  const botao = useRef<HTMLButtonElement>(null);
  const quadro = useRef<HTMLIFrameElement>(null);
  const jaAbriu = useRef(false);
  const [ampliado, setAmpliado] = useState(false);
  const [carregado, setCarregado] = useState(0);

  useEffect(() => {
    const janela = quadro.current?.contentWindow;
    if (!janela || carregado === 0) {
      return;
    }
    const sincronizar = () => {
      const visao = visaoDoQuadro(janela);
      if (!visao || visao === cargo) {
        return;
      }
      const params = new URLSearchParams();
      params.set("cargo", visao);
      if (turno !== "1") {
        params.set("turno", turno);
      }
      router.replace(`${pathname}?${params.toString()}`, { scroll: false });
    };
    janela.addEventListener("hashchange", sincronizar);
    return () => janela.removeEventListener("hashchange", sincronizar);
  }, [cargo, carregado, pathname, router, turno]);

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
        ref={quadro}
        key={`${tema}-${turno}`}
        title="Mapa eleitoral"
        src={`/mapa/arquivo?cargo=${CARGO_DO_ARQUIVO_DO_MAPA}&turno=${turno}&tema=${tema}#visao=${cargo}`}
        onLoad={() => setCarregado((vezes) => vezes + 1)}
        className="min-h-0 w-full flex-1 rounded-lg border border-border bg-background"
      />
    </dialog>
  );
}
