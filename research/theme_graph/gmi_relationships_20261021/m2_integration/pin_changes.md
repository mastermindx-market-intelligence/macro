# pin_changes.md — gmi-rel-m2-integ-build-20261022-r2

## data pins (tests/test_relationship_m2_keys.py PKG_PIN / EDGES_PIN)

Produced by F1 (run twice, byte-identical; full stdout in `producer_run.txt`):

    TZ=UTC python3 scripts/build_relationship_observations.py --as-of 2026-10-21T00:00:00Z

    relationship_observations: as_of=2026-10-21T00:00:00Z edges=248 non_edges=1115 revisions=111 warnings=0 package=pkg:698aec7868bbedb6c761

| pin | old (M1-era committed bytes) | new (regenerated committed bytes) |
|---|---|---|
| PKG_PIN | cc67c2f9c065d04f5029c75157eefad19277fde29d2cbda5b2865c0f5d1307bb | e55c5c3637b16196962311c8dd57f7c4ce4e8d77af585db5ffe8e0129f6d77eb |
| EDGES_PIN | 51434731fb33499e77ece20b9a71a9824cc3a76fa46c0fa5d14a9ccb53f986dd | 1b4b249ca5c69871d687c65e54ab88d819e20224757a419c19db4143b7bad684 |

`test_default_extraction_is_the_directory` (producer over the default
extraction DIRECTORY) pins PKG_PIN/EDGES_PIN and passes against the new values.

## FILE-scoped pins added in the same file (deviation note)

`test_m1_outputs_byte_identical_after_rekey` runs the producer over the M1
extraction FILE alone. That run provably produces different bytes from the
directory run (different input set -> different package_id
pkg:56502f8b52805a61749a vs pkg:698aec7868bbedb6c761), so no single constant
pair can satisfy both byte-identity tests. That test keeps the accepted M1
bytes as its oracle via new FILE_PKG_PIN / FILE_EDGES_PIN constants (the old
pin values); PKG_PIN / EDGES_PIN follow the regenerated committed artifact as
F3 directs. Both oracles are exact byte pins; neither test was weakened.

    file-run (M1 file alone): cc67c2f9c065d04f5029c75157eefad19277fde29d2cbda5b2865c0f5d1307bb  observation_package.v2.json
                             51434731fb33499e77ece20b9a71a9824cc3a76fa46c0fa5d14a9ccb53f986dd  relationship_edges.json

## M1 field assertions

No pinned VALUE changed: the SWKS->AAPL edge still carries every pinned field
(`test_m1_edge_exact` passes with the fields verbatim), the revision table is
still the pinned 6 revisions, the correction lineage is still the pinned ACC_26
assessment, and the PIT replay still shows the pinned FY2022-FY2024 history.
Only M1-era COUNT pins became identity-filtered assertions (`_m1_edge`
selection, PIT coverage filtered to SWKS, non_edges filtered to the M1
accessions, extraction-directory-vs-file equality on the SWKS slice), per F2.
