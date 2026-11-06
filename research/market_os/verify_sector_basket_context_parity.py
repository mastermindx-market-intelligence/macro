"""Compare explicit cores and compatibility adapters with immutable original code.

Run from the repository: python research/market_os/verify_sector_basket_context_parity.py
The optional --write-golden records original outputs after every comparison passes.
No provider, production data or canonical history writer is used.
"""
from __future__ import annotations

import argparse
from contextlib import redirect_stdout
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import types

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import pytest  # noqa: E402
from engine import baskets as bk, theme_context as tc  # noqa: E402
from tests import test_sector_basket_context_inputs as fixtures  # noqa: E402

BASE = "38f2441def30f02cf2accf9ddfbaee334d86e1b5"


def original(path):
    raw = subprocess.check_output(["git", "show", BASE + ":" + path], cwd=ROOT)
    name = "_parity_original_" + path.replace("/", "_").replace(".", "_")
    module = types.ModuleType(name)
    module.__file__ = str(ROOT / path)
    sys.modules[name] = module
    exec(compile(raw, module.__file__, "exec"), module.__dict__)
    return module, hashlib.sha256(raw).hexdigest()


def compare():
    old_bk, bk_sha = original("engine/baskets.py")
    old_tc, tc_sha = original("engine/theme_context.py")
    golden = {
        "schema": "sector.basket_context_parity.v1",
        "baseline_commit": BASE,
        "baseline_source_sha256": {"engine/baskets.py": bk_sha, "engine/theme_context.py": tc_sha},
        "fixture_source": "tests/test_sector_basket_context_inputs.py",
        "baskets": {}, "context": {},
    }
    digests = {}
    for case in fixtures.BASKET_CASES:
        inputs = fixtures.basket_inputs(case)
        with pytest.MonkeyPatch.context() as patch:
            for module in (old_bk, bk):
                patch.setattr(module, "_membership", lambda: deepcopy(inputs.membership))
                patch.setattr(module, "_closes", lambda: inputs.closes.copy(deep=True))
                patch.setattr(module, "_basket_extras", lambda: inputs.extras.copy(deep=True))
                patch.setattr(module, "_names_sectors", lambda: dict(inputs.names_sectors))
            patch.setattr(bk.store, "read", lambda group, symbol:
                          inputs.spy if symbol == "SPY" else inputs.proxy_frames.get(symbol))
            with redirect_stdout(io.StringIO()):
                expected = fixtures.normalized(old_bk.compute_baskets())
                adapter = fixtures.normalized(bk.compute_baskets())
            core = fixtures.normalized(bk.compute_baskets_from_inputs(inputs))
        if expected != adapter or expected != core:
            raise AssertionError("Full basket output differs: " + case)
        golden["baskets"][case] = expected
        digests["baskets/" + case] = hashlib.sha256(
            json.dumps(expected, sort_keys=True, allow_nan=False).encode()
        ).hexdigest()

    for case in fixtures.CONTEXT_CASES:
        inputs = fixtures.context_inputs(case)
        with TemporaryDirectory(prefix="mmx-context-parity-") as temp:
            root = Path(temp)
            path = old_tc._alignment_path(inputs.region, root)
            if inputs.rotation_events is not None:
                path.parent.mkdir(parents=True)
                path.write_text(json.dumps(inputs.rotation_events))
            with pytest.MonkeyPatch.context() as patch:
                for module in (old_tc, tc):
                    patch.setattr(module, "_load_history", lambda *args: deepcopy(inputs.history))
                    patch.setattr(module, "_advance_enabled", lambda *args: False)
                    patch.setattr(module, "_write_history", fixtures.forbidden)
                expected = fixtures.normalized(old_tc.compute_theme_context(
                    inputs.allocation, inputs.theme_intel, inputs.region, root,
                ))
                adapter = fixtures.normalized(tc.compute_theme_context(
                    inputs.allocation, inputs.theme_intel, inputs.region, root,
                ))
                core = fixtures.normalized(tc.compute_theme_context_from_inputs(inputs))
        if expected != adapter or expected != core:
            raise AssertionError("Full context output differs: " + case)
        golden["context"][case] = expected
        digests["context/" + case] = hashlib.sha256(
            json.dumps(expected, sort_keys=True, allow_nan=False).encode()
        ).hexdigest()
    return golden, digests


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-golden", action="store_true")
    args = parser.parse_args()
    golden, digests = compare()
    if args.write_golden:
        fixtures.GOLDEN.parent.mkdir(parents=True, exist_ok=True)
        fixtures.GOLDEN.write_text(json.dumps(golden, sort_keys=True, indent=2, allow_nan=False) + "\n")
    else:
        if json.loads(fixtures.GOLDEN.read_text()) != golden:
            raise AssertionError("Committed original-output fixture differs")
    print(json.dumps({"baseline": BASE, "full_output_cases": len(digests),
                      "unique_output_digests": len(set(digests.values())),
                      "digests": digests, "golden": str(fixtures.GOLDEN)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
