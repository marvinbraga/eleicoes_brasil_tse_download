import Link from "next/link";

import { buttonVariants } from "@/components/ui/button";
import { TURNOS, type Turno } from "@/lib/eleicoes";

export function SeletorTurnoEstados({ turno }: { turno: Turno }) {
  return (
    <nav aria-label="Turno do relatório" className="flex flex-wrap items-center gap-2">
      {TURNOS.map((opcao) => {
        const atual = opcao === turno;
        return (
          <Link
            key={opcao}
            href={`/relatorios/estados?turno=${opcao}`}
            scroll={false}
            aria-current={atual ? "page" : undefined}
            className={buttonVariants({ variant: atual ? "default" : "outline", size: "sm" })}
          >
            {opcao}º turno
          </Link>
        );
      })}
      {turno === "1" ? (
        <span className="text-sm text-muted-foreground">
          No 1º turno, só os dois mais votados do país; os demais ficam fora das barras.
        </span>
      ) : null}
    </nav>
  );
}
