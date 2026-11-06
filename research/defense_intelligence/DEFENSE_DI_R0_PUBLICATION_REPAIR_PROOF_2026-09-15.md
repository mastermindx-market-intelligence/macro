# Defense DI-R0 — candidate collection publication repair

Operation: `defense-intelligence-r0-publication-20260915-sol-001`.
Parent: `WS:DEFENSE-PROCUREMENT-V3`; projection: MAS-259.
Capability state: BUILT_NOT_PROVEN. Local real-data proof is not production acceptance.

## Scope and authority

The Chairman's live continuation authorizes this bounded publication repair. Sol
retains delivery ownership. Direct execution rationale: CRITICAL_PATH_SHORTCUT;
a narrow diagnosed contract repair is smaller than framing and dispatch overhead.
No worker or Executive Job is claimed. No old SBIR/GAO child is resumed.
Protected Skillpack: Mastermind `7642aea155d2817219135b24246b55c1d7611c66`,
v1.0.1/bootstrap 1; INDEX/COLD_START/ACTIVE_EXECUTION/RECONCILE_STATE/CLOSEOUT
were fetched atomically and matched their already-read content hashes.
Source base: Macro `95d39b2f3f0f9e63db6da3fbb895baeb65f76d63`.
The existing external-SSD storage helper created the isolated linked worktree;
no primary/foreign checkout was changed. Source and regression edits stay on
`claude/ssd-defense-r0-publication-20260915-8463e508e861a455`.

## Root cause and repair

The real source reconstruction produced 264 eligible research candidates from
500 workspace events. Exactly one queue-schema error occurred: `$.candidates`,
`maxItems=250`, observed length 264. The preceding committed projection was
still dated September 1, with 173 active rows and 235 historical ledger lines.
The existing API independently pages candidates at a maximum of 100 per request.
A 250-row cap on the complete collection conflicted with valid producer output.
The repair removes that collection-only limit; it does not truncate candidates,
relax row validation, change identifiers, bypass corrections, or grant trade authority.

The source workspace's 500-event bound, issuer eligibility, request page limit,
per-row proof requirements and generation-bound cursors remain unchanged. This
is not a claim of unlimited production capacity. The browser's four-page bearer
fetch budget is a separate existing limitation; the current 256-row output fits
in three pages. Future growth beyond that budget needs a separately proven
consumer change, not silent truncation or a claim this repair solves all scale.

## Discriminating proof

The new cardinality test first failed at 251/264/500 while 1/250 passed: five
failures and two passes. After the schema change it passed all seven tests,
including invalid evidence/authority after row 250 and 100/100/64 API pagination.
Oversized HTTP requests remain refused (101 -> 422). Test entitlement is an
explicit fixture, not a production signed-in-user proof.

Full local command: `python3 scripts/build_government_revenue.py --root
.pytest-local/r0-live-build --live-materialization`. This used isolated copies
of real committed Government Revenue, USAspending and Stock Identity inputs.
No live collection, production write, or original input replacement occurred.
The complete existing builder exited 0 in 225.54 seconds, not a stubbed builder.
Generation: `2026-09-16T03:39:39.078363+00:00`.
Queue: `grcq1-d8337a51b4280f0a44922fe3`.
264 source candidates -> 256 active candidates after the existing eight reviewed
quarantines. Ledger 235 -> 318, 83 appended observations, old prefix preserved.
Public candidate twin equals canonical bytes. HTML is 303,701 bytes, below the
current 311,296-byte fence. All display-only authority flags remain unchanged.

The real API reader accepted these real artifacts and served all 256 IDs across
100/100/56 pages with the identical content ID; the 101-item request returned
422. Both suppression-required and correction-required flags stayed true.
Only the local HTTP entitlement was a fixture; production authentication was
neither altered nor claimed tested.

The wider pre-publication test run exposed the expected stale-ledger accounting
failure. It was interrupted to diagnose it: 10 passed, one failed; this is not a
complete suite pass. Replaying that unchanged historical guard on the SAME frozen
real input failed against the old committed ledger and passed against the rebuilt
ledger. No guard, source identity, manifest, graph clock or reviewed quarantine
was changed to green it. Seven live-vintage accounting tests are separately
excluded from the focused regression run; its actual outcome must be recorded
as a later receipt rather than inferred from progress dots.

## Investor significance and limits

These are 83 previously unpublished research observations, not 83 new awards,
new trade signals, or newly discovered investment profits. All four first-cohort
issuers remain reviewed in the existing identity graph. The rebuilt queue holds
six RTX, 22 NOC, eight LHX and zero LMT active observations for this bounded
source snapshot; zero is not evidence of no LMT procurement. None of these rows
has an issuer-attributed financial denominator. That missing economic bridge,
not oil correlation or a larger contract count, remains the next intelligence
capability after publication is recovered. No ranking/entry/size flags changed.

## Later regression receipt

The focused 154-test run concluded: 153 passed, one failed, seven live-vintage
checks deselected. The remaining failure was an existing test-manifest gap:
`fms_cases`, `program_ontology`, and `program_dossier` were not classified in the
Prophet import-boundary test. They build/admit/compose evidence, not decorate
already-selected Prophet plans, so all three are now on the forbidden source
side. Three injected-edge tests first failed to detect them and now prove they
cannot enter the annotation seam. No production module or permission changed.

The seven cardinality cases were moved into the existing CI-listed
`tests/test_government_revenue_candidates.py`; no unregistered test-only file or
new CI control path remains. The final run of the complete Prophet-annotation
suite plus those seven cases passed: 66 passed, one dependency deprecation
warning, 7.75 seconds. This does not turn the earlier interrupted run or the
seven deselected live-vintage checks into a claimed full-suite pass.

Repair PR: #7186. The initial source revision was
`9bf062655e659eb4f1656caca503622e4db4c3cc`; read the PR head for the later test
classification revision. Keep it draft until applicable exact-head CI and
review permit release. Production remains unproven; never manually replace its
ledger with this local proof output or treat a skipped publisher as success.
