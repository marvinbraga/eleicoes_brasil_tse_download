import { DicaGrafico } from "@/components/relatorios/dica-grafico";
import { formatarInteiro } from "@/lib/fracao";
import {
  ALTURA_BARRA,
  ALTURA_LINHA,
  BASE,
  ESQUERDA,
  TOPO,
  layoutAcertoClasse,
  resumoAcertoClasse,
  type EntradaGraficoClasse,
} from "@/lib/grafico-acerto-classe";

const ID_TITULO = "grafico-acerto-classe-titulo";
const ID_DESC = "grafico-acerto-classe-desc";

export function GraficoAcertoClasse({ linhas, acerto, base, baseLider }: EntradaGraficoClasse) {
  const entrada = { linhas, acerto, base, baseLider };
  const layout = layoutAcertoClasse(entrada);
  if (layout === null) {
    return null;
  }
  const { largura, altura, barras, referencia, marcas } = layout;
  const fimPlotagem = altura - BASE;
  return (
    <figure className="folha-quieta flex flex-col gap-3">
      <DicaGrafico>
        <div className="overflow-x-auto">
          <svg
            viewBox={`0 0 ${largura} ${altura}`}
            className="w-full min-w-[480px]"
            role="img"
            aria-labelledby={`${ID_TITULO} ${ID_DESC}`}
          >
            <title id={ID_TITULO}>Acerto por situação</title>
            <desc id={ID_DESC}>{resumoAcertoClasse(entrada)}</desc>
            {barras.map((barra) => (
              <rect
                key={`alvo-${barra.classe}`}
                x={0}
                y={barra.y + ALTURA_BARRA / 2 - ALTURA_LINHA / 2}
                width={largura}
                height={ALTURA_LINHA}
                fill="transparent"
                className="hover:fill-muted/60"
                data-dica-titulo={barra.rotulo}
                data-dica-linhas={`Acertou ${barra.acertoTexto}\n${formatarInteiro(barra.municipios)} ${barra.municipios === 1 ? "município" : "municípios"} nesta situação`}
              />
            ))}
            <g pointerEvents="none">
              {marcas.map((marca) => (
                <g key={marca.rotulo}>
                  <line
                    x1={marca.x}
                    x2={marca.x}
                    y1={TOPO}
                    y2={fimPlotagem}
                    stroke="var(--border)"
                    strokeWidth={1}
                  />
                  <text
                    x={marca.x}
                    y={fimPlotagem + 16}
                    textAnchor="middle"
                    fontSize={11}
                    fill="currentColor"
                    className="text-muted-foreground"
                  >
                    {marca.rotulo}
                  </text>
                </g>
              ))}
              {barras.map((barra) => (
                <g key={barra.classe}>
                  <text
                    x={ESQUERDA - 10}
                    y={barra.y + ALTURA_BARRA / 2 - 7}
                    dy="0.35em"
                    textAnchor="end"
                    fontSize={12}
                    fill="currentColor"
                    className="text-foreground"
                  >
                    {barra.rotulo}
                  </text>
                  <text
                    x={ESQUERDA - 10}
                    y={barra.y + ALTURA_BARRA / 2 + 8}
                    dy="0.35em"
                    textAnchor="end"
                    fontSize={11}
                    fill="currentColor"
                    className="text-muted-foreground"
                  >
                    {`${formatarInteiro(barra.municipios)} ${barra.municipios === 1 ? "município" : "municípios"}`}
                  </text>
                  <rect
                    x={barra.x}
                    y={barra.y}
                    width={barra.largura}
                    height={ALTURA_BARRA}
                    rx={2}
                    fill="var(--tinta-quente)"
                    stroke="var(--tinta-frio)"
                    strokeWidth={barra.largura > 0 ? 1.5 : 0}
                  />
                  <text
                    x={barra.x + barra.largura + 6}
                    y={barra.y + ALTURA_BARRA / 2}
                    dy="0.35em"
                    fontSize={12}
                    fill="currentColor"
                    className="text-foreground tabular-nums"
                  >
                    {barra.acertoTexto}
                  </text>
                </g>
              ))}
              {referencia ? (
                <g className="text-foreground">
                  <line
                    x1={referencia.x}
                    x2={referencia.x}
                    y1={TOPO - 12}
                    y2={fimPlotagem}
                    stroke="currentColor"
                    strokeWidth={1}
                  />
                  <text
                    x={referencia.ancora === "start" ? referencia.x + 4 : referencia.x - 4}
                    y={TOPO - 16}
                    textAnchor={referencia.ancora}
                    fontSize={11}
                    fill="currentColor"
                  >
                    {`Acerto geral ${referencia.valorTexto}`}
                  </text>
                </g>
              ) : null}
            </g>
          </svg>
        </div>
      </DicaGrafico>
      <figcaption className="text-sm text-muted-foreground">
        Cada barra é uma situação: dos municípios que eram de fato daquela situação, a parte que o
        modelo acertou. A linha marca o acerto geral, que é a média das barras pesada pelo número
        de municípios.
      </figcaption>
    </figure>
  );
}
