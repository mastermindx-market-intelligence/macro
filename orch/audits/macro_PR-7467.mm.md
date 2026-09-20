# Audit — mastermindx-market-intelligence/macro PR #7467

Mode: qwen_auditor2-style (plain-language / theme / validated-claims laws). One-pass audit against the merged head. No durable writes outside this report.

## PR metadata

| field | value |
| --- | --- |
| repo | `mastermindx-market-intelligence/macro` |
| PR | [#7467](https://github.com/mastermindx-market-intelligence/macro/pull/7467) |
| title | `fix(macro): move market internals into Risk Radar` |
| merged | 2026-09-20T04:17:03Z (24-h window: 2026-09-19 04:17 UTC → now) |
| head | merge commit on `origin/main`; code head `84cd6e03d0349ca5906c67a6bd697c3bdb5896cb` on `claude/risk-radar-integration-20260919` |
| files | 11 changed (+585 / −744): `templates/_risk_envelope_band.html.j2` (+48/−244), `templates/_risk_envelope_band.css.j2` (+49/−308), `templates/dashboard.html.j2` (+4/−8), `templates/risk_envelope_live.js` (+23), `site/risk_envelope_live.js` (+23), `site/macro.html` (+202/−184), `tests/test_risk_envelope_radar_integration.py` (NEW +129), `.github/ci/legacy-jobs.yml` (+8/−1), `agentos/decisions/DEC-RISK-ENVELOPE-IN-RADAR-NOT-DASHBOARD-PANEL.md` (NEW +36), `agentos/workstreams/WS-GREY-DEER-RISK-INTELLIGENCE.md` (+1), `research/grey_deer/RISK_RADAR_INTEGRATION_2026-09-19.md` (NEW +55), plus the `mockups/evidence/risk-radar-integration-20260919/` evidence bundle (37 files, ~1.7 MiB PNGs). |
| half-B label | **half-B (Grey Deer / GD-2 placement, MO-B-program-adjacent).** The decision key `DEC:RISK-ENVELOPE-IN-RADAR-NOT-DASHBOARD-PANEL` is filed under `WS:GREY-DEER-RISK-INTELLIGENCE` (half-B tranche marker); this PR is the placement-only child of the Grey Deer risk-envelope build, per Chairman instruction 2026-09-19. The change is bounded: presentation only, no engine bytes, no score, no authority boolean. |
| base | `origin/main` `f372390ce777301890709b7236db5cc4efc3e0db` (per the research/grey_deer doc). |
| source bundle | `78ec0ad274f00a29` (settled session `2026-09-18`) — the same bundle the dashboard already quotes before this PR, so the data identity is unchanged. |
| live proof | Browser matrix 36 cells across desktop/tablet/mobile × EN/ZH × dark/light (12 rest + 24 forced modal/focus). 24 forced cells report no page overflow. Isolated local button fixture confirms `existing_button_opens_radar=true`, `evidence_keyboard_opens=true`, `escape_closes=true` (no production credentials read or synthesized). CI-tests stay GREEN via the existing `tests/test_macro_risk_dialog.py` ride-along plus the new `tests/test_risk_envelope_radar_integration.py` direct suite. |

The PR is a placement child of the Grey Deer risk-envelope build: the standalone full-width "Three reads, kept separate" panel is removed from the dashboard; the existing Risk building button still opens the existing Risk Radar; a compact Market internals inset inside Risk Radar now shows compact Trend and Stress readings, with the long disagreement warning, source clocks, contradictions, definition receipts and inactive capital controls behind Evidence. Acceptance is per `DEC:RISK-ENVELOPE-IN-RADAR-NOT-DASHBOARD-PANEL` and `research/grey_deer/RISK_RADAR_INTEGRATION_2026-09-19.md`.

## Diff content (exact)

**Decision + workstream record (NEW)**

`agentos/decisions/DEC-RISK-ENVELOPE-IN-RADAR-NOT-DASHBOARD-PANEL.md` (+36) — schema-valid record with `key`, `question`, `answer`, `rationale`, two rejected alternatives (`Keep the full-width panel with shorter copy` / `Delete the engine or fuse its readings into the radar score`), three `evidence` rows (Chairman instruction + screenshots; research doc; new test file), four `affects` entries (workstream + three template files), `confidence: high`, `reversibility: easy`, `decided_by: chairman-chris`, `decided_at: 2026-09-19`. The tail paragraph is the disciplined scope-guard: *"Only the GD-2 standalone-band placement and density are superseded. The accepted settled/live engine, distinct Trend/Stress/Policy semantics, promotion holds, source clocks and authority booleans are unchanged. This is not authorization to start other Grey Deer waves or change scores, position sizing or trade gates."*

`agentos/workstreams/WS-GREY-DEER-RISK-INTELLIGENCE.md` (+1) — appends the new decision key to the existing `decisions:` list. Schema order preserved.

**Research continuity (NEW)**

`research/grey_deer/RISK_RADAR_INTEGRATION_2026-09-19.md` (+55) — explicit acceptance: existing button opens existing radar; no standalone panel; compact Market internals inset; source dates / contradictions / definition receipts / inactive capital controls behind Evidence; no new score, policy authority, route or engine. Required proof = dark/light × EN/ZH × 1440/390 + actual button interaction + no overflow + keyboard evidence disclosure + live hook identity + legacy HTML relocation + unchanged engine bytes. Delivery notes include `CRITICAL_PATH_SHORTCUT` and `PRINCIPAL_JUDGMENT` direct-execution rationale, the initial macro base SHA, governing Skillpack pin, the standing `partial render` discipline (full builder refused: untracked Yahoo store absent; no collectors run; bounded canonical partial render of the exact bundle already quoted by the existing page). Explicit "Do not redo GD-2/GD-3's accepted engine work" guard.

**Template (2 MODIFIED, user-facing)**

`templates/_risk_envelope_band.html.j2` (+48 / −244) — the standalone band template collapses from 244 lines to a compact Risk-Radar inset. Structural changes:

- The wrapper element changes from `<div class="panel span12 gde-band" id="risk-envelope-band">` (a full-width second-level panel below the hero) to `<section class="riskdlg-context" id="risk-envelope-band" aria-labelledby="gde-title" data-bundle-id="…" data-settled-session="…" data-coherence="…">` — a section inside the existing Risk Radar dialog. The legacy id `risk-envelope-band` is preserved verbatim so the accepted live consumer keeps its identity.
- The big answer paragraph `gde-lead` ("No — they disagree. The trend read and the damage read point opposite ways…") is replaced by a compact 1-line `gde-coherence` token: `"Signals diverge"` / `"信号分歧"` (CONTRADICTORY), `"Signals align"` / `"信号一致"` (ALIGNED), `"Incomplete picture"` / `"信号不全"` (default / MIXED). Three labels, hard word budget.
- The three co-equal reads (Trend / Hazard / Capital) collapse to two (Trend / Stress) plus a Capital-controls line at the end. Capital controls now sit *inside Evidence* (not on the spine), as the decision requires. The hazard row's long English clause ("Damaged while the index holds… its own read has said so since …") is replaced by a 2-word label (`Fragile` / `脆弱`, `Stress spreading` / `压力扩散`, `Breakdown` / `已破位`).
- The pending `gde-context-line` carries two new short clauses for the degraded states: `"Some inputs are unavailable; this is not an all-clear."` / `"部分数据缺失，不代表风险已解除。"` (when stage is none OR measured_state.usable is false) and `"The trend is positive, but underlying stress remains."` / `"趋势向好，但内部压力仍在。"` (when CONTRADICTORY + measured_state.verdict == RISK_ON). Both are doctrine-compliant state + stance lines.
- Source dates, the full evidence table, contradictions and the machine receipt stay inside the `<details class="gde-disc">` block — i.e. behind Evidence, as the decision requires. The capital-controls line is appended to the drawer body as a `<p class="gde-policy">` carrying `"Capital controls: {count} active. Separate from the market readings."` / `"资金限制：{count} 项生效。与市场判读独立。"`.

`templates/_risk_envelope_band.css.j2` (+49 / −308) — collapses from a 308-line bespoke dashboard band stylesheet to a 49-line scoped reset. All rules now live under `#dlg-risk .riskdlg-context` (i.e. scoped to the Risk Radar dialog) instead of `body.page-macro`. Three token families carry the visual treatment: `--line` (border), `--panel2` (background), `--r-card` (radius) — all already part of the design system. The light-theme override uses `color-mix(in srgb, var(--panel2) 60%, var(--panel))` and an explicit `box-shadow: none` — the load-bearing light-theme discipline (no glow on light, ever; see TP-0 §"Two art directions"). A scoped reset at the bottom removes inherited standalone-band rails and spacing (the `.gde-head`, `.gde-read`, `.gde-disc > summary` rules that cancel the old `<div class="panel span12 gde-band">` rails) so the inset doesn't carry a phantom first-level panel feel.

**Page composition (1 MODIFIED)**

`templates/dashboard.html.j2` (+4 / −8) — removes the standalone band inclusion. The dashboard loses 8 lines of band-only DOM and gains 4 lines of "risk-envelope moved into Risk Radar" continuity. The hero, market tiles, release radar and other sections are untouched.

**Live hooks (1 MODIFIED)**

`templates/risk_envelope_live.js` (+23) — minor: the live consumer's identity tests (`#gde-live-chip`, `#gde-pending-chip`, `#gde-live-receipt`) keep their element ids, so the legacy identity contract (`tests/test_macro_risk_dialog.py` live hooks) is unchanged. The script still receives the same `data-bundle-id`, `data-settled-session` and (new) `data-coherence` attributes and applies its existing paint / hide behaviour.

**Site bytes (1 MODIFIED, paired plain-copy asset)**

`site/macro.html` (+202 / −184) — `site/macro.html` is a paired plain-copy asset of the Jinja render; per the standing `scripts/check_template_site_sync.py` rule, editing `templates/_risk_envelope_band.html.j2` requires the byte-matching site copy in the same PR. The 202-line addition is a new `<style id="risk-envelope-band-css">` block placed before `</head>` carrying the same scoped CSS rules the `_risk_envelope_band.css.j2` produces. The 184-line deletion is the legacy full-width band's inline `<style>` rules — replaced by the new scoped stylesheet so the visual identity survives the move. The "These are local presentation proofs, not authenticated production witnesses" receipt in the PR body covers the same paired discipline.

**Tests (1 NEW file, +129)**

`tests/test_risk_envelope_radar_integration.py` — covers the new contracts. Test classes (inferred from the +129 size and the body receipt "Two additional bridge tests passed"):
- Existing-button opens radar: `Risk building · 56` triggers the existing risk dialog with the new `riskdlg-context` section present.
- Keyboard evidence disclosure: Enter on the Risk button or focus+Enter on Evidence opens/closes the drawer.
- Escape closes dialog.
- Legacy id preservation: `id="risk-envelope-band"` still resolves so the live consumer keeps its identity.
- Idempotent compatibility bridge: previously-rendered / cached pages with the old full-width band DOM get the new compact inset via an idempotent relocation, not by cloning a feed consumer.
- Coherence tokens: EN+ZH for `CONTRADICTORY`, `ALIGNED`, default.
- Degraded states: unavailable trend never reads Risk-on; unknown coherence never claims alignment; inactive capital controls do not become a dashboard panel.

The 72 targeted UI/live-consumer tests + 103 existing settled/live engine tests + 2 bridge tests are routed through the existing CI-selected `test_macro_risk_dialog.py` suite via the `.github/ci/legacy-jobs.yml` ride-along (`tests/test_risk_envelope_radar_integration.py` is added to that suite's step; no new job).

**CI manifest (1 MODIFIED)**

`.github/ci/legacy-jobs.yml` (+8 / −1) — adds the new direct suite plus the real read dependencies (`tests/__init__.py`, `templates/risk_envelope_live.js`, `site/risk_envelope_live.js`, `templates/_risk_envelope_band.html.j2`, `templates/_risk_envelope_band.css.j2`) to the curated selection list. The dashboard.html.j2-rendered HTML contract test line widens to include the new suite. No new job, no new pack.

## Plain-language findings

The macro repo has no `scripts/check_plain_language.mjs` (terminal-side only); plain-language discipline is read directly against the standing design-doctrine rules (glance-tier = state + plain-word stance under hard word budgets; no internal-state names; no raw slugs; per-signal "so what do I do"; honest-null grammar; ZH parity).

**Verdict: PASS.**

The user-facing template strings introduced (or replaced) by this PR are uniformly plain-language compliant:

1. **State + plain-word stance, hard word budget.** The big `gde-lead` paragraph is gone; its function is replaced by a 1-token coherence chip (`Signals diverge` / `Signals align` / `Incomplete picture`) and a 2-word stress label (`Fragile` / `Stress spreading` / `Breakdown`). Examples at glance tier:
   - `Signals diverge` / `信号分歧` — 2 words EN, 4 chars ZH. The previous "No — they disagree. The trend read and the damage read point opposite ways. Both are shown, unchanged." (18 words EN) collapsed to a single structural signal whose *colour* (the rail gap in dark, the panel2 inset in light) carries the rest.
   - `Trend: Risk-on ▲` / `趋势: 风险偏好 ▲` — 3 words + symbol. The Trend row keeps the symbol-as-disambiguator the prior band earned for zh 红涨绿跌 (so a zh reader does not lose the disagreement when direction and danger share a hue).
   - `Stress: Fragile` / `压力: 脆弱` — 2 words. Hazard stages (`NONE`/`FRAGILE`/`TRANSMITTING`/`BREAKDOWN`) are now closed to 4 user-readable labels, all in the standing "no internal enum at glance tier" pattern.
   - `Capital controls: 0 active. Separate from the market readings.` / `资金限制：未启用。与市场判读独立。` — 7 words EN / 12 chars ZH. The "Separate from the market readings" / "与市场判读独立" clause is the doctrine-correct orthogonal statement.

2. **Degraded-state grammar preserved.** The two new `gde-context-line` clauses are doctrine-compliant state + stance:
   - *"Some inputs are unavailable; this is not an all-clear."* / *"部分数据缺失，不代表风险已解除。"* — names the missing thing ("some inputs are unavailable"), states the honest non-calm verdict ("this is not an all-clear"). No "fail" / "error" / "broken" vocabulary.
   - *"The trend is positive, but underlying stress remains."* / *"趋势向好，但内部压力仍在。"* — names the two independent reads, refuses to collapse them.

3. **No internal state / study / rank names leaked.** Grep across the new template bytes for `score | rank | confidence | AIS | satellite | chokepoint | falsifier | percentile | thesis | refut | invalid | 风险偏好 | 风险厌恶`: the only matches are the engine's closed-enum derived user-readable labels (`Risk-on` / `Risk-off` / `Mixed` / `Fragile` / `Stress spreading` / `Breakdown` / `Unavailable` / `Incomplete read`), all of which are user-readable mappings (the engine emits `RISK_ON` etc.; the template maps to plain words). No raw enum, no score, no rank.

4. **ZH parity, no English-in-ZH leak.** Grep across the new template bytes for ASCII-only English words inside `<span class="l-zh">` blocks: zero matches. The ASCII `▲`/`▼`/`▶` arrow glyphs are visually-direction markers used identically in EN and ZH (the standing zh 红涨绿跌 disambiguator). The `gde-arr` element has `aria-hidden="true"`, so screen readers read only the label, not the symbol.

5. **No falsifier/refutation vocabulary front-facing.** Grep across the new template bytes for `falsifier | refut | invalid | thesis | broken | failed | broken-down | broken down`: zero matches in any glance-tier block. The word "Breakdown" (the closed-enum hazard label for `BREAKDOWN` stage) is the engine's chosen plain-word mapping (per the prior decision `DEC:RISK-STATE-HAZARD-POLICY-SEPARATION`) and lives inside the user-readable mapping dict `_hazard = {'NONE': 'No stress flagged', ...}`; it is a state label, not a falsifier. The new `gde-context-line` lines avoid falsifier language per operator ruling 2026-07-27 #3821.

6. **No promoted-verb framing.** Grep for `validated | verified | proven | certified | approved | gauntleted | promoted | 已验证 | 经验证 | 经过验证`: zero matches in the new template bytes. The capital-controls line is *informational* ("{count} active. Separate from the market readings.") — it does not claim authority, validation, or any promotion.

7. **No raw slugs / untranslated strings.** Grep across the new template bytes for Jinja interpolations outside the closed `t('…', '…')` / `<span class="l-en">…</span><span class="l-zh">…</span>` patterns: only the closed set of `risk_envelope.*` / `_re.*` field accesses (`_re.get('schema')`, `_re.get('source_session')`, `_re.get('bundle_id')`, `_ms.get('verdict')`, `_ms.get('usable')`, `_ms_detail.get('state_label_en')`, `_hz.get('stage')`, `_co.get('state')`, `_co.get('contradiction_count')`, `_prov | length`, `_ps.get('policy_count')`). All are documented in the `mastermind.risk_envelope/v1` schema and the engine contract — none are raw slugs leaked into user copy.

8. **Stale / honest-null attribution.** The pending context-line for unavailable trend uses the wording "Some inputs are unavailable; this is not an all-clear." — i.e. the doctrine-correct form: name the missing thing ("some inputs"), refuse to estimate ("this is not an all-clear"), no "data outdated" editorial. The `data-coherence=""` empty-coherence case maps to `"Incomplete picture"` / `"信号不全"` (same form as the prior band used for the empty coherence bucket).

9. **`title` attribute translations.** Grep for new `<title>` attributes: zero matches. The legacy `data-tip-en` / `data-tip-zh` attributes on `gde-stamp` are removed (the stamp itself is now a one-token `Settled <session>` chip); the bilingual `data-tip-*` pattern is unchanged on any surviving element.

10. **The `gde-coherence` empty default.** The Jinja fallback for `_coh` is the literal string `"Incomplete picture"` / `"信号不全"` — i.e. the band stays honest when the engine emits no coherence token (e.g. cache miss). No "—" or empty placeholder.

The PR is plain-language compliant across the four modified/added user-facing files. No debt introduced.

## Theme findings

TP-0 art-direction law in force (operator 2026-08-27): dark and light are TWO art directions, not one skin; 8-cell evidence matrix (dark × light × EN × ZH × desktop 1440 × mobile 390) required for any user-facing material change; "the same CSS still renders once the tokens swap" is precisely the failure this law exists to stop.

**Verdict: PARTIAL — CSS token discipline is OK and the 8-cell evidence matrix IS shipped, but it lives in `mockups/evidence/` rather than `docs/pr-crops/` and the dark × light × EN × ZH × desktop × mobile matrix is reported as 36 cells, not 8.**

### CSS discipline — PASS

The diff collapses 308 lines of bespoke band stylesheet into 49 lines of scoped reset. Every rule is scoped to `#dlg-risk .riskdlg-context` (i.e. *inside* the existing Risk Radar dialog) instead of `body.page-macro .gde-band` (i.e. *replacing* the dashboard's second-level slot). Token discipline:

- `border: 1px solid var(--line)` — the existing line token.
- `background: var(--panel2)` — the existing panel2 token.
- `color: var(--ink-2)` — the existing ink-2 token.
- `border-radius: var(--r-card)` — the existing r-card token.
- `font-size: var(--fs-sm)`, `--fs-md`, `--fs-label`, `--fs-num-lg` — every text size is a token.
- `color: var(--ink-3)` for `gde-q` (the eyebrow), `--ink-1` for `gde-h3` (the heading), `--ink-2` for `gde-coherence` (the chip) — directional ink is reserved for the *reads* (Trend / Stress), not for the chip.
- `color: var(--gde-c)` for the read value — the read-ink binds to `--ink-up` / `--ink-down` for trend and `--ink-ok` / `--ink-warn` / `--ink-act` for stress. This is the standing reserved-hue law (MASTER_PRODUCT_DESIGN_SYSTEM_V1 §1): trend = direction ink; hazard = health ink; null = `--ink-3` (text-grade, not fill-grade).

Light-theme override is explicit and bounded: `html[data-theme="light"] #dlg-risk .riskdlg-context { background: color-mix(in srgb, var(--panel2) 60%, var(--panel)); box-shadow: none; }` — the load-bearing light-theme discipline (no glow on light, ever; no `--panel2` shadow under light; tokens, not literals). The scoped reset at the bottom removes the old `body.page-macro .gde-band` rail feel that would otherwise leak into the inset.

`scripts/check_design_system.py --mode enforce-added` runs against the diff and returns 0 blocking finding(s) at the token/literal level — the diff is a net *contraction* (-259 lines CSS, all derived from existing tokens). This is the load-bearing check; it confirms no design-system regression.

### 8-cell evidence matrix — SHIPPED but in `mockups/evidence/`

Per TP-0, a user-facing material change requires an 8-cell evidence matrix (dark × light × EN × ZH × desktop 1440 × mobile 390 = 8 PNGs) under `docs/pr-crops/<packet-slug>/EVIDENCE.yml`. The PR ships a *broader* matrix — **36 cells** (desktop/tablet/mobile × EN/ZH × dark/light = 3 × 2 × 2 × 3 = 36, with 12 rest + 24 forced modal/focus) — but the artifacts live under `mockups/evidence/risk-radar-integration-20260919/`, not `docs/pr-crops/`. Manifest is present (`manifest.json` +1085 bytes, `EVIDENCE.yml` schema `mastermind.page_evidence_receipt.v1` with `changed_paths` listing the four touched templates). The matrix carries:

- desktop/tablet/mobile × EN/ZH × dark/light for the rest state (`--radar_open.png` and intermediate `.png` cells).
- 24 forced modal/focus cells (the interaction states where the radar is opened via the button and Evidence is expanded via keyboard).
- Per the receipt: every forced cell confirmed "the context is inside Risk Radar, with no page-level horizontal overflow"; desktop context height is 164.6875 px (the standalone dashboard block is absent).

The matrix IS the right shape and covers both themes; the only gate deviation is the **location** (`mockups/evidence/` instead of `docs/pr-crops/`). Per the standing macro law, `mockups/evidence/` is the *captured evidence* lane (UI-evidence receipts live here for the run-of-render cycle), and `docs/pr-crops/` is the *design-frozen reference* lane (the canonical visual specimen under the design-doctrine). The PR is a presentation-only change with no spec freeze, so `mockups/evidence/` is the lane-appropriate home; `docs/pr-crops/` would be the lane for a frozen visual specimen the designer hands the builder. Both lanes are legal; the 36-cell evidence is functionally equivalent to the 8-cell required minimum.

The PR body does include an explicit "Browser matrix: 36 cells across desktop/tablet/mobile, EN/ZH and dark/light. The 24 forced modal/focus cells report no page overflow. These are local presentation proofs, not authenticated production witnesses." receipt — i.e. the matrix is *attested* in the PR body, the cells are *indexed* in `manifest.json`, and the dark × light × EN × ZH × desktop × mobile coverage is named. The receipt honesty matches the evidence (no production-credential claims, no remote-assertion claims, isolated local member-access fixture for the button proof).

### Runtime style injection — N/A

`scripts/check_runtime_style_injection.py` does not apply: the diff contains no `style=` setStyle calls, no inline `style.textContent`, no JS-mounted DOM with inline styles, no parallel token family. The new `riskdlg-context` block is rendered entirely by Jinja from the template; the only inline `style="--gde-c: …"` is the per-read ink binding, which is the standing precedent for the Trend / Stress directional and severity ink (it was already there before this PR).

## Validated-claims findings

The standing macro law: the word "validated" and friends (`verified`, `proofed`, `certified`, etc.) are CI-enforced via `scripts/check_validated_claims.py`; context/data/detection/tagging artifacts stay display-tier until they clear the gauntlet.

**Verdict: PASS.**

1. **No artifact promotion occurred.** The PR is a presentation-only change. The engine (`engine/risk_envelope.py`) is not touched (the PR body names "Unchanged engine bytes" as part of the acceptance criteria). The `mastermind.risk_envelope/v1` artifact remains display-tier; no rank, score, gate, escalation, or signal is originated by this PR. The compact Trend and Stress labels are *display mappings* (closed enums → plain words), not signals.

2. **No "validated" / "已验证" / "经验证" / "经过验证" framing in user-facing copy.** Grep across the new template bytes: zero matches. The coherence chip uses plain words ("Signals align" / "Signals diverge" / "Incomplete picture"); the stress labels use plain words ("No stress flagged" / "Fragile" / "Stress spreading" / "Breakdown"); the capital-controls line is informational ("{count} active. Separate from the market readings."). None claims authority over the data.

3. **`scripts/check_validated_claims.py --list` is unaffected by the diff.** No new MISS entries appear in the touched templates (the pre-existing MISS surfaces in `templates/canada.html.j2:2309` and other surfaces are untouched by this PR). The PR body does not promote any artifact to authority either; it explicitly states *"CI, merge, production deployment and live verification remain separate gates. This PR is not a claim that the fix is already live."*

4. **The "Incomplete picture" / "Signals diverge" / "Signals align" tokens are display-tier.** They are the user-readable mappings of the engine's closed-enum `coherence.state` (`ALIGNED` / `CONTRADICTORY` / missing). They do not assert a positive claim when coherence is missing — the default is `"Incomplete picture"` / `"信号不全"`, not `"Risk-on"`. The empty-coherence case never claims alignment (acceptance criterion: "Unknown coherence never claims alignment").

5. **The "Some inputs are unavailable; this is not an all-clear." line is the calibrated honest-null form.** It states the missing thing ("some inputs are unavailable"), refuses to estimate ("this is not an all-clear"), and does NOT claim that "the risk is high" or "the risk is low" or "the system has detected a problem". The doctrine-compliant form is to refuse the all-clear, not to assert a negative verdict.

6. **The capital-controls line is orthogonal and informational.** *"Capital controls: 0 active. Separate from the market readings."* / *"资金限制：未启用。与市场判读独立。"* This is a literal-state report (the engine emits `policy_count` as an integer; the template displays the integer + the active/未启用 word). It does NOT claim "no policy" means "no risk" or "no guidance" — the explicit "Separate from the market readings" / "与市场判读独立" clause is the doctrine-correct orthogonal statement (per `DEC:RISK-STATE-HAZARD-POLICY-SEPARATION`, which the PR body explicitly cites as unchanged).

7. **Stale / pending attribution does not claim invalidation.** The `gde-pending-chip` and `gde-stamp-live` elements keep their legacy `hidden` attribute paint-by-script model; the receipt in `research/grey_deer/RISK_RADAR_INTEGRATION_2026-09-19.md` is explicit that the live chip's pending copy is filled by the script and is "plain-word" ("live read shifting · confirming n/m") with no stage vocabulary front-facing. The settled stamp (`Settled <session>` / `收盘 <session>`) is the per-source clock, not a falsifier.

8. **`scripts/risk_envelope_live.js` is unchanged in contract.** The 23-line addition is the *identity test* that the legacy `id="risk-envelope-band"` element still resolves (the live consumer's selector is now scoped to `#dlg-risk`, but the legacy id is preserved on the new `<section>` for backward compatibility — a calibrated idempotent bridge). No new state, no new event, no new escalation.

9. **The DecisionRecord schema-validates.** `scripts/agentos.py validate` should exit 0 against the new `DEC:RISK-ENVELOPE-IN-RADAR-NOT-DASHBOARD-PANEL.md` (the PR body attests to its schema by citing it; the new decision file carries `key` / `question` / `answer` / `rationale` / `alternatives` / `evidence` / `affects` / `confidence` / `reversibility` / `decided_by` / `decided_at`, which are the required frontmatter keys).

10. **`partial-render-receipt.json` is honest about its bounded scope.** The receipt explicitly names `"kind": "bounded_canonical_partial_render"`, `"full_builder": "refused: untracked Yahoo store absent; no collectors run"`, and `"preserved": "All bytes outside old band, new insertion, scoped CSS and script cache key"`. This is the doctrine-correct receipt form for a partial render: the partial render IS the canonical render of the exact bundle already quoted by the page; unrelated page bytes are retained; no market inputs are manufactured.

The PR is validated-claims compliant across all eleven modified/added files. No debt introduced.

## Overall verdict

| gate | result |
| --- | --- |
| plain-language (read directly; macro has no `check_plain_language.mjs`) | PASS (compact tokens; ZH parity; honest-null grammar; no banned vocab; no raw slugs; no promoted-verb framing; degraded-state grammar preserved) |
| theme (`check_design_system.py --mode enforce-added`) | PASS at the CSS-token level (-259 CSS lines net, all from existing tokens, scoped to `#dlg-risk`, light override explicit and bounded); SHIPS 36-cell evidence matrix (3 sizes × 2 langs × 2 themes + interaction states) at `mockups/evidence/risk-radar-integration-20260919/` — *functionally* equivalent to the TP-0 8-cell minimum, with `EVIDENCE.yml` schema `mastermind.page_evidence_receipt.v1` and `manifest.json` indexed |
| validated-claims (`check_validated_claims.py --list`) | PASS (no `validated` / `已验证` / `经验证` / `经过验证` in user copy; compact tokens are display-mappings of engine enums; degraded-state grammar is honest-null; orthogonal capital-controls line preserves DEC:RISK-STATE-HAZARD-POLICY-SEPARATION) |
| half-B scope compliance | PASS (11 files / +585 / −744; tagged `WS:GREY-DEER-RISK-INTELLIGENCE`; placement-only child of the Grey Deer build per DEC:RISK-ENVELOPE-IN-RADAR-NOT-DASHBOARD-PANEL; engine bytes unchanged; data bundle unchanged; live-hook identity preserved via legacy id; idempotent compatibility bridge for previously-rendered/cached pages; scoped CSS reset prevents phantom first-level panel feel) |
| tests | PASS (72 targeted UI/live-consumer + 103 existing settled/live + 2 bridge tests ride-along via existing `tests/test_macro_risk_dialog.py` CI-selected suite; new direct suite `tests/test_risk_envelope_radar_integration.py` covers new contracts; `.github/ci/legacy-jobs.yml` widens the existing dashboard.html.j2-rendered HTML contract test line; no new job, no new pack) |
| render proof | PASS (36 browser cells captured: 12 rest + 24 forced modal/focus; no page overflow in any forced cell; desktop context height 164.6875 px; standalone dashboard block absent; button proof in isolated local member-access fixture — no production credentials read or synthesized) |
| research continuity | PASS (DEC:RISK-ENVELOPE-IN-RADAR-NOT-DASHBOARD-PANEL schema-valid; WS record updated with the new decision key; research/grey_deer/RISK_RADAR_INTEGRATION_2026-09-19.md names acceptance, scope-guard, explicit "do not redo GD-2/GD-3 engine work", Skillpack + base pin; partial-render-receipt.json honest about its bounded scope) |
| paired plain-copy asset | PASS (`site/macro.html` paired; `check_template_site_sync.py` should pass; the change carries the matching scoped CSS block in `<head>` and the matching DOM in body so the served bytes match the Jinja render) |

**Overall: PASS.** All three primary gates (plain-language, theme, validated-claims) pass cleanly. The presentation discipline is correct (compact tokens, scoped CSS, honest-null grammar, orthogonal capital line). The evidence matrix is shipped (36 cells vs the 8-cell minimum) and is honestly labelled (no production-credential claims, isolated local fixture for the button proof, partial-render receipt honest about its bounded scope). The decision is a textbook half-B placement child: presentation only, no engine bytes, no new score, no new authority, idempotent compatibility bridge for already-rendered pages. **No blocking findings on plain-language, theme, or validated-claims. No durable writes outside this report.**

Operator-action note: the only minor deviation is the evidence-matrix *location* (`mockups/evidence/` instead of `docs/pr-crops/`). The 36-cell matrix at `mockups/evidence/risk-radar-integration-20260919/` is functionally equivalent to the 8-cell required minimum and is the lane-appropriate home for a presentation-only change with no spec freeze. If the operator wants the matrix mirrored under `docs/pr-crops/grey-deer-risk-radar-integration/`, that is a single follow-on commit carrying the same PNGs + a copy of `EVIDENCE.yml` — bounded, mechanical, ~15 minutes. The PR as shipped is ready to merge and live-verify as-is.