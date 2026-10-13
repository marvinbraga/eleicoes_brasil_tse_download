"""HTML da grade de poder. Tema claro ou escuro, com a escala de cor local."""

import re
from collections.abc import Callable, Mapping
from fractions import Fraction
from html import escape
from typing import Final

from eleicoes.domain.grade import CelulaGrade, GradeDePoder, LinhaGrade
from eleicoes.domain.regiao import REGIONS
from eleicoes.domain.values import UF_CODES, UF_NAMES, uf_name

_TEAL: Final[tuple[int, int, int]] = (13, 111, 110)
_WHITE: Final[tuple[int, int, int]] = (255, 255, 255)
_INK: Final[tuple[int, int, int]] = (20, 20, 20)
_TEXT_LIMIT: Final[Fraction] = Fraction(3, 5)
_PERCENT_SCALE: Final = 10000
_TWO_DECIMALS: Final = 100
_SORT_SCALE: Final = 1_000_000_000
_STATE_SUFFIX: Final = re.compile(r"\(([A-Z]{2})\)\Z")
_BOOTSTRAP: Final = "https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css"
_BOOTSTRAP_HASH: Final = "sha384-QWTKZyjpPEjISv5WaRU9OFeRpok6YctnYmDr5pNlyT2bRjXh0JMhjY6hW+ALEwIH"
_NOTES: Final = (
    "Os votos nominais e de legenda são somados.",
    "Brancos e nulos ficam de fora.",
    "O percentual é o voto do partido sobre os votos válidos do lugar.",
    "Número sem candidato a presidente conta como nulo.",
    "Clique no título da coluna para ordenar.",
)
_STYLE: Final = """
html[data-bs-theme="dark"] {
  color-scheme: dark;
  --noite: #101616; --painel: #182220; --linha: #314340;
  --texto: #E7F1ED; --mudo: #A8C2BC; --marca: #0D6F6E; --hover: #243330;
}
html[data-bs-theme="light"] {
  color-scheme: light;
  --noite: #F3F6F5; --painel: #FFFFFF; --linha: #D3E0DB;
  --texto: #14201E; --mudo: #3E5550; --marca: #0D6F6E; --hover: #E4EEEB;
}
html { scroll-behavior: smooth; }
body {
  background: var(--noite); color: var(--texto);
  font-family: "Segoe UI", "Noto Sans", "Liberation Sans", "DejaVu Sans", sans-serif;
  font-size: 15px; line-height: 1.45;
}
main.container-fluid {
  max-width: 1440px; margin-inline: auto;
  padding-left: clamp(1rem, 3vw, 2.5rem);
  padding-right: clamp(1rem, 3vw, 2.5rem);
}
.pular {
  position: absolute; left: 0.75rem; top: 0.75rem;
  transform: translateY(-150%); background: var(--painel);
  color: var(--texto); padding: 0.4rem 0.7rem;
}
.pular:focus { transform: none; }
.masthead {
  display: flex; align-items: flex-end; justify-content: space-between;
  gap: 1.25rem 2rem; padding-bottom: 1.25rem; margin-bottom: 1.25rem;
  border-bottom: 1px solid var(--linha);
}
.masthead h1.h3 {
  font-family: Palatino, "Palatino Linotype", "Liberation Serif", Georgia, serif;
  font-size: clamp(1.8rem, 3vw, 2.45rem);
  font-weight: 600; letter-spacing: -0.03em; line-height: 1;
  margin: 0 0 0.7rem; color: var(--texto);
}
.escala {
  display: flex; align-items: center; gap: 0.7rem;
  margin: 0; max-width: 62ch; color: var(--mudo); font-size: 0.92rem;
}
.escala-barra {
  flex: 0 0 auto; width: 7.5rem; height: 0.55rem;
  background: linear-gradient(90deg, #ffffff, rgb(13,111,110));
  box-shadow: inset 0 0 0 1px rgba(13, 111, 110, 0.35);
}
.temas {
  display: inline-flex; flex: 0 0 auto; border: 1px solid var(--linha);
}
.temas button {
  font: inherit; cursor: pointer; color: var(--mudo);
  background: transparent; border: 0; min-height: 2.4rem; padding: 0.35rem 0.9rem;
}
html[data-bs-theme="dark"] .temas [data-tema="dark"],
html[data-bs-theme="light"] .temas [data-tema="light"] {
  background: var(--marca); color: #ffffff;
}
.indice {
  display: flex; flex-wrap: wrap; gap: 0.45rem 1.15rem; margin: 0 0 1.6rem;
}
.indice:empty { display: none; }
.indice a {
  color: var(--texto); text-underline-offset: 0.28rem;
  text-decoration-color: var(--marca);
}
main section > h2.h4 {
  font-size: 1.45rem; font-weight: 600; letter-spacing: -0.02em;
  margin: 0 0 0.85rem; color: var(--texto);
}
main section h3 {
  font-size: 1rem; font-weight: 600; color: var(--texto);
  border-left: 3px solid var(--marca); padding-left: 0.65rem;
}
.grade-scroll { max-height: 70vh; overflow: auto; }
table.grade {
  --bs-table-bg: transparent; --bs-table-color: var(--texto);
  --bs-table-border-color: transparent;
  border-collapse: separate; border-spacing: 2px;
  font-variant-numeric: tabular-nums; margin-bottom: 1.5rem;
}
table.grade th, table.grade td {
  text-align: right; vertical-align: middle; border: 0;
  padding: 0.32rem 0.55rem;
}
table.grade > :not(caption) > * > * { box-shadow: none; }
table.grade td.lugar, table.grade th.lugar {
  text-align: left; white-space: nowrap;
}
table.grade td.validos, table.grade th.validos { white-space: nowrap; }
table.grade td.lugar, table.grade td.validos { background: var(--painel); }
table.grade td.fatia {
  font-weight: 600; min-width: 4.6rem;
  box-shadow: inset 0 0 0 1px rgba(13, 111, 110, 0.16);
}
table.grade small { font-size: 0.78em; color: var(--mudo); margin-left: 0.35rem; }
table.grade thead th {
  position: sticky; top: 0; z-index: 2; cursor: pointer; user-select: none;
  font-size: 0.84rem; font-weight: 600; color: var(--texto);
  background-color: var(--painel); --bs-table-bg: var(--painel);
}
table.grade td.lugar, table.grade th.lugar {
  position: sticky; left: 0; z-index: 1; background-color: var(--painel);
}
table.grade thead th.lugar { z-index: 3; }
table.grade tbody tr:hover td.lugar,
table.grade tbody tr:hover td.validos { background: var(--hover); }
table.grade td.lugar { transition: background-color 120ms ease; }
table.grade thead th[aria-sort="ascending"]::after { content: " ▲"; }
table.grade thead th[aria-sort="descending"]::after { content: " ▼"; }
.notas {
  list-style: none; margin: 1.5rem 0 0; padding: 1rem 0 0;
  max-width: 68ch; border-top: 1px solid var(--linha);
}
.notas li { color: var(--mudo); padding: 0.12rem 0; }
.atalhos {
  display: flex; flex-wrap: wrap; align-items: center;
  gap: 0.35rem 0.7rem; margin: 0.55rem 0 0;
  color: var(--mudo); font-size: 0.88rem;
}
.atalhos kbd {
  font-family: inherit; font-size: 0.84em; color: var(--texto);
  background: transparent; border: 1px solid var(--linha);
  border-radius: 0; box-shadow: none; padding: 0.05rem 0.35rem;
}
#ferramenta:empty { display: none; }
#ferramenta { color: var(--texto); }
body.apontando { user-select: none; }
:focus-visible { outline: 2px solid var(--marca); outline-offset: 2px; }
@media (max-width: 720px) {
  .masthead { flex-direction: column; align-items: flex-start; }
  .grade-scroll { max-height: none; }
}
@media (prefers-reduced-motion: reduce) {
  html { scroll-behavior: auto; }
  table.grade td.lugar { transition: none; }
}
@media print {
  .temas, .indice, .pular, .atalhos, #laserCanvas, #markerCanvas { display: none; }
  body { background: #ffffff; color: #141414; }
  .grade-scroll { max-height: none; overflow: visible; }
  table.grade td.lugar, table.grade th.lugar { position: static; }
  table.grade td.fatia { print-color-adjust: exact; }
}
"""
_THEME_BOOT: Final = """
<script>
(function () {
  try {
    var saved = localStorage.getItem("poder-tema");
    if (saved === "light" || saved === "dark") {
      document.documentElement.setAttribute("data-bs-theme", saved);
    }
  } catch (error) {
    return;
  }
})();
</script>
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
  mountIndex();
  mountTheme();

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

  function mountIndex() {
    var headings = document.querySelectorAll("main section > h2");
    var nav = document.querySelector(".indice");
    if (nav === null || headings.length < 2) return;
    headings.forEach(function (heading) {
      var section = heading.parentElement;
      if (section === null || section.id === "") return;
      var link = document.createElement("a");
      var text = heading.textContent || "";
      var cut = text.split(" — ")[0];
      link.textContent = cut || text;
      link.href = "#" + section.id;
      nav.appendChild(link);
    });
  }

  function mountTheme() {
    var root = document.documentElement;
    var buttons = document.querySelectorAll(".temas button");
    function apply(theme) {
      root.setAttribute("data-bs-theme", theme);
      buttons.forEach(function (button) {
        var on = button.getAttribute("data-tema") === theme;
        button.setAttribute("aria-pressed", on ? "true" : "false");
      });
      try { localStorage.setItem("poder-tema", theme); }
      catch (error) { return; }
    }
    buttons.forEach(function (button) {
      button.addEventListener("click", function () {
        apply(button.getAttribute("data-tema") || "dark");
      });
    });
    apply(root.getAttribute("data-bs-theme") || "dark");
  }
})();
</script>
"""
_POINTER: Final = """
<script>
(function () {
  var LASER_R = 255, LASER_G = 40, LASER_B = 40;
  var TRAIL_FADE = 3000, DECAY_LENGTH = 50;
  var BASE_WIDTH = 3, GLOW_WIDTH = 14, STREAMLINE = 0.35;
  var MARKER_R = 255, MARKER_G = 230, MARKER_B = 0;
  var MARKER_ALPHA = 0.28, BORDER_ALPHA = 0.5;
  var laserActive = false, markerActive = false;
  var laserDrawing = false, markerDragging = false;
  var trails = [], currentTrail = null, rafId = null;
  var rects = [], dragStart = null, dragCurrent = null, dragAnchor = null;
  var dpr = window.devicePixelRatio || 1;
  var laserCanvas = layer("laserCanvas", "99999");
  var markerCanvas = layer("markerCanvas", "9997");
  var laserCtx = laserCanvas.getContext("2d");
  var markerCtx = markerCanvas.getContext("2d");

  function layer(id, zIndex) {
    var canvas = document.createElement("canvas");
    canvas.id = id;
    canvas.setAttribute("aria-hidden", "true");
    canvas.style.position = "fixed";
    canvas.style.inset = "0";
    canvas.style.width = "100%";
    canvas.style.height = "100%";
    canvas.style.pointerEvents = "none";
    canvas.style.zIndex = zIndex;
    document.body.appendChild(canvas);
    return canvas;
  }

  function fit(canvas, ctx) {
    dpr = window.devicePixelRatio || 1;
    canvas.width = Math.round(window.innerWidth * dpr);
    canvas.height = Math.round(window.innerHeight * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }

  function resize() {
    fit(laserCanvas, laserCtx);
    fit(markerCanvas, markerCtx);
    drawMarker();
  }

  function isPage(anchor) {
    return !anchor || anchor === document.body
      || anchor === document.documentElement
      || anchor === document.scrollingElement;
  }

  function anchorOf(target) {
    var node = target;
    while (node && node !== document.body) {
      if (node.classList && node.classList.contains("grade-scroll")) return node;
      node = node.parentElement;
    }
    return document.scrollingElement || document.documentElement;
  }

  function contentPoint(event, anchor) {
    if (isPage(anchor)) {
      return { x: event.clientX + window.scrollX, y: event.clientY + window.scrollY };
    }
    var box = anchor.getBoundingClientRect();
    return {
      x: event.clientX - box.left + anchor.scrollLeft,
      y: event.clientY - box.top + anchor.scrollTop
    };
  }

  function toView(x, y, anchor) {
    if (isPage(anchor)) return { x: x - window.scrollX, y: y - window.scrollY };
    var box = anchor.getBoundingClientRect();
    return {
      x: box.left + x - anchor.scrollLeft,
      y: box.top + y - anchor.scrollTop
    };
  }

  function clipOf(anchor) {
    if (isPage(anchor)) return null;
    var box = anchor.getBoundingClientRect();
    var top = box.top;
    var head = anchor.querySelector("thead th");
    if (head) {
      var headBox = head.getBoundingClientRect();
      if (headBox.bottom > top && headBox.bottom < box.bottom) top = headBox.bottom;
    }
    return { x: box.left, y: top, w: box.width, h: Math.max(0, box.bottom - top) };
  }

  function easeOut(value) { return 1 - Math.pow(1 - value, 3); }

  function dist(a, b) {
    var dx = b.x - a.x, dy = b.y - a.y;
    return Math.sqrt(dx * dx + dy * dy);
  }

  function lerp(a, b, t) {
    return { x: a.x + (b.x - a.x) * t, y: a.y + (b.y - a.y) * t };
  }

  function syncChrome() {
    var on = laserActive || markerActive;
    document.body.style.cursor = on ? "crosshair" : "";
    document.body.classList.toggle("apontando", on);
    var node = document.getElementById("ferramenta");
    if (!node) return;
    var parts = [];
    if (laserActive) parts.push("Laser ligado");
    if (markerActive) parts.push("Marca-texto ligado");
    node.textContent = parts.join(". ");
  }

  document.addEventListener("keydown", function (event) {
    if (event.repeat || event.ctrlKey || event.metaKey || event.altKey) return;
    var tag = event.target && event.target.tagName;
    if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;
    if (event.key === "k" || event.key === "K") {
      laserActive = !laserActive;
      if (!laserActive) stopLaser();
      syncChrome();
    } else if (event.key === "m" || event.key === "M") {
      markerActive = !markerActive;
      if (!markerActive) clearMarker();
      syncChrome();
    } else if (event.key === "Escape") {
      laserActive = false;
      stopLaser();
      syncChrome();
    }
  });

  document.addEventListener("mousedown", function (event) {
    if (event.button !== 0 || (!laserActive && !markerActive)) return;
    event.preventDefault();
  }, true);

  document.addEventListener("click", function (event) {
    if (!laserActive && !markerActive) return;
    event.preventDefault();
    event.stopPropagation();
  }, true);

  document.addEventListener("mousedown", function (event) {
    if (event.button !== 0) return;
    var anchor = anchorOf(event.target);
    var point = contentPoint(event, anchor);
    if (laserActive) startLaser(anchor, point);
    if (markerActive) startMarker(anchor, point);
  });

  document.addEventListener("mousemove", function (event) {
    if (laserDrawing && currentTrail) moveLaser(event);
    if (markerDragging && dragStart) moveMarker(event);
  });

  document.addEventListener("mouseup", function (event) {
    if (event.button !== 0) return;
    if (laserDrawing) stopLaser();
    if (markerDragging) finishMarker();
  });

  document.addEventListener("mouseleave", function () {
    if (laserDrawing) stopLaser();
    if (markerDragging) finishMarker();
  });

  function startLaser(anchor, point) {
    laserDrawing = true;
    currentTrail = {
      anchor: anchor,
      points: [{ x: point.x, y: point.y, t: performance.now() }],
      closed: false,
      closedAt: null
    };
    trails.push(currentTrail);
    if (!rafId) tick();
  }

  function moveLaser(event) {
    var pts = currentTrail.points;
    var last = pts[pts.length - 1];
    var point = contentPoint(event, currentTrail.anchor);
    var next = { x: point.x, y: point.y };
    if (STREAMLINE > 0) next = lerp(point, last, STREAMLINE);
    if (dist(last, next) > 2) pts.push({ x: next.x, y: next.y, t: performance.now() });
  }

  function stopLaser() {
    if (currentTrail && !currentTrail.closed) {
      currentTrail.closed = true;
      currentTrail.closedAt = performance.now();
    }
    laserDrawing = false;
    currentTrail = null;
  }

  function computeLengths(pts) {
    var lengths = new Array(pts.length);
    lengths[0] = 0;
    var i;
    for (i = 1; i < pts.length; i += 1) {
      lengths[i] = lengths[i - 1] + dist(pts[i - 1], pts[i]);
    }
    return lengths;
  }

  function pointOpacity(running, now, trail) {
    var opacity = 1;
    if (trail.closed && trail.closedAt !== null) {
      opacity = easeOut(Math.max(0, 1 - (now - trail.closedAt) / TRAIL_FADE));
    }
    if (running < DECAY_LENGTH) {
      opacity = Math.min(opacity, easeOut(running / DECAY_LENGTH));
    }
    return opacity;
  }

  function strokeLaser(from, to, width, alpha, blur) {
    laserCtx.beginPath();
    laserCtx.moveTo(from.x, from.y);
    laserCtx.lineTo(to.x, to.y);
    laserCtx.lineWidth = width;
    laserCtx.lineCap = "round";
    laserCtx.shadowBlur = blur;
    laserCtx.strokeStyle = "rgba(" + LASER_R + "," + LASER_G + "," + LASER_B + "," + alpha + ")";
    laserCtx.shadowColor = laserCtx.strokeStyle;
    laserCtx.stroke();
  }

  function drawTrail(trail, now) {
    var pts = trail.points;
    if (pts.length < 2) return false;
    var lengths = computeLengths(pts);
    var first = -1;
    var i;
    for (i = 0; i < pts.length; i += 1) {
      if (pointOpacity(lengths[i], now, trail) > 0.005) { first = i; break; }
    }
    if (first < 0) return false;
    var visible = false;
    var clip = clipOf(trail.anchor);
    laserCtx.save();
    if (clip) {
      laserCtx.beginPath();
      laserCtx.rect(clip.x, clip.y, clip.w, clip.h);
      laserCtx.clip();
    }
    for (i = Math.max(1, first); i < pts.length; i += 1) {
      var op = pointOpacity(lengths[i], now, trail);
      if (op < 0.005) continue;
      visible = true;
      var prev = toView(pts[i - 1].x, pts[i - 1].y, trail.anchor);
      var cur = toView(pts[i].x, pts[i].y, trail.anchor);
      strokeLaser(prev, cur, GLOW_WIDTH * op, op * 0.35, 16 * op);
      laserCtx.beginPath();
      laserCtx.moveTo(prev.x, prev.y);
      laserCtx.lineTo(cur.x, cur.y);
      laserCtx.strokeStyle = "rgba(255,255,255," + op + ")";
      laserCtx.lineWidth = BASE_WIDTH * op;
      laserCtx.shadowBlur = 6 * op;
      laserCtx.stroke();
    }
    laserCtx.restore();
    return visible;
  }

  function tick() {
    var now = performance.now();
    laserCtx.clearRect(0, 0, laserCanvas.width / dpr, laserCanvas.height / dpr);
    laserCtx.shadowBlur = 0;
    var alive = [];
    var i;
    for (i = 0; i < trails.length; i += 1) {
      if (drawTrail(trails[i], now) || !trails[i].closed) alive.push(trails[i]);
    }
    trails = alive;
    if (trails.length > 0 || laserDrawing) rafId = requestAnimationFrame(tick);
    else rafId = null;
  }

  function startMarker(anchor, point) {
    markerDragging = true;
    dragAnchor = anchor;
    dragStart = { x: point.x, y: point.y };
    dragCurrent = { x: point.x, y: point.y };
    drawMarker();
  }

  function moveMarker(event) {
    dragCurrent = contentPoint(event, dragAnchor);
    drawMarker();
  }

  function dragBox(anchor, start, current) {
    return {
      anchor: anchor,
      x: Math.min(start.x, current.x),
      y: Math.min(start.y, current.y),
      w: Math.abs(current.x - start.x),
      h: Math.abs(current.y - start.y)
    };
  }

  function finishMarker() {
    if (dragStart && dragCurrent) {
      var box = dragBox(dragAnchor, dragStart, dragCurrent);
      if (box.w > 4 && box.h > 4) rects.push(box);
    }
    markerDragging = false;
    dragStart = null;
    dragCurrent = null;
    dragAnchor = null;
    drawMarker();
  }

  function clearMarker() {
    rects = [];
    markerDragging = false;
    dragStart = null;
    dragCurrent = null;
    dragAnchor = null;
    drawMarker();
  }

  function paintRect(rect) {
    var origin = toView(rect.x, rect.y, rect.anchor);
    var clip = clipOf(rect.anchor);
    markerCtx.save();
    if (clip) {
      markerCtx.beginPath();
      markerCtx.rect(clip.x, clip.y, clip.w, clip.h);
      markerCtx.clip();
    }
    var fill = "rgba(" + MARKER_R + "," + MARKER_G + "," + MARKER_B + ",";
    markerCtx.fillStyle = fill + MARKER_ALPHA + ")";
    markerCtx.fillRect(origin.x, origin.y, rect.w, rect.h);
    markerCtx.strokeStyle = fill + BORDER_ALPHA + ")";
    markerCtx.lineWidth = 1.5;
    markerCtx.strokeRect(origin.x, origin.y, rect.w, rect.h);
    markerCtx.restore();
  }

  function drawMarker() {
    markerCtx.clearRect(0, 0, markerCanvas.width / dpr, markerCanvas.height / dpr);
    var i;
    for (i = 0; i < rects.length; i += 1) paintRect(rects[i]);
    if (markerDragging && dragStart && dragCurrent) {
      paintRect(dragBox(dragAnchor, dragStart, dragCurrent));
    }
  }

  document.addEventListener("scroll", drawMarker, true);
  window.addEventListener("resize", resize);
  resize();
})();
</script>
"""


def html_da_grade(grade: GradeDePoder) -> str:
    return html_das_grades((grade,))


def html_das_grades(grades: tuple[GradeDePoder, ...]) -> str:
    sections = "".join(_section(grade, index) for index, grade in enumerate(grades, start=1))
    return f"{_prefix()}{sections}{_suffix()}"


def _prefix() -> str:
    link = (
        f'<link rel="stylesheet" href="{_BOOTSTRAP}" '
        f'integrity="{_BOOTSTRAP_HASH}" crossorigin="anonymous">'
    )
    return (
        '<!DOCTYPE html>\n<html lang="pt-BR" data-bs-theme="dark">\n<head>\n'
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        "<title>Poder do partido</title>\n"
        f"{_THEME_BOOT}{link}\n<style>{_STYLE}</style>\n</head>\n"
        "<body>\n"
        '<a class="pular" href="#conteudo">Ir para o conteúdo</a>\n'
        '<main id="conteudo" class="container-fluid py-4">\n'
        '<header class="masthead">\n<div>\n'
        '<h1 class="h3 mb-4">Poder do partido</h1>\n'
        '<p class="escala"><span class="escala-barra" aria-hidden="true"></span>'
        "A célula mais intensa é a maior fatia deste recorte.</p>\n"
        '<p class="atalhos"><kbd>K</kbd> laser <kbd>M</kbd> marca-texto '
        "<kbd>Esc</kbd> solta o laser "
        '<span id="ferramenta" aria-live="polite"></span></p>\n'
        "</div>\n"
        '<div class="temas" role="group" aria-label="Tema">\n'
        '<button type="button" data-tema="light" aria-pressed="false">Claro</button>\n'
        '<button type="button" data-tema="dark" aria-pressed="true">Escuro</button>\n'
        "</div>\n</header>\n"
        '<nav class="indice" aria-label="Recortes"></nav>\n'
    )


def _suffix() -> str:
    return f"{_notes()}\n</main>\n{_SCRIPT}{_POINTER}</body>\n</html>\n"


def _notes() -> str:
    items = "".join(f"<li>{note}</li>" for note in _NOTES)
    return f'<ul class="notas">{items}</ul>'


def _section(grade: GradeDePoder, index: int) -> str:
    body = _municipio_tables(grade) if grade.nivel == "municipio" else _table(grade, grade.linhas)
    heading = _heading(grade)
    return (
        f'<section class="mb-5" id="recorte-{index}">'
        f'<h2 class="h4">{heading}</h2>{body}</section>\n'
    )


def _heading(grade: GradeDePoder) -> str:
    return _HEADINGS[grade.nivel](grade)


def _municipio_heading(grade: GradeDePoder) -> str:
    return f"Por município — {grade.ano}, turno {grade.turno}, {escape(grade.cargo)}"


def _estado_heading(grade: GradeDePoder) -> str:
    return f"Por estado — {grade.ano}, turno {grade.turno}, {escape(grade.cargo)}"


def _regiao_heading(_grade: GradeDePoder) -> str:
    legend = ", ".join(f"{escape(region.sigla)} {escape(region.name)}" for region in REGIONS)
    return f"Por região — {legend}"


def _pais_heading(grade: GradeDePoder) -> str:
    return f"No país — {grade.ano}, turno {grade.turno}, {escape(grade.cargo)}"


def _municipio_tables(grade: GradeDePoder) -> str:
    # A escala de cor continua a da grade inteira, para os estados serem comparáveis.
    named, loose = _split_states(grade.linhas)
    blocks = [_state_table(grade, code, rows) for code, rows in named]
    if loose:
        blocks.append(_table(grade, loose))
    return "".join(blocks)


def _split_states(
    rows: tuple[LinhaGrade, ...],
) -> tuple[tuple[tuple[str, tuple[LinhaGrade, ...]], ...], tuple[LinhaGrade, ...]]:
    grouped = _grouped(rows)
    named = tuple((code, tuple(grouped[code])) for code in UF_CODES if code in grouped)
    return named, tuple(grouped.get(None, ()))


def _grouped(rows: tuple[LinhaGrade, ...]) -> dict[str | None, list[LinhaGrade]]:
    grouped: dict[str | None, list[LinhaGrade]] = {}
    for row in rows:
        grouped.setdefault(_state_code(row.nome), []).append(row)
    return grouped


def _state_code(nome: str) -> str | None:
    found = _STATE_SUFFIX.search(nome)
    if found is None:
        return None
    code = found.group(1)
    if code not in UF_NAMES:
        return None
    return code


def _state_table(grade: GradeDePoder, code: str, rows: tuple[LinhaGrade, ...]) -> str:
    title = f"{escape(uf_name(code))} ({escape(code)})"
    return f'<h3 class="h5 mt-4 mb-2">{title}</h3>{_table(grade, rows)}'


def _table(grade: GradeDePoder, rows: tuple[LinhaGrade, ...]) -> str:
    largest = _largest(grade)
    parties = "".join(
        f'<th aria-sort="none" scope="col" title="Partido {party}">{party}</th>'
        for party in grade.colunas
    )
    body = "".join(_row(row, largest) for row in rows)
    head = (
        "<thead><tr>"
        '<th class="lugar" scope="col" aria-sort="none">Lugar</th>'
        '<th class="validos" aria-sort="none">Votos válidos</th>'
        f"{parties}</tr></thead>"
    )
    return (
        '<div class="table-responsive grade-scroll">'
        '<table class="table table-sm grade mb-4">'
        f"{head}<tbody>{body}</tbody></table></div>"
    )


def _row(row: LinhaGrade, largest: Fraction) -> str:
    validos = _votos_validos(row)
    place = (
        f'<td class="lugar" scope="row" data-ord="{escape(row.nome)}">'
        f"{escape(row.nome)} <small>{escape(row.codigo)}</small></td>"
    )
    valid = f'<td class="validos" data-ord="{validos}">{_inteiro(validos)}</td>'
    cells = "".join(_cell(cell, validos, largest) for cell in row.celulas)
    return f"<tr>{place}{valid}{cells}</tr>"


def _votos_validos(row: LinhaGrade) -> int:
    return sum(cell.votos for cell in row.celulas)


def _inteiro(value: int) -> str:
    return f"{value:,}".replace(",", ".")


def _cell(cell: CelulaGrade, validos: int, largest: Fraction) -> str:
    share = _sobre_validos(cell.votos, validos)
    title = escape(_title(cell, validos))
    order = _round_half_up(share * _SORT_SCALE)
    return (
        f'<td class="fatia" data-ord="{order}" title="{title}" '
        f'style="{_style(share, largest)}">{_percent(share)}</td>'
    )


def _title(cell: CelulaGrade, validos: int) -> str:
    return (
        f"nominais {cell.votos_nominais}, legenda {cell.votos_legenda}, "
        f"votos {cell.votos}, votos válidos {validos}, "
        f"comparecimento {cell.comparecimento}"
    )


def _sobre_validos(votos: int, validos: int) -> Fraction:
    if validos == 0:
        return Fraction(0)
    return Fraction(votos, validos)


def _largest(grade: GradeDePoder) -> Fraction:
    largest = Fraction(0)
    for row in grade.linhas:
        validos = _votos_validos(row)
        for cell in row.celulas:
            share = _sobre_validos(cell.votos, validos)
            if share > largest:
                largest = share
    return largest


def _style(share: Fraction, largest: Fraction) -> str:
    relative = Fraction(0) if largest == 0 else share / largest
    paint = _rgb(_mix(_WHITE, _TEAL, relative))
    ink = _WHITE if relative > _TEXT_LIMIT else _INK
    return f"background-color:{paint};color:{_rgb(ink)}"


def _mix(
    origin: tuple[int, int, int],
    target: tuple[int, int, int],
    relative: Fraction,
) -> tuple[int, int, int]:
    return (
        _channel(origin[0], target[0], relative),
        _channel(origin[1], target[1], relative),
        _channel(origin[2], target[2], relative),
    )


def _channel(origin: int, target: int, relative: Fraction) -> int:
    mixed = Fraction(origin) + Fraction(target - origin) * relative
    return _round_half_up(mixed)


def _rgb(color: tuple[int, int, int]) -> str:
    red, green, blue = color
    return f"rgb({red},{green},{blue})"


def _percent(share: Fraction) -> str:
    whole, frac = divmod(_round_half_up(share * _PERCENT_SCALE), _TWO_DECIMALS)
    return f"{whole},{frac:02d}%"


def _round_half_up(value: Fraction) -> int:
    quotient, remainder = divmod(value.numerator, value.denominator)
    if remainder * 2 >= value.denominator:
        return quotient + 1
    return quotient


_HEADINGS: Final[Mapping[str, Callable[[GradeDePoder], str]]] = {
    "municipio": _municipio_heading,
    "uf": _estado_heading,
    "regiao": _regiao_heading,
    "pais": _pais_heading,
}
