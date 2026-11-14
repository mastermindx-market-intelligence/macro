# Shared Search and Watchlists: narrow recovery states

## Delivered scope

Four editable root boards add two demonstrated state gaps in English and Chinese. Each board contains a customer screen and a separate builder note. The user sees one state, one useful primary action and an easy return; implementation details remain outside the product screen.

| File and page | Root board | Customer screen | Purpose |
|---|---|---|---|
| [Search p-4-0](https://app.paper.design/file/01M6Y31C449F02KGRNPGK94Q8D/p-4-0) | 1H3-0 | 1G2-0 | Company results unavailable, EN320 |
| Search p-4-0 | 1IO-0 | 1IW-0 | Company results unavailable, ZH320 |
| [Watchlists p-4-0](https://app.paper.design/file/01M6Y309YH7PJZMF23R7EDH3CM/p-4-0) | 2TX-0 | 2SV-0 | No available owned watchlists, EN390 |
| Watchlists p-4-0 | 2VV-0 | 2WV-0 | No available owned watchlists, ZH320 |

These are native design and implementation-reference additions. Current Terminal source already distinguishes the underlying branches; this amendment does not claim to have changed or tested that application.

## Search: unavailable Companies, usable Tools

### Show this state when

Companies has no qualified usable result and the independent Tools catalog remains available. A request failure with qualified cached Companies rows belongs to the retained R42 cache/availability state, 18L-0, rather than this empty-result-area specimen. Successful zero matches, loading, restricted access and an unavailable Tools catalog remain distinct states.

The interface retains the entered query, scope tabs and market context. It replaces the company result area with:

> Company results unavailable

The supporting line says the query is kept and Tools remain available. Retry company search is the primary action. Search tools switches to the existing Tools scope. No Open Analysis action appears without a qualified selected company.

Chinese copy follows the same meaning: 公司结果暂不可用; 查询已保留，工具搜索仍可使用。 The two actions are 重试公司搜索 and 搜索工具.

### Existing state and request owners

At Terminal master `1c0bf028cf72539a4d3fcb17fa137ee474d764f9`, [SharedSearchWorkspace.tsx](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/1c0bf028cf72539a4d3fcb17fa137ee474d764f9/terminal/components/SharedSearchWorkspace.tsx) has one shared `query` prop. Its `selectScope` changes scope and focuses the input. Tools filtering uses the same query. Companies and Tools have independent service status, catalog/result and selected-result state.

Switching scope therefore preserves the current shared query. Do not claim separate per-scope query drafts or introduce a second query persistence owner. Existing ShellSearch history return can restore its tool-origin query and selection; that is a separate, already owned return operation.

Retry uses the current matching request owner and inflight recovery. An earlier response may not overwrite a later query or subject. Closing restores the current invoker; a missing invoker uses the existing shell fallback. Preserve R42 keyboard/focus and return behavior in p-2-0 / 14V-0.

### Discriminating implementation proof

1. Companies unavailable and Tools ready: the new state appears; query remains unchanged through Search tools.
2. Companies failure with usable cached rows: retain R42 cached-result behavior, not the new no-usable-result specimen.
3. A later query succeeds while an earlier retry resolves: only the current matching result is shown.
4. Switching tabs, Escape, close and returning from a tool preserve the existing focus/history contract.
5. Both 320px locales keep the full state and both actions readable without horizontal overflow.

## Watchlists: qualified empty owned inventory

### Show this state when

The active subject's owned-list read succeeds and returns no eligible writable lists. The UI says “No available watchlists,” keeps the NVDA subject context and offers Open Monitor and Keep reading. It has no list chooser and no Save button.

This branch means no owned lists are available for this save. It does not establish that every database row is absent: upstream list normalization can exclude invalid identifiers or names. Shared-with-me lists are not owned writable destinations.

A failed or malformed read, unavailable permission, unknown subject or unresolved account change must use its existing unavailable/restricted/loading recovery. None may be rendered as an empty owned inventory.

Chinese copy uses 暂无可用列表 and 当前没有可用于保存的自有关注列表。 The actions are 打开监控 and 继续阅读.

### Existing save and destination owners

At the same Terminal pin, [CompanyWatchSave.tsx](https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/1c0bf028cf72539a4d3fcb17fa137ee474d764f9/terminal/components/fin/CompanyWatchSave.tsx) already renders the empty-inventory branch without chooser/Save. It retains the established `beginWatchSave`, `applyWatchSaveResponse`, `reconcileWatchSave`, browser storage, watchlist owner and subject/generation fences.

Open Monitor uses the existing generic `/monitor` destination from shared navigation. The design does not promise an exact list destination, a newly created list, an automatically selected symbol or an automatic save. Keep reading and close return to the current company/invoker context.

Any retained unknown or storage-blocked save recovery remains visible independently of the inventory branch. This native specimen depicts the empty-inventory branch without a separate active recovery, but it must not suppress one when present. The current source renders operation/storage recovery below inventory. Retain p-2-0 / 2RP-0, especially its 2RV-0 contract and 2S3-0 / 2S6-0 details, for that combined case.

A return from Monitor may refresh inventory only through the existing owner. It must not replay a save. Reuse current return behavior where implemented and prove it at the consumer; do not add a return store, identity owner or retry queue.

### Discriminating implementation proof

1. Valid empty owned-list response: no chooser or Save, correct company context, generic Monitor action.
2. Shared-with-me only: no shared list becomes a writable owned destination.
3. Malformed/failed/restricted read: existing recovery, never empty success.
4. Retained unknown save plus empty inventory: recovery remains available; navigating or checking storage issues no mutation.
5. Subject or generation changes while inventory resolves: stale results do not bind to the new account.
6. Close, Keep reading and Monitor/back preserve existing context. A list created elsewhere is only available after an owned inventory read; it is never assumed or auto-saved.
7. EN390 and ZH320 retain readable labels and visible actions.

## Source and retention

Root-inspected exact source excerpts, including blob identifiers, are in [terminal.source_excerpt.json](evidence/terminal.source_excerpt.json). They are source evidence, not runtime endpoint receipts.

Search retains all 20 existing product/build boards: 19 on p-1-0 and 14V-0 on p-2-0. Watchlists retains all 27: 22 on p-1-0 and five on p-2-0. Both files retain the other writer's AGENT README as their first page. New p-4-0 pages follow the existing current contract page and precede the older reference page.

The prior fictional Comparison refinement was inspected at 8F-0, IR-0 and ON-0. It already distinguishes the bounded three-company study, filtering, fixed scale/baseline/evidence, apply/cancel and restoring all results. Those inspected designs were retained. No production consumer or runtime eligibility for that fictional study was established by this audit.

