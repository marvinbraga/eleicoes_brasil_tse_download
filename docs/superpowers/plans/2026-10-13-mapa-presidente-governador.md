# Mapa de presidente e governador — plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Gerar um HTML estático, aberto do disco, que pinta o partido líder de presidente ou de governador no país, na UF e no município.

**Architecture:** O Python reaproveita `view_from_places` e o líder já escolhido em `CargoReading.leader.partido`. Ele cruza o código do TSE com `municipio_tse_ibge.csv`, resolve cor e logomarca num arquivo local e grava essas quatro propriedades no JSON do HTML. A geometria permanece TopoJSON. A função `aplicar`, no navegador, copia cor, número, logomarca e código na feição antes de `topojson.feature`. Esse é um desvio nomeado: a especificação pedia as propriedades já na feição antes de o navegador abrir. Não há decodificador de arcos em Python. O relatório não baixa nada. Um script à parte grava a malha medida em `downloads/malha/`.

**Tech Stack:** Python 3.11+ do projeto (uv, ruff, mypy strict, pytest), OpenLayers 10.11.0, topojson-client 3.1.0, TopoJSON do IBGE e `countries-110m.json` do world-atlas 2.0.2. Sem dependência nova.

**Spec:** `docs/bibliotecas-de-mapas.md`

## Verificação adversarial

A primeira afirmação, "o plano pode ser executado como está e produz o mapa da especificação", foi **recusada** em 13 de outubro de 2026. Os três leitores devolveram REFUTED. A seção Decisões fecha essa recusa.

A afirmação revisada, "o plano já com as decisões pode ser executado e produz o mapa aceito", passou no limiar de maioria: correção UPHELD, fidelidade à especificação UPHELD, reprodutibilidade REFUTED. Os defeitos da minoria eram divergências de cópia entre teste e bloco de implementação. Foram escritos neste plano depois dessa leitura: zoom do país com `None`, nome `municipio_tse_ibge.zip`, `exigir_centroide_municipal`, as frases de licença, o doctype, `ol_css` dentro de `<style>`, `csv_tamanho`, os nomes `foo` e `BRUF` na especificação, e a frase de que os textos do teste são entradas que o HTML ecoa. Não há dúvida de produto em aberto.

A leitura de correção, contra o domínio que já existe, obrigou estes ajustes. Não são escolha de produto:

- `collect_places` grava o município como `str(int)`. Bujari chega `"1007"` e o CSV traz `"01007"`. A busca completa com zeros à esquerda até 5 caracteres. `"10070"` não vira `"01007"`. O teste que exigia `BridgeMissingError` para `"1007"` foi trocado.
- O nome municipal já vem como `Bujari (AC)`. O buraco usa `place.nome`. Não se acrescenta a sigla de novo. O nome da UF continua `uf_name`, então o exterior segue `Exterior (ZZ)`.
- `collect` do comando é um adaptador `(ano, turno)`. `collect_places` real recebe `(reader, names, ano, turno)`, o mesmo desenho de `_collect_for` no relatório cruzado.
- `--sem-navegador` segue `_choose_opener`: um `open_report` injetado ganha; sem injeção, a flag pula o navegador.
- Toda frase de erro vai para `sys.stderr`.
- `MalhaCarregada` tem o campo `manifesto`. `codigos_no_objeto` não usa `Any`.
- O CSV de teste inclui o byte latin-1 de `ã`. Arquivo de logomarca ausente é `MeshMissingError`, não marca inválida.
- A camada do país não recebe `minZoom`.

Medido em 13 de outubro de 2026, no corpo descomprimido (`requests.get(...).content`, não o `Content-Length` do gzip):

| Arquivo | Bytes medidos | Fato conferido |
| --- | --- | --- |
| `ol.js` 10.11.0 | 1.070.771 | começa com `var ol=` |
| `ol.css` 10.11.0 | 6.343 | |
| `topojson-client.min.js` 3.1.0 | 7.169 | publica o global `topojson` |
| Malha municipal v2 | 1.626.114 | um objeto, chamado `foo`; 5.570 geometrias; `centroide` é par numérico |
| Malha de UFs v3 | 31.464 | um objeto, chamado `BRUF`; 27 `codarea`; sem centróide |
| `countries-110m.json` | 107.761 | objetos `countries` (177) e `land` (1); o Brasil é o `id` `"076"`, nome `Brazil`; Fiji é `"242"` |
| Zip TSE–IBGE | 139.031 | trava aceita pelo dono; o CSV interno tem 520.088 bytes; carimbo `11/10/2026` `09:00:16` |

O `id` `"76"` não existe nesse arquivo. `nome_do_objeto` vale só para a malha de um único objeto (municípios e UFs). Em países, a chave usada é `countries`. O objeto `land` não é desenhado e não passa por `nome_do_objeto`.

## Decisões

Respondidas pelo dono em 13 de outubro de 2026. Não há dúvida de produto em aberto.

- O download aceita o zip de 139.031 bytes somente se o CSV interno tiver 520.088 bytes. Qualquer um dos dois fora da medida encerra com código 1 e `A malha baixada não confere com a especificação.` A especificação registra a mesma trava.
- Arquivo local ausente, ponte sem o município e marca ausente saem com código 1 e a frase específica de cada caso. O código 2 deste projeto continua significando nada publicado ou nada importado. Este comando não o usa.
- País e UF mostram cor e número do partido. Não mostram logomarca, porque a malha não traz `centroide`. O Python e o JavaScript não calculam esse ponto. A logomarca entra só no município, quando `centroide` é um par numérico. Desvio nomeado em relação a "logomarca em todo recorte".
- A geometria fica em TopoJSON. `aplicar` copia as quatro propriedades no navegador. Desvio nomeado. O topojson-client permanece na página.
- Este plano desenha país, UF e município. A página avisa que a região ficou de fora. A malha de região não é inventada.

Fechado pela regra já escrita, sem pergunta:

- A vista permanece `EPSG:4326`, norte para cima, sem `fromLonLat` e sem `EPSG:3857`. `fromLonLat` desenha em Web Mercator, e a regra permanente proíbe Mercator e Albers.
- O texto de cada área é `str(RankedParty.partido)`. O total de votos não entra no polígono.
- A camada do país não recebe `minZoom`. `maxZoom` é 4, mesmo com `minZoom` nulo. Um `minZoom` de 0 é exclusivo e esconderia o país no zoom 0.

## Fora deste plano

A malha das cinco regiões não tem URL, tamanho nem nome de objeto medidos. A especificação manda não inventar esse arquivo. O dono confirmou, em 13 de outubro de 2026, que este plano desenha país, UF e município e que a página avisa a ausência. Um plano seguinte só começa depois que a URL, o tamanho, a contagem e o nome do objeto entrarem na especificação.

Também ficam de fora: rota FastAPI, Leaflet, MapLibre, `RenderFeature`, geojson-vt, shapefile, `countries-50m.json`, Matplotlib, GeoPandas, Shapely e pandas.

## Global Constraints

- OpenLayers 10.11.0, `dist/ol.js` com 1.070.771 bytes, começando com `var ol=`. CSS em `https://unpkg.com/ol@10.11.0/ol.css`, 6.343 bytes. topojson-client 3.1.0, `dist/topojson-client.min.js`, 7.169 bytes, global `topojson`.
- Municípios: `https://servicodados.ibge.gov.br/api/v2/malhas/BR?resolucao=5&qualidade=1&formato=application/json`, 1.626.114 bytes. UFs: `https://servicodados.ibge.gov.br/api/v3/malhas/paises/BR?intrarregiao=UF&qualidade=minima&formato=application/json`, 31.464 bytes. Países: `https://cdn.jsdelivr.net/npm/world-atlas@2.0.2/countries-110m.json`, 107.761 bytes, objeto `countries`.
- Ponte: `https://cdn.tse.jus.br/estatistica/sead/odsele/municipio_tse_ibge/municipio_tse_ibge.zip`, 139.031 bytes. O CSV interno tem 520.088 bytes, latin-1, separador `;`. A chave do CSV guarda os zeros do arquivo e não é completada nem cortada. A especificação proíbe completar o código de 7 dígitos para compará-lo ao de 5, e proíbe perder o zero ao ler o CSV. Nenhuma das duas acontece. O `zfill(5)` só reconstrói o código TSE que `collect_places` gravou com `str(int)`.
- A vista é `EPSG:4326`, norte para cima. O projeto não desenha este mapa em Mercator nem em Albers. O plano não chama `fromLonLat` e não usa `EPSG:3857`.
- `minZoom` e `maxZoom` vão no construtor da camada. País: sem `minZoom`, `maxZoom` 4. UF: 4 e 6. Município: 6 e 28. A opção trata `minZoom` como exclusivo e `maxZoom` como inclusivo. A camada do mundo não recebe limiar.
- `declutter: false`. O número usa `overflow: true`. A logomarca só entra quando o `centroide` da malha é um par de números. País e UF não têm esse par, então ficam com cor e número. O Python não calcula centróide.
- Cor, número, logomarca e código são resolvidos no Python e gravados no JSON. `aplicar` os copia na feição TopoJSON. O número é `str(RankedParty.partido)`. A cor não é escala. Há uma data URI por partido, escrita uma vez.
- ZZ, Boa Esperança do Norte (IBGE `5101837`) e as regiões não ganham polígono inventado. A UF é pintada por `CD_UF_IBGE`, achado pela sigla. `CD_UF_TSE` não pinta.
- O relatório sai com código 1, em português, quando falta arquivo local, quando a ponte não tem o município e quando falta a marca. A frase diz qual é o caso. Código 1 também cobre falha de conteúdo ou de argumento, com a frase genérica. Este comando não usa o código 2. Ele não baixa a malha.
- Identificadores e testes em inglês. Texto de CLI, README e HTML em português. Commits em inglês, com `--trailer "X-Jarvis-Ref: 0x1"`. Sem Facade. ruff: linha 100, mccabe ≤ 10. mypy strict. A suíte inteira é `uv run pytest`. O ciclo vermelho/verde de um arquivo usa `--override-ini='addopts='`.
- Não editar `html_grade.py` nem `html_presidente_governador.py`. Não gravar malha, CSV, `ol.js` nem logomarca no git. `downloads/` e `relatorios/` já estão no `.gitignore`.

## Review Focus

- O CSV guarda `01007`. O domínio manda `1007`. A busca faz `zfill(5)` só quando o código é numérico e tem menos de 5 caracteres. `10070` não casa com `01007`. O teste está na Task 1.
- São Paulo se pinta com `35`, a partir da sigla `SP`. O `CD_UF_TSE` `1` não pode virar `codarea`. O teste está na Task 1.
- Boa Esperança do Norte, a UF `ZZ` e as siglas `NO`, `NE`, `CO`, `SE` e `S` saem sem polígono. O teste está na Task 1 e a ausência de camada de região está na Task 4.
- Só a feição cujo `id` é o `brasil_id` do manifesto recebe cor. O `id` `242` (Fiji) permanece fundo. O teste está na Task 4.
- Partido líder sem cor ou sem logomarca encerra com código 1 e não gera HTML. `declutter` permanece `false`. Os testes estão na Task 1, na Task 2 e na Task 5.

## File structure

- Create `src/eleicoes/domain/mapa.py`: ponte, pintura e os erros do mapa.
- Create `src/eleicoes/ports/malha.py`: `MeshAssets`.
- Create `src/eleicoes/adapters/malha_local.py`: lê `downloads/malha/` e monta a data URI.
- Create `src/eleicoes/adapters/html_mapa.py`: o HTML.
- Create `src/eleicoes/use_cases/baixar_malha.py`: baixa só as URLs medidas.
- Create `src/eleicoes/use_cases/apresentar_mapa.py`: CLI.
- Create `scripts/baixar_malha.py` e `scripts/relatorio_mapa.py`.
- Create `tests/domain/test_mapa.py`, `tests/adapters/test_malha_local.py`, `tests/adapters/test_html_mapa.py`, `tests/use_cases/test_baixar_malha.py`, `tests/use_cases/test_apresentar_mapa.py`.
- Modify `README.md`: uma seção do comando, depois de "Cruzar presidente e governador".
- `downloads/malha/` é saída do script de download e dos arquivos que o operador coloca. Não é código.

---

### Task 1: Cruzar o líder com a malha

**Files:**

- Create: `src/eleicoes/domain/mapa.py`
- Test: `tests/domain/test_mapa.py`

**Interfaces:**

- Consumes: `CrossReportView`, `view_from_places`, `MunicipalPlace`, `CargoTally`, `PartyTally` em `src/eleicoes/domain/presidente_governador.py`. `PlaceReading.codigo` municipal é o código TSE. O grupo em `view.municipalities` é a sigla da UF. O estado usa a sigla em `codigo`. O país usa `codigo == "BR"`. O líder é `CargoReading.leader.partido`.
- Produces:
  - `class Marca`: `cor: str`, `logo: str`
  - `class Pintura`: `codigo: str`, `cor: str`, `numero: str`, `logo: str`
  - `class PonteTseIbge`: `municipio_por_tse: Mapping[str, str]`, `uf_por_sigla: Mapping[str, str]`
  - `class RecortePintado`: `pais: Pintura | None`, `ufs: tuple[Pintura, ...]`, `municipios: tuple[Pintura, ...]`, `sem_poligono: tuple[str, ...]`
  - `ponte_de_linhas(linhas: Sequence[Mapping[str, str]]) -> PonteTseIbge`
  - `recorte_pintado(view, cargo, ponte, marcas, codigos_municipio, codigos_uf, brasil_id) -> RecortePintado`
  - `InvalidPonteError`, `InvalidCargoError`, `BridgeMissingError`, `MarkMissingError`, subclasses de `ElectionError`. `BridgeMissingError.ausentes: tuple[tuple[str, str], ...]` é `(uf, codigo_tse)`. `MarkMissingError.partidos: tuple[int, ...]`.

- [ ] **Step 1: Write the failing test**

Create `tests/domain/test_mapa.py` with this content:

```python
from eleicoes.domain.mapa import (
    BridgeMissingError,
    InvalidCargoError,
    InvalidPonteError,
    Marca,
    MarkMissingError,
    ponte_de_linhas,
    recorte_pintado,
)
from eleicoes.domain.presidente_governador import (
    CargoTally,
    MunicipalPlace,
    PartyTally,
    view_from_places,
)

_HEADER = (
    "DT_GERACAO",
    "HH_GERACAO",
    "CD_UF_TSE",
    "CD_UF_IBGE",
    "SG_UF",
    "NM_UF",
    "CD_MUNICIPIO_TSE",
    "NM_MUNICIPIO_TSE",
    "CD_MUNICIPIO_IBGE",
    "NM_MUNICIPIO_IBGE",
)


def _row(tse_uf: str, ibge_uf: str, sigla: str, tse: str, nome: str, ibge: str) -> dict[str, str]:
    values = ("04/10/2026", "09:00:06", tse_uf, ibge_uf, sigla, nome, tse, nome, ibge, nome)
    return dict(zip(_HEADER, values, strict=True))


def _ponte() -> object:
    return ponte_de_linhas(
        (
            _row("1", "12", "AC", "01007", "Bujari", "1200138"),
            _row("1", "35", "SP", "71072", "São Paulo", "3550308"),
            _row("20", "53", "DF", "97012", "Brasília", "5300108"),
            _row("11", "51", "MT", "73709", "Boa Esperança do Norte", "5101837"),
        ),
    )


def _tally(partido: int) -> CargoTally:
    return CargoTally((PartyTally(partido, 10, 0),), 0, 0)


def _place(uf: str, codigo: str, nome: str, presidente: int, governador: int | None) -> MunicipalPlace:
    governor = None if governador is None else _tally(governador)
    return MunicipalPlace(uf, codigo, nome, _tally(presidente), governor)


def test_bujari_keeps_the_leading_zero_and_sp_uses_the_ibge_uf() -> None:
    ponte = _ponte()
    assert ponte.municipio_por_tse["01007"] == "1200138"
    assert ponte.municipio_por_tse["71072"] == "3550308"
    assert ponte.uf_por_sigla["SP"] == "35"
    assert ponte.uf_por_sigla["DF"] == "53"
    assert "1" not in ponte.uf_por_sigla.values()


def test_domain_code_joins_the_zero_padded_bridge() -> None:
    ponte = _ponte()
    view = view_from_places(2026, 1, (_place("AC", "1007", "Bujari (AC)", 22, 22),))
    painted = recorte_pintado(
        view, "presidente", ponte, {22: Marca("#112233", "data:x")}, frozenset({"1200138"}), frozenset({"12"}), "076",
    )
    assert painted.municipios[0].codigo == "1200138"


def test_five_digit_code_is_not_padded_into_another_city() -> None:
    ponte = _ponte()
    view = view_from_places(2026, 1, (_place("AC", "10070", "Outra", 22, 22),))
    try:
        recorte_pintado(view, "presidente", ponte, {22: Marca("#112233", "data:x")}, frozenset({"1200138"}), frozenset({"12"}), "076")
    except BridgeMissingError as error:
        assert error.ausentes == (("AC", "10070"),)
    else:
        raise AssertionError("expected BridgeMissingError")


def test_duplicate_tse_code_rejects_the_bridge() -> None:
    row = _row("1", "12", "AC", "01007", "Bujari", "1200138")
    try:
        ponte_de_linhas((row, row))
    except InvalidPonteError:
        return
    raise AssertionError("expected InvalidPonteError")


def test_paint_uses_the_leader_number_and_lists_holes() -> None:
    ponte = _ponte()
    places = (
        _place("AC", "01007", "Bujari (AC)", 22, 13),
        _place("MT", "73709", "Boa Esperança do Norte (MT)", 22, 22),
        _place("ZZ", "99001", "Lisboa (ZZ)", 22, None),
    )
    view = view_from_places(2026, 1, places)
    marcas = {22: Marca("#112233", "data:image/png;base64,QQ=="), 13: Marca("#AABBCC", "data:image/png;base64,Ug==")}
    painted = recorte_pintado(
        view,
        "presidente",
        ponte,
        marcas,
        frozenset({"1200138", "3550308"}),
        frozenset({"12", "35", "51", "53"}),
        "076",
    )
    assert painted.pais is not None
    assert painted.pais.codigo == "076"
    assert painted.pais.numero == "22"
    assert painted.pais.logo == "data:image/png;base64,QQ=="
    assert [item.codigo for item in painted.municipios] == ["1200138"]
    assert [item.codigo for item in painted.ufs] == ["12", "51"]
    assert "Boa Esperança do Norte (MT)" in painted.sem_poligono
    assert "Boa Esperança do Norte (MT) (MT)" not in painted.sem_poligono
    assert "Lisboa (ZZ)" in painted.sem_poligono
    assert "Exterior (ZZ)" in painted.sem_poligono
    assert all(item.codigo not in {"NO", "NE", "CO", "SE", "S"} for item in painted.ufs)


def test_governor_map_uses_the_governor_leader() -> None:
    ponte = _ponte()
    view = view_from_places(2026, 1, (_place("AC", "01007", "Bujari", 22, 13),))
    marcas = {22: Marca("#112233", "data:a"), 13: Marca("#AABBCC", "data:b")}
    painted = recorte_pintado(view, "governador", ponte, marcas, frozenset({"1200138"}), frozenset({"12"}), "076")
    assert painted.municipios[0].numero == "13"
    assert painted.municipios[0].cor == "#AABBCC"


def test_missing_mark_names_every_leader() -> None:
    ponte = _ponte()
    view = view_from_places(2026, 1, (_place("AC", "01007", "Bujari", 22, 22),))
    try:
        recorte_pintado(view, "presidente", ponte, {}, frozenset({"1200138"}), frozenset({"12"}), "076")
    except MarkMissingError as error:
        assert error.partidos == (22,)
    else:
        raise AssertionError("expected MarkMissingError")


def test_unknown_cargo_is_rejected() -> None:
    ponte = _ponte()
    view = view_from_places(2026, 1, (_place("AC", "01007", "Bujari", 22, 22),))
    try:
        recorte_pintado(view, "senador", ponte, {}, frozenset(), frozenset(), "076")
    except InvalidCargoError:
        return
    raise AssertionError("expected InvalidCargoError")
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/domain/test_mapa.py --override-ini='addopts=' -q`

Expected: FAIL with `ModuleNotFoundError` or `ImportError` for `eleicoes.domain.mapa`.

- [ ] **Step 3: Write the minimal implementation**

Create `src/eleicoes/domain/mapa.py`:

```python
"""Join of a cross-report leader to mesh codes. No file and no geometry."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Final

from eleicoes.domain.errors import ElectionError
from eleicoes.domain.presidente_governador import CargoReading, CrossReportView, PlaceReading

_COLUMNS: Final = (
    "DT_GERACAO",
    "HH_GERACAO",
    "CD_UF_TSE",
    "CD_UF_IBGE",
    "SG_UF",
    "NM_UF",
    "CD_MUNICIPIO_TSE",
    "NM_MUNICIPIO_TSE",
    "CD_MUNICIPIO_IBGE",
    "NM_MUNICIPIO_IBGE",
)
_CARGOS: Final = frozenset({"presidente", "governador"})
_EXTERIOR: Final = "ZZ"


class InvalidPonteError(ElectionError):
    def __init__(self) -> None:
        super().__init__("invalid TSE-IBGE bridge")


class InvalidCargoError(ElectionError):
    def __init__(self, value: object) -> None:
        self.value = value
        super().__init__(f"invalid cargo: {value}")


class BridgeMissingError(ElectionError):
    def __init__(self, ausentes: tuple[tuple[str, str], ...]) -> None:
        self.ausentes = ausentes
        super().__init__(f"missing IBGE code: {ausentes}")


class MarkMissingError(ElectionError):
    def __init__(self, partidos: tuple[int, ...]) -> None:
        self.partidos = partidos
        super().__init__(f"missing party mark: {partidos}")


@dataclass(frozen=True, slots=True)
class Marca:
    cor: str
    logo: str


@dataclass(frozen=True, slots=True)
class Pintura:
    codigo: str
    cor: str
    numero: str
    logo: str


@dataclass(frozen=True, slots=True)
class PonteTseIbge:
    municipio_por_tse: Mapping[str, str]
    uf_por_sigla: Mapping[str, str]


@dataclass(frozen=True, slots=True)
class RecortePintado:
    pais: Pintura | None
    ufs: tuple[Pintura, ...]
    municipios: tuple[Pintura, ...]
    sem_poligono: tuple[str, ...]


def ponte_de_linhas(linhas: Sequence[Mapping[str, str]]) -> PonteTseIbge:
    municipios: dict[str, str] = {}
    ufs: dict[str, str] = {}
    ibges: set[str] = set()
    for linha in linhas:
        if tuple(linha) != _COLUMNS:
            raise InvalidPonteError
        tse = linha["CD_MUNICIPIO_TSE"]
        ibge = linha["CD_MUNICIPIO_IBGE"]
        sigla = linha["SG_UF"]
        uf_ibge = linha["CD_UF_IBGE"]
        if len(tse) != 5 or len(ibge) != 7 or len(uf_ibge) != 2 or sigla == _EXTERIOR:
            raise InvalidPonteError
        if tse in municipios or ibge in ibges:
            raise InvalidPonteError
        municipios[tse] = ibge
        ibges.add(ibge)
        anterior = ufs.setdefault(sigla, uf_ibge)
        if anterior != uf_ibge:
            raise InvalidPonteError
    return PonteTseIbge(municipios, ufs)


def recorte_pintado(
    view: CrossReportView,
    cargo: str,
    ponte: PonteTseIbge,
    marcas: Mapping[int, Marca],
    codigos_municipio: frozenset[str],
    codigos_uf: frozenset[str],
    brasil_id: str,
) -> RecortePintado:
    if cargo not in _CARGOS:
        raise InvalidCargoError(cargo)
    faltando = _marcas_faltando(view, cargo, marcas)
    if faltando:
        raise MarkMissingError(faltando)
    ausentes = _sem_ponte(view, ponte)
    if ausentes:
        raise BridgeMissingError(ausentes)
    municipios, buracos = _municipios(view, cargo, ponte, marcas, codigos_municipio)
    ufs, buracos_uf = _ufs(view, cargo, ponte, marcas, codigos_uf)
    return RecortePintado(
        _pais(view, cargo, marcas, brasil_id),
        ufs,
        municipios,
        tuple(sorted(buracos + buracos_uf)),
    )


def _marcas_faltando(view: CrossReportView, cargo: str, marcas: Mapping[int, Marca]) -> tuple[int, ...]:
    found: set[int] = set()
    for reading in _leituras(view):
        leader = _lider(reading, cargo)
        if leader is not None and leader not in marcas:
            found.add(leader)
    return tuple(sorted(found))


def _chave_tse(codigo: str) -> str:
    if codigo.isdigit() and len(codigo) < 5:
        return codigo.zfill(5)
    return codigo


def _sem_ponte(view: CrossReportView, ponte: PonteTseIbge) -> tuple[tuple[str, str], ...]:
    found: list[tuple[str, str]] = []
    for uf, places in view.municipalities:
        if uf == _EXTERIOR:
            continue
        for place in places:
            if _chave_tse(place.codigo) not in ponte.municipio_por_tse:
                found.append((uf, place.codigo))
    return tuple(found)


def _municipios(
    view: CrossReportView,
    cargo: str,
    ponte: PonteTseIbge,
    marcas: Mapping[int, Marca],
    codigos: frozenset[str],
) -> tuple[tuple[Pintura, ...], tuple[str, ...]]:
    painted: list[Pintura] = []
    holes: list[str] = []
    for uf, places in view.municipalities:
        for place in places:
            if _lider(place, cargo) is None:
                continue
            if uf == _EXTERIOR:
                holes.append(place.nome)
                continue
            ibge = ponte.municipio_por_tse[_chave_tse(place.codigo)]
            if ibge not in codigos:
                holes.append(place.nome)
                continue
            painted.append(_pintura(ibge, place, cargo, marcas))
    return tuple(painted), tuple(holes)


def _ufs(
    view: CrossReportView,
    cargo: str,
    ponte: PonteTseIbge,
    marcas: Mapping[int, Marca],
    codigos: frozenset[str],
) -> tuple[tuple[Pintura, ...], tuple[str, ...]]:
    painted: list[Pintura] = []
    holes: list[str] = []
    for state in view.states:
        if _lider(state, cargo) is None:
            continue
        ibge = ponte.uf_por_sigla.get(state.codigo)
        if state.codigo == _EXTERIOR or ibge is None or ibge not in codigos:
            holes.append(f"{state.nome} ({state.codigo})")
            continue
        painted.append(_pintura(ibge, state, cargo, marcas))
    return tuple(painted), tuple(holes)


def _pais(view: CrossReportView, cargo: str, marcas: Mapping[int, Marca], brasil_id: str) -> Pintura | None:
    country = view.country
    if country is None or _lider(country, cargo) is None:
        return None
    return _pintura(brasil_id, country, cargo, marcas)


def _pintura(codigo: str, place: PlaceReading, cargo: str, marcas: Mapping[int, Marca]) -> Pintura:
    leader = _lider(place, cargo)
    if leader is None:
        raise MarkMissingError(())
    marca = marcas[leader]
    return Pintura(codigo, marca.cor, str(leader), marca.logo)


def _leituras(view: CrossReportView) -> tuple[PlaceReading, ...]:
    cities = tuple(place for _, places in view.municipalities for place in places)
    country = () if view.country is None else (view.country,)
    return cities + view.states + country


def _lider(place: PlaceReading, cargo: str) -> int | None:
    reading: CargoReading | None = place.presidente if cargo == "presidente" else place.governador
    if reading is None or reading.leader is None:
        return None
    return reading.leader.partido
```

`uf_name("ZZ")` já devolve `Exterior`. Não reimplementar o ranking: o líder vem pronto.

- [ ] **Step 4: Run the test to verify it passes**

Run: `uv run pytest tests/domain/test_mapa.py --override-ini='addopts=' -q`

Expected: PASS, 7 tests.

- [ ] **Step 5: Commit**

```bash
uv run ruff check src/eleicoes/domain/mapa.py tests/domain/test_mapa.py
uv run ruff format --check src/eleicoes/domain/mapa.py tests/domain/test_mapa.py
uv run mypy --strict -p eleicoes
uv run pytest
git add src/eleicoes/domain/mapa.py tests/domain/test_mapa.py
git commit -m "feat: join election leaders to mesh codes" --trailer "X-Jarvis-Ref: 0x1"
```

---

### Task 2: Ler a malha local

**Files:**

- Create: `src/eleicoes/ports/malha.py`
- Create: `src/eleicoes/adapters/malha_local.py`
- Test: `tests/adapters/test_malha_local.py`

**Interfaces:**

- Consumes: `PonteTseIbge`, `Marca`, `ponte_de_linhas`, `MeshMissingError` added in this task to `src/eleicoes/domain/mapa.py`.
- Produces:
  - `class Manifesto`: `municipios_objeto: str`, `ufs_objeto: str`, `paises_objeto: str`, `brasil_id: str`
  - `class MalhaCarregada`: `manifesto: Manifesto`, plus `municipios: str`, `ufs: str`, `paises: str`, `ol_js: str`, `ol_css: str`, `topojson_js: str`, `ponte: PonteTseIbge`, `marcas: Mapping[int, Marca]`, `codigos_municipio: frozenset[str]`, `codigos_uf: frozenset[str]`, `ids_pais: frozenset[str]`
  - `class MeshAssets(Protocol)`: `load(self) -> MalhaCarregada`
  - `class LocalMeshAssets`: `__init__(self, raiz: Path) -> None`, `load(self) -> MalhaCarregada`
  - `MeshMissingError.nome: str` is the path under `downloads/malha/`.
  - `MarkInvalidError` for a logo that is neither PNG nor SVG, or a color that is not `#` plus six hex digits.

- [ ] **Step 1: Write the failing test**

Create `tests/adapters/test_malha_local.py`. Use `tmp_path`. A one-pixel PNG payload is the base64 `iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==`.

The fixture writes:

- `manifesto.json` with `municipios_objeto=malha`, `ufs_objeto=ufs`, `paises_objeto=countries`, `brasil_id=076`
- `municipios.json`: Topology, object `malha`, one geometry, `codarea` `1200138`, `centroide` `[-67.8, -9.8]`
- `ufs.json`: object `ufs`, `codarea` `12`
- `paises.json`: object `countries`, geometry `id` `076` and another `id` `242`, neither with `codarea`
- `vendor/ol.js` text `var ol=1;`
- `vendor/ol.css` text `.ol {}`
- `vendor/topojson-client.min.js` text `var topojson=1;`
- `municipio_tse_ibge.csv` in latin-1, semicolon-separated, with the header from Task 1, the Bujari row, and a São Paulo row whose `NM_MUNICIPIO_TSE` contains `ã` (byte `0xE3`). That byte is not valid UTF-8. The test fails if the loader opens the CSV as UTF-8.
- `marcas.json`: `{"22": {"cor": "#112233", "arquivo": "22.png"}}`
- `logomarcas/22.png`: the PNG bytes above

Tests:

```python
def test_load_reads_codes_logos_and_country_ids(tmp_path: Path) -> None:
    _write_fixture(tmp_path)
    loaded = LocalMeshAssets(tmp_path).load()
    assert loaded.codigos_municipio == frozenset({"1200138"})
    assert loaded.codigos_uf == frozenset({"12"})
    assert loaded.ids_pais == frozenset({"076", "242"})
    assert loaded.ponte.municipio_por_tse["01007"] == "1200138"
    assert loaded.ponte.municipio_por_tse["71072"] == "3550308"
    assert b"\xe3" in (tmp_path / "municipio_tse_ibge.csv").read_bytes()
    assert loaded.marcas[22].cor == "#112233"
    assert loaded.marcas[22].logo.startswith("data:image/png;base64,iVBORw0KGgo")
    assert loaded.ol_js == "var ol=1;"
    assert loaded.manifesto.brasil_id == "076"


def test_missing_mesh_names_the_file(tmp_path: Path) -> None:
    with pytest.raises(MeshMissingError) as error:
        LocalMeshAssets(tmp_path).load()
    assert error.value.nome == "downloads/malha/manifesto.json"


def test_svg_logo_uses_an_svg_data_uri(tmp_path: Path) -> None:
    _write_fixture(tmp_path, png=b"<svg xmlns='http://www.w3.org/2000/svg'/>")
    loaded = LocalMeshAssets(tmp_path).load()
    assert loaded.marcas[22].logo.startswith("data:image/svg+xml;base64,")


def test_text_logo_is_rejected(tmp_path: Path) -> None:
    _write_fixture(tmp_path, png=b"not-an-image")
    with pytest.raises(MarkInvalidError):
        LocalMeshAssets(tmp_path).load()
```

`_write_fixture` takes `tmp_path` and an optional `png` override. The CSV keeps the quoted form `"01007"` so the loader proves it does not drop the zero.

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/adapters/test_malha_local.py --override-ini='addopts=' -q`

Expected: FAIL with `ImportError`.

- [ ] **Step 3: Write the minimal implementation**

Add to `src/eleicoes/domain/mapa.py`:

```python
class MeshMissingError(ElectionError):
    def __init__(self, nome: str) -> None:
        self.nome = nome
        super().__init__(f"missing mesh: {nome}")


class MarkInvalidError(ElectionError):
    def __init__(self, partido: int) -> None:
        self.partido = partido
        super().__init__(f"invalid party mark: {partido}")
```

`src/eleicoes/ports/malha.py` holds `Manifesto`, `MalhaCarregada` and `MeshAssets`. `Manifesto` and `MalhaCarregada` are frozen dataclasses. The port imports them from nowhere else; later tasks import these names from `eleicoes.ports.malha`.

`LocalMeshAssets.load` reads, in this order, and raises `MeshMissingError(f"downloads/malha/{relative}")` when a path is not a file: `manifesto.json`, `municipios.json`, `ufs.json`, `paises.json`, `vendor/ol.js`, `vendor/ol.css`, `vendor/topojson-client.min.js`, `municipio_tse_ibge.csv`, `marcas.json`. Logo files are checked after `marcas.json` is parsed.

`codigos_no_objeto(topology: Mapping[str, object], objeto: str, campo: str) -> frozenset[str]` reads the geometries of `objeto`. Do not annotate `Any`: `disallow_any_explicit` is on. Narrow each `object` with `isinstance` before indexing, `len`, or iteration. For `campo == "codarea"` read `properties["codarea"]`. For `campo == "id"` read `geometry["id"]`. Values become `str`. A missing CSV column raises `InvalidPonteError`. A missing topology object raises `MeshMismatchError(ElectionError)` with `nome: str`. It does not raise `MarkInvalidError`.

CSV: `path.read_text(encoding="latin-1")`, `csv.DictReader(..., delimiter=";")`. Pass the dicts to `ponte_de_linhas`.

`marcas.json` is a JSON object. Each key is `int` in `0..99`. `cor` matches `^#[0-9A-Fa-F]{6}$`. `arquivo` is a basename: reject empty, `/`, `\\` and `..`. A named logo file that is not on disk raises `MeshMissingError` with `nome` `downloads/malha/logomarcas/{arquivo}`. Bytes starting with `b"\x89PNG"` become `data:image/png;base64,{standard_b64encode}`. Bytes starting with `b"<svg"` or `b"<?xml"` become `data:image/svg+xml;base64,...`. Anything else raises `MarkInvalidError`. A missing file is not `MarkInvalidError`. Add `test_missing_logo_names_the_file`: `marcas.json` points at `22.png` and the file is absent.

- [ ] **Step 4: Run the test to verify it passes**

Run: `uv run pytest tests/adapters/test_malha_local.py tests/domain/test_mapa.py --override-ini='addopts=' -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
uv run ruff check src/eleicoes/domain/mapa.py src/eleicoes/ports/malha.py src/eleicoes/adapters/malha_local.py tests/adapters/test_malha_local.py
uv run ruff format --check src/eleicoes/domain/mapa.py src/eleicoes/ports/malha.py src/eleicoes/adapters/malha_local.py tests/adapters/test_malha_local.py
uv run mypy --strict -p eleicoes
uv run pytest
git add src/eleicoes/domain/mapa.py src/eleicoes/ports/malha.py src/eleicoes/adapters/malha_local.py tests/adapters/test_malha_local.py
git commit -m "feat: load local mesh, bridge, and party marks" --trailer "X-Jarvis-Ref: 0x1"
```

---

### Task 3: Baixar as malhas medidas

**Files:**

- Create: `src/eleicoes/use_cases/baixar_malha.py`
- Create: `scripts/baixar_malha.py`
- Test: `tests/use_cases/test_baixar_malha.py`

**Interfaces:**

- Consumes: `Manifesto` from `eleicoes.ports.malha`. `Fetch = Callable[[str], bytes]`.
- Produces: `baixar_malha(destino: Path, fetch: Fetch) -> Manifesto`. The script `main(argv: Sequence[str] | None = None) -> int` calls `requests.get(url, timeout=120).content` and prints Portuguese. Exit 0 on success. Exit 1 when the size, the prefix, the object name, the Brazil id, or the municipal centroid shape is wrong. The script does not fetch logos or colors.

Measured table, copied from the spec. A body is accepted only at that size:

| Nome | URL | Bytes | Checagem extra |
| --- | --- | --- | --- |
| `vendor/ol.js` | `https://unpkg.com/ol@10.11.0/dist/ol.js` | 1070771 | começa com `var ol=` |
| `vendor/ol.css` | `https://unpkg.com/ol@10.11.0/ol.css` | 6343 | |
| `vendor/topojson-client.min.js` | `https://unpkg.com/topojson-client@3.1.0/dist/topojson-client.min.js` | 7169 | contém `topojson` |
| `municipios.json` | `https://servicodados.ibge.gov.br/api/v2/malhas/BR?resolucao=5&qualidade=1&formato=application/json` | 1626114 | um único objeto; centróide de algum município é par numérico |
| `ufs.json` | `https://servicodados.ibge.gov.br/api/v3/malhas/paises/BR?intrarregiao=UF&qualidade=minima&formato=application/json` | 31464 | um único objeto |
| `paises.json` | `https://cdn.jsdelivr.net/npm/world-atlas@2.0.2/countries-110m.json` | 107761 | objeto `countries`; o `id` do Brasil é a string `"076"` |
| `municipio_tse_ibge.zip` | `https://cdn.tse.jus.br/estatistica/sead/odsele/municipio_tse_ibge/municipio_tse_ibge.zip` | 139031 | um `.csv` interno de 520088 bytes, gravado como `municipio_tse_ibge.csv` |

URLs que este use case não chama: malha municipal v3, `countries-50m.json`, GeoFTP, zip da Natural Earth, Leaflet, MapLibre.

- [ ] **Step 1: Write the failing test**

`tests/use_cases/test_baixar_malha.py` builds tiny stand-in bodies and passes `expected` overrides only through a test helper that calls the pure checkers. The production size table is asserted exactly:

```python
def test_measured_urls_and_sizes_match_the_spec() -> None:
    assert [(item.nome, item.url, item.tamanho) for item in MEDIDOS] == [
        ("vendor/ol.js", "https://unpkg.com/ol@10.11.0/dist/ol.js", 1_070_771),
        ("vendor/ol.css", "https://unpkg.com/ol@10.11.0/ol.css", 6_343),
        ("vendor/topojson-client.min.js", "https://unpkg.com/topojson-client@3.1.0/dist/topojson-client.min.js", 7_169),
        ("municipios.json", "https://servicodados.ibge.gov.br/api/v2/malhas/BR?resolucao=5&qualidade=1&formato=application/json", 1_626_114),
        ("ufs.json", "https://servicodados.ibge.gov.br/api/v3/malhas/paises/BR?intrarregiao=UF&qualidade=minima&formato=application/json", 31_464),
        ("paises.json", "https://cdn.jsdelivr.net/npm/world-atlas@2.0.2/countries-110m.json", 107_761),
        ("municipio_tse_ibge.zip", "https://cdn.tse.jus.br/estatistica/sead/odsele/municipio_tse_ibge/municipio_tse_ibge.zip", 139_031),
    ]


def test_wrong_size_is_rejected() -> None:
    with pytest.raises(MeshSizeError):
        exigir_tamanho(b"curto", 6_343, "vendor/ol.css")


def test_ol_js_must_start_with_the_global() -> None:
    with pytest.raises(MeshSizeError):
        exigir_prefixo(b"export default 1", b"var ol=")


def test_single_object_name_is_recorded() -> None:
    topology = {"type": "Topology", "objects": {"malha": {"type": "GeometryCollection", "geometries": []}}}
    assert nome_do_objeto(topology) == "malha"


def test_two_object_names_stop() -> None:
    topology = {"objects": {"a": {}, "b": {}}}
    with pytest.raises(MeshSizeError):
        nome_do_objeto(topology)


def test_brazil_id_accepts_only_076() -> None:
    assert id_do_brasil([{"id": "242"}, {"id": "076"}]) == "076"
    with pytest.raises(MeshSizeError):
        id_do_brasil([{"id": "242"}])


def test_municipal_centroid_must_exist_on_some_geometry() -> None:
    exigir_centroide_municipal([{"properties": {"codarea": "1", "centroide": [-1, -2]}}])
    with pytest.raises(MeshSizeError):
        exigir_centroide_municipal([{"properties": {"codarea": "1"}}])
```

`test_download_writes_the_manifest` calls `baixar_malha` with a `Fetch` keyed by URL and a small `medidos` sequence. Each fake body is valid for its checker, and each injected `Medido.tamanho` equals `len(body)`. Production `MEDIDOS` stays the spec table and is not used in this test. The size checker itself stays mandatory inside `baixar_malha`. Signature:

```python
def baixar_malha(destino: Path, fetch: Fetch, medidos: Sequence[Medido] = MEDIDOS) -> Manifesto:
```

The default argument is the spec table. The test passes a small `medidos` sequence whose sizes equal `len(body)`.

Also assert the fake fetch was not called with a URL containing `countries-50m`, `intrarregiao=municipio`, `geoftp`, `leaflet`, `maplibre` or `mapbox`. Add `test_countries_use_the_countries_object`: a topology whose `objects` are `countries` and `land` yields `paises_objeto == "countries"` and does not call `nome_do_objeto`. `id_do_brasil([{"id": "76"}])` raises `MeshSizeError`.

The zip test builds a `zipfile` in memory with one member `municipio_tse_ibge.csv` of a chosen size, sets that size in the injected `Medido`, and expects `destino / "municipio_tse_ibge.csv"` to hold those bytes. A second member `.csv` raises `MeshSizeError`.

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/use_cases/test_baixar_malha.py --override-ini='addopts=' -q`

Expected: FAIL with `ImportError`.

- [ ] **Step 3: Write the minimal implementation**

`Medido` is a frozen dataclass: `nome`, `url`, `tamanho`, `prefixo: bytes | None = None`, `contem: bytes | None = None`, `csv_tamanho: int | None = None`. The production zip row sets `csv_tamanho` to `520_088`. Every other row leaves it `None`.

`exigir_tamanho` compares `len(body)` with `tamanho` after `requests` has decompressed the body. It does not read `Content-Length`. `exigir_prefixo` and `exigir_contem` check the prefix and the substring. `nome_do_objeto` returns the only key of `objects` and raises `MeshSizeError` when there are two. It is used for municipalities and UFs only. Countries require the key `countries` and ignore `land`. `id_do_brasil` accepts only the string `"076"`. Any other id, including `"76"`, raises `MeshSizeError`. `exigir_centroide_municipal` raises when no geometry has `properties["centroide"]` as a list of two `int` or `float` values. A missing centroid on some other geometry does not raise. The live municipal file, measured on 2026-10-13, has one object named `foo` and numeric centroids. The live UF file has one object named `BRUF` and no centroids. The unit fixtures keep the small names `malha` and `ufs`. The real `manifesto.json` records `foo` and `BRUF`.

`baixar_malha` creates `destino`, fetches each item, checks, and writes the file. The zip item is extracted with `zipfile.ZipFile(io.BytesIO(body))`. Only one name ending in `.csv` is read with `read`; its size must be 520.088 when the production table is used. The injected test table carries `csv_tamanho: int | None`. Production zip `Medido.csv_tamanho` is `520_088`.

`manifesto.json` is UTF-8, `json.dumps(..., ensure_ascii=False, indent=2) + "\n"`, keys `municipios_objeto`, `ufs_objeto`, `paises_objeto`, `brasil_id`. `paises_objeto` is the constant `countries`. If that key is absent, raise `MeshSizeError`.

`scripts/baixar_malha.py` inserts `src` on `sys.path` the same way `scripts/relatorio_presidente_governador.py` does, then calls `main`. `main` prints `Malha gravada em downloads/malha.` and `As cores e as logomarcas ficam em downloads/malha/marcas.json e downloads/malha/logomarcas/.` Exit 1 prints `A malha baixada não confere com a especificação.` Do not catch that into exit 2.

- [ ] **Step 4: Run the test to verify it passes**

Run: `uv run pytest tests/use_cases/test_baixar_malha.py --override-ini='addopts=' -q`

Expected: PASS. This test does not open the network.

- [ ] **Step 5: Commit**

```bash
uv run ruff check src/eleicoes/use_cases/baixar_malha.py scripts/baixar_malha.py tests/use_cases/test_baixar_malha.py
uv run ruff format --check src/eleicoes/use_cases/baixar_malha.py scripts/baixar_malha.py tests/use_cases/test_baixar_malha.py
uv run mypy --strict -p eleicoes
uv run pytest
git add src/eleicoes/use_cases/baixar_malha.py scripts/baixar_malha.py tests/use_cases/test_baixar_malha.py
git commit -m "feat: download the measured map meshes" --trailer "X-Jarvis-Ref: 0x1"
```

---

### Task 4: Gerar o HTML

**Files:**

- Create: `src/eleicoes/adapters/html_mapa.py`
- Test: `tests/adapters/test_html_mapa.py`

**Interfaces:**

- Consumes: `RecortePintado`, `Pintura`, `PaginaDoMapa`.
- Produces: `html_do_mapa(pagina: PaginaDoMapa) -> str`.

Add `PaginaDoMapa` to `src/eleicoes/domain/mapa.py`:

```python
@dataclass(frozen=True, slots=True)
class PaginaDoMapa:
    ano: int
    turno: int
    cargo: str
    recorte: RecortePintado
    municipios: str
    ufs: str
    paises: str
    municipios_objeto: str
    ufs_objeto: str
    paises_objeto: str
    brasil_id: str
    ol_js: str
    ol_css: str
    topojson_js: str
```

The strings `municipios`, `ufs` and `paises` are the raw topology JSON. `ol_js` and `topojson_js` are the script bodies.

- [ ] **Step 1: Write the failing test**

`tests/adapters/test_html_mapa.py` builds a `PaginaDoMapa` with:

- cargo `presidente`, ano 2026, turno 1
- `RecortePintado` whose country `Pintura` is `codigo="076"`, `cor="#112233"`, `numero="22"`, `logo="data:image/png;base64,QQ=="`
- one UF `codigo="12"` with the same logo
- one municipality `codigo="1200138"` with the same logo
- `sem_poligono=("Boa Esperança do Norte (MT)", "Lisboa (ZZ)")`
- topologies of a few dozen bytes. The countries topology has ids `076` and `242`. The municipal geometry includes `centroide: [-67.8, -9.8]` and also the text `</script>` inside a property name's neighbor string so the embed must escape it. Put `"</script>"` in a property `"nome": "</script>"`.
- `ol_js="var ol=1;"`, `topojson_js="var topojson=1;"`, `ol_css=".ol{}"`
- object names `malha`, `ufs`, `countries`

Assertions, all substrings:

- `<!DOCTYPE html>` and `lang="pt-BR"`
- title `Mapa de presidente — 2026, turno 1`
- `var ol=1;`, `var topojson=1;` and the library CSS `.ol{}` inside `<style>`
- no `type="module"`, no `fromLonLat`, no `EPSG:3857`, no `openstreetmap`, no `Natural Earth`, no `maplibre`, no `leaflet`
- `EPSG:4326`, `topojson.feature`, `ol.format.GeoJSON`, `ol.style.Fill`, `ol.style.Text`, `ol.style.Icon` and `ol.geom.Point`
- `declutter: false` and `overflow: true`
- the country layer is `camada(brasil, estilo, null, 4)`; UF is `camada` with `4, 6`; municipality is `camada` with `6, 28`. The country layer has no `minZoom`, because a `minZoom` of 0 is exclusive and would hide the country at zoom 0
- `function soBrasil` and the world layer created with `estiloMundo`. `estiloMundo` has no `get("cor")`. The id `242` stays in the countries topology and is not a key of the pintura JSON
- the base64 `QQ==` appears once
- `properties.logo` is assigned from the shared logo table
- `centroide` is read from the feature and passed to `ol.geom.Point`. No centroid is computed in Python or in JavaScript
- `Boa Esperança do Norte (MT)` and `Lisboa (ZZ)` appear escaped in a list under `Sem polígono`
- a hostile hole `<script>` passed in `sem_poligono` is rendered as `&lt;script&gt;`
- `IBGE`, `OpenLayers Contributors`, `Redistributions in binary form`, `Michael Bostock` and `Permission to use, copy, modify`
- `DT_GERACAO` and `CD_MUNICIPIO_TSE` do not appear
- the note `O recorte das regiões não entra neste mapa.`
- `background: #ffffff` on `#mapa`

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/adapters/test_html_mapa.py --override-ini='addopts=' -q`

Expected: FAIL with `ImportError`.

- [ ] **Step 3: Write the minimal implementation**

`html_do_mapa` concatenates strings. It does not call `str.format` on the JavaScript: the braces of the script stay single. This project already broke a page by doubling CSS braces.

The page starts with the literals `<!DOCTYPE html>` and `<html lang="pt-BR">`. The head contains one `<style>` element. Its text is `pagina.ol_css` followed by the page rules, so the fixture `.ol{}` sits inside that element. The title element is `Mapa de presidente — {ano}, turno {turno}` or `Mapa de governador — {ano}, turno {turno}`. With the test's year and turn, that title is `Mapa de presidente — 2026, turno 1`.

Fixture strings are inputs. Inline `pagina.ol_js` and `pagina.topojson_js` unchanged, so the test's `var ol=1;` and `var topojson=1;` appear in the page. Inline the countries topology raw, so the fixture id `242` stays in the page and is not a key of the pintura JSON. Pass each `sem_poligono` line through `html.escape`, so `Boa Esperança do Norte (MT)`, `Lisboa (ZZ)` and a `<script>` hole rendered as `&lt;script&gt;` come from the fixture. Write the fixture logo once in `logos`, so `QQ==` appears once.

Escape `</` as `<\/` inside every inlined script and inside every `application/json` block. Escape HTML text with `html.escape`.

The pintura JSON is:

```python
{
    "logos": {pintura.numero: pintura.logo},
    "pais": _item(recorte.pais),
    "ufs": [_item(item) for item in recorte.ufs],
    "municipios": [_item(item) for item in recorte.municipios],
    "brasilId": pagina.brasil_id,
    "ufsObjeto": pagina.ufs_objeto,
    "municipiosObjeto": pagina.municipios_objeto,
    "paisesObjeto": pagina.paises_objeto,
}
```

`_item` returns `{"codigo", "cor", "numero"}` and omits `logo`. Build `logos` by walking country, UFs and municipalities. The same data URI is stored once.

JSON blocks:

```html
<script type="application/json" id="pintura">...</script>
<script type="application/json" id="municipios">...</script>
<script type="application/json" id="ufs">...</script>
<script type="application/json" id="paises">...</script>
```

Then `topojson_js`, then `ol_js`, then the page script, all as classic scripts.

Page script. The zoom pairs are `ZOOM_PAIS = (None, 4)`, `ZOOM_UF = (4, 6)` and `ZOOM_MUNICIPIO = (6, 28)`. Python `None` is emitted as JavaScript `null`. The country call is `camada(brasil, estilo, null, 4)`. Do not emit `0` for that layer.

```javascript
(function () {
  var pintura = JSON.parse(document.getElementById("pintura").textContent);
  var municipios = JSON.parse(document.getElementById("municipios").textContent);
  var ufs = JSON.parse(document.getElementById("ufs").textContent);
  var paises = JSON.parse(document.getElementById("paises").textContent);

  function aplicar(topology, objectName, itens) {
    var porCodigo = {};
    for (var i = 0; i < itens.length; i++) {
      porCodigo[String(itens[i].codigo)] = itens[i];
    }
    var geometries = topology.objects[objectName].geometries;
    for (var j = 0; j < geometries.length; j++) {
      var geometry = geometries[j];
      var properties = geometry.properties || {};
      var code = properties.codarea;
      if (code === undefined || code === null) {
        code = geometry.id;
      }
      var item = porCodigo[String(code)];
      geometry.properties = properties;
      if (!item) {
        continue;
      }
      properties.cor = item.cor;
      properties.numero = item.numero;
      properties.logo = pintura.logos[item.numero];
      properties.codigo = String(item.codigo);
    }
  }

  function colecao(topology, objectName) {
    return topojson.feature(topology, topology.objects[objectName]);
  }

  function soBrasil(collection, brasilId) {
    return {
      type: "FeatureCollection",
      features: collection.features.filter(function (feature) {
        return String(feature.id) === String(brasilId);
      })
    };
  }

  function parNumerico(valor) {
    return Array.isArray(valor) && valor.length === 2 &&
      Number.isFinite(valor[0]) && Number.isFinite(valor[1]);
  }

  function estiloMundo() {
    return new ol.style.Style({
      fill: new ol.style.Fill({color: "#f7f7f7"}),
      stroke: new ol.style.Stroke({color: "#cccccc", width: 1})
    });
  }

  function estilo(feature) {
    var cor = feature.get("cor");
    if (!cor) {
      return estiloMundo();
    }
    var estilos = [new ol.style.Style({
      fill: new ol.style.Fill({color: cor}),
      stroke: new ol.style.Stroke({color: "#222222", width: 1}),
      text: new ol.style.Text({
        text: String(feature.get("numero")),
        font: "12px sans-serif",
        overflow: true,
        fill: new ol.style.Fill({color: "#111111"})
      })
    })];
    var logo = feature.get("logo");
    var centroide = feature.get("centroide");
    if (logo && parNumerico(centroide)) {
      estilos.push(new ol.style.Style({
        geometry: new ol.geom.Point(centroide),
        image: new ol.style.Icon({src: logo})
      }));
    }
    return estilos;
  }

  function camada(geojson, style, minZoom, maxZoom) {
    var opcoes = {
      source: new ol.source.Vector({features: new ol.format.GeoJSON({
        dataProjection: "EPSG:4326",
        featureProjection: "EPSG:4326"
      }).readFeatures(geojson)}),
      declutter: false,
      style: style
    };
    if (minZoom !== null) {
      opcoes.minZoom = minZoom;
    }
    if (maxZoom !== null) {
      opcoes.maxZoom = maxZoom;
    }
    return new ol.layer.Vector(opcoes);
  }

  var mundo = colecao(paises, pintura.paisesObjeto);
  var itensPais = pintura.pais ? [pintura.pais] : [];
  aplicar(paises, pintura.paisesObjeto, itensPais);
  aplicar(ufs, pintura.ufsObjeto, pintura.ufs);
  aplicar(municipios, pintura.municipiosObjeto, pintura.municipios);
  var brasil = soBrasil(colecao(paises, pintura.paisesObjeto), pintura.brasilId);

  new ol.Map({
    target: "mapa",
    layers: [
      camada(mundo, estiloMundo, null, null),
      camada(brasil, estilo, null, 4),
      camada(colecao(ufs, pintura.ufsObjeto), estilo, 4, 6),
      camada(colecao(municipios, pintura.municipiosObjeto), estilo, 6, 28)
    ],
    view: new ol.View({projection: "EPSG:4326", center: [-54, -14], zoom: 3})
  });
})();
```

The world collection is built before `aplicar`. The Brazil collection is built after `aplicar`, from a second call to `colecao`, not from the world features. topojson-client keeps `properties` by reference, so `aplicar` can write `cor` onto the same object a world feature already holds. `estiloMundo` must not read `cor`. Fiji stays out of the pintura table. `aplicar` is the named deviation accepted on 2026-10-13: the electoral properties are copied in the browser, and topojson-client still decodes the arcs. `maxZoom` is assigned whenever it is not null, including when `minZoom` is null, so the country layer stops at 4. A feature without a numeric `centroide` gets fill and text and no icon.

Footer, in Portuguese:

- `Malha municipal e de estados: IBGE. Licença compatível com CC BY 4.0.`
- The BSD-2-Clause notice, pasted in full, beginning `Copyright (c) 2005-present, OpenLayers Contributors. All rights reserved.` and containing the sentence `Redistributions in binary form must reproduce the above copyright notice` plus the `AS IS` disclaimer.
- The ISC notice, pasted in full: `Copyright (c) 2012-2019, Michael Bostock` and the sentence `Permission to use, copy, modify, and/or distribute this software for any purpose with or without fee is hereby granted`, plus the `AS IS` disclaimer.
- `O recorte das regiões não entra neste mapa. A malha desse recorte ainda não foi medida.`
- Heading `Sem polígono` and one `<li>` per line, or `Nenhum lugar com líder ficou fora da malha.` when the tuple is empty.

Page CSS: `body` and `#mapa` use `background: #ffffff`. `#mapa` has `height: 80vh`.

Title: `Mapa de presidente — {ano}, turno {turno}` or `Mapa de governador — {ano}, turno {turno}`.

- [ ] **Step 4: Run the test to verify it passes**

Run: `uv run pytest tests/adapters/test_html_mapa.py --override-ini='addopts=' -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
uv run ruff check src/eleicoes/adapters/html_mapa.py src/eleicoes/domain/mapa.py tests/adapters/test_html_mapa.py
uv run ruff format --check src/eleicoes/adapters/html_mapa.py src/eleicoes/domain/mapa.py tests/adapters/test_html_mapa.py
uv run mypy --strict -p eleicoes
uv run pytest
git add src/eleicoes/adapters/html_mapa.py src/eleicoes/domain/mapa.py tests/adapters/test_html_mapa.py
git commit -m "feat: render the leader choropleth" --trailer "X-Jarvis-Ref: 0x1"
```

---

### Task 5: Comando do mapa

**Files:**

- Create: `src/eleicoes/use_cases/apresentar_mapa.py`
- Create: `scripts/relatorio_mapa.py`
- Modify: `README.md` after the section `Cruzar presidente e governador`
- Test: `tests/use_cases/test_apresentar_mapa.py`

**Interfaces:**

- Consumes: `MeshAssets.load`, `recorte_pintado`, `html_do_mapa`, `RelatorioPresidenteGovernadorStore`, `view_from_places`, `Collect = Callable[[int, int], tuple[MunicipalPlace, ...]]`, `OpenReport = Callable[[Path], bool]`.
- Produces: `class PresentMap` with `execute(self, ano: int, turno: int, cargo: str, destino: Path, *, atualizar: bool = False) -> PresentedMap`. `PresentedMap` has `destino: Path`, `opened: bool`, `loaded: bool`. `main(argv=None, *, reader=None, names=None, store=None, assets=None, collect=None, render=None, open_report=None) -> int`. `Collect = Callable[[int, int], tuple[MunicipalPlace, ...]]`. The default `collect` is a production adapter with that signature. It builds the reader and the names, then calls `collect_places(reader, names, ano, turno)`. It is not `collect_places` itself: that function takes `(reader, names, ano, turno)` and mypy rejects the mismatch. Tests pass the two-argument `collect`.

CLI:

```text
uv run python scripts/relatorio_mapa.py --ano 2026 --turno 1 --cargo presidente
uv run python scripts/relatorio_mapa.py --ano 2026 --turno 1 --cargo governador --sem-navegador
```

Flags: `--ano` default 2026, `--turno` default 1, `--cargo` required, `--destino`, `--sem-navegador`, `--atualizar`. No `--uf`. Default path: `relatorios/mapa-{cargo}-{ano}-turno-{turno}.html`.

Exit codes:

| Situação | Código | Frase |
| --- | --- | --- |
| HTML gravado | 0 | `Mapa gravado em {caminho}.` |
| Cache usado | 0 | segunda linha `Votos carregados do banco, gerados em AAAA-MM-DD HH:MM.` |
| Recalculado | 0 | segunda linha `Votos gravados no banco.` |
| Arquivo ausente | 1 | `Falta {MeshMissingError.nome}.` |
| Ponte sem o município | 1 | `Não há código IBGE para o município {codigo} ({uf}).` |
| Marca ausente | 1 | `Falta a cor ou a logomarca do partido {numero}.` |
| Cargo, ano, turno ou malha incoerente | 1 | `Não foi possível apresentar o mapa.` |

`brasil_id` of the manifesto must be a member of `ids_pais`. Otherwise raise `MeshMismatchError` and exit 1. The presenter does not call `requests` and does not call `baixar_malha`.

- [ ] **Step 1: Write the failing test**

`tests/use_cases/test_apresentar_mapa.py` uses an in-memory store with `load`, `save` and `close`, the same shape as `RelatorioPresidenteGovernadorStore`. `assets.load` returns a `MalhaCarregada` built from the Task 2 fixture types, with Bujari's codes and a mark for party 22. `collect` returns one `MunicipalPlace` for AC / `01007` / Bujari / party 22.

```python
def test_command_writes_the_president_map_without_a_browser(tmp_path: Path) -> None:
    destino = tmp_path / "mapa.html"
    code = main(
        ["--ano", "2026", "--turno", "1", "--cargo", "presidente", "--destino", str(destino), "--sem-navegador"],
        store=_Memory(),
        assets=_Assets(),
        collect=lambda ano, turno: (_bujari(),),
    )
    assert code == 0
    assert destino.is_file()
    assert "Mapa de presidente — 2026, turno 1" in destino.read_text(encoding="utf-8")


def test_injected_opener_records_the_path(tmp_path: Path) -> None:
    destino = tmp_path / "mapa.html"
    opened: list[Path] = []
    main(
        ["--ano", "2026", "--turno", "1", "--cargo", "presidente", "--destino", str(destino)],
        store=_Memory(),
        assets=_Assets(),
        collect=lambda ano, turno: (_bujari(),),
        open_report=opened.append,
    )
    assert opened == [destino]


def test_missing_mesh_exits_1(capsys: pytest.CaptureFixture[str]) -> None:
    code = main(
        ["--cargo", "presidente", "--sem-navegador"],
        store=_Memory(),
        assets=_BrokenAssets(),
        collect=lambda ano, turno: (),
        open_report=lambda path: True,
    )
    assert code == 1
    assert "Falta downloads/malha/manifesto.json." in capsys.readouterr().err


def test_governor_page_uses_the_governor_number(tmp_path: Path) -> None:
    destino = tmp_path / "mapa.html"
    main(
        ["--cargo", "governador", "--destino", str(destino), "--sem-navegador"],
        store=_Memory(),
        assets=_Assets(),
        collect=lambda ano, turno: (_bujari(),),
        open_report=lambda path: True,
    )
    text = destino.read_text(encoding="utf-8")
    assert "Mapa de governador — 2026, turno 1" in text
```

`_bujari` for the governor test uses president 22 and governor 13, and `_Assets` includes both marks. Assert the governor HTML contains `"numero": "13"` and the president HTML contains `"numero": "22"`.

`test_reload_does_not_collect_again`: save a stored report, call `main` without `--atualizar`, and assert `collect` was not called. Call again with `--atualizar` and assert `collect` was called.

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/use_cases/test_apresentar_mapa.py --override-ini='addopts=' -q`

Expected: FAIL with `ImportError`.

- [ ] **Step 3: Write the minimal implementation**

`PresentMap.execute` validates `ElectionYear` and `Turno`. It loads the store unless `atualizar` or `load` returns `None`. On a miss it calls `collect`, then `save`. It loads the mesh, checks `manifesto.brasil_id in ids_pais`, calls `view_from_places`, then `recorte_pintado`, then `html_do_mapa`, writes UTF-8, and calls the opener chosen below. `close` runs in `finally`.

`_choose_opener` copies `apresentar_presidente_governador._choose_opener`. An injected `open_report` is used even when `--sem-navegador` is present. Without an injection, the flag selects the skip opener, and the default selects the production opener.

`main` maps `MeshMissingError`, `BridgeMissingError` and `MarkMissingError` to exit 1 with the sentences in the table. One line per missing municipality and per missing party. Any other `ElectionError`, including `MarkInvalidError` and `MeshMismatchError`, prints `Não foi possível apresentar o mapa.` and returns 1. This command never returns 2. Every error sentence uses `print(..., file=sys.stderr)`. Success prints the path sentence and the cache sentence on stdout. Add `test_missing_bridge_exits_1` and `test_missing_mark_exits_1` with the sentences in the table, and assert that no HTML file is written.

`scripts/relatorio_mapa.py` matches the path insertion of `scripts/relatorio_presidente_governador.py` and calls `main`.

README section, inserted after the president×governor section:

```markdown
## Abrir o mapa de presidente ou de governador

O mapa pinta o partido líder em cada recorte. O zoom mínimo é o país, o seguinte é a UF e o máximo é o município. A região não entra: a malha desse recorte ainda não foi medida.

Antes da primeira página, grave a malha medida:

```bash
uv run python scripts/baixar_malha.py
```

Coloque as cores e as logomarcas em `downloads/malha/marcas.json` e `downloads/malha/logomarcas/`. A chave é o número do partido. O valor tem `cor` (`#` e seis dígitos) e `arquivo` (o nome do PNG ou do SVG). Sem a cor ou a logomarca de um líder, o comando para e não escreve o HTML.

```bash
uv run python scripts/relatorio_mapa.py --ano 2026 --turno 1 --cargo presidente
```

Para só gravar o arquivo:

```bash
uv run python scripts/relatorio_mapa.py --ano 2026 --turno 1 --cargo governador --sem-navegador
```

O arquivo sai em `relatorios/mapa-{cargo}-{ano}-turno-{turno}.html`. `--atualizar` relê os boletins e substitui os votos municipais que o relatório de presidente e governador também usa.

| Opção | Padrão | Efeito |
| --- | --- | --- |
| `--ano` | `2026` | Ano da eleição. |
| `--turno` | `1` | Turno. |
| `--cargo` |  | `presidente` ou `governador`. |
| `--destino` | pasta `relatorios/` | Caminho completo do HTML. |
| `--sem-navegador` | abre o navegador | Grava o HTML e deixa o navegador fechado. |
| `--atualizar` | usa o que está no banco | Recalcula os votos municipais. |
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `uv run pytest tests/use_cases/test_apresentar_mapa.py --override-ini='addopts=' -q`

Expected: PASS.

Then run the real download once, from the repository root. This step uses the network. The accepted zip is 139.031 bytes and the inner CSV is 520.088 bytes. If either size, or any other measured size, differs, stop and report the received size. Do not change the constant.

```bash
uv run python scripts/baixar_malha.py
```

Expected manifesto: `municipios_objeto` `foo`, `ufs_objeto` `BRUF`, `paises_objeto` `countries` and `brasil_id` `076`. Expected sentence: `Malha gravada em downloads/malha.`

Open a generated page only after `marcas.json` has the leaders of the loaded UFs. With the mesh in place and marks for those parties:

```bash
uv run python scripts/relatorio_mapa.py --ano 2026 --turno 1 --cargo presidente --sem-navegador
```

Open `relatorios/mapa-presidente-2026-turno-1.html` from disk. Confirm, on screen: no network request, the global `ol`, the country visible at zoom 0 and at the initial zoom, UF after zooming past 4, municipalities after zooming past 6, the municipal logo sitting on the centroid, every municipal logo still drawn in a metropolitan cluster, and no polygon for ZZ or for a region. If a cut appears on the wrong zoom, change the three `camada` thresholds together with the assertions in `tests/adapters/test_html_mapa.py`.

- [ ] **Step 5: Commit**

```bash
uv run ruff check src/eleicoes/use_cases/apresentar_mapa.py scripts/relatorio_mapa.py tests/use_cases/test_apresentar_mapa.py
uv run ruff format --check src/eleicoes/use_cases/apresentar_mapa.py scripts/relatorio_mapa.py tests/use_cases/test_apresentar_mapa.py
uv run mypy --strict -p eleicoes
uv run pytest
git add src/eleicoes/use_cases/apresentar_mapa.py scripts/relatorio_mapa.py tests/use_cases/test_apresentar_mapa.py README.md
git commit -m "feat: add the president and governor map command" --trailer "X-Jarvis-Ref: 0x1"
```

Do not `git add` `downloads/` or `relatorios/`.
