"""Tests for engine/valuation_scenario.py (FROZEN SPEC B-F07-1)."""
from __future__ import annotations

import re
from pathlib import Path

from engine import valuation_scenario as vs

ROOT = Path(__file__).resolve().parent.parent

FIXTURE_ROW = {
    "fy": 2025,
    "period_end": "2025-09-27",
    "revenue": 4.16e11,
    "op_income": 1.28e11,
    "ni": 1.05e11,  # loader column name (collectors/edgar_facts.py FLOW["ni"]) -- not "net_income"
    "cash": 3.2e10 + 1.0e10,  # arbitrary; net_debt derived below
    "debt_lt": 8.0e10,
    "debt_cur": 1.0e10,
    "shares": 1.49e10,
}


def _rows(**overrides):
    row = dict(FIXTURE_ROW)
    row.update(overrides)
    return [row]


def test_math_matches_frozen_formula():
    blob = vs.compute(_rows(), price=319.97, asof="2026-09-05", ticker="AAPL")
    assert blob is not None
    by_key = {s["key"]: s for s in blob["scenarios"]}
    net_income = FIXTURE_ROW["ni"]
    revenue = FIXTURE_ROW["revenue"]
    shares = FIXTURE_ROW["shares"]
    net_margin_base = net_income / revenue
    for key, g, m_pp, mult in vs.SCENARIOS:
        adj = net_income * (1 + g / 100.0) * (1 + (m_pp / 100.0) / net_margin_base)
        expected = round((adj * mult) / shares, 2)
        got = by_key[key]
        assert got["computable"] is True
        assert got["per_share"] == expected, (key, got["per_share"], expected)


def test_null_propagation():
    blob = vs.compute(_rows(ni=None))
    for s in blob["scenarios"]:
        assert s["computable"] is False
        assert s["per_share"] is None
        assert s["missing"] == ["net_income"]
    assert blob["base"]["net_income"]["value"] is None
    assert blob["base"]["net_income"]["reported"] is False

    # BLOCKER B2 (review B-F07-1): net_debt is reported ONLY as an
    # informational base fact -- the frozen per_share formula never consumes
    # it (an earnings multiple already yields equity value), so a missing
    # net_debt leg must NEVER gate scenario computability. The base row still
    # correctly prints a null for net_debt itself.
    blob2 = vs.compute(_rows(cash=None))
    assert blob2["base"]["net_debt"]["value"] is None
    assert blob2["base"]["net_debt"]["reported"] is False
    for s in blob2["scenarios"]:
        assert s["computable"] is True
        assert "net_debt" not in s["missing"]
        assert s["per_share"] is not None

    # No zero substitution anywhere for the dropped inputs.
    assert blob["base"]["net_income"]["value"] != 0
    assert blob2["base"]["net_debt"]["value"] != 0


def test_share_count_identity_is_declared():
    blob = vs.compute(_rows())
    assert blob["base"]["share_count"]["identity"] == "outstanding"
    assert blob["base"]["share_count"]["identity"] != "diluted"


def test_period_and_unit_consistency():
    blob = vs.compute(_rows(revenue_fy=2024))
    for s in blob["scenarios"]:
        assert s["computable"] is False
        assert s["missing"] == ["consistent period"]
    assert blob["base"]["revenue"]["unit"] == "USD"
    assert blob["base"]["share_count"]["unit"] == "shares"


def test_negative_or_zero_earnings_is_not_a_value():
    blob = vs.compute(_rows(ni=0))
    for s in blob["scenarios"]:
        assert s["computable"] is False
        assert s["per_share"] is None
        assert "positive reported earnings" in s["missing"]

    blob2 = vs.compute(_rows(ni=-5.0))
    for s in blob2["scenarios"]:
        assert s["computable"] is False
        assert s["per_share"] is None


def test_tiny_margin_base_is_not_computable():
    """MINOR-2 (review round 2): net_margin_base = net_income / revenue with no
    floor lets a thin-margin issuer's margin_delta_pp swamp the base margin --
    e.g. margin ~=0.1% makes the Cautious factor 1 + (-1.5/0.1) = -14, printing
    a negative dollar per-share as a computed value. A margin base this small
    is not a usable denominator, so it must gate computability (same as a
    missing net_margin_base) rather than silently produce a nonsense number."""
    revenue = 1.0e11
    tiny_ni = revenue * 0.001  # 0.1% margin -- reported, but unusable as a base
    blob = vs.compute(_rows(ni=tiny_ni, revenue=revenue))
    for s in blob["scenarios"]:
        assert s["computable"] is False
        assert s["per_share"] is None
        assert "net_margin_base" in s["missing"]
    assert blob["base"]["net_income"]["value"] == tiny_ni
    assert blob["base"]["net_income"]["reported"] is True

    # A normal margin (AAPL-scale, ~24%) stays fully computable -- the floor
    # must not touch any realistic issuer.
    normal = vs.compute(_rows())
    for s in normal["scenarios"]:
        assert s["computable"] is True
        assert s["per_share"] is not None
        assert s["per_share"] > 0


def test_margin_1_2_percent_gates_cautious_only():
    """MAJOR-1 (review round 3): round 2's MINOR-2 fix floored net_margin_base
    at 1%, but that floor alone left every margin in [1.0%, 1.5%) still
    producing a NEGATIVE per_share for Cautious -- e.g. at margin=1.2%
    (0.012), Cautious's factor is 1 + (-1.5/100)/0.012 = 1 + (-0.015/0.012),
    which is still negative, so `computable=True` with `per_share=-4.12` on
    the pre-fix module (confirmed by running it directly). The real gate is
    PER SCENARIO: computable only when net_margin_base + margin_delta_pp/100
    is strictly positive for THAT scenario. At margin=1.2%:
      cautious (m_pp=-1.5): 0.012 + (-0.015) = -0.003 <= 0 -> NOT computable
      base     (m_pp=0.0):  0.012 + 0.0      =  0.012 >  0 -> computable
      upbeat   (m_pp=+1.5): 0.012 + 0.015    =  0.027 >  0 -> computable
    Other scenarios must still render even though Cautious is gated -- this
    is a per-scenario gate, not a global one."""
    revenue = 1.0e11
    ni_1_2_pct = revenue * 0.012
    blob = vs.compute(_rows(ni=ni_1_2_pct, revenue=revenue), ticker="TEST")
    by_key = {s["key"]: s for s in blob["scenarios"]}

    cautious = by_key["cautious"]
    assert cautious["computable"] is False
    assert cautious["per_share"] is None
    assert "margin_too_thin" in cautious["missing"]
    # And NOT gated by the (different, global) net_margin_base-missing
    # reason -- the margin base itself is available at this magnitude, it is
    # only too thin for Cautious's own delta.
    assert "net_margin_base" not in cautious["missing"]

    for key in ("base", "upbeat"):
        s = by_key[key]
        assert s["computable"] is True, (key, s)
        assert s["per_share"] is not None
        assert s["per_share"] > 0
        assert "margin_too_thin" not in s["missing"]

    # Belt-and-braces: the rendered HTML contains no bare "$-" (a negative
    # dollar figure) anywhere -- the non-computable Cautious card must never
    # leak a computed negative value.
    import jinja2

    env = jinja2.Environment(loader=jinja2.FileSystemLoader(str(ROOT / "templates")))
    env.globals["t"] = lambda en, zh: en
    tmpl = env.from_string("{% include '_valuation_scenario.html.j2' %}")
    html = tmpl.render(valuation_scenario=blob, deep_ids=[])
    assert "$-" not in html
    assert "Margins are too thin to run the cautious case" in html


def test_fixture_keys_are_real_statement_columns():
    """Review B-F07-1 BLOCKER B1: engine/valuation_scenario.py previously read
    latest.get("net_income"), a key that does not exist anywhere in the real
    engine.stock_fundamentals._load_statements() schema -- every AAPL row
    silently produced net_income=None against live data, and no test caught
    it because the fixture used the same wrong key the module read. Ground
    the fixture in the loader's own declared column set (collectors/
    edgar_facts.py FLOW/BALANCE/BALANCE_SHARES -- the concept tables
    _load_statements()'s parquet is built from) so a fixture key that doesn't
    exist in the real schema fails here instead of passing silently."""
    from collectors.edgar_facts import BALANCE, BALANCE_SHARES, FLOW

    declared = set(FLOW) | set(BALANCE) | set(BALANCE_SHARES) | {"fy", "period_end"}
    fixture_keys = set(FIXTURE_ROW)
    assert fixture_keys <= declared, fixture_keys - declared
    # And the specific field this bug hinged on: real net income lives at "ni",
    # never "net_income" (which is only ever an OUTPUT/display key in this module).
    assert "ni" in fixture_keys
    assert "net_income" not in fixture_keys


def test_module_is_pure():
    src = (ROOT / "engine" / "valuation_scenario.py").read_text()
    for banned in ("open(", "requests", "read_parquet", "datetime.now", "Path("):
        assert banned not in src, banned


BANNED_VOCAB = [
    "probability", "confidence", "likely", "odds", "expected value",
    "fair value", "price target", "consensus", "analyst", "estimate",
    "forecast", "validated",
    "概率", "置信", "目标价", "共识", "预测",
]


def test_no_banned_vocabulary():
    partial = ROOT / "templates" / "_valuation_scenario.html.j2"
    text = partial.read_text().lower()
    for word in BANNED_VOCAB:
        assert word.lower() not in text, f"banned word {word!r} found in partial"


def test_bilingual_parity():
    partial = ROOT / "templates" / "_valuation_scenario.html.j2"
    text = partial.read_text()
    for m in re.finditer(r"t\(\s*'([^']*)'\s*,\s*'([^']*)'\s*\)", text):
        en, zh = m.group(1), m.group(2)
        assert zh.strip() != "", f"empty ZH for en={en!r}"
    for m in re.finditer(r'title="[^"]*[一-鿿][^"]*"', text):
        raise AssertionError(f"ZH text found in a title= attribute: {m.group(0)!r}")


def test_panel_renders_and_omits():
    import jinja2

    env = jinja2.Environment(loader=jinja2.FileSystemLoader(str(ROOT / "templates")))
    env.globals["t"] = lambda en, zh: en

    tmpl_src = (
        "{% include '_valuation_scenario.html.j2' %}"
    )
    tmpl = env.from_string(tmpl_src)

    computable_blob = vs.compute(_rows(), price=319.97, asof="2026-09-05", ticker="AAPL")
    html = tmpl.render(valuation_scenario=computable_blob, deep_ids=[])
    assert 'id="valuation-scenario"' in html
    assert 'data-valuation-scenario="v1"' in html

    null_blob = vs.compute(_rows(ni=None), ticker="AAPL")
    assert null_blob["any_computable"] is False
    html2 = tmpl.render(valuation_scenario=null_blob, deep_ids=[])
    assert 'id="valuation-scenario"' in html2
    assert "Can't be computed without reported net income" in html2
    assert "not reported" in html2
    # No raw internal field slug leaked into the null copy.
    for raw_slug in ("net_income", "net_debt", "net_margin_base", "share_count"):
        assert raw_slug not in html2

    # A blob with nothing computed AND no base data at all still must not
    # render an empty/broken section -- compute() only returns None when
    # there is no dated row at all, which the template also guards.
    assert vs.compute([]) is None


def test_null_reason_prioritizes_consistent_period_over_margin_too_thin():
    """Review round 4 MINOR-4: vs_null_en/vs_null_zh in
    templates/_valuation_scenario.html.j2 used to test
    `'margin_too_thin' in s.missing` (membership), so a scenario carrying
    BOTH a more fundamental reason ("consistent period") and margin_too_thin
    always got the scenario-named margin sentence, silently suppressing the
    mixed-period reason. engine/valuation_scenario.py always appends
    "consistent period" FIRST and "margin_too_thin" LAST to a scenario's
    `missing` list (guard order), so testing s.missing[0] instead of
    membership restores the correct priority: the more fundamental reason
    wins whenever more than one applies."""
    import jinja2

    # margin=1.2% drives Cautious's own factor negative (margin_too_thin),
    # same fixture as test_margin_1_2_percent_gates_cautious_only -- but this
    # fixture ALSO breaks period consistency (a debt_lt row tagged to a
    # different fiscal year), which the engine appends first and unconditionally.
    revenue = 1.0e11
    ni_1_2_pct = revenue * 0.012
    blob = vs.compute(
        _rows(ni=ni_1_2_pct, revenue=revenue, debt_lt_fy=2024), ticker="TEST"
    )
    by_key = {s["key"]: s for s in blob["scenarios"]}
    cautious = by_key["cautious"]
    assert cautious["missing"][0] == "consistent period", cautious["missing"]
    assert "margin_too_thin" in cautious["missing"]  # still recorded, just not first

    env = jinja2.Environment(loader=jinja2.FileSystemLoader(str(ROOT / "templates")))
    env.globals["t"] = lambda en, zh: en
    tmpl = env.from_string("{% include '_valuation_scenario.html.j2' %}")
    html = tmpl.render(valuation_scenario=blob, deep_ids=[])
    assert "Can't be computed without a consistent reporting period" in html
    assert "Margins are too thin to run the cautious case" not in html


def test_full_detail_dialog_requires_positive_per_share_not_just_computable():
    """Review round 4 MINOR-1: scripts/build_ticker_pages.py's Full-detail
    dialog (`_deep_valuation_scenario`) is a fourth render site for
    `per_share` and used to gate on `s.get("computable")` alone -- the PR's
    belt-and-braces claim (every render site requires computable AND
    per_share is not none AND per_share > 0) was true of the Jinja partial
    but one file short of true. Hand-craft a scenario dict the real engine
    could never emit (computable=True, per_share<=0) to prove the dialog
    itself refuses to print a dollar figure for it -- this is exactly the
    defence a real engine regression would need. Also asserts a
    margin_too_thin null now carries a plain-word reason instead of a bare
    "Not computable" with no explanation."""
    from scripts.build_ticker_pages import _deep_valuation_scenario

    blob = {
        "valuation_scenario": {
            "v1": {
                "fy": 2025,
                "period_end": "2025-09-27",
                "base": {
                    "revenue": {"value": 1e11}, "op_income": {"value": 1e10},
                    "net_income": {"value": 1e9},
                    "share_count": {"value": 1e9, "identity": "outstanding"},
                    "net_debt": {"value": None, "reported": False},
                },
                "scenarios": [
                    # Adversarial: engine can never emit this (belt-and-braces
                    # forecloses it), but the dialog must defend independently.
                    {"key": "cautious", "assumptions": {"sales_growth_pct": -2, "margin_delta_pp": -1.5, "earnings_multiple": 14},
                     "per_share": -4.12, "computable": True, "missing": [], "missing_plain": []},
                    {"key": "base", "assumptions": {"sales_growth_pct": 3, "margin_delta_pp": 0, "earnings_multiple": 18},
                     "per_share": None, "computable": False,
                     "missing": ["margin_too_thin"],
                     "missing_plain": [{"en": "a margin base wide enough for this case", "zh": "利润率基数不足以支撑该情景"}]},
                    {"key": "upbeat", "assumptions": {"sales_growth_pct": 7, "margin_delta_pp": 1.5, "earnings_multiple": 22},
                     "per_share": 55.0, "computable": True, "missing": [], "missing_plain": []},
                ],
            }
        }
    }
    dialog = _deep_valuation_scenario(blob)
    panels = dialog["panels"]
    by_title = {p["title_en"]: p for p in panels if p.get("kind") == "kv" and p.get("title_en") in ("Cautious", "Base", "Upbeat")}

    cautious_ps_row = next(r for r in by_title["Cautious"]["rows"] if r["k_en"] == "Per-share (computed)")
    assert cautious_ps_row["v"] == "", cautious_ps_row  # never a dollar figure for per_share<=0
    assert "$" not in cautious_ps_row["v_en"]

    base_ps_row = next(r for r in by_title["Base"]["rows"] if r["k_en"] == "Per-share (computed)")
    assert base_ps_row["v"] == ""
    assert base_ps_row["v_en"] != "Not computable"  # a reason, not a bare unexplained label
    assert "too thin" in base_ps_row["v_en"]
    assert base_ps_row["v_zh"] != "无法计算"
    assert "利润率过低" in base_ps_row["v_zh"]

    upbeat_ps_row = next(r for r in by_title["Upbeat"]["rows"] if r["k_en"] == "Per-share (computed)")
    assert upbeat_ps_row["v"] == "$55.00"


def test_research_display_only_line_present():
    import jinja2

    env = jinja2.Environment(loader=jinja2.FileSystemLoader(str(ROOT / "templates")))
    env.globals["t"] = lambda en, zh: f"{en}|{zh}"
    tmpl = env.from_string("{% include '_valuation_scenario.html.j2' %}")
    blob = vs.compute(_rows(), price=319.97, asof="2026-09-05", ticker="AAPL")
    html = tmpl.render(valuation_scenario=blob, deep_ids=[])
    assert "Research display only" in html
    assert "仅供研究展示" in html
