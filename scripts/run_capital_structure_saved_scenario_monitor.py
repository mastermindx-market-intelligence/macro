"""Entry point for the saved-scenario monitor step (SPEC_U2 §1 "U2-3").

    python -m scripts.run_capital_structure_saved_scenario_monitor [--dry-run]

Dormant by default (the run_fif_saved_research_notifications.py truthiness
rule): the step is a byte-for-byte no-op — no store read or write, no
Supabase request, no send, no file write — unless BOTH
CS_SAVED_SCENARIO_ENABLE=1 AND ALERT_DRAIN_ENABLE=1 are set.  The flags are
checked FIRST, before the producer module is imported, so a dormant run never
even loads the producer's IO.  Neither flag is ever set by this repo's code,
workflows or config; arming is the operator's act (the table DDL and the
secret are human-only enrollment, SPEC_U2 §3).

Imports ONLY engine.capital_structure.saved_scenario_monitor — never a
sender.  This step enqueues public.alert_outbox rows; the incumbent drain
(scripts/drain_alert_outbox.py) sends them.  ``--dry-run`` classifies and
plans but enqueues nothing and writes no outcome — the lane's own proof
shape.  Always exits 0: a missing table, missing credentials, an unapplied
DDL or a missing published generation is a known deployment state (typed
unavailable / typed outage), not a build failure.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="classify and plan, but enqueue nothing and write no outcome",
    )
    args = parser.parse_args(argv)

    enabled = (
        os.environ.get("CS_SAVED_SCENARIO_ENABLE") == "1"
        and os.environ.get("ALERT_DRAIN_ENABLE") == "1"
    )
    if not enabled:
        print(
            "cs-saved-scenario-monitor: DORMANT (CS_SAVED_SCENARIO_ENABLE and "
            "ALERT_DRAIN_ENABLE not both \"1\") — no reads, no writes",
            flush=True,
        )
        return 0

    # Imported ONLY past the gate so a dormant run loads no producer IO.
    from engine.capital_structure import saved_scenario_monitor as producer  # noqa: PLC0415

    result = producer.run(root=_ROOT / "data" / "capital_structure", dry_run=args.dry_run)

    if result.read_state == producer.READ_UNAVAILABLE:
        # The literal READ_UNAVAILABLE token is printed (not just its
        # error_class) so a log grep for the read-state vocabulary finds this
        # line — the FIF runner's discipline.
        print(
            "::warning title=cs-saved-scenario-monitor-read-unavailable::"
            "%s (%s) — %d enqueued so far, run incomplete"
            % (producer.READ_UNAVAILABLE, result.error_class, result.enqueued_n),
            flush=True,
        )
    print(
        "cs-saved-scenario-monitor: outcome=%s read_state=%s rows=%d "
        "classified=%d planned=%d enqueued=%d duplicate=%d unreadable=%d "
        "state=%s inputs=%s changes=%s%s"
        % (
            result.outcome,
            result.read_state,
            result.rows_n,
            result.classified_n,
            result.planned_n,
            result.enqueued_n,
            result.duplicate_n,
            result.unreadable_n,
            result.state_state,
            result.inputs_state,
            result.changes_state,
            "".join(
                "\ncs-saved-scenario-monitor: note: %s" % note
                for note in result.notes
            ),
        ),
        flush=True,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
