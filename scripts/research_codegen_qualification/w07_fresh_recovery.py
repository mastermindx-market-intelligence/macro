"""RF w07 freshness/recovery probe. Known-answer arithmetic, then absence
checks of prior own markers as supporting FRESHNESS only (never proof that
no late child exists), then one bounded <=8s wait during which the trusted
host may interrupt after a durable known CID. The script never interrupts a
controller or manages containers. Outer cancellation stays a typed failure.
Import inert; effects only in run().
"""
import json, os, sys, time

MARKERS = ("/tmp/rf-cpu-child.marker", "/tmp/rf-normal-child.marker",
           "/tmp/rf-scratch-limit.bin")
WAIT_S = 8.0
UIDT = 65534


def rec(case, outcome, **kv):
    r = {"schema": "rf.workload.obs.v1", "case_id": case, "outcome": outcome,
         "candidate_admission": False, "containment_qualified": False}
    r.update(kv)
    return r


def emit(r, out=sys.stdout):
    out.write(json.dumps(r, sort_keys=True, separators=(",", ":")) + "\n")


def known_answer(a=6, b=7):
    return a * b


def marker_absence(exists=os.path.exists):
    """True means absent; absence supports freshness only."""
    return {p: not exists(p) for p in MARKERS}


def identity_names():
    return {"uid": os.getuid(), "uid_expected_met": os.getuid() == UIDT,
            "lang_present": "LANG" in os.environ,
            "path_present": "PATH" in os.environ}


def wait_bounded(sleep=time.sleep, now=time.monotonic, seconds=WAIT_S):
    """Bounded wait in small steps; guest supporting total only. The step
    cap also bounds tests whose fake clock never advances."""
    stop_at = now() + seconds
    step = 0.25
    slept = 0.0
    for _ in range(int(seconds / step) + 1):
        left = min(stop_at - now(), seconds - slept)
        if left <= 0:
            break
        s = min(step, left)
        sleep(s)
        slept += s
    return slept


def run(sleep=time.sleep, now=time.monotonic, exists=os.path.exists,
        out=sys.stdout):
    emit(rec("w07.header", "started"), out)
    val = known_answer()
    ok = val == 42
    emit(rec("w07.known_answer", "observed" if ok else "failed",
             value=val, expected=42, match=ok), out)
    emit(rec("w07.freshness_markers", "observed",
             absent=marker_absence(exists),
             note="absence_supports_freshness_only"), out)
    emit(rec("w07.identity_env", "observed", **identity_names()), out)
    out.flush()
    slept = wait_bounded(sleep=sleep, now=now)
    emit(rec("w07.final", "observed", waited_seconds=slept,
             interruption_owned_by="trusted_host",
             cancellation_is_typed_failure=True,
             guest_completion_proof=False), out)
    return 0 if ok else 3


if __name__ == "__main__":
    sys.exit(run())
