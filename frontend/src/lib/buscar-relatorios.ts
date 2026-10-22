import { urlApi } from "@/lib/eleicoes";
import {
  lerCadeiras,
  lerClasseGovernador,
  lerGrade,
  lerRelatorioCruzado,
  lerRelatorioPerfis,
  RespostaInvalidaError,
  type GradeRelatorio,
  type RelatorioClasseGovernador,
  type RelatorioCruzado,
  type RelatorioPerfis,
  type SimulacaoCadeiras,
} from "@/lib/relatorios";

export type Resultado<T> =
  | { ok: true; dados: T }
  | { ok: false; detalhe: string };

// A agregação dos boletins pode demorar; não abortar antes de 120 segundos.
const ESPERA_MS = 600_000;

export function buscarCruzamento(
  ano: string,
  turno: string,
  uf: string,
): Promise<Resultado<RelatorioCruzado>> {
  const params = new URLSearchParams({ ano, turno, uf });
  return buscar(
    "/relatorios/dados/presidente-governador",
    params,
    lerRelatorioCruzado,
  );
}

export function buscarGrade(
  ano: string,
  turno: string,
  uf: string,
  cargo: string,
  nivel: string,
): Promise<Resultado<GradeRelatorio>> {
  const params = new URLSearchParams({
    ano,
    turno,
    uf,
    cargo,
    nivel,
    somente_gravado: "true",
  });
  return buscar("/relatorios/dados/grade", params, lerGrade);
}

export function buscarPerfis(
  ano: string,
  turno: string,
  cargo: string,
  grupos: string,
): Promise<Resultado<RelatorioPerfis>> {
  const params = new URLSearchParams({ ano, turno, cargo, grupos });
  return buscar("/relatorios/dados/perfis", params, lerRelatorioPerfis);
}

export function buscarClasseGovernador(
  ano: string,
  turno: string,
): Promise<Resultado<RelatorioClasseGovernador>> {
  const params = new URLSearchParams({ ano, turno });
  return buscar("/relatorios/dados/classe-governador", params, lerClasseGovernador);
}

export function buscarCadeiras(
  ano: string,
  turno: string,
): Promise<Resultado<SimulacaoCadeiras>> {
  const params = new URLSearchParams({ ano, turno });
  return buscar("/relatorios/dados/cadeiras", params, lerCadeiras);
}

async function buscar<T>(
  caminho: string,
  params: URLSearchParams,
  ler: (valor: unknown) => T,
): Promise<Resultado<T>> {
  try {
    const json = await buscarJson(caminho, params);
    return { ok: true, dados: ler(json) };
  } catch (erro) {
    return { ok: false, detalhe: mensagemDeErro(erro) };
  }
}

async function buscarJson(
  caminho: string,
  params: URLSearchParams,
): Promise<unknown> {
  const url = `${urlApi()}${caminho}?${params.toString()}`;
  let resposta: Response;
  try {
    resposta = await fetch(url, {
      cache: "no-store",
      signal: AbortSignal.timeout(ESPERA_MS),
    });
  } catch (erro) {
    if (consultaInterrompida(erro)) {
      throw new Error("A consulta passou de 10 minutos e foi interrompida.");
    }
    throw new Error("Não foi possível contactar a API.");
  }
  if (!resposta.ok) {
    throw new Error(await detalheHttp(resposta));
  }
  try {
    const corpo: unknown = await resposta.json();
    return corpo;
  } catch {
    throw new Error("A API não devolveu JSON.");
  }
}

async function detalheHttp(resposta: Response): Promise<string> {
  const fallback = `A API respondeu com status ${resposta.status}.`;
  const texto = await resposta.text();
  if (texto.trim().length === 0) {
    return fallback;
  }
  try {
    const corpo: unknown = JSON.parse(texto);
    return detalheJson(corpo) ?? fallback;
  } catch {
    return fallback;
  }
}

function ehRegistro(valor: unknown): valor is Record<string, unknown> {
  return typeof valor === "object" && valor !== null && !Array.isArray(valor);
}

function detalheJson(corpo: unknown): string | null {
  if (!ehRegistro(corpo) || !("detail" in corpo)) {
    return null;
  }
  const detalhe = corpo.detail;
  if (typeof detalhe === "string" && detalhe.trim().length > 0) {
    return detalhe;
  }
  if (!Array.isArray(detalhe)) {
    return null;
  }
  const mensagens = detalhe.flatMap((item) => {
    if (typeof item === "string" && item.trim().length > 0) {
      return [item];
    }
    if (ehRegistro(item) && typeof item.msg === "string" && item.msg.trim().length > 0) {
      return [item.msg];
    }
    return [];
  });
  return mensagens.length > 0 ? mensagens.join(" ") : null;
}

function consultaInterrompida(erro: unknown): boolean {
  if (!(erro instanceof Error)) {
    return false;
  }
  return (
    erro.name === "TimeoutError" ||
    erro.name === "AbortError" ||
    erro.name === "HeadersTimeoutError" ||
    erro.message.includes("Headers Timeout")
  );
}

function mensagemDeErro(erro: unknown): string {
  if (erro instanceof RespostaInvalidaError) {
    return erro.message;
  }
  if (erro instanceof Error && erro.message.trim().length > 0) {
    return erro.message;
  }
  return "Não foi possível carregar o relatório.";
}
