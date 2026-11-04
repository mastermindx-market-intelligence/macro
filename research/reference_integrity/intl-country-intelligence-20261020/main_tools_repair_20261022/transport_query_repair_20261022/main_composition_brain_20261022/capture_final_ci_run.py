#!/usr/bin/env python3
"""UNEXECUTED owner-run draft: preserve one exact completed final-head CI attempt.

Usage: python3 capture_final_ci_run.py --run-id ACTUAL_RUN_ID
       --expected-head-sha ACTUAL_FULL_HEAD_SHA --attempt ACTUAL_ATTEMPT
       --output-dir /absolute/NEW/directory [--gh /absolute/path/to/gh]

Only bounded `gh api --method GET` calls are used. No polling, rerun, mutation,
downloaded-code execution, or writes outside the new private output directory.
All current run artifacts and every started job log are preserved, including
failures and historical same-name artifacts. Required semantic artifacts must
have exact upload receipts in this attempt's logs; names alone do not bind them.
Exit 0 means complete evidence preservation, NOT a passing CI/release decision.
The caller must wait for natural completion before this one-shot invocation.
"""

import argparse
import collections
import datetime as dt
import hashlib
import json
import os
from pathlib import PurePosixPath
import re
import select
import selectors
import shutil
import signal
import stat
import subprocess
import sys
import time
import unicodedata
import zipfile


REPO = "mastermindx-market-intelligence/macro"
REPO_ID = 1266869026
# Deliberately unset until the caller supplies real immutable identities.
RUN = ATTEMPT = HEAD = None
PREFIX = "repos/" + REPO
RUN_PATH = PLAN_NAME = AGGREGATE_NAME = None
CHANGED_NAME = "ci-changed-files"
REQUIRED = {}
# Reviewed v2 transport/schema law. This file is never imported or executed.
SEMANTIC_PROTOCOL_SOURCE = {
    "path": "scripts/ci_semantic_proof.py",
    "git_blob": "df7e5007413584d8593bfeb69dd9b479daa99147",
    "sha256": "c3a36f7fafa5e2158c5e105d147553f026b9fc7002fab315df00165643e70a60",
}
MAX_PACKS = 256
MAX_LOGICAL_JOBS = 4096
MAX_PROOFS = 65536
MAX_PAGES = 16
MAX_JOBS = 1200
MAX_ARTIFACTS = 512
MAX_JSON = 8 * 1024 * 1024
MAX_ZIP = 64 * 1024 * 1024
MAX_LOG = 64 * 1024 * 1024
MAX_MEMBER = 32 * 1024 * 1024
MAX_EXPANDED = 128 * 1024 * 1024
MAX_MEMBERS = 256
MAX_TOTAL = 1024 * 1024 * 1024
DEADLINE = 0.0
TOTAL = 0
ROOT_FD = None
GH = None
FILES = {}
REQUESTS = []
STDOUT_BYTES = 0
STDOUT_ATTEMPTED = False


class Refusal(Exception):
    def __init__(self, code):
        self.code = code


def require(condition, code):
    if not condition:
        raise Refusal(code)


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def remaining():
    value = DEADLINE - time.monotonic()
    require(value > 0, "capture_deadline_exceeded")
    return value


def timeout_handler(signum, frame):
    raise Refusal("capture_deadline_exceeded")


def strict_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "duplicate_json_key")
            result[key] = value
        return result

    def constant(value):
        raise Refusal("non_finite_json_number")

    require(len(raw) <= MAX_JSON, "json_size_limit")
    return json.loads(raw.decode("utf-8", "strict"), object_pairs_hook=pairs, parse_constant=constant)


def parts(name):
    require(isinstance(name, str) and 0 < len(name.encode("utf-8")) <= 1024
            and not name.startswith("/") and "\\" not in name and ":" not in name
            and not any(ord(c) < 32 or ord(c) == 127 for c in name), "unsafe_relative_name")
    result = name.split("/")
    require(len(result) <= 20 and all(p not in ("", ".", "..") for p in result), "unsafe_relative_component")
    return result


def create_root(path):
    require(os.path.isabs(path) and str(PurePosixPath(path)) == path and path != "/", "output_must_be_normalized_absolute_path")
    components = path.split("/")[1:]
    require(all(p not in ("", ".", "..") for p in components), "unsafe_output_path")
    fd = os.open("/", os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        for component in components[:-1]:
            child = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=fd)
            os.close(fd)
            fd = child
        # Atomic refusal if anything already exists, including a dangling symlink.
        os.mkdir(components[-1], mode=0o700, dir_fd=fd)
        return os.open(components[-1], os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=fd)
    finally:
        os.close(fd)


def parent_fd(name):
    components = parts(name)
    fd = os.dup(ROOT_FD)
    try:
        for component in components[:-1]:
            try:
                os.mkdir(component, mode=0o700, dir_fd=fd)
            except FileExistsError:
                pass
            child = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=fd)
            os.close(fd)
            fd = child
        result, fd = fd, -1
        return result, components[-1]
    finally:
        if fd >= 0:
            os.close(fd)


def new_file(name):
    fd, leaf = parent_fd(name)
    try:
        return os.open(leaf, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600, dir_fd=fd)
    finally:
        os.close(fd)


def write_all(fd, data):
    global TOTAL
    TOTAL += len(data)
    require(TOTAL <= MAX_TOTAL, "total_preservation_limit")
    view = memoryview(data)
    while view:
        amount = os.write(fd, view)
        require(amount > 0, "short_output_write")
        view = view[amount:]


def read_saved(name, cap):
    fd, leaf = parent_fd(name)
    try:
        file_fd = os.open(leaf, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=fd)
    finally:
        os.close(fd)
    with os.fdopen(file_fd, "rb") as handle:
        require(stat.S_ISREG(os.fstat(handle.fileno()).st_mode), "non_regular_saved_file")
        raw = handle.read(cap + 1)
        require(len(raw) <= cap, "saved_read_limit")
        return raw


def api(endpoint, destination, cap=MAX_JSON, decode=True):
    """One read-only request; preserve the raw final response body, no retries."""
    require(endpoint.startswith(PREFIX + "/actions/"), "unexpected_api_endpoint")
    argv = [GH, "api", "--hostname", "github.com", "--method", "GET", endpoint,
            "-H", "Accept: application/vnd.github+json", "-H", "X-GitHub-Api-Version: 2022-11-28"]
    end = time.monotonic() + min(90.0, remaining())
    out_fd = new_file(destination)
    record = {"endpoint": endpoint, "method": "GET", "destination": destination, "started_at": now()}
    REQUESTS.append(record)
    proc = None
    poller = selectors.DefaultSelector()
    digest, count, stderr = hashlib.sha256(), 0, bytearray()
    try:
        environment = dict(os.environ, GH_PROMPT_DISABLED="1", GH_NO_UPDATE_NOTIFIER="1",
                           GH_NO_EXTENSION_UPDATE_NOTIFIER="1", NO_COLOR="1", CLICOLOR="0")
        proc = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, close_fds=True, env=environment)
        for pipe, label in ((proc.stdout, "stdout"), (proc.stderr, "stderr")):
            os.set_blocking(pipe.fileno(), False)
            poller.register(pipe, selectors.EVENT_READ, label)
        while poller.get_map():
            left = min(end - time.monotonic(), remaining())
            require(left > 0, "gh_api_timeout")
            for key, _ in poller.select(min(0.25, left)):
                chunk = os.read(key.fileobj.fileno(), 65536)
                if not chunk:
                    poller.unregister(key.fileobj)
                    continue
                if key.data == "stderr":
                    stderr.extend(chunk)
                    require(len(stderr) <= 32768, "gh_stderr_limit")
                else:
                    require(count + len(chunk) <= cap, "response_size_limit")
                    write_all(out_fd, chunk)
                    digest.update(chunk)
                    count += len(chunk)
        code = proc.wait(timeout=max(0.01, min(end - time.monotonic(), remaining())))
        record["returncode"] = code
        require(code == 0, "gh_api_failed")
        record["complete"] = True
    finally:
        poller.close()
        if proc is not None:
            if proc.poll() is None:
                proc.kill()
                proc.wait(timeout=2)
            proc.stdout.close()
            proc.stderr.close()
        os.fsync(out_fd)
        os.close(out_fd)
        pin = {"path": destination, "bytes": count, "sha256": digest.hexdigest()}
        FILES[destination] = pin
        record.update({"body": pin, "stderr_bytes": len(stderr), "stderr_sha256": sha(stderr), "finished_at": now()})
    return strict_json(read_saved(destination, cap)) if decode else pin


def run_identity(run):
    require(isinstance(run, dict) and run.get("id") == RUN and run.get("head_sha") == HEAD
            and run.get("run_attempt") == ATTEMPT and run.get("status") == "completed"
            and isinstance(run.get("conclusion"), str) and run["conclusion"],
            "run_not_completed_exact_attempt_and_head")
    require(run.get("name") == "ci" and run.get("path") == ".github/workflows/ci.yml"
            and run.get("event") == "pull_request"
            and run.get("repository", {}).get("full_name") == REPO
            and run.get("repository", {}).get("id") == REPO_ID,
            "run_repository_or_workflow_mismatch")
    return {key: run.get(key) for key in ("id", "run_attempt", "head_sha", "status", "conclusion",
            "event", "name", "path", "workflow_id", "head_branch", "created_at",
            "run_started_at", "updated_at", "head_commit")}


def job_identity(job):
    # The documented attempt-specific jobs response need not repeat run_attempt.
    # The endpoint plus bracketed attempt identity binds it when that field is absent.
    require(job.get("run_id") == RUN and job.get("head_sha") == HEAD
            and ("run_attempt" not in job or job["run_attempt"] == ATTEMPT)
            and job.get("status") == "completed" and isinstance(job.get("conclusion"), str)
            and isinstance(job.get("name"), str) and 0 < len(job["name"]) <= 512
            and isinstance(job.get("steps"), list), "job_identity_or_completion_mismatch")


def job_signature(rows):
    keys = ("id", "run_id", "run_attempt", "head_sha", "name", "status", "conclusion",
            "started_at", "completed_at", "steps", "runner_id", "runner_name", "runner_group_id")
    return sorted([{key: row.get(key) for key in keys} for row in rows], key=lambda row: row["id"])


def census(endpoint, key, prefix, limit):
    rows, identities, expected = [], set(), None
    for page in range(1, MAX_PAGES + 1):
        doc = api(f"{endpoint}?per_page=100&page={page}", f"api/{prefix}-page-{page:03d}.json")
        require(isinstance(doc, dict) and type(doc.get("total_count")) is int
                and isinstance(doc.get(key), list), "invalid_paginated_response")
        if expected is None:
            expected = doc["total_count"]
            require(0 <= expected <= limit, "pagination_total_limit")
        require(doc["total_count"] == expected and len(doc[key]) <= 100, "pagination_changed_or_invalid")
        for row in doc[key]:
            require(isinstance(row, dict) and type(row.get("id")) is int and row["id"] > 0
                    and row["id"] not in identities, "duplicate_or_invalid_paginated_identity")
            identities.add(row["id"])
            rows.append(row)
        require(len(rows) <= limit and len(rows) <= expected, "pagination_overflow")
        if len(doc[key]) < 100:
            require(len(rows) == expected, "incomplete_pagination")
            return rows
    raise Refusal("pagination_page_limit")


def archive_members(archive, artifact_id):
    """Retain original ZIP and manually preserve bounded safe regular members."""
    raw = read_saved(archive, MAX_ZIP)
    import io
    rows, names, expanded = [], set(), 0
    with zipfile.ZipFile(io.BytesIO(raw)) as zipped:
        infos = zipped.infolist()
        require(0 < len(infos) <= MAX_MEMBERS, "zip_member_count_limit")
        for info in infos:
            require(info.orig_filename == info.filename and not (info.flag_bits & 1), "encrypted_or_ambiguous_zip_member")
            name = info.filename[:-1] if info.is_dir() else info.filename
            parts(name)
            folded = name.casefold()
            require(folded not in names, "duplicate_or_case_colliding_zip_member")
            names.add(folded)
            mode = (info.external_attr >> 16) & 0xFFFF
            kind = stat.S_IFMT(mode)
            require(kind in ((0, stat.S_IFDIR) if info.is_dir() else (0, stat.S_IFREG)), "zip_special_or_symlink_member")
            require(info.compress_type in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED), "unsupported_zip_compression")
            require(0 <= info.file_size <= MAX_MEMBER, "zip_member_size_limit")
            expanded += info.file_size
            require(expanded <= MAX_EXPANDED, "zip_expanded_size_limit")
            if info.is_dir():
                require(info.file_size == 0, "nonempty_zip_directory")
                rows.append({"name": info.filename, "directory": True})
                continue
            destination = f"members/{artifact_id}/{name}"
            fd = new_file(destination)
            digest, count = hashlib.sha256(), 0
            try:
                with zipped.open(info, "r") as stream:
                    while True:
                        remaining()
                        chunk = stream.read(65536)
                        if not chunk:
                            break
                        count += len(chunk)
                        require(count <= info.file_size and count <= MAX_MEMBER, "zip_member_expanded_overflow")
                        write_all(fd, chunk)
                        digest.update(chunk)
                require(count == info.file_size, "zip_member_size_mismatch")
                os.fsync(fd)
            finally:
                os.close(fd)
            pin = {"path": destination, "bytes": count, "sha256": digest.hexdigest()}
            FILES[destination] = pin
            rows.append({"name": info.filename, "directory": False, "crc32": f"{info.CRC:08x}", **pin})
    return rows


def digest(value, length=64):
    return isinstance(value, str) and re.fullmatch(r"[a-f0-9]{%d}" % length, value) is not None


def logical_id(value):
    require(isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,255}", value),
            "invalid_logical_job_id")
    return value


def proof_id(value):
    require(isinstance(value, str), "invalid_proof_id")
    normalized = " ".join(unicodedata.normalize("NFC", value).split())
    require(value == normalized and re.fullmatch(r"[^\x00-\x1f\x7f]{1,256}", normalized),
            "noncanonical_proof_id")
    return normalized


def artifact_document(row, member_name):
    require(row.get("preserved") is True and row.get("github_digest_verified") is True,
            "required_artifact_not_preserved")
    regular = [item for item in row["members"] if not item["directory"]]
    require(len(regular) == 1 and regular[0]["name"] == member_name,
            "required_artifact_member_set_changed")
    return strict_json(read_saved(regular[0]["path"], MAX_JSON))


def plan_contract(value):
    """Structural census and published digest only; no outcome classification."""
    expected_keys = {
        "schema", "workflow_run_id", "workflow", "event", "role", "tested_tree_sha",
        "subject_head_sha", "base_sha", "authority_changed", "changed_from", "scope_mode",
        "reason", "scope_summary", "legacy_job_count", "eligible_job_count", "eligible_jobs",
        "skipped_job_count", "skipped_jobs", "packs", "nonempty_pack_indices", "matrix",
        "has_work", "semantic_jobs", "plan_sha256", "changed_files_sha256", "changed_files_count",
    }
    require(isinstance(value, dict) and set(value) == expected_keys
            and value["schema"] == "ci.pack_plan.v2", "unsupported_actual_plan_schema")
    identity = {key: value[key] for key in ("workflow_run_id", "workflow", "event", "role",
                "tested_tree_sha", "subject_head_sha", "base_sha", "plan_sha256")}
    require(identity["workflow_run_id"] == str(RUN) and identity["workflow"] == "ci"
            and identity["event"] == "pull_request" and identity["role"] == "pr_head"
            and identity["subject_head_sha"] == HEAD
            and digest(identity["tested_tree_sha"], 40) and digest(identity["base_sha"], 40)
            and digest(identity["plan_sha256"]), "plan_run_head_or_identity_mismatch")
    require(value["changed_from"] == identity["base_sha"]
            and type(value["authority_changed"]) is bool and value["scope_mode"] in ("active", "shadow", "off")
            and isinstance(value["reason"], str) and bool(value["reason"])
            and isinstance(value["scope_summary"], str) and bool(value["scope_summary"]),
            "invalid_plan_scope_metadata")
    require(type(value["changed_files_count"]) is int and value["changed_files_count"] >= 0
            and (digest(value["changed_files_sha256"]) or value["changed_files_sha256"] == ""
                 and value["changed_files_count"] == 0), "invalid_plan_changed_file_digest")
    eligible, skipped, packs = value["eligible_jobs"], value["skipped_jobs"], value["packs"]
    for items, count_name in ((eligible, "eligible_job_count"), (skipped, "skipped_job_count")):
        require(isinstance(items, list) and len(items) <= MAX_LOGICAL_JOBS,
                "plan_logical_inventory_limit")
        for name in items:
            logical_id(name)
        require(len(items) == len(set(items)) and type(value[count_name]) is int
                and len(items) == value[count_name], "plan_logical_inventory_count_or_duplicates")
    require(not set(eligible) & set(skipped) and type(value["legacy_job_count"]) is int
            and value["legacy_job_count"] == len(eligible) + len(skipped), "plan_legacy_inventory_mismatch")
    require(isinstance(packs, list) and 1 <= len(packs) <= MAX_PACKS, "plan_pack_limit")
    pack_by_job, pack_jobs, weights = {}, [], []
    for index, item in enumerate(packs):
        require(isinstance(item, dict) and set(item) == {"index", "weight", "jobs"}
                and type(item["index"]) is int and item["index"] == index
                and type(item["weight"]) is int and item["weight"] >= 0
                and isinstance(item["jobs"], list), "invalid_plan_pack")
        for name in item["jobs"]:
            logical_id(name)
            require(name not in pack_by_job, "duplicate_plan_pack_job")
            pack_by_job[name] = index
        pack_jobs.append(item["jobs"]); weights.append(item["weight"])
    nonempty = [index for index, names in enumerate(pack_jobs) if names]
    require(set(pack_by_job) == set(eligible) and value["nonempty_pack_indices"] == nonempty
            and value["matrix"] == {"include": [{"pack": index} for index in nonempty]}
            and type(value["has_work"]) is bool and value["has_work"] == bool(nonempty),
            "plan_pack_partition_or_matrix_mismatch")
    semantic_jobs = value["semantic_jobs"]
    require(isinstance(semantic_jobs, list) and len(semantic_jobs) == len(eligible), "plan_semantic_job_count")
    jobs, proofs, observed_order = {}, {}, []
    for job in semantic_jobs:
        require(isinstance(job, dict) and set(job) == {"logical_job_id", "pack_index", "job_exec_sha256", "steps"},
                "invalid_plan_semantic_job")
        name = logical_id(job["logical_job_id"])
        require(name not in jobs and name in pack_by_job and type(job["pack_index"]) is int
                and job["pack_index"] == pack_by_job[name] and digest(job["job_exec_sha256"]),
                "plan_semantic_job_binding_mismatch")
        require(isinstance(job["steps"], list) and 1 <= len(job["steps"]) <= 4096, "plan_proof_count_limit")
        jobs[name] = {"pack_index": job["pack_index"], "job_exec_sha256": job["job_exec_sha256"]}
        observed_order.append(name)
        for step in job["steps"]:
            require(isinstance(step, dict) and set(step) == {"proof_id", "step_spec_sha256"}, "invalid_plan_proof")
            key = (name, proof_id(step["proof_id"]))
            require(key not in proofs and digest(step["step_spec_sha256"]), "duplicate_or_unbound_plan_proof")
            proofs[key] = {**jobs[name], "step_spec_sha256": step["step_spec_sha256"]}
            require(len(proofs) <= MAX_PROOFS, "plan_total_proof_limit")
    require(observed_order == eligible, "plan_semantic_job_order_mismatch")
    # Exact v2 digest payload from the pinned canonical protocol. No reconciler
    # or downloaded module is imported; this binds data, not failure causality.
    payload = {key: value[key] for key in ("schema", "workflow_run_id", "workflow", "event", "role",
               "tested_tree_sha", "subject_head_sha", "base_sha", "authority_changed", "changed_from",
               "scope_mode", "changed_files_sha256")}
    payload.update(pack_count=len(packs), eligible_job_ids=eligible, pack_jobs=pack_jobs,
                   pack_weights=weights, semantic_jobs=semantic_jobs)
    require(sha(encoded(payload)) == identity["plan_sha256"], "actual_plan_canonical_digest_mismatch")
    return {"identity": identity, "jobs": jobs, "proofs": proofs, "pack_indices": nonempty,
            "authority_changed": value["authority_changed"], "document": value}


def semantic_census(value, contract, index=None):
    aggregate = index is None
    require(isinstance(value, dict) and value.get("schema") ==
            ("ci.semantic_evidence.v1" if aggregate else "ci.semantic_fragment.v1"), "semantic_schema_mismatch")
    require(all(value.get(key) == expected for key, expected in contract["identity"].items()), "semantic_identity_mismatch")
    if aggregate:
        require(value.get("status") in ("clear", "failure")
                and value.get("authority_changed") is contract["authority_changed"], "aggregate_shape_mismatch")
        payload = dict(value); published = payload.pop("evidence_sha256", None)
        require(digest(published) and sha(encoded(payload)) == published, "aggregate_canonical_digest_mismatch")
    else:
        require(type(value.get("pack_index")) is int and value["pack_index"] == index
                and index in contract["pack_indices"], "semantic_pack_index_mismatch")
    require(isinstance(value.get("jobs"), list) and len(value["jobs"]) <= MAX_LOGICAL_JOBS
            and isinstance(value.get("infrastructure"), list), "semantic_inventory_shape_mismatch")
    seen_jobs, seen_proofs, outcomes, classifications, not_passed = set(), set(), collections.Counter(), collections.Counter(), []
    infra = list(value["infrastructure"])
    for job in value["jobs"]:
        require(isinstance(job, dict), "semantic_job_not_object")
        name = logical_id(job.get("logical_job_id")); expected_job = contract["jobs"].get(name)
        require(expected_job is not None and name not in seen_jobs and job.get("job_exec_sha256") == expected_job["job_exec_sha256"],
                "unknown_duplicate_or_changed_semantic_job")
        actual_index = job.get("pack_index") if aggregate else index
        require(type(actual_index) is int and actual_index == expected_job["pack_index"], "semantic_job_pack_mismatch")
        seen_jobs.add(name)
        require(isinstance(job.get("steps"), list) and len(job["steps"]) <= 4096
                and isinstance(job.get("infrastructure"), dict), "semantic_job_shape_mismatch")
        if job["infrastructure"].get("outcome") != "passed":
            infra.append({"logical_job_id": name, "observation": job["infrastructure"]})
        for step in job["steps"]:
            require(isinstance(step, dict), "semantic_step_not_object")
            key = (name, proof_id(step.get("proof_id"))); expected = contract["proofs"].get(key)
            require(expected is not None and key not in seen_proofs
                    and step.get("step_spec_sha256") == expected["step_spec_sha256"], "unknown_duplicate_or_changed_semantic_proof")
            require(isinstance(step.get("outcome"), str) and 0 < len(step["outcome"]) <= 80, "semantic_outcome_not_bounded_text")
            seen_proofs.add(key); outcomes[step["outcome"]] += 1
            classification = step.get("classification")
            if aggregate:
                require(isinstance(classification, str) and 0 < len(classification) <= 80, "semantic_classification_not_bounded_text")
                classifications[classification] += 1
            if step["outcome"] != "passed":
                not_passed.append({"logical_job_id": name, "proof_id": key[1], "pack_index": actual_index,
                                   "outcome": step["outcome"], "classification": classification})
    expected_jobs = {name for name, row in contract["jobs"].items() if aggregate or row["pack_index"] == index}
    expected_proofs = {key for key, row in contract["proofs"].items() if aggregate or row["pack_index"] == index}
    if aggregate:
        require(seen_jobs == expected_jobs and seen_proofs == expected_proofs, "aggregate_plan_job_or_proof_census_incomplete")
    return {"logical_jobs": len(seen_jobs), "proofs": len(seen_proofs),
            "missing_jobs": sorted(expected_jobs - seen_jobs), "missing_proofs": [list(key) for key in sorted(expected_proofs - seen_proofs)],
            "outcome_counts": dict(outcomes), "classification_counts": dict(classifications),
            "nonpassed_observations": not_passed, "infrastructure": infra,
            "published_status": value.get("status"), "outcomes_reclassified": False}


def upload_records(job, pin):
    """Bound an upload by its actual current-attempt job log, never by name alone."""
    raw = read_saved(pin["path"], MAX_LOG).decode("utf-8", "replace")
    lines = [re.sub(r"^\d{4}-\d\d-\d\dT\S+Z\s+", "", re.sub(r"\x1b\[[0-9;]*m", "", line))
             for line in raw.splitlines()]
    # The runner's first endgroup closes inputs, before upload output starts.
    # Each new step/post-job boundary clears provenance from earlier uploads.
    boundaries = [index for index, line in enumerate(lines)
                  if line.startswith(("##[group]Run ", "##[group]Post ", "Post job cleanup.", "Cleaning up orphan processes"))]
    result, boundary_cursor = [], -1
    for position, line in enumerate(lines):
        while boundary_cursor + 1 < len(boundaries) and boundaries[boundary_cursor + 1] <= position:
            boundary_cursor += 1
        matched = re.fullmatch(r"Artifact (.+) has been successfully uploaded! Final size is ([0-9]+) bytes\. Artifact ID is ([0-9]+)", line)
        if not matched:
            continue
        name, size, artifact_id = matched.group(1), int(matched.group(2)), int(matched.group(3))
        beginning = boundaries[boundary_cursor] if boundary_cursor >= 0 else position
        ending = boundaries[boundary_cursor + 1] if boundary_cursor + 1 < len(boundaries) else len(lines)
        header = re.fullmatch(r"##\[group\]Run actions/upload-artifact@([a-f0-9]{40})", lines[beginning])
        # A normal upload has a short parameter/output region. Unexpected
        # action versions or verbose/ambiguous event shapes stay incomplete.
        preceding = lines[beginning:position] if position - beginning <= 2048 else []
        ends = [index for index, item in enumerate(preceding) if item == "##[endgroup]"]
        inputs_end = ends[0] if ends else 0
        configured_names = [item.removeprefix("name: ") for item in preceding[1:inputs_end] if item.startswith("name: ")]
        output = preceding[inputs_end + 1:] if ends else []
        digests = [(index, match.group(1)) for index, item in enumerate(output)
                   if (match := re.fullmatch(r"SHA256 digest of uploaded artifact zip is ([a-f0-9]{64})", item))]
        finalized = f"Artifact {name}.zip successfully finalized. Artifact ID {artifact_id}"
        download = f"Artifact download URL: https://github.com/{REPO}/actions/runs/{RUN}/artifacts/{artifact_id}"
        finalized_positions = [index for index, item in enumerate(output) if item == finalized]
        following = lines[position + 1:min(ending, position + 10)]
        complete = bool(header) and len(ends) == 1 and configured_names == [name] and 0 < size <= MAX_ZIP and artifact_id > 0 \
            and len(digests) == 1 and len(finalized_positions) == 1 and digests[0][0] < finalized_positions[0] \
            and not any("has been successfully uploaded! Final size is " in item for item in output) \
            and following.count(download) == 1
        result.append({"name": name, "artifact_id": artifact_id, "bytes": size,
                       "sha256": digests[0][1] if len(digests) == 1 else None, "complete": complete,
                       "job_id": job["id"], "job_name": job["name"], "run_id": RUN, "head_sha": HEAD, "attempt": ATTEMPT,
                       "job_census_endpoint": RUN_PATH + f"/attempts/{ATTEMPT}/jobs",
                       "log": pin, "action_ref": header.group(1) if header else None,
                       "upload_step_start_line": beginning + 1, "success_line": position + 1,
                       "artifact_url": download.removeprefix("Artifact download URL: ") if following.count(download) == 1 else None})
    return result


def selected_artifact(name, artifacts, uploads, producer=None):
    matches = [row for row in uploads if row["name"] == name]
    require(len(matches) == 1 and matches[0]["complete"], "missing_or_ambiguous_current_attempt_upload:" + name)
    upload = matches[0]
    require(producer is None or upload["job_name"] == producer, "unexpected_artifact_producer:" + name)
    rows = [row for row in artifacts if row["id"] == upload["artifact_id"] and row["name"] == name]
    require(len(rows) == 1 and rows[0].get("preserved") is True, "uploaded_artifact_not_preserved:" + name)
    row = rows[0]
    require(row["zip"]["sha256"] == upload["sha256"] and row["zip"]["bytes"] == upload["bytes"],
            "actual_upload_digest_or_size_mismatch:" + name)
    row["selected_attempt_upload"] = upload
    return row


def artifact_signature(rows):
    keys = ("id", "name", "size_in_bytes", "digest", "expired", "created_at", "updated_at", "expires_at", "workflow_run")
    return sorted([{key: row.get(key) for key in keys} for row in rows], key=lambda row: row["id"])


def error_row(scope, exc):
    result = {"scope": scope, "code": exc.code if isinstance(exc, Refusal) else "capture_exception", "type": type(exc).__name__}
    if isinstance(exc, OSError):
        result["errno"] = exc.errno
    return result


def capture(report):
    start = api(RUN_PATH, "api/run-start.json")
    report["run_identity_start"] = run_identity(start)
    attempt_path = RUN_PATH + f"/attempts/{ATTEMPT}"
    attempt_start = api(attempt_path, "api/attempt-start.json")
    report["attempt_identity_start"] = run_identity(attempt_start)
    require(report["attempt_identity_start"] == report["run_identity_start"], "current_run_and_requested_attempt_disagree")
    jobs_path = attempt_path + "/jobs"
    jobs = census(jobs_path, "jobs", f"jobs-attempt{ATTEMPT}-start", MAX_JOBS)
    for job in jobs:
        job_identity(job)
    artifacts = census(RUN_PATH + "/artifacts", "artifacts", "artifacts-start", MAX_ARTIFACTS)
    require(all(isinstance(row.get("name"), str) and 0 < len(row["name"]) <= 512 for row in artifacts), "invalid_artifact_name")
    report["jobs_count"], report["artifacts_count"] = len(jobs), len(artifacts)
    report["job_census_endpoint"] = jobs_path
    counts = collections.Counter(row["name"] for row in artifacts)
    report["historical_or_duplicate_artifact_names"] = {name: count for name, count in counts.items() if count > 1}
    report["artifacts"], report["job_logs"], report["upload_records"] = [], [], []
    for item in sorted(artifacts, key=lambda row: row["id"]):
        artifact_id, name = item["id"], item["name"]
        row = {"id": artifact_id, "name": name, "preserved": False}
        report["artifacts"].append(row)
        try:
            meta = api(PREFIX + f"/actions/artifacts/{artifact_id}", f"artifacts/{artifact_id}.metadata.json")
            require(artifact_signature([meta]) == artifact_signature([item]), "artifact_metadata_changed")
            owner = meta.get("workflow_run", {})
            require(owner.get("id") == RUN and owner.get("head_sha") == HEAD
                    and owner.get("repository_id") == REPO_ID and owner.get("head_repository_id") == REPO_ID,
                    "artifact_run_or_head_mismatch")
            require(meta.get("expired") is False and type(meta.get("size_in_bytes")) is int
                    and 0 < meta["size_in_bytes"] <= MAX_ZIP, "expired_or_oversize_artifact")
            github_digest = meta.get("digest")
            require(isinstance(github_digest, str) and re.fullmatch(r"sha256:[a-f0-9]{64}", github_digest), "missing_github_artifact_digest")
            pin = api(PREFIX + f"/actions/artifacts/{artifact_id}/zip", f"artifacts/{artifact_id}.zip", MAX_ZIP, False)
            row["zip"] = pin
            require(pin["sha256"] == github_digest[7:] and pin["bytes"] == meta["size_in_bytes"], "github_artifact_digest_or_size_mismatch")
            row["github_digest_verified"] = True
            row["members"] = archive_members(pin["path"], artifact_id)
            row["preserved"] = True
        except Exception as exc:
            report["errors"].append(error_row(f"artifact:{artifact_id}", exc))

    # Complete started-job logs bind artifact uploads to this explicit attempt.
    # A skipped job with no start timestamp has no executed log to preserve.
    for job in sorted(jobs, key=lambda row: row["id"]):
        if job["conclusion"] == "skipped" and job.get("started_at") is None and job["steps"] == []:
            report["job_logs"].append({"job_id": job["id"], "name": job["name"], "not_executed": True,
                                       "conclusion": "skipped", "preserved": True})
            continue
        row = {"job_id": job["id"], "name": job["name"], "conclusion": job["conclusion"],
               "run_attempt": ATTEMPT, "head_sha": HEAD, "html_url": job.get("html_url"), "preserved": False}
        report["job_logs"].append(row)
        try:
            row["log"] = api(PREFIX + f"/actions/jobs/{job['id']}/logs", f"logs/{job['id']}.log", MAX_LOG, False)
            require(row["log"]["bytes"] > 0, "required_job_log_empty")
            row["preserved"] = True
            uploads = upload_records(job, row["log"])
            row["upload_record_count"] = len(uploads); report["upload_records"].extend(uploads)
        except Exception as exc:
            report["errors"].append(error_row(f"job_log:{job['id']}", exc))

    # Discovery and identity/census checks happen after raw preservation, so a
    # red/missing/unsupported plan never erases its available artifacts or logs.
    try:
        plan_row = selected_artifact(PLAN_NAME, report["artifacts"], report["upload_records"], "ci-plan")
        plan = artifact_document(plan_row, "ci-plan.json")
        contract = plan_contract(plan)
        report["tested_tree"], report["tested_base"] = plan["tested_tree_sha"], plan["base_sha"]
        REQUIRED.update({f"ci-semantic-pack-{RUN}-{index}": f"pack-{index}.json" for index in contract["pack_indices"]})
        report["required_artifacts"] = dict(REQUIRED)
        job_counts = collections.Counter(job["name"] for job in jobs)
        expected_jobs = ["ci-plan", "ci-gate", *[f"ci-pack-{index}" for index in contract["pack_indices"]]]
        report["required_job_name_counts"] = {name: job_counts[name] for name in expected_jobs}
        require(all(count == 1 for count in report["required_job_name_counts"].values()), "required_job_name_set_incomplete_or_ambiguous")
        require(not {name for name in job_counts if re.fullmatch(r"ci-pack-[0-9]+", name)} - set(expected_jobs),
                "executed_pack_outside_actual_plan")
        report["additional_job_names"] = sorted(set(job_counts) - set(expected_jobs))
        report["plan_census"] = {"identity": contract["identity"], "canonical_plan_digest_verified": True,
            "eligible_logical_jobs": len(contract["jobs"]), "proof_count": len(contract["proofs"]),
            "skipped_logical_jobs": len(plan["skipped_jobs"]), "legacy_logical_jobs": plan["legacy_job_count"],
            "nonempty_pack_indices": contract["pack_indices"],
            "per_pack": [{"pack_index": index,
                          "logical_jobs": sum(row["pack_index"] == index for row in contract["jobs"].values()),
                          "proofs": sum(row["pack_index"] == index for row in contract["proofs"].values())}
                         for index in contract["pack_indices"]],
            "source_protocol": SEMANTIC_PROTOCOL_SOURCE, "canonical_reconciler_executed": False}
        report["semantic_census"] = {}
        for name, member in REQUIRED.items():
            if name == PLAN_NAME:
                continue
            try:
                producer = "ci-gate" if name == AGGREGATE_NAME else None if name == CHANGED_NAME else "ci-pack-" + name.rsplit("-", 1)[1]
                row = selected_artifact(name, report["artifacts"], report["upload_records"], producer)
                document = artifact_document(row, member)
                if name == CHANGED_NAME:
                    require(isinstance(document, list) and all(isinstance(item, str) for item in document), "changed_file_list_not_array_of_paths")
                    require(len(document) == plan["changed_files_count"], "plan_changed_file_count_mismatch")
                    report["changed_files_binding"] = {"count": len(document), "plan_published_digest": plan["changed_files_sha256"],
                        "captured_array_canonical_sha256": sha(encoded(document)),
                        "linkage": "Exact GitHub ZIP/upload custody and count correspondence; producer-specific changed-file normalization is not re-executed or assumed."}
                else:
                    index = None if name == AGGREGATE_NAME else int(name.rsplit("-", 1)[1])
                    report["semantic_census"][name] = semantic_census(document, contract, index)
            except Exception as exc:
                report["errors"].append(error_row("semantic_artifact:" + name, exc))
        report["missing_required_artifacts"] = sorted(name for name in REQUIRED
            if not any(row["name"] == name and row.get("selected_attempt_upload") for row in report["artifacts"]))
    except Exception as exc:
        report["errors"].append(error_row("actual_plan_and_census", exc))

    final_jobs = census(jobs_path, "jobs", f"jobs-attempt{ATTEMPT}-end", MAX_JOBS)
    for job in final_jobs:
        job_identity(job)
    final_artifacts = census(RUN_PATH + "/artifacts", "artifacts", "artifacts-end", MAX_ARTIFACTS)
    report["job_inventory_stable"] = job_signature(jobs) == job_signature(final_jobs)
    report["artifact_inventory_stable"] = artifact_signature(artifacts) == artifact_signature(final_artifacts)
    attempt_end = api(attempt_path, "api/attempt-end.json")
    report["attempt_identity_end"] = run_identity(attempt_end)
    end = api(RUN_PATH, "api/run-end.json")
    report["run_identity_end"] = run_identity(end)
    report["attempt_identity_stable"] = report["attempt_identity_start"] == report["attempt_identity_end"]
    report["run_identity_stable"] = report["run_identity_start"] == report["run_identity_end"]
    report["ci_conclusion"] = end["conclusion"]
    require(report["run_identity_stable"] and report["attempt_identity_stable"]
            and report["job_inventory_stable"] and report["artifact_inventory_stable"], "run_attempt_job_or_artifact_inventory_changed")
    report["raw_preservation_complete"] = all(row["preserved"] for row in report["artifacts"]) and all(row["preserved"] for row in report["job_logs"])
    require(report["raw_preservation_complete"], "raw_preservation_incomplete")
    require(report.get("plan_census") and not report.get("missing_required_artifacts") and not report["errors"], "capture_has_errors_or_missing_semantic_evidence")
    report["complete"], report["pass"] = True, True


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise Refusal("invalid_arguments")


def receipt_bytes(report):
    remaining()
    report["finished_at"], report["requests"], report["files"] = now(), REQUESTS, FILES
    raw = encoded(report) + b"\n"
    remaining()
    require(len(raw) <= MAX_JSON, "receipt_size_limit")
    return raw


def persist_receipt(raw, pending_name):
    """Atomically finalize only this invocation's receipt in its new directory."""
    remaining()
    if ROOT_FD is None:
        return
    fd = new_file(pending_name)
    try:
        view = memoryview(raw)
        while view:
            remaining()
            size = os.write(fd, view)
            require(size > 0, "receipt_short_write")
            view = view[size:]
        os.fsync(fd)
        remaining()
    finally:
        os.close(fd)
    # Keep this immutable snapshot even if a later stdout/finalization failure
    # replaces the latest alias. No raw file or earlier receipt is erased.
    link_name = pending_name + ".link"
    os.link(pending_name, link_name, src_dir_fd=ROOT_FD, dst_dir_fd=ROOT_FD, follow_symlinks=False)
    os.replace(link_name, "capture.json", src_dir_fd=ROOT_FD, dst_dir_fd=ROOT_FD)
    os.fsync(ROOT_FD)
    remaining()


def emit_stdout(raw):
    """No buffered flush or unlimited pipe wait, including at interpreter exit."""
    global STDOUT_BYTES, STDOUT_ATTEMPTED
    fd = sys.stdout.fileno()
    was_blocking = os.get_blocking(fd)
    end = time.monotonic() + min(5.0, remaining())
    os.set_blocking(fd, False)
    try:
        view = memoryview(raw)
        while view:
            left = min(end - time.monotonic(), remaining())
            require(left > 0, "stdout_deadline_exceeded")
            try:
                STDOUT_ATTEMPTED = True
                size = os.write(fd, view[:65536])
                require(size > 0, "stdout_short_write")
                STDOUT_BYTES += size
                view = view[size:]
            except BlockingIOError:
                select.select([], [fd], [], min(0.25, left))
        remaining()
    finally:
        os.set_blocking(fd, was_blocking)


def main():
    global ROOT_FD, GH, DEADLINE, RUN, ATTEMPT, HEAD, RUN_PATH, PLAN_NAME, AGGREGATE_NAME
    hard_deadline = time.monotonic() + 600.0
    # The normal deadline includes capture, serialization, fsync and stdout.
    # Reserve the final five seconds, still within 600, for a failure receipt.
    DEADLINE = hard_deadline - 5.0
    report = {"schema": "intl.completed_ci_capture.v2", "pass": False, "complete": False,
              "repository": REPO, "run_id": None, "attempt": None, "subject_head": None,
              "started_at": now(), "errors": [], "release_acceptance": False,
              "canonical_reconciler_executed": False,
              "qualification": "Complete capture is independent of CI success. Counts derive from the actual exact-attempt plan. Raw failures remain unchanged; the canonical semantic reconciler is not re-executed or replaced."}
    old_alarm = signal.signal(signal.SIGALRM, timeout_handler)
    signal.setitimer(signal.ITIMER_REAL, remaining())
    output_complete = False
    raw = None
    try:
        try:
            parser = Parser(add_help=False)
            parser.add_argument("--run-id", required=True)
            parser.add_argument("--expected-head-sha", required=True)
            parser.add_argument("--attempt", required=True)
            parser.add_argument("--output-dir", required=True)
            parser.add_argument("--gh")
            args = parser.parse_args()
            require(re.fullmatch(r"[1-9][0-9]{0,18}", args.run_id)
                    and re.fullmatch(r"[1-9][0-9]{0,5}", args.attempt)
                    and digest(args.expected_head_sha, 40), "explicit_run_attempt_and_full_head_required")
            RUN, ATTEMPT, HEAD = int(args.run_id), int(args.attempt), args.expected_head_sha
            RUN_PATH = PREFIX + "/actions/runs/" + str(RUN)
            PLAN_NAME = f"ci-semantic-plan-{RUN}-{ATTEMPT}"
            AGGREGATE_NAME = f"ci-semantic-evidence-{RUN}"
            REQUIRED.update({PLAN_NAME: "ci-plan.json", CHANGED_NAME: "changed-files.json", AGGREGATE_NAME: "ci-semantic-evidence.json"})
            report.update(run_id=RUN, attempt=ATTEMPT, subject_head=HEAD, required_artifacts=dict(REQUIRED))
            GH = args.gh or shutil.which("gh")
            require(isinstance(GH, str) and os.path.isabs(GH) and os.path.isfile(GH) and os.access(GH, os.X_OK), "gh_executable_not_available")
            ROOT_FD = create_root(args.output_dir)
            report["output_directory"] = args.output_dir
            report["gh_executable"] = GH
            capture(report)
        except Exception as exc:
            report["pass"], report["complete"] = False, False
            report["errors"].append(error_row("capture", exc))
        raw = receipt_bytes(report)
        persist_receipt(raw, "capture.finalizing.json")
        emit_stdout(encoded({"schema": report["schema"], "pass": report["pass"], "complete": report["complete"],
                             "run_id": RUN, "attempt": ATTEMPT, "subject_head": HEAD,
                             "ci_conclusion": report.get("ci_conclusion"), "release_acceptance": False,
                             "output_directory": report.get("output_directory"), "capture_sha256": sha(raw),
                             "jobs": report.get("jobs_count"), "artifacts": report.get("artifacts_count"),
                             "errors": len(report["errors"])}) + b"\n")
        output_complete = True
    except Exception as exc:
        report["pass"], report["complete"] = False, False
        report["errors"].append(error_row("finalization", exc))
        # Keep a live deadline through failure serialization/output too. Never
        # extend the original 600-second hard bound or retry any GitHub request.
        DEADLINE = min(hard_deadline, time.monotonic() + 5.0)
        signal.setitimer(signal.ITIMER_REAL, max(0.001, DEADLINE - time.monotonic()))
        report = {"schema": report["schema"], "pass": False, "complete": False, "repository": REPO,
                  "run_id": RUN, "attempt": ATTEMPT, "subject_head": HEAD,
                  "started_at": report["started_at"], "finished_at": now(),
                  "output_directory": report.get("output_directory"), "release_acceptance": False,
                  "errors": report["errors"], "stdout_bytes_before_failure": STDOUT_BYTES,
                  "stdout_write_attempted": STDOUT_ATTEMPTED,
                  "previous_candidate_receipt_sha256": sha(raw) if raw is not None else None,
                  "qualification": "Finalization failed. Existing raw captures remain diagnostic only; success requires exit0 and a complete matching receipt."}
        try:
            remaining()
            raw = encoded(report) + b"\n"
            persist_receipt(raw, "capture.failure-finalizing.json")
            # Do not append a second JSON object to a partial or complete first
            # output. Exit2 and the failure capture.json govern that situation.
            if not STDOUT_ATTEMPTED:
                emit_stdout(encoded({"schema": report["schema"], "pass": False, "complete": False,
                                     "run_id": RUN, "attempt": ATTEMPT, "subject_head": HEAD,
                                     "output_directory": report.get("output_directory"),
                                     "capture_sha256": sha(raw), "release_acceptance": False,
                                     "errors": len(report["errors"])}) + b"\n")
        except Exception:
            # A broken/full pipe or unusable filesystem can prevent the failure
            # receipt too; it must never restore a passing return code.
            report["pass"], report["complete"] = False, False
    finally:
        if ROOT_FD is not None:
            try:
                os.close(ROOT_FD)
            except OSError:
                report["pass"], report["complete"] = False, False
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old_alarm)
    return 0 if output_complete and report["pass"] and report["complete"] else 2


if __name__ == "__main__":
    sys.exit(main())
