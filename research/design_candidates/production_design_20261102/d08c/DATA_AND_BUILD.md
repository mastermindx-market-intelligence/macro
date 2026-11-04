# Data, backend and future build contract

This document maps the proposed UX to existing source owners. It authorizes no implementation, activation, migration, merge or deployment. All source links and exact blobs are in [SOURCE_AUDIT.md](SOURCE_AUDIT.md).

## Objects, identities and limits

`D08-OPTIONS/1.0.0` supplies semantic objects (`listing`, `observation`, `cohort`, `node`, `pin`, `draft`, `saveIntent`, `replay`, `returnContext`). Those logical fields are not a new store or released API. Use the existing validators and adapters, not a parallel representation that becomes canonical by accident.

### Canonical authored draft

Current schema: `options_plan_draft.v1` in `terminal/lib/optionsPlanDraft.ts`.

| Field / constraint | Actual source meaning | UI responsibility |
| --- | --- | --- |
| Root object | Exactly `schema`, `legs`, `research` | No extra ad hoc wire fields |
| `legs` | 1–4, one exact root, unique exact contract identities | Preserve independent side/quantity/price per leg; max4 is real |
| `snapshot` | Detached original ShortlistPin, not a refreshed quote | Preserve copied row, identity, source family/list/session, schema, raw as-of and stale flag |
| Contract identity | Exact root, right C/P, real expiry date, finite positive strike, supplied terms and identity key | Do not trim/case-fold/suffix-normalize; a human-readable label is not the identity |
| Terms | Multiplier, deliverable, settlement, exercise style may be null | Missing stays unknown; Hot estimated premium ×100 does not establish terms |
| `assumptions.side` | `buy`, `sell` or null | Direction is explicit; price does not carry a sell sign |
| `assumptions.quantity` | Null or safe integer 1–1,000,000 | Quantity is contracts per leg; proportional spread scaling cannot replace independent quantities |
| `assumptions.entry` | Null or `{kind:'user_assumption', premium_per_unit: finite >=0, currency:'USD'}` | Never populate from observed mark without an explicit authored decision |
| `research.thesis` / `invalidation` | Up to4000 Unicode code points each | Keep full user text and inline validation |
| `research.horizon` | Up to160 code points, single line | Editable research interval/date, independent of option expiry; do not force a new date-only schema |
| Bounded data graph | ≤65,536 serialized bytes, bounded depth/node/text graph; source row ≤8192bytes and bounded depth | Reject unsafe/oversized graph without invoking getters or coercing source values |

The constructor sets side, quantity and entry to null. Coherent snapshot validation does not authenticate the provider or re-run the full original-list ambiguity check; pin creation owns that check. Mixed expiries can remain a valid research draft even though the current expiry calculation refuses them.

### Calculation admission is narrower

`preparePlanExpiryRequest` admits ordinary SPY/QQQ interpretation, one common expiry and complete authored assumptions. The request is exactly `schema`, `draft`, `spots`, `payoff_basis`; basis is `{kind:'hold_to_expiry_intrinsic', expiration:'YYYY-MM-DD'}`.

The consumer fixes the axis:

```
lo = max(0, 0.8 * minimum strike)
hi = 1.2 * maximum strike
spots = sorted unique(101 equally spaced samples rounded to 0.001, plus exact strikes)
```

For the synthetic600/610 fixture: range480–732, step2.52,103 points.606 is a returned-axis candidate;605 and603.20 are not samples. A qualified breakeven annotation may be603.20, but the client must not invent a curve value there. Focus/full view selects existing samples; it does not interpolate. Display tick marks can label an axis without claiming a sampled quote or returned P/L.

The Macro bridge further bounds premium per unit and hypothetical spots to0–1,000,000,000; quantities remain1–1,000,000. Producer spots allow1–1001 values, but that does not grant custom-axis UI in the current consumer. Exact OCC strikes must be representable in thousandths with integer millistrike1–99,999,999; do not round an incompatible strike into a different contract. Any refused leg prevents the whole curve.

## Actual producer and API chain

| Concern | Existing entry point | Owner / boundary |
| --- | --- | --- |
| Structure | `StructureView` → `flowGet` with `max_pain:ROOT`, `oi_time:ROOT`, `oi_change:ROOT`; lazy all-root OI change | Incumbent Options data owner; retain EOD source cadence |
| Expiry calculation | Terminal `POST /api/options/plan/expiry` → fixed `${BILLING_BASE}/api/options/plan/expiry` | Existing auth and Options producer; request reconstructs canonical grid |
| Macro expiry preparation | `app/options_plan.py` → `app/options_plan_source.py` → `engine/options_plan_expiry.py` → `engine/options_payoff.py::expiry_payoff` | Existing privately installed dated reference, narrow ordinary ETF policy |
| Plan local admission | Original held #804 `investigationOptionPlanAdmission.ts` / native workspace callbacks | Existing Investigation owner; no network/storage/IDs/calculation in admission helper |
| Save/reconcile | `terminal/lib/investigations.ts`, `/api/investigations`, `apply_investigation_revision_v2`, `read_investigation_operation_v2` | Incumbent authenticated revision owner / D23 contract |
| Alert status and receipts | Existing `/api/alerts` and `/api/alerts/receipts` via native workspace | Incumbent alerts owner; open-time read, no new polling loop |
| Actual positions | Existing D22 holdings owner | No D08C account position or order write |

The expiry proxy validates content type, bounds UTF-8 request64KiB and upstream response192KiB, enforces its existing rate limit and15-second timeout, rejects redirects, uses private/no-store with Vary Authorization/Cookie and nosniff, and releases only validated qualified output. A timeout here is an unavailable calculation, not proof about an unrelated Save. Do not bypass the fixed upstream URL or inject caller-controlled credentials/reference contexts/clocks/hashes.

### Qualified dated reference

The private reader uses its service-owned configured path/hash, checks owned0700 directory and owned single-link0600 regular file, rejects symlinks, enforces256KiB, held/named identity consistency and SHA-256. Accepted original-source custody and installation are separate from matching bytes. No such private file or installation was inspected or changed in this assignment.

The terms join selects exactly one matching retained reference row or validates an exact-single observation, then applies the narrow `ordinary_etf_terms` policy. Supported root is exactly SPY or QQQ; shares per contract100, American exercise, no conflicting explicit currency/multiplier/deliverable, and applicable CFI checks. `additional_underlyings` absent versus explicitly empty remains distinguishable in term interpretation. The policy can qualify an ordinary100-share USD deliverable from the exact observation; it is not an inference from a source-list premium estimate.

The consumer requires `server_held_qualified_reference`, `dated_reference`, correct root/expiry coverage, zoned capture and known-by instants, capture≤known_by, canonical reference date, installed-observation/reference SHA-256 digests, zero reference requests, and explicit false assertions for current terms/quote eligibility, discovery authentication, original-byte replay and historical first availability. Unknown or mismatched fields suppress all current numerical output.

`known_by` is the calculation cutoff, not a source price. `reference_as_of` is the dated query basis; `reference_observed_at` is retained capture time. Discovery pin clocks remain original evidence. Same-day expiry carries “no expiry instant inferred”; comparing calendar dates does not prove a settlement instant or historical availability. No arbitrary age policy is invented for a clearly dated hypothetical. Current trading-term or quote eligibility stays false.

## Numerical meaning and presentation

For signed contract quantity q, multiplier m, authored unit premium p and intrinsic value I(S):

```
cost = Σ q*m*p                   # positive debit, negative credit
P/L(S) = Σ q*m*(I(S)-p)          # USD total for the exact quantities
```

The exact response fields are `curve.spots`, `pnl`, `cost`, `max_gain`, `max_loss`, `breakevens`. Do not invent `entry_net_cost` or submit a net spread entry field.

| Response | Meaning | Rendering rule |
| --- | --- | --- |
| `cost` | Signed net premium | Positive→entry debit, negative→entry credit; retain sign in data; 0 remains zero |
| `pnl` | Signed conditional expiry P/L | Currency/total quantity basis visible; not realized P/L |
| `max_gain` | Highest signed P/L or UNBOUNDED | Do not assume it is positive just because of its field name |
| `max_loss` | Lowest signed P/L or UNBOUNDED | Direct label: worst expiry P/L. A loss-amount card explicitly converts negative P/L to positive magnitude and retains raw sign; never reject a negative valid max_loss |
| `breakevens` | Discrete roots returned by producer | Empty means no discrete roots returned, not “P/L never equals zero”; zero plateaus need qualified copy |

Extrema are calculated over S≥0 from zero, strikes and the high-price call slope, not merely the displayed grid endpoints. Keep UNBOUNDED as such; never substitute a finite chart edge. The current consumer validates finite fields and exact axis but does not independently recompute cost, extrema or roots. Future adversarial checks should cover nonfinite/overflow inputs, incoherent arithmetic and plateau semantics without misrepresenting them as newly passed tests.

Fees/slippage are excluded/unknown. Early exercise, assignment, actual fixing/settlement, fill/execution and realized outcomes are excluded. The bridge invokes only expiry intrinsic math and removes generic BS/rate/IV metadata used by other engine functions. Before-expiry model/time/IV/rate/Greeks/POP controls remain unavailable for this Plan endpoint.

The fixture's cost+320, worst P/L−320, best P/L+680 and breakeven603.20 are independent arithmetic, not an actual returned producer response or qualified reference. The Paper card's “assumed100” is deliberate. A builder must replace it with source-qualified terms only after the actual reference has been validated.

## Clocks, freshness and nulls

| Dimension | Preserve | Prohibited substitution |
| --- | --- | --- |
| Listing | Namespace + exact root; venue/security identity when supplied | Joining by display ticker alone |
| Discovery | Original family/list/session/schema/raw as-of/stale flag/row | Replacing a pin with a later quote on reopen |
| Structure | Each panel's position session/report date/as-of | Calling t−1 OI live or directional |
| Observation | Actual event/spot time and source definition when available | Using retrieved/built time as observed time |
| Reference | Query basis, capture time, qualified term interpretation | Treating query date as proof of historical first availability |
| Calculation | Known-by cutoff and actual request axis | Labelling a saved old result current |
| Revision | Exact owner ID, revision, manifest and commit/readback status | Reopening latest when requested N is unavailable |
| Alert | Condition version/basis, evaluation/firing time, independent delivery status | Treating a firing as notification delivery |

Source absence, not-in-list, not-supplied, null, zero, unavailable, stale and partial stay distinct. The existing OI weekday staleness heuristic is not a complete market-holiday calendar. Cache TTL beyond the inspected component behavior was not established; use the incumbent source contract, not a guessed interval. Do not add polling to Structure or alerts. A manual current-evidence read keeps original data visible and cannot overwrite authored entry.

`investigationReview.receiptsFrom` preserves each supplied outbox row's own `payload.value` and `payload.source_asof`. The latest trigger stamp is a fallback only for that same firing, never for an older receipt. Keep queue `read`, `unavailable` and `absent` distinct; a capped readable queue's missing row is not nondelivery. Preserve `orderReceipts` correction relation and the complete supplied receipt list when rendering the latest-firing summary from `projectReview`. A correction follows its original; neither history nor original evidence is replaced. These are existing owner semantics, not a D08C outbox or delivery service.

## Persistence, account isolation and recovery

Protected master has a closed manifest without `option_plan`. Held #804 adds optional validated `option_plan` in `investigation_manifest.v3` and exact-revision callbacks. It also preserves/refuses conflicting `scenario_capture` rather than silently converting it. Reuse that carrier after its existing review/release gates; D08C must not add a Save endpoint, schema alias, side store, custom IDs, queue or fallback journal.

The incumbent session journal key is `mm.investigation.pending.v2:${encodeURIComponent(owner)}`. It inspects prior raw/account-prefixed custody and refuses conflicting/invalid operations. Retention is verified before transmission. The browser journal is not server persistence and does not promise survival after browser/session loss.

Exact receipt matching includes record ID, next revision, lifecycle and manifest. Known commitment is monotonic: session expiry or failed exact readback cannot downgrade it to unknown. Before commitment, `not_found`, auth failure, timeout and malformed responses remain uncertain. Held #804 handles legacy `invalid_payload` local rejections with owner recheck; a result-only receipt can be insufficient. Only an exact proved `not_applied` can make a later owner-supported new attempt possible. This design assignment performs no such replay or attempt.

On A→B account change, remove A's visible data/admission and reject stale callbacks. Preserve A's unresolved custody under A; never migrate it to B or fabricate settlement. A return to A reuses original reconciliation identity. Copy-draft escape is a user-initiated local readable export of the currently authorized research, not a canonical Save or recovery protocol. Preserve exact readable identities/assumptions/source references, exclude credentials/protected transport data, and report clipboard failure. Do not copy another account's retained intent.

## Build plan for a future authorized implementation

1. **Resolve prerequisites on original owners.** D08 confirms contextual entry/return behavior; F01/F02 publish the actual frozen joint contract; QA01 obtains formal review admission; original #804 owner resolves its held conditions; D23 confirms admitted condition and receipt semantics. No change in this package waives a hold.
2. **Reuse current source models.** Keep `optionsContractShortlist`, `optionsPlanDraft`, `optionsPlanPayoff`, `OptionsPlanDraftEditor`, `OptionsPlanPayoffPanel` and the incumbent Investigation host/workspace. Integrate inside the actual owned `/options` route, never promote `/dev/options-plan` by assumption.
3. **Compose presentation through F01/F02.** Reuse shell slots and tokens. Apply C01/C04/C05 hierarchy, C09 exact-leg controls and C06/C10 research editor. Preserve all 15 native pane families, aliases and actual mounted defaults. One overlay; conditionally restore focus.
4. **Implement comparison as a bounded presentation extension.** Alternatives stay local until explicit owner Save. Preserve per-leg inputs. Qualify each result; overlay only identical axes/identity/units and admitted calculation basis. The bridge exposes basis/engine semantics but no independently versioned model receipt in the consumer type; do not invent a version field. D08 must settle any needed cross-response version guarantee before declaring arbitrary overlays compatible.
5. **Wire native admission and revision reading.** After release, use existing callbacks and manifest-v3 path. Keep native New, Save and journal ownership. Test stale callbacks, exact revision mismatch, legacy custody and scenario conflict before enabling account Save.
6. **Connect existing watch/review UI.** Preview only supported conditions; arm separately; show condition, threshold, expiry, linked revision and evaluation/firing clocks. Revisit joins original revision, fresh reads and actual owner receipts without new evaluation infrastructure.
7. **Run the future acceptance contract on admitted test owners.** Arithmetic oracle alone is insufficient. Exercise genuine browser paths, responsive classes, account change, dropped responses, unavailable evidence and keyboard/screen-reader flows. Capture exact source/deployment/browser identity separately.
8. **Roll out only after a later explicit implementation/release commission.** Use the incumbent feature availability mechanism; no new control plane. Rollback disables the presentation/entry path through the same owner and preserves native records, journals and unresolved commands. Never clear uncertain custody to simplify rollback.

### Performance and rendering targets

Future p75 budgets: LCP≤2.5s, INP≤200ms, CLS≤0.1, separately mobile/desktop. These are targets, not measurements. Lazy-mount hidden pane charts and editors; bound active subscriptions; retain existing source-cache ownership; use stable skeleton dimensions; render only necessary dense rows/series; do not fetch every sibling pane or pre-open inspectors. Benchmark realistic four-pin/four-leg and dense OI data, not only the two-leg fixture.

### Accessibility and review gates

Use semantic forms/tables, labelled fields, non-color state communication, visible focus,44px house touch targets, localized errors and keyboard-accessible chart alternatives. Test320/390/768/1024/1280/1440/1600 widths with actual shell and inspector occupancy,400% zoom/reflow, long EN/ZH labels, light/dark and reduced motion. Screenshot inspection does not prove keyboard behavior, hit geometry, contrast ratios or screen-reader output; these remain explicit future gates.

No product tests, benchmark, live SQL save, alert activation, release pipeline or deployment is executed by this package. The source and artifact verification reported in `VERIFICATION.md` is narrower and must remain so.
