# Força da marca: voto de legenda para deputado

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Review between tasks via jarvis:codereview.

**Goal:** Uma página nova, `/relatorios/marca`, mostra para deputado federal e deputado estadual (eleição geral de 2026, 1º turno) quanto do voto de cada partido foi só no número do partido (voto de legenda) e não num candidato. Ela traz um ranking por cargo com a leitura "marca forte", "perto da média" ou "voto na pessoa", uma comparação federal × estadual, a média de cada UF, frases geradas a partir dos dados, tabelas acessíveis e, como passo opcional, um mapa de calor partido × UF. O texto explica de forma simples o que é o voto de legenda.

**Architecture:** Só frontend. A página faz duas chamadas em paralelo a `GET /relatorios/dados/grade?nivel=uf&somente_gravado=true`, uma por cargo. Essa rota já devolve `votos_nominais` e `votos_legenda` por (UF, partido), lidos de `analise.relatorio_poder_linha`, sem ler boletins. Um módulo puro (`lib/grafico-marca.ts`) soma as UFs, classifica, ordena, escreve as frases e calcula os layouts. Ele reaproveita `layoutBarras`, `MEDIDAS_PADRAO`, `MEDIDAS_ESTREITO` e `resumoBarras` de `lib/grafico-poder.ts`. Componentes de servidor desenham os SVGs com `DicaGrafico`. O backend, o banco e o Alembic não mudam.

**Tech Stack:** Next.js 16.4, React 19, TypeScript, Tailwind 4, shadcn/ui. Sem biblioteca de gráficos e sem runner de teste. O script de verificação roda com `node --experimental-strip-types`. Backend FastAPI só como fonte (sem alteração).

**Spec:** Este arquivo. O JSON consumido é o de `GET /relatorios/dados/grade` (`src/eleicoes/adapters/http/relatorios.py:69`), já tipado e validado em `frontend/src/lib/relatorios.ts` (`GradeRelatorio`, `LinhaGrade`, `CelulaGrade`; `lerCelula` exige `votos_nominais` e `votos_legenda`, linhas 335–345) e buscado por `buscarGrade` em `frontend/src/lib/buscar-relatorios.ts:34`, que já envia `somente_gravado=true`.

## Por que só frontend

- Com `nivel=uf`, `RenderPowerReport.grade` (`src/eleicoes/use_cases/render_reports.py:48-74`) filtra as células gravadas desse nível e devolve **todas** as UFs apuradas, qualquer que seja o `uf` da consulta. O `uf` só ancora a validação (`_GRADE`, `relatorios.py:39-45`). Assim, uma chamada por cargo traz a matriz UF × partido inteira: 27 linhas para deputado federal e 26 para deputado estadual (sem DF).
- Cada célula já separa `votos_nominais` e `votos_legenda` (`CelulaJson`, `schemas_relatorios.py:25-38`).
- O total nacional é a soma das linhas UF. Essa soma foi conferida no banco em 2026-10-22: para deputado federal dá 3.438.422 de legenda em 114.107.982 votos, e para deputado estadual dá 7.204.172 em 111.662.018, os mesmos números das linhas `nivel='pais'`. Deputado não tem voto no exterior (ZZ), então a soma não perde nada.
- Sem relatório gravado, a rota responde 409 com a mensagem de `MissingPowerReportError` (`domain/errors.py:215`, `adapters/http/errors.py:56`), e `buscarGrade` devolve `{ ok: false, detalhe }`.
- Não precisa de endpoint, tabela nem migração. Este plano não usa nenhuma revisão: a `0004` é do plano 2 e a `0005` do plano 6 (alinhado em 2026-10-22).

## Decisões

| # | Pergunta | Decisão |
|---|---|---|
| D1 | Fonte | Duas chamadas `buscarGrade("2026", "1", "AC", cargo, "uf")`, uma para `deputadoFederal` e outra para `deputadoEstadual`, em `Promise.all`. `"AC"` é só a âncora (é o padrão de `ufDeConsulta`). O total nacional é a soma das linhas. `nivel=pais` não é pedido. |
| D2 | Recorte fixo | Ano 2026, turno 1. A página não tem filtro nem botão "Consultar", porque deputado não tem 2º turno (turno 2 daria 409) e só existe o ano 2026. O subtítulo diz "Eleição geral de 2026, 1º turno". `FiltrosCurtos` não é usado nem alterado. |
| D3 | Indicador | Para cada partido: `legenda / (nominais + legenda)`, a "parte de legenda". Exibido com `formatarPercentualContagem(legenda, votos)` (exato, "33,33%"). O número em ponto flutuante serve só para a geometria. |
| D4 | Média do cargo | A mesma conta com todos os partidos juntos, inclusive os que ficam fora do ranking: `Σlegenda / Σvotos`. Em 2026, ela dá 3,01% para federal e 6,45% para estadual. Também é calculada por UF. |
| D5 | Limiares relativos | Cada partido é comparado com a média do próprio cargo, porque a média de estadual é cerca do dobro da de federal e um corte absoluto marcaria quase todos como "voto na pessoa". **Marca forte**: parte ≥ 2 × média (`legenda·Vcargo ≥ 2·Lcargo·votos`). **Voto na pessoa**: parte ≤ média ÷ 2 (`2·legenda·Vcargo ≤ Lcargo·votos`). Entre os dois, **perto da média**. A conta é exata, com `BigInt`. Se `Lcargo = 0`, todos ficam "perto da média" e o múltiplo vira "—". |
| D6 | Múltiplo da média | `formatarVezes` mostra a parte ÷ média com 2 casas e arredondamento meio para cima, sempre com "×" ("2,47×"). Um partido logo abaixo de 0,5 aparece como "0,50×" e com a leitura "voto na pessoa" (em 2026, PV 43 estadual, com 0,4966). Isso é aceito. |
| D7 | Partidos pequenos | Só entram no ranking os partidos com **≥ 100.000 votos** (nominais + legenda) no cargo, no Brasil. Os que têm de 1 a 99.999 votos vão para `fora`, que é mostrado numa frase e no fim de cada tabela, e nunca é descartado em silêncio. Partido com 0 voto no cargo não aparece. Motivo: abaixo de 100 mil votos ficam partidos com poucos candidatos, cuja parte de legenda (13% a 66%) mede a falta de candidato, não a marca. Em 2026, ficam fora 6 partidos em federal (PCO, PSTU, MOBILIZA, UP, AGIR, DEMOCRATA) e 4 em estadual (PCB, PCO, PSTU, UP). REDE entra nos dois (264 mil e 483 mil votos) e lidera os dois rankings. |
| D8 | Célula UF × partido | `estadoCelula(nominais, legenda)`. Total 0 dá `"sem-votos"` ("—"). Nominal 0 com legenda > 0 dá `"sem-candidato"`: em 2026 há 43 dessas células (até 2.287 votos), de partido sem candidato na UF. Total < **5.000** dá `"poucos"`. O resto dá `"ok"`. Só `"ok"` recebe cor e percentual no mapa de calor. Nenhuma célula vazia aparece como 0%. |
| D9 | Ordem | Parte de legenda decrescente, comparada em produto cruzado (`BigInt`). Empate vai para quem tem mais votos e, depois, para o menor número de partido. A mesma ordem vale para `fora`. As UFs seguem a ordem da grade (por nome). |
| D10 | Federal × estadual | Entram os partidos que estão nos dois rankings, na ordem do ranking federal. Para não confundir com a diferença entre as médias dos cargos, a comparação usa o múltiplo da média de cada cargo (D6), não a parte bruta. A frase destaca o partido com maior `|múltiplo estadual − múltiplo federal|` (exato, `BigInt`; empate vai para o menor número). Se a maior diferença for 0, não há frase. |
| D11 | DF | O DF elege deputados distritais. `deputadoDistrital` não está entre os 5 cargos gravados, então a grade de estadual tem 26 UFs. A frase nacional de estadual diz "(sem o DF, que elege deputados distritais)", e a explicação repete isso. A média nacional de federal inclui o DF. |
| D12 | Federações | Cada partido aparece com o próprio número. O voto de legenda conta para o número digitado (`partido_do_numero("legenda", n) = n`, `domain/boletim_consulta.py:391`). Não há agregação por federação (pergunta em aberto Q2). |
| D13 | Visual principal | Barras horizontais com a parte de legenda por partido (uma figura por cargo), escala ao maior valor entre as barras e a média, e uma linha tracejada vertical na média do cargo. A opacidade segue a leitura: forte 1, média 0,55, pessoa 0,25. Barras 100% empilhadas nominal × legenda foram **rejeitadas**: para os partidos grandes, a legenda fica entre 1% e 12% e viraria uma fatia invisível. Barras divergentes nominal × legenda também foram rejeitadas, porque o lado nominal teria ~90% em todos e não diferenciaria ninguém. A linha da média dá a mesma leitura ("acima ou abaixo") sem esse problema. |
| D14 | Visual de comparação | Halteres: uma linha por partido, um círculo cheio no múltiplo federal e um vazado no estadual, ligados por um traço. Eixo em "× a média do cargo", de 0 até `max(2, maior múltiplo)`. Linhas de referência em 0,5×, 1× e 2× (os limiares de D5). O rótulo de uma referência some se ficar perto demais do anterior. A forma distingue os cargos, não só a cor. |
| D15 | Indicador por UF | Obrigatório: `TabelaMarcaUf`, uma por cargo (Task 5). Linhas são as UFs da grade. A primeira coluna é a média da UF. As outras são os partidos do ranking. Cada célula mostra `celula.texto`. Fora de `"ok"`, a célula mostra "—" e um motivo em `sr-only` ("sem votos", "sem candidato" ou "menos de 5.000 votos"). O padrão é o de `tabela-poder.tsx` (partidos nas colunas, lugares nas linhas, rolagem horizontal), mas sem ordenação, sem estado e sem cor. O **mapa de calor** é o visual opcional por cima dessa tabela (Task 8): linhas com o ranking do cargo, colunas com as UFs da grade. A cor `--tinta-quente` tem opacidade proporcional à parte de legenda dividida pela maior parte entre as células `"ok"` do cargo. As células fora de `"ok"` ficam com `var(--muted)` e a dica explica o motivo. Sem variante estreita: fica num `overflow-x-auto` com `min-w-[560px]`, com a tabela abaixo como caminho acessível. É a única exceção à regra de variante estreita, e a `TabelaMarcaUf` é o caminho acessível. |
| D16 | Erros | Se as duas chamadas falham, aparece um `ErroRelatorio` com o detalhe da federal. Se só uma falha, as frases e a seção do cargo que funcionou aparecem, e a seção do outro cargo mostra `ErroRelatorio` com o próprio detalhe. Os halteres só aparecem com os dois cargos. |
| D17 | Contrato com o Placar (plano 1) | `fatiaLegendaNacional(grade)` devolve `Map<partido, { legenda, votos, texto }>` para **todo** partido com votos > 0, sem mínimo, ordenado pelo número. É a definição oficial de "% de voto de legenda nacional" (D3 sobre a soma das UFs de `nivel=uf`). O Placar deve importar esta função ou, se calcular no backend, usar a mesma fórmula. Veja Q3. **Consumo opcional (alinhado em 2026-10-22):** o placar não depende deste plano nas fases A, B e C. Na fase D do plano 1, o padrão é um link para `/relatorios/marca` (Task 19 de lá). A coluna opcional de voto de legenda (Task 20 de lá) é calculada **no backend do placar**, que já lê `deputadoFederal` e `deputadoEstadual` no nível `uf`. Ela usa esta mesma fórmula sobre a soma das UFs e tem um teste cruzado com os mesmos números: federal 3,01% (3.438.422 de 114.107.982) e estadual 6,45% (7.204.172 de 111.662.018). Esta função continua sendo a definição oficial, e não muda de nome. |
| D18 | Acessibilidade | `<svg role="img">` com `<title>` e `<desc>` (o `<desc>` traz todos os valores). A dica só aparece com ponteiro. Duas tabelas (uma por cargo) trazem tudo, inclusive `fora`. A leitura vem em texto, não só na opacidade. |

## Global Constraints

- **Arquivos novos** têm "marca" no nome: `lib/grafico-marca.ts`, `lib/verificar-grafico-marca.ts`, `components/relatorios/{dados-marca,explicacao-marca,grafico-marca,grafico-marca-cargos,tabela-marca,tabela-marca-uf,mapa-calor-marca}.tsx` e `app/relatorios/marca/page.tsx`.
- **Arquivos compartilhados modificados** (só uma entrada em cada): `components/layout/app-sidebar.tsx` (`ITENS`), `components/layout/app-breadcrumb.tsx` (`TRILHAS`) e `app/page.tsx` (`DESTINOS`). **Ponto de conflito:** os 6 planos de força partidária mexem nesses três arquivos. Quem integrar por último resolve, mantendo a ordem 1–6 num bloco contínuo **depois de "Classe do governador"** e antes de "Mapa": Força partidária, Cadeiras, Capilaridade, Verticalização, Força da marca, Municipais 2024 (alinhado em 2026-10-22; antes dizia "logo depois de Poder", o que punha o bloco antes de Perfis e Classe do governador).
- **Integração (alinhado em 2026-10-22):** a ordem dos planos é 2 → 6 → 1 (fases A, B e C), e este plano entra em qualquer momento, só por adição. A tabela de quem toca cada arquivo compartilhado está no plano 1, na seção "Integração entre os planos de 2026-10-22". Definições comuns: votos válidos = nominais + legenda; DF sem deputado estadual gravado (D11); deputado não tem exterior.
- `grafico-poder.ts`, `relatorios.ts`, `buscar-relatorios.ts`, `fracao.ts`, `partidos.ts`, `eleicoes.ts`, `dica-grafico.tsx` e o backend **não mudam**. Só são importados.
- Em `lib/grafico-marca.ts`, os imports de `./relatorios.ts` são **só `import type`**, porque `relatorios.ts` importa `@/lib/eleicoes` em tempo de execução, e o node com strip-types não resolve o alias. Os imports de valor usam caminho relativo com `.ts`: `./fracao.ts`, `./partidos.ts`, `./grafico-poder.ts`, `./largura-texto.ts`.
- Sem dependência nova, sem migração, sem tabela nova. Sem commit, a não ser que o usuário peça (nesse caso, use jarvis:commit). Nenhum git que muda estado (stash, checkout, reset).
- Mensagens ao usuário em português. Comentários de código, se houver, em inglês e só quando explicam um "porquê".
- **Verificação** (de `frontend/`):
  - `node --experimental-strip-types src/lib/verificar-grafico-marca.ts`, que imprime `ok`;
  - `pnpm exec tsc --noEmit`, sem saída;
  - `pnpm exec eslint <arquivos novos e modificados>`, sem saída.

## Review Focus

- A conta é exata em toda decisão (classe, ordem, maior mudança, UF extrema)? O float só pode aparecer em geometria e em `indice`.
- `fora` nunca some, e partido zerado nunca aparece.
- A média do cargo inclui os partidos de `fora` (D4).
- Uma célula `"sem-votos"`, `"sem-candidato"` ou `"poucos"` nunca vira "0,00%".
- A frase nacional de estadual menciona o DF.
- O 409 de um só cargo não derruba a página inteira (D16).
- Desempenho: cada chamada faz `store.load`, que lê todas as linhas gravadas do cargo, em todos os níveis (`postgres_relatorio_poder.py:105-111`). A página `/relatorios/poder` já faz isso. Medir no navegador (Task 7). Se passar de ~5 s, abrir uma tarefa de backend para filtrar por nível no SQL. Isso fica fora deste plano.
- Conflito nos três arquivos de navegação (Global Constraints).

## Verificação antes de começar

```bash
cd /run/media/marvinbraga/dados/marvin/eleicoes_brasil_tse_download/frontend
node --version            # Esperado: v22 ou mais novo (suporta --experimental-strip-types)
pnpm --version            # Esperado: 9 ou mais novo
git status --short        # Esperado: vazio
curl -s "http://localhost:15000/relatorios/dados/grade?ano=2026&turno=1&uf=AC&cargo=deputadoFederal&nivel=uf&somente_gravado=true" \
  | python3 -c 'import json,sys; g=json.load(sys.stdin); c=[x for l in g["linhas"] for x in l["celulas"]]; print(len(g["linhas"]), sum(x["votos_legenda"] for x in c), sum(x["votos"] for x in c))'
# Esperado: 27 3438422 114107982
curl -s "http://localhost:15000/relatorios/dados/grade?ano=2026&turno=1&uf=AC&cargo=deputadoEstadual&nivel=uf&somente_gravado=true" \
  | python3 -c 'import json,sys; g=json.load(sys.stdin); c=[x for l in g["linhas"] for x in l["celulas"]]; print(len(g["linhas"]), sum(x["votos_legenda"] for x in c), sum(x["votos"] for x in c))'
# Esperado: 26 7204172 111662018
```

Se o `curl` falhar, suba a API com `docker compose up -d api`, na raiz do repositório. Se a resposta for `{"detail": "O relatório de poder de ... ainda não foi gravado. ..."}`, pare e avise o humano: o relatório precisa ser gravado antes.

---

### Task 1: Núcleo puro (contagem, classe, ranking, células)

**Files:**
- Create: `frontend/src/lib/grafico-marca.ts`
- Test: `frontend/src/lib/verificar-grafico-marca.ts`

**Interfaces:**
- Consumes: `formatarInteiro` e `formatarPercentualContagem` de `./fracao.ts`; `rotuloPartido` de `./partidos.ts`; `import type { GradeRelatorio, LinhaGrade }` de `./relatorios.ts`.
- Produces:
  ```ts
  export const MINIMO_VOTOS_RANKING = 100_000, MINIMO_VOTOS_UF = 5_000, FATOR_LIMIAR = 2;
  export type CargoMarca = "deputadoFederal" | "deputadoEstadual";
  export const CARGOS_MARCA: readonly CargoMarca[] = ["deputadoFederal", "deputadoEstadual"];
  export const ROTULOS_CARGO_MARCA: Record<CargoMarca, string> =
    { deputadoFederal: "deputado federal", deputadoEstadual: "deputado estadual" };
  export type ClasseMarca = "forte" | "media" | "pessoa";
  export const ROTULOS_CLASSE_MARCA: Record<ClasseMarca, string> =
    { forte: "Marca forte", media: "Perto da média", pessoa: "Voto na pessoa" };
  export type EstadoCelula = "ok" | "poucos" | "sem-candidato" | "sem-votos";
  export type PartidoMarca = {
    partido: number; rotulo: string; nominais: number; legenda: number; votos: number;
    texto: string;   // "33,33%"
    vezes: string;   // "2,47×" ou "—"
    indice: number;  // float, só geometria: (legenda/votos)/(Lcargo/Vcargo); 0 se Lcargo = 0
    classe: ClasseMarca;
  };
  export type CelulaMarca = { partido: number; nominais: number; legenda: number; votos: number; texto: string; estado: EstadoCelula };
  export type UfMarca = { uf: string; nome: string; legenda: number; votos: number; texto: string; celulas: CelulaMarca[] };
  export type MarcaCargo = {
    cargo: CargoMarca; rotulo: string; legenda: number; votos: number; texto: string;
    ranking: PartidoMarca[]; fora: PartidoMarca[]; ufs: UfMarca[];
  };
  export function estadoCelula(nominais: number, legenda: number): EstadoCelula;
  export function classeMarca(legenda: number, votos: number, legendaCargo: number, votosCargo: number): ClasseMarca;
  export function formatarVezes(legenda: number, votos: number, legendaCargo: number, votosCargo: number): string;
  export function marcaDoCargo(cargo: CargoMarca, grade: GradeRelatorio): MarcaCargo | null; // null se Σvotos = 0
  ```

Regras da implementação:
- **Soma:** para cada partido, somar `votos_nominais` e `votos_legenda` de todas as linhas. O total do cargo soma todos os partidos.
- **`classeMarca`:** usa `BigInt`. Se `legendaCargo === 0` ou `votos === 0`, devolve `"media"`. Se `legenda·votosCargo ≥ FATOR_LIMIAR·legendaCargo·votos`, devolve `"forte"`. Se `FATOR_LIMIAR·legenda·votosCargo ≤ legendaCargo·votos`, devolve `"pessoa"`. Nos outros casos, `"media"`.
- **`formatarVezes`:** se `legendaCargo === 0` ou `votos === 0`, devolve `"—"`. Senão, calcula `num = legenda·votosCargo·100n` e `den = votos·legendaCargo`, depois `q = num / den` e soma 1 se `(num % den)·2n ≥ den`. O texto é `` `${q / 100n},${String(q % 100n).padStart(2, "0")}×` ``.
- **Ordem (D9):** a comparação é `cruz = BigInt(b.legenda)·BigInt(a.votos) − BigInt(a.legenda)·BigInt(b.votos)`. Se `cruz > 0`, b vem antes. Se empatar, vence quem tem mais votos e, depois, o menor `partido`.
- **`ranking` e `fora`:** `ranking` tem `votos ≥ MINIMO_VOTOS_RANKING`, e `fora` tem `0 < votos < MINIMO_VOTOS_RANKING`. Partido com `votos = 0` não entra em nenhum dos dois.
- **`ufs`:** uma entrada por linha, na ordem da grade. `uf` vem de `linha.codigo` e `nome` de `linha.nome`. `texto` é `formatarPercentualContagem(Σlegenda, Σvotos)`, ou `"—"` se `Σvotos = 0`. `celulas` traz só os partidos do `ranking`, na ordem do ranking. `texto` da célula é o percentual se o estado for `"ok"`, ou `"—"` nos outros casos.
- **`estadoCelula`:** se `nominais + legenda === 0`, devolve `"sem-votos"`. Se `nominais === 0`, devolve `"sem-candidato"`. Se `nominais + legenda < MINIMO_VOTOS_UF`, devolve `"poucos"`. Nos outros casos, `"ok"`.

- [x] **Step 1: Escrever o teste.** Criar `frontend/src/lib/verificar-grafico-marca.ts` com o conteúdo abaixo. As Tasks 2 e 3 acrescentam blocos antes do `console.log("ok")` final.

```ts
import assert from "node:assert/strict";
import {
  MINIMO_VOTOS_RANKING,
  classeMarca,
  estadoCelula,
  formatarVezes,
  marcaDoCargo,
  type MarcaCargo,
} from "./grafico-marca.ts";
import type { GradeRelatorio, LinhaGrade } from "./relatorios.ts";

type Par = [nominais: number, legenda: number];

function linha(codigo: string, nome: string, votos: Record<number, Par>): LinhaGrade {
  return {
    codigo,
    nome,
    comparecimento: 0,
    celulas: Object.entries(votos).map(([partido, [nominais, legenda]]) => ({
      partido: Number(partido),
      votos_nominais: nominais,
      votos_legenda: legenda,
      comparecimento: 0,
      votos: nominais + legenda,
      fatia: "0",
    })),
  };
}

function grade(cargo: string, linhas: LinhaGrade[]): GradeRelatorio {
  return { ano: 2026, turno: 1, uf: "AC", cargo, nivel: "uf", colunas: [], linhas };
}

const gradeFederal = grade("deputadoFederal", [
  linha("AC", "Acre", { 12: [40_000, 10_000], 13: [90_000, 10_000], 16: [1_000, 1_000], 18: [0, 2_000], 20: [49_500, 500] }),
  linha("BA", "Bahia", { 12: [60_000, 40_000], 13: [180_000, 20_000], 16: [0, 0], 18: [3_000, 1_000], 20: [99_000, 1_000] }),
  linha("DF", "Distrito Federal", { 12: [0, 0], 13: [27_000, 3_000], 16: [0, 0], 18: [0, 0], 20: [19_800, 200] }),
]);
const gradeEstadual = grade("deputadoEstadual", [
  linha("AC", "Acre", { 12: [45_000, 5_000], 13: [80_000, 20_000], 16: [0, 0], 18: [500, 500], 20: [58_800, 1_200] }),
  linha("BA", "Bahia", { 12: [90_000, 10_000], 13: [160_000, 40_000], 16: [0, 0], 18: [0, 0], 20: [117_600, 2_400] }),
]);
const federal = marcaDoCargo("deputadoFederal", gradeFederal) as MarcaCargo;
const estadual = marcaDoCargo("deputadoEstadual", gradeEstadual) as MarcaCargo;

// total do cargo: soma das UFs, inclusive os partidos fora do ranking
assert.equal(federal.rotulo, "deputado federal");
assert.equal(federal.legenda, 88_700);
assert.equal(federal.votos, 658_000);
assert.equal(federal.texto, "13,48%");
assert.equal(estadual.texto, "12,54%");

// ranking: ordem, parte, múltiplo e classe relativos à média do cargo
const resumir = (marca: MarcaCargo) =>
  marca.ranking.map((item) => [item.rotulo, item.texto, item.vezes, item.classe]);
assert.deepEqual(resumir(federal), [
  ["PDT 12", "33,33%", "2,47×", "forte"],
  ["PT 13", "10,00%", "0,74×", "media"],
  ["PODE 20", "1,00%", "0,07×", "pessoa"],
]);
assert.deepEqual(resumir(estadual), [
  ["PT 13", "20,00%", "1,60×", "media"],
  ["PDT 12", "10,00%", "0,80×", "media"],
  ["PODE 20", "2,00%", "0,16×", "pessoa"],
]);
assert.ok(Math.abs(federal.ranking[0].indice - (50_000 / 150_000) / (88_700 / 658_000)) < 1e-12);

// fora do ranking: listados, nunca descartados; partido zerado não aparece
assert.deepEqual(federal.fora.map((item) => [item.rotulo, item.texto, item.votos]), [
  ["REDE 18", "50,00%", 6_000],
  ["PSTU 16", "50,00%", 2_000],
]);
assert.deepEqual(estadual.fora.map((item) => item.rotulo), ["REDE 18"]);
assert.ok(![...estadual.ranking, ...estadual.fora].some((item) => item.partido === 16));

// limiares exatos: 2× é forte, 0,5× é pessoa; empate pelo número
const limiar = marcaDoCargo("deputadoFederal", grade("deputadoFederal", [
  linha("SP", "São Paulo", { 10: [80_000, 20_000], 11: [95_000, 5_000], 15: [95_000, 5_000] }),
])) as MarcaCargo;
assert.equal(limiar.texto, "10,00%");
assert.deepEqual(resumir(limiar), [
  ["REPUBLICANOS 10", "20,00%", "2,00×", "forte"],
  ["PP 11", "5,00%", "0,50×", "pessoa"],
  ["MDB 15", "5,00%", "0,50×", "pessoa"],
]);
assert.equal(classeMarca(1, 100, 1, 50), "pessoa");
assert.equal(classeMarca(2, 100, 1, 50), "media");
assert.equal(classeMarca(4, 100, 1, 50), "forte");
assert.equal(classeMarca(5, 100, 0, 50), "media");
assert.equal(formatarVezes(5, 100, 0, 50), "—");
assert.equal(formatarVezes(1, 3, 1, 1), "0,33×");
assert.equal(formatarVezes(2, 3, 1, 1), "0,67×");

// mínimo de votos: 99.999 fica fora, 100.000 entra; sem legenda no cargo, tudo "media"
const minimo = marcaDoCargo("deputadoFederal", grade("deputadoFederal", [
  linha("SP", "São Paulo", { 55: [MINIMO_VOTOS_RANKING - 1, 0], 70: [MINIMO_VOTOS_RANKING, 0] }),
])) as MarcaCargo;
assert.deepEqual(minimo.ranking.map((item) => [item.rotulo, item.classe, item.vezes]), [["AVANTE 70", "media", "—"]]);
assert.deepEqual(minimo.fora.map((item) => item.rotulo), ["PSD 55"]);

// empate de parte: mais votos primeiro, depois o menor número
const empate = marcaDoCargo("deputadoFederal", grade("deputadoFederal", [
  linha("RJ", "Rio de Janeiro", { 50: [90_000, 10_000], 22: [180_000, 20_000], 40: [90_000, 10_000], 13: [90_000, 10_000] }),
])) as MarcaCargo;
assert.deepEqual(empate.ranking.map((item) => item.rotulo), ["PL 22", "PT 13", "PSB 40", "PSOL 50"]);

// cargo sem votos
assert.equal(marcaDoCargo("deputadoFederal", grade("deputadoFederal", [linha("AC", "Acre", { 13: [0, 0] })])), null);
assert.equal(marcaDoCargo("deputadoFederal", grade("deputadoFederal", [])), null);

// estado da célula UF × partido
assert.equal(estadoCelula(0, 0), "sem-votos");
assert.equal(estadoCelula(0, 2_287), "sem-candidato");
assert.equal(estadoCelula(4_000, 999), "poucos");
assert.equal(estadoCelula(4_000, 1_000), "ok");

// UFs: média por UF e células só dos partidos do ranking, na ordem do ranking
assert.deepEqual(federal.ufs.map((uf) => [uf.uf, uf.nome, uf.texto]), [
  ["AC", "Acre", "11,52%"],
  ["BA", "Bahia", "15,35%"],
  ["DF", "Distrito Federal", "6,40%"],
]);
assert.deepEqual(federal.ufs[2].celulas.map((celula) => [celula.partido, celula.texto, celula.estado]), [
  [12, "—", "sem-votos"],
  [13, "10,00%", "ok"],
  [20, "1,00%", "ok"],
]);
assert.deepEqual(federal.ufs[1].celulas.map((celula) => celula.texto), ["40,00%", "10,00%", "1,00%"]);
assert.deepEqual(estadual.ufs.map((uf) => [uf.uf, uf.texto]), [["AC", "12,65%"], ["BA", "12,48%"]]);

console.log("ok");
```

- [x] **Step 2: Rodar e ver falhar.**
  Run: `cd frontend && node --experimental-strip-types src/lib/verificar-grafico-marca.ts`
  Expected: erro `ERR_MODULE_NOT_FOUND` citando `grafico-marca.ts`.

- [x] **Step 3: Implementar** `frontend/src/lib/grafico-marca.ts` seguindo as Interfaces e as Regras acima. Funções internas sugeridas: `somarPorPartido(linhas): Map<number, { nominais: number; legenda: number }>`, `compararMarca(a, b): number` e `partidoMarca(partido, contagem, legendaCargo, votosCargo): PartidoMarca`.

- [x] **Step 4: Rodar até passar.**
  Run: `cd frontend && node --experimental-strip-types src/lib/verificar-grafico-marca.ts`
  Expected: `ok`
  Run: `pnpm exec tsc --noEmit && pnpm exec eslint src/lib/grafico-marca.ts src/lib/verificar-grafico-marca.ts`
  Expected: nenhuma saída.

**If Task Fails:**
1. `ERR_UNSUPPORTED_NODE_SCHEME` ou erro de alias: algum import de `./relatorios.ts` não é `import type`.
2. Percentual errado por 0,01: o arredondamento deve vir de `formatarPercentualContagem`, não de `toFixed`.
3. Ordem errada no empate: confira o sinal de `cruz` e o desempate por votos e, depois, por número.
4. Sem saída depois de 3 tentativas: anote o assert que falha e pare.

---

### Task 2: Frases, comparação entre cargos e contrato do Placar

**Files:**
- Modify: `frontend/src/lib/grafico-marca.ts`
- Modify: `frontend/src/lib/verificar-grafico-marca.ts` (acrescentar antes de `console.log("ok")` e importar os nomes novos)

**Interfaces:**
- Produces:
  ```ts
  export type LegendaPartido = { legenda: number; votos: number; texto: string };
  export function fatiaLegendaNacional(grade: GradeRelatorio): Map<number, LegendaPartido>; // D17
  export type ParCargos = { partido: number; rotulo: string; federal: PartidoMarca; estadual: PartidoMarca };
  export type ComparacaoCargos = { pares: ParCargos[]; maisMuda: ParCargos | null };
  export function comparacaoCargos(federal: MarcaCargo, estadual: MarcaCargo): ComparacaoCargos;
  export function leituraMarca(federal: MarcaCargo | null, estadual: MarcaCargo | null): string[];
  ```

Modelos das frases (`C` = `ROTULOS_CARGO_MARCA[cargo]`, `M` = texto da média do cargo, `X (p)` = `` `${rotulo} (${texto})` ``, `juntar` = "a, b e c"). A ordem de saída é esta:
1. **Nacional.** Com os dois cargos: `No Brasil, ${Mf} dos votos para deputado federal foram só no número do partido. Para deputado estadual, foram ${Me} (sem o DF, que elege deputados distritais).` Só federal: a primeira oração. Só estadual: `No Brasil, ${Me} dos votos para deputado estadual foram só no número do partido (sem o DF, que elege deputados distritais).`
2. **Por cargo** (federal e depois estadual), nesta ordem:
   - forte, com 1 partido: `Marca forte para ${C}: ${rotulo}, com ${texto} de voto de legenda, pelo menos o dobro da média do cargo (${M}).`
   - forte, com n ≥ 2: `Marca forte para ${C}: ${juntar(X (p))}, cada um com pelo menos o dobro da média do cargo (${M}).`
   - forte, com 0: `Para ${C}, nenhum partido do ranking chega ao dobro da média do cargo (${M}).`
   - pessoa, com 1: `Voto na pessoa para ${C}: ${rotulo}, com ${texto} de voto de legenda, no máximo a metade da média do cargo (${M}).`
   - pessoa, com n ≥ 2: `Voto na pessoa para ${C}: ${juntar(X (p))}, cada um com no máximo a metade da média do cargo (${M}).`
   - pessoa, com 0: `Para ${C}, nenhum partido do ranking fica abaixo da metade da média do cargo (${M}).`
3. **Comparação** (só com os dois cargos e `maisMuda !== null`): `${rotulo} é o partido cuja marca mais muda entre os cargos: para deputado federal, tem ${f.texto} de voto de legenda (${f.vezes} a média do cargo); para deputado estadual, ${e.texto} (${e.vezes} a média do cargo).`
4. **UF** (por cargo, entre as UFs com votos > 0, com comparação exata; empate vai para o primeiro nome em `localeCompare("pt-BR")`): `Para ${C}, a UF com mais voto de legenda é ${nomeMax} (${textoMax}) e a com menos é ${nomeMin} (${textoMin}).` Com uma UF só: `Para ${C}, a única UF é ${nome}, com ${texto} de voto de legenda.`
5. **Fora** (por cargo, só se `fora` não estiver vazio): `Fora do ranking de ${C}, por terem menos de ${formatarInteiro(MINIMO_VOTOS_RANKING)} votos: ${juntar(`${rotulo} (${texto} de legenda em ${formatarInteiro(votos)} votos)`)}.`

Regras de `comparacaoCargos`:
- `pares` traz os partidos presentes nos dois `ranking`, na ordem do ranking federal.
- `maisMuda` é o par com maior `|ie − if|`, em que `i = (legenda·Vcargo)/(votos·Lcargo)`. A conta é exata com `BigInt`: `n = le·Ve·tf·Lf − lf·Vf·te·Le` e `d = te·Le·tf·Lf`, e a comparação de `|n1|/d1` com `|n2|/d2` é por produto cruzado. Empate vai para o menor número. Se o maior `|n|` for 0 ou algum `L` for 0, `maisMuda` é `null`.
- `fatiaLegendaNacional` soma as linhas da grade, mantém `votos > 0`, devolve um `Map` inserido em ordem crescente de partido e calcula `texto` com `formatarPercentualContagem`.

- [x] **Step 1: Acrescentar os testes** (antes de `console.log("ok")`; incluir `comparacaoCargos`, `fatiaLegendaNacional` e `leituraMarca` no import):

```ts
// contrato do Placar: todo partido com votos, sem mínimo, em ordem de número
assert.deepEqual(
  [...fatiaLegendaNacional(gradeFederal).entries()].map(([partido, item]) => [partido, item.legenda, item.votos, item.texto]),
  [
    [12, 50_000, 150_000, "33,33%"],
    [13, 33_000, 330_000, "10,00%"],
    [16, 1_000, 2_000, "50,00%"],
    [18, 3_000, 6_000, "50,00%"],
    [20, 1_700, 170_000, "1,00%"],
  ],
);

// comparação federal × estadual pelo múltiplo da média de cada cargo
const comparacao = comparacaoCargos(federal, estadual);
assert.deepEqual(comparacao.pares.map((par) => par.rotulo), ["PDT 12", "PT 13", "PODE 20"]);
assert.equal(comparacao.maisMuda?.rotulo, "PDT 12");
assert.equal(comparacaoCargos(minimo, minimo).maisMuda, null);

// leitura com os dois cargos
assert.deepEqual(leituraMarca(federal, estadual), [
  "No Brasil, 13,48% dos votos para deputado federal foram só no número do partido. Para deputado estadual, foram 12,54% (sem o DF, que elege deputados distritais).",
  "Marca forte para deputado federal: PDT 12, com 33,33% de voto de legenda, pelo menos o dobro da média do cargo (13,48%).",
  "Voto na pessoa para deputado federal: PODE 20, com 1,00% de voto de legenda, no máximo a metade da média do cargo (13,48%).",
  "Para deputado estadual, nenhum partido do ranking chega ao dobro da média do cargo (12,54%).",
  "Voto na pessoa para deputado estadual: PODE 20, com 2,00% de voto de legenda, no máximo a metade da média do cargo (12,54%).",
  "PDT 12 é o partido cuja marca mais muda entre os cargos: para deputado federal, tem 33,33% de voto de legenda (2,47× a média do cargo); para deputado estadual, 10,00% (0,80× a média do cargo).",
  "Para deputado federal, a UF com mais voto de legenda é Bahia (15,35%) e a com menos é Distrito Federal (6,40%).",
  "Para deputado estadual, a UF com mais voto de legenda é Acre (12,65%) e a com menos é Bahia (12,48%).",
  "Fora do ranking de deputado federal, por terem menos de 100.000 votos: REDE 18 (50,00% de legenda em 6.000 votos) e PSTU 16 (50,00% de legenda em 2.000 votos).",
  "Fora do ranking de deputado estadual, por terem menos de 100.000 votos: REDE 18 (50,00% de legenda em 1.000 votos).",
]);

// um cargo só, vários "pessoa" e UF única
assert.deepEqual(leituraMarca(limiar, null), [
  "No Brasil, 10,00% dos votos para deputado federal foram só no número do partido.",
  "Marca forte para deputado federal: REPUBLICANOS 10, com 20,00% de voto de legenda, pelo menos o dobro da média do cargo (10,00%).",
  "Voto na pessoa para deputado federal: PP 11 (5,00%) e MDB 15 (5,00%), cada um com no máximo a metade da média do cargo (10,00%).",
  "Para deputado federal, a única UF é São Paulo, com 10,00% de voto de legenda.",
]);
assert.equal(
  leituraMarca(null, estadual)[0],
  "No Brasil, 12,54% dos votos para deputado estadual foram só no número do partido (sem o DF, que elege deputados distritais).",
);
assert.deepEqual(leituraMarca(null, null), []);
```

- [x] **Step 2: Rodar e ver falhar.** Run: `cd frontend && node --experimental-strip-types src/lib/verificar-grafico-marca.ts`. Expected: `SyntaxError: The requested module './grafico-marca.ts' does not provide an export named 'comparacaoCargos'`.
- [x] **Step 3: Implementar** as três funções. `juntar` é local (mesma lógica de `grafico-poder.ts:316-322`, que não é exportada).
- [x] **Step 4: Rodar até `ok`**, depois `pnpm exec tsc --noEmit && pnpm exec eslint src/lib/grafico-marca.ts src/lib/verificar-grafico-marca.ts`, sem saída.

**If Task Fails:**
1. A frase difere por espaço ou pontuação: compare caractere a caractere com `assert.deepEqual`, que mostra o diff.
2. `maisMuda` errado: confira se `n` usa a média do **próprio** cargo de cada lado.
3. Erro de `BigInt` misturado com `number`: converta todos os operandos com `BigInt(...)`.

---

### Task 3: Layouts do ranking e dos halteres

**Files:**
- Modify: `frontend/src/lib/grafico-marca.ts`
- Modify: `frontend/src/lib/verificar-grafico-marca.ts`

**Interfaces:**
- Consumes: `layoutBarras`, `resumoBarras`, `MEDIDAS_PADRAO`, `MEDIDAS_ESTREITO` e `type ItemBarra, Barra, MedidasBarras, LayoutBarras` de `./grafico-poder.ts`; `larguraTexto` de `./largura-texto.ts`.
- Produces:
  ```ts
  export function itensRanking(marca: MarcaCargo): ItemBarra[];
  // chave String(partido); rotulo; valor = legenda/votos (float); texto; detalhe =
  // `${formatarInteiro(legenda)} de ${formatarInteiro(votos)} votos foram de legenda\n${ROTULOS_CLASSE_MARCA[classe]} (${vezes} a média do cargo)`
  export type BarraMarca = Barra & { classe: ClasseMarca };
  export type LayoutRanking = Omit<LayoutBarras, "barras"> & { barras: BarraMarca[]; xReferencia: number };
  export function layoutRanking(marca: MarcaCargo, medidas?: MedidasBarras): LayoutRanking | null;
  // usa layoutBarras para y/altura; escala = max(maior valor, Lcargo/Vcargo); largura = valor/escala*util;
  // xReferencia = esquerda + (Lcargo/Vcargo)/escala*util. null se o ranking estiver vazio.
  export function resumoRanking(marca: MarcaCargo): string;
  // resumoBarras(`Voto de legenda por partido, ${rotulo}, média do cargo ${texto}.`, itensRanking(marca))

  export type MedidasHalteres = { largura: number; esquerda: number; direita: number; topo: number; base: number;
    alturaLinha: number; raio: number; descida: number; rotuloAcima: boolean; fonte: number };
  export const MEDIDAS_HALTERES_PADRAO: MedidasHalteres = { largura: 640, esquerda: 120, direita: 24, topo: 24,
    base: 4, alturaLinha: 28, raio: 5, descida: 0, rotuloAcima: false, fonte: 12 };
  export const MEDIDAS_HALTERES_ESTREITO: MedidasHalteres = { largura: 340, esquerda: 8, direita: 16, topo: 24,
    base: 4, alturaLinha: 42, raio: 5, descida: 8, rotuloAcima: true, fonte: 13 };
  export type Haltere = { chave: string; rotulo: string; y: number; xFederal: number; xEstadual: number; dica: string };
  // dica = `Deputado federal: ${f.texto} (${f.vezes} a média)\nDeputado estadual: ${e.texto} (${e.vezes} a média)`
  export type ReferenciaHalteres = { valor: number; x: number; rotulo: string }; // rotulo "" quando oculto
  export type LayoutHalteres = { medidas: MedidasHalteres; largura: number; altura: number; escala: number;
    halteres: Haltere[]; referencias: ReferenciaHalteres[] };
  export function layoutHalteres(pares: readonly ParCargos[], medidas?: MedidasHalteres): LayoutHalteres | null;
  // escala = max(2, maior indice federal/estadual); x(v) = esquerda + v/escala*util; util = largura-esquerda-direita
  // y = topo + i*alturaLinha + alturaLinha/2 + descida; altura = topo + n*alturaLinha + base
  // referencias em 0.5, 1, 2 com rótulos "0,5×", "1×", "2×"; o rótulo fica "" se a distância ao último rótulo visível
  // for menor que larguraTexto(rotulo, fonte) + 4. null se pares estiver vazio.
  export function resumoHalteres(pares: readonly ParCargos[]): string;
  // `Voto de legenda como múltiplo da média de cada cargo. ${rotulo}: federal ${f.vezes}, estadual ${e.vezes}; ...`.
  ```

- [x] **Step 1: Acrescentar os testes:**

```ts
// ranking: barras da grafico-poder, escala que inclui a média e linha de referência
const itens = itensRanking(federal);
assert.equal(itens[0].detalhe, "50.000 de 150.000 votos foram de legenda\nMarca forte (2,47× a média do cargo)");
const ranking = layoutRanking(federal) as LayoutRanking;
const util = MEDIDAS_PADRAO.largura - MEDIDAS_PADRAO.esquerda - MEDIDAS_PADRAO.direita;
assert.equal(ranking.barras.length, 3);
assert.ok(Math.abs(ranking.barras[0].largura - util) < 1e-9);
assert.deepEqual(ranking.barras.map((barra) => barra.classe), ["forte", "media", "pessoa"]);
assert.ok(Math.abs(ranking.xReferencia - (MEDIDAS_PADRAO.esquerda + ((88_700 / 658_000) / (1 / 3)) * util)) < 1e-9);
// média acima de todas as barras (fora do ranking puxa a média): a escala passa a ser a média
const puxada = marcaDoCargo("deputadoFederal", grade("deputadoFederal", [
  linha("SP", "São Paulo", { 13: [100_000, 1_000], 16: [10_000, 80_000] }),
])) as MarcaCargo;
const layoutPuxado = layoutRanking(puxada) as LayoutRanking;
assert.equal(layoutPuxado.xReferencia, MEDIDAS_PADRAO.largura - MEDIDAS_PADRAO.direita);
assert.ok(layoutPuxado.barras[0].largura < util);
assert.equal(layoutRanking({ ...federal, ranking: [] }), null);
const rankingEstreito = layoutRanking(federal, MEDIDAS_ESTREITO) as LayoutRanking;
assert.ok(rankingEstreito.xReferencia <= MEDIDAS_ESTREITO.largura - MEDIDAS_ESTREITO.direita);
assert.equal(
  resumoRanking(federal),
  "Voto de legenda por partido, deputado federal, média do cargo 13,48%. PDT 12: 33,33%; PT 13: 10,00%; PODE 20: 1,00%.",
);

// halteres: múltiplo da média de cada cargo
const halteres = layoutHalteres(comparacao.pares) as LayoutHalteres;
const mh = MEDIDAS_HALTERES_PADRAO;
const utilH = mh.largura - mh.esquerda - mh.direita;
assert.ok(Math.abs(halteres.escala - (50_000 / 150_000) / (88_700 / 658_000)) < 1e-12);
assert.ok(Math.abs(halteres.halteres[0].xFederal - (mh.largura - mh.direita)) < 1e-9);
assert.equal(halteres.halteres[0].y, mh.topo + mh.alturaLinha / 2);
assert.equal(halteres.altura, mh.topo + 3 * mh.alturaLinha + mh.base);
assert.equal(halteres.halteres[0].dica, "Deputado federal: 33,33% (2,47× a média)\nDeputado estadual: 10,00% (0,80× a média)");
assert.deepEqual(halteres.referencias.map((ref) => ref.rotulo), ["0,5×", "1×", "2×"]);
assert.ok(Math.abs(halteres.referencias[1].x - (mh.esquerda + utilH / halteres.escala)) < 1e-9);
assert.equal(layoutHalteres([]), null);
// escala mínima 2: com múltiplos pequenos, 2× continua dentro do desenho
const pequenos = layoutHalteres(comparacaoCargos(estadual, estadual).pares) as LayoutHalteres;
assert.equal(pequenos.escala, 2);
assert.equal(pequenos.referencias[2].x, mh.largura - mh.direita);
// estreito: rótulo acima da linha, nada passa da borda, rótulos de referência não se sobrepõem
const me = MEDIDAS_HALTERES_ESTREITO;
const estreito = layoutHalteres(comparacao.pares, me) as LayoutHalteres;
for (const [indice, haltere] of estreito.halteres.entries()) {
  const topoLinha = me.topo + indice * me.alturaLinha;
  assert.ok(haltere.y - me.raio - 5 - me.fonte >= topoLinha);
  assert.ok(haltere.y + me.raio <= topoLinha + me.alturaLinha);
  assert.ok(Math.max(haltere.xFederal, haltere.xEstadual) + me.raio <= me.largura);
}
const visiveis = estreito.referencias.filter((ref) => ref.rotulo !== "");
for (let indice = 1; indice < visiveis.length; indice += 1) {
  assert.ok(visiveis[indice].x - visiveis[indice - 1].x >= larguraTexto(visiveis[indice].rotulo, me.fonte) + 4);
}
assert.equal(
  resumoHalteres(comparacao.pares),
  "Voto de legenda como múltiplo da média de cada cargo. PDT 12: federal 2,47×, estadual 0,80×; PT 13: federal 0,74×, estadual 1,60×; PODE 20: federal 0,07×, estadual 0,16×.",
);
```

Acrescente ao import do teste `itensRanking`, `layoutRanking`, `resumoRanking`, `layoutHalteres`, `resumoHalteres`, `MEDIDAS_HALTERES_PADRAO`, `MEDIDAS_HALTERES_ESTREITO`, `type LayoutRanking` e `type LayoutHalteres`, além de `MEDIDAS_PADRAO` e `MEDIDAS_ESTREITO` de `./grafico-poder.ts` e `larguraTexto` de `./largura-texto.ts`.

- [x] **Step 2: Rodar e ver falhar** com `does not provide an export named 'itensRanking'`.
- [x] **Step 3: Implementar.** `layoutRanking` chama `layoutBarras(itensRanking(marca), medidas)` e depois recalcula `largura` de cada barra e acrescenta `classe` (pelo índice, que é o mesmo do ranking) e `xReferencia`.
- [x] **Step 4: Rodar até `ok`.** Depois rodar `tsc` e `eslint` nos dois arquivos, sem saída.

**If Task Fails:**
1. `xReferencia` passa da borda: a escala precisa ser `Math.max(maior, media)`.
2. O teste do estreito falha no topo da linha: o `descida` de `MEDIDAS_HALTERES_ESTREITO` precisa ser 8, como em `grafico-poder.ts`.

---

### Task 4: Code Review

1. **REQUIRED SUB-SKILL:** Use jarvis:codereview: dispatch all reviewers in parallel sobre `frontend/src/lib/grafico-marca.ts` e `frontend/src/lib/verificar-grafico-marca.ts`.
2. **Handle findings by severity:** see jarvis:codereview severity rules.
3. **Proceed only when:** zero Critical/High/Medium issues remain. Foco: exatidão (D5, D9, D10), `fora` nunca some, células vazias nunca viram 0%.

---

### Task 5: Componentes

**Files:**
- Create: `frontend/src/components/relatorios/explicacao-marca.tsx` (servidor)
- Create: `frontend/src/components/relatorios/grafico-marca.tsx` (servidor)
- Create: `frontend/src/components/relatorios/grafico-marca-cargos.tsx` (servidor)
- Create: `frontend/src/components/relatorios/tabela-marca.tsx` (servidor)
- Create: `frontend/src/components/relatorios/tabela-marca-uf.tsx` (servidor)
- Create: `frontend/src/components/relatorios/dados-marca.tsx` (servidor, async)

**Interfaces:**
- `ExplicacaoMarca({ frases }: { frases: readonly string[] })`
- `GraficoMarca({ id, marca }: { id: string; marca: MarcaCargo })`, que devolve `null` se `layoutRanking` der `null`
- `GraficoMarcaCargos({ pares }: { pares: readonly ParCargos[] })`, que devolve `null` se `layoutHalteres` der `null`
- `TabelaMarca({ marca }: { marca: MarcaCargo })`
- `TabelaMarcaUf({ marca }: { marca: MarcaCargo })`, que devolve `null` se `marca.ranking` ou `marca.ufs` estiverem vazios
- `DadosMarca()`, sem props: `ANO = "2026" as const satisfies Ano` e `TURNO = "1" as const satisfies Turno`

**`explicacao-marca.tsx`**: mesmo esqueleto de `explicacao-poder.tsx` (`max-w-3xl`, `<dl>` e lista "Leitura deste recorte"). Texto fixo, nesta ordem:
- Abertura: "Este relatório mostra, para deputado federal e deputado estadual, quanto do voto de cada partido foi dado ao partido e não a um candidato."
- **O que é voto de legenda:** "Para deputado, o eleitor pode digitar o número inteiro de um candidato (4 dígitos para federal, 5 para estadual). Esse é o voto nominal. Ele também pode digitar só os 2 primeiros dígitos, que são o número do partido, e confirmar. Esse é o voto de legenda. Ele conta para o partido na divisão das cadeiras, mas não ajuda nenhum candidato a subir na lista do partido."
- **O indicador:** "É o voto de legenda dividido pelo total de votos válidos do partido (nominais mais legenda). Quanto maior, mais o eleitor escolheu o partido e não uma pessoa."
- **A média do cargo:** "É a mesma conta com todos os partidos juntos. O deputado estadual costuma ter mais voto de legenda que o federal, por isso cada partido é comparado com a média do próprio cargo."
- **Leitura:** "Marca forte: pelo menos o dobro da média do cargo. Voto na pessoa: no máximo a metade. Entre os dois: perto da média."
- **Partidos pequenos:** "Só entram no ranking os partidos com pelo menos 100.000 votos no cargo. Um partido com poucos candidatos recebe boa parte do voto na legenda porque o eleitor não tem em quem votar, e isso não é marca forte. Esses partidos aparecem no fim de cada tabela, fora do ranking."
- **DF e federações:** "O Distrito Federal elege deputados distritais, não estaduais, e não entra nas contas de deputado estadual. Partidos de uma federação concorrem juntos, mas aqui cada um aparece com o próprio número, porque o voto de legenda vai para o número digitado."
- **Como ler:** "Nas barras, cada partido mostra a parte do seu voto que foi de legenda; a linha tracejada é a média do cargo. Nos halteres, o círculo cheio é deputado federal e o vazado é deputado estadual, medidos em vezes a média de cada cargo. Passe o mouse para ver os votos."

**`grafico-marca.tsx`**: mesma estrutura de `grafico-poder.tsx` (figure `folha-quieta`, `DicaGrafico`, desenho largo `hidden sm:block` com `min-w-[480px]`, desenho estreito `sm:hidden`).
- Título: `Voto de legenda por partido, ${marca.rotulo}`.
- Legenda do figcaption: `A linha tracejada marca a média do cargo (${marca.texto}). Barra cheia: marca forte; média: perto da média; clara: voto na pessoa. Só partidos com pelo menos 100.000 votos.`
- `<desc>` com `resumoRanking(marca)`.
- Barra em `var(--tinta-quente)` com `fillOpacity` 1, 0,55 ou 0,25 conforme `barra.classe`.
- Linha de referência: `<line x1=x2={xReferencia} y1={0} y2={altura} stroke="currentColor" className="text-foreground" strokeDasharray="4 3" strokeWidth={1} />`.
- Retângulo transparente de dica por linha, com `data-dica-titulo={barra.rotulo}` e `data-dica-linhas={`${barra.texto}\n${barra.detalhe}`}`.

**`grafico-marca-cargos.tsx`**: mesma moldura.
- Título "Federal × estadual: vezes a média de cada cargo".
- Legenda: "Círculo cheio: deputado federal. Círculo vazado: deputado estadual. A linha 1× é a média do cargo; 2× e 0,5× são os limiares de marca forte e voto na pessoa. Só partidos que estão nos dois rankings."
- Referências tracejadas em `var(--border)`, com rótulo no topo (`y = topo − 8`, `textAnchor="middle"`, `text-muted-foreground`) quando `rotulo !== ""`.
- O traço entre os círculos usa `stroke="var(--border)"` com 2 px.
- Federal: `<circle fill="var(--tinta-quente)">`. Estadual: `<circle fill="var(--background)" stroke="var(--tinta-quente)" strokeWidth={2}>`.
- Rótulo do partido igual ao de `grafico-poder.tsx`: à esquerda, ou acima quando `rotuloAcima`.
- Dica por linha com `haltere.dica`.

**`tabela-marca.tsx`**: mesmo padrão de `tabela-acerto-uf.tsx` (`Table containerClassName="folha"`, `TableCaption sr-only`).
- Caption: `Voto de legenda, ${marca.rotulo}`.
- Colunas: Partido | Votos | Legenda | % de legenda | Vezes a média | Leitura.
- Linhas: o `ranking`, com a leitura em `ROTULOS_CLASSE_MARCA`, e depois o `fora`, com a leitura "Fora do ranking (menos de 100.000 votos)".
- Rodapé: uma linha `Todos os partidos` com `marca.votos`, `marca.legenda`, `marca.texto`, `1,00×` e "Média do cargo".
- Números com `formatarInteiro` e `tabular-nums text-right`.

**`tabela-marca-uf.tsx`** (D15): `Table containerClassName="folha"` (a rolagem horizontal vem do contêiner da tabela, como em `tabela-poder.tsx`).
- Caption visível: `Voto de legenda por UF, ${marca.rotulo}`, com a nota "Cada célula é a parte do voto do partido na UF que foi de legenda. Só partidos do ranking."
- Cabeçalho: `UF` | `Média da UF` | um `TableHead scope="col"` por partido do ranking, com `rotulo` e na ordem do ranking.
- Linhas: uma por `marca.ufs`, com `TableHead scope="row"` igual a `uf.nome`, depois `uf.texto` e depois uma célula por `uf.celulas` (`text-right tabular-nums`).
- Uma célula fora de `"ok"` mostra `—` e `<span className="sr-only">` com `sem votos`, `sem candidato` ou `menos de 5.000 votos`. Esse mapa de estado para motivo fica no próprio componente.
- Sem ordenação, sem cor e sem `"use client"`.

**`dados-marca.tsx`**:
```tsx
const [respostaFederal, respostaEstadual] = await Promise.all(
  CARGOS_MARCA.map((cargo) => buscarGrade(ANO, TURNO, "AC", cargo, "uf")),
);
```
- Se as duas respostas falham: `return <ErroRelatorio detalhe={respostaFederal.detalhe} />`.
- Senão, `federal = respostaFederal.ok ? marcaDoCargo("deputadoFederal", respostaFederal.dados) : null` (o mesmo para estadual).
- Render (`flex flex-col gap-10`):
  - `ExplicacaoMarca frases={leituraMarca(federal, estadual)}`;
  - para cada cargo, um `<section aria-labelledby>` com `<h2 className="leitura-titulo text-xl">` ("Deputado federal" ou "Deputado estadual"), seguido de `ErroRelatorio` se a resposta falhou, ou de `GraficoMarca`, `TabelaMarca` e `TabelaMarcaUf` se a marca existe, ou do texto "Sem votos gravados para este cargo." se a marca é `null`;
  - por fim, se as duas marcas existem e `comparacaoCargos(...).pares.length > 0`, o `GraficoMarcaCargos`.

- [ ] **Step 1:** Implementar os cinco componentes.
- [ ] **Step 2:** Run (de `frontend/`): `pnpm exec tsc --noEmit && pnpm exec eslint src/components/relatorios/*marca*.tsx && node --experimental-strip-types src/lib/verificar-grafico-marca.ts`. Expected: só `ok`.

**If Task Fails:**
1. Erro de tipo em `Promise.all` com `map`: tipe o retorno como `Promise<Resultado<GradeRelatorio>>[]` ou chame `buscarGrade` duas vezes, de forma explícita.
2. Erro de lint `react/no-array-index-key`: use `barra.chave` ou `haltere.chave` como key.

---

### Task 6: Página e navegação

**Files:**
- Create: `frontend/src/app/relatorios/marca/page.tsx`
- Modify: `frontend/src/components/layout/app-sidebar.tsx` (`ITENS`, linhas 17–27)
- Modify: `frontend/src/components/layout/app-breadcrumb.tsx` (`TRILHAS`, linhas 20–33)
- Modify: `frontend/src/app/page.tsx` (`DESTINOS`, linhas 10–36)

- [ ] **Step 1:** Criar a página:

```tsx
import type { Metadata } from "next";
import { Suspense } from "react";

import { DadosMarca } from "@/components/relatorios/dados-marca";
import { EsqueletoDados } from "@/components/relatorios/esqueleto-relatorio";
import { FerramentasApresentacao } from "@/components/relatorios/ferramentas-apresentacao";

export const metadata: Metadata = {
  title: "Força da marca",
};

export const maxDuration = 600;

export default function MarcaPage() {
  return (
    <div className="leitura flex min-h-0 flex-1 flex-col gap-6 overflow-auto p-4 md:p-6">
      <h1 className="leitura-titulo text-3xl">Força da marca</h1>
      <p className="text-sm text-muted-foreground">
        Eleição geral de 2026, 1º turno. Deputado federal e deputado estadual.
      </p>
      <FerramentasApresentacao />
      <Suspense fallback={<EsqueletoDados />}>
        <DadosMarca />
      </Suspense>
    </div>
  );
}
```

- [ ] **Step 2:** Navegação (uma entrada em cada arquivo). "Força da marca" é a 5ª do bloco dos seis planos, depois de "Classe do governador": fica depois de Força partidária, Cadeiras, Capilaridade e Verticalização, se existirem, e antes de "Municipais 2024" e "Mapa" (alinhado em 2026-10-22):
  - `app-sidebar.tsx`: `{ href: "/relatorios/marca", rotulo: "Força da marca" },`
  - `app-breadcrumb.tsx`: `"/relatorios/marca": { pagina: "Força da marca", relatorios: true },`
  - `app/page.tsx`: `{ href: "/relatorios/marca", titulo: "Força da marca", descricao: "Quanto do voto para deputado foi só no número do partido." },`
- [ ] **Step 3:** Run: `pnpm exec tsc --noEmit && pnpm exec eslint src/app/relatorios/marca/page.tsx src/components/layout/app-sidebar.tsx src/components/layout/app-breadcrumb.tsx src/app/page.tsx`. Expected: nenhuma saída.

**If Task Fails:**
1. Next 16 reclama da assinatura da página: leia `frontend/node_modules/next/dist/docs/` (veja `frontend/AGENTS.md`). A página não recebe `searchParams`.
2. Conflito com outro plano nos três arquivos: mantenha as duas entradas, na ordem 1–6.

---

### Task 7: Conferência no navegador

**Prerequisites:** a API responde em `http://localhost:15000` (Verificação antes de começar) e `cd frontend && pnpm dev` está rodando em `http://localhost:14000`.

- [ ] **Step 1:** Abrir `http://localhost:14000/relatorios/marca` no chrome-devtools, numa aba própria (`isolatedContext: "marca"`), e anotar o tempo até o conteúdo aparecer (Review Focus: desempenho).
- [ ] **Step 2:** Conferir as frases com os dados gravados de 2026, que devem aparecer nesta ordem:
  - "No Brasil, 3,01% dos votos para deputado federal foram só no número do partido. Para deputado estadual, foram 6,45% (sem o DF, que elege deputados distritais)."
  - "Marca forte para deputado federal: REDE 18 (19,01%), CIDADANIA 23 (12,03%), PDT 12 (11,33%) e PT 13 (6,82%), cada um com pelo menos o dobro da média do cargo (3,01%)."
  - "Voto na pessoa para deputado federal: PODE 20, com 1,08% de voto de legenda, no máximo a metade da média do cargo (3,01%)."
  - "Marca forte para deputado estadual: REDE 18 (40,65%) e CIDADANIA 23 (14,35%), cada um com pelo menos o dobro da média do cargo (6,45%)."
  - "Voto na pessoa para deputado estadual: PV 43 (3,20%), PODE 20 (3,01%), DC 27 (2,96%), AVANTE 70 (2,62%) e AGIR 36 (1,77%), cada um com no máximo a metade da média do cargo (6,45%)."
  - "PDT 12 é o partido cuja marca mais muda entre os cargos: para deputado federal, tem 11,33% de voto de legenda (3,76× a média do cargo); para deputado estadual, 9,98% (1,55× a média do cargo)."
  - "Para deputado federal, a UF com mais voto de legenda é Piauí (3,93%) e a com menos é Amapá (2,55%)."
  - "Para deputado estadual, a UF com mais voto de legenda é Bahia (9,53%) e a com menos é Roraima (3,00%)."
  - Fora de federal: PCO 29, PSTU 16, MOBILIZA 33, UP 80, AGIR 36 e DEMOCRATA 35, nesta ordem. Fora de estadual: PCB 21, PCO 29, PSTU 16 e UP 80.

  Se algum número divergir, rode de novo os dois `curl` da verificação inicial. Se os totais mudaram, o relatório foi regravado: atualize só este passo.
- [ ] **Step 3:** Conferir a tabela de federal: 22 linhas de ranking, 6 de fora e o rodapé "Todos os partidos" com 114.107.982 votos, 3.438.422 de legenda e 3,01%. A tabela de estadual deve ter 25 de ranking, 4 de fora e o rodapé com 111.662.018 votos, 7.204.172 de legenda e 6,45%.
- [ ] **Step 3b:** Conferir as tabelas por UF:
  - a de federal tem 27 linhas (com DF) e 22 colunas de partido;
  - a de estadual tem 26 linhas (sem DF) e 25 colunas de partido;
  - a "Média da UF" de Piauí em federal é 3,93%, e a de Roraima em estadual é 3,00%;
  - toda célula "—" tem o motivo no texto acessível (inspecionar o `sr-only` no DevTools).
- [ ] **Step 4:** Tema claro e escuro (`ToggleTheme`), 375 px (`emulate` ou `resize_page`): desenho estreito, sem rolagem horizontal da página. Tooltip nas barras e nos halteres. Console sem erros nem avisos de hidratação.
- [ ] **Step 5:** Simular falha de um cargo: com a API parada (`docker compose stop api`), a página mostra um único `ErroRelatorio` "Não foi possível contactar a API.". Depois, `docker compose start api`. Não é preciso simular o 409 de um só cargo no banco: a regra D16 já está na lógica do `dados-marca.tsx`, que deve ser revisada na Task 9.
- [ ] **Step 6:** Sidebar e breadcrumb mostram "Força da marca", e o cartão da página inicial leva à página.
- [ ] **Step 7:** Salvar as capturas `marca-*.png` (largo claro, largo escuro, 375 px, tooltip) no scratchpad.

---

### Task 8 (opcional): Mapa de calor partido × UF

Faça esta task só se o humano confirmar (Q5). Ela é independente das Tasks 5 a 7.

**Files:**
- Modify: `frontend/src/lib/grafico-marca.ts`
- Modify: `frontend/src/lib/verificar-grafico-marca.ts`
- Create: `frontend/src/components/relatorios/mapa-calor-marca.tsx`
- Modify: `frontend/src/components/relatorios/dados-marca.tsx` (`MapaCalorMarca` antes da `TabelaMarcaUf` de cada cargo)

**Interfaces:**
```ts
export type MedidasCalor = { largura: number; esquerda: number; direita: number; topo: number; base: number; alturaLinha: number; fonte: number };
export const MEDIDAS_CALOR: MedidasCalor = { largura: 640, esquerda: 120, direita: 4, topo: 24, base: 4, alturaLinha: 20, fonte: 11 };
export type QuadroCalor = { chave: string; x: number; y: number; lado: number; alfa: number; estado: EstadoCelula; titulo: string; linhas: string };
// alfa = (legenda/votos) / maior parte entre as células "ok" do cargo; 0 fora de "ok"
// titulo = `${rotulo}, ${nomeUf}`; linhas = "ok": `${texto} de legenda\n${formatarInteiro(legenda)} de ${formatarInteiro(votos)} votos`;
// "poucos": `Menos de 5.000 votos na UF`; "sem-candidato": `Sem candidato na UF`; "sem-votos": `Sem votos na UF`
export type LayoutCalor = { medidas: MedidasCalor; largura: number; altura: number; lado: number;
  colunas: { uf: string; x: number }[]; linhas: { rotulo: string; y: number }[]; quadros: QuadroCalor[] };
export function layoutCalor(marca: MarcaCargo, medidas?: MedidasCalor): LayoutCalor | null; // null sem ranking ou sem UFs
export function resumoCalor(marca: MarcaCargo): string;
// `Voto de legenda por partido e UF, ${rotulo}. ${UF}: ${rotulo} ${texto}, ...; ...` (só células "ok")
```
O lado de cada quadro é `(largura − esquerda − direita) / ufs.length`, com x = `esquerda + j·lado`, y = `topo + i·alturaLinha` e altura = `topo + linhas·alturaLinha + base`.

- [ ] **Step 1: Testes:**
```ts
const calor = layoutCalor(federal) as LayoutCalor;
assert.equal(calor.quadros.length, 9);
assert.deepEqual(calor.colunas.map((coluna) => coluna.uf), ["AC", "BA", "DF"]);
const quadro = (partido: number, uf: string) => calor.quadros.find((item) => item.chave === `${partido}-${uf}`)!;
assert.equal(quadro(12, "BA").alfa, 1);
assert.ok(Math.abs(quadro(12, "AC").alfa - 0.5) < 1e-12);
assert.equal(quadro(12, "DF").estado, "sem-votos");
assert.equal(quadro(12, "DF").alfa, 0);
assert.equal(quadro(12, "DF").linhas, "Sem votos na UF");
assert.equal(quadro(13, "AC").linhas, "10,00% de legenda\n10.000 de 100.000 votos");
assert.equal(calor.lado, (MEDIDAS_CALOR.largura - MEDIDAS_CALOR.esquerda - MEDIDAS_CALOR.direita) / 3);
assert.equal((layoutCalor(estadual) as LayoutCalor).colunas.length, 2);
assert.equal(layoutCalor({ ...federal, ranking: [] }), null);
```
- [ ] **Step 2: Ver falhar** (`does not provide an export named 'layoutCalor'`). **Step 3: Implementar.** **Step 4:** `ok`, depois `tsc` e `eslint`.
- [ ] **Step 5: Componente.** `<figure className="folha-quieta">`, `<div className="overflow-x-auto"><svg className="w-full min-w-[560px]" role="img">`, quadros `<rect fill="var(--tinta-quente)" fillOpacity={alfa}>` para "ok" e `fill="var(--muted)"` nos outros. Siglas das UFs no topo e rótulos dos partidos à esquerda, com dica por quadro. Título: `Voto de legenda por UF, ${marca.rotulo}`. Legenda: "Quanto mais forte a cor, maior a parte de legenda do partido na UF. Cinza: sem votos, sem candidato ou menos de 5.000 votos na UF."
- [ ] **Step 6:** Navegador, como na Task 7, Step 4: no federal, 27 colunas e a coluna DF presente; no estadual, 26 colunas, sem DF.

---

### Task 9: Code Review final

1. **REQUIRED SUB-SKILL:** Use jarvis:codereview: dispatch all reviewers in parallel sobre todos os arquivos novos e modificados.
2. **Handle findings by severity:** see jarvis:codereview severity rules.
3. **Proceed only when:** zero Critical/High/Medium issues remain. Depois, `node --experimental-strip-types src/lib/verificar-grafico-marca.ts` (`ok`), `pnpm exec tsc --noEmit` e `pnpm exec eslint` (sem saída). Sem commit, a não ser que o usuário peça.

## Perguntas em aberto

- **Q1 Limiares:** 100.000 votos para o ranking, 5.000 por célula UF e os fatores 2× e 0,5× da média são escolhas deste plano (D5, D7, D8). Estão em constantes exportadas. Confirmar ou ajustar.
- **Q2 Federações:** agregar os partidos federados (por exemplo, PT 13 + PCdoB 65 + PV 43) numa linha só? Hoje cada número aparece sozinho. Agregar exige uma tabela de federações de 2026 no frontend, que ainda não existe. A lista oficial fica no plano 2 (`domain/federacoes.py`, exposta em `legendas` de `GET /relatorios/dados/cadeiras`), e é ela que se reusa se a resposta for sim. Não crie uma segunda lista (alinhado em 2026-10-22).
- **Q3 Placar (plano 1), respondida em 2026-10-22:** o placar calcula no backend, com a fórmula D3 sobre a soma das UFs, e mostra os dois cargos, como coluna opcional da fase D (Task 20 do plano 1). Os dois planos têm teste com 3,01% e 6,45%.
- **Q4 Página sem filtro:** confirmar a página fixa em 2026, turno 1, sem botão "Consultar" (D2).
- **Q5 Mapa de calor:** fazer a Task 8 agora ou deixar para depois? Os valores por UF e partido já aparecem na `TabelaMarcaUf` sem ela.
- **Q6 Visual:** confirmar barras com linha da média e halteres no lugar de barras empilhadas ou divergentes nominal × legenda (D13).


## Decisões do usuário (2026-10-22)

O usuário aceitou as recomendações da revisão de coerência. Estas decisões valem sobre qualquer pergunta em aberto neste plano.

- **Fase D do placar:** só os links para Capilaridade, Verticalização e Força da marca e a coluna de voto de legenda (Tasks 19 e 20). A Task 21 não entra.
- **Federações:** a lista das cinco federações (Brasil da Esperança: PT, PCdoB, PV; PSDB Cidadania; PSOL Rede; Renovação Solidária: PRD, Solidariedade; União Progressista: União, PP) fica no código (`domain/federacoes.py`). A Força da marca não agrega os federados.
- **Limiares das classes:** manter os calibrados nos planos e rever depois da primeira execução com dados reais.
- **Itens menores:** sem população do IBGE, limiar de presença na lista fixa, sem classe de viés regional, Força da marca com página fixa, sem mapa de calor e com o visual proposto.
