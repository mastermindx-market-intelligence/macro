# Healthcare D1 — seat rulings at the merge window (2026-09-26)

Program `gmi-theme-graph` · operation `gmi-healthcare-fable-ceo-e2e-20260924-chairman-001` · research carrier #7788 · implementation carrier PR #7930 (`claude/healthcare-d1-fda-supply`).

D1 was accepted by an exact-head independent Opus review at `9abf409a` on 2026-09-24 20:50Z and the PR was flipped READY with `merge-on-green`. It did not merge. Two days later the seat re-opened the carrier and found two things — both recorded here because both are the kind of thing a later session would otherwise re-diagnose from scratch.

## Finding 1 — the carrier was CONFLICTING, not red

`gh pr view 7930` reported `mergeable: CONFLICTING`, `mergeStateStatus: DIRTY`. The `merge-on-green` sweeper was healthy throughout (runs minutes apart) and had correctly refused: it cannot resolve a conflict. It left **no `merge-blocked` label and no comment**, so the PR's outward state was "armed, no new red, nothing said" — which reads like a broken sweeper and is not one.

**R-D1-MERGE-00.** An armed PR that is neither merged nor labelled `merge-blocked` must be read for `mergeable`/`mergeStateStatus` before the sweeper is suspected. A conflict is silent.

The conflict was exactly one file: `tests/test_ci_pack.py`, in the `CURATED_EXCLUSIVE` registry, where the GMI Mining program had registered `mining-economic-dossier` at the same position this carrier registers `healthcare-fda-supply`. Two additive registrations of a shared list — resolved additively, main's text kept verbatim and the healthcare block appended after it (merge commit `f9258b0d`). No D1-owned product or test file moved in the merge: `git diff 9abf409a HEAD` over the D1 file set shows only `.github/ci/legacy-jobs.yml` and `tests/test_ci_pack.py`, both of which grew on main.

## Finding 2 — an accepted suite can rot while the PR waits

Re-running the job's eight suites on the merged head produced one failure that had nothing to do with main:

```
test_failed_refresh_discloses_the_retained_qualified_capture
- FDA shortage: current (1) · captured 32 d ago · …
+ FDA shortage: current (1) · captured 34 d ago · …
```

The test drives the chip through `compute_fda_scarcity`, which reads `datetime.now(timezone.utc)` and passes `max_capture_age=None` (R-T01-12: no invented capture-age limit). Its fixture, though, was pinned to a fixed calendar date (`2026-09-23`) and offset 31 days, while the assertion named a fixed `32 d ago`. Age was therefore measured against the *real* clock and constructed against a *frozen* one: the label gains a day every day, so the assertion could only ever pass on the day it was written. It passed for every reviewer because every review ran on that day.

**R-D1-MERGE-01.** A test that asserts an age rendered against the wall clock must anchor its fixture to that same clock. Fixing the expected number to a calendar date is a time bomb, not a pin.

Repair (seat commit `4a6cf768`): the fixture derives from the same call the product makes, so the asserted age is the fixture's own offset (31 d) for any wall clock. Nothing under test moved — the capture is still a retained qualified capture whose refresh failed, `source_status` stays `CURRENT_REPORTED`, `tone` stays `warn`, and the two absolute facts in the label (`source generation 2026-08-20`, `refresh failed 2026-09-22`) are echoed from the fixture rather than computed against now. The wall-clock path carries no age threshold at all, so 31 vs 32 days changes only the rendered count. **The six frozen probe files were not touched.**

Scope of the rot: exactly this one test. Every other age assertion in the eight suites injects `now` into `summarize_supply`, which the +2-day re-run proves — an absolute-anchored age assertion anywhere else would have drifted by the same two days and failed with it.

## Finding 3 — a translation-only edit reds a DESIGN gate

The repaired head `4a6cf768` came back with the packs concluded and exactly one red that was ours: `ci-pack-8` → the required `ci-gate`.

```
##[error]R0 enforce-added: 1 blocking finding(s) on line(s) added by this diff
          (25430 further pre-existing, non-blocking finding(s) in the estate)
##[error]templates/foresight.html.j2:581 [emoji] emoji U+1F48A
##[error]design-governance: step 'forward-only design ratchet' exited 1
CI_PACK_FAILED_JOBS=["design-governance"]
```

`healthcare-fda-supply` sits in pack **9**, which passed — the D1 suites were green in CI. Pack 8's red was the design ratchet, and the whole of this PR's diff against main on that template is one line: the chip's label gained its ZH half, `{{ tfs.label }}` → `{{ t(tfs.label, tfs.label_zh) }}`. The 💊 on that line is years-old estate debt. `--mode enforce-added` scores the lines a diff ADDS, so touching a line for an unrelated reason re-presents its inherited glyph as a newly-added forbidden decision — which is why 25,430 sibling findings stayed silent and this one did not.

**R-D1-MERGE-02.** An adopted-debt finding is repaired by moving to the *sanctioned kind*, not by deleting the offending element. Stripping a glyph to satisfy a lint removes meaning from the product; a waiver spends governance on a self-inflicted red. The ratchet reports a wider band than it blocks on purpose, and that gap is the repair path.

Repair (seat commit `871b6d36`): 💊 U+1F48A → **⚕ U+2695**, one glyph, nothing else. `EMOJI_BLOCKING_RE` blocks only the pictographic planes (U+1F300–1FAFF, U+1F900–1F9FF); Misc Symbols + Dingbats (U+2600–27BF) are left as ordinary typography by design, documented in `_emoji_finding_is_narrowly_blocking`'s own docstring. This very chip row already ships ⚖ U+2696, ⚠ U+26A0 and ⚑ U+2691 out of that block, so ⚕ — the medical member of the family, one code point from the ⚖ beside it — is both lawful and house-idiomatic. No U+FE0F was added: a variation selector re-requests colour presentation and is itself in the reported band.

It is additionally the better design under the theme art-direction law. ⚕ is monochrome, so it inherits the chip's own text colour and reads correctly in both the dark command-center and the light research-workspace treatment; a colour emoji is theme-blind by construction and was never a light-theme decision at all. Nothing but the glyph changed — no test, engine module or fixture references it (`templates/foresight.html.j2` is the only file in the repo that contains it), the label semantics, tone class, `title=` rationale and D1 banned-substring surface are untouched, and no ranking, entry, sizing or trading policy is involved.

Recorded as `DSC:A-DESIGN-RATCHET-REPORTS-WIDER-THAN-IT-BLOCKS`.

## Finding 4 — the probes never met the real feed

With the gates green, the seat did the one check no review round had done: ran the **committed production feed** through this PR's engine, in the exact state main is in immediately after the merge — `data/fda/shortages.parquet` at origin/main `5e921b1c` (1,787 rows), observation sidecar not yet written, so `_selected_state` returns `legacy=True` / `capture=None`. The live composition is **current=9, resolved=0, discontinued=5**, and the accepted head rendered:

```
FDA: mixed — current 9 / resolved 0 · capture time unknown
FDA：混合——当前9／已解决0 · 采集时间未知
title="The FDA reports both current and resolved shortages."
```

Three untruths in one chip: it asserts resolved shortages that do not exist, prints `resolved 0` beside the word "mixed", and hides five formulation discontinuations — the single distinction this program's semantics law exists to make. One merge away from replacing main's banned "demand exceeds supply" with a different untruth.

`summarize_supply` selects MIXED for `current and (resolved or discontinued)`, but the label template and the rationale both hard-coded "resolved" as the second component. Every MIXED test in the eight gated suites builds its mixture from current + resolved, so the `discontinued` disjunct was never exercised. The code was never right here; it was only ever green — through six adversarial Opus rounds and an exact-head ACCEPT.

**R-D1-MERGE-03.** A status selected by a disjunction must have its copy checked against every disjunct, and a data-driven consumer must be rendered from the committed production artifact before it merges. Never name a regulator state whose count is zero; never omit one whose count is non-zero.

Repair (seat commit `5f7ae25c`), display only: `_label` and `_chip_rationale` enumerate the non-zero components.

| composition | label | rationale |
|---|---|---|
| current + resolved | `FDA: mixed — current 1 / resolved 1` — **unchanged** | "…both current and resolved shortages." — unchanged |
| current + discontinued | `FDA: mixed — current 9 / discontinued 5` | "…current shortages and formulation discontinuations." |
| all three | `FDA: mixed — current 9 / resolved 2 / discontinued 5` | "…current shortages, resolved shortages and formulation discontinuations." |

The current+resolved rendering is byte-identical to before, so the only behaviour that moved is the behaviour that was false. `source_status`, `band`, `tone` and every count are untouched; the chip stays display-only; no ranking, entry, sizing or trading policy is involved.

New seat-frozen probe `tests/test_fda_supply_probes_mixed.py` (5 tests) pins the law and is proven falsifying — 3 of 5 fail at `871b6d36`, all 5 pass at `5f7ae25c`; the two that pass on both sides are the regression guards. It drives the injectable `summarize_supply` seam with an explicit `now`, per R-D1-MERGE-01. Wired into `healthcare-fda-supply` inside the job block (probe pytest step + `paths:` 34 → 35, `if: ${{ false }}` intact, name appears exactly twice in `legacy-jobs.yml`).

Recorded as `DSC:A-SYNTHETIC-FIXTURES-NEVER-REACHED-THE-BRANCH-THE-LIVE-FEED-TAKES`, which also carries the reusable ten-line technique for rendering a committed production artifact from a sparse worktree.

## Verification at `4a6cf768`

| Check | Result |
|---|---|
| job's eight suites | `127 passed` — probes 14+8+6+1+7+4 = 40, generation 25, cascade 62 (identical counts to the accepted head; with `test_policy_calendar.py`'s 8 this is the same 135 the acceptance review recorded) |
| `run_ci_pack.py --validate-only` | exit 0, 236 legacy jobs validated, `healthcare-fda-supply` in scope |
| `tests/test_ci_pack.py -k "exclusive or curated or contract or legacy_jobs"` | see README checkpoint line for this head |
| `check_contract_delta.py --base origin/main` | see README checkpoint line for this head |
| frozen probe authorship | unchanged; seat only |

No ranking, entry, sizing or trading policy changed; no `data/` or `site/` write; protected research untouched.

## Verification at `871b6d36` (final head)

| Check | Result |
|---|---|
| `check_design_system.py --mode enforce-added --diff-file <full 9,374-line PR diff>` | `R0 enforce-added: 0 blocking finding(s)` — exit 0 (was 1 blocking at `4a6cf768`) |
| design-governance's own four unit suites (`test_check_design_system`, `test_check_runtime_style_injection`, `test_check_ui_visual_evidence`, `test_freshness_chips_language_invariant`) | `190 passed, 2 skipped` |
| all three guard selftests (`--self-check`, `--selftest`, `--selftest`) | OK |
| job's eight suites | `127 passed` — unchanged from `4a6cf768`; the glyph is referenced by no test |
| glyph census | `templates/foresight.html.j2` is the only file in the repo containing ⚕, as it was the only one containing 💊 |

The one step that cannot be reproduced in this carrier is `check_runtime_style_injection.py`'s non-selftest ratchet, which REFUSES on a sparse worktree (`site/` not checked out) rather than printing a false pass. That step had already concluded green in CI at `4a6cf768`, and this head touches no JavaScript.

## Verification at `5f7ae25c` (final head)

| Check | Result |
|---|---|
| the job's suites, now nine | `132 passed` (was 127; +5 new probes, no existing assertion moved) |
| CI's own ratchet command reproduced exactly (`git diff --unified=0 $(git merge-base origin/main HEAD) HEAD -- templates` → `--mode enforce-added`) | 7-line diff, `0 blocking finding(s)`, exit 0 |
| `run_ci_pack.py --validate-only` | 236 legacy jobs validated |
| live feed re-rendered through the patched engine | `FDA: mixed — current 9 / discontinued 5` / `FDA：混合——当前9／停产5`, title "The FDA reports current shortages and formulation discontinuations." |
| probe falsifiability | 3/5 RED at `871b6d36`, 5/5 GREEN at `5f7ae25c` |
