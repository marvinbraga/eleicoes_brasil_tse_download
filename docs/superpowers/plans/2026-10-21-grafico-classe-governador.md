# Gráfico de acerto por classe e resumo simples (classe do governador)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A página da classe do governador ganha, no topo, um resumo curto em linguagem simples gerado dos dados (acerto geral comparado às duas linhas de base, a situação em que o modelo mais acerta e a que mais erra) e um gráfico de barras horizontais com o acerto de cada situação, o número de municípios e uma linha de referência no acerto geral. O gráfico de acerto por UF e as tabelas continuam abaixo, sem mudança.

**Architecture:** Mesmo padrão do plano de 2026-10-20 (`2026-10-20-grafico-acerto-uf.md`). Um módulo puro (`lib/grafico-acerto-classe.ts`) calcula o layout e as frases a partir do JSON que já chega. Um componente de servidor (`grafico-acerto-classe.tsx`) desenha o SVG e reaproveita `DicaGrafico` para o tooltip. O backend não muda.

**Tech Stack:** Next.js 16.4, React 19, TypeScript, Tailwind 4, shadcn/ui. Sem dependência nova. Verificação com `node --experimental-strip-types`.

## Decisões

| # | Pergunta | Decisão |
|---|---|---|
| C1 | Forma | Barras horizontais, uma por situação, ordenadas do maior acerto para o menor; empate mantém a ordem do backend |
| C2 | Escala | Eixo fixo de 0% a 100%, marcas em 0, 25, 50, 75 e 100%. Margem direita reservada para o valor ao fim da barra (barra de 100% não corta o rótulo) |
| C3 | Referência | Uma linha sólida, `text-foreground`, no acerto geral, com rótulo direto "Acerto geral X". As bases não entram no gráfico: comparam com o acerto geral, não com o acerto de cada situação |
| C4 | Cor | Barras em `--tinta-quente` com contorno `--tinta-frio`. Texto só em `text-foreground`/`text-muted-foreground` |
| C5 | Rótulos | À esquerda, o nome da situação e, embaixo, o número de municípios. Ao fim da barra, o percentual |
| C6 | Tooltip | `data-dica-titulo` = situação; `data-dica-linhas` = "Acertou X" e "N municípios nesta situação" |
| C7 | Resumo | Frases geradas no frontend, sem "recall", "F1", "baseline" ou "held out". Comparação com as bases na segunda frase (abaixo das duas, acima das duas, entre elas; base não percentual é omitida). Acerto zero vira "não acertou nenhum dos N" |
| C8 | Vocabulário | "o modelo" em todo o relatório (antes a página alternava "a leitura" e "o modelo") |
| C9 | Acessibilidade | `<svg role="img">` com `<title>`/`<desc>` de ids próprios (`grafico-acerto-classe-*`), para não colidir com o gráfico por UF |

## Global Constraints

- Só arquivos novos com "classe" no nome; modificar apenas `dados-classe-governador.tsx` e `tabela-classe-governador.tsx`. Não tocar em `relatorios.ts`, `fracao.ts`, `fatia.ts`, `dica-grafico.tsx`, `grafico-acerto-uf.tsx`, `grafico-acerto-uf.ts`, `globals.css`.
- Verificação: `node --experimental-strip-types src/lib/verificar-grafico-acerto-classe.ts` e `.../verificar-grafico-acerto-uf.ts` imprimem `ok`; `pnpm exec tsc --noEmit`; `pnpm exec eslint` nos arquivos tocados.

---

### Task 1: Layout e frases puros

**Files:**
- Create: `frontend/src/lib/grafico-acerto-classe.ts`
- Test: `frontend/src/lib/verificar-grafico-acerto-classe.ts`

**Interfaces:**
```ts
export const LARGURA = 640, ESQUERDA = 150, DIREITA = 64, TOPO = 36, BASE = 28,
  ALTURA_LINHA = 44, ALTURA_BARRA = 18;
export type EntradaGraficoClasse = { linhas: readonly LinhaClasseGovernador[]; acerto: string; base: string; baseLider: string };
export type BarraClasse = { classe: string; rotulo: string; municipios: number; acertoTexto: string; fracao: number; x: number; largura: number; y: number };
export type LayoutAcertoClasse = { largura: number; altura: number; barras: BarraClasse[]; referencia: { x: number; valorTexto: string; ancora: "start" | "end" } | null; marcas: { x: number; rotulo: string }[]; descartadas: number };
export function layoutAcertoClasse(entrada: EntradaGraficoClasse): LayoutAcertoClasse | null;
export function frasesClasse(entrada: EntradaGraficoClasse): string[];
export function resumoAcertoClasse(entrada: EntradaGraficoClasse): string;
```

- [x] **Step 1:** Escrever o script de verificação (layout com 3 e 4 situações, 100% na borda, recall "—" descartado, lista vazia → `null`; frases para abaixo das duas bases, acima das duas, entre elas, base inválida, acerto zero e empate).
- [x] **Step 2:** Rodar e ver falhar (módulo inexistente).
- [x] **Step 3:** Implementar `grafico-acerto-classe.ts`.
- [x] **Step 4:** Rodar e ver `ok`; o script do gráfico por UF continua `ok`.

### Task 2: Componente e encaixe

**Files:**
- Create: `frontend/src/components/relatorios/grafico-acerto-classe.tsx`
- Modify: `frontend/src/components/relatorios/dados-classe-governador.tsx`

- [x] **Step 1:** Componente de servidor no padrão de `grafico-acerto-uf.tsx` (`folha-quieta`, `overflow-x-auto`, `min-w-[480px]`, `DicaGrafico`, figcaption).
- [x] **Step 2:** Em `dados-classe-governador.tsx`, resumo "Em resumo" no topo com `frasesClasse`, o parágrafo duplicado de números sai, o gráfico por classe entra antes do gráfico por UF; "a leitura" vira "o modelo".
- [x] **Step 3:** `tsc --noEmit`, `eslint` nos arquivos tocados.
- [x] **Step 4:** Navegador (claro/escuro, 375 px, tooltips dos dois gráficos, console).
