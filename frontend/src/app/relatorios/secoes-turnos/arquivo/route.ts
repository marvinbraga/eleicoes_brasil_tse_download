import { readFile } from "node:fs/promises";

import { NextResponse } from "next/server";

import { ARQUIVO_SECOES_TURNOS } from "@/lib/secoes-turnos";

export async function GET() {
  try {
    const html = await readFile(ARQUIVO_SECOES_TURNOS, "utf8");
    return new NextResponse(html, {
      status: 200,
      headers: {
        "Content-Type": "text/html; charset=utf-8",
        "Cache-Control": "no-store",
      },
    });
  } catch {
    return new NextResponse("Relatório de seções não encontrado.", {
      status: 404,
      headers: { "Content-Type": "text/plain; charset=utf-8" },
    });
  }
}
