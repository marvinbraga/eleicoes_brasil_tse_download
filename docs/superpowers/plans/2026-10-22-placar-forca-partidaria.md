# Placar de força partidária

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Review between tasks via jarvis:codereview.

**Goal:** Criar a página `/relatorios/forca`. Ela traz uma linha por partido (e, na fase B, por federação), com colunas agrupadas em três esferas, Federação, Estados e Municípios, que ficam lado a lado e não se fundem num índice único. A tabela se ordena por qualquer coluna. A página tem ainda um gráfico de barras por esfera, um detalhe por UF e uma explicação de cada coluna. Onde falta dado, a célula mostra "—".

**Architecture:** O backend ganha uma função de domínio pura (`domain/forca.py`), que calcula votos, lideranças e presença a partir das `StoredCell` já gravadas em `analise.relatorio_poder_linha`. Essa função não reconstrói `GradeDePoder`. Um caso de uso lê só os níveis necessários de cada cargo, com um método novo `load_levels` no store assíncrono, e degrada por cargo. A rota `GET /relatorios/dados/forca` devolve só inteiros: votos, totais e contagens. No frontend, um componente de servidor busca o JSON e entrega tudo a um componente cliente. Esse componente cuida de ordenação, limiar de presença, recorte por UF e detalhe do partido, sem nova chamada à API. Módulos puros (`lib/placar-forca.ts`, `lib/grafico-forca.ts`) montam as linhas, os textos e o layout do SVG, e cada um tem seu script `verificar-*.ts`. A fase B, que depende do plano 2, liga cadeiras e federações por uma porta Python definida aqui. A fase C, que depende do plano 6, liga os dados municipais de 2024 por outra porta.

**Tech Stack:** Python 3.14, FastAPI, Pydantic v2, SQLAlchemy 2 (ORM síncrono via `run_sync`), pytest, ruff (C90 com complexidade máxima 10, ARG), mypy strict. No frontend: Next.js 16.4, React 19, TypeScript, Tailwind 4 e shadcn/ui, sem biblioteca de gráficos e sem runner de teste. Os scripts de verificação rodam com `node --experimental-strip-types`.

**Spec:** Este arquivo. As fontes são as linhas gravadas de `analise.relatorio_poder_linha` (níveis `municipio`, `uf`, `regiao`, `pais`; colunas `codigo`, `nome`, `partido`, `comparecimento`, `votos_nominais`, `votos_legenda`), lidas por `src/eleicoes/adapters/postgres_relatorio_poder.py`. A mensagem 409 vem de `MissingPowerReportError`, em `src/eleicoes/domain/errors.py:215`.

## Fatos dos dados (consulta só de leitura em 2026-10-22)

| Cargo | Municípios | UFs (nível `uf`) | Partidos | Válidos no país |
|---|---|---|---|---|
| presidente | 5.688, dos quais 117 no exterior (`(ZZ)`) | 28, contando ZZ | 12 | 119.299.501 |
| governador | 5.571 | 27 | 27 | 112.196.754 |
| senador | 5.571 | 27 | 29 | 207.631.289 (dois votos por eleitor em 2026) |
| deputadoFederal | 5.571 | 27 | 28 | 114.107.982 |
| deputadoEstadual | 5.570 | **26, sem DF** (o DF elege deputado distrital, cargo sem células gravadas) | 29 | 111.662.018 |

- As linhas são densas: cada lugar tem uma célula para cada partido do cargo, mesmo com 0 voto. Um partido ausente das células do cargo não concorreu a ele.
- O código de município é único no país. A UF do município só aparece no `nome`, no sufixo `" (UF)"` (`consultas/grade.py:217`). O frontend já lê esse sufixo (`dados-poder.tsx`, `siglaDoNome`).
- Ler `read_power` para `deputadoEstadual` (162 mil células, todos os níveis) levou 2,24 s, e para `presidente` 0,9 s. O SQL sozinho leva 14 ms, então o gasto está em montar os objetos Python.
- Valores de referência para a Task 12, com `cargo_referencia=deputadoEstadual`:

| Partido | Presidente | Dep. federal | Dep. estadual: UFs em 1º | Municípios em 1º | % do eleitorado deles | Presença ≥ 5% |
|---|---|---|---|---|---|---|
| PL 22 | 47,03% | 22,64% | 11 de 26 | 1.323 | 41,41% | 4.477 |
| PT 13 | 45,16% | 12,97% | 2 de 26 | 523 | 9,78% | 4.457 |

  Há 3 municípios com empate no topo. Antes de comparar, refaça a conta se os relatórios forem regravados.

## Decisões

| # | Pergunta | Decisão |
|---|---|---|
| F1 | Endpoint novo ou várias chamadas à grade no frontend | **Endpoint `GET /relatorios/dados/forca?ano&turno&cargo_referencia`.** No nível municipal, a grade traz cerca de 160 mil células por cargo, alguns MB de JSON por chamada, e precisaríamos de 3 a 5 chamadas e da mesma regra de liderança reescrita em TypeScript. O endpoint devolve cerca de 28 recortes × 30 partidos, só inteiros, e a regra fica no domínio Python testado com pytest. |
| F2 | Como ler o store | Método novo `load_levels(ano, turno, cargo, niveis)` no `AsyncRelatorioPoderStore`, que filtra `nivel IN (...)` no SQL. O placar lê `presidente` e `deputadoFederal` em `pais` e `uf` (poucas centenas de linhas), `deputadoEstadual` em `uf` e o cargo de referência em `municipio`. Fica uma única leitura municipal grande (cerca de 2,2 s). Sem cache em memória nesta versão: cada consulta lê o banco, então uma regravação pelo CLI aparece sem reiniciar a API. |
| F3 | Base das frações | Votos válidos = `votos_nominais + votos_legenda`, nunca o comparecimento, como na P2 do plano do Poder. Brancos e nulos não entram. |
| F4 | Liderança | Num lugar com válidos > 0, lidera o partido com mais votos. Empate no topo não conta para ninguém e soma em `empates`, como na P7 do Poder. Município com 0 válidos não entra nem no N. A regra vale só para liderança em votos. As cadeiras da fase B seguem os desempates legais do plano 2 (D12 de lá), que atribuem a vaga e só marcam `empate` (alinhado em 2026-10-22). |
| F5 | Exterior (ZZ) | Fica fora de todo indicador por UF e por município. O % nacional de presidente usa a linha `pais`, que inclui o exterior, e a explicação diz isso. É o mesmo número da tela Poder. Os planos 3 e 4 tiram o exterior também do presidente nacional, então o número deles pode diferir do placar em centésimos. Essa diferença é aceita e fica na explicação (alinhado em 2026-10-22). |
| F6 | DF sem deputado estadual | "UFs em 1º" é "X de N", com N = UFs com válidos > 0 nos dados, hoje 26. No recorte DF, as colunas de deputado estadual mostram "—". Com o cargo de referência padrão, Brasília não entra nos indicadores municipais (N = 5.570), e a explicação diz isso. |
| F7 | Denominadores | Sempre vêm dos dados (`base` de cada recorte), nunca de constante: 5.570, 5.571 e 5.688 mudam com o cargo. |
| F8 | "—" contra 0 | "—" quando falta a fonte (cargo não gravado), quando o partido não tem célula naquele cargo (não concorreu) ou quando o lugar não existe na fonte (DF em deputado estadual). Se o partido concorreu e teve 0 voto, a célula mostra "0,00%" ou "0". Nas colunas de cadeiras (fase B), a porta do plano 2 traz um inteiro para todo partido do registro em toda UF. Ali, 0 quer dizer "não elegeu", e "—" aparece só com `cadeiras.disponivel: false`. Nas colunas de 2024 (fase C), "—" aparece no DF, que não tem eleição municipal, e quando o bloco não está disponível (alinhado em 2026-10-22). |
| F9 | Limiar de presença | Lista fixa `1, 2, 5, 10, 20` (%), com 5% como padrão. O backend devolve a contagem para todos os limiares, e a tela troca o limiar sem nova chamada. Presença conta o município quando `votos × 100 ≥ limiar × válidos` e votos > 0, então o limite está incluído. O denominador é N: todos os municípios com válidos > 0 no recorte e no cargo de referência. No plano 3, a `presenca` usa o mesmo numerador a 5% (inclusivo), mas o denominador é só o universo do partido (municípios das UFs onde ele teve voto). Por isso o placar não mostra a presença do plano 3. Na fase D, só a classe e o índice dela entram (alinhado em 2026-10-22). |
| F10 | Cargo de referência municipal | Parâmetro de URL `cargo` (filtro "Cargo de referência"), com os 5 cargos de `CARGOS_PODER` e `deputadoEstadual` como padrão. Mudar o cargo faz nova consulta, porque cada cargo exige uma leitura municipal de cerca de 2 s. O backend valida o valor contra a lista e responde 422 "Cargo inválido." para qualquer outro, inclusive `deputadoDistrital`. |
| F11 | Degradação | Por cargo. Cargo sem gravação, ou gravado sem linhas, vai para `faltando`, com o comando do CLI, e suas colunas mostram "—". Responde 409 só quando nenhuma das fontes está gravada (`MissingStrengthSourcesError`, com todos os comandos). A página mostra um aviso com os comandos que faltam. |
| F12 | Coluna extra | "Deputado estadual (% válidos)" entra na esfera Estados. O dado já é lido para "UFs em 1º", e sem ele o detalhe por UF não teria o voto estadual. |
| F13 | Índice composto | **Fica fora desta versão.** Os pilares têm unidades diferentes (% de votos, contagens, cadeiras), a normalização muda o ranking e o usuário ainda não respondeu se quer o índice. Nas fases A e B, dois ou mais pilares estariam incompletos, e o índice enganaria. Como a tabela já é montada no cliente, acrescentar o índice depois é barato. O esboço está na seção "Fase E" (era "Fase D"; renomeada e alinhada em 2026-10-22), que fica como pergunta em aberto. |
| F14 | Gráfico | Um painel por esfera, sem misturar unidades num eixo só. Em cada painel, um grupo por partido (os 8 primeiros na ordem atual da tabela) e uma barra por indicador da esfera, cada barra como **fração do total da sua esfera**: % dos válidos, UFs/N, municípios/N, cadeiras/513 (B), vagas/54 (B), governadores no 1º turno/27 (B) e cadeiras/1.059 (B). A coluna "no 2º turno de governador" não vira barra: ela conta presença na disputa, e a soma entre partidos é o dobro das UFs com 2º turno, então não tem denominador útil (alinhado em 2026-10-22). A escala é fixa de 0 a 100%. O rótulo de texto de cada barra ("Dep. fed.", "UFs em 1º") é a codificação principal, e a opacidade (1; 0,7; 0,45) só reforça. A tinta é única, `--tinta-quente`. Há variante estreita para celular (`MEDIDAS_ESTREITO`), com o rótulo acima da barra. |
| F15 | Detalhe por UF | São dois caminhos. (a) O seletor "Recorte" (Brasil ou uma das 27 UFs) troca a tabela e os gráficos para a UF; nesse recorte, "UFs em 1º" vira "1º em dep. estadual" (Sim/Não). (b) O botão no nome do partido abre "Partido por UF", uma tabela com uma linha por UF e as mesmas colunas. Tudo roda no cliente. |
| F16 | Ordem padrão | Deputado federal (% válidos) decrescente, que é a melhor medida única de tamanho nacional de partido. Em empate, vence o menor número de partido. Valores nulos ficam por último nas duas direções (`compararNumero`). |
| F17 | Filtros | Componente novo `filtros-forca.tsx` (ano, turno, cargo de referência). `FiltrosCurtos` está preso a `CargoPerfil`, que tem 3 cargos e não tem deputado estadual, e mexer nele tocaria a página de perfis. Limiar, recorte e ordenação ficam como estado do cliente, fora da URL. |
| F18 | Federações (B) | A linha de federação é **recalculada**, não somada. Os votos dos partidos membros se juntam por lugar, e só depois se escolhe o líder e se aplica o limiar. O domínio já recebe uma função `chave(partido) -> str`: na fase A ela é `str(partido)`, e na B é o mapeamento para `fed:<sigla>`. A composição das federações vem do plano 2 e não fica fixa no código. |
| F19 | Governadores e Senado | A fonte única é o plano 2. O plano 1 não deriva governador eleito no 1º turno das linhas `governador/uf`, embora isso seja possível, para não haver duas verdades. Senado não sai de `relatorio_poder_linha`, porque os dois candidatos de um partido se fundem na mesma célula. |
| F20 | Colunas B e C na fase A | Ficam ocultas enquanto a resposta não trouxer o bloco `cadeiras` ou `municipal_2024`. Quando o bloco vem, mas a simulação não foi gravada, as colunas aparecem com "—" e um aviso com o comando. |
| F21 | Formato do JSON | Só inteiros e textos, sem float e sem percentual formatado. O frontend forma frações com `formatarPercentualContagem(n, d)` e ordena com números exatos. |

## Global Constraints

- Mensagens internas (exceções, logs, docstrings) em inglês; textos ao usuário em português. Identificadores do domínio novo em português, como em `stored_grade.py` e `grade.py`.
- Sem migração Alembic: as fases A, B, C e D só leem tabelas. A revisão atual continua `0003`. As tabelas da fase B são a `0004` do plano 2, e as da fase C a `0005` do plano 6 (que depende da `0004`). Os planos 3, 4 e 5 não têm migração (alinhado em 2026-10-22).
- O código Python precisa ser compatível com 3.11, porque `pyproject.toml` fixa `target-version = "py311"` e mypy `python_version = "3.11"`, mesmo que o ambiente rode 3.14 (alinhado em 2026-10-22).
- Sem dependência nova, no Python e no frontend.
- Não alterar o banco. Não chamar a API com `atualizar=true`. Não derrubar o Compose.
- Sem git que muda estado. **Subagentes não rodam `git stash`, `git checkout` nem `git reset`**, porque há edições em paralelo. Commit só quando o usuário pedir, com jarvis:commit. `frontend/src/lib` e `frontend/src/components/relatorios` são rastreados pelo git.
- Os módulos `frontend/src/lib/forca.ts`, `placar-forca.ts` e `grafico-forca.ts` só importam por caminho relativo com `.ts`, e tipos com `import type`, para o Node rodar os scripts. Por isso `forca.ts` tem seus próprios `exigir*`: os de `relatorios.ts` não são exportados, e esse arquivo importa `@/lib/eleicoes`, que o Node não resolve.
- Verificação do backend: `uv run pytest -q`, `uv run ruff check .` e `uv run mypy`, todos limpos.
- Verificação do frontend: `cd frontend && node --experimental-strip-types src/lib/verificar-<nome>.ts`, `pnpm exec tsc --noEmit` e `pnpm lint`.
- Servidores: o Next na 14000 (`pnpm dev`) e a API na 15000 (container `eleicoes_brasil-api-1`). O código da API está dentro da imagem (sem volume e sem `--reload`), então a rota nova só aparece depois de `docker compose up -d --build api`. Esse comando recria só o serviço `api`; peça ao usuário antes de rodá-lo.

## Review Focus

- **Empate no topo** e **município com 0 válidos**: nenhum dos dois conta liderança, o de 0 válidos nem entra no N, e os dois casos estão nos testes da Task 1.
- **Limiar no limite** (exatamente 5%): conta como presente (teste da Task 1).
- **ZZ** fora dos indicadores por UF e por município, e dentro do % nacional de presidente (Task 2).
- **DF**: "—" nas colunas estaduais e municipais quando a referência é `deputadoEstadual` (Task 2 e navegador).
- **"—" contra 0** (F8): o partido 65 (PCdoB) não concorre a presidente e mostra "—"; um partido com 0 voto mostra "0,00%" (Tasks 2 e 8).
- **Desempenho**: a rota responde em menos de 10 s com dados reais (Task 12, `curl -w`).
- **Degradação**: um cargo ausente devolve 200 com `faltando`; todos ausentes devolvem 409 (Tasks 4 e 5).
- **Federação recalculada** (fase B): um teste em que a soma das lideranças dos membros difere da liderança da federação (Task 14).

## Integração entre os planos de 2026-10-22 (alinhado em 2026-10-22)

**Ordem de execução:** 2 (cadeiras) → 6 (municipais 2024) → 1 (fases A, B e C). Os planos 3, 4 e 5 podem entrar em qualquer ordem, antes ou depois. A fase A deste plano não depende de ninguém e pode começar em paralelo com o 2, desde que a integração nos arquivos compartilhados siga a ordem acima. A fase D vem depois dos planos 3, 4 e 5 e é opcional. Toda mudança em arquivo compartilhado é **só por adição**: um campo com default, uma linha numa lista, uma função ou uma classe no fim do arquivo. Ninguém reordena nem reescreve o que outro plano acrescentou.

**Migrações:** `0004` é do plano 2, e `0005` é do plano 6, com `down_revision = "0004"`. Os planos 1, 3, 4 e 5 não têm migração. Se o plano 6 for executado sem a `0004`, ele para e avisa, sem renumerar.

**Quem toca o quê** (arquivos compartilhados):

| Arquivo | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|
| `src/eleicoes/domain/errors.py` | `comando_relatorio_poder`, `MissingStrengthSourcesError`. O texto de `MissingPowerReportError` não muda. | `MissingSeatReportError`, `InvalidSeatRuleError`, `UnknownPartyRegistryError` | 2 classes no fim | — | — | erros municipais |
| `src/eleicoes/adapters/http/errors.py` (`_OWN_TEXT`) | 1 linha | 3 linhas | 2 linhas | — | — | 1 linha |
| `src/eleicoes/adapters/http/bundle.py` (`ReadPorts`) | `seat_estimates` (B), `municipal_2024` (C) | `seat_store` | — | — | — | `municipais` |
| `src/eleicoes/adapters/http/dependencies.py` | `get_seat_estimates` (B), `get_municipal_2024` (C) | `get_seat_store` | job e cache + `clear_report_caches` | 1 import + `clear_report_caches` | — | `get_municipal_reader` |
| `src/eleicoes/adapters/http/relatorios.py` | rota `forca` | rota `cadeiras` | rota `capilaridade` | — (router próprio) | — | rota `municipais-2024` |
| `src/eleicoes/composition/api.py` | — | — | — | 1 `include_router` | — | — |
| `src/eleicoes/adapters/http/schemas_relatorios.py` | classes `*ForcaJson` no fim | — (`schemas_cadeiras.py`) | — (arquivo próprio) | — (`schemas_verticalizacao.py`) | — | — (`schemas_municipais.py`) |
| `src/eleicoes/ports/relatorio_poder.py` + store | `load_levels` (atualiza todos os fakes) | — | — | — | — | — |
| `src/eleicoes/adapters/postgres_perfis.py` | — | — | 1 método + `municipal_statement` | — | — | — |
| `src/eleicoes/composition/wiring.py` | — | wiring da CLI de cadeiras | — | — | — | wiring dos comandos municipais |
| `composition/cli.py`, `settings.py`, `Makefile` | — | — | — | — | — | comandos `download-municipais` e `import-municipais` |
| `tests/adapters/test_orm_migrate.py` | — | cadeia até `0004` + 2 testes | — | — | — | troca a cadeia para terminar em `0005` + 2 testes (depois do 2) |
| `tests/adapters/test_read_api.py` (`expected`) | `/relatorios/dados/forca` + `load_levels` no fake | `/relatorios/dados/cadeiras` | `/relatorios/dados/capilaridade` | — | — | — (teste próprio) |
| `frontend/src/lib/buscar-relatorios.ts` | `buscarForca` | `buscarCadeiras` | `buscarCapilaridade` | `buscarVerticalizacao` | — | `buscarMunicipais2024` |
| `frontend/src/lib/relatorios.ts` | — | tipos + `lerCadeiras` | `export` nos `exigir*` | — | — | — |
| `app-sidebar.tsx`, `app-breadcrumb.tsx`, `app/page.tsx` | 1 entrada em cada | 1 entrada em cada | 1 entrada em cada | 1 entrada em cada | 1 entrada em cada | 1 entrada em cada |

**Navegação, ordem única** em `ITENS` (sidebar), `TRILHAS` (breadcrumb) e `DESTINOS` (página inicial). As seis entradas formam um bloco contínuo depois de "Classe do governador" e antes de "Mapa":

| # | Rota | Sidebar | Breadcrumb (`pagina`) | Plano |
|---|---|---|---|---|
| 1 | `/relatorios/forca` | Força partidária | Força partidária | 1 |
| 2 | `/relatorios/cadeiras` | Cadeiras | Simulação de cadeiras | 2 |
| 3 | `/relatorios/capilaridade` | Capilaridade | Capilaridade | 3 |
| 4 | `/relatorios/verticalizacao` | Verticalização | Verticalização | 4 |
| 5 | `/relatorios/marca` | Força da marca | Força da marca | 5 |
| 6 | `/relatorios/municipais-2024` | Municipais 2024 | Municipais 2024 | 6 |

Quem integra depois insere a sua entrada na posição dela, mesmo que alguma das anteriores ainda não exista.

**Definições comuns** (os planos citam esta lista):
- **Votos válidos:** `votos_nominais + votos_legenda`, sem brancos e nulos, em todos os planos. O plano 2 lê `raw.boletim` e conta só números com prefixo de partido, o que é equivalente.
- **UF do município:** vem do sufixo `" (UF)"` do nome gravado, em todos os planos. Hoje nenhum nome municipal fica sem sufixo (plano 4, "Fatos do dado"). Se aparecer um, cada plano reage de um jeito: este plano o ignora (`cidades`, Task 1), o plano 3 falha com `InconsistentCellError` e o plano 4 o conta em `sem_uf` e mostra. Nenhum dos três atribui o município a uma UF errada. A divergência é aceita porque o caso não ocorre nos dados, mas o Review Focus da Task 1 deve conferir que o descarte daqui não muda o N sem aviso.
- **Exterior (ZZ):** fora de todo indicador por UF e por município em todos os planos. A única exceção é o % nacional de presidente neste plano (F5), que usa a linha `pais`, como a tela Poder.
- **DF:** não há `deputadoEstadual` gravado em `relatorio_poder_linha`. Os boletins têm `deputadoDistrital`, que só o plano 2 lê. Por isso, no recorte DF, as Assembleias (fase B) mostram as 24 cadeiras da Câmara Legislativa, e as colunas de voto em deputado estadual mostram "—". O DF também não tem eleição municipal (fase C, "—").
- **Empate no topo:** não conta liderança para ninguém (F4). Vale só para liderança em votos.
- **"—" contra 0:** como em F8. O plano 4 separa "—" (não concorreu) de "n/a" (sem eleição gravada), e a página dele mantém essa separação. No placar, as duas aparecem como "—", e o motivo vai na dica e no texto acessível.
- **Presença:** fatia ≥ limiar, inclusiva (F9). Os denominadores diferem entre os planos 1 e 3 (ver F9). "Concorreu", no plano 4, é outra coisa: a linha de UF com votos > 0.

---

## Fase A: só com o que já existe

### Task 1: Domínio municipal (liderança e presença)

**Files:**
- Create: `src/eleicoes/domain/forca.py`
- Test: `tests/domain/test_forca.py`

**Interfaces:**
- Consumes: `StoredCell` de `eleicoes.domain.stored_grade`, `InvalidCargoError` de `eleicoes.domain.errors` e `uf_name` de `eleicoes.domain.values`.
- Produces (as Tasks 2, 4 e 5 usam):
  ```python
  CARGOS_REFERENCIA: Final[tuple[str, ...]]  # presidente, governador, senador, deputadoFederal, deputadoEstadual
  LIMIARES: Final[tuple[int, ...]] = (1, 2, 5, 10, 20)
  PAIS: Final = "BR"; EXTERIOR: Final = "ZZ"
  Chave = Callable[[int], str]
  def require_cargo_referencia(cargo: str) -> str
  def uf_do_nome(nome: str) -> str | None
  def por_partido(partido: int) -> str
  def lider(votos: Mapping[str, int]) -> str | None
  @dataclass(frozen=True, slots=True) class Cidade: codigo: str; uf: str; votos: tuple[tuple[str, int], ...]  # + property validos
  @dataclass(frozen=True, slots=True) class Presenca: limiar: int; municipios: int
  @dataclass(frozen=True, slots=True) class Municipal: lidera: int; validos_liderados: int; presenca: tuple[Presenca, ...]
  @dataclass(frozen=True, slots=True) class BaseMunicipal: municipios: int; validos: int; empates: int
  MUNICIPAL_VAZIO: Final[Municipal]
  def cidades(cells: Iterable[StoredCell], chave: Chave = por_partido) -> tuple[Cidade, ...]
  def resumo_municipal(lista: Iterable[Cidade]) -> tuple[BaseMunicipal, dict[str, Municipal]]
  ```

- [ ] **Step 1: Escrever os testes que falham** em `tests/domain/test_forca.py`:

```python
"""Party strength scoreboard. Hand-built cells; no database."""

import pytest

from eleicoes.domain.errors import InvalidCargoError
from eleicoes.domain.forca import (
    LIMIARES,
    MUNICIPAL_VAZIO,
    BaseMunicipal,
    Municipal,
    Presenca,
    cidades,
    lider,
    require_cargo_referencia,
    resumo_municipal,
    uf_do_nome,
)
from eleicoes.domain.stored_grade import StoredCell


def _cell(
    nivel: str,
    codigo: str,
    nome: str,
    partido: int,
    votos: int,
    legenda: int = 0,
) -> StoredCell:
    return StoredCell(nivel, codigo, nome, 1000, partido, votos, legenda)


CIDADES = (
    _cell("municipio", "1", "RIO BRANCO (AC)", 13, 50, 10),
    _cell("municipio", "1", "RIO BRANCO (AC)", 22, 40),
    _cell("municipio", "2", "XAPURI (AC)", 13, 5),
    _cell("municipio", "2", "XAPURI (AC)", 22, 95),
    _cell("municipio", "3", "MANAUS (AM)", 13, 50),
    _cell("municipio", "3", "MANAUS (AM)", 22, 50),
    _cell("municipio", "4", "JURUA (AM)", 13, 0),
    _cell("municipio", "4", "JURUA (AM)", 22, 0),
    _cell("municipio", "5", "ABU DHABI (ZZ)", 13, 10),
    _cell("municipio", "5", "ABU DHABI (ZZ)", 22, 0),
)


def _presenca(*contagens: int) -> tuple[Presenca, ...]:
    return tuple(Presenca(limiar, n) for limiar, n in zip(LIMIARES, contagens, strict=True))


def test_uf_comes_from_the_name_suffix_only() -> None:
    assert uf_do_nome("RIO BRANCO (AC)") == "AC"
    assert uf_do_nome("ABU DHABI (ZZ)") == "ZZ"
    assert uf_do_nome("Brasília") is None
    assert uf_do_nome("Xapuri (ac)") is None


def test_leader_needs_a_single_positive_top() -> None:
    assert lider({"13": 5, "22": 3}) == "13"
    assert lider({"13": 5, "22": 5}) is None
    assert lider({"13": 0, "22": 0}) is None
    assert lider({}) is None


def test_reference_office_is_one_of_the_five_stored() -> None:
    assert require_cargo_referencia("deputadoEstadual") == "deputadoEstadual"
    with pytest.raises(InvalidCargoError):
        require_cargo_referencia("deputadoDistrital")


def test_cities_skip_abroad_and_other_levels_and_add_party_votes() -> None:
    found = cidades((*CIDADES, _cell("uf", "AC", "Acre", 13, 9)))
    assert [(cidade.codigo, cidade.uf) for cidade in found] == [
        ("1", "AC"), ("2", "AC"), ("3", "AM"), ("4", "AM"),
    ]
    assert found[0].votos == (("13", 60), ("22", 40))
    assert found[0].validos == 100


def test_municipal_summary_counts_leaders_ties_and_inclusive_thresholds() -> None:
    base, por_chave = resumo_municipal(cidades(CIDADES))
    assert base == BaseMunicipal(municipios=3, validos=300, empates=1)
    assert por_chave["13"] == Municipal(1, 100, _presenca(3, 3, 3, 2, 2))
    assert por_chave["22"] == Municipal(1, 100, _presenca(3, 3, 3, 3, 3))
    assert Municipal(0, 0, _presenca(0, 0, 0, 0, 0)) == MUNICIPAL_VAZIO


def test_party_without_votes_in_valid_cities_is_left_out() -> None:
    zero = (*CIDADES, _cell("municipio", "1", "RIO BRANCO (AC)", 65, 0))
    _base, por_chave = resumo_municipal(cidades(zero))
    assert "65" not in por_chave
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `uv run pytest tests/domain/test_forca.py -q`
Expected: `ModuleNotFoundError: No module named 'eleicoes.domain.forca'` (erro de coleta).

- [ ] **Step 3: Implementar a primeira parte de `src/eleicoes/domain/forca.py`**

```python
"""Party strength scoreboard from stored power cells. Counts stay integers; the page divides."""

import re
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from typing import Final

from eleicoes.domain.errors import InvalidCargoError
from eleicoes.domain.stored_grade import StoredCell

CARGOS_REFERENCIA: Final[tuple[str, ...]] = (
    "presidente",
    "governador",
    "senador",
    "deputadoFederal",
    "deputadoEstadual",
)
LIMIARES: Final[tuple[int, ...]] = (1, 2, 5, 10, 20)
PAIS: Final = "BR"
EXTERIOR: Final = "ZZ"
_MUNICIPIO: Final = "municipio"
_SUFIXO: Final = re.compile(r" \(([A-Z]{2})\)$")

Chave = Callable[[int], str]


def require_cargo_referencia(cargo: str) -> str:
    if cargo not in CARGOS_REFERENCIA:
        raise InvalidCargoError(cargo)
    return cargo


def uf_do_nome(nome: str) -> str | None:
    found = _SUFIXO.search(nome)
    return None if found is None else found.group(1)


def por_partido(partido: int) -> str:
    return str(partido)


def lider(votos: Mapping[str, int]) -> str | None:
    if not votos:
        return None
    topo = max(votos.values())
    if topo <= 0:
        return None
    primeiros = [chave for chave, valor in votos.items() if valor == topo]
    return primeiros[0] if len(primeiros) == 1 else None


@dataclass(frozen=True, slots=True)
class Cidade:
    codigo: str
    uf: str
    votos: tuple[tuple[str, int], ...]

    @property
    def validos(self) -> int:
        return sum(valor for _chave, valor in self.votos)


@dataclass(frozen=True, slots=True)
class Presenca:
    limiar: int
    municipios: int


@dataclass(frozen=True, slots=True)
class Municipal:
    lidera: int
    validos_liderados: int
    presenca: tuple[Presenca, ...]


@dataclass(frozen=True, slots=True)
class BaseMunicipal:
    municipios: int
    validos: int
    empates: int


MUNICIPAL_VAZIO: Final = Municipal(0, 0, tuple(Presenca(limiar, 0) for limiar in LIMIARES))


def somar(cells: Iterable[StoredCell], chave: Chave) -> dict[str, int]:
    totais: dict[str, int] = {}
    for cell in cells:
        nome = chave(cell.partido)
        totais[nome] = totais.get(nome, 0) + cell.votos_nominais + cell.votos_legenda
    return totais


def cidades(cells: Iterable[StoredCell], chave: Chave = por_partido) -> tuple[Cidade, ...]:
    grupos: dict[str, list[StoredCell]] = {}
    ufs: dict[str, str] = {}
    for cell in cells:
        uf = uf_do_nome(cell.nome) if cell.nivel == _MUNICIPIO else None
        if uf is None or uf == EXTERIOR:
            continue
        grupos.setdefault(cell.codigo, []).append(cell)
        ufs[cell.codigo] = uf
    return tuple(
        Cidade(codigo, ufs[codigo], tuple(sorted(somar(items, chave).items())))
        for codigo, items in grupos.items()
    )


def resumo_municipal(lista: Iterable[Cidade]) -> tuple[BaseMunicipal, dict[str, Municipal]]:
    validas = tuple(cidade for cidade in lista if cidade.validos > 0)
    conta = _Contagem()
    for cidade in validas:
        conta.adicionar(cidade)
    base = BaseMunicipal(len(validas), sum(cidade.validos for cidade in validas), conta.empates)
    return base, conta.municipais()


class _Contagem:
    def __init__(self) -> None:
        self.empates = 0
        self._lidera: dict[str, int] = {}
        self._liderados: dict[str, int] = {}
        self._presenca: dict[str, list[int]] = {}
        self._votos: dict[str, int] = {}

    def adicionar(self, cidade: Cidade) -> None:
        votos = dict(cidade.votos)
        primeiro = lider(votos)
        if primeiro is None:
            self.empates += 1
        else:
            self._lidera[primeiro] = self._lidera.get(primeiro, 0) + 1
            self._liderados[primeiro] = self._liderados.get(primeiro, 0) + cidade.validos
        for chave, valor in votos.items():
            self._votos[chave] = self._votos.get(chave, 0) + valor
            self._marcar(chave, valor, cidade.validos)

    def _marcar(self, chave: str, valor: int, validos: int) -> None:
        contagem = self._presenca.setdefault(chave, [0] * len(LIMIARES))
        for indice, limiar in enumerate(LIMIARES):
            if valor > 0 and valor * 100 >= limiar * validos:
                contagem[indice] += 1

    def municipais(self) -> dict[str, Municipal]:
        positivas = (chave for chave, total in self._votos.items() if total > 0)
        return {chave: self._municipal(chave) for chave in positivas}

    def _municipal(self, chave: str) -> Municipal:
        pares = zip(LIMIARES, self._presenca[chave], strict=True)
        presenca = tuple(Presenca(limiar, n) for limiar, n in pares)
        return Municipal(self._lidera.get(chave, 0), self._liderados.get(chave, 0), presenca)
```

- [ ] **Step 4: Rodar até passar**

Run: `uv run pytest tests/domain/test_forca.py -q && uv run ruff check src/eleicoes/domain/forca.py tests/domain/test_forca.py && uv run mypy`
Expected: `6 passed`; ruff `All checks passed!`; mypy `Success: no issues found`.

- [ ] **Step 5: Sem commit** (só se o usuário pedir, com jarvis:commit).

**If Task Fails:**
1. Erro de importação: confira o nome do módulo e `InvalidCargoError` em `src/eleicoes/domain/errors.py:166`.
2. Presença com uma unidade a mais ou a menos: confira o `>=` (limite incluído) e se `validos` é a soma da cidade, não o `comparecimento`.
3. Não conseguiu se recuperar: registre o que falhou e pare.

---

### Task 2: Domínio dos recortes (país e UFs)

**Files:**
- Modify: `src/eleicoes/domain/forca.py` (acrescentar no fim)
- Test: `tests/domain/test_forca.py` (acrescentar)

**Interfaces:**
- Produces:
  ```python
  @dataclass(frozen=True, slots=True)
  class FontesForca:
      presidente: tuple[StoredCell, ...] | None
      deputado_federal: tuple[StoredCell, ...] | None
      deputado_estadual: tuple[StoredCell, ...] | None
      referencia: tuple[StoredCell, ...] | None
  @dataclass(frozen=True, slots=True)
  class BaseRecorte:
      validos_presidente: int | None; validos_deputado_federal: int | None
      validos_deputado_estadual: int | None; ufs_deputado_estadual: int | None
      municipal: BaseMunicipal | None
  @dataclass(frozen=True, slots=True)
  class ForcaUnidade:
      chave: str; partidos: tuple[int, ...]
      presidente: int | None; deputado_federal: int | None; deputado_estadual: int | None
      ufs_lider_estadual: int | None; municipal: Municipal | None
  @dataclass(frozen=True, slots=True)
  class Recorte: codigo: str; nome: str; base: BaseRecorte; unidades: tuple[ForcaUnidade, ...]
  @dataclass(frozen=True, slots=True)
  class PlacarForca:
      ano: int; turno: int; cargo_referencia: str; limiares: tuple[int, ...]
      pais: Recorte; ufs: tuple[Recorte, ...]; faltando: tuple[str, ...]
  def placar_forca(ano: int, turno: int, cargo_referencia: str, fontes: FontesForca,
                   chave: Chave = por_partido) -> PlacarForca
  ```

Regras que a assinatura não fixa:
- País: presidente e deputado federal vêm da linha `("pais", "BR")`. O deputado estadual do país é a soma das linhas `uf` com válidos > 0, sem ZZ, porque o placar não lê o nível `pais` desse cargo. `ufs_deputado_estadual` é o número dessas UFs, e `ufs_lider_estadual` conta em quantas o partido lidera.
- UF: presidente e deputado federal vêm de `("uf", UF)`. Se o lugar não existe na fonte, o valor é `None`. `ufs_deputado_estadual` vale 1 quando a UF tem deputado estadual com válidos > 0 e `None` quando não tem (DF). `ufs_lider_estadual` do partido vale 1 ou 0.
- Unidades de um recorte: as chaves com voto > 0 em alguma fonte do recorte (presidente, deputado federal, deputado estadual ou municípios), ordenadas pelo menor número de partido.
- Valor da unidade: `None` quando a fonte é `None`, quando o lugar falta na fonte ou quando a chave não aparece nas células daquele cargo (F8). Nos outros casos é `votos.get(chave, 0)`. O municipal da chave presente sem voto é `MUNICIPAL_VAZIO`.
- UFs do placar: os códigos de nível `uf` de todas as fontes, mais as UFs das cidades, sem ZZ, em ordem alfabética. O nome vem de `uf_name`. O país se chama `"Brasil"`.
- `faltando`: os cargos com fonte `None`, sem repetição, na ordem de `CARGOS_REFERENCIA`.

- [ ] **Step 1: Acrescentar os testes que falham**

```python
from eleicoes.domain.forca import (  # junte ao import do topo
    BaseRecorte,
    FontesForca,
    ForcaUnidade,
    placar_forca,
)

PRES = (
    _cell("pais", "BR", "Brasil", 13, 60),
    _cell("pais", "BR", "Brasil", 22, 40),
    _cell("uf", "AC", "Acre", 13, 10),
    _cell("uf", "AC", "Acre", 22, 20),
    _cell("uf", "ZZ", "Exterior", 13, 1),
    _cell("uf", "ZZ", "Exterior", 22, 0),
)
FED = (
    _cell("pais", "BR", "Brasil", 13, 30),
    _cell("pais", "BR", "Brasil", 22, 50),
    _cell("pais", "BR", "Brasil", 65, 20),
    _cell("uf", "AC", "Acre", 13, 5),
    _cell("uf", "AC", "Acre", 22, 5),
    _cell("uf", "AC", "Acre", 65, 0),
    _cell("uf", "AM", "Amazonas", 13, 7),
    _cell("uf", "AM", "Amazonas", 22, 3),
    _cell("uf", "AM", "Amazonas", 65, 0),
)
EST = (
    _cell("uf", "AC", "Acre", 13, 10),
    _cell("uf", "AC", "Acre", 22, 30),
    _cell("uf", "AC", "Acre", 65, 0),
    _cell("uf", "AM", "Amazonas", 13, 20),
    _cell("uf", "AM", "Amazonas", 22, 20),
    _cell("uf", "AM", "Amazonas", 65, 0),
    *CIDADES,
)



def test_country_cut_uses_country_rows_and_sums_state_rows() -> None:
    placar = placar_forca(2026, 1, "deputadoEstadual", FontesForca(PRES, FED, EST, EST))
    assert placar.faltando == ()
    assert placar.limiares == LIMIARES
    assert (placar.pais.codigo, placar.pais.nome) == ("BR", "Brasil")
    assert placar.pais.base == BaseRecorte(100, 100, 80, 2, BaseMunicipal(3, 300, 1))
    assert placar.pais.unidades == (
        ForcaUnidade("13", (13,), 60, 30, 30, 0, Municipal(1, 100, _presenca(3, 3, 3, 2, 2))),
        ForcaUnidade("22", (22,), 40, 50, 50, 1, Municipal(1, 100, _presenca(3, 3, 3, 3, 3))),
        ForcaUnidade("65", (65,), None, 20, 0, 0, MUNICIPAL_VAZIO),
    )


def test_state_cuts_leave_abroad_out_and_mark_missing_places() -> None:
    placar = placar_forca(2026, 1, "deputadoEstadual", FontesForca(PRES, FED, EST, EST))
    assert [recorte.codigo for recorte in placar.ufs] == ["AC", "AM"]
    acre, amazonas = placar.ufs
    assert acre.nome == "Acre"
    assert acre.base == BaseRecorte(30, 10, 40, 1, BaseMunicipal(2, 200, 0))
    assert acre.unidades == (
        ForcaUnidade("13", (13,), 10, 5, 10, 0, Municipal(1, 100, _presenca(2, 2, 2, 1, 1))),
        ForcaUnidade("22", (22,), 20, 5, 30, 1, Municipal(1, 100, _presenca(2, 2, 2, 2, 2))),
    )
    assert amazonas.base == BaseRecorte(None, 10, 40, 1, BaseMunicipal(1, 100, 1))
    assert amazonas.unidades[0] == ForcaUnidade(
        "13", (13,), None, 7, 20, 0, Municipal(0, 0, _presenca(1, 1, 1, 1, 1))
    )


def test_state_without_state_deputies_shows_no_state_columns() -> None:
    sem_df = (
        *FED,
        _cell("uf", "DF", "Distrito Federal", 13, 9),
        _cell("uf", "DF", "Distrito Federal", 22, 1),
    )
    placar = placar_forca(2026, 1, "deputadoEstadual", FontesForca(PRES, sem_df, EST, EST))
    distrito = next(recorte for recorte in placar.ufs if recorte.codigo == "DF")
    assert distrito.base == BaseRecorte(None, 10, None, None, None)
    assert distrito.unidades[0] == ForcaUnidade("13", (13,), None, 9, None, None, None)


def test_missing_sources_become_dashes_and_are_listed_in_office_order() -> None:
    placar = placar_forca(2026, 1, "governador", FontesForca(None, FED, EST, None))
    assert placar.faltando == ("presidente", "governador")
    assert placar.pais.base.validos_presidente is None
    assert placar.pais.base.municipal is None
    assert placar.pais.unidades[0].presidente is None
    assert placar.pais.unidades[0].municipal is None
    assert placar.pais.unidades[0].deputado_federal == 30
```

Depois de juntar os nomes ao import do topo, rode `uv run ruff check --fix tests/domain/test_forca.py` para ordenar o bloco (I001).

- [ ] **Step 2: Rodar e ver falhar**

Run: `uv run pytest tests/domain/test_forca.py -q`
Expected: `ImportError: cannot import name 'BaseRecorte'`.

- [ ] **Step 3: Implementar no fim de `forca.py`**

```python
from collections import Counter  # junte aos imports do topo
from eleicoes.domain.values import uf_name  # junte aos imports do topo

_PAIS_NOME: Final = "Brasil"
_UF: Final = "uf"
_PAIS_NIVEL: Final = "pais"
Votos = dict[str, int]


@dataclass(frozen=True, slots=True)
class FontesForca:
    presidente: tuple[StoredCell, ...] | None
    deputado_federal: tuple[StoredCell, ...] | None
    deputado_estadual: tuple[StoredCell, ...] | None
    referencia: tuple[StoredCell, ...] | None


@dataclass(frozen=True, slots=True)
class BaseRecorte:
    validos_presidente: int | None
    validos_deputado_federal: int | None
    validos_deputado_estadual: int | None
    ufs_deputado_estadual: int | None
    municipal: BaseMunicipal | None


@dataclass(frozen=True, slots=True)
class ForcaUnidade:
    chave: str
    partidos: tuple[int, ...]
    presidente: int | None
    deputado_federal: int | None
    deputado_estadual: int | None
    ufs_lider_estadual: int | None
    municipal: Municipal | None


@dataclass(frozen=True, slots=True)
class Recorte:
    codigo: str
    nome: str
    base: BaseRecorte
    unidades: tuple[ForcaUnidade, ...]


@dataclass(frozen=True, slots=True)
class PlacarForca:
    ano: int
    turno: int
    cargo_referencia: str
    limiares: tuple[int, ...]
    pais: Recorte
    ufs: tuple[Recorte, ...]
    faltando: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class _Fonte:
    lugares: Mapping[tuple[str, str], Votos]
    presentes: frozenset[str]

    def votos(self, nivel: str, codigo: str) -> Votos | None:
        return self.lugares.get((nivel, codigo))

    def codigos(self, nivel: str) -> tuple[str, ...]:
        return tuple(codigo for chave_nivel, codigo in self.lugares if chave_nivel == nivel)


@dataclass(frozen=True, slots=True)
class _Lugar:
    presidente: Votos | None
    deputado_federal: Votos | None
    deputado_estadual: Votos | None
    lideres_estaduais: Votos | None
    municipal: tuple[BaseMunicipal, dict[str, Municipal]] | None


def placar_forca(
    ano: int,
    turno: int,
    cargo_referencia: str,
    fontes: FontesForca,
    chave: Chave = por_partido,
) -> PlacarForca:
    cargo = require_cargo_referencia(cargo_referencia)
    contexto = _Contexto(fontes, chave)
    pais = contexto.recorte_pais()
    ufs = tuple(contexto.recorte_uf(uf) for uf in contexto.ufs())
    return PlacarForca(ano, turno, cargo, LIMIARES, pais, ufs, _faltando(cargo, fontes))


class _Contexto:
    def __init__(self, fontes: FontesForca, chave: Chave) -> None:
        referencia = fontes.referencia
        self._pres = _fonte(fontes.presidente, chave)
        self._fed = _fonte(fontes.deputado_federal, chave)
        self._est = _fonte(fontes.deputado_estadual, chave)
        self._ref = None if referencia is None else frozenset(chave(c.partido) for c in referencia)
        self._cidades = None if referencia is None else _por_uf(cidades(referencia, chave))
        self._estaduais = _estaduais(self._est)
        self._membros = _membros(fontes, chave)

    def ufs(self) -> tuple[str, ...]:
        codigos: set[str] = set(self._estaduais)
        for fonte in (self._pres, self._fed):
            if fonte is not None:
                codigos.update(fonte.codigos(_UF))
        if self._cidades is not None:
            codigos.update(self._cidades)
        codigos.discard(EXTERIOR)
        return tuple(sorted(codigos))

    def recorte_pais(self) -> Recorte:
        sem_fonte = self._est is None
        estadual = None if sem_fonte or not self._estaduais else _soma(self._estaduais.values())
        lugar = _Lugar(
            _at(self._pres, _PAIS_NIVEL, PAIS),
            _at(self._fed, _PAIS_NIVEL, PAIS),
            estadual,
            None if sem_fonte else _lideres(self._estaduais),
            self._municipal(None),
        )
        quantas = None if sem_fonte else len(self._estaduais)
        return Recorte(PAIS, _PAIS_NOME, self._base(lugar, quantas), self._unidades(lugar))

    def recorte_uf(self, uf: str) -> Recorte:
        estadual = self._estaduais.get(uf)
        lugar = _Lugar(
            _at(self._pres, _UF, uf),
            _at(self._fed, _UF, uf),
            estadual,
            None if estadual is None else _lideres({uf: estadual}),
            self._municipal(uf),
        )
        quantas = None if estadual is None else 1
        return Recorte(uf, uf_name(uf), self._base(lugar, quantas), self._unidades(lugar))

    def _municipal(self, uf: str | None) -> tuple[BaseMunicipal, dict[str, Municipal]] | None:
        if self._cidades is None:
            return None
        if uf is None:
            lista = [cidade for grupo in self._cidades.values() for cidade in grupo]
        else:
            lista = self._cidades.get(uf, [])
        return resumo_municipal(lista) if lista else None

    def _base(self, lugar: _Lugar, quantas: int | None) -> BaseRecorte:
        municipal = None if lugar.municipal is None else lugar.municipal[0]
        return BaseRecorte(
            _validos(lugar.presidente),
            _validos(lugar.deputado_federal),
            _validos(lugar.deputado_estadual),
            quantas,
            municipal,
        )

    def _unidades(self, lugar: _Lugar) -> tuple[ForcaUnidade, ...]:
        municipais = None if lugar.municipal is None else lugar.municipal[1]
        votos = (lugar.presidente, lugar.deputado_federal, lugar.deputado_estadual)
        chaves = _positivas(votos, municipais)
        unidades = (self._unidade(chave, lugar, municipais) for chave in chaves)
        return tuple(sorted(unidades, key=_ordem_unidade))

    def _unidade(
        self,
        chave: str,
        lugar: _Lugar,
        municipais: dict[str, Municipal] | None,
    ) -> ForcaUnidade:
        return ForcaUnidade(
            chave,
            self._membros.get(chave, ()),
            _valor(self._pres, lugar.presidente, chave),
            _valor(self._fed, lugar.deputado_federal, chave),
            _valor(self._est, lugar.deputado_estadual, chave),
            _valor(self._est, lugar.lideres_estaduais, chave),
            _municipal_de(self._ref, municipais, chave),
        )


def _fonte(cells: tuple[StoredCell, ...] | None, chave: Chave) -> _Fonte | None:
    if cells is None:
        return None
    lugares: dict[tuple[str, str], Votos] = {}
    for cell in cells:
        if cell.nivel == _MUNICIPIO:
            continue
        votos = lugares.setdefault((cell.nivel, cell.codigo), {})
        nome = chave(cell.partido)
        votos[nome] = votos.get(nome, 0) + cell.votos_nominais + cell.votos_legenda
    return _Fonte(lugares, frozenset(chave(cell.partido) for cell in cells))


def _estaduais(fonte: _Fonte | None) -> dict[str, Votos]:
    if fonte is None:
        return {}
    return {
        codigo: votos
        for (nivel, codigo), votos in fonte.lugares.items()
        if nivel == _UF and codigo != EXTERIOR and sum(votos.values()) > 0
    }


def _por_uf(lista: tuple[Cidade, ...]) -> dict[str, list[Cidade]]:
    grupos: dict[str, list[Cidade]] = {}
    for cidade in lista:
        grupos.setdefault(cidade.uf, []).append(cidade)
    return grupos


def _membros(fontes: FontesForca, chave: Chave) -> dict[str, tuple[int, ...]]:
    grupos: dict[str, set[int]] = {}
    todas = (
        fontes.presidente,
        fontes.deputado_federal,
        fontes.deputado_estadual,
        fontes.referencia,
    )
    for cells in todas:
        for cell in cells or ():
            grupos.setdefault(chave(cell.partido), set()).add(cell.partido)
    return {nome: tuple(sorted(partidos)) for nome, partidos in grupos.items()}


def _at(fonte: _Fonte | None, nivel: str, codigo: str) -> Votos | None:
    return None if fonte is None else fonte.votos(nivel, codigo)


def _soma(lista: Iterable[Votos]) -> Votos:
    total: Votos = {}
    for votos in lista:
        for chave, valor in votos.items():
            total[chave] = total.get(chave, 0) + valor
    return total


def _lideres(por_uf: Mapping[str, Votos]) -> Votos:
    contagem = Counter(primeiro for primeiro in map(lider, por_uf.values()) if primeiro is not None)
    return dict(contagem)


def _validos(votos: Votos | None) -> int | None:
    return None if votos is None else sum(votos.values())


def _positivas(
    lista: tuple[Votos | None, ...],
    municipais: dict[str, Municipal] | None,
) -> set[str]:
    chaves = {chave for votos in lista for chave, valor in (votos or {}).items() if valor > 0}
    if municipais is not None:
        chaves.update(municipais)
    return chaves


def _valor(fonte: _Fonte | None, votos: Votos | None, chave: str) -> int | None:
    if fonte is None or votos is None or chave not in fonte.presentes:
        return None
    return votos.get(chave, 0)


def _municipal_de(
    presentes: frozenset[str] | None,
    municipais: dict[str, Municipal] | None,
    chave: str,
) -> Municipal | None:
    if presentes is None or municipais is None or chave not in presentes:
        return None
    return municipais.get(chave, MUNICIPAL_VAZIO)


def _ordem_unidade(unidade: ForcaUnidade) -> tuple[int, str]:
    return (unidade.partidos[0] if unidade.partidos else 100, unidade.chave)


def _faltando(cargo: str, fontes: FontesForca) -> tuple[str, ...]:
    pares = (
        ("presidente", fontes.presidente),
        ("deputadoFederal", fontes.deputado_federal),
        ("deputadoEstadual", fontes.deputado_estadual),
        (cargo, fontes.referencia),
    )
    faltam = {nome for nome, cells in pares if cells is None}
    return tuple(nome for nome in CARGOS_REFERENCIA if nome in faltam)
```

Nota: no recorte do país, `lideres_estaduais` é `None` só quando a fonte estadual falta. Quando a fonte existe sem nenhuma UF válida, `lideres_estaduais` é `{}` e `ufs_deputado_estadual` é 0, então o partido presente recebe 0 em "UFs em 1º" e "—" no % estadual. Os imports `Counter` e `uf_name` vão para o topo do arquivo, junto dos da Task 1; as linhas com `# junte aos imports` não ficam no meio do módulo.

- [ ] **Step 4: Rodar até passar**

Run: `uv run pytest tests/domain/test_forca.py -q && uv run ruff check src/eleicoes/domain/forca.py tests/domain/test_forca.py && uv run mypy`
Expected: `10 passed`; ruff limpo; mypy `Success`.

- [ ] **Step 5: Sem commit.**

**If Task Fails:**
1. `AM` com presidente 0 em vez de `None`: `_at` precisa devolver `None` quando o lugar falta, e `_valor` tem de respeitar esse `None`.
2. `65` aparece no Acre: `_positivas` só aceita voto > 0; confira se `municipais` não traz chaves zeradas (Task 1, `municipais()` filtra `total > 0`).
3. Não conseguiu se recuperar: registre e pare.

---

### Task 3: Leitura por nível no store

**Files:**
- Modify: `src/eleicoes/ports/relatorio_poder.py` (método novo em `AsyncRelatorioPoderStore`)
- Modify: `src/eleicoes/adapters/postgres_relatorio_poder.py` (função `read_power_levels`)
- Modify: `src/eleicoes/adapters/postgres_relatorio_poder_async.py` (método `load_levels`)
- Modify: `tests/adapters/test_read_api.py` (o fake `_PowerStore` ganha `load_levels`, senão o mypy falha)
- Modify (alinhado em 2026-10-22): **todo** outro fake de `AsyncRelatorioPoderStore` em `tests/`. Como a ordem de integração é 2 → 6 → 1, os planos 2 e 6 podem ter criado fakes próprios (por exemplo, em `tests/adapters/test_municipais_api.py`). Rode `grep -rn "AsyncRelatorioPoderStore\|_PowerStore\|async def load(self, _ano" tests/` e acrescente `load_levels` a cada um.
- Test: `tests/adapters/test_postgres_relatorio_poder.py`

**Interfaces:**
- Produces:
  ```python
  # ports/relatorio_poder.py, dentro de AsyncRelatorioPoderStore
  async def load_levels(self, ano: int, turno: int, cargo: str, niveis: tuple[str, ...]) -> StoredReport | None: ...
  # adapters/postgres_relatorio_poder.py
  def read_power_levels(session: Session, ano: int, turno: int, cargo: str, niveis: tuple[str, ...]) -> StoredReport | None
  ```
- `test_http_errors.py` e `test_relatorios_agrupamentos.py` usam `cast(AsyncRelatorioPoderStore, unused)` e não mudam.

- [ ] **Step 1: Escrever o teste que falha** em `tests/adapters/test_postgres_relatorio_poder.py`:

```python
from eleicoes.adapters.postgres_relatorio_poder import read_power_levels  # junte aos imports
from eleicoes.domain.errors import InvalidNivelError  # junte aos imports


def test_read_power_levels_keeps_only_the_requested_levels() -> None:
    sessions = memory_sessions()
    store = PostgresPowerReportStore(sessions)
    moment = store.save(2026, 1, "deputadoFederal", (_VOTES, _ZERO, _CITY))
    session = sessions()
    with session.begin():
        cidades = read_power_levels(session, 2026, 1, "deputadoFederal", ("municipio",))
        estados = read_power_levels(session, 2026, 1, "deputadoFederal", ("uf", "pais"))
        ausente = read_power_levels(session, 2026, 1, "senador", ("uf",))
    assert cidades == StoredReport((_CITY,), moment)
    assert estados is not None
    assert set(estados.cells) == {_VOTES, _ZERO}
    assert ausente is None
    with pytest.raises(InvalidNivelError):
        read_power_levels(session, 2026, 1, "deputadoFederal", ("estado",))
    with pytest.raises(InvalidNivelError):
        read_power_levels(session, 2026, 1, "deputadoFederal", ())
    store.close()
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `uv run pytest tests/adapters/test_postgres_relatorio_poder.py -q -k levels`
Expected: `ImportError: cannot import name 'read_power_levels'`.

- [ ] **Step 3: Implementar**

Em `postgres_relatorio_poder.py`, logo depois de `read_power`:

```python
from eleicoes.domain.errors import ElectionError, InvalidNivelError  # ajuste o import existente
from eleicoes.domain.grade import GradeLevel  # junte aos imports


def read_power_levels(
    session: Session,
    ano: int,
    turno: int,
    cargo: str,
    niveis: tuple[str, ...],
) -> StoredReport | None:
    if not niveis:
        raise InvalidNivelError(niveis)
    checked = tuple(GradeLevel(nivel).value for nivel in niveis)
    headers = _headers(session, ano, turno, cargo)
    if headers is None:
        return None
    statement = _lines(ano, turno, cargo).where(PowerReportLine.nivel.in_(checked))
    lines = session.execute(statement).scalars().all()
    moment = require_clock(session, headers.gerado_em, _BROKEN)
    return StoredReport(tuple(_cell(line) for line in lines), moment)
```

Em `ports/relatorio_poder.py`, acrescente ao `AsyncRelatorioPoderStore`:

```python
    async def load_levels(
        self,
        ano: int,
        turno: int,
        cargo: str,
        niveis: tuple[str, ...],
    ) -> StoredReport | None: ...
```

Em `postgres_relatorio_poder_async.py`, importe `read_power_levels` e acrescente:

```python
    async def load_levels(
        self,
        ano: int,
        turno: int,
        cargo: str,
        niveis: tuple[str, ...],
    ) -> StoredReport | None:
        def work(sync: Session) -> StoredReport | None:
            return read_power_levels(sync, ano, turno, cargo, niveis)

        return await self._run(work)
```

Em `tests/adapters/test_read_api.py`, no `_PowerStore.__init__`, acrescente `self.by_cargo: dict[str, StoredReport | None] = {}` e `self.level_calls: list[tuple[str, tuple[str, ...]]] = []`, e depois o método:

```python
    async def load_levels(
        self,
        _ano: int,
        _turno: int,
        cargo: str,
        niveis: tuple[str, ...],
    ) -> StoredReport | None:
        self.level_calls.append((cargo, niveis))
        found = self.by_cargo[cargo] if cargo in self.by_cargo else self.stored
        if found is None:
            return None
        kept = tuple(cell for cell in found.cells if cell.nivel in niveis)
        return StoredReport(kept, found.gerado_em)
```

- [ ] **Step 4: Rodar até passar**

Run: `uv run pytest tests/adapters/test_postgres_relatorio_poder.py tests/adapters/test_read_api.py -q && uv run ruff check . && uv run mypy`
Expected: todos passam; ruff e mypy limpos.

- [ ] **Step 5: Sem commit.**

**If Task Fails:**
1. Erro do mypy "Argument power_store has incompatible type": falta `load_levels` em algum fake. Rode `grep -rn "power_store=" tests` e confira cada um.
2. O SQLite não aplica `IN` em tupla vazia: o `raise` vem antes da consulta.
3. Não conseguiu se recuperar: registre e pare.

---

### Task 4: Caso de uso e erro 409

**Files:**
- Modify: `src/eleicoes/domain/errors.py` (função `comando_relatorio_poder`, `MissingPowerReportError` passa a usá-la, e a classe nova `MissingStrengthSourcesError`)
- Modify: `src/eleicoes/adapters/http/errors.py` (importar a classe nova e mapear `(MissingStrengthSourcesError, 409)` junto de `MissingPowerReportError`)
- Create: `src/eleicoes/use_cases/placar_forca.py`
- Test: `tests/use_cases/test_placar_forca.py`

**Interfaces:**
- Consumes: `AsyncRelatorioPoderStore.load_levels` (Task 3), `placar_forca`, `FontesForca` e `require_cargo_referencia` (Tasks 1 e 2), e `ElectionYear` e `Turno` de `eleicoes.domain.values`.
- Produces:
  ```python
  def comando_relatorio_poder(cargo: str) -> str  # errors.py
  class MissingStrengthSourcesError(ElectionError): cargos: tuple[str, ...]
  class MontarPlacarForca:
      def __init__(self, store: AsyncRelatorioPoderStore) -> None
      async def execute(self, ano: int, turno: int, cargo_referencia: str) -> PlacarForca
  ```

Plano de leitura (sempre nesta ordem; níveis em ordem fixa):
- `presidente`: `("pais", "uf")`, mais `"municipio"` quando é a referência.
- `deputadoFederal`: `("pais", "uf")`, mais `"municipio"` quando é a referência.
- `deputadoEstadual`: `("uf",)`, mais `"municipio"` quando é a referência.
- `governador` ou `senador`, quando é a referência: `("municipio",)`.
- Um relatório `None`, ou com `cells == ()`, vira fonte `None`.

- [ ] **Step 1: Escrever os testes que falham**

```python
"""Strength scoreboard use case. An in-memory store stands in for Postgres."""

import asyncio
from datetime import UTC, datetime

import pytest

from eleicoes.domain.errors import (
    InvalidCargoError,
    InvalidElectionYearError,
    MissingStrengthSourcesError,
)
from eleicoes.domain.stored_grade import StoredCell
from eleicoes.ports.relatorio_poder import StoredReport
from eleicoes.use_cases.placar_forca import MontarPlacarForca

_MOMENT = datetime(2026, 10, 22, tzinfo=UTC)
_UF = StoredCell("uf", "AC", "Acre", 100, 22, 30, 0)
_PAIS = StoredCell("pais", "BR", "Brasil", 100, 22, 30, 0)
_CITY = StoredCell("municipio", "1", "RIO BRANCO (AC)", 100, 22, 30, 0)


class _Store:
    def __init__(self, stored: dict[str, StoredReport | None]) -> None:
        self.stored = stored
        self.calls: list[tuple[str, tuple[str, ...]]] = []

    async def load(self, _ano: int, _turno: int, _cargo: str) -> StoredReport | None:
        raise AssertionError("the scoreboard reads levels only")

    async def save(
        self,
        _ano: int,
        _turno: int,
        _cargo: str,
        _cells: tuple[StoredCell, ...],
    ) -> datetime:
        raise AssertionError("the scoreboard never writes")

    async def load_levels(
        self,
        _ano: int,
        _turno: int,
        cargo: str,
        niveis: tuple[str, ...],
    ) -> StoredReport | None:
        self.calls.append((cargo, niveis))
        found = self.stored.get(cargo)
        if found is None:
            return None
        kept = tuple(cell for cell in found.cells if cell.nivel in niveis)
        return StoredReport(kept, found.gerado_em)


_CARGOS = ("presidente", "governador", "senador", "deputadoFederal", "deputadoEstadual")


def _all() -> dict[str, StoredReport | None]:
    cells = (_UF, _PAIS, _CITY)
    return {cargo: StoredReport(cells, _MOMENT) for cargo in _CARGOS}


def test_default_reference_reads_one_municipal_level() -> None:
    store = _Store(_all())
    placar = asyncio.run(MontarPlacarForca(store).execute(2026, 1, "deputadoEstadual"))
    assert store.calls == [
        ("presidente", ("pais", "uf")),
        ("deputadoFederal", ("pais", "uf")),
        ("deputadoEstadual", ("uf", "municipio")),
    ]
    assert placar.faltando == ()
    assert placar.pais.base.municipal is not None


def test_governor_reference_adds_a_fourth_read() -> None:
    store = _Store(_all())
    asyncio.run(MontarPlacarForca(store).execute(2026, 1, "governador"))
    assert store.calls[-1] == ("governador", ("municipio",))
    assert len(store.calls) == 4


def test_president_reference_reads_its_cities_in_the_same_call() -> None:
    store = _Store(_all())
    asyncio.run(MontarPlacarForca(store).execute(2026, 1, "presidente"))
    assert store.calls[0] == ("presidente", ("pais", "uf", "municipio"))
    assert len(store.calls) == 3


def test_empty_or_absent_reports_degrade_per_office() -> None:
    stored = _all()
    stored["presidente"] = None
    stored["deputadoFederal"] = StoredReport((), _MOMENT)
    placar = asyncio.run(MontarPlacarForca(_Store(stored)).execute(2026, 1, "deputadoEstadual"))
    assert placar.faltando == ("presidente", "deputadoFederal")


def test_nothing_stored_is_a_conflict_with_every_command() -> None:
    with pytest.raises(MissingStrengthSourcesError) as caught:
        asyncio.run(MontarPlacarForca(_Store({})).execute(2026, 1, "deputadoEstadual"))
    assert caught.value.cargos == ("presidente", "deputadoFederal", "deputadoEstadual")
    assert "--cargo deputadoFederal --sem-navegador" in str(caught.value)


def test_bad_input_fails_before_any_read() -> None:
    store = _Store(_all())
    with pytest.raises(InvalidCargoError):
        asyncio.run(MontarPlacarForca(store).execute(2026, 1, "deputadoDistrital"))
    with pytest.raises(InvalidElectionYearError):
        asyncio.run(MontarPlacarForca(store).execute(1900, 1, "deputadoEstadual"))
    assert store.calls == []
```

(`InvalidElectionYearError` está em `src/eleicoes/domain/errors.py:8`.)

- [ ] **Step 2: Rodar e ver falhar**

Run: `uv run pytest tests/use_cases/test_placar_forca.py -q`
Expected: `ImportError: cannot import name 'MissingStrengthSourcesError'`.

- [ ] **Step 3: Implementar**

Em `domain/errors.py`, antes de `MissingPowerReportError`:

```python
def comando_relatorio_poder(cargo: str) -> str:
    return f"uv run python scripts/relatorio_poder.py --cargo {cargo} --sem-navegador"
```

Troque o corpo de `MissingPowerReportError` para usar a função (o texto continua idêntico, e o teste `_MISSING_POWER` de `test_read_api.py` protege isso):

```python
class MissingPowerReportError(ElectionError):
    def __init__(self, cargo: str) -> None:
        self.cargo = cargo
        super().__init__(
            f"O relatório de poder de {cargo} ainda não foi gravado. "
            f"Gere com: {comando_relatorio_poder(cargo)}"
        )


class MissingStrengthSourcesError(ElectionError):
    def __init__(self, cargos: tuple[str, ...]) -> None:
        self.cargos = cargos
        comandos = "; ".join(comando_relatorio_poder(cargo) for cargo in cargos)
        super().__init__(
            "Nenhum relatório de poder usado pelo placar de força foi gravado. "
            f"Gere com: {comandos}"
        )
```

`src/eleicoes/use_cases/placar_forca.py`:

```python
"""Strength scoreboard from the stored power cells. Reads only the levels it needs."""

from eleicoes.domain.errors import MissingStrengthSourcesError
from eleicoes.domain.forca import FontesForca, PlacarForca, placar_forca, require_cargo_referencia
from eleicoes.domain.stored_grade import StoredCell
from eleicoes.domain.values import ElectionYear, Turno
from eleicoes.ports.relatorio_poder import AsyncRelatorioPoderStore

_BASE: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("presidente", ("pais", "uf")),
    ("deputadoFederal", ("pais", "uf")),
    ("deputadoEstadual", ("uf",)),
)
_MUNICIPIO = "municipio"
Cells = tuple[StoredCell, ...] | None


class MontarPlacarForca:
    def __init__(self, store: AsyncRelatorioPoderStore) -> None:
        self._store = store

    async def execute(self, ano: int, turno: int, cargo_referencia: str) -> PlacarForca:
        year = ElectionYear(ano).value
        turn = Turno(turno).value
        referencia = require_cargo_referencia(cargo_referencia)
        loaded: dict[str, Cells] = {}
        for cargo, niveis in _plano(referencia):
            loaded[cargo] = await self._cells(year, turn, cargo, niveis)
        if all(cells is None for cells in loaded.values()):
            raise MissingStrengthSourcesError(tuple(loaded))
        fontes = FontesForca(
            loaded["presidente"],
            loaded["deputadoFederal"],
            loaded["deputadoEstadual"],
            loaded[referencia],
        )
        return placar_forca(year, turn, referencia, fontes)

    async def _cells(self, ano: int, turno: int, cargo: str, niveis: tuple[str, ...]) -> Cells:
        report = await self._store.load_levels(ano, turno, cargo, niveis)
        if report is None or not report.cells:
            return None
        return report.cells


def _plano(referencia: str) -> tuple[tuple[str, tuple[str, ...]], ...]:
    plano = tuple((cargo, _niveis(cargo, niveis, referencia)) for cargo, niveis in _BASE)
    if any(cargo == referencia for cargo, _base in _BASE):
        return plano
    return (*plano, (referencia, (_MUNICIPIO,)))


def _niveis(cargo: str, niveis: tuple[str, ...], referencia: str) -> tuple[str, ...]:
    return (*niveis, _MUNICIPIO) if cargo == referencia else niveis
```

Em `adapters/http/errors.py`, importe `MissingStrengthSourcesError` e acrescente `(MissingStrengthSourcesError, 409),` logo depois de `(MissingPowerReportError, 409),`.

- [ ] **Step 4: Rodar até passar**

Run: `uv run pytest tests/use_cases/test_placar_forca.py tests/adapters/test_read_api.py tests/adapters/test_http_errors.py -q && uv run ruff check . && uv run mypy`
Expected: todos passam; ruff e mypy limpos.

- [ ] **Step 5: Sem commit.**

**If Task Fails:**
1. O teste `_MISSING_POWER` quebrou: o texto de `MissingPowerReportError` mudou. Compare com `tests/adapters/test_read_api.py:500`.
2. Não conseguiu se recuperar: registre e pare.

---

### Task 5: Rota HTTP e esquema JSON

**Files:**
- Modify: `src/eleicoes/adapters/http/schemas_relatorios.py` (classes `*ForcaJson` no fim)
- Modify: `src/eleicoes/adapters/http/relatorios.py` (rota nova)
- Test: `tests/adapters/test_read_api.py`

**Interfaces:**
- Produces, em `GET /relatorios/dados/forca?ano=2026&turno=1&cargo_referencia=deputadoEstadual`:
  ```json
  {
    "ano": 2026, "turno": 1, "cargo_referencia": "deputadoEstadual", "limiares": [1, 2, 5, 10, 20],
    "faltando": [{"cargo": "senador", "comando": "uv run python scripts/relatorio_poder.py --cargo senador --sem-navegador"}],
    "pais": {
      "codigo": "BR", "nome": "Brasil",
      "base": {"validos_presidente": 119299501, "validos_deputado_federal": 114107982,
               "validos_deputado_estadual": 111662018, "ufs_deputado_estadual": 26,
               "municipal": {"municipios": 5570, "validos": 111662018, "empates": 3}},
      "unidades": [{"chave": "22", "tipo": "partido", "nome": null, "partidos": [22],
                    "presidente": 56103951, "deputado_federal": 25830455, "deputado_estadual": 22522574,
                    "ufs_lider_estadual": 11,
                    "municipal": {"lidera": 1323, "validos_liderados": 46243740,
                                  "presenca": [{"limiar": 5, "municipios": 4477}]}}]
    },
    "ufs": [{"codigo": "AC", "nome": "Acre", "base": {}, "unidades": []}]
  }
  ```
  (Os números do PL 22 são os reais de 2026-10-22. No JSON de verdade, `presenca` sempre traz os 5 limiares; o exemplo mostra só o de 5%, e `ufs` foi cortado.)

- [ ] **Step 1: Escrever os testes que falham** em `tests/adapters/test_read_api.py`. Acrescente `"/relatorios/dados/forca"` ao conjunto `expected` de `test_health_and_openapi_advertise_the_read_routes` e inclua:

```python
_FORCA = "/relatorios/dados/forca?ano=2026&turno=1"


def _forca_power() -> _PowerStore:
    power = _PowerStore()
    moment = datetime(2026, 10, 22, tzinfo=UTC)
    power.by_cargo = {
        "presidente": StoredReport(
            (
                StoredCell("pais", "BR", "Brasil", 100, 22, 60, 0),
                StoredCell("uf", "AC", "Acre", 100, 22, 60, 0),
            ),
            moment,
        ),
        "deputadoFederal": None,
        "deputadoEstadual": StoredReport(
            (
                StoredCell("uf", "AC", "Acre", 100, 22, 30, 5),
                StoredCell("municipio", "1", "RIO BRANCO (AC)", 100, 22, 30, 5),
            ),
            moment,
        ),
    }
    return power


def test_forca_returns_integer_counts_and_lists_missing_offices() -> None:
    power = _forca_power()
    application = create_app(ports=_ports(power=power))
    response = _get(application, _FORCA)
    assert response.status_code == 200
    body = response.json()
    assert body["cargo_referencia"] == "deputadoEstadual"
    assert body["limiares"] == [1, 2, 5, 10, 20]
    assert body["faltando"] == [{
        "cargo": "deputadoFederal",
        "comando": "uv run python scripts/relatorio_poder.py --cargo deputadoFederal --sem-navegador",
    }]
    unidade = body["pais"]["unidades"][0]
    assert unidade["chave"] == "22"
    assert unidade["tipo"] == "partido"
    assert unidade["presidente"] == 60
    assert unidade["deputado_federal"] is None
    assert unidade["deputado_estadual"] == 35
    assert unidade["ufs_lider_estadual"] == 1
    assert unidade["municipal"]["lidera"] == 1
    assert [p["limiar"] for p in unidade["municipal"]["presenca"]] == [1, 2, 5, 10, 20]
    assert body["ufs"][0]["codigo"] == "AC"
    assert power.saves == []


def test_forca_without_any_stored_office_is_409() -> None:
    power = _PowerStore()
    power.stored = None
    response = _get(create_app(ports=_ports(power=power)), _FORCA)
    assert response.status_code == 409
    assert "placar de força" in response.json()["detail"]


def test_forca_rejects_an_unknown_reference_office() -> None:
    response = _get(create_app(ports=_ports()), f"{_FORCA}&cargo_referencia=deputadoDistrital")
    assert response.status_code == 422
    assert response.json()["detail"] == "Cargo inválido."
```

(Antes de fixar a última asserção, confira como `invalid cargo` vira detalhe: `uv run pytest tests/adapters/test_http_errors.py -q -k cargo`, e veja `adapters/http/errors.py:39`.)

- [ ] **Step 2: Rodar e ver falhar**

Run: `uv run pytest tests/adapters/test_read_api.py -q -k forca`
Expected: `404` em vez de `200` (`assert 404 == 200`).

- [ ] **Step 3: Implementar.** No fim de `schemas_relatorios.py`:

```python
from eleicoes.domain.errors import comando_relatorio_poder  # junte aos imports
from eleicoes.domain.forca import (  # junte aos imports
    BaseMunicipal,
    BaseRecorte,
    ForcaUnidade,
    Municipal,
    PlacarForca,
    Recorte,
)


class PresencaJson(BaseModel):
    limiar: int
    municipios: int


class MunicipalForcaJson(BaseModel):
    lidera: int
    validos_liderados: int
    presenca: list[PresencaJson]

    @classmethod
    def from_domain(cls, item: Municipal) -> Self:
        presenca = [PresencaJson(limiar=p.limiar, municipios=p.municipios) for p in item.presenca]
        return cls(
            lidera=item.lidera,
            validos_liderados=item.validos_liderados,
            presenca=presenca,
        )


class BaseMunicipalJson(BaseModel):
    municipios: int
    validos: int
    empates: int

    @classmethod
    def from_domain(cls, base: BaseMunicipal) -> Self:
        return cls(municipios=base.municipios, validos=base.validos, empates=base.empates)


class BaseForcaJson(BaseModel):
    validos_presidente: int | None
    validos_deputado_federal: int | None
    validos_deputado_estadual: int | None
    ufs_deputado_estadual: int | None
    municipal: BaseMunicipalJson | None

    @classmethod
    def from_domain(cls, base: BaseRecorte) -> Self:
        found = base.municipal
        municipal = None if found is None else BaseMunicipalJson.from_domain(found)
        return cls(
            validos_presidente=base.validos_presidente,
            validos_deputado_federal=base.validos_deputado_federal,
            validos_deputado_estadual=base.validos_deputado_estadual,
            ufs_deputado_estadual=base.ufs_deputado_estadual,
            municipal=municipal,
        )


class UnidadeForcaJson(BaseModel):
    chave: str
    tipo: str
    nome: str | None
    partidos: list[int]
    presidente: int | None
    deputado_federal: int | None
    deputado_estadual: int | None
    ufs_lider_estadual: int | None
    municipal: MunicipalForcaJson | None

    @classmethod
    def from_domain(cls, item: ForcaUnidade) -> Self:
        found = item.municipal
        municipal = None if found is None else MunicipalForcaJson.from_domain(found)
        return cls(
            chave=item.chave,
            tipo="partido",
            nome=None,
            partidos=list(item.partidos),
            presidente=item.presidente,
            deputado_federal=item.deputado_federal,
            deputado_estadual=item.deputado_estadual,
            ufs_lider_estadual=item.ufs_lider_estadual,
            municipal=municipal,
        )


class RecorteForcaJson(BaseModel):
    codigo: str
    nome: str
    base: BaseForcaJson
    unidades: list[UnidadeForcaJson]

    @classmethod
    def from_domain(cls, recorte: Recorte) -> Self:
        return cls(
            codigo=recorte.codigo,
            nome=recorte.nome,
            base=BaseForcaJson.from_domain(recorte.base),
            unidades=[UnidadeForcaJson.from_domain(item) for item in recorte.unidades],
        )


class FaltandoJson(BaseModel):
    cargo: str
    comando: str


class ForcaJson(BaseModel):
    ano: int
    turno: int
    cargo_referencia: str
    limiares: list[int]
    faltando: list[FaltandoJson]
    pais: RecorteForcaJson
    ufs: list[RecorteForcaJson]

    @classmethod
    def from_domain(cls, placar: PlacarForca) -> Self:
        faltando = [
            FaltandoJson(cargo=cargo, comando=comando_relatorio_poder(cargo))
            for cargo in placar.faltando
        ]
        return cls(
            ano=placar.ano,
            turno=placar.turno,
            cargo_referencia=placar.cargo_referencia,
            limiares=list(placar.limiares),
            faltando=faltando,
            pais=RecorteForcaJson.from_domain(placar.pais),
            ufs=[RecorteForcaJson.from_domain(item) for item in placar.ufs],
        )
```

Em `relatorios.py`, importe `ForcaJson` e `MontarPlacarForca` e acrescente, depois da rota `classe_governador`:

```python
_FORCA = (
    "Exige ano e turno. cargo_referencia escolhe o cargo dos indicadores municipais "
    "(padrão deputadoEstadual). Lê só as células gravadas do relatório de poder. "
    "Cargos sem gravação voltam em faltando, com o comando para gerar; "
    "sem nenhum cargo gravado, responde 409."
)


@router.get("/relatorios/dados/forca", summary="Placar de força partidária", description=_FORCA)
async def forca(
    ano: int,
    turno: int,
    store: PowerStore,
    cargo_referencia: str = "deputadoEstadual",
) -> ForcaJson:
    placar = await MontarPlacarForca(store).execute(ano, turno, cargo_referencia)
    return ForcaJson.from_domain(placar)
```

- [ ] **Step 4: Rodar até passar**

Run: `uv run pytest -q && uv run ruff check . && uv run mypy`
Expected: a suíte inteira passa; ruff e mypy limpos.

- [ ] **Step 5: Sem commit.**

**If Task Fails:**
1. Import circular entre `schemas_relatorios` e `domain.forca`: o domínio não importa adaptadores; confira os imports.
2. 500 em vez de 409: falta o mapeamento em `adapters/http/errors.py` (Task 4).
3. Não conseguiu se recuperar: registre e pare.

---

### Task 6: Code Review

1. **REQUIRED SUB-SKILL:** Use jarvis:codereview e dispare todos os revisores em paralelo sobre o diff das Tasks 1 a 5.
2. **Handle findings by severity:** siga as regras de severidade de jarvis:codereview.
3. **Proceed only when:** não restar nenhum achado Critical, High ou Medium.

---

### Task 7: Tipos, leitura do JSON e busca no frontend

**Files:**
- Create: `frontend/src/lib/forca.ts`
- Modify: `frontend/src/lib/buscar-relatorios.ts` (função `buscarForca`)
- Test: `frontend/src/lib/verificar-forca.ts`

**Interfaces:**
- Produces:
  ```ts
  export const LIMIAR_PADRAO = 5;
  export type Presenca = { limiar: number; municipios: number };
  export type MunicipalForca = { lidera: number; validos_liderados: number; presenca: Presenca[] };
  export type BaseMunicipalForca = { municipios: number; validos: number; empates: number };
  export type BaseForca = {
    validos_presidente: number | null; validos_deputado_federal: number | null;
    validos_deputado_estadual: number | null; ufs_deputado_estadual: number | null;
    municipal: BaseMunicipalForca | null;
  };
  export type UnidadeForca = {
    chave: string; tipo: "partido" | "federacao"; nome: string | null; partidos: number[];
    presidente: number | null; deputado_federal: number | null; deputado_estadual: number | null;
    ufs_lider_estadual: number | null; municipal: MunicipalForca | null;
  };
  export type RecorteForca = { codigo: string; nome: string; base: BaseForca; unidades: UnidadeForca[] };
  export type FaltandoForca = { cargo: string; comando: string };
  export type PlacarForca = {
    ano: number; turno: number; cargo_referencia: string; limiares: number[];
    faltando: FaltandoForca[]; pais: RecorteForca; ufs: RecorteForca[];
  };
  export class RespostaForcaInvalidaError extends Error {}
  export function lerPlacarForca(valor: unknown): PlacarForca;
  // buscar-relatorios.ts
  export function buscarForca(ano: string, turno: string, cargo: string): Promise<Resultado<PlacarForca>>;
  ```

Regras:
- Inteiro ou nulo: `null` e `undefined` viram `null`, e um campo ausente também. Essa folga deixa as fases B e C acrescentarem campos sem quebrar a leitura. Qualquer outro valor que não seja inteiro seguro lança `RespostaForcaInvalidaError`.
- `tipo` fora de `"partido"` ou `"federacao"` lança erro.
- `buscarForca` chama `/relatorios/dados/forca` com `{ ano, turno, cargo_referencia: cargo }`, reusando `buscar(...)`. Em `mensagemDeErro`, trate `RespostaForcaInvalidaError` como `RespostaInvalidaError`, para mostrar a mensagem dele.

- [ ] **Step 1: Escrever o script que falha** (`verificar-forca.ts`):

```ts
import assert from "node:assert/strict";
import { lerPlacarForca, RespostaForcaInvalidaError } from "./forca.ts";

const municipal = { lidera: 1, validos_liderados: 100, presenca: [{ limiar: 5, municipios: 3 }] };
const unidade = {
  chave: "22", tipo: "partido", nome: null, partidos: [22], presidente: 40, deputado_federal: null,
  deputado_estadual: 50, ufs_lider_estadual: 1, municipal,
};
const recorte = {
  codigo: "BR", nome: "Brasil", unidades: [unidade],
  base: { validos_presidente: 100, validos_deputado_federal: null, validos_deputado_estadual: 80,
    ufs_deputado_estadual: 2, municipal: { municipios: 3, validos: 300, empates: 1 } },
};
const json = { ano: 2026, turno: 1, cargo_referencia: "deputadoEstadual", limiares: [1, 2, 5, 10, 20],
  faltando: [{ cargo: "deputadoFederal", comando: "uv run x" }], pais: recorte, ufs: [] };

const lido = lerPlacarForca(json);
assert.equal(lido.pais.unidades[0].deputado_federal, null);
assert.equal(lido.pais.unidades[0].municipal?.presenca[0].municipios, 3);
assert.equal(lido.faltando[0].cargo, "deputadoFederal");

// campo ausente vira null (fases B e C acrescentam campos)
const semCampo = structuredClone(json);
delete (semCampo.pais.unidades[0] as Record<string, unknown>).ufs_lider_estadual;
assert.equal(lerPlacarForca(semCampo).pais.unidades[0].ufs_lider_estadual, null);

// entradas ruins
assert.throws(() => lerPlacarForca({ ...json, ano: "2026" }), RespostaForcaInvalidaError);
assert.throws(() => lerPlacarForca({ ...json, pais: { ...recorte, unidades: [{ ...unidade, tipo: "bloco" }] } }),
  RespostaForcaInvalidaError);
assert.throws(() => lerPlacarForca({ ...json, pais: { ...recorte, unidades: [{ ...unidade, presidente: 1.5 }] } }),
  RespostaForcaInvalidaError);
console.log("ok");
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd frontend && node --experimental-strip-types src/lib/verificar-forca.ts`
Expected: `ERR_MODULE_NOT_FOUND` para `forca.ts`.

- [ ] **Step 3: Implementar `forca.ts`** com os tipos acima e funções `exigirRegistro`, `exigirLista`, `exigirInteiro`, `exigirInteiroOuNulo`, `exigirTexto` e `exigirTextoOuNulo` locais, no mesmo padrão de `relatorios.ts:347-391`, lançando `RespostaForcaInvalidaError` com a mensagem `"A API devolveu um JSON que não confere com o placar de força."`. Depois, `buscarForca` em `buscar-relatorios.ts`.

- [ ] **Step 4: Rodar até passar**

Run: `cd frontend && node --experimental-strip-types src/lib/verificar-forca.ts && pnpm exec tsc --noEmit && pnpm exec eslint src/lib/forca.ts src/lib/verificar-forca.ts src/lib/buscar-relatorios.ts`
Expected: `ok`; tsc e eslint sem saída.

- [ ] **Step 5: Sem commit.**

**If Task Fails:**
1. O Node acusa `@/lib/...`: `forca.ts` não pode importar com alias.
2. Não conseguiu se recuperar: registre e pare.

---

### Task 8: Linhas, colunas e ordenação (módulo puro)

**Files:**
- Create: `frontend/src/lib/placar-forca.ts`
- Test: `frontend/src/lib/verificar-placar-forca.ts`

**Interfaces:**
- Consumes: os tipos de `./forca.ts`, `formatarInteiro`, `formatarPercentualContagem` e `TRACO` de `./fracao.ts`, `rotuloPartido` de `./partidos.ts`, e `compararNumero`, `compararTexto` e `type Direcao` de `./ordem.ts`.
- Produces:
  ```ts
  export type Esfera = "federacao" | "estados" | "municipios";
  export const ROTULOS_ESFERA: Record<Esfera, string>; // "Federação", "Estados", "Municípios"
  export type ChaveColuna = "presidente" | "deputado_federal" | "deputado_estadual" | "ufs_lider_estadual"
    | "municipios_lidera" | "eleitorado_liderado" | "presenca";
  export type Coluna = { chave: ChaveColuna; esfera: Esfera; titulo: string; curto: string; explicacao: string };
  export type Valor = { ordem: number | null; fracao: number | null; texto: string; detalhe: string };
  export type LinhaPlacar = { chave: string; rotulo: string; partidos: number[]; valores: Record<ChaveColuna, Valor> };
  export type NivelPlacar = "pais" | "uf";
  export const COLUNA_PADRAO: ChaveColuna = "deputado_federal";
  export function colunasPlacar(limiar: number, nivel: NivelPlacar): Coluna[];
  export function linhasPlacar(recorte: RecorteForca, limiar: number, nivel: NivelPlacar): LinhaPlacar[];
  export function linhasPorUf(placar: PlacarForca, chave: string, limiar: number): LinhaPlacar[];
  export function ordenarPlacar(linhas: readonly LinhaPlacar[], coluna: ChaveColuna | "unidade", direcao: Direcao): LinhaPlacar[];
  ```

Regras (os textos são exatos):

| Coluna | Esfera | `titulo` / `curto` | `texto` | `ordem` e `fracao` | `detalhe` |
|---|---|---|---|---|---|
| presidente | federacao | "Presidente (% válidos)" / "Presidente" | `formatarPercentualContagem(v, base.validos_presidente)` | v / base | `"{n} votos"` |
| deputado_federal | federacao | "Deputado federal (% válidos)" / "Dep. federal" | idem com `validos_deputado_federal` | v / base | idem |
| deputado_estadual | estados | "Deputado estadual (% válidos)" / "Dep. estadual" | idem com `validos_deputado_estadual` | v / base | idem |
| ufs_lider_estadual | estados | país: "UFs em 1º (dep. estadual)" / "UFs em 1º"; UF: "1º em dep. estadual" / "1º na UF" | país: `"{n} de {N}"`; UF: "Sim" ou "Não" | n e n/N | país: `"{n} de {N} UFs com deputado estadual"`; UF: `""` |
| municipios_lidera | municipios | "Municípios em 1º" / "Municípios em 1º" | `formatarInteiro(n)` | n e n/N | `"de {N} municípios"` |
| eleitorado_liderado | municipios | "Eleitorado dos municípios em 1º" / "Eleitorado em 1º" | `formatarPercentualContagem(validos_liderados, base.municipal.validos)` | fração | `"{validos_liderados} votos válidos"` |
| presenca | municipios | `"Presença (≥ {limiar}%)"` / `"Presença ≥ {limiar}%"` | `formatarInteiro(n do limiar)` | n e n/N | `"de {N} municípios com ao menos {limiar}% dos válidos"` |

- Valor nulo, ou base nula ou 0, vira `{ ordem: null, fracao: null, texto: TRACO, detalhe: "Sem dados" }`.
- `rotulo`: `rotuloPartido(partidos[0])` para `tipo === "partido"`, e `nome ?? chave` para federação.
- `linhasPorUf`: uma linha por recorte de `placar.ufs`, com `chave = recorte.codigo`, `rotulo = recorte.nome` e nível `"uf"`. Se a unidade não existir naquela UF, todos os valores ficam `TRACO`.
- `ordenarPlacar`: compara com `compararNumero(a.valores[c].ordem, b.valores[c].ordem, direcao)`, que deixa nulos por último; o empate vai para o menor `partidos[0]`. `"unidade"` usa `compararTexto(rotulo)`.
- Cada `explicacao` é uma frase em português simples, repetida em `explicacao-forca.tsx` (Task 11). Exemplo para `presenca`: `"Quantos municípios deram ao partido pelo menos o limiar escolhido dos votos válidos do cargo de referência."`

- [ ] **Step 1: Escrever o script que falha.** O fixture é a saída do domínio Python da Task 2 (`placar_forca(2026, 1, "deputadoEstadual", FontesForca(PRES, FED, EST, EST))`) no formato de `ForcaJson`. Ele foi gerado a partir do código deste plano; cole-o no script como `const PLACAR = lerPlacarForca(JSON.parse(String.raw`…`));`, importando `lerPlacarForca` de `./forca.ts`:

```json
{"ano":2026,"turno":1,"cargo_referencia":"deputadoEstadual","limiares":[1,2,5,10,20],"faltando":[],"pais":{"codigo":"BR","nome":"Brasil","base":{"validos_presidente":100,"validos_deputado_federal":100,"validos_deputado_estadual":80,"ufs_deputado_estadual":2,"municipal":{"municipios":3,"validos":300,"empates":1}},"unidades":[{"chave":"13","tipo":"partido","nome":null,"partidos":[13],"presidente":60,"deputado_federal":30,"deputado_estadual":30,"ufs_lider_estadual":0,"municipal":{"lidera":1,"validos_liderados":100,"presenca":[{"limiar":1,"municipios":3},{"limiar":2,"municipios":3},{"limiar":5,"municipios":3},{"limiar":10,"municipios":2},{"limiar":20,"municipios":2}]}},{"chave":"22","tipo":"partido","nome":null,"partidos":[22],"presidente":40,"deputado_federal":50,"deputado_estadual":50,"ufs_lider_estadual":1,"municipal":{"lidera":1,"validos_liderados":100,"presenca":[{"limiar":1,"municipios":3},{"limiar":2,"municipios":3},{"limiar":5,"municipios":3},{"limiar":10,"municipios":3},{"limiar":20,"municipios":3}]}},{"chave":"65","tipo":"partido","nome":null,"partidos":[65],"presidente":null,"deputado_federal":20,"deputado_estadual":0,"ufs_lider_estadual":0,"municipal":{"lidera":0,"validos_liderados":0,"presenca":[{"limiar":1,"municipios":0},{"limiar":2,"municipios":0},{"limiar":5,"municipios":0},{"limiar":10,"municipios":0},{"limiar":20,"municipios":0}]}}]},"ufs":[{"codigo":"AC","nome":"Acre","base":{"validos_presidente":30,"validos_deputado_federal":10,"validos_deputado_estadual":40,"ufs_deputado_estadual":1,"municipal":{"municipios":2,"validos":200,"empates":0}},"unidades":[{"chave":"13","tipo":"partido","nome":null,"partidos":[13],"presidente":10,"deputado_federal":5,"deputado_estadual":10,"ufs_lider_estadual":0,"municipal":{"lidera":1,"validos_liderados":100,"presenca":[{"limiar":1,"municipios":2},{"limiar":2,"municipios":2},{"limiar":5,"municipios":2},{"limiar":10,"municipios":1},{"limiar":20,"municipios":1}]}},{"chave":"22","tipo":"partido","nome":null,"partidos":[22],"presidente":20,"deputado_federal":5,"deputado_estadual":30,"ufs_lider_estadual":1,"municipal":{"lidera":1,"validos_liderados":100,"presenca":[{"limiar":1,"municipios":2},{"limiar":2,"municipios":2},{"limiar":5,"municipios":2},{"limiar":10,"municipios":2},{"limiar":20,"municipios":2}]}}]},{"codigo":"AM","nome":"Amazonas","base":{"validos_presidente":null,"validos_deputado_federal":10,"validos_deputado_estadual":40,"ufs_deputado_estadual":1,"municipal":{"municipios":1,"validos":100,"empates":1}},"unidades":[{"chave":"13","tipo":"partido","nome":null,"partidos":[13],"presidente":null,"deputado_federal":7,"deputado_estadual":20,"ufs_lider_estadual":0,"municipal":{"lidera":0,"validos_liderados":0,"presenca":[{"limiar":1,"municipios":1},{"limiar":2,"municipios":1},{"limiar":5,"municipios":1},{"limiar":10,"municipios":1},{"limiar":20,"municipios":1}]}},{"chave":"22","tipo":"partido","nome":null,"partidos":[22],"presidente":null,"deputado_federal":3,"deputado_estadual":20,"ufs_lider_estadual":0,"municipal":{"lidera":0,"validos_liderados":0,"presenca":[{"limiar":1,"municipios":1},{"limiar":2,"municipios":1},{"limiar":5,"municipios":1},{"limiar":10,"municipios":1},{"limiar":20,"municipios":1}]}}]}]}
```

  Confira:
  - `linhasPlacar(pais, 5, "pais")`: PL 22 tem presidente `"40,00%"`; PCdoB 65 tem presidente `"—"`, com `ordem === null`; `ufs_lider_estadual` de 22 é `"1 de 2"`; `municipios_lidera` de 13 é `"1"`, com detalhe `"de 3 municípios"`; `eleitorado_liderado` de 13 é `"33,33%"`.
  - `presenca` de 13 com limiar 5 é `"3"`, e com limiar 10 é `"2"`; o título com limiar 10 é `"Presença (≥ 10%)"`.
  - Recorte AC com nível `"uf"`: `ufs_lider_estadual` de 22 é `"Sim"`, e de 13 é `"Não"`.
  - `ordenarPlacar(linhas, "deputado_federal", "desc")` dá a ordem das chaves `["22", "13", "65"]`.
  - `ordenarPlacar(linhas, "presidente", "asc")` e `"desc"` deixam `"65"` por último nas duas.
  - `linhasPorUf(placar, "13", 5)`: os rótulos são `["Acre", "Amazonas"]`, e o presidente de AM é `"—"`.
  - O script termina com `console.log("ok")`.
- [ ] **Step 2:** Rodar `cd frontend && node --experimental-strip-types src/lib/verificar-placar-forca.ts` e ver falhar com `ERR_MODULE_NOT_FOUND`.
- [ ] **Step 3:** Implementar `placar-forca.ts`.
- [ ] **Step 4:** Rodar até imprimir `ok`; depois `pnpm exec tsc --noEmit` e `pnpm exec eslint src/lib/placar-forca.ts src/lib/verificar-placar-forca.ts`, sem saída.
- [ ] **Step 5:** Sem commit.

**If Task Fails:** um percentual diferente indica a base errada. Confira se a base vem de `recorte.base`, nunca de outro recorte. Se não conseguir se recuperar, pare.

---

### Task 9: Layout do gráfico por esfera (módulo puro)

**Files:**
- Create: `frontend/src/lib/grafico-forca.ts`
- Test: `frontend/src/lib/verificar-grafico-forca.ts`

**Interfaces:**
- Consumes: `type Coluna`, `type Esfera` e `type LinhaPlacar` de `./placar-forca.ts`.
- Produces:
  ```ts
  export type MedidasGrupos = { largura: number; esquerda: number; direita: number; topo: number; base: number;
    alturaCabeca: number; alturaBarra: number; passo: number; espaco: number; rotuloAcima: boolean; fonte: number };
  export const MEDIDAS_PADRAO: MedidasGrupos = { largura: 640, esquerda: 132, direita: 112, topo: 4, base: 4,
    alturaCabeca: 22, alturaBarra: 12, passo: 18, espaco: 10, rotuloAcima: false, fonte: 12 };
  export const MEDIDAS_ESTREITO: MedidasGrupos = { largura: 340, esquerda: 2, direita: 96, topo: 4, base: 4,
    alturaCabeca: 22, alturaBarra: 10, passo: 30, espaco: 10, rotuloAcima: true, fonte: 13 };
  export const LIMITE_GRUPOS = 8;
  export const OPACIDADES = [1, 0.7, 0.45, 0.3] as const;
  export type Metrica = { chave: string; curto: string; fracao: number; texto: string; detalhe: string };
  export type Grupo = { chave: string; rotulo: string; metricas: Metrica[] };
  export type BarraDesenhada = Metrica & { y: number; largura: number; opacidade: number };
  export type GrupoDesenhado = { chave: string; rotulo: string; yCabeca: number; barras: BarraDesenhada[] };
  export type LayoutGrupos = { medidas: MedidasGrupos; largura: number; altura: number; grupos: GrupoDesenhado[] };
  export function gruposEsfera(linhas: readonly LinhaPlacar[], colunas: readonly Coluna[], esfera: Esfera,
    limite?: number): Grupo[];
  export function layoutGrupos(grupos: readonly Grupo[], medidas?: MedidasGrupos): LayoutGrupos | null;
  export function resumoGrupos(titulo: string, grupos: readonly Grupo[]): string;
  ```

Regras:
- `gruposEsfera` mantém a ordem das linhas recebidas (a da tabela), toma as colunas da esfera em ordem e descarta métricas com `fracao === null`. Linha sem nenhuma métrica sai, e ficam as `limite` primeiras (padrão `LIMITE_GRUPOS`).
- A escala é fixa (F14): `largura = fracao · (medidas.largura − esquerda − direita)`, com `fracao` limitada a [0, 1].
- No modo padrão, `yCabeca` do grupo i é o acumulado de `alturaCabeca + n·passo + espaco`. Cada barra j fica em `y = yCabeca + alturaCabeca + j·passo`. Com `rotuloAcima`, a barra desce 14 px dentro do passo. `altura = topo + soma + base`.
- `opacidade = OPACIDADES[j]` (a última se j passar do fim).
- `layoutGrupos` devolve `null` sem grupos.
- `resumoGrupos`: `"{titulo}. {rotulo}: {curto} {texto}, {curto} {texto}; {rotulo}: …."`.

- [ ] **Step 1: Escrever o script que falha.** Os casos:
  - fração 1 ocupa a largura útil inteira (640 − 132 − 112 = 396);
  - fração 0 dá largura 0;
  - fração 1,2 é cortada em 396;
  - métrica nula sai;
  - linha toda nula sai;
  - com 10 linhas, ficam 8;
  - com 0 grupos, `layoutGrupos` dá `null`;
  - a altura de 2 grupos × 2 barras é `4 + 2·(22 + 2·18 + 10) + 4 = 144`;
  - a variante estreita tem `largura` 340;
  - `resumoGrupos` confere com o texto exato.
- [ ] **Step 2:** Rodar `node --experimental-strip-types src/lib/verificar-grafico-forca.ts` e ver falhar.
- [ ] **Step 3:** Implementar.
- [ ] **Step 4:** `ok`, `tsc` e `eslint` limpos.
- [ ] **Step 5:** Sem commit.

---

### Task 10: Code Review

1. **REQUIRED SUB-SKILL:** Use jarvis:codereview e dispare todos os revisores em paralelo sobre as Tasks 7 a 9.
2. **Handle findings by severity:** siga as regras de jarvis:codereview.
3. **Proceed only when:** não restar nenhum achado Critical, High ou Medium.

---

### Task 11: Componentes

**Files:**
- Create: `frontend/src/components/relatorios/explicacao-forca.tsx` (servidor)
- Create: `frontend/src/components/relatorios/grafico-forca.tsx` (sem `"use client"`; é renderizado dentro do cliente)
- Create: `frontend/src/components/relatorios/tabela-forca.tsx` (apresentação; recebe ordem e callbacks)
- Create: `frontend/src/components/relatorios/placar-forca.tsx` (`"use client"`)
- Create: `frontend/src/components/relatorios/dados-forca.tsx` (servidor)
- Create: `frontend/src/components/relatorios/filtros-forca.tsx` (`"use client"`)

**Interfaces:**
- `DadosForca({ ano, turno, cargo }: { ano: Ano; turno: Turno; cargo: CargoPoder })`: chama `buscarForca`. Em erro, mostra `<ErroRelatorio detalhe=…/>`. Em sucesso, mostra `<ExplicacaoForca cargo={…} />` e `<PlacarForcaVista placar={…} />`.
- `PlacarForcaVista({ placar }: { placar: PlacarForca })` guarda o estado `limiar` (padrão `LIMIAR_PADRAO`), `recorte` (`"BR"` ou uma UF), `coluna` (`COLUNA_PADRAO`), `direcao` (`"desc"`) e `partido` (`string | null`).
- `TabelaForca({ titulo, colunas, linhas, coluna, direcao, aoOrdenar, aoEscolher? })`.
- `GraficoForca({ id, titulo, legenda, grupos })` desenha como `GraficoPoder`: uma versão larga (`hidden sm:block`, `min-w-[480px]`) e uma estreita (`sm:hidden`), as duas dentro de `DicaGrafico`.
- `FiltrosForca({ ano, turno, cargo })`: "Ano", "Turno" e "Cargo de referência" (`CARGOS_PODER`), depois Consultar com `router.replace("?ano&turno&cargo&consultar=1")`. Copie a estrutura de `filtros-curtos.tsx`: spinner, `useTransition` e reinício do estado quando as props mudam.

Desenho e textos:
- **Aviso de faltando:** quando `placar.faltando.length > 0`, um `<div role="status" className="folha-quieta text-sm">` com "Alguns cargos ainda não foram gravados; as colunas deles mostram —." e uma lista `<code>` com cada `comando`.
- **Controles:** `FiltroSelect` "Recorte" (`Brasil` e `placar.ufs.map(nome)`) e `FiltroSelect` "Presença a partir de" (`placar.limiares`, rótulo `"{n}%"`).
- **Tabela:** `<Table>` com duas linhas de cabeçalho. A primeira tem as esferas, com `colSpan` igual ao número de colunas de cada uma e `scope="colgroup"`. A segunda tem as colunas: cada `<TableHead>` leva um `<button>`, `aria-sort="ascending" | "descending" | "none"` e `title={coluna.explicacao}`. A primeira coluna é "Partido", e cada célula dela é um `<button>` que abre o detalhe (`aoEscolher(chave)`). As células numéricas são `tabular-nums text-right`, com `title={valor.detalhe}`. O `<TableCaption>` traz o recorte e o cargo de referência: `"Brasil · municípios por deputado estadual · 2026, turno 1"`.
- **Gráficos:** três `GraficoForca` (um por esfera) com `gruposEsfera(linhasOrdenadas, colunas, esfera)`. Títulos: "Federação", "Estados" e "Municípios". Legenda: `"Os 8 primeiros da tabela, na ordem atual. Cada barra é a parte do total da esfera: votos válidos, UFs ou municípios. A escala vai de 0 a 100%."`. Rótulo da métrica à esquerda (`text-anchor="end"`, `text-muted-foreground`); valor no fim da barra (`text-foreground`, `tabular-nums`); barra em `var(--tinta-quente)` com `fillOpacity={opacidade}`; nome do partido no cabeçalho do grupo (`font-medium`). Cada barra tem um `<rect>` transparente com `data-dica-titulo="{rotulo}"` e `data-dica-linhas="{curto}: {texto}\n{detalhe}"`. O `<svg role="img">` traz `<title>` e `<desc>`, este com `resumoGrupos`.
- **Detalhe por UF:** com `partido !== null`, uma `<section aria-labelledby>` com o título `"{rotulo} por UF"`, o botão "Fechar" e `TabelaForca` com `linhasPorUf(placar, partido, limiar)` e `colunasPlacar(limiar, "uf")`, com ordenação própria (estado local separado) e "UF" no lugar de "Partido".
- **ExplicacaoForca** (servidor, `<section className="folha-quieta">`):
  - um parágrafo sobre as três esferas, avisando que elas não são somadas num índice único;
  - um `<dl>` com uma entrada por coluna (o texto de `explicacao`);
  - as notas: "Votos válidos são nominais mais legenda, sem brancos e nulos."; "Empate no topo não conta para nenhum partido."; "O exterior entra só no % nacional de presidente."; "O DF elege deputados distritais, que não estão nos dados; por isso fica fora das colunas de deputado estadual e, com esse cargo de referência, dos indicadores municipais."; "— significa sem dados: cargo não gravado, partido que não concorreu ao cargo ou lugar sem esse cargo.";
  - a frase "Cadeiras, governadores e prefeituras entram quando as simulações estiverem disponíveis.", que só aparece enquanto os blocos B e C não vierem.

- [ ] **Step 1:** Implementar os seis componentes.
- [ ] **Step 2:** Rodar `cd frontend && pnpm exec tsc --noEmit && pnpm lint && node --experimental-strip-types src/lib/verificar-placar-forca.ts && node --experimental-strip-types src/lib/verificar-grafico-forca.ts`. Expected: limpo, `ok` e `ok`.
- [ ] **Step 3:** Sem commit.

**If Task Fails:** um erro de hidratação aponta valor não determinístico no cliente; não use `Date` nem `Math.random`. Se não conseguir se recuperar, pare.

---

### Task 12: Página, navegação e verificação no navegador

**Files:**
- Create: `frontend/src/app/relatorios/forca/page.tsx`
- Modify: `frontend/src/components/layout/app-sidebar.tsx` (acrescentar `{ href: "/relatorios/forca", rotulo: "Força partidária" }` em `ITENS`, logo depois de "Classe do governador", como 1º item do bloco dos seis planos e antes de "Cadeiras", se já existir. Ver "Navegação, ordem única"; alinhado em 2026-10-22)
- Modify: `frontend/src/components/layout/app-breadcrumb.tsx` (acrescentar `"/relatorios/forca": { pagina: "Força partidária", relatorios: true }` em `TRILHAS`, na mesma posição)
- Modify: `frontend/src/app/page.tsx` (acrescentar em `DESTINOS` `{ href: "/relatorios/forca", titulo: "Força partidária", descricao: "Placar por partido em três esferas, a partir dos relatórios de poder gravados." }`, na mesma posição)

**Interfaces:**
- A página segue `app/relatorios/classe-governador/page.tsx`: `metadata.title = "Força partidária"`, `maxDuration = 600`, `CHAVES_FILTRO = ["ano", "turno", "cargo"]`, `<h1>Força partidária</h1>`, `<FerramentasApresentacao />`, `Suspense` com `EsqueletoFiltros` e `EsqueletoDados`, e "Selecione os filtros e clique em Consultar." enquanto `consultar` não vale 1.
- O cargo de referência é lido localmente: `const cargo = escolher(consulta.cargo, CARGOS_PODER.map((c) => c.value), "deputadoEstadual")`, com `escolher` e `CARGOS_PODER` de `@/lib/eleicoes`.

- [ ] **Step 1:** Implementar a página e os três links.
- [ ] **Step 2:** Rodar `cd frontend && pnpm exec tsc --noEmit && pnpm lint`. Expected: limpo.
- [ ] **Step 3: Conferir a API real.** O serviço `api` do `docker-compose.yml` não monta `src` como volume e roda `uvicorn` sem `--reload`, então o código fica na imagem `eleicoes_brasil-importer:dev`. Peça ao usuário para reconstruir **só** esse serviço: `docker compose up -d --build api`. Isso recria apenas o container da API, sem derrubar o Compose; o importer usa a mesma imagem, mas não é recriado. Com a API saudável (`curl -s localhost:15000/health` devolve `{"status":"ok"}`), rode:

```bash
URL='http://localhost:15000/relatorios/dados/forca?ano=2026&turno=1&cargo_referencia=deputadoEstadual'
curl -s -o /dev/null -w '%{http_code} %{time_total}\n' "$URL"
curl -s "$URL" | uv run python -I -c "import json,sys;d=json.load(sys.stdin);u={x['chave']:x for x in d['pais']['unidades']};print(d['pais']['base']);print(u['22']['ufs_lider_estadual'],u['22']['municipal']['lidera'],[p for p in u['22']['municipal']['presenca'] if p['limiar']==5])"
```

Expected: `200` e tempo menor que 10 s. A base mostra `ufs_deputado_estadual: 26` e `municipal: {'municipios': 5570, 'validos': 111662018, 'empates': 3}`. A segunda linha é `11 1323 [{'limiar': 5, 'municipios': 4477}]`.

- [ ] **Step 4: Conferir no navegador** (chrome-devtools, aba própria `isolatedContext: "forca"`) em `/relatorios/forca?ano=2026&turno=1&cargo=deputadoEstadual&consultar=1`:
  - **Brasil, PL 22:** Presidente 47,03%, Dep. federal 22,64%, UFs em 1º "11 de 26", Municípios em 1º 1.323, Eleitorado em 1º 41,41% e Presença (≥ 5%) 4.477.
  - **Brasil, PT 13:** Presidente 45,16%, Dep. federal 12,97%, "2 de 26", 523 e 4.457.
  - **PCdoB 65:** Presidente "—".
  - **Ordenação:** por "Municípios em 1º" decrescente, PL fica em primeiro e PSD 55 (935) em segundo. Os nulos ficam por último nas duas direções.
  - **Presença:** com o limiar trocado para 10%, o título muda e o valor muda sem nova requisição (a aba Network não mostra outro `forca`).
  - **Recorte DF:** as colunas de deputado estadual e as municipais mostram "—".
  - **Recorte SP:** a coluna mostra "1º em dep. estadual", Sim ou Não.
  - **Detalhe:** "PL 22 por UF" abre com 27 linhas.
  - **Cargo de referência = presidente:** o N municipal vira 5.571 (medido: 5.688 códigos, menos 117 do exterior, todos com válidos > 0), e o aviso de faltando não aparece.
  - **Tooltip:** aparece sobre uma barra.
  - **Temas:** claro e escuro.
  - **Celular (375 px):** a tabela rola na horizontal e o gráfico usa a variante estreita.
  - **Console:** sem erros novos.

  Salve as capturas `forca-*.png` no scratchpad.

- [ ] **Step 5:** Sem commit.

**If Task Fails:**
1. 404 na API: a imagem não foi reconstruída. `docker compose restart api` não basta, porque o código está dentro da imagem; use `docker compose up -d --build api`.
2. Mais de 10 s: o container tem limite de 0,5 CPU (`deploy.resources.limits`). Meça de novo; se passar de 15 s, troque em `read_power_levels` o `select(PowerReportLine)` pela seleção das sete colunas (`session.execute(select(PowerReportLine.nivel, ...)).all()`) e monte `StoredCell` direto das tuplas. Isso evita objetos ORM. Volte para a Task 3, com teste.
3. Números diferentes dos esperados: refaça as consultas SQL da seção "Fatos dos dados", porque os relatórios podem ter sido regravados.
4. Não conseguiu se recuperar: pare.

---

### Task 13: Code Review final da fase A

1. **REQUIRED SUB-SKILL:** Use jarvis:codereview e dispare todos os revisores em paralelo sobre as Tasks 11 e 12 e o diff completo da fase A.
2. **Handle findings by severity:** siga as regras de jarvis:codereview.
3. **Proceed only when:** não restar nenhum achado Critical, High ou Medium. Só então leve a fase A à validação do usuário.

---

## Fase B: cadeiras e federações (depende do plano 2)

**Bloqueio:** só comece depois que o plano 2 tiver a revisão `0004` aplicada e a Task 13 dele pronta (porta `src/eleicoes/ports/cadeiras.py` e adaptador `StoredSeatEstimates` em `src/eleicoes/use_cases/estimativa_cadeiras.py`). A porta abaixo foi conferida campo a campo com a Task 13 do plano 2 e é idêntica (alinhado em 2026-10-22).

### Interface mínima esperada do plano 2

Porta Python, que o plano 1 consome e o plano 2 implementa (Task 13 do plano 2):

```python
# src/eleicoes/ports/cadeiras.py
@dataclass(frozen=True, slots=True)
class Federacao:
    sigla: str                    # código interno estável do plano 2, ex.: "fe-brasil" (alinhado em 2026-10-22)
    nome: str                     # nome exibido, ex.: "Federação Brasil da Esperança"
    partidos: tuple[int, ...]     # números dos partidos membros em 2026, ex.: (13, 65, 43)

@dataclass(frozen=True, slots=True)
class CadeirasUnidade:
    chave: str                    # "13" (partido) ou "fed:<sigla>", ex.: "fed:fe-brasil" (federação)
    uf: str                       # "BR" para o total nacional, ou a sigla da UF
    camara: int | None            # cadeiras estimadas na Câmara (513 no país)
    senado: int | None            # vagas estimadas no Senado em 2026 (54 no país; não é a bancada de 81)
    governador_1t: int | None     # governadores eleitos no 1º turno
    governador_2t: int | None     # UFs em que o partido está no 2º turno de governador: presença na disputa, sem vencedor projetado (alinhado em 2026-10-22)
    assembleia: int | None        # cadeiras estimadas nas Assembleias, com as 24 da Câmara Legislativa do DF (1.059 no país)

@dataclass(frozen=True, slots=True)
class TotaisCadeiras:
    camara: int; senado: int; governadores: int; assembleias: int

@dataclass(frozen=True, slots=True)
class EstimativaCadeiras:
    ano: int; turno: int; gerado_em: datetime
    federacoes: tuple[Federacao, ...]
    totais: TotaisCadeiras
    linhas: tuple[CadeirasUnidade, ...]

class AsyncEstimativaCadeiras(Protocol):
    async def load(self, ano: int, turno: int) -> EstimativaCadeiras | None: ...
```

No HTTP, espera-se que `GET /relatorios/dados/cadeiras?ano&turno` exponha os mesmos campos (`federacoes`, `totais` e `linhas` com `chave`, `uf`, `camara`, `senado`, `governador_1t`, `governador_2t` e `assembleia`) e responda 409 com o comando para gerar quando faltar. O placar **não** chama essa rota: ele lê a porta no backend, porque precisa da composição das federações para recalcular votos e lideranças (F18).

O que o plano 2 já garante (alinhado em 2026-10-22):
- **Uma linha por partido do registro e uma por federação**, em cada UF com dado e em `"BR"`. Todos os campos vêm como inteiro, nunca `None`. As cadeiras de cada partido membro de federação também vêm, e isso responde à Q4.
- **A linha `fed:<sigla>` já soma os membros.** As cadeiras e os governadores são contagens aditivas, então o placar usa essa linha como vem e **não** soma de novo. Só votos e lideranças são recalculados (F18).
- **2º turno de governador:** `governador_2t` conta a presença do partido entre os dois finalistas da UF (`finalistas`). Não há vencedor projetado. Isso responde à Q3.
- **`load` devolve `None`** quando falta algum dos 5 cargos gravados no plano 2. Também devolve `None` quando o ano não tem registro partidário, porque o adaptador captura `MissingSeatReportError` e `UnknownPartyRegistryError`. O placar nunca recebe 409 nem 422 do plano 2.
- **Totais:** `camara` e `assembleias` são as vagas simuladas, `senado` os eleitos e `governadores` as UFs com resultado. A linha de totais do placar soma **só as linhas de partido**, nunca as de federação, para não contar em dobro.
- **Comando para `disponivel: false`:** `make migrate` (se faltar a `0004`) e `uv run python scripts/relatorio_cadeiras.py`.

### Task 14: Federações no domínio

**Files:** Modify `src/eleicoes/domain/forca.py` e `tests/domain/test_forca.py`.

- [ ] Acrescentar `tipo: str` (`"partido"` ou `"federacao"`) e `nome: str | None` a `ForcaUnidade`, com os padrões `"partido"` e `None` no fim da dataclass, para não quebrar a fase A.
- [ ] Criar `placar_com_federacoes(ano, turno, cargo, fontes, federacoes: tuple[Federacao, ...]) -> PlacarForca`. A função roda `placar_forca` duas vezes, uma com `por_partido` e outra com a chave `fed:<sigla>` para membros e `str(partido)` para os demais. Junta as unidades das duas rodadas, sem repetir partido fora de federação, e marca `tipo` e `nome`.
- [ ] Teste obrigatório (Review Focus) com 3 cidades e uma federação de 13 e 43. Na cidade 1, os votos são 13:30, 43:30 e 22:50, e a federação (60) lidera. Nas cidades 2 e 3, 22 lidera. Por partido, a liderança do 13 é 0, a do 43 é 0 e a da federação é 1, então a soma dos membros (0) não é a liderança da federação (1). Teste também a presença.
- [ ] `uv run pytest tests/domain/test_forca.py -q` passa; ruff e mypy limpos.

### Task 15: Cadeiras no caso de uso e no JSON

**Files:**
- Modify: `src/eleicoes/adapters/http/bundle.py` (campo `seat_estimates: AsyncEstimativaCadeiras | None = None` no fim, para não quebrar construções existentes)
- Modify: `src/eleicoes/adapters/http/dependencies.py` (`get_seat_estimates`, alinhado em 2026-10-22):
  - com `ReadPorts` instalado (testes), devolve `installed.seat_estimates`, que pode ser `None`;
  - em produção, devolve `StoredSeatEstimates(AsyncPostgresSeatVoteStore(_required_session(session)))`. `StoredSeatEstimates` vem de `eleicoes.use_cases.estimativa_cadeiras`, e `AsyncPostgresSeatVoteStore` de `eleicoes.adapters.postgres_relatorio_cadeiras_async`, ambos do plano 2;
  - **não** chama `get_seat_store` do plano 2: com ports instalados sem `seat_store`, ele levanta `ElectionError`, e os testes da fase A virariam 500.
- Modify: `src/eleicoes/use_cases/placar_forca.py`, `schemas_relatorios.py` e `relatorios.py`
- Test: `tests/use_cases/test_placar_forca.py` e `tests/adapters/test_read_api.py`

- [ ] `MontarPlacarForca(store, cadeiras: AsyncEstimativaCadeiras | None = None)`. Quando `cadeiras.load` devolve uma estimativa, o placar usa as federações dela e junta as `CadeirasUnidade` por `(chave, uf)`. Quando devolve `None`, o placar continua só por partido e o bloco `cadeiras` sai com `disponivel: false` e o comando do plano 2 (`uv run python scripts/relatorio_cadeiras.py`; alinhado em 2026-10-22).
- [ ] O JSON ganha `cadeiras: {disponivel: bool, comando: str | null, totais: {...} | null}` no topo e, em cada unidade, `camara`, `senado`, `governador_1t`, `governador_2t` e `assembleia` (`int | null`). Unidades de federação têm `tipo: "federacao"` e `nome`.
- [ ] Testes: com estimativa (os números aparecem e a federação vem recalculada), sem estimativa (`disponivel: false`, campos nulos) e com a porta ausente (`None`, comportamento da fase A).
- [ ] `uv run pytest -q`, `uv run ruff check .` e `uv run mypy` limpos.

### Task 16: Colunas de cadeiras e alternância de federação no frontend

**Files:** Modify `frontend/src/lib/forca.ts`, `placar-forca.ts`, `grafico-forca.ts`, os scripts `verificar-*` e `placar-forca.tsx`.

- [ ] `ChaveColuna` ganha `camara`, `senado`, `governador_1t`, `governador_2t` e `assembleia`. A Federação recebe "Câmara (cadeiras estimadas)" e "Senado (vagas estimadas)", com o texto `"{n}"`, o detalhe `"de {totais.camara}"` e fração n/513. Os Estados recebem "Governadores no 1º turno" (fração n/27), "No 2º turno de governador (disputa)" e "Assembleias (cadeiras estimadas)". A coluna do 2º turno mostra só a contagem de UFs em que o partido disputa, sem fração e sem barra no gráfico (F14). O detalhe diz "disputa, sem vencedor projetado". As Assembleias incluem as 24 cadeiras da Câmara Legislativa do DF (alinhado em 2026-10-22).
- [ ] `colunasPlacar` recebe `placar` e só inclui essas colunas quando `placar.cadeiras` existe (F20). Com `disponivel: false`, elas aparecem com "—", e o aviso mostra o comando.
- [ ] Controle "Mostrar" com duas opções: "Partidos" e "Federações e partidos fora delas". A segunda opção esconde os membros e mostra a linha da federação.
- [ ] Os scripts de verificação ganham casos com e sem `cadeiras`. Rodar `tsc` e `lint`.
- [ ] Verificar no navegador as cadeiras somando 513, 54 e 1.059 na linha de totais (rodapé da tabela) e a alternância de federação.

### Task 17: Code Review da fase B

1. **REQUIRED SUB-SKILL:** jarvis:codereview, com todos os revisores em paralelo.
2. **Proceed only when:** não restar nenhum achado Critical, High ou Medium.

---

## Fase C: prefeitos e vereadores de 2024 (depende do plano 6, opcional)

**Bloqueio:** só comece depois que o plano 6 tiver a revisão `0005` e a Task 11b dele pronta: a porta `src/eleicoes/ports/municipal_2024.py` e o adaptador `StoredMunicipal2024` em `src/eleicoes/use_cases/municipal_2024_placar.py`. A porta abaixo foi alinhada com os nomes do plano 6 em 2026-10-22. `prefeituras` passou a ser `prefeitos`, e `populacao_governada` passou a ser `eleitorado_governado`, porque o plano 6 mede o eleitorado apto e não a população (D5 de lá).

### Interface mínima esperada do plano 6 (alinhado em 2026-10-22)

```python
# src/eleicoes/ports/municipal_2024.py
@dataclass(frozen=True, slots=True)
class MunicipalPartido2024:
    partido: int                  # número de 2026, já convertido pela equivalência do plano 6 (D12, equivalente_2026)
    uf: str                       # "BR" ou uma das 26 UFs com eleição municipal (sem DF e sem ZZ)
    prefeitos: int                # prefeituras com prefeito do partido na data de corte
    eleitorado_governado: int     # eleitorado apto 2024 desses municípios (não é população)
    vereadores: int               # vereadores eleitos pelo partido

@dataclass(frozen=True, slots=True)
class TotaisMunicipal2024:
    uf: str                       # "BR" ou uma das 26 UFs
    municipios: int               # 5.569 no país; inclui municípios sem prefeito eleito
    com_prefeito: int
    eleitorado: int               # 155.912.680 no país
    vereadores: int

@dataclass(frozen=True, slots=True)
class Municipal2024:
    data_corte: datetime          # DT_GERACAO dos CSV do TSE (plano 6, D2)
    importado_em: datetime
    equivalencia_versao: str      # VERSAO_EQUIVALENCIA do plano 6
    totais: tuple[TotaisMunicipal2024, ...]  # um por UF e um "BR"; denominadores do recorte (não somar linhas)
    linhas: tuple[MunicipalPartido2024, ...]
    sem_correspondencia: tuple[int, ...]  # números de 2024 sem número em 2026; entram nos totais, não nas linhas

class AsyncMunicipal2024(Protocol):
    async def load(self) -> Municipal2024 | None: ...
```

A correspondência 2024 → 2026 é a tabela versionada do plano 6 (`src/eleicoes/domain/partido_equivalencia.py`, D12). Ela responde à Q5: a chave é o número; o 35 PMB vira 35 DEMOCRATA (`renomeado`) e o 65 "PC do B" vira 65 PCdoB (`grafia`). As fusões de 2023 já aparecem nos dados de 2024 com o número novo, e o 14 MISSÃO não existe em 2024. As federações não são fundidas em 2024. Na fase B, a linha da federação de 2026 **soma** os membros, porque prefeitos, eleitorado e vereadores são contagens aditivas.

### Task 18: Integrar 2024

- [ ] No backend, um campo opcional em `ReadPorts` (`municipal_2024: AsyncMunicipal2024 | None = None`), usado só nos testes. Ele é diferente do campo `municipais` do plano 6, que guarda o leitor bruto. Em `dependencies.py`, `get_municipal_2024` faz o seguinte (alinhado em 2026-10-22):
  - com ports instalados, devolve `installed.municipal_2024`, que pode ser `None`;
  - em produção, devolve `StoredMunicipal2024(AsyncPostgresMunicipalReader(cast(AsyncSqlConnection, connection)))`, com as duas classes do plano 6;
  - não chama `get_municipal_reader`, que levanta `ElectionError` quando os ports estão instalados sem leitor.
- [ ] O JSON ganha um bloco `municipal_2024: {disponivel, comando, data_corte, totais}`. Cada unidade ganha `prefeitos`, `eleitorado_governado` e `vereadores` (`int | null`).
  - Com `load` devolvendo `None`, o bloco vem com `disponivel: false` e o comando `make download-municipais && make import-municipais`. Se faltar a `0005`, siga antes o backup e o `make migrate` das Global Constraints do plano 6.
  - Para federação, os três valores **somam** os membros, ao contrário das lideranças da F18.
- [ ] No frontend, as colunas "Prefeituras (2024)" (n/municípios), "Eleitorado governado (2024)" (n/eleitorado) e "Vereadores (2024)" (n/vereadores) entram na esfera Municípios. Os denominadores vêm de `totais` do recorte: "BR" no Brasil, a UF no recorte por UF. Não vêm da soma das linhas, que deixa de fora os municípios sem prefeito e os partidos `sem_correspondencia`. O JSON leva `totais` por recorte, só com inteiros (F21).
  - Elas ficam visíveis só com o bloco presente.
  - No recorte DF, mostram "—".
  - O detalhe traz a data de corte: "situação divulgada pelo TSE em …; inclui cassações e suplementares" (pergunta em aberto do plano 6, P2).
- [ ] Testes nos dois lados, verificação no navegador e code review (jarvis:codereview) até não restar achado Critical, High ou Medium.

---

## Fase D: resumos dos planos 3, 4 e 5 (opcional, alinhado em 2026-10-22)

**Bloqueio:** nenhum para as fases A, B e C. Esta fase só começa depois que os planos 3, 4 e 5 estiverem integrados, e cada parte é independente: se um dos planos não existir, a parte dele fica de fora. Não há rota nova, tabela nem migração.

### Task 19: Links do partido para os relatórios irmãos (padrão)

**Files:** Modify `frontend/src/lib/placar-forca.ts`, `verificar-placar-forca.ts` e o componente do detalhe "Partido por UF".

- [ ] No detalhe do partido (F15b), acrescente três links. Eles são incondicionais, porque esta fase só começa com os planos 3, 4 e 5 integrados. A lista fica numa constante do módulo, para retirar um link sem mexer no resto:
  - "Capilaridade": `/relatorios/capilaridade?ano={ano}&turno={turno}&cargo={cargo_referencia}&recorte=brasil&partido={n}&consultar=1`;
  - "Verticalização": `/relatorios/verticalizacao?ano={ano}&turno={turno}&uf=TODAS&partido={n}&consultar=1`;
  - "Força da marca": `/relatorios/marca`.
- [ ] Linhas de federação (fase B) não têm link, porque os três relatórios são por partido.
- [ ] Uma função pura `linksPartido(placar, partido)` monta as URLs e é testada em `verificar-placar-forca.ts`.

### Task 20: Voto de legenda nacional (opcional)

É a única coluna resumida que sai barata, porque o placar já lê `deputadoFederal` (`pais` e `uf`) e `deputadoEstadual` (`uf`).

- [ ] No domínio, guarde `votos_legenda` à parte, além do total, para os dois cargos de deputado no recorte. Isso vale só para essas duas fontes.
- [ ] Siga a definição D17 do plano 5: `legenda / (nominais + legenda)` sobre a soma das linhas `uf` de cada cargo. Deputado não tem voto no exterior, então a soma das UFs é igual à linha `pais`.
- [ ] O JSON ganha os inteiros `legenda_federal` e `legenda_estadual` por unidade. O frontend forma a fração com `formatarPercentualContagem` (F21).
- [ ] Colunas "Voto de legenda (dep. federal)" e "(dep. estadual)" num grupo próprio, "Perfil do voto", fora das três esferas e fora do gráfico F14. As linhas de federação mostram "—", porque a métrica é por partido. No recorte DF, a coluna estadual mostra "—".
- [ ] Teste cruzado com o plano 5, com os números esperados: 3,01% em federal (3.438.422 de 114.107.982) e 6,45% em estadual (7.204.172 de 111.662.018).

### Task 21: Capilaridade e verticalização em colunas (só se o usuário pedir)

- [ ] Capilaridade (plano 3):
  - leia `summarize(job(ano, turno, cargo_referencia).view(None, None))` via `get_capillarity_job()`;
  - mostre só a classe (com o rótulo `rotulo_classe` do recorte Brasil) e `indice_100`;
  - **não** mostre a `presenca` do plano 3, cujo denominador difere do F9.
- [ ] Verticalização (plano 4):
  - leia `perfil` e `coerencia_mediana` do relatório do recorte Brasil via `get_vertical_job()`;
  - o cache frio custa alguns segundos, uma vez por (ano, turno).
- [ ] Os dois jobs são síncronos. Rode-os com `asyncio.to_thread`, como fazem as rotas dos planos 3 e 4, para não bloquear o event loop.
- [ ] As duas fontes são opcionais. Capture `MissingPowerReportError` (e erros de recorte) no caso de uso: as colunas mostram "—", e o aviso diz qual relatório falta. O placar nunca responde 409 por causa delas.
- [ ] As colunas entram no grupo "Perfil do voto" e mostram "—" nas linhas de federação e nos recortes por UF.

### Task 22: Code Review da fase D

1. **REQUIRED SUB-SKILL:** jarvis:codereview, com todos os revisores em paralelo.
2. **Proceed only when:** não restar nenhum achado Critical, High ou Medium.

---

## Fase E: índice composto (não implementar sem resposta do usuário; era "Fase D", renomeada em 2026-10-22)

Esboço para quando houver resposta:
- Por coluna c de um pilar p: `nota_c = fracao_c / max(fracao_c entre as unidades do recorte)`, com valores de 0 a 1 e nulo tratado como 0.
- Por pilar: `nota_p` é a média das `nota_c` das colunas disponíveis do pilar.
- Índice: `Σ w_p·nota_p / Σ w_p`, com os pesos `w_p` de 0 a 10 em três controles deslizantes na tela (padrão 1/1/1).
- O índice aparece como coluna "Índice (pesos ajustáveis)", ordenável, só com o interruptor "Mostrar índice composto", e traz o aviso: "o índice depende dos pesos e da normalização; use os três pilares para comparar".
- Ganchos já previstos: `LinhaPlacar.valores` aceita uma chave nova, e `colunasPlacar` monta a lista no cliente.
- As colunas do grupo "Perfil do voto" (fase D) não entram no índice.

## Perguntas em aberto

- **Q1:** O usuário quer o índice composto (Fase E)? Se quiser, com que normalização: pelo máximo, por posição ou por z-score?
- **Q2:** O limiar de presença deve aceitar valor livre (por exemplo 3%)? Hoje a lista é fixa, com 1, 2, 5, 10 e 20%. Um valor livre exigiria nova chamada à API ou o histograma completo na resposta.
- **Q3 (respondida em 2026-10-22):** O plano 2 não projeta vencedor no 2º turno de governador. `governador_2t` conta só a presença do partido entre os dois finalistas da UF. A coluna se chama "No 2º turno de governador (disputa)" (Task 16).
- **Q4 (respondida em 2026-10-22):** Sim. O plano 2 devolve as cadeiras de cada partido membro e também a linha da federação, já somada (D21 e Task 13 de lá).
- **Q5 (respondida em 2026-10-22):** A conversão usa a tabela versionada do plano 6 (D12, `equivalente_2026`), com chave no número. Ver "Fase C".
- **Q6 (em parte respondida em 2026-10-22):** O plano 2 lê `deputadoDistrital` dos boletins, então as Assembleias da fase B já incluem as 24 cadeiras do DF. O voto em deputado estadual por UF continua sem DF, porque o relatório de poder não grava distrital. Gravar distrital no relatório de poder é outro plano, e esta pergunta fica para depois dele.
- **Q7 (nova, 2026-10-22):** A fase D deve ir além dos links (Task 19) e da coluna de voto de legenda (Task 20) e mostrar também as colunas de capilaridade e verticalização (Task 21)? O padrão é não.


## Decisões do usuário (2026-10-22)

O usuário aceitou as recomendações da revisão de coerência. Estas decisões valem sobre qualquer pergunta em aberto neste plano.

- **Índice composto:** não entra agora. A fase E fica como esboço.
- **2024:** prefeito no cargo hoje (situação do dia do download), com a data de corte exibida.
- **Senado:** só as 54 vagas de 2026.
- **Fase D do placar:** só os links para Capilaridade, Verticalização e Força da marca e a coluna de voto de legenda (Tasks 19 e 20). A Task 21 não entra.
- **Federações:** a lista das cinco federações (Brasil da Esperança: PT, PCdoB, PV; PSDB Cidadania; PSOL Rede; Renovação Solidária: PRD, Solidariedade; União Progressista: União, PP) fica no código (`domain/federacoes.py`). A Força da marca não agrega os federados.
- **Cadeiras com cargo faltando:** a página de cadeiras responde 409; o placar mostra "—".
- **Divisor das sobras:** regra da Resolução do TSE (quociente partidário + médias já ganhas + 1), conferida com o resultado oficial.
- **Votos de candidato indeferido ou sub judice:** contam como válidos, com aviso na página.
- **Limiares das classes:** manter os calibrados nos planos e rever depois da primeira execução com dados reais.
- **Fusões de partido depois de dez/2025:** conferir no TSE antes da Task 1 do plano 6 (ação, não pergunta).
- **Título eleitoral e data de nascimento (2024):** guardar no `raw`, como nas demais tabelas brutas (dados públicos).
- **Itens menores:** sem população do IBGE, limiar de presença na lista fixa, sem classe de viés regional, Força da marca com página fixa, sem mapa de calor e com o visual proposto.
