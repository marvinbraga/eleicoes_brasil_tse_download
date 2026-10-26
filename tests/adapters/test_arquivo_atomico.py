"""Atomic report writes never leave a half-written file behind."""

from pathlib import Path

import pytest

from eleicoes.adapters.arquivo_atomico import gravar_texto


def test_writes_and_replaces_without_leftovers(tmp_path: Path) -> None:
    destino = tmp_path / "relatorios" / "mapa.html"

    gravar_texto(destino, "primeiro")
    gravar_texto(destino, "segundo")

    assert destino.read_text(encoding="utf-8") == "segundo"
    assert [p.name for p in destino.parent.iterdir()] == ["mapa.html"]
    assert destino.stat().st_mode & 0o777 == 0o644


def test_failed_write_keeps_the_old_file(tmp_path: Path) -> None:
    destino = tmp_path / "mapa.html"
    gravar_texto(destino, "antigo")

    with pytest.raises(UnicodeEncodeError):
        gravar_texto(destino, "\udc80")

    assert destino.read_text(encoding="utf-8") == "antigo"
    assert [p.name for p in tmp_path.iterdir()] == ["mapa.html"]
