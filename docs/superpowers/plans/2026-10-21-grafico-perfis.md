# Gráfico dos perfis municipais

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** O relatório Perfis municipais ganha um gráfico com a mistura típica de cada grupo (até 5 partidos principais e "Outros") e o peso de cada grupo (municípios e comparecimento). A explicação passa a usar frases curtas e diretas, e a separação é explicada por comparação.

**Architecture:** Um módulo puro (`lib/grafico-perfis.ts`) escolhe os partidos, calcula o layout e gera os textos (resumo do `<desc>` e leitura da separação). Um componente de servidor desenha o SVG dentro do `DicaGrafico` que já existe. A tabela de grupos continua abaixo como caminho acessível. O backend não muda.

**Tech Stack:** Next.js 16.4, React 19, TypeScript, Tailwind 4, shadcn/ui. Sem biblioteca de gráficos. O script de verificação roda com `node --experimental-strip-types`.

**Spec:** Este arquivo. O JSON é o de `GET /relatorios/dados/perfis`, tipado em `frontend/src/lib/relatorios.ts` (`RelatorioPerfis`, `GrupoPerfil`).

## Decisões

| # | Pergunta | Decisão |
|---|---|---|
| P1 | Forma | Barras horizontais agrupadas, um bloco por grupo. Com 6 grupos × 6 barras, barras verticais ficariam com uns 12 px e os rótulos de valor colidiriam. Na horizontal, cada barra tem o número do partido à esquerda e o valor logo depois do fim da barra |
| P2 | Partidos | Até 5, pelo peso total `Σ fatia × comparecimento` sobre os grupos, para que um grupo pequeno não promova um partido. Empate pelo número do partido. Exceção: o líder de cada grupo sempre entra (no governador de 2026 o líder do grupo 6, o 11 com 70,59%, ficaria escondido em "Outros"). Os líderes ocupam vagas primeiro; o total é `max(5, nº de líderes)`, no máximo 6 porque há no máximo 6 grupos. A ordem e o tom são os mesmos em todos os grupos |
| P3 | Branco e nulo | Ficam fora do gráfico, porque a base deles é o comparecimento, não os votos válidos. Continuam na tabela |
| P4 | Outros | Soma das fatias dos partidos restantes (não `100% − principais`, porque os centros não somam exatamente 100%). Some quando não há resto ou ele é zero |
| P5 | Escala da mistura | Comum a todos os grupos, de 0 até o maior valor arredondado para cima ao próximo múltiplo de 10% (teto de 100%) |
| P6 | Peso | Coluna à direita de cada bloco: duas barras, "Municípios" e "Votantes", como parte do total, num único eixo de 0 a 100%. Não há dois eixos |
| P7 | Cor | `--chart-1..5` existem, mas são cinzas sem croma e iguais nos dois temas: o 1 some no cartão claro e o 5 some no escuro. Os tons vêm de `color-mix(in oklab, var(--tinta-quente) p%, var(--foreground))` com p = 100, 78, 56, 36, 18, pelo posto do partido. No claro o tom escurece e no escuro clareia, sempre se afastando do cartão. Um 6º partido (só quando há 6 líderes distintos) usa `color-mix(in oklab, var(--tinta-quente) 50%, var(--tinta-frio))`, mais claro que a rampa no claro e mais escuro no escuro, sempre com o contorno. Uma rampa de 6 passos para o primeiro plano falhou o ΔL adjacente no claro (0,052–0,058). "Outros" usa `--muted-foreground` misturado ao cartão. Toda barra tem contorno de 1 px na própria cor-base (`--tinta-quente` ou `--muted-foreground`) |
| P8 | Validação de cor | `validate_palette.js --ordinal`: claro `#0d6f6e,#155656,#163f3e,#142b2a,#101a1a` sobre `#ffffff` passa tudo (ponta clara 5,97:1); escuro `#0d6f6e,#508c8b,#80aaa9,#abc6c5,#d2e0df` sobre `#171717` passa tudo (ponta 3,00:1). No modo categórico a rampa falha banda de luminosidade, croma e separação CVD (ΔE 5,6), como esperado de um só matiz. Por isso a identidade do partido é o rótulo direto em cada barra; o tom é só reforço |
| P9 | Texto | Rótulos e valores em `text-foreground`/`text-muted-foreground`, nunca na cor da barra |
| P10 | Acessibilidade | `<svg role="img">` com `<title>` e `<desc>` gerado. Tooltip só com ponteiro. Os mesmos números estão na tabela abaixo |
| P11 | Separação | Duas casas ("0,64"). Faixas: < 0 "os grupos se confundem"; < 0,25 "os grupos quase não se distinguem"; < 0,5 "os grupos se parecem em parte"; < 0,7 "os grupos são bem diferentes entre si"; ≥ 0,7 "os grupos são muito diferentes entre si". Valor negativo também gera frase |

## Global Constraints

- Sem dependências, sem backend, sem commit. `frontend/src/lib/` e `frontend/src/components/relatorios/` são ignorados pelo git.
- Não modificar `eleicoes.ts`, `relatorios.ts`, `fracao.ts`, `fatia.ts`, `buscar-relatorios.ts`, `dica-grafico.tsx`, `grafico-acerto-uf.tsx`, `relatorio-pagina.tsx`, `notas-relatorio.tsx`, `globals.css`, `tabela-poder.tsx`.
- Verificação: `cd frontend && node --experimental-strip-types src/lib/verificar-grafico-perfis.ts`, `pnpm exec tsc --noEmit`, `pnpm exec eslint` nos arquivos tocados.

---

### Task 1: Layout puro

**Files:**
- Create: `frontend/src/lib/grafico-perfis.ts`
- Test: `frontend/src/lib/verificar-grafico-perfis.ts`

**Interfaces:**
- Consumes: `lerFatia` de `./fatia.ts`, `formatarInteiro` e `formatarPercentualContagem` de `./fracao.ts`, `import type { GrupoPerfil }` de `./relatorios.ts`.
- Produces: `layoutPerfis(entrada)`, `resumoPerfis(entrada)`, `leituraSeparacao(silhueta)`, `principaisPerfis(entrada)` e as constantes de geometria.

- [x] **Step 1: Script de verificação falhando** (`ERR_MODULE_NOT_FOUND`)
- [x] **Step 2: Implementar `grafico-perfis.ts`**
- [x] **Step 3: Rodar até `ok`, tsc e eslint limpos**

### Task 2: SVG, texto e encaixe

**Files:**
- Create: `frontend/src/components/relatorios/grafico-perfis.tsx` (servidor)
- Modify: `frontend/src/components/relatorios/dados-perfis.tsx`

- [x] **Step 1: Componente** com `<figure className="folha-quieta">`, `overflow-x-auto`, `min-w-[560px]` (o viewBox tem 680 de largura; com 480 o texto de 11 cairia para menos de 8 px), alvos com `data-dica-titulo`/`data-dica-linhas` e figcaption
- [x] **Step 2: Reescrever a explicação** em frases curtas: o que é um grupo, o que é mistura típica, a separação por comparação, grupo maior e partido líder de cada grupo
- [x] **Step 3: tsc, eslint, script**
- [x] **Step 4: Navegador** (presidente e governador, claro/escuro, 375 px, tooltip, console) com capturas no scratchpad
