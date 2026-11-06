# Opus re-review, round 2 — PR #8002 nuclear theme-research module (2026-09-25)

- **Artifact:** PR #8002 at `9e3237efdef67ce7a8659bbe50f98b3e75d2a957`.
  - Branch `claude/energy-nuclear-vertical-module`, stacked on `claude/energy-stack-base-b-6cd958e9`, which is #7870 frozen at `6cd958e92b25`.
  - This head is the round-1 fix lane's output (lane `ene_w2_nuclear_module_r1fix`, m1, GLM).
- **Reviewer:** an Opus `reviewer`, MODE READ_ONLY, native child `a5ee31a5d1808346b`.
  - It stopped at its 24-turn limit with no verdict. The seat resumed it once, on the same carrier, with a bounded finish directive. Nothing was re-dispatched.
- **Verdict: FIX_REQUIRED.**
  - Round 1: B1, M1, M2 (a)(b), M3, M4, M5, m1, m3 (promoted), m4, m5, m7 and the nits are CLOSED. Each is killed by a named test, and the route test runs for real (httpx 0.28.1, not skipped).
  - New findings:
    - NEW-1 and NEW-2 are MAJOR.
    - NEW-3, NEW-4, NEW-5, NEW-6, NEW-7 and NEW-9 are MINOR.
    - NEW-8 and NEW-10 are NIT.
    - The reviewer's headline says "5 minor, 3 nits". The per-finding labels give 6 and 2, because NEW-8 carries two items.
- **Seat adjudication:** rulings R-ENE-17..22 in `../rulings/R-ENE-2026-09-25-w2-module-r2.md`.
  - The seat verified the MAJOR findings at the artifact before ruling.
  - It added one finding of its own, S1: the evidence selector iterates the pre-gate list.
  - It withdrew its own R-ENE-12 parenthetical, which was the source of NEW-2.
- **Record contents:** the reviewer's return verbatim, followed by its probe script. The probe script is the reproduction recipe the fix lane received.

---

STATUS: FAIL

RESULT:
**FIX_REQUIRED.** I reviewed PR #8002 at exact head `9e3237efdef67ce7a8659bbe50f98b3e75d2a957`. Most of the round-1 findings are closed, and every ruling mutant is now killed by a named test. Two new MAJOR findings block acceptance: the fix commit deleted tests the packet requires, and the reference day is computed over the wrong set of assertions. There are also 5 MINOR findings and 3 NITs.

**Closure of round 1** (line numbers are in `engine/market_ontology/nuclear_theme_research.py` unless a test file is named)

| Finding | State | Where | Test that now proves it |
|---|---|---|---|
| B1 | CLOSED | Port at :240-270, called at :224 in the same order as Robotics (review gate, then supersession, then syndication). Rows read corroboration at :382, :425-426. The logic matches Robotics `_apply_syndication`; the only difference is that the port omits Robotics' unused `by_revision` variable. | `test_syndicated_copy_collapses_into_its_single_original` |
| M1 | CLOSED for the original defect: the caller no longer decides (:117-142, :225-230). NEW-2 below is a different defect in the same function. | | `test_latest_without_cutoff_uses_the_evidence_frontier_for_targets` |
| M2 (a), (b) | CLOSED. Rows are keyed by revision. | `tests/test_nuclear_research_temporal.py:18-37` | cases (a) and (b) |
| M2 (c) | OPEN, MINOR (NEW-3) | | |
| M3 | CLOSED. `_ROW_ORDER` is removed; the X06/X07 fixture pair sorts smallest first under the shared key. | | `test_rows_order_is_deterministic_never_by_magnitude` |
| M4 | CLOSED. The route test runs for real (1 passed, no skip). Removing the route's rights filter makes it fail, so it does reach `app/theme_research.py` `_filter_bundle_for_rights`. The renamed composer test also asserts that `select_authorized_evidence` refuses X02. Error-response headers are not asserted (NEW-6). | | route test; `test_composer_defence_in_depth_excludes_unmapped_rights_source` |
| M5 | CLOSED. Counts are real (:174-205). | | `test_out_of_cohort_assertions_are_dropped_counted_and_absent_everywhere`; `test_composer_defence_in_depth_excludes_unmapped_rights_source` |
| m1 | CLOSED. `grep Robotics` over the contract finds nothing (rc=1). | | |
| m2 | (b) and (c) CLOSED; (a) PARTIAL (NEW-9) | | |
| m3 (promoted to MAJOR) | CLOSED. `_text_of` returns coverage only (:556-559). `next_evidence` excludes passed targets (:591). Rows still echo both lists (:432-433). | | `test_milestones_never_leave_limitations_for_summary_text`; `test_attributed_interpretation_is_never_a_view_row` |
| m4 | CLOSED. :527-553; `app:` subjects validate against the contract. | | `test_businessless_product_selector_and_application_subjects` |
| m5 | CLOSED, except the divergence in NEW-7 | :475-524, :562-648 | 5 tests in `test_nuclear_research_sections.py` |
| m6 (R-ENE-13) | PARTIAL (NEW-4). The tuple is at :65-83 and both pin tests exist. | | |
| m7 | CLOSED. Fixtures N13/N14. | | `test_equity_method_investee_never_consolidated` |
| nit: owner-bundle test name | CLOSED. The test asserts the exact tuple. | | |
| nit: loader imports | Accepted as-is under R-ENE-14; unchanged. | | |
| nit: `prd:None` | CLOSED; no `prd:None` anywhere. The replacement selector shape is NEW-8. | | |

**Mutants I ran myself** (as monkeypatch plugins under `$TMPDIR`, over all 8 nuclear test files)
- **B1, deleting the call:** 25 tests fail. Every row build crashes because `corroboration` is never set, so this kill proves little on its own.
- **B1, keeping the call but making it do nothing:** fails `test_syndicated_copy_collapses_into_its_single_original`.
- **M1/M2, literal `_is_passed_target = _is_retrospective`:** 25 tests crash with a signature error.
- **M1/M2, deleting only the passed-target branch:** fails
  - `test_latest_without_cutoff_uses_the_evidence_frontier_for_targets`
  - `test_explicit_latest_cutoff_still_decides_target_windows`
  - `test_same_retention_and_publication_still_judges_only_the_target_window`
  - `test_milestones_never_leave_limitations_for_summary_text`
- **M3, sort key = negated observation value:** fails `test_rows_order_is_deterministic_never_by_magnitude` and `test_contingent_backlog_rows_never_summed_or_funded`.
- **M5, restoring the hard-coded `:1`:** fails `test_out_of_cohort_assertions_are_dropped_counted_and_absent_everywhere` and `test_composer_defence_in_depth_excludes_unmapped_rights_source`.
- **m3, restoring the `establishes[0]` read:** fails `test_attributed_interpretation_is_never_a_view_row` and `test_milestones_never_leave_limitations_for_summary_text`.
- **m7, adding the investee figure into Cameco's row:** fails `test_equity_method_investee_never_consolidated`.
- **My own extra mutants:**
  - Supersession disabled: **SURVIVED**.
  - Correction lineage returns `[]`: **SURVIVED**.
  - Target windows judged in latest mode only: **SURVIVED**.
  - `<` instead of `≤`: **SURVIVED**.
  - No `target_windows_judged_at` disclosure: killed by the temporal test (a).
  - Route rights filter removed: killed by the route test.
  - Cohort gate removed: killed by 2 composition tests.
  - Composer rights gate removed: killed by the defence-in-depth test.
  - Passed targets kept in `next_evidence`: killed by `test_milestones_never_leave_limitations_for_summary_text`.
  - Reference day from `published_at` only: killed by the temporal test (a).

**New findings**
- **NEW-1 — MAJOR (regression).** The fix commit deleted four round-1 temporal tests, including two the packet names:
  - `test_passed_forward_target_stays_a_retrospective_target`
  - `test_correction_pair_supersedes_without_deleting` (the X03 correction pair and its lineage)
  - `test_system_replay_uses_recorded_cutoff`
  - `test_latest_selects_currently_available_evidence`

  Fixture X03 is now unused (`grep X03` over the nuclear tests returns rc=1). At head, the supersession-disabled and empty-lineage mutants both SURVIVE all 40 tests. Run against the head code, the deleted round-1 file kills both with `test_correction_pair_supersedes_without_deleting`. The packet requires "incl. `test_passed_forward_target_stays_a_retrospective_target` and the correction pair X03". Fix: restore these tests with revision keys.
- **NEW-2 — MAJOR (R-ENE-12, L5).** The reference day and the disclosure code are computed from `self.assertions` (:225-230). That list is filled at :201, before the review gate (:222) and before syndication (:224), so records excluded from every surface still move the reference day. Failing inputs:
  - **P1:** N03 alone gives `retrospective: False`, `target_windows_judged_at:2026-09-20`, and N03 in `next_evidence`. Add one *rejected* Oklo record dated 2028-06-01, which appears in no row or evidence. N03 then becomes `retrospective: True`, is dropped from `next_evidence`, and the response carries `target_windows_judged_at:2028-06-01`. That discloses the rejected record's date and marks a target that has not passed as passed. The payload still validates against the contract.
  - **P1b:** a collapsed syndicated copy dated 2028-06-01 has the same effect.
  - **P1c:** when the only DEPLOYMENT_TARGET is rejected, the commercial view has 0 rows, yet `target_windows_judged_at:2026-09-20` is still emitted. The commission names this case explicitly: the code must not be emitted when no DEPLOYMENT_TARGET is selected.

  Fix: compute the reference day and the DEPLOYMENT_TARGET presence check over the post-gate set (`self.current` / `self.row_assertions`). The seat's parenthetical "(the final `self.assertions`)" conflicts with "survive every selection gate" in the same ruling. The seat should rule which one binds.
- **NEW-3 — MINOR.** M2 case (c) was required in `source_history`. `test_same_retention_and_publication_still_judges_only_the_target_window` runs in latest mode (the `nuclear_query` default), so the mutant that judges windows in latest mode only survives. The code itself is correct: P4 gives N03C True, N03D False.
- **NEW-4 — MINOR (R-ENE-13 incomplete).** `LIMITATION_CODES` omits three shared codes the composer emits through `_passes_time_mode`: `same_day_grain_ambiguous`, `undatable_excluded` and `availability_unknown_excluded` (`semiconductor_theme_research.py:226`, `:232`, `:246`).
  - Failing input (P2): system_replay with `source_cutoff="2026-09-19T12:00:00Z"`, and an N04 variant observed at 01:00Z and retained at 02:00Z on 2026-09-19. The response carries `same_day_grain_ambiguous`, which matches no declared entry.
  - The pin-test matrix (`tests/test_nuclear_research_codes.py:25-36`) omits `system_replay` and the stale fixture, although the ruling says "every time mode".
- **NEW-5 — MINOR.** The `≤` boundary is untested: the `<` mutant survives. The behaviour is correct: P3 shows `valid_to` equal to the reference day gives `retrospective: True`.
- **NEW-6 — MINOR.** The route test (`tests/test_nuclear_research_route.py:59-72`) asserts `Cache-Control` / `X-Robots-Tag` only on the 200 response. The review standard requires an error response too. I did not re-probe the error path this round.
- **NEW-7 — MINOR (m5 not faithful).** At :607-612, `why_it_matters` includes superseded ATTRIBUTED_INTERPRETATION items. Robotics excludes `curation_revision in selection.superseded`. P7: X01 plus its correction X01B yields both revisions, with `superseded_present` set.
- **NEW-8 — NIT.** For a product with no business label, `_subject_selector` at :94-95 emits `prd:<product>` with kind `product`. Robotics returns `(None, None)`, so this is a selector shape Robotics never emits, though it validates (P11). Also, the company role sort key at :497 is `(assertion_ref, predicate)`; Robotics uses `(assertion_ref, role)`.
- **NEW-9 — MINOR (m2(a) partial).**
  - The cohort-count test uses SMR variants in `nuclear_components` rather than CCJ/LEU.
  - Its `select_authorized_evidence` check queries X04. X04 was re-faceted from `reactor_technology` to `fuel_cycle` in `tests/nuclear_research_helpers.py`, which contradicts the packet's definition of X04. So the evidence refusal comes from the facet gate, not the cohort gate, and that assertion proves nothing about the cohort.
  - No CCJ fixture is faceted `nuclear_components`.
  - The cohort gate as a whole is still guarded: removing it fails 2 tests.
- **NEW-10 — NIT.**
  - `test_explicit_latest_cutoff_still_decides_target_windows` checks that one specific string is absent, not the `target_windows_judged_at:` prefix.
  - The m7 checks `"150" not in str(payload)` and `"50" not in str(rows[0])` depend on hash text and could break by chance.

**Energy laws L1–L9**
- **L1 HOLDS.** :168-169 adds `supplemental_basket_witnesses` for `fuel_cycle`, and the cohort gate at :192 is guarded by 2 tests. The test weakness is NEW-9.
- **L2 HOLDS.** Across all 38 fixtures × 3 slices × 5 views × 2 modes, zero summary texts equal any `establishes` or `does_not_establish` string (P8).
- **L3 HOLDS.** Backlog rows stay separate; total is `{'value': None, 'reason': 'totals_not_computed'}` (P10).
- **L4 HOLDS.** Values [100, 50, 1, 3] stay separate; the summary never shows 150; the m7 mutant is killed.
- **L5 BROKEN (narrowly), via NEW-2.** A rejected or collapsed record flips an open target to retrospective and drops it from `next_evidence`, while every test stays green. A target that really has passed is never converted: P9 shows DEPLOYMENT_TARGET / FORWARD_TARGET, `retrospective: True`, absent from `next_evidence`.
- **L6 HOLDS.** :740-753 unchanged.
- **L7 HOLDS.** The composer uses the shared `family_for_source_ref` (:195) with no local prefix table. The production route path is proven: removing the route filter kills the route test.
- **L8 HOLDS.** The shared `_row_sort_key` is used and the M3 mutant is killed; `AUTHORITY` is imported from the shared module.
- **L9 HOLDS.** No clock, I/O, network, credential, store or robotics import in any owned file (the only robotics hits are a docstring and a test-only contract path). Refs match `gmi-curation://theme:nuclear_power/gmirca_<32 hex>` (P0 True). Fixtures are round, labelled synthetic, under `sec.gov/Archives/edgar/data/synthetic` and `nrc.gov/synthetic`.

**Scope:** the name-only diff lists only owned nuclear files, and the added test files are all new `tests/test_nuclear_*.py`. No shared or shell file is touched.

EVIDENCE:
- **Head and working tree.**
  - `git -C $W rev-parse HEAD` → `9e3237efdef67ce7a8659bbe50f98b3e75d2a957`.
  - `git log --oneline 1071dd9de3e9..9e3237efdef6` → `9e3237efdef fix(energy): complete nuclear research composition`.
- **Name-only diff** `6cd958e9...9e3237ef`: `contracts/market_ontology/nuclear_theme_research.v1.schema.json`, `engine/market_ontology/nuclear_owner_bundle.py`, `engine/market_ontology/nuclear_theme_research.py`, `tests/nuclear_research_helpers.py`, `tests/test_market_ontology_nuclear_theme_research.py`, `tests/test_nuclear_owner_bundle.py`, `tests/test_nuclear_research_codes.py`, `tests/test_nuclear_research_composition.py`, `tests/test_nuclear_research_inputs.py`, `tests/test_nuclear_research_route.py`, `tests/test_nuclear_research_sections.py`, `tests/test_nuclear_research_temporal.py`. A grep for anything outside the nuclear paths → `nonowned_rc=1` (none).
- **Fix stat:** "9 files changed, 730 insertions(+), 117 deletions(-)".
- **Route test** (httpx 0.28.1, fastapi 0.141.1, Python 3.14.7): `tests/test_nuclear_research_route.py::test_route_filters_refused_rights_families_before_composition PASSED [100%]` / `1 passed, 90 warnings in 1.47s`. No skip.
- **All 8 nuclear suites:** `40 passed, 90 warnings in 4.22s`.
- **Mutant runs:** `MUTANT=<id> PYTHONPATH=$TMPDIR/nucprobe python3 -m pytest <8 nuclear files> -q -p no:cacheprovider -p mutplug`. Summary lines:
  - B1 no-op: `1 failed, 39 passed`
  - M1 semantic: `4 failed, 36 passed`
  - M3: `2 failed, 38 passed`
  - M5: `2 failed, 38 passed`
  - m3: `2 failed, 38 passed`
  - m7: `1 failed, 39 passed`
  - supersession disabled, lineage empty, latest-only windows, `<` boundary: each `40 passed`
  - route filter removed: `1 failed, 39 passed`
- **Regression proof:** `git show 1071dd9de3e9:tests/test_nuclear_research_temporal.py` run against the head code gives `5 passed` with no mutant. With supersession disabled, and separately with lineage empty, it gives `FAILED ::test_correction_pair_supersedes_without_deleting` / `1 failed, 4 passed`.
- **Probes** (`PYTHONPATH=. python3 $TMPDIR/nucprobe/probe_r2.py`), verbatim:
  - `P1 base N03 retro/lims/next: {'gmirca_44b9ba0': False} ['target_windows_judged_at:2026-09-20'] [('target', 'gmirca_44b9ba0')]`
  - `P1 +rejected N03 retro/lims/next: {'gmirca_44b9ba0': True} ['rejected_present', 'target_windows_judged_at:2028-06-01'] []`
  - `P1b +collapsed copy: rows {'gmirca_44b9ba0': True} ['syndicated_collapsed', 'target_windows_judged_at:2028-06-01'] []`
  - `P1c only-rejected target: commercial rows 0 ['rejected_present', 'target_windows_judged_at:2026-09-20']`
  - `P2 limitations ['milestone_predicate_unavailable', 'same_day_grain_ambiguous', 'slice_scope_unowned'] unmatched ['same_day_grain_ambiguous'] errs []`
  - `P3 valid_to==frontier day retro {'gmirca_6d961b6': True}`
  - `P4 source_history window-only {'gmirca_08393ac': True, 'gmirca_bc45c1a': False}`
  - `P7 why_it_matters refs ['gmirca_38a5518', 'gmirca_fee0b73'] X01 gmirca_fee0b73 True`
  - `P8 L2 summary==milestone hits: []`
  - `P9 DEPLOYMENT_TARGET FORWARD_TARGET deployment_target True [] []`
  - `P10 values [100, 50, 1, 3] total {'value': None, 'reason': 'totals_not_computed'} False False`
  - `P11 selector ['prd:Synthetic product only'] errs []`
  - m4 check: `composition ['application', 'facet', 'product', 'product'] []`, i.e. the `app:` subject validates against the contract.
- **Static checks:**
  - The grep for clock, robotics, ImportError and I/O patterns hits only the docstring at :243 and the test contract-path lines.
  - `/opt/homebrew/bin/pyflakes <11 owned .py>` → `pyflakes_rc=0`.
- **Adjacent shared suites** (7 files): `10 failed, 298 passed, 101 skipped in 8.15s`. All 10 are in `test_semiconductor_theme_research_ui.py` (`node --check` / missing JS) or `test_theme_research_mount_context.py`, which fails with `FileNotFoundError: .../site/assets/js/theme-research.js`. Both are sparse-tree artifacts that need `site/`; this module touches no shared file.
- **Final state:** `git -C $W status --short` → empty (`status_rc=0`).

GAPS:
- Error-response header behaviour was not re-probed this round (round 1's P7 observed it on a 400).
- The evidence-route test is absent by ruling R-ENE-15; the shell-pattern gap belongs to #7870.
- The 10 adjacent failures need a full checkout with `site/` to clear.
- I did not open the lane's own report or the PR body, so neither is relied on or verified.
- The empty-coverage summary case (`text` must have `minLength` 1) cannot be reached: the shared assertion contract rejects an empty `coverage`, so that probe was dropped.
- L1 still rests on the limitation code and the slice label, because the shared company-row shape cannot carry the cohort relation.

DEVIATIONS:
- STATUS is FAIL because the verdict is FIX_REQUIRED.
- The literal B1 and M1 mutants crash rather than fail semantically, so I also ran semantic equivalents and report both.
- My first mutant loop in zsh did not split the file list and ran no tests; I re-ran it under bash.
- On the coordinator's instruction I finished within a limited budget.
- All probe files are only in `$TMPDIR/nucprobe/`: `mutplug.py`, `probe_r2.py`, `probe_r2b.py`, `test_r1_temporal_old.py`. Nothing was edited, committed or posted.

---

## Appendix — the reviewer's probe script (verbatim; `PYTHONPATH=. python3 probe_r2.py` from the repo root at `9e3237ef`)

```python
import json, dataclasses, re, copy
from engine.market_ontology import nuclear_theme_research as n
from engine.theme_graph.curation_assertion import source_ref_for, encode_assertion
from tests.nuclear_research_helpers import (N03, N03B, N04, N01, X01, X03, N07, N10, N11, N13, N14,
    clone, variant, nuclear_bundle, nuclear_query)
import jsonschema
from pathlib import Path
C = json.loads(Path("contracts/market_ontology/nuclear_theme_research.v1.schema.json").read_text())
V = jsonschema.Draft202012Validator(C, format_checker=jsonschema.FormatChecker())
def errs(p): return [e.message[:120] for e in V.iter_errors(p)]
def rv(p, view="commercial"): return {r["curation_revision"][:14]: r["retrospective"] for r in p["industrial_views"][view]["rows"]}
def ne(p): return [(i["label"], i["input_refs"][0][:14]) for i in p["summary"]["next_evidence"]]
print("P0 refs:", sorted({r["assertion_ref"].rsplit("/",1)[0] for r in n.compose_nuclear_research(nuclear_query("reactor_technology","commercial"), nuclear_bundle(N03,N03B))["evidence_refs"]}),
      all(re.fullmatch(r"gmi-curation://theme:nuclear_power/gmirca_[0-9a-f]{32}", source_ref_for(a)) for a in (N03,N03B,N04)))
# P1 frontier fed by a REJECTED (review-gated) assertion
late = variant("N04", "LATEREJ", source={"published_at": "2028-06-01", "retained_at": "2028-06-01T00:00:00Z", "observed_at": "2028-06-01T00:00:00Z"},
               scope={"technology_facet": "reactor_technology"}, subject={"company_node_id": "co:us:OKLO", "source_business_label": "Oklo"},
               review={"disposition": "rejected", "reviewer": "synthetic-energy-test", "reviewed_at": "2026-09-20T00:00:00Z", "review_due_at": None})
q = nuclear_query("reactor_technology", "commercial")
base = n.compose_nuclear_research(q, nuclear_bundle(N03))
p1 = n.compose_nuclear_research(q, nuclear_bundle(N03, late))
print("P1 base  N03 retro/lims/next:", rv(base), [l for l in base["limitations"] if "judged" in l], ne(base))
print("P1 +rejected N03 retro/lims/next:", rv(p1), [l for l in p1["limitations"] if "judged" in l or "rejected" in l], ne(p1))
print("P1 rejected in rows/evidence?", late["curation_revision"] in json.dumps(p1), "errs", errs(p1))
# P1b frontier fed by a syndicated copy that collapsed (not in any row)
cp = variant("N03", "LATECOPY", source={"publisher": "Synthetic Wire", "published_at": "2028-06-01", "retained_at": "2028-06-01T00:00:00Z", "observed_at": "2028-06-01T00:00:00Z"},
             limitations={"source_dependence": "syndicated_copy_of:Synthetic Energy Filings"})
p1b = n.compose_nuclear_research(q, nuclear_bundle(N03, cp))
print("P1b +collapsed copy: rows", rv(p1b), [l for l in p1b["limitations"] if "judged" in l or "synd" in l], ne(p1b))
# P1c DEPLOYMENT_TARGET only rejected → disclosure code emitted with no target selected
rejt = variant("N03", "REJT", review={"disposition": "rejected", "reviewer": "synthetic-energy-test", "reviewed_at": "2026-09-20T00:00:00Z", "review_due_at": None})
p1c = n.compose_nuclear_research(q, nuclear_bundle(N01, rejt))
print("P1c only-rejected target: commercial rows", len(p1c["industrial_views"]["commercial"]["rows"]), [l for l in p1c["limitations"] if "judged" in l or "rejected" in l])
# P2 same_day_grain_ambiguous / undatable / availability_unknown not in LIMITATION_CODES
sd = variant("N04", "SAMEDAY", source={"observed_at": "2026-09-19T01:00:00Z", "retained_at": "2026-09-19T02:00:00Z"})
p2 = n.compose_nuclear_research(nuclear_query("nuclear_components", "economics", time_mode="system_replay",
        source_cutoff="2026-09-19T12:00:00Z", recorded_cutoff="2026-12-31"), nuclear_bundle(sd))
def unmatched(p): return [t for t in p["limitations"] if sum(t == c or t.startswith(c) for c in n.LIMITATION_CODES) != 1]
print("P2 limitations", p2["limitations"], "unmatched", unmatched(p2), "errs", errs(p2))
# P3 boundary: valid_to == reference day
eq = variant("N03", "EQDAY", temporal={"business_valid_to": "2026-09-20"})
p3 = n.compose_nuclear_research(q, nuclear_bundle(eq))
print("P3 valid_to==frontier day retro", rv(p3), p3["limitations"])
# P4 source_history window-only (M2 case c as ruled)
from tests.nuclear_research_helpers import N03C, N03D
p4 = n.compose_nuclear_research(nuclear_query("reactor_technology", "commercial", time_mode="source_history", source_cutoff="2026-12-31"), nuclear_bundle(N03C, N03D))
print("P4 source_history window-only", rv(p4))
p4b = n.compose_nuclear_research(nuclear_query("reactor_technology", "commercial", time_mode="source_history"), nuclear_bundle(N03C, N03D))
print("P4b source_history no cutoff", rv(p4b), [l for l in p4b["limitations"] if "judged" in l])
# P5 source_history archival N03 (not passed) retrospective True yet in next_evidence labelled target
p5 = n.compose_nuclear_research(nuclear_query("reactor_technology", "commercial", time_mode="source_history", source_cutoff="2026-12-31"), nuclear_bundle(N03, N03B))
print("P5 source_history rows", rv(p5), "next", ne(p5))
# P6 summary text empty when coverage empty → contract?
nc = variant("N04", "NOCOV", limitations={"coverage": ""})
try:
    p6 = n.compose_nuclear_research(nuclear_query("nuclear_components", "economics"), nuclear_bundle(nc))
    print("P6 empty coverage what_changed", p6["summary"]["what_changed"], "errs", errs(p6))
except Exception as e:
    print("P6 variant rejected by shared contract:", type(e).__name__, str(e)[:160])
# P7 superseded ATTRIBUTED_INTERPRETATION stays in why_it_matters (Robotics drops it)
x1b = variant("X01", "X01B", correction={"predecessor_revision": X01["curation_revision"], "reason": "synthetic correction"})
p7 = n.compose_nuclear_research(nuclear_query("nuclear_components", "commercial"), nuclear_bundle(X01, x1b))
print("P7 why_it_matters refs", [i["input_refs"][0][:14] for i in p7["summary"]["why_it_matters"]], "X01", X01["curation_revision"][:14], "superseded_present" in p7["limitations"])
# P8 L2: summary text equal to any establishes/does_not_establish across full corpus
from tests.nuclear_research_helpers import FIXTURES
ms = {t for a in FIXTURES.values() for t in (a["limitations"].get("establishes") or []) + (a["limitations"].get("does_not_establish") or [])}
hits = []
for sk in n.SLICES:
    for vw in n.VIEWS:
        for tm in ({}, {"time_mode": "source_history", "source_cutoff": "2026-12-31"}):
            p = n.compose_nuclear_research(nuclear_query(sk, vw, **tm), nuclear_bundle(*FIXTURES.values()))
            for f in ("what_changed", "why_it_matters", "offset", "next_evidence"):
                hits += [i["text"] for i in p["summary"][f] if i["text"] in ms]
print("P8 L2 summary==milestone hits:", hits)
# P9 L5 passed target never converted: N03B in rows stays DEPLOYMENT_TARGET/FORWARD_TARGET
p9 = n.compose_nuclear_research(q, nuclear_bundle(N03B))
r = p9["industrial_views"]["commercial"]["rows"][0]
print("P9", r["predicate"], r["statement_mode"], r["relation_kind"], r["retrospective"], ne(p9), p9["summary"]["what_changed"])
# P10 L4: N13+N14 totals/summary never sum
p10 = n.compose_nuclear_research(nuclear_query("fuel_cycle", "economics"), nuclear_bundle(N13, N14, N10, N11))
vals = [r["observation"]["value"] for r in p10["industrial_views"]["economics"]["rows"]]
print("P10 values", vals, "total", p10["industrial_views"]["economics"]["total"], "150" in json.dumps(p10["summary"]), "4" in [str(v) for v in vals])
# P11 prd:<product> selector without business — contract + Robotics divergence
from tests.nuclear_research_helpers import X08
p11 = n.compose_nuclear_research(nuclear_query("reactor_technology", "composition"), nuclear_bundle(X08))
print("P11 selector", [r["selector"] for r in p11["industrial_views"]["composition"]["rows"]], "errs", errs(p11))
```
