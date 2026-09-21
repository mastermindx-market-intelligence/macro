#!/usr/bin/env python3
"""Gate: a P0B construction-input change must remint the browser receipts.

#7603 changed templates/hk.html.j2 without reminting
mockups/evidence/prophet-p0b-zero-fouc/mobile-layout*.json (still pinning the
prior digest), the same class as #7500 / site/navigation-refresh.css (healed
by #7597). Pure main then fails the receipt tests in
tests/test_stock_dashboard_first_frame.py, and every fresh merge-ref inherits
it. This guard is the GATE for that class.

The pinned set is derived at runtime FROM the committed receipts: each
mobile-layout*.json file's construction_inputs keys, loaded_assets keys, and
verifier.path, plus rendered-fixture.json's recipe input paths and the
fixture path the receipts bind. Template names are never hardcoded as the
live pin set.

Given a diff file-list: if any pinned path changed without a same-diff change
to every receipt that pins it, exit 1 naming the path and the remint command.
Exit 0 otherwise.

Usage:
    python3 scripts/check_p0b_receipt_closure.py --diff-file /tmp/changed.txt
    git diff --name-only "$MB" HEAD | python3 scripts/check_p0b_receipt_closure.py --diff-file -
    python3 scripts/check_p0b_receipt_closure.py --selftest
Exit codes: 0 = closed / nothing pinned moved / selftest passed
            1 = pinned path moved without its receipts / selftest failed
            2 = cannot derive the pin set (missing receipts / sparse refuse)
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

# Location of the receipts, not the pin set. The pin set is read from the
# JSON at runtime. Fallback glob is the same location the spec names.
EVIDENCE_DIR_REL = "mockups/evidence/prophet-p0b-zero-fouc"
RECEIPT_GLOB = "mobile-layout*.json"
FIXTURE_NAME = "rendered-fixture.json"
RECEIPT_SCHEMA = "mastermind.stock_dashboard_mobile_layout.v1"
FIXTURE_SCHEMA = "mastermind.stock_dashboard_rendered_fixture.v1"


def _posix(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def _sparse_refusal(root: Path) -> str | None:
    """Refuse rather than pass vacuously when the evidence tree is omitted."""
    try:
        from scripts.worktree_sparse import missing_dirs, remedy_line
    except Exception:  # noqa: BLE001
        return None
    try:
        absent = [d for d in missing_dirs(root) if d == "mockups"]
    except Exception:  # noqa: BLE001
        return None
    return remedy_line(absent) if absent else None


def parse_changed_paths(text: str) -> set[str]:
    """Accept `git diff --name-only` output or a unified diff."""
    lines = text.splitlines()
    if any(line.startswith("diff --git ") for line in lines):
        paths: set[str] = set()
        for line in lines:
            if not line.startswith("diff --git "):
                continue
            parts = line.split()
            if len(parts) < 4:
                continue
            right = parts[-1]
            if right.startswith("b/"):
                right = right[2:]
            if right and right != "/dev/null":
                paths.add(right)
        return paths
    out: set[str] = set()
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith('"') and line.endswith('"'):
            line = line[1:-1]
        out.add(line)
    return out


def load_browser_receipts(root: Path) -> list[tuple[str, dict]]:
    """Return (repo-relative path, payload) for every committed P0B receipt."""
    evidence = root / EVIDENCE_DIR_REL
    if not evidence.is_dir():
        return []
    rows: list[tuple[str, dict]] = []
    for path in sorted(evidence.glob(RECEIPT_GLOB)):
        if not path.is_file():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(payload, dict):
            continue
        if payload.get("schema") != RECEIPT_SCHEMA:
            continue
        rows.append((_posix(path, root), payload))
    return rows


def load_fixture(root: Path, relpath: str) -> dict | None:
    path = root / relpath
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict) or payload.get("schema") != FIXTURE_SCHEMA:
        return None
    return payload


def fixture_recipe_inputs(fixture: dict | None) -> set[str]:
    if not fixture:
        return set()
    paths: set[str] = set()
    markets = fixture.get("markets")
    if not isinstance(markets, dict):
        return paths
    for market in markets.values():
        if not isinstance(market, dict):
            continue
        for item in market.get("inputs") or []:
            if isinstance(item, dict) and isinstance(item.get("path"), str):
                paths.add(item["path"])
    return paths


def derive_pin_sets(root: Path) -> tuple[dict[str, set[str]], str | None]:
    """Map each receipt path to the paths it pins. Second value is a refuse reason."""
    receipts = load_browser_receipts(root)
    if not receipts:
        sparse = _sparse_refusal(root)
        if sparse:
            return {}, f"REFUSED: cannot derive the P0B pin set ({sparse})"
        return {}, (
            f"REFUSED: no {RECEIPT_SCHEMA} receipts under "
            f"{EVIDENCE_DIR_REL}/{RECEIPT_GLOB}"
        )

    pin_sets: dict[str, set[str]] = {}
    fixture_cache: dict[str, dict | None] = {}
    for relpath, payload in receipts:
        pins: set[str] = set()
        for key in ("construction_inputs", "loaded_assets"):
            block = payload.get(key)
            if isinstance(block, dict):
                pins.update(k for k in block if isinstance(k, str) and k)
        verifier = payload.get("verifier")
        if isinstance(verifier, dict) and isinstance(verifier.get("path"), str):
            pins.add(verifier["path"])
        fixture_row = payload.get("fixture_receipt")
        fixture_path = None
        if isinstance(fixture_row, dict) and isinstance(fixture_row.get("path"), str):
            fixture_path = fixture_row["path"]
            pins.add(fixture_path)
        if fixture_path:
            if fixture_path not in fixture_cache:
                fixture_cache[fixture_path] = load_fixture(root, fixture_path)
            pins.update(fixture_recipe_inputs(fixture_cache[fixture_path]))
        else:
            default_fixture = f"{EVIDENCE_DIR_REL}/{FIXTURE_NAME}"
            if default_fixture not in fixture_cache:
                fixture_cache[default_fixture] = load_fixture(root, default_fixture)
            pins.update(fixture_recipe_inputs(fixture_cache[default_fixture]))
        pin_sets[relpath] = pins
    return pin_sets, None


def remint_command(root: Path) -> str:
    """Name the remint recipe from the receipts themselves when possible."""
    receipts = load_browser_receipts(root)
    verifier = "scripts/verify_stock_dashboard_mobile_layout.cjs"
    fixture = f"{EVIDENCE_DIR_REL}/{FIXTURE_NAME}"
    recipe = "scripts/render_stock_dashboard_fixture.py"
    historical_head = None
    historical_tree = None
    assets = f"{EVIDENCE_DIR_REL}/inputs/browser-data"
    for _rel, payload in receipts:
        v = payload.get("verifier")
        if isinstance(v, dict) and isinstance(v.get("path"), str):
            verifier = v["path"]
        fr = payload.get("fixture_receipt")
        if isinstance(fr, dict) and isinstance(fr.get("path"), str):
            fixture = fr["path"]
        hb = payload.get("historical_baseline")
        if isinstance(hb, dict):
            if isinstance(hb.get("candidate_head"), str):
                historical_head = hb["candidate_head"]
            if isinstance(hb.get("candidate_tree"), str):
                historical_tree = hb["candidate_tree"]
        far = payload.get("fixture_assets_root")
        if isinstance(far, str) and far:
            assets = far
    loaded = load_fixture(root, fixture)
    if loaded:
        for path in sorted(fixture_recipe_inputs(loaded)):
            if path.endswith("render_stock_dashboard_fixture.py"):
                recipe = path
                break
    hist = ""
    if historical_head and historical_tree:
        hist = (
            f" --historical-head {historical_head}"
            f" --historical-tree {historical_tree}"
        )
    outs = " ".join(f"--out {rel}" for rel, _ in receipts) or (
        f"--out {EVIDENCE_DIR_REL}/mobile-layout.json"
    )
    return (
        f"python3 {recipe} --market all --out-dir DIR --receipt {fixture} && "
        f"node {verifier} --html DIR/<market>.html --site-dir site "
        f"--fixture-receipt {fixture} --fixture-assets-dir {assets} "
        f"--screenshot-dir {EVIDENCE_DIR_REL}{hist} ({outs})"
    )


def evaluate(changed: set[str], pin_sets: dict[str, set[str]]) -> list[str]:
    """Return findings: pinned paths that moved without their receipts."""
    findings: list[str] = []
    for relpath, pins in sorted(pin_sets.items()):
        if relpath in changed:
            continue
        moved = sorted(path for path in pins if path in changed)
        for path in moved:
            findings.append(
                f"PINNED PATH CHANGED WITHOUT RECEIPT: {path} is pinned by "
                f"{relpath}, which is not in the same diff"
            )
    return findings


def run_selftest() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="check_p0b_receipt_closure_selftest_"))
    evidence = tmp / EVIDENCE_DIR_REL
    evidence.mkdir(parents=True)
    hk_receipt = evidence / "mobile-layout.json"
    ca_receipt = evidence / "mobile-layout-canada.json"
    fixture = evidence / FIXTURE_NAME
    pinned = "templates/zz-selftest.html.j2"
    fixture.write_text(
        json.dumps(
            {
                "schema": FIXTURE_SCHEMA,
                "proof_class": "rendered_fixture",
                "markets": {
                    "hk": {
                        "inputs": [
                            {"path": pinned, "sha256": "a" * 64},
                            {
                                "path": "scripts/render_stock_dashboard_fixture.py",
                                "sha256": "b" * 64,
                            },
                        ]
                    }
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )
    hk_receipt.write_text(
        json.dumps(
            {
                "schema": RECEIPT_SCHEMA,
                "construction_inputs": {pinned: "a" * 64},
                "loaded_assets": {"site/stock-dashboard.css": "c" * 64},
                "verifier": {
                    "path": "scripts/verify_stock_dashboard_mobile_layout.cjs",
                    "sha256": "d" * 64,
                },
                "fixture_receipt": {
                    "path": f"{EVIDENCE_DIR_REL}/{FIXTURE_NAME}",
                    "sha256": "e" * 64,
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )
    ca_receipt.write_text(
        json.dumps(
            {
                "schema": RECEIPT_SCHEMA,
                "construction_inputs": {"templates/zz-selftest-ca.html.j2": "f" * 64},
                "loaded_assets": {"site/stock-dashboard.css": "c" * 64},
                "verifier": {
                    "path": "scripts/verify_stock_dashboard_mobile_layout.cjs",
                    "sha256": "d" * 64,
                },
                "fixture_receipt": {
                    "path": f"{EVIDENCE_DIR_REL}/{FIXTURE_NAME}",
                    "sha256": "e" * 64,
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )

    pin_sets, refuse = derive_pin_sets(tmp)
    if refuse or not pin_sets:
        print(f"selftest FAIL: could not derive pin sets: {refuse}")
        return 1
    if pinned not in pin_sets[f"{EVIDENCE_DIR_REL}/mobile-layout.json"]:
        print("selftest FAIL: construction input was not derived from the receipt")
        return 1

    # RED: pinned path alone.
    red = evaluate({pinned}, pin_sets)
    if not red:
        print("selftest FAIL: pinned-path-only diff unexpectedly passed")
        return 1

    # GREEN: pinned path plus every receipt that pins it (recipe inputs bind both).
    green = evaluate(
        {
            pinned,
            f"{EVIDENCE_DIR_REL}/mobile-layout.json",
            f"{EVIDENCE_DIR_REL}/mobile-layout-canada.json",
        },
        pin_sets,
    )
    if green:
        print(f"selftest FAIL: reminted receipts still red: {green}")
        return 1

    # GREEN: unrelated path.
    clean = evaluate({"engine/unrelated.py"}, pin_sets)
    if clean:
        print(f"selftest FAIL: unrelated path red: {clean}")
        return 1

    print("check_p0b_receipt_closure selftest OK", flush=True)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--diff-file",
        help="Changed-path list (`git diff --name-only`) or a unified diff; '-' reads stdin.",
    )
    parser.add_argument(
        "--repo-root",
        default=str(_ROOT),
        help="Repo root the receipts resolve against.",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="Run the built-in selftest and exit.",
    )
    args = parser.parse_args(argv)

    if args.selftest:
        return run_selftest()

    if not args.diff_file:
        print(
            "::error title=p0b-receipt-closure::--diff-file PATH is required (or use --selftest)",
            flush=True,
        )
        return 1

    root = Path(args.repo_root)
    if args.diff_file == "-":
        diff_text = sys.stdin.read()
    else:
        try:
            diff_text = Path(args.diff_file).read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            print(
                f"::error title=p0b-receipt-closure::could not read --diff-file: {exc}",
                flush=True,
            )
            return 1

    pin_sets, refuse = derive_pin_sets(root)
    if refuse:
        print(f"::error title=p0b-receipt-closure::{refuse}", flush=True)
        return 2

    changed = parse_changed_paths(diff_text)
    findings = evaluate(changed, pin_sets)
    if not findings:
        return 0
    hint = remint_command(root)
    for finding in findings:
        print(f"::error title=p0b-receipt-closure::{finding}", flush=True)
    print(
        f"::error title=p0b-receipt-closure::re-mint with: {hint}",
        flush=True,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
