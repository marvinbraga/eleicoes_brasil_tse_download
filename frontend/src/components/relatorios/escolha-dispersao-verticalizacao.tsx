"use client";

import { useState, useTransition } from "react";
import { usePathname, useRouter } from "next/navigation";

import { FiltroSelect } from "@/components/filtros/filtro-select";
import { Button } from "@/components/ui/button";
import { rotuloPartido } from "@/lib/partidos";
import {
  CARGOS_VERTICAIS,
  ROTULO_CARGO,
  ehCargoVertical,
  type CargoVertical,
} from "@/lib/verticalizacao";

type EscolhaDispersaoVerticalizacaoProps = {
  ano: string;
  turno: string;
  uf: string;
  partidos: readonly number[];
  partido: number;
  cargoX: CargoVertical;
  cargoY: CargoVertical;
};

const OPCOES_CARGO = CARGOS_VERTICAIS.map((cargo) => ({ value: cargo, label: ROTULO_CARGO[cargo] }));

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

export function EscolhaDispersaoVerticalizacao({
  ano,
  turno,
  uf,
  partidos,
  partido,
  cargoX,
  cargoY,
}: EscolhaDispersaoVerticalizacaoProps) {
  const router = useRouter();
  const pathname = usePathname();
  const [pendente, iniciar] = useTransition();
  const [partidoAtual, setPartidoAtual] = useState(String(partido));
  const [xAtual, setXAtual] = useState<CargoVertical>(cargoX);
  const [yAtual, setYAtual] = useState<CargoVertical>(cargoY);
  const [origem, setOrigem] = useState({ partido, cargoX, cargoY });
  if (partido !== origem.partido || cargoX !== origem.cargoX || cargoY !== origem.cargoY) {
    setOrigem({ partido, cargoX, cargoY });
    setPartidoAtual(String(partido));
    setXAtual(cargoX);
    setYAtual(cargoY);
  }
  const iguais = xAtual === yAtual;
  const numeros = partidos.includes(partido) ? partidos : [partido, ...partidos];
  const opcoesPartido = numeros.map((numero) => ({
    value: String(numero),
    label: rotuloPartido(numero),
  }));

  function mostrar() {
    if (iguais) {
      return;
    }
    const params = new URLSearchParams({ ano, turno, uf, consultar: "1" });
    params.set("partido", partidoAtual);
    params.set("x", xAtual);
    params.set("y", yAtual);
    iniciar(() => {
      router.replace(`${pathname}?${params.toString()}`, { scroll: false });
    });
  }

  return (
    <form
      className="flex flex-col gap-2"
      aria-label="Escolha da dispersão"
      onSubmit={(evento) => {
        evento.preventDefault();
        mostrar();
      }}
    >
      <div className="flex flex-wrap items-end gap-3">
        <FiltroSelect
          id="vz-partido"
          label="Partido"
          value={partidoAtual}
          options={opcoesPartido}
          onChange={setPartidoAtual}
        />
        <FiltroSelect
          id="vz-x"
          label="Eixo x"
          value={xAtual}
          options={OPCOES_CARGO}
          onChange={(valor) => {
            if (ehCargoVertical(valor)) setXAtual(valor);
          }}
        />
        <FiltroSelect
          id="vz-y"
          label="Eixo y"
          value={yAtual}
          options={OPCOES_CARGO}
          onChange={(valor) => {
            if (ehCargoVertical(valor)) setYAtual(valor);
          }}
        />
        <div className="flex shrink-0 flex-col gap-1.5">
          <span className="block h-5" aria-hidden="true" />
          <Button type="submit" disabled={pendente || iguais} aria-busy={pendente} className="h-8">
            {pendente ? <Spinner /> : null}
            Mostrar
          </Button>
        </div>
      </div>
      {iguais ? (
        <p className="text-sm text-muted-foreground" role="status">
          Escolha dois cargos diferentes.
        </p>
      ) : null}
    </form>
  );
}
