import { ErroRelatorio } from "@/components/relatorios/erro-relatorio";
import { GraficoPerfis } from "@/components/relatorios/grafico-perfis";
import { MunicipiosPerfis } from "@/components/relatorios/municipios-perfis";
import { NotasRelatorio } from "@/components/relatorios/notas-relatorio";
import { TabelaGruposPerfis } from "@/components/relatorios/tabela-grupos-perfil";
import { buscarPerfis } from "@/lib/buscar-relatorios";
import {
  rotuloCargoPerfil,
  type Ano,
  type CargoPerfil,
  type GruposPerfil,
  type Turno,
} from "@/lib/eleicoes";
import { formatarInteiro } from "@/lib/fracao";
import { leituraSeparacao, liderDe } from "@/lib/grafico-perfis";
import type { GrupoPerfil, RelatorioPerfis } from "@/lib/relatorios";

const NOTAS_CLARAS: Record<string, string> = {
  "A fatia do partido é o voto do partido sobre os votos válidos do município.":
    "O percentual do partido é a parte dele nos votos válidos.",
  "Branco e nulo são a parte deles sobre o comparecimento.":
    "Branco e nulo são a parte deles sobre quem compareceu.",
  "Senador não tem branco nem nulo neste relatório.": "Senador não traz branco nem nulo.",
  "Os lugares do exterior permanecem no perfil de presidente.":
    "No presidente, os lugares do exterior continuam na lista.",
  "Os grupos são um ajuste desta eleição, não uma previsão.": "Os grupos descrevem esta eleição.",
  "A silhueta é estimada numa amostra de 2000 municípios quando há mais que isso.":
    "Quando há mais de 2000 municípios, a separação dos grupos é medida numa amostra de 2000.",
  "Para grupos mais finos, peça um número fixo de grupos, como 5.":
    "Para ver grupos menores, escolha um número fixo de grupos no filtro.",
};

type DadosPerfisProps = {
  ano: Ano;
  turno: Turno;
  cargo: CargoPerfil;
  grupos: GruposPerfil;
};

export async function DadosPerfis({ ano, turno, cargo, grupos }: DadosPerfisProps) {
  const resultado = await buscarPerfis(ano, turno, cargo, grupos);
  if (!resultado.ok) {
    return <ErroRelatorio detalhe={resultado.detalhe} />;
  }
  const dados = resultado.dados;
  const nomeCargo = rotuloCargoPerfil(dados.cargo).toLocaleLowerCase("pt-BR");
  const maisLugares = extremo(dados.grupos, "municipios");
  const maisPeso = extremo(dados.grupos, "comparecimento");
  const separacao = leituraSeparacao(dados.silhueta);
  return (
    <div className="flex flex-col gap-10">
      <div className="flex max-w-3xl flex-col gap-3">
        <p className="text-sm text-muted-foreground">{subtitulo(dados)}</p>
        <p>
          Um grupo junta municípios que votaram de um jeito parecido para {nomeCargo}. Cada
          município fica em um grupo só.
        </p>
        <p>
          A mistura típica é o voto de um município comum do grupo. Ela mostra a parte de cada
          partido nos votos válidos.
        </p>
        {separacao !== null ? (
          <p>
            {separacao} Perto de 0, os grupos se misturam. Perto de 1, cada grupo vota de um jeito
            próprio.
          </p>
        ) : null}
        {dados.buscou ? null : <p>Você fixou o número de grupos na consulta.</p>}
        {maisLugares && maisPeso ? (
          <p>
            {maisLugares.numero === maisPeso.numero
              ? `O grupo ${maisLugares.numero} é o maior: tem mais municípios e mais votantes.`
              : `O grupo ${maisLugares.numero} tem mais municípios. O grupo ${maisPeso.numero} tem mais votantes.`}
          </p>
        ) : null}
        <ul className="flex flex-col gap-1">
          {dados.grupos.map((grupo) => (
            <li key={grupo.numero}>{leituraDoGrupo(dados.partidos, grupo)}</li>
          ))}
        </ul>
      </div>
      <section aria-labelledby="perfis-grupos" className="flex flex-col gap-3">
        <h2 id="perfis-grupos" className="leitura-titulo text-2xl">
          Grupos
        </h2>
        <GraficoPerfis partidos={dados.partidos} grupos={dados.grupos} />
        <div className="flex max-w-3xl flex-col gap-1 text-sm text-muted-foreground">
          <p>
            A tabela traz todos os partidos. Municípios conta os lugares do grupo. Comparecimento
            soma quem votou neles. A cor mais forte marca a maior fatia.
          </p>
          {dados.com_cedula ? (
            <p>Branco e nulo, nas últimas colunas, são a parte deles sobre quem compareceu.</p>
          ) : null}
        </div>
        <TabelaGruposPerfis
          partidos={dados.partidos}
          comCedula={dados.com_cedula}
          grupos={dados.grupos}
        />
      </section>
      <section aria-labelledby="perfis-municipios" className="flex flex-col gap-3">
        <h2 id="perfis-municipios" className="leitura-titulo text-2xl">
          Municípios
        </h2>
        <p className="max-w-3xl text-sm text-muted-foreground">
          Esta lista diz em qual grupo cada município entrou. O filtro de UF só esconde linhas. Os
          grupos não mudam.
        </p>
        <MunicipiosPerfis municipios={dados.municipios} />
      </section>
      <NotasRelatorio notas={dados.notas.map((nota) => NOTAS_CLARAS[nota] ?? nota)} />
    </div>
  );
}

function subtitulo(dados: RelatorioPerfis): string {
  const cargo = rotuloCargoPerfil(dados.cargo);
  const base = `${cargo} · ${dados.ano} · turno ${dados.turno} · ${dados.grupos.length} grupos`;
  return dados.buscou ? base : `${base} escolhidos`;
}

function extremo(
  grupos: readonly GrupoPerfil[],
  campo: "municipios" | "comparecimento",
): GrupoPerfil | null {
  return grupos.reduce<GrupoPerfil | null>((melhor, grupo) => {
    if (melhor === null || grupo[campo] > melhor[campo]) {
      return grupo;
    }
    return melhor;
  }, null);
}

function leituraDoGrupo(partidos: readonly number[], grupo: GrupoPerfil): string {
  const base = `Grupo ${grupo.numero}: ${formatarInteiro(grupo.municipios)} municípios e ${formatarInteiro(grupo.comparecimento)} votantes.`;
  const lider = liderDe(partidos, grupo);
  if (lider === null) {
    return base;
  }
  return `${base} Lidera o partido ${lider.partido}, com ${lider.texto} dos votos válidos.`;
}
