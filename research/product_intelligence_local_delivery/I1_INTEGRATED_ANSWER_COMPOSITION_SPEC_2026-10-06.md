# I1 integrated-answer composition spec (read-only, owner-gated)

**Inputs pinned:** I0 census head `779a9961689380efea2664175e5978bcf9ecb55e` (`origin/claude/mi-i0-integrated-answer-gate-census-20261006`). Macro main at authoring: `ca00b1c549733b562aae33d15f070300de3fb21e`. Package I law: gate on accepted H01/H04/H05/H06; consume by reference; no warehouse; no thesis mutation.

---

## §0 Acceptance gates (not buildable unless)

**Owner acceptance (I0 C0 on MAIN_PIN):**

- **H01 (MAS-268, financial query kernel):** not buildable unless **ACCEPTED** by WS:FINANCIAL-INTELLIGENCE-FABRIC / WS:FUNDAMENTAL-FORENSICS — **current: ACCEPTED** (`DEC:FIF-3A3-ACCEPTED-GOLDEN-QUERY-ON-MAIN`).
- **H04 (MAS-271, expectation / earnings display economics):** not buildable unless **ACCEPTED** by WS:EARNINGS-INTELLIGENCE-OS — **current: BUILT_NOT_ACCEPTED** (`engine/expectation_state.py`; E0 acceptance path absent on main; K3E held off main).
- **H05 (MAS-272, capital-structure qualification):** not buildable unless **ACCEPTED** by WS:CAPITAL-STRUCTURE-INTELLIGENCE-V2 — **current: ABSENT** (W4/W6 todo; no main artifact).
- **H06 (MAS-273, FIF publication / private-default seam):** not buildable unless **ACCEPTED** by WS:FUNDAMENTAL-FORENSICS — **current: BUILT_NOT_ACCEPTED** (default-off snapshots; no MAS-273 acceptance record).

**I0 freeze list (each blocks a composer lane until resolved):**

1. Canonical entitled READ surface identity chosen and recorded (today: **GAP** — no single nonbinding bundle on main).
2. Entitlement matrix frozen (teaser vs `require_site_full_user` vs Terminal) per `app/company_intelligence.py` and `app/forensics.py`.
3. H04 native expectation contract frozen (SRC-A1 vs held K3E) — **GAP** on main for full surface.
4. H05 debt/share qualification design accepted — **GAP** until W4/W6 land.
5. H06 publication seam accepted (`query_snapshots.py` default-off posture).
6. Per-component degraded-state copy for one answer — **GAP**.
7. Unified original/correction replay across readers — **GAP** (FIF revision vs event revisions).
8. Trace-to-span on every surfaced conclusion — **GAP** on public glance tiers.
9. Event-owner written acceptance before any persistent thesis field changes (`DEC:EARNINGS-EVENT-WORKSPACE-PUBLICATION-CONTRACT`).
10. MAS ↔ macro acceptance map — **GAP** (Linear IDs not in macro tree).

**Consumption law:** not buildable unless every leg is loaded by **reference** (immutable generation id, content hash, `as_of`, route) — never a copied warehouse row or merged authority state.

---

## §1 Question and refusals

**Answers (one sentence):** For one company (and optional theme lens), what nonbinding, display-tier context should an entitled reader see right now — financial facts, event workspace glance, expectation chips, theme membership, and tape context — with honest gaps when a leg is missing?

**Refuses:** trade instructions, sized positions, holdability scores, calibrated probabilities, fund-flow quantities, opportunity rankers, intraday-strength claims, LLM-originated escalation, or rewriting event/thesis storage. Instrument states (tripwires, expectation chips) are not market verdicts.

---

## §2 Composition graph (by reference only)

Each leg contributes a **pin** (schema key + generation_id or sha256 + `as_of` + freshness verdict). The composer holds pointers only; it does not re-derive owner math.

| Leg | Owner | Artifact / route | Read mechanism | Contributes | Must not use for |
|-----|--------|------------------|----------------|-------------|------------------|
| **H01** | WS:FINANCIAL-INTELLIGENCE-FABRIC; WS:FUNDAMENTAL-FORENSICS | `engine/fundamental_forensics/query.py`; `app/forensics.py` | POST `/api/forensics/v1/financial/query`; response generation + query `as_of` and health clocks | Point-in-time financial facts, spans, abstentions | Board order, alerts, sizing; authority beyond FIF acceptance |
| **H04** | WS:EARNINGS-INTELLIGENCE-OS | `engine/expectation_state.py`; `scripts/build_ticker_pages.py` | Module pins + nightly build id; per-ticker expectation panel is a served render artifact, not committed | Earnings-expectation chips (display-only) | Gates, rankers, Prophet floors (module law) |
| **H05** | WS:CAPITAL-STRUCTURE-INTELLIGENCE-V2 | n/a — no committed leg on main | — | Debt/share qualification when built | Any inference until owner ships W4/W6 |
| **H06** | WS:FUNDAMENTAL-FORENSICS | `engine/fundamental_forensics/query_snapshots.py`; `engine/fundamental_forensics/private_state.py`; `app/forensics.py` | Entitlement + publication flags; pin snapshot id | Whether private/default-off blocks a public leg | Leaking private purpose into anonymous tiers |
| **Event workspace** | WS:EARNINGS-INTELLIGENCE-OS | `engine/company_intelligence/event_workspace.py`; `engine/neuralweb/company_intelligence_reader.py` | `read_event_workspace` / `read_current_event_workspace`; manifest hash; workspace `as_of` | Canonical event glance, alias selection | Thesis **mutation** without owner acceptance |
| **Theme context** | WS:GMI-THEME-GRAPH | `engine/theme_context.py`; `site/basketdata/theme_context.json` | `read_context`; file `as_of` | Basket/theme tape context (display) | Scoring, ranking, escalation |
| **Company–theme exposure** | WS:GMI-THEME-GRAPH | `engine/company_theme_exposure/views.py`; `engine/company_theme_exposure/contracts.py` | `build_bundle`; strict closed keys; membership pin + generation | Membership projection, context-only authority | Thematic score, relationship model, extra wire keys |
| **Basket labels** | owner: not recorded (GAP) | `site/basketdata/baskets.json` | Read JSON by path; never inline copy into a warehouse | Labels and basket metadata for theme legs | Standalone “integrated score” |
| **Theme membership state** | owner: not recorded (GAP) | `site/neuralwebdata/theme_state.json` | Read JSON by path; never inline copy into a warehouse | Membership inputs for exposure/theme context | Standalone “integrated score” |

---

## §3 Conflict and precedence

When legs disagree, **dual-read leads**: name the user-visible tension in plain words (e.g., “event workspace still shows the prior quarter while expectation chips already moved”). The **state/instrument verdict is the footnote** (Tier 2 receipt: which schema, which `as_of`, which display-only flag). No silent winner-take-all merge. Precedence order for **surfacing** only: (1) entitlement refusals and H06 publication blocks; (2) newer `as_of` within the same schema generation family; (3) event-owner workspace for event-dated narrative; (4) FIF query facts for numeric financial claims; (5) theme/CTE `context_only` legs last. Never convert disagreement into a single calibrated probability or fused composite (`DNR:KILL-FUSED-COMPOSITE`, `DNR:KILL-CAUSAL-DAG-ALPHA`).

---

## §4 Honest-null matrix (Tier 1 EN / ZH)

For each §2 reader and state **absent**, **stale**, or **refused**: glance copy below or an explicit n/a line. **Coverage: 27 cells** (9 readers × 3 states).

| Condition | Glance EN | Glance ZH |
|-----------|-----------|-----------|
| Financial facts refused (entitlement) | “Financial detail isn’t available on this view.” | “此视图无法提供财务明细。” |
| Financial facts stale vs page stamp | “Financial facts are older than this page stamp — check the receipt.” | “财务事实早于本页时间戳，请查看来源说明。” |
| Earnings expectation absent | “Earnings expectation detail isn’t wired here yet.” | “盈利预期细节尚未接入。” |
| Earnings expectation stale | “Earnings expectation chips may be from an older build — check the receipt.” | “盈利预期标签可能来自较早构建，请查看来源说明。” |
| Earnings expectation refused | “Earnings expectation detail isn’t available on this view.” | “此视图无法提供盈利预期细节。” |
| Capital-structure leg absent | “Capital-structure context isn’t built yet.” | “资本结构背景尚未构建。” |
| Capital-structure leg stale | n/a — leg not on main | n/a |
| Capital-structure leg refused | n/a — leg not on main | n/a |
| Publication seam absent | “Account publication rules aren’t loaded for this answer.” | “本答复尚未加载账户发布规则。” |
| Publication seam stale | “Publication rules may be older than this page — check the receipt.” | “发布规则可能早于本页，请查看来源说明。” |
| Publication seam refused | “Some financial material is restricted on your account tier.” | “部分财务内容受账户权限限制。” |
| Event workspace absent | “No current event workspace for this company.” | “该公司暂无活动事件工作区。” |
| Event workspace stale | “Event workspace may be from an older quarter — check the receipt.” | “事件工作区可能来自较早季度，请查看来源说明。” |
| Event workspace refused | “Event workspace isn’t available on this view.” | “此视图无法提供事件工作区。” |
| Theme tape context absent | “Theme tape context isn’t available right now.” | “主题盘面背景暂不可用。” |
| Theme tape context stale | “Theme tape context may be dated — watch, don’t chase.” | “主题盘面背景可能已过期，宜观望。” |
| Theme tape context refused | “Theme tape context isn’t available on this view.” | “此视图无法提供主题盘面背景。” |
| Company–theme exposure absent | “Theme membership for this company isn’t available right now.” | “该公司主题归属暂不可用。” |
| Company–theme exposure stale | “Theme membership may be dated — watch, don’t chase.” | “主题归属可能已过期，宜观望。” |
| Company–theme exposure refused | “Theme membership isn’t available on this view.” | “此视图无法提供主题归属。” |
| Basket labels file absent | “Basket labels aren’t available right now.” | “篮子标签暂不可用。” |
| Basket labels file stale | “Basket labels may be from an older build — check the receipt.” | “篮子标签可能来自较早构建，请查看来源说明。” |
| Basket labels file refused | “Basket labels aren’t available on this view.” | “此视图无法提供篮子标签。” |
| Theme membership file absent | “Theme membership file isn’t available right now.” | “主题归属文件暂不可用。” |
| Theme membership file stale | “Theme membership file may be dated — check the receipt.” | “主题归属文件可能已过期，请查看来源说明。” |
| Theme membership file refused | “Theme membership file isn’t available on this view.” | “此视图无法提供主题归属文件。” |

Financial facts absent: n/a — accepted leg; composer attempts load when entitled. Display-only legs: stance **Watch — don’t chase**; footer “Heads-up only, not a buy signal.” / 立场 **观望，勿追**；脚注 “仅为提示，非买入信号。” Tier 2 hover carries generation ids, hashes, and study receipts per `docs/DESIGN_DOCTRINE.md` §1–2.

---

## §5 Freshness and coverage

Composer publishes one **page `as_of`** (ISO date or timestamp) ≥ max leg `as_of` used. Each leg declares fresh, stale, refused, or not-yet-built. SLA defaults (owner-adjustable): theme context and theme membership files **1 build day**; event workspace **current alias** only; FIF query **request-time cutoff**; expectation panel **nightly render build**. Coverage footnote when observation refusals or exposure warnings are non-empty: “Not everything below is published for every market.” Propagate `as_of` into every Tier 1 panel once.

---

## §6 Forbidden (package I + DNR)

No inferred fund-flow quantity; no calibrated probability; no new opportunity ranker; no holdability claim; no “intraday strength” wording; no statistical-approval claim wording on the integrated surface (the CI-banned promotion adjective in any case); no warehouse table or materialized integrated state table; no thesis field mutation from the composer; no second thesis lobe (`DNR:KILL-THESIS-LOBE`); no causal-DAG alpha (`DNR:KILL-CAUSAL-DAG-ALPHA`); no fused composite score across legs (`DNR:KILL-FUSED-COMPOSITE`). LLM may narrate **only** from pinned artifacts (A7); no new keys on the company–theme exposure wire contract.

---

## §7 Smallest first slice (after all §0 gates open)

**Route (proposed):** one entitled read `GET /api/integrated-answer/v1/{ticker}` (new handler beside `app/company_intelligence.py`, `require_site_full_user`, read-only).

**Reader set v0:** H01 golden query pin (fixed exemplar query id) + H04 expectation panel slice + `read_current_event_workspace` public glance + `theme_context.read_context` + CTE `build_bundle` single-ticker exposure pin — all by reference.

**Named tests (must pass before ship):** `tests/test_fundamental_forensics_query.py` (known-at / correction / unit mismatch cases cited in I0 Q5 #1–3,5,12); `tests/test_fundamental_forensics_health.py` (private leak); `tests/test_company_intelligence_event_workspace.py` (workspace schema); `tests/test_fundamental_forensics_query_snapshots.py` (generation mismatch); add one integration test asserting composer output pins hashes and refuses warehouse persistence (new file under `tests/`, owner-gated).

---

## §8 Open questions (yes/no to named owner)

1. **WS:EARNINGS-INTELLIGENCE-OS:** Will you accept H04 on main `expectation_state.py` alone as the integrated leg, without K3E, for v0? **Yes/No**
2. **WS:EARNINGS-INTELLIGENCE-OS:** Is `read_current_event_workspace` the only canonical event leg for package I? **Yes/No**
3. **WS:CAPITAL-STRUCTURE-INTELLIGENCE-V2:** Will W4/W6 ship a read-only artifact addressable like other legs before H05 counts accepted? **Yes/No**
4. **WS:FUNDAMENTAL-FORENSICS:** Does H06 acceptance require a new DEC explicitly blessing default-off snapshots for integrated glance? **Yes/No**
5. **WS:FINANCIAL-INTELLIGENCE-FABRIC:** Is POST forensics query the only H01 transport, or also a pinned GET snapshot? **Yes/No**
6. **WS:GMI-THEME-GRAPH:** Is Terminal `company-theme-context/[symbol]` the first consumer shell for the composed glance? **Yes/No**
7. **Meta-CEO / package I seat:** Is `OPEN_FOR_READ_ONLY_COMPOSITION` sufficient to authorize the §7 route before any thesis mutation? **Yes/No**
8. **WS:EARNINGS-INTELLIGENCE-OS:** Must integrated glance strip all Tier-3 receipts (current public workspace behavior)? **Yes/No**
9. **Meta-CEO / package I seat:** May the composer read `site/basketdata/baskets.json` and `site/neuralwebdata/theme_state.json` before an agentos owner is recorded for those paths? **Yes/No**

---

*End of spec — composition only; no executable shipped by this document.*
