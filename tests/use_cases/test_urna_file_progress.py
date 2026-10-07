"""Locked literals for one urna file's terminal line."""


def test_file_progress_line_matches_locked_literals() -> None:
    from eleicoes.use_cases import download_urnas

    line = download_urnas.file_progress_line
    assert line(801, 1000) == "[  80,1% --------.. ]"
    assert line(1000, 1000) == "[ 100,0% ---------- ]"
    assert line(1500, 1000) == "[ 100,0% ---------- ]"
    assert line(256 * 1024, None) == "[  256 KiB .......... ]"
    assert line(0, 0) == "[      0 B .......... ]"
    assert line(500, 1000) == "[  50,0% -----..... ]"


def test_byte_size_uses_1024_and_rounds_half_up() -> None:
    from eleicoes.use_cases import download_urnas

    size = download_urnas.format_byte_size
    assert size(0) == "0 B"
    assert size(1023) == "1023 B"
    assert size(1024) == "1 KiB"
    assert size(1280) == "1,3 KiB"
    assert size(1536) == "1,5 KiB"
    assert size(256 * 1024) == "256 KiB"
    assert size(int(1.2 * 1024 * 1024)) == "1,2 MiB"
    assert size(1024**2) == "1 MiB"
    assert size(1024**3) == "1 GiB"
