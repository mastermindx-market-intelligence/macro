import errno as ER, json, os, sys, time
MAX_BYTES = 12582912
CHUNK = 65536
DEADLINE_S = 5.0
CHILD_SLEEP_S = 2.0
FL = os.O_WRONLY | os.O_CREAT | os.O_EXCL
SCRATCH = "/tmp/rf-scratch-limit.bin"
CHILD_MARKER = "/tmp/rf-normal-child.marker"
FORBIDDEN = "/rf-forbidden-write"
OWN_FILES = (SCRATCH, CHILD_MARKER)
def rec(case, outcome, **kv):
    r = {"schema": "rf.workload.obs.v1", "case_id": case, "outcome": outcome,
         "candidate_admission": False, "containment_qualified": False}
    r.update(kv)
    return r
def emit(r, out=sys.stdout):
    out.write(json.dumps(r, sort_keys=True, separators=(",", ":")) + "\n")
def ec(e):
    return "errno_" + ER.errorcode.get(getattr(e, "errno", None), "unk")
def write_scratch(opener=None, writer=os.write, closer=os.close,
                  now=time.monotonic, deadline=DEADLINE_S,
                  max_bytes=MAX_BYTES):
    opener = opener or (lambda: os.open(SCRATCH, FL, 0o600))
    chunk = b"." * CHUNK
    end = now() + deadline
    written = 0
    try:
        fd = opener()
    except OSError as e:
        return 0, ec(e)
    try:
        for _ in range((max_bytes + CHUNK - 1) // CHUNK + 64):
            if written >= max_bytes:
                return written, "limit_reached"
            if now() >= end:
                return written, "guest_deadline_exceeded"
            try:
                n = writer(fd, chunk[:min(CHUNK, max_bytes-written)])
            except OSError as e:
                return written, ec(e)
            if n <= 0:
                return written, "no_write_progress"
            written += n
        return written, "attempt_budget"
    finally:
        closer(fd)
def forbidden_write():
    try:
        fd = os.open(FORBIDDEN, FL, 0o600)
    except OSError as e:
        return rec("w06.readonly_root", "observed_denied", category=ec(e))
    os.close(fd)
    return rec("w06.readonly_root", "failed", category="denial_missing")
def child_marker(sleep=time.sleep, exit_fn=os._exit, marker=CHILD_MARKER):
    try:
        sleep(CHILD_SLEEP_S)
        try:
            fd = os.open(marker, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            try:
                os.write(fd, b"rf06")
            finally:
                os.close(fd)
        except OSError:
            pass
    finally:
        exit_fn(0)
def cleanup_own(unlink=os.unlink, now=lambda: 0, end=5):
    gone = []
    for p in OWN_FILES:
        if now() >= end:
            break
        try:
            unlink(p)
            gone.append(p)
        except OSError:
            pass
    return gone
def run(fork=os.fork, wait=os.waitpid, kill=os.kill, sleep=time.sleep,
        now=time.monotonic, out=sys.stdout, exit_fn=None, unlink=None,
        opener=None, writer=os.write, closer=os.close, max_bytes=MAX_BYTES):
    end = now() + DEADLINE_S
    emit(rec("w06.header", "started"), out)
    root = forbidden_write()
    emit(root, out)
    pid = None
    try:
        pid = fork()
        if pid == 0:
            child_marker(sleep=sleep, exit_fn=exit_fn or os._exit)
            (exit_fn or os._exit)(1)
            return 1
        emit(rec("w06.child_fork", "observed", child_pid_recorded=True), out)
    except OSError as e:
        emit(rec("w06.child_fork", "observed", category=ec(e)), out)
    try:
        written, how = write_scratch(opener=opener, writer=writer,
            closer=closer, now=now, max_bytes=max_bytes,
            deadline=max(0.0, end-now()))
        emit(rec("w06.scratch", "observed" if how == "errno_ENOSPC"
                 else "inconclusive", bytes_written=written, ended_how=how,
                 expected_denial=how == "errno_ENOSPC"), out)
    finally:
        if pid and now() < end:
            try:
                kill(pid, 9)
                wait(pid, os.WNOHANG)
            except OSError:
                pass
        gone = cleanup_own(unlink or os.unlink, now, end)
    emit(rec("w06.final", "observed", own_files_removed=len(gone),
             guest_physical_pass=False), out)
    return int(root["outcome"] == "failed")*3

if __name__ == "__main__":
    sys.exit(run())
