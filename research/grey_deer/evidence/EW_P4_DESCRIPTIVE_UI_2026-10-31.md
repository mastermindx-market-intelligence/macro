# EW-P4.T1 — Descriptive early-warning observation UI (product A) — evidence record

Date: 2026-10-31 · Program: Grey Deer × Leadership Rotation Early-Warning (#10219) · Wave EW-P4.T1
Branch: `claude/gd-ew-p4-descriptive-early-warning-ui-20261031b` · Base: `1d253e1d25f22c61d1bcf8126b13b0229f26ccbd`
Evidence pack: `research/evidence/ew_p4_descriptive_ui_20261031/` (shots, contact sheets, `receipt.json`)

## What this change is

A consumer-only, descriptive rendering of the frozen `macro.rotation_observation.v1`
observation (`lib/rotation_observation_notification.py`) in two existing hosts:

- **Risk Radar envelope inset** (`#risk-envelope-band` inside `#dlg-risk` on `site/macro.html`):
  a GLANCE line set, a BRIEF drawer (`details.gde-disc`) and a STUDY disclosure
  (`details.gde-ew-study`), server-rendered by `templates/_risk_envelope_band.html.j2`
  from the optional view `risk_envelope.rotation_context.latest_observation`.
- **Sector Central, What's Moving view** (`#rc-early-context` under `#rc-events-mount` on
  `site/sector_central.html`): the same glance/brief/study copy, rendered client-side by
  `ewGlanceHtml()` in `templates/rotation_events.js` (byte-copied to `site/rotation_events.js`)
  from `marketdata/rotation_events.json` `early_context.latest_observation`, prepended to the
  existing early-context card without altering it.

Both mirrors validate the wrapper against the lib contract (V1–V7) plus the stricter engine id
rule (`rotobs_` + 40 lowercase hex) and apply one state precedence. Envelope verdicts
(measured trend, transition fragility, leadership) never feed the observation state: a quiet
headline cannot hide a qualified observation and a fragile one cannot create it.

**Forward-only consumer contract.** No producer writes `latest_observation` today. Recording
stays behind `ROTATION_OBSERVATION_RECORDING_ENABLED` (off) in
`scripts/build_rotation_events.py`, and no builder copies an observation into the envelope or
into `rotation_events.json`. Until one does, both hosts render the scoped
"Rotation data unavailable" state in production. The qualified states in the evidence pack
come from synthetic fixtures in `tests/fixtures/ew_p4_observation/`.

## Census map and chosen hosts

<!-- CENSUS MAP: inserted by orchestrator -->

The read-only census (lane GD-EW-P4-C1, repo HEAD `b38935afc1a5`) mapped these facts:

| Question | Finding | Consequence for the build |
|---|---|---|
| Q1 Radar inset | `templates/dashboard.html.j2:13091` includes `_risk_envelope_band.html.j2` inside `#dlg-risk` (`.mx5-dlg-body`); the inset is server-rendered from vm `risk_envelope` (`scripts/build_site.py:7395–7414`); the only client fetch is the live overlay `live/risk_envelope.json` | Host the Radar glance in the band template, read from the vm; no new fetch, no new panel; the existing `#gde-rotation-context` stays |
| Q2 Sector Central | Movement lives in the lazy `moving` view (`templates/si_workspace.js:101`); `rotation_events.js` mounts into `#rc-events-mount` (`sector_central.html.j2:2598`) | Host the SC glance inside the existing early-context card output; no new section |
| Q3 `rotation_events.js` | `earlyContextHtml()` renders `#rc-early-context` from `marketdata/rotation_events.json` | Add `ewGlanceHtml()` next to it and prepend its output; `earlyContextHtml()` output is unchanged |
| Q4 template→site copy | Plain byte copy (`lib/site_assets.py:135–152`, `scripts/build_sector_central.py:603–617`), CI job `template-site-sync` | Edit the template; byte-copy to `site/`; `check_template_site_sync` stays green |
| Q5 P0B pins | `mockups/evidence/prophet-p0b-zero-fouc/mobile-layout*.json` pin `_risk_radar_card.*` and `_risk_radar_dlg.*`; the band template, `rotation_events.js`, `dashboard.html.j2` and `sector_central.html.j2` are not pinned | Touch none of the pinned paths, so no receipt re-mint is needed |
| Q6 i18n | Both languages ship in the DOM (`.l-en`/`.l-zh`, `theme.css:582–583`); no string catalog | Every new string is a paired span; no `title=` copy |
| Q7 tokens/doctrine | `theme.css` tokens; `docs/DESIGN_DOCTRINE.md:106–118` forbids colored container edges | Tokens only, even borders, `:focus-visible` outlines; the pre-existing `.rc-ec-stale`/`.rc-ec-conflict` edge stripe was also repaired |
| Q8 test harness | pytest + node `--test` + playwright probe; CI registration in `.github/ci/legacy-jobs.yml` | pytest registered in `dashboard-render-contract`, node test in `ratio-lens` |
| Q9 `rotobs_` | Ids are minted only by `engine/rotation_events.py:2389–2395`; no site JSON exposes them | Consumer contract is forward-only (above) |
| Q10 envelope feed | `site/riskdata/risk_envelope.json` carries `source_session`, `data_state`, `freshness`, `policy_summary`, `produced_at` | The "how current" line reads source session, availability and quality first; build time is secondary |

## Consumer contract latest_observation (forward; no producer in this change)

Frozen build packet §A, verbatim. The validation mirror V1–V8 is implemented identically in
`templates/_risk_envelope_band.html.j2` and in `ewGlanceHtml()` in `templates/rotation_events.js`.

```text
§A Consumer contract `latest_observation` (one shape, both hosts).
Location: Radar reads `risk_envelope.rotation_context.latest_observation`; Sector Central reads `<rotation_events.json>.early_context.latest_observation`. Missing/null => no observation.
Shape (a "view wrapper" around the frozen notification payload):
{
  "schema": "rotation_observation_view/v1",
  "notification": { exact macro.rotation_observation.v1 payload: source, category, authority, kind, observation_id, previous_observation_id, pair_id, num, den, event_as_of, source_as_of, observed_at, not_after, values{sessions, numerator_return_pct, denominator_return_pct, ratio_return_pct} | null },
  "window_2s": {"start": "YYYY-MM-DD", "end": "YYYY-MM-DD"} | null,
  "horizon_20s": {"sessions": 20, "start": "YYYY-MM-DD", "end": "YYYY-MM-DD", "numerator_return_pct": n, "denominator_return_pct": d, "ratio_return_pct": r} | null,
  "basis": "dividend_adjusted_close",
  "availability": {"status": "VERIFIED"|"UNKNOWN", "available_at": iso|null},
  "coverage": {"registered_pairs": int, "evaluable_2s": int, "missing_pair_ids": [str]},
  "lineage_roots": [str],
  "previous": {"observation_id": str, "observed_at": iso, "values": {...same shape...} | null} | null
}
Validation MIRROR (implement identically in Jinja and JS; it mirrors lib/rotation_observation_notification.py:258-367 `validate()` plus one stricter id rule):
 V1 notification is an object; source == "macro.rotation_observation.v1"; category == "sector_rotation_relative"; authority == "notification_only".
 V2 kind in {observed_change, reversal, correction, data_withdrawal}.
 V3 observation_id matches ^rotobs_[0-9a-f]{40}$ (stricter than lib, as the engine mints it: engine/rotation_events.py `"rotobs_" + digest(identity)[:40]`); previous_observation_id null or same pattern; previous required unless kind == observed_change; previous != observation_id.
 V4 num, den match ^[A-Z0-9][A-Z0-9.^=-]{0,19}$ and num != den; pair_id non-empty string <= 128 chars.
 V5 event_as_of matches ^\d{4}-\d{2}-\d{2}$; observed_at and not_after are UTC ISO strings (`+00:00` or `Z` suffix) and not_after[:19] > observed_at[:19] after normalizing `Z` to `+00:00`.
 V6 measured kinds (all but data_withdrawal): source_as_of == event_as_of; values is an object with sessions === integer 2 (not boolean); the three returns are finite numbers (not boolean, not NaN, |x| < 1e12); numerator and denominator > -100; |((1+n/100)/(1+d/100)-1)*100 - r| <= 1e-6.
 V7 data_withdrawal: values === null; source_as_of null or <= event_as_of.
 V8 window_2s / horizon_20s, when present, must be well-formed (dates, sessions 20, finite returns, same identity check within 1e-6); a malformed one is treated as ABSENT (partial), not as a malformed observation.
```

- **Stricter id rule.** V3 requires `^rotobs_[0-9a-f]{40}$`, which is stricter than the lib's own id check.
  It matches how the engine mints ids (`engine/rotation_events.py`: `"rotobs_" + digest(identity)[:40]`).
  A lib-valid notification with another id form renders `unreadable`.
- **Explicit keys (review r1).** Both mirrors also carry the lib's explicit-key rule
  (`lib/rotation_observation_notification.py:306`): `source_as_of` and `values` must be present as keys,
  even when null for a withdrawal. A notification missing either key renders `unreadable` in both hosts.
- **Present non-object wrapper (review r1).** A `latest_observation` that is present but is not an object
  (a string, a list, a number or a boolean) fails V1 and renders `unreadable`. It is not treated as absent. Only a
  missing or null `latest_observation` is "no observation".

## State precedence

Frozen build packet §B, verbatim. Jinja and JS apply the same first-match order.

```text
§B State function (same precedence in Jinja and JS; first match wins). `session` = Radar: risk_envelope.source_session; Sector Central: rotation_events.json `as_of`.
 1 no latest_observation:
   - rotation context missing/not an object -> `unavailable`
   - Radar: rotation_context.coverage == "STALE" or rotation_context.as_of < session -> `stale` (uses rotation_context.as_of). Sector Central: early_context missing or the existing stale rule in earlyContextHtml (STALE_DAYS) fires -> `stale`.
   - else -> `unavailable`
 2 present but fails V1-V7 -> `unreadable`
 3 event_as_of > session (future) -> `unreadable`
 4 kind data_withdrawal -> `withdrawn`
 5 event_as_of < session -> `stale` (show the observation date; glance shows NO return numbers)
 6 kind correction -> `corrected`
 7 window_2s absent/malformed, or window_2s.end != event_as_of, or horizon_20s absent/malformed -> `partial` (reasons list; if the window is absent or mismatched, WITHHOLD legs and ratio)
 8 horizon_20s present and sign(ratio 2s) != sign(ratio 20s) (zero counts as its own sign) -> `conflicting`
 9 kind reversal -> `reversal`; else -> `observed`
 Envelope verdicts (measured_state, hazard_summary, leadership cohort) NEVER change this state: a quiet market must not hide a qualified observation; a fragile market must not create one.
```

## Rubric row → assertion / shot

Test files: `tests/test_ew_p4_descriptive_ui.py` (pytest, Jinja host) and
`tests/ew_p4_glance_ui.test.cjs` (node, Sector Central host). Shots are named
`<surface>-<family>-<lang>-<theme>-<width>.png`.

| Exercise (§7) | Assertions | Shots | Judged |
|---|---|---|---|
| Five-second glance — scope, what changed, what is uncertain; source age identifiable | pytest: `test_five_second_glance_structure`, `test_journey_c_exact_stale_strings`, `test_quality_and_build_time_are_separated`, `test_state_matrix_words_and_attribute`; node: EN and ZH state words on the glance | Radar observed + stale and SC observed, full 36-cell matrix | Glance names the scope (US Technology leadership), the state word, the sentence, then source session, availability and quality ahead of build time; no calm or crash wording |
| Side-by-side ratio — which leg gained or lost absolutely; what relative outperformance means | pytest: `test_side_by_side_ratio_legs_table`, `test_side_by_side_ratio_partial_window_mismatch_withholds_numbers`; node: legs withheld on a window mismatch, single both-fell sentence | Radar and SC observed (journey B, both legs fell) | Both legs are shown with their own signs and the sentence says both fell; the relative figure is never called a gain or an inflow |
| 2S vs 20S — why a short-term shift might not be durable; conflict not colour-only | pytest: `test_two_session_vs_twenty_session_horizons`, `test_sessions_must_be_an_integer_not_a_float`; node: conflicting horizons carry the conflict sentence as text | `radar-conflicting-en-dark-390.png` | Both horizons are listed; conflict is a state word plus a text sentence |
| Consent/revocation | pytest: `test_no_consent_or_revocation_controls`; node: no title= attributes and no consent controls | — (absence) | Product A sends nothing, so there is no subscription to bundle or hide; the absence is asserted |
| Correction history — what was first issued and what changed later; no backdating | pytest: `test_correction_history_original_and_corrected`, `test_withdrawal_keeps_original_and_hides_current_values`; node: correction and withdrawal keep the original in history | `radar-corrected-en-dark-390.png`, `radar-withdrawn-en-dark-390.png`, `sc-corrected-en-dark-390.png`, `sc-withdrawn-en-dark-390.png` | The original record stays in history with its own time; a withdrawal hides current values |
| Portfolio context — informational vs authorized policy; no execution or sizing implied | pytest: `test_portfolio_context_forbidden_language_scan`, `test_policy_footer_keeps_w9_fact_and_adds_not_an_all_clear`; node: no forecast/odds/sizing language in the rendered glance | Radar policy footer in every Radar shot | The policy footer keeps the capital-restriction fact and adds "This is not an all-clear"; the observation copy carries no trade, sizing or odds wording |
| Partial and offline — what is still known; stale or empty never reads as calm; skeleton never clears | pytest: `test_partial_renders_sentence_and_warn_word`, `test_unavailable_and_unreadable_render_sentence_and_warn_word`, `test_stale_never_uses_the_neutral_surface`, `test_unavailable_caveat_only_when_no_qualified_observation`, `test_quiet_headline_does_not_suppress_qualified_observation`, `test_fragile_headline_does_not_create_an_observation`; node: loading shell says Checking, fetch/parse failure is scoped unavailable, missing context unavailable, aged context stale | `radar-partial-en-dark-390.png`, `radar-unavailable-en-dark-390.png`, `radar-unreadable-en-dark-390.png`, `sc-stale-en-dark-390.png`, `sc-unreadable-en-dark-390.png`; Radar stale matrix | Every degraded state is a scoped sentence on the warning surface with a warning word |
| Cross-product handoff — the same qualified event, not a silent merge | pytest: `test_cross_product_handoff_study_link_and_no_delivery_claim`, `test_routes_land_on_the_registered_sector_central_hash`, `test_contract_parity_with_lib_validator`, `test_contract_parity_malformed_id_is_lib_valid_but_ui_unreadable`, `test_state_parity_rendered_state_matches_expected`; node: state parity against expected.json, stricter id rule | Study disclosure (observation id, stable link) in Radar and SC observed shots | Both hosts render the same observation id and state for every fixture; the Terminal/Market View side is EW-P4.T2 and out of scope |
| Design doctrine (CLAUDE.md, DESIGN_DOCTRINE.md) and evidence binding | pytest: `test_css_no_edge_stripe_no_color_literal_focus_visible`, `test_bilingual_spans_paired_and_no_title_attributes`, `test_receipt_shots_depict_the_source_under_test`; node: pre-existing rc-ec edge stripe repaired, rc-ew uses even borders | all 46 shots | No accent stripe, no new header, no colour literal; paired EN/ZH spans; shots bound to the tested source |

## States

| State | Radar (Jinja) | Sector Central (JS) | Shot |
|---|---|---|---|
| observed | journey B both fell, observed rise | same fixtures | 12 shots (`radar-observed-<en|zh>-<dark|light>-<1280|390|320>.png`), 12 shots (`sc-observed-<en|zh>-<dark|light>-<1280|390|320>.png`) |
| reversal | reversal fixture (test only) | reversal fixture (test only) | — (test only) |
| conflicting | 20-session conflict | 20-session conflict | `radar-conflicting-en-dark-390.png` |
| partial | missing 20-session, window mismatch (ratio withheld) | same fixtures | `radar-partial-en-dark-390.png` |
| stale | aged observation; journey C stale envelope | aged observation or aged early context | 12 shots (`radar-stale-<en|zh>-<dark|light>-<1280|390|320>.png`), `sc-stale-en-dark-390.png` |
| withdrawn | withdrawal keeps the original, hides current values | same | `radar-withdrawn-en-dark-390.png`, `sc-withdrawn-en-dark-390.png` |
| corrected | correction note, original kept in history | same | `radar-corrected-en-dark-390.png`, `sc-corrected-en-dark-390.png` |
| unreadable | malformed id, ratio or future time | same, plus the stricter `rotobs_` id rule | `radar-unreadable-en-dark-390.png`, `sc-unreadable-en-dark-390.png` |
| unavailable | no observation in the envelope | missing early context or fetch/parse failure | `radar-unavailable-en-dark-390.png` |
| loading | n/a (server-rendered) | shell says "Checking" before the fetch | — (node test) |

A skeleton/loading shell says "Checking" and never a calm word. A stale input is shown as
scoped unavailability ("Rotation data unavailable for Oct 30; latest is Oct 20.") on the
warning surface, never on the neutral surface.

## Shots and receipt

- **46 shots** in `research/evidence/ew_p4_descriptive_ui_20261031/shots/`, listed with sha256 in `research/evidence/ew_p4_descriptive_ui_20261031/receipt.json`.
- Matrix: Radar stale, Radar observed and Sector Central observed × EN/ZH × dark/light × 1280/390/320 (36 shots); state shots at EN/dark/390: radar/conflicting, radar/corrected, radar/partial, radar/unavailable, radar/unreadable, radar/withdrawn, sc/corrected, sc/stale, sc/unreadable, sc/withdrawn.
- Contact sheets: `contact-radar-observed.png`, `contact-radar-stale.png`, `contact-sc-observed.png`, `contact-sc-states.png`.
- `source_revision` `5bb16bdbe145208c8e7a5d2395a579e2f2c01a07` is the commit on this branch that the shots were rendered from (local Playwright Chromium, static harness, synthetic fixtures, every request served locally or aborted).
- `pr_source_equivalence` lists 19 render inputs with git blob ids at `source_revision` and on the branch (all equal). `test_receipt_shots_depict_the_source_under_test` re-checks those blob ids against the tested tree, every shot's sha256, the 36-cell matrix, no horizontal overflow and no page errors.
- `production_authenticated: false`; capture mode `dialog_unclipped_static_harness` (#dlg-risk rendered in normal flow with its max-height/overflow removed so the whole band is captured; live dialog scrolls).
- Every shot was opened and judged by the orchestrator (ORCH-P4b) in side-by-side strips per family. After repair wave C the set was re-rendered at the repair commit, and the shots whose content changed (Sector Central ZH study rows, correction and withdrawal history in both hosts, Sector Central stale) were opened and judged again.
- **Review r1 re-render.** After the review r1 repairs the whole set was re-rendered at the repair commit, and every shot whose bytes changed was opened and judged again. The open study disclosures now show the observation id in the mono token face.

## Not claimed

- **No forecast, delivery or sizing.** The copy is descriptive (watch/context only). There is
  no forecast, hazard, odds, probability, sizing, trade or activation language, and no
  subscribe/notify/consent control. Nothing is sent, scheduled or recorded.
- **No producer.** `latest_observation` is a forward-only consumer contract. Observation
  recording stays off, and no current build emits an observation into either host.
- **Not production-authenticated.** All qualified states are synthetic fixtures rendered in a
  static harness. The receipt says `production_authenticated: false`.
- **Separate work.** EW-P4.T2 (Terminal / Mastermind consumer) and EW-P4.T3 (exposure context)
  are not part of this change.
- **Not a statistical claim.** The 2-session and 20-session horizons are displayed facts from
  the observation record, not a validated signal.

## Deviations

- **Harness, not production.** Both hosts render in a static harness. The Radar dialog is shown in normal flow with its height clip and closed-state opacity removed so the whole band is captured; the live dialog scrolls.
- **Harness canvas.** Both harness pages carry the host pages' body rule (`background: var(--bg)`, `color: var(--text)`). A first render without it painted the dark Sector Central canvas white, so the translucent observation surface was illegible; those shots were discarded and re-rendered.
- **Shot provenance.** Fabric lane gd-ew-p4-4 wrote the probe repairs (unclipped band, open disclosures, agreeing early-context pair). Its shots were not kept; the committed shots were rendered locally at `source_revision`.
- **Sector Central harness pair.** For a qualified observation the harness gives the pre-existing early-context card one registered 2-session pair that agrees with the observation. Withdrawn, unreadable and mismatched states get no pair row.
- **Doctrine repair.** The pre-existing `.rc-ec-stale` / `.rc-ec-conflict` edge stripe on the early-context card was replaced by even borders and token surfaces.
- **Links.** The in-card "Review what changed" link targets `#rc-events-mount`; the Radar study link lands on Sector Central's registered hash route.
- **CI scope.** `dashboard-render-contract` now also owns `templates/si_workspace.js` (read by the route test), the evidence directory and the probe.
- **Base.** The branch stays on `1d253e1d`; `main` has moved since and is merged only if CI needs it.
- **Repair wave C.** Shot judgment found the Sector Central correction row running the original and corrected values together, four Sector Central study rows (source timestamps, coverage, immutable reference, rotation context) in English only under ZH, and record-supplied strings inserted without escaping in both hosts. All three were fixed (separate lines, paired EN/ZH rows, escaped sinks) and are asserted by the node and pytest wave-C tests, which fail on the pre-repair sources.
- **Capture artifact.** The site-wide aurora backdrop in `templates/theme.css` is a fixed, full-viewport layer. Element shots taller than the 1000 px capture viewport show its lower edge as a faint step behind the translucent Sector Central surface (dark shots, about 1000 px down). A live browser keeps the layer pinned to the viewport, so no reader sees that step.
- **Accepted limitation.** The Radar policy footer's state, count and sentence spans have no separators in the base markup, so the line reads as one run. That markup predates this change and is left as is.
- **Accepted limitation.** Below the new glance, the pre-existing Sector Central events list still prints both its not-an-all-clear sentence and "No active rotation events — quiet state is a valid state", and the early-context card keeps its English status enums (`VERIFIED`, `UNKNOWN`) under ZH. Both predate this change.
- **Review r1 repairs (F1–F5).** Independent lane gd-ew-p4-r1 (REQUEST_CHANGES on `dae8ba64`) found five gaps, all repaired. F1: `site/rotation_events.js` was not byte-copied after wave C; it is copied again, and a pytest now asserts byte identity. F2: both mirrors now require explicit `source_as_of` and `values` keys (lib:306). F3: a present non-object wrapper is `unreadable`, not `unavailable`. F4: the study id is set in `var(--font-mono)`. F5: this record now carries the §A contract, the §B precedence and the census marker. The r1 node test and seven of the ten r1 pytest cases fail on the pre-repair sources; the other three pin behaviour that was already correct.
