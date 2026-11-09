"""Observe two installed CLI consumers after independently authorized release.

No automatic source qualification or production acceptance is performed here.
The original assigning parent supplies an exact, independently qualified binding.
"""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import selectors
import signal
import stat
import subprocess
import sys
import time


FILES = (
    "engine/intelligence_registry.py", "scripts/build_intelligence_registry.py",
    "engine/postmortem.py", "scripts/build_output_health.py",
    "engine/qledger_validity.py", "scripts/check_qledger_metric_validity.py",
    "scripts/agentos.py",
    "engine/neuralweb/response_eval.py", "engine/neuralweb/native_facts.py",
    "engine/neuralweb/brain_gateway.py", "lib/mastermind_response_log.py",
    "app/deploy/update.sh",
)
LIMIT = 16 * 1024 * 1024
SCOPE = ("Observed CLI invocations and twelve direct source files only. This does not "
         "prove dependency closure, atomic data snapshots, production acceptance, "
         "model performance, live numeric-verifier execution, earned tiers, rights, Discovery adoption or natural "
         "owner progression. Qualification and authorization belong to the caller.")


class Refused(Exception):
    pass


def strict_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise Refused("duplicate_json_key")
            result[key] = value
        return result

    def constant(_):
        raise Refused("nonfinite_json")

    def number(value):
        result = float(value)
        if not (-float("inf") < result < float("inf")):
            raise Refused("nonfinite_json")
        return result

    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=pairs,
                          parse_constant=constant, parse_float=number)
    except (UnicodeError, ValueError, RecursionError):
        raise Refused("invalid_json") from None


def relative_path(value):
    if (not isinstance(value, str) or len(value.encode("utf-8")) > 2048
            or "\\" in value or "\x00" in value
            or any(part in ("", ".", "..") for part in value.split("/"))):
        raise Refused("invalid_relative_path")
    return value


def regular_bytes(path, limit):
    """No-follow traversal and bounded read; detects observed replacement/mutation."""
    path = Path(path)
    if not path.is_absolute() or any(p in (".", "..") for p in path.parts):
        raise Refused("absolute_path_required")
    directory = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
    descriptor = None
    try:
        for part in path.parts[1:-1]:
            next_directory = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                                     dir_fd=directory)
            os.close(directory)
            directory = next_directory
        descriptor = os.open(path.name, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW,
                             dir_fd=directory)
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or not 0 < before.st_size <= limit:
            raise Refused("source_not_bounded_regular_file")
        chunks, count = [], 0
        while count <= limit:
            chunk = os.read(descriptor, min(65536, limit + 1 - count))
            if not chunk:
                break
            chunks.append(chunk)
            count += len(chunk)
        after = os.fstat(descriptor)
        named = os.stat(path.name, dir_fd=directory, follow_symlinks=False)
        identity = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
        if (count > limit or count != before.st_size
                or identity(before) != identity(after) or identity(after) != identity(named)):
            raise Refused("source_changed_during_read")
        return b"".join(chunks)
    finally:
        if descriptor is not None:
            os.close(descriptor)
        os.close(directory)


def binding_from(path):
    value = strict_json(regular_bytes(path, 65536))
    if (not isinstance(value, dict) or set(value) != {"schema", "source_commit", "files"}
            or value["schema"] != "eval_os.followon_probe_binding.v1"
            or not isinstance(value["source_commit"], str)
            or not re.fullmatch(r"[0-9a-f]{40}", value["source_commit"])
            or not isinstance(value["files"], dict) or set(value["files"]) != set(FILES)
            or any(not isinstance(v, str) or not re.fullmatch(r"[0-9a-f]{64}", v)
                   for v in value["files"].values())):
        raise Refused("invalid_binding")
    return value


def snapshot(root):
    return {path: hashlib.sha256(regular_bytes(root / path, LIMIT)).hexdigest()
            for path in FILES}


def capture(argv, root, timeout=180, limit=LIMIT):
    """Drain both pipes within bounds and always reap this invocation's child."""
    start = time.monotonic()
    buffers = {"stdout": bytearray(), "stderr": bytearray()}
    condition = "completed"
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    proc = subprocess.Popen(argv, cwd=root, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            env=env, start_new_session=True)
    selector = selectors.DefaultSelector()
    try:
        for name in buffers:
            pipe = getattr(proc, name)
            os.set_blocking(pipe.fileno(), False)
            selector.register(pipe, selectors.EVENT_READ, name)
        while selector.get_map() or proc.poll() is None:
            remaining = timeout - (time.monotonic() - start)
            if remaining <= 0:
                condition = "timeout"
                break
            for key, _ in selector.select(min(remaining, 0.1)):
                data = os.read(key.fd, min(65536, limit + 1 - len(buffers[key.data])))
                if not data:
                    selector.unregister(key.fileobj)
                    continue
                buffers[key.data].extend(data)
                if len(buffers[key.data]) > limit:
                    condition = "output_limit"
                    break
            if condition != "completed":
                break
    finally:
        # Only the new process group created above is ever signalled. Descendants
        # holding a pipe open are also stopped, even if the immediate child exited.
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        proc.wait()
        selector.close()
        proc.stdout.close()
        proc.stderr.close()
    record = {"condition": condition, "returncode": proc.returncode,
              "elapsed_seconds": round(time.monotonic() - start, 3), "streams": {}}
    for name, data in buffers.items():
        record["streams"][name] = {"captured_bytes": len(data),
                                  "sha256": hashlib.sha256(data).hexdigest(),
                                  "complete": condition == "completed"}
    return record, bytes(buffers["stdout"])


def observed_head(root):
    record, data = capture(["git", "-C", str(root), "rev-parse", "HEAD"], root, 15, 4096)
    if record["condition"] != "completed" or record["returncode"] != 0:
        raise Refused("head_observation_failed")
    value = data.decode("ascii").strip()
    if not re.fullmatch(r"[0-9a-f]{40}", value):
        raise Refused("head_observation_invalid")
    return value


def summarize(kind, value):
    if not isinstance(value, dict):
        raise Refused("consumer_contract_invalid")
    if kind == "required_tier":
        query = value.get("query")
        if (value.get("schema") != "intelligence_registry.required_tier_cli.v1"
                or not isinstance(query, dict) or value.get("source_failure") is not None
                or not isinstance(value.get("source_report"), dict)
                or query.get("schema") != "intelligence_registry.required_tier.v1"
                or query.get("scope") != "exact_registered_producer_paths"
                or query.get("status") not in ("unresolved", "partial", "resolved")
                or not isinstance(query.get("changed_paths"), list)
                or not isinstance(query.get("engines"), list)
                or not isinstance(query.get("unresolved"), list)
                or query.get("evaluation_status") != "not_assessed"
                or "required_tier" not in query
                or query["required_tier"] not in (None, "T1", "T3")
                or "maximum_supported_tier" not in query
                or query["maximum_supported_tier"] not in (None, "T1", "T3")):
            raise Refused("consumer_contract_invalid")
        return {"schema": value["schema"], "evaluation_status": query["evaluation_status"],
                "required_tier": query["required_tier"],
                "status": query["status"], "maximum_supported_tier": query["maximum_supported_tier"],
                "engine_count": len(query["engines"]), "unresolved_count": len(query["unresolved"]),
                "source_report_present": isinstance(value.get("source_report"), dict)}
    if (value.get("schema") != "postmortem.source_findings.v1"
            or value.get("scope") != "source_data_observations"
            or value.get("evaluation_status") != "not_assessed"
            or value.get("count_unit") != "health_observations"
            or value.get("observation_identity_scope") != "this_snapshot_only"
            or value.get("observation_unit") != "output_reason_pair_in_supplied_snapshot"
            or "observed_at" not in value
            or (value["observed_at"] is not None and
                (not isinstance(value["observed_at"], str) or len(value["observed_at"]) > 64))
            or any(not isinstance(value.get(k), list)
                   for k in ("observations", "groups", "unaffected_outputs"))):
        raise Refused("consumer_contract_invalid")
    counts = {k: value.get(k) for k in
              ("n_outputs", "unavailable_output_count", "unclassified_observation_count")}
    if any(type(v) is not int or v < 0 for v in counts.values()):
        raise Refused("consumer_contract_invalid")
    return {"schema": value["schema"], "evaluation_status": value["evaluation_status"],
            "count_unit": value["count_unit"], "observed_at": value["observed_at"], **counts,
            **{k + "_count": len(value[k])
               for k in ("observations", "groups", "unaffected_outputs")}}


def observe(root, binding_path, producers, python):
    receipt = {"schema": "eval_os.followon_adoption_observation.v1", "scope": SCOPE,
               "observed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
               "production_proven": False, "programme_complete": False,
               "discovery_adopted": False, "status": "refused", "commands": []}
    try:
        root = Path(root)
        if not root.is_absolute() or not Path(python).is_absolute() or not producers:
            raise Refused("absolute_root_python_and_producer_required")
        producers = list(dict.fromkeys(relative_path(p) for p in producers))
        if len(producers) > 64:
            raise Refused("producer_limit")
        binding = binding_from(binding_path)
        receipt["source_commit"] = binding["source_commit"]
        receipt["before"] = snapshot(root)
        if receipt["before"] != binding["files"]:
            raise Refused("source_binding_mismatch")
        receipt["head_before"] = observed_head(root)
        commands = [("required_tier", [python, "-B", str(root / FILES[1]), "--root", str(root)]
                     + [a for p in producers for a in ("--required-tier", p)]),
                    ("source_findings", [python, "-B", str(root / FILES[3]), "--root", str(root),
                                         "--source-findings"])]
        receipt["producer_paths"] = producers
        for kind, argv in commands:
            if snapshot(root) != receipt["before"]:
                raise Refused("source_changed_during_observation")
            record, data = capture(argv, root)
            record["consumer"] = kind
            receipt["commands"].append(record)
            if record["condition"] != "completed" or record["returncode"] != 0:
                raise Refused("consumer_execution_failed")
            value = strict_json(data)
            record["summary"] = summarize(kind, value)
            if kind == "required_tier" and value["query"]["changed_paths"] != sorted(producers):
                raise Refused("consumer_query_identity_mismatch")
        receipt["after"] = snapshot(root)
        receipt["head_after"] = observed_head(root)
        if receipt["before"] != receipt["after"] or receipt["head_before"] != receipt["head_after"]:
            raise Refused("source_changed_during_observation")
        receipt["status"] = "observed"
    except Refused as exc:
        receipt["reason"] = str(exc)
    except (OSError, ValueError, UnicodeError, subprocess.SubprocessError, RecursionError):
        receipt["reason"] = "observation_unavailable"
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True)
    parser.add_argument("--binding", required=True)
    parser.add_argument("--producer", action="append", required=True)
    parser.add_argument("--python", required=True)
    args = parser.parse_args()
    result = observe(args.root, args.binding, args.producer, args.python)
    print(json.dumps(result, allow_nan=False, sort_keys=True))
    return 0 if result["status"] == "observed" else 2


if __name__ == "__main__":
    sys.exit(main())
