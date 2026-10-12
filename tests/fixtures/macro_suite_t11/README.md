# Paired inputs for the macro-suite preservation baseline

These fifteen JSON files are unchanged Git blobs from publication commit
`a58cf3cb6de26b702069515292beeba8309e32ab`, originally under
`site/macrodata/`. The manifest and all fourteen workspace snapshots belong to
`2026-10-11T03:40:41Z`, produced at
`49319de9aafa51427b9c50cbb653d73d35d5288b`.

`source-binding.json` records the source paths, original byte lengths and SHA256
values, plus the expected committed page blob identities observed when this
fixture was recovered. The production reader validates the original schema,
content hash and manifest byte count. No snapshot was reserialized or modified,
and no hash, generation, clock, freshness state or source record was substituted.

The preservation tests replay these fixed publication inputs through the current
renderer and compare the complete original page regions. They retain all thirteen
sibling targets, the hub and its fourteen input workspaces, the per-page build
clock, and the altered-clock and body/provenance mutation guards. Other reader and
builder tests continue to use their normal source/fixture roots.

Nightly artifacts and committed HTML update independently. The latest nightly
snapshot is therefore not the input of an older committed HTML golden. An
intentional golden refresh must carry its actual paired input generation, validate
its original bytes and review semantic changes. Never fall back to current data,
restamp provenance, strip evidence or generate expected output from the candidate
renderer just to obtain a passing comparison.
