export function ExplicacaoCadeiras() {
  return (
    <section
      aria-labelledby="como-ler-cadeiras"
      className="flex max-w-3xl flex-col gap-3"
    >
      <h2 id="como-ler-cadeiras" className="text-xl font-semibold">
        Como a estimativa é feita
      </h2>
      <p>
        Os votos de cada número de candidato foram somados nos boletins de urna do 1º turno. Com
        eles, a página refaz as contas da Justiça Eleitoral para cada UF.
      </p>
      <ul className="flex list-disc flex-col gap-1 pl-5">
        <li>
          <strong>Câmara e Assembleias.</strong> O quociente eleitoral é o total de votos válidos
          (nominais e de legenda) dividido pelas vagas da UF. Cada partido ou federação leva tantas
          vagas quantas vezes alcança o quociente, desde que o candidato tenha pelo menos 10% do
          quociente. As vagas que sobram vão pelas maiores médias: primeiro entre as legendas com
          80% do quociente e candidato com 20%; depois entre todas.
        </li>
        <li>
          <strong>Federação.</strong> Partidos federados disputam como uma lista só. A cadeira fica
          com o partido do número do candidato eleito.
        </li>
        <li>
          <strong>Senado.</strong> Em 2026 cada UF elege dois senadores: os dois mais votados.
        </li>
        <li>
          <strong>Governador.</strong> Quem passa da metade dos votos válidos se elege no 1º turno.
          Senão, os dois mais votados vão ao 2º turno.
        </li>
      </ul>
      <p>
        <strong>Por que é estimativa.</strong> O boletim de urna não diz se o registro do candidato
        foi indeferido. Na totalização oficial esses votos são anulados; aqui eles contam. O boletim
        também não traz a idade, que desempata candidatos. E, quando duas listas empatam na média,
        nos votos e nos votos do próximo candidato, a estimativa fica com a de menor código.
        Resultados que dependem de um desses empates aparecem marcados. Por fim, a lista de federações é a cadastrada no projeto e pode estar
        desatualizada.
      </p>
    </section>
  );
}
