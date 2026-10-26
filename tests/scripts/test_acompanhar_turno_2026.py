from pathlib import Path

import pytest
from scripts.acompanhar_turno_2026 import (
    Fim,
    Importada,
    Passada,
    acompanhar,
    assinatura,
    completo,
    ler_fins,
    ler_importadas,
    ler_opcoes,
    pendentes,
    rodar_com_log,
)

from eleicoes.domain.values import UF_CODES

_RESUMO = """\
2026-10-26 10:39:08 supervisor início
2026-10-26 10:39:08 início ano=2026 turno=2 ufs=28
2026-10-26 10:39:08 logs em /tmp/urnas-2026-turno-2
2026-10-26 10:39:08 início AC
2026-10-26 10:41:37 fim AC saída=0
2026-10-26 10:41:37 início AL
2026-10-26 10:49:10 fim AL saída=3
2026-10-26 10:49:10 início AM
2026-10-26 10:58:47 fim AM saída=0
2026-10-26 10:58:47 início AP
"""


def test_only_uf_whose_last_event_is_a_clean_end_is_ready() -> None:
    fins = ler_fins(_RESUMO)
    assert fins == {
        "AC": Fim("AC", "2026-10-26 10:41:37"),
        "AM": Fim("AM", "2026-10-26 10:58:47"),
    }


def test_new_start_after_the_end_takes_the_uf_out() -> None:
    texto = _RESUMO + "2026-10-26 12:00:00 início AC\n"
    assert "AC" not in ler_fins(texto)
    again = texto + "2026-10-26 12:01:00 fim AC saída=0\n"
    assert ler_fins(again)["AC"] == Fim("AC", "2026-10-26 12:01:00")


def test_last_import_line_of_each_uf_wins() -> None:
    texto = (
        "2026-10-26 11:00:00 AC fim=2026-10-26 10:41:37 boletins=10 ausentes=0\n"
        "lixo\n"
        "2026-10-26 13:00:00 AC fim=2026-10-26 12:01:00 boletins=11 ausentes=0\n"
    )
    assert ler_importadas(texto) == {
        "AC": Importada("AC", "2026-10-26 12:01:00", "boletins=11 ausentes=0")
    }


def test_pending_keeps_the_download_order_and_skips_consumed_ends() -> None:
    fins = {
        "AM": Fim("AM", "2026-10-26 10:58:47"),
        "AC": Fim("AC", "2026-10-26 10:41:37"),
        "ZZ": Fim("ZZ", "2026-10-26 15:00:00"),
    }
    importadas = {
        "AC": Importada("AC", "2026-10-26 10:41:37", "boletins=1 ausentes=0"),
        "AM": Importada("AM", "2026-10-26 09:00:00", "boletins=1 ausentes=2"),
    }
    assert pendentes(fins, importadas) == (fins["AM"], fins["ZZ"])


def test_complete_needs_every_uf_and_the_exterior() -> None:
    todas = {uf: Importada(uf, "2026-10-26 10:00:00", "x") for uf in UF_CODES}
    assert "ZZ" in todas
    assert completo(todas, ()) is True
    assert completo(todas, (Fim("AC", "2026-10-26 11:00:00"),)) is False
    sem_exterior = {uf: item for uf, item in todas.items() if uf != "ZZ"}
    assert completo(sem_exterior, ()) is False


def test_signature_counts_bulletins_and_absent_marks(tmp_path: Path) -> None:
    assert assinatura(tmp_path / "falta") == "boletins=0 ausentes=0"
    secao = tmp_path / "1" / "2" / "3"
    secao.mkdir(parents=True)
    (secao / "a-bu.dat").write_bytes(b"x")
    (secao / "b-bu.dat").write_bytes(b"x")
    (secao / "c.rdv").write_bytes(b"x")
    (secao / "d-bu.dat.ausente").write_text("", encoding="utf-8")
    assert assinatura(tmp_path) == "boletins=2 ausentes=1"


class _Mundo:
    """Pasta de logs falsa, importação e assinatura controladas pelo teste."""

    def __init__(self, pasta: Path, resumo: str) -> None:
        self.pasta = pasta
        (pasta / "resumo.log").write_text(resumo, encoding="utf-8")
        self.codigos: dict[str, int] = {}
        self.arquivos: dict[str, str] = {}
        self.importadas: list[str] = []
        self.notas: list[str] = []

    def importar(self, uf: str) -> int:
        self.importadas.append(uf)
        return self.codigos.get(uf, 0)

    def assinar(self, uf: str) -> str:
        return self.arquivos.get(uf, "boletins=1 ausentes=0")

    def passada(self) -> Passada:
        return Passada(
            self.pasta,
            self.importar,
            self.assinar,
            self.notas.append,
            lambda: "2026-10-26 20:00:00",
        )

    def acrescentar(self, linha: str) -> None:
        with (self.pasta / "resumo.log").open("a", encoding="utf-8") as resumo:
            resumo.write(linha + "\n")


def test_pass_imports_new_ufs_and_records_them(tmp_path: Path) -> None:
    mundo = _Mundo(tmp_path, _RESUMO)
    passada = mundo.passada()

    assert passada(set()) == 2
    assert mundo.importadas == ["AC", "AM"]
    log = (tmp_path / "importados.log").read_text(encoding="utf-8")
    assert log.splitlines() == [
        "2026-10-26 20:00:00 AC fim=2026-10-26 10:41:37 boletins=1 ausentes=0",
        "2026-10-26 20:00:00 AM fim=2026-10-26 10:58:47 boletins=1 ausentes=0",
    ]

    assert passada(set()) == 0
    assert mundo.importadas == ["AC", "AM"]


def test_redownload_with_new_files_imports_again(tmp_path: Path) -> None:
    mundo = _Mundo(tmp_path, _RESUMO)
    passada = mundo.passada()
    mundo.arquivos["AM"] = "boletins=10 ausentes=2"
    passada(set())

    mundo.acrescentar("2026-10-26 18:00:00 início AM")
    mundo.acrescentar("2026-10-26 18:05:00 fim AM saída=0")
    mundo.arquivos["AM"] = "boletins=12 ausentes=0"
    assert passada(set()) == 1
    assert mundo.importadas == ["AC", "AM", "AM"]


def test_redownload_without_new_files_only_records_the_end(tmp_path: Path) -> None:
    mundo = _Mundo(tmp_path, _RESUMO)
    passada = mundo.passada()
    passada(set())

    mundo.acrescentar("2026-10-26 18:00:00 início AC")
    mundo.acrescentar("2026-10-26 18:05:00 fim AC saída=0")
    assert passada(set()) == 0
    assert mundo.importadas == ["AC", "AM"]
    assert "AC sem arquivos novos (boletins=1 ausentes=0)" in mundo.notas
    assert ler_importadas((tmp_path / "importados.log").read_text(encoding="utf-8"))["AC"].fim == (
        "2026-10-26 18:05:00"
    )


def test_failed_import_is_not_recorded_nor_retried_for_the_same_end(tmp_path: Path) -> None:
    mundo = _Mundo(tmp_path, _RESUMO)
    mundo.codigos["AC"] = 1
    passada = mundo.passada()
    tentadas: set[Fim] = set()

    assert passada(tentadas) == 1
    assert passada(tentadas) == 0
    assert mundo.importadas == ["AC", "AM"]
    assert "falha ao importar AC saída=1" in mundo.notas
    assert "AC" not in ler_importadas((tmp_path / "importados.log").read_text(encoding="utf-8"))

    mundo.codigos["AC"] = 0
    mundo.acrescentar("2026-10-26 19:00:00 início AC")
    mundo.acrescentar("2026-10-26 19:30:00 fim AC saída=0")
    assert passada(tentadas) == 1
    assert mundo.importadas == ["AC", "AM", "AC"]


def test_missing_logs_mean_nothing_to_do(tmp_path: Path) -> None:
    mundo = _Mundo(tmp_path, "")
    (tmp_path / "resumo.log").unlink()
    assert mundo.passada()(set()) == 0
    assert mundo.importadas == []


def test_loop_renders_once_per_batch_and_sleeps_between_passes(tmp_path: Path) -> None:
    mundo = _Mundo(tmp_path, _RESUMO)
    mapas: list[str] = []
    esperas: list[int] = []

    def esperar(segundos: int) -> None:
        esperas.append(segundos)
        if len(esperas) == 2:
            raise KeyboardInterrupt

    def gerar_mapa() -> int:
        mapas.append("mapa")
        return 0

    with pytest.raises(KeyboardInterrupt):
        acompanhar(mundo.passada(), gerar_mapa, esperar, 30)

    assert mundo.importadas == ["AC", "AM"]
    assert mapas == ["mapa"]
    assert esperas == [30, 30]
    assert "mapa saída=0" in mundo.notas


def test_single_pass_does_not_sleep(tmp_path: Path) -> None:
    mundo = _Mundo(tmp_path, _RESUMO)
    esperas: list[int] = []
    code = acompanhar(mundo.passada(), lambda: 0, esperas.append, 120, uma_vez=True)
    assert code == 0
    assert esperas == []
    assert mundo.importadas == ["AC", "AM"]


def test_loop_without_new_imports_does_not_render(tmp_path: Path) -> None:
    mundo = _Mundo(tmp_path, "")
    mapas: list[int] = []
    acompanhar(mundo.passada(), lambda: mapas.append(1) or 0, lambda _s: None, 1, uma_vez=True)
    assert mapas == []


def test_loop_stops_when_every_uf_is_imported(tmp_path: Path) -> None:
    linhas = [f"2026-10-26 10:00:00 fim {uf} saída=0" for uf in UF_CODES]
    mundo = _Mundo(tmp_path, "\n".join(linhas) + "\n")
    esperas: list[int] = []
    mapas: list[int] = []

    code = acompanhar(mundo.passada(), lambda: mapas.append(1) or 0, esperas.append, 120)

    assert code == 0
    assert esperas == []
    assert mapas == [1]
    assert mundo.importadas == list(UF_CODES)
    assert mundo.notas[-1] == "concluído: 28 UFs importadas"


def test_run_with_log_turns_errors_into_exit_codes(tmp_path: Path) -> None:
    arquivo = tmp_path / "importar-AC.log"

    def explode() -> int:
        raise RuntimeError("banco fora")

    def sai() -> int:
        raise SystemExit(2)

    def diz() -> int:
        print("Boletins gravados: 3.")
        return 0

    assert rodar_com_log(arquivo, explode, "AC") == 1
    assert rodar_com_log(arquivo, sai, "AC") == 2
    assert rodar_com_log(arquivo, diz, "AC") == 0
    texto = arquivo.read_text(encoding="utf-8")
    assert "RuntimeError('banco fora')" in texto
    assert "Boletins gravados: 3." in texto
    assert "fim AC saída=2" in texto


def test_options_default_to_120_seconds_and_reject_zero() -> None:
    padrao = ler_opcoes([])
    assert (padrao.intervalo, padrao.uma_vez) == (120, False)
    escolhido = ler_opcoes(["--intervalo", "300", "--uma-vez"])
    assert (escolhido.intervalo, escolhido.uma_vez) == (300, True)
    with pytest.raises(SystemExit):
        ler_opcoes(["--intervalo", "0"])
