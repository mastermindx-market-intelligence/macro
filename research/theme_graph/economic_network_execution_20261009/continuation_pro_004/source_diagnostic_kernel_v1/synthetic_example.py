"""Wholly artificial input writer and explicit example runner; no acquisitions.

Generated IDs, venues, publishers, numeric tokens and historical sets are made up.
They are never substitutes for WP02's 30 genuine difficult disclosure cases.
"""
from collections import Counter
from hashlib import sha256
import json

GROUPS = ("US", "CN_MAINLAND", "HK", "CA", "UK", "JP", "EU")
ACTIVITIES = ("SEMICONDUCTOR_CLOUD", "INDUSTRIALS", "CONSUMER", "ENERGY_MATERIALS", "FINANCIALS", "HEALTHCARE")
EVENT_KINDS = ("ADMISSION", "REMOVAL", "TRANSFER", "CONVERSION", "IDENTITY_REPLACEMENT", "PRIMARY_STATUS_CHANGE")


def encode(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def source(request, text):
    raw = text.encode("utf-8")
    digest = sha256(raw).hexdigest()
    sid = "ARTIFICIAL_SOURCE:" + digest
    if not any(row["source_id"] == sid for row in request["sources"]):
        request["sources"].append({"source_id": sid, "content": text, "sha256": digest, "byte_length": len(raw)})
    return {"source_id": sid, "start": 0, "end": len(raw)}


def assertion(request, aid, value, *, coordinate="2026-09-30", basis="ORDINARY_D_UNITS",
              public="2026-10-01T00:00:00Z", publisher="ARTIFICIAL_PUBLISHER", valid_to=None):
    return {"assertion_id": aid, "publisher_id": publisher, "coordinate": coordinate,
            "valid_to": valid_to, "public_upper": public, "value": value, "unit_basis": basis,
            "status": "ACTUAL", "evidence": source(request, value)}


def point_bundle(request, aid, value, **kwargs):
    return {"state_kind": "POINT", "assertions": [assertion(request, aid, value, **kwargs)], "relations": []}


def relation(request, rid, old, new=None, *, kind="SUPERSEDES", public="2026-10-02T00:00:00Z"):
    return {"relation_id": rid, "kind": kind, "publisher_id": old["publisher_id"],
            "old_id": old["assertion_id"], "new_id": new["assertion_id"] if new else None,
            "fact_coordinate": old["coordinate"], "unit_basis": old["unit_basis"],
            "public_upper": public,
            "evidence": source(request, kind + ":" + (new["assertion_id"] if new else "") + ":" + old["assertion_id"]),
            "resolution_owner_id": "UNAUTHENTICATED_ARTIFICIAL_OWNER"}


def bind_history_sources(request):
    h = request["history"]
    for field, id_field in (("anchor_members", "anchor_source_id"), ("target_members", "target_source_id"), ("events", "events_source_id")):
        h[id_field] = source(request, encode(h[field]).decode("utf-8"))["source_id"]


def refresh_counts(request):
    h, records = request["history"], request["records"]
    anchor_count = len(h["anchor_members"])
    members = h["target_members"]
    kinds = Counter(row["kind"] for row in h["events"])
    request["counts"] = {"source_declared_total": anchor_count, "exhaustive_total": anchor_count,
        "raw_record_count": anchor_count, "parsed_record_count": anchor_count,
        "duplicates_resolved_count": len(members) - len({m["record_id"] for m in members}),
        "anchor_count": anchor_count, "resulting_d_member_count": len(members),
        "identity_resolved_issuer_count": len({r["issuer_id"] for r in records if r["issuer_id"] is not None}),
        "evidenced_out_of_scope_count": sum(r["eligibility"] == "EXCLUDED" for r in records),
        "potentially_eligible_omission_count": 0,
        "unresolved_potentially_eligible_count": sum(r["eligibility"] != "EXCLUDED" and
            (r["eligibility"] == "UNRESOLVED" or r["issuer_id"] is None or r["activity"] is None or not r["primary_groups"])
            for r in records)}
    request["counts"].update({"event_" + kind: kinds[kind] for kind in EVENT_KINDS})


def make_request(per_pool=4):
    if type(per_pool) is not int or not 0 <= per_pool <= 10:
        raise ValueError("example pool size outside bounded fixture range")
    request = {"schema": "research.gmi.wp02.source_diagnostic_request/v1", "mode": "SYNTHETIC_MODEL",
               "sources": [], "records": [], "history": {}, "fx": {}, "counts": {},
               "stress_cases": [], "claims": {}}
    for country in GROUPS:
        for activity in ACTIVITIES:
            for index in range(per_pool):
                issuer = "ARTIFICIAL:" + country + ":" + activity + ":" + str(index)
                cls = {"class_id": "ORDINARY", "kind": "ORDINARY", "d_basis": "ORDINARY_D_UNITS",
                       "shares": point_bundle(request, issuer + ":SHARES", "1000000", coordinate="2026-09-15"),
                       "price": point_bundle(request, issuer + ":PRICE", str(per_pool - index)),
                       "quote_scale": "1", "quote_scale_evidence": source(request, "1"), "currency": "USD",
                       "counter": {"mic": "ARTIFICIAL_MIC", "security_id": issuer + ":SECURITY"},
                       "calendar": ["2026-09-30"], "actions": [], "declared_event_ids": [],
                       "share_bridge_event_ids": [], "price_bridge_event_ids": []}
                request["records"].append({"record_id": issuer + ":RECORD", "issuer_id": issuer,
                    "eligibility": "ELIGIBLE", "primary_groups": [country], "activity": activity,
                    "exclusion_reason": None, "exclusion_evidence": None,
                    "class_ids": ["ORDINARY"], "classes": [cls]})
    members = [{"member_id": r["issuer_id"] + ":MEMBER", "record_id": r["record_id"],
                "partition_id": "ARTIFICIAL_PARTITION:" + r["primary_groups"][0],
                "instrument": "ORDINARY", "primary_status": "PRIMARY"} for r in request["records"]]
    request["history"] = {"kind": "SNAPSHOT", "target_date": "2026-09-30", "anchor_date": "2026-09-30",
        "anchor_public_upper": "2026-10-01T00:00:00Z",
        "partitions": [{"partition_id": "ARTIFICIAL_PARTITION:" + c, "jurisdiction": c} for c in GROUPS],
        "declared_partition_ids": ["ARTIFICIAL_PARTITION:" + c for c in GROUPS],
        "anchor_members": [dict(m) for m in members], "target_members": [dict(m) for m in members],
        "anchor_source_id": "", "target_source_id": "", "events_source_id": "", "events": [],
        "coverage_start": "2026-09-30", "coverage_end": "2026-09-30",
        "covered_event_kinds": list(EVENT_KINDS), "declared_event_ids": [],
        "expected_anchor_member_ids": [m["member_id"] for m in members],
        "expected_target_member_ids": [m["member_id"] for m in members]}
    request["fx"] = {"series": "ECB euro foreign exchange reference rates", "available_dates": ["2026-09-30"],
        "reference_date": "2026-09-30", "rates": [{"currency": "USD", "bundle": point_bundle(
            request, "ARTIFICIAL:ECB:USD", "1.1", basis="UNITS_USD_PER_EUR")} ]}
    bind_history_sources(request)
    refresh_counts(request)
    return request


def main():
    import argparse
    import sys
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--emit-input", action="store_true", help="Emit wholly artificial fixture JSON")
    args = parser.parse_args()
    if not args.emit_input:
        parser.error("Use --emit-input; execute source_diagnostic.py with explicit policy/adoption files")
    sys.stdout.buffer.write(encode(make_request()) + b"\n")


if __name__ == "__main__":
    main()
