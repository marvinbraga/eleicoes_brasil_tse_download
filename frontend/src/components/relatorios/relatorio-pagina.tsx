import { Suspense } from "react";

import { DadosPoder } from "@/components/relatorios/dados-poder";
import { DadosPresidenteGovernador } from "@/components/relatorios/dados-presidente-governador";
import {
  EsqueletoDados,
  EsqueletoFiltros,
} from "@/components/relatorios/esqueleto-relatorio";
import { FerramentasApresentacao } from "@/components/relatorios/ferramentas-apresentacao";
import { FiltrosRelatorio } from "@/components/relatorios/filtros-relatorio";
import {
  consultaPedida,
  lerAno,
  lerCargoPoder,
  lerNivel,
  lerTurno,
  lerUf,
  type ConsultaRelatorio,
} from "@/lib/eleicoes";

type TipoRelatorio = "presidente-governador" | "poder";

const TITULOS: Record<TipoRelatorio, string> = {
  "presidente-governador": "Relatório de presidente e governador",
  poder: "Relatório de poder",
};

type RelatorioPaginaProps = {
  tipo: TipoRelatorio;
  searchParams: Promise<ConsultaRelatorio>;
};

export function RelatorioPagina({ tipo, searchParams }: RelatorioPaginaProps) {
  return (
    <div className="leitura flex min-h-0 flex-1 flex-col gap-6 overflow-auto p-4 md:p-6">
      <h1 className="leitura-titulo text-3xl">{TITULOS[tipo]}</h1>
      <FerramentasApresentacao />
      <Suspense fallback={<EsqueletoFiltros comCargo={tipo === "poder"} />}>
        <FiltrosComConsulta tipo={tipo} searchParams={searchParams} />
      </Suspense>
      <Suspense fallback={<EsqueletoDados />}>
        <DadosComConsulta tipo={tipo} searchParams={searchParams} />
      </Suspense>
    </div>
  );
}

async function FiltrosComConsulta({ tipo, searchParams }: RelatorioPaginaProps) {
  const consulta = await searchParams;
  const ano = lerAno(consulta.ano);
  const turno = lerTurno(consulta.turno);
  const uf = lerUf(consulta.uf);
  return (
    <FiltrosRelatorio
      ano={ano}
      turno={turno}
      uf={uf}
      cargo={tipo === "poder" ? lerCargoPoder(consulta.cargo) : undefined}
      nivel={tipo === "poder" ? lerNivel(consulta.nivel) : undefined}
    />
  );
}

async function DadosComConsulta({ tipo, searchParams }: RelatorioPaginaProps) {
  const consulta = await searchParams;
  if (!consultaPedida(consulta.consultar)) {
    return (
      <p className="text-sm text-muted-foreground">
        Selecione os filtros e clique em Consultar.
      </p>
    );
  }
  const ano = lerAno(consulta.ano);
  const turno = lerTurno(consulta.turno);
  const uf = lerUf(consulta.uf);
  if (tipo === "poder") {
    return (
      <DadosPoder
        ano={ano}
        turno={turno}
        uf={uf}
        cargo={lerCargoPoder(consulta.cargo)}
        nivel={lerNivel(consulta.nivel)}
      />
    );
  }
  return <DadosPresidenteGovernador ano={ano} turno={turno} uf={uf} />;
}
