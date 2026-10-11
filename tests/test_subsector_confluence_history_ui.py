from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
TPL = ROOT / "templates" / "subsectors.js"
SITE = ROOT / "site" / "subsectors.js"
BUILDER = ROOT / "scripts" / "build_subsector_confluence.py"
HISTORY = ROOT / "site" / "marketdata" / "subsector_confluence_history.json"


def test_confluence_renderer_mirror_is_exact() -> None:
    assert TPL.read_bytes() == SITE.read_bytes()


def test_signal_and_entry_condition_are_presented_as_orthogonal_reads() -> None:
    js = TPL.read_text(encoding="utf-8")
    assert "Fresh signals — just triggered" in js
    assert "Fresh entry signal" in js
    assert "Entry condition: " in js
    assert "Stretched — wait for pullback" in js
    assert "Freshest cross — but extended, confirm" not in js
    assert "Buy-ready — just turned" not in js

    # Regression guard: payload.forming is a list of keys, never a list of group dicts.
    assert "var formingKeys = payload.forming || [];" in js
    assert "formingKeys.indexOf(g.key) >= 0" in js


def test_history_is_fetched_in_parallel_and_rendered_fail_open() -> None:
    js = TPL.read_text(encoding="utf-8")
    assert "var HISTORY = null;" in js
    assert "subsector_confluence_history.json" in js
    assert "Promise.all(deskFetches.concat([historyFetch]))" in js
    assert "historySection(ds)" in js
    assert "Earlier dates are not reconstructed from today" in js


def test_seed_history_is_true_pit_and_semis_keeps_both_dimensions() -> None:
    payload = json.loads(HISTORY.read_text(encoding="utf-8"))
    assert payload["schema"] == "subsector_confluence.history_projection.v1"
    assert payload["history_start"] == payload["pit_only_since"] == "2026-09-18"
    assert "No retrospective recomputation" in payload["methodology"]
    assert payload["accuracy"]["status"] == "accruing"

    day = payload["days"][0]
    recs = day["desks"]["subsectors"]["recommendations"]
    semi = next(r for r in recs if r["key"] == "semiconductors")
    assert semi["entry_tier"] == "T1"
    assert semi["entry_condition"] == "stretched"
    assert semi["regime_state"] == "EXTENDED"


def test_history_append_is_nightly_only_and_china_is_not_recorded() -> None:
    source = BUILDER.read_text(encoding="utf-8")
    assert 'os.environ.get("COLLECT_LANE", "").strip().lower() != "nightly"' in source
    assert '_record_history(site, ("subsectors", subs), ("baskets", baskets))' in source
    assert '_record_history(site, (ns, out))' in source

    china_start = source.index("def main_china()")
    china_end = source.index("def render_china_pages", china_start)
    assert "_record_history(" not in source[china_start:china_end]
