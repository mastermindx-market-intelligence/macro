"""RF w03 output cap probe. Emits at most 1MiB total raw output as fixed
4KiB chunks alternating stdout/stderr; header and final records live inside
the same cap. Host 64KiB truncation and cleanup are expected typed outer
failures, judged by the trusted host. Import inert; effects only in run().
"""
import json, sys, time

TOTAL = 1048576
CHUNK = 4096
DEADLINE_S = 5.0
MAX_STALLS = 64


def rec(case, outcome, **kv):
    r = {"schema": "rf.workload.obs.v1", "case_id": case, "outcome": outcome,
         "candidate_admission": False, "containment_qualified": False}
    r.update(kv)
    return r


def emit(r, out=None):
    o = out if out is not None else sys.stdout
    o.write((json.dumps(r, sort_keys=True, separators=(",", ":")) + "\n")
            .encode())


def write_all(write, data, now=time.monotonic, deadline=DEADLINE_S,
              max_stalls=MAX_STALLS):
    """Bounded write-all handling short writes; typed on stall/deadline."""
    view = memoryview(data)
    off = 0
    stop_at = now() + deadline
    stalls = 0
    while off < len(view):
        if now() >= stop_at:
            raise TimeoutError("write_deadline")
        n = write(view[off:])
        if n > 0:
            off += n
            stalls = 0
        else:
            stalls += 1
            if stalls > max_stalls:
                raise BlockingIOError("no_write_progress")
    return off


def chunk_bytes():
    return b"rf03" + b"." * (CHUNK - 4)


def encoded(r):
    return (json.dumps(r, sort_keys=True, separators=(",", ":")) + "\n").encode()


def run(out=None, err=None, now=time.monotonic, total=TOTAL):
    out = out if out is not None else sys.stdout.buffer
    err = err if err is not None else sys.stderr.buffer
    stop_at = now() + DEADLINE_S
    chunk = chunk_bytes()
    streams = (out, err)
    header = encoded(rec("w03.header", "started", planned_total=total,
                         chunk=CHUNK))
    reserve = 1024
    if total < len(header) + reserve:
        return 3
    try:
        write_all(out.write, header, now=now,
                  deadline=max(0.0, stop_at - now()))
    except (OSError, TimeoutError):
        return 3
    written = 0
    how = "completed"
    for i in range((total - len(header) - reserve) // CHUNK):
        if now() >= stop_at:
            how = "guest_deadline_exceeded"
            break
        try:
            written += write_all(streams[i & 1].write, chunk, now=now,
                                 deadline=max(0.0, stop_at - now()))
        except (TimeoutError, BlockingIOError) as e:
            how = type(e).__name__
            break
        except OSError:
            how = "oserror"
            break
    final = encoded(rec("w03.final", "observed",
        payload_bytes_written=written, ended_how=how,
        host_truncation_expected=True, guest_completion_proof=False))
    if len(final) > reserve:
        return 3
    try:
        write_all(out.write, final, now=now,
                  deadline=max(0.0, stop_at - now()))
    except (OSError, TimeoutError):
        return 3
    return 0 if how == "completed" else 3


if __name__ == "__main__":
    sys.exit(run())
