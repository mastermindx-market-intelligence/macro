"""ROR-1 regional regime JSON boundary — actual HK/CA/CN run() TDD.

Synthetic upstream regime fixtures; no market collector, remote writer or network executes.
Calls the actual country run() with upstream data/data-dir side effects mocked.
"""
from __future__ import annotations

from contextlib import ExitStack
from pathlib import Path
from types import ModuleType
from unittest import TestCase
from unittest.mock import patch
import json
import sys
import tempfile

import pandas as pd

def source_module(market):
    # Source lives in this PR's normal Macro tree; don't import a private worktree.
    from importlib import import_module
    return import_module(f"engine.{market}_run")

def frame(*, pending=None):
    idx=pd.DatetimeIndex(["2026-10-15"])
    return pd.DataFrame({
        "quad":["Q2"],"quad_name":["Reflation"],
        "growth_score":[0.1],"inflation_score":[0.2],
        "growth_confidence":[0.84],"inflation_confidence":[0.82],
        "regime_confidence":[0.85],"liquidity":["neutral"],"cycle":["mid"],
        "pending_quad":[pending],"pending_days":[0],
        "global_score":[float("nan")],"risk_state":[None],"peg_state":[None],
        "peg_distance":[float("nan")],
    },index=idx)


def stub_module(name,attrs):
    module=ModuleType(name)
    for key,val in attrs.items():
        setattr(module,key,val)
    return module


def exercise(market, path, *, pending=None, ratios=None):
    mod=source_module(market)
    mocked={
        "engine.hk_market_drivers":stub_module("engine.hk_market_drivers",{
            "snapshot":lambda:{}, "append_log":lambda *args,**kw:None,
        }),
        "engine.hk_conditions":stub_module("engine.hk_conditions",{
            "snapshot":lambda *args,**kw:{}, "fear_euphoria":lambda *args,**kw:{},
        }),
        "engine.hk_property":stub_module("engine.hk_property",{"regime_context":lambda:{}}),
        "engine.hk_alerts":stub_module("engine.hk_alerts",{
            "evaluate":lambda **kw:[], "log_and_dedup":lambda *args,**kw:[],
        }),
        "engine.china_market_drivers":stub_module("engine.china_market_drivers",{
            "snapshot":lambda:{}, "append_log":lambda *args,**kw:None,
        }),
        "engine.china_conditions":stub_module("engine.china_conditions",{
            "snapshot":lambda *args,**kw:{}, "fear_euphoria":lambda *args,**kw:{},
        }),
        "engine.china_property":stub_module("engine.china_property",{"regime_context":lambda:{}}),
        "engine.china_alerts":stub_module("engine.china_alerts",{
            "evaluate":lambda **kw:[], "log_and_dedup":lambda *args,**kw:[],
        }),
    }
    with ExitStack() as stack:
        stack.enter_context(patch.dict(sys.modules,mocked))
        stack.enter_context(patch.object(mod.config,"data_dir",return_value=path))
        stack.enter_context(patch.object(mod,"build_features",return_value=pd.DataFrame()))
        stack.enter_context(patch.object(mod,"classify",return_value=frame(pending=pending)))
        stack.enter_context(patch.object(mod,"check_coverage_regression",return_value=None))
        stack.enter_context(patch.object(pd.DataFrame,"to_parquet",return_value=None))
        stack.enter_context(patch.object(mod,"rs_table",return_value=pd.DataFrame()))
        stack.enter_context(patch.object(mod,"pair_ratios_snapshot",return_value=ratios if ratios is not None else {}))
        stack.enter_context(patch.object(mod,"preference_check",return_value={}))
        if market=="hk":
            stack.enter_context(patch.object(mod.hk_global,"snapshot",return_value={}))
        elif market=="canada":
            stack.enter_context(patch.object(mod.canada_overlay,"snapshot",return_value={}))
        return mod.run()


def strict_json(path):
    return json.loads(path.read_text(),parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)))


class CountryJsonBoundary(TestCase):
    def test_null_unknown_and_valid_quadrant_preserved_across_three_owners(self):
        for market in ("hk","canada","china"):
            for pending in (float("nan"),pd.NA,"Q3"):
                with self.subTest(market=market,pending=repr(pending)),tempfile.TemporaryDirectory() as td:
                    out=Path(td)
                    returned=exercise(market,out,pending=pending)
                    source=out/f"{market}_regime"/"latest.json"
                    doc=strict_json(source)
                    self.assertEqual(doc["pending_quad"],None if not isinstance(pending,str) else pending)
                    self.assertEqual(returned["pending_quad"],doc["pending_quad"])
                    self.assertEqual(doc["date"],"2026-10-15")
                    self.assertEqual(doc["quad"],"Q2")

    def test_nonfinite_nested_values_are_strictly_represented_as_null(self):
        with tempfile.TemporaryDirectory() as td:
            returned=exercise("hk",Path(td),pending=float("inf"),ratios={"a":[float("nan"),float("-inf"),4.0]})
            d=strict_json(Path(td)/"hk_regime"/"latest.json")
            self.assertEqual(d["pair_ratios"],{"a":[None,None,4.0]})
            self.assertIsNone(d["pending_quad"])
            self.assertEqual(returned["pair_ratios"],d["pair_ratios"])

    def test_invalid_encoder_cannot_destroy_previous_last_good(self):
        for market in ("hk","canada","china"):
            with self.subTest(market=market),tempfile.TemporaryDirectory() as td:
                dest=Path(td)/f"{market}_regime"/"latest.json"
                dest.parent.mkdir()
                previous=b'{"version":"accepted","risk":"safe-not-asserted"}'
                dest.write_bytes(previous)
                with self.assertRaises((ValueError,TypeError)):
                    exercise(market,Path(td),ratios={float("nan"):1})
                self.assertEqual(dest.read_bytes(),previous)
                self.assertFalse(list(dest.parent.glob("*.tmp")))
