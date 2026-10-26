"""BU × RDV × log: what must close between the files of one urn."""

from dataclasses import replace

from eleicoes.domain.boletim import Boletim, VoteLine
from eleicoes.domain.integridade_urna import (
    CONFERE,
    DIVERGE,
    SEM_LOG,
    SEM_RDV,
    RegistroDigital,
    ResumoLog,
    conferir,
    contagens_do_boletim,
)


def test_matching_files_confere() -> None:
    conferencia = conferir(_boletim(), _rdv(), _log())

    assert conferencia.situacao == CONFERE
    assert conferencia.divergencias == ()
    assert conferencia.urna_trocada is False


def test_one_vote_off_in_the_rdv_diverges_and_explains() -> None:
    rdv = replace(_rdv(), cargos={"presidente": {("nominal", 22): 6, ("nominal", 13): 4}})

    conferencia = conferir(_boletim(), rdv, _log())

    assert conferencia.situacao == DIVERGE
    assert conferencia.divergencias == ("rdv_difere:presidente",)
    assert "nominal 22=5" in conferencia.detalhes["rdv:presidente"]
    assert "nominal 22=6" in conferencia.detalhes["rdv:presidente"]


def test_log_counts_and_urn_must_match_the_bulletin() -> None:
    log = ResumoLog(11, {"presidente": 10}, frozenset({"00000099"}))

    conferencia = conferir(_boletim(), _rdv(), log)

    assert conferencia.divergencias == ("log_computados", "log_sem_a_urna_do_bu")


def test_rdv_from_another_section_or_urn_diverges() -> None:
    rdv = replace(_rdv(), secao=99, numero_interno_urna=1)

    assert conferir(_boletim(), rdv, _log()).divergencias == ("rdv_outra_secao", "rdv_outra_urna")


def test_missing_files_are_reported_apart() -> None:
    assert conferir(_boletim(), None, _log()).situacao == SEM_RDV
    assert conferir(_boletim(), _rdv(), None).situacao == SEM_LOG


def test_replaced_urn_is_flagged_but_still_confere() -> None:
    log = replace(_log(), urnas=frozenset({"02044893", "00000777"}), logs=2)

    conferencia = conferir(_boletim(), _rdv(), log)

    assert conferencia.situacao == CONFERE
    assert conferencia.urna_trocada is True


def test_bulletin_keys_use_the_number_for_nominal_and_the_party_for_legend() -> None:
    boletim = replace(
        _boletim(),
        votos=(
            _linha("deputadoFederal", "nominal", 11, 1101, 3),
            _linha("deputadoFederal", "legenda", 11, 11, 2),
            _linha("deputadoFederal", "branco", None, None, 1),
        ),
    )

    assert contagens_do_boletim(boletim) == {
        "deputadoFederal": {("nominal", 1101): 3, ("legenda", 11): 2, ("branco", None): 1}
    }


def _boletim() -> Boletim:
    return Boletim(
        arquivo="o03221ac0139200010436-bu.dat",
        fase="oficial",
        municipio=1392,
        zona=1,
        local=1929,
        secao=436,
        data_hora_emissao="20261025T150214",
        versao_urna="10.23.0.0",
        numero_interno_urna=2044893,
        data_hora_carga="20260925T120100",
        codigo_carga="1",
        codigo_midia="ZAC001STD25",
        eleitores_computados=10,
        indicador_habilitacao=1,
        qtd_biometria=10,
        qtd_manual=0,
        votos=(
            _linha("presidente", "nominal", 22, 22, 5),
            _linha("presidente", "nominal", 13, 13, 4),
            _linha("presidente", "nulo", None, None, 1),
        ),
    )


def _linha(cargo: str, tipo: str, partido: int | None, numero: int | None, n: int) -> VoteLine:
    return VoteLine(
        id_eleicao=6258,
        eleitores_aptos=12,
        qtd_comparecimento=12,
        qtd_eleitores_complemento=0,
        tipo_cargo="majoritario",
        cargo=cargo,
        ordem_impressao=1,
        comparecimento_cargo=10,
        tipo_voto=tipo,
        partido=partido,
        numero=numero,
        quantidade=n,
    )


def _rdv() -> RegistroDigital:
    return RegistroDigital(
        1392,
        1,
        436,
        2044893,
        {"presidente": {("nominal", 22): 5, ("nominal", 13): 4, ("nulo", None): 1}},
    )


def _log() -> ResumoLog:
    return ResumoLog(10, {"presidente": 10}, frozenset({"02044893"}))
