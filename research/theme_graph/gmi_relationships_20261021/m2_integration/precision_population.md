# M2 precision population — package-gated admission

Run: gmi-rel-m2-precpop-20261022-r1 (base 5b442662c672).

## Definition

The precision sample's population is the deduplicated extraction observation
rows (`scripts.relationship_m2_precision._dedupe_rows` output) that
`engine.company_intelligence.relationships.precision.admit_by_package` admits
against `data/company_intelligence/relationships/observation_package.v2.json`:

- Membership is exact on `observation_id` in both directions, plus a
  duplicate-package-id check. Any mismatch fails closed with
  `PACKAGE_MISMATCH: <n> extraction observations not in package, <m> package
  observations not in extraction; first: <id>` — rows are never silently
  dropped, and the sample refuses instead of proceeding on a partial
  population.
- A row is admitted iff its package observation has
  `source_state == "verified"` and `disposition in ("edge", "non_edge")`.
- Every other row is recorded in the manifest's `not_admitted` under
  `"<source_state>/<disposition>"` as a sorted list of observation ids. A
  refused observation is not a claim the package makes: it is never sampled,
  weighted or used as a decoy, and it is never hidden — the ids are in the
  manifest.

Admitted rows keep extraction visit order, so salt-keyed selection is
unchanged for them; `build_population` (excerpt exclusion) is unchanged.

## Counts at this base

Re-derived:

```
$ python3 -c "import json,collections;p=json.load(open('data/company_intelligence/relationships/observation_package.v2.json'));print(collections.Counter((o['source_state'],o['disposition']) for o in p['observations']))"
Counter({('verified', 'non_edge'): 1107, ('verified', 'edge'): 482, ('verified', 'refused'): 8})
```

1597 extraction observation rows after deduplication; membership matches the
package exactly (0 rows absent from the package, 0 package observations absent
from the extraction, no duplicate package ids). 1589 admitted = 482 edge +
1107 non_edge. 8 not admitted, all `verified/refused`, all
`refusal_reason: provider_unnamed`:

```
$ python3 -c "import json;p=json.load(open('data/company_intelligence/relationships/observation_package.v2.json'));rs=[o for o in p['observations'] if o['disposition'] not in ('edge','non_edge')];print(len(rs), sorted({o['refusal_reason'] for o in rs}))"
8 ['provider_unnamed']
```

## Package as a recorded input

The package file's sha256 is recorded in the sample manifest's `inputs`
(alongside extraction files, used excerpts and the leaves file). `score`
refuses with `INPUT_DRIFT` when the package at the recorded path changes, and
with `NOT_ADMITTED_MISMATCH` (both counts named) when the recomputed
`not_admitted` differs from the manifest's. The package path is the `--package`
argument on both `sample` and `score`, defaulting to
`data/company_intelligence/relationships/observation_package.v2.json`.

Nulls printed: at this base `excluded` is `{"EXCERPT_MISSING": [],
"EXCERPT_CORRUPT": []}` and the only `not_admitted` bucket is
`verified/refused` with the 8 ids above. Nothing hidden; this documents a
population definition and its counts, and makes no quality claim.
