"""Finding-only direct-native IO controls; no economic models or acquisitions.

The real native readers are exercised against explicitly undecodable synthetic
bytes or absence. A reader's missing/failed state is intentional, never a claim
that these inputs are financial evidence. The existing transaction fixture
supplies the already qualified same-invocation output contract independently.
"""
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess

import pytest

from scripts import render_intl_durable as durable
from tests.test_render_intl_durable import transaction, put, git, finish, build


@pytest.fixture(autouse=True)
def forbid_network(monkeypatch):
    import socket

    def forbidden(*args, **kwargs):
        pytest.fail("direct-native input controls prohibit network")

    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket.socket, "connect_ex", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)


def native_readers():
    from lib import (intl_boe_publication as boe, intl_ecb_policy_publication as ecb,
                     intl_eurostat_publication as euro, intl_annual_publication as annual,
                     intl_yield_publication as yields, intl_macro_publication as macro)
    return [
        ("data/" + boe.DIRECTORY.as_posix() + "/current.json", boe.read_boe_materialization),
        ("data/" + ecb.DIRECTORY.as_posix() + "/current.json", ecb.read_ecb_policy_materialization),
        *[("data/intl_macro/publication/" + euro._spec(field)["column"] + "/current.json",
           lambda *, data_root, _field=field: euro.read_eurostat_materialization(field=_field, data_root=data_root))
          for field in ("EZ.gdp_yoy", "EZ.cpi_yoy", euro.ANNUAL_FIELD)],
        ("data/" + annual.DIRECTORY.as_posix() + "/current.json", annual.read_current_account_materialization),
        ("data/" + yields.DIRECTORY.as_posix() + "/current.json", yields.read_jp_yield_materialization),
        ("data/intl_macro/ez_depo_rate.parquet", macro.read_ecb_deposit_materialization),
    ]


def with_native_builder(t, reader):
    original = t.builder.main

    def builder(**kwargs):
        assert reader(data_root=t.root / "data")["status"] in ("missing", "failed")
        return original(**kwargs)

    t.builder.main = builder


def upstream(t, path, body=b"new synthetic input"):
    blob = subprocess.check_output(["git", "-C", str(t.root), "hash-object", "-w", "--stdin"], input=body).decode().strip()
    env = dict(os.environ, GIT_INDEX_FILE=str(t.receipt.parent / "native-upstream.index"))
    subprocess.run(["git", "-C", str(t.root), "read-tree", t.source], env=env, check=True)
    subprocess.run(["git", "-C", str(t.root), "update-index", "--add", "--cacheinfo",
                    "100644," + blob + "," + path], env=env, check=True)
    tree = subprocess.check_output(["git", "-C", str(t.root), "write-tree"], env=env).decode().strip()
    return git(t.root, "commit-tree", tree, "-p", t.source, "-m", "controlled native input drift")


@pytest.mark.parametrize("index", range(8))
def test_every_absent_native_selector_or_fixed_pair_path_is_bound_before_read(transaction, index):
    t = transaction
    path, reader = native_readers()[index]
    with_native_builder(t, reader)
    finish(t)
    records = {r["path"]: r for r in json.loads(t.receipt.read_text())["inputs"]}
    assert records[path]["exists"] is False
    durable.verify(t.root, t.receipt)  # unchanged actual missing/failed stays honest
    with pytest.raises(durable.DurablePublicationError):
        durable.verify(t.root, t.receipt, target_ref=upstream(t, path))
    put(t.root, path, "new synthetic selector/body")
    with pytest.raises(durable.DurablePublicationError):
        durable.verify(t.root, t.receipt)


def selected_fixture(t, *, source_present=True, tracked=True):
    from lib import intl_ecb_policy_publication as ecb
    body = b"deliberately non-economic and undecodable CSV\n"
    artifact = b"deliberately non-economic and undecodable Parquet\n"
    receipt = {
        "schema": ecb.SCHEMA, "column": ecb.COLUMN, "source_id": ecb.SOURCE_ID,
        "source_url": ecb.SOURCE_URL, "source_sha256": sha256(body).hexdigest(),
        "artifact_sha256": sha256(artifact).hexdigest(),
        "requested_at": "2000-01-01T00:00:00Z", "response_received_at": "2000-01-01T00:00:01Z",
        "input_verified_at": "2000-01-01T00:00:02Z", "committed_at": "2000-01-01T00:00:03Z",
        "provider_published_at": None, "revision_vintage": None,
        "rows": 1, "first_observation": "2000-01-01", "last_observation": "2000-01-01",
    }
    raw = ecb._json(receipt)
    directory = "data/" + ecb.DIRECTORY.as_posix() + "/"
    paths = {"selector": directory + "current.json", "receipt": directory + sha256(raw).hexdigest() + ".json",
             "body": directory + sha256(body).hexdigest() + ".csv", "artifact": "data/intl_macro/ez_depo_rate.parquet"}
    put(t.root, paths["selector"], raw.decode())
    put(t.root, paths["receipt"], raw.decode())
    if source_present:
        put(t.root, paths["body"], body.decode())
    put(t.root, paths["artifact"], artifact.decode())
    # Selection metadata can be committed while its consumed body/cache is
    # untracked. The strict publisher must observe and then refuse that input.
    to_track = list(paths.values()) if tracked else [paths["selector"], paths["receipt"]]
    if not source_present:
        to_track.remove(paths["body"])
    git(t.root, "add", "--", *to_track)
    git(t.root, "commit", "-qm", "synthetic native selection, never economic evidence")
    t.source = git(t.root, "rev-parse", "HEAD")
    return paths, ecb.read_ecb_policy_materialization


@pytest.mark.parametrize("which", ["selector", "receipt", "body", "artifact"])
def test_present_selected_direct_dependencies_observed_without_git_enumeration(transaction, which):
    t = transaction
    paths, reader = selected_fixture(t)
    records = {}
    with durable._observe_store(t.root, records):
        assert reader(data_root=t.root / "data")["status"] == "failed"
    # A real reader reached all four paths before declining the synthetic parse.
    assert set(records) == set(paths.values())
    durable.validate_at_ref(t.root, t.source, list(records.values()))
    with pytest.raises(durable.DurablePublicationError):
        durable.validate_at_ref(t.root, upstream(t, paths[which]), list(records.values()))
    put(t.root, paths[which], "changed selected synthetic dependency")
    with pytest.raises(durable.DurablePublicationError):
        durable.validate_unchanged(t.root, list(records.values()))


def test_missing_selected_body_records_absence_and_blocks_appearance(transaction):
    t = transaction
    paths, reader = selected_fixture(t, source_present=False)
    with_native_builder(t, reader)
    finish(t)
    records = {r["path"]: r for r in json.loads(t.receipt.read_text())["inputs"]}
    assert records[paths["body"]]["exists"] is False
    with pytest.raises(durable.DurablePublicationError):
        durable.verify(t.root, t.receipt, target_ref=upstream(t, paths["body"]))
    put(t.root, paths["body"], "appeared after failed source read")
    with pytest.raises(durable.DurablePublicationError):
        durable.verify(t.root, t.receipt)


def test_untracked_consumed_body_and_artifact_refuse_publication(transaction):
    t = transaction
    paths, reader = selected_fixture(t, tracked=False)
    records = {}
    with durable._observe_store(t.root, records):
        assert reader(data_root=t.root / "data")["status"] == "failed"
    assert {paths["body"], paths["artifact"]} <= set(records)
    with pytest.raises(durable.DurablePublicationError, match="missing at ref"):
        durable.validate_at_ref(t.root, t.source, list(records.values()))
    with_native_builder(t, reader)
    with pytest.raises(durable.DurablePublicationError, match="missing at ref"):
        build(t)
    assert not t.receipt.exists()


def test_native_swallowed_observer_failure_is_sticky(transaction):
    t = transaction
    path, reader = native_readers()[0]
    target = put(t.root, "outside-synthetic-selector", "{}")
    (t.root / path).parent.mkdir(parents=True)
    (t.root / path).symlink_to(target)
    with_native_builder(t, reader)
    with pytest.raises(durable.DurablePublicationError):
        build(t)
    assert not t.receipt.exists()


@pytest.mark.parametrize("kind", ["status", "series"])
def test_existing_eod_direct_io_records_absence_before_shortcut(transaction, kind):
    t = transaction
    from lib import intl_eod_publication as eod
    records = {}
    with durable._observe_store(t.root, records):
        if kind == "series":
            assert eod._stored_witness(t.root / "data", "SYNTHETIC_X", None, None, None) is None
            path = "data/intl/SYNTHETIC_X.parquet"
        else:
            import pandas as pd
            # Empty typed frame and missing status intentionally refuse before
            # any arithmetic. This synthetic contract is not an access receipt.
            frame = pd.DataFrame(index=pd.DatetimeIndex([]))
            assert eod.build_eod_inputs(frame, data_root=t.root / "data",
                evaluated_at="2000-01-01T00:00:00Z", rights={"status": "confirmed",
                "scope": "intl-index-fx-eod-user-facing-v1", "decision_ref": "synthetic-test-only"}) is None
            path = "data/run_status.json"
    assert records[path]["exists"] is False
    put(t.root, path, "appeared synthetic dependency")
    with pytest.raises(durable.DurablePublicationError):
        durable.validate_unchanged(t.root, list(records.values()))


def test_output_role_never_exempts_an_arbitrary_generation_directory_file(transaction):
    t = transaction
    from lib.intl_macro_publication import _read_stable_once
    path = put(t.root, durable.GEN_DIR + "unrelated-input.json", "synthetic do-not-consume")
    with pytest.raises(durable.DurablePublicationError):
        with durable._observe_store(t.root, {}):
            _read_stable_once(path, 1024)
