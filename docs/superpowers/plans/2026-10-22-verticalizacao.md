# Verticalização: a força do partido se sustenta entre cargos?

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Revise entre os blocos com jarvis:codereview.

**Goal:** Um relatório novo, `/relatorios/verticalizacao`, responde se a força de cada partido se mantém entre presidente, governador, senador, deputado federal e deputado estadual. Ele tem quatro partes. A primeira é uma matriz partido × cargo com a fatia de cada partido no Brasil ou numa UF. A segunda mede a coerência municipal: dentro de cada UF, onde o partido vai melhor para deputado ele também vai melhor na majoritária? A terceira classifica cada par majoritária × proporcional como "puxador", "base", "alinhado" ou "sem candidato", com regras e limiares explícitos e frases geradas. A quarta é uma dispersão municipal para um partido e um par de cargos escolhidos.

**Architecture:** O backend lê só as linhas gravadas em `analise.relatorio_poder_linha` (níveis `municipio` e `uf`, os 5 cargos, só votos > 0), com um único SELECT novo num adaptador próprio. Um domínio puro em quatro módulos `domain/verticalizacao*.py` monta a base em memória, calcula as fatias, a presença por UF, as comparações e a correlação de Pearson ponderada dentro da UF. Um job com `lru_cache`, igual ao `ClassJob`, guarda a base por (ano, turno) e o relatório por (ano, turno, uf). A rota nova `GET /relatorios/dados/verticalizacao` fica num módulo de router próprio e devolve 409 quando falta um cargo. No frontend, um módulo puro (`lib/grafico-verticalizacao.ts`) calcula as faixas de cor, o layout das duas matrizes e da dispersão e as frases. Componentes SVG de servidor desenham com variante estreita e `DicaGrafico`. A página segue o padrão de `classe-governador`.

**Tech Stack:** Python 3.14, FastAPI, Pydantic v2, SQLAlchemy 2 (sync, `run_sync` não é usado), pytest, ruff, mypy strict. Next.js 16.4, React 19.3, TypeScript, Tailwind 4, shadcn/ui. Sem biblioteca de gráficos. Os scripts de verificação rodam com `node --experimental-strip-types`.

**Spec:** Este arquivo. Contrato JSON na seção "Contrato".

---

## Fatos do dado (consultas só de leitura, 2026, 1º turno, feitas em 2026-10-22)

| Fato | Consequência |
|---|---|
| Os 5 cargos estão gravados em `analise.relatorio_poder` (presidente 08/10, governador e senador 14/10, deputados 22/10). | O relatório pode rodar hoje. Se faltar um cargo, a rota devolve 409. |
| A grade é densa: cada município tem uma linha para cada partido das colunas do cargo, inclusive com 0 voto. Governador: 150.417 linhas municipais, só 37.498 com votos. | Uma fatia 0 não diz se o partido concorreu. A presença é medida na UF (D3). Filtrar `votos > 0` no SQL não perde nada: o zero volta como ausência na chave. |
| Linhas com votos > 0: cerca de 375 mil municipais e 2 mil de UF. | Uma carga de alguns segundos, uma vez por (ano, turno), guardada em `lru_cache`. |
| O nome municipal termina em ` (UF)`, como em `SANTA ROSA DO PURUS (AC)`, inclusive `(ZZ)` para o exterior. Nenhum nome municipal fica sem sufixo. | A UF do município sai do sufixo (D4). |
| `ZZ` (exterior, 117 "municípios") só existe para presidente. | O exterior sai de todas as comparações e da coluna nacional (D5). |
| O DF tem 1 município. | O DF não tem variação dentro da UF e não entra na correlação. Entra na matriz e nas comparações. |
| O DF **não tem deputado estadual gravado**: são 754 linhas de UF ÷ 29 partidos = 26 UF, e o município do DF só tem presidente, governador, senador e deputado federal. Os distritais não estão no relatório de poder. | No DF, a coluna Dep. estadual é "sem eleição gravada" e não "não concorreu" (D6). O DF sai do par Governador ↔ Dep. estadual e dos pares de coerência com Dep. estadual, sem virar "sem candidato". Há uma nota sobre isso. |
| O comparecimento de um município é igual entre os cargos (5.571 pares distintos (código, comparecimento) para 5.571 códigos). | O comparecimento é o peso comum da correlação (D7). |
| Senador: votos válidos ÷ comparecimento = 1,66 no país. Governador: 0,90. Em 2026 cada eleitor vota em 2 senadores. | A fatia de senador divide pelos votos dados. Um candidato raramente passa de 50%. A regra puxador/base compara fatias que somam 100% entre os partidos com candidato, então não precisa de correção (D9). |
| `pais` e `regiao` existem gravados, mas a soma das UF basta. | O relatório lê só `municipio` e `uf`. |

## Decisões

| # | Pergunta | Decisão |
|---|---|---|
| D1 | Fonte | Só `analise.relatorio_poder_linha`, `nivel IN ('municipio','uf')`, `cargo IN` (os 5), `votos_nominais + votos_legenda > 0`. Um SELECT, num adaptador novo (`adapters/postgres_verticalizacao.py`). Não usa `RelatorioPoderStore.load` cinco vezes, porque isso criaria cerca de 700 mil `StoredCell` validados e montaria grades que o relatório não usa. Nenhuma tabela nova e nenhuma migração. |
| D2 | Votos válidos | Nominais + legenda, como em `grafico-poder` (P2). O total válido de um lugar e cargo é a soma dos votos de todos os partidos. Brancos e nulos não entram. |
| D3 | Presença ("concorreu") | Um partido concorreu a um cargo numa UF quando a linha `nivel='uf'` desse (cargo, UF, partido) tem votos > 0. Onde não concorreu, a fatia não vale zero: aquela UF sai das contas do cargo para esse partido. Um candidato com 0 voto na UF inteira conta como ausente, e isso fica documentado como limite aceito. |
| D4 | UF do município | Vem do sufixo ` (XX)` do nome, validado contra `UF_CODES`. É a mesma regra de `linhasVisiveis` no frontend. Um nome sem sufixo válido vai para `sem_uf` (contado e exibido, como o `without_uf` da classe do governador). Não usa `analise.relatorio_presidente_governador_linha`, para não depender de outro relatório. |
| D5 | Exterior | `ZZ` sai de tudo: das linhas de UF, dos municípios e da coluna nacional de presidente. Nota: "O exterior só vota para presidente e fica fora de todas as comparações". Por isso a fatia nacional de presidente pode diferir em centésimos da tela Poder e do placar (plano 1, F5), que usam a linha `pais` com o exterior. A diferença é aceita (alinhado em 2026-10-22). |
| D6 | Matriz partido × cargo | Cada célula mostra a fatia **onde concorreu** (votos ÷ válidos das UF onde o partido teve candidato no cargo) e "em N de M UF". A fatia sobre todas as UF (`fatia`) vai no tooltip e na tabela. Há dois vazios distintos. Com `ufs_concorreu = 0` e `ufs_total > 0` ("não concorreu"), a célula fica hachurada com "—", nunca com o tom mais claro da escala. Com `ufs_total = 0` ("sem eleição gravada no recorte", como Dep. estadual com `uf=DF`), a célula fica sem fundo, com borda tracejada e o texto "n/a". Cada caso tem sua amostra na legenda. Para uma UF escolhida, as duas fatias coincidem. |
| D7 | Coerência municipal | É a **correlação de Pearson ponderada pelo comparecimento, calculada dentro de cada UF**. As fatias são centradas na média ponderada da UF, e os somatórios das UF são juntados num só r. Entram só os municípios das UF onde o partido concorreu nos dois cargos e que têm votos válidos nos dois. Uma UF com menos de 2 municípios não entra (é o caso do DF). Com menos de `MINIMO_MUNICIPIOS = 10` municípios, ou variância nula, `r = null`, exibido como "—" e nunca como 0. Justificativa: (a) o r agregado no país mede sobretudo a diferença entre estados (candidatos estaduais diferentes, alianças). A memória do projeto registra que a mistura entre UFs já inflou um resultado ("Governor class: no out-of-state skill"). (b) O peso pelo comparecimento faz o r refletir o eleitorado e não a contagem de municípios. Sem peso, 4 mil cidades pequenas e ruidosas dominariam. (c) O Spearman sem peso tem o mesmo defeito, e um Spearman ponderado não é padrão nem fácil de explicar. O Pearson não muda com a escala, então o duplo voto de senador não o afeta. |
| D8 | Pares de coerência | São 7, nesta ordem: (Dep. federal × Presidente), (Dep. estadual × Presidente), (Dep. federal × Governador), (Dep. estadual × Governador), (Dep. federal × Senador), (Dep. estadual × Senador) e (Dep. federal × Dep. estadual). O último é a **referência** de quanto vale um r "alto" entre dois cargos da mesma estrutura. O eixo x é sempre o primeiro cargo do par. |
| D9 | Esperado pela proporcional | Numa UF u, para a majoritária M e a proporcional P: `esperada(p,u) = votos_P(p,u) ÷ Σ votos_P(q,u)`, com q percorrendo os partidos que concorreram a M em u. É a fatia que o partido teria em M se os votos seguissem a força proporcional dos partidos que lançaram candidato. As duas fatias somam 100% entre esses partidos, o que neutraliza a concentração natural da majoritária, o número de candidatos e o duplo voto de senador. Se nenhum desses partidos tem voto em P, a esperada vale 0. |
| D10 | Pares canônicos para puxador/base | Governador ↔ Dep. estadual, Senador ↔ Dep. federal e Presidente ↔ Dep. federal. |
| D11 | Regra de classe | `RAZAO = 2` e `DIFERENCA = 10 pp`. **Puxador** quando `majoritária ≥ 2 × esperada` **e** `majoritária − esperada ≥ 10 pp`. **Base** quando `esperada ≥ 2 × majoritária` **e** `esperada − majoritária ≥ 10 pp`. **Alinhado** nos demais casos. As duas condições juntas impedem que um partido pequeno troque de classe por centésimos (3% contra 1% é razão 3, mas só 2 pp). A classe é calculada por UF e também na soma das UF onde o partido concorreu: a majoritária é Σvotos ÷ Σválidos, e a esperada é a média das esperadas da UF ponderada pelos válidos de M. |
| D12 | Sem candidato | O partido que não concorreu a M numa UF onde concorreu a P recebe a classe **sem candidato** nessa UF, com a fatia proporcional dele ali. Ela fica separada de "base", porque a ausência quase sempre é aliança e não fraqueza. Na soma, a classe vale `sem_candidato` só se o partido não concorreu a M em nenhuma UF do recorte. As frases citam só as UF com fatia proporcional ≥ `BASE_RELEVANTE = 5%`, com redação neutra ("pode ter apoiado um aliado"). |
| D13 | Indicador-resumo (para o Placar, plano 1) | Por partido: `perfil` e `coerencia_mediana`. O perfil vem do conjunto C das classes somadas dos 3 pares que são puxador, base ou alinhado. C vazio dá `sem_comparacao`. C com puxador e base dá `misto`. C com puxador dá `puxador`, e C com base dá `base`. Nos demais casos, `alinhado`. `coerencia_mediana` é a mediana dos r não nulos dos 6 pares cruzados (D8 sem a referência), ou `null`. **Consumo opcional (alinhado em 2026-10-22):** o placar não depende deste plano nas fases A, B e C. Na fase D do plano 1, o padrão é só um link do detalhe do partido para esta página (Task 19 de lá, `?uf=TODAS&partido=N&consultar=1`). As colunas `perfil` e `coerencia_mediana`, lidas do recorte Brasil por `get_vertical_job()`, só entram se o usuário pedir (Task 21 de lá). Não é preciso rota leve. |
| D14 | Ordem dos partidos | Votos em Dep. federal no recorte (decrescente), depois Dep. estadual, depois a soma dos 5 cargos, depois o número do partido. Entram todos os partidos com voto em algum cargo do recorte. |
| D15 | Dispersão | Parâmetros opcionais `partido`, `cargo_x` (padrão `deputadoFederal`) e `cargo_y` (padrão `governador`). Sem `partido`, vale o primeiro da ordem D14. Os pontos são os municípios da regra D7, inclusive de UF com 1 município, com x e y em "12,34%". Só a dispersão pedida vai no JSON. Mandar todas daria cerca de 5.570 × 30 × 5 valores. |
| D16 | Recorte por UF | `uf` é opcional. Ausente, vazio ou `TODAS` significa Brasil, e o r é intra-UF juntado. Com uma UF, tudo se restringe a ela e o r é o r dessa UF. `ZZ`, ou uma UF sem linhas, dá 422 "UF inválida.". |
| D17 | Formatação | Fatias com `format_percent` ("42,19%"). r e razão com `format_decimal` ("0,6213", "2,4000"). No frontend, o r aparece com 2 casas ("0,62") e a razão com 1 casa ("2,4 vezes"). |
| D18 | Cores | A matriz de fatias usa uma escala sequencial teal de 5 faixas, derivada de `--tinta-quente`. A matriz de r usa uma escala divergente vermelho ↔ azul com cinza neutro no meio (r negativo em vermelho, positivo em azul). Os valores foram validados com `validate_palette.js --ordinal` em claro (`#ffffff`) e escuro (`#171717`), e o contraste da tinta de cada célula foi conferido com `contrast()` (≥ 4,5:1). A ausência usa hachura em 45°. As cores ficam num CSS próprio da página, com `.dark`. |
| D19 | Frases | São geradas no frontend (`frasesVerticalizacao`), como em `frasesClasse`, a partir dos dados estruturados, e testadas com o texto exato. O backend devolve as classes, os números e os limiares. |
| D20 | Arquivos compartilhados | Os 6 planos correm em paralelo. Todo código deste plano vai para arquivos novos com "verticalizacao" no nome. Nos arquivos compartilhados entram só anexos de uma linha ou de um bloco curto (lista em Global Constraints). |

## Contrato

`GET /relatorios/dados/verticalizacao?ano=2026&turno=1[&uf=SP][&partido=13][&cargo_x=deputadoFederal][&cargo_y=governador]`

- 200 → `VerticalJson`.
- 409 → `{"detail": "O relatório de poder de senador ainda não foi gravado. Gere com: uv run python scripts/relatorio_poder.py --cargo senador --sem-navegador"}`. O texto é o de `MissingPowerReportError`, com o primeiro cargo ausente na ordem presidente, governador, senador, deputadoFederal, deputadoEstadual.
- 422 → "Ano inválido.", "Turno inválido.", "UF inválida.", "Cargo inválido." (cargo de dispersão fora dos 5 ou x = y), "Número inválido." (partido fora de 0..99) ou "Parâmetros inválidos." (tipo errado).

```jsonc
{
  "ano": 2026, "turno": 1,
  "uf": null,                       // ou "SP"
  "municipios": 5570,               // municípios com UF no recorte (sem exterior)
  "sem_uf": 0,
  "cargos": ["presidente","governador","senador","deputadoFederal","deputadoEstadual"],
  "limiares": { "razao": "2", "diferenca": "10,00%", "base_relevante": "5,00%", "minimo_municipios": 10 },
  "partidos": [{
    "partido": 22,
    "perfil": "puxador",            // puxador | base | alinhado | misto | sem_comparacao
    "coerencia_mediana": "0,4120",  // ou null
    "cargos": [{                    // 5, na ordem de "cargos"
      "cargo": "governador", "votos": 123, "validos": 456, "validos_onde": 300,
      "fatia": "26,97%", "fatia_onde": "41,00%",   // null quando não há base
      "ufs_concorreu": 9, "ufs_total": 27
    }],
    "coerencia": [{                 // 7, na ordem D8
      "cargo_x": "deputadoFederal", "cargo_y": "governador", "r": "0,6213", "municipios": 1830
    }],
    "comparacoes": [{               // 3, na ordem D10
      "majoritario": "governador", "proporcional": "deputadoEstadual",
      "majoritaria": "41,00%", "esperada": "15,20%", "razao": "2,6974",
      "classe": "puxador",          // puxador | base | alinhado | sem_candidato | null
      "por_uf": [{ "uf": "SP", "majoritaria": "52,00%", "esperada": "18,00%", "classe": "puxador" }],
      "sem_candidato": [{ "uf": "BA", "proporcional": "7,10%" }]
    }]
  }],
  "dispersao": {
    "partido": 22, "cargo_x": "deputadoFederal", "cargo_y": "governador",
    "coerencia": { "cargo_x": "deputadoFederal", "cargo_y": "governador", "r": "0,6213", "municipios": 1830 },
    "pontos": [{ "codigo": "1392", "nome": "RIO BRANCO (AC)", "uf": "AC", "comparecimento": 210000, "x": "12,30%", "y": "40,10%" }]
  },
  "notas": ["…"]
}
```

`classe: null` aparece quando o partido não concorreu nem à majoritária nem à proporcional do par no recorte. Também aparece quando ele concorreu à majoritária no recorte, mas só em UF sem a proporcional gravada (como governador só no DF): não há comparação e isso não é "sem candidato" (D12, ajuste da revisão da Task 5). Uma UF sem a majoritária gravada também não gera "sem candidato".

## Global Constraints

- Arquivos novos (backend): `src/eleicoes/domain/verticalizacao.py`, `verticalizacao_regras.py`, `verticalizacao_coerencia.py`, `verticalizacao_relatorio.py`, `src/eleicoes/ports/verticalizacao.py`, `src/eleicoes/adapters/postgres_verticalizacao.py`, `src/eleicoes/use_cases/verticalizacao.py`, `src/eleicoes/adapters/http/verticalizacao.py`, `schemas_verticalizacao.py`, `dependencies_verticalizacao.py` e os testes `tests/domain/test_verticalizacao*.py`, `tests/adapters/test_postgres_verticalizacao.py`, `tests/adapters/test_http_verticalizacao.py`.
- Arquivos novos (frontend): `frontend/src/lib/verticalizacao.ts`, `grafico-verticalizacao.ts`, `verificar-grafico-verticalizacao.ts`, `frontend/src/components/relatorios/*-verticalizacao.tsx`, `frontend/src/app/relatorios/verticalizacao/page.tsx`, `verticalizacao.css`.
- Os únicos arquivos compartilhados que mudam, todos com anexos curtos:
  1. `src/eleicoes/composition/api.py`: 1 import e 1 `include_router`.
  2. `src/eleicoes/adapters/http/dependencies.py`: 1 import e 1 linha em `clear_report_caches`.
  3. `frontend/src/lib/buscar-relatorios.ts`: 1 import e 1 função `buscarVerticalizacao` no fim do bloco de funções exportadas.
  4. `frontend/src/components/layout/app-sidebar.tsx`: 1 item em `ITENS`.
  5. `frontend/src/components/layout/app-breadcrumb.tsx`: 1 entrada em `TRILHAS` (alinhado em 2026-10-22).
  6. `frontend/src/app/page.tsx`: 1 entrada em `DESTINOS` (alinhado em 2026-10-22).
- **Integração (alinhado em 2026-10-22):** a ordem dos planos é 2 → 6 → 1 (fases A, B e C), e este plano entra em qualquer momento, só por adição. A tabela de quem toca cada arquivo compartilhado está no plano 1, na seção "Integração entre os planos de 2026-10-22". Este é o único plano que mexe em `composition/api.py`.
- Proibido: tabela ou migração nova (0004/0005 são de outros planos), ler `raw.*` ou boletins, mudar `domain/presidente_governador.py`, `classe_governador.py`, `stored_grade.py`, `relatorios.ts`, `globals.css` ou `dica-grafico.tsx`.
- Sem dependência nova. Sem commit até a revisão final. **Subagentes não rodam `git stash`, `checkout`, `reset` nem outro git que muda estado**: os planos correm em paralelo na mesma árvore.
- Mensagens internas (exceções, docstrings) em inglês. Texto ao usuário (notas, frases, rótulos) em português.
- Backend verde: `uv run pytest -q`, `uv run ruff check src tests`, `uv run ruff format --check src tests`, `uv run mypy src tests`.
- Frontend verde (em `frontend/`): `node --experimental-strip-types src/lib/verificar-grafico-verticalizacao.ts` imprime `ok`, e `pnpm exec tsc --noEmit` e `pnpm exec eslint` passam nos arquivos tocados.

## Review Focus

- A presença (D3) é usada em **todas** as contas de cargo: fatia onde concorreu, esperada, coerência e dispersão. Nenhuma ausência vira zero.
- O r é intra-UF (D7): a média ponderada sai por UF antes de somar, e as UF com 1 município ficam fora de n.
- Nenhum `None` vira "0,00%" ou 0 na UI: aparece "—" com hachura.
- Os limiares têm testes de borda (exatamente 2× e exatamente 10 pp contam).
- O cache é limpo em `clear_report_caches` e não guarda erros (o `lru_cache` não guarda exceção).
- O exterior sai da coluna nacional de presidente.
- Variante estreita e tema escuro conferidos no navegador.

---

### Task 1: Base de domínio (linhas, UF, presença, fatias)

**Files:**
- Create: `src/eleicoes/domain/verticalizacao.py`
- Test: `tests/domain/test_verticalizacao.py`

**Interfaces:**
- Consumes: `ElectionYear`, `Turno`, `UF_CODES` (`domain/values.py`), e `InconsistentCellError`, `InvalidUfError`, `MissingPowerReportError` (`domain/errors.py`).
- Produces: `CARGOS`, `MAJORITARIOS`, `PROPORCIONAIS`, as constantes de cargo, `EXTERIOR`, `VerticalLine`, `MunicipioVertical`, `VerticalBase`, `CargoShare`, `municipal_uf`, `vertical_base` e `cargo_share`.

- [x] **Step 1: Escrever os testes que falham**

```python
"""Vertical base: stored lines become per-UF and per-city votes. No ballot is read."""

from fractions import Fraction

import pytest

from eleicoes.domain.errors import InvalidUfError, MissingPowerReportError
from eleicoes.domain.verticalizacao import (
    CARGOS,
    GOVERNADOR,
    VerticalLine,
    cargo_share,
    municipal_uf,
    vertical_base,
)


def uf_lines(cargo: str, uf: str, votos: dict[int, int]) -> tuple[VerticalLine, ...]:
    return tuple(VerticalLine(cargo, "uf", uf, uf, 1000, p, v) for p, v in votos.items())


def city_lines(
    cargo: str, codigo: str, nome: str, comparecimento: int, votos: dict[int, int]
) -> tuple[VerticalLine, ...]:
    return tuple(
        VerticalLine(cargo, "municipio", codigo, nome, comparecimento, p, v)
        for p, v in votos.items()
    )


def every_cargo(uf: str = "SP", skip: tuple[str, ...] = ()) -> tuple[VerticalLine, ...]:
    return tuple(
        line for cargo in CARGOS if cargo not in skip for line in uf_lines(cargo, uf, {13: 1})
    )


def test_municipal_uf_reads_the_suffix() -> None:
    assert municipal_uf("RIO BRANCO (AC)") == "AC"
    assert municipal_uf("LISBOA (ZZ)") == "ZZ"
    assert municipal_uf("SEM UF") is None
    assert municipal_uf("ERRADO (XX)") is None


def test_missing_cargo_is_the_power_report_error_in_cargo_order() -> None:
    lines = tuple(line for line in every_cargo() if line.cargo not in {"senador", "deputadoEstadual"})
    with pytest.raises(MissingPowerReportError) as caught:
        vertical_base(2026, 1, lines)
    assert caught.value.cargo == "senador"


def test_zero_votes_exterior_and_orphans_are_dropped() -> None:
    lines = (
        *every_cargo(),
        *uf_lines("presidente", "ZZ", {13: 50}),
        *uf_lines(GOVERNADOR, "SP", {22: 0}),
        *city_lines("presidente", "1", "LISBOA (ZZ)", 60, {13: 50}),
        *city_lines("presidente", "2", "SEM UF", 10, {13: 5}),
        *city_lines("presidente", "3", "CAMPINAS (SP)", 100, {13: 40, 22: 0}),
    )
    base = vertical_base(2026, 1, lines)
    assert set(base.estados) == {"SP"}
    assert base.concorreu("SP", GOVERNADOR, 22) is False
    assert base.sem_uf == 1
    [campinas] = base.municipios["SP"]
    assert campinas.votos["presidente"] == {13: 40}
    assert campinas.validos["presidente"] == 40


def test_cargo_share_ignores_states_where_the_party_did_not_run() -> None:
    lines = (
        *every_cargo("SP"),
        *every_cargo("MG"),
        *uf_lines(GOVERNADOR, "SP", {22: 30}),
        *uf_lines(GOVERNADOR, "MG", {15: 99}),
    )
    base = vertical_base(2026, 1, lines)
    share = cargo_share(base, base.scope(None), GOVERNADOR, 22)
    assert share.fatia == Fraction(30, 1 + 30 + 1 + 99)
    assert share.fatia_onde == Fraction(30, 31)
    assert (share.ufs_concorreu, share.ufs_total) == (1, 2)
    absent = cargo_share(base, base.scope(None), GOVERNADOR, 45)
    assert absent.fatia == Fraction(0) and absent.fatia_onde is None


def test_scope_rejects_exterior_and_unknown_states() -> None:
    base = vertical_base(2026, 1, every_cargo("SP"))
    assert base.scope("sp") == ("SP",)
    for uf in ("ZZ", "MG"):
        with pytest.raises(InvalidUfError):
            base.scope(uf)
```

- [x] **Step 2: Rodar e ver falhar**

Run: `uv run pytest tests/domain/test_verticalizacao.py -q`
Expected: `ModuleNotFoundError: No module named 'eleicoes.domain.verticalizacao'`.

- [x] **Step 3: Implementar**

```python
"""Party strength across offices, read from the stored power cells. No ballot is read."""

import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Final

from eleicoes.domain.errors import InconsistentCellError, InvalidUfError, MissingPowerReportError
from eleicoes.domain.values import UF_CODES, ElectionYear, Turno

PRESIDENTE: Final = "presidente"
GOVERNADOR: Final = "governador"
SENADOR: Final = "senador"
DEPUTADO_FEDERAL: Final = "deputadoFederal"
DEPUTADO_ESTADUAL: Final = "deputadoEstadual"
CARGOS: Final[tuple[str, ...]] = (
    PRESIDENTE,
    GOVERNADOR,
    SENADOR,
    DEPUTADO_FEDERAL,
    DEPUTADO_ESTADUAL,
)
MAJORITARIOS: Final[tuple[str, ...]] = (PRESIDENTE, GOVERNADOR, SENADOR)
PROPORCIONAIS: Final[tuple[str, ...]] = (DEPUTADO_FEDERAL, DEPUTADO_ESTADUAL)
EXTERIOR: Final = "ZZ"
_MUNICIPIO: Final = "municipio"
_UF: Final = "uf"
_MAX_PARTIDO: Final = 99
_SUFIXO: Final = re.compile(r"\(([A-Z]{2})\)\s*$")
_STATES: Final = frozenset(UF_CODES) - {EXTERIOR}

Votes = Mapping[int, int]


@dataclass(frozen=True, slots=True)
class VerticalLine:
    cargo: str
    nivel: str
    codigo: str
    nome: str
    comparecimento: int
    partido: int
    votos: int

    def __post_init__(self) -> None:
        if self.cargo not in CARGOS or self.nivel not in (_MUNICIPIO, _UF):
            raise InconsistentCellError()
        object.__setattr__(self, "codigo", _text(self.codigo))
        object.__setattr__(self, "nome", _text(self.nome))
        _count(self.comparecimento)
        _count(self.votos)
        _count(self.partido)
        if self.partido > _MAX_PARTIDO:
            raise InconsistentCellError()


@dataclass(frozen=True, slots=True, eq=False)
class MunicipioVertical:
    codigo: str
    nome: str
    uf: str
    comparecimento: int
    votos: Mapping[str, Votes]
    validos: Mapping[str, int]


@dataclass(frozen=True, slots=True, eq=False)
class VerticalBase:
    ano: int
    turno: int
    estados: Mapping[str, Mapping[str, Votes]]
    municipios: Mapping[str, tuple[MunicipioVertical, ...]]
    sem_uf: int

    def scope(self, uf: str | None) -> tuple[str, ...]:
        if uf is None:
            return tuple(sorted(self.estados))
        code = uf.strip().upper()
        if code not in self.estados:
            raise InvalidUfError(uf)
        return (code,)

    def votos_uf(self, uf: str, cargo: str) -> Votes:
        return self.estados.get(uf, {}).get(cargo, {})

    def validos_uf(self, uf: str, cargo: str) -> int:
        return sum(self.votos_uf(uf, cargo).values())

    def concorreu(self, uf: str, cargo: str, partido: int) -> bool:
        return self.votos_uf(uf, cargo).get(partido, 0) > 0


@dataclass(frozen=True, slots=True)
class CargoShare:
    cargo: str
    votos: int
    validos: int
    validos_onde: int
    ufs_concorreu: int
    ufs_total: int

    @property
    def fatia(self) -> Fraction | None:
        if self.validos == 0:
            return None
        return Fraction(self.votos, self.validos)

    @property
    def fatia_onde(self) -> Fraction | None:
        if self.ufs_concorreu == 0 or self.validos_onde == 0:
            return None
        return Fraction(self.votos, self.validos_onde)


@dataclass(slots=True)
class _CityDraft:
    nome: str
    comparecimento: int
    votos: dict[str, dict[int, int]] = field(default_factory=dict)


def municipal_uf(nome: str) -> str | None:
    found = _SUFIXO.search(nome)
    if found is None:
        return None
    code = found.group(1)
    if code in _STATES or code == EXTERIOR:
        return code
    return None


def vertical_base(ano: int, turno: int, lines: tuple[VerticalLine, ...]) -> VerticalBase:
    year = ElectionYear(ano).value
    turn = Turno(turno).value
    states: dict[str, dict[str, dict[int, int]]] = {}
    cities: dict[str, _CityDraft] = {}
    for line in lines:
        if line.votos == 0:
            continue
        if line.nivel == _UF:
            _put_state(states, line)
        else:
            _put_city(cities, line)
    _require_cargos(states)
    grouped, orphans = _group_cities(cities)
    return VerticalBase(year, turn, states, grouped, orphans)


def cargo_share(base: VerticalBase, ufs: tuple[str, ...], cargo: str, partido: int) -> CargoShare:
    votos = validos = onde = concorreu = total = 0
    for uf in ufs:
        valid = base.validos_uf(uf, cargo)
        if valid == 0:
            continue
        total += 1
        validos += valid
        own = base.votos_uf(uf, cargo).get(partido, 0)
        if own > 0:
            votos += own
            onde += valid
            concorreu += 1
    return CargoShare(cargo, votos, validos, onde, concorreu, total)


def _put_state(states: dict[str, dict[str, dict[int, int]]], line: VerticalLine) -> None:
    if line.codigo == EXTERIOR:
        return
    if line.codigo not in _STATES:
        raise InconsistentCellError()
    by_cargo = states.setdefault(line.codigo, {}).setdefault(line.cargo, {})
    by_cargo[line.partido] = by_cargo.get(line.partido, 0) + line.votos


def _put_city(cities: dict[str, _CityDraft], line: VerticalLine) -> None:
    draft = cities.get(line.codigo)
    if draft is None:
        draft = _CityDraft(line.nome, line.comparecimento)
        cities[line.codigo] = draft
    draft.comparecimento = max(draft.comparecimento, line.comparecimento)
    by_cargo = draft.votos.setdefault(line.cargo, {})
    by_cargo[line.partido] = by_cargo.get(line.partido, 0) + line.votos


def _require_cargos(states: Mapping[str, Mapping[str, Votes]]) -> None:
    present = {cargo for by_cargo in states.values() for cargo in by_cargo}
    for cargo in CARGOS:
        if cargo not in present:
            raise MissingPowerReportError(cargo)


def _group_cities(
    cities: Mapping[str, _CityDraft],
) -> tuple[dict[str, tuple[MunicipioVertical, ...]], int]:
    grouped: dict[str, list[MunicipioVertical]] = {}
    orphans = 0
    for codigo, draft in cities.items():
        uf = municipal_uf(draft.nome)
        if uf is None:
            orphans += 1
            continue
        if uf == EXTERIOR:
            continue
        validos = {cargo: sum(votes.values()) for cargo, votes in draft.votos.items()}
        city = MunicipioVertical(codigo, draft.nome, uf, draft.comparecimento, draft.votos, validos)
        grouped.setdefault(uf, []).append(city)
    ordered = {
        uf: tuple(sorted(items, key=lambda city: (city.nome.casefold(), city.codigo)))
        for uf, items in grouped.items()
    }
    return ordered, orphans


def _text(value: str) -> str:
    if not isinstance(value, str) or value.strip() == "":
        raise InconsistentCellError()
    return value.strip()


def _count(value: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise InconsistentCellError()
```

- [x] **Step 4: Rodar até passar**

Run: `uv run pytest tests/domain/test_verticalizacao.py -q && uv run mypy src/eleicoes/domain/verticalizacao.py tests/domain/test_verticalizacao.py && uv run ruff check src/eleicoes/domain/verticalizacao.py tests/domain/test_verticalizacao.py`
Expected: `5 passed`, `Success: no issues found in 2 source files`, `All checks passed!`.

**If Task Fails:** um `MissingPowerReportError` inesperado indica que `every_cargo` não cobriu os 5 cargos. Se o mypy reclamar de `Mapping` num dataclass congelado, confira o `eq=False`.

---

### Task 2: Regras puxador / base / alinhado / sem candidato

**Files:**
- Create: `src/eleicoes/domain/verticalizacao_regras.py`
- Test: `tests/domain/test_verticalizacao_regras.py`

**Interfaces:**
- Consumes: `VerticalBase` e as constantes da Task 1.
- Produces: `RAZAO`, `DIFERENCA`, `BASE_RELEVANTE`, `PUXADOR`, `BASE`, `ALINHADO`, `SEM_CANDIDATO`, `PARES_CANONICOS`, `classify`, `UfComparison`, `AbsentState`, `Comparison` e `compare`.

- [x] **Step 1: Testes que falham**

```python
"""Puxador / base rules. Thresholds count at the boundary."""

from fractions import Fraction as F

from tests.domain.test_verticalizacao import every_cargo, uf_lines

from eleicoes.domain.verticalizacao import DEPUTADO_ESTADUAL, GOVERNADOR, vertical_base
from eleicoes.domain.verticalizacao_regras import (
    ALINHADO,
    BASE,
    PUXADOR,
    SEM_CANDIDATO,
    classify,
    compare,
)


def test_classify_boundaries() -> None:
    assert classify(F(40, 100), F(20, 100)) == PUXADOR
    assert classify(F(39, 100), F(20, 100)) == ALINHADO
    assert classify(F(12, 100), F(1, 100)) == PUXADOR
    assert classify(F(8, 100), F(0)) == ALINHADO
    assert classify(F(10, 100), F(30, 100)) == BASE
    assert classify(F(10, 100), F(19, 100)) == ALINHADO


_PAIR = (GOVERNADOR, DEPUTADO_ESTADUAL)


def _state(
    uf: str, governador: dict[int, int], estadual: dict[int, int]
) -> tuple[VerticalLine, ...]:
    return (
        *every_cargo(uf, skip=_PAIR),
        *uf_lines(GOVERNADOR, uf, governador),
        *uf_lines(DEPUTADO_ESTADUAL, uf, estadual),
    )


def test_compare_uses_the_running_parties_as_the_pool() -> None:
    base = vertical_base(2026, 1, _state("SP", {13: 70, 22: 30}, {13: 10, 22: 30, 45: 60}))
    ufs = base.scope(None)
    pt = compare(base, ufs, 13, *_PAIR)
    assert (pt.majoritaria, pt.esperada, pt.classe) == (F(70, 100), F(10, 40), PUXADOR)
    assert pt.razao == F(14, 5)
    pl = compare(base, ufs, 22, *_PAIR)
    assert (pl.majoritaria, pl.esperada, pl.classe) == (F(30, 100), F(30, 40), BASE)
    psdb = compare(base, ufs, 45, *_PAIR)
    assert psdb.classe == SEM_CANDIDATO and psdb.majoritaria is None
    assert [(item.uf, item.proporcional) for item in psdb.sem_candidato] == [("SP", F(60, 100))]
    assert compare(base, ufs, 99, *_PAIR).classe is None


def test_pooled_share_weights_states_by_majoritarian_valid_votes() -> None:
    lines = (
        *_state("SP", {13: 60, 22: 40}, {13: 20, 22: 20}),
        *_state("MG", {13: 10, 15: 90}, {13: 10, 15: 30}),
    )
    base = vertical_base(2026, 1, lines)
    pt = compare(base, base.scope(None), 13, *_PAIR)
    assert pt.majoritaria == F(70, 200)
    assert pt.esperada == (F(1, 2) * 100 + F(1, 4) * 100) / 200
    assert [(row.uf, row.classe) for row in pt.por_uf] == [("MG", BASE), ("SP", ALINHADO)]
```

Inclua `VerticalLine` no import de `eleicoes.domain.verticalizacao`. Conta conferida: em MG, a majoritária é 10% e a esperada 25%; como 25 ≥ 2 × 10 e a diferença é de 15 pp, a classe é base. Em SP, 60% contra 50% dá alinhado. A soma das UF dá 35% contra 37,5%, também alinhado.

- [x] **Step 2:** `uv run pytest tests/domain/test_verticalizacao_regras.py -q` → `ModuleNotFoundError`.

- [x] **Step 3: Implementar**

```python
"""Puxador / base: the majoritarian share against what the proportional base predicts."""

from dataclasses import dataclass
from fractions import Fraction
from typing import Final

from eleicoes.domain.verticalizacao import (
    DEPUTADO_ESTADUAL,
    DEPUTADO_FEDERAL,
    GOVERNADOR,
    PRESIDENTE,
    SENADOR,
    VerticalBase,
)

RAZAO: Final = 2
DIFERENCA: Final = Fraction(1, 10)
BASE_RELEVANTE: Final = Fraction(1, 20)
PUXADOR: Final = "puxador"
BASE: Final = "base"
ALINHADO: Final = "alinhado"
SEM_CANDIDATO: Final = "sem_candidato"
PARES_CANONICOS: Final[tuple[tuple[str, str], ...]] = (
    (GOVERNADOR, DEPUTADO_ESTADUAL),
    (SENADOR, DEPUTADO_FEDERAL),
    (PRESIDENTE, DEPUTADO_FEDERAL),
)


@dataclass(frozen=True, slots=True)
class UfComparison:
    uf: str
    majoritaria: Fraction
    esperada: Fraction
    classe: str


@dataclass(frozen=True, slots=True)
class AbsentState:
    uf: str
    proporcional: Fraction


@dataclass(frozen=True, slots=True)
class Comparison:
    majoritario: str
    proporcional: str
    majoritaria: Fraction | None
    esperada: Fraction | None
    classe: str | None
    por_uf: tuple[UfComparison, ...]
    sem_candidato: tuple[AbsentState, ...]

    @property
    def razao(self) -> Fraction | None:
        if self.majoritaria is None or self.esperada is None or self.esperada == 0:
            return None
        return self.majoritaria / self.esperada


def classify(majoritaria: Fraction, esperada: Fraction) -> str:
    if majoritaria >= RAZAO * esperada and majoritaria - esperada >= DIFERENCA:
        return PUXADOR
    if esperada >= RAZAO * majoritaria and esperada - majoritaria >= DIFERENCA:
        return BASE
    return ALINHADO


def compare(
    base: VerticalBase,
    ufs: tuple[str, ...],
    partido: int,
    majoritario: str,
    proporcional: str,
) -> Comparison:
    rows: list[UfComparison] = []
    absent: list[AbsentState] = []
    for uf in ufs:
        row = _uf_row(base, uf, partido, majoritario, proporcional)
        if row is not None:
            rows.append(row)
            continue
        missing = _absent(base, uf, partido, majoritario, proporcional)
        if missing is not None:
            absent.append(missing)
    if not rows:
        classe = SEM_CANDIDATO if absent else None
        return Comparison(majoritario, proporcional, None, None, classe, (), tuple(absent))
    weights = [base.validos_uf(row.uf, majoritario) for row in rows]
    total = sum(weights)
    maj = sum((row.majoritaria * w for row, w in zip(rows, weights, strict=True)), Fraction(0))
    esp = sum((row.esperada * w for row, w in zip(rows, weights, strict=True)), Fraction(0))
    majoritaria = maj / total
    esperada = esp / total
    return Comparison(
        majoritario,
        proporcional,
        majoritaria,
        esperada,
        classify(majoritaria, esperada),
        tuple(rows),
        tuple(absent),
    )


def _uf_row(
    base: VerticalBase,
    uf: str,
    partido: int,
    majoritario: str,
    proporcional: str,
) -> UfComparison | None:
    running = base.votos_uf(uf, majoritario)
    own = running.get(partido, 0)
    valid_m = sum(running.values())
    prop = base.votos_uf(uf, proporcional)
    if own == 0 or valid_m == 0 or not prop:
        return None
    pool = sum(prop.get(party, 0) for party in running)
    esperada = Fraction(0) if pool == 0 else Fraction(prop.get(partido, 0), pool)
    majoritaria = Fraction(own, valid_m)
    return UfComparison(uf, majoritaria, esperada, classify(majoritaria, esperada))


def _absent(
    base: VerticalBase,
    uf: str,
    partido: int,
    majoritario: str,
    proporcional: str,
) -> AbsentState | None:
    if base.concorreu(uf, majoritario, partido) or not base.concorreu(uf, proporcional, partido):
        return None
    valid = base.validos_uf(uf, proporcional)
    return AbsentState(uf, Fraction(base.votos_uf(uf, proporcional)[partido], valid))
```

- [x] **Step 4:** `uv run pytest tests/domain/test_verticalizacao_regras.py -q && uv run mypy src tests && uv run ruff check src tests` → tudo verde.

**If Task Fails:** se a esperada der 0/0, confira o `pool == 0`. Se a soma dos pesos estiver errada, imprima `weights` no teste e compare com os válidos da UF.

---

### Task 3: Coerência intra-UF e pontos da dispersão

**Files:**
- Create: `src/eleicoes/domain/verticalizacao_coerencia.py`
- Test: `tests/domain/test_verticalizacao_coerencia.py`

**Interfaces:**
- Consumes: `VerticalBase`, `MunicipioVertical` e as constantes.
- Produces: `MINIMO_MUNICIPIOS`, `PARES_COERENCIA`, `Coherence`, `ScatterPoint`, `coherence` e `scatter_points`.

- [x] **Step 1: Testes que falham** (com fixture de municípios via `city_lines` e linhas de UF com votos > 0 nos dois cargos)
  1. **Offsets entre UF não contam.** Em SP há 5 municípios com x = 5, 10, 15, 20, 25% e y = 2x (10 a 50%). Em MG há 5 municípios com o mesmo x e y = 2x + 30 pp (40 a 80%). Toda fatia fica abaixo de 100%. Monte cada município com votos inteiros sobre 100 válidos por cargo, colocando o resto num partido 99. O r intra-UF é `pytest.approx(1.0)`, mesmo com o r agregado menor. Confira o agregado no teste com `numpy.corrcoef` para provar que ele é diferente.
  2. **Inverso.** y = 60% − x em 10 municípios de uma UF → `approx(-1.0)`.
  3. **Peso.** Em 12 municípios com comparecimentos diferentes, `r == approx(_ref)`. A referência vem de `numpy.cov(x, y, aweights=w)` calculado por UF depois de centrar. O numpy já está no `.venv` por causa do sklearn, mas só no teste.
  4. **Amostra pequena.** 9 municípios → `r is None` e `municipios == 9`.
  5. **UF de 1 município.** O DF com 1 município fica fora de n, mas aparece em `scatter_points`.
  6. **Ausência.** O partido sem governador em MG não traz os municípios de MG nem para a coerência nem para os pontos.
  7. **Variância nula.** x igual em todos → `None`.
  8. **UF sem o cargo.** Uma UF sem linhas de Dep. estadual (como o DF) não entra no par Dep. estadual × Governador, e os pontos dela não aparecem.

- [x] **Step 2:** `uv run pytest tests/domain/test_verticalizacao_coerencia.py -q` → `ModuleNotFoundError`.

- [x] **Step 3: Implementar**

```python
"""Within-state coherence: weighted Pearson on shares centred per UF."""

import math
from collections.abc import Iterator
from dataclasses import dataclass
from fractions import Fraction
from typing import Final

from eleicoes.domain.verticalizacao import (
    DEPUTADO_ESTADUAL,
    DEPUTADO_FEDERAL,
    MAJORITARIOS,
    PROPORCIONAIS,
    MunicipioVertical,
    VerticalBase,
)

MINIMO_MUNICIPIOS: Final = 10
_EPS: Final = 1e-12
PARES_COERENCIA: Final[tuple[tuple[str, str], ...]] = (
    *((prop, maj) for maj in MAJORITARIOS for prop in PROPORCIONAIS),
    (DEPUTADO_FEDERAL, DEPUTADO_ESTADUAL),
)


@dataclass(frozen=True, slots=True)
class Coherence:
    cargo_x: str
    cargo_y: str
    r: float | None
    municipios: int


@dataclass(frozen=True, slots=True)
class ScatterPoint:
    codigo: str
    nome: str
    uf: str
    comparecimento: int
    x: Fraction
    y: Fraction


def coherence(
    base: VerticalBase, ufs: tuple[str, ...], partido: int, x: str, y: str
) -> Coherence:
    sxy = sxx = syy = 0.0
    n = 0
    for cities in _paired(base, ufs, partido, x, y):
        if len(cities) < 2:
            continue
        part = _within(cities, partido, x, y)
        sxy += part[0]
        sxx += part[1]
        syy += part[2]
        n += len(cities)
    if n < MINIMO_MUNICIPIOS or sxx <= _EPS or syy <= _EPS:
        return Coherence(x, y, None, n)
    return Coherence(x, y, sxy / math.sqrt(sxx * syy), n)


def scatter_points(
    base: VerticalBase, ufs: tuple[str, ...], partido: int, x: str, y: str
) -> tuple[ScatterPoint, ...]:
    return tuple(
        ScatterPoint(
            city.codigo,
            city.nome,
            city.uf,
            city.comparecimento,
            Fraction(city.votos[x].get(partido, 0), city.validos[x]),
            Fraction(city.votos[y].get(partido, 0), city.validos[y]),
        )
        for cities in _paired(base, ufs, partido, x, y)
        for city in cities
    )


def _paired(
    base: VerticalBase, ufs: tuple[str, ...], partido: int, x: str, y: str
) -> Iterator[tuple[MunicipioVertical, ...]]:
    for uf in ufs:
        if not (base.concorreu(uf, x, partido) and base.concorreu(uf, y, partido)):
            continue
        cities = tuple(
            city
            for city in base.municipios.get(uf, ())
            if city.validos.get(x, 0) > 0 and city.validos.get(y, 0) > 0 and city.comparecimento > 0
        )
        if cities:
            yield cities


def _within(
    cities: tuple[MunicipioVertical, ...], partido: int, x: str, y: str
) -> tuple[float, float, float]:
    weights = [float(city.comparecimento) for city in cities]
    xs = [city.votos[x].get(partido, 0) / city.validos[x] for city in cities]
    ys = [city.votos[y].get(partido, 0) / city.validos[y] for city in cities]
    total = math.fsum(weights)
    mx = math.fsum(w * v for w, v in zip(weights, xs, strict=True)) / total
    my = math.fsum(w * v for w, v in zip(weights, ys, strict=True)) / total
    dx = [v - mx for v in xs]
    dy = [v - my for v in ys]
    return (
        math.fsum(w * a * b for w, a, b in zip(weights, dx, dy, strict=True)),
        math.fsum(w * a * a for w, a in zip(weights, dx, strict=True)),
        math.fsum(w * b * b for w, b in zip(weights, dy, strict=True)),
    )
```

Aqui o caminho quente usa float e não `Fraction` (30 partidos × 7 pares × 5.570 municípios). Só os pontos da dispersão, que são poucos, usam `Fraction`.

- [x] **Step 4:** `uv run pytest tests/domain/test_verticalizacao_coerencia.py -q && uv run mypy src tests && uv run ruff check src tests` → verde.

**If Task Fails:** um r fora de [-1, 1] indica centragem errada. Confira se a média é por UF. Um `KeyError` em `city.votos[x]` aparece se `_paired` deixou passar um município sem o cargo, e o filtro `validos.get(x, 0) > 0` evita isso.

---

### Task 4: Relatório, perfil e dispersão pedida

**Files:**
- Create: `src/eleicoes/domain/verticalizacao_relatorio.py`
- Test: `tests/domain/test_verticalizacao_relatorio.py`

**Interfaces:**
- Produces:
  ```python
  PERFIL_MISTO = "misto"; SEM_COMPARACAO = "sem_comparacao"
  NOTES: tuple[str, ...]
  @dataclass(frozen=True, slots=True)
  class PartyVertical: partido: int; cargos: tuple[CargoShare, ...]; coerencia: tuple[Coherence, ...]; comparacoes: tuple[Comparison, ...]
      # @property perfil -> str ; @property coerencia_mediana -> float | None
  @dataclass(frozen=True, slots=True)
  class VerticalReport: ano: int; turno: int; uf: str | None; municipios: int; sem_uf: int; partidos: tuple[PartyVertical, ...]
  @dataclass(frozen=True, slots=True)
  class ScatterView: partido: int; cargo_x: str; cargo_y: str; coerencia: Coherence; pontos: tuple[ScatterPoint, ...]
  @dataclass(frozen=True, slots=True)
  class VerticalView: report: VerticalReport; dispersao: ScatterView
  def profile(comparisons: tuple[Comparison, ...]) -> str
  def vertical_report(base: VerticalBase, uf: str | None) -> VerticalReport
  def scatter_view(base: VerticalBase, report: VerticalReport, partido: int | None, cargo_x: str, cargo_y: str) -> ScatterView
  ```

Regras:
- `vertical_report`: `ufs = base.scope(uf)`. Os partidos com voto em algum cargo de `ufs` saem na ordem D14. Para cada um, os 5 `cargo_share`, os 7 `coherence` (`PARES_COERENCIA`) e os 3 `compare` (`PARES_CANONICOS`). `municipios = Σ len(base.municipios.get(u, ()))`. `uf` do relatório é `None` ou `ufs[0]`.
- `coerencia_mediana`: `statistics.median` dos r não nulos dos 6 primeiros pares, ou `None`.
- `scatter_view`: `cargo_x` e `cargo_y` precisam estar em `CARGOS` e ser diferentes, senão `InvalidCargoError(valor)`. `partido` fora de 0..99 ou booleano dá `InvalidNumeroError`. Com `partido=None`, vale `report.partidos[0].partido`. Como `vertical_base` garante dados, a lista não fica vazia. Se ficar, vale `EmptyStoredCellsError()`. A coerência e os pontos vêm do mesmo escopo do relatório (`base.scope(report.uf)`).
- `NOTES`, em português e nesta ordem:
  1. "Lê só as células gravadas do relatório de poder; não lê os boletins."
  2. "Votos válidos são os nominais mais os de legenda. Brancos e nulos não entram."
  3. "Um partido concorreu a um cargo numa UF quando teve votos nesse cargo na UF. Onde não concorreu, a fatia não vale zero: aquela UF fica fora das contas do cargo para esse partido."
  4. "O exterior só vota para presidente e fica fora de todas as comparações."
  5. "Em 2026 cada eleitor tem dois votos para senador. A fatia de senador divide pelos votos dados, por isso um candidato raramente passa de 50%."
  6. "A coerência é a correlação de Pearson dentro de cada UF, ponderada pelo comparecimento do município. Com menos de 10 municípios, fica em branco."
  7. "O esperado é a fatia que o partido teria na majoritária se os votos seguissem a força dele na proporcional, entre os partidos que lançaram candidato."
  8. "O Distrito Federal não tem deputado estadual gravado. Por isso fica fora do par governador e deputado estadual e da coerência com deputado estadual."

- [x] **Step 1: Testes que falham**
  - `profile` com {puxador, alinhado} → `puxador`; {puxador, base} → `misto`; {sem_candidato, None} → `sem_comparacao`; {alinhado} → `alinhado`.
  - Ordem D14 com empate de deputado federal resolvido pelo deputado estadual.
  - `vertical_report(base, "SP").uf == "SP"`, e `vertical_report(base, None).municipios` soma as UF.
  - `scatter_view` padrão escolhe o primeiro partido. `cargo_x == cargo_y` dá `InvalidCargoError`, `"vereador"` dá `InvalidCargoError`, e `partido=100` dá `InvalidNumeroError`.
  - `coerencia_mediana` ignora a referência Fed × Est (um teste em que só a referência tem r não nulo dá `None`).
- [x] **Step 2:** rodar e ver falhar.
- [x] **Step 3:** implementar.
- [x] **Step 4:** `uv run pytest tests/domain -q -k verticalizacao && uv run mypy src tests && uv run ruff check src tests` → verde.

**If Task Fails:** um erro de import circular indica que `verticalizacao_relatorio` só pode importar dos três módulos anteriores, e nunca o contrário.

---

### Task 5: Code Review (domínio)

1. **REQUIRED SUB-SKILL:** use jarvis:codereview e despache todos os revisores em paralelo sobre `src/eleicoes/domain/verticalizacao*.py` e os testes.
2. Foco: D3, D7, D9, D11 e D12 conferidos contra o código. Bordas dos limiares. Nenhuma ausência vira zero.
3. Siga para a próxima task só com zero achados Critical, High ou Medium.

**Resultado (2026-10-22):** zero achados Critical, High ou Medium. Correções vindas da revisão: (a) na soma, `sem_candidato` só vale se o partido não concorreu à majoritária em nenhuma UF do recorte (D12); quem concorreu só onde a proporcional não está gravada (governador só no DF) fica com `classe: null`; (b) uma UF sem a majoritária gravada não gera "sem candidato"; (c) testes de borda com exatamente 2× e exatamente 10 pp; (d) o r é limitado a [−1, 1] contra arredondamento; (e) `MAX_PARTIDO` passou a ser compartilhado.

---

### Task 6: Porta, adaptador SQL e caso de uso

**Files:**
- Create: `src/eleicoes/ports/verticalizacao.py`
- Create: `src/eleicoes/adapters/postgres_verticalizacao.py`
- Create: `src/eleicoes/use_cases/verticalizacao.py`
- Test: `tests/adapters/test_postgres_verticalizacao.py`
- Test: `tests/use_cases/test_verticalizacao_base.py` (o nome `test_verticalizacao.py` colide com `tests/domain/test_verticalizacao.py`, porque as pastas de teste não têm `__init__.py`)

**Interfaces:**
```python
# ports/verticalizacao.py
class VerticalSource(Protocol):
    def vertical_lines(self, ano: int, turno: int) -> tuple[VerticalLine, ...]: ...
    def close(self) -> None: ...

# adapters/postgres_verticalizacao.py
class PostgresVerticalLines:
    def __init__(self, sessions: SyncSessionFactory) -> None: ...
    def vertical_lines(self, ano: int, turno: int) -> tuple[VerticalLine, ...]: ...
    def close(self) -> None: ...
def vertical_statement(ano: int, turno: int) -> Executable: ...

# use_cases/verticalizacao.py
def build_vertical_base(source: VerticalSource, ano: int, turno: int) -> VerticalBase: ...
def _production_reader() -> VerticalSource: ...
```

O adaptador copia a estrutura de `PostgresStoredLines` (`adapters/postgres_perfis.py`): uma sessão preguiçosa, `_guard` que transforma `SQLAlchemyError` ou `psycopg.Error` em `StoredReadError`, e `_as_tuple`, `_text` e `_count` locais. A duplicação é pequena e consciente, para não mexer num arquivo de outro relatório. A instrução:

```python
def vertical_statement(ano: int, turno: int) -> Executable:
    votos = (PowerReportLine.votos_nominais + PowerReportLine.votos_legenda).label("votos")
    return select(
        PowerReportLine.cargo,
        PowerReportLine.nivel,
        PowerReportLine.codigo,
        PowerReportLine.nome,
        PowerReportLine.comparecimento,
        PowerReportLine.partido,
        votos,
    ).where(
        PowerReportLine.ano == ano,
        PowerReportLine.turno == turno,
        PowerReportLine.nivel.in_(("municipio", "uf")),
        PowerReportLine.cargo.in_(CARGOS),
        (PowerReportLine.votos_nominais + PowerReportLine.votos_legenda) > 0,
    )
```

Cada linha vira `VerticalLine(*row)`, com 7 colunas. Com outra largura, a linha dá `InconsistentCellError`.

`build_vertical_base` valida `ElectionYear` e `Turno` antes de ler, e depois chama `vertical_base(year, turn, source.vertical_lines(year, turn))`. `_production_reader` copia `apresentar_classe_governador._production_reader` (com `load_dotenv`, `_host_settings` e `open_sync_session`) e devolve `PostgresVerticalLines`.

- [x] **Step 1: Testes que falham** (`ScriptedSession` de `tests/adapters/orm_fakes.py`)
  - Uma linha empurrada `("governador", "uf", "SP", "SP", 100, 13, 40)` vira `VerticalLine` igual. Há só 1 `Select`, e o SQL compilado em postgresql contém `analise.relatorio_poder_linha` e não contém `boletim`, `secoes` nem `raw.`. Os parâmetros incluem `municipio`, `uf` e os 5 cargos. A soma `votos_nominais + votos_legenda` aparece no SELECT e no WHERE.
  - Uma linha de 6 colunas dá `InconsistentCellError`.
  - `SQLAlchemyError` na execução dá `StoredReadError`.
  - `close()` fecha a sessão uma vez.
  - Caso de uso: uma fonte falsa com `turno=9` dá `InvalidTurnoError` sem chamar `vertical_lines`. Uma fonte falsa válida devolve `VerticalBase` com `ano == 2026`.
- [x] **Step 2:** rodar e ver falhar.
- [x] **Step 3:** implementar.
- [x] **Step 4:** `uv run pytest tests/adapters/test_postgres_verticalizacao.py tests/use_cases/test_verticalizacao.py -q && uv run mypy src tests && uv run ruff check src tests` → verde.

**If Task Fails:** se o `ScriptedSession` não devolver as linhas, leia `tests/adapters/orm_fakes.py:51` (`_rows`), que espera `push` antes de `execute`.

---

### Task 7: Job em cache, schema JSON e rota

**Files:**
- Create: `src/eleicoes/adapters/http/dependencies_verticalizacao.py`
- Create: `src/eleicoes/adapters/http/schemas_verticalizacao.py`
- Create: `src/eleicoes/adapters/http/verticalizacao.py`
- Modify: `src/eleicoes/adapters/http/dependencies.py` (import + 1 linha em `clear_report_caches`, perto da linha 133)
- Modify: `src/eleicoes/composition/api.py` (import perto da linha 24 + `application.include_router(verticalizacao_router)` depois da linha 48)
- Test: `tests/adapters/test_http_verticalizacao.py`

**Interfaces:**
```python
# dependencies_verticalizacao.py
VerticalJob: TypeAlias = Callable[[int, int, str | None, int | None, str, str], VerticalView]
def get_vertical_job() -> VerticalJob: ...
def clear_vertical_caches() -> None: ...   # _vertical_base.cache_clear(); _vertical_report.cache_clear()
# _stored_vertical(ano, turno, uf, partido, cargo_x, cargo_y):
#   year = ElectionYear(ano).value; turn = Turno(turno).value; code = None if uf is None else Uf(uf).code
#   report = _vertical_report(year, turn, code); return VerticalView(report, scatter_view(_vertical_base(year, turn), report, partido, cargo_x, cargo_y))
# @lru_cache(maxsize=2) _vertical_base(ano, turno): lazy import de use_cases.verticalizacao (_production_reader, build_vertical_base); try/finally reader.close()
# @lru_cache(maxsize=32) _vertical_report(ano, turno, uf): vertical_report(_vertical_base(ano, turno), uf)

# verticalizacao.py (router)
router = APIRouter(tags=["Relatórios"])
@router.get("/relatorios/dados/verticalizacao", summary="Verticalização", description=_VERTICAL)
async def verticalizacao(ano: int, turno: int, build: VerticalBuild, uf: str | None = None,
                         partido: int | None = None, cargo_x: str = DEPUTADO_FEDERAL,
                         cargo_y: str = GOVERNADOR) -> VerticalJson:
    view = await asyncio.to_thread(build, ano, turno, _uf(uf), partido, cargo_x, cargo_y)
    return VerticalJson.from_domain(view)
# _uf: None, "" ou "todas" (casefold) → None; senão o texto.
```

`_VERTICAL` = "Exige ano e turno. uf é opcional: sem ela, o recorte é o Brasil, e a coerência é calculada dentro de cada UF. partido, cargo_x e cargo_y escolhem a dispersão. Lê só as células gravadas dos cinco cargos; sem algum deles, responde 409."

O schema tem os modelos `CargoVerticalJson`, `CoerenciaJson`, `UfComparacaoJson`, `SemCandidatoJson`, `ComparacaoJson`, `PartidoVerticalJson`, `PontoJson`, `DispersaoJson`, `LimiaresJson` e `VerticalJson`, com campos e ordem exatamente como em "Contrato". Cada um tem `from_domain`, no padrão de `schemas_relatorios.ClassJson`. Fatias e esperadas usam `format_percent`. `r` usa `format_decimal(r)`. `razao` usa `format_decimal(float(razao))`. Um `None` vira `null`. `limiares` = `{"razao": str(RAZAO), "diferenca": format_percent(DIFERENCA), "base_relevante": format_percent(BASE_RELEVANTE), "minimo_municipios": MINIMO_MUNICIPIOS}`. `notas = list(NOTES)`.

- [x] **Step 1: Testes que falham** (com `create_app(ports=_ports())` de `tests/adapters/test_read_api.py` e `application.dependency_overrides[get_vertical_job] = lambda: job`, como em `test_relatorios_agrupamentos.py:515`)
  - A rota aparece no `/openapi.json` com `summary == "Verticalização"` e os parâmetros `{"ano","turno","uf","partido","cargo_x","cargo_y"}`.
  - Um job falso que devolve a `VerticalView` de uma base pequena dá 200, e o JSON tem as chaves do contrato, `cargos` com 5 itens, `coerencia` com 7 e `comparacoes` com 3. `r` nulo sai como `null`.
  - `uf=TODAS` e `uf=` chegam ao job como `None`. `uf=sp` chega como `"sp"` e o job normaliza.
  - Um job que levanta `MissingPowerReportError("senador")` dá 409 com o texto exato de `_MISSING` (ver Contrato).
  - Erros 422: `InvalidUfError` → "UF inválida.", `InvalidCargoError` → "Cargo inválido.", `InvalidNumeroError` → "Número inválido.", e `partido=abc` → "Parâmetros inválidos.".
  - Job real com monkeypatch de `eleicoes.use_cases.verticalizacao._production_reader`:
    - (a) constrói uma vez por (ano, turno), mesmo com duas UF diferentes;
    - (b) fecha o leitor;
    - (c) não guarda erro (como `test_stored_class_job_does_not_cache_an_error`);
    - (d) `clear_report_caches()` força uma nova leitura.
  - Use `clear_vertical_caches()` num fixture `autouse` para isolar os testes.
- [x] **Step 2:** rodar e ver falhar.
- [x] **Step 3:** implementar e encaixar (`api.py` e `dependencies.py`).
- [x] **Step 4:** `uv run pytest -q && uv run ruff check src tests && uv run ruff format --check src tests && uv run mypy src tests` → toda a suíte verde.

**If Task Fails:**
- Se 409 virar 500, confira se `MissingPowerReportError` não foi embrulhado. `asyncio.to_thread` repassa a exceção original.
- Se o cache vazar entre testes, falta `clear_vertical_caches()` no fixture.

---

### Task 8: Verificação real do backend

- [ ] **Step 1:** Reconstruir e subir a API: `docker compose build api && docker compose up -d api`. Esperado: o contêiner `api` em `healthy` depois de cerca de 20 s (`docker compose ps api`).
- [x] **Step 2:** `time curl -s 'http://localhost:15000/relatorios/dados/verticalizacao?ano=2026&turno=1' -o /tmp/claude-1000/vert.json -w '%{http_code}\n'`. Esperado: `200`, com o primeiro pedido em menos de 30 s e o segundo em menos de 1 s (cache).
- [x] **Step 3:** Conferir um número contra o SQL. Para o primeiro partido de `partidos` (P), a `fatia` de deputadoFederal deve bater, em 2 casas, com:
  ```sql
  select round(100.0 * sum(votos_nominais + votos_legenda) filter (where partido = P)
         / sum(votos_nominais + votos_legenda), 2)
  from analise.relatorio_poder_linha
  where ano = 2026 and turno = 1 and cargo = 'deputadoFederal' and nivel = 'uf' and codigo <> 'ZZ';
  ```
- [x] **Step 4:** Rodar `…&uf=SP&partido=13&cargo_x=deputadoEstadual&cargo_y=governador`. Esperado: `dispersao.pontos` com cerca de 645 itens (municípios de SP), ou `[]` se o 13 não concorreu a governador em SP, caso em que `comparacoes[0].sem_candidato` traz SP.
- [x] **Step 5:** `…&uf=ZZ` dá 422. `…&cargo_x=governador&cargo_y=governador` dá 422.
- [ ] **Step 6:** Memória: `docker stats --no-stream api`. Esperado: uso bem abaixo de 1,5 GiB depois do cache quente. Anote o valor no resumo da task.

**Resultado (2026-10-22, execução no worktree, sem Docker):** os Steps 2 a 5 rodaram em processo com `get_vertical_job()` contra o Postgres real, só leitura. Os Steps 1 e 6 (contêiner e `docker stats`) ficam para o orquestrador. Números:
- Brasil a frio: 3,4 s. Com cache: 0,015 s. JSON de 0,53 MB. Pico de memória do processo: 370 MB.
- `municipios = 5571`, `sem_uf = 0`, 30 partidos. O primeiro é o 22, e a fatia de deputado federal dele (22,64%) bate com o SQL do Step 3 (22.64).
- A dispersão padrão (22, Dep. federal × Governador) tem 3.118 pontos, com r = 0,3749.
- SP, partido 13, Dep. estadual × Governador: 645 pontos, r = 0,7450, classe `alinhado` e sem `sem_candidato`.
- `uf=DF`: Dep. estadual com `ufs_total = 0` ("n/a").
- `uf=ZZ` dá 422 "UF inválida.", e governador × governador dá 422 "Cargo inválido.".
- Calibração (classe somada no Brasil, 30 partidos):
  - Governador ↔ Dep. estadual: 24 alinhado, 2 puxador, 1 base, 3 sem candidato. Por UF: 161 alinhado, 9 puxador, 10 base.
  - Senador ↔ Dep. federal: 27 alinhado, 2 puxador, 1 sem candidato. Por UF: 221 alinhado, 28 puxador, 20 base.
  - Presidente ↔ Dep. federal: 11 alinhado, 1 base, 17 sem candidato, 1 null. Por UF: 291 alinhado, 10 puxador, 23 base.
  - Perfil: 23 alinhado, 4 puxador, 2 base, 1 sem comparação.
  - Os limiares ficam como estão, por decisão do usuário (rever depois).

---

### Task 9: Code Review (backend)

1. **REQUIRED SUB-SKILL:** jarvis:codereview com todos os revisores, sobre o diff do backend.
2. Foco: o contrato bate com "Contrato", os anexos nos arquivos compartilhados são mínimos e o cache é limpo.
3. Siga para a próxima task só com zero achados Critical, High ou Medium.

**Resultado (2026-10-22):** zero achados Critical, High ou Medium. Dois Low foram corrigidos: a validação do par de cargos e do partido (`require_scatter`) agora roda antes da carga em cache, e há testes HTTP com o job real para `uf=ZZ`, cargo x = y e `partido=100`. Ficam como limites conhecidos o build em dobro quando dois pedidos chegam a frio ao mesmo tempo (igual ao `ClassJob`) e o relatório em cache que sobrevive à base (`maxsize=2`).

---

### Task 10: Tipos, leitura do JSON e busca (frontend)

**Files:**
- Create: `frontend/src/lib/verticalizacao.ts`
- Modify: `frontend/src/lib/buscar-relatorios.ts` (import + função no fim das exportadas, antes de `async function buscar`)

**Interfaces:**
```ts
export const CARGOS_VERTICAIS = ["presidente", "governador", "senador", "deputadoFederal", "deputadoEstadual"] as const;
export type CargoVertical = (typeof CARGOS_VERTICAIS)[number];
export const ROTULO_CARGO: Record<CargoVertical, string>;   // "Presidente", "Governador", "Senador", "Dep. federal", "Dep. estadual"
export const CURTO_CARGO: Record<CargoVertical, string>;    // "Pres.", "Gov.", "Sen.", "Fed.", "Est."
export type Classe = "puxador" | "base" | "alinhado" | "sem_candidato";
export type Perfil = "puxador" | "base" | "alinhado" | "misto" | "sem_comparacao";
export type CargoVerticalDados = { cargo: CargoVertical; votos: number; validos: number; validos_onde: number; fatia: string | null; fatia_onde: string | null; ufs_concorreu: number; ufs_total: number };
export type Coerencia = { cargo_x: CargoVertical; cargo_y: CargoVertical; r: string | null; municipios: number };
export type ComparacaoUf = { uf: string; majoritaria: string; esperada: string; classe: Classe };
export type Comparacao = { majoritario: CargoVertical; proporcional: CargoVertical; majoritaria: string | null; esperada: string | null; razao: string | null; classe: Classe | null; por_uf: ComparacaoUf[]; sem_candidato: { uf: string; proporcional: string }[] };
export type PartidoVertical = { partido: number; perfil: Perfil; coerencia_mediana: string | null; cargos: CargoVerticalDados[]; coerencia: Coerencia[]; comparacoes: Comparacao[] };
export type PontoDispersao = { codigo: string; nome: string; uf: string; comparecimento: number; x: string; y: string };
export type RelatorioVerticalizacao = { ano: number; turno: number; uf: string | null; municipios: number; sem_uf: number; cargos: CargoVertical[]; limiares: { razao: string; diferenca: string; base_relevante: string; minimo_municipios: number }; partidos: PartidoVertical[]; dispersao: { partido: number; cargo_x: CargoVertical; cargo_y: CargoVertical; coerencia: Coerencia; pontos: PontoDispersao[] }; notas: string[] };
export function lerVerticalizacao(valor: unknown): RelatorioVerticalizacao;  // lança RespostaInvalidaError (de ./relatorios.ts)
export function lerDecimal(texto: string | null): number | null;            // "0,6213" | "-0,1200" → número; null → null
```

As funções de leitura (`exigirRegistro`, `exigirLista`, `exigirTexto`, `exigirTextoOuNulo`, `exigirInteiro` e uma `exigirCargo` nova) ficam **locais** neste arquivo. A duplicação de cerca de 40 linhas é consciente, para não mexer em `relatorios.ts` durante os planos paralelos. Ela fica como follow-up: extrair `lib/ler-json.ts` depois que os 6 planos entrarem.

Em `buscar-relatorios.ts`:
```ts
export function buscarVerticalizacao(
  ano: string, turno: string, uf: string, partido: string | null, cargoX: string, cargoY: string,
): Promise<Resultado<RelatorioVerticalizacao>> {
  const params = new URLSearchParams({ ano, turno, cargo_x: cargoX, cargo_y: cargoY });
  if (uf !== UF_TODAS) params.set("uf", uf);
  if (partido !== null) params.set("partido", partido);
  return buscar("/relatorios/dados/verticalizacao", params, lerVerticalizacao);
}
```

- [x] **Step 1:** Implementar.
- [x] **Step 2:** `cd frontend && pnpm exec tsc --noEmit && pnpm exec eslint src/lib/verticalizacao.ts src/lib/buscar-relatorios.ts`. Esperado: sem saída de erro.

---

### Task 11: Faixas de cor, layouts e frases (puro, com verificação)

**Files:**
- Create: `frontend/src/lib/grafico-verticalizacao.ts`
- Test: `frontend/src/lib/verificar-grafico-verticalizacao.ts`

**Interfaces:**
```ts
export const LIMITES_FATIA = [0.05, 0.10, 0.20, 0.35] as const;   // faixas 0..4: <5%, 5–10%, 10–20%, 20–35%, ≥35%
export const LIMITES_R = [0.2, 0.4, 0.6, 0.8] as const;           // |r| <0,2 → neutro; depois 1..4 por lado
export function faixaFatia(fatia: number | null): number | null;   // null → null (hachura)
export function faixaR(r: number | null): number | null;           // -4..4; 0 = neutro; null → null
export function corFatia(faixa: number): { fundo: string; tinta: string };   // "var(--vz-seq-2)", "var(--vz-seq-tinta-2)"
export function corR(faixa: number): { fundo: string; tinta: string };       // "var(--vz-div-n3)" … "var(--vz-div-0)" … "var(--vz-div-p4)"

export type MedidasMatriz = { largura: number; esquerda: number; topo: number; alturaLinha: number; vao: number; fonte: number; fonteCabeca: number; rotuloCurto: boolean };
export const MEDIDAS_MATRIZ: MedidasMatriz;          // largura 640, esquerda 132, topo 40, alturaLinha 24, vao 2, fonte 12, fonteCabeca 12, rotuloCurto false
export const MEDIDAS_MATRIZ_ESTREITO: MedidasMatriz; // largura 340, esquerda 84, topo 44, alturaLinha 26, vao 2, fonte 12, fonteCabeca 11, rotuloCurto true
export type CelulaMatriz = { chave: string; x: number; y: number; largura: number; altura: number; faixa: number | null; texto: string; dicaTitulo: string; dicaLinhas: string[] };
export type LayoutMatriz = { medidas: MedidasMatriz; largura: number; altura: number; colunas: { rotulo: string; x: number }[]; linhas: { rotulo: string; y: number }[]; celulas: CelulaMatriz[] };
export function matrizFatias(dados: RelatorioVerticalizacao, medidas?: MedidasMatriz): LayoutMatriz | null;
export function matrizCoerencia(dados: RelatorioVerticalizacao, medidas?: MedidasMatriz): LayoutMatriz | null;

export type MedidasDispersao = { largura: number; altura: number; esquerda: number; direita: number; topo: number; base: number; raioMin: number; raioMax: number; fonte: number };
export const MEDIDAS_DISPERSAO: MedidasDispersao;          // 640×400, esquerda 52, direita 16, topo 16, base 44, raio 1,5–8, fonte 12
export const MEDIDAS_DISPERSAO_ESTREITO: MedidasDispersao; // 340×320, esquerda 44, direita 12, topo 16, base 44, raio 1,5–6, fonte 13
export type PontoLayout = { chave: string; cx: number; cy: number; raio: number; dicaTitulo: string; dicaLinhas: string[] };
export type LayoutDispersao = { medidas: MedidasDispersao; marcasX: { x: number; texto: string }[]; marcasY: { y: number; texto: string }[]; diagonal: { x1: number; y1: number; x2: number; y2: number } | null; pontos: PontoLayout[]; rotuloX: string; rotuloY: string };
export function layoutDispersao(dados: RelatorioVerticalizacao, medidas?: MedidasDispersao): LayoutDispersao | null;

export function frasesVerticalizacao(dados: RelatorioVerticalizacao): string[];
export function resumoMatriz(layout: LayoutMatriz): string;   // texto do <desc>: todos os valores, linha por linha
```

Regras:
- **Matriz de fatias.** As linhas são os partidos na ordem do JSON, e as colunas são os 5 cargos. O texto da célula é `fatia_onde` sem o "%" e com 1 casa ("41,0"), porque a unidade vai no cabeçalho. Com `fatia_onde` nulo, o texto é "—" e a faixa é `null`. O tooltip tem o título `rotuloPartido(p) · ROTULO_CARGO[c]` e as linhas `Onde concorreu: 41,00%`, `No recorte todo: 26,97%` e `Concorreu em 9 de 27 UFs` (com `ufs_total === 1`, a última linha vira `Concorreu na UF` ou `Não concorreu na UF`). Com `ufs_total === 0`, a célula leva o texto "n/a", `faixa: null`, a marca `semEleicao: true` (campo a mais em `CelulaMatriz`) e uma única linha no tooltip: `Sem eleição gravada para este cargo no recorte`. O rótulo da linha é `rotuloPartido(p)` na largura padrão e `siglaPartido(p) ?? String(p)` na estreita.
- **Matriz de coerência.** As colunas são os 7 pares de `coerencia`, com cabeçalho `${CURTO_CARGO[x]}×${CURTO_CARGO[y]}`. A última coluna ganha um vão extra de 8 px e o cabeçalho "Ref." em cima, para marcar a referência. O texto é o r com 2 casas ("0,62" ou "−0,15", com o sinal de menos U+2212). Com r nulo, "—" com hachura. O tooltip tem `r = 0,6213` e `1.830 municípios`. Com r nulo, a linha vira `Menos de 10 municípios para medir` quando `municipios < 10`, e `Sem variação para medir` nos demais casos.
- **Dispersão.** x e y saem de `lerFatia`. Os eixos são independentes, de 0 ao teto "redondo" do maior valor (passos de 5, 10, 20 ou 25 pp, no máximo 5 marcas). A diagonal y = x é desenhada só no trecho dentro dos dois eixos e fica `null` se não couber. O raio é `raioMin + (raioMax − raioMin) · √(comparecimento ÷ maior)`. Os pontos saem em ordem decrescente de raio, para os pequenos ficarem por cima. O tooltip tem o título `nome` e as linhas `${ROTULO_CARGO[x]}: 12,30%`, `${ROTULO_CARGO[y]}: 40,10%` e `Comparecimento: 210.000`. Sem pontos, o layout é `null`.
- **Frases** (ordem fixa, texto exato):
  1. Coerência do primeiro partido no par escolhido na dispersão: `Dentro de cada UF, onde o ${rotulo} vai melhor para ${x minúsculo} ele também vai melhor para ${y minúsculo}? A coerência é ${forca} (r = 0,62, ${n} municípios).`. A força é "forte" para |r| ≥ 0,6, "moderada" de 0,3 a 0,6 e "fraca" abaixo de 0,3. Com r < 0, acrescenta "e inversa" depois da força. Com r nulo, a frase vira `Não há municípios suficientes para medir a coerência do ${rotulo} entre ${x} e ${y}.`. Com `uf` preenchida, "Dentro de cada UF" vira "Em ${nomeUf(uf)}".
  2. Até 3 puxadores (classe somada `puxador`), por razão decrescente, com razão nula primeiro: `${rotulo} puxa em ${cargo}: teve ${maj} onde concorreu, ${razao} vezes o esperado pela força em ${prop} (${esp}).`. Com razão nula, `${rotulo} puxa em ${cargo}: teve ${maj} onde concorreu sem base em ${prop}.`.
  3. Até 3 bases, por razão crescente: `${rotulo} tem base sem cabeça de chapa forte em ${cargo}: a força em ${prop} indicaria ${esp}, e veio ${maj}.`.
  4. Sem candidato relevante: para cada partido e par com `sem_candidato` filtrado por `proporcional ≥ limiares.base_relevante`, no máximo 3 frases, pelo maior número de UF: `${rotulo} não lançou ${cargo} em ${n} UF onde tem ${base_relevante} ou mais em ${prop} (${UFs}). Pode ter apoiado um aliado; isso não conta como fraqueza.`. Use "1 UF" no singular e "N UFs" no plural.
  5. Se sobrarem casos além dos 3 de cada tipo: `Mais ${k} casos na tabela.`.
  - Os nomes de cargo nas frases vêm em minúsculas: "presidente", "governador", "senador", "deputado federal" e "deputado estadual".

- [x] **Step 1:** Escrever `verificar-grafico-verticalizacao.ts` com `node:assert/strict` e um `RelatorioVerticalizacao` montado à mão. Casos:
  - bordas de faixa (0,05 → 1; 0,0499 → 0; 0,35 → 4; null → null; r 0,2 → 1; −0,2 → −1; 0,19 → 0; 0,8 → 4);
  - célula ausente com "—" e faixa null;
  - célula sem eleição (`ufs_total === 0`) com "n/a", `semEleicao: true` e o tooltip próprio;
  - `ufs_total === 1` no tooltip;
  - r negativo com U+2212;
  - vão da coluna "Ref.";
  - largura estreita ≤ 340 e nenhum rótulo estreito mais largo que `esquerda − 6` (via `larguraTexto`);
  - diagonal recortada, ou `null`, quando os eixos não se cruzam na faixa;
  - ordem dos pontos por raio;
  - as 5 frases com texto exato, inclusive o singular "1 UF", o r nulo e o "e inversa";
  - `resumoMatriz` contém todos os valores.
- [x] **Step 2:** `cd frontend && node --experimental-strip-types src/lib/verificar-grafico-verticalizacao.ts`. Esperado: `ERR_MODULE_NOT_FOUND`.
- [x] **Step 3:** Implementar.
- [x] **Step 4:** Rodar até imprimir `ok`. Depois `pnpm exec tsc --noEmit` e `pnpm exec eslint src/lib/grafico-verticalizacao.ts src/lib/verificar-grafico-verticalizacao.ts`.

**If Task Fails:** um import sem `.ts` quebra o `--experimental-strip-types`. Use `./fatia.ts`, `./partidos.ts` e assim por diante, como em `grafico-perfis.ts`.

---

### Task 12: Cores validadas (CSS da página)

**Files:**
- Create: `frontend/src/app/relatorios/verticalizacao/verticalizacao.css`

Valores (validados em 2026-10-22 com `node <skill>/dataviz/scripts/validate_palette.js "<rampa>" --ordinal --mode light --surface "#ffffff"` e `--mode dark --surface "#171717"`: todos ALL CHECKS PASS; a tinta de cada célula com contraste ≥ 4,5:1 por `contrast()`):

```css
:root {
  --vz-seq-0: #6fbdb3; --vz-seq-tinta-0: #0b0b0b;
  --vz-seq-1: #45a69c; --vz-seq-tinta-1: #0b0b0b;
  --vz-seq-2: #22897f; --vz-seq-tinta-2: #0b0b0b;
  --vz-seq-3: #0d6f6e; --vz-seq-tinta-3: #ffffff;
  --vz-seq-4: #0a4f4e; --vz-seq-tinta-4: #ffffff;
  --vz-div-n4: #a92b2a; --vz-div-tinta-n4: #ffffff;
  --vz-div-n3: #d03b3b; --vz-div-tinta-n3: #ffffff;
  --vz-div-n2: #e66767; --vz-div-tinta-n2: #0b0b0b;
  --vz-div-n1: #ef9a99; --vz-div-tinta-n1: #0b0b0b;
  --vz-div-0:  #f0efec; --vz-div-tinta-0:  #0b0b0b;
  --vz-div-p1: #86b6ef; --vz-div-tinta-p1: #0b0b0b;
  --vz-div-p2: #5598e7; --vz-div-tinta-p2: #0b0b0b;
  --vz-div-p3: #256abf; --vz-div-tinta-p3: #ffffff;
  --vz-div-p4: #104281; --vz-div-tinta-p4: #ffffff;
  --vz-hachura: var(--border);
}
.dark {
  --vz-seq-0: #1a6662; --vz-seq-tinta-0: #f0efec;
  --vz-seq-1: #2b9a91; --vz-seq-tinta-1: #0b0b0b;
  --vz-seq-2: #5bb8ae; --vz-seq-tinta-2: #0b0b0b;
  --vz-seq-3: #8fd0c8; --vz-seq-tinta-3: #0b0b0b;
  --vz-seq-4: #c4e8e4; --vz-seq-tinta-4: #0b0b0b;
  --vz-div-n4: #f2a7a6; --vz-div-tinta-n4: #0b0b0b;
  --vz-div-n3: #e66767; --vz-div-tinta-n3: #0b0b0b;
  --vz-div-n2: #b83b3a; --vz-div-tinta-n2: #f0efec;
  --vz-div-n1: #9a2f2e; --vz-div-tinta-n1: #f0efec;
  --vz-div-0:  #383835; --vz-div-tinta-0:  #f0efec;
  --vz-div-p1: #1c4a86; --vz-div-tinta-p1: #f0efec;
  --vz-div-p2: #2a6cc0; --vz-div-tinta-p2: #f0efec;
  --vz-div-p3: #5598e7; --vz-div-tinta-p3: #0b0b0b;
  --vz-div-p4: #9ec5f4; --vz-div-tinta-p4: #0b0b0b;
}
```

No escuro, a magnitude cresce para o claro, ou seja, o mais forte tem o maior contraste com a superfície. É uma escolha própria e não uma inversão automática. O tema escuro do app é a classe `.dark` (`globals.css:103`).

- [x] **Step 1:** Criar o arquivo. Rodar de novo o validador nas 6 rampas (teal claro e escuro, braço azul claro e escuro, braço vermelho claro e escuro, cada uma da faixa mais fraca para a mais forte) com `--ordinal`. Esperado: `ALL CHECKS PASS` nas 6. Rodar `node -e 'import("<skill>/scripts/validate_palette.js").then(m=>…contrast(tinta, fundo)…)'` nos 28 pares fundo/tinta. Esperado: todos ≥ 4,5. O caminho do skill é `/tmp/claude-1000/bundled-skills/2.1.308/b3ed5388aace147827b588d8cd073e96/dataviz/`, mas pode mudar: procure com `ls /tmp/claude-1000/bundled-skills/*/*/dataviz/scripts`.

---

### Task 13: Code Review (frontend puro)

1. **REQUIRED SUB-SKILL:** jarvis:codereview sobre as Tasks 10 a 12.
2. Foco: as frases batem com D11 e D12, nenhum null vira 0 e a acessibilidade do `<desc>` está completa.
3. Siga só com zero achados Critical, High ou Medium.

---

### Task 14: Componentes, página e navegador

**Files:**
- Create: `frontend/src/components/relatorios/matriz-verticalizacao.tsx` (servidor)
- Create: `frontend/src/components/relatorios/dispersao-verticalizacao.tsx` (servidor)
- Create: `frontend/src/components/relatorios/escolha-dispersao-verticalizacao.tsx` (cliente)
- Create: `frontend/src/components/relatorios/tabela-verticalizacao.tsx` (servidor)
- Create: `frontend/src/components/relatorios/dados-verticalizacao.tsx` (servidor)
- Create: `frontend/src/app/relatorios/verticalizacao/page.tsx`
- Modify: `frontend/src/components/layout/app-sidebar.tsx` (item `{ href: "/relatorios/verticalizacao", rotulo: "Verticalização" }`. É a 4ª entrada do bloco dos seis planos, que fica depois de "Classe do governador" e antes de "Mapa" na ordem Força partidária, Cadeiras, Capilaridade, Verticalização, Força da marca, Municipais 2024. Entra depois das anteriores que já existirem; alinhado em 2026-10-22)
- Modify (alinhado em 2026-10-22): `frontend/src/components/layout/app-breadcrumb.tsx` (`"/relatorios/verticalizacao": { pagina: "Verticalização", relatorios: true }`, na mesma posição)
- Modify (alinhado em 2026-10-22): `frontend/src/app/page.tsx` (`DESTINOS`: `{ href: "/relatorios/verticalizacao", titulo: "Verticalização", descricao: "Se a força de cada partido se sustenta entre presidente, governador, senador e deputados." }`, na mesma posição)

Desenho:
- **`MatrizVerticalizacao`** recebe `{ id, titulo, legenda, layout, estreito, escala: "fatia" | "r" }` e segue o padrão de `grafico-poder.tsx`: `<figure className="folha-quieta">`, `DicaGrafico`, um `<svg>` largo em `hidden sm:block overflow-x-auto` e um estreito em `sm:hidden`, com `role="img"`, `<title>` e `<desc>` (`resumoMatriz`). Cada célula é um `<rect rx={2}>` com fundo `corFatia` ou `corR`. O vão de 2 px entre células é a superfície. O texto central usa a tinta da faixa, `tabular-nums`. A célula nula usa `fill="url(#${id}-hachura${sufixo})"`: um `<pattern>` de linhas a 45° em `var(--vz-hachura)` sobre `var(--card)`, com o texto "—" em `text-muted-foreground`. A legenda fica em HTML abaixo do SVG: 5 amostras com o rótulo da faixa ("até 5%", "5–10%", "10–20%", "20–35%", "35% ou mais") e duas amostras de vazio: hachurada para "não concorreu" e com borda tracejada sem fundo para "sem eleição gravada". A célula `semEleicao` é um `<rect>` com `fill="none"`, `stroke="var(--border)"`, `strokeDasharray="3 2"` e o texto "n/a" em `text-muted-foreground`. Para r, as amostras são "−1 a −0,8" … "−0,2 a 0,2" … "0,8 a 1" e "sem medida". Cabeçalhos de coluna e rótulos de linha em `text-foreground`, nunca na cor da série.
- **`DispersaoVerticalizacao`** tem eixos e marcas em `var(--border)` e `text-muted-foreground`, e a diagonal tracejada em `var(--muted-foreground)` com o rótulo "mesma fatia nos dois cargos". Cada ponto é um único `<circle>` com `fill="var(--tinta-quente)" fillOpacity={0.35}`, `stroke="transparent" strokeWidth={8}` (a área de toque passa do ponto) e `data-dica-titulo` e `data-dica-linhas`. Há um `<circle>` por município e nenhum elemento extra (cerca de 5,6 mil nós por variante). O figcaption tem o r e o n do par. Sem pontos, aparece o parágrafo "O partido não concorreu aos dois cargos em nenhuma UF do recorte.".
- **`EscolhaDispersaoVerticalizacao`** (cliente) tem três `FiltroSelect`: "Partido" (as opções vêm de `dados.partidos`, com rótulo `rotuloPartido`), "Eixo x" e "Eixo y" (os 5 cargos). O botão "Mostrar" faz `router.replace` mantendo `ano`, `turno`, `uf` e `consultar`, e trocando `partido`, `x` e `y`, com `useTransition` e spinner, como em `filtros-curtos.tsx`. Com x = y, o botão fica desabilitado e aparece o texto "Escolha dois cargos diferentes.".
- **`TabelaVerticalizacao`** é a tabela acessível das comparações, com colunas Partido, Cargo, Onde concorreu, Esperado, Razão, Classe, UFs puxador, UFs base e Sem candidato (UFs). Os rótulos de classe são: puxador = "Puxador", base = "Base sem cabeça forte", alinhado = "Alinhado" e sem_candidato = "Sem candidato". Um `null` aparece como `TRACO`.
- **`DadosVerticalizacao`** busca com `buscarVerticalizacao` e trata o erro com `ErroRelatorio`, que mostra o 409 com a instrução de gerar o cargo. A ordem:
  1. "Em resumo", com `frasesVerticalizacao` (lista com marcadores);
  2. a explicação fixa;
  3. a matriz de fatias;
  4. a matriz de coerência;
  5. a escolha e a dispersão;
  6. a tabela;
  7. `NotasRelatorio` com `dados.notas`;
  8. com `sem_uf > 0`, a frase "N municípios ficaram de fora por não terem UF.".

  Texto da explicação fixa (português simples):
  - "A matriz mostra, para cada partido, a fatia dos votos válidos em cada cargo, contada só onde o partido teve candidato. Onde não teve, a célula fica riscada: não é fraqueza, é ausência."
  - "A coerência pergunta se, dentro de um mesmo estado, os municípios onde o partido vai melhor para deputado são também os municípios onde ele vai melhor na eleição majoritária. Vai de −1 (o contrário) a 1 (sempre juntos). A última coluna compara deputado federal com estadual e serve de referência."
  - "Puxador é o partido cuja candidatura majoritária teve pelo menos o dobro do esperado pela força em deputado, com 10 pontos ou mais de diferença. Base sem cabeça forte é o contrário. O esperado é a fatia que o partido teria se os votos da majoritária seguissem os de deputado entre os partidos que lançaram candidato."
- **`page.tsx`** copia `classe-governador/page.tsx` com `import "./verticalizacao.css"`, `metadata.title = "Verticalização"`, `maxDuration = 600` e `CHAVES_FILTRO = ["ano", "turno", "uf"]`. Usa `<FiltrosRelatorio ano turno uf />` sem cargo nem nível. Esse modo já existe: `relatorio-pagina.tsx:54` o usa na página presidente-governador, e lá o botão de HTML fica desabilitado. `ConsultaRelatorio` (`lib/eleicoes.ts:93`) não tem `partido`, `x` nem `y`, então declare no próprio `page.tsx` o tipo `type ConsultaVerticalizacao = ConsultaRelatorio & { partido?: ValorConsulta; x?: ValorConsulta; y?: ValorConsulta }` e use-o em `searchParams: Promise<ConsultaVerticalizacao>`, sem mexer no tipo compartilhado. Lê `partido` (inteiro 0..99 ou null), `x` e `y` (válidos em `CARGOS_VERTICAIS`, com padrão `deputadoFederal` e `governador`) e passa tudo a `DadosVerticalizacao`.

- [ ] **Step 1:** Implementar os componentes, a página e o item da sidebar.
- [ ] **Step 2:** `cd frontend && pnpm exec tsc --noEmit && pnpm exec eslint src/components/relatorios/*verticalizacao*.tsx src/app/relatorios/verticalizacao/page.tsx src/components/layout/app-sidebar.tsx src/components/layout/app-breadcrumb.tsx src/app/page.tsx && node --experimental-strip-types src/lib/verificar-grafico-verticalizacao.ts`. Esperado: sem erros e `ok`.
- [ ] **Step 3:** Conferir no navegador (chrome-devtools, aba própria `isolatedContext: "verticalizacao"`, com o `pnpm dev` do frontend e a API da Task 8):
  - `/relatorios/verticalizacao?ano=2026&turno=1&uf=TODAS&consultar=1`: as frases, as duas matrizes, a dispersão padrão e a tabela aparecem;
  - `uf=SP`: as fatias mudam e a coerência vale só para SP;
  - `partido=13&x=deputadoEstadual&y=governador`: a dispersão troca e o r do figcaption bate com a célula da matriz;
  - um partido sem governador numa UF aparece hachurado e com "—";
  - tema claro e escuro: o contraste das tintas é legível e a hachura aparece nos dois;
  - 375 px: as variantes estreitas, sem rolagem horizontal da página e sem rótulo cortado;
  - tooltip na célula e no ponto;
  - console sem erros;
  - peso da página: com `list_network_requests`, anote o tamanho transferido do documento e do payload RSC no recorte Brasil. Acima de 3 MB, aplique o mesmo recurso do "If Task Fails" (amostra na variante estreita) e registre;
  - `uf=DF`: a coluna Dep. estadual aparece como "n/a", não hachurada;
  - o 409 aparece com a mensagem (simule com um job falso ou pule, se não houver como sem mexer no banco);
  - item "Verticalização" ativo na sidebar.

  Salvar as capturas `verticalizacao-*.png` no scratchpad.
- [ ] **Step 4:** Sem commit nesta task.

**If Task Fails:**
- Se o `import "./verticalizacao.css"` falhar no build, mova o import para um `layout.tsx` novo em `app/relatorios/verticalizacao/`. O App Router aceita CSS global em layout e page.
- Se o SVG da dispersão ficar lento, meça com `performance_start_trace`. Se passar de 200 ms de script, reduza a variante estreita a uma amostra dos 2.000 maiores municípios e anote isso na legenda.

---

### Task 15: Code Review final

1. **REQUIRED SUB-SKILL:** jarvis:codereview com todos os revisores, sobre o diff completo.
2. Rodar de novo a suíte inteira, backend (`uv run pytest -q`, `ruff`, `mypy`) e frontend (`tsc`, `eslint`, `verificar`).
3. Siga só com zero achados Critical, High ou Medium. Depois, faça o commit com jarvis:commit, se o humano pedir.

---

## Perguntas em aberto

1. **Limiares.** `RAZAO = 2`, `DIFERENCA = 10 pp`, `BASE_RELEVANTE = 5%` e `MINIMO_MUNICIPIOS = 10` são escolhas de partida. Depois da Task 8, vale olhar quantos partidos caem em cada classe. Se quase todos forem "alinhado" ou "puxador", calibre só as constantes. As frases e os testes de borda acompanham a mudança.
2. **Presença por votos > 0.** Um candidato com 0 voto na UF inteira conta como ausente. É um limite aceito, porque não existe lista de candidaturas no banco.
3. **Indicador para o Placar (plano 1), respondida em 2026-10-22:** o consumo é opcional e fica na fase D do plano 1. O padrão é um link. As colunas `perfil` e `coerencia_mediana` só entram se o usuário pedir, e aí vêm em processo, por `get_vertical_job()`, com o custo do cache frio uma vez por (ano, turno). Não há rota leve nova.
4. **Partido com dois candidatos a senador na mesma UF.** Ele soma votos das duas candidaturas, e isso puxa o par Senador ↔ Dep. federal para "puxador". Sem dados de candidatura não dá para detectar. Fica como limite conhecido e entra na nota se aparecer na calibração.
5. **Senador com 2 vagas.** A nota fixa fala de 2026. Num ano de 1 vaga (2030), a nota muda. Um teste pode derivar "dois votos" da razão válidos ÷ comparecimento, se o projeto passar a ter outros anos.


## Decisões do usuário (2026-10-22)

O usuário aceitou as recomendações da revisão de coerência. Estas decisões valem sobre qualquer pergunta em aberto neste plano.

- **Fase D do placar:** só os links para Capilaridade, Verticalização e Força da marca e a coluna de voto de legenda (Tasks 19 e 20). A Task 21 não entra.
- **Limiares das classes:** manter os calibrados nos planos e rever depois da primeira execução com dados reais.
