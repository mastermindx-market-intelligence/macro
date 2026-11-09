# P0 — Rates & Inflation workflow design (prepare · explain · inspect)

Task-graph row **P0** of the 2026-10-13 Rates & Inflation e2e masterplan (immutable copy:
`research/rates_inflation_command/e2e_20261013/MASTERPLAN.md` @ `fd5c6600`, §13 row P0, acceptance A34).
Seat: Fable Meta-CEO `fc3dfe4b`. Surface census: read-only lane `ric-p0-census-1` against
`origin/main` `3e5b68f3` (PASS-WITH-GAPS). Basis vocabulary: `B0_BASIS_CONTRACT_FREEZE.md`
(`rates_command_basis.v1`, same directory). Research gates: `E0_RESEARCH_PROTOCOL.md`.

This is a design specification for three user workflows on surfaces that already exist. It adds
no page, no navigation family, no route, no data plane and no score. P1 and P2 implement it.

---

## §0 Acceptance gates — P1/P2 are NOT DONE UNLESS

Every implementing PR carries these in its body with evidence. A missing row is `PARTIAL`, never `PASS`.

1. **Real numbers, matched basis.** At least one real, source-backed comparison renders on the live
   site with target, model, vintage, basis and rights reachable in one hover (A36). A fixture-only or
   all-empty shell fails this gate.
2. **First viewport is useful (A34).** At 1440 and at 390, the first visible state of each workflow
   names the thing (release / print / curve), gives one plain-word stance, and shows no reason code,
   enum, slug or untranslated statistic. Status codes live only in the hover receipt.
3. **Unknown stays unknown (A38, A03).** A missing source, target, vintage or basis renders as the
   plain unknown state. No defaulted label ("ZQ"), no zero, no interpolated look-alike.
4. **No forced path or cause.** `not_identified` and `feasible_alternatives` show the alternatives;
   a single policy path or single attribution never appears unless the basis module returned
   `identified_conditional` with its assumptions in the hover.
5. **No unearned accuracy.** No accuracy badge, MAE, hit-rate or "beats" copy appears for any target
   whose E1 verdict is not reached (E0 §6). Legacy-epoch scores read as an earlier method.
6. **Before / first print / revision / current (A37).** The explain-print history shows each as its own
   column; a revised value never overwrites the first print.
7. **Rights before read (A41).** Nothing whose `rights` is not `public_official` is baked into the open
   HTML; machine export refuses `rights_unknown`; anonymous visitors see an honest sign-in state.
8. **Both art directions (TP-0).** Dark and light are judged as designs, with the evidence matrix in
   §10 posted as crops in the PR body: 3 workflows × dark/light × EN/ZH × 1440/390.
9. **Keyboard and focus (A35).** Every hover receipt is reachable by keyboard (focus opens it, Esc
   closes it); every dialog restores focus to its opener on close; tablet width (768) does not clip.
10. **No GRI.** `regime_outlook` is neither rendered nor altered (issue #8317 family stays separate).

---

## §1 What this design is for

The principal job is **correct interpretation**: what a release is expected to show, what it did
show against what we and others expected on the same measure, and what the rates market priced
before and after — with the honest limit of what the evidence identifies. The surfaces exist; what
is missing is that the qualification (target, model, vintage, basis, rights) currently falls off
between the data and the glass (census §"Dropped fields").

Three workflows, one per user moment:

| Workflow | User moment | Existing home |
|---|---|---|
| **W1 Prepare** | "A release is coming — what should I expect and how sure is it?" | Events row `#sx-events-v2` → `#dlg-events` / `#rr-inline`; Release Radar modal |
| **W2 Explain** | "It printed — was it a surprise, on which measure, and against whom?" | Same cards after the print; RR modal History tab |
| **W3 Inspect** | "What is the curve / futures strip pricing, and what moved?" | Fed card `#sx-v5-fed` → `#dlg-fed`; `macro_rates_curves.html` |

Progressive disclosure follows `docs/DESIGN_DOCTRINE.md` exactly: Tier 1 glance (always visible,
hard word budgets), Tier 2 LENS hover (`data-tip-en/zh` + `data-tip-rc-*` receipt, ~80 words),
Tier 3 study (dialogs, modal tabs, the curves page).

---

## §2 Surfaces and entitlement map (census @ `3e5b68f3`)

| Surface | Source | Public HTML | Payload | Notes |
|---|---|---|---|---|
| macro.html Fed card `#sx-v5-fed` | `templates/dashboard.html.j2:11426-11554` | 200 | `rates_command` baked (`scripts/build_site.py:6586-6595`) | Fed dialog `#dlg-fed` :14450; ZQ static copy :14004; Kim-Wright hover :14733; FOMC trading-day chip :11922-11931 |
| macro.html Events row `#sx-events-v2` | `dashboard.html.j2:9050` → `#dlg-events` | 200 | `release_forecast` via `/macrodata/` | Inline radar `#rr-inline` :12564-12592; standalone `#release-radar` :9490 is off-screen on mx4-grid (:3026) |
| Release Radar modal | `dashboard.html.j2:10951-10956` (5 tabs) | 200 | same | `intervalConeSVG` :10270-10322; `modelDotPlot` :10326; `scoreboardBlock` :9749-9786 |
| macro_rates_curves.html | `scripts/build_macro_suite_pages.py:220`, `_curve_panel.html.j2` | 200 | `/macrodata/workspaces/rates_curves/US/latest.json` → 401 anon | CMT nodes only; no SR3, no fitted par/zero, no ACM |
| Release publications hydrator | `templates/release_publications_live.js` | 200 | `live/release_publications.json` 200 public | America/New_York; 60 s poll; carries `official_embargo_at`, `source_released_at`, `parser`, `actual`, `reference_period` |

Entitlement: HTML is open; `/macrodata/` payloads are registered-Free (`app/paywall.py:162`).
Anonymous `release_forecast` returns `401 {"locked":true,"reason":"authentication_required","signin_url":"/?signin=1"}`.

**Defects this design resolves (owned by P1 unless noted):**

- D-1 Anonymous radar shows "Release Radar data not yet available" (:11245) on a 401 — dishonest.
- D-2 A missing Fed-path source becomes the label "ZQ fed-funds futures" (`engine/rates_inflation_command.py:847-848`, static copy :14004) — A03. B0 already fixes the producer; P1 removes the template default.
- D-3 `scoreboardBlock` binds `our_mae`/`naive_mae`, absent on `last_scored` rows whose `target_epoch` is legacy — accuracy shown as current (F1 owns the producer label; P1 owns the glass).
- D-4 RR `days_to` counts calendar days from the producer's `today`; the live embargo time is ignored.
- D-5 Target, model epoch, vintage, inputs hash, methodology status and `accuracy_claim` exist in the payload and are not rendered anywhere.

---

## §3 Shared grammar

### 3.1 The comparison bridge (the one signature element)

Every place two numbers are set against each other, they are joined by a small **bridge glyph** whose
shape is the B0 `ComparisonStatus`. It is the only new visual idea in this spec; everything else is
existing components. It says, before any words, whether the user may read the gap.

| Status | Glyph (12 px, inline SVG) | Glance words EN | Glance words ZH | Gap shown? |
|---|---|---|---|---|
| `directly_comparable` | solid span ─ | Same measure | 同一口径 | yes |
| `comparable_after_transformation` | span with a node ─●─ | Comparable after adjustment | 调整后可比 | yes, hover names the adjustment |
| `not_comparable` | broken span ─ ─ | Different measures — no gap shown | 口径不同，不作比较 | **no** |
| `not_identified` | fork ─< | Several paths fit | 多种路径均可解释 | alternatives, never one |
| `unavailable` | dotted ···· | Not available yet | 暂无数据 | no |

Colour: glyph uses `--muted`; the fork uses `--ink-info`. The glyph never uses up/down colour — a
comparison's legitimacy is not a direction. Raw reason codes (`basis_mismatch:rate_index`,
`unknown_basis:vintage`, `rights_unknown`) appear only in the LENS receipt line `data-tip-rc-*`.

### 3.2 Evidence class → who is speaking

| `EvidenceClass` | EN label | ZH label |
|---|---|---|
| `official_measurement` | Official figure | 官方数据 |
| `house_estimate` | Our estimate | 本站估计 |
| `market_implied_expectation` | Priced by futures | 期货定价隐含 |
| `survey_participant_projection` | Fed officials' projection | 美联储官员预测 |
| `estimated_decomposition` | Model estimate | 模型估算 |
| `hypothetical_scenario` | What-if | 假设情景 |

These are the only speaker labels on Tier 1. A number with no speaker label is a defect.

### 3.3 Value state and quality

| `ValueState` | Tier 1 | Tier 2 receipt |
|---|---|---|
| `present` | the number | as-of, vintage, source |
| `missing` | "Not published yet" / "尚未公布" | expected time (ET) |
| `withheld` | "Held back" / "暂不显示" | the reason in one sentence |
| `stale` | number + quiet `.dtp-chip.stale` "as of Oct 9" | last good vintage, why |
| `refused` | "Not shown" / "不予显示" | rule + reason code |

Quality flags: `stale` and `fallback_strip` change the meaning, so they earn a Tier-1 chip
("as of …", "backup source" / "备用数据源"). `carried`, `interpolated`, `proxy_vintage`,
`accuracy_withheld`, `benchmark_only`, `experimental` live in the receipt only.

Rights on the glass: `public_official` carries no mark. `redistribution_limited` and `display_only`
add a receipt line "View only — not in downloads" / "仅供浏览，不含于下载". `unknown` adds
"Source terms unconfirmed — not in downloads" / "数据来源条款待确认，不含于下载". The rights line never
appears on Tier 1.

### 3.4 Stance vocabulary

Only the doctrine's vocabulary: **Get ready** / 准备 · **Watch — don't chase** / 观察，勿追 ·
**Stand aside** / 观望 · **Ignore** / 忽略. This programme never emits Act or Protect gains: it
interprets releases and pricing, it does not size trades (commission exclusion).

---

## §4 W1 — Prepare for a release

**Home:** events row card face in `#sx-events-v2`; detail in `#dlg-events` → `#rr-inline`; deep detail
in the RR modal (Overview / Models / Components / History / Context).

### Tier 1 (card face)

```
┌───────────────────────────────────────────────┐
│ CPI next Wednesday            ⏱ 2d 14h · 8:30 ET │   title ≤4 words + embargo clock chip
│ Our read 0.3% m/m ─ Cleveland 0.28%            │   speaker labels + bridge glyph
│ Get ready — close to outside reads, wide range │   stance + plain reason ≤14 words
│ Our record on this measure is still building.  │   footer ≤1 sentence
└───────────────────────────────────────────────┘
```

ZH: 「下周三公布CPI」 / 「本站预估 环比0.3% ─ 克利夫兰联储 0.28%」 / 「准备 — 与外部预估接近，区间较宽」 /
「本口径的预测记录仍在积累中。」

Rules:

- **Title** names the release and the day in words ("CPI tomorrow", "PCE Friday"); ≤4 words.
- **Clock chip** counts down to `official_embargo_at` in ET from the live hydrator; when the embargo
  time is absent it falls back to labelled calendar days at the explicit display cutoff ("~3 days",
  receipt "calendar days from Oct 13 build") — never an unlabelled `days_to` (D-4, A05).
- **Our read vs outside read** shows our `projection.point` and one benchmark, joined by the bridge.
  The benchmark is a named single source (Cleveland nowcast where available). A blended or averaged
  "consensus" is never shown (A12); `street_consensus='unavailable'` is honoured — no street number.
- **Stance** is Get ready when the release is ≤3 trading days out, otherwise Watch — don't chase.
  The plain reason uses the interval width in words ("narrow / usual / wide range") — no p-values.
- **No accuracy badge** while `methodology_status.accuracy_claim =
  withheld_until_clean_aligned_forward_evidence` (D-3, E0 §6). The footer says the record is building.

### Tier 2 (LENS hover on the read line)

≤80 words, in this order: target ("CPI-U all items, m/m, seasonally adjusted, first print"); model
("our model — current method since Oct 2026", from `model_epoch`); vintage/cutoff ("inputs to Oct 13
close; built Oct 13 22:10 ET"); range ("80% range 0.1–0.5%"); benchmark provenance ("Cleveland Fed
inflation nowcast, Oct 12"); rights line when not `public_official`. Receipt line (`data-tip-rc-*`):
`target=mom_sa_pct · epoch=<target_epoch> · inputs=<hash[:8]>`.

### Tier 3 (RR modal)

- **Overview:** the existing interval cone, labelled with its target; the benchmark dot plot keeps
  every benchmark as its own dot with speaker label — never a mean line.
- **Models:** per-model rows with `model_epoch`; legacy-epoch rows carry "earlier method" / "旧方法".
- **Components / Context:** unchanged content, plus the target/vintage header line.
- `reaction_sensitivity` is labelled "past reactions — descriptive, not a forecast" /
  "历史市场反应——仅作描述，非预测" (E0 H3).

### States

| State | Tier 1 |
|---|---|
| Signed in, forecast present | as above |
| Anonymous (401 `authentication_required`) | Title + clock chip stay (public calendar). Read line: "Sign in free to see our read" / "免费登录查看本站预估", linking `signin_url`. Never "not yet available" (D-1). |
| Forecast withheld / abstained | "We are not publishing a read for this one" + hover reason |
| No forecast model for this release | Calendar row only; no read line, no placeholder |

---

## §5 W2 — Explain a print

**Home:** the same card face flips after the print; history in the RR modal History tab.

### Flip rule

The card flips to the print only when the live hydrator carries a parsed `actual` with
`reference_period` matching the forecast's period **and** the basis module returns a comparable status
for `forecast_vs_first_print.v1`. Between the embargo time and that moment the card shows a quiet
"Read being updated" / "数据更新中" chip (the existing specimen chip) — never a stale forecast dressed
as a result, never a guessed print.

### Tier 1 (after the print)

```
┌───────────────────────────────────────────────┐
│ CPI came in hot               printed 8:30 ET │
│ Official 0.4% m/m ─ our read 0.3%  (+0.1)      │   bridge solid → gap shown
│ Watch — don't chase: one month, range was wide │
│ Revisions and market reaction in the detail.   │
└───────────────────────────────────────────────┘
```

ZH: 「CPI高于预期」/「官方数据 环比0.4% ─ 本站预估0.3%（+0.1）」/「观察，勿追：仅一个月，预估区间本就较宽」/
「修正与市场反应见详情。」

- The words "hot / cool / in line" derive only from the matched-basis gap against our read and against
  the named benchmark, with the interval: inside the 80% range = "in line" / "符合预期".
- Up/down colours follow the convention per locale: EN green-up/red-down tokens; ZH 红涨绿跌. Inflation
  "hot" is not coloured as good or bad — the gap number carries `--ink-warn` when outside the range.
- A forecast from a legacy epoch shows "earlier method — not scored" / "旧方法，不计分" in place of the gap,
  with the reason in the hover (E0 §6; DEC:RIC-E0-RETROSPECTIVE-FALSIFIES-PROSPECTIVE-PROMOTES).
- `cpi_vs_pce.v1` and `cpi_month_vs_breakeven_10y.v1` are `not_comparable`: if a consumer pairs them,
  the broken bridge shows and no gap is printed.

### Tier 3 — History tab (A37)

One row per release; columns are distinct facts, never merged:

| Period | Before (our frozen read) | Outside read (named) | First print | Revised | Current | Status |
|---|---|---|---|---|---|---|

`Status` cell = bridge glyph + glance words. "Revised" is empty until a later vintage exists and is
labelled with its vintage date in the hover. A revision never overwrites the first print, and
scoring always uses the first print (E0).

### What repriced (deferred)

"What the market did" needs P2/X1/E1. Until they land, the slot renders the existing `.mx-empty`
state: "Market reaction view is still being built" / "市场反应视图建设中" with `.mx-empty-why`
"We only show reactions once timing and coverage are checked." No placeholder chart.

---

## §6 W3 — Inspect the curve and the policy path

**Home:** Fed card `#sx-v5-fed` (glance) → `#dlg-fed` (study) and `macro_rates_curves.html` (curve study).

### Tier 1 (Fed card)

```
┌───────────────────────────────────────────────┐
│ Fed path: two cuts priced          FOMC Oct 29 │
│ Futures average 4.07% Dec ─< several paths fit │   fork glyph when not identified
│ Watch — don't chase: pricing, not a promise    │
│ Officials' year-end projection in the detail.  │
└───────────────────────────────────────────────┘
```

ZH: 「联储路径：期货定价两次降息」/「12月期货隐含平均 4.07% ─< 多种路径均可解释」/「观察，勿追：是定价，不是承诺」/
「官员年底预测见详情。」

- "N cuts priced" appears only when the basis module returns `identified_conditional`. Otherwise the
  title reads "Fed path: easing priced" / "联储路径：期货定价宽松" and the read line carries the fork.
- The source label comes from the qualified row (`source_en`/`source_zh`). When the source is None the
  line reads "Futures source unavailable" / "期货数据源暂缺" — never a defaulted "ZQ" (D-2, A03).

### Tier 3 (Fed dialog) — drawing rules

| Element | Drawn as | Never |
|---|---|---|
| ZQ month (`market_implied_expectation`, monthly-average EFFR) | a plateau bar spanning the calendar month at the average | a step path or a meeting-dated jump |
| Policy path `identified_conditional` | one dashed path; hover lists the assumptions (effective dates, pre-change rate, EFFR–midpoint spread) | drawn without its assumptions |
| `feasible_alternatives` | 2–4 thin paths of equal weight, caption "Several paths fit the same prices" / "同一组价格可对应多种路径" | one path emphasised over others |
| `inconsistent` / `missing_inputs` | plateaus only + `.mx-empty-why` line naming the missing input | any path |
| SEP (`survey_participant_projection`) | dots at year-end only; hover "Officials' projection for year-end — not a promise" / "官员对年底的预测——并非承诺" | dots on meeting dates; joined to the futures line |
| SR3 (compounded SOFR) | its own row, label "SOFR futures — a different rate" / "SOFR期货——不同的利率" | overlaid on the funds plateaus (`sr3_vs_zq.v1` not_comparable) |
| Monthly-average witness | Study-tier footnote, once: "A month averaging 4.25% can be 15 days at 4.50% then 15 at 4.00% — a 50 bp cut, not 25." | — |

`zq_month_vs_policy_midpoint.v1` without an explicit `effr_minus_midpoint_bp` returns
`not_identified`: the dialog then shows the plateau and the target range side by side with the fork,
not a computed gap.

### Tier 3 (curves page)

- CMT nodes labelled "Treasury par yields (constant maturity)" / "美国国债恒定期限票面收益率". Par, zero and
  forward are never on one axis without the bridge (`par_vs_zero.v1` not_comparable).
- Inflation compensation is labelled as such ("Inflation compensation (breakeven)" / "通胀补偿（盈亏平衡）"),
  never "expected inflation"; hover notes it contains risk and liquidity premia
  (`inflation_compensation.v1`).
- Term premium: Kim-Wright and ACM side by side as **two model estimates**, caption "Two models,
  different answers" / "两种模型，结论不同". Never summed, never averaged (`term_premium_kw_vs_acm.v1`).
- "What moved the 10-year": `yield_move_attribution.v1` returns `not_identified`; the panel lists the
  alternatives in words ("+30 bp could be +10 expectations and +20 term premium, or −10 and +40") with
  the fork glyph. No single attribution bar.
- `regime_outlook` is not rendered on this or any W3 surface.

---

## §7 Rights, bake rule and anonymous state

1. **Bake rule.** Server-baked HTML (`build_site.py` → open macro.html) may carry only values whose
   `rights == public_official`. Every other value hydrates on the client from the existing gated
   `/macrodata/` copy of the same payload. No new endpoint, no new gate (no new auth plane).
2. **Export rule.** Any machine projection or download built from these rows runs the basis module with
   rule purpose `export`; `rights_unknown` refuses (B0 refusal order step 2). The refusal row stays in the
   projection as a refusal, not a silent omission.
3. **Anonymous honesty.** On a 401 `authentication_required`, the surface renders the sign-in state from
   §4 with the payload's `signin_url`. A 5xx or network failure renders "Couldn't load our read — retrying"
   / "暂时无法加载，正在重试" — distinct from the sign-in state and from "not published".
4. **Cleveland nowcast rights.** Until R1/G0 records its rights stanza, the nowcast is `rights=unknown`:
   it displays to signed-in users with the "Source terms unconfirmed" receipt line and is refused for
   export. It is not baked into open HTML.

---

## §8 Art direction — dark and light are two designs

Shared across both: information architecture, tiers, glyph shapes, copy, state meanings, ordering.
Tokens extend `templates/theme.css` only (`--bg`, `--panel`, `--panel2`, `--text`, `--muted`, `--line`,
`--up`, `--down`, `--warn`, `--ink-up/down/warn/ok/act/info/link/orange`). No new palette family,
no runtime stylesheet in page JS.

| Mechanism | Dark — command center | Light — research workspace |
|---|---|---|
| Card material | existing panel luminance step (`--panel` over `--bg`) | white panel, 1 px `--line` hairline, soft shadow instead of glow |
| Clock chip | `.dtp-chip` with restrained glow when ≤24 h | same chip, hairline border, no glow |
| Interval cone | translucent fill, low alpha | diagonal hatch with hairline edges (prints and photocopies legibly) |
| Feasible alternative paths | thin, low-alpha strokes in `--ink-info` | graphite dashed strokes (`--muted`), equal weight |
| ZQ plateaus | filled bars, luminance edge | outlined bars, hairline fill |
| SEP dots | hollow, `--text` stroke | solid graphite dots |
| Bridge glyph | `--muted`; fork `--ink-info` | same tokens; stroke 1.25 px for hairline parity |
| Withheld / unknown states | `.mx-empty` dimmed text | `.mx-empty` on white with hairline divider |

Degraded states per theme: stale chip and "backup source" chip use `--warn` text in dark and a `--warn`
hairline outline in light (no fill), so the chip never reads as an alarm in light mode.

ZH uses 红涨绿跌 for directional numbers in both themes; glyphs and stance words are uncoloured.

---

## §9 Layout, responsive and keyboard

- Card faces keep their current grid slots; no card grows past its current height at 1440. At 390 the
  read line wraps to two lines at most; the stance line truncates never — the footer drops first.
- Tablet 768: the Fed dialog's plateau chart keeps month labels legible by thinning to every other month.
- The bridge glyph has an accessible name equal to its glance words (`aria-label`), so the comparison
  status is read by screen readers before the second number.
- LENS receipts open on focus and close on Esc; dialogs restore focus to the opening card (A35).
- Bilingual text uses paired `.l-en`/`.l-zh` spans (`t(en, zh)` macro); no translated text in `title=`.

---

## §10 Evidence matrix and visual verification

Posted as crops in each implementing PR body (P1 and P2), against fresh `origin/main` render output:

| | dark EN 1440 | dark ZH 1440 | light EN 1440 | light ZH 1440 | dark EN 390 | dark ZH 390 | light EN 390 | light ZH 390 |
|---|---|---|---|---|---|---|---|---|
| W1 prepare (signed in) | | | | | | | | |
| W1 prepare (anonymous) | | | | | | | | |
| W2 explain (after print) | | | | | | | | |
| W3 inspect (Fed card + dialog) | | | | | | | | |

Plus: one keyboard walk (Tab to card → hover receipt → open dialog → Esc → focus back) per workflow,
and one tablet (768) crop of the Fed dialog. A reviewer `PASS` requires both themes judged as designs,
not only "renders without error" (TP-0).

---

## §11 Field binding (payload → glass)

| Payload field | Where it lands | Tier |
|---|---|---|
| `release_forecast.upcoming[].target`, `target_epoch` | W1 hover target line; History status | 2 / 3 |
| `model_epoch`, `code_receipt`, `inputs_hash` | W1 hover model line; receipt | 2 |
| `methodology_status.accuracy_claim` | gates any accuracy display; W1 footer | 1 |
| `methodology_status.street_consensus` | suppresses any street number | — |
| `projection.point`, `p10…p90` | W1 read line; range words; cone | 1 / 2 / 3 |
| `benchmark_set.cleveland_nowcast` (+ rights) | W1 outside read | 1 |
| `last_scored[]` (actual, first print, frozen projection, epochs) | W2 History columns | 3 |
| `release_publications.official_embargo_at` | W1 clock chip | 1 |
| `release_publications.actual`, `reference_period`, `parser` | W2 flip rule | 1 |
| `rates_command.qualified_comparisons[]` | bridge glyph + glance words everywhere | 1 |
| `rates_command` rows `.basis` (evidence class, value state, rights, flags) | speaker labels, chips, receipts | 1 / 2 |
| `rates_command.countdown.source_cutoff` / `display_cutoff` | fallback clock label | 1 / 2 |
| `rates_command.regime_outlook` | **not rendered** | — |

---

## §12 Implementation slices

| Slice | Owner task | Content | Depends on |
|---|---|---|---|
| P1-a | P1 | Honest anonymous/error/withheld states (D-1); remove template "ZQ" default (D-2); legacy accuracy relabel (D-3) | B0 merged |
| P1-b | P1 | Bridge glyph + speaker labels + receipts on W1 and W3 glance tiers; embargo clock (D-4) | B0, T0 |
| P1-c | P1 | Fed dialog drawing rules (§6) with real ZQ/SEP rows and path status from the basis module | B0, D1/Y1 |
| P1-d | P1 | W2 flip rule + History columns (A37) on real first-print data | B0, F0 coverage |
| P2 | P2 | "What repriced" panel replacing the §5 empty state | P1, X1, E1 |

Each slice is a builder packet with this file's §0 copied inline (spawn-handoff law) and the §10 matrix
as its visual acceptance. Design choices in this spec are frozen; a builder that finds one unworkable
stops and returns to the seat rather than inventing a substitute.

---

## §13 Not in this design

No new page, route, header family, dashboard, score, calendar, forecast, evaluator, publisher, auth
gate or control plane. No policy-timing predictor, no "probability of a cut" headline, no trade
stance beyond the doctrine's watch/ready vocabulary. No dealer/OPEX (original F2 is excluded, not
complete). No GRI rendering. No change to `regime_outlook`, the `asof` fallback or
`compact_state.usd_dir`.
