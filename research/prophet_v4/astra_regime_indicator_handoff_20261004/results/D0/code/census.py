#!/usr/bin/env python3
"""D0 census: point-in-time theme membership for the B1 stock universe.

Reproduces every number in result.json and RESULT.md. Run from the repo root:

    python3 research/prophet_v4/astra_regime_indicator_handoff_20261004/results/D0/code/census.py

No writes outside RESULTS_DIR. No returns, no hypothesis, no indicator.
RESULT.md is rendered from the just-written result.json. main() then runs pytest,
folds the summary, re-renders, and write_hashes last. gh api is used only for
write-time commit cites (H4); everything else is offline.
"""
from __future__ import annotations

import hashlib
import inspect
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
from collections import defaultdict
from datetime import date
from functools import lru_cache
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

YEARS = [str(y) for y in range(2014, 2027)]
PIT_CLASSES = ("PIT_HONEST", "BACKFILLED", "UNDECIDABLE")
VERDICTS = ("PIT_AVAILABLE", "PIT_PARTIAL", "PIT_UNAVAILABLE")
MIN_ROWS = 800
LEADING_LABELS = {"dominant", "emerging"}
CONTEXT_HISTORY_FIRST_WRITE = "2026-07-19"
ROUND1_RESULT_SHA256 = "6ed2c8799dc622f76662b1c6c352be47c08ab9ec7746c0ef5f8ddafb893bcf18"
ROUND2_RESULT_SHA256 = "c4b0241f5622656e7bb79cc9e6080a895f5a503c57b8b20fca67c859119ddd61"
GH_EVIDENCE_NAME = "gh_evidence.json"
RERUN_NOTICE = (
    "This round was first launched on host mini2 at 05:21Z as remote_sub id "
    "rs_20261004T051657Z_81412 (lease b6face03ca9a); that host lost ssh access "
    "fleet-wide and the carrier concluded `DONE rc=124 signal=effect_unknown "
    "reason=transport_deadline_without_rc` with its remote artifacts preserved "
    "but unreachable. This run on the seat host m2 is the RECORD of D0 round 3; "
    "the mini2 artifacts, if ever recovered, are a cross-host reproduction check only."
)
FROZEN_LEAVES = {
    "honest_window.start": "2026-07-05",
    "honest_window.end": "2026-10-03",
    "change_points.2026-07-05": 660,
    "change_points.2026-08-13": 933,
    "change_points.2026-08-15": 932,
    "change_points.2026-08-18": 931,
    "change_points.2026-09-04": 932,
    "change_points.2026-10-03": 932,
    "leading_restricted.min_n": 29,
    "leading_restricted.min_coverage": 0.011175,
    "leading_restricted.min_date": "2026-09-16",
    "leading_restricted.max_n": 307,
    "leading_restricted.max_coverage": 0.118304,
    "leading_restricted.max_date": "2026-08-24",
    "any_theme_union_ever": 0.359923,
}

HONEST_WINDOW_RULE = (
    "D* is the earliest date on which a PIT_HONEST ticker-theme membership "
    "observation exists, using each source's honest clock only "
    "(tree_history.asof; membership_history.snapshot_date). "
    "edges.parquet sub-sources are all BACKFILLED on the observed clock "
    "(evidence_time or valid_from precedes belief_time, or date_provenance="
    "seed_constant), so they do not set D*. "
    "D* = min(tree_history.asof min, membership_history.snapshot_date min). "
    "E* (honest window end) is data/theme_graph/_meta.json belief_time "
    "(as-observed-today bound). "
    "Per-date coverage on D is the union of universe names in force from any "
    "PIT_HONEST membership tape whose last snapshot/asof is <= D "
    "(carry-forward; stepwise constant between change-points). "
    "PIT_AVAILABLE iff min coverage(D) for D in [D*, E*] >= 0.50. "
    "union_max_ever is reported alongside and is NOT the grading rule."
)


def find_root() -> Path:
    here = Path(__file__).resolve()
    for p in [Path.cwd(), *here.parents]:
        if (p / "data" / "baskets" / "ohlcv").is_dir() and (p / "engine").is_dir():
            return p
    raise SystemExit("cannot locate repo root (data/baskets/ohlcv missing)")


def results_dir(root: Path) -> Path:
    return root / "research/prophet_v4/astra_regime_indicator_handoff_20261004/results/D0"


def cite_function(fn) -> dict:
    """Write-time file:line from inspect.getsourcelines (I4)."""
    _lines, start = inspect.getsourcelines(fn)
    return {
        "file": "census.py",
        "line": int(start),
        "symbol": fn.__name__,
        "where": f"census.py:{start} {fn.__name__}",
    }


def cite_assign(name: str) -> dict:
    src = Path(__file__).read_text(encoding="utf-8").splitlines()
    needle = f"{name} ="
    for i, line in enumerate(src, 1):
        if line.startswith(needle) or line.startswith(f"{name}="):
            return {
                "file": "census.py",
                "line": i,
                "symbol": name,
                "where": f"census.py:{i} {name}",
                "text": line.rstrip(),
            }
    raise ValueError(f"assignment {name!r} not found")


def cite_test(fn_name: str) -> dict:
    test_path = Path(__file__).resolve().parent / "test_d0.py"
    src = test_path.read_text(encoding="utf-8").splitlines()
    needle = f"def {fn_name}("
    for i, line in enumerate(src, 1):
        if needle in line:
            return {
                "file": "test_d0.py",
                "line": i,
                "symbol": fn_name,
                "where": f"test_d0.py:{i} {fn_name}",
            }
    raise ValueError(f"test {fn_name!r} not found")


def format_cites(*parts: dict | str) -> str:
    bits = []
    for p in parts:
        if isinstance(p, dict):
            bits.append(p["where"])
        else:
            bits.append(str(p))
    return "; ".join(bits)


def leaf_paths(obj, prefix: str = ""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            key = f"{prefix}.{k}" if prefix else str(k)
            yield from leaf_paths(v, key)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from leaf_paths(v, f"{prefix}[{i}]")
    else:
        yield prefix, obj


def _leaf_clip(v, n: int = 160):
    if isinstance(v, str) and len(v) > n:
        return v[:n] + "…"
    return v


def leaf_diff(old, new) -> dict:
    """I8: code-emitted leaf diff; never a typed key list."""
    a = dict(leaf_paths(old))
    b = dict(leaf_paths(new))
    added = sorted(set(b) - set(a))
    removed = sorted(set(a) - set(b))
    changed = []
    numeric_changed = []
    label_changed = []
    for k in sorted(set(a) & set(b)):
        if a[k] != b[k]:
            rec = {"path": k, "from": _leaf_clip(a[k]), "to": _leaf_clip(b[k])}
            changed.append(rec)
            if isinstance(a[k], (int, float)) and isinstance(b[k], (int, float)):
                numeric_changed.append(rec)
            else:
                label_changed.append(rec)
    cap = 80
    return {
        "n_added": len(added),
        "n_removed": len(removed),
        "n_changed": len(changed),
        "n_numeric_changed": len(numeric_changed),
        "n_label_changed": len(label_changed),
        "added": added[:cap],
        "removed": removed[:cap],
        "changed_paths": [c["path"] for c in changed][:cap],
        "numeric_changed": numeric_changed,
        "label_changed_paths": [c["path"] for c in label_changed][:cap],
        "truncated": any(n > cap for n in (len(added), len(removed), len(changed), len(label_changed))),
    }


def gh_evidence_path(root: Path) -> Path:
    return results_dir(root) / GH_EVIDENCE_NAME


def load_gh_evidence(root: Path) -> dict | None:
    path = gh_evidence_path(root)
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def git_head_committer_date(root: Path) -> str | None:
    proc = subprocess.run(
        ["git", "log", "-1", "--format=%cI", "HEAD"],
        cwd=root,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        return None
    return (proc.stdout or "").strip() or None


def fetch_gh_path_commits(rel: str, per_page: int, until: str) -> dict:
    endpoint = (
        "repos/mastermindx-market-intelligence/macro/commits"
        f"?path={rel}&per_page={per_page}&until={until}"
    )
    env = dict(os.environ)
    env["NO_COLOR"] = "1"
    env["CLICOLOR"] = "0"
    env["GH_FORCE_TTY"] = "0"
    try:
        proc = subprocess.run(
            ["gh", "api", endpoint, "--jq", "."],
            capture_output=True,
            text=True,
            timeout=90,
            env=env,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return {
            "key": None,
            "path": rel,
            "endpoint": endpoint,
            "per_page": per_page,
            "until": until,
            "ok": False,
            "rc": None,
            "stderr": str(exc),
            "commits": [],
            "n_commits": 0,
        }
    rec = {
        "key": None,
        "path": rel,
        "endpoint": endpoint,
        "per_page": per_page,
        "until": until,
        "ok": proc.returncode == 0,
        "rc": proc.returncode,
        "stderr": (proc.stderr or "")[:500],
        "commits": [],
        "n_commits": 0,
    }
    if proc.returncode == 0 and (proc.stdout or "").strip():
        raw = json.loads(proc.stdout)
        rec["commits"] = [
            {
                "sha": str(item.get("sha") or "")[:12],
                "sha_full": str(item.get("sha") or ""),
                "date": ((item.get("commit") or {}).get("committer") or {}).get("date"),
                "msg": str(((item.get("commit") or {}).get("message") or "")).split("\n", 1)[0][:160],
            }
            for item in (raw if isinstance(raw, list) else [])
        ]
        rec["n_commits"] = len(rec["commits"])
    return rec


def ensure_gh_evidence(root: Path) -> dict:
    """I2: snapshot the four commit queries ONCE. Tests never call this."""
    existing = load_gh_evidence(root)
    if existing:
        return existing
    until = git_head_committer_date(root) or "2026-10-02T07:02:07Z"
    head = git_head(root)
    queries = {
        "tree_history": fetch_gh_path_commits(
            "data/themes_heatmap/tree_history.jsonl", 5, until
        ),
        "membership_history": fetch_gh_path_commits(
            "data/baskets/membership_history.parquet", 5, until
        ),
        "context_history_latest5": fetch_gh_path_commits(
            "data/themes/context_history.jsonl", 5, until
        ),
        "context_history_first": fetch_gh_path_commits(
            "data/themes/context_history.jsonl", 5, "2026-07-20T00:00:00Z"
        ),
    }
    for key, rec in queries.items():
        rec["key"] = key
    payload = {
        "repo_head": head,
        "until_repo_head_committer_date": until,
        "queries": queries,
    }
    path = gh_evidence_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload


def tree_pit_class_reason_from_commits(write_time: dict | None) -> str:
    """I3: reason text is built from snapshot/local evidence, never a baked commit id."""
    rec = (write_time or {}).get("tree_history") or {}
    commits = rec.get("commits") or []
    if not rec.get("ok") or not commits:
        return (
            "Dated Finviz trees with member tickers. asof is the snapshot date "
            "(first observed date of that vintage's state). Write-time proof: "
            "evidence unavailable."
        )
    oldest = list(reversed(commits))
    parts = []
    for c in oldest:
        parts.append(f"{c.get('sha')} at {c.get('date')} ({c.get('msg')!r})")
    return (
        "Dated Finviz trees with member tickers. asof is the snapshot date "
        "(first observed date of that vintage's state). Write-time proof: "
        "data/themes_heatmap/tree_history.jsonl commits "
        + "; ".join(parts)
        + "; asof values match those commit dates. PIT_HONEST."
    )


def write_time_note_from_evidence(write_time: dict) -> str:
    tree = (write_time.get("tree_history") or {}).get("commits") or []
    memb = (write_time.get("membership_history") or {}).get("commits") or []
    ctx0 = (write_time.get("context_history_first") or {}).get("commits") or []
    if not tree and not memb and not ctx0:
        return "Write-time commit evidence unavailable."
    bits = []
    if tree:
        bits.append(
            "tree_history commits "
            + ", ".join(f"{c.get('sha')} ({c.get('date')})" for c in reversed(tree))
        )
    if memb:
        bits.append(
            "membership_history commits "
            + ", ".join(f"{c.get('sha')} ({c.get('date')})" for c in reversed(memb))
        )
    if ctx0:
        c = ctx0[-1]
        bits.append(
            f"context_history first git write is {c.get('sha')} at {c.get('date')} "
            f"({c.get('msg')!r}); asof rows before {CONTEXT_HISTORY_FIRST_WRITE} "
            "are BACKFILLED."
        )
    return ". ".join(bits)


def iso_day(value: object) -> str | None:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "nat"}:
        return None
    if "T" in text:
        text = text.split("T", 1)[0]
    if len(text) >= 10 and text[4] == "-" and text[7] == "-":
        return text[:10]
    if len(text) >= 4 and text[:4].isdigit():
        return text[:10] if len(text) >= 10 else text
    return None


def year_of(value: object) -> str | None:
    day = iso_day(value)
    if day and len(day) >= 4 and day[:4] in YEARS:
        return day[:4]
    return None


def parse_company_ticker(node_id: object) -> str | None:
    text = str(node_id)
    parts = text.split(":")
    if len(parts) >= 3 and parts[0] == "co":
        return parts[2].upper()
    return None


def empty_year_cov() -> dict[str, float]:
    return {y: 0.0 for y in YEARS}


def frac(n: int, d: int) -> float:
    if d <= 0:
        return 0.0
    return round(n / d, 6)


def min_max_days(values) -> tuple[str | None, str | None]:
    days = sorted({d for d in (iso_day(v) for v in values) if d})
    if not days:
        return None, None
    return days[0], days[-1]


def weeks_between(start: str | None, end: str | None) -> dict:
    if not start or not end:
        return {"start": start, "end": end, "days": None, "weeks": None}
    a = date.fromisoformat(start)
    b = date.fromisoformat(end)
    days = (b - a).days
    return {"start": start, "end": end, "days": days, "weeks": round(days / 7, 4)}


def pct_cell(v: float) -> str:
    if v == 0.0:
        return "0"
    return f"{100.0 * v:.2f}%"


@lru_cache(maxsize=1)
def load_universe(root: Path) -> tuple[list[str], int, int]:
    """Return sorted universe tickers, n_files, n_excluded_short."""
    names: list[str] = []
    n_files = 0
    n_short = 0
    for path in sorted((root / "data/baskets/ohlcv").glob("*.parquet")):
        n_files += 1
        n_rows = pq.ParquetFile(path).metadata.num_rows
        if n_rows >= MIN_ROWS:
            names.append(path.stem.upper())
        else:
            n_short += 1
    return names, n_files, n_short


def coverage_from_pairs(universe: set[str], pairs: list[tuple[str, str]]) -> tuple[float, dict[str, float], int, dict[str, int]]:
    """pairs = (ticker, date_str). Coverage is membership-in-universe share."""
    ever: set[str] = set()
    by_year: dict[str, set[str]] = {y: set() for y in YEARS}
    for ticker, date_s in pairs:
        t = ticker.upper()
        if t not in universe:
            continue
        ever.add(t)
        y = year_of(date_s)
        if y:
            by_year[y].add(t)
    n = len(universe)
    return (
        frac(len(ever), n),
        {y: frac(len(by_year[y]), n) for y in YEARS},
        len(ever),
        {y: len(by_year[y]) for y in YEARS},
    )


def per_date_dated(universe: set[str], tickers, dates) -> list[dict]:
    by: dict[str, set[str]] = {}
    rows_by: dict[str, int] = {}
    for t, d in zip(tickers, dates):
        day = iso_day(d)
        name = str(t).upper() if t is not None else None
        if not day or not name:
            continue
        rows_by[day] = rows_by.get(day, 0) + 1
        if name in universe:
            by.setdefault(day, set()).add(name)
    n = len(universe)
    out = []
    for day in sorted(set(rows_by) | set(by)):
        names = by.get(day, set())
        out.append(
            {
                "date": day,
                "n_rows": int(rows_by.get(day, 0)),
                "n_univ_tickers": len(names),
                "coverage": frac(len(names), n),
            }
        )
    return out


PER_DATE_IN_FORCE_SEMANTICS = (
    "cumulative-ever: a name once observed on this clock remains counted on later "
    "eval dates; membership never closes. Not interval in-force. The grading minimum "
    "does not use this series."
)


def per_date_in_force(universe: set[str], tickers, dates, eval_dates: list[str]) -> list[dict]:
    """Cumulative-ever ticker counts (membership never closes). See PER_DATE_IN_FORCE_SEMANTICS."""
    pairs: list[tuple[str, str]] = []
    for t, d in zip(tickers, dates):
        day = iso_day(d)
        name = str(t).upper() if t is not None else None
        if day and name and name in universe:
            pairs.append((day, name))
    n = len(universe)
    out = []
    for d in eval_dates:
        names = {name for day, name in pairs if day <= d}
        out.append({"date": d, "n_univ_tickers": len(names), "coverage": frac(len(names), n)})
    return out


def honest_in_force_names(
    d: str,
    universe: set[str],
    tree_members: dict[str, set[str]],
    snap_names: dict[str, set[str]],
) -> set[str]:
    """Universe names in force at D from tree asof and snapshot_date only.

    Never unions membership_history.added or theme_graph_edges.
    """
    names: set[str] = set()
    t_el = [a for a in sorted(tree_members) if a <= d]
    if t_el:
        names |= tree_members[t_el[-1]]
    s_el = [a for a in sorted(snap_names) if a <= d]
    if s_el:
        names |= snap_names[s_el[-1]]
    return names & universe


def load_snapshot_names(root: Path) -> dict[str, set[str]]:
    mh = pd.read_parquet(root / "data/baskets/membership_history.parquet")
    tickers = mh["ticker"].astype(str).str.upper()
    snaps = mh["snapshot_date"].map(iso_day)
    out: dict[str, set[str]] = {}
    for snap, t in zip(snaps.tolist(), tickers.tolist()):
        if not snap:
            continue
        out.setdefault(snap, set()).add(t)
    return out


def iso_week_leading_table(
    per_date: list[dict],
    year: int = 2026,
    weeks=range(33, 41),
    honest_start: str | None = None,
) -> list[dict]:
    """I7: keep min/max over all dates in the week (frozen numbers) and mark
    weeks that include a date before leading_theme_join.honest_start.
    Do not drop those dates: dropping 2026-08-12 would change week-33 min from 0 to 228.
    """
    week_set = set(weeks)
    buckets: dict[int, list[dict]] = {w: [] for w in weeks}
    for r in per_date:
        d = date.fromisoformat(r["date"])
        y, w, _ = d.isocalendar()
        if y == year and w in week_set:
            buckets[w].append(r)
    out = []
    for w in weeks:
        rows = buckets[w]
        if not rows:
            out.append(
                {
                    "iso_year": year,
                    "iso_week": w,
                    "dates": [],
                    "n_dates": 0,
                    "min_leading_n": None,
                    "min_leading_coverage": None,
                    "min_date": None,
                    "max_leading_n": None,
                    "max_leading_coverage": None,
                    "max_date": None,
                    "status": None,
                    "n_dates_before_honest_start": 0,
                }
            )
            continue
        min_r = min(rows, key=lambda r: (r["snapshot_honest_leading_n"], r["date"]))
        max_r = max(rows, key=lambda r: (r["snapshot_honest_leading_n"], r["date"]))
        n_before = 0
        if honest_start:
            n_before = sum(1 for r in rows if r["date"] < honest_start)
        out.append(
            {
                "iso_year": year,
                "iso_week": w,
                "dates": [r["date"] for r in rows],
                "n_dates": len(rows),
                "min_leading_n": min_r["snapshot_honest_leading_n"],
                "min_leading_coverage": min_r["snapshot_honest_leading_coverage"],
                "min_date": min_r["date"],
                "max_leading_n": max_r["snapshot_honest_leading_n"],
                "max_leading_coverage": max_r["snapshot_honest_leading_coverage"],
                "max_date": max_r["date"],
                "status": "BEFORE_HONEST_START" if n_before else "HONEST",
                "n_dates_before_honest_start": n_before,
            }
        )
    return out


def source_record(
    *,
    name: str,
    path: str,
    grain: str,
    date_field: str,
    date_min: str | None,
    date_max: str | None,
    n_tickers: int,
    n_themes: int,
    pit_class: str,
    universe_coverage_ever: float,
    coverage_by_year: dict[str, float],
    **extra,
) -> dict:
    if pit_class not in PIT_CLASSES:
        raise ValueError(f"bad pit_class {pit_class}")
    rec = {
        "name": name,
        "path": path,
        "grain": grain,
        "date_field": date_field,
        "date_min": date_min,
        "date_max": date_max,
        "n_tickers": n_tickers,
        "n_themes": n_themes,
        "pit_class": pit_class,
        "universe_coverage_ever": universe_coverage_ever,
        "coverage_by_year": coverage_by_year,
    }
    rec.update(extra)
    return rec


def load_jsonl(path: Path) -> tuple[list[dict], int]:
    rows: list[dict] = []
    n_fail = 0
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            text = line.strip()
            if not text:
                continue
            try:
                obj = json.loads(text)
            except json.JSONDecodeError:
                n_fail += 1
                continue
            if isinstance(obj, dict):
                rows.append(obj)
            else:
                n_fail += 1
    return rows, n_fail


def find_quote(root: Path, rel: str, snippet: str) -> tuple[int, str]:
    path = root / rel
    lines = path.read_text(encoding="utf-8").splitlines()
    for i, line in enumerate(lines, 1):
        if snippet in line:
            return i, line.strip()
    raise ValueError(f"snippet not found in {rel}: {snippet!r}")


def census_theme_graph_meta(root: Path, universe: set[str]) -> dict:
    rel = "data/theme_graph/_meta.json"
    meta = json.loads((root / rel).read_text(encoding="utf-8"))
    belief = iso_day(meta.get("belief_time"))
    return source_record(
        name="theme_graph_meta",
        path=rel,
        grain="graph-generation snapshot (one file per nightly belief)",
        date_field="belief_time",
        date_min=belief,
        date_max=belief,
        n_tickers=0,
        n_themes=0,
        pit_class="BACKFILLED",
        universe_coverage_ever=0.0,
        coverage_by_year=empty_year_cov(),
        n_membership_rows=0,
        n_univ_tickers_ever=0,
        pit_class_field="belief_time",
        pit_class_reason=(
            "Single current-belief sidecar. belief_time is the generation date; "
            "computed_at is the build clock. Graded on belief_time. No ticker-theme rows. "
            "This date is E* (as-observed-today bound) for the honest window."
        ),
        computed_at=meta.get("computed_at"),
        edges_latest_belief=(meta.get("counts") or {}).get("edges_latest_belief"),
        finviz_vintages=((meta.get("local_plane") or {}).get("finviz") or {}).get("vintages"),
        baskets_membership_published_at=(
            ((meta.get("per_suite") or {}).get("baskets") or {}).get("membership_published_at")
        ),
        baskets_seed_constant=((meta.get("per_suite") or {}).get("baskets") or {}).get("seed_constant"),
        honest_clock="belief_time (current generation; not a membership tape)",
        honest_start=belief,
    )


def census_nodes(root: Path, universe: set[str]) -> dict:
    rel = "data/theme_graph/nodes.parquet"
    df = pd.read_parquet(root / rel)
    tickers = sorted({t for t in (parse_company_ticker(x) for x in df["node_id"]) if t})
    n_themes = int((df["kind"] == "theme").sum() + (df["kind"] == "local_theme").sum())
    dmin, dmax = min_max_days(df["computed_at"].tolist())
    birth_by_kind = {
        str(k): int(v)
        for k, v in df.groupby("kind")["birth_date"].apply(lambda s: int(s.notna().sum())).items()
    }
    return source_record(
        name="theme_graph_nodes",
        path=rel,
        grain="node_id (keep-first current catalog; one row per node)",
        date_field="computed_at",
        date_min=dmin,
        date_max=dmax,
        n_tickers=len(tickers),
        n_themes=n_themes,
        pit_class="BACKFILLED",
        universe_coverage_ever=0.0,
        coverage_by_year=empty_year_cov(),
        n_membership_rows=0,
        n_univ_tickers_ever=0,
        n_company_nodes=int((df["kind"] == "company").sum()),
        n_us_company_nodes=int(df["node_id"].astype(str).str.startswith("co:us:").sum()),
        birth_date_nonnull=int(df["birth_date"].notna().sum()),
        birth_date_nonnull_by_kind=birth_by_kind,
        pit_class_field="computed_at",
        pit_class_reason=(
            "Node catalog is keep-first. Company/basket/theme/etf birth_date is null; "
            "birth_date is populated only on local_theme nodes (Finviz vintage dates). "
            "computed_at is a write clock, not a membership observation."
        ),
        honest_clock="none (keep-first catalog)",
        honest_start=None,
    )


def _subsource_pit_class(g: pd.DataFrame) -> tuple[str, str]:
    """BACKFILLED if any row's observed clock (evidence_time or valid_from) precedes belief_time."""
    n_precede = 0
    for et, vf, bt in zip(g["evidence_time"].tolist(), g["valid_from"].tolist(), g["belief_time"].tolist()):
        etd, vfd, btd = iso_day(et), iso_day(vf), iso_day(bt)
        if btd and ((etd and etd < btd) or (vfd and vfd < btd)):
            n_precede += 1
    if n_precede:
        return (
            "BACKFILLED",
            f"{n_precede}/{len(g)} rows have evidence_time or valid_from strictly before belief_time",
        )
    return (
        "PIT_HONEST",
        "every row's evidence_time and valid_from are >= belief_time (known on belief_time)",
    )


def census_edges(root: Path, universe: set[str]) -> dict:
    rel = "data/theme_graph/edges.parquet"
    df = pd.read_parquet(root / rel)
    mo = df[df["type"] == "MEMBER_OF"].copy()
    mo["ticker"] = mo["src"].map(parse_company_ticker)
    mo = mo[mo["ticker"].notna()]
    pairs = [
        (str(t), str(d))
        for t, d in zip(mo["ticker"].tolist(), mo["evidence_time"].tolist())
        if t and iso_day(d)
    ]
    ever, by_year, n_ever, n_by_year = coverage_from_pairs(universe, pairs)
    tickers = sorted(set(mo["ticker"].tolist()))
    themes = sorted(set(mo["dst"].astype(str).tolist()))
    dmin, dmax = min_max_days(mo["evidence_time"].tolist())
    us = mo[mo["src"].astype(str).str.startswith("co:us:")]
    us_univ = us[us["ticker"].isin(universe)]
    finviz = us_univ[us_univ["date_provenance"].astype(str) == "raw_snapshot"]
    seed = us_univ[us_univ["date_provenance"].astype(str) == "seed_constant"]
    vf_pairs = [
        (str(t), str(d))
        for t, d in zip(us_univ["ticker"].tolist(), us_univ["valid_from"].tolist())
        if t and iso_day(d)
    ]
    vf_ever, vf_year, vf_n_ever, vf_n_year = coverage_from_pairs(universe, vf_pairs)

    sub_sources = []
    for prov, g in us.groupby(us["date_provenance"].astype(str), sort=True):
        pit, reason = _subsource_pit_class(g)
        bt_min, bt_max = min_max_days(g["belief_time"].tolist())
        et_min, et_max = min_max_days(g["evidence_time"].tolist())
        vf_min, vf_max = min_max_days(g["valid_from"].tolist())
        g_univ = g[g["ticker"].isin(universe)]
        bt_vals = sorted({iso_day(x) for x in g["belief_time"].tolist() if iso_day(x)})
        sub_sources.append(
            {
                "name": str(prov),
                "n_rows": int(len(g)),
                "n_univ_rows": int(len(g_univ)),
                "n_univ_tickers": int(g_univ["ticker"].nunique()) if len(g_univ) else 0,
                "pit_class": pit,
                "pit_class_reason": reason,
                "belief_time_min": bt_min,
                "belief_time_max": bt_max,
                "belief_time_values": bt_vals,
                "evidence_time_min": et_min,
                "evidence_time_max": et_max,
                "valid_from_min": vf_min,
                "valid_from_max": vf_max,
                "dst_kind_counts": {
                    str(k): int(v)
                    for k, v in g["dst"].astype(str).str.split(":").str[0].value_counts().items()
                },
            }
        )

    dated_obs = per_date_dated(universe, us_univ["ticker"].tolist(), us_univ["evidence_time"].tolist())
    dated_belief = per_date_dated(universe, us_univ["ticker"].tolist(), us_univ["belief_time"].tolist())
    dated_valid = per_date_dated(universe, us_univ["ticker"].tolist(), us_univ["valid_from"].tolist())
    eval_obs = [r["date"] for r in dated_obs]
    eval_bel = [r["date"] for r in dated_belief]
    in_force_obs = per_date_in_force(
        universe, us_univ["ticker"].tolist(), us_univ["evidence_time"].tolist(), eval_obs
    )
    in_force_bel = per_date_in_force(
        universe, us_univ["ticker"].tolist(), us_univ["belief_time"].tolist(), eval_bel
    )
    max_dated_belief = max((r["coverage"] for r in dated_belief), default=0.0)
    max_dated_belief_n = max((r["n_univ_tickers"] for r in dated_belief), default=0)
    max_dated_belief_date = None
    for r in dated_belief:
        if r["n_univ_tickers"] == max_dated_belief_n:
            max_dated_belief_date = r["date"]
            break
    max_dated_obs = max((r["coverage"] for r in dated_obs), default=0.0)
    max_dated_obs_n = max((r["n_univ_tickers"] for r in dated_obs), default=0)

    return source_record(
        name="theme_graph_edges",
        path=rel,
        grain="edge_id x belief_time (bitemporal); membership grain = company ticker x basket|ltheme",
        date_field="evidence_time",
        date_min=dmin,
        date_max=dmax,
        n_tickers=len(tickers),
        n_themes=len(themes),
        pit_class="BACKFILLED",
        universe_coverage_ever=ever,
        coverage_by_year=by_year,
        n_membership_rows=int(len(mo)),
        n_univ_tickers_ever=n_ever,
        n_univ_tickers_by_year=n_by_year,
        n_us_member_of_rows=int(len(us)),
        n_us_univ_tickers=int(us_univ["ticker"].nunique()) if len(us_univ) else 0,
        n_finviz_univ_tickers=int(finviz["ticker"].nunique()) if len(finviz) else 0,
        n_seed_constant_univ_tickers=int(seed["ticker"].nunique()) if len(seed) else 0,
        valid_from_min=min_max_days(mo["valid_from"].tolist())[0],
        valid_from_max=min_max_days(mo["valid_from"].tolist())[1],
        belief_time_min=min_max_days(df["belief_time"].tolist())[0],
        belief_time_max=min_max_days(df["belief_time"].tolist())[1],
        valid_from_coverage_ever=vf_ever,
        valid_from_coverage_by_year=vf_year,
        valid_from_n_univ_ever=vf_n_ever,
        valid_from_n_univ_by_year=vf_n_year,
        pit_class_field="belief_time vs evidence_time/valid_from (sub-source split on date_provenance)",
        pit_class_reason=(
            "File-level BACKFILLED after a belief_time check: every US MEMBER_OF sub-source "
            "has observed dates (evidence_time and/or valid_from) strictly before belief_time "
            "on at least one row. raw_snapshot (2365 rows) has belief_time=2026-08-15 on EVERY "
            "row while evidence_time/valid_from include 2026-06-27. Q2 year table still uses "
            "evidence_time (union-within-year). Headline membership coverage is the per-date "
            "figure on belief_time dated-that-day, not the union-ever. This source is excluded "
            "from the honest in-force series."
        ),
        us_era_counts={str(k): int(v) for k, v in us["era"].value_counts().sort_index().items()}
        if len(us)
        else {},
        us_date_provenance_counts={
            str(k): int(v) for k, v in us["date_provenance"].value_counts().sort_index().items()
        }
        if len(us)
        else {},
        sub_sources=sub_sources,
        per_date_observed_evidence_time=dated_obs,
        per_date_belief_time=dated_belief,
        per_date_valid_from=dated_valid,
        per_date_in_force_evidence_time=in_force_obs,
        per_date_in_force_belief_time=in_force_bel,
        per_date_in_force_semantics=PER_DATE_IN_FORCE_SEMANTICS,
        headline_per_date_honest_clock=(
            "belief_time dated-that-day (BACKFILLED source; excluded from the honest series; "
            "not union-ever, not cumulative-ever)"
        ),
        headline_per_date_coverage=max_dated_belief,
        headline_per_date_n=int(max_dated_belief_n),
        headline_per_date_date=max_dated_belief_date,
        max_dated_evidence_time_coverage=max_dated_obs,
        max_dated_evidence_time_n=int(max_dated_obs_n),
        union_ever_coverage=ever,
        union_ever_n=int(n_ever),
        honest_clock="belief_time (BACKFILLED source; excluded from the honest series)",
        honest_start=min_max_days(us_univ["belief_time"].tolist())[0] if len(us_univ) else None,
    )


def census_lifecycle(root: Path, universe: set[str]) -> dict:
    rel = "data/theme_graph/node_lifecycle.parquet"
    df = pd.read_parquet(root / rel)
    tickers = sorted({t for t in (parse_company_ticker(x) for x in df["node_id"]) if t})
    dmin, dmax = min_max_days(df["retire_date"].tolist())
    return source_record(
        name="theme_graph_node_lifecycle",
        path=rel,
        grain="node_id (retirement events; 2 rows)",
        date_field="retire_date",
        date_min=dmin,
        date_max=dmax,
        n_tickers=len(tickers),
        n_themes=0,
        pit_class="BACKFILLED",
        universe_coverage_ever=0.0,
        coverage_by_year=empty_year_cov(),
        n_membership_rows=0,
        n_univ_tickers_ever=0,
        pit_class_field="retire_date vs ratified_by",
        pit_class_reason=(
            "Identity-break retirements, not theme membership. A past retire_date stamped "
            "after ratification is not a PIT membership tape."
        ),
        node_ids=sorted(df["node_id"].astype(str).tolist()),
        honest_clock="none (retirement events, backfilled vs ratification)",
        honest_start=None,
    )


def census_identity(root: Path, universe: set[str]) -> dict:
    rel = "data/theme_graph/identity_resolution.parquet"
    df = pd.read_parquet(root / rel)
    tickers = sorted({str(s).upper() for s in df["source_native_symbol"].dropna().tolist()})
    dmin, dmax = min_max_days(df["resolution_asof"].tolist())
    return source_record(
        name="theme_graph_identity_resolution",
        path=rel,
        grain="node_id x resolution_asof (identity join, not membership)",
        date_field="resolution_asof",
        date_min=dmin,
        date_max=dmax,
        n_tickers=len(tickers),
        n_themes=0,
        pit_class="PIT_HONEST",
        universe_coverage_ever=0.0,
        coverage_by_year=empty_year_cov(),
        n_membership_rows=0,
        n_univ_tickers_ever=0,
        n_rows=int(len(df)),
        n_distinct_asof=int(df["resolution_asof"].nunique()),
        pit_class_field="resolution_asof",
        pit_class_reason=(
            "Append-only identity resolutions dated by resolution_asof. A row could have "
            "been known on its resolution_asof. No theme column; Q2 membership coverage 0."
        ),
        honest_clock="resolution_asof",
        honest_start=dmin,
    )


def census_capability(root: Path, universe: set[str]) -> dict:
    rel = "data/theme_graph/capability.parquet"
    df = pd.read_parquet(root / rel)
    dmin, dmax = min_max_days(df["computed_at"].tolist())
    n_themes = int(df["node_id"].nunique())
    return source_record(
        name="theme_graph_capability",
        path=rel,
        grain="ltheme node_id x computed_at (re-derived sidecar)",
        date_field="computed_at",
        date_min=dmin,
        date_max=dmax,
        n_tickers=0,
        n_themes=n_themes,
        pit_class="PIT_HONEST",
        universe_coverage_ever=0.0,
        coverage_by_year=empty_year_cov(),
        n_membership_rows=0,
        n_univ_tickers_ever=0,
        n_rows=int(len(df)),
        pit_class_field="computed_at",
        pit_class_reason=(
            "Capability sidecar is re-derived; historical computed_at rows survive. "
            "Not ticker-theme membership; coverage 0."
        ),
        honest_clock="computed_at",
        honest_start=dmin,
    )


def census_evidence(root: Path, universe: set[str]) -> dict:
    rel = "data/theme_graph/evidence.parquet"
    df = pd.read_parquet(root / rel)
    dmin, dmax = min_max_days(df["published_at"].tolist())
    pub_ne_comp = int(
        sum(
            iso_day(a) != iso_day(b)
            for a, b in zip(df["published_at"].tolist(), df["computed_at"].tolist())
        )
    )
    return source_record(
        name="theme_graph_evidence",
        path=rel,
        grain="evidence_id (source receipts)",
        date_field="published_at",
        date_min=dmin,
        date_max=dmax,
        n_tickers=0,
        n_themes=0,
        pit_class="PIT_HONEST",
        universe_coverage_ever=0.0,
        coverage_by_year=empty_year_cov(),
        n_membership_rows=0,
        n_univ_tickers_ever=0,
        n_rows=int(len(df)),
        n_published_at_ne_computed_at_day=pub_ne_comp,
        published_at_values=sorted({str(x) for x in df["published_at"].dropna().tolist()}),
        pit_class_field="published_at",
        pit_class_reason=(
            "Evidence receipts dated by published_at of the source document (creation clock). "
            "computed_at is the write clock. Honest as receipts; no ticker column."
        ),
        honest_clock="published_at",
        honest_start=dmin,
    )


def census_phase_history(root: Path, universe: set[str]) -> tuple[dict, int]:
    rel = "data/neuralweb/theme_phase_history.jsonl"
    rows, n_fail = load_jsonl(root / rel)
    themes = sorted({str(r.get("theme_id")) for r in rows if r.get("theme_id")})
    dmin, dmax = min_max_days([r.get("as_of") for r in rows])
    rec = source_record(
        name="neuralweb_theme_phase_history",
        path=rel,
        grain="theme_id x as_of (phase/lifecycle snapshot; no tickers)",
        date_field="as_of",
        date_min=dmin,
        date_max=dmax,
        n_tickers=0,
        n_themes=len(themes),
        pit_class="PIT_HONEST",
        universe_coverage_ever=0.0,
        coverage_by_year=empty_year_cov(),
        n_membership_rows=0,
        n_univ_tickers_ever=0,
        n_rows=len(rows),
        n_distinct_as_of=len({iso_day(r.get("as_of")) for r in rows if iso_day(r.get("as_of"))}),
        parse_failures=n_fail,
        pit_class_field="as_of",
        pit_class_reason=(
            "Dated per-theme phase snapshots. as_of is the observation date. Theme-level only."
        ),
        scoring_lifecycle_values=sorted(
            {str(r.get("scoring_lifecycle")) for r in rows if r.get("scoring_lifecycle") is not None}
        ),
        foresight_stage_values=sorted(
            {str(r.get("foresight_stage")) for r in rows if r.get("foresight_stage") is not None}
        ),
        honest_clock="as_of",
        honest_start=dmin,
    )
    return rec, n_fail


def census_context(root: Path, universe: set[str], rel: str, name: str) -> tuple[dict, int]:
    rows, n_fail = load_jsonl(root / rel)
    theme_ids: set[str] = set()
    asofs = []
    for r in rows:
        labels = r.get("labels") or {}
        if isinstance(labels, dict):
            theme_ids.update(str(k) for k in labels.keys())
        day = iso_day(r.get("asof"))
        if day:
            asofs.append(day)
    dmin, dmax = min_max_days(asofs)
    # I1: US context_history first git write is 2026-07-19. Rows before that
    # were written after the fact (BACKFILLED), consistent with the edges treatment.
    # CN file is not re-dated; only themes_context_history is split.
    if name == "themes_context_history":
        first_write = CONTEXT_HISTORY_FIRST_WRITE
        n_before = sum(1 for d in asofs if d < first_write)
        n_from = sum(1 for d in asofs if d >= first_write)
        honest_start = first_write
        pit_class = "PIT_HONEST"
        pit_class_reason = (
            "Dated theme-context snapshots. asof is the observation date. Labels are "
            "theme-level (dominant/emerging/fading/…). No ticker membership on the row; "
            "join to membership_history.snapshot_date is required to name members. "
            f"I1: first git write is commit 15c39ef87650 at 2026-07-19T03:22:13Z, so "
            f"asof < {first_write} ({n_before} rows) is BACKFILLED; asof >= {first_write} "
            f"({n_from} rows) is PIT_HONEST. honest_start={first_write} "
            f"(was {dmin}). Leading-theme join starts 2026-08-13 so membership numbers "
            "do not move."
        )
        asof_classes = {
            "before_first_write": {
                "pit_class": "BACKFILLED",
                "asof_lt": first_write,
                "n_rows": n_before,
            },
            "from_first_write": {
                "pit_class": "PIT_HONEST",
                "asof_ge": first_write,
                "n_rows": n_from,
            },
        }
        honest_clock = f"asof >= {first_write} (rows before first git write BACKFILLED)"
    else:
        honest_start = dmin
        pit_class = "PIT_HONEST"
        pit_class_reason = (
            "Dated theme-context snapshots. asof is the observation date. Labels are "
            "theme-level (dominant/emerging/fading/…). No ticker membership on the row; "
            "join to membership_history.snapshot_date is required to name members."
        )
        asof_classes = None
        honest_clock = "asof"
    rec = source_record(
        name=name,
        path=rel,
        grain="asof snapshot of theme labels/scores/leadership_state (no tickers)",
        date_field="asof",
        date_min=dmin,
        date_max=dmax,
        n_tickers=0,
        n_themes=len(theme_ids),
        pit_class=pit_class,
        universe_coverage_ever=0.0,
        coverage_by_year=empty_year_cov(),
        n_membership_rows=0,
        n_univ_tickers_ever=0,
        n_rows=len(rows),
        n_distinct_asof=len(set(asofs)),
        parse_failures=n_fail,
        theme_ids=sorted(theme_ids),
        pit_class_field="asof",
        pit_class_reason=pit_class_reason,
        leadership_state_values=sorted(
            {str(r.get("leadership_state")) for r in rows if r.get("leadership_state") is not None}
        ),
        label_values=sorted(
            {str(v) for r in rows for v in (r.get("labels") or {}).values() if v is not None}
        ),
        honest_clock=honest_clock,
        honest_start=honest_start,
        asof_classes=asof_classes,
        honest_start_before_i1=dmin if name == "themes_context_history" else None,
    )
    return rec, n_fail


def census_subsector_perf(root: Path, universe: set[str]) -> tuple[dict, int]:
    rel = "data/themes_heatmap/subsector_perf_history.jsonl"
    rows, n_fail = load_jsonl(root / rel)
    keys: set[str] = set()
    for r in rows:
        subs = r.get("subsectors") or {}
        if isinstance(subs, dict):
            keys.update(str(k) for k in subs.keys())
    dmin, dmax = min_max_days([r.get("asof") for r in rows])
    rec = source_record(
        name="themes_heatmap_subsector_perf_history",
        path=rel,
        grain="asof x subsector performance (returns, not membership)",
        date_field="asof",
        date_min=dmin,
        date_max=dmax,
        n_tickers=0,
        n_themes=len(keys),
        pit_class="PIT_HONEST",
        universe_coverage_ever=0.0,
        coverage_by_year=empty_year_cov(),
        n_membership_rows=0,
        n_univ_tickers_ever=0,
        n_rows=len(rows),
        parse_failures=n_fail,
        pit_class_field="asof",
        pit_class_reason=(
            "Dated subsector performance snapshots. Honest as a performance tape; members "
            "are not present on the row."
        ),
        honest_clock="asof",
        honest_start=dmin,
    )
    return rec, n_fail


def _tree_members(row: dict) -> set[str]:
    out: set[str] = set()
    for theme in row.get("tree") or []:
        if not isinstance(theme, dict):
            continue
        for sub in theme.get("subsectors") or []:
            if not isinstance(sub, dict):
                continue
            for m in sub.get("members") or []:
                if isinstance(m, str):
                    out.add(m.upper())
    return out


def census_tree_history(root: Path, universe: set[str]) -> tuple[dict, int]:
    rel = "data/themes_heatmap/tree_history.jsonl"
    rows, n_fail = load_jsonl(root / rel)
    pairs: list[tuple[str, str]] = []
    tickers: set[str] = set()
    theme_keys: set[str] = set()
    sub_keys: set[str] = set()
    per_asof: dict[str, dict] = {}
    members_by_asof: dict[str, set[str]] = {}
    for r in rows:
        asof = iso_day(r.get("asof"))
        if not asof:
            continue
        snap = _tree_members(r)
        members_by_asof[asof] = snap
        tickers |= snap
        for theme in r.get("tree") or []:
            if isinstance(theme, dict) and theme.get("key"):
                theme_keys.add(str(theme["key"]))
            for sub in (theme.get("subsectors") or []) if isinstance(theme, dict) else []:
                if isinstance(sub, dict) and sub.get("key"):
                    sub_keys.add(str(sub["key"]))
        for t in snap:
            pairs.append((t, asof))
        in_u = snap & universe
        per_asof[asof] = {"n_tickers": len(snap), "n_univ_tickers": len(in_u)}
    ever, by_year, n_ever, n_by_year = coverage_from_pairs(universe, pairs)
    dmin, dmax = min_max_days(per_asof.keys())
    change = {
        "semantics": "first_observed_date_of_new_state",
        "not": "recorded_transition_date",
        "cite": "engine/theme_graph/local_sources.py:8-18",
        "note": (
            "tree_history rows are snapshots keyed by asof. A membership present in "
            "vintages i..j opens at asof(i) (first observed date of the new state) and "
            "closes at asof(j+1) — the first date the source was observed WITHOUT it. "
            "There is no recorded mid-window transition date. Closing is interval-censored "
            "to the next refresh (valid_from means FIRST OBSERVED)."
        ),
    }
    asofs = sorted(members_by_asof)
    ls_path = root / "engine/theme_graph/local_sources.py"
    ls_lines = ls_path.read_text(encoding="utf-8").splitlines()
    change["quoted_lines"] = [{"line": i, "text": ls_lines[i - 1]} for i in range(8, 19)]
    change["quote_path"] = "engine/theme_graph/local_sources.py"
    if len(asofs) >= 2:
        a, b = asofs[0], asofs[1]
        sa, sb = members_by_asof[a], members_by_asof[b]
        change["example"] = {
            "from_asof": a,
            "to_asof": b,
            "n_added": len(sb - sa),
            "n_removed": len(sa - sb),
            "n_stable": len(sa & sb),
            "delta": f"+{len(sb - sa)} / -{len(sa - sb)}",
            "interpretation": (
                f"Members in {b} but not {a} first become observed at {b} "
                f"(not at an unrecorded date between {a} and {b}). "
                f"Members in {a} but not {b} are interval-censored closed at {b}."
            ),
        }
    rec = source_record(
        name="themes_heatmap_tree_history",
        path=rel,
        grain="ticker x subsector x asof (Finviz tree snapshots)",
        date_field="asof",
        date_min=dmin,
        date_max=dmax,
        n_tickers=len(tickers),
        n_themes=len(theme_keys),
        pit_class="PIT_HONEST",
        universe_coverage_ever=ever,
        coverage_by_year=by_year,
        n_membership_rows=len(pairs),
        n_univ_tickers_ever=n_ever,
        n_univ_tickers_by_year=n_by_year,
        n_subsectors=len(sub_keys),
        n_rows=len(rows),
        parse_failures=n_fail,
        per_asof=[{"asof": k, **per_asof[k]} for k in sorted(per_asof)],
        change_point_semantics=change,
        pit_class_field="asof",
        pit_class_reason=tree_pit_class_reason_from_commits(None),
        write_time_commits_cite=(
            "gh_evidence.json queries.tree_history (until=repo_head committer date)"
        ),
        honest_clock="asof",
        honest_start=dmin,
    )
    rec["_members_by_asof"] = {k: sorted(v) for k, v in members_by_asof.items()}
    return rec, n_fail


def census_program_ledger(root: Path, universe: set[str]) -> dict:
    rel = "data/theme_activity/program_ledger.parquet"
    df = pd.read_parquet(root / rel)
    dmin, dmax = min_max_days(df["first_seen_date"].tolist())
    return source_record(
        name="theme_activity_program_ledger",
        path=rel,
        grain="SAM.gov program/solicitation x basket_id",
        date_field="first_seen_date",
        date_min=dmin,
        date_max=dmax,
        n_tickers=0,
        n_themes=int(df["basket_id"].nunique()),
        pit_class="PIT_HONEST",
        universe_coverage_ever=0.0,
        coverage_by_year=empty_year_cov(),
        n_membership_rows=0,
        n_univ_tickers_ever=0,
        n_rows=int(len(df)),
        pit_class_field="first_seen_date",
        pit_class_reason=(
            "first_seen_date is the date a procurement program was observed. No stock ticker."
        ),
        basket_ids=sorted(df["basket_id"].astype(str).unique().tolist()),
        honest_clock="first_seen_date",
        honest_start=dmin,
    )


def census_phase0(root: Path, universe: set[str]) -> dict:
    rel = "data/theme_discovery/phase0.json"
    obj = json.loads((root / rel).read_text(encoding="utf-8"))
    gen = iso_day(obj.get("generated_at"))
    return source_record(
        name="theme_discovery_phase0",
        path=rel,
        grain="single aggregate discovery snapshot (no ticker list)",
        date_field="generated_at",
        date_min=gen,
        date_max=gen,
        n_tickers=0,
        n_themes=0,
        pit_class="UNDECIDABLE",
        universe_coverage_ever=0.0,
        coverage_by_year=empty_year_cov(),
        n_membership_rows=0,
        n_univ_tickers_ever=0,
        n_flags=obj.get("n_flags"),
        pit_class_field="generated_at",
        pit_class_reason=(
            "Aggregate stats only (n_flags=116, no flag/ticker/theme list). Cannot decide "
            "PIT membership without the missing flag roster."
        ),
        verdict_field=obj.get("verdict"),
        honest_clock="undecidable (roster missing)",
        honest_start=None,
    )


def census_membership_history(root: Path, universe: set[str]) -> dict:
    """US basket PIT tape. snapshot_date is PIT_HONEST; added is BACKFILLED."""
    rel = "data/baskets/membership_history.parquet"
    path = root / rel
    df = pd.read_parquet(path)
    df = df.copy()
    df["ticker"] = df["ticker"].astype(str).str.upper()
    df["basket_id"] = df["basket_id"].astype(str)
    added_pairs = [
        (str(t), str(d))
        for t, d in zip(df["ticker"].tolist(), df["added"].tolist())
        if t and iso_day(d)
    ]
    ever, by_year, n_ever, n_by_year = coverage_from_pairs(universe, added_pairs)
    dmin, dmax = min_max_days(df["added"].tolist())
    snap_min, snap_max = min_max_days(df["snapshot_date"].tolist())
    snap_counts = []
    for snap, g in df.groupby(df["snapshot_date"].map(iso_day)):
        if not snap:
            continue
        names = set(g["ticker"].tolist())
        snap_counts.append(
            {
                "snapshot_date": snap,
                "n_rows": int(len(g)),
                "n_tickers": len(names),
                "n_univ_tickers": len(names & universe),
                "coverage": frac(len(names & universe), len(universe)),
                "n_baskets": int(g["basket_id"].nunique()),
            }
        )
    snap_counts.sort(key=lambda r: r["snapshot_date"])
    snap_pairs = [
        (str(t), str(d))
        for t, d in zip(df["ticker"].tolist(), df["snapshot_date"].tolist())
        if t and iso_day(d)
    ]
    snap_ever, snap_year, snap_n_ever, snap_n_year = coverage_from_pairs(universe, snap_pairs)
    return source_record(
        name="baskets_membership_history",
        path=rel,
        grain="(snapshot_date, basket_id, ticker) keep-FIRST; also added/removed columns",
        date_field="snapshot_date",
        date_min=snap_min,
        date_max=snap_max,
        n_tickers=int(df["ticker"].nunique()),
        n_themes=int(df["basket_id"].nunique()),
        pit_class="PIT_HONEST",
        universe_coverage_ever=snap_ever,
        coverage_by_year=snap_year,
        n_membership_rows=int(len(df)),
        n_univ_tickers_ever=snap_n_ever,
        n_univ_tickers_by_year=snap_n_year,
        added_date_min=dmin,
        added_date_max=dmax,
        added_universe_coverage_ever=ever,
        added_coverage_by_year=by_year,
        added_n_univ_tickers_ever=n_ever,
        added_n_univ_tickers_by_year=n_by_year,
        n_added_eq_seed_2023_05_09=int((df["added"].map(iso_day) == "2023-05-09").sum()),
        snapshot_counts=snap_counts,
        classes={
            "snapshot_date": {
                "pit_class": "PIT_HONEST",
                "cite": [
                    "engine/basket_membership_pit.py:16-18",
                    "engine/basket_membership_pit.py:99",
                ],
                "cite_text": {
                    "16-18": (
                        "one row per (snapshot_date, basket_id, ticker), keep-FIRST on that key "
                        "so a re-run on the same day can never duplicate or rewrite a stamped day"
                    ),
                    "99": "SUITE_US = \"baskets\"",
                },
                "carry_forward": (
                    "membership in force at D is the newest snapshot_date <= D "
                    "(engine/basket_membership_pit.py:33)"
                ),
            },
            "added": {
                "pit_class": "BACKFILLED",
                "reason": (
                    "added is dominated by the 2023-05-09 seed constant; memberships are "
                    "applied to dates before the snapshots that recorded them"
                ),
            },
        },
        pit_class_field="snapshot_date (honest) vs added (backfilled)",
        pit_class_reason=(
            "snapshot_date is the PIT tape (keep-FIRST; SUITE_US=baskets). added is BACKFILLED. "
            "Headline pit_class for this artifact is PIT_HONEST because the load-bearing clock "
            "is snapshot_date. Q2 year table uses snapshot_date (all mass in 2026)."
        ),
        listed_in_required_inputs=False,
        honest_clock="snapshot_date",
        honest_start=snap_min,
        backfilled_clock="added",
    )


def census_leading_theme_join(root: Path, universe: set[str], membership: dict) -> dict:
    """Join context_history theme ids to membership_history by basket_id.

    Two classes:
      snapshot_date-honest: carry newest snapshot_date <= D
      added-backfilled: added <= D and (removed is null or removed > D), from latest snapshot rows
    """
    rel_ctx = "data/themes/context_history.jsonl"
    rel_mh = "data/baskets/membership_history.parquet"
    rows, n_fail = load_jsonl(root / rel_ctx)
    mh = pd.read_parquet(root / rel_mh)
    mh = mh.copy()
    mh["ticker"] = mh["ticker"].astype(str).str.upper()
    mh["basket_id"] = mh["basket_id"].astype(str)
    snap_dates = sorted({d for d in (iso_day(x) for x in mh["snapshot_date"].tolist()) if d})
    by_snap_basket: dict[str, dict[str, set[str]]] = {}
    by_snap_names: dict[str, set[str]] = {}
    for snap in snap_dates:
        g = mh[mh["snapshot_date"].map(iso_day) == snap]
        baskets: dict[str, set[str]] = defaultdict(set)
        names: set[str] = set()
        for b, t in zip(g["basket_id"].tolist(), g["ticker"].tolist()):
            baskets[b].add(t)
            names.add(t)
        by_snap_basket[snap] = dict(baskets)
        by_snap_names[snap] = names
    latest = snap_dates[-1]
    gL = mh[mh["snapshot_date"].map(iso_day) == latest]
    added_rows = []
    for b, t, a, r in zip(
        gL["basket_id"].tolist(),
        gL["ticker"].tolist(),
        gL["added"].tolist(),
        gL["removed"].tolist(),
    ):
        added_rows.append((b, t, iso_day(a), iso_day(r)))

    ctx = []
    theme_ids: set[str] = set()
    for r in rows:
        asof = iso_day(r.get("asof"))
        if not asof:
            continue
        labels = r.get("labels") or {}
        if not isinstance(labels, dict):
            labels = {}
        labs = {str(k): v for k, v in labels.items()}
        theme_ids.update(labs)
        ctx.append(
            {
                "asof": asof,
                "labels": labs,
                "trailing_leader_id": r.get("trailing_leader_id"),
                "leadership_state": r.get("leadership_state"),
            }
        )
    ctx.sort(key=lambda x: x["asof"])
    basket_ids = set(mh["basket_id"].tolist())
    n = len(universe)

    def snap_at(d: str) -> tuple[str | None, dict[str, set[str]]]:
        el = [s for s in snap_dates if s <= d]
        if not el:
            return None, {}
        s = el[-1]
        return s, by_snap_basket[s]

    def added_at(d: str) -> dict[str, set[str]]:
        out: dict[str, set[str]] = defaultdict(set)
        for b, t, a, r in added_rows:
            if a and a <= d and (r is None or r > d):
                out[b].add(t)
        return dict(out)

    def ctx_at(d: str) -> dict | None:
        cands = [c for c in ctx if c["asof"] <= d]
        return cands[-1] if cands else None

    def cov(themes: set[str], byb: dict[str, set[str]]) -> tuple[int, float, int]:
        names: set[str] = set()
        for t in themes:
            names |= byb.get(t, set())
        in_u = names & universe
        return len(in_u), frac(len(in_u), n), len(themes)

    eval_dates = sorted(set(c["asof"] for c in ctx) | set(snap_dates) | {"2026-08-07"})
    per_date = []
    for d in eval_dates:
        c = ctx_at(d)
        labels = c["labels"] if c else {}
        lead = {k for k, v in labels.items() if v in LEADING_LABELS}
        all_th = set(labels)
        leader = {c["trailing_leader_id"]} if c and c.get("trailing_leader_id") else set()
        snap, snap_by = snap_at(d)
        add_by = added_at(d)
        hon_all_n, hon_all_f, n_all = cov(all_th, snap_by)
        hon_lead_n, hon_lead_f, n_lead = cov(lead, snap_by)
        hon_ldr_n, hon_ldr_f, _ = cov(leader, snap_by)
        bf_all_n, bf_all_f, _ = cov(all_th, add_by)
        bf_lead_n, bf_lead_f, _ = cov(lead, add_by)
        per_date.append(
            {
                "date": d,
                "ctx_asof": c["asof"] if c else None,
                "snapshot_date_used": snap,
                "n_labeled_themes": n_all,
                "n_leading_themes_dominant_emerging": n_lead,
                "trailing_leader_id": c.get("trailing_leader_id") if c else None,
                "snapshot_honest_all49_n": hon_all_n,
                "snapshot_honest_all49_coverage": hon_all_f,
                "snapshot_honest_leading_n": hon_lead_n,
                "snapshot_honest_leading_coverage": hon_lead_f,
                "snapshot_honest_leader_n": hon_ldr_n,
                "snapshot_honest_leader_coverage": hon_ldr_f,
                "added_backfilled_all49_n": bf_all_n,
                "added_backfilled_all49_coverage": bf_all_f,
                "added_backfilled_leading_n": bf_lead_n,
                "added_backfilled_leading_coverage": bf_lead_f,
            }
        )

    honest_rows = [r for r in per_date if r["snapshot_date_used"]]
    honest_start = honest_rows[0]["date"] if honest_rows else None
    min_all = min((r["snapshot_honest_all49_coverage"] for r in honest_rows), default=0.0)
    max_all = max((r["snapshot_honest_all49_coverage"] for r in honest_rows), default=0.0)
    min_lead = min((r["snapshot_honest_leading_coverage"] for r in honest_rows), default=0.0)
    max_lead = max((r["snapshot_honest_leading_coverage"] for r in honest_rows), default=0.0)
    min_all_row = min(honest_rows, key=lambda r: r["snapshot_honest_all49_coverage"]) if honest_rows else None
    min_lead_row = min(honest_rows, key=lambda r: r["snapshot_honest_leading_coverage"]) if honest_rows else None

    return {
        "path_context": rel_ctx,
        "path_membership": rel_mh,
        "grain": "asof x (theme_id = basket_id) x ticker, membership carried from snapshot_date <= asof",
        "n_context_theme_ids": len(theme_ids),
        "n_basket_ids": len(basket_ids),
        "n_theme_ids_matching_basket_ids": len(theme_ids & basket_ids),
        "theme_ids_not_in_baskets": sorted(theme_ids - basket_ids),
        "basket_ids_not_in_context": sorted(basket_ids - theme_ids),
        "parse_failures": n_fail,
        "leading_label_values": sorted(LEADING_LABELS),
        "snapshot_date_pit_class": "PIT_HONEST",
        "added_pit_class": "BACKFILLED",
        "snapshot_date_cite": [
            "engine/basket_membership_pit.py:16-18",
            "engine/basket_membership_pit.py:99",
        ],
        "honest_start": honest_start,
        "honest_end": ctx[-1]["asof"] if ctx else None,
        "min_snapshot_honest_all49_coverage": min_all,
        "max_snapshot_honest_all49_coverage": max_all,
        "min_snapshot_honest_leading_coverage": min_lead,
        "max_snapshot_honest_leading_coverage": max_lead,
        "min_snapshot_honest_all49_row": min_all_row,
        "min_snapshot_honest_leading_row": min_lead_row,
        "membership_snapshot_counts": membership.get("snapshot_counts"),
        "per_date": per_date,
        "iso_week_leading_restricted": iso_week_leading_table(
            per_date, year=2026, weeks=range(33, 41), honest_start=honest_start
        ),
        "note": (
            "context_history theme ids match the 49 US basket ids exactly. "
            "snapshot-honest coverage is 0 before the first snapshot_date "
            f"({snap_dates[0] if snap_dates else None}). added-backfilled coverage is "
            "available from baskets membership_published_at (2026-08-07) but is look-ahead "
            "relative to snapshot_date. 'all49' = every labeled theme; 'leading' = labels "
            "in {dominant, emerging}."
        ),
    }


def load_tree_members_by_asof(root: Path) -> dict[str, set[str]]:
    rows, _ = load_jsonl(root / "data/themes_heatmap/tree_history.jsonl")
    out: dict[str, set[str]] = {}
    for r in rows:
        asof = iso_day(r.get("asof"))
        if asof:
            out[asof] = _tree_members(r)
    return out


def compute_honest_window(
    root: Path,
    universe: set[str],
    sources: list[dict],
    extra: dict,
    join: dict,
) -> dict:
    """Single computation of D*, E*, per-source starts, weeks, min per-date coverage."""
    by_name = {s["name"]: s for s in sources}
    meta = by_name["theme_graph_meta"]
    tree = by_name["themes_heatmap_tree_history"]
    edges = by_name["theme_graph_edges"]
    n = len(universe)

    tree_start = tree.get("honest_start") or tree.get("date_min")
    snap_start = extra.get("honest_start") or extra.get("date_min")
    honest_starts = [d for d in (tree_start, snap_start) if d]
    # DSTAR_FROM_TREE_AND_SNAPSHOT_ONLY: edges observed dates do not set D*
    d_star = min(honest_starts) if honest_starts else None
    e_star = meta.get("date_min")  # belief_time of current sidecar

    tree_members = load_tree_members_by_asof(root)
    tree_asofs = sorted(tree_members)
    snap_names = load_snapshot_names(root)
    snap_dates = sorted(snap_names)

    def in_force(d: str) -> set[str]:
        names = honest_in_force_names(d, universe, tree_members, snap_names)
        # IN_FORCE_TREE_AND_SNAPSHOT_ONLY: do not union membership_history.added or edges
        return names

    change_points = sorted(set(tree_asofs) | set(snap_dates) | ({e_star} if e_star else set()))
    change_points = [d for d in change_points if d_star and d >= d_star]
    per_date = []
    for d in change_points:
        names = in_force(d)
        t_el = [a for a in tree_asofs if a <= d]
        s_el = [a for a in snap_dates if a <= d]
        per_date.append(
            {
                "date": d,
                "n_univ_tickers": len(names),
                "coverage": frac(len(names), n),
                "tree_asof_used": t_el[-1] if t_el else None,
                "snapshot_date_used": s_el[-1] if s_el else None,
                "n_tree_univ": len((tree_members[t_el[-1]] & universe) if t_el else set()),
                "n_snapshot_univ": len((snap_names[s_el[-1]] & universe) if s_el else set()),
            }
        )
    min_row = min(per_date, key=lambda r: r["coverage"]) if per_date else None
    max_row = max(per_date, key=lambda r: r["coverage"]) if per_date else None
    min_cov = min_row["coverage"] if min_row else 0.0
    union_max_ever = max(
        float(tree.get("universe_coverage_ever") or 0.0),
        float(edges.get("universe_coverage_ever") or 0.0),
        float(extra.get("universe_coverage_ever") or 0.0),
    )
    if min_cov >= 0.5:
        verdict = "PIT_AVAILABLE"
    elif min_cov > 0:
        verdict = "PIT_PARTIAL"
    else:
        verdict = "PIT_UNAVAILABLE"

    per_source = []
    for s in sources:
        per_source.append(
            {
                "name": s["name"],
                "path": s["path"],
                "honest_clock": s.get("honest_clock") or s.get("date_field"),
                "honest_start": s.get("honest_start"),
                "date_min": s.get("date_min"),
                "date_max": s.get("date_max"),
                "pit_class": s["pit_class"],
                "weeks_own_span": weeks_between(s.get("date_min"), s.get("date_max")),
                "weeks_start_to_Estar": weeks_between(s.get("honest_start") or s.get("date_min"), e_star),
            }
        )
    per_source.append(
        {
            "name": extra["name"],
            "path": extra["path"],
            "honest_clock": "snapshot_date",
            "honest_start": extra.get("honest_start"),
            "date_min": extra.get("date_min"),
            "date_max": extra.get("date_max"),
            "pit_class": extra["pit_class"],
            "weeks_own_span": weeks_between(extra.get("date_min"), extra.get("date_max")),
            "weeks_start_to_Estar": weeks_between(extra.get("honest_start"), e_star),
            "backfilled_clock": "added",
            "added_min": extra.get("added_date_min"),
            "added_max": extra.get("added_date_max"),
        }
    )
    per_source.append(
        {
            "name": "leading_theme_join",
            "path": join["path_context"] + " x " + join["path_membership"],
            "honest_clock": "context.asof + membership.snapshot_date (carry-forward)",
            "honest_start": join.get("honest_start"),
            "date_min": join.get("honest_start"),
            "date_max": join.get("honest_end"),
            "pit_class": "PIT_HONEST",
            "weeks_own_span": weeks_between(join.get("honest_start"), join.get("honest_end")),
            "weeks_start_to_Estar": weeks_between(join.get("honest_start"), e_star),
        }
    )

    observed_clock_start = d_star
    belief_dates = [r["date"] for r in (edges.get("per_date_belief_time") or [])]
    belief_clock_start = min(belief_dates) if belief_dates else edges.get("belief_time_min")

    return {
        "rule": HONEST_WINDOW_RULE,
        "start": d_star,
        "end": e_star,
        "weeks_observed_clock": weeks_between(observed_clock_start, e_star),
        "weeks_belief_clock": weeks_between(belief_clock_start, e_star),
        "observed_clock_start": observed_clock_start,
        "belief_clock_start": belief_clock_start,
        "per_source": per_source,
        "change_points": per_date,
        "min_per_date_from_honest_start": min_cov,
        "min_per_date_row": min_row,
        "max_per_date_from_honest_start": max_row["coverage"] if max_row else 0.0,
        "max_per_date_row": max_row,
        "union_max_ever": union_max_ever,
        "union_max_ever_components": {
            "tree_history": tree.get("universe_coverage_ever"),
            "edges_evidence_time": edges.get("universe_coverage_ever"),
            "membership_snapshot_date": extra.get("universe_coverage_ever"),
        },
        "grading_metric": "min_per_date_from_honest_start",
        "previous_grading_metric": "union_max_ever",
        "threshold": 0.5,
        "verdict": verdict,
        "tree_per_asof": tree.get("per_asof") or [],
        "leading_theme_honest_start": join.get("honest_start"),
        "leading_theme_min_all49": join.get("min_snapshot_honest_all49_coverage"),
        "leading_theme_min_leading": join.get("min_snapshot_honest_leading_coverage"),
        "edges_headline_per_date_belief": edges.get("headline_per_date_coverage"),
        "edges_headline_per_date_belief_n": edges.get("headline_per_date_n"),
        "edges_headline_per_date_belief_date": edges.get("headline_per_date_date"),
        "edges_union_ever": edges.get("union_ever_coverage"),
        "in_force_sources": [
            "tree_history.asof",
            "membership_history.snapshot_date",
        ],
        "in_force_excludes": [
            "membership_history.added",
            "theme_graph_edges",
        ],
        "in_force_semantics": (
            "union of universe names on the last tree_history.asof <= D and the last "
            "membership_history.snapshot_date <= D. added and edges never enter."
        ),
        "justification": (
            f"{verdict}: D*={d_star} E*={e_star}. "
            f"min per-date honest in-force coverage from D* onward is "
            f"{min_row['n_univ_tickers'] if min_row else 0}/{n}="
            f"{min_cov:.6f} on {min_row['date'] if min_row else None} "
            f"(tree_asof={min_row.get('tree_asof_used') if min_row else None}, "
            f"snapshot={min_row.get('snapshot_date_used') if min_row else None}). "
            f"union_max_ever (previous metric) is {union_max_ever:.6f}. "
            f"edges belief_time dated-that-day max is "
            f"{edges.get('headline_per_date_n')}/{n}="
            f"{float(edges.get('headline_per_date_coverage') or 0):.6f} on "
            f"{edges.get('headline_per_date_date')} but every edges sub-source is BACKFILLED. "
            f"leading-theme join (snapshot-honest, all 49 baskets) starts "
            f"{join.get('honest_start')} near "
            f"{float(join.get('min_snapshot_honest_all49_coverage') or 0):.6f}. "
            f"Neither min-per-date nor union-ever is >= 0.50. 2014-2025 honest coverage is 0."
        ),
    }


def derive_repo_claims(root: Path) -> list[dict]:
    """Re-derive every matches_disk cell from files on disk. Command stored per cell."""
    ev = pd.read_parquet(root / "data/theme_graph/evidence.parquet")
    nodes = pd.read_parquet(root / "data/theme_graph/nodes.parquet")
    edges = pd.read_parquet(root / "data/theme_graph/edges.parquet")
    meta = json.loads((root / "data/theme_graph/_meta.json").read_text(encoding="utf-8"))
    schema = json.loads(
        (root / "contracts/biocatalyst/biocatalyst_theme_rollup_pit.v1.schema.json").read_text(
            encoding="utf-8"
        )
    )
    us_mo = edges[(edges["type"] == "MEMBER_OF") & edges["src"].astype(str).str.startswith("co:us:")]
    seed_n = int((us_mo["date_provenance"].astype(str) == "seed_constant").sum())
    prov_n = int(us_mo["date_provenance"].nunique()) if len(us_mo) else 0
    company_birth = int(
        nodes.loc[nodes["kind"] == "company", "birth_date"].notna().sum()
    ) if "kind" in nodes.columns else None
    local_birth = int(
        nodes.loc[nodes["kind"] == "local_theme", "birth_date"].notna().sum()
    ) if "kind" in nodes.columns else None
    pub_ne = int(
        sum(
            iso_day(a) != iso_day(b)
            for a, b in zip(ev["published_at"].tolist(), ev["computed_at"].tolist())
        )
    )
    has_ticker_col = any(c.lower() in {"ticker", "symbol"} for c in ev.columns)
    coverage_const = ((schema.get("properties") or {}).get("coverage_class") or {}).get("const")
    pit_const = ((schema.get("properties") or {}).get("pit_key_policy") or {}).get("const")
    memb_auth = ((schema.get("properties") or {}).get("membership_authority") or {}).get("const")
    seed_meta = ((meta.get("per_suite") or {}).get("baskets") or {}).get("seed_constant")
    desc = schema.get("description") or ""

    specs = [
        {
            "file": "engine/theme_graph/membership_evidence.py",
            "snippet": "Original proposal evidence has its own creation clock",
            "disk_command": (
                "python3 -c \"import pandas as pd; "
                "df=pd.read_parquet('data/theme_graph/evidence.parquet'); "
                "print(sorted(df.columns)); print(len(df)); "
                "print(df[['published_at','computed_at']].head(3).to_string()); "
                "print((df['published_at'].astype(str).str[:10] != df['computed_at'].astype(str).str[:10]).sum())\""
            ),
            "disk_result": (
                f"evidence.parquet n={len(ev)} cols include published_at and computed_at; "
                f"{pub_ne}/{len(ev)} rows have published_at day != computed_at day; "
                f"ticker_col={has_ticker_col}"
            ),
            "inprocess_matches": bool("published_at" in ev.columns and pub_ne > 0 and not has_ticker_col),
            "disk_match_needles": ["published_at", "computed_at"],
            "note": (
                "Claim is that original proposal evidence has its own creation clock and is "
                "not recomputed historical evidence. Disk: published_at is a distinct source "
                "clock from computed_at; 22 receipts, no ticker column. matches_disk=true. "
                "Round-0 false was a misread that asked whether this is a B1 membership tape."
            ),
        },
        {
            "file": "engine/theme_graph/membership_evidence.py",
            "snippet": "Same-vintage comparability is not established",
            "disk_command": (
                "python3 -c \"import pandas as pd; "
                "df=pd.read_parquet('data/theme_graph/edges.parquet'); "
                "us=df[(df.type=='MEMBER_OF') & df.src.astype(str).str.startswith('co:us:')]; "
                "print(us['date_provenance'].value_counts().to_dict())\""
            ),
            "disk_result": (
                f"US MEMBER_OF date_provenance nunique={prov_n} "
                f"counts={us_mo['date_provenance'].value_counts().sort_index().to_dict() if len(us_mo) else {}}"
            ),
            "inprocess_matches": prov_n > 1,
            "disk_match_needles": ["raw_snapshot"],
            "note": "Mixed date_provenance on disk; same-vintage comparability is not automatic.",
        },
        {
            "file": "engine/biocatalyst/theme_rollup_pit.py",
            "snippet": "A snapshot contributes to an ``as_of`` rollup only when its",
            "disk_command": (
                "python3 -c \"import json; "
                "s=json.load(open('contracts/biocatalyst/biocatalyst_theme_rollup_pit.v1.schema.json')); "
                "print(s['properties']['pit_key_policy'])\""
            ),
            "disk_result": f"schema properties.pit_key_policy.const={pit_const!r}",
            "inprocess_matches": pit_const == "knowledge_cutoff_at_or_before_as_of",
            "disk_match_needles": ["knowledge_cutoff_at_or_before_as_of"],
            "note": (
                "Adapter PIT law is on disk as schema const knowledge_cutoff_at_or_before_as_of. "
                "No BioCatalyst rollup in the D0 sources binds B1 names to themes."
            ),
        },
        {
            "file": "engine/biocatalyst/theme_rollup_pit.py",
            "snippet": "Theme membership arrives as",
            "disk_command": (
                "python3 -c \"import json; "
                "s=json.load(open('contracts/biocatalyst/biocatalyst_theme_rollup_pit.v1.schema.json')); "
                "print(s['properties']['membership_authority']); print(s['description'][:180])\""
            ),
            "disk_result": (
                f"membership_authority.const={memb_auth!r}; schema description forbids "
                f"security join: {'no issuer, ticker' in desc or 'carries no issuer, ticker' in desc}"
            ),
            "inprocess_matches": memb_auth == "reviewed_modality_config_only",
            "disk_match_needles": ["reviewed_modality_config_only"],
            "note": "Membership authority is a reviewed NCT-modality binding, not a stock ticker.",
        },
        {
            "file": "agentos/handoffs/GMI-THEME-GRAPH-2026-08-27-d2c-pit-vintage-commission.md",
            "snippet": "No backfilled discovery date inferred from present membership.",
            "disk_command": (
                "python3 -c \"import pandas as pd; "
                "n=pd.read_parquet('data/theme_graph/nodes.parquet'); "
                "print(n.groupby('kind')['birth_date'].apply(lambda s: int(s.notna().sum())).to_dict()); "
                "print(sorted(n.loc[n.kind=='local_theme','birth_date'].dropna().astype(str).unique().tolist()))\""
            ),
            "disk_result": (
                f"company birth_date nonnull={company_birth}; local_theme birth_date nonnull={local_birth} "
                f"(values {sorted(nodes.loc[nodes['kind']=='local_theme','birth_date'].dropna().astype(str).unique().tolist())})"
            ),
            "inprocess_matches": company_birth == 0,
            "disk_match_needles": ["'company': 0"],
            "note": (
                "Commission forbids inferring a discovery date from present membership. "
                "Disk: company/basket/theme/etf birth_date is null (not inferred). local_theme "
                "birth_date is the Finviz vintage dates, not company membership. seed_constant "
                "is a valid_from reconstruction (separate claim at line 95), not a discovery date. "
                "Round-0 false was a misread that conflated seed_constant valid_from with discovery/birth."
            ),
        },
        {
            "file": "agentos/handoffs/GMI-THEME-GRAPH-2026-08-27-d2c-pit-vintage-commission.md",
            "snippet": "remains a reconstruction convention, never observation proof.",
            "disk_command": (
                "python3 -c \"import json,pandas as pd; "
                "m=json.load(open('data/theme_graph/_meta.json')); "
                "e=pd.read_parquet('data/theme_graph/edges.parquet'); "
                "us=e[(e.type=='MEMBER_OF') & e.src.astype(str).str.startswith('co:us:')]; "
                "print(m['per_suite']['baskets']['seed_constant']); "
                "print(int((us.date_provenance.astype(str)=='seed_constant').sum()))\""
            ),
            "disk_result": (
                f"_meta per_suite.baskets.seed_constant={seed_meta!r}; "
                f"US MEMBER_OF seed_constant rows={seed_n}"
            ),
            "inprocess_matches": seed_n > 0 and seed_meta == "2023-05-09",
            "disk_match_needles": ["2023-05-09"],
            "note": "seed_constant is present on disk as a reconstruction convention.",
        },
        {
            "file": "contracts/biocatalyst/biocatalyst_theme_rollup_pit.v1.schema.json",
            "snippet": '"coverage_class": {"const": "current_only"}',
            "disk_command": (
                "python3 -c \"import json; "
                "s=json.load(open('contracts/biocatalyst/biocatalyst_theme_rollup_pit.v1.schema.json')); "
                "print(s['properties']['coverage_class'])\""
            ),
            "disk_result": f"coverage_class.const={coverage_const!r}",
            "inprocess_matches": coverage_const == "current_only",
            "disk_match_needles": ["current_only"],
            "note": "Schema declares current_only coverage.",
        },
        {
            "file": "contracts/biocatalyst/biocatalyst_theme_rollup_pit.v1.schema.json",
            "snippet": '"pit_key_policy": {"const": "knowledge_cutoff_at_or_before_as_of"}',
            "disk_command": (
                "python3 -c \"import json; "
                "s=json.load(open('contracts/biocatalyst/biocatalyst_theme_rollup_pit.v1.schema.json')); "
                "print(s['properties']['pit_key_policy'])\""
            ),
            "disk_result": f"pit_key_policy.const={pit_const!r}",
            "inprocess_matches": pit_const == "knowledge_cutoff_at_or_before_as_of",
            "disk_match_needles": ["knowledge_cutoff_at_or_before_as_of"],
            "note": "PIT key is trial knowledge_cutoff, not ticker-theme membership.",
        },
    ]
    out = []
    for spec in specs:
        line, quote = find_quote(root, spec["file"], spec["snippet"])
        ran = run_disk_command(root, spec["disk_command"])
        needles = spec.get("disk_match_needles") or []
        derived = all(n in ran for n in needles) if needles else False
        out.append(
            {
                "file": spec["file"],
                "line": line,
                "quote": quote,
                "matches_disk": bool(derived),
                "matches_disk_inprocess": bool(spec.get("inprocess_matches")),
                "disk_command": spec["disk_command"],
                "disk_result": ran,
                "disk_result_interpreted": spec["disk_result"],
                "disk_match_needles": needles,
                "note": spec["note"],
            }
        )
    return out


def run_disk_command(root: Path, cmd: str) -> str:
    proc = subprocess.run(
        cmd,
        shell=True,
        cwd=root,
        capture_output=True,
        text=True,
        timeout=120,
    )
    out = (proc.stdout or "").strip()
    err = (proc.stderr or "").strip()
    if proc.returncode != 0:
        return f"rc={proc.returncode} stdout={out[:2000]} stderr={err[:500]}"
    return re.sub(r"\s+", " ", out)[:4000]


def snapshot_query_to_write_time(rec: dict | None) -> dict:
    rec = rec or {}
    return {
        "path": rec.get("path"),
        "command": f"gh api {rec.get('endpoint')}" if rec.get("endpoint") else None,
        "endpoint": rec.get("endpoint"),
        "until": rec.get("until"),
        "ok": bool(rec.get("ok")),
        "error": rec.get("stderr") if not rec.get("ok") else None,
        "commits": [
            {"sha": c.get("sha"), "date": c.get("date"), "msg": c.get("msg")}
            for c in (rec.get("commits") or [])
        ],
    }


def collect_write_time_commits(root: Path | None = None) -> dict:
    """I2: read gh_evidence.json only. No network. Tests pass with fake `gh`."""
    root = root or find_root()
    ev = load_gh_evidence(root)
    if not ev:
        empty = {
            "path": None,
            "command": None,
            "endpoint": None,
            "until": None,
            "ok": False,
            "error": "gh_evidence.json missing",
            "commits": [],
        }
        return {
            "tree_history": dict(empty),
            "membership_history": dict(empty),
            "context_history_latest5": dict(empty),
            "context_history_first": dict(empty),
            "source": "missing",
            "note": "Write-time commit evidence unavailable.",
        }
    queries = ev.get("queries") or {}
    out = {
        "tree_history": snapshot_query_to_write_time(queries.get("tree_history")),
        "membership_history": snapshot_query_to_write_time(queries.get("membership_history")),
        "context_history_latest5": snapshot_query_to_write_time(
            queries.get("context_history_latest5")
        ),
        "context_history_first": snapshot_query_to_write_time(
            queries.get("context_history_first")
        ),
        "source": str(gh_evidence_path(root).relative_to(root)),
        "until_repo_head_committer_date": ev.get("until_repo_head_committer_date"),
        "snapshot_repo_head": ev.get("repo_head"),
    }
    out["note"] = write_time_note_from_evidence(out)
    return out


def leadership_artifacts(sources: list[dict]) -> list[dict]:
    by_path = {s["path"]: s for s in sources}
    wanted = [
        "data/neuralweb/theme_phase_history.jsonl",
        "data/themes/context_history.jsonl",
        "data/themes/context_history_cn.jsonl",
        "data/themes_heatmap/subsector_perf_history.jsonl",
    ]
    out = []
    for path in wanted:
        s = by_path[path]
        out.append(
            {
                "path": path,
                "grain": s["grain"],
                "date_min": s["date_min"],
                "date_max": s["date_max"],
                "pit_class": s["pit_class"],
            }
        )
    out.append(
        {
            "path": "data/neuralweb/theme_state.json",
            "grain": "current 18-theme state snapshot (foresight/radar/basket_ids); as_of only",
            "date_min": "2026-10-03",
            "date_max": "2026-10-03",
            "pit_class": "BACKFILLED",
            "note": "grep-found current snapshot, not a history tape; as_of=2026-10-03",
        }
    )
    return out


GREP_OPENED_PATHS = [
    "engine/theme_graph/store.py",
    "engine/theme_graph/materialize.py",
    "engine/theme_graph/local_sources.py",
    "engine/theme_graph/membership_evidence.py",
    "engine/theme_graph/identity_resolution.py",
    "engine/biocatalyst/theme_rollup_pit.py",
    "engine/theme_alerts.py",
    "engine/theme_clinical.py",
    "engine/basket_membership_pit.py",
    "data/baskets/membership_history.parquet",
    "data/neuralweb/theme_state.json",
    "data/themes/state.json",
]

GREP_ONLY_NAMED_PATHS = [
    "engine/theme_placebo.py",
    "engine/theme_extension.py",
    "engine/theme_discovery.py",
    "engine/theme_scoring.py",
    "engine/theme_crowding.py",
    "engine/theme_context.py",
    "engine/theme_emergence.py",
    "engine/neuralweb/theme_thesis.py",
    "engine/neuralweb/thematic_state.py",
    "engine/neuralweb/factor_contradictions.py",
    "engine/neuralweb/earnings_context_reader.py",
    "data/theme_graph/probation/proposals.jsonl",
    "data/baskets/membership.json",
    "data/themes_heatmap/themes_tree.json",
    "data/themes_heatmap/perf_snapshot.json",
]


def touch_opened_inputs(root: Path) -> list[str]:
    """I5: actually open every path grep_census claims as opened."""
    opened = []
    for rel in GREP_OPENED_PATHS:
        path = root / rel
        if path.is_file():
            path.read_bytes()
            opened.append(rel)
    return opened


def grep_census() -> dict:
    return {
        "searched": [
            "engine/theme_graph/",
            "engine/theme_*.py",
            "engine/neuralweb/",
        ],
        "terms": ["belief_time", "as_of", "published_at", "first_seen", "vintage", "leader", "phase"],
        "opened": list(GREP_OPENED_PATHS),
        "found_not_opened": list(GREP_ONLY_NAMED_PATHS),
        "grep_only_named_paths": list(GREP_ONLY_NAMED_PATHS),
        "note": (
            "store.py claims append-only bitemporal edges with latest-belief collapse; "
            "materialize.py labels backfill era=reconstruction and seed_constant as not "
            "when a company joined; local_sources.py defines Finviz as a snapshot ladder "
            "with valid_from=first observed. basket_membership_pit.py:16-18 and :99 make "
            "snapshot_date the PIT-honest US tape; added is backfilled. "
            "I5: grep_only_named_paths are named in census.py but never opened "
            "(not hashed as inputs)."
        ),
    }


def git_head(root: Path) -> str:
    proc = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    return proc.stdout.strip()


def strip_private(obj):
    if isinstance(obj, dict):
        return {k: strip_private(v) for k, v in obj.items() if not str(k).startswith("_")}
    if isinstance(obj, list):
        return [strip_private(x) for x in obj]
    return obj


def build_repair_items() -> tuple[list[dict], list[dict], list[dict]]:
    """I4: every file:line is inspect.getsourcelines / symbol search at write time."""
    r1 = [
        {"id": 1, "status": "FIXED", "where": format_cites(cite_assign("HONEST_WINDOW_RULE"), cite_function(compute_honest_window), cite_function(render_result_md))},
        {"id": 2, "status": "FIXED", "where": format_cites(cite_function(_subsource_pit_class), cite_function(census_edges))},
        {"id": 3, "status": "FIXED", "where": format_cites(cite_function(census_membership_history), cite_function(census_leading_theme_join))},
        {"id": 4, "status": "FIXED", "where": format_cites(cite_function(compute_honest_window)) + " grading_metric=min_per_date_from_honest_start"},
        {"id": 5, "status": "FIXED", "where": format_cites(cite_function(derive_repo_claims))},
        {"id": 6, "status": "FIXED", "where": format_cites(cite_function(render_result_md)) + " Data law section"},
        {"id": 7, "status": "ANSWERED", "where": format_cites(cite_function(census_tree_history)) + "; engine/theme_graph/local_sources.py:8-18"},
        {"id": 8, "status": "ANSWERED", "where": format_cites(cite_function(render_result_md)) + " seat weeks table"},
    ]
    r2 = [
        {"id": "H1", "status": "FIXED", "where": format_cites(cite_function(honest_in_force_names), cite_function(compute_honest_window), cite_function(_mutate_m1), cite_test("test_honest_change_points_pinned"), cite_test("test_d_star_is_exactly_2026_07_05"), cite_test("test_in_force_from_tree_and_snapshot_only"))},
        {"id": "H2", "status": "FIXED", "where": format_cites(cite_function(write_hashes), cite_function(main)) + " last write is write_hashes"},
        {"id": "H3", "status": "FIXED", "where": format_cites(cite_function(main)) + " folds pytest_summary then render_result_md"},
        {"id": "H4", "status": "FIXED", "where": format_cites(cite_function(collect_write_time_commits), cite_function(census_tree_history), cite_function(tree_pit_class_reason_from_commits))},
        {"id": "H5", "status": "FIXED", "where": format_cites(cite_assign("PER_DATE_IN_FORCE_SEMANTICS"), cite_function(census_edges))},
        {"id": "H6", "status": "FIXED", "where": format_cites(cite_function(run_disk_command), cite_function(iso_week_leading_table)) + "; local_sources.py:8-18 quoted in census_tree_history"},
    ]
    r3 = [
        {"id": "I1", "status": "FIXED", "where": format_cites(cite_assign("CONTEXT_HISTORY_FIRST_WRITE"), cite_function(census_context))},
        {"id": "I2", "status": "FIXED", "where": format_cites(cite_function(ensure_gh_evidence), cite_function(collect_write_time_commits), cite_function(load_gh_evidence))},
        {"id": "I3", "status": "FIXED", "where": format_cites(cite_function(tree_pit_class_reason_from_commits), cite_test("test_tree_pit_class_reason_unavailable_without_evidence"))},
        {"id": "I4", "status": "FIXED", "where": format_cites(cite_function(cite_function), cite_function(build_repair_items), cite_test("test_repair_item_cites_contain_symbol"))},
        {"id": "I5", "status": "FIXED", "where": format_cites(cite_assign("CENSUS_READ_TARGETS"), cite_assign("GREP_ONLY_NAMED_PATHS"), cite_function(touch_opened_inputs))},
        {"id": "I6", "status": "FIXED", "where": format_cites(cite_function(derive_repo_claims), cite_test("test_matches_disk_derived_from_disk_result"))},
        {"id": "I7", "status": "FIXED", "where": format_cites(cite_function(iso_week_leading_table), cite_test("test_iso_week_33_marked_before_honest_start"))},
        {"id": "I8", "status": "FIXED", "where": format_cites(cite_function(leaf_diff))},
    ]
    return r1, r2, r3


def frozen_guard(window: dict, join: dict, sources: list[dict]) -> dict:
    """Record before/after of seat-frozen leaves. Never rewrite the computed values."""
    by_cp = {r["date"]: r["n_univ_tickers"] for r in (window.get("change_points") or [])}
    honest_rows = [r for r in (join.get("per_date") or []) if r.get("snapshot_date_used")]
    min_lead = min(honest_rows, key=lambda r: r["snapshot_honest_leading_n"]) if honest_rows else {}
    max_lead = max(honest_rows, key=lambda r: r["snapshot_honest_leading_n"]) if honest_rows else {}
    ctx = next((s for s in sources if s["name"] == "themes_context_history"), {})
    observed = {
        "honest_window.start": window.get("start"),
        "honest_window.end": window.get("end"),
        "change_points.2026-07-05": by_cp.get("2026-07-05"),
        "change_points.2026-08-13": by_cp.get("2026-08-13"),
        "change_points.2026-08-15": by_cp.get("2026-08-15"),
        "change_points.2026-08-18": by_cp.get("2026-08-18"),
        "change_points.2026-09-04": by_cp.get("2026-09-04"),
        "change_points.2026-10-03": by_cp.get("2026-10-03"),
        "leading_restricted.min_n": min_lead.get("snapshot_honest_leading_n"),
        "leading_restricted.min_coverage": min_lead.get("snapshot_honest_leading_coverage"),
        "leading_restricted.min_date": min_lead.get("date"),
        "leading_restricted.max_n": max_lead.get("snapshot_honest_leading_n"),
        "leading_restricted.max_coverage": max_lead.get("snapshot_honest_leading_coverage"),
        "leading_restricted.max_date": max_lead.get("date"),
        "any_theme_union_ever": window.get("union_max_ever"),
    }
    moved = []
    for k, expected in FROZEN_LEAVES.items():
        got = observed.get(k)
        if got != expected:
            moved.append({"leaf": k, "expected": expected, "observed": got})
    iso = join.get("iso_week_leading_restricted") or []
    return {
        "expected": FROZEN_LEAVES,
        "observed": observed,
        "moved": moved,
        "n_moved": len(moved),
        "context_history_honest_start_before": ctx.get("honest_start_before_i1"),
        "context_history_honest_start_after": ctx.get("honest_start"),
        "iso_week_40": next((w for w in iso if w.get("iso_week") == 40), None),
        "iso_week_33_status": next((w.get("status") for w in iso if w.get("iso_week") == 33), None),
    }


def load_prior_result(root: Path, name: str) -> dict | None:
    path = results_dir(root) / "prior" / name
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def provenance_host() -> dict:
    versions = {"python": sys.version.split()[0], "executable": sys.executable}
    try:
        import numpy

        versions["numpy"] = numpy.__version__
    except Exception:
        versions["numpy"] = None
    try:
        import pyarrow

        versions["pyarrow"] = pyarrow.__version__
    except Exception:
        versions["pyarrow"] = None
    try:
        import scipy

        versions["scipy"] = scipy.__version__
    except Exception:
        versions["scipy"] = None
    try:
        import pytest

        versions["pytest"] = pytest.__version__
    except Exception:
        versions["pytest"] = None
    versions["pandas"] = pd.__version__
    return {
        "hostname": platform.node(),
        "platform": platform.platform(),
        "versions": versions,
        "rerun_notice": RERUN_NOTICE,
        "as_found_round2_result_json_sha256": ROUND2_RESULT_SHA256,
    }


def build_payload(root: Path | None = None) -> dict:
    root = root or find_root()
    universe_list, n_files, n_short = load_universe(root)
    universe = set(universe_list)
    universe_n = len(universe_list)
    write_time = collect_write_time_commits(root)
    touch_opened_inputs(root)

    parse_failures: dict[str, int] = {}
    sources: list[dict] = []

    sources.append(census_theme_graph_meta(root, universe))
    sources.append(census_nodes(root, universe))
    edges = census_edges(root, universe)
    sources.append(edges)
    sources.append(census_lifecycle(root, universe))
    sources.append(census_identity(root, universe))
    sources.append(census_capability(root, universe))
    sources.append(census_evidence(root, universe))

    phase, nfail = census_phase_history(root, universe)
    parse_failures[phase["path"]] = nfail
    sources.append(phase)

    ctx, nfail = census_context(
        root, universe, "data/themes/context_history.jsonl", "themes_context_history"
    )
    parse_failures[ctx["path"]] = nfail
    sources.append(ctx)

    ctx_cn, nfail = census_context(
        root, universe, "data/themes/context_history_cn.jsonl", "themes_context_history_cn"
    )
    parse_failures[ctx_cn["path"]] = nfail
    sources.append(ctx_cn)

    sub, nfail = census_subsector_perf(root, universe)
    parse_failures[sub["path"]] = nfail
    sources.append(sub)

    tree, nfail = census_tree_history(root, universe)
    tree["pit_class_reason"] = tree_pit_class_reason_from_commits(write_time)
    parse_failures[tree["path"]] = nfail
    sources.append(tree)

    sources.append(census_program_ledger(root, universe))
    sources.append(census_phase0(root, universe))

    extra = census_membership_history(root, universe)
    join = census_leading_theme_join(root, universe, extra)
    window = compute_honest_window(root, universe, sources, extra, join)
    r1_items, r2_items, r3_items = build_repair_items()
    guard = frozen_guard(window, join, sources)
    prior1 = load_prior_result(root, "round1_result.json")
    prior2 = load_prior_result(root, "round2_result.json")

    payload = {
        "lane": "D0",
        "status": "DELIVERED",
        "verdict": window["verdict"],
        "universe_n": universe_n,
        "sources": strip_private(sources),
        "leadership_artifacts": leadership_artifacts(sources),
        "repo_claims": derive_repo_claims(root),
        "repo_head": git_head(root),
        "hashes_file": "hashes.txt",
        "universe_n_files": n_files,
        "universe_n_excluded_short": n_short,
        "universe_rule": "file stems of data/baskets/ohlcv/*.parquet, uppercased; exclude < 800 rows",
        "data_class": {
            "vintage": "final",
            "universe": "survivor-selected baskets",
        },
        "honest_window": {
            "start": window["start"],
            "end": window["end"],
            "rule": window["rule"],
            "weeks_observed_clock": window["weeks_observed_clock"],
            "weeks_belief_clock": window["weeks_belief_clock"],
            "observed_clock_start": window["observed_clock_start"],
            "belief_clock_start": window["belief_clock_start"],
            "per_source": window["per_source"],
            "change_points": window["change_points"],
            "min_per_date_from_honest_start": window["min_per_date_from_honest_start"],
            "min_per_date_row": window["min_per_date_row"],
            "max_per_date_from_honest_start": window["max_per_date_from_honest_start"],
            "max_per_date_row": window["max_per_date_row"],
            "union_max_ever": window["union_max_ever"],
            "union_max_ever_components": window["union_max_ever_components"],
            "grading_metric": window["grading_metric"],
            "previous_grading_metric": window["previous_grading_metric"],
            "threshold": window["threshold"],
            "leading_theme_honest_start": window["leading_theme_honest_start"],
            "in_force_sources": window["in_force_sources"],
            "in_force_excludes": window["in_force_excludes"],
            "in_force_semantics": window["in_force_semantics"],
        },
        "verdict_detail": {
            "verdict": window["verdict"],
            "honest_window_start": window["start"],
            "honest_window_end": window["end"],
            "honest_window_rule": window["rule"],
            "min_per_date_from_honest_start": window["min_per_date_from_honest_start"],
            "min_per_date_row": window["min_per_date_row"],
            "union_max_ever": window["union_max_ever"],
            "threshold": 0.5,
            "justification": window["justification"],
            "tree_per_asof": window["tree_per_asof"],
            "edges_headline_per_date_belief": window["edges_headline_per_date_belief"],
            "edges_union_ever": window["edges_union_ever"],
            "years_2014_2025_tree": {y: tree["coverage_by_year"][y] for y in YEARS if y != "2026"},
        },
        "leading_theme_join": join,
        "extra_artifacts": [strip_private(extra)],
        "write_time_commits": write_time,
        "grep": grep_census(),
        "jsonl_parse_failures": parse_failures,
        "gaps": [
            "No daily PIT ticker-theme membership tape exists for 2014-2025.",
            "Finviz tree_history has only two asof dates (2026-07-05, 2026-08-15); _meta finviz vintages are 2026-06-27 and 2026-08-15 (declared seed map vs tape).",
            "edges.parquet US MEMBER_OF sub-sources are all BACKFILLED on the observed clock relative to belief_time; raw_snapshot belief_time is 2026-08-15 on every row.",
            "leading-theme join is snapshot-honest only from first membership_history.snapshot_date (2026-08-13); context_history asof min is 2026-06-18 but honest_start is 2026-07-19 (first git write); rows before that are BACKFILLED.",
            "phase0.json does not enumerate its 116 flags.",
            "CN/HK/CA/INTL MEMBER_OF edges do not join the US B1 ohlcv universe.",
        ]
        + (
            [
                "gh api write-time commit lookup failed for at least one path; see write_time_commits.",
            ]
            if any(
                not (write_time.get(k) or {}).get("ok")
                for k in ("tree_history", "membership_history", "context_history_latest5")
            )
            else []
        ),
        "deviations": [
            "Workspace is this git checkout, not ~/lanes/repos/macro (path absent on this host).",
            "Q2 year table for edges.parquet still uses evidence_time (union-within-year) so the 13-year grid remains comparable; the headline and verdict use belief_time per-date and min-per-date from D*.",
            "data/baskets/membership_history.parquet is now used for the leading-theme join (repair item 3) and is still listed under extra_artifacts plus leading_theme_join.",
            "No indicator imports (engine.canon / session_anchor / bar_derive) — this lane is a census.",
            "RESULT.md is rendered from result.json inside census.py so the honest-window start cannot drift.",
            "Round-3 I2 reads write-time commits from gh_evidence.json (until=repo_head committer date); tests run with a fake gh that exits 1.",
        ],
        "repair_items": r1_items,
        "repair_items_round2": r2_items,
        "repair_items_round3": r3_items,
        "provenance": {"host": provenance_host()},
        "frozen_number_guard": guard,
        "i1_context_history_honest_start": {
            "before": ctx.get("honest_start_before_i1"),
            "after": ctx.get("honest_start"),
        },
        "changed_keys": {
            "round1_to_round2": leaf_diff(prior1, prior2) if prior1 and prior2 else None,
            "round2_to_round3_payload_pre_fold": None,
        },
        "grep_only_named_paths": list(GREP_ONLY_NAMED_PATHS),
    }
    if prior2:
        payload["changed_keys"]["round2_to_round3_payload_pre_fold"] = leaf_diff(
            prior2, strip_private(payload)
        )
    return payload


def dump_payload(payload: dict, path: Path) -> None:
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _md_table(headers: list[str], rows: list[list[object]]) -> str:
    def cell(x: object) -> str:
        if x is None:
            return ""
        return str(x).replace("|", "\\|")

    out = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" if i == 0 else "---:" if i else "---" for i, _ in enumerate(headers)).replace("---: " * 0, "") + " |",
    ]
    # alignment: first col left, numeric-looking right — keep simple: first left, rest as given
    align = []
    for i, h in enumerate(headers):
        align.append("---" if i == 0 else "---:")
    out[1] = "| " + " | ".join(align) + " |"
    for row in rows:
        out.append("| " + " | ".join(cell(c) for c in row) + " |")
    return "\n".join(out)


def render_result_md(payload: dict, *, result_json_sha256: str | None = None) -> str:
    n = payload["universe_n"]
    hw = payload["honest_window"]
    vd = payload["verdict_detail"]
    start = hw["start"]
    end = hw["end"]
    min_row = hw.get("min_per_date_row") or {}
    min_cov = hw["min_per_date_from_honest_start"]
    min_n = min_row.get("n_univ_tickers")
    union_ever = hw["union_max_ever"]
    w_obs = hw["weeks_observed_clock"]
    w_bel = hw["weeks_belief_clock"]
    join = payload["leading_theme_join"]
    by_name = {s["name"]: s for s in payload["sources"]}
    edges = by_name["theme_graph_edges"]
    tree = by_name["themes_heatmap_tree_history"]
    extra = payload["extra_artifacts"][0]

    lines: list[str] = []
    lines.append("# D0 — Wave-2 gate census: point-in-time theme membership for the B1 stock universe")
    lines.append("")
    lines.append(
        "The B1 stock universe is survivor-selected (current `data/baskets/ohlcv/` membership only). "
        "Price stores are FINAL-VINTAGE (as observed today, not point-in-time). "
        f"ANSWER FIRST: leading-theme membership cannot be reconstructed point-in-time for 2014–2025; "
        f"the honest window is **{start} → {end}** "
        f"({w_obs.get('weeks')} weeks on the observed clock, {w_bel.get('weeks')} weeks on the belief_time clock) "
        f"with minimum per-date coverage **{pct_cell(min_cov)} ({min_n}/{n})** from D* onward "
        f"(union-ever was {pct_cell(union_ever)}); the verdict is **{payload['verdict']}**."
    )
    lines.append("")
    lines.append("Lane: D0. Operation: prophet-astra-ceo-fable-20261004-001. This is a census: no returns, no hypothesis, no indicator.")
    lines.append("")
    lines.append("Numbers in this file are rendered from `result.json` (including `honest_window.start`).")
    lines.append("")
    lines.append("## Data law")
    lines.append("")
    lines.append(
        f"**Honest start D\\*** = `{start}`. **Honest end E\\*** = `{end}`. "
        f"Rule (stored as `honest_window.rule` in result.json): {hw['rule']}"
    )
    lines.append("")
    lines.append("Which clock each source is graded on:")
    lines.append("")
    clock_rows = []
    for row in hw["per_source"]:
        clock_rows.append(
            [
                row["name"],
                row.get("honest_clock"),
                row.get("honest_start") or "",
                row.get("pit_class"),
                (row.get("weeks_start_to_Estar") or {}).get("weeks"),
            ]
        )
    lines.append(
        _md_table(
            ["Source", "Honest clock", "Honest start", "PIT class", "Weeks start→E*"],
            clock_rows,
        )
    )
    lines.append("")
    lines.append("Honest columns vs backfilled columns:")
    lines.append("")
    lines.append("- `tree_history.asof` — **honest** (snapshot date; first observed date of that vintage's state).")
    lines.append("- `membership_history.snapshot_date` — **honest** (`engine/basket_membership_pit.py:16-18` keep-FIRST; `:99` `SUITE_US = \"baskets\"`). Carry-forward: newest snapshot ≤ D (`:33`).")
    lines.append("- `membership_history.added` — **backfilled** (seed-dominated; applied before the snapshot that recorded it).")
    lines.append("- `edges.belief_time` — graph belief clock. **BACKFILLED source; excluded from the honest series.** Sub-sources have observed dates that precede belief_time.")
    lines.append("- `edges.evidence_time` — observed/publication clock. Used for the Q2 year grid only. Not the honest clock for raw_snapshot (belief_time=2026-08-15 on every raw_snapshot row).")
    lines.append("- `edges.valid_from` — valid-time. **Backfilled** for `seed_constant` (`2023-05-09`) and mixed for `curated_changelog`.")
    lines.append(
        "- `context_history.asof` — **honest** at theme grain from first git write "
        f"`{CONTEXT_HISTORY_FIRST_WRITE}` (I1); asof rows before that are **BACKFILLED**. "
        "0 tickers until joined to snapshot_date."
    )
    lines.append("- `_meta.json belief_time` — current generation sidecar; sets E*, not a membership tape.")
    lines.append(
        "- Honest in-force series at D = last `tree_history.asof` ≤ D ∪ last "
        "`membership_history.snapshot_date` ≤ D. `membership_history.added` and "
        "`theme_graph_edges` never enter that series."
    )
    lines.append("")
    lines.append("## Universe")
    lines.append("")
    lines.append(
        _md_table(
            ["Item", "N"],
            [
                ["`data/baskets/ohlcv/*.parquet` files", payload["universe_n_files"]],
                ["Excluded (`< 800` rows)", payload["universe_n_excluded_short"]],
                ["**Universe used** (stems uppercased, ≥ 800 rows)", f"**{n}**"],
            ],
        )
    )
    lines.append("")
    lines.append("Rule matches lane B1. Names are current survivors; delisted names are absent.")
    lines.append("")
    lines.append("## Q1 — Source grain, date field, PIT class")
    lines.append("")
    lines.append(
        "A claim without a path and field name is not an answer. `pit_class` is one of "
        "`PIT_HONEST` (membership could have been known on the named date field), "
        "`BACKFILLED` (current snapshot stamped with a date, or memberships applied before they were published), "
        "`UNDECIDABLE` (named evidence missing)."
    )
    lines.append("")
    q1_rows = []
    for s in payload["sources"]:
        q1_rows.append(
            [
                s["name"],
                f"`{s['path']}`",
                s["grain"],
                f"`{s['date_field']}`",
                s["date_min"],
                s["date_max"],
                s["n_tickers"],
                s["n_themes"],
                s["pit_class"],
            ]
        )
    lines.append(
        _md_table(
            ["Source", "Path", "Grain", "Date field", "Date min", "Date max", "Distinct tickers", "Distinct themes", "PIT class"],
            q1_rows,
        )
    )
    lines.append("")
    lines.append("### Per-source decision (field named)")
    lines.append("")
    for s in payload["sources"]:
        lines.append(
            f"**`{s['path']}` / `{s['date_field']}`.** {s.get('pit_class_reason') or ''} "
            f"Decision field: `{s.get('pit_class_field') or s['date_field']}`."
        )
        lines.append("")

    lines.append("### edges.parquet sub-sources and both clocks")
    lines.append("")
    lines.append(
        "Repair item 2: `belief_time` was checked. Each `date_provenance` sub-source is labelled "
        "PIT_HONEST or BACKFILLED with row count and belief_time range. Headline is the per-date "
        "figure on the honest clock (belief_time dated-that-day), not the union-ever."
    )
    lines.append("")
    sub_rows = []
    for sub in edges.get("sub_sources") or []:
        sub_rows.append(
            [
                sub["name"],
                sub["n_rows"],
                sub["n_univ_tickers"],
                sub["pit_class"],
                f"{sub.get('belief_time_min')} → {sub.get('belief_time_max')}",
                f"{sub.get('evidence_time_min')} → {sub.get('evidence_time_max')}",
                sub.get("pit_class_reason"),
            ]
        )
    lines.append(
        _md_table(
            ["Sub-source (date_provenance)", "Rows", "Univ tickers", "PIT class", "belief_time", "evidence_time", "Why"],
            sub_rows,
        )
    )
    lines.append("")
    lines.append("Per-date coverage, dated-that-day, **observed clock** (`evidence_time`):")
    lines.append("")
    lines.append(
        _md_table(
            ["Date", "Rows", "Univ tickers", "Coverage"],
            [
                [r["date"], r["n_rows"], r["n_univ_tickers"], pct_cell(r["coverage"])]
                for r in edges.get("per_date_observed_evidence_time") or []
            ],
        )
    )
    lines.append("")
    lines.append("Per-date coverage, dated-that-day, **belief_time clock** (BACKFILLED source; excluded from the honest series):")
    lines.append("")
    lines.append(
        _md_table(
            ["Date", "Rows", "Univ tickers", "Coverage"],
            [
                [r["date"], r["n_rows"], r["n_univ_tickers"], pct_cell(r["coverage"])]
                for r in edges.get("per_date_belief_time") or []
            ],
        )
    )
    lines.append("")
    lines.append(
        "Per-date **cumulative-ever** (clock ≤ D; membership never closes; not interval in-force) on both clocks:"
    )
    lines.append("")
    lines.append(
        _md_table(
            ["Clock", "Date", "Univ tickers", "Coverage"],
            [["evidence_time", r["date"], r["n_univ_tickers"], pct_cell(r["coverage"])] for r in edges.get("per_date_in_force_evidence_time") or []]
            + [["belief_time", r["date"], r["n_univ_tickers"], pct_cell(r["coverage"])] for r in edges.get("per_date_in_force_belief_time") or []],
        )
    )
    lines.append("")
    lines.append(
        f"Headline (belief_time dated-that-day max; BACKFILLED source; excluded from the honest series): "
        f"**{pct_cell(edges.get('headline_per_date_coverage') or 0)} "
        f"({edges.get('headline_per_date_n')}/{n})** on `{edges.get('headline_per_date_date')}`. "
        f"Union-ever (previous headline, not per-date): {pct_cell(edges.get('union_ever_coverage') or 0)} "
        f"({edges.get('union_ever_n')}/{n})."
    )
    lines.append("")
    lines.append("### tree_history change-point semantics")
    lines.append("")
    cp = tree.get("change_point_semantics") or {}
    lines.append(
        f"A change-point is the **{cp.get('semantics')}**, not a **{cp.get('not')}**. "
        f"Cite `{cp.get('cite')}`. {cp.get('note')}"
    )
    if cp.get("example"):
        ex = cp["example"]
        lines.append(
            f" Example: {ex.get('from_asof')} → {ex.get('to_asof')}: "
            f"delta +{ex.get('n_added')} / −{ex.get('n_removed')}, stable {ex.get('n_stable')}. "
            f"{ex.get('interpretation')}"
        )
    quoted = cp.get("quoted_lines") or []
    if quoted:
        lines.append("")
        lines.append(f"Quoted `{cp.get('quote_path') or 'engine/theme_graph/local_sources.py'}:8-18`:")
        lines.append("")
        lines.append("```")
        for q in quoted:
            lines.append(f"{q['line']:2d}| {q['text']}")
        lines.append("```")
    wt = payload.get("write_time_commits") or {}
    if wt:
        lines.append("")
        lines.append("Write-time commits (`gh api repos/mastermindx-market-intelligence/macro/commits?path=<path>&per_page=5`):")
        lines.append("")
        for key, label in (
            ("tree_history", "data/themes_heatmap/tree_history.jsonl"),
            ("membership_history", "data/baskets/membership_history.parquet"),
            ("context_history_latest5", "data/themes/context_history.jsonl (latest 5)"),
            ("context_history_first", "data/themes/context_history.jsonl (until 2026-07-20, first write)"),
        ):
            rec = wt.get(key) or {}
            lines.append(f"- `{label}` ok={rec.get('ok')}:")
            for c in rec.get("commits") or []:
                lines.append(f"  - `{c.get('sha')}` {c.get('date')} {c.get('msg')}")
            if rec.get("error"):
                lines.append(f"  - error: {rec.get('error')}")
        if wt.get("note"):
            lines.append("")
            lines.append(wt["note"])
    lines.append("")
    lines.append("### Grep (history-bearing artifacts)")
    lines.append("")
    g = payload["grep"]
    lines.append(f"Searched {', '.join(f'`{x}`' for x in g['searched'])} for {', '.join(g['terms'])}.")
    lines.append("")
    lines.append("Opened: " + ", ".join(f"`{x}`" for x in g["opened"]) + ".")
    lines.append("")
    lines.append("Found, not opened: " + ", ".join(f"`{x}`" for x in g["found_not_opened"]) + ".")
    lines.append("")
    lines.append(g.get("note") or "")
    lines.append("")
    lines.append("## Q2 — Coverage vs the universe")
    lines.append("")
    lines.append(
        "Membership = a record that binds a ticker to a theme/basket. Identity, capability, phase, "
        "scores, and receipts are not membership; their coverage is 0. Percent = (distinct universe "
        "names with ≥1 membership record dated in that year via the Q1 date field) / "
        f"{n}. Zeros included. All 13 years 2014–2026."
    )
    lines.append("")
    headers = ["Source", "Ever"] + YEARS + ["Honest-N ever"]
    q2_rows = []
    for s in payload["sources"]:
        q2_rows.append(
            [s["name"], pct_cell(s["universe_coverage_ever"])]
            + [pct_cell(s["coverage_by_year"][y]) for y in YEARS]
            + [s.get("n_univ_tickers_ever", 0)]
        )
    lines.append(_md_table(headers, q2_rows))
    lines.append("")
    lines.append(
        "Trap (not Q2): edges `valid_from` would print a 2023 mass from `seed_constant`. "
        "That is look-ahead if used as a 2023 membership tape. See `valid_from_coverage_by_year` on the edges source."
    )
    lines.append("")
    lines.append("## Q3 — Leadership, not membership")
    lines.append("")
    lead_rows = []
    for art in payload["leadership_artifacts"]:
        lead_rows.append([f"`{art['path']}`", art["grain"], art["date_min"], art["date_max"], art["pit_class"]])
    lines.append(_md_table(["Path", "Grain", "Date min", "Date max", "PIT class"], lead_rows))
    lines.append("")
    lines.append("### Leading-theme join (repair item 3)")
    lines.append("")
    lines.append(
        f"`{join['path_context']}` carries **{join['n_context_theme_ids']}** theme ids; "
        f"`{join['path_membership']}` has **{join['n_basket_ids']}** basket ids; "
        f"intersection = **{join['n_theme_ids_matching_basket_ids']}**. "
        f"`snapshot_date` is PIT_HONEST (`engine/basket_membership_pit.py:16-18` and `:99`); "
        f"`added` is BACKFILLED. Membership is carried forward from each `snapshot_date` "
        f"(newest snapshot ≤ D)."
    )
    lines.append("")
    lines.append(
        _md_table(
            ["snapshot_date", "Rows", "Names", "Univ names", "Coverage"],
            [
                [
                    r["snapshot_date"],
                    r["n_rows"],
                    r["n_tickers"],
                    r["n_univ_tickers"],
                    pct_cell(r["coverage"]),
                ]
                for r in extra.get("snapshot_counts") or []
            ],
        )
    )
    lines.append("")
    lines.append(
        "Per-date join (all labeled themes = the 49 US baskets; leading = labels in {dominant, emerging}). "
        "Honest class uses snapshot_date; backfilled class uses added."
    )
    lines.append("")
    jrows = []
    for r in join.get("per_date") or []:
        if r["date"] < "2026-08-07":
            continue
        jrows.append(
            [
                r["date"],
                r.get("ctx_asof"),
                r.get("snapshot_date_used") or "",
                r["n_labeled_themes"],
                r["n_leading_themes_dominant_emerging"],
                f"{r['snapshot_honest_all49_n']} ({pct_cell(r['snapshot_honest_all49_coverage'])})",
                f"{r['snapshot_honest_leading_n']} ({pct_cell(r['snapshot_honest_leading_coverage'])})",
                f"{r['added_backfilled_all49_n']} ({pct_cell(r['added_backfilled_all49_coverage'])})",
                f"{r['added_backfilled_leading_n']} ({pct_cell(r['added_backfilled_leading_coverage'])})",
            ]
        )
    lines.append(
        _md_table(
            [
                "Date",
                "ctx asof",
                "snap used",
                "n labels",
                "n leading",
                "honest all49",
                "honest leading",
                "added-backfilled all49",
                "added-backfilled leading",
            ],
            jrows,
        )
    )
    lines.append("")
    lines.append(
        f"Snapshot-honest all49 starts `{join.get('honest_start')}` with min coverage "
        f"{pct_cell(join.get('min_snapshot_honest_all49_coverage') or 0)} "
        f"and max {pct_cell(join.get('max_snapshot_honest_all49_coverage') or 0)}. "
        f"Leading-restricted (dominant+emerging) min "
        f"{pct_cell(join.get('min_snapshot_honest_leading_coverage') or 0)}, max "
        f"{pct_cell(join.get('max_snapshot_honest_leading_coverage') or 0)}. "
        f"Before the first snapshot, honest coverage is 0 even though context_history and "
        f"`added` are populated (2026-08-07 published_at is the backfilled start)."
    )
    lines.append("")
    lines.append("Per-ISO-week leading-restricted coverage (snapshot-honest, weeks 33–40 of 2026):")
    lines.append("")
    iso_rows = []
    for w in join.get("iso_week_leading_restricted") or []:
        iso_rows.append(
            [
                w.get("iso_week"),
                w.get("status") or "",
                ", ".join(w.get("dates") or []) or "",
                w.get("min_leading_n") if w.get("min_leading_n") is not None else "",
                pct_cell(w["min_leading_coverage"]) if w.get("min_leading_coverage") is not None else "",
                w.get("min_date") or "",
                w.get("max_leading_n") if w.get("max_leading_n") is not None else "",
                pct_cell(w["max_leading_coverage"]) if w.get("max_leading_coverage") is not None else "",
                w.get("max_date") or "",
            ]
        )
    lines.append(
        _md_table(
            [
                "ISO week",
                "Status",
                "Dates",
                "min N",
                "min cov",
                "min date",
                "max N",
                "max cov",
                "max date",
            ],
            iso_rows,
        )
    )
    lines.append("")
    lines.append(
        "I7: week 33 includes 2026-08-12, which is before `leading_theme_join.honest_start` "
        "2026-08-13. Dates are kept (dropping 08-12 would change min N from 0 to 228). "
        "The row is marked `BEFORE_HONEST_START`."
    )
    lines.append("")
    lines.append("## Q4 — What the repository claims vs disk")
    lines.append("")
    lines.append("Quotes from the four named inputs (file:line). `matches_disk` is re-derived from the file on disk; the command per cell is stored in result.json and shown here.")
    lines.append("")
    for i, claim in enumerate(payload["repo_claims"], 1):
        lines.append(
            f"{i}. `{claim['file']}:{claim['line']}` — `{claim['quote']}` — "
            f"**matches_disk={str(claim['matches_disk']).lower()}**."
        )
        lines.append(f"   - disk_command: `{claim.get('disk_command')}`")
        lines.append(f"   - disk_result: {claim.get('disk_result')}")
        lines.append(f"   - {claim.get('note')}")
        lines.append("")
    lines.append("## Q5 — Verdict")
    lines.append("")
    lines.append(f"**{payload['verdict']}**")
    lines.append("")
    lines.append(f"Honest window (single stored value): **{start} → {end}**.")
    lines.append("")
    lines.append(f"Rule: {hw['rule']}")
    lines.append("")
    lines.append(
        f"- Grading metric (repair item 4): **minimum per-date coverage from D\\* onward** = "
        f"**{pct_cell(min_cov)} ({min_n}/{n})** on `{min_row.get('date')}` "
        f"(tree_asof={min_row.get('tree_asof_used')}, snapshot={min_row.get('snapshot_date_used')})."
    )
    lines.append(
        f"- Previous metric (union max_ever): {pct_cell(union_ever)}. Both numbers are stored. "
        f"The verdict uses the minimum per-date figure. Neither is ≥ 50%."
    )
    lines.append(
        f"- edges belief_time dated-that-day max (BACKFILLED source; excluded from the honest series): {pct_cell(edges.get('headline_per_date_coverage') or 0)} "
        f"({edges.get('headline_per_date_n')}/{n}) on `{edges.get('headline_per_date_date')}`; "
        f"union-ever {pct_cell(edges.get('union_ever_coverage') or 0)} ({edges.get('union_ever_n')}/{n}). "
        f"Every edges sub-source is BACKFILLED."
    )
    lines.append(
        f"- leading-theme join snapshot-honest all49 starts `{join.get('honest_start')}` near "
        f"{pct_cell(join.get('min_snapshot_honest_all49_coverage') or 0)}."
    )
    lines.append("- 2014–2025: no PIT_HONEST ticker-theme membership record.")
    lines.append("")
    lines.append(vd.get("justification") or "")
    lines.append("")
    lines.append("Cheapest honest way to obtain the missing 2014–2025 / 50% coverage: a **forward membership log starting now** (continue dated Finviz/tree snapshots and basket changelogs; do not backfill from today's graph).")
    lines.append("")
    lines.append("## Seat question — honest window length in weeks")
    lines.append("")
    lines.append("The seat rules run-D-in-window versus park. This census does not rule it.")
    lines.append("")
    lines.append(
        _md_table(
            ["Clock", "Start", "End", "Days", "Weeks"],
            [
                [
                    "observed (D* from PIT_HONEST asof/snapshot_date)",
                    w_obs.get("start"),
                    w_obs.get("end"),
                    w_obs.get("days"),
                    w_obs.get("weeks"),
                ],
                [
                    "belief_time (earliest US MEMBER_OF belief_time)",
                    w_bel.get("start"),
                    w_bel.get("end"),
                    w_bel.get("days"),
                    w_bel.get("weeks"),
                ],
            ],
        )
    )
    lines.append("")
    lines.append("Honest start date per source (same table as Data law, with own-span weeks):")
    lines.append("")
    seat_rows = []
    for row in hw["per_source"]:
        own = row.get("weeks_own_span") or {}
        to_e = row.get("weeks_start_to_Estar") or {}
        seat_rows.append(
            [
                row["name"],
                row.get("honest_clock"),
                row.get("honest_start") or "",
                row.get("date_max") or "",
                own.get("weeks"),
                to_e.get("weeks"),
                row.get("pit_class"),
            ]
        )
    lines.append(
        _md_table(
            ["Source", "Clock", "Honest start", "Own date_max", "Weeks own span", "Weeks start→E*", "PIT class"],
            seat_rows,
        )
    )
    lines.append("")
    lines.append("Change-points of honest in-force union (tree asof ∪ snapshot_date), from D* onward:")
    lines.append("")
    lines.append(
        _md_table(
            ["Date", "Univ in force", "Coverage", "tree asof used", "snapshot used", "n tree", "n snap"],
            [
                [
                    r["date"],
                    r["n_univ_tickers"],
                    pct_cell(r["coverage"]),
                    r.get("tree_asof_used") or "",
                    r.get("snapshot_date_used") or "",
                    r.get("n_tree_univ"),
                    r.get("n_snapshot_univ"),
                ]
                for r in hw.get("change_points") or []
            ],
        )
    )
    lines.append("")
    lines.append("## Tests")
    lines.append("")
    lines.append("`python3 -m pytest research/prophet_v4/astra_regime_indicator_handoff_20261004/results/D0/code -q -p no:cacheprovider`")
    lines.append("")
    lines.append(
        "Invariants: 13 years on every source, verdict token, required JSON keys, universe ≥800 rule, "
        "path+date_field on every source, two in-process builds byte-identical, single honest_window.start, "
        "edges sub-sources, leading-theme join, min per-date grading, Q4 disk_command per claim, "
        "pinned change_points (2026-07-05=660, 08-13=933, 08-15=932, 08-18=931, 09-04=932), "
        "D*=2026-07-05, in_force from tree+snapshot only."
    )
    lines.append("")
    orch = payload.get("orchestrated_run") or {}
    summary = orch.get("pytest_summary") or ""
    if summary:
        lines.append(f"**{summary}**")
        lines.append("")
    mutants = orch.get("mutants") or {}
    if mutants:
        lines.append("Mutants (scratch copy of census.py; backfill leaks must fail):")
        lines.append("")
        for mid in ("M1", "M2"):
            info = mutants.get(mid) or {}
            fails = info.get("failed_test_names") or []
            fail_s = ", ".join(fails) if fails else "(none — DEFECT: mutant did not fail)"
            lines.append(
                f"- {mid} ({info.get('description') or ''}): FAILED {fail_s}"
            )
        lines.append("")
    lines.append("## Reproducibility")
    lines.append("")
    lines.append(
        "`census.py` writes `result.json`, renders this file, runs pytest, folds the pytest "
        "summary (no wall-clock timing) into `result.json`, re-renders this file from that JSON, "
        "then writes `hashes.txt` last via `write_hashes`."
    )
    lines.append("")
    if result_json_sha256:
        lines.append(
            f"result.json sha256 after the final fold: `{result_json_sha256}`"
        )
        lines.append("")
        lines.append(
            "Round-1 result.json sha256 (census definitions unchanged): "
            "`6ed2c8799dc622f76662b1c6c352be47c08ab9ec7746c0ef5f8ddafb893bcf18`"
        )
        lines.append("")
    lines.append("## Repair items (round 1)")
    lines.append("")
    for item in payload.get("repair_items") or []:
        lines.append(f"{item['id']}. {item['status']} — `{item['where']}`")
    lines.append("")
    lines.append("## Repair items (round 2)")
    lines.append("")
    for item in payload.get("repair_items_round2") or []:
        lines.append(f"{item['id']}. {item['status']} — `{item['where']}`")
    lines.append("")
    lines.append("## Repair items (round 3)")
    lines.append("")
    for item in payload.get("repair_items_round3") or []:
        lines.append(f"{item['id']}. {item['status']} — `{item['where']}`")
    lines.append("")
    lines.append("## I1 honest_start (themes_context_history)")
    lines.append("")
    i1 = payload.get("i1_context_history_honest_start") or {}
    lines.append(
        f"before={i1.get('before')} after={i1.get('after')}. "
        "Rows with asof < 2026-07-19 are BACKFILLED (first git write 15c39ef87650 at "
        "2026-07-19T03:22:13Z). Leading-restricted range, any-theme share, change points "
        "and ISO-week min/max are independent of this label (join starts 2026-08-13)."
    )
    lines.append("")
    lines.append("## Frozen-number guard")
    lines.append("")
    fg = payload.get("frozen_number_guard") or {}
    moved = fg.get("moved") or []
    if not moved:
        lines.append("All seat-frozen leaves match round-2 values.")
    else:
        lines.append(
            "These seat-frozen leaves moved under this host's skip-worktree working copies "
            "(not rewritten to chase round-2):"
        )
        lines.append("")
        for m in moved:
            lines.append(f"- `{m['leaf']}`: expected {m['expected']!r}, observed {m['observed']!r}")
    lines.append("")
    lines.append("## I8 changed-key lists (leaf diff, emitted by code)")
    lines.append("")
    ck = payload.get("changed_keys") or {}
    for label, key in (
        ("round-1 → round-2", "round1_to_round2"),
        ("round-2 → round-3", "round2_to_round3"),
    ):
        diff = ck.get(key)
        if key == "round2_to_round3" and not diff:
            diff = ck.get("round2_to_round3_payload_pre_fold")
        if not diff:
            lines.append(f"- {label}: prior file missing.")
            continue
        lines.append(
            f"- {label}: added={diff.get('n_added')} removed={diff.get('n_removed')} "
            f"changed={diff.get('n_changed')} numeric_changed={diff.get('n_numeric_changed')} "
            f"label_changed={diff.get('n_label_changed')}"
        )
        num = diff.get("numeric_changed") or []
        if num:
            lines.append("  numeric leaves:")
            for rec in num[:40]:
                lines.append(f"  - `{rec.get('path')}`: {rec.get('from')!r} → {rec.get('to')!r}")
        lines.append("")
    lines.append("## Grep-only named paths (I5; not inputs, not hashed)")
    lines.append("")
    for rel in payload.get("grep_only_named_paths") or GREP_ONLY_NAMED_PATHS:
        lines.append(f"- `{rel}`")
    lines.append("")
    lines.append("## Provenance")
    lines.append("")
    host = ((payload.get("provenance") or {}).get("host") or {})
    vers = host.get("versions") or {}
    lines.append(host.get("rerun_notice") or RERUN_NOTICE)
    lines.append("")
    lines.append(
        f"Host `{host.get('hostname')}` ({host.get('platform')}). "
        f"python={vers.get('python')} pandas={vers.get('pandas')} numpy={vers.get('numpy')} "
        f"pyarrow={vers.get('pyarrow')} scipy={vers.get('scipy')} pytest={vers.get('pytest')} "
        f"executable=`{vers.get('executable')}`."
    )
    lines.append("")
    lines.append(
        f"As-found round-2 result.json sha256 (recorded before any round-3 write): "
        f"`{host.get('as_found_round2_result_json_sha256') or ROUND2_RESULT_SHA256}`."
    )
    lines.append("")
    lines.append("## Deviations")
    lines.append("")
    for d in payload.get("deviations") or []:
        lines.append(f"- {d}")
    lines.append("")
    lines.append("## Gaps")
    lines.append("")
    for g in payload.get("gaps") or []:
        lines.append(f"- {g}")
    lines.append("")
    lines.append(f"- jsonl parse failures: {payload.get('jsonl_parse_failures')}")
    lines.append("")
    return "\n".join(lines) + "\n"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


CENSUS_READ_TARGETS = [
    "agentos/handoffs/GMI-THEME-GRAPH-2026-08-27-d2c-pit-vintage-commission.md",
    "contracts/biocatalyst/biocatalyst_theme_rollup_pit.v1.schema.json",
    "data/baskets/membership_history.parquet",
    "data/neuralweb/theme_phase_history.jsonl",
    "data/neuralweb/theme_state.json",
    "data/theme_activity/program_ledger.parquet",
    "data/theme_discovery/phase0.json",
    "data/theme_graph/_meta.json",
    "data/theme_graph/capability.parquet",
    "data/theme_graph/edges.parquet",
    "data/theme_graph/evidence.parquet",
    "data/theme_graph/identity_resolution.parquet",
    "data/theme_graph/node_lifecycle.parquet",
    "data/theme_graph/nodes.parquet",
    "data/themes/context_history.jsonl",
    "data/themes/context_history_cn.jsonl",
    "data/themes/state.json",
    "data/themes_heatmap/subsector_perf_history.jsonl",
    "data/themes_heatmap/tree_history.jsonl",
    "engine/basket_membership_pit.py",
    "engine/biocatalyst/theme_rollup_pit.py",
    "engine/theme_alerts.py",
    "engine/theme_clinical.py",
    "engine/theme_graph/identity_resolution.py",
    "engine/theme_graph/local_sources.py",
    "engine/theme_graph/materialize.py",
    "engine/theme_graph/membership_evidence.py",
    "engine/theme_graph/store.py",
    "research/prophet_v4/astra_regime_indicator_handoff_20261004/results/D0/gh_evidence.json",
    "research/prophet_v4/astra_regime_indicator_handoff_20261004/results/D0/prior/round1_result.json",
    "research/prophet_v4/astra_regime_indicator_handoff_20261004/results/D0/prior/round2_result.json",
]

CENSUS_OUTPUT_TARGETS = [
    "research/prophet_v4/astra_regime_indicator_handoff_20261004/results/D0/RESULT.md",
    "research/prophet_v4/astra_regime_indicator_handoff_20261004/results/D0/code/census.py",
    "research/prophet_v4/astra_regime_indicator_handoff_20261004/results/D0/code/run.py",
    "research/prophet_v4/astra_regime_indicator_handoff_20261004/results/D0/code/test_d0.py",
    "research/prophet_v4/astra_regime_indicator_handoff_20261004/results/D0/result.json",
]


def write_hashes(root: Path, out_path: Path) -> None:
    rels: list[str] = list(CENSUS_READ_TARGETS) + list(CENSUS_OUTPUT_TARGETS)
    for p in sorted((root / "data/baskets/ohlcv").glob("*.parquet")):
        rels.append(str(p.relative_to(root)))
    lines = []
    for rel in sorted(set(rels)):
        path = root / rel
        if not path.is_file():
            continue
        lines.append(f"{sha256_file(path)}  {rel}")
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _pytest_summary_no_timing(text: str) -> str:
    summary = ""
    for line in text.splitlines():
        stripped = line.strip()
        if re.search(r"\d+ passed", stripped) or re.search(r"\d+ failed", stripped):
            summary = re.sub(r"\s+in\s+[0-9.]+s$", "", stripped)
    return summary


def _failed_test_names(text: str) -> list[str]:
    names = []
    for line in text.splitlines():
        if ("FAILED" in line or "ERROR" in line) and "::" in line:
            m = re.search(r"::(test_\S+)", line)
            if m:
                names.append(m.group(1).rstrip("."))
    seen = []
    for n in names:
        if n not in seen:
            seen.append(n)
    return seen


def _fake_gh_env(base_env: dict | None = None) -> tuple[dict, Path]:
    """I2: tests must not call the network. A fake `gh` that exits 1 is first on PATH."""
    td = Path(tempfile.mkdtemp(prefix="d0_fakegh_"))
    gh = td / "gh"
    gh.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
    gh.chmod(0o755)
    env = dict(base_env or os.environ)
    env["PATH"] = str(td) + os.pathsep + env.get("PATH", "")
    env["NO_COLOR"] = "1"
    return env, td


def run_pytest(root: Path, code_dir: Path) -> dict:
    env, fake_dir = _fake_gh_env()
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        str(code_dir),
        "-q",
        "-p",
        "no:cacheprovider",
        "--tb=line",
    ]
    proc = subprocess.run(cmd, cwd=root, capture_output=True, text=True, timeout=900, env=env)
    text = (proc.stdout or "") + "\n" + (proc.stderr or "")
    return {
        "rc": proc.returncode,
        "summary": _pytest_summary_no_timing(text),
        "failed_test_names": _failed_test_names(text),
        "command": "python3 -m pytest research/prophet_v4/astra_regime_indicator_handoff_20261004/results/D0/code -q -p no:cacheprovider",
        "fake_gh": str(fake_dir / "gh"),
        "full_output_tail": "\n".join(text.strip().splitlines()[-8:]),
    }


def _mutate_m1(src: str) -> str:
    marker = "        # IN_FORCE_TREE_AND_SNAPSHOT_ONLY: do not union membership_history.added or edges"
    inject = (
        "        for t, a in zip(mh_tickers[\"ticker\"].tolist(), mh_tickers[\"added\"].tolist()):\n"
        "            ad = iso_day(a)\n"
        "            if ad and ad <= d:\n"
        "                names.add(str(t).upper())\n"
        "        # IN_FORCE_TREE_AND_SNAPSHOT_ONLY: do not union membership_history.added or edges"
    )
    if marker not in src:
        raise RuntimeError("M1 marker missing")
    load_marker = "    snap_names = load_snapshot_names(root)\n    snap_dates = sorted(snap_names)\n"
    load_inject = (
        "    snap_names = load_snapshot_names(root)\n"
        "    snap_dates = sorted(snap_names)\n"
        "    mh_tickers = pd.read_parquet(root / \"data/baskets/membership_history.parquet\").copy()\n"
        "    mh_tickers[\"ticker\"] = mh_tickers[\"ticker\"].astype(str).str.upper()\n"
    )
    if load_marker not in src:
        raise RuntimeError("M1 load marker missing")
    return src.replace(load_marker, load_inject, 1).replace(marker, inject, 1)


def _mutate_m2(src: str) -> str:
    marker = "    # DSTAR_FROM_TREE_AND_SNAPSHOT_ONLY: edges observed dates do not set D*"
    inject = (
        "    obs = [r[\"date\"] for r in (edges.get(\"per_date_observed_evidence_time\") or [])]\n"
        "    if obs:\n"
        "        honest_starts.append(min(obs))\n"
        "    # DSTAR_FROM_TREE_AND_SNAPSHOT_ONLY: edges observed dates do not set D*"
    )
    if marker not in src:
        raise RuntimeError("M2 marker missing")
    return src.replace(marker, inject, 1)


def run_mutants(root: Path) -> dict:
    src_dir = results_dir(root) / "code"
    census_src = (src_dir / "census.py").read_text(encoding="utf-8")
    out = {}
    mutators = {
        "M1": (
            "membership_history added names counted into in_force",
            _mutate_m1,
        ),
        "M2": (
            "edges observed date allowed to set D*",
            _mutate_m2,
        ),
    }
    for mid, (desc, mutator) in mutators.items():
        td = Path(tempfile.mkdtemp(prefix=f"d0_{mid}_"))
        dst = td / "code"
        dst.mkdir()
        for name in ("census.py", "test_d0.py", "run.py"):
            shutil.copy2(src_dir / name, dst / name)
        mutated = mutator(census_src)
        if mutated == census_src:
            raise RuntimeError(f"{mid} mutation was a no-op")
        (dst / "census.py").write_text(mutated, encoding="utf-8")
        result = run_pytest(root, dst)
        result["description"] = desc
        result["scratch"] = str(dst)
        out[mid] = result
    return out


def main() -> int:
    root = find_root()
    rd = results_dir(root)
    rd.mkdir(parents=True, exist_ok=True)
    ensure_gh_evidence(root)
    payload = build_payload(root)
    out_json = rd / "result.json"
    out_md = rd / "RESULT.md"
    dump_payload(payload, out_json)
    out_md.write_text(render_result_md(json.loads(out_json.read_text(encoding="utf-8"))), encoding="utf-8")
    pytest_run = run_pytest(root, rd / "code")
    mutants = run_mutants(root)
    payload["orchestrated_run"] = {
        "pytest_summary": pytest_run["summary"],
        "pytest_rc": pytest_run["rc"],
        "pytest_failed": pytest_run["failed_test_names"],
        "pytest_command": pytest_run["command"],
        "pytest_fake_gh": "PATH prefix: fake gh exits 1 (no network)",
        "mutants": {
            mid: {
                "description": info["description"],
                "rc": info["rc"],
                "summary": info["summary"],
                "failed_test_names": info["failed_test_names"],
            }
            for mid, info in mutants.items()
        },
    }
    prior2 = load_prior_result(root, "round2_result.json")
    if prior2:
        payload.setdefault("changed_keys", {})
        payload["changed_keys"]["round2_to_round3"] = leaf_diff(prior2, strip_private(payload))
    dump_payload(payload, out_json)
    sha = sha256_file(out_json)
    loaded = json.loads(out_json.read_text(encoding="utf-8"))
    out_md.write_text(
        render_result_md(loaded, result_json_sha256=sha),
        encoding="utf-8",
    )
    hashes_path = rd / "hashes.txt"
    write_hashes(root, hashes_path)
    i1 = loaded.get("i1_context_history_honest_start") or {}
    fg = loaded.get("frozen_number_guard") or {}
    print(f"wrote {out_json.relative_to(root)}")
    print(f"wrote {out_md.relative_to(root)}")
    print(f"wrote {hashes_path.relative_to(root)}")
    print(f"universe_n={payload['universe_n']} verdict={payload['verdict']}")
    print(f"honest_window={loaded['honest_window']['start']} → {loaded['honest_window']['end']}")
    print(f"i1_honest_start_before={i1.get('before')} after={i1.get('after')}")
    print(f"frozen_moved={fg.get('n_moved')}")
    print(f"pytest_summary={pytest_run['summary']}")
    print(f"pytest_tail={pytest_run.get('full_output_tail')}")
    print(f"result_json_sha256={sha}")
    print(f"as_found_round2_sha256={ROUND2_RESULT_SHA256}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
