"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar";

const ITENS = [
  { href: "/", rotulo: "Início" },
  {
    href: "/relatorios/presidente-governador",
    rotulo: "Presidente e governador",
  },
  { href: "/relatorios/poder", rotulo: "Poder" },
  { href: "/relatorios/perfis", rotulo: "Perfis" },
  { href: "/relatorios/classe-governador", rotulo: "Classe do governador" },
  { href: "/relatorios/forca", rotulo: "Força partidária" },
  { href: "/relatorios/cadeiras", rotulo: "Cadeiras" },
  { href: "/relatorios/capilaridade", rotulo: "Capilaridade" },
  { href: "/relatorios/verticalizacao", rotulo: "Verticalização" },
  { href: "/relatorios/marca", rotulo: "Força da marca" },
  { href: "/relatorios/municipais-2024", rotulo: "Municipais 2024" },
  { href: "/relatorios/secoes-turnos", rotulo: "Seções 1º × 2º turno" },
  { href: "/mapa", rotulo: "Mapa" },
] as const;

export function AppSidebar() {
  const pathname = usePathname();

  return (
    <Sidebar collapsible="offcanvas">
      <SidebarHeader>
        <div className="px-2 py-1 text-sm font-semibold">Eleições Brasil</div>
      </SidebarHeader>
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupContent>
            <nav aria-label="Principal">
              <SidebarMenu>
                {ITENS.map((item) => (
                  <SidebarMenuItem key={item.href}>
                    <SidebarMenuButton
                      asChild
                      isActive={pathname === item.href}
                    >
                      <Link href={item.href}>{item.rotulo}</Link>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                ))}
              </SidebarMenu>
            </nav>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
    </Sidebar>
  );
}
