# X writer fact evidence handoff — 2026-11-14

## Incident and scope

The prior historical ledger audit identified 423 approval-desk quarantines
beginning `approval-desk: number_sanity: decisive posture` and a recent
39-item content plan with 38 numeric drafts but no retained `facts`,
`source_facts`, or `numbers_whitelist` on the saved rows. That is an evidence
loss problem; **those historical refusals remain valid**. Do not replay or
retroactively auto-approve the old queue.

The producer `content_studio.content_plan` calls `copywriter.build_context`
with deterministic `chart_facts`, `market_facts`, mover/theme or filing facts.
The writer sees the rounded `numbers_whitelist`, but that context previously
vanished. `outbox.emit_from_content_plan` stamped mostly chart and plan IDs,
while `approval_desk.item_evidence` could not use evidence it never received.

## Contract repair

1. Immediately after the writer context is built, capture the **input** facts
   and the exact pre-generation numeric license into the private
   `_writer_fact_packet` queue field. It is sourced only from deterministic
   producer context, **never** by extracting numbers from model-generated copy.
2. The canonical outbox emission validates producer marker, generation day,
   1–48 source facts, 1–128 number tokens, finite bounded field shapes and a
   16 KiB byte ceiling. A missing, malformed, wrong-day or oversized packet
   is omitted. `strip_scaffolding` keeps the private intermediate out of
   `content_plan.json` so the artifact does not grow with private context.
3. The outbox stores accepted input at `source.fact_packet`, using the same
   writer license for the existing value gate. Graded receipt stop and target
   values are stamped as typed levels rather than generic facts.
4. The approval desk accepts only same-day, bounded planned packets; otherwise
   original legacy behavior remains. With a valid planned packet it cross-checks
   numeric copy against the original writer license. Unsupported numbers remain
   `UNVERIFIABLE` (quarantined under decisive posture), not approvable.
   Source facts alone do not license a future target without a typed plan/receipt
   level. The thousands-count parser preserves `221,000` as one claim instead
   of mistaking it for the separate numbers `221` and `000`.

The packet is **generation-time provenance**, not independent proof of source
freshness or correctness. Existing liveness, market, language, target,
publication, and human controls stay authoritative. No old outbox item is
modified; no X or Buffer effect is invoked.

## Verification

- Ten isolated real-path tests (temporary outbox JSONL and approval evaluation):
  correct macro fact is emitted and receives full approval; unsupported
  percent/count remains quarantined; unrelated fact cannot be promoted into a
  forward target; stale/malformed/oversized packets fail closed; degenerate
  counts removed before writing stay removed; receipt typed levels survive;
  private scaffold is not saved to the content plan.
- `python3 -m compileall` on changed Python modules and tests; `git diff --check`.
- The local runtime has no `pytest` module; the ten zero-argument/`tmp_path`
  tests were executed directly against the same functions using fresh
  `tempfile.TemporaryDirectory` roots. Hosted binding CI is still required.

## Remaining limits and next work

- Full daily live generation from current first-party market data was not
  exercised here; the available local snapshot lacks the regime/daily-brief
  artifacts, and signed-in admin browser automation is blocked by an extension
  overlay. Fresh deployed evidence and a source-to-X/Buffer acceptance sample
  remain required.
- The legacy copywriter numeric pattern intentionally allows bare 1–2 digit
  integers outside price slots. The approval bridge inherits that exception.
  A later calibrated count-claim gate should target economic release counts
  and changes without punishing ordinary narrative `3-day` phrasing.
- Source `as_of` here is the writer plan day, not each market publication's
  timestamp. Long-lived source freshness, corrections and rights remain their
  producer owners' jobs.
- The held editorial/compiler PR #7493 changes earlier Content Studio mover
  generation hunks, not this writer handoff hunk. Preserve its
  `merge-blocked`/`CHANGES_REQUESTED` hold; apply normal exact-head integration
  and CI, never manually clear the hold for this evidence repair.

Related active source lanes: #11243 (Hot Tape voice/value gate), #11245
(press replay), #11235 (watchlist line rendering), #11196 (editorial floor).
