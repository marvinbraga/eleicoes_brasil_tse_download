"use client";

import { useState, useTransition } from "react";
import { usePathname, useRouter } from "next/navigation";

import { FiltroSelect } from "@/components/filtros/filtro-select";
import { Button } from "@/components/ui/button";
import {
  ANOS,
  CARGOS_PODER,
  TURNOS,
  escolher,
  lerAno,
  lerTurno,
  type Ano,
  type CargoPoder,
  type Turno,
} from "@/lib/eleicoes";

type FiltrosForcaProps = {
  ano: Ano;
  turno: Turno;
  cargo: CargoPoder;
};

const OPCOES_ANO = ANOS.map((ano) => ({ value: ano, label: ano }));
const OPCOES_TURNO = TURNOS.map((turno) => ({ value: turno, label: turno }));
const VALORES_CARGO: readonly CargoPoder[] = CARGOS_PODER.map((cargo) => cargo.value);

function Spinner() {
  return (
    <span
      className="girar inline-block size-4 shrink-0"
      style={{
        borderRadius: "9999px",
        border: "2px solid currentColor",
        borderTopColor: "transparent",
      }}
      aria-hidden="true"
    />
  );
}

export function FiltrosForca({ ano, turno, cargo }: FiltrosForcaProps) {
  const router = useRouter();
  const pathname = usePathname();
  const [pendente, iniciarConsulta] = useTransition();
  const [anoAtual, setAnoAtual] = useState(ano);
  const [turnoAtual, setTurnoAtual] = useState(turno);
  const [cargoAtual, setCargoAtual] = useState(cargo);
  const [origem, setOrigem] = useState({ ano, turno, cargo });
  if (ano !== origem.ano || turno !== origem.turno || cargo !== origem.cargo) {
    setOrigem({ ano, turno, cargo });
    setAnoAtual(ano);
    setTurnoAtual(turno);
    setCargoAtual(cargo);
  }

  function consultar() {
    const params = new URLSearchParams({
      ano: anoAtual,
      turno: turnoAtual,
      cargo: cargoAtual,
      consultar: "1",
    });
    iniciarConsulta(() => {
      router.replace(`${pathname}?${params.toString()}`, { scroll: false });
    });
  }

  return (
    <form
      className="flex flex-col gap-3"
      aria-label="Filtros do relatório"
      onSubmit={(event) => {
        event.preventDefault();
        consultar();
      }}
    >
      <div className="flex flex-wrap items-end gap-3">
        <FiltroSelect
          id="ano"
          label="Ano"
          value={anoAtual}
          options={OPCOES_ANO}
          onChange={(valor) => setAnoAtual(lerAno(valor))}
        />
        <FiltroSelect
          id="turno"
          label="Turno"
          value={turnoAtual}
          options={OPCOES_TURNO}
          onChange={(valor) => setTurnoAtual(lerTurno(valor))}
        />
        <FiltroSelect
          id="cargo"
          label="Cargo de referência"
          value={cargoAtual}
          options={CARGOS_PODER}
          onChange={(valor) => setCargoAtual(escolher(valor, VALORES_CARGO, "deputadoEstadual"))}
        />
        <div className="flex shrink-0 items-end gap-2">
          <div className="flex flex-col gap-1.5">
            <span className="block h-5" aria-hidden="true" />
            <Button type="submit" disabled={pendente} aria-busy={pendente} className="h-8">
              {pendente ? <Spinner /> : null}
              {pendente ? "Consultando" : "Consultar"}
            </Button>
          </div>
        </div>
      </div>
      {pendente ? (
        <p className="flex items-center gap-2 text-sm text-muted-foreground" role="status">
          <Spinner />
          Consultando o relatório…
        </p>
      ) : null}
    </form>
  );
}
