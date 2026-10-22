import { ErroRelatorio } from "@/components/relatorios/erro-relatorio";
import { GraficoPoder } from "@/components/relatorios/grafico-poder";
import { NotasRelatorio } from "@/components/relatorios/notas-relatorio";
import {
  Table,
  TableBody,
  TableCaption,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { buscarMunicipais2024 } from "@/lib/buscar-relatorios";
import { formatarInteiro } from "@/lib/fracao";
import {
  MEDIDAS_MUNICIPAIS,
  formatarCorte,
  itensEleitorado,
  itensPrefeituras,
  itensVereadores,
  leituraMunicipais,
  rotuloBarra,
  type MunicipioMunicipal,
  type PartidoMunicipal,
  type PrefeitoMunicipal,
  type RelatorioMunicipais,
} from "@/lib/municipais-2024";

type DadosMunicipais2024Props = {
  uf: string | null;
};

export async function DadosMunicipais2024({ uf }: DadosMunicipais2024Props) {
  const resultado = await buscarMunicipais2024(uf);
  if (!resultado.ok) {
    return <ErroRelatorio detalhe={resultado.detalhe} />;
  }
  const dados = resultado.dados;
  const recorte = dados.uf === null ? "no Brasil" : `em ${dados.uf}`;
  return (
    <div className="flex flex-col gap-10">
      <Explicacao corte={formatarCorte(dados.data_corte)} />
      <section
        aria-labelledby="resumo-municipais"
        className="flex max-w-3xl flex-col gap-2 rounded-md border border-border px-4 py-3"
      >
        <h2 id="resumo-municipais" className="font-semibold">
          Em resumo
        </h2>
        <ul className="flex list-disc flex-col gap-1 pl-5">
          {leituraMunicipais(dados).map((frase) => (
            <li key={frase}>{frase}</li>
          ))}
        </ul>
      </section>
      <GraficoPoder
        id="municipais-prefeituras"
        titulo="Prefeituras por partido"
        introducao={`Prefeituras por partido ${recorte}, de ${formatarInteiro(dados.totais.com_prefeito)} com prefeito eleito.`}
        legenda="Cada barra é um partido, com a sigla e o número de 2024. A porcentagem é sobre os municípios com prefeito eleito."
        itens={itensPrefeituras(dados)}
        medidas={MEDIDAS_MUNICIPAIS}
      />
      <GraficoPoder
        id="municipais-eleitorado"
        titulo="Eleitorado governado por partido"
        introducao={`Eleitorado dos municípios governados por partido ${recorte}, de ${formatarInteiro(dados.totais.eleitorado)} eleitores aptos.`}
        legenda="Soma do eleitorado apto de 2024 dos municípios onde o partido tem o prefeito. Não é população."
        itens={itensEleitorado(dados)}
        medidas={MEDIDAS_MUNICIPAIS}
      />
      <GraficoPoder
        id="municipais-vereadores"
        titulo="Vereadores eleitos por partido"
        introducao={`Vereadores eleitos por partido ${recorte}, de ${formatarInteiro(dados.totais.vereadores)} eleitos.`}
        legenda="Conta o partido do candidato, não a federação nem a coligação."
        itens={itensVereadores(dados)}
        medidas={MEDIDAS_MUNICIPAIS}
      />
      <TabelaPartidos dados={dados} />
      {dados.uf !== null ? <TabelaMunicipios uf={dados.uf} municipios={dados.municipios} /> : null}
      <NotasRelatorio notas={dados.notas} />
    </div>
  );
}

function Explicacao({ corte }: { corte: string }) {
  return (
    <section
      aria-labelledby="explicacao-municipais"
      className="flex max-w-3xl flex-col gap-2 text-sm text-muted-foreground"
    >
      <h2 id="explicacao-municipais" className="font-semibold text-foreground">
        Como ler
      </h2>
      <p>
        Uma prefeitura conta para o partido do prefeito eleito que está no cargo segundo o TSE. O
        eleitorado governado é a soma do eleitorado apto do 1º turno de 2024 nos municípios onde o
        partido tem o prefeito; não é a população. Vereador eleito é quem foi eleito por quociente
        partidário ou por média, contado pelo partido do candidato.
      </p>
      <p>
        Os dados refletem a situação divulgada pelo TSE em {corte}. O TSE regrava os arquivos: um
        prefeito cassado deixa de constar como eleito, e quem venceu a eleição suplementar passa a
        contar no lugar dele. Por isso não é o resultado da noite de 6 de outubro de 2024.
      </p>
    </section>
  );
}

function siglaEm2026(partido: PartidoMunicipal): string {
  return partido.sigla_2026 ?? "Sem correspondência";
}

function TabelaPartidos({ dados }: { dados: RelatorioMunicipais }) {
  return (
    <section aria-labelledby="tabela-partidos-municipais" className="flex flex-col gap-3">
      <h2 id="tabela-partidos-municipais" className="text-xl font-semibold">
        Partidos
      </h2>
      <Table containerClassName="folha">
        <TableCaption className="sr-only">Prefeituras, eleitorado governado e vereadores por partido</TableCaption>
        <TableHeader>
          <TableRow>
            <TableHead scope="col">Partido (2024)</TableHead>
            <TableHead scope="col">Em 2026</TableHead>
            <TableHead scope="col" className="text-right">Prefeituras</TableHead>
            <TableHead scope="col" className="text-right">Eleitorado governado</TableHead>
            <TableHead scope="col" className="text-right">Vereadores</TableHead>
            <TableHead scope="col" className="text-right">Municípios com vereador</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {dados.partidos.map((partido) => (
            <TableRow key={partido.numero}>
              <TableHead scope="row" className="h-auto p-2 text-left font-normal">
                {rotuloBarra(partido)}
                {partido.nota !== "" ? (
                  <span className="block text-xs whitespace-normal text-muted-foreground">
                    {partido.nota}
                  </span>
                ) : null}
              </TableHead>
              <TableCell>{siglaEm2026(partido)}</TableCell>
              <TableCell className="text-right tabular-nums">{formatarInteiro(partido.prefeitos)}</TableCell>
              <TableCell className="text-right tabular-nums">
                {formatarInteiro(partido.eleitorado_governado)}
              </TableCell>
              <TableCell className="text-right tabular-nums">{formatarInteiro(partido.vereadores)}</TableCell>
              <TableCell className="text-right tabular-nums">
                {formatarInteiro(partido.municipios_com_vereador)}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </section>
  );
}

function descricaoPrefeito(prefeito: PrefeitoMunicipal | null): string {
  if (prefeito === null) {
    return "Sem prefeito eleito";
  }
  const marcas = [
    prefeito.suplementar ? "suplementar" : null,
    prefeito.turno === 2 ? "2º turno" : null,
  ].filter((marca) => marca !== null);
  const base = `${prefeito.sigla_2024} · ${prefeito.nome_urna}`;
  return marcas.length > 0 ? `${base} (${marcas.join(", ")})` : base;
}

function TabelaMunicipios({ uf, municipios }: { uf: string; municipios: readonly MunicipioMunicipal[] }) {
  return (
    <section aria-labelledby="tabela-municipios-municipais" className="flex flex-col gap-3">
      <h2 id="tabela-municipios-municipais" className="text-xl font-semibold">
        Municípios de {uf}
      </h2>
      <Table containerClassName="folha">
        <TableCaption className="sr-only">Prefeito e vereadores eleitos por município em {uf}</TableCaption>
        <TableHeader>
          <TableRow>
            <TableHead scope="col">Município</TableHead>
            <TableHead scope="col" className="text-right">Eleitorado</TableHead>
            <TableHead scope="col">Prefeito</TableHead>
            <TableHead scope="col">Vereadores</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {municipios.map((municipio) => (
            <TableRow key={municipio.codigo_tse}>
              <TableHead scope="row" className="h-auto p-2 text-left font-normal">
                {municipio.nome}
              </TableHead>
              <TableCell className="text-right tabular-nums">{formatarInteiro(municipio.eleitorado)}</TableCell>
              <TableCell className={municipio.prefeito === null ? "text-muted-foreground" : undefined}>
                {descricaoPrefeito(municipio.prefeito)}
              </TableCell>
              <TableCell className="whitespace-normal">
                {municipio.vereadores
                  .map((item) => `${item.sigla_2024} ${formatarInteiro(item.eleitos)}`)
                  .join(", ")}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </section>
  );
}
