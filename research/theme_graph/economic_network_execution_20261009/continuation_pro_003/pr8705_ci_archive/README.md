# PR #8705 concluded CI evidence archive

This package preserves the completed, bounded CI evidence review for head
`930125848136f08efd1bb61cc5899d9a5a0eeb51`, CI run `37915994513`, attempt 1.
It contains the exact fifteen GitHub artifact ZIPs and their fifteen extracted
JSON members, the frozen final and preceding audit reports, intermediate and
final receipts, metadata snapshots, bounded source observations and read scripts,
and the existing independent artifact verifier. The CI finding is 12/12 packs,
99/99 selected logical jobs and 324/324 semantic proof steps passed; the owner
job log records 215 passing tests. Packaging does not expand that finding or
grant merge, production or predictive authority.

## Files for durable transfer

- `PR8705_CONCLUDED_CI_EVIDENCE_93012584.tar.gz`: normalized evidence archive.
- `PR8705_CONCLUDED_CI_EVIDENCE_MANIFEST.json`: complete external manifest of
  every regular file in the archive, with relative name, length and SHA-256,
  plus the archive's exact byte length and SHA-256.
- `README.md`: this packaging explanation, also archived as
  `packaging/README.md`.
- `PACKAGING_VERIFICATION_RECEIPT.json`: actual deterministic-build,
  extraction, source-preservation and extracted-verifier results. This is a
  post-build sidecar; it is deliberately not part of the archive it identifies.

The external manifest covers every archive member, including the packaging
script and this README. It is not inserted into the archive, so there is no
unhashed self-referential member. Transfer the archive and manifest together.

## Preserved layout and packaging adjustments

The two evidence directories retain their original relative layout:
`lanes/pr8705_final_ci_review/` and
`lanes/pr8705_release_audit_evidence/`. The preceding independent audit's two
report files retain their names under `lanes/`. This preserves the existing
verifier's sibling-directory references without editing its source or any
frozen report. Absolute source paths embedded in historical receipts remain
unchanged as provenance; the verifier uses the preserved relative layout.

The only added payload files are `packaging/build_and_verify_archive.py`,
`packaging/source_selection.json` and `packaging/README.md`. The only metadata
adjustments are in the outer archive:
lexicographic member order, regular files only, mode 0644, UID/GID zero, empty
owner names, epoch modification time, USTAR format, and a gzip header with no
filename and zero modification time. Original artifact ZIP bytes and their
internal metadata are preserved exactly. No input bytes were redacted,
rewritten, recompressed individually or renamed within the preserved layout.

There are no links, directory entries, duplicate archive members, absolute
member names, traversal components, caches or unrelated files. The raw Actions
log body was not retained and is not in this package. Its pre-existing bounded,
sanitized excerpt and whole-body hash are retained. No credentials or signed
download URLs are included. Ordinary unsigned GitHub API/avatar URLs in the
frozen snapshots are preserved. Packaging does not contact GitHub or the native
device, run application tests, import repository application modules or modify
Git.

## Verification and reproduction

The packager reads each explicit input as a bounded regular file, checks stable
file identity while reading, builds the archive twice and requires identical
bytes, and writes a complete manifest. It checks every inner artifact ZIP for
unique regular-file membership and exact equality with its retained JSON
member. It then extracts the outer archive manually into a new scratch
directory, refusing links and unsafe or duplicate names, verifies every length
and hash and the exact file inventory, and runs the unchanged artifact verifier
with a fresh receipt filename. The resulting semantic receipt must equal the
frozen final receipt in every field except its new creation timestamp. Every
original selected input is read and hash-checked again after verification.

To reconstruct from an extracted preserved layout, choose a new output
directory and run:

```bash
python -B packaging/build_and_verify_archive.py \
  --source-root /absolute/path/to/extracted/layout \
  --output-dir /absolute/path/to/new/output
```

The script uses only Python's standard library. It is create-only for the
archive, manifest, extraction directory and verification sidecar. The byte
determinism check covers two independent encodings of identical frozen inputs
with the same runtime and compression implementation; their versions are
recorded in the receipt. Reproduction with a different compression-library
implementation is not asserted to have the same compressed bytes.

The preserved verifier is also directly runnable from the extracted root:

```bash
python -B lanes/pr8705_final_ci_review/verify_observed_ci_artifacts.py \
  --snapshot native_snapshot_002.json \
  --aggregate ci-semantic-evidence.json \
  --output another_fresh_verification_receipt.json
```

Use a new output filename. A new verification receipt is a new observation;
the frozen reports and their earlier receipts remain unchanged.
