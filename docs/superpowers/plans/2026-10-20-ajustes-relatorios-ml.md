# Ajustes nos relatórios de ML (perfis e classe do governador)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** O acerto da classe do governador passa a medir generalização para uma UF que o modelo não viu, ao lado de duas linhas de base e de métricas por classe; os perfis municipais deixam de padronizar as fatias e calculam o silhouette por amostra.

**Architecture:** O domínio continua sem arrays. A UF de cada município chega por um novo método do leitor (`municipal_ufs`) e vira campo de `ClassPlace`. O adaptador sklearn faz a validação deixa-uma-UF-fora (`LeaveOneGroupOut`) e devolve só as previsões fora da dobra e as regras da árvore treinada com todos os municípios. O domínio calcula acerto, bases, recall, F1 macro e acerto por UF. O JSON só ganha campos; nenhum campo existente muda de nome ou tipo.

**Tech Stack:** Python 3.11, scikit-learn ≥1.5, Pydantic v2, SQLAlchemy 2, pytest (cobertura ≥85%), mypy strict, ruff, uv. Frontend: Next.js 16.4, TypeScript, sem runner de teste.

**Spec:** Este arquivo é o spec. As decisões vieram da sessão de perguntas e respostas de 2026-10-20 e estão fixadas na seção **Decisões**.

## Decisões

| # | Pergunta | Decisão |
|---|---|---|
| D1 | O que o acerto mede | Generalização para UF nova: deixa-uma-UF-fora |
| D2 | Linhas de base | Duas: maioria e regra do líder presidencial, ambas fora da dobra |
| D3 | Escala dos perfis | Sem `StandardScaler`; fatias como estão |
| D4 | Peso dos perfis | Cada município pesa 1 (sem `sample_weight`) |
| D5 | Fonte da UF | `analise.relatorio_presidente_governador_linha`, cargo `presidente` |
| D6 | Dobras | Uma por UF (`LeaveOneGroupOut`) |
| D7 | Regras exibidas | Árvore final treinada com 100% dos municípios |
| D8 | Cache/persistência | ~~Fora deste plano~~ Substituída pela D22 (cache em memória); persistência em banco segue fora |
| D9 | Métricas | Recall por classe e F1 macro; sem matriz de confusão |
| D10 | `class_weight` | Não muda |
| D11 | Escolha de k | Silhouette amostrado, `sample_size=2000`, `random_state=0` |
| D12 | Frontend | `frontend/` entra; `next-app/` fica fora |
| D13 | Agregação do acerto | Micro: todas as previsões fora da dobra juntas |
| D14 | Acerto por UF | Tabela `{uf, municipios, acerto}` ordenada por UF |
| D15 | UF ausente | Relatório cruzado sem linhas → erro; município sem UF → descartado e contado em `sem_uf` |
| D16 | Rótulo do recall | Frontend: "Reconhecidos"; HTML: "Recall"; JSON: `recall` |
| D17 | F1 macro | Só no JSON e no HTML; o frontend não mostra |
| D18 | Execução | Subagent-driven, com revisor entre tasks |
| D21 | Acerto abaixo das bases (Gate 9 da T-2/T-3) | Publicar com aviso. `ClassReport.below_baseline: bool` (propriedade) = `hit_rate < max(baseline, leader_baseline)`. JSON `abaixo_da_base: bool`. HTML e frontend mostram, quando verdadeiro: `"Num estado que o modelo não viu, as condições não acertam mais que as linhas de base. Elas descrevem esta eleição; não servem para prever outro estado."` A tabela por UF vem antes da tabela de regras. Real 2026/1: 50,48% × 62,61% × 51,75% |
| D22 | Custo por requisição (Gate 9 da T-2/T-3) | `functools.lru_cache(maxsize=32)` em `_stored_profile` e `_stored_class` (`src/eleicoes/adapters/http/dependencies.py`). Erros não ficam em cache (comportamento do `lru_cache`). Regenerar relatórios base exige reiniciar a API para refletir |
| D19 | Teto de k (Gate 9 da T-1) | `GroupSpan` rejeita `upper > 10` com `InvalidGroupSpanError` (HTTP 422) |
| D20 | k=2 nos perfis (Gate 9 da T-1) | Aceito: em 2026/1 presidente o padrão `2-6` passa de 5 para 2 grupos. Task 4 acrescenta a `html_perfis.NOTES`: `"A silhueta é estimada numa amostra de 2000 municípios quando há mais que isso."` e `"Para grupos mais finos, peça um número fixo de grupos, como 5."` |

**Fato verificado (2026-10-20, Postgres do Compose, 2026/1):** `analise.relatorio_presidente_governador_linha` com cargo `presidente` tem 28 UFs (27 + `ZZ`, exterior) e 5.688 códigos. Os 5.571 códigos municipais de `relatorio_poder_linha` (governador, `nivel='municipio'`) casam 100% por `codigo`, e nenhum código aparece em duas UFs. O relatório cruzado grava todas as UFs de uma vez (`collect_places` percorre todos os estados). `ZZ` não entra na classe porque não tem governador.

## Global Constraints

- Interface, rótulos, mensagens de erro e notas em português. Identificadores, docstrings e mensagem de commit em inglês, como no código atual.
- `random_state=0` e `threadpool_limits(limits=1)` em todo ajuste sklearn. `max_depth=3` e `min_samples_leaf=20` não mudam.
- O domínio (`src/eleicoes/domain/`) não importa sklearn, numpy nem threadpoolctl.
- JSON aditivo: `acerto`, `base`, `linhas[].classe|rotulo|apoio|regras`, `retidas`, `notas`, e todo o `ProfileJson` mantêm nome e tipo.
- `uv run pytest` passa com `--cov-fail-under=85`; `uv run mypy` e `uv run ruff check src tests` limpos.
- `cd frontend && pnpm exec tsc --noEmit` e `cd frontend && pnpm lint` limpos. Na raiz, `pnpm exec tsc` falha com `ERR_PNPM_NO_PKG_MANIFEST`.
- `.gitignore` ignora qualquer diretório `relatorios/` e `lib/`. Não editar o `.gitignore`. Mudanças em `frontend/src/lib/` e `frontend/src/components/relatorios/` não aparecem em `git diff`.
- O passo de commit fica escrito, mas só roda se o usuário pedir. Trailer: `--trailer "X-Jarvis-Ref: 0x1"`. Não incluir `.env`, `downloads/`, `logs/`, `relatorios/`, `next-app/`.
- Não chamar a API com `atualizar=true`. Não derrubar o Compose.

## Review Focus

- **UF com um só município (DF):** a dobra de tamanho 1 roda e conta 1 em `por_uf`. Teste na Task 3.
- **Classe que só existe na UF deixada de fora:** a árvore daquela dobra não a conhece; recall dessa classe pode ser 0, sem exceção. Teste na Task 3.
- **Mesmo `codigo` em duas UFs no relatório cruzado:** `InconsistentCellError`. Teste na Task 2.
- **Relatório cruzado existe, mas nenhum código bate:** todos viram `sem_uf`, sobram <3 municípios → `FewMunicipalitiesError`. Teste na Task 2.
- **Amostra ≤ 2000 municípios:** o silhouette é exato, sem `sample_size`. Teste na Task 1.

---

### Task 1: Perfis sem padronização e com silhouette amostrado

**Files:**
- Modify: `src/eleicoes/adapters/sklearn_ajuste.py` (`_kmeans`, `_scored`, `_once`, `_silhouette`, imports)
- Test: `tests/adapters/test_sklearn_ajuste.py`

**Interfaces:**
- Consumes: nada novo.
- Produces: `SklearnProfileClusterer.fit` com a mesma assinatura; `_SILHOUETTE_SAMPLE: Final = 2000`; `_silhouette(rows: list[list[float]], labels: tuple[int, ...]) -> float`.

- [ ] **Step 1: Write the failing tests**

```python
def test_tiny_bimodal_feature_does_not_drive_the_split() -> None:
    offsets = (-0.16, -0.08, 0.0, 0.08, 0.16)
    rows = tuple(
        (base + offsets[i % 5], 0.001 * (i % 2))
        for base, start in ((0.1, 0), (0.9, 10))
        for i in range(start, start + 10)
    )
    fit = SklearnProfileClusterer().fit(rows, GroupSpan(2, 2, False))
    assert len(set(fit.assignments[:10])) == 1
    assert len(set(fit.assignments[10:])) == 1
    assert fit.assignments[0] != fit.assignments[10]


def test_large_sample_scores_on_a_seeded_subsample(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, object] = {}

    def spy(_x: object, _labels: object, **kwargs: object) -> float:
        seen.update(kwargs)
        return 0.5

    monkeypatch.setattr("eleicoes.adapters.sklearn_ajuste.silhouette_score", spy)
    rows = [[float(i % 2), float(i % 3)] for i in range(2001)]
    assert _silhouette(rows, tuple(i % 2 for i in range(2001))) == 0.5
    assert seen == {"sample_size": 2000, "random_state": 0}


def test_small_sample_scores_exactly(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, object] = {}

    def spy(_x: object, _labels: object, **kwargs: object) -> float:
        seen.update(kwargs)
        return 0.5

    monkeypatch.setattr("eleicoes.adapters.sklearn_ajuste.silhouette_score", spy)
    rows = [[float(i % 2)] for i in range(2000)]
    _silhouette(rows, tuple(i % 2 for i in range(2000)))
    assert seen == {}
```

`test_range_separates_two_blobs_and_centers_stay_near_the_means` continua valendo sem mudança: os centros agora vêm direto de `model.cluster_centers_`.

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/adapters/test_sklearn_ajuste.py -v`
Expected: FAIL em `test_tiny_bimodal_feature_does_not_drive_the_split` (com o scaler, o KMeans corta pela segunda coluna) e em `test_large_sample_scores_on_a_seeded_subsample` (`seen == {}`).

- [ ] **Step 3: Implement**

`_kmeans(rows, k) -> tuple[tuple[int, ...], tuple[tuple[float, ...], ...]]`: `KMeans(n_clusters=k, n_init=_N_INIT, random_state=_RANDOM_STATE).fit(rows)`; centros = `_rows(model.cluster_centers_)`. Retirar `StandardScaler` e o terceiro elemento do retorno. `_scored` passa `rows` para `_silhouette`. `_silhouette` chama `silhouette_score(rows, list(labels), sample_size=_SILHOUETTE_SAMPLE, random_state=_RANDOM_STATE)` só quando `len(rows) > _SILHOUETTE_SAMPLE`; caso contrário, sem kwargs. Mantém o `ValueError → UnusableGroupCountError` e o NaN → `-1.0`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/adapters/test_sklearn_ajuste.py tests/use_cases/test_apresentar_perfis.py tests/adapters/test_relatorios_agrupamentos.py -v`
Expected: PASS

- [ ] **Step 5: Commit (só se o usuário pedir)**

```bash
git add src/eleicoes/adapters/sklearn_ajuste.py tests/adapters/test_sklearn_ajuste.py
git commit -m "fix: cluster raw shares and sample the silhouette" --trailer "X-Jarvis-Ref: 0x1"
```

---

### Task 2: A UF chega ao dataset da classe

**Files:**
- Modify: `src/eleicoes/domain/classe_governador.py` (`ClassPlace`, `ClassDataset`, `class_places`, `prepare_class_dataset`, `_labeled`, `_separate`)
- Modify: `src/eleicoes/domain/errors.py` (dois erros novos)
- Modify: `src/eleicoes/ports/classe_governador.py` (`ClassSource.municipal_ufs`)
- Modify: `src/eleicoes/adapters/postgres_perfis.py` (`municipal_ufs`, `uf_statement`)
- Modify: `src/eleicoes/use_cases/apresentar_classe_governador.py` (`build_governor_class` passa as UFs)
- Modify fakes: `tests/use_cases/test_apresentar_classe_governador.py`, `tests/adapters/test_relatorios_agrupamentos.py`
- Test: `tests/domain/test_classe_governador.py`, `tests/adapters/test_postgres_perfis.py`

**Interfaces:**
- Consumes: `read_cargo(tally).leader.partido` de `domain/presidente_governador.py`.
- Produces:
  - `ClassPlace(codigo, nome, comparecimento, label, votes, uf: str, leader: int)`, com `uf` e `leader` no fim.
  - `ClassDataset(parties, places, held_out, without_uf: int)` + `groups() -> tuple[str, ...]` (UF de cada lugar, na ordem de `places`).
  - `prepare_class_dataset(lines: tuple[ClassLine, ...], ufs: tuple[tuple[str, str], ...]) -> ClassDataset`, onde `ufs` são pares `(codigo, uf)`.
  - `ClassSource.municipal_ufs(self, ano: int, turno: int) -> tuple[tuple[str, str], ...]`.
  - `MissingCrossReportError(ElectionError)`: `"Gere o relatório presidente × governador antes."`
  - `FewStatesError(ElectionError)`: `"Menos de 2 UFs para validar."`

- [ ] **Step 1: Write the failing tests** (em `tests/domain/test_classe_governador.py`, adaptando `_pair`/`_block` para devolver também os pares `(codigo, uf)`)

```python
def test_place_carries_its_uf_and_presidential_leader() -> None:
    dataset = prepare_class_dataset(_three_classes(), _ufs("SP", "MG"))
    assert {place.uf for place in dataset.places} == {"SP", "MG"}
    assert dataset.groups() == tuple(place.uf for place in dataset.places)
    assert all(place.leader in dataset.parties for place in dataset.places)


def test_place_without_uf_is_dropped_and_counted() -> None:
    lines = _three_classes() + _pair("99", "Órfã", 13, 4)
    dataset = prepare_class_dataset(lines, _ufs("SP", "MG"))
    assert "99" not in {place.codigo for place in dataset.places}
    assert dataset.without_uf == 1


def test_empty_uf_map_asks_for_the_cross_report() -> None:
    with pytest.raises(MissingCrossReportError, match="Gere o relatório presidente × governador antes."):
        prepare_class_dataset(_three_classes(), ())


def test_code_under_two_ufs_is_inconsistent() -> None:
    with pytest.raises(InconsistentCellError):
        prepare_class_dataset(_three_classes(), (("1", "SP"), ("1", "MG")))


def test_no_code_matches_leaves_too_few_places() -> None:
    with pytest.raises(FewMunicipalitiesError):
        prepare_class_dataset(_three_classes(), (("zzz", "SP"),))


def test_single_state_cannot_be_validated() -> None:
    with pytest.raises(FewStatesError, match="Menos de 2 UFs para validar."):
        prepare_class_dataset(_three_classes(), _ufs("SP"))
```

`_three_classes()` monta ao menos 2 municípios em cada uma de 2 classes; `_ufs(*names)` distribui os códigos dessas linhas entre as UFs em rodízio. Os testes existentes de `prepare_class_dataset` passam a enviar `_ufs("SP", "MG")`. `class_places(lines, ufs)` também muda de aridade: `test_missing_governor_line_is_not_a_place`, `test_comparecimento_and_governor_votes_stay_out_of_the_vector` e os demais testes que chamam `class_places` passam a enviar os pares dos seus códigos.

Em `tests/adapters/test_postgres_perfis.py`:

```python
def test_municipal_ufs_reads_president_lines_once_per_code() -> None:
    # sessão falsa no mesmo estilo de test_load_*: devolve [("1", "SP"), ("2", "MG")]
    assert reader.municipal_ufs(2026, 1) == (("1", "SP"), ("2", "MG"))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/domain/test_classe_governador.py tests/adapters/test_postgres_perfis.py -v`
Expected: FAIL com `TypeError` (aridade de `prepare_class_dataset`) e `ImportError` dos erros novos.

- [ ] **Step 3: Implement**

- `class_places(lines, ufs)`: monta o mapa `codigo → uf` (código repetido com UF diferente → `InconsistentCellError`; o mesmo par repetido é aceito). Lugar sem UF não entra e incrementa o contador. `_labeled` grava `leader = read_cargo(president_tally).leader.partido`.
- `prepare_class_dataset`: `ufs == ()` → `MissingCrossReportError` antes de tudo. Depois de `_separate`, menos de 2 UFs distintas entre os lugares mantidos → `FewStatesError`. `without_uf` vai para `ClassDataset`.
- `uf_statement(ano, turno)`: `select(PresidentGovernorLine.codigo, PresidentGovernorLine.uf).where(ano, turno, cargo == "presidente").distinct().order_by(codigo, uf)`. `municipal_ufs` usa `_guard`, como `class_lines`.
- `build_governor_class`: `prepare_class_dataset(reader.class_lines(ano, turno), reader.municipal_ufs(ano, turno))`. O resto da função não muda nesta task.
- Fakes de `ClassSource` nos testes ganham `municipal_ufs` devolvendo pares para os códigos que já usam.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest -q`
Expected: PASS, cobertura ≥85%.

- [ ] **Step 5: Commit (só se o usuário pedir)**

```bash
git add src/eleicoes/domain/classe_governador.py src/eleicoes/domain/errors.py src/eleicoes/ports/classe_governador.py src/eleicoes/adapters/postgres_perfis.py src/eleicoes/use_cases/apresentar_classe_governador.py tests/
git commit -m "feat: attach the state to each governor-class place" --trailer "X-Jarvis-Ref: 0x1"
```

---

### Task 3: Validação deixa-uma-UF-fora e métricas no domínio

**Files:**
- Modify: `src/eleicoes/ports/classe_governador.py` (`ClassFit`, `GovernorClassModel.fit`)
- Modify: `src/eleicoes/adapters/sklearn_ajuste.py` (`SklearnGovernorTree`, `_tree`; remover `_TEST_SIZE`, `_unpack` e `train_test_split`)
- Modify: `src/eleicoes/domain/classe_governador.py` (`ClassOutcome`, `ClassReport`, `UfScore`, `class_report`)
- Modify: `src/eleicoes/use_cases/apresentar_classe_governador.py`
- Modify: construções de `ClassOutcome`/`ClassReport`/`ClassFit` em `tests/adapters/test_html_classe_governador.py`, `tests/adapters/test_relatorios_agrupamentos.py`, `tests/use_cases/test_apresentar_classe_governador.py`
- Test: `tests/domain/test_classe_governador.py`, `tests/adapters/test_sklearn_ajuste.py`

**Interfaces:**
- Consumes: `ClassDataset.groups()`, `ClassPlace.uf`, `ClassPlace.leader`, `majority_label` (Task 2 e código atual).
- Produces:
  - `ClassFit(predicted: tuple[str, ...], rules: tuple[ClassRule, ...])`: `predicted` alinhado com as linhas da matriz; cada rótulo em `CLASS_ORDER`; não vazio.
  - `GovernorClassModel.fit(self, matrix, labels, parties, groups: tuple[str, ...]) -> ClassFit`.
  - `ClassOutcome(classe, support, rules, recall: Fraction)`: `support` passa a ser o total de municípios da classe.
  - `UfScore(uf: str, municipios: int, hit_rate: Fraction)`.
  - `ClassReport(ano, turno, parties, hit_rate, baseline, rows, held_out, leader_baseline: Fraction, macro_f1: Fraction, by_uf: tuple[UfScore, ...], without_uf: int)`.
  - `class_report(ano: int, turno: int, dataset: ClassDataset, predicted: tuple[str, ...], rules: tuple[ClassRule, ...]) -> ClassReport`.

- [ ] **Step 1: Write the failing tests**

Domínio: `_hand_dataset(df_leader: int = 22) -> ClassDataset` monta à mão `ClassDataset(parties=(13, 22, 44), places, held_out=(), without_uf=0)` com 6 `ClassPlace`, nesta ordem (uf, rótulo, líder): `AC consolidacao 13`, `AC consolidacao 13`, `BA consolidacao 13`, `BA em_aberto 22`, `BA em_aberto 22`, `DF em_aberto df_leader`. Os votos de cada lugar dão ao líder a maior fatia. `_all(label, n)` devolve `(label,) * n`.

```python
def test_report_scores_out_of_fold_predictions() -> None:
    dataset = _hand_dataset()          # labels: AC(c,c) BA(c,a,a) DF(a); leaders: 13,13,13,22,22,22
    predicted = ("consolidacao", "em_aberto", "consolidacao", "em_aberto", "em_aberto", "em_aberto")
    report = class_report(2026, 1, dataset, predicted, ())
    assert report.hit_rate == Fraction(5, 6)
    assert [(s.uf, s.municipios, s.hit_rate) for s in report.by_uf] == [
        ("AC", 2, Fraction(1, 2)), ("BA", 3, Fraction(1)), ("DF", 1, Fraction(1)),
    ]
    assert {row.classe: row.recall for row in report.rows} == {
        "consolidacao": Fraction(2, 3), "em_aberto": Fraction(1),
    }
    assert report.macro_f1 == Fraction(1, 2) * (Fraction(4, 5) + Fraction(6, 7))


def test_majority_baseline_is_learned_without_the_held_out_state() -> None:
    report = class_report(2026, 1, _hand_dataset(), _all("em_aberto", 6), ())
    # sem AC: c=1, a=3 → a; sem BA: c=2, a=1 → c; sem DF: c=3, a=2 → c
    assert report.baseline == Fraction(0 + 1 + 0, 6)


def test_leader_baseline_maps_each_leader_to_its_training_majority() -> None:
    report = class_report(2026, 1, _hand_dataset(), _all("em_aberto", 6), ())
    # sem AC: 13→c (BA), 22→a; sem BA: 13→c, 22→a; sem DF: 13→c, 22→a
    assert report.leader_baseline == Fraction(6, 6)


def test_unseen_leader_falls_back_to_the_training_majority() -> None:
    dataset = _hand_dataset(df_leader=44)  # 44 só existe em DF; 22 passa a existir só na BA
    report = class_report(2026, 1, dataset, _all("em_aberto", 6), ())
    # sem AC: 13→c → AC 2/2
    # sem BA: 22 não está no treino → maioria do treino c (2 × 1) → BA 1/3
    # sem DF: 44 não está no treino → maioria do treino c (3 × 2) → DF 0/1
    assert report.leader_baseline == Fraction(3, 6)


def test_misaligned_prediction_is_inconsistent() -> None:
    with pytest.raises(InconsistentCellError):
        class_report(2026, 1, _hand_dataset(), ("consolidacao",), ())
```

Adaptador (substitui `test_tree_rules_are_portuguese_cuts_on_the_held_out_quarter` e `test_unstratifiable_sample_is_a_class_error`; em `test_bad_silhouette_and_unreadable_arrays`, retirar o import e a asserção de `_unpack`, que deixa de existir):

```python
def test_tree_predicts_every_row_out_of_its_state() -> None:
    rows, labels = _separable()                    # 80 linhas, dois rótulos separáveis por 13
    groups = tuple(("SP", "MG", "RJ", "DF")[i % 4] for i in range(len(rows)))
    fit = SklearnGovernorTree().fit(tuple(rows), tuple(labels), (13,), groups)
    assert len(fit.predicted) == len(rows)
    assert {cut.party for rule in fit.rules for cut in rule.cuts} == {13}
    assert all(len(rule.cuts) <= 3 for rule in fit.rules)


def test_class_only_in_the_held_out_state_is_not_an_error() -> None:
    rows = [[0.1]] * 20 + [[0.9]] * 20 + [[0.5]] * 2
    labels = ("consolidacao",) * 20 + ("em_aberto",) * 20 + ("sem_governador",) * 2
    groups = ("SP",) * 20 + ("MG",) * 20 + ("DF",) * 2
    fit = SklearnGovernorTree().fit(tuple(map(tuple, rows)), labels, (13,), groups)
    assert "sem_governador" not in fit.predicted[-2:]


def test_one_state_is_a_class_error() -> None:
    with pytest.raises(FewClassesError):
        SklearnGovernorTree().fit(((0.0,), (1.0,)), ("consolidacao", "em_aberto"), (13,), ("SP", "SP"))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/domain/test_classe_governador.py tests/adapters/test_sklearn_ajuste.py -v`
Expected: FAIL (assinaturas novas inexistentes).

- [ ] **Step 3: Implement**

- Adaptador: `LeaveOneGroupOut().split(rows, labels, groups)`; para cada dobra, `DecisionTreeClassifier(max_depth=_MAX_DEPTH, min_samples_leaf=_MIN_LEAF, random_state=_RANDOM_STATE)` treina e prevê a UF de fora, gravando na posição original. Depois, uma árvore com todas as linhas gera `rules` via `_rules`. Tudo dentro de um `threadpool_limits(limits=1)`. Menos de 2 grupos distintos → `FewClassesError` (o domínio já barra antes com `FewStatesError`; aqui é só defesa da porta).
- Domínio, `class_report`: valida `len(predicted) == len(dataset.places)` e todos os rótulos em `CLASS_ORDER`, senão `InconsistentCellError`. Para cada UF `u`, treino = lugares com `uf != u`:
  - base da maioria: `majority_label(rótulos do treino)`;
  - base do líder: para cada líder do treino, `majority_label` dos rótulos dele; líder ausente → maioria do treino.
  - Recall da classe `c` = acertos em `c` / apoio de `c`. Precisão = acertos em `c` / previsões `c` (0 se nenhuma). F1 = `2PR/(P+R)` (0 se `P+R == 0`). `macro_f1` = média simples sobre `_present(dataset.places)`.
  - `by_uf` ordenado por `uf`.
- Use case: `fit = model.fit(dataset.matrix(), dataset.labels(), dataset.parties, dataset.groups())`; `class_report(ano, turno, dataset, fit.predicted, fit.rules)`.
- `majority_label` não sai de `domain/classe_governador.py`; o adaptador deixa de importá-lo.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest -q && uv run mypy && uv run ruff check src tests`
Expected: PASS e zero erros.

- [ ] **Step 5: Commit (só se o usuário pedir)**

```bash
git add src/eleicoes tests
git commit -m "feat: validate the governor class by leaving one state out" --trailer "X-Jarvis-Ref: 0x1"
```

---

### Task 4: JSON, HTML e notas

**Files:**
- Modify: `src/eleicoes/adapters/http/schemas_relatorios.py` (`LinhaClasseJson`, `ClassJson`, novo `AcertoUfJson`)
- Modify: `src/eleicoes/adapters/html_classe_governador.py` (`NOTES`, `_rates`, `_table`, `_row`, nova `_states`)
- Modify: `src/eleicoes/adapters/html_perfis.py` (`NOTES`: as duas notas da D20)
- Modify: `src/eleicoes/use_cases/apresentar_classe_governador.py` (`_message` do CLI: `"Acerto em UF não vista: {hit}. Linha de base da maioria: {base}. Linha de base do líder presidencial: {lider}."`; atualizar o teste que fixa `"Acerto no teste: 100,00%"`)
- Modify: `README.md:299` (descrever a validação deixa-uma-UF-fora e as duas bases, no lugar do "quarto dos municípios")
- Modify: `src/eleicoes/domain/classe_governador.py` (`ClassReport.below_baseline`, D21)
- Modify: `src/eleicoes/adapters/http/dependencies.py` (`lru_cache` em `_stored_profile` e `_stored_class`, D22; teste: duas chamadas com a mesma chave constroem uma vez, chaves diferentes constroem de novo, e um erro não fica em cache)
- Test obrigatório (alerta de qualidade de dados da T-2): `sem_uf > 0` aparece no JSON e na frase do HTML
- Test: `tests/adapters/test_html_classe_governador.py`, `tests/adapters/test_relatorios_agrupamentos.py`

**Interfaces:**
- Consumes: `ClassReport` e `ClassOutcome` da Task 3.
- Produces (JSON, aditivo):
  - `LinhaClasseJson.recall: str` (`format_percent`)
  - `ClassJson.base_lider: str`, `ClassJson.f1_macro: str` (`format_decimal(float(report.macro_f1))`, 4 casas, como o silhouette), `ClassJson.por_uf: list[AcertoUfJson]`, `ClassJson.sem_uf: int`
  - `AcertoUfJson(uf: str, municipios: int, acerto: str)`

- [ ] **Step 1: Write the failing tests**

```python
def test_json_adds_state_scores_and_both_baselines() -> None:
    body = ClassJson.from_domain(_report()).model_dump()
    assert {"acerto", "base", "linhas", "retidas", "notas"} <= body.keys()
    assert body["base_lider"] == "100,00%"
    assert body["por_uf"][0] == {"uf": "AC", "municipios": 2, "acerto": "50,00%"}
    assert body["linhas"][0]["recall"] == "66,67%"
    assert body["sem_uf"] == 0


def test_page_explains_the_state_validation_and_lists_each_state() -> None:
    page = html_classe_governador(_report())
    assert "Acerto em UF não vista" in page
    assert "Linha de base do líder presidencial" in page
    assert "F1 macro" in page
    assert '<th class="num" scope="col" aria-sort="none">Recall</th>' in page
    assert '<td class="lugar" data-ord="AC">AC</td>' in page
```

`_report()` = `class_report(2026, 1, _hand_dataset(), ("consolidacao", "em_aberto", "consolidacao", "em_aberto", "em_aberto", "em_aberto"), ())`, a mesma entrada de `test_report_scores_out_of_fold_predictions` (Task 3); por isso AC = 50,00%, recall de consolidacao = 66,67% e `base_lider` = 100,00%. Literais conferidos: `format_percent(Fraction(1, 2)) == "50,00%"`, `format_percent(Fraction(2, 3)) == "66,67%"`, `format_decimal(0.5) == "0,5000"`.

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/adapters/test_html_classe_governador.py tests/adapters/test_relatorios_agrupamentos.py -v`
Expected: FAIL (`KeyError: 'base_lider'`, texto ausente).

- [ ] **Step 3: Implement**

`NOTES` (texto exato; a primeira nota substitui a do quarto de teste):

```python
NOTES = (
    "O acerto vem de deixar cada UF de fora e prever seus municípios com a árvore das outras.",
    "As regras mostradas são da árvore ajustada com todos os municípios.",
    "Isto não é uma previsão do segundo turno.",
    "As fatias são só do presidente, sobre os votos válidos.",
    "O governador entra apenas na classe, não nas contas da árvore.",
)
```

`_rates`: `Acerto em UF não vista: <strong>{hit}</strong>. Linha de base da maioria: <strong>{base}</strong>. Linha de base do líder presidencial: <strong>{lider}</strong>. F1 macro: <strong>{f1}</strong>.` Se `without_uf > 0`, um `<p>` com `"{n} municípios ficaram de fora por não terem UF no relatório cruzado."`. Coluna `Municípios no teste` vira `Municípios`; nova coluna `Recall` entre ela e `Regras`. `_states` gera uma segunda tabela (`UF`, `Municípios`, `Acerto`) com as mesmas classes CSS de `_table`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest -q`
Expected: PASS

- [ ] **Step 5: Commit (só se o usuário pedir)**

```bash
git add src/eleicoes/adapters/http/schemas_relatorios.py src/eleicoes/adapters/html_classe_governador.py tests/adapters
git commit -m "feat: report state validation, baselines and recall" --trailer "X-Jarvis-Ref: 0x1"
```

---

### Task 5: Frontend da classe do governador

**Files (ignorados pelo git, ver Global Constraints):**
- Modify: `frontend/src/lib/relatorios.ts` (`LinhaClasseGovernador`, `RelatorioClasseGovernador`, `lerClasseGovernador`, `lerLinhaClasse`, novo `AcertoUf` + `lerAcertoUf`)
- Modify: `frontend/src/components/relatorios/dados-classe-governador.tsx`
- Modify: `frontend/src/components/relatorios/tabela-classe-governador.tsx` (coluna Recall)

**Interfaces:**
- Consumes: JSON da Task 4.
- Produces: `AcertoUf = { uf: string; municipios: number; acerto: string }`; `LinhaClasseGovernador.recall: string`; `RelatorioClasseGovernador` ganha `base_lider: string`, `f1_macro: string`, `por_uf: AcertoUf[]`, `sem_uf: number`. Leitura com `exigirTexto`/`exigirInteiro`/`exigirLista`, como os campos atuais.

- [ ] **Step 1: Atualizar tipos e leitores** em `relatorios.ts`.

- [ ] **Step 2: Atualizar o texto da página.** Trocar o parágrafo "As condições foram montadas em três quartos dos municípios..." por: "Para medir, cada UF ficou de fora uma vez: as condições foram montadas com as outras UFs e testadas nos municípios dela." A frase do achado passa a ser: "Em UF não vista, a leitura acertou {acerto}. Marcar a situação mais comum das outras UFs chegaria a {base}; seguir só o partido líder de presidente nas outras UFs chegaria a {base_lider}." Remover o trecho "com {apoio} de {total} municípios ({base})": `base` não é mais `apoio/total`. `classeComum` pode continuar nomeando a situação mais comum ("A situação mais comum foi {rótulo}, com {apoio} de {total} municípios."), sem percentual. Se `sem_uf > 0`: "{n} municípios ficaram de fora por não terem UF." Em `NOTAS_CLARAS`, trocar a chave da nota antiga pela primeira nota nova → "Cada UF foi prova uma vez, sem ensinar a árvore que a testou." e a segunda → "As condições da tabela usam todos os municípios."

- [ ] **Step 2a: Notas dos perfis (D20).** Em `frontend/src/components/relatorios/dados-perfis.tsx`, acrescentar a `NOTAS_CLARAS` as duas notas novas da D20 com texto claro: "Quando há mais de 2000 municípios, a separação dos grupos é medida numa amostra de 2000." e "Para ver grupos menores, escolha um número fixo de grupos no filtro."

- [ ] **Step 2b: Aviso (D21).** Ler `abaixo_da_base: boolean` em `relatorios.ts`; quando verdadeiro, mostrar o texto da D21 em destaque logo após a frase do achado. A tabela por UF vem antes da tabela de condições.

- [ ] **Step 2c: Textos corrigidos no Gate 8 da T-5.** (a) "Na tabela, cada percentual…" → "Na tabela de condições, os percentuais das condições são a parte daquele partido nos votos válidos de presidente."; (b) frase visível acima da tabela de condições e `title` do cabeçalho: "Reconhecidos é a parte dos municípios de cada situação que a leitura acertou quando a UF deles ficou de fora."; (c) a nota clara de "Isto não é uma previsão do segundo turno." passa a "A leitura descreve este turno; não é uma previsão."; (d) a tabela por UF fica ANTES da tabela de condições (D21 prevalece sobre o "abaixo" do Step 3).

- [ ] **Step 3a: Renomear a coluna "Municípios da prova"** (`tabela-classe-governador.tsx:23`) para "Municípios": `apoio` agora é a classe inteira.

- [ ] **Step 3: Tabela por UF e coluna Reconhecidos.** Coluna `Reconhecidos` em `TabelaClasseGovernador`, com `title="Parte dos municípios desta situação que a leitura apontou certo."` no cabeçalho, mostrando `linha.recall`. `f1_macro` é lido e tipado, mas não aparece na página (D17). Abaixo dela, uma tabela simples `UF · Municípios · Acerto` com `formatarInteiro`, no mesmo estilo de tabela do componente.

- [ ] **Step 4: Verificar**

Run: `cd frontend && pnpm exec tsc --noEmit && pnpm lint`
Expected: zero erros. Se a porta 14000 já responder, abrir `/relatorios/classe-governador` e conferir que as frases novas, a coluna Reconhecidos e a tabela por UF aparecem, e que "F1" não aparece (sem `atualizar=true`).

- [ ] **Step 5: Sem commit.** Os arquivos estão em diretórios ignorados.

---

## Fora deste plano

- Persistir perfis e classe no banco (D8; o cache em memória entrou pela D22).
- `class_weight="balanced"` (D10), matriz de confusão (D9), estabilidade por ARI (D11).
- `next-app/` (D12).
- Peso por eleitor nos perfis (D4).
