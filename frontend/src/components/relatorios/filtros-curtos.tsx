"use client";

import { useState, useTransition } from "react";
import { usePathname, useRouter } from "next/navigation";

import { FiltroSelect } from "@/components/filtros/filtro-select";
import { Button } from "@/components/ui/button";
import {
  ANOS,
  CARGOS_PERFIL,
  GRUPOS_PERFIL,
  TURNOS,
  lerAno,
  lerCargoPerfil,
  lerGruposPerfil,
  lerTurno,
  type Ano,
  type CargoPerfil,
  type GruposPerfil,
  type Turno,
} from "@/lib/eleicoes";

type FiltrosCurtosProps = {
  ano: Ano;
  turno: Turno;
  cargo?: CargoPerfil;
  grupos?: GruposPerfil;
};

const OPCOES_ANO = ANOS.map((ano) => ({ value: ano, label: ano }));
const OPCOES_TURNO = TURNOS.map((turno) => ({ value: turno, label: turno }));

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

export function FiltrosCurtos({ ano, turno, cargo, grupos }: FiltrosCurtosProps) {
  const router = useRouter();
  const pathname = usePathname();
  const [pendente, iniciarConsulta] = useTransition();
  const [anoAtual, setAnoAtual] = useState(ano);
  const [turnoAtual, setTurnoAtual] = useState(turno);
  const [cargoAtual, setCargoAtual] = useState(cargo);
  const [gruposAtual, setGruposAtual] = useState(grupos);
  const [origem, setOrigem] = useState({ ano, turno, cargo, grupos });
  if (
    ano !== origem.ano ||
    turno !== origem.turno ||
    cargo !== origem.cargo ||
    grupos !== origem.grupos
  ) {
    setOrigem({ ano, turno, cargo, grupos });
    setAnoAtual(ano);
    setTurnoAtual(turno);
    setCargoAtual(cargo);
    setGruposAtual(grupos);
  }

  function consultar() {
    const params = new URLSearchParams();
    params.set("ano", anoAtual);
    params.set("turno", turnoAtual);
    if (cargoAtual !== undefined) {
      params.set("cargo", cargoAtual);
    }
    if (gruposAtual !== undefined) {
      params.set("grupos", gruposAtual);
    }
    params.set("consultar", "1");
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
        {cargoAtual !== undefined ? (
          <FiltroSelect
            id="cargo"
            label="Cargo"
            value={cargoAtual}
            options={CARGOS_PERFIL}
            onChange={(valor) => setCargoAtual(lerCargoPerfil(valor))}
          />
        ) : null}
        {gruposAtual !== undefined ? (
          <FiltroSelect
            id="grupos"
            label="Grupos"
            value={gruposAtual}
            options={GRUPOS_PERFIL}
            onChange={(valor) => setGruposAtual(lerGruposPerfil(valor))}
          />
        ) : null}
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
