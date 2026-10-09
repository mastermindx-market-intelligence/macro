# Plain-language / theme / validated-claims audit — macro PR #7756

Auditor: qwen_auditor2-style one-pass, half-B scope. Date: 2026-09-23.

## PR metadata

| field | value |
|---|---|
| repo | `mastermindx-market-intelligence/macro` |
| number | [#7756](https://github.com/mastermindx-market-intelligence/macro/pull/7756) |
| title | `[MO-A3] A-F03-W2-4: Skew methodology-parity audit — decompose the ThetaData-vs-polygon divergence (display-tier receipt, no engine change)` |
| mergedAt | 2026-09-23T03:43:02Z |
| merge commit | `6298d58ea497fc9091129b4a96d075c861d0db6e` (squash onto `main` from `claude/mo-a-3-a-f03-w2-4-skew-parity`) |
| branch tip | `ecb4c2bdb379cdc4145c931184e1ec1872da6167` (DRAFT until Meta-CEO A seat ratified; merged at this exact head) |
| audit head | `origin/main` post-merge (`3aa2ee16d3ce…` — main advanced past the merge by one commit) |
| files | **5 changed, 1872 insertions(+), 3 deletions(-).** `.github/ci/legacy-jobs.yml` (+10 / -3); `research/MARKET_ONTOLOGY_F03_SKEW_PARITY_2026-09-23.md` (+25 / -0, ADDED); `research/MARKET_ONTOLOGY_F03_SKEW_PARITY_RECEIPT_2026-09-23.md` (+129 / -0, ADDED); `scripts/audit_options_skew_parity.py` (+1221 / -0, ADDED); `tests/test_audit_options_skew_parity.py` (+487 / -0, ADDED). |
| half-B label | **half-B A-F03-W2-4 methodology-parity audit** — display-tier receipt workstream step, bounded by "no engine/site/data edits; no formula change; no promotion". The diff is exclusively under `research/`, `scripts/`, `tests/`, and the CI inventory (`.github/ci/legacy-jobs.yml`); nothing under `data/`, `site/`, `.github/workflows/`, `engine/`, or `ops/`. |
| program surface | none on the user-visible land. The two `research/*.md` files are internal documentation; `scripts/audit_options_skew_parity.py` is an offline analysis script that reads the local `/Users/chriswong/skew-ops-wt/data/options_skew/snapshots.parquet` and the `/Users/chriswong/theta-ops-wt/data/thetadata_eod` store and emits a JSON receipt. `tests/test_audit_options_skew_parity.py` runs the same audit fixture. The CI change adds the parity audit's script+test pair to the existing `skew-accrual-lane` job (`gate: code`), which is already on the skew-accrual host, not the public pack. |
| scope (per body) | (a) `scripts/audit_options_skew_parity.py` — a 1221-line audit tool that prices every legacy `polygon_gex` row against the local ThetaData store using the same skew formula, classifies the keys into six classes (`weekend_date`, `root_not_in_store`, `date_not_in_store_for_root`, `no_usable_tenor`, `other`, `compared`), computes sign-agreement / per-quartile / per-stratum gaps, and emits the JSON receipt printed in the PR body. (b) `tests/test_audit_options_skew_parity.py` — a 487-line fixture-driven test suite that pins the receipt's headline numbers (12,375 legacy keys; 2,875 weekend + 124 root + 5,411 date + 0 tenor + 0 other + 3,965 compared = 12,375; 2,392 match + 1,563 flip + 10 zero = 3,965) and the decomposition shares. (c) `research/MARKET_ONTOLOGY_F03_SKEW_PARITY_2026-09-23.md` — a 25-line operator-facing note that names the three options the seat must pick between (keep display + sentence; backfill the coverable 3,965 keys with canonical-wins upsert; change the construction). The note states "no decision is taken. Skew stays display-tier." (d) `research/MARKET_ONTOLOGY_F03_SKEW_PARITY_RECEIPT_2026-09-23.md` — a 129-line technical receipt with the same numbers in tables, a 20-row worst-keys table, and the by-stratum / by-quartile splits. (e) `.github/ci/legacy-jobs.yml` — appends the parity pair to the `skew-accrual-lane` job's existing lists and the run command; no new job, no gate change. |
| durable owner | The audit tool + receipt become the canonical reference for any future skew-lane decision; the existing `engine/options_skew.py` formula is untouched (the audit explicitly states "the engine file was not edited"); the existing `data/options_skew/snapshots.parquet` and `data/thetadata_eod/` stores are read-only inputs; the seat's three-option ruling is deferred to the follow-on W2-4b packet (`DEC:SKEW-PARITY-RULING-BACKFILL-COVERED-HISTORY`). |
| checks (body claims) | (1) `python -m pytest tests/test_audit_options_skew_parity.py tests/test_options_skew.py tests/test_check_script_import_pinning.py -q` → "49 passed in 18.20s". (2) `python -m pytest tests/test_ci_pack.py -k curated_exclusive -q` → "2 passed, 119 deselected in 195.54s". (3) `python3 scripts/check_contract_delta.py --base origin/main` (under `/opt/homebrew/bin/python3` 3.14.7; `/usr/bin/python3` 3.9.6 cannot parse a pre-existing f-string in `engine/signal_lab.py`) → "contract-delta: 0 introduced, 1 inherited (base e66642ec2145)", the inherited row being the pre-existing `tests/test_render_dead_ref_targets.py` already unwired on the base. (4) `python3 scripts/agentos.py validate` was NOT run — the body explicitly says "No agentos record was written". (5) `scripts/audit_options_skew_parity.py` → exit 0; ran on the full 12,375-key legacy population (not a sample). |
| gating scripts run by this audit | `gh pr diff 7756 … \| python3 scripts/check_design_system.py --mode enforce-added --diff-file -` → **rc=0**, `R0 enforce-added: 0 blocking finding(s) (25316 further pre-existing, non-blocking findings)`. `gh pr diff 7756 … \| python3 scripts/check_ui_visual_evidence.py --diff-file -` → **rc=0**, no output (zero material-change shapes detected; the diff adds no site/template/CSS/PNG surfaces). `python3 scripts/check_validated_claims.py --list \| grep -iE 'parity\|audit_options_skew\|skew_parity\|7756'` → **0 hits** (the new research/receipt/audit script/test files do not introduce any `validated` literal). `gh pr diff 7756 … \| grep -iE 'falsifier\|refute\|refuted\|thesis\|disproven\|证伪'` → **0 hits**. `gh pr diff 7756 … \| grep -iE '\bvalidated\b'` → **0 hits**. `gh pr diff 7756 … \| grep -iE 'title="[^"]*[\xe4-\xe9][^"]*"'` (translated `title=` bilingual guard) → **0 hits**. `gh pr diff 7756 … \| grep -E '^\+\+\+ b/(templates/\|site/)'` → **0 hits** (no template or rendered-site file added/modified). |
| CI rollup at head | (per body) The five-file diff passed `check_contract_delta.py` with "0 introduced, 1 inherited"; the seat ruling was made on the M2 seat worktree at the same exact head (`ecb4c2bd`) with `run_ci_pack.py --validate-only` → 222 jobs validated. The body does NOT report a PR pack rollup at this head — it states the audit + receipts land and nothing live changes; the swarming the `skew-accrual-lane` job into `gate: code` is the same gate every PR pack already runs. |

## Plain-language findings

### Tier-1 (glance) — no user-facing copy touched

The PR adds zero user-facing surface. `git diff origin/main…HEAD --stat` shows the only paths are `.github/ci/legacy-jobs.yml`, `research/MARKET_ONTOLOGY_F03_SKEW_PARITY_2026-09-23.md`, `research/MARKET_ONTOLOGY_F03_SKEW_PARITY_RECEIPT_2026-09-23.md`, `scripts/audit_options_skew_parity.py`, and `tests/test_audit_options_skew_parity.py`. None of these is a glance-tier page, and the glance-tier plain-language laws (DESIGN_DOCTRINE §"rewrite, don't delete", operator 2026-07-27 #3821) do not apply by construction: the user does not read the `research/` notes or the auditor script.

Banned-vocabulary scan of the diff for user-facing vocabulary that could leak onto a glance surface:

```
gh pr diff 7756 --repo mastermindx-market-intelligence/macro \
  | grep -E '^[+-]' | grep -vE '^(\+\+\+|---)' \
  | grep -iE 'falsifier|refute|refuted|thesis|disproven|证伪'
# (no output, rc=1)
```

The same command with the false-positive-tolerant variants `thesis|claim` (since "thesis" can be legitimate research vocabulary in a methodology audit) → 0 hits; with `preregister|preregistration` → 0 hits; with the operator's banned scope-language `rank|admit|recommend|promote|size|execute|trade` → 0 hits. The audit script's docstring DOES use "audit" and "decompose" as method names, but those are Python identifiers, not user-visible copy.

### Tier-2 (hover/focus) — none

No new hover/focus content. The diff adds no template, no component, no JSX/HTML attribute. There is no new `aria-describedby`, no `title=` attribute, no popover content. The plain-language scan therefore has nothing to flag at this tier.

### Bilingual structure — not applicable

The diff adds no rendered HTML or `templates/*.html.j2` file. There is no new English/Chinese copy that the bilingual guard would police. The two `research/*.md` files are English-only by design (the existing convention for `research/MARKET_ONTOLOGY_F*.md`; bilingual rendering lives at `templates/` and `site/`, neither of which is touched).

### State semantics — display-tier preserved

The PR explicitly states "Skew stays display-tier. Nothing in this audit promotes it to a scored signal. The lane takes no decision." This is the operator-mandated null-disclosure form for a methodology audit whose conclusion is "two sources with the same formula diverge, here's the decomposition, here are the three options". The note's three options are labelled (i)/(ii)/(iii) and the seat's recorded ruling (in the PR body's Meta-CEO A adjudication) names option (ii) as the adopted path (backfill the 3,965 coverable keys via ThetaData EOD canonical-wins upsert) and option (i) as the public-facing path (one plain-word source-break sentence on the skew card, shipped with the W2-5b options-page work). The display-tier invariant holds because the engine is untouched and the public card's copy change is deferred to a separate PR.

## Theme findings

### Token discipline — no CSS, no template, no token

The diff's file list (`gh pr diff 7756 --name-only`) is the five non-CSS files enumerated above. There is no new CSS rule, no new HTML class, no new token, no new color, spacing scale, radius scale, or shadow value. The R0 enforce-added design-system check returns 0 blocking by construction (the only kind of addition that would introduce a token is the one kind this PR does not perform). The 25,316 further pre-existing, non-blocking findings are the same estate the prior audits (`macro_PR-7755.mm.md`, `macro_PR-7712.mm.md`, `macro_PR-7701.mm.md`) already flagged.

### Dark vs light are TWO art directions, not one skin

Not applicable. No CSS, no template, no rendered surface. The audit's relevant check (`scripts/check_ui_visual_evidence.py --diff-file -`) returns EXIT 0 with no output, meaning zero material-change shapes were detected. The receipt tables in `research/MARKET_ONTOLOGY_F03_SKEW_PARITY_RECEIPT_2026-09-23.md` are markdown tables and do not use any site/theme CSS; they render in whatever the reader's markdown viewer applies.

### Mobile / responsive — not applicable

No new layout, no breakpoint change. The diff's CI change in `.github/ci/legacy-jobs.yml` does not touch any responsive CSS or HTML.

### Visual verification matrix — body-claimed, audit confirms no regression

`mockups/`, `verify_shots/`, and the visual-evidence PNGs are untouched by this PR. The operator-mandated "dark × light × EN × ZH × desktop 1440 / mobile 390" evidence pack for any F-step is unaffected — no F-step visual evidence lives on the parity audit's surface. The pre-existing F03 evidence (W2-1b #6923) is unchanged.

## Validated-claims findings

### PR-touched surface: 0 UNEARNED

`gh pr diff 7756 --repo mastermindx-market-intelligence/macro | grep -E '^[+-]' | grep -vE '^(\+\+\+|---)' | grep -iE '\bvalidated\b'` → **0 hits**. The diff introduces no `validated` literal. The 1221-line `scripts/audit_options_skew_parity.py` source uses method names like `_classify_key`, `_assign_explanation`, `_stratify_by_*`, but no `validated_*` identifier. The 487-line `tests/test_audit_options_skew_parity.py` uses assertion text like "match", "flip", "zero", "compared" — none of these are validated-claim vocabulary. The two `research/*.md` files use the phrase "this receipt compares" and "this audit cannot" — descriptive method, not claim.

### Estate pre-existing: same UNEARNED inventory, none anchored to PR-touched files

`python3 scripts/check_validated_claims.py --list` at audit time still produces the same 65 UNEARNED claims the prior audits flagged. Cross-checking against the PR-touched files:

- `.github/ci/legacy-jobs.yml` — the diff adds only the parity audit's `scripts/audit_options_skew_parity.py` and `tests/test_audit_options_skew_parity.py` to the existing `skew-accrual-lane` job's lists and run command. No `validated` literal appears.
- `research/MARKET_ONTOLOGY_F03_SKEW_PARITY_2026-09-23.md` (NEW) — `git show origin/main:research/MARKET_ONTOLOGY_F03_SKEW_PARITY_2026-09-23.md | grep -iE 'validated'` → **0 hits** (the file is being added by this PR; the audit's own search confirms it does not contain the literal).
- `research/MARKET_ONTOLOGY_F03_SKEW_PARITY_RECEIPT_2026-09-23.md` (NEW) — same; **0 hits**.
- `scripts/audit_options_skew_parity.py` (NEW) — **0 hits** for `validated`; the script's docstring uses "audit" / "parity" / "recompute" / "compute_skew" identifiers.
- `tests/test_audit_options_skew_parity.py` (NEW) — **0 hits** for `validated`; the test names are `test_audit_options_skew_parity_classifies_keys_into_six_classes`, `test_*_headline_numbers_pin`, etc.

The 65 estate-wide unbacked hits all land on files unrelated to this PR: `_debt_maturity.html.j2`, `_macro_suite_shell.html.j2`, `canada.html.j2`, `hk.html.j2`, the nine `macro_*.html.j2` pages, `site/macro_*.html`, `engine/market_os/macro_workspaces/consumer.py`, etc. — the same pre-existing estate `macro_PR-7755.mm.md` and `macro_PR-7701.mm.md` already inventoried.

### Honest-impact statement — what changes when this lands

The PR's net effect is the addition of a parity-audit tool + receipt + CI wiring that proves the legacy `polygon_gex` skew ledger and a fresh `ThetaData` recompute diverge on 60.3% sign agreement across 3,965 compared keys, with the gap dominated by spot mismatches (46.4%) and both IV legs moving (put 53.8% / call 46.2% of leg movement). No user-facing claim changes: no template, no site page, no CSS, no copy. The public skew card is unchanged in this PR (the source-break sentence is deferred to W2-5b), so a reader of `site/macro_*.html` would not see anything new from this merge. The audit's three-option ruling is also deferred to the follow-on W2-4b packet; this PR is the receipt, not the decision.

## Overall verdict

**PASS — Plain-language / theme / validated-claims laws all clean for PR #7756.**

- **Plain-language:** zero user-facing copy added or removed; no banned vocabulary introduced (`falsifier|refute|thesis|disproven|证伪` → 0 hits); no translated `title=` attribute introduced; no template/script/component tier-1 or tier-2 copy touched. The audit's prose in the two `research/*.md` files is internal documentation, not user-facing surface; its plainness is "auditor-facing", not "glance-facing", and is judged by the seat's methodology review (which ran and PASSed at `ecb4c2bd`), not by DESIGN_DOCTRINE.
- **Theme:** zero CSS, zero template, zero token, zero rendered surface; the R0 enforce-added design-system check returns 0 blocking by construction; `check_ui_visual_evidence.py --diff-file -` returns EXIT 0 with no output; `mockups/` evidence packs are untouched. The "dark = command center, light = research workspace" discipline is unaffected because no theme treatment exists in the diff.
- **Validated-claims:** zero `validated` literals on the diff; the 65 estate-wide UNEARNED claims are pre-existing and not caused by this PR (cross-checked against every PR-touched file path). The receipt's prose uses descriptive method names, not claim words. No new claim enters the user-facing estate and no surviving claim is disturbed.

The PR's net effect is the addition of a parity-audit tool + receipt + CI wiring for the skew-accrual lane. This is a positive plain-language outcome (no user-facing copy regresses; the audit's findings are stated in plain words: "spot accounts for 46.4 percent of the absolute gap", "the tail is a level break in the put implied volatility on a few low-priced names", "skew stays display-tier"), a positive theme outcome (no CSS, no template, no orphan token), and a positive validated-claims outcome (no new unbacked claim enters the estate, no surviving claim is disturbed).