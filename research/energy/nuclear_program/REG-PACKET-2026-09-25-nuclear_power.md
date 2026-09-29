# Registration packet: `nuclear_power` into the shared theme-research shell

Prepared 2026-09-25 by the Energy seat (session 8955bbc3), operation `gmi-energy-fable-ceo-e2e-20260923-chairman-001`.

**Status: PREPARED, not dispatched.**
- The carrier opens only after #7870 merges to main and #8002 is rebased onto that merge.
- Until then this packet is context. It is not a build order.
- The copy decisions below are recorded as seat ruling R-ENE-23. They land with the round-3 records.
- **Re-verified 2026-09-28** at #7870 head `a0d7b054ff23` and #8002 head `3c775ea592a6` (§1b). Two carrier obligations were added (§3b). The status is unchanged: PREPARED, not dispatched.
- **Dry-run 2026-09-28** (§1c). The packet was applied in a scratch tree at #7870 `a0d7b054ff23` plus #8002 `3c775ea592a6`, and every gate it names passed. The dry-run corrected two facts in this packet: the definition-version import in §3, and the curated block count in §3b.2 (seven, not six). The registration needs nothing from #7870 except RULING 8's widening (§4.6).
- **The ENERGY directive, 2026-09-29** (`rulings/R-ENE-2026-09-29-energy-directive.md`, R-ENE-41 to R-ENE-43). The carrier opens only after #7870 is released and source custody permits, and ONE writer executes it. §5b adds R-ENE-42 (the cutoff readers), the `$defs/when` alignment and two proofs. The status is unchanged: PREPARED, not dispatched.

## 1. Facts this packet rests on

Every fact was read at #7870 head `6cd958e92b25` and #8002 head `9e3237efdef6`. Re-verify each at the post-merge heads before the carrier writes anything.

| Fact | Where |
|---|---|
| A mount is one `MountFacts` row. Its fields are `anchor_theme_id`, `slice_keys`, `schema_id`, `evidence_schema_id`, `slice_labels` (an `(en, zh)` pair per slice), `title_en/zh` and `note_en/zh`. All text must be non-empty, and the two schema ids must differ. | `engine/market_ontology/theme_research_mounts.py:76-131` |
| `VerticalRegistration` reads the anchor, slices, schema ids and copy FROM the mount. It owns only `compose`, `select_evidence`, `load_bundle` and `definition_version`. | `engine/market_ontology/theme_research_registry.py:163-186` |
| The semiconductor loader is bound lazily. `test_registry_import_closure_stays_light` names the modules the registry must not import. | `theme_research_registry.py:147-160` |
| The client draws slice chips from the mount's `data-slice-labels`, through `SPEC.labels`. It checks a remembered slice against the mount's own `SLICES`. **No client edit is needed.** | `site/assets/js/theme-research.js:1405`, `:1053-1061` |
| The client's one compiled vocabulary, `TR_VIEW_KEYS`, equals nuclear `VIEWS` exactly: composition, manufacturing, commercial, capacity, economics. | `theme-research.js:113`; `nuclear_theme_research.py:36` |
| The MountFacts docstring and the docstring of `test_client_slice_labels_match_the_registration` are STALE. They say the client still renders chips from its own map, and that is no longer true. The test pins `ANCHOR = ai_semiconductors` only, so registering nuclear does not trip it. | `test_theme_research_mount_context.py:462-484` |
| Four pins enforce a closed set and must be updated additively (Energy relayed this to #7870 in comment `5830625739`). | `tests/test_theme_research_registry.py:89`, `:94`, `:275`; `tests/test_theme_research_mount_context.py:185` |
| Nuclear's entry points and ids: `compose_nuclear_research`, `select_authorized_evidence`, `load_nuclear_owner_bundle`, `DEFINITION_VERSION = "2026-09-25.1"`, `SCHEMA_ID = "nuclear_theme_research.v1"`, `EVIDENCE_SCHEMA_ID = "nuclear_theme_research.evidence.v1"`. | `nuclear_theme_research.py:31-36, 775, 801`; `nuclear_owner_bundle.py:25` |
| Slice cohorts: reactor technology is SMR and OKLO; nuclear components is BWXT; fuel cycle is CCJ and LEU. | `nuclear_theme_research.py:37-41` |
| A basket page mounts the crosswalk theme whose `primary_basket_id` is that basket, and only if that theme's `id` is a MOUNTS key. The crosswalk row `id: nuclear_power` has `primary_basket_id: nuclear_power` and `basket_ids: [nuclear_power, uranium_miners]`. So the `nuclear_power` page mounts, and `uranium_miners` is membership only, so it mounts nothing. | `theme_research_mounts.py` `registered_anchor_for_basket`; `config/theme_crosswalk.yml:121-128` (main `90704bbea8f0`) |
| House Chinese terms: the basket label is `nuclear_power → 核电`, and the house prose uses `核燃料循环` and `反应堆`. | `templates/committee.html.j2:1477`; `templates/report_second_act.html.j2:137,1659` |

## 1b. Re-verification, 2026-09-28 (#7870 `a0d7b054ff23`, #8002 `3c775ea592a6`)

The seat read every section-1 fact again with `git show` at both heads. It used the seat script `regcheck.py`, whose output is summarised here.

| Fact | Status at the new heads | Where now |
|---|---|---|
| `MountFacts` fields | HOLDS. The docstring is still stale. | `theme_research_mounts.py:76-99` (docstring `:80-86`); `_ENTRIES` `:153`; `registered_anchor_for_basket` `:257` |
| `VerticalRegistration` fields, the lazy loader and the entry | HOLDS | `theme_research_registry.py:84-110`; loader `:147-160`; entry `:169-190`; `REGISTRY` `:202` |
| The import closure stays light | HOLDS. Nuclear's eager closure adds `engine.theme_graph.identity` (`re`, `functools`, `pathlib`, `yaml`) and `rights` (`hashlib`, `logging`, `functools`, `pathlib`, `yaml`). None of these is on the test's list. The carrier still proves the test green. | `tests/test_theme_research_registry.py:199-213` |
| The registry's own imports | HOLDS. The nuclear import has root `engine`, which is inside the allowed set `{__future__, collections, dataclasses, types, typing, engine}`. | `tests/test_theme_research_registry.py:330-341` |
| The client needs no edit | HOLDS. A remembered slice is checked by `parseStoredSelectionFor(SPEC, raw)`, which tests `spec.slices`, and then against `SLICES`. The compiled `TR_SLICE_KEYS` (`:112`) is read only by the legacy `parseStoredSelection` (`:118-129`). | `site/assets/js/theme-research.js:591-603`, `:1048-1060`; chips `:1405-1406`; `data-slice-labels` `:1901` |
| `TR_VIEW_KEYS` equals nuclear `VIEWS` | HOLDS | `theme-research.js:113`; `nuclear_theme_research.py:36` |
| The four closed-set pins | HOLDS, at the same lines. `:582-583` derives from `_ENTRIES` and needs no edit. | registry test `:89`, `:94`, `:275`; mount-context test `:185` |
| Nuclear entry points and ids | HOLDS. Only the line numbers moved. | `nuclear_theme_research.py:32-36`, `:780`, `:806`; `nuclear_owner_bundle.py:25` |
| The crosswalk row | HOLDS. It is identical on main and on the base. | `config/theme_crosswalk.yml:121-134` (`theme_node_id: "theme:nuclear_power"`) |
| House Chinese terms | HOLDS | `templates/committee.html.j2:1477` |
| The evidence-route pattern | **STILL NARROW.** RULING 8's widening is not on #7870's head, so §4.6 stays gated. | `app/theme_research.py:207`: `^gmi-curation://[a-z0-9_]+/gmirca_[0-9a-f]{32}$` |

## 1c. Dry-run, 2026-09-28 (#7870 `a0d7b054ff23` + #8002 `3c775ea592a6`)

The seat applied §3, §3b.1, §3b.2 and §4.1 with exact-anchor edits in a throwaway worktree. Nothing was committed or pushed from it. Receipts:

| Gate | Before the edits | After the edits |
|---|---|---|
| The 11 nuclear test files plus `test_theme_research_mount_context`, `_registry`, `_api`, `test_semiconductor_theme_research_ui`, `test_theme_research_private_binding`, `_rights_refresh` and `test_deploy_update_self_heal` | `710 passed, 2 skipped` | `711 passed, 2 skipped`. The one new case is the appended `MUST_RESTART` row, which that file parametrizes (`:458`). |
| §4.2 to §4.5, written as tests (the bytes are in §4b) | not applicable | `5 passed`. The lazy-import test carries its own positive control: calling the entry's loader does put `nuclear_owner_bundle` into `sys.modules`. |
| `tests/test_ci_pack.py -k "closure or curated or scope"` | not run | `21 passed, 2 skipped, 112 deselected` |
| Curated-exclusive closure audit (`scripts/run_ci_pack.py:curated_exclusive_closure_findings`) | 7 jobs MISS, each exactly `nuclear_theme_research.py` and `nuclear_owner_bundle.py` (the positive control: the lines stripped) | 0 MISS |

- The two skips are the witness-fixture skips in `tests/test_theme_research_api.py`. On a correct tree they are the ONLY skips (§3b.3).
- **The client is ready.** `site/assets/js/theme-research.js` already serves a second vertical through its spec path: `applyResearchResponseFor` and `validateEvidenceFor` take a SPEC, the chips come from `SPEC.labels`, and the stored selection is per anchor. No #7870 file changes for nuclear to register. Energy told the owner so in #7870 comment 5866433049, item 2.

## 2. Seat copy decisions (R-ENE-23)

| Field | EN | ZH | Why |
|---|---|---|---|
| title | Nuclear power industry research | 核电产业研究 | Mirrors the shell's reviewed "Semiconductor industry research / 半导体产业研究". 核电 is the house basket label. |
| note | Paid research context for members. Nothing here ranks, gates, sizes or times anything. | 会员研究内容。此处内容不构成排序、准入、仓位或时机判断。 | The shell's reviewed disclaimer, **verbatim**. A second wording of the same promise would need its own review and could drift. |
| slice `reactor_technology` | Reactor technology | 反应堆技术 | Plain words. The cohort is reactor designers (SMR, OKLO). |
| slice `nuclear_components` | Nuclear components | 核电部件 | 核电部件, not 核部件, which can be read as weapons parts. The cohort is BWXT. |
| slice `fuel_cycle` | Fuel cycle | 核燃料循环 | The house term. The cohort is CCJ and LEU: mining and enrichment. |

These labels pass the plain-language gate: no slug, no internal state name, no untranslated statistic. `uranium_miners` gets no copy, because it never mounts.

## 3. Entry spec (the exact shape; the carrier writes nothing beyond it)

```python
# theme_research_mounts.py: one new row; _ENTRIES becomes (_SEMICONDUCTOR, _NUCLEAR)
_NUCLEAR = MountFacts(
    anchor_theme_id="nuclear_power",
    slice_keys=("reactor_technology", "nuclear_components", "fuel_cycle"),
    schema_id="nuclear_theme_research.v1",
    evidence_schema_id="nuclear_theme_research.evidence.v1",
    slice_labels=MappingProxyType({
        "reactor_technology": ("Reactor technology", "反应堆技术"),
        "nuclear_components": ("Nuclear components", "核电部件"),
        "fuel_cycle": ("Fuel cycle", "核燃料循环"),
    }),
    title_en="Nuclear power industry research",
    title_zh="核电产业研究",
    note_en=("Paid research context for members. Nothing here ranks, gates, sizes "
             "or times anything."),
    note_zh="会员研究内容。此处内容不构成排序、准入、仓位或时机判断。",
)

# theme_research_registry.py: one import, placed before the semiconductor import (alphabetical)
from engine.market_ontology.nuclear_theme_research import (
    DEFINITION_VERSION as _NUCLEAR_DEFINITION_VERSION,
    compose_nuclear_research,
    select_authorized_evidence as select_nuclear_evidence,
)

# then a lazy loader mirroring the semiconductor one, then the entry
def _load_nuclear_owner_bundle(query: Any, *, rights_snapshot: Any = None) -> Any:
    """The nuclear entry's loader, bound LAZILY for the same module law as
    the semiconductor one. Resolved on the first served request, never at import."""
    from engine.market_ontology.nuclear_owner_bundle import (  # noqa: PLC0415 — lazy by design
        load_nuclear_owner_bundle,
    )
    return load_nuclear_owner_bundle(query, rights_snapshot=rights_snapshot)

_NUCLEAR_MOUNT = _MOUNTS["nuclear_power"]
_NUCLEAR = VerticalRegistration(
    anchor_theme_id=_NUCLEAR_MOUNT.anchor_theme_id,
    slice_keys=_NUCLEAR_MOUNT.slice_keys,
    schema_id=_NUCLEAR_MOUNT.schema_id,
    evidence_schema_id=_NUCLEAR_MOUNT.evidence_schema_id,
    definition_version=_NUCLEAR_DEFINITION_VERSION,
    compose=compose_nuclear_research,
    select_evidence=select_nuclear_evidence,
    load_bundle=_load_nuclear_owner_bundle,
    title_en=_NUCLEAR_MOUNT.title_en, title_zh=_NUCLEAR_MOUNT.title_zh,
    note_en=_NUCLEAR_MOUNT.note_en, note_zh=_NUCLEAR_MOUNT.note_zh,
)
```

**[Corrected 2026-09-28 (registration dry-run): nuclear exports `DEFINITION_VERSION`, and no `NUCLEAR_DEFINITION_VERSION` exists. The block above now shows the import, and the loader in the exact shape the dry-run applied and proved.]**

The registry already imports `semiconductor_theme_research`, and `nuclear_theme_research` imports only that module plus `engine.theme_graph.*`. So the eager `compose` import adds no forbidden module. The carrier must still prove this with `test_registry_import_closure_stays_light` green.

## 3b. Carrier obligations added 2026-09-28 (Semiconductors B's carried laws, verified at `a0d7b054ff23`)

1. **The macro-api restart regex** is in `app/deploy/update.sh`, between `# BEGIN MACRO_API_RESTART_TRIGGER` and `# END`, at line 1261.
   - Registration puts nuclear inside the API's import closure: `app/theme_research.py:64` imports the registry at module level.
   - The seat ran the regex itself against the paths. `nuclear_theme_research.py`, `nuclear_owner_bundle.py` and `engine/theme_graph/identity.py` do **not** match it today. `theme_graph/rights.py` and `curation_assertion.py` do.
   - Add `nuclear_theme_research` and `nuclear_owner_bundle` to the `engine/market_ontology/(…)` group, and `identity` to the `engine/theme_graph/(…)` group. Enumerate the names; never glob.
   - `tests/test_deploy_update_self_heal.py::test_api_load_time_import_closure_is_covered_by_restart_regex` enforces the two modules imported at load time.
   - It cannot see `nuclear_owner_bundle`, which the registry's lazy loader imports inside a function, at request time. After the first request that module is pinned in `sys.modules` just the same. Append it to that file's `MUST_RESTART` list so a guard pins it.
2. **The curated CI closure lists** are in `.github/ci/legacy-jobs.yml`.
   - Every curated exclusive job that names `engine/market_ontology/theme_research_registry.py` must also name `nuclear_theme_research.py` and `nuclear_owner_bundle.py`. It must also name any `engine/theme_graph/*` file its paths do not already cover.
   - **[Corrected 2026-09-28 (registration dry-run): there are SEVEN such blocks, not six.]** At `a0d7b054ff23` there are six such blocks, near lines 2250, 2525, 9120, 9764, 11870 and 12252.
   - The seven lines at `a0d7b054ff23` are 2253, 2526, 9121, 9765, 11871, 12253 and 15848. The audit names the seven jobs: `semiconductor-b-boundary`, `biocatalyst-history`, `biocatalyst-serving`, `defense-rail-laws`, `flow-surface`, `unrun-government-revenue-candidate-projection` and `unrun-government-revenue-grader`.
   - No `engine/theme_graph/*` file was uncovered in any of them, so the union adds exactly the two nuclear files to each block.
   - Resolve each list as a UNION with whatever main has added since. Dropping either side breaks that side's audit.
   - Prove it with `tests/test_ci_pack.py -k "closure or curated or scope"` and the curated-exclusive closure audit. Re-run both after ANY merge or rebase, not only after your own edits.
3. **Gate discipline.**
   - Run `python3 scripts/worktree_sparse.py add site` before trusting any gate. The mount-context suite reads `site/assets/js/theme-research.js`, and a sparse `site/` gives failures that look exactly like code regressions.
   - For checks that need data, run `git sparse-checkout add data/regime data/theme_graph`, never the whole `data/`.
   - Attribute a red pack by reading its traceback, never by the job's name.
   - **A sparse tree hides suites behind skips.** Run with `-rs` and read every skip reason. On the dry-run tree the same suites gave `704 passed, 8 skipped` while fully sparse, then `10 failed, 607 passed, 95 skipped` with `data/` added but `site/` still omitted, and `710 passed, 2 skipped` only once the theme-research assets under `site/` were present. The only expected skips are the two witness-fixture skips in `tests/test_theme_research_api.py`. Any other skip reason means that gate did not run.

## 4. Tests the carrier adds or updates

**Append only.** No test is deleted or renamed (R-ENE-19 carries over).

1. The four closed-set pins become `["ai_semiconductors", "nuclear_power"]` and `{ANCHOR, "nuclear_power"}`. Only those four lines change.
2. `mount_context("nuclear_power")` renders all three slices with their labels. The crosswalk's `primary_basket_id` must resolve to `nuclear_power`.
3. **`uranium_miners` → None.** The supplemental basket never mounts and never borrows the nuclear mount.
4. The registry entry's anchor, slices, schema ids and copy equal the mount's field for field.
5. Importing the registry does not import `nuclear_owner_bundle`. That is the lazy positive control: assert the module is absent from `sys.modules` after a fresh import.
6. The evidence route with a `gmi-curation://theme:nuclear_power/gmirca_…` ref is added ONLY once the widened pattern `^gmi-curation://(?:theme:)?[a-z0-9_]+/gmirca_[0-9a-f]{32}$` is on main. Watch check F reports it. Before that, the route refuses every nuclear ref by design (RULING 8), so a test written earlier would pin the defect.

## 4b. §4.2 to §4.5 as proven test bytes (dry-run, 2026-09-28)

These five tests passed on the dry-run tree (§1c). The carrier may land them as `tests/test_theme_research_nuclear_registration.py`, a NEW file, so nothing is renamed or deleted. Re-run them after the rebase, because they read `scripts/build_theme_detail.py` and the mount template as they are on main then.

```python
"""Dry-run of REG-PACKET §4.2–4.5 against #7870 a0d7b054ff23 (proven on the dry-run tree)."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
NUC = "nuclear_power"
SLICES = ("reactor_technology", "nuclear_components", "fuel_cycle")


def test_4_2_mount_context_renders_three_labelled_slices():
    from engine.market_ontology.theme_research_mounts import (  # noqa: PLC0415
        mount_context, registered_anchor_for_basket,
    )
    ctx = mount_context(NUC)
    assert ctx is not None
    assert ctx["slices"].split(",") == list(SLICES)
    labels = json.loads(ctx["slice_labels_json"])
    assert set(labels) == set(SLICES)
    assert labels["fuel_cycle"] == ["Fuel cycle", "核燃料循环"]
    assert registered_anchor_for_basket(NUC) == NUC
    import jinja2  # noqa: PLC0415
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(str(REPO_ROOT / "templates")),
                             autoescape=True, undefined=jinja2.StrictUndefined)
    html = env.get_template("_theme_research_mount.html.j2").render(theme_research_mount=ctx)
    for key in SLICES:
        assert key in html
    assert "Nuclear power industry research" in html and "核电产业研究" in html


def test_4_2b_the_basket_page_builder_mounts_nuclear_on_us_only():
    from scripts.build_theme_detail import _theme_research_mount  # noqa: PLC0415
    mount = _theme_research_mount(NUC, "us")
    assert mount is not None and mount["anchor_theme_id"] == NUC
    assert _theme_research_mount("uranium_miners", "us") is None


def test_4_3_uranium_miners_never_mounts():
    from engine.market_ontology.theme_research_mounts import (  # noqa: PLC0415
        mount_context_for_basket, registered_anchor_for_basket,
    )
    assert registered_anchor_for_basket("uranium_miners") is None
    assert mount_context_for_basket("uranium_miners") is None


def test_4_4_registry_entry_equals_mount_field_for_field():
    from engine.market_ontology.theme_research_mounts import MOUNTS  # noqa: PLC0415
    from engine.market_ontology.theme_research_registry import REGISTRY  # noqa: PLC0415
    from engine.market_ontology import nuclear_theme_research as n  # noqa: PLC0415
    m, r = MOUNTS[NUC], REGISTRY[NUC]
    for f in ("anchor_theme_id", "slice_keys", "schema_id", "evidence_schema_id",
              "title_en", "title_zh", "note_en", "note_zh"):
        assert getattr(r, f) == getattr(m, f), f
    assert r.definition_version == n.DEFINITION_VERSION
    assert r.schema_id == n.SCHEMA_ID and r.evidence_schema_id == n.EVIDENCE_SCHEMA_ID
    assert tuple(r.slice_keys) == tuple(n.SLICES)
    assert r.compose is n.compose_nuclear_research
    assert r.select_evidence is n.select_authorized_evidence


def _fresh(code: str) -> str:
    run = subprocess.run([sys.executable, "-c", code], cwd=REPO_ROOT, capture_output=True,
                         text=True, env={"PYTHONPATH": str(REPO_ROOT), "PATH": "/usr/bin:/bin"})
    assert run.returncode == 0, run.stderr[-800:]
    return run.stdout.strip()


def test_4_5_registry_import_does_not_import_the_owner_bundle_with_positive_control():
    mod = "engine.market_ontology.nuclear_owner_bundle"
    absent = _fresh("import sys, engine.market_ontology.theme_research_registry as r\n"
                    f"print({mod!r} in sys.modules)")
    assert absent == "False"
    present = _fresh("import sys, engine.market_ontology.theme_research_registry as r\n"
                     "try:\n    r.REGISTRY['nuclear_power'].load_bundle(None)\nexcept Exception:\n    pass\n"
                     f"print({mod!r} in sys.modules)")
    assert present == "True", "positive control: the lazy loader must actually import it"
```

## 5. NOT DONE UNLESS (the carrier's acceptance gates)

- Every test in section 4 is green, and the full theme-research suite is green on a FULL checkout, not a sparse one.
- **Served proof.** On success AND on every error path, the nuclear query and evidence responses carry the accepted `private` / `no-store` / `noindex` / `noarchive` headers. The receipt is a raw `curl -sD-`, pasted in the PR body.
- **Privacy.** No full-fidelity paid research is written to public Git, Pages, public R2, static public JSON, a source map, or persistent browser storage. `localStorage` holds only the three-key selection (`slice_key` / `view` / `time_mode`). Proof is a grep of the built page, plus the stored key read back in the browser.
- **Browser proof.** Crops for dark and light × EN and ZH × 1440 and 390 are posted in the PR body. The mount renders the three plain-word chips. The `uranium_miners` basket page renders no mount.
- `tests/test_deploy_update_self_heal.py` is green, including the appended `MUST_RESTART` row (§3b.1). The curated-exclusive closure audit reports zero MISS (§3b.2).
- The carrier's own Opus READ_ONLY review returns PASS before the PR leaves DRAFT.
- **Plain language.** The shell's Limitations line prints wire tokens verbatim in EN and ZH. For nuclear it reads, for example, `milestone_predicate_unavailable · slice_scope_unowned · target_windows_judged_at:2026-09-20 · witness_cohort_excluded:2`. That is the shell's reviewed design (T10 BLOCKING-2), and semiconductor tokens render the same way. Energy asked the owner whether a token-to-plain-words map is planned (#7870 comment 5866433049, item 6) and offered a bilingual table for its own 20 tokens. Until the owner answers, the carrier does not edit `theme-research.js`, and the PR body names the raw tokens as a known gap next to the browser crops.
- The live rung stays behind the VPS pull-cron hold (`# MMX-DISK-TRIAGE-HOLD`, #6902). That hold is an EXACT_HUMAN_GATE and the seat never lifts it.

## 5b. Added by the ENERGY directive, 2026-09-29 (R-ENE-41 to R-ENE-43)

The same one writer carries these in the same carrier, after the reconciliation onto #7870's accepted base.
- **R-ENE-42, the cutoff readers.** Nuclear uses `recorded_cutoff` as a clock only in `system_replay`, and `source_cutoff` only in `source_history` and `system_replay`. Outside those modes the clocks stay data-derived, as with no cutoff. Every supplied cutoff is still validated in every mode. The six test obligations are in `rulings/R-ENE-2026-09-29-energy-directive.md`. They include P3's rows and R-ENE-43's rows, and they keep R-ENE-40's replay test and malformed-cutoff test unchanged.
- **The response-date grammar.** Nuclear's `$defs/when` matches the grammar the accepted base admits, the same grammar the validation uses. The alignment test is named in the same ruling.
- **Two further proofs**, besides §5:
  - *Unavailable and revoked.* The nuclear query and evidence routes answer the shell's typed unavailable and revoked states, never false, zero, stale or partial research. They carry the same private headers as §5's served proof, and the receipt is raw.
  - *Update and restart propagation.* After an update, the served route runs the new nuclear bytes. This is proven by a response that only the new bytes produce, not by the `MUST_RESTART` row alone. The live rung of this proof waits on the #6902 hold, like every live rung here.
- The production credential boundary (Task 10) and Power-Demand (R-ENE-16) stay outside this carrier. A green on this carrier is not nuclear acceptance.
