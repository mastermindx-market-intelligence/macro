# ROR-1 — risk-awareness incident research (2026-10-15)

**Scope:** characterizing the issued Risk Radar ledger and source-native replay/live
gate behavior. This is **not** a newly validated forecast, production warning
publisher, market-risk score, trading policy, alert delivery mechanism or episode
authority. Research home: [Mastermind #1478](https://github.com/mastermindx-market-intelligence/Mastermind/issues/1478).

## Reproduce

From an eligible Macro repository checkout with installed pandas/numpy:

```bash
python3 -m unittest discover -s research/grey_deer/ror1_risk_attention_20261015 -p 'test_*.py' -v
python3 research/grey_deer/ror1_risk_attention_20261015/audit_suppressed_risk.py --jsonl data/risk_radar/forward_log.jsonl
```

`test_native_risk_radar_gate_parity.py` intentionally CHARACTERIZES the
current divergence between `context_gate_series` and `context_gate_live`.
Those tests assert the documented defect exists; on repair, invert/replace them
with parity assertions and regrade every affected historical population.
Use `ROR1_MACRO_ROOT=/absolute/eligible/macro-root` only when executing these
research tests outside their repository tree. No source/live flags are changed.

## Evidence and exact source

- Research base Macro main: `9df20a3ac37d1f33d616d871abfd9857f8cd5d26`.
- Issued-ledger source observed at `8d272434f222d6736a09e757a339444c8ef56c46`, matching later base blob.
- `data/risk_radar/forward_log.jsonl` Git blob `4d8c65e711db560c24088bc6380eaecd07db2afd`, SHA256 `240c202431cc160ca8ec53ec65125c2f9d858597bea60e416a91f01dea55017d`, 66 records spanning June23–Oct13.
- Native `engine/risk_radar.py` Git blob `94222d44ec102e728da5443e2082da73ad29f17f`, SHA256 `31668c7fe097cdf631edb6cca6e77990b40afdb3d4cb37d27596336689afe70d`.
- First suppressed source session Sep24, recorded issuance Sep25 05:17:05 UTC; last source session Oct13, issuance Oct14 06:02:59 UTC.
- 13 of 13 prospective recorded rows published Caution/no alert while `state_ungated` was Elevated (3) or Risk-off (10); **none was graded**. 48 older rows have nonnull outcome grades, which do not validate the 13 current readings.
- The 13 rows are consecutive *recorded observations*, **not confirmed every NYSE trading session**. Early-warning effectiveness, provenance, independence and customer delivery remain open.

The isolated M2 research root first demonstrated RED against a stub, then
**8/8** ledger-audit tests and **5/5** native-source characterization tests
passed. The portable native test variant also passed 5/5 against the exact
read-only imported source. This evidence establishes functional semantics,
not forecast precision or deployed behavior.

## Metric-name discrepancy in existing tuning research

`METRIC_DEFINITION_FINDING_20261015.md` reproduces a historical report
mismatch: `research/RISK_RADAR_TUNING.md` labels four values
0.915/0.751/0.901/0.741 as false-positive rates despite their exact
identity with `1 − precision` (false-discovery rates). Using the
full-history report's rounded 17% fire-rate, precision .249, and
its H21/5%-event upper bound .1890 for H21/8%-events, ordinary
false-positive rate is bounded approximately .12767–.15742 **if**
those figures have matching eligible populations. Recover original
TP/FP/TN/FN and episode counts before using any derived cost budget.

Pure `metric_definition_audit.py` and `test_metric_definition_audit.py`
were RED-then-GREEN 4/4 locally. No historical numerical model was rerun.

## Related true owners and release constraints

Grey Deer #8132 owns a different held candidate for warning projection and
native banner wiring. Macro #9428 owns a separate held incident-response
candidate and active review; neither is superseded by this research branch.
Source publication, hosted CI, technical review, merge, installation and
authenticated browser/notification acceptance are distinct steps.

**No arbitrary gate removal.** The prior context gate was meant to control
false-positive alerts. A prospective ungated severe run across 13 recorded
observations creates alert-fatigue risk if blindly promoted. Study episode-
level factual attention and data-health disclosures separately from future
SPY drawdown forecasts and all capital sizing/selection authority.

## October 14 published artifact consistency — real pinned observations

The separate offline audit compares five committed Macro artifacts from
`1b12af09222df183ac61ed5bcabb1ecc6bf5c735`. A minimized
`evidence/artifact_boundary_inputs_20261015.json` preserves their exact
Git blob references and only fields required for this question.
`evidence/artifact_boundary_findings_20261015.json` is the deterministic
result. It does NOT establish what an authenticated subscriber saw.

Reproduce without network, credentials, a source writer or new alerts:

```bash
python3 research/grey_deer/ror1_risk_attention_20261015/audit_artifact_consistency.py \
  --bundle research/grey_deer/ror1_risk_attention_20261015/evidence/artifact_boundary_inputs_20261015.json
python3 -m unittest discover -s research/grey_deer/ror1_risk_attention_20261015 -p 'test_artifact_consistency.py' -v
```

Read-only source comparison found five distinct observations:

1. Site Risk Envelope for October 14 includes **FRESH native Leadership
   Crack `CRACKING`** and `dislocation=true`, but its hazard stage is null
   with reason `required_source_state_unmapped`. This is a **confirmed
   artifact-local mapping drop**, not an assertion of systemic contagion.
2. Site Risk Envelope is October 14 while `data/risk_envelope/latest.json`
   remains October 13. They were generated at different times; this is a
   **publication variant mismatch**, not by itself a pipeline error.
3. The persisted `data/leadership_crack/latest.json` is October 8 `INTACT`
   but site envelope contains October 14 `CRACKING`; reconstruct exact
   source/vintage lineage before deciding how consumers bind to each variant.
4. Context-only Neural Web plane reads 50/Mixed under an October 14 date
   while measured October 14 Market State is 44/Mixed. Production clocks
   differ; do not claim the older model was false when it was produced.
5. Market State explicitly reports four stale input families despite its
   October 14 score. These require a user-facing data-quality qualifier.

**Original owner already has the mapping fix:** existing Macro Draft #9428
includes `CRACKING → FRAGILE` in its held source head; do not create
or merge a competing adapter. The permitted descriptive stage is
`FRAGILE`, not `TRANSMITTING` or `BREAKDOWN` without competent evidence.
Existing alternate producer/consumer and read-permission holds still apply.

**Verification:** ten tests passed after test-first RED; the pinned bundle
replays to the exact same JSON findings receipt hash
`429605fc52fba14f63253416674f8ba5abfb5d97db89b6939e222d962a3cf979`.
No original source artifacts were edited and no production service was invoked.

## Source-native verdict date lost in Neural Web compact export

Sixth independently read original source:
`data/neuralweb/world_state.json`, Git blob
`5a79f3a14b90bad891d0fdba808c5176ea9fe51d` at the same
Macro main observation. Its verdict is **50/MIXED as of October 13**
(`world_state.verdict.asof`), while world-state `produced_at` is
October 14 19:32:19Z. The compact plane uses
`build_market_plane() -> _asof_of(world_state)`, which falls back to
the **processing timestamp** because world_state has no top-level
`asof`/`as_of`, so the plane labels itself October 14. Its verdict
projection copies label/score but not native verdict `asof`.
Top-level plane `stale=false` is a separate world-state freshness
decision; it does not certify the verdict's native session.

This is a **confirmed provenance-field omission**, not proof that the
October 13 reading was stale at 15:35 ET before the October 14 close.
The safest consumer-compatible response is to retain a typed native
verdict source session and input-health qualifier **additively** in
the existing plane projection, without treating `produced_at` as
the observed market session, recomputing risk, or changing forecast
and capital permissions. Route eventual code changes to the existing
Neural Web owner with current source custody and consumer tests.

Accepted five-source inputs/receipt remain immutable. Additive
`evidence/plane_provenance_inputs_20261015.json` and
`evidence/plane_provenance_findings_20261015.json` preserve the six-source
same-pin view. Its full ledger consists of the previous five qualified
artifact findings **plus** `VERDICT_SOURCE_SESSION_LOST`.
The new receipt SHA256 is
`2e842e286f19e2b11303670b878434f7b8eb2c4d05b3a39f7f1839c96d6c8a25`.
Two new test-first cases prove date-loss detection and no-false-finding
when native source session survives the plane projection.

Reproduce with the same `audit_artifact_consistency.py --bundle`
command above, pointing at the new `plane_provenance_inputs` file.

## Country Radar issuance and Chronicle gap

The October 15 cross-market census now has three additive artifacts:

- `COUNTRY_WARNING_INPUT_RECEIPT_20261015.json` and
  `COUNTRY_WARNING_SOURCE_RECONCILIATION_20261015.md`: exact nonmatching
  country source paths for held #8132 (CN missing native Radar; HK and CA
  strict-invalid JSON and missing native Radar), while separate CN/HK
  measured Market States still show Risk-off through October 15.
- `COUNTRY_NATIVE_ISSUED_LEDGER_RECEIPT_20261015.json` and
  `COUNTRY_NATIVE_ISSUED_LEDGER_FINDINGS_20261015.md`: actual native
  source-forward records show Oct13 China Risk-off/98 and HK Elevated/90,
  both model `alert=true`, **not** delivered notifications. China remains
  Risk-off/97 through Oct15; HK Radar later Caution/81 while HK measured
  State remains Risk-off/32. Original ledger source IDs are pinned.
- `COUNTRY_SOURCE_ALERT_FATIGUE_RECEIPT_20261015.json`: model
  `alert=true` appears on 26/42 CN and 14/47 HK recorded source rows.
  Since Sep23 it is 9/9 CN and 11/14 HK. The longest contiguous
  **recorded row** runs are 18 CN and 11 HK. No per-trading-session,
  independent-event, false-positive or user-delivery claim follows.
- `COUNTRY_EPISODE_CHRONICLE_GAP_20261015.md`: the *existing*
  Chronicle `risk_band` adapter currently reads **US-only**
  `data/risk_radar/forward_log.jsonl`. Its `REBUILD_SOURCES` and
  event schema do not cover CN/HK/CA Radar logs. The architecture
  assigns durable regional episodes to Chronicle/Reflexes/QLedger
  but the country adapter is **not implemented**. Extend original
  source/manifest/episode owners; do not create a second event store.

Source owner #8132 was informed via issue comments 6198645125 and
6198842106. Strict JSON, native observation/market dates, consumer
entitlement, all existing HOLDs and score/trading authority remain
unmodified. Nothing in this research PR ships a new warning.

## Retrospective issue-time and original Git-vintage confirmation

- `audit_radar_issue_timeline.py` and `test_radar_issue_timeline.py`: **16/16**
  focused synthetic TDD tests (first RED, then GREEN). Strict original
  source/market/clock/JSON validation, issue-time cutoff, observed-run
  diagnostics and post-hoc weekday frequency controls. No user
  notification, live engine, Chronicle append or trade authority.
- `evidence/issue_timeline_sources_20261015.json`: four original
  source blob IDs against Macro main `9b255a5377385a6b0dab23850e6a6ff67714a5f1`.
  **The Git source blobs are already held in the original Macro
  `data/risk_radar*/` paths; do not copy them into this PR.**
- `evidence/issue_time_compact_receipt_20261015.json`: five fixed UTC
  cutoff snapshots plus one exploratory Sept1–Oct13 weekday 17:00Z
  exposure grid. Full local raw output SHA256
  `8ac614b7b4e1dc190b9b7b5577fec53118f4141ed9c910a774088a4ff663ae4a`.
  The source-date/issue-cutoff proxy is not a verified historical
  Git-vintage replay or a forecast backtest by itself.
- `OCT13_PRE_SELLOFF_GIT_VINTAGE_RECEIPT_20261015.json` provides the
  missing **actual original Git-vintage proof**: Main commit
  `c49e4410492e8d2a0a16d00eca5edb3b45d66bc7` on Oct13
  **16:32:31Z**, parent `a6f7b49003d1ffd7e68e07d98e068d864f6f4867`,
  already contained CN native `risk-off/98`, HK `elevated/90`,
  CN measured `34/RISK_OFF` and HK measured `33/RISK_OFF`, while the
  US native latest was Oct12 `caution/70.3`. CN/HK/US source rows
  are field-identical to the later pinned archived copies.
  The original committed site/china.html and site/hk.html were changed
  by the same commit; **origin/CDN/entitled rendering are unproven**.

Recreate the source-only cutoff experiment on a separate, clean
**read-only research workspace**, after retrieving the already
registered four Git source files at the exact pinned revision and naming
them according to `issue_timeline_sources_20261015.json`:

```bash
python3 research/grey_deer/ror1_risk_attention_20261015/audit_radar_issue_timeline.py \
  --source-dir /trusted/research/source_snapshot \
  --expected-source-blobs research/grey_deer/ror1_risk_attention_20261015/evidence/issue_timeline_sources_20261015.json \
  --output /trusted/research/new-unique-report.json \
  --cutoff 2026-10-13T17:00:00Z \
  --weekday-grid-start 2026-09-01 --weekday-grid-end 2026-10-13 \
  --weekday-grid-hour-utc 17 --weekday-grid-joint cn,hk
python3 -m unittest discover -s research/grey_deer/ror1_risk_attention_20261015 -p 'test_radar_issue_timeline.py' -q
```

At Oct13 17Z, the latest *recorded* CN and HK alerts were true,
but the U.S. latest was still its Oct12 Caution; do not replace it
with a future U.S. daily close. Dual country model alerts were true
at **14/31** exploratory 17Z sampled weekdays Sept1–Oct13, mostly
as a continuing exposure, **not** a unique Oct14 forecast.
No independent exchange calendar, authentic served byte or real
user-notification acknowledgment was established.

## Oct13 exact-site source comparison (Git tree, NOT production browser)

The prior Git-vintage receipt is complemented by
`OCT13_GLANCE_SOURCE_CONTRAST_20261015.json` (exact source
commit `c49e4410492e8d2a0a16d00eca5edb3b45d66bc7`):

- `site/china.html` blob `9254db12acf4f9d3ed7571595669fda0f678400f`
  has a red first-glance Market State hero with ARIA `Risk-off — 34`;
- `site/hk.html` blob `73c3e20d63bf105692010d760196c2f61b4a4c97`
  has a red first-glance hero with ARIA `Risk-off — score 33`;
- `site/macro.html` blob `217a4a1a542c11e795285f6d0d9966c49f70874e`
  retains a yellow Mixed/transition hero, ARIA `Mixed — score 50`;
- `site/index.html` blob `3e7ce16ebeb5cbe3022868d681b264607e6d9116`
  contains a choreographed `US demo` 50/Mixed reading adjacent to
  `LIVE · MARKET READ` marketing language.

Both China/HK local state and U.S. Mixed were simultaneously **present
in the checked-in rendered site source**. These do not prove the
origin server installed, CDN served, entitled browser displayed, or a
user received a market-warning push. The product attention question
is whether the original publisher and globally salient actual consumer
promoted **qualified regional observed risks**, not whether local
severe-state text existed somewhere on a country-specific page.

## Alert client static-mount and held Chromium gap (Oct 16)

See `ALERT_MOUNT_AND_HELD_BROWSER_GAP_20261016.md` and the two
readback-verified receipts:

- `evidence/banner_mount_source_census_20261016.json`, SHA256
  `a4514fd28992d3bfa4c7f3cf8bf56a0d0e4420980e1d50ccfbbe7a275105f67d`.
  **12/12** synthetic HTML parser tests RED→GREEN, run against two
  exact six-page Git-vintage source trees (Oct13 and Oct16).
  Oct13 index/macro/china/hk were UNMOUNTED; Oct16 macro/china/hk
  mounted but index remains UNMOUNTED. Markets/status controls mounted
  in both tree versions. Source state alone is not deployed DOM proof.
- `evidence/held_banner_consumer_gap_verified_20261016.json`, SHA256
  `d4e8c2dadb197a5f585c1d2d2b082d8e3d4f6ace3a01efa8da48bc990634537f`.
  **3/3** isolated Chromium tests against actual held #8132
  `templates/wh_banner.js` Git blob
  `9362255160a6a7358014632c53dd865dad163ebe` show
  `warning_projection` is NOT consumed if legacy `alert=null`,
  and a long-open tab does NOT poll a new severe alert; an initial
  legacy severe alert DOES render. No production auth/network.

Reproduce:

```bash
python -m unittest discover -s research/grey_deer/ror1_risk_attention_20261015 -p 'test_banner_mount_census.py' -v
export ROR1_BANNER_SOURCE=/path/to/existing-held-8132-worktree/templates/wh_banner.js
export ROR1_BROWSER_RECEIPT=/tmp/new-unique-ror1-browser-receipt.json
python research/grey_deer/ror1_risk_attention_20261015/test_held_banner_client_gap.py
```

Source page copies for the HTML census were derived via `git show` from
the original Git object database into isolated M2 research storage; they
are **not** re-published in this PR. The Chromium test deliberately
requires the exact **external** held PR head source, not a copied or
invented substitute. Incumbent #8132 browser tests cover only the
legacy `alert` value, not current multi-market projection.

**Release effect:** remains NONE. Original source owners must qualify
homepage mounting, per-market warning consumption and long-open polling
through the existing alert transport/episode lifecycle with correct
entitlement, market clocks and release conditions. The tests do not
prove installed production site, browser delivery or notification ACK.

## Next acceptance

Native source-vintage/issuance-bound episode replay, a predeclared negative
control set, reasoned revisions after backtest population changes, source
publication/entitlement readbacks and real long-open user delivery proof by
the existing owners. Until then, this is research only.
