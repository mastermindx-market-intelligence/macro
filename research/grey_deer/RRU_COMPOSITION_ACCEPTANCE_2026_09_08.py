"""Actual-module, synthetic-input composition-to-consumer acceptance; no product writes."""
from __future__ import annotations
import argparse
import ast
from contextlib import ExitStack
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch
import numpy as np
import pandas as pd
from jinja2 import Environment, DictLoader, ChainableUndefined

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from engine import risk_radar_intl as radar, market_state, risk_radar_recovery as recovery
from engine import risk_radar_intl_audit as radar_audit
from engine import risk_radar_intl_tune as radar_tune
PIN = "eb9e91961ddc4f3043d0dad358602525e66eccda"
PATHS = ("engine/risk_radar_intl.py", "engine/market_state.py",
         "engine/risk_radar_recovery.py", "templates/_risk_radar_card.html.j2")

def committed(path):
    p = subprocess.run(["git", "show", f"{PIN}:{path}"], cwd=ROOT,
                       capture_output=True, check=True, timeout=30)
    return p.stdout.decode()

SOURCES = {path: committed(path) for path in PATHS}
TEMPLATE = SOURCES[PATHS[-1]]
RENDER_SOURCES = {PATHS[-1]: TEMPLATE}

def apply_bundle(bundle):
    global TEMPLATE
    modules = {PATHS[0]: radar, PATHS[1]: market_state, PATHS[2]: recovery,
               "engine/risk_radar_intl_audit.py": radar_audit,
               "engine/risk_radar_intl_tune.py": radar_tune}
    for path, entry in bundle.items():
        text = SOURCES.get(path) or committed(path)
        if hashlib.sha256(text.encode()).hexdigest() != entry["base_sha256"]:
            raise ValueError(f"Wrong source identity: {path}")
        for delta in entry["replacements"]:
            if text.count(delta["old"]) != 1:
                raise ValueError(f"Nonunique replacement: {path}")
            text = text.replace(delta["old"], delta["new"], 1)
        if path not in modules:
            if not path.startswith("templates/"):
                raise ValueError(f"Unsupported research bundle path: {path}")
            RENDER_SOURCES[path] = text
            if path == PATHS[-1]:
                TEMPLATE = text
            continue
        nodes = [n for n in ast.parse(text).body if isinstance(n, ast.FunctionDef)
                 and n.name in entry["functions"]]
        assert {n.name for n in nodes} == set(entry["functions"])
        future = ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0)
        code = ast.fix_missing_locations(ast.Module(body=[future, *nodes], type_ignores=[]))
        exec(compile(code, path, "exec"), modules[path].__dict__)

INDEX = pd.bdate_range("2023-01-02", periods=620)
BENCH = pd.Series(np.linspace(100, 140, len(INDEX)), index=INDEX)

def fixture(profile):
    codes = sorted({c for _, members, _ in profile.comp_legs for c in members})
    rng = np.random.default_rng(20260908)
    return {c: pd.Series(rng.uniform(.1, .9, len(INDEX)), index=INDEX) for c in codes}

def compute(profile, sub, bench=BENCH):
    with ExitStack() as stack:
        stack.enter_context(patch.object(radar, "_read", return_value=bench))
        stack.enter_context(patch.object(radar, "_sub_legs", return_value=sub))
        stack.enter_context(patch.object(radar, "_gate_series", return_value=pd.Series(True, index=INDEX)))
        stack.enter_context(patch.object(radar, "_calib", side_effect=lambda p, *a:
            dict(bands=dict(radar._BANDS), prob_cal=p.prob_cal, prob_base=p.prob_base)))
        return radar.compute(profile)

def project(out):
    with patch.object(market_state, "_rr_scorecard_track", return_value=None):
        rd = market_state._radar_to_rd(out)
    with patch.object(recovery, "_liquidity_catalysts", return_value=[]), \
         patch.object(recovery, "_market_catalysts", return_value=None):
        rd["recovery"] = recovery.assess({"risk_radar": out})
    return rd

def render(rd):
    env = Environment(loader=DictLoader({"card": TEMPLATE}),
                      undefined=ChainableUndefined, autoescape=True)
    return env.get_template("card").module.risk_radar_card(rd, [])

class CompositionAcceptance(unittest.TestCase):
    pass

def case_test(profile, case):
    def test(self):
        sub = fixture(profile)
        group = max(profile.comp_legs, key=lambda item: len(item[1]))[1]
        if case == "member_missing":
            sub[group[0]].iloc[-1] = np.nan
        elif case == "group_missing":
            for code in group:
                sub[code].iloc[-1] = np.nan
        elif case in ("all_missing", "old_score"):
            for series in sub.values():
                series.iloc[-1 if case == "all_missing" else -5:] = np.nan
        elif case == "restored":
            for code in group:
                sub[code].iloc[-20:-10] = np.nan
        elif case == "nonfinite":
            sub[group[0]].iloc[-1] = np.inf
        elif case == "structural_missing":
            del sub[group[0]]
        out = compute(profile, sub, None if case == "no_benchmark" else BENCH)
        self.assertIn("composition", out, "Producer must supply input composition")
        q = out["composition"]
        wanted = "UNAVAILABLE" if case in ("all_missing", "old_score", "no_benchmark") else (
            "COMPLETE" if case in ("complete", "restored") else "PARTIAL")
        self.assertEqual(q["status"], wanted)
        self.assertEqual(q["freshness"], "not_assessed")
        self.assertEqual(q["groups_expected"], len(profile.comp_legs))
        self.assertEqual(q["members_expected"], sum(len(x[1]) for x in profile.comp_legs))
        self.assertEqual(q["comparison_comparable"], case == "complete")
        self.assertEqual(q["members_available"], sum(len(x["present"]) for x in q["groups"]))
        rd = project(out)
        self.assertEqual(rd.get("composition"), q)
        html = render(rd)
        self.assertIn("Input coverage", html)
        self.assertIn("输入覆盖", html)
        if case != "complete":
            self.assertFalse((rd.get("recovery") or {}).get("receding", False))
            self.assertIn("Recovery comparison unavailable", html)
        if wanted == "UNAVAILABLE":
            self.assertIsNone(out.get("state"))
            self.assertIsNone(out.get("top_score"))
            self.assertIsNone(rd.get("dd21"))
            self.assertIn("Reading unavailable", html)
            self.assertNotIn("rrx-calm", html)
        if case not in ("all_missing", "old_score", "no_benchmark", "nonfinite"):
            self.assertIsNotNone(out.get("top_score"))
            self.assertIsNone(rd.get("dd21"), "Unreviewed old calibration is not a current forecast")
            self.assertIsNone(out.get("drawdown_prob"))
            self.assertIsNone(out.get("gross_factor"))
            self.assertEqual(rd.get("legacy_drawdown_prob"),
                             out["legacy_calibration_reference"]["drawdown_prob"])
        json.dumps(out, allow_nan=False)
    return test

for p in radar.PROFILES.values():
    for case in ("complete", "member_missing", "group_missing", "all_missing",
                 "old_score", "restored", "nonfinite", "structural_missing", "no_benchmark"):
        setattr(CompositionAcceptance, f"test_{p.key}_{case}", case_test(p, case))

class LegacyAcceptance(unittest.TestCase):
    def test_legacy_projection_retains_numbers_and_authority(self):
        out = dict(state="elevated", top_score=88, can_force=True,
                   gross_factor=.78, drawdown_prob=dict(h21=.4), market="us")
        rd = project(out)
        self.assertEqual((rd["dd21"], rd["gross"], rd["can_force"]), (.4, .78, True))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", type=Path)
    parser.add_argument("--candidate", action="store_true", help="Use the existing in-memory candidate module")
    args = parser.parse_args()
    before = {path: (ROOT / path).read_bytes() for path in PATHS[:3]}
    for path, raw in before.items():
        if raw.decode() != SOURCES[path]:
            raise SystemExit(f"Current source differs from the pinned fixture: {path}")
    if args.bundle and args.candidate:
        parser.error("Choose either --bundle or --candidate")
    if args.bundle:
        apply_bundle(json.loads(args.bundle.read_text()))
    if args.candidate:
        from RRU_COMPOSITION_BUILD_BUNDLE_2026_09_08 import bundle
        apply_bundle(bundle)
    suite = unittest.TestSuite([
        unittest.defaultTestLoader.loadTestsFromTestCase(CompositionAcceptance),
        unittest.defaultTestLoader.loadTestsFromTestCase(LegacyAcceptance)])
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    unchanged = all((ROOT / p).read_bytes() == raw for p, raw in before.items())
    print(json.dumps(dict(tests=result.testsRun, failures=len(result.failures),
          errors=len(result.errors), source_unchanged=unchanged,
          candidate=bool(args.bundle or args.candidate), synthetic_inputs=True)))
    raise SystemExit(0 if result.wasSuccessful() and unchanged else 1)

if __name__ == "__main__":
    main()
