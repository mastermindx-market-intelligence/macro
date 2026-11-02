# Terminal options matrix recovery

## Mission and source custody

The Chairman's same-chat continuation retains the original end-to-end job:
a useful options heatmap beside the main Terminal chart, backed by truthful
published data. This repair maintains the existing matrix producer; it does
not introduce another data, publication, lifecycle or trade-authority plane.

Mastermind procedure pin: `4c1b3d389286df2a4b5b98a4d4491f2c8a1263f2`.
Macro base: `1177cf84ffa46fa3e049ebe785aa1b391e42102d`.
Macro PR: #7861, branch `claude/options-matrix-session-repair-20260924`.
Terminal PR: #723, branch `claude/terminal-options-heatmap-20260923`.
Terminal UI/evidence head: `83f14a56bbf6657916df2f9bc93498bacd94d833`.
Producer implementation: `268d53cae74de5f6e5f165e4c85ec784e7017ab7`.
Direct principal work was a bounded source-timing/debugging intervention.
No independent worker, delegated execution or automatic continuation is claimed.

## Observed cause and repair

The existing M1 job chose the latest OI publication date, Sep-23, although
EOD and Greeks reached Sep-22. It uploaded ten empty matrices with an exit0.
Automatic selection now joins a root's OI/EOD/underlying-price sessions, newest
first, within the last64 EOD sessions. Explicit dates remain exact. This keeps
the current OI publication-date interpretation and never splices newer OI
into an older price snapshot. The separate option-premium-as-spot fallback
is removed: only a finite positive underlying reference can price the book.
See `DSC:OPTIONS-MATRIX-OI-DATE-CAN-OUTRUN-PRICE-SESSION`.

## Verification and limits

`python -m pytest tests/test_options_matrix.py tests/test_options_structure.py -q`
passed117 cases after adding discriminating all-healthy upload success/failure
cases. Existing missing-input and partial-publication tests also pass. Six
pytest warnings concern old temporary-directory cleanup, not failed assertions.

The real-source evaluation at2026-09-24T01:07:51Z returned755 MU cells, spot1096.16,
and session2026-09-22; the incumbent automatic path returned zero. Every cell
matches the incumbent explicit Sep-22 calculation. Its compact receipt is
`research/evidence/options-matrix-session-repair-20260924/mu-source-qualification.json`.
The installed source hash was unchanged; no production file or R2 object was
modified. The full evaluation digest is
`e9dd190c633a7633a020f9a7569d4972dd6eb6cacad7f71ba50cbfc900c79ed4`.

A Chromium check on the existing Terminal route consumed this real matrix
through an explicitly intercepted local API at2026-09-24T01:14:15Z. It rendered
84 visible cells, selected MU1100/Sep-25, displayed41.753106 million from
41,753,106 source dollars, showed5917 OI contracts, and pinned1100 natively.
The original chart canvas survived selection and closing; no page errors or
horizontal overflow occurred. This proves real-input LOCAL integration,
not authenticated published-API or live-release acceptance. Browser receipt
and screenshot remain in the existing Studio evidence directory; copying them
into the repository was refused by the tool and is not claimed completed.
Screenshot digest: `681e31ab53f92e213768b6037e8e1933ca6be8bd92adf175d9f13cbe37e6d376`.

MU/ARM join the existing default publisher. INTC's observed store stopped
Aug-21; this repair neither refreshes its vendor data nor calls it current.

## Publication and rollback boundary

The existing publisher finishes healthy roots but exits nonzero for source or
upload failures. A null result never replaces an existing dated valid local or
remote matrix. Missing required publish credentials fail before publication.
No historical artifact is relabeled fresh. The existing GEX and legacy VEX
formulas, authority_tier=display, and downstream sign/unit conventions are unchanged.

Deployment is still owed. Require concluded accepted-source checks, merge on
normal repository policy, an inactive `com.macro.optionsmatrix` job, exact
installed preimage verification, and rollback copies before changing either
`engine/options_matrix.py` or `scripts/build_options_matrix.py` on M1.
Never reset the dirty `flow-ops-wt`, create another publisher, change raw stores,
revive its retired GEX-state mirror, or bypass a denied deployment operation.
Use the existing runner and environment owner without exposing credentials.
Verify published MU/root/session/cell identities after the normal writer runs,
then verify the authenticated Terminal data path and git-gated UI release.

## Current cumulative continuation

MISSION_COMPLETE: false. State: built and locally source-qualified, not released.
The original Paper design, existing sidebar implementation, verified mobile
fold/Escape fixes, and exact local fixture qualifications are DO_NOT_REDO.
The current repair's source-date join and real MU evaluation are also not a
request to rebuild the options system. Next: consume Macro#7861 integrated
checks, repair only attributable failures, finish source acceptance and normal
merged-source deployment, then close the published-data-to-Terminal proof gap.
Terminal#723 stays separately gated; its copied-transcript CI defect was fixed
without weakening the existing security invariant. No background worker/wake is armed.

### Current shared-CI blocker attribution

Macro run35941605327 tested mergea5b08d2d against base2b2cae6a. Contract-delta
job107450466878 and failed packs1/3/6/9/11 all refuse execution because
`options-payoff-lab-consumer` does not declare the path of its own command's
`tests/test_options_skew_source_note.py`. This is not a matrix-test assertion.
The candidate does not change that manifest. Existing main-red-repair#7802
owns the shared recovery; precise evidence was delivered in comment5805741885.
Delivery is not proof that an owner started or completed the repair.
No competing manifest, queue, runner, job wrapper or CI authority change exists.

Material-source comparison1177cf84→2b2cae6a found no change to AGENTS/CLAUDE,
the matrix producer/validator, ThetaData reader, Greeks helper, publisher,
matrix tests or runner. Current integration still has its own CI gate.
Agent OS validation after this discovery:1228 records,0errors,89 existing warnings.

### Index-root performance finding

The original three-evaluation SPY proof hit its180-second read-only ceiling;
it is not counted as a successful SPY qualification. A bounded source-host
profile then stopped after25 actual IV lookups:5,056 Greek rows,0.465seconds
in those lookups,26.089seconds total including source loading. Installed code
was unchanged. Each scalar lookup re-normalized and scanned the entire frame.

The candidate now indexes exact contract IV once per loaded root/session and
uses the same first-nonmissing value, right/expiry/strike identity and delayed
numeric conversion. This is a local index over the existing frame, not a new
cache owner. No GEX/VEX formula or source-date choice changes. Discriminating
tests pin duplicate/null/zero/malformed-unused IV behavior, one index per real
builder call, and200 date conversions rather than200×200 for200 queries.
Focused matrix/structure regression now passes120 tests. Fresh real-source
qualification is required for this changed implementation before acceptance;
the earlier MU/ARM receipts remain evidence of their exact earlier candidate.

## Recovered source and candidate-owned CI closure — 2026-09-24

The clean local IV-index commit `66af476d73af8631b94cc634aecdefc1b79b4a2e`
was verified to have remote `0841c721519b485a534b963f0406d71025a39e3f`
as its sole parent, then published unchanged to the existing PR branch by a
normal fast-forward push. ARM/SPY receipts above were consumed, not regenerated.

Merged shared repair #7864 is present in tested base
`4597dd8e72a64aa86d1e07ae1a76924ce9a7b5ae`. The fresh integrated run
35964965570 tested merge `c72ec63f0b498a573ffe3398c687997512264147`.
Its contract-delta job 107521411893 exposed a DIFFERENT, candidate-introduced
edge: publisher tests in `tests/test_options_matrix.py` now reach
`scripts/build_options_matrix.py`, absent from `flow-surface`'s exclusive paths.
Add that exact path to the existing job; no command, runner, gate, dependency
installation, formula, test assertion or source-publication behavior changes.

Native `run_ci_pack` inference checked 744 concrete closure paths: before the
addition the publisher was the only uncovered path; afterward none were missing.
Native selection includes this existing job for a publisher-only change, and
semantic step specifications are identical. The owner definition was identical
at the feature head and tested base. This scoped qualification is NOT a concluded
whole-manifest/integrated CI pass. Transcript SHA256:
`b746d903bae8176a2ccb300cd7065c6b4660d9c68e59261062b6af7da4a2ca72`
(`matrix-ci-scope-66af476d-qualification.log` in the existing Studio evidence directory).

The production installation and authenticated published-data-to-Terminal journey
remain unproven. Both PRs stay draft/unmerged pending source and release gates.
