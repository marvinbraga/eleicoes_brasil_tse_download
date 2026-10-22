import { DicaGrafico } from "@/components/relatorios/dica-grafico";
import { formatarInteiro } from "@/lib/fracao";
import {
  ALTURA_BARRA,
  CABECA,
  ESQUERDA,
  LARGURA_PESO,
  PASSO,
  TONS,
  X_PESO,
  X_PESO_ROTULO,
  layoutPerfis,
  resumoPerfis,
  type BarraMistura,
  type BlocoPerfil,
  type EntradaPerfis,
} from "@/lib/grafico-perfis";

const ID_TITULO = "grafico-perfis-titulo";
const ID_DESC = "grafico-perfis-desc";
const RECUO = (PASSO - ALTURA_BARRA) / 2;

export function GraficoPerfis({ partidos, grupos }: EntradaPerfis) {
  const entrada = { partidos, grupos };
  const layout = layoutPerfis(entrada);
  if (layout === null) {
    return null;
  }
  const { largura, altura, blocos, tetoTexto } = layout;
  const legenda = blocos[0]?.barras ?? [];
  return (
    <figure className="folha-quieta flex flex-col gap-3">
      <DicaGrafico>
        <div className="overflow-x-auto">
          <svg
            viewBox={`0 0 ${largura} ${altura}`}
            className="w-full min-w-[560px]"
            role="img"
            aria-labelledby={`${ID_TITULO} ${ID_DESC}`}
          >
            <title id={ID_TITULO}>Mistura típica e peso de cada grupo</title>
            <desc id={ID_DESC}>{resumoPerfis(entrada)}</desc>
            <g fontSize={11} fill="currentColor" className="text-muted-foreground" pointerEvents="none">
              <text x={ESQUERDA} y={14}>{`Mistura típica (votos válidos), de 0 a ${tetoTexto}`}</text>
              <text x={X_PESO_ROTULO} y={14}>
                Parte do total, de 0 a 100%
              </text>
            </g>
            {blocos.map((bloco) => (
              <Bloco key={bloco.numero} bloco={bloco} />
            ))}
          </svg>
        </div>
      </DicaGrafico>
      <figcaption className="text-sm text-muted-foreground">
        <p>
          Cada bloco é um grupo. À esquerda, quanto cada partido costuma ter dos votos válidos num
          município do grupo. À direita, quanto do total de municípios e de votantes cai no grupo.
        </p>
        <p className="mt-2 inline-flex flex-wrap items-center gap-x-4 gap-y-1">
          {legenda.map((barra) => (
            <span key={barra.chave} className="inline-flex items-center gap-2">
              <svg width={12} height={12} viewBox="0 0 12 12" aria-hidden="true">
                <rect x={0.5} y={0.5} width={11} height={11} rx={2} style={estilo(barra)} />
              </svg>
              {barra.titulo}
            </span>
          ))}
        </p>
      </figcaption>
    </figure>
  );
}

function Bloco({ bloco }: { bloco: BlocoPerfil }) {
  const topoBarras = bloco.y + CABECA;
  const fimBarras = topoBarras + bloco.barras.length * PASSO;
  const [municipios, votantes] = bloco.peso;
  return (
    <g>
      {bloco.barras.map((barra) => (
        <rect
          key={`alvo-${barra.chave}`}
          x={0}
          y={barra.y}
          width={X_PESO_ROTULO - 8}
          height={PASSO}
          fill="transparent"
          className="hover:fill-muted/60"
          data-dica-titulo={`Grupo ${bloco.numero} · ${barra.titulo}`}
          data-dica-linhas={`${barra.texto} dos votos válidos`}
        />
      ))}
      {municipios && votantes ? (
        <rect
          x={X_PESO_ROTULO - 4}
          y={municipios.y}
          width={X_PESO + LARGURA_PESO + 60 - X_PESO_ROTULO}
          height={2 * PASSO}
          fill="transparent"
          className="hover:fill-muted/60"
          data-dica-titulo={`Grupo ${bloco.numero}`}
          data-dica-linhas={`${formatarInteiro(municipios.contagem)} municípios (${municipios.texto})\n${formatarInteiro(votantes.contagem)} votantes (${votantes.texto})`}
        />
      ) : null}
      <g pointerEvents="none">
        <text
          x={0}
          y={bloco.y + 14}
          fontSize={13}
          fontWeight={600}
          fill="currentColor"
          className="text-foreground"
        >
          {`Grupo ${bloco.numero}`}
        </text>
        <line
          x1={ESQUERDA}
          x2={ESQUERDA}
          y1={topoBarras}
          y2={fimBarras}
          stroke="var(--border)"
          strokeWidth={1}
        />
        {bloco.barras.map((barra) => (
          <g key={barra.chave}>
            <text
              x={ESQUERDA - 8}
              y={barra.y + PASSO / 2}
              dy="0.35em"
              textAnchor="end"
              fontSize={11}
              fill="currentColor"
              className={barra.tom === null ? "text-muted-foreground" : "text-foreground"}
            >
              {barra.rotulo}
            </text>
            {barra.largura > 0 ? (
              <rect
                x={ESQUERDA}
                y={barra.y + RECUO}
                width={Math.max(barra.largura, 1.5)}
                height={ALTURA_BARRA}
                rx={2}
                style={estilo(barra)}
              />
            ) : null}
            <text
              x={ESQUERDA + barra.largura + 4}
              y={barra.y + PASSO / 2}
              dy="0.35em"
              fontSize={11}
              fill="currentColor"
              className="text-foreground tabular-nums"
            >
              {barra.texto}
            </text>
          </g>
        ))}
        {bloco.peso.map((peso) => (
          <g key={peso.rotulo}>
            <text
              x={X_PESO_ROTULO}
              y={peso.y + PASSO / 2}
              dy="0.35em"
              fontSize={11}
              fill="currentColor"
              className="text-muted-foreground"
            >
              {peso.rotulo}
            </text>
            <rect
              x={X_PESO}
              y={peso.y + RECUO}
              width={LARGURA_PESO}
              height={ALTURA_BARRA}
              rx={2}
              fill="var(--muted)"
            />
            {peso.largura > 0 ? (
              <rect
                x={X_PESO}
                y={peso.y + RECUO}
                width={Math.max(peso.largura, 1.5)}
                height={ALTURA_BARRA}
                rx={2}
                fill="var(--tinta-quente)"
              />
            ) : null}
            <text
              x={X_PESO + LARGURA_PESO + 6}
              y={peso.y + PASSO / 2}
              dy="0.35em"
              fontSize={11}
              fill="currentColor"
              className="text-foreground tabular-nums"
            >
              {peso.texto}
            </text>
          </g>
        ))}
      </g>
    </g>
  );
}

function estilo(barra: Pick<BarraMistura, "tom">) {
  if (barra.tom === null) {
    return {
      fill: "color-mix(in oklab, var(--muted-foreground) 35%, var(--tinta-frio))",
      stroke: "var(--muted-foreground)",
      strokeWidth: 1,
    };
  }
  const tom = TONS[barra.tom];
  return {
    fill:
      tom === undefined
        ? "color-mix(in oklab, var(--tinta-quente) 50%, var(--tinta-frio))"
        : `color-mix(in oklab, var(--tinta-quente) ${tom}%, var(--foreground))`,
    stroke: "var(--tinta-quente)",
    strokeWidth: 1,
  };
}
