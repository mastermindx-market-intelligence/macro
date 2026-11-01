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

## Paired page goldens (`pages/`)

`pages/` holds the fifteen committed `site/` pages these inputs produced: the
thirteen siblings and the hub, byte-equal to `expected_pages` (sha256 and git
blob), plus `macro_rates_curves.html` (blob `72ddcbfbded7`). They are the exact
bytes on #8986's head `9255dba36c9b` and its base `60e8e959d0a0`. Every one of
them carries its paired snapshot's `content_sha256` and `generation_id`.

The preservation tests compare against these goldens, never against live
`site/macro_*.html`. Live pages are render-owned: every render rebakes them from
newer macrodata, so by the time #8986 squash-merged (`0b204cde`) none of the
fourteen live pages matched `expected_pages`, and main went red on a comparison
of two different generations. `test_11_page_goldens_are_the_paired_committed_bytes`
pins each golden's identity. Only `test_11_current_macro_command_region_*` still
reads the live hub, because it checks the current page owner rather than
preservation. A golden refresh replaces inputs and pages together, under the
rule above.
