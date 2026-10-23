import type { CSSProperties } from "react";

import { DicaGrafico } from "@/components/relatorios/dica-grafico";
import { TextoGrafico } from "@/components/relatorios/texto-grafico";
import {
  corFatia,
  corR,
  resumoMatriz,
  textoCelula,
  textosMatriz,
  type CelulaMatriz,
  type LayoutMatriz,
} from "@/lib/grafico-verticalizacao";

type Escala = "fatia" | "r";

type MatrizVerticalizacaoProps = {
  id: string;
  titulo: string;
  legenda: string;
  layout: LayoutMatriz;
  estreito: LayoutMatriz;
  escala: Escala;
};

const AMOSTRAS_FATIA = [
  { faixa: 0, rotulo: "até 5%" },
  { faixa: 1, rotulo: "5–10%" },
  { faixa: 2, rotulo: "10–20%" },
  { faixa: 3, rotulo: "20–35%" },
  { faixa: 4, rotulo: "35% ou mais" },
];

const AMOSTRAS_R = [
  { faixa: -4, rotulo: "−1 a −0,8" },
  { faixa: -3, rotulo: "−0,8 a −0,6" },
  { faixa: -2, rotulo: "−0,6 a −0,4" },
  { faixa: -1, rotulo: "−0,4 a −0,2" },
  { faixa: 0, rotulo: "−0,2 a 0,2" },
  { faixa: 1, rotulo: "0,2 a 0,4" },
  { faixa: 2, rotulo: "0,4 a 0,6" },
  { faixa: 3, rotulo: "0,6 a 0,8" },
  { faixa: 4, rotulo: "0,8 a 1" },
];

const HACHURA: CSSProperties = {
  backgroundImage:
    "repeating-linear-gradient(45deg, var(--vz-hachura) 0 2px, var(--card) 2px 5px)",
};

export function MatrizVerticalizacao({
  id,
  titulo,
  legenda,
  layout,
  estreito,
  escala,
}: MatrizVerticalizacaoProps) {
  const resumo = resumoMatriz(layout);
  return (
    <figure className="folha-quieta flex flex-col gap-3">
      <figcaption>
        <p className="font-medium text-foreground">{titulo}</p>
        <p className="mt-1 text-sm text-muted-foreground">{legenda}</p>
      </figcaption>
      <DicaGrafico>
        <div className="hidden overflow-x-auto sm:block">
          <Desenho
            layout={layout}
            id={id}
            sufixo=""
            titulo={titulo}
            resumo={resumo}
            escala={escala}
            className="w-full min-w-[560px]"
          />
        </div>
        <Desenho
          layout={estreito}
          id={id}
          sufixo="-estreito"
          titulo={titulo}
          resumo={resumo}
          escala={escala}
          className="w-full sm:hidden"
        />
      </DicaGrafico>
      {/* Um div em volta: ".folha-quieta > .flex" (globals.css) achataria a legenda. */}
      <div>
        <Legenda escala={escala} />
      </div>
    </figure>
  );
}

function Legenda({ escala }: { escala: Escala }) {
  const amostras = escala === "fatia" ? AMOSTRAS_FATIA : AMOSTRAS_R;
  const cor = escala === "fatia" ? corFatia : corR;
  return (
    <ul className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground" aria-label="Legenda">
      {amostras.map((amostra) => (
        <li key={amostra.rotulo} className="flex items-center gap-1.5">
          <span
            aria-hidden="true"
            className="inline-block size-3 rounded-[2px]"
            style={{ background: cor(amostra.faixa).fundo }}
          />
          {amostra.rotulo}
        </li>
      ))}
      <li className="flex items-center gap-1.5">
        <span aria-hidden="true" className="inline-block size-3 rounded-[2px] border" style={HACHURA} />
        {escala === "fatia" ? "não concorreu" : "sem medida"}
      </li>
      {escala === "fatia" ? (
        <li className="flex items-center gap-1.5">
          <span
            aria-hidden="true"
            className="inline-block size-3 rounded-[2px] border border-dashed border-border"
          />
          sem eleição gravada
        </li>
      ) : null}
    </ul>
  );
}

type DesenhoProps = {
  layout: LayoutMatriz;
  id: string;
  sufixo: string;
  titulo: string;
  resumo: string;
  escala: Escala;
  className: string;
};

function Desenho({ layout, id, sufixo, titulo, resumo, escala, className }: DesenhoProps) {
  const { medidas, largura, altura, celulas } = layout;
  const idTitulo = `${id}-titulo${sufixo}`;
  const idDesc = `${id}-desc${sufixo}`;
  const idHachura = `${id}-hachura${sufixo}`;
  return (
    <svg
      viewBox={`0 0 ${largura} ${altura}`}
      className={className}
      role="img"
      aria-labelledby={`${idTitulo} ${idDesc}`}
    >
      <title id={idTitulo}>{titulo}</title>
      <desc id={idDesc}>{resumo}</desc>
      <defs>
        <pattern
          id={idHachura}
          patternUnits="userSpaceOnUse"
          width={6}
          height={6}
          patternTransform="rotate(45)"
        >
          <rect width={6} height={6} fill="var(--card)" />
          <line x1={0} y1={0} x2={0} y2={6} stroke="var(--vz-hachura)" strokeWidth={2} />
        </pattern>
      </defs>
      <g pointerEvents="none">
        {textosMatriz(layout).map((texto) => (
          <TextoGrafico key={texto.chave} texto={texto} />
        ))}
      </g>
      {celulas.map((celula) => (
        <Celula
          key={celula.chave}
          celula={celula}
          escala={escala}
          hachura={idHachura}
          fonte={medidas.fonte}
        />
      ))}
    </svg>
  );
}

function Celula({
  celula,
  escala,
  hachura,
  fonte,
}: {
  celula: CelulaMatriz;
  escala: Escala;
  hachura: string;
  fonte: number;
}) {
  const cor = celula.faixa === null ? null : escala === "fatia" ? corFatia(celula.faixa) : corR(celula.faixa);
  const texto = textoCelula(celula, fonte);
  const dica = {
    "data-dica-titulo": celula.dicaTitulo,
    "data-dica-linhas": celula.dicaLinhas.join("\n"),
  };
  return (
    <g {...dica}>
      {celula.semEleicao ? (
        <rect
          x={celula.x + 0.5}
          y={celula.y + 0.5}
          width={celula.largura - 1}
          height={celula.altura - 1}
          rx={2}
          fill="transparent"
          stroke="var(--border)"
          strokeDasharray="3 2"
        />
      ) : (
        <rect
          x={celula.x}
          y={celula.y}
          width={celula.largura}
          height={celula.altura}
          rx={2}
          fill={cor === null ? `url(#${hachura})` : cor.fundo}
        />
      )}
      <text
        x={texto.x}
        y={texto.y}
        dy="0.35em"
        textAnchor="middle"
        fontSize={texto.fonte}
        pointerEvents="none"
        fill={cor === null ? "currentColor" : cor.tinta}
        className={cor === null ? "text-muted-foreground tabular-nums" : "tabular-nums"}
      >
        {texto.texto}
      </text>
    </g>
  );
}
