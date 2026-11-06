# ROR-1 — October 16 source publication rollback after successful Git rebase

**Research only.** Original risk/renderer/CI writer custody stays with #9428, original render/publication owner and ROR-1 #1478. No source publisher, site data, browser, scheduler or trade model changed.

## Exact reproducible immutable Git source proof

Macro closing-bell commit `c4db59f204ec43fa5da9fb9feb3e8e2bbf817aa1` committed **October 17, 2026 00:09:46Z**, source session Oct 16. Its direct-descendant render commit `ee7e7d9196e18b416caf1706c6df48343de82f0f` committed **00:40:35Z**, 30m49s later. GitHub compare confirms `status=ahead`, `ahead_by=4`, `merge_base=c4db59f2...`: **same accepted main ancestry**, not two incomparable branches.

| Artifact | Closing-bell `c4db59f2` blob / source session | Descendant render `ee7e7d91` blob / source session |
|---|---|---|
| `data/market_state/latest.json` | `af900d96005460e16e91103da55e2df78fccbd6f`, **Oct16 / 40 RISK_OFF** | same Git blob, **Oct16 / 40 RISK_OFF** |
| `site/riskdata/risk_envelope.json` | `a72825290b31557cdc669fc258bc3b492575c7d3`, **Oct16**, produced `2026-10-16T23:03:28Z`, bundle `2025aa98261ad22b` | `fd525185adcfc80bd2576d41cc792a0cc4cff979`, **Oct15**, produced `2026-10-16T23:28:09Z`, bundle `5b666e6b83420c2e` |
| `site/rr_banner.json` | `3545f17b26aa439a5c94f8e551d0cae6c74e80be`, **Oct16**, generated `2026-10-16T22:56:20Z`, legacy `alert:null` | `2f531c1422e0874461a3ccecaf103731040d23d1`, **Oct15**, generated `2026-10-16T23:25:48Z`, legacy `alert:null` |
| `data/risk_envelope/latest.json` | `4e5dc3bf106761017282c01cd319042d3de3b0e0`, **Oct15**, DEGRADED | same blob, **Oct15**, DEGRADED |
| `site/macro.html` | `d9806542027253ef3ca5497d0f50f0561b8cbda3`, baked Envelope **Oct16** bundle `2025aa98261ad22b`, red `Risk-off 40` | `8724b70535e6513fc7ecc0a017eae9ecaac9c808`, still baked **Oct16** bundle `2025aa98261ad22b`, red `Risk-off 40` |

**Observed regression:** the *site machine-readable* Envelope and legacy Radar-banner artifact each reverted one source session, while the U.S. measured source and rendered HTML remained on Oct16. A current page can therefore embed an Oct16 bundle while the adjacent canonical site JSON holds an older Oct15 bundle. This is stronger than a generic data-clock disagreement: Git ancestry proves the rollback on the accepted branch.

## Contributing implementation seams (not asserted complete causal root)

- `.github/workflows/engine-render.yml` (blob `071763bec708c8b596d2ef7f958242cfda73b127`) commits **site/** only from a rendering worktree and rebases using `git pull --rebase --autostash -X theirs`. Its post-rebase guards check site assets, Government Revenue, base data-shim, CSS, Market State board coherence and start runtime; no explicit compare-to-newer-main native `site/riskdata/risk_envelope.json:source_session` or `site/rr_banner.json:asof` monotonicity gate is visible. Rebasing a precomputed site JSON artifact onto fresher main can preserve Git ancestry while replacing the newer session. The original engine-render source-vintage and exact runner checkout still need authenticated job logs to prove execution-level causality.
- `scripts/build_site.py` at the same pin calls `scripts.build_risk_envelope.write()` in the same process and renders the returned dict. Its writer in `scripts/build_risk_envelope.py` (blob `df6901f799ad6608ca84904b5afa3aed9ddfc14e`) calls `_atomic_write(data_path)` and `_atomic_write(site_path)` independently and discards any per-file success indication. `_atomic_write` catches filesystem exceptions and returns None, while `write()` may still return a new envelope. A separate isolated M2 synthetic **no-op writer** characterization succeeded: return session Oct16 while both temp destinations remain Oct15. A later expanded one-sided fault-injection test was **platform-refused before execution**; it is NOT a passing test or proof that an actual filesystem error caused the Oct16 Git rollback.
- `site/risk_envelope_live.js` reads the *different* `live/risk_envelope.json` endpoint and validates provisional version/bundle; it is **not** an automatic reader of `site/riskdata/risk_envelope.json`. Do not claim a stale machine JSON overwrote the rendered HTML in the browser. Terminal/AI consumers and entitled origin/edge behavior need separate proof.
- The same current source rendered Macro/CN/HK pages without the `data-whb` alert-client mount after closing-bell. Existing independently scoped [Draft #9513](https://github.com/mastermindx-market-intelligence/macro/pull/9513) patches `lib.pages.write_page` to reuse the canonical wh-banner injector; it does not protect machine source-session monotonicity or create an alert if legacy `alert:null`.

## Minimal acceptance by the actual render/publisher owner

1. On an original render job whose checkout observes Oct15 while accepted main advances to an Oct16 valid site risk artifact, the existing post-rebase publish path must **refuse to replace** the Oct16 machine artifact with Oct15, or select accepted-main bytes, preserving original source/session/bundle. A rebase success is not a source monotonicity receipt.
2. Keep `site/macro.html` baked bundle/session consistent with the accepted site risk artifact **when they claim the same settled revision**. If machine source must lag, mark the old version/coverage honestly rather than replacing it while keeping a fresher page; do not silently average or advance model state.
3. Preserve dual writer last-good under deliberate failure; propagate a truthful write result to page publication instead of claiming a fresh published pair solely from a composed dict. Use existing writer/manifest, not a new store or backup scheduler.
4. Do not use the older site datum as a reason to downshift observed U.S. Risk-off/40 or erase a qualified last-known warning. Cross-region evidence, source health and paid-entitlement policy remain separately scoped.
5. Prove exact-head CI, path/source-vintage tests, complete permitted normal pipeline re-render and authenticated served/browser/notification observations through original release owners. The source-only evidence and PR #9513 are **NOT** production acceptance.

**Status:** SOURCE_VERSION_ROLLBACK_PROVEN_IN_GIT; root-causal job tracing and customer/user delivery **NOT PROVEN**; original #9428/#8132/C1/QLedger holds preserved.