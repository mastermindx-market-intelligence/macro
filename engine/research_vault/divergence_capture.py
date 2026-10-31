"""Prospective private native-capture retention over the incumbent Research R2 store.

Internal source preparation only: no API/CLI/cron, current pointer, activation,
public projection, generation qualification or automatic write retry.
"""
from __future__ import annotations

import hashlib
import json
import re
import math
from dataclasses import dataclass
from pathlib import Path

PREFIX = "research_vault/native_theme_state/v1"
MAX_BYTES = 8 * 1024 * 1024
SHA_RE = re.compile(r"[0-9a-f]{64}")
COMMIT_RE = re.compile(r"[0-9a-f]{40}")

class CaptureRefused(ValueError):
    pass

class CaptureEffectUnknown(RuntimeError):
    def __init__(self, key, expected_sha256):
        self.key, self.expected_sha256 = key, expected_sha256
        super().__init__("private capture effect unknown; reconcile the same key only")

@dataclass(frozen=True)
class CaptureReference:
    key: str
    payload_sha256: str
    state: str
    publication_allowed: bool = False
    qualification: str = "UNQUALIFIED_NATIVE_COMPUTATION"

def canonical(value):
    return json.dumps(value,sort_keys=True,ensure_ascii=False,allow_nan=False,separators=(",",":")).encode()

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def key_for_run(native_run_id):
    if type(native_run_id) is not str or not native_run_id or len(native_run_id)>192 or any(ord(c)<32 for c in native_run_id):
        raise CaptureRefused("original native run identity required")
    return PREFIX + "/" + digest(native_run_id.encode()) + "/divergence.json"

def _fields(value, names, *, optional=False):
    allowed=set(names.split())
    if type(value) is not dict or any(type(k) is not str for k in value) or (not set(value)<=allowed if optional else set(value)!=allowed):
        raise CaptureRefused("closed capture field shape required")

def _leaf(value):
    # A display label is a scalar, never a nested upstream source object.
    if value is None or type(value) is bool:
        return
    if type(value) in (int,float) and math.isfinite(value):
        return
    if type(value) is str and len(value)<=1024 and not any(ord(c)<32 for c in value):
        return
    raise CaptureRefused("bounded scalar capture field required")

def _scalars(value, names, *, optional=False):
    _fields(value,names,optional=optional)
    for v in value.values():
        _leaf(v)

def _rows(value):
    if type(value) is not list or len(value)>20000:
        raise CaptureRefused("bounded capture row array required")
    return value

def validate_projection(capture):
    """Closed storage/privacy shape, not an independent computation verifier."""
    _fields(capture,"schema capture_started_at capture_completed_at effective_at effective_at_declared source_available_at producer_revision input_scope input_sha256 inputs attempted_population n_input_rows identity_status axis_computations cross_section_positions method predecessor_ledger last_quadrants_used board member_identity_receipts source_purpose_receipts qualification publication_allowed capture_sha256")
    for key in ("source_available_at","producer_revision","member_identity_receipts","source_purpose_receipts"):
        if capture[key] is not None:
            raise CaptureRefused("native capture cannot invent qualification receipts")
    nested={"inputs","attempted_population","axis_computations","cross_section_positions","method","predecessor_ledger","last_quadrants_used","board"}
    for k,v in capture.items():
        if k not in nested:
            _leaf(v)
    inputs=capture["inputs"]
    _fields(inputs,"cascade activity")
    _fields(inputs["cascade"],"themes asof",optional=True)
    if "asof" in inputs["cascade"]:
        _leaf(inputs["cascade"]["asof"])
    rows=_rows(inputs["cascade"].get("themes"))
    for row in rows:
        _scalars(row,"theme name stage language_accel bottleneck_text_only bottleneck_band revision_breadth broadening_state",optional=True)
    if type(inputs["activity"]) is not dict:
        raise CaptureRefused("closed activity map required")
    attempted_keys={row.get("theme") for row in rows if type(row.get("theme")) is str and row["theme"]}
    for key,entry in inputs["activity"].items():
        if key not in attempted_keys:
            raise CaptureRefused("unattempted activity is outside the capture")
        _fields(entry,"fused_obs_z sources")
        _leaf(entry["fused_obs_z"])
        for source in _rows(entry["sources"]):
            _scalars(source,"name z")
            if source["name"]!="news_velocity":
                raise CaptureRefused("unconsumed activity source")
    population=_rows(capture["attempted_population"])
    if type(capture["n_input_rows"]) is not int or capture["n_input_rows"]!=len(rows) or len(population)!=len(rows):
        raise CaptureRefused("complete attempted population required")
    for i,row in enumerate(population):
        _scalars(row,"source_position theme status")
        theme=rows[i].get("theme")
        if type(row["source_position"]) is not int or row["source_position"]!=i or row["theme"]!=theme or row["status"]!=("ATTEMPTED" if theme else "MISSING_NATIVE_KEY"):
            raise CaptureRefused("attempted population does not bind exact input rows")
    for axis in _rows(capture["axis_computations"]):
        _fields(axis,"source_position theme narrative_legs money_legs narrative_native_values money_native_values narrative_raw money_raw")
        for key in ("source_position","theme","narrative_raw","money_raw"):
            _leaf(axis[key])
        for key in ("narrative_legs","money_legs"):
            for pair in _rows(axis[key]):
                if type(pair) not in (tuple,list) or len(pair)!=2:
                    raise CaptureRefused("closed native leg required")
                for value in pair:
                    if type(value) not in (float,int) or not math.isfinite(value):
                        raise CaptureRefused("finite numeric native leg required")
        _scalars(axis["narrative_native_values"],"news_z language_accel text_only_flag")
        _scalars(axis["money_native_values"],"fused_obs_z revision_breadth broadening_state")
    for position in _rows(capture["cross_section_positions"]):
        if type(position) is not int or not 0<=position<len(rows):
            raise CaptureRefused("cross-section position outside attempted population")
    _scalars(capture["method"],"rank minimum_rank_population narrative_high money_high catchup_calendar_days provisional")
    _scalars(capture["predecessor_ledger"],"state sha256 bytes")
    if type(capture["last_quadrants_used"]) is not dict:
        raise CaptureRefused("closed predecessor map required")
    for key,pair in capture["last_quadrants_used"].items():
        _leaf(key)
        if type(pair) not in (tuple,list) or len(pair)!=2:
            raise CaptureRefused("closed predecessor quadrant required")
        for value in pair:
            _leaf(value)
    board=capture["board"]
    _fields(board,"items n_cross_section n_total quadrant_counts thin_cross_section note")
    for key in ("n_cross_section","n_total","thin_cross_section","note"):
        _leaf(board[key])
    _scalars(board["quadrant_counts"],"confirmed hype-risk hidden-opportunity ignore")
    for row in _rows(board["items"]):
        _scalars(row,"theme name stage quadrant narrative_pct money_pct divergence n_narrative_legs_live n_money_legs_live excluded transition")

def prepare(capture, *, native_run_id, producer_commit):
    """Validate actual content, not source authenticity or rights."""
    key=key_for_run(native_run_id)
    if type(producer_commit) is not str or COMMIT_RE.fullmatch(producer_commit) is None:
        raise CaptureRefused("exact declared producer commit required")
    if type(capture) is not dict or capture.get("schema")!="gmi.divergence_same_run_capture/v1":
        raise CaptureRefused("closed same-run capture required")
    validate_projection(capture)
    if capture.get("publication_allowed") is not False or capture.get("qualification")!="UNQUALIFIED_NATIVE_COMPUTATION":
        raise CaptureRefused("capture cannot supply publication or qualification")
    if capture.get("input_scope")!="NATIVE_DIVERGENCE_FIELDS_NOT_UPSTREAM_PROVENANCE":
        raise CaptureRefused("only the closed native field projection may be retained")
    payload=dict(capture)
    expected=payload.pop("capture_sha256",None)
    if type(expected) is not str or SHA_RE.fullmatch(expected) is None or digest(canonical(payload))!=expected:
        raise CaptureRefused("capture digest mismatch")
    if digest(canonical(capture.get("inputs")))!=capture.get("input_sha256"):
        raise CaptureRefused("capture input digest mismatch")
    envelope={"schema":"gmi.private_divergence_capture/v1","native_run_id":native_run_id,
              "declared_producer_commit":producer_commit,"capture":capture,
              "purpose":"internal_replay","source_authentication":"NOT_ESTABLISHED",
              "qualification":"UNQUALIFIED_NATIVE_COMPUTATION","publication_allowed":False}
    raw=canonical(envelope)
    if len(raw)>MAX_BYTES:
        raise CaptureRefused("private capture exceeds allocation")
    return key,raw

def _read(store,key):
    raw=store.get_bytes_strict_bounded(key,MAX_BYTES)
    if raw is not None and (type(raw) is not bytes or len(raw)>MAX_BYTES):
        raise CaptureRefused("store violated the bounded byte contract")
    return raw

def _require_runtime_store(store):
    from engine.research_vault.r2_store import R2Store
    if type(store) is not R2Store or not store.available or not store._single_attempt_writes:
        raise CaptureRefused("provisioned private single-attempt Research R2 store required")
    store.validate_strict_conditional_write_capability()
    return store

def runtime_store():
    """Use only the already provisioned private Research R2 client."""
    from engine.research_vault.r2_store import build_store
    store=build_store(single_attempt_writes=True)
    return _require_runtime_store(store)

def reconcile(store, *, native_run_id, expected_sha256):
    """Read-only settlement of the original key; absence cannot license retry."""
    key=key_for_run(native_run_id)
    if type(expected_sha256) is not str or SHA_RE.fullmatch(expected_sha256) is None:
        raise CaptureRefused("exact expected payload digest required")
    try:
        raw=_read(store,key)
    except Exception as exc:
        raise CaptureEffectUnknown(key,expected_sha256) from exc
    if raw is None:
        raise CaptureEffectUnknown(key,expected_sha256)
    if digest(raw)!=expected_sha256:
        raise CaptureRefused("original native run holds different immutable bytes")
    return CaptureReference(key,expected_sha256,"COMMITTED_OBSERVED")

def _retain_prepared_store_once(store,capture,*,native_run_id,producer_commit,before_write):
    """Internal primitive; production enters through the original-run journal."""
    key,raw=prepare(capture,native_run_id=native_run_id,producer_commit=producer_commit)
    expected=digest(raw)
    store.validate_strict_conditional_write_capability()
    prior=_read(store,key)  # failure here is before any modifying request
    if prior is not None:
        if prior!=raw:
            raise CaptureRefused("original native run holds different immutable bytes")
        return CaptureReference(key,expected,"COMMITTED_OBSERVED")
    # Production callback must durably record intent before any modifying call.
    before_write(key,expected,len(raw))
    try:
        result=store.put_bytes_strict_conditional(key,raw,expected_version=None,content_type="application/json")
    except Exception:
        return reconcile(store,native_run_id=native_run_id,expected_sha256=expected)
    if type(result) is not bool:
        raise CaptureEffectUnknown(key,expected)
    # True and false both need exact authoritative bytes. A false response is a
    # predecessor conflict, never permission to overwrite/retry.
    return reconcile(store,native_run_id=native_run_id,expected_sha256=expected)

def retain_private_capture(capture,*,native_run_id,producer_commit,private_run_dir):
    """Submit once on the original private artifact carrier, never an API/CLI.

    Reuses the incumbent durable evidence sink; no catalog, global registry or
    current pointer is introduced. The ordinary native producer supplies its
    existing private artifact directory and stable invocation identity. These
    parameters do not authenticate a caller or permit changing carrier on
    recovery. The fixed exclusive slot remains after any outcome. Recovery uses
    read-only reconcile with the intent's exact key/digest, never this entry.
    """
    from engine.research_vault.generation_evidence import FileGenerationEvidence
    key,raw=prepare(capture,native_run_id=native_run_id,producer_commit=producer_commit)
    expected=digest(raw)
    store=_require_runtime_store(runtime_store())
    slot=Path(private_run_dir)/("native-divergence-"+digest(native_run_id.encode())+".jsonl")
    evidence=FileGenerationEvidence.create(slot,{"source_commit":producer_commit,"run":native_run_id},max_bytes=32768)
    issued=False
    def before_write(actual_key,actual_digest,length):
        nonlocal issued
        if issued or actual_key!=key or actual_digest!=expected:
            raise CaptureRefused("original invocation changed before submission")
        evidence.append("write_intent",{"key":key,"sha256":expected,"bytes":length,
            "conditional":True,"expected_version":None,"content_type":"application/json"},reserve_bytes=8192)
        issued=True
    try:
        try:
            result=_retain_prepared_store_once(store,capture,native_run_id=native_run_id,
                producer_commit=producer_commit,before_write=before_write)
        except Exception:
            try:
                evidence.append("terminal",{"state":"UNRESOLVED","write_intent_durable":issued,
                    "key":key,"sha256":expected})
            except Exception as finalization_error:
                if issued:
                    raise CaptureEffectUnknown(key,expected) from finalization_error
            raise
        try:
            evidence.append("terminal",{"state":result.state,"write_intent_durable":issued,
                "key":key,"sha256":expected})
        except Exception as finalization_error:
            if issued:
                raise CaptureEffectUnknown(key,expected) from finalization_error
            raise
        return result
    finally:
        try:
            evidence.close()
        except Exception as finalization_error:
            if issued:
                raise CaptureEffectUnknown(key,expected) from finalization_error
            raise
