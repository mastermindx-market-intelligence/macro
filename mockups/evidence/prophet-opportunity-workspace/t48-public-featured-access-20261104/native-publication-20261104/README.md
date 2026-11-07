# D03 T48 — original native public Featured publication (2026-11-04)

Status: **native source/pair and anonymous visual proof qualified**; **not deployed, signed-in or merge accepted**. Original macro PR #9495 remains Draft/HOLD. This supplements the pre-existing Save, P0B/G7 and EW-P4 evidence without replacing any screenshot history.

## Reproducible source and output

- Publisher source: `9378425800564062fe4d178e7c16c5360eb61636`. One clean, detached Ubuntu0 worktree; no external data refresh, drip or imported credentials. Native modules `scripts.build_site`, `scripts.inject_data_base`, `scripts.externalize_css`, `scripts.optimize_assets` each exited 0 (`native-build-receipt.json`); build duration about 18.6 minutes.
- Public `site/us_stocks.html`: SHA256 `2bfb709b652a92e40f48793fb2ac4bb542f7130b91a534b8ac8d2570388419db`; public Today 0 of 12 Featured, accessible EN/ZH access-empty region and functional Screener CTA. Generated stylesheet `site/assets/css/11a0c27d.css` is a **new referenced dependency**; preserve previously published CSS files.
- Bound `site/factordata/us_standouts.json`: SHA256 `2e77214946c6ea2b63271dddae81cdd5c0b8ac8bf22345bef50d1fa6e2623d7a`, board `2026-11-03`; `site/factordata/signal_gate.json` shares pair `f14ee3260ab9483b8776862544075323`. Essential protected `site/premiumdata/us_stocks.json`: SHA256 `92e2e176c52fc2ea4c1be7b791764c19b704c5b00d13a1966ae1f5d3f2a0d8cc`. Do not serve the protected payload anonymously.
- `pair-verify.json`: **12/12** identity, ordering, partition and Plan-target checks true. Candidate pool **3 public / 156 protected = 159**, Screener **3 preview / 48 protected = 51**, entitled Today 6, protected Plan targets 55, missing 0. The public HTML exposes zero protected Plan controls.

## Visual and access proof

- `capture-16cell/observations.json` is the exact native-generated source/page readback; 16 browser cells = widths 1440/768/390/320 × dark/light × EN/ZH, all `access_empty=true`, no horizontal overflow, zero Playwright page errors and zero public protected Plan controls. Every case has a hashed full-page PNG; six cases have additional above-fold images.
- The offline anonymous harness intentionally denied protected premium/remote URLs; local live-data endpoints consequently return 404 in its isolated server. These are documented in observations and **are not** production network, authenticated Save/list/return, or deploy acceptance.
- Focused source regression run after capture: `147 passed, 22 skipped` across public Featured state, stale-VM renderer guard, W1 intake and board priority UI; screenshot manifest SHA256 verified for all 16 full-page captures; all CSS references in the generated page resolve locally.
- The first capture harness attempted to wait for a public `po-card` and terminated on truthful public zero. The existing harness now detects zero-membership directly and asserts its explicit access-empty state; the successful `capture-16cell` is a **new v2 output**, not an overwrite of the previous failure or older accepted screenshots.

## Historical origination invariant — important non-publish decision

An exploratory `python -m scripts.build_prophet --date 2026-11-04` rerun against this **already-advanced** local plan ledger completed exit 0 but was **rejected for publication**. It would suppress 12 previously originated plan receipts (previously `intake.originated=12`, rerun `0`) and modify **367** `site/prophet/states` files, including clearing previously recorded change reasons. None of its `site/prophet/index.json`, states, ledger-derived changes or new source snapshot is approved for staging.

The committed index's `source_board_sha256=e655802dbb50851d726120ac7db48886a6d36d3a0f6d59ff68a99ddb40d6f792` remains the **immutable historical source of those 12 already-originated plans**, with its existing archived `data/prophet/origination_sources/e655802d....json.gz`. Do not falsely rebind the historical index to the later board. Normalized JSON diff of the historical snapshot versus the newly generated current board shows 12 added `already_open` lane reasons (the previously originated setups) plus emitter/observation timestamp and generation/pair identifiers; existing eligibility and ranking are preserved. The new board is an updated current distribution/withholding view, **not** a retroactive origination source. Exact current board and gate are published as a pair, while historical Plan lineage stays anchored.

## Post-commit source replay and safety repair

The detached clean checkout at `8182ed933354725ffa7af53b711d98fa32c91606` independently passed the same **12/12** native verifier checks, now retained in `pair-verify-clean-8182.json`. No mutable publisher-worktree index or state file is needed for that result.

The underlying source bug discovered above is addressed by a separate same-PR **same-date idempotency preflight** in `scripts/build_prophet.py`. It checks the previously recorded content-addressed snapshot before any new snapshot/ledger/state write. Replaying an identical source and publication date is a no-op; rebuilding the same date with a changed board emits a specific REFUSED error, preserving 12 historical origination receipts. It has 12 focused adversarial tests plus 253 existing Prophet regression cases, **265 passed**. A future EOD publication with a *new date* still takes the normal path; no bypass flag was added.

## Publishing fence and open acceptance

Stage only the verified generated page, **new** stylesheet, current board, matching gate, protected companion payload, repaired capture harness and this evidence directory; do **not** stage the other 14,000+ local generated/market/state changes or delete legacy CSS. Re-run the 12-case verifier against a clean post-commit checkout and qualify hosted exact-head CI. Product release still requires authenticated Save/reopen, Sources → Plan → same candidate, real served browser, shared-shell integration and eligible release gates. No merge, enqueue, un-draft, Ready label, deploy or purchase.
