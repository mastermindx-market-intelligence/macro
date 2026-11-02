"""A39 delegated-lane receipts ledger tests (SNI commission 8659).

This module is an SNI-local DRAFT contract. It consumes owner-supplied
launcher receipt values (run log, native-terminal.json, usage.json, and the
lane's own final stdout line). It does not fork or re-implement Data OS
identity, Company Event/Earnings, FIF, Capital Structure, Stock Identity,
Options, Research Vault, or qledger/Evaluation.

Identity identifiers are caller-supplied opaque strings. This module does
not mint HK/US issuer or security identifiers.

Setting rank_authority, gate_authority, size_authority, signal_authority,
escalation_authority, or trade_authority true is refused.

A lane status of PASS or PARTIAL is recorded as lane_claim only. This
ledger does not feed a ranker, gate, sizer, escalation, or trade path.
"""
from __future__ import annotations

import json
import re
from copy import deepcopy
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
JSON_PATH = (
    ROOT
    / "research"
    / "single_name_intelligence"
    / "e2e_20261011"
    / "A39_LANE_RECEIPTS_LEDGER.json"
)
MD_PATH = (
    ROOT
    / "research"
    / "single_name_intelligence"
    / "e2e_20261011"
    / "A39_LANE_RECEIPTS_LEDGER.md"
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
    "native_started",
    "output_complete",
    "usage_total_tokens",
    "lane",
    "status",
    "lane_head",
    "int1_commit",
)

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

FORBIDDEN_RUNGS = ("CI", "MERGED", "PRODUCTION_PROOF", "ACCEPTANCE")
TS_FIELDS = ("reserved_at", "lease_ok_at", "launched_at", "done_at")
GAP_SHAS = ("12eade4b", "5f09242e")
GAP_SUBJECTS = {
    "12eade4b": "S2 v1.1 reprint",
    "5f09242e": "S2 v1.1 repair X2-01..08, A7-F1/F2/F5",
}

AUTHORITY_FLAGS = (
    "rank_authority",
    "gate_authority",
    "size_authority",
    "signal_authority",
    "escalation_authority",
    "trade_authority",
)

_PRIVACY_PATHS = ("/Users/", "/home/")
_PRIVACY_CREDS = ("token=", "Bearer", "ssh-")
_AUTH_RE = re.compile(r"auth(?!ority)", re.IGNORECASE)
_IP_RE = re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b")


class AuthorityRefused(ValueError):
    """Raised when a caller tries to set a program authority flag true."""


def load_ledger():
    with JSON_PATH.open() as fh:
        return json.load(fh)


def set_authority(ledger, flag, value):
    """Write an authority flag. True is refused; only literal False is stored."""
    if flag not in AUTHORITY_FLAGS:
        raise KeyError(flag)
    if value is True:
        raise AuthorityRefused("%s must remain false" % flag)
    if value is not False:
        raise AuthorityRefused("%s must be literal false" % flag)
    ledger[flag] = False
    return ledger


def _has_parseable_final_line(row):
    return bool(row.get("lane") and row.get("status") and row.get("lane_head"))


def compute_rung_reached(row):
    """Independent application of the A39 rung rules to raw receipt fields."""
    rc = row.get("rc")
    if rc in (75, 76):
        return "NOT_STARTED"
    done = row.get("done_at")
    if rc is None and not done:
        return "RUNNING_OR_UNKNOWN_AT_CAPTURE"
    launched = row.get("launched_at")
    native = row.get("native_started")
    if launched and native is True:
        pass
    if rc == 0:
        complete = row.get("output_complete")
        has_final = _has_parseable_final_line(row)
        if complete is True and has_final:
            return "DELIVERED"
        if not has_final:
            return "EXITED_NO_RESULT"
    if rc == 1:
        return "EXITED_NONZERO"
    raise AssertionError("no rule classified %s rc=%r" % (row.get("run_id"), rc))


def rung_mismatches(ledger):
    """Rows whose stored rung_reached disagrees with the rules."""
    errors = []
    for row in ledger["rows"]:
        expected = compute_rung_reached(row)
        stored = row.get("rung_reached")
        if stored != expected:
            errors.append(
                "%s stored=%s expected=%s" % (row.get("run_id"), stored, expected)
            )
    return errors


def overclaim_errors(ledger):
    """Honesty failures: later-rung claims the receipts do not support."""
    errors = []
    for row in ledger["rows"]:
        run_id = row.get("run_id")
        rung = row.get("rung_reached")
        if rung in FORBIDDEN_RUNGS:
            errors.append("%s rung_reached=%s" % (run_id, rung))
        if row.get("accepted") is True:
            errors.append("%s accepted=true" % run_id)
        if row.get("merged") is True:
            errors.append("%s merged=true" % run_id)
        if row.get("rc") in (75, 76) and rung != "NOT_STARTED":
            errors.append("%s rc=%s rung=%s" % (run_id, row.get("rc"), rung))
        computed = compute_rung_reached(row)
        if computed in ("RUNNING_OR_UNKNOWN_AT_CAPTURE", "EXITED_NO_RESULT"):
            if rung == "DELIVERED":
                errors.append("%s %s claimed DELIVERED" % (run_id, computed))
    return errors


def timestamp_errors(ledger):
    """Present timestamps must be monotone reserved <= lease <= launched <= done."""
    errors = []
    for row in ledger["rows"]:
        present = [row[k] for k in TS_FIELDS if row.get(k)]
        for left, right in zip(present, present[1:]):
            if left > right:
                errors.append(
                    "%s timestamp %s > %s" % (row.get("run_id"), left, right)
                )
    return errors


def privacy_errors(text):
    """Flag home paths, credential substrings, and IPv4 addresses.

    The substring 'authority' is allowed because the six program flags
    are required keys. Other 'auth' spellings are not.
    """
    errors = []
    for token in _PRIVACY_PATHS:
        if token in text:
            errors.append("path %s" % token)
    for token in _PRIVACY_CREDS:
        if token in text:
            errors.append("cred %s" % token)
    if _AUTH_RE.search(text):
        errors.append("auth")
    if _IP_RE.search(text):
        errors.append("ip")
    return errors


def _cell(value):
    if value is None or value == "":
        return ""
    return str(value)


def _summary_paragraph(ledger):
    summary = ledger["summary"]
    by_rung = summary["by_rung"]
    return (
        "This ledger records launcher receipts for %s delegated Grok lanes "
        "captured at %s. Counts at capture: %s NOT_STARTED, %s "
        "RUNNING_OR_UNKNOWN_AT_CAPTURE, %s EXITED_NO_RESULT, %s "
        "EXITED_NONZERO, %s DELIVERED. %s rows carry an INT1 cherry-pick "
        "annotation; INT1 PR 9120 was open and unmerged at capture, so those "
        "rows remain DELIVERED. A launched lane is not a delivered lane, and "
        "a delivered lane is not a merged lane. No row is at CI, MERGED, "
        "PRODUCTION_PROOF, or ACCEPTANCE. A lane_claim of PASS or PARTIAL is "
        "the lane's own printed line. Two INT1 cherry-picks have no launcher "
        "receipt and are listed as integration gaps. This file does not cover "
        "orchestrator-native work, lanes launched by other seats, or events "
        "after capture."
        % (
            summary["rows"],
            ledger["captured_at"],
            by_rung.get("NOT_STARTED", 0),
            by_rung.get("RUNNING_OR_UNKNOWN_AT_CAPTURE", 0),
            by_rung.get("EXITED_NO_RESULT", 0),
            by_rung.get("EXITED_NONZERO", 0),
            by_rung.get("DELIVERED", 0),
            summary["int1_integrated"],
        )
    )


def render_ledger_md(ledger):
    """Pure render of the markdown view from the JSON ledger."""
    lines = []
    summary = ledger["summary"]
    by_rung = summary["by_rung"]
    lines.append("# A39 lane receipts ledger")
    lines.append("")
    lines.append(
        "Captured at %s. Schema version %s."
        % (ledger["captured_at"], ledger["schema_version"])
    )
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append("| rung | count |")
    lines.append("| --- | ---: |")
    for key in (
        "NOT_STARTED",
        "RUNNING_OR_UNKNOWN_AT_CAPTURE",
        "EXITED_NO_RESULT",
        "EXITED_NONZERO",
        "DELIVERED",
        "CI",
        "MERGED",
        "PRODUCTION_PROOF",
        "ACCEPTANCE",
    ):
        lines.append("| %s | %s |" % (key, by_rung.get(key, 0)))
    lines.append("")
    lines.append("| host | count |")
    lines.append("| --- | ---: |")
    for host, count in summary["by_host"].items():
        lines.append("| %s | %s |" % (host, count))
    lines.append("")
    lines.append("| rc | count |")
    lines.append("| --- | ---: |")
    for rc_key, count in summary["by_rc"].items():
        lines.append("| %s | %s |" % (rc_key, count))
    lines.append("")
    lines.append(
        "Rows: %s. INT1-integrated (PR 9120 unmerged at capture): %s."
        % (summary["rows"], summary["int1_integrated"])
    )
    lines.append("")
    lines.append(_summary_paragraph(ledger))
    lines.append("")
    lines.append("## Ladder and rules")
    lines.append("")
    lines.append(
        "A delegated lane passes through these rungs in order. None implies the next:"
    )
    lines.append("")
    for i, rung in enumerate(ledger["ladder"], 1):
        lines.append("%s. %s" % (i, rung))
    lines.append("")
    lines.append("Rules, applied in this order:")
    lines.append("")
    for i, rule in enumerate(ledger["rung_rules"], 1):
        when = rule.get("when", "")
        effect = rule.get("rung_reached") or rule.get("floor") or rule.get("annotation")
        if rule.get("forbids"):
            effect = "forbids " + ", ".join(rule["forbids"])
        extra = []
        if rule.get("highest_ladder_rung"):
            extra.append("highest ladder rung: " + rule["highest_ladder_rung"])
        if rule.get("note"):
            extra.append(rule["note"])
        body = "%s -> %s" % (when, effect)
        if extra:
            body = body + ". " + " ".join(extra)
        lines.append("%s. `%s`: %s" % (i, rule["id"], body))
    lines.append("")
    lines.append("## Table")
    lines.append("")
    lines.append(
        "| run_id | host | rung | lane | lane_claim | tokens | INT1 |"
    )
    lines.append("| --- | --- | --- | --- | --- | ---: | --- |")
    for row in ledger["rows"]:
        int1 = row.get("int1_commit") or ""
        lines.append(
            "| %s | %s | %s | %s | %s | %s | %s |"
            % (
                row["run_id"],
                _cell(row.get("host")),
                _cell(row.get("rung_reached")),
                _cell(row.get("lane")),
                _cell(row.get("lane_claim")),
                _cell(row.get("usage_total_tokens")),
                int1,
            )
        )
    lines.append("")
    lines.append("## Never-started runs")
    lines.append("")
    lines.append(
        "rc 75 or 76: the launcher refused or failed before the remote CLI started."
    )
    lines.append("")
    lines.append("| run_id | host | rc | reserved_at |")
    lines.append("| --- | --- | ---: | --- |")
    never = [r for r in ledger["rows"] if r.get("rung_reached") == "NOT_STARTED"]
    for row in never:
        lines.append(
            "| %s | %s | %s | %s |"
            % (
                row["run_id"],
                _cell(row.get("host")),
                _cell(row.get("rc")),
                _cell(row.get("reserved_at")),
            )
        )
    lines.append("")
    lines.append("## Runs without a result")
    lines.append("")
    lines.append(
        "These rows have no parseable final line, so they are not DELIVERED."
    )
    lines.append("")
    lines.append("| run_id | host | rung | rc |")
    lines.append("| --- | --- | --- | ---: |")
    no_result = [
        r
        for r in ledger["rows"]
        if r.get("rung_reached")
        in (
            "RUNNING_OR_UNKNOWN_AT_CAPTURE",
            "EXITED_NO_RESULT",
            "EXITED_NONZERO",
        )
    ]
    for row in no_result:
        lines.append(
            "| %s | %s | %s | %s |"
            % (
                row["run_id"],
                _cell(row.get("host")),
                _cell(row.get("rung_reached")),
                _cell(row.get("rc")),
            )
        )
    lines.append("")
    lines.append("## Integration gaps")
    lines.append("")
    lines.append(
        "INT1 cherry-picks for which the seat holds no local launcher receipt. "
        "No run row is fabricated for them."
    )
    lines.append("")
    for gap in ledger["integration_gaps"]:
        lines.append(
            "- `%s` — %s. %s"
            % (gap["short_sha"], gap["subject"], gap.get("note", ""))
        )
    lines.append("")
    lines.append("## Bounds")
    lines.append("")
    for item in ledger["bounds"]:
        lines.append("- %s" % item)
    lines.append("")
    return "\n".join(lines)


def test_a39_01_schema_and_row_count():
    ledger = load_ledger()
    assert ledger["schema_version"] == "1"
    assert ledger["captured_at"] == "2026-10-13T09:33Z"
    assert ledger["ladder"] == LADDER
    assert len(ledger["rows"]) == 61
    assert ledger["summary"]["rows"] == 61
    for row in ledger["rows"]:
        for col in TSV_COLUMNS:
            assert col in row, "missing column %s on %s" % (col, row.get("run_id"))
        assert "rung_reached" in row
        assert "rung_evidence" in row
        assert isinstance(row["rung_evidence"], list)
    for flag in AUTHORITY_FLAGS:
        assert flag in ledger


def test_a39_02_rungs_follow_rules():
    ledger = load_ledger()
    errors = rung_mismatches(ledger)
    assert errors == []


def test_a39_03_no_overclaim():
    ledger = load_ledger()
    errors = overclaim_errors(ledger)
    assert errors == []
    for row in ledger["rows"]:
        assert row.get("rung_reached") not in FORBIDDEN_RUNGS
        assert row.get("accepted") is not True
        assert row.get("merged") is not True
        if row.get("rc") in (75, 76):
            assert row["rung_reached"] == "NOT_STARTED"
        if row.get("rung_reached") in (
            "RUNNING_OR_UNKNOWN_AT_CAPTURE",
            "EXITED_NO_RESULT",
        ):
            assert row["rung_reached"] != "DELIVERED"


def test_a39_04_monotone_timestamps():
    ledger = load_ledger()
    errors = timestamp_errors(ledger)
    assert errors == []


def test_a39_05_integration_gaps_named():
    ledger = load_ledger()
    gaps = ledger["integration_gaps"]
    by_sha = {gap["short_sha"]: gap for gap in gaps}
    for sha, subject in GAP_SUBJECTS.items():
        assert sha in by_sha, "missing gap %s" % sha
        assert by_sha[sha]["subject"] == subject
    claimed = []
    for row in ledger["rows"]:
        blob = "%s %s" % (row.get("int1_commit") or "", row.get("lane_head") or "")
        for sha in GAP_SHAS:
            if sha in blob:
                claimed.append((row["run_id"], sha))
    assert claimed == []


def test_a39_06_md_matches_json():
    ledger = load_ledger()
    rendered = render_ledger_md(ledger)
    on_disk = MD_PATH.read_text()
    assert on_disk == rendered


def test_a39_07_privacy():
    json_text = JSON_PATH.read_text()
    md_text = MD_PATH.read_text()
    errors = privacy_errors(json_text) + privacy_errors(md_text)
    assert errors == []


def test_a39_08_authority_false():
    ledger = load_ledger()
    for flag in AUTHORITY_FLAGS:
        assert ledger[flag] is False
        with pytest.raises(AuthorityRefused):
            set_authority(ledger, flag, True)
        assert ledger[flag] is False
        set_authority(ledger, flag, False)
        assert ledger[flag] is False


def test_a39_09_positive_controls():
    ledger = load_ledger()

    flipped = deepcopy(ledger)
    rc75 = next(row for row in flipped["rows"] if row.get("rc") == 75)
    rc75["rung_reached"] = "DELIVERED"
    assert rung_mismatches(flipped), "rc-75 DELIVERED must fail rule recompute"
    assert overclaim_errors(flipped), "rc-75 DELIVERED must fail overclaim"

    merged = deepcopy(ledger)
    merged["rows"][0]["rung_reached"] = "MERGED"
    assert overclaim_errors(merged), "MERGED must fail overclaim"

    skewed = deepcopy(ledger)
    timed = next(
        row
        for row in skewed["rows"]
        if row.get("launched_at") and row.get("done_at")
    )
    timed["done_at"] = "2020-01-01T00:00Z"
    timed["launched_at"] = "2026-10-12T04:34Z"
    assert timestamp_errors(skewed), "done_at before launched_at must fail"

    leaked = deepcopy(ledger)
    leaked["source"] = leaked["source"] + " /Users/x"
    assert privacy_errors(json.dumps(leaked)), "/Users/x in source must fail"


if __name__ == "__main__":
    import sys

    sys.stdout.write(render_ledger_md(load_ledger()))
