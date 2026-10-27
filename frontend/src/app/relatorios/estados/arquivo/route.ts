import { readFile } from "node:fs/promises";

import { NextResponse, type NextRequest } from "next/server";

import { arquivoEstados, htmlComTema } from "@/lib/estados";

export async function GET(request: NextRequest) {
  const turno = request.nextUrl.searchParams.get("turno") ?? "2";
  const tema = request.nextUrl.searchParams.get("tema");
  const arquivo = arquivoEstados(turno);

  if (!arquivo) {
    return new NextResponse("Turno não suportado.", {
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
    return new NextResponse("Relatório de estados não encontrado.", {
      status: 404,
      headers: { "Content-Type": "text/plain; charset=utf-8" },
    });
  }
}
