# OPUS D1 ACCEPTANCE — PR #7930 @ 9abf409af678b1ee79fd2e2a70b21448ba8a1ba1

MODE: READ_ONLY. No repo file edited, no `data/`/`site/` write, no branch op.
Probe: `.../scratchpad/review/accept_scratch/test_acc.py` (independent of the seat's file).

## VERDICT

**ACCEPT @ 9abf409a** — 0 blockers, 0 majors, 3 minors.

All three predecessor blockers (D1F-B1/B2/B3) and M1 are repaired at the seam, not at the
unit. My independently authored truth path drives `collect_shortage_sweep →
save_shortage_observation → read_shortage_observation → compute_fda_scarcity →
format_theme_feed_chip → _compute_tier` off real on-disk state and is clean at every step:
five distinct truths, five distinct label pairs, one tier.

Root-cause repair confirmed: `engine/fda_scarcity.py:289-296` now computes `qualified`
and `engine/fda_scarcity.py:319` stamps `capture["qualified"]`/`capture["observation_state"]`,
so `summarize_supply`'s `if qualified is False: source_status = _UNAVAILABLE` (`:226`) is
reachable from the production read path for the first time.

## DELTA FOOTPRINT 28b986d4de69 → 9abf409a

5 files, +441 / −30:

| file | lines |
|---|---|
| `engine/fda_scarcity.py` | +75/−? (state machine, label branches, rationale, casefold) |
| `tests/test_foresight_cascade.py` | +152 |
| `tests/test_fda_supply_probes_final.py` | +234 (new; seat-authored) |
| `.github/ci/legacy-jobs.yml` | +4/−2 (probe file + `templates/foresight.html.j2` wired into `healthcare-fda-supply`) |
| `tests/test_fda_supply_probes_t02r2.py` | +3/−3 |

**Correction to the commission's premise — a frozen probe file DID change in this delta.**
`tests/test_fda_supply_probes_t02r2.py:289-292` moved from
`assert marks["T02R2-B"] is None or marks["T02R2-B"] != marks["T02R2-A"]` to
`assert marks["T02R2-B"] is None`. The new accepted set is a strict subset of the old one,
so the amendment is a **strengthening**, freezes no defect, and is lawful — but the claim
"no probe file changed" is inaccurate as stated. No other probe file moved.

CI wiring verified: `.github/ci/legacy-jobs.yml:13497` adds the probe file to `paths`,
`:13536` adds it to the acceptance-probe run line, `:13503` adds `templates/foresight.html.j2`
to `paths` (the T01 template change now triggers its own job).

## END-TO-END TRUTH TABLE (re-executed at 9abf409a, real seams, synthetic molecule `zetamide`)

| # | step | label EN | label ZH | rationale | tone | source_status | tier | capture_qualified |
|---|---|---|---|---|---|---|---|---|
| 1 | cold start (no parquet, no sidecar) | `FDA source not yet observed — no qualified generation on file` | `FDA来源尚未观测——无合格来源生成日期` | The FDA source is unavailable. | mute | `UNAVAILABLE` | P | `False` |
| 2 | qualified sweep, 1 Current row, gen 2026-09-23 | `FDA shortage: current (1) · captured 0 d ago · source generation 2026-09-23` | `FDA短缺：当前（1） · 采集于0天前 · 来源生成日期2026-09-23` | The FDA reports a current shortage for this theme. | warn | `CURRENT_REPORTED` | P | `True` |
| 3 | failed refresh `FIRST_PAGE_OUTAGE` over #2 | `FDA shortage: current (1) · captured 0 d ago · source generation 2026-09-23 · refresh failed 2026-09-24` | `FDA短缺：当前（1） · 采集于0天前 · 来源生成日期2026-09-23 · 刷新失败 2026-09-24` | The FDA reports a current shortage for this theme. | warn | `CURRENT_REPORTED` | P | `True` |
| 4 | generation-less page over #3 | identical to #3 | identical to #3 | same | warn | `CURRENT_REPORTED` (sweep refused `NO_SOURCE_GENERATION`, `promoted=False`, generation NOT overwritten) | P | `True` |
| 5 | torn pair (parquet digest ≠ sidecar) | `FDA source unavailable — last observation unreadable` | `FDA来源不可用——上次观测无法读取` | The FDA source is unavailable. | mute | `UNAVAILABLE` | P | `False` |
| 6a | legacy cache, non-empty parquet, no sidecar | `FDA shortage: current (1) · capture time unknown` | `FDA短缺：当前（1） · 采集时间未知` | The FDA reports a current shortage for this theme. | warn | `CURRENT_REPORTED` | P | `None` |
| 6b | legacy cache, empty parquet, no sidecar | `FDA: no matching records · capture time unknown` | `FDA：无匹配记录 · 采集时间未知` | No FDA records match this configured theme. | mute | `NO_MATCHING_RECORDS` | P | `None` |

Assertions that held across all rows: no literal `None`, no `nan`, none of
`glut / tell / all-clear / catching up / demand exceeds supply / supply constraint lifted`;
`label != label_zh` (EN/ZH both authored); `rationale.isascii()` (title-attribute law);
**tier `P` identical at every step** (display-only chip, `assert len(tiers) == 1` passed);
and the three previously-colliding states now render three different labels
(`cold != torn`, `refresh-failed != torn`).

Repairs confirmed against the predecessor's findings:
* **D1F-B1** — torn pair is now `UNAVAILABLE / "last observation unreadable"`, not
  `NO_MATCHING_RECORDS`. Gated by `engine/fda_scarcity.py:201` (`observation_state != "UNREADABLE"`
  blocks the retained-evidence re-promotion) and `:308` (`if observation.get("inconsistent"): UNREADABLE`).
* **D1F-B2** — cold start is now `UNAVAILABLE / "not yet observed — no qualified generation on file"`.
  `engine/fda_scarcity.py:312` `elif not last_refresh: "LEGACY" if capture else "NOT_OBSERVED"`.
* **D1F-B3** — the happy path no longer suffixes `capture time unknown`;
  `freshness.capture_qualified is True` (row 2).
* The `refresh failed <date>` suffix is correctly suppressed on `_UNAVAILABLE`
  (`:166-168`), so the unreadable label does not double-state a refresh it never reached.

## GLM MINOR — VERDICT: **NOT CONFIRMED AS DESCRIBED; downgraded to m2 (dead branch)**

The lane reviewer's claim was "an EMPTY legacy parquet maps to `LEGACY` but a NON-EMPTY
legacy parquet maps to `UNREADABLE`". Measured, that split does not exist. Rows 6a/6b above:
**both** readable legacy parquets (empty and non-empty) resolve to `LEGACY`.

The ternary the reviewer pointed at —
`engine/fda_scarcity.py:309`: `observation_state = "LEGACY" if frame is not None else "UNREADABLE"` —
has an **unreachable else-branch**, for two independent reasons:
1. `collectors/fda_shortages.py:308-323` returns `legacy=True` with `rows=None` **only** when
   the parquet fails to parse (`:314-316`), which also sets `inconsistent=True`; and
   `engine/fda_scarcity.py:307` tests `inconsistent` **first**, so that case never reaches `:309`.
2. The `df`-attrs path cannot supply `frame=None`, because
   `collectors/fda_shortages.py:574-575` (`_frame_attrs`) returns `None` when `frame is None`,
   so `df.attrs["fda_observation"]` only exists when a frame exists.

No false claim is rendered on either legacy branch. `LEGACY` deliberately demotes
`qualified` to `None` (`engine/fda_scarcity.py:188-189`), which suppresses the `_UNAVAILABLE`
door and appends `capture time unknown` / `采集时间未知` in both languages while reporting
`freshness.capture_qualified: null`. Row 6b's `no matching records` is therefore a
disclosed-undated read of a real artifact that genuinely holds zero rows — truthful with
disclosure, not the qualified-read claim the law reserves — and the behaviour is
deliberately pinned by the builder's own
`tests/test_foresight_cascade.py::test_observation_states_render_distinct_unavailable_truths`
(`capture_qualified is None`, `"capture time unknown" in chip["label"]`, `band == "SHORTAGE_ACTIVE"`).
Residue is the dead branch only (m2).

## FINDINGS

### m1 (minor) — a sidecar without `parquet_sha256` renders a *qualified* read that never happened
`engine/fda_scarcity.py:304-318` has no `frame is None` guard outside the `legacy` branch.
Failing input: a valid receipt carrying `selected_capture` but no `parquet_sha256`.
`collectors/fda_shortages.py:338` (`if expected is not None and path.exists() and not inconsistent`)
then leaves `rows=None` with `inconsistent=False`, and `:346` still returns the capture.
Measured state: `rows_is_none=True inconsistent=False capture=True`.
Wrong output: `NO_MATCHING_RECORDS`, label
`FDA: no matching records · captured 0 d ago · source generation 2026-09-23`,
rationale `No FDA records match this configured theme.`, `freshness.capture_qualified: True`
— i.e. the parquet was never opened, yet the chip asserts a fully-qualified read that
matched nothing, indistinguishable from a real empty observation.
Law broken: "`no matching records` is only for a qualified read that matched nothing."
RED probe: `test_acc.py::test_sidecar_without_parquet_digest_drops_rows`.
**Why minor, not blocking:** the shipped writer always stamps the digest on promotion
(`collectors/fda_shortages.py:489`), and the failed-refresh writer only propagates what it
was given (`:555`), so a clean-start production store cannot reach this shape. It is a
defensive gap, not a demonstrated production falsehood — but note that
`collectors/fda_shortages.py:535` (`if existing.get("parquet_sha256") is None and unselected_rows:`)
shows the codebase itself already anticipates a null digest, and the engine's behaviour in
that state is the most confident possible falsehood rather than a degradation. One
condition (`frame is None → UNREADABLE`) closes it. Records note for the next round.

### m2 (minor) — unreachable `else` in the legacy state branch
`engine/fda_scarcity.py:309`. See GLM MINOR above. Reads as a live guard, is dead code;
the honest guard it appears to be would be the one m1 asks for.

### m3 (minor) — one tooltip now serves four unavailable sub-states, plus a dead `read_error` branch
`engine/fda_scarcity.py:440` collapsed `_UNAVAILABLE`'s rationale from
`"The FDA source is unavailable after a failed refresh."` to `"The FDA source is unavailable."`.
That change is **correct** — the old sentence was false for `NOT_OBSERVED` and `UNREADABLE` —
but discrimination now lives only in the label, so the hover tooltip no longer distinguishes
not-observed from unreadable from refresh-failed. Separately,
`engine/fda_scarcity.py:322-323` reads `observation["read_error"]`, a key
`_selected_state` never returns on any of its four return paths
(`collectors/fda_shortages.py:300/317/328/344`) — dead.

## NON-FINDINGS CHECKED AND CLEARED

* **`molecule.casefold()`** (`engine/fda_scarcity.py:373-374`): all 3 `MOLECULE_THEME_MAP`
  keys are already lowercase (measured), so the change is a behavioural no-op today and a
  correctness improvement for any future capitalised key. Not a widened-match risk.
* **Builder cascade tests (+152), passing-by-construction sweep:**
  `assert chip["band"] == "NONE" if state_name != "LEGACY" else chip["band"] == "SHORTAGE_ACTIVE"`
  parses as `assert (X if C else Y)` — ugly but semantically correct, not vacuous. The rest
  pin exact EN **and** ZH literals, `capture_qualified` identity (`is True/False/None`),
  `tone`, `band` and `tier == baseline` per state; they compare against literals, not
  against the implementation's own output. No tautology found.
* **Theme art-direction law:** the delta contains zero CSS, zero JS, no runtime stylesheet,
  no new component. The T01 template change is one expression inside the pre-existing
  `fx-chip feed-{{ tone }}` span, swapping `{{ tfs.label }}` for `{{ t(tfs.label, tfs.label_zh) }}`
  — an EN/ZH parity fix using the template's own bilingual macro. Not a material UI packet;
  the predecessor's adjudication stands. (Unchanged proportionate ask: one 390px ZH glance,
  since rows 1/5 now emit ZH strings materially longer than the EN they replace.)

## SUITES RUN AT THIS HEAD

`tests/test_fda_supply_probes.py`, `_t02r`, `_t02r2`, `_t01r`, `_t02r3`, `_final`,
`tests/test_foresight_cascade.py`, `tests/test_fda_shortages_generation.py`
→ **127 passed in 6.36s** (PYTHONPATH=worktree, `-p no:cacheprovider`).
Independent probe `test_acc.py` → `test_truth_path` and `test_legacy_nonempty_parquet` GREEN;
`test_legacy_empty_parquet` and `test_sidecar_without_parquet_digest_drops_rows` RED by
design as the evidence for m2/m1 (both adjudicated non-blocking above).
