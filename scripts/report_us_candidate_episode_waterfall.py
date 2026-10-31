"""Entry Timing W1 — the candidate-episode intake waterfall, by session (read-only).

Measurement only; authority none.  Reads the SELECTED B1 candidate-episode
generation (``data/us_prophet_rank/episodes/HEAD.json`` -> ``generations/<id>``)
and reports, per observation session, how many source rows reached the
episode store (``mapped``) and how many were refused under which typed intake
class (``IDENTITY_UNRESOLVED`` / ``ISSUER_UNRESOLVED`` /
``MISSING_STRUCTURAL_ANCHOR`` / ``ACTIVE_EPISODE_DIFFERENT_ANCHOR``), with the
explicit denominator (``inputs = mapped + refused``) the brief asks for
before any gated outcome is inspected.

The identity replay re-resolves every refused (ticker, session) pair through
the ONE Data OS alias reader (``engine.us_candidate_episode_intake.
load_identity_spine`` -> ``VendorAliasTable.resolve("membership", …)``) against
the CURRENT committed reference and splits the ``IDENTITY_UNRESOLVED`` rows:

* ``no_current_reference`` — no membership alias knows the ticker today either:
  a reference-coverage gap (Data OS owner), not an intake defect;
* ``reference_widened_after_session`` — the alias exists today but was ingested
  after the session: the refusal was lawful as-known at the time (the as-known
  snapshot is pinned in the generation receipt); only prospective rows benefit;
* ``resolvable_at_session`` — the alias was already ingested on or before the
  session and resolves today: the only class that can indicate an intake or
  snapshot defect, to be examined row by row.

Nothing here reads outcomes, prices, grades or the W3 paired race; nothing is
written.  The output is a run document (stdout), JSON with ``--json``.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

SCHEMA = "us.prophet_entry_timing_w1_waterfall/v1"
REFUSAL_CLASSES = (
    "IDENTITY_UNRESOLVED",
    "ISSUER_UNRESOLVED",
    "MISSING_STRUCTURAL_ANCHOR",
    "ACTIVE_EPISODE_DIFFERENT_ANCHOR",
)
IDENTITY_VENDOR = "membership"  # the vendor the intake resolves through


def _jsonl(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def selected_generation_dir(data_root: Path) -> Path:
    head = json.loads((data_root / "us_prophet_rank" / "episodes" / "HEAD.json").read_text("utf-8"))
    return data_root / "us_prophet_rank" / "episodes" / "generations" / str(head["generation_id"])


def _event_session(event: dict) -> str | None:
    payload = event.get("payload") or {}
    for key in ("observation_session", "opened_session"):
        value = payload.get(key)
        if value:
            return str(value)[:10]
    occurred = event.get("occurred_at")
    return str(occurred)[:10] if occurred else None


def load_generation(generation_dir: Path) -> tuple[list[dict], list[dict]]:
    events = [row for path in sorted((generation_dir / "events").glob("*.jsonl")) for row in _jsonl(path)]
    suppressions = [row for path in sorted((generation_dir / "suppressions").glob("*.jsonl"))
                    for row in _jsonl(path)]
    return events, suppressions


def _alias_first_ingest(data_root: Path) -> dict[str, date]:
    """Earliest ingested_at per membership vendor_symbol (for the as-known split)."""
    import pandas as pd  # local: the parquet reader is only needed for the replay

    frame = pd.read_parquet(data_root / "reference" / "vendor_aliases.parquet")
    frame = frame[frame["vendor"] == IDENTITY_VENDOR]
    first: dict[str, date] = {}
    for symbol, stamp in zip(frame["vendor_symbol"].astype(str), frame["ingested_at"]):
        day = stamp.date() if hasattr(stamp, "date") else date.fromisoformat(str(stamp)[:10])
        if symbol not in first or day < first[symbol]:
            first[symbol] = day
    return first


def identity_replay(data_root: Path, suppressions: list[dict]) -> dict:
    from engine.us_candidate_episode_intake import load_identity_spine

    spine = load_identity_spine(data_root)
    first_ingest = _alias_first_ingest(data_root)
    pairs: Counter[tuple[str, str]] = Counter()
    for row in suppressions:
        if row.get("reason") == "IDENTITY_UNRESOLVED":
            pairs[(str(row.get("ticker_at_observation")), str(row.get("observation_session"))[:10])] += 1
    rows_by_class: Counter[str] = Counter()
    pairs_by_class: Counter[str] = Counter()
    by_session: dict[str, Counter] = defaultdict(Counter)
    resolvable_examples: list[dict] = []
    for (ticker, session), count in sorted(pairs.items()):
        on = date.fromisoformat(session)
        security = spine.aliases.resolve(IDENTITY_VENDOR, ticker, on=on)
        if not security:
            klass = "no_current_reference"
        elif first_ingest.get(ticker) is not None and first_ingest[ticker] > on:
            klass = "reference_widened_after_session"
        else:
            klass = "resolvable_at_session"
            if len(resolvable_examples) < 25:
                resolvable_examples.append({"ticker": ticker, "session": session, "security_id": security,
                                            "alias_first_ingested": str(first_ingest.get(ticker)),
                                            "rows": count})
        rows_by_class[klass] += count
        pairs_by_class[klass] += 1
        by_session[session][klass] += count
    receipts = []
    for receipt in spine.source_receipts:
        if "vendor_aliases" not in str(receipt.get("path", "")):
            continue
        receipt = dict(receipt)
        try:  # portable receipt: the path relative to the data root's parent, never a host path
            receipt["path"] = str(Path(str(receipt["path"])).resolve().relative_to(data_root.resolve().parent))
        except ValueError:
            receipt["path"] = Path(str(receipt["path"])).name
        receipts.append(receipt)
    return {
        "vendor": IDENTITY_VENDOR,
        "reference": receipts,
        "identity_unresolved_rows": sum(pairs.values()),
        "distinct_ticker_sessions": len(pairs),
        "distinct_tickers": len({t for t, _ in pairs}),
        "rows_by_class": dict(sorted(rows_by_class.items())),
        "ticker_sessions_by_class": dict(sorted(pairs_by_class.items())),
        "by_session": {s: dict(sorted(c.items())) for s, c in sorted(by_session.items())},
        "resolvable_at_session_examples": resolvable_examples,
    }


def waterfall(events: list[dict], suppressions: list[dict]) -> dict:
    mapped: dict[str, Counter] = defaultdict(Counter)
    refused: dict[str, Counter] = defaultdict(Counter)
    tickers: dict[str, set] = defaultdict(set)
    unsessioned_events = 0
    for event in events:
        session = _event_session(event)
        if session is None:
            unsessioned_events += 1
            continue
        mapped[session][str(event.get("source_system"))] += 1
    for row in suppressions:
        session = str(row.get("observation_session"))[:10]
        refused[session][str(row.get("reason"))] += 1
        refused[session]["__source__" + str(row.get("source_system"))] += 1
        tickers[session].add(str(row.get("ticker_at_observation")))
    sessions = []
    for session in sorted(set(mapped) | set(refused)):
        m = mapped[session]
        r = refused[session]
        by_class = {k: int(r.get(k, 0)) for k in REFUSAL_CLASSES}
        other = {k: int(v) for k, v in r.items() if k not in REFUSAL_CLASSES and not k.startswith("__source__")}
        n_mapped = int(sum(m.values()))
        n_refused = int(sum(by_class.values()) + sum(other.values()))
        sessions.append({
            "session": session,
            "inputs": n_mapped + n_refused,
            "mapped": n_mapped,
            "mapped_by_source": dict(sorted(m.items())),
            "refused": n_refused,
            "refused_by_class": by_class,
            "refused_other": other,
            "refused_by_source": {k[len("__source__"):]: int(v) for k, v in sorted(r.items()) if k.startswith("__source__")},
            "distinct_refused_tickers": len(tickers[session]),
        })
    totals = {
        "sessions": len(sessions),
        "inputs": sum(s["inputs"] for s in sessions),
        "mapped": sum(s["mapped"] for s in sessions),
        "refused": sum(s["refused"] for s in sessions),
        "refused_by_class": {k: sum(s["refused_by_class"][k] for s in sessions) for k in REFUSAL_CLASSES},
        "unsessioned_events": unsessioned_events,
    }
    return {"sessions": sessions, "totals": totals}


def build(data_root: Path, *, replay: bool = True) -> dict:
    generation_dir = selected_generation_dir(data_root)
    events, suppressions = load_generation(generation_dir)
    doc = {
        "schema": SCHEMA,
        "authority": "measurement only / none",
        "outcome_blind": True,
        "generation_id": generation_dir.name,
        "events": len(events),
        "suppressions": len(suppressions),
        "waterfall": waterfall(events, suppressions),
    }
    if replay:
        doc["identity_replay"] = identity_replay(data_root, suppressions)
    return doc


def render(doc: dict) -> str:
    lines = [f"W1 intake waterfall — generation {doc['generation_id']} (measurement only; outcome-blind)",
             f"{'session':10} {'inputs':>7} {'mapped':>7} {'IDENT':>6} {'ISSUER':>6} {'ANCHOR':>6} {'ACTIVE':>6} {'tickers':>7}"]
    for s in doc["waterfall"]["sessions"]:
        c = s["refused_by_class"]
        lines.append(f"{s['session']:10} {s['inputs']:>7} {s['mapped']:>7} {c['IDENTITY_UNRESOLVED']:>6} "
                     f"{c['ISSUER_UNRESOLVED']:>6} {c['MISSING_STRUCTURAL_ANCHOR']:>6} "
                     f"{c['ACTIVE_EPISODE_DIFFERENT_ANCHOR']:>6} {s['distinct_refused_tickers']:>7}")
    t = doc["waterfall"]["totals"]
    lines.append(f"TOTAL      {t['inputs']:>7} {t['mapped']:>7} " + " ".join(f"{t['refused_by_class'][k]:>6}" for k in REFUSAL_CLASSES))
    replay = doc.get("identity_replay")
    if replay:
        lines.append("identity replay (IDENTITY_UNRESOLVED rows vs the CURRENT membership reference): "
                     + json.dumps(replay["rows_by_class"], sort_keys=True))
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=None, help="data root (default: <repo>/data)")
    ap.add_argument("--json", action="store_true", help="emit the full run document as JSON")
    ap.add_argument("--no-replay", action="store_true", help="skip the identity replay (no reference read)")
    args = ap.parse_args(argv)
    data_root = Path(args.root).resolve() if args.root else ROOT / "data"
    doc = build(data_root, replay=not args.no_replay)
    print(json.dumps(doc, indent=2, sort_keys=True, default=str) if args.json else render(doc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
