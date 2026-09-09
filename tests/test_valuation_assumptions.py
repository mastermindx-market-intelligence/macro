"""Tests for engine/valuation_assumptions.py (FROZEN SPEC B-F07-2)."""
from __future__ import annotations

import hashlib
import json
import logging
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import jinja2

from engine import valuation_assumptions as va
from engine import valuation_scenario as vs
from tests.test_valuation_scenario import BANNED_VOCAB, FIXTURE_ROW, _rows

ROOT = Path(__file__).resolve().parent.parent

# Render of templates/_valuation_scenario.html.j2 against the V1 AAPL-shaped
# fixture with t(en, zh) = en and deep_ids=[]. Committed so a V1 template
# edit that this packet must not make fails T9 even if git is unavailable.
GOLDEN_V1_SHA256 = "a8fef1b18bce0246bc884ef8c18c84a348cacb7f7ec1cdc42ed3dd3abf14493f"

# sha256 of V1's two files at this head. Fleet law: tests never read git history.
GOLDEN_V1_FILE_SHA256 = {
    "engine/valuation_scenario.py": "66340a2d03c171239547fea288b11b4bd5cdf698736d5f4bee6a019c73510d27",
    "templates/_valuation_scenario.html.j2": "6571613442a840588c19cb208a36f2aaf80eb3b0e85c74e3e9fdf1410353ceac",
}


def _v1_blob(**overrides):
    return vs.compute(_rows(**overrides), ticker="AAPL")


def _render_assumptions(blob, *, t=None):
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(str(ROOT / "templates")))
    env.globals["t"] = t or (lambda en, zh: en)
    tmpl = env.from_string("{% include '_valuation_assumptions.html.j2' %}")
    return tmpl.render(valuation_assumptions=blob, deep_ids=[])


def _render_v1(blob, *, t=None):
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(str(ROOT / "templates")))
    env.globals["t"] = t or (lambda en, zh: en)
    tmpl = env.from_string("{% include '_valuation_scenario.html.j2' %}")
    return tmpl.render(valuation_scenario=blob, deep_ids=[])


def _extract_js(html: str) -> str:
    for m in re.finditer(
        r"<script(?P<attrs>[^>]*)>(?P<body>.*?)</script>", html, re.DOTALL | re.IGNORECASE
    ):
        attrs = m.group("attrs") or ""
        if re.search(r'type\s*=\s*["\']application/json["\']', attrs, re.I):
            continue
        body = m.group("body").strip()
        if body:
            return body
    raise AssertionError("no executable inline script found in rendered partial")


def test_per_share_at_matches_v1_for_every_frozen_scenario():
    """R3(6): per_share_at at the cautious and upbeat triples equals V1's
    scenario per-share values for the fixture (and at base, for the same
    identity)."""
    blob = _v1_blob()
    assert blob is not None
    by_key = {s["key"]: s for s in blob["scenarios"]}
    ni = FIXTURE_ROW["ni"]
    revenue = FIXTURE_ROW["revenue"]
    shares = FIXTURE_ROW["shares"]
    for key, g, m_pp, mult in vs.SCENARIOS:
        got = va.per_share_at(ni, revenue, shares, g, m_pp, mult)
        expected = by_key[key]["per_share"]
        assert got == expected, (key, got, expected)
    assert by_key["cautious"]["per_share"] == va.per_share_at(
        ni, revenue, shares, -2, -1.5, 14
    )
    assert by_key["upbeat"]["per_share"] == va.per_share_at(
        ni, revenue, shares, 7, 1.5, 22
    )


def test_controls_blob_default_equals_v1_base_card():
    v1 = _v1_blob()
    blob = va.controls_blob(v1)
    assert blob is not None
    by_key = {s["key"]: s for s in v1["scenarios"]}
    base = by_key["base"]
    defaults = {c["key"]: c["default"] for c in va.CONTROLS}
    sd = blob["server_default"]
    assert sd["sales_growth_pct"] == defaults["sales_growth_pct"]
    assert sd["margin_delta_pp"] == defaults["margin_delta_pp"]
    assert sd["earnings_multiple"] == defaults["earnings_multiple"]
    expected_ps = va.per_share_at(
        blob["inputs"]["net_income"],
        blob["inputs"]["revenue"],
        blob["inputs"]["shares"],
        defaults["sales_growth_pct"],
        defaults["margin_delta_pp"],
        defaults["earnings_multiple"],
    )
    assert sd["per_share"] == expected_ps
    assert sd["per_share"] == base["per_share"]
    blob_defaults = {c["key"]: c["default"] for c in blob["controls"]}
    assert blob_defaults == defaults


def test_controls_blob_returns_the_null_shape_when_v1_base_card_disagrees(caplog):
    """Section 2.6's equality is enforced, not assumed (round 6 ruling R2(b)).

    round2() here is half-up; V1's round() is half-to-even, so an exact
    half-cent can split them. When the sandbox's first paint would not equal
    the Base card printed directly above it, the panel is not shown at all --
    controls_blob returns the same null shape every other unusable-V1 branch
    returns, rather than painting a figure that contradicts the authority.
    Round 8 R3(5): the guard logs a warning naming the issuer and both values
    before it returns that null.
    """
    v1 = _v1_blob()
    assert va.controls_blob(v1) is not None
    by_key = {s["key"]: s for s in v1["scenarios"]}
    sandbox_ps = va.controls_blob(v1)["server_default"]["per_share"]
    assert sandbox_ps == by_key["base"]["per_share"]
    for delta in (0.01, -0.01):
        perturbed = json.loads(json.dumps(v1))
        v1_ps = None
        for s in perturbed["scenarios"]:
            if s["key"] == "base":
                s["per_share"] = round(s["per_share"] + delta, 2)
                v1_ps = s["per_share"]
        with caplog.at_level(logging.WARNING, logger="engine.valuation_assumptions"):
            caplog.clear()
            assert va.controls_blob(perturbed) is None, delta
        assert "AAPL" in caplog.text
        assert str(sandbox_ps) in caplog.text
        assert str(v1_ps) in caplog.text


def test_controls_blob_is_none_when_v1_is_not_usable():
    assert va.controls_blob(None) is None
    assert va.controls_blob(_v1_blob(ni=None)) is None
    assert va.controls_blob(_v1_blob(ni=0)) is None
    assert va.controls_blob(_v1_blob(ni=-5.0)) is None
    assert va.controls_blob(_v1_blob(revenue=None)) is None
    assert va.controls_blob(_v1_blob(shares=0)) is None
    revenue = 1.0e11
    tiny_ni = revenue * 0.001  # 0.1% margin, under the 1% floor
    thin = va.controls_blob(_v1_blob(ni=tiny_ni, revenue=revenue))
    # Seat ruling R5, issued in the seat's round-4 rulings
    # (ext/rul_m_f07_2_h4.txt) and recorded on this PR at ratification: the
    # thin artifact shape is the permitted section 2.6 exception, and its key
    # set is fixed at exactly these nine keys.
    assert thin is not None
    assert thin.get("too_thin_base") is True
    assert set(thin) == {
        "schema",
        "ticker",
        "tier",
        "fy",
        "period_end",
        "source",
        "too_thin_base",
        "inputs",
        "margin_base_floor",
    }
    assert "controls" not in thin
    assert "server_default" not in thin
    assert "presets" not in thin


def test_margin_too_thin_and_nonpositive_never_render_a_number():
    revenue = 1.0e11
    ni_1_2_pct = revenue * 0.012
    assert va.per_share_at(ni_1_2_pct, revenue, FIXTURE_ROW["shares"], 3, -1.5, 18) is None
    # Round 8 R3(3): a 1.2% margin base clears the floor, so the interactive
    # panel ships, and the too-thin sentence is pinned verbatim in both
    # languages on that render.
    blob_12 = va.controls_blob(_v1_blob(ni=ni_1_2_pct, revenue=revenue))
    assert blob_12 is not None
    assert blob_12.get("too_thin_base") is not True
    html_12 = _render_assumptions(blob_12, t=lambda en, zh: f"{en}|{zh}")
    assert (
        "Margins are too thin at this setting to produce a number."
        "|在该设置下利润率过低，无法算出数值。"
    ) in html_12
    # A positive raw under half a cent rounds to 0.00, which is not paintable:
    # per_share_at returns None, matching the JS twin (see T5's grid point).
    assert va.per_share_at(1.0e6, 1.0e8, 1.0e12, 0, 0, 8) is None
    tiny_ni = revenue * 0.001
    thin = va.controls_blob(_v1_blob(ni=tiny_ni, revenue=revenue))
    assert thin is not None and thin.get("too_thin_base") is True
    html = _render_assumptions(thin, t=lambda en, zh: f"{en}|{zh}")
    assert "Not enough reported margin to run this.|披露的利润率基数不足，无法进行试算。" in html
    # Round 6 ruling R2(j): the floor branch is a panel like every other module
    # on the dossier -- it carries the same heading (so "this" has an
    # antecedent), the same footer, and the same .rv reveal class. Section 2.3's
    # "and nothing else" is read as "no controls, no output, no bridge".
    assert '<section class="mod rv" id="valuation-assumptions-floor"' in html
    assert "Try your own assumptions|试试你自己的假设" in html
    assert "<h2>" in html
    assert 'class="mod-ft"' in html
    assert "Research display only — not advice.|仅供研究展示，非投资建议。" in html
    assert "Move the three inputs" not in html
    assert "va-lede" not in html
    assert "va-ctls" not in html
    assert "va-bridge" not in html
    assert "va-out" not in html
    assert "$-" not in html
    assert "$" not in html


def test_js_and_python_agree_stringwise_on_a_dense_grid():
    node = shutil.which("node")
    assert node, "node is required for T5; install Node.js (fail loudly, never skip)"
    v1 = _v1_blob()
    blob = va.controls_blob(v1)
    html = _render_assumptions(blob)
    js = _extract_js(html)
    growths = [-10, -8, -5, -2, 0, 1, 3, 5, 7, 10, 15, 20]
    margins = [-3.0, -1.5, -0.5, 0.0, 0.1, 1.5, 3.0]
    multiples = [8, 14, 18, 22, 28, 35]
    grid = [
        {"g": g, "m": m, "x": x}
        for g in growths
        for m in margins
        for x in multiples
    ]
    assert len(grid) >= 400, len(grid)
    # Exact-half-cent probe: construct a raw value of N + 0.005 by scaling
    # net income so Python/JS half-up must agree on the tie.
    ni = FIXTURE_ROW["ni"]
    revenue = FIXTURE_ROW["revenue"]
    shares = FIXTURE_ROW["shares"]
    half_cent_ni = (100.005 * shares) / (1.03 * 18)
    grid.append({"g": 3, "m": 0, "x": 18, "ni": half_cent_ni})
    # Sub-half-cent probe: raw = 1e6 * 1 * 1 * 8 / 1e12 = 8e-6, which round2
    # collapses to 0. Both languages must answer null, not "0.00".
    grid.append(
        {"g": 0, "m": 0, "x": 8, "ni": 1.0e6, "revenue": 1.0e8, "shares": 1.0e12}
    )

    payload = {
        "ni": ni,
        "revenue": revenue,
        "shares": shares,
        "grid": grid,
    }
    with tempfile.TemporaryDirectory() as td:
        tdir = Path(td)
        (tdir / "vs_math.js").write_text(js, encoding="utf-8")
        (tdir / "grid.json").write_text(json.dumps(payload), encoding="utf-8")
        harness = (
            "const math = require('./vs_math.js');\n"
            "const fs = require('fs');\n"
            "const p = JSON.parse(fs.readFileSync('./grid.json', 'utf8'));\n"
            "const out = p.grid.map((pt) => {\n"
            "  const ni = (pt.ni == null) ? p.ni : pt.ni;\n"
            "  const rev = (pt.revenue == null) ? p.revenue : pt.revenue;\n"
            "  const sh = (pt.shares == null) ? p.shares : pt.shares;\n"
            "  const v = math.perShareAt(ni, rev, sh, pt.g, pt.m, pt.x);\n"
            "  return v == null ? 'null' : math.format2(v);\n"
            "});\n"
            "process.stdout.write(JSON.stringify(out));\n"
        )
        (tdir / "harness.js").write_text(harness, encoding="utf-8")
        proc = subprocess.run(
            [node, "harness.js"],
            cwd=tdir,
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 0, proc.stderr
        js_out = json.loads(proc.stdout)

    py_out = []
    for pt in grid:
        use_ni = pt.get("ni", ni)
        use_rev = pt.get("revenue", revenue)
        use_sh = pt.get("shares", shares)
        got = va.per_share_at(use_ni, use_rev, use_sh, pt["g"], pt["m"], pt["x"])
        py_out.append("null" if got is None else f"{got:.2f}")
    assert js_out == py_out
    # The sub-half-cent probe is the last grid point and must be null on both
    # sides, not "0.00" on one of them.
    assert py_out[-1] == "null" and js_out[-1] == "null"


def test_no_banned_vocabulary_and_no_tax_declaration_term():
    partial = ROOT / "templates" / "_valuation_assumptions.html.j2"
    text = partial.read_text(encoding="utf-8")
    lowered = text.lower()
    for word in BANNED_VOCAB:
        assert word.lower() not in lowered, f"banned word {word!r} found in partial"
    assert "申报" not in text
    assert "披露" in text


def test_script_injects_no_style_and_stores_nothing():
    blob = va.controls_blob(_v1_blob())
    html = _render_assumptions(blob)
    js = _extract_js(html)
    banned = (
        "createElement('style'",
        'createElement("style"',
        "styleSheets",
        "insertRule",
        ".style.",
        "style.textContent",
        "localStorage",
        "sessionStorage",
        "document.cookie",
        "fetch(",
        "XMLHttpRequest",
        "navigator.sendBeacon",
    )
    for token in banned:
        assert token not in js, token


def test_bilingual_parity_and_no_zh_in_attributes():
    partial = ROOT / "templates" / "_valuation_assumptions.html.j2"
    text = partial.read_text(encoding="utf-8")
    n_plain = 0
    for m in re.finditer(r"t\(\s*'([^']*)'\s*,\s*'([^']*)'\s*\)", text):
        n_plain += 1
        en, zh = m.group(1), m.group(2)
        assert zh.strip() != "", f"empty ZH for en={en!r}"
    assert n_plain >= 1
    for m in re.finditer(r'title="[^"]*[一-鿿][^"]*"', text):
        raise AssertionError(f"ZH text found in a title= attribute: {m.group(0)!r}")
    for m in re.finditer(r'aria-label="[^"]*[一-鿿][^"]*"', text):
        raise AssertionError(f"ZH text found in an aria-label= attribute: {m.group(0)!r}")
    assert "同一批披露数据" in text
    assert "套用在按 SEC 披露的" in text
    assert "基准情景为 $" in text
    # Frozen §2.5 ZH footnote restored (round 8 R2). Round 6 had rewritten it
    # to '8× 至 35×' to match the readout; that departure is reversed. The
    # unit-forbid regex exempts this frozen footnote and the frozen control
    # label 市盈率倍数 — the only two lawful 倍 uses.
    frozen_footnote_zh = "市盈率倍数 8 倍至 35 倍。"
    frozen_label_zh = "市盈率倍数"
    assert frozen_footnote_zh in text
    remainder = text.replace(frozen_footnote_zh, "").replace(frozen_label_zh, "")
    for m in re.finditer(r"\d\s*倍", remainder):
        raise AssertionError(f"ZH multiple printed with the 倍 unit: {m.group(0)!r}")
    # The live output region's accessible name comes from the bilingual t()
    # label next to it, not from a static English attribute.
    assert 'aria-labelledby="va-out-k"' in text
    assert "aria-label=" not in text
    # One minus-sign convention, the site's: ASCII hyphen-minus everywhere,
    # the same character V1's cards and this panel's own readouts print.
    assert "−" not in text, "U+2212 MINUS SIGN found; the site writes ASCII '-'"


def test_v1_panel_output_is_byte_identical():
    blob = vs.compute(_rows(), price=319.97, asof="2026-09-05", ticker="AAPL")
    html = _render_v1(blob)
    assert hashlib.sha256(html.encode("utf-8")).hexdigest() == GOLDEN_V1_SHA256
    assert html == GOLDEN_V1_HTML
    for rel, pin in GOLDEN_V1_FILE_SHA256.items():
        digest = hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()
        assert digest == pin, rel


def test_langchange_binds_on_document_and_bridge_keeps_twins():
    text = (ROOT / "templates" / "_valuation_assumptions.html.j2").read_text(encoding="utf-8")
    assert 'document.addEventListener("langchange"' in text
    assert "documentElement.addEventListener" not in text
    blob = va.controls_blob(_v1_blob())
    html = _render_assumptions(blob)
    m = re.search(r'id="va-bridge"[^>]*>(.*?)</p>', html, re.DOTALL)
    assert m, "bridge markup missing"
    inner = m.group(1)
    assert 'class="l-en"' in inner
    assert 'class="l-zh"' in inner
    js = _extract_js(html)
    assert "bridge.textContent" not in js
    # Round 6 ruling R2(g): each twin declares its own language in the markup;
    # nothing stamps one language on the wrapper that holds both, so no hidden
    # twin is ever declared in the language it is not written in.
    assert 'setAttribute("lang"' not in js
    assert 'class="l-en" lang="en"' in inner
    assert 'class="l-zh" lang="zh-CN"' in inner
    live = re.search(r'<div id="va-out"[^>]*>', html)
    assert live, "the live region is missing"
    assert "lang=" not in live.group(0)
    assert 'id="valuation-assumptions"' in html


def _apply_triple_literal_args(js: str):
    """Every applyTriple(...) call site whose ARGUMENT LIST holds a numeric
    literal, in any position. Round 4's backdoor was
    `applyTriple(sd.sales_growth_pct, -3, 12)`, which a first-argument-only
    pin does not catch (round 6 ruling R2(a))."""
    bad = []
    for m in re.finditer(r"applyTriple\s*\(([^)]*)\)", js):
        args = m.group(1)
        if re.search(r"(?<![\w.$])-?\d", args):
            bad.append(m.group(0))
    return bad


def _reveal_overrides_for_section(css_text: str):
    """Every CSS rule whose SELECTOR names the module's section id, in any
    selector form, and whose body touches opacity or transform. The round-4
    override was welded on `#valuation-assumptions{opacity:1}`; `.mod#id`,
    `[id="..."]`, `html #id.rv` and friends are the same override
    (round 6 ruling R2(a))."""
    bad = []
    # Jinja comments are not markup; the partial's own header comment says the
    # words "<style> block", which would otherwise open a phantom block here.
    body = re.sub(r"\{#.*?#\}", "", css_text, flags=re.DOTALL)
    for block in re.findall(r"<style[^>]*>(.*?)</style>", body, re.DOTALL | re.IGNORECASE):
        for rule in re.finditer(r"([^{}]+)\{([^{}]*)\}", block):
            selector, decls = rule.group(1), rule.group(2)
            if "valuation-assumptions" not in selector:
                continue
            if "opacity" in decls or "transform" in decls:
                bad.append(selector.strip() + " {" + decls.strip() + "}")
    return bad


def test_no_capture_harness_hook_and_no_reveal_override():
    """The shipped panel carries nothing that exists only to serve a screenshot.

    Round 4 ruling R1/R2: no body-class backdoor, no MutationObserver, no
    re-typed assumption literals, and no CSS or class that opts this one module
    out of the dossier's own scroll reveal.
    """
    text = (ROOT / "templates" / "_valuation_assumptions.html.j2").read_text(encoding="utf-8")
    blob = va.controls_blob(_v1_blob())
    html = _render_assumptions(blob)
    js = _extract_js(html)
    for hook in ("va-moved", "MutationObserver", "applyMovedIfForced"):
        assert hook not in text, hook
        assert hook not in js, hook
    # The three assumptions are only ever read from the artifact, never re-typed
    # -- in ANY argument position, not just the first.
    assert _apply_triple_literal_args(js) == []
    # The pin itself is checked against the exact round-4 offending call and
    # against the two call sites that are allowed to stand, so it can never
    # again be narrower than the body says it is.
    assert _apply_triple_literal_args(
        "applyTriple(sd.sales_growth_pct, -3, 12);"
    ) == ["applyTriple(sd.sales_growth_pct, -3, 12)"]
    assert _apply_triple_literal_args("applyTriple(-3, 12, 18);") == [
        "applyTriple(-3, 12, 18)"
    ]
    assert _apply_triple_literal_args(
        "applyTriple(p.sales_growth_pct, p.margin_delta_pp, p.earnings_multiple);"
        "applyTriple(sd.sales_growth_pct, sd.margin_delta_pp, sd.earnings_multiple);"
    ) == []
    # The module reveals like every other .rv module: no completed-reveal class
    # baked into the markup, and no opacity/transform override under ANY
    # selector form that names the section id.
    assert 'class="mod rv"' in html
    assert "mod rv in" not in html
    assert _reveal_overrides_for_section(text) == []
    assert _reveal_overrides_for_section(
        "<style>.mod#valuation-assumptions{opacity:1;}</style>"
    ) == [".mod#valuation-assumptions {opacity:1;}"]
    assert _reveal_overrides_for_section(
        '<style>html.has-js [id="valuation-assumptions"]{transform:none}</style>'
    ) == ['html.has-js [id="valuation-assumptions"] {transform:none}']
    assert _reveal_overrides_for_section(
        "<style>#valuation-assumptions-floor.rv{opacity:1}</style>"
    ) == ["#valuation-assumptions-floor.rv {opacity:1}"]
    # The sandbox figure is never louder than V1's authoritative card value
    # (templates/_valuation_scenario.html.j2: .vs-card .vv is 20px/800, no glow).
    num_rule = re.search(r"\.va-out-num\{([^}]*)\}", text)
    assert num_rule, "the .va-out-num rule is missing"
    assert "text-shadow" not in num_rule.group(1)
    sizes = [float(s) for s in re.findall(r"\.va-out-num\{[^}]*?font-size:([0-9.]+)px", text)]
    assert sizes and max(sizes) <= 20.0, sizes


def test_no_signed_zero_and_one_sign_convention_across_both_twins():
    """A delta that rounds to zero carries no sign at all (round 6 ruling
    R2(c)): "-0.0%" beside two equal dollar figures is a formatting artifact,
    and the server render prints exactly what the JS twin prints."""
    node = shutil.which("node")
    assert node, "node is required; install Node.js (fail loudly, never skip)"
    blob = va.controls_blob(_v1_blob())
    html = _render_assumptions(blob)
    js = _extract_js(html)
    cases = [-0.049, -0.0001, 0, 0.049, -0.06, 0.06, -40.83, 34.52, 3, -1.5]
    expected = ["0.0", "0.0", "0.0", "0.0", "-0.1", "+0.1", "-40.8", "+34.5", "+3.0", "-1.5"]
    with tempfile.TemporaryDirectory() as td:
        tdir = Path(td)
        (tdir / "vs_math.js").write_text(js, encoding="utf-8")
        (tdir / "cases.json").write_text(json.dumps(cases), encoding="utf-8")
        (tdir / "harness.js").write_text(
            "const math = require('./vs_math.js');\n"
            "const fs = require('fs');\n"
            "const cs = JSON.parse(fs.readFileSync('./cases.json', 'utf8'));\n"
            "process.stdout.write(JSON.stringify(cs.map((c) => math.signedPct(c, 1))));\n",
            encoding="utf-8",
        )
        proc = subprocess.run([node, "harness.js"], cwd=tdir, capture_output=True, text=True)
        assert proc.returncode == 0, proc.stderr
        assert json.loads(proc.stdout) == expected
    # No signed zero anywhere a reader can see it, in either language, and the
    # server-rendered readouts are the strings signedPct produces for the same
    # defaults ("+3.0" for growth 3, "0.0" for margin 0). The script block is
    # excluded because its comment quotes the artifact it exists to prevent.
    visible = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.I)
    assert "-0.0" not in visible
    assert 'id="va-read-sales_growth_pct">+3.0%<' in html
    assert 'id="va-read-margin_delta_pp">0.0<' in html
    assert "Your assumptions give $%.2f (0.0%%)." % blob["server_default"]["per_share"] in html
    assert "你的假设得出 $%.2f（0.0%%）。" % blob["server_default"]["per_share"] in html


def test_live_region_is_a_status_and_its_label_sits_outside_it():
    """Round 6 ruling R2(f). role=generic is name-prohibited, so the
    aria-labelledby name is liable to be discarded; role="status" is a live
    region that takes a name. The label itself moves out of the live region so
    a slider tick announces the value, not the label with the value."""
    blob = va.controls_blob(_v1_blob())
    html = _render_assumptions(blob)
    m = re.search(r'<div id="va-out"[^>]*>', html)
    assert m, "the live region is missing"
    tag = m.group(0)
    assert 'role="status"' in tag
    assert 'aria-live="polite"' in tag
    assert 'aria-labelledby="va-out-k"' in tag
    # The label precedes the live region, so it cannot be a descendant of it.
    assert html.index('id="va-out-k"') < html.index(tag)
    # Both still sit inside the one output card.
    assert html.index('<div class="va-out">') < html.index('id="va-out-k"')
    # The value, the null line and the bridge all follow the live region's
    # opening tag, so they are what a status announcement carries.
    for node_id in ('id="va-out-num"', 'id="va-out-null"', 'id="va-bridge"'):
        assert html.index(tag) < html.index(node_id), node_id


def test_no_js_default_state_is_correct_and_complete():
    """T10 (round 8 R1 / R3(4)): server HTML ships disabled inputs, the no-JS
    sentence in place of the move sentence, min/max/step on each input, and
    each readout span.
    """
    blob = va.controls_blob(_v1_blob())
    html = _render_assumptions(blob)
    stripped = re.sub(
        r"<script(?![^>]*type=\"application/json\")[^>]*>.*?</script>",
        "",
        html,
        flags=re.DOTALL | re.IGNORECASE,
    )
    assert f"${blob['server_default']['per_share']:.2f}" in stripped
    assert 'id="va-ctl-sales_growth_pct"' in stripped
    assert 'id="va-ctl-margin_delta_pp"' in stripped
    assert 'id="va-ctl-earnings_multiple"' in stripped
    assert 'value="3"' in stripped or "value='3'" in stripped
    assert 'value="0"' in stripped or "value='0'" in stripped
    assert 'value="18"' in stripped or "value='18'" in stripped
    by_key = {c["key"]: c for c in blob["controls"]}
    for key, el_id in (
        ("sales_growth_pct", "va-ctl-sales_growth_pct"),
        ("margin_delta_pp", "va-ctl-margin_delta_pp"),
        ("earnings_multiple", "va-ctl-earnings_multiple"),
    ):
        tag = re.search(rf"<input[^>]*id=\"{el_id}\"[^>]*>", stripped)
        assert tag, el_id
        src = tag.group(0)
        assert "disabled" in src, el_id
        spec = by_key[key]
        assert f'min="{spec["min"]}"' in src or f"min='{spec['min']}'" in src
        assert f'max="{spec["max"]}"' in src or f"max='{spec['max']}'" in src
        assert f'step="{spec["step"]}"' in src or f"step='{spec['step']}'" in src
        assert f'id="va-read-{key}"' in stripped
    assert "These inputs need JavaScript to move. The base case is shown." in stripped
    zh_html = _render_assumptions(blob, t=lambda en, zh: zh)
    zh_stripped = re.sub(
        r"<script(?![^>]*type=\"application/json\")[^>]*>.*?</script>",
        "",
        zh_html,
        flags=re.DOTALL | re.IGNORECASE,
    )
    assert "这些输入需要启用 JavaScript 才能调整，当前显示的是基准情形。" in zh_stripped
    nojs_tag = re.search(r"<p[^>]*id=\"va-lede-nojs\"[^>]*>", stripped)
    assert nojs_tag and "hidden" not in nojs_tag.group(0)
    js_tag = re.search(r"<p[^>]*id=\"va-lede-js\"[^>]*>", stripped)
    assert js_tag and "hidden" in js_tag.group(0)


def test_js_enables_inputs_and_shows_the_move_sentence():
    """Round 8 R1 JS-path: bootstrap removes disabled and reveals the move
    sentence. Run under node against a minimal document mock of the served
    markup, not against source greps.
    """
    node = shutil.which("node")
    assert node, "node is required; install Node.js (fail loudly, never skip)"
    blob = va.controls_blob(_v1_blob())
    html = _render_assumptions(blob)
    js = _extract_js(html)
    island = re.search(
        r'<script type="application/json" id="vs-assumption-inputs">(.*?)</script>',
        html,
        re.DOTALL,
    )
    assert island, "the JSON island is missing"
    payload = json.loads(island.group(1))
    with tempfile.TemporaryDirectory() as td:
        tdir = Path(td)
        (tdir / "boot.js").write_text(js, encoding="utf-8")
        (tdir / "blob.json").write_text(json.dumps(payload), encoding="utf-8")
        (tdir / "harness.js").write_text(
            """
const fs = require('fs');
const vm = require('vm');
const data = JSON.parse(fs.readFileSync('./blob.json', 'utf8'));
const src = fs.readFileSync('./boot.js', 'utf8');
function el(id, attrs) {
  const o = {
    id: id,
    attrs: Object.assign({}, attrs),
    value: (attrs && attrs.value != null) ? String(attrs.value) : '',
    hidden: !!(attrs && attrs.hidden),
    textContent: (attrs && attrs.textContent) || '',
    classList: { add: function () {}, remove: function () {} },
    addEventListener: function () {},
    getAttribute: function (k) { return Object.prototype.hasOwnProperty.call(o.attrs, k) ? String(o.attrs[k]) : null; },
    setAttribute: function (k, v) { o.attrs[k] = v; },
    removeAttribute: function (k) { delete o.attrs[k]; },
    querySelector: function () { return null; },
    querySelectorAll: function () { return []; }
  };
  return o;
}
const elG = el('va-ctl-sales_growth_pct', {value: '3', disabled: ''});
const elM = el('va-ctl-margin_delta_pp', {value: '0', disabled: ''});
const elX = el('va-ctl-earnings_multiple', {value: '18', disabled: ''});
const ledeNojs = el('va-lede-nojs', {});
ledeNojs.hidden = false;
const ledeJs = el('va-lede-js', {hidden: true});
ledeJs.hidden = true;
const island = el('vs-assumption-inputs', {});
island.textContent = JSON.stringify(data);
const byId = {
  'vs-assumption-inputs': island,
  'va-ctl-sales_growth_pct': elG,
  'va-ctl-margin_delta_pp': elM,
  'va-ctl-earnings_multiple': elX,
  'va-out': el('va-out', {}),
  'va-out-num': el('va-out-num', {}),
  'va-out-null': el('va-out-null', {hidden: true}),
  'va-bridge': el('va-bridge', {}),
  'va-read-sales_growth_pct': el('va-read-sales_growth_pct', {}),
  'va-read-margin_delta_pp': el('va-read-margin_delta_pp', {}),
  'va-read-earnings_multiple': el('va-read-earnings_multiple', {}),
  'va-lede-nojs': ledeNojs,
  'va-lede-js': ledeJs,
  'va-reset': null,
  'va-presets': el('va-presets', {})
};
const document = {
  getElementById: function (id) { return Object.prototype.hasOwnProperty.call(byId, id) ? byId[id] : null; },
  querySelectorAll: function () { return []; },
  addEventListener: function () {}
};
vm.runInNewContext(src, {
  document: document,
  module: {exports: {}},
  globalThis: {},
  JSON: JSON,
  Number: Number,
  Math: Math,
  Infinity: Infinity,
  Object: Object,
  String: String,
  parseInt: parseInt,
  parseFloat: parseFloat
});
if (elG.getAttribute('disabled') !== null) {
  throw new Error('sales_growth_pct still disabled');
}
if (elM.getAttribute('disabled') !== null) {
  throw new Error('margin_delta_pp still disabled');
}
if (elX.getAttribute('disabled') !== null) {
  throw new Error('earnings_multiple still disabled');
}
if (ledeNojs.hidden !== true) {
  throw new Error('no-JS lede still visible');
}
if (ledeJs.hidden !== false) {
  throw new Error('move sentence still hidden');
}
process.stdout.write('ok');
""",
            encoding="utf-8",
        )
        proc = subprocess.run(
            [node, "harness.js"], cwd=tdir, capture_output=True, text=True
        )
        assert proc.returncode == 0, proc.stderr
        assert proc.stdout.strip() == "ok"
    assert "Move the three inputs below. The per-share number updates as you move them." in html
    zh_html = _render_assumptions(blob, t=lambda en, zh: zh)
    assert "调整下面三项输入，每股数值会随之更新。" in zh_html


def test_degraded_capture_host_reveals_rv_modules_under_has_js():
    """The JS-on degraded evidence host must depict both panels.

    Round-2 review of head 1271a69a: the host stamps has-js and the CSS
    `html.has-js .rv{opacity:0}` until `.in`, but neither section carried
    `.in` and no script added it. Recapture showed only the host banner.
    The sibling AAPL host already adds `.in`; this host must too.
    """
    path = (
        ROOT
        / "mockups"
        / "evidence"
        / "valuation_assumptions"
        / "hosts"
        / "evidence"
        / "valuation-assumptions-degraded.html"
    )
    html = path.read_text(encoding="utf-8")
    assert "classList.add('has-js')" in html or 'classList.add("has-js")' in html
    compact = re.sub(r"\s+", "", html)
    assert "html.has-js.rv{opacity:0" in compact
    assert 'id="valuation-assumptions"' in html
    assert 'id="valuation-assumptions-floor"' in html
    assert "Margins are too thin at this setting to produce a number." in html
    assert "在该设置下利润率过低，无法算出数值。" in html
    assert "Not enough reported margin to run this." in html
    assert "披露的利润率基数不足，无法进行试算。" in html
    assert "el.value = '-1.5'" in html
    sections = re.findall(
        r"<section\b[^>]*class=\"([^\"]*)\"[^>]*id=\"(valuation-assumptions(?:-floor)?)\"",
        html,
    )
    ids = {sid for _, sid in sections}
    assert ids == {"valuation-assumptions", "valuation-assumptions-floor"}, ids
    baked = all(re.search(r"(?:^|\s)in(?:\s|$)", cls) for cls, _ in sections)
    script_adds = "classList.add('in')" in html or 'classList.add("in")' in html
    assert baked or script_adds, (
        "degraded host stamps has-js and hides .rv at opacity 0, but never "
        "adds .in, so recapture cannot depict the panels"
    )


def test_module_is_pure():
    src = (ROOT / "engine" / "valuation_assumptions.py").read_text(encoding="utf-8")
    for banned in ("open(", "requests", "read_parquet", "datetime.now", "Path("):
        assert banned not in src, banned


def test_missing_labels_imported_read_only_from_v1():
    """Round 8 R3(7): spec §2.2 imports MISSING_LABELS from V1 read-only."""
    assert va._V1_MISSING_LABELS is vs.MISSING_LABELS
    src = (ROOT / "engine" / "valuation_assumptions.py").read_text(encoding="utf-8")
    assert "from engine.valuation_scenario import MISSING_LABELS, SCENARIOS" in src


def test_artifact_schema_shape():
    blob = va.controls_blob(_v1_blob())
    assert blob is not None
    expected_keys = {
        "schema",
        "ticker",
        "tier",
        "fy",
        "period_end",
        "source",
        "inputs",
        "margin_base_floor",
        "controls",
        "presets",
        "server_default",
    }
    assert set(blob) == expected_keys
    assert blob["schema"] == "valuation_scenario_controls.v1"
    assert blob["tier"] == "research_display_only"
    presets = blob["presets"]
    for key, g, m_pp, mult in vs.SCENARIOS:
        assert presets[key] == {
            "sales_growth_pct": g,
            "margin_delta_pp": m_pp,
            "earnings_multiple": mult,
        }
    assert set(presets) == {k for k, *_ in vs.SCENARIOS}
    assert set(blob["inputs"]) == {"net_income", "revenue", "shares", "net_margin_base"}
    assert set(blob["server_default"]) == {
        "sales_growth_pct",
        "margin_delta_pp",
        "earnings_multiple",
        "per_share",
    }
    for c in blob["controls"]:
        assert set(c) == {"key", "min", "max", "step", "default"}


# Committed golden string of the V1 panel render (t = EN-only, AAPL fixture).
GOLDEN_V1_HTML = '\n<style>\n.vs-lede{margin:2px 0 16px;font-size:13px;line-height:1.55;color:var(--muted);max-width:62ch;}\n.vs-ruler{position:relative;height:64px;margin:6px 4px 30px;}\n.vs-ruler .vs-track{position:absolute;left:0;right:0;top:28px;height:6px;border-radius:var(--r-ctl,3px);\n  background:var(--line);border:1px solid var(--hair);}\n.vs-ruler .vs-mark{position:absolute;top:16px;width:12px;height:12px;border-radius:var(--r-ctl,3px);\n  transform:translateX(-50%);background:var(--muted);}\n.vs-ruler .vs-mark.m-base{background:var(--link);box-shadow:0 0 10px color-mix(in srgb,var(--link) 55%,transparent);}\n.vs-ruler .vs-mark.m-upbeat{background:color-mix(in srgb,var(--link) 55%,var(--text));}\n.vs-ruler .vs-mark.m-gap{background:transparent;border:1px dashed var(--hair);box-shadow:none;}\n.vs-ruler .vs-mark:hover,.vs-ruler .vs-mark:focus-visible{height:14px;top:15px;transition:height var(--t-fast,.14s) ease,top var(--t-fast,.14s) ease;}\n.vs-ruler .vs-lbl{position:absolute;top:44px;transform:translateX(-50%);font-size:10.5px;\n  font-weight:650;color:var(--muted);white-space:nowrap;text-align:center;}\n.vs-ruler .vs-lbl.below{top:auto;bottom:-14px;}\n.vs-ruler .vs-lbl b{display:block;font-size:11.5px;font-weight:750;color:var(--text);font-variant-numeric:tabular-nums;}\n.vs-ruler .vs-price{position:absolute;top:6px;bottom:6px;width:2px;background:var(--text);\n  box-shadow:0 0 0 3px var(--panel);}\n.vs-ruler .vs-price-lbl{position:absolute;top:-14px;transform:translateX(-50%);font-size:9.5px;\n  font-weight:700;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);white-space:nowrap;}\n[data-theme="light"] .vs-ruler .vs-track{background:transparent;border:none;border-bottom:1px solid var(--line);}[data-theme="light"] .vs-ruler .vs-mark{top:28px;border-radius:var(--r-ctl,2px);background:transparent;border:1.5px solid var(--muted);}\n[data-theme="light"] .vs-ruler .vs-mark:hover,[data-theme="light"] .vs-ruler .vs-mark:focus-visible{top:27px;}\n[data-theme="light"] .vs-ruler .vs-mark.m-base{background:var(--link);\n  border:1px solid color-mix(in srgb,var(--link) 55%,var(--panel));box-shadow:0 2px 6px -3px color-mix(in srgb,var(--text) 28%,transparent);}\n[data-theme="light"] .vs-ruler .vs-mark.m-upbeat{background:color-mix(in srgb,var(--link) 50%,var(--panel));border-color:var(--text);}\n[data-theme="light"] .vs-ruler .vs-mark.m-cautious{background:transparent;border-color:var(--muted);}\n[data-theme="light"] .vs-ruler .vs-mark.m-gap{background:transparent;border:1px dashed var(--hair);box-shadow:none;}\n[data-theme="light"] .vs-ruler .vs-price{width:1.5px;background:var(--text);box-shadow:0 0 0 3px var(--panel);}\n\n.vs-cards{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:16px;}\n.vs-card{background:color-mix(in srgb,var(--panel2) 55%,transparent);border:1px solid var(--hair);\n  border-radius:var(--r-card,13px);padding:14px 15px;min-width:0;}\n[data-theme="light"] .vs-card{background:var(--panel);border:1px solid var(--hair);box-shadow:0 6px 18px -12px color-mix(in srgb,var(--text) 18%,transparent);}\n.vs-card .vk{font-size:10.5px;font-weight:650;color:var(--muted);text-transform:uppercase;letter-spacing:.06em;}\n[data-lang="zh"] .vs-card .vk{letter-spacing:0;text-transform:none;}\n.vs-card .vv{margin-top:6px;font-size:20px;font-weight:800;letter-spacing:-.02em;font-variant-numeric:tabular-nums;}\n.vs-card .vv.vv-null{font-size:12.5px;font-weight:600;color:var(--muted);}\n.vs-card .va{margin-top:8px;font-size:11.5px;line-height:1.5;color:var(--muted);}\n\n.vs-base{display:flex;flex-direction:column;gap:0;margin-top:2px;}\n.vs-base .r6{display:flex;justify-content:space-between;align-items:baseline;gap:12px;padding:8px 0;\n  border-bottom:1px solid var(--hair);font-size:12.5px;}\n.vs-base .r6:last-child{border-bottom:none;}\n.vs-base .k6{color:var(--muted);}\n.vs-base .k6 small{display:block;font-size:10.5px;margin-top:2px;}\n.vs-base .v6{font-weight:650;text-align:right;font-variant-numeric:tabular-nums;}\n.vs-base .v6.v6-null{font-weight:500;color:var(--muted);font-variant-numeric:normal;}\n.vs-base .v6 em{display:block;font-style:normal;font-size:10px;font-weight:500;color:var(--muted);margin-top:2px;}.vs-thirdparty-null{margin-top:12px;padding-top:10px;border-top:1px solid var(--hair);\n  font-size:11px;line-height:1.5;color:var(--muted);}\n\n@media(max-width:720px){.vs-cards{grid-template-columns:1fr;}}\n@media(max-width:390px){\n  .vs-base .r6{flex-direction:column;gap:2px;align-items:flex-start;}\n  .vs-base .v6{text-align:left;}\n}\n</style>\n\n\n\n\n\n\n\n\n\n\n\n\n<section class="mod rv" id="valuation-scenario" data-valuation-scenario="v1">\n  <div class="mod-hd">\n    <h2>What could it be worth?</h2>\n    <span class="hint">reported SEC figures · FY2025\n      \n    </span>\n  </div>\n  <p class="vs-lede">Three sets of assumptions applied to AAPL\'s last reported year. Change the assumption, change the answer.</p><div class="vs-ruler" role="img" aria-label="Per-share value scale across three assumption scenarios and today\'s price">\n    <div class="vs-track"></div>\n    \n    \n      \n      \n      <div class="vs-mark m-cautious" style="left:3.4%" tabindex="0"></div>\n      <div class="vs-lbl " style="left:3.4%">Cautious<b>$91</b></div>\n      \n    \n      \n      \n      <div class="vs-mark m-base" style="left:18.1%" tabindex="0"></div>\n      <div class="vs-lbl below" style="left:18.1%">Base<b>$131</b></div>\n      \n    \n      \n      \n      <div class="vs-mark m-upbeat" style="left:34.8%" tabindex="0"></div>\n      <div class="vs-lbl " style="left:34.8%">Upbeat<b>$176</b></div>\n      \n    \n    \n    <div class="vs-price" style="left:88.2%"></div>\n    <div class="vs-price-lbl" style="left:88.2%">Today\'s price</div>\n    \n  </div>\n\n  <div class="vs-cards">\n    \n    \n      \n      <div class="vs-card">\n        <div class="vk">Cautious</div>\n        \n        <div class="vv num">$90.94</div>\n        \n        <div class="va">\n          Sales fall 2% next year, margins narrow, valued at 14× the resulting earnings.\n          \n        </div>\n        \n        \n        \n        \n        <div class="va vs-bridge">Vs base: growth -5pp, margin -1.5pp, multiple -4x — $130.65 to $90.94 (-30.4%).</div>\n        \n      </div>\n    \n      \n      <div class="vs-card">\n        <div class="vk">Base</div>\n        \n        <div class="vv num">$130.65</div>\n        \n        <div class="va">\n          Sales grow 3% next year, margins hold, valued at 18× the resulting earnings.\n          \n        </div>\n      </div>\n    \n      \n      <div class="vs-card">\n        <div class="vk">Upbeat</div>\n        \n        <div class="vv num">$175.74</div>\n        \n        <div class="va">\n          Sales grow 7% next year, margins widen, valued at 22× the resulting earnings.\n        </div>\n        \n        \n        \n        \n        <div class="va vs-bridge">Vs base: growth +4pp, margin +1.5pp, multiple +4x — $130.65 to $175.74 (+34.5%).</div>\n        \n      </div>\n    \n  </div>\n\n  <div class="vs-base kv6">\n    \n    <div class="r6"><span class="k6">Revenue<small>FY2025 · Source: SEC filings</small></span>\n      <span class="v6 num">$416.0B</span></div>\n    <div class="r6"><span class="k6">Operating income<small>FY2025 · Source: SEC filings</small></span>\n      <span class="v6 num">$128.0B</span></div>\n    <div class="r6"><span class="k6">Net income<small>FY2025 · Source: SEC filings</small></span>\n      <span class="v6 num">$105.0B</span></div>\n    <div class="r6"><span class="k6">Share count<small>FY2025 · Source: SEC filings</small></span>\n      <span class="v6 num">14.90B<em>Shares outstanding, as reported</em></span></div>\n    <div class="r6"><span class="k6">Net cash / debt<small>FY2025 · Source: SEC filings</small></span>\n      <span class="v6 num">Net debt $48.0B</span></div>\n  </div>\n\n  <div class="vs-thirdparty-null" data-vs-thirdparty-null="1">This app does not license Wall Street\'s outside stock-picking research, so that layer is left empty here — shown honestly as missing, not filled in with a guess.</div>\n  <div class="mod-ft">Research display only — not advice.</div>\n</section>\n'
