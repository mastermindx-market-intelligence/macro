"""Invented wire records from the pinned Go JSON shape; no host inspection."""
from dataclasses import asdict
import hashlib
import json
import pytest
import host_identity as m

CID = "a" * 64


def records():
    oci = dict(ociVersion="1.2.1", id=CID, status="running", pid=101,
               bundle="/invented/private/bundle", annotations={})
    metadata = dict(id=CID, status="running", goferPid=102,
                    sandbox=dict(id=CID, pid=101,
                                 cgroup={"cgroupv2": {"Path": "/invented/cgroup"}}),
                    compatCgroup={"cgroupunknown": None},
                    spec={"process": {"env": ["PRIVATE_MARKER=invented"]}})
    return oci, metadata


def decode(oci, metadata):
    return m.decode_identity(json.dumps(oci).encode(), json.dumps(metadata).encode(),
                             expected_container_id=CID)


def test_exact_wire_join_redacts_private_fields_and_proves_no_host_facts():
    oci, metadata = records()
    result = decode(oci, metadata)
    assert (result.sandbox_pid, result.gofer_pid, result.cgroup_kind) == (101, 102, "cgroupv2")
    assert result.oci_state_sha256 == hashlib.sha256(json.dumps(oci).encode()).hexdigest()
    public = asdict(result)
    assert not public["host_observed"] and not public["helper_census_complete"]
    assert not public["cleanup_proven"]
    assert "PRIVATE_MARKER" not in json.dumps(public)
    assert "/invented" not in json.dumps(public)


def test_filename_is_implemented_state_file_shape_not_stale_meta_comment():
    assert m.state_basename(CID) == CID + "_sandbox:" + CID + ".state"


@pytest.mark.parametrize("cid", ["a", "A" * 64, "../" + CID, CID + "/x", True, None])
def test_no_partial_id_glob_or_path_lookup(cid):
    with pytest.raises(m.IdentityRefused, match="exact_container_id"):
        m.state_basename(cid)


@pytest.mark.parametrize("target,key,value", [
    ("oci", "id", "b" * 64), ("metadata", "id", "b" * 64),
    ("sandbox", "id", "b" * 64), ("sandbox", "pid", 103),
    ("sandbox", "pid", True), ("oci", "pid", 0), ("oci", "pid", -1),
    ("oci", "pid", True), ("oci", "pid", 2**31),
    ("metadata", "goferPid", True), ("metadata", "goferPid", -1),
    ("metadata", "goferPid", 101), ("metadata", "status", "created"),
    ("oci", "status", "stopped"), ("metadata", "sandbox", None),
    ("sandbox", "cgroup", {"cgroup": {"path": "/invented"}}),
    ("sandbox", "cgroup", {"cgroupv2": {}, "cgroupv1": {}}),
    ("sandbox", "cgroup", {"cgroupunknown": {"path": "/invented"}}),
])
def test_mismatched_or_unproved_identity_cannot_be_used(target, key, value):
    oci, metadata = records()
    {"oci": oci, "metadata": metadata, "sandbox": metadata["sandbox"]}[target][key] = value
    with pytest.raises(m.IdentityRefused):
        decode(oci, metadata)


def test_oci_state_is_not_internal_metadata_and_has_no_helper_fields():
    oci, metadata = records()
    with pytest.raises(m.IdentityRefused):
        decode(metadata, metadata)
    with pytest.raises(m.IdentityRefused):
        decode(oci, oci)
    oci["goferPid"] = 102
    with pytest.raises(m.IdentityRefused, match="oci_state_fields"):
        decode(oci, metadata)


def test_absent_gofer_or_unknown_cgroup_does_not_prove_cleanup():
    oci, metadata = records()
    metadata["goferPid"] = 0
    metadata["sandbox"]["cgroup"] = {"cgroupunknown": None}
    result = decode(oci, metadata)
    assert result.gofer_pid is None and result.cgroup_kind == "cgroupunknown"
    assert not result.cleanup_proven and not result.helper_census_complete


@pytest.mark.parametrize("raw", [b"{}" * 70000, b'{"id":1,"id":2}', b"NaN",
                                b'{"x":1e9999}', b'"not-an-object"', b"\xff"])
def test_bounded_strict_json(raw):
    with pytest.raises(m.IdentityRefused):
        m.decode_identity(raw, b"{}", expected_container_id=CID)


@pytest.mark.parametrize("encoding", ["utf-16", "utf-32"])
def test_non_utf8_records_are_not_runsc_json_wire_bytes(encoding):
    oci, metadata = records()
    with pytest.raises(m.IdentityRefused, match="record_json"):
        m.decode_identity(json.dumps(oci).encode(encoding),
                          json.dumps(metadata).encode(), expected_container_id=CID)
