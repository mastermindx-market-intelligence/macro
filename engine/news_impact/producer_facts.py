"""News-impact W3 producer, stage two: events to fact log, thesis views and Prophet evidence.

Reads stage-one ``events*.jsonl`` rows (``{case_id, shadow, novelty_source, event}``),
keys each news_impact_event.v1 event to a fact_log.v1 ``fact_key``, assigns novelty by
rule through ``cluster.assign_novelty``, appends one record at a time through
``thesis.append_records``, projects thesis views with ``thesis.project`` and assembles
Prophet evidence with ``prophet_adapter.adapt_batch``. Owner modules only; no label
remapping. Every row is recorded, deferred or rejected with a code, and the report holds
counts and codes only.

Outputs go only under the required ``--out`` directory. The producer never writes to
``thesis.DEFAULT_LOG_PATH``: the shared fact log is a forward ledger the nightly owns.
Authority is context_only throughout.
"""
from __future__ import annotations

import argparse
import copy
import json
import re
from collections import Counter
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import Any, Iterable, Mapping

from engine.news_impact import thesis
from engine.news_impact.cluster import FactObservation, NoveltyError, assign_novelty
from engine.news_impact.prophet_adapter import ProphetAdapterError, adapt_batch

PRODUCER_FACTS_VERSION = "ni-producer-facts-2"

T1 = "capital_allocation_event.v1"
T2 = "demand_guidance_contract_event.v1"
T3 = "strategic_product_partnership_event.v1"
TEMPLATES = (T1, T2, T3)

SOURCE_FAMILY = "regulator_filing"
OBJECT_NAME_MAX = 80  # fact_log.v1 slot.object_name maxLength
_SPAN_ID = re.compile(r"^span_[0-9a-f]{20}$")

# Leaf key <- event field (thesis section 7 default 7 critical numeric slots).
LEAF_KEYS: dict[str, tuple[tuple[str, str], ...]] = {
    T1: (
        ("incremental", "incremental_amount"),
        ("remaining", "remaining_authorization"),
        ("executed", "executed_amount"),
    ),
    T2: (("stated_amount", "stated_amount"),),
    T3: (("stated_quantity", "stated_quantity"),),
}

# T1 primary quantity by primary_amount_role (dividend / issuance name none).
_T1_PRIMARY = {
    "incremental_authorization": "incremental_amount",
    "remaining_authorization": "remaining_authorization",
    "executed": "executed_amount",
}

# Evidence ladder: the first span-backed field wins.
EVIDENCE_LADDER: dict[str, tuple[str, ...]] = {
    T1: ("action_span", "incremental_amount", "remaining_authorization", "executed_amount"),
    T2: ("stated_amount", "option_ceiling", "prior_amount"),
    T3: ("action_span", "stated_quantity"),
}

FACT_REVISION_NOVELTY = frozenset({
    "new_magnitude_timing_commitment_counterparty",
    "corrected_fact",
    "independently_observed_milestone",
})

OUTPUT_NAMES = ("fact_log.json", "thesis_views.jsonl", "prophet_evidence.jsonl", "facts_report.json")


class Reject(Exception):
    """A per-row outcome code; never carries a value."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


# --------------------------------------------------------------------------- keying


def period_token(fp: Mapping[str, Any]) -> str:
    """Lossless fiscal_period token (<= 16 chars) for a fact_log slot."""
    kind = fp.get("period_kind")
    year = fp.get("year")
    if not isinstance(year, int) or isinstance(year, bool):
        raise Reject("period_not_tokenizable")
    if kind == "fiscal_year":
        return f"FY{year}"
    if kind == "quarter":
        quarter = fp.get("quarter")
        if not isinstance(quarter, int) or isinstance(quarter, bool):
            raise Reject("period_not_tokenizable")
        return f"FY{year}Q{quarter}"
    if kind in ("half_year", "nine_months"):
        letter = "H" if kind == "half_year" else "N"
        end = fp.get("calendar_end")
        if isinstance(end, str) and len(end) == 10:
            return f"FY{year}{letter}-{end[5:7]}{end[8:10]}"
        return f"FY{year}{letter}"
    if kind == "multi_year":
        end_year = fp.get("end_year")
        if isinstance(end_year, int) and not isinstance(end_year, bool):
            return f"FY{year}-{end_year}"
        return f"FY{year}M"
    raise Reject("period_not_tokenizable")


def _is_period(value: Any) -> bool:
    return isinstance(value, Mapping) and "period_kind" in value


def _counterparty(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        raise Reject("counterparty_set_not_keyable")
    return None


def fact_slot(event: Mapping[str, Any]) -> dict[str, Any]:
    """fact_log.v1 slot for one event; only the slot keys the schema allows."""
    template = event.get("schema")
    if template == T1:
        kind = (
            "t1_execution_under_program"
            if event.get("primary_amount_role") == "executed"
            else "t1_authorization_program"
        )
        slot: dict[str, Any] = {"kind": kind, "action_type": event.get("action_type")}
        if _is_period(event.get("horizon_period")):
            slot["horizon_token"] = period_token(event["horizon_period"])
        return slot
    if template == T2:
        slot = {"kind": "t2_metric_period_counterparty", "metric": event.get("metric")}
        if _is_period(event.get("fiscal_period")):
            slot["fiscal_period_token"] = period_token(event["fiscal_period"])
        slot["counterparty_company_id"] = _counterparty(event.get("counterparty_company_id"))
        return slot
    if template == T3:
        name = event.get("object_name")
        if not isinstance(name, str):
            raise Reject("object_name_not_keyable")
        if len(name) > OBJECT_NAME_MAX:
            raise Reject("object_name_over_fact_key_limit")
        return {
            "kind": "t3_object_counterparty",
            "event_kind": event.get("event_kind"),
            "object_name": name,
            "counterparty_company_id": _counterparty(event.get("counterparty_company_id")),
        }
    raise Reject("template_unknown")


# --------------------------------------------------------------------------- leaf payload


def _number(value: Any, counts: Counter) -> Any:
    if isinstance(value, float) and value.is_integer():
        counts["leaf_int_normalised"] += 1
        return int(value)
    return value


def _leaf_value(quantity: Any, counts: Counter) -> Any:
    if not isinstance(quantity, Mapping):
        return None
    form = quantity.get("form")
    if form == "point":
        return _number(quantity.get("value"), counts)
    if form == "range":
        counts["leaf_range_carried"] += 1
        return {"low": _number(quantity.get("low"), counts), "high": _number(quantity.get("high"), counts)}
    return None


def leaf_payload(event: Mapping[str, Any], slot: Mapping[str, Any], counts: Counter) -> dict[str, Any]:
    """OwnerSnapshot.leaf_payloads entry: an owner-API input adapter, not a label remap."""
    template = event["schema"]
    leaf: dict[str, Any] = {
        "template": template,
        "quantity_terms": {},
        "commitment_status": event.get("commitment_status"),
        "negated": bool(event.get("negated", False)),
    }
    currency = None
    for key, field_name in LEAF_KEYS[template]:
        quantity = event.get(field_name)
        value = _leaf_value(quantity, counts)
        if value is None:
            continue
        leaf[key] = value
        # Preserve the canonical per-quantity unit, basis, period and evidence.
        # The scalar and structured term originate from this one quantity.
        leaf["quantity_terms"][key] = copy.deepcopy(dict(quantity))
        if currency is None and isinstance(quantity, Mapping) and quantity.get("currency"):
            currency = quantity["currency"]
    if currency is not None:
        leaf["currency"] = currency
    if event.get("channel_hint"):
        leaf["channel_hint"] = event["channel_hint"]
    if template == T1 and "horizon_token" in slot:
        leaf["horizon_token"] = slot["horizon_token"]
    if template == T3:
        leaf["object_name"] = slot["object_name"]
    return leaf


# --------------------------------------------------------------------------- record pieces


def _span_of(value: Any) -> Mapping[str, Any] | None:
    if not isinstance(value, Mapping):
        return None
    if isinstance(value.get("span"), Mapping):
        return value["span"]
    evidence = value.get("evidence")
    if isinstance(evidence, Mapping) and isinstance(evidence.get("span"), Mapping):
        return evidence["span"]
    return None


def evidence_ref(event: Mapping[str, Any]) -> dict[str, Any]:
    template = event["schema"]
    ladder = list(EVIDENCE_LADDER[template])
    if template == T1:
        primary = _T1_PRIMARY.get(event.get("primary_amount_role"))
        if primary:
            ladder.remove(primary)
            ladder.insert(1, primary)
    for field_name in ladder:
        span = _span_of(event.get(field_name))
        if span is None:
            continue
        span_id = span.get("span_id")
        document_id = span.get("document_id")
        if not isinstance(span_id, str) or not _SPAN_ID.match(span_id) or not isinstance(document_id, str):
            raise Reject("evidence_span_unbound")
        return {"form": "owner_span_ref", "document_id": document_id, "span_id": span_id}
    return thesis.FieldAbsence("evidence", "no span-backed field", ("evidence",)).to_dict()


def accession_of(document_id: str) -> str:
    parts = document_id.split(":")
    if len(parts) >= 3 and parts[0] == "sec" and parts[1]:
        return parts[1]
    return sha256(document_id.encode()).hexdigest()


def _parse_dt(value: Any) -> datetime:
    if not isinstance(value, str):
        raise Reject("observed_at_invalid")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise Reject("observed_at_invalid") from None
    if parsed.tzinfo is None:
        raise Reject("observed_at_invalid")
    return parsed


# --------------------------------------------------------------------------- pipeline


def _read_rows(paths: Iterable[Path]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in paths:
        with Path(path).open() as fh:
            for line in fh:
                if line.strip():
                    rows.append(json.loads(line))
    return rows


def _refused_out(out: Path) -> bool:
    target = out.resolve()
    log_dir = Path(thesis.DEFAULT_LOG_PATH).parent
    guarded = {(Path.cwd() / log_dir).resolve(), (Path(__file__).resolve().parents[2] / log_dir).resolve()}
    return any(target == g or g in target.parents for g in guarded)


def run(events_paths: list[Path], out: Path, as_of: str | None = None) -> dict[str, Any]:
    """Build the fact log, views and evidence from stage-one rows. Raises on a refused --out."""
    if _refused_out(out):
        raise Reject("out_refused")
    rows = _read_rows(events_paths)
    counts: Counter = Counter()
    deferred: Counter = Counter()
    rejected: Counter = Counter()
    novelty: Counter = Counter()
    rules: Counter = Counter()
    adapter: Counter = Counter()

    shadows = {bool(r.get("shadow")) for r in rows if isinstance(r, Mapping)}
    shadow = shadows == {True}
    mixed = len(shadows) > 1

    candidates: list[tuple[datetime, str, dict[str, Any]]] = []
    seen: set[str] = set()
    for row in rows:
        try:
            if mixed:
                raise Reject("shadow_mixed")
            event = row.get("event") if isinstance(row, Mapping) else None
            if not isinstance(event, Mapping):
                raise Reject("event_missing")
            if event.get("authority") != "context_only":
                raise Reject("authority_not_context_only")
            if event.get("unsolicited_instruction_detected") is not False:
                raise Reject("unsolicited_instruction")
            fact_id = event.get("fact_id")
            if not isinstance(fact_id, str) or not fact_id:
                raise Reject("event_missing")
            if fact_id in seen:
                raise Reject("duplicate_fact_id")
            seen.add(fact_id)
            if event.get("schema") not in TEMPLATES:
                raise Reject("template_unknown")
            slot = fact_slot(event)
            leaf = leaf_payload(event, slot, counts)
            ref = evidence_ref(event)
            observed = _parse_dt(event.get("observed_at"))
        except Reject as exc:
            rejected[exc.code] += 1
            continue
        candidates.append((observed, fact_id, {
            "row": row, "event": event, "slot": slot, "leaf": leaf, "evidence": ref,
        }))
    candidates.sort(key=lambda c: (c[0], c[1]))

    log: dict[str, Any] = thesis.FactLog(records=()).to_dict()
    history: list[FactObservation] = []
    revisions: list[tuple[FactObservation, str]] = []  # (observation, fact_id) of fact_revision records
    leaves: dict[str, dict[str, Any]] = {}
    appended: list[tuple[dict[str, Any], dict[str, Any], dict[str, Any]]] = []  # (row, event, record)

    for observed, fact_id, item in candidates:
        event, slot, leaf = item["event"], item["slot"], item["leaf"]
        template = event["schema"]
        company_id = event.get("company_id")
        fingerprint = thesis.quantity_fingerprint(leaf, template)
        obs = FactObservation(
            fact_key=(str(company_id), slot["kind"], template, thesis.canonical_json(slot)),
            quantity=fingerprint.get("canonical_sha256"),
            counterparty=slot.get("counterparty_company_id"),
            commitment=event.get("commitment_status"),
            observed_at=observed,
            source_family=SOURCE_FAMILY,
            fact_id=fact_id,
        )
        try:
            decision = assign_novelty(history, obs)
        except NoveltyError:
            rejected["novelty_error"] += 1
            continue
        same_key = [(o, fid) for o, fid in revisions if o.fact_key == obs.fact_key]
        if decision.value in FACT_REVISION_NOVELTY:
            record_kind, grain, reports = "fact_revision", "fact_revision", None
        elif decision.value == "new_reporting_of_old_fact":
            equal = [
                fid for o, fid in same_key
                if (o.quantity, o.counterparty, o.commitment) == (obs.quantity, obs.counterparty, obs.commitment)
            ]
            if not equal:
                deferred["manifestation_without_revision"] += 1
                continue
            record_kind, grain, reports = "manifestation", "article_manifestation", equal[-1]
        elif decision.value == "commentary":
            if not same_key:
                deferred["commentary_without_live_fact"] += 1
                continue
            record_kind, grain, reports = "manifestation", "article_manifestation", same_key[-1][1]
        else:
            rejected["novelty_unmapped"] += 1
            continue

        row = item["row"]
        document_id = event.get("document_id")
        accession = accession_of(str(document_id))
        record = {
            "record_kind": record_kind,
            "cluster_grain": grain,
            "fact_id": fact_id,
            "document_id": document_id,
            "observed_at": event.get("observed_at"),
            "source_available_at": event.get("source_available_at"),
            "supersedes_fact_id": decision.supersedes_fact_id,
            "company_id": company_id,
            "cluster_id": "ev2_" + sha256(accession.encode()).hexdigest()[:16],
            "novelty": decision.value,
            "polarity": thesis.assign_polarity(
                bool(event.get("negated", False)), event.get("contrary_mechanism_quote")
            ),
            "fact_key": {"company_id": company_id, "template": template, "slot": slot},
            "provenance": {
                "origin_document_id": document_id,
                "origin_claim_id": "claim_" + sha256(f"{row.get('case_id')}|{fact_id}".encode()).hexdigest()[:24],
                "root_family_id": accession,
                "source_family": SOURCE_FAMILY,
            },
            "evidence": item["evidence"],
            "payload_schema": template,
            "ci_event_id": thesis.FieldAbsence(
                "ci_event_id", "company_event join not performed in producer", ("ci_event_id",)
            ).to_dict(),
            "owner_claim_ids": [],
            "quantity_fingerprint": fingerprint,
            "reports_fact_id": reports,
            "linked_fact_ids": [],
            "unsolicited_instruction_detected": False,
        }
        try:
            log = thesis.append_records(log, [record])
        except thesis.ThesisError as exc:
            rejected[f"log_{exc.code}"] += 1
            continue
        history.append(obs)
        if record_kind == "fact_revision":
            revisions.append((obs, fact_id))
        leaves[fact_id] = leaf
        novelty[decision.value] += 1
        rules[str(decision.rule).split(":")[0]] += 1
        appended.append((row, event, log["records"][-1]))

    views: tuple[dict[str, Any], ...] = ()
    project_error = None
    effective_as_of = as_of or (max(str(rec["observed_at"]) for _, _, rec in appended) if appended else None)
    if effective_as_of is not None:
        try:
            views = thesis.project(log, thesis.OwnerSnapshot(leaf_payloads=leaves), effective_as_of)
        except thesis.ThesisError as exc:
            project_error = exc.code
            views = ()

    evidence_rows: list[dict[str, Any]] = []
    for row, event, record in appended:
        candidate = copy.deepcopy(dict(event))
        candidate["novelty"] = record["novelty"]
        candidate["supersedes_fact_id"] = record["supersedes_fact_id"]
        candidate["cluster_grain"] = record["cluster_grain"]
        try:
            produced = adapt_batch([candidate])
        except ProphetAdapterError as exc:
            adapter[f"adapter:{exc.code}"] += 1
            continue
        except (KeyError, TypeError, ValueError) as exc:
            # An owner crash on a contract-valid event is counted by class, never fatal
            # (DEC:NEWS-IMPACT-W3-PRODUCER-STAGE2).
            adapter[f"adapter_crash:{type(exc).__name__}"] += 1
            continue
        adapter["ok"] += len(produced)
        for item in produced:
            evidence_rows.append({
                "case_id": row.get("case_id"),
                "shadow": shadow,
                "fact_id": record["fact_id"],
                "evidence": item.to_dict(),
            })

    out.mkdir(parents=True, exist_ok=True)
    (out / "fact_log.json").write_text(json.dumps(log, indent=2, sort_keys=True) + "\n")
    with (out / "thesis_views.jsonl").open("w") as fh:
        for view in views:
            fh.write(json.dumps({"shadow": shadow, "view": view}, sort_keys=True) + "\n")
    with (out / "prophet_evidence.jsonl").open("w") as fh:
        for evidence_row in evidence_rows:
            fh.write(json.dumps(evidence_row, sort_keys=True) + "\n")

    record_kinds = Counter(rec["record_kind"] for rec in log["records"])
    report = {
        "producer_facts_version": PRODUCER_FACTS_VERSION,
        "mode": "shadow" if shadow else "adjudicated",
        "n_rows": len(rows),
        "n_records": dict(sorted(record_kinds.items())),
        "novelty": dict(sorted(novelty.items())),
        "rules": dict(sorted(rules.items())),
        "deferred": dict(sorted(deferred.items())),
        "rejected": dict(sorted(rejected.items())),
        "adapter": dict(sorted(adapter.items())),
        "n_views": len(views),
        "as_of_utc": effective_as_of,
        "project_error": project_error,
        "normalisation": dict(sorted(counts.items())),
    }
    (out / "facts_report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return report


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--events", type=Path, nargs="+", required=True, help="stage-one events*.jsonl files")
    ap.add_argument("--out", type=Path, required=True, help="output directory (never data/news_impact)")
    ap.add_argument("--as-of", default=None, help="projection as_of_utc (default: latest observed_at)")
    args = ap.parse_args(argv)
    try:
        report = run(args.events, args.out, args.as_of)
    except Reject as exc:
        print(json.dumps({"refused": exc.code}))
        return 2
    keys = ("mode", "n_rows", "n_records", "deferred", "rejected", "adapter", "n_views", "project_error")
    print(json.dumps({k: report[k] for k in keys}, sort_keys=True))
    return 1 if report["project_error"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
