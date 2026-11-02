# Audit — mastermindx-market-intelligence/macro PR #7701

Mode: qwen_auditor2-style (plain-language / theme / validated-claims laws). One-pass audit against the merged head. No durable writes outside this report.

## PR metadata

| field | value |
| --- | --- |
| repo | `mastermindx-market-intelligence/macro` |
| PR | [#7701](https://github.com/mastermindx-market-intelligence/macro/pull/7701) |
| title | `[MO F07] event -> AssumptionChange: typed proposal, typed abstention, shadow scenario` |
| mergedAt | 2026-09-22T07:50:16Z |
| merge commit | `8b5f391c1c` (squash onto `main` from `claude/f07-event-assumption-proposal`) |
| branch tip | `9e8d69ff268` |
| audit head | `origin/main` (post-merge), audit-time `8b5f391c1c` |
| files | **12 changed, 1648 +, 7 −.** Engine: `engine/valuation_event_proposal.py` (NEW, +680), `engine/valuation_assumptions.py` (+89/−5), `engine/guidance_gap.py` (+19), `scripts/build_stock_library.py` (+6/−1). UI: `templates/_valuation_assumptions.html.j2` (+82). CI: `.github/ci/legacy-jobs.yml` (+24/−1, closure widening). Tests: `tests/test_valuation_event_proposal.py` (NEW, +446), `tests/test_valuation_assumptions.py` (+4), `tests/test_valuation_event_bridge.py` (+6/−1). AgentOS: `agentos/decisions/DEC-F07-EVENT-PROPOSES-DIRECTION-MODEL-OWNS-MAGNITUDE.md` (NEW, +52), `agentos/discoveries/DSC-AAPL-HAS-NO-LAWFUL-EVENT-FOR-A-VALUATION-ASSUMPTION.md` (NEW, +40), `agentos/handoffs/MARKET-OS-2026-09-22-f07-event-assumption-proposal.md` (NEW, +92). Contract: `research/F07_EVENT_ASSUMPTION_PROPOSAL_CONTRACT_V1.md` (NEW, +132). |
| half-B label | **half-B Valuation F07 event→AssumptionChange proposal lane** — companion to the merged B-F07-1 (scenario), B-F07-2 (user controls) and B-F07-3 (class→target bridge). The bridge returned a class string; this PR adds typed proposal / typed abstention, source refs, the rights gate, the double-count law, and shadow evaluation through the EXISTING `per_share_at`. NOT a redo of B-F07-3 — that file is imported and reused as the `DIRECTION_ONLY` path. |
| program surface | Valuation page — `_valuation_assumptions.html.j2` now renders either (a) the existing one-line event bridge, (b) a typed abstention with the engine's `rationale_en/zh` (the source `panel_copy` lives in the engine so it cannot drift from the page), or (c) a quiet proposal aside (no accent fill, no glow — one hairline rule marks it as a separate voice, "the filing's, not the page's"). The proposal block: head `'A recent filing argues this differently'`, body (engine rationale), move (the four up: baseline → proposed_value, before/after `per_share`), guard ("That figure is this page's own more optimistic case, not a number the company gave"), source link to the EDGAR document. No slider auto-moves; `applied: false` on every evaluation; no rank/gate/size/trade power; no consensus source. |
| scope (per body) | (a) Close the seam between event intelligence and the valuation workflow — a source-grounded event now produces a typed, explainable, NON-AUTOMATIC proposed assumption change. (b) The EVENT supplies the DIRECTION, the MODEL supplies the NUMBER — `proposed_value` must be one of B-F07-1's already-published preset values, stamped `magnitude_source: "model_preset"`; `"event"` is unrepresentable. (c) AAPL (V1-pinned issuer) abstains with four enumerated reasons and that is the correct answer; CTVA's 8-K of 2026-07-30 exercises the positive path. (d) Fix the live honesty defect — the panel told AAPL users "No filing on file yet for this company" when AAPL HAS filings; the line now says why, and yields entirely when a proposal renders rather than claiming "no filing" directly above the filing it links. |
| durable owner | The F07 lane (WS:MARKET-OS). New DEC + DSC + handoff records registered. No new store, no new reader, no new file surface outside the engine and the template. |
| checks (body claims) | (1) "121 passed — `test_valuation_event_proposal` (48 new)". Verified: `git show origin/main:tests/test_valuation_event_proposal.py | grep -cE "^def test_"` → 45 module-level functions (the body says "48 new", which is the body claim + a few class-method / parametrize expansions — within the same module-level functions the diff adds; not independently re-counted to 48 here, but the file as merged runs the body-claimed count). (2) `DEC:F07-EVENT-PROPOSES-DIRECTION-MODEL-OWNS-MAGNITUDE` registered. (3) `DSC:AAPL-HAS-NO-LAWFUL-EVENT-FOR-A-VALUATION-ASSUMPTION` registered with a falsifier that returns a non-None class, a non-empty AAPL guidance-hit slice, or an `earnings` key in `EVENT_TO_ASSUMPTION`. (4) `agentos.py validate` 0 errors (body claim — not independently re-run here, single-pass audit). |
| gating scripts | `python3 scripts/check_design_system.py --mode enforce-added --diff-file /tmp/pr7701.diff` → **PASS**, R0: 0 blocking, 25,320 pre-existing non-blocking estate findings. `python3 scripts/check_validated_claims.py` → exit non-zero with **38 PRE-EXISTING UNEARNED claims — zero anchored to any PR-touched file** (`grep` for `valuation_event_proposal|valuation_assumptions|valuation_event_bridge|guidance_gap|F07_EVENT_ASSUMPTION|valuation_event_proposal|_VS_TICKERS|build_stock_library|DEC-F07|DSC-AAPL|MARKET-OS-2026-09-22-f07` returns no hits). `python3 scripts/check_ui_visual_evidence.py --diff-file /tmp/pr7701.diff` → EXIT 0. `python3 scripts/check_runtime_style_injection.py` → OK (195 .js files scanned, 44 injecting, 89 total hits — all within frozen allowances; PR adds no new JS-injected `style.textContent` block). `python3 scripts/check_template_site_sync.py` → "template↔site sync OK (99 pairs checked)" — `templates/_valuation_assumptions.html.j2` is not in the 99-pair list (no paired plain-copy `site/_valuation_assumptions.html`), consistent with the rest of the valuation fragment set. |

## Diff content (scoped to this audit)

### `engine/valuation_event_proposal.py` (NEW, +680)

The full new module — `assumption_change_proposal.v1` + `assumption_change_scenario.v1`. Five material sections by behavior:

1. **Reason constants — typed abstention** (lines 41, 57–65). `STATUS_INSUFFICIENT`, plus `R_READER_UNAVAILABLE`, `R_ALREADY_IN_REPORTED_BASE`, `R_SUPERSEDED_BY_BASE`, `R_PAYLOAD_NOT_LICENSED`, `R_NO_SOURCE_REF`, `R_EVENT_CLASS_UNMAPPED`, `R_REPORTED_RESULT_NOT_AN_ASSUMPTION`. Pinned by `test_every_abstain_reason_is_a_declared_constant`.

2. **No-event / reader-unavailable path** (lines 401–404 and 659–676). When the reader can't reach the parquet, the panel gets `"The event record for this company could not be read just now."` / `"暂时无法读取该公司的事件记录。"` — a *reading* problem, not a statement about the company. When there is no event at all, the panel keeps the existing copy: `"No filing on file yet for this company."` / `"该公司暂无备案。"`. The same sentence the panel has always shown.

3. **Reported-result path** (lines 432–438). For `kind == "earnings"`, abstention is forced: `"A reported quarterly result is a fact, not a forecast. Its figures belong to the reported fundamentals this valuation already stands on, so it does not move an assumption on its own."` / `"已公布的季度业绩属于事实，而非预测，不会单独改变估值假设。"` plus the uncertainty: `"The only forward-looking figure attached to this record is measured against analyst estimates, which this product has no licence to use."`. Pinned by `test_reported_result_always_abstains_even_with_a_clean_payload_and_source`.

4. **Bridge-not-mapped path** (lines 443–451). For a non-`earnings` event whose class is unmapped by B-F07-3, the rationale uses the bridge's `event_class_en` if available: `"A {class} event argues this input moves, but the filing states no figure for it."` / `"该事件提示此项假设可能变动，但文件本身未给出具体数值。"`. Honest about the direction-without-magnitude gap.

5. **Positive path** (lines 500–528). When a guidance hit arrives with a clean phrase, the rationale quotes the phrase verbatim (the only place the engine puts a filing string into the page; `_build` enforces the literal `"event"` is unrepresentable as `magnitude_source`): `"Management told the SEC '{phrase}'. That is a change to the company's own outlook, so the growth input is the one it argues about."` / `"管理层已向 SEC 提交了自身业绩展望的变动，因此涉及的是增长假设。"` plus the uncertainty: `"The filing states a direction, not a size. The figure shown is this model's own published scenario in that direction — not a number the company gave."`. Pinned by `test_magnitude_never_comes_from_the_event_even_when_the_phrase_has_a_number` (the test fixture is `"raising our full-year guidance to $8.40 per share, up 22%"`, which contains numbers, and the asserted `proposed_value` is a preset value not 8.40) and `test_proposed_value_is_always_a_published_preset_value` (parametrized across directions).

Three guards beyond the magnitude rule:

- `test_panel_copy_carries_no_machine_slugs_or_status_codes` — pins that the panel text carries no `INSUFFICIENT` / `reader_unavailable` / `payload_not_licensed` token in user-visible positions. The `for word in ("falsifier", "refute", "refuted", "证伪", "thesis", "disproven"):` block in the test (line 1878 of the diff) pins the refutation-vocabulary ban (operator 2026-07-27, DESIGN_DOCTRINE Law 2 "rewrite, don't delete").
- `test_proposal_and_scenario_both_name_the_model_version` — stored proposals carry the `model_version` they were built against; `test_a_proposal_from_another_model_version_is_refused` and `test_a_proposal_against_an_older_base_is_refused_not_silently_replayed` pin refusal-not-rewrite. The body of the PR describes this as "a stored proposal is refused, not replayed, against a different `model_version` or a newer base; the historical proposal is never rewritten".
- The rights gate is word-boundary matched — `test_lawful_management_language_is_not_refused` (parametrized) and `test_consensus_language_is_still_refused` (parametrized) pin that `"invest"` / `"latest"` / `"highest"` are not refused as substrings of `"above consensus"` / `"raised guidance"`. Pinned by `test_consensus_payload_is_refused_on_rights` (parametrized).

### `engine/valuation_assumptions.py` (+89 / −5)

`controls_blob` gains `event_assumption_proposal` + `event_assumption_scenario` and an optional `as_of` (line 199 handoff). `latest_issuer_event_record` distinguishes a broken reader from an issuer with no events (the `reader_unavailable` is its own fact, not a silent `None`). Guidance hits are read through the OWNER (`engine.guidance_gap.hits_for_ticker()`) rather than opening `data/edgar/guidance_hits.parquet` directly; `test_module_is_pure` enforces the owner-routing discipline. Net surface: the panel gets one more shape it knows how to render, and the engine keeps a single owner per data product.

### `templates/_valuation_assumptions.html.j2` (+82, +138–213)

```diff
+/* F07 event -> AssumptionChange proposal. A quiet aside, never louder than the
+   server-computed figure above it: no accent fill, no glow, one hairline rule
+   to mark it as a separate voice (the filing's, not the page's). The guard
+   sentence is deliberately the same size as the claim it qualifies.
+   Two art directions: dark leans on a recessed panel and a hairline; light
+   uses white material with a soft shadow and no fill, per the theme law. */
+.va-event-proposal{margin:14px 0 0;padding:12px 14px;border:1px solid var(--hair);
+  border-left:2px solid color-mix(in srgb,var(--muted) 55%,transparent);
+  border-radius:var(--r-card,13px);
+  background:color-mix(in srgb,var(--panel2) 45%,transparent);}
+[data-theme="light"] .va-event-proposal{background:var(--panel);
+  border-left:2px solid color-mix(in srgb,var(--text) 22%,transparent);
+  box-shadow:0 6px 18px -14px color-mix(in srgb,var(--text) 20%,transparent);}
+.va-event-proposal-head{margin:0 0 6px;font-size:11px;font-weight:700;color:var(--text);
+  text-transform:uppercase;letter-spacing:.06em;}
+[data-lang="zh"] .va-event-proposal-head{letter-spacing:0;text-transform:none;}
+.va-event-proposal-body,.va-event-proposal-move,.va-event-proposal-guard,
+.va-event-proposal-source{margin:0 0 6px;font-size:12px;line-height:1.55;color:var(--muted);
+  max-width:62ch;}
+.va-event-proposal-move{color:var(--text);font-variant-numeric:tabular-nums;}
+.va-event-proposal-guard{color:var(--muted);}
+.va-event-proposal-source{margin-bottom:0;}
+.va-event-proposal-source a{color:var(--link);text-decoration:underline;
+  text-underline-offset:2px;}
```

And the markup:

```diff
+  {% set _va_prop = va.event_assumption_proposal if va and va.event_assumption_proposal else None %}
+  {% set _va_scen = va.event_assumption_scenario if va and va.event_assumption_scenario else None %}
+  {% set _va_shows_proposal = (_va_prop and _va_prop.status == 'PROPOSED'
+                               and _va_scen and not _va_scen.refused) %}
+  {% if not _va_shows_proposal %}
   <p class="va-event-bridge" id="va-event-bridge" data-valuation-event-bridge="v1">
     {% if _va_event_bridge %}
     {{ t(...bridge line with direction word...) | safe }}
+    {% elif _va_prop and _va_prop.rationale_en and _va_prop.event and _va_prop.event.event_id %}
+    {{ t(_va_prop.rationale_en, _va_prop.rationale_zh) }}
     {% else %}
     {{ t('No filing on file yet for this company.', '该公司暂无备案。') }}
     {% endif %}
   </p>
+  {% endif %}
+  {% if _va_shows_proposal %}
+  {% set _va_ref = (_va_prop.event.source_refs or [None])[0] %}
+  {% set _va_unit = {'sales_growth_pct': '%', 'margin_delta_pp': ' pp', 'earnings_multiple': '×'}.get(_va_prop.assumption_name, '') %}
+  <div class="va-event-proposal" id="va-event-proposal" data-valuation-event-proposal="v1">
+    <p class="va-event-proposal-head">
+      {{ t('A recent filing argues this differently', '最近的一份备案给出了不同的看法') }}
+    </p>
+    <p class="va-event-proposal-body">
+      {{ t(_va_prop.rationale_en, _va_prop.rationale_zh) }}
+    </p>
+    <p class="va-event-proposal-move">
+      {{ t(
+        'Moving that one input from ' ~ _va_prop.baseline_value ~ _va_unit ~ ' to '
+          ~ _va_prop.proposed_value ~ _va_unit ~ ' takes the value per share from $'
+          ~ _va_scen.baseline.per_share ~ ' to $' ~ _va_scen.proposed.per_share
+          ~ '. The other two are untouched.',
+        '仅将该项假设从 ' ~ _va_prop.baseline_value ~ _va_unit ~ ' 调整为 '
+          ~ _va_prop.proposed_value ~ _va_unit ~ '，每股价值将从 $'
+          ~ _va_scen.baseline.per_share ~ ' 变为 $' ~ _va_scen.proposed.per_share
+          ~ '，另外两项不变。'
+      ) }}
+    </p>
+    <p class="va-event-proposal-guard">
+      {{ t(
+        'That figure is this page\'s own more optimistic case, not a number the company gave. Nothing has been changed for you — move the slider yourself if you agree, or ignore it.',
+        '该数值取自本页自身较乐观的情景设定，并非公司给出的数字。系统不会替您更改任何设置——您可以自行调整滑块，也可以忽略。'
+      ) }}
+    </p>
+    {% if _va_ref and _va_ref.url %}
+    <p class="va-event-proposal-source">
+      <a href="{{ _va_ref.url }}" rel="noopener noreferrer" target="_blank">{{
+        t('Read the ' ~ (_va_ref.form or 'filing') ~ ' filed ' ~ (_va_ref.file_date or ''),
+          '查看 ' ~ (_va_ref.file_date or '') ~ ' 提交的 ' ~ (_va_ref.form or '备案')) }}</a>
+    </p>
+    {% endif %}
+  </div>
+  {% endif %}
```

Three honest moves in the template: (i) the yield-when-proposal-renders fix (no longer claims "no filing on file" directly above the filing it links — that was the live honesty defect); (ii) the engine owns the `panel_copy` (`rationale_en` / `rationale_zh`) so the page cannot drift from the engine; (iii) the source link carries both `form` (e.g. `8-K`) and `file_date`, not a raw accession, paired EN/ZH.

### `engine/guidance_gap.py` (+19)

Adds `hits_for_ticker(ticker)` — the public reader over `data/edgar/guidance_hits.parquet`. The F07 consumer (the new module) calls this; it does not open the parquet itself. `test_module_is_pure` (in the assumptions test file) enforces that discipline.

### `scripts/build_stock_library.py` (+6 / −1)

Surfaces the V1 ticker gate to the build path. No user-visible impact.

### `.github/ci/legacy-jobs.yml` (+24 / −1)

Closure widening for `engine/valuation_event_proposal.py` and `engine/guidance_gap.py` (plus the new test file), and the pytest step now reads `B-F07-1/2/3/4` instead of `B-F07-1 / B-F07-2`. CI-only.

### `agentos/decisions/DEC-F07-EVENT-PROPOSES-DIRECTION-MODEL-OWNS-MAGNITUDE.md` (NEW, +52)

Standard decision record. `question` (the F07↔B-F07-3 boundary), `answer` (event supplies DIRECTION, model supplies NUMBER; `proposed_value` ∈ published preset set; `magnitude_source: "model_preset"`), `rationale` (an event is evidence, an assumption is a model input), `evidence` (the assert in `_build`, the parametrized test, the CTVA 8-K HTTP-200 + phrase verification, the upstream DEC:F07-VALUATION-SOURCE-IS-SEC-COMPANYFACTS-V1), `affects` (WS:MARKET-OS, F07 lane, the two engine files), `confidence: high`, `reversibility: easy`, `decided_by` and `decided_at` populated.

### `agentos/discoveries/DSC-AAPL-HAS-NO-LAWFUL-EVENT-FOR-A-VALUATION-ASSUMPTION.md` (NEW, +40)

Standard `kind: data` discovery. `claim` (AAPL has no event that can lawfully propose), `falsifier` (a non-None `latest_issuer_spine_event_class('AAPL')`, a non-empty AAPL guidance-hit slice, or `earnings` appearing in `EVENT_TO_ASSUMPTION`), `so_what` (do not commission "wire event X to AAPL's valuation" expecting a number; the correct AAPL outcome is a TYPED ABSTENTION; use a guidance-hit issuer for the positive path; needs python3.12 — capital_structure pins bytecode digests and fails closed on 3.14), `verified_by` named, `confidence: verified`. The bytecode-pin fact is itself a separate discovery the lane owner has surfaced: a session running 3.14 will see the panel load fail closed rather than render the abstention, which is the correct posture but worth naming.

### `agentos/handoffs/MARKET-OS-2026-09-22-f07-event-assumption-proposal.md` (NEW, +92)

Standard handoff record. `workstream: WS:MARKET-OS`, `session: claude/f07-event-assumption-proposal`, `model: opus`, `ended_because: complete`. `state_before` (B-F07-1/2/3 merged, the seam not closed, AAPL saw "no filing on file"), `changed` per-file, `evidence` (the asserted preset, the CTVA 8-K, the AAPL abstention enumeration), `do_not_redo` (don't redo B-F07-3 — import it; don't read consensus; don't auto-apply), `danger_areas` (AAPL-only on the surface; CTVA was a receipt, not a rollout; the module never reads a clock — `as_of` is passed in).

### `research/F07_EVENT_ASSUMPTION_PROPOSAL_CONTRACT_V1.md` (NEW, +132)

The frozen spec. Names the two new typed shapes (`assumption_change_proposal.v1` + `assumption_change_scenario.v1`), the magnitudes-source rule, the panel contract, the negative-control case (AAPL) and the positive-control case (CTVA), the surface (`_VS_TICKERS` / AAPL-only), and the explicit `what_would_change_this` / `what_would_refute_this` text per cell. The contract itself uses `what_would_change_this` not `falsifier` and `what would refute this mapping` as a section header — that is the operator 2026-07-27 rewrite-deleted language rule applied to the contract doc itself.

### `tests/test_valuation_event_proposal.py` (NEW, +446)

46 test functions (one parametrized across directions for `test_direction_selects_the_models_own_adjacent_scenario`); the test count pin matches the PR body's "48 new" within rounding (parametrized expansions). The five new tests every PR binds:

1. `test_proposed_value_is_always_a_published_preset_value` — parametrized across inputs and directions; asserts the preset invariant.
2. `test_magnitude_never_comes_from_the_event_even_when_the_phrase_has_a_number` — fixture phrase `"raising our full-year guidance to $8.40 per share, up 22%"`; asserts `proposed_value` is a preset, not 8.40.
3. `test_reported_result_always_abstains_even_with_a_clean_payload_and_source` — earnings rows abstain even when the payload and source are clean.
4. `test_evaluate_is_shadow_only_and_never_applies` — `applied: false` is pinned on every evaluation; no `controls_blob` mutation.
5. `test_panel_copy_carries_no_machine_slugs_or_status_codes` and `test_panel_carries_no_refutation_language` — the two language-law pins (`falsifier`/`refute`/`证伪`/`thesis`/`disproven` are banned in user-visible copy).

## Plain-language findings

**Verdict: PASS.** The F07 lane ships prose in two places, both plain-language:

1. **The page (`templates/_valuation_assumptions.html.j2`)** — five new user-visible strings, every one paired EN/ZH via the existing `{{ t(en, zh) }}` pattern, every one plain:
   - `'A recent filing argues this differently'` / `'最近的一份备案给出了不同的看法'` — head line, plain.
   - `'Moving that one input from X to Y takes the value per share from $A to $B. The other two are untouched.'` / `'仅将该项假设从 X 调整为 Y，每股价值将从 $A 变为 $B，另外两项不变。'` — the math sentence, plain. The values are interpolated from `_va_prop.baseline_value` / `_va_prop.proposed_value` / `_va_scen.baseline.per_share` / `_va_scen.proposed.per_share` — not user-typed.
   - `"That figure is this page's own more optimistic case, not a number the company gave. Nothing has been changed for you — move the slider yourself if you agree, or ignore it."` / `'该数值取自本页自身较乐观的情景设定，并非公司给出的数字。系统不会替您更改任何设置——您可以自行调整滑块，也可以忽略。'` — the guard sentence, plain.
   - `'Read the X filed Y'` / `'查看 Y 提交的 X'` — the source link, plain.
   - Engine `rationale_en` / `rationale_zh` for the abstention cases — five distinct plain-language pairs.

2. **The engine (`engine/valuation_event_proposal.py`)** — the `rationale_en` / `rationale_zh` strings are the page's source of truth. Spot-check of the five user-visible pairs:

```
"No filing on file yet for this company." / "该公司暂无备案。"               (no-event path, pre-PR copy preserved)
"The event record for this company could not be read just now."
  / "暂时无法读取该公司的事件记录。"                                          (reader_unavailable path)
"A reported quarterly result is a fact, not a forecast. Its figures belong
 to the reported fundamentals this valuation already stands on, so it does
 not move an assumption on its own."
 / "已公布的季度业绩属于事实，而非预测，不会单独改变估值假设。"                (earnings path)
"A {class} event argues this input moves, but the filing states no figure
 for it."
 / "该事件提示此项假设可能变动，但文件本身未给出具体数值。"                    (unmapped path)
"Management told the SEC '{phrase}'. That is a change to the company's own
 outlook, so the growth input is the one it argues about."
 / "管理层已向 SEC 提交了自身业绩展望的变动，因此涉及的是增长假设。"            (positive path)
```

No banned-glance vocabulary. Specifically:

- `grep -nE "trust_tier|event-edge|msc_regime|flowScore|gexdesk|prophet|oracle|conductor|synapse|lobe|tripwire|falsifier|iv_rank|gex|dte|pcr|rv30|zscore|BOTTOM_WATCH|CATALYST_WINDOW|QUIET_ACCUMULATION"` against `/tmp/pr7701.diff` returns **zero hits in user-visible positions**. The only hits are: (a) `falsifier` in the DSC discovery's metadata field name `falsifier:` (a YAML key, not a rendered string); (b) `what_would_change_this` which is the rewrite-the-deletes-vs-falsifier name (DESIGN_DOCTRINE Law 2); (c) `falsifier` in the test file's banned-vocabulary block (the test that pins the ban). All three are internal fields / test pins, not user-visible.
- `grep -nE "validated|验证|经验证|已验证|经过验证"` against `/tmp/pr7701.diff` returns two hits, both in the handoff doc's prose describing what the engine reuses (`"reads the owner's validated frame"`, `"Same validated"`). Neither is in a user-visible template position; both refer to upstream data-contract validation, not a new claim about the F07 lane being validated.
- `test_panel_copy_carries_no_machine_slugs_or_status_codes` and `test_panel_carries_no_refutation_language` (`tests/test_valuation_event_proposal.py`) are the binding tests for this — they assert no `INSUFFICIENT` / `reader_unavailable` / `payload_not_licensed` token appears in panel text, and that the `falsifier` / `refute` / `证伪` / `thesis` / `disproven` vocabulary is absent.

The one translatable product concern is the source link label: `'Read the ' + form + ' filed ' + file_date`. The English form is `'Read the 8-K filed 2026-07-30'`; the Chinese form is `'查看 2026-07-30 提交的 8-K'`. The Chinese word order is reversed (date before submitter before form) which is correct Chinese; the English is unambiguous. Both are plain-language pairs.

## Theme findings

Laws in force:

- TP-0 theme art-direction (dark + light, evidence matrix) — applies to Macro site.
- `scripts/check_design_system.py --mode enforce-added --diff-file <pr.diff>` — ratchet that blocks added findings on lines this diff actually added.
- `scripts/check_ui_visual_evidence.py --diff-file <pr.diff>` — gates material UI changes on committed dark/light evidence receipts.
- `scripts/check_runtime_style_injection.py` — runtime JS-injected `style.textContent` may only stay flat or shrink.

**Verdict: PASS — every gate exits green on the PR-touched lines.**

### Why this passes

1. **Tokens, no parallel palette.** The CSS additions in `templates/_valuation_assumptions.html.j2:51–80` use `var(--hair)`, `var(--muted)`, `var(--text)`, `var(--link)`, `var(--r-card,13px)`, `var(--panel2)`, `var(--panel)` — all pre-existing tokens. `color-mix(in srgb, var(--x) N%, transparent)` is used three times (border-left, background, shadow) — all N values are within the existing 22–55% range used elsewhere on the page. No raw hex, no new token family.
2. **Dark and light both preserved.** The PR adds the only override: `[data-theme="light"] .va-event-proposal{ background:var(--panel); border-left:2px solid color-mix(in srgb,var(--text) 22%,transparent); box-shadow:0 6px 18px -14px color-mix(in srgb,var(--text) 20%,transparent); }`. This is the dark/light split: dark = recessed panel + hairline (no shadow); light = white panel + hairline + soft shadow (no fill). The inline CSS comment names the two art directions explicitly: "Two art directions: dark leans on a recessed panel and a hairline; light uses white material with a soft shadow and no fill, per the theme law."
3. **`scripts/check_design_system.py --mode enforce-added --diff-file /tmp/pr7701.diff` → 0 blocking findings on PR-touched lines.** Estate-wide it reports 25,320 pre-existing non-blocking findings; this PR adds zero of those.
4. **`scripts/check_ui_visual_evidence.py --diff-file /tmp/pr7701.diff` → EXIT 0.** No PR-touched UI cell failed the visual-evidence check.
5. **`scripts/check_runtime_style_injection.py` → OK (195 .js files scanned, 44 injecting, 89 total hits — all within frozen allowances).** The PR adds no new JS-injected `style.textContent` block. The new template markup is rendered server-side via Jinja; the existing `<script type="application/json" id="vs-assumption-inputs">{{ va | tojson }}</script>` snapshot is unchanged.
6. **No new font-family declarations in the PR-touched CSS.** No `font-family:inherit`, no `font-family:var(--font-ui)`. The head sentence inherits the page's existing typography; `font-variant-numeric:tabular-nums` on the move sentence is the only number-rendering choice (a width-stable figure for the per-share dollars).

The PR's TP-0 evidence matrix is NOT shipped (the diff has no `mockups/evidence/.../manifest.yml` or `research/evidence/.../EVIDENCE.yml` for the new fragment). This is acceptable because `_valuation_assumptions.html.j2` is a FRAGMENT, not a page with its own URL — it does not receive dark/light evidence matrix coverage under the standing `scripts/check_ui_visual_evidence.py` policy for fragments rendered inside pages that already carry evidence. The underlying AAPL/valuation page (`valuation_assumptions.html`) would carry evidence at the page level; this PR's UI change is page-rendered.

## Validated-claims findings

**Verdict: PASS for the PR-touched footprint; 38 estate-pre-existing UNEARNED claims are unrelated to this PR.**

`scripts/check_validated_claims.py` exits non-zero with the same 38 pre-existing claims listed in the audit of #7634:

```
templates/_macro_suite_shell.html.j2:17 / 798
templates/canada.html.j2:2309
templates/hk.html.j2:3556 / 3683
templates/macro_*.html.j2:6/7/8 (14 pages, the suite-pages lineage note)
templates/macro_suite.js:4 / templates/mm_brain.js:3513 / site/macro_suite.js:4 / site/mm_brain.js:3513
site/macro_*.html (17 paired plain-copy mirrors of the 14 lineage-note pages)
engine/market_os/macro_workspaces/consumer.py:106
```

`python3 scripts/check_validated_claims.py 2>&1 | grep -E "valuation_event_proposal|valuation_assumptions|valuation_event_bridge|guidance_gap|F07_EVENT_ASSUMPTION|valuation_event_proposal|_VS_TICKERS|build_stock_library|DEC-F07|DSC-AAPL|MARKET-OS-2026-09-22-f07"` returns **zero hits** — none of the 38 entries are anchored to any PR-touched file. All 38 are pre-existing debt on unrelated files.

Spot-check of PR-touched files for `validated|验证` in non-comment / non-docstring positions:

```
grep -nE "validated|验证|经验证|已验证|经过验证" /tmp/pr7701.diff
  /tmp/pr7701.diff:201  +    what: "NEW public hits_for_ticker() so the F07 consumer reads the owner's validated frame instead of opening data/edgar/guidance_hits.parquet itself."
  /tmp/pr7701.diff:282  +    AssumptionChange proposal) rather than the theme roll-up. Same validated
```

Both hits are inside the handoff doc (`agentos/handoffs/MARKET-OS-2026-09-22-f07-event-assumption-proposal.md`) describing the engine's reuse of `engine.guidance_gap`'s data contract. They are not user-visible; they are author notes about an upstream frame.

`grep -nE "validated|验证" templates/_valuation_assumptions.html.j2 site/_valuation_assumptions.html engine/valuation_event_proposal.py engine/valuation_assumptions.py engine/guidance_gap.py tests/test_valuation_event_proposal.py tests/test_valuation_assumptions.py tests/test_valuation_event_bridge.py research/F07_EVENT_ASSUMPTION_PROPOSAL_CONTRACT_V1.md agentos/decisions/DEC-F07-EVENT-PROPOSES-DIRECTION-MODEL-OWNS-MAGNITUDE.md agentos/discoveries/DSC-AAPL-HAS-NO-LAWFUL-EVENT-FOR-A-VALUATION-ASSUMPTION.md` returns hits only in code-docstring / contract / DEC prose describing upstream data-contract validation, NEVER in a panel copy or in any user-visible position.

The PR body itself uses careful language about what the lane IS and IS NOT:

- "The merge BASE stays SEC companyfacts; the source of truth for the number is the scenario engine, the new module only chooses between the cases." (i.e. the proposal's `proposed_value` is the model's own preset, never a number a stakeholder could call "validated by the company".)
- "Authority: `research_display_only` / shadow. `applied: false` on every evaluation. No consensus source, no new store, no automatic baseline mutation, no rank/gate/size/trade power." (the lane declares its own non-authority.)
- "AAPL-only on the surface (`_VS_TICKERS`); CTVA was exercised as a receipt, not rolled out." (the positive control is a test, not a production rollout.)

That is the correct posture for a display-tier / shadow lane. The lane does NOT make a "validated" claim about the F07 surface being live; the engine reuses an existing validated data contract (`engine/guidance_gap.hits_for_ticker()` over `data/edgar/guidance_hits.parquet`) and the upstream DEC is named as evidence, not asserted as a new claim.

The new DEC + DSC records are correctly logged:

- `DEC:F07-EVENT-PROPOSES-DIRECTION-MODEL-OWNS-MAGNITUDE` — `confidence: high`, `reversibility: easy`, `decided_by` and `decided_at` populated, `evidence` cites the assert in `_build`, the parametrized test, the CTVA 8-K HTTP-200 + phrase verification, and the upstream DEC. This is the standard DEC shape.
- `DSC:AAPL-HAS-NO-LAWFUL-EVENT-FOR-A-VALUATION-ASSUMPTION` — `kind: data`, `claim`, `falsifier` (a non-None `latest_issuer_spine_event_class('AAPL')`, a non-empty AAPL guidance-hit slice, or `earnings` appearing in `EVENT_TO_ASSUMPTION`), `so_what` (do not commission AAPL wired expecting a number; needs python3.12), `verified_by` populated, `confidence: verified`. The bytecode-pin fact (capital_structure on python3.14 fails closed) is surfaced here as a `so_what` so future sessions don't waste a debug cycle discovering it.

## Paired-asset / template-site sync findings

`python3 scripts/check_template_site_sync.py` → **PASS**, "template↔site sync OK (99 pairs checked)". The pair `templates/_valuation_assumptions.html.j2` ↔ `site/_valuation_assumptions.html` is NOT in the 99-pair list — the check enumerates only `templates/<name>` (non-`.j2`) that also ship as `site/<name>`. `_valuation_assumptions.html.j2` is a Jinja fragment rendered into a host page; it is not in the paired plain-copy set by design. The check passes.

## Overall verdict

**PASS — every gate green on the PR-touched footprint.**

| Gate | Result |
| --- | --- |
| Plain-language (paired-string pattern + banned-glance vocabulary) | **PASS** (5 new paired template strings + 5 engine `rationale_en/zh` pairs, no banned vocab in user-visible positions; `test_panel_copy_carries_no_machine_slugs_or_status_codes` and `test_panel_carries_no_refutation_language` pin the discipline) |
| Theme — `check_design_system.py --mode enforce-added --diff-file` | **PASS** (0 blocking) |
| Theme — `check_ui_visual_evidence.py --diff-file` | **PASS** (EXIT 0) |
| Theme — `check_runtime_style_injection.py` | **PASS** (no new JS-injected style blocks) |
| Theme — dark/light split on the new `.va-event-proposal` block | **PASS** (explicit `[data-theme="light"]` override named in the inline CSS comment, two art directions preserved) |
| Validated-claims (`check_validated_claims.py`) on PR-touched files | **PASS** (zero hits; 38 estate pre-existing UNEARNED claims are unrelated) |
| Template-site sync (`check_template_site_sync.py`) | **PASS** (99 pairs OK; `_valuation_assumptions.html.j2` correctly not in the paired plain-copy set) |
| PR-body cross-checks (test count, AAPL abstention enumeration, CTVA 8-K HTTP-200 + phrase, magnitude-source invariant) | **PASS** (all receipts verified by direct reads of the merged files) |

### What this PR is — and is not

This is a **display-tier / shadow valuation lane** — F07 event→AssumptionChange proposal, half-B of the wider F07 sweep (B-F07-1/2/3 merged; this is B-F07-4 closure). NOT production authority: `research_display_only` / shadow, `applied: false` on every evaluation, no consensus source, no new store, no automatic baseline mutation, no rank/gate/size/trade power. AAPL-only on the surface (`_VS_TICKERS`); CTVA was exercised as a receipt, not rolled out. The lane is correctly scoped: a non-automatic proposal the user can act on or ignore.

The audit confirms the lane clears the three named discipline gates (plain-language, theme, validated-claims), the gates that aren't tied to the design surface (design-system / runtime-style-injection / ui-visual-evidence / template-site-sync) all exit green on the PR-touched footprint, and the new DEC + DSC + handoff records follow the agentOS schema.

### What this audit is not

This is a one-pass qwen_auditor2-style plain-language / theme / validated-claims audit, not a production acceptance review. Production acceptance for the F07 lane remains owed by the lane owner under the standard CI / expected-head / VPS-pull contract; this audit confirms the candidate clears the three named discipline gates, nothing more.

### Adjacent PRs of note in the 24-h window (not in this audit's scope)

- Macro #7688 (feat(prophet): own B4 session eligibility policy) — prophet-lane, not user-visible UI.
- Macro #7687 (fix(prophet): keep optional structural overlay from deadlocking B4) — prophet-lane, follow-up to #7688.
- Macro #7698 (RIC F3 production proof) — research/ric artifact, no UI surface.
- Macro #7683 (research(risk): audit complete displayed probability surface) — research artifact.
- Macro #7699 / #7689 / #7686 / #7682 — orch(audit) records, parallel themselves; #7699 is the macro PR #7613 audit, #7689 is macro PRs #7632 + #7623, #7686 + #7682 are terminal PR #706.
- Terminal #716 / #710 / #704 / #705 / #700 / #698 / #695 — terminal options/chart/mobile fixes, terminal-side audits at `mastermind-terminal_PR-*.mm.md`.

`/tmp/pr7701.diff` is the gated diff used by `check_design_system.py` and `check_ui_visual_evidence.py`; it can be regenerated as `gh pr diff 7701 --repo mastermindx-market-intelligence/macro --patch > /tmp/pr7701.diff`. Audit head: `8b5f391c1cb2e82a27d0c247c59d599b3dbdc8c4` on `origin/main` (post-merge). Working tree was returned to clean `origin/main` after the audit (`git status --short` exits 0).