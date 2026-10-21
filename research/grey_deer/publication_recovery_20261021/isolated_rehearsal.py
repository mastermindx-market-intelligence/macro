"""Full eligible-archive copy/startup/restore in an isolated temporary receiver."""
import argparse
import datetime
import hashlib
import json
import os
import pathlib
import re
import shlex
import signal
import shutil
import subprocess
import sys
import tarfile
import traceback
import time
import urllib.request

parser = argparse.ArgumentParser()
parser.add_argument("--stage", required=True)
parser.add_argument("--candidate", required=True)
parser.add_argument("--archive-sha256", required=True)
parser.add_argument("--baseline", required=True)
parser.add_argument("--cohort-sha256", required=True)
args = parser.parse_args()
assert re.fullmatch(r"[0-9a-f]{40}", args.candidate)
assert re.fullmatch(r"[0-9a-f]{40}", args.baseline)
assert re.fullmatch(r"[0-9a-f]{64}", args.archive_sha256)
assert re.fullmatch(r"[0-9a-f]{64}", args.cohort_sha256)
stage = pathlib.Path(args.stage).resolve()
assert re.fullmatch(r"/tmp/rr-publication-rehearsal-20261021-[A-Za-z0-9]+", str(stage))
assert stage.is_dir()
code = pathlib.Path("/opt/mastermind")
canonical = pathlib.Path("/opt/mastermind-live-data")
assert code.resolve() == code and canonical.resolve() == canonical
source, receiver, backup = (stage / name for name in ("source", "receiver", "backup"))
assert all(not path.exists() for path in (source, receiver, backup))
archive = stage / "release.tar"
assert hashlib.sha256(archive.read_bytes()).hexdigest() == args.archive_sha256
assert (stage / "isolated_startup.py").is_file()

def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

def service_state():
    proc = subprocess.run([
        "systemctl", "show", "mastermind.service", "-p", "MainPID", "-p", "NRestarts",
        "-p", "ActiveState", "-p", "ActiveEnterTimestamp",
    ], capture_output=True, text=True, check=True, timeout=10)
    return dict(line.split("=", 1) for line in proc.stdout.splitlines() if "=" in line)

def identity(path):
    raw = path.read_bytes()
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}

def authorities(root):
    result = {}
    for book in ("autonomous", "china", "hk"):
        directory = root / "portfolios" / book
        for name in ("nav_history.jsonl", "account.json", "fills.jsonl"):
            path = directory / name
            assert path.is_file() and path.read_bytes().strip(), "missing or empty authority " + str(path)
            result[str(path.relative_to(root))] = identity(path)
        for name in ("pending_target.json", "paper_transaction.json", "paper_transaction.wal.json"):
            assert not (directory / name).exists(), "pending/WAL state present: " + book + "/" + name
        receipts = directory / "settlement_receipts"
        assert not receipts.exists() or (receipts.is_dir() and not any(receipts.iterdir())), "settlement receipts present"
    cohort = root / "portfolio_forward_evaluation/start.json"
    result[str(cohort.relative_to(root))] = identity(cohort)
    assert result["portfolio_forward_evaluation/start.json"]["sha256"] == args.cohort_sha256
    return result

def health():
    try:
        with urllib.request.urlopen("http://127.0.0.1:8001/health", timeout=10) as response:
            body = json.loads(response.read(1024 * 1024))
            return {"http_status": response.status, **{
                key: body.get(key) for key in (
                    "status", "paper_only", "reasoning_policy_ok", "scheduled_runtime_ok", "commit"
                )
            }}
    except Exception as exc:
        return {"exception_type": type(exc).__name__, "error": str(exc)[:300]}

report = {
    "schema": "grey_deer.full_archive_isolated_rehearsal.v2",
    "candidate": args.candidate, "baseline": args.baseline, "stage": str(stage),
    "archive": {"sha256": args.archive_sha256, "bytes": archive.stat().st_size},
    "started_at": now(), "production_service_mutated": False,
    "scope": "Complete eligible-archive rsync replacement and restoration; actual registered startup with installed Linux dependencies; deterministic pre-resume dispatch hold; live roots read-only in private mount/net/PID namespaces; no producer, model, portfolio, release helper or systemd mutation invoked.",
    "limitations": [
        "Paused registration/startup is not natural scheduled execution or real publication proof.",
        "Temporary receiver data effects are not production effects.",
        "Code restoration is not rollback of future publication or decision evidence.",
        "Unchanged release-helper fault-matrix evidence remains separately scoped.",
    ],
}
backup_verified = False
before = None
live_before = None
exclude = None
startup_child_settled = True

def sync(src, dst, dry=False):
    proc = subprocess.run(
        ["rsync", "-acn" if dry else "-ac", "--delete", "--itemize-changes",
         *exclude, str(src) + "/", str(dst) + "/"],
        capture_output=True, text=True, timeout=90,
    )
    return {"exit_code": proc.returncode, "changes": proc.stdout.splitlines(), "stderr": proc.stderr}

try:
    live_before = service_state()
    assert live_before["ActiveState"] == "active" and int(live_before["MainPID"]) > 0
    namespace = pathlib.Path("/proc") / live_before["MainPID"] / "root/opt/mastermind"
    assert (code / ".deployed_git_sha").read_text().strip() == args.baseline
    assert (namespace / ".deployed_git_sha").read_text().strip() == args.baseline
    before = authorities(canonical)
    assert authorities(namespace / "data") == before, "service data namespace differs from canonical authority"
    report["production_before"] = {"service": live_before, "marker": args.baseline, "health": health()}
    report["authority_snapshot_before"] = before
    for path in (source, receiver, backup):
        path.mkdir()
    with tarfile.open(archive) as handle:
        members = handle.getmembers()
        assert all(not pathlib.PurePosixPath(item.name).is_absolute() and ".." not in pathlib.PurePosixPath(item.name).parts for item in members)
        report["archive"]["members"] = len(members)
        handle.extractall(source, filter="data")
    helper = source / "scripts/deploy_code_to_vps.sh"
    helper_text = helper.read_text()
    exclude = shlex.split(helper_text.split("EXC=(", 1)[1].split("\n)", 1)[0])
    assert exclude and all(value.startswith("--exclude=") for value in exclude)
    report["helper_sha256"] = {
        name: identity(source / "scripts" / name)["sha256"]
        for name in ("deploy_from_git.sh", "deploy_code_to_vps.sh")
    }
    for name, src, dst, dry in (
        ("baseline_copy", code, receiver, False),
        ("backup_copy", receiver, backup, False),
        ("backup_verification", receiver, backup, True),
    ):
        report[name] = sync(src, dst, dry)
        assert report[name]["exit_code"] == 0
        if dry:
            assert not report[name]["changes"]
    backup_verified = True
    data = receiver / "data"
    data.mkdir()
    for relative in before:
        destination = data / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(canonical / relative, destination)
    assert authorities(canonical) == before, "canonical authority changed during snapshot"
    assert authorities(data) == before
    report["candidate_copy"] = sync(source, receiver)
    assert report["candidate_copy"]["exit_code"] == 0
    report["candidate_verification"] = sync(source, receiver, True)
    assert report["candidate_verification"]["exit_code"] == 0 and not report["candidate_verification"]["changes"]
    (receiver / "vendor").symlink_to(code / "vendor", target_is_directory=True)
    (receiver / ".deployed_git_sha").write_text(args.candidate + "\n")
    (stage / "tmp").mkdir()
    protected = sorted({
        str(path.resolve()) for path in (
            code, canonical, code / "vendor", code / "vendor/macro"
        ) if path.exists()
    })
    report["read_only_live_roots"] = protected
    shell = ["set -e", "mount --make-rprivate /"]
    for root in protected:
        shell.extend([
            "mount --bind " + shlex.quote(root) + " " + shlex.quote(root),
            "mount -o remount,bind,ro " + shlex.quote(root),
        ])
    shell.append(
        "exec /opt/mastermind/.venv/bin/python "
        + shlex.quote(str(stage / "isolated_startup.py")) + " " + shlex.quote(str(stage))
    )
    env = {
        "PATH": "/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1", "TMPDIR": str(stage / "tmp"),
        "MASTERMIND_VPS_AUTHORITATIVE": "1", "MASTERMIND_SERVE_ONLY": "0",
        "MASTERMIND_JOBSTORE": "memory", "MASTERMIND_MACRO_MANAGED_EXTERNALLY": "1",
        "MASTERMIND_AUTH_TOKEN": "isolated-rehearsal-fixture-token",
    }
    command = [
        "unshare", "--mount", "--net", "--pid", "--fork", "--kill-child=KILL",
        "--mount-proc", "/bin/bash", "-c", "\n".join(shell),
    ]
    proc = subprocess.Popen(
        command, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, start_new_session=True,
    )
    startup_child_settled = False
    stdout, stderr = "", ""
    communication_completed = False
    try:
        stdout, stderr = proc.communicate(timeout=45)
        communication_completed = True
    finally:
        # The session/process group belongs only to this rehearsal. Terminate any
        # surviving launcher/namespace child before permitting receiver restoration.
        def group_exists():
            try:
                os.killpg(proc.pid, 0)
                return True
            except ProcessLookupError:
                return False
        if group_exists():
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass  # The group exited between observation and termination.
        if not communication_completed:
            stdout, stderr = proc.communicate(timeout=5)
        else:
            proc.wait(timeout=5)
        deadline = time.monotonic() + 5
        while group_exists() and time.monotonic() < deadline:
            time.sleep(0.05)
        startup_child_settled = not group_exists()
        report["startup_process"] = {
            "exit_code": proc.returncode, "launcher_reaped": proc.poll() is not None,
            "process_group_gone": startup_child_settled, "communication_completed": communication_completed,
            "stdout_bytes": len(stdout), "stderr_bytes": len(stderr),
            "stderr_tail": stderr[-4000:],
        }
        (stage / "startup.stdout.txt").write_text(stdout)
        (stage / "startup.stderr.txt").write_text(stderr)
    assert startup_child_settled, "startup child exit unverified; isolated receiver retained"
    report["startup"] = json.loads((stage / "startup-result.json").read_text()) if (
        stage / "startup-result.json"
    ).is_file() else {"result_missing": True}
    report["snapshot_authority_after"] = authorities(data)
    report["all_snapshot_authority_unchanged"] = report["snapshot_authority_after"] == before
    assert proc.returncode == 0 and report["startup"].get("qualified") is True
    assert report["all_snapshot_authority_unchanged"]
except BaseException as exc:
    report["failure"] = {
        "exception_type": type(exc).__name__, "exception": str(exc),
        "traceback": traceback.format_exc(),
    }
finally:
    if backup_verified and startup_child_settled:
        try:
            report["restoration"] = sync(backup, receiver)
            report["restoration_verification"] = sync(backup, receiver, True)
            (receiver / ".deployed_git_sha").write_text(args.baseline + "\n")
        except BaseException as exc:
            report["restoration_failure"] = {"type": type(exc).__name__, "error": str(exc)}
    elif backup_verified:
        report["restoration_skipped"] = "namespace child exit unverified; retain isolated receiver and reconcile original process group"
    try:
        after_service = service_state()
        report["production_after"] = {
            "service": after_service,
            "marker": (code / ".deployed_git_sha").read_text().strip(),
        }
        report["canonical_authority_after"] = authorities(canonical)
        report["all_canonical_authority_unchanged"] = report["canonical_authority_after"] == before
        report["production_identity_unchanged"] = (
            after_service == live_before and report["production_after"]["marker"] == args.baseline
        )
    except BaseException as exc:
        report["after_observation_failure"] = {"type": type(exc).__name__, "error": str(exc)}
    restore = report.get("restoration_verification", {})
    report["qualified"] = bool(
        "failure" not in report
        and report.get("startup", {}).get("qualified")
        and report.get("all_snapshot_authority_unchanged")
        and report.get("all_canonical_authority_unchanged")
        and report.get("production_identity_unchanged")
        and report.get("restoration", {}).get("exit_code") == 0
        and restore.get("exit_code") == 0 and not restore.get("changes")
    )
    report["completed_at"] = now()
    (stage / "REHEARSAL_RESULT.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps({
    key: report.get(key) for key in (
        "candidate", "qualified", "failure", "all_snapshot_authority_unchanged",
        "all_canonical_authority_unchanged", "production_identity_unchanged", "completed_at"
    )
}))
sys.exit(0 if report["qualified"] else 1)
