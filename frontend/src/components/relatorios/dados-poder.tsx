import { ErroRelatorio } from "@/components/relatorios/erro-relatorio";
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
  return (
    <div className="flex flex-col gap-10">
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
      <p className="max-w-xl text-sm text-muted-foreground">
        O percentual é o voto do partido sobre os votos válidos do lugar.
      </p>
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
