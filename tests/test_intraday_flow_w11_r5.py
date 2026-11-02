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


def test_light_post_stack_uses_theme_tokens_not_color_functions():
    """TOKENIZE-7070: added light post-stack lines must not carry color-mix/rgba/hex.

    Fails on head f4f17de018db: the W11 light block still inlines 11 color-mix()
    colour decisions (stamp mix, hairline mixes, skeleton wash, chip ink, tip
    shadow). Passes once those lines bind existing theme.css tokens only.
    """
    src = _src()
    light = src[src.index("post-stack: consolidate") : src.index("</style>")]
    assert "color-mix(" not in light
    assert re.search(r"\brgba?\s*\(", light) is None
    assert re.search(r"#[0-9a-fA-F]{3,8}\b", light) is None
    assert re.search(r"border-radius\s*:", light) is None
    assert "color:var(--ink-link, var(--link))" in light
    assert "color:var(--muted)" in light
    assert "border-color:var(--line)" in light
    assert "box-shadow:var(--card-shadow)" in light
    assert "background:transparent" in light
    assert "box-shadow:var(--popover-shadow)" in light or "box-shadow:none" in light


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


def test_manifest_declares_see_all_hover_and_focus_force_states():
    """TOKENIZE-7070 visual-evidence: light post-stack owns :hover/:focus-visible.

    Fails on head f4f17de018db: axes.force_states is a string list of named
    board states and has no hover/focus dict, so check_ui_visual_evidence
    cannot prove the See-all interaction. Passes once desktop/en dark+light
    cells carry applied_force_state for see-all-hover and see-all-focus.
    """
    manifest = json.loads((EVIDENCE / "manifest.json").read_text(encoding="utf-8"))
    defs = manifest["axes"]["force_states"]
    by_kind = {d["kind"]: d for d in defs if isinstance(d, dict)}
    assert by_kind["hover"]["name"] == "see-all-hover"
    assert by_kind["hover"]["value"] == ".ift-see-all"
    assert by_kind["focus"]["name"] == "see-all-focus"
    assert by_kind["focus"]["value"] == ".ift-see-all"
    states = [s for page in manifest["pages"] for s in page.get("states") or []]
    for name in ("see-all-hover", "see-all-focus"):
        pair = [
            s for s in states
            if s.get("force_state") == name
            and s.get("applied_force_state") == name
            and s.get("captured") is True
            and s.get("viewport") == "desktop"
            and s.get("locale") == "en"
        ]
        themes = {s.get("theme") for s in pair}
        assert themes == {"dark", "light"}, (name, themes)


def test_readme_records_recessive_light_chips():
    readme = (EVIDENCE / "README.md").read_text(encoding="utf-8")
    assert "Tape chips ghost/hairline in light — recessive by design" in readme


# ── TOKENIZE-7070-R2: radius token + no blocking emoji ───────────────────────

# The six pictographic glyphs the TOKENIZE-7070-R2 seat named. Dingbats
# (⚡ ⚪) and other pre-existing plane hits are out of this round's scope.
_NAMED_BLOCKING_EMOJI = {
    "\U0001F9ED": "compass",
    "\U0001F7E2": "green-circle",
    "\U0001F535": "blue-circle",
    "\U0001F3C3": "runner",
    "\U0001F7E0": "orange-circle",
    "\U0001F440": "eyes",
}
_NAMED_BLOCKING_EMOJI_RE = re.compile("|".join(re.escape(g) for g in _NAMED_BLOCKING_EMOJI))


def test_regime_dot_uses_tokenized_circular_radius():
    """TOKENIZE-7070-R2: .regime-dot must not ship border-radius:50%.

    Fails on head 45e7dc759e: `.regime-dot { ... border-radius:50%; ... }`.
    Passes once the circular radius binds the design-system --r-pill token
    (theme.css: --r-pill on a square box is a circle; was 50%).
    """
    css = _page_css(_src())
    match = re.search(r"\.regime-dot\s*\{[^}]+\}", css)
    assert match, "missing .regime-dot rule"
    rule = match.group(0)
    assert "border-radius:50%" not in rule.replace(" ", ""), rule
    assert re.search(r"border-radius\s*:\s*var\(\s*--r-pill", rule), rule


def test_template_has_no_blocking_emoji_codepoints():
    """TOKENIZE-7070-R2: pictographic emoji are banned in front-facing markup.

    Fails on head 45e7dc759e: templates/intraday_flow.html.j2 still carries
    U+1F9ED (compass at the ctx-watch row), U+1F7E2/U+1F535/U+1F7E0 (colored
    circles in the field guide and STANCE_META), U+1F3C3 (runner), U+1F440
    (eyes). Passes once those glyphs are gone: colored-circle markers use
    tokenized .regime-dot + lane classes; decorative compass/runner/eyes are
    removed and the bilingual words carry the meaning.
    """
    hits = []
    for i, line in enumerate(_src().splitlines(), 1):
        for match in _NAMED_BLOCKING_EMOJI_RE.finditer(line):
            glyph = match.group(0)
            hits.append((i, f"U+{ord(glyph):04X}", _NAMED_BLOCKING_EMOJI[glyph]))
    assert hits == [], f"named blocking emoji still in template: {hits}"


def test_field_guide_colored_circles_are_regime_dots_not_emoji():
    """TOKENIZE-7070-R2: field-guide state markers are .regime-dot + lane.

    Fails on head 45e7dc759e: the EN/ZH 'What each call means' lists lead with
    🟢/🔵/🟠 (and decorative 🏃/👀). Passes once Buy now / Almost ready /
    Take profits use .regime-dot.lane-* and In favour / Watch keep the plain
    bilingual words with no replacement iconography.
    """
    body = _region(_src(), "2 · What each call means", "3 · The options tape")
    for glyph in ("\U0001F7E2", "\U0001F535", "\U0001F3C3", "\U0001F7E0", "\U0001F440"):
        assert glyph not in body, f"{glyph!r} still in the field guide"
    assert 'class="regime-dot lane-act"' in body
    assert 'class="regime-dot lane-ready"' in body
    assert 'class="regime-dot lane-profit"' in body
    assert "<b>In favour</b>" in body
    assert "<b>Watch — don’t chase</b>" in body or "<b>Watch — don't chase</b>" in body
    assert "<b>走势占优</b>" in body
    assert "<b>观望——勿追</b>" in body


def test_hero_ctx_watch_has_no_compass_iconography():
    """TOKENIZE-7070-R2: decorative compass is removed; words stay.

    Fails on head 45e7dc759e: `<span class="ctx-ic">🧭</span>` wraps the
    ctx-watch row. Passes once that span is gone and the bilingual sentence
    remains.
    """
    src = _src()
    assert "\U0001F9ED" not in src
    watch = _region(src, 'id="ctx-watch"', "</div>")
    assert "The board below carries every name" in watch
    assert "下方看板列出每只标的及其结论依据。" in watch
    ctx = _region(src, 'class="hero-ctx"', 'id="ift-stamp"')
    assert "ctx-ic" not in ctx.split("ctx-watch")[1]


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
