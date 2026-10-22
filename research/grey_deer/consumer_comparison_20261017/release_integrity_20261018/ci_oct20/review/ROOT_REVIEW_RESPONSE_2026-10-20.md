# Root response to the independent CI review — 20 October 2026

Both documentary findings are resolved in the current adjudication. The operational ruling remains unchanged: retain the ac08 red result, make no competing RIG repair, and require actual integrated CI for the substantive next evidence commit.

**F1:** the 10:34:12 failure is now correctly attributed to the tested **base** b912fd, following its explicit checkout at log lines 957–958. The 10:28:53 failure belongs to integrated3d1a4e. No new rerun occurred.

**F2:** the already-completed root native [exact-object/path receipt](../EXACT_PATH_AND_BASE_BLOB_READ_2026-10-20.json) is now included. It records ac08/current absence of the old paths, all three failed-base blob identities, and the addition2cca/deletionb915 history. It was observed at2026-10-20T03:46:16.286661+00:00, before the independent review, and its process completed with exit0. No Git operation was replayed to produce this attachment.

The current draft file snippets were requested as lines1–55; their returned SHA fields identify each full repository blob. The revised report explicitly states this limit. The snippets cannot be used to reproduce the full-file hash. Comparing their advertised whole-object Git IDs with the native failed-base object IDs supports the root-observed byte-preservation claim, without treating excerpt bytes as the source objects. Current-only guard inspection establishes present L8 behavior and no guard mutation by this continuation, not a historical full-guard identity proof.

The independent review is preserved at its original reviewed hashes. The exact pre-correction report is also retained as CI_ADJUDICATION_REVIEWED_VERSION_2026-10-20.md.txt. No CI waiver, approval receipt, production acceptance or writer-custody transfer follows from this correction.
