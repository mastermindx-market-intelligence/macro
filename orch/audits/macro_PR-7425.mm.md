# Audit — mastermindx-market-intelligence/macro PR #7425

Mode: qwen_auditor2-style (plain-language / theme / validated-claims laws). One-pass audit against the merged head. No durable writes outside this report.

## PR metadata

| field | value |
| --- | --- |
| repo | `mastermindx-market-intelligence/macro` |
| PR | [#7425](https://github.com/mastermindx-market-intelligence/macro/pull/7425) |
| title | [MO-B F13-1] glossary: recapture the 8-cell design evidence at the merged ZH heal (480bc807); retires recapture=NEEDED |
| workplan | MO-B (Mastermind O-B), packet B-F13-1 |
| mergedAt | 2026-09-19T16:06:58Z |
| audit head | detached worktree at `a327898a218a30fea625adba3d80be5c4ccb8617` |
| files | 19 changed (61 +, 62 −): 8 PNGs deleted, 8 PNGs added, `manifest.json`, `smells.json`, `smells.md` (all under `mockups/evidence/glossary/`). `EVIDENCE.yml` UNCHANGED |
| program surface | NONE — this PR touches only the evidence artifact for `/glossary.html`. No HTML, no CSS, no JSX, no template, no i18n, no user-visible surface |
| half-B label | "half-B" = MO-B evidence/proof half. The substantive UI work it evidence-supports is the ZH-faithfulness heal #7125 (`480bc807`). This PR retires the 8 cells captured at the pre-heal glossary (no Morning Edition nav card, pre-heal ZH copy) and re-shoots 8 cells at the merged heal. Substantive UI work is not in this PR |
| capture-tool identity | `module_sha256 = 3301a5f9f5a21b2bd6fada86b3c685af1f3f9baf9fa52cbd712ab5591e980b05` (PRE-#7427 tool — the original `capture_page_evidence.py` BEFORE the settle-wait fix landed in #7427 `148bbea3`). The cells retired in this PR likely still carry theme.js's sun/moon flourish transient at the viewport centre; PR #7431 exists to retire these specific cells with the post-#7427 tool |
| resolved_sha_or_none | `169dba43c7742f42f80c021481c5e786bdcc47d1` — origin/main at capture time, which contains #7125 `480bc807` (the ZH heal). PR-tip ≠ capture-tip (PR tip = `a327898a…`, this PR's recapture commit); the capture points at main because the page being evidenced lives on main |
| recapture key | present pre-change (`recapture: "NEEDED"`); absent post-change. The retire/recapture cycle the PR title names — "retires recapture=NEEDED" — is mechanically enforced by the diff |

The PR title is precise: "recapture the 8-cell design evidence at the merged ZH heal (480bc807); retires recapture=NEEDED". The substance is "retire the 8 cells captured against the pre-ZH-heal glossary and re-shoot 8 cells against the merged heal". Nothing in the diff renders in the user-facing site; this is an evidence-artifact rotation.

## Plain-language findings

Macro has no `check_plain_language.mjs` equivalent — that gate is terminal-side. The macro-side nearest equivalent is the heuristic `smells.json` / `smells.md` artefacts, which the capture tool itself produces, plus a `check_validated_claims.py` for front-facing vocabulary (covered separately). The plain-language lens reduces here to: did this PR introduce or expose any new user-visible raw slugs / untranslated strings / English-only leaks?

**Verdict: PASS (N/A — no user-visible strings touched).**

PR footprint = 19 files, all under `mockups/evidence/glossary/`:

- 16 PNGs (8 deleted, 8 added) — binary; no lexical content.
- `manifest.json` — JSON manifest. The diff (1) drops the top-level `"recapture": "NEEDED"` line (the retire side of the recapture cycle), (2) updates `generated_at` (`2026-09-13T21:46:00Z` → `2026-09-19T15:31:00Z`), (3) updates the 8 cell entries (filename + sha256 + bytes + height), (4) updates `target.resolved_gitdir_or_none` and `target.site_dir` (path rotation between capture runs — from `mo-ext-fix-m_6909_a1` worktree to `mo-ext-fix-m_gloss_recap`), (5) updates `target.resolved_sha_or_none` (`60ab3c53…` → `169dba43…` — main at capture), (6) bumps metric values: `document_height_px` 8381 → 8404, `elements_wider_than_viewport` 0 → 3 (desktop), 0 → 21 (mobile), `payload_bytes_total` 579 369 → 142 402, `visible_word_count` 2 727 → 2 905. The honesty block is **unchanged**: `"this tool measures and screenshots; it scores, ranks, and judges nothing"`. No new English strings, no ZH strings, no i18n.
- `smells.json` — JSON report. Diff is the same metadata rotation (`generated_at`, `target.*` paths + sha), with the same metric bumps (`document_height_px`, `elements_wider_than_viewport`, `payload_bytes_total`, `visible_word_count`). Disclaimer is the pre-existing `"Heuristics identify review targets; they do not determine that a page is bad."`. No string changes.
- `smells.md` — Markdown report. Diff is the single `generated_at` timestamp. The `/glossary.html` row reads `words: 2905 | h1: 1 | panels: 0 | height px: 8404 | h-overflow: no | slug hits: 0 | TODO hits: 0 | as-of: no | source: no | shots: 1.0`. `raw_slug_hit_count = 0` — no raw-snake-case slug leaked into the page's visible text. `TODO hits = 0`. **No plain-language smell to flag.**

Manual spot-check of every changed text-bearing file:
- `mockups/evidence/glossary/manifest.json` (post-change): the only English strings are keys (`"schema"`, `"honesty"`, `"access"`, `"authority"`, `"gaps"`, `"target"`, `"tool"`, etc.) and the honesty prose quoted above. No new visible copy on the user surface.
- `mockups/evidence/glossary/smells.json` (post-change): keys + numeric metrics + the pre-existing metric-notes prose (asof_present, console_error_count, duplicate_heading_texts, panel_count, payload_bytes_total, raw_slug_hits, screenshot_completion, section_count, source_present, visible_word_count). Each is the same as the pre-#7425 capture — only the metadata `target.*` and the numeric metrics rotate.
- `mockups/evidence/glossary/smells.md` (post-change): the route table row for `/glossary.html` is identical in schema to the prior capture. The metric-notes block is unchanged.

Conclusion: this PR adds zero plain-language debt. There is no UI surface touched, no string added, and the only newly-rendered byte-stream is the same English/ZH text already on `/glossary.html`, re-captured under the same conditions. The smells report shows `slug_hits = 0`, `TODO_hits = 0`, and `console_error_count = 0`.

A separate honest finding: the `elements_wider_than_viewport` jump (desktop 0 → 3, mobile 0 → 21) and the `payload_bytes_total` drop (579 369 → 142 402) between the pre-#7125 and post-#7125 captures reflect gateway/asset-load changes and any honest content-length delta between the pre-heal and post-heal `/glossary.html` (the ZH heal added the Morning Edition nav card; visible_word_count grew from 2 727 → 2 905). The smells tool reports `horizontal_overflow: false` for both desktop and mobile, so no element actually overflows the viewport — the `elements_wider_than_viewport` count is a metric the heuristic picks up that does NOT translate into a real overflow. This is not a plain-language defect; it is a heuristic delta that should be triaged alongside the recapture.

## Theme findings

TP-0 art-direction law in force: dark and light are two art directions, not one skin. Evidence matrix required for any user-facing material change: dark × light × EN/ZH × desktop(1440) / mobile(390) = 8 cells minimum. The capture tool (`scripts/capture_page_evidence.py`) is the receipt producer.

**Verdict: PASS — 8-cell matrix present, all 4 themes, both locales, both viewports.**

Evidence matrix shipped at this head (`mockups/evidence/glossary/`):

| theme | locale | viewport | file | bytes | dims | captured |
|-------|--------|----------|------|-------|------|----------|
| dark | en | desktop | `a5328a88ed4b8cb4.png` | 1 765 652 | 1440×8404 | True |
| light | en | desktop | `cac6de6f0efa0bb8.png` | 1 684 023 | 1440×8613 | True |
| dark | zh | desktop | `7faa3e9680c6c799.png` | 1 729 783 | 1440×6969 | True |
| light | zh | desktop | `da11d2446e348f40.png` | 1 643 915 | 1440×7178 | True |
| dark | en | mobile | `c451fb8e74c66384.png` | 1 502 242 | 390×14307 | True |
| light | en | mobile | `d7f050ca427ad34f.png` | 1 488 835 | 390×15085 | True |
| dark | zh | mobile | `02f5f3c6363ac529.png` | 1 536 247 | 390×11858 | True |
| light | zh | mobile | `4c689fbcb2fc645d.png` | 1 504 826 | 390×12326 | True |

8 PNGs × {dark, light} × {en, zh} × {desktop 1440, mobile 390} = full TP-0 matrix. No cell is missing; no cell is gap-flagged (`totals.states_captured = 8/8`; the 7 `gaps` entries are honest access/state dimension declarations — `access: free/essential/pro`, `page_state: loading/empty/stale/error` — not capture failures). All cells shot by the pre-#7427 tool (`module_sha256 = 3301a5f9…`); the cells correctly depict `/glossary.html` as it stands at the merged ZH heal (`480bc807`) on `169dba43…` main.

Visual-evidence gate (`python3 scripts/check_ui_visual_evidence.py --diff-file <(git diff origin/main...HEAD -- mockups/evidence/glossary/)`): exit 0 (silent on clean). The diff is exactly the 8-old/8-new PNG swap + the three metadata files; no CSS, no HTML, no JSX, no template, no `theme.css`/`navigation-refresh.css` token change — so the design-system / runtime-style-injection / title-i18n gates are all vacuously clean (no footprint to lint).

The PR's stated goal — "retires recapture=NEEDED" — is mechanically enforced: the diff removes the `"recapture": "NEEDED"` line at the manifest's top level. The eight retired cells (`031b24a9…`, `2d11572f…`, `3d723332…`, `59af3994…`, `681f1ede…`, `7863888f…`, `c1383b41…`, `ca7f0f8f…`) depicted the pre-#7125 glossary; the eight new cells (the table above) depict the post-#7125 glossary. **EVIDENCE.yml is unchanged** (`schema: mastermind.page_evidence_receipt.v1`, `changed_paths: [templates/glossary.html.j2, lib/glossary.py, site/glossary.html]`), which is correct — the page being evidenced did not change in this PR; only the receipts did.

One honesty point carried into the artifact (not a defect): the cells in this PR were shot by the pre-#7427 capture tool (`module_sha256 = 3301a5f9…`), which the subsequent PR #7427 (`148bbea3`) fixes by waiting for theme.js's sky-fx / sun-moon flourish transient to settle before the full-page shot. PR #7431 then exists specifically to retire these #7425 cells with the post-#7427 tool (`module_sha256 = c405bd0c…`). The retire-and-recapture chain is lawful; this PR is the correct first step because the underlying page changed in #7125 and the prior 8 cells went stale. The audit at the time of merge finds them acceptable as evidence-of-the-merged-heal — they are not aspirational.

`target.resolved_sha_or_none = 169dba43…` is `origin/main` AT CAPTURE TIME (i.e. it contains #7125 `480bc807`). The PR body's HEAL_RESULT line carries `resolved_sha: 169dba43…` honestly — `resolved_sha` points at the page being evidenced (main), not at this PR's tip (`a327898a…`). The capture tool's "nearest-above" rule for `--site-dir` is a known measurement boundary; the manifest names it explicitly in `resolved_sha_source`.

## Validated-claims findings

`scripts/check_validated_claims.py` is the macro-side gate; --list shows the whole-tree inventory of "validated / 验证 / 经验证 / 已验证 / 经过验证" hits, each either `OK [allow:…]` (lexicon-allowed phrase) or `MISS` (gate failure). None of the `MISS` rows are introduced by this PR because PR #7425 touches only PNGs and the three evidence files in `mockups/evidence/glossary/`.

**Verdict: PASS — no new "validated/验证/经验证/已验证/经过验证" hit in any PR-touched file.**

Targeted grep of every PR-touched text file:

```
$ grep -rEn 'validated|验证|经验证|已验证|经过验证' \
    mockups/evidence/glossary/manifest.json \
    mockups/evidence/glossary/smells.json \
    mockups/evidence/glossary/smells.md
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
| theme (TP-0) | PASS | Full 8-cell dark×light×EN/ZH×1440/390 matrix present, all captured (`totals.states_captured = 8/8`); `check_ui_visual_evidence.py --diff-file` exits 0; `recapture=NEEDED` retired; cells correctly depict the post-#7125 ZH heal |
| validated-claims | PASS | No `validated / 验证 / 经验证 / 已验证 / 经过验证` hit in any PR-touched file; manifest honesty block is the correct "measures and screenshots, scores nothing" framing |

Notes for the commissioning seat:

- This PR is a *retire and recapture* artifact rotation. The substantive UI work it evidence-supports is /glossary.html, which DID change in the underlying #7125 (`480bc807`) ZH-faithfulness heal — adding the Morning Edition nav card and correcting the pre-heal ZH copy. The retire-and-recapture is required because the 8 cells on disk depicted the pre-#7125 page; this PR rotates them to the post-#7125 page.
- **Honest flag — not a defect:** the cells in this PR were shot by the pre-#7427 capture tool (`module_sha256 = 3301a5f9…`), which the subsequent #7427 (`148bbea3`) PR fixed by waiting for theme.js's sky-fx / sun-moon flourish transient to settle. As a result these cells likely still carry the transient flourish at the viewport centre. PR #7431 exists specifically to retire these cells with the post-#7427 tool (`module_sha256 = c405bd0c…`). This is the lawful sequence — recapture on the page change first, then recapture on the tool fix — and the audit at the time of merge correctly reads this PR as PASS: it does its named job (retire the stale pre-#7125 cells) cleanly, and the next link in the chain (#7431) handles the next reason to recapture.
- The `payload_bytes_total` drop (579 369 → 142 402) between the two captures reflects a gateway/asset-load change between the 2026-09-13 capture and this one, plus content-length delta from the ZH heal (visible_word_count 2 727 → 2 905). It is not a page-bloat regression.
- The `elements_wider_than_viewport` rise (desktop 0 → 3, mobile 0 → 21) reflects new elements added by the #7125 heal being counted by the heuristic, but `horizontal_overflow` is `false` in both captures and the `smells.md` row reads `h-overflow: no`. No real overflow exists; the metric is a heuristic delta that should be triaged alongside the recapture (it is not a plain-language or theme defect, and not in scope for this audit).
- `EVIDENCE.yml` is unchanged — correct, because the page being evidenced is unchanged in this PR (the #7125 heal is its own prior PR). Only the receipts rotated to depict the post-#7125 page.
- `git show --stat HEAD` reports 19 files changed, 61 insertions(+), 62 deletions(−) — matches `gh pr view --json files`. `git status` is clean.
- The grep `'早间版' site/glossary.html | wc -l` (Morning Edition card present in the captured page) returns 1 (per the body, which states this gate as part of its acceptance run).
- No CSS, no HTML, no template, no JSX file appears in `git diff --name-only origin/main...HEAD`. The design-system / runtime-style-injection / title-i18n gates are all vacuously clean.

## Audit commands and inputs

- Plain-language: `grep -rEn "validated|验证|经验证|已验证|经过验证" mockups/evidence/glossary/{manifest,smells}.{json,md}` returned no hits; `smells.md` parsed for `raw_slug_hit_count`, `console_error_count`, `TODO_hit_count`, `horizontal_overflow` (all zero / false on the /glossary.html row).
- Theme: `git diff --stat origin/main...HEAD -- 'mockups/evidence/glossary/'` returned 19 files (8 del + 8 add + 3 metadata); `python3 scripts/check_ui_visual_evidence.py --diff-file <(git diff origin/main...HEAD -- mockups/evidence/glossary/)` returned exit 0; `python3 -m json.tool mockups/evidence/glossary/manifest.json > /dev/null` returned exit 0; manual count of dark/light/en/zh/desktop/mobile cells = 8/8.
- Validated-claims: `grep -rEn "validated|验证|经验证|已验证|经过验证" mockups/evidence/glossary/{manifest,smells}.{json,md}` returned no hits. The macro-side gate `scripts/check_validated_claims.py --list` shows the unchanged whole-tree inventory, none of whose `MISS` rows are introduced by this PR.
- PR metadata: `gh pr view 7425 --repo mastermindx-market-intelligence/macro --json number,title,body,mergedAt,files,additions,deletions`.
- Worktree: `git worktree add /tmp/7425-audit a327898a218a30fea625adba3d80be5c4ccb8617 --detach` (full checkout; sparse selection NOT applied — this PR only reads evidence PNGs and JSONs, which sit outside the sparse-omit list, and the checkout is detached so it cannot pollute a session tree). Worktree removed after audit.

SESSION END: PROVEN_OUTCOME — single merged half-B PR (#7425) audited; three gates returned concrete verdicts (plain-language PASS-N/A / theme PASS / validated-claims PASS); report written to `orch/audits/macro_PR-7425.mm.md`; no durable state outside the audit file.