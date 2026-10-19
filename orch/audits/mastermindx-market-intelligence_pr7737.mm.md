# Audit — mastermindx-market-intelligence/macro PR #7737

Mode: qwen_auditor2-style (plain-language / theme / validated-claims laws). One-pass audit against the merged head. No durable writes outside this report.

## PR metadata

| field | value |
| --- | --- |
| repo | `mastermindx-market-intelligence/macro` |
| PR | [#7737](https://github.com/mastermindx-market-intelligence/macro/pull/7737) |
| title | [MO-A3] A-F03-W2-2: ThetaData skew accrual lane on the store host (launchd + R2 publish) + real-overlap audit tool |
| workplan | MO-A3 (Mastermind O-A3), packet `A-F03-W2-2` — store-host producer that feeds `data/options_skew/snapshots.parquet` (MO-PAID-013 F03-OPTIONS-EXPRESSION, W2-2 / W2-3 cutover) |
| mergedAt | 2026-09-22T23:35:22Z |
| head SHA | `6075860bb31aa4c10562bb7f48bf548552f97312` |
| branch tip | `6075860bb31aa4c10562bb7f48bf548552f97312` (claude/mo-a-3-a-f03-w2-2-skew-accrual-lane) |
| files | 16 changed (4,234 +, 2 −): 5 new scripts, 5 new test files, 1 new plist, 1 new runner shell, 1 new runbook, 1 new DEC, 1 new CI job, 1 small `scripts/publish_r2.py` registration (`options_skew` to `_DATA_DIRS`), 1 small `tests/test_ci_pack.py` (`CURATED_EXCLUSIVE` registration) |
| program surface | backend lane only — `engine/options_skew.py` and `scripts/build_options_skew.py` explicitly NOT touched (W2-1b sibling owns them); no `data/`, no `site/`, no `templates/`, no `.github/workflows/` changes; one new `gate: code / scope: exclusive` CI job in `.github/ci/legacy-jobs.yml` |
| half-B label | "half-B" = MO-A3 backend infra half. The W2-2 packet is the lane that runs W2-1b's `--accrue` against the live ThetaData EOD store on the M1 ops host and publishes the ledger to R2 so W2-3 (`#7743`, render cutover) can `fetch_r2 --dirs options_skew` into render hosts. The body documents the round-1/2/3/4/5/6 review chain and explicitly carries a "W2-3 merges only after the first R2-publish receipt" sequencing law (frozen, do not reorder). |

The PR title says "ThetaData skew accrual lane on the store host" and the body opens with a one-sentence authority/sequencing claim:

> MO-PAID-013 W2-2 / F03-OPTIONS-EXPRESSION ships the **store-host producer** that feeds the options-skew forward ledger (`data/options_skew/snapshots.parquet`).

The packet's own "What this packet did NOT change" list (`scripts/build_options_skew.py`, `engine/options_skew.py`, `data/`, `site/`, any workflow file other than `.github/ci/legacy-jobs.yml`) confirms this is a pure infra lane: the authority ceiling here is a freshness gate (`scripts/skew_accrual_gate.py`) and a precheck/verify helper, with no signal, rank, score, or sizing authored. The runbook (`research/MARKET_ONTOLOGY_F03_SKEW_ACCRUAL_LANE_2026-09-22.md`) is the only prose artifact and is internal (`research/`), not user-facing.

## Plain-language findings

Macro repo does not host `terminal/scripts/check_plain_language.mjs` (Terminal-only). The macro-side plain-language discipline gates user-facing surface copy (`templates/`, `templates/_public_*`, generated `site/*.js`, `_data.js`, `engine/` display-copy fields that FEED them — see `scripts/check_validated_claims.py` / the TP-0 ZW-mode page tests pattern).

**Verdict: PASS (N/A — PR adds zero user-visible strings).**

Spot-check of all 16 PR-touched files for paired-span `t(...)` macros, raw `[A-Z_]{3,}` slug/enum leaks, or any literal English string the user could ever see:

| file | user-visible strings added |
| --- | --- |
| `.github/ci/legacy-jobs.yml` | 0 — one new job name (`skew-accrual-lane`) and a `paths:` list; YAML keys, never rendered to UI |
| `agentos/decisions/DEC-SKEW-ACCRUAL-ON-THE-STORE-HOST.md` | 0 — internal decision record; lives under `agentos/decisions/` which the public site never reads |
| `ops/launchd/com.macro.skewaccrual.plist` | 0 — `Label`, `ProgramArguments`, `StandardOutPath`, `StandardErrorPath`, `EnvironmentVariables`; launchd metadata, never rendered |
| `ops/launchd/run_skew_accrual.sh` | 0 — bash runner; writes `$SKEW_STATE_DIR` artifacts and `--info`/stderr receipts only |
| `research/MARKET_ONTOLOGY_F03_SKEW_ACCRUAL_LANE_2026-09-22.md` | 0 — install runbook; not in `templates/` or `site/`, never reaches the user |
| `scripts/audit_options_skew_overlap.py` | 0 — exit codes (`EXIT_OK`/`EXIT_MISSING_ENGINE`/`EXIT_NO_LEGACY_ROWS`/`EXIT_READ_ERROR`) are stderr receipts, not display copy |
| `scripts/publish_r2.py` | 0 — adds `options_skew` to `_DATA_DIRS`; comment text mentions "data/options_skew" is TRACKED — internal docstring |
| `scripts/skew_accrual_gate.py` | 0 — `::gate-info:: <dict>` receipts to stderr (operator-visible only via `launchd` log tail) |
| `scripts/skew_accrual_precheck.py` | 0 — source-grep for `--accrue`; `BLOCKER-1` is a comment label, not UI |
| `scripts/skew_accrual_verify_ledger.py` | 0 — ledger row-count check + `--pre-rows` no-op refuse |
| `tests/test_*.py` (×5 + 1 modified) | 0 — test code; assertions against synthetic stubs; never rendered |
| `tests/test_ci_pack.py` | 0 — adds one `CURATED_EXCLUSIVE` entry; test code |

No new plain-language debt. The `agentos.py validate` step the body runs (0 errors, 90 warnings) is the right gate for the DEC record this PR introduces — and 90 inherited warnings is the steady-state floor for that file.

## Theme findings

Laws in force:
- TP-0 theme art-direction (dark + light, dark × light × EN/ZH × 1440/390 evidence matrix) — applies to Macro site.
- `scripts/check_ui_visual_evidence.py` — gates material UI changes on committed dark/light evidence receipts.
- `scripts/check_design_system.py --mode enforce-added` — ratchet that blocks only the ADDED_BLOCKING_RULES findings on lines this diff actually added.
- `scripts/check_runtime_style_injection.py` — runtime JS-injected `style.textContent` may only stay flat or shrink.

**Verdict: PASS (N/A — PR adds zero template/CSS/JS changes; all four gates have no added surface to evaluate).**

Spot-check of the 16-file footprint for `templates/`, `templates/_public_*`, `site/`, `site/**/*.css`, `site/**/*.js`, or `theme.js`/`theme.css`/`navigation-refresh.css`/`nav_market.js`/`_public_chrome_*`:

- Zero files touched under any of those roots.
- No `style.textContent` JS-injected CSS authored (the CI guard `check_runtime_style_injection.py` measures runtime injection, none exists here).
- No `archetype`/`nav_family`/`payload_tier`/`access_shell`/`themes` row added to any page registry — `scripts/publish_r2.py`'s `_DATA_DIRS` row is data-side, not UI-side.

This PR cannot regress TP-0 by construction: nothing it ships reaches a browser.

## Validated-claims findings

Laws in force (per `scripts/check_validated_claims.py`):
- The word "validated" (`'validated'`, `'已验证'`, `'经验证'`, `'经过验证'`) is gated by `data/regime/validated_claims_allowlist.json` on user-facing surfaces (`templates/`, `site/*.js`, generated `*_data.js`, and `engine/` display-copy fields).
- NEGATED/HEDGED uses (`unvalidated`, `not ... validated`, `未经验证`, `非...验证`, etc.) are explicitly ignored.
- Engine source copy and registry rows are scanned in-tree (the latter on the data side rather than after nightly render).

**Verdict: PASS (N/A — PR adds zero display-surface claims and the only "validated" hit is in a generic English prose phrase, not an affirmative user-facing assertion).**

Spot-check of the 16-file footprint for `validated|经验证|已验证|经过验证`:

| file | hit | in scope? |
| --- | --- | --- |
| `agentos/decisions/DEC-SKEW-ACCRUAL-ON-THE-STORE-HOST.md` | 0 | n/a (internal) |
| `research/MARKET_ONTOLOGY_F03_SKEW_ACCRUAL_LANE_2026-09-22.md` | 1 — line 123: `"validated by the schema)"` | n/a (`research/` is not a user-facing surface; the gate's `_SURFACE_TEMPLATES` / `_SURFACE_SITE_JS` mappings do not list `research/`) |
| `scripts/skew_accrual_*.py` | 0 (gate-info receipts use the literal `::gate-info::` prefix, not `validated`) | n/a |
| `ops/launchd/com.macro.skewaccrual.plist` | 0 | n/a |
| `ops/launchd/run_skew_accrual.sh` | 0 | n/a |
| `.github/ci/legacy-jobs.yml` | 0 | n/a |
| `tests/test_*.py` | 0 (assertions are on string substrings but not on the literal `"validated"` claim) | n/a |
| `scripts/publish_r2.py` | 0 | n/a |

The single `validated` hit is in runbook prose ("validated by the schema") — a generic English sentence describing how the parquet writer checks rows, not an affirmative claim about a Macro Dashboard signal/rank/score/gate. The PR does not assert any "validated" status to a user, and the file lives under `research/` which the gate does not scan.

The gate's body-side tone ("Validated 222 legacy jobs", "0 error(s), 90 warning(s)", "0 introduced, 1 inherited") is descriptive command output, not user-facing copy — and even if it were, the only one that would name an unbacked affirmative claim is "Validated 222 legacy jobs", and that's a CI run-result fact (not a platform signal claim), so it would be `n/a` to the gate's `validated` claim class.

## Overall verdict

**PASS.** This PR is a clean backend infra packet: zero user-facing surface changes (no templates, no site/, no CSS, no JS, no engine display-copy fields), zero plain-language debt, zero theme debt, zero validated-claim debt. The 16 files all live under `ops/`, `scripts/`, `tests/`, `agentos/decisions/`, `research/`, or CI config — roots that the three UI/discipline gates do not scan by design.

Scope notes that the body itself flags honestly:
- W2-1b (sibling PR, `claude/mo-a-2-a-f03-w2-1`) owns `engine/options_skew.py` and `scripts/build_options_skew.py`; this packet only writes the lane that runs the accrue flag. The body names the W2-3 (#7743) sequencing dependency: "merges only after the first R2-publish receipt".
- The `skew-accrual-lane` CI job (`gate: code / scope: exclusive`) names the five new suites by `run:` step (per `tests/test_ci_pack.py::test_curated_exclusive_scopes_cover_their_own_import_closure`), so the waiver file (`config/unrun_test_waivers.yml`) loses 5 self-parked rows in this PR — a deliberate un-park, not a regression.
- The plist is **OFF by default** until the Meta-CEO A seat installs it per the runbook — the M1 ops host is not affected until that install happens, regardless of merge.
- The PR is DRAFT at delivery per the round-6 body header ("DRAFT until the Meta-CEO A seat ratifies; merge only by the seat at a RATIFIED head"); the seat installed the cure commits and shipped the merge via PR #7737's own squash, so this is the seat's ratification.
- Round-6 evidence cited in the body (`73 passed in 35.27s` across five suites, `tests/test_check_script_import_pinning.py` 11 passed, `tests/test_ci_pack.py -k curated_exclusive` 2 passed, `check_contract_delta.py --base origin/main` 0 introduced / 1 inherited, `sh -n run_skew_accrual.sh` exit 0, `plutil -lint` OK, `agentos.py validate` 0 errors) is consistent with the lane type — a backend infra PR with no UI surface to render, so no 24-cell evidence matrix is owed.

For the qwen_auditor2 framing this audit mirrors: a backend lane that does not touch the user-facing surface is genuinely out-of-scope for the three laws the auditor runs, and naming that explicitly (rather than forcing a vacuous "PASS") is the audit's correct verdict form.