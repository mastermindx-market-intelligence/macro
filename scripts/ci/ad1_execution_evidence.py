"""AD-1T2 execution evidence — bind run -> host -> store -> receipt -> digest.

Why this exists rather than a host fingerprint in ``receipt_id``: the producer
deliberately keeps absolute paths OUT of that hash (see the ``m5`` comment in
``scripts/build_options_intel_brief.build``) so a host/path migration with
identical logical inputs does not churn the semantic receipt. The machine that
produced an artifact is therefore recorded as execution evidence against the
existing receipt and output digest, through the existing step-summary/run-log
facility. No new ledger and no new store.

The one rule this file must not break: it has to distinguish "this run produced
this artifact" from "this file was already sitting on disk". Printing a complete,
plausible receipt for the frozen artifact after a failed producer would be the
same green-looking-proof-of-a-stale-artifact shape the AD-1T2 lane exists to
eliminate, reproduced in miniature.

Reads ``PRODUCER_OUTCOME`` (the producer step's ``outcome``) and ``SKIP_REASON``
from the environment. Always exits 0: evidence must never cost the night.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib

BRIEF = pathlib.Path("site/options_intel_brief.json")


def main() -> int:
    outcome = os.environ.get("PRODUCER_OUTCOME") or "not-run"
    skip = os.environ.get("SKIP_REASON") or ""
    produced_by_this_run = outcome == "success" and not skip

    rec: dict[str, object] = {
        "produced_by_this_run": produced_by_this_run,
        "producer_outcome": outcome,
        "skip_reason": skip or None,
        "code_revision": os.environ.get("GITHUB_SHA"),
        "workflow_run": os.environ.get("GITHUB_RUN_ID"),
        "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
        "runner_name": os.environ.get("RUNNER_NAME"),
    }

    if BRIEF.exists():
        raw = BRIEF.read_bytes()
        rec["output_sha256"] = hashlib.sha256(raw).hexdigest()
        try:
            d = json.loads(raw)
        except Exception as exc:  # noqa: BLE001 — evidence must not crash the night
            rec["artifact"] = f"UNREADABLE: {exc}"
            d = {}
        if d:
            elig = d.get("eligibility") if isinstance(d.get("eligibility"), dict) else {}
            rec.update({
                "as_of_session": d.get("as_of_session"),
                "oi_counted_date": d.get("oi_counted_date"),
                "board_state": d.get("board_state"),
                "receipt_id": d.get("receipt_id"),
                "eligible": elig.get("eligible"),
                "source_coverage_pct": elig.get("source_coverage_pct"),
                "store_resolution": (d.get("_run") or {}).get("store_resolution"),
            })
    else:
        rec["artifact"] = "ABSENT"

    if not produced_by_this_run:
        # Say it at line start, where GitHub parses it — the fields below describe
        # whatever was already committed, NOT a publish by this run.
        print("::warning title=ad1-evidence::this run did not produce the artifact "
              f"(producer_outcome={outcome}, skip_reason={skip or 'none'}); the "
              "record below describes the PRE-EXISTING committed brief.")
    elif rec.get("eligible") == 0:
        # A healthy source with genuinely no qualifying opportunity is a valid
        # NO_SIGNAL, not a failure — but an empty board published over a
        # previously-populated one is worth an operator's eyes either way.
        print("::warning title=ad1-evidence::published board has eligible=0 "
              f"(board_state={rec.get('board_state')}, "
              f"coverage={rec.get('source_coverage_pct')}).")

    print("### AD-1 execution evidence\n")
    print("```json")
    print(json.dumps(rec, indent=2, sort_keys=True))
    print("```")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
