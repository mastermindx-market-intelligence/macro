"""RF w05 process limit probe. Up to 160 bounded fork attempts; each child
sleeps <=2s then exits without descendants. The parent retains only its own
recorded child pids and reaps only those within a bounded cleanup, never a
broad group. Fork EAGAIN is a supporting observation; exhausting all attempts
without refusal is UNPROVEN for the intended guest task limit. No guest
RLIMIT is invented. Import inert; effects only in run().
"""
import errno as ER, json, os, sys, time

MAX_ATTEMPTS = 160
PARENT_DEADLINE_S = 5.0
CHILD_SLEEP_S = 2.0


def rec(case, outcome, **kv):
    r = {"schema": "rf.workload.obs.v1", "case_id": case, "outcome": outcome,
         "candidate_admission": False, "containment_qualified": False}
    r.update(kv)
    return r


def emit(r, out=sys.stdout):
    out.write(json.dumps(r, sort_keys=True, separators=(",", ":")) + "\n")


def leaf(sleep=time.sleep, exit_fn=os._exit):
    """Leaf child branch: bounded sleep, then unconditional exit."""
    try:
        sleep(CHILD_SLEEP_S)
    finally:
        exit_fn(0)


def bounded_reap(pids, wait=os.waitpid, kill=os.kill, now=time.monotonic,
                 end=0.0):
    """Terminate and nonblocking wait only recorded own pids; bounded by list length
    and the parent deadline."""
    reaped = []
    for pid in pids:
        if now() >= end:
            break
        try:
            kill(pid, 9)
        except OSError:
            pass
        try:
            got, _ = wait(pid, os.WNOHANG)
            if got == pid:
                reaped.append(got)
        except OSError:
            pass
    return reaped


def run(fork=os.fork, wait=os.waitpid, kill=os.kill, sleep=time.sleep,
        now=time.monotonic, out=sys.stdout, exit_fn=None):
    emit(rec("w05.header", "started", max_attempts=MAX_ATTEMPTS,
             parent_deadline_s=PARENT_DEADLINE_S), out)
    stop_at = now() + PARENT_DEADLINE_S
    pids = []
    cats = {}
    stopped = "max_attempts"
    for _ in range(MAX_ATTEMPTS):
        if now() >= stop_at:
            stopped = "parent_deadline"
            break
        try:
            pid = fork()
        except OSError as e:
            code = "errno_" + ER.errorcode.get(e.errno, "unknown")
            cats[code] = cats.get(code, 0) + 1
            stopped = "fork_refused" if e.errno == ER.EAGAIN \
                else "typed_fork_error"
            break
        if pid == 0:
            leaf(sleep=sleep, exit_fn=exit_fn or os._exit)
            (exit_fn or os._exit)(1)
            return 1
        pids.append(pid)
    reaped = bounded_reap(pids, wait, kill, now, stop_at)
    outcome = {"fork_refused": "observed", "parent_deadline": "inconclusive",
               "typed_fork_error": "inconclusive"}.get(stopped, "unproven")
    tried = len(pids) + (1 if stopped.endswith("_error") or
                         stopped == "fork_refused" else 0)
    emit(rec("w05.fork_attempts", outcome, attempts=tried,
             children_created=len(pids), stopped_how=stopped,
             refusal_categories=cats, own_pids_retained=len(pids),
             reaped_own=len(reaped), guest_task_limit_claim=False), out)
    emit(rec("w05.final", "observed", note="host_pids_limit_is_host_oracle",
             guest_physical_pass=False), out)
    return 0


if __name__ == "__main__":
    sys.exit(run())
