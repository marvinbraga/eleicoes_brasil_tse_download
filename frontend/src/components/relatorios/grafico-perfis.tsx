import { DicaGrafico } from "@/components/relatorios/dica-grafico";
import { formatarInteiro } from "@/lib/fracao";
import {
  MEDIDAS_ESTREITO,
  TONS,
  layoutPerfis,
  resumoPerfis,
  type BarraMistura,
  type BlocoPerfil,
  type EntradaPerfis,
  type LayoutPerfis,
  type MedidasPerfis,
} from "@/lib/grafico-perfis";

const ID_TITULO = "grafico-perfis-titulo";
const ID_DESC = "grafico-perfis-desc";

export function GraficoPerfis({ partidos, grupos }: EntradaPerfis) {
  const entrada = { partidos, grupos };
  const layout = layoutPerfis(entrada);
  const estreito = layoutPerfis(entrada, MEDIDAS_ESTREITO);
  if (layout === null || estreito === null) {
    return null;
  }
  const resumo = resumoPerfis(entrada);
  const legenda = layout.blocos[0]?.barras ?? [];
  return (
    <figure className="folha-quieta flex flex-col gap-3">
      <DicaGrafico>
        <div className="hidden overflow-x-auto sm:block">
          <Desenho layout={layout} resumo={resumo} sufixo="" className="w-full min-w-[560px]" />
        </div>
        <Desenho layout={estreito} resumo={resumo} sufixo="-estreito" className="w-full sm:hidden" />
      </DicaGrafico>
      <figcaption className="text-sm text-muted-foreground">
        <p>
          Cada bloco é um grupo. As barras de partido mostram quanto cada um costuma ter dos votos
          válidos num município do grupo. Municípios e Votantes mostram quanto do total cai no grupo.
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

type DesenhoProps = {
  layout: LayoutPerfis;
  resumo: string;
  sufixo: string;
  className: string;
};

function Desenho({ layout, resumo, sufixo, className }: DesenhoProps) {
  const { medidas, largura, altura, blocos, tetoTexto } = layout;
  const [mistura, peso] = medidas.cabecalhos;
  const idTitulo = `${ID_TITULO}${sufixo}`;
  const idDesc = `${ID_DESC}${sufixo}`;
  return (
    <svg
      viewBox={`0 0 ${largura} ${altura}`}
      className={className}
      role="img"
      aria-labelledby={`${idTitulo} ${idDesc}`}
    >
      <title id={idTitulo}>Mistura típica e peso de cada grupo</title>
      <desc id={idDesc}>{resumo}</desc>
      <g fontSize={medidas.fonte} fill="currentColor" className="text-muted-foreground" pointerEvents="none">
        <text x={mistura.x} y={mistura.y}>{`Mistura típica (votos válidos), de 0 a ${tetoTexto}`}</text>
        <text x={peso.x} y={peso.y}>
          Parte do total, de 0 a 100%
        </text>
      </g>
      {blocos.map((bloco) => (
        <Bloco key={bloco.numero} bloco={bloco} medidas={medidas} />
      ))}
    </svg>
  );
}

function Bloco({ bloco, medidas }: { bloco: BlocoPerfil; medidas: MedidasPerfis }) {
  const { esquerda, cabeca, passo, alturaBarra, xPeso, xPesoRotulo, larguraPeso, fonte } = medidas;
  const recuo = (passo - alturaBarra) / 2;
  const topoBarras = bloco.y + cabeca;
  const fimBarras = topoBarras + bloco.barras.length * passo;
  const [municipios, votantes] = bloco.peso;
  return (
    <g>
      {bloco.barras.map((barra) => (
        <rect
          key={`alvo-${barra.chave}`}
          x={0}
          y={barra.y}
          width={medidas.alvoMistura}
          height={passo}
          fill="transparent"
          className="hover:fill-muted/60"
          data-dica-titulo={`Grupo ${bloco.numero} · ${barra.titulo}`}
          data-dica-linhas={`${barra.texto} dos votos válidos`}
        />
      ))}
      {municipios && votantes ? (
        <rect
          x={medidas.alvoPeso.x}
          y={municipios.y}
          width={medidas.alvoPeso.largura}
          height={2 * passo}
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
          fontSize={medidas.fonteGrupo}
          fontWeight={600}
          fill="currentColor"
          className="text-foreground"
        >
          {`Grupo ${bloco.numero}`}
        </text>
        <line
          x1={esquerda}
          x2={esquerda}
          y1={topoBarras}
          y2={fimBarras}
          stroke="var(--border)"
          strokeWidth={1}
        />
        {bloco.barras.map((barra) => (
          <g key={barra.chave}>
            <text
              x={esquerda - 8}
              y={barra.y + passo / 2}
              dy="0.35em"
              textAnchor="end"
              fontSize={fonte}
              fill="currentColor"
              className={barra.tom === null ? "text-muted-foreground" : "text-foreground"}
            >
              {barra.rotulo}
            </text>
            {barra.largura > 0 ? (
              <rect
                x={esquerda}
                y={barra.y + recuo}
                width={Math.max(barra.largura, 1.5)}
                height={alturaBarra}
                rx={2}
                style={estilo(barra)}
              />
            ) : null}
            <text
              x={esquerda + barra.largura + 4}
              y={barra.y + passo / 2}
              dy="0.35em"
              fontSize={fonte}
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
              x={xPesoRotulo}
              y={peso.y + passo / 2}
              dy="0.35em"
              fontSize={fonte}
              fill="currentColor"
              className="text-muted-foreground"
            >
              {peso.rotulo}
            </text>
            <rect
              x={xPeso}
              y={peso.y + recuo}
              width={larguraPeso}
              height={alturaBarra}
              rx={2}
              fill="var(--muted)"
            />
            {peso.largura > 0 ? (
              <rect
                x={xPeso}
                y={peso.y + recuo}
                width={Math.max(peso.largura, 1.5)}
                height={alturaBarra}
                rx={2}
                fill="var(--tinta-quente)"
              />
            ) : null}
            <text
              x={xPeso + larguraPeso + 6}
              y={peso.y + passo / 2}
              dy="0.35em"
              fontSize={fonte}
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
