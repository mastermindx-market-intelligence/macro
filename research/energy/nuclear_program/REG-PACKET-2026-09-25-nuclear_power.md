# Registration packet: `nuclear_power` into the shared theme-research shell

Prepared 2026-09-25 by the Energy seat (session 8955bbc3), operation `gmi-energy-fable-ceo-e2e-20260923-chairman-001`.

**Status: PREPARED, not dispatched.**
- The carrier opens only after #7870 merges to main and #8002 is rebased onto that merge.
- Until then this packet is context. It is not a build order.
- The copy decisions below are recorded as seat ruling R-ENE-23. They land with the round-3 records.

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

# theme_research_registry.py: a lazy loader mirroring the semiconductor one, then the entry
def _load_nuclear_owner_bundle(query, *, rights_snapshot=None):
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
    definition_version=NUCLEAR_DEFINITION_VERSION,   # imported from nuclear_theme_research
    compose=compose_nuclear_research,
    select_evidence=select_nuclear_evidence,         # nuclear select_authorized_evidence, aliased on import
    load_bundle=_load_nuclear_owner_bundle,
    title_en=_NUCLEAR_MOUNT.title_en, title_zh=_NUCLEAR_MOUNT.title_zh,
    note_en=_NUCLEAR_MOUNT.note_en, note_zh=_NUCLEAR_MOUNT.note_zh,
)
```

The registry already imports `semiconductor_theme_research`, and `nuclear_theme_research` imports only that module plus `engine.theme_graph.*`. So the eager `compose` import adds no forbidden module. The carrier must still prove this with `test_registry_import_closure_stays_light` green.

## 4. Tests the carrier adds or updates

**Append only.** No test is deleted or renamed (R-ENE-19 carries over).

1. The four closed-set pins become `["ai_semiconductors", "nuclear_power"]` and `{ANCHOR, "nuclear_power"}`. Only those four lines change.
2. `mount_context("nuclear_power")` renders all three slices with their labels. The crosswalk's `primary_basket_id` must resolve to `nuclear_power`.
3. **`uranium_miners` → None.** The supplemental basket never mounts and never borrows the nuclear mount.
4. The registry entry's anchor, slices, schema ids and copy equal the mount's field for field.
5. Importing the registry does not import `nuclear_owner_bundle`. That is the lazy positive control: assert the module is absent from `sys.modules` after a fresh import.
6. The evidence route with a `gmi-curation://theme:nuclear_power/gmirca_…` ref is added ONLY once the widened pattern `^gmi-curation://(?:theme:)?[a-z0-9_]+/gmirca_[0-9a-f]{32}$` is on main. Watch check F reports it. Before that, the route refuses every nuclear ref by design (RULING 8), so a test written earlier would pin the defect.

## 5. NOT DONE UNLESS (the carrier's acceptance gates)

- Every test in section 4 is green, and the full theme-research suite is green on a FULL checkout, not a sparse one.
- **Served proof.** On success AND on every error path, the nuclear query and evidence responses carry the accepted `private` / `no-store` / `noindex` / `noarchive` headers. The receipt is a raw `curl -sD-`, pasted in the PR body.
- **Privacy.** No full-fidelity paid research is written to public Git, Pages, public R2, static public JSON, a source map, or persistent browser storage. `localStorage` holds only the three-key selection (`slice_key` / `view` / `time_mode`). Proof is a grep of the built page, plus the stored key read back in the browser.
- **Browser proof.** Crops for dark and light × EN and ZH × 1440 and 390 are posted in the PR body. The mount renders the three plain-word chips. The `uranium_miners` basket page renders no mount.
- The carrier's own Opus READ_ONLY review returns PASS before the PR leaves DRAFT.
- The live rung stays behind the VPS pull-cron hold (`# MMX-DISK-TRIAGE-HOLD`, #6902). That hold is an EXACT_HUMAN_GATE and the seat never lifts it.
