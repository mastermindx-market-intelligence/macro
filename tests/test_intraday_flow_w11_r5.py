"""W11 r5 — recessive light chips, guarded stamp, skeleton a11y, subordinated degraded row.

r1–r4 repairs stay frozen. Page-scoped template CSS/markup/JS only.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from tests.test_intraday_flow_w11_r1 import _region, _run_node, _src
from tests.test_intraday_flow_w11_r2 import needs_node

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates" / "intraday_flow.html.j2"
EVIDENCE = ROOT / "mockups" / "evidence" / "intraday-flow-w11"

HOST_IDS = ("ift-hero-copy", "spot-grid", "ift-board-skel")


def _open_tag(src: str, ident: str) -> str:
    m = re.search(rf"<[^>]+id=\"{re.escape(ident)}\"[^>]*>", src)
    assert m, f"missing #{ident}"
    return m.group(0)


def _host_inner(src: str, ident: str, end: str) -> str:
    tag = re.search(rf"<[^>]+id=\"{re.escape(ident)}\"[^>]*>", src)
    assert tag, ident
    return src[tag.end() : src.index(end, tag.end())]


def _page_css(src: str) -> str:
    i = src.index("<style>")
    j = src.index("</style>", i)
    return src[i + 7 : j]


def _render_stamp(as_of_display) -> str:
    env = Environment(loader=FileSystemLoader(str(ROOT / "templates")), autoescape=False)
    html = env.get_template("intraday_flow.html.j2").render(
        intraday_flow={"as_of_display": as_of_display, "leaders": []}
    )
    return re.sub(r"<script\b[^>]*>.*?</script>", "", html, flags=re.S | re.I)


def _parse_rgba(value: str) -> tuple[int, int, int, float]:
    s = (value or "").strip().lower()
    if s in ("transparent", "none"):
        return (0, 0, 0, 0.0)
    m = re.match(r"rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)(?:\s*/\s*|\s*,\s*)?([\d.]+)?\s*\)", s)
    if m:
        r, g, b = (int(float(m.group(i))) for i in (1, 2, 3))
        a = float(m.group(4)) if m.group(4) is not None else 1.0
        return (r, g, b, a)
    m = re.match(r"color\(srgb\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)(?:\s*/\s*([\d.]+))?\)", s)
    assert m, f"unparseable color {value!r}"
    r, g, b = (int(round(float(m.group(i)) * 255)) for i in (1, 2, 3))
    a = float(m.group(4)) if m.group(4) is not None else 1.0
    return (r, g, b, a)


# ── m-2 light Tape chips ─────────────────────────────────────────────────────

def test_light_tape_chips_are_ghost_hairline_in_post_stack():
    src = _src()
    assert "post-stack: consolidate" in src
    light = src[src.index("post-stack: consolidate") :]
    assert "html[data-theme=\"light\"] body.page-intraday-flow .badge-blue" in light
    rule = _region(
        light,
        'html[data-theme="light"] body.page-intraday-flow .badge-blue',
        "body.page-intraday-flow .lens-pop",
    )
    assert "background:transparent" in rule
    assert "font-weight:500" in rule
    assert "border-color" in rule
    assert "color-mix(in srgb, var(--info)" not in rule
    # Dark filled treatment is unchanged and lives before the light override.
    dark = src[: src.index("post-stack: consolidate")]
    assert ".badge-blue { color:var(--ink-info, var(--info,#5b9bf0)); border-color:color-mix(in srgb,var(--info) 45%,transparent); background:color-mix(in srgb,var(--info) 10%,transparent); }" in dark


def test_light_tape_chip_computed_style_probe():
    """Light chip is transparent/near-canvas with a hairline; dark stays filled."""
    from playwright.sync_api import sync_playwright

    src = _src()
    css = _page_css(src)
    html = f"""<!doctype html>
<html>
<head>
<style>
:root {{ --info:#5b9bf0; --ink-info:#5b9bf0; --text:#d8dee8; --muted:#8b93a2; --panel:#14171e; --bg:#0a0c11; --line:#2a3140; }}
html[data-theme="light"] {{ --text:#1c2430; --muted:#5c6573; --panel:#ffffff; --bg:#e8ebf1; --line:#c9d0db; }}
{css}
</style>
</head>
<body class="page-intraday-flow">
<span class="badge badge-blue" id="chip">big block×1</span>
</body>
</html>"""

    def _probe(page, theme: str) -> dict:
        page.evaluate("(t) => document.documentElement.setAttribute('data-theme', t)", theme)
        return page.evaluate(
            """() => {
              const el = document.getElementById('chip');
              const cs = getComputedStyle(el);
              return {
                background: cs.backgroundColor,
                color: cs.color,
                borderWidth: cs.borderTopWidth,
                borderStyle: cs.borderTopStyle,
                borderColor: cs.borderTopColor,
                fontWeight: cs.fontWeight
              };
            }"""
        )

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.set_content(html, wait_until="load")
        light = _probe(page, "light")
        dark = _probe(page, "dark")
        browser.close()

    lr, lg, lb, la = _parse_rgba(light["background"])
    assert la < 0.08, light
    assert float(str(light["borderWidth"]).replace("px", "") or 0) >= 1, light
    assert light["borderStyle"] not in ("none", ""), light
    assert str(light["fontWeight"]) in ("400", "500"), light

    dr, dg, db, da = _parse_rgba(dark["background"])
    assert da >= 0.05, dark
    # Dark type stays the info ink, not the muted mix.
    assert str(dark["fontWeight"]) == "600", dark
    assert dark["background"] != light["background"]


def test_readme_records_recessive_light_chips():
    readme = (EVIDENCE / "README.md").read_text(encoding="utf-8")
    assert "Tape chips ghost/hairline in light — recessive by design" in readme


# ── m-4 guarded empty stamp ──────────────────────────────────────────────────

def test_empty_stamp_dict_renders_wordless_skeleton_not_dangling_prefix():
    html = _render_stamp({})
    stamp = _region(html, 'id="ift-stamp"', "</header>")
    assert "Board built" not in stamp
    assert "看板构建于" not in stamp
    assert "Board can't load right now" not in stamp
    assert "看板暂时无法加载" not in stamp
    assert "skel" in stamp
    assert "ift-skel-inline" in stamp
    # Whole pre-JS document must not dangle the prefix either.
    assert "Board built" not in html
    assert "看板构建于" not in html


def test_formed_stamp_still_prints_the_absolute_prefix():
    html = _render_stamp({"en": "10 Sep 11:34pm UTC", "zh": "9月10日 23:34 UTC"})
    stamp = _region(html, 'id="ift-stamp"', "</header>")
    assert "Board built 10 Sep 11:34pm UTC" in stamp
    assert "看板构建于9月10日 23:34 UTC" in stamp


# ── n-1 skeleton a11y ────────────────────────────────────────────────────────

def test_three_skeleton_hosts_carry_aria_busy_and_one_sr_only_each():
    src = _src()
    for ident in HOST_IDS:
        tag = _open_tag(src, ident)
        assert 'aria-busy="true"' in tag, ident
        assert "ift-skel-host" in tag, ident

    hero = _host_inner(src, "ift-hero-copy", 'class="hero-grid"')
    spot = _region(src, 'id="spot-grid"', "</section>")
    board = _region(src, 'id="ift-board-skel"', 'id="count-label"')
    for name, blob in (("hero", hero), ("spot", spot), ("board", board)):
        assert blob.count("sr-only") == 1, (name, blob.count("sr-only"))
        assert "Loading" in blob, name
        assert "加载中" in blob, name
        assert 'aria-hidden="true"' in blob, name
        # Decorative bars stay hidden; the sr-only text is not.
        assert re.search(r'class="sr-only"[^>]*aria-hidden', blob) is None, name

    assert src.count('aria-busy="true"') == 3


# ── n-2 subordinated degraded row ────────────────────────────────────────────

@needs_node
def test_degraded_row_auxiliary_cells_carry_muted_class_healthy_does_not():
    src = _src()
    js = "\n".join((
        "function lz(en, zh){ return '<span class=\"l-en\">'+en+'</span><span class=\"l-zh\">'+(zh||en)+'</span>'; }",
        "function esc(s){ return String(s==null?'':s); }",
        "function prettyBasket(){ return 'Mag7'; }",
        "function fmtDollar(v){ return v==null?'—':'$'+v; }",
        "function fmtPct(v){ return v==null?'':'+1.00%'; }",
        "function rangeWords(){ return ''; }",
        "function volumeWords(){ return {en:'2.4× normal · holding', zh:'2.4×正常 · 持稳', cls:'gauge-hi', pct:80}; }",
        "function dealerCompact(){ return '<div class=\"dealer-line\">ceiling ~$120 (hard) / floor ~$90</div>'; }",
        "function detailContent(){ return ''; }",
        "var flowRTH = true, openRows = {};",
        _region(src, "function buildRow", "function prettyBasket"),
    ))
    script = f"""
    {js}
    function row(key) {{
      return {{
        l: {{ticker:'NVDA', baskets:['mag7']}},
        q: key==='degraded' ? null : {{price:106, changePct:1.8}},
        p: {{vol_durability:0.85, higher_lows:0}},
        f: {{ncp:1, badges:['big block×1']}},
        conf: {{K:4}},
        st: key==='degraded'
          ? {{key:'degraded', reason_en:'Prices aren\\'t coming through — no read on this name right now', reason_zh:'行情未送达——该标的暂无判断', muted:true}}
          : {{key:'act', reason_en:'Reclaimed.', reason_zh:'收复。', muted:false}},
        rvol: 2.4, rangePos: null, vwapDelta: key==='degraded' ? null : 1.5,
        d: {{call_wall:120, put_wall:90, call_wall_hard:true}},
        meta: key==='degraded'
          ? {{lane:'lane-aside', en:'No read', zh:'暂无判断', order:6}}
          : {{lane:'lane-act', en:'Buy now', zh:'现在买入', order:0}}
      }};
    }}
    var deg = buildRow(row('degraded'));
    var ok = buildRow(row('act'));
    function tds(html, cls) {{
      var re = /<td class="([^"]*)">/g, m, out=[];
      while ((m = re.exec(html))) out.push(m[1]);
      return out;
    }}
    process.stdout.write(JSON.stringify({{
      deg: deg, ok: ok,
      degTds: tds(deg), okTds: tds(ok),
      degHasNoRead: /No read/.test(deg),
      degCopy: /2\\.4× normal · holding/.test(deg) && /ceiling/.test(deg) && /~call buying/.test(deg)
    }}));
    """
    out = _run_node(script)
    assert out["degHasNoRead"] is True
    assert out["degCopy"] is True, "facts stay; only treatment changes"
    aux = [c for c in out["degTds"] if "ift-aux-muted" in c]
    stance = [c for c in out["degTds"] if "stance-cell" in c]
    assert len(aux) == 4, out["degTds"]
    assert stance and "ift-aux-muted" not in stance[0]
    assert all("ift-aux-muted" not in c for c in out["okTds"]), out["okTds"]
    assert "ift-aux-muted" not in out["ok"]
    # No copy change on the degraded facts.
    assert "2.4× normal · holding" in out["deg"]
    assert "~call buying" in out["deg"]
