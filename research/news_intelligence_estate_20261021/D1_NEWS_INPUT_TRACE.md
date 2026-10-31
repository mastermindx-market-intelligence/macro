# D1 news input trace
BASE: 64ef5131a5f50fb65f0ad25a049a457e18258495
RUN_ID: ne-d1-trace-20261022-r1
MODEL: glm-5.3-flash
MASTERMIND EXCERPTS: read-only paste at Mastermind HEAD c7e47c859eb2925c5626931fd511800773ba09ac (read-only grep/sed by ORCH-FACTS 2026-10-22)
VERDICT: PASS

Trace of every path by which news enters a macro engine, a site/*.json artifact, or a
Mastermind consumer, hop by hop, with an AUTHORITY class per hop. All path:line citations
resolve at BASE 64ef5131a5f50fb65f0ad25a049a457e18258495 unless marked `mastermind:` (those
cite the pasted excerpts at the Mastermind HEAD above).

AUTHORITY classes (exactly one per hop):
- `display-only` — rendered/served, never read by a computation.
- `research context` — read by a research/report builder or an LLM prompt, never by a scoring/sizing computation.
- `engine input` — read by a scoring/ranking/sizing/signal computation with NO gate.
- `gated engine input` — read by a computation only through a named gate (gate named + cited).

Gates cited are code that actually stands between the news value and the computation. An
access/rights gate (auth, entitlement) is noted as such; it is not a signal gate.

---

## T1 — engine/news_flow.py: the GDELT macro-narrative velocity leg

The news bus accrues `data/news_vector/events.parquet` (engine/news_flow.py:4). news_flow is
a LEAF: it reads the bus parquet directly, never importing the bus module (engine/news_flow.py:11-12, 54-59).

| hop | source (path:line) | clock | transformation | output artifact | next reader(s) | AUTHORITY | gate |
|---|---|---|---|---|---|---|---|
| T1.1 | engine/news_vector.py:355 (fetch_range), :266 (accrue), :285-286 (columns), :530 (to_parquet) | `first_seen_utc` (crawl-first-seen, NEVER overwritten on re-ingest — engine/news_vector.py:25, 281); `seendate` (GDELT crawl publish); `scheduled_ref` (release-window flag — :247) | GDELT fetch → theme classification → tier stamp (`source_tier`, :163, :220) → keep-first accrual → parquet | data/news_vector/events.parquet | engine/news_flow.py:62 (T1.2); engine/news_vector.py:548 (T1.7); engine/news_vector.py:643 (T1.8) | engine input (substrate of the scoring legs T1.4/T2.1) | none |
| T1.2 | engine/news_flow.py:62-73 (load_events; _events_path :54-59) | `first_seen_utc` → parsed UTC `ts` (:72) | read parquet, parse clock, drop unparseable rows | in-memory DataFrame | engine/news_flow.py:86 (theme_flow, T1.3); engine/theme_activity.py:486 (T1.4); engine/foresight_earliness.py:128 (T2.1) | engine input (transit into scoring legs) | none |
| T1.3 | engine/news_flow.py:86-118 (theme_flow) | `ts` (from first_seen_utc) vs `today` window (:95-100) | 7d tier-weighted velocity + acceleration vs prior 7d; `metric`=acceleration (:113); stamps `is_context_only: True` (:117) | in-memory dict per basket | engine/theme_activity.py:516 (T1.4); engine/foresight_earliness.py:137 (T2.1) | engine input (consumed as a fusion metric in both readers) | none at this hop |
| T1.4 | engine/theme_activity.py:461 (compute_real_activity), news leg load :484-491, call :513-518, fusion :562-563, :570 | event `ts` window vs build-day `today` | news leg robust-z, fused at NEWS_WEIGHT=0.5 (:69) with hard sources (weights 0.45–1.0, :104-130) into `fused_obs_z`/`fused_accel`/`obs_dir` (:534, :562-566, :570-573) | in-memory per-basket dict (carried in radar payload) | engine/radar.py:167 (T1.5); scripts/build_foresight.py:272-276 (T3.6 board); engine/foresight_divergence.py:338 | gated engine input | hard-source precondition: a basket with no HARD (spend/alt-data) source is dropped entirely — news alone never qualifies a basket (engine/theme_activity.py:519-521); deliberately low weight (NEWS_WEIGHT=0.5, :69) |
| T1.5 | engine/radar.py:151-167 (compute_radar consumes ra), stamps :242, :254; scripts/build_baskets.py:456-459 | radar payload `as_of` (baskets payload; engine/radar.py:178) | real-activity z vs price consensus → per-theme divergence states, `is_context_only: True` | site/basketdata/radar.json + append_ledger (data/radar ledger) | templates/_radar_panel.html.j2:2 via radar_panel.js (display); engine/signal_governor.py:44-51 radar_ic path (T1.6); scripts/build_radar_page.py (display) | display-only for the published artifact; the ledger branch continues into a governed scoring path (T1.6) | artifact-level `is_context_only: True` (engine/radar.py:242, :254) — a stamp, not a code gate |
| T1.6 | engine/signal_governor.py:79 (_SIGNALS incl. "radar"), trust map :44-55; applied engine/intel_hub.py:632-639 | matured track-record horizon (radar_ic daily IC) | de-escalation-only trust ∈ [floor,1] multiplies DOWN the opportunity of radar-driven hub names | data/hub/signal_governor.json; hub opportunity (in-memory → site/intel_hub/hub.json) | engine/intel_hub.py:634-639 (T4.6) | gated engine input (news-influenced radar states may only ever REDUCE hub opportunity through this path) | signal governor de-escalation-only gate: trust clamped ≤1.0, HAC-significance + n_matured gate, missing ⇒ no-op (engine/signal_governor.py:12-21, :128) |
| T1.7 | engine/news_vector.py:548-594 (ingest_to_qbus; row map :572-586, append :588), driven by scripts/build_news.py:236 | `seendate`=first_seen_utc + `_crawled_at`; `timestamp_quality=CRAWL_BOUNDED` (:551, :581) — crawl-bounded, NOT publisher-stated; `importance_raw` from source_tier (:585) | GDELT events → qbus store rows | qbus live-news store (engine/qbus_news_store.py:255-281 schema; `published_at`/`received_at`/`first_received_at` :403-415) | engine/qbus_news_store.py:1976 (news_flow read) → app/ticker_news.py:583 (T4.10) | display-only (served read API) | `NewsReadRights` source-rights gate (app/ticker_news.py:580-583) — an ACCESS gate, not a signal gate |
| T1.8 | engine/news_vector.py:643-670 (recent_panel), called scripts/build_news.py:237 | `first_seen_utc` cutoff (days window, :656) | recent GDELT events + uncertainty-regime context → narrative feed | site/news/narrative.json (scripts/build_news.py:317) | none found in repo (`git grep` for readers: no in-repo reader at BASE) | display-only | none |

Docstring note: engine/news_flow.py:9 claims the fused observable lives in `engine/real_activity.py` — that module does NOT exist at BASE; the implementation is `engine/theme_activity.compute_real_activity` (engine/theme_activity.py:461). Cross-check: `git grep -n "real_activity" -- engine scripts` hits only docstrings/comments (engine/news_flow.py:9, engine/radar.py:4, engine/macro_surprise.py:18, engine/foresight_divergence.py:142, :338) plus the real call sites above.

---

## T2 — engine/foresight_earliness.py: attention score from news velocity

| hop | source (path:line) | clock | transformation | output artifact | next reader(s) | AUTHORITY | gate |
|---|---|---|---|---|---|---|---|
| T2.1 | engine/foresight_earliness.py:119-146 (_leg_news_flow; nf.load_events :128; nf.theme_flow :137; velocity→attention :145) | event `ts` (first_seen_utc) via theme_flow window | per-theme news velocity → attention leg (louder = later) | in-memory leg dict | engine/foresight_earliness.py:267, :282 (T2.2) | engine input (leg of the earliness composite) | leg-coverage floor: a leg is usable only at ≥ LEG_MIN_COVERAGE=6 themes and non-tied values (engine/foresight_earliness.py:52, :289-297) — a coverage gate, not a signal gate |
| T2.2 | engine/foresight_earliness.py:239-358 (compute_foresight_earliness; per-leg rank-pct :286-299; earliness=1−rank_pct :319-321) | build-day `asof` = date.today() (:340) | 4 attention legs → cross-sectional earliness ∈ [0,1] | in-memory payload; append data/foresight/earliness_log.jsonl :365-411 — write gated to the nightly lane (:404-409), driven by scripts/grade_thematic.py:79 | engine/foresight_score.py:316-317; engine/foresight_convergence.py:112-118; engine/foresight_sizing.py:256-257 (T2.3); engine/foresight_leadlag.py:417-434 (T2.4) | engine input (feeds the desk's score/sizing-band computations) | none beyond the leg-coverage floor (T2.1) |
| T2.3 | engine/foresight_sizing.py:251-262 (_load_earliness_map), :270-296 (_size_mult; earliness_tilt) | earliness `asof` (same build day) | `size_mult = stage_cap × earliness_tilt × cluster_dilution` — a relative size scalar in [0,1] | in-memory posture bands in the foresight payload (display artifact) | foresight display builders (site/foresight pages) | engine input (a sizing computation reads the news-derived earliness; output is stamped DISPLAY-ONLY guidance — engine/foresight_sizing.py:11, :18, :273) | coverage floor `n_live >= 2` usable legs else earliness=None → tilt 1.0 (engine/foresight_sizing.py:262; absent earliness → neutral :18) — a coverage gate, not a signal gate |
| T2.4 | engine/foresight_leadlag.py:408-434 (grade: reads data/foresight/earliness_log.jsonl :417-434) | log rows' `asof`/`ts` (foresight_earliness.py:390-393) | forward-grading of attention legs against later foresight logs | grading report (research) | scripts/grade_thematic.py output; research review | research context | none |

Note: foresight_score (engine/foresight_score.py:204, :316-317) and foresight_convergence (engine/foresight_convergence.py:112-118, :358) both call `compute_foresight_earliness(write_log=False)`; earliness is one input to the Foresight Desk's ranked score — the same engine-input class as T2.3, same coverage gates, same display-tier destination.

---

## T3 — real_activity: SF-Fed news sentiment and other news-derived series

### T3.a — SF-Fed Daily News Sentiment (frbsf store)

| hop | source (path:line) | clock | transformation | output artifact | next reader(s) | AUTHORITY | gate |
|---|---|---|---|---|---|---|---|
| T3.1 | collectors/frbsf.py:23-51 (NewsSentimentAdapter; date index :43-51); registered scripts/collect.py:173 | `date` (index; daily series, T+5 publication lag — noted engine/risk_radar_market_catalysts.py:995) | CSV download → date-indexed series | data/frbsf/news_sentiment.parquet (scripts/narrative_realign_phase0.py:75) | engine/inputs.py:429 (T3.2); engine/risk_radar_market_catalysts.py:1000 (T3.5); engine/narrative_regime.py:18 (T3.6) | engine input (substrate; strongest downstream is the scoring core) | none |
| T3.2 | engine/inputs.py:429-431 (store.read("frbsf","news_sentiment"); put with ffill_limit=7) | series `date`; staleness bounded by ffill_limit=7 days | feature-frame column `news_sentiment` in the mechanical scoring core's frame (engine/macro_surprise.py:3-4 names inputs.py as that core) | in-memory feature frame | engine/conditions.py:368 (T3.3) — no other scoring-core reader (grep: none in run/regime/equity_alloc) | engine input (transit) | none at this hop (quarantine happens one hop later, T3.3) |
| T3.3 | engine/conditions.py:368-371 (z-score, 252d), surfaced :824-827 | ffill-bounded series | `news_sentiment_z` + optimistic/pessimistic state in the risk block | conditions payload → site conditions panel | scripts/build_site.py:6574 (state string, T3.4) | research context (a reported gauge; read by a computation but never by a scoring/sizing term) | structural EXCLUSION: explicitly NOT folded into the roro composite "to keep that gauge stable until this leg is separately validated" (engine/conditions.py:822-823) — an exclusion by omission with an in-code guard comment, not a conditional gate |
| T3.4 | scripts/build_site.py:6574 | z + state as of build | renders "state (z=…)" string | site conditions display | browser | display-only | none |
| T3.5 | engine/risk_radar_market_catalysts.py:987-1000+ (_c10_news_tone_recovering; store.read :1000; 21d mean, 504d causal pctile, washout/recovery states) | series `date`, lag-honest label (:995) | catalyst chip `news_tone_recovering` | risk-radar catalysts dict | engine/risk_radar_recovery.py:101-115, :327; engine/ignition_radar.py:1041; templates/_risk_radar_card.html.j2:205 | display-only (ignition_radar: "DISPLAY-ONLY, FORWARD-GRADED, NOT VALIDATED — nothing here is a buy signal"; two channels "NEVER fused into any cross-channel score" — engine/ignition_radar.py:3-7) | none (label taxonomy only) |
| T3.6 | engine/narrative_regime.py:18 (SFED residual pass); scripts/narrative_realign_phase0.py:12-13, :75 | series `date`, expanding-z PIT | VIX-orthogonal residual study (phase-0 research); NDI banner | research output; site banner (scripts/build_site.py:6605-6629, stamped DISPLAY-ONLY :6614) | scripts/build_site.py:6610-6622 | research context | none |

### T3.b — China news-sentiment analog (the only news→direction chain with a real code gate)

| hop | source (path:line) | clock | transformation | output artifact | next reader(s) | AUTHORITY | gate |
|---|---|---|---|---|---|---|---|
| T3.7 | engine/china_news_intel.py:13-15 (SF-Fed Daily News Sentiment analog), :154 (data/china_news_vector/events.parquet) | per-item timestamp z-scored over a trailing window (:13-15) | CCTV+wire sentiment → z-series | china news intel surfaces (news_sent band/z) | engine/china_validation.py:269-277, :694-698 (T3.8); engine/china_intel_analysis.py:144 (T3.9) | engine input (transit into the conviction computation) | none at this hop |
| T3.8 | engine/china_validation.py:269-277 (_news_sentiment_series), family validation :694-698 | weekly panel dates | sign/validation grading of the news_sentiment family | china_validation results (proven/sign_ok flags) | engine/china_intel_analysis.py:115-119 (gate read) | research context (validation research) | none |
| T3.9 | engine/china_intel_analysis.py:109-122 (_news_sign_proven), news leg weight :143 (`"news", .20`), direction zeroing :197-206, basis stamp :271 | news band/z as of build | news leg in the 5-leg china conviction: salience ALWAYS contributes; DIRECTION is held at 0 until the validation family is proven+sign_ok; row stamped `direction_basis="salience_only"` | china divergence conviction rows | china policy-watch surfaces (display) | gated engine input | `_news_sign_proven` sign gate: direction stays weight-0/salience-only until china_validation proves the contrarian sign (engine/china_intel_analysis.py:109-122, :197-206) — the named, code-enforced gate |
| T3.10 | engine/china_national_team.py:23, :362-364, :419, :445 (china_news_vector events → state_media_drumbeat / facility_watch) | effective-timestamp column `_eff` UTC (:363-364) | tier-1 + keyword state-media drumbeat intensity | china national-team radar payload (`authority: context_only, may_originate: False` — :726) | china_policy_watch page (display) | display-only | module authority stamp `may_originate=False, may_escalate=False` (engine/china_national_team.py:11, :726) — a declared constraint on the payload, not a conditional gate |

### T3.c — Polygon editorial news-sentiment inside the alt-data desk

| hop | source (path:line) | clock | transformation | output artifact | next reader(s) | AUTHORITY | gate |
|---|---|---|---|---|---|---|---|
| T3.11 | engine/altdata.py:666-676 (news_sentiment_signals; data/polygon/news_sentiment.parquet) | parquet series dates (Polygon publish) | per-ticker bull-ratio lean | in-memory signals list | engine/altdata.py:1283 (into the signals dict) | engine input (transit into the desk's weighted kernel) | none |
| T3.12 | engine/altdata_models.py:166 (CHANNEL_WEIGHTS `news_sentiment: 0.20` — "abundant but noisy"), :65 (isolation note), :673-678 | signal recency as of build | news channel enters the alt-data weighted kernel → convergence_score / weighted_score (engine/altdata_signals.py:33-47) | site/altdata/by_ticker.json + site/altdata/mastermind.json (published via scripts/build_alt_data.py) | engine/intelligence.py:286-287 (T4.3, alt facet); engine/altdata_alerts.py:110, :152-154; engine/altdata_ledger.py:252-312; Mastermind lenses (Mastermind section) | engine input (news is 0.20 of a scored composite) | none in macro — the composite is scored; Mastermind-side consumption is context-only by Mastermind's own lens code (see Mastermind section) |

---

## T4 — engine/intelligence.py by_ticker bundle (SCHEMA intelligence.by_ticker.v2)

| hop | source (path:line) | clock | transformation | output artifact | next reader(s) | AUTHORITY | gate |
|---|---|---|---|---|---|---|---|
| T4.1 | engine/financial_news.py:303-304 (Polygon fetch, sort `published_utc` desc), lean/score/strength derivation :877-922 (mastermind_by_ticker; "never a scored axis" :880-881), feed stamp :852-857 | per-headline `seendate` (GDELT) / `published_utc` (Polygon); artifact `fetched_at` + `asof` (:852); per-item `published`=seendate (:916) | multi-provider financial news → per-ticker flow (n_recent, sentiment_lean, sentiment_score, sentiment_strength) | site/news/financial.json + site/news/by_ticker.json (T4.2) | scripts/build_news.py:307 (T4.2); engine/intelligence.py:285 (T4.3) | engine input (transit into the bundle's brain-priority scoring) | none |
| T4.2 | scripts/build_news.py:307-309 | artifact `asof` = build date (:308); per-item published timestamps carried through | compact per-ticker write, stamped `is_context_only: True` | site/news/by_ticker.json (schema news_flow.v1) | engine/intelligence.py:285 (T4.3); scripts/build_stock_library.py:3874-3884 (T4.9); scripts/build_ticker_pages.py:894-906 (T4.9); templates/alt_data.html.j2:695 (T4.9) | engine input (artifact transit; strongest downstream is the hub vote T4.6) | stamp `is_context_only: True` (scripts/build_news.py:307-308) — a stamp, not a code gate |
| T4.3 | engine/intelligence.py:282-291 (load_and_build; news :285, alt :286-287, radar :288, standout :289), build :225-270, _brain :174-222 (priority = confidence×strength :215), _synthesize :95-126 (early_edge/crowded_top use news_dir :115-120) | bundle `as_of` = build date (:262-264); input artifact stamps carried | 4-facet merge; news direction enters facet agreement/lean/priority; `is_context_only: True` + DISCLAIMER (:263, :34-39) | in-memory bundle → site/intelligence/by_ticker.json (scripts/build_intelligence.py:73) + site/basketdata/radar_news.json (:38-66) | engine/intel_hub.py:1124 (T4.6); engine/briefing.py (T4.5); scripts/build_ticker_pages.py:894 (T4.9); Mastermind tools/lenses (Mastermind section); engine/us_context_vector.py (hub columns, T4.7) | engine input (news participates in a deterministic ranking-key computation) | none |
| T4.4 | engine/briefing.py:78-99 (_item; _facts carries news_lean/news_n_recent :71-72), rank :116-118; scripts/build_briefing.py:27-33 | bundle `as_of` | reduce bundle to a RANKED priority_queue + divergences for an LLM reader; "Nothing here scores or sizes" (engine/briefing.py:22) | site/intelligence/briefing.json (scripts/build_briefing.py:33) | engine/neuralweb/contradictions.py:551+; engine/neuralweb/world_state.py:2789; engine/recurring_briefs.py:52; engine/signal_sanity.py:132; Mastermind get_daily_briefing (Mastermind section) | research context (ranked triage whose ranking key already contains news — see T4.3) | none |
| T4.5 | engine/neuralweb/contradictions.py:551-576 (pair-E: briefing divergences vs by_ticker demand/tape), :1040; engine/neuralweb/world_state.py:2789 (intelligence lobe) | artifact as_of stamps | cross-artifact contradiction detection; LLM world-state context | neuralweb research payloads / LLM prompts | brain LLM flows | research context | none |
| T4.6 | engine/intel_hub.py:1121-1129 (load_and_build; bundle :1124); _VOTING_DESKS includes "news" :89; news votes in n_confirm/lean :563-569; composite base from brain.priority :575-582; news crowding discount in edge_remaining :413-420 (weight 0.9); self-accrued news-velocity ledger :291-334 (load_velocity :299); velocity_spike flag :615; loud_bull :585-588; opportunity :620-624 | bundle as_of; velocity ledger day-over-day n_recent | 5-desk dossier: news VOTES on composite_conviction/lean and discounts edge_remaining; command ranked by opportunity_score | in-memory dossiers → site/intel_hub/hub.json (scripts/build_intel_hub.py:451) + site/intel_hub/track_record.json (:452) + data/hub/track_record.json (:405-408) + data/hub/signal_governor.json (:414-421) | engine/us_context_vector.py:759-800 (T4.7); engine/signal_sanity.py:187; Mastermind get_intel_hub (Mastermind section); intelligence_hub page render (scripts/build_intel_hub.py:499-509) | engine input (news is a VOTING desk in a ranked 0-100 conviction + opportunity ranking, with NO gate on the news leg itself) | none for news: the A7 exclusion removes the LLM-originated POLICY desk from voting, not news (engine/intel_hub.py:89, :470, :563-564); the signal governor de-escalates RADAR only, never news (engine/intel_hub.py:632-639) |
| T4.7 | engine/us_context_vector.py:759-800 (hub_columns reads site/intel_hub/hub.json :767 + data/hub/signal_governor.json) | snapshot-night stamp (keep-first PIT :17-19) | six typed `hub_*` columns into the PIT feature-and-admission log | data/us_prophet_rank/candidates/YYYY-MM.parquet | future studies only ("Nothing reads this store for scoring" — :10-11) | research context | bounded-authority ladder: "Zero authority at birth… each rung needs its own preregistration" (engine/us_context_vector.py:8-13) |
| T4.8 | scripts/build_ticker_pages.py:894-906 (intel_map/news_map agg) | artifact as_of stamps | per-ticker page view-model | site stock/ticker pages | browser | display-only | none |
| T4.9 | scripts/build_stock_library.py:3870-3884 (news burst chip, "DISPLAY-ONLY; 17-ticker coverage today"); templates/alt_data.html.j2:695-696 (JS reads news/by_ticker.json + financial.json); templates/committee.html.j2:1616-1617 (labels) | artifact as_of/asof stamps | render chips/boards | site pages | browser | display-only | none |
| T4.10 | engine/qbus_news_store.py:1976-2015 (news_flow read; published_at/received_at clocks :169-171, :403-415) → app/ticker_news.py:573-601 (_compute_flow; rights :578-583) | `now` (tz-aware, required :1997-2002) vs published/received clocks | per-security 24h/7d/28d report counts (ticker_news.flow.v1) | API response (ticker_news flow) | site ticker-news UI (site/ticker_news.js — templates/verify harness scripts/verify_ticker_news_stream_ui.py:681) | display-only | `NewsReadRights` source-rights + editorial-security gate (app/ticker_news.py:580-583; engine/qbus_news_store.py:1990) — ACCESS gate, not a signal gate |

---

## T5 — scripts/ builders that write news into site/*.json

| hop | source (path:line) | clock | transformation | output artifact | next reader(s) | AUTHORITY | gate |
|---|---|---|---|---|---|---|---|
| T5.1 | scripts/build_news.py:222-237 (GDELT ingest + qbus wire + narrative panel), :307-309 (by_ticker.json), :312-317 (macro/china/narrative.json), :324-328 (macro_releases.json) | per-feed fetched_at/asof + item timestamps | nightly news JSON side-artifacts | site/news/{financial,by_ticker,macro,china,narrative,macro_releases}.json | see T1.7, T1.8, T4.2-T4.3, T3.4, T4.9 | engine input (by_ticker/financial feed the bundle+hub); the rest display-only | never-darken guard keeps a healthier existing artifact (scripts/build_news.py:39-77) — a freshness/coverage guard, not a signal gate |
| T5.2 | scripts/build_intelligence.py:67-73 (bundle write :73; radar_news builder :37-65) | bundle as_of | unified 4-facet bundle + per-basket radar headlines | site/intelligence/by_ticker.json; site/basketdata/radar_news.json | T4.4-T4.9; templates/_radar_panel.html.j2:2 (radar_news via radar_panel.js) | engine input (bundle feeds the hub vote, T4.6) | single-writer discipline note (scripts/build_intelligence.py:10-16) — process rule, not a signal gate |
| T5.3 | scripts/build_briefing.py:27-33 | bundle as_of | ranked brain briefing | site/intelligence/briefing.json | T4.4-T4.5; Mastermind get_daily_briefing | research context | none |
| T5.4 | scripts/build_intel_hub.py:384-461 (hub.json :451, track_record :452 + data/hub persist :405-408, governor :414-421, china packet :185-292, page render :499-509) | hub as_of + `stamp_special_freshness` staleness aging (:76-126, called :385) | 5-desk command + falsifiable track record + governor persist | site/intel_hub/hub.json; site/intel_hub/track_record.json; site/intel_hub/regions/china.json; data/hub/{track_record,signal_governor}.json | T4.6-T4.7; Mastermind get_intel_hub; scripts/backfill_qledger_intel_hub.py:4 | engine input (hub command is a ranked scoring output) | `_STALE_SURFACE_DAYS = 3` staleness surfacing (scripts/build_intel_hub.py:39) — ages inputs loudly, does not block |
| T5.5 | scripts/build_china_news.py:1-4, :70-72 | feed as-of stamps | china news intel artifacts | site/chinanews/{sentiment,feed,by_ticker}.json | engine/china_intel_hub.py:138-140 (reader) | display-only | none |
| T5.6 | scripts/grade_news_events.py:3-28, :406 (reads event log), :482 (writes calibration) | event log PIT timestamps → forward-return windows | event-class forward-return calibration | site/news/calibration.json | scripts/build_site.py:7416-7431 (news page display, :7431) | research context (measured diagnostics, displayed) | none |

---

## T6 — readers of news_events / news_event_ledger / news_impact

| hop | source (path:line) | clock | transformation | output artifact | next reader(s) | AUTHORITY | gate |
|---|---|---|---|---|---|---|---|
| T6.1 | engine/financial_news.py:40 + engine/macro_news.py:346 (`from engine import news_events … # W2: event-identity layer (display-only)`) | item timestamps | event identity/classification enrichment of the displayed feed | display feeds (site/news/*.json items carry `event`) | build_news writers (T5.1); site pages | display-only (comment says display-only at both sites) | none |
| T6.2 | engine/news_ai_feed.py:249-254 (`classify_event` — "event identity feeds the display ranker") | item timestamps | AI-feed headline enrichment | AI feed display items | news display surfaces | display-only | none |
| T6.3 | engine/qbus_news_annotate.py:14 (classify_event into qbus annotations) | qbus received/published clocks (:169-171, :403-415) | annotation columns on qbus items | qbus store annotations | app/ticker_news.py API (T4.10) | display-only | qbus rights gate (T4.10) — access gate |
| T6.4 | scripts/build_news.py:369-416 (persist :395, :412) → engine/news_event_ledger.py:105 (persist_kept_events → data/news/event_log.parquet, :13, :110), :191 (persist_reject_sample → data/news/reject_sample.parquet, :14, :197) | `asof_utc` stamp + event classification metadata | PIT event log + reject-sample store (W4) | data/news/event_log.parquet; data/news/reject_sample.parquet | scripts/grade_news_events.py:3-28, :406 (T5.6/T6.5); engine/news_event_ledger.py:302-311 reader helpers | research context (PIT grading substrate) | none |
| T6.5 | scripts/grade_news_events.py:3-28, :406 (loads ledger), :482+ (emits calibration) | ledger event time → forward-return horizons | forward-return calibration per event class | site/news/calibration.json | scripts/build_site.py:7431 (display) | research context | none |
| T6.6 | engine/news_impact/producer.py:28-29, producer_facts.py:27-29, prophet_adapter.py:1-16 (`AUTHORITY = "context_only"` :34; "does not patch, import, or call any Prophet consumer" :11; `as_of` always derived from the fact's `source_available_at` (I10) :14-16) | fact `source_available_at` (I10) — no clock read, no model call (:15-16) | validated news_impact_event.v1 → prophet_evidence.v1 display-tier evidence records | prophet_evidence.v1 records (in-package; contracts/news_impact/prophet_evidence.v1.schema.json:5: "never originates a rank, size, gate, score, confidence, probability, price target or fair value") | NONE at BASE — the seam is unwired ("a later wiring PR may call" — prophet_adapter.py:10-11); no importer outside engine/news_impact/ (grep) | research context (display-tier evidence with zero consumers) | contract-level prohibition (contracts/news_impact/prophet_evidence.v1.schema.json:5) + in-code AUTHORITY stamp (prophet_adapter.py:34) |
| T6.7 | engine/china_national_team.py:362-364, :419, :445 (china_news_vector events) | `_eff` effective UTC column (:363-364) | state-media drumbeat / facility watch legs | national-team radar (context_only, :726) | china policy watch page | display-only | `may_originate=False, may_escalate=False` (:11, :726) |

Note: no Prophet/sector/rotation module reads news_events, news_event_ledger or news_impact at BASE
(`git grep -n -E "news_events|news_event_ledger|news_impact" -- engine scripts app`, excluding
engine/news_impact/ itself, returns only the hops above; the news_impact hits outside the package
are contracts/*.schema.json only).

---

## Mastermind consumers

Classified from the pasted EXCERPTS only (mastermind HEAD c7e47c859eb2925c5626931fd511800773ba09ac). Macro artifacts read, fields used, authority and gate per consumer. `mastermind:<path>:<line>` cites the excerpt as numbered.

| consumer | macro artifact(s) read | fields used | AUTHORITY | gate |
|---|---|---|---|---|
| get_intelligence (mastermind:brain/bot_mcp.py:336-351) | site/intelligence/by_ticker.json then data/intelligence/by_ticker.json (:338-339); fallback site/news/by_ticker.json + site/altdata/mastermind.json (:343-344) | `tickers[t]` whole record: news facet (n_recent, sentiment_lean…), alt facet (signal_score, action…), has_news/has_alt | research context (LLM tool; docstring: "CONTEXT-ONLY — informs conviction, never sizes alone" :330-334, :350-351) | docstring-level context-only contract; no code gate in the excerpt |
| get_daily_briefing (mastermind:brain/bot_mcp.py:380-394) | site/intelligence/briefing.json then data/intelligence/briefing.json (:382-383); fallback brain.intake.build (:390-391) | as_of, macro_context, n_actionable, n_divergences, priority_queue (priority/confidence/strength/lean/facts — which carry news via T4.3/T4.4), divergences | research context ("Context-only — a triage, never a position size" :377-378) | docstring-level contract; no code gate in the excerpt |
| get_intel_hub (mastermind:brain/bot_mcp.py:408-430) | site/intel_hub/hub.json then data/intel_hub/hub.json (:409-410) | command[] dossiers: composite_conviction, lean, n_confirm/n_dissent, flags, read, falsifier, macro_context, desks, sector_heat | research context ("context-only, never sizes" :406) | docstring-level contract; no code gate in the excerpt |
| _news_by_ticker (mastermind:portfolio/lenses.py:299-304) | site/news/by_ticker.json `tickers`, else data/news/by_ticker.json `tickers` (:302-303) | per-ticker news substrate dict | research context (lens substrate; consumed only by _news_row, below) | none in the excerpt |
| _news_row (mastermind:portfolio/lenses.py:307-330) | unified bundle's `news` sub-object (via _intelligence, :313) else _news_by_ticker (:313); fields n_recent, sentiment_lean, n_pos/n_neg, baskets, sectors, is_mag7 (:316-322) | builds a `news_flow` lens row with weight class "context" and direction from lean (:323-330) | research context ("CONTEXT-ONLY (display-only in the macro engine) — informs narrative/conviction, never drives size alone" :310-311) | lens weight class "context" passed to the matrix (:327-330); matrix-side fail-closed marker (next row) |
| lens assembly _name_rows (mastermind:portfolio/lenses.py:502-521) | news row `nw` (:507) alongside alt `ad` and flow `fl` (:506-508) | when per-name stockdata is ABSENT only context lenses exist → explicit sentinel row `"missing"` so synthesize() refuses to size up (:520-521) | research context | FAIL-CLOSED MARKER: "a lone context lens can NEVER earn a full-size buy" (:512-519); doctrine "one dim alone is forbidden" (:519) |

Mastermind docstrings naming macro modules absent at BASE:
- mastermind:portfolio/lenses.py:300-301 — `_news_by_ticker` docstring: "published by the macro engine (engine/news_signals)". `engine/news_signals.py` does NOT exist at BASE (`git cat-file -e HEAD:engine/news_signals.py` → fatal: path does not exist). The actual writer of site/news/by_ticker.json is engine/financial_news.py (:877-922) via scripts/build_news.py:307-309 (schema `news_flow.v1`).
- mastermind:portfolio/lenses.py:303 — fallback `data/news/by_ticker.json` has NO macro writer at BASE (grep over engine/scripts/app finds writers only of site/news/by_ticker.json; data/news/ holds only news_event_ledger's event_log/reject_sample parquets — engine/news_event_ledger.py:13-14). The fallback path is dead at BASE.
- mastermind:brain/bot_mcp.py:330 — "news_flow" names the lens/desk, not a macro module; no absent-module claim.

---

## Answers

**Q1 — Which news-derived values reach a scoring/ranking/sizing computation, and through which gate?**
- GDELT narrative velocity/acceleration → `fused_obs_z`/`obs_dir` in engine/theme_activity (T1.3→T1.4) — gated by the hard-source precondition (theme_activity.py:519-521; news weight 0.5, :69); then into radar divergence states (T1.5, display-stamped) and — via the radar track record — into the hub's de-escalation-only governor (T1.6, signal_governor.py:12-21).
- GDELT velocity → foresight earliness leg (T2.1) → foresight score/convergence and the foresight sizing-band `earliness_tilt` (T2.2→T2.3) — coverage floors only (foresight_earliness.py:52; foresight_sizing.py:262); the sizing output is stamped DISPLAY-ONLY guidance (foresight_sizing.py:11, :18, :273).
- Polygon news sentiment → alt-data weighted kernel at 0.20 (T3.11→T3.12) — no gate in macro; convergence_score feeds the intelligence bundle's alt facet (T4.3) and the Mastermind lens substrate.
- Editorial news flow → intelligence bundle brain-priority/agreement (T4.3) → hub composite_conviction/lean/opportunity as a VOTING desk (T4.6) — NO gate on the news leg (the A7 exclusion and the signal governor bind policy and radar respectively, intel_hub.py:89, :470, :563-564, :632-639).
- China news sentiment z → china conviction direction (T3.9) — the ONLY news→direction chain behind a real code gate: `_news_sign_proven` (china_intel_analysis.py:109-122, :197-206).
Program-law check: every scored destination above is a macro-internal research/display surface (radar, foresight desk, intel hub, alt-data desk); none writes an executed position size, and the artifacts are stamped context-only (theme_activity.py:35-36, radar.py:242/:254, intelligence.py:263, intel_hub.py:39-42). The one sizing-flavored consumer (earliness_tilt) is explicitly display-only guidance (foresight_sizing.py:11).

**Q2 — Which hops carry no clock, so availability-time cannot be enforced downstream?**
- T4.3/T4.4: the intelligence bundle and briefing stamp only build-day `as_of` (intelligence.py:262-264; briefing build) — per-headline publish times survive only inside `top[].published` copies; the aggregate fields the consumers rank on (n_recent, sentiment_lean/score, priority) carry NO per-item clock, so a stale-window aggregate is indistinguishable from a fresh one downstream.
- T1.4/T1.5: theme_activity/radar carry basket-level fused metrics with no per-event clock; radar stamps payload `as_of` only (radar.py:178).
- T2.2: earliness log rows stamp `asof`=date.today() + append-time `ts` (foresight_earliness.py:340, :385, :390-393) — the news leg's underlying event clock (first_seen_utc) is lost after the velocity aggregation (T2.1).
- T3.11/T3.12: polygon news_sentiment signals carry no explicit as-of field in the hop code cited (parquet series dates only) — recency enforcement is upstream collector discipline.
- T6.6 news_impact is the counter-example done right: `as_of` is always derived from the fact's `source_available_at` (prophet_adapter.py:14-16).
- qbus is the other clean chain: published_at/received_at/first_received_at (qbus_news_store.py:403-415) and CRAWL_BOUNDED honesty on the GDELT wire (news_vector.py:551, :581).

**Q3 — Which consumers read the legacy event ledger vs qbus vs news_impact, and does any read two of them for one fact?**
- Legacy PIT ledger (data/news/event_log.parquet): written by build_news (T6.4), read only by grade_news_events (T6.5) → site/news/calibration.json (display). No engine scoring reader.
- qbus store: read by app/ticker_news.py (T4.10) for the live ticker-news UI flow; fed by news_vector.ingest_to_qbus (T1.7) and the intraday intake; annotated via qbus_news_annotate (T6.3).
- news_impact: zero consumers outside its own package at BASE (T6.6).
- Double-read for one fact: YES, by design and documented — the GDELT narrative event reaches consumers twice: once via the parquet/`news_flow` scoring leg (T1.2-T1.4) and once via `ingest_to_qbus` as a qbus row (T1.7) — two representations of the same headline in two stores. Similarly the Mastermind bot can see the same editorial news twice: once in the unified bundle's `news` sub-object and once via the standalone site/news/by_ticker.json fallback (mastermind:brain/bot_mcp.py:338-348; mastermind:portfolio/lenses.py:313) — the fallback fires only when the unified bundle is absent, so not simultaneously. brain_market_intel merges the live wire with the nightly digests but orders them SOURCE-MAJOR and never cross-sorts scores, explicitly because "press salience and the news desk's importance/quality scores share a 0..100 range and nothing else" (engine/neuralweb/brain_market_intel.py:592-600) — a documented guard against blending the two pools into one fact.

**Q4 — Which site/*.json news artifacts have no in-repo reader (display-only by construction)?**
- site/news/narrative.json — written scripts/build_news.py:317; no in-repo reader found.
- site/news/china.json — written scripts/build_news.py:315; no in-repo reader found.
- site/news/macro.json — in-repo consumer is only the brain LLM top-up (brain_market_intel.py:473, :502, :595) and the news page; no computation reads it.
- site/basketdata/radar_news.json — read only client-side by radar_panel.js (templates/_radar_panel.html.j2:2).
- site/news/calibration.json — read only by build_site for display (scripts/build_site.py:7431).
(Readers determined by repo grep at BASE; absence of an in-repo reader is repo-relative, not a claim about the rendered site's JS beyond the templates cited.)

**Q5 — Where does the Mastermind side treat news as context-only, and where (if anywhere) can it move size?**
- Context-only everywhere, by explicit docstring contract: get_intelligence ("never sizes alone", mastermind:brain/bot_mcp.py:334, :350-351), get_daily_briefing ("a triage, never a position size", :377-378), get_intel_hub ("context-only, never sizes", :406), _news_row ("never drives size alone", mastermind:portfolio/lenses.py:310-311).
- The structural backstop is the lens matrix: news enters `_name_rows` only as a "context"-weight row (mastermind:portfolio/lenses.py:327-330), and when stockdata is absent the matrix stamps a "missing" sentinel so synthesize() refuses to size up — "a lone context lens can NEVER earn a full-size buy" (:512-519).
- Nowhere in the excerpts can news move size: no sizing function reads a news field; the sizing path (trend/valuation/quality rows) reads stockdata tech/valuation blocks (mastermind:portfolio/lenses.py:333-345, :531-537). The residual risk D2 must weigh is influence-not-size: news raises `priority`/`composite_conviction` (macro T4.3/T4.6), which steers the brain's ATTENTION (where it spends depth), and the Mastermind side's own note concedes it "informs conviction" (:334) — attention-steering, not sizing, is the live channel.

---

## Authority summary

| artifact | strongest authority reached (chain) | gate or none |
|---|---|---|
| data/news_vector/events.parquet | engine input (T1.1→T1.4 scoring leg) | none |
| news_flow.theme_flow metric | engine input (T1.3) | none at hop; gated at fusers |
| fused_obs_z / obs_dir (theme_activity) | gated engine input (T1.4) | hard-source precondition (theme_activity.py:519-521) |
| site/basketdata/radar.json | display-only (T1.5) | is_context_only stamp (radar.py:242, :254) |
| radar ledger → governor trust → hub opportunity | gated engine input (T1.6) | signal governor de-escalation-only (signal_governor.py:12-21; applied intel_hub.py:632-639) |
| qbus news store / ticker_news flow API | display-only (T1.7, T4.10) | access-rights gate only (app/ticker_news.py:580-583) |
| site/news/narrative.json, site/news/china.json | display-only (T1.8, T5.1) | none (no in-repo reader) |
| data/foresight/earliness_log.jsonl | engine input (T2.2→T2.3) | nightly-lane write gate (foresight_earliness.py:404-409); LEG_MIN_COVERAGE floor (:52) |
| foresight size_mult (earliness_tilt) | engine input (T2.3) — sizing computation, output display-only | coverage floor n_live≥2 (foresight_sizing.py:262) |
| frbsf news_sentiment in conditions payload | research context (T3.3) | structural exclusion from roro (conditions.py:822-823) |
| risk-radar news_tone chip / ignition radar | display-only (T3.5) | none (label taxonomy; ignition "never fused into any cross-channel score", ignition_radar.py:6-7) |
| china news sentiment direction | gated engine input (T3.9) | `_news_sign_proven` sign gate (china_intel_analysis.py:109-122, :197-206) |
| site/altdata/{by_ticker,mastermind}.json (news channel 0.20) | engine input (T3.12) | none in macro |
| site/news/by_ticker.json | engine input transit (T4.2→T4.3→T4.6) | is_context_only stamp (build_news.py:307-308) |
| site/intelligence/by_ticker.json | engine input (T4.3; hub vote T4.6) | none (is_context_only stamp only, intelligence.py:263) |
| site/intelligence/briefing.json | research context (T4.4) | none |
| site/intel_hub/hub.json | engine input (T4.6 — ranked scoring output; Mastermind reads context-only) | none on the news leg (A7 binds policy; governor binds radar — intel_hub.py:89, :632-639) |
| us_prophet_rank hub_* columns | research context (T4.7) | zero-authority preregistration ladder (us_context_vector.py:8-13) |
| data/news/event_log.parquet (+ calibration) | research context (T6.4-T6.5) | none |
| news_impact prophet_evidence | research context (T6.6) — zero consumers at BASE | contract prohibition + AUTHORITY=context_only (prophet_adapter.py:34) |
| Mastermind news surfaces (tools + lenses) | research context (Mastermind section) | docstring context-only contracts + fail-closed context-lens marker (mastermind:portfolio/lenses.py:512-519) |

## GAPS / UNRESOLVED

- None UNRESOLVED. Two citations warrant care in D2: (1) the stale `engine/real_activity.py` pointer in engine/news_flow.py:9 (implementation is theme_activity.compute_real_activity); (2) the Mastermind docstring module `engine/news_signals` (mastermind:portfolio/lenses.py:300) and the `data/news/by_ticker.json` fallback (lenses.py:303) both reference things that do not exist at BASE.
- app/ and templates/ JS were grepped, not executed; client-side reads are cited from templates/*.j2 and builder comments (radar_panel.js itself is generated/served, its read set documented at templates/_radar_panel.html.j2:2).

## Seat adjudication 2026-10-31

Adjudication by the News Intelligence Estate seat (602cd180) under the Chairman completion directive of 2026-10-31. It names the first real consumer and the first product proof the estate is measured against. The trace T1–T6 above stays as written at BASE 64ef5131; this section adds pointers only.

**FIRST REAL CONSUMER — the Mastermind boundary.** The estate's first real consumer is Mastermind's read of the two Macro per-ticker artifacts through `brain/bot_mcp.py` `get_news` / `get_intelligence` and `portfolio/lenses.py`. The consumer-side freshness work is being built by ORCH-2 (the seat's consumer orchestrator, running on 2026-10-31); it is not part of this PR and is not landed by it.

| side | pointer (`file:function`) | revision |
| --- | --- | --- |
| Macro producer, news flow | `scripts/build_news.py:build` writes `site/news/by_ticker.json` (`news_flow.v1`, `is_context_only: true`) from `engine/financial_news.py:mastermind_by_ticker` | macro main `f2efb8ba` |
| Macro producer, intelligence bundle | `scripts/build_intelligence.py:build` writes `site/intelligence/by_ticker.json` | macro main `f2efb8ba` |
| Mastermind MCP read | `brain/bot_mcp.py:get_news` (l.322) reads `site/news/by_ticker.json`, falling back to `data/news/by_ticker.json`; context only, never sizes alone | Mastermind master `bb85b429` |
| Mastermind MCP read | `brain/bot_mcp.py:get_intelligence` (l.341) reads `site/intelligence/by_ticker.json`, falling back to `data/intelligence/by_ticker.json` | Mastermind master `bb85b429` |
| Mastermind portfolio lens | `portfolio/lenses.py:_intelligence` (l.212), `_news_by_ticker` (l.299), `_news_row` (l.307), `_name_rows` (l.502) | Mastermind master `bb85b429` |

**FIRST PRODUCT PROOF — the Terminal authenticated R2 rail.** The first product proof is the authenticated Terminal ticker-news rail that carries the R2 evidence ladder: `terminal/components/news/TickerNewsPanel.tsx:TickerNewsPanel` (mastermind-terminal #1111, merged 2026-10-22 at `58c44ed9d6c1`; R2 lexicon #1110 at `ca8347f8230c`; R2 e2e cells and crops #1128 at `c78b705d56e8`). That proof belongs to a later seat orchestrator (ORCH-4). A source merge of #1110/#1111/#1128 is not installed or production proof. The Terminal BFF route that serves the rail was not read for this section and is left for ORCH-4 to bind.

Neither consumer gains sizing or trading authority from news, sentiment or LLM output: the news-flow artifact is published `is_context_only: true`, and `get_news` informs narrative only.
