# mastermind-terminal PR #711 — plain-language / theme / validated-claims audit (2026-09-22)

## PR metadata

| Field | Value |
|---|---|
| Repo | `mastermindx-market-intelligence/mastermind-terminal` |
| PR | [#711](https://github.com/mastermindx-market-intelligence/mastermind-terminal/pull/711) |
| Title | `fix(chart): keep indicator drawings stable under Y-axis scaling` |
| Merge commit | `136ff81b735def6c12be1f342dc79fb01d599b29` |
| PR head | `b3c9c4d525f1d098ee5a8ea4fedca3e60ee58c87` |
| Merged at | 2026-09-22T22:02:25Z |
| Size | 16 files, +280 / −96 (half-B) |
| Headline change | Translates between chart-root Y and pane-local Y for drawings bound to indicator panes; persists a `paneCoordSpace: pane-value-v2` marker; one-shot migrates drawings created since PR #481 into the corrected coordinate space; clips indicator-pane drawings to their owning pane SVG without disturbing price-pane tools that intentionally span the full chart (e.g. vertical lines). |
| Receipts | `terminal/docs/pr-crops/options-level-axis-labels/`, `terminal/docs/pr-crops/terminal-visual-intelligence/` (both re-minted against this exact head with content hashes) |

## plain-language findings

**Verdict: PASS (0 added findings, 0 blocking).**

Ran `node terminal/scripts/check_plain_language.mjs --json` against the PR head (with the `ChartPanel.tsx` changes shipped on `b3c9c4d5`) inside `/Users/chriswong/lanes/repos/mastermind-terminal/terminal`:

```json
{
  "version": 1, "mode": "enforce-added", "base": "origin/master", "baseResolved": true,
  "vocabulary": { "declaredTerms": 83, "overlaySource": "terminal/lib/plainLabels.ts",
                  "overlayPresent": true, "overlayTerms": 37 },
  "scannedFiles": 252, "findings": [],
  "legacy": [ 6 raw_slug_interpolation reports on pre-existing files, none on PR #711 surfaces ],
  "counts": { "blocking": 0, "legacyReported": 6, "waived": 0 },
  "nulls": []
}
```

What changed in plain-language-relevant surface area:

- `ChartPanel.tsx` — no new user-visible copy strings. The additions are pure coordinate math (`yOfIn`, `priceAtIn`, `paneLayoutFor`, `drawingMetaForPane`, `migrateLegacyPaneDrawings`, `applyDrawingPaneClip`), internal markers (`PANE_VALUE_SPACE = "pane-value-v2"`), and SVG `<clipPath>` plumbing. The 6 legacy raw-slug reports on `AlertTimeline`, `WatchingList`, `ForecastPage`, `ExposureMatrix`, `SectionAccount`, and `visualIntelligenceCopy` are pre-existing debt and **not** introduced or worsened by this PR.
- `terminal/e2e/drawing-system.spec.ts` — 3 new test names added: `"an indicator-pane drawing holds its place when the price scale rescales"`, `"an indicator-pane drawing stays in its pane when that pane y-axis rescales"`, `"legacy indicator-pane drawing coordinates migrate into pane value space"`. All are plain English, neutral, and descriptive.
- `terminal/lib/__tests__/visualIntelligenceEvidence.test.ts` — 1-line tweak updating the test summary string. Not user-facing.

No banned vocabulary introduced (no raw internal-study slugs, no machine tokens like `pane_value_v2` surfaced into copy).

## theme findings

**Verdict: N/A for material theme; receipts RE-MINTED, content-hash bound.**

The PR introduces zero changes to color, type, spacing, motion, or component geometry. It is a coordinate-system correctness fix on the existing drawing render path; the rendered output should be visually identical to the previous behavior **except** for the bug being fixed (drawings now stay inside their owning pane instead of escaping into neighbours).

Evidence-matrix review:

- `terminal/docs/pr-crops/terminal-visual-intelligence/`: 6 PNGs (desktop / tablet / mobile × EN / ZH) + `EVIDENCE.yml`. Re-minted against this PR head. SHA-256 hashes are content-bound (e.g. `desktop.png: c04d900c12307f05b30dc0203e7fdfe4ca618d1610fd11b5be94152832b6e689`). Manifest records `sourceHead` for the integrated code before the evidence-only commit, so the receipts are pinned to implementation bytes rather than to a moving artifact.
- `terminal/docs/pr-crops/options-level-axis-labels/`: 3 PNGs (desktop / desktop-compact / mobile, `desktop-left-percentage.png`) + `manifest.json` schema `mastermind.options_level_axis_evidence/v1`. This crop is from a prior options lane (PR #676 area); the manifest was updated and re-captured against this exact integrated head, again with content hashes.
- Dark + light + EN + ZH × desktop / tablet / mobile coverage is preserved on the visual-intelligence crop. **No NEW visual surface was added, so no theme art-direction gate is required** under §Theme art direction in the root CLAUDE.md (the rule applies when introducing a material UI packet; coordinate plumbing is not one).
- `check_design_system.py` / `check_runtime_style_injection.py` / `check_ui_visual_evidence.py` are macro-only and do not apply to the terminal repo. The terminal repo carries its own plain-language enforcement (`check_plain_language.mjs`) and no local theme CI gate.

The PR body's "Collision control" section explicitly notes that shared browser-evidence files can collide mechanically across PRs and requires a later carrier to re-mint against its own final head — that discipline is honored here.

## validated-claims findings

**Verdict: PASS — exemplary calibration.**

The PR body uses measured, falsifiable language throughout and explicitly disclaims claims it cannot yet back. Inventory of strong claims:

| Phrase | Calibration |
|---|---|
| "Fixes the Terminal chart bug where drawings created inside indicator panes … move or escape into neighboring panes when that indicator pane's Y-axis is compressed or expanded." | Bounded to the specific bug class. No "all charts" overreach. |
| "Drawings now remain anchored to the indicator's own value space, remain clipped to the pane that owns them, and preserve existing price-pane/full-chart drawing behavior." | Cites the specific contract preserved (price-pane tools including vertical lines). |
| "Lightweight Charts consumes and returns series Y coordinates in **pane-local coordinates**, while Terminal's drawing SVG and pointer input use **chart-root coordinates**." | Technical claim tied to the API surface. |
| "stamp new indicator drawings with `paneCoordSpace: pane-value-v2`; migrate legacy pane drawings created since PR #481 once into corrected pane value space, persist the migration marker, and never reconvert them." | Precise, falsifiable, and scoped (one-shot migration, idempotent marker). |
| "The public production pre-deploy run is RED on the reported path: deployed Terminal does not emit `paneCoordSpace: pane-value-v2`. The same regression is GREEN on this PR head. Production must be rerun after deployment before this is called proven live." | **Explicitly disclaims production proof** until the rerun lands — the strongest calibration possible. |
| "No CI result is being claimed before it completes." | Pre-emptive guard against over-claim. |
| "Fresh hosted CI run: `35785778025` — queued/running for this exact head." | Names the exact run id; does not assert a green conclusion. |
| Test counts ("3/3 PASS", "30/30 PASS", "5/5 PASS", "379 files / 6,088 passed / 4 todo / 0 failed") | Concrete, granular, falsifiable receipts. |

No instances of "validated / proven / certified / guaranteed / ensures" surfaced into user-facing copy. No internal study names, raw slugs, or untranslated stat tokens leaked into the body. The phrase "current protected master" is consistent with the procedure pin block (Sol Skillpack reference), not a market-side authority claim.

## overall verdict

**PASS on all three dimensions.**

- **plain-language: PASS.** `check_plain_language.mjs --json` returns 0 added findings, 0 blocking, 6 pre-existing legacy reports unrelated to this PR. No new user-visible copy introduced.
- **theme: N/A (no material UI surface added); receipts RE-MINTED with content-hash pinning to implementation bytes.** 6 PNG EN/ZH × desktop/tablet/mobile + 3 PNG options-level crops; dark/light parity preserved by the inherited design; both manifest sources bind to `sourceHead` of the integrated code.
- **validated-claims: PASS.** Body uses measured language throughout and explicitly disclaims both CI conclusion (hosted run still queued) and live production proof ("Production must be rerun after deployment before this is called proven live"). Test counts are granular and falsifiable.

**Slot verdict: half-B, MERGEABLE.** The PR is a tight coordinate-math fix with one-shot legacy migration, idempotent marker, scoped SVG clipping, and disciplined evidence re-mint. Zero new visual surface, zero new copy surface, zero new claim surface. Recommended for archival without further change.

### Followups noted (not blockers)

1. The PR body's "Current protected Terminal master integrated" line locks the carrier to `3b488ce96` (#713). If a newer protected master lands before the merge-on-green sweep, the carrier must re-integrate to keep `paneLayoutFor` / `migrateLegacyPaneDrawings` consistent with the live renderer.
2. `mergeLegacyPaneDrawings` triggers on the first measured pane layout; if a user opens the chart with an indicator pane already compressed, the migration runs in the same paint cycle. The receipt `migratedLegacyDrawings` triggers a synchronous `renderDraw()` after `setPaneLayout`, which is correct but worth keeping an eye on for very large drawing stores.
3. No automated gate in the terminal repo covers validated-claims phrasing; the discipline here is human, not CI-enforced. Worth a future `check_validated_claims.py`-style addition if terminal starts shipping user-visible copy at this volume.

### Audit metadata

- Audit target selected: most recent merged half-B PR in `mastermind-terminal` or `macro` last 24 h, excluding already-audited PRs. `terminal #711` (`fix(chart)`, +280 / −96, 16 files) chosen over `macro #7704` (`Checkpoint China dashboard selective synthesis`, +248 / −0, 1 file of Agent OS continuation notes — not a user-facing surface, no plain-language or theme surface to audit).
- Existing `orch/audits/` files cross-checked via `git ls-tree origin/main -- orch/audits/`. Terminal audits on disk: `mastermind-terminal_PR-{648, 658, 670, 673, 684, 685, 689, 693, 695, 696, 698, 701, 704, 705, 706, 713, 716}.mm.md`. `terminal #711` is not in that set.
- Plain-language gate ran on PR head `b3c9c4d525f1d098ee5a8ea4fedca3e60ee58c87` via a transient git worktree at `/tmp/terminal-pr711` (removed after the check). No `ChartPanel.tsx` mutation left in the terminal repo (verified `git status` clean).
- Audit date: 2026-09-22.
