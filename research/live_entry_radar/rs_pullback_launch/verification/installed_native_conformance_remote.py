#!/usr/bin/env python3
"""Root-reviewed, read-only installed Native-reference proof.

Run on the approved host with /opt/macro-api/.venv/bin/python -B, feeding this
file on stdin if desired. The required checkout and process pins come from root's
delivery record. A separate root receipt must prove the exact positive release
ancestry when this installed checkout lacks the required history. The release pin is the
actual squashed release, not an assumption
that the pre-merge candidate is an ancestor after squashing.

This script does not install, restart, fetch, build, derive, retry acquisition,
or write an evidence file. Its sole output is one JSON document on stdout.
Health, installed-reader behavior, and in-memory synthetic controls are separate.
The historical cutoff queries do not claim this verifier read evidence then.
"""
from __future__ import annotations

import argparse
import dataclasses
import hashlib
import http.client
import importlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from datetime import date, datetime, timedelta, timezone


ROOT = Path("/opt/macro")
VENV = Path("/opt/macro-api/.venv")
NATIVE_CANDIDATE = "6d14f398564dce1d0f68daf956315cf7e9d19520"
MERGED_RELEASE_COMMIT = "7a1f9ad0a28973cdc9b261e80bfdf61f4eae9575"
MASTER_OWNER_COMMIT = "75a2bfce6dd95ee921d05d719cfc67976de17145"
SOURCE_READ_NS = 1791354276802797000
REFERENCE_DAY = date(2026, 10, 7)
PROSPECTIVE_SHA256 = "0e07e498d7a6983c8752a53d719281b07c30d334895c0b418edbbcc160145856"
MAX_FILE_BYTES = 64 * 1024 * 1024
SOURCES = {
    "lib/__init__.py": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "lib/dataos/__init__.py": "0d8df3c0c127df3ec7a5b7148dd32dfed66dbd4c22e5fa496b77ec15377213a7",
    "lib/dataos/identity.py": "8baefdf03e29afb59b4bc70805327e88e0e4e96e0a720727ffa695ba1775ad6f",
    "scripts/build_security_master.py": "bfe25480ec3e3dca98dcc5a4f0efad5fdad0f19870095066285e795598b022d6",
    "engine/theme_graph/identity_resolution.py": "ad1ad1622295816c30c094b375396f6afd6891e830ed2b0d7177b23981464b86",
    "engine/theme_graph/store.py": "7e9488741f4fe58343fd7f9255a4d694a3bda1cb081a35239ecda277d8ee8221",
}
ARTIFACTS = {
    "data/reference/_receipt.json": "792484bcdfab9f5908eb1bd1c54e1f051405a8d59b1ce9f1ca966b93474b3ecc",
    "data/reference/security_master.parquet": "289f0c9c7ef0e550c12c36bb6dab558d741b326fcb36c9bfa8214f8f7dd09133",
    "data/reference/vendor_aliases.parquet": "a4d3a12b1700a012c0f6215dfd8470a408c674028d688c9ba864eeb206e7c635",
    "data/reference/issuer_master.parquet": "c8823f9a3a830e1714112086ee17a6509cf2960f52b4906cb2bafe0fb26c8c5f",
    "data/reference/issuer_migrations.parquet": "a06787b85cddd891a7e850044abbbb6b0aafa65b20359b126a38d263b3bdb118",
    "data/reference/security_migrations.parquet": "cb99695357d34b03cfcdda3468fbd4233067b833a2e3662090a8d365f0c0ab11",
    "data/theme_graph/identity_resolution.parquet": "ac46f77718d103847d59266e55be15e7cc7b129ce38dc9166d01aea3ce3d3085",
}
GIT_PREFIX = ("git", "--no-optional-locks", "-c", "core.fsmonitor=false",
              "-c", "protocol.allow=never", "-C", str(ROOT))
SERVICE_COMMAND = (
    "systemctl", "show", "macro-api",
    "--property=ActiveState,SubState,MainPID,ExecMainStartTimestamp,NeedDaemonReload,FragmentPath,DropInPaths,WorkingDirectory",
)


class ProofFailure(RuntimeError):
    pass


def require(condition, code):
    if not condition:
        raise ProofFailure(code)


def iso_ns(value):
    seconds, nanos = divmod(value, 1_000_000_000)
    return datetime.fromtimestamp(seconds, timezone.utc).strftime("%Y-%m-%dT%H:%M:%S") + f".{nanos:09d}Z"


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode()


def command(argv, accepted_codes=(0,)):
    result = subprocess.run(
        list(argv), cwd=ROOT, capture_output=True, text=True, timeout=20,
        env={"PATH": os.defpath, "GIT_OPTIONAL_LOCKS": "0", "GIT_TERMINAL_PROMPT": "0",
             "GIT_NO_LAZY_FETCH": "1", "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": "/dev/null"},
    )
    # Do not copy arbitrary child stderr or any environment into the evidence.
    require(result.returncode in accepted_codes, "READ_ONLY_COMMAND_FAILED")
    require(len(result.stdout.encode()) <= 16384, "READ_ONLY_COMMAND_OUTPUT_BOUND")
    return result.stdout.strip()


def service_state():
    value = dict(line.split("=", 1) for line in command(SERVICE_COMMAND).splitlines() if "=" in line)
    require(value.get("ActiveState") == "active" and value.get("SubState") == "running", "API_NOT_ACTIVE")
    require(value.get("MainPID", "").isdigit() and int(value["MainPID"]) > 0, "API_PID_UNAVAILABLE")
    require(value.get("WorkingDirectory") == str(ROOT), "API_WRONG_WORKING_DIRECTORY")
    require(value.get("NeedDaemonReload") == "no", "API_MANAGER_RELOAD_REQUIRED")
    require(value.get("FragmentPath") == "/etc/systemd/system/macro-api.service", "API_UNEXPECTED_UNIT")
    require(value.get("DropInPaths") == "", "API_UNREVIEWED_DROPINS")
    return value


def health(expected_head, expected_process_commit):
    started = time.time_ns()
    connection = http.client.HTTPConnection("127.0.0.1", 8000, timeout=5)
    try:
        # Exact local read route; http.client does not follow redirects or proxies.
        connection.request("GET", "/api/health", headers={"Accept": "application/json"})
        response = connection.getresponse()
        body = response.read(8193)
        completed = time.time_ns()
        require(response.status == 200 and len(body) <= 8192, "API_HEALTH_RESPONSE_REFUSED")
        parsed = json.loads(body)
        require(isinstance(parsed, dict) and parsed.get("status") == "ok", "API_HEALTH_NOT_OK")
        for field, expected in (("commit", expected_process_commit), ("checkout", expected_head)):
            observed = parsed.get(field)
            require(isinstance(observed, str) and re.fullmatch(r"[0-9a-f]{7,40}", observed), "API_HEALTH_COMMIT_UNAVAILABLE")
            require(expected.startswith(observed), "API_PROCESS_OR_CHECKOUT_VERSION_MISMATCH")
        return {
            "scope": "local API liveness and process-imported/checkout commit; not Native API semantics",
            "route": "http://127.0.0.1:8000/api/health", "status": response.status,
            "commit": parsed["commit"], "checkout": parsed["checkout"],
            "expected_process_commit": expected_process_commit,
            "expected_checkout_commit": expected_head,
            "request_started_at_utc_ns": str(started), "response_completed_at_utc_ns": str(completed),
            "response_bytes": len(body), "response_sha256": hashlib.sha256(body).hexdigest(),
        }
    finally:
        connection.close()


def arm_guards(allowed_commands, blocked):
    """Defense in depth for the reviewed Python path, not an OS sandbox claim."""
    write_events = {
        "os.remove", "os.rename", "os.mkdir", "os.rmdir", "os.link", "os.symlink",
        "os.chmod", "os.chown", "os.truncate", "os.utime", "shutil.copyfile",
        "os.system", "os.exec", "os.posix_spawn", "os.fork", "os.forkpty",
    }

    def refuse(kind):
        blocked.append(kind)
        raise ProofFailure("FORBIDDEN_EFFECT_" + kind)

    def audit(event, args):
        if event == "open":
            path, mode, flags = args
            if isinstance(mode, str) and any(c in mode for c in "wax+"):
                refuse("WRITE_OPEN")
            if isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND):
                refuse("WRITE_OPEN")
            if isinstance(path, (str, bytes, os.PathLike)):
                name = os.fsdecode(path)
                parts = Path(name).parts
                if ".ssh" in parts or ".aws" in parts or ".codex" in parts or Path(name).name.startswith(".env") or name.endswith(".env"):
                    refuse("CREDENTIAL_READ")
        elif event in write_events:
            refuse("FILESYSTEM_OR_PROCESS_MUTATION")
        elif event.startswith("socket."):
            refuse("NETWORK")
        elif event == "subprocess.Popen":
            argv = args[1]
            if not isinstance(argv, (list, tuple)) or tuple(argv) not in allowed_commands:
                refuse("CHILD_PROCESS")

    sys.addaudithook(audit)


def run(args, record):
    require(Path(sys.prefix).resolve() == VENV.resolve(), "WRONG_PYTHON_ENVIRONMENT")
    require(bool(sys.flags.dont_write_bytecode), "PYTHON_B_FLAG_REQUIRED")
    require(ROOT.is_dir() and ROOT.resolve() == ROOT, "WRONG_INSTALL_ROOT")
    os.chdir(ROOT)
    sys.path.insert(0, str(ROOT))
    head_command = GIT_PREFIX + ("rev-parse", "--verify", "HEAD")
    release_command = GIT_PREFIX + ("rev-parse", "--verify", MERGED_RELEASE_COMMIT + "^{commit}")
    ancestry_command = GIT_PREFIX + ("merge-base", "--is-ancestor", MERGED_RELEASE_COMMIT, args.expected_head)
    require(command(head_command) == args.expected_head, "INSTALLED_HEAD_MISMATCH")
    require(command(release_command) == MERGED_RELEASE_COMMIT, "MERGED_RELEASE_UNAVAILABLE")
    shallow = command(GIT_PREFIX + ("rev-parse", "--is-shallow-repository"))
    require(shallow in ("true", "false"), "SHALLOW_STATE_UNAVAILABLE")
    if shallow == "false":
        command(ancestry_command)
    record["installation"] = {
        "root": str(ROOT), "expected_head": args.expected_head, "actual_head": args.expected_head,
        "merged_release_commit": MERGED_RELEASE_COMMIT,
        "expected_process_commit": args.expected_process_commit,
        "shallow_repository": shallow == "true",
        "release_is_ancestor_locally": None if shallow == "true" else True,
        "external_release_lineage_required": shallow == "true",
        "accepted_candidate_reference": NATIVE_CANDIDATE,
        "ancestry_note": "Candidate source is bound by exact hashes. A shallow checkout cannot prove missing ancestry; root must pair this proof with an exact positive release-ancestry receipt from a repository containing the required history before accepting delivery.",
    }
    before_service = service_state()
    record["api_health"] = health(args.expected_head, args.expected_process_commit)
    record["api_service_before"] = before_service

    blocked = []
    arm_guards({head_command, SERVICE_COMMAND}, blocked)
    record["guard"] = {"kind": "Python audit defense in depth", "blocked_attempts": blocked,
                       "provider_transport_after_health": "blocked", "filesystem_mutations": "blocked"}
    retained = {}
    record["installed_reads"] = {}
    for path, expected in {**SOURCES, **ARTIFACTS}.items():
        target = ROOT / path
        require(target.resolve().is_relative_to(ROOT), "PROTECTED_PATH_ESCAPES_INSTALL")
        require(target.stat().st_size <= MAX_FILE_BYTES, "PROTECTED_FILE_SIZE_LIMIT")
        start = time.time_ns()
        with target.open("rb") as stream:
            data = stream.read(MAX_FILE_BYTES + 1)
        end = time.time_ns()
        require(len(data) <= MAX_FILE_BYTES, "PROTECTED_FILE_SIZE_LIMIT")
        observed = hashlib.sha256(data).hexdigest()
        require(observed == expected, "INSTALLED_BYTES_MISMATCH:" + path)
        retained[path] = data
        record["installed_reads"][path] = {
            "source_ref": str(target), "byte_length": len(data), "sha256": observed,
            "read_started_at_utc_ns": str(start), "read_completed_at_utc_ns": str(end),
        }

    # lib.config eagerly reads .env. Do not import the graph loader, builders or
    # the API application here. The actual pure alias owner needs no credentials.
    owner = importlib.import_module("lib.dataos.identity")
    require(Path(owner.__file__).resolve() == ROOT / "lib/dataos/identity.py", "IDENTITY_IMPORT_FROM_WRONG_SOURCE")
    import pyarrow as pa
    import pyarrow.parquet as pq

    def rows(path):
        return pq.read_table(pa.BufferReader(retained[path])).to_pylist()

    aliases = rows("data/reference/vendor_aliases.parquet")
    table = owner.VendorAliasTable.from_records(aliases)
    native = [row for row in table.rows if row.vendor == "polygon"]
    require(len(aliases) == 6042 and len(native) == 1 and native[0].vendor_symbol == "MU", "NATIVE_ALIAS_POPULATION_CHANGED")
    mu = native[0]
    require(mu.security_id == "SEC:US-XNAS-MU" and mu.valid_from == REFERENCE_DAY and mu.valid_to is None, "MU_BINDING_CHANGED")
    require(mu.known_at.isoformat() == "2026-10-07T06:24:36.802797+00:00", "MU_SOURCE_CLOCK_CHANGED")
    receipt = json.loads(retained["data/reference/_receipt.json"])
    prospective = receipt["prospective_reference"]
    require(prospective["source_read_completed_at_utc_ns"] == SOURCE_READ_NS, "ORIGINAL_SOURCE_CLOCK_CHANGED")
    require(hashlib.sha256(canonical(prospective)).hexdigest() == PROSPECTIVE_SHA256, "ORIGINAL_PROSPECTIVE_BLOCK_CHANGED")
    require(receipt["generated_at"] == "2026-10-07T10:11:04" and receipt["code_version"] == MASTER_OWNER_COMMIT, "MASTER_PROVENANCE_CHANGED")
    record["retained_reference"] = {
        "original_source_read_completed_at_utc_ns": str(SOURCE_READ_NS),
        "prospective_reference_sha256": PROSPECTIVE_SHA256,
        "master_generated_at": receipt["generated_at"], "master_code_version": receipt["code_version"],
        "native_binding_symbols": ["MU"], "original_refused_symbols": ["SPY", "QQQ", "SMH"],
    }

    # The new actual read is reported as an observation, not minted as a Radar
    # read receipt or backdated to the original source observation.
    decision_ns = time.time_ns()
    reads_completed = max(int(v["read_completed_at_utc_ns"]) for v in record["installed_reads"].values())
    require(decision_ns // 1000 * 1000 >= reads_completed, "DECISION_PRECEDES_ACTUAL_READ")
    decision = iso_ns(decision_ns)
    outcomes = {symbol: table.resolve("polygon", symbol, REFERENCE_DAY, decision_at=decision)
                for symbol in ("MU", "SPY", "QQQ", "SMH")}
    require(outcomes == {"MU": "SEC:US-XNAS-MU", "SPY": None, "QQQ": None, "SMH": None}, "ACTUAL_NATIVE_RESULTS_CHANGED")
    require(table.vendor_symbol_for("polygon", mu.security_id, REFERENCE_DAY, decision_at=decision) == "MU", "ACTUAL_REVERSE_LOOKUP_CHANGED")
    record["installed_owner_read"] = {
        "owner": "lib.dataos.identity.VendorAliasTable.from_records/resolve/vendor_symbol_for",
        "module_file": str(Path(owner.__file__).resolve()), "event_date": REFERENCE_DAY.isoformat(),
        "actual_decision_at_utc_ns": str(decision_ns), "decision_at": decision, "results": outcomes,
        "reverse_mu": "MU", "scope": "pure installed Native alias reader over actual retained installed bytes",
        "radar_candidate_admission": "NOT_TESTED",
    }

    cutoff_results = {}
    for label, ns in (("before", SOURCE_READ_NS - 1), ("at", SOURCE_READ_NS), ("after", SOURCE_READ_NS + 1000)):
        result = table.resolve("polygon", "MU", REFERENCE_DAY, decision_at=iso_ns(ns))
        require(result == (None if label == "before" else mu.security_id), "RETAINED_SOURCE_CUTOFF_FAILED:" + label)
        cutoff_results[label] = {"decision_at_utc_ns": str(ns), "decision_at": iso_ns(ns), "result": result}
    record["retained_evidence_cutoff_controls"] = {
        "classification": "historical cutoff queries against evidence read now; not historical verifier/Radar visibility",
        "results": cutoff_results,
    }

    def must_refuse(label, call):
        try:
            call()
        except owner.IdentityError:
            return {"control": label, "result": "IdentityError"}
        raise ProofFailure("EXPECTED_IDENTITY_ERROR:" + label)

    synthetic = []
    synthetic.append(must_refuse("native decision omitted", lambda: table.resolve("polygon", "MU", REFERENCE_DAY)))
    synthetic.append(must_refuse("naive native decision", lambda: table.resolve("polygon", "MU", REFERENCE_DAY, decision_at=datetime(2026, 10, 7))))
    synthetic.append(must_refuse("tampered alias seal", lambda: dataclasses.replace(mu, security_id="SEC:US-XNAS-TAMPERED")))
    synthetic.append(must_refuse("missing native known_at", lambda: dataclasses.replace(mu, known_at=None)))
    bounded_to = REFERENCE_DAY + timedelta(days=1)
    seal = owner.alias_binding_sha256(mu.vendor, mu.vendor_symbol, mu.security_id, mu.valid_from,
                                     bounded_to, mu.known_at, mu.evidence_sha256)
    bounded = owner.VendorAliasTable([dataclasses.replace(mu, valid_to=bounded_to, binding_sha256=seal)])
    future_decision = datetime(2026, 10, 9, tzinfo=timezone.utc)
    require(bounded.resolve("polygon", "MU", REFERENCE_DAY, decision_at=future_decision) == mu.security_id, "SYNTHETIC_VALID_FROM_FAILED")
    require(bounded.resolve("polygon", "MU", bounded_to, decision_at=future_decision) is None, "SYNTHETIC_VALID_TO_NOT_EXCLUSIVE")
    fractional = iso_ns(SOURCE_READ_NS + 1)
    seal = owner.alias_binding_sha256(mu.vendor, mu.vendor_symbol, mu.security_id, mu.valid_from,
                                     None, fractional, mu.evidence_sha256)
    fractional_table = owner.VendorAliasTable([dataclasses.replace(mu, known_at=fractional, binding_sha256=seal)])
    require(fractional_table.resolve("polygon", "MU", REFERENCE_DAY, decision_at=iso_ns(SOURCE_READ_NS + 999)) is None, "SYNTHETIC_NS_CEIL_FLOOR_FAILED")
    require(fractional_table.resolve("polygon", "MU", REFERENCE_DAY, decision_at=iso_ns(SOURCE_READ_NS + 1000)) == mu.security_id, "SYNTHETIC_NEXT_MICROSECOND_FAILED")
    # Recovery is pure reconstruction from the same original sealed row.
    recovered = owner.VendorAliasTable([mu])
    require(recovered.resolve("polygon", "MU", REFERENCE_DAY, decision_at=decision) == mu.security_id, "SEALED_ROW_RECOVERY_FAILED")
    record["synthetic_controls"] = {
        "classification": "in-memory copies/invalid arguments only; no acquired evidence, files or admission",
        "typed_refusals": synthetic, "half_open_valid_to": "PASS", "evidence_ceil_decision_floor": "PASS",
        "same_sealed_row_recovery": "PASS",
    }
    require(table.resolve("membership", "MU", REFERENCE_DAY) == mu.security_id, "LEGACY_MEMBERSHIP_CHANGED")

    master = rows("data/reference/security_master.parquet")
    require(len(master) == 2383, "MASTER_POPULATION_CHANGED")
    current = {r["inception_code"]: r for r in master if not r.get("security_state")}
    for symbol, mic in (("CBOE", "BATS"), ("MU", "XNAS"), ("ETHA", "XNAS"), ("IBIT", "XNAS")):
        row = current[symbol]
        require(row["security_id"] == f"SEC:US-{mic}-{symbol}" and row["issuer_id"] == f"ISS:US-{mic}-{symbol}" and row["mic"] == mic, "CANONICAL_MASTER_CHANGED:" + symbol)
    history = rows("data/theme_graph/identity_resolution.parquet")
    require(len(history) == 165493, "SIDECAR_HISTORY_POPULATION_CHANGED")
    keys = [(r["node_id"], r["computed_at"]) for r in history]
    require(len(set(keys)) == len(keys) and all(all(k) for k in keys), "SIDECAR_DUPLICATE_OR_NULL_KEY")
    latest = {}
    for row in sorted(history, key=lambda r: (r["node_id"], r["computed_at"])):
        latest[row["node_id"]] = row
    require(len(latest) == 2807, "SIDECAR_LATEST_POPULATION_CHANGED")
    require(all(r["computed_at"] == "2026-10-07T10:11:06Z" and r["master_generated_at"] == "2026-10-07T10:11:04" and r["master_code_version"] == MASTER_OWNER_COMMIT for r in latest.values()), "SIDECAR_PROVENANCE_CHANGED")
    cboe, etha, ibit = (latest["co:us:" + s] for s in ("CBOE", "ETHA", "IBIT"))
    require(cboe["resolution_state"] == "RESOLVED" and cboe["security_id"] == "SEC:US-BATS-CBOE" and cboe["issuer_id"] == "ISS:US-BATS-CBOE", "CBOE_SIDECAR_CHANGED")
    require(etha["resolution_state"] == "RESOLVED" and etha["security_id"] == "SEC:US-XNAS-ETHA", "ETHA_SIDECAR_CHANGED")
    require(ibit["resolution_state"] == "ENTITY_TYPE_CONFLICT" and ibit["security_id"] is None and ibit["issuer_id"] is None, "IBIT_GRAPH_CONFLICT_CHANGED")
    record["canonical_retained_artifacts"] = {
        "classification": "exact installed artifacts; graph loader/API semantic route not executed",
        "master_rows": len(master), "sidecar_history_rows": len(history), "latest_nodes": len(latest),
        "CBOE": "RESOLVED:SEC:US-BATS-CBOE", "ETHA": "RESOLVED:SEC:US-XNAS-ETHA",
        "IBIT_master": "SEC:US-XNAS-IBIT", "IBIT_graph": "ENTITY_TYPE_CONFLICT; null security/issuer",
        "computed_at": "2026-10-07T10:11:06Z", "master_generated_at": "2026-10-07T10:11:04",
        "master_code_version": MASTER_OWNER_COMMIT,
    }

    for path, expected in {**SOURCES, **ARTIFACTS}.items():
        with (ROOT / path).open("rb") as stream:
            final = stream.read(MAX_FILE_BYTES + 1)
        require(len(final) <= MAX_FILE_BYTES and hashlib.sha256(final).hexdigest() == expected, "INSTALLED_BYTES_CHANGED_DURING_PROOF:" + path)
    require(command(head_command) == args.expected_head, "CHECKOUT_MOVED_DURING_PROOF")
    after_service = service_state()
    require(after_service == before_service, "API_PROCESS_CHANGED_DURING_PROOF")
    require(not blocked, "FORBIDDEN_EFFECT_ATTEMPTED")
    record["api_service_after"] = after_service
    record["protected_bytes_unchanged_after"] = True
    record["status"] = "PASS_SCOPED_INSTALLED_PROOF"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-head", required=True, help="Exact root-approved installed checkout commit")
    parser.add_argument("--expected-process-commit", required=True, help="Exact root-approved API process build commit, separately bound from the checkout")
    args = parser.parse_args()
    if not re.fullmatch(r"[0-9a-f]{40}", args.expected_head):
        parser.error("expected-head must be an exact 40-character lowercase SHA-1 ID")
    if not re.fullmatch(r"[0-9a-f]{40}", args.expected_process_commit):
        parser.error("expected-process-commit must be an exact 40-character lowercase SHA-1 ID")
    record = {
        "schema": "mastermind.rs_pullback_launch.installed_native_conformance.v1",
        "proof_started_at_utc_ns": str(time.time_ns()), "status": "UNAVAILABLE",
        "authority": {"research_admitted": False, "trading_authority": False},
        "overall_panel": "NOT_ADMITTED", "hypotheses": {"H1": "NOT_TESTED", "H2": "NOT_TESTED", "H3": "NOT_TESTED"},
        "limits": [
            "No provider call, acquisition retry, deployment, restart or owner regeneration.",
            "No new Radar read receipt, candidate admission, market-basis proof or transition ingestion.",
            "API health/version is not an HTTP Native-reference semantic proof.",
            "A shallow installed checkout requires a separate exact positive release-ancestry receipt for root acceptance; local unknown ancestry is not recorded as true.",
            "Graph loader is not imported because lib.config eagerly reads .env; retained graph artifacts are checked directly.",
            "Python audit guards are defense in depth, not an operating-system sandbox attestation.",
        ],
    }
    exit_code = 0
    try:
        run(args, record)
    except Exception as exc:
        record["status"] = "FAIL_OR_UNAVAILABLE"
        record["failure"] = {"type": type(exc).__name__, "code": str(exc) if isinstance(exc, ProofFailure) else "UNEXPECTED_PROOF_ERROR"}
        exit_code = 1
    record["proof_completed_at_utc_ns"] = str(time.time_ns())
    print(json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
