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
    assert "Senado: 2 de 54 vagas." in out
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


def test_main_accepts_only_the_first_round(capsys: pytest.CaptureFixture[str]) -> None:
    source = _Source()
    with pytest.raises(SystemExit) as caught:
        main(["--turno", "2"], source=source, store=_Store())
    assert caught.value.code == 2
    assert "--turno" in capsys.readouterr().err
    assert source.calls == []
