import { DispersaoVerticalizacao } from "@/components/relatorios/dispersao-verticalizacao";
import { ErroRelatorio } from "@/components/relatorios/erro-relatorio";
import { EscolhaDispersaoVerticalizacao } from "@/components/relatorios/escolha-dispersao-verticalizacao";
import { MatrizVerticalizacao } from "@/components/relatorios/matriz-verticalizacao";
import { NotasRelatorio } from "@/components/relatorios/notas-relatorio";
import { TabelaVerticalizacao } from "@/components/relatorios/tabela-verticalizacao";
import { buscarVerticalizacao } from "@/lib/buscar-relatorios";
import { nomeUf, type Ano, type Turno, type UfFiltro } from "@/lib/eleicoes";
import { formatarInteiro } from "@/lib/fracao";
import {
  MEDIDAS_COERENCIA_ESTREITO,
  MEDIDAS_MATRIZ_ESTREITO,
  frasesVerticalizacao,
  matrizCoerencia,
  matrizFatias,
} from "@/lib/grafico-verticalizacao";
import type { CargoVertical } from "@/lib/verticalizacao";

type DadosVerticalizacaoProps = {
  ano: Ano;
  turno: Turno;
  uf: UfFiltro;
  partido: string | null;
  cargoX: CargoVertical;
  cargoY: CargoVertical;
};

const EXPLICACAO = [
  "A matriz mostra, para cada partido, a fatia dos votos válidos em cada cargo, contada só onde o partido teve candidato. Onde não teve, a célula fica riscada: não é fraqueza, é ausência.",
  "A coerência pergunta se, dentro de um mesmo estado, os municípios onde o partido vai melhor para deputado são também os municípios onde ele vai melhor na eleição majoritária. Vai de −1 (o contrário) a 1 (sempre juntos). A última coluna compara deputado federal com estadual e serve de referência.",
  "Puxador é o partido cuja candidatura majoritária teve pelo menos o dobro do esperado pela força em deputado, com 10 pontos ou mais de diferença. Base sem cabeça forte é o contrário. O esperado é a fatia que o partido teria se os votos da majoritária seguissem os de deputado entre os partidos que lançaram candidato.",
];

export async function DadosVerticalizacao({
  ano,
  turno,
  uf,
  partido,
  cargoX,
  cargoY,
}: DadosVerticalizacaoProps) {
  const resultado = await buscarVerticalizacao(ano, turno, uf, partido, cargoX, cargoY);
  if (!resultado.ok) {
    return <ErroRelatorio detalhe={resultado.detalhe} />;
  }
  const dados = resultado.dados;
  const recorte = dados.uf === null ? "no Brasil" : `em ${nomeUf(dados.uf)}`;
  const fatias = matrizFatias(dados);
  const fatiasEstreita = matrizFatias(dados, MEDIDAS_MATRIZ_ESTREITO);
  const coerencia = matrizCoerencia(dados);
  const coerenciaEstreita = matrizCoerencia(dados, MEDIDAS_COERENCIA_ESTREITO);
  return (
    <div className="flex flex-col gap-6">
      <section
        aria-labelledby="resumo-verticalizacao"
        className="flex max-w-3xl flex-col gap-2 rounded-md border border-border px-4 py-3"
      >
        <h2 id="resumo-verticalizacao" className="font-semibold">
          Em resumo
        </h2>
        <ul className="flex list-disc flex-col gap-1 pl-5">
          {frasesVerticalizacao(dados).map((frase) => (
            <li key={frase}>{frase}</li>
          ))}
        </ul>
      </section>
      <div className="flex max-w-3xl flex-col gap-3">
        {EXPLICACAO.map((texto) => (
          <p key={texto}>{texto}</p>
        ))}
      </div>
      {fatias !== null && fatiasEstreita !== null ? (
        <MatrizVerticalizacao
          id="vz-fatias"
          titulo={`Fatia de cada partido por cargo ${recorte}`}
          legenda="Percentual dos votos válidos onde o partido teve candidato. Passe o cursor numa célula para ver a fatia no recorte todo e em quantas UFs ele concorreu."
          layout={fatias}
          estreito={fatiasEstreita}
          escala="fatia"
        />
      ) : null}
      {coerencia !== null && coerenciaEstreita !== null ? (
        <MatrizVerticalizacao
          id="vz-coerencia"
          titulo={`Coerência municipal entre cargos ${recorte}`}
          legenda={`Correlação r dentro de cada UF, ponderada pelo comparecimento. Fica em branco com menos de ${dados.limiares.minimo_municipios} municípios.`}
          layout={coerencia}
          estreito={coerenciaEstreita}
          escala="r"
        />
      ) : null}
      <section className="flex flex-col gap-4" aria-label="Dispersão municipal">
        <EscolhaDispersaoVerticalizacao
          ano={ano}
          turno={turno}
          uf={uf}
          partidos={dados.partidos.map((item) => item.partido)}
          partido={dados.dispersao.partido}
          cargoX={dados.dispersao.cargo_x}
          cargoY={dados.dispersao.cargo_y}
        />
        <DispersaoVerticalizacao id="vz-dispersao" dados={dados} />
      </section>
      <TabelaVerticalizacao partidos={dados.partidos} />
      <NotasRelatorio notas={dados.notas} />
      {dados.sem_uf > 0 ? <p className="text-sm">{fraseSemUf(dados.sem_uf)}</p> : null}
    </div>
  );
}

function fraseSemUf(quantidade: number): string {
  if (quantidade === 1) {
    return "1 município ficou de fora por não ter UF.";
  }
  return `${formatarInteiro(quantidade)} municípios ficaram de fora por não terem UF.`;
}
