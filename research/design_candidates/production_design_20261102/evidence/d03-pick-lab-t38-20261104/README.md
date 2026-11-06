# D03 T38 — Pick Lab publication outcome and rerender-only recovery

Status: bounded maintenance source proof; Draft/HOLD. This is not atomic multi-file publication, deployment or full D03 acceptance.

## Source and custody

- Original D03 Phase 2A: macro `e521f04dcc5afb4fb06152584d35c8a01dbe21ff`; retained 78-capability / 53-case tree.
- Protected Mastermind procedure: `75a6540519cf519edfef7633e74f57b68aef9329`, compatible 1.0.1.
- Audited source `201e94dd75f385d118cc0f692768c26e0f02b355`; admitted base `52abe2e183833a216267942a99513e6c9cbe062f`. Relevant source, tests, CI manifest and instructions were unchanged between them.
- Original isolated branch: `claude/ssd-d03-pick-lab-publication-state-20261104-c2-984c7053ee70656f`.
- Canonical cumulative receipt: https://github.com/mastermindx-market-intelligence/macro/pull/10617#issuecomment-6623889088
- Direct bounded maintenance rationale: LOWER_TOTAL_OVERHEAD. No new workstream or publication plane.

The source census found no relevant open Pick Lab path overlap. Original #9495/dirty T004, Paper R8 and UX Fabric effects stay untouched. Shared `lib/pages.py` has an existing #9513 owner and is not changed. Foresight/Radar already emit their mixed-vintage annotations; that accepted behavior is not rebuilt.

## Problem and repair

The nightly caller writes three JSON artifacts before rendering HTML. Previously its render failure was an ordinary log warning, while success and caught failure both returned None. The committed-artifact rerender helper also swallowed render failure into a log, but left view-model construction outside its advertised fail-soft boundary.

Both caller-owned paths now emit a bare line-start GitHub warning and return an explicit HTML-publication boolean. True means the existing render/write call completed. False means publication is not confirmed, **not** that the previous page remains intact. An interrupted writer can already have changed page bytes.

The nightly warning truthfully says its JSON writes completed and HTML/JSON may differ in vintage. The rerender warning does not claim JSON was refreshed. The latter path loads existing artifacts, catches view-model/render failures and can regenerate HTML without firing, grading or rewriting the sources.

PL-R10's CLI **exit 0** is preserved, including exceptions and no-snapshot runs. It is process continuation, not page-freshness proof. No candidate engine, book, ruler, ledger policy, source payload, template, shared writer, scheduler or release control changes.

## Deterministic proof

New 12-case publication suite: initial exact-base **11 failed / 1 passed**; after repair all cases pass within the aggregate below.

```bash
python -m pytest tests/test_pick_lab_publication.py tests/test_pick_lab_runner.py \
  tests/test_pick_lab_render.py tests/test_gh_annotation_line_start.py -q -rs
```

**178 passed**, including existing never-break, real renderer, bilingual/book/ruler and annotation-placement contracts.

Fault injection distinguishes view-model, pre-write Jinja and interrupted-write failures in both nightly and committed-artifact paths. Tests verify:

- A column-zero failure annotation, not a logger-prefixed pseudo-annotation.
- Correct failure/success publication outcomes.
- New JSON dates still recorded when nightly HTML fails.
- Byte-preserved old HTML only for pre-write failures; the interrupted writer deliberately changes bytes, and no untouched-page claim is made.
- Actual existing view model/template/write_page recovery to the new date, including its data-base shim.
- Byte-identical JSON, fires/grades ledgers and snapshots across rerender-only recovery.
- Unavailable snapshot remains a no-op; committed missing inputs still render the existing empty state.
- Malformed source shapes cannot escape the rerender's view-model failure boundary.
- CLI exit 0 remains separate from HTML outcome.

All source/ledger/output paths are temporary. Price refresh/store access is replaced by unavailable fixture inputs; no production source or repository site output is touched. Actual templates are read through a temporary read-only link; no test writes through it. There is no HTML mock or custom publication fallback.

## CI and remaining boundary

The new suite is explicitly code-gated. Keeping it only in the existing data-gated runner/render owner would not guard PRs. Initial registration appended it to the existing Pick Lab family job and passed all three scope guards and 312-code-job/12-pack validation. However, the actual exact-head differential gate at `e36cd901933d78b5d2c7096feb9086a42b7985fa` found **1 introduced / 0 inherited** defect: the index-template probe rose 5912→5914 weight-seconds (137 jobs/10 packs unchanged); the other two probes remained at base. A unit-test pass was not packing proof.

The CI repair follows the adjacent `pick-lab-cn-render` precedent: the incumbent four-suite job is restored **byte-for-byte** to the admitted base (inferred weight10), and a focused `pick-lab-publication` code job (inferred weight4) owns all40 concrete measured import/read dependencies, ancestor initializers and the real Jinja/include/shared assets. The first narrowed candidate `a599bbebef7798d6ef36ea76a5430d26d7770762` restored all three packing probes to their base ceilings, but its canonical tracked-tree census found three additional literal artifact dependencies absent from the local sparse-file census: `site/flowleaders/leaders.json`, `site/leaderradar/radar.json` and `site/us_stocks_lab.html`. All three are now retained, for55 explicit paths. The exact-head gate, not the sparse-only closure test, owns the final coverage claim. Only opaque unrelated render-root/temporary-fixture traversal fallbacks are omitted from this new exclusive job. No existing job's scope, command, dependency, gate or limit is narrowed, and no observed-weight override or ceiling is changed. The explicit curated-job set and a positive/negative selection regression in `tests/test_ci_pack.py` preserve these obligations.

A clean Python3.12 environment installed exactly the existing six dependencies (pytest, pandas, numpy, pyarrow, PyYAML, Jinja2). The initial five-suite command passed **256/256**. After the registration repair, the exact new command passed **12/12**, and the unchanged incumbent command passed **244/244**. Nine CI guards passed, including gate declaration, path validity, explicit curated-set equality, complete import-closure coverage, opaque-only fallback removal, trigger startability, ancestor-initializer protection and positive/negative selection. Manifest validation passed for **313 code jobs / 12 packs** (385 logical jobs across gates). The new exact-head differential gate result is recorded on the same Draft PR and cumulative receipt after observation. A topology change may conservatively select the full safe CI plan for this PR; no planner/admission behavior is weakened.

No Paper or template layout was changed in this backend-only slice. Existing D03 editable design evidence is retained; there is no new visual-acceptance claim. T38's remaining crash windows and multi-file atomicity are still open obligations under the existing writer/publication owner.

**No Ready, un-draft, labels, enqueue, merge, auto-merge or deploy.**
