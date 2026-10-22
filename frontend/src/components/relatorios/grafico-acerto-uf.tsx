import { DicaGrafico } from "@/components/relatorios/dica-grafico";
import { formatarInteiro } from "@/lib/fracao";
import {
  ALTURA_FAIXA,
  ALTURA_LINHA,
  BASE,
  DIREITA,
  ESQUERDA,
  RAIO_MAX,
  RAIO_MIN,
  TOPO,
  layoutAcertoUf,
  resumoAcertoUf,
  type EntradaGrafico,
} from "@/lib/grafico-acerto-uf";

const ID_TITULO = "grafico-acerto-uf-titulo";
const ID_DESC = "grafico-acerto-uf-desc";
const LADO_LEGENDA = 2 * RAIO_MAX + 4;

export function GraficoAcertoUf({ porUf, acerto, base, baseLider }: EntradaGrafico) {
  const entrada = { porUf, acerto, base, baseLider };
  const layout = layoutAcertoUf(entrada);
  if (layout === null) {
    return null;
  }
  const { largura, altura, pontos, linhas, marcas } = layout;
  const fimPlotagem = altura - BASE;
  const larguraPlotagem = largura - ESQUERDA - DIREITA;
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
            <title id={ID_TITULO}>Acerto por UF</title>
            <desc id={ID_DESC}>{resumoAcertoUf(entrada)}</desc>
            {pontos.map((ponto) => (
              <rect
                key={`alvo-${ponto.uf}`}
                x={ESQUERDA}
                y={ponto.y - ALTURA_LINHA / 2}
                width={larguraPlotagem}
                height={ALTURA_LINHA}
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
              {linhas.map((linha) => (
                <g
                  key={linha.chave}
                  className={linha.chave === "acerto" ? "text-foreground" : "text-muted-foreground"}
                >
                  <line
                    x1={linha.x}
                    x2={linha.x}
                    y1={TOPO - 4}
                    y2={fimPlotagem}
                    stroke="currentColor"
                    strokeWidth={1}
                    strokeDasharray={linha.chave === "acerto" ? undefined : "4 3"}
                  />
                  <text
                    x={linha.ancora === "start" ? linha.x + 4 : linha.x - 4}
                    y={12 + linha.faixa * ALTURA_FAIXA}
                    textAnchor={linha.ancora}
                    fontSize={11}
                    fill="currentColor"
                  >
                    {`${linha.rotulo} ${linha.valorTexto}`}
                  </text>
                </g>
              ))}
              {pontos.map((ponto) => (
                <g key={ponto.uf}>
                  <text
                    x={ESQUERDA - 8}
                    y={ponto.y}
                    dy="0.35em"
                    textAnchor="end"
                    fontSize={12}
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
        </div>
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
