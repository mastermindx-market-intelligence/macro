from __future__ import annotations
import copy
import datetime as dt
import hashlib
import importlib.util
import itertools
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import types
from dataclasses import replace
from unittest.mock import patch

root = Path.cwd()
sys.path.insert(0, str(root))
from engine import sector_central as current, sector_cycles, conditions, cycles, inputs, narrative_rotation

base = "0c4c28e4a3e1ba0b1dde3ebdd9774355822f1527"
source = subprocess.check_output(["git", "show", base + ":engine/sector_central.py"], text=True)
legacy = types.ModuleType("sector_central_before_explicit_inputs")
legacy.__file__ = str(root / "engine/sector_central.py")
exec(compile(source, legacy.__file__, "exec"), legacy.__dict__)
spec = importlib.util.spec_from_file_location("sector_core_parity_fixtures", root / "tests/test_sector_central.py")
fixtures = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixtures)
real_datetime = dt.datetime

class FixedDateTime(real_datetime):
    @classmethod
    def now(cls, tz=None):
        value = cls(2026, 11, 6, 0, 0, tzinfo=dt.timezone.utc)
        return value if tz is None else value.astimezone(tz)

results = []
with tempfile.TemporaryDirectory(prefix="mmx-sector-core-parity-") as scratch:
    data = Path(scratch)
    (data / "baskets").mkdir()
    (data / "us_sector_rotation").mkdir()
    for rotation_session, membership_mode in itertools.product(
            [None, "2026-11-04", "2026-11-05", "2026-11-09"],
            ["normal", "empty", "missing", "malformed"]):
        bundle = fixtures._explicit_central_inputs(rotation_session=rotation_session)
        membership_path = data / "baskets/membership.json"
        membership_path.unlink(missing_ok=True)
        if membership_mode == "normal":
            membership_path.write_text(json.dumps(bundle.membership_document))
        elif membership_mode == "empty":
            membership_path.write_text("{}")
            bundle = replace(bundle, membership_document={})
        elif membership_mode == "malformed":
            membership_path.write_text("{")
            bundle = replace(bundle, membership_document=None, membership_unavailable=True)
        else:
            bundle = replace(bundle, membership_document=None, membership_unavailable=True)
        (data / "us_sector_rotation/latest.json").write_text(json.dumps(bundle.rotation_artifact))
        with patch.object(current.config, "data_dir", lambda: data), \
             patch.object(sector_cycles, "compute", lambda: copy.deepcopy(bundle.cycle_spine)), \
             patch.object(inputs, "yahoo_closes", lambda: bundle.closes.copy(deep=True)), \
             patch.object(narrative_rotation, "compute_narrative_rotation", lambda **kwargs: copy.deepcopy(bundle.narrative_rotation)), \
             patch.object(conditions, "sector_macro_beta", lambda key: 0.4), \
             patch.object(cycles, "risk_size_mult", lambda state, family: 0.8), \
             patch.object(legacy, "market_context", lambda: copy.deepcopy(bundle.market_context)), \
             patch.object(current, "market_context", lambda: copy.deepcopy(bundle.market_context)), \
             patch.object(legacy, "_load_rotation_events", lambda: copy.deepcopy(bundle.rotation_events)), \
             patch.object(current, "_load_rotation_events", lambda: copy.deepcopy(bundle.rotation_events)), \
             patch.object(dt, "datetime", FixedDateTime):
            before = legacy.compute()
            after = current.compute()
            explicit = current.compute_from_inputs(bundle, evaluation_date=dt.date(2026, 11, 6))
        assert before == after == explicit, (rotation_session, membership_mode)
        encoded = json.dumps(after, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        results.append({"rotation_session": rotation_session, "membership": membership_mode,
                        "output_sha256": hashlib.sha256(encoded).hexdigest()})
receipt = {"scope": "deterministic source parity on sixteen constructed cases; no production proof",
           "base": base, "legacy_source_sha256": hashlib.sha256(source.encode()).hexdigest(),
           "cases_equal": len(results), "cases": results}
Path("/tmp/macro-sector-core-parity-20261105-c3.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps({"cases_equal": len(results), "distinct_outputs": len({r["output_sha256"] for r in results}),
                  "receipt": "/tmp/macro-sector-core-parity-20261105-c3.json"}))
