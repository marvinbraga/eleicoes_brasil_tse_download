import { NextResponse, type NextRequest } from "next/server";

import {
  ANOS,
  CARGOS_PODER,
  TURNOS,
  UF_TODAS,
  UFS,
  ufDeConsulta,
  urlApi,
  type Ano,
  type CargoPoder,
  type Turno,
  type UfFiltro,
} from "@/lib/eleicoes";

export const maxDuration = 600;

const ESPERA_MS = 600_000;

const CARGOS_GRAVADOS = new Set<CargoPoder>(["presidente", "governador", "senador"]);

const UFS_FILTRO = new Set<UfFiltro>([UF_TODAS, ...UFS.map((uf) => uf.value)]);

export async function GET(request: NextRequest) {
  const consulta = lerConsulta(request.nextUrl.searchParams);
  if (!consulta.ok) {
    return texto(consulta.detalhe, 400);
  }
  if (!CARGOS_GRAVADOS.has(consulta.cargo)) {
    return texto("O HTML desse cargo ainda não está gravado.", 409);
  }

  const uf = ufDeConsulta(consulta.uf);
  const params = new URLSearchParams({
    ano: consulta.ano,
    turno: consulta.turno,
    uf,
    cargo: consulta.cargo,
  });
  let resposta: Response;
  try {
    resposta = await fetch(`${urlApi()}/relatorios/poder?${params.toString()}`, {
      cache: "no-store",
      signal: AbortSignal.timeout(ESPERA_MS),
    });
  } catch {
    return texto("Não foi possível exportar o HTML.", 502);
  }
  if (!resposta.ok) {
    return texto("Não foi possível exportar o HTML.", 502);
  }

  const html = await resposta.text();
  const nome = `${uf.toLowerCase()}-${consulta.ano}-turno-${consulta.turno}-${consulta.cargo}.html`;
  return new NextResponse(html, {
    status: 200,
    headers: {
      "Content-Type": "text/html; charset=utf-8",
      "Content-Disposition": `attachment; filename="${nome}"`,
      "Cache-Control": "no-store",
    },
  });
}

type ConsultaHtml =
  | { ok: true; ano: Ano; turno: Turno; uf: UfFiltro; cargo: CargoPoder }
  | { ok: false; detalhe: string };

function lerConsulta(params: URLSearchParams): ConsultaHtml {
  const ano = params.get("ano") ?? "";
  const turno = params.get("turno") ?? "";
  const uf = params.get("uf") ?? "";
  const cargo = params.get("cargo") ?? "";
  if (!contem(ANOS, ano)) {
    return { ok: false, detalhe: "Ano inválido." };
  }
  if (!contem(TURNOS, turno)) {
    return { ok: false, detalhe: "Turno inválido." };
  }
  if (!UFS_FILTRO.has(uf as UfFiltro)) {
    return { ok: false, detalhe: "UF inválida." };
  }
  if (!CARGOS_PODER.some((item) => item.value === cargo)) {
    return { ok: false, detalhe: "Cargo inválido." };
  }
  return {
    ok: true,
    ano,
    turno,
    uf: uf as UfFiltro,
    cargo: cargo as CargoPoder,
  };
}

function contem<T extends string>(valores: readonly T[], valor: string): valor is T {
  return valores.some((item) => item === valor);
}

function texto(mensagem: string, status: number) {
  return new NextResponse(mensagem, {
    status,
    headers: { "Content-Type": "text/plain; charset=utf-8" },
  });
}
