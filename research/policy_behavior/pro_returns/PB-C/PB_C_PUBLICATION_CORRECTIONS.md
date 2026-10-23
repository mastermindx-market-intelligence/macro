# PB-C — Publication-integrity correction

Final readback compared the protocol blob with its original freeze commit. The local working copy used for the initial calculations had one extra terminal newline. Its substantive text and every parameter were identical to the canonical original. The publication was corrected before final delivery to restore the original Git protocol byte for byte.

- Original protocol Git blob: `d0b4dd5da49684f13bed8e96feaed434d958df15`.
- Canonical original SHA256: `351cdd278aced686f6ac61bd2f4d9cc30c1e56497083edf5c7b9d8cdcbc78f67`.
- Initial working-copy SHA256, with extra terminal LF: `a2e42071c1de29be8d90b643d15566fc796296b8b9672f5ad7ea8dcf7e5ec4d0`.
- No universe, date, stress definition, taxonomy, event, code, seed, simulation, result or interpretation changed.

The initial independent numerical review refers to its recorded pre-normalization result hash. Root reran the analysis after restoration and compared the complete parsed outputs: the **only** changed field was the protocol-file hash in provenance. A separate-directory rerun then reproduced the final analysis and descriptive outputs byte for byte. The final receipt records their current hashes.

Original Treasury derivation receipts remain unchanged and correctly retain the working-copy protocol hash actually consumed at derivation time. That script used the file for provenance hashing; the recorded stress specifications and calculations are unchanged. This note explicitly relates that historical working-copy hash to the byte-exact canonical Git protocol.

This is a publication/provenance normalization after analysis, not a retrospective amendment to the research choices or a new source of statistical evidence.

## Treasury calendar serialization

The final Git blob audit also found that ordinary text reading had normalized the CSV calendar's CRLF line endings to LF when preparing its Git write. The Git copy was repaired to preserve the original local CSV bytes, matching the frozen derivation receipt and analysis input digest. No calendar value, holiday, date ordering or computation changed. The final publication receipt compares all repository blob hashes with the delivered files.
