"""Discriminating tests for intl_durable_publication.

Tiny controlled Git repos and temp files only; no external input, no
network, no producer/collector/cloud delegation.
"""

import hashlib
import json
import os
import subprocess
import uuid

import pytest

from lib import intl_durable_publication as idp

GIT_IDENTITY = {
    "GIT_AUTHOR_NAME": "test",
    "GIT_AUTHOR_EMAIL": "test@example.com",
    "GIT_COMMITTER_NAME": "test",
    "GIT_COMMITTER_EMAIL": "test@example.com",
    "GIT_AUTHOR_DATE": "2026-01-01T00:00:00+0000",
    "GIT_COMMITTER_DATE": "2026-01-01T00:00:00+0000",
}

GENERATIONS = "data/intl/publication/generations"


def _git(repo, *args, input_bytes=None, extra_env=None):
    env = dict(os.environ)
    env.update(GIT_IDENTITY)
    env["GIT_CONFIG_GLOBAL"] = os.devnull
    env["GIT_CONFIG_SYSTEM"] = os.devnull
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    if extra_env:
        env.update(extra_env)
    proc = subprocess.run(
        ["git", *args],
        cwd=str(repo),
        env=env,
        input=input_bytes,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert proc.returncode == 0, proc.stderr.decode("utf-8", "replace")
    return proc.stdout.decode("utf-8", "replace")


def _plumb_commit(repo, changes, msg="drift"):
    """Commit blob changes on HEAD via plumbing, without touching the worktree.

    ``changes`` maps a repo path to new bytes (or None to remove it). The
    working tree and its stat identity stay sealed-unchanged, so only the
    upstream tree drifts.
    """
    index = os.path.join(str(repo), ".git", "tmpindex")
    index_env = {"GIT_INDEX_FILE": index}
    head = _head(repo)
    try:
        _git(repo, "read-tree", head, extra_env=index_env)
        for rel, data in changes.items():
            if data is None:
                _git(repo, "update-index", "--force-remove", rel, extra_env=index_env)
                continue
            blob = _git(repo, "hash-object", "-w", "--stdin", input_bytes=data).strip()
            _git(
                repo,
                "update-index", "--add", "--cacheinfo",
                "100644,%s,%s" % (blob, rel),
                extra_env=index_env,
            )
        tree = _git(repo, "write-tree", extra_env=index_env).strip()
        return _git(
            repo, "-c", "commit.gpgsign=false", "commit-tree", tree,
            "-p", head, "-m", msg, extra_env=index_env,
        ).strip()
    finally:
        if os.path.exists(index):
            os.remove(index)


def _commit(repo, msg="c"):
    _git(repo, "add", "-A")
    _git(repo, "-c", "commit.gpgsign=false", "commit", "-q", "-m", msg)
    return _git(repo, "rev-parse", "HEAD").strip()


def _head(repo):
    return _git(repo, "rev-parse", "HEAD").strip()


def _write(repo, rel, data):
    path = os.path.join(str(repo), rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as fh:
        fh.write(data)


def _read(repo, rel):
    with open(os.path.join(str(repo), rel), "rb") as fh:
        return fh.read()


INPUT_BYTES = {
    "templates/intl.tmpl.json": b'{"layout":"intl"}\n',
    "data/intl/risk_points.json": b'{"points":[1,2,3]}\n',
}
INPUT_PATHS = sorted(INPUT_BYTES)


def _sha256(data):
    return hashlib.sha256(data).hexdigest()


def _output_bytes():
    return {
        "site/intl.html": b"<html><body>intl risk</body></html>\n",
        "data/intl_risk/latest.json": b'{"build":"sealed"}\n',
        "%s/intl_generation_%s_%s.json"
        % (GENERATIONS, uuid.uuid4(), _sha256(b'{"generation":true}\n')): b'{"generation":true}\n',
        "%s/intl_generation_descriptor_%s.json" % (GENERATIONS, _sha256(b'{"descriptor":true}\n')): b'{"descriptor":true}\n',
        "%s/intl_policy_points_%s_%s.json"
        % (GENERATIONS, uuid.uuid4(), _sha256(b'{"policy_points":[]}\n')): b'{"policy_points":[]}\n',
        "%s/intl_generation_current.json" % GENERATIONS: b'{"gen":"cur"}\n',
    }


def _world(repo):
    for rel, data in INPUT_BYTES.items():
        _write(repo, rel, data)
    source_sha = _commit(repo, "source")
    outputs = _output_bytes()
    for rel, data in outputs.items():
        _write(repo, rel, data)
    _commit(repo, "publish")
    return source_sha, sorted(outputs)


def _record_by_path(records, path):
    for record in records:
        if record["path"] == path:
            return record
    pytest.fail("no record for %r" % (path,))


@pytest.fixture()
def repo(tmp_path):
    base = tmp_path / "repo"
    base.mkdir()
    _git(base, "init", "-q")
    return base


@pytest.fixture()
def sealed(repo):
    source_sha, output_paths = _world(repo)
    inputs = idp.capture_inputs(repo, INPUT_PATHS)
    manifest = idp.build_manifest(repo, source_sha, inputs, output_paths)
    return repo, source_sha, manifest


# ---------------------------------------------------------------------------
# capture_inputs


def test_capture_sorted_records_with_stable_absence(repo):
    _write(repo, INPUT_PATHS[0], INPUT_BYTES[INPUT_PATHS[0]])
    records = idp.capture_inputs(repo, [INPUT_PATHS[0], "missing/child.json"])
    assert [r["path"] for r in records] == [INPUT_PATHS[0], "missing/child.json"]
    present = _record_by_path(records, INPUT_PATHS[0])
    assert set(present) == {"path", "exists", "sha256", "git_blob", "size", "identity"}
    assert present["exists"] is True
    assert present["size"] == len(INPUT_BYTES[INPUT_PATHS[0]])
    assert present["sha256"] == _sha256(INPUT_BYTES[INPUT_PATHS[0]])
    assert set(present["identity"]) == {
        "dev", "ino", "mode", "uid", "gid", "size", "mtime_ns", "ctime_ns",
    }
    absent = _record_by_path(records, "missing/child.json")
    assert absent["exists"] is False
    assert absent["sha256"] is None
    assert absent["git_blob"] is None
    assert absent["size"] is None
    assert absent["identity"] is None
    with pytest.raises(idp.DurablePublicationError):
        idp.capture_inputs(repo, ["missing/child.json"], allow_missing=False)


def test_capture_git_blob_matches_hash_object(repo):
    payload = b"payload\n"
    _write(repo, "in.txt", payload)
    record = idp.capture_inputs(repo, ["in.txt"])[0]
    assert record["git_blob"] == _git(repo, "hash-object", "in.txt").strip()
    assert record["git_blob"] == hashlib.sha1(b"blob %d\0" % len(payload) + payload).hexdigest()


def test_capture_rejects_traversal_absolute_backslash_nul(repo):
    for bad in (
        "../outside.txt",
        "a/../../b.txt",
        "a/./b.txt",
        "/etc/passwd",
        "a\\b.txt",
        "a/b\0.txt",
        "a//b.txt",
        "trailing/",
    ):
        with pytest.raises(idp.DurablePublicationError):
            idp.capture_inputs(repo, [bad])


def test_capture_rejects_symlink_component_and_symlink_file(tmp_path):
    _write(tmp_path, "real.txt", b"hi\n")
    os.symlink(str(tmp_path), str(tmp_path / "linkdir"))
    os.symlink(os.path.join(str(tmp_path), "real.txt"), str(tmp_path / "link.txt"))
    os.symlink("no-such-target", str(tmp_path / "dangling.txt"))
    for path in (
        "linkdir/file.txt",
        "linkdir/nope.json",
        "link.txt",
        "dangling.txt",
    ):
        with pytest.raises(idp.DurablePublicationError):
            idp.capture_inputs(tmp_path, [path], allow_missing=True)


def test_capture_rejects_duplicate_and_nonregular(repo):
    _write(repo, "in.txt", b"x\n")
    _write(repo, "data/inner", b"")
    with pytest.raises(idp.DurablePublicationError):
        idp.capture_inputs(repo, ["in.txt", "in.txt"])
    with pytest.raises(idp.DurablePublicationError):
        idp.capture_inputs(repo, ["data"])
    if hasattr(os, "mkfifo"):
        os.mkfifo(os.path.join(str(repo), "fifo"))
        with pytest.raises(idp.DurablePublicationError):
            idp.capture_inputs(repo, ["fifo"])


def test_capture_per_file_cap_boundary(tmp_path):
    exact = b"a" * idp.PER_FILE_BYTES_CAP
    _write(tmp_path, "exact.bin", exact)
    record = idp.capture_inputs(tmp_path, ["exact.bin"])[0]
    assert record["size"] == idp.PER_FILE_BYTES_CAP
    _write(tmp_path, "big.bin", b"b" * (idp.PER_FILE_BYTES_CAP + 1))
    with pytest.raises(idp.DurablePublicationError):
        idp.capture_inputs(tmp_path, ["big.bin"])


def test_capture_aggregate_cap(tmp_path, monkeypatch):
    monkeypatch.setattr(idp, "AGGREGATE_BYTES_CAP", 64)
    _write(tmp_path, "a.txt", b"x" * 40)
    _write(tmp_path, "b.txt", b"y" * 40)
    idp.capture_inputs(tmp_path, ["a.txt"])
    with pytest.raises(idp.DurablePublicationError):
        idp.capture_inputs(tmp_path, ["a.txt", "b.txt"])


# ---------------------------------------------------------------------------
# validate_unchanged


def test_validate_unchanged_detects_equal_size_mutation(repo):
    _write(repo, "in.txt", b"aaaa\n")
    records = idp.capture_inputs(repo, ["in.txt"])
    _write(repo, "in.txt", b"bbbb\n")
    with pytest.raises(idp.DurablePublicationError):
        idp.validate_unchanged(repo, records)


def test_validate_unchanged_detects_replaced_inode(repo):
    _write(repo, "in.txt", b"same\n")
    records = idp.capture_inputs(repo, ["in.txt"])
    path = os.path.join(str(repo), "in.txt")
    os.remove(path)
    with open(path, "wb") as fh:
        fh.write(b"same\n")
    with pytest.raises(idp.DurablePublicationError):
        idp.validate_unchanged(repo, records)


def test_validate_unchanged_detects_deletion_and_appearance(repo):
    _write(repo, "in.txt", b"x\n")
    records = idp.capture_inputs(repo, ["in.txt", "absent.json"])
    os.remove(os.path.join(str(repo), "in.txt"))
    with pytest.raises(idp.DurablePublicationError):
        idp.validate_unchanged(repo, records)
    # Fresh records over restored bytes validate cleanly, then appearance
    # of the recorded-absent path refuses.
    records = idp.capture_inputs(repo, ["in.txt", "absent.json"])
    idp.validate_unchanged(repo, records)
    _write(repo, "absent.json", b"now here\n")
    with pytest.raises(idp.DurablePublicationError):
        idp.validate_unchanged(repo, records)


# ---------------------------------------------------------------------------
# validate_at_ref


def test_validate_at_ref_proves_blob_and_absence(repo):
    _write(repo, "in.txt", b"tracked\n")
    sha = _commit(repo)
    records = idp.capture_inputs(repo, ["in.txt", "missing.json"])
    idp.validate_at_ref(repo, sha, records)


def test_validate_at_ref_refuses_bad_sha_formats(repo):
    _write(repo, "in.txt", b"x\n")
    sha = _commit(repo)
    records = idp.capture_inputs(repo, ["in.txt"])
    for bad in (sha.upper(), sha[:39], "z" * 40, 123, None):
        with pytest.raises(idp.DurablePublicationError):
            idp.validate_at_ref(repo, bad, records)
    with pytest.raises(idp.DurablePublicationError):
        idp.validate_at_ref(repo, "0" * 40, records)


def test_validate_at_ref_refuses_blob_drift_and_absence_drift(repo):
    _write(repo, "in.txt", b"old\n")
    sha_old = _commit(repo)
    records_old = idp.capture_inputs(repo, ["in.txt"])
    absent = idp.capture_inputs(repo, ["appeared.json"])[0]
    _write(repo, "in.txt", b"new\n")
    _write(repo, "appeared.json", b"late\n")
    sha_new = _commit(repo)
    idp.validate_at_ref(repo, sha_old, [records_old[0], absent])
    with pytest.raises(idp.DurablePublicationError):
        idp.validate_at_ref(repo, sha_new, records_old)
    with pytest.raises(idp.DurablePublicationError):
        idp.validate_at_ref(repo, sha_new, [absent])


def test_validate_at_ref_allows_unrelated_upstream_change(repo):
    _write(repo, "in.txt", b"mine\n")
    sha = _commit(repo)
    records = idp.capture_inputs(repo, ["in.txt"])
    _write(repo, "docs/other.txt", b"unrelated\n")
    sha2 = _commit(repo)
    idp.validate_at_ref(repo, sha, records)
    idp.validate_at_ref(repo, sha2, records)


# ---------------------------------------------------------------------------
# build_manifest


def test_build_manifest_seals_strict_shape(repo):
    source_sha, output_paths = _world(repo)
    inputs = idp.capture_inputs(repo, INPUT_PATHS)
    manifest = idp.build_manifest(repo, source_sha, inputs, output_paths)
    assert set(manifest) == {"schema", "source_sha", "inputs", "outputs"}
    assert manifest["schema"] == "intl.durable_publication.v1"
    assert manifest["source_sha"] == source_sha
    assert "current" not in manifest and "status" not in manifest
    assert [r["path"] for r in manifest["inputs"]] == INPUT_PATHS
    assert [r["path"] for r in manifest["outputs"]] == sorted(output_paths)
    assert {r["path"] for r in manifest["outputs"]} >= set(idp.REQUIRED_OUTPUT_PATHS)
    assert json.loads(json.dumps(manifest)) == manifest  # truthful JSON receipt
    idp.validate_manifest(repo, manifest)
    # The publish commit is the tracked tree that holds the sealed outputs.
    idp.validate_manifest(repo, manifest, target_sha=_head(repo))


def test_build_manifest_passes_after_unrelated_upstream_change(sealed):
    repo, _source_sha, manifest = sealed
    _write(repo, "docs/notes.txt", b"unrelated\n")
    other = _commit(repo)
    idp.validate_manifest(repo, manifest, target_sha=other)


def test_build_manifest_requires_outputs_on_disk(repo):
    source_sha, output_paths = _world(repo)
    inputs = idp.capture_inputs(repo, INPUT_PATHS)
    os.remove(os.path.join(str(repo), output_paths[-1]))
    with pytest.raises(idp.DurablePublicationError):
        idp.build_manifest(repo, source_sha, inputs, output_paths)


def test_build_manifest_requires_required_outputs(repo):
    source_sha, output_paths = _world(repo)
    inputs = idp.capture_inputs(repo, INPUT_PATHS)
    reduced = [p for p in output_paths if p != "site/intl.html"]
    with pytest.raises(idp.DurablePublicationError):
        idp.build_manifest(repo, source_sha, inputs, reduced)


def test_build_manifest_rejects_extra_output_paths(repo):
    source_sha, output_paths = _world(repo)
    inputs = idp.capture_inputs(repo, INPUT_PATHS)
    for extra in (
        "data/intl_risk/raw_dump.json",
        "data/intl/publication/status.json",
        "templates/out.html",
        "site/../escape.html",
        "%s/extra_gen.json" % GENERATIONS,
    ):
        with pytest.raises(idp.DurablePublicationError):
            idp.build_manifest(repo, source_sha, inputs, list(output_paths) + [extra])


def test_build_manifest_rejects_duplicate_outputs(repo):
    source_sha, output_paths = _world(repo)
    inputs = idp.capture_inputs(repo, INPUT_PATHS)
    with pytest.raises(idp.DurablePublicationError):
        idp.build_manifest(
            repo, source_sha, inputs, list(output_paths) + ["site/intl.html"]
        )


def test_build_manifest_rejects_immutable_sha_name_mismatch(repo):
    _write(repo, INPUT_PATHS[0], INPUT_BYTES[INPUT_PATHS[0]])
    source_sha = _commit(repo)
    outputs = _output_bytes()
    good_name = "%s/intl_generation_descriptor_%s.json" % (
        GENERATIONS, _sha256(b'{"descriptor":true}\n'),
    )
    del outputs[good_name]
    wrong_named = "%s/intl_generation_descriptor_%s.json" % (
        GENERATIONS, _sha256(b"other"),
    )
    outputs[wrong_named] = b'{"descriptor":true}\n'
    for rel, data in outputs.items():
        _write(repo, rel, data)
    _commit(repo, "publish")
    inputs = idp.capture_inputs(repo, INPUT_PATHS)
    with pytest.raises(idp.DurablePublicationError):
        idp.build_manifest(repo, source_sha, inputs, sorted(outputs))


def test_build_manifest_refuses_input_ref_drift(repo):
    _write(repo, INPUT_PATHS[0], INPUT_BYTES[INPUT_PATHS[0]])
    source_sha = _commit(repo)
    _write(repo, INPUT_PATHS[0], INPUT_BYTES[INPUT_PATHS[0]] + b"changed\n")
    inputs = idp.capture_inputs(repo, INPUT_PATHS)
    with pytest.raises(idp.DurablePublicationError):
        idp.build_manifest(
            repo, source_sha, inputs, ["site/intl.html", "data/intl_risk/latest.json"]
        )


# ---------------------------------------------------------------------------
# validate_manifest


def test_validate_manifest_rejects_malformed(sealed):
    repo, _source_sha, manifest = sealed
    good = json.loads(json.dumps(manifest))

    bad_schema = dict(good)
    bad_schema["schema"] = "intl.durable_publication.v2"
    with pytest.raises(idp.DurablePublicationError):
        idp.validate_manifest(repo, bad_schema)

    extra_key = dict(good)
    extra_key["generated_at"] = "2026-01-01"
    with pytest.raises(idp.DurablePublicationError):
        idp.validate_manifest(repo, extra_key)

    missing_key = {k: v for k, v in good.items() if k != "outputs"}
    with pytest.raises(idp.DurablePublicationError):
        idp.validate_manifest(repo, missing_key)

    unsorted = dict(good)
    unsorted["inputs"] = list(reversed(good["inputs"]))
    with pytest.raises(idp.DurablePublicationError):
        idp.validate_manifest(repo, unsorted)

    dup_record = dict(good)
    dup_record["outputs"] = list(good["outputs"]) + [dict(good["outputs"][0])]
    with pytest.raises(idp.DurablePublicationError):
        idp.validate_manifest(repo, dup_record)

    not_allowed = dict(good)
    not_allowed["outputs"] = list(good["outputs"]) + [
        {
            "path": "data/intl_risk/extra.json",
            "exists": True,
            "sha256": "a" * 64,
            "git_blob": "b" * 40,
            "size": 2,
            "identity": {k: 1 for k in (
                "dev", "ino", "mode", "uid", "gid", "size", "mtime_ns", "ctime_ns",
            )},
        }
    ]
    with pytest.raises(idp.DurablePublicationError):
        idp.validate_manifest(repo, not_allowed)

    fabricated = json.loads(json.dumps(good))
    fabricated["inputs"] = [dict(good["inputs"][0])]
    fabricated["inputs"][0]["sha256"] = "c" * 64
    with pytest.raises(idp.DurablePublicationError):
        idp.validate_manifest(repo, fabricated)

    absent_output = json.loads(json.dumps(good))
    absent_output["outputs"] = [dict(good["outputs"][0])]
    for key in ("sha256", "git_blob", "size", "identity"):
        absent_output["outputs"][0][key] = None
    absent_output["outputs"][0]["exists"] = False
    with pytest.raises(idp.DurablePublicationError):
        idp.validate_manifest(repo, absent_output)


def test_validate_manifest_refuses_output_mutation_same_size(sealed):
    repo, _source_sha, manifest = sealed
    rel = "site/intl.html"
    old = _read(repo, rel)
    new = old.replace(b"intl", b"INTL")
    assert len(new) == len(old)
    _write(repo, rel, new)
    with pytest.raises(idp.DurablePublicationError):
        idp.validate_manifest(repo, manifest)


def test_validate_manifest_refuses_input_mutation(sealed):
    repo, _source_sha, manifest = sealed
    rel = INPUT_PATHS[0]
    _write(repo, rel, _read(repo, rel) + b"\x00")
    with pytest.raises(idp.DurablePublicationError):
        idp.validate_manifest(repo, manifest)


def test_validate_manifest_refuses_target_ref_drift(sealed):
    repo, _source_sha, manifest = sealed
    drifted = _plumb_commit(
        repo,
        {INPUT_PATHS[0]: INPUT_BYTES[INPUT_PATHS[0]] + b"drifted\n"},
        msg="drift",
    )
    idp.validate_manifest(repo, manifest)  # disk identity still matches the seal
    with pytest.raises(idp.DurablePublicationError):
        idp.validate_manifest(repo, manifest, target_sha=drifted)


def test_validate_manifest_refuses_input_removed_at_target_ref(sealed):
    repo, _source_sha, manifest = sealed
    removed = _plumb_commit(repo, {INPUT_PATHS[0]: None}, msg="drop input")
    with pytest.raises(idp.DurablePublicationError):
        idp.validate_manifest(repo, manifest, target_sha=removed)


def test_validate_manifest_refuses_absent_input_present_at_ref(sealed):
    repo, _source_sha, manifest = sealed
    late = json.loads(json.dumps(manifest))
    late["inputs"] = sorted(
        list(manifest["inputs"]) + [idp.capture_inputs(repo, ["not_yet.json"])[0]],
        key=lambda r: r["path"],
    )
    _write(repo, "not_yet.json", b"appeared\n")
    appeared = _commit(repo, "appeared")
    os.remove(os.path.join(str(repo), "not_yet.json"))
    _commit(repo, "hide")
    idp.validate_manifest(repo, late, target_sha=_head(repo))  # absent at HEAD
    with pytest.raises(idp.DurablePublicationError):
        idp.validate_manifest(repo, late, target_sha=appeared)


def test_validate_manifest_rejects_immutable_sha_name_binding(sealed):
    repo, _source_sha, manifest = sealed
    renamed = json.loads(json.dumps(manifest))
    for record in renamed["outputs"]:
        if "intl_generation_descriptor_" in record["path"]:
            forged = _sha256(b"forged")
            assert record["sha256"] in record["path"]
            record["path"] = record["path"].replace(record["sha256"], forged)
            break
    else:
        pytest.fail("no immutable sha-named output in world")
    renamed["outputs"] = sorted(renamed["outputs"], key=lambda r: r["path"])
    with pytest.raises(idp.DurablePublicationError):
        idp.validate_manifest(repo, renamed)


def test_validate_manifest_refuses_bad_target_sha(sealed):
    repo, _source_sha, manifest = sealed
    for bad in ("zz" * 20, "abc", 5):
        with pytest.raises(idp.DurablePublicationError):
            idp.validate_manifest(repo, manifest, target_sha=bad)
