# Dev Report: ml-reports-2026-10-20

**Completed:** 2026-10-20
**Agents:** backend-engineer-python-oop (T-1 a T-4), frontend-engineer (T-5); revisão com o pool do jarvis:codereview em cada task
**Language:** python, typescript | **Service Type:** domain/library + api + frontend
**Plan:** `docs/superpowers/plans/2026-10-20-ajustes-relatorios-ml.md` (D1–D22)

## Score: 90/100 (Excellent)

| Item | Pontos |
|---|---|
| TDD RED completo (T-1 a T-4; T-5 sem runner de teste no frontend) | 20 |
| TDD GREEN completo | 20 |
| Cobertura 94,15% ≥ 85% | 20 |
| Entrega PASS (5/5 tasks) | 20 |
| Lint: ruff/mypy/tsc limpos, mas `pnpm lint` falha por erro anterior ao ciclo | 0 |
| Tamanho de arquivo (maior: `classe_governador.py`, ~490 linhas) | 5 |
| Cabeçalho de licença: o projeto não usa (N/A) | 5 |

## Metrics

| Metric | Value | Status |
|--------|-------|--------|
| TDD RED | completo no backend; frontend sem runner (tsc + lint + scripts de conferência) | ✅ |
| TDD GREEN | 771 testes passando | ✅ |
| Coverage | 94,15% (threshold: 85%) | ✅ |
| Delivery | 5/5 tasks, 22 decisões | ✅ |
| Lint | ruff ✅ · mypy strict ✅ · tsc ✅ · `pnpm lint` ❌ (1 erro anterior em `filtros-relatorio.tsx:66`) | ⚠️ |
| File Size | 0 violações | ✅ |
| License | N/A | — |

## Delivery Traceability

| Requisito | Status | Evidência |
|-------------|--------|----------|
| D3/D11 perfis sem scaler, silhouette amostrado | DELIVERED | `sklearn_ajuste.py`; teste bimodal falha com scaler |
| D19 teto k ≤ 10 | DELIVERED | `GroupSpan`; `grupos=2-11` → 422 |
| D5/D15 UF no dataset, `sem_uf` | DELIVERED | `municipal_ufs`; 5.571/5.571 códigos casam em 2026/1 |
| D1/D6/D13 deixa-uma-UF-fora | DELIVERED | `cross_val_predict` + `LeaveOneGroupOut`; idêntico ao sklearn em 0/5.571 diferenças |
| D2 duas bases fora da dobra | DELIVERED | maioria 62,61%, líder 51,75% (dados reais) |
| D7 regras da árvore final | DELIVERED | nota no HTML/JSON/frontend |
| D9/D14 recall, F1 macro, acerto por UF | DELIVERED | JSON aditivo, HTML, frontend |
| D21 aviso abaixo da base | DELIVERED | `below_baseline`; aviso no HTML e no frontend |
| D22 cache por chave | DELIVERED | `lru_cache` com chave normalizada; limpa em `atualizar=true` |
| D16/D17/D20 textos e notas | DELIVERED | `NOTAS_CLARAS` batendo 5/5 e 7/7 com o backend |

## Issues Found

- ISSUE-001 (LOW): `pnpm lint` falha em `frontend/src/components/relatorios/filtros-relatorio.tsx:66` (`react-hooks/set-state-in-effect`). O erro é anterior ao ciclo (arquivo de 2026-10-14) e está fora do escopo.
- ISSUE-002 (LOW): `sklearn_ajuste.py` importa `numpy` diretamente. Ele não está declarado no `pyproject.toml` e vem de forma transitiva pelo scikit-learn.
- ISSUE-003 (INFO): o frontend em `frontend/src/lib/` e `frontend/src/components/relatorios/` é ignorado pelo `.gitignore`, então a Task 5 inteira não aparece no git.
- ISSUE-004 (INFO): as regras irmãs da árvore que caem na mesma classe não são fundidas, e por isso há regras redundantes no HTML.

## Achado de domínio

Com validação honesta (deixando uma UF de fora), a árvore acerta 50,48%, abaixo da base da maioria (62,61%) e da regra do líder (51,75%). A divisão 75/25 antiga dava 67,62%: cerca de 17 pontos eram vazamento entre UFs. A classe do governador é quase um dado do estado: a classe mais comum de cada UF acerta 92,6%.

## Improvements for Next Cycle

1. Incluir no plano, desde o início, uma varredura dos textos visíveis ao usuário que descrevem o método. Isso evita achados de "texto agora falso" no Gate 8, que apareceram nas Tasks 3, 4 e 5.
2. Nos testes de adaptadores de ML, escrever dados que distingam previsões fora da dobra de previsões dentro da amostra. Assim um mutante desse tipo é detectado desde o primeiro RED.
3. Decidir sobre um runner de teste no frontend (ex.: vitest) para leitores e lógica pura, hoje conferidos só por scripts descartáveis.
