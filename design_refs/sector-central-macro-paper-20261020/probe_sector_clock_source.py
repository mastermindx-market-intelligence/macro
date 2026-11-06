"""Read the checked-out Sector/Prophet pair through the actual caution owner."""
from __future__ import annotations
import copy
import hashlib
import json
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from scripts.build_site import _attach_board_display_chips
from tests.test_rlt_sector_stance_enrich import _render_stance_board_row

paths = {
    "sector": ROOT / "site/sectordata/sector_central.json",
    "prophet": ROOT / "site/factordata/us_standouts.json",
}
before = {key: hashlib.sha256(path.read_bytes()).hexdigest() for key, path in paths.items()}
source = json.loads(paths["sector"].read_text())
original = json.loads(paths["prophet"].read_text())
candidate = copy.deepcopy(original)
# Isolate unrelated existing enrichments; the Sector loader and join are real.
with patch("lib.options_context.load_gex_walls", return_value={}), \
     patch("lib.options_context.load_iv_rank", return_value={}), \
     patch("lib.board_state.board_state_view", return_value=None), \
     patch("scripts.close_pass_reconcile.board_state_for", return_value=None), \
     patch("engine.prophet_board_since.stamp_us_board_since_fail_open",
           side_effect=lambda doc, **kwargs: doc):
    out = _attach_board_display_chips(ROOT / "site", candidate)

allowed = {"sector_stance", "sector_stance_zh", "sector_stance_source"}
def without_attaches(doc):
    clean = copy.deepcopy(doc)
    for row in clean.get("buy") or []:
        for key in allowed:
            row.pop(key, None)
    return clean
assert without_attaches(out) == without_attaches(original)
matched = [row for row in out.get("buy", []) if row.get("sector_stance_source")]
cautions = [row for row in matched if row.get("sector_stance") in ("Reduce", "Cautious")]
assert cautions, "The checked-out board has no source-qualified caution to probe"
row = cautions[0]
receipt = row["sector_stance_source"]
assert receipt["snapshot_as_of"] == source["as_of"]
html = _render_stance_board_row(row)
en = "Sector snapshot date (" + receipt["etf"] + "): " + receipt["snapshot_as_of"] + "."
zh = "板块快照日期 (" + receipt["etf"] + ")：" + receipt["snapshot_as_of"] + "。"
assert en in html and zh in html
after = {key: hashlib.sha256(path.read_bytes()).hexdigest() for key, path in paths.items()}
assert before == after
result = {
    "scope": "Actual checked-out Sector and Prophet inputs through the real Sector attach and US card partial; other display enrichments isolated; not full build/browser acceptance",
    "input_sha256": before, "inputs_unchanged": before == after,
    "sector_snapshot_as_of": source.get("as_of"),
    "prophet_board_as_of": original.get("as_of"),
    "buy_rows": len(original.get("buy") or []),
    "matched_sector_rows": len(matched), "caution_rows": len(cautions),
    "example": {"ticker": row.get("ticker"), "signal_date": row.get("signal_date"),
                "source": receipt, "rendered_en": en, "rendered_zh": zh},
    "non_sector_fields_and_order_unchanged": True,
    "source_date_replaces_signal_or_board_date": False,
    "freshness_policy_added": False,
    "production_payload_written": False, "browser_acceptance": False,
    "source_sha256": {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                      for name in ("scripts/build_site.py", "templates/_us_board_cards.html.j2")},
}
(OUT / "sector-clock-source-probe.json").write_text(
    json.dumps(result, indent=2, ensure_ascii=False) + "\n")
print(json.dumps(result, indent=2, ensure_ascii=False))
