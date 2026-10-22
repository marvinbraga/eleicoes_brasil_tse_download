import "./verticalizacao.css";

import type { Metadata } from "next";
import { Suspense } from "react";

import { DadosVerticalizacao } from "@/components/relatorios/dados-verticalizacao";
import { EsqueletoDados, EsqueletoFiltros } from "@/components/relatorios/esqueleto-relatorio";
import { FerramentasApresentacao } from "@/components/relatorios/ferramentas-apresentacao";
import { FiltrosRelatorio } from "@/components/relatorios/filtros-relatorio";
import {
  consultaPedida,
  escolher,
  lerAno,
  lerTurno,
  lerUf,
  type ConsultaRelatorio,
  type ValorConsulta,
} from "@/lib/eleicoes";
import { CARGOS_VERTICAIS, type CargoVertical } from "@/lib/verticalizacao";

export const metadata: Metadata = {
  title: "Verticalização",
};

export const maxDuration = 600;

const CHAVES_FILTRO = ["ano", "turno", "uf"];
const MAXIMO_PARTIDO = 99;

type ConsultaVerticalizacao = ConsultaRelatorio & {
  partido?: ValorConsulta;
  x?: ValorConsulta;
  y?: ValorConsulta;
};

export default function VerticalizacaoPage({
  searchParams,
}: {
  searchParams: Promise<ConsultaVerticalizacao>;
}) {
  return (
    <div className="leitura flex min-h-0 flex-1 flex-col gap-6 overflow-auto p-4 md:p-6">
      <h1 className="leitura-titulo text-3xl">Verticalização</h1>
      <FerramentasApresentacao />
      <Suspense fallback={<EsqueletoFiltros chaves={CHAVES_FILTRO} />}>
        <FiltrosComConsulta searchParams={searchParams} />
      </Suspense>
      <Suspense fallback={<EsqueletoDados />}>
        <DadosComConsulta searchParams={searchParams} />
      </Suspense>
    </div>
  );
}

async function FiltrosComConsulta({
  searchParams,
}: {
  searchParams: Promise<ConsultaVerticalizacao>;
}) {
  const consulta = await searchParams;
  return (
    <FiltrosRelatorio
      ano={lerAno(consulta.ano)}
      turno={lerTurno(consulta.turno)}
      uf={lerUf(consulta.uf)}
    />
  );
}

async function DadosComConsulta({
  searchParams,
}: {
  searchParams: Promise<ConsultaVerticalizacao>;
}) {
  const consulta = await searchParams;
  if (!consultaPedida(consulta.consultar)) {
    return (
      <p className="text-sm text-muted-foreground">
        Selecione os filtros e clique em Consultar.
      </p>
    );
  }
  return (
    <DadosVerticalizacao
      ano={lerAno(consulta.ano)}
      turno={lerTurno(consulta.turno)}
      uf={lerUf(consulta.uf)}
      partido={lerPartido(consulta.partido)}
      cargoX={lerCargo(consulta.x, "deputadoFederal")}
      cargoY={lerCargo(consulta.y, "governador")}
    />
  );
}

function lerPartido(valor: ValorConsulta): string | null {
  const bruto = Array.isArray(valor) ? valor[0] : valor;
  if (bruto === undefined || !/^\d{1,2}$/.test(bruto)) {
    return null;
  }
  const numero = Number(bruto);
  return numero <= MAXIMO_PARTIDO ? String(numero) : null;
}

function lerCargo(valor: ValorConsulta, padrao: CargoVertical): CargoVertical {
  return escolher(valor, CARGOS_VERTICAIS, padrao);
}
