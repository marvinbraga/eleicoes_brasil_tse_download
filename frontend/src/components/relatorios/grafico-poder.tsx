import { DicaGrafico } from "@/components/relatorios/dica-grafico";
import {
  MEDIDAS_ESTREITO,
  layoutBarras,
  resumoBarras,
  type ItemBarra,
  type LayoutBarras,
} from "@/lib/grafico-poder";

type GraficoPoderProps = {
  id: string;
  titulo: string;
  introducao: string;
  legenda: string;
  itens: readonly ItemBarra[];
};

export function GraficoPoder({ id, titulo, introducao, legenda, itens }: GraficoPoderProps) {
  const layout = layoutBarras(itens);
  const estreito = layoutBarras(itens, MEDIDAS_ESTREITO);
  if (layout === null || estreito === null) {
    return null;
  }
  const resumo = resumoBarras(introducao, itens);
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
            className="w-full min-w-[480px]"
          />
        </div>
        <Desenho
          layout={estreito}
          id={id}
          sufixo="-estreito"
          titulo={titulo}
          resumo={resumo}
          className="w-full sm:hidden"
        />
      </DicaGrafico>
    </figure>
  );
}

type DesenhoProps = {
  layout: LayoutBarras;
  id: string;
  sufixo: string;
  titulo: string;
  resumo: string;
  className: string;
};

function Desenho({ layout, id, sufixo, titulo, resumo, className }: DesenhoProps) {
  const { medidas, largura, altura, barras } = layout;
  const { esquerda, alturaLinha, alturaBarra, fonte } = medidas;
  const idTitulo = `${id}-titulo${sufixo}`;
  const idDesc = `${id}-desc${sufixo}`;
  return (
    <svg
      viewBox={`0 0 ${largura} ${altura}`}
      className={className}
      role="img"
      aria-labelledby={`${idTitulo} ${idDesc}`}
    >
      <title id={idTitulo}>{titulo}</title>
      <desc id={idDesc}>{resumo}</desc>
      {barras.map((barra) => (
        <rect
          key={`alvo-${barra.chave}`}
          x={0}
          y={barra.y - medidas.descida - alturaLinha / 2}
          width={largura}
          height={alturaLinha}
          fill="transparent"
          className="hover:fill-muted/60"
          data-dica-titulo={barra.rotulo}
          data-dica-linhas={`${barra.texto}\n${barra.detalhe}`}
        />
      ))}
      <g pointerEvents="none">
        <line
          x1={esquerda}
          x2={esquerda}
          y1={0}
          y2={altura}
          stroke="var(--border)"
          strokeWidth={1}
        />
        {barras.map((barra) => (
          <g key={barra.chave}>
            {medidas.rotuloAcima ? (
              <text
                x={esquerda + 4}
                y={barra.y - alturaBarra / 2 - 5}
                fontSize={fonte}
                fill="currentColor"
                className="text-foreground"
              >
                {barra.rotulo}
              </text>
            ) : (
              <text
                x={esquerda - 8}
                y={barra.y}
                dy="0.35em"
                textAnchor="end"
                fontSize={fonte}
                fill="currentColor"
                className="text-foreground"
              >
                {barra.rotulo}
              </text>
            )}
            <rect
              x={esquerda}
              y={barra.y - alturaBarra / 2}
              width={barra.largura}
              height={alturaBarra}
              rx={2}
              fill="var(--tinta-quente)"
              fillOpacity={barra.chave === "outros" ? 0.5 : 1}
            />
            <text
              x={esquerda + barra.largura + 6}
              y={barra.y}
              dy="0.35em"
              fontSize={fonte}
              fill="currentColor"
              className="text-foreground tabular-nums"
            >
              {barra.texto}
            </text>
          </g>
        ))}
      </g>
    </svg>
  );
}
