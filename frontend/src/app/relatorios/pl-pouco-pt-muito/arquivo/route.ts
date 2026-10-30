import { readFile } from "node:fs/promises";

import { NextResponse } from "next/server";

import { ARQUIVO_PL_POUCO_PT_MUITO } from "@/lib/pl-pouco-pt-muito";

export async function GET() {
  try {
    const html = await readFile(ARQUIVO_PL_POUCO_PT_MUITO, "utf8");
    return new NextResponse(html, {
      status: 200,
      headers: {
        "Content-Type": "text/html; charset=utf-8",
        "Cache-Control": "no-store",
      },
    });
  } catch {
    return new NextResponse("Relatório de seções do PL e do PT não encontrado.", {
      status: 404,
      headers: { "Content-Type": "text/plain; charset=utf-8" },
    });
  }
}
