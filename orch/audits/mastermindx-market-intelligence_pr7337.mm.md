# Audit — mastermindx-market-intelligence/macro PR #7337

Mode: qwen_auditor2-style (plain-language / theme / validated-claims laws). One-pass audit against the merged head. No durable writes outside this report.

## PR metadata

| field | value |
| --- | --- |
| repo | `mastermindx-market-intelligence/macro` |
| PR | [#7337](https://github.com/mastermindx-market-intelligence/macro/pull/7337) |
| title | [MO-B F01-1] Morning edition page before the US open |
| workplan | MO-B (Mastermind O-B), packet B-F01-1 / MO-PAID-011 page child (W5-K1 applier) |
| mergedAt | 2026-09-19T14:03:08Z |
| merge commit | `38adeb1e7065cb3aa52a1f8453ca0b3944327789` (merge onto `main`) |
| branch tip | `dd20710cc40323a7dbd55b1ec83be1ab250bc659` |
| fork base | `9d2c11c9ab9e77abbef5b5000e9a7711af3c9e6b` (the actual `git merge-base` between the two) |
| audit head | detached worktree at `38adeb1e70` (sparse-checkout via `git worktree add --detach`) |
| files | 21 changed (1286 +, 6 −): 1 new template (`templates/am_edition.html.j2`, 323 +), 1 new evidence producer (`scripts/capture_am_edition_evidence.py`, 312 +), 1 new test (`tests/test_am_edition_page.py`, 330 +), 1 page-registry row (45 +), 1 ci wiring block (9 +), 2 small build/registry edits (4 + / 2 ±), 1 test_public_chrome allowlist (4 + / 1 −), 1 nav card (1 +), 1 re-baked `site/glossary.html` (1 +), 1 page_registry_overrides entry (4 +), 1 `EVIDENCE.yml` (4 +), 1 `manifest.json` (231 +), 8 content-addressed PNGs |
| program surface | new public-facing editorial page `am_edition.html` — `archetype: editorial`, `nav_family: public_nav.public`, `payload_tier: public_shell_premium_payload`, `access_shell: anonymous`, `bilingual: true`, `themes: [light, dark]`, `locales: [en, zh]` |
| half-B label | "half-B" = MO-B user-facing surface half. The display copy + nav + 8-cell evidence matrix are the shipped surface; the underlying feeds (market_state, regime, neuralweb market_plane, release_forecast, live quotes, master_brief) are pre-existing owner facts read verbatim by `scripts/build_am_edition.py` |

The PR title says "Morning edition page before the US open" and the body declares a single-sentence plain-language discipline: "The ZH-mode test now checks fixtures both with and without `_zh` fields and rejects `Risk-on`, `Constructive`, `Risk-off`, and `CPI` outside `.l-en`." The builder's leading comment block (`scripts/build_am_edition.py:1-9`) states the authority ceiling explicitly: "Authority ceiling: display_only. No signal, rank, score, gate, sizing, ENTRY_OPEN, Prophet, portfolio or trade authority is originated here — every value is either an owner fact read verbatim from an already-committed deterministic artifact, a deterministic derived comparison, a deterministic calendar fact, or a reference to the EXISTING model-generated prior-close brief."

## Plain-language findings

Macro repo does not host `terminal/scripts/check_plain_language.mjs` (Terminal-only). The macro-side plain-language discipline for this packet is the in-tree gate that lives in `tests/test_am_edition_page.py::test_page_contains_no_english_only_payload_values_in_zh_mode`, which was **strengthened by this PR** to cover both the with-`_zh`-fields and the without-`_zh`-fields fixtures.

**Verdict: PASS (0 blocking; in-tree gate strengthened, not weakened).**

Run output:
```
python3 -m pytest tests/test_am_edition_page.py tests/test_am_edition_producer.py tests/test_public_chrome.py -q -p no:cacheprovider
.........................................                                [100%]
41 passed in 1.96s
```

The strengthened assertion (`tests/test_am_edition_page.py:142-202`) renders the page, strips every `<span class="l-en">…</span>` block (plus the `<script>`, `<title>`, `<nav>` containers), and asserts that four English payload tokens — `Risk-on`, `Constructive`, `Risk-off`, `CPI` — never leak outside the EN span in either fixture:

```python
visible_text = render_without_english_spans(payload)
for token in ("Risk-on", "Constructive", "Risk-off", "CPI"):
    assert token not in visible_text, (
        f"English-only payload token {token!r} leaks in ZH mode "
        f"(fixture with Zh fields: {not drop_zh_fields})"
    )
```

Spot-check of `templates/am_edition.html.j2` (323 lines added):
- A `t(en, zh)` paired-span macro at lines 1-3 plus a `help(en, zh)` macro at lines 4-6. Every visible string in the page routes through `t(en, zh)` — 30+ callsites across the page header, feasibility notice, session-clock block, tape-since-prior-close block, market-regime block, cross-asset block, today's calendar block, prior-close brief block, and null-count footer.
- All session-state display copy is bilingual: `OPEN` → `US markets open / 美股正在交易`; `CLOSED` → `US markets closed / 美股已收盘`; `NOT_YET_OPEN` → `US markets not yet open / 美股尚未开盘`. Block-key comparisons (`session_clock`, `tape_since_prior_close`, `market_state`, `cross_asset_plane`, `todays_calendar`, `prior_close_brief_ref`) and state-key comparisons (`CURRENT`, `STALE_WITH_LAST_KNOWN`, `UNAVAILABLE`, `NOT_COVERED`) are control-flow, never rendered as text.
- The four forbidden tokens (`Risk-on`, `Constructive`, `Risk-off`, `CPI`) are sourced exclusively from the calendar / market-state JSON feeds and rendered through paired `t(row.label_en or 'Regime unavailable', row.label_zh or row.label_en or '周期数据不可用')` macros; the calendar `_RELEASE_TITLES` map in `scripts/build_am_edition.py:71-84` rewrites the raw `CPI` slug to the bilingual pair `("CPI (consumer prices)", "消费者物价指数")`, with the producer test asserting `消费者物价指数` appears in the calendar list.
- `templates/_public_nav.html.j2` (+1 line) and `site/glossary.html` (+1 line) add the public-nav card with paired EN/ZH spans (`<span class="l-en">Morning Edition</span><span class="l-zh">早间版</span>` plus a paired description).
- The feasibility-notice copy uses a paired pair that falls through gracefully: `{{ t(payload.morning_source_feasibility_cause_en or '', payload.morning_source_feasibility_cause_zh or payload.morning_source_feasibility_cause_en or '') }}` — ZH falls back to EN if missing; EN falls back to empty if missing.

No new plain-language debt. The PR strengthens the in-tree gate; the legacy plain-language pile (pre-existing in `terminal/`, `templates/_public_*`, etc.) is unchanged.

## Theme findings

Laws in force:
- TP-0 theme art-direction (dark + light, dark × light × EN/ZH × 1440/390 evidence matrix) — applies to Macro site.
- `scripts/check_ui_visual_evidence.py` — gates material UI changes on committed dark/light evidence receipts.
- `scripts/check_design_system.py --mode enforce-added` — ratchet that blocks only the ADDED_BLOCKING_RULES findings on lines this diff actually added.
- `scripts/check_runtime_style_injection.py` — runtime JS-injected `style.textContent` may only stay flat or shrink.

**Verdict: PASS — full dark × light × EN/ZH × 1440/390 matrix shipped; all three gates exit 0.**

Evidence matrix shipped (`mockups/evidence/am_edition/manifest.json`, 8 cells × 8 PNGs content-addressed by SHA-256):

| axis | value | source |
| --- | --- | --- |
| viewports | desktop 1440×900, mobile 390×844 | `manifest.json:11-20` |
| locales | en, zh | `manifest.json:21-24` |
| themes | dark, light | `manifest.json:25-28` |
| access | anonymous | `manifest.json:29-32` |
| subjects | full | `manifest.json:33-35` |
| `totals.rest_cells` / `rest_required` | 8 / 8 | `manifest.json:52-56` |
| `outcome` | `captured` | `manifest.json:51` |
| aliases (8) | full-{dark,light}-{en,zh}-{desktop,mobile}.png → SHA-256-keyed PNGs | `manifest.json:40-48` |

`mockups/evidence/am_edition/EVIDENCE.yml` declares `schema: mastermind.page_evidence_receipt.v1`, lists `templates/am_edition.html.j2` as the changed path, and points at the manifest. `mockups/evidence/am_edition/manifest.json` declares `honesty.authority: "This tool captures screenshots; it scores nothing."` — honest disclosure of scope.

Gate runs (all exit 0):
```
$ git diff 9d2c11c9ab9e dd20710cc4 | python3 scripts/check_ui_visual_evidence.py --diff-file - --repo-root .
EXIT=0

$ python3 scripts/check_design_system.py --mode enforce-added --diff-file /tmp/pr-7337.diff
::notice title=design-system::R0 enforce-added: 0 blocking finding(s) (18973 further pre-existing, non-blocking finding(s) in the estate — run --mode report for the full census)
design-system ratchet — mode=enforce-added blocking=0 (estate pre-existing, non-blocking: 18973)
EXIT=0

$ python3 scripts/check_runtime_style_injection.py
runtime style injection guard OK (195 .js files scanned, 44 injecting, 89 total hits — all within frozen allowances)
EXIT=0
```

Substantive styling via governed tokens: the inline `<style>` block in `templates/am_edition.html.j2` (lines 19-63, ~45 lines) uses exclusively `var(--…)` CSS custom properties — `--bg`, `--panel`, `--line`, `--r-card`, `--r-pill`, `--r-ctl`, `--text`, `--muted`, `--link`, `--ink-link`, `--up`, `--down`, `--popover-shadow`. No raw hex literals, no parallel palette, no token family declared outside `theme.css`. The block is authored as a static template fragment, not as runtime JS-injected text; `check_runtime_style_injection.py` is green. No third-header invented — the page extends the public-shell chrome with one new nav card.

Light art direction is **deliberate, not a token swap** — the template's typography scale, panel border weight, state-badge contrast, and the help-tip popover are sized for the editorial archetype (`panel` cards with `var(--r-card, 10px)` rounded corners, `state-badge` chips for session state, `ctx-chip` for regime/tape chips, `brief-link-panel` for the prior-close reference, `help` tooltips with `var(--popover-shadow)` depth). Both themes are committed in the 8-cell matrix and judged independently.

CSS-delta audit: `git diff --name-only 9d2c11c9ab9e...dd20710cc4 | grep -iE '\.css$|\.scss$'` returned empty — no CSS files touched by this PR. Theme tokens are inherited from the existing shell; the new page extends the public-shell chrome with one nav card and one bespoke editorial template.

Open items / disclosures:
- The evidence matrix's `head` field (`manifest.json:9`) names `7c219107c54fa1b1008068de5a2692f170f770aa`, which is the `fix: close AM Edition round-2 ruling` commit. The PR body's `EVIDENCE` section explicitly verifies: `manifest.json:9 head 7c219107c54fa1b1008068de5a2692f170f770aa equals CODE_HEAD`; `git diff --name-only $CODE_HEAD..HEAD` contains only `mockups/evidence/am_edition/`; `git diff --quiet $CODE_HEAD HEAD -- templates/ scripts/build_am_edition.py` exits `0`. The evidence is content-addressed by SHA-256; any re-capture invalidates the receipt — this is a known characteristic of `mastermind.p0_evidence.v2`, not a TP-0 issue.
- The PR's `design_system.compliant: false` flag on the registry row (`data/product_experience/page_registry.json`) reflects the open design-system migration ratchet; the page is TP-0 evidence-complete, but the broader design-system ratchet still owes this archetype. The page passes `enforce-added` (no NEW debt introduced); the inherited estate's 18,973 findings are pre-existing, non-blocking.

## Validated-claims findings

Laws in force:
- `scripts/check_validated_claims.py` (Macro-side gate; the convention of not using "validated/经验证/已验证/经过验证" to describe platform signals/rank/gate/scoring claims is repo-wide per `CLAUDE.md` §House laws).
- Front-facing: never use "validated / 已验证 / 经验证 / 经过验证" without a backing artifact.

**Verdict: PASS — no new affirmative "validated" claim introduced; gate exits 0.**

Gate run:
```
$ python3 scripts/check_validated_claims.py
EXIT=0
```

Spot-check of all 8 PR-touched user-facing files for `validated|经验证|已验证|经过验证` returned **zero hits**:

| file | hits |
| --- | --- |
| `templates/am_edition.html.j2` | 0 |
| `templates/_public_nav.html.j2` | 0 |
| `site/glossary.html` | 0 |
| `scripts/build_am_edition.py` | 0 |
| `scripts/capture_am_edition_evidence.py` | 0 |
| `tests/test_am_edition_page.py` | 0 |
| `tests/test_am_edition_producer.py` | 0 |
| `tests/test_public_chrome.py` | 0 |

The page is **display-tier copy only** — no signal/rank/gate/score claim originates here. The builder's leading comment block (`scripts/build_am_edition.py:1-9`) states the authority ceiling explicitly:

> Authority ceiling: display_only. No signal, rank, score, gate, sizing, ENTRY_OPEN, Prophet, portfolio or trade authority is originated here — every value is either an owner fact read verbatim from an already-committed deterministic artifact, a deterministic derived comparison (prior close vs last known price), a deterministic calendar fact, or a reference to the EXISTING model-generated prior-close brief (site/master_brief.json), never re-summarised or re-ranked.

The four owner-fact sources are pre-existing owner artifacts (already gauntleted/published upstream):
- `market_state` (regime quad, owned by `engine/regime.py`)
- `neuralweb/market_plane.json` (cross-asset consensus, owned by Neural Web)
- `release_forecast` (calendar, owned by `data/release_forecast/`)
- `master_brief.json` (prior-close brief, already model-generated)

The PR does not assert any platform-claim of pre-registration, gauntlet passage, or "validated" status — it only re-presents already-committed owner facts. UWP-R2 (two-organisms law) is honored implicitly: the page is a presentation layer over an existing organism, not a new scoring organ.

The `manifest.json` `honesty.authority: "This tool captures screenshots; it scores nothing."` is honest scope disclosure, not a validated-claim.

## Overall verdict

**PASS** — all three gates satisfied; packet is lawful under the plain-language / theme-art-direction / validated-claims stack.

| gate | result | evidence |
| --- | --- | --- |
| plain-language | PASS | in-tree gate `test_am_edition_page.py::test_page_contains_no_english_only_payload_values_in_zh_mode` **strengthened** by this PR to cover both with-`_zh` and without-`_zh` fixtures; 41 tests passed in 1.96s; every visible string in `templates/am_edition.html.j2` routes through the `t(en, zh)` paired-span macro |
| theme (TP-0 + design-system + runtime-injection) | PASS | 8 PNGs = dark × light × EN/ZH × 1440/390 matrix in `mockups/evidence/am_edition/`; `EVIDENCE.yml` + `manifest.json` (v2 schema) committed; all three gates (`check_ui_visual_evidence.py`, `check_design_system.py --mode enforce-added`, `check_runtime_style_injection.py`) exit 0 |
| validated-claims | PASS | zero hits of `validated|经验证|已验证|经过验证` in any PR-touched user-facing file; `check_validated_claims.py` exits 0; builder explicitly declares `display_only` authority ceiling and refuses to originate any signal/rank/gate/score |

Notes for the commissioning seat:
- The in-tree plain-language gate (`test_page_contains_no_english_only_payload_values_in_zh_mode`) is now stronger than it was before this PR — both fixtures are covered (with and without `_zh` fields), and the four forbidden tokens are the ones an automated ZH-mode render would actually surface if a payload leaked. This is a net improvement, not just a non-regression.
- The page is `design_system.compliant: false` on the registry row — that's the ratchet's own tracking of an open design-system migration for the editorial archetype, NOT a TP-0 gap. The 8-cell evidence matrix is TP-0 complete; the broader design-system ratchet (component-level compliance) still owes this archetype. `enforce-added` mode is green: zero NEW debt introduced.
- The build-side script `scripts/build_am_edition.py` does **not** write a `site/am_edition.html` file (the builder derives the page on every render). The registry note is honest about this: `"no committed site/am_edition.html; builder derives on every render"`. This is consistent with the public-shell re-bake pattern (`scripts/build_aibrief.py`, etc.).
- `tests/test_public_chrome.py::test_shared_public_nav_matches_landing_core_information_architecture` was patched in round h5 to add `"am_edition.html"` to the `shared_only` set with a dated comment. The h4 round's failure was correctly classified by the seat as outside the two named reds and left unpatched per the round-3 ruling; the h5 patch closes it. The PR carries a clean `shared_hrefs <= landing_hrefs | {"stocks/earnings/index.html", "glossary.html", "am_edition.html"}` invariant.

## Audit commands and inputs

- Plain-language: `cd /Users/chriswong/lanes/tmp/audit-pr-7337 && python3 -m pytest tests/test_am_edition_page.py tests/test_am_edition_producer.py tests/test_public_chrome.py -q -p no:cacheprovider` (41 passed in 1.96s).
- Theme: `git diff 9d2c11c9ab9e dd20710cc4 | python3 scripts/check_ui_visual_evidence.py --diff-file - --repo-root .` (exit 0); `python3 scripts/check_design_system.py --mode enforce-added --diff-file /tmp/pr-7337.diff` (exit 0, 0 blocking on added lines); `python3 scripts/check_runtime_style_injection.py` (exit 0). Manifest + EVIDENCE.yml parsed from `mockups/evidence/am_edition/`.
- Validated-claims: `python3 scripts/check_validated_claims.py` (exit 0); `grep -in 'validated\|验证\|经验证\|已验证\|经过验证'` over the 8 PR-touched files returned zero hits.
- PR metadata: `gh pr view 7337 --repo mastermindx-market-intelligence/macro --json number,title,body,mergedAt,mergeCommit,headRefName,baseRefName,files`.
- Worktree: `git worktree add /Users/chriswong/lanes/tmp/audit-pr-7337 38adeb1e7065cb3aa52a1f8453ca0b3944327789 --detach` (full worktree, NOT sparse — the design-system and runtime-style gates need the full estate to compute the pre-existing pile).
- Diff base: `git merge-base 808cba3a8d dd20710cc4` returned `9d2c11c9ab9e77abbef5b5000e9a7711af3c9e6b` (the actual fork base — `808cba3a8d` was the cataloging commit immediately before the merge and is NOT main's pre-merge tip).

SESSION END: PROVEN_OUTCOME — single merged PR audited; three gates returned concrete verdicts (plain-language PASS / theme PASS / validated-claims PASS); report written to `orch/audits/mastermindx-market-intelligence_pr7337.mm.md`; no durable state outside the audit file.
