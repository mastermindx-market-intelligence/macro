"""Finite, owned execution boundary for authenticated Evaluation HTTP misses.

The pure intelligence_os API remains an in-process derivation API. HTTP callers
use this boundary: one Linux child, a hard address-space limit, a wall deadline,
and a finite result. A two-second reap grace follows the execution deadline.
These are safety limits, not performance acceptance SLOs.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import selectors
import signal
import subprocess
import sys
import threading
import time

ADDRESS_SPACE_BYTES = 1024 * 1024 * 1024
WALL_SECONDS = 45.0
RESULT_BYTES = 16 * 1024 * 1024
CLEANUP_SECONDS = 2.0
_SLOT = threading.BoundedSemaphore(1)
_CLEANUP_UNCONFIRMED = threading.Event()


class CleanupUnconfirmed(RuntimeError):
    """The original owned process group could not be confirmed terminated."""


def _unavailable(code: str) -> dict:
    return {"ok": False, "error": "Could not derive the evidence estate within its safety envelope",
            "error_code": code}


def _collect(command: list[str], *, cwd: Path, seconds: float, limit: int) -> bytes:
    """Drain only a bounded result; kill the owned group before reaping its leader."""
    if sys.platform != "linux":
        raise RuntimeError("Linux process envelope required")
    deadline = time.monotonic() + seconds
    process = subprocess.Popen(command, cwd=cwd, stdin=subprocess.DEVNULL,
                               stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                               close_fds=True, start_new_session=True,
                               env={**os.environ, "OPENBLAS_NUM_THREADS": "1",
                                    "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1",
                                    "NUMEXPR_NUM_THREADS": "1"})
    output = bytearray()
    try:
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout, selectors.EVENT_READ)
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError("evidence deadline")
                if not selector.select(remaining):
                    raise TimeoutError("evidence deadline")
                chunk = os.read(process.stdout.fileno(), min(65536, limit + 1 - len(output)))
                if not chunk:
                    break
                output.extend(chunk)
                if len(output) > limit:
                    raise ValueError("evidence result bound")
        # Observe exit without reaping: keep the leader PID reserved until its
        # descendants have been killed, even when they closed inherited stdout.
        while True:
            status = os.waitid(os.P_PID, process.pid, os.WEXITED | os.WNOHANG | os.WNOWAIT)
            if status is not None:
                break
            if time.monotonic() >= deadline:
                raise TimeoutError("evidence deadline")
            time.sleep(min(0.01, max(0, deadline - time.monotonic())))
        if status.si_code != os.CLD_EXITED or status.si_status != 0:
            raise ValueError("evidence worker failed")
        return bytes(output)
    finally:
        cleanup_error = None
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        except OSError as error:
            cleanup_error = error
        finally:
            if process.stdout:
                process.stdout.close()
            try:
                process.wait(timeout=CLEANUP_SECONDS)
            except (OSError, subprocess.TimeoutExpired) as error:
                cleanup_error = error
        if cleanup_error is not None:
            # Keep a cleanup refusal/unknown sticky in this admin process; a
            # second request must not replace an unconfirmed child generation.
            raise CleanupUnconfirmed("owned child cleanup unconfirmed") from cleanup_error


def response(operation: str, *, engine_id: str = "", force: bool = False,
             root: Path | None = None) -> dict:
    from engine.qledger_store import has_process_local_claims_selection
    if operation not in {"panel", "detail"} or len(engine_id.encode("utf-8")) > 4096:
        return _unavailable("evidence_request_invalid")
    if has_process_local_claims_selection():
        return _unavailable("evidence_binding_not_transferable")
    if sys.platform != "linux":
        return _unavailable("evidence_limits_unavailable")
    if _CLEANUP_UNCONFIRMED.is_set():
        return _unavailable("evidence_cleanup_unconfirmed")
    if not _SLOT.acquire(blocking=False):
        return _unavailable("evidence_derivation_busy")
    try:
        root = Path(root) if root is not None else Path(__file__).resolve().parent.parent
        command = [sys.executable, "-B", "-m", "admin.intelligence_execution", operation,
                   str(root), engine_id, "1" if force else "0"]
        raw = _collect(command, cwd=Path(__file__).resolve().parent.parent,
                       seconds=WALL_SECONDS, limit=RESULT_BYTES)
        frame = json.loads(raw)
        if not isinstance(frame, dict) or frame.get("complete") is not True or not isinstance(frame.get("result"), dict):
            raise ValueError("incomplete evidence frame")
        return frame["result"]
    except CleanupUnconfirmed:
        _CLEANUP_UNCONFIRMED.set()
        return _unavailable("evidence_cleanup_unconfirmed")
    except TimeoutError:
        return _unavailable("evidence_deadline_exceeded")
    except Exception:
        return _unavailable("evidence_execution_unavailable")
    finally:
        _SLOT.release()


def _establish_limits() -> None:
    if sys.platform != "linux":
        raise RuntimeError("unsupported enforcement")
    import resource
    _, hard = resource.getrlimit(resource.RLIMIT_AS)
    cap = ADDRESS_SPACE_BYTES if hard == resource.RLIM_INFINITY else min(ADDRESS_SPACE_BYTES, hard)
    resource.setrlimit(resource.RLIMIT_AS, (cap, cap))
    if resource.getrlimit(resource.RLIMIT_AS) != (cap, cap):
        raise RuntimeError("unconfirmed enforcement")
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def _child() -> int:
    # This module's imports are lightweight. Enforce before importing the estate
    # or opening the selected source; never copy a parent's private snapshot.
    try:
        _establish_limits()
        from admin import intelligence_os
        operation, root, engine_id, force = sys.argv[1:]
        if operation == "panel":
            result = intelligence_os.panel(root=Path(root), force=force == "1")
        elif operation == "detail":
            result = intelligence_os.engine_detail(engine_id, root=Path(root))
        else:
            return 2
        # Complete framing prevents an interrupted/partial derivation becoming
        # a successful response. The parent enforces the transport byte cap.
        payload = json.dumps({"complete": True, "result": result}, allow_nan=False).encode("utf-8")
        if len(payload) > RESULT_BYTES:
            return 3
        sys.stdout.buffer.write(payload)
        sys.stdout.buffer.flush()
        return 0
    except Exception:
        return 4


if __name__ == "__main__":
    raise SystemExit(_child())
