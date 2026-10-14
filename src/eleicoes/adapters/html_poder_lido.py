"""Lê as células de um HTML de poder já gravado. Não consulta o boletim."""

import re
from html.parser import HTMLParser

from eleicoes.domain.errors import ElectionError
from eleicoes.domain.stored_grade import StoredCell

_TITLE = re.compile(
    r"nominais (\d+), legenda (\d+), votos (\d+), "
    r"votos válidos (\d+), comparecimento (\d+)"
)
_LEVELS = (
    ("Por município", "municipio"),
    ("Por estado", "uf"),
    ("Por região", "regiao"),
    ("No país", "pais"),
)


def cells_from_power_html(html: str) -> tuple[StoredCell, ...]:
    reader = _PowerHtml()
    reader.feed(html)
    reader.close()
    return tuple(reader.cells)


class _PowerHtml(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.cells: list[StoredCell] = []
        self._nivel: str | None = None
        self._h2 = False
        self._h2_text: list[str] = []
        self._thead = False
        self._th = False
        self._th_text: list[str] = []
        self._parties: list[int] = []
        self._row = False
        self._td = False
        self._td_class = ""
        self._td_title = ""
        self._td_ord = ""
        self._small = False
        self._small_text: list[str] = []
        self._fatias: list[str] = []
        self._codigo = ""
        self._nome = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        found = dict(attrs)
        if tag == "h2":
            self._h2 = True
            self._h2_text = []
        elif tag == "thead":
            self._thead = True
            self._parties = []
        elif tag == "th" and self._thead:
            self._th = True
            self._th_text = []
        elif tag == "tr":
            self._row = True
            self._fatias = []
            self._codigo = ""
            self._nome = ""
        elif tag == "td" and self._row:
            self._td = True
            self._td_class = found.get("class") or ""
            self._td_title = found.get("title") or ""
            self._td_ord = found.get("data-ord") or ""
        elif tag == "small" and self._td:
            self._small = True
            self._small_text = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "h2" and self._h2:
            self._h2 = False
            self._nivel = _nivel("".join(self._h2_text))
        elif tag == "th" and self._th:
            self._th = False
            self._remember_party("".join(self._th_text))
        elif tag == "thead":
            self._thead = False
        elif tag == "small" and self._small:
            self._small = False
            self._codigo = "".join(self._small_text).strip()
        elif tag == "td" and self._td:
            self._td = False
            self._remember_cell()
        elif tag == "tr" and self._row:
            self._row = False
            self._emit()

    def handle_data(self, data: str) -> None:
        if self._h2:
            self._h2_text.append(data)
        elif self._th:
            self._th_text.append(data)
        elif self._small:
            self._small_text.append(data)

    def _remember_party(self, text: str) -> None:
        party = text.strip()
        if party.isdigit():
            self._parties.append(int(party))

    def _remember_cell(self) -> None:
        classes = self._td_class.split()
        if "lugar" in classes:
            self._nome = self._td_ord.strip()
        elif "fatia" in classes:
            self._fatias.append(self._td_title)

    def _emit(self) -> None:
        if self._nivel is None or self._nome == "" or self._codigo == "":
            return
        if not self._parties or len(self._fatias) != len(self._parties):
            raise ElectionError("power html row is incomplete")
        for party, title in zip(self._parties, self._fatias, strict=True):
            self.cells.append(_cell(self._nivel, self._codigo, self._nome, party, title))


def _nivel(heading: str) -> str | None:
    text = heading.strip()
    for prefix, level in _LEVELS:
        if text.startswith(prefix):
            return level
    return None


def _cell(nivel: str, codigo: str, nome: str, party: int, title: str) -> StoredCell:
    found = _TITLE.fullmatch(title.strip())
    if found is None:
        raise ElectionError("power html cell is incomplete")
    nominais = int(found.group(1))
    legenda = int(found.group(2))
    comparecimento = int(found.group(5))
    return StoredCell(nivel, codigo, nome, comparecimento, party, nominais, legenda)
