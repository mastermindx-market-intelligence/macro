# Development findings retained

The first repair replay exited 1 before writing a PASS result. A synthetic optional open of `10**400` caused pandas `DataFrame.iterrows()` to raise `OverflowError` while constructing a Series, before the new scalar validator was called. The traceback pointed to `retention.py`'s iteration, through pandas `maybe_convert_objects`. Required Close/Volume remained usable by the incumbent extractor.

The repair now iterates with `itertuples(index=True, name=None)` and builds a plain dictionary. This preserves source scalar objects and lets the shared opening validator issue `OPEN_INVALID`. The test accesses the preserved optional scalar with `at` to avoid introducing the same Series coercion in its own assertion. This is a synthetic robustness finding, not an observed vendor-data occurrence.

This note records a development failure; the acceptance evidence applies only to the subsequently hash-bound code and terminal passing replay.

The independent reviewer then challenged `contract.py` SHA-256 `ad90cf372a95ae7ca05691681d95ea9a18e784a1379066e19e15fa05b0ef6b7d` and found two additional boundary gaps. Selecting an earlier row allowed a blob whose claimed availability preceded another finalized row contained in the same bytes. The repair now checks every row's calendar close against the blob-wide availability clock. A correction recorded at exactly the original timestamp also passed, despite the design's later-clock requirement. It now requires strictly later recording. Both counterexamples are retained as new producer controls; publication at the entry anchor remains an explicitly permitted mark-diagnostic boundary.
