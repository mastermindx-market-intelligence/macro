"""Isolated registered-startup rehearsal; never a production launcher."""
import hashlib
import json
import os
import pathlib
import sys
import threading
import traceback

stage = pathlib.Path(sys.argv[1]).resolve()
assert str(stage).startswith("/tmp/rr-publication-rehearsal-20261021-")
receiver = stage / "receiver"
os.chdir(receiver)
sys.path.insert(0, str(receiver))
denied, writes, dispatch_attempts, first_run_attempts, resume_requests = [], set(), [], [], []

def resolved_path(value, dir_fd=None):
    if isinstance(value, int):
        if value in (0, 1, 2):
            return None
        value = os.readlink("/proc/self/fd/" + str(value))
    if isinstance(value, bytes):
        value = os.fsdecode(value)
    path = pathlib.Path(value)
    if not path.is_absolute() and dir_fd not in (None, -1):
        path = pathlib.Path(os.readlink("/proc/self/fd/" + str(dir_fd))) / path
    return path.resolve()

def allowwrite(value, event, dir_fd=None):
    path = resolved_path(value, dir_fd)
    if path is None:
        return
    if not path.is_relative_to(stage):
        denied.append({"event": event, "path": str(path)})
        raise PermissionError("isolated rehearsal write fence")
    writes.add(str(path.relative_to(stage)))

def audit(event, args):
    if event == "open":
        path, mode, flags = args
        if (mode and any(x in mode for x in ("w", "a", "x", "+"))) or (
            isinstance(flags, int) and flags & (
                os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND
            )
        ):
            allowwrite(path, event)
    elif event == "os.mkdir":
        allowwrite(args[0], event, args[2])
    elif event in ("os.remove", "os.rmdir"):
        allowwrite(args[0], event, args[1])
    elif event in ("os.rename", "os.link"):
        allowwrite(args[0], event, args[2])
        allowwrite(args[1], event, args[3])
    elif event == "os.symlink":
        allowwrite(args[1], event, args[2])
    elif event in ("os.truncate", "os.chmod", "os.chown", "os.utime"):
        allowwrite(args[0], event)
    elif event in (
        "socket.connect", "socket.connect_ex", "socket.bind", "socket.sendto",
        "socket.getaddrinfo", "subprocess.Popen", "os.system", "os.posix_spawn",
        "os.exec", "os.fork", "os.forkpty",
    ):
        denied.append({"event": event})
        raise PermissionError("isolated rehearsal network/process fence")

sys.addaudithook(audit)
result = {
    "registered_startup_called": False,
    "startup_completed": False,
    "dispatch_mode": "resume held before registered startup; executor dispatch forbidden",
}
scheduler = None
try:
    from apscheduler.executors.base import BaseExecutor
    from apscheduler.schedulers.base import BaseScheduler, STATE_PAUSED

    def hold_resume(self):
        resume_requests.append({"state": self.state, "job_count": len(self.get_jobs())})
        assert self.state == STATE_PAUSED, "resume requested from an unexpected state"
        # Deliberately do not call the real resume. Registration and preflight still run.

    def forbid_dispatch(self, job, run_times):
        dispatch_attempts.append({"job": job.id, "run_times": [str(x) for x in run_times]})
        raise AssertionError("isolated rehearsal scheduled-job dispatch denied")

    BaseScheduler.resume = hold_resume
    BaseExecutor.submit_job = forbid_dispatch
    original_thread_start = threading.Thread.start

    def guarded_thread_start(self, *args, **kwargs):
        if self.name.endswith("-first-run"):
            first_run_attempts.append(self.name)
            raise AssertionError("isolated rehearsal first-run portfolio dispatch denied")
        return original_thread_start(self, *args, **kwargs)

    threading.Thread.start = guarded_thread_start
    from app import main
    from brain import perception_publication, perception_receipt
    from brain import cli_bridge, codex_bridge, provider_waterfall
    from portfolio import performance_read, performance_projection

    imported = (
        main, perception_publication, perception_receipt,
        cli_bridge, codex_bridge, provider_waterfall,
        performance_read, performance_projection,
    )
    assert all(pathlib.Path(module.__file__).resolve().is_relative_to(receiver) for module in imported)
    result["candidate_modules"] = {
        module.__name__: hashlib.sha256(pathlib.Path(module.__file__).read_bytes()).hexdigest()
        for module in imported
    }
    before_threads = {thread.name for thread in threading.enumerate()}
    result["registered_startup_called"] = True
    main._start_scheduler()
    scheduler = main.app.state.scheduler
    result["startup_completed"] = True
    result["scheduler_running"] = bool(scheduler and scheduler.running)
    result["scheduler_state_before_shutdown"] = getattr(scheduler, "state", None)
    result["first_run_states"] = {
        name: getattr(main.app.state, name, None) for name in (
            "autonomous_first_run", "china_first_run", "hk_first_run",
            "heavyweight_first_run", "etf_first_run",
        )
    }
    result["threads_created"] = sorted(
        {thread.name for thread in threading.enumerate()} - before_threads
    )
    result["jobs"] = [
        {"id": job.id, "next_run_time": str(job.next_run_time)} for job in scheduler.get_jobs()
    ] if scheduler else []
    assert scheduler and scheduler.state == STATE_PAUSED
    assert len(resume_requests) == 1
    assert all(value is False for value in result["first_run_states"].values())
    assert not dispatch_attempts and not first_run_attempts and not denied
    result["qualified"] = True
except BaseException as exc:
    result.update({
        "qualified": False, "exception_type": type(exc).__name__,
        "exception": str(exc), "traceback": traceback.format_exc(),
    })
finally:
    if scheduler and scheduler.running:
        scheduler.shutdown(wait=True)
result.update({
    "resume_requests": resume_requests, "dispatch_attempts": dispatch_attempts,
    "first_run_attempts": first_run_attempts, "denied_events": denied,
    "write_paths": sorted(writes), "python_version": sys.version,
})
(stage / "startup-result.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({"qualified": result.get("qualified"), "startup_completed": result["startup_completed"]}))
sys.exit(0 if result.get("qualified") else 1)
