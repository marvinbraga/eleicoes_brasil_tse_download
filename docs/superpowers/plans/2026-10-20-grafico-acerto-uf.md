# Gráfico de acerto por UF (classe do governador)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A página da classe do governador ganha um gráfico de pontos com o acerto de cada UF, ordenado do maior para o menor, com o tamanho do ponto pelo número de municípios e três linhas de referência (acerto geral, base da maioria e base do líder).

**Architecture:** Um módulo puro (`lib/grafico-acerto-uf.ts`) calcula o layout (coordenadas, raios, faixas dos rótulos e resumo textual) a partir do JSON que já chega. Um componente de servidor desenha o SVG e um pequeno componente cliente cuida só do tooltip, por delegação de eventos. A tabela por UF continua logo abaixo como caminho acessível. O backend não muda.

**Tech Stack:** Next.js 16.4, React 19, TypeScript, Tailwind 4, shadcn/ui. Não há biblioteca de gráficos nem runner de teste no frontend. Node 22 executa o script de verificação com `--experimental-strip-types` (`allowImportingTsExtensions` já está ligado no `tsconfig.json`).

**Spec:** Este arquivo. As decisões vieram da sessão de 2026-10-20 (tabela abaixo). O JSON consumido é o de `GET /relatorios/dados/classe-governador`, já tipado em `frontend/src/lib/relatorios.ts` (`RelatorioClasseGovernador`, `AcertoUf`).

## Decisões

| # | Pergunta | Decisão |
|---|---|---|
| G1 | Peso visual | Raio pelo número de municípios: `RAIO_MIN + (RAIO_MAX − RAIO_MIN)·√(n / nMax)`, com raio de 4 a 10 px e legenda de tamanho com o menor e o maior n |
| G2 | Ordem | Acerto decrescente; empate por UF em ordem alfabética. A tabela continua alfabética |
| G3 | Tecnologia | SVG próprio. Componente de servidor para o desenho e componente cliente só para o tooltip. Sem dependência nova |
| G4 | Escopo | Só no frontend, acima da tabela por UF. O HTML do backend não muda |
| G5 | Escala | Eixo fixo de 0% a 100%, com marcas em 0, 25, 50, 75 e 100% |
| G6 | Linhas | "Acerto geral" (sólida, `text-foreground`), "Maioria" e "Líder presidencial" (tracejadas `4 3`, `text-muted-foreground`), todas de 1 px |
| G7 | Cor | Pontos em `--tinta-quente` (#0d6f6e) com anel de 2 px em `--tinta-frio`. O contraste passou nos dois temas no `validate_palette.js`. O piso de croma falha, por isso as linhas usam traço e rótulo direto como codificação secundária |
| G8 | Acessibilidade | `<svg role="img">` com `<title>` e `<desc>` (resumo gerado). O tooltip só aparece com ponteiro, e os mesmos dados estão na tabela logo abaixo. As linhas do gráfico não recebem foco, para não somar 27 paradas de tab antes da tabela |

## Global Constraints

- Não adicionar dependências. Não editar `.gitignore`. `frontend/src/lib/` e `frontend/src/components/relatorios/` são ignorados pelo git, então os arquivos novos não aparecem em `git diff` (é esperado). Não fazer commit no frontend.
- O texto usa tokens de texto (`text-foreground` e `text-muted-foreground`), nunca a cor dos pontos. Rótulos de valor ficam só nas linhas de referência; os valores dos pontos ficam no tooltip e na tabela.
- Interface em português. Identificadores seguem o padrão do frontend, em português.
- Verificação: `cd frontend && node --experimental-strip-types src/lib/verificar-grafico-acerto-uf.ts`, `pnpm exec tsc --noEmit` e `pnpm lint`, todos limpos.
- Não chamar a API com `atualizar=true`. Não derrubar o Compose.

## Review Focus

- **Acerto geral e base do líder quase iguais** (50,48% e 51,75%, cerca de 7 px de distância): os rótulos não se sobrepõem. Cada linha vai para uma faixa própria (teste na Task 1).
- **Acerto de 100% na borda direita**: o ponto não é cortado, porque `x + RAIO_MAX ≤ LARGURA`. Rótulo de linha perto da borda usa `text-anchor="end"` (teste na Task 1).
- **`acerto` que não é percentual** (ex.: "—"): a UF sai do gráfico e é contada em `descartadas`, sem exceção (teste na Task 1).
- **`nMax` igual a 0, ou uma UF só**: todos os raios ficam em `RAIO_MIN` ou `RAIO_MAX`, sem divisão por zero (teste na Task 1).
- **Tela estreita (375 px)**: o SVG mantém largura mínima de 480 px dentro de um contêiner com rolagem horizontal, sem texto espremido (verificado na Task 2 com o chrome-devtools).

---

### Task 1: Layout puro do gráfico

**Files:**
- Create: `frontend/src/lib/grafico-acerto-uf.ts`
- Test: `frontend/src/lib/verificar-grafico-acerto-uf.ts` (script com `node:assert/strict`)

**Interfaces:**
- Consumes: `lerFatia(texto: string): number | null` de `./fatia.ts` e `type AcertoUf` de `./relatorios.ts`. Os dois imports são relativos com extensão `.ts`, e o de `relatorios` é `import type`, para que o Node consiga rodar o script.
- Produces:
  ```ts
  export const LARGURA = 640, ALTURA_LINHA = 24, RAIO_MIN = 4, RAIO_MAX = 10,
    ESQUERDA = 44, DIREITA = 16, TOPO = 50, BASE = 28, DISTANCIA_ROTULO = 96, ALTURA_FAIXA = 14;
  export type EntradaGrafico = { porUf: readonly AcertoUf[]; acerto: string; base: string; baseLider: string };
  export type PontoUf = { uf: string; municipios: number; acertoTexto: string; x: number; y: number; raio: number };
  export type LinhaReferencia = { chave: "acerto" | "base" | "base_lider"; rotulo: string; valorTexto: string;
    x: number; faixa: 0 | 1 | 2; ancora: "start" | "end" };
  export type Marca = { x: number; rotulo: string };
  export type LayoutAcertoUf = { largura: number; altura: number; pontos: PontoUf[]; linhas: LinhaReferencia[];
    marcas: Marca[]; descartadas: number; menorMunicipios: number; maiorMunicipios: number };
  export function layoutAcertoUf(entrada: EntradaGrafico): LayoutAcertoUf | null;
  export function resumoAcertoUf(entrada: EntradaGrafico): string;
  ```

Regras que a assinatura não fixa:
- `x(f) = ESQUERDA + f·(LARGURA − ESQUERDA − DIREITA)`. `y` do i-ésimo ponto, já ordenado, é `TOPO + i·ALTURA_LINHA + ALTURA_LINHA/2`. `altura = TOPO + n·ALTURA_LINHA + BASE`.
- Rótulos das linhas: `"Acerto geral"`, `"Maioria"`, `"Líder presidencial"`, nas chaves `acerto`, `base` e `base_lider`. Uma linha cujo valor não é percentual é omitida.
- Faixa: percorrer as linhas por `x` crescente e atribuir a primeira faixa (0, 1, 2) cuja última linha esteja a pelo menos `DISTANCIA_ROTULO` de distância; se nenhuma servir, usar a faixa 2. `ancora = "end"` quando `x > LARGURA − 120`; caso contrário, `"start"`.
- Raio: com `nMax ≤ 0`, todos os pontos ficam em `RAIO_MIN`; caso contrário, vale a fórmula da G1 (uma UF só com n > 0 fica em `RAIO_MAX`).
- Retornar `null` quando não sobra nenhum ponto válido.
- Resumo: `"{n} UFs. Maior acerto: {UFs empatadas no topo, juntas com vírgula e 'e'} com {acerto}. Menor: {UFs empatadas na base} com {acerto}. {k} de {n} UFs ficam abaixo da base da maioria ({base})."` Abaixo significa fração estritamente menor que a da base.

- [ ] **Step 1: Write the failing verification script**

```ts
import assert from "node:assert/strict";
import { layoutAcertoUf, resumoAcertoUf, LARGURA, RAIO_MAX, RAIO_MIN, TOPO, ALTURA_LINHA } from "./grafico-acerto-uf.ts";

const base = { acerto: "50,48%", base: "62,61%", baseLider: "51,75%" };
const tres = { ...base, porUf: [
  { uf: "BA", municipios: 417, acerto: "9,83%" },
  { uf: "AC", municipios: 22, acerto: "100,00%" },
  { uf: "MG", municipios: 853, acerto: "95,08%" },
] };

// ordem, coordenadas e raios
const l = layoutAcertoUf(tres)!;
assert.deepEqual(l.pontos.map((p) => p.uf), ["AC", "MG", "BA"]);
assert.equal(l.pontos[0].x, 624);
assert.ok(Math.abs(l.pontos[2].x - (44 + 0.0983 * 580)) < 1e-9);
assert.equal(l.pontos[0].y, TOPO + ALTURA_LINHA / 2);
assert.equal(l.pontos[1].raio, RAIO_MAX);
assert.ok(Math.abs(l.pontos[0].raio - (RAIO_MIN + 6 * Math.sqrt(22 / 853))) < 1e-9);
assert.ok(l.pontos[0].x + RAIO_MAX <= LARGURA);
assert.equal(l.altura, TOPO + 3 * ALTURA_LINHA + 28);
assert.deepEqual([l.menorMunicipios, l.maiorMunicipios], [22, 853]);
assert.deepEqual(l.marcas.map((m) => m.rotulo), ["0%", "25%", "50%", "75%", "100%"]);

// faixas dos rótulos: 50,48 e 51,75 não dividem faixa; 62,61 também não cabe nas duas primeiras
assert.deepEqual(l.linhas.map((r) => [r.chave, r.faixa]), [["acerto", 0], ["base_lider", 1], ["base", 2]]);
assert.ok(l.linhas.every((r) => r.ancora === "start"));
assert.equal(layoutAcertoUf({ ...tres, base: "98,00%" })!.linhas.find((r) => r.chave === "base")!.ancora, "end");

// entradas ruins
assert.equal(layoutAcertoUf({ ...base, porUf: [] }), null);
const ruim = layoutAcertoUf({ ...base, porUf: [...tres.porUf, { uf: "PI", municipios: 224, acerto: "—" }] })!;
assert.equal(ruim.descartadas, 1);
assert.equal(ruim.pontos.length, 3);
assert.equal(layoutAcertoUf({ ...base, baseLider: "x", porUf: tres.porUf })!.linhas.length, 2);
const zero = layoutAcertoUf({ ...base, porUf: [{ uf: "DF", municipios: 0, acerto: "100,00%" }] })!;
assert.equal(zero.pontos[0].raio, RAIO_MIN);
const empate = layoutAcertoUf({ ...base, porUf: [
  { uf: "TO", municipios: 1, acerto: "100,00%" }, { uf: "AL", municipios: 1, acerto: "100,00%" }] })!;
assert.deepEqual(empate.pontos.map((p) => p.uf), ["AL", "TO"]);

// resumo
assert.equal(resumoAcertoUf(tres),
  "3 UFs. Maior acerto: AC com 100,00%. Menor: BA com 9,83%. 1 de 3 UFs ficam abaixo da base da maioria (62,61%).");
assert.equal(resumoAcertoUf({ ...base, porUf: [
  { uf: "TO", municipios: 1, acerto: "100,00%" }, { uf: "AL", municipios: 1, acerto: "100,00%" },
  { uf: "AP", municipios: 1, acerto: "100,00%" }, { uf: "PI", municipios: 1, acerto: "1,34%" }] }),
  "4 UFs. Maior acerto: AL, AP e TO com 100,00%. Menor: PI com 1,34%. 1 de 4 UFs ficam abaixo da base da maioria (62,61%).");
console.log("ok");
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd frontend && node --experimental-strip-types src/lib/verificar-grafico-acerto-uf.ts`
Expected: FAIL with `ERR_MODULE_NOT_FOUND` for `grafico-acerto-uf.ts`.

- [ ] **Step 3: Implement `frontend/src/lib/grafico-acerto-uf.ts`** with the interfaces and rules above. Use `lerFatia` for every percentage; sort with `localeCompare("pt-BR")` for UF ties.

- [ ] **Step 4: Run to verify it passes**

Run: `cd frontend && node --experimental-strip-types src/lib/verificar-grafico-acerto-uf.ts && pnpm exec tsc --noEmit && pnpm exec eslint src/lib/grafico-acerto-uf.ts src/lib/verificar-grafico-acerto-uf.ts`
Expected: `ok`, then no output from tsc/eslint.

- [ ] **Step 5: No commit** (git-ignored dir).

---

### Task 2: SVG, tooltip e encaixe na página

**Files:**
- Create: `frontend/src/components/relatorios/grafico-acerto-uf.tsx` (componente de servidor, sem `"use client"`)
- Create: `frontend/src/components/relatorios/dica-grafico.tsx` (`"use client"`)
- Modify: `frontend/src/components/relatorios/dados-classe-governador.tsx` (inserir o gráfico imediatamente antes de `<TabelaAcertoUf …/>`)

**Interfaces:**
- Consumes: `layoutAcertoUf`, `resumoAcertoUf`, `RAIO_MIN`, `RAIO_MAX` e os tipos da Task 1. Os dados vêm de `dados.por_uf`, `dados.acerto`, `dados.base` e `dados.base_lider`.
- Produces: `GraficoAcertoUf({ porUf, acerto, base, baseLider }: EntradaGrafico)`, que devolve `null` quando o layout é `null`; e `DicaGrafico({ children }: { children: React.ReactNode })`.

Desenho (valores fixos):
- `<figure className="folha-quieta flex flex-col gap-3">` com um `<div className="overflow-x-auto">` envolvendo o `<svg viewBox="0 0 {largura} {altura}" className="w-full min-w-[480px]" role="img" aria-labelledby="{titulo} {desc}">`. O `<title>` diz `"Acerto por UF"`; o `<desc>` traz `resumoAcertoUf(...)`.
- Grade: uma linha vertical por marca, 1 px sólida, `stroke="var(--border)"`. O rótulo da marca fica embaixo, em `text-muted-foreground`, tamanho 11.
- UFs: texto à esquerda em `x = ESQUERDA − 8`, `text-anchor="end"`, `text-foreground`, tamanho 12.
- Linhas de referência do `TOPO − 4` até `altura − BASE`, conforme a G6. O rótulo `"{rotulo} {valorTexto}"` fica em `y = 12 + faixa·ALTURA_FAIXA`, deslocado 4 px na direção da âncora, tamanho 11.
- Pontos: `<circle>` com `fill="var(--tinta-quente)"`, `stroke="var(--tinta-frio)"` e `strokeWidth={2}`.
- Alvo de hover por UF: `<rect>` transparente, da largura total da área de plotagem e altura `ALTURA_LINHA`, com `data-dica-uf`, `data-dica-acerto` e `data-dica-municipios` (formatado com `formatarInteiro`), mais `className="hover:fill-muted/60"`.
- `<figcaption className="text-sm text-muted-foreground">`: `"Cada ponto é uma UF, do maior acerto para o menor. O tamanho acompanha o número de municípios. As linhas marcam o acerto geral e as duas linhas de base."`. Em seguida vem a legenda de tamanho, com dois círculos inline (raio mínimo e máximo) e os textos `"{menorMunicipios} município(s)"` e `"{maiorMunicipios} municípios"` (singular quando o valor é 1).
- `DicaGrafico`: um `div` relativo em volta do SVG. Ele trata `pointermove` e `pointerdown` buscando `closest("[data-dica-uf]")` e mostra um tooltip `absolute` perto do ponteiro com `"{UF}"` em negrito, `"{acerto}"` e `"{municípios} municípios"`, todos como texto React, nunca HTML. O tooltip some em `pointerleave`. Visual: `rounded-md border bg-popover text-popover-foreground px-2 py-1 text-xs shadow-sm pointer-events-none`.

- [ ] **Step 1: Implementar os dois componentes e o encaixe** conforme acima.

- [ ] **Step 2: Verificar tipos e lint**

Run: `cd frontend && pnpm exec tsc --noEmit && pnpm lint && node --experimental-strip-types src/lib/verificar-grafico-acerto-uf.ts`
Expected: tudo limpo e `ok`.

- [ ] **Step 3: Verificar no navegador (chrome-devtools)** com o Next na 14000 e a API na 15000. Abrir `/relatorios/classe-governador?ano=2026&turno=1&consultar=1` e conferir:
  - há 27 pontos; o primeiro é uma UF com 100,00% e o último é PI com 1,34%;
  - aparecem as três linhas com os rótulos "Acerto geral 50,48%", "Líder presidencial 51,75%" e "Maioria 62,61%", sem sobreposição;
  - o `<desc>` contém `"15 de 27 UFs ficam abaixo da base da maioria (62,61%)."`;
  - ao passar o mouse sobre a linha de BA, o tooltip mostra "BA", "9,83%" e "417 municípios";
  - o tema escuro funciona (botão "Alternar tema");
  - em 375 px de largura há rolagem horizontal sem texto espremido;
  - o console não mostra erros novos.

  Salvar capturas claro e escuro no scratchpad.

- [ ] **Step 4: No commit** (git-ignored dirs). Commit only this plan doc if the user asks.
