"""Entry point for the FIF saved-research notifications step (X2-n).

    python -m scripts.run_fif_saved_research_notifications

Dormant by default (S1, the run_thesis_condition_monitor.py:34 truthiness
rule): the step is a byte-for-byte no-op — no store read or write, no
Supabase request, no send, no R2 read, no file write — unless BOTH
FIF_SAVED_RESEARCH_ENABLE=1 AND ALERT_DRAIN_ENABLE=1 are set. The flags are
checked FIRST, before the producer module is imported, so a dormant run never
even loads the producer's IO. Neither flag is ever set by this repo's code,
workflows or config; arming is the operator's act (seat ruling R4).

Imports ONLY engine.fif_saved_research_notifications — never a sender. This
step enqueues public.alert_outbox rows; scripts/drain_alert_outbox.py (F08)
sends them. Always exits 0: a missing table, missing credentials, an unmerged
migration or a missing trigger input is a known deployment state (typed
unavailable / no-event), not a build failure.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))


def main(argv: list[str] | None = None) -> int:
    del argv  # no flags: the nightly step takes none
    enabled = (
        os.environ.get("FIF_SAVED_RESEARCH_ENABLE") == "1"
        and os.environ.get("ALERT_DRAIN_ENABLE") == "1"
    )
    if not enabled:
        print(
            "fif-saved-research: DORMANT (FIF_SAVED_RESEARCH_ENABLE and "
            "ALERT_DRAIN_ENABLE not both \"1\") — no reads, no writes",
            flush=True,
        )
        return 0

    # Imported ONLY past the gate so a dormant run loads no producer IO (S1).
    from engine import fif_saved_research_notifications as producer  # noqa: PLC0415

    result = producer.run(root=_ROOT, dry_run=False)

    if result.read_state == producer.READ_UNAVAILABLE:
        # The literal READ_UNAVAILABLE token is printed (not just its
        # error_class) so a log grep for the read-state vocabulary finds this
        # line — the thesis monitor's MINOR-3 discipline.
        print(
            "::warning title=fif-saved-research-read-unavailable::"
            "%s (%s) — %d enqueued so far, run incomplete"
            % (producer.READ_UNAVAILABLE, result.error_class, result.enqueued_n),
            flush=True,
        )

    # R3e: the typed high-finding suppression counts ride the SAME summary
    # line, in SUPPRESSION_KEYS order, so a gated backlog is counted in the
    # log rather than silently dropped. "0" when nothing was suppressed.
    suppressed_txt = ",".join(
        "%s=%d" % (key, result.suppressed.get(key, 0))
        for key in producer.SUPPRESSION_KEYS
        if result.suppressed.get(key, 0)
    ) or "0"
    print(
        "fif-saved-research: outcome=%s read_state=%s users=%d symbols=%d "
        "events=%d enqueued=%d duplicate=%d "
        "state=%s receipt=%s pointer=%s suppressed=%s"
        % (
            result.outcome,
            result.read_state,
            result.users_n,
            result.symbols_n,
            result.events_n,
            result.enqueued_n,
            result.duplicate_n,
            result.state_state,
            result.receipt_state,
            result.pointer_state,
            suppressed_txt,
        ),
        flush=True,
    )
    for note in result.notes:
        print("fif-saved-research: note: %s" % note, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
