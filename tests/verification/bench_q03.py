#!/usr/bin/env python3
"""Q03-1 frozen matched workload runner for the Data Workspace read path.

Run by hand (never collected by pytest: the file name does not start with
``test_``).  One bench process is the PARENT: it generates/verifies the frozen
fixture, writes the host binding configs, spawns one child DRIVER process per
(commit, round) and applies the pre-registered detection rule frozen in the
spec.  The parent never imports ``lib.*``; each driver inserts its target tree
at ``sys.path[0]`` and asserts where ``lib.dataos.web_workspace`` resolved from,
so the two commits (which share module names) are never imported into one
process.

Determinism: fixtures come from ``random.Random(seed)`` with fixed date
strings; no ``datetime.now``, no wall-clock-derived values, no network; timing
uses ``time.perf_counter_ns`` only.

Instruments (existing, no new collector): a ``sys.addaudithook`` counting
``open``/``os.listdir``/``os.scandir``/``subprocess.Popen``/``socket.connect``/
``socket.getaddrinfo`` per request (pyarrow opens files in C++ and is NOT seen
by it — /proc/self/io syscr/rchar deltas cover those reads), ``tracemalloc``
peak (Python heap only), ``pyarrow.total_allocated_bytes()`` deltas,
``resource.getrusage`` ru_maxrss at driver end and ``threading.active_count()``
around every request.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import random
import statistics
import subprocess
import sys
import threading
import time
import tracemalloc
from datetime import date, timedelta
from pathlib import Path

SPEC_VERSION = "dataos.q03.workload/v1"
BENCH_VERSION = "dataos.q03.bench/v1"
AUDIT_EVENTS = ("open", "os.listdir", "os.scandir", "subprocess.Popen",
                "socket.connect", "socket.getaddrinfo")
#: Response keys removed before the result digest, frozen in the spec.
#: ``observed_at`` is wall-clock; ``implementation_revision`` is the label the
#: harness passes in (identical at both commits, stripped per the spec anyway).
VOLATILE_KEYS = ("observed_at", "implementation_revision")
REQUEST_ORDER = ("R1", "R2", "R3", "R4", "R5", "R6", "R7", "R8", "R9",
                 "R10", "R11", "R12")
LIMITS_PATHS = ("lib/dataos/web_api.py", "lib/dataos/web_workspace.py",
                "lib/dataos/web_readers.py", "scripts/data_workspace.py")
ALPHABET = "abcdefghijklmnopqrstuvwxyz0123456789"
EVENT_KINDS = ("dividend", "split", "earnings", "guidance")
BASKET_MEMBERS = 300
BASKET_MEMBERS_2 = 150


# ─────────────────────────── fixture (frozen, seeded) ────────────────────────

def _business_dates(start_iso: str, n: int) -> list[str]:
    """n business days from a fixed ISO date — pure date arithmetic."""
    out: list[str] = []
    cur = date.fromisoformat(start_iso)
    while len(out) < n:
        if cur.weekday() < 5:
            out.append(cur.isoformat())
        cur += timedelta(days=1)
    return out


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write_text(path: Path, text: str) -> bytes:
    data = text.encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return data


def generate_fixture(fixture_dir: Path, spec: dict) -> dict:
    """Regenerate the frozen fixture; return the digest block for the spec."""
    import pandas as pd  # local, deterministic, seeded — no wall clock

    rng = random.Random(spec["seed"])
    fx = spec["fixture"]["shape"]
    digests: dict[str, dict] = {}

    # bars_small.csv — one ticker, business days from 2020-01-02.
    dates = _business_dates("2020-01-02", fx["bars_small_rows"])
    lines = ["date,ticker,open,high,low,close,volume"]
    for d in dates:
        o = round(100.0 + rng.random() * 50.0, 4)
        c = round(o + (rng.random() - 0.5) * 4.0, 4)
        hi = round(max(o, c) + rng.random() * 1.5, 4)
        lo = round(min(o, c) - rng.random() * 1.5, 4)
        vol = int(100000 + rng.random() * 4_900_000)
        lines.append(f"{d},T000,{o:.4f},{hi:.4f},{lo:.4f},{c:.4f},{vol}")
    data = _write_text(fixture_dir / "bars_small.csv", "\n".join(lines) + "\n")
    digests["bars_small.csv"] = {"sha256": _sha256_bytes(data), "rows": len(dates)}

    # bars_large.parquet — 100 tickers x 500 dates, sorted by (ticker, date).
    rows = {"date": [], "ticker": [], "open": [], "high": [], "low": [],
            "close": [], "volume": []}
    for t in range(fx["bars_large_tickers"]):
        tick = f"T{t:03d}"
        for d in dates:
            o = round(10.0 + (rng.random() * 90.0), 4)
            c = round(o + (rng.random() - 0.5) * 3.0, 4)
            hi = round(max(o, c) + rng.random() * 1.0, 4)
            lo = round(max(0.5, min(o, c) - rng.random() * 1.0), 4)
            rows["date"].append(d)
            rows["ticker"].append(tick)
            rows["open"].append(o)
            rows["high"].append(hi)
            rows["low"].append(lo)
            rows["close"].append(c)
            rows["volume"].append(int(10000 + rng.random() * 900000))
    pq_path = fixture_dir / "bars_large.parquet"
    pq_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_parquet(pq_path)
    digests["bars_large.parquet"] = _parquet_digests(pq_path)

    # events.jsonl
    out = []
    for i in range(fx["events_rows"]):
        out.append(json.dumps(
            {"date": dates[i % len(dates)],
             "ticker": f"T{i % fx['bars_large_tickers']:03d}",
             "kind": EVENT_KINDS[i % len(EVENT_KINDS)],
             "value": round(rng.random() * 10.0, 2)},
            sort_keys=True, separators=(",", ":")))
    data = _write_text(fixture_dir / "events.jsonl", "\n".join(out) + "\n")
    digests["events.jsonl"] = {"sha256": _sha256_bytes(data), "rows": len(out)}

    # nested/f000.csv .. f199.csv — 10 rows each.
    nested = fixture_dir / "nested"
    nested.mkdir(parents=True, exist_ok=True)
    ndates = _business_dates("2021-01-04", fx["nested_rows_per_file"])
    for i in range(fx["nested_files"]):
        lines = ["date,tag,score"]
        for d in ndates:
            tag = "".join(rng.choice(ALPHABET) for _ in range(8))
            lines.append(f"{d},{tag},{rng.random():.6f}")
        p = nested / f"f{i:03d}.csv"
        data = _write_text(p, "\n".join(lines) + "\n")
        digests[f"nested/f{i:03d}.csv"] = {
            "sha256": _sha256_bytes(data), "rows": fx["nested_rows_per_file"]}

    # wide.csv — 60 columns x 300 rows of 40-character strings.
    cols = [f"c{i:03d}" for i in range(fx["wide_columns"])]
    lines = [",".join(cols)]
    for _ in range(fx["wide_rows"]):
        cells = ["".join(rng.choice(ALPHABET) for _ in range(40))
                 for _ in cols]
        lines.append(",".join(cells))
    data = _write_text(fixture_dir / "wide.csv", "\n".join(lines) + "\n")
    digests["wide.csv"] = {"sha256": _sha256_bytes(data), "rows": fx["wide_rows"]}

    return digests


def _parquet_digests(pq_path: Path) -> dict:
    """LOGICAL digest (canonical text of the table) + physical digest/version.

    Physical parquet bytes depend on the pyarrow version; the logical digest is
    over the values actually read back, so it is the frozen one.
    """
    import pyarrow as pa
    import pyarrow.parquet as pq
    table = pq.read_table(pq_path)
    parts = []
    for row in table.to_pylist():
        parts.append("|".join([
            str(row["date"]), str(row["ticker"]), repr(row["open"]),
            repr(row["high"]), repr(row["low"]), repr(row["close"]),
            str(row["volume"])]))
    text = "\n".join(parts) + "\n"
    return {"logical_sha256": _sha256_bytes(text.encode("utf-8")),
            "physical_sha256": _sha256_bytes(pq_path.read_bytes()),
            "physical_pyarrow_version": pa.__version__,
            "rows": table.num_rows}


def verify_fixture(fixture_dir: Path, spec: dict) -> dict:
    """Regenerate-and-compare: raise SystemExit on any drift from the spec."""
    got = generate_fixture(fixture_dir, spec)
    want = spec["fixture"]["files"]
    bad = []
    for name, expect in want.items():
        g = got.get(name)
        if g is None:
            bad.append(f"{name}: missing")
            continue
        for key in ("sha256", "rows", "logical_sha256"):
            if key in expect and g.get(key) != expect[key]:
                bad.append(f"{name}.{key}: {g.get(key)!r} != {expect[key]!r}")
    if bad:
        raise SystemExit("fixture drift vs frozen spec:\n  " + "\n  ".join(bad))
    return got


# ─────────────────────────── response canonicalisation ───────────────────────

def strip_volatile(obj):
    if isinstance(obj, dict):
        return {k: strip_volatile(v) for k, v in obj.items()
                if k not in VOLATILE_KEYS}
    if isinstance(obj, list):
        return [strip_volatile(v) for v in obj]
    return obj


def result_digest(result: dict) -> str:
    canon = json.dumps(strip_volatile(result), sort_keys=True,
                       separators=(",", ":"), ensure_ascii=False)
    return _sha256_bytes(canon.encode("utf-8"))


def response_bytes(result: dict) -> int:
    return len(json.dumps(result, separators=(",", ":"),
                          ensure_ascii=False).encode("utf-8"))


def extract_shape(result) -> tuple:
    """(rows, columns, scanned_rows) — the Q03.02 members/fields observables."""
    if not isinstance(result, dict):
        return (None, None, None)
    action = result.get("action")
    if action == "read":
        body = result.get("result") or {}
        rows = body.get("rows") or []
        cols = sorted(rows[0]) if rows else sorted(
            (result.get("query") or {}).get("columns") or [])
        return (len(rows), cols, body.get("scanned_rows"))
    if action == "browse":
        return (result.get("entries_observed"), None, None)
    if action == "search":
        return (result.get("matches_observed"), None, None)
    if action == "describe_contract":
        contract = result.get("contract") or {}
        return (len(contract), sorted(contract.get("schema") or {}), None)
    if action == "describe_file":
        details = result.get("details") or {}
        return (details.get("row_count"), details.get("columns"), None)
    return (None, None, None)


# ─────────────────────────── driver-side instruments ─────────────────────────

class Instruments:
    """The audit hook + /proc/self/io fd + tracemalloc, one per driver.

    ``snapshot(reset_peak=True)`` is taken BEFORE each measured call so the
    ``tm_peak`` read after it is that call's own Python-heap peak.
    """

    def __init__(self) -> None:
        self.counters: dict[str, int] = {ev: 0 for ev in AUDIT_EVENTS}
        seen = frozenset(AUDIT_EVENTS)

        def hook(event, args):
            if event in seen:
                self.counters[event] += 1

        sys.addaudithook(hook)
        self._io_fd = os.open("/proc/self/io", os.O_RDONLY)
        tracemalloc.start()

    def snapshot(self, reset_peak: bool = False) -> dict:
        if reset_peak:
            tracemalloc.reset_peak()
        cur, peak = tracemalloc.get_traced_memory()
        return {"counters": dict(self.counters),
                "syscr": self._syscr(), "rchar": self._rchar(),
                "tm_current": cur, "tm_peak": peak,
                "threads": threading.active_count()}

    def _io_text(self) -> str:
        return os.pread(self._io_fd, 8192, 0).decode("ascii", "replace")

    def _syscr(self) -> int:
        for line in self._io_text().splitlines():
            if line.startswith("syscr:"):
                return int(line.split()[1])
        return -1

    def _rchar(self) -> int:
        for line in self._io_text().splitlines():
            if line.startswith("rchar:"):
                return int(line.split()[1])
        return -1


def pa_allocated():
    if "pyarrow" not in sys.modules:
        return None
    import pyarrow
    return pyarrow.total_allocated_bytes()


def snap_with_pa(instruments: Instruments, reset_peak: bool = False) -> dict:
    s = instruments.snapshot(reset_peak=reset_peak)
    s["pa"] = pa_allocated()
    return s


def _delta(after: dict, before: dict) -> dict:
    return {
        "counters": {ev: after["counters"][ev] - before["counters"][ev]
                     for ev in AUDIT_EVENTS},
        "syscr": after["syscr"] - before["syscr"],
        "rchar": after["rchar"] - before["rchar"],
        "tm_peak": after["tm_peak"],
        "tm_current_delta": after["tm_current"] - before["tm_current"],
        "pa_delta": ((after["pa"] - before["pa"])
                     if after["pa"] is not None and before["pa"] is not None
                     else None),
        "threads_before": before["threads"],
        "threads_after": after["threads"],
    }


def timed_request(dispatch, workspace, request: dict, cfg_path, instruments):
    """One measured request; every field is A/B-comparable."""
    before = snap_with_pa(instruments, reset_peak=True)
    t0 = time.perf_counter_ns()
    ok, refusal, error, result = False, None, None, None
    try:
        result = dispatch(workspace, request, config_path=cfg_path)
        ok = True
    except Exception as exc:  # WorkspaceError carries .code; others are errors
        refusal = getattr(exc, "code", None)
        error = None if refusal is not None else type(exc).__name__
    latency_ms = (time.perf_counter_ns() - t0) / 1e6
    after = snap_with_pa(instruments)
    sample = _delta(after, before)
    sample.update({"ok": ok, "refusal": refusal, "error": error,
                   "latency_ms": latency_ms,
                   "response_bytes": (response_bytes(result)
                                      if result is not None else None),
                   "digest": (result_digest(result)
                              if result is not None else None)})
    rows, columns, scanned = extract_shape(result)
    sample.update({"rows": rows, "columns": columns, "scanned": scanned})
    return sample


# ─────────────────────────── drivers (child processes) ───────────────────────

def _insert_repo(repo: Path, modules: list[str]) -> dict:
    """sys.path[0] isolation + the recorded assertion line."""
    sys.path.insert(0, str(repo))
    t0 = time.perf_counter_ns()
    import importlib
    loaded = [importlib.import_module(m) for m in modules]
    import_ms = (time.perf_counter_ns() - t0) / 1e6
    ws_file = Path(loaded[0].__file__).resolve()
    repo_r = repo.resolve()
    if repo_r not in ws_file.parents:
        sys.stderr.write(
            f"IMPORT-ISOLATION-FAILURE {ws_file} not under {repo_r}\n")
        raise SystemExit(3)
    return {"import_ms": import_ms,
            "isolation": (f"assert lib.dataos.web_workspace.__file__ "
                          f"{ws_file.relative_to(repo_r)} under repo "
                          f"{repo_r.name}: OK")}


def driver_inproc(args) -> None:
    import resource
    repo = Path(args.repo)
    info = _insert_repo(repo, ["lib.dataos.web_workspace", "lib.dataos.web_api"])
    import lib.dataos.web_api as api
    import lib.dataos.web_workspace as wsm
    instruments = Instruments()
    cfg_path = Path(args.cfg)

    before = snap_with_pa(instruments, reset_peak=True)
    t0 = time.perf_counter_ns()
    workspace = wsm.load_workspace_config(cfg_path, source_revision="q03-bench")
    construction_ms = (time.perf_counter_ns() - t0) / 1e6
    after = snap_with_pa(instruments)
    construction = _delta(after, before)
    construction["ms"] = construction_ms

    spec = json.loads(Path(args.spec).read_text(encoding="utf-8"))
    requests = [spec["requests"][rid] for rid in REQUEST_ORDER]
    samples_by_pass: dict[str, dict] = {}
    for pass_name in ("cold", "warm1", "warm2"):
        per = {rid: timed_request(api.dispatch, workspace, request, cfg_path,
                                  instruments)
               for rid, request in zip(REQUEST_ORDER, requests)}
        samples_by_pass[pass_name] = per
    out = {"driver": "inproc", "commit": args.label,
           "round": int(args.round_idx), **info, "construction": construction,
           "passes": samples_by_pass,
           "end": {"ru_maxrss_kb": resource.getrusage(
               resource.RUSAGE_SELF).ru_maxrss,
               "threads": threading.active_count(),
               "loadavg": list(os.getloadavg())}}
    print(json.dumps(out, separators=(",", ":")))


def driver_regas(args) -> None:
    """as-shipped registry arm: construction + R2/R3, one cold pass."""
    import resource
    repo = Path(args.repo)
    info = _insert_repo(repo, ["lib.dataos.web_workspace", "lib.dataos.web_api"])
    import lib.dataos.web_api as api
    import lib.dataos.web_workspace as wsm
    instruments = Instruments()
    cfg_path = Path(args.cfg)
    before = snap_with_pa(instruments, reset_peak=True)
    t0 = time.perf_counter_ns()
    workspace = wsm.load_workspace_config(cfg_path, source_revision="q03-bench")
    construction_ms = (time.perf_counter_ns() - t0) / 1e6
    after = snap_with_pa(instruments)
    construction = _delta(after, before)
    construction["ms"] = construction_ms
    spec = json.loads(Path(args.spec).read_text(encoding="utf-8"))
    per = {rid: timed_request(api.dispatch, workspace,
                              spec["requests"][rid], cfg_path, instruments)
           for rid in ("R2", "R3")}
    print(json.dumps({"driver": "regas", "commit": args.label,
                      "round": int(args.round_idx), **info,
                      "construction": construction,
                      "passes": {"cold": per},
                      "end": {"ru_maxrss_kb": resource.getrusage(
                          resource.RUSAGE_SELF).ru_maxrss,
                          "threads": threading.active_count()}},
                     separators=(",", ":")))


def driver_basket(args) -> None:
    """C_basket: the unchanged PIT membership reader over a synthetic store."""
    repo = Path(args.repo)
    sys.path.insert(0, str(repo))
    t0 = time.perf_counter_ns()
    import engine.basket_membership_pit as pit
    from lib import config
    import_ms = (time.perf_counter_ns() - t0) / 1e6
    root = Path(args.scratch)
    root.mkdir(parents=True, exist_ok=True)
    # The tests/test_basket_membership_pit.py redirect idiom.
    config.data_dir = lambda: root
    instruments = Instruments()

    def members(ticker, added="2021-06-15", removed=None):
        return {"ticker": ticker, "added": added, "removed": removed,
                "name_zh": f"zh-{ticker}", "rationale": "q03"}

    doc1 = {"version": 1, "seed_date": "2021-06-15", "curated": False,
            "baskets": {
                "bench_ai": {"name": "BENCH_AI", "name_zh": "bench_ai",
                             "category": "theme",
                             "members": [members(f"S{i:04d}.SZ")
                                         for i in range(BASKET_MEMBERS)]},
                "bench_chip": {"name": "BENCH_CHIP", "name_zh": "bench_chip",
                               "category": "theme",
                               "members": [members(f"C{i:04d}.SS")
                                           for i in range(BASKET_MEMBERS_2)]}}}
    p = root / pit.SUITE_THS / "membership.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(doc1, ensure_ascii=False), encoding="utf-8")
    seeds = {}
    t0 = time.perf_counter_ns()
    seeds["snap1"] = pit.append_snapshot(pit.SUITE_THS, asof="2026-07-08",
                                         lane="asia")
    seeds["snap1_ms"] = (time.perf_counter_ns() - t0) / 1e6
    # snapshot 2: a REAL membership change — 5 members carry removed dates
    # (absence from a later snapshot is not a removal in this store's model).
    doc2 = json.loads(json.dumps(doc1))
    for row in doc2["baskets"]["bench_ai"]["members"][-5:]:
        row["removed"] = "2026-07-15"
    p.write_text(json.dumps(doc2, ensure_ascii=False), encoding="utf-8")
    t0 = time.perf_counter_ns()
    seeds["snap2"] = pit.append_snapshot(pit.SUITE_THS, asof="2026-07-15",
                                         lane="asia")
    seeds["snap2_ms"] = (time.perf_counter_ns() - t0) / 1e6

    def call(fn, *a, **kw):
        before = snap_with_pa(instruments, reset_peak=True)
        t0 = time.perf_counter_ns()
        error = None
        try:
            result = fn(*a, **kw)
        except Exception as exc:
            error = type(exc).__name__
            result = None
        latency_ms = (time.perf_counter_ns() - t0) / 1e6
        after = snap_with_pa(instruments)
        sample = _delta(after, before)
        sample.update({"ok": error is None, "error": error,
                       "latency_ms": latency_ms})
        return sample, result

    samples = {"asof_pit": [], "asof_before_coverage": [], "coverage": []}
    for _ in range(5):
        s, r = call(pit.members_asof, "bench_ai", "2026-07-20",
                    suite=pit.SUITE_THS)
        s.update({"rows": len(r["members"]), "pit": r["pit"], "refusal": None,
                  "response_bytes": None, "digest": None})
        samples["asof_pit"].append(s)
        s, r = call(pit.members_asof, "bench_ai", "2026-01-01",
                    suite=pit.SUITE_THS)
        s.update({"rows": len(r["members"]), "pit": r["pit"], "refusal": None,
                  "response_bytes": None, "digest": None})
        samples["asof_before_coverage"].append(s)
        s, r = call(pit.coverage, pit.SUITE_THS)
        s.update({"rows": r["rows"], "snapshots": r["snapshots"],
                  "refusal": None, "response_bytes": None, "digest": None})
        samples["coverage"].append(s)
    print(json.dumps({"driver": "basket", "commit": args.label,
                      "round": int(args.round_idx),
                      "isolation": (f"engine.basket_membership_pit imported "
                                    f"from repo {repo.resolve().name}"),
                      "import_ms": import_ms, "seeds": seeds,
                      "samples": samples}, separators=(",", ":")))


def driver_newpath(args) -> None:
    """B_newpath (main only; no baseline): the C01 seam + account_coverage."""
    repo = Path(args.repo)
    sys.path.insert(0, str(repo))
    t0 = time.perf_counter_ns()
    import pandas as pd
    import engine.price_ladder as pl
    from lib.dataos.read_contract import (ReadMode, ReadRequest, ViewContract,
                                          Disposition, MemberDisposition,
                                          SourceSegment, account_coverage)
    import_ms = (time.perf_counter_ns() - t0) / 1e6
    store = Path(args.scratch) / "store"
    stocks = store / "stocks"
    stocks.mkdir(parents=True, exist_ok=True)
    idx = pd.bdate_range("2026-06-01", periods=30)
    base = pd.Series([100.0 + i for i in range(30)], index=idx)
    n_tickers = 50
    for t in range(n_tickers):
        s = base + (t * 0.01)
        pd.DataFrame({"close": s.values}, index=s.index).to_parquet(
            stocks / f"T{t:03d}.parquet")

    def view(mode=ReadMode.CURRENT, **kw):
        contract = ViewContract(
            purpose="q03_bench", field_units={},
            identity={"security_id": "SEC:US-XNYS-T000",
                      "listing_id": "US-XNYS-T000"},
            adjustment_reference={"basis": "tradj"}, coverage="requested")
        return ReadRequest(mode=mode, contract=contract, **kw)

    instruments = Instruments()

    def call(fn, *a, **kw):
        before = snap_with_pa(instruments, reset_peak=True)
        t0 = time.perf_counter_ns()
        error = None
        try:
            result = fn(*a, **kw)
        except Exception as exc:
            error = type(exc).__name__
            result = None
        latency_ms = (time.perf_counter_ns() - t0) / 1e6
        after = snap_with_pa(instruments)
        sample = _delta(after, before)
        sample.update({"ok": error is None, "error": error,
                       "latency_ms": latency_ms})
        return sample, result

    def decorate(sample, result):
        sample.update({
            "ok_call": bool(result.ok),
            "rows": (len(result.values) if result.values else 0),
            "refusal": (result.contract.refusal_reasons[0]
                        if result.contract.refusal_reasons else None),
            "response_bytes": None, "digest": None})
        return sample

    first_s, first_r = call(pl.resolve_close_canonical, "T000",
                            view=view(), data_dir=str(store))
    decorate(first_s, first_r)
    current = []
    for t in range(n_tickers):
        s, r = call(pl.resolve_close_canonical, f"T{t:03d}", view=view(),
                    data_dir=str(store))
        current.append(decorate(s, r))
    replay = []
    for _ in range(20):
        s, r = call(pl.resolve_close_canonical, "T000",
                    view=view(ReadMode.REPLAY, output_id="out-1"),
                    data_dir=str(store))
        replay.append(decorate(s, r))

    population = [f"US-XNYS-M{i:03d}" for i in range(500)]
    dispositions = [MemberDisposition(
        m, Disposition.SERVED,
        segments=(SourceSegment("bench_vendor", "tradj", m),))
        for m in population]
    cov_contract = ViewContract(
        purpose="q03_bench", field_units={},
        identity={"security_id": "SEC:US-XNYS-T000",
                  "listing_id": "US-XNYS-T000"},
        adjustment_reference={"basis": "tradj"}, coverage="requested")
    coverage = []
    for _ in range(5):
        s, r = call(account_coverage, cov_contract, population, dispositions)
        s.update({"ok_call": True, "rows": r.requested,
                  "qualified": len(r.qualified), "refusal": None,
                  "response_bytes": None, "digest": None})
        coverage.append(s)
    print(json.dumps({"driver": "newpath", "commit": args.label,
                      "round": int(args.round_idx),
                      "isolation": (f"engine.price_ladder imported from repo "
                                    f"{repo.resolve().name}"),
                      "import_ms": import_ms,
                      "first": first_s, "current": current, "replay": replay,
                      "coverage": coverage}, separators=(",", ":")))


# ─────────────────────────── MAX_* extraction (ast, no import) ───────────────

def extract_max_literals(source: str) -> dict[str, int]:
    """Module-level MAX_* names and their literal values, via ast only."""
    out: dict[str, int] = {}
    tree = ast.parse(source)
    for node in ast.walk(tree):
        targets = []
        value = None
        if isinstance(node, ast.Assign):
            targets = node.targets
            value = node.value
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            targets = [node.target]
            value = node.value
        for target in targets:
            if (isinstance(target, ast.Name) and target.id.startswith("MAX_")
                    and value is not None):
                try:
                    out[target.id] = ast.literal_eval(value)
                except (ValueError, TypeError):
                    pass
    return dict(sorted(out.items()))


def _ensure_commit(repo: Path, sha: str) -> None:
    """A spec-pinned commit is a landed `origin/main` ancestor, but the CI pack checkout is
    `fetch-depth: 1`, so it can be absent locally. Fetch it BLOBLESS: a depth-1 fetch by SHA
    without an object filter ships the commit's whole tree (data/ + site/, gigabytes) and
    overran the smoke fixture's 120 s budget on ubuntu (run 39031759012); with
    `--filter=blob:none` only the commit and its trees travel, and the one `git show` blob
    is fetched lazily by the promisor remote git registers for the filtered fetch. A full
    clone answers the probe and never reaches the fetch."""
    probe = subprocess.run(["git", "-C", str(repo), "cat-file", "-e", f"{sha}^{{commit}}"],
                           capture_output=True, text=True, timeout=30)
    if probe.returncode == 0:
        return
    subprocess.run(["git", "-C", str(repo), "fetch", "--quiet", "--depth=1",
                    "--filter=blob:none", "origin", sha],
                   check=True, capture_output=True, text=True, timeout=300)


def git_show(repo: Path, sha: str, path: str) -> str:
    _ensure_commit(repo, sha)
    proc = subprocess.run(["git", "-C", str(repo), "show", f"{sha}:{path}"],
                          check=True, capture_output=True, text=True, timeout=30)
    return proc.stdout


# ─────────────────────────── statistics + detection rule ─────────────────────

def p90(values: list) -> float:
    data = sorted(values)
    if not data:
        return float("nan")
    return data[max(0, min(len(data) - 1, -(-9 * len(data) // 10) - 1))]


def stats(values: list) -> dict:
    if not values:
        return {"n": 0}
    return {"n": len(values), "median": statistics.median(values),
            "p90": p90(values), "min": min(values), "max": max(values)}


def latency_verdict(a: list, b: list) -> str:
    """Frozen rule: B regresses iff median(B) > max(A) AND > 1.10*median(A)."""
    if not a or not b:
        return "n/a"
    ma, mb = statistics.median(a), statistics.median(b)
    if mb > max(a) and mb > 1.10 * ma:
        return "REGRESSION"
    return "ok"


def compare_deterministic(arm: str, rid: str, a_samples: list,
                          b_samples: list, phase: str = "",
                          counters=("open", "listdir", "scandir", "popen",
                          "connect", "getaddrinfo", "syscr", "rchar")) -> list:
    """The frozen deterministic-counter rule (counts/bytes/digest/refusal/shape)."""
    gaps: list[dict] = []
    if not a_samples or not b_samples:
        return gaps
    event_of = {"listdir": "os.listdir", "scandir": "os.scandir",
                "popen": "subprocess.Popen", "connect": "socket.connect",
                "getaddrinfo": "socket.getaddrinfo"}

    def counter(sample, key):
        if key in ("syscr", "rchar"):
            return sample.get(key)
        return (sample.get("counters") or {}).get(event_of.get(key, key))

    for key in counters:
        a_vals = [counter(s, key) for s in a_samples if counter(s, key) is not None]
        b_vals = [counter(s, key) for s in b_samples if counter(s, key) is not None]
        if a_vals and b_vals and max(b_vals) > max(a_vals):
            gaps.append({"type": "REGRESSION", "arm": arm, "request": rid,
                         "metric": key, "phase": phase,
                         "detail": f"max(B)={max(b_vals)} > max(A)={max(a_vals)}"})
    a_rb = [s["response_bytes"] for s in a_samples
            if s.get("response_bytes") is not None]
    b_rb = [s["response_bytes"] for s in b_samples
            if s.get("response_bytes") is not None]
    if a_rb and b_rb and max(b_rb) > max(a_rb):
        gaps.append({"type": "REGRESSION", "arm": arm, "request": rid,
                     "metric": "response_bytes", "phase": phase,
                     "detail": f"max(B)={max(b_rb)} > max(A)={max(a_rb)}"})
    a_dg = {s.get("digest") for s in a_samples if s.get("digest")}
    b_dg = {s.get("digest") for s in b_samples if s.get("digest")}
    if a_dg and b_dg and a_dg != b_dg:
        gaps.append({"type": "CHANGE", "arm": arm, "request": rid,
                     "metric": "digest", "phase": phase,
                     "detail": "stripped digests differ"})
    a_rc = {str(s.get("refusal")) for s in a_samples}
    b_rc = {str(s.get("refusal")) for s in b_samples}
    if a_rc != b_rc:
        gaps.append({"type": "CHANGE", "arm": arm, "request": rid,
                     "metric": "refusal_code", "phase": phase,
                     "detail": f"A={sorted(a_rc)} B={sorted(b_rc)}"})
    a_rows = [s.get("rows") for s in a_samples if s.get("rows") is not None]
    b_rows = [s.get("rows") for s in b_samples if s.get("rows") is not None]
    if a_rows and b_rows and max(b_rows) < max(a_rows):
        gaps.append({"type": "Q03.02", "arm": arm, "request": rid,
                     "metric": "rows", "phase": phase,
                     "detail": f"max(B)={max(b_rows)} < max(A)={max(a_rows)}"})
    a_cols = next((s.get("columns") for s in a_samples if s.get("columns")),
                  None)
    b_cols = next((s.get("columns") for s in b_samples if s.get("columns")),
                  None)
    if a_cols and b_cols and set(b_cols) < set(a_cols):
        gaps.append({"type": "Q03.02", "arm": arm, "request": rid,
                     "metric": "columns", "phase": phase,
                     "detail": f"B dropped {sorted(set(a_cols) - set(b_cols))}"})
    return gaps


def background_gaps(arm: str, label: str, samples: list,
                    listing_budget=None) -> list:
    """Q03.04: no subprocess/socket, stable threads, listing discipline."""
    gaps = []
    for i, s in enumerate(samples):
        c = s.get("counters") or {}
        for ev in ("subprocess.Popen", "socket.connect", "socket.getaddrinfo"):
            if c.get(ev, 0) > 0:
                gaps.append({"type": "Q03.04", "arm": arm, "request": label,
                             "metric": ev,
                             "detail": f"sample {i}: {c.get(ev)} event(s)"})
        if s.get("threads_after") != s.get("threads_before"):
            gaps.append({"type": "Q03.04", "arm": arm, "request": label,
                         "metric": "threads",
                         "detail": (f"sample {i}: {s.get('threads_before')}"
                                    f" -> {s.get('threads_after')}")})
        if listing_budget is not None:
            listed = c.get("os.scandir", 0) + c.get("os.listdir", 0)
            if listed > listing_budget:
                gaps.append({"type": "Q03.04", "arm": arm, "request": label,
                             "metric": "directory_listings",
                             "detail": (f"sample {i}: {listed} listings > "
                                        f"{listing_budget} returned")})
    return gaps


def compact(sample: dict) -> dict:
    """The deterministic summary kept per (commit, pass) in the results file."""
    return {k: sample.get(k) for k in (
        "ok", "refusal", "error", "response_bytes", "digest", "rows",
        "columns", "scanned", "counters", "syscr", "rchar", "tm_peak",
        "tm_current_delta", "pa_delta", "threads_before", "threads_after")}


# ─────────────────────────── parent orchestration ────────────────────────────

def interleave(n_rounds: int) -> str:
    """Frozen interleave: 'ABBA' repeated, truncated to 2N (N=6 gives the
    mandated A B B A A B B A A B B A)."""
    return ("ABBA" * n_rounds)[:2 * n_rounds]


def run_driver(kind: str, repo: Path, label: str, round_idx: int,
               spec_path: Path, fixture_dir: Path, cfg,
               scratch_dir: Path, timeout: int = 900) -> dict:
    cmd = [sys.executable, "-B", str(Path(__file__).resolve()), "--driver",
           kind, "--repo", str(repo), "--label", label,
           "--round-idx", str(round_idx), "--spec", str(spec_path),
           "--fixture-dir", str(fixture_dir), "--cfg", str(cfg),
           "--scratch", str(scratch_dir)]
    proc = subprocess.run(cmd, capture_output=True, timeout=timeout, text=True)
    if proc.returncode != 0:
        tail = (proc.stderr or "").strip().splitlines()[-1:] or ["<no stderr>"]
        raise RuntimeError(f"driver {kind}/{label}/{round_idx} exit "
                           f"{proc.returncode}: {tail[0][:300]}")
    try:
        return json.loads(proc.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError) as exc:
        raise RuntimeError(f"driver {kind}/{label}/{round_idx} bad json: {exc}")


def write_binding_cfg(path: Path, fixture_dir: Path, registry_path: Path) -> None:
    cfg = {"schema_version": "mastermind.data_workspace_bindings/v1",
           "registry_path": str(registry_path),
           "roots": [
               {"alias": "fixture", "path": str(fixture_dir),
                "evidence_kind": "research_sample",
                "note": "q03-1 synthetic frozen fixture"},
               {"alias": "nested", "path": str(fixture_dir / "nested"),
                "evidence_kind": "research_sample",
                "note": "q03-1 synthetic nested fixture"}]}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cfg), encoding="utf-8")


def arm_a_inproc(spec, repos, spec_path, fixture_dir, scratch, rounds):
    cfg = scratch / "cfg_matched.json"
    order = interleave(rounds)
    drivers = []
    seen = {"A": 0, "B": 0}
    for label in order:
        seen[label] += 1
        drivers.append(run_driver("inproc", repos[label], label, seen[label],
                                  spec_path, fixture_dir, cfg,
                                  scratch / "inproc" / f"{label}{seen[label]}"))
    return drivers


def analyze_inproc(arm_name: str, drivers: list, passes,
                   requests=REQUEST_ORDER, retain_all=False) -> tuple:
    per_request: dict = {}
    gaps: list = []
    listing_budget = {"R2": 2, "R4": 1, "R5": 1}
    for rid in requests:
        blob: dict = {}
        for commit in ("A", "B"):
            blob[commit] = {}
            for phase in passes:
                samples = [d["passes"][phase][rid] for d in drivers
                           if d["commit"] == commit
                           and rid in d["passes"].get(phase, {})]
                blob[commit][phase] = {
                    "latency": stats([s["latency_ms"] for s in samples]),
                    "tm_peak": stats([s["tm_peak"] for s in samples
                                      if s.get("tm_peak") is not None]),
                    "first": compact(samples[0]) if samples else None}
                if retain_all:
                    blob[commit][phase]["all_samples"] = samples
        verdicts = {}
        for phase in passes:
            a = [d["passes"][phase][rid] for d in drivers
                 if d["commit"] == "A" and rid in d["passes"].get(phase, {})]
            b = [d["passes"][phase][rid] for d in drivers
                 if d["commit"] == "B" and rid in d["passes"].get(phase, {})]
            latency = latency_verdict(
                [s["latency_ms"] for s in a], [s["latency_ms"] for s in b])
            tm = latency_verdict(
                [s["tm_peak"] for s in a if s.get("tm_peak") is not None],
                [s["tm_peak"] for s in b if s.get("tm_peak") is not None])
            verdicts[phase] = {"latency": latency, "tm_peak": tm}
            for metric, verdict in (("latency", latency), ("tm_peak", tm)):
                if verdict == "REGRESSION":
                    gaps.append({"type": "REGRESSION", "arm": arm_name,
                                 "request": rid, "metric": f"{metric}:{phase}",
                                 "phase": phase,
                                 "detail": "median(B) > max(A) and > 1.10*median(A)"})
            gaps.extend(compare_deterministic(arm_name, rid, a, b,
                                              phase=phase))
            for commit in ("A", "B"):
                gaps.extend(background_gaps(
                    f"{arm_name}[{commit}]", rid,
                    [d["passes"][phase][rid] for d in drivers
                     if d["commit"] == commit
                     and rid in d["passes"].get(phase, {})],
                    listing_budget.get(rid)))
        blob["verdicts"] = verdicts
        per_request[rid] = blob
    construction = {}
    a_ms = [d["construction"]["ms"] for d in drivers if d["commit"] == "A"]
    b_ms = [d["construction"]["ms"] for d in drivers if d["commit"] == "B"]
    construction["verdict"] = latency_verdict(a_ms, b_ms)
    if construction["verdict"] == "REGRESSION":
        gaps.append({"type": "REGRESSION", "arm": arm_name,
                     "request": "construction", "metric": "latency",
                     "phase": "*",
                     "detail": "median(B) > max(A) and > 1.10*median(A)"})
    for commit, ms in (("A", a_ms), ("B", b_ms)):
        construction[commit] = {"stats": stats(ms)}
        construction[commit]["first"] = compact(
            next((d["construction"] for d in drivers if d["commit"] == commit),
                 {}))
    construction["import_ms"] = {
        "A": stats([d["import_ms"] for d in drivers if d["commit"] == "A"]),
        "B": stats([d["import_ms"] for d in drivers if d["commit"] == "B"]),
        "note": "informational: one-time module import cost per driver process"}
    return {"per_request": per_request, "construction": construction,
            "driver_ends": [{"commit": d["commit"], "round": d["round"],
                             "end": d["end"]} for d in drivers]}, gaps


def arm_a_cli(spec, repos, scratch, reps: int) -> tuple:
    cfg = str(scratch / "cfg_matched.json")
    results = {rid: {"A": [], "B": []} for rid in REQUEST_ORDER}
    for rep in range(1, reps + 1):
        order = ("A", "B") if rep % 2 == 1 else ("B", "A")
        for rid in REQUEST_ORDER:
            request = spec["requests"][rid]
            payload = json.dumps(request, separators=(",", ":"),
                                 ensure_ascii=False).encode("utf-8")
            for commit in order:
                script = repos[commit] / "scripts" / "data_workspace.py"
                t0 = time.perf_counter_ns()
                try:
                    proc = subprocess.run(
                        [sys.executable, "-B", str(script), "--config", cfg],
                        input=payload, capture_output=True, timeout=60)
                    wall_ms = (time.perf_counter_ns() - t0) / 1e6
                    out = proc.stdout.decode("utf-8", "replace").strip()
                    try:
                        parsed = json.loads(out)
                    except ValueError:
                        parsed = None
                    # exit 2 with a JSON body carrying "error" is the
                    # documented refusal shape, not an error sample.
                    refusal = (proc.returncode == 2
                               and isinstance(parsed, dict)
                               and isinstance(parsed.get("error"), str))
                    sample = {"wall_ms": wall_ms, "timeout": False,
                              "exit_code": proc.returncode,
                              "stdout_bytes": len(proc.stdout),
                              "rep": rep,
                              "response_bytes": (response_bytes(parsed)
                                                 if isinstance(parsed, dict)
                                                 else None),
                              "digest": (result_digest(parsed)
                                         if isinstance(parsed, dict) else None),
                              "error": (None if (proc.returncode == 0 or refusal)
                                        else "NONZERO_EXIT"),
                              "refusal": (parsed.get("error") if refusal
                                          else None)}
                except subprocess.TimeoutExpired:
                    sample = {"wall_ms": 60000.0, "timeout": True,
                              "exit_code": None, "stdout_bytes": None,
                              "rep": rep, "response_bytes": None,
                              "digest": None, "error": "TIMEOUT",
                              "refusal": None}
                results[rid][commit].append(sample)
    per_request = {}
    gaps: list = []
    for rid in REQUEST_ORDER:
        blob = {c: {"wall": stats([s["wall_ms"] for s in results[rid][c]]),
                    "exit_codes": sorted({s["exit_code"]
                                          for s in results[rid][c]}),
                    "samples": results[rid][c]} for c in ("A", "B")}
        verdict = latency_verdict(
            [s["wall_ms"] for s in results[rid]["A"]],
            [s["wall_ms"] for s in results[rid]["B"]])
        blob["verdict"] = verdict
        if verdict == "REGRESSION":
            gaps.append({"type": "REGRESSION", "arm": "A_cli", "request": rid,
                         "metric": "wall_latency", "phase": "*",
                         "detail": "median(B) > max(A) and > 1.10*median(A)"})
        a = [dict(s) for s in results[rid]["A"]]
        b = [dict(s) for s in results[rid]["B"]]
        gaps.extend(compare_deterministic("A_cli", rid, a, b, counters=()))
        per_request[rid] = blob
    note = ("_revision() spawns git subprocesses per CLI call at BOTH commits "
            "(pre-existing scripts/data_workspace.py behaviour; reported, not "
            "a regression).")
    return {"per_request": per_request, "note": note}, gaps


def arm_c_basket(spec, repos, spec_path, fixture_dir, scratch, drivers_n=5):
    drivers = []
    seen = {"A": 0, "B": 0}
    for label in interleave(drivers_n):
        seen[label] += 1
        drivers.append(run_driver("basket", repos[label], label, seen[label],
                                  spec_path, fixture_dir, scratch / "none",
                                  scratch / "basket" / f"{label}{seen[label]}"))
    per_call = {}
    gaps: list = []
    for call_name in ("asof_pit", "asof_before_coverage", "coverage"):
        blob = {}
        for commit in ("A", "B"):
            samples = [s for d in drivers if d["commit"] == commit
                       for s in d["samples"][call_name]]
            blob[commit] = {"latency": stats([s["latency_ms"] for s in samples]),
                            "first": compact(samples[0]) if samples else None}
        a = [s for d in drivers if d["commit"] == "A"
             for s in d["samples"][call_name]]
        b = [s for d in drivers if d["commit"] == "B"
             for s in d["samples"][call_name]]
        verdict = latency_verdict([s["latency_ms"] for s in a],
                                  [s["latency_ms"] for s in b])
        blob["verdict"] = verdict
        if verdict == "REGRESSION":
            gaps.append({"type": "REGRESSION", "arm": "C_basket",
                         "request": call_name, "metric": "latency",
                         "phase": "*", "detail": "median(B) > max(A) and > 1.10*median(A)"})
        gaps.extend(compare_deterministic("C_basket", call_name, a, b,
                                          counters=("syscr", "rchar")))
        for commit in ("A", "B"):
            gaps.extend(background_gaps(
                f"C_basket[{commit}]", call_name,
                [s for d in drivers if d["commit"] == commit
                 for s in d["samples"][call_name]]))
        per_call[call_name] = blob
    return {"per_call": per_call,
            "seeds": [{"commit": d["commit"], "round": d["round"],
                       "snap1_ms": d["seeds"]["snap1_ms"],
                       "snap2_ms": d["seeds"]["snap2_ms"],
                       "snap1": d["seeds"]["snap1"],
                       "snap2": d["seeds"]["snap2"]} for d in drivers]}, gaps


def arm_b_newpath(spec, repos, spec_path, fixture_dir, scratch, drivers_n=5):
    drivers = [run_driver("newpath", repos["B"], "B", i + 1, spec_path,
                          fixture_dir, scratch / "none",
                          scratch / "newpath" / f"B{i + 1}")
               for i in range(drivers_n)]
    blob = {}
    for key in ("current", "replay", "coverage"):
        samples = [s for d in drivers for s in d[key]]
        blob[key] = {"latency": stats([s["latency_ms"] for s in samples]),
                     "tm_peak": stats([s["tm_peak"] for s in samples]),
                     "ok_calls": sum(1 for s in samples if s.get("ok_call")),
                     "errors": sum(1 for s in samples if s.get("error")),
                     "refusals": sorted({str(s.get("refusal")) for s in samples
                                         if s.get("refusal")})}
    firsts = [{"latency_ms": d["first"]["latency_ms"],
               "ok_call": d["first"]["ok_call"],
               "refusal": d["first"]["refusal"],
               "rows": d["first"]["rows"]} for d in drivers]
    gaps: list = []
    for d in drivers:
        for key, samples in (("current", d["current"]),
                             ("replay", d["replay"]),
                             ("coverage", d["coverage"])):
            gaps.extend(background_gaps("B_newpath", key, samples))
    label = ("new path; no baseline; observed cost, not a regression comparison")
    return {"per_call": blob, "first_call_per_process": firsts,
            "import_ms": stats([d["import_ms"] for d in drivers]),
            "label": label}, gaps


def arm_limits(spec, repos) -> tuple:
    table = {}
    for commit, sha in (("A", spec["commits"]["A"]), ("B", spec["commits"]["B"])):
        table[commit] = {}
        for path in LIMITS_PATHS:
            table[commit][path] = extract_max_literals(
                git_show(repos["A"], sha, path))
    gaps: list = []
    for path in LIMITS_PATHS:
        if table["A"][path] != table["B"][path]:
            gaps.append({"type": "LIMITS", "arm": "limits", "request": path,
                         "metric": "MAX_* A vs B",
                         "detail": f"A={table['A'][path]} B={table['B'][path]}"})
        if table["B"][path] != spec["max_limits"].get(path):
            gaps.append({"type": "LIMITS", "arm": "limits", "request": path,
                         "metric": "spec drift",
                         "detail": "source MAX_* no longer equals frozen spec"})
    return table, gaps


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--spec", required=False)
    ap.add_argument("--repo-a", required=False)
    ap.add_argument("--repo-b", required=False)
    ap.add_argument("--fixture-dir", required=False)
    ap.add_argument("--out", required=False)
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--arms", default=None,
                    help="comma list from A_inproc,A_cli,C_basket,B_newpath,"
                         "reg_as_shipped,limits")
    ap.add_argument("--rounds", type=int, default=None)
    # internal driver mode (this same file spawns itself)
    ap.add_argument("--driver", default=None)
    ap.add_argument("--repo", default=None)
    ap.add_argument("--label", default=None)
    ap.add_argument("--round-idx", default="1")
    ap.add_argument("--cfg", default=None)
    ap.add_argument("--scratch", default=None)
    args = ap.parse_args()

    if args.driver:
        {"inproc": driver_inproc, "regas": driver_regas,
         "basket": driver_basket, "newpath": driver_newpath}[args.driver](args)
        return 0

    missing = [name for name in ("spec", "repo_a", "repo_b", "fixture_dir",
                                 "out") if not getattr(args, name)]
    if missing:
        raise SystemExit(f"missing required arguments: {missing}")
    spec_path = Path(args.spec).resolve()
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    if spec.get("spec_version") != SPEC_VERSION:
        raise SystemExit(f"spec_version mismatch: {spec.get('spec_version')}")
    fixture_dir = Path(args.fixture_dir).resolve()
    fixture_dir.mkdir(parents=True, exist_ok=True)
    scratch = fixture_dir.parent
    repos = {"A": Path(args.repo_a).resolve(), "B": Path(args.repo_b).resolve()}

    arms = (args.arms.split(",") if args.arms else
            (["A_inproc"] if args.smoke else
             ["A_inproc", "A_cli", "C_basket", "B_newpath", "reg_as_shipped",
              "limits"]))
    rounds = args.rounds if args.rounds is not None else (
        1 if args.smoke else spec["arms"]["A_inproc"]["rounds_per_commit"])

    verify_fixture(fixture_dir, spec)

    # matched registry: baseline YAML, verified against the spec's content hash
    registry_base = scratch / "registry_base.yml"
    if not registry_base.exists():
        registry_base.write_bytes(git_show(
            repos["A"], spec["commits"]["A"],
            "config/dataset_registry.yml").encode("utf-8"))
    got = _sha256_bytes(registry_base.read_bytes())
    if got != spec["fixture"]["registry_matched_sha256"]:
        raise SystemExit(f"registry_base.yml sha256 {got} != frozen spec")
    write_binding_cfg(scratch / "cfg_matched.json", fixture_dir, registry_base)
    write_binding_cfg(scratch / "cfg_asshipped_A.json", fixture_dir,
                      repos["A"] / "config" / "dataset_registry.yml")
    write_binding_cfg(scratch / "cfg_asshipped_B.json", fixture_dir,
                      repos["B"] / "config" / "dataset_registry.yml")

    results = {"bench_version": BENCH_VERSION, "spec_version": SPEC_VERSION,
               "run_id": spec["run_id"], "commits": spec["commits"],
               "smoke": bool(args.smoke), "rounds": rounds, "arms_run": arms,
               "host": {"py": sys.version.split()[0],
                        "cpu_count": os.cpu_count(),
                        "load_start": list(os.getloadavg())},
               "fixture_top_level": sorted(
                   p.name for p in fixture_dir.iterdir() if p.is_file())}
    gaps: list = []
    sample_total = 0
    error_total = 0
    timeout_total = 0

    for arm in arms:
        if arm == "A_inproc":
            drivers = arm_a_inproc(spec, repos, spec_path, fixture_dir, scratch,
                                   rounds)
            analysis, g = analyze_inproc("A_inproc", drivers,
                                         ("cold", "warm1", "warm2"),
                                         retain_all=args.smoke)
            analysis["interleave"] = interleave(rounds)
            analysis["isolation"] = {
                c: next(d["isolation"] for d in drivers if d["commit"] == c)
                for c in ("A", "B")}
            results["A_inproc"] = analysis
            for d in drivers:
                for phase in d["passes"]:
                    sample_total += len(d["passes"][phase])
                    error_total += sum(1 for s in d["passes"][phase].values()
                                       if s.get("error"))
        elif arm == "A_cli":
            reps = 2 if args.smoke else spec["arms"]["A_cli"]["reps"]
            analysis, g = arm_a_cli(spec, repos, scratch, reps)
            analysis["reps"] = reps
            results["A_cli"] = analysis
            for rid in REQUEST_ORDER:
                for c in ("A", "B"):
                    samples = analysis["per_request"][rid][c]["samples"]
                    sample_total += len(samples)
                    error_total += sum(1 for s in samples if s.get("error"))
                    timeout_total += sum(1 for s in samples if s.get("timeout"))
        elif arm == "C_basket":
            n = spec["arms"]["C_basket"]["drivers_per_commit"]
            analysis, g = arm_c_basket(spec, repos, spec_path, fixture_dir,
                                       scratch, n)
            results["C_basket"] = analysis
            sample_total += 15 * 2 * n
        elif arm == "B_newpath":
            n = spec["arms"]["B_newpath"]["drivers"]
            analysis, g = arm_b_newpath(spec, repos, spec_path, fixture_dir,
                                        scratch, n)
            results["B_newpath"] = analysis
            for key in ("current", "replay", "coverage"):
                sample_total += analysis["per_call"][key]["latency"]["n"]
                error_total += analysis["per_call"][key]["errors"]
            sample_total += n  # first calls
        elif arm == "reg_as_shipped":
            n = spec["arms"]["reg_as_shipped"]["drivers_per_commit"]
            seen = {"A": 0, "B": 0}
            drivers = []
            for label in interleave(n):
                seen[label] += 1
                cfg = scratch / f"cfg_asshipped_{label}.json"
                drivers.append(run_driver(
                    "regas", repos[label], label, seen[label], spec_path,
                    fixture_dir, cfg,
                    scratch / "regas" / f"{label}{seen[label]}"))
            analysis, _g = analyze_inproc("reg_as_shipped", drivers, ("cold",),
                                          requests=("R2", "R3"))
            analysis["note"] = ("as-shipped registry per commit; reported, "
                                "not judged under the paired rule")
            analysis["isolation"] = {
                c: next(d["isolation"] for d in drivers if d["commit"] == c)
                for c in ("A", "B")}
            results["reg_as_shipped"] = analysis
            g = []
            for d in drivers:
                for phase in d["passes"]:
                    sample_total += len(d["passes"][phase])
        elif arm == "limits":
            table, g = arm_limits(spec, repos)
            results["limits"] = table
        else:
            raise SystemExit(f"unknown arm {arm}")
        gaps.extend(g)
        results["host"][f"load_after_{arm}"] = list(os.getloadavg())

    results["host"]["load_end"] = list(os.getloadavg())
    collapsed: dict = {}
    for gap in gaps:
        key = (gap.get("type"), gap.get("arm"), gap.get("request"),
               gap.get("metric"), gap.get("detail"))
        if key in collapsed:
            if gap.get("phase"):
                phases = collapsed[key].setdefault("phases", [collapsed[key].get("phase")])
                if gap["phase"] not in phases:
                    phases.append(gap["phase"])
        else:
            collapsed[key] = gap
    gaps = list(collapsed.values())
    results["gaps"] = gaps
    counts: dict = {}
    for gap in gaps:
        counts[gap["type"]] = counts.get(gap["type"], 0) + 1
    results["gap_counts"] = counts
    results["totals"] = {"samples": sample_total, "errors": error_total,
                         "timeouts": timeout_total}
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(results, indent=1), encoding="utf-8")
    print(f"arms={','.join(arms)} samples={sample_total} "
          f"errors={error_total} timeouts={timeout_total} "
          f"regression_gaps={counts.get('REGRESSION', 0)}"
          f"+{counts.get('Q03.02', 0)}q02+{counts.get('Q03.04', 0)}q04"
          f"+{counts.get('LIMITS', 0)}lim "
          f"change_gaps={counts.get('CHANGE', 0)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
