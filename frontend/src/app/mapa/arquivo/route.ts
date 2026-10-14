import { readFile } from "node:fs/promises";

import { NextResponse, type NextRequest } from "next/server";

import { arquivoMapa } from "@/lib/mapas";

const CSS_CLARO =
  "body { background: #ffffff; } #mapa { background: #ffffff; height: 80vh; }";

const CSS_ESCURO = [
  "body { background: oklch(0.145 0 0); color: oklch(0.985 0 0); }",
  "#mapa { background: oklch(0.205 0 0); height: 80vh; }",
  "h1 { color: oklch(0.985 0 0); }",
  "footer, footer p, footer li { color: oklch(0.708 0 0); }",
  ".ol-control button { background-color: oklch(0.269 0 0); color: oklch(0.985 0 0); }",
].join(" ");

export function htmlComTema(html: string, tema: string | null): string {
  if (tema !== "dark" || !html.includes(CSS_CLARO)) {
    return html;
  }
  const inicio = html.indexOf("function estiloMundo()");
  const fim = html.indexOf("function estilo(", inicio);
  if (inicio < 0 || fim < 0) {
    return html;
  }
  const mundo = html
    .slice(inicio, fim)
    .replace('color: "#f7f7f7"', 'color: "oklch(0.205 0 0)"')
    .replace('color: "#cccccc"', 'color: "oklch(1 0 0 / 18%)"');
  return html.slice(0, inicio).replace(CSS_CLARO, CSS_ESCURO) + mundo + html.slice(fim);
}

export async function GET(request: NextRequest) {
  const cargo = request.nextUrl.searchParams.get("cargo") ?? "";
  const tema = request.nextUrl.searchParams.get("tema");
  const arquivo = arquivoMapa(cargo);

  if (!arquivo) {
    return new NextResponse("Cargo não suportado.", {
      status: 400,
      headers: { "Content-Type": "text/plain; charset=utf-8" },
    });
  }

  try {
    const html = htmlComTema(await readFile(arquivo, "utf8"), tema);
    return new NextResponse(html, {
      status: 200,
      headers: {
        "Content-Type": "text/html; charset=utf-8",
        "Cache-Control": "no-store",
      },
    });
  } catch {
    return new NextResponse("Mapa não encontrado.", {
      status: 404,
      headers: { "Content-Type": "text/plain; charset=utf-8" },
    });
  }
}
