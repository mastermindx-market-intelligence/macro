# Independent review — `mmx-press-research-pool-review-20261014-001`

**Verdict: PASS** (with two non‑blocking observations).

## What I checked

Read only the supplied current `_plan_research` and the diff (no filesystem reads, no provider calls, no edits). Compared against the six requested checks plus the surrounding invariants the comment block above the function advertises (rank/audit‑trail fields, W1 fallback, cap, dynamic `blocked_refs` mutation).

## Diff scope and intent

The patch is a 4‑line addition (`candidates = [...]`) that runs *after* `engine_stat_facts(...)` and the `cap <= 0` early return, and swaps `eligible[: candidate_pool]` for `candidates[: candidate_pool]`. The inline `if ref in blocked_refs: continue` and the trailing `blocked_refs.add(ref)` are left in place. Inline ref check + `add` continue to mutate `blocked_refs`, so any pre‑merged `extra_blocked_refs` and any `blocked_refs` that arrived via ledger/staging reads are still consumed by both passes.

That is the right surgical shape: it does the "coverage refusal before the work budget" exactly where the comment in the existing triager (`A report the triage did not rank must fall to the BACK of the queue, never off it.`) and the existing `if ref in blocked_refs: continue` imply, and it leaves the dynamic mid‑iteration veto (banned vocabulary, cap break) untouched.

## Acceptance checks

1. **Priority / order** — `[it for it in eligible if ...]` walks `eligible` in order, so the W2R ranked+tail sequence produced just above by `_triage_order` (`ranked + tail`) is preserved; rerank is not performed. ✓
2. **Cap** — `cap = _triage_cap(...)` is unchanged, computed on the same `desk_cfg`. The `if cap <= 0` early return sits *above* the new filter, so a dark tier still returns `[]` before any allocation. ✓
3. **Freshness / window** — the `pub > as_of or pub < lo` and `summary_points` checks run in the `eligible` build loop *above* the new filter; nothing downstream of those checks moved. ✓
4. **Rights / lexicon** — `rights` gate is upstream of `_plan_research`; `_press_safe` filtering inside the loop is unchanged. ✓
5. **Dedupe** — two eligible items that share an id would still both pass the pre‑filter (ref starts out not in `blocked_refs`), but the first successful iteration does `blocked_refs.add(ref)` and the second hits the inline `continue`. Net dedupe behaviour matches the prior code. ✓
6. **Rank metadata preservation** — `triage_meta` is built once by `_triage_order` upstream of the new filter; the slot still looks up its row via `triage_meta.get(str(it.get('id') or ''))` and writes the same `rank / w_score / w_score_pre_veto / veto / scoring_version / score_source / datasketch_present / ordered` block, including `ordered: bool(order)`. Tier/cap/series shape unchanged. ✓
7. **Fixture discrimination** — the new test constructs ten items `_item(f"pool-{i:02d}")`, holds the first 8 (`ids[:pool]`), and asserts the produced slot's single source is `research_vault:{ids[pool]}`. This is genuinely the ninth item: pre‑fix the loop is over the 8 held reports and exits with `[]`, so the test would fail; post‑fix `candidates` drops the 8 and walks the tail into the `[0:8]` slice. The 3×2 parametrization (`blocked_by × ranked`) hits three distinct blocked‑ref ingress paths (ledger `sources`, staging JSON `sources`, `extra_blocked_refs`) which is exactly the three pre‑decisions the `extra_blocked_refs` arg is meant to substitute in. ✓
8. **Duplicate ids** — the fix does not make identical ids any safer or any less safe than the prior inline check + `.add` already was. No new failure mode. ✓

## Non‑blocking observations (not blockers for this intake)

- **O‑1.** `test_research_pool_stays_bounded_after_coverage_filter` is labelled a "negative control" and is good guardrail against an over‑eager widening of the inspection budget, but it produces `slots == []` *both* before and after the fix (8 banned‑vocab items 1..8 already exhaust the pool in the old code because the inline check skip leaves nothing inspected). It documents the bound; it does not discriminate the regression. Fine to keep; just don't lean on it as the regression evidence — the parametrised six are.
- **O‑2.** The `before / after` equality assertion in the parametrised test snapshots files already present under `root/data/press/` (and the catalog at the test's `path`) before `P.plan(...)`. New files that `P.plan` might create under `data/press/` won't be enumerated; only existing files are re‑read. `_plan_research` returns slots — the writer is downstream — so the assertion's coverage is consistent with the no‑write claim, but if a future change ever moves a writer upstream of `P.plan(...)` this test will not catch a *new* file. Today, not a bug.

## Out‑of‑scope items I deliberately did not re‑examine

The deferred issuer‑context review and any other prototype outside `desk_planner.py`'s triager were not opened; the brief explicitly excludes replacement of that work and limits scope to this one bounded intake.

## Result

`engine/press/desk_planner.py` `@c7db0a00641f..60d421acd8db` and `tests/test_press_research_triage.py` `@b1b34ad0eef4..0f2d2267190b` match the SHA256s the author declared and are consistent with the diff and the described validation. Returning to root/parent with **PASS**.
