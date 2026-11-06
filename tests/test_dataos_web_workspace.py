"""Real filesystem and Parquet boundary tests for the web data workspace."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
import yaml

from lib.dataos.web_workspace import (
    DataWorkspace, RootBinding, WorkspaceError, load_workspace_config,
)


@pytest.fixture
def case(tmp_path):
    root = tmp_path / "source-data"
    root.mkdir()
    registry = tmp_path / "registry.yml"
    base = {
        "dataset_id": "fixture.prices", "layer": "L1", "status": "PROPOSED",
        "owner": "fixture-owner", "producer": "fixture-producer",
        "storage": "data/stocks/{ticker}.parquet", "format": "parquet",
        "grain": ["ticker", "Date"], "temporal_profile": "BARS",
        "version": "1.0.0", "schema": {"close": {"dtype": "float64"}},
    }
    derived = dict(base, dataset_id="fixture.summary", layer="L3", inputs=["fixture.prices"])
    registry.write_text(yaml.safe_dump({"schema": "dataset_registry.v1", "datasets": [base, derived]}))
    prices = root / "prices.parquet"
    dates = [dt.datetime(2026, 10, n, tzinfo=dt.timezone.utc) for n in [5, 6, 7, 8]]
    table = pa.table({
        "Date": dates,
        "available_at": [value + dt.timedelta(days=1) for value in dates],
        "ticker": ["AMD", "AMD", "MU", "AMD"],
        "close": [100.0, None, 200.0, 104.0],
    })
    pq.write_table(table, prices, row_group_size=2)
    # Deliberately separate stored data clocks from old filesystem metadata.
    os.utime(prices, (946684800, 946684800))
    ws = DataWorkspace(
        (RootBinding("fixture", root, "research_capture", "Synthetic fixtures; no admission"),),
        registry,
        source_revision="c" * 40,
    )
    config = tmp_path / "host.json"
    payload = {
        "schema_version": "mastermind.data_workspace_bindings/v1",
        "registry_path": "registry.yml",
        "roots": [{"alias": "fixture", "path": str(root), "evidence_kind": "research_capture"}],
    }
    config.write_text(json.dumps(payload))
    return SimpleNamespace(ws=ws, root=root, registry=registry, prices=prices,
                           config=config, payload=payload, tmp=tmp_path)


def _snapshot(root):
    return {
        path.relative_to(root).as_posix(): (
            path.stat().st_mtime_ns, path.stat().st_ctime_ns,
            hashlib.sha256(path.read_bytes()).hexdigest(),
        )
        for path in root.rglob("*") if path.is_file()
    }


def test_describe_reports_real_footer_clocks_and_unqualified_provenance(case):
    before = _snapshot(case.root)
    result = case.ws.describe("fixture:prices.parquet")
    details, source = result["details"], result["source"]
    assert details["row_count"] == 4 and details["row_groups"] == 2
    assert details["time_ranges"]["Date"]["min"].startswith("2026-10-05")
    assert details["time_ranges"]["Date"]["max"].startswith("2026-10-08")
    assert details["time_ranges"]["available_at"]["max"].startswith("2026-10-09")
    assert details["time_ranges"]["Date"]["statistics_complete"]
    assert source["filesystem_mtime"].startswith("2000-01-01")
    assert source["filesystem_mtime_is_data_freshness"] is False
    assert source["content_sha256"] is None
    assert source["file_version"].startswith("statv1:")
    assert source["registry_admission"] == "NOT_INFERRED_FROM_FILE_PRESENCE"
    assert source["evidence_kind"] == "research_capture"
    assert result["implementation_revision"] == "c" * 40
    assert result["production_qualification"] == "NOT_ESTABLISHED_BY_THIS_ADAPTER"
    assert result["source_access"] == "read_only"
    assert str(case.root) not in json.dumps(result)
    assert _snapshot(case.root) == before


def test_read_filters_actual_rows_preserves_nulls_and_reproducible_query_receipt(case):
    before = _snapshot(case.root)
    version = case.ws.describe("fixture:prices.parquet")["source"]["file_version"]
    request = dict(
        ref="fixture:prices.parquet", columns=["Date", "close"], time_column="Date",
        start="2026-10-06", end="2026-10-08", equals={"ticker": "AMD"},
        limit=10, expected_version=version,
    )
    one, two = case.ws.read(**request), case.ws.read(**request)
    assert [row["close"] for row in one["result"]["rows"]] == [None, 104.0]
    assert one["result"]["row_positions"] == [1, 3]
    assert one["result"]["scan_complete"]
    assert one["source"]["file_version"] == version
    assert one["query_receipt_sha256"] == two["query_receipt_sha256"]
    assert len(one["query_receipt_sha256"]) == 64
    assert one["price_basis"] == "PRESERVED_AS_STORED_NOT_REBASED"
    assert "point-in-time" in one["temporal_caution"]
    json.dumps(one, allow_nan=False)
    assert _snapshot(case.root) == before


def test_search_distinguishes_contract_declarations_physical_files_and_missing_roots(case):
    missing = RootBinding("missing", case.tmp / "not-present", "proposed_source")
    ws = DataWorkspace(tuple(case.ws.roots.values()) + (missing,), case.registry)
    result = ws.search("prices")
    contract = next(row for row in result["results"] if row["kind"] == "registered_contract")
    physical = next(row for row in result["results"] if row["kind"] == "physical_namespace")
    assert contract["ref"] == "registry:fixture.prices"
    assert contract["status"] == "PROPOSED"
    assert contract["availability"] == "NOT_ESTABLISHED_BY_DECLARATION"
    assert physical["ref"] == "fixture:prices.parquet"
    assert physical["registry_admission"] == "NOT_INFERRED"
    state = next(row for row in result["roots"] if row["root_alias"] == "missing")
    assert state["state"] == "SOURCE_NOT_FOUND" and not state["namespace_scan_complete"]
    described = ws.describe("registry:fixture.prices")
    assert described["declared_consumers"] == ["fixture.summary"]
    assert described["availability"] == "NOT_ESTABLISHED_BY_DECLARATION"


def test_browse_pins_directory_version_across_pages_and_rejects_later_change(case):
    (case.root / "more.csv").write_text("x\n1\n")
    (case.root / "nested").mkdir()
    first = case.ws.browse("fixture", limit=1)
    assert first["next_offset"] == 1
    second = case.ws.browse("fixture", offset=1, limit=1,
                            expected_directory_version=first["directory_version"])
    assert second["directory_version"] == first["directory_version"]
    assert first["entries"][0]["ref"] != second["entries"][0]["ref"]
    (case.root / "new.csv").write_text("x\n2\n")
    with pytest.raises(WorkspaceError) as error:
        case.ws.browse("fixture", expected_directory_version=first["directory_version"])
    assert error.value.code == "DIRECTORY_VERSION_MISMATCH"


def test_hidden_entries_count_toward_scan_budget_without_being_returned(case):
    hidden = case.root / "hidden-entries"
    hidden.mkdir()
    for name in [".one", ".two", ".three", "api_key.json"]:
        (hidden / name).write_text("do not project")
    with case.ws._directory(case.ws.roots["fixture"], ("hidden-entries",)) as fd:
        entries, complete = case.ws._entries(fd, "fixture", "hidden-entries", cap=2)
    assert entries == []
    assert complete is False


@pytest.mark.parametrize("relative", [
    "../outside.csv", "/etc/passwd", "sub/../prices.parquet", "sub//prices.parquet",
    "./prices.parquet", ".env", ".ssh/key", "api_key.json", "secret_store/data.csv",
    "sub\\prices.parquet", "prices.parquet\x00",
])
def test_traversal_hidden_and_sensitive_paths_are_refused(case, relative):
    with pytest.raises(WorkspaceError) as error:
        case.ws.read("fixture:" + relative)
    assert error.value.code == "PATH_REFUSED"
    assert str(case.root) not in str(error.value)


def test_unbound_root_and_malformed_ref_have_closed_errors(case):
    with pytest.raises(WorkspaceError) as error:
        case.ws.describe("elsewhere:prices.parquet")
    assert error.value.code == "ROOT_NOT_BOUND"
    with pytest.raises(WorkspaceError) as error:
        case.ws.describe("prices.parquet")
    assert error.value.code == "INVALID_DATA_REF"


def test_leaf_and_ancestor_child_symlinks_cannot_escape_root(case):
    outside = case.tmp / "outside"
    outside.mkdir()
    (outside / "other.csv").write_text("close\n777\n")
    (case.root / "leaf.csv").symlink_to(outside / "other.csv")
    (case.root / "bridge").symlink_to(outside, target_is_directory=True)
    for ref in ["fixture:leaf.csv", "fixture:bridge/other.csv"]:
        with pytest.raises(WorkspaceError) as error:
            case.ws.read(ref)
        assert error.value.code == "PATH_OR_SOURCE_REFUSED"


def test_symlink_as_configured_root_is_refused(case):
    alias = case.tmp / "root-link"
    alias.symlink_to(case.root, target_is_directory=True)
    ws = DataWorkspace((RootBinding("alias", alias),), case.registry)
    with pytest.raises(WorkspaceError) as error:
        ws.describe("alias:prices.parquet")
    assert error.value.code == "PATH_OR_SOURCE_REFUSED"


def test_hardlinked_file_is_refused_under_both_names(case):
    os.link(case.prices, case.root / "linked.parquet")
    for name in ["prices.parquet", "linked.parquet"]:
        with pytest.raises(WorkspaceError) as error:
            case.ws.read("fixture:" + name)
        assert error.value.code == "REGULAR_PRIVATE_FILE_REQUIRED"


def test_fifo_and_directory_are_refused_without_blocking(case):
    os.mkfifo(case.root / "pipe.csv")
    (case.root / "directory.csv").mkdir()
    for name in ["pipe.csv", "directory.csv"]:
        with pytest.raises(WorkspaceError) as error:
            case.ws.read("fixture:" + name)
        assert error.value.code == "REGULAR_PRIVATE_FILE_REQUIRED"


def test_expected_source_version_refuses_changed_source(case):
    old = case.ws.describe("fixture:prices.parquet")["source"]["file_version"]
    os.utime(case.prices, ns=(1_800_000_000_000_000_000,) * 2)
    with pytest.raises(WorkspaceError) as error:
        case.ws.read("fixture:prices.parquet", expected_version=old)
    assert error.value.code == "SOURCE_VERSION_MISMATCH"


@pytest.mark.parametrize("change", ["append", "replace"])
def test_open_source_change_is_detected_before_return(case, change):
    with pytest.raises(WorkspaceError) as error:
        with case.ws._file("fixture:prices.parquet") as (stream, _source):
            assert stream.read(4) == b"PAR1"
            if change == "append":
                with case.prices.open("ab") as out:
                    out.write(b"changed")
            else:
                replacement = case.root / "replacement.parquet"
                replacement.write_bytes(case.prices.read_bytes())
                replacement.replace(case.prices)
    assert error.value.code == "SOURCE_CHANGED"


def test_root_inode_replacement_is_detected(case):
    with pytest.raises(WorkspaceError) as error:
        with case.ws._directory(case.ws.roots["fixture"], ()):
            case.root.rename(case.tmp / "original-root")
            case.root.mkdir()
    assert error.value.code == "ROOT_BINDING_CHANGED"


def test_large_logical_offset_is_accepted_without_large_read(case):
    result = case.ws.read("fixture:prices.parquet", columns=["close"],
                          offset=2_000_000_000, limit=1)
    assert result["result"]["rows"] == []
    assert result["result"]["scanned_rows"] == 0
    assert result["result"]["scan_complete"] and result["result"]["next_offset"] is None


def test_raw_archive_is_metadata_only(case):
    raw = case.root / "capture.pcap.gz"
    raw.write_bytes(b"fixture raw bytes")
    result = case.ws.describe("fixture:capture.pcap.gz")
    assert not result["details"]["read_supported"]
    assert result["details"]["row_count"] is None
    assert result["details"]["reason"] == "USE_EXISTING_OWNER_DECODER"
    with pytest.raises(WorkspaceError):
        case.ws.read("fixture:capture.pcap.gz")


def test_host_config_loads_only_explicit_roots_and_relative_registry(case):
    workspace = load_workspace_config(case.config, source_revision="verified-source")
    assert tuple(workspace.roots) == ("fixture",)
    assert workspace.registry_path == case.registry
    assert workspace.describe("fixture:prices.parquet")["implementation_revision"] == "verified-source"


@pytest.mark.parametrize("mutation", [
    lambda p: p.update(extra="not permitted"),
    lambda p: p.update(schema_version="unknown"),
    lambda p: p.update(roots="not a list"),
    lambda p: p["roots"][0].update(extra="not permitted"),
    lambda p: p["roots"][0].update(alias="Uppercase"),
    lambda p: p["roots"][0].update(path="relative/data"),
    lambda p: p["roots"][0].update(evidence_kind="PROVEN_LIVE"),
    lambda p: p["roots"][0].update(required_mount="relative-volume"),
    lambda p: p["roots"][0].update(note=123),
])
def test_host_config_rejects_unknown_fields_and_unsafe_bindings(case, mutation):
    payload = json.loads(json.dumps(case.payload))
    mutation(payload)
    case.config.write_text(json.dumps(payload))
    with pytest.raises(ValueError):
        load_workspace_config(case.config)


# --- U03 (DATA-OS-COMPLETION): bounded web read under a declared view contract -------------------------------
from lib.dataos import web_workspace as u03_web_workspace  # noqa: E402
from lib.dataos.read_contract import READ_CONTRACT_VERSION  # noqa: E402

U03_CUTOFF = "2026-10-07T00:00:00+00:00"
_U03_DROP = object()


def _u03_contract(**changes):
    contract = {"purpose": "U03 synthetic close read",
                "identity": {"security_id": "SEC-AMD", "listing_id": "US-XNAS-AMD"},
                "field_units": {"close": "USD"}, "adjustment_reference": {"basis": "raw"},
                "coverage": "synthetic fixture rows local to this suite"}
    for key, value in changes.items():
        if value is _U03_DROP:
            contract.pop(key, None)
        else:
            contract[key] = value
    return contract


def _u03_view(**changes):
    view = {"mode": "CURRENT", "contract": _u03_contract()}
    for key, value in changes.items():
        if value is _U03_DROP:
            view.pop(key, None)
        else:
            view[key] = value
    return view


def _u03_read(ws, view=None, **changes):
    kwargs = {"columns": ["Date", "close"], "limit": 10}
    kwargs.update(changes)
    return ws.read_view("fixture:prices.parquet", view=_u03_view() if view is None else view, **kwargs)


def _u03_refused_before_open(monkeypatch):
    def _never(*args, **kwargs):
        raise AssertionError("U03: the source was opened before the view was refused")
    monkeypatch.setattr(DataWorkspace, "_file", _never)


def _u03_ws_with_basis(case, basis):
    doc = yaml.safe_load(case.registry.read_text())
    doc["datasets"][0]["basis"] = basis
    path = case.tmp / f"registry-u03-{basis}.yml"
    path.write_text(yaml.safe_dump(doc))
    return DataWorkspace(
        (RootBinding("fixture", case.root, "research_capture", "Synthetic fixtures; no admission"),),
        path, source_revision="c" * 40)


def test_U03_legacy_read_is_unchanged_and_carries_no_view(case):
    legacy = case.ws.read("fixture:prices.parquet", columns=["Date", "close"], limit=10)
    assert legacy["action"] == "read"
    assert "view" not in legacy and "view_digest_sha256" not in legacy
    assert legacy["price_basis"] == "PRESERVED_AS_STORED_NOT_REBASED"


def test_U03_current_view_read_is_repeatable_and_binds_evidence(case):
    legacy = case.ws.read("fixture:prices.parquet", columns=["Date", "close"], limit=10)
    one, two = _u03_read(case.ws), _u03_read(case.ws)
    assert len(one["view_digest_sha256"]) == 64
    assert one["view_digest_sha256"] == two["view_digest_sha256"]
    assert one["action"] == "read_view"
    assert one["result"] == legacy["result"]
    assert one["query_receipt_sha256"] == legacy["query_receipt_sha256"]
    view = one["view"]
    assert view["mode"] == "CURRENT" and view["label"] == "current"
    assert view["generation"] == legacy["source"]["file_version"]
    assert view["generation_basis"] == "statv1_file_version_not_a_producer_generation"
    assert view["evidence"] == {"source_revision": "c" * 40, "file_version": legacy["source"]["file_version"],
                                "identity_generation_id": None, "action_revision_set_id": None,
                                "receipt_sha256s": []}
    assert "DATASET_NOT_DECLARED" in view["binding_gaps"]
    assert "IDENTITY_GENERATION_UNBOUND" in view["binding_gaps"]
    assert view["qualification"] == "VIEW_DECLARED_NOT_PRODUCTION_QUALIFIED"
    assert view["dataset"] is None
    assert view["read_contract_version"] == READ_CONTRACT_VERSION
    assert view["contract"]["identity"] == {"security_id": "SEC-AMD", "listing_id": "US-XNAS-AMD"}
    assert one["price_basis"] == "PRESERVED_AS_STORED_NOT_REBASED"
    assert one["implementation_revision"] == "c" * 40
    json.dumps(one, allow_nan=False)


def test_U03_the_view_digest_moves_with_the_declared_view_and_the_query(case):
    base = _u03_read(case.ws)["view_digest_sha256"]
    other_view = _u03_read(case.ws, _u03_view(contract=_u03_contract(purpose="U03 another declared purpose")))
    other_query = _u03_read(case.ws, limit=2)
    assert len({base, other_view["view_digest_sha256"], other_query["view_digest_sha256"]}) == 3


def test_U03_statv1_stays_a_file_version_not_a_content_hash(case):
    one = _u03_read(case.ws)
    assert one["source"]["file_version"].startswith("statv1:")
    assert one["source"]["file_version_basis"] == "device_inode_size_mtime_ctime_not_content_hash"
    assert one["source"]["content_sha256"] is None
    assert "CONTENT_HASH_NOT_COMPUTED" in one["view"]["binding_gaps"]


def test_U03_a_matching_generation_pin_serves_the_same_read(case):
    unpinned = _u03_read(case.ws)
    pinned = _u03_read(case.ws, _u03_view(generation=unpinned["view"]["generation"]))
    assert pinned["view_digest_sha256"] == unpinned["view_digest_sha256"]
    assert pinned["result"] == unpinned["result"]


def test_U03_a_missing_old_generation_is_GENERATION_UNAVAILABLE_never_the_current_file(case):
    old = _u03_read(case.ws)["view"]["generation"]
    os.utime(case.prices, ns=(1_800_000_000_000_000_000,) * 2)
    new = _u03_read(case.ws)["view"]["generation"]
    assert new != old
    for pin in (old, "statv1:" + "0" * 64):
        with pytest.raises(WorkspaceError) as error:
            _u03_read(case.ws, _u03_view(generation=pin))
        assert error.value.code == "GENERATION_UNAVAILABLE"


@pytest.mark.parametrize("changes,code", [
    ({"mode": "RECONSTRUCT", "cutoff": U03_CUTOFF, "clock": "published_at"}, "VIEW_REFUSED_UNBOUND_DEPENDENCY"),
    ({"mode": "RECONSTRUCT", "cutoff": U03_CUTOFF, "clock": "ingested_at"}, "VIEW_REFUSED_UNBOUND_DEPENDENCY"),
    ({"mode": "RECONSTRUCT", "cutoff": U03_CUTOFF, "clock": "event_at"}, "VIEW_REFUSED_CLOCK_NOT_DECLARED"),
    ({"mode": "RECONSTRUCT", "cutoff": U03_CUTOFF, "clock": "bogus"}, "VIEW_REFUSED_UNKNOWN_CLOCK"),
    ({"mode": "REPLAY", "output_id": "out-1"}, "VIEW_REFUSED_NO_RETAINED_OUTPUT"),
])
def test_U03_unprovable_modes_refuse_before_the_source_is_opened(case, monkeypatch, changes, code):
    _u03_refused_before_open(monkeypatch)
    with pytest.raises(WorkspaceError) as error:
        _u03_read(case.ws, _u03_view(**changes))
    assert error.value.code == code


@pytest.mark.parametrize("revision", [None, "c" * 39, "C" * 40, "g" * 40])
def test_U03_current_without_a_full_lowercase_revision_refuses_MISSING_CURRENT_EVIDENCE(case, monkeypatch, revision):
    ws = DataWorkspace(
        (RootBinding("fixture", case.root, "research_capture", "Synthetic fixtures; no admission"),),
        case.registry, source_revision=revision)
    _u03_refused_before_open(monkeypatch)
    with pytest.raises(WorkspaceError) as error:
        _u03_read(ws)
    assert error.value.code == "VIEW_REFUSED_MISSING_CURRENT_EVIDENCE"


@pytest.mark.parametrize("view", [
    None, [], "CURRENT",
    _u03_view(contract=_U03_DROP),
    _u03_view(extra="x"),
    _u03_view(contract=[]),
    _u03_view(mode=1),
    _u03_view(mode="LIVE"),
    _u03_view(contract=_u03_contract(coverage=_U03_DROP)),
    _u03_view(contract=_u03_contract(extra="x")),
    _u03_view(contract=_u03_contract(identity={"security_id": "SEC-AMD"})),
    _u03_view(contract=_u03_contract(identity={"security_id": "SEC-AMD", "listing_id": 7})),
    _u03_view(contract=_u03_contract(field_units=["close"])),
    _u03_view(contract=_u03_contract(refusal_reasons="STALE")),
    _u03_view(contract=_u03_contract(purpose="x" * 201)),
    _u03_view(cutoff=U03_CUTOFF),
    _u03_view(output_id="out-1"),
    _u03_view(generation="sha256:" + "0" * 64),
    _u03_view(generation=7),
    _u03_view(mode="RECONSTRUCT", cutoff="2026-10-07T00:00:00", clock="published_at"),
    _u03_view(mode="RECONSTRUCT", clock="published_at"),
    _u03_view(mode="REPLAY"),
    _u03_view(contract=_u03_contract(identity={"security_id": "", "listing_id": "x"})),
])
def test_U03_a_malformed_view_is_INVALID_VIEW_before_open(case, monkeypatch, view):
    _u03_refused_before_open(monkeypatch)
    with pytest.raises(WorkspaceError) as error:
        case.ws.read_view("fixture:prices.parquet", view=view, columns=["Date", "close"], limit=10)
    assert error.value.code == "INVALID_VIEW"


def test_U03_a_generation_that_conflicts_with_expected_version_is_INVALID_VIEW(case, monkeypatch):
    current = _u03_read(case.ws)["view"]["generation"]
    _u03_refused_before_open(monkeypatch)
    with pytest.raises(WorkspaceError) as error:
        _u03_read(case.ws, _u03_view(generation=current), expected_version="statv1:" + "0" * 64)
    assert error.value.code == "INVALID_VIEW"


@pytest.mark.parametrize("ref,code", [
    ("fixture:../outside.csv", "PATH_REFUSED"),
    ("elsewhere:prices.parquet", "ROOT_NOT_BOUND"),
])
def test_U03_a_view_never_widens_roots_or_paths(case, ref, code):
    with pytest.raises(WorkspaceError) as legacy:
        case.ws.read(ref)
    with pytest.raises(WorkspaceError) as viewed:
        case.ws.read_view(ref, view=_u03_view())
    assert legacy.value.code == code
    assert viewed.value.code == legacy.value.code


def test_U03_the_response_cap_is_kept_not_widened(case, monkeypatch):
    assert u03_web_workspace.MAX_RESPONSE_BYTES == 131072
    legacy = case.ws.read("fixture:prices.parquet", columns=["Date", "close"], limit=10)
    size = len(json.dumps(legacy, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))
    monkeypatch.setattr(u03_web_workspace, "MAX_RESPONSE_BYTES", size + 64)
    case.ws.read("fixture:prices.parquet", columns=["Date", "close"], limit=10)
    with pytest.raises(WorkspaceError) as error:
        _u03_read(case.ws)
    assert error.value.code == "RESULT_TOO_LARGE_REDUCE_COLUMNS_OR_LIMIT"


def test_U03_a_declared_dataset_is_named_but_its_storage_binding_is_not_verified(case):
    out = _u03_read(case.ws, _u03_view(dataset_id="fixture.prices"))
    assert out["view"]["dataset"] == {"dataset_id": "fixture.prices", "version": "1.0.0", "status": "PROPOSED",
                                      "registry_basis": None, "storage_binding": "DECLARED_NOT_VERIFIED"}
    assert "STORAGE_BINDING_DECLARED_NOT_VERIFIED" in out["view"]["binding_gaps"]
    assert "DATASET_NOT_DECLARED" not in out["view"]["binding_gaps"]


def test_U03_an_unregistered_dataset_is_refused_before_open(case, monkeypatch):
    _u03_refused_before_open(monkeypatch)
    with pytest.raises(WorkspaceError) as error:
        _u03_read(case.ws, _u03_view(dataset_id="fixture.unknown"))
    assert error.value.code == "DATASET_NOT_REGISTERED"


def test_U03_a_declared_basis_that_matches_the_registry_row_is_served(case):
    ws = _u03_ws_with_basis(case, "tradj")
    view = _u03_view(dataset_id="fixture.prices", contract=_u03_contract(adjustment_reference={"basis": "tradj"}))
    out = _u03_read(ws, view)
    assert out["view"]["dataset"]["registry_basis"] == "tradj"
    assert out["view"]["contract"]["adjustment_reference"] == {"basis": "tradj"}


def test_U03_an_undeclared_basis_is_reported_not_guessed(case):
    ws = _u03_ws_with_basis(case, "tradj")
    view = _u03_view(dataset_id="fixture.prices",
                     contract=_u03_contract(adjustment_reference={"vendor": "fixture"}))
    out = _u03_read(ws, view)
    assert out["view"]["dataset"]["registry_basis"] == "tradj"
    assert out["view"]["contract"]["adjustment_reference"] == {"vendor": "fixture"}


def test_U03_a_declared_basis_that_disagrees_with_the_registry_row_refuses_BASIS_CHANGED(case, monkeypatch):
    ws = _u03_ws_with_basis(case, "tradj")
    _u03_refused_before_open(monkeypatch)
    with pytest.raises(WorkspaceError) as error:
        _u03_read(ws, _u03_view(dataset_id="fixture.prices"))
    assert error.value.code == "VIEW_REFUSED_BASIS_CHANGED"
