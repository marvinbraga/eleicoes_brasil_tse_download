const FORMATO_INTEIRO = new Intl.NumberFormat("pt-BR");
const FRACAO = /^(\d+)(?:\/(\d+))?$/;
const ZERO = BigInt(0);
const UM = BigInt(1);
const DOIS = BigInt(2);
const ESCALA_PERCENTUAL = BigInt(10000);
const DUAS_CASAS = BigInt(100);

export const TRACO = "—";

export type Fracao = {
  numerador: bigint;
  denominador: bigint;
};

export function formatarInteiro(valor: number): string {
  return FORMATO_INTEIRO.format(valor);
}

export function analisarFracao(texto: string): Fracao | null {
  const encontrado = FRACAO.exec(texto.trim());
  if (encontrado === null || encontrado[1] === undefined) {
    return null;
  }
  const denominador = encontrado[2] === undefined ? UM : BigInt(encontrado[2]);
  if (denominador === ZERO) {
    return null;
  }
  return { numerador: BigInt(encontrado[1]), denominador };
}

export function formatarFracao(fracao: Fracao | null): string {
  if (fracao === null || fracao.denominador === ZERO) {
    return TRACO;
  }
  const produto = fracao.numerador * ESCALA_PERCENTUAL;
  const quociente = produto / fracao.denominador;
  const resto = produto % fracao.denominador;
  const arredondado =
    resto * DOIS >= fracao.denominador ? quociente + UM : quociente;
  const inteiro = arredondado / DUAS_CASAS;
  const centesimos = (arredondado % DUAS_CASAS).toString().padStart(2, "0");
  return `${formatarParte(inteiro)},${centesimos}%`;
}

export function formatarPercentualContagem(
  numerador: number,
  denominador: number,
): string {
  if (
    !Number.isSafeInteger(numerador) ||
    !Number.isSafeInteger(denominador) ||
    denominador <= 0
  ) {
    return TRACO;
  }
  return formatarFracao({
    numerador: BigInt(numerador),
    denominador: BigInt(denominador),
  });
}

export function formatarPercentualTexto(texto: string): string {
  return formatarFracao(analisarFracao(texto));
}

export function fracaoMaior(atual: Fracao, candidata: Fracao): Fracao {
  const esquerda = atual.numerador * candidata.denominador;
  const direita = candidata.numerador * atual.denominador;
  return esquerda >= direita ? atual : candidata;
}

export function alfaFracao(fracao: Fracao, maximo: Fracao): number {
  if (maximo.numerador === ZERO || fracao.denominador === ZERO) {
    return 0;
  }
  const numerador = fracao.numerador * maximo.denominador;
  const denominador = fracao.denominador * maximo.numerador;
  if (denominador === ZERO) {
    return 0;
  }
  const medido = (numerador * ESCALA_PERCENTUAL) / denominador;
  if (medido <= ZERO) {
    return 0;
  }
  if (medido >= ESCALA_PERCENTUAL) {
    return 1;
  }
  return Number(medido) / Number(ESCALA_PERCENTUAL);
}

function formatarParte(valor: bigint): string {
  if (valor <= BigInt(Number.MAX_SAFE_INTEGER)) {
    return FORMATO_INTEIRO.format(Number(valor));
  }
  const digitos = valor.toString();
  const grupos: string[] = [];
  for (let indice = digitos.length; indice > 0; indice -= 3) {
    grupos.push(digitos.slice(Math.max(0, indice - 3), indice));
  }
  return grupos.reverse().join(".");
}
