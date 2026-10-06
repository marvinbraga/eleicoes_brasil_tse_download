"""Public consultation functions. An injected reader never opens Postgres."""

from collections.abc import Sequence
from datetime import datetime

import pytest

from eleicoes.composition.correspondencia import build_correspondencia_reader
from eleicoes.consultas.correspondencia import (
    contingencias,
    correspondencias_novas,
    indicios,
    mudancas_entre_geracoes,
    rastro_da_midia,
    resumo_por_uf,
    secoes_alteradas,
    secoes_do_municipio,
)
from eleicoes.domain.correspondencia import (
    Contingencia,
    MapaDeIndicios,
    MudancaGeracao,
    ProjecaoSecao,
    ResumoUf,
    Secao,
    StatusCorrespondencia,
)
from eleicoes.domain.errors import InvalidUfError

_OLDER = datetime(2026, 10, 3, 15, 34)
_NEWER = datetime(2026, 10, 4, 12, 59)


def test_injected_reader_answers_without_postgres() -> None:
    reader = _Reader()
    match = _secao(municipio="SÃO PAULO")
    reader.sections[None] = (match, _secao(municipio="CAMPINAS"))
    reader.sections[StatusCorrespondencia.ALTERADA] = (match,)
    reader.sections[StatusCorrespondencia.NOVA] = ()
    reader.contingency_rows[None] = (_contingencia(),)
    reader.contingency_rows[StatusCorrespondencia.NOVA] = ()
    reader.summary_rows = (_resumo("AC"),)
    reader.change_rows = (_change(),)
    reader.generation_rows = (_secao(geracao_em=_NEWER), _secao(geracao_em=_OLDER))
    reader.projection_rows = (
        _projecao(secao=1),
        _projecao(secao=2),
    )

    found = secoes_do_municipio("ac", "Sao Paulo", reader=reader)
    assert found == (match,)
    assert secoes_alteradas("AC", reader=reader) == (match,)
    novas = correspondencias_novas(reader=reader)
    assert novas.secoes == ()
    assert novas.contingencias == ()
    assert resumo_por_uf(reader=reader)[0].uf == "AC"
    assert contingencias("AC", reader=reader)[0].municipio == "RIO BRANCO"
    assert mudancas_entre_geracoes(reader=reader)[0].campos_alterados == ("urna",)
    trace = rastro_da_midia("AC", "sao paulo", 8, 3, reader=reader)
    assert [item.geracao_em for item in trace] == [_OLDER, _NEWER]
    assert indicios(reader=reader) == MapaDeIndicios().avaliar(reader.projection_rows, ())
    assert ("close",) not in reader.calls


def test_invalid_uf_raises_before_the_injected_reader_is_used() -> None:
    reader = _Reader()
    with pytest.raises(InvalidUfError):
        secoes_do_municipio("XX", "RIO BRANCO", reader=reader)
    assert reader.calls == []


def test_omitted_reader_loads_the_environment_and_closes_on_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[object] = []

    class Reader:
        def secoes(self, uf: str | None, status: object) -> tuple[Secao, ...]:
            events.append(("secoes", uf, status))
            raise RuntimeError("boom")

        def close(self) -> None:
            events.append("close")

    monkeypatch.setattr(
        "eleicoes.consultas.correspondencia.load_dotenv",
        lambda: events.append("dotenv"),
    )
    monkeypatch.setattr(
        "eleicoes.consultas.correspondencia.build_correspondencia_reader",
        lambda _env: Reader(),
    )
    with pytest.raises(RuntimeError):
        secoes_do_municipio("AC", "RIO BRANCO")
    assert events == ["dotenv", ("secoes", "AC", None), "close"]


def test_invalid_uf_still_closes_the_reader_it_opened(monkeypatch: pytest.MonkeyPatch) -> None:
    events: list[str] = []

    class Reader:
        def close(self) -> None:
            events.append("close")

    monkeypatch.setattr(
        "eleicoes.consultas.correspondencia.load_dotenv",
        lambda: events.append("dotenv"),
    )
    monkeypatch.setattr(
        "eleicoes.consultas.correspondencia.build_correspondencia_reader",
        lambda _env: Reader(),
    )
    with pytest.raises(InvalidUfError):
        secoes_do_municipio("XX", "RIO BRANCO")
    assert events == ["dotenv", "close"]


def test_compose_host_uses_the_published_port_outside_the_stack(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: dict[str, str] = {}

    def connect(env: object) -> _Connection:
        assert isinstance(env, dict)
        seen.update(env)
        return _Connection()

    monkeypatch.setattr("eleicoes.composition.correspondencia.connect_postgres", connect)
    monkeypatch.setattr("eleicoes.composition.correspondencia._resolves", lambda _host: False)
    reader = build_correspondencia_reader(
        {
            "POSTGRES_HOST": "postgres",
            "POSTGRES_PORT": "5432",
            "POSTGRES_PUBLISH_PORT": "25432",
            "POSTGRES_DB": "eleicoes",
        }
    )
    assert reader.resumos() == ()
    reader.close()
    assert seen["POSTGRES_HOST"] == "127.0.0.1"
    assert seen["POSTGRES_PORT"] == "25432"


def test_compose_host_stays_on_the_internal_port_when_it_resolves(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: dict[str, str] = {}

    def connect(env: object) -> _Connection:
        assert isinstance(env, dict)
        seen.update(env)
        return _Connection()

    monkeypatch.setattr("eleicoes.composition.correspondencia.connect_postgres", connect)
    monkeypatch.setattr("eleicoes.composition.correspondencia._resolves", lambda _host: True)
    reader = build_correspondencia_reader(
        {
            "POSTGRES_HOST": "postgres",
            "POSTGRES_PORT": "5432",
            "POSTGRES_PUBLISH_PORT": "25432",
        }
    )
    assert reader.resumos() == ()
    reader.close()
    assert seen["POSTGRES_HOST"] == "postgres"
    assert seen["POSTGRES_PORT"] == "5432"


def test_reader_factory_binds_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    _Connection.closed_count = 0
    seen: dict[str, str] = {}

    def connect(env: object) -> _Connection:
        assert isinstance(env, dict)
        seen.update(env)
        return _Connection()

    monkeypatch.setattr("eleicoes.composition.correspondencia.connect_postgres", connect)
    reader = build_correspondencia_reader({"POSTGRES_DB": "eleicoes"})
    assert reader.resumos() == ()
    reader.close()
    reader.close()
    assert seen["POSTGRES_DB"] == "eleicoes"
    assert _Connection.closed_count == 1


class _Reader:
    def __init__(self) -> None:
        self.calls: list[tuple[object, ...]] = []
        self.sections: dict[StatusCorrespondencia | None, tuple[Secao, ...]] = {}
        self.contingency_rows: dict[StatusCorrespondencia | None, tuple[Contingencia, ...]] = {}
        self.summary_rows: tuple[ResumoUf, ...] = ()
        self.change_rows: tuple[MudancaGeracao, ...] = ()
        self.generation_rows: tuple[Secao, ...] = ()
        self.projection_rows: tuple[ProjecaoSecao, ...] = ()

    def secoes(self, uf: str | None, status: StatusCorrespondencia | None) -> tuple[Secao, ...]:
        self.calls.append(("secoes", uf, status))
        return self.sections.get(status, ())

    def contingencias(
        self, uf: str | None, status: StatusCorrespondencia | None
    ) -> tuple[Contingencia, ...]:
        self.calls.append(("contingencias", uf, status))
        return self.contingency_rows.get(status, ())

    def resumos(self) -> tuple[ResumoUf, ...]:
        self.calls.append(("resumos",))
        return self.summary_rows

    def mudancas(self, uf: str | None) -> tuple[MudancaGeracao, ...]:
        self.calls.append(("mudancas", uf))
        return self.change_rows

    def geracoes(self, uf: str, zona: int | None, secao: int | None) -> tuple[Secao, ...]:
        self.calls.append(("geracoes", uf, zona, secao))
        return self.generation_rows

    def projecoes(self, uf: str | None) -> tuple[ProjecaoSecao, ...]:
        self.calls.append(("projecoes", uf))
        return self.projection_rows

    def projecoes_contingencia(self, uf: str | None) -> tuple[object, ...]:
        self.calls.append(("projecoes_contingencia", uf))
        return ()

    def close(self) -> None:
        self.calls.append(("close",))


def _secao(
    *,
    municipio: str = "SÃO PAULO",
    geracao_em: datetime = _NEWER,
) -> Secao:
    return Secao(
        uf="AC",
        codigo_municipio="01392",
        municipio=municipio,
        zona=8,
        numero=3,
        local_votacao="1104",
        urna_esperada="1",
        codigo_carga="CARGA",
        flashcard="FA10805F",
        carga_em=None,
        status=StatusCorrespondencia.ALTERADA,
        maquina_geracao="MAQ",
        tpm_geracao="TPM",
        instalacao_geracao="INST",
        maquina_transmissao="MAQ",
        tpm_transmissao="TPM",
        instalacao_transmissao="INST",
        geracao_em=geracao_em,
    )


def _contingencia() -> Contingencia:
    return Contingencia(
        uf="AC",
        codigo_municipio="01392",
        municipio="RIO BRANCO",
        zona=8,
        urna_esperada="1",
        codigo_carga="CARGA",
        flashcard="FA10805F",
        carga_em=None,
        status=StatusCorrespondencia.NAO_ALTERADA,
        maquina_geracao="MAQ",
        tpm_geracao="TPM",
        instalacao_geracao="INST",
        maquina_transmissao="MAQ",
        tpm_transmissao="TPM",
        instalacao_transmissao="INST",
        geracao_em=_NEWER,
    )


def _resumo(uf: str) -> ResumoUf:
    return ResumoUf(uf, 1, 1, 1, 1, 0, 0, 0, 0)


def _change() -> MudancaGeracao:
    return MudancaGeracao(
        uf="AC",
        codigo_municipio="01392",
        municipio="RIO BRANCO",
        zona=8,
        secao=3,
        geracao_anterior=_OLDER,
        geracao_atual=_NEWER,
        urna_anterior="1",
        urna_atual="2",
        carga_anterior="A",
        carga_atual="A",
        flashcard_anterior="AA",
        flashcard_atual="AA",
        local_anterior="10",
        local_atual="10",
        maquina_anterior="M1",
        maquina_atual="M1",
    )


def _projecao(*, secao: int) -> ProjecaoSecao:
    return ProjecaoSecao(
        uf="AC",
        codigo_municipio="01392",
        municipio="RIO BRANCO",
        zona=8,
        secao=secao,
        urna=str(secao),
        carga="MESMA",
        flashcard="FA10805F",
        status=StatusCorrespondencia.NAO_ALTERADA,
        maquina_geracao="MAQ",
    )


class _Cursor:
    def execute(self, _query: str, _params: Sequence[object] | None = None) -> None:
        return None

    def fetchall(self) -> list[tuple[object, ...]]:
        return []

    def __enter__(self) -> "_Cursor":
        return self

    def __exit__(self, *args: object) -> None:
        return None


class _Connection:
    closed_count = 0

    def cursor(self) -> _Cursor:
        return _Cursor()

    def transaction(self) -> "_Connection":
        return self

    def close(self) -> None:
        _Connection.closed_count += 1

    def __enter__(self) -> "_Connection":
        return self

    def __exit__(self, *args: object) -> None:
        return None
