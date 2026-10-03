# Forex Carry & Funding R19 — existing-owner integration

Status: **SOURCE CANDIDATE — NOT MERGED, NOT DEPLOYED, BROWSER ACCEPTANCE OUTSTANDING.**

Parent mission: Macro #8147 / `bonds-forex-research-design-20260928-sol-c1-001`.

Stacked source base: Forex PR #8243 exact reviewed head
`cf6afd62e8a22fb25a9fdea14c9ae0fe70908bd6`.

Branch/worktree owner:
`claude/forex-carry-funding-r19-20261003-sol-c1` in the existing registered
`.claude/worktrees/pr-8243` carrier. The base PR source is not modified by this
stacked slice.

## Product job

Expose the evidence needed to judge **carry fragility** without inventing a new
carry engine, funding score, forecast, trade instruction, or scenario setter.

The existing Forex page gains a read-only **Carry & funding evidence** disclosure
after Movement evidence and before The pairs. It preserves five distinct questions:

1. **Rate edge & positioning** — existing pair carry, carry/vol, 10y differential
   and CFTC positioning, with their units kept separate.
2. **Canonical scenario confirmation** — the existing
   `engine.forex_regime` carry-unwind state and emitted legs; R19 never
   recomputes activation.
3. **Historical receipt** — past conditional frequency/base rate/Wilson interval
   and effective sample only when the existing sample gate is valid.
4. **Funding plumbing** — OFR total/funding, SOFR−IORB, A2/P2, and CP−bill as
   contextual proxies.
5. **Missing direct evidence** — direct market-wide USD cross-currency basis
   remains explicitly unavailable. Proxy calm never becomes “basis normal.”

Paper references remain the governing visual/product grammar:
`5IGG-1` desktop funding evidence, `5IRE-1` tablet, and `5IXJ-1` mobile
missing-basis state in file `01M2WGNCX9475G79JRKJTCM08P`. These are design
references, not browser acceptance.

## Existing owners reused

| Evidence | Existing owner consumed | R19 handling |
| --- | --- | --- |
| Carry / carry-vol / 10y differential / COT | existing `pair_vm` output | additive display projection only |
| Carry-unwind state, intensity, fired legs, historical receipt | `engine.forex_regime.fx_stress_regime` | validates internal receipt consistency; never recomputes market state |
| OFR FSI + Funding component | existing `lib.store` series | latest actually stored point, no forward-fill |
| SOFR−IORB corridor | published `data/intl_risk/latest.json#two_tier` | **percentage points → basis points** for display; artifact build time kept distinct from source freshness |
| A2/P2 + CP−bill | published `data/regime/latest.json#conditions.systemic_stress` | artifact as-of is context only, never vendor observation time |
| Direct USD x-ccy basis | no admitted current owner | remains unavailable |

R19 originally re-called `contagion.two_tier_read()` from the Forex builder.
Audit rejected that duplicate computation. The candidate now reads the already
published `intl_risk/latest.json` display artifact, consistent with other
repository consumers.

A unit defect was caught during that audit: the canonical SOFR−IORB leg stores
`-0.02` **percentage point**, which is **-2 basis points**. Tests were changed
RED first; the projector now performs that explicit conversion.

## Semantics and fail-closed rules

- Non-boolean scenario activity is Unknown.
- Canonical `active`, `n_fired`, `min_legs`, and emitted leg flags must be
  internally consistent; contradictions withhold the scenario state.
- Duplicate pair identity quarantines the pair rather than selecting one copy.
- Boolean/non-finite/malformed numeric evidence is invalid, not zero.
- Historical receipt is withheld unless probabilities are bounded, Wilson
  geometry contains the conditional frequency, and `n_eff <= n_raw`.
- `status=insufficient` never headlines a percentage.
- OFR total and OFR Funding are one related source family, not independent votes.
- Artifact build/as-of dates are not vendor observation/release timestamps.
- Missing direct x-ccy basis never becomes zero, estimated, or “normal.”
- No component input, JavaScript, storage, watch, alert, position, trade, or
  market-state mutation is introduced.

## Source boundary

- `lib/forex_carry_funding_view.py` — pure validation/projection.
- `scripts/build_forex.py` — reads existing published artifacts and exports one
  projection to both the page context and `data/forex/latest.json`.
- `templates/_forex_carry_funding.html.j2` — read-only bilingual responsive view.
- `templates/forex.html.j2` — one include.
- `tests/test_forex_carry_funding_view.py` — model, source-owner, page/JSON,
  template and page-writer coverage.
- `.github/ci/legacy-jobs.yml` — extends the existing `data-base-shim` code job;
  no new CI job/plane. Explicit paths include non-imported artifact producers
  `scripts/build_intl.py`, `engine/contagion.py`, and `engine/conditions.py`.

No engine/data source/global theme/shared navigation/generated `site/` file is
owned by this slice.

## Verification boundary

Targeted TDD includes deliberate RED states for:
- old recomputation-oriented funding collector;
- missing A2/P2 and CP−bill rows;
- redundant contagion call;
- fired-leg/`n_fired` inconsistency;
- impossible historical confidence/sample geometry.

The sparse checkout’s free-content shim tests require nine committed site link
targets. Final owner-suite verification restores exactly those HEAD blobs into a
temporary directory and redirects only `build_free_content._LIVE_SITE_DIR`
inside the pytest process; no production site/source is changed.

The final exact test/contract receipts belong in the parent #8147 checkpoint and
PR description. This document intentionally does **not** claim real-browser,
keyboard/focus, screen-reader, visual-regression, live-data freshness, merge, or
deployment acceptance.

## Release gates

Keep Draft/HOLD until:
- exact-head hosted CI and independent source review return;
- the existing browser evidence lane is legitimately available;
- real desktop/tablet/mobile × EN/ZH × dark/light review verifies disclosure
  opening, evidence states, contrast/overflow, keyboard/focus, reduced motion,
  and missing/stale handling;
- the existing admitted render/publication owner builds and serves the changed
  Forex page.

The historical browser administrator denial remains frozen. Do not fabricate an
`EVIDENCE.yml` or use another host/profile/browser to bypass it.

Rollback is ordinary removal of the include/export/projector and CI path
extension. There is no persisted user state, schema migration, market state, or
financial engine to roll back.
