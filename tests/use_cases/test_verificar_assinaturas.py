"""The signature check walks the downloaded sections and writes CSV and HTML."""

import shutil
from pathlib import Path

import pytest

from eleicoes.use_cases.verificar_assinaturas import (
    ILEGIVEL,
    SEM_ASSINATURA,
    ResultadoAssinatura,
    main,
    verificar,
    verificar_secao,
)

_PASTA = Path(__file__).resolve().parents[1] / "fixtures" / "boletins"
_NOME = "o03220ac0110400050028"


def _secao(raiz: Path, secao: str, com_vsc: bool = True) -> Path:
    pasta = raiz / "AC" / "01104" / "0005" / secao
    pasta.mkdir(parents=True)
    tipos = ["bu.dat", "rdv.dat"] + (["vota.vsc"] if com_vsc else [])
    for tipo in tipos:
        shutil.copy(_PASTA / f"{_NOME}-{tipo}", pasta / f"{_NOME}-{tipo}")
    (pasta / f"{_NOME}-imgbu.dat.ausente").write_bytes(b"")
    return pasta / f"{_NOME}-bu.dat"


def test_real_section_is_valid(tmp_path: Path) -> None:
    resultado = verificar_secao("AC", str(_secao(tmp_path, "0028")))

    assert resultado.situacao == "valida"
    assert resultado.conferencia is not None
    assert resultado.conferencia.cadeia == "verificada"


def test_missing_and_broken_signature_files(tmp_path: Path) -> None:
    sem = verificar_secao("AC", str(_secao(tmp_path, "0028", com_vsc=False)))
    quebrado = _secao(tmp_path, "0029")
    (quebrado.parent / f"{_NOME}-vota.vsc").write_bytes(b"\x30\x00")
    ilegivel = verificar_secao("AC", str(quebrado))

    assert sem.situacao == SEM_ASSINATURA
    assert ilegivel.situacao == ILEGIVEL
    assert ilegivel.erro == "InvalidSignatureFileError"


def test_changed_rdv_diverges(tmp_path: Path) -> None:
    bu = _secao(tmp_path, "0028")
    rdv = bu.parent / f"{_NOME}-rdv.dat"
    rdv.write_bytes(rdv.read_bytes() + b"\x00")

    resultado = verificar_secao("AC", str(bu))

    assert resultado.situacao == "diverge"
    assert resultado.conferencia is not None
    assert "hash_difere:rdv.dat" in resultado.conferencia.divergencias


def test_download_in_progress_is_ignored_or_reported_as_unreadable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bu = _secao(tmp_path, "0028")
    (bu.parent / f".{_NOME}-log.jez.partial").write_bytes(b"metade")
    assert verificar_secao("AC", str(bu)).situacao == "valida"

    def sumiu(self: Path) -> bytes:
        raise FileNotFoundError(str(self))

    monkeypatch.setattr(Path, "read_bytes", sumiu)
    resultado = verificar_secao("AC", str(bu))
    assert resultado.situacao == ILEGIVEL
    assert resultado.erro == "FileNotFoundError"


def test_signer_other_than_the_bu_urn_needs_the_recovery_in_the_log(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from dataclasses import replace

    from eleicoes.use_cases import verificar_assinaturas as caso

    leitores = caso._leitores()
    ler_bu = leitores.bu.read
    monkeypatch.setattr(
        leitores.bu,
        "read",
        lambda nome, dados: replace(ler_bu(nome, dados), numero_interno_urna=1841837),
    )
    bu = _secao(tmp_path, "0028")
    sem_recuperacao = verificar_secao("AC", str(bu))
    monkeypatch.setattr(caso, "_recuperadoras", lambda _log: frozenset({2295748}))
    com_recuperacao = verificar_secao("AC", str(bu))

    def quebrado(_log: Path) -> frozenset[int]:
        raise OSError

    monkeypatch.setattr(caso, "_recuperadoras", quebrado)
    ilegivel = verificar_secao("AC", str(bu))

    assert sem_recuperacao.situacao == "diverge"
    assert com_recuperacao.situacao == "valida"
    assert com_recuperacao.conferencia is not None and com_recuperacao.conferencia.recuperada
    assert ilegivel.situacao == ILEGIVEL


def test_recovery_urns_come_from_the_log_when_there_is_one(tmp_path: Path) -> None:
    from eleicoes.use_cases.verificar_assinaturas import _recuperadoras

    log = tmp_path / "log.jez"
    assert _recuperadoras(log) == frozenset()
    log.write_bytes(_log("01758779"))
    assert _recuperadoras(log) == frozenset({1758779})


def _log(urna: str) -> bytes:
    import io
    import zipfile

    linha = f"25/10/2026 21:28:01\tINFO\t{urna}\tRED\tGerando arquivo de resultado [bu.dat]\tAB"
    saida = io.BytesIO()
    with zipfile.ZipFile(saida, "w") as arquivo:
        arquivo.writestr("logd.dat", linha.encode("latin-1"))
    return saida.getvalue()


def test_two_processes_give_the_same_answer(tmp_path: Path) -> None:
    secoes = [("AC", _secao(tmp_path, "0028")), ("AC", _secao(tmp_path, "0029"))]

    resultados = verificar(secoes, 2)

    assert [item.situacao for item in resultados] == ["valida", "valida"]


def test_command_writes_csv_and_html(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    raiz = tmp_path / "downloads" / "2026" / "arquivo-urna" / "turno-1"
    _secao(raiz, "0028")
    _secao(raiz, "0029")
    _secao(raiz, "0030", com_vsc=False)
    bu = raiz / "AC" / "01104" / "0005" / "0029" / f"{_NOME}-bu.dat"
    rdv = bu.parent / f"{_NOME}-rdv.dat"
    rdv.write_bytes(b"alterado")
    (raiz / "AC" / "01104" / "0005" / "0031").mkdir()
    (raiz / "AC" / "01104" / "0005" / "0031" / f"{_NOME}-bu.dat").write_bytes(b"")
    (raiz / "AC" / "01104" / "0005" / "0031" / f"{_NOME}-vota.vsc").write_bytes(b"lixo")
    destino = tmp_path / "saida" / "assinaturas"

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
        ]
    )

    csv = destino.with_suffix(".csv").read_text(encoding="utf-8")
    html = destino.with_suffix(".html").read_text(encoding="utf-8")
    saida = capsys.readouterr().out
    assert code == 0
    assert f"AC,{_NOME},valida,22,ed521,UEAO02295748,AC UE2022,verificada,bu.dat|rdv.dat," in csv
    assert "tamanho_difere:rdv.dat|hash_difere:rdv.dat" in csv
    assert f"AC,{_NOME},sem_assinatura," in csv
    assert "InvalidSignatureFileError" in csv
    assert "Assinatura digital das urnas — 2026, 1º turno" in html
    assert "hash_difere:rdv.dat" in html
    assert "AC RAIZ UE e AC URNA v2" in html
    assert "Assinatura válida: 1, Divergem: 1, Sem vota.vsc: 1, Arquivo ilegível: 1" in saida
    assert "ms por seção" in saida


def test_html_without_problems_says_none() -> None:
    from eleicoes.use_cases.verificar_assinaturas import html_da_verificacao

    html = html_da_verificacao(
        2026, 2, [ResultadoAssinatura("AC", "x-bu.dat", None, "", "sem_assinatura")]
    )
    assert "<p>Nenhuma.</p>" in html


def test_missing_download_folder_fails(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--origem", str(tmp_path)]) == 1
    assert "Não há urnas baixadas" in capsys.readouterr().err
