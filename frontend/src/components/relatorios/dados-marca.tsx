import { ErroRelatorio } from "@/components/relatorios/erro-relatorio";
import { ExplicacaoMarca } from "@/components/relatorios/explicacao-marca";
import { GraficoMarca } from "@/components/relatorios/grafico-marca";
import { GraficoMarcaCargos } from "@/components/relatorios/grafico-marca-cargos";
import { TabelaMarca } from "@/components/relatorios/tabela-marca";
import { TabelaMarcaUf } from "@/components/relatorios/tabela-marca-uf";
import { buscarGrade, type Resultado } from "@/lib/buscar-relatorios";
import type { Ano, Turno } from "@/lib/eleicoes";
import {
  CARGOS_MARCA,
  comparacaoCargos,
  leituraMarca,
  marcaDoCargo,
  type CargoMarca,
  type MarcaCargo,
} from "@/lib/grafico-marca";
import type { GradeRelatorio } from "@/lib/relatorios";

const ANO = "2026" as const satisfies Ano;
const TURNO = "1" as const satisfies Turno;
// The UF only anchors validation: at nivel=uf the API returns every UF of the office.
const UF_ANCORA = "AC";

const TITULOS: Record<CargoMarca, string> = {
  deputadoFederal: "Deputado federal",
  deputadoEstadual: "Deputado estadual",
};

export async function DadosMarca() {
  const [respostaFederal, respostaEstadual] = await Promise.all(
    CARGOS_MARCA.map((cargo) => buscarGrade(ANO, TURNO, UF_ANCORA, cargo, "uf")),
  );
  if (!respostaFederal.ok && !respostaEstadual.ok) {
    return <ErroRelatorio detalhe={respostaFederal.detalhe} />;
  }
  const federal = respostaFederal.ok
    ? marcaDoCargo("deputadoFederal", respostaFederal.dados)
    : null;
  const estadual = respostaEstadual.ok
    ? marcaDoCargo("deputadoEstadual", respostaEstadual.dados)
    : null;
  // Without party votes in an office its multiples are undefined, so there is nothing to compare.
  const pares =
    federal !== null && estadual !== null && federal.legenda > 0 && estadual.legenda > 0
      ? comparacaoCargos(federal, estadual).pares
      : [];
  return (
    <div className="flex flex-col gap-10">
      <ExplicacaoMarca frases={leituraMarca(federal, estadual)} />
      <SecaoCargo cargo="deputadoFederal" resposta={respostaFederal} marca={federal} />
      <SecaoCargo cargo="deputadoEstadual" resposta={respostaEstadual} marca={estadual} />
      {pares.length > 0 ? <GraficoMarcaCargos pares={pares} /> : null}
    </div>
  );
}

type SecaoCargoProps = {
  cargo: CargoMarca;
  resposta: Resultado<GradeRelatorio>;
  marca: MarcaCargo | null;
};

function SecaoCargo({ cargo, resposta, marca }: SecaoCargoProps) {
  const idTitulo = `marca-${cargo}`;
  return (
    <section aria-labelledby={idTitulo} className="flex flex-col gap-4">
      <h2 id={idTitulo} className="leitura-titulo text-xl">
        {TITULOS[cargo]}
      </h2>
      {!resposta.ok ? (
        <ErroRelatorio detalhe={resposta.detalhe} />
      ) : marca === null ? (
        <p className="text-sm text-muted-foreground">Sem votos gravados para este cargo.</p>
      ) : (
        <>
          <GraficoMarca id={`grafico-marca-${cargo}`} marca={marca} />
          <TabelaMarca marca={marca} />
          <TabelaMarcaUf marca={marca} />
        </>
      )}
    </section>
  );
}
