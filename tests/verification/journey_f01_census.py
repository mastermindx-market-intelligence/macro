#!/usr/bin/env python3
"""F01-1 census driver — proof that inspection triggers nothing (F01.03).

Run ONLY as a subprocess by ``tests/verification/test_journey_f01.py``:

    python -B journey_f01_census.py --store <synthetic-store> --cfg <bindings.json>

The fixture (synthetic store, basket history, host bindings, the outside.txt
sentinel and the in-root symlink) is built by the TEST before this driver runs;
the driver itself creates nothing.  ``sys.addaudithook`` is installed BEFORE any
project module is imported, so every socket / subprocess / write-mode open /
filesystem mutation any consumer call makes is counted.  The CLI transport leg
is deliberately excluded from this census: ``scripts/data_workspace.py`` spawns
``git`` for its implementation revision (pre-existing, disclosed), so the
in-process ``dispatch`` carries the inspector leg here.

The one JSON object printed to stdout carries store-relative paths and path
CLASSES only — never an absolute host path.
"""
from __future__ import annotations

import os
import sys

# ── the audit hook: installed before any project module is imported ──────────
_OS_MUTATIONS = ("os.remove", "os.rename", "os.replace", "os.mkdir", "os.rmdir",
                 "os.truncate")
_WATCHED_NETWORK = ("requests", "urllib3", "httpx", "anthropic", "openai",
                    "yfinance", "boto3", "botocore")
_WRITE_FLAGS = (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_APPEND | os.O_TRUNC)
COUNTS: dict[str, object] = {
    "socket_events": 0,
    "subprocess_popen": 0,
    "shutil_events": 0,
    "os_mutations": {name: 0 for name in _OS_MUTATIONS},
    "network_modules_imported": [],
    "write_opens_inside_store": 0,
    "write_opens_outside_by_class": {"tmp": 0, "cache": 0, "other": 0},
}
STATE = {"store": None}


def _path_class(path: str) -> str:
    lowered = path.lower()
    if "/tmp" in lowered or lowered.startswith(os.environ.get("TMPDIR", "/__no_tmp__").lower()):
        return "tmp"
    if any(mark in lowered for mark in (".cache", "__pycache__", "/cache/")):
        return "cache"
    return "other"


def _audit(event, args) -> None:
    if event.startswith("socket."):
        COUNTS["socket_events"] += 1                      # type: ignore[index]
    elif event == "subprocess.Popen":
        COUNTS["subprocess_popen"] += 1                   # type: ignore[index]
    elif event.startswith("shutil."):
        COUNTS["shutil_events"] += 1                      # type: ignore[index]
    elif event in _OS_MUTATIONS:
        COUNTS["os_mutations"][event] += 1                # type: ignore[index]
    elif event == "import":
        name = args[0] if args else ""
        if name in _WATCHED_NETWORK:
            COUNTS["network_modules_imported"].append(name)   # type: ignore[union-attr]
    elif event == "open":
        path, mode, flags = args
        write = isinstance(mode, str) and any(c in mode for c in "wax+")
        try:
            write = write or bool(flags & _WRITE_FLAGS)
        except TypeError:
            pass
        if not write:
            return
        text = str(path)
        store = STATE["store"]
        if store is not None and text.startswith(store):
            COUNTS["write_opens_inside_store"] += 1       # type: ignore[index]
        else:
            cls = _path_class(text)                       # type: ignore[assignment]
            COUNTS["write_opens_outside_by_class"][cls] += 1  # type: ignore[index]


sys.addaudithook(_audit)

# ── stdlib + project imports happen only now, under the hook ─────────────────
import argparse  # noqa: E402
import hashlib  # noqa: E402
import json  # noqa: E402
from fractions import Fraction  # noqa: E402
from pathlib import Path  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from lib import config                                   # noqa: E402
from lib.dataos.nulls import MissingReason               # noqa: E402
from lib.dataos.read_contract import (Disposition, MemberDisposition, ReadMode,   # noqa: E402
                                      ReadRequest, SourceSegment, ViewContract,
                                      account_coverage, replay as read_contract_replay)
from lib.dataos.registry import load_registry            # noqa: E402
from lib.dataos.web_api import dispatch                  # noqa: E402
from lib.dataos.web_workspace import WorkspaceError, load_workspace_config  # noqa: E402
from engine import basket_membership_pit as pit          # noqa: E402
from engine.price_ladder import resolve_close_canonical, terminal_daily_ohlc_contract_v1  # noqa: E402

VIEW_ID = "f01-journey-v1"
BASKET_ID = "f01-basket"
MEMBERSHIP_DATE = "2026-01-15"
TIME_COL = "__index_level_0__"
NIGHT = "statv1:" + "0" * 64      # syntactically valid, wrong for every file


def snapshot(store: Path) -> dict[str, list]:
    """sha256 + st_mtime_ns of every regular file under the store, by relative path."""
    out: dict[str, list] = {}
    for p in sorted(store.rglob("*")):
        if p.is_symlink() or not p.is_file():
            continue        # the fixture's in-root symlink is a link, not a file
        out[p.relative_to(store).as_posix()] = [
            hashlib.sha256(p.read_bytes()).hexdigest(), p.stat().st_mtime_ns]
    return out


def view(ticker: str, mode: ReadMode = ReadMode.CURRENT, **kw) -> ReadRequest:
    listing = f"US-XNYS-{ticker}"
    contract = ViewContract(
        purpose=terminal_daily_ohlc_contract_v1()["purpose"],
        identity={"security_id": f"SEC:{listing}", "listing_id": listing, "mic": "XNYS"},
        field_units={}, adjustment_reference={"basis": "tradj"}, coverage="requested")
    return ReadRequest(mode=mode, contract=contract, **kw)


def refused(ws, cfg: Path, request: dict) -> str:
    try:
        dispatch(ws, request, config_path=cfg)
    except WorkspaceError as exc:
        return exc.code
    raise AssertionError(f"census expected a refusal for {request.get('ref')!r}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--store", type=Path, required=True)
    parser.add_argument("--cfg", type=Path, required=True)
    args = parser.parse_args()
    store, cfg = args.store.resolve(), args.cfg.resolve()
    STATE["store"] = str(store)
    calls = {"seam_served": 0, "seam_refused": 0, "describe": 0, "read": 0,
             "inspector_refusals": 0, "basket_calls": 0}
    before = snapshot(store)

    # The basket reader resolves through config.data_dir(); point it at the
    # synthetic store exactly as the test fixture does.  No IO of its own.
    config.data_dir = lambda: store
    ws = load_workspace_config(cfg)
    registry = load_registry(REPO / "config" / "dataset_registry.yml")

    # ── J1/J2: seam + inspector describe/read of the SAME declared view ──────
    seam_evidence = {}
    for ticker in ("PLAINCO", "SPLITCO"):
        cc = resolve_close_canonical(ticker, view=view(ticker),
                                     data_dir=str(store), registry=registry)
        assert cc.ok, ticker
        calls["seam_served"] += 1
        seam_evidence[ticker] = dict(cc.evidence_mode)
        ref = "store:" + cc.evidence_mode["source_path"]
        dispatch(ws, {"action": "describe", "ref": ref}, config_path=cfg)
        dispatch(ws, {"action": "read", "ref": ref,
                      "columns": [TIME_COL, cc.evidence_mode["column"]], "limit": 200},
                 config_path=cfg)
        calls["describe"] += 1
        calls["read"] += 1
    # J3: the raw/adjusted two-view read
    dispatch(ws, {"action": "read", "ref": "store:stocks/SPLITCO.parquet",
                  "columns": [TIME_COL, "close", "close_raw"], "limit": 200}, config_path=cfg)
    calls["read"] += 1

    # ── J5 stale/denied + J6 broken links, through the in-process transport ──
    for request in (
        {"action": "read", "ref": "store:stocks/PLAINCO.parquet",
         "expected_version": NIGHT, "limit": 5},
        {"action": "read", "ref": "store:../outside.txt"},
        {"action": "read", "ref": "store:missing.parquet"},
        {"action": "read", "ref": "store:stocks/leak.parquet"},
        {"action": "read", "ref": "nosuchroot:x.parquet"},
        {"action": "describe", "ref": "registry:no.such.dataset"},
    ):
        refused(ws, cfg, request)
        calls["inspector_refusals"] += 1

    # ── J6 seam refusals: the missing member and the replay ───────────────────
    gone = resolve_close_canonical("GONECO", view=view("GONECO"),
                                   data_dir=str(store), registry=registry)
    assert not gone.ok and gone.values is None
    calls["seam_refused"] += 1
    rep = resolve_close_canonical(
        "PLAINCO", view=view("PLAINCO", ReadMode.REPLAY, output_id="f01-no-such-output"),
        data_dir=str(store), registry=registry)
    assert not rep.ok and rep.values is None and rep.legacy is None
    calls["seam_refused"] += 1
    try:
        read_contract_replay(
            view("PLAINCO", ReadMode.REPLAY, output_id="f01-no-such-output"), None)
    except Exception as exc:  # noqa: BLE001 — the typed refusal is the expected exit
        assert getattr(exc, "code", None) is not None
    calls["seam_refused"] += 1

    # ── J4: basket membership + the fixed-population coverage account ────────
    members = pit.members_asof(BASKET_ID, MEMBERSHIP_DATE, suite=pit.SUITE_US)
    assert members["members"] == ["GONECO", "PLAINCO", "SPLITCO"]
    store_cov = pit.coverage(pit.SUITE_US)
    assert store_cov["snapshots"] == 1
    mapping = terminal_daily_ohlc_contract_v1()
    contract = ViewContract(
        purpose=mapping["purpose"],
        identity={"security_id": "BASKET:" + VIEW_ID, "listing_id": "US-XNYS-F01B"},
        field_units=dict(mapping["field_units"]),
        adjustment_reference=dict(mapping["adjustment_reference"]), coverage="requested")
    dispositions = [
        MemberDisposition(t, Disposition.SERVED, segments=(
            SourceSegment(source=seam_evidence[t]["source"],
                          basis=seam_evidence[t]["basis"], listing_id=t),))
        for t in ("PLAINCO", "SPLITCO")]
    dispositions.append(MemberDisposition(
        "GONECO", Disposition.MISSING, missing_reason=MissingReason.NO_COVERAGE))
    account = account_coverage(contract, ["PLAINCO", "SPLITCO", "GONECO"], dispositions)
    assert account.qualified_fraction == Fraction(2, 3)
    calls["basket_calls"] += 2

    after = snapshot(store)
    changes = sorted(set(before) ^ set(after)) + sorted(
        rel for rel in set(before) & set(after) if before[rel] != after[rel])
    print(json.dumps({
        "view_id": VIEW_ID,
        **COUNTS,
        "cli_leg": "excluded: scripts/data_workspace.py spawns git for its "
                   "implementation revision (pre-existing, disclosed)",
        "store_files_before": before,
        "store_files_after": after,
        "store_unchanged": before == after and not changes,
        "store_changes": changes,
        "journey_calls": calls,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
