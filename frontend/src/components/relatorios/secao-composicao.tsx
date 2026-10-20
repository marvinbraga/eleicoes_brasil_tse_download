import {
  definicaoDaClasse,
  estiloDaBarra,
  FRASE_FINALIDADE,
  FRASE_MARGEM,
  fraseDoAchado,
} from "@/cruzamento/finalidade";
import { formatarInteiro, formatarPercentualContagem } from "@/lib/fracao";
import { rotuloClasse, type Composicao } from "@/lib/relatorios";

type SecaoComposicaoProps = {
  composicao: Composicao;
};

export function SecaoComposicao({ composicao }: SecaoComposicaoProps) {
  const achado = fraseDoAchado(composicao);
  return (
    <section aria-labelledby="composicao" className="flex flex-col gap-3">
      <h2 id="composicao" className="leitura-titulo text-2xl">
        Composição dos municípios
      </h2>
      <div className="folha-quieta flex flex-col gap-5">
        <p>{FRASE_FINALIDADE}</p>
        {achado === null ? null : <p>{achado}</p>}
        <p className="text-sm text-muted-foreground">{FRASE_MARGEM}</p>
        <div className="flex h-2 gap-0.5" aria-hidden="true">
          {composicao.classes.map((fatia) => (
            <span
              key={fatia.classe}
              className={votosDaBarra(fatia.votos_validos)}
              style={estiloDaBarra(fatia.classe, fatia.votos_validos)}
            />
          ))}
        </div>
        <div className="grid gap-x-6 gap-y-5 sm:grid-cols-2 lg:grid-cols-4">
          {composicao.classes.map((fatia) => (
            <div key={fatia.classe} className="flex flex-col gap-1">
              <p className="leitura-titulo text-base">{rotuloClasse(fatia.classe)}</p>
              <p className="text-sm text-muted-foreground">
                {definicaoDaClasse(fatia.classe)}
              </p>
              <p className="text-2xl tabular-nums tracking-tight">
                {formatarPercentualContagem(
                  fatia.votos_validos,
                  composicao.votos_validos,
                )}
              </p>
              <p className="text-sm tabular-nums">
                {formatarInteiro(fatia.cidades)} municípios
              </p>
              <p className="text-sm tabular-nums">
                {formatarInteiro(fatia.votos_validos)} votos válidos
              </p>
            </div>
          ))}
        </div>
        <p className="text-sm">
          Brancos de presidente: {formatarInteiro(composicao.branco)}. Nulos de
          presidente: {formatarInteiro(composicao.nulo)}.
        </p>
      </div>
    </section>
  );
}

function votosDaBarra(votos: number): string {
  return votos > 0 ? "h-full min-w-0.5" : "h-full";
}
