"""Recover and qualify B-17's original frozen inputs without changing runtime state.

This research CLI reads immutable Git objects. It does not regenerate the stock
library, fill unknown admission fields, accept B-17, or publish product metrics.
"""
from __future__ import annotations

import argparse
import bisect
import hashlib
import io
import json
import re
import subprocess
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
FROZEN_REF = "228c25d37617a7217c8f65f1613ade701a2fe01a"
SOURCE_REF = "45dae5dba0a252ceaef05a8ab8c17decb73d99d8"
FROZEN_DIR = "research/prophet_us_audit"
SNAPSHOT_PATH = "site/factordata/us_standouts.json"
GITHUB_REPO = "mastermindx-market-intelligence/macro"
CUTOFF = "2026-08-10"
IMPLEMENTATION_SHA256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
HEX = re.compile(r"^[0-9a-f]{40}$")


class SourceAccessRefused(RuntimeError):
    """An explicit access refusal ends this source-read operation."""


def checked_read(args: list[str], *, cwd: Path | None = None, timeout: int = 120) -> bytes:
    result = subprocess.run(args, cwd=cwd, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, timeout=timeout)
    if result.returncode:
        error = result.stderr.decode(errors="replace").lower()
        denials = ("http 401", "http 403", "authentication failed", "permission denied",
                   "access denied", "could not read username", "gh auth login")
        if any(term in error for term in denials):
            raise SourceAccessRefused("Canonical source access refused; no fallback or retry")
        raise subprocess.CalledProcessError(result.returncode, args, result.stdout, result.stderr)
    return result.stdout


class InputUnavailable(ValueError):
    """An input is unknown, not evidence of a negative signal."""


def utc(value: str) -> datetime:
    stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if stamp.tzinfo is None:
        raise InputUnavailable("An availability time must include its timezone")
    return stamp.astimezone(timezone.utc)


def git_blob_sha(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


@dataclass(frozen=True)
class GitInput:
    ref: str
    path: str
    blob: str
    raw: bytes
    transport: str

    def receipt(self) -> dict[str, Any]:
        return {
            "ref": self.ref, "path": self.path, "git_blob": self.blob,
            "sha256": hashlib.sha256(self.raw).hexdigest(),
            "bytes": len(self.raw), "transport": self.transport,
        }


class GitReader:
    """Read one repository's pinned objects; optional GitHub fallback is read-only."""

    def __init__(self, repo: Path, github_fallback: bool = False):
        self.repo = Path(repo)
        self.github_fallback = github_fallback
        self.cache: dict[tuple[str, str], GitInput] = {}

    def command(self, args: list[str], timeout: int = 120) -> bytes:
        return checked_read(["git", "-C", str(self.repo), *args], timeout=timeout)

    def tree(self, ref: str, prefix: str) -> dict[str, str]:
        if not HEX.fullmatch(ref):
            raise InputUnavailable("A full immutable commit is required")
        raw = self.command(["ls-tree", "-r", "-z", ref, "--", prefix])
        result = {}
        for row in raw.split(b"\0"):
            if not row:
                continue
            info, path = row.split(b"\t", 1)
            _, kind, oid = info.decode().split()
            if kind == "blob":
                result[path.decode()] = oid
        return result

    def read(self, ref: str, path: str) -> GitInput:
        if not HEX.fullmatch(ref) or path.startswith("/") or ".." in Path(path).parts:
            raise InputUnavailable("Read requires an immutable ref and relative repository path")
        key = ref, path
        if key in self.cache:
            return self.cache[key]
        try:
            oid = self.command(["rev-parse", f"{ref}:{path}"], timeout=30).decode().strip()
            if not HEX.fullmatch(oid):
                raise InputUnavailable("Git did not return a blob identity")
            raw = self.command(["cat-file", "blob", oid])
            transport = "git_object"
        except (subprocess.SubprocessError, InputUnavailable):
            if not self.github_fallback:
                raise InputUnavailable(f"Immutable input unavailable locally: {ref}:{path}")
            endpoint = f"repos/{GITHUB_REPO}/contents/{path}?ref={ref}"
            meta = json.loads(checked_read(["gh", "api", endpoint], timeout=90))
            oid = meta.get("sha")
            if not isinstance(oid, str) or not HEX.fullmatch(oid):
                raise InputUnavailable("GitHub metadata lacks an immutable blob identity")
            raw = checked_read(
                ["gh", "api", "-H", "Accept: application/vnd.github.raw+json", endpoint], timeout=90
            )
            transport = "github_immutable_contents"
        if git_blob_sha(raw) != oid:
            raise InputUnavailable(f"Blob identity mismatch: {ref}:{path}")
        result = GitInput(ref, path, oid, raw, transport)
        self.cache[key] = result
        return result


def normalized_prices(raw: bytes, cutoff: str) -> tuple[pd.DataFrame, int]:
    """The frozen evaluator's normalization, then an explicit right-edge fence."""
    frame = pd.read_parquet(io.BytesIO(raw))
    if not {"high", "low", "close"}.issubset(frame.columns):
        raise InputUnavailable("Price file does not supply high, low and close")
    frame.index = pd.DatetimeIndex(frame.index).tz_localize(None).normalize()
    frame = frame[~frame.index.duplicated(keep="last")].sort_index()
    cols = [x for x in ("open", "high", "low", "close", "volume") if x in frame]
    frame = frame[cols].dropna(subset=["close", "high", "low"])
    excluded = int((frame.index > pd.Timestamp(cutoff)).sum())
    return frame.loc[:cutoff].copy(), excluded


def frozen_coverage(anchors: pd.DataFrame, candidates: pd.DataFrame) -> dict[str, Any]:
    """Reproduce R2i: same ticker, inclusive 0..30 sessions, latest candidate."""
    positions: dict[str, list[int]] = {}
    for ticker, group in candidates.groupby("ticker"):
        positions[str(ticker)] = sorted({int(x) for x in group["pos"]})
    leads = []
    for row in anchors.itertuples():
        pos = int(row.pos)
        known = positions.get(str(row.ticker), [])
        right = bisect.bisect_right(known, pos)
        if right and 0 <= pos - known[right - 1] <= 30:
            leads.append(pos - known[right - 1])
    count = len(anchors)
    return {
        "denominator": count, "covered": len(leads),
        "coverage_pct": round(100 * len(leads) / count, 2) if count else None,
        "median_lead_sessions": float(np.median(leads)) if leads else None,
        "same_day_covered": sum(x == 0 for x in leads),
        "ruler": "inclusive_0_to_30_sessions_latest_candidate",
    }


def dedup_positions(positions: list[int], gap: int = 10) -> list[int]:
    """Same keep-first rule as the frozen evaluator, not rolling clustering."""
    kept: list[int] = []
    for pos in sorted(set(positions)):
        if not kept or pos - kept[-1] >= gap:
            kept.append(pos)
    return kept


def qualify_snapshot(
    body: dict[str, Any] | None,
    *,
    known_at: str | None,
    decision_at: str,
    cutoff: str,
    complete_original: bool,
    panel: list[str],
) -> dict[str, Any]:
    """Use the canonical selector only on a complete, source-bound original blob.

    Missing optional fields in original bytes retain canonical compatibility
    semantics. Missing fields in an incomplete reconstruction NEVER inherit them.
    """
    unknown = {"state": "unknown_input", "admitted": [], "refused": [],
               "unknown": list(panel), "stats": {}}
    if not isinstance(body, dict) or not complete_original:
        return {**unknown, "reason": "complete_original_snapshot_unavailable"}
    if known_at is None or utc(known_at) > utc(decision_at):
        return {**unknown, "reason": "snapshot_not_known_by_decision_cutoff"}
    source_asof = body.get("as_of")
    if not isinstance(source_asof, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", source_asof):
        return {**unknown, "reason": "invalid_source_asof"}
    try:
        date.fromisoformat(source_asof)
    except ValueError:
        return {**unknown, "reason": "invalid_source_asof"}
    if source_asof > utc(known_at).date().isoformat():
        return {**unknown, "reason": "source_after_archive_availability"}
    if source_asof > cutoff:
        return {**unknown, "reason": "source_after_frozen_price_edge"}
    rows = body.get("buy")
    if not isinstance(rows, list) or any(not isinstance(x, dict) for x in rows):
        return {**unknown, "reason": "buy_population_unavailable"}
    tickers = [x.get("ticker") for x in rows]
    if any(not isinstance(t, str) or not t for t in tickers) or len(set(tickers)) != len(tickers):
        return {**unknown, "reason": "buy_population_identity_invalid"}
    from engine.prophet_bridge import select_candidates
    stats: dict[str, Any] = {}
    try:
        admitted_rows = select_candidates(body, n=None, stats=stats)
    except (TypeError, ValueError, AttributeError, KeyError) as exc:
        return {**unknown, "reason": f"selector_input_invalid:{type(exc).__name__}"}
    admitted_all = {x["ticker"] for x in admitted_rows}
    panel_set = set(panel)
    return {
        "state": "known_snapshot_selection", "reason": None,
        "source_asof": source_asof, "known_at": known_at,
        "admitted": sorted(panel_set & admitted_all),
        "refused": sorted(panel_set - admitted_all), "unknown": [],
        "admitted_all_count": len(admitted_all), "buy_rows": len(rows), "stats": stats,
        "scope": "fixed_rule_on_archived_complete_buy_population",
    }


def first_eligible_surfaces(observations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Preserve signature time and first evidenced eligible input session separately.

    Unknown input in a fire's preceding liveness interval makes its first visibility
    unproven. This consumes evidence; it neither computes nor replaces admission.
    """
    if any(x["admission_state"] not in {"admitted", "refused", "unknown_input"} for x in observations):
        raise InputUnavailable("Unknown admission-state vocabulary")
    keys = [(x["ticker"], int(x["pos"])) for x in observations]
    if len(keys) != len(set(keys)):
        raise InputUnavailable("Conflicting duplicate session observations")
    seen: set[tuple[str, str]] = set()
    unknown_by_ticker: dict[str, set[int]] = {}
    out = []
    for row in sorted(observations, key=lambda x: (x["pos"], x["ticker"])):
        ticker, pos = row["ticker"], int(row["pos"])
        if row["admission_state"] == "unknown_input":
            unknown_by_ticker.setdefault(ticker, set()).add(pos)
        if not row.get("union_fired") or row["admission_state"] != "admitted":
            continue
        fire_pos = int(row["fire_pos"])
        if not 0 <= pos - fire_pos <= 3:
            raise InputUnavailable("Union liveness evidence is inconsistent")
        key = ticker, row["fire_date"]
        if key in seen:
            continue
        seen.add(key)
        unknown = any(fire_pos <= p < pos for p in unknown_by_ticker.get(ticker, set()))
        covered = {int(x["pos"]) for x in observations
                   if x["ticker"] == ticker and fire_pos <= int(x["pos"]) <= pos}
        unknown = unknown or covered != set(range(fire_pos, pos + 1))
        out.append({
            "ticker": ticker, "signature_date": row["fire_date"],
            "signature_pos": fire_pos, "first_evidenced_surface_date": row["date"],
            "surface_pos": pos, "first_visibility_proven": not unknown,
        })
    return out


def replay_cutoff_intersection(
    snapshots: list[dict[str, Any]], frames: dict[str, pd.DataFrame],
) -> dict[str, Any]:
    """Run the existing union on the selected original-cutoff buy population.

    This proves only the as-of-date input intersection. The daily archive sample
    cannot establish first publication, actual served membership or full-panel lead.
    """
    candidates = [
        x for x in snapshots
        if x.get("state") == "known_snapshot_selection" and x["source_asof"] == CUTOFF
    ]
    if not candidates:
        return {"state": "unknown_input", "reason": "original_cutoff_snapshot_unavailable"}
    snapshot = max(candidates, key=lambda x: utc(x["known_at"]))
    from engine.us_early_turn import union_admission
    results = []
    for ticker in snapshot["admitted"]:
        frame = frames.get(ticker)
        if frame is None:
            results.append({"ticker": ticker, "state": "unknown_input", "reason": "price_vintage_unqualified"})
            continue
        union = union_admission(frame, asof=CUTOFF)
        reason = str(union.get("reason") or "")
        unavailable = reason.startswith("union admission unavailable:") or reason.startswith("fewer than ")
        results.append({
            "ticker": ticker, "state": "unknown_input" if unavailable else "known_signature",
            "union_fired": None if unavailable else bool(union["fired"]),
            "signature_date": union.get("fire_date"), "age_sessions": union.get("age_bars"),
            "legs": union.get("legs"), "reason": union.get("reason"),
        })
    return {
        "state": "input_intersection_replayed",
        "scope": "current_pinned_rule_on_archived_cutoff_inputs; not first visibility or served-deck proof",
        "source_asof": CUTOFF, "snapshot_ref": snapshot["ref"],
        "snapshot_git_blob": snapshot["git_blob"], "snapshot_sha256": snapshot["sha256"],
        "snapshot_known_at": snapshot["known_at"],
        "buy_rows_all_names": snapshot["buy_rows"],
        "selector_admitted_all_names": snapshot["admitted_all_count"],
        "selector_admitted_primary_panel": len(snapshot["admitted"]),
        "union_live_primary_panel": [x["ticker"] for x in results if x.get("union_fired") is True],
        "unknown_primary_panel": [x["ticker"] for x in results if x["state"] == "unknown_input"],
        "rows": results, "coverage_result": None, "lead_result": None,
    }


def _sha_file(reader: GitReader, ref: str, path: str) -> tuple[Any, GitInput]:
    item = reader.read(ref, path)
    return json.loads(item.raw), item


def recover(
    reader: GitReader, *, frozen_ref: str, source_ref: str,
    archive_index: dict[str, Any] | None = None,
    report_progress: bool = False,
) -> dict[str, Any]:
    # Imports below resolve from this implementation's checkout. A different
    # reader checkout could otherwise advertise a rule_ref it never executed.
    if reader.repo.resolve() != REPO.resolve():
        raise InputUnavailable("Recovery reader must match the implementation checkout")
    rule_ref = reader.command(["rev-parse", "HEAD"]).decode().strip()
    reader.command(["diff", "--exit-code", rule_ref, "--", "engine", "config"])
    rule_sources = [reader.read(rule_ref, path).receipt() for path in
                    ("engine/prophet_bridge.py", "engine/us_early_turn.py",
                     "engine/confluence_tiers.py", "engine/session_anchor.py", "engine/signal_quality.py")]
    frozen, frozen_file = _sha_file(reader, frozen_ref, f"{FROZEN_DIR}/early_admission_bakeoff_results.json")
    decision_at = frozen["run_metadata"]["run_utc"]
    panel = frozen["universe"]["primary_panel"]
    if len(panel) != 240 or len(set(panel)) != 240:
        raise InputUnavailable("The original 240-name primary panel changed")
    episode_file = reader.read(frozen_ref, f"{FROZEN_DIR}/early_admission_bakeoff_episodes.parquet")
    episodes = pd.read_parquet(io.BytesIO(episode_file.raw))
    if len(episodes) != frozen["split_out"]["episodes_rows"]:
        raise InputUnavailable("Frozen episode row count disagrees with its result JSON")
    primary = episodes.loc[~episodes["addon"].astype(bool) & episodes["ticker"].isin(panel)]
    counts = primary.groupby("construction").size().to_dict()
    for key, expected in frozen["split_out"]["episodes_by_construction"].items():
        if counts.get(key) != expected:
            raise InputUnavailable(f"Frozen episode population mismatch: {key}")
    anchors = primary.loc[primary["construction"] == "C0"].copy()
    c1 = primary.loc[primary["construction"] == "C1"]
    baseline = frozen_coverage(anchors, c1)
    if (baseline["covered"], baseline["denominator"], baseline["median_lead_sessions"]) != (4800, 7918, 12.0):
        raise InputUnavailable("The frozen R2i C1 baseline did not reproduce")

    signal_files = reader.tree(source_ref, "site/signals")
    signal_files = {p: h for p, h in signal_files.items() if p.endswith(".json")}
    expected_names = set(panel) | set(frozen["universe"]["store_names_unpriced"])
    if {Path(p).stem for p in signal_files} != expected_names:
        raise InputUnavailable("Signal-store population differs from the frozen study")
    signals, signal_dates = [], Counter()
    for signal_number, path in enumerate(sorted(signal_files), 1):
        item = reader.read(source_ref, path)
        doc = json.loads(item.raw)
        if doc.get("asof", "9999") > CUTOFF:
            raise InputUnavailable("Signal store contains a post-cutoff source")
        signal_dates[doc.get("asof")] += 1
        signals.append({**item.receipt(), "ticker": Path(path).stem, "asof": doc.get("asof")})
        if report_progress and signal_number % 60 == 0:
            print(json.dumps({"phase": "signals", "done": signal_number, "total": len(signal_files)}), flush=True)

    prices, frames = [], {}
    for i, ticker in enumerate(panel):
        meta = frozen["price_meta"][ticker]
        if meta["source"] not in {"ohlcv", "stocks"}:
            raise InputUnavailable(f"Unknown original price source: {meta['source']}")
        prefix = "data/baskets/ohlcv" if meta["source"] == "ohlcv" else "data/stocks"
        path = f"{prefix}/{ticker}.parquet"
        record: dict[str, Any] = {"ticker": ticker, "expected": meta, "path": path}
        try:
            item = reader.read(source_ref, path)
            frame, excluded = normalized_prices(item.raw, CUTOFF)
            obs = {"first": str(frame.index.min().date()),
                   "last": str(frame.index.max().date()), "rows": len(frame)}
            rows = primary.loc[primary["ticker"] == ticker, ["date", "close", "pos"]].drop_duplicates()
            dates = pd.DatetimeIndex(pd.to_datetime(rows["date"])).normalize()
            actual = frame["close"].reindex(dates).to_numpy(dtype=float)
            expected = rows["close"].to_numpy(dtype=float)
            matched = np.isclose(actual, expected, rtol=1e-9, atol=1e-8, equal_nan=False)
            positions = frame.index.get_indexer(dates)
            pos_match = positions == rows["pos"].to_numpy(dtype=int)
            metadata_match = all(obs[k] == meta[k] for k in obs)
            record.update({
                **item.receipt(), "observed": obs,
                "post_cutoff_rows_excluded": excluded, "metadata_match": metadata_match,
                "frozen_episode_anchors": len(rows), "close_anchors_matched": int(matched.sum()),
                "session_positions_matched": int(pos_match.sum()),
                "anchor_mismatches": [
                    {"date": str(d.date()), "frozen_close": float(e), "archived_close": float(a) if np.isfinite(a) else None}
                    for d, e, a, ok in zip(dates, expected, actual, matched, strict=True) if not ok
                ][:8],
                "state": "archive_matches_frozen_observations"
                if metadata_match and matched.all() and pos_match.all() else "archive_vintage_mismatch",
            })
            if record["state"] == "archive_matches_frozen_observations":
                frames[ticker] = frame
        except (InputUnavailable, ValueError, OSError, subprocess.SubprocessError) as exc:
            record.update({"state": "unavailable", "reason": str(exc)[:240]})
        prices.append(record)
        if report_progress and (i + 1) % 20 == 0:
            print(json.dumps({"phase": "prices", "done": i + 1, "total": len(panel),
                              "qualified": len(frames)}), flush=True)

    archive_index = archive_index or {}
    entries = archive_index.get("selected", [])
    if not entries:
        known_at = reader.command(["show", "-s", "--format=%cI", source_ref]).decode().strip()
        entries = [{"sha": source_ref, "known_at": known_at}]
    snapshots = []
    for i, entry in enumerate(entries):
        rec: dict[str, Any] = {"ref": entry["sha"], "known_at": entry["known_at"]}
        try:
            item = reader.read(entry["sha"], SNAPSHOT_PATH)
            body = json.loads(item.raw)
            result = qualify_snapshot(body, known_at=entry["known_at"], decision_at=decision_at,
                                      cutoff=CUTOFF, complete_original=True, panel=panel)
            rec.update({**item.receipt(), **result})
        except (InputUnavailable, ValueError, OSError, subprocess.SubprocessError) as exc:
            rec.update({"state": "unknown_input", "reason": str(exc)[:240]})
        snapshots.append(rec)
        if report_progress:
            print(json.dumps({"phase": "snapshots", "done": i + 1, "total": len(entries),
                              "state": rec["state"], "asof": rec.get("source_asof")}), flush=True)

    dates = sorted({x["source_asof"] for x in snapshots if x["state"] == "known_snapshot_selection"})
    available = set(dates)
    complete_windows = 0
    qualified_anchors = 0
    for row in anchors.itertuples():
        frame = frames.get(row.ticker)
        if frame is None:
            continue
        qualified_anchors += 1
        days = frame.index[max(0, int(row.pos) - 33): int(row.pos) + 1]
        if len(days) == 34 and all(str(day.date()) in available for day in days):
            complete_windows += 1

    return {
        "schema": "prophet.b17.frozen_input_recovery.v1",
        "implementation_sha256": IMPLEMENTATION_SHA256,
        "rule_ref": rule_ref, "rule_sources": rule_sources,
        "cutoff_intersection": replay_cutoff_intersection(snapshots, frames),
        "scope": "input_recovery_and_fixed_rule_archive_selection; not historical served-deck or efficacy acceptance",
        "decision_cutoff": decision_at, "frozen_price_edge": CUTOFF,
        "frozen_result": frozen_file.receipt(), "frozen_episodes": {
            **episode_file.receipt(), "rows": len(episodes),
            "primary_construction_counts": {k: int(v) for k, v in counts.items()},
            "c0_denominator": len(anchors), "first_c0": str(anchors["date"].min()),
            "last_c0": str(anchors["date"].max()),
        },
        "panel": panel, "unpriced_exclusions": frozen["universe"]["store_names_unpriced"],
        "separate_addons": frozen["universe"]["addon_exemplars"],
        "baseline_replication": {"identity": "C1_relaxed_R2i_not_union_or_shipped_roster", **baseline},
        "signal_store": {"source_ref": source_ref, "count": len(signals),
                         "asof_counts": dict(sorted(signal_dates.items())), "files": signals},
        "price_archive": {
            "source_ref": source_ref, "qualified_count": len(frames), "total": len(panel),
            "states": dict(Counter(x["state"] for x in prices)), "files": prices,
            "proof_limit": "Git identities and all frozen metadata/episode-close/session-position anchors are checked. The study did not record full per-price-file digests, so byte identity to its original working files is not asserted.",
        },
        "admission_archive": {
            "selection_policy": archive_index.get("selection_policy", "exact_frozen_signal_origin_tree"),
            "history_commit_count": archive_index.get("history_commit_count"),
            "history_commit_index_complete": archive_index.get("history_complete", False),
            "history_index_sha256": hashlib.sha256(json.dumps(archive_index, sort_keys=True).encode()).hexdigest(),
            "history_first_commit": archive_index.get("history_first_commit"),
            "candidate_snapshot_count": len(snapshots), "distinct_qualified_asof_count": len(dates),
            "qualified_asof_dates": dates, "snapshots": snapshots,
            "full_population_scope": "original complete buy[] bytes, not study-panel-only reconstruction",
        },
        "measurement_readiness": {
            "ready": False, "b17_disposition": "STILL_LIVE",
            "c0_denominator": len(anchors), "price_qualified_c0": qualified_anchors,
            "c0_with_complete_34_session_admission_date_window": complete_windows,
            "coverage_result": None, "lead_result": None,
            "missing": [
                "Complete historically bound admission inputs across the original 2014+ frozen panel.",
                "Availability/first-surface clocks for product lead, not a backdated union fire.",
                "Original per-file price digests or an explicit archive-vintage qualification.",
                "A frozen full-population measurement and independent scientific adjudication before seq2.",
            ],
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=REPO)
    parser.add_argument("--frozen-ref", default=FROZEN_REF)
    parser.add_argument("--source-ref", default=SOURCE_REF)
    parser.add_argument("--archive-index", type=Path)
    parser.add_argument("--github-fallback", action="store_true",
                        help="Read absent immutable objects via the existing authenticated gh client")
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    index = json.loads(args.archive_index.read_text()) if args.archive_index else None
    report = recover(GitReader(args.repo, args.github_fallback), frozen_ref=args.frozen_ref,
                     source_ref=args.source_ref, archive_index=index, report_progress=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, sort_keys=True, indent=2, allow_nan=False) + "\n")
    print(json.dumps({
        "report": str(args.report), "sha256": hashlib.sha256(args.report.read_bytes()).hexdigest(),
        "prices_qualified": report["price_archive"]["qualified_count"],
        "snapshot_dates": report["admission_archive"]["distinct_qualified_asof_count"],
        "readiness": report["measurement_readiness"],
    }), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
