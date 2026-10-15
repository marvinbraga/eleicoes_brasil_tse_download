"""Profile HTML. Percent cells use the shared half-up rule."""

from eleicoes.adapters.html_perfis import html_perfis
from eleicoes.domain.perfis import ProfileDataset, ProfilePlace, assemble_profile


def test_presidente_page_shows_centers_as_percents() -> None:
    html = html_perfis(_report(ballot=True, searched=True))

    assert "Perfis municipais" in html
    assert "Presidente" in html
    assert "silhueta" in html
    assert ">Branco</th>" in html
    assert ">Nulo</th>" in html
    assert "50,00%" in html
    assert "12,50%" in html
    assert "1.234" in html or "12.345" in html
    assert "bootstrap@5.3.3" in html
    assert "Senador não tem branco nem nulo neste relatório." in html
    assert "não uma previsão" in html
    assert "exterior" in html
    assert "votos válidos" in html
    assert "comparecimento" in html
    assert 'data-bs-theme="dark"' in html
    assert "laser" not in html.lower()


def test_senador_page_omits_blank_and_null_columns() -> None:
    html = html_perfis(_report(ballot=False, searched=False))

    assert "Senador" in html
    assert "grupos escolhidos" in html
    assert ">Branco</th>" not in html
    assert ">Nulo</th>" not in html
    assert "Alpha" in html
    assert "Grupo" in html


def _report(*, ballot: bool, searched: bool) -> object:
    if ballot:
        places = (
            ProfilePlace("1", "Alpha", 12345, (8, 2), 1, 1),
            ProfilePlace("2", "Beta", 20, (1, 1), 0, 0),
            ProfilePlace("3", "Gama", 20, (0, 4), 0, 0),
        )
        dataset = ProfileDataset("presidente", (13, 22), places)
        centers = (
            (0.5, 0.125, 0.5, 0.25),
            (0.25, 0.5, 0.0, 0.0),
            (0.0, 1.0, 0.0, 0.0),
        )
    else:
        places = (
            ProfilePlace("1", "Alpha", 10, (4,), None, None),
            ProfilePlace("2", "Beta", 10, (4,), None, None),
            ProfilePlace("3", "Gama", 10, (4,), None, None),
        )
        dataset = ProfileDataset("senador", (13,), places)
        centers = ((1.0,), (1.0,), (1.0,))
    return assemble_profile(
        2026,
        1,
        dataset,
        (0, 1, 2),
        centers,
        searched=searched,
        silhouette=0.5 if searched else None,
    )
