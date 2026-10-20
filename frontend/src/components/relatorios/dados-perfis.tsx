import { ErroRelatorio } from "@/components/relatorios/erro-relatorio";
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
import { lerFatia } from "@/lib/fatia";
import { formatarInteiro } from "@/lib/fracao";
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
  const separacao = lerDecimal(dados.silhueta);
  return (
    <div className="flex flex-col gap-10">
      <div className="flex max-w-3xl flex-col gap-3">
        <p className="text-sm text-muted-foreground">{subtitulo(dados)}</p>
        <p>Os municípios que votaram de um jeito parecido para {nomeCargo} ficam no mesmo grupo.</p>
        <p>
          Em cada linha, Municípios conta os lugares. Comparecimento soma quem votou neles e mostra
          o peso do grupo. O percentual de cada número é a mistura típica: a parte daquele partido
          nos votos válidos.
        </p>
        <p>A cor mais forte marca a maior fatia da tabela.</p>
        {dados.com_cedula ? (
          <p>Branco e nulo, nas últimas colunas, são a parte deles sobre quem compareceu.</p>
        ) : (
          <p>As colunas são só os partidos.</p>
        )}
        {dados.buscou && separacao !== null ? (
          <p>
            A separação entre os grupos é {dados.silhueta}. Zero significa que os grupos se
            misturam. Um significa que eles ficam separados.{" "}
            {separacao < 0.5
              ? "Este valor fica mais perto de zero: os grupos se parecem entre si."
              : "Este valor fica mais perto de um: os grupos se separam."}
          </p>
        ) : null}
        {dados.buscou ? null : <p>O número de grupos foi fixado na consulta.</p>}
        {maisLugares && maisPeso ? (
          <p>
            {maisLugares.numero === maisPeso.numero
              ? `O grupo ${maisLugares.numero} reúne mais municípios e concentra quem votou.`
              : `O grupo ${maisLugares.numero} reúne mais municípios. O grupo ${maisPeso.numero} concentra quem votou.`}
          </p>
        ) : null}
        <ul className="flex flex-col gap-1">
          {dados.grupos.map((grupo) => (
            <li key={grupo.numero}>{leituraDoGrupo(dados.partidos, grupo)}</li>
          ))}
        </ul>
        <p>
          A lista de baixo diz em qual grupo cada lugar entrou. A UF só esconde linhas. Ela não
          monta os grupos de novo.
        </p>
      </div>
      <section aria-labelledby="perfis-grupos" className="flex flex-col gap-3">
        <h2 id="perfis-grupos" className="leitura-titulo text-2xl">
          Grupos
        </h2>
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
  const base = `Grupo ${grupo.numero}: ${formatarInteiro(grupo.municipios)} municípios, ${formatarInteiro(grupo.comparecimento)} compareceram.`;
  const lider = partidoMaior(partidos, grupo.centro);
  if (lider === null) {
    return base;
  }
  return `${base} O partido ${lider.partido} fica com ${lider.texto}.`;
}

function partidoMaior(
  partidos: readonly number[],
  centro: readonly string[],
): { partido: number; texto: string } | null {
  let melhorPartido = 0;
  let melhorTexto = "";
  let melhorValor = -1;
  for (let indice = 0; indice < partidos.length; indice += 1) {
    const partido = partidos[indice];
    const texto = centro[indice];
    if (partido === undefined || texto === undefined) {
      continue;
    }
    const valor = lerFatia(texto);
    if (valor === null || valor <= melhorValor) {
      continue;
    }
    melhorPartido = partido;
    melhorTexto = texto;
    melhorValor = valor;
  }
  if (melhorValor < 0) {
    return null;
  }
  return { partido: melhorPartido, texto: melhorTexto };
}

function lerDecimal(texto: string | null): number | null {
  if (texto === null) {
    return null;
  }
  const corpo = texto.trim().replace(",", ".");
  if (!/^\d+(?:\.\d+)?$/.test(corpo)) {
    return null;
  }
  const valor = Number(corpo);
  return Number.isFinite(valor) ? valor : null;
}
