# Finalidade do relatório de presidente e governador

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Depois de Consultar, a página diz sozinha para que serve o relatório, o que cada classe significa e qual classe concentra os votos válidos de presidente.

**Architecture:** Um módulo puro, versionado, monta as frases a partir da composição já recebida. A página Next só as exibe. A classificação, as frações, as colunas e o filtro de UF não mudam.

**Tech Stack:** Next.js 16.4, React 19, TypeScript, Tailwind 4, as funções já existentes em `frontend/src/lib/fracao.ts`. Não há runner de teste no frontend. Node 22 executa o módulo com `--experimental-strip-types`.

**Spec:** Este arquivo é o spec. A regra de classe já está em `src/eleicoes/domain/presidente_governador.py` (`classify`, `CLASS_LABELS`) e não será alterada.

## Global Constraints

- Interface, rótulos e frases em português. Identificadores e a mensagem de commit em inglês.
- Não alterar `classify`, `party_share`, `formatarPercentualContagem`, o JSON da API nem `html_presidente_governador.py`.
- Não acrescentar sigla, nome de partido ou cor de partido. O partido continua sendo o número.
- Não recortar composição, estados, regiões ou país pela UF. A UF continua só escolhendo a lista de municípios. `ufDeConsulta("TODAS")` continua enviando `AC` à API.
- Não mudar as colunas de `TabelaLeitura`. Não mudar a ordenação.
- A cor de destaque continua `rgb(13, 111, 110)`. Quatro intensidades dessa cor, nesta ordem: consolidação 1, terreno de virada 0,72, em aberto 0,48, sem governador 0,28. Sem paleta nova.
- Texto e superfície seguem o tema (`text-foreground`, `text-muted-foreground`, `folha-quieta`). Sem controle novo de tema.
- Não chamar a API com `atualizar=true`. Não consultar deputado federal nem deputado estadual. Não reiniciar o download das urnas. Não derrubar o Compose.
- `.gitignore` ignora qualquer diretório `relatorios/` e `lib/`. Não editar o `.gitignore`. `frontend/src/components/relatorios/` e `frontend/src/lib/` não aparecem em `git diff`.
- O passo de commit fica escrito, mas só roda se o usuário pedir. Trailer: `--trailer "X-Jarvis-Ref: 0x1"`. Sem assinatura. Não incluir `.env`, `downloads/`, `logs/`, `relatorios/` nem `docs/dev-python-oop/current-cycle.json`.
- `cd frontend && pnpm exec tsc --noEmit` é a checagem de tipos. Na raiz, `pnpm exec tsc` falha com `ERR_PNPM_NO_PKG_MANIFEST`.
- Se a porta 14000 já responder, usar esse Next. Não encerrar o Chrome do usuário.

## Review Focus

- Composição com zero votos válidos não pode gerar percentual nem a palavra “NaN”. A frase do achado fica ausente; as quatro definições continuam.
- Empate na maior fatia usa a primeira classe desta ordem: `consolidacao`, `terreno_de_virada`, `em_aberto`, `sem_governador`.
- Classe desconhecida não quebra a página. Ela não vence o achado. O rótulo visível cai no texto cru da classe.
- UF `AC` e UF `Todas` mostram a mesma composição e a mesma frase do achado. Só a lista de municípios muda.
- A linha de Santa Rosa do Purus permanece 13 com 50,47%, 22 com 45,88% e margem 4,60%. O Relatório de poder não ganha estas frases.

---

### Task 1: Frases da finalidade

**Files:**
- Create: `frontend/src/app/relatorios/presidente-governador/finalidade.ts`
- Create: `frontend/src/app/relatorios/presidente-governador/verificar-finalidade.ts`
- Test: `node --experimental-strip-types frontend/src/app/relatorios/presidente-governador/verificar-finalidade.ts`

**Interfaces:**
- Consumes: `Composicao` e `FatiaClasse` de `frontend/src/lib/relatorios.ts`; `formatarPercentualContagem` de `frontend/src/lib/fracao.ts`.
- Produces:
  - `ORDEM_CLASSE: readonly ["consolidacao", "terreno_de_virada", "em_aberto", "sem_governador"]`
  - `DEFINICOES: Record<(typeof ORDEM_CLASSE)[number], string>`
  - `INTENSIDADE: Record<(typeof ORDEM_CLASSE)[number], number>`
  - `FRASE_FINALIDADE: string`
  - `FRASE_RECORTE: string`
  - `FRASE_MARGEM: string`
  - `definicaoDaClasse(classe: string): string`
  - `fraseDoAchado(composicao: Composicao): string | null`

- [ ] **Step 1: Write the failing check**

Criar `frontend/src/app/relatorios/presidente-governador/verificar-finalidade.ts` com o conteúdo abaixo. O import do módulo ainda não existe, então o Node falha.

```ts
import assert from "node:assert/strict";

import type { Composicao } from "../../lib/relatorios.ts";
import {
  DEFINICOES,
  FRASE_FINALIDADE,
  FRASE_MARGEM,
  FRASE_RECORTE,
  fraseDoAchado,
  INTENSIDADE,
  ORDEM_CLASSE,
} from "./finalidade.ts";

const cheia: Composicao = {
  votos_validos: 119299501,
  branco: 2300777,
  nulo: 3674209,
  classes: [
    { classe: "consolidacao", cidades: 1, votos_validos: 34682119 },
    { classe: "terreno_de_virada", cidades: 1, votos_validos: 1249978 },
    { classe: "em_aberto", cidades: 1, votos_validos: 83037291 },
    { classe: "sem_governador", cidades: 1, votos_validos: 330113 },
  ],
};

assert.equal(
  FRASE_FINALIDADE,
  "Este relatório mostra se o governador de cada lugar segue o líder da presidência, o segundo colocado, um terceiro partido, ou se não há governador.",
);
assert.equal(
  fraseDoAchado(cheia),
  "A maior parte dos votos válidos de presidente, 69,60%, está em municípios em aberto: o governador é de um partido que não lidera nem fica em segundo na presidência nesse lugar.",
);
assert.equal(fraseDoAchado(zerada()), null);
assert.match(fraseDoAchado(empate()) ?? "", /consolidação/i);
assert.equal(fraseDoAchado(desconhecida()), null);
assert.deepEqual(ORDEM_CLASSE.length, 4);
assert.deepEqual(
  ORDEM_CLASSE.map((classe) => INTENSIDADE[classe]),
  [1, 0.72, 0.48, 0.28],
);
assert.equal(FRASE_RECORTE.includes("lista de municípios"), true);
assert.equal(FRASE_MARGEM.includes("Brancos e nulos"), true);
assert.equal(Object.keys(DEFINICOES).length, 4);

function zerada(): Composicao {
  return {
    votos_validos: 0,
    branco: 0,
    nulo: 0,
    classes: ORDEM_CLASSE.map((classe) => ({
      classe,
      cidades: 0,
      votos_validos: 0,
    })),
  };
}

function empate(): Composicao {
  return {
    votos_validos: 20,
    branco: 0,
    nulo: 0,
    classes: [
      { classe: "em_aberto", cidades: 1, votos_validos: 10 },
      { classe: "consolidacao", cidades: 1, votos_validos: 10 },
      { classe: "terreno_de_virada", cidades: 0, votos_validos: 0 },
      { classe: "sem_governador", cidades: 0, votos_validos: 0 },
    ],
  };
}

function desconhecida(): Composicao {
  return {
    votos_validos: 10,
    branco: 0,
    nulo: 0,
    classes: [{ classe: "outra", cidades: 1, votos_validos: 10 }],
  };
}

console.log("finalidade ok");
```

- [ ] **Step 2: Run the check and confirm it fails**

Run from the repository root:

```bash
node --experimental-strip-types frontend/src/app/relatorios/presidente-governador/verificar-finalidade.ts
```

Expected: failure because `./finalidade.ts` does not exist.

- [ ] **Step 3: Write the module**

Criar `frontend/src/app/relatorios/presidente-governador/finalidade.ts`:

```ts
import { formatarPercentualContagem } from "../../lib/fracao.ts";
import type { Composicao, FatiaClasse } from "../../lib/relatorios.ts";

export const ORDEM_CLASSE = [
  "consolidacao",
  "terreno_de_virada",
  "em_aberto",
  "sem_governador",
] as const;

export type ClasseCruzada = (typeof ORDEM_CLASSE)[number];

export const DEFINICOES: Record<ClasseCruzada, string> = {
  consolidacao:
    "O governador é do mesmo partido que lidera a presidência nesse lugar.",
  terreno_de_virada:
    "O governador é do partido que ficou em segundo na presidência nesse lugar.",
  em_aberto:
    "O governador é de um partido que não lidera nem fica em segundo na presidência nesse lugar.",
  sem_governador:
    "Há líder na presidência e não há líder de governador nesse lugar.",
};

export const INTENSIDADE: Record<ClasseCruzada, number> = {
  consolidacao: 1,
  terreno_de_virada: 0.72,
  em_aberto: 0.48,
  sem_governador: 0.28,
};

export const FRASE_FINALIDADE =
  "Este relatório mostra se o governador de cada lugar segue o líder da presidência, o segundo colocado, um terceiro partido, ou se não há governador.";

export const FRASE_RECORTE =
  "A UF escolhe somente a lista de municípios. A composição, os estados, as regiões e o país reúnem todos os lugares apurados.";

export const FRASE_MARGEM =
  "A margem é o líder menos o segundo, sobre os votos válidos de presidente. Brancos e nulos ficam de fora do percentual, da margem e da classe.";

const FECHO: Record<ClasseCruzada, string> = {
  consolidacao: "municípios em consolidação",
  terreno_de_virada: "municípios em terreno de virada",
  em_aberto: "municípios em aberto",
  sem_governador: "municípios sem governador",
};

export function definicaoDaClasse(classe: string): string {
  if (eClasse(classe)) {
    return DEFINICOES[classe];
  }
  return classe;
}

export function fraseDoAchado(composicao: Composicao): string | null {
  if (composicao.votos_validos <= 0) {
    return null;
  }
  const vencedora = maiorFatia(composicao.classes);
  if (vencedora === null || !eClasse(vencedora.classe)) {
    return null;
  }
  const percentual = formatarPercentualContagem(
    vencedora.votos_validos,
    composicao.votos_validos,
  );
  return `A maior parte dos votos válidos de presidente, ${percentual}, está em ${FECHO[vencedora.classe]}: ${definicaoDaClasse(vencedora.classe)}`;
}

function maiorFatia(classes: readonly FatiaClasse[]): FatiaClasse | null {
  let escolhida: FatiaClasse | null = null;
  let posicao = ORDEM_CLASSE.length;
  for (const fatia of classes) {
    if (!eClasse(fatia.classe) || fatia.votos_validos <= 0) {
      continue;
    }
    const indice = ORDEM_CLASSE.indexOf(fatia.classe);
    if (
      escolhida === null ||
      fatia.votos_validos > escolhida.votos_validos ||
      (fatia.votos_validos === escolhida.votos_validos && indice < posicao)
    ) {
      escolhida = fatia;
      posicao = indice;
    }
  }
  return escolhida;
}

function eClasse(classe: string): classe is ClasseCruzada {
  return (ORDEM_CLASSE as readonly string[]).includes(classe);
}
```

Os imports usam caminho relativo e sufixo `.ts` para o Node. O Next também resolve esse sufixo no App Router desta versão. Se `pnpm exec tsc --noEmit` recusar o sufixo, trocar os dois imports para `../../lib/fracao` e `../../lib/relatorios` e manter o sufixo só no verificador, por meio de uma cópia mínima das assinaturas. Não duplicar a fórmula do percentual.

- [ ] **Step 4: Run the check and the type check**

```bash
node --experimental-strip-types frontend/src/app/relatorios/presidente-governador/verificar-finalidade.ts
cd frontend && pnpm exec tsc --noEmit
```

Expected: `finalidade ok` and `tsc` exit 0.

- [ ] **Step 5: Commit when the user asks**

```bash
git add frontend/src/app/relatorios/presidente-governador/finalidade.ts frontend/src/app/relatorios/presidente-governador/verificar-finalidade.ts
git commit -m "feat: state what the president and governor report shows" --trailer "X-Jarvis-Ref: 0x1"
```

### Task 2: Mostrar a finalidade na composição

**Files:**
- Modify: `frontend/src/components/relatorios/secao-composicao.tsx`
- Modify: `frontend/src/components/relatorios/dados-presidente-governador.tsx`
- Test: Chrome em `http://localhost:14000/relatorios/presidente-governador?ano=2026&turno=1&uf=AC&consultar=1`

**Interfaces:**
- Consumes: `FRASE_FINALIDADE`, `FRASE_MARGEM`, `FRASE_RECORTE`, `INTENSIDADE`, `definicaoDaClasse`, `fraseDoAchado` da Task 1. `rotuloClasse` continua sendo o nome curto do cartão.
- Produces: a primeira tela do relatório cruzado, sem mudança de dado.

- [ ] **Step 1: Render the sentences and the weighted bar**

Em `secao-composicao.tsx`, importar o módulo pelo alias `@/app/relatorios/presidente-governador/finalidade`. Acima da barra, nesta ordem:

1. Um parágrafo com `FRASE_FINALIDADE`.
2. Se `fraseDoAchado(composicao)` não for `null`, um parágrafo com essa frase.
3. Um parágrafo menor, `text-sm text-muted-foreground`, com `FRASE_MARGEM`.

Na barra, cada fatia com `votos_validos > 0` usa `backgroundColor: rgb(13, 111, 110)` e `opacity` igual a `INTENSIDADE[fatia.classe]` quando a classe for conhecida. Classe desconhecida fica na opacidade `1`. Fatia com zero votos continua sem cor, como hoje. O `flexGrow` continua sendo `fatia.votos_validos`.

Debaixo do nome de cada cartão (`rotuloClasse`), antes do percentual, colocar a definição em `text-sm text-muted-foreground`: `definicaoDaClasse(fatia.classe)`. O percentual, o número de municípios e os votos válidos permanecem. Brancos e nulos permanecem na última linha.

Em `dados-presidente-governador.tsx`, logo antes de `{secoesMunicipio(...)}`, um parágrafo `text-sm text-muted-foreground` com `FRASE_RECORTE`. Não colocar essa frase em `filtros-relatorio.tsx`.

- [ ] **Step 2: Typecheck**

```bash
cd frontend && pnpm exec tsc --noEmit
```

Expected: exit 0.

- [ ] **Step 3: Verify in Chrome**

Subir `cd frontend && pnpm dev` só se a porta 14000 não responder. Abrir:

`http://localhost:14000/relatorios/presidente-governador?ano=2026&turno=1&uf=AC&consultar=1`

Confirmar, no tema escuro e no claro:

- A primeira frase é a da finalidade, visível sem rolar a tabela.
- O achado contém `69,60%` e `em aberto`.
- Os quatro cartões têm definição, percentual, municípios e votos válidos. Em aberto mostra `69,60%` e `83.037.291`.
- A barra tem quatro pesos do mesmo verde. O trecho de em aberto é o mais longo e mais claro que o de consolidação.
- A frase da UF aparece uma vez, acima dos municípios.
- Acre aparece na lista municipal. A composição não muda ao trocar a UF para `Todas`; a lista passa a ter as demais UF.
- Santa Rosa do Purus permanece com líder 13 a `50,47%`, segundo 22 a `45,88%` e margem `4,60%`.
- `http://localhost:14000/relatorios/poder` não mostra `FRASE_FINALIDADE`. Não clicar em Consultar nessa página.

- [ ] **Step 4: Commit when the user asks**

Os componentes estão ignorados pelo Git. Não usar `git add -f` e não alterar `.gitignore`. Commit só se algum arquivo fora desses diretórios tiver mudado além da Task 1. Se a Task 2 só mexeu em `frontend/src/components/relatorios/`, registrar no resumo que a apresentação ficou no disco e fora do commit.

## Out of scope

- Filtrar a tabela ao clicar numa classe.
- Sigla ou nome de partido.
- Recalcular a composição pela UF escolhida.
- Alinhar colunas, margem ou brancos/nulos com o HTML antigo.
- Mapa, relatório de poder, API e varredura de boletim.

## Self-review

- A finalidade, as quatro definições, o achado calculado, o aviso da UF e a margem têm tarefa.
- Zero votos, empate, classe desconhecida, UF e a linha de Santa Rosa estão no Review Focus e no verificador ou no Chrome.
- Não há tarefa de filtro por clique, sigla ou mudança de conta.
- Os nomes exportados são os mesmos na Task 1 e na Task 2.
