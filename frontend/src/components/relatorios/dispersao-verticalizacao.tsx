import { DicaGrafico } from "@/components/relatorios/dica-grafico";
import { formatarInteiro } from "@/lib/fracao";
import {
  MEDIDAS_DISPERSAO_ESTREITO,
  formatarR,
  layoutDispersao,
  type LayoutDispersao,
} from "@/lib/grafico-verticalizacao";
import { rotuloPartido } from "@/lib/partidos";
import { ROTULO_CARGO, type RelatorioVerticalizacao } from "@/lib/verticalizacao";

type DispersaoVerticalizacaoProps = {
  id: string;
  dados: RelatorioVerticalizacao;
};

export function DispersaoVerticalizacao({ id, dados }: DispersaoVerticalizacaoProps) {
  const { partido, cargo_x: x, cargo_y: y, coerencia } = dados.dispersao;
  const titulo = `${rotuloPartido(partido)}: ${ROTULO_CARGO[x]} × ${ROTULO_CARGO[y]} por município`;
  const layout = layoutDispersao(dados);
  const estreito = layoutDispersao(dados, MEDIDAS_DISPERSAO_ESTREITO);
  const medida =
    coerencia.r === null
      ? `Coerência sem medida (${formatarInteiro(coerencia.municipios)} municípios).`
      : `Coerência dentro das UFs: r = ${formatarR(coerencia.r)}, com ${formatarInteiro(coerencia.municipios)} municípios.`;
  if (layout === null || estreito === null) {
    return (
      <section className="flex flex-col gap-2">
        <p className="font-medium text-foreground">{titulo}</p>
        <p className="text-sm text-muted-foreground">
          O partido não concorreu aos dois cargos em nenhuma UF do recorte.
        </p>
      </section>
    );
  }
  const resumo = `${dados.dispersao.pontos.length} municípios. Cada ponto é um município, com a fatia do ${rotuloPartido(partido)} em ${ROTULO_CARGO[x]} no eixo horizontal e em ${ROTULO_CARGO[y]} no vertical. ${medida}`;
  return (
    <figure className="folha-quieta flex flex-col gap-3">
      <figcaption>
        <p className="font-medium text-foreground">{titulo}</p>
        <p className="mt-1 text-sm text-muted-foreground">
          {medida} O tamanho do ponto segue o comparecimento. A linha tracejada marca a mesma fatia
          nos dois cargos.
        </p>
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
  layout: LayoutDispersao;
  id: string;
  sufixo: string;
  titulo: string;
  resumo: string;
  className: string;
};

function Desenho({ layout, id, sufixo, titulo, resumo, className }: DesenhoProps) {
  const { medidas, marcasX, marcasY, diagonal, pontos, rotuloX, rotuloY } = layout;
  const { largura, altura, esquerda, direita, topo, base, fonte } = medidas;
  const idTitulo = `${id}-titulo${sufixo}`;
  const idDesc = `${id}-desc${sufixo}`;
  const chao = altura - base;
  const direitaX = largura - direita;
  return (
    <svg
      viewBox={`0 0 ${largura} ${altura}`}
      className={className}
      role="img"
      aria-labelledby={`${idTitulo} ${idDesc}`}
    >
      <title id={idTitulo}>{titulo}</title>
      <desc id={idDesc}>{resumo}</desc>
      <g pointerEvents="none">
        {marcasY.map((marca) => (
          <g key={`y-${marca.texto}`}>
            <line x1={esquerda} x2={direitaX} y1={marca.y} y2={marca.y} stroke="var(--border)" strokeWidth={1} />
            <text
              x={esquerda - 6}
              y={marca.y}
              dy="0.35em"
              textAnchor="end"
              fontSize={fonte}
              fill="currentColor"
              className="text-muted-foreground tabular-nums"
            >
              {marca.texto}
            </text>
          </g>
        ))}
        {marcasX.map((marca) => (
          <text
            key={`x-${marca.texto}`}
            x={marca.x}
            y={chao + fonte + 4}
            textAnchor="middle"
            fontSize={fonte}
            fill="currentColor"
            className="text-muted-foreground tabular-nums"
          >
            {marca.texto}
          </text>
        ))}
        <line x1={esquerda} x2={esquerda} y1={topo} y2={chao} stroke="var(--border)" strokeWidth={1} />
        {diagonal ? (
          <g>
            <line
              x1={diagonal.x1}
              y1={diagonal.y1}
              x2={diagonal.x2}
              y2={diagonal.y2}
              stroke="var(--muted-foreground)"
              strokeWidth={1}
              strokeDasharray="4 3"
            />
            <text
              x={diagonal.x2 - 4}
              y={diagonal.y2 + fonte + 2}
              textAnchor="end"
              fontSize={fonte - 1}
              fill="currentColor"
              className="text-muted-foreground"
            >
              mesma fatia nos dois cargos
            </text>
          </g>
        ) : null}
        <text
          x={(esquerda + direitaX) / 2}
          y={altura - 6}
          textAnchor="middle"
          fontSize={fonte}
          fill="currentColor"
          className="text-foreground"
        >
          {rotuloX}
        </text>
        <text
          transform={`translate(${fonte - 2} ${(topo + chao) / 2}) rotate(-90)`}
          textAnchor="middle"
          fontSize={fonte}
          fill="currentColor"
          className="text-foreground"
        >
          {rotuloY}
        </text>
      </g>
      {pontos.map((ponto) => (
        <circle
          key={ponto.chave}
          cx={ponto.cx}
          cy={ponto.cy}
          r={ponto.raio}
          fill="var(--tinta-quente)"
          fillOpacity={0.35}
          stroke="transparent"
          strokeWidth={8}
          data-dica-titulo={ponto.dicaTitulo}
          data-dica-linhas={ponto.dicaLinhas.join("\n")}
        />
      ))}
    </svg>
  );
}
