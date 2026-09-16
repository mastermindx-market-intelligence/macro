# Commodity release score-parser repair

Operation: `commodities-release-ms-score-parser-20260916-sol-001`. Source writer: Sol, same attended Remote Desktop / gh carrier.
Parent: commodity asset-first safety R1, PR #7198. This is a separate, path-disjoint
release dependency; it does not change R1 semantics or create another workstream.
Procedure: Mastermind 8ba7deedde164c90298d3e88785d98e02fa5e2d2, Skillpack 1.0.1.
Base: `c91daea47c77cfc55bdd41e0417eb05340f6d26a`. Parser blob: `00712a8fa5a7d0e82e70ce65f25207772df52764`.

## Outcome and authority

Restore the existing release validator's ability to read the current dashboard's
visible score with its provenance attribute, while preserving every semantic
coherence rule. Current Chairman direction approves the commodities repair end to
end. Direct execution reason: CRITICAL_PATH_SHORTCUT; this bounded parser defect
blocks publication and does not require another architectural decision.

No numerical policy, score bands, risk overrides, history writes, data licensing,
release permissions, CI configuration, deployment or live capital is changed.
The shared release checker remains the sole coherence owner.

## Root cause

Merged #7184 emits `<span class="v-score" id="ms-score" data-measured-score="61">61</span>`.
The path checker already accepts attributes, but the board checker expected the
closing angle bracket immediately after the id. Thus a coherent page is rejected
as unparseable before any semantic comparison. The committed macro.html at
c37c4e37b20ada935f32516a2a31428d558430c3 reproduces this exact failure.

## Bounded implementation

Modify only `scripts/check_ms_board_coherence.py` plus this evidence note.
Use one attribute-tolerant visible-score regex for board and path checks:
`_SCORE = re.compile(r'id="ms-score"[^>]*>(\d+)<')`; `_SCORE_ANY = _SCORE`.
Retain the visible-score versus measured-score distinction and all rules (a)-(h).
Add score-provenance cases to the existing `--selftest`, not another CI workflow.

## Verification performed

Before correction: all 12 legacy selftests passed despite the real artifact
failing. The initial new cases failed 9/10 for the expected parser mismatch.
After correction: 23/23 built-in selftests pass and the exact committed macro
artifact has zero coherence violations. Eleven deliberate regression variants
are detected: old parser; disabled band, tick, thesis, forced-risk, mixed cap,
generic force, generic cap, flip, and path checks; and measured-score substitution.
These were executed from the actual source in memory against the archived source
closure. They are not independent review, hosted CI, a render or production proof.

Run `python3 scripts/check_ms_board_coherence.py --selftest` on this candidate.
Then run the normal registered guard suite and hosted checks under their owners.
A prior combined read of the existing pytest file was tool-refused; it was not
retried or edited. New discriminating tests are in the existing checker selftest.

## Release sequence and stop boundary

Obtain current-head checks/review, merge through the existing repository process,
and reconcile the existing HK dead-route dependency #7163. Only the normal
publication path plus a successful real page/data read can establish delivery.
No current render was cancelled or duplicated by this operation. R1 stays on
its existing DRAFT/HOLD branch and independent-review request.

Status: BUILT_NOT_PROVEN, not deployed. Do not weaken a release check or treat
this code repair as the full commodities model or product upgrade.
