import { ErroRelatorio } from "@/components/relatorios/erro-relatorio";
import { GraficoPresidenteGovernador } from "@/components/relatorios/grafico-presidente-governador";
import { SecaoComposicao } from "@/components/relatorios/secao-composicao";
import { SecaoLeitura } from "@/components/relatorios/secao-leitura";
import { buscarCruzamento } from "@/lib/buscar-relatorios";
import {
  nomeUf,
  UF_TODAS,
  ufDeConsulta,
  type Ano,
  type Turno,
  type UfFiltro,
} from "@/lib/eleicoes";
import type { GrupoMunicipios } from "@/lib/relatorios";

const FRASE_RECORTE =
  "O filtro de UF muda só a lista de municípios abaixo. A composição, os gráficos e as tabelas por estado, por região e do país sempre reúnem todos os lugares apurados.";

type DadosPresidenteGovernadorProps = {
  ano: Ano;
  turno: Turno;
  uf: UfFiltro;
};

export async function DadosPresidenteGovernador({
  ano,
  turno,
  uf,
}: DadosPresidenteGovernadorProps) {
  const resultado = await buscarCruzamento(ano, turno, ufDeConsulta(uf));
  if (!resultado.ok) {
    return <ErroRelatorio detalhe={resultado.detalhe} />;
  }
  const dados = resultado.dados;
  const pais = dados.country === null ? [] : [dados.country];
  const apoio = `${ano}, turno ${turno}`;
  return (
    <div className="flex flex-col gap-10">
      <SecaoComposicao composicao={dados.composition} />
      <GraficoPresidenteGovernador grupos={dados.municipalities} />
      <p className="text-sm text-muted-foreground">{FRASE_RECORTE}</p>
      {secoesMunicipio(dados.municipalities, uf, apoio)}
      <SecaoLeitura id="estado" titulo="Por estado" apoio={apoio} lugares={dados.states} />
      <SecaoLeitura id="regiao" titulo="Por região" apoio={apoio} lugares={dados.regions} />
      <SecaoLeitura id="pais" titulo="No país" apoio={apoio} lugares={pais} />
    </div>
  );
}

function secoesMunicipio(
  grupos: readonly GrupoMunicipios[],
  uf: UfFiltro,
  apoio: string,
) {
  const visiveis = uf === UF_TODAS ? grupos : grupos.filter((grupo) => grupo.uf === uf);
  if (visiveis.length === 0) {
    return (
      <SecaoLeitura
        id={`municipio-${uf}`}
        titulo={uf === UF_TODAS ? "Todas" : nomeUf(uf)}
        apoio={`Por município, ${apoio}`}
        lugares={[]}
      />
    );
  }
  return visiveis.map((grupo) => (
    <SecaoLeitura
      key={grupo.uf}
      id={`municipio-${grupo.uf}`}
      titulo={nomeUf(grupo.uf)}
      apoio={`Por município, ${apoio}`}
      lugares={grupo.places}
    />
  ));
}
