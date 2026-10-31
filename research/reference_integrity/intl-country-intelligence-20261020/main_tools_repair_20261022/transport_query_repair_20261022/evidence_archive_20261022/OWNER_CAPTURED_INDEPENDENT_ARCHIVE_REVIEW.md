# Owner-captured independent archive review

Reviewer: `/root/intl_query_candidate_review`. Subject: the six-directory manifest prepared from `ba4466fc170f2f4f3cdfdb131ca6b51508703934`.

Disposition: **ACCEPT**, scoped to the reviewed consolidation and preparation procedure, pending immutable resulting-delta verification.

The reviewer independently compared all 259 unique manifest entries with immutable GitHub enumeration: zero missing, extra or mismatched path/blob/size records; per-root counts 43/43/43/44/43/43; 28,918,589 original bytes; safe repository-relative paths; all modes 100644. The reference root is absent at comparison base `2d33475adef502ab6b00b8003356c1b0ad1673c0`, consistent with additions in this PR.

Procedure review confirmed clean-head fencing, exact Git-tree enumeration, unsupported-mode/symlink rejection, live-byte Git-blob verification, deterministic sorted archive construction, and full archive readback checking member names, mode, length, SHA-256 and byte equality. Preparation writes only to temporary staging and performs no deletion.

The reviewer independently assessed the source-claims and RIG guards. These historical copies are outside the source-claims scan. The canonical baseline/proposal/manifest does not reference any of the six roots; required frozen artifact, baseline screenshots and current input/build/proof files remain ordinary checkout files.

The reviewer did not independently read or hash the compressed archive. Its recorded SHA-256 is `df8e74b13511259675f355ccb05aa86fb0b371ddf98fe656e768cf27cf842c02`; root directly observed the full successful round trip.

Final publication must remove exactly the reviewed 259 paths, add only the archive/custody evidence, preserve current product/proof bindings, and recheck the complete PR inventory including every new evidence file against the authority ceiling. This review does not claim that authority or hosted CI has passed.
