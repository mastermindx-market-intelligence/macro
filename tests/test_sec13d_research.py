"""Retained-read custody, knowledge and validity differ from parser correctness."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from lib.dataos import sec13d_research as reader
from tests.test_dataos_sec13d_cusip import inputs

CUTOFF = "2026-10-19T20:01:00Z"
ON = "2026-04-30"


@pytest.fixture
def bundle(tmp_path):
    root = tmp_path / "retained"
    root.mkdir()
    repo = tmp_path / "native.git"
    subprocess.run(["git", "init", "--bare", str(repo)], check=True, capture_output=True)
    def git(*args, data=None):
        env = {**os.environ, "GIT_AUTHOR_NAME": "Fixture", "GIT_AUTHOR_EMAIL": "fixture@example.test",
               "GIT_COMMITTER_NAME": "Fixture", "GIT_COMMITTER_EMAIL": "fixture@example.test",
               "GIT_AUTHOR_DATE": "2026-10-19T19:59:59Z", "GIT_COMMITTER_DATE": "2026-10-19T19:59:59Z"}
        return subprocess.check_output(["git", "-C", str(repo), *args], input=data, env=env).decode().strip()
    data = inputs()
    blob = git("hash-object", "-w", "--stdin", data=data["master_raw"])
    tree = git("mktree", data=f"100644 blob {blob}\tsecurity_master.parquet\n".encode())
    tree = git("mktree", data=f"040000 tree {tree}\treference\n".encode())
    tree = git("mktree", data=f"040000 tree {tree}\tdata\n".encode())
    commit = git("commit-tree", tree, data=b"Fixture native master\n")
    (root / "0001104659-26-053223.txt").write_bytes(data["filing_raw"])
    (root / "registration.xml").write_bytes(data["registration_raw"])
    (root / "security_master.parquet").write_bytes(data["master_raw"])
    def acquisition(raw, url):
        return dict(source_url=url, status=200, bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest(),
                    request_started_at="2026-10-19T19:59:59Z", retained_at="2026-10-19T20:00:00Z")
    records = {
        "acquisition.json": acquisition(data["filing_raw"], "https://www.sec.gov/Archives/edgar/data/1811210/000110465926053223/0001104659-26-053223.txt"),
        "registration-acquisition.json": acquisition(data["registration_raw"], "https://www.sec.gov/Archives/edgar/data/1811210/000162828026011053/registration.xml"),
        "master-source.json": dict(commit=commit, path="data/reference/security_master.parquet",
                                   retained_at="2026-10-19T20:00:00Z", sha256=hashlib.sha256(data["master_raw"]).hexdigest()),
    }
    for name, value in records.items():
        (root / name).write_text(json.dumps(value))
    return root, repo


def read(bundle, **kwargs):
    return reader.read_retained_sec13d_research(*bundle,
        **{"decision_cutoff": CUTOFF, "security_on": ON, **kwargs})


def change_record(bundle, name, **fields):
    path = bundle[0] / name
    value = json.loads(path.read_text()); value.update(fields)
    path.write_text(json.dumps(value))


def test_actual_retained_assertions_and_pinned_master_are_a_research_read(bundle):
    out = read(bundle)
    assert out["state"] == "AVAILABLE_UNQUALIFIED"
    assert out["security_binding"]["canonical_security_id"] == "SEC:US-XNAS-LCID"
    assert out["security_binding"]["state"] == "ASSERTION_DAY_MATCHED_UNPUBLISHED"
    assert out["security_binding"]["alias_published"] is False
    facts = out["assertions"]
    assert (facts["event_on"], facts["accepted_at"]) == ("2026-04-28", "2026-04-30T22:26:24+00:00")
    assert "Ayar is a wholly-owned subsidiary of PIF." in facts["control_statement"]["text"]
    assert facts["control_statement"]["effective_interval"] is None
    people = facts["reporting_persons"]
    assert [(x["name"], x["cik"]) for x in people][-2:] == [("Turqi A. Alnowaiser", None), ("Yasir Alsalman", None)]
    assert people[1]["aggregate_amount_owned"] == "280992324"
    assert facts["position_statement"]["consumer_performed_quantity_aggregation"] is False
    assert all(v is False for v in out["authority"].values())
    assert out["qualifications"] == {"ownership_continuity": "UNKNOWN", "economic_vehicle_class": None,
                                   "decision_mode": None, "purpose_source_use": "UNKNOWN"}
    assert out["recipe"] is out["compiled"] is None
    assert out["k2c_admissible"] is out["k3e_admissible"] is False
    assert out["custody"]["canonical_owner_adoption"] is False
    assert len(out["source_references"]) == 3


def test_earlier_cutoff_exposes_no_later_facts_or_raw_reads(bundle, monkeypatch):
    def forbidden(*args):
        pytest.fail("raw source read before availability")
    monkeypatch.setattr(reader, "_sec_input", forbidden)
    out = read(bundle, decision_cutoff="2026-08-27T09:22:23.700168Z")
    assert out["state"] == "UNAVAILABLE"
    assert out["assertions"] is None and out["source_references"] == []
    assert out["security_binding"]["canonical_security_id"] is None


def test_later_identity_input_does_not_suppress_available_filing_or_leak_identity(bundle, monkeypatch):
    change_record(bundle, "master-source.json", retained_at="2026-10-20T00:00:00Z")
    monkeypatch.setattr(reader, "_master_input", lambda *a: pytest.fail("future master read"))
    out = read(bundle)
    assert out["state"] == "AVAILABLE_UNQUALIFIED" and out["assertions"]
    assert out["security_binding"] == {"state": "UNAVAILABLE", "canonical_security_id": None,
                                       "reason": "IDENTITY_INPUT_NOT_AVAILABLE_AT_CUTOFF"}
    assert len(out["source_references"]) == 1


@pytest.mark.parametrize("on", ["2026-03-31", "2026-04-28", "2026-05-01", "2026-06-30"])
def test_dated_assertion_does_not_become_quarter_or_event_day_security_history(bundle, on):
    out = read(bundle, security_on=on)
    assert out["state"] == "AVAILABLE_UNQUALIFIED"
    assert out["security_binding"]["canonical_security_id"] is None
    assert out["security_binding"]["reason"] == "VALID_DATE_NOT_SUPPORTED"
    assert out["assertions"]["assertion_scope"] == "AS_REPORTED_IN_THIS_FILING_NOT_CONTINUOUS_OWNERSHIP"


@pytest.mark.parametrize("name", ["0001104659-26-053223.txt", "registration.xml", "security_master.parquet"])
def test_tampered_retained_object_refuses(bundle, name):
    path = bundle[0] / name; path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(ValueError):
        read(bundle)


def test_rehashed_master_still_must_match_the_pinned_native_git_object(bundle):
    path = bundle[0] / "security_master.parquet"; path.write_bytes(path.read_bytes() + b" ")
    change_record(bundle, "master-source.json", sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    with pytest.raises(ValueError, match="^native master size mismatch$"):
        read(bundle)


@pytest.mark.parametrize("url", [
    "https://www.sec.gov.evil.test/Archives/edgar/data/1811210/000110465926053223/0001104659-26-053223.txt",
    "https://www.sec.gov/Archives/edgar/data/1874832/000110465926053223/0001104659-26-053223.txt",
    "https://www.sec.gov/Archives/edgar/data/1811210/000110465926053222/0001104659-26-053223.txt",
])
def test_http_record_origin_and_wire_identity_must_agree(bundle, url):
    change_record(bundle, "acquisition.json", source_url=url)
    with pytest.raises(ValueError):
        read(bundle)


def test_symlink_is_not_a_retained_file(bundle):
    path = bundle[0] / "registration.xml"; saved = path.read_bytes(); path.unlink()
    other = bundle[0] / "elsewhere.xml"; other.write_bytes(saved); path.symlink_to(other)
    with pytest.raises(ValueError, match="unavailable"):
        read(bundle)


def test_duplicate_or_reversed_acquisition_metadata_is_not_qualified(bundle):
    path = bundle[0] / "acquisition.json"
    raw = path.read_text(); path.write_text(raw[:-1] + ',"status":200}')
    with pytest.raises(ValueError, match="duplicate"):
        read(bundle)
    path.write_text(raw)
    change_record(bundle, "acquisition.json", request_started_at="2026-10-20T00:00:00Z")
    with pytest.raises(ValueError, match="reversed"):
        read(bundle)


def test_local_record_is_not_independently_authenticated_or_a_semantic_grant(bundle):
    change_record(bundle, "acquisition.json", owner_verified=True, can_rank=True)
    out = read(bundle)
    assert out["custody"]["clock_authentication"] == "NOT_INDEPENDENTLY_ATTESTED_BY_THIS_READER"
    assert out["custody"]["canonical_owner_adoption"] is False
    assert all(v is False for v in out["authority"].values())


def test_changed_global_authority_is_refused(bundle, monkeypatch):
    monkeypatch.setitem(reader.ALL_FALSE_AUTHORITY, "can_rank", True)
    with pytest.raises(ValueError, match="authority"):
        read(bundle)


def test_command_line_invokes_the_actual_local_read(bundle, capsys):
    reader.main(["--bundle-root", str(bundle[0]), "--repository", str(bundle[1]),
                 "--decision-cutoff", CUTOFF, "--security-on", ON])
    out = json.loads(capsys.readouterr().out)
    assert out["assertions"]["accession"] == "0001104659-26-053223"
    assert out["persistence"] == "none"


@pytest.mark.parametrize("committed, refused", [
    ("2026-10-19T20:00:00Z", False),
    ("2026-10-25T00:00:00Z", True),
])
def test_native_commit_cannot_postdate_its_claimed_retention(bundle, committed, refused):
    record = json.loads((bundle[0] / "master-source.json").read_text())
    tree = subprocess.check_output(["git", "-C", str(bundle[1]), "rev-parse", record["commit"] + "^{tree}"], text=True).strip()
    env = {**os.environ, "GIT_AUTHOR_NAME": "Fixture", "GIT_AUTHOR_EMAIL": "fixture@example.test",
           "GIT_COMMITTER_NAME": "Fixture", "GIT_COMMITTER_EMAIL": "fixture@example.test",
           "GIT_AUTHOR_DATE": committed, "GIT_COMMITTER_DATE": committed}
    commit = subprocess.check_output(["git", "-C", str(bundle[1]), "commit-tree", tree],
                                     input=b"Dated fixture snapshot\n", env=env).decode().strip()
    change_record(bundle, "master-source.json", commit=commit)
    if refused:
        with pytest.raises(ValueError, match="^native master commit follows claimed retention$"):
            read(bundle)
    else:
        assert read(bundle)["security_binding"]["canonical_security_id"] == "SEC:US-XNAS-LCID"


def test_same_size_rehashed_master_reports_the_specific_blob_mismatch(bundle):
    path = bundle[0] / "security_master.parquet"
    raw = path.read_bytes(); changed = bytes([raw[0] ^ 1]) + raw[1:]
    path.write_bytes(changed)
    change_record(bundle, "master-source.json", sha256=hashlib.sha256(changed).hexdigest())
    with pytest.raises(ValueError, match="^retained master differs from pinned native blob$"):
        read(bundle)


@pytest.mark.parametrize("name", ["acquisition.json", "registration.xml"])
def test_fifo_refuses_without_blocking_the_native_cli(bundle, name):
    path = bundle[0] / name; path.unlink(); os.mkfifo(path)
    result = subprocess.run([sys.executable, "-m", "lib.dataos.sec13d_research",
        "--bundle-root", str(bundle[0]), "--repository", str(bundle[1]),
        "--decision-cutoff", CUTOFF, "--security-on", ON],
        capture_output=True, text=True, timeout=5)
    assert result.returncode == 2
    assert result.stdout == ""
    assert "regular file" in result.stderr
