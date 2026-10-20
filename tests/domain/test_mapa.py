from eleicoes.domain.mapa import (
    BridgeMissingError,
    InvalidCargoError,
    InvalidPonteError,
    Marca,
    MarkMissingError,
    PaginaDoMapa,
    Pintura,
    RecortePintado,
    ponte_de_linhas,
    recorte_pintado,
)
from eleicoes.domain.presidente_governador import (
    CargoTally,
    MunicipalPlace,
    PartyTally,
    view_from_places,
)

_HEADER = (
    "DT_GERACAO",
    "HH_GERACAO",
    "CD_UF_TSE",
    "CD_UF_IBGE",
    "SG_UF",
    "NM_UF",
    "CD_MUNICIPIO_TSE",
    "NM_MUNICIPIO_TSE",
    "CD_MUNICIPIO_IBGE",
    "NM_MUNICIPIO_IBGE",
)


def _row(tse_uf: str, ibge_uf: str, sigla: str, tse: str, nome: str, ibge: str) -> dict[str, str]:
    values = ("04/10/2026", "09:00:06", tse_uf, ibge_uf, sigla, nome, tse, nome, ibge, nome)
    return dict(zip(_HEADER, values, strict=True))


def _ponte() -> object:
    return ponte_de_linhas(
        (
            _row("1", "12", "AC", "01007", "Bujari", "1200138"),
            _row("1", "35", "SP", "71072", "São Paulo", "3550308"),
            _row("20", "53", "DF", "97012", "Brasília", "5300108"),
            _row("11", "51", "MT", "73709", "Boa Esperança do Norte", "5101837"),
        ),
    )


def _tally(partido: int) -> CargoTally:
    return CargoTally((PartyTally(partido, 10, 0),), 0, 0)


def _place(
    uf: str, codigo: str, nome: str, presidente: int, governador: int | None
) -> MunicipalPlace:
    governor = None if governador is None else _tally(governador)
    return MunicipalPlace(uf, codigo, nome, _tally(presidente), governor)


def test_bujari_keeps_the_leading_zero_and_sp_uses_the_ibge_uf() -> None:
    ponte = _ponte()
    assert ponte.municipio_por_tse["01007"] == "1200138"
    assert ponte.municipio_por_tse["71072"] == "3550308"
    assert ponte.uf_por_sigla["SP"] == "35"
    assert ponte.uf_por_sigla["DF"] == "53"
    assert "1" not in ponte.uf_por_sigla.values()


def test_domain_code_joins_the_zero_padded_bridge() -> None:
    ponte = _ponte()
    view = view_from_places(2026, 1, (_place("AC", "1007", "Bujari (AC)", 22, 22),))
    painted = recorte_pintado(
        view,
        "presidente",
        ponte,
        {22: Marca("#112233", "data:x")},
        frozenset({"1200138"}),
        frozenset({"12"}),
        "076",
    )
    assert painted.municipios[0].codigo == "1200138"


def test_five_digit_code_is_not_padded_into_another_city() -> None:
    ponte = _ponte()
    view = view_from_places(2026, 1, (_place("AC", "10070", "Outra", 22, 22),))
    try:
        recorte_pintado(
            view,
            "presidente",
            ponte,
            {22: Marca("#112233", "data:x")},
            frozenset({"1200138"}),
            frozenset({"12"}),
            "076",
        )
    except BridgeMissingError as error:
        assert error.ausentes == (("AC", "10070"),)
    else:
        raise AssertionError("expected BridgeMissingError")


def test_duplicate_tse_code_rejects_the_bridge() -> None:
    row = _row("1", "12", "AC", "01007", "Bujari", "1200138")
    try:
        ponte_de_linhas((row, row))
    except InvalidPonteError:
        return
    raise AssertionError("expected InvalidPonteError")


def test_paint_uses_the_leader_number_and_lists_holes() -> None:
    ponte = _ponte()
    places = (
        _place("AC", "01007", "Bujari (AC)", 22, 13),
        _place("MT", "73709", "Boa Esperança do Norte (MT)", 22, 22),
        _place("ZZ", "99001", "Lisboa (ZZ)", 22, None),
    )
    view = view_from_places(2026, 1, places)
    marcas = {
        22: Marca("#112233", "data:image/png;base64,QQ=="),
        13: Marca("#AABBCC", "data:image/png;base64,Ug=="),
    }
    painted = recorte_pintado(
        view,
        "presidente",
        ponte,
        marcas,
        frozenset({"1200138", "3550308"}),
        frozenset({"12", "35", "51", "53"}),
        "076",
    )
    assert painted.pais is not None
    assert painted.pais.codigo == "076"
    assert painted.pais.numero == "22"
    assert painted.pais.logo == "data:image/png;base64,QQ=="
    assert [item.codigo for item in painted.municipios] == ["1200138"]
    assert [item.codigo for item in painted.ufs] == ["12", "51"]
    assert "Boa Esperança do Norte (MT)" in painted.sem_poligono
    assert "Boa Esperança do Norte (MT) (MT)" not in painted.sem_poligono
    assert "Lisboa (ZZ)" in painted.sem_poligono
    assert "Exterior (ZZ)" in painted.sem_poligono
    assert all(item.codigo not in {"NO", "NE", "CO", "SE", "S"} for item in painted.ufs)


def test_governor_map_uses_the_governor_leader() -> None:
    ponte = _ponte()
    view = view_from_places(2026, 1, (_place("AC", "01007", "Bujari", 22, 13),))
    marcas = {22: Marca("#112233", "data:a"), 13: Marca("#AABBCC", "data:b")}
    painted = recorte_pintado(
        view, "governador", ponte, marcas, frozenset({"1200138"}), frozenset({"12"}), "076"
    )
    assert painted.municipios[0].numero == "13"
    assert painted.municipios[0].cor == "#AABBCC"
    assert painted.municipios[0].peso == "10/10"


def test_paint_weight_is_the_leader_share_of_valid_votes() -> None:
    ponte = _ponte()
    president = CargoTally((PartyTally(22, 3, 0), PartyTally(13, 1, 0)), 0, 0)
    governor = CargoTally((PartyTally(13, 4, 0),), 0, 0)
    view = view_from_places(
        2026,
        1,
        (MunicipalPlace("AC", "01007", "Bujari", president, governor),),
    )
    marcas = {22: Marca("#112233", "data:a"), 13: Marca("#AABBCC", "data:b")}
    painted = recorte_pintado(
        view, "presidente", ponte, marcas, frozenset({"1200138"}), frozenset({"12"}), "076"
    )
    assert painted.municipios[0].cor == "#112233"
    assert painted.municipios[0].peso == "3/4"
    assert painted.municipios[0].nome == "Bujari"
    assert painted.pais is not None
    assert painted.pais.peso == "3/4"
    assert painted.pais.nome == "Brasil"
    assert painted.ufs[0].nome == "Acre"


def test_paint_weight_keeps_the_valid_total() -> None:
    ponte = _ponte()
    president = CargoTally((PartyTally(22, 2, 0), PartyTally(13, 2, 0)), 0, 0)
    governor = CargoTally((PartyTally(13, 4, 0),), 0, 0)
    view = view_from_places(
        2026,
        1,
        (MunicipalPlace("AC", "01007", "Bujari", president, governor),),
    )
    marcas = {22: Marca("#112233", "data:a"), 13: Marca("#AABBCC", "data:b")}
    painted = recorte_pintado(
        view, "presidente", ponte, marcas, frozenset({"1200138"}), frozenset({"12"}), "076"
    )
    assert painted.municipios[0].peso == "2/4"
    assert painted.pais is not None
    assert painted.pais.peso == "2/4"


def test_missing_mark_names_every_leader() -> None:
    ponte = _ponte()
    view = view_from_places(2026, 1, (_place("AC", "01007", "Bujari", 22, 22),))
    try:
        recorte_pintado(
            view, "presidente", ponte, {}, frozenset({"1200138"}), frozenset({"12"}), "076"
        )
    except MarkMissingError as error:
        assert error.partidos == (22,)
    else:
        raise AssertionError("expected MarkMissingError")


def test_unknown_cargo_is_rejected() -> None:
    ponte = _ponte()
    view = view_from_places(2026, 1, (_place("AC", "01007", "Bujari", 22, 22),))
    try:
        recorte_pintado(view, "senador", ponte, {}, frozenset(), frozenset(), "076")
    except InvalidCargoError:
        return
    raise AssertionError("expected InvalidCargoError")


def test_paint_carries_the_runner_up_and_blank_and_null_votes() -> None:
    ponte = _ponte()
    president = CargoTally((PartyTally(22, 5, 0), PartyTally(13, 3, 0)), 2, 1)
    governor = CargoTally((PartyTally(13, 4, 0),), 0, 0)
    view = view_from_places(
        2026,
        1,
        (MunicipalPlace("AC", "01007", "Bujari", president, governor),),
    )
    marcas = {22: Marca("#112233", "data:a"), 13: Marca("#AABBCC", "data:b")}
    painted = recorte_pintado(
        view, "presidente", ponte, marcas, frozenset({"1200138"}), frozenset({"12"}), "076"
    )
    for item in (painted.municipios[0], painted.ufs[0], painted.pais):
        assert item is not None
        assert item.segundo == "13"
        assert item.votos_segundo == 3
        assert item.branco == 2
        assert item.nulo == 1


def test_governor_paint_carries_the_governor_runner_up() -> None:
    ponte = _ponte()
    president = CargoTally((PartyTally(22, 5, 0),), 0, 0)
    governor = CargoTally((PartyTally(13, 6, 0), PartyTally(45, 2, 0)), 4, 3)
    view = view_from_places(
        2026,
        1,
        (MunicipalPlace("AC", "01007", "Bujari", president, governor),),
    )
    marcas = {22: Marca("#112233", "data:a"), 13: Marca("#AABBCC", "data:b")}
    painted = recorte_pintado(
        view, "governador", ponte, marcas, frozenset({"1200138"}), frozenset({"12"}), "076"
    )
    assert painted.municipios[0].segundo == "45"
    assert painted.municipios[0].votos_segundo == 2
    assert painted.municipios[0].branco == 4
    assert painted.municipios[0].nulo == 3


def test_paint_without_runner_up_leaves_it_empty() -> None:
    ponte = _ponte()
    view = view_from_places(2026, 1, (_place("AC", "01007", "Bujari", 22, 22),))
    painted = recorte_pintado(
        view,
        "presidente",
        ponte,
        {22: Marca("#112233", "data:a")},
        frozenset({"1200138"}),
        frozenset({"12"}),
        "076",
    )
    assert painted.municipios[0].segundo == ""
    assert painted.municipios[0].votos_segundo == 0
    assert painted.municipios[0].branco == 0
    assert painted.municipios[0].nulo == 0


def _exterior_paint(cargo: str, exterior: dict[str, tuple[float, float]]) -> RecortePintado:
    view = view_from_places(
        2026,
        1,
        (
            _place("AC", "01007", "Bujari", 22, 13),
            MunicipalPlace(
                "ZZ",
                "29386",
                "Lisboa",
                CargoTally((PartyTally(13, 7, 0), PartyTally(22, 2, 0)), 1, 3),
                None,
            ),
        ),
    )
    marcas = {22: Marca("#112233", "data:a"), 13: Marca("#AABBCC", "data:b")}
    return recorte_pintado(
        view,
        cargo,
        _ponte(),
        marcas,
        frozenset({"1200138"}),
        frozenset({"12"}),
        "076",
        exterior=exterior,
    )


def test_abroad_place_with_a_coordinate_becomes_a_point() -> None:
    painted = _exterior_paint("presidente", {"29386": (-9.14, 38.72)})
    [ponto] = painted.exterior
    assert ponto.lon == -9.14
    assert ponto.lat == 38.72
    assert ponto.pintura.codigo == "29386"
    assert ponto.pintura.numero == "13"
    assert ponto.pintura.cor == "#AABBCC"
    assert ponto.pintura.logo == "data:b"
    assert ponto.pintura.nome == "Lisboa"
    assert ponto.pintura.peso == "7/9"
    assert ponto.pintura.segundo == "22"
    assert ponto.pintura.votos_segundo == 2
    assert ponto.pintura.branco == 1
    assert ponto.pintura.nulo == 3
    assert "Lisboa" not in painted.sem_poligono
    assert [item.codigo for item in painted.municipios] == ["1200138"]


def test_abroad_place_without_a_coordinate_stays_a_hole() -> None:
    painted = _exterior_paint("presidente", {"99999": (0.0, 0.0)})
    assert painted.exterior == ()
    assert "Lisboa" in painted.sem_poligono


def test_governor_map_has_no_abroad_points() -> None:
    painted = _exterior_paint("governador", {"29386": (-9.14, 38.72)})
    assert painted.exterior == ()
    assert "Lisboa" not in painted.sem_poligono
    assert [item.numero for item in painted.municipios] == ["13"]


def test_paint_without_exterior_keeps_abroad_places_as_holes() -> None:
    view = view_from_places(2026, 1, (_place("ZZ", "29386", "Lisboa", 22, None),))
    painted = recorte_pintado(
        view,
        "presidente",
        _ponte(),
        {22: Marca("#112233", "data:a")},
        frozenset(),
        frozenset(),
        "076",
    )
    assert painted.exterior == ()
    assert "Lisboa" in painted.sem_poligono


def test_recorte_built_positionally_has_no_points() -> None:
    assert RecortePintado(None, (), (), ()).exterior == ()


def test_recorte_built_positionally_has_no_marks() -> None:
    assert RecortePintado(None, (), (), ()).marcas == {}


def test_marks_hold_leaders_and_runner_ups_of_every_painted_item() -> None:
    painted = _exterior_paint("presidente", {"29386": (-9.14, 38.72)})
    assert painted.marcas == {
        "22": Marca("#112233", "data:a"),
        "13": Marca("#AABBCC", "data:b"),
    }


def test_abroad_point_runner_up_contributes_its_mark() -> None:
    view = view_from_places(
        2026,
        1,
        (
            _place("AC", "01007", "Bujari", 22, 22),
            MunicipalPlace(
                "ZZ",
                "29386",
                "Lisboa",
                CargoTally((PartyTally(22, 7, 0), PartyTally(45, 2, 0)), 0, 0),
                None,
            ),
        ),
    )
    marcas = {22: Marca("#112233", "data:a"), 45: Marca("#0000FF", "data:c", "PSDB")}
    painted = recorte_pintado(
        view,
        "presidente",
        _ponte(),
        marcas,
        frozenset({"1200138"}),
        frozenset({"12"}),
        "076",
        exterior={"29386": (-9.14, 38.72)},
    )
    assert painted.marcas == {"22": marcas[22], "45": marcas[45]}


def test_runner_up_without_a_mark_is_left_out() -> None:
    president = CargoTally((PartyTally(22, 5, 0), PartyTally(13, 3, 0)), 0, 0)
    view = view_from_places(2026, 1, (MunicipalPlace("AC", "01007", "Bujari", president, None),))
    painted = recorte_pintado(
        view,
        "presidente",
        _ponte(),
        {22: Marca("#112233", "data:a")},
        frozenset({"1200138"}),
        frozenset({"12"}),
        "076",
    )
    assert painted.marcas == {"22": Marca("#112233", "data:a")}


def test_hole_places_do_not_contribute_marks() -> None:
    bujari = CargoTally((PartyTally(22, 10, 0), PartyTally(13, 5, 0)), 0, 0)
    hole = CargoTally((PartyTally(45, 1, 0),), 0, 0)
    view = view_from_places(
        2026,
        1,
        (
            MunicipalPlace("AC", "01007", "Bujari", bujari, None),
            MunicipalPlace("SP", "71072", "São Paulo", hole, None),
            MunicipalPlace("ZZ", "29386", "Lisboa", hole, None),
        ),
    )
    marcas = {
        22: Marca("#112233", "data:a"),
        45: Marca("#0000FF", "data:c"),
        13: Marca("#AABBCC", "data:b"),
    }
    painted = recorte_pintado(
        view, "presidente", _ponte(), marcas, frozenset({"1200138"}), frozenset({"12"}), "076"
    )
    assert {"São Paulo", "São Paulo (SP)", "Lisboa", "Exterior (ZZ)"} <= set(painted.sem_poligono)
    assert painted.marcas == {"22": marcas[22], "13": marcas[13]}


def test_governor_marks_use_the_governor_readings() -> None:
    president = CargoTally((PartyTally(22, 5, 0), PartyTally(10, 3, 0)), 0, 0)
    governor = CargoTally((PartyTally(13, 6, 0), PartyTally(45, 2, 0)), 0, 0)
    view = view_from_places(
        2026, 1, (MunicipalPlace("AC", "01007", "Bujari", president, governor),)
    )
    marcas = {
        22: Marca("#112233", "data:a"),
        10: Marca("#101010", "data:d"),
        13: Marca("#AABBCC", "data:b"),
        45: Marca("#0000FF", "data:c"),
    }
    painted = recorte_pintado(
        view, "governador", _ponte(), marcas, frozenset({"1200138"}), frozenset({"12"}), "076"
    )
    assert painted.marcas == {"13": marcas[13], "45": marcas[45]}


def test_mark_acronym_defaults_to_empty() -> None:
    assert Marca("#112233", "data:a").sigla == ""
    assert Marca("#112233", "data:a", "PL").sigla == "PL"


def _cross_paint(cargo: str) -> RecortePintado:
    president = CargoTally((PartyTally(22, 6, 0), PartyTally(13, 4, 0)), 2, 1)
    governor = CargoTally((PartyTally(45, 3, 0), PartyTally(22, 2, 0)), 0, 0)
    view = view_from_places(
        2026,
        1,
        (
            MunicipalPlace("AC", "01007", "Bujari", president, governor),
            MunicipalPlace("ZZ", "29386", "Lisboa", president, None),
        ),
    )
    marcas = {
        22: Marca("#112233", "data:a"),
        13: Marca("#AABBCC", "data:b"),
        45: Marca("#0000FF", "data:c"),
    }
    return recorte_pintado(
        view,
        cargo,
        _ponte(),
        marcas,
        frozenset({"1200138"}),
        frozenset({"12"}),
        "076",
        exterior={"29386": (-9.14, 38.72)},
    )


def test_cross_map_paints_like_the_president_map() -> None:
    cross = _cross_paint("cruzamento")
    president = _cross_paint("presidente")
    assert cross == president
    [bujari] = cross.municipios
    assert (bujari.numero, bujari.peso, bujari.segundo, bujari.votos_segundo) == (
        "22",
        "6/10",
        "13",
        4,
    )
    assert (bujari.branco, bujari.nulo) == (2, 1)
    assert [ponto.pintura.codigo for ponto in cross.exterior] == ["29386"]


def test_paint_carries_the_place_class() -> None:
    painted = _cross_paint("cruzamento")
    assert painted.municipios[0].classe == "em_aberto"
    assert painted.exterior[0].pintura.classe == "sem_governador"


def test_paint_carries_the_governor_leader_and_weight() -> None:
    for cargo in ("presidente", "governador", "cruzamento"):
        painted = _cross_paint(cargo)
        assert painted.municipios[0].governador == "45"
        assert painted.municipios[0].peso_governador == "3/5"


def test_place_without_governor_leaves_the_governor_fields_empty() -> None:
    ponto = _cross_paint("cruzamento").exterior[0].pintura
    assert ponto.governador == ""
    assert ponto.peso_governador == ""


def test_marks_include_the_governor_leader_for_every_cargo() -> None:
    for cargo in ("presidente", "cruzamento"):
        assert "45" in _cross_paint(cargo).marcas


def test_governor_leader_without_a_mark_is_left_out() -> None:
    governor = CargoTally((PartyTally(77, 3, 0),), 0, 0)
    view = view_from_places(
        2026, 1, (MunicipalPlace("AC", "01007", "Bujari", _tally(22), governor),)
    )
    painted = recorte_pintado(
        view,
        "cruzamento",
        _ponte(),
        {22: Marca("#112233", "data:a")},
        frozenset({"1200138"}),
        frozenset({"12"}),
        "076",
    )
    assert painted.municipios[0].governador == "77"
    assert painted.marcas == {"22": Marca("#112233", "data:a")}


def test_pintura_built_positionally_has_no_class_nor_governor() -> None:
    pintura = Pintura("1200138", "#112233", "22", "data:a")
    assert (pintura.classe, pintura.governador, pintura.peso_governador) == ("", "", "")


def test_page_built_positionally_has_no_extra_cuts() -> None:
    recorte = RecortePintado(None, (), (), ())
    pagina = PaginaDoMapa(
        2026, 1, "presidente", recorte, "{}", "{}", "{}", "m", "u", "p", "076", "", "", ""
    )
    assert pagina.recortes == {}
