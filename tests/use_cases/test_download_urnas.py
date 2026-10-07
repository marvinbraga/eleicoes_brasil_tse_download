import json
from collections.abc import Iterator
from io import StringIO
from pathlib import Path
from typing import TextIO

import pytest
from tests.support import FakeHttpResponse
from tests.urna_fakes import ManualClock, ManualSleeper, QueueHttp

from eleicoes.adapters.urna_index import CsvUrnaLedger
from eleicoes.adapters.urna_json import UrnaJsonReader
from eleicoes.adapters.urna_store import PartialUrnaStore
from eleicoes.domain.errors import (
    AnnouncedFilesMissingError,
    TransportError,
    TseBlockedError,
    UnexpectedHttpStatusError,
)
from eleicoes.domain.report import EXIT_NOT_PUBLISHED, EXIT_SUCCESS
from eleicoes.domain.request_pace import RequestPace
from eleicoes.domain.urna_models import UrnaDownloadCommand
from eleicoes.domain.urna_urls import CONFIG_URL
from eleicoes.domain.values import ElectionYear, Turno, Uf
from eleicoes.use_cases.download_urnas import DownloadUrnaFiles, progress_line

HASH = "65312d4970434764763677645275443244505641544f4678695966744b623941565a665876706c6d7271343d"
BU = "o03220ac0139200010003-bu.dat"
AUX_URL = (
    "https://resultados.tse.jus.br/oficial/ele2026/arquivo-urna/3220/dados/"
    "ac/01392/0001/0003/p003220-ac-m01392-z0001-s0003-aux.json"
)
FILE_URL = (
    "https://resultados.tse.jus.br/oficial/ele2026/arquivo-urna/3220/dados/"
    f"ac/01392/0001/0003/{HASH}/{BU}"
)
INDEX_URL = (
    "https://resultados.tse.jus.br/oficial/ele2026/arquivo-urna/3220/config/ac/ac-p003220-cs.json"
)
SECTION_TEMPLATE = "<base>/<ambiente>/<ciclo>/arquivo-urna/<cd_pleito>/config/<uf>"
AUX_TEMPLATE = (
    "<base>/<ambiente>/<ciclo>/arquivo-urna/<cd_pleito>/dados/<uf>/<municipio>/<zona>/<secao>"
)
BLOCKED = (
    "O TSE bloqueou o endereço por excesso de requisições. "
    "A espera de 10 minutos não liberou o acesso."
)
INTERRUPTED = (
    "Download interrompido: o TSE respondeu 404 para arquivos anunciados. "
    "Novas tentativas podem bloquear o IP."
)


def _config(pleitos: list[dict[str, object]] | None = None) -> bytes:
    body: dict[str, object] = {
        "arq": [
            {"tp": "cs", "dir": SECTION_TEMPLATE},
            {"tp": "aux", "dir": AUX_TEMPLATE},
        ],
        "pl": pleitos
        if pleitos is not None
        else [{"cd": "3220", "c": "ele2026", "dt": "20261004", "e": [{"t": 1, "nm": "Geral"}]}],
    }
    return json.dumps(body).encode()


def _index(
    sections: list[dict[str, object]],
    *,
    mu: str = "01392",
    zona: str = "0001",
    uf: str = "ac",
) -> bytes:
    body = {
        "abr": [
            {
                "cd": uf,
                "mu": [{"cd": mu, "zon": [{"cd": zona, "sec": sections}]}],
            }
        ]
    }
    return json.dumps(body).encode()


def _ready(ns: str = "0003") -> dict[str, object]:
    return {"ns": ns, "da": "20261004", "ha": "171500"}


def _hash(digest: str, status: str, names: list[str], kind: str = "bu") -> dict[str, object]:
    return {"hash": digest, "st": status, "arq": [{"nm": name, "tp": kind} for name in names]}


def _aux(hashes: list[dict[str, object]]) -> bytes:
    return json.dumps({"st": "Totalizado", "hashes": hashes}).encode()


def _rio_aux() -> bytes:
    return _aux(
        [
            _hash("old", "Totalizado", ["old.dat"]),
            _hash("rej", "Rejeitado", ["rejected.dat"]),
            _hash("exc", "Excluído", ["excluded.dat"]),
            _hash("exc2", "Excluido", ["excluded-plain.dat"]),
            _hash(HASH, "Totalizado", [BU, "o03220ac0139200010003-rdv.dat"], kind="bu"),
            _hash("later", "Rejeitado", ["later.dat"]),
        ]
    )


def _app(http: QueueHttp, sleeper: ManualSleeper | None = None) -> DownloadUrnaFiles:
    clock = sleeper.clock if sleeper is not None else ManualClock()
    waiter = sleeper if sleeper is not None else ManualSleeper(clock, http)
    return DownloadUrnaFiles(
        http=http,
        pace=RequestPace(clock, waiter),
        documents=UrnaJsonReader(),
        store=PartialUrnaStore(),
        ledger=CsvUrnaLedger(),
        sleeper=waiter,
    )


def _command(
    destination: Path,
    *,
    year: int = 2026,
    turnos: tuple[Turno, ...] = (Turno(1),),
    ufs: tuple[Uf, ...] = (Uf("AC"),),
) -> UrnaDownloadCommand:
    return UrnaDownloadCommand(
        year=ElectionYear(year),
        turnos=turnos,
        ufs=ufs,
        destination=destination,
    )


def test_progress_line_uses_ten_marks() -> None:
    assert progress_line(0) == "[   0%            ]"
    assert progress_line(50) == "[  50% -----      ]"
    assert progress_line(100) == "[ 100% ---------- ]"


def test_section_without_stamp_is_not_requested_and_rejected_hashes_are_skipped(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    http = QueueHttp(
        {
            CONFIG_URL: [(200, _config())],
            INDEX_URL: [
                (
                    200,
                    _index(
                        [
                            {"ns": "0009"},
                            {"ns": "0008", "da": "20261004"},
                            _ready(),
                        ]
                    ),
                )
            ],
            AUX_URL: [(200, _rio_aux())],
            FILE_URL: [(200, b"abc")],
            FILE_URL.replace(BU, "o03220ac0139200010003-rdv.dat"): [(200, b"rdv")],
        }
    )
    report = _app(http).execute(_command(tmp_path))
    joined = "\n".join(http.urls)
    assert "s0009" not in joined
    assert "s0008" not in joined
    assert "rejected.dat" not in joined
    assert "excluded.dat" not in joined
    assert "excluded-plain.dat" not in joined
    assert "old.dat" not in joined
    assert "later.dat" not in joined
    assert FILE_URL in http.urls
    assert report.downloaded == 2
    assert report.exit_code == EXIT_SUCCESS
    stored = tmp_path / "arquivo-urna" / "turno-1" / "AC" / "01392" / "0001" / "0003" / BU
    assert stored.read_bytes() == b"abc"
    output = capsys.readouterr().out
    assert "[   0%            ]\n" in output
    assert "[ 100% ---------- ]\n" in output


def test_unpadded_codes_keep_leading_zeros_in_the_request(tmp_path: Path) -> None:
    http = QueueHttp(
        {
            CONFIG_URL: [(200, _config())],
            INDEX_URL: [(200, _index([_ready("3")], mu="1392", zona="1"))],
            AUX_URL: [(200, _aux([_hash(HASH, "Recebido", [BU])]))],
            FILE_URL: [(200, b"abc")],
        }
    )
    _app(http).execute(_command(tmp_path))
    assert AUX_URL in http.urls
    assert FILE_URL in http.urls


def test_block_waits_ten_minutes_once_then_retries_the_same_request(
    tmp_path: Path,
) -> None:
    http = QueueHttp(
        {
            CONFIG_URL: [(429, b""), (200, _config())],
            INDEX_URL: [(200, _index([_ready()]))],
            AUX_URL: [(200, _aux([_hash(HASH, "Totalizado", [BU])]))],
            FILE_URL: [(200, b"abc")],
        }
    )
    clock = ManualClock()
    sleeper = ManualSleeper(clock, http)
    report = _app(http, sleeper).execute(_command(tmp_path))
    assert sleeper.waits == [600.0]
    assert sleeper.urls_when_sleeping == [1]
    assert http.urls[0] == CONFIG_URL
    assert http.urls[1] == CONFIG_URL
    assert http.urls[2] == INDEX_URL
    assert report.downloaded == 1


@pytest.mark.parametrize("status", [429, 403])
def test_a_second_block_aborts_without_waiting_again(tmp_path: Path, status: int) -> None:
    http = QueueHttp({CONFIG_URL: [(status, b""), (status, b"")]})
    clock = ManualClock()
    sleeper = ManualSleeper(clock, http)
    with pytest.raises(TseBlockedError) as caught:
        _app(http, sleeper).execute(_command(tmp_path))
    assert str(caught.value) == BLOCKED
    assert sleeper.waits == [600.0]
    assert sleeper.urls_when_sleeping == [1]
    assert http.urls == [CONFIG_URL, CONFIG_URL]


def test_two_announced_404s_are_missing_and_the_run_continues(tmp_path: Path) -> None:
    first = "o03220ac0139200010003-bu.dat"
    second = "o03220ac0139200010003-rdv.dat"
    third = "o03220ac0139200010003-log.jez"
    http = QueueHttp(
        {
            CONFIG_URL: [(200, _config())],
            INDEX_URL: [(200, _index([_ready()]))],
            AUX_URL: [(200, _aux([_hash(HASH, "Totalizado", [first, second, third])]))],
            _file(first): [(404, b"")],
            _file(second): [(404, b"")],
            _file(third): [(200, b"ok")],
        }
    )
    report = _app(http).execute(_command(tmp_path))
    assert report.missing == 2
    assert report.downloaded == 1
    assert report.exit_code == EXIT_SUCCESS
    text = (tmp_path / "indice-urnas.csv").read_text(encoding="utf-8")
    assert text.count(",ausente,") == 2


def test_the_third_announced_404_aborts(tmp_path: Path) -> None:
    names = [
        "o03220ac0139200010003-bu.dat",
        "o03220ac0139200010003-rdv.dat",
        "o03220ac0139200010003-log.jez",
    ]
    http = QueueHttp(
        {
            CONFIG_URL: [(200, _config())],
            INDEX_URL: [(200, _index([_ready()]))],
            AUX_URL: [(200, _aux([_hash(HASH, "Totalizado", names)]))],
            **{_file(name): [(404, b"")] for name in names},
        }
    )
    with pytest.raises(AnnouncedFilesMissingError) as caught:
        _app(http).execute(_command(tmp_path))
    assert str(caught.value) == INTERRUPTED
    text = (tmp_path / "indice-urnas.csv").read_text(encoding="utf-8")
    assert text.count(",ausente,") >= 2
    assert _file(names[0]) in http.urls
    assert _file(names[1]) in http.urls


def test_existing_file_is_skipped_without_a_request(tmp_path: Path) -> None:
    target = tmp_path / "arquivo-urna" / "turno-1" / "AC" / "01392" / "0001" / "0003" / BU
    target.parent.mkdir(parents=True)
    target.write_bytes(b"already")
    index = tmp_path / "indice.csv"
    index.write_text("original\n", encoding="utf-8")
    http = QueueHttp(
        {
            CONFIG_URL: [(200, _config())],
            INDEX_URL: [(200, _index([_ready()]))],
            AUX_URL: [(200, _aux([_hash(HASH, "Totalizado", [BU])]))],
        }
    )
    report = _app(http).execute(_command(tmp_path))
    assert AUX_URL in http.urls
    assert FILE_URL not in http.urls
    assert report.skipped == 1
    assert report.exit_code == EXIT_SUCCESS
    assert target.read_bytes() == b"already"
    assert index.read_text(encoding="utf-8") == "original\n"
    ledger = (tmp_path / "indice-urnas.csv").read_text(encoding="utf-8")
    assert ledger.splitlines()[0] == (
        "conjunto,turno,uf,municipio,zona,secao,arquivo,caminho,situacao,tamanho_bytes"
    )
    assert (
        "arquivo-urna,1,AC,01392,0001,0003,"
        "o03220ac0139200010003-bu.dat,"
        "arquivo-urna/turno-1/AC/01392/0001/0003/o03220ac0139200010003-bu.dat,"
        "ignorado,7"
    ) in ledger


def test_complete_section_is_ignored_without_waiting(tmp_path: Path) -> None:
    names = (
        "o03220ac0139200010003-bu.dat",
        "o03220ac0139200010003-log.jez",
        "o03220ac0139200010003-rdv.dat",
        "o03220ac0139200010003-vota.vsc",
    )
    folder = tmp_path / "arquivo-urna" / "turno-1" / "AC" / "01392" / "0001" / "0003"
    folder.mkdir(parents=True)
    for name in names:
        (folder / name).write_bytes(b"kept")
    http = QueueHttp(
        {
            CONFIG_URL: [(200, _config())],
            INDEX_URL: [(200, _index([_ready()]))],
        }
    )
    clock = ManualClock()
    sleeper = ManualSleeper(clock, http)
    report = _app(http, sleeper).execute(_command(tmp_path))
    assert http.urls == [CONFIG_URL, INDEX_URL]
    assert sleeper.waits == []
    assert report.skipped == 4
    assert report.downloaded == 0
    assert all((folder / name).read_bytes() == b"kept" for name in names)


def test_partial_download_does_not_leave_the_final_file_and_a_retry_does(tmp_path: Path) -> None:
    target = tmp_path / "arquivo-urna" / "turno-1" / "AC" / "01392" / "0001" / "0003" / BU
    routes = {
        CONFIG_URL: [(200, _config())],
        INDEX_URL: [(200, _index([_ready()]))],
        AUX_URL: [(200, _aux([_hash(HASH, "Totalizado", [BU])]))],
    }
    with pytest.raises(TransportError):
        _app(_ExplodingFileHttp(routes)).execute(_command(tmp_path))
    assert not target.exists()
    assert not target.with_name(f".{target.name}.partial").exists()
    http = QueueHttp({**routes, FILE_URL: [(200, b"abc")]})
    report = _app(http).execute(_command(tmp_path))
    assert report.downloaded == 1
    assert target.read_bytes() == b"abc"
    assert not target.with_name(f".{target.name}.partial").exists()


def test_success_appends_indice_urnas_and_leaves_indice_csv_alone(tmp_path: Path) -> None:
    index = tmp_path / "indice.csv"
    index.write_text("original\n", encoding="utf-8")
    http = QueueHttp(
        {
            CONFIG_URL: [(200, _config())],
            INDEX_URL: [(200, _index([_ready()]))],
            AUX_URL: [(200, _aux([_hash(HASH, "Totalizado", [BU])]))],
            FILE_URL: [(200, b"abc")],
        }
    )
    _app(http).execute(_command(tmp_path))
    assert index.read_text(encoding="utf-8") == "original\n"
    ledger = (tmp_path / "indice-urnas.csv").read_text(encoding="utf-8")
    assert (
        "arquivo-urna,1,AC,01392,0001,0003,"
        f"{BU},arquivo-urna/turno-1/AC/01392/0001/0003/{BU},baixado,3"
    ) in ledger


def test_year_without_a_matching_pleito_exits_not_published_and_skips_sections(
    tmp_path: Path,
) -> None:
    http = QueueHttp(
        {
            CONFIG_URL: [
                (
                    200,
                    _config(
                        [{"cd": "5440", "c": "ele2030", "e": [{"t": 1, "nm": "Outro"}]}],
                    ),
                )
            ]
        }
    )
    report = _app(http).execute(_command(tmp_path, year=2026))
    assert report.exit_code == EXIT_NOT_PUBLISHED
    assert http.urls == [CONFIG_URL]
    assert list(tmp_path.iterdir()) == []


def test_a_non_2026_pleito_code_is_taken_from_the_config(tmp_path: Path) -> None:
    index = "https://resultados.tse.jus.br/oficial/ele2030/arquivo-urna/5440/config/ac/ac-p005440-cs.json"
    auxiliary = (
        "https://resultados.tse.jus.br/oficial/ele2030/arquivo-urna/5440/dados/"
        "ac/01392/0001/0003/p005440-ac-m01392-z0001-s0003-aux.json"
    )
    archive = (
        "https://resultados.tse.jus.br/oficial/ele2030/arquivo-urna/5440/dados/"
        "ac/01392/0001/0003/abc/boletim.dat"
    )
    http = QueueHttp(
        {
            CONFIG_URL: [
                (200, _config([{"cd": "5440", "c": "ele2030", "e": [{"t": "1", "nm": "Geral"}]}]))
            ],
            index: [(200, _index([_ready()]))],
            auxiliary: [(200, _aux([_hash("abc", "Totalizado", ["boletim.dat"])]))],
            archive: [(200, b"zz")],
        }
    )
    report = _app(http).execute(_command(tmp_path, year=2030))
    assert archive in http.urls
    assert "3220" not in "\n".join(http.urls)
    assert report.downloaded == 1


def test_only_the_published_turno_is_downloaded(tmp_path: Path) -> None:
    http = QueueHttp(
        {
            CONFIG_URL: [(200, _config())],
            INDEX_URL: [(200, _index([_ready()]))],
            AUX_URL: [(200, _aux([_hash(HASH, "Totalizado", [BU])]))],
            FILE_URL: [(200, b"abc")],
        }
    )
    report = _app(http).execute(_command(tmp_path, turnos=(Turno(1), Turno(2))))
    assert report.downloaded == 1
    assert report.unpublished_turnos == (2,)
    assert report.exit_code == EXIT_SUCCESS
    assert all("/3220/" in url or url == CONFIG_URL for url in http.urls)


def test_no_ready_section_is_not_published(tmp_path: Path) -> None:
    http = QueueHttp(
        {
            CONFIG_URL: [(200, _config())],
            INDEX_URL: [(200, _index([{"ns": "0003"}]))],
        }
    )
    report = _app(http).execute(_command(tmp_path))
    assert report.exit_code == EXIT_NOT_PUBLISHED
    assert http.urls == [CONFIG_URL, INDEX_URL]


def test_three_missing_uf_indexes_abort_without_guessing_sections(tmp_path: Path) -> None:
    indexes = [
        (
            "https://resultados.tse.jus.br/oficial/ele2026/arquivo-urna/3220/config/"
            f"{uf.lower()}/{uf.lower()}-p003220-cs.json"
        )
        for uf in ("AC", "AL", "AM")
    ]
    http = QueueHttp({CONFIG_URL: [(200, _config())], **{url: [(404, b"")] for url in indexes}})
    with pytest.raises(AnnouncedFilesMissingError):
        _app(http).execute(_command(tmp_path, ufs=(Uf("AC"), Uf("AL"), Uf("AM"))))
    assert http.urls == [CONFIG_URL, *indexes]


def test_http_500_does_not_create_the_final_file(tmp_path: Path) -> None:
    http = QueueHttp(
        {
            CONFIG_URL: [(200, _config())],
            INDEX_URL: [(200, _index([_ready()]))],
            AUX_URL: [(200, _aux([_hash(HASH, "Totalizado", [BU])]))],
            FILE_URL: [(500, b"erro")],
        }
    )
    with pytest.raises(UnexpectedHttpStatusError):
        _app(http).execute(_command(tmp_path))
    assert list(tmp_path.rglob("*.dat")) == []
    assert list(tmp_path.rglob("*.partial")) == []


def test_aggregated_section_is_not_requested(tmp_path: Path) -> None:
    aggregated = (
        "https://resultados.tse.jus.br/oficial/ele2026/arquivo-urna/3220/dados/"
        "ac/01392/0001/0004/p003220-ac-m01392-z0001-s0004-aux.json"
    )
    http = QueueHttp(
        {
            CONFIG_URL: [(200, _config())],
            INDEX_URL: [
                (
                    200,
                    _index(
                        [
                            {"ns": "0003", "da": "20261004", "ha": "171500", "nsa": ["0004"]},
                            {"ns": "0004", "da": "20261004", "ha": "171500"},
                        ]
                    ),
                )
            ],
            AUX_URL: [(200, _aux([_hash(HASH, "Totalizado", [BU])]))],
            FILE_URL: [(200, b"abc")],
        }
    )
    _app(http).execute(_command(tmp_path))
    assert aggregated not in http.urls
    assert AUX_URL in http.urls


def _file(name: str) -> str:
    return (
        "https://resultados.tse.jus.br/oficial/ele2026/arquivo-urna/3220/dados/"
        f"ac/01392/0001/0003/{HASH}/{name}"
    )


class _ExplodingBody:
    def iter_chunks(self, chunk_size: int) -> Iterator[bytes]:
        del chunk_size
        yield b"parcial"
        raise OSError("disco cheio")

    def read_bytes(self) -> bytes:
        return b""

    def close(self) -> None:
        return None


class _ExplodingResponse:
    status_code = 200
    content_length: int | None = None

    def __init__(self) -> None:
        self.body = _ExplodingBody()


class _ExplodingFileHttp(QueueHttp):
    def get(self, url: str) -> FakeHttpResponse | _ExplodingResponse:
        if url == FILE_URL:
            self.urls.append(url)
            return _ExplodingResponse()
        return super().get(url)


RDV = "o03220ac0139200010003-rdv.dat"
_SECTION = "AC 01392  zona 0001  seção 0003"


class _TtyBuffer(StringIO):
    def isatty(self) -> bool:
        return True


class _LengthHttp(QueueHttp):
    def __init__(
        self,
        routes: dict[str, list[tuple[int, bytes]]],
        length: int | None,
    ) -> None:
        super().__init__(routes)
        self._length = length

    def get(self, url: str) -> FakeHttpResponse:
        response = super().get(url)
        if url == FILE_URL:
            response.content_length = self._length
        return response


def _lines(output: str) -> list[str]:
    return output.replace("\r", "\n").splitlines()


def _finished(output: str, label: str, name: str, size: str | None = None) -> bool:
    expected = f"[{label}] {name}" if size is None else f"[{label}] {name}  {size}"
    return any(line.rstrip(" ") == expected for line in _lines(output))


def _watching(http: QueueHttp, output: TextIO) -> DownloadUrnaFiles:
    clock = ManualClock()
    waiter = ManualSleeper(clock, http)
    return DownloadUrnaFiles(
        http=http,
        pace=RequestPace(clock, waiter),
        documents=UrnaJsonReader(),
        store=PartialUrnaStore(),
        ledger=CsvUrnaLedger(),
        sleeper=waiter,
        output=output,
    )


def test_tty_download_rewrites_one_line_and_finishes_with_the_size(tmp_path: Path) -> None:
    payload = b"a" * 1000
    http = _LengthHttp(
        {
            CONFIG_URL: [(200, _config())],
            INDEX_URL: [(200, _index([_ready()]))],
            AUX_URL: [(200, _aux([_hash(HASH, "Totalizado", [BU])]))],
            FILE_URL: [(200, payload)],
        },
        len(payload),
    )
    screen = _TtyBuffer()
    _watching(http, screen).execute(_command(tmp_path))
    output = screen.getvalue()
    assert "\r" in output
    assert output.count("\r") >= 2
    assert "[  50,0% -----..... ]" in output
    assert f"[  50,0% -----..... ] {BU}" in output
    assert "[baixando]" not in output
    assert "arquivo-urna/turno-1" not in output
    assert _finished(output, "baixado", BU, "1000 B")
    assert output.count(f"{_SECTION}\n") == 1
    ledger = (tmp_path / "indice-urnas.csv").read_text(encoding="utf-8")
    assert f"arquivo-urna/turno-1/AC/01392/0001/0003/{BU},baixado,1000" in ledger


def test_non_tty_prints_the_section_once_and_only_the_final_line(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    http = QueueHttp(
        {
            CONFIG_URL: [(200, _config())],
            INDEX_URL: [(200, _index([_ready()]))],
            AUX_URL: [(200, _aux([_hash(HASH, "Totalizado", [BU, RDV])]))],
            _file(BU): [(200, b"abc")],
            _file(RDV): [(200, b"rdv")],
        }
    )
    _app(http).execute(_command(tmp_path))
    output = capsys.readouterr().out
    assert "\r" not in output
    assert "[baixando]" not in output
    assert ".........." not in output
    assert "," not in output
    assert output.count(f"{_SECTION}\n") == 1
    assert output.count(f"[baixado] {BU}  3 B\n") == 1
    assert output.count(f"[baixado] {RDV}  3 B\n") == 1
    ledger = (tmp_path / "indice-urnas.csv").read_text(encoding="utf-8")
    assert f"arquivo-urna/turno-1/AC/01392/0001/0003/{BU},baixado,3" in ledger
    assert f"arquivo-urna/turno-1/AC/01392/0001/0003/{RDV},baixado,3" in ledger


def test_tty_without_content_length_shows_received_size_not_percent(tmp_path: Path) -> None:
    payload = b"x" * (256 * 1024)
    http = _LengthHttp(
        {
            CONFIG_URL: [(200, _config())],
            INDEX_URL: [(200, _index([_ready()]))],
            AUX_URL: [(200, _aux([_hash(HASH, "Totalizado", [BU])]))],
            FILE_URL: [(200, payload)],
        },
        None,
    )
    screen = _TtyBuffer()
    _watching(http, screen).execute(_command(tmp_path))
    output = screen.getvalue()
    assert "[baixando]" not in output
    assert "\r" in output
    pieces = [piece for piece in output.split("\r") if ".........." in piece]
    assert pieces
    assert all("%" not in piece for piece in pieces)
    assert all("KiB" in piece or " B" in piece for piece in pieces)
    assert _finished(output, "baixado", BU, "256 KiB")
    assert output.count(f"{_SECTION}\n") == 1


def test_stream_without_isatty_still_prints_only_the_final_line(tmp_path: Path) -> None:
    class _Log:
        def __init__(self) -> None:
            self.parts: list[str] = []

        def write(self, text: str) -> int:
            self.parts.append(text)
            return len(text)

        def flush(self) -> None:
            return None

    http = QueueHttp(
        {
            CONFIG_URL: [(200, _config())],
            INDEX_URL: [(200, _index([_ready()]))],
            AUX_URL: [(200, _aux([_hash(HASH, "Totalizado", [BU])]))],
            FILE_URL: [(200, b"abc")],
        }
    )
    screen = _Log()
    _watching(http, screen).execute(_command(tmp_path))  # type: ignore[arg-type]
    output = "".join(screen.parts)
    assert "\r" not in output
    assert "[baixando]" not in output
    assert output.count(f"{_SECTION}\n") == 1
    assert f"[baixado] {BU}  3 B\n" in output


def test_ignored_and_absent_lines_have_no_bar(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    target = tmp_path / "arquivo-urna" / "turno-1" / "AC" / "01392" / "0001" / "0003" / BU
    target.parent.mkdir(parents=True)
    target.write_bytes(b"already")
    http = QueueHttp(
        {
            CONFIG_URL: [(200, _config())],
            INDEX_URL: [(200, _index([_ready()]))],
            AUX_URL: [(200, _aux([_hash(HASH, "Totalizado", [BU, RDV])]))],
            _file(RDV): [(404, b"")],
        }
    )
    _app(http).execute(_command(tmp_path))
    output = capsys.readouterr().out
    assert f"[ignorado] {BU}\n" in output
    assert f"[ausente] {RDV}\n" in output
    assert output.count(f"{_SECTION}\n") == 1
    assert "[baixando]" not in output
    for line in output.splitlines():
        if line.startswith("[ignorado]") or line.startswith("[ausente]"):
            assert "%" not in line
            assert ".." not in line
            assert "  " not in line
    ledger = (tmp_path / "indice-urnas.csv").read_text(encoding="utf-8")
    assert f"arquivo-urna/turno-1/AC/01392/0001/0003/{BU},ignorado,7" in ledger
    assert f"arquivo-urna/turno-1/AC/01392/0001/0003/{RDV},ausente," in ledger
