"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb";

type Trilha = {
  pagina: string;
  relatorios: boolean;
};

const TRILHAS: Record<string, Trilha> = {
  "/": { pagina: "Início", relatorios: false },
  "/relatorios/presidente-governador": {
    pagina: "Presidente e governador",
    relatorios: true,
  },
  "/relatorios/poder": { pagina: "Poder", relatorios: true },
  "/relatorios/perfis": { pagina: "Perfis municipais", relatorios: true },
  "/relatorios/classe-governador": {
    pagina: "Classe do governador",
    relatorios: true,
  },
  "/mapa": { pagina: "Mapa", relatorios: false },
};

export function AppBreadcrumb() {
  const pathname = usePathname();
  const trilha = TRILHAS[pathname];

  if (!trilha || pathname === "/") {
    return (
      <Breadcrumb aria-label="Trilha de navegação">
        <BreadcrumbList>
          <BreadcrumbItem>
            <BreadcrumbPage>Início</BreadcrumbPage>
          </BreadcrumbItem>
        </BreadcrumbList>
      </Breadcrumb>
    );
  }

  return (
    <Breadcrumb aria-label="Trilha de navegação">
      <BreadcrumbList>
        <BreadcrumbItem>
          <BreadcrumbLink asChild>
            <Link href="/">Início</Link>
          </BreadcrumbLink>
        </BreadcrumbItem>
        {trilha.relatorios ? (
          <>
            <BreadcrumbSeparator />
            <BreadcrumbItem>
              <span>Relatórios</span>
            </BreadcrumbItem>
          </>
        ) : null}
        <BreadcrumbSeparator />
        <BreadcrumbItem>
          <BreadcrumbPage>{trilha.pagina}</BreadcrumbPage>
        </BreadcrumbItem>
      </BreadcrumbList>
    </Breadcrumb>
  );
}
