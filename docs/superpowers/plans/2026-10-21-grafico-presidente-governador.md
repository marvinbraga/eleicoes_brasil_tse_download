# Gráfico de composição por UF (presidente e governador)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A página Presidente e governador ganha barras empilhadas a 100%, uma por UF e uma por região. Cada barra divide os votos válidos de presidente daquele lugar entre as quatro classes (Consolidação, Terreno de virada, Em aberto e Sem governador). Antes do gráfico entram um parágrafo "como ler" e frases geradas dos dados.

**Architecture:** Um módulo puro (`lib/grafico-presidente-governador.ts`) agrega os municípios que já chegam no JSON por UF e por região (mapa IBGE fixo) e calcula o layout, as frases e o resumo. Um componente de servidor desenha os dois SVGs e reaproveita `DicaGrafico` para o tooltip. As tabelas continuam abaixo como caminho acessível. O backend não muda.

**Tech Stack:** Next.js 16.4, React 19, TypeScript, Tailwind 4, shadcn/ui. Não há biblioteca de gráficos nem runner de teste no frontend. Node 22 executa o script de verificação com `--experimental-strip-types`.

**Spec:** Este arquivo. O JSON é o de `GET /relatorios/dados/presidente-governador` (`RelatorioCruzado` em `frontend/src/lib/relatorios.ts`). Conferido em 2026, turno 1: a soma de `presidente.valid` dos municípios por classe bate com `composition.classes`, a soma por UF bate com `states[].presidente.valid`, e a soma por região (mapa IBGE) bate com `regions[].presidente.valid`.

## Decisões

| # | Pergunta | Decisão |
|---|---|---|
| P1 | Fonte | Soma de `presidente.valid` dos municípios de `municipalities`, agrupada por `(uf, classe)`. A classe de `states[]` é a do total estadual e não serve para a fatia |
| P2 | Exterior | `ZZ` sai do gráfico (não tem governador; toda a sua fatia é Sem governador). A legenda mantém as 4 classes, igual à barra de composição |
| P3 | Ordem | Fatia de Consolidação decrescente, comparada com inteiros exatos (`BigInt`, produto cruzado); empate pela sigla em `pt-BR` |
| P4 | Cor | A mesma da barra de composição: `var(--tinta-quente)` com `fillOpacity = INTENSIDADE[classe]` de `cruzamento/finalidade.ts`, na ordem `ORDEM_CLASSE`. A figura usa `folha-quieta`, onde o token existe. 1 px de vão entre fatias; fatia com voto tem ao menos 1 px |
| P5 | "Maior parte" | Maior fatia (pluralidade), empate pela ordem de `ORDEM_CLASSE`, igual a `fraseDoAchado` |
| P6 | Região | Mapa IBGE fixo no módulo. Segundo SVG com margem esquerda maior e ids próprios de `title`/`desc` |
| P7 | Acessibilidade | `<svg role="img">` com `<title>` e `<desc>` gerado. Texto só em `text-foreground`/`text-muted-foreground`. Tooltip só com ponteiro; cada linha leva o rótulo da classe (chaves únicas). As tabelas abaixo continuam |
| P8 | Texto | O texto de `finalidade.ts` não muda (fora do escopo e coberto por `verificar-finalidade.ts`). A frase do recorte, que agora também cobre o gráfico, é reescrita em `dados-presidente-governador.tsx` |

## Global Constraints

- Sem dependência nova. Não editar `eleicoes.ts`, `relatorios.ts`, `fracao.ts`, `fatia.ts`, `buscar-relatorios.ts`, `dica-grafico.tsx`, `grafico-acerto-uf.tsx`, `relatorio-pagina.tsx`, `notas-relatorio.tsx`, `globals.css`, `cruzamento/finalidade.ts`. Não fazer commit.
- O módulo puro só usa imports relativos com `.ts`; de `relatorios.ts` só `import type` (o arquivo importa `@/lib/eleicoes`, que o Node não resolve).
- `.folha-quieta > .flex` força 0,7 rem de altura: nenhum filho direto da figura usa a classe `flex`.
- Verificação: `cd frontend && node --experimental-strip-types src/lib/verificar-grafico-presidente-governador.ts`, `pnpm exec tsc --noEmit` e `pnpm exec eslint` nos arquivos novos, todos limpos.

## Review Focus

- **Fatia minúscula** (ex.: 0,03% de terreno de virada no Sudeste): continua visível com 1 px e aparece no tooltip (teste na Task 1).
- **Última borda**: a soma das fatias termina exatamente na borda direita da área de plotagem (teste na Task 1).
- **UF sem voto válido** ou sigla desconhecida: sai do gráfico sem exceção (teste na Task 1).
- **Muitas UFs com 0% de consolidação**: a frase não lista 13 siglas; conta as UFs e cita a menor fatia acima de zero (teste na Task 1).
- **Tema escuro**: a classe de intensidade 0,28 continua visível sobre `--card` (verificado na Task 2).

---

### Task 1: Agregação, layout e frases

**Files:**
- Create: `frontend/src/lib/grafico-presidente-governador.ts`
- Test: `frontend/src/lib/verificar-grafico-presidente-governador.ts`

**Interfaces:**
- Consumes: `ORDEM_CLASSE`, `INTENSIDADE`, `type ClasseCruzada` de `../cruzamento/finalidade.ts`; `formatarPercentualContagem` de `./fracao.ts`; `import type { GrupoMunicipios }` de `./relatorios.ts`.
- Produces:
  ```ts
  export const LARGURA = 640, ALTURA_LINHA = 24, ALTURA_BARRA = 14, ESQUERDA_UF = 44, ESQUERDA_REGIAO = 96,
    DIREITA = 16, TOPO = 8, BASE = 28, VAO = 1;
  export const ROTULOS: Record<ClasseCruzada, string>;
  export type ComposicaoLugar = { codigo: string; votos: Record<ClasseCruzada, number>; total: number };
  export type FatiaBarra = { classe: ClasseCruzada; votos: number; fatiaTexto: string; x: number; largura: number; opacidade: number };
  export type BarraLugar = { codigo: string; total: number; y: number; fatias: FatiaBarra[] };
  export type LayoutComposicao = { largura: number; altura: number; esquerda: number; barras: BarraLugar[];
    marcas: { x: number; rotulo: string }[] };
  export function composicaoPorUf(grupos: readonly GrupoMunicipios[]): ComposicaoLugar[];
  export function composicaoPorRegiao(porUf: readonly ComposicaoLugar[]): ComposicaoLugar[];
  export function layoutComposicao(lugares: readonly ComposicaoLugar[], esquerda: number): LayoutComposicao | null;
  export function frasesComposicao(lugares: readonly ComposicaoLugar[], unidade: "UFs" | "regiões"): string[];
  export function resumoComposicao(lugares: readonly ComposicaoLugar[], unidade: "UFs" | "regiões"): string;
  ```

Regras:
- `composicaoPorUf` só aceita as 27 UFs do mapa IBGE e `total > 0`; devolve já ordenado (P3). `composicaoPorRegiao` soma as UFs por região e ordena igual.
- Bordas: `natural_i = esquerda + (acumulado_i / total)·L`, com `L = LARGURA − esquerda − DIREITA`. Fatia com voto: `x = max(natural, fimAnterior + VAO)` e `largura = max(1, borda − x − VAO)`, menos a última com voto, que vai até a borda (`largura = max(1, borda − x)`); assim uma fatia de menos de 1 px não é coberta pela seguinte. Fatia sem voto: `x = max(natural, fimAnterior)` e `largura = 0`.
- Barra `i`: `y = TOPO + i·ALTURA_LINHA + (ALTURA_LINHA − ALTURA_BARRA)/2`. `altura = TOPO + n·ALTURA_LINHA + BASE`. Marcas em 0, 25, 50, 75 e 100%.
- Frase 1: `"Em {k} de {n} {unidade} a maior parte dos votos válidos de presidente está em {fecho}."` e, se as outras tiverem uma classe só, `" Nas outras {n−k}, está em {fecho}."`; com mais de uma, `" Nas outras {n−k}, a maior fatia é {Rótulo} ({m}) ou {Rótulo} ({m})."` (lista com vírgula e "ou", ordem por contagem e depois `ORDEM_CLASSE`). Quando só resta um lugar, a abertura é `"Na outra"`.
- Frase 2: `"Maior fatia de consolidação: {topo}, com {%}."` e então, com `z` lugares em 0: `" Em {z} de {n} {unidade} nenhum voto está em municípios em consolidação; entre as demais, a menor é {X}, com {%}."`, ou, sem zeros, `" Menor: {X}, com {%}."`. Sem nenhuma consolidação: `"Nenhuma {unidade singular} tem voto em municípios em consolidação."` Empates juntam siglas com vírgula e "e". Quando topo e fundo empatam, a parte da menor sai.
- `resumoComposicao`: `"{n} {unidade}, da maior para a menor fatia de consolidação. "` + frases.

- [x] **Step 1: Write the failing verification script** (`node:assert/strict`, termina com `console.log("ok")`).
- [x] **Step 2: Run it to verify it fails** — `ERR_MODULE_NOT_FOUND`.
- [x] **Step 3: Implement `frontend/src/lib/grafico-presidente-governador.ts`.**
- [x] **Step 4: Run to verify it passes** — `ok`, tsc e eslint limpos.
- [x] **Step 5: No commit.**

---

### Task 2: SVG, texto e encaixe

**Files:**
- Create: `frontend/src/components/relatorios/grafico-presidente-governador.tsx` (servidor)
- Modify: `frontend/src/components/relatorios/dados-presidente-governador.tsx` (seção nova logo depois de `SecaoComposicao`; frase do recorte reescrita)

Desenho:
- `<section aria-labelledby="composicao-lugar">` com `<h2>` "Composição por estado e região", o parágrafo "como ler", uma nota de que a classe das tabelas por estado/região vem do total do lugar (e por isso pode divergir da barra) e as frases geradas da UF.
- Duas `<figure className="folha-quieta flex flex-col gap-3">` (UF e região), cada uma com `DicaGrafico` > `div.overflow-x-auto` > `<svg className="w-full min-w-[480px]" role="img">` com `<title>`/`<desc>`.
- Marcas: linha vertical de 1 px em `var(--border)` por trás das barras, que têm um fundo opaco em `var(--tinta-frio)` para a grade não aparecer através das fatias translúcidas; rótulo embaixo em `text-muted-foreground`, tamanho 11. Sigla à esquerda em `text-foreground`, tamanho 12.
- Alvo de hover por lugar: `<rect>` transparente com `data-dica-titulo` = sigla/região e `data-dica-linhas` = `"{Rótulo} {%}"` das 4 classes + `"{n} votos válidos"`.
- `figcaption`: legenda com amostra de cada classe (mesma cor/opacidade), em `inline-flex`; nota de que o Exterior fica de fora.

- [x] **Step 1: Implementar o componente e o encaixe.**
- [x] **Step 2: Verificar tipos e lint.**
- [x] **Step 3: Verificar no navegador** em `/relatorios/presidente-governador?ano=2026&turno=1&consultar=1`:
  - 27 barras de UF; a primeira é PI (Consolidação 99,05%); a última das empatadas em 0% é TO;
  - frase "Em 16 de 27 UFs a maior parte dos votos válidos de presidente está em municípios em aberto. Nas outras 11, está em municípios em consolidação.";
  - 5 barras de região, na ordem Sul, Nordeste, Norte, Sudeste, Centro-Oeste;
  - tooltip de RN com as 4 fatias ("Consolidação 35,39%", "Terreno de virada 30,63%", "Em aberto 33,98%", "Sem governador 0,00%", "2.071.898 votos válidos"); tema claro e escuro; 375 px com rolagem horizontal; console sem erros novos.
- [x] **Step 4: No commit.**
