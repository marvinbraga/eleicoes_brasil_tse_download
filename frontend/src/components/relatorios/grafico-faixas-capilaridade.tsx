import { DicaGrafico } from "@/components/relatorios/dica-grafico";
import type { PartidoCapilaridade } from "@/lib/capilaridade";
import {
  MEDIDAS_FAIXAS_ESTREITO,
  ROTULOS_FAIXA,
  layoutFaixas,
  resumoFaixas,
  type LayoutFaixas,
  type MedidaFaixa,
} from "@/lib/grafico-capilaridade";
import { rotuloPartido } from "@/lib/partidos";

const PAINEIS: readonly { medida: MedidaFaixa; titulo: string }[] = [
  { medida: "municipios", titulo: "Municípios" },
  { medida: "votos", titulo: "Votos do partido" },
];

const TITULO_EIXO = "vezes a fatia média do partido";

export function GraficoFaixasCapilaridade({ partido }: { partido: PartidoCapilaridade }) {
  const rotulo = rotuloPartido(partido.partido);
  return (
    <figure className="folha-quieta flex flex-col gap-3">
      <figcaption>
        <p className="font-medium text-foreground">Onde {rotulo} é fraco e onde é forte</p>
        <p className="mt-1 text-sm text-muted-foreground">
          As mesmas faixas nos dois painéis. Muitos municípios nas faixas baixas e muitos votos em
          &quot;3+&quot; indicam concentração.
        </p>
      </figcaption>
      <DicaGrafico>
        <div className="grid gap-4 sm:grid-cols-2">
          {PAINEIS.map((painel) => (
            <Painel key={painel.medida} partido={partido} medida={painel.medida} titulo={painel.titulo} />
          ))}
        </div>
      </DicaGrafico>
    </figure>
  );
}

type PainelProps = { partido: PartidoCapilaridade; medida: MedidaFaixa; titulo: string };

function Painel({ partido, medida, titulo }: PainelProps) {
  const largo = layoutFaixas(partido.faixas, medida);
  const estreito = layoutFaixas(partido.faixas, medida, MEDIDAS_FAIXAS_ESTREITO);
  if (largo === null || estreito === null) {
    return null;
  }
  const resumo = resumoFaixas(partido, medida);
  const id = `faixas-${partido.partido}-${medida}`;
  return (
    <div className="flex flex-col gap-1">
      <p className="text-sm font-medium text-foreground">{titulo}</p>
      <Desenho layout={largo} id={id} sufixo="" titulo={titulo} resumo={resumo} className="hidden w-full sm:block" />
      <Desenho
        layout={estreito}
        id={id}
        sufixo="-estreito"
        titulo={titulo}
        resumo={resumo}
        className="w-full sm:hidden"
      />
    </div>
  );
}

type DesenhoProps = {
  layout: LayoutFaixas;
  id: string;
  sufixo: string;
  titulo: string;
  resumo: string;
  className: string;
};

function Desenho({ layout, id, sufixo, titulo, resumo, className }: DesenhoProps) {
  const { medidas, largura, altura, colunas } = layout;
  const chao = altura - medidas.base;
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
      <line
        x1={medidas.esquerda}
        x2={largura - medidas.direita}
        y1={chao}
        y2={chao}
        stroke="var(--border)"
        strokeWidth={1}
      />
      {colunas.map((coluna) => {
        const centro = coluna.x + coluna.largura / 2;
        return (
          <g key={coluna.chave}>
            <rect
              x={coluna.x}
              y={medidas.topo}
              width={coluna.largura}
              height={chao - medidas.topo}
              fill="transparent"
              className="hover:fill-muted/60"
              data-dica-titulo={ROTULOS_FAIXA[coluna.chave].longo}
              data-dica-linhas={coluna.dica.join("\n")}
            />
            <g pointerEvents="none">
              <rect
                x={coluna.x}
                y={coluna.y}
                width={coluna.largura}
                height={coluna.altura}
                fill={coluna.neutra ? "var(--muted-foreground)" : "var(--tinta-quente)"}
                fillOpacity={coluna.neutra ? 0.45 : 1}
              />
              <text
                x={centro}
                y={coluna.y - 4}
                textAnchor="middle"
                fontSize={medidas.fonte - 1}
                fill="currentColor"
                className="text-foreground tabular-nums"
              >
                {coluna.valor}
              </text>
              <text
                x={centro}
                y={chao + 14}
                textAnchor="middle"
                fontSize={medidas.fonte}
                fill="currentColor"
                className="text-muted-foreground"
              >
                {ROTULOS_FAIXA[coluna.chave].curto}
              </text>
            </g>
          </g>
        );
      })}
      <text
        x={largura / 2}
        y={altura - 6}
        textAnchor="middle"
        fontSize={medidas.fonte - 1}
        fill="currentColor"
        className="text-muted-foreground"
        pointerEvents="none"
      >
        {TITULO_EIXO}
      </text>
    </svg>
  );
}
