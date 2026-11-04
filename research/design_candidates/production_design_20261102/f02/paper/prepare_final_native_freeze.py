#!/usr/bin/env python3
"""Validate and, only with --create, seal the complete F02 native evidence set.

Local files only. No Paper/Browser/network/Git calls and no source-file writes.
The default is a read-only dry run. A successful freeze is evidence packaging,
not visual acceptance, browser proof, a formal RIG receipt or approval.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sys


SCHEMA = "f02.final-native-freeze.v1"
MANIFEST = "manifest.json"
EXPECTED_COUNT = 32
RETAINED_ROLES = {
    "VirtualizedDataInspector", "CountLadder", "LifecycleRail",
    "DecisionRow / VerdictHero",
}
BEFORE = [
    "evidence/macro-before.png", "evidence/company-before.png",
    "evidence/options-before.png", "evidence/editorial-before.png",
    "evidence/paper-metric-before.jpg", "evidence/paper-state-before.jpg",
    "evidence/paper-pattern-before.jpg",
]
FIXTURE = "paper/repairs/fixture-coherence-v1/"
IDENTITY = "paper/repairs/observation-identity-clocks-v1/"
COMPANY = "paper/repairs/company-annual-growth-v2/"
COMPANIONS = "paper/repairs/consumer-companions-v1/"
# Each successive packet has precedence for construction keys, not native IDs.
GROUPS = [
    ("foundation", 6, ["paper/foundation-inputs/boards.json", FIXTURE + "effective-spaced/foundation-boards.json"]),
    ("consumer", 8, ["paper/consumer-inputs/consumer-boards.json", FIXTURE + "effective-spaced/consumer-boards.json", IDENTITY + "effective/consumer-boards.json"]),
    ("mobile", 6, ["paper/mobile-inputs/mobile-state-boards.json", FIXTURE + "effective-spaced/mobile-state-boards.json"]),
    ("supplemental", 4, ["paper/mobile-inputs/supplemental-boards.json", FIXTURE + "effective-spaced/supplemental-boards.json"]),
    ("core", 2, ["paper/core-supplement-inputs.json", FIXTURE + "effective-spaced/core-supplement-inputs.json"]),
    ("fault", 1, ["paper/fault-composition-inputs.json", FIXTURE + "effective-spaced/fault-composition-inputs.json", IDENTITY + "effective/fault-composition-inputs.json"]),
    ("companions", 4, [COMPANIONS + "consumer-companion-inputs.v1.json"]),
]
REQUIRED_FILES = [
    "SYSTEM_CONTRACT.md", "SOURCE_AND_DATA_CONTRACT.md", "INTERACTION_STATES.md",
    "CAPABILITY_LEDGER.md", "PAPER_RETENTION_LEDGER.md", "paper-retention-ledger.json",
    "token-map.json", "fixtures/company-history.json",
    "paper/CURRENT_DESIGN_AUTHORITY.md", "paper/CONTINUATION_GATES_20261103.md",
    "paper/FORMAL_RIG_ROUTE_20261103.md", "paper/NATIVE_BOARD_INDEX.md",
    "paper/native-board-index.json", "paper/native-role-bindings.json",
    "paper/native-predecessor-bindings.json", "paper/writer-continuation-progress.json",
    "paper/role-evidence-input-map.json", "paper/ROLE_EVIDENCE_INPUT_MAP.md",
    "paper/role-evidence-source-receipts.json", "paper/role-evidence-local-validation.json",
    "paper/readme-completion-inputs.json", "paper/reviews/NATIVE_FIRST_PASS_PACKET.md",
    "paper/reviews/native-first-pass-artifacts.json",
    "paper/reviews/NATIVE_REPAIR_REVIEW_PACKET.md", "paper/reviews/NATIVE_AUTHOR_RATIONALE.md",
    "paper/prepare_final_native_freeze.py", "paper/FINAL_NATIVE_FREEZE_README.md",
    FIXTURE + "FIXTURE_CONTRACT.md", FIXTURE + "fixture-contract.json",
    FIXTURE + "arithmetic-validation.json", FIXTURE + "independent-source-validation.json",
    FIXTURE + "packet-manifest.json", FIXTURE + "step-overrides.json",
    FIXTURE + "visible-copy-spacing-overrides.json", FIXTURE + "native-patch-candidates.spaced.json",
    FIXTURE + "effective-spaced/supplemental-wide-clone.json",
    IDENTITY + "README.md", IDENTITY + "source-overrides.v1.json",
    IDENTITY + "minimal-native-identity-patch.v1.json",
    IDENTITY + "native-patch-candidates.cumulative.v2.json", IDENTITY + "validation.json",
    COMPANY + "WRITER_README.md", COMPANY + "company-row-replacements.v2.json",
    COMPANY + "company-caveat-replacements.v2.json", COMPANY + "company-growth-arithmetic.v2.json",
    COMPANY + "company-row-validation.v2.json", COMPANY + "company-source-overrides.v2.json",
    COMPANIONS + "WRITER_README.md", COMPANIONS + "consumer-companion-validation.v1.json",
    "paper/repairs/numeric-alignment-native-patch.json",
    "paper/repairs/numeric-alignment-source-input-override.json",
    "paper/repairs/numeric-alignment-verification.json",
    "paper/repairs/company-zero-clone-native-binding.json",
    "paper/repairs/company-zero-clone-native-verification.json",
    "paper/repairs/controls-variants-native-repairs.json",
    "paper/repairs/options320-header-native-repair.json",
    "paper/repairs/macro-en390-native-verification.json",
    "paper/repairs/writer-controls-spacing-override.json",
    "paper/repairs/writer-controls-icon-stroke-override.json",
]
FINAL_RECEIPTS = {
    "retention": "paper/native-final-retention.json",
    "verification": "paper/native-final-verification.json",
}
GENERATED = ["EXPECTED_BOARDS.json", "CAPTURE_SELECTION.json", "TASK_MANIFEST.json",
             "FREEZE_SOURCE_FILES.txt", "FREEZE_FILES_FOR_GIT.txt"]
HASH = re.compile(r"^[0-9a-f]{64}$")
NODE = re.compile(r"^[A-Za-z0-9]+-\d+$")
TAG = re.compile(r"<(?P<close>/)?(?P<tag>[A-Za-z][\w:.-]*)(?P<attrs>(?:[^<>\"']|\"[^\"]*\"|'[^']*')*)>", re.S)
ID_ATTR = re.compile(r"(?:^|\s)id\s*=\s*[\"']([^\"']+)[\"']")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def json_bytes(value) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def relative_path(value: str) -> str:
    """Normalize observed f02-prefixed records; reject escapes and odd paths."""
    if not isinstance(value, str) or not value or any(c in value for c in "\x00\r\n\\"):
        raise ValueError("expected a nonempty POSIX relative path")
    if value.startswith("f02/"):
        value = value[4:]
    p = PurePosixPath(value)
    if p.is_absolute() or any(part in ("", ".", "..") for part in value.split("/")):
        raise ValueError("absolute, empty, dot and parent path segments are forbidden")
    return p.as_posix()


def parse_time(value: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError("missing timestamp")
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None or result.utcoffset().total_seconds() != 0:
        raise ValueError("timestamp must have an explicit UTC offset")
    return result


def aggregate(members: list[dict]) -> str:
    return sha(b"".join(
        m["path"].encode("utf-8") + b"\x00" + m["sha256"].encode("ascii") + b"\n"
        for m in sorted(members, key=lambda item: item["path"])
    ))


def jsx_elements(text: str) -> tuple[str | None, dict[str, str]]:
    """Read the literal tags/IDs in Paper's static JSX, without executing JSX."""
    stack, spans = [], {}
    first_id = None
    first_tag = True
    for m in TAG.finditer(text):
        tag, attrs = m.group("tag"), m.group("attrs")
        if m.group("close"):
            if not stack or stack[-1][0] != tag:
                raise ValueError("unbalanced literal JSX tags")
            _, start, node_id = stack.pop()
            if node_id:
                if node_id in spans:
                    raise ValueError(f"duplicate export ID {node_id}")
                spans[node_id] = text[start:m.end()]
        else:
            found = ID_ATTR.search(attrs)
            node_id = found.group(1) if found else None
            if first_tag:
                first_id, first_tag = node_id, False
            if attrs.rstrip().endswith("/"):
                if node_id:
                    if node_id in spans:
                        raise ValueError(f"duplicate export ID {node_id}")
                    spans[node_id] = m.group(0)
            else:
                stack.append((tag, m.start(), node_id))
    if stack or first_tag:
        raise ValueError("missing or unclosed literal JSX root")
    return first_id, spans


def comparable(fragment: str) -> str:
    return re.sub(r"\s+", " ", fragment).strip()


def node_values(value):
    if isinstance(value, dict):
        for key, item in value.items():
            if key not in {"html", "text", "reason", "before", "after", "sourceId"}:
                yield from node_values(item)
    elif isinstance(value, list):
        for item in value:
            yield from node_values(item)
    elif isinstance(value, str) and NODE.fullmatch(value):
        yield value


class Packager:
    def __init__(self, args):
        self.args = args
        self.root = Path(args.f02_root).resolve()
        self.files, self.documents, self.errors = {}, {}, []
        self.expected, self.actual, self.exports, self.full_captures = {}, {}, {}, {}
        self.optional_captures, self.excluded_captures, self.receipts = [], [], {}
        self.progress = {}
        self.created_output = None

    def fail(self, code, path, message):
        self.errors.append({"code": code, "path": path, "message": message})

    def check(self, condition, code, path, message):
        if not condition:
            self.fail(code, path, message)
        return bool(condition)

    def source(self, rel, category="source"):
        try:
            rel = relative_path(rel)
            if rel in self.files:
                self.files[rel]["categories"].add(category)
                return self.files[rel]["data"]
            path = self.root / rel
            cursor = self.root
            for part in PurePosixPath(rel).parts:
                cursor /= part
                if cursor.is_symlink():
                    raise ValueError("symlinks are forbidden in freeze sources")
            data = path.read_bytes()
            if not data:
                raise ValueError("empty source file")
            self.files[rel] = {"data": data, "sha256": sha(data), "bytes": len(data), "categories": {category}}
            return data
        except (OSError, ValueError) as exc:
            self.fail("SOURCE_UNAVAILABLE", str(rel), str(exc))
            return None

    def read_json(self, rel, category="source"):
        normalized = relative_path(rel)
        if normalized in self.documents:
            self.source(normalized, category)
            return self.documents[normalized]
        data = self.source(normalized, category)
        if data is None:
            return {}
        try:
            result = json.loads(data)
            if not isinstance(result, dict):
                raise ValueError("expected a JSON object")
            self.documents[normalized] = result
            return result
        except (ValueError, UnicodeError) as exc:
            self.fail("INVALID_JSON", normalized, str(exc))
            return {}

    def time(self, value, where):
        try:
            return parse_time(value)
        except (ValueError, TypeError) as exc:
            self.fail("INVALID_UTC", where, str(exc))
            return None

    def derive_expected(self):
        effective_packets = []
        for group, count, paths in GROUPS:
            previous_keys, selected = None, []
            for path in paths:
                packet = self.read_json(path, "construction-input")
                boards = packet.get("boards", [])
                keys = [b.get("key") for b in boards]
                self.check(len(boards) == count and len(set(keys)) == count and all(keys),
                           "INPUT_BOARD_COUNT", path, f"{group} must contain exactly {count} distinct board keys")
                if previous_keys is not None:
                    self.check(set(keys) == previous_keys, "INPUT_KEY_DRIFT", path, "overlay changed its canonical board-key set")
                previous_keys, selected = set(keys), boards
            effective_packets.append((paths[-1], self.documents.get(paths[-1], {})))
            for board in selected:
                key = board.get("key")
                if not key:
                    continue
                self.check(key not in self.expected, "DUPLICATE_EXPECTED_BOARD", paths[-1], str(key))
                steps = [s.get("key") for s in board.get("steps", [])]
                self.check(all(steps) and len(steps) == len(set(steps)), "INPUT_STEP_KEYS", paths[-1], f"invalid or duplicate step key on {key}")
                self.expected[key] = {"key": key, "group": group, "input_packets": list(paths),
                                      "expected_step_keys": set(s for s in steps if s),
                                      "planned_width": board.get("width")}
        # This is the single observed clone added to the seven canonical groups.
        if "metrics" in self.expected:
            self.expected["metrics-light"] = {
                "key": "metrics-light", "group": "metrics-light-clone", "clone_of_key": "metrics",
                "input_packets": list(self.expected["metrics"]["input_packets"]),
                "expected_step_keys": set(self.expected["metrics"]["expected_step_keys"]),
                "planned_width": self.expected["metrics"]["planned_width"],
            }
        completion = self.read_json("paper/readme-completion-inputs.json", "construction-input")
        self.check(completion.get("observed_board_count") == EXPECTED_COUNT, "DIRECTORY_NOT_FINAL",
                   "paper/readme-completion-inputs.json", "regenerate directory input from the final 32 observed boards")
        effective_packets.append(("paper/readme-completion-inputs.json", completion))
        for path, packet in effective_packets:
            for append in packet.get("append_to_existing", []):
                key = append.get("target_board_key") or append.get("board_key")
                if self.check(key in self.expected, "APPEND_TARGET_UNKNOWN", path, str(key)):
                    self.expected[key]["expected_step_keys"].update(s["key"] for s in append.get("steps", []))
                    self.expected[key]["input_packets"].append(path)
            for replacement in packet.get("replacements", []):
                key, step = replacement.get("board_key"), replacement.get("step_key")
                if self.check(key in self.expected, "REPLACEMENT_TARGET_UNKNOWN", path, str(key)):
                    self.expected[key]["expected_step_keys"].add(step)
        # Only construction keys are read here. IDs in prepared repair inputs are
        # historical targets, never sources of current native identity.
        for path in [COMPANY + "company-row-replacements.v2.json", COMPANY + "company-caveat-replacements.v2.json"]:
            for op in self.read_json(path, "source-repair").get("operations", []):
                key, step = op.get("board_key"), op.get("step_key")
                if self.check(key in self.expected and bool(step), "REPAIR_TARGET_UNKNOWN", path, f"{key}/{step}"):
                    self.expected[key]["expected_step_keys"].add(step)
                    self.expected[key]["input_packets"].append(path)
        self.check(len(self.expected) == EXPECTED_COUNT, "EXPECTED_UNION_COUNT", "construction-inputs", "canonical union must contain exactly 32 boards")

    def indexed(self, records, key, where):
        result = {}
        for record in records:
            identity = record.get(key)
            if self.check(identity and identity not in result, "DUPLICATE_OR_MISSING_KEY", where, str(identity)):
                result[identity] = record
        return result

    def validate_operations(self, progress, index):
        path = "paper/writer-continuation-progress.json"
        self.check(progress.get("unresolved_effects") == [], "UNRESOLVED_OPERATIONS", path, "unresolved_effects must be an explicit empty list")
        self.check(index.get("unresolved_operations") == [], "UNRESOLVED_OPERATIONS", "paper/native-board-index.json", "unresolved_operations must be empty")
        operations = progress.get("operations", [])
        self.check(bool(operations), "OPERATION_HISTORY_MISSING", path, "observed operation history is required")
        seen = set()
        for op in operations:
            identity = op.get("id")
            self.check(identity and identity not in seen, "DUPLICATE_OPERATION", path, str(identity))
            seen.add(identity)
            state = op.get("state") or op.get("response", {}).get("state")
            self.check(state == "APPLIED_RESPONSE_OBSERVED", "UNRESOLVED_OPERATION", path, f"{identity}: {state}")
            result = op.get("result", op.get("response", {}).get("result", {}))
            self.check(not result.get("isError", False), "OPERATION_ERROR", path, str(identity))
        self.check(index.get("operation_count") == len(operations), "STALE_REGISTRY", "paper/native-board-index.json", "operation count differs from writer checkpoint")
        progress_data = self.files.get(path)
        self.check(progress_data and index.get("checkpoint_sha256") == progress_data["sha256"], "STALE_REGISTRY", "paper/native-board-index.json", "checkpoint SHA256 differs from current writer file")
        self.check(index.get("source_checkpoint") == path, "REGISTRY_SOURCE", "paper/native-board-index.json", "registry must bind writer-continuation-progress.json")

    def checked_artifact(self, receipt, category, expected_suffix):
        if not isinstance(receipt, dict):
            self.fail("ARTIFACT_RECEIPT_MISSING", category, "expected path, bytes and SHA256")
            return None, None
        try:
            path = relative_path(receipt.get("path"))
        except ValueError as exc:
            self.fail("ARTIFACT_PATH", category, str(exc))
            return None, None
        self.check(Path(path).suffix.lower() in expected_suffix, "ARTIFACT_FORMAT", path, str(expected_suffix))
        data = self.source(path, category)
        if data is not None:
            self.check(receipt.get("bytes") == len(data), "ARTIFACT_LENGTH", path, "byte length differs from native registry")
            self.check(receipt.get("sha256") == sha(data), "ARTIFACT_HASH", path, "SHA256 differs from native registry")
        return path, data

    @staticmethod
    def complete_scope(capture):
        state = str(capture.get("capture_state", "")).upper()
        tokens = set(re.findall(r"[A-Z0-9]+", state))
        bad = {"INCOMPLETE", "PARTIAL", "PENDING", "UNFINISHED", "INTERIM"}
        if tokens & bad or "IN_PROGRESS" in state or "NOT_COMPLETE" in state:
            return False
        scope = capture.get("capture_scope", capture.get("scope", {}))
        return (isinstance(scope, dict) and scope.get("complete") is True) or bool(tokens & {"FINAL", "COMPLETE"})

    def capture_common(self, capture, board, screenshot, jsx, where):
        self.check(capture.get("boardId") == board["id"] and capture.get("boardKey") == board["key"], "STALE_CAPTURE_ID", where, "capture board binding differs from writer")
        for field, path in [("screenshot", screenshot), ("jsx", jsx)]:
            try:
                observed_path = relative_path(capture.get(field))
            except ValueError:
                observed_path = None
            self.check(observed_path == path, "CAPTURE_PATH", where, f"{field} does not bind selected artifact")
            if path in self.files:
                self.check(capture.get(field + "_sha256") == self.files[path]["sha256"], "CAPTURE_HASH", where, f"{field} hash does not bind selected bytes")
                if field + "_bytes" in capture:
                    self.check(capture[field + "_bytes"] == self.files[path]["bytes"], "CAPTURE_LENGTH", where, field)
        self.time(capture.get("captured_at"), where)
        through = capture.get("operations_through")
        self.check(isinstance(through, int) and not isinstance(through, bool) and 0 <= through <= len(self.progress.get("operations", [])), "CAPTURE_OPERATION_BOUNDARY", where, "operations_through must identify a confirmed checkpoint")

    def validate_boards(self, progress, index):
        writer = self.indexed(progress.get("boards", []), "key", "writer boards")
        registry = self.indexed(index.get("boards", []), "key", "registry boards")
        for label, mapping in [("writer", writer), ("registry", registry)]:
            for key in sorted(set(self.expected) - set(mapping)):
                self.fail("EXPECTED_BOARD_MISSING", label, key)
            for key in sorted(set(mapping) - set(self.expected)):
                self.fail("UNEXPECTED_BOARD", label, key)
        roots = [b.get("id") for b in writer.values()]
        self.check(len(set(roots)) == len(roots) and all(roots), "DUPLICATE_BOARD_ID", "writer boards", "actual roots must be unique and nonempty")
        for key in sorted(set(self.expected) & set(writer) & set(registry)):
            board, row = writer[key], registry[key]
            self.actual[key] = board
            where = f"{key} / {board.get('id')}"
            self.check(row.get("board_id") == board.get("id") and row.get("page_id") == board.get("pageId") and row.get("file_id") == progress.get("fileId"), "STALE_BOARD_BINDING", where, "registry identity differs from writer")
            steps = board.get("steps", {})
            self.check(isinstance(steps, dict) and all(steps.values()), "STEP_BINDING_MISSING", where, "all writer step bindings must resolve")
            self.check(row.get("step_ids") == steps, "STALE_STEP_BINDING", where, "registry step map differs from writer")
            missing = self.expected[key]["expected_step_keys"] - set(steps)
            self.check(not missing, "EXPECTED_STEPS_MISSING", where, ", ".join(sorted(missing)))
            self.check(len(set(steps.values())) == len(steps), "ALIASED_STEP_BINDING", where, "distinct construction steps share one native ID")
            jpg, jpg_data = self.checked_artifact(row.get("screenshot"), "final-native-image", {".jpg", ".jpeg"})
            jsx, jsx_data = self.checked_artifact(row.get("jsx"), "final-native-export", {".jsx"})
            if jpg:
                self.check(Path(jpg).stem == key and "--" not in Path(jpg).stem, "NOT_FULL_BOARD_IMAGE", jpg, "final image must use the bare board key")
            if jsx:
                self.check(Path(jsx).stem == key and "--" not in Path(jsx).stem, "NOT_FULL_BOARD_EXPORT", jsx, "final export must use the bare board key")
            if jpg_data:
                self.check(jpg_data.startswith(b"\xff\xd8") and jpg_data.endswith(b"\xff\xd9"), "INVALID_JPEG", jpg, "JPEG start/end markers are required")
            if jsx_data:
                try:
                    root_id, elements = jsx_elements(jsx_data.decode("utf-8"))
                    self.exports[key] = elements
                    self.check(root_id == board.get("id"), "STALE_EXPORT_ROOT", jsx, f"root {root_id!r} differs from actual board {board.get('id')!r}")
                    absent = [step for step, node in steps.items() if node not in elements]
                    self.check(not absent, "STALE_EXPORT_STEPS", jsx, ", ".join(absent))
                except (UnicodeError, ValueError) as exc:
                    self.fail("INVALID_JSX_EXPORT", jsx, str(exc))
            captures = [c for c in progress.get("captures", []) if c.get("key") == key and c.get("boardKey") == key]
            if not self.check(bool(captures), "FINAL_CAPTURE_RECEIPT_MISSING", where, "writer must record a complete full-board capture"):
                continue
            capture = captures[-1]
            self.full_captures[key] = capture
            self.check(row.get("latest_writer_capture") == capture, "STALE_CAPTURE_REGISTRY", where, "registry latest capture differs from writer")
            self.check(capture.get("nodeId") == board.get("id") and capture.get("stepKey") is None, "NOT_FULL_BOARD_CAPTURE", where, "capture must target the actual board root")
            self.check(self.complete_scope(capture) and "BEFORE" not in str(capture.get("capture_state", "")).upper(), "CAPTURE_NOT_COMPLETE", where, "recorded scope must explicitly be complete/final")
            self.capture_common(capture, board, jpg, jsx, where)
        if "metrics-light" in writer and "metrics" in writer:
            self.check(writer["metrics-light"].get("clone_source") == writer["metrics"]["id"], "CLONE_LINEAGE", "metrics-light", "clone_source must bind the observed metrics root")
        # Reject captures taken before a later mutation of their board. Finish is
        # a non-rendering handoff operation; no other operation is ignored.
        node_owners = {}
        for key, board in writer.items():
            for node in set(self.exports.get(key, {})) | {board.get("id")} | set(board.get("steps", {}).values()):
                node_owners.setdefault(node, set()).add(key)
        last_touch = {key: 0 for key in writer}
        for position, op in enumerate(progress.get("operations", []), 1):
            if op.get("tool") == "finish_working_on_nodes":
                continue
            # Duplication reads the source node. Its returned new IDs and any
            # explicit insertion parent identify the affected destination.
            arguments = op.get("arguments", {})
            nodes = set(node_values(arguments)) if op.get("tool") != "duplicate_nodes" else set(node_values({k: v for k, v in arguments.items() if k in {"parentNodeId", "targetNodeId"}}))
            result = op.get("result", op.get("response", {}).get("result", {}))
            nodes.update(node_values(result))
            for block in result.get("content", []):
                if block.get("type") == "text":
                    try:
                        nodes.update(node_values(json.loads(block["text"])))
                    except (ValueError, TypeError):
                        pass
            touched = set().union(*(node_owners.get(node, set()) for node in nodes)) if nodes else set()
            # Historical packets use an object; later observed repairs may use a
            # source-reference string with an explicit, separately bound board.
            # Preserve conservative all-board invalidation when neither resolves.
            source_input = op.get("source_input")
            source_key = source_input.get("key") if isinstance(source_input, dict) else op.get("board_key")
            if source_key in writer:
                touched.add(source_key)
            # Unknown affected scope cannot silently make a capture current.
            if not touched:
                touched = set(writer)
            for key in touched:
                last_touch[key] = position
        for key, capture in self.full_captures.items():
            through = capture.get("operations_through")
            self.check(isinstance(through, int) and through >= last_touch[key], "CAPTURE_PRECEDES_MUTATION", key, f"capture through {through}; last potentially affecting mutation {last_touch[key]}")

    def validate_roles_and_predecessors(self):
        roles = self.read_json("paper/native-role-bindings.json", "native-binding")
        role_map = self.read_json("paper/role-evidence-input-map.json", "source-contract")
        role_rows = self.indexed(roles.get("roles", []), "role", "native role bindings")
        source_rows = self.indexed(role_map.get("roles", []), "role", "role input map")
        self.check(set(role_rows) == set(source_rows) and len(role_rows) == 21, "ROLE_SET", "paper/native-role-bindings.json", "all 21 contract roles must be present")
        self.check(roles.get("input_map_sha256") == self.files.get("paper/role-evidence-input-map.json", {}).get("sha256"), "STALE_ROLE_MAP", "paper/native-role-bindings.json", "input map SHA256 mismatch")
        self.check(roles.get("unresolved_bindings") == [] and roles.get("summary", {}).get("unresolved_binding_count") == 0, "UNRESOLVED_PORTABLE_BINDINGS", "paper/native-role-bindings.json", "all portable board/step/export bindings must resolve")
        self.check(set(roles.get("summary", {}).get("retained_unqualified_roles", [])) == RETAINED_ROLES, "RETAINED_ROLE_BOUNDARY", "paper/native-role-bindings.json", "only the four declared retained domain/source roles remain unqualified")

        def evidence(record, where):
            key = record.get("board_key")
            board = self.actual.get(key)
            if not self.check(board is not None, "ROLE_BOARD_MISSING", where, str(key)):
                return
            steps = record.get("step_keys", [])
            expected = {step: board.get("steps", {}).get(step) for step in steps}
            self.check(record.get("binding_status") == "ACTUAL_IDS_PRESENT_IN_EXPORT" and not record.get("unbound_steps") and not record.get("steps_not_in_current_export"), "UNRESOLVED_PORTABLE_BINDING", where, str(key))
            self.check(record.get("native_board_id") == board["id"] and record.get("native_page_id") == board["pageId"], "STALE_ROLE_BOARD", where, str(key))
            self.check(record.get("native_step_ids") == expected and all(expected.values()), "STALE_ROLE_STEP", where, str(key))
            self.check(all(node in self.exports.get(key, {}) for node in expected.values()), "ROLE_EXPORT_MISMATCH", where, str(key))

        for name, role in role_rows.items():
            wanted = "RETAINED_UNQUALIFIED" if name in RETAINED_ROLES else "BOUND_TO_OBSERVED_CANDIDATE_IDS"
            self.check(role.get("native_projection_status") == wanted, "ROLE_PROJECTION_STATUS", name, wanted)
            source_variants = {v.get("variant"): v for v in source_rows.get(name, {}).get("variants", [])}
            variants = {v.get("variant"): v for v in role.get("variants", [])}
            self.check(set(variants) == set(source_variants), "ROLE_VARIANT_SET", name, "native map must retain every source variant")
            for label, variant in variants.items():
                signature = lambda refs: [(r.get("board_key"), tuple(r.get("step_keys", []))) for r in refs]
                self.check(signature(variant.get("evidence", [])) == signature(source_variants.get(label, {}).get("evidence", [])), "ROLE_EVIDENCE_SET", name, str(label))
                for ref in variant.get("evidence", []):
                    evidence(ref, f"{name} / {label}")
        cross_signature = lambda items: [(item.get("topic"), [(ref.get("board_key"), tuple(ref.get("step_keys", []))) for ref in item.get("refs", [])]) for item in items]
        self.check(cross_signature(roles.get("cross_cutting_evidence", [])) == cross_signature(role_map.get("cross_cutting_evidence", [])), "CROSS_CUTTING_BINDING_SET", "paper/native-role-bindings.json", "cross-cutting source evidence may not be omitted")
        for item in roles.get("cross_cutting_evidence", []):
            for ref in item.get("refs", []):
                evidence(ref, item.get("topic", "cross-cutting"))
        predecessors = self.read_json("paper/native-predecessor-bindings.json", "native-binding")
        ledger = self.read_json("paper-retention-ledger.json", "retention-contract")
        identity = lambda row: (row.get("file_id"), row.get("page_id"), row.get("board_id"))
        old = {identity(row): row for row in ledger.get("rows", [])}
        current = {identity(row): row for row in predecessors.get("rows", [])}
        self.check(len(old) == len(current) == len(predecessors.get("rows", [])) == 67 and set(old) == set(current), "PREDECESSOR_SET", "paper/native-predecessor-bindings.json", "all 67 original identities must remain represented once")
        for key, row in current.items():
            self.check(row.get("disposition") == old.get(key, {}).get("disposition") and row.get("original_action") == "RETAIN_IN_PLACE_NO_F02_MUTATION", "PREDECESSOR_DISPOSITION", str(key), "original retention/disposition changed")
            if row.get("disposition") == "RETAIN":
                self.check(identity(row.get("retained_successor") or {}) == key, "RETAINED_IDENTITY", str(key), "retained identity must stay at its recorded location")
            for companion in row.get("candidate_companions", []):
                board = self.actual.get(companion.get("board_key"), {})
                self.check(companion.get("status") == "OBSERVED_CANDIDATE_COMPANION" and companion.get("board_id") == board.get("id") and companion.get("page_id") == board.get("pageId") and companion.get("file_id") == self.progress.get("fileId"), "STALE_PREDECESSOR_COMPANION", str(key), str(companion.get("board_key")))

    def select_optional_captures(self):
        requested = set(self.args.section_capture)
        found = set()
        # Only the latest record for a given capture key can be selected.
        captures = {c.get("key"): c for c in self.progress.get("captures", [])}
        for key, capture in sorted(captures.items()):
            if key in self.expected:
                continue
            board_key, step = capture.get("boardKey"), capture.get("stepKey")
            board = self.actual.get(board_key)
            state = str(capture.get("capture_state", "")).upper()
            scope = capture.get("capture_scope", capture.get("scope", {}))
            kind = scope.get("kind") if isinstance(scope, dict) else None
            width_board = str(board_key).startswith("width-") or board_key == "macro-docked-1280"
            closed = kind in {"full_closed_table", "closed_table_width"} or ("CLOSED" in state and ("TABLE" in state or "COMPARISON" in state))
            full_width = width_board and closed and self.complete_scope(capture)
            final_section = bool(step) and self.complete_scope(capture) and not any(word in state for word in ["BEFORE", "INTERIM", "IN_PROGRESS"])
            classification = "closed-table-width" if full_width else "final-section" if final_section else None
            selected = key in requested or (classification == "final-section" and self.args.include_final_sections) or (classification == "closed-table-width" and self.args.include_closed_table_width)
            if not selected:
                self.excluded_captures.append({"key": key, "recorded_scope": capture.get("capture_state"), "reason": "not selected" if classification else "scope is neither final section nor complete closed-table width evidence"})
                continue
            found.add(key)
            if not self.check(classification is not None and board is not None, "INELIGIBLE_OPTIONAL_CAPTURE", str(key), "explicit selection cannot promote an interim/partial capture"):
                continue
            try:
                jpg, jsx = relative_path(capture["screenshot"]), relative_path(capture["jsx"])
            except (ValueError, KeyError) as exc:
                self.fail("OPTIONAL_CAPTURE_PATH", str(key), str(exc))
                continue
            image_data, export_data = self.source(jpg, classification), self.source(jsx, classification)
            self.capture_common(capture, board, jpg, jsx, str(key))
            if image_data:
                self.check(image_data.startswith(b"\xff\xd8") and image_data.endswith(b"\xff\xd9"), "INVALID_JPEG", jpg, "JPEG start/end markers are required")
            if export_data:
                try:
                    root, elements = jsx_elements(export_data.decode("utf-8"))
                    self.check(root == capture.get("nodeId"), "OPTIONAL_CAPTURE_ROOT", jsx, "export root differs from capture node")
                    expected_node = board.get("steps", {}).get(step) if step else board["id"]
                    self.check(capture.get("nodeId") == expected_node, "STALE_OPTIONAL_BINDING", jsx, "captured step/root is no longer current")
                    if classification == "final-section":
                        current = self.exports.get(board_key, {}).get(expected_node)
                        self.check(current is not None and comparable(elements.get(expected_node, "")) == comparable(current), "STALE_SECTION_CONTENT", jsx, "section differs from the final full export")
                    else:
                        required = [s for s in self.expected[board_key]["expected_step_keys"] if re.fullmatch(r"sector-\d+", s)]
                        self.check(len(required) == 10, "CLOSED_TABLE_ROWS", jsx, "full width evidence must include all ten sector rows")
                        for s in required + [s for s in ("table", "table-header", "table-label") if s in board.get("steps", {})]:
                            node = board["steps"].get(s)
                            current = self.exports.get(board_key, {}).get(node)
                            self.check(node in elements and current is not None and comparable(elements.get(node, "")) == comparable(current), "STALE_CLOSED_TABLE_CONTENT", jsx, s)
                except (UnicodeError, ValueError) as exc:
                    self.fail("INVALID_JSX_EXPORT", jsx, str(exc))
            self.optional_captures.append({"classification": classification, "capture": capture,
                                           "not_a_completed_full_screen": True})
        for key in sorted(requested - found):
            self.fail("OPTIONAL_CAPTURE_NOT_FOUND", key, "no recorded optional writer capture with this key")

    def final_receipts(self):
        for kind, default in FINAL_RECEIPTS.items():
            supplied = getattr(self.args, kind + "_receipt")
            path = supplied or default
            if not supplied and not (self.root / default).is_file():
                self.receipts[kind] = {"status": "NOT_SUPPLIED", "path": None}
                if self.args.require_final_receipts:
                    self.fail("FINAL_RECEIPT_MISSING", default, "--require-final-receipts was selected")
                continue
            path = relative_path(path)
            receipt = self.read_json(path, "final-" + kind + "-receipt")
            self.receipts[kind] = {"status": "SUPPLIED", "path": path, "receipt_status": receipt.get("status")}
            observed = self.time(receipt.get("observed_at", receipt.get("recorded_at")), path)
            operation_times = []
            for op in self.progress.get("operations", []):
                value = op.get("completed_at", op.get("started_at"))
                if value:
                    try:
                        operation_times.append(parse_time(value))
                    except (ValueError, TypeError):
                        self.fail("INVALID_UTC", str(op.get("id")), "operation timestamp is not explicit UTC")
            self.check(observed is not None and (not operation_times or observed >= max(operation_times)), "STALE_FINAL_RECEIPT", path, "receipt must follow the current recorded operations")
            self.check(bool(receipt.get("schema_version") or receipt.get("schema")), "RECEIPT_SCHEMA", path, "schema identity is required")
            status = str(receipt.get("status", ""))
            self.check(bool(status) and not re.search(r"\b(?:PENDING|INCOMPLETE|FAILED|BLOCKED)\b", status.replace("_", " ").upper()), "RECEIPT_INCOMPLETE", path, status)
            if "checkpoint_sha256" in receipt:
                self.check(receipt["checkpoint_sha256"] == self.files["paper/writer-continuation-progress.json"]["sha256"], "STALE_FINAL_RECEIPT", path, "checkpoint hash differs")
            if kind == "retention":
                expected = self.documents["paper/native-predecessor-bindings.json"].get("rows", [])
                original_identity = lambda row: (row.get("file_id", row.get("file")), row.get("page_id", row.get("page")), row.get("board_id", row.get("id")))
                counts = receipt.get("counts", {})
                rows = receipt.get("originals_present", receipt.get("originals", []))
                self.check(receipt.get("originals_expected", counts.get("originals_expected")) == 67 and len(rows) == 67 and {original_identity(r) for r in rows} == {original_identity(r) for r in expected} and all(r.get("present", True) is True and r.get("location_matches", True) is True for r in rows), "RETENTION_READBACK_SET", path, "all 67 originals must match recorded file/page/board identities")
                missing = receipt.get("originals_missing", [r for r in rows if r.get("present", True) is not True])
                self.check(missing == [] and receipt.get("uncertain_operations") == [], "RETENTION_UNRESOLVED", path, "missing originals and uncertain operations must be empty")
                tokens = receipt.get("shared_tokens", receipt.get("tokens", {}))
                self.check(tokens.get("expected_count") == tokens.get("observed_count") == 20 and tokens.get("original_hash", tokens.get("expected_content_hash")) == tokens.get("observed_hash", tokens.get("observed_content_hash")) == "356191c3" and tokens.get("all_original_names_values_match", True) is True, "RETENTION_TOKEN_DRIFT", path, "shared token count/hash does not match the retained baseline")
                scope_check = receipt.get("owned_mutation_scope_check", receipt.get("operation_scope_audit"))
                # Operation IDs may legitimately contain specimen state names
                # (for example "save-pending"). Judge the audit's verdict, then
                # validate every operation's custody booleans and exact set below.
                scope_verdict = {key: scope_check.get(key) for key in ("status", "state", "verdict") if key in scope_check} if isinstance(scope_check, dict) else scope_check
                scope_text = json.dumps(scope_verdict, ensure_ascii=False).replace("_", " ").upper()
                scope_ok = bool(scope_check) and not re.search(r"\b(?:FAIL|FAILED|PENDING|UNKNOWN|VIOLATED)\b", scope_text)
                if isinstance(scope_check, dict):
                    scope_ok = scope_ok and not scope_check.get("violations") and scope_check.get("passed", True) is not False and scope_check.get("ok", True) is not False
                    if "operations" in scope_check:
                        scope_operations = scope_check["operations"]
                        scope_ok = scope_ok and len(scope_operations) == len(self.progress.get("operations", [])) and {o.get("id") for o in scope_operations} == {o.get("id") for o in self.progress.get("operations", [])} and all(o.get("all_targets_previously_created_by_F02") is True and o.get("targets_original_board") is False for o in scope_operations)
                self.check(scope_ok, "RETENTION_SCOPE_CHECK", path, "owned mutation scope check is missing or unresolved")
            else:
                self.check(set(receipt.get("expected_board_keys", [])) == set(self.expected) == set(receipt.get("observed_board_keys", [])), "VERIFICATION_BOARD_SET", path, "verification must enumerate exactly the expected 32 boards")
                operations = receipt.get("operations", {})
                uncertain = receipt.get("uncertain_operations", operations.get("uncertain"))
                confirmed = receipt.get("operations_confirmed", operations.get("confirmed"))
                self.check(uncertain == [] or uncertain == 0, "VERIFICATION_UNCERTAIN", path, "uncertain operations must be explicitly empty/zero")
                self.check(confirmed == len(self.progress.get("operations", [])) or (isinstance(confirmed, list) and set(confirmed) == {op.get("id") for op in self.progress.get("operations", [])}), "VERIFICATION_OPERATION_COUNT", path, "confirmed operations must match the writer history")
                unresolved = receipt.get("portable_role_bindings_unresolved_count", receipt.get("portable_role_bindings", {}).get("unresolved_count"))
                self.check(unresolved == 0, "VERIFICATION_ROLE_BINDINGS", path, "portable role binding unresolved count must be zero")
                rows = receipt.get("boards", receipt.get("per_board", []))
                if isinstance(rows, dict):
                    rows = [dict(value, key=key) for key, value in rows.items()]
                by_key = self.indexed(rows, "key", path)
                self.check(set(by_key) == set(self.expected), "VERIFICATION_ARTIFACT_SET", path, "per-board receipt must cover all 32 boards")
                for key, row in by_key.items():
                    capture = self.full_captures.get(key, {})
                    for field in ("screenshot", "jsx"):
                        value = row.get(field, {})
                        supplied_path = value.get("path") if isinstance(value, dict) else value
                        supplied_hash = value.get("sha256") if isinstance(value, dict) else row.get(field + "_sha256")
                        try:
                            same = relative_path(supplied_path) == relative_path(capture.get(field))
                        except ValueError:
                            same = False
                        self.check(same and supplied_hash == capture.get(field + "_sha256"), "VERIFICATION_ARTIFACT_HASH", path, f"{key}/{field}")
        for path in self.args.repair_receipt:
            normalized = relative_path(path)
            self.check(normalized.startswith("paper/repairs/") and "/company-annual-growth-v1/" not in normalized,
                       "REPAIR_RECEIPT_SCOPE", normalized, "only current paper/repairs receipts may be added")
            self.read_json(normalized, "additional-repair-receipt")

    def task_manifest(self):
        path = "paper/reviews/NATIVE_FIRST_PASS_PACKET.md"
        data = self.files.get(path, {}).get("data", b"").decode("utf-8")
        job = re.search(r"## User / business job\n(.*?)\n## Exact evidence boundary", data, re.S)
        table = re.search(r"## Capability / task manifest\n(.*?)\n## Required critic output", data, re.S)
        rows = []
        if table:
            for line in table.group(1).splitlines():
                columns = [v.strip() for v in line.strip().strip("|").split("|")]
                if columns and re.match(r"T\d{2}\b", columns[0]):
                    rows.append({"task": columns[0], "critical": columns[1], "required_retained_capability": columns[2]})
        self.check(bool(job) and [r["task"].split()[0] for r in rows] == [f"T{i:02d}" for i in range(1, 13)], "TASK_MANIFEST", path, "unchanged user job and T01–T12 must be extractable")
        return {"schema": "f02.native-review-task-manifest.v1", "source": path,
                "source_sha256": self.files.get(path, {}).get("sha256"),
                "user_business_job": job.group(1).strip() if job else None, "tasks": rows}

    def run_validation(self):
        self.derive_expected()
        for path in REQUIRED_FILES:
            self.source(path, "contract-or-repair-evidence")
        original_manifest = self.read_json("paper/reviews/native-first-pass-artifacts.json", "historical-before-hash-receipt")
        original_images = {item.get("path"): item for item in original_manifest.get("files", []) if item.get("path") in BEFORE}
        self.check(set(original_images) == set(BEFORE), "BEFORE_BASELINE_SET", "paper/reviews/native-first-pass-artifacts.json", "all seven original before-image receipts must be present")
        for path in BEFORE:
            data = self.source(path, "production-or-existing-system-before")
            if data:
                # Preserve the seven original names and bytes. Four historical
                # .png filenames contain JPEG payloads; do not transcode them.
                good = data.startswith(b"\x89PNG\r\n\x1a\n") or (data.startswith(b"\xff\xd8") and data.endswith(b"\xff\xd9"))
                self.check(good, "BEFORE_IMAGE_FORMAT", path, "expected original PNG or JPEG payload, independently of historical suffix")
                receipt = original_images.get(path, {})
                self.check(receipt.get("bytes") == len(data) and receipt.get("sha256") == sha(data), "BEFORE_BASELINE_CHANGED", path, "before-image bytes differ from the original closed first-pass manifest")
        self.progress = self.read_json("paper/writer-continuation-progress.json", "native-operation-provenance")
        index = self.read_json("paper/native-board-index.json", "native-binding")
        self.time(self.progress.get("observed_at"), "writer checkpoint")
        self.validate_operations(self.progress, index)
        self.validate_boards(self.progress, index)
        self.validate_roles_and_predecessors()
        self.select_optional_captures()
        self.final_receipts()
        task_manifest = self.task_manifest()
        return task_manifest

    def expected_rows(self):
        return [dict(value, expected_step_keys=sorted(value["expected_step_keys"]), input_packets=sorted(set(value["input_packets"]))) for _, value in sorted(self.expected.items())]

    def report(self):
        return {"schema": "f02.native-freeze-preflight.v1", "observed_at_utc": utc_now(),
                "mode": "CREATE" if self.args.create else "DRY_RUN",
                "ready_to_package": not self.errors, "freeze_created": False,
                "partial_output_directory": str(self.created_output) if self.created_output else None,
                "expected_board_count": len(self.expected), "writer_board_count": len(self.progress.get("boards", [])),
                "final_capture_receipts": len(self.full_captures), "selected_optional_captures": len(self.optional_captures),
                "source_file_count": len(self.files), "final_receipts": self.receipts,
                "errors": self.errors}

    def create(self, task_manifest):
        if self.errors:
            raise ValueError("incomplete freeze refused")
        if not self.args.output:
            raise ValueError("--create requires --output paper/freezes/<new-name>")
        output_rel = relative_path(self.args.output)
        parts = PurePosixPath(output_rel).parts
        if len(parts) != 3 or parts[:2] != ("paper", "freezes"):
            raise ValueError("output must be a new direct child of f02/paper/freezes")
        output = self.root / output_rel
        if output.exists() or output.is_symlink():
            raise ValueError("refusing to overwrite an existing freeze directory")
        for path, record in self.files.items():
            if sha((self.root / path).read_bytes()) != record["sha256"]:
                raise ValueError(f"source changed during validation: {path}; no freeze created")
        now = utc_now()
        extra = {
            "EXPECTED_BOARDS.json": json_bytes({"schema": "f02.expected-native-board-set.v1", "board_count": EXPECTED_COUNT, "boards": self.expected_rows()}),
            "CAPTURE_SELECTION.json": json_bytes({"schema": "f02.final-native-capture-selection.v1", "full_boards": [self.full_captures[k] for k in sorted(self.full_captures)], "optional": self.optional_captures, "excluded": self.excluded_captures, "selection_flags": {"include_final_sections": self.args.include_final_sections, "include_closed_table_width": self.args.include_closed_table_width, "section_capture": sorted(self.args.section_capture)}, "boundary": "Optional section/closed-table width images are supplementary; only the 32 bare-key full-board pairs are completed-screen evidence."}),
            "TASK_MANIFEST.json": json_bytes(task_manifest),
            "FREEZE_SOURCE_FILES.txt": ("\n".join(sorted(self.files)) + "\n").encode(),
        }
        all_paths = sorted(set(self.files) | set(GENERATED) | {MANIFEST})
        # Paths only: self-listing is safe. No self-referential file/commit hash.
        prefix = self.root.name + "/" + output_rel + "/"
        extra["FREEZE_FILES_FOR_GIT.txt"] = ("\n".join(prefix + p for p in all_paths) + "\n").encode()
        payload = {path: record["data"] for path, record in self.files.items()}
        payload.update(extra)
        members = [{"path": path, "source_path": path if path in self.files else None,
                    "bytes": len(data), "sha256": sha(data),
                    "categories": sorted(self.files[path]["categories"]) if path in self.files else ["generated-freeze-metadata"]}
                   for path, data in sorted(payload.items())]
        manifest = {"schema": SCHEMA, "created_at_utc": now,
                    "status": "FROZEN_NATIVE_DESIGN_EVIDENCE_NOT_APPROVAL",
                    "source_paths_relative_to": "f02", "members": members,
                    "member_count": len(members), "total_member_bytes": sum(m["bytes"] for m in members),
                    "artifact_set_sha256": aggregate(members),
                    "aggregate_definition": "SHA256 of sorted relative path UTF-8 + NUL + lowercase file SHA256 ASCII + LF for every member; manifest.json is excluded",
                    "expected_board_count": EXPECTED_COUNT, "before_image_count": len(BEFORE),
                    "final_full_board_pairs": len(self.full_captures), "optional_capture_count": len(self.optional_captures),
                    "writer_checkpoint_sha256": self.files["paper/writer-continuation-progress.json"]["sha256"],
                    "final_receipts": self.receipts, "source_commit_context": self.args.source_commit,
                    "immutable_git_freeze_commit": None,
                    "git_commit_binding": "Root supplies the immutable commit separately after persistence; do not edit this manifest to embed its own containing commit.",
                    "remaining_evidence_boundaries": ["Independent native design verdict is not supplied by this packager.", "Retained domain/source roles remain unqualified as declared.", "Browser input/focus/touch/400% zoom, F01 joint release, consumer/domain integration, formal RIG admission and production acceptance require their own evidence."]}
        payload[MANIFEST] = json_bytes(manifest)
        # Reserve a new name atomically. Partial write failures remain at that
        # name for inspection; this program never replaces or cleans a freeze.
        output.parent.mkdir(parents=True, exist_ok=True)
        if output.parent.is_symlink():
            raise ValueError("freeze parent may not be a symlink")
        output.mkdir(exist_ok=False)
        self.created_output = output
        for path, data in sorted(payload.items()):
            destination = output / path
            destination.parent.mkdir(parents=True, exist_ok=True)
            with destination.open("xb") as stream:
                stream.write(data)
            destination.chmod(0o444)
        verification = verify_freeze(output)
        if verification["errors"]:
            raise ValueError("new freeze failed readback: " + json.dumps(verification["errors"]))
        for directory in sorted((p for p in output.rglob("*") if p.is_dir()), key=lambda p: len(p.parts), reverse=True):
            directory.chmod(0o555)
        output.chmod(0o555)
        return {"freeze_created": True, "output": str(output), "artifact_set_sha256": manifest["artifact_set_sha256"],
                "member_count": len(members), "files_for_git": str(output / "FREEZE_FILES_FOR_GIT.txt"),
                "source_files": str(output / "FREEZE_SOURCE_FILES.txt"),
                "git_commit": "supplied separately by root after commit"}


def verify_freeze(directory: Path) -> dict:
    directory = directory.resolve()
    errors = []
    try:
        if (directory / MANIFEST).is_symlink() or any(p.is_symlink() for p in directory.rglob("*")):
            raise ValueError("symlinks are forbidden anywhere in the freeze")
        manifest = json.loads((directory / MANIFEST).read_bytes())
        if manifest.get("schema") != SCHEMA:
            raise ValueError("unsupported manifest schema")
        members = manifest.get("members", [])
        paths = [m.get("path") for m in members]
        if paths != sorted(set(paths)) or MANIFEST in paths:
            errors.append("members must be unique, sorted, and exclude manifest.json")
        observed = []
        for member in members:
            path = relative_path(member["path"])
            cursor = directory
            for part in PurePosixPath(path).parts:
                cursor /= part
                if cursor.is_symlink():
                    raise ValueError(f"symlink member: {path}")
            data = (directory / path).read_bytes()
            if len(data) != member.get("bytes") or sha(data) != member.get("sha256"):
                errors.append(f"hash/length mismatch: {path}")
            observed.append({"path": path, "sha256": sha(data)})
        actual = {p.relative_to(directory).as_posix() for p in directory.rglob("*") if p.is_file()}
        if actual != set(paths) | {MANIFEST}:
            errors.append("extra or missing files outside manifest membership")
        if aggregate(observed) != manifest.get("artifact_set_sha256"):
            errors.append("artifact-set aggregate mismatch")
        if manifest.get("member_count") != len(members) or manifest.get("total_member_bytes") != sum(m["bytes"] for m in members):
            errors.append("manifest member/byte totals mismatch")
        parse_time(manifest.get("created_at_utc"))
        return {"verified": not errors, "directory": str(directory), "artifact_set_sha256": manifest.get("artifact_set_sha256"), "members_checked": len(members), "errors": errors}
    except (OSError, ValueError, KeyError, TypeError) as exc:
        errors.append(str(exc))
        return {"verified": False, "directory": str(directory), "errors": errors}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--f02-root", default=str(Path(__file__).resolve().parents[1]), help="local f02 source root")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="read-only full preflight (default)")
    mode.add_argument("--create", action="store_true", help="create a new sealed directory only after every gate passes")
    mode.add_argument("--verify-freeze", metavar="DIRECTORY", help="verify every member, byte length and aggregate in an existing freeze")
    parser.add_argument("--output", help="new f02-relative paper/freezes/<name>; never overwritten")
    parser.add_argument("--source-commit", help="optional existing source commit context; never the containing freeze commit")
    parser.add_argument("--include-final-sections", action="store_true", help="include recorded complete/final section captures unchanged in final JSX")
    parser.add_argument("--include-closed-table-width", action="store_true", help="include recorded complete closed-table width evidence, with all ten current rows")
    parser.add_argument("--section-capture", action="append", default=[], metavar="KEY", help="select a specific eligible optional writer capture; repeatable")
    parser.add_argument("--retention-receipt", help="f02-relative final live retention receipt; auto-detected at paper/native-final-retention.json")
    parser.add_argument("--verification-receipt", help="f02-relative final native verification receipt; auto-detected at paper/native-final-verification.json")
    parser.add_argument("--require-final-receipts", action="store_true", help="also refuse missing final live retention and native verification receipts")
    parser.add_argument("--repair-receipt", action="append", default=[], metavar="PATH", help="additional current JSON receipt under paper/repairs; repeatable")
    parser.add_argument("--json", action="store_true", help="print complete machine-readable preflight details")
    args = parser.parse_args(argv)
    if args.verify_freeze:
        result = verify_freeze(Path(args.verify_freeze))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["verified"] else 2
    if args.source_commit and not re.fullmatch(r"[0-9a-f]{40}", args.source_commit):
        parser.error("--source-commit must be an exact lowercase 40-character existing commit")
    packager = Packager(args)
    try:
        tasks = packager.run_validation()
        result = packager.report()
        if args.create and not packager.errors:
            result.update(packager.create(tasks))
    except (OSError, ValueError, TypeError, KeyError) as exc:
        packager.fail("PACKAGER_REFUSED", "preflight", str(exc))
        result = packager.report()
    if args.json or result.get("freeze_created"):
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("READY TO PACKAGE" if not result["errors"] else "FREEZE NOT COMPLETED — partial output retained at " + result["partial_output_directory"] if result.get("partial_output_directory") else "FREEZE REFUSED — no freeze directory created")
        print(f"Expected {result['expected_board_count']} boards; writer {result['writer_board_count']}; final capture receipts {result['final_capture_receipts']}; selected optional captures {result['selected_optional_captures']}.")
        counts = Counter(error["code"] for error in result["errors"])
        print("Gate failures: " + (", ".join(f"{code}={count}" for code, count in sorted(counts.items())) or "none"))
        for error in result["errors"][:20]:
            print(f"- {error['code']}: {error['path']}: {error['message']}")
        if len(result["errors"]) > 20:
            print(f"{len(result['errors']) - 20} further failures; use --json for all details.")
        print("Final receipts: " + json.dumps(result["final_receipts"], sort_keys=True))
    return 2 if result["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
