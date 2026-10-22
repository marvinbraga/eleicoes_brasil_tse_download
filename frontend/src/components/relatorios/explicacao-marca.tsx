import { formatarInteiro } from "@/lib/fracao";
import { MINIMO_VOTOS_RANKING } from "@/lib/grafico-marca";

type ExplicacaoMarcaProps = {
  frases: readonly string[];
};

const TERMOS = [
  {
    termo: "O que é voto de legenda",
    texto:
      "Para deputado, o eleitor pode digitar o número inteiro de um candidato (4 dígitos para federal, 5 para estadual). Esse é o voto nominal. Ele também pode digitar só os 2 primeiros dígitos, que são o número do partido, e confirmar. Esse é o voto de legenda. Ele conta para o partido na divisão das cadeiras, mas não ajuda nenhum candidato a subir na lista do partido.",
  },
  {
    termo: "O indicador",
    texto:
      "É o voto de legenda dividido pelo total de votos válidos do partido (nominais mais legenda). Quanto maior, mais o eleitor escolheu o partido e não uma pessoa.",
  },
  {
    termo: "A média do cargo",
    texto:
      "É a mesma conta com todos os partidos juntos. O deputado estadual costuma ter mais voto de legenda que o federal, por isso cada partido é comparado com a média do próprio cargo.",
  },
  {
    termo: "Leitura",
    texto:
      "Marca forte: pelo menos o dobro da média do cargo. Voto na pessoa: no máximo a metade. Entre os dois: perto da média.",
  },
  {
    termo: "Partidos pequenos",
    texto: `Só entram no ranking os partidos com pelo menos ${formatarInteiro(MINIMO_VOTOS_RANKING)} votos no cargo. Um partido com poucos candidatos recebe boa parte do voto na legenda porque o eleitor não tem em quem votar, e isso não é marca forte. Esses partidos aparecem no fim de cada tabela, fora do ranking.`,
  },
  {
    termo: "DF e federações",
    texto:
      "O Distrito Federal elege deputados distritais, não estaduais, e não entra nas contas de deputado estadual. Partidos de uma federação concorrem juntos, mas aqui cada um aparece com o próprio número, porque o voto de legenda vai para o número digitado.",
  },
] as const;

export function ExplicacaoMarca({ frases }: ExplicacaoMarcaProps) {
  return (
    <div className="flex max-w-3xl flex-col gap-3">
      <p>
        Este relatório mostra, para deputado federal e deputado estadual, quanto do voto de cada
        partido foi dado ao partido e não a um candidato.
      </p>
      <dl className="flex flex-col gap-2">
        {TERMOS.map((item) => (
          <div key={item.termo}>
            <dt className="font-medium">{item.termo}</dt>
            <dd className="text-muted-foreground">{item.texto}</dd>
          </div>
        ))}
      </dl>
      <p>
        Como ler: nas barras, cada partido mostra a parte do seu voto que foi de legenda; a linha
        tracejada é a média do cargo. Nos halteres, o círculo cheio é deputado federal e o vazado
        é deputado estadual, medidos em vezes a média de cada cargo. Passe o mouse para ver os
        votos.
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
