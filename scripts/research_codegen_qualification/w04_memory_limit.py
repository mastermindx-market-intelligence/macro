"""RF w04 memory probe. Grows up to 384MiB in 256KiB chunks, touching every
4096B page; chunks are retained until the boundary. MemoryError yields a
typed allocator_refusal with nonzero exit; full success or deadline expiry is
INCONCLUSIVE, never a physical PASS. Cause needs trusted host oracles
(memory.current/peak/events, OOM/exit witness). Import inert; effects only in
run().
"""
import json, sys, time

MAX_BYTES = 402653184
CHUNK = 262144
PAGE = 4096
GUEST_DEADLINE_S = 5.0


def rec(case, outcome, **kv):
    r = {"schema": "rf.workload.obs.v1", "case_id": case, "outcome": outcome,
         "candidate_admission": False, "containment_qualified": False}
    r.update(kv)
    return r


def emit(r, out=sys.stdout):
    out.write(json.dumps(r, sort_keys=True, separators=(",", ":")) + "\n")


def touch_pages(buf, page=PAGE):
    n = 0
    for off in range(0, len(buf), page):
        buf[off] = 1
        n += 1
    return n


def grow(alloc, now=time.monotonic, deadline=GUEST_DEADLINE_S,
         max_bytes=MAX_BYTES, chunk=CHUNK, page=PAGE):
    """Returns (pages_touched, bytes_allocated, ended_how)."""
    keep = []
    pages = 0
    stop_at = now() + deadline
    while len(keep) * chunk < max_bytes:
        if now() >= stop_at:
            return pages, len(keep) * chunk, "guest_deadline_exceeded"
        try:
            buf = alloc(chunk)
        except MemoryError:
            return pages, len(keep) * chunk, "allocator_refusal"
        pages += touch_pages(buf, page)
        keep.append(buf)
    return pages, len(keep) * chunk, "intended_boundary_reached"


def run(alloc=None, now=time.monotonic, out=sys.stdout,
        deadline=GUEST_DEADLINE_S, max_bytes=MAX_BYTES, chunk=CHUNK,
        page=PAGE):
    emit(rec("w04.header", "started", max_bytes=max_bytes, chunk=chunk,
             page=page), out)
    alloc = alloc or (lambda n: bytearray(n))
    try:
        pages, total, how = grow(alloc, now=now, deadline=deadline,
                                 max_bytes=max_bytes, chunk=chunk, page=page)
    except Exception as e:
        emit(rec("w04.memory_growth", "failed",
                 error_class=type(e).__name__), out)
        emit(rec("w04.final", "failed", note="typed_unexpected_failure",
                 guest_physical_pass=False), out)
        return 4
    if how == "allocator_refusal":
        emit(rec("w04.memory_growth", "observed", pages_touched=pages,
                 bytes_allocated=total, ended_how=how), out)
        emit(rec("w04.final", "observed", allocator_refusal=True,
                 note="cause_needs_host_oracle", guest_physical_pass=False),
             out)
        return 4
    emit(rec("w04.memory_growth", "inconclusive", pages_touched=pages,
             bytes_allocated=total, ended_how=how), out)
    emit(rec("w04.final", "inconclusive",
             note="boundary_settling_needs_host_oracle",
             guest_physical_pass=False), out)
    return 0


if __name__ == "__main__":
    sys.exit(run())
