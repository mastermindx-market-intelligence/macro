"""Tests for the FIF Q0 counts-only label-conformance gate (pre-seal).

Every label set here is synthetic (``tmp_path``); the real Q0 protocol JSON is
read read-only. The gate is never run against a real held-out label directory
in this suite. Expected sets and minimums are derived from the protocol, not
from literal pack/ticker lists.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
TOOL_PATH = REPO_ROOT / "scripts" / "fif_q0_label_conformance.py"
PROTOCOL_PATH = (
    REPO_ROOT
    / "research"
    / "financial_intelligence_fabric"
    / "FIF_Q0_QUALITY_PROTOCOL.json"
)
PROTOCOL = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
PACKS = {pack["pack_id"]: pack for pack in PROTOCOL["packs"]}
HELD_OUT_ROWS = [row for row in PROTOCOL["minimum_n"] if row["split"] == "held_out"]
# The held-out per-issuer positive minimum ("pack, applicable issuer,
# polarity=positive"); today's frozen value is 2.
POSITIVE_MIN = next(
    row["minimum_n"]
    for row in HELD_OUT_ROWS
    if row["cell"] == "pack, applicable issuer, polarity=positive"
)

# The held-out format-generalization row ("pack, format_class != <primary>"):
# the primary format and the minimum both come from the protocol.
FORMAT_ROW = next(
    row for row in HELD_OUT_ROWS if row["cell"].startswith("pack, format_class != ")
)
PRIMARY_FORMAT = FORMAT_ROW["cell"].rsplit(" ", 1)[1]
FORMAT_MIN = FORMAT_ROW["minimum_n"]
# A synthetic non-primary format; the gate counts it but must never echo it.
NONPRIMARY_FORMAT = "zz-nonprimary-format"

POSITIVE_CLASS = "extract_positive"
NEGATIVE_CLASS = "extract_absent"
SENTINEL = "ZZ-SENTINEL-VALUE-ZZ"


def make_record(
    pack_id,
    issuer,
    label_class,
    section_family,
    form_type="10-K",
    polarity=None,
    format_class=PRIMARY_FORMAT,
):
    """A synthetic label record carrying every LabelRecord key."""
    if polarity is None:
        polarity = (
            "positive"
            if label_class in ("extract_positive", "finding_triggered_expected")
            else "negative"
        )
    return {
        "trial_id": "zz-synthetic-trial",
        "pack_id": pack_id,
        "issuer": issuer,
        "form_type": form_type,
        "fiscal_year": "FY2025",
        "section_family": section_family,
        "polarity": polarity,
        "format_class": format_class,
        "split": "held_out",
        "accession": "0000000000-00-000000",
        "label_class": label_class,
        "target_kind": "extract",
        "target_id": "zz-synthetic-target",
        "expected_value_text": None,
        "expected_unit": None,
        "expected_period_end": None,
        "expected_span_ref": None,
        "reason": "",
    }


def write_labels(root, pack_id, records, sealed=True):
    labels_dir = root / "packs" / pack_id / "labels"
    labels_dir.mkdir(parents=True)
    (labels_dir / "labels.json").write_text(json.dumps(records), encoding="utf-8")
    if sealed:
        (labels_dir / "_SEALED").write_text("", encoding="utf-8")
    return labels_dir


def run_tool(root, *extra):
    return subprocess.run(
        [sys.executable, str(TOOL_PATH), "--held-out-root", str(root), *extra],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )


def report_of(result):
    return json.loads(result.stdout)


def with_nonprimary_formats(records):
    """Give the first FORMAT_MIN records a non-primary format_class."""
    for record in records[:FORMAT_MIN]:
        record["format_class"] = NONPRIMARY_FORMAT
    return records


def required_issuers(pack_id):
    return [
        issuer
        for issuer in PROTOCOL["issuers"]
        if PACKS[pack_id]["applicability"][issuer] == "required"
    ]


def negative_issuers(pack_id):
    return [
        issuer
        for issuer in PROTOCOL["issuers"]
        if PACKS[pack_id]["applicability"][issuer] == "negative"
    ]


def pk11_conforming_records():
    """PK11 set meeting every held-out minimum (BAC: 2 positives, rest 1 neg)."""
    pack = PACKS["PK11"]
    family = pack["section_family_ids"][0]
    form = pack["forms"][0]
    records = [
        make_record("PK11", issuer, POSITIVE_CLASS, family, form_type=form)
        for issuer in required_issuers("PK11")
        for _ in range(POSITIVE_MIN)
    ]
    records += [
        make_record("PK11", issuer, NEGATIVE_CLASS, family, form_type=form)
        for issuer in negative_issuers("PK11")
    ]
    return with_nonprimary_formats(records)


def pk12_all_negative_records():
    """One negative label on every PK12 issuer (all negative-applicability)."""
    pack = PACKS["PK12"]
    family = pack["section_family_ids"][0]
    form = pack["forms"][0]
    return with_nonprimary_formats(
        [
            make_record("PK12", issuer, NEGATIVE_CLASS, family, form_type=form)
            for issuer in negative_issuers("PK12")
        ]
    )


# (1) a conforming PK11 set exits 0 with conforming true.
def test_conforming_pk11_set(tmp_path):
    write_labels(tmp_path, "PK11", pk11_conforming_records())
    result = run_tool(tmp_path, "--packs", "PK11")
    assert result.returncode == 0, result.stderr
    report = report_of(result)
    assert report["schema"] == "fif_q0_label_conformance.v1"
    assert report["protocol_id"] == PROTOCOL["protocol_id"]
    assert report["conforming"] is True
    assert report["totals"] == {"violations": 0, "shortfalls": 0}
    pack = report["packs"]["PK11"]
    assert pack["labels_present"] is True
    assert pack["sealed"] is True
    assert pack["violations"] == {}
    assert pack["shortfalls"] == []
    assert pack["n_labels"] == POSITIVE_MIN * len(required_issuers("PK11")) + len(
        negative_issuers("PK11")
    )
    assert pack["by_issuer"][required_issuers("PK11")[0]]["positive"] == POSITIVE_MIN
    assert pack["format_nonprimary"] == FORMAT_MIN
    assert pack["by_issuer"][negative_issuers("PK11")[0]] == {
        "applicability": "negative",
        "positive": 0,
        "negative": 1,
        "other": 0,
        "polarity": {"negative": 1},
    }


# (2) a PK12 positive on any five-issuer ticker raises the violation.
@pytest.mark.parametrize("issuer", PROTOCOL["issuers"])
def test_pk12_positive_on_negative_issuer(issuer, tmp_path):
    pack = PACKS["PK12"]
    assert pack["applicability"][issuer] == "negative"
    record = make_record(
        "PK12",
        issuer,
        POSITIVE_CLASS,
        pack["section_family_ids"][0],
        form_type=pack["forms"][0],
    )
    write_labels(tmp_path, "PK12", [record])
    result = run_tool(tmp_path, "--packs", "PK12")
    assert result.returncode == 1
    report = report_of(result)
    assert report["conforming"] is False
    assert report["packs"]["PK12"]["violations"] == {"positive_on_negative_issuer": 1}


# (3) PK12 negatives on only two issuers shortfall exactly the other three.
def test_pk12_negative_issuer_shortfall(tmp_path):
    pack = PACKS["PK12"]
    family = pack["section_family_ids"][0]
    form = pack["forms"][0]
    labeled = negative_issuers("PK12")[:2]
    write_labels(
        tmp_path,
        "PK12",
        with_nonprimary_formats(
            [
                make_record("PK12", issuer, NEGATIVE_CLASS, family, form_type=form)
                for issuer in labeled
            ]
        ),
    )
    row = next(row for row in HELD_OUT_ROWS if row["cell"].startswith("PK12 x "))
    expected = set(negative_issuers("PK12")) - set(labeled)
    result = run_tool(tmp_path, "--packs", "PK12")
    assert result.returncode == 1
    shortfalls = report_of(result)["packs"]["PK12"]["shortfalls"]
    assert len(shortfalls) == len(expected)
    for shortfall in shortfalls:
        assert shortfall["code"] == "negative_issuer_short"
        assert shortfall["have"] == 0
        assert shortfall["need"] == row["minimum_n"]
    assert {shortfall["scope"] for shortfall in shortfalls} == expected


# (4) a required issuer with a single positive yields positive_cell_short.
def test_required_issuer_positive_cell_shortfall(tmp_path):
    pack = PACKS["PK11"]
    issuer = required_issuers("PK11")[0]
    record = make_record(
        "PK11", issuer, POSITIVE_CLASS, pack["section_family_ids"][0], form_type=pack["forms"][0]
    )
    write_labels(tmp_path, "PK11", [record])
    result = run_tool(tmp_path, "--packs", "PK11")
    assert result.returncode == 1
    shorts = [
        shortfall
        for shortfall in report_of(result)["packs"]["PK11"]["shortfalls"]
        if shortfall["code"] == "positive_cell_short"
    ]
    assert POSITIVE_MIN == 2  # today's frozen protocol value
    assert shorts == [
        {"code": "positive_cell_short", "scope": issuer, "have": 1, "need": POSITIVE_MIN}
    ]


# (5) record-level violations are counted; the raw outside issuer never leaks.
def test_record_level_violations_and_outside_issuer_hidden(tmp_path):
    pack = PACKS["PK11"]
    family = pack["section_family_ids"][0]
    form = pack["forms"][0]
    outside_issuer = "ZZZZ"
    bogus_class = "zz_bogus_label_class"
    records = [
        make_record("PK12", required_issuers("PK11")[0], NEGATIVE_CLASS, family, form_type=form),
        make_record("PK11", required_issuers("PK11")[0], bogus_class, family, form_type=form),
        make_record("PK11", outside_issuer, NEGATIVE_CLASS, family, form_type=form),
    ]
    write_labels(tmp_path, "PK11", records)
    result = run_tool(tmp_path, "--packs", "PK11")
    assert result.returncode == 1
    report = report_of(result)
    violations = report["packs"]["PK11"]["violations"]
    assert violations["pack_mismatch"] == 1
    assert violations["label_class_outside_vocabulary"] == 1
    assert violations["issuer_outside_protocol"] == 1
    assert "<outside_protocol>" in report["packs"]["PK11"]["by_issuer"]
    assert outside_issuer not in result.stdout
    assert bogus_class not in result.stdout


# (6) --require-sealed refuses an unsealed dir (exit 2); default reads it.
def test_require_sealed_gate(tmp_path):
    write_labels(tmp_path, "PK11", pk11_conforming_records(), sealed=False)
    refused = run_tool(tmp_path, "--packs", "PK11", "--require-sealed")
    assert refused.returncode == 2
    assert "_SEALED" in refused.stderr
    read = run_tool(tmp_path, "--packs", "PK11")
    assert read.returncode == 0
    pack = report_of(read)["packs"]["PK11"]
    assert pack["sealed"] is False
    assert pack["n_labels"] > 0


# (7) record payload fields never reach stdout or the --out file.
def test_no_record_payload_leak(tmp_path):
    records = pk11_conforming_records()
    leaky_fields = (
        "trial_id",
        "accession",
        "target_id",
        "expected_value_text",
        "expected_span_ref",
        "reason",
    )
    for record in records:
        for field in leaky_fields:
            record[field] = SENTINEL
    write_labels(tmp_path, "PK11", records)
    out_path = tmp_path / "report.json"
    via_file = run_tool(tmp_path, "--packs", "PK11", "--out", str(out_path))
    assert via_file.returncode == 0
    written = out_path.read_text(encoding="utf-8")
    via_stdout = run_tool(tmp_path, "--packs", "PK11")
    assert via_stdout.returncode == 0
    for text in (via_file.stdout, written, via_stdout.stdout):
        assert SENTINEL not in text
        assert NONPRIMARY_FORMAT not in text


# (8) --min-positive-per-family yields family_positive_short per family.
def test_min_positive_per_family(tmp_path):
    write_labels(tmp_path, "PK11", pk11_conforming_records())
    result = run_tool(tmp_path, "--packs", "PK11", "--min-positive-per-family", "2")
    assert result.returncode == 1
    report = report_of(result)
    assert report["min_positive_per_family"] == 2
    shorts = [
        shortfall
        for shortfall in report["packs"]["PK11"]["shortfalls"]
        if shortfall["code"] == "family_positive_short"
    ]
    families = PACKS["PK11"]["section_family_ids"]
    covered = families[0]  # the conforming records all use the first family
    assert {shortfall["scope"] for shortfall in shorts} == set(families) - {covered}
    assert all(
        shortfall["have"] == 0 and shortfall["need"] == 2 for shortfall in shorts
    )


# (9) the tool has no default held-out root.
def test_missing_held_out_root_argument_is_usage_error():
    result = subprocess.run(
        [sys.executable, str(TOOL_PATH)],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    assert result.returncode == 2


# (10) a pack without a labels dir is labels_present: false, not an error.
def test_pack_without_labels_dir(tmp_path):
    result = run_tool(tmp_path, "--packs", "PK11")
    assert result.returncode == 0
    report = report_of(result)
    pack = report["packs"]["PK11"]
    assert pack["labels_present"] is False
    assert pack["n_labels"] == 0
    assert pack["violations"] == {}
    assert pack["shortfalls"] == []
    assert report["conforming"] is True


# (11) an out-of-pack section_family is sentinel-tallied, never raw.
def test_section_family_outside_pack(tmp_path):
    records = pk12_all_negative_records()
    outside_family = "zz_outside_family"
    records[0]["section_family"] = outside_family
    write_labels(tmp_path, "PK12", records)
    result = run_tool(tmp_path, "--packs", "PK12")
    assert result.returncode == 1
    pack = report_of(result)["packs"]["PK12"]
    assert pack["violations"] == {"section_family_outside_pack": 1}
    assert set(pack["by_family"]) == set(PACKS["PK12"]["section_family_ids"]) | {
        "<outside_pack>"
    }
    assert pack["by_family"]["<outside_pack>"]["negative"] == 1
    assert outside_family not in result.stdout


# (12) a PK12 negative on a 10-Q raises form_outside_pack (PK12 is 10-K only).
def test_form_outside_pack(tmp_path):
    assert PACKS["PK12"]["forms"] == ["10-K"]
    records = pk12_all_negative_records()
    records[0]["form_type"] = "10-Q"
    write_labels(tmp_path, "PK12", records)
    result = run_tool(tmp_path, "--packs", "PK12")
    assert result.returncode == 1
    pack = report_of(result)["packs"]["PK12"]
    assert pack["violations"] == {"form_outside_pack": 1}
    assert pack["by_form"] == {PACKS["PK12"]["forms"][0]: len(records) - 1, "<outside_pack>": 1}


# (13) an out-of-vocabulary polarity is counted under a sentinel, never echoed.
def test_polarity_outside_vocabulary_is_sentinel_tallied(tmp_path):
    leak = "ZZLEAK-POLARITY"
    records = pk11_conforming_records()
    records[0]["polarity"] = leak
    write_labels(tmp_path, "PK11", records)
    out_path = tmp_path / "report.json"
    result = run_tool(tmp_path, "--packs", "PK11", "--out", str(out_path))
    assert result.returncode == 1
    written = out_path.read_text(encoding="utf-8")
    assert leak not in result.stdout
    assert leak not in written
    pack = json.loads(written)["packs"]["PK11"]
    assert pack["violations"] == {"polarity_outside_vocabulary": 1}
    issuer = records[0]["issuer"]
    assert pack["by_issuer"][issuer]["polarity"]["<outside_vocabulary>"] == 1


# (14) a pack whose labels are all in the primary format is format-short.
def test_format_cell_shortfall(tmp_path):
    records = pk12_all_negative_records()
    for record in records:
        record["format_class"] = PRIMARY_FORMAT
    write_labels(tmp_path, "PK12", records)
    result = run_tool(tmp_path, "--packs", "PK12")
    assert result.returncode == 1
    pack = report_of(result)["packs"]["PK12"]
    assert pack["violations"] == {}
    assert pack["format_nonprimary"] == 0
    assert pack["shortfalls"] == [
        {"code": "format_cell_short", "scope": "pack", "have": 0, "need": FORMAT_MIN}
    ]


def group_row_pack():
    """The pack of the first "<PACK> x <group>" row that is not an "all" row."""
    for row in HELD_OUT_ROWS:
        head, sep, group = row["cell"].partition(" x ")
        if sep and head in PACKS and not group.startswith("all "):
            return head, row["minimum_n"]
    raise AssertionError("protocol has no aggregate per-pack negative row")


# (15) a non-"all" group row is ONE aggregate over the non-required issuers.
def test_group_row_is_an_aggregate_over_non_required_issuers(tmp_path):
    pack_id, need = group_row_pack()
    pack = PACKS[pack_id]
    family = pack["section_family_ids"][0]
    form = pack["forms"][0]
    group = [
        issuer
        for issuer in PROTOCOL["issuers"]
        if pack["applicability"][issuer] != "required"
    ]
    assert len(group) > 1
    positives = [
        make_record(pack_id, issuer, POSITIVE_CLASS, family, form_type=form)
        for issuer in required_issuers(pack_id)
        for _ in range(POSITIVE_MIN)
    ]
    # `need` negatives, all on ONE issuer of the group, satisfy the row.
    one_issuer = [
        make_record(pack_id, group[0], NEGATIVE_CLASS, family, form_type=form)
        for _ in range(need)
    ]
    write_labels(tmp_path / "a", pack_id, with_nonprimary_formats(positives + one_issuer))
    met = run_tool(tmp_path / "a", "--packs", pack_id)
    assert met.returncode == 0, met.stdout
    assert report_of(met)["packs"][pack_id]["shortfalls"] == []
    # With no negatives on the group, the row is short once, at pack scope.
    write_labels(tmp_path / "b", pack_id, with_nonprimary_formats(list(positives)))
    short = run_tool(tmp_path / "b", "--packs", pack_id)
    assert short.returncode == 1
    group_shorts = [
        shortfall
        for shortfall in report_of(short)["packs"][pack_id]["shortfalls"]
        if shortfall["code"] in ("negative_group_short", "negative_issuer_short")
    ]
    assert group_shorts == [
        {"code": "negative_group_short", "scope": "pack", "have": 0, "need": need}
    ]


def optional_issuer_pack():
    for pack_id, pack in PACKS.items():
        for issuer in PROTOCOL["issuers"]:
            if pack["applicability"].get(issuer) == "optional":
                return pack_id, issuer
    raise AssertionError("protocol has no optional issuer")


# (16) an optional issuer is held to the positive cell once it carries labels.
def test_labeled_optional_issuer_gets_the_positive_cell(tmp_path):
    pack_id, issuer = optional_issuer_pack()
    pack = PACKS[pack_id]
    family = pack["section_family_ids"][0]
    form = pack["forms"][0]
    write_labels(
        tmp_path / "a",
        pack_id,
        [make_record(pack_id, issuer, POSITIVE_CLASS, family, form_type=form)],
    )
    labeled = run_tool(tmp_path / "a", "--packs", pack_id)
    shorts = [
        shortfall
        for shortfall in report_of(labeled)["packs"][pack_id]["shortfalls"]
        if shortfall["code"] == "positive_cell_short" and shortfall["scope"] == issuer
    ]
    assert shorts == [
        {"code": "positive_cell_short", "scope": issuer, "have": 1, "need": POSITIVE_MIN}
    ]
    # An optional issuer with no labels is not an applicable issuer.
    write_labels(tmp_path / "b", pack_id, pk12_like_negative(pack_id, issuer))
    unlabeled = run_tool(tmp_path / "b", "--packs", pack_id)
    assert not [
        shortfall
        for shortfall in report_of(unlabeled)["packs"][pack_id]["shortfalls"]
        if shortfall["code"] == "positive_cell_short" and shortfall["scope"] == issuer
    ]


def pk12_like_negative(pack_id, skip_issuer):
    pack = PACKS[pack_id]
    other = next(i for i in PROTOCOL["issuers"] if i != skip_issuer)
    return [
        make_record(
            pack_id,
            other,
            NEGATIVE_CLASS,
            pack["section_family_ids"][0],
            form_type=pack["forms"][0],
        )
    ]


# (17) empty or absent forms / section_family_ids place no restriction.
@pytest.mark.parametrize("mode", ["empty", "absent"])
def test_unrestricted_forms_and_families(mode, tmp_path):
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    for pack in protocol["packs"]:
        if pack["pack_id"] == "PK12":
            if mode == "empty":
                pack["forms"] = []
                pack["section_family_ids"] = []
            else:
                pack.pop("forms", None)
                pack.pop("section_family_ids", None)
    protocol_path = tmp_path / "protocol.json"
    protocol_path.write_text(json.dumps(protocol), encoding="utf-8")
    records = pk12_all_negative_records()
    records[0]["form_type"] = "zz-any-form"
    records[0]["section_family"] = "zz-any-family"
    root = tmp_path / "root"
    write_labels(root, "PK12", records)
    result = run_tool(root, "--packs", "PK12", "--protocol", str(protocol_path))
    assert result.returncode == 0, result.stdout
    pack = report_of(result)["packs"]["PK12"]
    assert pack["violations"] == {}
    assert pack["by_form"] == {"<unrestricted>": len(records)}
    assert pack["by_family"]["<unrestricted>"]["negative"] == len(records)
    assert "zz-any-form" not in result.stdout
    assert "zz-any-family" not in result.stdout


# (18) floors count by polarity, as the evaluator does: a record whose
# label_class disagrees with its polarity cannot fill a cell.
def test_positive_cell_counts_by_polarity(tmp_path):
    records = pk11_conforming_records()
    issuer = required_issuers("PK11")[0]
    for record in records:
        if record["issuer"] == issuer and record["label_class"] == POSITIVE_CLASS:
            record["polarity"] = "negative"
    write_labels(tmp_path, "PK11", records)
    result = run_tool(tmp_path, "--packs", "PK11")
    assert result.returncode == 1
    pack = report_of(result)["packs"]["PK11"]
    assert pack["by_issuer"][issuer]["positive"] == POSITIVE_MIN
    assert {
        "code": "positive_cell_short",
        "scope": issuer,
        "have": 0,
        "need": POSITIVE_MIN,
    } in pack["shortfalls"]


def test_negative_issuer_row_counts_by_polarity(tmp_path):
    records = pk12_all_negative_records()
    records[0]["polarity"] = "positive"
    write_labels(tmp_path, "PK12", records)
    result = run_tool(tmp_path, "--packs", "PK12")
    assert result.returncode == 1
    pack = report_of(result)["packs"]["PK12"]
    assert pack["by_issuer"][records[0]["issuer"]]["negative"] == 1
    assert {
        "code": "negative_issuer_short",
        "scope": records[0]["issuer"],
        "have": 0,
        "need": 1,
    } in pack["shortfalls"]

