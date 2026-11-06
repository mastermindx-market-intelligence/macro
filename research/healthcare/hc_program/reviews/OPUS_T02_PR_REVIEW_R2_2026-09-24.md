# Opus adversarial review R2 — PR #7930, Healthcare D1 T02
Exact head: `8d858bba8ef1d12c2ee8985933947bb853088788` (branch `claude/healthcare-d1-fda-supply`)
Mode: READ_ONLY. Probes: `scratchpad/review/test_fda_supply_probes_t02r2.py` (6 tests, all RED at this head).

## VERDICT

**REJECT @8d858bba.** 2 blockers, 4 majors, 2 minors. The repair round-1 items (B1–B5/M1/M2/N1) are
genuinely green and I found no new failing input against them. The defects below are all NEW surface:
the drip receipt this PR adds to `scripts/build_foresight.py` can never report a failure code, and a
failed metadata write destroys the selected observation rather than declining to promote it. Both are
pinned as expected behaviour by the builder-authored suite, so the suite is co-varying on exactly the
two blockers — a green `healthcare-fda-supply` job is not evidence here.

## GLM CLAIM ADJUDICATION

- **GLM-B1 (receipt reads `capture.failure_code`) — CONFIRMED (blocker, T02R2-B1).**
  `collectors/fda_shortages.py:260` `f"failure_code={capture.get('failure_code') or 'none'} "`.
  `capture` is the sidecar's `selected_capture` (`:310`), and the capture dict built by the sweep
  (`:213-226`) has **no `failure_code` key at all** — the code lives at the result top level (`:118`)
  and is persisted at `:455` under `last_refresh.failure_code`. The field is dead: it prints `none`
  for every state that can exist. GLM understated it — this is not "sometimes wrong", it is
  unconditionally wrong.
- **GLM-M1 (parquet promoted before the sidecar) — CONFIRMED and UPGRADED to blocker (T02R2-B2).**
  Detection is real (`inconsistent=True`) but **not sufficient**, because the failure mode is
  destructive, not merely non-promoting: after `METADATA_WRITE_FAILED` the reader returns
  `rows=None` **and** `capture=None` (`:300-310`), so the previously selected qualified observation
  is unreadable, and the next qualified save restarts from `_empty_history_frame()` (`:348-350`),
  resetting `first_observed_generation` / `absent_since_generation` / `generations_seen` and with them
  the 90-generation retention clock. The seat's prior asked whether the ORDER is a defect: **yes** —
  the law says a partial acquisition is never promoted, not that a complete acquisition may delete the
  last good one.
- **GLM-M2 (unrelated `glut_watch.py` churn) — CONFIRMED as fact, DOWNGRADED to minor, direction
  corrected (T02R2-m1).** See YML HYGIENE. GLM says the entries "move alphabetically"; they move the
  other way — the PR **breaks** sort order in three unrelated jobs. No behavioural effect (a `paths:`
  list is a match set), so minor, but revert it.
- **GLM-m1 (only six upstream fields type-checked) — CONFIRMED, re-scoped, raised to major
  (T02R2-M1).** GLM's mechanism is wrong: every other field in `_parse_record` **is** guarded
  (`:89` `isinstance(brands, list)`, `:91`, `:92`, `:93`, `:94`), so no other *field value* raises a
  TypeError. The real hole is the **container**: `:73-74`
  `openfda = rec.get("openfda") or {}` / `brands = openfda.get("brand_name") or []` — a truthy
  non-dict `openfda` (list / str / int) raises **AttributeError**, which the sweep's
  `except (TypeError, ValueError)` at `:182` does not catch, so `collect_shortage_sweep` **raises**
  instead of returning `MALFORMED_ROW`.

## FINDINGS

### T02R2-B1 — blocker — the drip receipt can never name a failure code
`collectors/fda_shortages.py:253-265`; consumed at `scripts/build_foresight.py:116`.
Input: one qualified save at generation `2026-09-23`, then a refresh whose first page raises
(`FIRST_PAGE_OUTAGE`), saved to the same pair. `last_refresh.failure_code == "FIRST_PAGE_OUTAGE"` on
disk. Output:
`fda_shortages: observation qualified=True failure_code=none source_generation=2026-09-23 last_refresh=2026-09-24T12:00:03+00:00 legacy=False inconsistent=False`
Law broken: *complete-empty ≠ failed ≠ stale ≠ unrecognized*. A total upstream outage is
byte-indistinguishable from a clean refresh except for a timestamp the operator must diff by hand,
and the line affirmatively says `qualified=True`.
Co-varying test: `tests/test_fda_shortages_generation.py:481-484` asserts the literal
`"...qualified=False failure_code=none..."` for what it calls the "failed" case — but that case is
`read_shortage_observation(path=tmp_path / "missing.parquet")`, a cold start that legitimately has no
failure code (`:481`). No test in the PR ever formats a state whose `last_refresh.failure_code` is
set, so the suite pins the defect instead of catching it.
Probe: `test_t02r2_drip_receipt_names_the_failure_code_of_a_failed_refresh` — RED.

### T02R2-B2 — blocker — a failed sidecar write destroys the selected observation
`collectors/fda_shortages.py:409-411` (`_write_staged(path, write_parquet)`) runs before the receipt
is serialised (`:438`) and staged (`:445`).
Input: qualified save at `2026-09-23` (1 row); make the sidecar's staged target unwritable; qualified
save at `2026-09-24` (2 rows). Output: `promoted=False`, `reason=METADATA_WRITE_FAILED` — and
`read_shortage_observation(path=path)` then returns `inconsistent=True`, `rows=None`, `capture=None`.
The 2026-09-23 observation, which was never superseded, is gone.
Laws broken: *the last qualified observation survives a failed refresh* (the module's own docstring,
`:498`), *retention keeps absent rows 90 distinct generations, never drops a present row* (the
history frame the next save inherits is empty, so every absence marker and the generation ledger are
lost), and the fail-safe framing of *partial acquisition never promoted*.
Co-varying test: `tests/test_fda_shortages_generation.py:339-341` asserts
`state["rows"] is None` and `state["capture"] is None` after exactly this failure — the suite
*ratifies* the destruction as the contract.
Probe: `test_t02r2_failed_sidecar_write_keeps_the_last_qualified_observation` — RED.

### T02R2-M1 — major — a non-dict `openfda` raises AttributeError out of the sweep
`collectors/fda_shortages.py:73-74`, `:180-184`. Input: a well-formed row with
`"openfda": ["SYN-1"]` (also `"SYN-1"`, `7`). Output: `AttributeError: 'list' object has no attribute
'get'` propagating out of `collect_shortage_sweep` — no `failure_code`, no rows, no taxonomy. Through
`fetch_shortages` the `except Exception` at `:517` swallows it, so **no `last_refresh` is written at
all**: the sidecar keeps the previous (possibly `qualified: true`) refresh and the receipt reports a
clean state while the feed is broken. Laws broken: *the sweep never raises* (the frozen probe's own
statement, `tests/test_fda_supply_probes_t02r.py:155`), *failed refresh writes only `last_refresh`*.
Probe: `test_t02r2_non_dict_openfda_is_malformed_not_an_exception` — RED.

### T02R2-M2 — major — the legacy read path is unguarded
`collectors/fda_shortages.py:280` `frame = pd.read_parquet(path) if path.exists() else ...` — the
sidecar-fenced branch has a `try/except` (`:302-307`), the legacy branch (parquet present, sidecar
absent — i.e. every pre-T02 cache this PR must absorb, and exactly what a sparse worktree truncates)
has none. Input: a 23-byte non-parquet file at `shortages.parquet`, no sidecar. Output:
`pyarrow.lib.ArrowInvalid: ... Parquet magic bytes not found in footer` out of
`read_shortage_observation` / `load_shortages_cache`. Law broken: *a torn pair never raises; nothing
raises into the build*. Probe: `test_t02r2_unreadable_legacy_parquet_reads_as_state_not_an_exception` — RED.

### T02R2-M3 — major — a failed refresh over a corrupt sidecar raises
`collectors/fda_shortages.py:458` `existing = json.loads(sidecar.read_text()) if sidecar.exists() else {}`
— unguarded, while `_selected_state:289-296` handles precisely this shape. Input: sidecar containing
`{not json at all`, then a `FIRST_PAGE_OUTAGE` refresh. Output:
`json.decoder.JSONDecodeError: Expecting property name enclosed in double quotes: line 1 column 2`
out of `save_shortage_observation`. Law broken: *failed refresh writes only `last_refresh`* — here it
writes nothing and raises. Probe: `test_t02r2_failed_refresh_over_a_corrupt_sidecar_does_not_raise` — RED.

### T02R2-M4 — major — a capture with no source generation qualifies and hides an absence
`collectors/fda_shortages.py:155` (`generation = meta.get("last_updated")`, no type check), `:212`
(`complete` ignores `source_generation`), `:355`, `:365`, `:385`, `:399`. Input: two qualified sweeps
whose pages carry `meta.results.total` but **no** `meta.last_updated`; the second drops one row.
Output: `promoted=True`, and the persisted frame carries
`{'T02R2-B': None, 'T02R2-A': None}` for `absent_since_generation` — the disappeared row is stamped
byte-identically to the present one. `generations_seen` filters `None` (`:399`), so the row's
retention age is `-1` forever and it can never expire. Laws broken: *absence ≠ resolution*,
*source generation ≠ acquisition time*, *retention keys on distinct generations*. (The
`GENERATION_REGRESSION` fence at `:343` masks this once a real generation is selected, so it is
reachable when the first qualified observation lands generation-less.)
Probe: `test_t02r2_capture_without_a_source_generation_cannot_hide_an_absence` — RED.

### T02R2-m1 — minor — three unrelated jobs' `paths:` churned (GLM-M2)
See YML HYGIENE.

### T02R2-m2 — minor — the PR's only production wiring is untested
`scripts/build_foresight.py:112-116` is the whole production change (+5/-1) and it is listed in the
new job's `paths:`, but **no suite in the job's `run:` imports it** — measured: the four run-listed
test modules' import closure does not contain `scripts/build_foresight.py`. That is precisely how
T02R2-B1 shipped green.

## YML HYGIENE

`git diff --numstat origin/main...8d858bba -- .github/ci/legacy-jobs.yml` → `51	3`.
**Hunks outside the `healthcare-fda-supply` block (line 13485): 3.** All three are the same edit in
an unrelated job's `paths:` list:

| hunk | job (declared at) | edit |
|---|---|---|
| @@ -8296 | `biocatalyst-serving` (8109) | `engine/glut_watch.py` moved from after `engine/global_liquidity.py` to between `flip_confirmation.py` and `foresight_cascade.py` |
| @@ -12798 | `unrun-picks-boards` (12427) | same move |
| @@ -14550 | `unrun-subsector-themes` (14542) | moved from after `engine/foresight_sizing.py` to before `engine/foresight_cascade.py` |

`git diff ... | grep -n "^[-+].*glut_watch"` → `+9 -17 +25 -33 +65 +96 -102` (the `+65` line is the
new job's own legitimate entry). Direction: `glut` sorts after `global_liquidity` and after every
`foresight_*`, so the PR **breaks** alphabetical order in three jobs it has no business touching.
No behaviour changes (a `paths:` list is an unordered match set), hence minor — but revert.

Checked and clean, do not re-raise:
- `if: ${{ false }}` on the new job is house convention, not a disabled job — 230 occurrences across
  229 jobs; `run_ci_pack.py` dispatches these, GitHub does not.
- Every test file in the job's `run:` (`test_foresight_cascade.py`, `test_fda_shortages_generation.py`,
  `test_fda_supply_probes.py`, `test_fda_supply_probes_t02r.py`) is present in `paths:`.
- `paths:` is a **superset** of the measured import-time closure of those four modules
  (`CLOSURE_NOT_IN_PATHS: []`) — no under-listing; the extra `engine/*` entries are the cascade's
  lazy runtime imports, conservative and acceptable.
- `scope: exclusive` registration is present in `tests/test_ci_pack.py:3537` with a rationale comment.
- Banned substrings: `format_observation_receipt` emits none of `glut / tell / all-clear /
  catching up / demand exceeds supply / supply constraint lifted`; no ranking, entry, sizing or
  trading code is touched (`scripts/build_foresight.py` diff is one `log.info` plus its import).

## REPAIR SPEC

1. **T02R2-B1** — In `format_observation_receipt`, take `failure_code` from
   `observation["last_refresh"]["failure_code"]` (not `capture`), and derive the printed
   `qualified=` from the last refresh's own `qualified` flag so an outage cannot read `qualified=True
   failure_code=none`; update `tests/test_fda_shortages_generation.py:466-492` to format a state whose
   `last_refresh.failure_code` is actually set.
2. **T02R2-B2** — Serialise the receipt and stage the sidecar bytes *before* `_write_staged(path,
   write_parquet)`, then promote parquet and sidecar back-to-back, returning `METADATA_WRITE_FAILED`
   with the parquet untouched whenever serialisation or staging fails; amend
   `tests/test_fda_shortages_generation.py:339-341` to assert the previous observation survives.
3. **T02R2-M1** — Treat a non-dict `openfda` as a malformed row: guard
   `collectors/fda_shortages.py:73` with `isinstance(rec.get("openfda"), dict)` and widen the sweep's
   `except` at `:182` to also catch `AttributeError`, `KeyError` and `IndexError`.
4. **T02R2-M2** — Wrap the legacy `pd.read_parquet(path)` at `collectors/fda_shortages.py:280` in
   `try/except Exception` and return the `inconsistent=True` state shape on failure.
5. **T02R2-M3** — Wrap the `json.loads(sidecar.read_text())` at `collectors/fda_shortages.py:458` in
   `try/except Exception`, falling back to `{}` so a corrupt sidecar cannot turn an upstream outage
   into a raise.
6. **T02R2-M4** — Refuse to qualify a capture whose `source_generation` is not a non-empty string
   (a distinct failure code in the sweep's taxonomy), so a generation-less page can never promote and
   can never stamp an absent row with the same marker a present row carries.
7. **T02R2-m1** — Revert the three `engine/glut_watch.py` line moves in `biocatalyst-serving`,
   `unrun-picks-boards` and `unrun-subsector-themes` so this PR's `legacy-jobs.yml` diff is the new
   job block only.
8. **T02R2-m2** — Add one test to a `run:`-listed suite that drives the
   `scripts/build_foresight.py` drip line (import + receipt emission) so the production wiring this
   PR adds is covered by the job whose `paths:` already claims it.
