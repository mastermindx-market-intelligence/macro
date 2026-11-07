# SPX session mechanics: source admission and clock-retention return

This is the S1 source qualification return for the October 8 execution commission,
under `WS:ADVANCED-DATA-OPTIONS`. It supports the single integration carrier
Macro #8684, `claude/spx-session-mechanics-20261008`; it is not a second programme
or a source-admission authority. **S1 remains partial: parser evidence improves,
but no current raw SPX/SPXW book, captured consumer availability, or licensed
participant-labelled panel was admitted by this work.** F1 (15-minute excursions),
F2 (remaining-session extremes), and F3 (close) remain separately NOT_EVALUATED.
Descriptive mechanics can advance while those empirical gates remain closed.

## Identity and custody

- Root: `01a11ee7-d9fe-71f1-b582-193891266722`; source lane:
  `01a11eed-84cf-75e1-af19-fec04c4e4d5e`.
- Current procedure: Mastermind protected `master`
  `ad362ef45def043ee5970c2b131be9825fcea1ae`, Skillpack 1.0.1/bootstrap 1;
  INDEX, ACTIVE_EXECUTION, SESSION_RELIABILITY and delegation rules read at that pin.
- Source-repair base: Macro `4c23c2a0a397be7ecb764e39fbe9f7bf169da8d7`,
  fast-forwarded from `4fd2d0e2b2fb0eeb5d98222e01c4a8b36d9e9396` in the
  existing protected external-SSD worktree. Source lane branch:
  `claude/spx-source-admission-20261009-a44e`.
- Commission markdown SHA-256:
  `2ab447c172db12a996755fdeb9a950c344bf33fe181bafd263dc3b37a55cdf08`.
- #8555 stays `HOLD-FOR-SOL / DO NOT MERGE`, draft head
  `82bc91ba18684f4a2c7f7f83ffd0c8d2a80625a6`. Its research is reference input.
- MAS-260 #7328 remote head is `9515f2558a006c913a7c0eb30d966c47fa1a143b`;
  retained local Macro head `b281fe529717656e070abaa15651c75fb74bf93f` contains
  the later calibration lane. Terminal consumer head
  `be92323426d9971ebd881ce3df6c529f182dc22d` and the original dirty Terminal
  checkout are preserved. No squash-merged or held carrier was overwritten.
- October 3 B1/B2 mechanics, B3/B5 source-admission reference and repair briefs
  are reused. #8201 was freshly checked: MERGED October 4, head
  `481c059818de0e48895c5f38c29ca99c2bf44891`. Its five `source_event_*`
  Flow-history diagnostics and verified FS5 receipt namespace are separate from
  the Greek parser omission repaired here. No Flow ledger repair is duplicated.

## Contract and availability matrix

| Input / existing owner | Evidence and present limit | Required admission evidence |
|---|---|---|
| SPX/SPXW reference | Theta root names plus official Cboe specs distinguish normal AM SPX from PM SPXW; both European cash-settled index options, multiplier 100. Root and expiration alone do not prove the exact last-trade/fixing calendar. | Exact series reference, multiplier, settlement style/fixing instant, trading calendar/early closes, and retained reference revision per contract. Do not collapse AM/PM by calendar date. |
| Historical EOD Greeks: `collectors/thetadata.py::bulk_greeks` | Existing parser derives `date` and previously discarded raw `timestamp` and `underlying_timestamp`. Repair retains them only when supplied, without inventing receipt/availability. Vendor history is reconstructed evidence unless original receipts prove otherwise. | Raw bytes/schema/parameter version, Greek model/rate/dividend/IV/TTE conventions, distinct underlying observation and actual acquisition/publication/consumer clocks. |
| Snapshot Greeks: same collector and `scripts/chain_snapshot_poller.py` | Existing parsed `snapshot_ts` retained; raw quote/underlying clock evidence added. Snapshot bid/ask is explicitly `vendor_snapshot_bid_ask`, not qualified NBBO/current/live/executable. Poller joins second-order Greeks on contract plus exact quote timestamp; this does not independently qualify underlying-clock agreement. | Natural source sample; clocks for each Greek leg and underlying; source age/clock uncertainty; eligible quote/underlying matching and complete-book coverage. Raw string retention alone passes none of these. |
| OI: `engine/thetadata_store.py` and snapshot owner | `oi_for_date` selects contract, effective date and OI. `chain` joins same-date raw OI; `doi_series` owns its prior-session signal rule. Effective position date is not first-known availability. Unsigned OI is not dealer inventory. | Effective OI session plus source publication, receipt and first consumer availability. Prior-session OI baseline must state its sign assumptions. |
| Public Flow: existing `bulk_trade_quote`, `engine/live_flow.py`, Flow stage/history | Active trade parser already retains exact sequence/size integers and raw quote/trade condition and venue fields. The private unused normalizer is not the production parser and was not rewritten. Published notable events are coalesced and capped at 2,000, not an atomic full-market tape. | Feed-specific sequence/correction/cancel law; quote chronology/age/condition eligibility; package ambiguity; source-valid denominators; signing abstentions and coverage. A sequence maximum is not a correction ledger or dealer/open-close label. |
| Existing Flow history #8201 / FS5 | Diagnostic source clocks do not populate verified stage receipts. Keep-first history and existing stage/publication owners remain authoritative. | Exact immutable event/artifact, stage availability and consumer receipt. No retrospective restamp/backfill may manufacture captured-PIT eligibility. |
| ES: futures Data OS, Macro #8451 | Existing futures-tape owner, not a new collector. LSE ES.F is a vendor continuous secondary research feed with unresolved roll semantics. No current accepted ES contract tape or market-depth sample was obtained here. | Contract identity, venue/feed entitlement, price/size units, exchange/event/receipt clocks, sessions/rolls, and exact SPX-to-ES basis/hedge mapping. Unsupported ES coverage stays unavailable. |
| Participant-informed C/D comparisons | No entitled Cboe participant-labelled dataset or current sample was found. Public vendor descriptions do not establish account entitlement or live availability. | Legally available labelled input, venue/universe coverage, delivery delay, opening/closing and participant semantics, exact revision and separate research protocol. No purchase or inferred label substitution. |

Official references checked October 9 UTC:
[Theta symbology](https://thetadata.net/docs/Articles/Data-And-Requests/Symbology.html),
[Cboe SPX fact sheet](https://cdn.cboe.com/resources/spx/spx-fact-sheet.pdf),
[Theta historical Greeks](https://thetadata.net/docs/operations/option_history_greeks_all.html).
Theta's documented latest historical calculation uses actual time-to-expiration
with a minimum of one hour; version 1 uses fixed 0.15 DTE. Therefore those vendor
Greeks cannot by themselves validate exact final-hour repricing. The admitted
pricing owner and the exact contract clock must determine that model boundary.

## Implemented source delta

`collectors/thetadata.py` retains optional raw `timestamp` and
`underlying_timestamp` in historical and snapshot Greek frames. Existing parsed
`date`/`snapshot_ts`, numeric Greeks, root mapping and legacy column order remain.
Missing clocks stay absent; null/malformed/offset-bearing underlying clocks remain
raw evidence. No wall clock, timezone assumption, availability or freshness flag
is added. Exact duplicate rows still collapse; clock-distinct source observations
survive.

The incumbent `engine/thetadata_store.py::_load_parquets` stores/caches all raw
Greek vintages. Its default legacy Greek view excludes the two newly retained
clocks and deduplicates the resulting economic projection, so existing surface,
VEX, hub and aggregate readers retain their earlier cardinality. Provenance
readers can explicitly request `retain_source_clocks=True`; reading either view
cannot alter the cached or persisted source. This is a view option on the existing
store, not a new store or an intraday-admission claim.

The legacy `engine/thetadata_store.py::chain` consumer additionally projects source clocks out
of its date-key Greek join. It must collapse identical projected economic rows
before joining, so extra clock-only vintages cannot multiply OI or volume. This
does not choose the latest source vintage or qualify this legacy date view for
intraday/PIT use. Raw source frames remain intact; genuinely different economic
values are not reconciled by inventing an ordering policy.

No new collector, Greek calculator, endpoint, scheduler, source store, ledger,
forecast lifecycle or production process was created. This code has not been
installed in the source service. Historic files are not rewritten by the change.

## Actual retained receipts and present access

1. The local canonical source resolver returned `None` for
   `resolve_thetadata_store(required=False, purpose='spx-source-admission-read-only')`.
   No local source substitute was created. This establishes local availability,
   not that the original historical data never existed.
2. One bounded read-only SSH invocation to incumbent `m1`, with BatchMode and a
   five-second connect timeout, exited **255**, `exec request failed on channel 0`.
   `ssh -G m1` showed no multiplexed control session. One authorized fleet inventory
   reported `m1studio` offline, last seen approximately 57 hours earlier. No remote
   source read executed, service was restarted, or lease overridden. Access must
   recover through the incumbent host/service owner; this is transport/host
   unavailability, not a vendor entitlement denial.
3. Retained October 4 source-install adoption receipt SHA-256
   `dad45e1a08a6455d11b8049cee4bf9c2b38e71b52ccc0b07df09ed3e4c9a5dad`
   identifies historical live-flow and matrix installation receipts. It is not a
   new October 9 observation or proof of current service health.
4. Retained Flow enrichment adoption receipt SHA-256
   `97d442d76e46746998a45610e89d1ee8e8d091669f143055f11620fffce07fc5`
   records matching local/R2 payload hash
   `8eabd08b10aa0fa437e9c2afe3f6131f0619a04f6ff933d1a1fbc0ad9686b1d9`.
   Its `built_at=2026-10-03T23:47:41.724556Z` and R2 publication do **not** make
   `source_asof=2026-09-25T20:09:25.764815Z` fresh. It contains 2,000 selected
   events, not a full current SPX options tape. Both receipt files are retained
   under `/Volumes/Mastermind/evidence/fable-options-20261003-01a10340/`.
5. Committed aggregate artifacts at Macro `4fd2d0e2` were inspected:
   `site/gex/SPX.json`, SHA-256
   `f99d1d98b8a6be9862b7e8775d4c748e7859f528b7d77f2a9b448141f18800c3`,
   and `site/options_structure/gex_state/SPX.json`, SHA-256
   `7723ec6c6d17ff498aba2edbd0d319caa27db55f7d776d66b217cc573f527b65`.
   The latter's October 8 16:00 ET as-of label is aggregate source evidence,
   not raw per-contract admission or live SSE/one-minute history. Legacy heuristic
   probability-labelled fields are not calibrated probabilities for this product.
6. Fresh browser observation on October 9 around 05:45 UTC:
   `https://app.mastermind-x.com/options` in the existing Chrome profile was
   signed in (the Account panel confirmed an existing Google sign-in), but the
   page displayed **Unlock the Options desk**, requiring Essential or Pro.
   The incumbent audit tab was preserved; this check used a separate tab in the
   same profile. No trial, subscription change, account switch or protected API
   bypass was attempted. This is an authenticated entitlement boundary, not
   proof of the Options contents. Non-account screenshot:
   `options-entitlement-gate-20261009.jpg`, SHA-256
   `c3f05ea3dbcc086db357578c3e4445f247cfb3eeba80e3c8a79c6a3eb1b4156a`,
   retained under
   `/Volumes/Mastermind/evidence/spx-session-mechanics-01a11ee7/source-admission/`.
   Natural source-to-browser acceptance needs the ordinary entitled user path;
   passing source tests cannot substitute for that path.

## Rights and source-specific ceilings

The canonical [Theta entitlement record](../licenses/THETADATA_ENTITLEMENT_RECORD.md)
confirms the operator's private/professional subscription, Full Trade Stream and
prior display/redistribution rights. It is incorrect to describe all Theta usage
as unlicensed. The same record leaves the specific full-universe intraday-derived
Terminal panel scope subject to the existing prepublish check. Generic
[subscriber terms](https://www.thetadata.net/subscriber-agreement) cannot resolve
or override a privately agreed addendum. Keep confidential contractual material
private; no agreement text is added here. Preserve customer-facing debranding.

The canonical [Massive entitlement record](../licenses/MASSIVE_ENTITLEMENT_RECORD.md)
establishes broad stock-data rights, including derived and ML uses; it does not
establish a Futures-specific subscription. Existing Macro #8451 source/entitlement
qualification remains the ES route. Optional participant-informed evidence remains
unavailable pending actual lawful access and temporal qualification.

## Validation and acceptance boundary

Validation on this source candidate:

- Initial regressions reproduced lost clock vintages (two failures, exit 1),
  then passed all 24 parser cases (exit 0). A separate chain counterexample
  reproduced one position becoming three solely because of clock-only vintages
  (one failure, exit 1), before the compatibility repair.
- `python3 -m pytest tests/test_thetadata.py tests/test_thetadata_store.py tests/test_chain_snapshot_poller.py -q --disable-warnings --maxfail=3`
  passed **315 tests**, exit **0**, on the first parser/chain repair. This preceded
  the broader loader compatibility projection and does not replace its testing.
- Final production-source compatibility command:
  `python3 -m pytest tests/test_thetadata.py tests/test_thetadata_store.py tests/test_chain_snapshot_poller.py tests/test_options_surface.py tests/test_vex_engine.py tests/test_options_hub.py tests/test_options_matrix.py tests/test_topup_thetadata_daily.py -q --disable-warnings --maxfail=3`
  returned **559 passed, 1 failed**, exit **1**. The sole failure opened a deleted,
  hard-coded author worktree in `test_f15_writer_lock_gitignored`. The assertion
  now resolves the current repository's `.gitignore` using its existing
  `REPO_ROOT`; no product code changed after this run.
- `python3 -m pytest tests/test_topup_thetadata_daily.py::test_f15_writer_lock_gitignored -q --disable-warnings`
  then passed **1 test**, exit **0**. Thus all 560 selected cases have passing
  evidence across those two commands; there was no fabricated single green
  560-case run. `git diff --check` on all changed source/test paths exited **0**.
- New tests exercise actual collector entry points and the existing daily/snapshot
  writers through temporary parquet storage, raw/default read order, clock-only
  cardinality and preservation of different economic rows. Test data is synthetic;
  only temporary test stores are written.
- Separate integration-parent review passed **22 independent adversarial checks**,
  exit **0**, with no blocking findings. Scope includes mixed old/new parquet
  schemas, raw/legacy read order, cache mutation isolation, unchanged persisted
  bytes, malformed-clock evidence, retained economic differences and non-Greek
  invariance. Reviewed SHA-256 values: collector
  `41bb8778ffc4996eeb2a12e1e7cc53d985acf3a95af94cb44bdf489489c8f5cd`,
  store `683b57802527aa3375787e8a269bb4f00ac80ae6b2c7dbdcc32330c2c970ead6`.
  Receipt: `/Volumes/Mastermind/evidence/spx-session-mechanics-01a11ee7/source-clock-parent-review.json`.
  This is independent principal source review, not a Fabric execution, GitHub
  approval, mechanics review, release approval or market-source admission.

The source-admission research self-test/mutation suite also ran:
`python3 research/options_intelligence/2026-10-03/source-admission-reference.py --self-test --mutation-check`
exited **0**, 73 cases passed, 10 mutants killed, zero survivors and zero
post-mutation failures. These are synthetic contract checks, not source certification.

The Fabric request `spx-source-contract-census-20261009-a44e`, original root retained,
was routed by the approved stable-handle adapter and failed before provider START:
`SUPPORT_POLICY_STALE_ACTIVE_REFUSED`, `SUPPORT_PUBLICATION_REFUSED`, `SCP_FAILED rc=75`.
Exact-ID status is `TERMINAL_FAILURE`, `prelaunch_failure`, no result available.
No worker result or independent approval is claimed; no alternate host/provider
was used to bypass that refusal. The visible Executive service was read-only.
The parent performed the bounded repair for the concrete no-eligible-pre-effect-
worker / critical-path reason. The separate source review above subsequently
closed its bounded source-review gate; protected CI and release remain separate.

Preserve the MAS-260 calibration null result at retained `b281fe5297`:
`EXPOSURE_OUTLOOK_CALIBRATION_REPLAY_2026-09-21.json`,
`EXPOSURE_OUTLOOK_CROSS_INSTRUMENT_ABLATION_2026-09-21.json`, and
`DSC:EXPOSURE-OUTLOOK-INTERVAL-ADJUSTMENT-FAILS-PROPER-SCORE-GATE`.
Neither earlier negative GEX forecasting results nor failed interval challengers
are replaced by passing mechanics tests. `can_publish` and `r2_published` remain
false in that lane. No fitting, probabilities, Prophet ranking or trading is enabled.

Next: consume the exact source repair and scoped review into #8684;
continue disjoint Terminal/scenario work through its existing writer; then obtain
one natural qualified SPX/SPXW source-to-consumer sample on the recovered incumbent
service. S1 needs clock/contract/rights qualification, S3 needs honest episode counts,
frozen outcomes and separate held-out F1/F2/F3 verdicts, and S5 needs transport/API/
authenticated browser proof. This document alone satisfies none of those final gates.
