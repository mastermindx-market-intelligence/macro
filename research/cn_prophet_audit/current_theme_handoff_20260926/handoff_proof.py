"""Actual caller -> pinned consumer checks; synthetic data, not production proof."""
from pathlib import Path
from datetime import datetime
from copy import deepcopy
from unittest.mock import patch
import hashlib
import json
import subprocess
import sys
import tempfile
import types

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts import build_china

CALLER = "c0d2a314f08e287ede354353cc45dc4e346aa6ec"
CONSUMERS = {"mature": "9c8ff7315347eb8b6d00875603c55b1bd63ad8b5",
             "emerging": "0fab873d85decf6ce72d08e9d4df6b7668e5626f"}
CLOCK = datetime.fromisoformat("2026-09-23T10:00:00+00:00")
SECTOR = {"ticker": "512480.SS", "name": "Sector control",
          "entry": {"urgency": "now", "tag": "BUY NOW"}}

def git(*args):
    return subprocess.check_output(["git", "-C", str(ROOT), *args])

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def intel(day="2026-09-23", clean=False, verb="enter"):
    item = {"id": "cn_probe", "name": "Theme control", "score": 68,
            "action": verb, "action_en": verb.upper(), "action_zh": verb}
    return {"as_of": day, "themes": [{
        "id": "cn_probe", "name": "Theme control", "label": "emerging",
        "reco": verb, "reco_en": verb.upper(), "score": 68,
        "regime_demoted": False, "chase_demoted": False,
        "textures": {"clean_entry": {"flag": clean}},
        "observation": {"effective_as_of": day, "aggregate_eligible": True},
    }], "act_now": {"buy": [item] if clean else [],
                     "add_on_pullback": [] if clean else [item],
                     "reduce": [], "conflicted": []}}

source_path = ROOT / "scripts/build_china.py"
assert source_path.read_bytes() == git("show", f"{CALLER}:scripts/build_china.py")
source_before = digest(source_path.read_bytes())
scenarios = [
    ("current-continuing", {"theme_intel": intel("2026-09-22")}, intel(), True, False),
    ("initial-entry", {}, intel(clean=True), True, False),
    ("same-session-hold", {"theme_intel": intel()}, intel(verb="hold"), True, False),
    ("stale-result", {}, intel("2026-09-22"), True, False),
    ("no-refresh-stale", {"theme_intel": intel("2026-09-22")}, None, False, False),
    ("owner-fails-stale", {"theme_intel": intel("2026-09-22")}, None, True, True),
    ("bad-envelope-refresh", ["invalid root"], intel(), True, False),
    ("bad-envelope-rerender", ["invalid root"], None, False, False),
]
rows = []
consumer_hashes = {}
for stage, commit in CONSUMERS.items():
    raw = git("show", f"{commit}:engine/china_act_now.py")
    consumer_hashes[stage] = digest(raw)
    assert git("show", f"{commit}:lib/cn_calendar.py") == (ROOT / "lib/cn_calendar.py").read_bytes()
    module = types.ModuleType("proof_consumer_" + stage)
    module.__file__ = str(ROOT / "engine/china_act_now.py")
    sys.modules[module.__name__] = module
    exec(compile(raw, module.__file__, "exec"), module.__dict__)
    for name, persisted, fresh, refresh, fail in scenarios:
        calls = []
        def producer(region):
            calls.append(region)
            assert refresh, "no-network consumer called the producer"
            if fail:
                raise RuntimeError("controlled producer failure")
            return deepcopy(fresh)
        with tempfile.TemporaryDirectory(prefix="cn-handoff-proof-") as tmp:
            path = Path(tmp) / "baskets.json"
            path.write_text(json.dumps(persisted))
            before = path.read_bytes()
            with patch("engine.theme_scoring.compute_theme_intel", producer):
                resolved = build_china._theme_intel_for_act_now(path, refresh=refresh)
            assert calls == (["china"] if refresh else [])
            board = module.assemble_act_now([deepcopy(SECTOR)], resolved, None, observed_at=CLOCK)
            assert path.read_bytes() == before
        view = board["display_lanes"]
        sectors = [r for r in view["buy_now"] if r.get("kind") == "SECTOR"]
        assert len(sectors) == 1
        themes = [(lane, r) for lane, rs in view.items() for r in rs if r.get("kind") == "THEME"]
        should_buy = name == "initial-entry" or (stage == "emerging" and name in
                                                {"current-continuing", "bad-envelope-refresh"})
        assert any(lane == "buy_now" for lane, _ in themes) is should_buy, (stage, name, themes)
        for lane, row in themes:
            assert row["theme_decision"]["stock_entry_permission"] is False
            if name in {"stale-result", "no-refresh-stale", "owner-fails-stale"}:
                assert row["theme_decision"]["status"] == "UNAVAILABLE"
                assert row["reco"] is None
            if name == "same-session-hold":
                assert row["reco"] == "hold"
        if name == "bad-envelope-rerender":
            assert themes == []
        rows.append({"stage": stage, "case": name, "owner_calls": calls,
                     "sector_cards": len(sectors), "theme_buy": should_buy,
                     "themes": [{"lane": lane, "id": r["id"], "reco": r.get("reco"),
                                 "route": r.get("entry_route"), "decision": r["theme_decision"]}
                                for lane, r in themes]})
    del sys.modules[module.__name__]
assert digest(source_path.read_bytes()) == source_before
report = {"proof_kind": "pinned caller-to-consumer composition; synthetic inputs",
          "not_proven": ["production", "independent review", "whole-repo integration", "investment performance"],
          "caller": CALLER, "caller_sha256": source_before,
          "consumers": CONSUMERS, "consumer_sha256": consumer_hashes,
          "clock": CLOCK.isoformat(), "cases": rows, "source_unchanged": True}
out = Path(__file__).with_name("handoff_proof.json")
out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
print(json.dumps({"cases": len(rows), "failed": 0, "receipt_sha256": digest(out.read_bytes())}))
