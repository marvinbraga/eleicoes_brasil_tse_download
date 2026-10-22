import { DicaGrafico } from "@/components/relatorios/dica-grafico";
import {
  MEDIDAS_HALTERES_ESTREITO,
  layoutHalteres,
  resumoHalteres,
  type LayoutHalteres,
  type ParCargos,
} from "@/lib/grafico-marca";

const TITULO = "Federal × estadual: vezes a média de cada cargo";
const ID = "grafico-marca-cargos";

export function GraficoMarcaCargos({ pares }: { pares: readonly ParCargos[] }) {
  const layout = layoutHalteres(pares);
  const estreito = layoutHalteres(pares, MEDIDAS_HALTERES_ESTREITO);
  if (layout === null || estreito === null) {
    return null;
  }
  const resumo = resumoHalteres(pares);
  return (
    <figure className="folha-quieta flex flex-col gap-3">
      <figcaption>
        <p className="font-medium text-foreground">{TITULO}</p>
        <p className="mt-1 text-sm text-muted-foreground">
          Círculo cheio: deputado federal. Círculo vazado: deputado estadual. A linha 1× é a média
          do cargo; 2× e 0,5× são os limiares de marca forte e voto na pessoa. Só partidos que
          estão nos dois rankings.
        </p>
      </figcaption>
      <DicaGrafico>
        <div className="hidden overflow-x-auto sm:block">
          <Desenho layout={layout} sufixo="" resumo={resumo} className="w-full min-w-[480px]" />
        </div>
        <Desenho
          layout={estreito}
          sufixo="-estreito"
          resumo={resumo}
          className="w-full sm:hidden"
        />
      </DicaGrafico>
    </figure>
  );
}

type DesenhoProps = {
  layout: LayoutHalteres;
  sufixo: string;
  resumo: string;
  className: string;
};

function Desenho({ layout, sufixo, resumo, className }: DesenhoProps) {
  const { medidas, largura, altura, halteres, referencias } = layout;
  const { esquerda, topo, alturaLinha, raio, descida, fonte, rotuloAcima } = medidas;
  const idTitulo = `${ID}-titulo${sufixo}`;
  const idDesc = `${ID}-desc${sufixo}`;
  return (
    <svg
      viewBox={`0 0 ${largura} ${altura}`}
      className={className}
      role="img"
      aria-labelledby={`${idTitulo} ${idDesc}`}
    >
      <title id={idTitulo}>{TITULO}</title>
      <desc id={idDesc}>{resumo}</desc>
      {halteres.map((haltere) => (
        <rect
          key={`alvo-${haltere.chave}`}
          x={0}
          y={haltere.y - descida - alturaLinha / 2}
          width={largura}
          height={alturaLinha}
          fill="transparent"
          className="hover:fill-muted/60"
          data-dica-titulo={haltere.rotulo}
          data-dica-linhas={haltere.dica}
        />
      ))}
      <g pointerEvents="none">
        {referencias.map((referencia) => (
          <g key={referencia.valor}>
            <line
              x1={referencia.x}
              x2={referencia.x}
              y1={topo - 4}
              y2={altura - medidas.base}
              stroke="var(--border)"
              strokeDasharray="4 3"
              strokeWidth={1}
            />
            {referencia.rotulo !== "" ? (
              <text
                x={referencia.x}
                y={topo - 8}
                textAnchor="middle"
                fontSize={fonte}
                fill="currentColor"
                className="text-muted-foreground tabular-nums"
              >
                {referencia.rotulo}
              </text>
            ) : null}
          </g>
        ))}
        {halteres.map((haltere) => (
          <g key={haltere.chave}>
            {rotuloAcima ? (
              <text
                x={esquerda}
                y={haltere.y - raio - 5}
                fontSize={fonte}
                fill="currentColor"
                className="text-foreground"
              >
                {haltere.rotulo}
              </text>
            ) : (
              <text
                x={esquerda - 8}
                y={haltere.y}
                dy="0.35em"
                textAnchor="end"
                fontSize={fonte}
                fill="currentColor"
                className="text-foreground"
              >
                {haltere.rotulo}
              </text>
            )}
            <line
              x1={haltere.xFederal}
              x2={haltere.xEstadual}
              y1={haltere.y}
              y2={haltere.y}
              stroke="var(--border)"
              strokeWidth={2}
            />
            <circle cx={haltere.xFederal} cy={haltere.y} r={raio} fill="var(--tinta-quente)" />
            <circle
              cx={haltere.xEstadual}
              cy={haltere.y}
              r={raio}
              fill="var(--background)"
              stroke="var(--tinta-quente)"
              strokeWidth={2}
            />
          </g>
        ))}
      </g>
    </svg>
  );
}
