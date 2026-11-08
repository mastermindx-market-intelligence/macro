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


# ---------------------------------------------------------------------------
# --contract: pack-scoped split cohorts (every contract below is synthetic)
# ---------------------------------------------------------------------------

SYNB1 = "SYNB1"
SYNB2 = "SYNB2"
SYNC1 = "SYNC1"
SPLIT_ID = 3
CONTRACT_SENTINEL = "ZZ-CONTRACT-SENTINEL"


def syn_accession(n):
    """A synthetic accession string; never a real filing id."""
    return f"0000000000-00-9000{n:02d}"


def contract_path(tmp_path, payload):
    path = tmp_path / "contract.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def scoped_rows(ticker, accessions, pack="PK12", split=SPLIT_ID):
    return {
        "ticker": ticker,
        "accessions": [
            {"accession": accession, "split_decision": split, "pack_scope": [pack]}
            for accession in accessions
        ],
    }


def synb_contract(tmp_path, pack="PK12"):
    """SYNB1 with three PK12-scoped rows and SYNB2 with two, split 3."""
    return contract_path(
        tmp_path,
        {
            "split_decisions": [{"id": 1}, {"id": SPLIT_ID}],
            "issuers": [
                scoped_rows(
                    SYNB1, [syn_accession(n) for n in (1, 2, 3)], pack
                ),
                scoped_rows(SYNB2, [syn_accession(n) for n in (4, 5)], pack),
            ],
        },
    )


def synb_label(ticker, accession, label_class, pack="PK12"):
    pack_cfg = PACKS[pack]
    record = make_record(
        pack,
        ticker,
        label_class,
        pack_cfg["section_family_ids"][0],
        form_type=pack_cfg["forms"][0],
    )
    record["accession"] = accession
    return record


def synb_conforming_records():
    """The PK12 negatives the protocol already requires, plus the scoped
    cohort: 2 positives on each of SYNB1/SYNB2 and every scoped accession
    labelled (SYNB1's third row carries the cohort's negative)."""
    records = pk12_all_negative_records()
    records += [
        synb_label(SYNB1, syn_accession(1), POSITIVE_CLASS),
        synb_label(SYNB1, syn_accession(2), POSITIVE_CLASS),
        synb_label(SYNB1, syn_accession(3), NEGATIVE_CLASS),
        synb_label(SYNB2, syn_accession(4), POSITIVE_CLASS),
        synb_label(SYNB2, syn_accession(5), POSITIVE_CLASS),
    ]
    return records


# (19) without --contract the two new top-level keys are present and inert.
def test_no_contract_reports_contract_not_supplied(tmp_path):
    write_labels(tmp_path, "PK11", pk11_conforming_records())
    result = run_tool(tmp_path, "--packs", "PK11")
    assert result.returncode == 0, result.stderr
    report = report_of(result)
    assert report["contract_supplied"] is False
    assert report["split_cohorts"] == {}


# (20) a conforming scoped-cohort PK12 label set exits 0 and reports cohort 3.
def test_contract_admits_scoped_cohort_conforming(tmp_path):
    write_labels(tmp_path, "PK12", synb_conforming_records())
    result = run_tool(
        tmp_path, "--packs", "PK12", "--contract", str(synb_contract(tmp_path))
    )
    assert result.returncode == 0, result.stderr
    report = report_of(result)
    assert report["contract_supplied"] is True
    assert report["split_cohorts"][str(SPLIT_ID)] == {
        "packs": ["PK12"],
        "issuers": 2,
        "accessions": 5,
        "labelled_accessions": {"PK12": 5},
        "labels": {"PK12": {"positive": 4, "negative": 1, "other": 0}},
    }
    synb1 = report["packs"]["PK12"]["by_issuer"][SYNB1]
    assert synb1["applicability"] == "required"
    assert synb1["split_decision"] == SPLIT_ID
    assert synb1["positive"] == POSITIVE_MIN
    assert report["packs"]["PK12"]["violations"] == {}
    assert report["packs"]["PK12"]["shortfalls"] == []
    assert report["conforming"] is True


# (21) a scoped issuer with only one positive is positive-cell short.
def test_scoped_issuer_positive_cell_short(tmp_path):
    records = [r for r in synb_conforming_records() if r["issuer"] != SYNB1]
    records += [
        synb_label(SYNB1, syn_accession(1), POSITIVE_CLASS),
        synb_label(SYNB1, syn_accession(2), NEGATIVE_CLASS),
        synb_label(SYNB1, syn_accession(3), NEGATIVE_CLASS),
    ]
    write_labels(tmp_path, "PK12", records)
    result = run_tool(
        tmp_path, "--packs", "PK12", "--contract", str(synb_contract(tmp_path))
    )
    assert result.returncode == 1
    pack = report_of(result)["packs"]["PK12"]
    assert {
        "code": "positive_cell_short",
        "scope": SYNB1,
        "have": 1,
        "need": POSITIVE_MIN,
    } in pack["shortfalls"]


# (22) a scoped-cohort label outside the cohort's pack stays outside-protocol.
def test_scoped_issuer_label_outside_pack_scope(tmp_path):
    contract = synb_contract(tmp_path)
    record = synb_label(SYNB1, syn_accession(1), NEGATIVE_CLASS, pack="PK01")
    write_labels(tmp_path, "PK01", [record])
    result = run_tool(tmp_path, "--packs", "PK01", "--contract", str(contract))
    assert result.returncode == 1
    pack = report_of(result)["packs"]["PK01"]
    assert pack["violations"] == {
        "issuer_outside_protocol": 1,
        "accession_outside_split_scope": 1,
    }
    assert "<outside_protocol>" in pack["by_issuer"]
    assert SYNB1 not in pack["by_issuer"]


# (23) a scoped-pack label whose accession is not one of the contract's.
def test_accession_outside_contract(tmp_path):
    records = synb_conforming_records()
    positives = [
        r for r in records if r["issuer"] == SYNB1 and r["label_class"] == POSITIVE_CLASS
    ]
    positives[0]["accession"] = "ZZ-BOGUS-ACCESSION"
    write_labels(tmp_path, "PK12", records)
    result = run_tool(
        tmp_path, "--packs", "PK12", "--contract", str(synb_contract(tmp_path))
    )
    assert result.returncode == 1
    pack = report_of(result)["packs"]["PK12"]
    assert pack["violations"] == {"accession_outside_contract": 1}
    assert "ZZ-BOGUS-ACCESSION" not in result.stdout


# (24) one of SYNB1's three scoped accessions left unlabelled.
def test_split_accession_unlabelled(tmp_path):
    records = [
        r for r in synb_conforming_records() if r["accession"] != syn_accession(3)
    ]
    write_labels(tmp_path, "PK12", records)
    result = run_tool(
        tmp_path, "--packs", "PK12", "--contract", str(synb_contract(tmp_path))
    )
    assert result.returncode == 1
    pack = report_of(result)["packs"]["PK12"]
    assert pack["violations"] == {}
    assert pack["shortfalls"] == [
        {"code": "split_accession_unlabelled", "scope": SYNB1, "have": 2, "need": 3}
    ]


# (25) contract and label accession values never reach stdout or --out.
def test_contract_accessions_never_leak(tmp_path):
    accessions = [f"{CONTRACT_SENTINEL}-ACC-{n}" for n in range(5)]
    contract = contract_path(
        tmp_path,
        {
            "split_decisions": [{"id": 1}, {"id": SPLIT_ID}],
            "issuers": [
                scoped_rows(SYNB1, accessions[:3]),
                scoped_rows(SYNB2, accessions[3:]),
            ],
        },
    )
    records = pk12_all_negative_records()
    for record in records:
        record["accession"] = f"{CONTRACT_SENTINEL}-LABEL"
    records += [
        synb_label(SYNB1, accessions[0], POSITIVE_CLASS),
        synb_label(SYNB1, accessions[1], POSITIVE_CLASS),
        synb_label(SYNB1, accessions[2], NEGATIVE_CLASS),
        synb_label(SYNB2, accessions[3], POSITIVE_CLASS),
        synb_label(SYNB2, accessions[4], POSITIVE_CLASS),
    ]
    write_labels(tmp_path, "PK12", records)
    out_path = tmp_path / "report.json"
    result = run_tool(
        tmp_path,
        "--packs",
        "PK12",
        "--contract",
        str(contract),
        "--out",
        str(out_path),
    )
    assert result.returncode == 0, result.stderr
    written = out_path.read_text(encoding="utf-8")
    for text in (result.stdout, written):
        for value in (*accessions, f"{CONTRACT_SENTINEL}-LABEL"):
            assert value not in text
    assert json.loads(written)["split_cohorts"][str(SPLIT_ID)][
        "labelled_accessions"
    ] == {"PK12": 5}


# (26) every malformed-contract case exits 2 without echoing contract values.
MALFORMED_CONTRACTS = {
    "unreadable_file": None,
    "invalid_json": "not-json " + CONTRACT_SENTINEL + " {{{",
    "top_level_not_object": [{"ticker": CONTRACT_SENTINEL}],
    "issuers_missing": {
        "split_decisions": [{"id": SPLIT_ID, "note": CONTRACT_SENTINEL}]
    },
    "issuers_not_list": {"issuers": {"ticker": CONTRACT_SENTINEL}},
    "ticker_not_string": {"issuers": [{"ticker": [CONTRACT_SENTINEL], "accessions": []}]},
    "accessions_missing": {"issuers": [{"ticker": CONTRACT_SENTINEL}]},
    "accessions_not_list": {"issuers": [{"ticker": "T", "accessions": CONTRACT_SENTINEL}]},
    "row_missing_accession": {
        "split_decisions": [{"id": SPLIT_ID}],
        "issuers": [
            {
                "ticker": "T",
                "accessions": [{"split_decision": SPLIT_ID, "x": CONTRACT_SENTINEL}],
            }
        ],
    },
    "row_missing_split_decision": {
        "split_decisions": [{"id": SPLIT_ID}],
        "issuers": [{"ticker": "T", "accessions": [{"accession": CONTRACT_SENTINEL}]}],
    },
    "pack_scope_not_list": {
        "split_decisions": [{"id": SPLIT_ID}],
        "issuers": [
            {
                "ticker": "T",
                "accessions": [
                    {
                        "accession": CONTRACT_SENTINEL,
                        "split_decision": SPLIT_ID,
                        "pack_scope": "PK12",
                    }
                ],
            }
        ],
    },
    "pack_scope_empty": {
        "split_decisions": [{"id": SPLIT_ID}],
        "issuers": [
            {
                "ticker": "T",
                "accessions": [
                    {
                        "accession": CONTRACT_SENTINEL,
                        "split_decision": SPLIT_ID,
                        "pack_scope": [],
                    }
                ],
            }
        ],
    },
    "pack_scope_unknown_pack": {
        "split_decisions": [{"id": SPLIT_ID}],
        "issuers": [
            {
                "ticker": "T",
                "accessions": [
                    {
                        "accession": CONTRACT_SENTINEL,
                        "split_decision": SPLIT_ID,
                        "pack_scope": ["PK12", "ZZ99"],
                    }
                ],
            }
        ],
    },
    "pack_scope_bad_split_decision": {
        "split_decisions": [{"id": 1}],
        "issuers": [
            {
                "ticker": "T",
                "accessions": [
                    {
                        "accession": CONTRACT_SENTINEL,
                        "split_decision": SPLIT_ID,
                        "pack_scope": ["PK12"],
                    }
                ],
            }
        ],
    },
}


@pytest.mark.parametrize(
    "case", sorted(MALFORMED_CONTRACTS), ids=sorted(MALFORMED_CONTRACTS)
)
def test_malformed_contract_exits_two(case, tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    payload = MALFORMED_CONTRACTS[case]
    if payload is None:
        contract = tmp_path / "no-such-contract.json"
    else:
        contract = tmp_path / "contract.json"
        contract.write_text(
            payload if isinstance(payload, str) else json.dumps(payload),
            encoding="utf-8",
        )
    result = run_tool(root, "--packs", "PK12", "--contract", str(contract))
    assert result.returncode == 2
    assert CONTRACT_SENTINEL not in result.stderr
    assert CONTRACT_SENTINEL not in result.stdout


# (27) contract rows without pack_scope admit nothing.
def test_unscoped_contract_issuer_not_admitted(tmp_path):
    contract = contract_path(
        tmp_path,
        {
            "split_decisions": [{"id": SPLIT_ID}],
            "issuers": [
                {
                    "ticker": SYNC1,
                    "accessions": [
                        {"accession": syn_accession(1), "split_decision": SPLIT_ID},
                        {"accession": syn_accession(2), "split_decision": SPLIT_ID},
                    ],
                }
            ],
        },
    )
    records = pk12_all_negative_records()
    records += [
        synb_label(SYNC1, syn_accession(1), NEGATIVE_CLASS),
        synb_label(SYNC1, syn_accession(2), NEGATIVE_CLASS),
    ]
    write_labels(tmp_path, "PK12", records)
    result = run_tool(tmp_path, "--packs", "PK12", "--contract", str(contract))
    assert result.returncode == 1
    report = report_of(result)
    pack = report["packs"]["PK12"]
    assert pack["violations"] == {"issuer_outside_protocol": 2}
    assert "<outside_protocol>" in pack["by_issuer"]
    assert SYNC1 not in pack["by_issuer"]
    assert report["split_cohorts"] == {}


# (28) the same label set with and without --contract differs only in the
# contract-dependent parts; protocol-issuer by_issuer entries are equal.
def test_contract_changes_only_contract_dependent_keys(tmp_path):
    write_labels(tmp_path, "PK12", synb_conforming_records())
    plain = report_of(run_tool(tmp_path, "--packs", "PK12"))
    with_contract = report_of(
        run_tool(
            tmp_path, "--packs", "PK12", "--contract", str(synb_contract(tmp_path))
        )
    )
    assert plain["contract_supplied"] is False
    assert with_contract["contract_supplied"] is True
    assert plain["split_cohorts"] == {}
    for key in ("schema", "protocol_id", "require_sealed", "min_positive_per_family"):
        assert plain[key] == with_contract[key]
    for pack_id, plain_pack in plain["packs"].items():
        scoped_pack = with_contract["packs"][pack_id]
        assert {
            key: value
            for key, value in plain_pack.items()
            if key not in ("by_issuer", "violations")
        } == {
            key: value
            for key, value in scoped_pack.items()
            if key not in ("by_issuer", "violations")
        }
        for issuer in PROTOCOL["issuers"]:
            assert plain_pack["by_issuer"][issuer] == scoped_pack["by_issuer"][issuer]
        assert set(plain_pack["by_issuer"]) - set(PROTOCOL["issuers"]) == {
            "<outside_protocol>"
        }
        assert set(scoped_pack["by_issuer"]) - set(PROTOCOL["issuers"]) == {SYNB1, SYNB2}
    assert plain["packs"]["PK12"]["violations"] == {"issuer_outside_protocol": 5}
    assert with_contract["packs"]["PK12"]["violations"] == {}
    assert with_contract["conforming"] is True


# (29) a non-scalar split-decision id, a non-scalar split_decision on a
# pack_scope row, and mutually incomparable split_decision values on one
# issuer's pack_scope rows each exit 2 through the error path: no traceback,
# no contract value echoed.
def two_scoped_rows(first_split, second_split):
    return {
        "ticker": "T",
        "accessions": [
            {
                "accession": CONTRACT_SENTINEL + "-1",
                "split_decision": first_split,
                "pack_scope": ["PK12"],
            },
            {
                "accession": CONTRACT_SENTINEL + "-2",
                "split_decision": second_split,
                "pack_scope": ["PK12"],
            },
        ],
    }


TYPE_MALFORMED_CONTRACTS = {
    "split_decisions_id_not_scalar": {
        "split_decisions": [{"id": SPLIT_ID}, {"id": [CONTRACT_SENTINEL]}],
        "issuers": [],
    },
    "pack_scope_split_decision_not_scalar": {
        "split_decisions": [{"id": SPLIT_ID}],
        "issuers": [
            {
                "ticker": "T",
                "accessions": [
                    {
                        "accession": CONTRACT_SENTINEL,
                        "split_decision": {"id": CONTRACT_SENTINEL},
                        "pack_scope": ["PK12"],
                    }
                ],
            }
        ],
    },
    "pack_scope_split_decisions_int_and_str": {
        "split_decisions": [{"id": SPLIT_ID}, {"id": CONTRACT_SENTINEL}],
        "issuers": [two_scoped_rows(SPLIT_ID, CONTRACT_SENTINEL)],
    },
    "pack_scope_split_decisions_null_and_int": {
        "split_decisions": [{"id": None}, {"id": SPLIT_ID}],
        "issuers": [two_scoped_rows(None, SPLIT_ID)],
    },
}


@pytest.mark.parametrize(
    "case", sorted(TYPE_MALFORMED_CONTRACTS), ids=sorted(TYPE_MALFORMED_CONTRACTS)
)
def test_contract_type_malformed_exits_two_cleanly(case, tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    contract = contract_path(tmp_path, TYPE_MALFORMED_CONTRACTS[case])
    result = run_tool(root, "--packs", "PK12", "--contract", str(contract))
    assert result.returncode == 2
    assert "Traceback" not in result.stderr
    assert "fif_q0_label_conformance: error: contract file" in result.stderr
    assert CONTRACT_SENTINEL not in result.stderr
    assert CONTRACT_SENTINEL not in result.stdout


# (30) one issuer's pack_scope rows under two comparable ids are still admitted
# under the smaller id: the comparability check rejects nothing valid.
def test_comparable_split_decisions_still_admitted(tmp_path):
    synb1 = scoped_rows(SYNB1, [syn_accession(n) for n in (1, 2, 3)])
    synb1["accessions"][1]["split_decision"] = 1
    contract = contract_path(
        tmp_path,
        {
            "split_decisions": [{"id": 1}, {"id": SPLIT_ID}],
            "issuers": [
                synb1,
                scoped_rows(SYNB2, [syn_accession(n) for n in (4, 5)]),
            ],
        },
    )
    write_labels(tmp_path, "PK12", synb_conforming_records())
    result = run_tool(tmp_path, "--packs", "PK12", "--contract", str(contract))
    assert result.returncode == 0, result.stderr
    report = report_of(result)
    assert report["packs"]["PK12"]["by_issuer"][SYNB1]["split_decision"] == 1
    assert report["packs"]["PK12"]["by_issuer"][SYNB2]["split_decision"] == SPLIT_ID


# (31) bytes that json.load cannot turn into a value (bad UTF-8, an integer
# past the interpreter's digit limit, runaway nesting) exit 2 through the
# error path for every input file, never rc 1: rc 1 means non-conforming.
UNPARSEABLE_BYTES = {
    "invalid_utf8": b'{"issuers": ["' + CONTRACT_SENTINEL.encode() + b'\xff\xfe"]}',
    "nesting_200000": b'{"issuers": ' + b"[" * 200000 + b"]" * 200000 + b"}",
}
if hasattr(sys, "get_int_max_str_digits"):
    UNPARSEABLE_BYTES["integer_5000_digits"] = (
        b'{"split_decisions": [{"id": ' + b"9" * 5000 + b'}], "issuers": []}'
    )


@pytest.mark.parametrize("kind", ["contract", "label", "protocol"])
@pytest.mark.parametrize(
    "shape", sorted(UNPARSEABLE_BYTES), ids=sorted(UNPARSEABLE_BYTES)
)
def test_unparseable_input_file_exits_two_cleanly(kind, shape, tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    bad = tmp_path / "bad.json"
    bad.write_bytes(UNPARSEABLE_BYTES[shape])
    extra = ["--packs", "PK12"]
    if kind == "contract":
        extra += ["--contract", str(bad)]
    elif kind == "protocol":
        extra += ["--protocol", str(bad)]
    else:
        labels_dir = write_labels(root, "PK12", [])
        (labels_dir / "labels.json").write_bytes(UNPARSEABLE_BYTES[shape])
    result = run_tool(root, *extra)
    assert result.returncode == 2
    assert "Traceback" not in result.stderr
    assert f"{kind} file" in result.stderr
    assert "is not valid JSON" in result.stderr
    assert CONTRACT_SENTINEL not in result.stderr
    assert CONTRACT_SENTINEL not in result.stdout


# (32) a protocol ticker is never admitted, so the comparability check skips
# it as _contract_model does: incomparable ids on its pack_scope rows still load.
def test_protocol_ticker_with_incomparable_ids_is_not_checked(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    rows = two_scoped_rows(SPLIT_ID, "s")
    rows["ticker"] = PROTOCOL["issuers"][0]
    contract = contract_path(
        tmp_path,
        {"split_decisions": [{"id": SPLIT_ID}, {"id": "s"}], "issuers": [rows]},
    )
    result = run_tool(root, "--packs", "PK12", "--contract", str(contract))
    assert result.returncode in (0, 1), result.stderr
    assert "Traceback" not in result.stderr
    assert report_of(result)["split_cohorts"] == {}

