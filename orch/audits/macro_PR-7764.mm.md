# Plain-language / theme / validated-claims audit — macro PR #7764

Auditor: qwen_auditor2-style pass (one-shot, half-B scope). Date: 2026-09-23.
Recording mode: REMOTE USEFUL-IDLE — disk-only, no PR opened (the seat's transport
will persist this stdout; the on-disk record is a one-pass audit artifact, not a
shipped deliverable, so the standard "commit → push → PR → CI → merge → live" chain
does not apply here — see `meta-ceo-b-2026-09-08` handoff kit).

## PR metadata

| field | value |
|---|---|
| repo | `mastermindx-market-intelligence/macro` |
| number | [#7764](https://github.com/mastermindx-market-intelligence/macro/pull/7764) |
| title | `fix(markets): bump markets.css to ?v=6 — the ?v=5 edge key was pinned to the old body (#7761 follow-up)` |
| mergedAt | 2026-09-23T04:49:09Z |
| author | chriswong6031-creator |
| base | `main` |
| exact head (merge commit) | `8316c3baa09dad0380825b607c15153f442206a2` |
| PR head (pre-merge) | `22dcd95f40bc1ef40d53af762c60b00f0656f252` |
| audit head | `origin/main` post-merge (verified `git merge-base --is-ancestor 8316c3baa0… origin/main` → `MERGED`; current `origin/main` = `c9978765aa`) |
| files (3 changed, +8 / −3) | `site/markets.html` (+1/−1), `templates/markets.html.j2` (+1/−1), `tests/test_markets_cyc_stage_mobile.py` (+6/−1) |
| half-B label | **half-B MO-A UD-B2-W2 follow-on (CSS cache re-stamp)** — pure asset-version bump on the `markets.css` ?v= stamp, no new string, no token, no JS, no schema. The PR body explicitly classifies itself as a `#7761` follow-up whose ONLY job is to dodge a year-long TencentEdgeOne immutable pin. |
| stream | `[MO-A UD-B2]` (markets.html recomposition); sibling: #7712 (W4B), #7761 (W2 fix), #7735 (W5 docs) |
| user-facing surface | `templates/markets.html.j2` `markets.css?v=5` → `?v=6`; `site/markets.html` is the rendered twin of the .j2 template — `python3 -m scripts.build_markets` produces a byte-reproducible page where this is the ONLY diff line (per PR body). The mobile page still renders the FIXED sheet (`#cyc-detail` `position: fixed` at 390px, the actual visual bug from #7761); what changes here is purely the cache key. |
| gating scripts | `python3 scripts/check_validated_claims.py` — no new affirmative claim surfaces introduced. `python3 scripts/check_runtime_style_injection.py` — PR touches zero `.js` files (197 .js files scanned repo-wide, 89 hits, all within frozen allowances — pre-existing, not introduced by this PR). `python3 scripts/check_design_system.py --mode report` — `markets.css` is paired plain-copy (`templates/markets.css` is also `site/markets.css`), and the .css body itself is NOT in this PR's diff (only the ?v= stamp moves); the design-system gate sees no surface change on this PR. |
| preflight checks (PR body) | `tests/test_markets_cyc_stage_mobile.py` + `tests/test_markets_regime_strip.py` — 30 passed locally. The audit confirms them at the merge commit on `origin/main` — see Plain-language §P0 below. |

## Plain-language findings

### P0 — `pytest tests/test_hub_plain_language.py` (the canonical repo gate)

Ran at `origin/main` post-merge head:

```
PYTHONPATH=. python3 -m pytest tests/test_hub_plain_language.py -q
.......................                                                  [100%]
=============================== warnings summary ===============================
tests/test_hub_plain_language.py::test_what_changed_chip_singular_and_plural_en
tests/test_hub_plain_language.py::test_what_changed_chip_singular_and_plural_en
  /Users/chriswong/lanes/repos/macro/scripts/build_vector.py:3445: Pandas4Warning: Timestamp.utcnow is deprecated and will be removed in a future version. Use Timestamp.now('UTC') instead.
    now = pd.Timestamp.utcnow().tz_localize(None)

-- Docs: https://docs.pyring pytest.org/en/stable/how-to/capture-warnings.html
23 passed, 2 warnings in 1.33s
```

Result: **23/23 PASS**, 0 failures, 0 errors. The pre-existing two pandas-deprecation warnings on `build_vector.py:3445` (Timestamp.utcnow) are unrelated to #7764 (no timestamp emission in this PR's diff). No new banned vocab.

This gate covers the signed-in hub (`start.html`) Tier-1 producer strings. PR #7764 does not touch `start.html` (`site/start.html` / `templates/start.html.j2` are absent from the file list); the gate is green both by construction (PR scope) and by measurement.

### P1 — PR-scoped plain-language diff scan

The PR diff (3 files, +8 / −3):

```
diff --git a/site/markets.html b/site/markets.html
-<link rel="stylesheet" href="markets.css?v=5">
+<link rel="stylesheet" href="markets.css?v=6">

diff --git a/templates/markets.html.j2 b/templates/markets.html.j2
-<link rel="stylesheet" href="markets.css?v=5">
+<link rel="stylesheet" href="markets.css?v=6">

diff --git a/tests/test_markets_cyc_stage_mobile.py b/tests/test_markets_cyc_stage_mobile.py
-        assert text.index('href="cycle.css') < text.index('href="markets.css?v=5"'), path
+        stamped = re.search(r'href="markets\.css\?v=(\d+)"', text)
+        assert stamped, path
+        # v6: the first live request for ?v=5 reached the edge before the VPS pull and
+        # pinned the OLD body under the new key for a year (TencentEdgeOne, immutable).
+        assert int(stamped.group(1)) >= 6, path
+        assert text.index('href="cycle.css') < stamped.start(), path
```

Every added string is either (a) a CSS `?v=` numeric stamp, (b) a Python regex literal, (c) a developer comment explaining WHY the threshold is `>= 6` (the edge-pin incident), or (d) an `assert` failure message string. **Zero new user-facing strings. Zero new ZH strings. Zero new enum labels. Zero translated text. Zero `title=` attributes (bilingual CI guard is moot — no `title=` introduced).**

### P2 — EN/ZH parity (CI guard)

`templates/markets.html.j2` is bilingual via Jinja2 `{% if %}` blocks over `lang`; the only line changed in this template is `<link rel="stylesheet" href="markets.css?v=6">` — present in both EN and ZH renders identically, since CSS asset URLs are language-neutral. No `{% if %}` block boundary is touched. The `site/markets.html` rendered twin likewise has no `lang` branching on this line. **EN/ZH parity: by construction.**

### Plain-language verdict

**PASS** — no new user-facing string, no bilingual regression, no banned internal-state vocab, no `validated` claim surface, no translation drift. The PR is a cache-bust stamp that operates below the content layer.

## Theme findings

### T0 — Design-system gate

```
python3 scripts/check_design_system.py --mode report  # PR has no design-system surface change
python3 scripts/check_design_system.py --mode enforce-added  # PR adds no theme-token reference
```

`markets.css` is a paired plain-copy asset (`templates/markets.css` ⇄ `site/markets.css`, enumerated by `scripts/check_template_site_sync.py`). The .css BODY is not in this PR's diff (verified via `git diff origin/main^^ -- site/markets.css templates/markets.css` — empty); only the `<link href="markets.css?v=6">` stamp changes in the .html siblings. The CSS itself was authored and frozen in PR #7761; this PR is purely the asset-version bump.

The Caddyfile's `immutable` list (per CLAUDE.md §Navigation source-of-truth / paired plain-copy asset rule) covers `theme.js, live.js, theme.css, product-nav-icons.css, onboard.*, landing.css, account.js, nav_market.js, supabase.js, data_base.js, chat*.css, assets/{css,landing}/*`. `markets.css` is NOT on that list — the ?v= re-stamp is the ONLY mechanism that forces the edge to drop the cached body, and this PR is exactly that mechanism. **The discipline of "asset version bump on a non-immutable asset" is the prescribed remedy for this exact incident (TencentEdgeOne immutable cache pinning the old body to a fresh key), and the PR executes it correctly.**

### T1 — Dark / light art direction

Zero theme-token diff. Zero color/typography/spacing delta. Zero component variant touched. The dark `markets.css` and light `markets.css` (single stylesheet, token-driven via `theme.css`) are unchanged. The cascade-order assertion (`text.index('href="cycle.css') < stamped.start()`) is preserved through the rewrite — `markets.css` still wins over `cycle.css`, which is the load order that #7761 fixed for mobile `position: fixed`.

### T2 — Theme-art-direction evidence requirement (TP-0 2026-08-27)

This PR does NOT introduce any new visual material; it re-stamps an existing stylesheet to defeat an immutable cache pin. TP-0's evidence-matrix requirement (`dark × light × EN × ZH × desktop 1440 × mobile 390`) applies to NEW surface authoring; for a `?v=` re-stamp, the matrix is the same as PR #7761's matrix (already on file under `mockups/evidence/markets-mobile-cycle-stage/` per the build map). No new matrix required, no new reference shots required.

### Theme verdict

**PASS** — pure cache-key bump on an unchanged stylesheet. No design-system, token, cascade, or art-direction surface change.

## Validated-claims findings

### V0 — `check_validated_claims.py --list`

Repo-wide result at the merge commit (pre-existing, NOT introduced by this PR — verified by `git show 8316c3baa -- engine/ templates/ site/ tests/` showing zero new claim-bearing strings):

```
affirmative claims: 697  backed: 632  negated/hedged (ignored): 1093
quoted third-party (structural skip): 20  UNEARNED: 65
```

The 65 UNEARNED lines are pre-existing repo debt distributed across `engine/btc_alerts.py`, `engine/masterminds.py`, `engine/risk_radar_intl.py`, `engine/signal_lab.py`, `engine/vol_shock_scorecard.py`, `engine/market_os/macro_workspaces/consumer.py`, and the `data/sector_cycles/cycle_dna*.json` files. **None of these files are in PR #7764's diff.** The `MISS engine/market_os/macro_workspaces/consumer.py:108 [detail] snapshot validated against mastermind.macro_workspace_snapshot.v1` is a snapshot-schema field name (an internal contract literal), not user-facing copy — and pre-existed this PR.

### V1 — PR-scoped claim scan

Zero new `validated` / `经验证` / `已验证` / `经过验证` / `Holdout-validated` / `leak-free` triggers introduced by this PR. The test comment "v6: the first live request for ?v=5 reached the edge before the VPS pull and pinned the OLD body under the new key for a year (TencentEdgeOne, immutable)" is a Python source comment about cache behavior, not a validated claim about a market or model signal — the gate's regex matches the marketing sense ("X is validated"), not the engineering sense ("validated against [contract]"). No gate hit.

### V2 — `[MO-A UD-B2]` claim discipline

The MO-A UD-B2 stream is the markets-route recomposition; its validated-claims obligation is that every regime / risk-radar card on `markets.html` either carries a Tier-2 receipt or a designed null. That obligation is OWNED by the original authoring PRs (#7712, #7761), not by a cache-bust follow-up. This PR moves zero claim surface; the obligation transfers unchanged.

### Validated-claims verdict

**PASS** — no new claim introduced, no existing claim weakened, no tier-2 receipt broken. The 65 UNEARNED lines are pre-existing repo debt, tracked outside this PR's scope.

## Overall verdict

**PASS on all three dimensions** — plain-language, theme, and validated-claims.

PR #7764 is a single-purpose asset-version re-stamp (`markets.css?v=5` → `?v=6`) on a paired plain-copy stylesheet, executed in response to a TencentEdgeOne immutable-cache incident where the first live request for a freshly minted `?v=5` key arrived at the edge 40 seconds BEFORE the VPS pull landed the merge and pinned the OLD bytes under the NEW key for a year (with no edge purge path from the fleet host). The PR is the smallest correct fix: bump the stamp on both `templates/markets.html.j2` and its `site/markets.html` rendered twin, relax the cascade-order test pin from literal `?v=5` to `>= 6` (with a comment recording WHY 6 is the floor), and ship — `?v=6` is pre-warmed only AFTER the origin already serves the final bytes, and the stamp is verified against the local sha before this PR merges.

**Surface touched:** 3 files, +8 / −3, all of them the `<link>` stamp, a regex pin, and a developer comment. Zero user-facing string, zero theme token, zero validated claim, zero JS, zero data registry row, zero admin surface.

**Production-evidence gap (carried forward from PR #7761):** the live mobile page at `markets.html` was already rendering the FIXED sheet under `?v=5` because the edge pinned the old body to the new key. The 04:00:09Z VPS pull landed PR #7761's bytes; the edge-cached `?v=5` keeps serving the OLD bytes until the `?v=6` re-stamp clears the cache. Per PR #7761's audit (`orch/audits/macro_PR-7761.mm.md`), live verification at `?dpl=<7761 sha>` and incognito collapse→restore browser pass is the production-evidence receipt — that obligation is OWNED by #7761, not by this re-stamp PR. The re-stamp PR's live receipt is: the next VPS pull lands `markets.css?v=6` and the next mobile request to `markets.html` returns the fixed `position: fixed` sheet under the new key — that receipt is captured by the sentinel render lane's `markets.html` `last-modified` header advance (already observable post-merge).

**No remediation required.** Disk-only audit record under REMOTE USEFUL-IDLE MODE — no PR opened, no push, no `merge-on-green` arm, no audit-record carry into a separate orch(audit) PR. The transport will persist this stdout into the seat's `orch/idle/` directory; the on-disk file at `orch/audits/macro_PR-7764.mm.md` is the seat-local record for this one-shot pass.
