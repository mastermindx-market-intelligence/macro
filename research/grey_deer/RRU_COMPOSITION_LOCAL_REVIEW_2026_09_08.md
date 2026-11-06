# Composition candidate: executed review checkpoints

This is a synthetic, in-memory candidate, not installed production code.
The original source remains pinned to eb9e91961ddc4f3043d0dad358602525e66eccda.
The four affected source blobs were independently compared to current main
0b30e044b6456a96f1d6e1a9885987691a2b46dc and were byte-identical.

Initial integration test: 91 cases; baseline 90 assertion failures/one legacy pass,
then candidate 91 passed. The test uses all ten profiles, actual percentile code,
actual projection/recovery functions and the actual shared card template.

The first browser matrix completed 32 mechanical checks with no overflow and
working keyboard disclosure. Visual review REJECTED it as final design evidence:
the fixture omitted the host body/help styles, making dark cards sit on a light
canvas and exposing help text. Separately, the candidate still painted a partial
low-score reading with a green check/CALM badge. That is a genuine candidate bug.
The new eight-case edge suite reproduced that defect (one failure, seven controls
passed). Existing snapshot-error/invalid-profile guards passed those edge tests.
The original 32 images and their receipt are retained as a failed visual checkpoint.

Neither passing synthetic checks nor a corrected fixture clears source custody,
calibration applicability, production publication, full-route or independent review.
