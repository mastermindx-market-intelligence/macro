# direction_fix — judged subject_role recorded on observation rows (gmi-rel-m2-dirfix-20261022-r1)

## Defect

`engine/company_intelligence/relationships/judge.py::CandidateMapper._observation_row` validated the judged
`subject_role` against the species' role pair and used it for XBRL magnitude mapping, but never wrote it onto the
observation row. Every materialized row therefore carried no `subject_role` key, and the producer
(`engine/company_intelligence/relationships/package_v2.py::_resolve_direction`) fell back to the species DEFAULT
role (`SPECIES_ROLES[species][2]`). For every judgment in which the FILER is the to-side of the species
(customer / client / licensee / distributor / dependent), the edge was built the wrong way round: the filer was
placed on the from-side while the species semantics say from=supplier/manufacturer/licensor/provider. A blind
precision review found 31 direction errors in a 100-item sample, all on exactly those rows. The committed
judgments were right and were NOT re-judged; nothing here scores, ranks, predicts or sizes.

## Fix (two lines, the only engine change)

In `engine/company_intelligence/relationships/judge.py`, method `_observation_row`, inserted immediately before
the `object_label = (` expression (after the `row = {...}` literal is closed):

```python
        if subject_role is not None:
            row["subject_role"] = subject_role
```

A judgment whose `subject_role` is null keeps a row with NO `subject_role` key, so the M1 rows and every
default-role row keep their exact bytes. `observation_identity` does not take the role, so every observation_id
is unchanged. The extraction contract
(`contracts/company_intelligence/relationship_extraction.v1.schema.json`, `$defs/observation_row`) already
allowed `subject_role`; no contract was edited.

## Re-materialization: rows that gained the key (STEP 4)

All 5 M2 leaves re-materialized from the UNCHANGED committed judgments (candidates + pack index sha pins all
matched on the first try; `verify --strict` missing=0, advisory codes only; second `materialize` run
byte-identical to the first). BYTE_PROOF PASS: same line counts, and every changed row differs ONLY by the added
`subject_role` key.

| species | role | side | rows gained |
|---|---|---|---|
| component_dependency | dependent | TO_SIDE_FLIP | 21 |
| contract_manufacturing | client | TO_SIDE_FLIP | 231 |
| distribution | distributor | TO_SIDE_FLIP | 6 |
| licensing | licensee | TO_SIDE_FLIP | 60 |
| licensing | licensor | default_side | 141 |
| supplier_customer | customer | TO_SIDE_FLIP | 113 |
| supplier_customer | supplier | default_side | 134 |

TOTAL_GAINED 706, TO_SIDE_FLIPS 431 (ORCH-REL-2 expected roughly 450; the real number is 431). GAINED <= JUDGED
holds for every (species, role) cell against the committed judgment entries.

## Edge diff (STEP 6)

```
EDGES old 248 new 248
REMOVED 85 flip_to_new_key 84 flip_merged_into_existing 1 OTHER_REMOVED 0
ADDED 85 partial_flip_split 1 OTHER_ADDED 0
BY_SPECIES_REMOVED {'contract_manufacturing': 50, 'supplier_customer': 19, 'licensing': 5, 'component_dependency': 10, 'distribution': 1}
BY_SPECIES_ADDED {'component_dependency': 10, 'supplier_customer': 19, 'contract_manufacturing': 50, 'distribution': 1, 'licensing': 5}
SWKS_AAPL_EDGE_PRESENT True
EDGE_DIFF PASS
```

Every edge change is a direction flip (84 to new keys; 1 merged into the pre-existing opposite-direction key,
with its mirror split out on the added side). The M1 SWKS<->AAPL edge `rel:2dddc958720e18bf0275` is present
exactly once.

## Producer counts (old -> new)

```
edges=248 -> 248        non_edges=1115 -> 1107        revisions=111 -> 111        warnings=0 -> 8
package=pkg:698aec7868bbedb6c761 -> pkg:4aba1d2a658bdff832c5
```

The 8 new warnings are `relationship-provider-unnamed`: flipped component_dependency rows whose provider side is
unnamed, now surfaced as `refused` dispositions (`excluded dispositions: refused=8` in the envelope print)
instead of silent non-edges. Producer run twice: run A stdout == run B stdout and the artifacts byte-identical
(see `producer_run.txt`); replay rc=0 (sources=1138, failures=0, problems=0).

## Pins (old -> new), tests/test_relationship_m2_keys.py

```
PKG_PIN         e55c5c3637b16196962311c8dd57f7c4ce4e8d77af585db5ffe8e0129f6d77eb -> 455c0b95392e4523bee1aaa483f77fb35ff537bc93080f2c271c2cfc4b64a136
EDGES_PIN       1b4b249ca5c69871d687c65e54ab88d819e20224757a419c19db4143b7bad684 -> d80f23fff40e6e653ed4c0a985e39daf9a3e1a533623d8096609166a5fc0992f
PACKAGE_ID_PIN  pkg:56502f8b52805a61749a (UNCHANGED — it pins the M1 file-scoped run, untouched by this fix)
FILE_PKG_PIN    cc67c2f9c065d04f5029c75157eefad19277fde29d2cbda5b2865c0f5d1307bb (UNCHANGED)
FILE_EDGES_PIN  51434731fb33499e77ece20b9a71a9824cc3a76fa46c0fa5d14a9ccb53f986dd (UNCHANGED)
```

## Immutability statement

Judgments, ledgers, reports and sources byte-identical to 603c3551 (git diff --stat empty).
