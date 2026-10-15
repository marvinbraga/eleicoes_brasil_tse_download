"""JSON for municipal profiles and the governor class. Fakes stand in for Postgres."""

import asyncio
import inspect
from collections.abc import Callable
from fractions import Fraction
from typing import cast

import httpx
import pytest
from fastapi import FastAPI

from eleicoes.adapters.html_classe_governador import NOTES as CLASS_NOTES
from eleicoes.adapters.html_classe_governador import texto_regra
from eleicoes.adapters.html_perfis import NOTES as PROFILE_NOTES
from eleicoes.adapters.http.bundle import ReadPorts
from eleicoes.adapters.http.dependencies import get_class_job, get_profile_job
from eleicoes.adapters.http.relatorios import classe_governador, perfis
from eleicoes.adapters.http.schemas_relatorios import ClassJson, ProfileJson
from eleicoes.composition.api import create_app
from eleicoes.domain.classe_governador import (
    ClassLine,
    ClassOutcome,
    ClassReport,
    ClassRule,
    RuleCut,
)
from eleicoes.domain.errors import CargoSemCelulasError, InvalidTurnoError
from eleicoes.domain.perfis import GroupSpan, ProfileCity, ProfileGroup, ProfileLine, ProfileReport
from eleicoes.ports.boletim_consulta import AsyncBoletimReader
from eleicoes.ports.classe_governador import ClassFit
from eleicoes.ports.grade import AsyncMunicipalityNames
from eleicoes.ports.perfis import RawClusterFit
from eleicoes.ports.relatorio_poder import AsyncRelatorioPoderStore
from eleicoes.ports.relatorio_presidente_governador import AsyncRelatorioPresidenteGovernadorStore
from eleicoes.use_cases.apresentar_classe_governador import build_governor_class
from eleicoes.use_cases.apresentar_perfis import build_profile

_PROFILE = "/relatorios/dados/perfis"
_CLASS = "/relatorios/dados/classe-governador"
_CENTER = (0.25, 0.5, 0.0, 1.0)
_DEPUTY = "O cargo deputado federal não tem células gravadas."


class _ProfileReader:
    def __init__(self, lines: tuple[ProfileLine, ...] = ()) -> None:
        self.lines = lines
        self.calls: list[tuple[int, int, str]] = []
        self.closed = False

    def profile_lines(self, ano: int, turno: int, cargo: str) -> tuple[ProfileLine, ...]:
        self.calls.append((ano, turno, cargo))
        return self.lines

    def close(self) -> None:
        self.closed = True


class _ClassReader:
    def __init__(self, lines: tuple[ClassLine, ...] = ()) -> None:
        self.lines = lines
        self.calls: list[tuple[int, int]] = []
        self.closed = False

    def class_lines(self, ano: int, turno: int) -> tuple[ClassLine, ...]:
        self.calls.append((ano, turno))
        return self.lines

    def close(self) -> None:
        self.closed = True


class _Cluster:
    def fit(
        self,
        matrix: tuple[tuple[float, ...], ...],
        span: GroupSpan,
    ) -> RawClusterFit:
        width = len(matrix[0])
        k = span.values()[0]
        center = tuple(_CENTER[index % len(_CENTER)] for index in range(width))
        centers = tuple(center for _group in range(k))
        labels = tuple(index % k for index in range(len(matrix)))
        return RawClusterFit(labels, centers, 0.25 if span.searched else None)


class _Model:
    def __init__(self, result: ClassFit) -> None:
        self.result = result

    def fit(
        self,
        matrix: tuple[tuple[float, ...], ...],
        labels: tuple[str, ...],
        parties: tuple[int, ...],
    ) -> ClassFit:
        self.seen = (matrix, labels, parties)
        return self.result


def test_profile_json_uses_the_formatted_center_and_the_shared_notes() -> None:
    reader = _ProfileReader(_president_lines())
    payload = _profile(reader, "presidente", "2")
    assert set(payload) == {
        "ano",
        "turno",
        "cargo",
        "partidos",
        "com_cedula",
        "buscou",
        "silhueta",
        "grupos",
        "municipios",
        "notas",
    }
    assert payload["ano"] == 2026
    assert payload["turno"] == 1
    assert payload["cargo"] == "presidente"
    assert payload["partidos"] == [13, 22]
    assert payload["com_cedula"] is True
    assert payload["buscou"] is False
    assert payload["silhueta"] is None
    assert payload["notas"] == list(PROFILE_NOTES)
    assert len(PROFILE_NOTES) == 5
    group = payload["grupos"][0]
    assert set(group) == {"numero", "municipios", "comparecimento", "centro"}
    assert group["numero"] == 1
    assert group["municipios"] == 2
    assert group["comparecimento"] == 18
    assert group["centro"] == ["25,00%", "50,00%", "0,00%", "100,00%"]
    assert [row["municipios"] for row in payload["grupos"]] == [2, 1]
    assert payload["municipios"] == [
        {"codigo": "1", "nome": "Alpha", "grupo": 1},
        {"codigo": "3", "nome": "Gama", "grupo": 1},
        {"codigo": "2", "nome": "Beta", "grupo": 2},
    ]
    assert reader.calls == [(2026, 1, "presidente")]


def test_searched_profile_publishes_the_silhouette_decimal() -> None:
    payload = _profile(_ProfileReader(_president_lines()), "presidente", "2-2")
    assert payload["buscou"] is True
    assert payload["silhueta"] == "0,2500"


def test_senator_center_stops_at_the_parties() -> None:
    payload = _profile(_ProfileReader(_senator_lines()), "senador", "2")
    assert payload["com_cedula"] is False
    assert payload["partidos"] == [13]
    assert payload["grupos"][0]["centro"] == ["25,00%"]


def test_deputy_is_refused_before_the_stored_lines() -> None:
    reader = _ProfileReader(_president_lines())
    response = _get(_profile_app(reader), f"{_PROFILE}?ano=2026&turno=1&cargo=deputadoFederal")
    assert response.status_code == 409
    assert response.json()["detail"] == _DEPUTY
    assert reader.calls == []


def test_invalid_group_span_is_422_and_does_not_read() -> None:
    reader = _ProfileReader(_president_lines())
    response = _get(_profile_app(reader), f"{_PROFILE}?ano=2026&turno=1&cargo=senador&grupos=6-2")
    assert response.status_code == 422
    assert response.json()["detail"] == "A faixa de grupos é inválida."
    assert reader.calls == []


def test_class_json_uses_the_rule_text_and_the_shared_notes() -> None:
    payload = _class_payload()
    assert set(payload) == {"ano", "turno", "acerto", "base", "linhas", "retidas", "notas"}
    assert payload["ano"] == 2026
    assert payload["turno"] == 1
    assert payload["acerto"] == "100,00%"
    assert payload["base"] == "50,00%"
    assert payload["retidas"] == []
    assert payload["notas"] == list(CLASS_NOTES)
    assert len(CLASS_NOTES) == 4
    first, second = payload["linhas"]
    assert set(first) == {"classe", "rotulo", "apoio", "regras"}
    assert first == {
        "classe": "consolidacao",
        "rotulo": "Consolidação",
        "apoio": 1,
        "regras": [texto_regra((RuleCut(13, 0.5, True),))],
    }
    assert second["classe"] == "em_aberto"
    assert second["rotulo"] == "Em aberto"
    assert second["apoio"] == 1
    assert second["regras"] == [texto_regra(())]


def test_held_out_labels_keep_the_report_order() -> None:
    report = ClassReport(
        2026,
        1,
        (13,),
        Fraction(1, 2),
        Fraction(1, 2),
        (ClassOutcome("consolidacao", 1, ()),),
        ("sem_governador", "em_aberto"),
    )
    payload = ClassJson.from_domain(report).model_dump()
    assert payload["retidas"] == ["Sem governador", "Em aberto"]
    assert payload["acerto"] == "50,00%"
    assert payload["base"] == "50,00%"
    assert payload["linhas"][0]["regras"] == ["A árvore não cortou esta classe."]


def test_silhouette_is_null_unless_the_search_produced_one() -> None:
    hidden = _bare_profile(searched=False, silhouette=0.25)
    missing = _bare_profile(searched=True, silhouette=None)
    shown = _bare_profile(searched=True, silhouette=0.25)
    assert ProfileJson.from_domain(hidden).silhueta is None
    assert ProfileJson.from_domain(missing).silhueta is None
    assert ProfileJson.from_domain(shown).silhueta == "0,2500"


def test_queries_do_not_accept_or_send_atualizar() -> None:
    assert "atualizar" not in inspect.signature(perfis).parameters
    assert "atualizar" not in inspect.signature(classe_governador).parameters
    application = _both()
    spec = _get(application, "/openapi.json").json()
    assert _names(spec, _PROFILE) == {"ano", "turno", "cargo", "grupos"}
    assert _names(spec, _CLASS) == {"ano", "turno"}
    assert spec["paths"][_PROFILE]["get"]["summary"] == "Perfis municipais"
    assert spec["paths"][_CLASS]["get"]["summary"] == "Classe do governador"
    profile = _get(application, f"{_PROFILE}?ano=2026&turno=1&cargo=presidente&grupos=2")
    refreshed = _get(
        application,
        f"{_PROFILE}?ano=2026&turno=1&cargo=presidente&grupos=2&atualizar=true",
    )
    assert profile.status_code == 200
    assert refreshed.json() == profile.json()
    classified = _get(application, f"{_CLASS}?ano=2026&turno=1")
    again = _get(application, f"{_CLASS}?ano=2026&turno=1&atualizar=true")
    assert classified.status_code == 200
    assert again.json() == classified.json()


def test_invalid_year_and_turno_keep_the_fixed_sentences() -> None:
    reader = _ProfileReader(_president_lines())
    year = _get(_profile_app(reader), f"{_PROFILE}?ano=1800&turno=1&cargo=presidente")
    assert year.status_code == 422
    assert year.json()["detail"] == "Ano inválido."
    assert reader.calls == []
    turno = _get(_class_app(_ClassReader(_sample())), f"{_CLASS}?ano=2026&turno=9")
    assert turno.status_code == 422
    assert turno.json()["detail"] == "Turno inválido."


def test_stored_profile_job_closes_the_reader(monkeypatch: pytest.MonkeyPatch) -> None:
    reader = _ProfileReader(_senator_lines())
    _patch_profile(monkeypatch, reader)
    report = get_profile_job()(2026, 1, "senador", "2")
    assert report.cargo == "senador"
    assert reader.calls == [(2026, 1, "senador")]
    assert reader.closed is True


def test_stored_profile_job_closes_when_the_cargo_is_refused(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reader = _ProfileReader(_president_lines())
    _patch_profile(monkeypatch, reader)
    with pytest.raises(CargoSemCelulasError, match="deputado federal"):
        get_profile_job()(2026, 1, "deputadoFederal", "2-6")
    assert reader.calls == []
    assert reader.closed is True


def test_stored_class_job_closes_the_reader(monkeypatch: pytest.MonkeyPatch) -> None:
    reader = _ClassReader(_sample())
    _patch_class(monkeypatch, reader)
    report = get_class_job()(2026, 1)
    assert report.hit_rate == Fraction(1, 1)
    assert reader.calls == [(2026, 1)]
    assert reader.closed is True


def test_stored_class_job_closes_when_the_turno_is_invalid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reader = _ClassReader(_sample())
    _patch_class(monkeypatch, reader)
    with pytest.raises(InvalidTurnoError):
        get_class_job()(2026, 9)
    assert reader.calls == []
    assert reader.closed is True


def _profile(reader: _ProfileReader, cargo: str, grupos: str) -> dict[str, object]:
    query = f"{_PROFILE}?ano=2026&turno=1&cargo={cargo}&grupos={grupos}"
    response = _get(_profile_app(reader), query)
    assert response.status_code == 200
    found = response.json()
    assert isinstance(found, dict)
    return cast(dict[str, object], found)


def _class_payload() -> dict[str, object]:
    response = _get(_class_app(_ClassReader(_sample())), f"{_CLASS}?ano=2026&turno=1")
    assert response.status_code == 200
    found = response.json()
    assert isinstance(found, dict)
    return cast(dict[str, object], found)


def _profile_app(reader: _ProfileReader) -> FastAPI:
    return _application(_profile_job(reader), _unused)


def _class_app(reader: _ClassReader) -> FastAPI:
    return _application(_unused, _class_job(reader))


def _both() -> FastAPI:
    profile = _profile_job(_ProfileReader(_president_lines()))
    governor = _class_job(_ClassReader(_sample()))
    return _application(profile, governor)


def _application(
    profile: Callable[[int, int, str, str], ProfileReport],
    governor: Callable[[int, int], ClassReport],
) -> FastAPI:
    application = create_app(ports=_ports())
    application.dependency_overrides[get_profile_job] = lambda: profile
    application.dependency_overrides[get_class_job] = lambda: governor
    return application


def _profile_job(
    reader: _ProfileReader,
) -> Callable[[int, int, str, str], ProfileReport]:
    cluster = _Cluster()

    def build(ano: int, turno: int, cargo: str, grupos: str) -> ProfileReport:
        return build_profile(reader, cluster, ano, turno, cargo, grupos)

    return build


def _class_job(reader: _ClassReader) -> Callable[[int, int], ClassReport]:
    model = _Model(_fit())

    def build(ano: int, turno: int) -> ClassReport:
        return build_governor_class(reader, model, ano, turno)

    return build


def _unused(*_args: object, **_kwargs: object) -> ProfileReport:
    raise AssertionError("build")


def _patch_profile(monkeypatch: pytest.MonkeyPatch, reader: _ProfileReader) -> None:
    monkeypatch.setattr(
        "eleicoes.use_cases.apresentar_perfis._production_reader",
        lambda: reader,
    )
    monkeypatch.setattr(
        "eleicoes.use_cases.apresentar_perfis._production_clusterer",
        lambda: _Cluster(),
    )


def _patch_class(monkeypatch: pytest.MonkeyPatch, reader: _ClassReader) -> None:
    monkeypatch.setattr(
        "eleicoes.use_cases.apresentar_classe_governador._production_reader",
        lambda: reader,
    )
    monkeypatch.setattr(
        "eleicoes.use_cases.apresentar_classe_governador._production_model",
        lambda: _Model(_fit()),
    )


def _bare_profile(*, searched: bool, silhouette: float | None) -> ProfileReport:
    return ProfileReport(
        2026,
        1,
        "senador",
        (13,),
        False,
        searched,
        silhouette,
        (ProfileGroup(1, 3, 30, (0.25,)),),
        (
            ProfileCity("1", "Alpha", 1),
            ProfileCity("2", "Beta", 1),
            ProfileCity("3", "Gama", 1),
        ),
    )


def _names(spec: dict[str, object], path: str) -> set[str]:
    paths = cast(dict[str, object], spec["paths"])
    operation = cast(dict[str, object], cast(dict[str, object], paths[path])["get"])
    parameters = cast(list[dict[str, object]], operation["parameters"])
    return {cast(str, item["name"]) for item in parameters}


def _president_lines() -> tuple[ProfileLine, ...]:
    return (
        ProfileLine("1", "Alpha", 10, 13, 6, 0, 1, 1),
        ProfileLine("1", "Alpha", 10, 22, 2, 0, 1, 1),
        ProfileLine("2", "Beta", 20, 13, 4, 0, 2, 2),
        ProfileLine("2", "Beta", 20, 22, 12, 0, 2, 2),
        ProfileLine("3", "Gama", 8, 13, 1, 0, 1, 1),
        ProfileLine("3", "Gama", 8, 22, 5, 0, 1, 1),
    )


def _senator_lines() -> tuple[ProfileLine, ...]:
    return (
        ProfileLine("1", "Alpha", 10, 13, 4, 0),
        ProfileLine("2", "Beta", 10, 13, 3, 0),
        ProfileLine("3", "Gama", 12, 13, 5, 0),
    )


def _fit() -> ClassFit:
    return ClassFit(
        "consolidacao",
        ("consolidacao", "em_aberto"),
        ("consolidacao", "em_aberto"),
        (
            ClassRule("consolidacao", (RuleCut(13, 0.5, True),)),
            ClassRule("em_aberto", ()),
        ),
    )


def _sample() -> tuple[ClassLine, ...]:
    found: list[ClassLine] = []
    for index, governor in enumerate((13, 13, 13, 44, 44, 44)):
        found.extend(_city(str(index), f"C{index}", governor))
    return tuple(found)


def _city(codigo: str, nome: str, governor: int) -> tuple[ClassLine, ...]:
    return (
        ClassLine("presidente", codigo, nome, 100, 13, 10, 0),
        ClassLine("presidente", codigo, nome, 100, 22, 4, 0),
        ClassLine("governador", codigo, nome, 80, governor, 9, 0),
    )


class _Unused:
    def __getattr__(self, name: str) -> object:
        raise AssertionError(name)


def _ports() -> ReadPorts:
    unused = _Unused()
    return ReadPorts(
        boletim=cast(AsyncBoletimReader, unused),
        names=cast(AsyncMunicipalityNames, unused),
        power_store=cast(AsyncRelatorioPoderStore, unused),
        cross_store=cast(AsyncRelatorioPresidenteGovernadorStore, unused),
    )


def _get(application: FastAPI, path: str) -> httpx.Response:
    return asyncio.run(_fetch(application, path))


async def _fetch(application: FastAPI, path: str) -> httpx.Response:
    transport = httpx.ASGITransport(app=application, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.get(path)
