"""Dark page chrome shared by the profile and class reports. No party colors."""

from html import escape
from typing import Final

_BOOTSTRAP: Final = "https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css"
_BOOTSTRAP_HASH: Final = "sha384-QWTKZyjpPEjISv5WaRU9OFeRpok6YctnYmDr5pNlyT2bRjXh0JMhjY6hW+ALEwIH"
_STYLE: Final = """
html[data-bs-theme="dark"] {
  color-scheme: dark;
  --noite: #101616; --painel: #182220; --linha: #314340;
  --texto: #E7F1ED; --mudo: #A8C2BC; --marca: #0D6F6E; --hover: #243330;
}
body {
  background: var(--noite); color: var(--texto);
  font-family: "Segoe UI", "Noto Sans", "Liberation Sans", "DejaVu Sans", sans-serif;
  font-size: 15px; line-height: 1.45;
}
main.container-fluid { max-width: 1440px; margin-inline: auto; padding: 1.5rem; }
h1 {
  font-family: Palatino, "Palatino Linotype", "Liberation Serif", Georgia, serif;
  font-size: clamp(1.8rem, 3vw, 2.45rem); font-weight: 600; letter-spacing: -0.03em;
}
.subtitulo { color: var(--mudo); max-width: 70ch; }
.grade-scroll { max-height: 70vh; overflow: auto; }
table.grade {
  --bs-table-bg: transparent; --bs-table-color: var(--texto);
  --bs-table-border-color: var(--linha);
  font-variant-numeric: tabular-nums;
}
table.grade th, table.grade td { vertical-align: middle; }
table.grade th.lugar, table.grade td.lugar {
  position: sticky; left: 0; z-index: 1; text-align: left; white-space: nowrap;
  background: var(--painel);
}
table.grade thead th {
  position: sticky; top: 0; z-index: 2; cursor: pointer; user-select: none;
  background: var(--painel);
}
table.grade thead th.lugar { z-index: 3; }
table.grade thead th[aria-sort="ascending"]::after { content: " ▲"; }
table.grade thead th[aria-sort="descending"]::after { content: " ▼"; }
table.grade td.num, table.grade th.num { text-align: right; white-space: nowrap; }
.notas {
  list-style: none; margin: 1.5rem 0 0; padding: 1rem 0 0;
  max-width: 72ch; border-top: 1px solid var(--linha); color: var(--mudo);
}
"""
_SCRIPT: Final = """
<script>
(function () {
  document.querySelectorAll("table.grade").forEach(function (table) {
    table.querySelectorAll("thead th").forEach(function (header, index) {
      header.tabIndex = 0;
      header.addEventListener("click", function () { reorder(table, header, index); });
      header.addEventListener("keydown", function (event) {
        if (event.key !== "Enter" && event.key !== " ") return;
        event.preventDefault();
        reorder(table, header, index);
      });
    });
  });

  function reorder(table, header, index) {
    var ascending = header.getAttribute("aria-sort") !== "ascending";
    table.querySelectorAll("thead th").forEach(function (item) {
      item.setAttribute("aria-sort", "none");
    });
    header.setAttribute("aria-sort", ascending ? "ascending" : "descending");
    var body = table.tBodies[0];
    var rows = Array.prototype.slice.call(body.rows);
    var sign = ascending ? 1 : -1;
    rows.sort(function (left, right) {
      return sign * compare(left.cells[index], right.cells[index], index);
    });
    rows.forEach(function (row) { body.appendChild(row); });
  }

  function compare(left, right, index) {
    var a = left.getAttribute("data-ord") || "";
    var b = right.getAttribute("data-ord") || "";
    if (index === 0) {
      return a.localeCompare(b, "pt-BR", {numeric: true, sensitivity: "base"});
    }
    return Number(a) - Number(b);
  }
})();
</script>
"""


def render_page(title: str, subtitle: str, body: str, notes: tuple[str, ...]) -> str:
    items = "".join(f"<li>{escape(note)}</li>" for note in notes)
    return (
        "<!DOCTYPE html>"
        '<html lang="pt-BR" data-bs-theme="dark">'
        "<head>"
        '<meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{escape(title)}</title>"
        f'<link rel="stylesheet" href="{_BOOTSTRAP}" integrity="{_BOOTSTRAP_HASH}" '
        'crossorigin="anonymous">'
        f"<style>{_STYLE}</style>"
        "</head><body>"
        '<main class="container-fluid">'
        f"<h1>{escape(title)}</h1>"
        f'<p class="subtitulo">{subtitle}</p>'
        f"{body}"
        f'<ul class="notas">{items}</ul>'
        "</main>"
        f"{_SCRIPT}"
        "</body></html>"
    )
