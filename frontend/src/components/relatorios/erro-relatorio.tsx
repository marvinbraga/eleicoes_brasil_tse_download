import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

type ErroRelatorioProps = {
  detalhe: string;
};

export function ErroRelatorio({ detalhe }: ErroRelatorioProps) {
  return (
    <Card role="alert">
      <CardHeader>
        <CardTitle>Não foi possível carregar o relatório</CardTitle>
      </CardHeader>
      <CardContent>
        <p>{detalhe}</p>
      </CardContent>
    </Card>
  );
}
