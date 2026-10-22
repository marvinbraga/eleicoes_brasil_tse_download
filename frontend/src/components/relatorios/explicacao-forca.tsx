import { CARGOS_PODER } from "@/lib/eleicoes";
import { LIMIAR_PADRAO } from "@/lib/forca";
import { ROTULOS_ESFERA, colunasPlacar } from "@/lib/placar-forca";

type ExplicacaoForcaProps = {
  cargo: string;
  // Fases B e C: falso quando a resposta trouxer os blocos de cadeiras e de 2024.
  semSimulacoes?: boolean;
};

export function ExplicacaoForca({ cargo, semSimulacoes = true }: ExplicacaoForcaProps) {
  const colunas = colunasPlacar(LIMIAR_PADRAO, "pais");
  const rotulo = CARGOS_PODER.find((item) => item.value === cargo)?.label.toLowerCase() ?? cargo;
  return (
    <section aria-labelledby="como-ler-forca" className="folha-quieta max-w-3xl space-y-3">
      <h2 id="como-ler-forca" className="text-xl font-semibold">
        Como ler o placar
      </h2>
      <p>
        Cada partido aparece em três esferas: {ROTULOS_ESFERA.nacional}, {ROTULOS_ESFERA.estados} e{" "}
        {ROTULOS_ESFERA.municipios}. Elas ficam lado a lado e não são somadas num índice único, porque
        medem coisas diferentes: parte dos votos, UFs e municípios. Os indicadores municipais usam o
        cargo de referência escolhido, hoje {rotulo}.
      </p>
      <dl className="space-y-2">
        {colunas.map((coluna) => (
          <div key={coluna.chave}>
            <dt className="font-medium">
              {coluna.chave === "presenca" ? "Presença (≥ limiar)" : coluna.titulo}
            </dt>
            <dd className="text-muted-foreground">{coluna.explicacao}</dd>
          </div>
        ))}
      </dl>
      <ul className="list-disc space-y-1 pl-5 text-sm">
        <li>Votos válidos são nominais mais legenda, sem brancos e nulos.</li>
        <li>Empate no topo não conta para nenhum partido.</li>
        <li>O exterior entra só no % nacional de presidente.</li>
        <li>
          O DF elege deputados distritais, que não estão nos dados; por isso fica fora das colunas de
          deputado estadual e, com esse cargo de referência, dos indicadores municipais.
        </li>
        <li>— significa sem dados: cargo não gravado, partido que não concorreu ao cargo ou lugar sem esse cargo.</li>
      </ul>
      {semSimulacoes ? (
        <p className="text-sm text-muted-foreground">
          Cadeiras, governadores e prefeituras entram quando as simulações estiverem disponíveis.
        </p>
      ) : null}
    </section>
  );
}
