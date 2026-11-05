# Product Experience Blueprint — Grey Deer × Leadership Rotation

**State:** design proposal, not an edited Paper file, rendered screenshot, user-tested prototype or production UI. **Owner:** existing Macro Risk Radar/Sector Central, Terminal and Mastermind consumer paths; original product/design owners retain release custody. **Principle:** *extremely simple at first glance, extraordinarily powerful underneath.*

Fable may improve or replace the proposed composition. These scenarios specify **information meaning and usability outcomes**, not fixed artboard coordinates, new routes, a mandatory dashboard or a new component framework.

## 1. User tasks and proposed information architecture

| Person / situation | Asked in their own words | Successful moment | Failure to prevent |
|---|---|---|---|
| Concentrated semiconductor/AI investor | “The index still looks okay—are the leaders breaking?” | Separate market state and specific leadership deterioration, actual session/coverage and what is not known | Current-looking composite headline hides ten-day-old rotation feed |
| Sector/theme analyst | “Where is leadership moving and is it durable?” | Two absolute legs, same-clock relative wealth and short-vs-long disagreement, membership/benchmark | Positive relative return mistaken for real money flowing or gains |
| Returning mobile user | “What changed since I last looked?” | Latest **eligible observed change**, current source time, old unresolved receipt, direct next meaningful action | Blank page/skeleton erases severe warning or announces the same stale event |
| Portfolio/watchlist holder | “Do my holdings matter here?” | Existing authorized exposure concentration view, with no invisible inferred trade permission | Unreviewed sizing, naked-options or automatic exit prompt |
| Subscription user | “Can I opt in, quiet it or stop it?” | Family/category/global choice, known activation, quiet-hour behavior, corrections/history | A delayed settings save silently re-enables after opt-out |
| Evidence challenger / policy reviewer | “What was known then and what was corrected?” | Original, first-recorded, first-published, served and delivered timestamps separated | Reconstructed backtest dressed up as old user warning |

These are **programme-derived personas, not interview findings**. Candidate flow can fit within Risk Radar’s compact inset and Sector Central movement, using existing Terminal sector BFF and Mastermind decision context. Avoid another full-width Grey Deer panel or duplicate rotation map unless a user test demonstrates need. [Macro #7480](https://github.com/mastermindx-market-intelligence/macro/pull/7480) records the prior risk band move into Risk Radar; [#10103](https://github.com/mastermindx-market-intelligence/macro/pull/10103) already renders descriptive pair context separately from confirmed events.

## 2. Proposed glance → brief → study hierarchy

### Glance: 5-second answer

A compact existing-page element conveys:

1. **What scope?** “US Technology leadership” vs “Broad US market,” not generic red risk.
2. **What changed?** A plain sentence from a qualified observation, or “Rotation data unavailable” when no qualifying observation exists.
3. **How current?** Actual source market session, source availability qualifier and quality state; a displayed build time is secondary.
4. **What does that mean?** Informational *watch/context*, not crash odds or a capital instruction.
5. **Where next?** One route to evidence or exposure review, with no pressure to trade.

Do not make a quiet market headline suppress a qualified sector-specific observation. Conversely, if the sector input is stale, show scoped unavailability; do not infer sector weakness from the current Oct30 envelope alone.

### Brief: 20–60-second guided understanding

A single coherent presentation or drawer (Fable chooses) gives:

- **Two independent headings:** “Market trend: Mixed” and “Transition fragility: Fragile,” each with source name and market session, plus data-quality status. A `NORMAL` policy footer means “no restriction active,” not “risk passed.”
- **Leadership facts:** actual name/cohort/event, breadth/participation and historical transition context, no invented degree of predictive confidence.
- **Relative/absolute comparison:** receiver vs donor symbol/sector, both leg returns, denominator/benchmark and exact 2-session window. If both are negative but relative positive, the first-line copy explicitly says “both fell, one fell less.”
- **Horizon conflict:** one vs two vs five vs twenty sessions where eligible. Contrary direction receives equal evidence status rather than hidden behind a tiny tooltip.
- **Disconfirming evidence:** broad-market gate, independent credit/vol/breadth contexts, data lag, missing theme members, or conflicting source lineage; never majority-vote correlated prices into consensus.
- **Invalidation/repair:** what would change the observation, its expiry/revision, what is unconfirmed. Repair only if current canonical owner has qualified it.
- **Next action:** “Review source evidence,” “See affected exposure,” “Manage observations,” or “Explore sector,” not “Sell now.”

### Study: full evidence with provenance

On demand, expose event ID, definition/version, market calendar, normalized numerator/denominator, both close basis and adjusted-price caveat, source timestamps, coverage roster/missingness, original vs corrected/reconstructed, immutable source refs/hash, rights/redistribution, historical availability, correlated ancestry, stable links to source and scientific disposition. This depth must be reachable by keyboard/touch and not hover-only.

**Design freedom:** Fable can invert which surface hosts glance vs brief, combine cards, use compact typography, or choose a no-alert comparative monitor if it produces better comprehension; maintain meaning and source identity through navigation.

## 3. Concrete user journeys to test

### Journey A — quiet index but qualified sector deterioration (future eligible event)

1. User enters Macro US Risk Radar. Whole-market Risk Radar may remain **Caution**, because its SPY/breadth broad gate is not tripped.
2. A **separate** source-qualified sector watch names the specific fresh `rotobs_` event and market session; neither says “market crash imminent” nor changes Radar score.
3. User opens brief and sees both absolute legs with same-clock relative ratio, short and long disagreement, and one alternate explanation (e.g., rates rather than defensive rotation) where supported.
4. User expands evidence, sees availability `available_at`, first recorded/published and correction status, or a frank “original availability unknown.”
5. User opens existing watchlist/portfolio exposure *only if authenticated and entitled*. No market-level ranking or trade permission is created.
6. Back returns to the same Risk Radar scroll/selection. A correction is a new documented state of the same event, not a new fabricated original.

**Negative:** no qualifying fresh sector record means no watch headline even when a stale public file has a strong 2S number; render a transparent missing-context state.

### Journey B — two legs down; relative shelter

Set a synthetic test fixture with receiving sector -1.0%, donor -3.0% over the exact same two-session window: relative wealth `(0.99/0.97)-1 ≈ +2.06%`. Say “both fell; the receiving sector fell less,” not “defensive sector gained 2.06%.” Show the actual sign, window, denominator and alternate benchmark. If legs have unequal end sessions, **withhold** a same-clock ratio or show ineligible reason.

This is a **synthetic explanation fixture**, not observed market data or a preselected trading threshold.

### Journey C — partial, stale, contradictory envelope

Use actual tracked Oct30 source snapshot as a specimen (not live proof): market `MIXED`, hazard `FRAGILE`, leadership Oct30, Radar Oct30, rotation **Oct20 stale**, repair absent, zero active policy. A user should articulate in their own words:
- Some current sources see fragile internals even though headline market remains mixed.
- Rotation-specific evidence is not current; one cannot confirm a *new* sector observation from it.
- No active policy does not mean safety or permission to trade.
- “Produced Oct31” cannot erase the Oct20 source lag.

Try a simulated reversed-order response (Oct29 after Oct30) and malformed/future date. Older data may remain last-qualified history but cannot replace current source as if fresh. No transient quiet skeleton may clear a severe unresolved warning.

### Journey D — sign in, consent, one natural event, correction and withdrawal

1. Anonymous user can inspect permitted public description, but not protected portfolio or subscriber details.
2. User deliberately enables the rotation family via the reviewed existing consent path; server returns authoritative revision and activation time. Baseline is **non-notifying**.
3. A later *naturally recorded* qualified observation results in one logical user-scoped `fire_event_id` row under existing outbox; quiet hours/entitlement/suppression act at admitted send time.
4. User receives a bilingual readable message and opens authenticated event deep link retaining same observation ID and source version.
5. If the event is corrected/withdrawn, show the original issued text/history and its current disposition; if the original email was sent, deliver a separately qualified correction where authorized; do not claim email retraction.
6. User opts out globally/category/family (or changes entitlement); a stale other-tab language save must not resurrect activation. A pending ineligible send stays suppressed. An SMTP uncertain effect remains visible to operator and cannot blind retry.

**Cannot be claimed complete** from a DB outbox row, CLI send or preview screenshot alone. Requires signed-in, naturally sourced, opted-in path and negative send controls.

### Journey E — Terminal/Mastermind same evidence, different view

From the exact Macro event ID/deep link, Terminal Sector Intelligence reads the existing BFF and displays the same qualified observation with its own source-retrieval status, not a recomputed severity. Mastermind Market View/Decision Context incorporates the same immutable source ancestor in an actual captured initial prompt, with staleness and contradiction given to the model. If another source generation slips in between, either a qualified join is explicitly performed or the combined claim is **withheld**—never borrow a same-date label as proof of shared capture.

## 4. State and transition matrix — required semantics

These are **visual/product acceptance cases**, not a proposal to add backend states. Run each applicable state across English/Simplified Chinese, light/dark, desktop/mobile, plus keyboard, screen reader and reduced motion. Tests are *planned*, not executed in this packet.

| State | Required visible meaning | Do not do | Interaction/recovery |
|---|---|---|---|
| First baseline / no eligible new record | “No new eligible change recorded” with current source coverage | “No risk” or a backfilled notification | Show known context; no toast/email |
| Fresh sector watch, market Caution | Explicit different scope/target/horizon | Overwrite whole-market Radar or claim crash odds | Inspect source/event; other path unaffected |
| Existing severe market warning | Visible until owner-qualified resolve/expiry; acknowledgement separate | Let news/refresh/close erase it | Evidence and acknowledgement separate keyboard controls |
| Partial/missing required source | Source name, as-of, remaining valid findings, unknown reason | Quiet all-clear from zero/null | Read last-qualified with age, retry view, no new alert |
| Stale source inside new envelope | Component-specific old source date prominent | Imply all components current because bundle produced today | Scoped degraded explanation |
| Cross-horizon disagreement | 2S and 20S both signed and identified | Average/collapse to false consensus | Compare time windows and end sessions |
| Relative shelter / both down | Both absolute negatives, positive relative difference | “Gain” or “inflow” | Side-by-side comparison and glossary |
| Market risk-on or mixed + hazard fragile | Orthogonal honest readings | Raise policy or pick one “true” score | Trend vs hazard explanation |
| Current data malformed/future/cross-market | `UNAVAILABLE` / ineligible source and retained historical context if allowed | Coerce market, fabricate fallback or clear severe receipt | Visible problem + safe recovery |
| Loading / network failure | Preserve last qualified receipt with verification age | Blank/confident spinner hiding uncertainty | Accessible status once; retry/re-auth |
| Correction / withdrawal | Original issue, revision, reason, current disposition | Backdate or overwrite history; resend as new event | Linked timeline, optional corrected notice |
| Reconstructed/estimated past value | Labeled hypothetical/reconstructed and source rights | Attach today's rebuilt coordinate to original event | Separate view/toggle, no issued-alert badge |
| Repair forming/confirmed/failed | Exact owner-qualified stage, conditions met/unmet | Derive confirmation from price rebound or “caution” | Compare hazard vs repair, invalidation |
| Consent off/on/revoked | Authoritative family/category/global permission and epoch | Bundle opt-in with dismiss; stale metadata as authority | Confirmation/revocation readback |
| Quiet hours / entitlement withheld | Not sent, next eligible review if policy permits | Pretend deferred = delivered | User-visible status and controls |
| SMTP unknown/failed/accepted | Different logical outbox, provider admission, mailbox receipt | Blind retry after ambiguous DATA ack; claim exactly once | Operator quarantine, non-sensitive audit |
| Anonymous / 401 / 403 / expired | Sign-in or entitlement state precisely | Pass protected payloads through public fallback | Return to originally requested event |
| Empty universe / holiday | Market schedule and coverage, no false zero observation | Generate synthetic “no rotation” from exchange closure | Context and next valid session |

### State combinations to prioritize

- `MIXED + FRAGILE + PARTIAL + stale rotation + NORMAL policy` (actual Oct30 tracked specimen).
- `RISK_ON + qualified sector deterioration + no broad loud market alert`.
- `both legs negative + relative positive + 20S contradiction`.
- `old severe pending + current malformed calm refresh`.
- `future/foreign market envelope + independently valid market state`.
- `opt-out concurrent with pending send`, plus delayed stale metadata language PUT.
- `corrected pre-opt-in original` after new activation.
- `available source + anonymous paywall` vs `unavailable source + entitled user`.
- `screen reader announcement + high-frequency passive refresh`, and reduced-motion representation.

## 5. Translation and microcopy contract

Examples below are **optional design copy**, contingent on source qualification; do not treat as actual future warnings.

| Intent | English | 简体中文 |
|---|---|---|
| Glance (actual mixed/fragile type) | Mixed market · Fragile internals | 市场信号不一 · 内部结构脆弱 |
| Source limitation | Rotation context is from Oct 20; other inputs are from Oct 30. | 轮动依据截至10月20日；其他依据截至10月30日。 |
| Policy limitation | No capital restrictions are active. This is not an all-clear. | 当前没有生效的资金限制；不代表风险已经解除。 |
| Evidence | Review what changed | 查看变化依据 |
| Qualified future sector watch | Technology leadership is weakening. | 科技板块领涨趋势正在减弱。 |
| Absolute shelter | Both sectors fell; defensives fell less. | 两个板块都下跌；防御板块跌幅较小。 |
| Freshness unknown | First public availability could not be verified. | 首次公开可用时间尚未核实。 |
| Watch vs forecast | This is an observation, not a crash probability. | 这是已观察到的变化，不是崩盘概率预测。 |
| Conflicting horizon | The two-session move conflicts with the 20-session trend. | 两个交易日的变化与20个交易日趋势不一致。 |
| No evidence | Rotation evidence is unavailable, not proof of stability. | 轮动依据暂不可用，并不代表市场稳定。 |
| Correction | This observation was corrected; the original notice remains in history. | 这条观察已更正；原通知仍保留在历史记录中。 |
| Opt-in | Notify me of future qualified sector changes. | 当未来出现符合条件的板块变化时通知我。 |
| Consent revoked | Rotation notifications are off. Pending unapproved messages will not be sent. | 板块轮动通知已关闭；尚未获准发送的待发消息将不会发出。 |
| No auto-trade | Review your exposure; no portfolio action was taken. | 请检查持仓敞口；系统未执行任何交易。 |

**Localization risks:** directional gain/loss colors can differ by market convention, but *hazard* and *quality* states must remain named text, icon or shape, not solely red/green. Preserve sign, numeric unit, exchange calendar, session and timezone, not “today/yesterday” after locale shifts. English/ZH sentences must claim exactly the same causal, predictive and policy limits; avoid translating “relative shelter” as “safe haven” or “early context” as “certain risk-off.”

## 6. Visual composition and source tokens

Verified reuse pointers at Macro main `d533508a4e66e4abece8cac91466660b679bff9e`:

- [`templates/theme.css`](https://github.com/mastermindx-market-intelligence/macro/blob/d533508a4e66e4abece8cac91466660b679bff9e/templates/theme.css): `--font-ui`, `--font-mono`, `--fs-*`; base surfaces `--bg/panel/panel2/line`; health `--warn/act/ok`; directional `--up/down`; context `--link/info`; `--ink-warn`, `--prov-ink`.
- [`_risk_envelope_band.html.j2`](https://github.com/mastermindx-market-intelligence/macro/blob/d533508a4e66e4abece8cac91466660b679bff9e/templates/_risk_envelope_band.html.j2) and [CSS](https://github.com/mastermindx-market-intelligence/macro/blob/d533508a4e66e4abece8cac91466660b679bff9e/templates/_risk_envelope_band.css.j2): existing `.riskdlg-context`, `.gde-reads`, `.gde-disc`, `.gde-tblwrap`, `.gde-button-context`; already includes contrast/focus/detail treatment.
- [`templates/rotation_events.js`](https://github.com/mastermindx-market-intelligence/macro/blob/d533508a4e66e4abece8cac91466660b679bff9e/templates/rotation_events.js): `#rc-events-mount`, `.rc-early-context`, `.rc-ec-pair`, bilingual detail/windows. Its four-day stale code uses **UTC calendar days**, not proven market sessions.
- [Design doctrine](https://github.com/mastermindx-market-intelligence/macro/blob/d533508a4e66e4abece8cac91466660b679bff9e/docs/DESIGN_DOCTRINE.md) and [Master product design system](https://github.com/mastermindx-market-intelligence/macro/blob/d533508a4e66e4abece8cac91466660b679bff9e/research/MASTER_PRODUCT_DESIGN_SYSTEM_V1.md): glance/brief/study, plain language, restrained accents, evidence integrity, no decorative colored edges.
- [Specimen](https://github.com/mastermindx-market-intelligence/macro/blob/d533508a4e66e4abece8cac91466660b679bff9e/mockups/design_system/specimen.html) and [macro reference](https://github.com/mastermindx-market-intelligence/macro/blob/d533508a4e66e4abece8cac91466660b679bff9e/mockups/design_system/macro_reference.html) are design exemplars **with illustrative data**, not currently served product acceptance.
- [#8132 briefing](https://github.com/mastermindx-market-intelligence/macro/blob/639aaed06ce7754110d3bd6e94a0b704bb6c7760/research/grey_deer/RISK_WARNING_CAPITAL_PROTECTION_BRIEFING_DESIGN_2026-09-27.md) supplies prior composition ideas, but its “reduce gross/stand aside” language is not authorized by this descriptive tier.

**Verify in actual CSS cascade before using** `--r-card`, `--r-ctl`, `.mx-vh` or `.mx-disc`; the targeted source scan did not establish globally defined tokens/classes even though parts of the envelope consume them. Do not invent approval of such primitives.

### Responsive and accessibility outcomes

- **Desktop:** compare two legs and relevant horizon conflict without hiding the absolute basis; one stable detail region. The product remains meaningful with optional panels collapsed and under wide data tables. Avoid nested dashboards competing for attention.
- **Mobile:** one column, clear scope and source date, compact action; comparison can stack but must preserve labels for both legs and the denominator. Evidence remains a native tappable disclosure, not a hover-only chart tooltip. Maintain context when auth/locale changes.
- **Keyboard:** stable tab order, visible focus, Enter/Space open, Escape close, return focus to opener, no invisible severe alert behind modal or focus trap. Correct announcement of loading, completion and errors.
- **Screen reader:** risk and data quality are text/semantic status, comparison table headers associate units and source clocks, change announcements are rate-limited not spammed. A “mixed market/fragile internals” contradiction is readable linearly.
- **Reduced motion:** any pulse or transition enhances but never supplies the only new-warning meaning; reduced-motion state preserves full content.
- **Light/dark:** tokens generate readable surfaces; do not adjust hazard stage based on theme. Test focus, muted body, badges, table, severity, links and form disabled states.
- **WCAG 2.2 source basis:** [W3C status messages](https://www.w3.org/WAI/WCAG22/Understanding/status-messages.html), [use of color/contrast](https://www.w3.org/TR/wcag/) favor accessible status updates, non-color-only meaning and readable contrast; this is *design guidance*, not tested WCAG conformance.

## 7. Testable storyboard / design-review rubric

| Exercise | User should answer (without digging into source code) | Reject if |
|---|---|---|
| Five-second glance | Scope, what changed, what remains uncertain | They say “confirmed crash soon,” “all clear,” or can't identify source age |
| Side-by-side ratio | Which leg gained/lost absolutely and what relative outperformance means | They call both-down positive an absolute gain or fund inflow |
| 2S vs 20S | Why short-term shift might not be durable | Conflict is omitted or indicated by color only |
| Consent/revocation | Will I get a new event? How do I stop it? | Opt-out is bundled with dismiss, or hidden advanced settings |
| Correction history | What was first issued and what was changed later? | Later correction backdates original watch |
| Portfolio context | Which page is informational vs authorized policy? | UI implies trade execution or automatic sizing |
| Partial and offline | What do we still know, and what can’t we verify? | Stale/no data reads as healthy calm, or skeleton clears severe |
| Cross-product handoff | Does Terminal/Market View refer to the same qualified event? | Same date but different bundle silently merged |

A designer may use Paper for prototypes only under verified original file/editor ownership. **No Paper artboard, screenshot, visual QA, user interview, WCAG test, deployed code, or authenticated browser journey was produced in this preparation.** Fable should commission those as gated deliverables when the source contract stabilizes.

### What Fable may freely change

The overall layout, copy tone, alert terminology, object/card boundaries, microinteraction and animation, account-consent affordance placement, the mix of Sector Central vs Risk Radar emphasis, and how much evidence is initially visible. The acceptance criteria are **semantic clarity, source honesty, consistent identity, non-dangerous response and tested usability**, not pixel-level obedience to this proposal.
