import { ErroRelatorio } from "@/components/relatorios/erro-relatorio";
import { GraficoAcertoClasse } from "@/components/relatorios/grafico-acerto-classe";
import { GraficoAcertoUf } from "@/components/relatorios/grafico-acerto-uf";
import { NotasRelatorio } from "@/components/relatorios/notas-relatorio";
import { TabelaAcertoUf } from "@/components/relatorios/tabela-acerto-uf";
import { TabelaClasseGovernador } from "@/components/relatorios/tabela-classe-governador";
import { buscarClasseGovernador } from "@/lib/buscar-relatorios";
import type { Ano, Turno } from "@/lib/eleicoes";
import { formatarInteiro } from "@/lib/fracao";
import { frasesClasse } from "@/lib/grafico-acerto-classe";
import { rotuloPartido } from "@/lib/partidos";
import type { LinhaClasseGovernador } from "@/lib/relatorios";

const SIGNIFICADO: Record<string, string> = {
  consolidacao: "O partido que lidera o governador é o mesmo que lidera a presidência.",
  terreno_de_virada: "O partido que lidera o governador é o segundo da presidência.",
  em_aberto: "O partido que lidera o governador é um terceiro partido.",
  sem_governador: "Há líder para presidente e não há líder para governador.",
};

const ORDEM = ["consolidacao", "terreno_de_virada", "em_aberto", "sem_governador"];
const SEM_CORTE = "A árvore não cortou esta classe.";
const AVISO_ABAIXO_DA_BASE =
  "Num estado que o modelo não viu, as condições não acertam mais que os dois chutes simples do resumo. Elas descrevem esta eleição; não servem para prever outro estado.";

const RECONHECIDOS = {
  id: "significado-reconhecidos",
  texto:
    "Reconhecidos é a parte dos municípios de cada situação que o modelo acertou quando a UF deles ficou de fora.",
};

const NOTAS_CLARAS: Record<string, string> = {
  "O acerto vem de deixar cada UF de fora e prever seus municípios com a árvore das outras.":
    "Cada UF foi prova uma vez, sem ensinar o modelo que a testou.",
  "As regras mostradas são da árvore ajustada com todos os municípios.":
    "As condições da tabela usam todos os municípios.",
  "Isto não é uma previsão do segundo turno.": "O modelo descreve este turno; não é uma previsão.",
  "As fatias são só do presidente, sobre os votos válidos.":
    "As condições usam o voto de presidente sobre os votos válidos.",
  "O governador entra apenas na classe, não nas contas da árvore.":
    "O voto de governador só dá nome à situação. As condições olham o voto de presidente.",
};

type DadosClasseGovernadorProps = {
  ano: Ano;
  turno: Turno;
};

export async function DadosClasseGovernador({ ano, turno }: DadosClasseGovernadorProps) {
  const resultado = await buscarClasseGovernador(ano, turno);
  if (!resultado.ok) {
    return <ErroRelatorio detalhe={resultado.detalhe} />;
  }
  const dados = resultado.dados;
  const comum = classeComum(dados.linhas);
  const total = dados.linhas.reduce((soma, linha) => soma + linha.apoio, 0);
  const semCondicao = dados.linhas.filter(linhaSemCondicao);
  const nomesSemCondicao = juntar(semCondicao.map((linha) => linha.rotulo));
  const entrada = {
    linhas: dados.linhas,
    acerto: dados.acerto,
    base: dados.base,
    baseLider: dados.base_lider,
  };
  return (
    <div className="flex flex-col gap-6">
      <section
        aria-labelledby="resumo-classe-governador"
        className="flex max-w-3xl flex-col gap-2 rounded-md border border-border px-4 py-3"
      >
        <h2 id="resumo-classe-governador" className="font-semibold">
          Em resumo
        </h2>
        <ul className="flex list-disc flex-col gap-1 pl-5">
          {frasesClasse(entrada).map((frase) => (
            <li key={frase}>{frase}</li>
          ))}
        </ul>
      </section>
      <div className="flex max-w-3xl flex-col gap-3">
        <p>
          Só com a votação para presidente, dá para reconhecer a situação do governador no mesmo
          município?
        </p>
        <dl className="flex flex-col gap-2">
          {dados.linhas.map((linha) => (
            <div key={linha.classe}>
              <dt className="font-medium">{linha.rotulo}</dt>
              {SIGNIFICADO[linha.classe] ? (
                <dd className="text-muted-foreground">{SIGNIFICADO[linha.classe]}</dd>
              ) : null}
            </div>
          ))}
        </dl>
        <p>
          Para medir, cada UF ficou de fora uma vez: as condições foram montadas com as outras UFs e
          testadas nos municípios dela.
        </p>
        {dados.abaixo_da_base ? (
          <p
            role="note"
            className="rounded-md border border-border bg-muted px-4 py-3 font-medium text-foreground"
          >
            {AVISO_ABAIXO_DA_BASE}
          </p>
        ) : null}
        {comum ? (
          <p>
            A situação mais comum foi {comum.rotulo}, com {formatarInteiro(comum.apoio)} de{" "}
            {formatarInteiro(total)} municípios.
          </p>
        ) : null}
        {dados.sem_uf > 0 ? <p>{fraseSemUf(dados.sem_uf)}</p> : null}
        {nomesSemCondicao.length > 0 ? (
          <p>
            {nomesSemCondicao} {semCondicao.length === 1 ? "não tem" : "não têm"} uma condição
            própria: o modelo não separou {semCondicao.length === 1 ? "esse caso" : "esses casos"}.
          </p>
        ) : null}
        {dados.retidas.length > 0 ? (
          <p>Ficaram de fora, com menos de 2 municípios: {dados.retidas.join(", ")}.</p>
        ) : null}
      </div>
      <GraficoAcertoClasse {...entrada} />
      <GraficoAcertoUf
        porUf={dados.por_uf}
        acerto={dados.acerto}
        base={dados.base}
        baseLider={dados.base_lider}
      />
      <TabelaAcertoUf linhas={dados.por_uf} />
      <p className="max-w-3xl">
        Na tabela de condições, os percentuais das condições são a parte daquele partido nos votos
        válidos de presidente. Se todas as condições da linha acontecem, o modelo aponta aquela
        situação. <span id={RECONHECIDOS.id}>{RECONHECIDOS.texto}</span>
      </p>
      <TabelaClasseGovernador
        linhas={dados.linhas.map((linha) => ({
          ...linha,
          regras: linha.regras.map(textoDaRegra),
        }))}
        reconhecidos={RECONHECIDOS}
      />
      <NotasRelatorio notas={dados.notas.map(notaClara)} />
    </div>
  );
}

function classeComum(linhas: readonly LinhaClasseGovernador[]): LinhaClasseGovernador | null {
  const primeira = linhas[0];
  if (primeira === undefined) {
    return null;
  }
  const maior = Math.max(...linhas.map((linha) => linha.apoio));
  const empatadas = linhas.filter((linha) => linha.apoio === maior);
  return empatadas.reduce((escolhida, linha) =>
    posto(linha.classe) < posto(escolhida.classe) ? linha : escolhida,
  );
}

function posto(classe: string): number {
  const indice = ORDEM.indexOf(classe);
  return indice === -1 ? ORDEM.length : indice;
}

function linhaSemCondicao(linha: LinhaClasseGovernador): boolean {
  return linha.regras.length === 0 || linha.regras.every((regra) => regra === SEM_CORTE);
}

function textoDaRegra(regra: string): string {
  if (regra === SEM_CORTE) {
    return "Não há uma condição que aponte só esta situação.";
  }
  return regra
    .replace(/a fatia do partido (\d+) /g, (_, numero: string) => `o ${rotuloPartido(Number(numero))} `)
    .replaceAll("a fatia do partido ", "o partido ")
    .replaceAll(" for menor ou igual a ", " ficou com até ")
    .replaceAll(" for maior que ", " ficou com mais de ");
}

function fraseSemUf(quantidade: number): string {
  if (quantidade === 1) {
    return "1 município ficou de fora por não ter UF.";
  }
  return `${formatarInteiro(quantidade)} municípios ficaram de fora por não terem UF.`;
}

function notaClara(nota: string): string {
  return NOTAS_CLARAS[nota] ?? nota;
}

function juntar(nomes: readonly string[]): string {
  if (nomes.length <= 1) {
    return nomes[0] ?? "";
  }
  if (nomes.length === 2) {
    return `${nomes[0]} e ${nomes[1]}`;
  }
  const ultimo = nomes[nomes.length - 1] ?? "";
  return `${nomes.slice(0, -1).join(", ")} e ${ultimo}`;
}
