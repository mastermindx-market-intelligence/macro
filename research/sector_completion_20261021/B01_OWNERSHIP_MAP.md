# B01 — Sector Central + Sector Cycles ownership map

Base: `3d8d14acdc8de99fa2c17316aa22de6177364dbc` (2026-10-21). Every line reference below
was read at that commit. This map is descriptive: defects are listed under Findings and
left in place (read-only packet). `tests/test_sector_completion_ownership_map.py` pins
this table against the code; `tests/test_sector_metric_definitions.py` pins the metric
definitions in `B04_METRIC_DEFINITIONS.md`.

## 1. Artifacts

One row per artifact written by the two builders, the rotation engine, the forward log
or the grader, plus each raw JSON file the two page families fetch at runtime. The two
page families are `templates/sector_central.html.j2` (hub) and `templates/sector_cycles.html.j2`
+ its copied asset `templates/sector_cycles.js`.

| artifact | writer file:symbol | inputs (paths) | consumer template file:function | session/generation fields present (exact key names) | freshness clock (what decides stale, file:line) | disposition |
|---|---|---|---|---|---|---|
| `site/sector_central.html` | `scripts/build_sector_central.py:main` (write_page :573) | `templates/sector_central.html.j2` + data JS rows below | the page itself | none (server-rendered shell) | rebuilt wholesale nightly; no age check | incorporated — live hub page |
| `site/sector_central_data.js` | `scripts/build_sector_central.py:main` (:445) | `engine.sector_central.compute` → data/yahoo parquets (`engine/inputs.py:37`), `site/marketdata/sp500_heatmap.json` (`engine/sector_central.py:181`), `data/us_sector_rotation/latest.json` (`engine/sector_central.py:657`), `data/baskets/membership.json` (`engine/sector_central.py:883`), `site/marketdata/rotation_events.json` (`engine/sector_central.py:695`), `data/strategies/thematic_rotation_phase0.json` (method tag, `engine/sector_central.py:932`) | `templates/sector_central.html.j2` hydrateMiniCycs (:3166; window.SECTOR_CENTRAL) | `as_of`; `meta.n_sectors`; `meta.n_baskets`; `meta.region`; `meta.experimental`; `meta.method`; `meta.board_order`; `market.n_above_trend`; `market.rotation_board_order`; `grader.*` (scorecard block, `engine/sector_central_grader.py:271-339`) | replaced nightly in full; consumer has no staleness rule (data-sync script tag :3063) | incorporated — the product payload |
| `site/sectordata/sector_central.json` | `scripts/build_sector_central.py:main` (:448) | same as `site/sector_central_data.js` | none in-repo (raw mirror for external/debug consumers) | same payload as the data JS | replaced nightly in full | remaining — raw mirror, no template consumer |
| `site/premiumdata/sector_central.json` | `scripts/build_sector_central.py:write_payload` (:213; write :244) | `site/basketdata/action_board.json` (:481), `site/basketdata/baskets.json` (:499), `site/basketdata/si_handoff.json` (:468), `templates/_us_act_now_board.html.j2` rows-only render (:238) | `templates/sector_central.html.j2` tier hydrate (PGATE.payload; fetch :4151) | `schema`=`tier_payload.v1`; `page`; `gated`; `required_tier`; `built`; `as_of`; `baskets_sha256`; `action_board_sha256`; `panels.actnow`; `actnow_html` | ALWAYS-written rule — a board that shrank below the cap must not leave yesterday's payload hydrating stale rows (`scripts/build_sector_central.py:217-227`) | incorporated — tier-gated Act-Now payload |
| `site/sector_cycles.html` | `scripts/build_sector_cycles.py:main` (write_page :146) | `templates/sector_cycles.html.j2` | the page itself | none (shell) | rebuilt nightly in full | incorporated |
| `site/sector_cycles_data.js` | `scripts/build_sector_cycles.py:main` (:118) | `engine.sector_cycles.compute` → data/yahoo parquets TR + price panels (`engine/sector_cycles.py:1314,1323`), `data/sector_cycles/narratives*.json`, `data/sector_cycles/cycle_dna*.json` | `templates/sector_cycles.html.j2` boot; `templates/sector_cycles.js` (window.SECTOR_CYCLES) | `meta.asOf`; `meta.today`; `meta.xDomain`; `meta.window_years`; `meta.rebaseDate`; `meta.benchmark`; `meta.rs_history.schema`; `meta.rs_history.mode`; `meta.rs_history.naturally_observed`; `meta.rs_history.basis`; `meta.rs_history.horizons_sessions`; `meta.rs_history.max_points_per_sector`; `meta.rs_history.as_of`; `meta.rs_history.min_history_sessions`; `meta.rs_history.benchmark_ffill_limit_sessions` (`engine/sector_cycles.py:1396-1420`) | no page-level age rule; the narrative halves carry their own TTL/epoch clocks (rows below) | incorporated — core cycles payload |
| `site/sector_cycles_series_data.js` | `scripts/build_sector_cycles.py:main` (:121) | same engine payload, split by `scripts/_cycles_payload.split_cycles_payload` (:116-117) | `templates/sector_cycles.js` `_scheduleExtras`/`_scheduleSeries` post-paint hydrate | per-entity osc/turns/price arrays; no own session key (inherits core meta) | hydrated after first paint; no staleness rule | incorporated |
| `site/sector_cycles_narr_data.js` | `scripts/build_sector_cycles.py:main` (:124) + `scripts/_narrative_ttl.enrich_narr_ttl` (:122) | `data/sector_cycles/narratives.json` / `narratives.price_c4414dcb.json` via `scripts/_narrative_epoch.resolve_narratives` (:51) | `templates/sector_cycles.js` focus panels (window.SECTOR_NARR) | per-entry `as_of`; `ttl_days`; `_ttl.as_of`; `_ttl.ttl_days`; `_ttl.staleness_days`; `_ttl.stale_amber`; `_ttl.stale_red`; `_ttl.archetype_check_id`; `_ttl.arch_state`; `_ttl.arch_fired_on`; `_ttl.revision_note` (`scripts/_narrative_ttl.py:229-239`) | two clocks: calendar-day TTL amber `>ttl_days`, red `>2×ttl_days`, default 90 (`scripts/_narrative_ttl.py:171-180`); epoch quarantine on epoch mismatch (`scripts/_narrative_epoch.py:146`) | incorporated |
| `site/sector_cycles_dna_data.js` | `scripts/build_sector_cycles.py:main` (:127) | `data/sector_cycles/cycle_dna*.json` via the same epoch resolver (:64) | `templates/sector_cycles.js` dnaHTML (window.SECTOR_DNA) | epoch metadata via the resolver (`epoch`, `prev_epoch`, `rekeyed_from`, `detector_version` in the source files) | epoch quarantine (`scripts/_narrative_epoch.py:146`) | incorporated |
| `site/sectordata/sector_cycles.json` | `scripts/build_sector_cycles.py:main` (:134) | same as `site/sector_cycles_data.js` | none in-repo (raw model mirror, external/debug) | full compute payload incl. `meta.asOf` | replaced nightly in full | remaining — raw mirror |
| `site/sector_cycles.css` + `site/sector_cycles.js` | `scripts/build_sector_cycles.py:main` (:148-151, copy2) | `templates/sector_cycles.css`, `templates/sector_cycles.js` | the cycles page (and the central hub's embedded overlay) | none | copied each build | incorporated |
| `site/mm_charts.js` + `site/cycle.css` | `scripts/build_sector_cycles.py:main` (:152-158, only-if-missing backfill) | `templates/mm_charts.js`, `templates/cycle.css` | shared cycle design system (both cycle pages) | none | `exists()`-guarded backfill; primary owner is `scripts/build_cycle.py` (see §2) | remaining — backfill only; primary owner outside this pair |
| `data/us_sector_rotation/latest.json` | `engine/us_sector_rotation.py:write_latest` (:875; write :892) | data/yahoo parquets (`engine.inputs.yahoo_closes`), `data/baskets/membership.json`, `data/sector_cycles/forward_log.parquet` `timing_state` (`engine/us_sector_rotation.py:125-126`) | `engine/sector_central.py:_load_rotation_artifact` (:655) — board re-order on the central page | `asof`; `ts`; `authority`; `instruments[]` (`engine/us_sector_rotation.py:885-890`) | 48 h wall-clock guard at the consumer (`engine/sector_central.py:677`), key `ts` OR `asof` (:668) | incorporated — display-tier board order |
| `data/sector_cycles/forward_log.parquet` | `engine/cycle_forward_log.py:append_forward_log` (:205; keep-first :274-275) | `engine.sector_cycles.compute` rows, stamped by `scripts/build_sector_cycles.py:91-92` | `engine/us_sector_rotation.py` (timing_state states); ledger readers | `date`; `id`; `kind`; `name`; `phase`; `pos`; `osc_slope`; `signal`; `timing_state`; `above200d`; `rs_63d`; `proj_next`; `proj_central`; `proj_lo`; `proj_hi`; `pos_v2`; `phase_v2`; `stance`; `divergence`; `overdue`; `basis`; `hazard_*` (`engine/cycle_forward_log.py:_extract_rows`) | append-only, keep-FIRST per (`date`,`id`) — a past day's stamp is never rewritten (:274); NO lane gate on this append (contrast the calls log, `engine/sector_central_grader.py:109`) | incorporated — point-in-time ledger |
| `data/sector_central/calls.parquet` | `engine/sector_central_grader.py:append_central_log` (:103; write :142) | `engine.sector_central.compute` rows + yahoo panel + basket levels | `engine/sector_central_grader.grade` (:220) → `grader` block of `site/sector_central_data.js` | `date`; `id`; `kind`; `ticker`; `basket_id`; `name`; `score`; `label`; `dir`; `confluence`; `trend_pass`; `ret_12m`; `gate_factor`; `level` (`engine/sector_central_grader.py:121-131`) | keep-FIRST per (`date`,`id`) (:138-139) and nightly-lane gate `nightly_advance_enabled` (:109) — render lanes stay read-only | incorporated — point-in-time calls ledger |
| `site/marketdata/rotation_events.json` | `scripts/build_rotation_events.py:build` (:112; write :179) | `engine.rotation_events` + `engine.sector_legs` + sector closes | `templates/sector_cycles.js:loadRotation` (:2052); `engine/sector_central.py:_load_rotation_events` (:695) | `generated_utc` (:122,165); `active[]` | none at either consumer (fail-soft reads; `cache:no-cache` fetch) | incorporated |
| `site/marketdata/sector_fragmentation.json` | `scripts/build_rotation_events.py:build` (:136) | `engine.sector_fragmentation.compute` (:135) | `templates/sector_cycles.js:loadRotation` (:2053) | `generated_utc` | none | incorporated |
| `site/live/shock_state.json` | `engine/shock_deescalation.py:build_intraday` (:194; `_SHOCK_STATE_REL` :50; hooked from `scripts/build_risk_state.py:485-491`) | `site/live/market_drivers.json` | `templates/sector_central.html.j2` inline fetch (:1442) | shock state fields per its engine | none in-page (no-cache fetch) | incorporated |
| `site/policy_lever.json` | `scripts/build_policy_lever.py:build` (:476) | policy-lever engine inputs | `templates/sector_central.html.j2` inline fetch (:1457) | per its builder | none in-page | incorporated |
| `site/basketdata/pulse.json` | `engine/group_pulse.py:write_site_artifact` (:1390; `_SITE_REL` :266) | `data/baskets/membership.json` + member tape | `templates/sector_central.html.j2` fetchJson/refreshPulse (:2575) | `group_pulse.v1` per-object schema | none in-page | incorporated |
| `site/basketdata/etf_pulse.json` | `scripts/build_theme_addons.py:main` (:38; `engine.etf_pulse.compute_etf_pulse` :44) | style/risk/rotation feeds | `templates/sector_central.html.j2` (:2750) | per its engine | none in-page | incorporated |
| `site/basketdata/vol_sentiment.json` | `scripts/build_theme_addons.py:main` (:38) | vol/sentiment feeds | `templates/sector_central.html.j2` (:2771) | per its engine | none in-page | incorporated |
| `site/basketdata/theme_extension.json` | `scripts/build_theme_addons.py:main` (:38) | theme feeds | `templates/sector_central.html.j2` (:2780) | per its engine | none in-page | incorporated |
| `site/basketdata/baskets.json` | `scripts/build_baskets.py:main` (:239) | theme-intel engine chain | `templates/sector_central.html.j2` `__siInitPage` (:3022); `scripts/build_sector_central.py:499` (sha256 + bottoming lane) | `as_of`; `theme_intel.as_of`; `generated_utc` | none at read; sha256 pinned into the premium payload (:486,503) | incorporated |

Adjacent engine inputs of the two builders (not written by the five owners, not fetched
by the templates, so not Artifacts-table rows — listed for completeness): `site/marketdata/sp500_heatmap.json`
(written by `scripts/build_sp500_heatmap.py`, `generated_utc` :460,468; read at
`engine/sector_central.py:181`), `site/marketdata/subsector_rotation.json` (written by
`scripts/build_subsector_rotation.py`, `asof`+`generated_utc` :193,250,255; read at
`scripts/build_sector_central.py:142`), `site/factordata/us_standouts.json` (read at
`scripts/build_sector_central.py:143`), `site/basketdata/foresight_cascade.json` (read at
:154), `site/basketdata/si_handoff.json` (written by `scripts/build_baskets.py`; read at
:468), `site/basketdata/action_board.json` (written by `scripts/build_sector_action_board.py`;
read at :481), `data/basket_levels/us.parquet` (frozen store, read by the grader),
`data/strategies/thematic_rotation_phase0.json` (validation record, read for the method tag).

## 2. Duplicate or competing owners

1. **`site/mm_charts.js` + `site/cycle.css` have two lawful writers.** Primary owner
   `scripts/build_cycle.py` (the comment at `scripts/build_sector_cycles.py:38-40` says
   so); `scripts/build_sector_cycles.py:152-158` backfills them only when missing
   (`exists()` guard, with a warning when absent). Benign by construction, but a rename
   in the primary owner silently turns the backfill into the shipping copy.
2. **`data/us_sector_rotation/latest.json` carries two freshness fields and its consumer
   accepts either.** The writer stamps `asof` (session date, from `scored[0]["asof"]`)
   and `ts` (write wall-clock, `datetime.now(timezone.utc)`) at
   `engine/us_sector_rotation.py:885-886`; the 48 h guard reads `ts` OR `asof`
   (`engine/sector_central.py:668`) and rejects at `age_h > 48` (:677). A session-date
   `asof` sits at midnight, so an evening read of a same-day artifact can measure ~a day
   more age than `ts` would — two clocks, one threshold.
3. **One central render can carry three different session labels.** The data JS `as_of`
   is the cycles engine's benchmark session (`engine/sector_central.py:928`); the
   premium payload `as_of` is a fallback chain across *other* artifacts
   (`action_board.as_of` → `baskets.theme_intel.as_of` → `baskets.as_of` → central
   `as_of`, `scripts/build_sector_central.py:531-538`); the payload `built` is
   `si_handoff.generated_utc` or central `as_of` (:530). No rule reconciles them.
4. **The NARR surface has two independent staleness rules.** Calendar-day TTL
   (`scripts/_narrative_ttl.py:171-180`, amber/red vs `ttl_days`, default 90) and epoch
   quarantine (`scripts/_narrative_epoch.py:146`, engine epoch vs file epoch). Both can
   fire independently on the same entry; neither subsumes the other.
5. **Forward-log advance is not lane-gated while the calls log is.**
   `engine/cycle_forward_log.py:append_forward_log` appends unconditionally (only the
   keep-first dedupe protects history, :274), while
   `engine/sector_central_grader.py:109` refuses off-nightly appends via
   `nightly_advance_enabled()`. A render-lane run of `scripts/build_sector_cycles.py`
   (its only caller, :91-92) would advance the forward ledger on the wrong lane. See
   Findings F1.

## 3. Correction/version census (R3A-92)

Method: for every artifact above, the writer's source was AST-scanned for string-literal
dict keys matching `correct*|revis*|supersede*` — all twelve writer sources are clean
(`tests/test_sector_completion_ownership_map.py` re-proves this on every run). The
payloads themselves were inspected for version/correction keys. `none_native` means
exactly that: no native correction, revision or supersession contract exists on that
surface, and none may be fabricated for it.

| artifact | schema | field(s) or none | semantics |
|---|---|---|---|
| `site/sector_central_data.js` | — | `none_native` | payload replaced wholesale nightly; since SIC-D-B13 every conviction row carries `conviction.score_version` — a score-DEFINITION stamp (1 = crowding cap dormant, 2 = cap input resolved via `ticker`), not a correction or supersession key |
| `site/sectordata/sector_central.json` | — | `none_native` | same payload, same contract — the per-record `conviction.score_version` stamp rides both encodings |
| `site/premiumdata/sector_central.json` | — | `none_native` | `built`/`as_of`/sha256 are generation stamps, not correction contracts; ALWAYS-written rule supersedes by replacement |
| `site/sector_cycles_data.js` | — | `none_native` | `meta.rs_history` stamps provenance (`mode`, `naturally_observed`) but no correction/supersession field |
| `site/sector_cycles_series_data.js` | — | `none_native` | split of the core payload; no version key |
| `site/sector_cycles_narr_data.js` | — | `_ttl.revision_note` (from authored `prev_revision`) | the ONE native revision channel in these two artifacts: a narrative entry may carry `prev_revision` `{as_of|date, summary_of_change|summary}` (authored research data, initialised `null` by `scripts/migrate_narrative_ttl.py:147`); the TTL enricher surfaces it as `_ttl.revision_note` = `"revised {date}: {summary}"` (`scripts/_narrative_ttl.py:217-224,237`). File-level epoch chain (`epoch`, `prev_epoch` `tr_v0`→`price_c4414dcb`, `rekeyed_from`, `detector_version` in `data/sector_cycles/narratives.price_c4414dcb.json`) supersedes a whole narrative generation |
| `site/sector_cycles_dna_data.js` | — | `none_native` | epoch metadata only; no per-record correction field |
| `site/sectordata/sector_cycles.json` | — | `none_native` | raw mirror |
| `data/us_sector_rotation/latest.json` | — | `none_native` | display-tier snapshot; `asof`/`ts` are generation stamps |
| `data/sector_cycles/forward_log.parquet` | — | `none_native` | immutability by construction: append-only, keep-FIRST per (`date`,`id`) (`engine/cycle_forward_log.py:274`) — a wrong row is never corrected, only never overwritten |
| `data/sector_central/calls.parquet` | — | `none_native` | same keep-FIRST immutability (`engine/sector_central_grader.py:305-306`); SIC-D-B13 appends a `score_version` column — prior rows read NaN (never rewritten) and grade as legacy version 1, so the scorecard never pools calls made under two score definitions |
| `site/marketdata/rotation_events.json` | — | `none_native` | detector output regenerated nightly; no event-level correction key |
| `site/marketdata/sector_fragmentation.json` | — | `none_native` | same |
| `site/live/shock_state.json` | — | `none_native` | state snapshot |
| `site/policy_lever.json` | — | `none_native` | regenerated |
| `site/basketdata/pulse.json` | — | `none_native` | display snapshot |
| `site/basketdata/etf_pulse.json` / `vol_sentiment.json` / `theme_extension.json` | — | `none_native` | display strips |
| `site/basketdata/baskets.json` | — | `none_native` | `as_of`/`generated_utc` are generation stamps |
| — | `contracts/sector_intelligence/sector_event.v1.schema.json` | `supersedes_event_id`; `valid_from`; `schema_version` | record-level supersession: a new event row names the event it supersedes; bitemporal validity |
| — | `contracts/sector_intelligence/source_record.v1.schema.json` | `valid_from`/`valid_to` + `transaction_from`/`transaction_to`; `source_published_at`/`source_effective_at`/`retrieved_at`/`first_seen_at`; `parser_version`; `source_schema_version` | full bitemporal source custody (valid-time + transaction-time) |
| — | `contracts/sector_intelligence/prediction.v1.schema.json` | `supersedes_prediction_id`; `schema_version` | record-level supersession of predictions |
| — | `contracts/sector_intelligence/evidence_claim.v1.schema.json` | `correction_of_claim_id`; `parser_or_model_version`; `valid_from` | record-level correction: a claim may name the claim it corrects |
| — | `contracts/sector_intelligence/outcome_label.v1.schema.json` | `revision_reason`; `outcome_taxonomy_version` | labelled revisions of outcome labels |
| — | `contracts/sector_intelligence/authority_manifest.v1.schema.json` | `schema_version`; `valid_from` | schema-evolution version + validity |
| — | `contracts/sector_intelligence/entity_link.v1.schema.json` | `schema_version`; `valid_from` | schema-evolution version + validity |
| — | `contracts/sector_intelligence/feature_snapshot.v1.schema.json` | `schema_version`; `feature_set_version`; `as_of` | feature-set versioning |
| — | `contracts/sector_intelligence/finance_intelligence_read_model.v1.schema.json` | `schema_version`; `common_as_of` | read-model versioning |
| — | `contracts/sector_intelligence/finance_intelligence_research.v1.schema.json` (+ `.evidence`) | `definition_version` | definition versioning |
| — | `contracts/sector_intelligence/lobe_run.v1.schema.json` | `schema_version`; `model_versions` | model/version provenance |
| — | `contracts/sector_intelligence/sector_dossier_read_model.v1.schema.json` | `schema_version`; `dossier_version`; `common_as_of` | dossier versioning |
| — | `contracts/sector_intelligence/sector_intelligence_packet.v1.schema.json` | `schema_version`; `packet_version` | packet versioning |
| — | `contracts/sector_intelligence/consumer_cyclical_intelligence_read_model.v1.schema.json` | `schema_version` | schema-evolution version only |

Net census: the *contract layer* has real correction/supersession vocabulary
(`sector_event`, `prediction`, `evidence_claim`, `outcome_label`, `source_record`), but
**none of the artifacts these two pages write or read is emitted under those schemas** —
the emitted surfaces are `none_native` except the authored `prev_revision`/epoch channel
on narratives. Later packets must stamp only what this table shows exists.

## 4. History provenance census (B11)

| history-bearing surface | observed_then / reconstructed / restated / unknown | code that proves it |
|---|---|---|
| forward log (`data/sector_cycles/forward_log.parquet`) | **observed_then** — each night's compute() state stamped once, point-in-time | append-only keep-FIRST per (`date`,`id`) `engine/cycle_forward_log.py:274`; stamped in the nightly builder `scripts/build_sector_cycles.py:89-95` |
| calls log (`data/sector_central/calls.parquet`) | **observed_then** — nightly lane appends today's call, never rewrites | keep-FIRST `engine/sector_central_grader.py:138-139`; lane gate :109 |
| grader scorecard (`grader` block of the central payload) | **observed_then calls, recomputed read** — the calls are PIT; the scorecard itself is recomputed each run over those calls against frozen series | `grade()` re-derives every horizon each run `engine/sector_central_grader.py:220-341`; basket legs read only the frozen store `data/basket_levels/us.parquet` (:42-57) clamped to chain anchors |
| reconstructed price history (`meta.rs_history` + per-sector `rs_history` trail) | **reconstructed** — and labelled as such | `"mode": "reconstructed_price_history"`, `"naturally_observed": False` `engine/sector_cycles.py:1407-1408`; docstring: "historical reconstruction from the committed price owner, not a claim that these snapshots were naturally observed at the time" `engine/sector_cycles.py:493-499`; eligibility gated on the live owner's own 210-row minimum (:507-508) |
| Time-Machine-style as-of reads (`compute(asof=...)`, `_leadership(asof=...)`) | **reconstructed** — as-of slicing of today's committed panel, not a replay of what was published then | `compute(asof)` slices both panels to `<= asof` `engine/sector_cycles.py:1328-1331`; `_leadership(asof=...)` slices ticker+bench `engine/sector_cycles.py:462-466`; the panel itself is the current yahoo parquet store (`engine/inputs.py:37`) |
| phase narratives (`data/sector_cycles/narratives*.json` → `SECTOR_NARR`) | **restated** — researched "what happened & why" prose authored after the legs, keyed by detected turn dates; restatements tracked, not observed | file header note + `version: "2026-06-27-basket-rotation"`; per-entry `as_of`/`ttl_days`/`prev_revision` (revision channel, §3); epoch rekeying re-dates legs to a new detector generation (`scripts/rekey_narratives.py:289`, `prev_epoch` `tr_v0` → `price_c4414dcb`) |
| heat / breadth context (`sp500_heatmap.json` feed) | **unknown (window semantics owned upstream)** — the aggregation is exact but the 1D/1M/YTD windows are the feed producer's, not re-derived here | `engine/sector_central.py:195-220` consumes `tile["perf"][tf]` as delivered |

## 5. Findings

Defects and hazards seen while mapping. None fixed (read-only packet).

- **F1 — forward-log advance has no lane gate.** `engine/cycle_forward_log.py:append_forward_log`
  appends whenever called; its only caller is the render-side builder
  `scripts/build_sector_cycles.py:91-92`. `engine/sector_central_grader.py:109` shows
  the intended pattern (`nightly_advance_enabled` gate). An off-nightly run of the
  cycles builder advances `data/sector_cycles/forward_log.parquet` on the wrong lane;
  keep-first makes that day's row permanently the wrong-lane stamp.
- **F2 — premium payload `as_of` can describe another artifact's session.** The chain at
  `scripts/build_sector_central.py:531-538` prefers `action_board.json`'s `as_of`; when
  the board lags the cycle spine, the gated payload wears a session the central data
  itself does not have. No reconciliation exists.
- **F3 — 48 h guard accepts two clocks.** `engine/sector_central.py:668` reads `ts` or
  `asof`; midnight-anchored `asof` ages faster than write-time `ts`
  (`engine/us_sector_rotation.py:885-886`). Same artifact, two stale verdicts.
  *Superseded at integration (SIC-D-B02, 2026-10-21): the wall-clock guard is replaced by the
  settled-session generation guard `engine/sector_generation_guard.session_alignment`
  (`engine/sector_central.py:1008-1013`); `session`/`asof` is the gate, `ts` is provenance only.*
- **F4 — basket RS benchmark gap tolerance differs from sector RS.** Sector RS ffills
  the benchmark with `RS_BENCH_FFILL_LIMIT = 5` (`engine/sector_cycles.py:412,441`);
  `_basket_rs` ffills SPY without a limit (`engine/sector_cycles.py:1141`). Same-named
  `rs_21d`/`rs_63d` fields, different holiday-gap behavior.
- **F5 — grader bases mix within one scorecard.** Sector legs grade on the TR ETF panel
  (`engine/sector_central_grader.py:34-40`, `yahoo_closes()` default basis `tr`);
  basket legs grade on the frozen EW `level_tr` store (:42-57). Disclosed in code, but
  the two `fwd` populations are not one measurement basis.
- **F6 — rotation freshness posture is inconsistent across the hub.** `latest.json`
  has a 48 h wall-clock guard (`engine/sector_central.py:677`); `rotation_events.json`
  — read by the same engine (`:688-699`) and by `templates/sector_cycles.js:2052` — has
  no age check at all. *Post-B02 the `latest.json` side is the generation guard above;
  the `rotation_events.json` gap is tracked by the same packet's Cycles guard (B02/B1011).*
- **F7 — `templates/sector_central.html.j2:46` prefetches `heatmap.js`** while the
  page's rendered heat context is computed server-side from `sp500_heatmap.json`
  (`engine/sector_central.py:175-224`). Whether the prefetched script fetches the raw
  feed on this page was not traced; recorded as an untraced second heatmap path.
- **F8 — `narratives.json` (legacy, un-suffixed) entries carry no `as_of`/`ttl_days`**;
  only the epoch-migrated file (`narratives.price_c4414dcb.json`) does. While the
  legacy file is the one resolved (no flip), TTL staleness silently reads `None`
  (`scripts/_narrative_ttl.py:170-181`) and the amber/red clocks never fire.
