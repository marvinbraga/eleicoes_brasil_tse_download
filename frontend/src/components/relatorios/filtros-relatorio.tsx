"use client";

import { useState, useTransition } from "react";
import { usePathname, useRouter } from "next/navigation";

import { FiltroSelect } from "@/components/filtros/filtro-select";
import { Button } from "@/components/ui/button";
import {
  ANOS,
  CARGOS_PODER,
  NIVEIS,
  OPCOES_UF,
  TURNOS,
  type Ano,
  type CargoPoder,
  type Nivel,
  type Turno,
  type UfFiltro,
} from "@/lib/eleicoes";

type FiltrosRelatorioProps = {
  ano: Ano;
  turno: Turno;
  uf: UfFiltro;
  cargo?: CargoPoder;
  nivel?: Nivel;
};

const OPCOES_ANO = ANOS.map((ano) => ({ value: ano, label: ano }));
const OPCOES_TURNO = TURNOS.map((turno) => ({ value: turno, label: turno }));
const CARGOS_COM_HTML = new Set<CargoPoder>(["presidente", "governador", "senador"]);

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

export function FiltrosRelatorio({
  ano,
  turno,
  uf,
  cargo,
  nivel,
}: FiltrosRelatorioProps) {
  const router = useRouter();
  const pathname = usePathname();
  const [pendente, iniciarConsulta] = useTransition();
  const [anoAtual, setAnoAtual] = useState(ano);
  const [turnoAtual, setTurnoAtual] = useState(turno);
  const [ufAtual, setUfAtual] = useState(uf);
  const [cargoAtual, setCargoAtual] = useState(cargo);
  const [nivelAtual, setNivelAtual] = useState(nivel);
  const [exportando, setExportando] = useState(false);
  const [falhaExportacao, setFalhaExportacao] = useState<string | null>(null);

  const [origem, setOrigem] = useState({ ano, turno, uf, cargo, nivel });
  if (
    ano !== origem.ano ||
    turno !== origem.turno ||
    uf !== origem.uf ||
    cargo !== origem.cargo ||
    nivel !== origem.nivel
  ) {
    setOrigem({ ano, turno, uf, cargo, nivel });
    setAnoAtual(ano);
    setTurnoAtual(turno);
    setUfAtual(uf);
    setCargoAtual(cargo);
    setNivelAtual(nivel);
    setFalhaExportacao(null);
  }

  const htmlGravado = cargoAtual !== undefined && CARGOS_COM_HTML.has(cargoAtual);

  async function exportarHtml() {
    if (cargoAtual === undefined || !CARGOS_COM_HTML.has(cargoAtual) || exportando) {
      return;
    }
    setExportando(true);
    setFalhaExportacao(null);
    const params = new URLSearchParams({
      ano: anoAtual,
      turno: turnoAtual,
      uf: ufAtual,
      cargo: cargoAtual,
    });
    try {
      const resposta = await fetch(`/relatorios/poder/html?${params.toString()}`, {
        cache: "no-store",
      });
      if (!resposta.ok) {
        const detalhe = (await resposta.text()).trim();
        setFalhaExportacao(detalhe || "Não foi possível exportar o HTML.");
        return;
      }
      const arquivo = await resposta.blob();
      const reserva = nomeReserva(ufAtual, anoAtual, turnoAtual, cargoAtual);
      baixar(arquivo, nomeDoAnexo(resposta, reserva));
    } catch {
      setFalhaExportacao("Não foi possível exportar o HTML.");
    } finally {
      setExportando(false);
    }
  }

  function consultar() {
    const params = new URLSearchParams();
    params.set("ano", anoAtual);
    params.set("turno", turnoAtual);
    params.set("uf", ufAtual);
    if (cargoAtual !== undefined) {
      params.set("cargo", cargoAtual);
    }
    if (nivelAtual !== undefined) {
      params.set("nivel", nivelAtual);
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
        onChange={(valor) => setAnoAtual(valor as Ano)}
      />
      <FiltroSelect
        id="turno"
        label="Turno"
        value={turnoAtual}
        options={OPCOES_TURNO}
        onChange={(valor) => setTurnoAtual(valor as Turno)}
      />
      <FiltroSelect
        id="uf"
        label="UF"
        value={ufAtual}
        options={OPCOES_UF}
        onChange={(valor) => setUfAtual(valor as UfFiltro)}
      />
      {cargoAtual !== undefined ? (
        <FiltroSelect
          id="cargo"
          label="Cargo"
          value={cargoAtual}
          options={CARGOS_PODER}
          onChange={(valor) => setCargoAtual(valor as CargoPoder)}
        />
      ) : null}
      {nivelAtual !== undefined ? (
        <FiltroSelect
          id="nivel"
          label="Nível"
          value={nivelAtual}
          options={NIVEIS}
          onChange={(valor) => setNivelAtual(valor as Nivel)}
        />
      ) : null}
      <div className="flex shrink-0 items-end gap-2">
        <div className="flex flex-col gap-1.5">
          <span className="block h-5" aria-hidden="true" />
          <Button
            type="submit"
            disabled={pendente}
            aria-busy={pendente}
            className="h-8"
          >
            {pendente ? <Spinner /> : null}
            {pendente ? "Consultando" : "Consultar"}
          </Button>
        </div>
        {cargoAtual !== undefined ? (
          <div className="flex flex-col gap-1.5">
            <span className="block h-5" aria-hidden="true" />
            <Button
              type="button"
              variant="outline"
              disabled={!htmlGravado || exportando}
              aria-busy={exportando}
              className="h-8"
              onClick={() => {
                void exportarHtml();
              }}
            >
              {exportando ? <Spinner /> : null}
              {exportando ? "Exportando" : "Exportar HTML"}
            </Button>
          </div>
        ) : null}
      </div>
      </div>
      {cargoAtual !== undefined && !htmlGravado ? (
        <p className="text-sm text-muted-foreground">
          O HTML desse cargo ainda não está gravado.
        </p>
      ) : null}
      {falhaExportacao ? (
        <p className="text-sm text-destructive" role="alert">
          {falhaExportacao}
        </p>
      ) : null}
      {pendente ? (
        <p
          className="flex items-center gap-2 text-sm text-muted-foreground"
          role="status"
        >
          <Spinner />
          Consultando o relatório…
        </p>
      ) : null}
    </form>
  );
}

function nomeReserva(uf: string, ano: string, turno: string, cargo: string): string {
  return `${uf.toLowerCase()}-${ano}-turno-${turno}-${cargo}.html`;
}

function nomeDoAnexo(resposta: Response, reserva: string): string {
  const disposicao = resposta.headers.get("Content-Disposition") ?? "";
  const encontrado = /filename="([^"]+)"/.exec(disposicao);
  return encontrado?.[1] ?? reserva;
}

function baixar(arquivo: Blob, nome: string) {
  const url = URL.createObjectURL(arquivo);
  const link = document.createElement("a");
  link.href = url;
  link.download = nome;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
