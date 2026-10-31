"""Paired actual health-route qualification in temporary receivers only.

No release helper, systemd mutation, provider call or scheduled job is invoked.
The production service is observed by identity and hashes; it is not health-polled.
"""
import argparse
import datetime
import hashlib
import json
import os
import pathlib
import re
import shlex
import shutil
import signal
import subprocess
import sys
import tarfile
import time
import traceback

parser = argparse.ArgumentParser()
parser.add_argument("--stage", required=True)
parser.add_argument("--archive-sha256", required=True)
args = parser.parse_args()
stage = pathlib.Path(args.stage).resolve()
assert re.fullmatch(r"/tmp/rr-publication-rehearsal-20261021-[A-Za-z0-9]+", str(stage))
assert re.fullmatch(r"[0-9a-f]{64}", args.archive_sha256)
assert stage.is_dir()
inputs = json.loads((stage / "health_route_inputs.json").read_text())
source_manifest = inputs["source_manifest"]
candidate = source_manifest["candidate"]["commit"]
baseline = source_manifest["baseline"]["commit"]
assert candidate == "87d4af0a152eefa3c5f441f5600fae9133b3deaa"
assert baseline == "fe7afd0111141bae27927715e709d074fea729e2"
cohort_sha = "75d5182d55ffc7e569f50008d9293682cadf56130d42b00eaba23412e2e8585c"
code = pathlib.Path("/opt/mastermind")
canonical = pathlib.Path("/opt/mastermind-live-data")
macro = (code / "vendor/macro").resolve()
assert code.resolve() == code and canonical.resolve() == canonical
assert str(macro) == "/opt/macro"
source, receiver, backup, frozen = (stage / n for n in ("source", "receiver", "backup", "frozen"))
assert all(not p.exists() for p in (source, receiver, backup, frozen))
archive = stage / "release.tar"
assert hashlib.sha256(archive.read_bytes()).hexdigest() == args.archive_sha256
assert (stage / "isolated_health_route.py").is_file()

def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

def identity(path):
    raw = path.read_bytes()
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}

def service_state():
    proc = subprocess.run([
        "systemctl", "show", "mastermind.service", "-p", "MainPID", "-p", "NRestarts",
        "-p", "ActiveState", "-p", "ActiveEnterTimestamp",
    ], capture_output=True, text=True, check=True, timeout=10)
    return dict(line.split("=", 1) for line in proc.stdout.splitlines() if "=" in line)

def context(pid):
    # Only explicitly allowlisted nonsecret settings and presence booleans leave
    # this function. Credential values are neither returned, copied nor logged.
    raw = (pathlib.Path("/proc") / pid / "environ").read_bytes()
    env = dict(item.decode().split("=", 1) for item in raw.split(bytes([0])) if b"=" in item)
    del raw
    settings = [
        "CODEX_PROVIDER_ENABLED", "CODEX_ACCOUNT_HOMES", "PATH", "BOT_LLM_BACKEND",
        "METAB_KEYS_ENABLED", "MASTERMIND_WEEKLY_CEILING_PCT", "MASTERMIND_SHARED_LLM_POOL",
        "METABOLISM_STATE_ROOT", "CODEX_HOME", "MASTERMIND_RESP_CACHE_TTL",
        "MASTERMIND_VPS_AUTHORITATIVE", "MASTERMIND_SERVE_ONLY", "MASTERMIND_JOBSTORE",
        "MASTERMIND_MACRO_MANAGED_EXTERNALLY",
    ]
    presence_names = [
        "DEEPSEEK_API_KEY", "CODEX_ACCESS_TOKEN", "CODEX_API_KEY",
        "CLAUDE_CODE_OAUTH_TOKEN",
    ] + ["CLAUDE_CODE_OAUTH_TOKEN_" + str(n) for n in range(1, 8)]
    effective = {k: env[k] for k in settings if k in env}
    presence = {k: bool(env.get(k)) for k in presence_names}
    assert all(bool(env.get(k, "")) == bool(env.get(k, "").strip())
               for k in presence_names), "presence/stripped-presence mismatch"
    seen = set(env)
    env_files = []
    for name in (".env", ".env.local"):
        path = code / name
        env_files.append({"path": str(path), "exists": path.is_file()})
        if not path.is_file():
            continue
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            if key in seen:
                continue
            seen.add(key)
            if key in settings:
                effective[key] = value.strip().strip('"').strip("'")
            if key in presence_names:
                presence[key] = bool(value.strip().strip('"').strip("'"))
    service_home = env.get("HOME", "/root")
    codex_home = effective.get("CODEX_HOME", service_home + "/.codex")
    result = {
        "nonsecret_settings": effective, "oauth_presence_only": presence,
        "local_env_files": env_files, "service_home_is_root": service_home == "/root",
        "codex_executable": shutil.which("codex", path=effective.get("PATH", "")),
        "codex_auth_file_present": (pathlib.Path(codex_home) / "auth.json").is_file(),
    }
    del env
    return result

def authorities(root):
    out = {}
    for book in ("autonomous", "china", "hk"):
        directory = root / "portfolios" / book
        for name in ("nav_history.jsonl", "account.json", "fills.jsonl"):
            path = directory / name
            assert path.is_file() and path.read_bytes().strip(), "missing authority " + str(path)
            out[str(path.relative_to(root))] = identity(path)
        for name in ("pending_target.json", "paper_transaction.json", "paper_transaction.wal.json"):
            assert not (directory / name).exists(), "pending/WAL state present"
        receipts = directory / "settlement_receipts"
        assert not receipts.exists() or (receipts.is_dir() and not any(receipts.iterdir()))
    path = root / "portfolio_forward_evaluation/start.json"
    out[str(path.relative_to(root))] = identity(path)
    assert out[str(path.relative_to(root))]["sha256"] == cohort_sha
    return out

def release_files(root, phase):
    actual = {relative: identity(root / relative)["sha256"]
              for relative in source_manifest[phase]["files"]}
    assert actual == source_manifest[phase]["files"], phase + " source identity mismatch"
    return actual

exclude = []
sync_index = 0

def sync(src, dst, dry=False):
    global sync_index
    sync_index += 1
    proc = subprocess.run(
        ["rsync", "-acn" if dry else "-ac", "--delete", "--itemize-changes",
         *exclude, str(src) + "/", str(dst) + "/"],
        capture_output=True, text=True, timeout=90,
    )
    receipt = stage / ("rsync-" + str(sync_index) + ".txt")
    receipt.write_text(proc.stdout)
    changes = proc.stdout.splitlines()
    out = {
        "exit_code": proc.returncode, "change_count": len(changes),
        "transcript": receipt.name, "transcript_sha256": identity(receipt)["sha256"],
        "stderr": proc.stderr,
    }
    if dry:
        out["changes"] = changes
    return out

def verified_empty(receipt):
    return receipt["exit_code"] == 0 and receipt["change_count"] == 0

def load_optional(path):
    return json.loads(path.read_text()) if path.is_file() else None

report = {
    "schema": "grey_deer.paired_isolated_health_route.v1",
    "candidate": candidate, "baseline": baseline,
    "started_at": now(), "stage": str(stage),
    "archive": {"sha256": args.archive_sha256, "bytes": archive.stat().st_size},
    "production_service_mutated": False, "production_health_polled": False,
    "scope": "One complete actual ASGI GET /health per exact fresh release process, with registered startup paused and frozen health inputs; full eligible-code restoration between processes.",
    "limitations": [
        "Presence fixtures preserve branching but do not authenticate providers.",
        "Paused scheduler.running may satisfy the literal route while dispatch remains forbidden.",
        "ASGI includes routing/middleware/body but excludes TCP/uvicorn and production contention.",
        "Audit/read-only fences and cold-process effects differ from unconstrained production timing.",
        "An isolated pass cannot erase the separately recorded live six-second failure.",
    ],
}
before = None
live_before = None
backup_verified = False
children_settled = True
snapshot_mounts = []
snapshot_manifest = {}
dependency_sources = {}
macro_files = [
    "data/metabolism/key_ledger.jsonl",
    "data/metabolism/key_usage.jsonl",
    "data/metabolism/key_budget_status.json",
    "data/mastermind/key_events.jsonl",
    "data/mastermind/key_pool_status.json",
    "config/capability_manifest.yml",
    "config/metabolism_budget.yml",
    "config.yml",
]
macro_source_files = [
    "engine/llm_auth.py", "engine/neuralweb/key_pool.py",
    "engine/neuralweb/capability_broker.py", "engine/metabolism/budget_gate.py",
    "engine/codex_provider.py", "engine/codex_lane/runner.py", "lib/config.py",
]

def freeze(src, dest, target):
    rec = {"source": str(src), "target_in_namespace": str(target), "present": src.is_file()}
    assert rec["present"], "required frozen health input absent: " + str(src)
    if src.is_file():
        assert not src.is_symlink(), "unexpected input symlink"
        dest.parent.mkdir(parents=True, exist_ok=True)
        data = src.read_bytes()
        dest.write_bytes(data)
        rec.update({"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
        assert identity(src) == identity(dest), "input changed during snapshot"
        snapshot_mounts.append((dest, target))
    snapshot_manifest[str(src)] = rec

def snapshot_sources_unchanged():
    return all(
        (pathlib.Path(path).is_file() == rec["present"])
        and (not rec["present"] or identity(pathlib.Path(path)) == {
            "bytes": rec["bytes"], "sha256": rec["sha256"]
        })
        for path, rec in snapshot_manifest.items()
    )

def frozen_unchanged():
    return all(
        identity(src) == {
            "bytes": snapshot_manifest[str(
                canonical / "metabolism/key_ledger.jsonl"
                if target == receiver / "data/metabolism/key_ledger.jsonl" else target
            )]["bytes"],
            "sha256": snapshot_manifest[str(
                canonical / "metabolism/key_ledger.jsonl"
                if target == receiver / "data/metabolism/key_ledger.jsonl" else target
            )]["sha256"],
        }
        for src, target in snapshot_mounts
    )

def run_probe(phase, env):
    global children_settled
    protected = sorted({
        str(p.resolve()) for p in (code, canonical, code / "vendor", macro) if p.exists()
    })
    shell = ["set -e", "mount --make-rprivate /"]
    for root in protected:
        shell += [
            "mount --bind " + shlex.quote(root) + " " + shlex.quote(root),
            "mount -o remount,bind,ro " + shlex.quote(root),
        ]
    for src, target in snapshot_mounts:
        assert target.is_file()
        shell += [
            "mount --bind " + shlex.quote(str(src)) + " " + shlex.quote(str(target)),
            "mount -o remount,bind,ro " + shlex.quote(str(target)),
        ]
    shell.append(
        "exec /opt/mastermind/.venv/bin/python "
        + shlex.quote(str(stage / "isolated_health_route.py")) + " "
        + shlex.quote(str(stage)) + " " + phase
    )
    command = [
        "unshare", "--mount", "--net", "--pid", "--fork", "--kill-child=KILL",
        "--mount-proc", "/bin/bash", "-c", "\n".join(shell),
    ]
    started_ns = time.monotonic_ns()
    deadline_kind = None
    start_marker = stage / (phase + "-request-start.json")
    complete_marker = stage / (phase + "-response-complete.json")
    with (stage / (phase + ".stdout.txt")).open("w") as stdout, (
        stage / (phase + ".stderr.txt")
    ).open("w") as stderr:
        proc = subprocess.Popen(
            command, env=env, stdout=stdout, stderr=stderr, text=True, start_new_session=True,
        )
        children_settled = False
        observed_start = None
        observed_complete = None
        try:
            while proc.poll() is None:
                observed_start = load_optional(start_marker)
                observed_complete = load_optional(complete_marker)
                if observed_complete is not None:
                    # Response timing is already fixed. Allow only bounded shutdown.
                    try:
                        proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        deadline_kind = "post_response_cleanup_5s"
                    break
                now_ns = time.monotonic_ns()
                if observed_start is not None:
                    if now_ns >= observed_start["monotonic_ns"] + 6_000_000_000:
                        deadline_kind = "request_6s"
                        break
                elif now_ns >= started_ns + 45_000_000_000:
                    deadline_kind = "startup_45s"
                    break
                time.sleep(0.025)
        finally:
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
                    pass
            proc.wait(timeout=5)
            deadline = time.monotonic() + 5
            while group_exists() and time.monotonic() < deadline:
                time.sleep(0.05)
            children_settled = not group_exists()
        observed_start = load_optional(start_marker)
        observed_complete = load_optional(complete_marker)
        outcome = {
            "phase": phase, "exit_code": proc.returncode,
            "launcher_reaped": proc.poll() is not None,
            "process_group_gone": children_settled, "deadline_kind": deadline_kind,
            "request_start": observed_start, "response": observed_complete,
            "startup": load_optional(stage / (phase + "-startup.json")),
            "child_result": load_optional(stage / (phase + "-probe.json")),
            "stdout": identity(stage / (phase + ".stdout.txt")),
            "stderr": identity(stage / (phase + ".stderr.txt")),
        }
        outcome["helper_contract_passed"] = bool(
            observed_complete and observed_complete.get("helper_contract_passed")
            and observed_complete["complete_monotonic_ns"]
            <= observed_complete["start_monotonic_ns"] + 6_000_000_000
            and outcome["child_result"] and outcome["child_result"].get("safety_qualified")
            and children_settled and deadline_kind is None
        )
    report.setdefault("phases", {})[phase] = outcome
    assert children_settled, "child exit unverified; receiver retained"
    return outcome

try:
    live_before = service_state()
    assert live_before["ActiveState"] == "active"
    assert live_before["MainPID"] == inputs["context"]["pid"], "service process changed"
    assert (code / ".deployed_git_sha").read_text().strip() == baseline
    service_root = pathlib.Path("/proc") / live_before["MainPID"] / "root/opt/mastermind"
    assert (service_root / ".deployed_git_sha").read_text().strip() == baseline
    live_context = context(live_before["MainPID"])
    expected_context = {k: v for k, v in inputs["context"].items() if k not in {"at", "pid"}}
    assert live_context == expected_context, "health context changed"
    assert live_context["service_home_is_root"] and not live_context["codex_auth_file_present"]
    assert not live_context["nonsecret_settings"].get("METABOLISM_STATE_ROOT")
    assert not (macro / ".env").exists() and not (macro / ".env.local").exists()
    before = authorities(canonical)
    assert authorities(service_root / "data") == before
    report["production_before"] = {"service": live_before, "marker": baseline}
    report["context"] = live_context
    report["authority_snapshot_before"] = before
    report["installed_baseline_source"] = release_files(code, "baseline")
    dependency_sources = {p: identity(macro / p) for p in macro_source_files}
    report["macro_dependency_sources"] = dependency_sources
    for path in (source, receiver, backup, frozen):
        path.mkdir()
    with tarfile.open(archive) as handle:
        members = handle.getmembers()
        assert all(not pathlib.PurePosixPath(m.name).is_absolute()
                   and ".." not in pathlib.PurePosixPath(m.name).parts for m in members)
        report["archive"]["members"] = len(members)
        handle.extractall(source, filter="data")
    helper_text = (source / "scripts/deploy_code_to_vps.sh").read_text()
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
            assert verified_empty(report[name])
    backup_verified = True
    data = receiver / "data"
    data.mkdir()
    for relative in before:
        dest = data / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(canonical / relative, dest)
    local_ledger = canonical / "metabolism/key_ledger.jsonl"
    local_target = data / "metabolism/key_ledger.jsonl"
    local_target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(local_ledger, local_target)
    freeze(local_ledger, frozen / "mastermind/key_ledger.jsonl", local_target)
    for relative in macro_files:
        freeze(macro / relative, frozen / "macro" / relative, macro / relative)
    report["health_input_manifest"] = snapshot_manifest
    assert snapshot_sources_unchanged() and frozen_unchanged()
    assert authorities(canonical) == before and authorities(data) == before
    report["candidate_copy"] = sync(source, receiver)
    assert report["candidate_copy"]["exit_code"] == 0
    report["candidate_verification"] = sync(source, receiver, True)
    assert verified_empty(report["candidate_verification"])
    (receiver / "vendor").symlink_to(code / "vendor", target_is_directory=True)
    (receiver / ".deployed_git_sha").write_text(candidate + "\n")
    report["candidate_source"] = release_files(receiver, "candidate")
    (stage / "tmp").mkdir()
    env = dict(live_context["nonsecret_settings"])
    env.update({
        "PYTHONDONTWRITEBYTECODE": "1", "TMPDIR": str(stage / "tmp"),
        "MASTERMIND_AUTH_TOKEN": "isolated-health-operator-presence-fixture",
    })
    for name, present in live_context["oauth_presence_only"].items():
        if present:
            env[name] = "isolated-nonsecret-presence-fixture"
    report["credential_fixture_policy"] = {
        "names": sorted(name for name, present in live_context["oauth_presence_only"].items() if present),
        "value": "isolated-nonsecret-presence-fixture",
        "auth_file_created": False, "credential_values_copied": False,
        "credential_file_open_denied": True, "presence_semantics_verified": True,
    }
    run_probe("candidate", env)
    assert authorities(data) == before and frozen_unchanged()
    # No imported candidate modules survive across this restore.
    report["restoration"] = sync(backup, receiver)
    report["restoration_verification"] = sync(backup, receiver, True)
    assert verified_empty(report["restoration_verification"])
    assert report["restoration"]["exit_code"] == 0
    (receiver / ".deployed_git_sha").write_text(baseline + "\n")
    report["restored_baseline_source"] = release_files(receiver, "baseline")
    run_probe("baseline", env)
    assert authorities(data) == before and frozen_unchanged()
    report["baseline_post_probe_verification"] = sync(backup, receiver, True)
    assert verified_empty(report["baseline_post_probe_verification"])
except BaseException as exc:
    report["failure"] = {
        "type": type(exc).__name__, "error": str(exc), "traceback": traceback.format_exc(),
    }
finally:
    if backup_verified and children_settled:
        try:
            report["final_restoration"] = sync(backup, receiver)
            report["final_restoration_verification"] = sync(backup, receiver, True)
            (receiver / ".deployed_git_sha").write_text(baseline + "\n")
        except BaseException as exc:
            report["restoration_failure"] = {"type": type(exc).__name__, "error": str(exc)}
    elif backup_verified:
        report["restoration_skipped"] = "child exit unverified; retain receiver"
    try:
        after_service = service_state()
        report["production_after"] = {
            "service": after_service, "marker": (code / ".deployed_git_sha").read_text().strip(),
        }
        report["production_identity_unchanged"] = (
            after_service == live_before and report["production_after"]["marker"] == baseline
        )
        report["health_context_unchanged"] = (
            context(after_service["MainPID"]) == report.get("context")
        )
        report["canonical_authority_after"] = authorities(canonical)
        report["all_canonical_authority_unchanged"] = report["canonical_authority_after"] == before
        report["all_snapshot_authority_unchanged"] = (
            before is not None and (receiver / "data").exists()
            and authorities(receiver / "data") == before
        )
        report["health_input_sources_unchanged"] = snapshot_sources_unchanged()
        report["health_input_snapshots_unchanged"] = frozen_unchanged()
        report["macro_dependency_sources_unchanged"] = (
            {p: identity(macro / p) for p in macro_source_files} == dependency_sources
        )
    except BaseException as exc:
        report["after_observation_failure"] = {"type": type(exc).__name__, "error": str(exc)}
    phases = report.get("phases", {})
    report["execution_completed"] = bool(
        "failure" not in report and "restoration_failure" not in report
        and children_settled and set(phases) == {"candidate", "baseline"}
        and all(p["process_group_gone"] for p in phases.values())
        and report.get("production_identity_unchanged")
        and report.get("health_context_unchanged")
        and report.get("all_canonical_authority_unchanged")
        and report.get("all_snapshot_authority_unchanged")
        and report.get("health_input_sources_unchanged")
        and report.get("health_input_snapshots_unchanged")
        and report.get("macro_dependency_sources_unchanged")
        and verified_empty(report.get("final_restoration_verification", {
            "exit_code": -1, "change_count": -1,
        }))
    )
    report["paired_helper_contract_passed"] = bool(
        report["execution_completed"] and all(p["helper_contract_passed"] for p in phases.values())
    )
    report["completed_at"] = now()
    (stage / "HEALTH_ROUTE_RESULT.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps({
    key: report.get(key) for key in (
        "candidate", "baseline", "execution_completed", "paired_helper_contract_passed",
        "failure", "production_identity_unchanged", "all_canonical_authority_unchanged",
        "health_input_sources_unchanged", "health_input_snapshots_unchanged", "completed_at",
    )
}))
sys.exit(0 if report["execution_completed"] else 1)
