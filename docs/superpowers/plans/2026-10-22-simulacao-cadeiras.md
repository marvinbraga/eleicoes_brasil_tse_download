# Simulação de cadeiras (Câmara, Assembleias, Senado e governadores)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Review between blocks of tasks with jarvis:codereview.

**Goal:** Estimar, com os votos do 1º turno de 2026 gravados nos boletins, as 513 cadeiras da Câmara, as 1.059 das Assembleias (com as 24 da Câmara Legislativa do DF), as 54 vagas do Senado e o resultado de governador em cada UF. O resultado sai em `GET /relatorios/dados/cadeiras`, na página `/relatorios/cadeiras` e num contrato por partido que o placar de força partidária (plano 1) consome.

**Architecture:** Uma CLI (`scripts/relatorio_cadeiras.py`) faz uma varredura agrupada de `raw.boletim` por cargo e grava os votos por (UF, tipo de voto, número) em `analise.relatorio_cadeiras_voto` (migração `0004`). As cadeiras **não** são gravadas: o domínio puro (`proporcional.py`, `majoritario.py`, `simulacao_cadeiras.py`) refaz as contas a cada leitura, em milissegundos. Assim, uma mudança na lista de federações (`domain/federacoes.py`, dado versionado no git) vale sem nova varredura. A API lê só o gravado e responde 409 com o comando quando falta um cargo. O frontend reaproveita o `GraficoPoder` com uma margem maior.

**Tech Stack:** Python 3.14 (uv), SQLAlchemy 2 + Alembic, FastAPI + Pydantic v2, psycopg 3, pytest, ruff, mypy strict. Next.js 16.4, React 19, TypeScript, Tailwind 4, shadcn/ui. Sem dependência nova.

**Spec:** Este arquivo. As decisões estão numeradas abaixo. Todo o código deste plano foi rodado num protótipo fora do repositório, em 2026-10-22: `uv run pytest -q` deu 958 passed (878 + 80 novos), com cobertura de 94,37%; ruff e mypy strict ficaram limpos; no frontend, `tsc` e `eslint` passaram nos arquivos novos e o script de verificação imprimiu `ok`. O protótipo também rodou com os votos reais do AC (Task 14).

---

## Fontes

**Regras do sistema proporcional**

- Código Eleitoral (Lei 4.737/1965), arts. 106 a 112, na redação da Lei 14.211/2021: <https://www.planalto.gov.br/ccivil_03/leis/l4737compilado.htm>
  - Art. 106: o quociente eleitoral (QE) é o número de votos válidos dividido pelas vagas. A fração de meio ou menos é desprezada; acima de meio, arredonda para 1.
  - Art. 107: o quociente partidário (QP) é o número de votos válidos do partido dividido pelo QE, desprezada a fração.
  - Art. 108: elegem-se pelo QP só candidatos com pelo menos 10% do QE.
  - Art. 109, I e II e § 2º: as sobras vão pela maior média entre os partidos com 80% do QE que tenham candidato com 20% do QE.
  - Art. 109, III: quando não houver mais partido que cumpra as duas exigências, as cadeiras vão para as maiores médias.
  - Art. 110: empate entre candidatos vai para o mais idoso.
  - Art. 111: se nenhum partido alcança o QE, elegem-se os mais votados. Este artigo foi declarado inconstitucional (ver abaixo).
- STF, ADIs 7228, 7263 e 7325:
  - Mérito em 28/02/2024. O art. 109, § 2º recebeu interpretação conforme: a última fase das sobras (inciso III) vale para **todas** as legendas, sem 80% nem 20%. O art. 111 e o art. 13 da Res.-TSE 23.677/2021 foram declarados inconstitucionais. Notícia: <https://portal.stf.jus.br/noticias/verNoticiaDetalhe.asp?idConteudo=528283&ori=1>
  - Embargos em 13/03/2025: a decisão vale desde 2022. Notícia: <https://noticias.stf.jus.br/postsnoticias/decisao-do-stf-sobre-distribuicao-de-sobras-eleitorais-vale-desde-2022/>
  - Em qualquer leitura das datas, 2026 está coberto.
- Res.-TSE 23.677/2021 (sistemas eleitorais): <https://www.tse.jus.br/eleicoes/eleicoes-2024-content/normas-e-documentacoes/arquivos/tse-resolucao-no-23-677-sistemas-eleitorais>
  - Arts. 8 a 10: 10% do QE; votos válidos; QE e QP.
  - Art. 11, §§ 1º e 5º: média = votos ÷ (QP + 1), somando as vagas já obtidas por média.
  - Art. 11, §§ 6º e 7º: empate de médias vai para o partido mais votado; persistindo, para o candidato mais votado.
  - Art. 12: idade.
  - O caput do art. 11 (80% para todas as sobras) e o art. 13 foram superados pelo STF.
- Lei 9.504/1997, art. 59, § 2º: na proporcional, o voto em número que não identifica candidato, mas tem o prefixo de partido certo, vai para a legenda.

**Vagas**

- CF art. 45, § 1º, e LC 78/1993: 513 deputados federais, de 8 a 70 por UF.
- O STF manteve a distribuição de 1993 para 2026 depois do veto ao projeto de 531 cadeiras: decisão do Min. Luiz Fux de 29/09/2025, noticiada em <https://www.terra.com.br/noticias/brasil/politica/fux-mantem-numero-de-deputados-para-as-eleicoes-de-2026-veja-quantos-sao-em-cada-estado,81334519b28aaf8a650c649fae342378f7ynihmo.html>.
- Tabela por UF publicada em 09/2026: <https://www.correiobraziliense.com.br/politica/2026/09/7505399-quantos-deputados-federais-cada-estado-elege-em-2026-veja-a-lista-completa.html>. Ela soma 513 e coincide com a da notícia anterior.
- CF art. 27: deputados estaduais = 3 × federais até 36. Daí em diante, +1 para cada federal acima de 12.
- CF art. 32, § 3º: a mesma regra vale para a Câmara Legislativa do DF, com 24 distritais.
- Conta conferida: 1.035 + 24 = **1.059**.
- No banco, o DF tem `cargo = 'deputadoDistrital'` e **não** tem `deputadoEstadual`. Isso foi conferido em 2026-10-22 com consulta de leitura pelo índice `boletim_uf_cargo_numero_idx`.
- CF art. 46, § 2º: em 2026 o Senado renova 2/3, com duas vagas por UF, ou seja, 54.
- CF art. 28 c/c art. 77, §§ 2º e 3º: governador eleito com maioria absoluta dos votos válidos. Sem ela, há 2º turno entre os dois mais votados.

**Federações de 2026 (fonte oficial TSE)**

| Código interno | Sigla | Partidos (número) | Registro |
|---|---|---|---|
| `fe-brasil` | FE BRASIL | PT 13, PCdoB 65, PV 43 | 2022, vigente |
| `psdb-cidadania` | PSDB CIDADANIA | PSDB 45, CIDADANIA 23 | 2022, vigente |
| `psol-rede` | PSOL REDE | PSOL 50, REDE 18 | 2022, vigente |
| `renovacao-solidaria` | RENOVAÇÃO SOLIDÁRIA | PRD 25, SOLIDARIEDADE 77 | Deferida em 04/12/2025 (RFP 0600839-93.2025.6.00.0000) |
| `uniao-progressista` | UNIÃO PROGRESSISTA | UNIÃO 44, PP 11 | Deferida em 26/03/2026 (RFP 0601165-53.2025.6.00.0000) |

- Lista oficial: <https://www.tse.jus.br/partidos/federacoes-registradas-no-tse>
- Notícias do TSE:
  - <https://www.tse.jus.br/comunicacao/noticias/2025/Dezembro/tse-aprova-criacao-da-federacao-renovacao-solidaria>
  - <https://www.tse.jus.br/comunicacao/noticias/2026/Marco/tse-aprova-registro-da-federacao-uniao-progressista-1>
- Lista de partidos, federações e candidaturas do 1º turno (DJE-TSE de 18/09/2026), que cita 25-PRD/77-SOLIDARIEDADE e 44-UNIÃO/11-PP: <https://sintse.tse.jus.br/documentos/2026/Set/23/diario-da-justica-eletronico-tres-destaques-edicoes-anteriores/lista-de-partidos-federacoes-coligacoes-candidatas-e-candidatos-eleicao-geral-federal-2026-1o-turno>
- O site do TSE devolve 403 a leitores automáticos. A tabela acima foi conferida nos resultados de busca do próprio TSE e em A Gazeta (04/08/2026, cinco federações). O executor deve abrir a página oficial num navegador e confirmar antes da Task 2 (pergunta em aberto Q2).
- Partidos com número em 2026: os 30 de `frontend/src/lib/partidos.ts` (10, 11, 12, 13, 14, 15, 16, 18, 20, 21, 22, 23, 25, 27, 28, 29, 30, 33, 35, 36, 40, 43, 44, 45, 50, 55, 65, 70, 77, 80).

## Decisões

| # | Pergunta | Decisão |
|---|---|---|
| D1 | Que dado agregar | Votos por `(cargo, uf, tipo_voto, numero)`, só `nominal` e `legenda`. O voto nominal é por candidato e o prefixo do número dá o partido (`partido_do_numero`, já usado pelo relatório de poder). `analise.relatorio_poder_linha` não serve: tem só o total por partido e não tem distrital. |
| D2 | Como varrer `raw.boletim` | Uma consulta por cargo, `WHERE ano, turno, cargo ... GROUP BY uf, tipo_voto, numero`. `EXPLAIN` (sem `ANALYZE`, 2026-10-22): a tabela tem 26 GB e cerca de 68 milhões de linhas. Para SP o planejador já escolhe *Parallel Seq Scan*; só UF pequena usa `boletim_uf_cargo_numero_idx` (*Index Scan* no AC). Por isso não fazer um laço por UF, que daria 27 varreduras por cargo: são 5 varreduras no total, uma por cargo. Sem índice novo. |
| D3 | O que gravar (migração 0004) | Os votos, não as cadeiras. Cabeçalho `analise.relatorio_cadeiras(ano, turno, cargo, gerado_em)` e linhas `analise.relatorio_cadeiras_voto(ano, turno, cargo, uf, tipo_voto, numero, votos)`. A chave segue o padrão de `relatorio_poder`. Um cargo sem votos fica só com o cabeçalho. |
| D4 | Cargos gravados | `governador`, `senador`, `deputadoFederal`, `deputadoEstadual`, `deputadoDistrital`. A Casa "assembleias" usa `deputadoDistrital` no DF e `deputadoEstadual` nas outras 26 UFs (`cargo_assembleia`). |
| D5 | Onde ficam as federações | Em `src/eleicoes/domain/federacoes.py`, como `REGISTROS = {2026: RegistroPartidario(...)}`, versionado no git, com as fontes no docstring. Para atualizar: editar, rodar os testes, reiniciar a API. Não vai para tabela: o dado muda pouco, precisa de revisão e não tem tela de edição (YAGNI). |
| D6 | Número cujo prefixo não é partido | Vira nulo: sai da conta e soma em `descartados`. O exterior (`ZZ`) também sai. |
| D7 | Votos de candidato indeferido ou sub judice | Contam como válidos, porque o boletim não traz a situação do registro. É a principal fonte de diferença para o oficial e fica dita na página e nas notas. |
| D8 | QE | `q, r = divmod(validos, vagas)`, mais 1 só se `2r > vagas`. Exatamente meio é desprezado (teste). |
| D9 | Fases | (1) Pelo QP, só candidatos com `10·votos ≥ QE`. (2) Maior média entre listas com `5·votos_lista ≥ 4·QE` cujo próximo candidato tem `5·votos ≥ QE`; a lista sem esse candidato pula a vaga e não a "gasta". (3) Maior média entre **todas** as listas com candidato restante, sem limiar. A fase 2 continua enquanto houver lista apta. Toda comparação é feita em inteiros ou `Fraction`, sem ponto flutuante. |
| D10 | Divisor da média | `QP + vagas já obtidas por média + 1` (Res. 23.677, art. 11, §§ 1º e 5º). A vaga de QP que ficou vazia pelos 10% **conta** no divisor. O Código diz "lugares por ele obtido", o que é ambíguo; o teste `test_average_divisor_counts_the_quotient_seat_left_empty` mostra onde as duas leituras divergem (pergunta em aberto Q1). |
| D11 | Ninguém atinge o QE | Sem regra especial: todos os QP são 0 e seguem as fases 2 e 3 (art. 111 inconstitucional). |
| D12 | Desempates | Médias iguais: vence a lista com mais votos (§ 6º), depois o próximo candidato com mais votos (§ 7º), depois o menor código de legenda. Candidatos com votos iguais: vence o menor número, porque a idade (art. 110) não está no boletim. Todo desempate que a lei não resolve com os dados marca `empate = true`. |
| D13 | Lista sem candidato | A lista sai das fases seguintes. Se ninguém tiver candidato, a vaga fica em `vagas_sem_candidato`. Só existem nos dados os números que receberam votos. |
| D14 | Federação | Uma `Lista` por federação, com os candidatos de todos os partidos membros e os votos de legenda somados. A cadeira é atribuída ao partido do número do eleito. Senado e governador não usam federação. |
| D15 | Senado | Os dois mais votados por UF, por número. `empate` quando o 2º e o 3º têm os mesmos votos. |
| D16 | Governador | `2·votos_1º > válidos` elege. Senão, há 2º turno entre os dois primeiros. Válidos são a soma dos nominais com prefixo de partido. `empate` quando o 2º e o 3º empatam. Fica dito que a regra conta voto em número de partido sem candidato no estado, o que infla um pouco o denominador. |
| D17 | Quando calcular | Na leitura, a cada requisição. São cerca de 27 × 5 grupos de poucas centenas de números, em milissegundos. Sem cache (YAGNI). |
| D18 | Falta de dado | A API exige os 5 cargos gravados. Senão responde 409 com `MissingSeatReportError`, que lista os cargos e o comando. A CLI só imprime o resumo da simulação com os 5 cargos. Uma UF sem votos num cargo entra em `ufs_sem_votos`, e as vagas dela ficam fora de `vagas_simuladas`. |
| D19 | `gerado_em` | O mais antigo dos 5 cabeçalhos, porque descreve o dado mais velho que entrou na conta. |
| D20 | Frontend | Página `/relatorios/cadeiras` com filtros `ano` e `turno` (`FiltrosCurtos`). Traz o aviso de estimativa no topo, "Em resumo", a explicação, um gráfico de barras por Casa (reaproveita `GraficoPoder` com a nova prop opcional `medidas` e `MEDIDAS_CADEIRAS.esquerda = 152`, para caber "RENOVAÇÃO SOLIDÁRIA"), a tabela por legenda, um `<details>` por UF, o Senado (gráfico e tabela), os governadores (tabela) e as notas. Todas as legendas com cadeira aparecem, sem "Outros". |
| D21 | Porta do placar | O plano 1 define, na seção "Fase B", a porta `AsyncEstimativaCadeiras` em `src/eleicoes/ports/cadeiras.py` e lê as cadeiras por ela, não pela rota HTTP. Este plano cria a porta exatamente como lá está e o adaptador `StoredSeatEstimates` (Task 13). O código de federação daqui (`fe-brasil`) vira a `sigla` e a `chave` `fed:fe-brasil`. As cadeiras de cada partido membro de federação também saem, o que responde à Q4 do plano 1. `governador_2t` conta a presença entre os finalistas, sem vencedor projetado, o que responde à Q3 do plano 1. A porta devolve `None` também para ano sem registro partidário. A forma foi conferida com o plano 1 e é idêntica (alinhado em 2026-10-22). |

## Contrato para o placar (plano 1)

O placar lê pela **porta Python** `AsyncEstimativaCadeiras` (D21, Task 13), implementada por `StoredSeatEstimates(store)` sobre `AsyncSeatVoteStore`. `load(ano, turno)` devolve `EstimativaCadeiras` ou `None`. As linhas são `(chave, uf)` com `chave` "13" ou "fed:fe-brasil" e `uf` sigla ou "BR". Para outros consumidores, há também:

- **HTTP:** `GET /relatorios/dados/cadeiras?ano=2026&turno=1`. Responde 200 com o JSON abaixo, 409 quando falta cargo gravado e 422 para um ano sem registro partidário.
- **Python:** `await stored_simulation(store, ano, turno)`, de `eleicoes.use_cases.simular_cadeiras`. Devolve `SimulacaoGravada(simulacao: SimulacaoCadeiras, gerado_em)`; `simulacao.partidos()` devolve `tuple[ForcaPartido, ...]`.

```jsonc
{
  "ano": 2026, "turno": 1, "gerado_em": "2026-10-22T14:03:00+00:00", "estimativa": true,
  "legendas": [{"codigo": "fe-brasil", "sigla": "FE BRASIL", "nome": "Federação Brasil da Esperança",
                "federacao": true, "partidos": [13, 65, 43]},
               {"codigo": "22", "sigla": "22", "nome": "Partido 22", "federacao": false, "partidos": [22]}],
  "casas": [{"casa": "camara" | "assembleias", "nome": "...", "vagas": 513, "vagas_simuladas": 513,
             "ufs_sem_votos": [], "legendas": [{"legenda": "fe-brasil", "cadeiras": 0}],
             "partidos": [{"partido": 13, "cadeiras": 0}],
             "ufs": [{"uf": "AC", "cargo": "deputadoFederal", "vagas": 8, "votos_validos": 0,
                      "quociente_eleitoral": 0, "vagas_sem_candidato": 0,
                      "listas": [{"legenda": "...", "votos": 0, "votos_legenda": 0, "quociente_partidario": 0,
                                  "cadeiras_quociente": 0, "cadeiras_media": 0, "cadeiras_media_livre": 0,
                                  "cadeiras": 0}],
                      "eleitos": [{"numero": 1301, "partido": 13, "legenda": "fe-brasil", "votos": 0,
                                   "fase": "quociente" | "media" | "media_livre", "empate": false}]}]}],
  "senado": {"vagas": 54, "vagas_simuladas": 54, "ufs_sem_votos": [], "partidos": [{"partido": 22, "cadeiras": 0}],
             "ufs": [{"uf": "AC", "votos_validos": 0, "eleitos": [{"numero": 222, "partido": 22, "votos": 0, "fatia": "25,59%"}], "empate": false}]},
  "governo": {"ufs_sem_votos": [], "partidos": [{"partido": 13, "eleitos": 0, "segundo_turno": 0}],
              "ufs": [{"uf": "AC", "situacao": "eleito" | "segundo_turno" | "sem_votos", "votos_validos": 0,
                       "candidatos": [{"numero": 11, "partido": 11, "votos": 0, "fatia": "49,76%"}], "empate": false}]},
  "partidos": [{"partido": 22, "legenda": "22", "camara": 0, "assembleias": 0, "senado": 0,
                "governadores": 0, "governadores_segundo_turno": 0}],
  "descartados": 0,
  "notas": ["É uma estimativa ..."]
}
```

O placar usa `partidos[]`. Cada linha é um partido real, e não a federação: a federação é a `legenda` daquele partido. `senado` conta só as vagas disputadas em 2026, não a bancada inteira (pergunta em aberto Q4). `governadores_segundo_turno` conta presença no 2º turno, não vitória.

## Global Constraints

- **Não** alterar o banco fora de `make migrate` (Task 14). Não rodar `alembic upgrade` à mão nem `atualizar=true` em outras rotas.
- **Git:** nenhum comando que mude estado (`stash`, `checkout`, `reset`, `commit`, `rebase`), inclusive em subagentes. O commit fica a cargo do usuário. Se ele pedir, use o skill `jarvis:commit`.
- `frontend/src/lib/`, `frontend/src/components/relatorios/` e `frontend/src/app/relatorios/` **são rastreados** pelo git: `git check-ignore` não os ignora e `git ls-files` os lista (conferido em 2026-10-22). As mudanças neles aparecem em `git diff`. Não editar o `.gitignore` (alinhado em 2026-10-22).
- **Formatação:** rodar `uv run ruff format` só nos arquivos **novos**. Há arquivos antigos que o formatador mudaria (por exemplo, `domain/boletim_consulta.py` e `adapters/html_presidente_governador.py`), e eles não fazem parte desta mudança.
- Mensagens internas e de exceção técnica em inglês. Texto ao usuário em português.
- Verificação Python: `uv run pytest -q`, `uv run ruff check .`, `uv run mypy`. Os três precisam ficar limpos, com cobertura ≥ 85%.
- Verificação frontend, sempre a partir de `frontend/`: `node --experimental-strip-types src/lib/verificar-grafico-cadeiras.ts`, `pnpm exec tsc --noEmit` e `pnpm exec eslint <arquivos>`.
- **Conflito com os outros planos de 2026-10-22 (alinhado em 2026-10-22).** A tabela de quem toca cada arquivo compartilhado está no plano 1, na seção "Integração entre os planos de 2026-10-22". A ordem de integração é 2 → 6 → 1 (fases A, B e C), e os planos 3, 4 e 5 entram em qualquer ordem. Este plano vem **primeiro**. Toda mudança em arquivo compartilhado é só por adição: um campo com default, uma linha ou uma função no fim.
  - Na navegação (`ITENS`, `TRILHAS` e `DESTINOS`), as seis entradas formam um bloco contínuo depois de "Classe do governador" e antes de "Mapa", nesta ordem: Força partidária, Cadeiras, Capilaridade, Verticalização, Força da marca, Municipais 2024. "Cadeiras" é a 2ª do bloco: fica depois de "Força partidária", se ela já existir, e senão logo depois de "Classe do governador".
  - Migrações: este plano é a `0004` (`down_revision = "0003"`). O plano 6 encadeia a `0005` nela. Se o plano 6 rodar antes e tiver usado a `0004` (D16 dele), pare e avise: a cadeia precisa ser refeita.
- Não derrubar o Compose. Se a 14000 (Next) e a 15000 (API) já respondem, usar essas.

## Review Focus

- **D9/D10:** a fase 2 pula a lista sem candidato com 20% sem gastar a vaga dela. O divisor usa QP, não as vagas preenchidas. Testes `test_list_without_a_twenty_percent_candidate_skips_the_second_phase` e `test_average_divisor_counts_the_quotient_seat_left_empty`.
- **Nenhuma lista atinge o QE:** não pode haver o atalho "mais votados" (`test_no_list_reaching_the_quotient_still_uses_the_averages`).
- **Aritmética exata:** nenhum `float` no domínio. As médias são `Fraction` e os limiares são produtos inteiros.
- **DF:** a Assembleia lê `deputadoDistrital`. As somas 513 e 1.059 têm teste.
- **Federação:** os votos de legenda dos membros se somam, e a cadeira volta ao partido do número (`test_federation_is_one_list_and_seats_go_to_each_candidate_party`).
- **409:** a rota nunca lê boletim. Sem os 5 cargos, devolve 409 com o comando.
- **ReadPorts:** o campo novo tem default `None`, então os quatro construtores existentes nos testes não mudam.
- **Frontend:** "RENOVAÇÃO SOLIDÁRIA" cabe na margem (`rotuloCabe`). Em 375 px vale a variante estreita, sem rolagem horizontal da página.

## Verificação antes de começar

```bash
cd /run/media/marvinbraga/dados/marvin/eleicoes_brasil_tse_download
git status --short            # Esperado: nada (árvore limpa)
uv run pytest -q 2>&1 | tail -1   # Esperado: "N passed", sem falhas. Anote N (878 em 2026-10-22); o plano soma +81 testes (80 do protótipo + 1 alinhado em 2026-10-22)
docker compose exec -T postgres sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -At -c "select version_num from alembic_version"'
# Esperado: 0003
cd frontend && node --experimental-strip-types src/lib/verificar-grafico-poder.ts   # Esperado: ok
```

---

### Task 1: Erros novos e vagas por UF

**Files:**
- Modify: `src/eleicoes/domain/errors.py` (acrescentar ao fim)
- Create: `src/eleicoes/domain/cadeiras.py`
- Test: `tests/domain/test_cadeiras.py`

**Interfaces:**
- Produces: `InvalidSeatRuleError(field)`, `UnknownPartyRegistryError(ano)`, `MissingSeatReportError(cargos)`; `VAGAS_CAMARA_2026`, `vagas_camara(uf)`, `vagas_assembleia(uf)`, `cargo_assembleia(uf)`, `ufs_com_vagas()`, `CARGOS_GRAVADOS` e as constantes `CARGO_*`.

- [ ] **Step 1: Escrever o teste** `tests/domain/test_cadeiras.py`:

```python
"""Seats per UF in 2026."""

import pytest

from eleicoes.domain.cadeiras import (
    VAGAS_CAMARA_2026,
    cargo_assembleia,
    ufs_com_vagas,
    vagas_assembleia,
    vagas_camara,
)
from eleicoes.domain.errors import InvalidSeatRuleError


def test_camara_has_513_seats_and_assemblies_1059() -> None:
    assert sum(VAGAS_CAMARA_2026.values()) == 513
    assert sum(vagas_assembleia(uf) for uf in ufs_com_vagas()) == 1059
    assert len(ufs_com_vagas()) == 27


@pytest.mark.parametrize(
    ("uf", "federais", "estaduais"),
    [("AC", 8, 24), ("PB", 12, 36), ("MA", 18, 42), ("SP", 70, 94), ("DF", 8, 24)],
)
def test_assembly_is_three_times_up_to_36_then_one_per_federal_seat(
    uf: str,
    federais: int,
    estaduais: int,
) -> None:
    assert vagas_camara(uf) == federais
    assert vagas_assembleia(uf) == estaduais


def test_df_fills_the_camara_legislativa_with_deputado_distrital() -> None:
    assert cargo_assembleia("df") == "deputadoDistrital"
    assert cargo_assembleia("SP") == "deputadoEstadual"


def test_abroad_has_no_seats() -> None:
    with pytest.raises(InvalidSeatRuleError):
        vagas_camara("ZZ")
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `uv run pytest tests/domain/test_cadeiras.py -q`
Expected: `ModuleNotFoundError: No module named 'eleicoes.domain.cadeiras'` (erro de coleta).

- [ ] **Step 3: Acrescentar ao fim de `src/eleicoes/domain/errors.py`:**

```python
class InvalidSeatRuleError(ElectionError):
    def __init__(self, field: str) -> None:
        self.field = field
        super().__init__(f"invalid seat simulation input: {field}")


class UnknownPartyRegistryError(ElectionError):
    def __init__(self, ano: int) -> None:
        self.ano = ano
        super().__init__(f"Não há partidos e federações cadastrados para {ano}.")


class MissingSeatReportError(ElectionError):
    def __init__(self, cargos: tuple[str, ...]) -> None:
        self.cargos = cargos
        listed = ", ".join(cargos)
        super().__init__(
            f"Os votos por candidato de {listed} ainda não foram gravados. "
            "Gere com: uv run python scripts/relatorio_cadeiras.py"
        )
```

- [ ] **Step 4: Criar `src/eleicoes/domain/cadeiras.py`:**

```python
"""Seats per UF in 2026 and the cargo that fills each house.

Câmara: 513 seats (LC 78/1993; CF art. 45, § 1). The STF kept the 1993 distribution for
2026 after the veto to the 531-seat bill (decision of Min. Luiz Fux, 29/09/2025).
Assembleias: CF art. 27 — three times the federal seats up to 36, then one more per
federal seat above 12. The Câmara Legislativa do DF follows the same rule (CF art. 32,
§ 3) and its cargo in the urna is deputadoDistrital.
"""

from typing import Final

from eleicoes.domain.errors import InvalidSeatRuleError
from eleicoes.domain.values import Uf

CARGO_CAMARA: Final = "deputadoFederal"
CARGO_ESTADUAL: Final = "deputadoEstadual"
CARGO_DISTRITAL: Final = "deputadoDistrital"
CARGO_SENADO: Final = "senador"
CARGO_GOVERNO: Final = "governador"
CARGOS_GRAVADOS: Final[tuple[str, ...]] = (
    CARGO_GOVERNO,
    CARGO_SENADO,
    CARGO_CAMARA,
    CARGO_ESTADUAL,
    CARGO_DISTRITAL,
)
_DF: Final = "DF"
_LIMIAR_TRIPLO: Final = 12
_TRIPLO: Final = 3

VAGAS_CAMARA_2026: Final[dict[str, int]] = {
    "AC": 8,
    "AL": 9,
    "AM": 8,
    "AP": 8,
    "BA": 39,
    "CE": 22,
    "DF": 8,
    "ES": 10,
    "GO": 17,
    "MA": 18,
    "MG": 53,
    "MS": 8,
    "MT": 8,
    "PA": 17,
    "PB": 12,
    "PE": 25,
    "PI": 10,
    "PR": 30,
    "RJ": 46,
    "RN": 8,
    "RO": 8,
    "RR": 8,
    "RS": 31,
    "SC": 16,
    "SE": 8,
    "SP": 70,
    "TO": 8,
}


def vagas_camara(uf: str) -> int:
    code = Uf(uf).code
    found = VAGAS_CAMARA_2026.get(code)
    if found is None:
        raise InvalidSeatRuleError("uf")
    return found


def vagas_assembleia(uf: str) -> int:
    federais = vagas_camara(uf)
    if federais <= _LIMIAR_TRIPLO:
        return _TRIPLO * federais
    return _TRIPLO * _LIMIAR_TRIPLO + (federais - _LIMIAR_TRIPLO)


def cargo_assembleia(uf: str) -> str:
    return CARGO_DISTRITAL if Uf(uf).code == _DF else CARGO_ESTADUAL


def ufs_com_vagas() -> tuple[str, ...]:
    return tuple(sorted(VAGAS_CAMARA_2026))
```

- [ ] **Step 5: Rodar até passar**

Run: `uv run pytest tests/domain/test_cadeiras.py -q && uv run ruff check src/eleicoes/domain tests/domain/test_cadeiras.py`
Expected: `8 passed`, depois `All checks passed!`.

**If Task Fails:** se a soma der 1.035, a regra do DF ficou de fora (`vagas_assembleia("DF")` precisa dar 24). Se aparecer `InvalidUfError`, o `Uf("ZZ")` é válido; quem barra o exterior é `VAGAS_CAMARA_2026.get`.

---

### Task 2: Registro de partidos e federações

**Files:**
- Create: `src/eleicoes/domain/federacoes.py`
- Test: `tests/domain/test_federacoes.py`

**Prerequisites:** Task 1. Confirmar a tabela de federações no site do TSE (seção Fontes). Se mudou, ajustar `REGISTRO_2026` e o primeiro teste **antes** do Step 3.

**Interfaces:**
- Produces: `Federacao(codigo, sigla, nome, partidos)`, `RegistroPartidario(ano, partidos, federacoes)` com `.legenda(partido) -> str` e `.federacao_de(partido)`, `REGISTRO_2026`, `REGISTROS`, `registro_partidario(ano)`.

- [ ] **Step 1: Teste** `tests/domain/test_federacoes.py`:

```python
"""Party registry: a federation is one proportional list."""

import pytest

from eleicoes.domain.errors import InvalidSeatRuleError, UnknownPartyRegistryError
from eleicoes.domain.federacoes import (
    REGISTRO_2026,
    Federacao,
    RegistroPartidario,
    registro_partidario,
)


def test_2026_has_five_federations_with_their_party_numbers() -> None:
    found = {federacao.codigo: federacao.partidos for federacao in REGISTRO_2026.federacoes}
    assert found == {
        "fe-brasil": (13, 65, 43),
        "psdb-cidadania": (45, 23),
        "psol-rede": (50, 18),
        "renovacao-solidaria": (25, 77),
        "uniao-progressista": (44, 11),
    }
    assert len(REGISTRO_2026.partidos) == 30


def test_legenda_is_the_federation_code_or_the_party_number() -> None:
    assert REGISTRO_2026.legenda(65) == "fe-brasil"
    assert REGISTRO_2026.legenda(11) == "uniao-progressista"
    assert REGISTRO_2026.legenda(22) == "22"
    assert REGISTRO_2026.federacao_de(22) is None


def test_registry_is_chosen_by_year() -> None:
    assert registro_partidario(2026) is REGISTRO_2026
    with pytest.raises(UnknownPartyRegistryError):
        registro_partidario(2022)


@pytest.mark.parametrize(
    "federacoes",
    [
        (Federacao("a", "A", "Federação A", (13, 99)),),
        (
            Federacao("a", "A", "Federação A", (13, 65)),
            Federacao("b", "B", "Federação B", (65, 43)),
        ),
        (
            Federacao("a", "A", "Federação A", (13, 65)),
            Federacao("a", "B", "Federação B", (43, 45)),
        ),
    ],
)
def test_registry_rejects_unknown_shared_or_repeated_members(
    federacoes: tuple[Federacao, ...],
) -> None:
    with pytest.raises(InvalidSeatRuleError):
        RegistroPartidario(2026, frozenset({13, 43, 45, 65}), federacoes)


@pytest.mark.parametrize(
    ("codigo", "partidos"),
    [("", (13, 65)), ("13", (13, 65)), ("a", (13,)), ("a", (13, 13))],
)
def test_federation_needs_a_code_and_two_distinct_parties(
    codigo: str,
    partidos: tuple[int, ...],
) -> None:
    with pytest.raises(InvalidSeatRuleError):
        Federacao(codigo, "A", "Federação A", partidos)


def test_party_numbers_stay_in_the_two_digit_range() -> None:
    with pytest.raises(InvalidSeatRuleError):
        RegistroPartidario(2026, frozenset({9}), ())
```

- [ ] **Step 2:** `uv run pytest tests/domain/test_federacoes.py -q` → falha com `ModuleNotFoundError: ... eleicoes.domain.federacoes`.

- [ ] **Step 3: Criar `src/eleicoes/domain/federacoes.py`:**

```python
"""Partidos e federações de cada eleição geral. Na proporcional, a federação é uma lista só.

Fontes de 2026 (conferidas em 2026-10-22):
- https://www.tse.jus.br/partidos/federacoes-registradas-no-tse
- https://www.tse.jus.br/comunicacao/noticias/2025/Dezembro/tse-aprova-criacao-da-federacao-renovacao-solidaria
- https://www.tse.jus.br/comunicacao/noticias/2026/Marco/tse-aprova-registro-da-federacao-uniao-progressista-1
- Lista de partidos, federações e candidaturas do 1º turno (DJE-TSE, 18/09/2026):
  https://sintse.tse.jus.br/documentos/2026/Set/23/diario-da-justica-eletronico-tres-destaques-edicoes-anteriores/lista-de-partidos-federacoes-coligacoes-candidatas-e-candidatos-eleicao-geral-federal-2026-1o-turno

Para atualizar: edite REGISTROS, rode os testes e reinicie a API. Os votos gravados
não mudam; as cadeiras são recalculadas na leitura.
"""

from dataclasses import dataclass
from typing import Final

from eleicoes.domain.errors import InvalidSeatRuleError, UnknownPartyRegistryError

_MIN_PARTIDO: Final = 10
_MAX_PARTIDO: Final = 99
_MIN_MEMBROS: Final = 2


@dataclass(frozen=True, slots=True)
class Federacao:
    codigo: str
    sigla: str
    nome: str
    partidos: tuple[int, ...]

    def __post_init__(self) -> None:
        if not self.codigo.strip() or not self.sigla.strip() or not self.nome.strip():
            raise InvalidSeatRuleError("federacao")
        if self.codigo.isdigit():
            raise InvalidSeatRuleError("codigo")
        if len(self.partidos) < _MIN_MEMBROS or len(set(self.partidos)) != len(self.partidos):
            raise InvalidSeatRuleError("partidos")


@dataclass(frozen=True, slots=True)
class RegistroPartidario:
    ano: int
    partidos: frozenset[int]
    federacoes: tuple[Federacao, ...]

    def __post_init__(self) -> None:
        if any(p < _MIN_PARTIDO or p > _MAX_PARTIDO for p in self.partidos):
            raise InvalidSeatRuleError("partidos")
        seen: set[int] = set()
        codes: set[str] = set()
        for federacao in self.federacoes:
            members = set(federacao.partidos)
            if not members <= self.partidos or members & seen:
                raise InvalidSeatRuleError("federacao")
            if federacao.codigo in codes:
                raise InvalidSeatRuleError("codigo")
            seen |= members
            codes.add(federacao.codigo)

    def legenda(self, partido: int) -> str:
        """The proportional list a party competes in: a federation code or the party number."""
        federacao = self.federacao_de(partido)
        return federacao.codigo if federacao is not None else str(partido)

    def federacao_de(self, partido: int) -> Federacao | None:
        for federacao in self.federacoes:
            if partido in federacao.partidos:
                return federacao
        return None


REGISTRO_2026: Final = RegistroPartidario(
    ano=2026,
    partidos=frozenset(
        {
            10,
            11,
            12,
            13,
            14,
            15,
            16,
            18,
            20,
            21,
            22,
            23,
            25,
            27,
            28,
            29,
            30,
            33,
            35,
            36,
            40,
            43,
            44,
            45,
            50,
            55,
            65,
            70,
            77,
            80,
        }
    ),
    federacoes=(
        Federacao("fe-brasil", "FE BRASIL", "Federação Brasil da Esperança", (13, 65, 43)),
        Federacao("psdb-cidadania", "PSDB CIDADANIA", "Federação PSDB Cidadania", (45, 23)),
        Federacao("psol-rede", "PSOL REDE", "Federação PSOL Rede", (50, 18)),
        Federacao(
            "renovacao-solidaria",
            "RENOVAÇÃO SOLIDÁRIA",
            "Federação Renovação Solidária",
            (25, 77),
        ),
        Federacao(
            "uniao-progressista",
            "UNIÃO PROGRESSISTA",
            "Federação União Progressista",
            (44, 11),
        ),
    ),
)

REGISTROS: Final[dict[int, RegistroPartidario]] = {REGISTRO_2026.ano: REGISTRO_2026}


def registro_partidario(ano: int) -> RegistroPartidario:
    found = REGISTROS.get(ano)
    if found is None:
        raise UnknownPartyRegistryError(ano)
    return found
```

- [ ] **Step 4:** `uv run pytest tests/domain/test_federacoes.py -q` → `11 passed`.

**If Task Fails:** um código de federação só com dígitos colide com o código de partido isolado. Por isso `Federacao` recusa `codigo.isdigit()`.

---

### Task 3: Algoritmo proporcional

**Files:**
- Create: `src/eleicoes/domain/proporcional.py`
- Test: `tests/domain/test_proporcional.py`

**Prerequisites:** Task 1.

**Interfaces:**
- Produces: `Candidato(numero, votos)`, `Lista(legenda, votos_legenda, candidatos)` com `.votos`, `Eleito(legenda, numero, votos, fase, empate)`, `ResultadoLista`, `ResultadoProporcional` com `.vagas_sem_candidato`, `quociente_eleitoral(validos, vagas)`, `distribuir(vagas, listas)` e as constantes `FASE_QUOCIENTE`, `FASE_MEDIA`, `FASE_MEDIA_LIVRE`.

Os casos foram calculados à mão. Os comentários no teste mostram a conta. Exemplo da fase 3: 700 válidos e 3 vagas dão QE 233 (700/3 = 233,3). A tem QP 1 e elege 1001. Na fase 2 ninguém é apto: o 1002 de A tem 10 votos, menos que 20% de 233 = 46,6; B e C ficam abaixo de 80% do QE = 186,4. Na fase 3, as médias são A 410/2 = 205, B 150 e C 140, e A leva o 1002 com 10 votos. Depois são A 410/3 = 136,7, B 150 e C 140, e B leva.

- [ ] **Step 1: Teste** `tests/domain/test_proporcional.py`:

```python
"""Proportional seats. Every expected number was worked out by hand."""

from collections.abc import Callable

import pytest

from eleicoes.domain.errors import InvalidSeatRuleError
from eleicoes.domain.proporcional import (
    FASE_MEDIA,
    FASE_MEDIA_LIVRE,
    FASE_QUOCIENTE,
    Candidato,
    Lista,
    ResultadoProporcional,
    distribuir,
    quociente_eleitoral,
)


def _lista(legenda: str, votos_legenda: int, *votos: tuple[int, int]) -> Lista:
    return Lista(legenda, votos_legenda, tuple(Candidato(numero, qtd) for numero, qtd in votos))


def _eleitos(resultado: ResultadoProporcional) -> list[tuple[int, str, bool]]:
    return [(eleito.numero, eleito.fase, eleito.empate) for eleito in resultado.eleitos]


def _por_lista(resultado: ResultadoProporcional) -> dict[str, tuple[int, int]]:
    return {item.legenda: (item.quociente_partidario, item.cadeiras) for item in resultado.listas}


def test_quociente_drops_one_half_and_rounds_up_above_it() -> None:
    assert quociente_eleitoral(1000, 8) == 125
    assert quociente_eleitoral(1004, 8) == 125
    assert quociente_eleitoral(1005, 8) == 126
    assert quociente_eleitoral(1010, 4) == 252
    assert quociente_eleitoral(3, 8) == 0


@pytest.mark.parametrize("vagas", [0, -1, True])
def test_quociente_needs_at_least_one_seat(vagas: int) -> None:
    with pytest.raises(InvalidSeatRuleError):
        quociente_eleitoral(10, vagas)


def test_list_without_a_twenty_percent_candidate_skips_the_second_phase() -> None:
    # 999 válidos, 4 vagas, QE 250. A tem a maior média (519/3), mas o 1003 tem 49 < 50.
    resultado = distribuir(
        4,
        [
            _lista("A", 20, (1001, 300), (1002, 150), (1003, 49)),
            _lista("B", 0, (2001, 200), (2002, 100)),
            _lista("C", 0, (3001, 180)),
        ],
    )
    assert resultado.quociente_eleitoral == 250
    assert _eleitos(resultado) == [
        (1001, FASE_QUOCIENTE, False),
        (1002, FASE_QUOCIENTE, False),
        (2001, FASE_QUOCIENTE, False),
        (2002, FASE_MEDIA, False),
    ]
    assert _por_lista(resultado) == {"A": (2, 2), "B": (1, 2), "C": (0, 0)}


def test_third_phase_opens_the_averages_to_every_list() -> None:
    # 700 válidos, 3 vagas, QE 233. Ninguém cumpre 80% + 20% depois do QP de A.
    resultado = distribuir(
        3,
        [
            _lista("A", 0, (1001, 400), (1002, 10)),
            _lista("B", 0, (2001, 150)),
            _lista("C", 0, (3001, 140)),
        ],
    )
    assert resultado.quociente_eleitoral == 233
    assert _eleitos(resultado) == [
        (1001, FASE_QUOCIENTE, False),
        (1002, FASE_MEDIA_LIVRE, False),
        (2001, FASE_MEDIA_LIVRE, False),
    ]


def test_no_list_reaching_the_quotient_still_uses_the_averages() -> None:
    # 400 válidos, 3 vagas, QE 133. Art. 111 caiu (ADI 7228): não elege os mais votados.
    resultado = distribuir(
        3,
        [
            _lista("A", 0, (1001, 90), (1002, 40)),
            _lista("B", 0, (2001, 110)),
            _lista("C", 0, (3001, 100)),
            _lista("D", 0, (4001, 60)),
        ],
    )
    assert resultado.quociente_eleitoral == 133
    assert _eleitos(resultado) == [
        (1001, FASE_MEDIA, False),
        (2001, FASE_MEDIA, False),
        (1002, FASE_MEDIA, False),
    ]
    assert _por_lista(resultado) == {"A": (0, 2), "B": (0, 1), "C": (0, 0), "D": (0, 0)}


def test_equal_averages_go_to_the_list_with_more_votes() -> None:
    # QE 100. Média de A = 180/2 = 90 e de B = 90/1 = 90; A tem mais votos (art. 11, § 6).
    resultado = distribuir(
        3,
        [
            _lista("A", 0, (1001, 100), (1002, 80)),
            _lista("B", 0, (2001, 90)),
            _lista("C", 0, (3001, 30)),
        ],
    )
    assert _eleitos(resultado) == [
        (1001, FASE_QUOCIENTE, False),
        (1002, FASE_MEDIA, False),
        (2001, FASE_MEDIA, False),
    ]


def test_full_tie_goes_to_the_smaller_code_and_is_flagged() -> None:
    resultado = distribuir(1, [_lista("B", 0, (2001, 50)), _lista("A", 0, (1001, 50))])
    assert _eleitos(resultado) == [(1001, FASE_MEDIA_LIVRE, True)]


def test_tied_candidates_go_to_the_smaller_number_and_are_flagged() -> None:
    resultado = distribuir(1, [_lista("A", 0, (1002, 60), (1001, 60))])
    assert _eleitos(resultado) == [(1001, FASE_QUOCIENTE, True)]


def test_average_divisor_counts_the_quotient_seat_left_empty() -> None:
    # 1010 válidos, 4 vagas, QE 252. A tem QP 2 e só o 1001 passa dos 10% (25,2).
    # Divisor de A = QP + médias + 1: 550/3 leva a 3ª vaga e 550/4 < 160 dá a 4ª a C.
    resultado = distribuir(
        4,
        [
            _lista("A", 480, (1001, 40), (1002, 20), (1003, 10)),
            _lista("B", 0, (2001, 300)),
            _lista("C", 0, (3001, 160)),
        ],
    )
    assert _eleitos(resultado) == [
        (1001, FASE_QUOCIENTE, False),
        (2001, FASE_QUOCIENTE, False),
        (1002, FASE_MEDIA_LIVRE, False),
        (3001, FASE_MEDIA_LIVRE, False),
    ]


def test_seats_without_candidates_stay_empty() -> None:
    resultado = distribuir(3, [_lista("A", 0, (1001, 300))])
    assert _eleitos(resultado) == [(1001, FASE_QUOCIENTE, False)]
    assert resultado.vagas_sem_candidato == 2


def test_no_valid_votes_fills_nothing() -> None:
    resultado = distribuir(8, [])
    assert resultado.quociente_eleitoral == 0
    assert resultado.eleitos == ()
    assert resultado.vagas_sem_candidato == 8


def test_legend_votes_count_for_the_list_and_candidates_are_sorted() -> None:
    lista = _lista("A", 7, (1002, 5), (1001, 9))
    assert lista.votos == 21
    assert [candidato.numero for candidato in lista.candidatos] == [1001, 1002]


@pytest.mark.parametrize(
    "build",
    [
        lambda: Lista(" ", 0, ()),
        lambda: Lista("A", -1, ()),
        lambda: Lista("A", 0, (Candidato(1001, 1), Candidato(1001, 2))),
        lambda: Candidato(1001, -1),
        lambda: distribuir(1, [Lista("A", 0, ()), Lista("A", 0, ())]),
    ],
)
def test_bad_input_is_rejected(build: Callable[[], object]) -> None:
    with pytest.raises(InvalidSeatRuleError):
        build()
```

- [ ] **Step 2:** `uv run pytest tests/domain/test_proporcional.py -q` → `ModuleNotFoundError`.

- [ ] **Step 3: Criar `src/eleicoes/domain/proporcional.py`:**

```python
"""Proportional seats: Código Eleitoral arts. 106-109 after ADIs 7228, 7263 and 7325.

1. Quociente partidário, only for candidates with at least 10% of the quociente eleitoral.
2. Highest averages among lists with at least 80% of the quotient whose best remaining
   candidate has at least 20% of it (art. 109, I-II and § 2).
3. Highest averages among every list, without thresholds (art. 109, III, as the STF read it).

Average = list votes / (quociente partidário + seats won by average + 1), as in
Res.-TSE 23.677/2021, art. 11, §§ 1 and 5. Ties: more list votes, then more votes for the
next candidate (art. 11, §§ 6-7), then the smaller list code. The data has no candidate
age (art. 110), so a tie between candidates goes to the smaller number and is flagged.
"""

from collections.abc import Sequence
from dataclasses import dataclass, replace
from fractions import Fraction
from typing import Final

from eleicoes.domain.errors import InvalidSeatRuleError

FASE_QUOCIENTE: Final = "quociente"
FASE_MEDIA: Final = "media"
FASE_MEDIA_LIVRE: Final = "media_livre"


@dataclass(frozen=True, slots=True)
class Candidato:
    numero: int
    votos: int

    def __post_init__(self) -> None:
        _require_count(self.numero, "numero")
        _require_count(self.votos, "votos")


@dataclass(frozen=True, slots=True)
class Lista:
    """One party alone or one federation. Candidates of a federation keep their own number."""

    legenda: str
    votos_legenda: int
    candidatos: tuple[Candidato, ...]

    def __post_init__(self) -> None:
        if not self.legenda.strip():
            raise InvalidSeatRuleError("legenda")
        _require_count(self.votos_legenda, "votos_legenda")
        numbers = [candidato.numero for candidato in self.candidatos]
        if len(numbers) != len(set(numbers)):
            raise InvalidSeatRuleError("numero")
        ordered = tuple(sorted(self.candidatos, key=lambda c: (-c.votos, c.numero)))
        object.__setattr__(self, "candidatos", ordered)

    @property
    def votos(self) -> int:
        return self.votos_legenda + sum(candidato.votos for candidato in self.candidatos)


@dataclass(frozen=True, slots=True)
class Eleito:
    legenda: str
    numero: int
    votos: int
    fase: str
    empate: bool


@dataclass(frozen=True, slots=True)
class ResultadoLista:
    legenda: str
    votos: int
    votos_legenda: int
    quociente_partidario: int
    cadeiras_quociente: int
    cadeiras_media: int
    cadeiras_media_livre: int

    @property
    def cadeiras(self) -> int:
        return self.cadeiras_quociente + self.cadeiras_media + self.cadeiras_media_livre


@dataclass(frozen=True, slots=True)
class ResultadoProporcional:
    vagas: int
    votos_validos: int
    quociente_eleitoral: int
    listas: tuple[ResultadoLista, ...]
    eleitos: tuple[Eleito, ...]

    @property
    def vagas_sem_candidato(self) -> int:
        return self.vagas - len(self.eleitos)


def quociente_eleitoral(votos_validos: int, vagas: int) -> int:
    """Art. 106: a fraction of one half or less is dropped; more than one half rounds up."""
    _require_count(votos_validos, "votos_validos")
    if isinstance(vagas, bool) or not isinstance(vagas, int) or vagas < 1:
        raise InvalidSeatRuleError("vagas")
    quotient, remainder = divmod(votos_validos, vagas)
    return quotient + 1 if 2 * remainder > vagas else quotient


def distribuir(vagas: int, listas: Sequence[Lista]) -> ResultadoProporcional:
    codes = [lista.legenda for lista in listas]
    if len(codes) != len(set(codes)):
        raise InvalidSeatRuleError("legenda")
    validos = sum(lista.votos for lista in listas)
    qe = quociente_eleitoral(validos, vagas)
    if qe == 0:
        return ResultadoProporcional(vagas, validos, 0, (), ())
    state = _Apuracao(vagas, qe, tuple(sorted(listas, key=lambda lista: lista.legenda)))
    state.quocientes()
    state.medias(FASE_MEDIA)
    state.medias(FASE_MEDIA_LIVRE)
    return state.resultado(validos)


class _Apuracao:
    def __init__(self, vagas: int, qe: int, listas: tuple[Lista, ...]) -> None:
        self._vagas = vagas
        self._qe = qe
        self._listas = listas
        self._qp = {lista.legenda: lista.votos // qe for lista in listas}
        self._usados = {lista.legenda: 0 for lista in listas}
        self._por_fase = {
            (lista.legenda, fase): 0
            for lista in listas
            for fase in (FASE_QUOCIENTE, FASE_MEDIA, FASE_MEDIA_LIVRE)
        }
        self._eleitos: list[Eleito] = []

    def quocientes(self) -> None:
        for lista in self._listas:
            for _ in range(self._qp[lista.legenda]):
                proximo = self._proximo(lista)
                if proximo is None or 10 * proximo.votos < self._qe:
                    break
                self._eleger(lista, FASE_QUOCIENTE, empate_media=False)

    def medias(self, fase: str) -> None:
        while len(self._eleitos) < self._vagas:
            escolhida = self._maior_media(fase)
            if escolhida is None:
                return
            lista, empate = escolhida
            self._eleger(lista, fase, empate_media=empate)

    def resultado(self, validos: int) -> ResultadoProporcional:
        listas = tuple(
            ResultadoLista(
                lista.legenda,
                lista.votos,
                lista.votos_legenda,
                self._qp[lista.legenda],
                self._por_fase[(lista.legenda, FASE_QUOCIENTE)],
                self._por_fase[(lista.legenda, FASE_MEDIA)],
                self._por_fase[(lista.legenda, FASE_MEDIA_LIVRE)],
            )
            for lista in self._listas
        )
        return ResultadoProporcional(
            self._vagas, validos, self._qe, listas, self._com_empate_de_nome()
        )

    def _maior_media(self, fase: str) -> tuple[Lista, bool] | None:
        candidatas = [lista for lista in self._listas if self._pode_disputar(lista, fase)]
        if not candidatas:
            return None
        chaves = {lista.legenda: self._chave(lista) for lista in candidatas}
        melhor = min(candidatas, key=lambda lista: (chaves[lista.legenda], lista.legenda))
        empatadas = sum(
            1 for lista in candidatas if chaves[lista.legenda] == chaves[melhor.legenda]
        )
        return melhor, empatadas > 1

    def _pode_disputar(self, lista: Lista, fase: str) -> bool:
        proximo = self._proximo(lista)
        if proximo is None:
            return False
        if fase == FASE_MEDIA_LIVRE:
            return True
        return 5 * lista.votos >= 4 * self._qe and 5 * proximo.votos >= self._qe

    def _chave(self, lista: Lista) -> tuple[Fraction, int, int]:
        """Sorts ascending: the highest average, list votes and next-candidate votes come first."""
        proximo = self._proximo(lista)
        votos_proximo = proximo.votos if proximo is not None else 0
        return (-Fraction(lista.votos, self._divisor(lista)), -lista.votos, -votos_proximo)

    def _divisor(self, lista: Lista) -> int:
        legenda = lista.legenda
        medias = self._por_fase[(legenda, FASE_MEDIA)] + self._por_fase[(legenda, FASE_MEDIA_LIVRE)]
        return self._qp[legenda] + medias + 1

    def _proximo(self, lista: Lista) -> Candidato | None:
        usados = self._usados[lista.legenda]
        if usados >= len(lista.candidatos):
            return None
        return lista.candidatos[usados]

    def _eleger(self, lista: Lista, fase: str, *, empate_media: bool) -> None:
        usados = self._usados[lista.legenda]
        candidato = lista.candidatos[usados]
        self._usados[lista.legenda] = usados + 1
        self._por_fase[(lista.legenda, fase)] += 1
        self._eleitos.append(
            Eleito(lista.legenda, candidato.numero, candidato.votos, fase, empate_media)
        )

    def _com_empate_de_nome(self) -> tuple[Eleito, ...]:
        """Flags the last elected candidate of a list who ties with the first one left out."""
        flagged: list[Eleito] = []
        for eleito in self._eleitos:
            lista = next(item for item in self._listas if item.legenda == eleito.legenda)
            usados = self._usados[lista.legenda]
            fora = lista.candidatos[usados] if usados < len(lista.candidatos) else None
            empate = fora is not None and fora.votos == eleito.votos
            flagged.append(replace(eleito, empate=eleito.empate or empate))
        return tuple(flagged)


def _require_count(value: int, field: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise InvalidSeatRuleError(field)
```

- [ ] **Step 4:** `uv run pytest tests/domain/test_proporcional.py -q` → `19 passed`. Depois `uv run mypy` → `Success`.

**If Task Fails:**
- Falha em `test_average_divisor...`: o divisor está usando as vagas preenchidas em vez do QP (D10).
- Falha em `test_list_without_a_twenty_percent...`: a fase 2 está escolhendo a maior média antes de filtrar a aptidão (D9).

---

### Task 4: Senado e governador

**Files:**
- Create: `src/eleicoes/domain/majoritario.py`
- Test: `tests/domain/test_majoritario.py`

**Prerequisites:** Task 1.

**Interfaces:**
- Produces: `VotoCandidato(numero, partido, votos)`, `ResultadoSenado(uf, votos_validos, eleitos, empate)`, `ResultadoGoverno(uf, votos_validos, situacao, candidatos, empate)` com `.eleito` e `.finalistas`, `eleger_senado(uf, votos, vagas=2)`, `apurar_governo(uf, votos)`, `SITUACAO_*`, `VAGAS_SENADO_2026`.

- [ ] **Step 1: Teste** `tests/domain/test_majoritario.py`:

```python
"""Senate and governor from first-round votes."""

import pytest

from eleicoes.domain.errors import InvalidSeatRuleError
from eleicoes.domain.majoritario import (
    SITUACAO_ELEITO,
    SITUACAO_SEGUNDO_TURNO,
    SITUACAO_SEM_VOTOS,
    VotoCandidato,
    apurar_governo,
    eleger_senado,
)


def _voto(numero: int, votos: int) -> VotoCandidato:
    return VotoCandidato(numero, numero // 10 if numero > 99 else numero, votos)


def test_senate_elects_the_two_most_voted() -> None:
    resultado = eleger_senado("AC", [_voto(100, 157), _voto(222, 223), _voto(111, 145)])
    assert [eleito.numero for eleito in resultado.eleitos] == [222, 100]
    assert resultado.votos_validos == 525
    assert resultado.empate is False


def test_senate_flags_a_tie_for_the_second_seat() -> None:
    resultado = eleger_senado("AC", [_voto(222, 9), _voto(111, 5), _voto(100, 5)])
    assert [eleito.numero for eleito in resultado.eleitos] == [222, 100]
    assert resultado.empate is True


def test_governor_needs_more_than_half_of_the_valid_votes() -> None:
    eleito = apurar_governo("SE", [_voto(13, 51), _voto(22, 49)])
    assert eleito.situacao == SITUACAO_ELEITO
    assert eleito.eleito == _voto(13, 51)
    assert eleito.finalistas == ()
    metade = apurar_governo("SE", [_voto(13, 50), _voto(22, 30), _voto(45, 20)])
    assert metade.situacao == SITUACAO_SEGUNDO_TURNO
    assert metade.eleito is None
    assert [item.numero for item in metade.finalistas] == [13, 22]


def test_governor_without_votes_and_tied_runoff() -> None:
    assert apurar_governo("SE", []).situacao == SITUACAO_SEM_VOTOS
    empate = apurar_governo("SE", [_voto(13, 40), _voto(45, 30), _voto(22, 30)])
    assert [item.numero for item in empate.finalistas] == [13, 22]
    assert empate.empate is True


def test_repeated_number_is_rejected() -> None:
    with pytest.raises(InvalidSeatRuleError):
        eleger_senado("AC", [_voto(222, 1), _voto(222, 2)])
    with pytest.raises(InvalidSeatRuleError):
        VotoCandidato(222, 22, -1)
```

- [ ] **Step 2:** `uv run pytest tests/domain/test_majoritario.py -q` → `ModuleNotFoundError`.

- [ ] **Step 3: Criar `src/eleicoes/domain/majoritario.py`:**

```python
"""Senate and governor races from first-round nominal votes.

Senado 2026: two seats per UF (renewal of two thirds), the two most voted candidates.
Governador: more than half of the valid votes wins in the first round (CF art. 28 with
art. 77, § 2); otherwise the two most voted go to the second round. A tie the data cannot
break (age, art. 77, § 5) goes to the smaller number and is flagged.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Final

from eleicoes.domain.errors import InvalidSeatRuleError

SITUACAO_ELEITO: Final = "eleito"
SITUACAO_SEGUNDO_TURNO: Final = "segundo_turno"
SITUACAO_SEM_VOTOS: Final = "sem_votos"
VAGAS_SENADO_2026: Final = 2
_FINALISTAS: Final = 2


@dataclass(frozen=True, slots=True)
class VotoCandidato:
    numero: int
    partido: int
    votos: int

    def __post_init__(self) -> None:
        for value, field in (
            (self.numero, "numero"),
            (self.partido, "partido"),
            (self.votos, "votos"),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise InvalidSeatRuleError(field)


@dataclass(frozen=True, slots=True)
class ResultadoSenado:
    uf: str
    votos_validos: int
    eleitos: tuple[VotoCandidato, ...]
    empate: bool


@dataclass(frozen=True, slots=True)
class ResultadoGoverno:
    uf: str
    votos_validos: int
    situacao: str
    candidatos: tuple[VotoCandidato, ...]
    empate: bool

    @property
    def eleito(self) -> VotoCandidato | None:
        if self.situacao != SITUACAO_ELEITO:
            return None
        return self.candidatos[0]

    @property
    def finalistas(self) -> tuple[VotoCandidato, ...]:
        if self.situacao != SITUACAO_SEGUNDO_TURNO:
            return ()
        return self.candidatos[:_FINALISTAS]


def eleger_senado(
    uf: str, votos: Sequence[VotoCandidato], vagas: int = VAGAS_SENADO_2026
) -> ResultadoSenado:
    ordered = _ordered(votos)
    eleitos = ordered[:vagas]
    return ResultadoSenado(uf, _validos(ordered), eleitos, _tie_at(ordered, vagas))


def apurar_governo(uf: str, votos: Sequence[VotoCandidato]) -> ResultadoGoverno:
    ordered = _ordered(votos)
    validos = _validos(ordered)
    if validos == 0:
        return ResultadoGoverno(uf, 0, SITUACAO_SEM_VOTOS, ordered, False)
    if 2 * ordered[0].votos > validos:
        return ResultadoGoverno(uf, validos, SITUACAO_ELEITO, ordered, False)
    return ResultadoGoverno(
        uf, validos, SITUACAO_SEGUNDO_TURNO, ordered, _tie_at(ordered, _FINALISTAS)
    )


def _ordered(votos: Sequence[VotoCandidato]) -> tuple[VotoCandidato, ...]:
    numbers = [voto.numero for voto in votos]
    if len(numbers) != len(set(numbers)):
        raise InvalidSeatRuleError("numero")
    return tuple(sorted(votos, key=lambda voto: (-voto.votos, voto.numero)))


def _validos(votos: Sequence[VotoCandidato]) -> int:
    return sum(voto.votos for voto in votos)


def _tie_at(ordered: tuple[VotoCandidato, ...], cut: int) -> bool:
    """True when the last one in and the first one out have the same votes."""
    if len(ordered) <= cut or cut == 0:
        return False
    return ordered[cut - 1].votos == ordered[cut].votos
```

- [ ] **Step 4:** `uv run pytest tests/domain/test_majoritario.py -q` → `5 passed`.

**If Task Fails:** com exatamente 50%, o governador **não** se elege (`2·50 > 100` é falso). O teste `metade` cobre esse caso.

---

### Task 5: Simulação completa e contrato por partido

**Files:**
- Create: `src/eleicoes/domain/simulacao_cadeiras.py`
- Test: `tests/domain/test_simulacao_cadeiras.py`

**Prerequisites:** Tasks 1–4.

**Interfaces:**
- Consumes: `partido_do_numero(tipo_voto, numero)` de `eleicoes.domain.boletim_consulta` (já existe e levanta `InvalidNumeroError` fora das faixas).
- Produces: `VotoApurado(cargo, uf, tipo_voto, numero, votos)`, `CasaUf`, `CasaSimulada` (com `.vagas_simuladas`, `.cadeiras_por_partido()` e `.cadeiras_por_legenda()`), `SenadoSimulado`, `GovernoSimulado`, `ForcaPartido`, `SimulacaoCadeiras` (com `.partidos()`), `simular_cadeiras(ano, turno, votos, registro)`, `NOTAS`, `CASA_CAMARA`, `CASA_ASSEMBLEIAS`.

O fixture do primeiro teste também mostra um efeito real. No AC (8 vagas, QE 100), a Fe Brasil soma 410 votos e tem QP 4, mas só 2 candidatos. A União Progressista leva uma vaga por média (100/2 = 50). Duas vagas ficam sem candidato.

- [ ] **Step 1: Teste** `tests/domain/test_simulacao_cadeiras.py`:

```python
"""Whole simulation from stored votes. Two small UFs keep the numbers readable."""

import pytest

from eleicoes.domain.errors import InvalidSeatRuleError
from eleicoes.domain.federacoes import REGISTRO_2026
from eleicoes.domain.simulacao_cadeiras import ForcaPartido, VotoApurado, simular_cadeiras


def _v(cargo: str, uf: str, tipo: str, numero: int, votos: int) -> VotoApurado:
    return VotoApurado(cargo, uf, tipo, numero, votos)


_VOTOS = (
    # Câmara AC, 8 vagas, 800 válidos, QE 100. PT + PCdoB somam como Fe Brasil.
    _v("deputadoFederal", "AC", "nominal", 1301, 250),
    _v("deputadoFederal", "AC", "nominal", 6501, 150),
    _v("deputadoFederal", "AC", "legenda", 65, 10),
    _v("deputadoFederal", "AC", "nominal", 2201, 200),
    _v("deputadoFederal", "AC", "nominal", 2202, 90),
    _v("deputadoFederal", "AC", "nominal", 4401, 60),
    _v("deputadoFederal", "AC", "nominal", 1101, 40),
    # Prefixo 99 não é partido: vira nulo.
    _v("deputadoFederal", "AC", "nominal", 9901, 7),
    _v("deputadoDistrital", "DF", "nominal", 1501, 100),
    _v("senador", "AC", "nominal", 222, 300),
    _v("senador", "AC", "nominal", 131, 200),
    _v("senador", "AC", "nominal", 100, 100),
    _v("governador", "AC", "nominal", 13, 600),
    _v("governador", "AC", "nominal", 22, 400),
    _v("governador", "DF", "nominal", 22, 450),
    _v("governador", "DF", "nominal", 15, 350),
    _v("governador", "DF", "nominal", 13, 200),
    # O exterior não elege ninguém.
    _v("governador", "ZZ", "nominal", 13, 5),
)


def test_federation_is_one_list_and_seats_go_to_each_candidate_party() -> None:
    simulacao = simular_cadeiras(2026, 1, _VOTOS, REGISTRO_2026)
    ac = simulacao.camara.ufs[0]
    assert ac.uf == "AC"
    assert ac.resultado.votos_validos == 800
    assert ac.resultado.quociente_eleitoral == 100
    # QP: Fe Brasil 4, PL 2, UP 1. Fe Brasil só tem 2 candidatos; UP leva 1 média (100/2);
    # as 2 vagas restantes ficam sem candidato.
    assert simulacao.camara.cadeiras_por_legenda() == {
        "fe-brasil": 2,
        "22": 2,
        "uniao-progressista": 2,
    }
    assert simulacao.camara.cadeiras_por_partido() == {13: 1, 65: 1, 22: 2, 44: 1, 11: 1}
    assert ac.resultado.vagas_sem_candidato == 2
    assert simulacao.descartados == 12


def test_missing_ufs_are_listed_and_df_assembly_reads_distrital() -> None:
    simulacao = simular_cadeiras(2026, 1, _VOTOS, REGISTRO_2026)
    assert simulacao.camara.vagas == 513
    assert simulacao.camara.vagas_simuladas == 8
    assert len(simulacao.camara.ufs_sem_votos) == 26
    assert [item.uf for item in simulacao.assembleias.ufs] == ["DF"]
    assert simulacao.assembleias.ufs[0].cargo == "deputadoDistrital"
    assert simulacao.assembleias.vagas == 1059


def test_senate_and_governor_feed_the_party_contract() -> None:
    simulacao = simular_cadeiras(2026, 1, _VOTOS, REGISTRO_2026)
    assert simulacao.senado.cadeiras_por_partido() == {22: 1, 13: 1}
    assert simulacao.governo.eleitos_por_partido() == {13: 1}
    assert simulacao.governo.segundo_turno_por_partido() == {22: 1, 15: 1}
    linhas = {linha.partido: linha for linha in simulacao.partidos()}
    assert linhas[13] == ForcaPartido(13, "fe-brasil", 1, 0, 1, 1, 0)
    assert linhas[22] == ForcaPartido(22, "22", 2, 0, 1, 0, 1)
    assert linhas[15] == ForcaPartido(15, "15", 0, 1, 0, 0, 1)
    assert [linha.partido for linha in simulacao.partidos()][:2] == [22, 13]


def test_registry_year_must_match() -> None:
    with pytest.raises(InvalidSeatRuleError):
        simular_cadeiras(2030, 1, (), REGISTRO_2026)


@pytest.mark.parametrize(
    ("tipo", "numero", "votos"),
    [("branco", 0, 1), ("nominal", -1, 1), ("nominal", 1301, -1)],
)
def test_stored_vote_rejects_bad_rows(tipo: str, numero: int, votos: int) -> None:
    with pytest.raises(InvalidSeatRuleError):
        VotoApurado("deputadoFederal", "AC", tipo, numero, votos)
```

- [ ] **Step 2:** `uv run pytest tests/domain/test_simulacao_cadeiras.py -q` → `ModuleNotFoundError`.

- [ ] **Step 3: Criar `src/eleicoes/domain/simulacao_cadeiras.py`:**

```python
"""Seat estimate from stored first-round votes per candidate number. Pure; no IO.

A number whose prefix is not a registered party is treated as null and only counted in
descartados. Candidates whose registration was rejected cannot be told apart in the
boletim, so their votes stay valid here: this is an estimate, not the official result.
"""

from collections import defaultdict
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from typing import Final, TypeAlias

from eleicoes.domain.boletim_consulta import partido_do_numero
from eleicoes.domain.cadeiras import (
    CARGO_CAMARA,
    CARGO_GOVERNO,
    CARGO_SENADO,
    cargo_assembleia,
    ufs_com_vagas,
    vagas_assembleia,
    vagas_camara,
)
from eleicoes.domain.errors import InvalidNumeroError, InvalidSeatRuleError
from eleicoes.domain.federacoes import RegistroPartidario
from eleicoes.domain.majoritario import (
    VAGAS_SENADO_2026,
    ResultadoGoverno,
    ResultadoSenado,
    VotoCandidato,
    apurar_governo,
    eleger_senado,
)
from eleicoes.domain.proporcional import Candidato, Lista, ResultadoProporcional, distribuir
from eleicoes.domain.values import ElectionYear, Turno, Uf

CASA_CAMARA: Final = "camara"
CASA_ASSEMBLEIAS: Final = "assembleias"
_NOMINAL: Final = "nominal"
_LEGENDA: Final = "legenda"
_TIPOS: Final = frozenset({_NOMINAL, _LEGENDA})
_ABROAD: Final = "ZZ"


@dataclass(frozen=True, slots=True)
class VotoApurado:
    cargo: str
    uf: str
    tipo_voto: str
    numero: int
    votos: int

    def __post_init__(self) -> None:
        if not self.cargo.strip():
            raise InvalidSeatRuleError("cargo")
        object.__setattr__(self, "uf", Uf(self.uf).code)
        if self.tipo_voto not in _TIPOS:
            raise InvalidSeatRuleError("tipo_voto")
        for value, field in ((self.numero, "numero"), (self.votos, "votos")):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise InvalidSeatRuleError(field)


@dataclass(frozen=True, slots=True)
class CasaUf:
    uf: str
    cargo: str
    resultado: ResultadoProporcional


@dataclass(frozen=True, slots=True)
class CasaSimulada:
    casa: str
    vagas: int
    ufs: tuple[CasaUf, ...]
    ufs_sem_votos: tuple[str, ...]

    @property
    def vagas_simuladas(self) -> int:
        return sum(item.resultado.vagas for item in self.ufs)

    def cadeiras_por_partido(self) -> dict[int, int]:
        counts: dict[int, int] = defaultdict(int)
        for item in self.ufs:
            for eleito in item.resultado.eleitos:
                counts[partido_do_numero(_NOMINAL, eleito.numero)] += 1
        return dict(counts)

    def cadeiras_por_legenda(self) -> dict[str, int]:
        counts: dict[str, int] = defaultdict(int)
        for item in self.ufs:
            for eleito in item.resultado.eleitos:
                counts[eleito.legenda] += 1
        return dict(counts)


@dataclass(frozen=True, slots=True)
class SenadoSimulado:
    vagas: int
    ufs: tuple[ResultadoSenado, ...]
    ufs_sem_votos: tuple[str, ...]

    def cadeiras_por_partido(self) -> dict[int, int]:
        counts: dict[int, int] = defaultdict(int)
        for item in self.ufs:
            for eleito in item.eleitos:
                counts[eleito.partido] += 1
        return dict(counts)


@dataclass(frozen=True, slots=True)
class GovernoSimulado:
    ufs: tuple[ResultadoGoverno, ...]
    ufs_sem_votos: tuple[str, ...]

    def eleitos_por_partido(self) -> dict[int, int]:
        counts: dict[int, int] = defaultdict(int)
        for item in self.ufs:
            if item.eleito is not None:
                counts[item.eleito.partido] += 1
        return dict(counts)

    def segundo_turno_por_partido(self) -> dict[int, int]:
        counts: dict[int, int] = defaultdict(int)
        for item in self.ufs:
            for finalista in item.finalistas:
                counts[finalista.partido] += 1
        return dict(counts)


@dataclass(frozen=True, slots=True)
class ForcaPartido:
    """One row of the contract the força partidária scoreboard reads."""

    partido: int
    legenda: str
    camara: int
    assembleias: int
    senado: int
    governadores: int
    governadores_segundo_turno: int


@dataclass(frozen=True, slots=True)
class SimulacaoCadeiras:
    ano: int
    turno: int
    registro: RegistroPartidario
    camara: CasaSimulada
    assembleias: CasaSimulada
    senado: SenadoSimulado
    governo: GovernoSimulado
    descartados: int

    def partidos(self) -> tuple[ForcaPartido, ...]:
        camara = self.camara.cadeiras_por_partido()
        assembleias = self.assembleias.cadeiras_por_partido()
        senado = self.senado.cadeiras_por_partido()
        eleitos = self.governo.eleitos_por_partido()
        segundo = self.governo.segundo_turno_por_partido()
        found = set(camara) | set(assembleias) | set(senado) | set(eleitos) | set(segundo)
        rows = (
            ForcaPartido(
                partido,
                self.registro.legenda(partido),
                camara.get(partido, 0),
                assembleias.get(partido, 0),
                senado.get(partido, 0),
                eleitos.get(partido, 0),
                segundo.get(partido, 0),
            )
            for partido in found
        )
        return tuple(
            sorted(rows, key=lambda row: (-row.camara, -row.assembleias, -row.senado, row.partido))
        )


def simular_cadeiras(
    ano: int,
    turno: int,
    votos: Sequence[VotoApurado],
    registro: RegistroPartidario,
) -> SimulacaoCadeiras:
    year = ElectionYear(ano).value
    if registro.ano != year:
        raise InvalidSeatRuleError("ano")
    validos, descartados = _split(votos, registro)
    by_cargo_uf: dict[tuple[str, str], list[VotoApurado]] = defaultdict(list)
    for voto in validos:
        by_cargo_uf[(voto.cargo, voto.uf)].append(voto)
    ufs = ufs_com_vagas()
    return SimulacaoCadeiras(
        year,
        Turno(turno).value,
        registro,
        _casa(CASA_CAMARA, ufs, _cargo_camara, vagas_camara, by_cargo_uf, registro),
        _casa(CASA_ASSEMBLEIAS, ufs, cargo_assembleia, vagas_assembleia, by_cargo_uf, registro),
        _senado(ufs, by_cargo_uf),
        _governo(ufs, by_cargo_uf),
        descartados,
    )


def _cargo_camara(_uf: str) -> str:
    return CARGO_CAMARA


def _split(
    votos: Iterable[VotoApurado], registro: RegistroPartidario
) -> tuple[list[VotoApurado], int]:
    kept: list[VotoApurado] = []
    dropped = 0
    for voto in votos:
        if voto.uf == _ABROAD or _partido(voto) not in registro.partidos:
            dropped += voto.votos
            continue
        kept.append(voto)
    return kept, dropped


def _partido(voto: VotoApurado) -> int | None:
    try:
        return partido_do_numero(voto.tipo_voto, voto.numero)
    except InvalidNumeroError:
        return None


_Grouped: TypeAlias = dict[tuple[str, str], list[VotoApurado]]


def _casa(
    casa: str,
    ufs: tuple[str, ...],
    cargo_of: Callable[[str], str],
    vagas_of: Callable[[str], int],
    by_cargo_uf: _Grouped,
    registro: RegistroPartidario,
) -> CasaSimulada:
    found: list[CasaUf] = []
    missing: list[str] = []
    for uf in ufs:
        cargo = cargo_of(uf)
        rows = by_cargo_uf.get((cargo, uf), [])
        if not rows:
            missing.append(uf)
            continue
        found.append(CasaUf(uf, cargo, distribuir(vagas_of(uf), _listas(rows, registro))))
    total = sum(vagas_of(uf) for uf in ufs)
    return CasaSimulada(casa, total, tuple(found), tuple(missing))


def _listas(rows: Sequence[VotoApurado], registro: RegistroPartidario) -> tuple[Lista, ...]:
    legenda: dict[str, int] = defaultdict(int)
    nominais: dict[str, list[Candidato]] = defaultdict(list)
    for row in rows:
        party = partido_do_numero(row.tipo_voto, row.numero)
        key = registro.legenda(party)
        if row.tipo_voto == _LEGENDA:
            legenda[key] += row.votos
        else:
            nominais[key].append(Candidato(row.numero, row.votos))
    keys = sorted(set(legenda) | set(nominais))
    return tuple(Lista(key, legenda.get(key, 0), tuple(nominais.get(key, []))) for key in keys)


def _majoritarios(rows: Sequence[VotoApurado]) -> tuple[VotoCandidato, ...]:
    return tuple(
        VotoCandidato(row.numero, partido_do_numero(_NOMINAL, row.numero), row.votos)
        for row in rows
        if row.tipo_voto == _NOMINAL
    )


def _senado(ufs: tuple[str, ...], by_cargo_uf: _Grouped) -> SenadoSimulado:
    found: list[ResultadoSenado] = []
    missing: list[str] = []
    for uf in ufs:
        rows = _majoritarios(by_cargo_uf.get((CARGO_SENADO, uf), []))
        if not rows:
            missing.append(uf)
            continue
        found.append(eleger_senado(uf, rows))
    return SenadoSimulado(VAGAS_SENADO_2026 * len(ufs), tuple(found), tuple(missing))


def _governo(ufs: tuple[str, ...], by_cargo_uf: _Grouped) -> GovernoSimulado:
    found: list[ResultadoGoverno] = []
    missing: list[str] = []
    for uf in ufs:
        rows = _majoritarios(by_cargo_uf.get((CARGO_GOVERNO, uf), []))
        if not rows:
            missing.append(uf)
            continue
        found.append(apurar_governo(uf, rows))
    return GovernoSimulado(tuple(found), tuple(missing))


NOTAS: Final[tuple[str, ...]] = (
    "É uma estimativa feita com os votos do 1º turno gravados nos boletins de urna. "
    "Não é o resultado oficial do TSE.",
    "Votos em candidatos com registro indeferido ou sub judice contam como válidos aqui. "
    "Na totalização oficial eles são anulados, o que muda o quociente eleitoral.",
    "Na Câmara e nas Assembleias, a federação conta como um partido só. A cadeira fica "
    "com o partido do número do candidato eleito.",
    "As sobras seguem o STF (ADIs 7228, 7263 e 7325): primeiro as legendas com 80% do "
    "quociente e candidato com 20%; depois todas, pelas maiores médias.",
    "Empate entre candidatos se decide pela idade, que o boletim não traz. A estimativa "
    "usa o menor número e marca o empate.",
    "Governador: mais da metade dos votos válidos elege no 1º turno. Senado: os dois "
    "mais votados de cada UF.",
)
```

- [ ] **Step 4: Verificar o bloco do domínio**

Run: `uv run pytest tests/domain -q && uv run ruff format src/eleicoes/domain/{cadeiras,federacoes,proporcional,majoritario,simulacao_cadeiras}.py tests/domain/test_{cadeiras,federacoes,proporcional,majoritario,simulacao_cadeiras}.py && uv run ruff check . && uv run mypy`
Expected: todos os testes de `tests/domain` passam; `ruff format` diz `10 files left unchanged`; `All checks passed!`; `Success: no issues found`.

---

### Task 6: Code Review (domínio)

1. **REQUIRED SUB-SKILL:** Use jarvis:codereview — dispatch all reviewers in parallel. Diff: `git diff` + arquivos novos de `src/eleicoes/domain` e `tests/domain`.
2. **Foco extra para o business-logic-reviewer:** D8–D13, contra os textos legais da seção Fontes.
3. **Handle findings by severity:** see jarvis:codereview severity rules.
4. **Proceed only when:** zero Critical/High/Medium issues remain.

---

### Task 7: Migração 0004 e modelos ORM

**Files:**
- Create: `src/eleicoes/adapters/orm/migrations/versions/r0004_relatorio_cadeiras.py`
- Modify: `src/eleicoes/adapters/orm/models.py` (duas classes ao fim)
- Modify: `tests/adapters/test_orm_migrate.py` (cadeia até 0004 e dois testes novos)

**Prerequisites:** Task 5. `migrate.py` **não** muda: `BASELINE_TABLES` descreve só a base 0001.

- [ ] **Step 1: Ajustar o teste de migração** (diff exato):

```diff
--- a/tests/adapters/test_orm_migrate.py
+++ b/tests/adapters/test_orm_migrate.py
@@ -129,10 +129,10 @@
     session.close()
 
 
-def test_migrations_form_one_linear_chain_ending_at_0003() -> None:
+def test_migrations_form_one_linear_chain_ending_at_0004() -> None:
     script = ScriptDirectory.from_config(migration_config())
-    assert head_revision() == "0003"
-    assert [item.revision for item in script.walk_revisions()] == ["0003", "0002", "0001"]
+    assert head_revision() == "0004"
+    assert [item.revision for item in script.walk_revisions()] == ["0004", "0003", "0002", "0001"]
 
 
 def test_offline_sql_creates_the_base_schema_and_relaxes_legacy_columns() -> None:
@@ -284,3 +284,19 @@
     @contextmanager
     def begin(self) -> Iterator[_PostgresConnection]:
         yield self._connection
+
+
+def test_0004_creates_the_seat_vote_tables() -> None:
+    sql = _offline("0003:0004")
+    assert "CREATE TABLE IF NOT EXISTS analise.relatorio_cadeiras (" in sql
+    assert "CREATE TABLE IF NOT EXISTS analise.relatorio_cadeiras_voto (" in sql
+    assert "PRIMARY KEY (ano, turno, cargo, uf, tipo_voto, numero)" in sql
+    assert "UPDATE alembic_version SET version_num='0004'" in sql
+    assert "DROP " not in sql
+
+
+def test_0004_downgrade_drops_only_the_seat_tables() -> None:
+    sql = _offline_downgrade("0004:0003")
+    assert "DROP TABLE IF EXISTS analise.relatorio_cadeiras_voto" in sql
+    assert "DROP TABLE IF EXISTS analise.relatorio_cadeiras" in sql
+    assert "relatorio_poder" not in sql
```

- [ ] **Step 2:** `uv run pytest tests/adapters/test_orm_migrate.py -q` → 3 falhas: `head_revision() == "0003"` e as duas de `0004` (o `alembic` não acha a revisão `0004`).

- [ ] **Step 3: Criar a migração:**

```python
"""Votes per candidate number for the seat estimate: analise.relatorio_cadeiras(_voto).

Revision ID: 0004
Revises: 0003
"""

from typing import Final

from alembic import op

revision: Final = "0004"
down_revision: Final[str | None] = "0003"
branch_labels: Final[str | None] = None
depends_on: Final[str | None] = None

_DDL: Final = (
    """
CREATE TABLE IF NOT EXISTS analise.relatorio_cadeiras (
    ano integer NOT NULL,
    turno integer NOT NULL,
    cargo text NOT NULL,
    gerado_em timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (ano, turno, cargo)
)
""",
    """
CREATE TABLE IF NOT EXISTS analise.relatorio_cadeiras_voto (
    ano integer NOT NULL,
    turno integer NOT NULL,
    cargo text NOT NULL,
    uf text NOT NULL,
    tipo_voto text NOT NULL CHECK (tipo_voto IN ('nominal', 'legenda')),
    numero integer NOT NULL CHECK (numero >= 0),
    votos integer NOT NULL CHECK (votos >= 0),
    PRIMARY KEY (ano, turno, cargo, uf, tipo_voto, numero),
    FOREIGN KEY (ano, turno, cargo)
        REFERENCES analise.relatorio_cadeiras (ano, turno, cargo) ON DELETE CASCADE
)
""",
)


def upgrade() -> None:
    for statement in _DDL:
        op.execute(statement.strip())


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS analise.relatorio_cadeiras_voto")
    op.execute("DROP TABLE IF EXISTS analise.relatorio_cadeiras")
```

- [ ] **Step 4: Acrescentar os modelos** (diff exato; os imports `DateTime`, `ForeignKeyConstraint`, `Integer` e `Text` já existem):

```diff
--- a/src/eleicoes/adapters/orm/models.py
+++ b/src/eleicoes/adapters/orm/models.py
@@ -113,3 +113,36 @@
     comparecimento: Mapped[int] = mapped_column(Integer, nullable=False)
     votos_nominais: Mapped[int] = mapped_column(Integer, nullable=False)
     votos_legenda: Mapped[int] = mapped_column(Integer, nullable=False)
+
+
+class SeatReportHeader(Base):
+    __tablename__ = "relatorio_cadeiras"
+    __table_args__ = {"schema": "analise"}
+
+    ano: Mapped[int] = mapped_column(Integer, primary_key=True)
+    turno: Mapped[int] = mapped_column(Integer, primary_key=True)
+    cargo: Mapped[str] = mapped_column(Text, primary_key=True)
+    gerado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
+
+
+class SeatReportVote(Base):
+    __tablename__ = "relatorio_cadeiras_voto"
+    __table_args__ = (
+        ForeignKeyConstraint(
+            ["ano", "turno", "cargo"],
+            [
+                "analise.relatorio_cadeiras.ano",
+                "analise.relatorio_cadeiras.turno",
+                "analise.relatorio_cadeiras.cargo",
+            ],
+        ),
+        {"schema": "analise"},
+    )
+
+    ano: Mapped[int] = mapped_column(Integer, primary_key=True)
+    turno: Mapped[int] = mapped_column(Integer, primary_key=True)
+    cargo: Mapped[str] = mapped_column(Text, primary_key=True)
+    uf: Mapped[str] = mapped_column(Text, primary_key=True)
+    tipo_voto: Mapped[str] = mapped_column(Text, primary_key=True)
+    numero: Mapped[int] = mapped_column(Integer, primary_key=True)
+    votos: Mapped[int] = mapped_column(Integer, nullable=False)
```

- [ ] **Step 5:** `uv run pytest tests/adapters/test_orm_migrate.py -q` → todos passam. Inclui `test_autogenerate_ignores_unmapped_tables_and_columns`, que confirma que modelo e migração batem.
- [ ] **Step 6:** `uv run alembic upgrade 0003:0004 --sql | grep -c "CREATE TABLE"` → `2`. Só gera SQL; não toca no banco.

**If Task Fails:** se o autogenerate acusar diferença, compare os nomes de coluna do modelo com o DDL. Os `CHECK` existem só no DDL e o autogenerate os ignora.

---

### Task 8: Portas e store dos votos

**Files:**
- Create: `src/eleicoes/ports/relatorio_cadeiras.py`
- Create: `src/eleicoes/adapters/postgres_relatorio_cadeiras.py`
- Create: `src/eleicoes/adapters/postgres_relatorio_cadeiras_async.py`
- Test: `tests/adapters/test_postgres_relatorio_cadeiras.py`

**Prerequisites:** Task 7.

**Interfaces:**
- Produces: `StoredSeatVotes(cargo, votos, gerado_em)`, `CandidateVoteSource`, `SeatVoteStore` (`load`, `generated_at`, `save`, `close`), `AsyncSeatVoteStore` (`load`), `PostgresSeatVoteStore(sessions, schema=None)`, `read_seat_votes`, `write_seat_votes`, `seat_header`, `AsyncPostgresSeatVoteStore(session)`.

- [ ] **Step 1: Teste:**

```python
"""Seat votes through the ORM: SQLite for the round trip, a scripted session for Postgres."""

import asyncio
from datetime import UTC, datetime

import psycopg
import pytest
from sqlalchemy.orm import Session
from tests.adapters.orm_fakes import ScriptedSession, SyncSessionBridge, memory_sessions

import eleicoes.adapters.postgres_relatorio_cadeiras as seat_store
from eleicoes.adapters.postgres_relatorio_cadeiras import PostgresSeatVoteStore
from eleicoes.adapters.postgres_relatorio_cadeiras_async import AsyncPostgresSeatVoteStore
from eleicoes.domain.errors import ElectionError
from eleicoes.domain.simulacao_cadeiras import VotoApurado

_FEDERAL = (
    VotoApurado("deputadoFederal", "AC", "nominal", 1301, 250),
    VotoApurado("deputadoFederal", "AC", "legenda", 13, 10),
)
_GOVERNOR = (VotoApurado("governador", "AC", "nominal", 13, 600),)


@pytest.fixture(autouse=True)
def _schema_checks(monkeypatch: pytest.MonkeyPatch) -> list[object]:
    seen: list[object] = []
    monkeypatch.setattr(seat_store, "require_current_schema", seen.append)
    return seen


def test_save_load_and_header_round_trip() -> None:
    store = PostgresSeatVoteStore(memory_sessions())
    assert store.generated_at(2026, 1, "deputadoFederal") is None
    assert store.load(2026, 1) == ()
    first = store.save(2026, 1, "deputadoFederal", _FEDERAL)
    store.save(2026, 1, "governador", _GOVERNOR)
    assert first.tzinfo is not None
    assert store.generated_at(2026, 1, "deputadoFederal") == first
    loaded = store.load(2026, 1)
    assert [item.cargo for item in loaded] == ["deputadoFederal", "governador"]
    assert set(loaded[0].votos) == set(_FEDERAL)
    assert loaded[1].votos == _GOVERNOR
    store.close()


def test_save_replaces_the_previous_votes_of_the_cargo() -> None:
    store = PostgresSeatVoteStore(memory_sessions())
    store.save(2026, 1, "deputadoFederal", _FEDERAL)
    store.save(2026, 1, "deputadoFederal", _FEDERAL[:1])
    assert store.load(2026, 1)[0].votos == _FEDERAL[:1]


def test_empty_cargo_keeps_its_header() -> None:
    store = PostgresSeatVoteStore(memory_sessions())
    store.save(2026, 1, "deputadoDistrital", ())
    loaded = store.load(2026, 1)
    assert [(item.cargo, item.votos) for item in loaded] == [("deputadoDistrital", ())]


def test_vote_of_another_cargo_is_refused() -> None:
    store = PostgresSeatVoteStore(memory_sessions())
    with pytest.raises(ElectionError):
        store.save(2026, 1, "governador", _FEDERAL)


def test_postgres_checks_the_revision_once_without_ddl(_schema_checks: list[object]) -> None:
    session = ScriptedSession()
    store = PostgresSeatVoteStore(lambda: session)
    store.ensure_model()
    store.ensure_model()
    assert _schema_checks == [session]
    assert session.executed == []


def test_driver_errors_become_election_errors() -> None:
    def broken() -> Session:
        raise psycopg.OperationalError("down")

    with pytest.raises(ElectionError, match="seat vote store failed"):
        PostgresSeatVoteStore(broken).load(2026, 1)


def test_async_store_reads_what_the_sync_store_wrote() -> None:
    sessions = memory_sessions()
    PostgresSeatVoteStore(sessions).save(2026, 1, "governador", _GOVERNOR)
    bridge = SyncSessionBridge(sessions())
    loaded = asyncio.run(AsyncPostgresSeatVoteStore(bridge).load(2026, 1))  # type: ignore[arg-type]
    assert loaded[0].votos == _GOVERNOR
    assert loaded[0].gerado_em.tzinfo is not None
    assert loaded[0].gerado_em <= datetime.now(UTC)
```

- [ ] **Step 2:** `uv run pytest tests/adapters/test_postgres_relatorio_cadeiras.py -q` → `ModuleNotFoundError`.

- [ ] **Step 3: Porta** `src/eleicoes/ports/relatorio_cadeiras.py`:

```python
"""Ports for the stored votes per candidate number behind the seat estimate."""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from eleicoes.domain.errors import InvalidStoredReportError
from eleicoes.domain.simulacao_cadeiras import VotoApurado


@dataclass(frozen=True, slots=True)
class StoredSeatVotes:
    cargo: str
    votos: tuple[VotoApurado, ...]
    gerado_em: datetime

    def __post_init__(self) -> None:
        if self.gerado_em.tzinfo is None:
            raise InvalidStoredReportError("gerado_em")
        if any(voto.cargo != self.cargo for voto in self.votos):
            raise InvalidStoredReportError("cargo")


class CandidateVoteSource(Protocol):
    def candidate_totals(self, ano: int, turno: int, cargo: str) -> tuple[VotoApurado, ...]: ...

    def close(self) -> None: ...


class SeatVoteStore(Protocol):
    def load(self, ano: int, turno: int) -> tuple[StoredSeatVotes, ...]: ...

    def generated_at(self, ano: int, turno: int, cargo: str) -> datetime | None: ...

    def save(
        self, ano: int, turno: int, cargo: str, votos: tuple[VotoApurado, ...]
    ) -> datetime: ...

    def close(self) -> None: ...


class AsyncSeatVoteStore(Protocol):
    async def load(self, ano: int, turno: int) -> tuple[StoredSeatVotes, ...]: ...
```

- [ ] **Step 4: Store síncrono** `src/eleicoes/adapters/postgres_relatorio_cadeiras.py`:

```python
"""Stores the votes per candidate number behind the seat estimate. Seats are not stored."""

from collections.abc import Callable
from datetime import datetime
from typing import Final, TypeVar

import psycopg
from sqlalchemy import delete, insert, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from eleicoes.adapters.orm.migrate import SchemaCheck, require_current_schema
from eleicoes.adapters.orm.models import Base, SeatReportHeader, SeatReportVote
from eleicoes.adapters.orm.schema import (
    dialect_name,
    is_postgresql,
    require_clock,
    server_clock,
)
from eleicoes.adapters.orm.sessions import SyncSessionFactory
from eleicoes.domain.errors import ElectionError
from eleicoes.domain.simulacao_cadeiras import VotoApurado
from eleicoes.ports.relatorio_cadeiras import StoredSeatVotes

_MISSING: Final = "seat votes were not stored"
_BROKEN: Final = "seat vote row is incomplete"
_FAILED: Final = "seat vote store failed"
_SQLITE: Final = "sqlite"
_INDEX: Final = ["ano", "turno", "cargo"]
_T = TypeVar("_T")


class PostgresSeatVoteStore:
    def __init__(self, sessions: SyncSessionFactory, schema: SchemaCheck | None = None) -> None:
        self._sessions = sessions
        self._schema = schema if schema is not None else require_current_schema
        self._schema_checked = False
        self._session: Session | None = None

    def ensure_model(self) -> None:
        session = self._open()
        if not is_postgresql(session):
            Base.metadata.create_all(session.get_bind())
            return
        if self._schema_checked:
            return
        with session.begin():
            self._schema(session)
        self._schema_checked = True

    def load(self, ano: int, turno: int) -> tuple[StoredSeatVotes, ...]:
        def work() -> tuple[StoredSeatVotes, ...]:
            self.ensure_model()
            with self._open().begin():
                return read_seat_votes(self._open(), ano, turno)

        return self._guard(work)

    def generated_at(self, ano: int, turno: int, cargo: str) -> datetime | None:
        def work() -> datetime | None:
            self.ensure_model()
            with self._open().begin():
                return seat_header(self._open(), ano, turno, cargo)

        return self._guard(work)

    def save(self, ano: int, turno: int, cargo: str, votos: tuple[VotoApurado, ...]) -> datetime:
        def work() -> datetime:
            self.ensure_model()
            with self._open().begin():
                return write_seat_votes(self._open(), ano, turno, cargo, votos)

        return self._guard(work)

    def close(self) -> None:
        session = self._session
        self._session = None
        if session is not None:
            session.close()

    def _guard(self, work: Callable[[], _T]) -> _T:
        try:
            return work()
        except ElectionError:
            raise
        except (SQLAlchemyError, psycopg.Error) as exc:
            raise ElectionError(_FAILED) from exc

    def _open(self) -> Session:
        if self._session is None:
            self._session = self._sessions()
        return self._session


def seat_header(session: Session, ano: int, turno: int, cargo: str) -> datetime | None:
    found = session.execute(
        select(SeatReportHeader.gerado_em).where(
            SeatReportHeader.ano == ano,
            SeatReportHeader.turno == turno,
            SeatReportHeader.cargo == cargo,
        )
    ).scalar_one_or_none()
    if found is None:
        return None
    return require_clock(session, found, _BROKEN)


def read_seat_votes(session: Session, ano: int, turno: int) -> tuple[StoredSeatVotes, ...]:
    headers = (
        session.execute(
            select(SeatReportHeader)
            .where(SeatReportHeader.ano == ano, SeatReportHeader.turno == turno)
            .order_by(SeatReportHeader.cargo)
        )
        .scalars()
        .all()
    )
    lines = (
        session.execute(
            select(SeatReportVote).where(SeatReportVote.ano == ano, SeatReportVote.turno == turno)
        )
        .scalars()
        .all()
    )
    by_cargo: dict[str, list[VotoApurado]] = {header.cargo: [] for header in headers}
    for line in lines:
        if line.cargo not in by_cargo:
            raise ElectionError(_BROKEN)
        by_cargo[line.cargo].append(_vote(line))
    return tuple(
        StoredSeatVotes(
            header.cargo,
            tuple(by_cargo[header.cargo]),
            require_clock(session, header.gerado_em, _BROKEN),
        )
        for header in headers
    )


def write_seat_votes(
    session: Session,
    ano: int,
    turno: int,
    cargo: str,
    votos: tuple[VotoApurado, ...],
) -> datetime:
    if any(voto.cargo != cargo for voto in votos):
        raise ElectionError(_BROKEN)
    moment = _touch(session, ano, turno, cargo)
    session.execute(
        delete(SeatReportVote).where(
            SeatReportVote.ano == ano,
            SeatReportVote.turno == turno,
            SeatReportVote.cargo == cargo,
        )
    )
    if votos:
        session.execute(
            insert(SeatReportVote),
            [
                {
                    "ano": ano,
                    "turno": turno,
                    "cargo": cargo,
                    "uf": voto.uf,
                    "tipo_voto": voto.tipo_voto,
                    "numero": voto.numero,
                    "votos": voto.votos,
                }
                for voto in votos
            ],
        )
    return moment


def _touch(session: Session, ano: int, turno: int, cargo: str) -> datetime:
    clock = server_clock(session)
    values = {"ano": ano, "turno": turno, "cargo": cargo, "gerado_em": clock}
    if dialect_name(session) == _SQLITE:
        statement = (
            sqlite_insert(SeatReportHeader)
            .values(**values)
            .on_conflict_do_update(index_elements=_INDEX, set_={"gerado_em": clock})
            .returning(SeatReportHeader.gerado_em)
        )
    else:
        statement = (
            pg_insert(SeatReportHeader)
            .values(**values)
            .on_conflict_do_update(index_elements=_INDEX, set_={"gerado_em": clock})
            .returning(SeatReportHeader.gerado_em)
        )
    found: object = session.execute(statement).scalar_one()
    return require_clock(session, found, _MISSING)


def _vote(line: SeatReportVote) -> VotoApurado:
    values = (line.cargo, line.uf, line.tipo_voto, line.numero, line.votos)
    cargo, uf, tipo, numero, votos = values
    if not isinstance(cargo, str) or not isinstance(uf, str) or not isinstance(tipo, str):
        raise ElectionError(_BROKEN)
    if not isinstance(numero, int) or not isinstance(votos, int):
        raise ElectionError(_BROKEN)
    return VotoApurado(cargo, uf, tipo, numero, votos)
```

- [ ] **Step 5: Store assíncrono** `src/eleicoes/adapters/postgres_relatorio_cadeiras_async.py`:

```python
"""Async read of the stored seat votes. Same ORM statements as the sync store, no DDL."""

import psycopg
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from eleicoes.adapters.postgres_relatorio_cadeiras import read_seat_votes
from eleicoes.domain.errors import ElectionError
from eleicoes.ports.relatorio_cadeiras import StoredSeatVotes

_FAILED = "seat vote store failed"


class AsyncPostgresSeatVoteStore:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def load(self, ano: int, turno: int) -> tuple[StoredSeatVotes, ...]:
        def work(sync: Session) -> tuple[StoredSeatVotes, ...]:
            return read_seat_votes(sync, ano, turno)

        try:
            async with self._session.begin():
                return await self._session.run_sync(work)
        except ElectionError:
            raise
        except (SQLAlchemyError, psycopg.Error) as exc:
            raise ElectionError(_FAILED) from exc
```

- [ ] **Step 6:** `uv run pytest tests/adapters/test_postgres_relatorio_cadeiras.py -q` → `7 passed`; `uv run mypy` → `Success`.

**If Task Fails:** o SQLite não tem `timestamptz`, e `require_clock` põe UTC. Se `gerado_em.tzinfo` vier `None`, a leitura não passou por `require_clock`.

---

### Task 9: Varredura dos boletins por cargo

**Files:**
- Create: `src/eleicoes/adapters/postgres_votos_candidato.py`
- Test: `tests/adapters/test_postgres_votos_candidato.py`

**Prerequisites:** Task 8. A porta `CandidateVoteSource` fica separada de `BoletimReader` para não obrigar os fakes existentes a ganhar um método.

- [ ] **Step 1: Teste:**

```python
"""Candidate vote scan against a fake cursor. No database."""

from collections.abc import Sequence

import pytest

from eleicoes.adapters.postgres_votos_candidato import PostgresCandidateVotes
from eleicoes.domain.errors import InvalidBoletimConsultaError, InvalidCargoError
from eleicoes.domain.simulacao_cadeiras import VotoApurado


class _Cursor:
    def __init__(self, rows: list[tuple[object, ...]], log: list[tuple[str, tuple[object, ...]]]):
        self._rows = rows
        self._log = log

    def execute(self, query: str, params: Sequence[object] | None = None) -> None:
        self._log.append((query, tuple(params or ())))

    def fetchall(self) -> list[tuple[object, ...]]:
        return self._rows

    def __enter__(self) -> "_Cursor":
        return self

    def __exit__(self, *_args: object) -> None:
        return None


class _Connection:
    def __init__(self, rows: list[tuple[object, ...]]) -> None:
        self.statements: list[tuple[str, tuple[object, ...]]] = []
        self.rows = rows
        self.closed = 0

    def cursor(self) -> _Cursor:
        return _Cursor(self.rows, self.statements)

    def transaction(self) -> "_Connection":
        return self

    def close(self) -> None:
        self.closed += 1

    def __enter__(self) -> "_Connection":
        return self

    def __exit__(self, *_args: object) -> None:
        return None


def test_one_grouped_scan_per_cargo_with_bound_parameters() -> None:
    connection = _Connection([("AC", "nominal", 1301, 250), ("AC", "legenda", 13, 10)])
    source = PostgresCandidateVotes(lambda: connection)  # type: ignore[arg-type,return-value]
    found = source.candidate_totals(2026, 1, "deputadoFederal")
    assert found == (
        VotoApurado("deputadoFederal", "AC", "nominal", 1301, 250),
        VotoApurado("deputadoFederal", "AC", "legenda", 13, 10),
    )
    sql, params = connection.statements[0]
    assert "SUM(quantidade)" in sql
    assert "GROUP BY uf, tipo_voto, numero" in sql
    assert "tipo_voto IN ('nominal', 'legenda')" in sql
    assert params == (2026, 1, "deputadoFederal")
    source.close()
    source.close()
    assert connection.closed == 1


@pytest.mark.parametrize(
    "row",
    [("AC", "nominal", "1301", 1), ("AC", "nominal", 1301, True), ("AC", "nominal", 1301)],
)
def test_bad_rows_are_rejected(row: tuple[object, ...]) -> None:
    source = PostgresCandidateVotes(lambda: _Connection([row]))  # type: ignore[arg-type,return-value]
    with pytest.raises(InvalidBoletimConsultaError):
        source.candidate_totals(2026, 1, "deputadoFederal")


def test_blank_cargo_is_refused_before_the_query() -> None:
    connection = _Connection([])
    with pytest.raises(InvalidCargoError):
        PostgresCandidateVotes(lambda: connection).candidate_totals(2026, 1, " ")  # type: ignore[arg-type,return-value]
    assert connection.statements == []
```

- [ ] **Step 2:** falha com `ModuleNotFoundError`.

- [ ] **Step 3: Criar o adaptador:**

```python
"""Sums raw.boletim per UF and candidate number, one sequential scan per cargo."""

from collections.abc import Sequence
from typing import Final

from eleicoes.adapters.postgres_sink import ConnectionFactory, SqlConnection
from eleicoes.domain.boletim_consulta import require_cargo
from eleicoes.domain.errors import InvalidBoletimConsultaError
from eleicoes.domain.simulacao_cadeiras import VotoApurado
from eleicoes.domain.values import ElectionYear, Turno

_WIDTH: Final = 4
_TOTALS: Final = """
SELECT uf, tipo_voto, numero, SUM(quantidade)::bigint AS votos
FROM raw.boletim
WHERE ano = %s
  AND turno = %s
  AND cargo = %s
  AND tipo_voto IN ('nominal', 'legenda')
  AND numero IS NOT NULL
GROUP BY uf, tipo_voto, numero
ORDER BY uf, tipo_voto, numero
"""


class PostgresCandidateVotes:
    def __init__(self, connect: ConnectionFactory) -> None:
        self._connect = connect
        self._connection: SqlConnection | None = None

    def candidate_totals(self, ano: int, turno: int, cargo: str) -> tuple[VotoApurado, ...]:
        params = (ElectionYear(ano).value, Turno(turno).value, require_cargo(cargo))
        connection = self._open()
        with connection.transaction(), connection.cursor() as cursor:
            cursor.execute(_TOTALS, params)
            rows = tuple(tuple(row) for row in cursor.fetchall())
        return tuple(_vote(cargo, row) for row in rows)

    def close(self) -> None:
        connection = self._connection
        self._connection = None
        if connection is not None:
            connection.close()

    def _open(self) -> SqlConnection:
        if self._connection is None:
            self._connection = self._connect()
        return self._connection


def _vote(cargo: str, row: Sequence[object]) -> VotoApurado:
    if len(row) != _WIDTH:
        raise InvalidBoletimConsultaError(row)
    uf, tipo, numero, votos = row
    if not isinstance(uf, str) or not isinstance(tipo, str):
        raise InvalidBoletimConsultaError(row)
    return VotoApurado(cargo, uf, tipo, _integer(numero), _integer(votos))


def _integer(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise InvalidBoletimConsultaError(value)
    return value
```

- [ ] **Step 4:** `uv run pytest tests/adapters/test_postgres_votos_candidato.py -q` → `5 passed`.

---

### Task 10: Gravação por CLI, wiring e script

**Files:**
- Create: `src/eleicoes/use_cases/gravar_cadeiras.py`
- Create: `src/eleicoes/composition/cadeiras.py`
- Create: `scripts/relatorio_cadeiras.py`
- Test: `tests/use_cases/test_gravar_cadeiras.py`, `tests/composition/test_cadeiras_wiring.py`

**Prerequisites:** Tasks 8 e 9.

**Interfaces:**
- Produces: `RecordSeatVotes(source, store, announce=None).execute(ano, turno, cargos=CARGOS_GRAVADOS, *, atualizar=False) -> tuple[RecordedCargo, ...]`, `summary(simulacao)`, `main(argv=None, *, source=None, store=None) -> int`, `build_candidate_votes(env=None)`, `build_seat_vote_store(env=None)`.

- [ ] **Step 1: Testes:**

```python
"""Recording the seat votes: one scan per cargo, reuse unless --atualizar."""

from datetime import UTC, datetime

import pytest

from eleicoes.domain.cadeiras import CARGOS_GRAVADOS
from eleicoes.domain.errors import ElectionError, SchemaOutdatedError
from eleicoes.domain.simulacao_cadeiras import VotoApurado
from eleicoes.ports.relatorio_cadeiras import StoredSeatVotes
from eleicoes.use_cases.gravar_cadeiras import RecordSeatVotes, main

_MOMENT = datetime(2026, 10, 22, 12, 0, tzinfo=UTC)


class _Source:
    def __init__(self) -> None:
        self.calls: list[str] = []
        self.closed = False

    def candidate_totals(self, _ano: int, _turno: int, cargo: str) -> tuple[VotoApurado, ...]:
        self.calls.append(cargo)
        numero = {"governador": 13, "senador": 131}.get(cargo, 1301)
        return (VotoApurado(cargo, "AC", "nominal", numero, 10),)

    def close(self) -> None:
        self.closed = True


class _Store:
    def __init__(self, saved: tuple[str, ...] = ()) -> None:
        self.saved: dict[str, tuple[VotoApurado, ...]] = {cargo: () for cargo in saved}
        self.closed = False

    def load(self, _ano: int, _turno: int) -> tuple[StoredSeatVotes, ...]:
        return tuple(StoredSeatVotes(c, v, _MOMENT) for c, v in self.saved.items())

    def generated_at(self, _ano: int, _turno: int, cargo: str) -> datetime | None:
        return _MOMENT if cargo in self.saved else None

    def save(self, _ano: int, _turno: int, cargo: str, votos: tuple[VotoApurado, ...]) -> datetime:
        self.saved[cargo] = votos
        return _MOMENT

    def close(self) -> None:
        self.closed = True


def test_records_every_cargo_once_and_reuses_what_is_stored() -> None:
    source = _Source()
    store = _Store(saved=("governador",))
    said: list[str] = []
    recorded = RecordSeatVotes(source, store, said.append).execute(2026, 1)
    assert [item.cargo for item in recorded] == list(CARGOS_GRAVADOS)
    assert recorded[0].reaproveitado is True
    assert source.calls == list(CARGOS_GRAVADOS[1:])
    assert said[0] == "Somando os votos de senador nos boletins..."


def test_atualizar_scans_again() -> None:
    source = _Source()
    RecordSeatVotes(source, _Store(saved=CARGOS_GRAVADOS)).execute(
        2026, 1, ("deputadoFederal",), atualizar=True
    )
    assert source.calls == ["deputadoFederal"]


def test_main_prints_each_cargo_and_the_summary(capsys: pytest.CaptureFixture[str]) -> None:
    source = _Source()
    store = _Store()
    assert main([], source=source, store=store) == 0
    out = capsys.readouterr().out
    assert "deputadoFederal: 1 números gravados em" in out
    assert "Câmara: 8 de 513 vagas." in out
    assert "Governadores eleitos no 1º turno: 1 de 1 UFs." in out
    assert source.closed and store.closed


def test_main_with_one_cargo_skips_the_summary(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--cargo", "senador"], source=_Source(), store=_Store()) == 0
    assert "Câmara:" not in capsys.readouterr().out


def test_main_turns_failures_into_portuguese(capsys: pytest.CaptureFixture[str]) -> None:
    class _Broken(_Store):
        def generated_at(self, _ano: int, _turno: int, _cargo: str) -> datetime | None:
            raise ElectionError("seat vote store failed")

    class _Old(_Store):
        def generated_at(self, _ano: int, _turno: int, _cargo: str) -> datetime | None:
            raise SchemaOutdatedError(("0003",), "0004")

    assert main([], source=_Source(), store=_Broken()) == 1
    assert "Não foi possível gravar os votos por candidato." in capsys.readouterr().err
    assert main([], source=_Source(), store=_Old()) == 1
    assert "make migrate" in capsys.readouterr().err
```

```python
"""The seat stores use the same Postgres settings as the other reports, without a socket."""

from collections.abc import Mapping

import pytest

from eleicoes.composition.cadeiras import build_candidate_votes, build_seat_vote_store

_ENV = {
    "POSTGRES_HOST": "127.0.0.1",
    "POSTGRES_PORT": "25432",
    "POSTGRES_USER": "eleicoes",
    "POSTGRES_PASSWORD": "secret",
    "POSTGRES_DB": "eleicoes",
}


def test_builders_bind_the_given_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[dict[str, str]] = []

    def remember(settings: Mapping[str, str]) -> object:
        seen.append(dict(settings))
        return object()

    monkeypatch.setattr("eleicoes.composition.cadeiras.open_sync_session", remember)
    monkeypatch.setattr("eleicoes.composition.cadeiras.connect_postgres", remember)
    store = build_seat_vote_store(_ENV)
    source = build_candidate_votes(_ENV)
    store._open()  # noqa: SLF001
    source._open()  # noqa: SLF001
    assert [item["POSTGRES_PORT"] for item in seen] == ["25432", "25432"]


def test_builders_read_the_process_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for key, value in _ENV.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setattr("eleicoes.composition.cadeiras.load_dotenv", lambda: None)
    assert build_seat_vote_store() is not None
    assert build_candidate_votes() is not None
```

- [ ] **Step 2:** os dois falham com `ModuleNotFoundError`.

- [ ] **Step 3: Caso de uso** `src/eleicoes/use_cases/gravar_cadeiras.py`:

```python
"""Sum the votes per candidate number once per cargo and store them for the seat estimate.

The scan of raw.boletim is the slow part (minutes per cargo). Seats are not stored: the
API recalculates them from these votes, so a federation update needs no new scan.
"""

import argparse
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Final

from eleicoes.domain.cadeiras import CARGOS_GRAVADOS
from eleicoes.domain.errors import (
    SCHEMA_OUTDATED_HINT,
    ElectionError,
    InvalidCargoError,
    SchemaOutdatedError,
)
from eleicoes.domain.federacoes import registro_partidario
from eleicoes.domain.percentual import format_integer
from eleicoes.domain.report import EXIT_FAILURE, EXIT_SUCCESS
from eleicoes.domain.simulacao_cadeiras import SimulacaoCadeiras, simular_cadeiras
from eleicoes.domain.values import ElectionYear, Turno
from eleicoes.ports.relatorio_cadeiras import CandidateVoteSource, SeatVoteStore
from eleicoes.use_cases.failure import failure_line

_FAILURE: Final = "Não foi possível gravar os votos por candidato."
Announce = Callable[[str], None]


@dataclass(frozen=True, slots=True)
class RecordedCargo:
    cargo: str
    linhas: int | None
    gerado_em: datetime
    reaproveitado: bool


class RecordSeatVotes:
    def __init__(
        self,
        source: CandidateVoteSource,
        store: SeatVoteStore,
        announce: Announce | None = None,
    ) -> None:
        self._source = source
        self._store = store
        self._announce = announce or _silent

    def execute(
        self,
        ano: int,
        turno: int,
        cargos: Sequence[str] = CARGOS_GRAVADOS,
        *,
        atualizar: bool = False,
    ) -> tuple[RecordedCargo, ...]:
        year = ElectionYear(ano).value
        turn = Turno(turno).value
        return tuple(self._one(year, turn, _known(cargo), atualizar) for cargo in cargos)

    def _one(self, ano: int, turno: int, cargo: str, atualizar: bool) -> RecordedCargo:
        if not atualizar:
            found = self._store.generated_at(ano, turno, cargo)
            if found is not None:
                return RecordedCargo(cargo, None, found, True)
        self._announce(f"Somando os votos de {cargo} nos boletins...")
        votos = self._source.candidate_totals(ano, turno, cargo)
        moment = self._store.save(ano, turno, cargo, votos)
        return RecordedCargo(cargo, len(votos), moment, False)


def summary(simulacao: SimulacaoCadeiras) -> str:
    governo = simulacao.governo
    eleitos = sum(1 for item in governo.ufs if item.eleito is not None)
    return "\n".join(
        (
            f"Câmara: {_part(simulacao.camara.vagas_simuladas, simulacao.camara.vagas)} vagas.",
            "Assembleias: "
            f"{_part(simulacao.assembleias.vagas_simuladas, simulacao.assembleias.vagas)} vagas.",
            f"Senado: {_part(2 * len(simulacao.senado.ufs), simulacao.senado.vagas)} vagas.",
            f"Governadores eleitos no 1º turno: {eleitos} de {len(governo.ufs)} UFs.",
        )
    )


def main(
    argv: Sequence[str] | None = None,
    *,
    source: CandidateVoteSource | None = None,
    store: SeatVoteStore | None = None,
) -> int:
    args = _parser().parse_args(argv)
    try:
        text = _run(args, source, store)
    except SchemaOutdatedError:
        print(SCHEMA_OUTDATED_HINT, file=sys.stderr)
        return EXIT_FAILURE
    except ElectionError as exc:
        print(failure_line(_FAILURE, exc), file=sys.stderr)
        return EXIT_FAILURE
    print(text)
    return EXIT_SUCCESS


def _run(
    args: argparse.Namespace,
    source: CandidateVoteSource | None,
    store: SeatVoteStore | None,
) -> str:
    opened_source = source if source is not None else _production_source()
    opened_store = store if store is not None else _production_store()
    try:
        cargos = tuple(args.cargo) if args.cargo else CARGOS_GRAVADOS
        recorded = RecordSeatVotes(opened_source, opened_store, _print).execute(
            args.ano, args.turno, cargos, atualizar=bool(args.atualizar)
        )
        stored = opened_store.load(args.ano, args.turno)
    finally:
        opened_source.close()
        opened_store.close()
    lines = [_line(item) for item in recorded]
    if {item.cargo for item in stored} >= set(CARGOS_GRAVADOS):
        votos = tuple(voto for item in stored for voto in item.votos)
        registro = registro_partidario(args.ano)
        lines.append(summary(simular_cadeiras(args.ano, args.turno, votos, registro)))
    return "\n".join(lines)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Grava os votos por candidato que a simulação de cadeiras usa.",
    )
    parser.add_argument("--ano", type=int, default=2026)
    parser.add_argument("--turno", type=int, default=1)
    parser.add_argument(
        "--cargo",
        action="append",
        choices=CARGOS_GRAVADOS,
        help="Repita para mais de um cargo. Sem a opção, grava os cinco.",
    )
    parser.add_argument(
        "--atualizar",
        action="store_true",
        help="Soma os boletins de novo e substitui os votos gravados.",
    )
    return parser


def _line(item: RecordedCargo) -> str:
    stamp = item.gerado_em.astimezone().strftime("%Y-%m-%d %H:%M")
    if item.reaproveitado:
        return f"{item.cargo}: já gravado em {stamp}. Use --atualizar para somar de novo."
    linhas = format_integer(item.linhas or 0)
    return f"{item.cargo}: {linhas} números gravados em {stamp}."


def _part(simuladas: int, total: int) -> str:
    return f"{format_integer(simuladas)} de {format_integer(total)}"


def _known(cargo: str) -> str:
    if cargo not in CARGOS_GRAVADOS:
        raise InvalidCargoError(cargo)
    return cargo


def _print(message: str) -> None:
    print(message, flush=True)


def _silent(_message: str) -> None:
    return None


def _production_source() -> CandidateVoteSource:
    from eleicoes.composition.cadeiras import build_candidate_votes

    return build_candidate_votes()


def _production_store() -> SeatVoteStore:
    from eleicoes.composition.cadeiras import build_seat_vote_store

    return build_seat_vote_store()
```

- [ ] **Step 4: Wiring** `src/eleicoes/composition/cadeiras.py`:

```python
"""Wires the candidate-vote scan and the stored seat votes."""

import os
from collections.abc import Mapping

from dotenv import load_dotenv

from eleicoes.adapters.orm.sessions import open_sync_session
from eleicoes.adapters.postgres_relatorio_cadeiras import PostgresSeatVoteStore
from eleicoes.adapters.postgres_sink import connect_postgres
from eleicoes.adapters.postgres_votos_candidato import PostgresCandidateVotes
from eleicoes.composition.correspondencia import _host_settings


def build_candidate_votes(env: Mapping[str, str] | None = None) -> PostgresCandidateVotes:
    settings = _host_settings(_settings(env))
    return PostgresCandidateVotes(lambda: connect_postgres(settings))


def build_seat_vote_store(env: Mapping[str, str] | None = None) -> PostgresSeatVoteStore:
    settings = _host_settings(_settings(env))
    return PostgresSeatVoteStore(lambda: open_sync_session(settings))


def _settings(env: Mapping[str, str] | None) -> Mapping[str, str]:
    if env is not None:
        return env
    load_dotenv()
    return os.environ
```

- [ ] **Step 5: Script** `scripts/relatorio_cadeiras.py`:

```python
"""Grava os votos por candidato que a simulação de cadeiras usa.

Uso, na raiz do projeto:

    uv run python scripts/relatorio_cadeiras.py

Soma os boletins uma vez por cargo (governador, senador, deputadoFederal,
deputadoEstadual e deputadoDistrital) e grava em analise.relatorio_cadeiras_voto.
Um cargo já gravado não é somado de novo. Para refazer:

    uv run python scripts/relatorio_cadeiras.py --atualizar
    uv run python scripts/relatorio_cadeiras.py --cargo deputadoFederal --atualizar

As cadeiras não são gravadas: a API as calcula a partir desses votos.
"""

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from eleicoes.use_cases.gravar_cadeiras import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 6:** `uv run pytest tests/use_cases/test_gravar_cadeiras.py tests/composition/test_cadeiras_wiring.py -q` → `7 passed`. Depois `uv run python scripts/relatorio_cadeiras.py --help` → mostra `--ano`, `--turno`, `--cargo {governador,senador,deputadoFederal,deputadoEstadual,deputadoDistrital}` e `--atualizar`, sem tocar no banco.

---

### Task 11: Code Review (persistência e CLI)

1. **REQUIRED SUB-SKILL:** Use jarvis:codereview — dispatch all reviewers in parallel.
2. **Foco:** a SQL é uma varredura por cargo, com parâmetros ligados e sem interpolação. A gravação substitui as linhas do cargo numa transação só. O store respeita `require_current_schema` e não roda DDL no Postgres.
3. **Proceed only when:** zero Critical/High/Medium issues remain.

---

### Task 12: Leitura na API

**Files:**
- Create: `src/eleicoes/use_cases/simular_cadeiras.py`
- Create: `src/eleicoes/adapters/http/schemas_cadeiras.py`
- Modify: `src/eleicoes/adapters/http/bundle.py`, `dependencies.py`, `errors.py`, `relatorios.py`
- Modify: `tests/adapters/test_read_api.py` (rota nova no conjunto esperado do OpenAPI)
- Test: `tests/use_cases/test_simular_cadeiras.py`, `tests/adapters/test_read_api_cadeiras.py`

**Prerequisites:** Tasks 5 e 8.

**Interfaces:**
- Produces: `SimulacaoGravada(simulacao, gerado_em)`, `stored_simulation(store, ano, turno, registro=None)`, `CadeirasJson.from_domain(gravada)`, `get_seat_store`, `ReadPorts.seat_store` (default `None`) e a rota `GET /relatorios/dados/cadeiras`.

- [ ] **Step 1: Testes:**

```python
"""The API use case: stored votes in, simulation out, 409 when a cargo is missing."""

import asyncio
from datetime import UTC, datetime

import pytest

from eleicoes.domain.cadeiras import CARGOS_GRAVADOS
from eleicoes.domain.errors import MissingSeatReportError, UnknownPartyRegistryError
from eleicoes.domain.simulacao_cadeiras import VotoApurado
from eleicoes.ports.relatorio_cadeiras import StoredSeatVotes
from eleicoes.use_cases.simular_cadeiras import stored_simulation

_OLD = datetime(2026, 10, 20, tzinfo=UTC)
_NEW = datetime(2026, 10, 22, tzinfo=UTC)


class _Store:
    def __init__(self, stored: tuple[StoredSeatVotes, ...]) -> None:
        self.stored = stored

    async def load(self, _ano: int, _turno: int) -> tuple[StoredSeatVotes, ...]:
        return self.stored


def _all() -> tuple[StoredSeatVotes, ...]:
    rows = [StoredSeatVotes(cargo, (), _NEW) for cargo in CARGOS_GRAVADOS]
    rows[0] = StoredSeatVotes(
        "governador", (VotoApurado("governador", "SE", "nominal", 13, 9),), _OLD
    )
    return tuple(rows)


def test_simulation_uses_the_oldest_timestamp() -> None:
    found = asyncio.run(stored_simulation(_Store(_all()), 2026, 1))
    assert found.gerado_em == _OLD
    assert found.simulacao.governo.eleitos_por_partido() == {13: 1}


def test_missing_cargos_are_named_with_the_command() -> None:
    with pytest.raises(MissingSeatReportError) as caught:
        asyncio.run(stored_simulation(_Store(_all()[:3]), 2026, 1))
    assert caught.value.cargos == ("deputadoEstadual", "deputadoDistrital")
    assert "scripts/relatorio_cadeiras.py" in str(caught.value)


def test_year_without_registry_fails_before_reading() -> None:
    with pytest.raises(UnknownPartyRegistryError):
        asyncio.run(stored_simulation(_Store(()), 2022, 1))
```

```python
"""GET /relatorios/dados/cadeiras with fake ports."""

import asyncio
from datetime import UTC, datetime

import httpx
from fastapi import FastAPI
from tests.adapters.test_read_api import _ports

from eleicoes.adapters.http.bundle import ReadPorts
from eleicoes.composition.api import create_app
from eleicoes.domain.cadeiras import CARGOS_GRAVADOS
from eleicoes.domain.simulacao_cadeiras import VotoApurado
from eleicoes.ports.relatorio_cadeiras import StoredSeatVotes

_MOMENT = datetime(2026, 10, 22, tzinfo=UTC)
_FEDERAL = (
    VotoApurado("deputadoFederal", "AC", "nominal", 1301, 250),
    VotoApurado("deputadoFederal", "AC", "nominal", 6501, 150),
    VotoApurado("deputadoFederal", "AC", "legenda", 65, 10),
    VotoApurado("deputadoFederal", "AC", "nominal", 2201, 390),
)


class _SeatStore:
    def __init__(self, stored: tuple[StoredSeatVotes, ...]) -> None:
        self.stored = stored

    async def load(self, _ano: int, _turno: int) -> tuple[StoredSeatVotes, ...]:
        return self.stored


def _app(stored: tuple[StoredSeatVotes, ...]) -> FastAPI:
    base = _ports()
    ports = ReadPorts(
        boletim=base.boletim,
        names=base.names,
        power_store=base.power_store,
        cross_store=base.cross_store,
        seat_store=_SeatStore(stored),
    )
    return create_app(ports=ports)


def _get(application: FastAPI, path: str) -> httpx.Response:
    async def fetch() -> httpx.Response:
        transport = httpx.ASGITransport(app=application, raise_app_exceptions=False)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get(path)

    return asyncio.run(fetch())


def _stored() -> tuple[StoredSeatVotes, ...]:
    return tuple(
        StoredSeatVotes(cargo, _FEDERAL if cargo == "deputadoFederal" else (), _MOMENT)
        for cargo in CARGOS_GRAVADOS
    )


def test_cadeiras_json_has_houses_federations_and_the_party_contract() -> None:
    response = _get(_app(_stored()), "/relatorios/dados/cadeiras?ano=2026&turno=1")
    assert response.status_code == 200
    body = response.json()
    assert body["estimativa"] is True
    assert body["gerado_em"] == "2026-10-22T00:00:00+00:00"
    camara = body["casas"][0]
    assert (camara["casa"], camara["vagas"], camara["vagas_simuladas"]) == ("camara", 513, 8)
    assert camara["legendas"] == [
        {"legenda": "fe-brasil", "cadeiras": 2},
        {"legenda": "22", "cadeiras": 1},
    ]
    ac = camara["ufs"][0]
    assert (ac["uf"], ac["quociente_eleitoral"], ac["vagas_sem_candidato"]) == ("AC", 100, 5)
    assert ac["eleitos"][0] == {
        "numero": 2201,
        "partido": 22,
        "legenda": "22",
        "votos": 390,
        "fase": "quociente",
        "empate": False,
    }
    assert body["partidos"][0]["partido"] in {13, 22, 65}
    assert {
        "codigo": "fe-brasil",
        "sigla": "FE BRASIL",
        "nome": "Federação Brasil da Esperança",
        "federacao": True,
        "partidos": [13, 65, 43],
    } in body["legendas"]
    assert body["casas"][1]["ufs_sem_votos"][0] == "AC"
    assert len(body["notas"]) == 6


def test_cadeiras_without_every_cargo_is_409_with_the_command() -> None:
    response = _get(_app(_stored()[:2]), "/relatorios/dados/cadeiras?ano=2026&turno=1")
    assert response.status_code == 409
    assert "uv run python scripts/relatorio_cadeiras.py" in response.json()["detail"]


def test_cadeiras_for_a_year_without_registry_is_422() -> None:
    response = _get(_app(_stored()), "/relatorios/dados/cadeiras?ano=2022&turno=1")
    assert response.status_code == 422
    assert response.json()["detail"] == "Não há partidos e federações cadastrados para 2022."


def test_ports_without_a_seat_store_hide_the_internal_error() -> None:
    response = _get(create_app(ports=_ports()), "/relatorios/dados/cadeiras?ano=2026&turno=1")
    assert response.status_code == 500
    assert response.json()["detail"] == "Não foi possível consultar os dados."
```

```diff
--- a/tests/adapters/test_read_api.py
+++ b/tests/adapters/test_read_api.py
@@ -54,6 +54,7 @@
         "/relatorios/dados/presidente-governador",
         "/relatorios/poder",
         "/relatorios/presidente-governador",
+        "/relatorios/dados/cadeiras",
     }
     assert expected <= set(paths)
     assert paths["/votos/cargos"]["get"]["summary"] == "Totais do cargo"
```

- [ ] **Step 2:** os testes novos falham com `ModuleNotFoundError`; `test_health_and_openapi_advertise_the_read_routes` falha porque a rota não existe.

- [ ] **Step 3: Caso de uso** `src/eleicoes/use_cases/simular_cadeiras.py`:

```python
"""Seat estimate for the API: stored votes in, pure simulation out. Never scans boletins."""

from dataclasses import dataclass
from datetime import datetime

from eleicoes.domain.cadeiras import CARGOS_GRAVADOS
from eleicoes.domain.errors import MissingSeatReportError
from eleicoes.domain.federacoes import RegistroPartidario, registro_partidario
from eleicoes.domain.simulacao_cadeiras import SimulacaoCadeiras, simular_cadeiras
from eleicoes.domain.values import ElectionYear, Turno
from eleicoes.ports.relatorio_cadeiras import AsyncSeatVoteStore


@dataclass(frozen=True, slots=True)
class SimulacaoGravada:
    simulacao: SimulacaoCadeiras
    gerado_em: datetime


async def stored_simulation(
    store: AsyncSeatVoteStore,
    ano: int,
    turno: int,
    registro: RegistroPartidario | None = None,
) -> SimulacaoGravada:
    year = ElectionYear(ano).value
    turn = Turno(turno).value
    rules = registro if registro is not None else registro_partidario(year)
    stored = await store.load(year, turn)
    found = {item.cargo for item in stored}
    missing = tuple(cargo for cargo in CARGOS_GRAVADOS if cargo not in found)
    if missing:
        raise MissingSeatReportError(missing)
    votos = tuple(voto for item in stored for voto in item.votos)
    oldest = min(item.gerado_em for item in stored)
    return SimulacaoGravada(simular_cadeiras(year, turn, votos, rules), oldest)
```

- [ ] **Step 4: Esquemas** `src/eleicoes/adapters/http/schemas_cadeiras.py`:

```python
"""JSON of the seat estimate. The scoreboard (placar) reads `partidos`."""

from fractions import Fraction
from typing import Final, Self

from pydantic import BaseModel

from eleicoes.domain.boletim_consulta import partido_do_numero
from eleicoes.domain.federacoes import RegistroPartidario
from eleicoes.domain.majoritario import ResultadoGoverno, ResultadoSenado, VotoCandidato
from eleicoes.domain.percentual import format_percent
from eleicoes.domain.proporcional import Eleito, ResultadoLista
from eleicoes.domain.simulacao_cadeiras import (
    CASA_CAMARA,
    NOTAS,
    CasaSimulada,
    CasaUf,
    ForcaPartido,
    SimulacaoCadeiras,
)
from eleicoes.use_cases.simular_cadeiras import SimulacaoGravada

_NOMES_CASA: Final = {CASA_CAMARA: "Câmara dos Deputados"}
_NOMINAL: Final = "nominal"
_ASSEMBLEIAS: Final = "Assembleias Legislativas e Câmara Legislativa do DF"


class LegendaJson(BaseModel):
    codigo: str
    sigla: str
    nome: str
    federacao: bool
    partidos: list[int]


class ListaJson(BaseModel):
    legenda: str
    votos: int
    votos_legenda: int
    quociente_partidario: int
    cadeiras_quociente: int
    cadeiras_media: int
    cadeiras_media_livre: int
    cadeiras: int

    @classmethod
    def from_domain(cls, item: ResultadoLista) -> Self:
        return cls(
            legenda=item.legenda,
            votos=item.votos,
            votos_legenda=item.votos_legenda,
            quociente_partidario=item.quociente_partidario,
            cadeiras_quociente=item.cadeiras_quociente,
            cadeiras_media=item.cadeiras_media,
            cadeiras_media_livre=item.cadeiras_media_livre,
            cadeiras=item.cadeiras,
        )


class EleitoJson(BaseModel):
    numero: int
    partido: int
    legenda: str
    votos: int
    fase: str
    empate: bool

    @classmethod
    def from_domain(cls, item: Eleito, partido: int) -> Self:
        return cls(
            numero=item.numero,
            partido=partido,
            legenda=item.legenda,
            votos=item.votos,
            fase=item.fase,
            empate=item.empate,
        )


class CasaUfJson(BaseModel):
    uf: str
    cargo: str
    vagas: int
    votos_validos: int
    quociente_eleitoral: int
    vagas_sem_candidato: int
    listas: list[ListaJson]
    eleitos: list[EleitoJson]

    @classmethod
    def from_domain(cls, item: CasaUf) -> Self:
        resultado = item.resultado
        return cls(
            uf=item.uf,
            cargo=item.cargo,
            vagas=resultado.vagas,
            votos_validos=resultado.votos_validos,
            quociente_eleitoral=resultado.quociente_eleitoral,
            vagas_sem_candidato=resultado.vagas_sem_candidato,
            listas=[ListaJson.from_domain(lista) for lista in resultado.listas if lista.votos],
            eleitos=[
                EleitoJson.from_domain(eleito, partido_do_numero(_NOMINAL, eleito.numero))
                for eleito in resultado.eleitos
            ],
        )


class LegendaCadeirasJson(BaseModel):
    legenda: str
    cadeiras: int


class PartidoCadeirasJson(BaseModel):
    partido: int
    cadeiras: int


class CasaJson(BaseModel):
    casa: str
    nome: str
    vagas: int
    vagas_simuladas: int
    ufs_sem_votos: list[str]
    legendas: list[LegendaCadeirasJson]
    partidos: list[PartidoCadeirasJson]
    ufs: list[CasaUfJson]

    @classmethod
    def from_domain(cls, casa: CasaSimulada) -> Self:
        return cls(
            casa=casa.casa,
            nome=_NOMES_CASA.get(casa.casa, _ASSEMBLEIAS),
            vagas=casa.vagas,
            vagas_simuladas=casa.vagas_simuladas,
            ufs_sem_votos=list(casa.ufs_sem_votos),
            legendas=[
                LegendaCadeirasJson(legenda=chave, cadeiras=valor)
                for chave, valor in _ranked(casa.cadeiras_por_legenda())
            ],
            partidos=_parties(casa.cadeiras_por_partido()),
            ufs=[CasaUfJson.from_domain(item) for item in casa.ufs],
        )


class CandidatoJson(BaseModel):
    numero: int
    partido: int
    votos: int
    fatia: str

    @classmethod
    def from_domain(cls, item: VotoCandidato, validos: int) -> Self:
        share = Fraction(item.votos, validos) if validos else Fraction(0)
        return cls(
            numero=item.numero, partido=item.partido, votos=item.votos, fatia=format_percent(share)
        )


class SenadoUfJson(BaseModel):
    uf: str
    votos_validos: int
    eleitos: list[CandidatoJson]
    empate: bool

    @classmethod
    def from_domain(cls, item: ResultadoSenado) -> Self:
        return cls(
            uf=item.uf,
            votos_validos=item.votos_validos,
            eleitos=[
                CandidatoJson.from_domain(eleito, item.votos_validos) for eleito in item.eleitos
            ],
            empate=item.empate,
        )


class SenadoJson(BaseModel):
    vagas: int
    vagas_simuladas: int
    ufs_sem_votos: list[str]
    partidos: list[PartidoCadeirasJson]
    ufs: list[SenadoUfJson]


class GovernoUfJson(BaseModel):
    uf: str
    situacao: str
    votos_validos: int
    candidatos: list[CandidatoJson]
    empate: bool

    @classmethod
    def from_domain(cls, item: ResultadoGoverno) -> Self:
        return cls(
            uf=item.uf,
            situacao=item.situacao,
            votos_validos=item.votos_validos,
            candidatos=[
                CandidatoJson.from_domain(candidato, item.votos_validos)
                for candidato in item.candidatos
            ],
            empate=item.empate,
        )


class GovernoPartidoJson(BaseModel):
    partido: int
    eleitos: int
    segundo_turno: int


class GovernoJson(BaseModel):
    ufs_sem_votos: list[str]
    partidos: list[GovernoPartidoJson]
    ufs: list[GovernoUfJson]


class ForcaPartidoJson(BaseModel):
    partido: int
    legenda: str
    camara: int
    assembleias: int
    senado: int
    governadores: int
    governadores_segundo_turno: int

    @classmethod
    def from_domain(cls, item: ForcaPartido) -> Self:
        return cls(
            partido=item.partido,
            legenda=item.legenda,
            camara=item.camara,
            assembleias=item.assembleias,
            senado=item.senado,
            governadores=item.governadores,
            governadores_segundo_turno=item.governadores_segundo_turno,
        )


class CadeirasJson(BaseModel):
    ano: int
    turno: int
    gerado_em: str
    estimativa: bool
    legendas: list[LegendaJson]
    casas: list[CasaJson]
    senado: SenadoJson
    governo: GovernoJson
    partidos: list[ForcaPartidoJson]
    descartados: int
    notas: list[str]

    @classmethod
    def from_domain(cls, gravada: SimulacaoGravada) -> Self:
        simulacao = gravada.simulacao
        return cls(
            ano=simulacao.ano,
            turno=simulacao.turno,
            gerado_em=gravada.gerado_em.isoformat(),
            estimativa=True,
            legendas=_legendas(simulacao.registro),
            casas=[
                CasaJson.from_domain(simulacao.camara),
                CasaJson.from_domain(simulacao.assembleias),
            ],
            senado=_senado(simulacao),
            governo=_governo(simulacao),
            partidos=[ForcaPartidoJson.from_domain(item) for item in simulacao.partidos()],
            descartados=simulacao.descartados,
            notas=list(NOTAS),
        )


def _legendas(registro: RegistroPartidario) -> list[LegendaJson]:
    federadas = {partido for federacao in registro.federacoes for partido in federacao.partidos}
    rows = [
        LegendaJson(
            codigo=federacao.codigo,
            sigla=federacao.sigla,
            nome=federacao.nome,
            federacao=True,
            partidos=list(federacao.partidos),
        )
        for federacao in registro.federacoes
    ]
    rows.extend(
        LegendaJson(
            codigo=str(partido),
            sigla=str(partido),
            nome=f"Partido {partido}",
            federacao=False,
            partidos=[partido],
        )
        for partido in sorted(registro.partidos - federadas)
    )
    return rows


def _senado(simulacao: SimulacaoCadeiras) -> SenadoJson:
    senado = simulacao.senado
    return SenadoJson(
        vagas=senado.vagas,
        vagas_simuladas=sum(len(item.eleitos) for item in senado.ufs),
        ufs_sem_votos=list(senado.ufs_sem_votos),
        partidos=_parties(senado.cadeiras_por_partido()),
        ufs=[SenadoUfJson.from_domain(item) for item in senado.ufs],
    )


def _governo(simulacao: SimulacaoCadeiras) -> GovernoJson:
    governo = simulacao.governo
    eleitos = governo.eleitos_por_partido()
    segundo = governo.segundo_turno_por_partido()
    partidos = sorted(
        set(eleitos) | set(segundo), key=lambda p: (-eleitos.get(p, 0), -segundo.get(p, 0), p)
    )
    return GovernoJson(
        ufs_sem_votos=list(governo.ufs_sem_votos),
        partidos=[
            GovernoPartidoJson(
                partido=p, eleitos=eleitos.get(p, 0), segundo_turno=segundo.get(p, 0)
            )
            for p in partidos
        ],
        ufs=[GovernoUfJson.from_domain(item) for item in governo.ufs],
    )


def _ranked(counts: dict[str, int]) -> list[tuple[str, int]]:
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))


def _parties(counts: dict[int, int]) -> list[PartidoCadeirasJson]:
    ordered = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return [PartidoCadeirasJson(partido=partido, cadeiras=valor) for partido, valor in ordered]
```

- [ ] **Step 5: Encaixe HTTP** (diffs exatos):

```diff
--- a/src/eleicoes/adapters/http/bundle.py
+++ b/src/eleicoes/adapters/http/bundle.py
@@ -4,6 +4,7 @@
 
 from eleicoes.ports.boletim_consulta import AsyncBoletimReader
 from eleicoes.ports.grade import AsyncMunicipalityNames
+from eleicoes.ports.relatorio_cadeiras import AsyncSeatVoteStore
 from eleicoes.ports.relatorio_poder import AsyncRelatorioPoderStore
 from eleicoes.ports.relatorio_presidente_governador import AsyncRelatorioPresidenteGovernadorStore
 
@@ -14,3 +15,4 @@
     names: AsyncMunicipalityNames
     power_store: AsyncRelatorioPoderStore
     cross_store: AsyncRelatorioPresidenteGovernadorStore
+    seat_store: AsyncSeatVoteStore | None = None
--- a/src/eleicoes/adapters/http/dependencies.py
+++ b/src/eleicoes/adapters/http/dependencies.py
@@ -11,6 +11,7 @@
 from eleicoes.adapters.orm.sessions import AsyncSessionMaker
 from eleicoes.adapters.postgres_boletim_consulta_async import AsyncPostgresBoletimReader
 from eleicoes.adapters.postgres_municipio_async import AsyncPostgresMunicipalityNames
+from eleicoes.adapters.postgres_relatorio_cadeiras_async import AsyncPostgresSeatVoteStore
 from eleicoes.adapters.postgres_relatorio_poder_async import AsyncPostgresPowerReportStore
 from eleicoes.adapters.postgres_relatorio_presidente_governador_async import (
     AsyncPostgresPresidentGovernorStore,
@@ -21,6 +22,7 @@
 from eleicoes.ports.async_sql import AsyncPool, AsyncSqlConnection
 from eleicoes.ports.boletim_consulta import AsyncBoletimReader
 from eleicoes.ports.grade import AsyncMunicipalityNames
+from eleicoes.ports.relatorio_cadeiras import AsyncSeatVoteStore
 from eleicoes.ports.relatorio_poder import AsyncRelatorioPoderStore
 from eleicoes.ports.relatorio_presidente_governador import AsyncRelatorioPresidenteGovernadorStore
 
@@ -84,6 +86,15 @@
     return AsyncPostgresPresidentGovernorStore(_required_session(session))
 
 
+async def get_seat_store(request: Request, session: SessionDep) -> AsyncSeatVoteStore:
+    installed = _installed(request)
+    if installed is not None:
+        if installed.seat_store is None:
+            raise ElectionError("seat store is not installed")
+        return installed.seat_store
+    return AsyncPostgresSeatVoteStore(_required_session(session))
+
+
 def _installed(request: Request) -> ReadPorts | None:
     found = getattr(request.app.state, "ports", None)
     if isinstance(found, ReadPorts):
--- a/src/eleicoes/adapters/http/errors.py
+++ b/src/eleicoes/adapters/http/errors.py
@@ -22,13 +22,16 @@
     InvalidNivelError,
     InvalidNumeroError,
     InvalidOrdemError,
+    InvalidSeatRuleError,
     InvalidStoredReportError,
     InvalidTurnoError,
     InvalidUfError,
     MissingCrossReportError,
     MissingPowerReportError,
+    MissingSeatReportError,
     SchemaOutdatedError,
     StoredReadError,
+    UnknownPartyRegistryError,
     UnusableGroupCountError,
 )
 
@@ -42,6 +45,7 @@
     (InvalidOrdemError, 422, "Ordem inválida."),
     (InvalidBoletimConsultaError, 422, "Consulta de boletim inválida."),
     (InvalidStoredReportError, 422, "Relatório armazenado inválido."),
+    (InvalidSeatRuleError, 500, "Votos gravados inconsistentes para a simulação."),
     (DatabaseConfigError, 500, "Configuração do banco ausente."),
     (SchemaOutdatedError, 503, SCHEMA_OUTDATED_HINT),
 )
@@ -54,6 +58,8 @@
     (FewStatesError, 409),
     (MissingCrossReportError, 409),
     (MissingPowerReportError, 409),
+    (MissingSeatReportError, 409),
+    (UnknownPartyRegistryError, 422),
     (CargoSemCelulasError, 409),
     (InconsistentCellError, 409),
     (StoredReadError, 500),
--- a/src/eleicoes/adapters/http/relatorios.py
+++ b/src/eleicoes/adapters/http/relatorios.py
@@ -16,7 +16,9 @@
     get_municipality_names,
     get_power_store,
     get_profile_job,
+    get_seat_store,
 )
+from eleicoes.adapters.http.schemas_cadeiras import CadeirasJson
 from eleicoes.adapters.http.schemas_relatorios import (
     ClassJson,
     CrossReportJson,
@@ -25,9 +27,11 @@
 )
 from eleicoes.ports.boletim_consulta import AsyncBoletimReader
 from eleicoes.ports.grade import AsyncMunicipalityNames
+from eleicoes.ports.relatorio_cadeiras import AsyncSeatVoteStore
 from eleicoes.ports.relatorio_poder import AsyncRelatorioPoderStore
 from eleicoes.ports.relatorio_presidente_governador import AsyncRelatorioPresidenteGovernadorStore
 from eleicoes.use_cases.render_reports import RenderPowerReport, RenderPresidentGovernorReport
+from eleicoes.use_cases.simular_cadeiras import stored_simulation
 
 router = APIRouter(tags=["Relatórios"])
 Reader = Annotated[AsyncBoletimReader, Depends(get_boletim_reader)]
@@ -36,6 +40,7 @@
 CrossStore = Annotated[AsyncRelatorioPresidenteGovernadorStore, Depends(get_cross_store)]
 ProfileBuild = Annotated[ProfileJob, Depends(get_profile_job)]
 ClassBuild = Annotated[ClassJob, Depends(get_class_job)]
+SeatStore = Annotated[AsyncSeatVoteStore, Depends(get_seat_store)]
 _GRADE = (
     "Exige ano, turno, uf e cargo. nivel admite municipio, uf, regiao ou pais. "
     "A UF ancora o relatório, como na linha de comando, e não recorta um único estado "
@@ -136,6 +141,23 @@
     return ClassJson.from_domain(report)
 
 
+_CADEIRAS = (
+    "Exige ano e turno. Estima as cadeiras da Câmara, das Assembleias e do Senado e o "
+    "resultado de governador com os votos do 1º turno gravados por candidato. "
+    "É uma estimativa, não o resultado oficial. Não lê os boletins: sem os votos "
+    "gravados, responde 409 com o comando que os grava."
+)
+
+
+@router.get(
+    "/relatorios/dados/cadeiras",
+    summary="Simulação de cadeiras",
+    description=_CADEIRAS,
+)
+async def cadeiras(ano: int, turno: int, store: SeatStore) -> CadeirasJson:
+    return CadeirasJson.from_domain(await stored_simulation(store, ano, turno))
+
+
 @router.get(
     "/relatorios/poder",
     summary="Relatório de poder em HTML",
```

- [ ] **Step 6: Suíte inteira**

Run: `uv run ruff format src/eleicoes/adapters/orm/migrations/versions/r0004_relatorio_cadeiras.py src/eleicoes/ports/relatorio_cadeiras.py src/eleicoes/adapters/postgres_relatorio_cadeiras.py src/eleicoes/adapters/postgres_relatorio_cadeiras_async.py src/eleicoes/adapters/postgres_votos_candidato.py src/eleicoes/use_cases/gravar_cadeiras.py src/eleicoes/use_cases/simular_cadeiras.py src/eleicoes/composition/cadeiras.py src/eleicoes/adapters/http/schemas_cadeiras.py scripts/relatorio_cadeiras.py tests/adapters/test_postgres_relatorio_cadeiras.py tests/adapters/test_postgres_votos_candidato.py tests/adapters/test_read_api_cadeiras.py tests/use_cases/test_gravar_cadeiras.py tests/use_cases/test_simular_cadeiras.py tests/composition/test_cadeiras_wiring.py && uv run pytest -q && uv run ruff check . && uv run mypy`
Expected: N + 78 passed (N anotado no início; 956 se nenhum outro plano rodou antes), sem falhas, `Required test coverage of 85% reached`, `All checks passed!`, `Success: no issues found`.

**If Task Fails:** um 500 em `test_cadeiras_json...` com ports instalados indica que `ReadPorts(...)` foi montado sem o 5º argumento. Um 422 inesperado indica que `UnknownPartyRegistryError` não entrou em `_OWN_TEXT`.

---

### Task 13: Porta do placar (`AsyncEstimativaCadeiras`)

**Files:**
- Create: `src/eleicoes/ports/cadeiras.py`, com a interface que o plano 1 definiu na seção "Fase B" de `docs/superpowers/plans/2026-10-22-placar-forca-partidaria.md`, copiada sem mudança.
- Create: `src/eleicoes/use_cases/estimativa_cadeiras.py`
- Test: `tests/use_cases/test_estimativa_cadeiras.py`

**Prerequisites:** Task 12.

**Interfaces:**
- Produces: `Federacao(sigla, nome, partidos)`, `CadeirasUnidade(chave, uf, camara, senado, governador_1t, governador_2t, assembleia)`, `TotaisCadeiras`, `EstimativaCadeiras`, `AsyncEstimativaCadeiras` (porta); `StoredSeatEstimates(store).load(ano, turno) -> EstimativaCadeiras | None` e `estimativa_de(gravada)`.
- Regras:
  - Há uma linha por partido do registro e uma por federação (`chave = "fed:<codigo>"`), em cada UF com dado e em `"BR"`.
  - A linha da federação **soma** os membros. Isso é exato para cadeiras e governadores, que são contagens aditivas.
  - `Federacao.sigla` recebe o código interno estável (`fe-brasil`).
  - Se faltar um cargo gravado, a porta devolve `None`, como o plano 1 espera, e não levanta 409. Ano sem registro partidário (`UnknownPartyRegistryError`) também dá `None`, e não 422 (alinhado em 2026-10-22).
  - `governador_2t` conta a presença do partido entre os finalistas da UF, e não um vencedor projetado. O plano 1 rotula a coluna como "No 2º turno de governador (disputa)" (alinhado em 2026-10-22).
  - A forma da porta foi conferida campo a campo com a "Fase B" do plano 1 em 2026-10-22 e é idêntica. Lá, o exemplo de `sigla` passou a ser `"fe-brasil"`.
  - `totais.camara` e `totais.assembleias` são as vagas simuladas; `totais.senado`, os eleitos; `totais.governadores`, as UFs com resultado.

- [ ] **Step 1: Teste:**

```python
"""The scoreboard port: rows per party and federation, per UF and for Brazil."""

import asyncio
from datetime import UTC, datetime

from eleicoes.domain.cadeiras import CARGOS_GRAVADOS
from eleicoes.domain.simulacao_cadeiras import VotoApurado
from eleicoes.ports.cadeiras import CadeirasUnidade, TotaisCadeiras
from eleicoes.ports.relatorio_cadeiras import StoredSeatVotes
from eleicoes.use_cases.estimativa_cadeiras import StoredSeatEstimates

_MOMENT = datetime(2026, 10, 22, tzinfo=UTC)
_VOTOS = {
    "deputadoFederal": (
        VotoApurado("deputadoFederal", "AC", "nominal", 1301, 250),
        VotoApurado("deputadoFederal", "AC", "nominal", 6501, 150),
        VotoApurado("deputadoFederal", "AC", "nominal", 2201, 390),
    ),
    "senador": (
        VotoApurado("senador", "AC", "nominal", 222, 300),
        VotoApurado("senador", "AC", "nominal", 131, 200),
        VotoApurado("senador", "AC", "nominal", 100, 100),
    ),
    "governador": (
        VotoApurado("governador", "AC", "nominal", 13, 600),
        VotoApurado("governador", "AC", "nominal", 22, 400),
        VotoApurado("governador", "SE", "nominal", 22, 45),
        VotoApurado("governador", "SE", "nominal", 65, 35),
        VotoApurado("governador", "SE", "nominal", 15, 20),
    ),
}


class _Store:
    def __init__(self, cargos: tuple[str, ...]) -> None:
        self.cargos = cargos

    async def load(self, _ano: int, _turno: int) -> tuple[StoredSeatVotes, ...]:
        return tuple(StoredSeatVotes(c, _VOTOS.get(c, ()), _MOMENT) for c in self.cargos)


def test_rows_cover_parties_federations_ufs_and_brazil() -> None:
    found = asyncio.run(StoredSeatEstimates(_Store(CARGOS_GRAVADOS)).load(2026, 1))
    assert found is not None
    assert found.gerado_em == _MOMENT
    assert found.totais == TotaisCadeiras(camara=8, senado=2, governadores=2, assembleias=0)
    assert [f.sigla for f in found.federacoes][0] == "fe-brasil"
    rows = {(row.chave, row.uf): row for row in found.linhas}
    assert rows[("13", "AC")] == CadeirasUnidade("13", "AC", 1, 1, 1, 0, 0)
    assert rows[("65", "SE")].governador_2t == 1
    assert rows[("fed:fe-brasil", "AC")] == CadeirasUnidade("fed:fe-brasil", "AC", 2, 1, 1, 0, 0)
    assert rows[("fed:fe-brasil", "BR")] == CadeirasUnidade("fed:fe-brasil", "BR", 2, 1, 1, 1, 0)
    assert rows[("22", "BR")] == CadeirasUnidade("22", "BR", 1, 1, 0, 1, 0)
    assert {uf for _chave, uf in rows} == {"AC", "SE", "BR"}


def test_missing_cargo_is_none_for_the_scoreboard() -> None:
    assert asyncio.run(StoredSeatEstimates(_Store(("governador",))).load(2026, 1)) is None


def test_year_without_registry_is_none_for_the_scoreboard() -> None:
    # alinhado em 2026-10-22: o placar (plano 1) nunca recebe o 422 do registro
    assert asyncio.run(StoredSeatEstimates(_Store(CARGOS_GRAVADOS)).load(2022, 1)) is None
```

- [ ] **Step 2:** `uv run pytest tests/use_cases/test_estimativa_cadeiras.py -q` → `ModuleNotFoundError`.

- [ ] **Step 3: Porta** `src/eleicoes/ports/cadeiras.py`:

```python
"""Port the força partidária scoreboard (plano 1) reads. Plano 2 implements it.

Shape agreed in docs/superpowers/plans/2026-10-22-placar-forca-partidaria.md (Fase B).
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True, slots=True)
class Federacao:
    sigla: str
    nome: str
    partidos: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class CadeirasUnidade:
    chave: str
    uf: str
    camara: int | None
    senado: int | None
    governador_1t: int | None
    governador_2t: int | None
    assembleia: int | None


@dataclass(frozen=True, slots=True)
class TotaisCadeiras:
    camara: int
    senado: int
    governadores: int
    assembleias: int


@dataclass(frozen=True, slots=True)
class EstimativaCadeiras:
    ano: int
    turno: int
    gerado_em: datetime
    federacoes: tuple[Federacao, ...]
    totais: TotaisCadeiras
    linhas: tuple[CadeirasUnidade, ...]


class AsyncEstimativaCadeiras(Protocol):
    async def load(self, ano: int, turno: int) -> EstimativaCadeiras | None: ...
```

- [ ] **Step 4: Adaptador** `src/eleicoes/use_cases/estimativa_cadeiras.py`:

```python
"""Adapts the seat simulation to the scoreboard port: one row per (chave, uf), plus BR.

A party row counts its own candidates. A federation row (chave "fed:<codigo>") sums its
members, which is exact for seats and governors because they are additive counts.
"""

from collections import Counter
from collections.abc import Iterable
from typing import Final

from eleicoes.domain.boletim_consulta import partido_do_numero
from eleicoes.domain.errors import MissingSeatReportError, UnknownPartyRegistryError
from eleicoes.domain.simulacao_cadeiras import CasaSimulada
from eleicoes.ports.cadeiras import (
    CadeirasUnidade,
    EstimativaCadeiras,
    Federacao,
    TotaisCadeiras,
)
from eleicoes.ports.relatorio_cadeiras import AsyncSeatVoteStore
from eleicoes.use_cases.simular_cadeiras import SimulacaoGravada, stored_simulation

PAIS: Final = "BR"
_NOMINAL: Final = "nominal"
_FED: Final = "fed:"
_Key = tuple[int, str]


class StoredSeatEstimates:
    """AsyncEstimativaCadeiras over the stored votes.

    Missing cargos or a year without a party registry give None, never 409 or 422.
    """

    def __init__(self, store: AsyncSeatVoteStore) -> None:
        self._store = store

    async def load(self, ano: int, turno: int) -> EstimativaCadeiras | None:
        try:
            gravada = await stored_simulation(self._store, ano, turno)
        except (MissingSeatReportError, UnknownPartyRegistryError):
            return None
        return estimativa_de(gravada)


def estimativa_de(gravada: SimulacaoGravada) -> EstimativaCadeiras:
    simulacao = gravada.simulacao
    registro = simulacao.registro
    contagens = {
        "camara": _casa(simulacao.camara),
        "assembleia": _casa(simulacao.assembleias),
        "senado": _counts((e.partido, uf.uf) for uf in simulacao.senado.ufs for e in uf.eleitos),
        "governador_1t": _counts(
            (uf.eleito.partido, uf.uf) for uf in simulacao.governo.ufs if uf.eleito is not None
        ),
        "governador_2t": _counts(
            (item.partido, uf.uf) for uf in simulacao.governo.ufs for item in uf.finalistas
        ),
    }
    ufs = sorted({uf for counter in contagens.values() for _p, uf in counter})
    lugares = (*ufs, PAIS)
    linhas = [
        _linha(str(partido), (partido,), uf, contagens)
        for partido in sorted(registro.partidos)
        for uf in lugares
    ]
    linhas.extend(
        _linha(f"{_FED}{federacao.codigo}", federacao.partidos, uf, contagens)
        for federacao in registro.federacoes
        for uf in lugares
    )
    return EstimativaCadeiras(
        ano=simulacao.ano,
        turno=simulacao.turno,
        gerado_em=gravada.gerado_em,
        federacoes=tuple(
            Federacao(federacao.codigo, federacao.nome, federacao.partidos)
            for federacao in registro.federacoes
        ),
        totais=TotaisCadeiras(
            camara=simulacao.camara.vagas_simuladas,
            senado=sum(len(uf.eleitos) for uf in simulacao.senado.ufs),
            governadores=len(simulacao.governo.ufs),
            assembleias=simulacao.assembleias.vagas_simuladas,
        ),
        linhas=tuple(linhas),
    )


def _casa(casa: CasaSimulada) -> Counter[_Key]:
    return _counts(
        (partido_do_numero(_NOMINAL, eleito.numero), item.uf)
        for item in casa.ufs
        for eleito in item.resultado.eleitos
    )


def _counts(pairs: Iterable[_Key]) -> Counter[_Key]:
    return Counter(pairs)


def _linha(
    chave: str,
    partidos: tuple[int, ...],
    uf: str,
    contagens: dict[str, Counter[_Key]],
) -> CadeirasUnidade:
    def soma(nome: str) -> int:
        counter = contagens[nome]
        if uf == PAIS:
            return sum(n for (partido, _uf), n in counter.items() if partido in partidos)
        return sum(counter[(partido, uf)] for partido in partidos)

    return CadeirasUnidade(
        chave=chave,
        uf=uf,
        camara=soma("camara"),
        senado=soma("senado"),
        governador_1t=soma("governador_1t"),
        governador_2t=soma("governador_2t"),
        assembleia=soma("assembleia"),
    )
```

- [ ] **Step 5:** `uv run ruff format src/eleicoes/ports/cadeiras.py src/eleicoes/use_cases/estimativa_cadeiras.py tests/use_cases/test_estimativa_cadeiras.py && uv run pytest -q && uv run ruff check . && uv run mypy` → N + 81 passed, sem falhas; limpo. São 81 porque o teste `test_year_without_registry_is_none_for_the_scoreboard` foi acrescentado depois do protótipo (alinhado em 2026-10-22).

**If Task Fails:** se o plano 1 já tiver criado `ports/cadeiras.py`, não sobrescreva. Compare com o Step 3. Se a forma for igual, só crie o adaptador. Se divergir, pare e avise.

---

### Task 14: Migrar e gravar os votos (operacional)

**Prerequisites:** Task 13 verde. Compose de pé. Avisar o usuário: cada cargo é uma varredura sequencial da tabela de 26 GB (*Parallel Seq Scan* no `EXPLAIN`). Contar de 5 a 30 minutos por cargo, uma vez só.

- [ ] **Step 1:** `make migrate` → termina sem erro. Conferir com `docker compose exec -T postgres sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -At -c "select version_num from alembic_version"'`, que deve dar `0004`.
- [ ] **Step 2:** reconstruir a API para carregar o código novo: `docker compose up -d --build api`. Depois, `curl -s localhost:15000/health` → `{"status":"ok"}`.
- [ ] **Step 3:** num terminal do usuário (é longo), na raiz: `uv run python scripts/relatorio_cadeiras.py`. Saída esperada, com números ilustrativos:

```
Somando os votos de governador nos boletins...
Somando os votos de senador nos boletins...
Somando os votos de deputadoFederal nos boletins...
Somando os votos de deputadoEstadual nos boletins...
Somando os votos de deputadoDistrital nos boletins...
governador: 2xx números gravados em 2026-10-22 HH:MM.
senador: 2xx números gravados em ...
deputadoFederal: 1x.xxx números gravados em ...
deputadoEstadual: 1x.xxx números gravados em ...
deputadoDistrital: 9xx números gravados em ...
Câmara: 513 de 513 vagas.
Assembleias: 1.059 de 1.059 vagas.
Senado: 54 de 54 vagas.
Governadores eleitos no 1º turno: N de 27 UFs.
```

  Se aparecer "x de 513", faltam boletins de alguma UF. Ver `ufs_sem_votos` no JSON e avisar o usuário.

- [ ] **Step 4:** `curl -s "localhost:15000/relatorios/dados/cadeiras?ano=2026&turno=1" | python -m json.tool | head -40` → `"estimativa": true` e duas `casas`.
- [ ] **Step 5: Conferir o AC com o protótipo.** O protótipo rodou em 2026-10-22, com consulta só de leitura dos votos do AC:
  - Câmara (8 vagas, QE 58.582): UNIÃO PROGRESSISTA 4 (1101, 4444, 4422, 1111), MDB 15 com 2, REPUBLICANOS 10 com 1, PL 22 com 1.
  - Assembleia (24 vagas, QE 19.716): UNIÃO PROGRESSISTA 9, PL 4, REPUBLICANOS 3, MDB 2, PSD 2, PDT 1, NOVO 1, FE BRASIL 1, PSDB CIDADANIA 1.
  - Senado: 222 e 100.
  - Governador: 2º turno entre 11 (49,76%) e 10.

  A API deve dar o mesmo, desde que os boletins do AC não tenham mudado.

---

### Task 15: Code Review (API)

1. **REQUIRED SUB-SKILL:** Use jarvis:codereview — dispatch all reviewers in parallel.
2. **Foco:** contrato JSON e porta `AsyncEstimativaCadeiras` contra a "Fase B" do plano 1, 409 sem leitura de boletim e mensagens em português ao usuário.
3. **Proceed only when:** zero Critical/High/Medium issues remain.

---

### Task 16: Frontend — tipos, leitura e busca

**Files:**
- Modify: `frontend/src/lib/relatorios.ts`. Os tipos entram logo antes de `const ROTULOS_CLASSE` (linha 134 hoje); `lerCadeiras` e as funções auxiliares entram logo antes de `function lerComposicao(` (linha 226 hoje). Os helpers `exigir*` já existem no arquivo.
- Modify: `frontend/src/lib/buscar-relatorios.ts`

- [ ] **Step 1: Tipos** (inserir antes de `const ROTULOS_CLASSE`):

```ts
export type LegendaCadeiras = {
  codigo: string;
  sigla: string;
  nome: string;
  federacao: boolean;
  partidos: number[];
};

export type ListaCadeiras = {
  legenda: string;
  votos: number;
  votos_legenda: number;
  quociente_partidario: number;
  cadeiras_quociente: number;
  cadeiras_media: number;
  cadeiras_media_livre: number;
  cadeiras: number;
};

export type EleitoCadeiras = {
  numero: number;
  partido: number;
  legenda: string;
  votos: number;
  fase: string;
  empate: boolean;
};

export type CasaUfCadeiras = {
  uf: string;
  cargo: string;
  vagas: number;
  votos_validos: number;
  quociente_eleitoral: number;
  vagas_sem_candidato: number;
  listas: ListaCadeiras[];
  eleitos: EleitoCadeiras[];
};

export type ContagemLegenda = { legenda: string; cadeiras: number };
export type ContagemPartido = { partido: number; cadeiras: number };

export type CasaCadeiras = {
  casa: string;
  nome: string;
  vagas: number;
  vagas_simuladas: number;
  ufs_sem_votos: string[];
  legendas: ContagemLegenda[];
  partidos: ContagemPartido[];
  ufs: CasaUfCadeiras[];
};

export type CandidatoMajoritario = {
  numero: number;
  partido: number;
  votos: number;
  fatia: string;
};

export type SenadoUf = {
  uf: string;
  votos_validos: number;
  eleitos: CandidatoMajoritario[];
  empate: boolean;
};

export type SenadoCadeiras = {
  vagas: number;
  vagas_simuladas: number;
  ufs_sem_votos: string[];
  partidos: ContagemPartido[];
  ufs: SenadoUf[];
};

export type GovernoUf = {
  uf: string;
  situacao: string;
  votos_validos: number;
  candidatos: CandidatoMajoritario[];
  empate: boolean;
};

export type GovernoCadeiras = {
  ufs_sem_votos: string[];
  partidos: { partido: number; eleitos: number; segundo_turno: number }[];
  ufs: GovernoUf[];
};

export type ForcaPartido = {
  partido: number;
  legenda: string;
  camara: number;
  assembleias: number;
  senado: number;
  governadores: number;
  governadores_segundo_turno: number;
};

export type SimulacaoCadeiras = {
  ano: number;
  turno: number;
  gerado_em: string;
  estimativa: boolean;
  legendas: LegendaCadeiras[];
  casas: CasaCadeiras[];
  senado: SenadoCadeiras;
  governo: GovernoCadeiras;
  partidos: ForcaPartido[];
  descartados: number;
  notas: string[];
};
```

- [ ] **Step 2: Leitura** (inserir antes de `function lerComposicao(`):

```ts
export function lerCadeiras(valor: unknown): SimulacaoCadeiras {
  const registro = exigirRegistro(valor);
  return {
    ano: exigirInteiro(registro.ano),
    turno: exigirInteiro(registro.turno),
    gerado_em: exigirTexto(registro.gerado_em),
    estimativa: exigirBooleano(registro.estimativa),
    legendas: exigirLista(registro.legendas, lerLegendaCadeiras),
    casas: exigirLista(registro.casas, lerCasaCadeiras),
    senado: lerSenadoCadeiras(registro.senado),
    governo: lerGovernoCadeiras(registro.governo),
    partidos: exigirLista(registro.partidos, lerForcaPartido),
    descartados: exigirInteiro(registro.descartados),
    notas: exigirLista(registro.notas, exigirTexto),
  };
}

function lerLegendaCadeiras(valor: unknown): LegendaCadeiras {
  const registro = exigirRegistro(valor);
  return {
    codigo: exigirTexto(registro.codigo),
    sigla: exigirTexto(registro.sigla),
    nome: exigirTexto(registro.nome),
    federacao: exigirBooleano(registro.federacao),
    partidos: exigirLista(registro.partidos, exigirInteiro),
  };
}

function lerCasaCadeiras(valor: unknown): CasaCadeiras {
  const registro = exigirRegistro(valor);
  return {
    casa: exigirTexto(registro.casa),
    nome: exigirTexto(registro.nome),
    vagas: exigirInteiro(registro.vagas),
    vagas_simuladas: exigirInteiro(registro.vagas_simuladas),
    ufs_sem_votos: exigirLista(registro.ufs_sem_votos, exigirTexto),
    legendas: exigirLista(registro.legendas, lerContagemLegenda),
    partidos: exigirLista(registro.partidos, lerContagemPartido),
    ufs: exigirLista(registro.ufs, lerCasaUf),
  };
}

function lerContagemLegenda(valor: unknown): ContagemLegenda {
  const registro = exigirRegistro(valor);
  return { legenda: exigirTexto(registro.legenda), cadeiras: exigirInteiro(registro.cadeiras) };
}

function lerContagemPartido(valor: unknown): ContagemPartido {
  const registro = exigirRegistro(valor);
  return { partido: exigirInteiro(registro.partido), cadeiras: exigirInteiro(registro.cadeiras) };
}

function lerCasaUf(valor: unknown): CasaUfCadeiras {
  const registro = exigirRegistro(valor);
  return {
    uf: exigirTexto(registro.uf),
    cargo: exigirTexto(registro.cargo),
    vagas: exigirInteiro(registro.vagas),
    votos_validos: exigirInteiro(registro.votos_validos),
    quociente_eleitoral: exigirInteiro(registro.quociente_eleitoral),
    vagas_sem_candidato: exigirInteiro(registro.vagas_sem_candidato),
    listas: exigirLista(registro.listas, lerListaCadeiras),
    eleitos: exigirLista(registro.eleitos, lerEleitoCadeiras),
  };
}

function lerListaCadeiras(valor: unknown): ListaCadeiras {
  const registro = exigirRegistro(valor);
  return {
    legenda: exigirTexto(registro.legenda),
    votos: exigirInteiro(registro.votos),
    votos_legenda: exigirInteiro(registro.votos_legenda),
    quociente_partidario: exigirInteiro(registro.quociente_partidario),
    cadeiras_quociente: exigirInteiro(registro.cadeiras_quociente),
    cadeiras_media: exigirInteiro(registro.cadeiras_media),
    cadeiras_media_livre: exigirInteiro(registro.cadeiras_media_livre),
    cadeiras: exigirInteiro(registro.cadeiras),
  };
}

function lerEleitoCadeiras(valor: unknown): EleitoCadeiras {
  const registro = exigirRegistro(valor);
  return {
    numero: exigirInteiro(registro.numero),
    partido: exigirInteiro(registro.partido),
    legenda: exigirTexto(registro.legenda),
    votos: exigirInteiro(registro.votos),
    fase: exigirTexto(registro.fase),
    empate: exigirBooleano(registro.empate),
  };
}

function lerCandidatoMajoritario(valor: unknown): CandidatoMajoritario {
  const registro = exigirRegistro(valor);
  return {
    numero: exigirInteiro(registro.numero),
    partido: exigirInteiro(registro.partido),
    votos: exigirInteiro(registro.votos),
    fatia: exigirTexto(registro.fatia),
  };
}

function lerSenadoCadeiras(valor: unknown): SenadoCadeiras {
  const registro = exigirRegistro(valor);
  return {
    vagas: exigirInteiro(registro.vagas),
    vagas_simuladas: exigirInteiro(registro.vagas_simuladas),
    ufs_sem_votos: exigirLista(registro.ufs_sem_votos, exigirTexto),
    partidos: exigirLista(registro.partidos, lerContagemPartido),
    ufs: exigirLista(registro.ufs, (item) => {
      const uf = exigirRegistro(item);
      return {
        uf: exigirTexto(uf.uf),
        votos_validos: exigirInteiro(uf.votos_validos),
        eleitos: exigirLista(uf.eleitos, lerCandidatoMajoritario),
        empate: exigirBooleano(uf.empate),
      };
    }),
  };
}

function lerGovernoCadeiras(valor: unknown): GovernoCadeiras {
  const registro = exigirRegistro(valor);
  return {
    ufs_sem_votos: exigirLista(registro.ufs_sem_votos, exigirTexto),
    partidos: exigirLista(registro.partidos, (item) => {
      const linha = exigirRegistro(item);
      return {
        partido: exigirInteiro(linha.partido),
        eleitos: exigirInteiro(linha.eleitos),
        segundo_turno: exigirInteiro(linha.segundo_turno),
      };
    }),
    ufs: exigirLista(registro.ufs, (item) => {
      const uf = exigirRegistro(item);
      return {
        uf: exigirTexto(uf.uf),
        situacao: exigirTexto(uf.situacao),
        votos_validos: exigirInteiro(uf.votos_validos),
        candidatos: exigirLista(uf.candidatos, lerCandidatoMajoritario),
        empate: exigirBooleano(uf.empate),
      };
    }),
  };
}

function lerForcaPartido(valor: unknown): ForcaPartido {
  const registro = exigirRegistro(valor);
  return {
    partido: exigirInteiro(registro.partido),
    legenda: exigirTexto(registro.legenda),
    camara: exigirInteiro(registro.camara),
    assembleias: exigirInteiro(registro.assembleias),
    senado: exigirInteiro(registro.senado),
    governadores: exigirInteiro(registro.governadores),
    governadores_segundo_turno: exigirInteiro(registro.governadores_segundo_turno),
  };
}
```

- [ ] **Step 3: Busca** (diff exato):

```diff
--- a/frontend/src/lib/buscar-relatorios.ts
+++ b/frontend/src/lib/buscar-relatorios.ts
@@ -1,5 +1,6 @@
 import { urlApi } from "@/lib/eleicoes";
 import {
+  lerCadeiras,
   lerClasseGovernador,
   lerGrade,
   lerRelatorioCruzado,
@@ -9,6 +10,7 @@
   type RelatorioClasseGovernador,
   type RelatorioCruzado,
   type RelatorioPerfis,
+  type SimulacaoCadeiras,
 } from "@/lib/relatorios";
 
 export type Resultado<T> =
@@ -67,6 +69,14 @@
   return buscar("/relatorios/dados/classe-governador", params, lerClasseGovernador);
 }
 
+export function buscarCadeiras(
+  ano: string,
+  turno: string,
+): Promise<Resultado<SimulacaoCadeiras>> {
+  const params = new URLSearchParams({ ano, turno });
+  return buscar("/relatorios/dados/cadeiras", params, lerCadeiras);
+}
+
 async function buscar<T>(
   caminho: string,
   params: URLSearchParams,
```

- [ ] **Step 4:** `cd frontend && pnpm exec tsc --noEmit && pnpm exec eslint src/lib/relatorios.ts src/lib/buscar-relatorios.ts` → sem saída.

---

### Task 17: Frontend — módulo puro do gráfico

**Files:**
- Create: `frontend/src/lib/grafico-cadeiras.ts`
- Test: `frontend/src/lib/verificar-grafico-cadeiras.ts`

**Prerequisites:** Task 16. O script só importa **tipos** de `relatorios.ts`, porque esse arquivo usa o alias `@/` e o Node não o resolve.

**Interfaces:**
- Consumes: `MEDIDAS_PADRAO`, `ItemBarra`, `MedidasBarras` de `./grafico-poder.ts`; `larguraTexto`; `rotuloPartido`; `formatarInteiro`.
- Produces: `MEDIDAS_CADEIRAS`, `rotuloFase`, `rotuloSituacao`, `rotuloLegenda`, `rotuloCabe`, `cadeiras`, `itensCasa`, `itensSenado`, `frasesCadeiras`.

- [ ] **Step 1: Script de verificação:**

```ts
import assert from "node:assert/strict";
import {
  MEDIDAS_CADEIRAS,
  frasesCadeiras,
  itensCasa,
  itensSenado,
  rotuloCabe,
  rotuloFase,
  rotuloLegenda,
  rotuloSituacao,
} from "./grafico-cadeiras.ts";
import { MEDIDAS_ESTREITO, layoutBarras } from "./grafico-poder.ts";
import type { SimulacaoCadeiras } from "./relatorios.ts";

const legendas = [
  { codigo: "fe-brasil", sigla: "FE BRASIL", nome: "Federação Brasil da Esperança", federacao: true, partidos: [13, 65, 43] },
  { codigo: "renovacao-solidaria", sigla: "RENOVAÇÃO SOLIDÁRIA", nome: "Federação Renovação Solidária", federacao: true, partidos: [25, 77] },
  { codigo: "uniao-progressista", sigla: "UNIÃO PROGRESSISTA", nome: "Federação União Progressista", federacao: true, partidos: [44, 11] },
  { codigo: "22", sigla: "22", nome: "Partido 22", federacao: false, partidos: [22] },
];

function casa(nome: string, sem: string[] = []): SimulacaoCadeiras["casas"][number] {
  return {
    casa: nome === "Câmara dos Deputados" ? "camara" : "assembleias",
    nome,
    vagas: 513,
    vagas_simuladas: sem.length > 0 ? 505 : 513,
    ufs_sem_votos: sem,
    legendas: [
      { legenda: "22", cadeiras: 90 },
      { legenda: "fe-brasil", cadeiras: 90 },
      { legenda: "renovacao-solidaria", cadeiras: 0 },
    ],
    partidos: [{ partido: 22, cadeiras: 90 }, { partido: 13, cadeiras: 80 }, { partido: 65, cadeiras: 10 }],
    ufs: [{
      uf: "AC", cargo: "deputadoFederal", vagas: 8, votos_validos: 800, quociente_eleitoral: 100,
      vagas_sem_candidato: 0, listas: [],
      eleitos: [{ numero: 1301, partido: 13, legenda: "fe-brasil", votos: 250, fase: "quociente", empate: true }],
    }],
  };
}

const simulacao: SimulacaoCadeiras = {
  ano: 2026, turno: 1, gerado_em: "2026-10-22T00:00:00+00:00", estimativa: true, legendas,
  casas: [casa("Câmara dos Deputados", ["AC"])],
  senado: { vagas: 54, vagas_simuladas: 2, ufs_sem_votos: [], partidos: [{ partido: 22, cadeiras: 2 }, { partido: 13, cadeiras: 0 }],
    ufs: [{ uf: "AC", votos_validos: 10, eleitos: [], empate: false }] },
  governo: { ufs_sem_votos: [], partidos: [], ufs: [
    { uf: "AC", situacao: "segundo_turno", votos_validos: 10, candidatos: [], empate: false },
    { uf: "SE", situacao: "eleito", votos_validos: 10, candidatos: [], empate: false },
    { uf: "SP", situacao: "eleito", votos_validos: 10, candidatos: [], empate: true },
  ] },
  partidos: [], descartados: 0, notas: [],
};

// rótulos
assert.equal(rotuloLegenda("fe-brasil", legendas), "FE BRASIL");
assert.equal(rotuloLegenda("22", legendas), "PL 22");
assert.equal(rotuloLegenda("xx", legendas), "xx");
assert.equal(rotuloFase("media_livre"), "Média (todas as legendas)");
assert.equal(rotuloSituacao("segundo_turno"), "2º turno");
for (const legenda of legendas) {
  assert.ok(rotuloCabe(rotuloLegenda(legenda.codigo, legendas)), legenda.codigo);
}
assert.equal(rotuloCabe("X".repeat(30)), false);

// itens: sem zeros, ordenados por cadeiras e depois por rótulo; federação detalha os membros
const itens = itensCasa(simulacao.casas[0]!, legendas);
assert.deepEqual(itens.map((item) => item.rotulo), ["FE BRASIL", "PL 22"]);
assert.equal(itens[0]!.detalhe, "90 de 505 vagas simuladas\nPT 13: 80\nPCdoB 65: 10\nPV 43: 0");
assert.equal(itens[1]!.detalhe, "90 de 505 vagas simuladas");
assert.deepEqual(itensSenado(simulacao).map((item) => [item.rotulo, item.texto]), [["PL 22", "2"]]);

// layout com a margem própria e na tela estreita
const layout = layoutBarras(itens, MEDIDAS_CADEIRAS)!;
assert.equal(layout.barras[0]!.largura, 640 - 152 - 72);
assert.ok(layoutBarras(itens, MEDIDAS_ESTREITO) !== null);
assert.equal(layoutBarras([], MEDIDAS_CADEIRAS), null);

// frases
assert.deepEqual(frasesCadeiras(simulacao), [
  "Câmara dos Deputados: empatam FE BRASIL e PL 22, com 90 cadeiras de 505.",
  "Câmara dos Deputados: faltam votos gravados de AC; 8 vagas ficaram fora da conta.",
  "Governador: 2 UFs elegeriam no 1º turno e 1 iria ao 2º turno.",
  "2 resultados dependem de um desempate que os boletins não resolvem (idade do candidato).",
]);
console.log("ok");
```

- [ ] **Step 2:** `cd frontend && node --experimental-strip-types src/lib/verificar-grafico-cadeiras.ts` → `ERR_MODULE_NOT_FOUND` para `grafico-cadeiras.ts`.

- [ ] **Step 3: Módulo:**

```ts
import { formatarInteiro } from "./fracao.ts";
import { MEDIDAS_PADRAO, type ItemBarra, type MedidasBarras } from "./grafico-poder.ts";
import { larguraTexto } from "./largura-texto.ts";
import { rotuloPartido } from "./partidos.ts";
import type {
  CasaCadeiras,
  ContagemPartido,
  LegendaCadeiras,
  SimulacaoCadeiras,
} from "./relatorios.ts";

// "RENOVAÇÃO SOLIDÁRIA" tem 19 caracteres: 0,6 × 12 × 19 ≈ 137 px, mais 8 px de folga.
export const MEDIDAS_CADEIRAS: MedidasBarras = { ...MEDIDAS_PADRAO, esquerda: 152 };

const FASES: Record<string, string> = {
  quociente: "Quociente partidário",
  media: "Média (80% e 20%)",
  media_livre: "Média (todas as legendas)",
};

const SITUACOES: Record<string, string> = {
  eleito: "Eleito no 1º turno",
  segundo_turno: "2º turno",
  sem_votos: "Sem votos",
};

export function rotuloFase(fase: string): string {
  return FASES[fase] ?? fase;
}

export function rotuloSituacao(situacao: string): string {
  return SITUACOES[situacao] ?? situacao;
}

export function rotuloLegenda(codigo: string, legendas: readonly LegendaCadeiras[]): string {
  const legenda = legendas.find((item) => item.codigo === codigo);
  if (legenda?.federacao) {
    return legenda.sigla;
  }
  const numero = Number(codigo);
  return Number.isSafeInteger(numero) ? rotuloPartido(numero) : codigo;
}

export function rotuloCabe(rotulo: string, medidas: MedidasBarras = MEDIDAS_CADEIRAS): boolean {
  return larguraTexto(rotulo, medidas.fonte) + 8 <= medidas.esquerda;
}

export function cadeiras(n: number): string {
  return `${formatarInteiro(n)} ${n === 1 ? "cadeira" : "cadeiras"}`;
}

export function itensCasa(
  casa: CasaCadeiras,
  legendas: readonly LegendaCadeiras[],
): ItemBarra[] {
  return casa.legendas
    .filter((item) => item.cadeiras > 0)
    .map((item) => {
      const legenda = legendas.find((linha) => linha.codigo === item.legenda);
      const membros = legenda?.federacao ? detalheFederacao(legenda, casa.partidos) : "";
      const fatia = `${formatarInteiro(item.cadeiras)} de ${formatarInteiro(casa.vagas_simuladas)} vagas simuladas`;
      return {
        chave: item.legenda,
        rotulo: rotuloLegenda(item.legenda, legendas),
        valor: item.cadeiras,
        texto: formatarInteiro(item.cadeiras),
        detalhe: membros === "" ? fatia : `${fatia}\n${membros}`,
      };
    })
    .sort((a, b) => b.valor - a.valor || a.rotulo.localeCompare(b.rotulo, "pt-BR"));
}

export function itensSenado(simulacao: SimulacaoCadeiras): ItemBarra[] {
  return simulacao.senado.partidos
    .filter((item) => item.cadeiras > 0)
    .map((item) => ({
      chave: String(item.partido),
      rotulo: rotuloPartido(item.partido),
      valor: item.cadeiras,
      texto: formatarInteiro(item.cadeiras),
      detalhe: `${formatarInteiro(item.cadeiras)} de ${formatarInteiro(simulacao.senado.vagas_simuladas)} vagas simuladas`,
    }));
}

export function frasesCadeiras(simulacao: SimulacaoCadeiras): string[] {
  const frases: string[] = [];
  for (const casa of simulacao.casas) {
    const itens = itensCasa(casa, simulacao.legendas);
    const maior = itens[0];
    if (maior === undefined) {
      continue;
    }
    const empatadas = itens.filter((item) => item.valor === maior.valor).map((item) => item.rotulo);
    const quem = empatadas.length > 1 ? `empatam ${juntar(empatadas)}` : `a maior bancada é ${maior.rotulo}`;
    frases.push(
      `${casa.nome}: ${quem}, com ${cadeiras(maior.valor)} de ${formatarInteiro(casa.vagas_simuladas)}.`,
    );
    if (casa.ufs_sem_votos.length > 0) {
      frases.push(
        `${casa.nome}: faltam votos gravados de ${juntar(casa.ufs_sem_votos)}; ${formatarInteiro(casa.vagas - casa.vagas_simuladas)} vagas ficaram fora da conta.`,
      );
    }
  }
  const governo = simulacao.governo.ufs;
  const eleitos = governo.filter((uf) => uf.situacao === "eleito").length;
  const segundo = governo.filter((uf) => uf.situacao === "segundo_turno").length;
  if (governo.length > 0) {
    frases.push(
      `Governador: ${formatarInteiro(eleitos)} ${eleitos === 1 ? "UF elegeria" : "UFs elegeriam"} no 1º turno e ${formatarInteiro(segundo)} ${segundo === 1 ? "iria" : "iriam"} ao 2º turno.`,
    );
  }
  const empates = contarEmpates(simulacao);
  if (empates > 0) {
    frases.push(
      `${formatarInteiro(empates)} ${empates === 1 ? "resultado depende" : "resultados dependem"} de um desempate que os boletins não resolvem (idade do candidato).`,
    );
  }
  return frases;
}

function detalheFederacao(legenda: LegendaCadeiras, partidos: readonly ContagemPartido[]): string {
  return legenda.partidos
    .map((numero) => {
      const n = partidos.find((item) => item.partido === numero)?.cadeiras ?? 0;
      return `${rotuloPartido(numero)}: ${formatarInteiro(n)}`;
    })
    .join("\n");
}

function contarEmpates(simulacao: SimulacaoCadeiras): number {
  const proporcionais = simulacao.casas.reduce(
    (soma, casa) =>
      soma + casa.ufs.reduce((parcial, uf) => parcial + uf.eleitos.filter((e) => e.empate).length, 0),
    0,
  );
  const senado = simulacao.senado.ufs.filter((uf) => uf.empate).length;
  const governo = simulacao.governo.ufs.filter((uf) => uf.empate).length;
  return proporcionais + senado + governo;
}

function juntar(itens: readonly string[]): string {
  if (itens.length <= 1) {
    return itens.join("");
  }
  return `${itens.slice(0, -1).join(", ")} e ${itens[itens.length - 1]}`;
}
```

- [ ] **Step 4:** `node --experimental-strip-types src/lib/verificar-grafico-cadeiras.ts && node --experimental-strip-types src/lib/verificar-grafico-poder.ts && pnpm exec tsc --noEmit && pnpm exec eslint src/lib/grafico-cadeiras.ts src/lib/verificar-grafico-cadeiras.ts` → `ok`, `ok`, sem saída.

---

### Task 18: Frontend — componentes, página e navegação

**Files:**
- Modify: `frontend/src/components/relatorios/grafico-poder.tsx` (prop opcional `medidas`; o poder continua igual)
- Create: `frontend/src/components/relatorios/explicacao-cadeiras.tsx`
- Create: `frontend/src/components/relatorios/tabela-cadeiras.tsx`
- Create: `frontend/src/components/relatorios/dados-cadeiras.tsx`
- Create: `frontend/src/app/relatorios/cadeiras/page.tsx`
- Modify: `frontend/src/components/layout/app-sidebar.tsx`, `frontend/src/components/layout/app-breadcrumb.tsx`
- Modify (alinhado em 2026-10-22): `frontend/src/app/page.tsx`. Em `DESTINOS`, acrescente `{ href: "/relatorios/cadeiras", titulo: "Simulação de cadeiras", descricao: "Estimativa de cadeiras na Câmara, nas Assembleias, no Senado e nos governos." }` na mesma posição do bloco.

**Posição na navegação (alinhado em 2026-10-22):** "Cadeiras" é a 2ª entrada do bloco dos seis planos, entre "Classe do governador" e "Mapa". Se "Força partidária" (plano 1) já existir, fica depois dela. Os diffs abaixo assumem que este plano é o primeiro a integrar (ordem 2 → 6 → 1).

- [ ] **Step 1: `GraficoPoder` com margem opcional, sidebar e breadcrumb** (diffs exatos):

```diff
--- a/frontend/src/components/relatorios/grafico-poder.tsx
+++ b/frontend/src/components/relatorios/grafico-poder.tsx
@@ -5,6 +5,7 @@
   resumoBarras,
   type ItemBarra,
   type LayoutBarras,
+  type MedidasBarras,
 } from "@/lib/grafico-poder";
 
 type GraficoPoderProps = {
@@ -13,10 +14,18 @@
   introducao: string;
   legenda: string;
   itens: readonly ItemBarra[];
+  medidas?: MedidasBarras;
 };
 
-export function GraficoPoder({ id, titulo, introducao, legenda, itens }: GraficoPoderProps) {
-  const layout = layoutBarras(itens);
+export function GraficoPoder({
+  id,
+  titulo,
+  introducao,
+  legenda,
+  itens,
+  medidas,
+}: GraficoPoderProps) {
+  const layout = layoutBarras(itens, medidas);
   const estreito = layoutBarras(itens, MEDIDAS_ESTREITO);
   if (layout === null || estreito === null) {
     return null;
--- a/frontend/src/components/layout/app-sidebar.tsx
+++ b/frontend/src/components/layout/app-sidebar.tsx
@@ -23,6 +23,7 @@
   { href: "/relatorios/poder", rotulo: "Poder" },
   { href: "/relatorios/perfis", rotulo: "Perfis" },
   { href: "/relatorios/classe-governador", rotulo: "Classe do governador" },
+  { href: "/relatorios/cadeiras", rotulo: "Cadeiras" },
   { href: "/mapa", rotulo: "Mapa" },
 ] as const;
 
--- a/frontend/src/components/layout/app-breadcrumb.tsx
+++ b/frontend/src/components/layout/app-breadcrumb.tsx
@@ -29,6 +29,7 @@
     pagina: "Classe do governador",
     relatorios: true,
   },
+  "/relatorios/cadeiras": { pagina: "Simulação de cadeiras", relatorios: true },
   "/mapa": { pagina: "Mapa", relatorios: false },
 };
 
```

- [ ] **Step 2: Explicação** `explicacao-cadeiras.tsx`:

```tsx
export function ExplicacaoCadeiras() {
  return (
    <section
      aria-labelledby="como-ler-cadeiras"
      className="flex max-w-3xl flex-col gap-3"
    >
      <h2 id="como-ler-cadeiras" className="text-xl font-semibold">
        Como a estimativa é feita
      </h2>
      <p>
        Os votos de cada número de candidato foram somados nos boletins de urna do 1º turno. Com
        eles, a página refaz as contas da Justiça Eleitoral para cada UF.
      </p>
      <ul className="flex list-disc flex-col gap-1 pl-5">
        <li>
          <strong>Câmara e Assembleias.</strong> O quociente eleitoral é o total de votos válidos
          (nominais e de legenda) dividido pelas vagas da UF. Cada partido ou federação leva tantas
          vagas quantas vezes alcança o quociente, desde que o candidato tenha pelo menos 10% do
          quociente. As vagas que sobram vão pelas maiores médias: primeiro entre as legendas com
          80% do quociente e candidato com 20%; depois entre todas.
        </li>
        <li>
          <strong>Federação.</strong> Partidos federados disputam como uma lista só. A cadeira fica
          com o partido do número do candidato eleito.
        </li>
        <li>
          <strong>Senado.</strong> Em 2026 cada UF elege dois senadores: os dois mais votados.
        </li>
        <li>
          <strong>Governador.</strong> Quem passa da metade dos votos válidos se elege no 1º turno.
          Senão, os dois mais votados vão ao 2º turno.
        </li>
      </ul>
      <p>
        <strong>Por que é estimativa.</strong> O boletim de urna não diz se o registro do candidato
        foi indeferido. Na totalização oficial esses votos são anulados; aqui eles contam. O boletim
        também não traz a idade, que desempata candidatos. Resultados que dependem disso aparecem
        marcados. Por fim, a lista de federações é a cadastrada no projeto e pode estar
        desatualizada.
      </p>
    </section>
  );
}
```

- [ ] **Step 3: Tabelas** `tabela-cadeiras.tsx`:

```tsx
import {
  Table,
  TableBody,
  TableCaption,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { formatarInteiro } from "@/lib/fracao";
import { rotuloFase, rotuloLegenda, rotuloSituacao } from "@/lib/grafico-cadeiras";
import { rotuloPartido } from "@/lib/partidos";
import type {
  CandidatoMajoritario,
  CasaCadeiras,
  CasaUfCadeiras,
  GovernoCadeiras,
  LegendaCadeiras,
  SenadoCadeiras,
} from "@/lib/relatorios";

const MARCA_EMPATE = " *";

function candidato(item: CandidatoMajoritario | undefined): string {
  if (item === undefined) {
    return "—";
  }
  return `Nº ${item.numero} (${rotuloPartido(item.partido)}), ${item.fatia}`;
}

export function TabelaLegendasCasa({
  casa,
  legendas,
}: {
  casa: CasaCadeiras;
  legendas: readonly LegendaCadeiras[];
}) {
  return (
    <Table containerClassName="folha">
      <TableCaption className="sr-only">Cadeiras estimadas por legenda — {casa.nome}</TableCaption>
      <TableHeader>
        <TableRow>
          <TableHead scope="col">Partido ou federação</TableHead>
          <TableHead scope="col" className="text-right">
            Cadeiras
          </TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {casa.legendas.map((item) => {
          const legenda = legendas.find((linha) => linha.codigo === item.legenda);
          const membros = legenda?.federacao
            ? legenda.partidos
                .map(
                  (numero) =>
                    `${rotuloPartido(numero)}: ${formatarInteiro(
                      casa.partidos.find((linha) => linha.partido === numero)?.cadeiras ?? 0,
                    )}`,
                )
                .join(" · ")
            : null;
          return (
            <TableRow key={item.legenda}>
              <TableHead scope="row" className="h-auto p-2 text-left font-normal">
                {rotuloLegenda(item.legenda, legendas)}
                {membros ? (
                  <span className="block text-xs text-muted-foreground">{membros}</span>
                ) : null}
              </TableHead>
              <TableCell className="text-right tabular-nums">
                {formatarInteiro(item.cadeiras)}
              </TableCell>
            </TableRow>
          );
        })}
      </TableBody>
    </Table>
  );
}

export function DetalheUf({
  uf,
  legendas,
}: {
  uf: CasaUfCadeiras;
  legendas: readonly LegendaCadeiras[];
}) {
  const listas = uf.listas.filter((lista) => lista.cadeiras > 0 || lista.quociente_partidario > 0);
  return (
    <details className="rounded-md border border-border px-3 py-2">
      <summary className="cursor-pointer">
        {uf.uf}: {formatarInteiro(uf.vagas)} vagas, quociente eleitoral{" "}
        {formatarInteiro(uf.quociente_eleitoral)}
        {uf.vagas_sem_candidato > 0
          ? `, ${formatarInteiro(uf.vagas_sem_candidato)} sem candidato`
          : ""}
      </summary>
      <div className="mt-3 flex flex-col gap-3">
        <Table containerClassName="folha">
          <TableCaption className="sr-only">Legendas em {uf.uf}</TableCaption>
          <TableHeader>
            <TableRow>
              <TableHead scope="col">Legenda</TableHead>
              <TableHead scope="col" className="text-right">Votos</TableHead>
              <TableHead scope="col" className="text-right">QP</TableHead>
              <TableHead scope="col" className="text-right">Pelo QP</TableHead>
              <TableHead scope="col" className="text-right">Média 80/20</TableHead>
              <TableHead scope="col" className="text-right">Média livre</TableHead>
              <TableHead scope="col" className="text-right">Total</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {listas.map((lista) => (
              <TableRow key={lista.legenda}>
                <TableHead scope="row" className="h-auto p-2 text-left font-normal">
                  {rotuloLegenda(lista.legenda, legendas)}
                </TableHead>
                <TableCell className="text-right tabular-nums">{formatarInteiro(lista.votos)}</TableCell>
                <TableCell className="text-right tabular-nums">{lista.quociente_partidario}</TableCell>
                <TableCell className="text-right tabular-nums">{lista.cadeiras_quociente}</TableCell>
                <TableCell className="text-right tabular-nums">{lista.cadeiras_media}</TableCell>
                <TableCell className="text-right tabular-nums">{lista.cadeiras_media_livre}</TableCell>
                <TableCell className="text-right tabular-nums">{lista.cadeiras}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
        <Table containerClassName="folha">
          <TableCaption className="sr-only">Eleitos estimados em {uf.uf}</TableCaption>
          <TableHeader>
            <TableRow>
              <TableHead scope="col">Número</TableHead>
              <TableHead scope="col">Partido</TableHead>
              <TableHead scope="col" className="text-right">Votos</TableHead>
              <TableHead scope="col">Como entrou</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {uf.eleitos.map((eleito) => (
              <TableRow key={eleito.numero}>
                <TableHead scope="row" className="h-auto p-2 text-left font-normal tabular-nums">
                  {eleito.numero}
                  {eleito.empate ? MARCA_EMPATE : ""}
                </TableHead>
                <TableCell>{rotuloPartido(eleito.partido)}</TableCell>
                <TableCell className="text-right tabular-nums">{formatarInteiro(eleito.votos)}</TableCell>
                <TableCell>{rotuloFase(eleito.fase)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </details>
  );
}

export function TabelaSenado({ senado }: { senado: SenadoCadeiras }) {
  return (
    <Table containerClassName="folha">
      <TableCaption className="sr-only">Senadores estimados por UF</TableCaption>
      <TableHeader>
        <TableRow>
          <TableHead scope="col">UF</TableHead>
          <TableHead scope="col">1ª vaga</TableHead>
          <TableHead scope="col">2ª vaga</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {senado.ufs.map((uf) => (
          <TableRow key={uf.uf}>
            <TableHead scope="row" className="h-auto p-2 text-left font-normal">
              {uf.uf}
              {uf.empate ? MARCA_EMPATE : ""}
            </TableHead>
            <TableCell>{candidato(uf.eleitos[0])}</TableCell>
            <TableCell>{candidato(uf.eleitos[1])}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

export function TabelaGoverno({ governo }: { governo: GovernoCadeiras }) {
  return (
    <Table containerClassName="folha">
      <TableCaption className="sr-only">Governador por UF</TableCaption>
      <TableHeader>
        <TableRow>
          <TableHead scope="col">UF</TableHead>
          <TableHead scope="col">Situação</TableHead>
          <TableHead scope="col">1º colocado</TableHead>
          <TableHead scope="col">2º colocado</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {governo.ufs.map((uf) => (
          <TableRow key={uf.uf}>
            <TableHead scope="row" className="h-auto p-2 text-left font-normal">
              {uf.uf}
              {uf.empate ? MARCA_EMPATE : ""}
            </TableHead>
            <TableCell>{rotuloSituacao(uf.situacao)}</TableCell>
            <TableCell>{candidato(uf.candidatos[0])}</TableCell>
            <TableCell>{candidato(uf.candidatos[1])}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
```

- [ ] **Step 4: Dados** `dados-cadeiras.tsx`:

```tsx
import { ErroRelatorio } from "@/components/relatorios/erro-relatorio";
import { ExplicacaoCadeiras } from "@/components/relatorios/explicacao-cadeiras";
import { GraficoPoder } from "@/components/relatorios/grafico-poder";
import { NotasRelatorio } from "@/components/relatorios/notas-relatorio";
import {
  DetalheUf,
  TabelaGoverno,
  TabelaLegendasCasa,
  TabelaSenado,
} from "@/components/relatorios/tabela-cadeiras";
import { buscarCadeiras } from "@/lib/buscar-relatorios";
import type { Ano, Turno } from "@/lib/eleicoes";
import { formatarInteiro } from "@/lib/fracao";
import {
  MEDIDAS_CADEIRAS,
  frasesCadeiras,
  itensCasa,
  itensSenado,
} from "@/lib/grafico-cadeiras";

type DadosCadeirasProps = {
  ano: Ano;
  turno: Turno;
};

const AVISO =
  "Isto é uma estimativa feita com os boletins de urna, não o resultado oficial do TSE. " +
  "Votos anulados depois da eleição, registros indeferidos e desempates por idade podem mudar cadeiras.";

export async function DadosCadeiras({ ano, turno }: DadosCadeirasProps) {
  const resultado = await buscarCadeiras(ano, turno);
  if (!resultado.ok) {
    return <ErroRelatorio detalhe={resultado.detalhe} />;
  }
  const dados = resultado.dados;
  const gravado = new Date(dados.gerado_em).toLocaleString("pt-BR");
  return (
    <div className="flex flex-col gap-10">
      <p
        role="note"
        className="max-w-3xl rounded-md border border-border bg-muted px-4 py-3 font-medium text-foreground"
      >
        {AVISO}
      </p>
      <section
        aria-labelledby="resumo-cadeiras"
        className="flex max-w-3xl flex-col gap-2 rounded-md border border-border px-4 py-3"
      >
        <h2 id="resumo-cadeiras" className="font-semibold">
          Em resumo
        </h2>
        <ul className="flex list-disc flex-col gap-1 pl-5">
          {frasesCadeiras(dados).map((frase) => (
            <li key={frase}>{frase}</li>
          ))}
        </ul>
      </section>
      <ExplicacaoCadeiras />
      {dados.casas.map((casa) => (
        <section
          key={casa.casa}
          aria-labelledby={`casa-${casa.casa}`}
          className="flex flex-col gap-4"
        >
          <h2 id={`casa-${casa.casa}`} className="text-xl font-semibold">
            {casa.nome}
          </h2>
          <GraficoPoder
            id={`grafico-cadeiras-${casa.casa}`}
            titulo={`Cadeiras estimadas — ${casa.nome}`}
            introducao={`Cadeiras estimadas por partido ou federação, de ${formatarInteiro(casa.vagas_simuladas)} vagas simuladas.`}
            legenda="Cada barra é um partido ou uma federação. Na federação, o detalhe mostra quantas cadeiras ficam com cada partido."
            itens={itensCasa(casa, dados.legendas)}
            medidas={MEDIDAS_CADEIRAS}
          />
          <TabelaLegendasCasa casa={casa} legendas={dados.legendas} />
          <div className="flex flex-col gap-2">
            <h3 className="font-medium">Por UF</h3>
            {casa.ufs.map((uf) => (
              <DetalheUf key={uf.uf} uf={uf} legendas={dados.legendas} />
            ))}
          </div>
        </section>
      ))}
      <section aria-labelledby="casa-senado" className="flex flex-col gap-4">
        <h2 id="casa-senado" className="text-xl font-semibold">
          Senado Federal
        </h2>
        <GraficoPoder
          id="grafico-cadeiras-senado"
          titulo="Senadores estimados por partido"
          introducao={`Senadores estimados por partido, de ${formatarInteiro(dados.senado.vagas_simuladas)} vagas em disputa.`}
          legenda="Duas vagas por UF em 2026. No Senado não há federação na conta: vale o partido do candidato."
          itens={itensSenado(dados)}
        />
        <TabelaSenado senado={dados.senado} />
      </section>
      <section aria-labelledby="casa-governo" className="flex flex-col gap-4">
        <h2 id="casa-governo" className="text-xl font-semibold">
          Governadores
        </h2>
        <TabelaGoverno governo={dados.governo} />
      </section>
      <NotasRelatorio notas={dados.notas} />
      <p className="text-sm text-muted-foreground">
        Votos gravados em {gravado}. * marca resultado que depende de desempate por idade.
      </p>
    </div>
  );
}
```

- [ ] **Step 5: Página** `frontend/src/app/relatorios/cadeiras/page.tsx`:

```tsx
import type { Metadata } from "next";
import { Suspense } from "react";

import { DadosCadeiras } from "@/components/relatorios/dados-cadeiras";
import { EsqueletoDados, EsqueletoFiltros } from "@/components/relatorios/esqueleto-relatorio";
import { FerramentasApresentacao } from "@/components/relatorios/ferramentas-apresentacao";
import { FiltrosCurtos } from "@/components/relatorios/filtros-curtos";
import { consultaPedida, lerAno, lerTurno, type ConsultaRelatorio } from "@/lib/eleicoes";

export const metadata: Metadata = {
  title: "Simulação de cadeiras",
};

export const maxDuration = 600;

const CHAVES_FILTRO = ["ano", "turno"];

export default function CadeirasPage({
  searchParams,
}: {
  searchParams: Promise<ConsultaRelatorio>;
}) {
  return (
    <div className="leitura flex min-h-0 flex-1 flex-col gap-6 overflow-auto p-4 md:p-6">
      <h1 className="leitura-titulo text-3xl">Simulação de cadeiras</h1>
      <FerramentasApresentacao />
      <Suspense fallback={<EsqueletoFiltros chaves={CHAVES_FILTRO} />}>
        <FiltrosComConsulta searchParams={searchParams} />
      </Suspense>
      <Suspense fallback={<EsqueletoDados />}>
        <DadosComConsulta searchParams={searchParams} />
      </Suspense>
    </div>
  );
}

async function FiltrosComConsulta({
  searchParams,
}: {
  searchParams: Promise<ConsultaRelatorio>;
}) {
  const consulta = await searchParams;
  return <FiltrosCurtos ano={lerAno(consulta.ano)} turno={lerTurno(consulta.turno)} />;
}

async function DadosComConsulta({
  searchParams,
}: {
  searchParams: Promise<ConsultaRelatorio>;
}) {
  const consulta = await searchParams;
  if (!consultaPedida(consulta.consultar)) {
    return (
      <p className="text-sm text-muted-foreground">
        Selecione os filtros e clique em Consultar.
      </p>
    );
  }
  return <DadosCadeiras ano={lerAno(consulta.ano)} turno={lerTurno(consulta.turno)} />;
}
```

- [ ] **Step 6:** `cd frontend && pnpm exec tsc --noEmit && pnpm lint && node --experimental-strip-types src/lib/verificar-grafico-cadeiras.ts` → limpo e `ok`.

---

### Task 19: Conferência no navegador (chrome-devtools)

**Prerequisites:** Task 14 (votos gravados) e Task 18. Next na 14000 e API na 15000. Use uma aba própria (`isolatedContext: "cadeiras"`) e salve as capturas `cadeiras-*.png` no scratchpad.

- [ ] Abrir `http://localhost:14000/relatorios/cadeiras?ano=2026&turno=1&consultar=1` e conferir:
  - o aviso de estimativa;
  - o "Em resumo" com a maior bancada de cada Casa e a frase dos governadores;
  - os gráficos da Câmara, das Assembleias e do Senado, com "RENOVAÇÃO SOLIDÁRIA" e "UNIÃO PROGRESSISTA" inteiros;
  - o tooltip de uma federação, que lista os partidos;
  - os `<details>` por UF, que abrem;
  - as tabelas do Senado (27 linhas) e dos governadores (27 linhas).
- [ ] Sem votos gravados, por exemplo `ano=2026&turno=2&consultar=1`, aparece o cartão de erro com o texto "Os votos por candidato de ... Gere com: uv run python scripts/relatorio_cadeiras.py".
- [ ] Tema claro e escuro. Em 375 px aparece a variante estreita do gráfico, sem rolagem horizontal da página. O console fica sem erros novos.
- [ ] O link "Cadeiras" aparece na sidebar e o breadcrumb mostra "Simulação de cadeiras".

---

### Task 20: Validação contra o resultado oficial

**Goal:** medir quanto a estimativa erra e por quê, sem mexer no código de produção. O script fica no scratchpad.

- [ ] **Step 1: Baixar os dados abertos do TSE** para um diretório novo do scratchpad (`$SCRATCH/tse/`). O arquivo de candidaturas de 2026 é `consulta_cand_2026.zip`. Nos anos anteriores ele ficava em `https://cdn.tse.jus.br/estatistica/sead/odsele/consulta_cand/consulta_cand_<ano>.zip`; confirmar o link no Portal de Dados Abertos. Ele traz `SG_UF`, `DS_CARGO`, `NR_CANDIDATO`, `SG_PARTIDO` e `DS_SIT_TOT_TURNO`, com valores como `ELEITO POR QP`, `ELEITO POR MÉDIA`, `SUPLENTE`, `2º TURNO` e `ELEITO`. O CSV usa `;` e latin-1.
- [ ] **Step 2: Script de comparação** `$SCRATCH/conferir_cadeiras.py`. Rodar com `python -I`, passando os caminhos por argumento:

```python
"""Compara a simulação (API) com DS_SIT_TOT_TURNO do TSE. Uso:
python -I conferir_cadeiras.py <consulta_cand_2026_BRASIL.csv> <cadeiras.json> AC AP RR DF SE
"""
import csv
import json
import sys

CARGOS = {"DEPUTADO FEDERAL": "camara", "DEPUTADO ESTADUAL": "assembleias", "DEPUTADO DISTRITAL": "assembleias"}
ELEITO = {"ELEITO POR QP": "quociente", "ELEITO POR MÉDIA": "media"}


def oficiais(path: str, ufs: set[str]) -> dict[tuple[str, str], dict[int, str]]:
    found: dict[tuple[str, str], dict[int, str]] = {}
    with open(path, encoding="latin-1", newline="") as handle:
        for row in csv.DictReader(handle, delimiter=";"):
            casa = CARGOS.get(row["DS_CARGO"].upper())
            fase = ELEITO.get(row["DS_SIT_TOT_TURNO"].upper())
            if casa and fase and row["SG_UF"] in ufs:
                found.setdefault((casa, row["SG_UF"]), {})[int(row["NR_CANDIDATO"])] = fase
    return found


def main() -> None:
    csv_path, json_path, *ufs = sys.argv[1:]
    oficial = oficiais(csv_path, set(ufs))
    with open(json_path, encoding="utf-8") as handle:
        dados = json.load(handle)
    for casa in dados["casas"]:
        for uf in casa["ufs"]:
            if uf["uf"] not in ufs:
                continue
            nosso = {eleito["numero"]: eleito["fase"] for eleito in uf["eleitos"]}
            deles = oficial.get((casa["casa"], uf["uf"]), {})
            so_nosso = sorted(set(nosso) - set(deles))
            so_deles = sorted(set(deles) - set(nosso))
            print(f"{casa['casa']} {uf['uf']}: {len(set(nosso) & set(deles))}/{uf['vagas']} iguais; "
                  f"só na estimativa {so_nosso}; só no oficial {so_deles}")


if __name__ == "__main__":
    main()
```

  Run:
  1. `curl -s "localhost:15000/relatorios/dados/cadeiras?ano=2026&turno=1" > $SCRATCH/cadeiras.json`
  2. `python -I $SCRATCH/conferir_cadeiras.py $SCRATCH/tse/consulta_cand_2026_BRASIL.csv $SCRATCH/cadeiras.json AC AP RR DF SE`

  Expected: uma linha por Casa e UF, como `camara AC: 8/8 iguais; só na estimativa []; só no oficial []`.

- [ ] **Step 3: Governador e Senado em todas as UFs.** Pelo mesmo CSV (`DS_CARGO` GOVERNADOR e SENADOR; `DS_SIT_TOT_TURNO` ELEITO e 2º TURNO), comparar `governo.ufs[].situacao` e os finalistas, e `senado.ufs[].eleitos`. Dica: o AC deu 49,76% na estimativa. Se o oficial disser "ELEITO", a diferença vem dos votos anulados (D7, D16).
- [ ] **Step 4: Registrar o resultado para o usuário**, em texto na resposta e não num arquivo do repositório. Para cada divergência, dar a causa provável: registro indeferido ou sub judice, que muda o QE (D7); boletim faltando (`ufs_sem_votos`); empate marcado (D12); ou federação desatualizada (D5).
- [ ] **Step 5: Casos de borda já cobertos por teste unitário**, sem depender do oficial:
  - UF onde ninguém atinge o QE: `test_no_list_reaching_the_quotient_still_uses_the_averages`;
  - empate de médias: `test_equal_averages_go_to_the_list_with_more_votes` e `test_full_tie_goes_to_the_smaller_code_and_is_flagged`;
  - candidato sem 10%: `test_average_divisor_counts_the_quotient_seat_left_empty` (o 1002 fica abaixo de 10% e a vaga do QP vai para as sobras);
  - lista sem candidato com 20%: `test_list_without_a_twenty_percent_candidate_skips_the_second_phase`;
  - fase 3: `test_third_phase_opens_the_averages_to_every_list`;
  - vaga sem candidato: `test_seats_without_candidates_stay_empty`;
  - QE com fração de meio: `test_quociente_drops_one_half_and_rounds_up_above_it`.

---

### Task 21: Code Review final

1. **REQUIRED SUB-SKILL:** Use jarvis:codereview — dispatch all reviewers in parallel. Escopo: backend (diff do git mais os arquivos novos) e frontend (arquivos ignorados pelo git, listados nas Tasks 16–18).
2. **Proceed only when:** zero Critical/High/Medium issues remain. Depois, rodar de novo `uv run pytest -q && uv run ruff check . && uv run mypy` e `cd frontend && pnpm exec tsc --noEmit && pnpm lint`.
3. Sem commit, a menos que o usuário peça.

---

## Perguntas em aberto para o usuário

- **Q1 — Divisor da média (D10).** O plano segue a Res.-TSE 23.677, art. 11, § 1º: QP + médias + 1, e a vaga de QP perdida pelos 10% conta no divisor. A leitura literal do Código ("lugares por ele obtido") usaria as vagas preenchidas. A Task 20 pode desempatar. Manter a da Resolução?
- **Q2 — Federações.** A tabela de cinco federações (Fe Brasil, PSDB Cidadania, PSOL Rede, Renovação Solidária e União Progressista) e os 30 partidos vêm do TSE e da imprensa, porque o site do TSE recusa leitura automática. Confirma a lista? Prefere dado no código (D5) ou numa tabela editável?
- **Q3 — Votos anulados.** Aceita contar como válidos os votos de candidato indeferido ou sub judice (D7)? A alternativa é importar `consulta_cand_2026` (situação do registro) num plano à parte, o que também daria nome aos candidatos.
- **Q4 — Placar.** A porta segue a "Fase B" do plano 1 sem mudança (D21, conferida em 2026-10-22). O Senado conta só as 54 vagas de 2026. A bancada inteira (81) exigiria os eleitos de 2022, que o banco não tem. Presidente fica fora deste plano. Está bom assim?
- **Q5 — 409 parcial.** Hoje falta de um cargo bloqueia a página inteira (D18). Prefere mostrar o que existir e avisar o que falta?


## Decisões do usuário (2026-10-22)

O usuário aceitou as recomendações da revisão de coerência. Estas decisões valem sobre qualquer pergunta em aberto neste plano.

- **Senado:** só as 54 vagas de 2026.
- **Federações:** a lista das cinco federações (Brasil da Esperança: PT, PCdoB, PV; PSDB Cidadania; PSOL Rede; Renovação Solidária: PRD, Solidariedade; União Progressista: União, PP) fica no código (`domain/federacoes.py`). A Força da marca não agrega os federados.
- **Cadeiras com cargo faltando:** a página de cadeiras responde 409; o placar mostra "—".
- **Divisor das sobras:** regra da Resolução do TSE (quociente partidário + médias já ganhas + 1), conferida com o resultado oficial.
- **Votos de candidato indeferido ou sub judice:** contam como válidos, com aviso na página.
