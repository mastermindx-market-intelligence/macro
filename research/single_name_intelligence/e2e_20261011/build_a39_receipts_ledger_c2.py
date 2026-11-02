"""A39 capture-2 delegated-lane receipts ledger builder (SNI commission 8659).

This module is an SNI-local DRAFT contract. It consumes owner-supplied
launcher receipt values (the per-run TSV captured at the seat, plus the
lane's own final stdout line of the form LANE: STATUS sha). It does not fork
or re-implement Data OS identity, Company Event/Earnings, FIF, Capital
Structure, Stock Identity, Options, Research Vault, or
qledger/Evaluation.

Identity identifiers are caller-supplied opaque strings. This module does
not mint HK/US issuer or security identifiers.

Setting any of rank_authority, gate_authority, size_authority,
signal_authority, escalation_authority, trade_authority true is refused.

A lane status of PASS or PARTIAL is recorded as status only. This ledger
does not feed a ranker, gate, sizer, escalation, or trade path.

This builder is stdlib only (json, csv, io, pathlib, collections) and
contains no calls to .strip, .lower, .upper, .casefold, or .replace. File
reads/writes happen only under if __name__ == "__main__".
"""
from __future__ import annotations

import json
import pathlib
from collections import Counter


LADDER = [
    "ACK",
    "QUEUED",
    "START",
    "RUNNING",
    "DELIVERED",
    "CI",
    "MERGED",
    "PRODUCTION_PROOF",
    "ACCEPTANCE",
]

BY_RUNG_ORDER = [
    "ACK",
    "QUEUED",
    "START",
    "RUNNING",
    "NOT_STARTED",
    "RUNNING_OR_UNKNOWN_AT_CAPTURE",
    "EXITED_NO_RESULT",
    "EXITED_NONZERO",
    "DELIVERED",
    "CI",
    "MERGED",
    "PRODUCTION_PROOF",
    "ACCEPTANCE",
]

AUTHORITY_FLAGS = (
    "rank_authority",
    "gate_authority",
    "size_authority",
    "signal_authority",
    "escalation_authority",
    "trade_authority",
)

TSV_COLUMNS = (
    "run_id",
    "host",
    "model",
    "reserved_at",
    "lease_ok_at",
    "launched_at",
    "done_at",
    "rc",
    "signal",
    "native_started",
    "output_complete",
    "usage_total_tokens",
    "lane",
    "status",
    "lane_head",
    "integrated_on_main",
)

ROW_KEYS = (
    "run_id",
    "host",
    "model",
    "reserved_at",
    "lease_ok_at",
    "launched_at",
    "done_at",
    "rc",
    "signal",
    "native_started",
    "output_complete",
    "usage_total_tokens",
    "lane",
    "status",
    "lane_head",
    "integrated_on_main",
    "rule_id",
    "rung_reached",
    "rung_evidence",
)

CAPTURED_AT = "2026-10-14T07:11Z"
CAPTURE_ID = "C2"
SCHEMA_VERSION = "1"

SOURCE_PARAGRAPH = (
    "Seat capture at 2026-10-14T07:11Z of the lane launcher per-run receipts "
    "captured in the A39_LANE_RECEIPTS_C2_INPUT.tsv file, together with each "
    "lane's own final stdout line of the form LANE: STATUS sha. Host labels "
    "in the rows are recorded by the launcher (bm1, bmb, mb, mini1, mini3, "
    "ubuntu0, ubuntu1, ubuntu2, ubuntu3). This file is an SNI-local draft "
    "contract that consumes those owner-supplied receipt values."
)

PRIOR_PATH = "research/single_name_intelligence/e2e_20261011/A39_LANE_RECEIPTS_LEDGER.json"

RUNG_RULES = [
    {
        "id": "never_started",
        "when": "rc in {75, 76, 78}",
        "rung_reached": "NOT_STARTED",
        "note": (
            "Launcher refused or failed before the remote CLI started; 75 is "
            "a launcher admission refusal, 76 is a lease refusal, 78 is an "
            "admission refusal at a different launcher stage. The lane never "
            "started. START and every later rung stay unclaimed even if "
            "launched_at is present."
        ),
    },
    {
        "id": "running_or_unknown",
        "when": "rc is None and done_at is None",
        "rung_reached": "RUNNING_OR_UNKNOWN_AT_CAPTURE",
        "note": "Capture ended with no DONE event. This is never DELIVERED.",
    },
    {
        "id": "exited_nonzero",
        "when": "rc in {1, 124}",
        "rung_reached": "EXITED_NONZERO",
        "note": "124 is a launcher timeout; 1 is a non-zero remote CLI exit.",
    },
    {
        "id": "delivered",
        "when": (
            "rc == 0 and lane, status, lane_head are all present and "
            "output_complete is not False"
        ),
        "rung_reached": "DELIVERED",
        "note": (
            "output_complete may be None for non-native launcher modes; that "
            "alone does not block DELIVERED."
        ),
    },
    {
        "id": "exited_no_result",
        "when": "rc == 0 and any of lane, status, lane_head is missing",
        "rung_reached": "EXITED_NO_RESULT",
        "note": "No parseable final line. This is never DELIVERED.",
    },
    {
        "id": "capture_ceiling",
        "when": "always in this ledger",
        "rung_reached": "never claim CI, MERGED, PRODUCTION_PROOF, ACCEPTANCE",
        "note": (
            "CI, MERGED, PRODUCTION_PROOF, and ACCEPTANCE are never claimed "
            "by this capture."
        ),
    },
    {
        "id": "integrated_annotation",
        "when": "integrated_on_main is non-empty",
        "rung_reached": "annotation only",
        "note": (
            "integrated_on_main records a cherry-pick trailer naming "
            "lane_head on main. The rung stays DELIVERED. Integration is "
            "not acceptance."
        ),
    },
]

BOUNDS = [
    "Launcher receipts captured at 2026-10-14T07:11Z are the only source.",
    "Orchestrator-native work is not covered.",
    "Lanes launched by other seats are not covered.",
    "Rows past DELIVERED need per-row CI and merge receipts, which this capture does not hold.",
    "integrated_on_main records a cherry-pick trailer on main and is not acceptance.",
    "A PASS status is the lane's own claim, judged separately by the seat.",
    "Usage tokens are absent for non-native launcher modes.",
    "rc 78 is a launcher admission refusal.",
    "No row in this ledger is at CI, MERGED, PRODUCTION_PROOF, or ACCEPTANCE.",
    "This draft consumes owner-supplied receipt values; it does not mint issuer or security identifiers.",
    "This module does not feed a ranker, gate, sizer, escalation, or trade path.",
]


def _parse_int(value):
    if value is None or value == "":
        return None
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(
            "not int: %r" % (value,)
        ) from exc


def _parse_bool(value):
    if value == "True":
        return True
    if value == "False":
        return False
    if value is None or value == "":
        return None
    raise ValueError("not bool: %r" % (value,))


def _parse_tsv(tsv_text):
    """Parse the TSV text deterministically. Returns list of typed row dicts."""
    lines = tsv_text.split("\n")
    rows = []
    if lines and lines[0] != "":
        header = lines[0].split("\t")
        if len(header) != 16:
            raise ValueError(
                "bad TSV header column count: %d" % len(header)
            )
        for idx, line in enumerate(lines[1:], start=1):
            if line == "":
                continue
            parts = line.split("\t")
            if len(parts) != 16:
                raise ValueError(
                    "bad TSV row column count at line %d: %d"
                    % (idx, len(parts))
                )
            row = {
                "run_id": parts[0] if parts[0] != "" else None,
                "host": parts[1] if parts[1] != "" else None,
                "model": parts[2] if parts[2] != "" else None,
                "reserved_at": (
                    parts[3] if parts[3] != "" else None
                ),
                "lease_ok_at": (
                    parts[4] if parts[4] != "" else None
                ),
                "launched_at": (
                    parts[5] if parts[5] != "" else None
                ),
                "done_at": parts[6] if parts[6] != "" else None,
                "rc": _parse_int(parts[7]),
                "signal": parts[8] if parts[8] != "" else None,
                "native_started": _parse_bool(parts[9]),
                "output_complete": _parse_bool(parts[10]),
                "usage_total_tokens": _parse_int(parts[11]),
                "lane": parts[12] if parts[12] != "" else None,
                "status": parts[13] if parts[13] != "" else None,
                "lane_head": (
                    parts[14] if parts[14] != "" else None
                ),
                "integrated_on_main": (
                    parts[15] if parts[15] != "" else None
                ),
            }
            rows.append(row)
    return rows


def classify(row):
    """Apply the R1..R5 rung rules to one TSV row.

    Returns (rule_id, rung_reached). Raises ValueError when no rule applies.
    """
    rc = row["rc"]
    done_at = row["done_at"]
    launched_at = row["launched_at"]
    output_complete = row["output_complete"]
    lane = row["lane"]
    status = row["status"]
    lane_head = row["lane_head"]

    if rc in (75, 76, 78):
        return ("never_started", "NOT_STARTED")
    if rc is None and done_at is None:
        return ("running_or_unknown", "RUNNING_OR_UNKNOWN_AT_CAPTURE")
    if rc in (1, 124):
        return ("exited_nonzero", "EXITED_NONZERO")
    if rc == 0:
        if (
            lane is not None
            and status is not None
            and lane_head is not None
            and output_complete is not False
        ):
            return ("delivered", "DELIVERED")
        return ("exited_no_result", "EXITED_NO_RESULT")
    if rc is None and done_at is not None:
        raise ValueError(
            "rc None with done_at present on %s"
            % (row.get("run_id") or "<no run_id>",)
        )
    raise ValueError(
        "unknown rc on %s: rc=%r done_at=%r launched_at=%r"
        % (
            row.get("run_id") or "<no run_id>",
            rc,
            done_at,
            launched_at,
        )
    )


def _rung_evidence(row, rung_reached):
    """Build rung_evidence per spec item 4 (ladder-ordered)."""
    evidence = [{"rung": "ACK", "field": "run_id"}]
    if row["reserved_at"] is not None:
        evidence.append({"rung": "QUEUED", "field": "reserved_at"})
    if (
        row["launched_at"] is not None
        and rung_reached != "NOT_STARTED"
    ):
        evidence.append({"rung": "START", "field": "launched_at"})
    if (
        row["native_started"] is True
        and rung_reached != "NOT_STARTED"
    ):
        evidence.append(
            {"rung": "RUNNING", "field": "native_started"}
        )
    if rung_reached == "DELIVERED":
        evidence.append({"rung": "DELIVERED", "field": "lane_head"})
    return evidence


def _short(value, length):
    if value is None or value == "":
        return ""
    return str(value)[:length]


def _cell(value):
    if value is None or value == "":
        return ""
    return str(value)


def _summarize(rows, c1):
    """Build the summary dict per spec item 8."""
    by_rung = {key: 0 for key in BY_RUNG_ORDER}
    for r in rows:
        by_rung[r["rung_reached"]] += 1
    by_host = Counter()
    by_rc = Counter()
    by_model = Counter()
    by_signal = Counter()
    for r in rows:
        by_host[_cell(r["host"]) if r["host"] is not None else "empty"] += 1
        by_rc[str(r["rc"]) if r["rc"] is not None else "empty"] += 1
        by_model[_cell(r["model"]) if r["model"] is not None else "empty"] += 1
        by_signal[_cell(r["signal"]) if r["signal"] is not None else "empty"] += 1
    delivered_by_claim = Counter()
    for r in rows:
        if r["rung_reached"] == "DELIVERED":
            delivered_by_claim[
                _cell(r["status"]) if r["status"] is not None else "empty"
            ] += 1
    integrated = sum(
        1 for r in rows if r.get("integrated_on_main") is not None
    )
    usage_present = sum(
        1 for r in rows if r.get("usage_total_tokens") is not None
    )
    c2_ids = [r["run_id"] for r in rows if r["run_id"] is not None]
    c1_ids = [r["run_id"] for r in c1["rows"] if r.get("run_id") is not None]
    c1_set = set(c1_ids)
    c2_set = set(c2_ids)
    overlap = c1_set & c2_set
    disjoint = len(overlap) == 0
    return {
        "rows": len(rows),
        "by_rung": by_rung,
        "by_host": dict(sorted(by_host.items())),
        "by_rc": dict(sorted(by_rc.items())),
        "by_model": dict(sorted(by_model.items())),
        "by_signal": dict(sorted(by_signal.items())),
        "delivered_by_claim": dict(sorted(delivered_by_claim.items())),
        "integrated_on_main_annotated": integrated,
        "usage_tokens_present": usage_present,
        "combined_with_prior": {
            "rows": len(c1_ids) + len(c2_ids),
            "run_ids_disjoint": disjoint,
        },
    }


def _build_rows(parsed_rows):
    """Build the per-row dicts (preserves TSV order)."""
    out = []
    for row in parsed_rows:
        rule_id, rung_reached = classify(row)
        evidence = _rung_evidence(row, rung_reached)
        out.append({
            "run_id": row["run_id"],
            "host": row["host"],
            "model": row["model"],
            "reserved_at": row["reserved_at"],
            "lease_ok_at": row["lease_ok_at"],
            "launched_at": row["launched_at"],
            "done_at": row["done_at"],
            "rc": row["rc"],
            "signal": row["signal"],
            "native_started": row["native_started"],
            "output_complete": row["output_complete"],
            "usage_total_tokens": row["usage_total_tokens"],
            "lane": row["lane"],
            "status": row["status"],
            "lane_head": row["lane_head"],
            "integrated_on_main": row["integrated_on_main"],
            "rule_id": rule_id,
            "rung_reached": rung_reached,
            "rung_evidence": evidence,
        })
    return out


def _render_md(ledger):
    """Render the markdown view from the JSON ledger per spec item 10."""
    summary = ledger["summary"]
    by_rung = summary["by_rung"]
    out = []
    out.append("# A39 lane receipts ledger — capture 2")
    out.append("")
    out.append(
        "Captured at %s. Schema version %s. Capture id %s."
        % (ledger["captured_at"], ledger["schema_version"], ledger["capture_id"])
    )
    out.append("")
    out.append("## Summary")
    out.append("")
    out.append("| rung | count |")
    out.append("| --- | ---: |")
    for key in BY_RUNG_ORDER:
        out.append("| %s | %s |" % (key, by_rung.get(key, 0)))
    out.append("")
    out.append("| host | count |")
    out.append("| --- | ---: |")
    for host, count in summary["by_host"].items():
        out.append("| %s | %s |" % (host, count))
    out.append("")
    out.append("| rc | count |")
    out.append("| --- | ---: |")
    for rc_key, count in summary["by_rc"].items():
        out.append("| %s | %s |" % (rc_key, count))
    out.append("")
    out.append("| model | count |")
    out.append("| --- | ---: |")
    for model, count in summary["by_model"].items():
        out.append("| %s | %s |" % (model, count))
    out.append("")
    out.append("| signal | count |")
    out.append("| --- | ---: |")
    for sig, count in summary["by_signal"].items():
        out.append("| %s | %s |" % (sig, count))
    out.append("")
    out.append(
        "Rows: %s. integrated_on_main annotated: %s. usage_total_tokens "
        "present: %s. combined_with_prior rows: %s (disjoint=%s)."
        % (
            summary["rows"],
            summary["integrated_on_main_annotated"],
            summary["usage_tokens_present"],
            summary["combined_with_prior"]["rows"],
            summary["combined_with_prior"]["run_ids_disjoint"],
        )
    )
    out.append("")
    out.append(
        "This ledger records launcher receipts for %s delegated lanes "
        "captured at %s. Counts at capture: %s NOT_STARTED, %s "
        "RUNNING_OR_UNKNOWN_AT_CAPTURE, %s EXITED_NO_RESULT, %s "
        "EXITED_NONZERO, %s DELIVERED. %s rows carry an integrated_on_main "
        "annotation and stay DELIVERED. A launched lane is not a delivered "
        "lane, and a delivered lane is not a merged lane. No row is at CI, "
        "MERGED, PRODUCTION_PROOF, or ACCEPTANCE. A status of PASS or "
        "PARTIAL is the lane's own printed line. This file does not cover "
        "orchestrator-native work, lanes launched by other seats, or "
        "events after capture."
        % (
            summary["rows"],
            ledger["captured_at"],
            by_rung.get("NOT_STARTED", 0),
            by_rung.get("RUNNING_OR_UNKNOWN_AT_CAPTURE", 0),
            by_rung.get("EXITED_NO_RESULT", 0),
            by_rung.get("EXITED_NONZERO", 0),
            by_rung.get("DELIVERED", 0),
            summary["integrated_on_main_annotated"],
        )
    )
    out.append("")
    out.append("## Ladder and rules")
    out.append("")
    out.append(
        "A delegated lane passes through these rungs in order. None implies the next:"
    )
    out.append("")
    for i, rung in enumerate(ledger["ladder"], 1):
        out.append("%s. %s" % (i, rung))
    out.append("")
    out.append("Rules, applied in this order:")
    out.append("")
    for i, rule in enumerate(ledger["rung_rules"], 1):
        when = rule.get("when", "")
        effect = rule.get("rung_reached") or rule.get("note", "")
        out.append(
            "%s. `%s`: %s → %s"
            % (i, rule["id"], when, effect)
        )
    out.append("")
    out.append("## Rows")
    out.append("")
    out.append(
        "| run_id | host | rc | rung_reached | lane | status | lane_head | integrated_on_main |"
    )
    out.append("| --- | --- | ---: | --- | --- | --- | --- | --- |")
    for row in ledger["rows"]:
        out.append(
            "| %s | %s | %s | %s | %s | %s | %s | %s |"
            % (
                _cell(row["run_id"]),
                _cell(row["host"]),
                _cell(row["rc"]),
                _cell(row["rung_reached"]),
                _cell(row["lane"]),
                _cell(row["status"]),
                _short(row["lane_head"], 12),
                _short(row["integrated_on_main"], 12),
            )
        )
    out.append("")
    out.append("## Bounds")
    out.append("")
    for item in ledger["bounds"]:
        out.append("- %s" % item)
    out.append("")
    text = "\n".join(out)
    if not text.endswith("\n"):
        text = text + "\n"
    return text


def build(tsv_text, c1_json_text):
    """Build (json_text, md_text) for capture 2 from the inputs."""
    parsed_rows = _parse_tsv(tsv_text)
    c1 = json.loads(c1_json_text)
    rows = _build_rows(parsed_rows)
    summary = _summarize(rows, c1)
    ledger = {
        "schema_version": SCHEMA_VERSION,
        "capture_id": CAPTURE_ID,
        "captured_at": CAPTURED_AT,
        "source": SOURCE_PARAGRAPH,
        "prior_capture": {
            "path": PRIOR_PATH,
            "captured_at": c1.get("captured_at", ""),
            "rows": len(c1.get("rows", [])),
            "run_ids_disjoint": summary["combined_with_prior"][
                "run_ids_disjoint"
            ],
        },
        "ladder": list(LADDER),
        "rung_rules": list(RUNG_RULES),
        "rows": rows,
        "summary": summary,
        "bounds": list(BOUNDS),
        "rank_authority": False,
        "gate_authority": False,
        "size_authority": False,
        "signal_authority": False,
        "escalation_authority": False,
        "trade_authority": False,
    }
    json_text = json.dumps(ledger, indent=2, ensure_ascii=False) + "\n"
    md_text = _render_md(ledger)
    return (json_text, md_text)


def _main():
    base = pathlib.Path(__file__).resolve().parent
    tsv_path = base / "A39_LANE_RECEIPTS_C2_INPUT.tsv"
    c1_path = base / "A39_LANE_RECEIPTS_LEDGER.json"
    json_out = base / "A39_LANE_RECEIPTS_LEDGER_C2.json"
    md_out = base / "A39_LANE_RECEIPTS_LEDGER_C2.md"
    tsv_text = tsv_path.read_text()
    c1_text = c1_path.read_text()
    json_text, md_text = build(tsv_text, c1_text)
    json_out.write_text(json_text)
    md_out.write_text(md_text)


if __name__ == "__main__":
    _main()
