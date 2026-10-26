"""The urn check walks the downloaded sections and writes CSV and HTML."""

import shutil
from pathlib import Path

import pytest

from eleicoes.domain.integridade_urna import CONFERE, DIVERGE, Conferencia
from eleicoes.use_cases.verificar_urnas import ResultadoSecao, main, verificar_secao

_PASTA = Path(__file__).resolve().parents[1] / "fixtures" / "boletins"
_NOME = "o03220ac0110400050028"


def test_command_writes_csv_and_html_for_each_section(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    raiz = tmp_path / "downloads" / "2026" / "arquivo-urna" / "turno-1"
    for secao in ("0028", "0029"):
        pasta = raiz / "AC" / "01104" / "0005" / secao
        pasta.mkdir(parents=True)
        (pasta / f"{_NOME}-bu.dat").write_bytes(b"")

    def falsa(uf: str, caminho: str) -> ResultadoSecao:
        secao = int(Path(caminho).parent.name)
        situacao = CONFERE if secao == 28 else DIVERGE
        divergencias = () if secao == 28 else ("rdv_difere:presidente",)
        return ResultadoSecao(
            uf, caminho, Conferencia(1104, 5, secao, 7, situacao, divergencias, secao == 28)
        )

    destino = tmp_path / "saida" / "integridade"
    code = main(
        [
            "--turno",
            "1",
            "--origem",
            str(tmp_path / "downloads"),
            "--processos",
            "1",
            "--destino",
            str(destino),
        ],
        verificar_uma=falsa,
    )

    csv = destino.with_suffix(".csv").read_text(encoding="utf-8")
    html = destino.with_suffix(".html").read_text(encoding="utf-8")
    assert code == 0
    assert "AC,1104,5,28,7,confere,sim," in csv
    assert "AC,1104,5,29,7,diverge,,rdv_difere:presidente" in csv
    assert "Integridade das urnas — 2026, 1º turno" in html
    assert "rdv_difere:presidente" in html
    assert "Conferem: 1, Divergem: 1" in capsys.readouterr().out


def test_missing_download_folder_fails(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--origem", str(tmp_path)]) == 1
    assert "Não há urnas baixadas" in capsys.readouterr().err


def test_real_section_without_log_is_reported_as_such(tmp_path: Path) -> None:
    pasta = tmp_path / "AC" / "01104" / "0005" / "0028"
    pasta.mkdir(parents=True)
    for sufixo in ("bu", "rdv"):
        shutil.copy(_PASTA / f"{_NOME}-{sufixo}.dat", pasta / f"{_NOME}-{sufixo}.dat")

    resultado = verificar_secao("AC", str(pasta / f"{_NOME}-bu.dat"))

    assert resultado.conferencia is not None
    assert resultado.situacao == "sem_log"


def test_unreadable_bulletin_is_reported(tmp_path: Path) -> None:
    caminho = tmp_path / f"{_NOME}-bu.dat"
    caminho.write_bytes(b"lixo")

    resultado = verificar_secao("AC", str(caminho))

    assert resultado.situacao == "ilegivel"
    assert resultado.erro
