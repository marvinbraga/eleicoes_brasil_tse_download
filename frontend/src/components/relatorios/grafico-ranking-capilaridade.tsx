import { DicaGrafico } from "@/components/relatorios/dica-grafico";
import { TextoGrafico } from "@/components/relatorios/texto-grafico";
import type { PartidoCapilaridade } from "@/lib/capilaridade";
import {
  MEDIDAS_RANKING_ESTREITO,
  layoutRanking,
  linhasAcima,
  resumoRanking,
  textoDireita,
  textosRanking,
  type LayoutRanking,
} from "@/lib/grafico-capilaridade";

type GraficoRankingProps = {
  partidos: readonly PartidoCapilaridade[];
  selecionado: number;
  hrefs: Readonly<Record<number, string>>;
};

const TITULO = "Concentração dos votos por partido";

export function GraficoRankingCapilaridade({ partidos, selecionado, hrefs }: GraficoRankingProps) {
  const href = (partido: number) => hrefs[partido] ?? "#";
  const largo = layoutRanking(partidos, selecionado, href);
  const estreito = layoutRanking(partidos, selecionado, href, MEDIDAS_RANKING_ESTREITO);
  if (largo === null || estreito === null) {
    return (
      <p className="text-sm text-muted-foreground">
        Nenhum partido teve voto bastante para entrar no ranking; veja a tabela abaixo.
      </p>
    );
  }
  const resumo = resumoRanking(partidos);
  return (
    <figure className="folha-quieta flex flex-col gap-3">
      <figcaption>
        <p className="font-medium text-foreground">{TITULO}</p>
        <p className="mt-1 text-sm text-muted-foreground">
          O índice vai de 0 (mesma fatia em todo município) a 100 (votos vindos de um pedaço pequeno
          do eleitorado). Clique num partido para ver o detalhe.
        </p>
      </figcaption>
      <DicaGrafico>
        <div className="hidden overflow-x-auto sm:block">
          <Desenho layout={largo} sufixo="" resumo={resumo} className="w-full min-w-[560px]" />
        </div>
        <Desenho layout={estreito} sufixo="-estreito" resumo={resumo} className="w-full sm:hidden" />
      </DicaGrafico>
    </figure>
  );
}

type DesenhoProps = {
  layout: LayoutRanking;
  sufixo: string;
  resumo: string;
  className: string;
};

function Desenho({ layout, sufixo, resumo, className }: DesenhoProps) {
  const { medidas, largura, altura, marcas, barras } = layout;
  const { esquerda, topo, alturaBarra, fonte, rotuloAcima } = medidas;
  const textosMarca = textosRanking(layout).filter((texto) => texto.chave.startsWith("marca-"));
  const idTitulo = `ranking-capilaridade-titulo${sufixo}`;
  const idDesc = `ranking-capilaridade-desc${sufixo}`;
  const fundo = altura - medidas.base;
  return (
    <svg
      viewBox={`0 0 ${largura} ${altura}`}
      className={className}
      role="img"
      aria-labelledby={`${idTitulo} ${idDesc}`}
    >
      <title id={idTitulo}>{TITULO}</title>
      <desc id={idDesc}>{resumo}</desc>
      <g pointerEvents="none">
        {marcas.map((marca) => (
          <line
            key={marca.texto}
            x1={marca.x}
            x2={marca.x}
            y1={topo - 4}
            y2={fundo}
            stroke="var(--border)"
            strokeWidth={1}
          />
        ))}
        {textosMarca.map((texto) => (
          <TextoGrafico key={texto.chave} texto={texto} />
        ))}
      </g>
      {barras.map((barra) => {
        const destaque = barra.selecionado ? "font-semibold text-foreground" : "text-foreground";
        return (
          // Dentro de role="img" o link não é anunciado; a tabela abaixo leva os mesmos links.
          <a key={barra.partido} href={barra.href} tabIndex={-1} aria-hidden="true">
            <rect
              x={0}
              y={barra.topoLinha}
              width={largura}
              height={barra.alturaLinha}
              fill="transparent"
              className="hover:fill-muted/60"
              data-dica-titulo={barra.rotulo}
              data-dica-linhas={barra.dica.join("\n")}
            />
            <g pointerEvents="none">
              {rotuloAcima ? (
                linhasAcima(barra, medidas).map((linha, indice) => (
                  <text
                    key={indice}
                    x={esquerda}
                    y={linha.y}
                    fontSize={fonte}
                    fill="currentColor"
                    className={linha.classe ? "text-muted-foreground" : destaque}
                  >
                    {linha.classe ? linha.texto : barra.rotulo}
                    {!linha.classe && barra.classeNaLinha ? (
                      <tspan className="text-muted-foreground"> · {barra.classe}</tspan>
                    ) : null}
                  </text>
                ))
              ) : (
                <text
                  x={esquerda - 8}
                  y={barra.y + alturaBarra / 2}
                  dy="0.35em"
                  textAnchor="end"
                  fontSize={fonte}
                  fill="currentColor"
                  className={destaque}
                >
                  {barra.rotulo}
                </text>
              )}
              <rect
                x={esquerda}
                y={barra.y}
                width={Math.max(barra.largura, 1)}
                height={alturaBarra}
                rx={4}
                fill={barra.selecionado ? "var(--tinta-quente)" : "var(--muted-foreground)"}
                fillOpacity={barra.selecionado ? 1 : 0.45}
              />
              <text
                x={esquerda + barra.largura + 6}
                y={barra.y + alturaBarra / 2}
                dy="0.35em"
                fontSize={fonte}
                fill="currentColor"
                className="text-foreground tabular-nums"
              >
                {rotuloAcima ? (
                  textoDireita(barra, medidas)
                ) : (
                  <>
                    {barra.valor}
                    <tspan className="text-muted-foreground" dx={10}>
                      {barra.classe}
                    </tspan>
                  </>
                )}
              </text>
            </g>
          </a>
        );
      })}
    </svg>
  );
}
