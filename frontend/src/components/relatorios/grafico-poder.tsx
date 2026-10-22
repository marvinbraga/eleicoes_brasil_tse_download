import { DicaGrafico } from "@/components/relatorios/dica-grafico";
import {
  ALTURA_BARRA,
  ALTURA_LINHA,
  ESQUERDA,
  LARGURA,
  layoutBarras,
  resumoBarras,
  type ItemBarra,
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
  if (layout === null) {
    return null;
  }
  const { largura, altura, barras } = layout;
  const idTitulo = `${id}-titulo`;
  const idDesc = `${id}-desc`;
  return (
    <figure className="folha-quieta flex flex-col gap-3">
      <figcaption>
        <p className="font-medium text-foreground">{titulo}</p>
        <p className="mt-1 text-sm text-muted-foreground">{legenda}</p>
      </figcaption>
      <DicaGrafico>
        <div className="overflow-x-auto">
          <svg
            viewBox={`0 0 ${largura} ${altura}`}
            className="w-full min-w-[480px]"
            role="img"
            aria-labelledby={`${idTitulo} ${idDesc}`}
          >
            <title id={idTitulo}>{titulo}</title>
            <desc id={idDesc}>{resumoBarras(introducao, itens)}</desc>
            {barras.map((barra) => (
              <rect
                key={`alvo-${barra.chave}`}
                x={0}
                y={barra.y - ALTURA_LINHA / 2}
                width={LARGURA}
                height={ALTURA_LINHA}
                fill="transparent"
                className="hover:fill-muted/60"
                data-dica-titulo={barra.rotulo}
                data-dica-linhas={`${barra.texto}\n${barra.detalhe}`}
              />
            ))}
            <g pointerEvents="none">
              <line
                x1={ESQUERDA}
                x2={ESQUERDA}
                y1={0}
                y2={altura}
                stroke="var(--border)"
                strokeWidth={1}
              />
              {barras.map((barra) => (
                <g key={barra.chave}>
                  <text
                    x={ESQUERDA - 8}
                    y={barra.y}
                    dy="0.35em"
                    textAnchor="end"
                    fontSize={12}
                    fill="currentColor"
                    className="text-foreground"
                  >
                    {barra.rotulo}
                  </text>
                  <rect
                    x={ESQUERDA}
                    y={barra.y - ALTURA_BARRA / 2}
                    width={barra.largura}
                    height={ALTURA_BARRA}
                    rx={2}
                    fill="var(--tinta-quente)"
                    fillOpacity={barra.chave === "outros" ? 0.5 : 1}
                  />
                  <text
                    x={ESQUERDA + barra.largura + 6}
                    y={barra.y}
                    dy="0.35em"
                    fontSize={12}
                    fill="currentColor"
                    className="text-foreground tabular-nums"
                  >
                    {barra.texto}
                  </text>
                </g>
              ))}
            </g>
          </svg>
        </div>
      </DicaGrafico>
    </figure>
  );
}
