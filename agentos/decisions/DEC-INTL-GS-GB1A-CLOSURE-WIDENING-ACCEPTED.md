---
key: INTL-GS-GB1A-CLOSURE-WIDENING-ACCEPTED
question: >
  The gb1a lane (intl-gs-w2b-gb1a-r1) committed a six-line, paths-only widening of the
  international-workspace-browser job closure in .github/ci/legacy-jobs.yml (+engine/intl_global_graph_boundary.py,
  +engine/intl_transmission_evidence.py, +config/intl_transmission_channels_v1.json) although its packet fenced
  that file NEVER, and the independent review INTL-GS-W2B-GB1 raised it as F1 BLOCKING. Accept the widening or
  strip it before merging #10354?
answer: >
  ACCEPTED. The NEVER fence in the gb1a packet guarded pack budgets and job structure, not the job's paths
  closure. The widening is paths-only, checker-prescribed (the dossier now imports the graph-boundary engine and
  the transmission-evidence module and reads the channels config, so the closure checker requires the three
  paths), and dropping the commit reds contract-delta. Review F1 is therefore resolved by ruling, not by repair;
  F2 (display-registry tokens) accepted; F3 pre-existing; F4 (chip rendered as its own row) tolerated and moved to
  the deferred ledger as F12, closed by pin1 #10355; F5 cosmetic. Verdict line: SEAT_ACCEPT at
  ecbd01fb8cfb36b4972fca4b1b183249a0759d50.
rationale: >
  A lane fence exists to stop a worker from changing a budget or a job it was not commissioned to change. A
  closure-path addition that the repository's own checker prescribes for the modules the lane was commissioned
  to add is the opposite case: refusing it would leave main with a dossier that imports modules its CI job
  closure does not cover, and contract-delta would go red. Stripping the hunk and re-minting the lane would burn
  another lane id to reproduce the same six lines.
alternatives:
  - option: Strip commit 6b97b94a (or the legacy-jobs.yml hunk) and merge the rest.
    why_not: >
      contract-delta reds on the missing closure paths; the dossier's new imports are real dependencies, so the
      checker's prescription is correct.
  - option: Re-mint the lane with a packet that permits the closure paths.
    why_not: Produces the same six lines, burns a run id, and delays a merge already reviewed at every other standard.
  - option: Accept the paths-only widening by seat ruling and record it (chosen).
    why_not: n/a — chosen.
evidence:
  - "#10354 feat(intl-gs): W2B dossier graph-boundary label (gb1) — head ecbd01fb8cfb36b4972fca4b1b183249a0759d50 → main aba326f385ea19672e1a87f47e97c25e01c3b6d1, 2026-11-01T01:03:18Z (gh api graphql pullRequest(number:10354) → MERGED, read 2026-11-01)"
  - "Review record INTL-GS-W2B-GB1 (lane intl-gs-w2b-gb1-review-r1): FAIL on F1 fenced-file class, F2–F5 as listed; seat adjudication appended, ending INTL-GS-W2B-GB1-REVIEW: SEAT_ACCEPT ecbd01fb8cfb36b4972fca4b1b183249a0759d50 (seat kit; seat-attested)"
  - "gb1a commits f96e8456 (chip/footnote/builder + tests T1–T7) and 6b97b94a (closure widening) on the lane branch; gb1b ecbd01fb (pins, defaults walk, recapture, browser assertion) — short shas seat-attested"
  - "Lane packet fence text (seat kit intl_gs_w2b_gb1a_body.txt): .github/** NEVER — guarding pack budgets (seat-attested)"
affects:
  - "WS:INTL-GLOBAL-SURVEILLANCE"
  - ".github/ci/legacy-jobs.yml (international-workspace-browser paths closure: +3 paths)"
  - "templates/intl_workspace/dossier.html.j2 and lib dossier builder (imports the covered modules)"
  - "deferred F12 → closed by pin1 #10355 (chip in the Typed-edges head row)"
confidence: high
reversibility: easy
decided_by: fable-meta-ceo-seat-d7c4f490
decided_at: 2026-10-31
review_by: 2026-11-30
---

## Scope

Binds the adjudication of review finding F1 on #10354 only: a paths-only closure widening prescribed by the
closure checker for modules the lane was commissioned to add is inside the lane's effective scope even when the
packet fenced the file for budget purposes. It does not loosen the fence for budgets, job structure or any other
file, and it grants no lane a general right to edit .github/**.

## Options considered

Strip the hunk (rejected — reds contract-delta); re-mint the lane with a widened packet (rejected — same lines,
burns an id); accept by ruling and record (ruled).

## Consequences

- #10354 merged at ecbd01fb with the three closure paths; contract-delta 0 / 0 at the merge.
- F4 (chip as its own row) became deferred F12 and was closed the same night by pin1 #10355
  (→ 4e1ae041040e638028f9b189fe6dfe932f4eb5b1).
- Future packets name the distinction explicitly: budgets and job structure NEVER; checker-prescribed paths
  closure for the lane's own new modules allowed and disclosed in the PR body.

## Provenance

Seat ruling of 2026-10-31 (Fable Meta-CEO seat d7c4f490), applied before the #10354 merge, recorded in this
records PR (r8) and in the continuation handoff checkpoint "2026-11-01 01:0x–02:3xZ — gb1 + pin1 MERGED".

Date precision (records r9, review INTL-GS-REC8 F-3): the ruling was made in the seat's 2026-10-31 local session
and applied before the #10354 merge at 2026-11-01T01:03:18Z; the exact UTC minute is not recorded, so the UTC
calendar date may be 2026-11-01. `decided_at` is kept as attested.
