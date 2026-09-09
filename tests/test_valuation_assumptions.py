"""Tests for engine/valuation_assumptions.py (FROZEN SPEC B-F07-2)."""
from __future__ import annotations

import hashlib
import json
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

_V1_BASE_REFS = (
    "origin/claude/mo-b-b1-b-f07-1",
    "claude/mo-b-b1-b-f07-1",
)

# Render of templates/_valuation_scenario.html.j2 against the V1 AAPL-shaped
# fixture with t(en, zh) = en and deep_ids=[]. Committed so a V1 template
# edit that this packet must not make fails T9 even if git is unavailable.
GOLDEN_V1_SHA256 = "a8fef1b18bce0246bc884ef8c18c84a348cacb7f7ec1cdc42ed3dd3abf14493f"


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


def _git_show(rel: str) -> bytes:
    for ref in _V1_BASE_REFS:
        proc = subprocess.run(
            ["git", "show", f"{ref}:{rel}"],
            cwd=ROOT,
            capture_output=True,
        )
        if proc.returncode == 0:
            return proc.stdout
    raise AssertionError(f"could not git show {rel} from stacked parent {_V1_BASE_REFS}")


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


def test_controls_blob_default_equals_v1_base_card():
    v1 = _v1_blob()
    blob = va.controls_blob(v1)
    assert blob is not None
    by_key = {s["key"]: s for s in v1["scenarios"]}
    base = by_key["base"]
    assert blob["server_default"]["per_share"] == base["per_share"]
    assert blob["server_default"]["sales_growth_pct"] == 3
    assert blob["server_default"]["margin_delta_pp"] == 0
    assert blob["server_default"]["earnings_multiple"] == 18
    defaults = {c["key"]: c["default"] for c in blob["controls"]}
    assert defaults["sales_growth_pct"] == 3
    assert defaults["margin_delta_pp"] == 0
    assert defaults["earnings_multiple"] == 18


def test_controls_blob_is_none_when_v1_is_not_usable():
    assert va.controls_blob(None) is None
    assert va.controls_blob(_v1_blob(ni=None)) is None
    assert va.controls_blob(_v1_blob(ni=0)) is None
    assert va.controls_blob(_v1_blob(ni=-5.0)) is None
    assert va.controls_blob(_v1_blob(revenue=None)) is None
    assert va.controls_blob(_v1_blob(shares=0)) is None
    revenue = 1.0e11
    tiny_ni = revenue * 0.001  # 0.1% margin, under the 1% floor
    assert va.controls_blob(_v1_blob(ni=tiny_ni, revenue=revenue)) is None


def test_margin_too_thin_and_nonpositive_never_render_a_number():
    revenue = 1.0e11
    ni_1_2_pct = revenue * 0.012
    assert va.per_share_at(ni_1_2_pct, revenue, FIXTURE_ROW["shares"], 3, -1.5, 18) is None
    v1 = _v1_blob(ni=ni_1_2_pct, revenue=revenue)
    # Base (m_pp=0) is still computable at 1.2%, so the panel ships.
    blob = va.controls_blob(v1)
    assert blob is not None
    html = _render_assumptions(blob, t=lambda en, zh: f"{en}|{zh}")
    assert "$-" not in html
    assert "Margins are too thin at this setting to produce a number." in html
    assert "在该设置下利润率过低，无法算出数值。" in html


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
            "  const v = math.perShareAt(ni, p.revenue, p.shares, pt.g, pt.m, pt.x);\n"
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
        got = va.per_share_at(use_ni, revenue, shares, pt["g"], pt["m"], pt["x"])
        py_out.append("null" if got is None else f"{got:.2f}")
    assert js_out == py_out


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
    for m in re.finditer(r"t\(\s*'([^']*)'\s*,\s*'([^']*)'\s*\)", text):
        en, zh = m.group(1), m.group(2)
        assert zh.strip() != "", f"empty ZH for en={en!r}"
    for m in re.finditer(r'title="[^"]*[一-鿿][^"]*"', text):
        raise AssertionError(f"ZH text found in a title= attribute: {m.group(0)!r}")
    for m in re.finditer(r'aria-label="[^"]*[一-鿿][^"]*"', text):
        raise AssertionError(f"ZH text found in an aria-label= attribute: {m.group(0)!r}")


def test_v1_panel_output_is_byte_identical():
    blob = vs.compute(_rows(), price=319.97, asof="2026-09-05", ticker="AAPL")
    html = _render_v1(blob)
    assert hashlib.sha256(html.encode("utf-8")).hexdigest() == GOLDEN_V1_SHA256
    assert html == GOLDEN_V1_HTML
    for rel in ("engine/valuation_scenario.py", "templates/_valuation_scenario.html.j2"):
        shown = _git_show(rel)
        on_disk = (ROOT / rel).read_bytes()
        assert shown == on_disk, f"{rel} changed versus stacked parent"


def test_no_js_default_state_is_correct_and_complete():
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
    assert "Interactive controls need JavaScript." in stripped


def test_module_is_pure():
    src = (ROOT / "engine" / "valuation_assumptions.py").read_text(encoding="utf-8")
    for banned in ("open(", "requests", "read_parquet", "datetime.now", "Path("):
        assert banned not in src, banned


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
