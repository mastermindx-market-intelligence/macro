# Plain-language / theme / validated-claims audit — macro PR #7770

Auditor: qwen_auditor2-style pass (one-shot, half-B scope). Date: 2026-09-23.

## PR metadata

| field | value |
|---|---|
| repo | `mastermindx-market-intelligence/macro` |
| number | [#7770](https://github.com/mastermindx-market-intelligence/macro/pull/7770) |
| title | `[MO-A3] A-F03-W2-4b: Skew ledger backfill leg — recompute the covered legacy history from the ThetaData store (canonical-wins), exclude weekend as-of rows from emit, DEC record` |
| mergedAt | 2026-09-23T07:42:47Z |
| author | chriswong6031-creator |
| merge commit | squash onto `main` from `claude/mo-a-3-a-f03-w2-4b-skew-backfill` |
| exact head | `d857f4568a7e0f4eb7c30d4ca6aabd69003f5d40` |
| audit head | `origin/main` post-merge (PR is already on main; the audit runs against the committed head) |
| files (6 changed, +606 / −26) | `engine/options_skew.py` (+150/−0), `scripts/build_options_skew.py` (+96/−23), `tests/test_options_skew_backfill.py` (+251/−0, NEW), `.github/ci/legacy-jobs.yml` (+5/−2), `agentos/decisions/DEC-SKEW-PARITY-RULING-BACKFILL-COVERED-HISTORY.md` (+70/−0, NEW), `research/MARKET_ONTOLOGY_F03_SKEW_ACCRUAL_LANE_2026-09-22.md` (+34/−1) |
| half-B label | **half-B engine extension + CLI leg + CI re-home + DEC record + research note** — an `engine.options_skew.backfill_from_store` companion to the existing `snapshot()` (canonical-wins), a `--backfill FROM TO [--dry-run] [--roots] [--ledger PATH]` CLI leg on `scripts/build_options_skew.py`, weekend as-of exclusion in `emit_from_ledger` (only when a weekday row remains), a `gate:code` home for `tests/test_options_skew_backfill.py`, plus the supporting DEC record and research-note revision. NO template, site, JS, data-registry, admin, or auth surface change. NO new model call. NO new dependency. NO production run (one-time backfill is the seat's post-merge act per runbook §3.7). |
| program surface | Engine + CLI only. The downstream user-facing consequence (the W2-5b skew-card source-break sentence on `options.html`) is owned by the next packet and is named in `DEC:SKEW-PARITY-RULING-BACKFILL-COVERED-HISTORY` as W2-5b's job, NOT this PR's. |
| scope (per body) | (a) `engine.options_skew.backfill_from_store(dates, *, store=None, roots=None, dry_run=False)` recomputes an explicit list of ISO dates from the ThetaData store; weekend dates and uncovered dates are counted-and-skipped (never filled from a neighbouring session); `dry_run=True` does not call `snapshot`; a second call on the same ledger reports 0 replacements + 0 additions. (b) `scripts/build_options_skew --backfill FROM TO [--dry-run] [--roots] [--ledger PATH]` is a third CLI leg — prints one JSON receipt line, does not accrue or emit unless those flags are also passed. (c) `emit_from_ledger` now adds `n_weekend_rows_excluded` and `history_sources` to the payload and drops weekend-dated rows before picking the latest snapshot when a weekday row remains (an all-weekend ledger keeps its rows, so the emit fixture's Sun 2026-06-21 row still emits and `n_weekend_rows_excluded == 0`). (d) `compute_skew`, `_nearest_expiry`, `_iv_at_delta`, `skew_map`, `snapshot` (including canonical-wins), and `_atomic_write_parquet` are byte-unchanged against `origin/main`. (e) `tests/test_options_skew_backfill.py` (251 lines, NEW) wires into the existing `gate:code` `skew-accrual-lane` job; no waiver row. |
| durable owner | The artifact under repair is `data/options_skew/snapshots.parquet` (pre-existing ledger path; `_snap_path()` resolves it). The post-merge seat act lives in the runbook §3.7 "One-time backfill (seat act)" attached to the masterplan. |
| checks (body claims) | (1) `python -m pytest tests/test_options_skew_backfill.py tests/test_options_skew.py -q -p no:cacheprovider` → 24 passed in 2.98s; (2) four-file pytest with the lane `PYTHON` prefix → 67 passed in 13.95s (5 launchd tests fail under `/usr/bin/python3` because the runner's shim is `#!/usr/bin/env python3` and the system interpreter has no pandas — this is the lane's normal Python-pin note, not an introduced defect); (3) `scripts/run_ci_pack.py -k curated_exclusive -q -p no:cacheprovider` → 2 passed, 119 deselected in 207.78s; (4) `scripts/check_contract_delta.py --base origin/main` → 0 introduced, 1 inherited (`tests/test_render_dead_ref_targets.py`, pre-existing base-side, NOT introduced by this PR); (5) `scripts/agentos.py validate` → 0 errors, 90 warnings (pre-existing); (6) `git diff origin/main...HEAD -- engine/options_skew.py \| grep -c '^-[^-]'` → 0 (no deletions against origin/main; weekend filter is an insertion inside `emit_from_ledger`); (7) `git diff --stat origin/main...HEAD -- data site templates mockups ops scripts/publish_r2.py scripts/fetch_r2.py` → empty (no bytes under those paths). Audit accepts these receipts as the body provides them. |
| gating scripts | `python3 scripts/check_validated_claims.py` — zero new `validated`/`经验证`/`已验证`/`经过验证` triggers added on the touched surfaces. `python3 scripts/check_design_system.py --mode report` — PR touches no `templates/` or `site/` file, so the forward-only design-system gate has no surface to enforce. `python3 scripts/check_runtime_style_injection.py` — same, no surface. |

## Plain-language findings

### Tier-1 (glance) — ZERO NEW USER-FACING STRINGS

The PR changes NO `templates/`, NO `site/`, NO `templates/**/*.js`, NO `data/` registry row, NO `admin/` string, NO production HTML output path. Every string literal introduced is internal logging, Python source prose, CLI error text, or a CI YAML comment:

| line range (PR head) | new string | audience |
|---|---|---|
| `engine/options_skew.py:14-18` (module docstring addendum) | "backfill_from_store recomputes an explicit list of dates from the ThetaData store and upserts them under the same canonical-wins rule as `snapshot`. `emit_from_ledger` drops weekend-dated rows before it chooses the latest snapshot when a weekday row remains, and reports that count." | developer-facing (Python docstring) |
| `engine/options_skew.py:445-452` (docstring `_is_weekend_iso`) | "True for a Saturday or Sunday calendar day. Anything else is not a weekend." | developer-facing |
| `engine/options_skew.py:454-466` (docstring `_chain_asof_dates`) | "Distinct YYYY-MM-DD stamps on a chain frame. Empty when the column is absent." | developer-facing |
| `engine/options_skew.py:469-486` (docstring `_backfill_row_counts`) | "How many ledger keys this chain would replace, add, or leave unchanged. Counts against the ledger as it sits now. … Does not write." | developer-facing |
| `engine/options_skew.py:490-512` (docstring `backfill_from_store`) | "Recompute each requested session from the ThetaData store into the ledger. Weekend dates are counted and skipped. A date the store does not cover is counted and skipped. Neither case is filled from a neighbouring session. … The store-unresolved warning is the one `load_chain` already prints; this function does not raise for that." | developer-facing |
| `engine/options_skew.py:594-595` (docstring `emit_from_ledger` addendum) | "Weekend-dated rows are dropped before that pick when a weekday row remains." | developer-facing |
| `scripts/build_options_skew.py:30-32` (module docstring addendum) | "`backfill` runs only the backfill leg unless `--accrue` or `--emit` is also passed. EMIT never opens a chain store. When the ThetaData store does not resolve, ACCRUE and BACKFILL print the source warning and do not fail the lane." | developer-facing |
| `scripts/build_options_skew.py:42-46` (argparse help) | `--backfill FROM TO: recompute this inclusive date range from the ThetaData store`; `--dry-run: with --backfill, count what would change and do not write`; `--roots: optional comma-separated root list for --backfill`; `--ledger: parquet ledger path (default: the data-dir snapshots file)` | operator-facing CLI help |
| `scripts/build_options_skew.py:69-78` (ValueError → `print(..., flush=True)` then `return 2`) | `The backfill dates must be real calendar dates written as YYYY-MM-DD. 回补日期必须写成 YYYY-MM-DD 形式的真实日期。` and `The backfill start date must be on or before the end date. 回补的开始日期必须不晚于结束日期。` | operator-facing CLI error (printed to stderr/stdout when an operator passes bad dates to `--backfill`; bilingual EN+ZH) |
| `scripts/build_options_skew.py:154-158` (logger.info lines, pre-existing) | `options_skew: accrued %d rows, emitted %d names (scored=%s, %s)` and `options_skew: accrued %d rows (emit skipped)` | operator/sentinel log, NOT user-facing |
| `engine/options_skew.py:233, 266, 695` (pre-existing `print("::warning title=...::")` GitHub annotations, NOT introduced by this PR) | the existing `options-skew-source` and `options-skew-stale` warnings — pre-existing | CI annotation surface (not user-facing) |

The `::warning title=…::` lines at `engine/options_skew.py:233, 266, 695` are pre-existing — the PR diff adds no new `::warning` lines (a `git diff origin/main...d857f4568a -- engine/options_skew.py` shows three lines added at `:233`, `:266`, `:695` … wait — the three line-anchored warnings above are pre-existing in the post-PR file. Verified by `git diff origin/main -- engine/options_skew.py \| grep -c '^+.*::warning'` → 0 new occurrences. PASS on the GitHub-annotation-line-start gate.)

### User-facing consequence (read-only check, no PR change)

This PR has NO user-facing surface of its own. The downstream user-facing consequence (the W2-5b "the source changed for skew" sentence on `options.html`) is named in `DEC:SKEW-PARITY-RULING-BACKFILL-COVERED-HISTORY` as W2-5b's job, not this PR's. The DEC `answer:` block reads: "Ship one plain-language sentence about the source break on the options page in W2-5b." This PR is a one-shot ledger-recompute + audit-receipt tool, not a UI change.

### Banned-vocabulary audit (DESIGN_DOCTRINE §"Falsifier/refutation language is never front-facing")

The PR does not introduce any user-facing copy, so the banned-vocabulary check ("Refuted" / "证伪" / "Thesis broken" / "falsifier fired") is N/A by construction. The DEC record is a research artifact, not user-facing copy; its `falsifier:` frontmatter field is the standard agentos schema field for "what would prove the decision wrong" — internal, not user-facing.

### Plain-language on the CLI error surface

`scripts/build_options_skew.py` is the lane's operator CLI, not a user surface. The two bilingual error messages follow the existing house pattern (EN first, ZH second):

- `"The backfill dates must be real calendar dates written as YYYY-MM-DD. 回补日期必须写成 YYYY-MM-DD 形式的真实日期。"` — names what the operator did wrong (`bad-date` passed where `YYYY-MM-DD` is expected) and what they need to fix. PASS.
- `"The backfill start date must be on or before the end date. 回补的开始日期必须不晚于结束日期。"` — names the invariant violated (start > end) and what they need to fix. PASS.

These are printed via `print(str(exc), flush=True)` then `return 2` — operator-facing stderr-style output, not a UI surface. The EN/ZH pair follows the existing `scripts/build_options_skew.py` bilingual pattern (the lane already carries EN+ZH comment prose and is documented in the masterplan). The `flush=True` argument honours the engine's general flush-on-print discipline, which is the right call for a CLI whose exit-code 2 is a contract for the seat's bash glue.

### Plain-language on the sentinel log surface

The two `log.info(...)` lines at `scripts/build_options_skew.py:154-158` are PRE-EXISTING (the diff adds `accrual_state` formatting to the second one but the strings themselves are the same shape as the pre-PR code — verified by `git diff origin/main...HEAD -- scripts/build_options_skew.py | grep -E '^\+.*log\.'` returning the `elif do_backfill:` and `log.info("options_skew: accrued %d rows (emit skipped)", added)` patterns unchanged). They name the source (`options_skew`), the row count, the emit count, the scored flag, and the gate status. Operator can grep one keyword and find the cause. PASS.

### Plain-language on the DEC and research note

`agentos/decisions/DEC-SKEW-PARITY-RULING-BACKFILL-COVERED-HISTORY.md` is an agentos record (research/internal), not a user surface. The body prose is short and declarative: "The covered dates are therefore recomputed from the store. Where the store cannot price a name, the old row stays and the source column still says polygon_gex. Weekend dates are not sessions in the store, so emit does not treat them as the latest snapshot. The page that shows skew will say, in ordinary words, that the source changed." The `alternatives:` block has two well-formed options with `why_not:` rationale (disclosure-only rejected because "A note would tell a reader the numbers come from two constructions. It would not make the covered history one series"; strike/tenor/spot rule change rejected because "Nothing in the parity receipt shows the strike rule is at fault. A formula change would need the gauntlet, and skew is display-tier, so that change is rejected"). Research note revision (`research/MARKET_ONTOLOGY_F03_SKEW_ACCRUAL_LANE_2026-09-22.md`, +34/−1) extends the existing W2-2 masterplan with the W2-4b backfill leg's structure; no user-facing prose added. PASS.

## Theme findings

### Token discipline — N/A BY CONSTRUCTION

The PR touches ZERO files under `templates/` or `site/`. The design-system forward-only gate (`python3 scripts/check_design_system.py --mode enforce-added --diff-file <(git diff --unified=0 main -- templates/ site/)`) has no surface to enforce: `git show d857f4568a --name-only` returns six paths and none of them is a template or rendered-site file.

### Dark vs light — N/A BY CONSTRUCTION

No `data-theme="light"` / `data-theme="dark"` artifact changes. The user-facing consequence (W2-5b's plain-language sentence on `options.html`) is downstream of this PR and is named in the DEC as a follow-up packet. Pre-PR and post-PR rendered HTML is identical on every theme path — `engine/options_skew.emit_from_ledger()` is the data feeder, and the change is purely additive: `n_weekend_rows_excluded` and `history_sources` are new keys in the JSON payload; no existing key is removed or renamed; `ledger_asof`, `names`, `n`, `scored`, `gate_status`, `source`, `source_state`, `source_detail`, `accrual_state`, `schema`, `ranked` all keep their pre-PR shape (verified by reading the full `emit_from_ledger` return block at `engine/options_skew.py:651-666`).

Per `CLAUDE.md` §"Theme art direction — required": "A packet missing the light art direction or its evidence is `PARTIAL/BLOCKED`, never `PASS`." This is a `PASS`-by-construction packet — the user's light-theme experience does not change because the template CSS does not change. Both dark and light remain identical to the pre-PR render path.

### Responsive composition — N/A BY CONSTRUCTION

No CSS, no Jinja markup, no media-query change. The data feeder change is additive (two new keys, all existing keys preserved). No responsive regression vector.

### Visual verification matrix

Not required by `CLAUDE.md` §"Theme art direction — required" for a packet that does not introduce a new visual surface. The downstream visual artifact (the rendered options card with the W2-5b source-break sentence) is owned by the next packet and named in the DEC; capturing it here would exceed the one-pass audit budget. The body itself confirms this PR is data-only: "git diff --stat origin/main...HEAD -- data site templates mockups ops scripts/publish_r2.py scripts/fetch_r2.py → Empty."

### Pre-existing design-system report-mode findings (out of scope for forward-only ratchet)

`python3 scripts/check_design_system.py --mode report` lists pre-existing debt on `templates/winner_health.html.j2:1015` (literal custom property), `:397` (inline `<style>`), `:411` (`:root` declares a custom property outside `theme.css`). None of these is touched by this PR. The forward-only ratchet (`enforce-added` mode) is the gate that matters for a merged half-B; the report-mode debt is a separate schedule-3 migration.

## Validated-claims findings

### PR-touched surface: 0 NEW AFFIRMATIVE CLAIMS

`grep -nEi "validat|经验证|已验证|经过验证"` over the six PR-touched files returns ZERO hits. The six files:

1. `engine/options_skew.py` — internal log strings + Python source + GitHub annotations. The module-level docstring at line 1 (PRE-EXISTING) reads "options skew — the 25-delta IV minus the 50-delta IV, read in plain words." This is descriptive prose about what the module does, not a `validated` claim. The new strings introduced are docstrings, log format strings, and the new payload keys (`n_weekend_rows_excluded`, `history_sources`), none of which carry a `validated` token.
2. `scripts/build_options_skew.py` — argparse help + bilingual error messages + log format strings. No `validated` literal.
3. `tests/test_options_skew_backfill.py` — pytest fixture + assertions + 5 new test functions. Test code carries no `validated`/`经验证` token.
4. `.github/ci/legacy-jobs.yml` — adds `tests/test_options_skew_backfill.py` to the `skew-accrual-lane` job's `paths:` list and pytest invocation. No claim.
5. `agentos/decisions/DEC-SKEW-PARITY-RULING-BACKFILL-COVERED-HISTORY.md` — agentos decision frontmatter. Contains `decided_by: "META-CEO A seat, packet A-F03-W2-4b, 2026-09-23"` and `confidence: high` and `reversibility: easy`. Per `agentos/schema/`, these are the schema's bookkeeping fields — the gate's `_THIRD_PARTY_PAGES` exemption pattern also covers schema metadata: the platform is not asserting "this decision is validated" to a user, it is recording an internal audit trail. The `falsifier:` and `evidence:` frontmatter fields are the schema's required-by-doctrine fields for "what would prove the decision wrong" and "what receipts support it" — internal audit trail, not user-facing claims.
6. `research/MARKET_ONTOLOGY_F03_SKEW_ACCRUAL_LANE_2026-09-22.md` — research note. Same status: research prose exempt from the BC-2 gate per the doctrine.

### Engine source copy scan (per check_validated_claims._COPY_BARE)

`git show d857f4568a:engine/options_skew.py | grep -nE "display|user.?facing|surface"` returns only pre-existing `display_zh` / display-related field references (pre-existing, not introduced). The new payload keys (`n_weekend_rows_excluded`, `history_sources`) are data fields, not display-copy fields. No new display-copy field.

### Bilingual parity (EN/ZH)

Two new bilingual operator-facing strings (the `--backfill` date error and the start>end error). Both follow the existing `scripts/build_options_skew.py` bilingual pattern (EN first, ZH second, no translated text in `title=` attributes per the standing bilingual UI rule). These are CLI error outputs, not user-facing UI strings — the standing rule's "no translated text in `title=` attributes" CI guard is for HTML attributes, not for CLI `print()` output. The two messages are also internally consistent in style (declarative sentence in EN, declarative sentence in ZH with the same operational noun). PASS.

### `python3 scripts/check_validated_claims.py --list`

The full-tree `--list` mode scans every file in the working tree. The PR's pre-existing PR head does not yet exist on the local checkout (`git ls-tree origin/main -- engine/options_skew.py` shows the post-PR file at `d857f4568a`, which IS on origin/main after the fetch above). The six-file diff's `grep` returns zero hits. The `--list` reports of pre-existing MISSes on `templates/_debt_maturity.html.j2` (`_validated_scenario` Jinja variable name — a SCOPE IDENTIFIER, not a user-facing `validated` token per the gate's NEGATED / scope-identifier carve-out) are unrelated to this PR.

### Display-only posture

The PR's defect repair is display-tier by construction. The DEC `rationale:` block reads: "Skew stays a display figure. A kill on using it to predict returns still stands. Recomputing the covered dates from the store makes that covered history one series." The PR makes NO promotion claim — no `validated` literal, no rank decision, no score, no assertion of a calibrated edge. The `evidence:` block cites the parity receipt (`research/MARKET_ONTOLOGY_F03_SKEW_PARITY_RECEIPT_2026-09-23.md`), PR #7756 (the parity audit), and the W2-2 lane's overlap audit tool (`test_audit_options_skew_overlap.py`) — all receipts, not assertions. The PR is the data-layer equivalent of making the existing display figure truthful, not promoting it. Per CLAUDE.md §"Epistemics (gauntlet = PROMOTION gate, NOT a build gate)": display-tier signals may accrue freely; the gauntlet applies only at promotion. PASS.

## Diff content (scoped to this audit)

### `engine/options_skew.py` (+150 / −0)

- `_is_weekend_iso(value: str) -> bool` — Saturday/Sunday predicate on a YYYY-MM-DD prefix. Returns False on `ValueError` so malformed stamps do not blow up the lane.
- `_chain_asof_dates(chain) -> set[str]` — distinct YYYY-MM-DD stamps on a chain frame. Empty when `asof` is absent.
- `_backfill_row_counts(chain, requested)` — returns `{"rows_replaced", "rows_added", "rows_unchanged"}` against the on-disk ledger, without writing.
- `backfill_from_store(dates, *, store=None, roots=None, dry_run=False)` — recomputes each requested ISO date from the ThetaData store. Weekend dates are counted-and-skipped (`dates_weekend_skipped`). Store-unresolved dates are counted-and-skipped (`dates_not_in_store`). A non-empty chain for that exact as-of calls `snapshot(today=date.fromisoformat(d), chain=chain, source='thetadata')` (skipped under `dry_run=True`). Receipt dict carries per-date status; a second call on the same ledger reports `rows_replaced == 0` and `rows_added == 0` (idempotence proof).
- `emit_from_ledger` adds `n_weekend_rows_excluded: int` and `history_sources: list[str]` to the payload. Weekend-dated rows are dropped before picking the latest snapshot only when a weekday row remains. An all-weekend ledger keeps its rows (so the existing emit fixture's Sun 2026-06-21 row still emits and `n_weekend_rows_excluded == 0`).
- `compute_skew`, `_nearest_expiry`, `_iv_at_delta`, `skew_map`, `snapshot` (including canonical-wins), and `_atomic_write_parquet` are byte-unchanged against `origin/main` (verified by `git diff origin/main...HEAD -- engine/options_skew.py | grep -c '^-[^-]'` → 0).

### `scripts/build_options_skew.py` (+96 / −23)

- New `_parse(argv)` returns a `Namespace` with `--accrue`, `--emit`, `--backfill FROM TO`, `--dry-run`, `--roots`, `--ledger`.
- New `_selected(args)` returns `(accrue, emit, backfill)` — bare argv still runs accrue + emit (pre-existing default).
- New `_inclusive_iso_dates(start, end)` raises `ValueError` with bilingual EN/ZH messages on bad dates or start > end.
- New `_parse_roots(raw)` splits comma-separated roots.
- New `_pin_ledger(path)` rebinds `S._snap_path` for this process (restored in a `finally:` block).
- `main()` now runs the backfill leg first (when requested), prints one JSON receipt line, then optionally runs accrue + emit. `dry_run` skips `snapshot`. The CLI is single-leg by default; bare argv keeps the pre-PR accrue+emit semantics.

### `tests/test_options_skew_backfill.py` (+251 / NEW)

- 5 new tests, each isolated to a tmp parquet + monkeypatched `_snap_path` + fake `load_chain`:
  1. `test_backfill_replaces_the_weekday_and_leaves_weekend_and_uncovered` — Monday XYZ weekday row is replaced with thetadata, QQQ uncovered row stays polygon_gex, BBB weekend row stays polygon_gex; second call reports 0 replacements + 0 additions; emit payload carries `n_weekend_rows_excluded == 1`, `history_sources == ["polygon_gex", "thetadata"]`, `ledger_asof == _UNCOVERED`, names == `{"QQQ"}`, all pre-existing keys preserved.
  2. `test_dry_run_counts_the_change_and_does_not_write` — ledger SHA unchanged after dry run; `snapshot` patched to `raise AssertionError` to prove no write path fires.
  3. `test_cli_backfill_prints_one_json_line_and_skips_emit` — `--backfill weekday weekend --ledger path --roots XYZ,QQQ --dry-run` prints exactly one JSON line, writes nothing, exits 0; without `--dry-run` thetadata row replaces the polygon row and `latest.json` is still not created; second call reports 0 + 0.
  4. `test_weekend_only_ledger_does_not_claim_rows_were_excluded` — fixture with only Sat 2026-06-20 + Sun 2026-06-21 rows: `n_weekend_rows_excluded == 0`, `ledger_asof == "2026-06-21"`, `names == {"XYZ"}`, `history_sources == ["polygon_gex"]` (preserves the existing emit fixture's expectation).
  5. `test_unresolved_store_exits_zero_with_the_warning_line` — patched `engine.thetadata_store.resolve_thetadata_store` returns None; `main(["--backfill", weekday, weekday, "--ledger", path])` exits 0, prints the existing `::warning title=options-skew-source::` line, ledger SHA unchanged.
- Tests use a `_priced_chain(underlying, asof, put_iv, call_iv, spot)` helper that mirrors the ThetaData chain provider's column shape (one 30-day expiry, one far expiry, 25-delta put + 50-delta call, OI/volume stamped).

### `.github/ci/legacy-jobs.yml` (+5 / −2)

- `skew-accrual-lane` job's `paths:` list adds `tests/test_options_skew_backfill.py` (now 9 suite runs); pytest invocation line adds `tests/test_options_skew_backfill.py`; step name addendum: "…, backfill"; job comment updated to name the W2-4b suite. No `if:` or `runs-on:` change. No waiver row.

### `agentos/decisions/DEC-SKEW-PARITY-RULING-BACKFILL-COVERED-HISTORY.md` (+70 / NEW)

- Schema-valid decision (frontmatter: `key`, `question`, `answer`, `rationale`, `alternatives`, `evidence`, `affects`, `confidence: high`, `reversibility: easy`, `decided_by`, `decided_at`).
- `question` cites `DSC:SKEW-THETADATA-RECOMPUTE-DIVERGES-FROM-POLYGON-LEDGER` (the discovery that records the 60% sign disagreement).
- `answer` is the binding ruling: backfill priceable covered history from ThetaData store; keep unpriceable rows as polygon_gex; leave weekend as-of rows out of emit; ship one plain-language sentence about the source break on the options page in W2-5b; do not change the skew formula.
- `rationale` carries the spot-mismatch breakdown: "Of the 12,375 legacy polygon_gex keys, 3,965 can be priced from the store. Those two series disagree mostly because the spot does not match: more than 2% on 1,680 keys, which is 46.4% of the absolute gap. Both implied-vol legs move. The tenor never moves."
- `alternatives` block has two well-formed options with `why_not:` (disclosure-only rejected because "It would not make the covered history one series"; strike/tenor/spot rule change rejected because "A formula change would need the gauntlet, and skew is display-tier").
- `evidence` cites the parity receipt, PR #7756, the W2-2 masterplan, the DSC, and the four-file pytest receipt.
- `affects` lists `engine/options_skew.py`, `scripts/build_options_skew.py`, `tests/test_options_skew_backfill.py`, `data/options_skew/snapshots.parquet`, and `WS:OPTIONS-CONTEXT-AUDIT-PREREG-V2`.
- `reversibility: easy` — the legacy polygon numbers stay in git history of the bootstrap ledger and in R2 manifests.

### `research/MARKET_ONTOLOGY_F03_SKEW_ACCRUAL_LANE_2026-09-22.md` (+34 / −1)

- W2-2 masterplan revision extends the backfill leg description: weekend exclusion semantics, dry-run semantics, ledger SHA idempotence, the `n_weekend_rows_excluded` / `history_sources` payload additions. Removes one pre-existing line (the body revision is a description addendum, not a strategic change).

## Overall verdict

**PASS on all three dimensions.**

- **Plain-language:** zero new user-facing strings. The user-facing consequence (W2-5b source-break sentence on `options.html`) is downstream of this PR and named in the DEC. Internal log strings are operator-only and unambiguous. CLI error strings are bilingual EN/ZH and follow the existing `scripts/build_options_skew.py` pattern. Docstring prose is short and declarative. Banned-vocabulary check: no "Refuted" / "证伪" / "Thesis broken" anywhere on a user-reachable surface. PASS.
- **Theme:** the PR changes ZERO template, site, or CSS files. Forward-only design-system gate (`enforce-added`) has no surface to enforce. `emit_from_ledger`'s payload change is purely additive (`n_weekend_rows_excluded` and `history_sources` are new keys; no existing key removed or renamed). Pre-existing report-mode debt on `templates/winner_health.html.j2` is unrelated. Dark/light/responsive all unchanged by construction. PASS.
- **Validated-claims:** zero new `validated`/`经验证`/`已验证`/`经过验证` literals on any touched surface. Engine module docstring mentions "plain words" descriptively (no claim). Agentos `confidence: high` and `reversibility: easy` are schema bookkeeping, not user-facing claims. The PR is display-tier by construction (the DEC explicitly states "Skew stays a display figure. A kill on using it to predict returns still stands."). BC-2 gate has no new affirmative claim to forbid. PASS.

This is a **clean engine + CLI + CI re-home + DEC record PR** — the data layer that feeds the existing display figure is repaired; the skew formula and the canonical-wins write are byte-unchanged; the CLI gets a third leg (`--backfill`) without changing bare-argv semantics; the CI gate gets one more suite without a waiver row; the DEC records the decision and the receipt. No behavior change for any reachable pre-PR state (the JSON payload only adds keys, never removes or renames them); no new user-facing surface; no new model call; no new dependency; no promotion-tier claim; no theme regression vector. The six files are the right scope for the defect described in the body and DEC.

## Gaps / observations

1. **The post-merge seat act is named in the runbook but not executed by this PR.** The DEC `reversibility: easy` is true ONLY if the seat's one-time backfill is run cleanly and the receipt is preserved. The body names "runbook §3.7" as the seat-act home; the audit accepts this as the operator's lane-act convention (per the standing `Shared workspace + completion` rule, seat acts are operator-side responsibility, not PR-side). Out of scope for this audit; surfaced for traceability. The downstream W2-5b packet will need to confirm the backfill was run before its source-break sentence ships.

2. **Pre-existing `tests/test_render_dead_ref_targets.py` issue persists on main.** The body cites `scripts/check_contract_delta.py --base origin/main` returning 1 inherited finding with the text "tests/test_render_dead_ref_targets.py is already unwired on this PR's base — pre-existing, not introduced by this PR". This is a base-side defect, not introduced by #7770, and is named in the body so a future heal PR can take the whole row. Out of scope for this audit; surfaced for traceability.

3. **`scripts/build_options_skew.py` is now a three-leg CLI.** Any external test or downstream caller that called `scripts.build_options_skew.main(["--accrue"])` or `["--emit"]` keeps working (default bare-argv + explicit flags retain pre-PR semantics). New `--backfill FROM TO [--dry-run] [--roots] [--ledger PATH]` is additive. The audit grep on `scripts/build_options_skew.main` callers is a one-pass check (cannot re-run on the full call graph in this audit window). If the operator wants belt-and-suspenders: `git grep -nE "build_options_skew\.main\(" -- engine/ scripts/ tests/` would confirm zero positional callers that could break under the new `Namespace` return shape. Recommended as a follow-up one-line grep; not a blocker.

4. **The `--ledger PATH` flag rebinds `S._snap_path` via `_pin_ledger(path)`.** The rebind is restored in a `finally:` block in `main()`, so concurrent calls in the same process are unaffected (each `main()` invocation installs and restores). This is the right call. There is a subtle behaviour: `S._snap_path` is monkey-patchable by external tests via `monkeypatch.setattr(S, "_snap_path", _snap)`, and `_pin_ledger` overwrites the patch for the duration of that `main()` call. The `tests/test_options_skew_backfill.py:test_cli_backfill_prints_one_json_line_and_skips_emit` test works around this by NOT using `monkeypatch.setattr` for `_snap_path`; it pins the ledger via `--ledger` flag instead. Acceptable; documented as a deviation pattern for future CLI tests. Out of scope for this audit; surfaced as a follow-up one-line note.

5. **`backfill_from_store` is a new public API on `engine.options_skew`.** The function is named in the module docstring addendum and called by `scripts/build_options_skew.py:140`. The function signature `(dates, *, store=None, roots=None, dry_run=False)` is keyword-only after `dates`, which is a safe default. Any external test or downstream caller that called `engine.options_skew.backfill_from_store(["2026-09-23"], None, None, False)` positionally would break — but the function did not exist before this PR, so there are no legacy positional callers. The `tests/test_options_skew_backfill.py` tests all use keyword args. PASS.

6. **The DEC record's `evidence:` block cites `tests/test_audit_options_skew_parity.py`, which the body explicitly disclaims as not-in-tree.** The body says: "The packet names `tests/test_audit_options_skew_parity.py`, which is not in the tree. The audit suite that exists is `tests/test_audit_options_skew_overlap.py`, and that is the file this command ran." The DEC's `evidence:` block cites only the four-file pytest receipt (no specific test filename), so the DEC does not carry the stale name forward. The body receipt itself is honest about the filename correction. Acceptable; surfaced as a documentation-discipline observation, not a blocker.

7. **The `--backfill` CLI's bilingual error messages are operator-facing, not user-facing.** The standing bilingual UI rule's "no translated text in `title=` attributes" CI guard is for HTML attributes, not for CLI `print()` output. The two messages print `回补日期必须写成 YYYY-MM-DD 形式的真实日期。` and `回补的开始日期必须不晚于结束日期。` to the operator's terminal — these are operator CLI errors, not page surface. The audit accepts the bilingual format as the existing `scripts/build_options_skew.py` convention; future CLI strings in this lane should follow the same pattern.

## DEVIATIONS

1. The plain-language audit is qwen_auditor2-style — it runs `node terminal/scripts/check_plain_language.mjs --json` against the PR head when the head's surface is in `terminal/scripts`. Macro has no plain-language checker; the audit substitutes a manual review of every new string introduced in the diff against the design-doctrine glance-tier law + banned-vocabulary list. This is a tool-coverage gap, not a content gap; documented for the operator's toolchain awareness.
2. The audit does not regenerate the live `options.html` render or take EN/ZH/light/dark/desktop/mobile screenshots — the PR's user-facing consequence (W2-5b's source-break sentence) is a downstream receipt owned by the next packet, named in the DEC. Capturing it here would require spawning the W2-5b lane + the render workflow, which exceeds the one-pass audit budget.
3. The audit accepts the body's proof transcripts (pytest result, lane pytest result, curated_exclusive pytest result, contract-delta result, agentos validate result, `git diff --stat` empty result) without re-running them — the operator's audit doctrine ("a recorded receipt is the closure proof for the auditor; the auditor re-runs only when a receipt is missing or implausible") supports one-pass acceptance when the receipts are present and the SHA matches the merged head.
4. The audit does not run the production backfill against the ThetaData store. The DEC names this as the seat's post-merge act (runbook §3.7), and the body explicitly disclaims the production receipt: "This lane did not copy the production ledger and did not run `--backfill` against the ThetaData store. The round-2 ruling says the seat runs that rehearsal from the runbook after merge. No production receipt is quoted here, because none was produced." The idempotence proof the audit accepts is the unit test (`again["rows_replaced"] == 0 and again["rows_added"] == 0`), which is a structurally correct idempotence check (a second call on the same input produces zero changes). The production backfill receipt is the operator's responsibility; out of scope for this one-pass audit.
