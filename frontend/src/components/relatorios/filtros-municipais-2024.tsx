"use client";

import { useState, useTransition } from "react";
import { usePathname, useRouter } from "next/navigation";

import { FiltroSelect } from "@/components/filtros/filtro-select";
import { Button } from "@/components/ui/button";
import { UFS, UF_TODAS } from "@/lib/eleicoes";

type FiltrosMunicipais2024Props = {
  uf: string;
};

// Não há eleição municipal no DF nem no exterior (D15).
const OPCOES_UF = [
  { value: UF_TODAS, label: "Todas" },
  ...UFS.filter((uf) => uf.value !== "DF" && uf.value !== "ZZ"),
];

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

export function FiltrosMunicipais2024({ uf }: FiltrosMunicipais2024Props) {
  const router = useRouter();
  const pathname = usePathname();
  const [pendente, iniciarConsulta] = useTransition();
  const [ufAtual, setUfAtual] = useState(uf);
  const [origem, setOrigem] = useState(uf);
  if (uf !== origem) {
    setOrigem(uf);
    setUfAtual(uf);
  }

  function consultar() {
    const params = new URLSearchParams();
    params.set("uf", ufAtual);
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
          id="uf"
          label="UF"
          value={ufAtual}
          options={OPCOES_UF}
          onChange={setUfAtual}
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
