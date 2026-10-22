import { CARGOS_PODER } from "@/lib/eleicoes";
import { LIMIAR_PADRAO } from "@/lib/forca";
import { ROTULOS_ESFERA, colunasPlacar, type BlocosPlacar } from "@/lib/placar-forca";

type ExplicacaoForcaProps = {
  cargo: string;
  blocos: BlocosPlacar;
};

export function ExplicacaoForca({ cargo, blocos }: ExplicacaoForcaProps) {
  const colunas = colunasPlacar(blocos, LIMIAR_PADRAO, "pais");
  const cadeiras = blocos.cadeiras !== null;
  const de2024 = blocos.municipal_2024 !== null;
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
        <li>
          O grupo Perfil do voto mostra quanto dos votos do partido para deputado foi só no número do
          partido. Ele fica fora dos gráficos e mostra — nas federações. A linha de totais traz a média
          do cargo, com todos os partidos.
        </li>
        <li>— significa sem dados: cargo não gravado, partido que não concorreu ao cargo ou lugar sem esse cargo.</li>
        {cadeiras ? (
          <>
            <li>
              Cadeiras e governadores vêm da simulação de cadeiras. Nessas colunas, 0 quer dizer que o
              partido não elegeu ninguém.
            </li>
            <li>
              Em &quot;Federações e partidos fora delas&quot;, os votos dos membros de cada federação são
              somados em cada lugar antes de apurar quem lidera, e as lideranças, a presença e os empates de
              todas as linhas são recalculados. As cadeiras da federação já vêm somadas da simulação. A
              linha de totais soma só os partidos e não soma o 2º turno de governador.
            </li>
          </>
        ) : null}
        {de2024 ? (
          <li>
            Prefeituras, eleitorado governado e vereadores vêm da eleição municipal de 2024, já com o número
            de partido de 2026. Nas federações, essas contagens somam os membros. O DF não tem eleição
            municipal e mostra —.
          </li>
        ) : null}
      </ul>
      {cadeiras || de2024 ? null : (
        <p className="text-sm text-muted-foreground">
          Cadeiras, governadores e prefeituras entram quando as simulações estiverem disponíveis.
        </p>
      )}
    </section>
  );
}
