# OIF P1–P6 family prereg V1: blindness audit and review status

This audit was written by ORCH-1, the Opus sub-orchestrator under the Options
Intelligence CEO seat (root `a1c77f0e-56b9-4edf-8d4f-3d31a338a8ed`), on
2026-11-01.

It is an addendum. It does not edit the sealed files: the preregistration is
`OIF_P1_P6_FAMILY_PREREG_V1.md` (sha256
`aea58e59bf9d2af190a603640a7039c35bed5dcb842fc6ec6e77cb0b613fb0cd`) and its
seal is `OIF_P1_P6_FAMILY_PREREG_V1.seal.json` (sha256
`f68d28089e5e8aba79f4f219db57b4b0690259bb2dc95d0c379a4e08c851812d`). Both were
committed at `2a97665844be80c8a52a829c26dfb9511b139c0f` (2026-11-01T08:46:26Z)
and are unchanged.

It completes the item that §12 of the preregistration left pending: "ORCH-1
log audit + independent Fabric review".

Claim classes: OBSERVED means read from a named artifact; INTERPRETED is
labelled as such.

## 1. Drafting-lane log audit: LIMITED, no contradicting evidence

The draft was produced by Fabric lane `oi1-l3a-r1` (fix_build, C1, placed on
m1/MiniMax-M3, rc 0, result sha256 prefix `250c4968b61fed6e`).

OBSERVED:
- The retained Fabric lane log (6,153 B) contains only transport, lease and
  poll events. It holds no tool-call transcript.
- `process.jsonl` (818 B) is a process receipt only.
- The lane's own return says it accessed no repository, network or data.

INTERPRETED: the retained artifacts can neither confirm nor refute the
worker's statement that it read no outcome table. No retained record shows an
out-of-packet read. The audit is limited because no tool transcript was
retained, not because anything was found.

## 2. Disclosure: metadata reads by the framing orchestrator before the seal

The seal states that the framing orchestrator read specification documents
only, and no outcome tables, before the seal. That statement is qualified as
follows. The seal file itself is not edited.

OBSERVED. At 2026-11-01T08:39:17Z, before the seal commit at 08:46:26Z,
ORCH-1 staged the committed `data/flow_signals/` blobs (`gate.json`,
`ledger.parquet`, `grades.parquet`) and read the following, which is metadata
only:

| File | What was read |
| --- | --- |
| `gate.json` | Top-level schema id `flow_signals.gate/v2`, as-of `2026-10-18`, status `building_history`, `elapsed_sec` 7.02, and the key/type layout |
| Both parquet files | Column schemas and row counts (the ledger has 103,893 rows) |

What was not read:
- No outcome value, return, score, hit rate, calibration value or monitor value.
- No per-row value of any column.

INTERPRETED. These files belong to the existing `flow_signals` producer, which
is not an input defined for P1–P6 (§2–§7 name their own sources). They carry no
P1–P6 outcome. The reads therefore did not expose any quantity that the
preregistration's hypotheses, thresholds or falsifiers could have been tuned
to. The reads are disclosed so that the blindness record is complete.

OBSERVED. The AC24 count-only extraction (row counts, categorical status
counts and null counts on the same blobs) ran from 09:02Z to 09:04Z, after the
seal.

## 3. Independent Fabric review: NOT RUN (WAITING_CAPACITY)

| Lane | Requested | Placement | Outcome |
| --- | --- | --- | --- |
| `oi1-l3r-r1` | review, C1 | ubuntu1 / grok-4.7 | Admission refused, rc 75, 08:48Z, not started; id burned |
| `oi1-l3r-r2` | review, C1 | ubuntu1 / glm-5.3 (glm-frontier) | Admission refused, rc 75, 08:56Z, not started; id burned |

OBSERVED:
- A read-only router preview for the next review id returned
  `ubuntu1 / glm-5.3` (`judgment_order_glm+burn_down_urgent`).
- Cached ubuntu1 host telemetry at 09:16:32Z read `cpu_tctl_c` 78.0, active
  lanes 1, load1 2.36.
- The temperature is above the admission threshold that refused the earlier
  lanes.

No host was selected to route around that refusal.

Status: the independent review is **WAITING_CAPACITY**.
- No review verdict exists.
- No finding exists, so no repair commit is owed.
- The S0 binding is sealed but not independently reviewed.

INTERPRETED. Every empirical step stays behind gates G0–G6 (§11.3) whatever
the review returns.

Reachable resolution, whichever comes first:
- Request the review once ubuntu1 admission clears, under a fresh id, on a pool
  and model different from the drafting lane (m1/MiniMax-M3).
- Or the seat commissions a native read-only Opus auditor as the fallback for
  the required independent review.

The verdict and its findings are then recorded in a follow-up addendum, with at
most two repair rounds. Each repair is a new versioned file; the sealed V1
files are not edited.
