import { ORDEM_CLASSE, INTENSIDADE } from "@/cruzamento/finalidade";
import { DicaGrafico } from "@/components/relatorios/dica-grafico";
import { formatarInteiro } from "@/lib/fracao";
import {
  ALTURA_BARRA,
  ALTURA_LINHA,
  BASE,
  DIREITA,
  ESQUERDA_REGIAO,
  ESQUERDA_UF,
  ROTULOS,
  TOPO,
  composicaoPorRegiao,
  composicaoPorUf,
  frasesComposicao,
  layoutComposicao,
  resumoComposicao,
  type ComposicaoLugar,
} from "@/lib/grafico-presidente-governador";
import type { GrupoMunicipios } from "@/lib/relatorios";

type GraficoPresidenteGovernadorProps = {
  grupos: readonly GrupoMunicipios[];
};

export function GraficoPresidenteGovernador({ grupos }: GraficoPresidenteGovernadorProps) {
  const porUf = composicaoPorUf(grupos);
  if (porUf.length === 0) {
    return null;
  }
  const porRegiao = composicaoPorRegiao(porUf);
  return (
    <section aria-labelledby="composicao-lugar" className="flex flex-col gap-3">
      <h2 id="composicao-lugar" className="leitura-titulo text-2xl">
        Composição por estado e região
      </h2>
      <p>
        Cada barra é uma UF e soma 100% dos votos válidos de presidente dados nela. A barra se
        divide pela classe do município onde o voto foi dado, nas mesmas quatro classes e com os
        mesmos tons da composição acima, do mais forte (Consolidação) ao mais fraco (Sem
        governador). As UFs vão da maior para a menor fatia de consolidação. O segundo gráfico
        soma as UFs de cada região.
      </p>
      <p className="text-sm text-muted-foreground">
        As tabelas por estado e por região dão uma classe só, calculada com o total do lugar. A
        barra olha cada município. Por isso um lugar pode estar em consolidação na tabela e ter a
        maior parte dos votos em municípios em aberto.
      </p>
      {frasesComposicao(porUf, "UFs").map((frase) => (
        <p key={frase}>{frase}</p>
      ))}
      <FiguraComposicao
        id="grafico-presidente-governador-uf"
        titulo="Composição por UF"
        lugares={porUf}
        unidade="UFs"
        esquerda={ESQUERDA_UF}
        nota="O Exterior fica de fora: lá não há governador."
      />
      {porRegiao.length === 0 ? null : (
        <FiguraComposicao
          id="grafico-presidente-governador-regiao"
          titulo="Composição por região"
          lugares={porRegiao}
          unidade="regiões"
          esquerda={ESQUERDA_REGIAO}
          nota={frasesComposicao(porRegiao, "regiões").join(" ")}
        />
      )}
    </section>
  );
}

type FiguraComposicaoProps = {
  id: string;
  titulo: string;
  lugares: readonly ComposicaoLugar[];
  unidade: "UFs" | "regiões";
  esquerda: number;
  nota: string;
};

function FiguraComposicao({ id, titulo, lugares, unidade, esquerda, nota }: FiguraComposicaoProps) {
  const layout = layoutComposicao(lugares, esquerda);
  if (layout === null) {
    return null;
  }
  const { largura, altura, barras, marcas } = layout;
  const fimPlotagem = altura - BASE;
  const idTitulo = `${id}-titulo`;
  const idDesc = `${id}-desc`;
  return (
    <figure className="folha-quieta flex flex-col gap-3">
      <DicaGrafico>
        <div className="overflow-x-auto">
          <svg
            viewBox={`0 0 ${largura} ${altura}`}
            className="w-full min-w-[480px]"
            role="img"
            aria-labelledby={`${idTitulo} ${idDesc}`}
          >
            <title id={idTitulo}>{titulo}</title>
            <desc id={idDesc}>{resumoComposicao(lugares, unidade)}</desc>
            {marcas.map((marca) => (
              <g key={marca.rotulo} pointerEvents="none">
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
              <g key={barra.codigo}>
                <rect
                  x={0}
                  y={barra.y - (ALTURA_LINHA - ALTURA_BARRA) / 2}
                  width={largura}
                  height={ALTURA_LINHA}
                  fill="transparent"
                  className="hover:fill-muted/60"
                  data-dica-titulo={barra.codigo}
                  data-dica-linhas={[
                    ...barra.fatias.map((fatia) => `${ROTULOS[fatia.classe]} ${fatia.fatiaTexto}`),
                    `${formatarInteiro(barra.total)} votos válidos`,
                  ].join("\n")}
                />
                <g pointerEvents="none">
                  <text
                    x={esquerda - 8}
                    y={barra.y + ALTURA_BARRA / 2}
                    dy="0.35em"
                    textAnchor="end"
                    fontSize={12}
                    fill="currentColor"
                    className="text-foreground"
                  >
                    {barra.codigo}
                  </text>
                  <rect
                    x={esquerda}
                    y={barra.y}
                    width={largura - esquerda - DIREITA}
                    height={ALTURA_BARRA}
                    fill="var(--tinta-frio)"
                  />
                  {barra.fatias.map((fatia) =>
                    fatia.largura > 0 ? (
                      <rect
                        key={fatia.classe}
                        x={fatia.x}
                        y={barra.y}
                        width={fatia.largura}
                        height={ALTURA_BARRA}
                        fill="var(--tinta-quente)"
                        fillOpacity={fatia.opacidade}
                      />
                    ) : null,
                  )}
                </g>
              </g>
            ))}
          </svg>
        </div>
      </DicaGrafico>
      <figcaption className="text-sm text-muted-foreground">
        <p className="inline-flex flex-wrap items-center gap-x-4 gap-y-1">
          {ORDEM_CLASSE.map((classe) => (
            <span key={classe} className="inline-flex items-center gap-2">
              <svg width={12} height={12} viewBox="0 0 12 12" aria-hidden="true">
                <rect
                  width={12}
                  height={12}
                  fill="var(--tinta-quente)"
                  fillOpacity={INTENSIDADE[classe]}
                />
              </svg>
              {ROTULOS[classe]}
            </span>
          ))}
        </p>
        <p className="mt-2">{nota}</p>
      </figcaption>
    </figure>
  );
}
