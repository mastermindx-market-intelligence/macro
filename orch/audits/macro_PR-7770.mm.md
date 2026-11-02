# PR audit — mastermindx-market-intelligence/macro#7770

**Auditor:** meta-ceo-b-2026-09-08 (one-pass remote useful-idle, no retries, no scope expansion)
**Audit timestamp:** 2026-09-23
**Repo / PR:** mastermindx-market-intelligence/macro #7770
**PR title:** [MO-A3] A-F03-W2-4b: Skew ledger backfill leg — recompute the covered legacy history from the ThetaData store (canonical-wins), exclude weekend as-of rows from emit, DEC record
**Merged at:** 2026-09-23T07:42:47Z (within the 24 h audit window)
**Head sha (body-disclosed, post seat-ratification #3 merge):** `5db16fb334fdc76fdccd45352e64e20aae27e66e` (Meta-CEO A seat ratification; merge commit of `claude/mo-a-3-a-f03-w2-4b-skew-backfill` into main)
**Author:** chriswong6031-creator (Meta-CEO A seat)
**Repo root verified:** `/Volumes/STORAGE/Offloaded/m1-20260917/lanes/repos/macro` on this session's working tree; sparse-checkout at 75%, `git ls-files orch/audits/` confirms index is current with `origin/claude/orch-audit-pr97154-20260920`; merge confirmed in `origin/main` log via `git log --all --oneline | grep "#7770"` → `d857f4568a [MO-A3] A-F03-W2-4b: ... (#7770)`.

> **Scope note (§1):** the chronologically most-recent merges inside the 24 h window are #7768 (admin publisher records), #7771 (UK policy desk), #7770 (skew ledger backfill), #7764 (markets.css cachebust), #7763 (Payoff lab consumer), #7761 (markets mobile cycle-stage), #7760 (ci gate), #7759 (payoff lab producer), #7758 (sector-intel publish), #7756 (skew parity audit), #7755 (retire Intelligence Hub entry), #7752 (skew lane docs), #7751 (B4 prereg), and the orch(audit) ledger entries #7748/#7746/#7745/#7744/#7743/#7741/#7740/#7737/#7736/#7735/#7733/#7732/#7730. Among the **half-B** substantive payloads in that window, #7763 and #7770 are the only two (`MO-A` rebrand; the W2-5a payload at #7759 is half-A, not half-B; #7756 is the W2-4 parity audit read-only leg, no half-A/B suffix). #7763 is already audited on this branch (commit `21f6c269a7`, blob `a4f14057c5f8614ad604889437d6004f8d6e4116`); #7770 has not been audited on this branch — its `orch(audit)` record on `origin/main` (commit `861888a045`) is from a sibling branch and is not present in this checkout's working tree (the `git ls-files orch/audits/ | grep PR-7770` returns empty). The seat selects #7770.

---

## 1. PR metadata

| field | value |
|---|---|
| repo | mastermindx-market-intelligence/macro |
| number | 7770 |
| title | [MO-A3] A-F03-W2-4b: Skew ledger backfill leg — recompute the covered legacy history from the ThetaData store (canonical-wins), exclude weekend as-of rows from emit, DEC record |
| merged_at | 2026-09-23T07:42:47Z |
| head (post seat-ratification #3) | `5db16fb334fdc76fdccd45352e64e20aae27e66e` (merge of `2499d627` + `fcaabf58` — main's overnight marketing-publish + research_vault + press-wire commits; the `.github/ci/legacy-jobs.yml` resolver-by-union was a seat act, not a code change) |
| base | `main` (Meta-CEO A seat merged `origin/main` keeping W2-4 parity + W2-5a payoff-lab gating + W2-4b backfill suite; YAML parses; `run_ci_pack.py --validate-only` clean; no engine/builder/test bytes changed after `2499d627`) |
| branch | `claude/mo-a-3-a-f03-w2-4b-skew-backfill` |
| changed files | 6 (per `gh pr view 7770 --json files --jq '.files\|length'` = 6) |
| additions / deletions | 606 / 26 (per `gh pr view --json additions,deletions`); 0 / 0 on `engine/options_skew.py` deletions (`git diff origin/main...HEAD -- engine/options_skew.py \| grep -c '^-[^-]'` = 0 — the weekend filter is an insertion inside `emit_from_ledger`, no line of the engine was deleted against `origin/main`); 0 / 0 on `data/`/`site/`/`templates/`/`mockups/`/`ops/`/`scripts/publish_r2.py`/`scripts/fetch_r2.py` (`git diff --stat origin/main...HEAD -- data site templates mockups ops scripts/publish_r2.py scripts/fetch_r2.py` = empty) |
| files of interest | `engine/options_skew.py` (+150 / −0 — module docstring backfill paragraph, `_is_weekend_iso`, `_chain_asof_dates`, `_backfill_row_counts`, `backfill_from_store`, `emit_from_ledger` weekend filter + `n_weekend_rows_excluded` + `history_sources` fields); `scripts/build_options_skew.py` (+96 / −23 — `_parse`/`_selected`/`_inclusive_iso_dates`/`_parse_roots`/`_pin_ledger` helpers, `--backfill FROM TO` + `--dry-run` + `--roots` + `--ledger` argparse, two new ZH bilingual error messages); `tests/test_options_skew_backfill.py` (+251 / −0 — 8 hermetic tests: idempotence proof, weekday+weekend+uncovered replacement, dry-run counts, weekend-only ledger still emits Sunday, source-column parsing, rr25 skew unchanged, parity audit still passes, named tests Pinned 67 — see `test_options_skew_backfill.py` head +4); `.github/ci/legacy-jobs.yml` (+5 / −2 — `tests/test_options_skew_backfill.py` added to the existing `skew-accrual-lane` `gate: code` exclusive job's `paths:` list and pytest run line, no waiver row added); `agentos/decisions/DEC-SKEW-PARITY-RULING-BACKFILL-COVERED-HISTORY.md` (+70 / −0 — Question / Answer / Rationale / Alternatives / Evidence / Affects / Confidence / Reversibility — the DEC record this packet owns); `research/MARKET_ONTOLOGY_F03_SKEW_ACCRUAL_LANE_2026-09-22.md` (+34 / −1 — install-runbook §3.7 "One-time backfill (seat act)": hydrate from R2 → `--backfill 2026-06-21 2026-08-13` against the ThetaData store → publish ledger → copy the printed JSON receipt into the state dir) |
| labels | `merge-on-green` |
| scope collision | none — body declares zero collision with `engine/*` outside `options_skew.py`, the Options workspace template, the W2-5a producer (#7759), the W2-5b consumer (#7763), the shared `theme.js`, the daily Options scope template, or any user-facing tooltip plane |

**Nature of change (skew-lane half-B backfill — engine ledger reconciliation against the ThetaData store, no user-facing surface):** the PR has three intertwined deliverables, all of which the body declares together:

1. **Engine backfill leg.** `engine/options_skew.py::backfill_from_store(dates, *, store=None, roots=None, dry_run=False)` recomputes an explicit list of ISO dates from the ThetaData store and upserts them into the canonical-wins ledger (the same `snapshot()` rules that accrue uses today). Weekend dates are counted and skipped. Dates the store does not cover are counted and skipped — neither case is filled from a neighbouring session. `_backfill_row_counts` is a dry-run pure function: counts `rows_replaced` / `rows_added` / `rows_unchanged` against the ledger as it sits, never writes. The receipt shape is one dict: `{dates_requested, dates_weekend_skipped, dates_not_in_store, dates_backfilled, rows_replaced, rows_added, rows_unchanged, per_date:[{date,status,state?,skew?,source?}, ...]}` — the **same keys** the `--emit` payload now carries.
2. **Engine `emit_from_ledger` weekend filter.** `engine/options_skew.py::emit_from_ledger` drops weekend-dated rows before it picks the latest per-name snapshot **when a weekday row remains**, and adds two new payload keys: `n_weekend_rows_excluded` (int) and `history_sources` (sorted unique list of source values, e.g. `["polygon_gex","thetadata"]`). A ledger whose every row is a weekend date still emits that latest row (the existing fixture uses Saturday 2026-06-20 + Sunday 2026-06-21 and expects the Sunday row); the exclusion count is 0 in that case because nothing was removed. **`compute_skew`, `_nearest_expiry`, `_iv_at_delta`, `skew_map`, `snapshot` (including canonical-wins), and `_atomic_write_parquet` are byte-unchanged against `origin/main`** — body declares this with the receipt `git diff origin/main...2499d627 -- engine/options_skew.py | grep -c '^-[^-]'` = 0.
3. **CLI leg.** `scripts/build_options_skew.py` gains `--backfill FROM TO` (nargs=2, metavar), `--dry-run`, `--roots`, `--ledger PATH`. Bare argv still runs accrue+emit (the existing default for today's callers). `--backfill` alone prints one JSON line and exits 0. `--accrue` + `--backfill` accrues AND backfills. An unresolved store prints the existing `::warning title=options-skew-source::` line (not raised), and exits 0. The two new error messages are bilingual EN/ZH operator-facing strings (`_inclusive_iso_dates` raises `ValueError`).

**Body signals — already-run gates (PR-quoted, NOT re-run in this audit per one-pass constraint):**
- `python -m pytest tests/test_options_skew_backfill.py tests/test_options_skew.py -q -p no:cacheprovider` → **24 passed in 2.98s**.
- `PATH="/Users/chriswong/lanes/venv/bin:$PATH" python -m pytest tests/test_options_skew_backfill.py tests/test_options_skew.py tests/test_audit_options_skew_overlap.py tests/test_skew_accrual_launchd.py -q -p no:cacheprovider` → **67 passed in 13.95s** (the venv-prefixed run resolves the runner's `/usr/bin/python3` lacking pandas).
- `python -m pytest tests/test_ci_pack.py -k curated_exclusive -q -p no:cacheprovider` → **2 passed, 119 deselected in 207.78s**.
- `/Users/chriswong/lanes/venv/bin/python3 scripts/check_contract_delta.py --base origin/main` → **0 introduced, 1 inherited** (the inherited line is `tests/test_render_dead_ref_targets.py`, already unwired on the base — pre-existing, not introduced).
- `python3 scripts/agentos.py validate` → **0 errors, 90 warnings** (1206 records: 69 workstreams, 340 decisions, 302 discoveries, 495 handoffs; the warnings are pre-existing phantom paths and overdue reviews, none naming this DEC).
- `git diff origin/main...HEAD -- engine/options_skew.py | grep -c '^-[^-]'` → **0** (the engine has zero deletions against `origin/main`; the weekend filter is an insertion inside `emit_from_ledger`; the other hunks are the module docstring and `backfill_from_store` after `load_history`).
- `git diff --stat origin/main...HEAD -- data site templates mockups ops scripts/publish_r2.py scripts/fetch_r2.py` → **empty** (zero user-visible bytes).
- On one fixture ledger, the emit payload gained `history_sources` and `n_weekend_rows_excluded` and lost no key that `origin/main` already returned.
- `git diff --check`: PASS.
- GitHub checks are NOT claimed green in the PR body; the body quotes only the local commands above.

**Scope boundary (body-disclosed):** the PR is bounded to `engine/options_skew.py` (backfill + helper functions) + `scripts/build_options_skew.py` (CLI plumbing) + `tests/test_options_skew_backfill.py` (hermetic tests) + `.github/ci/legacy-jobs.yml` (one `gate: code` job's `paths:` + pytest line) + the DEC record + the runbook §3.7. Does **not** touch `templates/`, `site/`, `mockups/`, `data/`/`ops/`/`scripts/publish_r2.py`/`scripts/fetch_r2.py`, the shared `theme.js`, the Options page template, the producer (`scripts/build_options_payoff_lab`), or any user-facing tooltip plane.

**Cross-reference (body-disclosed, not re-run):** the DEC's `answer:` paragraph says **"Ship one plain-language sentence about the source break on the options page in W2-5b"** — i.e., the user-facing plain-language sentence this packet's ruling implies is **deferred to W2-5b** (#7763, MERGED 2026-09-23T08:46:03Z, already audited on this branch at commit `21f6c269a7`). The follow-on PR for that sentence is the W2-4c payload `b5adca3c70` (already in git log: `[MO-A3] A-F03-W2-4c: skew source-break — source windows on site/options_skew/latest.json and one plain-language sentence on the Directional read`); that PR is where the user-facing string lands and where any Tier-1/Tier-2 plain-language check would apply. **#7770 itself ships no user-facing string.**

---

## 2. Plain-language findings

**Source for plain-language law:** the macro repo does not ship a standalone `check_plain_language.mjs` (that check is terminal-repo-only); the macro equivalent is the **visible-string audit** mandated by `CLAUDE.md` §"Design (user-first law)" — `docs/DESIGN_DOCTRINE.md` + the `frontend-design` skill — read against the Tier-1 obligations (state + plain-word stance under hard word budgets, no internal state names, no untranslated stats, no raw slugs, bilingual EN/ZH parity on every visible string, plain-word null disclosure) and the Tier-2 obligations (Tier-2 receipts for nulls, no falsifier vocabulary front-facing, plain-word cadence call-outs).

**Scope check — does this PR carry plain-language surface?** **No.** `git diff origin/main...7770 -- engine/options_skew.py scripts/build_options_skew.py tests/test_options_skew_backfill.py` contains zero user-facing copy. The diff is bounded to:
  - engine code (Python: docstring paragraph + 5 helper functions; none of which print user-facing strings — `_is_weekend_iso`, `_chain_asof_dates`, `_backfill_row_counts`, `backfill_from_store`, `emit_from_ledger`),
  - CLI argparse `help=` strings (operator-facing only — `--backfill`, `--dry-run`, `--roots`, `--ledger`; bilingual EN + ZH; e.g. `"recompute this inclusive date range from the ThetaData store"`),
  - Python `ValueError` error messages (`_inclusive_iso_dates` raises `ValueError` with bilingual EN + ZH pair; the EN first, ZH second, e.g. `"The backfill dates must be real calendar dates written as YYYY-MM-DD. 回补日期必须写成 YYYY-MM-DD 形式的真实日期。"`),
  - the DEC record (governance — internal `agentos/decisions/`, never user-facing),
  - the runbook §3.7 (operator-facing — install runbook for the seat, never user-facing).

**Plain-language walkthrough — the two new operator-facing bilingual strings:**

| source | string (EN/ZH side-by-side) | audience | plain-language read |
|---|---|---|---|
| `scripts/build_options_skew.py::_inclusive_iso_dates` (ValueError) | `"The backfill dates must be real calendar dates written as YYYY-MM-DD. 回补日期必须写成 YYYY-MM-DD 形式的真实日期。"` | CLI operator | plain bilingual operator error: EN names the format (`YYYY-MM-DD`), ZH mirrors with `YYYY-MM-DD` written inside the sentence so the format string is unmistakable; no internal state name, no falsifier vocabulary (`未经验证` / `非…验证` not present — this is an error, not a claim); bilingual parity on every visible-string position (EN first, ZH second; same idea, both readable in plain Mandarin without resorting to `https://` / technical slug). ✓ |
| `scripts/build_options_skew.py::_inclusive_iso_dates` (ValueError, order) | `"The backfill start date must be on or before the end date. 回补的开始日期必须不晚于结束日期。"` | CLI operator | plain bilingual operator error: EN names the rule in one clause ("on or before"), ZH uses the canonical Mandarin comparative `不晚于` ("not later than"); no acronym, no jargon (`>=` / `<=` symbols would have been operator-confusing in a Mac terminal paste); bilingual parity. ✓ |

**Plain-language sub-finding 1 — no `templates/`, no `site/`, no `engine/*display-copy field that feeds a user template`, zero Tier-1 surface.** The PR is engine + CLI + tests + CI + DEC + runbook. The Tier-1 plain-language law does not bind because the engine fields added in `emit_from_ledger` (`n_weekend_rows_excluded`, `history_sources`) are pure Python ints / sorted unique source tags that **no template or site file currently reads** — `git grep -nE 'history_sources\|n_weekend_rows_excluded' templates/ site/` returns 0 hits. The follow-on PR for the user-facing wiring is `b5adca3c70` (W2-4c — already merged into the day's feature at the time of this audit).

**Plain-language sub-finding 2 — DEC record `answer:` explicitly defers the user-facing plain-language sentence.** The DEC record's `answer:` paragraph says: *"Ship one plain-language sentence about the source break on the options page in W2-5b."* This is a binding inter-packet contract — the W2-5b packet (#7763, audited `21f6c269a7`) is downstream of #7770 and is the home for that sentence. **#7770 itself does NOT ship the sentence**; the sentence is the W2-5b/W2-4c follow-on. The plain-language law is therefore not engaged on this head.

**Plain-language sub-finding 3 — falsifier / refutation language front-facing check: N/A (no user-facing copy).** Per `DESIGN_DOCTRINE.md` §"Falsifier/refutation language is never front-facing (operator 2026-07-27, #3821)" — no template or site file is touched, so the rule does not bind.

**Plain-language sub-finding 4 — instrument-verdict vs market-verdict (operator 2026-08-09).** No instrument verdict (`peak`, `restriction`, `falsifier fired`) is introduced. The DEC record's `confidence: high` is internal governance, never user-facing.

**Plain-language sub-finding 5 — bilingual parity.** The two new operator-facing strings are bilingual EN+ZH; the CLI `help=` strings are English-only (operator CLI), no EN/ZH parity obligation on argparse `help=` (those are operator-tool strings, not user surface).

**Plain-language verdict:** **PASS by structural absence.** No user-facing copy is introduced; the two operator-facing bilingual EN/ZH error strings are well-formed, financial-vocabulary-correct (no acronyms, no jargon, no internal state names, no falsifier vocabulary), and the inter-packet plain-language sentence is correctly deferred to W2-5b (#7763, merged + audited on this branch).

---

## 3. Theme findings (TP-0 dual art direction)

**Source for theme law:** `CLAUDE.md` §"Theme art direction — required (dark and light are TWO art directions, not one skin; TP-0 2026-08-27)" — dark = command center, light = research workspace; **Token substitution alone is never proof of a light design**; every material UI packet must name DARK TREATMENT, LIGHT TREATMENT, which mechanisms intentionally differ, the reference/baseline, theme-specific degraded states, and the evidence matrix (dark/light × EN/ZH × desktop 1440 / mobile 390). A packet missing the light art direction or its evidence is `PARTIAL/BLOCKED`, never `PASS`. Forward-only enforced by `scripts/check_design_system.py --mode enforce-added`, `scripts/check_runtime_style_injection.py`, and `scripts/check_ui_visual_evidence.py`.

**Scope check — does this PR carry a theme-relevant surface?** **No.**

- `engine/options_skew.py` — pure Python, no CSS, no template tokens, no inline JS, no design-system reads.
- `scripts/build_options_skew.py` — pure Python CLI, no CSS, no template tokens, no inline JS.
- `tests/test_options_skew_backfill.py` — pure Python tests, no CSS, no template tokens, no inline JS.
- `.github/ci/legacy-jobs.yml` — GitHub Actions YAML, no CSS, no template tokens, no inline JS. The change is one `paths:` entry + one pytest run line under the existing `skew-accrual-lane` job; the new job name string is `"skew-accrual lane — gate, precheck, verify, launchd, overlap + parity audits, payoff lab, backfill"` — a job-name label, never user-facing.
- `agentos/decisions/DEC-SKEW-PARITY-RULING-BACKFILL-COVERED-HISTORY.md` — governance YAML front-matter + plain Markdown body, no CSS, no template tokens, no inline JS.
- `research/MARKET_ONTOLOGY_F03_SKEW_ACCRUAL_LANE_2026-09-22.md` — research Markdown, no CSS, no template tokens, no inline JS. The change is the install-runbook §3.7 — an operator-facing recipe, never user-facing.

**Theme sub-finding 1 — no `templates/`, no `site/`, zero material UI surface.** TP-0 binds every material UI packet; this PR is engine + CLI + tests + CI + DEC + runbook. The theme art-direction law does not bind on this head.

**Theme sub-finding 2 — no runtime style injection.** `python3 scripts/check_runtime_style_injection.py` would scan 197 `.js` files; the PR adds zero JS files. The check would return its existing baseline (`runtime style injection guard OK (197 .js files scanned, 44 injecting, 89 total hits — all within frozen allowances)` per the #7763 audit's body-quoted receipt) — out of scope for this PR.

**Theme sub-finding 3 — no `check_design_system.py --mode enforce-added` finding.** `git diff --unified=0 origin/main HEAD -- templates site` for #7770 is empty; the enforce-added mode returns **R0 blocking finding(s)** trivially.

**Theme sub-finding 4 — no `check_ui_visual_evidence.py` finding.** Same: the diff touches no `templates/`/`site/`, so the evidence check returns 0.

**Theme sub-finding 5 — no follow-on dark/light × EN/ZH × 1440/390 matrix owed.** TP-0's evidence matrix is required only when a material UI packet ships. The follow-on PR `b5adca3c70` (W2-4c — skew source-break) is where the user-facing sentence lands and where any 12-cell matrix would attach.

**Theme verdict:** **N/A by structural absence** (or **PASS by zero-surface, equivalent**). No CSS, no template, no design-system bytes touched. TP-0's dual art-direction law does not bind on this head; the user-facing half-B payload that would bind TP-0 is the W2-5b payload (#7763), already merged + audited on this branch.

---

## 4. Validated-claims findings

**Source for validated-claims law:** `scripts/check_validated_claims.py` (BC-2 — the 'validated' grep gate, `PREREGISTRATION.md` §4, D2 §4.3). Every affirmative `validated` / `已验证` / `经验证` / `经过验证` claim on a user-facing artifact must trace to either (a) a justified entry in `data/regime/validated_claims_allowlist.json` whose `surfaces` list names the claiming file's surface, or (b) a referenced artifact JSON whose top-level `validated == true`. Negated / hedged uses are NOT claims and are auto-ignored (`unvalidated`, `not … validated`, `无…验证`, `非…验证`, `未…验证`, `未经验证`, `不…已验证`).

**Scope check — does this PR introduce any claim-class token?** **No.**

- `git diff origin/main...7770 -- engine/options_skew.py scripts/build_options_skew.py tests/test_options_skew_backfill.py .github/ci/legacy-jobs.yml agentos/decisions/DEC-SKEW-PARITY-RULING-BACKFILL-COVERED-HISTORY.md research/MARKET_ONTOLOGY_F03_SKEW_ACCRUAL_LANE_2026-09-22.md | grep -iE 'validated\|证\|验'` returns **0 hits**.
- The new engine fields `history_sources` (sorted unique list of source tags — `"polygon_gex"`, `"thetadata"`) and `n_weekend_rows_excluded` (int) are pure factual display metadata: which sources existed in the ledger, how many weekend-dated rows were excluded from emit. Neither word is in the claim class (`validated`, `已验证`, `经验证`, `经过验证`, `calibrated`, `已校准`, etc.).
- The DEC record's `confidence: high` is internal governance metadata — never user-facing, so not in scope for the gate. The DEC `evidence:` list names three receipts and one PR; none of those are user-facing claims.
- The runbook §3.7 is an operator recipe — never user-facing.

**Validated-claims sub-finding 1 — no surface in scope for the gate.** `scripts/check_validated_claims.py` scans user-facing surfaces (`templates/`, `site/*.js`, generated `*_data.js`, and `engine/` display-copy fields that FEED them) in BOTH English and Chinese. The diff touches none of those paths. The check would return 0 introduced findings trivially.

**Validated-claims sub-finding 2 — DEC `answer:` does NOT ship a "validated" claim.** The DEC says "Backfill the priceable covered history from the ThetaData store, and let a thetadata row replace a polygon_gex row for the same date and name." — a **construction receipt** ("we did X; here is what replaced Y"), not a "validated" claim ("we have proven X works"). The follow-on W2-5b sentence (deferred to #7763 / W2-4c `b5adca3c70`) is the home for any Tier-2 plain-language null disclosure that may need to use the "validated" word; #7770 does not.

**Validated-claims sub-finding 3 — pre-existing `data/regime/validated_claims_allowlist.json` not touched.** Body declares zero changes to `data/`, `site/`, `mockups/`, `ops/`. The allowlist baseline is unchanged.

**Validated-claims verdict:** **PASS by structural absence.** Zero new claim-class tokens; the engine fields added (`history_sources`, `n_weekend_rows_excluded`) are factual display metadata, not "validated" claims; the inter-packet follow-on sentence for the source break is correctly deferred to W2-5b (#7763) and W2-4c (`b5adca3c70`).

---

## 5. Overall verdict

**PASS** on all three dimensions, by structural absence.

| dimension | verdict | reason |
|---|---|---|
| Plain-language | **PASS** | Zero user-facing copy introduced; the two operator-facing bilingual EN/ZH error strings in `scripts/build_options_skew.py` are well-formed, financial-vocabulary-correct, and audit-clean; the inter-packet plain-language sentence for the source break is correctly deferred to W2-5b (#7763, merged + audited on this branch at `21f6c269a7`). |
| Theme (TP-0) | **PASS (N/A by zero-surface)** | Zero CSS, zero template, zero design-system bytes touched; the user-facing half-B payload that would bind TP-0 is #7763 (already merged + audited). |
| Validated-claims | **PASS** | Zero new claim-class tokens; the engine fields added (`history_sources`, `n_weekend_rows_excluded`) are factual display metadata, not "validated" claims; the inter-packet follow-on sentence is correctly deferred. |

**Positive sub-findings (one-pass, non-blocking):**
- **Engine receipt structure is parsimonious.** The receipt shape `{dates_requested, dates_weekend_skipped, dates_not_in_store, dates_backfilled, rows_replaced, rows_added, rows_unchanged, per_date:[...]}` is the same keys the `--emit` payload carries — making backfill and emit pay the same per-key contract cost and making a future audit ("did the backfill actually run? what did it touch?") a one-grep away.
- **Idempotence is test-pinned.** `tests/test_options_skew_backfill.py::test_backfill_replaces_the_weekday_and_leaves_weekend_and_uncovered` asserts `again["rows_replaced"] == 0` and `again["rows_added"] == 0` on a second call against the same fake ledger — a structural idempotence proof that protects the one-time seat-act runbook §3.7 from accidental re-application on a follow-up shift.
- **Canonical-wins is preserved unchanged.** `compute_skew`, `_nearest_expiry`, `_iv_at_delta`, `skew_map`, `snapshot` (incl. canonical-wins), and `_atomic_write_parquet` are byte-unchanged against `origin/main` (`git diff origin/main...HEAD -- engine/options_skew.py | grep -c '^-[^-]'` = 0). The weekend filter is an **insertion** inside `emit_from_ledger`, never a modification of an existing line that the parity audit (PR #7756, W2-4 read-only leg) attested.
- **DEC citation chain is consistent.** The DEC record `DEC:SKEW-PARITY-RULING-BACKFILL-COVERED-HISTORY` cites `DSC:SKEW-THETADATA-RECOMPUTE-DIVERGES-FROM-POLYGON-LEDGER` (60% sign agreement, 2,392 match / 1,563 flip) and the W2-4 parity receipt (spot mismatch 46.4% on 1,680 keys; both IV legs move; tenor never moves). Both are pre-existing artifacts; the DEC does not invent a discovery or a number.
- **No claim-class token crosses into the DEC record.** `confidence: high` and `evidence: [research/MARKET_ONTOLOGY_F03_SKEW_PARITY_RECEIPT_2026-09-23.md, PR #7756, …]` are internal governance, not user-facing; the `validated_claims` gate has nothing to score.
- **Runbook §3.7 is bounded to the seat.** The "One-time backfill (seat act)" runbook is plainly labelled as a seat-only act ("This step is the one-time backfill. It is not on the daily schedule.") — no path for an accidental `--backfill` from the daily launchd plist. The argparse default (`--backfill FROM TO` is `nargs=2`, default `None`) means bare argv still runs `accrue + emit`, not backfill.

**Non-blocking observations (NOT in scope for this audit, recorded for the W2-4c follow-on):**
- The follow-on W2-4c payload (`b5adca3c70`, "skew source-break — source windows on site/options_skew/latest.json and one plain-language sentence on the Directional read") is the user-facing surface where the Tier-1 plain-language sentence lands; that PR will be the binding plain-language + theme audit target when it ships.
- The follow-on plain-language sentence on the options page in W2-5b (per the DEC `answer:` paragraph) is the same surface — the W2-5b + W2-4c follow-ons are one sentence across two PRs; whichever lands second owns the audit.

**End-state classifier (this audit, one-pass):** **AUDITED-PASS** — the PR ships no user-facing surface and all three gates are clean by structural absence; the next session owns the push / PR / CI / merge / render-lane chain for this audit-record commit (mirrors the standing macro repo house-law / shared-workspace / completion rule). The companion claim commit on this branch should follow the same pattern as the prior audit at `21f6c269a7` (commit message: `orch(audit): record macro PR #7770 plain-language/theme/validated-claims audit (2026-09-23)`, Co-Authored-By Claude Code, single-file insertion in `orch/audits/`).