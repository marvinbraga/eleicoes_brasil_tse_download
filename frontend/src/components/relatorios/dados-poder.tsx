import { ErroRelatorio } from "@/components/relatorios/erro-relatorio";
import { ExplicacaoPoder } from "@/components/relatorios/explicacao-poder";
import { GraficoPoder } from "@/components/relatorios/grafico-poder";
import { TabelaPoder } from "@/components/relatorios/tabela-poder";
import { buscarGrade } from "@/lib/buscar-relatorios";
import {
  nomeUf,
  rotuloCargoPoder,
  rotuloNivel,
  UFS,
  ufDeConsulta,
  type Ano,
  type CargoPoder,
  type Nivel,
  type Turno,
  type UfFiltro,
} from "@/lib/eleicoes";
import { formatarInteiro } from "@/lib/fracao";
import { fatiasPoder, leituraPoder, liderancasPoder } from "@/lib/grafico-poder";
import { linhasVisiveis, type LinhaGrade } from "@/lib/relatorios";

type DadosPoderProps = {
  ano: Ano;
  turno: Turno;
  uf: UfFiltro;
  cargo: CargoPoder;
  nivel: Nivel;
};

export async function DadosPoder({ ano, turno, uf, cargo, nivel }: DadosPoderProps) {
  const resultado = await buscarGrade(ano, turno, ufDeConsulta(uf), cargo, nivel);
  if (!resultado.ok) {
    return <ErroRelatorio detalhe={resultado.detalhe} />;
  }
  const grade = resultado.dados;
  const apoio = `${rotuloCargoPoder(cargo)}, ${rotuloNivel(nivel).toLowerCase()}, ${ano}, turno ${turno}`;
  const visiveis = linhasVisiveis(grade.linhas, nivel, uf);
  const grupos = nivel === "municipio" ? gruposPorUf(visiveis) : [{ uf: "", linhas: visiveis }];
  const liderancas = liderancasPoder(visiveis);
  return (
    <div className="flex flex-col gap-10">
      <ExplicacaoPoder nivel={nivel} frases={leituraPoder(visiveis)} />
      <div className="flex flex-col gap-6">
        <GraficoPoder
          id="grafico-poder-fatias"
          titulo="Parte de cada partido nos votos válidos"
          introducao={`Parte de cada partido no total de votos válidos do recorte (${apoio}).`}
          legenda="Soma de todos os lugares do recorte, do maior para o menor. Os partidos menores entram juntos em Outros, sempre por último."
          itens={fatiasPoder(visiveis)}
        />
        {liderancas.lugares > 1 ? (
          <GraficoPoder
            id="grafico-poder-liderancas"
            titulo="Votos dos lugares em que cada partido lidera"
            introducao={`Parte dos votos válidos do recorte que está nos lugares em que cada partido ficou em primeiro, entre ${formatarInteiro(liderancas.lugares)} lugares.`}
            legenda={
              liderancas.empates > 0
                ? "Cada barra soma os votos válidos de todos os partidos nos lugares em que o partido ficou em primeiro, como parte do total do recorte. Assim, uma capital pesa mais que uma cidade pequena. Lugares com empate no topo não contam para ninguém."
                : "Cada barra soma os votos válidos de todos os partidos nos lugares em que o partido ficou em primeiro, como parte do total do recorte. Assim, uma capital pesa mais que uma cidade pequena."
            }
            itens={liderancas.itens}
          />
        ) : null}
      </div>
      {grupos.map((grupo) => (
        <TabelaPoder
          key={grupo.uf === "" ? "recorte" : grupo.uf}
          titulo={grupo.uf === "" ? rotuloNivel(nivel) : nomeUf(grupo.uf)}
          apoio={apoio}
          colunas={grade.colunas}
          linhas={grupo.linhas}
          escala={grade.linhas}
        />
      ))}
    </div>
  );
}

function gruposPorUf(linhas: readonly LinhaGrade[]): { uf: string; linhas: LinhaGrade[] }[] {
  const mapa = new Map<string, LinhaGrade[]>();
  for (const linha of linhas) {
    const sigla = siglaDoNome(linha.nome);
    const grupo = mapa.get(sigla);
    if (grupo === undefined) {
      mapa.set(sigla, [linha]);
    } else {
      grupo.push(linha);
    }
  }
  const ordem = UFS.map((item) => item.value);
  return [...mapa.keys()]
    .sort((esquerda, direita) => posicao(ordem, esquerda) - posicao(ordem, direita))
    .map((sigla) => ({ uf: sigla, linhas: mapa.get(sigla) ?? [] }));
}

function siglaDoNome(nome: string): string {
  const encontrado = / \(([A-Z]{2})\)$/.exec(nome);
  return encontrado?.[1] ?? "";
}

function posicao(ordem: readonly string[], sigla: string): number {
  const indice = ordem.indexOf(sigla);
  return indice < 0 ? ordem.length : indice;
}
