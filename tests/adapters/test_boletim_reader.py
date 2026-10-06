from pathlib import Path

import pytest

from eleicoes.adapters.asn1.boletim_reader import Asn1BoletimReader
from eleicoes.domain.boletim import Boletim
from eleicoes.domain.errors import InvalidBoletimContentError, InvalidBoletimError

_FIXTURE = (
    Path(__file__).resolve().parents[1] / "fixtures" / "boletins" / "o03220ac0110400050028-bu.dat"
)
_SPEC = Path(__file__).resolve().parents[2] / "src" / "eleicoes" / "adapters" / "asn1" / "bu.asn1"
_ARQUIVO = "01104/0005/0028/o03220ac0110400050028-bu.dat"
_PRESIDENTE = {
    ("nominal", 13, 13): 82,
    ("nominal", 14, 14): 2,
    ("nominal", 22, 22): 92,
    ("nominal", 55, 55): 4,
    ("nominal", 70, 70): 12,
    ("branco", None, None): 1,
    ("nulo", None, None): 9,
}
_GOVERNADOR = {
    ("nominal", 10, 10): 69,
    ("nominal", 11, 11): 84,
    ("nominal", 40, 40): 8,
    ("nominal", 45, 45): 5,
    ("nulo", None, None): 36,
}


@pytest.fixture(scope="module")
def reader() -> Asn1BoletimReader:
    return Asn1BoletimReader()


@pytest.fixture(scope="module")
def codec() -> object:
    import asn1tools

    return asn1tools.compile_files(str(_SPEC), codec="ber")


def test_golden_section_parses_the_official_bulletin(reader: Asn1BoletimReader) -> None:
    boletim = reader.read(_ARQUIVO, _FIXTURE.read_bytes())
    assert boletim.arquivo == _ARQUIVO
    assert boletim.fase == "oficial"
    assert boletim.data_hora_emissao == "20261004T155025"
    assert (boletim.municipio, boletim.zona, boletim.local, boletim.secao) == (1104, 5, 1023, 28)
    assert boletim.versao_urna.startswith("10.23.0.0")
    assert boletim.numero_interno_urna == 2295748
    assert boletim.data_hora_carga == "20260924T085600"
    assert boletim.codigo_carga == "136568155446399692414911"
    assert boletim.codigo_midia == "ZAC001STD29"
    assert boletim.eleitores_computados == 202
    assert (boletim.indicador_habilitacao, boletim.qtd_biometria, boletim.qtd_manual) == (
        1,
        180,
        21,
    )
    _assert_election(boletim, 6257)
    _assert_election(boletim, 6259)
    assert _quantities(boletim, 6257, "presidente") == _PRESIDENTE
    assert _quantities(boletim, 6259, "governador") == _GOVERNADOR
    _assert_cargo_sum(boletim, 6257, "presidente", "majoritario", 5)
    _assert_cargo_sum(boletim, 6259, "governador", "majoritario", 4)
    senador = _one(boletim, 6259, "senador", "nominal", 555)
    assert senador.partido == 55
    assert senador.quantidade == 124
    # Two senate seats: quantities sum to twice the attendance, and every row is kept.
    assert boletim.total_for(6259, "senador") == 404
    assert boletim.lines_for(6259, "senador")[0].comparecimento_cargo == 202
    _assert_cargo_sum(boletim, 6259, "deputadoFederal", "proporcional", 1)
    _assert_cargo_sum(boletim, 6259, "deputadoEstadual", "proporcional", 2)
    assert {line.id_eleicao for line in boletim.votos} == {6257, 6259}


def test_free_cargo_keeps_the_two_election_integers(
    reader: Asn1BoletimReader,
    codec: object,
) -> None:
    boletim = reader.read("01104/0005/0028/consulta-bu.dat", _bulletin(codec))
    line = boletim.lines_for(1, "25")[0]
    assert line.tipo_cargo == "consulta"
    assert line.eleitores_aptos == 10
    assert line.qtd_comparecimento == 4
    assert line.qtd_eleitores_complemento == 6
    assert boletim.total_for(1, "25") == line.comparecimento_cargo == 4
    assert _quantities(boletim, 1, "25")[("branco", None, None)] == 1


def test_wrong_envelope_or_garbage_names_the_file(
    reader: Asn1BoletimReader,
    codec: object,
) -> None:
    arquivo = "01104/0005/0028/x-bu.dat"
    rejected = (
        b"\x00",
        _shell(codec, "simulado", "envelopeBoletimUrna", b"\x01\x02"),
        _shell(codec, "oficial", "envelopeRegistroDigitalVoto", b"\x01\x02"),
        _shell(codec, "oficial", "envelopeBoletimUrna", b""),
        _shell(codec, "oficial", "envelopeBoletimUrna", _inner(codec, fase="simulado")),
    )
    for payload in rejected:
        with pytest.raises(InvalidBoletimError) as caught:
            reader.read(arquivo, payload)
        assert caught.value.arquivo == arquivo
        assert isinstance(caught.value.__cause__, InvalidBoletimContentError)


def _assert_election(boletim: Boletim, id_eleicao: int) -> None:
    lines = [line for line in boletim.votos if line.id_eleicao == id_eleicao]
    assert lines
    assert lines[0].eleitores_aptos == 277
    assert lines[0].qtd_comparecimento == 277
    assert lines[0].qtd_eleitores_complemento == 0


def _assert_cargo_sum(boletim: Boletim, id_eleicao: int, cargo: str, tipo: str, ordem: int) -> None:
    lines = boletim.lines_for(id_eleicao, cargo)
    assert lines
    assert lines[0].tipo_cargo == tipo
    assert lines[0].ordem_impressao == ordem
    assert boletim.total_for(id_eleicao, cargo) == lines[0].comparecimento_cargo == 202


def _quantities(
    boletim: Boletim,
    id_eleicao: int,
    cargo: str,
) -> dict[tuple[str, int | None, int | None], int]:
    return {
        (line.tipo_voto, line.partido, line.numero): line.quantidade
        for line in boletim.lines_for(id_eleicao, cargo)
    }


def _one(boletim: Boletim, id_eleicao: int, cargo: str, tipo: str, numero: int) -> object:
    matches = [
        line
        for line in boletim.lines_for(id_eleicao, cargo)
        if line.tipo_voto == tipo and line.numero == numero
    ]
    assert len(matches) == 1
    return matches[0]


def _bulletin(codec: object) -> bytes:
    return _shell(codec, "oficial", "envelopeBoletimUrna", _inner(codec, fase="oficial"))


def _inner(codec: object, fase: str) -> bytes:
    return _encode(codec, "EntidadeBoletimUrna", _bulletin_body(fase))


def _shell(codec: object, fase: str, tipo: str, conteudo: bytes) -> bytes:
    return _encode(
        codec,
        "EntidadeEnvelopeGenerico",
        {
            "cabecalho": _header(),
            "fase": fase,
            "identificacao": ("identificacaoSecaoEleitoral", _section()),
            "tipoEnvelope": tipo,
            "conteudo": conteudo,
        },
    )


def _bulletin_body(fase: str) -> dict[str, object]:
    nominal = {
        "tipoVoto": "nominal",
        "quantidadeVotos": 3,
        "identificacaoVotavel": {"partido": 13, "codigo": 13},
        "ordem": 1,
        "assinatura": b"\x01",
    }
    branco = {"tipoVoto": "branco", "quantidadeVotos": 1, "ordem": 2, "assinatura": b"\x02"}
    return {
        "cabecalho": _header(),
        "fase": fase,
        "urna": _urna(),
        "identificacaoSecao": _section(),
        "dataHoraEmissao": "20261004T155025",
        "dadosSecaoSA": (
            "dadosSecao",
            {
                "dataHoraAbertura": "20261004T080000",
                "dataHoraEncerramento": "20261004T170000",
            },
        ),
        "qtdEleitoresComputados": 4,
        "resumoHabilitacao": {"indicador": 1, "qtdBiometria": 3, "qtdManual": 1},
        "resultadosVotacaoPorEleicao": [
            {
                "idEleicao": 1,
                "qtdEleitoresAptos": 10,
                "qtdComparecimento": 4,
                "qtdEleitoresExtra": 6,
                "resultadosVotacao": [
                    {
                        "tipoCargo": "consulta",
                        "qtdComparecimento": 4,
                        "totaisVotosCargo": [
                            {
                                "codigoCargo": ("numeroCargoConsultaLivre", 25),
                                "ordemImpressao": 1,
                                "votosVotaveis": [nominal, branco],
                            }
                        ],
                    }
                ],
                "assinatura": b"\x03",
                "complemento": b"\x04",
            }
        ],
        "codigoCargaRegistrado": {"codigo": "136568155446399692414911"},
    }


def _header() -> dict[str, object]:
    return {
        "dataGeracao": "20261004T155025",
        "idEleitoral": ("idEleicao", 1),
    }


def _section() -> dict[str, object]:
    return {
        "municipioZona": {"municipio": 1104, "zona": 5},
        "local": 1023,
        "secao": 28,
    }


def _urna() -> dict[str, object]:
    secao = _section()
    return {
        "tipoUrna": "secao",
        "versaoVotacao": "10.23.0.0",
        "correspondenciaResultado": {
            "identificacao": ("identificacaoSecaoEleitoral", secao),
            "carga": {
                "numeroInternoUrna": 2295748,
                "numeroSerieFC": b"\x00\x00\x00\x01",
                "origemCarga": {
                    "codigoMidia": "ZAC001STD29",
                    "resumoMidia": "ABC",
                    "complemento": "FF",
                },
                "dataHoraCarga": "20260924T085600",
                "codigoCarga": "136568155446399692414911",
            },
        },
        "tipoArquivo": "votacaoUE",
        "numeroSerieFV": b"\x00\x00\x00\x02",
    }


def _encode(codec: object, name: str, value: object) -> bytes:
    encoded = codec.encode(name, value)
    assert isinstance(encoded, bytes)
    return encoded
