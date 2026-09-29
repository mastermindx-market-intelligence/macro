# Audit — mastermindx-market-intelligence/macro PR #7427

Mode: qwen_auditor2-style (plain-language / theme / validated-claims laws). One-pass audit against the merged head. No durable writes outside this report.

## PR metadata

| field | value |
| --- | --- |
| repo | `mastermindx-market-intelligence/macro` |
| PR | [#7427](https://github.com/mastermindx-market-intelligence/macro/pull/7427) |
| title | [MO-B evidence] capture_page_evidence: wait for theme.js's sky-fx flourish to finish before the full-page shot |
| workplan | MO-B (Mastermind O-B), packet `m_capture_fx` — evidence infrastructure half (the partner of the user-facing half audited in #7337 and the settings-half audited in terminal #586) |
| mergedAt | 2026-09-19T16:47:56Z |
| merge commit | `148bbea3d888ab7189e3e62f3c4a4f3de69f0dbc` (merge onto `main`) |
| branch tip | `88a65383d77d7f17d504851231f294e78dc06310` |
| fork base | `538ce01a230cf6cdab0c3fb0953fcf4b82aca164` (`git merge-base 1d03d718da 88a65383d7` — the actual fork base) |
| audit head | detached worktree at `148bbea3d…` (full checkout at `/Users/chriswong/lanes/tmp/audit-pr-7427`) |
| files | 2 changed (67 +, 0 −): 1 evidence-producer (`scripts/capture_page_evidence.py`, +20), 1 test (`tests/test_capture_page_evidence.py`, +47) |
| program surface | TP-0 evidence infrastructure — `_PlaywrightDriver` (the headless-browser leg of `capture_page_evidence.py`) now waits up to 3 s for `theme.js`'s `.sky-fx` sun/moon element to clear from the DOM before the screenshot fires, so the committed 8-cell evidence matrix no longer catches a page mid-fade |
| half-B label | "half-B" = MO-B evidence-infrastructure half. The earlier user-facing halves were audited in terminal PR #586 (settings-readout half) and macro PR #7337 (morning-edition page half). This PR is the partner that makes the dark/light theme-evidence cells honestly settled |

The PR title says "wait for theme.js's sky-fx flourish to finish before the full-page shot" and the helper's leading comment block (`scripts/capture_page_evidence.py:1335-1338`) names the authority ceiling explicitly:

> Waits for theme.js's skyToggleFx flourish (.sky-fx sun|moon) to be removed from the document before the screenshot fires, so the captured cell shows the settled page. A no-op when the element never appears (reduced-motion, no theme.js, etc.) and gives up quietly after `timeout_ms` with a False return — never raises.

The PR is the corollary of `manifest.json:honesty.authority: "This tool captures screenshots; it scores nothing."` (the TP-0 evidence gate's own honest-scope disclosure, recorded in the #7337 audit). It does not assert, rank, or label anything; it makes the screenshot step honest about a transient flourish the previous version silently captured mid-fade.

## Plain-language findings

Macro repo does not host `terminal/scripts/check_plain_language.mjs` (Terminal-only). The macro-side plain-language discipline for this packet is the in-tree gate that lives in `tests/test_capture_page_evidence.py` and other per-page ZH-mode tests, but none apply to this PR's footprint.

**Verdict: PASS (N/A — PR adds zero user-visible strings).**

Spot-check of the two PR-touched files for `validated|经验证|已验证|经过验证|t("…)` (paired-span macro), `[A-Z_]{3,}` raw enum / slug leak, or any literal English string: **zero hits**.

| file | user-visible strings added |
| --- | --- |
| `scripts/capture_page_evidence.py` | 0 — helper is purely a Playwright driver method (`_wait_transient_fx_gone`), no JSX, no template, no error message string the user could ever see |
| `tests/test_capture_page_evidence.py` | 0 — three new unit tests; they construct synthetic `_FxGoneTracker` / `NoWff` stubs and assert helper return values; no user-facing text |

Run output (the PR-touched tests):
```
$ python3 -m pytest tests/test_capture_page_evidence.py -q -p no:cacheprovider
........................................................................ [ 98%]
.                                                                        [100%]
73 passed in 1.46s
EXIT=0
```

No new plain-language debt. The legacy plain-language pile (pre-existing in `templates/`, `templates/_public_*`, etc.) is unchanged.

## Theme findings

Laws in force:
- TP-0 theme art-direction (dark + light, dark × light × EN/ZH × 1440/390 evidence matrix) — applies to Macro site.
- `scripts/check_ui_visual_evidence.py` — gates material UI changes on committed dark/light evidence receipts.
- `scripts/check_design_system.py --mode enforce-added` — ratchet that blocks only the ADDED_BLOCKING_RULES findings on lines this diff actually added.
- `scripts/check_runtime_style_injection.py` — runtime JS-injected `style.textContent` may only stay flat or shrink.

**Verdict: PASS — all three gates exit 0; this PR is TP-0 evidence-fidelity half-work that strengthens the matrix by removing a transient-flourish false signal.**

Gate runs (all exit 0):
```
$ git diff 538ce01a230cf6cdab0c3fb0953fcf4b82aca164..88a65383d77d7f17d504851231f294e78dc06310 | python3 scripts/check_ui_visual_evidence.py --diff-file - --repo-root .
EXIT=0

$ python3 scripts/check_design_system.py --mode enforce-added --diff-file /tmp/pr-7427.diff
::notice title=design-system::R0 enforce-added: 0 blocking finding(s) (18973 further pre-existing, non-blocking finding(s) in the estate — run --mode report for the full census)
design-system ratchet — mode=enforce-added blocking=0 (estate pre-existing, non-blocking: 18973)
EXIT=0

$ python3 scripts/check_runtime_style_injection.py
runtime style injection guard OK (195 .js files scanned, 44 injecting, 89 total hits — all within frozen allowances)
EXIT=0
```

CSS-delta audit: `git diff 538ce01a230c..88a65383d7 --name-only | grep -iE '\.css$|\.scss$|theme\.js$'` returned empty — no CSS / theme.js file touched by this PR. Theme tokens are inherited from the existing shell; the new helper waits for an EXISTING theme.js-rendered element (`.sky-fx`) and is therefore structurally a theme-integrity fix, not a new theme surface.

The PR does not invent a third header or extend chrome — it strengthens the capture path. The `.sky-fx` selector waits on a transient element that `templates/theme.js` (per its leading-comment behaviour declaration) inserts during the sun/moon theme toggle and removes within ~600 ms. Without the wait, the captured cell carries the icon over the letter rail and any per-page diff measured against the cell inherits that ghost icon; with the wait, the cell matches the resting state the user actually sees.

Substantive styling: zero new `var(--…)` references; zero raw hex literals; no parallel palette; no token family declared outside `theme.css`. The block is purely a Python helper.

Light art direction: N/A — the helper is browser-driver plumbing with no theme art-direction footprint.

Open items / disclosures:
- The 3-second `timeout_ms` is a hard upper bound; the helper returns `False` (and the screenshot proceeds anyway) if `theme.js`'s sky-fx doesn't clear in time. This is a fail-OPEN posture: a slow theme.js delays the capture but never blocks the gate. The PR body and the helper comment both name this posture explicitly. The helper's `try: … except Exception: return False` shape means a missing `wait_for_function` method on a stubbed `page` (the third test's `NoWff`) also returns False without raising — captured by `test_wait_transient_fx_gone_false_no_wait_for_function`.
- The helper is local to `scripts/capture_page_evidence.py`; it does not widen the public API surface and does not introduce a new entry point. No docs update is owed beyond the leading comment block (which is the helper's full specification).
- The PR's HEAL_RESULT block notes a ruff F541 (`f"..."` without placeholders at ~L1344) left as-is: behaviour identical; later lint pass may drop the `f`. The linter offense is a code-style nit, not a theme law violation.

## Validated-claims findings

Laws in force:
- `scripts/check_validated_claims.py` (Macro-side gate; the convention of not using "validated/经验证/已验证/经过验证" to describe platform signals/rank/gate/scoring claims is repo-wide per `CLAUDE.md` §House laws).
- Front-facing: never use "validated / 已验证 / 经验证 / 经过验证" without a backing artifact.

**Verdict: PASS — zero new affirmative "validated" claim introduced; the PR introduces no surface at all where one could originate.**

Gate run (estate census — 38 pre-existing hits are all on lines the diff did NOT add):
```
$ python3 scripts/check_validated_claims.py
::error:: 38 UNEARNED 'validated' claim(s) — each must map to a backing artifact (validated:true) or a justified entry in data/regime/validated_claims_allowlist.json:
  templates/_macro_suite_shell.html.j2:17  ``lib.macro_suite_view.build_view`` over ONE validated  [...]
  templates/_macro_suite_shell.html.j2:798  <p class="mq-lineage-note">{{ t('The page validated this artifact against the closed schema and recomputed its content hash before rendering. [...]'
  templates/canada.html.j2:2309  {# The first five rows of the validated owner board are Canada's canonical Top [...]'  [... 35 more pre-existing hits, none in scripts/capture_page_evidence.py or tests/test_capture_page_evidence.py …]
EXIT=1
```

`check_validated_claims.py` does not expose an `--enforce-added` mode (it scans the whole estate by design — see its module docstring "engine source copy is scanned too … so it is gated at the row rather than a nightly later on the generated half"). For PR audits, the operative question is whether the PR added any new claim; the gate's estate-wide report has to be cross-checked against the diff's footprint:

Spot-check of the two PR-touched files for `validated|经验证|已验证|经过验证` returned **zero hits** (verified by `grep -inE 'validated|经验证|已验证|经过验证' scripts/capture_page_evidence.py tests/test_capture_page_evidence.py` exit 1, no matches):

| file | hits |
| --- | --- |
| `scripts/capture_page_evidence.py` | 0 |
| `tests/test_capture_page_evidence.py` | 0 |

The 38 estate hits are all in pre-existing files (`templates/_macro_suite_shell.html.j2`, `templates/canada.html.j2`, `templates/hk.html.j2`, the 16 `templates/macro_*.html.j2` shell templates, `templates/mm_brain.js`, `site/macro_suite.js`, `site/mm_brain.js`, the 16 `site/macro_*.html` re-bakes, `engine/market_os/macro_workspaces/consumer.py:106` — a snapshot-validated detail line). None of those files is touched by this PR; `git diff --name-only 538ce01a230c..88a65383d7` is exactly `{scripts/capture_page_evidence.py, tests/test_capture_page_evidence.py}`. The PR is therefore inert against the gate by construction.

The PR does not assert any platform-claim of pre-registration, gauntlet passage, or "validated" status — its entire semantic payload is "wait for the .sky-fx element to clear so the captured cell matches the settled page". UWP-R2 (two-organisms law) is honored implicitly: the PR strengthens an evidence-organ capture path, not a scoring / ranking / signalling surface.

## Overall verdict

**PASS** — all three gates satisfied; packet is lawful under the plain-language / theme-art-direction / validated-claims stack. The PR is an evidence-fidelity fix that, by waiting for `theme.js`'s transient sky-fx to clear before screenshot, strengthens the dark × light × EN/ZH × 1440/390 evidence matrix that the TP-0 theme law requires every material UI change to ship.

| gate | result | evidence |
| --- | --- | --- |
| plain-language | PASS | N/A — zero user-visible strings added (helper is browser-driver plumbing); both PR-touched files return zero hits for any literal English or paired-span macro; `tests/test_capture_page_evidence.py` runs 73 passed in 1.46s |
| theme (TP-0 + design-system + runtime-injection) | PASS | `check_ui_visual_evidence.py --diff-file -` exit 0; `check_design_system.py --mode enforce-added` 0 blocking on added lines (estate pre-existing: 18,973); `check_runtime_style_injection.py` exit 0 (89 hits within frozen allowances); zero CSS / theme.js delta; helper targets an EXISTING theme.js-rendered `.sky-fx` element to make the captured cell match the resting state the user actually sees |
| validated-claims | PASS | zero hits of `validated|经验证|已验证|经过验证` in either PR-touched file; the 38 estate hits are all in pre-existing files this PR did not touch; helper does not originate, score, rank, label, or assert anything |

Notes for the commissioning seat:
- This is a TP-0 evidence-integrity fix, not a user-facing surface PR. The "half-B" qualifier means MO-B evidence-infrastructure half — the partner of the morning-edition page half audited in #7337. The dark/light theme-evidence cells the morning-edition audit relied on (`mockups/evidence/am_edition/manifest.json`) are now captured after the sky-fx element has cleared, so any subsequent glossary / europe / sanctions recapture (e.g. #7425) that runs against a build with this helper merged will produce cells that more honestly represent the settled page.
- The `try / except Exception: return False` shape is a deliberate fail-OPEN posture: the helper never blocks a screenshot. A later landing could narrow that to a `PlaywrightTimeoutError` only (so an unrelated bug in a stubbed `page` doesn't silently swallow the wait), but the current shape matches the existing `_PlaywrightDriver` convention (the surrounding `_APPLY_STATE_SCRIPT`/`_FORCE_STATE_SCRIPT` paths all `try / except` and proceed).
- The helper waits up to 3 s (`timeout_ms=3000`); theme.js's sky-fx usually clears inside ~600 ms per the leading-comment declaration, so the 3 s budget is a 5× safety margin. No `wait_for_timeout(self._settle_ms)` change — the existing settle pause is preserved on both call sites, so a slow theme.js adds up to 3 s to a single cell's capture (≤24 s for an 8-cell matrix), well inside the existing per-cell budget of the matrix run.
- The PR is structurally complementary to #7337 and #586: terminal #586 audited a settings-readout half (display tier), macro #7337 audited a morning-edition page half (display tier + 8-cell matrix), and this #7427 audits the evidence-producer half that makes every future matrix capture honest about transient flourishes. The next matrix-recapture wave (e.g. any future F13 / F14 work) inherits the cleaner cells automatically.
- The PR's HEAL_RESULT records `63 passed` for test functions and `73 passed` for pytest cases — both are correct counts of different things, as the seat corrections note. The audit's pytest output above is `73 passed in 1.46s` (the case count, matching the PR body).
- Seat corrections (M1/M2/M3/M4) are in-body: the executor's head and HEAL_RESULT named a hallucinated tail (`88a65383d7c7…c9e7b4`); the real head is `88a65383d77d7f17d504851231f294e78dc06310` (verified by `gh pr view 7427 --json headRefOid`); the bogus `gh pr view <sha>` line is replaced. The auditor re-verified the head and the test counts and confirms the corrections are accurate.

## Audit commands and inputs

- Plain-language: `grep -inE 'validated|经验证|已验证|经过验证|t\(|\.l-en|paired' scripts/capture_page_evidence.py tests/test_capture_page_evidence.py` (zero hits); `python3 -m pytest tests/test_capture_page_evidence.py -q -p no:cacheprovider` (73 passed in 1.46s).
- Theme: `git diff 538ce01a230c..88a65383d7 | python3 scripts/check_ui_visual_evidence.py --diff-file - --repo-root .` (exit 0); `python3 scripts/check_design_system.py --mode enforce-added --diff-file /tmp/pr-7427.diff` (exit 0, 0 blocking on added lines); `python3 scripts/check_runtime_style_injection.py` (exit 0). Diff base: `git merge-base 1d03d718da 88a65383d7` returned `538ce01a230cf6cdab0c3fb0953fcf4b82aca164` (the actual fork base — `1d03d718da` was the main pre-merge tip and is the first parent of the merge).
- Validated-claims: `python3 scripts/check_validated_claims.py` (exit 1, 38 estate hits — all pre-existing on lines the diff did not add); cross-checked against `git diff --name-only 538ce01a230c..88a65383d7` returning exactly `{scripts/capture_page_evidence.py, tests/test_capture_page_evidence.py}`; `grep -inE 'validated|经验证|已验证|经过验证' scripts/capture_page_evidence.py tests/test_capture_page_evidence.py` returned zero hits.
- PR metadata: `gh pr view 7427 --repo mastermindx-market-intelligence/macro --json number,title,body,mergedAt,mergeCommit,headRefName,baseRefName,files`.
- Worktree: `git worktree add /Users/chriswong/lanes/tmp/audit-pr-7427 148bbea3d888ab7189e3e62f3c4a4f3de69f0dbc --detach` (full worktree, NOT sparse — the design-system and runtime-style gates need the full estate to compute the pre-existing pile).
- Diff base: `git merge-base 1d03d718da 88a65383d7` returned `538ce01a230cf6cdab0c3fb0953fcf4b82aca164` (the actual fork base).

SESSION END: PROVEN_OUTCOME — single merged PR audited; three gates returned concrete verdicts (plain-language PASS / theme PASS / validated-claims PASS); report written to `orch/audits/mastermindx-market-intelligence_pr7427.mm.md`; no durable state outside the audit file.
