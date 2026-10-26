import pytest
from scripts.baixar_urnas_2026 import RAIZ, ler_turno, pasta_logs


def test_turno_defaults_to_the_first_round() -> None:
    assert ler_turno([]) == "1"


def test_turno_accepts_the_second_round() -> None:
    assert ler_turno(["--turno", "2"]) == "2"


def test_turno_rejects_an_unknown_round() -> None:
    with pytest.raises(SystemExit):
        ler_turno(["--turno", "3"])


def test_first_round_keeps_the_original_log_folder() -> None:
    assert pasta_logs("1") == RAIZ / "logs" / "urnas-2026"


def test_second_round_logs_to_its_own_folder() -> None:
    assert pasta_logs("2") == RAIZ / "logs" / "urnas-2026-turno-2"
