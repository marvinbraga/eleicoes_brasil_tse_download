import { ORDEM_CLASSE, COR_CLASSE } from "@/cruzamento/finalidade";
import { DicaGrafico } from "@/components/relatorios/dica-grafico";
import { formatarInteiro } from "@/lib/fracao";
import {
  MEDIDAS_ESTREITO,
  MEDIDAS_PADRAO,
  ROTULOS,
  composicaoPorRegiao,
  composicaoPorUf,
  frasesComposicao,
  layoutComposicao,
  resumoComposicao,
  type ComposicaoLugar,
  type LayoutComposicao,
  type MedidasComposicao,
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
        nota="O Exterior fica de fora: lá não há governador."
      />
      {porRegiao.length === 0 ? null : (
        <FiguraComposicao
          id="grafico-presidente-governador-regiao"
          titulo="Composição por região"
          lugares={porRegiao}
          unidade="regiões"
          nota={frasesComposicao(porRegiao, "regiões").join(" ")}
        />
      )}
    </section>
  );
}

type Unidade = "UFs" | "regiões";

type FiguraComposicaoProps = {
  id: string;
  titulo: string;
  lugares: readonly ComposicaoLugar[];
  unidade: Unidade;
  nota: string;
};

function layoutDa(lugares: readonly ComposicaoLugar[], unidade: Unidade, medidas: MedidasComposicao) {
  return layoutComposicao(lugares, unidade === "UFs" ? medidas.esquerdaUf : medidas.esquerdaRegiao, medidas);
}

function FiguraComposicao({ id, titulo, lugares, unidade, nota }: FiguraComposicaoProps) {
  const layout = layoutDa(lugares, unidade, MEDIDAS_PADRAO);
  const estreito = layoutDa(lugares, unidade, MEDIDAS_ESTREITO);
  if (layout === null || estreito === null) {
    return null;
  }
  const resumo = resumoComposicao(lugares, unidade);
  return (
    <figure className="folha-quieta flex flex-col gap-3">
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
      <figcaption className="text-sm text-muted-foreground">
        <p className="inline-flex flex-wrap items-center gap-x-4 gap-y-1">
          {ORDEM_CLASSE.map((classe) => (
            <span key={classe} className="inline-flex items-center gap-2">
              <svg width={12} height={12} viewBox="0 0 12 12" aria-hidden="true">
                <rect
                  width={12}
                  height={12}
                  fill={COR_CLASSE[classe]}
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

type DesenhoProps = {
  layout: LayoutComposicao;
  id: string;
  sufixo: string;
  titulo: string;
  resumo: string;
  className: string;
};

function Desenho({ layout, id, sufixo, titulo, resumo, className }: DesenhoProps) {
  const { medidas, largura, altura, esquerda, barras, marcas } = layout;
  const { topo, alturaLinha, alturaBarra } = medidas;
  const fimPlotagem = altura - medidas.base;
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
      {marcas.map((marca) => (
        <g key={marca.rotulo} pointerEvents="none">
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
            fontSize={medidas.fonteMenor}
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
            y={barra.y - (alturaLinha - alturaBarra) / 2}
            width={largura}
            height={alturaLinha}
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
              y={barra.y + alturaBarra / 2}
              dy="0.35em"
              textAnchor="end"
              fontSize={medidas.fonte}
              fill="currentColor"
              className="text-foreground"
            >
              {barra.codigo}
            </text>
            <rect
              x={esquerda}
              y={barra.y}
              width={largura - esquerda - medidas.direita}
              height={alturaBarra}
              fill="var(--tinta-frio)"
            />
            {barra.fatias.map((fatia) =>
              fatia.largura > 0 ? (
                <rect
                  key={fatia.classe}
                  x={fatia.x}
                  y={barra.y}
                  width={fatia.largura}
                  height={alturaBarra}
                  fill={fatia.cor}
                />
              ) : null,
            )}
          </g>
        </g>
      ))}
    </svg>
  );
}
