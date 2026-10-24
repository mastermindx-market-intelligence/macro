#!/usr/bin/env python3
"""Export fixed International release artifacts from local, immutable Git objects.

Owner-run preparation only. This does not prove acquisition, rendering,
publication, deployment, or production acceptance. No worktree bytes are used.
Render paths retain public-relative directories (including fonts/).
"""

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import select
import shutil
import signal
import stat
import subprocess
import sys
import time
from datetime import datetime, timezone


REVIEW_COMMIT = "PENDING_COMMIT_RETAINING_ACTUAL_COMPOSITION_BUILD_RECEIPT"
REVIEW_SOURCE = "PENDING_ACTUAL_INTEGRATED_SOURCE_COMMIT"
FROZEN_REFERENCE_MAIN = "24559ffa06bcf06fa8e9f36bb7e078412bd769fe"
EVIDENCE_ROOT = (
    "research/reference_integrity/intl-country-intelligence-20261020/"
    "main_tools_repair_20261022/transport_query_repair_20261022/"
)
COMPOSITION_ROOT = EVIDENCE_ROOT + "main_composition_brain_20261022/"
RECEIPT_PATH = COMPOSITION_ROOT + "repair_braincomposition20261022_build_receipt.json"
RECEIPT_PREFIX = COMPOSITION_ROOT + "proposed_braincomposition20261022_repair/"
RECEIPT_SHA256 = "PENDING_ACTUAL_COMPOSITION_BUILD_RECEIPT_SHA256"
RECEIPT_BLOB = "PENDING_ACTUAL_COMPOSITION_BUILD_RECEIPT_GIT_BLOB"
BUILD_DRIVER_SHA256 = "73bdd3087b0c55542731cf318ace953e046e1b5415b45c755d41049ba4c0a8ce"
INPUT_SNAPSHOT_SHA256 = "081592644c4f2d425fdde59d7b8e153e4aa214aa00d115ba64b13bd31c145b08"
FX_NAMES = "USDJPY_X USDKRW_X USDTWD_X USDINR_X AUDUSD_X GBPUSD_X EURUSD_X".split()
RENDER_ROUTES = """
account.js chart_i18n.js charts.js dashboard-icons.css dashboard-icons.js
data_base.js favicon.svg fonts/Inter-400.woff2 fonts/Inter-500.woff2
fonts/Inter-600.woff2 fonts/Inter-700.woff2 fonts/Inter-800.woff2
fonts/Inter-900.woff2 fonts/InterDisplay-500.woff2 fonts/InterDisplay-600.woff2
fonts/InterDisplay-700.woff2 intl.html intl_library_search.js intl_workspace.css
intl_workspace.js intl_workspace_entry.js intl_workspace_history.css
intl_workspace_macro.css intl_workspace_risk.css intl_workspace_scenario.js
intl_workspace_state.js intl_workspace_surveillance.css live.js live_config.js
mm_brain.js mm_brain_visuals.css mtf.js nav_market.js navigation-refresh.css
product-nav-icons.css shared_shell.css shared_shell_bridge.js stock-logos.js
stockdata.js stockview.js tablesort.js theme.css theme.js
mm_brain_presentation.js mm_brain_markdown.js mm_brain_finance.js mm_brain_finance.css mm_brain_finance_math_v1.js mm_brain_math.js mm_brain_visuals.js
""".split()
FILE_LIMIT = 128 * 1024 * 1024
TOTAL_LIMIT = 512 * 1024 * 1024
MANIFEST = "export_manifest.json"
ENV = {
    "PATH": "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin",
    "LC_ALL": "C", "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_OPTIONAL_LOCKS": "0",
    "GIT_NO_REPLACE_OBJECTS": "1", "GIT_NO_LAZY_FETCH": "1",
    "GIT_TERMINAL_PROMPT": "0", "GIT_ATTR_NOSYSTEM": "1",
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def utc():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def timeout(_signum, _frame):
    raise TimeoutError("export deadline exceeded")


def git(repo, args, limit=8192):
    """Bound every child read; protocol denial also prevents lazy fetching."""
    binary = shutil.which("git", path=ENV["PATH"])
    require(binary, "local Git executable unavailable")
    command = [binary, "--no-optional-locks", "-c", "protocol.allow=never",
               "-c", "core.fsmonitor=false", "-c", "gc.auto=0", "-C", str(repo)] + args
    child = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                             stderr=subprocess.DEVNULL, env=ENV, start_new_session=True)
    chunks, size, deadline = [], 0, time.monotonic() + 20
    try:
        while True:
            remaining = deadline - time.monotonic()
            require(remaining > 0, "Git read exceeded 20 seconds")
            ready, _, _ = select.select([child.stdout], [], [], remaining)
            require(ready, "Git read exceeded 20 seconds")
            chunk = os.read(child.stdout.fileno(), min(65536, limit - size + 1))
            if not chunk:
                break
            size += len(chunk)
            require(size <= limit, "Git output exceeded its byte limit")
            chunks.append(chunk)
        require(child.wait(timeout=max(0.01, deadline - time.monotonic())) == 0,
                "local Git read failed: " + args[0])
        return b"".join(chunks)
    finally:
        if child.poll() is None:
            try:
                os.killpg(child.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            child.wait(timeout=2)
        child.stdout.close()


def entry(repo, commit, path, limit=FILE_LIMIT):
    raw = git(repo, ["ls-tree", "--full-tree", "-l", "-z", commit, "--", path])
    rows = raw.split(b"\0")
    require(len(rows) == 2 and rows[-1] == b"", "missing or ambiguous Git path: " + path)
    metadata, name = rows[0].split(b"\t", 1)
    mode, kind, blob, size = metadata.decode("ascii").split()
    require(name == path.encode("utf-8"), "Git path mismatch")
    require(mode in ("100644", "100755") and kind == "blob",
            "non-regular Git entry rejected: " + path)
    require(re.fullmatch(r"[0-9a-f]{40}", blob), "unsupported Git object identity")
    length = int(size)
    require(0 <= length <= limit, "file exceeds byte limit: " + path)
    return {"git_path": path, "git_mode": mode, "git_blob": blob, "bytes": length}


def blob_bytes(repo, info):
    data = git(repo, ["cat-file", "blob", info["git_blob"]], info["bytes"])
    require(len(data) == info["bytes"], "Git blob length mismatch")
    identity = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
    require(identity == info["git_blob"], "Git blob identity mismatch")
    return data


def inventory(repo, kind):
    git(repo, ["merge-base", "--is-ancestor", FROZEN_REFERENCE_MAIN, REVIEW_SOURCE])
    if kind == "acquisition":
        paths = ["data/intl/" + name + ".parquet" for name in FX_NAMES]
        return [(name, name) for name in paths], {"kind": "fixed_seven_fx_stores"}
    info = entry(repo, REVIEW_COMMIT, RECEIPT_PATH, 1024 * 1024)
    require(info["git_blob"] == RECEIPT_BLOB, "review receipt Git blob mismatch")
    raw = blob_bytes(repo, info)
    require(hashlib.sha256(raw).hexdigest() == RECEIPT_SHA256, "review receipt hash mismatch")
    receipt = json.loads(raw)
    require(receipt["schema"] == "intl.current_main_build.v1"
            and receipt["source_commit"] == REVIEW_SOURCE
            and receipt["static_dependency_source_commit"] == REVIEW_SOURCE
            and receipt["source_overlays"] == [] and receipt["exit_code"] == 0,
            "unexpected review receipt source binding")
    require(receipt["build_driver_sha256"] == BUILD_DRIVER_SHA256
            and receipt["input_snapshot_sha256"] == INPUT_SNAPSHOT_SHA256
            and receipt["input_snapshot"] == "../../../production_input_snapshot.json"
            and receipt["source_reacquisition"] is False
            and receipt["production_mutation"] is False,
            "composition build/input contract changed")
    require(receipt["kind"] == "ordinary builder with copied existing production stores"
            and receipt["artifact_inventory_kind"] == "build output plus required static dependency inventory",
            "composition receipt does not retain the qualified ordinary-build inventory")
    git(repo, ["merge-base", "--is-ancestor", REVIEW_SOURCE, REVIEW_COMMIT])
    routes = []
    for row in receipt["files"]:
        require(row["path"].startswith(RECEIPT_PREFIX), "unexpected receipt artifact root")
        route = row["path"][len(RECEIPT_PREFIX):]
        require(str(PurePosixPath(route)) == route and not route.startswith("/")
                and ".." not in PurePosixPath(route).parts, "unsafe receipt route")
        require(row["source_path"] in ("site/" + route, "templates/" + route),
                "reviewed source route lost its public-relative path")
        require(re.fullmatch(r"[0-9a-f]{64}", row["sha256"])
                and type(row["bytes"]) is int and row["bytes"] > 0,
                "missing finite reviewed artifact identity")
        routes.append(route)
    require(len(routes) == 51 and len(set(routes)) == 51
            and set(routes) == set(RENDER_ROUTES) | {"logo_config.js"}
            and len(RENDER_ROUTES) == 50 and len(set(RENDER_ROUTES)) == 50,
            "reviewed composed render inventory mismatch")
    return [(route, "site/" + route) for route in sorted(RENDER_ROUTES)], {
        "kind": "reviewed_render_routes_only", "review_commit": REVIEW_COMMIT,
        "reviewed_source_commit": REVIEW_SOURCE, "frozen_reference_main": FROZEN_REFERENCE_MAIN,
        "receipt_path": RECEIPT_PATH,
        "receipt_git_blob": RECEIPT_BLOB, "receipt_sha256": RECEIPT_SHA256,
        "excluded_runtime_overlays": ["logo_config.js"],
        "note": "Inventory only; supplied publication bytes include primary intl.html and "
                "static dependencies, not a claim that build_intl emitted every file.",
    }


def fresh_destination(value, repo):
    path = Path(value)
    require(path.is_absolute() and str(path) == value and ".." not in path.parts,
            "output must be a normalized absolute path")
    require(path != repo and repo not in path.parents, "output must be outside the worktree")
    require(not os.path.lexists(path), "output already exists; choose a fresh directory")
    for ancestor in reversed(path.parents):
        require(stat.S_ISDIR(ancestor.lstat().st_mode), "output parent is not an ordinary directory")
    return path


def write_file(root_fd, name, data, mode):
    """Directory-fd anchored writes, exclusive files, no symlink traversal."""
    parts, opened = PurePosixPath(name).parts, []
    parent = root_fd
    try:
        for part in parts[:-1]:
            try:
                os.mkdir(part, 0o700, dir_fd=parent)
            except FileExistsError:
                pass
            parent = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
            opened.append(parent)
        fd = os.open(parts[-1], os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                     0o600, dir_fd=parent)
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fchmod(handle.fileno(), mode)
            os.fsync(handle.fileno())
        fd = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW, dir_fd=parent)
        with os.fdopen(fd, "rb") as handle:
            require(stat.S_ISREG(os.fstat(handle.fileno()).st_mode), "output is not regular")
            actual = handle.read(len(data) + 1)
        require(actual == data, "exported bytes failed readback")
    finally:
        for fd in reversed(opened):
            os.close(fd)


def manifest(root_fd, report):
    raw = (json.dumps(report, indent=2, sort_keys=True) + "\n").encode()
    require(len(raw) <= 256 * 1024, "manifest exceeded byte limit")
    temporary = ".export_manifest.pending"
    write_file(root_fd, temporary, raw, 0o600)
    os.replace(temporary, MANIFEST, src_dir_fd=root_fd, dst_dir_fd=root_fd)
    os.fsync(root_fd)


def stdout_json(report, state):
    require(not state["write_attempted"], "stdout JSON delivery already started")
    raw = (json.dumps(report, separators=(",", ":")) + "\n").encode()
    require(len(raw) <= 4096, "stdout summary exceeded byte limit")
    fd, deadline = sys.stdout.fileno(), time.monotonic() + 3
    os.set_blocking(fd, False)
    while raw:
        remaining = deadline - time.monotonic()
        require(remaining > 0, "stdout deadline exceeded")
        _, ready, _ = select.select([], [fd], [], remaining)
        require(ready, "stdout deadline exceeded")
        try:
            # Mark before the syscall: a signal may interrupt after bytes reach
            # the pipe but before Python records the returned byte count.
            state["write_attempted"] = True
            written = os.write(fd, raw)
            require(written > 0, "stdout write made no progress")
            state["bytes_confirmed"] += written
            raw = raw[written:]
        except BlockingIOError:
            continue


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--kind", choices=("acquisition", "render"), required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    report = {"schema": "intl.release_artifact_export.v1", "pass": False, "complete": False,
              "kind": args.kind, "commit": args.commit, "started_at": utc(), "files": {},
              "scope": "Immutable extraction provenance only; no release acceptance claim.",
              "limits": {"per_file_bytes": FILE_LIMIT, "total_bytes": TOTAL_LIMIT}}
    root_fd, output = None, None
    stdout_state = {"write_attempted": False, "bytes_confirmed": 0}
    signal.signal(signal.SIGALRM, timeout)
    signal.setitimer(signal.ITIMER_REAL, 235)
    try:
        # Preparation placeholders cannot authorize any export or create output.
        for label, value in (("integrated source", REVIEW_SOURCE), ("build evidence", REVIEW_COMMIT),
                             ("build receipt blob", RECEIPT_BLOB)):
            require(re.fullmatch(r"[0-9a-f]{40}", value), "unresolved immutable " + label)
        require(re.fullmatch(r"[0-9a-f]{64}", RECEIPT_SHA256), "unresolved actual build receipt digest")
        require(re.fullmatch(r"[0-9a-f]{40}", args.commit), "commit must be a full lowercase SHA1")
        require(Path(args.repo).is_absolute(), "repo must be absolute")
        repo = Path(args.repo).resolve(strict=True)
        require(git(repo, ["rev-parse", "--show-toplevel"]).decode().strip() == str(repo),
                "repo must identify the worktree root")
        require(git(repo, ["cat-file", "-t", args.commit]).strip() == b"commit",
                "supplied identity is not a locally available commit")
        output = fresh_destination(args.output, repo)
        paths, report["inventory_binding"] = inventory(repo, args.kind)
        entries = [(name, entry(repo, args.commit, path)) for name, path in paths]
        total = sum(item["bytes"] for _, item in entries)
        require(total <= TOTAL_LIMIT, "export total exceeds byte limit")
        os.mkdir(output, 0o700)
        root_fd = os.open(output, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        initial = os.fstat(root_fd)
        report.update(repo=str(repo), output=str(output), total_bytes=total,
                      expected_file_count=len(entries))
        manifest(root_fd, report)
        for name, info in entries:
            data = blob_bytes(repo, info)
            mode = 0o755 if info["git_mode"] == "100755" else 0o644
            write_file(root_fd, name, data, mode)
            report["files"][name] = dict(info, sha256=hashlib.sha256(data).hexdigest(),
                                         output_mode=format(mode, "04o"))
        current = output.lstat()
        require(stat.S_ISDIR(current.st_mode)
                and (current.st_dev, current.st_ino) == (initial.st_dev, initial.st_ino),
                "output directory identity changed")
        require(len(report["files"]) == len(entries), "incomplete export")
        report.update({"pass": True, "complete": True, "finished_at": utc()})
        manifest(root_fd, report)
        stdout_json({"schema": report["schema"], "pass": True, "complete": True,
                     "kind": args.kind, "commit": args.commit, "files": len(entries),
                     "total_bytes": total, "manifest": str(output / MANIFEST)}, stdout_state)
        return 0
    except BaseException as exc:
        # Reserve a finite finalization window, including failed stdout delivery.
        signal.setitimer(signal.ITIMER_REAL, 5)
        report.update({"pass": False, "complete": False, "finished_at": utc(),
                       "error": type(exc).__name__ + ": " + str(exc)[:400],
                       "stdout_delivery": dict(stdout_state)})
        try:
            if root_fd is not None:
                manifest(root_fd, report)
            # Never append a second JSON after any attempted stdout write,
            # including a partial write whose byte count was interrupted.
            if not stdout_state["write_attempted"]:
                stdout_json({"schema": report["schema"], "pass": False, "complete": False,
                             "kind": args.kind, "commit": args.commit, "error": report["error"],
                             "output": str(output) if root_fd is not None else None}, stdout_state)
        except BaseException:
            pass
        return 1
    finally:
        if root_fd is not None:
            os.close(root_fd)
        signal.setitimer(signal.ITIMER_REAL, 0)


if __name__ == "__main__":
    sys.exit(main())
