# Exposure Outlook R1 — source-readiness consumer and build checkpoint

## Commission and approved experience

MAS-260, child of MAS-160 in existing Market OS / Options Intelligence.
Operation: `options-exposure-outlook-20260918-sol-001`.

On September 18 the Chairman approved one forecasting capability with a detailed view inside
Options -> GEX and a synchronized, optional main-chart overlay, then explicitly instructed Sol
to initiate the build. This approval supersedes the initial document's architectural-approval
question; do not ask again. It does not authorize trades, new data purchases, another options
owner/store/collector, or taking over the broader Options integration amendment.

Source law for this build: protected Mastermind
`61a2ff79aba4e8a5685e779707ad5c4426cf5cc5`, Skillpack 1.0.1/bootstrap major 1, including
INDEX, COLD_START, ACTIVE_EXECUTION, WEB_CEO_DELEGATION, COMMISSION_WAVE and CLOSEOUT.
Source worktree base: Macro `d3578d8d55e721fd003180a422f5c3e3ee4909e6`.
Carrier: `claude/mas260-exposure-baseline-20260918`, under macro-main/.claude/worktrees/.

## The capability in this source slice

An operator or research process can audit the actual options replay index and the existing
Terminal intraday response, receiving bounded, hash-attributed, machine-readable reasons why
those inputs can or cannot support later forecast research. This is a real consumer, not a
new schema waiting for a consumer. It writes only stdout. No production feed, feature flag,
forecast, event identity, calibration ledger, collector, price API or chart is changed.

- `engine/exposure_outlook_data.py`: follow only the declared root/session index; never glob
  old frame files or silently use current data in place of missing history. Verify frame
  identities, grids, spot validity and clock relationships; measure index and source-clock
  spacing separately. Bound each file and total session bytes. Missing optional charm does
  not invalidate a valid GEX grid. Publish exact per-file SHA-256 evidence and per-frame reasons.
- `engine/exposure_outlook_prices.py`: consume `terminal.intraday_source_evidence.v1`, verify
  OHLC shape, response/evidence identity and counts, decode the documented US market-local
  display epoch using the historical session's ET offset, and preserve unverified admission
  facts. It does not infer a full exchange calendar from a bar count.
- `engine/exposure_outlook_research.py`: command-line consumer of both readers. Only installed
  audit modes are exposed. Invalid input exits 2; a valid audit with negative findings exits 0.

`forecast_eligible` remains false in this audit-only wave. A consistent input is not a
qualified corpus or calibrated model. `source_integrity` is consistency against the forecast
reader's declared requirements, not a verdict that a display payload or its producer is broken.
A capture-label/source-asof difference can reflect distinct clock semantics; the source owner
must establish that meaning before a forecast uses it as a historical availability clock.

## Reproduction

From a checkout containing this slice:

```sh
python3 -m pytest tests/test_exposure_outlook_data.py tests/test_exposure_outlook_prices.py tests/test_exposure_outlook_audit_cli.py tests/test_gex_state.py -q
python3 -m engine.exposure_outlook_research audit-surface --surface-dir /path/to/surface --root SPY --session 2026-09-18 --as-of 2026-09-18T21:00:00Z --layout current
python3 -m engine.exposure_outlook_research audit-price --input /path/to/canonical-response.json --root SPY --session 2026-09-17 --as-of 2026-09-18T21:00:00Z
```

The `current` layout must be requested explicitly and still enforces the exact session in
its index. Default `dated` reads root/date/idx.json and never falls back. No network client or
credential is embedded in either reader. Source bytes are obtained through existing authorized
owners. These examples are research invocations, not permission to install into live M1 worktrees.

## Actual production-path observations

`EXPOSURE_OUTLOOK_SOURCE_READINESS_2026-09-18.json` is a real read-only execution receipt from
M1's existing local `live_flow_out/surface` staging, observed at
`2026-09-18T21:34:57.609290+00:00`. Reviewed reader SHA-256:
`52d98a11f17c77206af3664700a8d58d270c01f285fbb1ff71a8e712ad3d2bfc`.
The module was piped into a temporary Python process; no M1 source file, process configuration,
collector, schedule, or state was modified. Scope is local current staging, NOT R2 archive,
raw Theta parquets, live price health, or a general options-system acceptance.

For SPY, QQQ and IWM independently, the canonical current index selected 12 readable frames.
Configured cadence is 120 seconds. Index-label spacing is 24 minutes minimum, 37 minutes
median and 41 minutes maximum. Source-asof spacing differs: median 1,639.153539 seconds,
maximum 6,414.310848 seconds, and at least one non-advancing source clock. Each root has
nine frames with an unusable spot field and no explicit published_at in any of its 12 frames.
The GEX-grid check itself passed these frames; the nine INVALID_FRAME findings identify spot,
not bad gamma arithmetic. All of this is visible per frame in the receipt.

An earlier directory listing also contained an unindexed 1709.json from July 29. The reader
never used it. A same-day dated staging directory was absent; that does not prove the separate
R2 dated archive is absent. Ten retained sessions were declared by the current dates index.
Do not expand that retention into a fictional long intraday training history.

`EXPOSURE_OUTLOOK_PRICE_READINESS_2026-09-18.json` records an actual served Terminal request:
`/api/intraday?sym=SPY&tf=5m&date=2026-09-17`. It returned 78 bars, attributed by its owner to
live_tail. The documented display epochs correctly decode to 13:30 UTC open and 20:00 UTC
final-bar close. Treating those numbers directly as UTC would shift this US session by four
hours. The API itself marks point-in-time availability, instrument identity and price adjustment
not_verified, completeness not_assessed, and warns live_tail_construction_not_receipted.
A successful response and valid bars do not erase those explicit research limitations.

A separate bounded Theta stock-OHLC entitlement probe returned HTTP 403: the installed account
reported FREE stocks access where that endpoint requires a Value subscription. This says nothing
about the paid options source. The existing Theta daily-refresh manifest reported September-18
incremental completion, S=September-17, 369/375 AD-ready roots (0.984), and 372 complete T1 roots.
No upgrade or purchase was attempted. The Terminal's already-existing underlying-bar source is
an independent canonical source; no new provider or options fallback was created.

Public endpoint contract used for that entitlement probe:
https://docs.thetadata.us/operations/stock_history_ohlc.html
Terminal epoch/source contracts inspected: terminal/app/api/intraday/route.ts and
terminal/lib/intradayShared.ts in the canonical Terminal repository.

## Tests and rejected shortcuts

Initial missing-reader tests failed before implementation. Subsequent targeted regressions
were observed failing before their changes: explicit current-layout admission, optional metric
nulls, per-frame diagnostics, bounded total reads, and the CLI's price-response consumer.
Final pre-commit focused execution on the real Macro worktree: **134 passed** (55 new and
79 existing GEX-state tests). These are software-integrity tests, not forecast-performance data.

Do not: recycle pin_probability; call state persistence a cone-containment probability; train on
same-session future labels; backfill known_at from file mtime; manufacture a missing spot; infer
publication from a fresh index; mistake market-local display epochs for UTC; call this audit a
model qualification; restart or move M1's live poller; revive the old C0 hold; create a duplicate
Options owner or a second quote/Greek store.

## Deferred baseline and exact continuation

A price/volatility-only offline baseline prototype plus a CLI and adversarial tests was built in
the conversation's isolated artifact workspace. Its 62-test set passed there. It uses previous
sessions only, one time-selected donor per day, mature-outcome clocks, exact horizons, explicit
insufficient-data output, empirical quantiles and CRPS/day-balanced evaluation. No real-market
performance or calibration is claimed.

A platform block prevented its separate source-file transfer. Reconciliation on this same
worktree confirmed engine/exposure_outlook.py absent. It is NOT in this source slice; do not
claim it shipped or retry the blocked write blindly. The executable R1 CLI does not advertise
that absent component. The prototype is preserved separately as a research artifact, not current
repository authority. Reconcile source/permission state before any later incorporation.

Next critical path: finish independent review and exact-head CI for this read-only consumer;
then resolve the concrete corpus/availability and source-clock meanings with existing Options
and Terminal source owners. Qualify actual historical anchors before scoring the baseline;
only later compare GEX ablations and earned calibration. Full GEX UI, main-chart overlay,
immutable live forecasts and browser/export proof remain owed under the approved commission.

## Follow-up: numeric Greek grids are not proof of measured exposure

The same source review uncovered a material admission distinction in the existing producer.
`scripts/build_flow_surface.py::greek_columns_for_stamp` documents coverage against the union
of quoted strikes, not the full options chain. `append_stamp` retains Greek-grid keys once they
have appeared and pads a cycle without Greek contributions with numeric zeros. Thus valid
array dimensions and finite values do not prove that a cycle observed zero gamma.

Eight new regression cases first failed, then passed after the reader began preserving
`reported_greek_coverage` with `coverage_scope=quoted_strike_union_not_full_chain`, refusing
invalid/missing coverage and explicitly flagging zero contributing strikes. Positive partial
coverage is reported without inventing a full-chain denominator. The local prototype is still
separate; no baseline-file transfer was retried.

A separate real read at `2026-09-18T21:53:37.891862+00:00` is preserved in
`EXPOSURE_OUTLOOK_GREEK_COVERAGE_2026-09-18.json`, reader SHA-256
`65886a87b0138c7071879a19c927db4d968025e3ca4303c014be24e99f97b4ba`.
The earlier readiness receipt is retained unchanged under its original reader hash.
For each of SPY, QQQ and IWM, the same nine unusable-spot frames report zero Greek coverage;
only three of twelve frames have a positive contributing-strike fraction. Those three still
do not meet the unresolved availability/clock/corpus requirements. No producer or M1 runtime
was changed by this read or reader change.

Final focused source test after this addition: **142 passed** (63 new and 79 existing).
The original e4d6656344da119e3bb524bd889ff8ad439bd318 is the initial R1 head; current source
review must use the eventual pushed coverage-hardening successor on **the same PR #7328**.
Native GitHub review was requested from existing collaborator mastermindx-2; this is not a
worker START. GitHub CI was observed in progress on the initial head. The inactive-base
ci-authority/codex/merge-queue-pilot red is not a binding source failure: its check explicitly
reported context_active=false / inactive_base_context. HOLD remains until actual independent
review and exact-successor-head CI have completed; no auto-merge is armed.

## Approved continuation: CI enrollment and observed-outcome consumer

Current live Chairman continuation retains the approved hybrid design. This slice stays on
PR #7328 and adds observed price outcomes to the existing read-only research CLI, not the
blocked forecasting-baseline transfer. No probability, training, source-store or runtime writer.
Procedure pin: Mastermind@20dc89a201b9dfa65c2b6a2366072f45d885cb5c, compatible Skillpack 1.0.1.

- [x] Enroll the three existing suites in the options-data job in `.github/ci/legacy-jobs.yml`.
  Reproducer: contract-delta job 105774897691 names all three as unrun. No waiver or new job.
- [x] Add `engine/exposure_outlook_outcomes.py::label_price_outcomes(payload, *, root,
  session, origin, as_of, session_open, session_close, calendar_ref, barriers=None)`.
  The explicit session window comes from the caller's calendar owner; do not invent another
  early-close calendar. Reuse Terminal display-epoch decoding and source-evidence checks.
- [x] Tests in `tests/test_exposure_outlook_prices.py` first prove the module absent, then pin
  exact 30/60/90/120/close endpoints, no silent clipping, pending outcomes, missing anchors,
  per-horizon gap handling, same-bar first-touch ambiguity, touch versus exit, inclusive
  endpoint containment, missing barrier nulls, late-defined target refusal and identity checks.
  Example: a missing interior bar permits an observed endpoint return but never false
  path containment; high==upper touches the barrier without exiting the closed interval.
- [x] Add `label-price` to `engine/exposure_outlook_research.py`, wire explicit window/ref
  flags, and run its real subprocess from `tests/test_exposure_outlook_audit_cli.py`.
- [x] Run all four focused suites plus contract-delta; use actual served Terminal bars to
  produce a hash-attributed outcome receipt with research admission still unqualified.
- [ ] Commit/push this same carrier, obtain independent review and actual current-head CI;
  no self-review-as-independent, auto-merge, source restart or baseline-transfer retry.

The full feature is not complete at an outcome label, data receipt, test run, PR or merge.

## Continuation verification — September 18, 23:35 UTC

The existing R1 carrier now includes observed-outcome labeling, not the blocked baseline
forecast model. `label-price` is a real stdout-only CLI over existing Terminal responses.
It separates endpoint observations, complete supplied-bar paths, inclusive touches, strict
range exits, and unresolved first-touch order inside an OHLC bar. A missing interior candle
may leave an endpoint observed but cannot prove a barrier was never touched. Nothing here
proves full exchange-feed completeness, historical availability, or forecast calibration.

Verification: 162 focused tests passed (83 Exposure Outlook / 79 existing GEX-state tests).
The first 13 outcome tests failed before the module existed; the CLI and two adversarial
clock/first-touch cases failed before their implementation. The active suite has no new
skips or waivers. Two unimplemented optional calendar-default tests are separately retained
as a deferred specification, not reported as passing tests or an installed feature.

The original `contract-delta` failure named three unregistered pytest suites. All three now
run inside the existing options-data job. After materializing omitted source directories in
this worktree (not generated data/site), `python3 scripts/check_contract_delta.py --base
b9bd603745c6d5afa86a0183f4a12d196c7c8ad7` returned 0 introduced / 0 inherited. The manifest
is a CI-authority path; this is enrollment, not a gate exemption. Current-head hosted proof
and independent review are still required; no auto-merge or protection change is implied.

`EXPOSURE_OUTLOOK_OBSERVED_OUTCOMES_2026-09-18.json` records the actual served SPY response
for September 17, 78 five-minute bars, origin 18:00 UTC. The CLI observed exact 30/60/90/120/
close endpoints. The caller used existing `lib.nyse_calendar.is_session` and
`engine.session_digest.session_window_et` and supplied their explicit window. No barriers
were retrospectively selected for this real-input receipt. Source hashes and original
research-admission limitations travel with it. These are observations, not forecast scores.

### Additional measured source boundaries

The actual M1 SPY 2026 Theta parquet metadata shows 2,352,602 EOD rows, 2,352,602 Greek
rows and 2,297,761 OI rows. Their clocks are date-level; last inspected EOD/Greek dates
were September 17 and OI September 18. No per-row intraday availability/method-version
field appears in the inspected schemas. This is substantial EOD history, not proof of a
minute-level historical exposure corpus. Only metadata and bounded clock samples were read;
no store, producer, schedule, subscription or credentials were modified.

The served `surface_dates:SPY` request returned HTTP 403 / `pro_required`. This session did
not inspect the authenticated R2 archive through that product endpoint and did not fetch a
public bucket URL to evade it. Archive coverage remains unknown, not absent. The existing
canonical ArchiveReader is an available code seam; an authenticated read still needs its
proper principal/context and no duplicate archive reader or source system was created.

The optional automatic-calendar-default source patch was platform-blocked before execution.
Same-worktree reconciliation confirmed no effect. The implemented explicit-window API is
unchanged; the two draft default tests are preserved in the named deferred specification.
The prior forecasting-baseline transfer remains separately blocked/absent. No blocked write
was retried through another path, actor or renamed implementation. Further source writes
outside those exact blocked operations continued on the original allowed R1 carrier.

### Historical Greek request feasibility resolved for the bounded probe

The existing M1 Theta service returned HTTP 200 for both requested methodology versions
on a SPY 762 call expiring September 17, 15:45-15:55, interval=5m. Three matched timestamps
had matching quote/underlying inputs and method-dependent delta, gamma, IV and charm.
The metadata-only feasibility receipt records parameters, observation clocks and response
hashes. This materially supersedes using the July interval-rejection observation as a
current blocker. The adapter remains EOD-only in this PR; full capture, historical
availability, rate/dividend conventions and immutable version/build provenance remain
to be qualified through the existing Theta owner. A mutable latest label is not an
immutable model version. No raw vendor quote corpus was committed.
