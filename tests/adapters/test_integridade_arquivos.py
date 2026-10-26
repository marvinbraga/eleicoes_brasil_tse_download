"""The RDV and log readers against a real 2026 section and synthetic logs."""

import io
import itertools
import zipfile
from pathlib import Path

import pytest

from eleicoes.adapters.asn1.boletim_reader import Asn1BoletimReader
from eleicoes.adapters.asn1.rdv_reader import Asn1RdvReader
from eleicoes.adapters.log_urna import dia_do_boletim, resumo_do_log
from eleicoes.domain.errors import InvalidBoletimContentError
from eleicoes.domain.integridade_urna import CONFERE, ResumoLog, conferir

_PASTA = Path(__file__).resolve().parents[1] / "fixtures" / "boletins"
_BU = _PASTA / "o03220ac0110400050028-bu.dat"
_RDV = _PASTA / "o03220ac0110400050028-rdv.dat"
_DIA = "04/10/2026"
_URNA = "02295748"


def test_real_rdv_recounts_every_office_exactly_like_its_bulletin() -> None:
    boletim = Asn1BoletimReader().read(_BU.name, _BU.read_bytes())
    rdv = Asn1RdvReader().read(_RDV.read_bytes())
    log = ResumoLog(
        boletim.eleitores_computados,
        {"presidente": boletim.eleitores_computados, "governador": boletim.eleitores_computados},
        frozenset({_URNA}),
    )

    conferencia = conferir(boletim, rdv, log)

    assert (rdv.municipio, rdv.zona, rdv.secao, rdv.numero_interno_urna) == (1104, 5, 28, 2295748)
    assert set(rdv.cargos) >= {"presidente", "governador", "deputadoFederal"}
    assert conferencia.situacao == CONFERE, conferencia.detalhes


def test_rdv_legend_votes_keep_only_the_party_digits() -> None:
    rdv = Asn1RdvReader().read(_RDV.read_bytes())

    assert all(numero < 100 for tipo, numero in rdv.cargos["deputadoFederal"] if tipo == "legenda")


def test_garbage_rdv_is_a_content_error() -> None:
    with pytest.raises(InvalidBoletimContentError):
        Asn1RdvReader().read(b"\x30\x03\x02\x01\x01")


def test_log_counts_only_votes_that_were_computed_on_election_day() -> None:
    linhas = [
        _evento("03/10/2026", "O voto do eleitor foi computado"),
        _evento(_DIA, "Eleitor foi habilitado"),
        _evento(_DIA, "Voto confirmado para [Governador]"),
        _evento(_DIA, "Voto confirmado para [Presidente]"),
        _evento(_DIA, "O voto do eleitor foi computado"),
        _evento(_DIA, "Eleitor foi habilitado"),
        _evento(_DIA, "Voto confirmado para [Governador]"),
        _evento(_DIA, "Atribuido voto nulo por suspensão [Presidente]"),
        _evento(_DIA, "O voto do eleitor foi computado"),
        _evento(_DIA, "Eleitor foi habilitado"),
        _evento(_DIA, "Voto confirmado para [Governador]"),
        _evento(_DIA, "Urna desligada pela chave"),
    ]

    resumo = resumo_do_log(_zip({"logd.dat": "\n".join(linhas)}), _DIA)

    assert resumo.computados == 2
    assert resumo.votos_por_cargo == {"presidente": 2, "governador": 2}
    assert resumo.urnas == frozenset({_URNA})
    assert resumo.logs == 1


def test_replaced_urn_log_is_read_from_the_nested_zip() -> None:
    anterior = _zip({"logd.dat": _evento(_DIA, "O voto do eleitor foi computado", "00000001")})

    atual = _evento(_DIA, "O voto do eleitor foi computado")

    resumo = resumo_do_log(_zip({"anterior.jez": anterior, "logd.dat": atual}), _DIA)

    assert resumo.computados == 2
    assert resumo.logs == 2
    assert resumo.urnas == frozenset({_URNA, "00000001"})


def test_broken_log_and_bad_date_are_content_errors() -> None:
    with pytest.raises(InvalidBoletimContentError):
        resumo_do_log(b"not a zip", _DIA)
    with pytest.raises(InvalidBoletimContentError):
        dia_do_boletim("T1")
    assert dia_do_boletim("20261025T150214") == "25/10/2026"


_RESUMOS = itertools.count()


def _evento(dia: str, texto: str, urna: str = _URNA) -> str:
    """Cada linha real do log termina num resumo próprio; o contador faz o mesmo."""
    return f"{dia} 10:00:00\tINFO\t{urna}\tVOTA\t{texto}\t{next(_RESUMOS):016X}"


def _zip(membros: dict[str, str | bytes]) -> bytes:
    saida = io.BytesIO()
    with zipfile.ZipFile(saida, "w") as arquivo:
        for nome, conteudo in membros.items():
            dado = conteudo.encode("latin-1") if isinstance(conteudo, str) else conteudo
            arquivo.writestr(nome, dado)
    return saida.getvalue()


def test_power_loss_right_after_the_last_office_is_counted_apart() -> None:
    linhas = [
        _evento(_DIA, "Eleitor foi habilitado"),
        _evento(_DIA, "Voto confirmado para [Presidente]"),
        _evento(_DIA, "Início das operações do logd"),
        _evento(_DIA, "Eleitor foi habilitado"),
        _evento(_DIA, "Voto confirmado para [Governador]"),
        _evento(_DIA, "Início das operações do logd"),
    ]

    resumo = resumo_do_log(_zip({"logd.dat": "\n".join(linhas)}), _DIA)

    assert resumo.computados == 0
    assert resumo.interrompidos == 1
    assert resumo.contagens() == (0, 1)


def test_repeated_log_lines_are_the_same_event() -> None:
    computado = _evento(_DIA, "O voto do eleitor foi computado")
    texto = "\n".join([_evento(_DIA, "Eleitor foi habilitado"), computado, computado])

    assert resumo_do_log(_zip({"logd.dat": texto}), _DIA).computados == 1
