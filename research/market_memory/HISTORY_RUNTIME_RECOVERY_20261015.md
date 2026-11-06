# Real-reader shutdown recovery

The first source-integrated CLI produced a correct 23-proxy 2008-09-15 packet,
but Python3.14/Arrow25 hung in process finalization. A targeted sample of the
original read-only process showed Arrow ThreadPool::Shutdown waiting while
PyBuffer destruction attempted PyGILState_Ensure after interpreter finalization.
This is an observed stack, not a blanket claim about every Arrow installation.

The original terminal was terminated; its queued Fabric acceptance response was
interrupted. The canonical original-run status independently confirmed ACCEPTED.
No accept or worker request was replayed. Source artifacts were unmodified.

The parent archive reader now uses ParquetFile with pre_buffer=False and
read(use_threads=False), closes it explicitly, and applies the exact-date Arrow
predicate in memory. A regression forbids the asynchronous dataset scanner.
The retained v1 data and byte hashes were not rewritten. The new same-date CLI
process exited0 in0.452s under a15s subprocess bound, with the same23rows and no
outcomes.117combined tests pass.

Primary API reference: https://arrow.apache.org/docs/python/generated/pyarrow.parquet.ParquetFile.html
Bounded local evidence: own .test-tmp/cli-hang-sample.txt and cli-exit-proof.json.
