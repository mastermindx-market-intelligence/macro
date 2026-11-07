"""Bounded, read-only PRIVATE research runner over already-held source objects.

Run from Macro with --manifest, --source-repository and --store-root. It prints
private derived JSON only; it never publishes, downloads a missing source, writes
original files or treats caller-provided data as an entitlement/quality grant.
The input manifest is a study input description, not a new source registry.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys

import pandas as pd
import pyarrow.parquet as pq

from lib.us_cash_calendar import expected_last_session, is_session, sessions_between
from research.factor_atlas.session3.retrospective import build_study, _COLUMNS

_GIT = re.compile(r"^[a-f0-9]{40}$")
_SHA = re.compile(r"^[a-f0-9]{64}$")
_ROOT = re.compile(r"^[A-Z][A-Z0-9.-]{0,11}$")
_MAX_GIT_BYTES = 16 * 1024 * 1024
_MAX_GREEK_BYTES = 256 * 1024 * 1024


def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError("duplicate JSON field")
        result[key] = value
    return result


def _reject_nonfinite(value):
    raise ValueError("nonfinite JSON value")


def _json(raw):
    return json.loads(raw, object_pairs_hook=_pairs, parse_constant=_reject_nonfinite)


def _date(value):
    if not isinstance(value, str) or len(value) != 10:
        raise ValueError("canonical calendar date required")
    result = date.fromisoformat(value)
    if result.isoformat() != value:
        raise ValueError("canonical calendar date required")
    return result


def _git_blob(repository: Path, sha: str) -> bytes:
    if not isinstance(sha, str) or _GIT.fullmatch(sha) is None:
        raise ValueError("exact Git object identity required")
    env = dict(os.environ, GIT_NO_LAZY_FETCH="1", GIT_NO_REPLACE_OBJECTS="1",
               GIT_OPTIONAL_LOCKS="0", GIT_TERMINAL_PROMPT="0")
    def read(*args):
        p = subprocess.run(["git", "-C", str(repository), "cat-file", *args, sha],
                           capture_output=True, check=False, timeout=15, env=env)
        if p.returncode:
            raise ValueError("required local Git object unavailable; no network fallback")
        return p.stdout
    size = int(read("-s").strip())
    if not 0 < size <= _MAX_GIT_BYTES:
        raise ValueError("Git source object exceeds research byte bound")
    raw = read("blob")
    actual = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
    if len(raw) != size or actual != sha:
        raise ValueError("Git source object digest mismatch")
    return raw


def _stat(s):
    return (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)


def _greeks(store: Path, root: str, expected: str, anchor: date):
    if not isinstance(expected, str) or _SHA.fullmatch(expected) is None:
        raise ValueError("Greek source digest required")
    original = store / "greeks" / root / f"{anchor.year}.parquet"
    if not original.exists():
        return None, {"state": "MISSING", "expected_sha256": expected}
    # The incumbent store intentionally links its whole Greek tier to an external volume.
    # Admit that existing tier binding, but never a nested root/file escape outside it.
    tier = (store / "greeks").resolve()
    if not original.resolve().is_relative_to(tier):
        raise ValueError("Greek source must remain within the original Greek tier")
    with original.open("rb") as f:
        before = _stat(os.fstat(f.fileno()))
        if not 0 < before[2] <= _MAX_GREEK_BYTES:
            raise ValueError("Greek source exceeds research byte bound")
        h = hashlib.sha256()
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
        if h.hexdigest() != expected:
            raise ValueError("Greek source digest mismatch")
        f.seek(0)
        table = pq.read_table(f, filters=[("date", "=", datetime.combine(anchor, datetime.min.time()))],
                              columns=sorted(_COLUMNS))
        after = _stat(os.fstat(f.fileno()))
        if before != after or before != _stat(original.stat()):
            raise ValueError("Greek source changed during research read")
    return table.to_pandas(), {"state": "READ_VERIFIED", "sha256": expected,
                              "bytes": before[2], "anchor_rows": table.num_rows,
                              "artifact": f"greeks/{root}/{anchor.year}.parquet"}


def load_study(*, manifest: dict, source_repository: Path, store_root: Path,
               captured_at: datetime | None = None) -> dict:
    allowed = {"schema", "anchor", "basket_id", "membership_blob", "roots", "price_column"}
    if not isinstance(manifest, dict) or set(manifest) != allowed:
        raise ValueError("exact retrospective input manifest fields required")
    if manifest["schema"] != "factor_atlas.s3.retrospective_inputs/v1" or manifest["basket_id"] != "mag7":
        raise ValueError("this bounded reader supports only the declared Mag7 pilot")
    anchor = _date(manifest["anchor"])
    if not is_session(anchor):
        raise ValueError("requested anchor is not an incumbent US cash session")
    if manifest["price_column"] not in ("close", "close_price"):
        raise ValueError("explicit existing close column required")
    source_repository, store_root = Path(source_repository), Path(store_root)
    if not source_repository.is_dir() or not store_root.is_dir():
        raise ValueError("existing original source repository and store required")
    raw_registry = _git_blob(source_repository, manifest["membership_blob"])
    document = _json(raw_registry)
    basket = document.get("baskets", {}).get("mag7", {})
    if basket.get("weighting") != "equal" or not isinstance(basket.get("members"), list):
        raise ValueError("existing explicit equal-weight house membership required")
    roots, seen = [], set()
    for row in basket["members"]:
        if not isinstance(row, dict) or not isinstance(row.get("ticker"), str) or not _ROOT.fullmatch(row["ticker"]):
            raise ValueError("invalid registry root identity")
        root = row["ticker"]
        if root in seen:
            raise ValueError("duplicate registry member")
        seen.add(root)
        added = _date(row["added"])
        removed = _date(row["removed"]) if row.get("removed") is not None else None
        if removed is not None and removed <= added:
            raise ValueError("invalid registry effective interval")
        if added <= anchor and (removed is None or anchor < removed):
            roots.append(root)
    if not 3 <= len(roots) <= 10:
        raise ValueError("bounded Mag7 registry population required")
    input_roots = manifest["roots"]
    if not isinstance(input_roots, dict) or not set(input_roots).issubset(roots):
        raise ValueError("source roots do not match effective membership")
    Greeks, prices, receipts = {}, {}, {}
    for root in sorted(roots):
        item = input_roots.get(root)
        if item is None:
            receipts[root] = {"state": "SOURCE_NOT_SUPPLIED"}
            continue
        if not isinstance(item, dict) or set(item) != {"price_blob", "greeks_sha256"}:
            raise ValueError("exact source root fields required")
        greeks, grec = _greeks(store_root, root, item["greeks_sha256"], anchor)
        if greeks is not None:
            Greeks[root] = greeks
        raw_price = _git_blob(source_repository, item["price_blob"])
        frame = pd.read_parquet(io.BytesIO(raw_price))
        col = manifest["price_column"]
        if col not in frame or not isinstance(frame.index, pd.DatetimeIndex):
            raise ValueError("source price session index or selected column missing")
        prices[root] = frame[col]
        receipts[root] = {"greeks": grec, "price_git_blob": item["price_blob"],
                          "price_sha256": hashlib.sha256(raw_price).hexdigest(),
                          "price_bytes": len(raw_price), "price_column": col,
                          "price_rows": len(frame), "adjustment_vintage": None}
    # Calendar ownership stays with the existing US cash session module.
    sessions = sessions_between(anchor - timedelta(days=550), anchor)
    panel = pd.DataFrame(prices) if prices else pd.DataFrame(index=pd.DatetimeIndex([]))
    capture = captured_at if captured_at is not None else datetime.now(timezone.utc)
    result = build_study(weights={r: 1 / len(roots) for r in roots}, greeks=Greeks,
                         closes=panel, sessions=sessions, anchor=anchor, captured_at=capture)
    result["source_receipts"] = {
        "membership_git_blob": manifest["membership_blob"],
        "membership_sha256": hashlib.sha256(raw_registry).hexdigest(),
        "source_receipt_meaning": "byte identity at research read, not historical release or rights",
        "roots": receipts,
    }
    canonical = {k: v for k, v in result.items() if k != "captured_at"}
    result["measurement_sha256"] = hashlib.sha256(json.dumps(canonical, sort_keys=True, separators=(",", ":"),
                                                             allow_nan=False).encode()).hexdigest()
    result["calendar_status"] = {"latest_completed_session_at_read": expected_last_session(capture).isoformat(),
                                 "anchor_is_latest_completed": anchor == expected_last_session(capture)}
    return result



def render_markdown(result: dict) -> str:
    """Human-readable private research output; not a new public product surface."""
    def pct(value):
        return "Unavailable" if value is None else f"{100 * value:.2f}%"
    c=result["coverage"]
    lines=["# Factor Atlas — private basket options study", "",
           "**PRIVATE RETROSPECTIVE RESEARCH — not a directly traded basket option.**", "",
           f"Reported source session: {result['anchor']}. Research capture: {result['captured_at']}.",
           "Historical availability: unknown. Original per-quote timestamps and source pricing certification are not established.", "",
           f"Usable research constituents: **{c['count']}/{c['total_count']}**, original basket-weight coverage **{100*c['weight']:.1f}%**.",
           f"Covered mean constituent IV: **{pct(result['research']['mean_iv'])}**. RMS: **{pct(result['research']['rms_iv'])}**.", "",
           "| Constituent | Research IV30, annualized | Source limitations / exclusions |",
           "|---|---:|---|"]
    for row in result["members"]:
        lines.append(f"| {row['root']} | {pct(row['iv30'])} | {', '.join(row['reasons']) or 'Retrospective; not product-qualified'} |")
    lines += ["", "## Covariance-based research estimates", "",
              "30 calendar days / 365. Historical correlation, not implied correlation or a calibrated probability band.", "",
              "| Return-session window | Modeled move | 10% identity-shrinkage sensitivity | Withheld reason |",
              "|---|---:|---:|---|"]
    for window, model in sorted(result["models"].items(), key=lambda kv:int(kv[0])):
        lines.append(f"| {window} | {pct(model['move'])} | {pct(model['shrunken_move'])} | {', '.join(model['reasons']) or 'Research estimate only'} |")
    lines += ["", "## Boundaries", "",
              "Missing source contracts or price sessions are not filled or removed from the basket. "
              "Dates select the reported retrospective cohort; they do not certify point-in-time knowledge. "
              "The strike and quote filters are declared research policy, not a calibration certificate.", "",
              "Qualified product IV and expected move remain unavailable. No publication, Prophet or position-sizing authority is granted."]
    if "measurement_sha256" in result:
        lines += ["", f"Measurement SHA-256: `{result['measurement_sha256']}`."]
    if "calendar_status" in result:
        lines += [f"Latest completed source session expected at capture: {result['calendar_status']['latest_completed_session_at_read']}."]
    return "\n".join(lines)+"\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--source-repository", type=Path, required=True)
    parser.add_argument("--store-root", type=Path, required=True)
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    args = parser.parse_args(argv)
    try:
        with args.manifest.open("rb") as source_file:
            raw = source_file.read(128 * 1024 + 1)
        if not 0 < len(raw) <= 128 * 1024:
            raise ValueError("bounded source input manifest required")
        result = load_study(manifest=_json(raw), source_repository=args.source_repository,
                            store_root=args.store_root)
        if args.format == "markdown":
            print(render_markdown(result), end="")
        else:
            print(json.dumps(result, sort_keys=True, indent=2, allow_nan=False))
        return 0
    except (ValueError, OSError, KeyError, TypeError, subprocess.SubprocessError) as error:
        print(f"RETROSPECTIVE_RESEARCH_REFUSED: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
