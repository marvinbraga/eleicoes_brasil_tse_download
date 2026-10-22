import { DicaGrafico } from "@/components/relatorios/dica-grafico";
import {
  DESCIDA_ROTULO_ACIMA,
  MEDIDAS_ESTREITO,
  layoutGrupos,
  resumoGrupos,
  type Grupo,
  type LayoutGrupos,
} from "@/lib/grafico-forca";

type GraficoForcaProps = {
  id: string;
  titulo: string;
  legenda: string;
  grupos: readonly Grupo[];
};

// Sem "use client": é renderizado dentro de PlacarForcaVista, que já é cliente.
export function GraficoForca({ id, titulo, legenda, grupos }: GraficoForcaProps) {
  const layout = layoutGrupos(grupos);
  const estreito = layoutGrupos(grupos, MEDIDAS_ESTREITO);
  if (layout === null || estreito === null) {
    return null;
  }
  const resumo = resumoGrupos(titulo, grupos);
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
  layout: LayoutGrupos;
  id: string;
  sufixo: string;
  titulo: string;
  resumo: string;
  className: string;
};

function Desenho({ layout, id, sufixo, titulo, resumo, className }: DesenhoProps) {
  const { medidas, largura, altura, grupos } = layout;
  const { esquerda, alturaBarra, alturaCabeca, passo, fonte, rotuloAcima } = medidas;
  const descida = rotuloAcima ? DESCIDA_ROTULO_ACIMA : 0;
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
      {grupos.flatMap((grupo) =>
        grupo.barras.map((barra) => (
          <rect
            key={`alvo-${grupo.chave}-${barra.chave}`}
            x={0}
            y={barra.y - descida - (rotuloAcima ? 0 : (passo - alturaBarra) / 2)}
            width={largura}
            height={passo}
            fill="transparent"
            className="hover:fill-muted/60"
            data-dica-titulo={grupo.rotulo}
            data-dica-linhas={`${barra.curto}: ${barra.texto}\n${barra.detalhe}`}
          />
        )),
      )}
      <g pointerEvents="none">
        {grupos.map((grupo) => {
          const primeira = grupo.barras[0];
          const ultima = grupo.barras.at(-1);
          return (
            <g key={grupo.chave}>
              <text
                x={rotuloAcima ? esquerda : 0}
                y={grupo.yCabeca + alturaCabeca / 2}
                dy="0.35em"
                fontSize={fonte}
                fill="currentColor"
                className="font-medium text-foreground"
              >
                {grupo.rotulo}
              </text>
              {primeira !== undefined && ultima !== undefined && !rotuloAcima ? (
                <line
                  x1={esquerda}
                  x2={esquerda}
                  y1={primeira.y - (passo - alturaBarra) / 2}
                  y2={ultima.y + alturaBarra + (passo - alturaBarra) / 2}
                  stroke="var(--border)"
                  strokeWidth={1}
                />
              ) : null}
              {grupo.barras.map((barra) => (
                <g key={barra.chave}>
                  {rotuloAcima ? (
                    <text
                      x={esquerda}
                      y={barra.y - 4}
                      fontSize={fonte}
                      fill="currentColor"
                      className="text-muted-foreground"
                    >
                      {barra.curto}
                    </text>
                  ) : (
                    <text
                      x={esquerda - 8}
                      y={barra.y + alturaBarra / 2}
                      dy="0.35em"
                      textAnchor="end"
                      fontSize={fonte}
                      fill="currentColor"
                      className="text-muted-foreground"
                    >
                      {barra.curto}
                    </text>
                  )}
                  <rect
                    x={esquerda}
                    y={barra.y}
                    width={barra.largura}
                    height={alturaBarra}
                    rx={2}
                    fill="var(--tinta-quente)"
                    fillOpacity={barra.opacidade}
                  />
                  <text
                    x={esquerda + barra.largura + 6}
                    y={barra.y + alturaBarra / 2}
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
          );
        })}
      </g>
    </svg>
  );
}
