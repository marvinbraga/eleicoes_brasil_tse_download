from scripts.manter_urnas_2026 import _ESPERA_SEGUNDOS, repetir


def test_supervisor_stops_when_the_download_succeeds() -> None:
    waits: list[int] = []
    notes: list[str] = []

    code = repetir(lambda: 0, waits.append, notes.append)

    assert code == 0
    assert waits == []
    assert notes == ["supervisor início", "supervisor concluído"]


def test_supervisor_retries_a_failed_download() -> None:
    results = iter((1, 0))
    waits: list[int] = []
    notes: list[str] = []

    code = repetir(lambda: next(results), waits.append, notes.append)

    assert code == 0
    assert waits == [_ESPERA_SEGUNDOS]
    assert notes == [
        "supervisor início",
        "supervisor saída=1; nova tentativa em 3 min",
        "supervisor concluído",
    ]
