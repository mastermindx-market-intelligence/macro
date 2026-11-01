"""RF w02 CPU deadline probe. Finite 100M-iteration accumulation with an 8s
guest fallback deadline; one forked child sleeps <=8s, writes a <=16B own
marker, and always exits. The trusted host outer deadline is authoritative;
caller outer timeout is expected, not a guest completion proof. Import inert.
"""
import errno as ER, json, os, sys, time

MAX_ITERS = 100000000
GUEST_DEADLINE_S = 8.0
CHILD_SLEEP_S = 8.0
MARKER = "/tmp/rf-cpu-child.marker"


def rec(case, outcome, **kv):
    r = {"schema": "rf.workload.obs.v1", "case_id": case, "outcome": outcome,
         "candidate_admission": False, "containment_qualified": False}
    r.update(kv)
    return r


def emit(r, out=sys.stdout):
    out.write(json.dumps(r, sort_keys=True, separators=(",", ":")) + "\n")


def accumulate(n=MAX_ITERS, now=time.monotonic, deadline=GUEST_DEADLINE_S):
    """Bounded arithmetic accumulation, no heavy allocation."""
    acc = 0
    stop_at = now() + deadline
    for i in range(n):
        acc = (acc + i) & 0xFFFFFFFFFFFF
        if not i & 0xFFFFF and now() >= stop_at:
            return acc, i + 1, "guest_deadline_exceeded"
    return acc, n, "iterations_completed"


def write_marker(path=MARKER):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        return os.write(fd, b"rf02")
    finally:
        os.close(fd)


def child_body(sleep=time.sleep, exit_fn=os._exit, marker=MARKER):
    """Leaf branch only: bounded sleep, best-effort marker, always exits."""
    try:
        sleep(CHILD_SLEEP_S)
        try:
            write_marker(marker)
        except OSError:
            pass
    finally:
        exit_fn(0)


def run(fork=os.fork, now=time.monotonic, out=sys.stdout, exit_fn=None,
        sleep=time.sleep, iters=MAX_ITERS):
    emit(rec("w02.header", "started", max_iters=iters,
             guest_deadline_s=GUEST_DEADLINE_S), out)
    try:
        pid = fork()
    except OSError as e:
        emit(rec("w02.child_fork", "observed",
                 category="errno_" + ER.errorcode.get(e.errno, "unknown")), out)
    else:
        if pid == 0:
            child_body(sleep=sleep, exit_fn=exit_fn or os._exit)
            (exit_fn or os._exit)(1)
            return 1
        emit(rec("w02.child_fork", "observed", child_pid_recorded=True), out)
    acc, done, how = accumulate(n=iters, now=now)
    emit(rec("w02.cpu_work", "observed", iterations=done, ended_how=how), out)
    emit(rec("w02.final", "observed", note="outer_timeout_expected",
             guest_completion_proof=False), out)
    return 0


if __name__ == "__main__":
    sys.exit(run())
