import type { TextoSvg } from "@/lib/texto-svg";

// Um <text> a partir da posição calculada na lib; a mesma lista é medida nos verificar-*.
export function TextoGrafico({ texto }: { texto: TextoSvg }) {
  const tinta = texto.tom === "suave" ? "text-muted-foreground" : "text-foreground";
  const classe = texto.tabular ? `${tinta} tabular-nums` : tinta;
  return (
    <text
      x={texto.vertical ? undefined : texto.x}
      y={texto.vertical ? undefined : texto.y}
      transform={texto.vertical ? `translate(${texto.x} ${texto.y}) rotate(-90)` : undefined}
      dy={texto.centrado ? "0.35em" : undefined}
      textAnchor={texto.ancora === "start" ? undefined : texto.ancora}
      fontSize={texto.fonte}
      fill="currentColor"
      className={classe}
    >
      {texto.texto}
    </text>
  );
}
