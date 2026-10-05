from eleicoes.domain.layout import locate


def test_classic_bundle_is_grouped_by_turn_and_uf() -> None:
    location = locate("bu_imgbu_logjez_rdv_vscmr_2022_2t_SP.zip")
    assert location.collection == "totalizacao"
    assert location.turno == "2"
    assert location.uf == "SP"
    assert location.relative_path.as_posix() == (
        "totalizacao/turno-2/SP/bu_imgbu_logjez_rdv_vscmr_2022_2t_SP.zip"
    )


def test_gedai_and_correspondence_keep_their_own_collections() -> None:
    gedai = locate("log_gedai_1t_AC_041020261441.zip")
    correspondencia = locate("CESP_1t_RR_031020261534.zip")
    assert gedai.relative_path.as_posix().startswith("logs-gedai/turno-1/AC/")
    assert correspondencia.relative_path.as_posix().startswith("correspondencias/turno-1/RR/")


def test_unknown_zip_stays_out_of_the_uf_tree() -> None:
    location = locate("perfil_eleitorado.zip")
    assert location.relative_path.as_posix() == "outros/perfil_eleitorado.zip"
