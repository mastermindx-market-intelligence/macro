# TP-2 private off-exchange research view — Phase A (2026-10-11)

**Program:** Macro [#7367](https://github.com/mastermindx-market-intelligence/macro/issues/7367), separate TP-2 owner [#7370](https://github.com/mastermindx-market-intelligence/macro/issues/7370). **Status:** `BUILT_NOT_PROVEN`; overall **MISSION_COMPLETE=false**. This is a *source-free, read-only PRIVATE HOLD* derived view, not the final live product, source acquisition, R2 publisher, API, authenticator, browser, dashboard, model signal, or trading authority.

## Scope and existing owners

- TP1 [PR #8660](https://github.com/mastermindx-market-intelligence/macro/pull/8660) is the sole incumbent trade/quote source and canonical classifier; it lacks admitted production singleton access, real RTH proof and private R2 delivery. No new WS, raw quote archive or duplicate classifier.
- TP-B [PR #8784](https://github.com/mastermindx-market-intelligence/macro/pull/8784) owns draft source-free `equity.tp_b.historical_ruler/v0` observation and `equity.tp_b.history_calibration/v0`. Its source receipts, correction lineage, trading calendar/split-factor vintages and historical completeness are unproven on real vendor data. TP-2 does not reinterpret native correction codes or calculate split factors.
- Macro's existing `darkpool_context.v2` EOD/weekly FINRA/ATS product is untouched. Terminal [PR #915](https://github.com/mastermindx-market-intelligence/mastermind-terminal/pull/915) separately owns the TP1/R0 lossless private decoder; no second Terminal decoder created.

The additive, path-disjoint candidate `engine/tp2_private_ruler_view.py` exposes `build_private_tp2_view(observation,calibration=None,view_asof_ns=...)`, output `darkpool.tp2_private_offexchange_view/v0`. It consumes **only owner-supplied derived dictionaries**. It has no network/storage/credential inputs or side effects, controls no worker or release plane, and never decodes vendor raw T/Q.

## Truthful private states and distinctions

If a valid TP-B observation and its separately available historical calibration agree on `ticker`, RTH `session`, source snapshot SHA, original as-of and split basis/segment, the result is `PRIVATE_TPB_RESEARCH_CONTEXT_ONLY`. The private reader also checks the RTH timestamp is **09:30 America/New_York on the claimed session date**, including DST (without certifying holiday/close eligibility), and refuses single print/cluster notionals greater than the sampled off-exchange total. It enforces bounded exact fixed-decimal tokens and rank/minute range rather than trusting a forged derived row. Eligible output includes:
- distinct observed largest **single print**, largest **same-level/time-window cluster**, and **day total**, plus sample counts and absolute $100k/$500k/$1m tiers;
- distinct `SINGLE_PRINT` / `SAME_LEVEL_CLUSTER` / `DAILY_TOTAL` observed-sample rank states (not all-time claims);
- the TP-B source's **exact-minute-index cumulative** historical baseline with N, median/MAD and nullable robust z;
- source snapshot, manifest and generation SHA refs; original decision/cutoff nanosecond clocks serialized as **decimal strings** so JavaScript cannot silently round their low bits.

Otherwise the returned hold may be `NO_TPB_OBSERVATION_SOURCE`, `SOURCE_NOT_YET_KNOWABLE`, `NO_QUALIFIED_TRF_OBSERVATIONS`, `HISTORICAL_CALIBRATION_PENDING`, `CALIBRATION_NOT_YET_KNOWABLE` or `CALIBRATION_STALE_SOURCE_GENERATION`. **When the source observation is not yet knowable at the requested view time, even its session, ticker, original `asof_ns` and source-generation/manifest/snapshot digests remain null**; retaining them would leak future provenance into an as-seen view. An updated source generation cannot inherit stale historical ranks. Never turn source absence into zero shares, neutral flow or an invented live clock.

For a separately matured calibration, the requested cumulative minute's **share must match the same source-generation minute point**, its `source_available_ns` must be at or before the observation/view cutoff, and a claimed observed baseline requires a source-qualified prefix. A missing or unqualified prefix never silently becomes a robust z-score. Daily rank kinds must bind their source metric; percentiles/median/MAD must be bounded real fractions with positive dispersion for a reported z-score, while missing/thin/zero-MAD states retain their distinct typed nulls. This is derived-record integrity checking, not re-running the historical estimator or certifying original vendor source custody.

The following are deliberately **null**, not empty market tape or substituted EOD values: `live_block_tape`, `repeat_print_price_shelves`, `live_signed_offexchange_flow`, `nbbo_classification_coverage`, `named_ats_attribution`, `finra_ats_delayed_context`, `signal`. Live TRF pipe is NOT a named ATS or aggressor identity. Every result carries `source_authenticated=false`, `market_capture_completeness_proven=false`, `public_delivery_allowed=false`, `ranking_trading_alert_authority=false`. The existing EOD/weekly consumer remains independently `UNCHANGED_SEPARATE_EXISTING_CONSUMER`.

## Separate TP1 provisional minute — no historical joining or second verifier

The optional `tp1_private_minute` argument to `build_private_tp2_view` accepts **only a decoded, already-canonically-verified TP1** `equity.tick_plane.private_minute_artifact/v0` body. The caller must run TP1's existing `engine.tick_plane.private_minute_artifact.verify_private_minute_bytes` first and retain its private blob/custody in the existing source-owned system; TP-2 **does not** independently decode, re-sign, store, fetch or authenticate those bytes. Independent consumer guards check that body is provisional, not source-authenticated, not public or trading-authorized, and aligned to the claimed RTH ticker/session/minute, its own original watermark and cutoff. The new output fields `tp1_minute_state` and `tp1_provisional_minute` default to `TP1_MINUTE_NOT_SUPPLIED` and null. A pre-cutoff TP1 minute becomes `TP1_MINUTE_NOT_YET_KNOWABLE` with **zero source fields or digests revealed**, even when TP-B history happens to be separately available.

Where separately known, the TP1 projection is `PROVISIONAL_TP1_MINUTE_RESEARCH_HOLD`, with its original minute/decision/watermark nanoseconds as decimal strings, source manifest/observation digests, sampled lit/TRF counts, source-lit quote-age-qualified count, and **provisional raw TRF gross notional INCLUDING potentially source-condition-ineligible prints**. It explicitly sets `trf_volume_eligibility_proven=false`, `classification_accuracy_validated=false` and `join_to_tpb_historical_ranks=false`. It cannot be added to or matched numerically against TP-B's **condition-qualified/final-vintage historical** TRF total; each family's clocks, source generations, correction status and numerator policy are different until the original owner qualifies a shared receipt. It does not populate live per-print block tape, recurring price shelves, signed TRF aggressor flow, NBBO coverage, named ATS, public/tenant route, Prophet predictions or trading signals.

A second frozen fixture `tests/fixtures/tp2_tp1_private_minute.synthetic.v0.json` was produced by TP1's **actual** `project_provisional_minute` → `project_private_minute` at `macro@a3879855b943e1007e43750b38aedd185d745cb9` using two synthetic source observations (one lit and one unclassified TRF) at 2026-10-08 **09:30 ET**. It was independently read back through **the original canonical** `verify_private_minute_bytes`: **2,411 canonical bytes**, SHA256 `61097ef904444751058994e4015b2a4ddaa650c56f0f57ea4e880a097676d60e`, sampled lit=1/TRF=1, raw provisional TRF notional $250,000, all source/public claims on HOLD. This is an interoperability proof for synthetic data, **not actual vendor capture or entitlement**, and the fixture has no native trade IDs, private source URLs or raw vendor frame.

## Reproducible evidence

`tests/fixtures/tp2_tpb_source.synthetic.v0.json` is a frozen actual-Python-serializer fixture, generated from TP-B's **immutable published source commit `23787b0518b6bd9ab807194698014b32976d1f48`**, not a manually emulated producer. A second read-only source replay on M2 reproduced the exact **4,618 bytes**, SHA-256 `a499fb167aab3498943663598593408b008b2e98c79565e07177c310cba4a196`, including its original synthetic unqualified source state. This is **not licensed market data, genuine external producer receipts or history authenticity**.

Run from the exact isolated Macro worktree on M2:
```sh
cd /Volumes/Mastermind/agent-workspaces/sol/tp2-private-offexchange-view-20261011
PYTHONPATH=. python3 -m pytest -q --noconftest -p no:cacheprovider tests/test_tp2_private_ruler_view.py
```

The existing new TP-2 suite checks byte-pinned source/golden, private-only authority, null/unknown statuses, exact 64-bit clock representation as text, separate observed objects/history, correction-generation invalidation, original vs evaluation availability, split/session mismatch and synthetic source/issuer-identity/ATS overclaims. Tests establish private transformation behavior only. New suite requires **proper original CI policy owner enrollment** under the protected workflow. No rename/waiver/bypass or different account/tool retry of refused CI effects.

## Actual unblock and DONE_WHEN

1. The original approved Quote Hub/TP1 source operator proves incumbent singleton T/Q lease, entitlements and original RTH T/Q receipts with 99% connected RTH seconds, >=95% qualified lit quote-rule coverage using prior eligible NBBO <=5 seconds, and same-scope volume within 2% for >=90% comparable names. Previously denied root SSH remains denied; no second RT socket.
2. TP-B source owner LISTs and budgets entitled Tier-A historical objects **before GET**, supplies a small licensed original RTH TRF cohort with venue, condition, correction/restatement, source-availability, real market calendar, consolidated volume and split-vintage proof. No 2y all-market wholesale archive on an approximately 93%-full 4TB drive.
3. Original data/security and CI policy owners independently review this phase, enroll the test, qualify rights/private R2 and actual Macro service reader. The existing Terminal #655 owner then wires the authenticated source alongside unchanged EOD/weekly FINRA, renders truthful original/report clocks, real block/shelf evidence only when present, and proves responsive EN/ZH/light/dark browser behavior with correction/replay.
4. Only successful original data and browser acceptance justifies release; no Prophet ranking, automated signals, sizing, alerts or trading authorization follows from this private research view.

**NOT merged, deployed, installed, authenticated or production proven. Do not use Vercel.**
