import { TabelaLeitura } from "@/components/relatorios/tabela-leitura";
import type { LeituraLugar } from "@/lib/relatorios";

type SecaoLeituraProps = {
  id: string;
  titulo: string;
  lugares: readonly LeituraLugar[];
  apoio?: string;
};

export function SecaoLeitura({ id, titulo, lugares, apoio }: SecaoLeituraProps) {
  const rotulo = apoio === undefined ? titulo : `${titulo}. ${apoio}`;
  return (
    <section aria-labelledby={id} className="flex flex-col gap-3">
      <div className="flex flex-col gap-1">
        <h2 id={id} className="leitura-titulo text-2xl">
          {titulo}
        </h2>
        {apoio === undefined ? null : (
          <p className="text-sm text-muted-foreground">{apoio}</p>
        )}
      </div>
      {lugares.length === 0 ? (
        <p className="text-sm text-muted-foreground">Nenhum lugar neste recorte.</p>
      ) : (
        <TabelaLeitura rotulo={rotulo} lugares={lugares} />
      )}
    </section>
  );
}
