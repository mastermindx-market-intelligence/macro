# Portfolio AI Truth-Boundary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every Portfolio-aware Macro and Mastermind AI read distinguish an unavailable private store from a genuinely empty account, while preserving truthful totals and overlays for large or position-only books.

**Architecture:** Keep the existing Supabase tables, `_sb_get` client, Portfolio population rules, composer, and API/Brain consumers. Use `None` as the existing failed-query sentinel and `[]` as a successful empty result. Fail closed before composition or change-digest creation, and enrich only the bounded display rows while counting every valid canonical row.

**Tech Stack:** Python 3, FastAPI, pytest, pandas/Parquet fixtures, existing `engine.neuralweb.brain_gateway` and `app.main` paths.

**Spec:** `agentos/workstreams/WS-MARKET-OS.md`; current Chairman continuation; protected Skillpack `Mastermind@6f321cb42166e4224e5107ac3312a6f7cd01fffa`.

## Global Constraints

- Do not create another Portfolio, Watchlist, identity, state, cache, retry, or brief store.
- Portfolio positions remain ownership truth; Watchlists remain attention sets.
- `None` means the private-store query did not answer; `[]` means it answered with no rows.
- A failed private read must not produce an empty-book CTA, a zero count, a state digest, or a cached brief.
- Keep detail payloads bounded to 30 rows, but report totals from every valid canonical row.
- Model output remains display-tier and cannot originate scores, rank, size, gates, or trades.
- Do not absorb A2-A6, redesign UI, change schemas, or modify persistence semantics.

## Review Focus

- A successful zero-position account must still fall through to Watchlists and render normally.
- A failed child `watchlist_symbols` read must not look like an empty Watchlist.
- More than 30 positions must report the full valid total while returning only 30 detail rows.
- Position-only names must receive the same named board-state and weekly-stage overlays as Watchlist names.
- Missing board/stage artifacts must degrade to null overlays without making the private store unavailable.

---
### Task 1: Fail closed before composing personalized Portfolio state

**Files:**
- Modify: `tests/test_portfolio_changes.py`
- Modify: `app/main.py:1893-2025`
- Modify: `engine/neuralweb/brain_gateway.py:2742-2835`

**Interfaces:**
- Consumes: `_portfolio_load_holdings(uid) -> tuple[list[dict], str]`, where `population == "unspecified"` is the existing failed-read state.
- Produces: API HTTP 503 detail `{"error": "portfolio_store_unavailable"}` and Brain result `{"available": false, "error": "portfolio_store_unavailable", ...}`.

- [x] **Step 1: Write failing endpoint and Brain regressions**

```python
def test_portfolio_endpoints_fail_closed_when_private_store_is_unavailable(monkeypatch, tmp_path):
    m, client = _client(monkeypatch, tmp_path, ctx=_ctx(), holdings=[], population="unspecified")
    for method, path, kwargs in ((client.get, "/api/portfolio/brief", {}),
                                 (client.post, "/api/portfolio/changes", {"json": {}})):
        response = method(path, headers={"Authorization": "Bearer x"}, **kwargs)
        assert response.status_code == 503
        assert response.json()["detail"]["error"] == "portfolio_store_unavailable"
    assert not m._PORTFOLIO_CACHE


def test_brain_portfolio_brief_fails_closed_when_private_store_is_unavailable(monkeypatch, tmp_path):
    # Patch `_sb_get` so the canonical positions query returns None.
    result = gw._tool_get_portfolio_brief({}, repo, user_id="u1")
    assert result["available"] is False
    assert result["error"] == "portfolio_store_unavailable"
```

- [x] **Step 2: Run the new tests and verify RED**

Run: `python3 -m pytest tests/test_portfolio_changes.py -k 'private_store_is_unavailable or brain_portfolio_brief_fails_closed' -q -p no:cacheprovider`
Expected: FAIL because the endpoints return 200 and the Brain tool composes an empty brief.
- [x] **Step 3: Implement the smallest fail-closed boundary**

```python
holdings, population = _portfolio_load_holdings(uid)
if population == "unspecified":
    raise HTTPException(503, detail={"error": "portfolio_store_unavailable"})
```

Apply that check before the brief cache lookup and before `snapshot_state`. In `_tool_get_portfolio_brief`, return the same typed unavailable result immediately after the private reads and before loading/composing `portfolio_ctx.json`.

- [x] **Step 4: Verify GREEN and legitimate-empty controls**

Run: `python3 -m pytest tests/test_portfolio_changes.py -k 'private_store_is_unavailable or brain_gateway_loader_also_refuses_to_guess or genuinely_empty_positions' -q -p no:cacheprovider`
Expected: PASS; genuine `[]` still reaches `watchlist_union`, while `None` refuses.

### Task 2: Make `get_watchlist` totals and overlays truthful

**Files:**
- Modify: `tests/test_brain_gateway.py:3630-3710`
- Modify: `engine/neuralweb/brain_gateway.py:2640-2740`

**Interfaces:**
- Consumes: `_sb_get(path) -> list | None`, `us_standouts.json`, optional `equitydesk_overview.parquet`.
- Produces: existing `get_watchlist` shape plus truthful `counts`, per-position overlays, and explicit Watchlist/position truncation booleans.

- [x] **Step 1: Write failing query-boundary regressions**

```python
@pytest.mark.parametrize("failed_prefix", ["watchlist_symbols?", "portfolio_positions?"])
def test_get_watchlist_child_store_failure_is_unavailable(tmp_path, failed_prefix):
    result = gw._tool_get_watchlist({}, tmp_path, user_id="u1")
    assert result["available"] is False
    assert result["error"] == "portfolio_store_unavailable"
    assert "counts" not in result
```

- [x] **Step 2: Write failing large-book and position-overlay regressions**

```python
def test_get_watchlist_reports_full_position_total_but_bounds_details(tmp_path):
    assert result["counts"]["n_open_positions"] == 35
    assert len(result["positions"]) == 30
    assert result["truncated"]["positions"] is True


def test_position_only_name_gets_board_and_stage_overlays(tmp_path):
    assert result["positions"][0]["board_state"] == "on the buy board"
    assert result["positions"][0]["stage"] == "advancing"
```
- [x] **Step 3: Run the four new tests and verify RED**

Run: `python3 -m pytest tests/test_brain_gateway.py -k 'child_store_failure or full_position_total or position_only_name' -q -p no:cacheprovider`
Expected: child failures return successful zeroes, totals stop at 30, and position-only overlays are null/missing.

- [x] **Step 4: Implement minimal truthful parsing**

```python
def _portfolio_store_unavailable(note: str) -> dict:
    return {"available": False, "error": "portfolio_store_unavailable", "note": note}

if rows is None:
    return _portfolio_store_unavailable("watchlist symbol store unreachable")
if pos_rows is None:
    return _portfolio_store_unavailable("portfolio position store unreachable")

valid_positions = [r for r in pos_rows if isinstance(r, dict) and r.get("ticker")]
position_details = valid_positions[:30]
overlay_symbols = list(dict.fromkeys(
    [_safe_symbol(s) for s in symbols[:30] if s]
    + [_safe_symbol(r.get("ticker")) for r in position_details if r.get("ticker")]
))
```

Build `stage_by_sym` for `overlay_symbols`. Add `board_state` and `stage` to each returned position detail. Keep `n_open_positions=len(valid_positions)`, and return both truncation booleans without changing canonical state.

- [x] **Step 5: Verify GREEN and existing tool contracts**

Run: `python3 -m pytest tests/test_brain_gateway.py -k 'get_watchlist or dispatch_threads_user_id' -q -p no:cacheprovider`
Expected: all selected tests pass and no composite/risk score appears.

### Task 3: Integration, review, release, and production readback

**Files:**
- Modify: `docs/superpowers/plans/2026-09-21-portfolio-ai-truth-boundary.md` only for checked steps if useful.
- No Agent OS record unless a durable non-obvious discovery or unfinished handoff remains.

- [x] **Step 1: Run the complete affected suites**

Run: `python3 -m pytest tests/test_brain_gateway.py tests/test_portfolio_changes.py -q -p no:cacheprovider`
Expected: zero failures; record exact counts and warnings.

- [x] **Step 2: Run repository guards**

Run: `python3 -m py_compile app/main.py engine/neuralweb/brain_gateway.py`
Run: `git diff --check`
Run: `python3 scripts/agentos.py validate`
Expected: all exit 0.
- [x] **Step 3: Reconcile current source and open-PR overlap**

Re-fetch `origin/main`; compare its movement against the four owned files and confirm open work remains exact-hunk disjoint. Do not merge main into this branch merely for ancestry.

Audit evidence on 2026-09-21:
- `origin/main=2b62f49603e731daf68877516d3f6f748497b160`; its 74-commit movement from the pickup base touches none of the four owned code/test files.
- Open-PR file census found only Macro PR #6872 touching `app/main.py`; its hunk is at the router registrations near line 2284, disjoint from the Portfolio endpoints near lines 1893-2025.
- Other private readers were checked: recurring briefs and Entry Radar already publish `unavailable` on transport failure; `templates/watchstore.js` preserves cloud authority and returns `null`/degraded/error rather than a false empty account.
- The Terminal proxy relays upstream status verbatim and caches only 200 responses; `stateForResponse` maps every 503 to the explicit unavailable panel, so `portfolio_store_unavailable` cannot clear or masquerade as an empty book.
- A new RED/GREEN regression seals malformed 200 JSON: `_sb_get` now rejects non-list PostgREST payloads as unavailable rather than iterating an object into a false zero result.

- [ ] **Step 4: Commit, push, and open one bounded PR**

```bash
git add app/main.py engine/neuralweb/brain_gateway.py \
  tests/test_brain_gateway.py tests/test_portfolio_changes.py \
  docs/superpowers/plans/2026-09-21-portfolio-ai-truth-boundary.md
git commit -m "fix(portfolio): fail closed on unavailable private state"
git push -u origin claude/portfolio-ai-truth-boundary-20260921
```

Open one PR describing RED/GREEN evidence, exact collision census, API restart impact, and the distinction between unavailable and empty state.

- [ ] **Step 5: Independent review and concluded CI**

Review the immutable head against `WS:MARKET-OS`, repair any blocker test-first, then wait for every binding check to conclude. Arm `merge-on-green` only when no hold exists; stay through merge.

- [ ] **Step 6: Production verification**

Verify the deployed API process includes the merge, unauthenticated privacy boundaries still hold, normal authenticated Portfolio/Brain reads remain healthy where an existing session is lawfully available, and no endpoint caches or publishes an unavailable-store result. A production store outage must not be induced solely for proof.

- [ ] **Step 7: Closeout**

Record exact merge/deploy/readback evidence and classify the outcome truthfully. Do not call CI, merge, or process restart alone production acceptance.
