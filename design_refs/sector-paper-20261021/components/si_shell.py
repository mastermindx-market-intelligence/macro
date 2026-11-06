"""Shared Sector Intelligence shell for the HTML specimens (wave 2, SIC-V2-C02/C03/C04/C09).

The production shell is `templates/_sector_central_paper.css.j2` (page header + workflow
switcher) and `templates/theme.js` (mobile nav toggle); their static copy is
`si_shell.css`. Both specimen builders import this module so the chrome is one source:

  nav()                 the canonical site nav (`brief_repair/nav_static.html`, trimmed to
                        the <nav> plus the static mobile toggle, PRC-031 ZH placeholder swap)
  page_header(asof)     the `.si-page-header` identity row (title · region · as-of)
  workflow_nav(current) the six-workflow switcher; every label is a copy-deck entry
  prov(items, ...)      a closed-by-default provenance drawer; producer field paths, codes
                        and deck `source` citations live here, never on the card face

Nothing user-facing is typed here: labels come from copy_deck.json (components.nav_*,
components.workflow_note, components.provenance_*). Hrefs are the production anchors of
templates/sector_central.html.j2:1494-1498 where the workflow exists there; Dossier and
Cycles use the anchors the integration plan names (#dossier, #cycles).
"""
import html, json, pathlib
HERE = pathlib.Path(__file__).resolve().parent
DECK = json.loads((HERE.parent / "copy_deck.json").read_text(encoding="utf-8"))
NAV_PATH = HERE.parent / "brief_repair" / "nav_static.html"

WORKFLOWS = (  # (key, deck key, href, production class family)
    ("brief", "nav_brief", "#overview", "si-view-btn"),
    ("explore", "nav_explore", "#map", "si-workflow-link"),
    ("dossier", "nav_dossier", "#dossier", "si-workflow-link"),
    ("research", "nav_research", "#tm-mount", "si-workflow-link"),
    ("watches", "nav_watches", "#accumulation-section", "si-workflow-link"),
    ("cycles", "nav_cycles", "#cycles", "si-workflow-link"),
)

def esc(s): return html.escape(str(s), quote=True)
def bi(en, zh): return f'<span class="l-en">{esc(en)}</span><span class="l-zh">{esc(zh)}</span>'
def D(sec, key, **fmt):
    e = DECK[sec][key]; en, zh = e["en"], e["zh"]
    if fmt: en, zh = en.format(**fmt), zh.format(**fmt)
    return bi(en, zh)

def nav(): return NAV_PATH.read_text(encoding="utf-8")

def page_header(asof_html=""):
    foot = f'<div class="si-side-foot"><span id="si-side-asof">{asof_html}</span><span id="si-side-grade"></span></div>' if asof_html else ""
    return (f'<header class="si-page-header"><div class="si-page-identity">'
            f'<h1 class="si-page-title">{D("brief","title")}</h1>'
            f'<span class="si-page-region"><span class="l-en">United States</span><span class="l-zh">美国</span></span>'
            f'</div>{foot}</header>')

def workflow_nav(current):
    assert current in {w[0] for w in WORKFLOWS}, current
    links = ""
    for key, dk, href, fam in WORKFLOWS:
        on = key == current
        cls = fam + (" on" if on else "")
        cur = ' aria-current="page"' if on else ""
        links += f'<a class="{cls}" data-si-workflow="{key}" href="{href}"{cur}>{D("components", dk)}</a>'
    e = DECK["components"]["workflow_aria"]
    return (f'<nav class="si-workflow" aria-label="{esc(e["en"])}" data-aria-zh="{esc(e["zh"])}">{links}'
            f'<span class="si-workflow-note">{D("components","workflow_note")}</span></nav>')

def prov(items, cls="", hint=True):
    """items: iterable of (label_html_or_text, value_html). Rendered as a closed <details>.
    Values are producer data (field paths, codes, deck sources) and render in mono/code."""
    rows = "".join(f'<div><dt>{k}</dt><dd>{v}</dd></div>' for k, v in items)
    h = f' <span class="cyc-prov-hint">{D("components","provenance_hint")}</span>' if hint else ""
    return (f'<details class="cyc-prov {cls}"><summary>{D("components","provenance_label")}{h}</summary>'
            f'<dl class="cyc-prov-body">{rows}</dl></details>')
