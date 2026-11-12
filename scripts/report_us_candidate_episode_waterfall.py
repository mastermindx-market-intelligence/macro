"""Entry Timing W1 — the candidate-episode intake waterfall, by session (read-only).

Measurement only; authority none.  Reads the SELECTED B1 candidate-episode
generation (``data/us_prophet_rank/episodes/HEAD.json`` -> ``generations/<id>``)
and reports, per observation session, how many source rows reached the
episode store (``mapped``) and how many were refused under which typed intake
class (``IDENTITY_UNRESOLVED`` / ``ISSUER_UNRESOLVED`` /
``MISSING_STRUCTURAL_ANCHOR`` / ``ACTIVE_EPISODE_DIFFERENT_ANCHOR``), with the
explicit denominator (``inputs = mapped + refused``) the brief asks for
before any gated outcome is inspected.

The observation session is the session on which the intake READ the row:

* ``candidate`` / ``doors`` rows carry it directly (``opened_session`` for an
  ``OPENED`` event, else the ``occurred_at`` date; ``observation_session`` for
  a suppression);
* ``turn_watch`` rows do not.  The intake stamps them with the trigger clock
  (``occurred_at = known_at = min(trigger.last_date)``), which can precede the
  session the row was first read by months, and the ledger's
  ``observation_session`` for turn_watch suppressions is not uniformly the
  document's session either.  Both sides are therefore binned by the
  ``data_session`` of the turn_watch source document they were read from,
  recovered through the row's ``source_receipt`` (the document's
  ``content_sha256``) from ``episode_inputs/turn_watch/*.json`` — the tracked
  files by default, plus every historical version with ``--git-history REF``.
  A turn_watch row whose receipt is not recoverable is reported under
  ``unrecovered_turn_watch`` and kept OUT of the per-session table; nothing is
  guessed from the trigger clock.

The identity replay re-resolves every refused (ticker, session) pair through
the ONE Data OS alias reader (``engine.us_candidate_episode_intake.
load_identity_spine`` -> ``VendorAliasTable.resolve("membership", …)``) against
the CURRENT committed reference, on the same session clock, and splits the
``IDENTITY_UNRESOLVED`` rows:

* ``no_current_reference`` — no membership alias covers the ticker on that
  session today either: a reference-coverage gap (Data OS owner), not an
  intake defect;
* ``reference_widened_after_session`` — the alias resolves today but was
  ingested after the session; the refusal stood on the reference the nightly
  had, and the ledger is append-only, so it stays (the intake itself applies
  no as-known gate: a from-scratch rebuild would map these rows);
* ``resolvable_at_session`` — the alias resolves today and was ingested on or
  before the session (or carries no ingest stamp, counted here
  conservatively): the only class that can indicate an intake or snapshot
  defect, to be examined row by row.

Nothing here reads outcomes, prices, grades or the W3 paired race; nothing is
written.  The output is a run document (stdout), JSON with ``--json``.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import date
from hashlib import sha256
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

SCHEMA = "us.prophet_entry_timing_w1_waterfall/v2"
REFUSAL_CLASSES = (
    "IDENTITY_UNRESOLVED",
    "ISSUER_UNRESOLVED",
    "MISSING_STRUCTURAL_ANCHOR",
    "ACTIVE_EPISODE_DIFFERENT_ANCHOR",
)
IDENTITY_VENDOR = "membership"  # the vendor the intake resolves through
TURN_WATCH = "turn_watch"
TURN_WATCH_INPUTS = Path("us_prophet_rank") / "episode_inputs" / "turn_watch"


def _jsonl(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def selected_generation_dir(data_root: Path) -> Path:
    head = json.loads((data_root / "us_prophet_rank" / "episodes" / "HEAD.json").read_text("utf-8"))
    return data_root / "us_prophet_rank" / "episodes" / "generations" / str(head["generation_id"])


def load_generation(generation_dir: Path) -> tuple[list[dict], list[dict]]:
    events = [row for path in sorted((generation_dir / "events").glob("*.jsonl")) for row in _jsonl(path)]
    suppressions = [row for path in sorted((generation_dir / "suppressions").glob("*.jsonl"))
                    for row in _jsonl(path)]
    return events, suppressions


# ---------------------------------------------------------------- turn_watch clock


def _document_receipt(raw: bytes) -> tuple[str, str] | None:
    """(receipt, data_session) of one turn_watch source document, or None if it
    is not a well-formed document whose stored digest matches its content."""
    from engine.us_candidate_episode_intake import canonical_json  # the ONE digest definition

    try:
        document = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    if not isinstance(document, dict):
        return None
    digest = document.get("content_sha256")
    session = document.get("data_session")
    if not isinstance(digest, str) or not isinstance(session, str) or len(session) < 10:
        return None
    expected = sha256(canonical_json({k: v for k, v in document.items()
                                      if k != "content_sha256"}).encode("utf-8")).hexdigest()
    if expected != digest:
        return None
    return f"sha256:{digest}", session[:10]


def turn_watch_receipt_sessions(data_root: Path, *, git_ref: str | None = None) -> dict:
    """``{receipt: data_session}`` over the distinct turn_watch source documents.

    Tracked files under ``<data_root>/us_prophet_rank/episode_inputs/turn_watch``
    always; with ``git_ref`` also every historical blob of that directory
    reachable from the ref, full history without simplification (the nightly
    rewrites ``<session>.json`` in place, so an older receipt only survives in
    history, possibly on a side branch of a merge).  Documents whose stored
    ``content_sha256`` does not match their content are ignored, never guessed.
    """
    sessions: dict[str, str] = {}
    documents = 0
    directory = data_root / TURN_WATCH_INPUTS
    for path in sorted(directory.glob("*.json")) if directory.is_dir() else []:
        found = _document_receipt(path.read_bytes())
        if found is not None and found[0] not in sessions:
            documents += 1
            sessions[found[0]] = found[1]
    history = None
    if git_ref:
        repo = data_root.parent
        rel = str(Path(data_root.name) / TURN_WATCH_INPUTS)
        commits = subprocess.run(["git", "-C", str(repo), "rev-list", "--full-history", git_ref, "--", rel],
                                 capture_output=True, text=True, check=True).stdout.split()
        blobs: set[str] = set()
        for commit in commits:
            tree = subprocess.run(["git", "-C", str(repo), "ls-tree", "-r", commit, "--", rel],
                                  capture_output=True, text=True, check=True).stdout
            for line in tree.splitlines():
                blob = line.split("\t", 1)[0].split()[2]
                if blob in blobs:
                    continue
                blobs.add(blob)
                raw = subprocess.run(["git", "-C", str(repo), "cat-file", "-p", blob],
                                     capture_output=True, check=True).stdout
                found = _document_receipt(raw)
                if found is not None and found[0] not in sessions:
                    documents += 1
                    sessions[found[0]] = found[1]
        history = {"ref": git_ref, "commits": len(commits), "blobs": len(blobs)}
    return {"sessions": sessions, "documents": documents, "git_history": history}


def _row_session(row: dict, receipt_sessions: dict[str, str], *, event: bool) -> str | None:
    """The observation session of one mapped event or one suppression row.

    turn_watch rows: the source document's ``data_session`` via the receipt, or
    None when unrecoverable.  Other sources: the row's own session field."""
    if str(row.get("source_system")) == TURN_WATCH:
        return receipt_sessions.get(str(row.get("source_receipt")))
    if event:
        opened = (row.get("payload") or {}).get("opened_session")
        if opened:
            return str(opened)[:10]
        occurred = row.get("occurred_at")
        return str(occurred)[:10] if occurred else None
    session = row.get("observation_session")
    return str(session)[:10] if session else None


# ---------------------------------------------------------------- identity replay


def _alias_first_ingest(data_root: Path) -> dict[str, date]:
    """Earliest ingested_at per membership vendor_symbol (for the as-known split).
    A row without an ingest stamp contributes nothing (the replay then counts the
    pair conservatively as ``resolvable_at_session``)."""
    import pandas as pd  # local: the parquet reader is only needed for the replay

    frame = pd.read_parquet(data_root / "reference" / "vendor_aliases.parquet")
    frame = frame[frame["vendor"] == IDENTITY_VENDOR]
    first: dict[str, date] = {}
    for symbol, stamp in zip(frame["vendor_symbol"].astype(str), frame["ingested_at"]):
        if stamp is None or pd.isna(stamp):
            continue
        day = stamp.date() if hasattr(stamp, "date") else date.fromisoformat(str(stamp)[:10])
        if symbol not in first or day < first[symbol]:
            first[symbol] = day
    return first


def identity_replay(data_root: Path, suppressions: list[dict], receipt_sessions: dict[str, str]) -> dict:
    from engine.us_candidate_episode_intake import load_identity_spine

    spine = load_identity_spine(data_root)
    first_ingest = _alias_first_ingest(data_root)
    pairs: Counter[tuple[str, str]] = Counter()
    unrecovered = 0
    for row in suppressions:
        if row.get("reason") != "IDENTITY_UNRESOLVED":
            continue
        session = _row_session(row, receipt_sessions, event=False)
        if session is None:
            unrecovered += 1
            continue
        pairs[(str(row.get("ticker_at_observation")), session)] += 1
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
        "identity_unresolved_rows_unrecovered_session": unrecovered,
        "distinct_ticker_sessions": len(pairs),
        "distinct_tickers": len({t for t, _ in pairs}),
        "rows_by_class": dict(sorted(rows_by_class.items())),
        "ticker_sessions_by_class": dict(sorted(pairs_by_class.items())),
        "by_session": {s: dict(sorted(c.items())) for s, c in sorted(by_session.items())},
        "resolvable_at_session_examples": resolvable_examples,
    }


# ---------------------------------------------------------------- waterfall


def waterfall(events: list[dict], suppressions: list[dict], receipt_sessions: dict[str, str]) -> dict:
    mapped: dict[str, Counter] = defaultdict(Counter)
    refused: dict[str, Counter] = defaultdict(Counter)
    tickers: dict[str, set] = defaultdict(set)
    unsessioned_events = 0
    unsessioned_suppressions = 0
    unrecovered = Counter()
    clock = Counter()
    for event in events:
        session = _row_session(event, receipt_sessions, event=True)
        if session is None:
            if str(event.get("source_system")) == TURN_WATCH:
                unrecovered["events"] += 1
            else:
                unsessioned_events += 1
            continue
        if str(event.get("source_system")) == TURN_WATCH:
            clock["turn_watch_events_recovered"] += 1
            if str(event.get("occurred_at"))[:10] < session:
                clock["turn_watch_events_trigger_before_session"] += 1
        mapped[session][str(event.get("source_system"))] += 1
    for row in suppressions:
        session = _row_session(row, receipt_sessions, event=False)
        if session is None:
            if str(row.get("source_system")) == TURN_WATCH:
                unrecovered["suppressions"] += 1
            else:
                unsessioned_suppressions += 1
            continue
        if str(row.get("source_system")) == TURN_WATCH:
            clock["turn_watch_suppressions_recovered"] += 1
            if str(row.get("observation_session"))[:10] != session:
                clock["turn_watch_suppressions_ledger_session_differs"] += 1
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
        "unsessioned_suppressions": unsessioned_suppressions,
        "unrecovered_turn_watch": {"events": int(unrecovered["events"]),
                                   "suppressions": int(unrecovered["suppressions"])},
    }
    clock_doc = {
        "turn_watch_session_basis": "source document data_session via source_receipt",
        "other_sources_session_basis": "opened_session / occurred_at date (events); observation_session (suppressions)",
        **{k: int(clock[k]) for k in ("turn_watch_events_recovered", "turn_watch_events_trigger_before_session",
                                      "turn_watch_suppressions_recovered",
                                      "turn_watch_suppressions_ledger_session_differs")},
    }
    return {"sessions": sessions, "totals": totals, "clock": clock_doc}


def build(data_root: Path, *, replay: bool = True, git_ref: str | None = None) -> dict:
    generation_dir = selected_generation_dir(data_root)
    events, suppressions = load_generation(generation_dir)
    receipts = turn_watch_receipt_sessions(data_root, git_ref=git_ref)
    doc = {
        "schema": SCHEMA,
        "authority": "measurement only / none",
        "outcome_blind": True,
        "generation_id": generation_dir.name,
        "events": len(events),
        "suppressions": len(suppressions),
        "turn_watch_receipts": {"documents": receipts["documents"], "receipts": len(receipts["sessions"]),
                                "git_history": receipts["git_history"]},
        "waterfall": waterfall(events, suppressions, receipts["sessions"]),
    }
    if replay:
        doc["identity_replay"] = identity_replay(data_root, suppressions, receipts["sessions"])
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
    u = t["unrecovered_turn_watch"]
    lines.append(f"turn_watch rows binned by source-document session: clock={json.dumps(doc['waterfall']['clock'], sort_keys=True)}; "
                 f"unrecovered (excluded above): events={u['events']} suppressions={u['suppressions']}")
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
    ap.add_argument("--git-history", default=None, metavar="REF",
                    help="also recover turn_watch receipts from every historical version of the "
                         "episode_inputs/turn_watch documents reachable from REF (read-only git)")
    args = ap.parse_args(argv)
    data_root = Path(args.root).resolve() if args.root else ROOT / "data"
    doc = build(data_root, replay=not args.no_replay, git_ref=args.git_history)
    print(json.dumps(doc, indent=2, sort_keys=True, default=str) if args.json else render(doc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
