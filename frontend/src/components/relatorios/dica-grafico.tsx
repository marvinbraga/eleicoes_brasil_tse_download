"use client";

import { useState, type PointerEvent, type ReactNode } from "react";

type Dica = {
  uf: string;
  acerto: string;
  municipios: string;
  x: number;
  y: number;
  aEsquerda: boolean;
};

export function DicaGrafico({ children }: { children: ReactNode }) {
  const [dica, setDica] = useState<Dica | null>(null);

  function mostrar(evento: PointerEvent<HTMLDivElement>) {
    const alvo = evento.target instanceof Element ? evento.target.closest("[data-dica-uf]") : null;
    if (alvo === null) {
      setDica(null);
      return;
    }
    const caixa = evento.currentTarget.getBoundingClientRect();
    const x = evento.clientX - caixa.left;
    setDica({
      uf: alvo.getAttribute("data-dica-uf") ?? "",
      acerto: alvo.getAttribute("data-dica-acerto") ?? "",
      municipios: alvo.getAttribute("data-dica-municipios") ?? "",
      x,
      y: evento.clientY - caixa.top,
      aEsquerda: x > caixa.width / 2,
    });
  }

  return (
    <div
      className="relative"
      onPointerMove={mostrar}
      onPointerDown={mostrar}
      onPointerLeave={() => setDica(null)}
    >
      {children}
      {dica ? (
        <div
          className="pointer-events-none absolute z-10 rounded-md border bg-popover px-2 py-1 text-xs text-popover-foreground shadow-sm"
          style={{
            top: dica.y + 12,
            ...(dica.aEsquerda ? { right: `calc(100% - ${dica.x - 12}px)` } : { left: dica.x + 12 }),
          }}
        >
          <div className="font-semibold">{dica.uf}</div>
          <div className="tabular-nums">{dica.acerto}</div>
          <div className="tabular-nums">
            {dica.municipios} {dica.municipios === "1" ? "município" : "municípios"}
          </div>
        </div>
      ) : null}
    </div>
  );
}
