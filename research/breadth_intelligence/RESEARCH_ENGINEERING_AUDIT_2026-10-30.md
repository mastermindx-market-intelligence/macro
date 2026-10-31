# Breadth Intelligence: research/engineering audit and quote-qualification slice

Work began 2026-10-30 and continued 2026-10-31 UTC. Commission: Chris's RESEARCH/ENGINEERING request via Grok Bot, carried by the current user. Source custodian/program CEO: Chris. This report supplements [Draft #10212](https://github.com/mastermindx-market-intelligence/macro/pull/10212); it does not replace its master plan. The separate DESIGN session owns Paper and visual design.

**Disposition: source-only candidate; no producer integration, merge, production change, alert, trade, historical-capture or product-acceptance claim.** The user authorized one bounded backend implementation with tests and independent Subagent Fabric review. Selecting this additive input contract under that assignment is not a claim that Chris separately approved the final code. Chris retains program integration and release decisions.

## Source custody and census

Protected procedure pin: `mastermindx-market-intelligence/Mastermind@bb85b429f2ffffd38408080ce4df7d6378c34100`, skillpack 1.0.1. Parent #10212 inspected at `f9781a8172b5940773d540e9386a6f48b3159b69`, including [MASTER_PLAN.md](https://github.com/mastermindx-market-intelligence/macro/blob/f9781a8172b5940773d540e9386a6f48b3159b69/research/breadth_intelligence/MASTER_PLAN.md) and [PAPER_DESIGN_BRIEF.md](https://github.com/mastermindx-market-intelligence/macro/blob/f9781a8172b5940773d540e9386a6f48b3159b69/research/breadth_intelligence/PAPER_DESIGN_BRIEF.md). That branch is read-only to this session.

Isolated branch: `sol/breadth-quote-qualification-20261030-c3`, from Macro main `3c8546e8aa56a0310e49fbcfba2c3debf84d8127`. The initial branch-create call was interrupted; same-carrier exact-ref reads established absence before successful same-name creation. The census/contract was posted and read back at [#10212 comment 6537418132](https://github.com/mastermindx-market-intelligence/macro/pull/10212#issuecomment-6537418132).

| Incumbent | Observed state and custody decision |
| --- | --- |
| #10212 | Draft; four added files: projection, its new test suite, master plan, Paper brief. Pure `compute_tier` adapter remains a candidate. No edit to those paths. |
| #10213 | Active Draft/HOLD sector/theme factor, regime, timeline, owner-bridge and multi-horizon work; observed head `92cc89d9c12db5005df5ba3a5ca93bd6d4262e67`. Also owns a CI manifest edit. Preserve that writer and its clock/factor contracts. |
| #8299 | Draft subtheme replay qualification, observed head `a9668b5c6ed23f4fe7a273b63c54af728e71608e`. Preserve subsector/replay paths. |
| #7870 | Draft semiconductor/theme foundation, observed head `ab3faefa3bf739d806ce6c41227b56bd861737ae`. Preserve theme graph and source-local rights work. |
| #9507 / #9600 | Draft rotation architecture and sector source-time disclosure, observed heads `d86fbab2269cbf1c5f73003322bc4a7ab2ee29a7` / `a96b39002fcf9fbe0f8108252a7a8203709dafe9`. |
| #9240 | Merged measured-group contract in `engine/leadership_rotation_context.py`; reuse its measurement semantics, do not rebuild. |
| Mastermind #1556 | Open draft SIC-pure subindustry scientific research, observed head `3d8137d1f35440540736f196ec7c924346883886`. No predictive qualification is inferred from its existence. |

Changed-filename comparisons for the six open Macro PRs above showed no intersection with this slice's two code/test paths or this report. This is an observed census, not a global writer lock. Recheck collisions before later integration.

The existing `WS-LEADERSHIP-ROTATION-INTELLIGENCE` and `WS-GMI-THEME-GRAPH` workstreams and their referenced handoffs were consumed, including `LEADERSHIP-ROTATION-INTELLIGENCE-2026-10-14.md` and `GMI-THEME-GRAPH-2026-10-21-completion-commission.md`. Preserve accepted measured-product work, open scientific/natural-path proof, and GMI current-generation identity/membership/rights/sealing obligations. This candidate creates no organizational workstream, competing plan, taxonomy, ledger or source owner.

### Parent CI finding

At the inspected parent head, [fences run 41120467258](https://github.com/mastermindx-market-intelligence/macro/actions/runs/41120467258) passed. [CI run 41120467198](https://github.com/mastermindx-market-intelligence/macro/actions/runs/41120467198) failed: contract-delta job `124285878092` identified `tests/test_breadth_intelligence_projection.py` as a new pytest suite named by no workflow `run:` step. The 12 pack jobs passed, but that is not evidence the new suite executed. Chris owns the parent correction. This slice appends tests to the already registered `tests/test_live_breadth.py`; it does not edit CI authority or #10213's manifest.

Independent of hosted CI, this session also staged the exact parent projection/test blobs (`a327c256b461496f5128d5210c65b2a552405433` / `b3d55914d5c0e757062bfb7609ad1371a07b8b32`) and ran all **14** existing cases with their injected counter replaced by the real, unmodified `engine.live_breadth.compute_tier`: all passed. A separate default-adapter call, with no counter override, returned the expected 40% positive participation and 50% legacy A/D ratio. This establishes focused incumbent-counter compatibility for those fixtures; it does not cure workflow registration, qualify live inputs or approve the parent PR.

## 1. Algorithmic intraday breadth

The incumbent [live breadth core](https://github.com/mastermindx-market-intelligence/macro/blob/3c8546e8aa56a0310e49fbcfba2c3debf84d8127/engine/live_breadth.py) is a pure counting/join owner. Keep descriptive measures separate:

- Positive participation is `100 * advances / observed_valid_return_n`, including genuine unchanged observations in the denominator.
- Legacy `adv_pct` is `100 * advances / (advances + declines)`, excluding unchanged. These measures can differ materially and need distinct labels.
- For `k` positives among `n` observed eligible names from a known cohort of size `N`, the logical interval is `[100*k/N, 100*(k+N-n)/N]`. It is an identification bound, not a confidence interval.
- Prior-close returns, each MA comparison and each new-high/low comparison need their own valid threshold denominators. A fresh price alone does not establish a valid return or MA comparison.
- Comparisons of changes require the same cohort, definition, endpoint basis and comparable elapsed session time. Daily McClellan/EMA or other daily series cannot be relabeled intraday without a separate supported definition and observations.

`compute_tier` can count a supplied last price in `n` even if its prior-close threshold is absent. Therefore quote qualification must not be called final measured breadth. Same-basis prior-close/MA/extrema validity remains a downstream prerequisite, including corporate-action adjustment and the prior completed-session cutoff.

Two additional full-core synthetic counterexamples delimit incumbent semantics. One price with no prior close yields `n=1` while `adv=dec=unch=0`. Also, the existing composite weights each tier's MA percentage by tier `n`, not by its valid MA denominator. A 100-name tier with one valid MA observation (below MA) and a one-name tier with one valid MA observation (above MA) produce composite `pa50=0.990099%`, whereas pooling the two valid observations gives 50%. This faithfully preserves the existing nightly weighting convention, but it is not a pooled constituent-level MA share when availability differs. Future group/composite consumers must expose and use the applicable per-metric counts. This audit does not change that incumbent contract.

The [poller's ThresholdStore](https://github.com/mastermindx-market-intelligence/macro/blob/3c8546e8aa56a0310e49fbcfba2c3debf84d8127/scripts/live_breadth_poller.py) reads current constituent/cache files and refreshes according to the newest close date. Same-date corrections or membership changes need explicit invalidation and version evidence before a historical/PIT claim. No cache or threshold-store change belongs to this slice.

## 2. Per-symbol freshness: reproduced failure and selected boundary

The [existing parser](https://github.com/mastermindx-market-intelligence/macro/blob/3c8546e8aa56a0310e49fbcfba2c3debf84d8127/engine/live_quotes.py) emits price, real/synthetic timestamp status, price basis, source and native quote identity. `fetch_full_market` currently drops these per-member fields, retains all non-null prices, and uses the maximum quote timestamp as the snapshot clock. One fresh member can therefore refresh a stale cohort. A daily/previous-close fallback can also have a recent synthetic refresh clock.

Controlled synthetic responses exercised the actual unmodified parser, poller and core, with no real vendor request:

| Synthetic 1,500-name input | Incumbent result |
| --- | --- |
| One fresh advance; 1,499 stale flat prices | `usable=true`, 100% coverage, source age 1 minute, 1,499 unchanged votes |
| 1,500 daily-bar fallback prices with fresh synthetic clocks | `usable=true`, 100% coverage, source age 0, 1,500 unchanged votes |

These prove source-level counterexamples, not their frequency in the live feed. The committed `site/live/breadth.json` is an old artifact; it does not prove a current production outage. No authenticated live-feed or current production-path receipt was obtained.

### One additive backend slice

Add `qualify_snapshot_members` to `engine/live_breadth.py` and discriminating tests to `tests/test_live_breadth.py`. The intended later consumer is the existing single-snapshot producer at its parser-to-count seam. No competing fetcher or history store is introduced.

The helper accepts parsed quotes, a canonical unique cohort, explicit timezone-aware `observed_at`, `asof`, `session_start`, `session_end`, and a finite positive age limit. It returns admitted prices, per-member source times, explicit exclusions, quote-qualified coverage and oldest/newest admitted clocks. It requires consistent Polygon/native identity metadata, positive finite prices, trade/minute basis, a literally false synthetic flag, real aware timestamps, no source time after receipt, receipt no later than the query cutoff, the caller's half-open session interval, and per-member bounded source age. Canonical dot/dash collisions are refused instead of selecting the last row. Unrelated fresh symbols cannot refresh the cohort. Inputs are not mutated.

This validates caller-supplied metadata; it is not independent source authentication. A mapping cannot recover exact duplicate rows already overwritten by an upstream parser. Canonical ticker spelling is not a permanent historical security identifier. Recent quotes can have different timestamps within the allowed window: this is bounded-age coverage, not a synchronized tape or proof of current trading/absence of a halt.

The session interval is `[session_start, session_end)`. An observation exactly at the closing boundary is excluded, so this is not an official-close/closing-auction methodology. The caller supplies calendar-qualified boundaries, including holidays and early closes. The helper does not infer that the market is currently open.

The current breadth poller's `session_tag` explicitly does not model early closes. Other quote paths already use existing early-close/calendar helpers; future breadth integration should reuse the proper owner rather than copying another calendar or treating the current poller tag as early-close proof.

**The existing poller, parser, `live.breadth.v1` payload/gate and production behavior remain unchanged.** The two reproduced failures remain possible on that incumbent path until separately reviewed producer integration uses qualified inputs. No `usable`, measured, licensed or product-ready verdict is emitted by this helper.

## 3. Point-in-time GICS and theme membership

The current `engine/stage_flows._load_gics_map` reads a current EquityDesk reference parquet; that is not a historical classification-vintage contract. `engine/subsector_rotation._theme_history` explicitly rolls today's theme tree across earlier history. Such curves must remain retrospective reconstructions, not information asserted to have been known then.

Use the existing [GMI graph contract](https://github.com/mastermindx-market-intelligence/macro/blob/3c8546e8aa56a0310e49fbcfba2c3debf84d8127/contracts/theme_graph/README.md). Resolve the latest relevant version known by the query's knowledge cutoff, then apply its effective interval: `belief_time <= knowledge_cutoff` and `valid_from <= membership_at < valid_to`. Preserve later corrections as later-known versions, delisted/closed memberships and original evidence. An announced future classification does not become effective early. An older version must not be resurrected merely because the newer known version closes an edge.

Company-to-basket `MEMBER_OF` and basket-to-theme `EXPRESSES` joins remain read-time composition. No persistent company-to-canonical-theme shortcut is added. Themes overlap and cannot be summed as disjoint market participation. Historical symbol changes, multiple securities per issuer, unavailable cohort membership and seeded/reconstructed edges need explicit counting/evidence modes.

The parent projection's belief-time check is not a complete bitemporal resolver. Distinguish source event/valuation time, actual receipt/knowledge time, membership effective time, revision knowledge time and build time. A delayed observation can be received after its market timestamp; these clocks are not interchangeable.

## 4. Commercial rights, access and retention

**Commercial gate: `APPROVED_BY_CHAIRMAN_ATTESTATION`.** [Protected commercial-rights law](https://github.com/mastermindx-market-intelligence/Mastermind/blob/bb85b429f2ffffd38408080ce4df7d6378c34100/docs/COMMERCIAL_DATA_RIGHTS.md) and [Macro's decision](https://github.com/mastermindx-market-intelligence/macro/blob/3c8546e8aa56a0310e49fbcfba2c3debf84d8127/agentos/decisions/DEC-COMMERCIAL-DATA-RIGHTS-CHAIRMAN-ATTESTATION-20261023.md) already cover Massive/Polygon, Tiingo, ThetaData options, and the named Research Factory Yahoo/yfinance route including XLB/XLE/XLF/XLI/XLK/XLP/XLU/XLV/XLY. Do not request repeated approval, contract upload or public-terms reproof. The parent plan's older generic licence-unqualified wording is superseded for those named sources.

That recorded approval does not establish unmentioned GICS/EquityDesk/other reference-source rights, an authenticated current feed receipt, actual historical vintages, scientific validity or a retention implementation. Do not invent contract clauses, retention duration or new providers. Existing GMI source-local call-time usage checks remain canonical; a stored rights boolean is not an evergreen permission.

[Massive's full-market snapshot documentation](https://massive.com/docs/rest/stocks/snapshots/full-market-snapshot) describes daily reset/repopulation, plan-dependent delayed or real-time data, and no historical-snapshot plan history for this endpoint. [Its day-bar explanation](https://massive.com/knowledge-base/article/why-is-the-stocks-snapshots-day-bar-zero-before-the-open-and-how-do-i-get-the-pre-market-change) distinguishes regular-session day fields from premarket trade/minute information. The entitled feed's actual delay must remain visible; polling frequency does not remove source delay.

A latest JSON view or occasional Git snapshot is not evidence of a complete intraday observation archive. The existing retention owner must demonstrate retained original observations and receipts, correction lineage, membership and threshold revisions, deduplication, actual horizon/completeness, permitted fields/duration and reproducible replay before observed-history claims. A later vendor backfill may support a clearly labeled reconstruction, not an invented original observation. No archive is created here.

## Validation and review receipts

The baseline was staged from complete original source files with Git blob identity verification; no AST-extracted implementation or replacement core was used. Relevant baseline blobs:

- `engine/live_breadth.py`: `b3e6aa3eafd472148d9d8f87d1ecc4b068352b53`.
- `tests/test_live_breadth.py`: `5cddeaf9f3aed23054a6d6741e1f0b804385f987`.
- `engine/live_quotes.py`: `61b9ce7551b4e71b8897eac8f7c6a56f89e5b7f9`.
- `scripts/live_breadth_poller.py`: `a2708763252a0ae1c0e3b806a467077ed1e488a1`.

Baseline focused execution: **51 passed** with Python 3.12, pytest 9.2.0, real source imports and test-only dependencies. This focused isolated invocation uses `-c /dev/null` and disables plugin autoload; it is not full repository CI. Test responses are synthetic; no production feed was queried.

Fabric root: `breadth-intelligence-research-engineering-20261030-c3`. Builder run: `breadth-quote-qualification-builder-20261030-01`, patch-proposal-only leaf, with no source-write/push authority. Its result, candidate execution and separate independent review must be recorded in the exact-head PR/handoff before acceptance. No review or implementation completion is inferred from a launch acknowledgement.

## Chris's reserved continuation

1. Consume the reviewed immutable source PR and reconcile it with #10212; correct that PR's new-suite CI registration and superseded commercial-rights wording through its own source custody.
2. Separately commission producer integration: preserve per-member evidence at the existing parser seam, invoke qualification, and demonstrate the stale/synthetic counterexamples no longer pass the integrated path. Keep coverage, delay and fallback truthful.
3. Qualify prior-completed-session thresholds, compatible price basis, correction invalidation, PIT cohort/version joins and source-local usage rights before claiming measured historical group breadth.
4. Establish the existing retention path's actual replay evidence before intraday-history/time-travel claims. Coordinate Paper/product work with the DESIGN session. Independent review, CI and real-path product acceptance remain separate receipts.

The capability gained by this slice is a tested, inspectable input qualifier for an existing backend consumer. It does not complete the master plan's broader DONE_WHEN contract.
