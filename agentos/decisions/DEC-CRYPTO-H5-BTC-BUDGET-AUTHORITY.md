---
key: CRYPTO-H5-BTC-BUDGET-AUTHORITY
question: >
  Should Crypto H5 continue deriving total crypto exposure directly from
  vector/signals.alloc_optimal, or consume the canonical P0A Bitcoin DecisionState?
answer: >
  H5 must consume the canonical decision-bearing final BTC exposure as its total
  crypto budget. The class overlay may only split that budget across BTC, ETH and
  altcoins, with cash as the residual. If the canonical decision is unavailable
  or fails integrity, H5 must fail closed rather than recompute or fall back to
  raw signal state.
rationale: >
  P0A created btc.decision/v1 specifically to make final exposure and user action
  singular, provenance-visible and integrity checked. H5 currently rereads
  signals.alloc_optimal and therefore bypasses those checks while its own UI says
  Bitcoin Vector sets total crypto exposure. That can leave H5 actionable when the
  canonical decision surface is correctly unavailable. Reusing the existing
  decision projection preserves one sizing authority. The existing class overlay
  remains a deterministic split/context layer and gains no authority to size total
  crypto exposure.
alternatives:
  - option: >
      Keep H5 reading signals.alloc_optimal directly because it is the same
      economic source column used by btc.decision/v1.
    why_not: >
      Same source value is not the same authority boundary. The direct read bypasses
      btc.decision/v1 integrity and fail-closed semantics, so two decision-bearing
      consumers can disagree on whether the state is eligible to act on.
  - option: >
      Create a new crypto-wide allocation or sizing model for H5.
    why_not: >
      That would expand P0B into new signal authority, duplicate the existing BTC
      budget owner and violate the program's no-premature-signal-authority boundary.
evidence:
  - >
    PR #6294 merged as f039c86ae037cf75238cfdd1f3d732d9b643dbb7 after the
    exact reconciliation head e573a341e406532748a9ba62e69e8c5444341630 passed
    CI, fence and authority workflows.
  - >
    engine/btc_decision.py at main ce4a33aeeed779530942560c5b05f4df8ab0306c
    defines btc.decision/v1 as the sole final exposure projection and fails closed
    on integrity errors.
  - >
    Historical defect evidence: scripts/build_crypto.py at main
    ce4a33aeeed779530942560c5b05f4df8ab0306c derived H5 total exposure directly
    from latest["alloc_optimal"].
  - >
    Source implementation candidate fc93f8e7eeec8c70b285191aa2374e88f71332c3
    on PR #8050 replaces that bypass with the existing btc.decision/v1 budget
    projection; local Crypto owner tests are 34/34 and Vector owner tests 95/95.
  - >
    site/crypto.html at main ce4a33aeeed779530942560c5b05f4df8ab0306c says
    Bitcoin Vector sets total crypto exposure and the class overlay only splits it.
affects:
  - "WS:CRYPTO-INTELLIGENCE"
  - crypto-intelligence
  - scripts/build_vector.py
  - scripts/build_crypto.py
  - templates/crypto.html.j2
  - tests/test_crypto_wave2.py
confidence: high
reversibility: easy
decided_by: ceo-sol
decided_at: 2026-08-24
---

# Crypto H5 BTC budget authority

P0B closes one authority seam. It does not redesign the crypto cockpit and it does
not introduce a crypto-wide optimizer.

## Frozen boundary

The total risk budget shown in H5 is a projection of the already-governed final BTC
DecisionState. H5 may deterministically split an available final exposure among BTC,
ETH and altcoins using the existing class overlay, and cash remains the residual to
100%. The overlay cannot originate, raise, lower, rescue or otherwise replace the
total budget.

An unavailable `btc.decision/v1` state is an unavailable H5 budget. No direct
`signals.alloc_optimal` fallback, stale prior value, silent zero, legacy recommendation
or newly invented score may make the shelf look actionable.

## Implementation preference

Prefer extending the existing `crypto.cockpit/v1` display projection with the
already-built P0A DecisionState or the minimum additive fields required for H5 to
consume its status and final exposure. Do not create a second durable DecisionState
file or parallel allocation truth store merely to bridge the two pages.

## What would reverse this decision

Only a separately commissioned architecture decision that changes the program-level
owner of total crypto exposure, with point-in-time replay and forward promotion
proof, may replace Bitcoin DecisionState as H5 budget authority.

## 2026-09-27 implementation checkpoint — canonical budget seam closed in source

This decision is now implemented in source commit `fc93f8e7eeec8c70b285191aa2374e88f71332c3` on Draft PR #8050.

Current protected Mastermind law for the modifying continuation is `c01d890f6536539496f2d6744f3143ff49da296d`, INDEX blob `94d1af402598894372858793a5b1931019c5fa77`, Skillpack 1.0.1. The Chairman's live continuation supplied current intent. The older P0B narrative requiring a redundant Personal-Pro Executive request before routine source modification is superseded by this current protected law only for this already-assigned, custody-clear source execution. It does **not** waive collision, effect, CI, release, transport or production-proof gates.

### What changed

- `engine/btc_decision.py` now exposes `project_budget()`, a minimal fail-closed projection of the existing `btc.decision/v1` authority. Integrity-invalid decisions may retain diagnostic final fields inside the full DecisionState, but the projected downstream budget is unavailable and carries no exposure.
- `scripts/build_vector.py` now writes that canonical budget projection into the existing `crypto.cockpit/v1` receipt. Its hero exposure and `authority.sizing_source` now come from `btc.decision/v1.final.exposure_pct`, not a direct raw signal read. H5 is named as a consumer of the existing cockpit contract.
- `scripts/build_crypto.py` no longer derives H5 total exposure from `signals.alloc_optimal`. It builds the canonical DecisionState through the existing `engine.btc_decision` owner, projects the canonical budget, and passes that budget into the pre-existing BTC/ETH/alt class split. The class grid can split an available total budget but cannot originate or rescue it.
- valid 0% remains a real 0% crypto budget with 100% cash; unavailable or integrity-invalid DecisionState yields no BTC/ETH/alt/cash values.
- if canonical budget or class-split inputs are unavailable, `build_crypto` fails explicitly with `Crypto H5 budget unavailable` before rendering `crypto.html`. It does not silently publish 0% or 100% cash.

No new DecisionState file, optimizer, allocation model, alert owner, or durable truth store was created.

### TDD / verification receipts

RED first:
- old `_allocation(signals, market)` rejected the canonical budget argument;
- missing cockpit state defaulted hero exposure to 0%;
- no explicit H5 fail-closed build guard existed.

GREEN on final source bytes:
- focused H5/cockpit cases: **5 passed**;
- full existing Crypto CI owner command (`test_crypto_cockpit_contract.py`, `test_crypto_wave2.py`, `test_crypto_wave3.py`, `test_crypto_house_style.py`): **34 passed, 0 failed**;
- exact existing Vector CI owner command including `test_btc_decision.py` and R2 suites: **95 passed, 0 failed**;
- Python compile and `git diff --check`: PASS.

The first broader Crypto run in the intentionally sparse worktree had four environment-only failures because `site/`, `content/`, and `data/` were not checked out. Those exact dependencies were added without a full checkout; the unchanged suites then passed. Existing temporary Chromium cleanup warnings remain and are not asserted resolved.

### Remaining P0B acceptance boundary

Open PR #7645 still owns `templates/crypto.html.j2` / `site/crypto.html`. This source carrier deliberately did **not** touch those paths. The current H5 template cannot truthfully render the new unavailable allocation object because it assumes numeric percentages. Therefore P0B is **BUILT_NOT_PROVEN**, not complete.

Exact next integration action after #7645 is reconciled: add one explicit H5 unavailable state to the accepted Crypto template, consuming `allocation.available` / canonical decision metadata without changing the class split or total-budget authority; then prove valid 0%, integrity-invalid/unavailable, and happy-path allocations on the real generated route in EN/ZH and both themes. Only after exact-head CI/fences and real H5 browser proof may P0B be accepted.


## Exact-receipt refinement — supersedes fc93 as current P0B source head

Commit `26fd88c7dad5448f69e6096037cf099d96d0c01e` supersedes `fc93f8e7eeec8c70b285191aa2374e88f71332c3` as the current P0B source candidate. The earlier commit established the correct owner and fail-closed split; this refinement removes the final recomputation seam.

The production pipeline already guarantees Vector before Crypto in daily/render/engine-render. Therefore `build_crypto` now consumes the exact `crypto.cockpit/v1.decision` receipt emitted by the preceding Vector build. It no longer imports or invokes `btc_decision.build_decision`. The class split also requires `decision.as_of` to equal the Vector signals date; a stale otherwise-valid receipt returns `CANONICAL_DECISION_AS_OF_MISMATCH` and the build fails closed.

Test fixtures that directly build Crypto now stage a minimal valid cockpit DecisionState receipt, matching the real pipeline dependency rather than relying on hidden recomputation.

Fresh current-source verification:
- focused exact-receipt cases: **3 passed**;
- full Crypto CI-owner pack: **36 passed, 0 failed**;
- Python compile and diff checks: PASS.

This is still BUILT_NOT_PROVEN because #7645 owns the H5 template and the real unavailable-state rendering/browser proof remains pending.


### 2026-09-27 Extra High verification refinement

Current protected Mastermind law for this continuation is `90402d76494707ca4d385076a007b2de78d23a20`; INDEX blob `94d1af402598894372858793a5b1931019c5fa77`, Skillpack 1.0.1 / bootstrap major 1. The Chairman's live `Continue` instruction supplies present intent for the already-assigned Crypto production-readiness mission. Current law supersedes the older redundant Executive-request prerequisite for routine, custody-clear source work; it does not waive source collision, CI, effect or release gates.

The current P0B source candidate remains `26fd88c7dad5448f69e6096037cf099d96d0c01e`. Additional adversarial coverage added on top of that candidate proves:

- the class overlay cannot raise or lower the canonical total budget: for canonical 0/17/40/73/100% exposures, BTC+ETH+alts equals exactly the canonical exposure and cash is the residual;
- a named override may legitimately make raw model exposure differ from final exposure, and H5 consumes the final canonical 40% rather than the raw 80%;
- a canonical decision with a stale `as_of` is rejected with `CANONICAL_DECISION_AS_OF_MISMATCH`;
- `project_budget()` preserves a valid 0% target, suppresses diagnostic final exposure when DecisionState integrity fails, and rejects missing/noncanonical decision objects.

Fresh combined local regression receipt after de-duplicating tests already present in `26fd88c7`: **147 passed, 0 failed** across the exact Vector authority/R2 pack plus every `tests/test_crypto_*.py` suite. Existing Pandas deprecation and temporary Chromium cleanup warnings remain and are not asserted resolved. Standalone `test_crypto_build_is_lightweight_and_live_wired` also passed independently.

Bypass census on current bytes:
- `scripts/build_crypto.py` contains zero `alloc_optimal` references;
- `crypto.cockpit/v1.authority.sizing_source` is `btc.decision/v1.final.exposure_pct`;
- `build_crypto` consumes `e0["decision"]` and does not import/call `btc_decision.build_decision`;
- `build_vector` names `crypto.html:H5` as a cockpit consumer.

Open PR #7645 remains open at `74298e32bbbbc7f00884ece259455b9bbe46fd6f` and still owns `templates/crypto.html.j2` / `site/crypto.html`. This carrier does not edit those paths. P0B therefore remains `BUILT_NOT_PROVEN`: source authority is closed locally, but live H5 unavailable-state presentation and browser proof remain blocked on template custody reconciliation.
