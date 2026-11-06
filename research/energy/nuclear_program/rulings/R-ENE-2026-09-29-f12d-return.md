# R-ENE-44 to R-ENE-46 — #7870 moved to `f12db8bff1d1` (#8002 compatible; the packet delta; a `business_valid_to` crash reported)

- Seat: Energy Fable CEO, session 8955bbc3 (claude8). Operation `gmi-energy-fable-ceo-e2e-20260923-chairman-001`.
- Issued 2026-09-29. At issue, PR #8002 is at `508d8c206357287a5f8ff9d1596efc32b3749459` (round 11), DRAFT, with no labels and auto-merge null, last updated 2026-09-28T13:40:40Z. #7870 is OPEN and DRAFT at `f12db8bff1d1a46a2c9fbf100bed8f6f3abc9ec9`, last updated 2026-09-29T17:20:07Z. The Slack root has no reply since 2026-09-28.
- It consumes two #7870 edges: the owner's shared-source return, comment 5894500015 (16:38:15Z), and Sol's ruling on it, comment 5895067178 (17:14:45Z). Energy answered in comment 5895389582, with no asks.
- A later #7870 edge was read before these records were committed: the Technology ex-Semiconductors seat's comment 5895399391 (17:36:22Z). It reports a Technology-owned defect. That module reads temporal keys the contract's closed `temporal` object cannot carry. It offers this as design input: the kernel should own the temporal key names. It does not name Energy. Nuclear reads the contract's own names, `business_valid_to` at `nuclear_theme_research.py:136` and `business_valid_from` at `:427-428` and `:529`, so that defect does not reproduce here. Only the `:136` value is parsed, at `:142`, which is R-ENE-46's site. Nothing below changes, and Energy owes no reply.
- This ruling changes records only. Nothing on #8002 changes under it.

## What moved, and why this is not an audit round

#7870 moved from `a0d7b054ff23` to `f12db8bff1d1`: five files, +502 −20. The return names five fixes, D1 to D5:
- **D1:** the scope gate matches the anchor slug against `theme:<slug>`;
- **D2:** the evidence ref admits `theme:` (Energy's item 1);
- **D3:** a malformed cutoff is a 400 in every mode (item 4);
- **D4:** an unreadable owner timestamp withholds the row instead of failing the request (item 5);
- **D5:** `identity` joins the restart regex, and the lazily imported modules are pinned in `MUST_RESTART` (item 3).

R-ENE-41 reopens when #7870's head changes. So the seat re-checked #8002 against the new head, bounded to that delta. The check asked two questions:
1. Does #8002 still compose and pass on `f12db8bff1d1`?
2. Does any of D1 to D5 change something Energy owns?

It did not review nuclear's module. The ENERGY directive also asks for material correctness defects to be reported, and R-ENE-46 is one.

## R-ENE-44 — #8002 is compatible with `f12db8bff1d1`; the pause resumes there

**Method.** #8002's 15 files at `508d8c206357` were overlaid on an archive of `f12db8bff1d1`. The base's five changed files and #8002's 15 files do not overlap. Every overlaid blob equals `git show 508d8c206357:<path>`. The same checks ran on the round-11 sim of `a0d7b054ff23` for comparison.

**Results.**
- On both heads, nuclear's 11 test files give 128 passed: 124 in the ten non-route files and 4 in `test_nuclear_research_route.py`.
- On both heads, `tests/test_theme_research_api.py` has the same five non-passes: three errors and two failures, named in Reproduction. `f12db8bff1d1` adds none. The check is differential only, and their cause was not investigated.
- On both heads, every probe in Reproduction gives the same result, apart from D3, which is the intended change. In the `probe_bvt_trace` stack the base's `_parse_day` line moves from 151 to 152. R-ENE-43's target-window rewind reproduces byte for byte at `f12db8bff1d1`.

**Ruling.**
- #8002 is compatible with `f12db8bff1d1`, and the base owes Energy nothing.
- The pause (R-ENE-41) resumes at `508d8c206357` on #8002 and `f12db8bff1d1` on #7870.
- **The reopen trigger is narrowed.** Sol's 5895067178 approves an extraction on the same carrier. That extraction will move #7870 again, and it is expected to move names nuclear imports. So Energy does not re-check each intermediate head. It re-checks at the head #7870 is released at, or sooner if a return on #7870 names Energy. A change to nuclear's engine, or a material defect, still reopens, as before.

## R-ENE-45 — the packet delta at `f12db8bff1d1`, and what nuclear takes from the base

Sol's 5895067178 puts the D1, D3 and D4 laws in one shared kernel, which verticals consume instead of copying. D2 and D5 stay with their current owners. This ruling reads each fix against that.

- **D1, scope matching: nothing to copy.**
  - Nuclear's own selection already matches both scope forms (`nuclear_theme_research.py:172-191`). It maps the anchor with `theme_node_id` and counts slug-keyed rows as its own limitation.
  - At the reconciliation, nuclear consumes the kernel's matcher and keeps only its slug-keyed limitation token. Limitation tokens stay vertical under the ruling.
- **D2, the `theme:` evidence ref: nothing to change.** It closes Energy's item 1.
  - The scoped-evidence proof the ENERGY directive asks for now includes a round trip.
  - A nuclear corpus minted the way the canonical-id law says (scope `theme:nuclear_power`, refs from `source_ref_for`) must go from query, to `evidence_refs`, to an evidence POST through the registered route.
  - This mirrors the base's `test_a_law_conforming_vertical_round_trips_query_to_evidence`. Item 1 is the defect it guards.
- **D3, the malformed cutoff: inherited.**
  - Measured with `probe_d3`. On `a0d7b054ff23`, `20261231`, `2026-W53-4` and `not-a-date` escape as a raw `ValueError`. On `f12db8bff1d1` all three are a `ResearchRefusal` with `cutoff_unreadable`, in `latest`, `source_history` and `system_replay`. A well-formed cutoff is still served on both heads.
  - Nuclear's `_compose` and `select_authorized_evidence` call the base's `_validate_query` (`:719`, `:821`). The call comes before any nuclear reader, so the refusal lands first.
  - R-ENE-42 left one decision to the reconciliation: whether nuclear keeps validation of its own once the base validates every cutoff in every mode. At `f12db8bff1d1` the base does.
  - **The seat's decision:** if the accepted base still refuses in every mode, nuclear adds no validation of its own. A nuclear copy is the duplication the extraction removes.
  - **Test note.** Nuclear's malformed-cutoff tests pin `pytest.raises(ValueError)` by design (R-ENE-35, and the danger item on `_le` and `_parse_day`). They are `test_nuclear_research_review_gate.py:137-145` and `test_nuclear_research_interpretation_scope.py:162-170`.
  - `ResearchRefusal` subclasses `ValueError` on both heads (MRO measured). So at `f12db8bff1d1` these pins pass on the base's refusal, and the nuclear readers they are named for are never reached.
  - At the reconciliation, with D3 in the accepted base, they pin `ResearchRefusal` and its `cutoff_unreadable` code. An escaping raw `ValueError` then fails them. An engine test still never pins an HTTP status.
- **D4, unreadable owner timestamps: adopted for nuclear's own reads.** See R-ENE-46.
- **D5, restart propagation: one re-anchor on Energy's side.** The packet dry-run at `f12db8bff1d1` applies 7 of its 9 edits. The two `app/deploy/update.sh` anchors fail because the base moved:
  - The `engine/theme_graph/(…)` group already reads `(store|rights|curation_assertion|identity)`. §3b.1's `identity` edit is base-carried and is dropped.
  - The `engine/market_ontology/(…)` group now reads `(__init__|exposure_map|semiconductor_owner_bundle|semiconductor_theme_research|semiconductor_witness_scope|theme_research_binding|theme_research_mounts|theme_research_registry|workspace_projection)`. The carrier inserts `nuclear_owner_bundle|nuclear_theme_research|` after `exposure_map|`. The names are enumerated, never globbed.
  - `MUST_RESTART` at `f12db8bff1d1` pins `semiconductor_owner_bundle`, `semiconductor_witness_scope` and `workspace_projection`. Nuclear's row for `nuclear_owner_bundle` still applies.
- **The imports, which the extraction moves.** Nuclear's production code takes 11 names from `semiconductor_theme_research` (`nuclear_theme_research.py:10-21`).
  - Seven are private: `_canonical_text`, `_is_retrospective`, `_le`, `_parse_day`, `_passes_time_mode`, `_row_sort_key` and `_validate_query`.
  - The other four are `AUTHORITY`, `OwnerBundle`, `ResearchQuery` and `ResearchRefusal`.
  - It also takes `PRIVATE_ASSERTIONS_UNBOUND` from `semiconductor_owner_bundle`, and its tests take `wire_omission`.
  - It already takes `BundleUnavailable` from `theme_research_binding`, the leaf Sol prefers to evolve into the kernel.
  - At the reconciliation nuclear re-points every name onto what the accepted base's kernel exports. Where a name stays vertical under the ruling, nuclear defines its own; the ruling keeps query literals, schema IDs and authority vertical.
  - The choice is made against the accepted base's actual exports, not predicted here. Nothing has to stay importable from the semiconductor modules for Energy's sake (5895389582).
- **The registry binding (§3).**
  - §3 adds a module-level `from engine.market_ontology.nuclear_theme_research import (…)` to `theme_research_registry.py`, before the semiconductor import.
  - At `f12db8bff1d1` the registry (`:50`) and the shell (`app/theme_research.py:58`) import `semiconductor_theme_research` at module level. Sol's ruling removes exactly that edge, so §3's module-level import would re-create it for nuclear.
  - At the reconciliation, §3's registry edit follows the accepted base's closed binding for the semiconductor entry.
  - The import-closure proof must hold with nuclear registered: importing the shell and the registry leaves `nuclear_theme_research` unloaded.
  - If the accepted base loads composers lazily, `nuclear_theme_research` joins `nuclear_owner_bundle` in `MUST_RESTART`. The load-time probe cannot see a function-level import, which is why `f12db8bff1d1` pins its three lazies by hand.

### Test obligations (they land with the integration)

1. **The scoped-evidence round trip** (D1 and D2), as above, through the registered route.
2. **The D3 pins.** Nuclear's malformed-cutoff tests name `ResearchRefusal` and `cutoff_unreadable` if the accepted base keeps D3. The well-formed control stays beside each one.
3. **Import closure with nuclear registered.** Importing the shell and the registry leaves every vertical composer unloaded, nuclear's included. Serving `nuclear_power` loads nuclear's implementation and no other. This follows the accepted base's own closure test.
4. **Restart.** The regex matches both nuclear modules. `MUST_RESTART` carries a row for every nuclear module that is loaded only lazily.

## R-ENE-46 — a contract-admitted `business_valid_to` crashes nuclear's whole composition

The ENERGY directive asks for material correctness defects to be reported. This is one, and it is nuclear's own. D4's law exposed it; D4 did not cause it.

**The defect.** `_is_passed_target` (`nuclear_theme_research.py:133-143` at `508d8c206357`) judges a `DEPLOYMENT_TARGET` / `FORWARD_TARGET` assertion. It reads `temporal.business_valid_to` with the base's `_parse_day`, unguarded, at `:142`.
- The shared curation contract admits a calendar-invalid `business_valid_to`. `2026-13-45` and `2026-02-30` encode cleanly.
- It refuses `not-a-date`, `20261231`, `2026-W53-4` and `2026-1-5`.

On such a row, `_row` (`:409`) calls `_is_passed_target`, and `_parse_day` raises `ValueError` (`probe_bvt_trace`). The whole composition fails:
- in `latest`, with and without a source cutoff;
- in `source_history`;
- in `system_replay`;
- on both heads.

**Why it matters.** One admitted row takes down every other row in the slice. The law the base now publishes is that a row with an unreadable owner timestamp is withheld, never fatal. Through the route, an escaping error is what item 5 of 5894500015 describes as `service_unavailable` / `retry_later`. Nuclear's route response for this case was not measured.

**Why it is not live.** Nuclear's loader returns an empty bundle (`nuclear_owner_bundle.py:25-45`, omissions `PRIVATE_ASSERTIONS_UNBOUND` and `PUBLIC_ASSERTIONS_UNCURATED`). No admitted row reaches the reader in production today.

**The rest of the matrix** (`probe_encoded_owner_ts`, identical on both heads):
- `source.published_at` also admits `2026-13-45` and `2026-02-30`. In this fixture the composition succeeds and `target_windows_judged_at:2026-09-20` is unchanged, so it is not a crash. Nothing more is claimed for it.
- `source.retained_at`, `review.review_due_at` and `review.reviewed_at` refuse all six malformed values. They cannot reach nuclear's readers through the contract.

**A latent sibling.** `identity_state` (`:346`) reads `mapping_learned_at` (`:353`) with the base's `_le` in `system_replay`, unguarded, at `:354-355`.
- An unreadable value raises `ValueError` for all four probe values, on both heads (the identity rows of `probe_unreadable_owner_ts`).
- A missing or empty value is already refused as `identity_vintage_unsupported` (`:700-709`).
- Identity results come from the identity owner, not from the curation contract. Whether that owner can emit an unreadable `mapping_learned_at` was not measured.
- The base's `identity_index` withholds such an identity (5894500015).

**The ruling.** At the reconciliation, in the same carrier and by the same writer as R-ENE-42:
1. A forward target whose `business_valid_to` does not parse is withheld and counted under the shared `undatable_excluded` token. The fix uses the kernel's withholding primitive if the accepted base exports one.
2. An identity whose `mapping_learned_at` does not parse is withheld, as the base's `identity_index` withholds it, with the same reason token until the v1.1 bundle adds an honest one.
3. No base change is asked.

### Test obligations (they land with the integration)

1. **The crash closed.** Take a forward target whose `business_valid_to` is `2026-13-45`, and one whose value is `2026-02-30`, both encoded through the contract. In `latest`, `source_history` and `system_replay`:
   - the composition succeeds;
   - that row is withheld and counted under `undatable_excluded`;
   - every other row is unchanged from the control.
2. **The readable path kept.** A readable `business_valid_to` still judges exactly as R-ENE-42's tests 3 and 4 say.
3. **The identity sibling.** In `system_replay`, an identity whose `mapping_learned_at` is `not-a-date` is withheld and the composition succeeds. A readable value inside the cutoff still resolves.
4. **Mutants.** Removing either guard makes test 1 or test 3 raise. Each no-raise assertion sits beside a positive control on the same fixture (the danger item on vacuous raise pins).

## Sol's decomposition ruling (5895067178), for Energy

**What Sol approved.**
- One bounded shared-kernel extraction on #7870's own carrier, before the release composition.
- The kernel holds the D1, D3 and D4 laws. D2 and D5 stay with their owners.
- The shell and the registry stop importing the semiconductor composer at load.
- Vertical meaning stays vertical, including query literals and authority.
- Industrials' path-disjoint dossier work may proceed in parallel. Energy is not named.

**What it means for Energy.**
1. #7870 moves again, and nothing Energy does speeds it up.
2. The reconciliation re-points nuclear's imports and follows the new registry binding (R-ENE-45).
3. R-ENE-46's fix uses the kernel's primitive where one exists.
4. Energy's integration still starts only after #7870 is released (the ENERGY directive). Nothing on #8002 changes before then.

## The integration, in order (amends the list in `R-ENE-2026-09-29-energy-directive.md`)

Only after #7870 is released and source custody permits:
1. **Reconcile #8002 onto the accepted base.**
   - Re-point nuclear's imports (R-ENE-45).
   - Record `m34_broad` and `my8_swallow_cutoff` per the round-9 closure.
   - Re-run REG-PACKET §1c's gates at the post-merge heads.
2. **ONE writer executes the packet:** §3, §3b, §4, §4b, §5, §5b and §5c.
   - §3's registry edit follows the accepted base's binding.
   - §3b.1 loses its `identity` edit and takes §5c's re-anchor.
   - §5c carries R-ENE-45's and R-ENE-46's obligations.
3. **Review at the reconciliation.** Unchanged (R-ENE-41).
4. **The proof list.** Unchanged, except that its scoped-evidence rung now includes R-ENE-45's round trip.
5. **The separate gates.** Unchanged: the VPS disk hold (#6902), the production credential boundary (Task 10) and Power-Demand (R-ENE-16). Nuclear acceptance is never claimed early.

## Reproduction

**The trees.**
- `r11gate/simB11f` is #8002 over #7870 `a0d7b054ff23`, the round-11 sim.
- `r12gate/newhead_f12d` is #8002 over #7870 `f12db8bff1d1`.

**The bytes.**
- In both trees, `engine/market_ontology/nuclear_theme_research.py` hashes to sha256 `3a795c54c70e3a08…` and `tests/nuclear_research_helpers.py` to `60801c548c0831b2…`. Both equal `git show 508d8c206357:<path>`.
- The base's `semiconductor_theme_research.py` is `722369b33d10753b…` at `a0d7b054ff23` and `a8c48aa7266ec0b3…` at `f12db8bff1d1`.
- Python 3.12.13.

**The commands.**
- Every probe ran as `cd <tree> && PYTHONPATH=<tree> python3.12 <probe>.py`, once per tree.
- The suites ran as `PYTHONPATH=<tree> python3.12 -m pytest -q -p no:cacheprovider --rootdir <tree> <files>`.
- The packet dry-run applied `r12gate/apply_reg_report.py` to a copy of the `f12db8bff1d1` tree. It is the 2026-09-28 dry-run's `apply_reg.py` (REG-PACKET §1c) with one change: a missing anchor is printed and skipped instead of exiting. `apply_reg.py` is sha256 `82fd4f8a86d111ba…` and the copy is `da622ff2b0ba737e…`.

**A confound.** `probe_unreadable_owner_ts` sets curation fields on raw rows while keeping their `curation_revision`. Every modified curation row is therefore refused as `assertion_invalid` before any reader, so its curation rows show no reader behaviour. `probe_encoded_owner_ts` re-encodes each row through the contract and is the record for curation fields. Only the identity rows of `probe_unreadable_owner_ts` are cited, because identity results are not curation assertions.

### `probe_d3.py` — D3, the malformed cutoff

```python
from engine.market_ontology import nuclear_theme_research as nuclear
from engine.market_ontology.semiconductor_theme_research import ResearchRefusal
from tests.nuclear_research_helpers import N03, N03B, nuclear_bundle, nuclear_query
for mode, kw in (("latest", {"source_cutoff": "20261231"}), ("source_history", {"time_mode": "source_history", "source_cutoff": "2026-W53-4"}),
                 ("system_replay", {"time_mode": "system_replay", "source_cutoff": "2026-09-30", "recorded_cutoff": "not-a-date"}),
                 ("latest ok", {"source_cutoff": "2026-09-30"})):
    try:
        p = nuclear.compose_nuclear_research(nuclear_query("reactor_technology", "commercial", **kw), nuclear_bundle(N03, N03B))
        print(f"{mode:15} served selected={p['authorized_coverage'].get('selected')}")
    except ResearchRefusal as exc:
        print(f"{mode:15} ResearchRefusal {getattr(exc, 'status', getattr(exc, 'status_code', '?'))} {str(exc)[:80]}")
    except Exception as exc:
        print(f"{mode:15} RAISE {type(exc).__name__}: {str(exc)[:70]}")
```

On `a0d7b054ff23`:

```text
latest          RAISE ValueError: time data '20261231' does not match format '%Y-%m-%d'
source_history  RAISE ValueError: time data '2026-W53-4' does not match format '%Y-%m-%d'
system_replay   RAISE ValueError: time data 'not-a-date' does not match format '%Y-%m-%d'
latest ok       served selected=2
```

On `f12db8bff1d1`:

```text
latest          ResearchRefusal ? cutoff_unreadable
source_history  ResearchRefusal ? cutoff_unreadable
system_replay   ResearchRefusal ? cutoff_unreadable
latest ok       served selected=2
```

### `probe_bvt_trace.py` — R-ENE-46, the stack of the crash

```python
import copy, json, sys, traceback
from engine.market_ontology import nuclear_theme_research as nuclear
from tests.nuclear_research_helpers import N03, N03B, encode_assertion, nuclear_bundle, nuclear_query
def enc(rec):
    rec = copy.deepcopy(rec); rec["curation_revision"] = None
    return json.loads(encode_assertion(rec))
for mode, kw in (("latest", {}), ("latest+src", {"source_cutoff": "2026-09-30"}),
                 ("source_history", {"time_mode": "source_history", "source_cutoff": "2026-09-30"}),
                 ("system_replay", {"time_mode": "system_replay", "source_cutoff": "2026-09-30", "recorded_cutoff": "2026-09-30"})):
    a = copy.deepcopy(N03); a["temporal"]["business_valid_to"] = "2026-13-45"
    try:
        nuclear.compose_nuclear_research(nuclear_query("reactor_technology", "commercial", **kw), nuclear_bundle(enc(a), enc(N03B)))
        print(f"{mode:15} OK (no raise)")
    except Exception as exc:
        fr = [f for f in traceback.extract_tb(exc.__traceback__) if "market_ontology" in f.filename]
        print(f"{mode:15} RAISE {type(exc).__name__} at " + " <- ".join(f"{f.filename.split('/')[-1]}:{f.lineno}:{f.name}" for f in reversed(fr[-3:])))
```

On `a0d7b054ff23`:

```text
latest          RAISE ValueError at semiconductor_theme_research.py:151:_parse_day <- nuclear_theme_research.py:142:_is_passed_target <- nuclear_theme_research.py:409:_row
latest+src      RAISE ValueError at semiconductor_theme_research.py:151:_parse_day <- nuclear_theme_research.py:142:_is_passed_target <- nuclear_theme_research.py:409:_row
source_history  RAISE ValueError at semiconductor_theme_research.py:151:_parse_day <- nuclear_theme_research.py:142:_is_passed_target <- nuclear_theme_research.py:409:_row
system_replay   RAISE ValueError at semiconductor_theme_research.py:151:_parse_day <- nuclear_theme_research.py:142:_is_passed_target <- nuclear_theme_research.py:409:_row
```

On `f12db8bff1d1`:

```text
latest          RAISE ValueError at semiconductor_theme_research.py:152:_parse_day <- nuclear_theme_research.py:142:_is_passed_target <- nuclear_theme_research.py:409:_row
latest+src      RAISE ValueError at semiconductor_theme_research.py:152:_parse_day <- nuclear_theme_research.py:142:_is_passed_target <- nuclear_theme_research.py:409:_row
source_history  RAISE ValueError at semiconductor_theme_research.py:152:_parse_day <- nuclear_theme_research.py:142:_is_passed_target <- nuclear_theme_research.py:409:_row
system_replay   RAISE ValueError at semiconductor_theme_research.py:152:_parse_day <- nuclear_theme_research.py:142:_is_passed_target <- nuclear_theme_research.py:409:_row
```

### `probe_encoded_owner_ts.py` — R-ENE-46, what the contract admits (the record for curation fields)

```python
"""Seat probe 2026-09-29, part 2: the same unreadable owner timestamps, but carried by a CORRECTLY ENCODED row
(curation_revision recomputed by encode_assertion), so the contract -- not a digest mismatch -- decides admission."""
import copy, json, sys
from engine.market_ontology import nuclear_theme_research as nuclear
from tests.nuclear_research_helpers import N03, N03B, encode_assertion, nuclear_bundle, nuclear_query
VALUES = ["2026-13-45", "2026-02-30", "not-a-date", "20261231", "2026-W53-4", "2026-1-5"]
WATCH = ("assertion_invalid", "undatable", "review_expired", "target_windows")
def enc(rec):
    rec = copy.deepcopy(rec); rec["curation_revision"] = None
    return json.loads(encode_assertion(rec))
def compose(q, bundle):
    try:
        p = nuclear.compose_nuclear_research(q, bundle)
    except Exception as exc:
        return f"RAISE {type(exc).__name__}: {str(exc)[:60]}"
    return f"OK selected={p['authorized_coverage'].get('selected')} lims={sorted(x for x in p['limitations'] if x.startswith(WATCH))}"
q = nuclear_query("reactor_technology", "commercial")
print(f"{'control (both re-encoded)':40} {compose(q, nuclear_bundle(enc(N03), enc(N03B)))}")
CASES = [("N03", ("temporal", "business_valid_to")), ("N03B", ("source", "published_at")),
         ("N03B", ("source", "retained_at")), ("N03", ("review", "review_due_at")), ("N03B", ("review", "reviewed_at"))]
for who, (sec, key) in CASES:
    for v in VALUES:
        a, b = copy.deepcopy(N03), copy.deepcopy(N03B)
        if key == "reviewed_at":
            a["review"]["review_due_at"] = "2026-09-25T00:00:00Z"
        (a if who == "N03" else b)[sec][key] = v
        try:
            a2, b2 = enc(a), enc(b)
        except Exception as exc:
            print(f"{who + '.' + key + '=' + v:40} contract refuses ({type(exc).__name__})"); continue
        print(f"{who + '.' + key + '=' + v:40} contract ADMITS -> {compose(q, nuclear_bundle(a2, b2))}")
print(sys.version.split()[0])
```

The output is byte-identical on both heads:

```text
control (both re-encoded)                OK selected=2 lims=['target_windows_judged_at:2026-09-20']
N03.business_valid_to=2026-13-45         contract ADMITS -> RAISE ValueError: time data '2026-13-45' does not match format '%Y-%m-%d'
N03.business_valid_to=2026-02-30         contract ADMITS -> RAISE ValueError: day is out of range for month
N03.business_valid_to=not-a-date         contract refuses (CurationAssertionError)
N03.business_valid_to=20261231           contract refuses (CurationAssertionError)
N03.business_valid_to=2026-W53-4         contract refuses (CurationAssertionError)
N03.business_valid_to=2026-1-5           contract refuses (CurationAssertionError)
N03B.published_at=2026-13-45             contract ADMITS -> OK selected=2 lims=['target_windows_judged_at:2026-09-20']
N03B.published_at=2026-02-30             contract ADMITS -> OK selected=2 lims=['target_windows_judged_at:2026-09-20']
N03B.published_at=not-a-date             contract refuses (CurationAssertionError)
N03B.published_at=20261231               contract refuses (CurationAssertionError)
N03B.published_at=2026-W53-4             contract refuses (CurationAssertionError)
N03B.published_at=2026-1-5               contract refuses (CurationAssertionError)
N03B.retained_at=2026-13-45              contract refuses (CurationAssertionError)
N03B.retained_at=2026-02-30              contract refuses (CurationAssertionError)
N03B.retained_at=not-a-date              contract refuses (CurationAssertionError)
N03B.retained_at=20261231                contract refuses (CurationAssertionError)
N03B.retained_at=2026-W53-4              contract refuses (CurationAssertionError)
N03B.retained_at=2026-1-5                contract refuses (CurationAssertionError)
N03.review_due_at=2026-13-45             contract refuses (CurationAssertionError)
N03.review_due_at=2026-02-30             contract refuses (CurationAssertionError)
N03.review_due_at=not-a-date             contract refuses (CurationAssertionError)
N03.review_due_at=20261231               contract refuses (CurationAssertionError)
N03.review_due_at=2026-W53-4             contract refuses (CurationAssertionError)
N03.review_due_at=2026-1-5               contract refuses (CurationAssertionError)
N03B.reviewed_at=2026-13-45              contract refuses (CurationAssertionError)
N03B.reviewed_at=2026-02-30              contract refuses (CurationAssertionError)
N03B.reviewed_at=not-a-date              contract refuses (CurationAssertionError)
N03B.reviewed_at=20261231                contract refuses (CurationAssertionError)
N03B.reviewed_at=2026-W53-4              contract refuses (CurationAssertionError)
N03B.reviewed_at=2026-1-5                contract refuses (CurationAssertionError)
3.12.13
```

### `probe_unreadable_owner_ts.py` — the identity sibling (only its identity rows are cited; see the confound above)

```python
"""Seat probe 2026-09-29 (R-ENE-41 reopen, #7870 f12db8bff1d1 D4): does ONE unreadable OWNER timestamp
fail nuclear's whole composition, where the base's published law says the row is WITHHELD, never fatal?
Each value is tried two ways: through the contract encoder (variant -> encode_assertion), and raw
(clone + field set, curation_revision kept) straight into nuclear's pipeline, which validates each row."""
import copy
import dataclasses
import sys
from engine.market_ontology import nuclear_theme_research as nuclear
import json
from tests.nuclear_research_helpers import N03, N03B, encode_assertion, nuclear_bundle, nuclear_query
SRC = {"N03": N03, "N03B": N03B}

VALUES = ["2026-13-45", "not-a-date", "20261231", "2026-W53-4"]
WATCH = ("assertion_invalid", "undatable", "review_expired", "target_windows")


def compose(q, bundle):
    try:
        p = nuclear.compose_nuclear_research(q, bundle)
    except Exception as exc:  # the question IS whether anything escapes
        return f"RAISE {type(exc).__name__}: {str(exc)[:70]}"
    lims = sorted(x for x in p["limitations"] if x.startswith(WATCH))
    return f"OK selected={p['authorized_coverage'].get('selected')} lims={lims}"


def set_path(rec, path, value):
    node = rec
    for key in path[:-1]:
        node = node[key]
    node[path[-1]] = value


def encode_outcome(name, section, key, value):
    try:
        rec = copy.deepcopy(SRC[name]); rec["curation_revision"] = None; rec[section][key] = value
        json.loads(encode_assertion(rec))
        return "admits"
    except Exception as exc:
        return f"refuses({type(exc).__name__})"


q = nuclear_query("reactor_technology", "commercial")
print(f"{'control':44} {compose(q, nuclear_bundle(N03, N03B))}")

CASES = [
    ("N03.temporal.business_valid_to", "N03", ("temporal", "business_valid_to"), "temporal"),
    ("N03B.source.retained_at", "N03B", ("source", "retained_at"), "source"),
    ("N03.review.review_due_at", "N03", ("review", "review_due_at"), None),
]
for label, name, path, section in CASES:
    for value in VALUES:
        enc = encode_outcome(name, section, path[-1], value) if section else "n/a(review not a variant section)"
        a, b = copy.deepcopy(N03), copy.deepcopy(N03B)
        set_path(a if name == "N03" else b, path, value)
        print(f"{label + '=' + value:44} encode:{enc:28} raw:{compose(q, nuclear_bundle(a, b))}")

# reviewed_at feeds _now_of_query (string max); give N03 a readable due date so the comparison runs
for value in VALUES:
    a, b = copy.deepcopy(N03), copy.deepcopy(N03B)
    a["review"]["review_due_at"] = "2026-09-25T00:00:00Z"
    b["review"]["reviewed_at"] = value
    print(f"{'N03B.review.reviewed_at=' + value:44} {'':37} raw:{compose(q, nuclear_bundle(a, b))}")

# identity: mapping_learned_at read with _le in system_replay
label = (N03.get("subject") or {}).get("source_business_label") or (N03.get("subject") or {}).get("label")
for value in ["2026-09-01T00:00:00Z"] + VALUES:
    bundle = nuclear_bundle(N03, N03B)
    ident = ({"source_business_label": label, "mapping_learned_at": value,
              "company_node_id": "company:synthetic", "resolution": "RESOLVED"},)
    bundle = dataclasses.replace(bundle, identity_results=ident) if dataclasses.is_dataclass(bundle) \
        else bundle._replace(identity_results=ident)
    qr = nuclear_query("reactor_technology", "commercial", time_mode="system_replay",
                       recorded_cutoff="2026-09-30", source_cutoff="2026-09-30")
    print(f"{'identity.mapping_learned_at=' + value:44} {'(label=' + str(label)[:24] + ')':37} raw:{compose(qr, bundle)}")
print(sys.version.split()[0])
```

The output is byte-identical on both heads:

```text
control                                      OK selected=2 lims=['target_windows_judged_at:2026-09-20']
N03.temporal.business_valid_to=2026-13-45    encode:admits                       raw:OK selected=1 lims=['assertion_invalid:0', 'target_windows_judged_at:2026-09-20']
N03.temporal.business_valid_to=not-a-date    encode:refuses(CurationAssertionError) raw:OK selected=1 lims=['assertion_invalid:0', 'target_windows_judged_at:2026-09-20']
N03.temporal.business_valid_to=20261231      encode:refuses(CurationAssertionError) raw:OK selected=1 lims=['assertion_invalid:0', 'target_windows_judged_at:2026-09-20']
N03.temporal.business_valid_to=2026-W53-4    encode:refuses(CurationAssertionError) raw:OK selected=1 lims=['assertion_invalid:0', 'target_windows_judged_at:2026-09-20']
N03B.source.retained_at=2026-13-45           encode:refuses(CurationAssertionError) raw:OK selected=1 lims=['assertion_invalid:1', 'target_windows_judged_at:2026-09-20']
N03B.source.retained_at=not-a-date           encode:refuses(CurationAssertionError) raw:OK selected=1 lims=['assertion_invalid:1', 'target_windows_judged_at:2026-09-20']
N03B.source.retained_at=20261231             encode:refuses(CurationAssertionError) raw:OK selected=1 lims=['assertion_invalid:1', 'target_windows_judged_at:2026-09-20']
N03B.source.retained_at=2026-W53-4           encode:refuses(CurationAssertionError) raw:OK selected=1 lims=['assertion_invalid:1', 'target_windows_judged_at:2026-09-20']
N03.review.review_due_at=2026-13-45          encode:n/a(review not a variant section) raw:OK selected=1 lims=['assertion_invalid:0', 'target_windows_judged_at:2026-09-20']
N03.review.review_due_at=not-a-date          encode:n/a(review not a variant section) raw:OK selected=1 lims=['assertion_invalid:0', 'target_windows_judged_at:2026-09-20']
N03.review.review_due_at=20261231            encode:n/a(review not a variant section) raw:OK selected=1 lims=['assertion_invalid:0', 'target_windows_judged_at:2026-09-20']
N03.review.review_due_at=2026-W53-4          encode:n/a(review not a variant section) raw:OK selected=1 lims=['assertion_invalid:0', 'target_windows_judged_at:2026-09-20']
N03B.review.reviewed_at=2026-13-45                                                 raw:OK selected=0 lims=['assertion_invalid:0', 'assertion_invalid:1']
N03B.review.reviewed_at=not-a-date                                                 raw:OK selected=0 lims=['assertion_invalid:0', 'assertion_invalid:1']
N03B.review.reviewed_at=20261231                                                   raw:OK selected=0 lims=['assertion_invalid:0', 'assertion_invalid:1']
N03B.review.reviewed_at=2026-W53-4                                                 raw:OK selected=0 lims=['assertion_invalid:0', 'assertion_invalid:1']
identity.mapping_learned_at=2026-09-01T00:00:00Z (label=Oklo)                          raw:OK selected=2 lims=[]
identity.mapping_learned_at=2026-13-45       (label=Oklo)                          raw:RAISE ValueError: time data '2026-13-45' does not match format '%Y-%m-%d'
identity.mapping_learned_at=not-a-date       (label=Oklo)                          raw:RAISE ValueError: time data 'not-a-date' does not match format '%Y-%m-%d'
identity.mapping_learned_at=20261231         (label=Oklo)                          raw:RAISE ValueError: time data '20261231' does not match format '%Y-%m-%d'
identity.mapping_learned_at=2026-W53-4       (label=Oklo)                          raw:RAISE ValueError: time data '2026-W53-4' does not match format '%Y-%m-%d'
3.12.13
```

### The suites (R-ENE-44)

The ten non-route nuclear test files, then `tests/test_nuclear_research_route.py`, on each head:

```text
a0d7 suite(10 files): 124 passed, 47 warnings in 4.90s
a0d7 route: 4 passed, 34 warnings in 1.64s
f12d suite(10 files): 124 passed, 47 warnings in 5.07s
f12d route: 4 passed, 48 warnings in 1.24s
```

`tests/test_theme_research_api.py` has the same five non-passes on both heads (`diff` empty):

```text
ERROR tests/test_theme_research_api.py::test_served_identity_plane_disagreement_never_reaches_economics
ERROR tests/test_theme_research_api.py::test_served_rights_snapshot_is_read_exactly_once_per_request
ERROR tests/test_theme_research_api.py::test_served_system_replay_is_refused_before_any_reader_fetch
FAILED tests/test_theme_research_api.py::test_served_single_period_nest_degrades_to_witness_economics_missing
FAILED tests/test_theme_research_api.py::test_served_uncovered_witness_is_a_typed_omission_not_a_503
```

`ResearchRefusal.__mro__` on both heads: `['ResearchRefusal', 'ValueError', 'Exception', 'BaseException', 'object']`.

R-ENE-43's rewind, `probe_target_rewind.py` (recorded verbatim in `R-ENE-2026-09-29-energy-directive.md`), gives byte-identical output at `f12db8bff1d1` (`diff` empty).

### The packet dry-run at `f12db8bff1d1` (R-ENE-45, D5)

```text
ok engine/market_ontology/theme_research_mounts.py (1x)
ok engine/market_ontology/theme_research_registry.py (1x)
ok engine/market_ontology/theme_research_registry.py (1x)
ok engine/market_ontology/theme_research_registry.py (1x)
FAIL ANCHOR app/deploy/update.sh: expected 1 got 0: 'engine/theme_graph/(store|rights|curation_assertion)\\.py'
FAIL ANCHOR app/deploy/update.sh: expected 1 got 0: 'engine/market_ontology/(__init__|exposure_map|semiconductor_theme_research|theme_research_'
ok tests/test_deploy_update_self_heal.py (1x)
ok tests/test_theme_research_mount_context.py (1x)
ok tests/test_theme_research_registry.py (3x)
```
