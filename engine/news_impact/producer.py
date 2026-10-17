"""W3 Phase 1 measured packet producer, stage one (context_only).

Turns graded label bundles plus labeler returns into candidate news_impact_event.v1
payloads behind the owner gates: label-return parsing, source and issuer ties, span
replay, two-family routing, owner span binding and the validate_event chokepoint.
Every case lands in exactly one of emitted, deferred or rejected, with a code.

Authority is context_only and every prophet flag is false. Novelty here is the
labeler's value carried for validation only; the rule-assigned novelty, fact-log
append/projection and Prophet adapter stage is the next producer stage. The output
directory must be explicit and the report carries counts and codes only, never values.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import tempfile
from collections import Counter
from datetime import datetime, timezone
from functools import lru_cache
from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping

from jsonschema import Draft202012Validator

from engine.company_intelligence.documents import DocumentError, text_span, verify_span
from engine.news_impact import agreement as ag
from engine.news_impact.validate import load_contract, validate_event

PRODUCER_VERSION = "ni-producer-1"
FAMILIES = ("fam_a", "fam_b")
QUANTITY_FIELDS = frozenset({"incremental_amount", "remaining_authorization", "executed_amount", "stated_amount", "stated_quantity"})
PERIOD_FIELDS = frozenset({"horizon_period", "fiscal_period"})
EVIDENCE_FIELDS = frozenset({"action_span"})
PERIOD_KEYS = ("year", "quarter", "calendar_end", "period_kind", "end_year")
QUANTITY_KEYS = {"point": ("form", "value", "bound", "unit", "currency", "basis", "negated"),
                 "range": ("form", "low", "high", "unit", "currency", "basis", "negated")}
BASELINE_KEYS = ("type", "timestamp", "contributors", "coverage", "period", "basis", "age_days")
PERIOD_KINDS = frozenset({"quarter", "half_year", "nine_months", "fiscal_year", "multi_year"})
CALENDAR_END = re.compile(r"^\d{4}-\d{2}-\d{2}$")
CURRENCY = re.compile(r"^([A-Z]{3}|NA)$")
FALSE_FLAGS = {"may_rank": False, "may_size": False, "may_gate": False, "prophet_authority": False}


@lru_cache(maxsize=1)
def _defs() -> dict:
    return load_contract()["$defs"]


@lru_cache(maxsize=None)
def _validator(fragment_json: str) -> Draft202012Validator:
    return Draft202012Validator({"$defs": _defs(), **json.loads(fragment_json)})


def _admits(fragment: Mapping[str, Any], value: Any) -> bool:
    """True when the contract fragment (refs resolved against the contract $defs) admits value."""
    return _validator(json.dumps(fragment, sort_keys=True)).is_valid(value)


def _property(template: str, name: str) -> dict:
    return _defs()[template]["properties"][name]


def _enum_values(template: str, name: str) -> frozenset:
    prop = _property(template, name)
    if "$ref" in prop:
        prop = _defs()[prop["$ref"].rsplit("/", 1)[1]]
    return frozenset(prop["enum"])


class Reject(Exception):
    """A case-level fail-closed outcome; ``code`` is printable, the detail is not kept."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _absence(subject: str) -> dict:
    return {"schema": "field_absence.v1", "authority": "context_only", "reason": "not_stated",
            "subject": subject[:64], "detail": "not stated in the cited filing", "missing_fields": [subject[:64]]}


def _is_absence(value: Any) -> bool:
    return isinstance(value, dict) and value.get("schema") in ag.ABSENCE_SCHEMA_CONSTS


def _entry_absence(entry: Mapping[str, Any], subject: str, counts: Counter) -> dict:
    ta = entry.get("typed_absence")
    if _is_absence(ta) and ta.get("missing_fields"):
        return ta
    counts["absence_synthesised"] += 1
    return _absence(subject)


def _fold(value: Any) -> Any:
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def bind_span(source_span: Mapping[str, Any], segments: list, source_bytes: bytes) -> tuple[dict, dict]:
    """Bind a label span to the owner text_span of its bundle segment (verified)."""
    seg = next((s for s in segments if s.get("segment_index") == source_span.get("segment_index")), None)
    if seg is None:
        raise Reject("span_segment_unknown")
    seg_bytes = source_bytes[seg["byte_start"]:seg["byte_end"]]
    seg_text = seg_bytes.decode("utf-8")
    body = sha256(seg_bytes).hexdigest()
    start, end = source_span["byte_start"] - seg["byte_start"], source_span["byte_end"] - seg["byte_start"]
    try:
        span = text_span(document_id=seg["document_id"], document_version=1, body_sha256=body, segment_index=0,
                         segment_text=seg_text, start_byte=start, end_byte=end,
                         text=seg_bytes[start:end].decode("utf-8"), display_excerpt=source_span.get("excerpt"))
        verify_span(span, segment_text=seg_text, body_sha256=body)
    except (DocumentError, UnicodeDecodeError, ValueError):
        raise Reject("span_bind_failed") from None
    return {"claimed_quote": source_span.get("excerpt"), "span": span.to_payload()}, seg


def _unwrap_absent(value: Any, subject: str, counts: Counter) -> Any:
    """Return a contract absence for a ``{form: absent}`` wrapper, else the value unchanged."""
    if isinstance(value, dict) and value.get("form") == "absent":
        inner = value.get("absence")
        if _is_absence(inner) and _admits({"$ref": "#/$defs/absence_union"}, inner):
            return inner
        counts["absence_synthesised"] += 1
        return _absence(subject)
    return value


def _period(value: Any, subject: str, counts: Counter) -> Any:
    """Normalise a labeler period to a contract fiscal_period or absence; raises Reject."""
    if value is None:
        counts["period_absent"] += 1
        return _absence(subject)
    value = _unwrap_absent(value, subject, counts)
    if _is_absence(value):
        if _admits({"$ref": "#/$defs/absence_union"}, value):
            return value
        counts["absence_synthesised"] += 1
        return _absence(subject)
    if not isinstance(value, dict) or not {"year", "period_kind"} <= set(value):
        raise Reject("period_shape_unrecognized")
    out = {k: _fold(value.get(k)) for k in PERIOD_KEYS}
    if out["end_year"] is None:
        del out["end_year"]
    if out["period_kind"] not in PERIOD_KINDS:
        raise Reject("period_kind_out_of_contract")
    quarter = out["quarter"]
    if (out["period_kind"] == "quarter") != (quarter is not None) or (quarter is not None and quarter not in (1, 2, 3, 4)):
        raise Reject("period_quarter_conflict")
    end = out["calendar_end"]
    if isinstance(end, str) and not CALENDAR_END.match(end) and CALENDAR_END.match(end[:10]) and end[10:11] == "T":
        out["calendar_end"] = end[:10]
        counts["period_calendar_end_truncated"] += 1
    if not _admits({"$ref": "#/$defs/fiscal_period"}, out):
        raise Reject("period_invalid")
    return out


def _quantity(entry: Mapping[str, Any], subject: str, ctx: dict, counts: Counter) -> dict:
    value = entry.get("value")
    if value is None or (isinstance(value, dict) and value.get("form") == "absent"):
        absence = value.get("absence") if isinstance(value, dict) and _is_absence(value.get("absence")) else None
        return {"form": "absent", "absence": absence or _entry_absence(entry, subject, counts)}
    form = value.get("form") if isinstance(value, dict) else None
    if form not in QUANTITY_KEYS:
        raise Reject("quantity_shape_unrecognized")
    if entry.get("source_span") is None:
        raise Reject("quantity_span_missing")
    out = {k: _fold(value.get(k)) for k in QUANTITY_KEYS[form] if k in value}
    if form == "range" and "bound" in value:
        counts["range_bound_dropped"] += 1
    currency, unit = out.get("currency"), str(out.get("unit") or "")
    if not (isinstance(currency, str) and CURRENCY.match(currency)):
        folded = unit.split()[0].upper() if unit.split() else ""
        if not CURRENCY.match(folded):
            raise Reject("quantity_currency_unrecognized")
        out["currency"] = folded
        counts["currency_folded_from_unit"] += 1
    out["period"] = _period(value.get("period"), subject + ".period", counts)
    out["evidence"], _ = bind_span(entry["source_span"], ctx["segments"], ctx["source"])
    return out


def _baseline(entry: Mapping[str, Any], counts: Counter) -> dict:
    """Normalise a labeler baseline sub-value by sub-value against the contract.

    A sub-value the contract does not admit becomes an absence (``type`` becomes the
    contract's UNKNOWN), counted per key: the baseline is context, so an unusable
    sub-value is de-escalated to "not known", never repaired into a different value.
    """
    value = entry.get("value") if isinstance(entry.get("value"), dict) else {}
    for key in sorted(set(value) - set(BASELINE_KEYS)):
        counts[f"baseline_{key}_dropped"] += 1
    props = _defs()["baseline"]["properties"]
    out: dict[str, Any] = {}
    for key in BASELINE_KEYS:
        subject = "baseline." + key
        v = _unwrap_absent(_fold(value.get(key)), subject, counts)
        if key == "period" and v is not None and not _is_absence(v):
            try:
                v = _period(v, subject, counts) if isinstance(v, dict) else None
            except Reject:
                v = None
            if v is None:
                counts["baseline_period_unusable"] += 1
                v = _absence(subject)
        if v is not None and _admits(props[key], v):
            out[key] = v
            continue
        counts[f"baseline_{key}_{'absent' if v is None else 'not_admitted'}"] += 1
        out[key] = "UNKNOWN" if key == "type" else _absence(subject)
    return out


def _iso(stamp: str) -> str:
    stamp = str(stamp)
    if re.fullmatch(r"\d{8}T\d{6}Z", stamp):
        return datetime.strptime(stamp, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", stamp):
        return stamp + "T00:00:00Z"
    return stamp


def build_event(bundle: Mapping[str, Any], source: bytes, chosen: Mapping[str, Mapping[str, Any]], template: str,
                counts: Counter) -> dict:
    """Assemble one candidate event from per-field label entries; raises Reject."""
    ctx = {"segments": bundle["segments"], "source": source}
    event: dict[str, Any] = {}
    cited: list[dict] = []
    for name in ag.TEMPLATE_FIELDS[template]:
        entry = chosen[name]
        if name in QUANTITY_FIELDS:
            event[name] = _quantity(entry, name, ctx, counts)
        elif name in PERIOD_FIELDS:
            event[name] = _period(entry.get("value"), name, counts)
        elif name in EVIDENCE_FIELDS:
            if entry.get("source_span") is None:
                raise Reject("action_span_missing")
            event[name], seg = bind_span(entry["source_span"], ctx["segments"], source)
            cited.insert(0, seg)
        elif name == "baseline":
            event[name] = _baseline(entry, counts)
        elif ag.FIELD_KINDS[template].get(name) == ag.KIND_ENUM:
            # The contract's enums admit no absence and no synonym: a missing or foreign
            # value is the labeler's error, rejected rather than mapped onto a contract value.
            value = entry.get("value")
            if value is None:
                raise Reject(f"enum_missing:{name}")
            if value not in _enum_values(template, name):
                raise Reject(f"enum_out_of_contract:{name}")
            event[name] = value
        else:
            value = entry.get("value")
            event[name] = value if value is not None else _entry_absence(entry, name, counts)
        if entry.get("source_span") is not None and name not in EVIDENCE_FIELDS:
            seg = next((s for s in ctx["segments"] if s.get("segment_index") == entry["source_span"].get("segment_index")), None)
            if seg is not None:
                cited.append(seg)
    seg = cited[0] if cited else bundle["segments"][0]
    available = seg["filing_date"] + "T23:59:59Z"
    seen = _iso(bundle.get("seendate") or available)
    event.update({
        "schema": template, "authority": "context_only", "prophet_flags": dict(FALSE_FLAGS),
        "unsolicited_instruction_detected": False,
        "fact_id": "fact_" + sha256(f"{bundle['case_id']}|{template}".encode()).hexdigest()[:24],
        "document_id": seg["document_id"], "source_available_at": available,
        "observed_at": max(seen, available), "supersedes_fact_id": None,
    })
    return event


CASE_ID_RE = re.compile(r"[A-Za-z0-9_][A-Za-z0-9._-]{0,127}\Z")


class ProducerInputError(ValueError):
    """A stable, input-safe error code; never put source contents in the message."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _safe_case_id(value: object) -> str:
    if not isinstance(value, str) or CASE_ID_RE.fullmatch(value) is None:
        raise ProducerInputError("case_id_invalid")
    return value


def _read_case_file(path: Path, root: Path, *, code: str) -> bytes:
    """Only read regular, non-symlink files contained by the supplied case root."""
    if path.is_symlink() or not path.resolve(strict=False).is_relative_to(root.resolve()):
        raise ProducerInputError(code)
    try:
        return path.read_bytes()
    except OSError:
        raise ProducerInputError(code) from None


def _load_family(labels: Path, case_id: str, family: str) -> dict | None:
    case_id = _safe_case_id(case_id)
    if family not in FAMILIES:
        raise ProducerInputError("family_invalid")
    path = labels / f"{case_id}.{family}.json"
    if path.is_symlink() or not path.resolve(strict=False).is_relative_to(labels.resolve()):
        raise ProducerInputError("label_path_outside_root")
    if not path.exists():
        return None
    try:
        result = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        raise ProducerInputError("label_json_malformed") from None
    if not isinstance(result, dict):
        raise ProducerInputError("label_json_not_object")
    return result


def produce_case(bundle: Mapping[str, Any], source: bytes, returns: Mapping[str, Mapping[str, Any]],
                 shadow_family: str | None, counts: Counter) -> tuple[str, str, dict | None]:
    """Return (outcome, code, event) with outcome in emitted/deferred/rejected."""
    try:
        if sha256(source).hexdigest() != bundle["source_sha256"]:
            raise Reject("source_sha_mismatch")
        issuer = str(bundle["issuer"])
        cik = issuer if issuer.startswith("cik:") else "cik:" + issuer.zfill(10)
        families = (shadow_family,) if shadow_family else FAMILIES
        parsed = {}
        for fam in families:
            if returns.get(fam) is None:
                return "deferred", "family_return_missing", None
            try:
                parsed[fam] = ag.parse_label_return(returns[fam])
            except ag.AgreementError as exc:
                raise Reject("parse:" + str(exc.code)) from None
            replay =ag.replay_return_spans(parsed[fam], source, bundle["source_sha256"], segments=bundle["segments"])
            if replay["n_failed"]:
                raise Reject("replay_failed")
            if replay["injection_flagged"]:
                return "deferred", "injection_flagged", None
        if shadow_family:
            first = parsed[shadow_family]
        else:
            routing = ag.route_case(parsed["fam_a"], parsed["fam_b"], source, bundle["source_sha256"],
                                    segments=bundle["segments"])
            if routing.status == ag.ST_ROUTED_PENDING_THIRD:
                return "deferred", "pending_third_family", None
            if routing.status == ag.ST_ADJUDICATION_NEEDED:
                return "deferred", "adjudication_needed", None
            if routing.status == ag.ST_RESOLVED_BY_THIRD:
                return "deferred", "resolved_by_third_unbound", None
            if routing.status != ag.ST_ACCEPTED_FIRST_PASS:
                raise Reject("routing:" + routing.status)
            first = parsed["fam_a"]
        # The issuer tie applies to the routed value: a family that names another issuer is a
        # field disagreement the router sends to a third family, not a case-level reject.
        if first.field_entry("company_id").get("value") != cik:
            raise Reject("company_id_mismatch")
        template = first.template
        chosen = {name: first.field_entry(name) for name in ag.TEMPLATE_FIELDS[template]}
        event = build_event(bundle, source, chosen, template, counts)
        report = validate_event(event)
        if not report.ok:
            # Codes and JSON-pointer paths name contract fields only (indices folded), never values.
            for issue in report.issues:
                counts["validation:" + issue.code] += 1
            first_issue = report.issues[0]
            raise Reject(f"validation:{first_issue.code}:{re.sub(r'/[0-9]+', '/N', first_issue.path)}")
        return "emitted", template, event
    except Reject as exc:
        return "rejected", exc.code, None



def _published_name(shadow_family: str | None) -> str:
    if shadow_family is not None and shadow_family not in FAMILIES:
        raise ProducerInputError("family_invalid")
    return "events_shadow_" + shadow_family if shadow_family else "events"


def _case_result(case_dir: Path, bundles: Path, labels: Path, shadow_family: str | None,
                 counts: Counter) -> tuple[str, str, dict | None, str]:
    case_id = case_dir.name
    try:
        _safe_case_id(case_id)
        if case_dir.is_symlink() or not case_dir.resolve().is_relative_to(bundles.resolve()):
            raise ProducerInputError("case_path_outside_root")
        try:
            bundle = json.loads(_read_case_file(case_dir / "bundle.json", case_dir, code="bundle_read_failed"))
        except (UnicodeError, json.JSONDecodeError):
            raise ProducerInputError("bundle_json_malformed") from None
        if not isinstance(bundle, dict):
            raise ProducerInputError("bundle_json_not_object")
        if _safe_case_id(bundle.get("case_id")) != case_id:
            raise ProducerInputError("bundle_case_id_mismatch")
        if not {"source_sha256", "issuer", "segments"} <= set(bundle):
            raise ProducerInputError("bundle_fields_missing")
        if not isinstance(bundle["source_sha256"], str) or not isinstance(bundle["segments"], list):
            raise ProducerInputError("bundle_fields_invalid")
        source = _read_case_file(case_dir / "source.txt", case_dir, code="source_read_failed")
        returns = {fam: _load_family(labels, case_id, fam) for fam in FAMILIES}
        kind, code, event = produce_case(bundle, source, returns, shadow_family, counts)
        return kind, code, event, case_id
    except ProducerInputError as exc:
        return "rejected", exc.code, None, case_id


def run(bundles: Path, labels: Path, out: Path, cases: list[str] | None = None,
        shadow_family: str | None = None) -> dict:
    name = _published_name(shadow_family)
    if not bundles.is_dir() or bundles.is_symlink():
        raise ProducerInputError("bundles_root_invalid")
    case_dirs = sorted(p for p in bundles.iterdir() if p.is_dir())
    if cases is not None:
        if not cases:
            raise ProducerInputError("requested_cases_empty")
        requested = [_safe_case_id(cid) for cid in cases]
        if len(requested) != len(set(requested)):
            raise ProducerInputError("requested_cases_duplicate")
        requested_set = set(requested)
        present = {p.name for p in case_dirs}
        if requested_set - present:
            raise ProducerInputError("requested_cases_missing")
        case_dirs = [p for p in case_dirs if p.name in requested_set]

    # A failed build cannot truncate the last published pair. Staging is entirely
    # private to the explicit output directory; only completed runs are published.
    out.mkdir(parents=True, exist_ok=True)
    counts: Counter = Counter()
    outcome = {"emitted": Counter(), "deferred": Counter(), "rejected": Counter()}
    with tempfile.TemporaryDirectory(dir=out, prefix=f".{name}.staging.") as temp_dir:
        temp_events = Path(temp_dir) / f"{name}.jsonl"
        temp_report = Path(temp_dir) / f"{name}_report.json"
        with temp_events.open("w", encoding="utf-8") as fh:
            for case_dir in case_dirs:
                kind, code, event, case_id = _case_result(case_dir, bundles, labels, shadow_family, counts)
                outcome[kind][code] += 1
                if event is not None:
                    fh.write(json.dumps({"case_id": case_id, "shadow": bool(shadow_family),
                                         "novelty_source": "label_provisional", "event": event},
                                        sort_keys=True) + "\n")
        event_bytes = temp_events.read_bytes()
        n_emitted = sum(outcome["emitted"].values())
        if sum(sum(v.values()) for v in outcome.values()) != len(case_dirs):
            raise ProducerInputError("case_accounting_invalid")
        report = {
            "producer_version": PRODUCER_VERSION,
            "mode": "shadow:" + shadow_family if shadow_family else "adjudicated",
            "n_cases": len(case_dirs),
            **{k: dict(sorted(v.items())) for k, v in outcome.items()},
            "n_emitted": n_emitted,
            "normalisation": dict(sorted(counts.items())),
            "events_sha256": sha256(event_bytes).hexdigest(),
            "events_bytes": len(event_bytes),
        }
        temp_report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        # Two independent path replacements cannot be atomic together. A reader
        # MUST verify the digest in the report: a crash between replacements is
        # detectable and fails closed, never a valid mixed-generation receipt.
        os.replace(temp_events, out / f"{name}.jsonl")
        os.replace(temp_report, out / f"{name}_report.json")
    return report


def read_verified_output(out: Path, shadow_family: str | None = None) -> tuple[dict, tuple[dict, ...]]:
    """Load a complete producer generation, refusing stale/mismatched receipts."""
    name = _published_name(shadow_family)
    try:
        raw = (out / f"{name}.jsonl").read_bytes()
        report = json.loads((out / f"{name}_report.json").read_text(encoding="utf-8"))
        if not isinstance(report, dict):
            raise ValueError("report not object")
        if report.get("producer_version") != PRODUCER_VERSION:
            raise ValueError("producer version mismatch")
        if report.get("mode") != ("shadow:" + shadow_family if shadow_family else "adjudicated"):
            raise ValueError("mode mismatch")
        if report.get("events_sha256") != sha256(raw).hexdigest() or report.get("events_bytes") != len(raw):
            raise ValueError("generation digest mismatch")
        rows = tuple(json.loads(line) for line in raw.splitlines())
        if any(not isinstance(row, dict) or row.get("shadow") is not bool(shadow_family)
               or row.get("novelty_source") != "label_provisional" for row in rows):
            raise ValueError("unverified row shape")
        emitted = report["emitted"]
        outcomes = (emitted, report["deferred"], report["rejected"])
        if any(not isinstance(item, dict) or any(not isinstance(n, int) or n < 0 for n in item.values())
               for item in outcomes):
            raise ValueError("invalid counts")
        if report["n_emitted"] != len(rows) or report["n_emitted"] != sum(emitted.values()):
            raise ValueError("event count mismatch")
        if report["n_cases"] != sum(sum(item.values()) for item in outcomes):
            raise ValueError("case count mismatch")
    except (OSError, UnicodeError, ValueError, TypeError, KeyError, IndexError):
        raise ProducerInputError("output_generation_unverified") from None
    return report, rows


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--bundles", type=Path, required=True)
    ap.add_argument("--labels", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--cases", nargs="*")
    ap.add_argument("--shadow-single-family", choices=FAMILIES)
    args = ap.parse_args(argv)
    report = run(args.bundles, args.labels, args.out, args.cases, args.shadow_single_family)
    print(json.dumps({k: report[k] for k in ("mode", "n_cases", "n_emitted", "deferred", "rejected")}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
