# Relatório de capilaridade partidária

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Review between blocks of tasks via jarvis:codereview.

**Goal:** Uma página nova, `/relatorios/capilaridade`, mostra para cada partido e cargo se a força dele está espalhada pelos municípios ou concentrada em poucos lugares, numa região ou nas capitais. A página traz um ranking dos partidos por concentração e o detalhe de cada um: distribuição por faixa, a parte dos votos que vem dos 10% de municípios mais fortes, o índice de concentração e uma classificação com o motivo. Os dados saem de um endpoint novo, `GET /relatorios/dados/capilaridade`, calculado só a partir das linhas municipais já gravadas em `analise.relatorio_poder_linha`.

**Architecture:** O domínio puro (`domain/capilaridade.py` e `domain/capilaridade_classe.py`) recebe as `StoredCell` municipais e calcula tudo com `Fraction`: municípios, recortes, métricas por partido, classificação e o resumo que o placar (plano 1) reaproveita. Um leitor síncrono (`PostgresStoredLines.municipal_cells`) faz um único SELECT em `analise`, sem tocar `raw.boletim`. Um job em `dependencies.py`, com `lru_cache`, monta o relatório de um cargo para todos os recortes (Brasil, 5 regiões, 27 UFs). A rota roda o job em `asyncio.to_thread` e escolhe o recorte. É o mesmo padrão de `perfis` e `classe-governador`. No frontend, um módulo puro (`lib/grafico-capilaridade.ts`) monta o layout e as frases, e componentes de servidor desenham os SVGs (ranking e faixas), a tabela e a explicação. Sem tabela nova e sem migração Alembic.

**Tech Stack:** Python 3.11, FastAPI, Pydantic v2, SQLAlchemy 2 (síncrono, como `postgres_perfis.py`), pytest, ruff (`C90` com complexidade máxima 10, linha de 100), mypy strict (`disallow_any_explicit`). Next.js 16.4, React 19, TypeScript, Tailwind 4. Sem biblioteca de gráficos. O script de verificação roda com `node --experimental-strip-types`.

**Spec:** Este arquivo. A seção "Contrato JSON" fixa os campos. A seção "Evidência de calibração" mostra o que as regras produzem nos dados reais de 2026.

---

## Decisões

| # | Pergunta | Decisão |
|---|---|---|
| D1 | Fonte | Só as linhas `nivel='municipio'` de `analise.relatorio_poder_linha` para `(ano, turno, cargo)`. Não lê boletins, não usa os níveis `uf`, `regiao` nem `pais` e não cria tabela. Sem linhas para o cargo, a resposta é `MissingPowerReportError`, que já vira 409 com a instrução de gerar o relatório. |
| D2 | Municípios | A UF vem do sufixo ` (UF)` do nome gravado (`"SÃO PAULO (SP)"`), o mesmo critério do frontend em `linhasVisiveis`. Os lugares `ZZ` (exterior, 117 no presidente) saem do cálculo e são contados em `exterior`. Não há número fixo de municípios: os dados têm 5.571 municípios (inclui Boa Esperança do Norte, MT, instalado em 2025), 5.570 em deputado estadual (o DF elege distrital) e 5.688 no presidente antes de tirar o exterior. Municípios com 0 voto válido saem das métricas e são contados em `sem_validos`. |
| D3 | Votos e fatia | Os votos do partido no município são `votos_nominais + votos_legenda`. Os votos válidos do município são a soma de todos os partidos, o mesmo critério de `grafico-poder` (P2). A fatia é votos do partido / votos válidos. Brancos e nulos não entram. |
| D4 | Universo do partido | O universo de um partido no recorte são os municípios com voto válido das **UFs onde o partido teve pelo menos um voto** (`ufs_com_voto`). Sem isso, governador e senador (candidaturas estaduais) parecem "concentrados" só porque o partido não concorreu em todas as UFs. No presidente, o universo é sempre o recorte inteiro. As métricas de concentração (índice, 10% mais fortes, presença, capitais, faixas) usam o universo. A regra "regional" usa o recorte inteiro, porque mede onde os votos estão no mapa. |
| D5 | Índice de concentração | É o **Gini da curva de concentração ponderada pelo eleitorado**, e não um HHI ou Gini simples sobre os votos do partido. Esses dois medem sobretudo onde a população mora: São Paulo domina qualquer partido. A fórmula: ordenar os municípios do universo pela fatia do partido, do menor para o maior. Com `V_i` = válidos, `v_i` = votos do partido, `T = ΣV_i`, `P = Σv_i` e `C_i` = soma acumulada de `v`, vale `G = 1 − Σ V_i·(C_{i−1} + C_i) / (T·P)`. Como só entram inteiros, o resultado é uma `Fraction` exata. Empates de fatia não mudam o valor. O índice fica entre 0 e 1 (`G = 1 − 1/N` quando N municípios iguais e só um vota). A tela mostra `indice_100 = round_half_up(G·100)`, de 0 a 100. Em linguagem simples: "0 quer dizer que o partido teve a mesma fatia em todo município. Perto de 100 quer dizer que quase todos os votos vieram de um pedaço pequeno do eleitorado." |
| D6 | 10% mais fortes | "Mais forte" é a maior **fatia**, não o maior número de votos. A ordem é fatia decrescente, depois votos decrescentes, depois código. `k = max(1, ceil(municípios do universo / 10))`. A saída tem a parte dos votos do partido que vem desses k municípios (`top10.parte`) e, sempre ao lado, a parte dos votos válidos que eles têm (`top10.eleitorado`), que é a base de comparação. `vezes = parte / eleitorado`. A frase fica assim: "Os 557 municípios onde é mais forte deram 31,30% dos votos do partido. Eles têm 7,30% do eleitorado." |
| D7 | Presença | Um município tem presença quando a fatia do partido é de pelo menos 5% (`PRESENCA = 5/100`). `presenca.parte` = municípios com presença / municípios do universo. "Teve voto" (> 0) não serve, porque dá ~100% para todo partido grande. |
| D8 | Forma da distribuição | Um **histograma por faixa relativa à média do partido**, em dois painéis lado a lado com as mesmas faixas: "Municípios" (quantos) e "Votos do partido" (de onde vêm). As faixas, em vezes a fatia média do partido no universo (`P/T`), são: `0 voto`, `< ½`, `½–1`, `1–1,5`, `1,5–2`, `2–3`, `3 ou mais`. Faixas relativas servem para todos os cargos: uma fatia absoluta de 0–10% esmaga deputado numa barra só e espalha presidente. Strip e beeswarm foram descartados, porque são 5.571 nós SVG × 2 variantes por partido e ilegíveis para leigo. A curva de Lorenz também foi descartada, porque é abstrata para leigo. O par de painéis conta a mesma história sem eixo duplo: muitos municípios em "< ½" e muitos votos em "3 ou mais" é concentração. |
| D9 | Ranking | Barras horizontais de `indice_100` numa escala fixa de 0–100 (o índice é absoluto, então a escala não se ajusta ao maior valor). As barras seguem a forma de ênfase: o partido selecionado em `--tinta-quente`, os outros em `--muted-foreground`. A classe aparece como texto ao lado, nunca como cor. Ordem: classes classificáveis primeiro, depois índice decrescente, depois número do partido. `pouco_voto` e `sem_base` ficam fora do gráfico e aparecem só na tabela. Cada barra é um link `?…&partido=N`. |
| D10 | Classificação | Uma lista ordenada de regras. A primeira que vale decide. Os limites são constantes nomeadas (`capilaridade_classe.py`): **1.** `pouco_voto`: fatia no universo < 1%. **2.** `sem_base`: universo com menos de 20 municípios (DF, RR e AP no recorte por UF). **3.** `capitais`: `capitais.vezes ≥ 1,75`, ou seja, a parte dos votos vinda das capitais do universo é pelo menos 1,75 vez o peso delas no eleitorado do universo. **4.** `regional`: existe uma subdivisão (região no recorte Brasil, UF no recorte região) que dá pelo menos 50% dos votos do partido com `vezes ≥ 1,5`. **5.** `poucos_municipios`: `top10.parte ≥ 50%` e `top10.vezes ≥ 2`. **6.** `espalhado`: nenhuma das anteriores. |
| D11 | Recorte | Query `regiao=NO\|NE\|CO\|SE\|S` ou `uf=XX`, e nunca os dois (422). Sem nenhum dos dois, o recorte é Brasil. Dois parâmetros evitam o choque entre a sigla `SE` da região Sudeste e a UF Sergipe. Muda o seguinte por recorte: as subdivisões (Brasil → regiões, região → UFs, UF → nenhuma, então a regra regional não se aplica), as capitais (as do universo) e os rótulos ("Nacional / espalhado", "Espalhado pela região", "Espalhado pelo estado"). `uf=ZZ` dá 422. Um recorte sem municípios gravados para o cargo (DF em deputado estadual) dá 409. |
| D12 | Capitais | Constante `CAPITAIS` com os 27 códigos TSE, conferidos em 22/10/2026 com um SELECT só de leitura em `analise.relatorio_poder_linha` (governador, 2026, 1º turno): 1392 Rio Branco, 27855 Maceió, 6050 Macapá, 2550 Manaus, 38490 Salvador, 13897 Fortaleza, 97012 Brasília, 57053 Vitória, 93734 Goiânia, 9210 São Luís, 90670 Cuiabá, 90514 Campo Grande, 41238 Belo Horizonte, 4278 Belém, 20516 João Pessoa, 75353 Curitiba, 25313 Recife, 12190 Teresina, 60011 Rio de Janeiro, 17612 Natal, 88013 Porto Alegre, 35 Porto Velho, 3018 Boa Vista, 81051 Florianópolis, 71072 São Paulo, 31054 Aracaju, 73440 Palmas. Os códigos são gravados sem zero à esquerda. Uma capital ausente de um cargo simplesmente não entra. Sem capital no universo, `capitais` é `null` e a regra 3 não se aplica. |
| D13 | Cache | O job `get_capillarity_job()` devolve uma função `(ano, turno, cargo) → CapillarityReport` com `lru_cache(maxsize=16)`, que guarda todos os recortes. `clear_report_caches()` passa a limpar esse cache também. Medição: ler as 162 mil linhas do maior cargo leva 0,4 s no `psql`, e o cálculo de Brasil com `Fraction` fica abaixo de 1 s por cargo. Regenerar o relatório de poder pela linha de comando exige reiniciar a API, como já acontece com perfis. |
| D14 | Números no JSON | Razões exatas vão como `str(Fraction)` (por exemplo `"15/28"`, `"0"`, `"1"`), lidas por `analisarFracao` de `fracao.ts`. Ao lado vai o texto pronto `*_texto` (`format_percent`, `"53,57%"`), e "vezes" vai com 2 casas (`"2,17"`). Contagens vão como inteiros. O índice vai em três formas: `indice` (fração), `indice_texto` (`format_decimal`, `"0,5357"`) e `indice_100` (inteiro). |
| D15 | Resumo para o placar | `resumo` no JSON e a função pura `summarize(view) → tuple[PartySummary, ...]`. Campos de `PartySummary` (domínio): `partido`, `votos`, `fatia`, `indice`, `presenca`, `ufs_com_voto` e `classe`, mais a propriedade `indice_100`. O rótulo depende do recorte e é texto ao usuário, então `rotulo_classe` existe só no JSON (adapter `rotulo_classe(classe, scope, subdivisao)`). Campos de `resumo` no JSON: `partido`, `votos`, `fatia`, `fatia_texto`, `indice`, `indice_100`, `presenca`, `presenca_texto`, `ufs_com_voto`, `classe` e `rotulo_classe`. O plano 1 chama `GET /relatorios/dados/capilaridade?ano&turno&cargo` sem recorte e lê `resumo`, ou chama `summarize` direto no backend. Os nomes não mudam sem atualizar o plano 1. **Consumo opcional (alinhado em 2026-10-22):** o placar não depende deste plano nas fases A, B e C. Na fase D do plano 1, o padrão é só um link do detalhe do partido para esta página (Task 19 de lá), com `cargo`, `recorte=brasil` e `partido`. As colunas, com `classe`/`rotulo_classe` e `indice_100` lidos por `summarize(get_capillarity_job()(ano, turno, cargo).view(None, None))`, só entram se o usuário pedir (Task 21 de lá). O placar **não** mostra a `presenca` daqui, porque o denominador dela (universo do partido) difere do da presença do placar (F9 do plano 1). |
| D16 | Partido padrão no detalhe | Sem `?partido=`, ou com um partido que não está na resposta, o detalhe abre no partido com mais votos no recorte (desempate pelo menor número). |
| D17 | Sigla | `rotuloPartido` de `frontend/src/lib/partidos.ts` ("PT 13"). O backend devolve só o número. |
| D18 | Acessibilidade | `<svg role="img">` com `<title>` e `<desc>`, e o `<desc>` traz todos os valores. A tabela com todos os partidos fica abaixo, como caminho acessível. O tooltip usa `DicaGrafico`, e há uma variante estreita (`MEDIDAS_ESTREITO`) para 375 px. |

### Evidência de calibração (dados reais, 2026, 1º turno, Brasil)

Um script só de leitura (`\copy` das linhas municipais para o scratchpad, mais Python com `Fraction`) aplicou as regras de D4 a D10 em 22/10/2026. Contagem de partidos por classe:

| Cargo | espalhado | regional | capitais | poucos_municipios | pouco_voto | sem_base |
|---|---|---|---|---|---|---|
| presidente | 5 | 0 | 0 | 0 | 7 | 0 |
| governador | 3 | 10 | 1 | 0 | 13 | 0 |
| senador | 6 | 9 | 1 | 2 | 11 | 0 |
| deputadoFederal | 9 | 6 | 1 | 2 | 10 | 0 |
| deputadoEstadual | 9 | 2 | 1 | 6 | 11 | 0 |

Nenhuma classe passa de 80% dos partidos classificáveis em nenhum cargo, exceto presidente: lá todo partido com 1% ou mais é `espalhado`, o que é esperado numa disputa nacional. Alguns pontos de referência:
- PSOL 50 é `capitais` em deputado federal e estadual (`vezes` 1,92 e 2,17).
- NOVO 30 é `regional` (Sul) em deputado federal.
- PL 22 é `regional` (Sul) em governador e `espalhado` em senador. Esse caso levou à exigência de "pelo menos 50% dos votos" em D10, porque só com `vezes ≥ 1,5` o PL sairia regional no Centro-Oeste.
- MISSÃO 14 no presidente seria `poucos_municipios` sem a exigência `vezes ≥ 2`: os seus 10% mais fortes têm 41% do eleitorado.
- PSD 55 no presidente (Centro-Oeste 3,09 vezes, mas só 23% dos votos) fica `espalhado`. O detalhe mostra a subdivisão com 3,09 vezes.

Índice no Brasil, presidente: PT 13 = 0,196, PL 22 = 0,174. Deputado federal: PT 0,30, PL 0,34, PSD 0,53, PV 0,82. A Task 8 refaz esta tabela pelo endpoint e compara.

---

## Contrato JSON

`GET /relatorios/dados/capilaridade?ano=2026&turno=1&cargo=deputadoFederal[&regiao=NE|&uf=SP]`

```json
{
  "ano": 2026, "turno": 1, "cargo": "deputadoFederal",
  "recorte": {"tipo": "pais", "codigo": "BR", "nome": "Brasil"},
  "municipios": 5571, "ufs": 27, "sem_validos": 0, "votos_validos": 104000000, "exterior": 0,
  "limites": {
    "presenca": "5,00%", "pouco_voto": "1,00%", "minimo_municipios": 20,
    "capitais_vezes": "1,75", "regional_parte": "50,00%", "regional_vezes": "1,50",
    "poucos_parte": "50,00%", "poucos_vezes": "2,00"
  },
  "partidos": [
    {
      "partido": 50, "votos": 4800000, "votos_validos": 103000000, "votos_validos_recorte": 104000000,
      "fatia": "…/…", "fatia_texto": "4,66%", "fatia_recorte_texto": "4,62%",
      "ufs_com_voto": 26, "municipios": 5500,
      "indice": "…/…", "indice_texto": "0,6240", "indice_100": 62,
      "top10": {"municipios": 550, "votos": 4000000, "parte": "…", "parte_texto": "83,90%",
                "eleitorado": "…", "eleitorado_texto": "33,60%", "vezes": "2,50"},
      "presenca": {"municipios": 600, "parte": "…", "parte_texto": "10,91%"},
      "capitais": {"municipios": 27, "votos": 2000000, "parte": "…", "parte_texto": "43,60%",
                   "eleitorado": "…", "eleitorado_texto": "22,70%", "vezes": "1,92"},
      "subdivisoes": [{"codigo": "SE", "nome": "Sudeste", "municipios": 1668, "votos": 3700000,
                       "parte": "…", "parte_texto": "78,00%", "eleitorado": "…",
                       "eleitorado_texto": "42,00%", "vezes": "1,85"}],
      "faixas": [{"chave": "zero", "municipios": 900, "votos_validos": 3000000, "votos": 0}],
      "fortes": [{"codigo": "71072", "nome": "SÃO PAULO (SP)", "votos": 1, "votos_validos": 1,
                  "fatia": "…", "fatia_texto": "12,00%"}],
      "maiores": [],
      "classe": "capitais", "rotulo_classe": "Concentrado nas capitais",
      "motivo": "As capitais deram 43,60% dos votos do partido, 1,92 vez o peso delas no eleitorado (22,70%)."
    }
  ],
  "resumo": [
    {"partido": 50, "votos": 4800000, "fatia": "…", "fatia_texto": "4,66%", "indice": "…",
     "indice_100": 62, "presenca": "…", "presenca_texto": "10,91%", "ufs_com_voto": 26,
     "classe": "capitais", "rotulo_classe": "Concentrado nas capitais"}
  ],
  "notas": ["…"]
}
```

`ufs` é o número de UFs distintas entre os municípios com voto válido do recorte (26 em deputado estadual no Brasil). O frontend compara esse número com `ufs_com_voto`. `faixas` traz sempre as 7 chaves, nesta ordem: `zero`, `ate_metade`, `metade_a_media`, `media_a_1_5`, `1_5_a_2`, `2_a_3`, `3_ou_mais`. `fortes` e `maiores` têm até 5 itens. `subdivisoes` vem vazio no recorte por UF. `partidos` e `resumo` seguem a mesma ordem (D9).

Rótulos (`rotulo_classe`) por recorte:

| classe | pais | regiao | uf |
|---|---|---|---|
| `pouco_voto` | Pouco voto | Pouco voto | Pouco voto |
| `sem_base` | Poucos municípios para classificar | idem | idem |
| `capitais` | Concentrado nas capitais | Concentrado nas capitais | Concentrado na capital |
| `regional` | Regional ({nome da região}) | Concentrado em uma UF ({nome da UF}) | — |
| `poucos_municipios` | Concentrado em poucos municípios | idem | idem |
| `espalhado` | Nacional / espalhado | Espalhado pela região | Espalhado pelo estado |

Motivos (`motivo`), em texto exato, com os números já formatados:
- `pouco_voto`: `"Teve {fatia_texto} dos votos válidos onde recebeu voto, abaixo de 1,00%."`
- `sem_base`: `"Só {municipios} municípios com voto; são precisos 20 para classificar."`
- `capitais`: `"As capitais deram {parte_texto} dos votos do partido, {vezes} vez(es) o peso delas no eleitorado ({eleitorado_texto})."` Use `vez` quando o valor formatado for `"1,00"` até `"1,99"`, e `vezes` nos demais.
- `regional`: `"{nome} deu {parte_texto} dos votos do partido, {vezes} vez(es) o peso no eleitorado ({eleitorado_texto})."`
- `poucos_municipios`: `"Os {k} municípios onde é mais forte deram {parte_texto} dos votos, {vezes} vez(es) o peso deles no eleitorado ({eleitorado_texto})."`
- `espalhado`: `"Nenhuma regra de concentração se aplicou. Os {k} municípios onde é mais forte deram {parte_texto} dos votos e têm {eleitorado_texto} do eleitorado."`

`notas` (texto fixo, nesta ordem):
1. `"Os votos do partido somam votos nominais e de legenda; votos válidos não incluem brancos e nulos."`
2. `"Cada partido é medido só nas UFs onde recebeu voto, para não confundir falta de candidato com fraqueza."`
3. `"O exterior fica fora do cálculo; os municípios são os que têm células gravadas para o cargo."`
4. `"Os limites das classes foram calibrados com os dados de 2026 e podem mudar."`

Os textos evitam artigo antes do nome de UF ("em Bahia" e "de Distrito Federal" seriam erros), por isso usam "uma UF ({nome})" e "recorte {nome}".

Erros: 422 `"Ano inválido."` / `"Turno inválido."` / `"Cargo inválido."` / `"UF inválida."`; 422 `"Recorte inválido. Use regiao (NO, NE, CO, SE ou S) ou uf, não os dois."`; 409 com o texto de `MissingPowerReportError`; 409 `"Não há municípios gravados para {cargo} no recorte {nome do recorte}."`.

---

## Global Constraints

- Sem tabela nova e sem migração (0004/0005 são dos planos 2 e 6, e 0006 não é usada). Só leitura em `analise`. Nenhuma consulta a `raw.*`.
- Sem dependência nova, Python ou npm. Sem commit até o humano pedir. Sem git que muda estado (`stash`, `checkout`, `reset`, `commit`).
- Mensagens internas e docstrings em inglês. Texto ao usuário em português.
- Python: funções com complexidade ≤ 10, linhas ≤ 100, mypy strict sem `Any` explícito.
- **Integração (alinhado em 2026-10-22):** a ordem dos planos é 2 → 6 → 1 (fases A, B e C), e este plano entra em qualquer momento. A tabela de quem toca cada arquivo compartilhado está no plano 1, na seção "Integração entre os planos de 2026-10-22". Definições comuns: votos válidos = nominais + legenda; UF pelo sufixo `" (UF)"`; exterior (ZZ) fora; DF sem deputado estadual gravado (409 no recorte DF); presença ≥ 5% inclusiva. O denominador da presença daqui é o universo do partido, e o do placar é todo o recorte.
- **Arquivos compartilhados que este plano toca** (os planos irmãos também podem tocar, então faça edições pequenas e só por adição):
  - `src/eleicoes/domain/errors.py`: duas classes novas no fim do arquivo.
  - `src/eleicoes/adapters/http/errors.py`: duas linhas em `_OWN_TEXT`.
  - `src/eleicoes/adapters/postgres_perfis.py`: um método e uma função `municipal_statement`.
  - `src/eleicoes/adapters/http/dependencies.py`: job, cache e uma linha em `clear_report_caches`.
  - `src/eleicoes/adapters/http/relatorios.py`: uma rota no fim.
  - `tests/adapters/test_read_api.py`: uma entrada no conjunto `expected` de `test_health_and_openapi_advertise_the_read_routes`.
  - `frontend/src/lib/relatorios.ts`: só `export` diante de `exigirLista`, `exigirRegistro`, `exigirTexto`, `exigirTextoOuNulo` e `exigirInteiro`.
  - `frontend/src/lib/buscar-relatorios.ts`: uma função `buscarCapilaridade`.
  - `frontend/src/components/layout/app-sidebar.tsx`, `frontend/src/components/layout/app-breadcrumb.tsx` e `frontend/src/app/page.tsx` (`DESTINOS`): uma entrada em cada.
- Não mudam: `schemas_relatorios.py` (o JSON novo vai num arquivo próprio), `eleicoes.ts` (o tipo de consulta novo fica em `lib/ler-capilaridade.ts`, e `nomeUf` já é exportado), `FiltrosCurtos` (usa `CARGOS_PERFIL`, que tem só 3 cargos), `dica-grafico.tsx`, `fracao.ts` e `partidos.ts`.

## Review Focus

- A fórmula do índice (D5) e as comparações exatas das faixas (sem `float` no backend).
- O universo por UF com voto (D4) aplicado a todas as métricas de concentração, e a regra regional calculada sobre o recorte inteiro.
- A precedência das regras (D10) e os limites como constantes, com teste de borda em cada limite (`>=` contra `<`).
- O cache limpo em `clear_report_caches` e um erro nunca cacheado.
- O frontend não refaz cálculo do backend: só layout e frases.

---

### Task 1: Erros, municípios e recortes (domínio)

**Files:**
- Modify: `src/eleicoes/domain/errors.py` (adicionar no fim)
- Create: `src/eleicoes/domain/capilaridade.py` (primeira parte)
- Test: `tests/domain/test_capilaridade.py`

**Interfaces:**
- Consumes: `StoredCell` (`domain/stored_grade.py`), `REGIONS` e `region_of` (`domain/regiao.py`), `Uf`, `uf_name` e `UF_NAMES` (`domain/values.py`), `InconsistentCellError` e `InvalidCargoError` (`domain/errors.py`).
- Produces:
  ```python
  CARGOS: Final[frozenset[str]]; ABROAD: Final = "ZZ"; CAPITAIS: Final[frozenset[str]]
  PAIS, REGIAO, UF: Final[str]   # "pais", "regiao", "uf"
  def require_capillarity_cargo(cargo: str) -> str
  @dataclass Municipality(codigo: str, nome: str, uf: str, votos: Mapping[int, int]); .validos: int; .of(partido) -> int
  @dataclass MunicipalSet(places: tuple[Municipality, ...], exterior: int)
  def places_from_cells(cells: Iterable[StoredCell]) -> MunicipalSet
  def uf_of(nome: str) -> str
  @dataclass Scope(tipo: str, codigo: str, nome: str); BRASIL: Final[Scope]
  def scope_of(regiao: str | None, uf: str | None) -> Scope
  def all_scopes() -> tuple[Scope, ...]
  def contains(scope: Scope, place: Municipality) -> bool
  def subdivision_of(scope: Scope, place: Municipality) -> tuple[str, str] | None
  class InvalidRecorteError(ElectionError); class EmptyRecorteError(ElectionError)
  ```

- [x] **Step 1: Escrever os testes que falham** em `tests/domain/test_capilaridade.py`:

```python
"""Capillarity: municipalities, scopes and exact concentration metrics."""

from fractions import Fraction

import pytest

from eleicoes.domain.capilaridade import (
    BRASIL,
    Municipality,
    Scope,
    all_scopes,
    contains,
    places_from_cells,
    require_capillarity_cargo,
    scope_of,
    subdivision_of,
    uf_of,
)
from eleicoes.domain.errors import (
    InconsistentCellError,
    InvalidCargoError,
    InvalidRecorteError,
    InvalidUfError,
)
from eleicoes.domain.stored_grade import StoredCell


def _cell(codigo: str, nome: str, partido: int, nominais: int, legenda: int = 0) -> StoredCell:
    return StoredCell("municipio", codigo, nome, 1000, partido, nominais, legenda)


def test_places_sum_nominal_and_legenda_and_drop_the_abroad() -> None:
    cells = (
        _cell("71072", "SÃO PAULO (SP)", 13, 30, 5),
        _cell("71072", "SÃO PAULO (SP)", 22, 65),
        _cell("29999", "LISBOA (ZZ)", 13, 4),
    )
    found = places_from_cells(cells)
    assert found.exterior == 1
    assert len(found.places) == 1
    place = found.places[0]
    assert (place.codigo, place.uf, place.validos) == ("71072", "SP", 100)
    assert place.of(13) == 35
    assert place.of(99) == 0


def test_places_reject_a_name_without_uf_a_repeated_party_and_other_levels() -> None:
    with pytest.raises(InconsistentCellError):
        places_from_cells((_cell("1", "SEM UF", 13, 1),))
    with pytest.raises(InconsistentCellError):
        places_from_cells((_cell("1", "A (AC)", 13, 1), _cell("1", "A (AC)", 13, 2)))
    with pytest.raises(InconsistentCellError):
        places_from_cells((StoredCell("uf", "AC", "Acre", 10, 13, 1, 0),))


def test_uf_of_reads_the_suffix() -> None:
    assert uf_of("BELÉM (PA)") == "PA"
    with pytest.raises(InconsistentCellError):
        uf_of("BELÉM PA")


def test_scope_of_defaults_to_brasil_and_keeps_sudeste_apart_from_sergipe() -> None:
    assert scope_of(None, None) == BRASIL
    assert scope_of("se", None) == Scope("regiao", "SE", "Sudeste")
    assert scope_of(None, "se") == Scope("uf", "SE", "Sergipe")


def test_scope_of_rejects_both_unknown_region_and_abroad() -> None:
    with pytest.raises(InvalidRecorteError):
        scope_of("NE", "PE")
    with pytest.raises(InvalidRecorteError):
        scope_of("XX", None)
    with pytest.raises(InvalidRecorteError):
        scope_of(None, "ZZ")
    with pytest.raises(InvalidUfError):
        scope_of(None, "QQ")


def test_all_scopes_are_brasil_five_regions_and_27_ufs() -> None:
    scopes = all_scopes()
    assert scopes[0] == BRASIL
    assert [s.tipo for s in scopes].count("regiao") == 5
    assert [s.tipo for s in scopes].count("uf") == 27
    assert all(s.codigo != "ZZ" for s in scopes)


def test_contains_and_subdivision_follow_the_scope() -> None:
    recife = Municipality("25313", "RECIFE (PE)", "PE", {13: 1})
    assert contains(BRASIL, recife)
    assert contains(Scope("regiao", "NE", "Nordeste"), recife)
    assert not contains(Scope("regiao", "SE", "Sudeste"), recife)
    assert contains(Scope("uf", "PE", "Pernambuco"), recife)
    assert subdivision_of(BRASIL, recife) == ("NE", "Nordeste")
    assert subdivision_of(Scope("regiao", "NE", "Nordeste"), recife) == ("PE", "Pernambuco")
    assert subdivision_of(Scope("uf", "PE", "Pernambuco"), recife) is None


def test_cargo_must_be_one_of_the_five() -> None:
    assert require_capillarity_cargo("deputadoEstadual") == "deputadoEstadual"
    with pytest.raises(InvalidCargoError):
        require_capillarity_cargo("prefeito")
```

- [x] **Step 2: Rodar e ver falhar.**
  Run: `uv run pytest tests/domain/test_capilaridade.py -q`
  Expected: `ModuleNotFoundError: No module named 'eleicoes.domain.capilaridade'` (erro de coleta, `1 error`).

- [x] **Step 3: Adicionar os erros** no fim de `src/eleicoes/domain/errors.py`:

```python
class InvalidRecorteError(ElectionError):
    def __init__(self) -> None:
        super().__init__(
            "Recorte inválido. Use regiao (NO, NE, CO, SE ou S) ou uf, não os dois."
        )


class EmptyRecorteError(ElectionError):
    def __init__(self, recorte: str, cargo: str) -> None:
        self.recorte = recorte
        self.cargo = cargo
        super().__init__(f"Não há municípios gravados para {cargo} no recorte {recorte}.")
```

- [x] **Step 4: Criar `src/eleicoes/domain/capilaridade.py`** (primeira parte):

```python
"""Where a party's votes come from among the municipalities of one scope. Pure and exact."""

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Final

from eleicoes.domain.errors import (
    InconsistentCellError,
    InvalidCargoError,
    InvalidRecorteError,
)
from eleicoes.domain.regiao import REGIONS, region_of
from eleicoes.domain.stored_grade import StoredCell
from eleicoes.domain.values import UF_NAMES, Uf, uf_name

CARGOS: Final[frozenset[str]] = frozenset(
    {"presidente", "governador", "senador", "deputadoFederal", "deputadoEstadual"}
)
ABROAD: Final = "ZZ"
PAIS: Final = "pais"
REGIAO: Final = "regiao"
UF: Final = "uf"
_MUNICIPIO: Final = "municipio"
_SUFFIX: Final = re.compile(r" \(([A-Z]{2})\)$")
# TSE codes of the 27 capitals, checked read-only in analise.relatorio_poder_linha on 2026-10-22.
CAPITAIS: Final[frozenset[str]] = frozenset(
    {
        "1392", "27855", "6050", "2550", "38490", "13897", "97012", "57053", "93734",
        "9210", "90670", "90514", "41238", "4278", "20516", "75353", "25313", "12190",
        "60011", "17612", "88013", "35", "3018", "81051", "71072", "31054", "73440",
    }
)


def require_capillarity_cargo(cargo: str) -> str:
    if cargo not in CARGOS:
        raise InvalidCargoError(cargo)
    return cargo


@dataclass(frozen=True, slots=True)
class Municipality:
    codigo: str
    nome: str
    uf: str
    votos: Mapping[int, int]
    validos: int = field(init=False)

    def __post_init__(self) -> None:
        copied = dict(self.votos)
        if any(count < 0 for count in copied.values()):
            raise InconsistentCellError()
        object.__setattr__(self, "votos", copied)
        object.__setattr__(self, "validos", sum(copied.values()))

    def of(self, partido: int) -> int:
        return self.votos.get(partido, 0)


@dataclass(frozen=True, slots=True)
class MunicipalSet:
    places: tuple[Municipality, ...]
    exterior: int


def places_from_cells(cells: Iterable[StoredCell]) -> MunicipalSet:
    grouped: dict[str, list[StoredCell]] = {}
    for cell in cells:
        if cell.nivel != _MUNICIPIO:
            raise InconsistentCellError()
        grouped.setdefault(cell.codigo, []).append(cell)
    built = tuple(_place(codigo, items) for codigo, items in grouped.items())
    kept = sorted((p for p in built if p.uf != ABROAD), key=lambda p: (p.nome.casefold(), p.codigo))
    return MunicipalSet(tuple(kept), len(built) - len(kept))


def _place(codigo: str, cells: list[StoredCell]) -> Municipality:
    nome = cells[0].nome
    if any(cell.nome != nome for cell in cells):
        raise InconsistentCellError()
    votos: dict[int, int] = {}
    for cell in cells:
        if cell.partido in votos:
            raise InconsistentCellError()
        votos[cell.partido] = cell.votos_nominais + cell.votos_legenda
    return Municipality(codigo, nome, uf_of(nome), votos)


def uf_of(nome: str) -> str:
    found = _SUFFIX.search(nome)
    if found is None:
        raise InconsistentCellError()
    return Uf(found.group(1)).code


@dataclass(frozen=True, slots=True)
class Scope:
    tipo: str
    codigo: str
    nome: str


BRASIL: Final = Scope(PAIS, "BR", "Brasil")


def scope_of(regiao: str | None, uf: str | None) -> Scope:
    if regiao is not None and uf is not None:
        raise InvalidRecorteError()
    if regiao is not None:
        return _region_scope(regiao)
    if uf is not None:
        return _uf_scope(uf)
    return BRASIL


def _region_scope(sigla: str) -> Scope:
    wanted = sigla.strip().upper()
    for region in REGIONS:
        if region.sigla == wanted:
            return Scope(REGIAO, region.sigla, region.name)
    raise InvalidRecorteError()


def _uf_scope(code: str) -> Scope:
    normalized = Uf(code).code
    if normalized == ABROAD:
        raise InvalidRecorteError()
    return Scope(UF, normalized, uf_name(normalized))


def all_scopes() -> tuple[Scope, ...]:
    regions = tuple(Scope(REGIAO, region.sigla, region.name) for region in REGIONS)
    codes = sorted(code for code in UF_NAMES if code != ABROAD)
    return (BRASIL, *regions, *(Scope(UF, code, uf_name(code)) for code in codes))


def contains(scope: Scope, place: Municipality) -> bool:
    if scope.tipo == PAIS:
        return True
    if scope.tipo == REGIAO:
        return region_of(place.uf).sigla == scope.codigo
    return place.uf == scope.codigo


def subdivision_of(scope: Scope, place: Municipality) -> tuple[str, str] | None:
    if scope.tipo == PAIS:
        region = region_of(place.uf)
        return region.sigla, region.name
    if scope.tipo == REGIAO:
        return place.uf, uf_name(place.uf)
    return None
```

- [x] **Step 5: Rodar até passar.**
  Run: `uv run pytest tests/domain/test_capilaridade.py -q`
  Expected: `8 passed`.
  Run: `uv run ruff check src/eleicoes/domain/capilaridade.py src/eleicoes/domain/errors.py tests/domain/test_capilaridade.py && uv run ruff format --check src/eleicoes/domain/capilaridade.py tests/domain/test_capilaridade.py`
  Expected: `All checks passed!` e `2 files already formatted`. Se `ruff format` quiser reformatar o bloco `CAPITAIS`, rode `uv run ruff format` nos dois arquivos e aceite o resultado.

**If Task Fails:**
1. `InvalidUfError` não vem de `Uf("QQ")`: confira o nome real em `domain/errors.py` (`class InvalidUfError`) e ajuste o import do teste.
2. `field(init=False)` com `slots=True` falha: troque por uma `@property validos` que faz `sum(self.votos.values())` e tire o `object.__setattr__` do `validos`.
3. Não conseguiu resolver: anote o erro e pare.

---

### Task 2: Métricas por partido (domínio)

**Files:**
- Modify: `src/eleicoes/domain/capilaridade.py` (segunda parte, no fim)
- Test: `tests/domain/test_capilaridade.py` (adicionar)

**Interfaces:**
- Produces:
  ```python
  PRESENCA: Final = Fraction(5, 100); DESTAQUES: Final = 5
  BAND_KEYS: Final[tuple[str, ...]]  # 7 chaves, na ordem do contrato
  @dataclass Share(municipios, votos, validos: int, parte, eleitorado: Fraction); .vezes -> Fraction
  @dataclass Subdivision(codigo: str, nome: str, share: Share)
  @dataclass Band(chave: str, municipios: int, validos: int, votos: int)
  @dataclass PlaceStrength(codigo, nome: str, votos, validos: int); .fatia -> Fraction
  @dataclass PartyMetrics(partido, votos, validos, validos_recorte, ufs_com_voto, municipios: int,
      indice: Fraction, top10: Share, presenca: int, capitais: Share | None,
      subdivisoes: tuple[Subdivision, ...], faixas: tuple[Band, ...],
      fortes: tuple[PlaceStrength, ...], maiores: tuple[PlaceStrength, ...])
      .fatia, .fatia_recorte, .presenca_parte -> Fraction
  def concentration_index(rows: Sequence[tuple[int, int]]) -> Fraction  # (validos, votos)
  def party_metrics(partido: int, scope: Scope, members: Sequence[Municipality]) -> PartyMetrics
  ```

- [x] **Step 1: Escrever os testes que falham** (adicionar ao arquivo e aos imports: `PRESENCA`, `PartyMetrics`, `concentration_index`, `party_metrics`):

```python
def test_index_is_zero_when_the_share_is_the_same_everywhere() -> None:
    assert concentration_index(((100, 10), (300, 30))) == 0


def test_index_is_one_minus_one_over_n_when_one_equal_place_has_every_vote() -> None:
    assert concentration_index(((100, 0), (100, 0), (100, 0), (100, 40))) == Fraction(3, 4)


def test_index_of_a_mixed_case_matches_the_hand_count() -> None:
    # sorted by share: (100, 0), (200, 20), (100, 50); C = 0, 20, 70
    # area = 100*(0+0) + 200*(0+20) + 100*(20+70) = 13000; T*P = 400*70
    assert concentration_index(((100, 50), (200, 20), (100, 0))) == Fraction(15, 28)


def test_index_without_votes_is_zero() -> None:
    assert concentration_index(((100, 0),)) == 0
    assert concentration_index(()) == 0


def _sp(codigo: str, a: int, b: int) -> Municipality:
    return Municipality(codigo, f"M{codigo} (SP)", "SP", {13: a, 22: b})


def test_metrics_of_the_mixed_case() -> None:
    members = (_sp("1", 50, 50), _sp("2", 20, 180), _sp("3", 0, 100))
    found = party_metrics(13, Scope("uf", "SP", "São Paulo"), members)
    assert (found.votos, found.validos, found.municipios, found.ufs_com_voto) == (70, 400, 3, 1)
    assert found.indice == Fraction(15, 28)
    assert found.top10.municipios == 1
    assert found.top10.parte == Fraction(5, 7)
    assert found.top10.eleitorado == Fraction(1, 4)
    assert found.top10.vezes == Fraction(20, 7)
    assert found.presenca == 2
    assert found.presenca_parte == Fraction(2, 3)
    assert [(b.chave, b.municipios, b.validos, b.votos) for b in found.faixas] == [
        ("zero", 1, 100, 0),
        ("ate_metade", 0, 0, 0),
        ("metade_a_media", 1, 200, 20),
        ("media_a_1_5", 0, 0, 0),
        ("1_5_a_2", 0, 0, 0),
        ("2_a_3", 1, 100, 50),
        ("3_ou_mais", 0, 0, 0),
    ]
    assert [p.codigo for p in found.fortes] == ["1", "2", "3"]
    assert [p.codigo for p in found.maiores] == ["1", "2"]
    assert found.capitais is None
    assert found.subdivisoes == ()


def test_band_edge_is_inclusive_at_the_mean() -> None:
    members = (_sp("1", 10, 90), _sp("2", 10, 90))
    found = party_metrics(13, Scope("uf", "SP", "São Paulo"), members)
    assert found.faixas[3].municipios == 2  # exactly 1x the mean falls in media_a_1_5


def test_presence_threshold_is_inclusive() -> None:
    members = (_sp("1", 5, 95), _sp("2", 4, 96))
    found = party_metrics(13, Scope("uf", "SP", "São Paulo"), members)
    assert PRESENCA == Fraction(5, 100)
    assert found.presenca == 1


def test_universe_keeps_only_the_ufs_where_the_party_had_votes() -> None:
    members = (
        Municipality("71072", "SÃO PAULO (SP)", "SP", {13: 10, 22: 90}),
        Municipality("60011", "RIO DE JANEIRO (RJ)", "RJ", {22: 100}),
        Municipality("9", "VAZIO (RJ)", "RJ", {22: 0}),
    )
    found = party_metrics(13, BRASIL, members)
    assert (found.ufs_com_voto, found.municipios, found.validos) == (1, 1, 100)
    assert found.validos_recorte == 200
    assert found.fatia == Fraction(1, 10)
    assert found.fatia_recorte == Fraction(1, 20)
    assert found.capitais is not None
    assert (found.capitais.municipios, found.capitais.parte) == (1, Fraction(1))
    sudeste = found.subdivisoes[0]
    assert (sudeste.codigo, sudeste.share.parte, sudeste.share.eleitorado) == (
        "SE", Fraction(1), Fraction(1),
    )


def test_top_count_rounds_up_and_is_at_least_one() -> None:
    members = tuple(_sp(str(i), i + 1, 100) for i in range(11))
    found = party_metrics(13, Scope("uf", "SP", "São Paulo"), members)
    assert found.top10.municipios == 2
    assert [p.codigo for p in found.fortes][:2] == ["10", "9"]
```

- [x] **Step 2: Rodar e ver falhar.**
  Run: `uv run pytest tests/domain/test_capilaridade.py -q`
  Expected: `ImportError: cannot import name 'concentration_index'` (erro de coleta).

- [x] **Step 3: Implementar** (adicionar a `capilaridade.py`, com os imports `from collections.abc import Sequence` e `from fractions import Fraction`):

```python
PRESENCA: Final = Fraction(5, 100)
DESTAQUES: Final = 5
BAND_KEYS: Final[tuple[str, ...]] = (
    "zero", "ate_metade", "metade_a_media", "media_a_1_5", "1_5_a_2", "2_a_3", "3_ou_mais",
)
_BAND_EDGES: Final[tuple[Fraction, ...]] = (
    Fraction(1, 2), Fraction(1), Fraction(3, 2), Fraction(2), Fraction(3),
)


def _ratio(numerator: int, denominator: int) -> Fraction:
    if denominator == 0:
        return Fraction(0)
    return Fraction(numerator, denominator)


@dataclass(frozen=True, slots=True)
class Share:
    municipios: int
    votos: int
    validos: int
    parte: Fraction
    eleitorado: Fraction

    @property
    def vezes(self) -> Fraction:
        if self.eleitorado == 0:
            return Fraction(0)
        return self.parte / self.eleitorado


@dataclass(frozen=True, slots=True)
class Subdivision:
    codigo: str
    nome: str
    share: Share


@dataclass(frozen=True, slots=True)
class Band:
    chave: str
    municipios: int
    validos: int
    votos: int


@dataclass(frozen=True, slots=True)
class PlaceStrength:
    codigo: str
    nome: str
    votos: int
    validos: int

    @property
    def fatia(self) -> Fraction:
        return _ratio(self.votos, self.validos)


@dataclass(frozen=True, slots=True)
class PartyMetrics:
    partido: int
    votos: int
    validos: int
    validos_recorte: int
    ufs_com_voto: int
    municipios: int
    indice: Fraction
    top10: Share
    presenca: int
    capitais: Share | None
    subdivisoes: tuple[Subdivision, ...]
    faixas: tuple[Band, ...]
    fortes: tuple[PlaceStrength, ...]
    maiores: tuple[PlaceStrength, ...]

    @property
    def fatia(self) -> Fraction:
        return _ratio(self.votos, self.validos)

    @property
    def fatia_recorte(self) -> Fraction:
        return _ratio(self.votos, self.validos_recorte)

    @property
    def presenca_parte(self) -> Fraction:
        return _ratio(self.presenca, self.municipios)


def concentration_index(rows: Sequence[tuple[int, int]]) -> Fraction:
    """Gini of the party's votes against valid votes, places sorted by the party's share."""
    total = sum(validos for validos, _votos in rows)
    party = sum(votos for _validos, votos in rows)
    if total == 0 or party == 0:
        return Fraction(0)
    ordered = sorted((row for row in rows if row[0] > 0), key=lambda row: Fraction(row[1], row[0]))
    cumulative = 0
    area = 0
    for validos, votos in ordered:
        previous = cumulative
        cumulative += votos
        area += validos * (previous + cumulative)
    return 1 - Fraction(area, total * party)


def share(rows: Sequence[Municipality], partido: int, party_total: int, valid_total: int) -> Share:
    votos = sum(place.of(partido) for place in rows)
    validos = sum(place.validos for place in rows)
    return Share(len(rows), votos, validos, _ratio(votos, party_total), _ratio(validos, valid_total))


def party_metrics(partido: int, scope: Scope, members: Sequence[Municipality]) -> PartyMetrics:
    counted = tuple(place for place in members if place.validos > 0)
    ufs = frozenset(place.uf for place in counted if place.of(partido) > 0)
    universe = tuple(place for place in counted if place.uf in ufs)
    votos = sum(place.of(partido) for place in universe)
    validos = sum(place.validos for place in universe)
    if votos == 0:
        raise InconsistentCellError()
    strong = _by_strength(universe, partido)
    return PartyMetrics(
        partido,
        votos,
        validos,
        sum(place.validos for place in counted),
        len(ufs),
        len(universe),
        concentration_index(tuple((place.validos, place.of(partido)) for place in universe)),
        share(strong[: _top_count(len(strong))], partido, votos, validos),
        sum(1 for place in universe if Fraction(place.of(partido), place.validos) >= PRESENCA),
        _capitals(universe, partido, votos, validos),
        _subdivisions(scope, counted, partido, votos),
        _bands(universe, partido, votos, validos),
        tuple(_strength(place, partido) for place in strong[:DESTAQUES]),
        _largest(universe, partido),
    )


def _top_count(total: int) -> int:
    return max(1, -(-total // 10))


def _by_strength(rows: Sequence[Municipality], partido: int) -> tuple[Municipality, ...]:
    def key(place: Municipality) -> tuple[Fraction, int, str]:
        return (-Fraction(place.of(partido), place.validos), -place.of(partido), place.codigo)

    return tuple(sorted(rows, key=key))


def _capitals(
    universe: Sequence[Municipality], partido: int, votos: int, validos: int
) -> Share | None:
    found = tuple(place for place in universe if place.codigo in CAPITAIS)
    if not found:
        return None
    return share(found, partido, votos, validos)


def _subdivisions(
    scope: Scope, counted: Sequence[Municipality], partido: int, votos: int
) -> tuple[Subdivision, ...]:
    total = sum(place.validos for place in counted)
    grouped: dict[tuple[str, str], list[Municipality]] = {}
    for place in counted:
        key = subdivision_of(scope, place)
        if key is not None:
            grouped.setdefault(key, []).append(place)
    built = (
        Subdivision(code, name, share(rows, partido, votos, total))
        for (code, name), rows in grouped.items()
    )
    return tuple(sorted(built, key=lambda item: (-item.share.parte, item.codigo)))


def _bands(
    universe: Sequence[Municipality], partido: int, votos: int, validos: int
) -> tuple[Band, ...]:
    counts = [[0, 0, 0] for _key in BAND_KEYS]
    for place in universe:
        slot = counts[_band_index(place.of(partido), place.validos, votos, validos)]
        slot[0] += 1
        slot[1] += place.validos
        slot[2] += place.of(partido)
    return tuple(
        Band(key, slot[0], slot[1], slot[2]) for key, slot in zip(BAND_KEYS, counts, strict=True)
    )


def _band_index(party: int, valid: int, party_total: int, valid_total: int) -> int:
    if party == 0:
        return 0
    relative = Fraction(party * valid_total, valid * party_total)
    return 1 + sum(1 for edge in _BAND_EDGES if relative >= edge)


def _largest(universe: Sequence[Municipality], partido: int) -> tuple[PlaceStrength, ...]:
    voted = (place for place in universe if place.of(partido) > 0)
    ordered = sorted(voted, key=lambda place: (-place.of(partido), place.codigo))
    return tuple(_strength(place, partido) for place in ordered[:DESTAQUES])


def _strength(place: Municipality, partido: int) -> PlaceStrength:
    return PlaceStrength(place.codigo, place.nome, place.of(partido), place.validos)
```

- [x] **Step 4: Rodar até passar.**
  Run: `uv run pytest tests/domain/test_capilaridade.py -q`
  Expected: `17 passed`.
  Run: `uv run ruff check src/eleicoes/domain/capilaridade.py tests/domain/test_capilaridade.py && uv run mypy`
  Expected: `All checks passed!` e `Success: no issues found in N source files`.

**If Task Fails:**
1. `test_top_count...` falha na ordem: o desempate é fatia decrescente, depois votos decrescentes, depois código. Com 11 municípios de 100 válidos para o 22, as fatias de "10" (11/111) e "9" (10/110) são as maiores.
2. `mypy` reclama do `Mapping` mutado em `__post_init__`: mantenha `votos: Mapping[int, int]` e grave `dict(...)` com `object.__setattr__`, como no Step 4 da Task 1.
3. Não conseguiu resolver: anote o erro e pare.

---

### Task 3: Classificação, visão por recorte, relatório e resumo (domínio)

**Files:**
- Create: `src/eleicoes/domain/capilaridade_classe.py`
- Test: `tests/domain/test_capilaridade_classe.py`

**Interfaces:**
- Consumes: tudo de `capilaridade.py`, mais `ElectionYear` e `Turno` (`values.py`), e `EmptyRecorteError` e `MissingPowerReportError` (`errors.py`).
- Produces:
  ```python
  POUCO_VOTO = Fraction(1, 100); MIN_MUNICIPIOS = 20; CAPITAIS_VEZES = Fraction(7, 4)
  REGIONAL_PARTE = Fraction(1, 2); REGIONAL_VEZES = Fraction(3, 2)
  POUCOS_PARTE = Fraction(1, 2); POUCOS_VEZES = Fraction(2)
  CLASSES: tuple[str, ...] = ("pouco_voto", "sem_base", "capitais", "regional", "poucos_municipios", "espalhado")
  UNRANKED: frozenset[str] = {"pouco_voto", "sem_base"}
  @dataclass Classification(classe: str, subdivisao: Subdivision | None = None)
  def classify(metrics: PartyMetrics) -> Classification
  @dataclass ClassifiedParty(metrics: PartyMetrics, classificacao: Classification)
  @dataclass CapillarityView(scope: Scope, municipios: int, ufs: int, sem_validos: int, validos: int, partidos: tuple[ClassifiedParty, ...])
  def build_view(scope: Scope, places: Sequence[Municipality]) -> CapillarityView | None
  @dataclass CapillarityReport(ano, turno: int, cargo: str, exterior: int, views: tuple[CapillarityView, ...]); .view(regiao, uf) -> CapillarityView
  def build_report(ano: int, turno: int, cargo: str, municipal: MunicipalSet) -> CapillarityReport
  @dataclass PartySummary(partido, votos: int, fatia, indice, presenca: Fraction, ufs_com_voto: int, classe: str); .indice_100 -> int
  def summarize(view: CapillarityView) -> tuple[PartySummary, ...]
  ```

- [x] **Step 1: Escrever os testes que falham** em `tests/domain/test_capilaridade_classe.py`:

```python
"""Capillarity classes: ordered rules, one boundary test per threshold."""

from dataclasses import replace
from fractions import Fraction

import pytest

from eleicoes.domain.capilaridade import (
    BRASIL,
    MunicipalSet,
    Municipality,
    PartyMetrics,
    Share,
    Subdivision,
)
from eleicoes.domain.capilaridade_classe import (
    build_report,
    build_view,
    classify,
    summarize,
)
from eleicoes.domain.errors import (
    EmptyRecorteError,
    InvalidRecorteError,
    MissingPowerReportError,
)
from eleicoes.domain.percentual import round_half_up


def _share(parte: Fraction, eleitorado: Fraction) -> Share:
    return Share(1, 1, 1, parte, eleitorado)


_BASE = PartyMetrics(
    partido=13, votos=10, validos=100, validos_recorte=100, ufs_com_voto=27, municipios=100,
    indice=Fraction(1, 5), top10=_share(Fraction(1, 5), Fraction(1, 10)), presenca=50,
    capitais=_share(Fraction(1, 4), Fraction(1, 4)),
    subdivisoes=(Subdivision("SE", "Sudeste", _share(Fraction(2, 5), Fraction(2, 5))),),
    faixas=(), fortes=(), maiores=(),
)


def test_spread_party_is_espalhado() -> None:
    assert classify(_BASE).classe == "espalhado"


def test_pouco_voto_boundary() -> None:
    assert classify(replace(_BASE, votos=99, validos=10_000)).classe == "pouco_voto"
    assert classify(replace(_BASE, votos=100, validos=10_000)).classe == "espalhado"


def test_sem_base_boundary() -> None:
    assert classify(replace(_BASE, municipios=19)).classe == "sem_base"
    assert classify(replace(_BASE, municipios=20)).classe == "espalhado"


def test_capitais_boundary_and_missing_capitals() -> None:
    at = replace(_BASE, capitais=_share(Fraction(7, 20), Fraction(1, 5)))
    below = replace(_BASE, capitais=_share(Fraction(34, 100), Fraction(1, 5)))
    assert classify(at).classe == "capitais"
    assert classify(below).classe == "espalhado"
    assert classify(replace(_BASE, capitais=None)).classe == "espalhado"


def test_regional_needs_half_of_the_votes_and_one_and_a_half_times_the_weight() -> None:
    nordeste = Subdivision("NE", "Nordeste", _share(Fraction(1, 2), Fraction(1, 3)))
    found = classify(replace(_BASE, subdivisoes=(nordeste,)))
    assert (found.classe, found.subdivisao) == ("regional", nordeste)
    short = Subdivision("NE", "Nordeste", _share(Fraction(49, 100), Fraction(1, 5)))
    assert classify(replace(_BASE, subdivisoes=(short,))).classe == "espalhado"
    light = Subdivision("SE", "Sudeste", _share(Fraction(3, 5), Fraction(41, 100)))
    assert classify(replace(_BASE, subdivisoes=(light,))).classe == "espalhado"


def test_poucos_municipios_needs_half_of_the_votes_and_twice_the_weight() -> None:
    at = replace(_BASE, top10=_share(Fraction(1, 2), Fraction(1, 4)))
    heavy = replace(_BASE, top10=_share(Fraction(1, 2), Fraction(26, 100)))
    assert classify(at).classe == "poucos_municipios"
    assert classify(heavy).classe == "espalhado"


def test_capitais_wins_over_regional_and_regional_over_poucos() -> None:
    nordeste = Subdivision("NE", "Nordeste", _share(Fraction(3, 5), Fraction(1, 4)))
    both = replace(
        _BASE,
        capitais=_share(Fraction(1, 2), Fraction(1, 4)),
        subdivisoes=(nordeste,),
        top10=_share(Fraction(3, 5), Fraction(1, 10)),
    )
    assert classify(both).classe == "capitais"
    assert classify(replace(both, capitais=None)).classe == "regional"


def _ac(codigo: str, a: int, b: int) -> Municipality:
    return Municipality(codigo, f"M{codigo} (AC)", "AC", {13: a, 22: b})


def test_view_ranks_classifiable_parties_first_then_by_index() -> None:
    places = tuple(_ac(str(i), 1 + (i % 2) * 50, 100) for i in range(30))
    places += (Municipality("99", "M99 (AC)", "AC", {44: 1, 22: 5_000}),)
    view = build_view(BRASIL, places)
    assert view is not None
    assert (view.municipios, view.ufs) == (31, 1)
    order = [item.metrics.partido for item in view.partidos]
    assert order[-1] == 44  # pouco_voto stays last
    assert view.partidos[-1].classificacao.classe == "pouco_voto"
    summary = summarize(view)
    assert [s.partido for s in summary] == order
    assert summary[0].indice_100 == round_half_up(view.partidos[0].metrics.indice * 100)


def test_report_picks_the_scope_and_reports_missing_ones() -> None:
    places = tuple(_ac(str(i), 10, 90) for i in range(25))
    report = build_report(2026, 1, "governador", MunicipalSet(places, 0))
    assert report.view(None, "AC").scope.codigo == "AC"
    assert report.view("NO", None).scope.nome == "Norte"
    with pytest.raises(EmptyRecorteError):
        report.view(None, "SP")
    with pytest.raises(InvalidRecorteError):
        report.view("NO", "AC")


def test_report_without_places_is_missing() -> None:
    with pytest.raises(MissingPowerReportError):
        build_report(2026, 1, "senador", MunicipalSet((), 3))
```

- [x] **Step 2: Rodar e ver falhar.**
  Run: `uv run pytest tests/domain/test_capilaridade_classe.py -q`
  Expected: `ModuleNotFoundError: No module named 'eleicoes.domain.capilaridade_classe'`.

- [x] **Step 3: Implementar `src/eleicoes/domain/capilaridade_classe.py`:**

```python
"""Readable spread class per party, the view per scope, and the summary the scoreboard reuses."""

from collections.abc import Sequence
from dataclasses import dataclass
from fractions import Fraction
from typing import Final

from eleicoes.domain.capilaridade import (
    MunicipalSet,
    Municipality,
    PartyMetrics,
    Scope,
    Subdivision,
    all_scopes,
    contains,
    party_metrics,
    require_capillarity_cargo,
    scope_of,
)
from eleicoes.domain.errors import EmptyRecorteError, MissingPowerReportError
from eleicoes.domain.percentual import round_half_up
from eleicoes.domain.values import ElectionYear, Turno

POUCO_VOTO: Final = Fraction(1, 100)
MIN_MUNICIPIOS: Final = 20
CAPITAIS_VEZES: Final = Fraction(7, 4)
REGIONAL_PARTE: Final = Fraction(1, 2)
REGIONAL_VEZES: Final = Fraction(3, 2)
POUCOS_PARTE: Final = Fraction(1, 2)
POUCOS_VEZES: Final = Fraction(2)
CLASSES: Final[tuple[str, ...]] = (
    "pouco_voto", "sem_base", "capitais", "regional", "poucos_municipios", "espalhado",
)
UNRANKED: Final[frozenset[str]] = frozenset({"pouco_voto", "sem_base"})


@dataclass(frozen=True, slots=True)
class Classification:
    classe: str
    subdivisao: Subdivision | None = None


def classify(metrics: PartyMetrics) -> Classification:
    if metrics.fatia < POUCO_VOTO:
        return Classification("pouco_voto")
    if metrics.municipios < MIN_MUNICIPIOS:
        return Classification("sem_base")
    capitals = metrics.capitais
    if capitals is not None and capitals.vezes >= CAPITAIS_VEZES:
        return Classification("capitais")
    dominant = _dominant(metrics.subdivisoes)
    if dominant is not None:
        return Classification("regional", dominant)
    top = metrics.top10
    if top.parte >= POUCOS_PARTE and top.vezes >= POUCOS_VEZES:
        return Classification("poucos_municipios")
    return Classification("espalhado")


def _dominant(items: Sequence[Subdivision]) -> Subdivision | None:
    for item in items:
        if item.share.parte >= REGIONAL_PARTE and item.share.vezes >= REGIONAL_VEZES:
            return item
    return None


@dataclass(frozen=True, slots=True)
class ClassifiedParty:
    metrics: PartyMetrics
    classificacao: Classification


@dataclass(frozen=True, slots=True)
class CapillarityView:
    scope: Scope
    municipios: int
    ufs: int
    sem_validos: int
    validos: int
    partidos: tuple[ClassifiedParty, ...]


def build_view(scope: Scope, places: Sequence[Municipality]) -> CapillarityView | None:
    members = tuple(place for place in places if contains(scope, place))
    if not members:
        return None
    counted = tuple(place for place in members if place.validos > 0)
    parties = sorted({party for place in counted for party, n in place.votos.items() if n > 0})
    built = (_classified(party, scope, members) for party in parties)
    ranked = tuple(sorted(built, key=_rank_key))
    validos = sum(place.validos for place in counted)
    ufs = len({place.uf for place in counted})
    missing = len(members) - len(counted)
    return CapillarityView(scope, len(counted), ufs, missing, validos, ranked)


def _classified(partido: int, scope: Scope, members: Sequence[Municipality]) -> ClassifiedParty:
    metrics = party_metrics(partido, scope, members)
    return ClassifiedParty(metrics, classify(metrics))


def _rank_key(item: ClassifiedParty) -> tuple[bool, Fraction, int]:
    unranked = item.classificacao.classe in UNRANKED
    return (unranked, -item.metrics.indice, item.metrics.partido)


@dataclass(frozen=True, slots=True)
class CapillarityReport:
    ano: int
    turno: int
    cargo: str
    exterior: int
    views: tuple[CapillarityView, ...]

    def view(self, regiao: str | None, uf: str | None) -> CapillarityView:
        scope = scope_of(regiao, uf)
        for item in self.views:
            if item.scope == scope:
                return item
        raise EmptyRecorteError(scope.nome, self.cargo)


def build_report(ano: int, turno: int, cargo: str, municipal: MunicipalSet) -> CapillarityReport:
    year = ElectionYear(ano).value
    turn = Turno(turno).value
    office = require_capillarity_cargo(cargo)
    if not municipal.places:
        raise MissingPowerReportError(office)
    built = (build_view(scope, municipal.places) for scope in all_scopes())
    views = tuple(view for view in built if view is not None)
    return CapillarityReport(year, turn, office, municipal.exterior, views)


@dataclass(frozen=True, slots=True)
class PartySummary:
    partido: int
    votos: int
    fatia: Fraction
    indice: Fraction
    presenca: Fraction
    ufs_com_voto: int
    classe: str

    @property
    def indice_100(self) -> int:
        return round_half_up(self.indice * 100)


def summarize(view: CapillarityView) -> tuple[PartySummary, ...]:
    return tuple(
        PartySummary(
            item.metrics.partido,
            item.metrics.votos,
            item.metrics.fatia,
            item.metrics.indice,
            item.metrics.presenca_parte,
            item.metrics.ufs_com_voto,
            item.classificacao.classe,
        )
        for item in view.partidos
    )
```

- [x] **Step 4: Rodar até passar.**
  Run: `uv run pytest tests/domain/test_capilaridade_classe.py tests/domain/test_capilaridade.py -q`
  Expected: `27 passed`.
  Run: `uv run ruff check src/eleicoes/domain tests/domain && uv run mypy`
  Expected: `All checks passed!` e `Success: no issues found`.

**If Task Fails:**
1. `test_view_ranks...` falha porque o partido 44 não é `pouco_voto`: 44 tem 1 voto em 5.001 válidos no universo (AC), ou seja, < 1%. Confira se `fatia` usa `validos` do universo.
2. `test_report_picks...`: o recorte `NO` existe porque AC é do Norte. `SP` não tem lugares, então `build_view` devolve `None` e `view()` levanta `EmptyRecorteError`.
3. Não conseguiu resolver: anote o erro e pare.

---

### Task 4: Code Review

1. **REQUIRED SUB-SKILL:** Use jarvis:codereview e despache os revisores em paralelo sobre `src/eleicoes/domain/capilaridade*.py`, `src/eleicoes/domain/errors.py` e `tests/domain/test_capilaridade*.py`.
2. Foco: a fórmula (D5) contra os três vetores à mão, a precedência (D10), o universo (D4), nenhum `float`, e a complexidade ≤ 10.
3. Trate os achados conforme as regras de severidade de jarvis:codereview. Siga só com zero Critical/High/Medium.

---

### Task 5: Porta e leitor das linhas municipais

**Files:**
- Create: `src/eleicoes/ports/capilaridade.py`
- Modify: `src/eleicoes/adapters/postgres_perfis.py` (método `municipal_cells`, função `municipal_statement`, `_cell` e a constante `_CELL_WIDTH = 6`)
- Test: `tests/adapters/test_postgres_perfis.py` (adicionar)

**Interfaces:**
- Produces:
  ```python
  class MunicipalCellSource(Protocol):
      def municipal_cells(self, ano: int, turno: int, cargo: str) -> tuple[StoredCell, ...]: ...
      def close(self) -> None: ...
  # PostgresStoredLines.municipal_cells(ano, turno, cargo) -> tuple[StoredCell, ...]
  def municipal_statement(ano: int, turno: int, cargo: str) -> Executable
  ```

- [x] **Step 1: Escrever o teste que falha** (adicionar a `tests/adapters/test_postgres_perfis.py`, com o import `from eleicoes.domain.stored_grade import StoredCell`):

```python
def test_municipal_cells_is_one_select_on_the_municipal_level_only() -> None:
    session = ScriptedSession()
    session.push(("1392", "RIO BRANCO (AC)", 100, 13, 10, 2))
    reader = PostgresStoredLines(lambda: session)

    found = reader.municipal_cells(2026, 1, "deputadoFederal")

    assert found == (StoredCell("municipio", "1392", "RIO BRANCO (AC)", 100, 13, 10, 2),)
    selects = [item for _begin, item in session.executed if isinstance(item, Select)]
    assert len(selects) == 1
    compiled = selects[0].compile(dialect=postgresql.dialect())
    sql = str(compiled).lower()
    assert "analise.relatorio_poder_linha" in sql
    assert "cedula" not in sql
    assert "raw." not in sql
    assert "boletim" not in sql
    assert _bound(compiled.params) >= {"deputadoFederal", "municipio"}
    reader.close()
    assert session.closed == 1


def test_municipal_cells_rejects_a_short_row() -> None:
    session = ScriptedSession()
    session.push(("1392", "RIO BRANCO (AC)", 100, 13, 10))
    reader = PostgresStoredLines(lambda: session)
    with pytest.raises(InconsistentCellError):
        reader.municipal_cells(2026, 1, "senador")
```

- [x] **Step 2: Rodar e ver falhar.**
  Run: `uv run pytest tests/adapters/test_postgres_perfis.py -q -k municipal_cells`
  Expected: `2 failed` com `AttributeError: 'PostgresStoredLines' object has no attribute 'municipal_cells'`.

- [x] **Step 3: Implementar.** `src/eleicoes/ports/capilaridade.py`:

```python
"""Port for the stored municipal cells the capillarity report reads."""

from typing import Protocol

from eleicoes.domain.stored_grade import StoredCell


class MunicipalCellSource(Protocol):
    def municipal_cells(self, ano: int, turno: int, cargo: str) -> tuple[StoredCell, ...]: ...

    def close(self) -> None: ...
```

  Em `postgres_perfis.py`, adicionar à classe, depois de `municipal_ufs`:

```python
    def municipal_cells(self, ano: int, turno: int, cargo: str) -> tuple[StoredCell, ...]:
        return self._guard(lambda: self._cells(ano, turno, cargo))
```

  Adicionar, depois de `_ufs`:

```python
    def _cells(self, ano: int, turno: int, cargo: str) -> tuple[StoredCell, ...]:
        with self._open().begin():
            fetched = self._open().execute(municipal_statement(ano, turno, cargo)).all()
        return tuple(_cell(_as_tuple(row)) for row in fetched)
```

  Adicionar, como funções de módulo (com `from eleicoes.domain.stored_grade import StoredCell` e `_CELL_WIDTH = 6` junto das outras constantes):

```python
def municipal_statement(ano: int, turno: int, cargo: str) -> Executable:
    return select(
        PowerReportLine.codigo,
        PowerReportLine.nome,
        PowerReportLine.comparecimento,
        PowerReportLine.partido,
        PowerReportLine.votos_nominais,
        PowerReportLine.votos_legenda,
    ).where(
        PowerReportLine.ano == ano,
        PowerReportLine.turno == turno,
        PowerReportLine.cargo == cargo,
        PowerReportLine.nivel == _MUNICIPIO,
    )


def _cell(row: tuple[object, ...]) -> StoredCell:
    if len(row) != _CELL_WIDTH:
        raise InconsistentCellError()
    return StoredCell(
        _MUNICIPIO,
        _text(row[0]),
        _text(row[1]),
        _count(row[2]),
        _count(row[3]),
        _count(row[4]),
        _count(row[5]),
    )
```

- [x] **Step 4: Rodar até passar.**
  Run: `uv run pytest tests/adapters/test_postgres_perfis.py -q`
  Expected: todos passam (os existentes mais 2).
  Run: `uv run ruff check src/eleicoes/ports/capilaridade.py src/eleicoes/adapters/postgres_perfis.py && uv run mypy`
  Expected: `All checks passed!` e `Success`.

**If Task Fails:**
1. `_bound` não existe no arquivo de teste: ele está no fim de `test_postgres_perfis.py`. Se o nome for outro, use o helper que já compara `compiled.params`.
2. `StoredCell` rejeita o valor: o `__post_init__` valida contagens, então use dados não negativos no teste.
3. Não conseguiu resolver: anote o erro e pare.

---

### Task 6: Caso de uso e job com cache

**Files:**
- Create: `src/eleicoes/use_cases/apresentar_capilaridade.py`
- Modify: `src/eleicoes/adapters/http/dependencies.py` (`CapillarityJob`, `get_capillarity_job`, `_stored_capillarity` e uma linha em `clear_report_caches`)
- Test: `tests/use_cases/test_apresentar_capilaridade.py` e `tests/adapters/test_relatorios_capilaridade.py` (só os testes do job, nesta task)

**Interfaces:**
- Produces:
  ```python
  def build_capillarity(reader: MunicipalCellSource, ano: int, turno: int, cargo: str) -> CapillarityReport
  def _production_reader() -> MunicipalCellSource   # same as apresentar_perfis
  CapillarityJob: TypeAlias = Callable[[int, int, str], CapillarityReport]
  def get_capillarity_job() -> CapillarityJob
  ```

- [x] **Step 1: Escrever os testes que falham.** `tests/use_cases/test_apresentar_capilaridade.py`:

```python
"""Capillarity use case: validates first, reads once, 409 without stored cells."""

import pytest

from eleicoes.domain.errors import InvalidCargoError, InvalidTurnoError, MissingPowerReportError
from eleicoes.domain.stored_grade import StoredCell
from eleicoes.use_cases.apresentar_capilaridade import build_capillarity


class _Cells:
    def __init__(self, cells: tuple[StoredCell, ...]) -> None:
        self.cells = cells
        self.calls: list[tuple[int, int, str]] = []

    def municipal_cells(self, ano: int, turno: int, cargo: str) -> tuple[StoredCell, ...]:
        self.calls.append((ano, turno, cargo))
        return self.cells

    def close(self) -> None:
        return None


def _cells() -> tuple[StoredCell, ...]:
    return tuple(
        StoredCell("municipio", str(i), f"M{i} (AC)", 100, partido, votos, 0)
        for i in range(25)
        for partido, votos in ((13, 10 + i), (22, 90 - i))
    )


def test_builds_every_scope_from_one_read() -> None:
    reader = _Cells(_cells())
    report = build_capillarity(reader, 2026, 1, "governador")
    assert reader.calls == [(2026, 1, "governador")]
    assert report.view(None, None).municipios == 25
    assert report.view(None, "AC").scope.nome == "Acre"


def test_without_cells_is_missing_power_report() -> None:
    with pytest.raises(MissingPowerReportError):
        build_capillarity(_Cells(()), 2026, 1, "senador")


def test_validates_before_reading() -> None:
    reader = _Cells(_cells())
    with pytest.raises(InvalidCargoError):
        build_capillarity(reader, 2026, 1, "prefeito")
    with pytest.raises(InvalidTurnoError):
        build_capillarity(reader, 2026, 9, "senador")
    assert reader.calls == []
```

  Em `tests/adapters/test_relatorios_capilaridade.py`, comece com os testes do job (copiar o padrão de `test_stored_profile_job_builds_once_per_key` e `..._does_not_cache_an_error` de `test_relatorios_agrupamentos.py`). Monkeypatch em `"eleicoes.use_cases.apresentar_capilaridade._production_reader"`:
  - `test_capillarity_job_builds_once_per_key_and_closes_the_reader`: dois `get_capillarity_job()(2026, 1, "governador")` devolvem o mesmo objeto (`is`), abrem um leitor só e esse leitor fica `closed is True`. Outro cargo abre um segundo leitor.
  - `test_capillarity_job_does_not_cache_an_error`: `_production_reader` levanta `ElectionError`. Duas chamadas levantam erro e o contador vale 2.
  - `test_clear_report_caches_drops_the_capillarity_cache`: chamar, depois `clear_report_caches()`, depois chamar de novo. O resultado é outro objeto.

- [x] **Step 2: Rodar e ver falhar.**
  Run: `uv run pytest tests/use_cases/test_apresentar_capilaridade.py tests/adapters/test_relatorios_capilaridade.py -q`
  Expected: `ModuleNotFoundError: No module named 'eleicoes.use_cases.apresentar_capilaridade'`.

- [x] **Step 3: Implementar.** `src/eleicoes/use_cases/apresentar_capilaridade.py`:

```python
"""Capillarity report from the stored municipal cells. No ballot is read."""

import os
from collections.abc import Mapping

from dotenv import load_dotenv

from eleicoes.domain.capilaridade import places_from_cells, require_capillarity_cargo
from eleicoes.domain.capilaridade_classe import CapillarityReport, build_report
from eleicoes.domain.errors import MissingPowerReportError
from eleicoes.domain.values import ElectionYear, Turno
from eleicoes.ports.capilaridade import MunicipalCellSource


def build_capillarity(
    reader: MunicipalCellSource,
    ano: int,
    turno: int,
    cargo: str,
) -> CapillarityReport:
    year = ElectionYear(ano).value
    turn = Turno(turno).value
    office = require_capillarity_cargo(cargo)
    cells = reader.municipal_cells(year, turn, office)
    if not cells:
        raise MissingPowerReportError(office)
    return build_report(year, turn, office, places_from_cells(cells))


def _production_reader() -> MunicipalCellSource:
    from eleicoes.adapters.orm.sessions import open_sync_session
    from eleicoes.adapters.postgres_perfis import PostgresStoredLines
    from eleicoes.composition.correspondencia import _host_settings

    settings = _host_settings(_environment())
    return PostgresStoredLines(lambda: open_sync_session(settings))


def _environment() -> Mapping[str, str]:
    load_dotenv()
    return os.environ
```

  Em `dependencies.py`, junto de `ProfileJob` e `ClassJob`:

```python
CapillarityJob: TypeAlias = Callable[[int, int, str], CapillarityReport]
_CAPILLARITY_REPORTS: Final = 16


def get_capillarity_job() -> CapillarityJob:
    return _stored_capillarity


@lru_cache(maxsize=_CAPILLARITY_REPORTS)
def _stored_capillarity(ano: int, turno: int, cargo: str) -> CapillarityReport:
    from eleicoes.use_cases.apresentar_capilaridade import _production_reader, build_capillarity

    reader = _production_reader()
    try:
        return build_capillarity(reader, ano, turno, cargo)
    finally:
        reader.close()
```

  Adicionar o import `from eleicoes.domain.capilaridade_classe import CapillarityReport` e a linha `_stored_capillarity.cache_clear()` em `clear_report_caches()`.

- [x] **Step 4: Rodar até passar.**
  Run: `uv run pytest tests/use_cases/test_apresentar_capilaridade.py tests/adapters/test_relatorios_capilaridade.py -q`
  Expected: `6 passed`.
  Run: `uv run ruff check src tests && uv run mypy`
  Expected: `All checks passed!` e `Success`.

**If Task Fails:**
1. O `conftest.py` limpa os caches com `clear_report_caches`. Se o teste do job vazar entre casos, confira se a linha `cache_clear()` foi adicionada.
2. `lru_cache` guardou um erro: não guarda, porque exceções não entram no cache. Se o contador não for 2, o monkeypatch está no módulo errado.
3. Não conseguiu resolver: anote o erro e pare.

---

### Task 7: JSON, rota e erros HTTP

**Files:**
- Create: `src/eleicoes/adapters/http/schemas_capilaridade.py`
- Modify: `src/eleicoes/adapters/http/relatorios.py` (rota nova no fim, o import de `get_capillarity_job` e o alias `CapillarityBuild`)
- Modify: `src/eleicoes/adapters/http/errors.py` (`InvalidRecorteError` → 422 e `EmptyRecorteError` → 409, em `_OWN_TEXT`)
- Modify: `tests/adapters/test_read_api.py` (`"/relatorios/dados/capilaridade"` no conjunto `expected`)
- Test: `tests/adapters/test_relatorios_capilaridade.py` (adicionar)

**Interfaces:**
- Produces:
  ```python
  class CapilaridadeJson(BaseModel):
      @classmethod
      def from_domain(cls, report: CapillarityReport, view: CapillarityView) -> Self
  def rotulo_classe(classe: str, scope: Scope, subdivisao: Subdivision | None) -> str
  def motivo(party: ClassifiedParty) -> str
  def format_times(value: Fraction) -> str   # "2,17", half-up
  NOTES: tuple[str, ...]
  # route
  @router.get("/relatorios/dados/capilaridade", summary="Capilaridade partidária", description=_CAPILARIDADE)
  async def capilaridade(ano: int, turno: int, cargo: str, build: CapillarityBuild,
                         regiao: str | None = None, uf: str | None = None) -> CapilaridadeJson
  ```
  Corpo da rota: `report = await asyncio.to_thread(build, ano, turno, cargo)`; `view = report.view(regiao, uf)`; `return CapilaridadeJson.from_domain(report, view)`.
  `_CAPILARIDADE = "Exige ano, turno e cargo. regiao (NO, NE, CO, SE, S) ou uf recorta; sem os dois, é o Brasil. Lê só as células municipais gravadas do relatório de poder; sem elas, responde 409."`

- [x] **Step 1: Escrever os testes que falham** em `tests/adapters/test_relatorios_capilaridade.py`. O app é `create_app(ports=_read_ports())` (importado de `tests.adapters.test_read_api`, como em `test_relatorios_agrupamentos.py`), com `application.dependency_overrides[get_capillarity_job] = lambda: job`, onde `job` chama `build_capillarity` com o fake `_Cells` da Task 6. Os dados de exemplo: 25 municípios no AC (`M{i} (AC)`, 13 e 22) e 25 em PE, mais Rio Branco `"1392"` com o partido 50 forte. Casos:
  - `test_capilaridade_brasil_has_the_contract_fields`: 200. As chaves de topo são `{"ano","turno","cargo","recorte","municipios","ufs","sem_validos","votos_validos","exterior","limites","partidos","resumo","notas"}`. `recorte == {"tipo": "pais", "codigo": "BR", "nome": "Brasil"}`. Cada `partidos[i]` tem 7 `faixas` com as chaves na ordem do contrato. `[r["partido"] for r in resumo] == [p["partido"] for p in partidos]`. `limites["capitais_vezes"] == "1,75"`. `notas == list(NOTES)`.
  - `test_capilaridade_regional_label_and_reason_are_exact`: um partido que só tem voto no AC, no recorte Brasil, sai com `classe == "regional"`, `rotulo_classe == "Regional (Norte)"` e `motivo` começando por `"Norte deu "`.
  - `test_capilaridade_uf_scope_has_no_subdivisions_and_uf_labels`: `?uf=AC` dá `subdivisoes == []` e o espalhado sai `"Espalhado pelo estado"`.
  - `test_capilaridade_both_scopes_is_422`: `?regiao=NE&uf=PE` dá 422 com `detail` igual ao texto de `InvalidRecorteError`.
  - `test_capilaridade_abroad_is_422_and_unknown_uf_is_422`: `uf=ZZ` dá o texto do recorte, e `uf=QQ` dá `"UF inválida."`.
  - `test_capilaridade_missing_scope_is_409`: `?uf=SP` dá 409 com `"Não há municípios gravados para governador no recorte São Paulo."`.
  - `test_capilaridade_without_cells_is_409_with_the_power_hint`: o fake vazio dá 409 com o texto de `MissingPowerReportError("governador")`.
  - `test_capilaridade_bad_cargo_is_422`: `cargo=prefeito` dá 422 `"Cargo inválido."`.
  - `test_format_times_rounds_half_up`: `format_times(Fraction(2175, 1000)) == "2,18"`, `format_times(Fraction(7, 4)) == "1,75"` e `format_times(Fraction(0)) == "0,00"`.
  - `test_motivo_uses_vez_below_two`: com `capitais.vezes = 7/4`, o texto tem `"1,75 vez o peso"`. Com 2, tem `"2,00 vezes o peso"`.

- [x] **Step 2: Rodar e ver falhar.**
  Run: `uv run pytest tests/adapters/test_relatorios_capilaridade.py -q`
  Expected: os testes da Task 6 passam e os novos falham com `ModuleNotFoundError: ... schemas_capilaridade` ou com `404`.

- [x] **Step 3: Implementar `schemas_capilaridade.py`.** Os modelos Pydantic são `RecorteJson`, `LimitesJson`, `ParteJson` (municipios, votos, parte, parte_texto, eleitorado, eleitorado_texto, vezes), `PresencaJson`, `SubdivisaoJson` (codigo, nome + campos de `ParteJson`), `FaixaJson`, `LugarJson`, `PartidoCapilaridadeJson`, `ResumoCapilaridadeJson` e `CapilaridadeJson`. Os campos e nomes são os do "Contrato JSON". Regras:
  - Fração: `str(value)`. Percentual: `format_percent(value)`. Índice: `format_decimal(float(indice))` e `round_half_up(indice * 100)`. Use `format_decimal` só para o texto. A fração exata vai em `indice`.
  - `format_times(value)`: `scaled = round_half_up(value * 100)`, `whole, cents = divmod(scaled, 100)`, `return f"{format_integer(whole)},{cents:02d}"`.
  - `rotulo_classe` e `motivo` seguem as tabelas do contrato. `motivo` usa `vez` quando `format_times(...)` começa com `"1,"`, e `vezes` nos demais casos.
  - `limites` vem das constantes de `capilaridade_classe.py` e de `PRESENCA`, nunca de literais.
  - `NOTES` com as 4 notas do contrato.
  - Para manter a complexidade ≤ 10, use um dicionário `classe → função de motivo` em vez de um `if` encadeado.

  Em `relatorios.py`:

```python
CapillarityBuild = Annotated[CapillarityJob, Depends(get_capillarity_job)]


@router.get(
    "/relatorios/dados/capilaridade",
    summary="Capilaridade partidária",
    description=_CAPILARIDADE,
)
async def capilaridade(
    ano: int,
    turno: int,
    cargo: str,
    build: CapillarityBuild,
    regiao: str | None = None,
    uf: str | None = None,
) -> CapilaridadeJson:
    report = await asyncio.to_thread(build, ano, turno, cargo)
    return CapilaridadeJson.from_domain(report, report.view(regiao, uf))
```

  Em `errors.py`, importe `InvalidRecorteError` e `EmptyRecorteError` e adicione `(InvalidRecorteError, 422)` e `(EmptyRecorteError, 409)` em `_OWN_TEXT`.

- [x] **Step 4: Rodar a suíte toda.**
  Run: `uv run pytest -q`
  Expected: tudo passa, sem `failed` e sem `error`.
  Run: `uv run ruff check src tests && uv run ruff format --check src tests && uv run mypy`
  Expected: `All checks passed!`, `... files already formatted`, `Success: no issues found`.

**If Task Fails:**
1. 500 em vez de 422/409: a classe nova não entrou em `_OWN_TEXT` ou foi importada de outro módulo.
2. Pydantic reclama de `Fraction`: todos os campos de razão são `str`. Converta em `from_domain`.
3. Complexidade > 10 em `from_domain`: separe em `_partido(item, scope)`, `_parte(share)`, `_faixa(band)` e `_lugar(place)`.
4. Não conseguiu resolver: anote o erro e pare.

---

### Task 8: Code Review e conferência com dados reais

1. **REQUIRED SUB-SKILL:** Use jarvis:codereview e despache os revisores em paralelo sobre o diff do backend (Tasks 5–7).
2. Siga só com zero Critical/High/Medium.
3. Conferência com o banco real (só leitura; a API precisa estar rodando com `.env`):
   - [ ] Subir a API local: `uv run uvicorn eleicoes.composition.api:app --port 8000`. O `_host_settings` de `composition/correspondencia.py` já troca `POSTGRES_HOST=postgres` por `127.0.0.1:$POSTGRES_PUBLISH_PORT` quando o nome do compose não resolve. O serviço `api` do `docker-compose.yml` usa o mesmo `eleicoes.composition.api:app`, mas na porta `${API_PORT:-15000}` e com a imagem reconstruída.
   - [ ] `time curl -s "http://localhost:8000/relatorios/dados/capilaridade?ano=2026&turno=1&cargo=deputadoFederal" -o /tmp/cap.json -w "%{http_code}\n"`
     Expected: `200`. A primeira chamada leva alguns segundos e a segunda menos de 1 s (cache).
   - [x] `python3 -c "import json,collections;d=json.load(open('/tmp/cap.json'));print(d['municipios'],collections.Counter(p['classe'] for p in d['partidos']))"`
     Expected: `5571` e a contagem da linha deputadoFederal da tabela de calibração (`espalhado 9, regional 6, capitais 1, poucos_municipios 2, pouco_voto 10`). Repita para os 5 cargos. Diferença de no máximo 1 partido por classe vem de desempate. Qualquer diferença maior é bug: pare e investigue.
   - [x] `curl -s ".../capilaridade?ano=2026&turno=1&cargo=deputadoEstadual&uf=DF" -w "%{http_code}\n"` dá `409`. `cargo=presidente` dá `"exterior": 117`.
   - [x] Para PT 13 no presidente, `indice_texto` é `"0,1960"` ± 0,0005 (calibração: 0,196).

   - Executado em 2026-10-22 sem subir a API: um script só de leitura chamou `build_capillarity` + `CapilaridadeJson.from_domain` com o `.env` real. As contagens por classe batem exatamente com a tabela de calibração nos 5 cargos; presidente tem `exterior` 117 e 5.571 municípios; PT 13 presidente `indice_texto` "0,1957"; deputadoEstadual `uf=DF` dá 409. Tempo do job (todos os recortes, sem cache): 3,3 a 7,4 s por cargo. Os passos de API e curl ficam para o orquestrador.

---

### Task 9: Tipos e busca no frontend

**Files:**
- Create: `frontend/src/lib/capilaridade.ts`: só tipos e constantes, **sem nenhum import de runtime**, para o script de verificação carregar com `node --experimental-strip-types`. `relatorios.ts` e `eleicoes.ts` importam `@/lib/...`, que o Node não resolve.
- Create: `frontend/src/lib/ler-capilaridade.ts`: leitor do JSON, opções de recorte e leitura da consulta. Importa `@/lib/relatorios`, `@/lib/eleicoes` e `./capilaridade`.
- Modify: `frontend/src/lib/relatorios.ts` (só `export` diante de `exigirLista`, `exigirRegistro`, `exigirTexto`, `exigirTextoOuNulo` e `exigirInteiro`)
- Modify: `frontend/src/lib/buscar-relatorios.ts` (adicionar `buscarCapilaridade`, que importa `lerCapilaridade` de `@/lib/ler-capilaridade`)

**Interfaces:**
- Produces:
  ```ts
  export type Recorte = { tipo: "pais" | "regiao" | "uf"; codigo: string; nome: string };
  export type ParteCapilaridade = { municipios: number; votos: number; parte: string; parte_texto: string;
    eleitorado: string; eleitorado_texto: string; vezes: string };
  export type SubdivisaoCapilaridade = ParteCapilaridade & { codigo: string; nome: string };
  export type FaixaCapilaridade = { chave: ChaveFaixa; municipios: number; votos_validos: number; votos: number };
  export type LugarCapilaridade = { codigo: string; nome: string; votos: number; votos_validos: number; fatia: string; fatia_texto: string };
  export type PartidoCapilaridade = { partido: number; votos: number; votos_validos: number; votos_validos_recorte: number;
    fatia: string; fatia_texto: string; fatia_recorte_texto: string; ufs_com_voto: number; municipios: number;
    indice: string; indice_texto: string; indice_100: number; top10: ParteCapilaridade;
    presenca: { municipios: number; parte: string; parte_texto: string }; capitais: ParteCapilaridade | null;
    subdivisoes: SubdivisaoCapilaridade[]; faixas: FaixaCapilaridade[]; fortes: LugarCapilaridade[];
    maiores: LugarCapilaridade[]; classe: ClasseCapilaridade; rotulo_classe: string; motivo: string };
  export type ResumoCapilaridade = { partido: number; votos: number; fatia: string; fatia_texto: string; indice: string;
    indice_100: number; presenca: string; presenca_texto: string; ufs_com_voto: number; classe: ClasseCapilaridade; rotulo_classe: string };
  export type RelatorioCapilaridade = { ano: number; turno: number; cargo: string; recorte: Recorte; municipios: number; ufs: number;
    sem_validos: number; votos_validos: number; exterior: number; limites: Record<string, string | number>;
    partidos: PartidoCapilaridade[]; resumo: ResumoCapilaridade[]; notas: string[] };
  export const CHAVES_FAIXA = ["zero","ate_metade","metade_a_media","media_a_1_5","1_5_a_2","2_a_3","3_ou_mais"] as const;
  export const CLASSES_CAPILARIDADE = ["pouco_voto","sem_base","capitais","regional","poucos_municipios","espalhado"] as const;
  export const NAO_RANQUEADAS: ReadonlySet<ClasseCapilaridade>;   // pouco_voto, sem_base
  // ---- daqui para baixo: ler-capilaridade.ts (usa nomeUf de eleicoes.ts, já exportado) ----
  export const RECORTES: readonly { value: string; label: string }[];  // "brasil", "regiao-NO"…"regiao-S", "uf-AC"…"uf-TO"
  export type ConsultaCapilaridade = ConsultaRelatorio & { recorte?: ValorConsulta; partido?: ValorConsulta };
  export function lerRecorte(valor: ValorConsulta): string;          // padrão "brasil"
  export function paramsRecorte(recorte: string): Record<string, string>;  // {} | {regiao} | {uf}
  export function lerCapilaridade(valor: unknown): RelatorioCapilaridade;  // lança RespostaInvalidaError
  export function partidoEscolhido(dados: RelatorioCapilaridade, valor: ValorConsulta): PartidoCapilaridade | null; // D16
  // buscar-relatorios.ts
  export function buscarCapilaridade(ano: string, turno: string, cargo: string, recorte: string): Promise<Resultado<RelatorioCapilaridade>>;
  ```
  Os rótulos de `RECORTES` são "Brasil", "Região Norte"…"Região Sul" e `nomeUf(sigla)` (função já exportada por `eleicoes.ts`) para as 27 UFs de `UFS`, sem o exterior (`ZZ`). `lerCapilaridade` confere as 7 chaves de faixa na ordem e as classes conhecidas.

- [x] **Step 1:** Escrever `capilaridade.ts` (tipos e constantes), `ler-capilaridade.ts` e `buscarCapilaridade`. Confirme que `capilaridade.ts` não tem nenhuma linha `import` que não seja `import type`: `grep -n "^import" frontend/src/lib/capilaridade.ts` não deve imprimir nada além de `import type`. `buscarCapilaridade` monta `new URLSearchParams({ ano, turno, cargo, ...paramsRecorte(recorte) })` e chama `buscar("/relatorios/dados/capilaridade", params, lerCapilaridade)`.
- [x] **Step 2:** Rodar `cd frontend && pnpm exec tsc --noEmit`.
  Expected: sem saída (código 0).
- [x] **Step 3:** Rodar `pnpm exec eslint src/lib/capilaridade.ts src/lib/ler-capilaridade.ts src/lib/buscar-relatorios.ts src/lib/relatorios.ts`.
  Expected: sem saída.

**If Task Fails:** se `exigir*` já foram exportados por um plano irmão, não duplique e só importe. Se `tsc` reclamar de `ConsultaRelatorio`, importe o tipo de `@/lib/eleicoes` com `import type`.

---

### Task 10: Layout e frases puros, com verificação

**Files:**
- Create: `frontend/src/lib/grafico-capilaridade.ts`
- Test: `frontend/src/lib/verificar-grafico-capilaridade.ts`

**Interfaces:**
- Consumes: `formatarInteiro` e `formatarPercentualContagem` (`./fracao.ts`), `rotuloPartido` (`./partidos.ts`), `larguraTexto` (`./largura-texto.ts`), e tipos e constantes de `./capilaridade.ts` (import `.ts`). **Nunca** importa `ler-capilaridade.ts`, `relatorios.ts` (exceto `import type`) nem `eleicoes.ts`.
- Produces:
  ```ts
  export type MedidasRanking = { largura: number; esquerda: number; direita: number; topo: number; base: number;
    alturaLinha: number; alturaBarra: number; descida: number; rotuloAcima: boolean; fonte: number };
  export const MEDIDAS_RANKING: MedidasRanking;          // largura 640, esquerda 120, direita 220 (valor + classe)
  export const MEDIDAS_RANKING_ESTREITO: MedidasRanking; // largura 340, rótulo acima, classe só no rótulo
  export type BarraRanking = { partido: number; rotulo: string; classe: string; valor: number; y: number;
    largura: number; selecionado: boolean; href: string; dica: string[] };
  export function layoutRanking(partidos: readonly PartidoCapilaridade[], selecionado: number,
    href: (partido: number) => string, medidas?: MedidasRanking):
    { largura: number; altura: number; marcas: { x: number; texto: string }[]; barras: BarraRanking[] } | null;
  export type MedidasFaixas = { largura: number; altura: number; esquerda: number; direita: number; topo: number; base: number; vao: number; fonte: number };
  export const MEDIDAS_FAIXAS: MedidasFaixas;            // largura 300, altura 180 por painel
  export const MEDIDAS_FAIXAS_ESTREITO: MedidasFaixas;   // largura 340, painéis empilhados
  export const ROTULOS_FAIXA: Record<ChaveFaixa, { curto: string; longo: string }>;
  export type ColunaFaixa = { chave: ChaveFaixa; x: number; y: number; largura: number; altura: number;
    valor: string; neutra: boolean; dica: string[] };
  export function layoutFaixas(faixas: readonly FaixaCapilaridade[], medida: "municipios" | "votos",
    medidas?: MedidasFaixas): { largura: number; altura: number; colunas: ColunaFaixa[] } | null;
  export function resumoRanking(partidos: readonly PartidoCapilaridade[]): string;
  export function resumoFaixas(partido: PartidoCapilaridade, medida: "municipios" | "votos"): string;
  export function leituraCapilaridade(partido: PartidoCapilaridade, recorte: Recorte, ufs: number): string[];
  ```
  Regras:
  - Ranking: só os partidos fora de `NAO_RANQUEADAS`. O comprimento é `indice_100 / 100 × (largura − esquerda − direita)` (escala fixa de 0–100). As marcas de grade ficam em 0, 25, 50, 75 e 100. A dica tem estas linhas: `"Índice {indice_100} de 100"`, `rotulo_classe`, `"Fatia {fatia_texto}"`, `"10% mais fortes: {top10.parte_texto} dos votos, {top10.eleitorado_texto} do eleitorado"`. Sem partidos ranqueáveis, devolve `null`.
  - Faixas: a altura é proporcional ao maior valor do painel. O valor é a parte em percentual (`formatarPercentualContagem(municipios, Σmunicipios)` ou `(votos, Σvotos)`). A faixa `zero` é `neutra: true` (cor muted). No painel "votos", a faixa `zero` sempre vale 0 e mostra `"—"`. Sem municípios, devolve `null`. Os rótulos curtos são `"0"`, `"<½"`, `"½–1"`, `"1–1,5"`, `"1,5–2"`, `"2–3"`, `"3+"`. Os longos são `"Sem voto"`, `"Menos da metade da média"`, `"Da metade até a média"`, `"Da média até 1,5 vez"`, `"De 1,5 a 2 vezes a média"`, `"De 2 a 3 vezes a média"`, `"3 vezes a média ou mais"`.
  - `leituraCapilaridade` devolve, nesta ordem e com texto exato:
    1. `"{rotulo} teve {fatia_texto} dos votos válidos no recorte {recorte.nome}."` Quando `ufs_com_voto < dados.ufs`, a frase vira `"{rotulo} teve {fatia_texto} dos votos válidos no recorte {recorte.nome}, contando só as {ufs_com_voto} UFs onde recebeu voto."` Por isso `leituraCapilaridade` recebe também `ufs: number` (assinatura: `leituraCapilaridade(partido, recorte, ufs)`).
    2. `"Os {top10.municipios} municípios onde é mais forte deram {top10.parte_texto} dos votos dele. Eles têm {top10.eleitorado_texto} do eleitorado."`
    3. `"Teve pelo menos 5% dos votos em {presenca.municipios} de {municipios} municípios ({presenca.parte_texto})."`
    4. `"Índice de concentração: {indice_100} de 100. {motivo}"`

- [x] **Step 1:** Escrever `verificar-grafico-capilaridade.ts` com `node:assert/strict` e dados feitos à mão (3 partidos ranqueáveis, 1 `pouco_voto`). Casos:
  - ordem e exclusão do `pouco_voto`;
  - escala fixa (índice 50 dá metade da área útil);
  - `selecionado` marca só um;
  - `href` usado;
  - marcas 0–100;
  - faixas com total zero dão `null`;
  - `zero` neutra e com `"—"` no painel de votos;
  - a soma das alturas não passa da área útil;
  - variante estreita com largura 340;
  - as quatro frases de `leituraCapilaridade` com texto exato para Brasil, região e UF;
  - o acréscimo "contando só as N UFs" com `ufs_com_voto = 12` e `ufs = 27`, e a ausência dele com `ufs_com_voto = 26` e `ufs = 26` (deputado estadual);
  - `resumoRanking` cita todos os valores.
- [x] **Step 2:** `cd frontend && node --experimental-strip-types src/lib/verificar-grafico-capilaridade.ts`
  Expected: falha com `ERR_MODULE_NOT_FOUND` (o módulo ainda não existe).
- [x] **Step 3:** Implementar `grafico-capilaridade.ts`.
- [x] **Step 4:** Rodar o script de novo.
  Expected: imprime `ok`. Depois `pnpm exec tsc --noEmit` e `pnpm exec eslint src/lib/grafico-capilaridade.ts src/lib/verificar-grafico-capilaridade.ts`, ambos sem saída.

**If Task Fails:** o Node exige o import com `.ts` e caminho relativo nos módulos `lib`. Um `ERR_MODULE_NOT_FOUND` com `@/lib/...` na mensagem quer dizer que algum módulo da cadeia importa em runtime de `relatorios.ts`, `eleicoes.ts` ou `ler-capilaridade.ts`. Mova a constante para `capilaridade.ts` ou troque por `import type`.

---

### Task 11: Componentes

**Files:**
- Create: `frontend/src/components/relatorios/grafico-ranking-capilaridade.tsx` (servidor)
- Create: `frontend/src/components/relatorios/grafico-faixas-capilaridade.tsx` (servidor)
- Create: `frontend/src/components/relatorios/tabela-capilaridade.tsx` (servidor)
- Create: `frontend/src/components/relatorios/explicacao-capilaridade.tsx` (servidor)
- Create: `frontend/src/components/relatorios/dados-capilaridade.tsx` (servidor, async)

Desenho (copie a estrutura de `grafico-poder.tsx` e `grafico-perfis.tsx`):
- **Ranking:** `<figure className="folha-quieta">`, com `DicaGrafico` envolvendo duas variantes: `hidden overflow-x-auto sm:block` com `min-w-[560px]` e `sm:hidden` estreita. Cada linha é um `<a href>` com o `<rect>` da barra (`rx` 4 na ponta, `fill` `var(--tinta-quente)` no selecionado e `var(--muted-foreground)` com `fillOpacity` 0,45 nos outros), o rótulo do partido (`text-foreground`, `text-anchor="end"`), o valor (`tabular-nums`) e a classe (`text-muted-foreground`). Um `<rect>` transparente maior que a barra leva `data-dica-titulo` e `data-dica-linhas`. Grade em `var(--border)` com 1 px. O figcaption diz: "O índice vai de 0 (mesma fatia em todo município) a 100 (votos vindos de um pedaço pequeno do eleitorado). Clique num partido para ver o detalhe."
- **Faixas:** dois `<svg>` lado a lado (`grid sm:grid-cols-2`), com os títulos "Municípios" e "Votos do partido". As colunas usam `--tinta-quente`, e `zero` usa `--muted-foreground`, com 2 px de vão entre colunas. O eixo x leva os rótulos curtos e o título "vezes a fatia média do partido". O valor fica acima de cada coluna. `<desc>` com `resumoFaixas`.
- **Tabela:** uma `<table>` com todos os partidos (incluindo os não ranqueados) e as colunas Partido (link), Classe, Índice, Fatia, 10% mais fortes (votos / eleitorado), Presença e UFs com voto. As linhas não ranqueadas ficam com `text-muted-foreground`.
- **Explicação:** texto fixo em parágrafos curtos:
  - o que é fatia e fatia média;
  - como ler as faixas (exemplo: "'3+' quer dizer municípios onde o partido teve três vezes a sua fatia média ou mais");
  - o índice (D5, em linguagem simples);
  - os 10% mais fortes e a base de comparação;
  - as classes em lista, com as regras montadas a partir de `dados.limites` (sem número fixo no texto);
  - o aviso para governador, senador e deputados: "o partido é medido só nas UFs onde recebeu voto";
  - as `notas` do backend.
- **Dados:** recebe `ano`, `turno`, `cargo`, `recorte` e `partido` e chama `buscarCapilaridade`. Usa `partidoEscolhido` de `ler-capilaridade.ts` e chama `leituraCapilaridade(partido, dados.recorte, dados.ufs)`. Em erro, mostra `<ErroRelatorio detalhe>`. A ordem na página é: subtítulo (`"{cargo} · {recorte.nome} · {municipios} municípios"`), explicação, ranking, detalhe do partido escolhido (título `rotuloPartido`, as frases de `leituraCapilaridade`, os painéis de faixas, uma lista de `subdivisoes` com "parte / eleitorado / vezes", e duas listas curtas "Onde é mais forte" (`fortes`) e "De onde vêm mais votos" (`maiores`)) e, por fim, a tabela. O `href` de cada partido preserva `ano`, `turno`, `cargo`, `recorte` e `consultar=1` e troca `partido`.

- [x] **Step 1:** Implementar os 5 componentes.
- [x] **Step 2:** `cd frontend && pnpm exec tsc --noEmit && pnpm exec eslint src/components/relatorios/*capilaridade*.tsx`
  Expected: sem saída.

---

### Task 12: Página, filtro e links

**Files:**
- Create: `frontend/src/app/relatorios/capilaridade/page.tsx`
- Create: `frontend/src/components/relatorios/filtros-capilaridade.tsx` (cliente)
- Modify: `frontend/src/components/layout/app-sidebar.tsx` (`{ href: "/relatorios/capilaridade", rotulo: "Capilaridade" }`. É a 3ª entrada do bloco dos seis planos, que fica depois de "Classe do governador" e antes de "Mapa" na ordem Força partidária, Cadeiras, Capilaridade, Verticalização, Força da marca, Municipais 2024. Entra depois das anteriores que já existirem; alinhado em 2026-10-22)
- Modify: `frontend/src/components/layout/app-breadcrumb.tsx` (`"/relatorios/capilaridade": { pagina: "Capilaridade", relatorios: true }`, na mesma posição)
- Modify: `frontend/src/app/page.tsx` (`DESTINOS`: `{ href: "/relatorios/capilaridade", titulo: "Capilaridade", descricao: "Se a força de cada partido está espalhada ou concentrada nos municípios." }`, na mesma posição)

Página: copie `app/relatorios/perfis/page.tsx`. `metadata.title = "Capilaridade partidária"`, `maxDuration = 600`, `CHAVES_FILTRO = ["ano", "turno", "cargo", "recorte"]` e o título h1 "Capilaridade partidária". `searchParams: Promise<ConsultaCapilaridade>`. O cargo vem de `lerCargoPoder` (5 cargos), o recorte de `lerRecorte` (de `ler-capilaridade.ts`) e o partido é repassado cru. Sem `consultar=1`, mostra "Selecione os filtros e clique em Consultar."
Filtro: copie `filtros-curtos.tsx` com Ano, Turno, Cargo (`CARGOS_PODER`) e Recorte (`RECORTES` de `ler-capilaridade.ts`). O botão Consultar monta `ano`, `turno`, `cargo`, `recorte` e `consultar=1`, sem `partido`, para voltar ao padrão D16.

- [x] **Step 1:** Implementar.
- [x] **Step 2:** `cd frontend && pnpm exec tsc --noEmit && pnpm exec eslint src/app/relatorios/capilaridade src/components/relatorios/filtros-capilaridade.tsx src/components/layout src/app/page.tsx`
  Expected: sem saída.
- [x] **Step 3:** `pnpm build`
  Expected: termina com a rota `/relatorios/capilaridade` listada e sem erro.

---

### Task 13: Verificação no navegador

Com a API e o frontend rodando (`pnpm dev` em `frontend/`), use chrome-devtools numa aba própria (`isolatedContext: "capilaridade"`):
- [ ] `/relatorios/capilaridade?ano=2026&turno=1&cargo=presidente&recorte=brasil&consultar=1`: ranking com 5 partidos, PT e PL abaixo de 25 e o detalhe abrindo no PL 22 (D16).
- [ ] `cargo=deputadoFederal`: PSOL 50 com "Concentrado nas capitais" e NOVO 30 com "Regional (Sul)".
- [ ] `cargo=governador&recorte=regiao-NE`: rótulos "Concentrado em …" e "Espalhado pela região".
- [ ] `cargo=senador&recorte=uf-SP`: sem lista de subdivisões e com "Espalhado pelo estado".
- [ ] `cargo=deputadoEstadual&recorte=uf-DF`: mensagem de erro 409 em português.
- [ ] Clique numa barra do ranking: a URL ganha `partido=`, o detalhe muda e a barra fica destacada.
- [ ] Tema claro e escuro, largura de 375 px (variantes estreitas e nenhuma rolagem horizontal da página), tooltip no ranking e nas faixas, e console sem erro.
- [ ] Salvar as capturas `capilaridade-*.png` no scratchpad.

---

### Task 14: Code Review final

1. **REQUIRED SUB-SKILL:** Use jarvis:codereview sobre o diff completo (backend e frontend).
2. Siga só com zero Critical/High/Medium.
3. Rode tudo de novo: `uv run pytest -q`, `uv run ruff check src tests`, `uv run mypy`, `cd frontend && node --experimental-strip-types src/lib/verificar-grafico-capilaridade.ts && pnpm exec tsc --noEmit && pnpm exec eslint`.
   Expected: tudo verde e o script imprimindo `ok`.
4. Sem commit. O humano decide.

---

## Perguntas em aberto

1. **Limites das classes:** 1% para pouco voto; 20 municípios; capitais 1,75×; regional 50% e 1,5×; poucos municípios 50% e 2×; presença 5%. Eles foram calibrados uma vez com 2026 (tabela acima). Servem, ou o usuário quer outra régua, por exemplo limites por cargo?
2. **Presidente:** todo partido com 1% ou mais sai `espalhado`. Isso é aceitável, ou o PSD (Centro-Oeste 3,09×, mas só 23% dos votos) deveria ganhar uma classe "com viés regional"?
3. **Universo por UF com voto (D4):** para deputado, voto de legenda aparece em quase todas as UFs, então o efeito é pequeno. Para governador, o efeito é grande. Mostrar também o índice sobre o recorte inteiro, para comparar?
4. **Placar (plano 1), respondida em 2026-10-22:** o placar mantém a presença dele (todo o recorte, F9 do plano 1) e não lê a `presenca` daqui. Não é preciso `presenca_recorte`. O consumo deste plano pelo placar é opcional (D15).
5. **Mapa:** um coroplético da fatia por município ficou fora (YAGNI). O mapa existente (`/mapa`) poderia ganhar essa camada depois.


## Decisões do usuário (2026-10-22)

O usuário aceitou as recomendações da revisão de coerência. Estas decisões valem sobre qualquer pergunta em aberto neste plano.

- **Fase D do placar:** só os links para Capilaridade, Verticalização e Força da marca e a coluna de voto de legenda (Tasks 19 e 20). A Task 21 não entra.
- **Limiares das classes:** manter os calibrados nos planos e rever depois da primeira execução com dados reais.
- **Itens menores:** sem população do IBGE, limiar de presença na lista fixa, sem classe de viés regional, Força da marca com página fixa, sem mapa de calor e com o visual proposto.
