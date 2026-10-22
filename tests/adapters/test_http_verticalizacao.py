"""Verticalization route: contract, errors and the cached job."""

from collections.abc import Callable, Iterator

import pytest
from fastapi import FastAPI
from tests.adapters.test_read_api import _get, _ports
from tests.domain.test_verticalizacao import city_lines, every_cargo, uf_lines

from eleicoes.adapters.http.dependencies import clear_report_caches
from eleicoes.adapters.http.dependencies_verticalizacao import (
    clear_vertical_caches,
    get_vertical_job,
)
from eleicoes.composition.api import create_app
from eleicoes.domain.errors import (
    ElectionError,
    InvalidCargoError,
    InvalidNumeroError,
    InvalidUfError,
    MissingPowerReportError,
)
from eleicoes.domain.verticalizacao import (
    DEPUTADO_ESTADUAL,
    DEPUTADO_FEDERAL,
    GOVERNADOR,
    PRESIDENTE,
    VerticalLine,
    vertical_base,
)
from eleicoes.domain.verticalizacao_relatorio import VerticalView, scatter_view, vertical_report

_ROUTE = "/relatorios/dados/verticalizacao"
_MISSING = (
    "O relatório de poder de senador ainda não foi gravado. "
    "Gere com: uv run python scripts/relatorio_poder.py --cargo senador --sem-navegador"
)
Job = Callable[[int, int, str | None, int | None, str, str], VerticalView]


@pytest.fixture(autouse=True)
def _fresh_caches() -> Iterator[None]:
    clear_vertical_caches()
    yield
    clear_vertical_caches()


def _lines() -> tuple[VerticalLine, ...]:
    cities = tuple(
        line
        for index in range(3)
        for cargo, votos in (
            (DEPUTADO_FEDERAL, {13: 10 + index, 22: 30}),
            (GOVERNADOR, {13: 40 + 2 * index, 22: 20}),
            (PRESIDENTE, {13: 50, 22: 50}),
        )
        for line in city_lines(cargo, str(index), f"CIDADE {index} (SP)", 100, votos)
    )
    return (
        *every_cargo("SP", skip=(GOVERNADOR, DEPUTADO_ESTADUAL)),
        *uf_lines(GOVERNADOR, "SP", {13: 70, 22: 30}),
        *uf_lines(DEPUTADO_ESTADUAL, "SP", {13: 10, 22: 30, 45: 60}),
        *every_cargo("MG"),
        *cities,
    )


def _view(uf: str | None = None, partido: int | None = None) -> VerticalView:
    base = vertical_base(2026, 1, _lines())
    report = vertical_report(base, uf)
    return VerticalView(report, scatter_view(base, report, partido, DEPUTADO_FEDERAL, GOVERNADOR))


def _app(job: Job) -> FastAPI:
    application = create_app(ports=_ports())
    application.dependency_overrides[get_vertical_job] = lambda: job
    return application


def _recording(calls: list[tuple[object, ...]]) -> Job:
    def job(
        ano: int, turno: int, uf: str | None, partido: int | None, x: str, y: str
    ) -> VerticalView:
        calls.append((ano, turno, uf, partido, x, y))
        return _view()

    return job


def _raising(error: ElectionError) -> Job:
    def job(
        _ano: int, _turno: int, _uf: str | None, _partido: int | None, _x: str, _y: str
    ) -> VerticalView:
        raise error

    return job


def test_route_is_documented() -> None:
    schema = _get(create_app(ports=_ports()), "/openapi.json").json()
    operation = schema["paths"][_ROUTE]["get"]
    assert operation["summary"] == "Verticalização"
    names = {item["name"] for item in operation["parameters"]}
    assert names == {"ano", "turno", "uf", "partido", "cargo_x", "cargo_y"}


def test_json_follows_the_contract() -> None:
    response = _get(_app(_recording([])), f"{_ROUTE}?ano=2026&turno=1")
    assert response.status_code == 200
    body = response.json()
    assert list(body) == [
        "ano",
        "turno",
        "uf",
        "municipios",
        "sem_uf",
        "cargos",
        "limiares",
        "partidos",
        "dispersao",
        "notas",
    ]
    assert body["cargos"] == [
        "presidente",
        "governador",
        "senador",
        "deputadoFederal",
        "deputadoEstadual",
    ]
    assert body["limiares"] == {
        "razao": "2",
        "diferenca": "10,00%",
        "base_relevante": "5,00%",
        "minimo_municipios": 10,
    }
    assert body["municipios"] == 3
    first = body["partidos"][0]
    assert list(first) == [
        "partido",
        "perfil",
        "coerencia_mediana",
        "cargos",
        "coerencia",
        "comparacoes",
    ]
    assert len(first["cargos"]) == 5
    assert len(first["coerencia"]) == 7
    assert len(first["comparacoes"]) == 3
    assert list(first["cargos"][0]) == [
        "cargo",
        "votos",
        "validos",
        "validos_onde",
        "fatia",
        "fatia_onde",
        "ufs_concorreu",
        "ufs_total",
    ]
    assert first["coerencia"][0]["r"] is None
    assert first["coerencia_mediana"] is None
    comparacao = first["comparacoes"][0]
    assert list(comparacao) == [
        "majoritario",
        "proporcional",
        "majoritaria",
        "esperada",
        "razao",
        "classe",
        "por_uf",
        "sem_candidato",
    ]
    dispersao = body["dispersao"]
    assert list(dispersao) == ["partido", "cargo_x", "cargo_y", "coerencia", "pontos"]
    assert list(dispersao["pontos"][0]) == ["codigo", "nome", "uf", "comparecimento", "x", "y"]
    assert len(body["notas"]) == 8


def test_numbers_are_formatted_in_portuguese() -> None:
    body = _get(_app(lambda *_args: _view("SP", 13)), f"{_ROUTE}?ano=2026&turno=1").json()
    pt = next(item for item in body["partidos"] if item["partido"] == 13)
    governador = pt["cargos"][1]
    assert governador["fatia"] == "70,00%"
    assert governador["fatia_onde"] == "70,00%"
    assert (governador["ufs_concorreu"], governador["ufs_total"]) == (1, 1)
    comparacao = pt["comparacoes"][0]
    assert comparacao["majoritaria"] == "70,00%"
    assert comparacao["esperada"] == "25,00%"
    assert comparacao["razao"] == "2,8000"
    assert comparacao["classe"] == "puxador"
    assert comparacao["por_uf"] == [
        {"uf": "SP", "majoritaria": "70,00%", "esperada": "25,00%", "classe": "puxador"}
    ]
    psdb = next(item for item in body["partidos"] if item["partido"] == 45)
    assert psdb["comparacoes"][0]["sem_candidato"] == [{"uf": "SP", "proporcional": "60,00%"}]
    assert psdb["comparacoes"][0]["majoritaria"] is None
    assert psdb["cargos"][0]["fatia_onde"] is None
    ponto = body["dispersao"]["pontos"][0]
    assert ponto == {
        "codigo": "0",
        "nome": "CIDADE 0 (SP)",
        "uf": "SP",
        "comparecimento": 100,
        "x": "25,00%",
        "y": "66,67%",
    }


def test_coherence_is_formatted_with_four_decimals() -> None:
    from eleicoes.adapters.http.schemas_verticalizacao import CoerenciaJson
    from eleicoes.domain.verticalizacao_coerencia import Coherence

    item = CoerenciaJson.from_domain(Coherence(DEPUTADO_FEDERAL, GOVERNADOR, -0.12, 30))
    assert item.r == "-0,1200"


@pytest.mark.parametrize(
    ("query", "uf"),
    [("&uf=TODAS", None), ("&uf=", None), ("", None), ("&uf=todas", None), ("&uf=sp", "sp")],
)
def test_uf_reaches_the_job(query: str, uf: str | None) -> None:
    calls: list[tuple[object, ...]] = []
    response = _get(_app(_recording(calls)), f"{_ROUTE}?ano=2026&turno=1{query}")
    assert response.status_code == 200
    assert calls == [(2026, 1, uf, None, DEPUTADO_FEDERAL, GOVERNADOR)]


def test_scatter_parameters_reach_the_job() -> None:
    calls: list[tuple[object, ...]] = []
    query = "ano=2026&turno=1&partido=13&cargo_x=deputadoEstadual&cargo_y=presidente"
    _get(_app(_recording(calls)), f"{_ROUTE}?{query}")
    assert calls == [(2026, 1, None, 13, DEPUTADO_ESTADUAL, PRESIDENTE)]


def test_missing_power_report_is_409() -> None:
    response = _get(
        _app(_raising(MissingPowerReportError("senador"))), f"{_ROUTE}?ano=2026&turno=1"
    )
    assert response.status_code == 409
    assert response.json() == {"detail": _MISSING}


@pytest.mark.parametrize(
    ("error", "detail"),
    [
        (InvalidUfError("ZZ"), "UF inválida."),
        (InvalidCargoError("vereador"), "Cargo inválido."),
        (InvalidNumeroError(100), "Número inválido."),
    ],
)
def test_domain_errors_are_422(error: ElectionError, detail: str) -> None:
    response = _get(_app(_raising(error)), f"{_ROUTE}?ano=2026&turno=1")
    assert response.status_code == 422
    assert response.json() == {"detail": detail}


def test_wrong_type_is_422() -> None:
    response = _get(_app(_recording([])), f"{_ROUTE}?ano=2026&turno=1&partido=abc")
    assert response.status_code == 422
    assert response.json() == {"detail": "Parâmetros inválidos."}


class _Reader:
    def __init__(self, opened: list["_Reader"]) -> None:
        self.calls: list[tuple[int, int]] = []
        self.closed = 0
        opened.append(self)

    def vertical_lines(self, ano: int, turno: int) -> tuple[VerticalLine, ...]:
        self.calls.append((ano, turno))
        return _lines()

    def close(self) -> None:
        self.closed += 1


def _patch_reader(monkeypatch: pytest.MonkeyPatch, opened: list[_Reader]) -> None:
    monkeypatch.setattr(
        "eleicoes.use_cases.verticalizacao._production_reader", lambda: _Reader(opened)
    )


def test_real_job_builds_once_per_election_and_closes(monkeypatch: pytest.MonkeyPatch) -> None:
    opened: list[_Reader] = []
    _patch_reader(monkeypatch, opened)
    job = get_vertical_job()
    brasil = job(2026, 1, None, None, DEPUTADO_FEDERAL, GOVERNADOR)
    sp = job(2026, 1, "sp", 13, DEPUTADO_FEDERAL, GOVERNADOR)
    mg = job(2026, 1, "MG", None, DEPUTADO_FEDERAL, GOVERNADOR)
    assert len(opened) == 1
    assert opened[0].calls == [(2026, 1)]
    assert opened[0].closed == 1
    assert brasil.report.uf is None
    assert (sp.report.uf, sp.dispersao.partido) == ("SP", 13)
    assert mg.report.uf == "MG"
    assert job(2026, 1, "SP", None, DEPUTADO_FEDERAL, GOVERNADOR).report is sp.report


def test_real_job_validates_before_reading(monkeypatch: pytest.MonkeyPatch) -> None:
    opened: list[_Reader] = []
    _patch_reader(monkeypatch, opened)
    with pytest.raises(InvalidUfError):
        get_vertical_job()(2026, 1, "XX", None, DEPUTADO_FEDERAL, GOVERNADOR)
    assert opened == []


def test_real_job_does_not_cache_an_error(monkeypatch: pytest.MonkeyPatch) -> None:
    attempts: list[int] = []

    def failing() -> _Reader:
        attempts.append(1)
        raise ElectionError("database session is not configured")

    monkeypatch.setattr("eleicoes.use_cases.verticalizacao._production_reader", failing)
    for _attempt in range(2):
        with pytest.raises(ElectionError):
            get_vertical_job()(2026, 1, None, None, DEPUTADO_FEDERAL, GOVERNADOR)
    assert len(attempts) == 2


def test_clear_report_caches_forces_a_new_read(monkeypatch: pytest.MonkeyPatch) -> None:
    opened: list[_Reader] = []
    _patch_reader(monkeypatch, opened)
    get_vertical_job()(2026, 1, None, None, DEPUTADO_FEDERAL, GOVERNADOR)
    clear_report_caches()
    get_vertical_job()(2026, 1, None, None, DEPUTADO_FEDERAL, GOVERNADOR)
    assert len(opened) == 2


@pytest.mark.parametrize(
    ("query", "detail"),
    [
        ("&uf=ZZ", "UF inválida."),
        ("&cargo_x=governador", "Cargo inválido."),
        ("&partido=100", "Número inválido."),
    ],
)
def test_real_job_answers_422(monkeypatch: pytest.MonkeyPatch, query: str, detail: str) -> None:
    opened: list[_Reader] = []
    _patch_reader(monkeypatch, opened)
    response = _get(create_app(ports=_ports()), f"{_ROUTE}?ano=2026&turno=1{query}")
    assert response.status_code == 422
    assert response.json() == {"detail": detail}
    assert len(opened) == (1 if query == "&uf=ZZ" else 0)
