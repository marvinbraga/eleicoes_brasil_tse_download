import { ErroRelatorio } from "@/components/relatorios/erro-relatorio";
import { ExplicacaoCapilaridade } from "@/components/relatorios/explicacao-capilaridade";
import { GraficoFaixasCapilaridade } from "@/components/relatorios/grafico-faixas-capilaridade";
import { GraficoRankingCapilaridade } from "@/components/relatorios/grafico-ranking-capilaridade";
import { TabelaCapilaridade } from "@/components/relatorios/tabela-capilaridade";
import { buscarCapilaridade } from "@/lib/buscar-relatorios";
import type { LugarCapilaridade, PartidoCapilaridade } from "@/lib/capilaridade";
import { rotuloCargoPoder, type Ano, type CargoPoder, type Turno, type ValorConsulta } from "@/lib/eleicoes";
import { formatarInteiro } from "@/lib/fracao";
import { leituraCapilaridade } from "@/lib/grafico-capilaridade";
import { partidoEscolhido } from "@/lib/ler-capilaridade";
import { rotuloPartido } from "@/lib/partidos";

type DadosCapilaridadeProps = {
  ano: Ano;
  turno: Turno;
  cargo: CargoPoder;
  recorte: string;
  partido: ValorConsulta;
};

const CAMINHO = "/relatorios/capilaridade";

export async function DadosCapilaridade({ ano, turno, cargo, recorte, partido }: DadosCapilaridadeProps) {
  const resultado = await buscarCapilaridade(ano, turno, cargo, recorte);
  if (!resultado.ok) {
    return <ErroRelatorio detalhe={resultado.detalhe} />;
  }
  const dados = resultado.dados;
  const escolhido = partidoEscolhido(dados, partido);
  const hrefs: Record<number, string> = {};
  for (const item of dados.partidos) {
    const params = new URLSearchParams({
      ano,
      turno,
      cargo,
      recorte,
      consultar: "1",
      partido: String(item.partido),
    });
    hrefs[item.partido] = `${CAMINHO}?${params.toString()}`;
  }
  return (
    <div className="flex flex-col gap-8">
      <p className="text-sm text-muted-foreground">
        {rotuloCargoPoder(cargo)} · {dados.recorte.nome} · {formatarInteiro(dados.municipios)} municípios
      </p>
      <ExplicacaoCapilaridade dados={dados} />
      <GraficoRankingCapilaridade
        partidos={dados.partidos}
        selecionado={escolhido?.partido ?? -1}
        hrefs={hrefs}
      />
      {escolhido === null ? null : (
        <Detalhe partido={escolhido} leitura={leituraCapilaridade(escolhido, dados.recorte, dados.ufs)} />
      )}
      <TabelaCapilaridade partidos={dados.partidos} selecionado={escolhido?.partido ?? null} hrefs={hrefs} />
    </div>
  );
}

function Detalhe({ partido, leitura }: { partido: PartidoCapilaridade; leitura: string[] }) {
  return (
    <section aria-labelledby="detalhe-capilaridade" className="flex flex-col gap-4">
      <div className="folha-quieta max-w-3xl space-y-2">
        <h2 id="detalhe-capilaridade" className="text-xl font-semibold">
          {rotuloPartido(partido.partido)}
          <span className="ml-2 text-base font-normal text-muted-foreground">{partido.rotulo_classe}</span>
        </h2>
        {leitura.map((frase) => (
          <p key={frase}>{frase}</p>
        ))}
      </div>
      <GraficoFaixasCapilaridade partido={partido} />
      {partido.subdivisoes.length > 0 ? (
        <div className="folha-quieta max-w-3xl">
          <h3 className="font-medium">Por subdivisão (parte dos votos / parte do eleitorado / vezes)</h3>
          <ul className="mt-2 space-y-1 text-sm">
            {partido.subdivisoes.map((item) => (
              <li key={item.codigo} className="tabular-nums">
                {item.nome}: {item.parte_texto} / {item.eleitorado_texto} / {item.vezes}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      <div className="grid gap-4 sm:grid-cols-2">
        <Lugares titulo="Onde é mais forte" lugares={partido.fortes} />
        <Lugares titulo="De onde vêm mais votos" lugares={partido.maiores} />
      </div>
    </section>
  );
}

function Lugares({ titulo, lugares }: { titulo: string; lugares: readonly LugarCapilaridade[] }) {
  return (
    <div className="folha-quieta">
      <h3 className="font-medium">{titulo}</h3>
      {lugares.length === 0 ? <p className="mt-2 text-sm text-muted-foreground">Sem dados.</p> : null}
      <ol className="mt-2 list-decimal space-y-1 pl-5 text-sm">
        {lugares.map((lugar) => (
          <li key={lugar.codigo} className="tabular-nums">
            {lugar.nome}: {formatarInteiro(lugar.votos)} votos ({lugar.fatia_texto})
          </li>
        ))}
      </ol>
    </div>
  );
}
