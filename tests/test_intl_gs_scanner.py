"""INTL-GS-W2A (IM13 scanner) unit + render tests.

Every number test runs against the PRODUCTION VARIANT observation set built
by tests/intl_gs_scanner_fixture.py (the incumbent chain over synthetic
closes) and the ABSTAIN-ALL variant (observations=None); every asserted value
is recomputed from the observation set / engine output, never typed.
"""
import importlib.util
import re
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from engine.intl_global_universe import load_rights_matrix, load_universe  # noqa: E402
from engine.intl_workspace_overview import build_workspace_overviews  # noqa: E402
from lib.intl_gs_display import (  # noqa: E402
    CAPABILITY_DISPLAY,
    NAMES_ZH,
    REASON_COPY,
    rights_view,
)
from lib.intl_surveillance_mount import GS_VIEWS, attach_surveillance  # noqa: E402

MINUS = "−"
RAW_ISO_TEXT = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}")


def _fixture():
    spec = importlib.util.spec_from_file_location(
        "intl_gs_scanner_fixture", REPO / "tests/intl_gs_scanner_fixture.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


FX = _fixture()


def _mounted(tmp_path, observations):
    workspace = build_workspace_overviews(None)
    return attach_surveillance(workspace, observations=observations)


def _production_mounted(tmp_path):
    observations = FX.observation_set(tmp_path)
    return _mounted(tmp_path, observations), observations


_PAGE = {}


def _production_html():
    if "prod" not in _PAGE:
        _PAGE["prod"] = FX.render_production_page()
    return _PAGE["prod"]


def _abstain_html():
    if "abstain" not in _PAGE:
        _PAGE["abstain"] = FX.render_abstain_page()
    return _PAGE["abstain"]


def _specimen_html():
    if "spec" not in _PAGE:
        _PAGE["spec"] = FX.render_specimen_page()
    return _PAGE["spec"]


def _panel_chunks(html, view, horizon=None, basis=None):
    """Inner HTML of every panel of one view (optionally one context)."""
    pattern = re.compile(
        r'<section class="intl-gs__panel intl-gs__view intl-gs__view--' + view
        + r'"([^>]*)>(.*?)(?=<section class="intl-gs__panel|<p><a href="#intl-legacy-research")',
        re.DOTALL)
    chunks = []
    for attrs, body in pattern.findall(html):
        if horizon is not None and f'data-horizon="{horizon}"' not in attrs:
            continue
        if basis is not None and f'data-basis="{basis}"' not in attrs:
            continue
        chunks.append(body)
    return chunks


def _scanner_panel(html, horizon="1m", basis="usd_unhedged"):
    chunks = _panel_chunks(html, "scanner", horizon, basis)
    assert chunks, f"no scanner panel for {horizon}/{basis}"
    return chunks[0]


def _signed(value, dp=2, unit="%"):
    sign = "+" if value > 0 else (MINUS if value < 0 else "")
    return f"{sign}{abs(value):.{dp}f}{unit}"


class _TextAndAttrs(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text = []
        self.attrs = []

    def handle_starttag(self, tag, attrs):
        for name, value in attrs:
            if value is not None:
                self.attrs.append((tag, name, value))

    def handle_data(self, data):
        self.text.append(data)


def _scan(html):
    parser = _TextAndAttrs()
    parser.feed(html)
    return parser


def _visible_text(html):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))


# ---------------------------------------------------------------- A1 mount


def test_a1_scanner_and_coverage_mount_with_real_inputs(tmp_path):
    workspace, observations = _production_mounted(tmp_path)
    views = workspace["surveillance"]["views"]
    assert views["scanner"]["status"] == "available", views["scanner"]
    assert views["coverage"]["status"] == "available", views["coverage"]
    contexts = workspace["config"]["horizons"], workspace["config"]["bases"]
    expected_panels = len(contexts[0]) * len(contexts[1])
    for view in ("scanner", "coverage"):
        panels = [p for p in workspace["surveillance_panels"] if p["view"] == view]
        assert len(panels) == expected_panels, (view, len(panels))
        for panel in panels:
            assert panel["context"]["currency_basis"] in ("local", "usd_unhedged")
            assert panel["context"]["return_basis"] == "price"
            assert panel["context"]["horizon"] in workspace["config"]["horizons"]
            assert panel["payload"], "payload must not be empty"


def test_a1b_abstain_all_variant_renders_states_not_numbers():
    html = _abstain_html()
    panel = _scanner_panel(html)
    # with observations=None no market has an observation: the table carries no
    # numeric row at all and every market sits in the no-data disclosure
    assert not re.findall(r'<tr data-gs-market-row="([A-Z]{2})"[^>]*>(.*?)</tr>', panel, re.DOTALL)
    tfoot = re.search(r'<tfoot>.*?</tfoot>', panel, re.DOTALL).group(0)
    assert "0" in tfoot and "64" in tfoot
    nodata = re.search(r'<details class="intl-gs__nodata".*?</details>', panel, re.DOTALL)
    assert nodata and "JP" in nodata.group(0) and "BR" in nodata.group(0)
    for kpi_id in ("largest", "common_factor", "spread", "breadth"):
        card = re.search(r'data-kpi="%s".*?</div>\s*</div>' % kpi_id, panel, re.DOTALL)
        assert card, kpi_id
        body = re.sub(r"<[^>]+>", " ", card.group(0))
        assert "intl-gs__chip--muted-dashed" in card.group(0) or "Abstain" in body, kpi_id
        assert not re.search(r"[+−]?\d+\.\d+%", body), (kpi_id, body)
    handoff = re.search(r'class="intl-gs__handoff".*?</div>', panel, re.DOTALL)
    assert handoff and handoff.group(0).count('data-abstain="session_calendar_unadmitted"') == 3


# ---------------------------------------------------------------- A2 numbers


def _observation_index(observations):
    index = {}
    for basis in ("local", "usd_unhedged"):
        for observation in observations["bases"][basis]:
            identity = observation["identity"]
            index[(identity["market_id"], identity["horizon"], basis)] = observation
    return index


def test_a2_every_number_matches_a_qualified_observation(tmp_path):
    workspace, observations = _production_mounted(tmp_path)
    index = _observation_index(observations)
    html = _production_html()
    for horizon in workspace["config"]["horizons"]:
        panel = _scanner_panel(html, horizon=horizon, basis="usd_unhedged")
        rows = re.findall(r'<tr data-gs-market-row="([A-Z]{2})"[^>]*>(.*?)</tr>', panel, re.DOTALL)
        assert rows, horizon
        for market, chunk in rows:
            for leg, key in (("local", "local"), ("usd", "usd_unhedged")):
                observation = index.get((market, horizon, key))
                cell = re.search(r'data-leg="%s"[^>]*>(.*?)</td>' % leg, chunk, re.DOTALL)
                assert cell, (market, leg)
                if observation is not None and observation["state"] == "qualified":
                    expected = _signed(observation["value"]["pct"])
                    assert expected in cell.group(1).replace("&amp;", "&"), \
                        (market, horizon, leg, expected, cell.group(1)[:160])
                else:
                    assert "intl-gs__chip--muted-dashed" in cell.group(1), (market, leg)
            # FX % reads the usd observation decomposition, never a view computation
            usd = index.get((market, horizon, "usd_unhedged"))
            fx_cell = re.search(r'data-leg="fx"[^>]*>(.*?)</td>', chunk, re.DOTALL)
            assert fx_cell
            if usd is not None and usd["state"] == "qualified":
                expected = _signed(usd["decomposition"]["fx_pct"])
                assert expected in fx_cell.group(1), (market, expected, fx_cell.group(1)[:160])


def test_a2b_abstaining_market_renders_reason_chip(tmp_path):
    # one market's usd leg is broken in the frame -> its USD cell abstains with copy
    import shutil
    import pandas as pd
    from engine import intl_inputs
    from lib.intl_eod_publication import build_eod_inputs
    from lib.intl_gs_observations import build_observation_set
    frame, series = FX.synthetic_closes(tmp_path)
    broken_fx = intl_inputs.countries()["JP"]["fx"]
    frame = frame.copy()
    frame.loc[frame.index[-1], broken_fx] = float("nan")
    # rewrite the parquet the publication chain re-reads
    for symbol in (broken_fx,):
        path = tmp_path / "intl" / (
            symbol.replace("^", "_").replace("=", "_").replace("/", "_") + ".parquet")
        pd.DataFrame({"close": frame[symbol].tolist()}, index=frame.index).to_parquet(path)
    FX._run_status(tmp_path)
    selected, inputs = build_eod_inputs(
        frame, data_root=tmp_path, evaluated_at=FX.EVALUATED_AT, rights=FX.W2A_GRANT)
    observations = build_observation_set(
        selected, publication_inputs=inputs, evaluated_at=FX.EVALUATED_AT,
        data_root=tmp_path, rights=FX.W2A_GRANT)
    jp_usd = next(o for o in observations["bases"]["usd_unhedged"]
                  if o["identity"]["market_id"] == "JP" and o["identity"]["horizon"] == "1m")
    assert jp_usd["state"] == "abstain"
    workspace = _mounted(tmp_path, observations)
    panel = next(p for p in workspace["surveillance_panels"]
                 if p["view"] == "scanner" and p["context"]["horizon"] == "1m"
                 and p["context"]["currency_basis"] == "usd_unhedged")
    row = next(r for r in panel["payload"]["rows"] if r["id"] == "JP")
    usd = row["usd"]
    assert usd["state"] == "abstain"
    assert usd["reasons"] == jp_usd["abstain_reasons"]
    first = REASON_COPY[jp_usd["abstain_reasons"][0]]
    assert usd["first_reason"] == first
    # and the rendered panel shows the reason copy, not a numeral
    html = FX.render_page_with_observations(observations)
    panel = _scanner_panel(html)
    jp_row = re.search(r'<tr data-gs-market-row="JP".*?</tr>', panel, re.DOTALL).group(0)
    usd_cell = re.search(r'data-leg="usd"[^>]*>(.*?)</td>', jp_row, re.DOTALL).group(0)
    assert first[0] in usd_cell
    assert not re.search(r"[+−]?\d+\.\d+%", usd_cell)


# ---------------------------------------------------------------- A3 unsourced


def test_a3_unsourced_columns_carry_view_abstain_tokens():
    from lib.intl_gs_display import VIEW_ABSTAIN_TOKENS
    assert {"common_factor_unadmitted", "divergence_unadmitted", "series_unadmitted",
            "stance_unadmitted", "attention_unadmitted", "credit_funding_unadmitted",
            "transmission_unadmitted", "us_corroboration_unadmitted", "thesis_unadmitted",
            "session_calendar_unadmitted"} <= set(VIEW_ABSTAIN_TOKENS)
    production, abstain = _production_html(), _abstain_html()
    panel = _scanner_panel(production)
    for token in ("common_factor_unadmitted", "divergence_unadmitted",
                  "series_unadmitted", "stance_unadmitted"):
        assert panel.count(f'data-abstain="{token}"') >= 7, token  # every row
        en, zh = REASON_COPY[token]
        assert en in panel and zh in panel, token
    abstain_panel = _scanner_panel(abstain)
    # no rows on the withheld variant: the per-row tokens are vacuous, but the
    # rail/band/handoff tokens still render, and the empty table says so
    assert not re.findall(r'<tr data-gs-market-row="([A-Z]{2})"', abstain_panel)
    assert "No market has an observation" in abstain_panel
    for source_panel in (panel, abstain_panel):
        rail = re.search(r'data-role="attention".*?(?=<div class="intl-gs__bands4"|<p class="intl-gs__footnote")',
                         source_panel, re.DOTALL)
        assert rail, "attention rail missing"
        assert 'data-abstain="attention_unadmitted"' in rail.group(0)
        for token in ("credit_funding_unadmitted", "transmission_unadmitted",
                      "us_corroboration_unadmitted", "thesis_unadmitted"):
            assert f'data-abstain="{token}"' in source_panel, token
        handoff = re.search(r'class="intl-gs__handoff".*?</div>', source_panel, re.DOTALL)
        assert handoff
        assert handoff.group(0).count('data-abstain="session_calendar_unadmitted"') == 3
        assert re.search(r'<span class="intl-gs__num">—</span>', handoff.group(0))


# ---------------------------------------------------------------- A4 KPI row


def test_a4_kpi_row_four_cards_largest_and_breadth(tmp_path):
    workspace, observations = _production_mounted(tmp_path)
    panel_payload = next(p["payload"] for p in workspace["surveillance_panels"]
                         if p["view"] == "scanner" and p["context"]["horizon"] == "1m"
                         and p["context"]["currency_basis"] == "usd_unhedged")
    cards = panel_payload["kpi"]
    assert len(cards) == 4
    assert [c["id"] for c in cards] == ["breadth", "largest", "common_factor", "spread"]
    qualified = [o for o in observations["bases"]["usd_unhedged"]
                 if o["identity"]["horizon"] == "1m" and o["state"] == "qualified"]
    largest = max(qualified, key=lambda o: abs(o["value"]["pct"]))
    move = cards[1]
    assert move["kind"] == "move" and move["pct"] == largest["value"]["pct"]
    assert move["market"][0].startswith(largest["identity"]["market_id"])
    assert move["local_pct"] == largest["decomposition"]["local_pct"]
    assert move["fx_pct"] == largest["decomposition"]["fx_pct"]
    breadth = cards[0]
    assert breadth["up"] == sum(1 for o in qualified if o["value"]["pct"] > 0)
    assert breadth["qualified"] == len(qualified)
    html = _production_html()
    panel = _scanner_panel(html)
    assert len(re.findall(r'data-kpi="', panel)) == 4

    def card_by_id(panel_html, kpi_id):
        parts = panel_html.split('data-kpi="')
        for part in parts[1:]:
            if part.startswith(kpi_id + '"'):
                return part.split('data-kpi="')[0] if 'data-kpi="' in part else part
        raise AssertionError(kpi_id)

    breadth_html = card_by_id(panel, "breadth")
    body = re.sub(r"<[^>]+>", " ", breadth_html)
    assert not re.search(r"\d+(\.\d+)?%", body), body[:200]
    for tier in ("T1", "T2", "T3"):
        assert f'<span class="l-en">{tier}</span>' not in panel, tier
        assert f'<span class="l-zh">{tier}</span>' not in panel, tier


# ---------------------------------------------------------------- A5 table


def test_a5_table_semantics_sort_disclosure_tfoot_links(tmp_path):
    workspace, observations = _production_mounted(tmp_path)
    payload = next(p["payload"] for p in workspace["surveillance_panels"]
                   if p["view"] == "scanner" and p["context"]["horizon"] == "1m"
                   and p["context"]["currency_basis"] == "usd_unhedged")
    index = _observation_index(observations)
    rows = payload["rows"]
    with_usd = [r for r in rows if r["usd"]["state"] == "qualified"]
    without = [r for r in rows if r["usd"]["state"] != "qualified"]
    expected = ([r["id"] for r in sorted(
        with_usd, key=lambda r: -index[(r["id"], "1m", "usd_unhedged")]["value"]["pct"])]
        + [r["id"] for r in sorted(without, key=lambda r: r["name_en"])])
    assert [r["id"] for r in rows] == expected
    universe = load_universe()
    observed_ids = {r["id"] for r in rows}
    universe_ids = set(universe["jurisdictions"]) | set(universe.get("aggregates") or {})
    nodata_ids = universe_ids - observed_ids
    assert payload["nodata"]["count"] == len(nodata_ids)
    assert {m["id"] for m in payload["nodata"]["markets"]} == nodata_ids
    counts = payload["counts"]
    assert counts == {"rows": len(rows), "qualified": len(with_usd),
                      "abstain": len(without), "nodata": len(nodata_ids)}
    html = _production_html()
    panel = _scanner_panel(html)
    nodata = re.search(r'<details class="intl-gs__nodata".*?</details>', panel, re.DOTALL)
    assert nodata, "no-data disclosure missing"
    assert f"+{len(nodata_ids)}" in nodata.group(0)
    body = nodata.group(0)
    for jid in ("BR", "PL"):
        entry = next(m for m in payload["nodata"]["markets"] if m["id"] == jid)
        assert jid in body
        assert entry["reason"][0] in body, jid
    tfoot = re.search(r'<tfoot>.*?</tfoot>', panel, re.DOTALL)
    assert tfoot
    for value in (str(len(rows)), str(len(with_usd)), str(len(without)), str(len(nodata_ids))):
        assert value in tfoot.group(0)
    for market, chunk in re.findall(r'<tr data-gs-market-row="([A-Z]{2})"[^>]*>(.*?)</tr>', panel, re.DOTALL):
        assert f'href="?view=scanner&market={market}"' in chunk.replace("&amp;", "&")
        assert f'data-gs-select-market="{market}"' in chunk
        assert f'href="?view=dossier&market={market}"' in chunk.replace("&amp;", "&")
        assert f'data-gs-open="dossier"' in chunk


# ---------------------------------------------------------------- A6 tier


def test_a6_tier_chips_rights_and_capability():
    universe = load_universe()
    rights = load_rights_matrix()
    jp = rights_view(universe, rights, "JP", "equity_index_fx")
    assert jp["rights_class"] == "direct_display_ok"
    assert jp["delay"] == "intl-conservative-observed-eod-tplus2-v1"
    br = rights_view(universe, rights, "BR", "equity_index_fx")
    assert br is None  # rights_ref null -> never a guessed class
    html = _production_html()
    panel = _scanner_panel(html)
    jp_row = re.search(r'<tr data-gs-market-row="JP".*?</tr>', panel, re.DOTALL).group(0)
    tier = re.search(r'data-leg="tier".*?</td>', jp_row, re.DOTALL).group(0)
    assert "Display permitted" in tier and "允许展示" in tier
    assert "Delayed end-of-day source" in tier
    capability = universe["jurisdictions"]["JP"]["capabilities"]["equity_index_fx"]
    display = CAPABILITY_DISPLAY[capability["state"]]
    assert display != "complete"
    # delayed -> the Qualified chip (dashed warn) with the delayed-source copy
    assert "Qualified" in tier and "有条件" in tier
    assert "intl-gs__chip--warn-dashed" in tier


# ---------------------------------------------------------------- A7 specimen


def test_a7_specimen_isolation(tmp_path):
    workspace, _observations = _production_mounted(tmp_path)
    for panel in workspace["surveillance_panels"]:
        payload = panel["payload"]
        assert payload.get("specimen") is False
        for row in payload.get("rows", []):
            for leg_name in ("local", "fx", "usd"):
                assert row[leg_name]["state"] in ("qualified", "abstain"), (row["id"], leg_name)
    for view in ("scanner", "coverage"):
        module = f"lib.intl_gs_{view}_view"
        source = (REPO / (module.replace(".", "/") + ".py")).read_text(encoding="utf-8")
        # no code path can set specimen truthy (the payload key exists, False only)
        assert not re.findall(r"specimen\"\s*:\s*True", source), module
        assert not re.findall(r"specimen\s*=\s*True", source), module
    result = subprocess.run(["grep", "-rn", "specimen=True", "lib/", "templates/"],
                            cwd=REPO, capture_output=True, text=True)
    assert result.returncode != 0 and not result.stdout.strip(), result.stdout
    html = _specimen_html()
    assert "Specimen values · not live" in html and "示例数值 · 非实时" in html
    assert "intl-gs__specimen-scope" in html
    order = [m for m in re.findall(
        r'<tr data-gs-market-row="([A-Z]{2})"', _panel_chunks(html, "scanner")[0])]
    assert order == ["BR", "TW", "KR", "MX", "JP", "AU", "IN", "ZA", "PL"], order


def test_a7b_specimen_numbers_live_inside_the_specimen_scope():
    class Scope(HTMLParser):
        def __init__(self):
            super().__init__()
            self.stack, self.bad, self.numbers = [], 0, 0

        def handle_starttag(self, tag, attrs):
            classes = (dict(attrs).get("class") or "").split()
            self.stack.append("intl-gs__specimen-scope" in classes)
            if "intl-gs__num" in classes and not any(self.stack[:-1]):
                self.bad += 1
            elif "intl-gs__num" in classes:
                self.numbers += 1

        def handle_endtag(self, tag):
            if self.stack:
                self.stack.pop()

    parser = Scope()
    parser.feed(_specimen_html())
    assert parser.numbers > 0
    assert parser.bad == 0, f"{parser.bad} specimen numbers outside the specimen scope"


# ---------------------------------------------------------------- A9 design


def _w2a_css_region():
    css = (REPO / "templates/intl_workspace_surveillance.css").read_text(encoding="utf-8")
    start = css.index("/* ==== W2A region")
    end = css.index("/* ==== end W2A region")
    return css[start:end]


def test_a9_design_laws_static():
    css = _w2a_css_region()
    body = css.replace("/* ==== W2A region (IM13 scanner + coverage): the W2A lane inserts its rules between this line and the next ==== */",
                       "").replace("/* ==== end W2A region ==== */", "")
    assert len(re.sub(r"/\*.*?\*/", "", body, flags=re.DOTALL).strip()) > 200, \
        "the W2A region must carry real rules"
    for name in ("scanner.html.j2", "coverage.html.j2"):
        assert (REPO / "templates/intl_workspace" / name).exists(), name
    no_comments = re.sub(r"/\*.*?\*/", "", css, flags=re.DOTALL)
    assert not re.findall(r"#[0-9a-fA-F]{3,8}\b", no_comments), "hex literal"
    assert not re.findall(r"\b(?:rgb|rgba|hsl|hsla|color-mix|color)\(", no_comments), "colour fn"
    assert not re.findall(r"font-family\s*:\s*[^;}]*(?:Inter|Menlo|PingFang|monospace|system-ui)",
                          no_comments), "font literal"
    assert ".igs" not in css and "igs-" not in css
    selectors = [s.strip().split(",") for s in re.findall(r"([^{}]+)\{", no_comments)]
    flat = [part.strip() for group in selectors for part in group if part.strip()]
    for part in flat:
        if part.startswith("@") or re.fullmatch(r"\d+%|from|to", part):
            continue
        assert part.startswith(".intl-gs") or re.match(r"^html(\[[^\]]+\])+\s*\.intl-gs", part), part
    assert not re.search(r"--[A-Za-z0-9_-]+\s*:", no_comments), "custom property in region"
    opened = re.findall(r"var\(--[A-Za-z0-9_-]+\s*,", no_comments)
    allowed = re.findall(r"var\(--r-(?:panel,12px|btn,8px|pill,999px)\)", no_comments)
    assert len(opened) == len(allowed), (opened, allowed)
    for value in re.findall(r"border-radius\s*:\s*([^;}\n]+)", no_comments):
        pairs = re.findall(r"var\(--r-(?:panel,12px|btn,8px|pill,999px)\)", value)
        assert len(pairs) == 1 and "calc" not in value and " " not in value.strip(), value
    assert not re.search(r"--[A-Za-z0-9_-]+::?(?:before|after)", no_comments)
    assert not re.search(r":(?:before|after)", no_comments), "no pseudo-element rules in region"
    assert not re.search(r"\binset\b", no_comments)
    for prop in ("border-left", "border-right", "border-inline-start", "border-inline-end",
                 "border-block-start", "border-block-end"):
        assert not re.search(rf"{prop}\s*:", no_comments), prop
    for decl in re.findall(r"border-(?:top|bottom)\s*:[^;}]+", no_comments):
        assert decl.rstrip().endswith("1px solid var(--line)") or decl.rstrip().endswith(":none"), decl
    for selector, body in re.findall(r"([^{}]+)\{([^}]*)\}", no_comments):
        if ":hover" in selector:
            changed = {d.split(":")[0].strip() for d in body.split(";") if d.strip()}
            assert changed <= {"background", "background-color"}, (selector, changed)
    # templates: no <style>, no style= attribute, no <button aria-expanded lie>
    for name in ("scanner.html.j2", "coverage.html.j2", "_gs_scanner_macros.html.j2",
                 "_gs_snapshot.html.j2"):
        path = REPO / "templates/intl_workspace" / name
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        assert "<style" not in text, name
        assert not re.search(r'\sstyle="', text), name
        assert not re.findall(r'="\{\{\s*t\(', text), name


# ---------------------------------------------------------------- A10 ZH


def test_a10_zh_names_labels_and_semantic_ink():
    html = _production_html()
    zh_panel = _scanner_panel(html)
    universe = load_universe()
    for jid in ("JP", "KR"):
        assert NAMES_ZH[jid] in zh_panel, jid
    assert "全球发生了什么变化？" in zh_panel
    assert "本地、汇率、共同还是背离？" in zh_panel
    assert "信用、融资、流动性？" in zh_panel
    assert "如何传导至美国？" in zh_panel
    assert "合格的美国佐证？" in zh_panel
    assert "什么能验证或推翻论点？" in zh_panel
    # signed numerals bind semantic ink classes, never a raw up/down hue
    region = _w2a_css_region()
    for match in re.findall(r"color\s*:\s*([^;}]+)", region):
        assert "var(--up)" not in match and "var(--down)" not in match, match
    html_zh_cells = re.findall(r'class="intl-gs__num intl-gs__num--(up|down)"', zh_panel)
    assert html_zh_cells, "no signed numerals with direction ink"


def test_a10b_sign_to_direction_ink_pinned(tmp_path):
    # R-03 (review r2): a known positive qualified cell carries intl-gs__num--up and a
    # known negative one intl-gs__num--down, computed from the observation set (never
    # typed). EN and ZH renders are the same document (t() emits both spans); the ZH
    # up=red/down=green mapping is the theme.css token swap, never lane CSS (test_a10).
    workspace, observations = _production_mounted(tmp_path)
    index = _observation_index(observations)
    html = _production_html()
    panel = _scanner_panel(html)
    neg = [(o["identity"]["market_id"], o["value"]["pct"])
           for o in observations["bases"]["local"]
           if o["state"] == "qualified" and o["value"]["pct"] < 0]
    pos = [(o["identity"]["market_id"], o["value"]["pct"])
           for o in observations["bases"]["usd_unhedged"]
           if o["state"] == "qualified" and o["value"]["pct"] > 0]
    assert neg and pos, "fixture must admit one declining and one rising qualified series"
    neg_market, neg_pct = neg[0]
    pos_market, pos_pct = pos[0]
    neg_row = re.search(r'<tr data-gs-market-row="%s".*?</tr>' % neg_market, panel, re.DOTALL).group(0)
    pos_row = re.search(r'<tr data-gs-market-row="%s".*?</tr>' % pos_market, panel, re.DOTALL).group(0)
    neg_cell = re.search(r'data-leg="local"[^>]*>(.*?)</td>', neg_row, re.DOTALL).group(1)
    pos_cell = re.search(r'data-leg="usd"[^>]*>(.*?)</td>', pos_row, re.DOTALL).group(1)
    assert 'class="intl-gs__num intl-gs__num--down"' in neg_cell, (neg_market, neg_cell[:120])
    assert 'class="intl-gs__num intl-gs__num--up"' in pos_cell, (pos_market, pos_cell[:120])
    assert _signed(neg_pct) in neg_cell.replace("&amp;", "&")
    assert _signed(pos_pct) in pos_cell.replace("&amp;", "&")
    # the ZH render is the same markup: the row carries the ZH market name and the
    # direction class once per numeral (never a raw --up/--down hue in lane CSS)
    assert NAMES_ZH[neg_market] in neg_row and NAMES_ZH[pos_market] in pos_row
    assert neg_row.count('intl-gs__num--down') >= 1 and pos_row.count('intl-gs__num--up') >= 1


# ------------------------------------------- R-02 fixed table layout pin (review r2)

def test_a17_scanner_table_fixed_layout_and_widths_fit_wrap():
    # R-02: all ten section 10.1 columns must stay visible inside the clip wrap
    # (smallest measured desktop wrap inner width is 794px at 1440 beside-rail).
    region = _w2a_css_region()
    m = re.search(r"\.intl-gs \.intl-gs__table--scanner\{([^}]*)\}", region)
    assert m, "no .intl-gs__table--scanner block rule"
    assert "table-layout:fixed" in m.group(1).replace(" ", ""), m.group(1)
    # pull every declared scanner column width straight from the region
    widths = {}
    for cols, width in re.findall(r"([^{}]+)\{width:(\d+)px", region):
        if "intl-gs__table--scanner" in cols:
            for col in re.findall(r'data-col=\"([a-z0-9]+)\"', cols):
                widths[col] = int(width)
    assert set(widths) == {"market", "local", "fx", "usd", "minibar", "common",
                           "divergence", "usd20d", "tier", "stance"}, widths
    total = sum(widths.values())
    assert total <= 790, (total, widths)  # fits the 794px wrap with border
    for name in ("tier", "stance", "market"):
        assert widths[name] >= 80, (name, widths[name])
    # labels wrap (11.2) while values keep their fixed nowrap slot
    assert re.search(r"__table--scanner th,\.intl-gs \.intl-gs__table--scanner td\{white-space:normal", region)
    assert re.search(r"__table--scanner \.intl-gs__num\{white-space:nowrap", region)


# ------------------------------------------------- A13 horizon vocabulary


def test_a13_horizon_vocabulary_vd5():
    from lib.intl_gs_display import horizon_label
    assert horizon_label("1m") == ("1M", "1月")
    assert horizon_label("3m") == ("3M", "3月")
    assert horizon_label("6m") == ("6M", "6个月")
    assert horizon_label("12m") == ("1Y", "1年")
    assert horizon_label("ytd") == ("YTD", "年初至今")
    assert horizon_label("20d") == ("20D", "20日")
    assert horizon_label("2y") == ("2y", "2y")  # pass-through on undeclared ids
    config = build_workspace_overviews(None)["config"]
    for horizon in config["horizons"]:
        en, zh = horizon_label(horizon)
        assert en and zh, horizon
        assert en == en.upper() or horizon in ("ytd",), (horizon, en)
        assert not re.search(r"[A-Za-z]", zh), (horizon, zh)
    for html in (_production_html(), _abstain_html(), _specimen_html()):
        assert "12个月" not in html and ">12M<" not in html
    for path in (REPO / "lib/intl_gs_scanner_view.py", REPO / "lib/intl_gs_coverage_view.py",
                 REPO / "templates/intl_workspace/scanner.html.j2",
                 REPO / "templates/intl_workspace/coverage.html.j2"):
        if path.exists():
            text = path.read_text(encoding="utf-8")
            assert "12个月" not in text and "12M" not in text, path


def test_a13b_shell_horizon_options_carry_the_vocabulary():
    for html in (_production_html(), _abstain_html(), _specimen_html()):
        select = re.search(r'<select data-im-action="set_horizon">(.*?)</select>', html, re.DOTALL)
        assert select, "set_horizon select missing"
        options = re.findall(
            r'<option value="([^"]+)"[^>]*data-im-label-en="([^"]*)"'
            r'[^>]*data-im-label-zh="([^"]*)"[^>]*>([^<]*)</option>', select.group(1))
        assert options, "options carry no data-im-label vocabulary"
        from lib.intl_gs_display import horizon_label
        for value, en, zh, text in options:
            pair = horizon_label(value)
            assert (en, zh) == pair, (value, en, zh)
            assert text == en or text == value  # text must not stay the raw id
            assert text != value, f"option {value} still prints the raw id"
        values = [o[0] for o in options]
        assert values == build_workspace_overviews(None)["config"]["horizons"]


# ------------------------------------------------- A14 no raw ISO / attrs


def test_a14_no_raw_iso_and_clean_attributes():
    for html in (_production_html(), _abstain_html()):
        for view in ("scanner", "coverage"):
            for panel in _panel_chunks(html, view)[:2]:
                leaks = [node for node in _scan(panel).text if RAW_ISO_TEXT.search(node)]
                assert not leaks, (view, leaks[:3])
        scan = _scan(html)
        leaks = [node for node in scan.text if RAW_ISO_TEXT.search(node)]
        assert not leaks, leaks[:3]
        bad = [(tag, attr, value) for tag, attr, value in scan.attrs
               if "<" in value or (attr != "class" and ("l-en" in value or "l-zh" in value))]
        assert not bad, bad[:3]
        for tag, attr, value in scan.attrs:
            if tag == "time":
                assert attr != "data-checked"
    production_times = re.findall(r"<time([^>]*)>", _production_html())
    assert production_times, "the production variant carries clock instants"
    for attrs in production_times:
        assert "datetime=" in attrs, attrs
    for attrs in re.findall(r"<time([^>]*)>", _abstain_html()):
        assert "datetime=" in attrs, attrs
    for name in ("scanner.html.j2", "coverage.html.j2", "_gs_scanner_macros.html.j2",
                 "_gs_snapshot.html.j2"):
        path = REPO / "templates/intl_workspace" / name
        if path.exists():
            assert not re.findall(r'="\{\{\s*t\(', path.read_text(encoding="utf-8")), name


# ------------------------------------------------- A16 no section-title rail


def test_a16_no_section_title_rail_static():
    page = (REPO / "templates/intl.html.j2").read_text(encoding="utf-8")
    for block in re.findall(r"<style[^>]*>(.*?)</style>", page, re.DOTALL):
        for selector in re.findall(r"([^{}]+)\{", block):
            selector = selector.strip()
            if selector.endswith("h2::before") or selector.endswith("h2::after"):
                # the only allowed form neutralises the bar inside .intl-gs
                assert ".intl-gs" in selector, selector
                body = re.search(re.escape(selector) + r"\{([^}]*)\}", block)
                assert body and re.fullmatch(r"content:\s*none;?", body.group(1).strip()), selector
    assert not re.search(r"h2[^{{}]*::?(?:before|after)\s*\{[^}]*width", page)
    # seat commission 2026-10-30 (ORCH-6 adjudication of review r2): the .act-h::before
    # accent rail is deleted from templates/intl.html.j2 - deleted, never relocated.
    # No rule whose selector ends in .act-h::before may remain in the template or in
    # the rendered production /intl.html.
    rendered = _production_html()
    for source_name, source in (("template", page), ("rendered", rendered)):
        for block in re.findall(r"<style[^>]*>(.*?)</style>", source, re.DOTALL):
            for selector in re.findall(r"([^{}]+)\{", block):
                assert not selector.strip().endswith(".act-h::before"), (source_name, selector)
    region = _w2a_css_region()
    assert not re.search(r"h2[^{]*::?(?:before|after)", region)
    # my region draws no bar of width or height <= 4px at all (A16 lane rule)
    for prop in ("width", "height"):
        for value in re.findall(rf"{prop}\s*:\s*([^;}}]+)", region):
            match = re.match(r"([\d.]+)px", value.strip())
            if match:
                assert float(match.group(1)) > 4, (prop, value)


# ------------------------------------------------- census (W-CENSUS, operator)


def test_census_zh_pairs_are_real_chinese():
    pairs = set()
    for name in ("scanner.html.j2", "coverage.html.j2", "_gs_scanner_macros.html.j2",
                 "_gs_snapshot.html.j2"):
        path = REPO / "templates/intl_workspace" / name
        if path.exists():
            text = path.read_text(encoding="utf-8")
            pairs.update(re.findall(r"t\('([^']*)',\s*'([^']*)'\)", text))
            pairs.update(re.findall(r't\(([^,]+),\s*(?:\(([^)]*)\))\)', text) and [])
    for module in ("lib/intl_gs_scanner_view.py", "lib/intl_gs_coverage_view.py"):
        path = REPO / module
        if path.exists():
            text = path.read_text(encoding="utf-8")
            pairs.update((en, zh) for en, zh in
                         re.findall(r'\("([^"]*)",\s*"([^"]*)"\)', text)
                         if re.search(r"[一-鿿]", zh))
    assert pairs, "no t() pairs found"
    for en, zh in pairs:
        assert zh.strip(), (en, zh)
        if re.search(r"[A-Za-z]", en) and not re.match(r"^[A-Z0-9 |·%×→−+-]+$", en):
            # a word-y EN string must have real Chinese, not the EN echo
            assert zh != en, (en, zh)
            assert re.search(r"[一-鿿]", zh), (en, zh)
        assert "12个月" not in zh and zh != "12M", (en, zh)


def test_census_no_invented_numbers_in_payload(tmp_path):
    workspace, _observations = _production_mounted(tmp_path)
    allowed_keys = {"pct", "local_pct", "fx_pct", "additive_fx_contribution_pp",
                    "interaction_pp", "datetime", "up", "qualified", "rows", "count",
                    "cells_total", "q", "markets", "abstain", "nodata"}

    def walk(node, path):
        if isinstance(node, dict):
            for key, value in node.items():
                walk(value, f"{path}.{key}")
        elif isinstance(node, list):
            for item in node:
                walk(item, path + "[]")
        elif isinstance(node, (int, float)) and not isinstance(node, bool):
            leaf = path.rsplit(".", 1)[-1].split("[")[-1] or path
            assert leaf in allowed_keys or "clock" in path, \
                f"numeric leaf outside the observation/count vocabulary: {path}={node}"

    seen = set()
    for panel in workspace["surveillance_panels"]:
        walk(panel["payload"], panel["view"])
        seen.add(panel["view"])
    assert {"scanner", "coverage"} <= seen, seen
