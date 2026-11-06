"""Actual ASGI health route in the existing isolated, paused startup boundary.

OAuth/API environment entries are explicitly nonsecret presence fixtures. No
authentication, provider execution, job dispatch or production mutation is tested.
"""
import asyncio
import datetime
import hashlib
import json
import os
import pathlib
import sys
import threading
import time
import traceback

stage = pathlib.Path(sys.argv[1]).resolve()
phase = sys.argv[2]
assert str(stage).startswith("/tmp/rr-publication-rehearsal-20261021-")
assert phase in {"candidate", "baseline"}
receiver = stage / "receiver"
os.chdir(receiver)
sys.path.insert(0, str(receiver))
expected = json.loads((stage / "health_route_inputs.json").read_text())
expected_sha = expected["source_manifest"][phase]["commit"]
denied, writes, dispatch_attempts, first_run_attempts, resume_requests = [], set(), [], [], []
health_read_counts = {}
request_active = False

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
        raise PermissionError("isolated health write fence")
    writes.add(str(path.relative_to(stage)))

def audit(event, args):
    if event == "open":
        value, mode, flags = args
        writing = (
            (mode and any(x in mode for x in ("w", "a", "x", "+")))
            or (isinstance(flags, int) and flags & (
                os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND
            ))
        )
        if writing:
            allowwrite(value, event)
        else:
            path = resolved_path(value)
            if path is not None:
                if (
                    path.name in {"auth.json", ".env", ".env.local", "macro-api.env"}
                    or ".ssh" in path.parts
                    or (str(path).startswith("/proc/") and path.name == "environ")
                ):
                    denied.append({"event": "credential_read", "path": str(path)})
                    raise PermissionError("isolated health credential-read fence")
                if request_active and (
                    path.is_relative_to(receiver) or str(path).startswith("/opt/macro/")
                ):
                    key = str(path)
                    health_read_counts[key] = health_read_counts.get(key, 0) + 1
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
        raise PermissionError("isolated health network/process fence")

sys.addaudithook(audit)

def save(suffix, value):
    path = stage / (phase + "-" + suffix + ".json")
    temp = path.with_suffix(".json.tmp")
    temp.write_text(json.dumps(value, indent=2) + "\n")
    os.replace(temp, path)

def snapshot():
    return {
        "resume_requests": list(resume_requests),
        "dispatch_attempts": list(dispatch_attempts),
        "first_run_attempts": list(first_run_attempts),
        "denied_events": list(denied),
        "write_paths": sorted(writes),
    }

result = {
    "schema": "grey_deer.isolated_health_route_child.v1",
    "phase": phase,
    "expected_commit": expected_sha,
    "registered_startup_called": False,
    "startup_completed": False,
    "probe_completed": False,
    "helper_contract_passed": False,
    "provider_execution_allowed": False,
    "credential_material_supplied": False,
    "transport": "httpx ASGITransport; actual FastAPI routing, middleware and complete response body",
    "dispatch_mode": "resume held before registered startup; executor dispatch forbidden",
}
scheduler = None
try:
    from apscheduler.executors.base import BaseExecutor
    from apscheduler.schedulers.base import BaseScheduler, STATE_PAUSED

    def hold_resume(self):
        resume_requests.append({"state": self.state, "job_count": len(self.get_jobs())})
        assert self.state == STATE_PAUSED, "unexpected scheduler state"
        # Registration and preflight run; real resume is deliberately not called.

    def forbid_dispatch(self, job, run_times):
        dispatch_attempts.append({"job": job.id, "run_times": [str(x) for x in run_times]})
        raise AssertionError("isolated health scheduled dispatch denied")

    BaseScheduler.resume = hold_resume
    BaseExecutor.submit_job = forbid_dispatch
    original_thread_start = threading.Thread.start

    def guarded_thread_start(self, *args, **kwargs):
        if self.name.endswith("-first-run"):
            first_run_attempts.append(self.name)
            raise AssertionError("isolated health first-run dispatch denied")
        return original_thread_start(self, *args, **kwargs)

    threading.Thread.start = guarded_thread_start
    startup_started_ns = time.monotonic_ns()
    from app import main
    assert pathlib.Path(main.__file__).resolve() == receiver / "app/main.py"
    assert main._git_sha == expected_sha
    result["registered_startup_called"] = True
    main._start_scheduler()
    scheduler = main.app.state.scheduler
    result["startup_completed"] = True
    result["startup_elapsed_seconds"] = (time.monotonic_ns() - startup_started_ns) / 1e9
    result["scheduler_running"] = bool(scheduler and scheduler.running)
    result["scheduler_state"] = getattr(scheduler, "state", None)
    result["first_run_states"] = {
        name: getattr(main.app.state, name, None) for name in (
            "autonomous_first_run", "china_first_run", "hk_first_run",
            "heavyweight_first_run", "etf_first_run",
        )
    }
    result["jobs"] = [
        {"id": job.id, "next_run_time": str(job.next_run_time)}
        for job in scheduler.get_jobs()
    ]
    assert scheduler and scheduler.state == STATE_PAUSED
    assert len(resume_requests) == 1
    assert all(value is False for value in result["first_run_states"].values())
    assert not dispatch_attempts and not first_run_attempts and not denied
    result["startup_qualified"] = True
    save("startup", {**result, **snapshot()})

    # Constructing this transport does not run lifespan/startup and makes no
    # network connection. There is one real GET and no health warm-up.
    import httpx

    async def request():
        global request_active
        transport = httpx.ASGITransport(app=main.app, raise_app_exceptions=False)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://127.0.0.1:8001",
            trust_env=False, timeout=None,
        ) as client:
            request_active = True
            start_ns = time.monotonic_ns()
            save("request-start", {
                "phase": phase, "monotonic_ns": start_ns,
                "started_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "deadline_seconds": 6,
            })
            response = await client.get("/health")
            # client.get has consumed the full response body at this point.
            complete_ns = time.monotonic_ns()
            request_active = False
            body = response.content
            assert len(body) < 100000, "unexpected health response size"
            try:
                parsed = response.json()
            except Exception:
                parsed = None
            fields = {
                key: parsed.get(key) for key in (
                    "status", "paper_only", "reasoning_backend", "reasoning_policy",
                    "reasoning_policy_ok", "shared_reasoning_available",
                    "codex_available", "scheduled_runtime_ok",
                    "scheduled_runtime_expected", "scheduler_running",
                    "scheduler_started", "commit", "serve_only",
                )
            } if isinstance(parsed, dict) else None
            elapsed = (complete_ns - start_ns) / 1e9
            witness = {
                "phase": phase, "start_monotonic_ns": start_ns,
                "complete_monotonic_ns": complete_ns,
                "elapsed_seconds": elapsed, "http_status": response.status_code,
                "body_bytes": len(body), "body_sha256": hashlib.sha256(body).hexdigest(),
                "body_utf8": body.decode("utf-8", errors="replace"),
                "health": fields, "within_six_seconds": elapsed <= 6.0,
                "actual_scheduler_state": scheduler.state,
            }
            witness["helper_contract_passed"] = bool(
                response.status_code == 200 and elapsed <= 6.0 and fields
                and fields["reasoning_policy_ok"] is True
                and fields["scheduled_runtime_ok"] is True
                and fields["commit"] == expected_sha
            )
            save("response-complete", witness)
            return witness

    result["response"] = asyncio.run(request())
    result["probe_completed"] = True
    result["helper_contract_passed"] = result["response"]["helper_contract_passed"]
    result["health_input_read_counts"] = health_read_counts
    result["loaded_release_modules"] = {
        name: {
            "path": str(pathlib.Path(module.__file__).resolve()),
            "sha256": hashlib.sha256(pathlib.Path(module.__file__).read_bytes()).hexdigest(),
        }
        for name, module in list(sys.modules.items())
        if getattr(module, "__file__", None)
        and pathlib.Path(module.__file__).resolve().is_relative_to(receiver)
        and str(pathlib.Path(module.__file__).resolve().relative_to(receiver))
        in expected["source_manifest"][phase]["files"]
    }
    assert scheduler.state == STATE_PAUSED and len(resume_requests) == 1
    assert not dispatch_attempts and not first_run_attempts and not denied
    result["safety_qualified"] = True
except BaseException as exc:
    result.update({
        "safety_qualified": False, "exception_type": type(exc).__name__,
        "exception": str(exc), "traceback": traceback.format_exc(),
        "health_input_read_counts": health_read_counts,
    })
finally:
    request_active = False
    if scheduler and scheduler.running:
        scheduler.shutdown(wait=True)
result.update(snapshot())
result["python_version"] = sys.version
save("probe", result)
print(json.dumps({
    key: result.get(key) for key in (
        "phase", "startup_completed", "probe_completed", "helper_contract_passed",
        "safety_qualified", "exception_type",
    )
}))
sys.exit(0 if result.get("probe_completed") and result.get("safety_qualified") else 1)
