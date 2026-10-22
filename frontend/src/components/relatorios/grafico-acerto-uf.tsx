import { DicaGrafico } from "@/components/relatorios/dica-grafico";
import { formatarInteiro } from "@/lib/fracao";
import {
  MEDIDAS_ESTREITO,
  RAIO_MAX,
  RAIO_MIN,
  layoutAcertoUf,
  resumoAcertoUf,
  type EntradaGrafico,
  type LayoutAcertoUf,
} from "@/lib/grafico-acerto-uf";

const ID_TITULO = "grafico-acerto-uf-titulo";
const ID_DESC = "grafico-acerto-uf-desc";
const LADO_LEGENDA = 2 * RAIO_MAX + 4;

export function GraficoAcertoUf({ porUf, acerto, base, baseLider }: EntradaGrafico) {
  const entrada = { porUf, acerto, base, baseLider };
  const layout = layoutAcertoUf(entrada);
  const estreito = layoutAcertoUf(entrada, MEDIDAS_ESTREITO);
  if (layout === null || estreito === null) {
    return null;
  }
  const resumo = resumoAcertoUf(entrada);
  return (
    <figure className="folha-quieta flex flex-col gap-3">
      <DicaGrafico>
        <div className="hidden overflow-x-auto sm:block">
          <Desenho layout={layout} resumo={resumo} sufixo="" className="w-full min-w-[480px]" />
        </div>
        <Desenho layout={estreito} resumo={resumo} sufixo="-estreito" className="w-full sm:hidden" />
      </DicaGrafico>
      <figcaption className="text-sm text-muted-foreground">
        <p>
          Cada ponto é uma UF, do maior acerto para o menor. O tamanho acompanha o número de
          municípios. As linhas marcam o acerto geral e os dois chutes simples do resumo.
        </p>
        <p className="mt-2 inline-flex flex-wrap items-center gap-x-4 gap-y-1">
          <TamanhoLegenda raio={RAIO_MIN} municipios={layout.menorMunicipios} />
          <TamanhoLegenda raio={RAIO_MAX} municipios={layout.maiorMunicipios} />
        </p>
      </figcaption>
    </figure>
  );
}

type DesenhoProps = {
  layout: LayoutAcertoUf;
  resumo: string;
  sufixo: string;
  className: string;
};

function Desenho({ layout, resumo, sufixo, className }: DesenhoProps) {
  const { medidas, largura, altura, pontos, linhas, marcas } = layout;
  const { esquerda, direita, topo, base, alturaLinha, alturaFaixa, fonte, fonteMenor } = medidas;
  const fimPlotagem = altura - base;
  const larguraPlotagem = largura - esquerda - direita;
  const idTitulo = `${ID_TITULO}${sufixo}`;
  const idDesc = `${ID_DESC}${sufixo}`;
  return (
    <svg
      viewBox={`0 0 ${largura} ${altura}`}
      className={className}
      role="img"
      aria-labelledby={`${idTitulo} ${idDesc}`}
    >
      <title id={idTitulo}>Acerto por UF</title>
      <desc id={idDesc}>{resumo}</desc>
      {pontos.map((ponto) => (
        <rect
          key={`alvo-${ponto.uf}`}
          x={esquerda}
          y={ponto.y - alturaLinha / 2}
          width={larguraPlotagem}
          height={alturaLinha}
          fill="transparent"
          className="hover:fill-muted/60"
          data-dica-titulo={ponto.uf}
          data-dica-linhas={`${ponto.acertoTexto}\n${formatarInteiro(ponto.municipios)} ${ponto.municipios === 1 ? "município" : "municípios"}`}
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
        {linhas.map((linha) => (
          <g
            key={linha.chave}
            className={linha.chave === "acerto" ? "text-foreground" : "text-muted-foreground"}
          >
            <line
              x1={linha.x}
              x2={linha.x}
              y1={topo - 4}
              y2={fimPlotagem}
              stroke="currentColor"
              strokeWidth={1}
              strokeDasharray={linha.chave === "acerto" ? undefined : "4 3"}
            />
            <text
              x={linha.xTexto}
              y={medidas.primeiraFaixa + linha.faixa * alturaFaixa}
              textAnchor={linha.ancora}
              fontSize={fonteMenor}
              fill="currentColor"
            >
              {`${linha.rotulo} ${linha.valorTexto}`}
            </text>
          </g>
        ))}
        {pontos.map((ponto) => (
          <g key={ponto.uf}>
            <text
              x={esquerda - 8}
              y={ponto.y}
              dy="0.35em"
              textAnchor="end"
              fontSize={fonte}
              fill="currentColor"
              className="text-foreground"
            >
              {ponto.uf}
            </text>
            <circle
              cx={ponto.x}
              cy={ponto.y}
              r={ponto.raio}
              fill="var(--tinta-quente)"
              stroke="var(--tinta-frio)"
              strokeWidth={2}
            />
          </g>
        ))}
      </g>
    </svg>
  );
}

function TamanhoLegenda({ raio, municipios }: { raio: number; municipios: number }) {
  return (
    <span className="inline-flex items-center gap-2">
      <svg
        width={LADO_LEGENDA}
        height={LADO_LEGENDA}
        viewBox={`0 0 ${LADO_LEGENDA} ${LADO_LEGENDA}`}
        aria-hidden="true"
      >
        <circle
          cx={LADO_LEGENDA / 2}
          cy={LADO_LEGENDA / 2}
          r={raio}
          fill="var(--tinta-quente)"
          stroke="var(--tinta-frio)"
          strokeWidth={2}
        />
      </svg>
      {formatarInteiro(municipios)} {municipios === 1 ? "município" : "municípios"}
    </span>
  );
}
