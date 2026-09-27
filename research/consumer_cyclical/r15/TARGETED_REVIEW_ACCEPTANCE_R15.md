# Consumer Cyclical R15 — targeted independent review acceptance

**Reviewed Consumer head:** `1183127d24cb9d3654516323f4e4ba530aa15cd1`  
**Frozen packet:** `/tmp/cc-r14-targeted-review-1183127` on the authorized m2studio review surface  
**Packet manifest digest:** `6146906128d5cb09c543b8d954abb4c95205cbe27fc11902eabfb217e809b6fa`  
**Review route:** Claude Code, requested Opus/high, restricted read-only `Read,Grep,Glob`, no Bash/network/edit/write, no session persistence.  
**Provider result:** success / terminal completed / no permission denials. Primary model usage reports `claude-opus-5`; a tiny CLI auxiliary Haiku usage is also present in the provider receipt. Provider session: `e07aaee8-2315-4475-99f6-1af495c9fcc2`.  
**Verdict:** `ACCEPT_FOR_FABLE_HANDOFF`  
**Blocking findings:** 0.

The reviewer independently adjudicated H1–H3, M1–M9 and the R14 current-owner refresh. It did not grant native, source-admission, browser, deployment, merge or production acceptance. The review process was deliberately read-only; Sol separately replayed the saved R12 and R13 research verifiers from the immutable branch package and observed R12 **60 passed / 0 failed** and R13 **9 passed / 0 failed**, each with zero native/browser/production claims.

## Accepted findings

- **H1:** R12 exactly supersedes the proposed new-dossier Earnings delivery with the common POST `/api/themes/v1/research/query` + `/api/themes/v1/research/evidence` family and removes R7 Task4's duplicate implementation ownership. Existing Earnings owners remain intact.
- **H2:** one design contract is selected: `consumer_cyclical` / version 1 / `consumer_economic_change.v1` / company subject. It remains `PENDING_SHARED_OWNER_ACCEPTANCE`; no Semiconductor relabel/fallback is allowed.
- **H3:** ready derived numeric results carry value text, unit, power-of-ten scale, sign, periods/clocks, precision/display quantum and exact input keys. Explanations render the scale rather than silently treating thousands as dollars.
- **M1–M5:** interpretation guard, dependency-local degradation, period grain, timezone-aware event order and tiny-denominator policy are coherent and discriminating at research-reference level.
- **M6:** 174 obligations reconcile as 148 prior obligations + 10 R7 delivery obligations + 16 R10 foundation obligations. R6's 32 are already included in the 148. Product obligations remain unexecuted.
- **M7:** SEC rights treatment is representation-specific and explicitly excludes whole expressive documents, third-party attachments without their own family, branding and dataset redistribution.
- **M8:** pins are evidence/review pins only; every native write requires a fresh current-owner/source-custody re-pin.
- **M9:** incumbent positive-only entitlement-store-outage grace matches the current code/test contract, while deployed/live behavior remains unproven.
- **R14:** current #7870 truth is carried correctly: T09 exists but is not Consumer-accepted because unmatched source families pass through and current `https://www.sec.gov` witness refs resolve to no family; T08b and T11a are review-rejected/fix-queued; T10e/T10f are queued; #7780's build-out ruling remains open.

## Nonblocking review nits carried into the integration handoff

These do **not** reopen the accepted research package, but the integrator must not lose them:

1. R13's old sentence that T09's fix lane is queued is superseded by R14/current #7870: T09 is integrated **but NOT Consumer-accepted** because the unmatched-family rights seam fails open.
2. The two R13-pinned shared tests are unchanged at current #7870 head `3e3a7956d014b8c50be7b197fdbea847cecfa641`: `tests/test_theme_research_rights_refresh.py` blob `bfc04f38066029e46d23c2e61ac4dd1e5aa9acb0`, `tests/test_theme_research_private_binding.py` blob `a9c09169d3618abb2bb7df1c842fab0c7c0d1054`.
3. “60 checks” is a research regression count, not 60 independent financial guarantees; roughly 49 are substantive behavioral checks and others include literal/meta guards. Never use the count as evidence strength.
4. H2 fail-closed behavior is a design requirement, not executed owner-route proof. Require it in the accepted shared contract.
5. M2 has two deliberate failure levels: malformed values/local dependencies suppress dependent results; malformed case shape/unknown keys may refuse the whole case.
6. The research `range_relation` classification currently inherits a harmless display-quantum sentinel despite `rounding=not_applicable`. Product code should use the owning typed nonnumeric representation rather than copy this sentinel mechanically.
7. Research `input_refs` are local fact keys. Product result lineage must join those keys to exact native document/revision/locator evidence; case-level `source_references` must not be mistaken for per-result lineage.
8. The initial review's six low-severity findings were not numbered/dispositioned one-by-one in R12/R13. They remain nonblocking nits; no document may claim they were independently closed merely because this targeted review accepted the handoff.
9. `consumer_economic_change.v1` may not compose with #7780's still-open proposed mount discriminator grammar `^[a-z_]+_theme_research\.v1$`. The shared owner must rule; the integrator must not rename one side unilaterally.
10. R13 reports a two-test paywall replay without an attached receipt. Current code/test blobs and named tests corroborate the contract, but the implementation/release wave must rerun them rather than treating the historical count as immutable proof.

## Final Sol disposition

The package is accepted for a **principal integration handoff**, not for Ready/merge/deploy or product acceptance. External-owner gates remain external; their existence does not require redesigning the accepted Consumer economics package, and the package must never bypass them.
