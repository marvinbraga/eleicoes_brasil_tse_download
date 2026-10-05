from eleicoes.domain.tabular_contract import CCONT, CSEC, contract_for


def test_section_contract_has_the_published_header() -> None:
    contract = contract_for("csec_1t_AC_041020261259.csv")
    assert contract is CSEC
    assert len(CSEC.columns) == 21
    assert CSEC.columns[8:10] == ("NR_SECAO", "NR_LOCAL_VOTACAO")


def test_contingency_contract_omits_section_and_place() -> None:
    contract = contract_for("subdir/ccont_1t_AC_041020261259.csv")
    assert contract is CCONT
    assert len(CCONT.columns) == 19
    assert "NR_SECAO" not in CCONT.columns
    assert "NR_LOCAL_VOTACAO" not in CCONT.columns


def test_pdf_jez_and_unknown_csv_have_no_contract() -> None:
    assert contract_for("leiame-corresp-esperada-secao.pdf") is None
    assert contract_for("gedai-ue-ac-03220-oficial-log.jez") is None
    assert contract_for("outro_1t_AC_041020261259.csv") is None
