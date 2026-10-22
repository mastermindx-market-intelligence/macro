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

## gmi-rel-m2-integ-pins-20261022-r1 — M1 reference package

The seven M1-era envelope/describe tests asserted M1 literals against whatever
package is committed at `data/company_intelligence/relationships/` and broke
when the M2 integration committed the full 5-leaf package. Each keeps every
original literal, now asserted against an M1 REFERENCE PACKAGE each test file
builds itself (module-scoped fixture `m1_reference`: the producer over
`extraction/swks_aapl_m1.jsonl` alone with the exact `_run_producer` argument
list, sha-asserted to the m2_keys FILE_PKG_PIN `cc67c2f9…307bb` / FILE_EDGES_PIN
`51434731…986dd`; never re-pinned). Each also gains a full-data check whose
expected value is re-derived from the committed JSON at test time — no count,
sha, issuer list or edge key typed from today's data, so the parallel
regeneration cannot falsify it.

| test id | original target | M1 literals now asserted on | full-data check added | falsifier |
|---|---|---|---|---|
| test_relationship_m2_envelope.py::test_e1_every_eligible_issuer_accounted | committed package via env.e1_coverage | 283 accounted; D1 assessed == 1; SWKS state "assessed" (m1_reference) | accounted total == eligible count recomputed from leaves_v1.json domain_of; SWKS assessed; D1 assessed == direct recount of committed coverage rows | E1 drops/invents/double-counts an eligible issuer or misclassifies SWKS / D1 assessed rows |
| test_relationship_m2_envelope.py::test_e3_m1_pinned_counted | committed package via env.e3_sources(judging_dirs=[]) | collected_m1_pinned 1; m1_pinned_documents 3; D1 pending 145; D2 pending 137; judging ABSENT (m1_reference) | per domain, issuer-state counts sum to that domain's leaf count from leaves_v1.json | E3 drops or invents any issuer's source state |
| test_relationship_m2_envelope.py::test_real_m1_artifacts | envelope CLI on committed data (subprocess) | schema/as_of/panel; M0 1 edge + 2 obs + clean join; E1 assessed 1; E2 own_filing 1; E8 D1 FOUND + D2 11×ABSENT; E4 OWED; E6 NOT_MEASURABLE; E7 note (script constants monkeypatched to the fixture paths, main() in-process) | default CLI subprocess run: schema/as_of/panel, M0 join_missing == [], E4 OWED, E7 note, E1 eligible_total == independent leaf count | committed-artifacts run drops eligible issuers, breaks the M0 join, or drifts the usefulness note |
| test_relationship_m3_describe.py::test_no_inference_words | committed describe render | banned-word check unchanged on the synthetic render and the M1 reference render (json + txt + stdout) (fixture CLI run) | quoted spans that are byte-exact substrings of the excerpt their own line cites are exempt; unchanged check passes on the remainder; >= 1 exempted span contained a banned word; new narrow-exemption test: non-quoted "will" and a non-substring "will" quote each still fail | an exemption so wide it never fires (dead code), or an unexempted renderer-inflicted banned word |
| test_relationship_m3_describe.py::test_real_m1_describe | committed describe run | 1 edge; REL_KEY entry with pinned names/roles/67% fact/2 verbatims/4 firsts/2 reassertions/amendment line/counters (fixture CLI run) | default run: REL_KEY entry exactly once with SWKS/AAPL supplier/customer; counters edges == independent count of committed relationship_edges.json | renderer drops, duplicates or miscounts entries |
| test_relationship_m3_describe.py::test_correction_demo_pit | committed correction-demo run | T1/T2/T3 PIT literals: 3 then 3 new_revisions, 4 firsts + 2 reassertions at T2, amendment at T3, empty lineage then 1, backfill flags, reproducible (tmp --repo-root mirror holding the fixture files + symlinks) | default run: demo current_package_restatements == direct count of kind "restatement" entries in the committed package JSON, each citing an accession | demo invents, drops or miscounts the current package's restatements |
| test_relationship_m3_describe.py::test_restatement_absent_is_printed_not_synthesized | committed package/describe/demo | M1 reference package kinds contain no restatement; M1 describe restatements_found 0 and no "restatement" on stdout; M1 mirror demo ABSENT + empty census | default runs: describe counters["restatements_found"] and demo current_package_restatements == direct count in the committed package JSON, each entry citing an accession | renderer or demo invents, drops or miscounts restatements against the committed package |
