"""INTL-GS W4B — Transmission board (R14 §10.4) view tests V1–V20.

The board is proven through the TEST-ONLY builder in
``tests/intl_gs_transmission_fixture.py`` (real IM17 engine calls on synthetic,
specimen-marked inputs) injected as ``lib.intl_gs_transmission_view``; the
production site keeps the Transmission tab ``not_built`` because no admitted
live IM17 producer exists yet (V1). No data/ path is read, no network call.
"""
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

import engine.intl_transmission_evidence as te
from lib.intl_gs_transmission_present import (
    PresentError,
    present_transmission,
)
from tests import intl_gs_transmission_fixture as fixture

ROOT = Path(__file__).resolve().parents[1]
BASE_SHA = "e6debbb05b47b518f0a39f4dbf9d26f95f9c7fa7"
CSS_PATH = ROOT / "templates/intl_workspace_surveillance.css"
TEMPLATE_PATH = ROOT / "templates/intl_workspace/transmission.html.j2"
PRESENTER_PATH = ROOT / "lib/intl_gs_transmission_present.py"
BLOCK_START = "/* ==== INTL-GS IM17 transmission (.intl-transmission__*) — W4B ==== */"
BLOCK_END = "/* ==== end INTL-GS IM17 transmission ==== */"

SECTION_RE = re.compile(
    r'<section class="intl-gs__panel intl-gs__view intl-gs__view--transmission".*?</section>',
    re.S)


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def _render(**kw):
    return fixture.render_transmission_page(**kw)


def _section(html):
    found = SECTION_RE.findall(html)
    assert len(found) == 1, f"expected exactly one transmission section, got {len(found)}"
    return found[0]


def _panes(section):
    parts = section.split('intl-transmission__pane" data-i="')
    return parts[1:]  # parts[0] is before the first pane


def _strip_tags(markup):
    text = re.sub(r"<[^>]+>", " ", markup)
    return re.sub(r"\s+", " ", text).strip()


def _lang_text(markup, lang):
    spans = re.findall(rf'<span class="l-{lang}">(.*?)</span>', markup, re.S)
    return " ".join(_strip_tags(s) for s in spans)


def _css_block():
    css = CSS_PATH.read_text(encoding="utf-8")
    assert css.count(BLOCK_START) == 1 and css.count(BLOCK_END) == 1
    start = css.index(BLOCK_START)
    end = css.index(BLOCK_END) + len(BLOCK_END)
    return css, css[start:end]


def _rules(css_text):
    """(selector, body) pairs, @media blocks flattened."""
    css_text = re.sub(r"/\*.*?\*/", "", css_text, flags=re.S)
    out = []
    for match in re.finditer(r"([^{}]+)\{([^{}]*)\}", css_text):
        selector, body = match.group(1).strip(), match.group(2).strip()
        if selector.startswith("@media"):
            inner = match.group(2)
            for inner_match in re.finditer(r"([^{}]+)\{([^{}]*)\}", inner):
                out.append((inner_match.group(1).strip(), inner_match.group(2).strip()))
        elif not selector.startswith("@"):
            out.append((selector, body))
    return out


def _git_show(path):
    try:
        return subprocess.run(
            ["git", "show", f"{BASE_SHA}:{path}"], cwd=ROOT,
            capture_output=True, check=True).stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


# --------------------------------------------------------------------------
# V1 — the production site stays not_built without a builder
# --------------------------------------------------------------------------

def test_view_not_built_without_builder():
    from lib.intl_surveillance_mount import attach_surveillance
    from engine.intl_workspace_overview import build_workspace_overviews
    from tests.intl_gs_fixture_site import render_intl_page
    result = attach_surveillance(build_workspace_overviews(None))
    assert result["surveillance"]["views"]["transmission"]["status"] == "not_built"
    assert result["surveillance_panels"] == []
    html = render_intl_page(include_surveillance=True, stub_coverage=False)
    button = re.search(r'<button[^>]*data-im-view="transmission"[^>]*>', html)
    assert button, "Transmission nav button missing"
    assert "disabled" in button.group(0), "nav button must stay disabled without a builder"


# --------------------------------------------------------------------------
# V2 — the fixture builder makes exactly one available panel
# --------------------------------------------------------------------------

def test_fixture_builder_renders_available_panel():
    workspace = fixture.attach_transmission()
    assert workspace["surveillance"]["views"]["transmission"]["status"] == "available"
    html = _render()
    section = _section(html)
    assert 'id="im-gs-transmission-transmission"' in section
    assert section.count('data-view="transmission"') == 1
    assert 'id="im-gs-transmission-transmission-title"' in section
    button = re.search(r'<button[^>]*data-im-view="transmission"[^>]*>', html)
    assert button and "disabled" not in button.group(0)


# --------------------------------------------------------------------------
# V3 — the presenter refuses tampered inputs
# --------------------------------------------------------------------------

def test_presenter_refuses_tampered_inputs():
    payload = fixture.build_payload()

    extra = json.loads(json.dumps(payload))
    extra["surprise"] = 1
    with pytest.raises(PresentError, match="payload_keys"):
        present_transmission(extra)

    wrong_board = json.loads(json.dumps(payload))
    wrong_board["board"]["contract_version"] = "other-v1"
    with pytest.raises(PresentError, match="board_contract"):
        present_transmission(wrong_board)

    tampered_edge = json.loads(json.dumps(payload))
    first = tampered_edge["events"][0]
    assert first["state"] == "qualified" and first["channel_evidence"]
    first["channel_evidence"][0]["pathway"] = "hypothetical_scenario"
    with pytest.raises(PresentError, match="edge_invalid:"):
        present_transmission(tampered_edge)

    tampered_summary = json.loads(json.dumps(payload))
    event_id = tampered_summary["events"][0]["event_id"]
    del tampered_summary["summaries"][event_id]["edges"][0]["pathway_label_zh"]
    with pytest.raises(PresentError, match="summary_invalid:"):
        present_transmission(tampered_summary)

    unknown = json.loads(json.dumps(payload))
    unknown["selection"]["edge_id"] = "tedge:sha256:" + "0" * 64
    with pytest.raises(PresentError, match="selection_unknown"):
        present_transmission(unknown)

    orphan = json.loads(json.dumps(payload))
    orphan["summaries"]["tev:sha256:" + "1" * 64] = orphan["summaries"][
        list(orphan["summaries"])[0]]
    with pytest.raises(PresentError, match="summary_orphan"):
        present_transmission(orphan)


# --------------------------------------------------------------------------
# V4 — no forbidden keys, no causal language (payload and rendered text)
# --------------------------------------------------------------------------

BANNED_KEY_PARTS = ("pct", "percent", "share", "ratio", "score",
                    "centrality", "percentile")
CAUSAL_RE = re.compile(
    r"\b(caused|causes|causing|drove|drives|driven|triggered|triggers|"
    r"led to|spilled over|spill over|spills over|contagion)\b|"
    r"导致|引发|造成|传染")


def _walk_keys(node, prefix=""):
    if isinstance(node, dict):
        for key, val in node.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            yield path
            yield from _walk_keys(val, path)
    elif isinstance(node, list):
        for i, item in enumerate(node):
            yield from _walk_keys(item, f"{prefix}.{i}" if prefix else str(i))


def test_no_forbidden_keys_or_causal_language():
    out = present_transmission(fixture.build_payload())
    assert te.forbidden_keys(out) == []
    for path in _walk_keys(out):
        low = path.lower()
        assert not any(part in low for part in BANNED_KEY_PARTS), path
    assert te.scan_causal_language(out) == []

    section = _section(_render())
    for lang in ("en", "zh"):
        text = _lang_text(section, lang)
        assert not CAUSAL_RE.search(text), (lang, CAUSAL_RE.search(text).group(0))
    assert not CAUSAL_RE.search(_strip_tags(section))

    planted = json.loads(json.dumps(fixture.build_payload()))
    planted["events"][0]["channel_evidence"][0]["interpretation_en"] = \
        "This drove the US market lower."
    with pytest.raises(PresentError, match="output_causal:"):
        present_transmission(planted)


# --------------------------------------------------------------------------
# V5 — typed edges: four glyph families, legend and TYPE column match (T1)
# --------------------------------------------------------------------------

FAMILY_WORDS = {"flow": ("Flow", "资金流"), "lending": ("Lending", "借贷"),
                "credit": ("Credit", "信用"), "commodity": ("Commodity", "大宗商品")}


def test_typed_edges_legend_and_type_column_match():
    section = _section(_render())
    pane0 = _panes(section)[0]
    for family in te.GLYPH_FAMILIES:
        assert f'intl-gs__edge--{family}' in pane0, family
    legend = re.search(
        r'class="intl-transmission__legend".*?<svg class="intl-transmission__graph"',
        pane0, re.S).group(0)
    for family, (en, zh) in FAMILY_WORDS.items():
        assert f"intl-gs__edge--{family}" in legend, family
        assert f">{en}<" in legend and f">{zh}<" in legend, family
    rows = re.findall(r'<tr[^>]*data-e="\d+"[^>]*>.*?</tr>', pane0, re.S)
    assert rows
    for row in rows:
        family = re.search(
            r"intl-gs__edge--(flow|lending|credit|commodity)", row).group(1)
        en, zh = FAMILY_WORDS[family]
        assert f">{en}<" in row and f">{zh}<" in row, family


# --------------------------------------------------------------------------
# V6 — edge-list columns exact (T4)
# --------------------------------------------------------------------------

def test_edge_list_columns_exact():
    section = _section(_render())
    pane0 = _panes(section)[0]
    table = re.search(
        r'<table class="intl-gs__table intl-transmission__edges">.*?</table>',
        pane0, re.S).group(0)
    head = re.search(r"<thead>(.*?)</thead>", table, re.S).group(1)
    en_headers = re.findall(r'<span class="l-en">(.*?)</span>', head)
    zh_headers = re.findall(r'<span class="l-zh">(.*?)</span>', head)
    assert en_headers == ["#", "Edge", "Type", "Mechanism", "Evidence",
                          "US window", "US response", "Tier"]
    assert zh_headers == ["#", "传导边", "类型", "机制", "证据",
                          "美国窗口", "美国响应", "层级"]
    _, block = _css_block()
    for width in ("28px", "220px", "116px", "140px", "150px", "200px", "90px"):
        assert f"width:{width}" in block, width
    assert "height:24px" in block and "height:40px" in block
    assert "table-layout:fixed" in block


# --------------------------------------------------------------------------
# V7 — the US window is a numeral UTC clock range (T3)
# --------------------------------------------------------------------------

WIN_EN_RE = re.compile(
    r"^\d{1,2} [A-Z][a-z]{2} \d{2}:\d{2}(–\d{2}:\d{2}| – \d{1,2} [A-Z][a-z]{2} \d{2}:\d{2}) UTC$")
WIN_ZH_RE = re.compile(
    r"^\d{1,2}月\d{1,2}日 \d{2}:\d{2}(–\d{2}:\d{2}| – \d{1,2}月\d{1,2}日 \d{2}:\d{2}) UTC$")


def test_us_window_is_a_numeral_utc_clock_range():
    out = present_transmission(fixture.build_payload())
    by_market = {o["market_id"]: o for o in out["origins"]}
    assert by_market["JP"]["edges"][0]["window"]["en"] == "21 Oct 13:30–20:00 UTC"
    assert by_market["JP"]["edges"][0]["window"]["zh"] == "10月21日 13:30–20:00 UTC"
    assert by_market["GB"]["edges"][0]["window"]["en"] == "21 Oct 20:00 – 22 Oct 20:00 UTC"
    assert by_market["GB"]["edges"][0]["window"]["zh"] == "10月21日 20:00 – 10月22日 20:00 UTC"

    section = _section(_render())
    cells = re.findall(
        r'<td class="intl-transmission__win">(.*?)</td>', section, re.S)
    assert cells
    for cell in cells:
        clock = re.search(
            r'<span class="intl-gs__num"><span class="l-en">(.*?)</span>'
            r'<span class="l-zh">(.*?)</span>', cell, re.S)
        assert clock, cell
        assert WIN_EN_RE.fullmatch(clock.group(1)), clock.group(1)
        assert WIN_ZH_RE.fullmatch(clock.group(2)), clock.group(2)


# --------------------------------------------------------------------------
# V8 — expected vs observed is neutral ink (T2)
# --------------------------------------------------------------------------

def test_expected_vs_observed_neutral_ink():
    _, block = _css_block()
    for selector, body in _rules(block):
        if "intl-transmission__exp" in selector or "intl-transmission__obs" in selector:
            used = set(re.findall(r"var\((--[A-Za-z0-9_-]+)", body))
            assert used <= {"--muted", "--text", "--panel2", "--line"}, (selector, used)
    section = _section(_render())
    for banned in ("intl-gs__num--up", "intl-gs__num--down",
                   "intl-gs__chip--ok\"", "intl-gs__chip--warn\""):
        assert banned not in section, banned
    assert not re.search(r"intl-gs__chip--warn(?!-)", section)
    assert "var(--up)" not in block and "var(--down)" not in block


# --------------------------------------------------------------------------
# V9 — the common-shock alternative is always listed, never drawn
# --------------------------------------------------------------------------

def test_common_shock_always_listed():
    section = _section(_render())
    for pane in _panes(section):
        assert ">Common global shock<" in pane
        assert ">共同全球冲击<" in pane
        assert ">Receiver idiosyncratic<" in pane or ">接收方特质<" in pane
        status_words = ("Live", "仍然成立", "Favoured", "倾向", "Not indicated", "未显示")
        assert any(f">{word}<" in pane for word in status_words)
    assert not re.search(r"<path[^>]*common", section)
    drawn = set(re.findall(r'<path class="intl-gs__edge intl-gs__edge--([a-z]+)"',
                           section))
    assert drawn <= set(te.GLYPH_FAMILIES)


# --------------------------------------------------------------------------
# V10 — withheld and unavailable render states, never numbers
# --------------------------------------------------------------------------

def test_withheld_and_unavailable_render_states_never_numbers():
    payload = fixture.build_payload()
    out = present_transmission(payload)
    jp = out["origins"][0]
    for edge in jp["edges"]:
        if edge["value"]["display"].startswith("withheld"):
            assert edge["value"]["text"] is None
        else:
            assert edge["value"]["display"] == "unavailable"
            assert edge["value"]["text"] is None
    for row in jp["rank_strip"]:
        assert row["state"] in ("withheld", "unavailable")
        assert row["value_text"] is None and row["tick_x"] is None

    section = _section(_render())
    insps = section.split('class="intl-transmission__insp" data-e="')[1:]
    assert insps
    for insp in insps:
        if "withheld" in insp:
            assert "intl-gs__rights-slot" in insp
            assert not re.search(r'class="intl-transmission__value[^"]*"[^>]*>\s*<span class="l-en">\d', insp)
    for pane in _panes(section):
        rank_area = re.search(
            r'class="[^"]*intl-transmission__rankstrip.*?class="[^"]*intl-transmission__edgelist',
            pane, re.S).group(0)
        assert ">0<" not in rank_area
        assert 'data-fam=' not in rank_area  # no bar is drawn for withheld rows
        assert ">No data<" in pane and ">无数据<" in pane

    shown = json.loads(json.dumps(payload))
    row = shown["rank_strips"]["JP"][0]
    row.update({"state": "shown", "value": 12.5, "rank": 2, "rank_population": 5})
    out_shown = present_transmission(shown)
    strip_row = out_shown["origins"][0]["rank_strip"][0]
    assert strip_row["state"] == "shown"
    assert strip_row["value_text"] == "12.5"
    assert strip_row["tick_x"] == 150
    assert strip_row["ticks"] == [{"rank": 1, "x": 200}, {"rank": 5, "x": 0}]


# --------------------------------------------------------------------------
# V11 — an out-of-graph market has no graph number
# --------------------------------------------------------------------------

def test_out_of_graph_market_has_no_graph_number():
    out = present_transmission(fixture.build_payload())
    br = next(m for m in out["markets"] if m["market_id"] == "BR")
    assert br["structural"]["state"] == "outside_structural_graph"
    assert br["structural"]["en"] == "Outside structural graph"
    assert br["structural"]["zh"] == "在结构图外"
    assert [s["id"] for s in br["sections"]] == [
        "structural_research", "qualified_observations", "statistical_evidence"]
    section = _section(_render())
    br_block = re.search(
        r'class="intl-transmission__mkt" data-market="BR".*?(?=class="intl-transmission__mkt"|$)',
        section, re.S)
    assert br_block, "BR block missing from the structural-graph coverage disclosure"
    text = _strip_tags(br_block.group(0))
    assert "Outside structural graph" in text
    assert "在结构图外" in text
    assert not re.search(r"rank\s*\d|tick", text, re.I)


# --------------------------------------------------------------------------
# V12 — native radio switch contract, no script, ASSETS unchanged
# --------------------------------------------------------------------------

def _load_build_intl():
    spec = importlib.util.spec_from_file_location(
        "build_intl_under_test", ROOT / "scripts/build_intl.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_native_radio_switch_contract():
    html = _render()
    section = _section(html)
    assert "<script" not in section.lower()
    ids = re.findall(r'id="([^"]+)"', section)
    assert len(ids) == len(set(ids)), "duplicate ids inside the section"
    radios = re.findall(r'<input type="radio"[^>]*>', section)
    assert radios
    radio_ids = {re.search(r'id="([^"]+)"', r).group(1) for r in radios}
    by_name = {}
    for radio in radios:
        name = re.search(r'name="([^"]+)"', radio).group(1)
        by_name.setdefault(name, []).append("checked" in radio)
    assert by_name
    for name, checked in by_name.items():
        assert sum(checked) == 1, f"radio group {name} must have exactly one checked"
    for label_for in re.findall(r'<label[^>]*for="([^"]+)"', section):
        assert label_for in radio_ids, f"label for={label_for} resolves to no radio"
    payload = fixture.build_payload()
    out = present_transmission(payload)
    panes = _panes(section)
    assert len(panes) == len(out["origins"])
    assert section.count('class="intl-transmission__insp" data-e="') == sum(
        len(o["edges"]) for o in out["origins"])
    module = _load_build_intl()
    assert module.ASSETS[-1] == "intl_workspace_surveillance.css"
    assert module.ASSETS.count("intl_workspace_surveillance.css") == 1
    base = _git_show("scripts/build_intl.py")
    if base is not None:
        assert base == (ROOT / "scripts/build_intl.py").read_bytes()


# --------------------------------------------------------------------------
# V13 — the CSS block is scoped, literal-free and stripe-free (A1/A1.1)
# --------------------------------------------------------------------------

def test_css_block_scoped_literal_free_and_stripe_free():
    css, block = _css_block()
    base_css = _git_show("templates/intl_workspace_surveillance.css")
    if base_css is None:
        pytest.skip("git or base object unavailable; append-only check skipped with this message")
    without_block = css.replace(block + "\n", "", 1)
    if block in without_block:
        without_block = without_block.replace(block, "", 1)
    assert without_block.encode("utf-8") == base_css, \
        "removing the W4B block must reproduce the base file byte for byte " \
        "(one block inserted, nothing edited, moved or deleted; it sits " \
        "before the W2A region so the file still ends with the W2B end " \
        "anchor the W2 foundation suite pins)"

    for selector, _body in _rules(block):
        selector = re.sub(r":(?:is|where|not)\([^)]*\)", "", selector)
        for part in selector.split(","):
            part = part.strip()
            if not part or part.startswith("@"):
                continue
            assert (part.startswith(".intl-gs ")
                    or part.startswith('html[data-lang="zh"] .intl-gs ')
                    or part.startswith('html[data-theme="light"] .intl-gs ')), part

    assert not re.findall(r"#[0-9a-fA-F]{3,8}\b", block)
    assert not re.findall(r"\b(?:rgb|rgba|hsl|hsla|hwb|lab|lch|oklab|oklch|"
                          r"color-mix|color)\(", block)
    for value in re.findall(r"font-family\s*:\s*([^;}\n]+)", block):
        assert value.strip() in ("var(--font-ui)", "var(--font-mono)"), value
    for value in re.findall(r"border-radius\s*:\s*([^;}\n]+)", block):
        assert value.strip() in ("var(--r-panel,12px)", "var(--r-btn,8px)",
                                 "var(--r-pill,999px)"), value
    for value in re.findall(r"var\(--[A-Za-z0-9_-]+\s*,\s*[^)]+\)", block):
        assert value in ("var(--r-panel,12px)", "var(--r-btn,8px)",
                         "var(--r-pill,999px)"), value
    for owned in (block, TEMPLATE_PATH.read_text(encoding="utf-8"),
                  PRESENTER_PATH.read_text(encoding="utf-8"),
                  (ROOT / "tests/intl_gs_transmission_fixture.py").read_text(encoding="utf-8")):
        assert "--r-card" not in owned and "--r-ctl" not in owned
    for selector, body in _rules(block):
        for prop in ("border-left", "border-right", "border-top", "border-bottom",
                     "border-inline-start", "border-inline-end",
                     "border-block-start", "border-block-end"):
            assert f"{prop}:" not in body, (selector, prop)
        assert "box-shadow" not in body, selector
        assert "::before" not in selector and "::after" not in selector
    assert not re.search(r"(--[A-Za-z0-9_-]+)\s*:", block), \
        "no custom-property declaration and no --modifier token before :/:: in a selector"
    for banned in ("--sp-", "--returns-", "--font-zh", "color-mix("):
        assert banned not in block
        assert banned not in TEMPLATE_PATH.read_text(encoding="utf-8")

    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    assert "<style" not in template and "style=" not in template

    theme = (ROOT / "templates/theme.css").read_text(encoding="utf-8")
    theme_names = set(re.findall(r"(--[A-Za-z0-9_-]+)\s*:", theme))
    a1_names = set(re.findall(r"(--[A-Za-z0-9_-]+)\s*:", css[:css.index("=== END INTL-GS")]))
    used = set(re.findall(r"var\((--[A-Za-z0-9_-]+)",
                          re.sub(r"/\*.*?\*/", "", block, flags=re.S)))
    unresolved = {name for name in used
                  if name not in theme_names and name not in a1_names}
    assert not unresolved, unresolved

    base_theme = _git_show("templates/theme.css")
    if base_theme is not None:
        assert base_theme == (ROOT / "templates/theme.css").read_bytes(), \
            "templates/theme.css must equal the merge base"


# --------------------------------------------------------------------------
# V14 — the site copy is byte-identical
# --------------------------------------------------------------------------

def test_site_css_copy_identical():
    assert (ROOT / "site/intl_workspace_surveillance.css").read_bytes() == \
        CSS_PATH.read_bytes()


# --------------------------------------------------------------------------
# V15 — bilingual twins, ZH typography, total vocabulary coverage
# --------------------------------------------------------------------------

VOCABULARIES = {
    "RESPONSE_WORDS": te.RESPONSE_STATUSES,
    "STAGE_WORDS": te.US_RESPONSE_STAGES,
    "ATTRIBUTION_WORDS": te.ATTRIBUTIONS,
    "COMMON_WORDS": te.COMMON_SHOCK_STATUSES,
    "CONFIDENCE_WORDS": te.CONFIDENCE_LEVELS,
    "ORIGIN_STAGE_WORDS": te.ORIGIN_STAGES,
    "SEVERITY_WORDS": te.SEVERITY_TIERS,
    "REASON_WORDS": te.EVENT_ABSTAIN_REASONS,
    "MODEL_STATUS_WORDS": te.MODEL_STATUSES,
}


def test_bilingual_twins_and_zh_typography():
    section = _section(_render())
    pairs = re.findall(
        r'<span class="l-en">(.*?)</span><span class="l-zh">(.*?)</span>',
        section, re.S)
    assert pairs
    code = re.compile(r"^[A-Z0-9#·—\-\s]{1,8}$")
    machine_id = re.compile(r"^[a-z0-9_]{1,16}$")
    numeral = re.compile(r"^[\d .:%+−→#]+$")
    for en, zh in pairs:
        assert en.strip() and zh.strip(), (en, zh)
        if en.strip() == zh.strip():
            assert (code.match(en.strip()) or machine_id.match(en.strip())
                    or numeral.match(en.strip())), (en, zh)

    _, block = _css_block()
    assert re.search(
        r'html\[data-lang="zh"\] \.intl-gs [^{]*intl-transmission__edges[^{]*'
        r"\{[^}]*text-transform:none[^}]*letter-spacing:0\.02em", block)
    import lib.intl_gs_transmission_present as presenter
    for attr, constant in VOCABULARIES.items():
        words = getattr(presenter, attr)
        assert set(constant) <= set(words), (attr, set(constant) - set(words))
        for key, (en, zh) in words.items():
            assert en and zh, (attr, key)
    bogus = json.loads(json.dumps(fixture.build_payload()))
    for receiver in bogus["events"][0]["receivers"]:
        receiver["response"]["status"] = "bogus_status"
    with pytest.raises(PresentError, match="vocab:response:bogus_status"):
        present_transmission(bogus)


# --------------------------------------------------------------------------
# V16 — the specimen chip only for specimen payloads
# --------------------------------------------------------------------------

def test_specimen_chip_only_for_specimen_payload():
    plain = _section(_render(specimen=False))
    assert "intl-gs__chip--specimen" not in plain
    specimen = _section(_render(specimen=True))
    assert specimen.count("intl-gs__chip--specimen") == 1


# --------------------------------------------------------------------------
# V17 — production files carry no specimen value
# --------------------------------------------------------------------------

GEOMETRY = {"880", "300", "110", "150", "770", "60", "240", "200", "26"}


def test_production_files_carry_no_specimen():
    for path in (TEMPLATE_PATH, PRESENTER_PATH):
        text = path.read_text(encoding="utf-8")
        digits = set(re.findall(r"\d{3,}", text))
        assert digits <= GEOMETRY, (path.name, digits - GEOMETRY)
        for banned in ("β", "R²", "σ"):
            assert banned not in text, (path.name, banned)
    grep = subprocess.run(
        ["grep", "-rn", "intl_gs_transmission_fixture", "templates", "lib", "scripts"],
        cwd=ROOT, capture_output=True, text=True)
    assert grep.returncode == 1, grep.stdout
    assert not (ROOT / "lib/intl_gs_transmission_view.py").exists()


# --------------------------------------------------------------------------
# V18 — caps are counted, never dropped
# --------------------------------------------------------------------------

def test_caps_are_counted_not_dropped():
    payload6 = fixture.build_payload(origins=6)
    out6 = present_transmission(payload6)
    assert len(out6["origins"]) == 4
    assert len(out6["more_origins"]) == 2
    assert [m["rank"] for m in out6["more_origins"]] == [5, 6]
    html6 = _section(_render(origins=6))
    footnote = re.search(r'class="intl-gs__footnote intl-transmission__more"[^>]*>(.*?)</p>', html6, re.S)
    assert footnote, "more-origins footnote missing"
    foot_text = _strip_tags(re.sub(r"<[^>]+>", " ", footnote.group(1)))
    assert "#5" in foot_text and "#6" in foot_text

    payload10 = fixture.build_payload(edges_per_origin=10)
    out10 = present_transmission(payload10)
    jp10 = out10["origins"][0]
    assert len(jp10["edges"]) == 8 and jp10["more_edges"]["count"] == 2
    html10 = _section(_render(edges_per_origin=10))
    assert "+2" in _lang_text(html10, "en")

    promoted = fixture.build_payload(
        origins=6, selection={"origin_market": "IN", "event_id": None,
                              "edge_id": None})
    out_promoted = present_transmission(promoted)
    assert out_promoted["selection_promoted"] is True
    assert out_promoted["origins"][3]["market_id"] == "IN"
    assert out_promoted["selected"]["i"] == 3


# --------------------------------------------------------------------------
# V19 — the presenter is deterministic
# --------------------------------------------------------------------------

def _reversed_dicts(mapping):
    return {k: mapping[k] for k in reversed(list(mapping))}


def test_presenter_is_deterministic():
    payload = fixture.build_payload()
    out = present_transmission(payload)
    assert [o["market_id"] for o in out["origins"]] == [
        r["market_id"] for r in payload["board"]["us_relevance"][:4]]

    permuted = json.loads(json.dumps(payload))
    permuted["events"] = list(reversed(permuted["events"]))
    permuted["summaries"] = _reversed_dicts(permuted["summaries"])
    permuted["rank_strips"] = _reversed_dicts(permuted["rank_strips"])
    for event in permuted["events"]:
        event["channel_evidence"] = [
            {k: edge[k] for k in reversed(list(edge))}
            for edge in event["channel_evidence"]]
    out2 = present_transmission(permuted)
    assert json.dumps(out, sort_keys=True) == json.dumps(out2, sort_keys=True)


# --------------------------------------------------------------------------
# V20 — the abstained event pane
# --------------------------------------------------------------------------

def test_abstained_event_pane():
    out = present_transmission(fixture.build_payload())
    abstain = [o for o in out["origins"] if o["event_state"] == "abstain"]
    assert len(abstain) == 1
    assert abstain[0]["abstain_reasons"]
    assert abstain[0]["desk_read"]["en"] == abstain[0]["ceiling"]["en"]
    assert abstain[0]["desk_read"]["zh"] == abstain[0]["ceiling"]["zh"]

    section = _section(_render())
    pane = next(pane for pane in _panes(section)
                if ">Abstain<" in pane or ">弃权<" in pane)
    assert "clock_order_violation" in pane
    assert ">Clock order violation<" in pane and ">时钟顺序违规<" in pane
    graph = re.search(r'<svg class="intl-transmission__graph".*?</svg>', pane, re.S)
    assert graph
    assert "<path" not in graph.group(0)
    assert "No qualified transmission event" in _lang_text(pane, "en")
    assert "无合格传导事件" in _lang_text(pane, "zh")
    assert ">Common global shock<" in pane
    ceiling_en = abstain[0]["ceiling"]["en"]
    assert ceiling_en in _lang_text(pane, "en")
