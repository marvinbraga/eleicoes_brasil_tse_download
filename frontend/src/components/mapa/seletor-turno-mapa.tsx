import Link from "next/link";

import { buttonVariants } from "@/components/ui/button";
import { TURNOS, type CargoMapa, type Turno } from "@/lib/eleicoes";

const COMPARATIVOS: readonly CargoMapa[] = ["turnos", "turnosgov"];

function destino(cargo: CargoMapa, turno: Turno): string {
  // O 2º turno não tem os comparativos: quem estava neles vai para presidente.
  const visao = turno === "2" && COMPARATIVOS.includes(cargo) ? "presidente" : cargo;
  const params = new URLSearchParams({ cargo: visao });
  if (turno !== "1") {
    params.set("turno", turno);
  }
  return `/mapa?${params.toString()}`;
}

export function SeletorTurnoMapa({ cargo, turno }: { cargo: CargoMapa; turno: Turno }) {
  return (
    <nav aria-label="Turno do mapa" className="flex flex-wrap items-center gap-2">
      {TURNOS.map((opcao) => {
        const atual = opcao === turno;
        return (
          <Link
            key={opcao}
            href={destino(cargo, opcao)}
            scroll={false}
            aria-current={atual ? "page" : undefined}
            className={buttonVariants({ variant: atual ? "default" : "outline", size: "sm" })}
          >
            {opcao}º turno
          </Link>
        );
      })}
      {COMPARATIVOS.includes(cargo) ? (
        <span className="text-sm text-muted-foreground">
          O comparativo usa os dois turnos.
        </span>
      ) : null}
      {turno === "2" ? (
        <span className="text-sm text-muted-foreground">
          Parcial: o mapa e o total marcado como Brasil só somam as UFs com 2º turno já
          importado. O comparativo 1º × 2º turno lista quais são.
        </span>
      ) : null}
    </nav>
  );
}
