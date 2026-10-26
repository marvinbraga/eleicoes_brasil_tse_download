import Link from "next/link";

import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

const DESTINOS = [
  {
    href: "/relatorios/presidente-governador",
    titulo: "Presidente e governador",
    descricao: "Relatório da API por UF.",
  },
  {
    href: "/relatorios/poder",
    titulo: "Poder",
    descricao: "Relatório da API por cargo e UF.",
  },
  {
    href: "/relatorios/perfis",
    titulo: "Perfis municipais",
    descricao: "Grupos de municípios a partir das células já gravadas.",
  },
  {
    href: "/relatorios/classe-governador",
    titulo: "Classe do governador",
    descricao: "A classe do governador lida pela mistura de presidente.",
  },
  {
    href: "/relatorios/forca",
    titulo: "Força partidária",
    descricao: "Placar por partido em três esferas, a partir dos relatórios de poder gravados.",
  },
  {
    href: "/relatorios/cadeiras",
    titulo: "Simulação de cadeiras",
    descricao:
      "Estimativa de cadeiras na Câmara, nas Assembleias, no Senado e nos governos.",
  },
  {
    href: "/relatorios/capilaridade",
    titulo: "Capilaridade",
    descricao: "Se a força de cada partido está espalhada ou concentrada nos municípios.",
  },
  {
    href: "/relatorios/verticalizacao",
    titulo: "Verticalização",
    descricao:
      "Se a força de cada partido se sustenta entre presidente, governador, senador e deputados.",
  },
  {
    href: "/relatorios/marca",
    titulo: "Força da marca",
    descricao: "Quanto do voto para deputado foi só no número do partido.",
  },
  {
    href: "/relatorios/municipais-2024",
    titulo: "Municipais 2024",
    descricao: "Prefeitos, eleitorado governado e vereadores de 2024 por partido.",
  },
  {
    href: "/relatorios/secoes-turnos",
    titulo: "Seções 1º × 2º turno",
    descricao: "Arquivo já gerado: seções que o cenário de transferência explica mal.",
  },
  {
    href: "/mapa",
    titulo: "Mapa",
    descricao: "Arquivo de mapa já gerado.",
  },
] as const;

export default function Home() {
  return (
    <div className="flex flex-col gap-6 p-6">
      <div className="flex max-w-3xl flex-col gap-2">
        <h1 className="text-2xl font-semibold tracking-tight">
          Eleições Brasil
        </h1>
        <p className="text-muted-foreground">
          Estas páginas abrem os relatórios que a API já publica e o arquivo de
          mapa já gerado, para o ano 2026, turno 1.
        </p>
      </div>
      <div className="grid gap-4 md:grid-cols-3">
        {DESTINOS.map((destino) => (
          <Link
            key={destino.href}
            href={destino.href}
            className="rounded-xl focus-visible:ring-3 focus-visible:ring-ring focus-visible:outline-none"
          >
            <Card className="h-full transition-colors hover:bg-muted/40">
              <CardHeader>
                <CardTitle>{destino.titulo}</CardTitle>
                <CardDescription>{destino.descricao}</CardDescription>
              </CardHeader>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
