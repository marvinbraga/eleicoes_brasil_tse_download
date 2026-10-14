from eleicoes.domain.mapa import (
    BridgeMissingError,
    InvalidCargoError,
    InvalidPonteError,
    Marca,
    MarkMissingError,
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
    assert painted.municipios[0].peso == "1/1"


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
    assert painted.pais is not None
    assert painted.pais.peso == "3/4"


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
