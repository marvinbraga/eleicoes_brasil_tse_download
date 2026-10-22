import { DicaGrafico } from "@/components/relatorios/dica-grafico";
import { formatarInteiro } from "@/lib/fracao";
import {
  MEDIDAS_ESTREITO,
  layoutAcertoClasse,
  resumoAcertoClasse,
  type EntradaGraficoClasse,
  type LayoutAcertoClasse,
} from "@/lib/grafico-acerto-classe";

const ID_TITULO = "grafico-acerto-classe-titulo";
const ID_DESC = "grafico-acerto-classe-desc";

export function GraficoAcertoClasse({ linhas, acerto, base, baseLider }: EntradaGraficoClasse) {
  const entrada = { linhas, acerto, base, baseLider };
  const layout = layoutAcertoClasse(entrada);
  const estreito = layoutAcertoClasse(entrada, MEDIDAS_ESTREITO);
  if (layout === null || estreito === null) {
    return null;
  }
  const resumo = resumoAcertoClasse(entrada);
  return (
    <figure className="folha-quieta flex flex-col gap-3">
      <DicaGrafico>
        <div className="hidden overflow-x-auto sm:block">
          <Desenho layout={layout} resumo={resumo} sufixo="" className="w-full min-w-[480px]" />
        </div>
        <Desenho layout={estreito} resumo={resumo} sufixo="-estreito" className="w-full sm:hidden" />
      </DicaGrafico>
      <figcaption className="text-sm text-muted-foreground">
        Cada barra é uma situação: dos municípios que eram de fato daquela situação, a parte que o
        modelo acertou. A linha marca o acerto geral, que é a média das barras pesada pelo número
        de municípios.
      </figcaption>
    </figure>
  );
}

type DesenhoProps = {
  layout: LayoutAcertoClasse;
  resumo: string;
  sufixo: string;
  className: string;
};

function Desenho({ layout, resumo, sufixo, className }: DesenhoProps) {
  const { medidas, largura, altura, barras, referencia, marcas } = layout;
  const { esquerda, topo, base, alturaLinha, alturaBarra, fonte, fonteMenor } = medidas;
  const fimPlotagem = altura - base;
  const idTitulo = `${ID_TITULO}${sufixo}`;
  const idDesc = `${ID_DESC}${sufixo}`;
  return (
    <svg
      viewBox={`0 0 ${largura} ${altura}`}
      className={className}
      role="img"
      aria-labelledby={`${idTitulo} ${idDesc}`}
    >
      <title id={idTitulo}>Acerto por situação</title>
      <desc id={idDesc}>{resumo}</desc>
      {barras.map((barra) => (
        <rect
          key={`alvo-${barra.classe}`}
          x={0}
          y={barra.y + alturaBarra / 2 - alturaLinha / 2}
          width={largura}
          height={alturaLinha}
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
              y1={topo}
              y2={fimPlotagem}
              stroke="var(--border)"
              strokeWidth={1}
            />
            <text
              x={marca.x}
              y={fimPlotagem + medidas.descidaMarca}
              textAnchor="middle"
              fontSize={fonteMenor}
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
              x={esquerda - 10}
              y={barra.y + alturaBarra / 2 + medidas.deslocRotulo}
              dy="0.35em"
              textAnchor="end"
              fontSize={fonte}
              fill="currentColor"
              className="text-foreground"
            >
              {barra.rotulo}
            </text>
            <text
              x={esquerda - 10}
              y={barra.y + alturaBarra / 2 + medidas.deslocContagem}
              dy="0.35em"
              textAnchor="end"
              fontSize={fonteMenor}
              fill="currentColor"
              className="text-muted-foreground"
            >
              {`${formatarInteiro(barra.municipios)} ${barra.municipios === 1 ? "município" : "municípios"}`}
            </text>
            <rect
              x={barra.x}
              y={barra.y}
              width={barra.largura}
              height={alturaBarra}
              rx={2}
              fill="var(--tinta-quente)"
              stroke="var(--tinta-frio)"
              strokeWidth={barra.largura > 0 ? 1.5 : 0}
            />
            <text
              x={barra.x + barra.largura + 6}
              y={barra.y + alturaBarra / 2}
              dy="0.35em"
              fontSize={fonte}
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
              y1={topo - 12}
              y2={fimPlotagem}
              stroke="currentColor"
              strokeWidth={1}
            />
            <text
              x={referencia.xTexto}
              y={topo - 16}
              textAnchor={referencia.ancora}
              fontSize={fonteMenor}
              fill="currentColor"
            >
              {`Acerto geral ${referencia.valorTexto}`}
            </text>
          </g>
        ) : null}
      </g>
    </svg>
  );
}
