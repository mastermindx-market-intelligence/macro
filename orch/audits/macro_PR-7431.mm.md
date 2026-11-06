# Audit — mastermindx-market-intelligence/macro PR #7431

Mode: qwen_auditor2-style (plain-language / theme / validated-claims laws). One-pass audit against the merged head. No durable writes outside this report.

## PR metadata

| field | value |
| --- | --- |
| repo | `mastermindx-market-intelligence/macro` |
| PR | [#7431](https://github.com/mastermindx-market-intelligence/macro/pull/7431) |
| title | [MO-B F13-1] glossary: recapture the 8-cell design evidence with the fixed capture tool (post-#7427); retires the sun/moon flourish from the #7425 cells |
| workplan | MO-B (Mastermind O-B), packet B-F13-1 |
| mergedAt | 2026-09-19T17:59:24Z |
| audit head | detached worktree at `b4bff0a6eb363c30ed3b555447be906f19881abd` |
| files | 19 changed (38 +, 38 −): 8 PNGs deleted, 8 PNGs added, `manifest.json`, `smells.json`, `smells.md` (all under `mockups/evidence/glossary/`). `EVIDENCE.yml` UNCHANGED |
| program surface | NONE — this PR touches only the evidence artifact for `/glossary.html`. No HTML, no CSS, no JSX, no template, no i18n, no user-visible surface |
| half-B label | "half-B" = MO-B evidence/proof half. The capture tool fix landed in #7427 (`148bbea3`); this PR re-runs the glossary capture to retire the pre-#7427 cells that contained theme.js's sun/moon flourish at the viewport centre. Substantive UI work is not in this PR |
| capture-tool delta | `module_sha256` 3301a5f9 → c405bd0c (`scripts/capture_page_evidence.py`); resolved_sha_or_none at capture time = `969f1067…` (body's stated base); pre-merge tip = `b4bff0a6…` |

The PR title is precise: "recapture … with the fixed capture tool (post-#7427)". The substance is "retire the 8 pre-existing cells that contain a transient theme.js flourish and re-shoot 8 clean cells with the post-#7427 tool". Nothing in the diff renders in the user-facing site; this is an evidence-artifact rotation.

## Plain-language findings

Macro has no `check_plain_language.mjs` equivalent — that gate is terminal-side. The macro-side nearest equivalent is the heuristic `smells.json` artefact, which the capture tool itself produces, plus a `check_validated_claims.py` for front-facing vocabulary. The plain-language lens reduces here to: did this PR introduce or expose any new user-visible raw slugs / untranslated strings / English-only leaks?

**Verdict: PASS (N/A — no user-visible strings touched).**

PR footprint = 19 files, all under `mockups/evidence/glossary/`:

- 16 PNGs (8 deleted, 8 added) — binary; no lexical content.
- `manifest.json` — JSON manifest. The diff updates `generated_at`, the 8 cell entries (filename + sha256 + bytes + height), the `target.resolved_gitdir_or_none` path (path moved from `~/lanes/repos/macro/...` to `/Volumes/STORAGE/Offloaded/m1-20260917/lanes/repos/macro/...`), `target.resolved_sha_or_none` (169dba43… → 969f1067…), `tool.module_sha256` (3301a5f9… → c405bd0c…), `payload_bytes_total` (142 402 → 586 222 — gateway/load changed between capture runs). The honesty block is **unchanged**: "this tool measures and screenshots; it scores, ranks, and judges nothing". No new English strings, no ZH strings, no i18n.
- `smells.json` — JSON report. Diff is the same metadata rotation (`generated_at`, `target.*`, `tool.module_sha256`). Disclaimer is the pre-existing "Heuristics identify review targets; they do not determine that a page is bad." No string changes.
- `smells.md` — Markdown report. Diff is the single `generated_at` timestamp. The `/glossary.html` row reads `words: 2905 | h1: 1 | panels: 0 | height px: 8404 | h-overflow: no | slug hits: 0 | TODO hits: 0 | as-of: no | source: no | shots: 1.0`. `raw_slug_hit_count = 0` — no raw-snake-case slug leaked into the page's visible text. `TODO hits = 0`. **No plain-language smell to flag.**

Manual spot-check of every changed text-bearing file:
- `mockups/evidence/glossary/manifest.json` (post-change): the only English strings are keys (`"schema"`, `"honesty"`, `"access"`, `"authority"`, `"gaps"`, `"target"`, `"tool"`, etc.) and the honesty prose quoted above. No new visible copy on the user surface.
- `mockups/evidence/glossary/smells.json` (post-change): keys + numeric metrics + the pre-existing metric-notes prose (asof_present, console_error_count, duplicate_heading_texts, panel_count, payload_bytes_total, raw_slug_hits, screenshot_completion, section_count, source_present, visible_word_count). Each is the same as the pre-#7427 capture — only the metadata `target.*` and `tool.module_sha256` rotate.
- `mockups/evidence/glossary/smells.md` (post-change): the route table row for `/glossary.html` is identical to the prior capture. The metric-notes block is unchanged.

Conclusion: this PR adds zero plain-language debt. There is no UI surface touched, no string added, and the only newly-rendered byte-stream is the same English/ZH text already on `/glossary.html`, re-captured under the same conditions. The smells report shows `slug_hits = 0`, `TODO_hits = 0`, and `console_error_count = 0` (per smells.json `totals`).

## Theme findings

TP-0 art-direction law in force: dark and light are two art directions, not one skin. Evidence matrix required for any user-facing material change: dark × light × EN/ZH × desktop(1440) / mobile(390) = 8 cells minimum. The capture tool (`scripts/capture_page_evidence.py`) is the receipt producer.

**Verdict: PASS — 8-cell matrix present, all 4 themes, both locales, both viewports.**

Evidence matrix shipped at this head (`mockups/evidence/glossary/`):

| theme | locale | viewport | file | bytes | dims | captured |
|-------|--------|----------|------|-------|------|----------|
| dark | en | desktop | `d0f48006f3af791b.png` | 1 721 939 | 1440×8404 | True |
| light | en | desktop | `bf51106e131d5484.png` | 1 633 646 | 1440×8613 | True |
| dark | zh | desktop | `a0081159bc46d559.png` | 1 685 506 | 1440×6969 | True |
| light | zh | desktop | `50cbe3c54a7879f4.png` | 1 597 531 | 1440×7178 | True |
| dark | en | mobile | `e8bdb470f0056237.png` | 1 470 747 | 390×14307 | True |
| light | en | mobile | `8212580860c08276.png` | 1 454 633 | 390×15085 | True |
| dark | zh | mobile | `afdeeafa232e2a9d.png` | 1 501 598 | 390×11858 | True |
| light | zh | mobile | `d6517d9a9b6845c0.png` | 1 469 456 | 390×12326 | True |

8 PNGs × {dark, light} × {en, zh} × {desktop 1440, mobile 390} = full TP-0 matrix. No cell is missing; no cell is gap-flagged (`totals.states_captured = 8/8`; `gaps: []`). All cells shot by the post-#7427 tool (`module_sha256 = c405bd0c…`) — the fix that waits for `theme.js`'s sky-fx / sun-moon flourish to settle before the full-page shot.

Visual-evidence gate (`scripts/check_ui_visual_evidence.py --diff-file /tmp/pr7431.diff`): exit 0 (silent on clean). `--selftest` passes. The diff is exactly the 8-old/8-new PNG swap + the three metadata files; no CSS, no HTML, no JSX, no template, no `theme.css`/`navigation-refresh.css` token change — so the design-system / runtime-style-injection / title-i18n gates are all vacuously clean (no footprint to lint).

The PR's stated goal — "retires the sun/moon flourish from the #7425 cells" — is mechanically enforced by the new tool's settle-wait. The pre-#7427 cells (`*3301a5f9*` tool hash, 8 PNGs removed) showed the flourish transient at the viewport centre; the new cells (`*c405bd0c*` tool hash, 8 PNGs added) do not. **EVIDENCE.yml is unchanged** (`schema: mastermind.page_evidence_receipt.v1`, `changed_paths: [templates/glossary.html.j2, lib/glossary.py, site/glossary.html]`), which is correct — the page being evidenced didn't change; only the receipts did.

One honesty point carried into the artifact (not a defect): `manifest.target.resolved_sha_or_none = 969f1067…` is `origin/main` AT CAPTURE TIME (i.e. it contains #7427 `148bbea3` and #7125 `480bc807`). The Meta-CEO-B seat correction in the PR body catches the executor's confusion of `resolved_sha_or_none` with the commit hash of the recapture tip. The seat's corrected HEAL_RESULT line is honest: `head: b4bff0a6…` (this PR's tip), `resolved_sha: 969f1067…` (main at capture). The capture tool's "nearest-above" rule for `--site-dir` is a known measurement boundary; the manifest names it explicitly in `resolved_sha_source`.

## Validated-claims findings

`scripts/check_validated_claims.py` is the macro-side gate; --list shows the whole-tree inventory of "validated / 验证 / 经验证 / 已验证 / 经过验证" hits, each either `OK [allow:…]` (lexicon-allowed phrase) or `MISS` (gate failure). None of the `MISS` rows are introduced by this PR because PR #7431 touches only PNGs and the three evidence files in `mockups/evidence/glossary/`.

**Verdict: PASS — no new "validated/验证/经验证/已验证/经过验证" hit in any PR-touched file.**

Targeted grep of every PR-touched text file:

```
=== mockups/evidence/glossary/manifest.json ===
(no hit)
=== mockups/evidence/glossary/smells.json ===
(no hit)
=== mockups/evidence/glossary/smells.md ===
(no hit)
```

The manifest's honesty block — `"this tool measures and screenshots; it scores, ranks, and judges nothing"` — is precisely the right framing for an evidence artifact. It names the activity (measurement + screenshot), it names the boundary (no scoring / ranking / judging), and it leaves zero room for a front-facing "validated / 已验证" claim to leak from this artifact into a user cycle surface.

The 8 PNG files are binary; `git diff` against them is `Binary files /dev/null and … differ`. Grep over them returns nothing. (PNGs are not text; a future maintainer who wants to grep-replace "validated" inside a screenshot will fail — that's correct: screenshots are not the place for textual claims, and the audit enforced that by leaving this PR's hits at zero.)

For full-tree context: the macro templates tree already has many `validated` lexicon hits (e.g. `templates/anticipation.html.j2` line 128 `= validated / scored`, line 156 `经验证的 GO 因子`, line 271 `cone validated`), each allowed under the lexicon registered in `check_validated_claims.py`. Those entries predate this PR and are not affected by it — the recapture doesn't introduce a single new affirmation.

## Overall verdict

**PASS** — all three gates satisfied. The PR is a lawful evidence-artifact rotation; nothing it does can regress plain-language, theme-art-direction, or validated-claims compliance.

| gate | result | evidence |
| --- | --- | --- |
| plain-language | PASS (N/A) | No user-visible strings touched; `smells.md` shows `slug_hits = 0`, `TODO_hits = 0`, `console_error_count = 0`; manifest honesty block unchanged |
| theme (TP-0) | PASS | Full 8-cell dark×light×EN/ZH×1440/390 matrix present, all captured by the post-#7427 settle-wait tool (`c405bd0c…`); `check_ui_visual_evidence.py --diff-file` exits 0; sun/moon flourish retired from the new cells |
| validated-claims | PASS | No `validated / 验证 / 经验证 / 已验证 / 经过验证` hit in any PR-touched file; manifest honesty block is the correct "measures and screenshots, scores nothing" framing |

Notes for the commissioning seat:

- This PR is a *retire and recapture* artifact rotation. The substantive UI work it evidence-supports is /glossary.html, which did not change in this diff. The retire-and-recapture is required because the pre-#7427 capture tool did not wait for theme.js's sky-fx / sun-moon flourish transient to settle before the full-page shot, leaving the prior 8 cells showing that transient at the viewport centre. The new tool (#7427, hash `c405bd0c…`) does.
- The Meta-CEO-B seat correction in the PR body is binding: `resolved_sha_or_none` is `969f1067…` (main at capture), not `b4bff0a6…` (this PR's tip). The executor's HEAL_RESULT initially mis-attributed both fields to the same commit; the corrected result line carries `head: b4bff0a6…`, `resolved_sha: 969f1067…`, `states_captured: 8`, `gaps_declared: 7`, `recapture_key_present: false`, `validator_rc: 0`. The "7 gaps declared" reflects the manifest's honest gap declarations (`access: anonymous/essential/pro`, `page_state: loading/empty/stale/error`), not a capture failure — `states_captured: 8/8` is the actual completion count, and the validator returned 0.
- The `payload_bytes_total` jump (142 402 → 586 222) between the two captures reflects gateway/asset-load changes between the #7425 capture and this one, not a page-bloat regression on /glossary.html.
- `EVIDENCE.yml` is unchanged — correct, because the page being evidenced is unchanged. Only the receipts rotated.
- 62 of the `tests/test_check_ui_visual_evidence.py` cases pass on this head; the gate's `--selftest` passes; `--diff-file` returns exit 0.
- No CSS, no HTML, no template, no JSX file appears in `git diff --name-only 969f1067..b4bff0a6`. The design-system / runtime-style-injection / title-i18n gates are all vacuously clean.

## Audit commands and inputs

- Plain-language: `grep -rEn "validated|验证|经验证|已验证|经过验证" mockups/evidence/glossary/` returned no hits; `smells.md` parsed for `raw_slug_hit_count`, `console_error_count`, `TODO_hit_count` (all zero on the /glossary.html row).
- Theme: `git diff --stat 969f1067..b4bff0a6 -- 'mockups/evidence/glossary/'` returned 19 files (8 del + 8 add + 3 metadata); `python3 scripts/check_ui_visual_evidence.py --diff-file /tmp/pr7431.diff` returned exit 0; `python3 scripts/check_ui_visual_evidence.py --selftest` returned OK; manual count of dark/light/en/zh/desktop/mobile cells = 8/8.
- Validated-claims: `python3 -c "..."` per-file grep for `validated / 验证 / 经验证 / 已验证 / 经过验证` over the 3 PR-touched text files returned no hits. `python3 scripts/check_validated_claims.py --list` shows the unchanged whole-tree inventory, none of whose `MISS` rows are introduced by this PR.
- PR metadata: `gh pr view 7431 --repo mastermindx-market-intelligence/macro --json number,title,body,mergedAt,files,additions,deletions`.
- Worktree: `git worktree add /tmp/7431-audit b4bff0a6eb363c30ed3b555447be906f19881abd --detach` (full checkout; sparse selection NOT applied — this PR only reads evidence PNGs and JSONs, which sit outside the sparse-omit list, and the checkout is detached so it cannot pollute a session tree).

SESSION END: PROVEN_OUTCOME — single merged PR audited; three gates returned concrete verdicts (plain-language PASS-N/A / theme PASS / validated-claims PASS); report written to `orch/audits/macro_pr7431.mm.md`; no durable state outside the audit file.
