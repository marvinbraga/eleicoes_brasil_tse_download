import type { RelatorioCapilaridade } from "@/lib/capilaridade";

type ExplicacaoCapilaridadeProps = {
  dados: RelatorioCapilaridade;
};

function limite(dados: RelatorioCapilaridade, chave: string): string {
  const valor = dados.limites[chave];
  return valor === undefined ? "—" : String(valor);
}

export function ExplicacaoCapilaridade({ dados }: ExplicacaoCapilaridadeProps) {
  const estadual = dados.cargo !== "presidente";
  return (
    <section aria-labelledby="como-ler-capilaridade" className="folha-quieta max-w-3xl space-y-3">
      <h2 id="como-ler-capilaridade" className="text-xl font-semibold">
        Como ler a capilaridade
      </h2>
      <p>
        A fatia de um partido num município é a parte dos votos válidos dali que ele recebeu. A fatia
        média é a fatia dele somando todos os municípios em que é medido.
      </p>
      <p>
        As faixas comparam cada município com essa média. &quot;3+&quot; quer dizer municípios onde o
        partido teve três vezes a sua fatia média ou mais; &quot;&lt;½&quot;, menos da metade dela; e
        &quot;0&quot;, nenhum voto.
      </p>
      <p>
        O índice de concentração vai de 0 a 100. 0 quer dizer que o partido teve a mesma fatia em todo
        município. Perto de 100 quer dizer que quase todos os votos vieram de um pedaço pequeno do
        eleitorado.
      </p>
      <p>
        Os 10% mais fortes são os municípios onde a fatia do partido é maior. Ao lado da parte dos
        votos que eles deram vem a parte do eleitorado que eles têm: é essa a base de comparação.
      </p>
      <dl className="space-y-2">
        <div>
          <dt className="font-medium">Pouco voto</dt>
          <dd className="text-muted-foreground">
            Fatia abaixo de {limite(dados, "pouco_voto")} onde recebeu voto. Fica fora do ranking.
          </dd>
        </div>
        <div>
          <dt className="font-medium">Poucos municípios para classificar</dt>
          <dd className="text-muted-foreground">
            Menos de {limite(dados, "minimo_municipios")} municípios com voto válido. Fica fora do
            ranking.
          </dd>
        </div>
        <div>
          <dt className="font-medium">Concentrado nas capitais</dt>
          <dd className="text-muted-foreground">
            As capitais deram pelo menos {limite(dados, "capitais_vezes")} vezes o peso delas no
            eleitorado.
          </dd>
        </div>
        <div>
          <dt className="font-medium">Regional ou concentrado em uma UF</dt>
          <dd className="text-muted-foreground">
            Uma região (no Brasil) ou uma UF (numa região) deu pelo menos{" "}
            {limite(dados, "regional_parte")} dos votos do partido, com {limite(dados, "regional_vezes")}{" "}
            vezes ou mais o peso dela no eleitorado.
          </dd>
        </div>
        <div>
          <dt className="font-medium">Concentrado em poucos municípios</dt>
          <dd className="text-muted-foreground">
            Os 10% mais fortes deram pelo menos {limite(dados, "poucos_parte")} dos votos, com{" "}
            {limite(dados, "poucos_vezes")} vezes ou mais o peso deles no eleitorado.
          </dd>
        </div>
        <div>
          <dt className="font-medium">Espalhado</dt>
          <dd className="text-muted-foreground">
            Nenhuma das regras acima se aplicou. As regras são testadas nesta ordem, e a primeira que
            vale decide. Presença é ter pelo menos {limite(dados, "presenca")} dos votos no município.
          </dd>
        </div>
      </dl>
      {estadual ? (
        <p className="text-sm">
          Em governador, senador e deputados, o partido é medido só nas UFs onde recebeu voto.
        </p>
      ) : null}
      <ul className="list-disc space-y-1 pl-5 text-sm text-muted-foreground">
        {dados.notas.map((nota) => (
          <li key={nota}>{nota}</li>
        ))}
      </ul>
    </section>
  );
}
