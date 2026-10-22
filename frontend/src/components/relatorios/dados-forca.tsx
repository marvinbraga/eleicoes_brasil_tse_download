import { ErroRelatorio } from "@/components/relatorios/erro-relatorio";
import { ExplicacaoForca } from "@/components/relatorios/explicacao-forca";
import { PlacarForcaVista } from "@/components/relatorios/placar-forca";
import { buscarForca } from "@/lib/buscar-relatorios";
import type { Ano, CargoPoder, Turno } from "@/lib/eleicoes";

type DadosForcaProps = {
  ano: Ano;
  turno: Turno;
  cargo: CargoPoder;
};

export async function DadosForca({ ano, turno, cargo }: DadosForcaProps) {
  const resultado = await buscarForca(ano, turno, cargo);
  if (!resultado.ok) {
    return <ErroRelatorio detalhe={resultado.detalhe} />;
  }
  const placar = resultado.dados;
  return (
    <div className="flex flex-col gap-8">
      {placar.faltando.length > 0 ? (
        <div role="status" className="folha-quieta max-w-3xl space-y-2 text-sm">
          <p>Alguns cargos ainda não foram gravados; as colunas deles mostram —.</p>
          <ul className="space-y-1">
            {placar.faltando.map((item) => (
              <li key={item.cargo}>
                <code className="break-all">{item.comando}</code>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      {placar.cadeiras !== null && !placar.cadeiras.disponivel ? (
        <div role="status" className="folha-quieta max-w-3xl space-y-2 text-sm">
          <p>A simulação de cadeiras ainda não foi gravada; as colunas de cadeiras mostram —.</p>
          {placar.cadeiras.comando !== null ? <code className="break-all">{placar.cadeiras.comando}</code> : null}
        </div>
      ) : null}
      {placar.municipal_2024 !== null && !placar.municipal_2024.disponivel ? (
        <div role="status" className="folha-quieta max-w-3xl space-y-2 text-sm">
          <p>Os resultados municipais de 2024 ainda não foram importados; as colunas de 2024 mostram —.</p>
          {placar.municipal_2024.comando !== null ? (
            <code className="break-all">{placar.municipal_2024.comando}</code>
          ) : null}
        </div>
      ) : null}
      <ExplicacaoForca cargo={placar.cargo_referencia} blocos={placar} />
      <PlacarForcaVista placar={placar} />
    </div>
  );
}
