"""Explicit per-job native APT cold-acquisition adapter; no automatic selection.

The pack owner supplies its original absolute deadline, isolated command env
and digest-bound helper sources. Root staging is ephemeral job output, not a
cache service, journal, restart protocol or authority to retry unknown effects.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import re
import selectors
import shutil
import subprocess
import sys
import time

from scripts.ci_apt_cold_acquisition import AcquisitionRefused, Archive, ChildResult, acquire_and_install, make_download_plan
from scripts.ci_apt_native_plan import qualified_direct_packages
from scripts.ci_apt_native_stage import LIMIT, NativeUnknown, RESULT_PREFIX, observe_command, sanitize_reported_errors

ROOT_FILES = ("ci_apt_cold_acquisition.py", "ci_apt_native_plan.py", "ci_apt_native_stage.py", "ci_apt_transaction_contract.py")
BOUND_FILES = (*ROOT_FILES, "ci_browser_native_setup.py", "ci_browser_dependency_capture.py", "ci_browser_dependency_inputs.py")

# Fixed privileged loader only: receives hash-bound code bytes through stdin,
# never imports a candidate filesystem path as root. The sticky /tmp parent
# prevents a non-owner from replacing the resulting root-owned job directory.
BOOTSTRAP = r'''
import base64,hashlib,json,os,pathlib,tempfile
assert os.geteuid()==0
raw=__import__('sys').stdin.buffer.read(1048577)
assert len(raw)<=1048576
packet=json.loads(raw)
allowed={'ci_apt_cold_acquisition.py','ci_apt_native_plan.py','ci_apt_native_stage.py','ci_apt_transaction_contract.py'}
assert set(packet['files'])==set(packet['expected'])==allowed
files={name:base64.b64decode(text,validate=True) for name,text in packet['files'].items()}
assert all(len(data)<=262144 and hashlib.sha256(data).hexdigest()==packet['expected'][name] for name,data in files.items())
root=pathlib.Path(tempfile.mkdtemp(prefix='ci-apt-',dir='/tmp'))
os.chmod(root,0o755)
scripts=root/'scripts';scripts.mkdir(mode=0o755)
files['__init__.py']=b''
for name,data in files.items():
 fd=os.open(scripts/name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o444)
 with os.fdopen(fd,'wb') as target:
  target.write(data);target.flush();os.fsync(target.fileno())
wrapper=('#!/bin/sh\nexec /usr/bin/python3 -I '+str(scripts/'ci_apt_native_stage.py')+' "$@"\n').encode()
fd=os.open(root/'txn-hook',os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o555)
with os.fdopen(fd,'wb') as target:
 target.write(wrapper);target.flush();os.fsync(target.fileno())
os.chmod(scripts,0o555)
print('CI_APT_NATIVE_BOOTSTRAP='+json.dumps({'root':str(root),'expected':packet['expected']},sort_keys=True))
'''


def source_packet(expected: dict[str, str]) -> bytes:
    folder = Path(__file__).parent
    if set(expected) != set(BOUND_FILES):
        raise AcquisitionRefused("HELPER_SOURCE_BINDING_ABSENT")
    observed = {}
    for name in BOUND_FILES:
        with (folder / name).open("rb") as source:
            observed[name] = source.read(262145)
        if len(observed[name]) > 262144:
            raise AcquisitionRefused("HELPER_SOURCE_LIMIT")
    if any(hashlib.sha256(raw).hexdigest() != expected[name] for name, raw in observed.items()):
        raise AcquisitionRefused("HELPER_SOURCE_CHANGED")
    return json.dumps({"files": {name: base64.b64encode(observed[name]).decode("ascii") for name in ROOT_FILES},
                       "expected": {name: expected[name] for name in ROOT_FILES}}, sort_keys=True).encode()


def parsed_result(code: int, raw: bytes, *, mode: str, index=None) -> dict:
    if len(raw) > LIMIT or not raw.startswith(RESULT_PREFIX) or raw.count(b"\n") != 1:
        raise NativeUnknown("NATIVE_RESPONSE_UNPROVEN")
    result = json.loads(raw[len(RESULT_PREFIX):])
    if result.get("mode") != mode or (index is not None and result.get("index") != index):
        raise NativeUnknown("NATIVE_RESPONSE_UNPROVEN")
    if result.get("outcome") not in {"passed", "failed", "timed_out"} or result.get("settlement") not in {"settled", "unknown"}:
        raise NativeUnknown("NATIVE_RESPONSE_UNPROVEN")
    if (code == 0) != (result["outcome"] == "passed" and result["settlement"] == "settled"):
        raise NativeUnknown("NATIVE_RESPONSE_UNPROVEN")
    return result


def failed_download_summaries(records) -> list[list]:
    """Bounded [archive index, native returncode, reported enums] only.

    The core stops new launches on failure and drains at most four children.
    These diagnostics never alter its original outcome/settlement decisions.
    """
    rows = []
    if type(records) is not dict:
        return rows
    for index in range(128):
        result = records.get(index)
        if (type(result) is not dict or result.get("mode") != "download" or
                result.get("outcome") != "failed" or result.get("settlement") != "settled"):
            continue
        code = result.get("returncode")
        if type(code) is not int or not -255 <= code <= 255 or code == 0:
            code = None  # absent/untrusted is not an observed native exit code
        rows.append([index, code, sanitize_reported_errors(result.get("reported_errors"))])
        if len(rows) == 4:
            break
    return rows


@dataclass
class Pending:
    process: object
    output: bytearray
    eof: bool = False


class NativeAptBackend:
    def __init__(self, root: str, command_env: dict, plan):
        if not re.fullmatch(r"/tmp/ci-apt-[A-Za-z0-9_-]+", root):
            raise AcquisitionRefused("PRIVATE_ROOT_UNQUALIFIED")
        self.root, self.command_env, self.plan = root, command_env, plan
        self.records = {}
        self.handles = {}

    def now(self):
        return time.monotonic()

    def argv(self, mode: str, deadline: float, index=None):
        return ("sudo", "-n", "--", "/usr/bin/python3", "-I",
                f"{self.root}/scripts/ci_apt_native_stage.py", mode, repr(deadline),
                *((str(index),) if index is not None else ()))

    def stage(self, mode: str, deadline: float):
        try:
            code, raw = observe_command(self.argv(mode, deadline), deadline=deadline, command_env=self.command_env)
        except NativeUnknown as error:
            self.handles[mode] = error.child_pid
            raise
        result = parsed_result(code, raw, mode=mode)
        self.records[mode] = result
        return result

    def launch(self, index, argv, deadline):
        # Core validates the native selector; privileged stage independently
        # uses the immutable root-owned archive inventory for the same index.
        if time.monotonic() >= deadline:
            raise NativeUnknown("TOTAL_DEADLINE")
        process = subprocess.Popen(self.argv("download", deadline, index), env=self.command_env,
                                   stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT, close_fds=True)
        self.handles[index] = process.pid
        return Pending(process, bytearray())

    def collect(self, children, deadline):
        observations = {}
        with selectors.DefaultSelector() as events:
            for index, child in children.items():
                if child is None:
                    raise NativeUnknown("LAUNCH_RESPONSE_UNKNOWN")
                if not child.eof:
                    events.register(child.process.stdout, selectors.EVENT_READ, index)
            while not observations:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return {i: ChildResult("timed_out", "unknown") for i in children}
                for key, _ in events.select(min(remaining, 0.05)):
                    child = children[key.data]
                    data = os.read(key.fileobj.fileno(), 65536)
                    if not data:
                        child.eof = True; events.unregister(key.fileobj)
                    else:
                        child.output.extend(data)
                        if len(child.output) > LIMIT:
                            raise NativeUnknown("NATIVE_OUTPUT_LIMIT", child.process.pid)
                for index, child in children.items():
                    code = child.process.poll()
                    if code is None or not child.eof:
                        continue
                    child.process.wait(timeout=0)
                    child.process.stdout.close()
                    result = parsed_result(code, bytes(child.output), mode="download", index=index)
                    self.records[index] = result
                    observations[index] = ChildResult(result["outcome"], result["settlement"])
        return observations

    def verify_archive(self, index, archive):
        if archive != self.plan.transaction[index] or self.records[index].get("outcome") != "passed":
            raise AcquisitionRefused("ARCHIVE_RESULT_UNPROVEN")
        # Exact bytes were verified by the bound native stage; the final native
        # hook independently re-verifies root-owned immutable adopted bytes.

    def install_frozen(self, original, deadline):
        if original != self.plan.transaction:
            raise AcquisitionRefused("TRANSACTION_CHANGED")
        try:
            result = self.stage("install", deadline)
        except NativeUnknown as error:
            return ChildResult(error.outcome, "unknown")
        return ChildResult(result["outcome"], result["settlement"])

    def complete_native_transaction(self, original, attempt, deadline):
        if (original != self.plan.transaction or attempt.reason != "NATIVE_DOWNLOAD_FAILED" or
                attempt.outcome != "failed" or attempt.settlement != "settled" or attempt.pending or
                attempt.installation != "never_started" or time.monotonic() >= deadline):
            return None
        failed = False
        for index, outcome, settlement in attempt.observations:
            row = self.records.get(index, {})
            if row.get("mode") != "download" or type(row.get("index")) is not int or row["index"] != index or row.get("outcome") != outcome or row.get("settlement") != settlement:
                return None
            if outcome == "failed":
                # Diagnostic exclusions only. Independent native index trust,
                # fresh native CheckAuth and full frozen bytes remain required.
                if type(row.get("returncode")) is not int or row["returncode"] != 100 or row.get("reported_errors") != ["FETCH"]:
                    return None
                failed = True
        if not failed:
            return None
        self.completion_attempted = True
        result = self.stage("complete", deadline)
        return ChildResult(result["outcome"], result["settlement"])

    def cleanup_success(self):
        if getattr(self, "completion_attempted", False):
            return  # preserve original failed attempt and completion staging
        # Native children are settled. Keep the immutable transaction/install
        # result until browser acquisition also finishes affirmatively.
        result = self.stage("cleanup-downloads", self.deadline)
        if result["outcome"] != "passed" or result["settlement"] != "settled":
            raise NativeUnknown("CLEANUP_UNPROVEN")


def bootstrap_root(packet: bytes, command_env: dict, deadline: float) -> str:
    if not math.isfinite(deadline) or time.monotonic() >= deadline:
        raise AcquisitionRefused("TOTAL_DEADLINE_BEFORE_LAUNCH")
    # Bootstrap input must be written without an unbounded communicate()
    # buffer. All payload bytes are bounded public helper source, no secrets.
    bootstrap = subprocess.Popen(("sudo", "-n", "--", "/usr/bin/python3", "-I", "-c", BOOTSTRAP),
                                 env=command_env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT, close_fds=True)
    try:
        os.set_blocking(bootstrap.stdin.fileno(), False)
        offset = 0
        pending = Pending(bootstrap, bytearray())
        # This small bootstrap has no acquisition children. Still require
        # positive exit AND EOF, with the original deadline, before stages.
        with selectors.DefaultSelector() as events:
            events.register(bootstrap.stdout, selectors.EVENT_READ)
            events.register(bootstrap.stdin, selectors.EVENT_WRITE)
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise NativeUnknown("BOOTSTRAP_RESPONSE_UNKNOWN", bootstrap.pid, "timed_out")
                for key, _ in events.select(min(remaining, 0.05)):
                    if key.fileobj is bootstrap.stdin:
                        offset += os.write(bootstrap.stdin.fileno(), packet[offset:offset + 65536])
                        if offset == len(packet):
                            events.unregister(bootstrap.stdin); bootstrap.stdin.close()
                        continue
                    chunk = os.read(key.fileobj.fileno(), 65536)
                    if not chunk:
                        pending.eof = True; events.unregister(key.fileobj)
                    else:
                        pending.output.extend(chunk)
                        if len(pending.output) > LIMIT:
                            raise NativeUnknown("BOOTSTRAP_RESPONSE_UNKNOWN", bootstrap.pid)
                code = bootstrap.poll()
                if code is not None and pending.eof:
                    bootstrap.wait(timeout=0); bootstrap.stdout.close(); break
        marker = b"CI_APT_NATIVE_BOOTSTRAP="
        if code != 0 or not pending.output.startswith(marker):
            raise NativeUnknown("BOOTSTRAP_RESPONSE_UNKNOWN", bootstrap.pid)
        prepared = json.loads(pending.output[len(marker):])
        if prepared["expected"] != json.loads(packet)["expected"]:
            raise NativeUnknown("BOOTSTRAP_SOURCE_UNPROVEN", bootstrap.pid)
        return prepared["root"]
    except Exception as error:
        raise NativeUnknown("BOOTSTRAP_RESPONSE_UNKNOWN", bootstrap.pid,
                            error.outcome if isinstance(error, NativeUnknown) else "failed") from error


def run_native_setup(*, deadline: float, command_env: dict, expected_sources: dict,
                     browser_stream) -> dict:
    """Called only by the explicit digest-bound pack phase in the original owner."""
    root = None
    backend = None
    installation = "never_started"
    browser_outcome = "never_started"
    original_detail = ""
    original_attempt_detail = ""
    try:
        if type(deadline) not in {int, float} or not math.isfinite(deadline) or deadline <= time.monotonic():
            raise AcquisitionRefused("TOTAL_DEADLINE_BEFORE_LAUNCH")
        if "PLAYWRIGHT_HOST_PLATFORM_OVERRIDE" in command_env:
            raise AcquisitionRefused("DEPENDENCY_PLATFORM_OVERRIDE_UNQUALIFIED")
        packet = source_packet(expected_sources)
        python = shutil.which("python", path=command_env.get("PATH"))
        if python is None:
            raise AcquisitionRefused("DEPENDENCY_PYTHON_ABSENT")
        capture = Path(__file__).with_name("ci_browser_dependency_capture.py")
        code, raw = observe_command((python, str(capture), "playwright"), deadline=deadline, command_env=command_env)
        prefix = b"CI_BROWSER_DEPENDENCY_INPUTS="
        if code != 0 or not raw.startswith(prefix):
            raise AcquisitionRefused("DEPENDENCY_SOURCE_UNQUALIFIED")
        source = json.loads(raw[len(prefix):])
        host = platform.freedesktop_os_release()
        qualified_direct_packages(distribution_version=source["observed_version"], driver_version=source["driver_version"],
                                  bundle_sha256=source["input_sha256"]["driver_bundle"], os_id=host.get("ID"),
                                  os_version=host.get("VERSION_ID"), machine=platform.machine())
        root = bootstrap_root(packet, command_env, deadline)
        backend = NativeAptBackend(root, command_env, None)
        backend.deadline = deadline
        update = backend.stage("update", deadline)
        if update["outcome"] != "passed" or update["settlement"] != "settled":
            raise NativeUnknown("UPDATE_UNPROVEN", update.get("child_pid"), update["outcome"])
        resolved = backend.stage("resolve", deadline)
        if resolved["outcome"] != "passed" or resolved["settlement"] != "settled":
            raise NativeUnknown("RESOLUTION_UNPROVEN", resolved.get("child_pid"), resolved["outcome"])
        backend.plan = make_download_plan(tuple(Archive(**row) for row in resolved["archives"]))
        result = acquire_and_install(backend.plan, backend, deadline=deadline)
        installation = result.installation
        if result.initial_download_failure is not None:
            completion = result.completion
            original_detail = (f"; initial_download_failure={result.initial_download_failure}; "
                               f"completion={completion.outcome if completion else 'unknown'}/{completion.settlement if completion else 'unknown'}")
            original_attempt_detail = original_detail + f"; original_downloads={json.dumps(failed_download_summaries(backend.records), separators=(',', ':'))}; retained {root}"
        if result.outcome != "passed":
            return {"outcome": result.outcome, "returncode": None if result.settlement == "unknown" or result.outcome == "timed_out" else 1, "failure_signature": None,
                    "timeout_settlement": "unknown" if result.settlement == "unknown" else None,
                    "detail": f"native cold acquisition {result.reason}{original_detail}; downloads[index,returncode,reported_errors]={json.dumps(failed_download_summaries(backend.records), separators=(',', ':'))}; installation={result.installation}; retained {root}; pending={result.pending}; handles={backend.handles}; native_children={[(i, r.get('child_pid')) for i, r in backend.records.items() if type(r.get('child_pid')) is int and 0 < r['child_pid'] <= 2147483647]}"}
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return {"outcome": "timed_out", "returncode": None, "failure_signature": None,
                    "timeout_settlement": "not_started", "detail": "native packages applied; original total exhausted before browser acquisition" + original_attempt_detail}
        observation = browser_stream("python -m playwright install chromium", env=command_env, timeout_seconds=remaining)
        browser_outcome = observation.outcome
        if observation.outcome == "passed" and observation.timeout_settlement != "unknown" and result.initial_download_failure is None:
            cleaned = backend.stage("cleanup", deadline)
            if cleaned["outcome"] != "passed" or cleaned["settlement"] != "settled":
                raise NativeUnknown("FINAL_CLEANUP_UNPROVEN")
        return {"outcome": observation.outcome, "returncode": observation.returncode,
                "failure_signature": observation.failure_signature,
                "detail": "native packages applied" + original_attempt_detail + "; " + (observation.detail or f"browser acquisition {observation.outcome}") +
                          (f"; retained {root}" if observation.outcome != "passed" else ""),
                "timeout_settlement": observation.timeout_settlement}
    except AcquisitionRefused as error:
        return {"outcome": "failed", "returncode": 1, "failure_signature": None,
                "timeout_settlement": "unknown" if root is not None else None,
                "detail": f"native cold acquisition refused {str(error)}; installation={installation}; browser={browser_outcome}; retained={root}{original_attempt_detail}"}
    except NativeUnknown as error:
        return {"outcome": error.outcome, "returncode": None, "failure_signature": None,
                "timeout_settlement": "unknown",
                "detail": f"native cold acquisition unproven; installation={installation}; browser={browser_outcome}; retained={root}{original_attempt_detail}; child_pid={error.child_pid}; handles={backend.handles if backend else {}}"}
    except Exception:
        return {"outcome": "failed", "returncode": None, "failure_signature": None,
                "timeout_settlement": "unknown", "detail": f"native cold acquisition unproven; installation={installation}; browser={browser_outcome}; retained={root}{original_attempt_detail}; handles={backend.handles if backend else {}}"}
