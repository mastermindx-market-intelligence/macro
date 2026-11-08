# B20 DESIGN PACKET V2

STATUS: V2 COMPLETE

**Operation:** `prophet-us-fable-meta-ceo-20260923-001`

## 0. STATUS + BASE

**Status:** V2 — DIRECTION APPROVED (R6-B20-01); DESIGN ACCEPTED pending B16 captures + comprehension tests; NOT a D09 closure artifact; no builder consumes v1.

Binding seat records, read in order:

1. `research/prophet_v4/r6_program/rulings/R6-B20-01_DIRECTION_2026-09-23.md` freezes R-A..R-G.
2. `research/prophet_v4/r6_program/reviews/RV_7839_B20_V1_OPUS_2026-09-23.md` supplies B1–B3, M1–M14, and m1–m4.

Binding prior base:

- `research/migration_packets/MP-1-prophet-board.md` — route `/us_stocks.html`, discovery-board archetype, seven-cell lifecycle ladder, density/access law, and the ban on blended confidence numbers.
- `research/prophet_v4/EXPERIENCE_REFERENCE_COMPOSITIONS.md` §2/§10 — workspace intent and operators-only measurement law.

Reference crop files present after `python3 scripts/worktree_sparse.py add mockups`:

- `mockups/refs/institutionalize/us_stocks/DESIGN_NOTES.md`
- `mockups/refs/institutionalize/us_stocks/board-data.js`
- `mockups/refs/institutionalize/us_stocks/board.css`
- `mockups/refs/institutionalize/us_stocks/board.js`
- `mockups/refs/institutionalize/us_stocks/compare.html`
- `mockups/refs/institutionalize/us_stocks/index.html`

This is a design packet. It adds no route, stylesheet, JavaScript, token, data owner, permission, price, chart, production DDL, or deployment.

## 1. USER FLOWS

Every availability read is bound to `availability_state` from `engine/prophet_entry_availability.py`; the closed set is `AVAILABILITY_STATES`. No template consumes it today (`git grep -n availability_state -- templates | wc -l` = `0`). Consequently the **No read yet / 暂无判断** row is the default composition of every list; an `ENTRY_OPEN` row is an exception, never an assumed state.

1. **Find a displaced candidate:** scan All Candidates by lifecycle count, open a row, then judge whether the change and opposing facts displace its position.
2. **Understand a refusal:** open the expanded row. The plain sentence says what is missing, what is known, and the exact action state; a missing read says “No read yet / 暂无判断,” never “Wait.”
3. **Save to the correct list:** Watch opens the WatchStore list chooser, then confirms the owner and destination list.
4. **Recover the original thesis:** Track Record links the immutable decision record and separately marks later corrections; it does not rewrite history.
5. **Compare themes:** Themes groups candidates by shared driver, with the count ladder retained as the discovery identity.
6. **Check the workspace now:** Action Desk leads with availability, risk, and the next permitted research action; Radar groups fresh candidates without painting them as tracked records.

Disclosure uses inline expanded rows, never a cross-page overlay (R-B, `research/prophet_v4/r6_program/rulings/R6-B20-01_DIRECTION_2026-09-23.md`). The row expands beneath its row, keeps two columns at ≥1024px, collapses to one column below that, and links the full dossier at `/prophet/<T>`.

## 2. INFORMATION ARCHITECTURE

### Workspace route

The current US Prophet board route is `/us_stocks.html`, rendered from `templates/dashboard.html.j2` through the MP-1 shell beginning at line 16689; `scripts/build_site.py:7258` writes the destination.

- **Archetype:** discovery board.
- **In-page destinations:** Action Desk · Radar · All Candidates · Themes.
- **Track Record:** separate `/us_track_record.html` route (`templates/us_track_record.html.j2`), editorial/measurement archetype, linked from the workspace but not a tab.
- **Health & Receipts:** operators only; moved to the measurement surface per `research/prophet_v4/EXPERIENCE_REFERENCE_COMPOSITIONS.md:13`.
- **Identity device:** the seven-cell count ladder always identifies the discovery board.
- **Tab row:** present in every desktop and mobile composition; it scrolls horizontally at 390px and never replaces shared navigation.

### Disclosure law

- Row expansion is inline and visually owned by the row.
- At ≥1024px, its body is two columns: evidence and implications left; risks, conditions, and actions right.
- Below 1024px, the same body becomes one column in the same information order.
- The full dossier is `/prophet/<T>`; it may hold the complete history but never replaces inline evidence.

## 3. VOCABULARY

### Availability → stance → action → color (verbatim R-A)

| `availability_state` | Stance EN / ZH | Action-column label EN / ZH | Color role |
|---|---|---|---|
| `ENTRY_OPEN` | Act / 可行动 | Entry open / 入场窗口开启 | the only green (`--ink-ok`) |
| `APPROACHING_ENTRY` | Get ready / 准备 | Approaching / 接近入场 | neutral accent ink, never green |
| `NOT_READY` | Watch — don't chase / 观察，勿追 | Not ready / 尚未就绪 | muted ink |
| `WAIT_PULLBACK` | Watch — don't chase / 观察，勿追 | Wait for pullback / 等待回调 | muted ink |
| `RAN_DONT_CHASE` | Stand aside / 观望 | Ran — don't chase / 已启动，勿追 | muted ink |
| `INVALIDATED` | Ignore / 忽略 | Invalidated / 已失效 | struck stance, muted ink, no red alarm (`research/prophet_v4/r6_program/rulings/R6-B20-01_DIRECTION_2026-09-23.md` R-A) |
| `UNAVAILABLE_DATA` or no producer row | (no stance) No read yet / 暂无判断 | No read yet / 暂无判断 | muted ink, dashed leading rule |

Source: `research/prophet_v4/r6_program/rulings/R6-B20-01_DIRECTION_2026-09-23.md` R-A; annotations may cite the ruling without changing the seven rows above.

“Protect gains” is unused because V2 has no held-position surface. Delivery health is never green: healthy uses a neutral hairline check, degraded amber, failed red. Direction uses signed-change ink and never `--ink-ok`.

### Frozen lane labels

The lifecycle labels and order come from `research/migration_packets/MP-1-prophet-board.md` §4b: **Watch · Ready · Entered · Delivering · Overtime · Invalidated · Resolved**, with the EN/ZH pairs 观察 · 就绪 · 入场 · 达标 · 超时 · 失效 · 已结 preserved. `research/prophet_v4/r6_program/rulings/R6-B20-01_DIRECTION_2026-09-23.md` R-F freezes this source.

### Two-axis rule

- **Ladder = where:** the lifecycle cell says where the row sits in its journey.
- **Availability = whether:** the state says whether research permits action now.
- The two are always separate fields and never collapse into one color. A high ladder cell does not green an unavailable row; an available row does not change its ladder cell.

### User-copy ban list

| Banned user-facing term | Required replacement |
|---|---|
| stage / 阶段 (`research/prophet_v4/r6_program/rulings/R6-B20-01_DIRECTION_2026-09-23.md` R-F) | lifecycle step / 生命周期位置 |
| blended confidence number | one owner-backed score, or “No score yet / 暂无评分” |
| validated (`research/prophet_v4/r6_program/rulings/R6-B20-01_DIRECTION_2026-09-23.md` R-D) | checked / 已核对 |
| Promoted / 晋级 (`research/prophet_v4/r6_program/rulings/R6-B20-01_DIRECTION_2026-09-23.md` R-D) | moved to the next lifecycle step / 进入下一生命周期位置 |
| Control / control-only (`research/prophet_v4/r6_program/rulings/R6-B20-01_DIRECTION_2026-09-23.md` R-D) | research comparison / 研究对照 |
| producer | data source / 数据来源 |
| nomination | new candidate / 新候选 |
| episode | record / 记录 |
| receipt(s) / 凭据 | source note / 来源说明 |
| owner | source / 来源 |
| calibrated | checked against outcomes / 已按结果核对 |
| substitute read | No read yet / 暂无判断 |
| `UNAVAILABLE_FIELD` | No read yet / 暂无判断 |

## 4. COMPONENT MAP

All presentation lands through DS-PR-0 in `templates/theme.css`; B20 writes none of it. There are **ten NEW components**:

| Component | Purpose | DS-PR-0 dependency |
|---|---|---|
| `ProphetWorkspaceShell` | shared context, route links, and responsive destination row | workspace grid, focus ring, panel token mapping |
| `CountLadderIdentity` | seven-cell lifecycle identity with honest absent and withheld counts | ladder geometry, ghost treatment, count typography |
| `AvailabilityStance` | the seven-state stance/action pair and state ink | `--ink-ok`, accent/muted ink roles, strike treatment |
| `ProphetRow` | name · ≤14-word change · stance verb · action label · chevron | row grid, density rules, chevron/focus primitive |
| `ExpandedEvidenceRow` | inline two-column evidence, risks, conditions, and actions | expansion grid, hairline/luminance-step treatment |
| `ResearchOnlyChip` | read-only statement that no permission is granted | neutral chip and border/inset primitive |
| `AsOfStamp` | one publication stamp and stale/corrected marks | stamp typography, status ink, corrected mark |
| `WatchAction` | visible WatchStore action, disabled reason, and saved state | button, pending, failure, tombstone, focus primitives |
| `TierLockProphet` | honest entitlement boundary over `mx-tier-gate--prophet` | frosted/white overlay, `.mx-tier-gate--prophet` |
| `PreviewRowState` | the governed preview remainder under incumbent rollout controls | preview-row rule, count treatment, lock join |

`ProphetRow` is not `.mx-chg-row`: its five-cell anatomy is name, one-line change, stance verb, action label, and chevron. Six-field detail belongs only to `ExpandedEvidenceRow`.

Rollout and entitlement use incumbent controls named by `agentos/decisions/DEC-PROPHET-US-D11-RELEASE-PATH-INCUMBENT-CONTROLS.md`: `config.yml: us_board_gate.panels`, `panel_preview_rows`, same-PR `premium.enforced_early`, and the plans-page disclosure. A preview row remains visible with its count and lock; it never silently disappears.

## 5. DARK ART DIRECTION

Dark is a command center: calm luminance depth, restrained state color, and no glow for rank.

| Surface | Material and color bindings |
|---|---|
| Action Desk | rows on `--bg` (theme.css:63); expanded row one step up on `--panel2` (63); separators `--line` (69); only `ENTRY_OPEN` gets a restrained `--ink-ok` (373) left rule. |
| Radar | same row grammar; fresh candidates use a dotted `--line` leading rule, neutral `--text` (63), and no lifecycle color. |
| All Candidates | dense rows on `--panel` (63), luminance zebra with `--panel2` (63), hairlines `--line` (69), muted labels `--muted` (64). |
| Themes | muted caps with `--muted` (64); group bodies one luminance step up on `--panel2` (63); dividers `--line` (69). |
| Track Record | editorial column on `--bg` (63); panels `--panel` (63); dividers use `--line` (69); tabular figures inherit `--text` (63). |

### Dark degraded states

1. **Stale quote:** dimmed `--text` (`templates/theme.css:63`), amber hairline under price from `--ink-warn` (`templates/theme.css:372`).
2. **Required-source loss:** warm-tinted `--panel` (`templates/theme.css:63`) border with `--ink-warn` (`templates/theme.css:372`); border only, no glow.
3. **Disabled action:** 40% `--text`, no border, reason always visible.
4. **Entitlement ghost / TierLock:** frosted `--panel2` overlay one step lighter with `--line` edge.
5. **Invalidated row:** struck stance in `--muted`; no red alarm. `research/prophet_v4/r6_program/rulings/R6-B20-01_DIRECTION_2026-09-23.md` R-G.
6. **Missing read:** em dash plus “No read yet / 暂无判断” in `--muted`; never blank.
7. **Corrected value:** small “corrected / 已更正” mark in `--muted`; prior value remains available on hover.

## 6. LIGHT ART DIRECTION

Light is a research workspace: cool canvas, white material, hairline discipline, and shadow rather than glow.

| Surface | Material and color bindings |
|---|---|
| Action Desk | cool canvas `--bg` (210); white row material `--panel` (210); hairlines `--line` (218); `ENTRY_OPEN` keeps only the `--ink-ok` (373) left rule. |
| Radar | fresh candidates sit directly on canvas `--bg` (210), with dotted `--line` (218) rule and `--text` (210); no white panel and no lifecycle color. |
| All Candidates | white `--panel` (210) with `--line` (218) rows and no zebra; labels use `--muted` (211). |
| Themes | headers as caps directly on `--bg` (210); group bodies as white `--panel` (210) with `--line` (218) edges. |
| Track Record | editorial column on `--bg` (210); white `--panel` (210); hairline `--line` (218) dividers; tabular `--text` (210). |

### Light degraded states

1. **Stale quote:** grey `--muted` (`templates/theme.css:211`), amber left rule from `--ink-warn` (`templates/theme.css:372`).
2. **Required-source loss:** pale amber fill plus `--line` (`templates/theme.css:218`) hairline; no heavy shadow.
3. **Disabled action:** 50% `--text`, dashed `--line` hairline, visible reason.
4. **Entitlement ghost / TierLock:** white `--panel` overlay with blur and `--card-shadow` (236).
5. **Invalidated row:** struck stance in `--muted`; no red alarm. `research/prophet_v4/r6_program/rulings/R6-B20-01_DIRECTION_2026-09-23.md` R-G.
6. **Missing read:** em dash plus “No read yet / 暂无判断” in `--muted`; never blank.
7. **Corrected value:** small “corrected / 已更正” mark in `--muted`; prior value remains available on hover.

### Mechanisms intentionally different

- Depth: dark advances by luminance steps; light separates by hairlines, white material, and shadow.
- Emphasis: dark uses restrained rules/ink; light may use fill plus a hairline, but never glow.
- Radar otherness: dark withholds a luminance step; light withholds white material.
- All Candidates: dark zebra is luminance; light is hairline-only.
- Themes and Track Record: dark uses nested luminance; light uses canvas-versus-panel and hairline dividers.

## 7. COMPOSITIONS

Each matrix cell below is fully specified here; B16 owes one capture for each cell.

| Surface | Dark EN 1440 | Dark EN 390 | Dark ZH 1440 | Dark ZH 390 | Light EN 1440 | Light EN 390 | Light ZH 1440 | Light ZH 390 |
|---|---|---|---|---|---|---|---|---|
| Action Desk | SPECIFIED · capture owed at B16 | SPECIFIED · capture owed at B16 | SPECIFIED · capture owed at B16 | SPECIFIED · capture owed at B16 | SPECIFIED · capture owed at B16 | SPECIFIED · capture owed at B16 | SPECIFIED · capture owed at B16 | SPECIFIED · capture owed at B16 |
| Radar | SPECIFIED · capture owed at B16 | SPECIFIED · capture owed at B16 | SPECIFIED · capture owed at B16 | SPECIFIED · capture owed at B16 | SPECIFIED · capture owed at B16 | SPECIFIED · capture owed at B16 | SPECIFIED · capture owed at B16 | SPECIFIED · capture owed at B16 |
| All Candidates | SPECIFIED · capture owed at B16 | SPECIFIED · capture owed at B16 | SPECIFIED · capture owed at B16 | SPECIFIED · capture owed at B16 | SPECIFIED · capture owed at B16 | SPECIFIED · capture owed at B16 | SPECIFIED · capture owed at B16 | SPECIFIED · capture owed at B16 |
| Themes | SPECIFIED · capture owed at B16 | SPECIFIED · capture owed at B16 | SPECIFIED · capture owed at B16 | SPECIFIED · capture owed at B16 | SPECIFIED · capture owed at B16 | SPECIFIED · capture owed at B16 | SPECIFIED · capture owed at B16 | SPECIFIED · capture owed at B16 |
| Track Record | SPECIFIED · capture owed at B16 | SPECIFIED · capture owed at B16 | SPECIFIED · capture owed at B16 | SPECIFIED · capture owed at B16 | SPECIFIED · capture owed at B16 | SPECIFIED · capture owed at B16 | SPECIFIED · capture owed at B16 | SPECIFIED · capture owed at B16 |

### A. Action Desk 1440 EN dark

```text
┌ Shared authenticated navigation ─────────────────────────────────────────────┐
│ Prophet US · Research only · As of Sep 23, 2026 09:05 PDT                    │
│ Watch 21 │ Ready 9 │ Entered 3 │ Delivering 7 │ Overtime 4 │ Invalidated 2 │ Resolved 12 │
│ [Action Desk] [Radar] [All Candidates] [Themes]           Track Record →    │
├─────────────────────────────────────────────────────────────────────────────┤
│ AAPL   Services demand accelerated again        Act          Entry open   › │
│ ┌ expanded row: evidence + implications │ risks, conditions, actions ────┐ │
│ │ Watch · Full dossier at /prophet/AAPL                                │ │
│ └──────────────────────────────────────────────────────────────────────┘ │
│ MSFT   Cloud mix improved, but the price already ran. Watch — don't chase  › │
│ NVDA   No source note yet for this field.          No read yet            › │
└─────────────────────────────────────────────────────────────────────────────┘
```

### B. Action Desk 390 ZH light

```text
┌ 共享导航 ────────────────────────────────────────┐
│ Prophet 美国 · 仅研究 · 数据截至 9月23日 09:05   │
│ 观察21│就绪9│入场3│达标7│超时4│失效2│已结12      │
│ [行动台][雷达][全部候选][主题] →战绩              │
├─────────────────────────────────────────────────┤
│ AAPL 服务需求再次加速          可行动  入场窗口开启›│
│ └ 展开：证据│风险、条件、行动；完整档案 /prophet/AAPL│
│ MSFT 云业务改善，但股价已启动。 观察，勿追 等待回调›│
│ NVDA 此字段暂无来源说明。       暂无判断 暂无判断 ›│
└─────────────────────────────────────────────────┘
```

### C. Radar 390 ZH dark

```text
┌ 共享导航 ─────────────────────────────────────┐
│ Prophet 美国 · 仅研究 · 数据截至 9月23日       │
│ 观察21│就绪9│入场3│达标7│超时4│失效2│已结12    │
│ [行动台][雷达][全部候选][主题] →战绩           │
├──────────────────────────────────────────────┤
│ 新候选 · 生命周期：设置                        │
│ AMD  AI 服务器订单增长，但估值已高。  准备  ›  │
│ └ 展开：证据│风险、条件、行动                  │
│ ORCL 此字段暂无来源说明。       暂无判断 ›     │
└──────────────────────────────────────────────┘
```

### D. All Candidates 1440 EN light

```text
┌ Shared authenticated navigation ─────────────────────────────────────────────┐
│ Prophet US · Research only · As of Sep 23, 2026 09:05 PDT                    │
│ Watch 21│Ready 9│Entered 3│Delivering 7│Overtime 4│Invalidated 2│Resolved 12│
│ [Action Desk] [Radar] [All Candidates] [Themes]           Track Record →    │
├─────────────────────────────────────────────────────────────────────────────┤
│ Name    Change                          Lifecycle   Stance     Action       │
│ AAPL    Services demand accelerated     Ready      Act        Entry open   │
│ MSFT    Cloud mix improved, then ran.   Entered    Stand aside Wait pullback│
│ NVDA    No source note yet.             Watch      No read yet No read yet │
└─────────────────────────────────────────────────────────────────────────────┘
```

### E. Themes 1440 ZH dark

```text
┌ 共享认证导航 ────────────────────────────────────────────────────────────────┐
│ Prophet 美国 · 仅研究 · 数据截至 9月23日 09:05 PDT                           │
│ 观察21│就绪9│入场3│达标7│超时4│失效2│已结12    │
│ [行动台][雷达][全部候选][主题] →战绩                                         │
├─────────────────────────────────────────────────────────────────────────────┤
│ 人工智能基础设施 · 8                                                        │
│ │ NVDA AI 服务器需求继续增长。        可行动 入场窗口开启 ›                 │
│ │ AMD  此字段暂无来源说明。           暂无判断 暂无判断 ›                   │
│ 工业自动化 · 3                                                              │
│ │ ROCK 订单周期改善，但价格已经运行。  观望 已启动，勿追 ›                   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### F. Track Record 390 EN light

```text
┌ Shared authenticated navigation ───────────────┐
│ Prophet US · Research only · As of Sep 23, 09:05│
│ [Action Desk][Radar][All][Themes] →Track Record│
│ As of Sep 23, 2026 09:05 PDT                   │
│ Population · Ruler · Corrections               │
├────────────────────────────────────────────────┤
│ Sep 12 · Setup                                 │
│ Original thesis held for 9 days.               │
│ Corrected Sep 21 · Changed fact: supply slip.  │
│ Availability: No read yet                      │
│ No trade, fill, position, or plan is implied.  │
│ Watch · Not saved yet                          │
└────────────────────────────────────────────────┘
```

Remaining cells reuse the matching base above with these named deltas: language swaps the exact EN/ZH twin; width moves the tab row to horizontal scroll, stacks expanded evidence above risks, and preserves every mark; theme applies §5 or §6; surface substitutes its header and rows without removing navigation, tabs, chip, stamp, or default missing-read anatomy.

## 8. INTERACTION

**Static bake is the default** (R-E, `research/prophet_v4/r6_program/rulings/R6-B20-01_DIRECTION_2026-09-23.md`). The publication is static. V2 deletes the pulse, invalidation announcements, the “Updated” reorder button, and every live interaction. Keyboard focus and accessible status remain. Hydration only restores known UI state and **refuses a mismatched generation**.

Keyboard ownership is closed:

- A list owns `↑` / `↓` and moves focus between rows.
- An expanded row owns `←` / `→` and moves focus within its evidence/action cells.
- The tab row owns `Tab` / `Shift-Tab`; it never captures arrows.

Expansion state is local to the publication view and is announced as “Row expanded / 行已展开” or “Row collapsed / 行已收起.” A hydration mismatch does not reorder, repaint availability, or silently accept newer data.

## 8.1 BILINGUAL COPY

Every state has an exact twin; neither language invents a missing counterpart.

| State | EN | ZH |
|---|---|---|
| Empty Action Desk, no qualifying rows | Nothing to act on today. Rows appear here when an entry opens. | 今日无可行动项。入场窗口开启时会在此显示。 |
| Empty Action Desk, required source lost | The action list is unavailable. Required data did not load. | 行动列表暂不可用。必需数据未能加载。 |
| Empty Action Desk, no access | You have reached the limit for this plan. | 您已达到当前方案的上限。 |
| Empty candidates | No candidates match this filter. | 没有候选符合此筛选条件。 |
| Empty Themes | No themes have enough members yet. | 目前没有主题达到最低成员数。 |
| Empty Track Record | No records are ready to show yet. | 暂无可以展示的记录。 |
| Missing read | No read yet | 暂无判断 |
| Missing field | No source note yet | 暂无来源说明 |
| Stale | Price is stale | 价格数据已过期 |
| Failed source | Required data did not load. | 必需数据未能加载。 |
| Disabled save | Not saved yet | 暂未保存 |
| Save pending | Saving your list choice… | 正在保存您的列表选择… |
| Save failed | Your list choice did not save. Try again. | 您的列表选择未保存。请重试。 |
| Unwatched | Removed from <list> | 已从 <list> 移除 |
| Watch failed | Your change did not save. Try again. | 您的更改未保存。请重试。 |
| Local-only | Saved on this device only | 仅保存在此设备 |
| Hydration mismatch | This page cannot finish loading safely. Refresh it. | 此页面无法安全完成加载。请刷新。 |
| Corrected | Corrected · prior value available | 已更正 · 可查看原值 |
| Research only | Research only | 仅研究 |
| Publication stamp | As of <date time> | 数据截至 <date time> |
| Full dossier | Full dossier at /prophet/<T> | 完整档案 /prophet/<T> |

The first-visit empty Action Desk adds exactly: “Watch saves research to your list. It does not place a trade. / 关注会把研究保存到您的列表，不会下单。” The no-row line above is the mandatory onboarding line and always precedes that first-visit sentence.

## 9. USER ACTIONS

### Watch state machine (R-D)

```text
idle --click--> pending --success--> saved
pending --failure--> failed --retry--> pending
saved --unwatch--> unwatched --timeout--> idle
saved --unwatch failure--> failed
saved --offline/local-only--> local-only
```

| State | EN / ZH behavior |
|---|---|
| idle | Watch / 关注 |
| pending | Saving your list choice… / 正在保存您的列表选择… |
| saved | Saved to <list> / 已保存至 <list> |
| failed | Your list choice did not save. Try again. / 您的列表选择未保存。请重试。 |
| unwatched | Removed from <list> / 已从 <list> 移除; list-scoped tombstone permits Undo / 撤销 |
| local-only | Saved on this device only / 仅保存在此设备 |

A read never paints `Saved`; only a successful WatchStore write does. Unwatch produces a tombstone in the affected list, never a global removal mark. A pull never resurrects an unwatch tombstone; only an explicit re-watch in that same list can save the symbol again. WatchStore remains the owner, and Prophet adds no second save format.

Disabled copy is exactly **“Not saved yet / 暂未保存,”** with no decision ID and no arrival promise. The Reason/Note contradiction is removed: Reason states why the action is disabled now; Note holds only source context and never promises future data.

**Watch is research, not execution.** Copy never says buy, sell, position, fill, order, or trade. **Held-position management is RESIDUAL R-D1:** no V2 surface can safely own it because the product has no held-position owner. A future packet must name that owner before design.

## 10. COMPREHENSION ACCEPTANCE

1. Find a displaced candidate in fewer than 45 seconds and state why its position changed.
2. Explain a refusal from the expanded row: missing read, opposing fact, and action state.
3. Save an exact row to one of at least two named lists and retrieve it from only that list.
4. Recover the original thesis after a correction and distinguish it from later developments; an absent owner-backed read must assert the honest **“No read yet / 暂无判断”** mark.
5. Distinguish sleeve research from a holding: identify the sleeve tag and state that V2 does not manage holdings, per the R-D1 owner gap.
6. Read a Track Record row without inferring execution: no independent reader may infer a trade, fill, position, or plan from a Watch click.
7. Read one complete record and state its population, ruler, and correction basis without pooling it into one win rate.

Each task uses real difficult states, EN and ZH, dark and light, and 1440/390. Thresholds belong to the registered usability protocol, not this packet.

## 11. EVIDENCE

Commands and outputs are recorded at final-head audit time:

1. `python3 scripts/worktree_sparse.py add mockups` → `worktree-sparse: materialized mockups`
2. `find mockups/refs/institutionalize/us_stocks -type f -maxdepth 1 -print | sort` → the six paths in §0.
3. `rg -n 'AVAILABILITY_STATES|ENTRY_OPEN|APPROACHING_ENTRY|NOT_READY|WAIT_PULLBACK|RAN_DONT_CHASE|INVALIDATED|UNAVAILABLE_DATA' engine/prophet_entry_availability.py` → lines 35–43 and implementation lines 356–440.
4. `git grep -n availability_state -- templates | wc -l` → `0`.
5. Token receipts (definition lines; the trailing colon anchors the definition — an unanchored grep counts every use of the token): `grep -n -- '--bg:' templates/theme.css` → `63,210`; `'--panel:'` → `63,210`; `'--panel2:'` → `63,210`; `'--text:'` → `63,210`; `'--muted:'` → `64,211`; `'--line:'` → `69,218`; `'--card-shadow:'` → `120,236`; `'--ink-ok:'` → `373,501,502`; `'--ink-warn:'` → `372`.
6. Ban audit: `grep -nE 'Promoted|晋级|[Cc]ontrol-only|CONTROL_ONLY|arrive after|[Dd]rawer|pulse|stage|阶段|\bvalidated\b' research/prophet_v4/r6_program/wave1/B20_DESIGN_PACKET_V1_2026-09-23.md` → 7 hits: 97, 99, 100, 101, 296, 402 plus this receipt line itself (384). Lines 97–101 are the §3 ban-list rows, each citing the ruling record path; 296 is the R-E citation line; the last is the §12 changelog row for M4. The word boundary on `validated` is deliberate: the unbounded pattern also matched the `INVALIDATED` / "Invalidated" availability label at 201 and 248, which is the R-A state vocabulary the ruling requires, not a banned term.
7. Matrix cell audit: counting the complete cell phrase (the word SPECIFIED, a middle dot, then the four words "capture owed at B16") with `grep -o … | wc -l` → `40`, i.e. 5 surface rows × 8 cells; this receipt deliberately does not spell the phrase so the audit line cannot count itself.
8. Onboarding audit: `grep -n -F 'Nothing to act on today' …` and `grep -n -F '今日无可行动项' …` → line 312 in §8.1.
9. Pull-safety audit: `grep -n -i -E 'pull.*resurrect|resurrect.*pull' …` → line 357 in §9.
10. Glance budget audit: every EN composition glance and §8.1 EN empty-state sentence has ≤14 words (tickers, numbers, markup placeholders, and terminal punctuation excluded); no row exceeds the ceiling.
11. No test file ships with this packet: a lane-added `tests/test_b20_design_packet_v2.py` was removed by the seat at final audit (not commissioned; a research record needs no suite, and an unwired suite would fail contract-delta).
12. Commit chronology: the empty §12 heading was appended in a partial commit before the `STATUS: V2 IN PROGRESS` skeleton commit; the successful-commit chain is otherwise as ordered.

## 12. CHANGELOG (critique ID → repair)

| ID | Disposition |
|---|---|
| B1 | §1/§3 rebind every read to `availability_state`; default is No read yet. |
| B2 | §5/§6/§7 provide five surfaces, seven degraded states, and 40 specified cells. |
| B3 | §9 replaces disabled telemetry with exact “Not saved yet / 暂未保存.” |
| M1 | §3 applies the frozen seven-state table and green-only `ENTRY_OPEN`. |
| M2 | §3/§4 separate stance from direction and define the Prophet row anatomy. |
| M3 | §4 counts ten NEW components and names each DS-PR-0 dependency. |
| M4 | §2 removes drawers and specifies inline expansion plus `/prophet/<T>`. `research/prophet_v4/r6_program/rulings/R6-B20-01_DIRECTION_2026-09-23.md` R-B. |
| M5 | §2 fixes four destinations, separate Track Record, and operator measurement. |
| M6 | §7 uses the shared authenticated navigation line in every composition. |
| M7 | §8.1 replaces the permission toggle with the read-only Research-only chip. |
| M8 | §9 adds held-position onboarding and the R-D1 owner-gap residual. |
| M9 | §8 freezes static bake and removes all live interactions. |
| M10 | §9 adds pending, failed, unwatched, list-scoped tombstone, and local-only. |
| M11 | §3 bans machine vocabulary and §8.1 gives exact EN/ZH replacements. |
| M12 | §4 adds TierLock, preview state, and incumbent rollout controls. |
| M13 | §0 lists the real reference crops and §11 records command outputs. |
| M14 | §0 cites MP-1 and ERC §2/§10 as binding base. |
| m1 | §8.1 trims every glance and empty-state sentence to the word budget. |
| m2 | §2 removes Health from users and gives Themes a discovery stance. |
| m3 | §8 assigns list, expanded-row, and tab-row arrow ownership. |
| m4 | §11 records real commands and outputs; §7 no longer treats the specimen as the product base. |

All 21 findings are closed: 20 repaired and M8 partially repaired with **RESIDUAL R-D1** carried by the ruling’s no-held-position-surface clause.
