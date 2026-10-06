import json

import pytest

from eleicoes.adapters.urna_json import UrnaJsonReader
from eleicoes.domain.errors import UnexpectedTsePayloadError
from eleicoes.domain.values import ElectionYear, Turno, Uf

FORMAT = "Resposta do TSE fora do formato esperado."


def test_malformed_payload_uses_the_portuguese_message() -> None:
    reader = UrnaJsonReader()
    with pytest.raises(UnexpectedTsePayloadError) as caught:
        reader.read_config(b"[]")
    assert str(caught.value) == FORMAT
    with pytest.raises(UnexpectedTsePayloadError):
        reader.read_sections(b"{", Uf("AC"))
    with pytest.raises(UnexpectedTsePayloadError):
        reader.read_auxiliary(b"{}")


def test_last_downloadable_hash_ignores_rejected_statuses() -> None:
    payload = json.dumps(
        {
            "hashes": [
                {"hash": "old", "st": "Totalizado", "arq": [{"nm": "old.dat", "tp": "bu"}]},
                {"hash": "rej", "st": "Rejeitado", "arq": [{"nm": "rej.dat", "tp": "bu"}]},
                {"hash": "accent", "st": "Excluído", "arq": [{"nm": "accent.dat", "tp": "bu"}]},
                {"hash": "plain", "st": "Excluido", "arq": [{"nm": "plain.dat", "tp": "bu"}]},
                {
                    "hash": "good",
                    "st": "Totalizado",
                    "arq": [
                        {"nm": "boletim.dat", "tp": "bu"},
                        {"nm": "foto.bin", "tp": "imgbu"},
                    ],
                },
            ]
        }
    ).encode()
    selected = UrnaJsonReader().read_auxiliary(payload)
    assert selected is not None
    assert selected.digest == "good"
    assert selected.filenames == ("boletim.dat", "foto.bin")


def test_config_selects_pleito_by_cycle_and_turno() -> None:
    payload = json.dumps(
        {
            "arq": [
                {"tp": "cs", "dir": "<base>/<uf>"},
                {"tp": "aux", "dir": "<base>/<uf>/<municipio>"},
            ],
            "pl": [
                {"cd": 1111, "c": "ele2026", "e": [{"t": "2", "nm": "Segundo"}]},
                {"cd": "3220", "c": "ele2026", "e": [{"t": 1, "nm": "Primeiro"}]},
            ],
        }
    ).encode()
    config = UrnaJsonReader().read_config(payload)
    first = config.find(ElectionYear(2026), Turno(1))
    second = config.find(ElectionYear(2026), Turno(2))
    assert first is not None and first.code.value == "3220"
    assert second is not None and second.code.value == "1111"
    assert config.find(ElectionYear(2024), Turno(1)) is None


def test_section_parser_pads_codes_and_drops_aggregated_sections() -> None:
    payload = json.dumps(
        {
            "abr": [
                {
                    "cd": "AC",
                    "mu": [
                        {
                            "cd": 1392,
                            "zon": [
                                {
                                    "cd": "1",
                                    "sec": [
                                        {
                                            "ns": "3",
                                            "da": "20261004",
                                            "ha": "180000",
                                            "nsa": ["4", {"ns": "5"}],
                                        },
                                        {"ns": "0004", "da": "20261004", "ha": "180000"},
                                        {"ns": "0005", "da": "20261004", "ha": "180000"},
                                        {"ns": "0006"},
                                    ],
                                }
                            ],
                        }
                    ],
                }
            ]
        }
    ).encode()
    sections = UrnaJsonReader().read_sections(payload, Uf("AC"))
    assert [(item.address.secao.value, item.has_auxiliary) for item in sections] == [
        ("0003", True),
        ("0006", False),
    ]
    assert sections[0].address.municipio.value == "01392"
    assert sections[0].address.zona.value == "0001"
