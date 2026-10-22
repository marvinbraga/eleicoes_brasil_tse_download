import { ErroRelatorio } from "@/components/relatorios/erro-relatorio";
import { ExplicacaoCadeiras } from "@/components/relatorios/explicacao-cadeiras";
import { GraficoPoder } from "@/components/relatorios/grafico-poder";
import { NotasRelatorio } from "@/components/relatorios/notas-relatorio";
import {
  DetalheUf,
  TabelaGoverno,
  TabelaLegendasCasa,
  TabelaSenado,
} from "@/components/relatorios/tabela-cadeiras";
import { buscarCadeiras } from "@/lib/buscar-relatorios";
import type { Ano, Turno } from "@/lib/eleicoes";
import { formatarInteiro } from "@/lib/fracao";
import {
  MEDIDAS_CADEIRAS,
  frasesCadeiras,
  itensCasa,
  itensSenado,
} from "@/lib/grafico-cadeiras";

type DadosCadeirasProps = {
  ano: Ano;
  turno: Turno;
};

const AVISO =
  "Isto é uma estimativa feita com os boletins de urna, não o resultado oficial do TSE. " +
  "Votos anulados depois da eleição, registros indeferidos e empates que o boletim não " +
  "resolve podem mudar cadeiras.";

export async function DadosCadeiras({ ano, turno }: DadosCadeirasProps) {
  const resultado = await buscarCadeiras(ano, turno);
  if (!resultado.ok) {
    return <ErroRelatorio detalhe={resultado.detalhe} />;
  }
  const dados = resultado.dados;
  const gravado = new Date(dados.gerado_em).toLocaleString("pt-BR", {
    timeZone: "America/Sao_Paulo",
  });
  return (
    <div className="flex flex-col gap-10">
      <p
        role="note"
        className="max-w-3xl rounded-md border border-border bg-muted px-4 py-3 font-medium text-foreground"
      >
        {AVISO}
      </p>
      <section
        aria-labelledby="resumo-cadeiras"
        className="flex max-w-3xl flex-col gap-2 rounded-md border border-border px-4 py-3"
      >
        <h2 id="resumo-cadeiras" className="font-semibold">
          Em resumo
        </h2>
        <ul className="flex list-disc flex-col gap-1 pl-5">
          {frasesCadeiras(dados).map((frase) => (
            <li key={frase}>{frase}</li>
          ))}
        </ul>
      </section>
      <ExplicacaoCadeiras />
      {dados.casas.map((casa) => (
        <section
          key={casa.casa}
          aria-labelledby={`casa-${casa.casa}`}
          className="flex flex-col gap-4"
        >
          <h2 id={`casa-${casa.casa}`} className="text-xl font-semibold">
            {casa.nome}
          </h2>
          <GraficoPoder
            id={`grafico-cadeiras-${casa.casa}`}
            titulo={`Cadeiras estimadas — ${casa.nome}`}
            introducao={`Cadeiras estimadas por partido ou federação, de ${formatarInteiro(casa.vagas_simuladas)} vagas simuladas.`}
            legenda="Cada barra é um partido ou uma federação. Na federação, o detalhe mostra quantas cadeiras ficam com cada partido."
            itens={itensCasa(casa, dados.legendas)}
            medidas={MEDIDAS_CADEIRAS}
          />
          <TabelaLegendasCasa casa={casa} legendas={dados.legendas} />
          <div className="flex flex-col gap-2">
            <h3 className="font-medium">Por UF</h3>
            {casa.ufs.map((uf) => (
              <DetalheUf key={uf.uf} uf={uf} legendas={dados.legendas} />
            ))}
          </div>
        </section>
      ))}
      <section aria-labelledby="casa-senado" className="flex flex-col gap-4">
        <h2 id="casa-senado" className="text-xl font-semibold">
          Senado Federal
        </h2>
        <GraficoPoder
          id="grafico-cadeiras-senado"
          titulo="Senadores estimados por partido"
          introducao={`Senadores estimados por partido, de ${formatarInteiro(dados.senado.vagas_simuladas)} vagas em disputa.`}
          legenda="Duas vagas por UF em 2026. No Senado não há federação na conta: vale o partido do candidato."
          itens={itensSenado(dados)}
        />
        <TabelaSenado senado={dados.senado} />
      </section>
      <section aria-labelledby="casa-governo" className="flex flex-col gap-4">
        <h2 id="casa-governo" className="text-xl font-semibold">
          Governadores
        </h2>
        <TabelaGoverno governo={dados.governo} />
      </section>
      <NotasRelatorio notas={dados.notas} />
      <p className="text-sm text-muted-foreground">
        Votos gravados em {gravado} (horário de Brasília). * marca resultado que depende de um
        empate que o boletim não resolve: entre candidatos (decidido pela idade) ou entre listas
        com média, votos e votos do próximo candidato iguais.
      </p>
    </div>
  );
}
