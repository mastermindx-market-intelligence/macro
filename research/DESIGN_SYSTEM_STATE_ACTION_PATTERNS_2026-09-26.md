# State and action patterns — R5 working design contract

Scope: the existing State Panel, Freshness, Callout, Button, Detail Disclosure and LENS families. This is implementation guidance and illustrative copy for the existing system, not another state machine, component registry, token root, ranking model or approval gate. All numbers below are synthetic examples. No generated trade instruction or live connectivity claim is permitted.

**Native state: NOT_APPLIED_TO_PAPER.** This is a candidate supporting contract under #7394; existing source law and release gates remain authoritative.

## A prepared answer includes a prepared recovery

Show the state in ordinary language, its material consequence and the useful continuation. Omit boilerplate that adds no decision value. Do not require a subtitle on every state. Keep warnings beside the claim they qualify. The page remains usable when an independent input fails: disable only the action or conclusion that genuinely depends on it.

Choose the display from the existing producer/result owner. Never deduce successful completion from elapsed time, a transport acknowledgement, HTTP acceptance or optimistic UI. Never infer an empty population from missing data. Freshness follows the source's existing clock and policy, not an arbitrary new UI timeout.

## Data-state examples and exact action meaning

| Existing state | English first read | Chinese first read | Useful action | Required source truth |
|---|---|---|---|---|
| Loading | Checking the latest data… | 正在获取最新数据… | Keep independent browsing available | No result yet; geometry is a placeholder, not zero or a measured percentage |
| Stale | Latest update delayed | 最新数据更新延迟 | View last confirmed / 查看上次确认的数据 | Show its observation date; do not silently refresh the date or pass the old value off as current |
| Error | Latest update unavailable | 暂时无法获取最新数据 | Try again / 重试 | Data read failed; offer earlier evidence only when that evidence actually exists |
| True empty | No setups qualify | 暂无符合条件的机会 | View all 24 / 查看全部24项 | All 24 in the declared current population were examined; zero qualifying is a real result |
| Filtered empty | No matches for 3 filters | 没有符合这3项筛选条件的结果 | Clear 3 filters / 清除这3项筛选 | 12 items exist without these filters; clear only the relevant filters, not market, saved scope or unrelated preferences |
| Partial | 6 of 9 above average | 已有数据的9项中，6项高于均线 | See coverage / 查看数据覆盖 | 12 expected, 9 usable, 3 unavailable; rate is 6/9, not 6/12 and not complete market breadth |
| Conflicting checks | Entry checks disagree | 入场判断不一致 | Compare the checks / 对比两项判断 | Preserve both check names, states, scopes and clocks; do not average them or invent a combined entry call |
| Denied/locked | This research detail requires access | 此项研究详情需要相应权限 | View access / 查看所需权限 | Identify the actual locked object; public answer and public evidence remain public |

The counts belong to separate component examples, not one common population. For production, interpolate only the owner-supplied scope/counts. A denied field is not null evidence; a provisional interpretation is not denied access. Corrected data must retain an inspectable prior record and correction context under the existing evidence owner.

## One save, five observable outcomes

This pattern is shown with a saved research view, not a trade order. The same distinction applies to watches and alerts, but their successful state must come from their existing activation owner.

| Display | EN / ZH action | What happens in the real implementation |
|---|---|---|
| Ready | Save view / 保存当前视图 | Submit the exact current view to its existing save owner |
| In progress | Saving… / 正在保存… | Keep the control readable but unavailable for duplicate submission; preserve the current view and focus; expose progress nonvisually |
| Confirmed | Open saved view / 打开已保存的视图 | Render only after the canonical result confirms the exact object; navigate to that saved object |
| Failed | Try saving again / 重试保存 | Only when the owner confirms no successful effect; retain the view and reuse the incumbent safe retry/idempotency path |
| Not confirmed | Check save status / 查询保存状态 | Query the original operation/result; do not submit another save or create a replacement operation |

For an uncertain result, the system should first reconcile automatically through its existing read/status capability, rather than asking the user to search for a duplicate or infer what happened. The displayed Check save status action is a bounded read-only recovery. When status remains unavailable, state that honestly, preserve the current view, and offer the safe existing return path. Do not spin indefinitely or introduce a new watcher/retry engine in the frontend.

Keep confirmation visually modest. Green must not imply a bullish market judgment; explicit Saved/Not saved wording carries the result. The sample's blue primary action identifies the next action, not statistical confidence or entitlement. Violet remains reserved for the existing lock role.

## Inspect and return without losing the task

See coverage opens the missing/usable-member explanation for the exact inspected snapshot. Compare the checks shows both reads together, not two separate pages the user must reconcile. View last confirmed opens a visibly dated record. These are inspector or existing LENS/Detail Disclosure uses, not new navigation families.

On narrow screens, use the existing sheet/detail route rather than compressing a desktop two-column inspector. Keep the subject, benchmark/period and consequence visible before detail. Dismissal restores the initiating item/control and applicable filters, selection and scroll position. A new live update can advertise new data but must not silently replace the inspected snapshot.

Do not turn every evidence read into a modal. An ordinary inline disclosure is preferable for a short method explanation; long comparative work needs the established research route. A state panel should not contain a nested stack of dialogs.

## Accessibility and implementation boundary

Use native buttons for actions and links for navigation. Keyboard activation, available/disabled states and visible focus belong to the real implementation. A Paper div is neither a functioning button nor evidence of keyboard support. Keep ordinary pending/success/status updates available to assistive technology without stealing focus; urgent errors may require a stronger announcement, but routine updates must not become interruptive alerts. A modal must manage its own focus and restore it to the logical initiator when it closes.

The external references informing those interaction details are W3C's current Button Pattern, Dialog (Modal) Pattern and Understanding SC 4.1.3 Status Messages. No human comprehension, assistive-technology or production pass is implied by following a written pattern.

Comfortable 44px controls are the existing product target. The draft uses shared radii, spacing and type tokens. Normal text and its actual painted background are measured separately from borders/focus indicators, disabled states and overall usability. Pending must remain readable, even when resubmission is unavailable.

## Design-to-source mapping

- Missing/empty: existing `.mx-empty` / `.mx-empty-why`, not a new page-local status engine.
- Staleness: existing `.dtp` observation/session contract.
- Partial/conflicting/corrected context: existing `.mx-callout` and evidence owner.
- Actions: existing `.gbtn` family; any solid treatment is a source-owned extension, not a new component name. `--fill-info` already exists in theme.css; its dark/light Paper aliases project that role only.
- Inspection: existing LENS, `.mx-disc` and established mobile sheet/research routes.
- Storage, monitoring and result reconciliation: incumbent product owners; no fixture handler is production persistence.

Native target: file `01M2WGNCX9475G79JRKJTCM08P`, existing system page `p-1-0`, desktop boards `1BB-0` and `1BC-0`. Prepared additions extend the existing degraded-state section while preserving the data/chart examples and access section. Each example is explicitly illustrative. No specialist board, source palette or R4 warning-label/button/template result is to be overwritten.

## Discriminating acceptance cases

A complete-source zero must not render for a failed feed. Filter removal must restore the known items without resetting unrelated context. Partial coverage must preserve both the usable and expected populations. Conflicting checks must retain both states and their scopes. Stale data must retain its old observation date. Failed save may retry only after the original effect is known; unknown save exposes status lookup, never another submission. Successful save must open the exact saved view. Inspection/dismissal must restore the task in keyboard and touch flows. Lock styling must not hide public evidence.

Native schema/content/color checks, rendered author review, implemented keyboard/state behavior, independent review and cold-user comprehension are five different observations. Record each honestly. Native/mobile/locale proof remains unperformed until the actual corresponding result is captured and inspected.


## R7 executable projection

The existing specimen's State/Loading/Error panel now contains these eight data
states and five save outcomes at `#specimen-state-actions`, with EN/ZH twins.
The gallery is for reviewing independent fictional examples, not a proposed
customer screen that shows thirteen states simultaneously. Real disclosures let
reviewers inspect coverage, filters, dated/public evidence and conflicting reads
without leaving their place. They compose existing `.mx-disc` and `.gbtn` families;
no new state or persistence engine is introduced.

All save/retry/clear/access controls are explicitly unconnected and disabled in
this fixture. Inspecting a sample does not verify any save or alert backend.
Actual production Clear filters / View population / Check save status must bind
the corresponding existing owner and scope; the fixture does not substitute for
that integration. Unknown results never become retries merely because time passed.

Native status remains NOT_APPLIED_TO_PAPER. The shared-file hold has not been
resolved by this source work. See R7 in the existing readability record for exact
browser/source checks, retained screenshots and proof limits.
