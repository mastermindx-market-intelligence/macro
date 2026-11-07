"""scripts/run_causal_brainstorm.py — CHF W5 LLM chain runner.

Operator trigger + auto_loop gate + OAuth identity + ISO-week idempotency.
Mirrors the cortex job architecture (tool loop client pattern, provider waterfall,
run_status dict, never-raise contract, exit 0 always except unexpected crash).

CHF-R8 (as amended by operator ruling 2026-07-09 — masterplan §9): the LLM chain
runs only when:
  (i)  trigger == 'operator'   — any available auth provider (full waterfall)
  (ii) trigger == 'scheduled'  AND config auto_loop is true  AND the
       CLAUDE_CODE_OAUTH_TOKEN (oauth) provider is available. The operator
       directed OAuth-ONLY identity for scheduled runs, superseding the
       original service-key requirement; the ANTHROPIC_API_KEY provider is
       explicitly excluded from the scheduled path.
Without auth or gate: pack-only mode (operator-paste workflow).

CHF-R17: LLM actor law — the chain is a mechanical rule-application pipeline.
The script never transitions card status; cards land status='inbox' via the ingest.

Usage:
    python -m scripts.run_causal_brainstorm [--root PATH] [--trigger operator|scheduled] [--dry-run]
    python -m scripts.run_causal_brainstorm --status-only   # nightly lane-status refresh

--status-only refreshes data/neuralweb/causal_llm_lane.json from config truth
(no pack build, no LLM calls). The nightly non-Tuesday branch of daily.yml runs
it so the lane artifact never misreports the auto_loop state between weekly
runs (before 2026-07-11 the file was only written on Tuesdays, so a config
flip mid-week showed as "auto_loop disabled" for up to six days).

Outputs (non-fatal on any individual failure):
  /tmp/causal_brainstorm_pack_<isoweek>.txt  — brainstorm pack (always rebuilt fresh)
  data/neuralweb/causal_brainstorm_runs.jsonl — LLM raw replies + token counts (append)
  data/neuralweb/causal_llm_lane.json        — W3-readable lane status
  data/neuralweb/causal_mechanisms.jsonl     — cards filed via ingest (write mode only)
  data/neuralweb/governance.jsonl            — a6_llm_proposed event per filed batch
"""
from __future__ import annotations

import argparse
import copy
from contextlib import contextmanager
import fcntl
import hashlib
import json
import logging
import os
import secrets
import stat
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_CONFIG_PATH = ROOT / "config" / "causal_llm.yml"
_LANE_FILE = ROOT / "data" / "neuralweb" / "causal_llm_lane.json"
_RUNS_FILE = ROOT / "data" / "neuralweb" / "causal_brainstorm_runs.jsonl"
_MECHANISMS_DIR = ROOT / "data" / "neuralweb"


# Selected research records extend each runner's existing append journal. They
# are not a provider ledger: the shared Fabric owners alone admit, call, charge
# and close. A crash leaves the original run held, including across week or
# selector changes.
_RESEARCH_EVENT = "fabric_research_run.v1"
_RESEARCH_LIMIT = 64 * 1024 * 1024
_RESEARCH_TEXT_LIMIT = 1024 * 1024
_RESEARCH_ROLES = ("generator", "skeptic", "compiler")
_RESEARCH_BOUNDS = {"causal-brainstorm": (4000, 2000, 3000),
                    "signal-foundry": (6000, 3000, 5000)}


class _ResearchHeld(ValueError):
    pass


def _r_json(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      allow_nan=False, separators=(",", ":"))


def _r_hash(value):
    return hashlib.sha256(_r_json(value).encode("utf-8")).hexdigest()


def _r_pairs(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise _ResearchHeld("research_duplicate_json_key")
        value[key] = item
    return value


def _r_decode(text):
    def nonfinite(_value):
        raise _ResearchHeld("research_nonfinite_json")
    return json.loads(text, object_pairs_hook=_r_pairs, parse_constant=nonfinite)


def _r_path(root, lane):
    relative = ("data/neuralweb/causal_brainstorm_runs.jsonl"
                if lane == "causal-brainstorm" else
                "data/signal_foundry/governance.jsonl")
    if lane not in _RESEARCH_BOUNDS:
        raise _ResearchHeld("research_lane_invalid")
    return root / relative


@contextmanager
def _r_parent_fd(path, root, *, create=False, durable=False):
    """Anchor every component and keep its physical parent until the I/O ends."""
    path, root = Path(path).absolute(), Path(root).absolute()
    if path == root or not path.is_relative_to(root):
        raise _ResearchHeld("research_root_boundary")
    fds, links = [], []
    try:
        parent_fd = os.open(path.anchor, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        fds.append(parent_fd)
        current = Path(path.anchor)
        for component in path.parent.parts[1:]:
            current = current / component
            try:
                before = os.stat(component, dir_fd=parent_fd, follow_symlinks=False)
            except FileNotFoundError:
                if not create or not current.is_relative_to(root):
                    raise
                os.mkdir(component, mode=0o700, dir_fd=parent_fd)
                os.fsync(parent_fd)
                before = os.stat(component, dir_fd=parent_fd, follow_symlinks=False)
            if not stat.S_ISDIR(before.st_mode):
                raise _ResearchHeld("research_unsafe_parent")
            child_fd = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                               dir_fd=parent_fd)
            fds.append(child_fd)
            actual = os.fstat(child_fd)
            identity = (actual.st_dev, actual.st_ino)
            if identity != (before.st_dev, before.st_ino):
                raise _ResearchHeld("research_parent_changed")
            links.append((parent_fd, component, child_fd, identity))
            if durable and (current == root or current.is_relative_to(root)):
                os.fsync(child_fd)
                os.fsync(parent_fd)
            parent_fd = child_fd
        def check():
            for owner_fd, name, child_fd, identity in links:
                named = os.stat(name, dir_fd=owner_fd, follow_symlinks=False)
                actual = os.fstat(child_fd)
                if (not stat.S_ISDIR(named.st_mode)
                        or (named.st_dev, named.st_ino) != identity
                        or (actual.st_dev, actual.st_ino) != identity):
                    raise _ResearchHeld("research_parent_changed")
        check()
        yield parent_fd, check
        check()
    finally:
        for fd in reversed(fds):
            os.close(fd)


def _r_sync_dir(path):
    with _r_parent_fd(Path(path) / ".fsync-boundary", Path(path)) as (fd, check):
        check()
        os.fsync(fd)


def _r_safe_parent(path, root, *, create=False, durable=False):
    with _r_parent_fd(path, root, create=create, durable=durable):
        pass


class _ResearchSnapshot(bytes):
    def __new__(cls, raw, file_identity, parent_identity):
        value = super().__new__(cls, raw)
        value.file_identity = file_identity
        value.parent_identity = parent_identity
        return value


def _r_read_bytes(path, root, *, missing=True, snapshot=False):
    with _r_parent_fd(path, root) as (parent_fd, check):
        check()
        parent = os.fstat(parent_fd)
        parent_identity = (parent.st_dev, parent.st_ino)
        try:
            fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                         dir_fd=parent_fd)
        except FileNotFoundError:
            if missing:
                return _ResearchSnapshot(b"", None, parent_identity) if snapshot else b""
            raise _ResearchHeld("research_file_missing") from None
        try:
            before = os.fstat(fd)
            if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
                raise _ResearchHeld("research_unsafe_file")
            if before.st_size > _RESEARCH_LIMIT:
                raise _ResearchHeld("research_journal_bound")
            with os.fdopen(fd, "rb", closefd=False) as fh:
                raw = fh.read(_RESEARCH_LIMIT + 1)
            after = os.fstat(fd)
            named = os.stat(path.name, dir_fd=parent_fd, follow_symlinks=False)
            identity = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns)
            if (len(raw) > _RESEARCH_LIMIT or after.st_nlink != 1 or identity(before) != identity(after)
                    or identity(after) != identity(named)):
                raise _ResearchHeld("research_file_changed")
            check()
            return (_ResearchSnapshot(raw, (after.st_dev, after.st_ino), parent_identity)
                    if snapshot else raw)
        finally:
            os.close(fd)


def _r_rows(raw):
    if raw and not raw.endswith(b"\n"):
        raise _ResearchHeld("research_partial_journal_tail")
    rows = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        if len(line) > 8 * _RESEARCH_TEXT_LIMIT:
            raise _ResearchHeld("research_record_bound")
        value = _r_decode(line.decode("utf-8"))
        if type(value) is not dict:
            raise _ResearchHeld("research_record_invalid")
        rows.append(value)
    return rows


@contextmanager
def _r_lock(path, root):
    with _r_parent_fd(path, root, create=True, durable=True) as (parent_fd, check):
        name = path.name + ".lock"
        check()
        fd = os.open(name, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK,
                     0o600, dir_fd=parent_fd)
        try:
            before = os.fstat(fd)
            if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
                raise _ResearchHeld("research_unsafe_lock")
            fcntl.flock(fd, fcntl.LOCK_EX)
            named = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
            if (named.st_dev, named.st_ino) != (before.st_dev, before.st_ino):
                raise _ResearchHeld("research_lock_changed")
            check()
            os.fsync(fd)
            os.fsync(parent_fd)
            yield
            check()
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)


def _r_digest(value):
    return type(value) is str and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def _r_count(value):
    return type(value) is int and 0 <= value <= 10 ** 12


def _r_label(value):
    return type(value) is str and bool(value.strip()) and len(value.encode()) <= 512


def _r_inspection(value, identity):
    if (type(value) is not dict or set(value) !=
            {"provider", "model", "cap_id", "capability_id", "cost_basis",
             "workload_policy", "transport_identity"}
            or any(not _r_label(value[k]) for k in
                   ("provider", "model", "cap_id", "capability_id", "cost_basis"))
            or not _r_digest(value["transport_identity"])
            or identity["trigger"] == "scheduled" and value["cost_basis"] not in ("subscription", "local")):
        raise _ResearchHeld("research_inspection_invalid")
    policy = value["workload_policy"]
    if (type(policy) is not dict or set(policy) !=
            {"schema", "policy_revision", "policy_hash", "profiles",
             "execution_surface", "allowed_order", "denied_order"}
            or policy["schema"] != "mastermind.provider_workload_decision.v1"
            or type(policy["policy_revision"]) is not int or policy["policy_revision"] < 1
            or not _r_digest(policy["policy_hash"])
            or type(policy["profiles"]) is not list or not policy["profiles"]
            or any(not _r_label(p) for p in policy["profiles"])
            or len(policy["profiles"]) != len(set(policy["profiles"]))
            or policy["execution_surface"] != "inference"
            or policy["allowed_order"] != ["fabric"] or policy["denied_order"] != []):
        raise _ResearchHeld("research_workload_receipt_invalid")


def _r_stage_receipt(stage):
    receipt, inspection = stage["receipt"], stage["inspection"]
    if (type(receipt) is not dict or set(receipt) !=
            {"operation_id", "provider", "requested_model", "served_model",
             "observation", "usage", "close", "effect_unknown"}
            or receipt["operation_id"] != stage["operation_id"]
            or receipt["provider"] != inspection["provider"]
            or receipt["requested_model"] != inspection["model"]
            or type(receipt["effect_unknown"]) is not bool
            or receipt["served_model"] is not None and not _r_label(receipt["served_model"])):
        raise _ResearchHeld("research_receipt_invalid")
    close, observation, usage = receipt["close"], receipt["observation"], receipt["usage"]
    if close is None:
        if not receipt["effect_unknown"]:
            raise _ResearchHeld("research_close_receipt_invalid")
    elif (type(close) is not dict or set(close) !=
            {"disposition", "closed", "effect_unknown", "attempted"}
            or close["disposition"] not in ("not_bound", "local_only", "refused", "pending", "effect_unknown", "closed")
            or any(type(close[k]) is not bool for k in ("closed", "effect_unknown", "attempted"))
            or close["closed"] != (close["disposition"] == "closed")
            or close["disposition"] == "closed" and (not close["attempted"] or close["effect_unknown"])
            or close["disposition"] in ("not_bound", "local_only") and any(
                close[k] for k in ("closed", "effect_unknown", "attempted"))
            or close["effect_unknown"] and not receipt["effect_unknown"]
            or close["disposition"] in ("pending", "effect_unknown") and not receipt["effect_unknown"]):
        raise _ResearchHeld("research_close_receipt_invalid")
    if observation is not None and (type(observation) is not dict or set(observation) !=
            {"request_id", "serving_model", "input_tokens", "output_tokens"}
            or observation["request_id"] != stage["operation_id"] + ":brain:0"
            or observation["serving_model"] is not None and not _r_label(observation["serving_model"])
            or any(observation[k] is not None and not _r_count(observation[k])
                   for k in ("input_tokens", "output_tokens"))):
        raise _ResearchHeld("research_observation_invalid")
    if usage is None:
        if (close is None or close["disposition"] != "not_bound"
                or observation is not None or receipt["served_model"] is not None):
            raise _ResearchHeld("research_usage_invalid")
    elif (type(usage) is not dict or set(usage) !=
            {"input_tokens", "output_tokens", "usage_state",
             "completed_input_tokens", "completed_output_tokens"}
            or usage["usage_state"] not in ("known", "unknown")
            or any(not _r_count(usage[k]) for k in ("completed_input_tokens", "completed_output_tokens"))
            or any(usage[k] is not None and not _r_count(usage[k]) for k in ("input_tokens", "output_tokens"))
            or usage["usage_state"] == "known" and any(
                usage[k] != usage["completed_" + k] for k in ("input_tokens", "output_tokens"))
            or usage["usage_state"] == "unknown" and any(
                usage[k] is not None for k in ("input_tokens", "output_tokens"))):
        raise _ResearchHeld("research_usage_invalid")
    if usage is not None and observation is not None:
        # Exactly one request belongs to each role. Partial observations remain
        # nullable metadata; a complete pair alone contributes completed usage.
        pair = all(observation[k] is not None for k in ("input_tokens", "output_tokens"))
        if any(usage["completed_" + k] != (observation[k] if pair else 0)
               for k in ("input_tokens", "output_tokens")):
            raise _ResearchHeld("research_usage_observation_mismatch")
    if stage["state"] == "closed":
        if (stage["error"] is not None or stage["text"] is None or receipt["effect_unknown"]
                or receipt["served_model"] != inspection["model"]
                or observation is None or observation["serving_model"] != receipt["served_model"]
                or close is None or close["disposition"] not in ("closed", "local_only")
                or close["effect_unknown"] or usage is None):
            raise _ResearchHeld("research_closed_stage_invalid")
    elif not _r_label(stage["error"]):
        raise _ResearchHeld("research_held_reason_invalid")


def _r_file_receipt(value, path, before=None):
    if (type(value) is not dict or set(value) !=
            {"path", "before_sha256", "after_sha256", "rows", "file_identity"}
            or value["path"] != path
            or not _r_digest(value["before_sha256"]) or not _r_digest(value["after_sha256"])
            or before is not None and value["before_sha256"] != before
            or type(value["rows"]) is not list or any(type(r) is not dict for r in value["rows"])
            or value["file_identity"] is not None and (
                type(value["file_identity"]) is not list or len(value["file_identity"]) != 2
                or any(type(v) is not int or not 0 <= v < 2 ** 64 for v in value["file_identity"]))
            or value["rows"] and value["file_identity"] is None
            or not value["rows"] and value["before_sha256"] != value["after_sha256"]):
        raise _ResearchHeld("research_business_receipt_invalid")


def _r_filing_receipt(filing, run, lane):
    if (type(filing) is not dict or set(filing) != {"state", "intent", "intent_digest", "receipt"}
            or filing["state"] not in ("pending", "closed")
            or len(run["stages"]) != 3 or any(s["state"] != "closed" for s in run["stages"])
            or _r_hash(filing["intent"]) != filing["intent_digest"]):
        raise _ResearchHeld("research_filing_invalid")
    identity, intent, receipt = run["identity"], filing["intent"], filing["receipt"]
    models = {s["role"]: s["receipt"]["served_model"] for s in run["stages"]}
    causal = lane == "causal-brainstorm"
    key, kind = ("cards", "causal_ingest") if causal else ("specs", "signal_foundry_screen")
    if (type(intent) is not dict or set(intent) !=
            {"kind", key, "models", "dry_run", "iso_week", "before" if causal else "before_sha256"}
            or intent["kind"] != kind or intent["models"] != models
            or intent["dry_run"] is not identity["dry_run"] or intent["iso_week"] != identity["iso_week"]
            or type(intent[key]) is not list or any(type(v) is not dict for v in intent[key])):
        raise _ResearchHeld("research_filing_intent_invalid")
    paths = ({"cards": "data/neuralweb/causal_mechanisms.jsonl",
              "budget": "data/neuralweb/causal_filing_budget.jsonl",
              "governance": "data/neuralweb/governance.jsonl"} if causal else
             {"candidates": "data/signal_foundry/candidates.jsonl",
              "governance": "data/signal_foundry/governance.jsonl"})
    if causal:
        if (type(intent["before"]) is not dict or set(intent["before"]) != set(paths)
                or any(not _r_digest(v) for v in intent["before"].values())):
            raise _ResearchHeld("research_filing_preimage_invalid")
    elif not _r_digest(intent["before_sha256"]):
        raise _ResearchHeld("research_filing_preimage_invalid")
    if filing["state"] == "pending":
        if receipt is not None:
            raise _ResearchHeld("research_pending_filing_invalid")
        return
    fields = {"kind", "n_proposed", "n_filed", "dry_run", "files", "governance"}
    if not causal:
        fields |= {"n_admitted", "n_screen_rejected", "screened_rows"}
    if (type(receipt) is not dict or set(receipt) != fields or receipt["kind"] != kind
            or receipt["dry_run"] is not identity["dry_run"]
            or not _r_count(receipt["n_proposed"]) or receipt["n_proposed"] != len(intent[key])
            or not _r_count(receipt["n_filed"]) or receipt["n_filed"] > receipt["n_proposed"]
            or identity["dry_run"] and receipt["n_filed"] != 0
            or type(receipt["files"]) is not dict or set(receipt["files"]) != set(paths)):
        raise _ResearchHeld("research_filing_receipt_invalid")
    files = receipt["files"]
    for name, path in paths.items():
        before = intent["before"][name] if causal else (
            intent["before_sha256"] if name == "candidates" else None)
        _r_file_receipt(files[name], path, before)
    if causal:
        rows, budget = files["cards"]["rows"], files["budget"]["rows"]
        ids = [r.get("mechanism_id") for r in rows]
        if (len(rows) != receipt["n_filed"] or any(not _r_label(v) for v in ids)
                or len(ids) != len(set(ids))
                or sorted(ids) != sorted(r.get("mechanism_id", "") for r in budget)
                or any(r.get("kind") != "filing_budget" or r.get("filing_week") != identity["iso_week"]
                       for r in budget)
                or any(r.get("mechanism_id") not in [c.get("mechanism_id") for c in intent["cards"]]
                       or r.get("status") != "inbox" or r.get("actor") != "script"
                       or r.get("filing_week") != identity["iso_week"]
                       or type(r.get("lineage")) is not dict
                       or r["lineage"].get("model_label") != models["generator"] for r in rows)):
            raise _ResearchHeld("research_causal_receipt_invalid")
        evidence = {"pack_id": run["run_id"], "run_id": run["run_id"],
                    "n_cards": len(rows), "n_proposed": len(intent[key]),
                    "trigger": identity["trigger"], "models": models, "dry_run": identity["dry_run"]}
        events = files["governance"]["rows"]
        if (len(events) != 1 or events[0].get("event_type") != "a6_llm_proposed"
                or events[0].get("target") != "causal_mechanisms"
                or events[0].get("authored_by") != "run_causal_brainstorm"):
            raise _ResearchHeld("research_governance_receipt_invalid")
    else:
        rows = receipt["screened_rows"]
        if (type(rows) is not list or len(rows) != receipt["n_proposed"]
                or any(type(r) is not dict for r in rows)
                or any(not _r_count(receipt[k]) for k in ("n_admitted", "n_screen_rejected"))
                or sum(r.get("status") == "proposed" for r in rows) != receipt["n_admitted"]
                or sum(r.get("status") == "screen_rejected" for r in rows) != receipt["n_screen_rejected"]
                or receipt["n_admitted"] + receipt["n_screen_rejected"] != len(rows)
                or files["candidates"]["rows"] != ([] if identity["dry_run"] else rows)
                or receipt["n_filed"] != len(files["candidates"]["rows"])
                or any(r.get("fabric_run_id") != run["run_id"] or r.get("fabric_served_models") != models
                       or r.get("iso_week") != identity["iso_week"] or not _r_label(r.get("id"))
                       or type(r.get("screen_result")) is not dict for r in rows)
                or len({r["id"] for r in rows}) != len(rows)):
            raise _ResearchHeld("research_signal_receipt_invalid")
        evidence = {"pack_id": run["run_id"], "run_id": run["run_id"],
                    "iso_week": identity["iso_week"], "trigger": identity["trigger"],
                    "n_admitted": receipt["n_admitted"], "n_screen_rejected": receipt["n_screen_rejected"],
                    "n_proposed": len(intent[key]), "n_filed": receipt["n_filed"],
                    "models": models, "dry_run": identity["dry_run"]}
        events = files["governance"]["rows"]
        if (len(events) != 1 or events[0].get("event") != "sf_llm_proposed"
                or events[0].get("authored_by") != "run_signal_foundry_brainstorm"):
            raise _ResearchHeld("research_governance_receipt_invalid")
    if receipt["governance"] != evidence or events[0].get("evidence") != evidence:
        raise _ResearchHeld("research_governance_correlation_invalid")


def _r_validate_run(run, root, lane):
    if (type(run) is not dict or set(run) !=
            {"run_id", "identity", "identity_digest", "state", "stages", "filing", "outcome"}
            or run["state"] not in ("active", "held", "complete")
            or type(run["run_id"]) is not str
            or not run["run_id"].startswith(lane + ":")
            or len(run["run_id"]) != len(lane) + 33
            or any(c not in "0123456789abcdef" for c in run["run_id"].rsplit(":", 1)[-1])):
        raise _ResearchHeld("research_run_invalid")
    identity = run["identity"]
    if (type(identity) is not dict or set(identity) !=
            {"root", "lane", "iso_week", "trigger", "dry_run", "cfg",
             "selection", "pack", "source_digest"}
            or identity["root"] != str(root.absolute()) or identity["lane"] != lane
            or identity["trigger"] not in ("operator", "scheduled")
            or type(identity["dry_run"]) is not bool
            or type(identity["cfg"]) is not dict
            or type(identity["iso_week"]) is not str
            or not _r_digest(identity["source_digest"])
            or type(identity["selection"]) is not dict
            or set(identity["selection"]) != {"mode", "host_profile"}
            or not _r_label(identity["selection"]["mode"])
            or identity["selection"]["host_profile"] is not None
                and not _r_label(identity["selection"]["host_profile"])
            or type(identity["pack"]) is not str
            or len(identity["pack"].encode()) > _RESEARCH_TEXT_LIMIT
            or _r_hash(identity) != run["identity_digest"]):
        raise _ResearchHeld("research_identity_invalid")
    stages = run["stages"]
    if type(stages) is not list or len(stages) > 3:
        raise _ResearchHeld("research_stage_order")
    for index, stage in enumerate(stages):
        if (type(stage) is not dict or set(stage) !=
                {"role", "operation_id", "inspection", "request", "request_digest",
                 "state", "text", "text_digest", "receipt", "error"}
                or stage["role"] != _RESEARCH_ROLES[index]
                or stage["operation_id"] != run["run_id"] + ":" + stage["role"]
                or stage["state"] not in ("pending", "closed", "held")
                or type(stage["inspection"]) is not dict):
            raise _ResearchHeld("research_stage_invalid")
        _r_inspection(stage["inspection"], identity)
        if index and stage["inspection"] != stages[0]["inspection"]:
            raise _ResearchHeld("research_saved_inspection_changed")
        request = stage["request"]
        if (type(request) is not dict or set(request) !=
                {"system", "user", "max_tokens", "requested_model", "response_contract"}
                or type(request["system"]) is not str or type(request["user"]) is not str
                or not request["user"].strip()
                or len((request["system"] + request["user"]).encode()) > _RESEARCH_TEXT_LIMIT
                or request["max_tokens"] != _RESEARCH_BOUNDS[lane][index]
                or type(request["max_tokens"]) is not int
                or request["response_contract"] != "complete-text-v1"
                or not _r_label(request["requested_model"])
                or _r_hash(request) != stage["request_digest"]):
            raise _ResearchHeld("research_request_invalid")
        configured = identity["cfg"].get("model_roles" if lane == "causal-brainstorm" else "models") or {}
        defaults = ("claude-sonnet-4-6", "claude-opus-4-8", "claude-haiku-4-5-20251001")
        if (type(configured) is not dict or request["requested_model"] != configured.get(stage["role"], defaults[index])
                or index == 0 and request["user"] != identity["pack"]):
            raise _ResearchHeld("research_saved_request_changed")
        if index < len(stages) - 1 and stage["state"] != "closed":
            raise _ResearchHeld("research_stage_order")
        text = stage["text"]
        if text is not None and (type(text) is not str or not text.strip()
                or len(text.encode()) > _RESEARCH_TEXT_LIMIT
                or stage["text_digest"] != _r_hash(text)):
            raise _ResearchHeld("research_saved_text_invalid")
        if text is None and stage["text_digest"] is not None:
            raise _ResearchHeld("research_saved_text_invalid")
        if stage["state"] == "pending":
            if any(stage[key] is not None for key in ("text", "text_digest", "receipt", "error")):
                raise _ResearchHeld("research_pending_invalid")
        else:
            _r_stage_receipt(stage)
    filing = run["filing"]
    if filing is not None:
        _r_filing_receipt(filing, run, lane)
    if run["state"] != "complete" and run["outcome"] is not None:
        raise _ResearchHeld("research_unfinished_outcome")
    if any(s["state"] == "held" for s in stages) and run["state"] != "held":
        raise _ResearchHeld("research_held_stage_state")
    if run["state"] == "complete" and (
            any(s["state"] != "closed" for s in stages)
            or filing is not None and filing["state"] != "closed"
            or type(run["outcome"]) is not dict):
        raise _ResearchHeld("research_completion_invalid")
    if run["state"] == "complete":
        outcome = run["outcome"]
        if (outcome.get("mode") != "fabric" or outcome.get("trigger") != identity["trigger"]
                or outcome.get("iso_week") != identity["iso_week"]
                or outcome.get("dry_run") is not identity["dry_run"]
                or type(outcome.get("stages")) is not dict):
            raise _ResearchHeld("research_outcome_invalid")
        result = outcome.get("result")
        if (result not in ("pack_failed", "generator_parse_failed", "all_dropped", "filed")
                or not _r_count(outcome.get("n_filed"))):
            raise _ResearchHeld("research_outcome_invalid")
        if filing is None:
            details = outcome["stages"]
            valid = (result == "pack_failed" and not stages
                     and type(details.get("pack")) is str and details["pack"].startswith("error:"))
            valid = valid or (result == "generator_parse_failed" and len(stages) == 1
                             and type(details.get("generator")) is dict
                             and _r_label(details["generator"].get("parse_error")))
            if result == "all_dropped" and len(stages) == 2:
                valid = (details.get("skeptic", {}).get("n_surviving") == 0
                         or _parse_json_array(stages[0]["text"], _strict=True) == [])
            if not valid or outcome["n_filed"] != 0:
                raise _ResearchHeld("research_zero_filing_outcome_invalid")
        if filing is not None:
            receipt = filing["receipt"]
            if result != "filed" or outcome["n_filed"] != receipt["n_filed"]:
                raise _ResearchHeld("research_outcome_filing_mismatch")
            expected = ({"rc": 0, "dry_run": identity["dry_run"],
                         "n_proposed": receipt["n_proposed"], "n_filed": receipt["n_filed"]}
                        if lane == "causal-brainstorm" else
                        {k: receipt[k] for k in ("n_admitted", "n_screen_rejected", "n_filed")})
            if outcome["stages"].get("ingest" if lane == "causal-brainstorm" else "screen") != expected:
                raise _ResearchHeld("research_outcome_filing_mismatch")


def _r_transition(old, new):
    if old is None:
        if (new["state"] != "active" or new["stages"] or new["filing"] is not None
                or new["outcome"] is not None):
            raise _ResearchHeld("research_initial_record_invalid")
        return
    if old["run_id"] != new["run_id"]:
        if old["state"] != "complete" or new["state"] != "active" or new["stages"]:
            raise _ResearchHeld("research_original_not_complete")
        _r_transition(None, new)
    else:
        if (old["identity"] != new["identity"] or old["state"] != "active"
                or len(new["stages"]) not in (len(old["stages"]), len(old["stages"]) + 1)):
            raise _ResearchHeld("research_original_changed")
        for index, stage in enumerate(old["stages"]):
            current = new["stages"][index]
            if stage["state"] != "pending" and stage != current:
                raise _ResearchHeld("research_closed_result_changed")
            for key in ("role", "operation_id", "inspection", "request", "request_digest"):
                if stage[key] != current[key]:
                    raise _ResearchHeld("research_stage_identity_changed")
        if old["filing"] is not None:
            if (new["filing"] is None or old["filing"]["intent"] != new["filing"]["intent"]
                    or old["filing"]["state"] == "closed" and old["filing"] != new["filing"]):
                raise _ResearchHeld("research_filing_changed")
        if len(new["stages"]) > len(old["stages"]) and new["stages"][-1]["state"] != "pending":
            raise _ResearchHeld("research_stage_intent_missing")
        if old["filing"] is None and new["filing"] is not None and new["filing"]["state"] != "pending":
            raise _ResearchHeld("research_filing_intent_missing")


def _r_history(path, root, lane):
    raw = _r_read_bytes(path, root)
    records = []
    previous = None
    for row in _r_rows(raw):
        event = row.get("event")
        shaped = ("run" in row and any(key in row for key in ("revision", "previous", "digest")))
        if event != _RESEARCH_EVENT and (shaped or isinstance(event, str)
                                        and event.startswith("fabric_research_run")):
            raise _ResearchHeld("research_journal_version")
        if event != _RESEARCH_EVENT:
            continue
        if (set(row) != {"event", "revision", "previous", "run", "digest"}
                or type(row["revision"]) is not int or row["revision"] != len(records) + 1
                or row["previous"] != previous
                or row["digest"] != _r_hash({k: v for k, v in row.items() if k != "digest"})):
            raise _ResearchHeld("research_journal_order")
        _r_validate_run(row["run"], root, lane)
        _r_transition(records[-1]["run"] if records else None, row["run"])
        _r_unique_original(records, row["run"])
        records.append(row)
        previous = row["digest"]
    return raw, records


def _r_unique_original(records, run):
    if not records or records[-1]["run"]["run_id"] == run["run_id"]:
        return
    if any(record["run"]["run_id"] == run["run_id"]
           or record["run"]["state"] == "complete"
               and record["run"]["identity_digest"] == run["identity_digest"] for record in records):
        raise _ResearchHeld("research_duplicate_original")


def _r_append(path, root, lane, run, expected):
    # Caller owns only the short journal lock. No model/network work is here.
    raw, records = _r_history(path, root, lane)
    prior = records[-1]["digest"] if records else None
    if prior != expected:
        raise _ResearchHeld("research_journal_cas")
    _r_validate_run(run, root, lane)
    _r_transition(records[-1]["run"] if records else None, run)
    _r_unique_original(records, run)
    row = {"event": _RESEARCH_EVENT, "revision": len(records) + 1,
           "previous": prior, "run": copy.deepcopy(run)}
    row["digest"] = _r_hash(row)
    encoded = (_r_json(row) + "\n").encode()
    if len(encoded) - 1 > 8 * _RESEARCH_TEXT_LIMIT:
        raise _ResearchHeld("research_record_bound")
    if len(raw) + len(encoded) > _RESEARCH_LIMIT:
        raise _ResearchHeld("research_journal_bound")
    with _r_parent_fd(path, root) as (parent_fd, check):
        try:
            before = os.stat(path.name, dir_fd=parent_fd, follow_symlinks=False)
        except FileNotFoundError:
            before = None
        check()
        fd = os.open(path.name, os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK,
                     0o600, dir_fd=parent_fd)
        try:
            actual = os.fstat(fd)
            if (not stat.S_ISREG(actual.st_mode) or actual.st_nlink != 1
                    or before is not None and (before.st_dev, before.st_ino) != (actual.st_dev, actual.st_ino)):
                raise _ResearchHeld("research_journal_changed")
            check()
            if os.write(fd, encoded) != len(encoded):
                raise _ResearchHeld("research_short_append")
            os.fsync(fd)
            named = os.stat(path.name, dir_fd=parent_fd, follow_symlinks=False)
            if (named.st_dev, named.st_ino) != (actual.st_dev, actual.st_ino):
                raise _ResearchHeld("research_journal_changed")
            check()
            os.fsync(parent_fd)
        finally:
            os.close(fd)
    checked, history = _r_history(path, root, lane)
    if checked != raw + encoded or history[-1] != row:
        raise _ResearchHeld("research_append_ack_unknown")
    return row["digest"]


def _r_existing(root, lane):
    path = _r_path(root, lane)
    # Missing genuine parents are empty history; symlinks and replaced parents
    # are not. Keep this read free of creation until an actual journal exists.
    try:
        with _r_parent_fd(path, root) as (parent_fd, check):
            check()
            os.stat(path.name, dir_fd=parent_fd, follow_symlinks=False)
    except FileNotFoundError:
        return None
    with _r_lock(path, root):
        _, records = _r_history(path, root, lane)
        return copy.deepcopy(records[-1]["run"]) if records else None


def _r_selection(cfg):
    from engine import llm_auth
    return {"mode": llm_auth.application_mode_id(cfg),
            "host_profile": os.environ.get("MM_PROVIDER_WORKLOAD_PROFILE")}


def _r_native_guard(cfg, root, lane):
    original = _r_existing(root, lane)
    if original is not None and original["state"] != "complete":
        raise _ResearchHeld("research_original_held")
    if _r_selection(cfg)["mode"] is not None:
        raise _ResearchHeld("research_bound_stage_required")


class _ResearchRun:
    def __init__(self, cfg, trigger, iso_week, dry_run, root, lane, source_path):
        from engine.provider_production_modes import make_application_fabric_factory
        self.root, self.lane = Path(root).absolute(), lane
        self.path = _r_path(self.root, lane)
        self.cfg = copy.deepcopy(cfg)
        self.selection = _r_selection(cfg)
        if self.selection["mode"] is None:
            raise _ResearchHeld("research_selection_required")
        self.selected = {**copy.deepcopy(cfg), "provider_order": ["fabric"],
                         "usage_lane": lane, "oauth_pool_lane": lane}
        self.selected.setdefault("workload_profile", "portfolio_analysis")
        self.factory = make_application_fabric_factory(
            mode_id=self.selection["mode"], lane=lane, root=self.root,
            workload_cfg={"workload_profile": "portfolio_analysis", "usage_lane": lane,
                          "provider_order": ["fabric"]})
        self.inspection = self.factory.inspect(self.selected)
        if trigger == "scheduled" and self.inspection["cost_basis"] not in ("subscription", "local"):
            raise _ResearchHeld("research_scheduled_nonmetered_qualification_required")
        self.identity = {"root": str(self.root), "lane": lane, "iso_week": iso_week,
                         "trigger": trigger, "dry_run": dry_run, "cfg": copy.deepcopy(cfg),
                         "selection": copy.deepcopy(self.selection), "pack": "",
                         "source_digest": hashlib.sha256(Path(source_path).read_bytes()).hexdigest()}
        self.run = None
        self.digest = None
        self.reused = False

    def claim(self, pack):
        if type(pack) is not str or not pack.strip() or len(pack.encode()) > _RESEARCH_TEXT_LIMIT:
            raise _ResearchHeld("research_pack_invalid")
        self.identity["pack"] = pack
        identity_digest = _r_hash(self.identity)
        with _r_lock(self.path, self.root):
            _, records = _r_history(self.path, self.root, self.lane)
            if records:
                prior = records[-1]["run"]
                if prior["state"] != "complete":
                    raise _ResearchHeld("research_original_held")
                # An intervening completed run does not retire an original.
                # The newest unresolved record still fences every older result.
                for record in reversed(records):
                    previous = record["run"]
                    if previous["state"] == "complete" and previous["identity_digest"] == identity_digest:
                        self.run = copy.deepcopy(previous)
                        self.digest, self.reused = records[-1]["digest"], True
                        return False
            self.run = {"run_id": self.lane + ":" + secrets.token_hex(16),
                        "identity": copy.deepcopy(self.identity), "identity_digest": identity_digest,
                        "state": "active", "stages": [], "filing": None, "outcome": None}
            self.digest = _r_append(self.path, self.root, self.lane, self.run,
                                   records[-1]["digest"] if records else None)
        return True

    def save(self, updated):
        with _r_lock(self.path, self.root):
            digest = _r_append(self.path, self.root, self.lane, updated, self.digest)
        self.run, self.digest = copy.deepcopy(updated), digest

    def call(self, role, requested_model, system, user, max_tokens, context):
        from engine import llm_auth
        if self.run is None or self.run["state"] != "active" or self.reused:
            raise _ResearchHeld("research_original_held")
        index = len(self.run["stages"])
        if index >= 3 or role != _RESEARCH_ROLES[index]:
            raise _ResearchHeld("research_stage_order")
        if _r_selection(self.cfg) != self.selection:
            raise _ResearchHeld("research_selection_changed")
        inspection = self.factory.inspect(self.selected)
        if inspection != self.inspection:
            raise _ResearchHeld("research_inspection_changed")
        stage = {"role": role, "operation_id": self.run["run_id"] + ":" + role,
                 "inspection": copy.deepcopy(inspection),
                 "request": {"system": system, "user": user, "max_tokens": max_tokens,
                             "requested_model": requested_model, "response_contract": "complete-text-v1"},
                 "request_digest": None, "state": "pending", "text": None,
                 "text_digest": None, "receipt": None, "error": None}
        stage["request_digest"] = _r_hash(stage["request"])
        updated = copy.deepcopy(self.run)
        updated["stages"].append(stage)
        self.save(updated)  # durable original intent precedes bind
        provider = operation = None
        text = observed_model = None
        error = fatal = None
        try:
            if _r_selection(self.cfg) != self.selection:
                raise _ResearchHeld("research_selection_changed")
            provider = llm_auth.build_fabric_provider(self.factory.with_inspection(inspection),
                request_id=stage["operation_id"], workload_cfg=self.selected)
            provider["usage_lane"] = self.lane
            operation = llm_auth.begin_operation([provider], operation_id=stage["operation_id"],
                                                 context=context)
            def invoke(client, model):
                nonlocal observed_model
                response = client.messages.create(model=model, max_tokens=max_tokens, system=system,
                    messages=[{"role": "user", "content": user}])
                observed_model = getattr(response, "model", None)
                blocks = getattr(response, "content", None)
                if (getattr(response, "stop_reason", None) != "end_turn"
                        or not isinstance(blocks, (list, tuple)) or not blocks
                        or any(getattr(b, "type", None) != "text" or type(getattr(b, "text", None)) is not str
                               for b in blocks)):
                    raise llm_auth.FabricProviderError("research_response_not_complete")
                answer = "".join(b.text for b in blocks)
                if not answer.strip() or len(answer.encode()) > _RESEARCH_TEXT_LIMIT:
                    raise llm_auth.FabricProviderError("research_response_invalid")
                return answer, None, response
            text, reason, _ = llm_auth.make_call(operation.providers, invoke, context=context)
            if text is None or reason is not None:
                raise _ResearchHeld("research_response_unavailable")
        except BaseException as exc:
            error = getattr(exc, "code", "research_stage_held")
            if not isinstance(exc, Exception):
                fatal = exc
        finally:
            try:
                if operation is not None:
                    operation.close()
                elif provider is not None:
                    llm_auth.close_fabric_provider(provider)
            except BaseException as exc:
                error = "research_close_unknown"
                if not isinstance(exc, Exception):
                    fatal = exc
        close = (provider.get("_fabric_close") if provider is not None else
                 {"disposition": "not_bound", "closed": False, "effect_unknown": False, "attempted": False})
        unknown = (type(close) is not dict or close.get("effect_unknown") is not False
                   or close.get("disposition") not in ("closed", "local_only", "not_bound")
                   or bool(provider and (provider.get("_fabric_pending")
                       or getattr(provider.get("_fabric_failure"), "effect_unknown", False))))
        observation = provider.get("_fabric_last_observation") if provider is not None else None
        if observed_model is None and isinstance(observation, dict):
            observed_model = observation.get("serving_model")
        receipt = {"operation_id": stage["operation_id"], "provider": inspection["provider"],
                   "requested_model": inspection["model"], "served_model": observed_model,
                   "observation": observation,
                   "usage": llm_auth.fabric_usage(provider) if provider is not None else None,
                   "close": close, "effect_unknown": unknown}
        held = unknown or error is not None or text is None or not observed_model
        settled = {**stage, "state": "held" if held else "closed", "text": text,
                   "text_digest": _r_hash(text) if text is not None else None,
                   "receipt": receipt, "error": error or ("research_stage_held" if held else None)}
        updated = copy.deepcopy(self.run)
        updated["stages"][-1] = settled
        if held:
            updated["state"] = "held"
        self.save(updated)
        if fatal is not None:
            raise fatal
        if held:
            raise _ResearchHeld("research_original_held")
        return text, None, inspection["provider"], {
            **(receipt["usage"] or {}), "served_model": observed_model,
            "operation_id": stage["operation_id"]}

    def filing_intent(self, intent):
        if self.run["filing"] is not None:
            raise _ResearchHeld("research_filing_already_claimed")
        updated = copy.deepcopy(self.run)
        updated["filing"] = {"state": "pending", "intent": copy.deepcopy(intent),
                             "intent_digest": _r_hash(intent), "receipt": None}
        self.save(updated)

    def filing_complete(self, receipt):
        updated = copy.deepcopy(self.run)
        updated["filing"]["state"] = "closed"
        updated["filing"]["receipt"] = copy.deepcopy(receipt)
        self.save(updated)

    def complete(self, outcome):
        if self.reused:
            return
        updated = copy.deepcopy(self.run)
        result = ("filed" if updated["filing"] is not None else
                  {0: "pack_failed", 1: "generator_parse_failed", 2: "all_dropped"}.get(len(updated["stages"])))
        updated["state"], updated["outcome"] = "complete", {
            **copy.deepcopy(outcome), "result": result,
            "n_filed": updated["filing"]["receipt"]["n_filed"] if result == "filed" else 0}
        self.save(updated)

    def hold(self):
        if self.run is not None and self.run["state"] == "active":
            updated = copy.deepcopy(self.run)
            updated["state"] = "held"
            self.save(updated)


def _r_file_snapshot(path, root):
    if not os.path.lexists(path):
        _r_safe_parent(path, root, create=True, durable=True)
    raw = _r_read_bytes(path, root, snapshot=True)
    _r_rows(raw)
    return raw


def _r_file_append_receipt(path, root, before):
    """Read, fsync and attest one anchored inode used by the existing writer."""
    if not isinstance(before, _ResearchSnapshot):
        raise _ResearchHeld("research_business_preimage_required")
    with _r_parent_fd(path, root) as (parent_fd, check):
        parent = os.fstat(parent_fd)
        if (parent.st_dev, parent.st_ino) != before.parent_identity:
            raise _ResearchHeld("research_business_parent_changed")
        check()
        try:
            fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                         dir_fd=parent_fd)
        except FileNotFoundError:
            if before.file_identity is not None:
                raise _ResearchHeld("research_business_file_missing") from None
            raw, rows, identity = b"", [], None
            os.fsync(parent_fd)
        else:
            try:
                actual = os.fstat(fd)
                identity = (actual.st_dev, actual.st_ino)
                if (not stat.S_ISREG(actual.st_mode) or actual.st_nlink != 1
                        or actual.st_size > _RESEARCH_LIMIT
                        or before.file_identity is not None and identity != before.file_identity):
                    raise _ResearchHeld("research_business_file_changed")
                raw = os.pread(fd, _RESEARCH_LIMIT + 1, 0)
                if len(raw) > _RESEARCH_LIMIT or not raw.startswith(before):
                    raise _ResearchHeld("research_business_prefix_changed")
                rows = _r_rows(raw[len(before):])
                os.fsync(fd)
                after = os.fstat(fd)
                named = os.stat(path.name, dir_fd=parent_fd, follow_symlinks=False)
                if ((named.st_dev, named.st_ino) != identity or after.st_nlink != 1
                        or (after.st_size, after.st_mtime_ns) != (actual.st_size, actual.st_mtime_ns)
                        or os.pread(fd, _RESEARCH_LIMIT + 1, 0) != raw):
                    raise _ResearchHeld("research_business_readback_changed")
                check()
                os.fsync(parent_fd)
            finally:
                os.close(fd)
        check()
    return {"path": str(path.relative_to(root)), "before_sha256": hashlib.sha256(before).hexdigest(),
            "after_sha256": hashlib.sha256(raw).hexdigest(), "rows": rows,
            "file_identity": list(identity) if identity is not None else None}



def _r_config(root, filename, native_cfg):
    """Select the root's real config only for a deliberate Fabric entry."""
    import yaml
    path = root / "config" / filename
    selected_at_start = _r_selection(native_cfg)["mode"] is not None
    if not path.exists():
        if selected_at_start:
            raise _ResearchHeld("research_selected_config_missing")
        return native_cfg
    _r_safe_parent(path, root)
    raw = _r_read_bytes(path, root, missing=False)
    try:
        cfg = yaml.safe_load(raw) or {}
        if type(cfg) is not dict:
            raise _ResearchHeld("research_config_invalid")
        _r_json(cfg)
    except Exception:
        if selected_at_start:
            raise _ResearchHeld("research_config_invalid") from None
        return native_cfg
    if _r_selection(cfg)["mode"] is not None:
        return cfg
    if selected_at_start:
        raise _ResearchHeld("research_selection_changed")
    return native_cfg


def _r_causal_roots(root):
    from scripts import causal_brainstorm_pack as pack, causal_ingest_brainstorm as ingest
    root = root.absolute()
    for module in (pack, ingest):
        if (Path(module.ROOT).absolute() != root
                or Path(module.__file__).resolve().parent.parent != root):
            raise _ResearchHeld("research_causal_companion_root_mismatch")
    required = {"_NULLS_FILE": root / "data/neuralweb/causal_nulls.jsonl",
                "_MACHINE_REGISTRY": root / "data/neuralweb/machine_registry.jsonl",
                "_TRIAL_LEDGER": root / "data/trial_ledger.jsonl",
                "_FILING_BUDGET": root / "data/neuralweb/causal_filing_budget.jsonl",
                "_CAUSAL_PRIORS": root / "config/causal_priors.yml"}
    if any(Path(getattr(ingest, key)).absolute() != path for key, path in required.items()):
        raise _ResearchHeld("research_causal_companion_root_mismatch")
    return ingest


def _r_causal_file(ctx, cards, run_status):
    from engine.neuralweb import governance
    ingest = _r_causal_roots(ctx.root)
    root, identity = ctx.root, ctx.run["identity"]
    paths = {"cards": root / "data/neuralweb/causal_mechanisms.jsonl",
             "budget": root / "data/neuralweb/causal_filing_budget.jsonl",
             "governance": root / "data/neuralweb/governance.jsonl"}
    before = {name: _r_file_snapshot(path, root) for name, path in paths.items()}
    models = {stage["role"]: stage["receipt"]["served_model"] for stage in ctx.run["stages"]}
    intent = {"kind": "causal_ingest", "cards": cards, "models": models,
              "dry_run": identity["dry_run"], "iso_week": identity["iso_week"],
              "before": {name: hashlib.sha256(raw).hexdigest() for name, raw in before.items()}}
    ctx.filing_intent(intent)
    with tempfile.TemporaryDirectory(prefix="chf_inbox_") as tmp:
        inbox = Path(tmp)
        (inbox / "brainstorm_cards.json").write_text(_r_json(cards), encoding="utf-8")
        rc = ingest.ingest(inbox=inbox, out_dir=root / "data/neuralweb",
                           dry_run=identity["dry_run"], model_label=models["generator"])
    if rc != 0:
        raise _ResearchHeld("research_ingest_not_complete")
    receipts = {name: _r_file_append_receipt(paths[name], root, before[name])
                for name in ("cards", "budget")}
    filed, budget = receipts["cards"]["rows"], receipts["budget"]["rows"]
    if identity["dry_run"] and (filed or budget):
        raise _ResearchHeld("research_dry_run_wrote_artifacts")
    expected_ids = {card.get("mechanism_id") for card in cards}
    if any(row.get("mechanism_id") not in expected_ids
           or row.get("status") != "inbox" or row.get("actor") != "script"
           or row.get("filing_week") != identity["iso_week"]
           or row.get("lineage", {}).get("model_label") != models["generator"]
           or ingest.validate_card(row) for row in filed):
        raise _ResearchHeld("research_ingest_receipt_invalid")
    if (sorted(row.get("mechanism_id", "") for row in filed)
            != sorted(row.get("mechanism_id", "") for row in budget)
            or any(row.get("kind") != "filing_budget"
                   or row.get("filing_week") != identity["iso_week"] for row in budget)):
        raise _ResearchHeld("research_filing_budget_unknown")
    evidence = {"pack_id": ctx.run["run_id"], "run_id": ctx.run["run_id"],
                "n_cards": len(filed), "n_proposed": len(cards),
                "trigger": identity["trigger"], "models": models,
                "dry_run": identity["dry_run"]}
    ok = governance.append_event("a6_llm_proposed", target="causal_mechanisms",
        article=None, authored_by="run_causal_brainstorm", evidence=evidence, root=root,
        note=f"CHF Fabric original; iso_week={identity['iso_week']}; dry_run={identity['dry_run']}")
    receipts["governance"] = _r_file_append_receipt(paths["governance"], root, before["governance"])
    events = receipts["governance"]["rows"]
    if (ok is not True or len(events) != 1 or events[0].get("evidence") != evidence
            or events[0].get("event_type") != "a6_llm_proposed"
            or events[0].get("target") != "causal_mechanisms"
            or events[0].get("authored_by") != "run_causal_brainstorm"):
        raise _ResearchHeld("research_governance_ack_unknown")
    receipt = {"kind": "causal_ingest", "n_proposed": len(cards), "n_filed": len(filed),
               "dry_run": identity["dry_run"], "files": receipts, "governance": evidence}
    ctx.filing_complete(receipt)
    run_status["stages"]["ingest"] = {"rc": rc, "dry_run": identity["dry_run"],
                                    "n_proposed": len(cards), "n_filed": len(filed)}
    return receipt


def _r_selected_run(cfg, trigger, iso_week, dry_run, root, lane, source_path, run):
    """Enter the caller's existing pipeline with one frozen original context."""
    ctx = None
    try:
        original = _r_existing(root, lane)
        if original is not None and original["state"] != "complete":
            raise _ResearchHeld("research_original_held")
        if lane == "causal-brainstorm":
            _r_causal_roots(root)
        ctx = _ResearchRun(cfg, trigger, iso_week, dry_run, root, lane, source_path)
        result = run(cfg=cfg, trigger=trigger, iso_week=iso_week, dry_run=dry_run,
                     root=root, _fabric=ctx)
        if ctx.run is not None and ctx.run["state"] == "active":
            ctx.complete(getattr(ctx, "status", {"mode": "fabric"}))
        return result
    except Exception as exc:
        if ctx is not None:
            try:
                ctx.hold()
            except Exception:
                pass  # durable pending intent remains authoritative
        reason = str(exc) if isinstance(exc, _ResearchHeld) else getattr(exc, "code", "research_original_held")
        raise _ResearchHeld(reason) from None


def _load_config() -> dict:
    """Load config/causal_llm.yml; fail-open with defaults."""
    try:
        import yaml
        return yaml.safe_load(_CONFIG_PATH.read_text(encoding="utf-8")) or {}
    except Exception as exc:  # noqa: BLE001
        log.warning("run_causal_brainstorm: could not load causal_llm.yml (%s); using defaults", exc)
        return {}


# ---------------------------------------------------------------------------
# ISO week helpers (idempotency)
# ---------------------------------------------------------------------------

def _current_iso_week() -> str:
    now = datetime.now(timezone.utc)
    year, week, _ = now.isocalendar()
    return f"{year}-W{week:02d}"


def _already_filed_this_week() -> bool:
    """Return True if ISO-week lock says we already filed this week."""
    try:
        from scripts.causal_ingest_brainstorm import (  # noqa: PLC0415
            _count_filed_this_week,
            _BUDGET_PER_WEEK,
        )
        count = _count_filed_this_week(_MECHANISMS_DIR)
        return count >= _BUDGET_PER_WEEK
    except Exception:  # noqa: BLE001
        return False


# ---------------------------------------------------------------------------
# Lane status file
# ---------------------------------------------------------------------------

def _write_lane_status(
    status: str,
    reason: str,
    root: Path | None = None,
) -> None:
    """Write data/neuralweb/causal_llm_lane.json with current lane status.

    Statuses:
      degraded_pack_only — no auth or gate not passed; pack written, no LLM
      awaiting_phase_a   — auto_loop=False and no operator trigger
      ok                 — full LLM run completed
    """
    base = root or ROOT
    lane_path = base / "data" / "neuralweb" / "causal_llm_lane.json"
    try:
        lane_path.parent.mkdir(parents=True, exist_ok=True)
        doc = {
            "status": status,
            "asof": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "reason": reason,
        }
        if status.startswith("degraded"):
            # Explicit flag so health.py's lobe check treats the artifact as a
            # degraded self-report regardless of status-enum spelling.
            doc["degraded"] = True
        lane_path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    except Exception as exc:  # noqa: BLE001
        log.warning("run_causal_brainstorm: could not write lane status (%s)", exc)


# ---------------------------------------------------------------------------
# Provider builders for scheduled vs operator triggers
# ---------------------------------------------------------------------------

def _build_scheduled_providers(cfg: dict) -> list[dict]:
    """For scheduled trigger: ONLY the CLAUDE_CODE_OAUTH_TOKEN (oauth) provider.

    Operator ruling 2026-07-09 (masterplan §9) overrides the original W-AUTO
    service-key requirement for CHF: scheduled auto-loop runs on the user's
    OAuth identity. The ANTHROPIC_API_KEY and deepseek providers are explicitly
    EXCLUDED from the scheduled path — the operator directed "don't use api
    key, use oauth". A missing/invalid OAuth token degrades to pack-only mode.
    Pool keys are the same oauth class — expanding the oauth slot is compliant.
    """
    _r_native_guard(cfg, ROOT, 'causal-brainstorm')
    from engine import llm_auth  # noqa: PLC0415

    model = cfg.get("model_roles", {}).get("generator", "claude-sonnet-4-6")
    cfg_aug = {**cfg, "oauth_pool_lane": "causal-brainstorm", "usage_lane": "causal-brainstorm"}
    try:
        providers = llm_auth.build_providers(cfg_aug, opus_model=model)
    except Exception as exc:  # noqa: BLE001
        log.warning("run_causal_brainstorm: provider build failed (%s)", exc)
        return []
    return [p for p in providers if p.get("name") == "oauth"]


def _build_operator_providers(cfg: dict, model_override: str | None = None) -> list[dict]:
    """For operator trigger: full waterfall (oauth → anthropic → deepseek)."""
    _r_native_guard(cfg, ROOT, 'causal-brainstorm')
    from engine import llm_auth  # noqa: PLC0415
    model = model_override or cfg.get("model_roles", {}).get("generator", "claude-sonnet-4-6")
    cfg_aug = {**cfg, "oauth_pool_lane": "causal-brainstorm", "usage_lane": "causal-brainstorm"}
    return llm_auth.build_providers(cfg_aug, opus_model=model)


def _build_providers_for_model(
    cfg: dict,
    trigger: str,
    model_role: str,
) -> list[dict]:
    """Build providers selecting the right model from model_roles."""
    _r_native_guard(cfg, ROOT, 'causal-brainstorm')
    model = cfg.get("model_roles", {}).get(model_role)
    if trigger == "scheduled":
        # OAuth only (operator ruling 2026-07-09); swap the model
        providers = _build_scheduled_providers(cfg)
        if providers and model:
            for p in providers:
                p["model"] = model
        return providers
    else:
        return _build_operator_providers(cfg, model_override=model)


# ---------------------------------------------------------------------------
# Numeric field rejection (RF-7 / CHF-R17 skeptic validator)
# ---------------------------------------------------------------------------

_NUMERIC_FIELD_NAMES = frozenset({
    "confidence", "confidence_score", "probability", "prob",
    "score", "weight", "numeric_confidence", "confidence_pct",
})


def _has_numeric_confidence(obj: Any, depth: int = 0) -> bool:
    """Return True if obj (dict or list) contains a numeric confidence-like field."""
    if depth > 8:
        return False
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k.lower() in _NUMERIC_FIELD_NAMES and isinstance(v, (int, float)):
                return True
            if _has_numeric_confidence(v, depth + 1):
                return True
    elif isinstance(obj, list):
        for item in obj:
            if _has_numeric_confidence(item, depth + 1):
                return True
    return False


def _validate_skeptic_findings(findings: list[dict]) -> tuple[list[dict], list[str]]:
    """Validate skeptic output: reject any finding with numeric confidence (RF-7).

    Returns (valid_findings, rejection_reasons).
    """
    valid: list[dict] = []
    rejected: list[str] = []
    for i, f in enumerate(findings):
        if _has_numeric_confidence(f):
            card_id = f.get("card_id", f"finding[{i}]")
            rejected.append(f"{card_id}: contains numeric confidence field (RF-7 violation — skeptic output must be categorical only)")
        else:
            valid.append(f)
    return valid, rejected


# ---------------------------------------------------------------------------
# LLM call helpers (mirror cortex.py client usage + run_status pattern)
# ---------------------------------------------------------------------------

def _llm_call(
    providers: list[dict],
    system: str,
    user: str,
    max_tokens: int,
    context: str,
) -> tuple[str | None, str | None, str | None, dict]:
    """Make one LLM call via the provider waterfall.

    Returns (text, degraded_reason, provider_used, token_counts_dict).
    """
    _r_native_guard({}, ROOT, 'causal-brainstorm')
    from engine import llm_auth  # noqa: PLC0415

    token_counts: dict = {}

    def _call_fn(client, model: str) -> tuple:
        resp = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
            # temperature removed — rejected (400) on opus-4.7+ per Anthropic API
        )
        text = "".join(
            b.text for b in resp.content if getattr(b, "type", "") == "text"
        )
        usage = getattr(resp, "usage", None)
        if usage is not None:
            token_counts["input_tokens"] = getattr(usage, "input_tokens", None)
            token_counts["output_tokens"] = getattr(usage, "output_tokens", None)
        return text, None, resp

    text, reason, provider = llm_auth.make_call(providers, _call_fn, context=context)
    return text, reason, provider, token_counts


# ---------------------------------------------------------------------------
# Pack builder (always fresh — CHF-R8: never reuse a persisted pack)
# ---------------------------------------------------------------------------

def _build_fresh_pack(root: Path, n_cards: int = 3) -> str:
    """Build a fresh brainstorm pack via scripts.causal_brainstorm_pack.build_pack.

    CHF-R8 mandates the pack be rebuilt fresh every run — never reusing a persisted pack.
    The n_cards cap aligns with the weekly budget (CHF-R8: weekly_budget_cards: 3).
    """
    from scripts.causal_brainstorm_pack import build_pack  # noqa: PLC0415
    return build_pack(n_requested=n_cards)


# ---------------------------------------------------------------------------
# Status-only mode (nightly lane refresh — no pack, no LLM)
# ---------------------------------------------------------------------------

def _run_status_only(cfg: dict, root: Path) -> int:
    """Refresh causal_llm_lane.json from config truth. Always returns 0.

    Statuses written:
      armed            — auto_loop=true, waiting for the next scheduled run
      awaiting_phase_a — auto_loop=false (pack-only until operator arms)

    A run outcome (ok / degraded_pack_only) whose asof falls in the CURRENT
    ISO week is preserved while auto_loop is true — the outcome of this week's
    run is more informative than "armed" until the week rolls over.
    """
    auto_loop = bool(cfg.get("auto_loop", False))
    iso_week = _current_iso_week()
    lane_path = root / "data" / "neuralweb" / "causal_llm_lane.json"

    existing: dict = {}
    try:
        existing = json.loads(lane_path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        existing = {}

    if auto_loop and existing.get("status") in ("ok", "degraded_pack_only"):
        try:
            asof = datetime.fromisoformat(str(existing.get("asof")))
            year, week, _ = asof.isocalendar()
            if f"{year}-W{week:02d}" == iso_week:
                print(
                    f"[run_causal_brainstorm] status-only: keeping this week's run outcome "
                    f"(status={existing['status']!r}, asof={existing.get('asof')})"
                )
                return 0
        except Exception:  # noqa: BLE001
            pass  # unparseable asof → stale; fall through to rewrite

    if auto_loop:
        status = "armed"
        reason = (
            "auto_loop armed (operator ruling 2026-07-09); "
            "scheduled OAuth LLM run fires on the Tuesday nightly"
        )
    else:
        status = "awaiting_phase_a"
        reason = "auto_loop disabled — pack-only mode"

    _write_lane_status(status, reason, root=root)
    print(f"[run_causal_brainstorm] status-only: lane refreshed → {status} (iso_week={iso_week})")
    return 0


# ---------------------------------------------------------------------------
# Pack-only mode
# ---------------------------------------------------------------------------

def _run_pack_only_mode(
    cfg: dict,
    reason: str,
    iso_week: str,
    root: Path,
) -> int:
    """Build fresh pack, write to /tmp, update lane status. Always returns 0."""
    print(f"[run_causal_brainstorm] {reason}")
    print("[run_causal_brainstorm] Entering pack-only mode.")

    try:
        n_cards = int(cfg.get("weekly_budget_cards", 3))
        pack_text = _build_fresh_pack(root, n_cards=n_cards)
        pack_path = Path(tempfile.gettempdir()) / f"causal_brainstorm_pack_{iso_week}.txt"
        pack_path.write_text(pack_text, encoding="utf-8")
        print(f"[run_causal_brainstorm] Pack written to: {pack_path}")
    except Exception as exc:  # noqa: BLE001
        print(f"[run_causal_brainstorm] WARNING: pack build failed ({exc}); continuing")

    # Determine lane status: if auto_loop is False this is the expected state
    if "auto_loop disabled" in reason:
        lane_status = "awaiting_phase_a"
    else:
        lane_status = "degraded_pack_only"

    _write_lane_status(lane_status, reason, root=root)
    return 0


# ---------------------------------------------------------------------------
# Full mode: generator → skeptic → compiler → ingest
# ---------------------------------------------------------------------------

def _run_full_mode(
    cfg: dict,
    trigger: str,
    iso_week: str,
    dry_run: bool,
    root: Path,
    _fabric=None,
) -> int:
    """Run the full LLM chain: generator → skeptic (filter) → compiler → ingest.

    Returns 0 always (non-fatal pattern).
    """
    import tempfile  # noqa: PLC0415
    if _fabric is None:
        _r_native_guard(cfg, root, 'causal-brainstorm')
    run_status: dict[str, Any] = {
        "trigger": trigger,
        "iso_week": iso_week,
        "started_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "mode": "fabric" if _fabric is not None else "full",
        "dry_run": dry_run,
        "stages": {},
    }
    if _fabric is not None:
        _fabric.status = run_status

    n_cards = int(cfg.get("weekly_budget_cards", 3))
    model_roles = cfg.get("model_roles", {})
    generator_model = model_roles.get("generator", "claude-sonnet-4-6")
    skeptic_model = model_roles.get("skeptic", "claude-opus-4-8")
    compiler_model = model_roles.get("compiler", "claude-haiku-4-5-20251001")

    # ---- Step 1: Build fresh pack ----
    print("[run_causal_brainstorm] Building fresh brainstorm pack...")
    try:
        pack_text = _build_fresh_pack(root, n_cards=n_cards)
        if _fabric is not None and not _fabric.claim(pack_text):
            _write_lane_status("ok", "original Fabric run already complete; no model or filing effect", root=root)
            return 0
        pack_path = Path(tempfile.gettempdir()) / f"causal_brainstorm_pack_{iso_week}.txt"
        pack_path.write_text(pack_text, encoding="utf-8")
        print(f"[run_causal_brainstorm] Pack written to: {pack_path}")
        run_status["stages"]["pack"] = "ok"
    except _ResearchHeld:
        raise
    except Exception as exc:  # noqa: BLE001
        print(f"[run_causal_brainstorm] ERROR: pack build failed ({exc}); aborting full mode")
        run_status["stages"]["pack"] = f"error: {exc}"
        _write_run_log(run_status, root=root)
        _write_lane_status("degraded_pack_only", f"pack build failed: {exc}", root=root)
        return 0

    # ---- Step 2: GENERATOR — pack → JSON array of candidate cards ----
    print(f"[run_causal_brainstorm] Stage: GENERATOR (model={generator_model})")
    gen_providers = (_build_providers_for_model(cfg, trigger, "generator")
                  if _fabric is None else [])
    gen_system = (
        "You are the CHF brainstorm generator. Read the BRAINSTORM PACK carefully. "
        "Produce EXACTLY the requested number of candidate mechanism cards as a JSON array. "
        "Obey all forbidden-output constraints in the pack. Return JSON array ONLY."
    )
    gen_text, gen_reason, gen_provider, gen_tokens = (
        _llm_call(gen_providers, gen_system, pack_text, max_tokens=4000, context="chf_generator")
        if _fabric is None else _fabric.call("generator", generator_model, gen_system, pack_text,
                                              4000, "chf_generator"))

    run_status["stages"]["generator"] = {
        "model": generator_model,
        "provider": gen_provider,
        "degraded_reason": gen_reason,
        "token_counts": gen_tokens,
    }

    if gen_text is None:
        print(f"[run_causal_brainstorm] WARNING: generator failed (reason={gen_reason}); falling to pack-only")
        _write_run_log(run_status, root=root)
        _write_lane_status("degraded_pack_only", f"generator failed: {gen_reason}", root=root)
        return 0

    # Parse generator output
    try:
        candidate_cards = (_parse_json_array(gen_text) if _fabric is None else _parse_json_array(gen_text, _strict=True))
    except Exception as exc:  # noqa: BLE001
        print(f"[run_causal_brainstorm] WARNING: could not parse generator output ({exc}); falling to pack-only")
        run_status["stages"]["generator"]["parse_error"] = str(exc)
        _write_run_log(run_status, root=root)
        _write_lane_status("degraded_pack_only", f"generator parse error: {exc}", root=root)
        return 0

    print(f"[run_causal_brainstorm] Generator produced {len(candidate_cards)} card(s)")
    run_status["stages"]["generator"]["n_cards_raw"] = len(candidate_cards)

    # ---- Step 3: SKEPTIC — cards → per-card ADVISORY findings (categorical only) ----
    print(f"[run_causal_brainstorm] Stage: SKEPTIC (model={skeptic_model})")
    skeptic_providers = (_build_providers_for_model(cfg, trigger, "skeptic")
                  if _fabric is None else [])

    skeptic_system = (
        "You are the CHF adversarial skeptic. Your job is to find confounders, "
        "colliders, circular definitions, and missing falsifiers in proposed mechanism cards. "
        "\n\nRULES:\n"
        "- Produce ONLY categorical findings per card: NO numeric confidence scores, "
        "probabilities, weights, or any numeric field that represents confidence.\n"
        "- recommendation MUST be one of: ADVISORY_DROP or ADVISORY_KEEP (no other values).\n"
        "- blockers[] must be a list of strings describing specific methodological problems.\n"
        "- Return a JSON array where each element has: "
        "{card_id: str, recommendation: 'ADVISORY_DROP'|'ADVISORY_KEEP', blockers: [str]}.\n"
        "- If a card has a circular definition (outcome causes the cause), or a known "
        "collider as a conditioning variable, or fewer than 2 falsifiers: recommend ADVISORY_DROP.\n"
        "- This is ADVISORY-ONLY input to a mechanical rule-application script. "
        "Your output never directly transitions a card's status."
    )
    skeptic_user = (
        f"Review these {len(candidate_cards)} candidate mechanism cards for confounders, "
        f"colliders, and missing falsifiers. Return JSON array only.\n\n"
        f"CARDS:\n{json.dumps(candidate_cards, indent=2, ensure_ascii=False)}"
    )

    skep_text, skep_reason, skep_provider, skep_tokens = (
        _llm_call(skeptic_providers, skeptic_system, skeptic_user, max_tokens=2000, context="chf_skeptic")
        if _fabric is None else _fabric.call("skeptic", skeptic_model, skeptic_system, skeptic_user,
                                              2000, "chf_skeptic"))

    run_status["stages"]["skeptic"] = {
        "model": skeptic_model,
        "provider": skep_provider,
        "degraded_reason": skep_reason,
        "token_counts": skep_tokens,
    }

    # Mechanically apply skeptic findings (CHF-R17: actor stays 'script')
    surviving_cards = candidate_cards
    if skep_text is not None:
        try:
            findings_raw = (_parse_json_array(skep_text) if _fabric is None else _parse_json_array(skep_text, _strict=True))
            # Validate: reject numeric fields (RF-7)
            valid_findings, rf7_rejections = _validate_skeptic_findings(findings_raw)
            if rf7_rejections:
                print(f"[run_causal_brainstorm] WARNING: skeptic RF-7 violations (numeric confidence): {rf7_rejections}")
                run_status["stages"]["skeptic"]["rf7_rejections"] = rf7_rejections

            # Build drop set from valid ADVISORY_DROP recommendations
            drop_ids: set[str] = set()
            for f in valid_findings:
                if f.get("recommendation") == "ADVISORY_DROP":
                    cid = str(f.get("card_id", ""))
                    if cid:
                        drop_ids.add(cid)
                        blockers = f.get("blockers", [])
                        print(f"[run_causal_brainstorm] ADVISORY_DROP: card_id={cid!r} blockers={blockers}")

            # Drop ADVISORY_DROP cards (mechanical rule-application on advisory output)
            surviving_cards = [
                c for c in candidate_cards
                if str(c.get("mechanism_id", "")) not in drop_ids
            ]
            n_dropped = len(candidate_cards) - len(surviving_cards)
            print(f"[run_causal_brainstorm] Skeptic: {n_dropped} card(s) dropped by ADVISORY_DROP, "
                  f"{len(surviving_cards)} surviving")
            run_status["stages"]["skeptic"]["n_dropped"] = n_dropped
            run_status["stages"]["skeptic"]["n_surviving"] = len(surviving_cards)
            run_status["stages"]["skeptic"]["drop_ids"] = sorted(drop_ids)
        except Exception as exc:  # noqa: BLE001
            print(f"[run_causal_brainstorm] WARNING: skeptic parse failed ({exc}); proceeding with all cards")
            run_status["stages"]["skeptic"]["parse_error"] = str(exc)
    else:
        print(f"[run_causal_brainstorm] WARNING: skeptic unavailable (reason={skep_reason}); all cards survive")

    if not surviving_cards:
        print("[run_causal_brainstorm] All cards dropped by skeptic; nothing to file")
        _write_run_log(run_status, root=root)
        _write_lane_status("ok", "all cards dropped by skeptic; no filing this week", root=root)
        return 0

    # ---- Step 4: COMPILER — surviving cards → strict schema JSON ----
    # Skip if generator output already looks schema-valid (compiler is optional
    # refinement; if it fails we proceed with surviving generator cards)
    print(f"[run_causal_brainstorm] Stage: COMPILER (model={compiler_model})")
    compiler_providers = (_build_providers_for_model(cfg, trigger, "compiler")
                  if _fabric is None else [])

    compiler_system = (
        "You are the CHF schema compiler. Convert the given candidate mechanism cards "
        "to strictly conform to the neuralweb.causal_mechanism_card.v1 schema. "
        "Fix any missing required fields by inference from context. "
        "Do NOT change the meaning, cause, target, or falsifiers. "
        "Return a JSON array only — no prose."
    )
    compiler_user = (
        f"Compile these {len(surviving_cards)} surviving cards to strict schema. "
        f"Return JSON array only.\n\n"
        f"CARDS:\n{json.dumps(surviving_cards, indent=2, ensure_ascii=False)}"
    )

    comp_text, comp_reason, comp_provider, comp_tokens = (
        _llm_call(compiler_providers, compiler_system, compiler_user, max_tokens=3000, context="chf_compiler")
        if _fabric is None else _fabric.call("compiler", compiler_model, compiler_system, compiler_user,
                                              3000, "chf_compiler"))

    run_status["stages"]["compiler"] = {
        "model": compiler_model,
        "provider": comp_provider,
        "degraded_reason": comp_reason,
        "token_counts": comp_tokens,
    }

    final_cards = surviving_cards  # default: use pre-compiler cards
    if comp_text is not None:
        try:
            compiled = (_parse_json_array(comp_text) if _fabric is None else _parse_json_array(comp_text, _strict=True))
            if compiled and len(compiled) >= len(surviving_cards) * 0.5:
                final_cards = compiled
                run_status["stages"]["compiler"]["n_compiled"] = len(compiled)
                print(f"[run_causal_brainstorm] Compiler produced {len(compiled)} compiled card(s)")
            else:
                print(f"[run_causal_brainstorm] WARNING: compiler output too short; using pre-compiler cards")
        except Exception as exc:  # noqa: BLE001
            print(f"[run_causal_brainstorm] WARNING: compiler parse failed ({exc}); using pre-compiler cards")
            run_status["stages"]["compiler"]["parse_error"] = str(exc)
    else:
        print(f"[run_causal_brainstorm] NOTE: compiler unavailable (reason={comp_reason}); using pre-compiler cards")

    # ---- Step 5: Write raw LLM replies to runs log ----
    pack_id = f"chf-{iso_week}-{trigger}"
    _write_run_log(
        run_status,
        root=root,
        pack_id=pack_id,
        raw_replies={
            "generator": gen_text,
            "skeptic": skep_text,
            "compiler": comp_text,
        },
        models={
            "generator": generator_model,
            "skeptic": skeptic_model,
            "compiler": compiler_model,
        },
        trigger=trigger,
    )

    if _fabric is not None:
        receipt = _r_causal_file(_fabric, final_cards, run_status)
        _write_lane_status("ok", f"Fabric run completed; {receipt['n_filed']} card(s) actually filed", root=root)
        return 0

    # ---- Step 6: Write cards to temp inbox and invoke W4 ingest ----
    if not final_cards:
        print("[run_causal_brainstorm] No cards to file after pipeline")
        _write_lane_status("ok", "pipeline produced no cards to file", root=root)
        return 0

    # Write cards to a temp inbox dir for the ingest
    with tempfile.TemporaryDirectory(prefix="chf_inbox_") as tmp_inbox_str:
        tmp_inbox = Path(tmp_inbox_str)
        cards_file = tmp_inbox / "brainstorm_cards.json"
        cards_file.write_text(json.dumps(final_cards, ensure_ascii=False, indent=2), encoding="utf-8")

        try:
            from scripts.causal_ingest_brainstorm import ingest  # noqa: PLC0415
            rc = ingest(
                inbox=tmp_inbox,
                out_dir=root / "data" / "neuralweb",
                dry_run=dry_run,
                model_label=generator_model,
            )
            run_status["stages"]["ingest"] = {"rc": rc, "dry_run": dry_run}
            print(f"[run_causal_brainstorm] Ingest completed (rc={rc}, dry_run={dry_run})")
        except Exception as exc:  # noqa: BLE001
            print(f"[run_causal_brainstorm] WARNING: ingest failed ({exc}); cards not filed")
            run_status["stages"]["ingest"] = {"error": str(exc)}

    # ---- Step 7: Governance event ----
    try:
        from engine.neuralweb import governance  # noqa: PLC0415
        n_filed = len(final_cards)
        governance.append_event(
            "a6_llm_proposed",
            target="causal_mechanisms",
            article=None,
            authored_by="run_causal_brainstorm",
            evidence={
                "pack_id": pack_id,
                "n_cards": n_filed,
                "trigger": trigger,
                "models": {
                    "generator": generator_model,
                    "skeptic": skeptic_model,
                    "compiler": compiler_model,
                },
            },
            root=root,
            note=f"CHF W5 LLM brainstorm batch; iso_week={iso_week}; dry_run={dry_run}",
        )
        print(f"[run_causal_brainstorm] Governance event appended (a6_llm_proposed, n_cards={n_filed})")
    except Exception as exc:  # noqa: BLE001
        print(f"[run_causal_brainstorm] WARNING: governance event failed ({exc}); non-fatal")

    _write_lane_status("ok", f"full run completed; {len(final_cards)} card(s) processed", root=root)
    return 0


# ---------------------------------------------------------------------------
# Run log writer
# ---------------------------------------------------------------------------

def _write_run_log(
    run_status: dict,
    root: Path | None = None,
    pack_id: str | None = None,
    raw_replies: dict | None = None,
    models: dict | None = None,
    trigger: str | None = None,
) -> None:
    """Append one row to data/neuralweb/causal_brainstorm_runs.jsonl."""
    if run_status.get("mode") == "fabric":
        return
    base = root or ROOT
    runs_path = base / "data" / "neuralweb" / "causal_brainstorm_runs.jsonl"
    try:
        runs_path.parent.mkdir(parents=True, exist_ok=True)
        row: dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "pack_id": pack_id,
            "run_status": run_status,
        }
        if models:
            row["models"] = models
        if trigger:
            row["trigger"] = trigger
        if raw_replies:
            # Truncate raw replies to avoid gigantic log rows
            row["raw_replies"] = {
                k: (v[:2000] + "... [truncated]" if v and len(v) > 2000 else v)
                for k, v in raw_replies.items()
            }
        with runs_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, default=str, ensure_ascii=False) + "\n")
    except Exception as exc:  # noqa: BLE001
        log.warning("run_causal_brainstorm: could not write runs log (%s)", exc)


# ---------------------------------------------------------------------------
# JSON array parser (tolerant — mirrors causal_ingest_brainstorm pattern)
# ---------------------------------------------------------------------------

def _parse_json_array(text: str, *, _strict: bool = False) -> list[dict]:
    """Parse LLM output that should be a JSON array. Tries multiple strategies."""
    import json as _json

    text = text.strip()

    # Direct parse
    try:
        obj = (_r_decode(text) if _strict else _json.loads(text))
        if isinstance(obj, list):
            return [c for c in obj if isinstance(c, dict)]
    except _json.JSONDecodeError:
        pass

    # Strip markdown code fences
    for fence in ("```json", "```"):
        if fence in text:
            start = text.find(fence) + len(fence)
            end = text.rfind("```")
            if end > start:
                inner = text[start:end].strip()
                try:
                    obj = (_r_decode(inner) if _strict else _json.loads(inner))
                    if isinstance(obj, list):
                        return [c for c in obj if isinstance(c, dict)]
                except _json.JSONDecodeError:
                    pass

    # Find first '[' and last ']'
    start = text.find("[")
    end = text.rfind("]")
    if start != -1 and end > start:
        try:
            obj = (_r_decode(text[start:end + 1]) if _strict else _json.loads(text[start:end + 1]))
            if isinstance(obj, list):
                return [c for c in obj if isinstance(c, dict)]
        except _json.JSONDecodeError:
            pass

    raise ValueError(f"could not parse JSON array from text of length {len(text)}")


# ---------------------------------------------------------------------------
# Main entrypoint
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    """Main entrypoint. Always returns 0 except unexpected crash."""
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, default=None,
                    help="Repo root (default: inferred from script location)")
    ap.add_argument("--trigger", choices=["operator", "scheduled"], default="operator",
                    help="Trigger mode (default: operator)")
    ap.add_argument("--dry-run", action="store_true", default=False,
                    help="Dry-run: build pack + run LLM chain but do not write cards to disk")
    ap.add_argument("--status-only", action="store_true", default=False,
                    help="Refresh causal_llm_lane.json from config truth (no pack, no LLM) and exit")
    args = ap.parse_args(argv)

    root = (Path(args.root) if args.root else ROOT).absolute()
    trigger = args.trigger
    dry_run = args.dry_run
    iso_week = _current_iso_week()

    # Original selected custody precedes config, week, pack and native auth.
    try:
        original = _r_existing(root, 'causal-brainstorm')
        if original is not None and original["state"] != "complete":
            raise _ResearchHeld("research_original_held")
        cfg = _r_config(root, 'causal_llm.yml', _load_config())
        selected = _r_selection(cfg)["mode"] is not None
        if original is not None and not selected:
            raise _ResearchHeld("research_selection_changed")
    except Exception as exc:
        reason = str(exc) if isinstance(exc, _ResearchHeld) else "research_journal_refused"
        _write_lane_status("degraded_fabric_held", reason, root=root)
        return 0

    # ---- STATUS-ONLY: nightly lane refresh, then exit ----
    if args.status_only:
        return _run_status_only(cfg, root)

    if selected:
        try:
            ingest = _r_causal_roots(root)
        except _ResearchHeld as exc:
            _write_lane_status("degraded_fabric_held", str(exc), root=root)
            return 0

    print(f"[run_causal_brainstorm] trigger={trigger}, iso_week={iso_week}, dry_run={dry_run}")

    # ---- GATE 1: scheduled + auto_loop disabled → pack-only ----
    if trigger == "scheduled":
        auto_loop = cfg.get("auto_loop", False)
        if not auto_loop:
            return _run_pack_only_mode(
                cfg,
                reason="auto_loop disabled — pack-only mode",
                iso_week=iso_week,
                root=root,
            )

    # ---- GATE 2: ISO-week idempotency ----
    if not dry_run and (ingest._count_filed_this_week(root / "data/neuralweb") >= ingest._BUDGET_PER_WEEK
                        if selected else _already_filed_this_week()):
        print(f"[run_causal_brainstorm] ISO-week lock: already filed budget this week ({iso_week}); skip filing, exit 0")
        _write_lane_status("ok", f"already filed this week ({iso_week}); idempotent skip", root=root)
        return 0

    if selected:
        try:
            return _r_selected_run(cfg, trigger, iso_week, dry_run, root,
                                   'causal-brainstorm', __file__, _run_full_mode)
        except _ResearchHeld as exc:
            _write_lane_status("degraded_fabric_held", str(exc), root=root)
            return 0

    # ---- GATE 3: auth availability check ----
    if trigger == "scheduled":
        # Scheduled is OAuth-ONLY (operator ruling 2026-07-09, masterplan §9):
        # CLAUDE_CODE_OAUTH_TOKEN is the scheduled identity; ANTHROPIC_API_KEY
        # and deepseek are excluded from this path.
        providers = _build_scheduled_providers(cfg)
        if not providers:
            return _run_pack_only_mode(
                cfg,
                reason="scheduled trigger requires CLAUDE_CODE_OAUTH_TOKEN (OAuth identity) — not available; pack-only mode",
                iso_week=iso_week,
                root=root,
            )
    else:
        # Operator can use any provider (full waterfall)
        providers = _build_operator_providers(cfg)
        if not providers:
            return _run_pack_only_mode(
                cfg,
                reason="no LLM auth available (operator trigger); pack-only mode",
                iso_week=iso_week,
                root=root,
            )

    # ---- FULL MODE ----
    print("[run_causal_brainstorm] Auth available; running full LLM chain")
    return _run_full_mode(
        cfg=cfg,
        trigger=trigger,
        iso_week=iso_week,
        dry_run=dry_run,
        root=root,
    )


if __name__ == "__main__":
    sys.exit(main())
