# Gráfico e explicação do relatório Poder

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A página `/relatorios/poder` ganha, acima das tabelas, uma explicação em português simples (linhas, colunas, votos válidos, cor da célula, como ler), uma ou mais frases de leitura geradas a partir dos dados, um gráfico de barras horizontais com a fatia de cada partido no total de votos válidos do recorte e um segundo gráfico com o número de lugares que cada partido lidera. As tabelas continuam abaixo como caminho acessível.

**Architecture:** Um módulo puro (`lib/grafico-poder.ts`) soma os votos das linhas visíveis, monta os itens das barras, calcula o layout e escreve as frases. Um componente de servidor (`grafico-poder.tsx`) desenha o SVG e reaproveita o `DicaGrafico` para o tooltip. Outro componente de servidor (`explicacao-poder.tsx`) traz o texto fixo e as frases. O encaixe é em `dados-poder.tsx`. O backend não muda.

**Tech Stack:** Next.js 16.4, React 19, TypeScript, Tailwind 4, shadcn/ui. Sem biblioteca de gráficos e sem runner de teste. O script de verificação roda com `node --experimental-strip-types`.

**Spec:** Este arquivo. O JSON consumido é o de `GET /relatorios/dados/grade`, já tipado em `frontend/src/lib/relatorios.ts` (`GradeRelatorio`, `LinhaGrade`, `CelulaGrade`).

## Decisões

| # | Pergunta | Decisão |
|---|---|---|
| P1 | Base do cálculo | As linhas visíveis (`linhasVisiveis(grade.linhas, nivel, uf)`), as mesmas das tabelas. Com nível municipal e UF "Todas", são todos os municípios. |
| P2 | Votos válidos | Soma de `celula.votos` (nominais + legenda) da linha, como na tabela. `celula.fatia` não é usada, porque divide pelo comparecimento. Brancos e nulos não entram. |
| P3 | Fatia | `formatarPercentualContagem(votosDoPartido, totalValido)`, formato "42,19%". O número em ponto flutuante só serve para a geometria. |
| P4 | Partidos e "Outros" | Os partidos sem votos saem. Com até 9 partidos, todos aparecem. Com mais, aparecem os 8 maiores e os demais são somados em "Outros". "Outros" fica sempre por último. Empate de votos é resolvido pelo menor número de partido. |
| P5 | Rótulo | "Partido 22". Não existe mapa de número para sigla no frontend, e esta tarefa não cria um. |
| P6 | Escala | O comprimento da barra é proporcional ao maior valor. A margem direita (`DIREITA = 72`) guarda espaço para o rótulo de valor, inclusive com 100,00%. |
| P7 | Liderança | Por linha com votos válidos > 0, lidera o partido com mais votos. Empate no topo não conta para ninguém e entra na frase de empates. O segundo gráfico só aparece com mais de um lugar. |
| P8 | Disputa apertada | A menor diferença (1º − 2º) / votos válidos entre as linhas cujo 2º tem votos > 0. Empate de diferença é resolvido pelo nome. Com um lugar só, a frase vira "O segundo é …". |
| P9 | Cor | Barras em `var(--tinta-quente)`. Textos em `text-foreground` e `text-muted-foreground`. |
| P10 | Acessibilidade | `<svg role="img">` com `<title>` e `<desc>`, e `<desc>` com todos os valores. O tooltip só aparece com ponteiro. A tabela continua abaixo. |

## Global Constraints

- Só arquivos novos com "poder" no nome. O único arquivo modificado é `dados-poder.tsx`. Os arquivos compartilhados (`eleicoes.ts`, `relatorios.ts`, `fracao.ts`, `fatia.ts`, `dica-grafico.tsx` e outros) não mudam.
- Sem dependência nova. Sem commit. Sem git que muda estado.
- Verificação: `node --experimental-strip-types src/lib/verificar-grafico-poder.ts`, `pnpm exec tsc --noEmit` e `pnpm exec eslint` nos arquivos novos.

---

### Task 1: Dados e layout puros

**Files:**
- Create: `frontend/src/lib/grafico-poder.ts`
- Test: `frontend/src/lib/verificar-grafico-poder.ts`

**Interfaces:**
- Consumes: `formatarInteiro` e `formatarPercentualContagem` de `./fracao.ts`, e `import type { LinhaGrade }` de `./relatorios.ts`.
- Produces:
  ```ts
  export const LARGURA = 640, ALTURA_LINHA = 28, ALTURA_BARRA = 16, ESQUERDA = 96, DIREITA = 72,
    TOPO = 4, BASE = 4, LIMITE_PARTIDOS = 8;
  export type ItemBarra = { chave: string; rotulo: string; valor: number; texto: string; detalhe: string };
  export type Barra = ItemBarra & { y: number; largura: number };
  export type LayoutBarras = { largura: number; altura: number; barras: Barra[] };
  export function fatiasPoder(linhas: readonly LinhaGrade[]): ItemBarra[];
  export function liderancasPoder(linhas: readonly LinhaGrade[]): { itens: ItemBarra[]; lugares: number; empates: number };
  export function layoutBarras(itens: readonly ItemBarra[]): LayoutBarras | null;
  export function resumoBarras(introducao: string, itens: readonly ItemBarra[]): string;
  export function leituraPoder(linhas: readonly LinhaGrade[]): string[];
  ```

- [x] **Step 1:** Escrever `verificar-grafico-poder.ts` com `node:assert/strict`. Os casos são: "Outros" com 10 partidos; 9 partidos sem "Outros"; partido zerado; 100% na borda; empate na liderança; disputa apertada com e sem empate; um lugar só; recorte vazio. As frases são conferidas com o texto exato.
- [x] **Step 2:** Rodar e ver falhar com `ERR_MODULE_NOT_FOUND`.
- [x] **Step 3:** Implementar `grafico-poder.ts`.
- [x] **Step 4:** Rodar até imprimir `ok`, depois `tsc` e `eslint`.

---

### Task 2: Componentes, encaixe e navegador

**Files:**
- Create: `frontend/src/components/relatorios/grafico-poder.tsx` (servidor)
- Create: `frontend/src/components/relatorios/explicacao-poder.tsx` (servidor)
- Modify: `frontend/src/components/relatorios/dados-poder.tsx` (explicação e gráficos acima de `grupos.map`; o rodapé antigo sai, porque a explicação o cobre)

Desenho: `<figure className="folha-quieta">` com `overflow-x-auto` e `<svg className="w-full min-w-[480px]" role="img">`. O rótulo do partido fica à esquerda (`text-anchor="end"`, `text-foreground`). A barra fica em `--tinta-quente`, com o valor no fim (`text-foreground`, `tabular-nums`). Um `<rect>` transparente por linha leva `data-dica-titulo` e `data-dica-linhas`. O figcaption explica a leitura.

- [x] **Step 1:** Implementar os componentes e o encaixe.
- [x] **Step 2:** `pnpm exec tsc --noEmit`, `eslint` nos arquivos novos e o script de verificação.
- [x] **Step 3:** Conferir no navegador (chrome-devtools, aba própria `isolatedContext: "poder"`):
  - `/relatorios/poder?ano=2026&turno=1&uf=AC&cargo=presidente&consultar=1`;
  - `cargo=governador`;
  - `nivel=uf`;
  - tema claro e escuro;
  - 375 px;
  - tooltip;
  - console.

  Salvar as capturas `poder-*.png` no scratchpad.
- [x] **Step 4:** Sem commit.
