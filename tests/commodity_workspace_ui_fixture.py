"""Render deterministic commodity journeys through the actual publication owners.

Synthetic source data is kept in a temporary directory. The workspace builder,
identity adapter, bilingual templates, Gold panel and detail-tab script are the
production implementations. No generated site snapshot is used or rewritten.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import json
import sys
import tempfile

from jinja2 import Environment, FileSystemLoader, StrictUndefined
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engine.commodity_decision_workspace import build_workspace
from engine.commodity_workspace_adapter import attach_company_continuations
from engine.intelligence_workspace.entity import VENDOR_ALIASES

ASOF = "2026-10-16"
MEMBERS = (
    ("oil", "energy"), ("natgas", "energy"), ("gasoline", "energy"), ("heating_oil", "energy"),
    ("gold", "precious"), ("silver", "precious"), ("platinum", "precious"), ("palladium", "precious"),
    ("copper", "industrial"), ("corn", "grain"), ("wheat", "grain"), ("soybeans", "grain"),
    ("coffee", "soft"), ("cocoa", "soft"), ("sugar", "soft"), ("cotton", "soft"),
    ("live_cattle", "livestock"),
)


def source_documents():
    snapshot = {"asof": ASOF, "index": {"chg_1m_pct": 2},
        "breadth": {"n_members": 17, "n_up_trend": 17},
        "members": [{"name": name, "class": family, "chg_1m_pct": 2,
            "velocity": {"r5": 1, "r20": 2, "r60": 3, "r252": 4},
            "ts_trend": "up", "momentum_state": "neutral"} for name, family in MEMBERS]}
    chains = {"schema": "transmission_chains.v1", "asof": ASOF, "caveats": [], "chains": []}
    for name, node, channel, symbol in (
        ("oil_inflation_duration_derate", "breakeven_rise", "fixture_oil", "OILFIX"),
        ("real_rate_peak_gold_rerate", "real_rate_rolldown", "fixture_gold", "GOLDFIX")):
        chains["chains"].append({"chain": name, "rev": 1, "state": "arming",
            "title": {"en": "Synthetic source chain", "zh": "合成来源链"},
            "episode_id": "fixture:" + name, "falsifier_fired": None,
            "nodes": [{"id": node, "resolved": True, "confirmed": False, "receipts": []}], "hops": [],
            "blast": {channel: {"label": {"en": "Synthetic cohort", "zh": "合成公司组"},
                "note": {"en": "Fixture only; no investment conclusion.", "zh": "仅用于测试，不构成投资结论。"}, "n": 1,
                "unevaluable": 0, "names": [symbol], "cuts": {}}}})
    return snapshot, chains


def unique_between(source, start, end):
    if source.count(start) != 1 or source.count(end) != 1:
        raise AssertionError("production template marker missing or ambiguous")
    first = source.index(start)
    last = source.index(end, first + len(start))
    if last <= first:
        raise AssertionError("production template marker order")
    return source[first:last]


def render(workspace):
    page = (ROOT / "templates/commodities.html.j2").read_text()
    macro = unique_between(page, "{% macro t(en, zh='') -%}", "{% macro vbadge(v) -%}")
    advanced_start = '<details id="commodity-advanced" class="cw-advanced">'
    if page.count(advanced_start) != 1:
        raise AssertionError("advanced owner marker changed")
    advanced_index = page.index(advanced_start)
    advanced = page[advanced_index:page.index("{% endif %}", advanced_index)]
    details = unique_between(page,
        "<!-- ========================= SECTION 5 — PER-COMMODITY DETAIL ========================= -->",
        "{% else %}\n{# fallback when vm is empty (engine error) #}")
    script = unique_between(page, "/* ── detail tab selector ── */",
                             "/* ── alert timeline filter + more ── */")
    template = macro + '<!doctype html><html lang="en"><head><meta charset="utf-8"></head><body>' \
        + '{% include "_commodity_decision_workspace.html.j2" %}' + advanced + details \
        + '</details><script>' + script + '</script></body></html>'
    env = Environment(loader=FileSystemLoader(str(ROOT / "templates")),
                      undefined=StrictUndefined, autoescape=True)
    detail = [{"name": "oil", "label_en": "Oil", "label_zh": "原油", "available": False},
        {"name": "gold", "label_en": "Gold", "label_zh": "黄金", "available": True,
         "action_en": "Synthetic context", "action_zh": "合成背景", "top_score": None,
         "bot_score": None, "top_fired": [], "bottom_fired": [], "cycle_phase": None,
         "is_core4": False, "mtf_rows": [], "china_gold_premium": {
             "available": False, "current_method": None, "state": "unavailable"}}]
    return env.from_string(template).render(commodity_workspace=workspace, vm={"detail": detail})


def linked(workspace):
    return [row for chain in workspace["chains"] for cohort in chain["cohorts"]
            for row in cohort.get("companies", {}).get("linked", [])]


def fixtures():
    snapshot, chains = source_documents()
    with tempfile.TemporaryDirectory(prefix="commodity-ui-fixture-") as name:
        fixture_root = Path(name)
        alias = fixture_root / VENDOR_ALIASES
        alias.parent.mkdir(parents=True)
        pd.DataFrame([{"vendor": "store", "vendor_symbol": symbol,
            "security_id": "SEC:0:" + symbol, "valid_from": "2026-01-01", "valid_to": None}
            for symbol in ("OILFIX", "GOLDFIX")]).to_parquet(alias, index=False)
        positive = attach_company_continuations(build_workspace(snapshot, chain_state=chains), chains, fixture_root)
        # The adapter intentionally degrades on missing dependencies. This positive
        # assertion makes that degradation a test failure instead of hiding a link bug.
        assert {row["symbol"] for row in linked(positive)} == {"OILFIX", "GOLDFIX"}
        assert len(linked(positive)) == 2
        empty = deepcopy(chains)
        for chain in empty["chains"]:
            chain["blast"] = {}
        no_cohorts = attach_company_continuations(build_workspace(snapshot, chain_state=empty), empty, fixture_root)
        alias.unlink()
        no_identity = attach_company_continuations(build_workspace(snapshot, chain_state=chains), chains, fixture_root)
        assert not linked(no_cohorts) and not linked(no_identity)
        return {"positive": render(positive), "empty_cohorts": render(no_cohorts),
                "identity_unavailable": render(no_identity)}


if __name__ == "__main__":
    print(json.dumps(fixtures(), ensure_ascii=False))
