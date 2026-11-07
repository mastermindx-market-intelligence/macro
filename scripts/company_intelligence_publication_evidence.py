"""Allowlisted publication metadata; never a wire archive or source-use grant."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import stat
import tempfile
from typing import Any, Mapping

from engine.company_intelligence.event_workspace import (
    validate_event_workspace, validate_workspace_manifest, validate_generation_clocks,
)
from engine.company_intelligence.identity import company_id_for_cik
from engine.earnings_release.receipts import (
    resolve_sec_acquisition_location, sec_declared_charset, validate_sec_acquisition_url,
)

MAX_MANIFEST = 1024 * 1024
MAX_WIRE = 16 * 1024 * 1024
MAX_ROWS = 10000
MAX_EVIDENCE = 16 * 1024 * 1024
_SHA = re.compile(r"[0-9a-f]{64}\Z")
_RECEIPT_KEYS = frozenset({
    "schema", "filing_key", "requested_url", "final_url", "redirect_policy", "redirects",
    "http_status", "body_representation", "content_type", "content_encoding", "declared_charset",
    "entity_sha256", "entity_length", "decoder", "decode_errors", "decode_policy",
    "source_sha256", "source_utf8_length", "acquired_at",
})
_OUTCOMES = frozenset({
    "not_attempted_no_client", "not_attempted_no_bucket", "not_attempted_no_manifest",
    "manifest_rejected", "already_current", "dry_run", "payload_failure_partial_effects_possible",
    "marker_conflict", "marker_put_failed_effect_unknown", "marker_put_acknowledged",
    "outcome_unobserved_effect_unknown",
})
_CODES = frozenset({
    "invalid_json", "invalid_manifest", "invalid_wire", "invalid_selected_source",
    "invalid_receipt", "unsafe_receipt_metadata", "no_local_output", "unsafe_local_path",
    "output_unavailable", "evidence_limit", "invalid_context", "invalid_outcome",
})


class EvidenceValidationError(ValueError):
    def __init__(self, code: str):
        self.code = code if code in _CODES else "output_unavailable"
        super().__init__(self.code)


def _fail(code: str) -> None:
    raise EvidenceValidationError(code)


def _json(body: bytes, maximum: int) -> dict[str, Any]:
    def pairs(items):
        out = {}
        for key, value in items:
            if key in out:
                _fail("invalid_json")
            out[key] = value
        return out
    try:
        if type(body) is not bytes or len(body) > maximum:
            _fail("evidence_limit")
        value = json.loads(body.decode("utf-8"), object_pairs_hook=pairs,
                           parse_constant=lambda _value: _fail("invalid_json"))
        if type(value) is not dict:
            _fail("invalid_json")
        return value
    except (UnicodeError, ValueError, TypeError, RecursionError) as exc:
        if isinstance(exc, EvidenceValidationError):
            raise
        raise EvidenceValidationError("invalid_json") from None


def _utc(stamp: Any) -> datetime:
    if type(stamp) is not str or not re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{1,6})?Z", stamp):
        _fail("invalid_receipt")
    try:
        return datetime.fromisoformat(stamp[:-1] + "+00:00")
    except ValueError:
        raise EvidenceValidationError("invalid_receipt") from None


def _receipt(value: Any, source: dict[str, Any], cutoff: str) -> dict[str, Any]:
    try:
        if type(value) is not dict or set(value) != _RECEIPT_KEYS:
            _fail("invalid_receipt")
        if (value["schema"] != "earnings_release.sec_acquisition.v1"
                or value["redirect_policy"] != "sec_https_same_filing_max5.v1"
                or value["body_representation"] != "requests.content_after_content_decoding"
                or type(value["http_status"]) is not int or value["http_status"] != 200
                or value["filing_key"] != source["filing_key"]
                or value["source_sha256"] != source["source_sha256"]
                or value["requested_url"] != source["url"]):
            _fail("invalid_receipt")
        key = source["filing_key"]
        current = validate_sec_acquisition_url(value["requested_url"], **key)
        hops = value["redirects"]
        if type(hops) is not list or len(hops) > 5:
            _fail("invalid_receipt")
        visited = {current}
        for hop in hops:
            if (type(hop) is not dict or set(hop) != {"url", "status", "location", "next_url"}
                    or hop["url"] != current or type(hop["status"]) is not int
                    or hop["status"] not in {301, 302, 303, 307, 308}):
                _fail("invalid_receipt")
            next_url = resolve_sec_acquisition_location(current, hop["location"], **key)
            if next_url != hop["next_url"] or next_url in visited:
                _fail("invalid_receipt")
            visited.add(next_url)
            current = next_url
        if validate_sec_acquisition_url(value["final_url"], **key) != current:
            _fail("invalid_receipt")
        mime = value["content_type"]
        charset = r"(?:utf-8|utf8|iso-8859-1|latin-1)"
        if mime is not None and (type(mime) is not str or not re.fullmatch(
                r"(?:text/html|text/plain|application/xhtml\+xml)(?:;\s*charset=" + charset + r")?",
                mime, re.IGNORECASE)):
            _fail("unsafe_receipt_metadata")
        if value["content_encoding"] not in {None, "identity", "gzip", "deflate", "br", "zstd"}:
            _fail("unsafe_receipt_metadata")
        if value["declared_charset"] not in {None, "utf-8", "utf8", "iso-8859-1", "latin-1"}:
            _fail("unsafe_receipt_metadata")
        if value["declared_charset"] != sec_declared_charset(mime):
            _fail("invalid_receipt")
        if (value["decoder"] not in {"utf-8", "latin-1"} or value["decode_errors"] != "strict"
                or value["decode_policy"] not in {"utf8_strict", "utf8_strict_then_latin1_strict"}
                or (value["decode_policy"] == "utf8_strict" and value["decoder"] != "utf-8")):
            _fail("invalid_receipt")
        for field in ("entity_sha256", "source_sha256"):
            if type(value[field]) is not str or not _SHA.fullmatch(value[field]):
                _fail("invalid_receipt")
        for field in ("entity_length", "source_utf8_length"):
            if type(value[field]) is not int or not 1 <= value[field] <= 2 ** 53 - 1:
                _fail("invalid_receipt")
        if value["decoder"] == "utf-8" and (value["entity_sha256"] != value["source_sha256"]
                or value["entity_length"] != value["source_utf8_length"]):
            _fail("invalid_receipt")
        if value["decoder"] == "latin-1" and not (
                value["entity_length"] < value["source_utf8_length"] <= 2 * value["entity_length"]):
            _fail("invalid_receipt")
        if _utc(value["acquired_at"]) > _utc(cutoff):
            _fail("invalid_receipt")
        return deepcopy(value)
    except (ValueError, TypeError, KeyError, OverflowError) as exc:
        if isinstance(exc, EvidenceValidationError):
            raise
        raise EvidenceValidationError("invalid_receipt") from None


def build_sec_snapshot(manifest_bytes: bytes, workspace_bytes: Mapping[str, bytes]) -> dict[str, Any]:
    """Bind existing local wires, exporting no original manifest or mixed row."""
    manifest = _json(manifest_bytes, MAX_MANIFEST)
    try:
        validate_workspace_manifest(manifest)
        if len(manifest["files"]) > MAX_ROWS or set(workspace_bytes) != set(manifest["files"]):
            _fail("invalid_manifest")
    except (ValueError, TypeError, KeyError) as exc:
        if isinstance(exc, EvidenceValidationError):
            raise
        raise EvidenceValidationError("invalid_manifest") from None
    rows = {}
    for path, block in manifest["files"].items():
        body = workspace_bytes[path]
        if type(body) is not bytes or len(body) != block["bytes"] or sha256(body).hexdigest() != block["sha256"]:
            _fail("invalid_wire")
        row = _json(body, MAX_WIRE)
        try:
            validate_event_workspace(row)
            if path != f"workspaces/{row['event_id']}.json" or row["generation_id"] != manifest["generation_id"]:
                _fail("invalid_wire")
        except (ValueError, TypeError, KeyError) as exc:
            if isinstance(exc, EvidenceValidationError):
                raise
            raise EvidenceValidationError("invalid_wire") from None
        rows[row["event_id"]] = row
    try:
        validate_generation_clocks(manifest, rows)
    except (ValueError, TypeError, KeyError):
        raise EvidenceValidationError("invalid_wire") from None
    selected = []
    for event_id, row in sorted(rows.items()):
        sources = [x for x in row["sources"] if isinstance(x, dict) and x.get("kind") == "issuer_release"]
        if not sources:
            continue
        if len(sources) != 1:
            _fail("invalid_selected_source")
        source = sources[0]
        present = "acquisition_receipt" in source
        try:
            key = source["filing_key"]
            if (type(key) is not dict or set(key) != {"cik", "accession"}
                    or type(key["cik"]) is not str or not re.fullmatch(r"\d{10}", key["cik"])
                    or type(key["accession"]) is not str or not re.fullmatch(r"\d{10}-\d\d-\d{6}", key["accession"])):
                _fail("invalid_selected_source")
            try:
                url = validate_sec_acquisition_url(source["url"], **key)
            except ValueError:
                if present:
                    _fail("invalid_receipt")
                continue
            if (row["issuer"]["company_id"] != company_id_for_cik(key["cik"])
                    or not event_id.startswith("evt_cik" + key["cik"] + "_")
                    or type(source["source_sha256"]) is not str or not _SHA.fullmatch(source["source_sha256"])
                    or type(source["document_id"]) is not str
                    or not re.fullmatch(r"disclosure_document_[0-9a-f]{64}", source["document_id"])
                    or source.get("receipt_state") != "byte_replayed"):
                _fail("invalid_selected_source")
            receipt = _receipt(source["acquisition_receipt"], source, row["generated_at"]) if present else None
        except (ValueError, TypeError, KeyError) as exc:
            if isinstance(exc, EvidenceValidationError):
                raise
            raise EvidenceValidationError("invalid_selected_source") from None
        path = f"workspaces/{event_id}.json"
        selected.append({
            "event_id": event_id, "company_id": row["issuer"]["company_id"],
            "generation_id": row["generation_id"], "generated_at": row["generated_at"],
            "wire": {"path": path, **manifest["files"][path]},
            "source": {"kind": "issuer_release", "document_id": source["document_id"],
                "filing_key": deepcopy(key), "source_sha256": source["source_sha256"], "url": url,
                "receipt_state": "byte_replayed", "receipt_status": "present" if present else "absent",
                "acquisition_receipt": receipt},
        })
    return {"schema": "sec_publication_snapshot.v1", "manifest": {
        "schema": manifest["schema"], "sha256": sha256(manifest_bytes).hexdigest(),
        "bytes": len(manifest_bytes), "generation_id": manifest["generation_id"],
        "generated_at": manifest["generated_at"], "source_clock": manifest.get("source_clock"),
    }, "selected": selected}


def _read(path: Path, root: Path, maximum: int) -> bytes:
    try:
        relative = path.relative_to(root)
        current = root
        if root.is_symlink():
            _fail("unsafe_local_path")
        for part in relative.parts:
            current = current / part
            if current.is_symlink():
                _fail("unsafe_local_path")
        with path.open("rb") as source:
            body = source.read(maximum + 1)
        if len(body) > maximum:
            _fail("evidence_limit")
        return body
    except OSError:
        raise EvidenceValidationError("no_local_output") from None


def local_sec_snapshot(out_dir: Path) -> dict[str, Any]:
    root = Path(out_dir)
    nest = root / "event_workspaces"
    body = _read(nest / "manifest.json", root, MAX_MANIFEST)
    manifest = _json(body, MAX_MANIFEST)
    try:
        validate_workspace_manifest(manifest)
    except (ValueError, TypeError, KeyError):
        raise EvidenceValidationError("invalid_manifest") from None
    if len(manifest["files"]) > MAX_ROWS:
        _fail("evidence_limit")
    generation = nest / "generations" / manifest["generation_id"]
    if _read(generation / "manifest.json", root, MAX_MANIFEST) != body:
        _fail("invalid_manifest")
    return build_sec_snapshot(body, {p: _read(generation / p, root, MAX_WIRE) for p in manifest["files"]})


class PublicationEvidence:
    """One local attempt, with real decision-site outcomes, not rc0 inference."""
    def __init__(self, path: Path, *, checkout: str, run_id: str, run_attempt: str):
        if (any(type(value) is not str for value in (checkout, run_id, run_attempt))
                or not re.fullmatch(r"[0-9a-f]{40}", checkout)
                or not re.fullmatch(r"[1-9][0-9]*", run_id)
                or not re.fullmatch(r"[1-9][0-9]*", run_attempt)):
            _fail("invalid_context")
        self.path = Path(path)
        self._source_roots: tuple[Path, Path] | None = None
        self._final_serialized = False
        self.context = {"repository": "mastermindx-market-intelligence/macro", "checkout": checkout,
                        "run_id": run_id, "run_attempt": run_attempt}
        self.candidates: list[dict[str, Any]] = []
        self.unavailable: list[str] = []

    def _safe_destination(self, path: Path) -> bool:
        if self._source_roots is None:
            return False
        try:
            destinations = (Path(os.path.abspath(path)), path.resolve())
            return not path.is_symlink() and all(
                not destination.is_relative_to(root)
                for destination in destinations for root in self._source_roots
            )
        except (OSError, RuntimeError):
            return False

    def _bind_output(self, out_dir: Path) -> bool:
        try:
            roots = (Path(os.path.abspath(out_dir)), Path(out_dir).resolve())
        except (OSError, RuntimeError):
            self.unavailable.append("unsafe_local_path")
            return False
        if self._source_roots is None:
            self._source_roots = roots
        if self._source_roots != roots or not self._safe_destination(self.path):
            self.unavailable.append("unsafe_local_path")
            return False
        return True

    def begin(self, out_dir: Path) -> int | None:
        self._final_serialized = False
        if not self._bind_output(out_dir):
            return None
        try:
            snapshot = local_sec_snapshot(out_dir)
        except EvidenceValidationError as exc:
            self.unavailable.append(exc.code)
            return None
        token = len(self.candidates) + 1
        self.candidates.append({"sequence": token, "snapshot": snapshot,
                                "publish_outcome": "outcome_unobserved_effect_unknown"})
        return token

    def outcome(self, token: int | None, outcome: str) -> None:
        self._final_serialized = False
        if outcome not in _OUTCOMES:
            _fail("invalid_outcome")
        if token is not None:
            if type(token) is not int or not 1 <= token <= len(self.candidates):
                _fail("invalid_outcome")
            self.candidates[token - 1]["publish_outcome"] = outcome
        self._write("incomplete", None)

    def finish(self, out_dir: Path, refresh_outcome: str) -> bool:
        self._final_serialized = False
        if not self._bind_output(out_dir):
            return False
        if refresh_outcome not in {"returned_success", "returned_conflict", "failed"}:
            _fail("invalid_outcome")
        final = None
        if refresh_outcome == "returned_success":
            try:
                snapshot = local_sec_snapshot(out_dir)
                matches = [c["sequence"] for c in self.candidates
                           if c["snapshot"]["manifest"] == snapshot["manifest"]]
                final = {"snapshot": snapshot, "candidate_sequence": matches[-1] if matches else None}
            except EvidenceValidationError as exc:
                self.unavailable.append(exc.code)
        self._final_serialized = self._write(refresh_outcome, final)
        return self._final_serialized

    def mark_ready(self, path: Path) -> bool:
        """Append only to an existing, distinct, current-owned step-output sink."""
        if not self._final_serialized or not self._safe_destination(path):
            return False
        try:
            if path.resolve() == self.path.resolve():
                return False
            preliminary = path.lstat()
            if (not stat.S_ISREG(preliminary.st_mode) or preliminary.st_nlink != 1
                    or preliminary.st_uid != os.getuid()):
                return False
            descriptor = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_NOFOLLOW | os.O_NONBLOCK)
        except (OSError, RuntimeError):
            return False
        try:
            sink = os.fstat(descriptor)
            artifact = self.path.stat()
            if (not stat.S_ISREG(sink.st_mode) or sink.st_nlink != 1 or sink.st_uid != os.getuid()
                    or (sink.st_dev, sink.st_ino) == (artifact.st_dev, artifact.st_ino)
                    or not self._safe_destination(path)):
                return False
            line = b"sec_evidence_ready=true\n"
            return os.write(descriptor, line) == len(line)
        except OSError:
            return False
        finally:
            try:
                os.close(descriptor)
            except OSError:
                pass

    def _write(self, refresh_outcome: str, final: Any) -> bool:
        if not self._safe_destination(self.path):
            return False
        status = "unavailable" if not self.candidates and final is None else (
            "partial" if self.unavailable or refresh_outcome != "returned_success" or final is None
            or not self.candidates or final["candidate_sequence"] is None else "metadata_complete")
        envelope = {"retention_status": status, "schema": "sec_publication_evidence.v1", "context": self.context,
            "audience": "existing_public_repository_artifact_readers", "retention_days": 7,
            "scope": "selected_sec_metadata_only_not_original_wire_or_authorization",
            "candidates": self.candidates, "refresh_outcome": refresh_outcome,
            "final_local_selection": final, "unavailable": sorted(set(self.unavailable))}
        temporary = None
        try:
            body = json.dumps(envelope, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                              allow_nan=False).encode("utf-8")
            if len(body) > MAX_EVIDENCE:
                _fail("evidence_limit")
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(dir=self.path.parent, prefix=self.path.name + ".tmp.", delete=False) as dest:
                temporary = Path(dest.name)
                dest.write(body)
            if not self._safe_destination(self.path):
                return False
            os.replace(temporary, self.path)
            return True
        except (OSError, ValueError):
            # No unvalidated fallback or exception text may become an artifact.
            if self._safe_destination(self.path):
                try:
                    self.path.unlink(missing_ok=True)
                except OSError:
                    pass
            return False
        finally:
            if temporary is not None and self._safe_destination(temporary):
                try:
                    temporary.unlink(missing_ok=True)
                except OSError:
                    pass
