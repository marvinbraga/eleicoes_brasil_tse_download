type NotasRelatorioProps = {
  notas: readonly string[];
};

export function NotasRelatorio({ notas }: NotasRelatorioProps) {
  if (notas.length === 0) {
    return null;
  }
  return (
    <ul className="max-w-xl list-disc pl-5 text-sm text-muted-foreground">
      {notas.map((nota, indice) => (
        <li key={`${indice}:${nota}`}>{nota}</li>
      ))}
    </ul>
  );
}
