"""Jinja environment for the GMI explorer pages.

The template-side twin of the specimen helpers in
``mockups/refs/gmi_explorer/build_specimens.py`` (``de``/``dz``/``n``/``ordered``/
``fill`` and the ``ICONS`` set). Macros live in ``templates/_gmi_macros.html.j2``;
this module only supplies the filters and globals they need, so the specimen
markup and the production markup are generated from one vocabulary.

Presentation only: nothing here reads data, decides a state, or styles a page.
"""
from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape
from markupsafe import Markup

from scripts.gmi_explorer.model import KIND_ORDER

#: specimen ICONS, verbatim (24x24 stroke paths).
ICONS = {
    "search": '<circle cx="11" cy="11" r="6.5"/><path d="M16 16l4.5 4.5"/>',
    "chev": '<path d="M9 6l6 6-6 6"/>',
    "arrow": '<path d="M4.5 12h15M13.5 6l6 6-6 6"/>',
    "refresh": '<path d="M19.5 12a7.5 7.5 0 1 1-2.2-5.3"/><path d="M19.5 4.5v4h-4"/>',
    "info": '<circle cx="12" cy="12" r="8.5"/><path d="M12 11v5.2M12 7.8h.01"/>',
    "alert": '<path d="M12 4.2l8.6 15.3H3.4z"/><path d="M12 10v4.2M12 17h.01"/>',
    "clock": '<circle cx="12" cy="12" r="8.5"/><path d="M12 7.5V12l3 2"/>',
    "ext": '<path d="M14 4.5h5.5V10M19.5 4.5L11 13"/><path d="M17.5 14v5.5h-13v-13H10"/>',
    "eyeoff": '<path d="M3.5 3.5l17 17"/><path d="M10.6 6.1c.5-.1.9-.1 1.4-.1 5 0 8.4 4.4 9.4 6-.5.8-1.5 2.2-3 3.5M6.5 7.5C4.7 8.8 3.4 10.6 2.6 12c1 1.6 4.4 6 9.4 6 1.6 0 3-.4 4.2-1"/><path d="M9.9 9.9a3 3 0 0 0 4.2 4.2"/>',
    "pause": '<circle cx="12" cy="12" r="8.5"/><path d="M10 9v6M14 9v6"/>',
    "file": '<path d="M7 3.5h7l4 4v13H7z"/><path d="M14 3.5v4h4"/>',
    "question": '<circle cx="12" cy="12" r="8.5"/><path d="M9.8 9.6a2.3 2.3 0 1 1 3.1 2.1c-.6.3-.9.8-.9 1.5M12 16.6h.01"/>',
    "list": '<path d="M9 6.5h11M9 12h11M9 17.5h11"/><path d="M4.5 6.5h.01M4.5 12h.01M4.5 17.5h.01"/>',
}
ARROW_LONG = ('<svg viewBox="0 0 28 12" fill="none" stroke="currentColor" stroke-width="1.6" '
              'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
              '<path d="M1 6h25M21 1.5L26 6l-5 4.5"/></svg>')
MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def de(iso: str) -> str:
    """'2026-10-21' -> '21 Oct 2026' (specimen ``de``)."""
    y, m, d = str(iso)[:10].split("-")
    return f"{int(d)} {MON[int(m) - 1]} {y}"


def dz(iso: str) -> str:
    """'2026-10-21' -> '2026年10月21日' (specimen ``dz``)."""
    y, m, d = str(iso)[:10].split("-")
    return f"{y}年{int(m)}月{int(d)}日"


def num(x: int) -> str:
    """Thousands separator (specimen ``n``)."""
    return f"{int(x):,}"


def fill(tpl: str, **kw) -> str:
    """Fill a DECK template's ``{name}`` slots; a surviving ``{`` is a bug."""
    out = str(tpl)
    for key, value in kw.items():
        out = out.replace("{" + key + "}", str(value))
    if "{" in out:
        raise ValueError(f"unfilled DECK slot in {out!r}")
    return out


def make_env(model: dict, templates_dir: Path) -> Environment:
    """Environment carrying the explorer filters, bound to one model."""
    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        autoescape=select_autoescape(["html", "j2"]),
        undefined=StrictUndefined,
    )
    micros = model["micros"]

    def ordered(mids):
        """Held, admitted, core, extended, then English name (specimen ``ordered``)."""
        return sorted(mids, key=lambda m: (KIND_ORDER[micros[m]["kind"]], micros[m]["en"].lower()))

    env.filters.update(ordered=ordered, num=num, de=de, dz=dz, fill=fill)
    env.globals["gmi_icons"] = {name: Markup(path) for name, path in ICONS.items()}
    env.globals["gmi_arrow_long"] = Markup(ARROW_LONG)
    return env
