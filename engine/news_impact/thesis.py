"""Append-only fact log and pure thesis-view projector.

Implements masterplan section 5 (thesis memory: an evolving thesis view is a
fold over article manifestations, distinct facts/revisions, and linked
milestones — not a new lifecycle service) under Phase 0 freeze D16 (correction
replay via supersedes_fact_id), D12 (company_id = cik: + 10 digits), D13
(evidence is owner source_span.v1 or field_absence.v1), and standing kill
DNR:KILL-THESIS-LOBE: there is no mutable thesis object. The view is ONLY
F(fact_log, owner_snapshot, as_of_utc).

Seat-accepted design: designs/A1_thesis_store/A1_thesis_store.md section 4
(frozen spec) and section 7 defaults (W3-R1). Schema files fact_log.v1 and
thesis_view.v1 win on disagreement with the design text.

Determinism: no clock reads (as_of_utc is always a parameter), no RNG,
no network, no module-level I/O. The log path default is documentation only
and is never opened.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from hashlib import sha256
from math import isfinite
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from jsonschema import Draft202012Validator

# --------------------------------------------------------------------------- constants

SCHEMA_NAME_LOG = "fact_log.v1"
SCHEMA_NAME_VIEW = "thesis_view.v1"
AUTHORITY = "context_only"
DEFAULT_LOG_PATH = "data/news_impact/fact_log.jsonl"

PROPHET_FLAGS: dict[str, bool] = {
    "may_rank": False,
    "may_size": False,
    "may_gate": False,
    "prophet_authority": False,
}

FORBIDDEN_KEYS: frozenset[str] = frozenset(
    {
        "confidence",
        "probability",
        "score",
        "price_target",
        "fair_value",
        "sentiment",
        "contagion",
    }
)

CODES: frozenset[str] = frozenset(
    {
        "APPEND_ONLY_VIOLATION",
        "LOG_SEQ_INVALID",
        "DUPLICATE_FACT_ID",
        "SUPERSEDES_NOT_FOUND",
        "SUPERSEDES_KEY_MISMATCH",
        "SUPERSEDES_CYCLE",
        "SUPERSEDES_REQUIRED",
        "PIT_CLOCK_VIOLATION",
        "MANIFEST_REPORTS_MISSING",
        "TEXT_SAFE_VIOLATION",
        "SCHEMA_VIOLATION",
        "DECISION_CUT_AFTER_AS_OF",
        "JSONL_PARSE_ERROR",
        "AS_OF_INVALID",
    }
)

PROPOSITION_KINDS: frozenset[str] = frozenset(
    {
        "t1_authorization_program",
        "t1_execution_under_program",
        "t2_metric_period_counterparty",
        "t3_object_counterparty",
    }
)

T1_LADDER: tuple[str, ...] = (
    "announcement",
    "executed_repurchase",
    "net_dilution_reported",
)
T2_LADDER: tuple[str, ...] = ("announcement", "paid_bookings")
T3_LADDER: tuple[str, ...] = (
    "announcement",
    "artifact_available",
    "license_stated",
    "hardware_support_stated",
    "independent_deployment",
    "repeated_active_use",
    "paid_bookings",
    "reported_economics",
)

TEMPLATE_CHANNEL: dict[str, str] = {
    "capital_allocation_event.v1": "capital_allocation",
    "demand_guidance_contract_event.v1": "revenue_demand",
    "strategic_product_partnership_event.v1": "strategic_option",
}

TEMPLATE_LADDER: dict[str, tuple[str, ...]] = {
    "capital_allocation_event.v1": T1_LADDER,
    "demand_guidance_contract_event.v1": T2_LADDER,
    "strategic_product_partnership_event.v1": T3_LADDER,
}

TRIGGER_ORDER: tuple[str, ...] = (
    "changed_numeric_terms",
    "new_independent_source",
    "independently_observed_milestone",
    "contradiction",
    "missed_deadline",
    "source_correction",
    "exposure_change",
    "market_state_change",
)

# Case 4 lists independently_observed_milestone before new_independent_source.
# Emit independent-milestone first among those two when both fire; other
# triggers keep §4.9 table order.
TRIGGER_EMIT_ORDER: tuple[str, ...] = (
    "changed_numeric_terms",
    "independently_observed_milestone",
    "new_independent_source",
    "contradiction",
    "missed_deadline",
    "source_correction",
    "exposure_change",
    "market_state_change",
)

_TEXT_SAFE_PATTERNS: tuple[str, ...] = (
    r"(?i)\b(ignore|disregard|forget|override)\s+(all\s+|any\s+|the\s+|every\s+)?(previous|prior|above|preceding|earlier)\b",
    r"(?i)(^|[\n\r>\"'\]\[}{|])\s*(system|assistant|developer|user|tool|function)\s*[:：]",
    r"(?i)system\s*prompt",
    r"(?i)\b(https?|ftps?|wss?|file|javascript|vbscript|gopher|hxxps?|hxtp)\s*:",
    r"(?i)(~\/\.|/(etc|usr|bin|sbin|tmp|var|root|home|opt|dev|proc|lib)\b|\$\(|`|\brm\s+-rf\b|\bcurl\b|\bwget\b|\bchmod\b|\bbash\s+-c\b|\bsh\s+-c\b|\bpowershell\b|\bnc\s+-e\b|\|\s*sh\b)",
)


# --------------------------------------------------------------------------- errors / value objects


class ThesisError(Exception):
    """Module-specific error carrying a closed CODES string."""

    code: str

    def __init__(self, code: str, message: str) -> None:
        if code not in CODES:
            raise ValueError(f"unknown thesis error code: {code}")
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class FieldAbsence:
    """Typed absence (freeze D13); never a guessed quantity."""

    subject: str
    detail: str
    missing_fields: tuple[str, ...]
    reason: str = "not_stated"

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "field_absence.v1",
            "authority": AUTHORITY,
            "reason": self.reason,
            "subject": self.subject,
            "detail": self.detail,
            "missing_fields": list(self.missing_fields),
        }


@dataclass(frozen=True)
class OwnerSnapshot:
    """Injected read-only owner bundle (W3-R4). Never loaded from disk here."""

    identity_map: Mapping[str, Any] = field(default_factory=dict)
    qbus_clusters: Sequence[Mapping[str, Any]] = field(default_factory=tuple)
    news_event_ledger: Sequence[Mapping[str, Any]] = field(default_factory=tuple)
    ci_events: Sequence[Mapping[str, Any]] = field(default_factory=tuple)
    workspaces: Sequence[Mapping[str, Any]] = field(default_factory=tuple)
    claims: Sequence[Mapping[str, Any]] = field(default_factory=tuple)
    facts: Sequence[Mapping[str, Any]] = field(default_factory=tuple)
    guidance: Sequence[Mapping[str, Any]] = field(default_factory=tuple)
    source_spans: Sequence[Mapping[str, Any]] = field(default_factory=tuple)
    relationship_candidates: Sequence[Mapping[str, Any]] = field(default_factory=tuple)
    market_state: Mapping[str, Any] | None = None
    pbd_roots: Sequence[Mapping[str, Any]] = field(default_factory=tuple)
    leaf_payloads: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)
    decision_cut: str | None = None
    stripped_fields: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "identity_map": _plain(self.identity_map),
            "qbus_clusters": [_plain(x) for x in self.qbus_clusters],
            "news_event_ledger": [_plain(x) for x in self.news_event_ledger],
            "ci_events": [_plain(x) for x in self.ci_events],
            "workspaces": [_plain(x) for x in self.workspaces],
            "claims": [_plain(x) for x in self.claims],
            "facts": [_plain(x) for x in self.facts],
            "guidance": [_plain(x) for x in self.guidance],
            "source_spans": [_plain(x) for x in self.source_spans],
            "relationship_candidates": [_plain(x) for x in self.relationship_candidates],
            "market_state": _plain(self.market_state) if self.market_state is not None else None,
            "pbd_roots": [_plain(x) for x in self.pbd_roots],
            "leaf_payloads": {
                k: _plain(self.leaf_payloads[k])
                for k in sorted(self.leaf_payloads)
            },
            "decision_cut": self.decision_cut,
            "stripped_fields": list(self.stripped_fields),
        }


@dataclass(frozen=True)
class FactLog:
    """fact_log.v1 envelope. Records are immutable after append."""

    records: tuple[Mapping[str, Any], ...]
    stripped_fields: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA_NAME_LOG,
            "authority": AUTHORITY,
            "prophet_flags": dict(PROPHET_FLAGS),
            "unsolicited_instruction_detected": False,
            "records": [_plain(r) for r in self.records],
        }


@dataclass(frozen=True)
class ThesisView:
    """thesis_view.v1 derived fold. Identity = (company_id, original_proposition_fact_id)."""

    payload: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return _plain(self.payload)


# --------------------------------------------------------------------------- canonical JSON / hashing (W3-R2)


def canonical_json(obj: Any) -> str:
    """Canonical JSON: sorted keys, tight separators, UTF-8, no NaN."""
    return json.dumps(
        _jsonable(obj),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def canonical_json_sha256(obj: Any) -> str:
    return sha256(canonical_json(obj).encode("utf-8")).hexdigest()


def quantity_fingerprint(
    payload: Mapping[str, Any] | None,
    template: str,
) -> dict[str, Any]:
    """sha256 of canonical JSON of the live template's critical numeric slots.

    Section 7 default 7: T1 incremental/remaining/executed; T2 stated_amount;
    T3 stated_quantity. Cosmetic text is outside the fingerprint.
    """
    if not payload:
        return {"form": "absent"}
    keys: tuple[str, ...]
    if template == "capital_allocation_event.v1":
        keys = ("incremental", "remaining", "executed")
    elif template == "demand_guidance_contract_event.v1":
        keys = ("stated_amount",)
    elif template == "strategic_product_partnership_event.v1":
        keys = ("stated_quantity",)
    else:
        keys = ()
    slots: dict[str, Any] = {}
    for key in keys:
        if key in payload and payload[key] is not None:
            slots[key] = payload[key]
    if not slots:
        return {"form": "absent"}
    return {"form": "present", "canonical_sha256": canonical_json_sha256(slots)}


def assign_polarity(
    negated: bool,
    contrary_mechanism_quote: Mapping[str, Any] | None,
) -> str:
    """Section 7 default 5: unclassified unless negated or span-backed contrary quote."""
    if negated:
        return "contrary"
    if contrary_mechanism_quote:
        return "contrary"
    return "unclassified"


# --------------------------------------------------------------------------- schema load (lazy, path-parameterised)


def load_schema(name: str, path: Path | str | None = None) -> dict[str, Any]:
    """Load a contracts_w3 schema. Default path is relative to this module.

    ``Path(__file__).resolve().parents[2] / "contracts" / "news_impact" / name``.
    Read lazily inside this function; no module-level I/O.
    """
    if path is not None:
        p = Path(path)
    else:
        p = Path(__file__).resolve().parents[2] / "contracts" / "news_impact" / name
    return json.loads(p.read_text(encoding="utf-8"))


def validate_against_schema(
    instance: Mapping[str, Any],
    schema_name: str,
    path: Path | str | None = None,
) -> None:
    """Raise ThesisError(SCHEMA_VIOLATION) if instance does not match schema."""
    schema = load_schema(schema_name, path)
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(instance), key=lambda e: list(map(str, e.absolute_path)))
    if errors:
        err = errors[0]
        loc = "/".join(str(p) for p in err.absolute_path)
        raise ThesisError("SCHEMA_VIOLATION", f"{loc}: {err.message}")


# --------------------------------------------------------------------------- JSONL serialize / parse (strings and iterables; never a file)


def serialize_jsonl(records: Iterable[Mapping[str, Any]]) -> str:
    """Serialize log records as JSONL (one canonical record per line)."""
    lines: list[str] = []
    for rec in records:
        cleaned, _ = _strip_forbidden(rec)
        lines.append(canonical_json(cleaned))
    return "\n".join(lines) + ("\n" if lines else "")


def parse_jsonl(
    source: str | Iterable[str],
    *,
    log_path: str = DEFAULT_LOG_PATH,
) -> dict[str, Any]:
    """Parse JSONL records or a whole fact_log.v1 object into a fact_log.v1 dict.

    ``log_path`` is documentation only (default ``data/news_impact/fact_log.jsonl``)
    and is never read or written.
    """
    del log_path  # documentation only
    if isinstance(source, str):
        stripped = source.strip()
        if stripped.startswith("{") and '"records"' in stripped and "\n" not in stripped.strip():
            try:
                obj = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ThesisError("JSONL_PARSE_ERROR", str(exc)) from exc
            if isinstance(obj, dict) and "records" in obj:
                return _normalize_log(obj)
        lines: list[str] = source.splitlines()
    else:
        lines = [str(x) for x in source]
    # Whole-document JSON (pretty-printed fact_log.v1) is accepted as a parse
    # convenience; JSONL is the stored form.
    joined = "\n".join(lines).strip()
    if joined.startswith("{") and '"schema"' in joined and '"records"' in joined:
        try:
            obj = json.loads(joined)
        except json.JSONDecodeError:
            obj = None
        if isinstance(obj, dict) and obj.get("schema") == SCHEMA_NAME_LOG:
            return _normalize_log(obj)
    records: list[dict[str, Any]] = []
    for idx, line in enumerate(lines):
        text = line.strip()
        if not text:
            continue
        try:
            rec = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ThesisError("JSONL_PARSE_ERROR", f"line {idx + 1}: {exc}") from exc
        if not isinstance(rec, dict):
            raise ThesisError("JSONL_PARSE_ERROR", f"line {idx + 1}: record is not an object")
        records.append(rec)
    return _normalize_log(
        {
            "schema": SCHEMA_NAME_LOG,
            "authority": AUTHORITY,
            "prophet_flags": dict(PROPHET_FLAGS),
            "unsolicited_instruction_detected": False,
            "records": records,
        }
    )


def parse_fact_log(obj: Mapping[str, Any] | FactLog | str | Iterable[str]) -> dict[str, Any]:
    """Normalize any accepted log input to a fact_log.v1 dict and validate it."""
    if isinstance(obj, FactLog):
        log = obj.to_dict()
    elif isinstance(obj, str) or _is_iterable_of_str(obj):
        log = parse_jsonl(obj)  # type: ignore[arg-type]
    elif isinstance(obj, Mapping):
        log = _normalize_log(obj)
    else:
        raise ThesisError("SCHEMA_VIOLATION", f"unsupported fact_log type {type(obj)!r}")
    validate_log(log)
    return log


# --------------------------------------------------------------------------- append-only


def check_append_only(prior: Mapping[str, Any], candidate: Mapping[str, Any]) -> None:
    """Refuse a candidate whose prior prefix was mutated, reordered, or deleted."""
    prior_recs = list(prior.get("records") or [])
    cand_recs = list(candidate.get("records") or [])
    if len(cand_recs) < len(prior_recs):
        raise ThesisError(
            "APPEND_ONLY_VIOLATION",
            "candidate deletes records relative to the supplied prior prefix",
        )
    for i, rec in enumerate(prior_recs):
        if canonical_json(cand_recs[i]) != canonical_json(rec):
            raise ThesisError(
                "APPEND_ONLY_VIOLATION",
                f"record at index {i} was mutated or reordered relative to the prior prefix",
            )


def append_records(
    prior: Mapping[str, Any] | FactLog,
    new_records: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Return a new fact_log.v1 with ``new_records`` appended (new log_seq)."""
    log = prior.to_dict() if isinstance(prior, FactLog) else _normalize_log(prior)
    validate_log(log)
    records = [_plain(r) for r in log["records"]]
    next_seq = len(records) + 1
    for raw in new_records:
        cleaned, _stripped = _strip_forbidden(raw)
        rec = _plain(cleaned)
        rec["log_seq"] = next_seq
        next_seq += 1
        records.append(rec)
    out = {
        "schema": SCHEMA_NAME_LOG,
        "authority": AUTHORITY,
        "prophet_flags": dict(PROPHET_FLAGS),
        "unsolicited_instruction_detected": False,
        "records": records,
    }
    validate_log(out)
    return out


def validate_log(log: Mapping[str, Any]) -> None:
    """Named validators V_LOG_SEQ, V_FACT_ID_UNIQUE, V_SUPERSEDES_*, V_PIT_CLOCKS, V_MANIFEST_POINTS, V_TEXT_SAFE."""
    if not isinstance(log, Mapping):
        raise ThesisError("SCHEMA_VIOLATION", "fact_log is not an object")
    records = list(log.get("records") or [])
    for i, rec in enumerate(records, start=1):
        if rec.get("log_seq") != i:
            raise ThesisError(
                "LOG_SEQ_INVALID",
                f"log_seq must be 1-based dense; expected {i} got {rec.get('log_seq')!r}",
            )
    seen_ids: dict[str, int] = {}
    by_id: dict[str, Mapping[str, Any]] = {}
    for rec in records:
        fid = rec.get("fact_id")
        if not isinstance(fid, str):
            raise ThesisError("SCHEMA_VIOLATION", "fact_id missing")
        if fid in seen_ids:
            raise ThesisError("DUPLICATE_FACT_ID", f"duplicate fact_id {fid}")
        seen_ids[fid] = rec["log_seq"]
        by_id[fid] = rec
        _check_text_safe_record(rec)
        _check_pit_clocks(rec)
        novelty = rec.get("novelty")
        supersedes = rec.get("supersedes_fact_id")
        if novelty == "corrected_fact":
            if not isinstance(supersedes, str) or not supersedes:
                raise ThesisError(
                    "SUPERSEDES_REQUIRED",
                    f"{fid}: novelty=corrected_fact requires supersedes_fact_id",
                )
            if supersedes == fid:
                raise ThesisError("SUPERSEDES_CYCLE", f"{fid} supersedes itself")
            if supersedes not in by_id or by_id[supersedes]["log_seq"] >= rec["log_seq"]:
                raise ThesisError(
                    "SUPERSEDES_NOT_FOUND",
                    f"{fid}: supersedes_fact_id {supersedes} is not an earlier record",
                )
            if _fact_key(by_id[supersedes]) != _fact_key(rec):
                raise ThesisError(
                    "SUPERSEDES_KEY_MISMATCH",
                    f"{fid}: supersedes target has a different fact_key",
                )
            _check_supersedes_cycle(rec, by_id)
        kind = rec.get("record_kind")
        if kind == "manifestation":
            reports = rec.get("reports_fact_id")
            if not isinstance(reports, str) or reports not in by_id:
                raise ThesisError(
                    "MANIFEST_REPORTS_MISSING",
                    f"{fid}: manifestation reports_fact_id {reports!r} is not in the log",
                )
    envelope = {
        "schema": log.get("schema", SCHEMA_NAME_LOG),
        "authority": log.get("authority", AUTHORITY),
        "prophet_flags": log.get("prophet_flags", dict(PROPHET_FLAGS)),
        "unsolicited_instruction_detected": log.get("unsolicited_instruction_detected", False),
        "records": records,
    }
    validate_against_schema(envelope, "fact_log.v1.schema.json")


# --------------------------------------------------------------------------- projector F


def project(
    fact_log: Mapping[str, Any] | FactLog | str | Iterable[str],
    owner_snapshot: Mapping[str, Any] | OwnerSnapshot | None,
    as_of_utc: str,
    *,
    prior_as_of_utc: str | None = None,
    prior_owners: Mapping[str, Any] | OwnerSnapshot | None = None,
    decision_cut: str | None = None,
) -> tuple[dict[str, Any], ...]:
    """Pure projector F(fact_log, owner_snapshot, as_of_utc) -> thesis views.

    Returns one thesis_view.v1 dict per (company_id, original_proposition_fact_id),
    sorted. When as_of_utc is earlier than every fact, the tuple is empty; callers
    that need the typed absence use :func:`absent_thesis`.
    """
    _parse_dt(as_of_utc, code="AS_OF_INVALID")
    log = parse_fact_log(fact_log)
    owners = _coerce_owners(owner_snapshot)
    cut = decision_cut or owners.decision_cut
    if cut is not None and _parse_dt(cut) > _parse_dt(as_of_utc):
        raise ThesisError(
            "DECISION_CUT_AFTER_AS_OF",
            f"decision_cut {cut} is after as_of_utc {as_of_utc}",
        )
    views = _project_views(log, owners, as_of_utc, decision_cut=cut)
    if prior_as_of_utc is not None:
        prior_o = _coerce_owners(prior_owners) if prior_owners is not None else owners
        prior_cut = prior_o.decision_cut or cut
        prior_views = _project_views(log, prior_o, prior_as_of_utc, decision_cut=prior_cut)
        prior_index = {
            (v["company_id"], v["original_proposition_fact_id"]): v for v in prior_views
        }
        filled: list[dict[str, Any]] = []
        for view in views:
            key = (view["company_id"], view["original_proposition_fact_id"])
            triggers = _material_delta_triggers(
                log,
                owners,
                prior_o,
                view,
                prior_index.get(key),
                as_of_utc,
                prior_as_of_utc,
            )
            view = dict(view)
            view["material_delta_triggers"] = triggers
            filled.append(view)
        views = filled
    log_sha = canonical_json_sha256(log)
    owners_sha = canonical_json_sha256(owners.to_dict())
    out: list[dict[str, Any]] = []
    for view in views:
        payload = dict(view)
        payload["log_sha256"] = log_sha
        payload["owners_sha256"] = owners_sha
        payload["as_of_utc"] = as_of_utc
        if cut is not None:
            payload["decision_cut"] = cut
        validate_against_schema(payload, "thesis_view.v1.schema.json")
        _assert_no_forbidden(payload)
        out.append(payload)
    return tuple(out)


def F(
    fact_log: Mapping[str, Any] | FactLog | str | Iterable[str],
    owner_snapshot: Mapping[str, Any] | OwnerSnapshot | None,
    as_of_utc: str,
    **kwargs: Any,
) -> tuple[dict[str, Any], ...]:
    """Alias of :func:`project` (design section 4.11)."""
    return project(fact_log, owner_snapshot, as_of_utc, **kwargs)


def project_one(
    fact_log: Mapping[str, Any] | FactLog | str | Iterable[str],
    owner_snapshot: Mapping[str, Any] | OwnerSnapshot | None,
    as_of_utc: str,
    company_id: str,
    original_proposition_fact_id: str,
    **kwargs: Any,
) -> dict[str, Any]:
    """Project a single view key; typed field_absence.v1 when nothing is visible."""
    views = project(fact_log, owner_snapshot, as_of_utc, **kwargs)
    for view in views:
        if (
            view["company_id"] == company_id
            and view["original_proposition_fact_id"] == original_proposition_fact_id
        ):
            return view
    return absent_thesis(as_of_utc=as_of_utc, company_id=company_id)


def absent_thesis(*, as_of_utc: str, company_id: str | None = None) -> dict[str, Any]:
    """Typed empty/absent view named by section 4.5: field_absence.v1 reason not_stated."""
    detail = "no fact with observed_at at or before as_of_utc"
    if company_id:
        detail = f"{detail} for {company_id}"
    return FieldAbsence(
        subject="thesis_view",
        detail=detail,
        missing_fields=("thesis_view",),
        reason="not_stated",
    ).to_dict()


def live_payload(
    fact_key: Mapping[str, Any],
    log: Mapping[str, Any],
    as_of_utc: str,
) -> Mapping[str, Any] | dict[str, Any]:
    """Section 4.5 live_payload(key, log, as_of). Absence if the slot is empty."""
    rec = _live_record_for_key(fact_key, list(log.get("records") or []), as_of_utc)
    if rec is None:
        return FieldAbsence(
            subject="live_payload",
            detail="no live fact_revision for this fact_key at as_of_utc",
            missing_fields=("live_payload",),
        ).to_dict()
    return rec


# --------------------------------------------------------------------------- internal fold


def _project_views(
    log: Mapping[str, Any],
    owners: OwnerSnapshot,
    as_of_utc: str,
    *,
    decision_cut: str | None,
) -> list[dict[str, Any]]:
    records = [
        r
        for r in log["records"]
        if _parse_dt(r["observed_at"]) <= _parse_dt(as_of_utc)
    ]
    records = sorted(records, key=lambda r: (_parse_dt(r["observed_at"]), r["fact_id"]))
    if not records:
        return []
    by_id = {r["fact_id"]: r for r in records}
    _, live_ids = _live_sets(records)
    # Original proposition = earliest fact_revision of a proposition kind in each
    # supersedes-root chain (section 7 default 6: one view per original id).
    seeds: dict[str, Mapping[str, Any]] = {}
    for rec in records:
        if rec.get("record_kind") != "fact_revision":
            continue
        kind = (rec.get("fact_key") or {}).get("slot", {}).get("kind")
        if kind not in PROPOSITION_KINDS:
            continue
        root_id = _root_fact_id(rec, by_id)
        if root_id not in seeds:
            seeds[root_id] = by_id.get(root_id, rec)
    views: list[dict[str, Any]] = []
    for root_id in sorted(seeds, key=lambda i: (seeds[i]["company_id"], i)):
        root = seeds[root_id]
        company_id = root["company_id"]
        attached = _attached_records(root_id, records, by_id)
        live_attached = [
            r
            for r in attached
            if r.get("record_kind") == "fact_revision"
            and r["fact_id"] in live_ids
        ]
        # Live proposition record (latest non-superseded on the original key).
        live_prop = _live_record_for_key(_fact_key(root), records, as_of_utc)
        if live_prop is None:
            live_prop = root
        cut = decision_cut or root["observed_at"]
        view = _fill_view(
            company_id=company_id,
            original_id=root_id,
            root=root,
            live_prop=live_prop,
            attached=attached,
            live_attached=live_attached,
            owners=owners,
            as_of_utc=as_of_utc,
            decision_cut=cut,
        )
        views.append(view)
    views.sort(key=lambda v: (v["company_id"], v["original_proposition_fact_id"]))
    return views


def _fill_view(
    *,
    company_id: str,
    original_id: str,
    root: Mapping[str, Any],
    live_prop: Mapping[str, Any],
    attached: Sequence[Mapping[str, Any]],
    live_attached: Sequence[Mapping[str, Any]],
    owners: OwnerSnapshot,
    as_of_utc: str,
    decision_cut: str,
) -> dict[str, Any]:
    payload = _leaf_payload(owners, live_prop["fact_id"])
    template = live_prop.get("payload_schema") or root.get("payload_schema")
    proposition = _original_proposition(live_prop, payload, template)
    supporting, contrary = _claim_ids(live_attached, attached)
    families = _root_source_families(attached)
    exposure = _exposure_paths(owners, company_id)
    assumptions = _required_assumptions(template, payload, owners)
    milestones = _milestone_evidence(root, live_prop, live_attached, attached)
    next_obs = _next_expected(template, live_prop, attached, milestones)
    deadline = _deadline(live_attached, live_prop)
    weakening = _weakening_conditions(
        as_of_utc, deadline, next_obs, milestones, live_attached, attached, payload, owners
    )
    display = _display(
        template, live_prop, payload, next_obs, deadline, weakening, milestones, contrary
    )
    live_fact_ids = sorted(
        {
            r["fact_id"]
            for r in live_attached
            if r.get("record_kind") == "fact_revision"
        }
    )
    cluster_ids = sorted({r["cluster_id"] for r in attached if r.get("cluster_id")})
    group_ids = sorted({_provenance_group_id(r) for r in attached if _provenance_group_id(r)})
    return {
        "schema": SCHEMA_NAME_VIEW,
        "authority": AUTHORITY,
        "prophet_flags": dict(PROPHET_FLAGS),
        "unsolicited_instruction_detected": False,
        "company_id": company_id,
        "original_proposition_fact_id": original_id,
        "decision_cut": decision_cut,
        "as_of_utc": as_of_utc,
        "original_proposition": proposition,
        "supporting_claim_ids": supporting,
        "contrary_claim_ids": contrary,
        "root_source_families": families,
        "exposure_paths": exposure,
        "required_assumptions": assumptions,
        "current_milestone_evidence": milestones,
        "next_expected_observation": next_obs,
        "deadline": deadline,
        "weakening_conditions": weakening,
        "display": display,
        "live_fact_ids": live_fact_ids,
        "cluster_ids": cluster_ids,
        "provenance_group_ids": group_ids,
        "material_delta_triggers": [],
        "log_sha256": "0" * 64,
        "owners_sha256": "0" * 64,
    }


def _original_proposition(
    live_prop: Mapping[str, Any],
    payload: Mapping[str, Any],
    template: str,
) -> dict[str, Any]:
    slot = (live_prop.get("fact_key") or {}).get("slot") or {}
    negated = bool(payload.get("negated", False))
    status = payload.get("commitment_status")
    if not isinstance(status, str):
        if slot.get("kind") == "t1_authorization_program":
            status = "authorized"
        elif slot.get("kind") == "t1_execution_under_program":
            status = "executed"
        else:
            status = "announced"
    channel = payload.get("channel_hint") or TEMPLATE_CHANNEL.get(template, "market_only")
    statement = payload.get("plain_statement")
    if not isinstance(statement, str) or not statement:
        statement = _plain_statement(template, slot, payload)
    return {
        "payload_schema": template,
        "plain_statement": statement,
        "channel_hint": channel,
        "commitment_status": status,
        "negated": negated,
    }


def _plain_statement(
    template: str, slot: Mapping[str, Any], payload: Mapping[str, Any]
) -> str:
    if template == "capital_allocation_event.v1":
        inc = _billions(payload.get("incremental"))
        rem = _billions(payload.get("remaining"))
        horizon = str(slot.get("horizon_token") or payload.get("horizon_token") or "")
        year = horizon[2:] if horizon.startswith("FY") else horizon
        action = slot.get("action_type") or "share_repurchase"
        action_words = str(action).replace("_", " ")
        if inc is not None and rem is not None and year:
            return (
                f"Issuer authorized an additional {inc} billion dollars of {action_words}, "
                f"remaining authorization {rem} billion dollars, through fiscal {year}. "
                "Authorization is not execution."
            )
        return "Issuer authorized a capital allocation action. Authorization is not execution."
    if template == "strategic_product_partnership_event.v1":
        obj = slot.get("object_name") or payload.get("object_name") or "the stated object"
        return f"Issuer announced {obj}."
    if template == "demand_guidance_contract_event.v1":
        metric = slot.get("metric") or "the stated metric"
        return f"Issuer stated {metric}."
    return "the source states a proposition. Authorization is not execution."


def _claim_ids(
    live_attached: Sequence[Mapping[str, Any]],
    attached: Sequence[Mapping[str, Any]],
) -> tuple[list[str], list[str]]:
    supporting: set[str] = set()
    contrary: set[str] = set()
    # Live fact_revisions contribute polarity; manifestations of those facts
    # contribute owner_claim_ids of the same polarity (Case 1: one supporting
    # claim plus the live fact_id, not one claim per reprint).
    live_rev = [r for r in live_attached if r.get("record_kind") == "fact_revision"]
    for rec in live_rev:
        pol = rec.get("polarity") or "unclassified"
        bucket = supporting if pol == "supporting" else contrary if pol == "contrary" else None
        if bucket is None:
            continue
        for cid in rec.get("owner_claim_ids") or []:
            bucket.add(cid)
        bucket.add(rec["fact_id"])
    return sorted(supporting), sorted(contrary)


def _root_source_families(attached: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, list[Mapping[str, Any]]] = {}
    for rec in attached:
        gid = _provenance_group_id(rec)
        if not gid:
            continue
        groups.setdefault(gid, []).append(rec)
    families: list[dict[str, Any]] = []
    for gid in sorted(groups):
        members = sorted(groups[gid], key=lambda r: (_parse_dt(r["observed_at"]), r["fact_id"]))
        # Prefer the origin document's own source_family (issuer_primary over reprints).
        origin = members[0]
        for rec in members:
            if rec.get("provenance", {}).get("source_family") == "issuer_primary":
                origin = rec
                break
        prov = origin.get("provenance") or {}
        root_family_id = prov.get("root_family_id")
        origin_document_id = prov.get("origin_document_id")
        if not isinstance(root_family_id, str):
            root_family_id = gid
        if not isinstance(origin_document_id, str):
            origin_document_id = gid
        families.append(
            {
                "root_family_id": root_family_id,
                "origin_document_id": origin_document_id,
                "source_family": prov.get("source_family") or "unknown",
                "member_count": len(members),
            }
        )
    families.sort(key=lambda f: (f["root_family_id"], f["origin_document_id"]))
    return families


def _exposure_paths(owners: OwnerSnapshot, company_id: str) -> list[dict[str, Any]] | dict[str, Any]:
    rows = [
        _plain(r)
        for r in owners.relationship_candidates
        if isinstance(r, Mapping)
        and (
            r.get("company_id") == company_id
            or r.get("source_company_id") == company_id
            or r.get("target_company_id") == company_id
        )
    ]
    if not rows:
        return FieldAbsence(
            subject="exposure_paths",
            detail="no relationship_candidate row and PR 6514 remains blocked",
            missing_fields=("exposure_paths",),
        ).to_dict()
    paths: list[dict[str, Any]] = []
    for row in sorted(rows, key=lambda r: canonical_json(r)):
        target = row.get("target_company_id") or row.get("company_id") or company_id
        paths.append(
            {
                "target_company_id": target,
                "role": row.get("role") or "subject",
                "direction": row.get("direction") or "unknown",
                "mechanism_or_absence": row.get("mechanism")
                or row.get("mechanism_or_absence")
                or FieldAbsence(
                    subject="mechanism",
                    detail="relationship_candidate does not state a mechanism",
                    missing_fields=("mechanism",),
                ).to_dict(),
            }
        )
    return paths


def _required_assumptions(
    template: str,
    payload: Mapping[str, Any],
    owners: OwnerSnapshot,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if template == "capital_allocation_event.v1":
        if payload.get("executed_amount") is None and payload.get("executed") is None:
            out.append(
                FieldAbsence(
                    subject="executed_amount",
                    detail="authorization packet does not state completed purchases",
                    missing_fields=("executed_amount",),
                ).to_dict()
            )
    elif template == "demand_guidance_contract_event.v1":
        if payload.get("stated_amount") is None:
            out.append(
                FieldAbsence(
                    subject="stated_amount",
                    detail="demand or guidance packet does not state an amount",
                    missing_fields=("stated_amount",),
                ).to_dict()
            )
    elif template == "strategic_product_partnership_event.v1":
        if payload.get("stated_quantity") is None:
            out.append(
                FieldAbsence(
                    subject="stated_quantity",
                    detail="open-model or partnership packet does not state a quantity",
                    missing_fields=("stated_quantity",),
                ).to_dict()
            )
        if not _has_baseline(owners):
            out.append(
                FieldAbsence(
                    subject="baseline",
                    detail=(
                        "no prior_guidance, prior_reported_period, or "
                        "prior_announced_programme is in the owner snapshot; "
                        "surprise is unmeasured"
                    ),
                    missing_fields=("baseline",),
                ).to_dict()
            )
    return out


def _has_baseline(owners: OwnerSnapshot) -> bool:
    for key in ("prior_guidance", "prior_reported_period", "prior_announced_programme"):
        if key in owners.identity_map and owners.identity_map[key]:
            return True
    for item in list(owners.guidance) + list(owners.facts):
        if isinstance(item, Mapping) and item:
            return True
    return False


def _milestone_evidence(
    root: Mapping[str, Any],
    live_prop: Mapping[str, Any],
    live_attached: Sequence[Mapping[str, Any]],
    attached: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    # The original (or live) proposition itself is the announcement milestone.
    items.append(
        {
            "fact_id": root["fact_id"],
            "milestone_name": "announcement",
            "observed_at": root["observed_at"],
            "provenance_group_id": _provenance_group_id(root),
        }
    )
    seen = {("announcement", root["fact_id"])}
    for rec in live_attached:
        slot = (rec.get("fact_key") or {}).get("slot") or {}
        if slot.get("kind") == "milestone_under_proposition":
            name = slot.get("milestone_name")
            if not isinstance(name, str):
                continue
            key = (name, rec["fact_id"])
            if key in seen:
                continue
            seen.add(key)
            items.append(
                {
                    "fact_id": rec["fact_id"],
                    "milestone_name": name,
                    "observed_at": rec["observed_at"],
                    "provenance_group_id": _provenance_group_id(rec),
                }
            )
        elif rec.get("novelty") == "independently_observed_milestone" and rec["fact_id"] != root["fact_id"]:
            name = slot.get("milestone_name") or "other_stated_milestone"
            key = (name, rec["fact_id"])
            if key in seen:
                continue
            seen.add(key)
            items.append(
                {
                    "fact_id": rec["fact_id"],
                    "milestone_name": name,
                    "observed_at": rec["observed_at"],
                    "provenance_group_id": _provenance_group_id(rec),
                }
            )
    items.sort(key=lambda m: (_parse_dt(m["observed_at"]), m["fact_id"], m["milestone_name"]))
    return items


def _next_expected(
    template: str,
    live_prop: Mapping[str, Any],
    attached: Sequence[Mapping[str, Any]],
    milestones: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    observed = {m["milestone_name"] for m in milestones}
    ladder = TEMPLATE_LADDER.get(template, T1_LADDER)
    # Prefer an explicit next_expected_observation on the latest attached record
    # that carries one (proposition or thesis_link).
    explicit = None
    for rec in sorted(attached, key=lambda r: (_parse_dt(r["observed_at"]), r["fact_id"])):
        neo = rec.get("next_expected_observation")
        if isinstance(neo, Mapping) and "milestone_name" in neo:
            explicit = neo
    # After a later ladder milestone is observed, advance past the furthest
    # observed (Case 2: independent_deployment → repeated_active_use).
    furthest = -1
    for i, name in enumerate(ladder):
        if name in observed:
            furthest = i
    if furthest >= 0 and furthest + 1 < len(ladder):
        nxt = ladder[furthest + 1]
        window = _window_from_explicit(explicit) if explicit else {}
        # Keep the explicit window when the explicit name matches, or when the
        # live proposition still carries the next-watch window (Case 1).
        if explicit and explicit.get("milestone_name") == nxt:
            return _plain(explicit)
        if explicit and nxt == "executed_repurchase":
            # Case 1: live proposition names executed_repurchase with windows.
            if explicit.get("milestone_name") == "executed_repurchase" or live_prop.get(
                "next_expected_observation"
            ):
                neo = live_prop.get("next_expected_observation")
                if isinstance(neo, Mapping) and neo.get("milestone_name") == nxt:
                    return _plain(neo)
        out: dict[str, Any] = {"milestone_name": nxt}
        out.update(window)
        return out
    if explicit and explicit.get("milestone_name") not in observed:
        return _plain(explicit)
    for name in ladder:
        if name not in observed:
            return {"milestone_name": name}
    return FieldAbsence(
        subject="next_expected_observation",
        detail="every milestone in the template bundle has been observed in this store",
        missing_fields=("next_expected_observation",),
    ).to_dict()


def _window_from_explicit(explicit: Mapping[str, Any] | None) -> dict[str, str]:
    if not explicit:
        return {}
    out: dict[str, str] = {}
    if isinstance(explicit.get("window_start"), str):
        out["window_start"] = explicit["window_start"]
    if isinstance(explicit.get("window_end"), str):
        out["window_end"] = explicit["window_end"]
    return out


def _deadline(
    live_attached: Sequence[Mapping[str, Any]],
    live_prop: Mapping[str, Any],
) -> str | dict[str, Any]:
    times: list[str] = []
    for rec in list(live_attached) + [live_prop]:
        raw = rec.get("stated_deadline")
        if isinstance(raw, str):
            times.append(raw)
    if times:
        return max(times, key=_parse_dt)
    raw = live_prop.get("stated_deadline")
    if isinstance(raw, Mapping) and raw.get("schema") == "field_absence.v1":
        return _plain(raw)
    return FieldAbsence(
        subject="stated_deadline",
        detail="no source-stated deadline is in the live facts",
        missing_fields=("stated_deadline",),
    ).to_dict()


def _weakening_conditions(
    as_of_utc: str,
    deadline: str | Mapping[str, Any],
    next_obs: Mapping[str, Any],
    milestones: Sequence[Mapping[str, Any]],
    live_attached: Sequence[Mapping[str, Any]],
    attached: Sequence[Mapping[str, Any]],
    payload: Mapping[str, Any],
    owners: OwnerSnapshot,
) -> list[dict[str, Any]]:
    observed = {m["milestone_name"] for m in milestones}
    as_of = _parse_dt(as_of_utc)
    out: list[dict[str, Any]] = []
    deadline_str = deadline if isinstance(deadline, str) else None
    next_name = next_obs.get("milestone_name") if isinstance(next_obs, Mapping) else None
    next_absent = isinstance(next_name, str) and next_name not in observed

    if deadline_str:
        armed = as_of > _parse_dt(deadline_str) and next_absent
        evidence = [r["fact_id"] for r in live_attached if isinstance(r.get("stated_deadline"), str)]
        out.append(
            {
                "code": "missed_stated_deadline",
                "armed": armed,
                "evidence_fact_ids": sorted(evidence) if armed else [],
            }
        )

    if isinstance(next_obs, Mapping) and "milestone_name" in next_obs and next_obs.get("schema") != "field_absence.v1":
        window_end = next_obs.get("window_end")
        armed = False
        if isinstance(window_end, str) and next_absent:
            armed = as_of > _parse_dt(window_end)
        evidence = []
        if armed:
            evidence = sorted(m["fact_id"] for m in milestones)
        out.append(
            {
                "code": "expected_observation_absent",
                "armed": armed,
                "evidence_fact_ids": evidence,
            }
        )

    corrections = [
        r
        for r in attached
        if r.get("novelty") == "corrected_fact" and r.get("record_kind") == "fact_revision"
    ]
    if corrections:
        live_corrections = [
            r for r in live_attached
            if r.get("novelty") == "corrected_fact"
            and r.get("record_kind") == "fact_revision"
        ]
        evidence_ids = _magnitude_reduction_evidence(live_corrections, owners)
        out.append(
            {
                "code": "source_correction_reduces_magnitude",
                "armed": bool(evidence_ids),
                "evidence_fact_ids": evidence_ids,
            }
        )

    contrary = [
        r
        for r in live_attached
        if r.get("polarity") == "contrary" and r.get("record_kind") == "fact_revision"
    ]
    if contrary:
        out.append(
            {
                "code": "contrary_independent_measurement",
                "armed": True,
                "evidence_fact_ids": sorted(r["fact_id"] for r in contrary),
            }
        )

    if payload.get("commitment_status") == "withdrawn":
        out.append(
            {
                "code": "commitment_withdrawn",
                "armed": True,
                "evidence_fact_ids": sorted(r["fact_id"] for r in live_attached),
            }
        )

    return out


def _finite_nonnegative_amount(value: Any) -> bool:
    return (
        type(value) in (int, float)
        and (type(value) is int or isfinite(value))
        and 0 <= value <= 1_000_000_000_000_000
    )


def _magnitude_reduction_evidence(
    corrections: Sequence[Mapping[str, Any]],
    owners: OwnerSnapshot,
) -> list[str]:
    """Current corrections with a lower exact amount than their direct predecessor.

    Only producer-preserved canonical monetary points can qualify. Legacy scalar
    leaves and fingerprints do not establish units, scope or numerical direction.
    """
    monetary_keys = {
        "capital_allocation_event.v1": ("remaining", "incremental", "executed"),
        "demand_guidance_contract_event.v1": ("stated_amount",),
    }
    candidates = []
    for rec in corrections:
        prior_id = rec.get("supersedes_fact_id")
        if not isinstance(prior_id, str) or prior_id == rec["fact_id"]:
            continue
        prior = _leaf_payload(owners, prior_id)
        current = _leaf_payload(owners, rec["fact_id"])
        old_terms = prior.get("quantity_terms")
        new_terms = current.get("quantity_terms")
        if not isinstance(old_terms, Mapping) or not isinstance(new_terms, Mapping):
            continue
        if prior.get("negated") is not False or current.get("negated") is not False:
            continue
        # These existing leaf fields are negative evidence when inconsistent.
        if prior.get("horizon_token") != current.get("horizon_token"):
            continue
        template = rec.get("payload_schema")
        if prior.get("template") != template or current.get("template") != template:
            continue
        keys = monetary_keys.get(template, ())
        for key in keys:
            old, new = old_terms.get(key), new_terms.get(key)
            if not isinstance(old, Mapping) or not isinstance(new, Mapping):
                continue
            candidates.append((rec["fact_id"], key, prior, current, old, new))
    if not candidates:
        return []

    contract = load_schema("news_impact_event.v1.schema.json")
    validator = Draft202012Validator({
        "$defs": contract["$defs"],
        "$ref": "#/$defs/quantity_point",
    })
    qualified: set[str] = set()
    for fact_id, key, prior, current, old, new in candidates:
        if not validator.is_valid(old) or not validator.is_valid(new):
            continue
        if old["bound"] != "exact" or new["bound"] != "exact":
            continue
        if old["negated"] is not False or new["negated"] is not False:
            continue
        values = (old["value"], new["value"], prior.get(key), current.get(key))
        if not all(_finite_nonnegative_amount(value) for value in values):
            continue
        if prior[key] != old["value"] or current[key] != new["value"]:
            continue
        # Initial supported unit is the explicit base currency, e.g. USD.
        # Scaled/free-text units need a separate qualified normalization policy.
        currency = old["currency"]
        if not re.fullmatch(r"[A-Z]{3}", currency) or old["unit"] != currency:
            continue
        if any(old[field] != new[field] for field in ("unit", "currency", "basis", "period")):
            continue
        if old["basis"] not in {"total", "incremental"}:
            continue  # no rate, percentage or per-share denominator is inferred
        period = old["period"]
        if period.get("period_kind") not in {"fiscal_year", "quarter"}:
            continue  # equal absences or partial windows do not establish scope
        if "end_year" in period:
            continue
        if period["calendar_end"] is not None:
            try:
                date.fromisoformat(period["calendar_end"])
            except ValueError:
                continue
        if new["value"] < old["value"]:
            qualified.add(fact_id)
    return sorted(qualified)


def _display(
    template: str,
    live_prop: Mapping[str, Any],
    payload: Mapping[str, Any],
    next_obs: Mapping[str, Any],
    deadline: str | Mapping[str, Any],
    weakening: Sequence[Mapping[str, Any]],
    milestones: Sequence[Mapping[str, Any]],
    contrary: Sequence[str],
) -> dict[str, Any]:
    slot = (live_prop.get("fact_key") or {}).get("slot") or {}
    horizon = str(slot.get("horizon_token") or "")
    year = horizon[2:] if horizon.startswith("FY") else horizon
    windows = _display_windows(next_obs, deadline, live_prop, year)

    if live_prop.get("novelty") == "corrected_fact":
        subject = (
            "the repurchase disclosure"
            if slot.get("action_type") == "share_repurchase"
            else "this disclosure"
        )
        return {
            "what_we_are_watching": "Review the corrected terms and their supporting source records.",
            "windows": windows,
            "plain_status": f"A source correction is available for {subject}.",
        }

    if contrary:
        obj = slot.get("object_name") or "the stated object"
        watching = (
            "what we are watching is whether subsequent independent sources continue to "
            "report NVIDIA-hardware deployments or non-NVIDIA deployments, in the next "
            "two reporting windows. this store does not state which measurement is true."
            if obj == "Nemotron 3"
            else (
                "what we are watching is whether subsequent independent sources continue "
                "to report supporting or contrary measurements, in the next two reporting "
                "windows. this store does not state which measurement is true."
            )
        )
        status = (
            "the source states a proposition. a separate source family reports a "
            "conflicting measurement; we are watching both. surprise is unmeasured "
            "without a baseline."
        )
        return {
            "what_we_are_watching": watching,
            "windows": windows,
            "plain_status": status,
        }

    if template == "capital_allocation_event.v1":
        watching = (
            f"actual repurchases and net dilution through the fiscal {year} window, "
            "not further reprints of the authorization"
            if year
            else "actual repurchases and net dilution, not further reprints of the authorization"
        )
        status = (
            "the source states an authorization. completed purchases are not yet in this "
            "store. operating revenue impact is not established. surprise is unmeasured "
            "without a baseline."
        )
        return {
            "what_we_are_watching": watching,
            "windows": windows,
            "plain_status": status,
        }

    if template == "strategic_product_partnership_event.v1":
        watching = (
            "what we are watching is independent repeated use and paid bookings in the "
            "next reporting windows; repository stars are not in this store as profit evidence."
        )
        status = (
            "the source states an announcement. near-term earnings remain unquantified. "
            "surprise is unmeasured without a baseline."
        )
        return {
            "what_we_are_watching": watching,
            "windows": windows,
            "plain_status": status,
        }

    watching = "the next observation in the stated window, not further reprints"
    status = "the source states a proposition. the next observation is not yet in this store."
    return {
        "what_we_are_watching": watching,
        "windows": windows,
        "plain_status": status,
    }


def _display_windows(
    next_obs: Mapping[str, Any],
    deadline: str | Mapping[str, Any],
    live_prop: Mapping[str, Any],
    year: str,
) -> list[dict[str, str]]:
    start = None
    end = None
    if isinstance(next_obs, Mapping):
        start = next_obs.get("window_start")
        end = next_obs.get("window_end")
    neo = live_prop.get("next_expected_observation")
    if isinstance(neo, Mapping):
        start = start or neo.get("window_start")
        end = end or neo.get("window_end")
    if isinstance(deadline, str):
        end = end or deadline
    if not isinstance(start, str):
        start = live_prop.get("source_available_at") or live_prop.get("observed_at")
    if not isinstance(end, str):
        end = start
    label = (
        f"stated execution horizon through fiscal {year}"
        if year
        else "stated observation window"
    )
    return [{"label": label, "start": start, "end": end}]


def _material_delta_triggers(
    log: Mapping[str, Any],
    owners: OwnerSnapshot,
    prior_owners: OwnerSnapshot,
    view: Mapping[str, Any],
    prior_view: Mapping[str, Any] | None,
    as_of_utc: str,
    prior_as_of_utc: str,
) -> list[str]:
    if prior_view is None:
        # First materialization is not a recompute (§4.7).
        # Still detect triggers that fired by records arriving after prior_as_of.
        pass
    fired: set[str] = set()
    records = [
        r
        for r in log["records"]
        if _parse_dt(prior_as_of_utc) < _parse_dt(r["observed_at"]) <= _parse_dt(as_of_utc)
    ]
    records = sorted(records, key=lambda r: (_parse_dt(r["observed_at"]), r["fact_id"]))
    prior_groups = set(prior_view.get("provenance_group_ids") or []) if prior_view else set()
    prior_live = set(prior_view.get("live_fact_ids") or []) if prior_view else set()
    prior_supporting = set(prior_view.get("supporting_claim_ids") or []) if prior_view else set()
    for rec in records:
        if rec.get("company_id") != view["company_id"]:
            continue
        # Restrict to records attached to this view's original proposition.
        if not _record_belongs(rec, view["original_proposition_fact_id"], log, as_of_utc):
            continue
        gid = _provenance_group_id(rec)
        known_group_reporting = (
            rec.get("novelty") in {"new_reporting_of_old_fact", "commentary"}
            and gid in prior_groups
        )
        if rec.get("record_kind") == "fact_revision":
            fp = rec.get("quantity_fingerprint") or {}
            # Contributions belong to this attached record. A milestone is not
            # a numeric revision, and a mirror cannot erase another record's
            # independently established contribution to the interval.
            if (
                fp.get("form") == "present"
                and rec.get("novelty") != "independently_observed_milestone"
                and not known_group_reporting
            ):
                fired.add("changed_numeric_terms")
            if rec.get("novelty") == "independently_observed_milestone":
                fired.add("independently_observed_milestone")
            if rec.get("novelty") == "corrected_fact" and rec.get("supersedes_fact_id"):
                fired.add("source_correction")
            if rec.get("polarity") == "contrary" and prior_supporting:
                fired.add("contradiction")
        if gid and gid not in prior_groups:
            fired.add("new_independent_source")
    # missed_deadline: armed now, not armed before
    now_missed = any(
        w.get("code") == "missed_stated_deadline" and w.get("armed")
        for w in view.get("weakening_conditions") or []
    )
    prior_missed = False
    if prior_view:
        prior_missed = any(
            w.get("code") == "missed_stated_deadline" and w.get("armed")
            for w in prior_view.get("weakening_conditions") or []
        )
    if now_missed and not prior_missed:
        fired.add("missed_deadline")
    # exposure_change
    cur_exp = canonical_json(
        [
            _plain(r)
            for r in owners.relationship_candidates
            if isinstance(r, Mapping)
            and r.get("company_id") == view["company_id"]
            or (isinstance(r, Mapping) and r.get("target_company_id") == view["company_id"])
        ]
    )
    prior_exp = canonical_json(
        [
            _plain(r)
            for r in prior_owners.relationship_candidates
            if isinstance(r, Mapping)
            and (
                r.get("company_id") == view["company_id"]
                or r.get("target_company_id") == view["company_id"]
            )
        ]
    )
    if owners.relationship_candidates and cur_exp != prior_exp:
        fired.add("exposure_change")
    # market_state_change never fires unless an admitted owner is present.
    if owners.market_state is not None:
        if canonical_json(owners.market_state) != canonical_json(prior_owners.market_state):
            fired.add("market_state_change")
    # First materialization: empty unless prior_view existed or prior_as_of had content.
    if prior_view is None and not prior_live:
        # Still report triggers for records in the (prior, as_of] window when the
        # caller named a prior_as_of (Case 2/3/4).
        if not records:
            return []
    return [t for t in TRIGGER_EMIT_ORDER if t in fired]


def _record_belongs(
    rec: Mapping[str, Any],
    original_id: str,
    log: Mapping[str, Any],
    as_of_utc: str,
) -> bool:
    if rec.get("fact_id") == original_id:
        return True
    linked = rec.get("linked_fact_ids") or []
    if original_id in linked:
        return True
    if rec.get("reports_fact_id") == original_id:
        return True
    if rec.get("supersedes_fact_id") == original_id:
        return True
    # Same fact_key as the original.
    by_id = {r["fact_id"]: r for r in log["records"]}
    orig = by_id.get(original_id)
    if orig and _fact_key(orig) == _fact_key(rec) and rec.get("record_kind") in {
        "fact_revision",
        "manifestation",
        "thesis_link",
    }:
        return True
    # Walk linked ids to original.
    for lid in linked:
        if lid == original_id:
            return True
        other = by_id.get(lid)
        if other and _root_fact_id(other, by_id) == original_id:
            return True
    reports = rec.get("reports_fact_id")
    if isinstance(reports, str) and reports in by_id:
        if _root_fact_id(by_id[reports], by_id) == original_id:
            return True
    return _root_fact_id(rec, by_id) == original_id


# --------------------------------------------------------------------------- live-set / keys / provenance


def _compute_live(records: Sequence[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    """V_LIVE: per fact_key, latest (observed_at, fact_id) fact_revision not superseded.

    Same-key non-correction does not retire the old row; live is the latest
    of that polarity. A contrary record on the same slot stays live alongside
    a supporting one (Case 4: contradiction is not a revision). Manifestations
    and thesis_links do not compete for live (section 4.1).
    """
    _by_key, live_ids = _live_sets(records)
    # live_payload(key) wants the latest record of the key across polarities.
    remaining = [
        r
        for r in records
        if r.get("fact_id") in live_ids
    ]
    remaining.sort(key=lambda r: (_parse_dt(r["observed_at"]), r["fact_id"]))
    live: dict[str, Mapping[str, Any]] = {}
    for rec in remaining:
        live[_fact_key(rec)] = rec
    return live


def _live_sets(
    records: Sequence[Mapping[str, Any]],
) -> tuple[dict[tuple[str, str], Mapping[str, Any]], set[str]]:
    retired: set[str] = set()
    revisions = [
        r
        for r in records
        if r.get("record_kind") == "fact_revision" and r.get("novelty") != "commentary"
    ]
    by_id = {r["fact_id"]: r for r in revisions}
    for rec in revisions:
        if rec.get("novelty") == "corrected_fact" and isinstance(rec.get("supersedes_fact_id"), str):
            retired |= _supersedes_closure(rec["supersedes_fact_id"], by_id)
            retired.add(rec["supersedes_fact_id"])
    remaining = [r for r in revisions if r["fact_id"] not in retired]
    remaining.sort(key=lambda r: (_parse_dt(r["observed_at"]), r["fact_id"]))
    by_key_pol: dict[tuple[str, str], Mapping[str, Any]] = {}
    for rec in remaining:
        pol = rec.get("polarity") or "unclassified"
        by_key_pol[(_fact_key(rec), pol)] = rec
    live_ids = {r["fact_id"] for r in by_key_pol.values()}
    return by_key_pol, live_ids


def _live_record_for_key(
    fact_key: Mapping[str, Any] | str,
    records: Sequence[Mapping[str, Any]],
    as_of_utc: str,
) -> Mapping[str, Any] | None:
    visible = [r for r in records if _parse_dt(r["observed_at"]) <= _parse_dt(as_of_utc)]
    live = _compute_live(visible)
    if isinstance(fact_key, str):
        key = fact_key
    elif isinstance(fact_key, Mapping) and "fact_key" in fact_key:
        key = _fact_key(fact_key)
    else:
        key = _fact_key({"fact_key": fact_key})
    return live.get(key)


def _fact_key(rec: Mapping[str, Any]) -> str:
    return canonical_json(rec.get("fact_key") or {})


def _root_fact_id(rec: Mapping[str, Any], by_id: Mapping[str, Mapping[str, Any]]) -> str:
    cur = rec
    seen: set[str] = set()
    while True:
        fid = cur.get("fact_id")
        if not isinstance(fid, str) or fid in seen:
            return rec.get("fact_id") or ""
        seen.add(fid)
        sid = cur.get("supersedes_fact_id")
        if isinstance(sid, str) and sid in by_id:
            cur = by_id[sid]
            continue
        # linked_fact_ids may point at the parent proposition for milestones.
        slot = (cur.get("fact_key") or {}).get("slot") or {}
        if slot.get("kind") == "milestone_under_proposition":
            for lid in cur.get("linked_fact_ids") or []:
                if lid in by_id:
                    parent = by_id[lid]
                    pslot = (parent.get("fact_key") or {}).get("slot") or {}
                    if pslot.get("kind") in PROPOSITION_KINDS:
                        return _root_fact_id(parent, by_id)
        return fid


def _attached_records(
    original_id: str,
    records: Sequence[Mapping[str, Any]],
    by_id: Mapping[str, Mapping[str, Any]],
) -> list[Mapping[str, Any]]:
    attached: list[Mapping[str, Any]] = []
    orig = by_id.get(original_id)
    orig_key = _fact_key(orig) if orig else ""
    for rec in records:
        fid = rec.get("fact_id")
        if fid == original_id:
            attached.append(rec)
            continue
        if rec.get("supersedes_fact_id") == original_id:
            attached.append(rec)
            continue
        if rec.get("reports_fact_id") == original_id:
            attached.append(rec)
            continue
        linked = rec.get("linked_fact_ids") or []
        if original_id in linked:
            attached.append(rec)
            continue
        if orig_key and _fact_key(rec) == orig_key:
            attached.append(rec)
            continue
        if _root_fact_id(rec, by_id) == original_id:
            attached.append(rec)
            continue
        reports = rec.get("reports_fact_id")
        if isinstance(reports, str) and reports in by_id:
            if _root_fact_id(by_id[reports], by_id) == original_id:
                attached.append(rec)
                continue
        for lid in linked:
            if lid in by_id and _root_fact_id(by_id[lid], by_id) == original_id:
                attached.append(rec)
                break
    # Stable unique by fact_id.
    seen: set[str] = set()
    out: list[Mapping[str, Any]] = []
    for rec in attached:
        if rec["fact_id"] in seen:
            continue
        seen.add(rec["fact_id"])
        out.append(rec)
    out.sort(key=lambda r: (_parse_dt(r["observed_at"]), r["fact_id"]))
    return out


def _provenance_group_id(rec: Mapping[str, Any]) -> str:
    prov = rec.get("provenance") or {}
    origin_doc = prov.get("origin_document_id")
    origin_claim = prov.get("origin_claim_id")
    if isinstance(origin_doc, str) and origin_doc:
        return origin_doc
    if isinstance(origin_claim, str) and origin_claim:
        return origin_claim
    return ""


def _supersedes_closure(start_id: str, by_id: Mapping[str, Mapping[str, Any]]) -> set[str]:
    out: set[str] = set()
    stack = [start_id]
    while stack:
        cur = stack.pop()
        if cur in out:
            continue
        out.add(cur)
        rec = by_id.get(cur)
        if rec is None:
            continue
        sid = rec.get("supersedes_fact_id")
        if isinstance(sid, str):
            stack.append(sid)
    return out


def _check_supersedes_cycle(rec: Mapping[str, Any], by_id: Mapping[str, Mapping[str, Any]]) -> None:
    start = rec["fact_id"]
    seen: set[str] = set()
    cur: str | None = rec.get("supersedes_fact_id")
    while isinstance(cur, str):
        if cur == start or cur in seen and cur == rec.get("supersedes_fact_id") and start in seen:
            raise ThesisError("SUPERSEDES_CYCLE", f"{start} participates in a supersedes cycle")
        if cur == start:
            raise ThesisError("SUPERSEDES_CYCLE", f"{start} supersedes itself via a cycle")
        if cur in seen:
            break
        seen.add(cur)
        nxt = by_id.get(cur)
        if nxt is None:
            break
        cur = nxt.get("supersedes_fact_id")
    if rec.get("supersedes_fact_id") == rec.get("fact_id"):
        raise ThesisError("SUPERSEDES_CYCLE", f"{start} supersedes itself")


def _check_pit_clocks(rec: Mapping[str, Any]) -> None:
    observed = rec.get("observed_at")
    available = rec.get("source_available_at")
    if not isinstance(observed, str) or not isinstance(available, str):
        return
    if _parse_dt(observed) < _parse_dt(available):
        raise ThesisError(
            "PIT_CLOCK_VIOLATION",
            f"{rec.get('fact_id')}: observed_at is before source_available_at",
        )


def _check_text_safe_record(rec: Mapping[str, Any]) -> None:
    def walk(node: Any, loc: str) -> None:
        if isinstance(node, Mapping):
            for k in sorted(node):
                walk(node[k], f"{loc}/{k}")
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, f"{loc}/{i}")
        elif isinstance(node, str):
            for pat in _TEXT_SAFE_PATTERNS:
                if re.search(pat, node):
                    raise ThesisError(
                        "TEXT_SAFE_VIOLATION",
                        f"{loc}: free string failed text_safe; recorded as injection finding and refused",
                    )

    walk(rec, "")


# --------------------------------------------------------------------------- owners / stripping / json helpers


def _coerce_owners(raw: Mapping[str, Any] | OwnerSnapshot | None) -> OwnerSnapshot:
    if raw is None:
        return OwnerSnapshot()
    if isinstance(raw, OwnerSnapshot):
        cleaned, stripped = _strip_forbidden(raw.to_dict())
        return OwnerSnapshot(
            identity_map=cleaned.get("identity_map") or {},
            qbus_clusters=tuple(cleaned.get("qbus_clusters") or ()),
            news_event_ledger=tuple(cleaned.get("news_event_ledger") or ()),
            ci_events=tuple(cleaned.get("ci_events") or ()),
            workspaces=tuple(cleaned.get("workspaces") or ()),
            claims=tuple(cleaned.get("claims") or ()),
            facts=tuple(cleaned.get("facts") or ()),
            guidance=tuple(cleaned.get("guidance") or ()),
            source_spans=tuple(cleaned.get("source_spans") or ()),
            relationship_candidates=tuple(cleaned.get("relationship_candidates") or ()),
            market_state=cleaned.get("market_state"),
            pbd_roots=tuple(cleaned.get("pbd_roots") or ()),
            leaf_payloads=cleaned.get("leaf_payloads") or {},
            decision_cut=cleaned.get("decision_cut"),
            stripped_fields=tuple(sorted(set(raw.stripped_fields) | set(stripped))),
        )
    cleaned, stripped = _strip_forbidden(raw)
    return OwnerSnapshot(
        identity_map=cleaned.get("identity_map") or {},
        qbus_clusters=tuple(cleaned.get("qbus_clusters") or ()),
        news_event_ledger=tuple(cleaned.get("news_event_ledger") or ()),
        ci_events=tuple(cleaned.get("ci_events") or ()),
        workspaces=tuple(cleaned.get("workspaces") or ()),
        claims=tuple(cleaned.get("claims") or ()),
        facts=tuple(cleaned.get("facts") or ()),
        guidance=tuple(cleaned.get("guidance") or ()),
        source_spans=tuple(cleaned.get("source_spans") or ()),
        relationship_candidates=tuple(cleaned.get("relationship_candidates") or ()),
        market_state=cleaned.get("market_state"),
        pbd_roots=tuple(cleaned.get("pbd_roots") or ()),
        leaf_payloads=cleaned.get("leaf_payloads") or {},
        decision_cut=cleaned.get("decision_cut"),
        stripped_fields=tuple(sorted(set(cleaned.get("stripped_fields") or []) | set(stripped))),
    )


def _leaf_payload(owners: OwnerSnapshot, fact_id: str | None) -> dict[str, Any]:
    if not fact_id:
        return {}
    payload = owners.leaf_payloads.get(fact_id) or {}
    cleaned, _ = _strip_forbidden(payload)
    return cleaned


def _normalize_log(obj: Mapping[str, Any]) -> dict[str, Any]:
    cleaned, stripped = _strip_forbidden(obj)
    records = []
    for rec in cleaned.get("records") or []:
        rec_c, rec_s = _strip_forbidden(rec)
        stripped.extend(rec_s)
        # Assign polarity default if a payload flag is present on the record.
        rec_c = dict(rec_c)
        if "polarity" not in rec_c or rec_c.get("polarity") is None:
            rec_c["polarity"] = assign_polarity(
                bool(rec_c.get("negated", False)),
                rec_c.get("contrary_mechanism_quote"),
            )
        records.append(rec_c)
    records.sort(key=lambda r: (int(r.get("log_seq") or 0), r.get("fact_id") or ""))
    return {
        "schema": cleaned.get("schema") or SCHEMA_NAME_LOG,
        "authority": cleaned.get("authority") or AUTHORITY,
        "prophet_flags": dict(cleaned.get("prophet_flags") or PROPHET_FLAGS),
        "unsolicited_instruction_detected": False,
        "records": records,
    }


def strip_forbidden(obj: Any) -> tuple[Any, list[str]]:
    """Strip forbidden keys at ingest (W3-R3) and return (cleaned, stripped names)."""
    return _strip_forbidden(obj)


def _strip_forbidden(obj: Any) -> tuple[Any, list[str]]:
    stripped: list[str] = []

    def walk(node: Any) -> Any:
        if isinstance(node, Mapping):
            out: dict[str, Any] = {}
            for k in node:
                if k in FORBIDDEN_KEYS:
                    stripped.append(k)
                    continue
                out[k] = walk(node[k])
            return out
        if isinstance(node, list):
            return [walk(v) for v in node]
        if isinstance(node, tuple):
            return [walk(v) for v in node]
        return node

    return walk(obj), stripped


def _assert_no_forbidden(obj: Any) -> None:
    if isinstance(obj, Mapping):
        for k, v in obj.items():
            if k in FORBIDDEN_KEYS:
                raise ThesisError("SCHEMA_VIOLATION", f"forbidden key {k} leaked into output")
            _assert_no_forbidden(v)
    elif isinstance(obj, list):
        for v in obj:
            _assert_no_forbidden(v)


def _plain(obj: Any) -> Any:
    if isinstance(obj, Mapping):
        return {str(k): _plain(obj[k]) for k in obj}
    if isinstance(obj, (list, tuple)):
        return [_plain(v) for v in obj]
    return obj


def _jsonable(obj: Any) -> Any:
    if isinstance(obj, Mapping):
        return {str(k): _jsonable(obj[k]) for k in obj}
    if isinstance(obj, (list, tuple)):
        return [_jsonable(v) for v in obj]
    if isinstance(obj, bool) or obj is None:
        return obj
    if isinstance(obj, float) and obj.is_integer() and abs(obj) < 2**53:
        return int(obj)
    if isinstance(obj, (int, float, str)):
        return obj
    if hasattr(obj, "to_dict"):
        return _jsonable(obj.to_dict())
    return obj


def _parse_dt(value: str, *, code: str = "AS_OF_INVALID") -> datetime:
    if not isinstance(value, str) or not value:
        raise ThesisError(code, f"invalid timestamp {value!r}")
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise ThesisError(code, f"invalid timestamp {value!r}") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _billions(value: Any) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return int(round(value / 1_000_000_000))
    return None


def _is_iterable_of_str(obj: Any) -> bool:
    if isinstance(obj, (str, bytes, Mapping)):
        return False
    try:
        iterator = iter(obj)
    except TypeError:
        return False
    # Peek is not possible without consuming; treat list/tuple of str as yes.
    return isinstance(obj, (list, tuple)) and all(isinstance(x, str) for x in obj)


__all__ = [
    "CODES",
    "DEFAULT_LOG_PATH",
    "FORBIDDEN_KEYS",
    "PROPHET_FLAGS",
    "F",
    "FactLog",
    "FieldAbsence",
    "OwnerSnapshot",
    "ThesisError",
    "ThesisView",
    "absent_thesis",
    "append_records",
    "assign_polarity",
    "canonical_json",
    "canonical_json_sha256",
    "check_append_only",
    "live_payload",
    "load_schema",
    "parse_fact_log",
    "parse_jsonl",
    "project",
    "project_one",
    "quantity_fingerprint",
    "serialize_jsonl",
    "strip_forbidden",
    "validate_against_schema",
    "validate_log",
]
