# Reproduce the F03 source directory

This rebuild produces audit artifacts only. It does not run the product, write the canonical registry, change Paper or deploy anything. Python 3 and Node.js are sufficient for the included builder and source-logic probes; no package installation is required.

## Exact inputs

The package pin is `6e1862867193ec6486a22001a0e4fb515da20448`. The current-registry input is read from Macro `b66ca0fcfe7d79f1c90dbfa395e2d43ac5824a6e`. [provenance.json](data/provenance.json) contains expected Git blob SHAs for all 18 inputs. The full Macro inventory is frozen in [generated-document-inventory.json.gz](evidence/generated-document-inventory.json.gz), with its [receipt](evidence/inventory-receipt.json). Decompressed SHA-256: `4ddbd8102368d3af8a8a02a54f49ac2dfea485472feb771237c6f9a7d0e77026`.

The original exporter was loaded from immutable Git blobs, including its registry owner, and executed using existing `bind_inventory_commit`, `document_inventory` and `derive_projection` behavior. It read policy/navigation/HTML from the exact Macro inventory pin. `sources.macro` remains the registry's historical source pin; `sources.inventory` records the bound newer enumeration, exactly as the owner's `--inventory-ref` path specifies. This is why fresh Macro enumeration must not be confused with regenerating the canonical registry or refreshing native modules.

## Rebuild in a temporary output directory

From this extracted F03 directory, use an existing readable Macro checkout containing the two pinned commits. The materializer uses `git show` only; it does not fetch, checkout, reset or alter that repository. Seed the fresh output with this exact retained native-effect log before building: the current-effect projection and its source probe require it. This copies evidence; it does not dispatch a Paper operation.

```bash
python3 tools/materialize_inputs.py --repo /absolute/path/to/existing/macro --output /absolute/path/to/f03-inputs
f03_rebuild_dir=$(mktemp -d /tmp/f03-rebuild.XXXXXX)
mkdir -p "$f03_rebuild_dir/paper"
cp paper/native-progress.json "$f03_rebuild_dir/paper/native-progress.json"
python3 tools/build_directory.py --inputs /absolute/path/to/f03-inputs --evidence ./evidence --output "$f03_rebuild_dir"
node tools/verify_directory.mjs "$f03_rebuild_dir"
python3 tools/verify_data.py --inputs /absolute/path/to/f03-inputs --output "$f03_rebuild_dir" --skip-doc-links
```

The builder accepts either uncompressed inventory JSON beside the evidence or the committed gzip. It checks every input blob before generating. Curated relationship claims live in `curation.json`; the tool-local copy must match that source file. HTML templates and the local directory script are build inputs, not production components.

The builder generates directory/data/assignment files. Authored contracts, review and continuity documents are maintained separately and are not overwritten. For a complete final-package link check, use `verify_data.py` without `--skip-doc-links` against the delivered directory.

## Meaning and limits of verification

The source-logic checks execute the directory script in a minimal DOM-shaped harness. They test the previously identified search/ownership/history/router regressions and complete inventory counts. They are explicitly **not** Playwright/browser, screenshot, screen-reader, touch, focus-visibility, responsive layout, zoom, contrast or performance tests.

The data verifier independently compares original IDs and preserved fields against pinned inputs, confirms unique compound identities, checks the action ledger's no-effect state, validates all generated-member dispositions, and resolves relative Markdown/document links. It does not assert successful access to external Paper/GitHub URLs, current live writer custody or formal approval.

The artifact manifest contains byte lengths and SHA-256 for the files frozen at publication. Recompute it after an amendment and treat affected review findings as stale until re-reviewed. The manifest does not hash itself; the containing Git commit supplies immutable identity for that final manifest.

## Refresh only observed assignment returns (current continuation)

The existing `curation.json` and `tools/curation.json` mirrors carry eight immutable return observations. This is an evidence overlay on the original assignment projection, not another route registry. A refresh preserves the frozen page/artboard/route/action files byte-for-byte and regenerates only returned assignment entries, F03's entry, the index, assignment/provenance JSON and the HTML companion.

From this complete owned F03 package:

```bash
python3 tools/build_directory.py --refresh-returns --output .
python3 -B tools/verify_returns.py .
node tools/verify_directory.mjs .
```

The overlay requires every evidence field explicitly, including null native candidates and null RIG receipts. Omission of a previously observed return is rejected rather than interpreted as a withdrawal. An actual withdrawal requires an explicit source-bound replacement observation. All rows validate before any are applied; immutable-source links reject dot-segment normalization. Candidate page IDs and Read me page/board IDs remain separate.

Current operation counts come exclusively from `paper/native-progress.json`; the full-baseline command block above seeds that exact file before building. Without it, temporary output has no current-effect input and must not be represented as a current native package. The complete delivered package, including authored contracts, captures and review evidence, remains the verification target. The old 399-input suite is historical unless separately rerun with its pinned inputs.

`verify_returns.py` additionally compares nine frozen artifacts to their prior-head SHA256/Git blobs and all 36 assignments' non-evidence fields to their prior-head digests. Its checks and the 33 script probes are source checks, not browser/Paper interaction or approval. Keep the two curation mirrors byte-equivalent; update source observations, not the generated JSON by hand.
