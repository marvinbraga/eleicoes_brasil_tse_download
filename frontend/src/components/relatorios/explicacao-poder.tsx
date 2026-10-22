import type { Nivel } from "@/lib/eleicoes";

const LUGAR: Record<Nivel, string> = {
  municipio: "um município",
  uf: "uma UF",
  regiao: "uma região",
  pais: "o país inteiro",
};

type ExplicacaoPoderProps = {
  nivel: Nivel;
  frases: readonly string[];
};

export function ExplicacaoPoder({ nivel, frases }: ExplicacaoPoderProps) {
  return (
    <div className="flex max-w-3xl flex-col gap-3">
      <p>
        Este relatório mostra como os votos válidos se dividem entre os partidos em cada lugar do
        recorte.
      </p>
      <dl className="flex flex-col gap-2">
        <div>
          <dt className="font-medium">Linhas</dt>
          <dd className="text-muted-foreground">
            Cada linha da tabela é um lugar. Neste nível, cada lugar é {LUGAR[nivel]}.
          </dd>
        </div>
        <div>
          <dt className="font-medium">Colunas</dt>
          <dd className="text-muted-foreground">
            &ldquo;Votos válidos&rdquo; é o total do lugar. Cada coluna com número é um partido,
            pelo número dele na urna.
          </dd>
        </div>
        <div>
          <dt className="font-medium">Votos válidos</dt>
          <dd className="text-muted-foreground">
            São os votos dados a um candidato ou só ao número do partido (voto de legenda). Votos
            brancos e nulos não entram.
          </dd>
        </div>
        <div>
          <dt className="font-medium">Percentual e cor</dt>
          <dd className="text-muted-foreground">
            Cada célula mostra a parte dos votos válidos do lugar que foi para o partido. Quanto
            mais forte a cor, maior essa parte. A cor mais forte é a maior parte de toda a consulta,
            que pode incluir lugares fora desta lista, e as outras são proporcionais a ela. A cor
            não diz quem venceu: compare as células da mesma linha.
          </dd>
        </div>
      </dl>
      <p>
        Como ler: o primeiro gráfico soma todos os lugares do recorte e mostra a parte de cada
        partido no total. Nas tabelas, o maior percentual de uma linha é o partido que lidera
        naquele lugar. Clique num cabeçalho para ordenar e passe o mouse sobre uma célula para ver
        os votos.
      </p>
      {frases.length > 0 ? (
        <div className="flex flex-col gap-1">
          <p className="font-medium">Leitura deste recorte</p>
          <ul className="flex list-disc flex-col gap-1 pl-5">
            {frases.map((frase) => (
              <li key={frase}>{frase}</li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}
