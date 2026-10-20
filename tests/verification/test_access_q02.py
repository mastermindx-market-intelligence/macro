"""Q02 adversarial access at the REAL handler boundary (DATA-OS-COMPLETION).

Every test drives a real entrypoint, never a dataclass in isolation:

  E1a  the CLI transport the Studio host runs: ``scripts/data_workspace.py
       --config <bindings.json>``, one JSON payload on stdin -> one JSON result
       on stdout; rc 2 = typed refusal envelope, never a traceback or a path.
  E1b  the same composition in-process: ``lib.dataos.web_workspace.
       load_workspace_config(cfg)`` then ``lib.dataos.web_api.dispatch(...)``.
  E2   the read contract: ``lib.dataos.read_contract`` (current / reconstruct /
       replay / select_generation / account_coverage).
  E3   the basket reader: ``engine.basket_membership_pit.members_asof`` and
       ``coverage``, with the data directory redirected to ``tmp_path`` using
       the house fixture idiom from ``tests/test_basket_membership_pit.py``.

All fixtures are synthetic licensed-shaped values written only under
``tmp_path``; no network, no real market data, no secret probes.  This is a
VERIFICATION lane: production code is never edited here, and a defect is pinned
as a strict-xfail test that asserts the CORRECT behaviour.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from fractions import Fraction
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from engine import basket_membership_pit as pit  # noqa: E402
from lib import config  # noqa: E402
from lib.dataos import web_api, web_workspace  # noqa: E402
from lib.dataos.nulls import MissingReason  # noqa: E402
from lib.dataos.read_contract import (  # noqa: E402
    CurrentEvidence,
    Dependency,
    Disposition,
    GenerationRef,
    MemberDisposition,
    ReadMode,
    ReadRefusal,
    ReadRequest,
    RetainedOutput,
    SourceSegment,
    ViewContract,
    account_coverage,
    current,
    reconstruct,
    replay,
    select_generation,
)
from lib.dataos.temporal import TemporalProfile  # noqa: E402

REGISTRY = REPO / "config" / "dataset_registry.yml"

CSV_HEADER = "date,symbol,close"
CSV_A = (
    "2026-01-02,SYNTH1,101.25\n"
    "2026-01-03,SYNTH2,102.50\n"
    "2026-01-04,SYNTH3,103.75\n"
)
CSV_B = "2026-01-05,SYNTHB,104.00\n"
CSV_A_BYTES = (CSV_HEADER + "\n" + CSV_A).encode("utf-8")
CSV_B_BYTES = (CSV_HEADER + "\n" + CSV_B).encode("utf-8")
EXPECTED_ROWS = [
    {"date": "2026-01-02", "symbol": "SYNTH1", "close": "101.25"},
    {"date": "2026-01-03", "symbol": "SYNTH2", "close": "102.50"},
    {"date": "2026-01-04", "symbol": "SYNTH3", "close": "103.75"},
]
LEAK_MARKERS = ("SYNTH1", "101.25", "SYNTH2", "102.50", "SYNTH3", "103.75")
PRIVATE_TOKEN = "Q02-PRIVATE-7f3a"
TRANSPORTS = ["cli", "dispatch"]

HEX64 = "9f" * 32
CODE_VERSION = "5d" * 20


# ---------------------------------------------------------------------------
# E1 helpers (the real CLI process and the in-process composition)
# ---------------------------------------------------------------------------

def _write_cfg(path: Path, roots) -> Path:
    """A host-binding JSON exactly like the host writes (schema pinned)."""
    path.write_text(json.dumps({
        "schema_version": "mastermind.data_workspace_bindings/v1",
        "registry_path": str(REGISTRY),
        "roots": [{"alias": alias, "path": str(root)} for alias, root in roots],
    }), encoding="utf-8")
    return path


def _root_with_csv(tmp_path: Path, *, name: str = "root",
                   filename: str = "prices.csv", content: bytes = CSV_A_BYTES) -> Path:
    root = tmp_path / name
    root.mkdir(parents=True, exist_ok=True)
    (root / filename).write_bytes(content)
    return root


def _cli(cfg: Path, payload, cwd: Path, *, markers=()):
    """E1a: the real CLI transport. ("ok", response) or ("refused", code).

    L1 leak discipline is enforced on every call: no traceback, no host path,
    and on a refusal exactly ONE JSON object whose keys are a subset of the
    documented error envelope, carrying no fixture value.
    """
    raw = payload if isinstance(payload, (bytes, bytearray)) else json.dumps(payload).encode("utf-8")
    env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "PYTHONDONTWRITEBYTECODE": "1"}
    proc = subprocess.run(
        [sys.executable, "-B", str(REPO / "scripts" / "data_workspace.py"),
         "--config", str(cfg)],
        input=bytes(raw), capture_output=True, timeout=60, cwd=cwd, env=env)
    out = proc.stdout.decode("utf-8", "replace")
    err = proc.stderr.decode("utf-8", "replace")
    assert "Traceback" not in out + err, err
    assert str(cwd) not in out and str(cwd) not in err, (out, err)
    if proc.returncode == 0:
        return "ok", json.loads(out)
    assert proc.returncode == 2, (proc.returncode, out, err)
    for marker in markers:
        assert marker not in out and marker not in err, (marker, out, err)
    refusal = json.loads(out)  # exactly one JSON object, nothing after it
    assert set(refusal) <= {"schema_version", "error", "error_type"}, refusal
    assert refusal["schema_version"] == "mastermind.data_workspace/v1"
    assert isinstance(refusal["error"], str) and refusal["error"]
    return "refused", refusal["error"]


def _dispatch(cfg: Path, payload):
    """E1b: the same composition in-process, one fresh workspace per host config."""
    workspace = web_workspace.load_workspace_config(cfg)
    try:
        return "ok", web_api.dispatch(workspace, payload, config_path=cfg)
    except web_workspace.WorkspaceError as exc:
        return "refused", exc.code


def _send(transport: str, cfg: Path, payload, cwd: Path, *, markers=()):
    if transport == "cli":
        return _cli(cfg, payload, cwd, markers=markers)
    return _dispatch(cfg, payload)


def _ok(transport, cfg, payload, cwd, *, markers=()):
    state, body = _send(transport, cfg, payload, cwd, markers=markers)
    assert state == "ok", body
    return body


def _refused(transport, cfg, payload, cwd, *, code: str, markers=()):
    state, got = _send(transport, cfg, payload, cwd, markers=markers)
    assert state == "refused", got
    assert got == code, (got, code)
    return got


READ_PRICES = {"action": "read", "ref": "q02:prices.csv"}


# ---------------------------------------------------------------------------
# E2 helpers (the read contract)
# ---------------------------------------------------------------------------

def _contract() -> ViewContract:
    return ViewContract(
        purpose="q02 adversarial access verification",
        identity={"security_id": "SYNTH-SEC-1", "listing_id": "SYNTH-LIST-1"},
        field_units={"close": "synthetic_currency_units"},
        adjustment_reference={"basis": "synthetic_unadjusted"},
        coverage="synthetic window 2026-01-01..2026-12-31",
    )


def _evidence(generation_id: str) -> CurrentEvidence:
    return CurrentEvidence(
        receipt_sha256s=(HEX64,), identity_generation_id=generation_id,
        action_revision_set_id="rev-set-q02", code_version=CODE_VERSION)


def _gen_row(generation_id: str, close: str) -> dict:
    return {"symbol": "SYNTH1", "close": close, "generation_id": generation_id,
            "published_at": "2026-01-15T00:00:00+00:00"}


def _ledger_aba() -> tuple:
    """g1 (content A) <- g2 (B) <- g3 (A's bytes re-published)."""
    return (
        GenerationRef("g1", published_at="2026-01-01T00:00:00+00:00"),
        GenerationRef("g2", published_at="2026-02-01T00:00:00+00:00", supersedes="g1"),
        GenerationRef("g3", published_at="2026-03-01T00:00:00+00:00", supersedes="g2"),
    )


def _retained(payload: bytes, *, output_id: str = "out-X",
              sha256: str | None = None) -> RetainedOutput:
    return RetainedOutput(output_id=output_id, payload=payload,
                          sha256=sha256 or hashlib.sha256(payload).hexdigest(),
                          publishing_receipt_sha256=HEX64)


# ---------------------------------------------------------------------------
# E3 helpers (the basket reader; house data-dir redirect idiom)
# ---------------------------------------------------------------------------

THS = pit.SUITE_THS


def _membership_doc(baskets: dict) -> dict:
    return {"version": 1, "seed_date": "2021-06-15", "curated": False,
            "baskets": {bid: {"name": bid, "name_zh": bid, "category": "theme",
                              "members": members}
                        for bid, members in baskets.items()}}


def _member(ticker: str, added: str = "2021-06-15", removed: str | None = None) -> dict:
    return {"ticker": ticker, "added": added, "removed": removed,
            "name_zh": f"zh-{ticker}", "rationale": "q02-synthetic"}


def _write_membership(root: Path, doc: dict) -> None:
    p = root / THS / "membership.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")


@pytest.fixture
def data_root(tmp_path, monkeypatch):
    """Point config.data_dir() at a scratch tree (the house fixture idiom)."""
    monkeypatch.setattr(config, "data_dir", lambda: tmp_path)
    return tmp_path


def _seed_suite(data_root: Path, baskets: dict, asof: str = "2026-07-01") -> None:
    _write_membership(data_root, _membership_doc(baskets))
    stamped = pit.append_snapshot(THS, asof=asof, lane="asia")
    assert stamped["written"], stamped


# ===========================================================================
# Q02.01 — the permitted path succeeds; mismatched / revoked / old variants
#          refuse at the actual user boundary
# ===========================================================================

@pytest.mark.parametrize("transport", TRANSPORTS)
def test_a1_permitted_read_succeeds(transport, tmp_path):
    """ENTRYPOINT: E1a+E1b scripts/data_workspace.py + lib.dataos.web_api.dispatch

    A permitted end-to-end read of a small synthetic CSV succeeds at the real
    boundary, with a stat-identity file version (statv1:, 71 chars).
    """
    root = _root_with_csv(tmp_path)
    cfg = _write_cfg(tmp_path / "bindings.json", [("q02", root)])
    resp = _ok(transport, cfg, READ_PRICES, tmp_path, markers=LEAK_MARKERS)
    assert resp["action"] == "read"
    assert resp["source"]["ref"] == "q02:prices.csv"
    assert resp["source"]["root_alias"] == "q02"
    assert resp["result"]["rows"] == EXPECTED_ROWS
    version = resp["source"]["file_version"]
    assert version.startswith("statv1:")
    assert len(version) == 71


def test_a1_both_transports_return_the_same_rows(tmp_path):
    """ENTRYPOINT: E1a+E1b scripts/data_workspace.py + lib.dataos.web_api.dispatch

    The CLI process and the in-process dispatcher observe the same file: same
    rows, same stat version — one adapter, two lawful transports.
    """
    root = _root_with_csv(tmp_path)
    cfg = _write_cfg(tmp_path / "bindings.json", [("q02", root)])
    cli_resp = _ok("cli", cfg, READ_PRICES, tmp_path)
    dispatch_resp = _ok("dispatch", cfg, READ_PRICES, tmp_path)
    assert cli_resp["result"] == dispatch_resp["result"]
    assert cli_resp["source"]["file_version"] == dispatch_resp["source"]["file_version"]


@pytest.mark.parametrize("transport", TRANSPORTS)
def test_a1_describe_succeeds(transport, tmp_path):
    """ENTRYPOINT: E1a+E1b scripts/data_workspace.py + lib.dataos.web_api.dispatch"""
    root = _root_with_csv(tmp_path)
    cfg = _write_cfg(tmp_path / "bindings.json", [("q02", root)])
    resp = _ok(transport, cfg, {"action": "describe", "ref": "q02:prices.csv"},
               tmp_path, markers=LEAK_MARKERS)
    assert resp["action"] == "describe_file"
    assert resp["details"]["row_count"] == 3
    assert resp["details"]["columns"] == ["date", "symbol", "close"]


@pytest.mark.parametrize("transport", TRANSPORTS)
def test_a2_expected_version_of_another_file_refused(transport, tmp_path):
    """ENTRYPOINT: E1a+E1b scripts/data_workspace.py + lib.dataos.web_api.dispatch

    A read pinned to ANOTHER file's valid version is refused
    SOURCE_VERSION_MISMATCH and carries no fixture row value.
    """
    root = _root_with_csv(tmp_path, filename="other.csv",
                          content=(CSV_HEADER + "\n2026-02-02,OTHER1,201.25\n").encode("utf-8"))
    _root_with_csv(tmp_path)
    cfg = _write_cfg(tmp_path / "bindings.json", [("q02", root)])
    other_version = _ok(transport, cfg, {"action": "read", "ref": "q02:other.csv"},
                        tmp_path)["source"]["file_version"]
    _refused(transport, cfg, {**READ_PRICES, "expected_version": other_version},
             tmp_path, code="SOURCE_VERSION_MISMATCH",
             markers=LEAK_MARKERS + ("OTHER1", "201.25"))


@pytest.mark.parametrize("transport", TRANSPORTS)
def test_a3_revoked_alias_refused(transport, tmp_path):
    """ENTRYPOINT: E1a+E1b scripts/data_workspace.py + lib.dataos.web_api.dispatch

    Revocation is a host act: the identical payload that succeeded is refused
    ROOT_NOT_BOUND once the host config no longer binds the alias.
    """
    root = _root_with_csv(tmp_path)
    cfg = _write_cfg(tmp_path / "bindings.json", [("q02", root)])
    _ok(transport, cfg, READ_PRICES, tmp_path)
    other = tmp_path / "other_root"
    other.mkdir()
    (other / "x.csv").write_bytes(CSV_A_BYTES)
    _write_cfg(cfg, [("other", other)])  # host rewrites the binding file
    _refused(transport, cfg, READ_PRICES, tmp_path, code="ROOT_NOT_BOUND",
             markers=LEAK_MARKERS)


@pytest.mark.parametrize("transport", TRANSPORTS)
def test_a4_root_swapped_under_same_path(transport, tmp_path):
    """ENTRYPOINT: E1a+E1b scripts/data_workspace.py + lib.dataos.web_api.dispatch

    A byte-identical file under a NEW directory at the same path is a different
    source: the old version pin refuses, the unpinned read reports a new one.
    """
    root = _root_with_csv(tmp_path)
    cfg = _write_cfg(tmp_path / "bindings.json", [("q02", root)])
    first = _ok(transport, cfg, READ_PRICES, tmp_path)
    v1 = first["source"]["file_version"]
    payload = (root / "prices.csv").read_bytes()
    os.rename(root, tmp_path / "root_away")
    root.mkdir()
    (root / "prices.csv").write_bytes(payload)  # byte-identical, new inode
    _refused(transport, cfg, {**READ_PRICES, "expected_version": v1}, tmp_path,
             code="SOURCE_VERSION_MISMATCH", markers=LEAK_MARKERS)
    second = _ok(transport, cfg, READ_PRICES, tmp_path)
    assert second["source"]["file_version"] != v1
    assert second["result"]["rows"] == EXPECTED_ROWS  # same bytes, new identity


def test_a5_pinned_generation_no_longer_selectable():
    """ENTRYPOINT: E2 lib.dataos.read_contract.select_generation"""
    g1 = GenerationRef("g1", published_at="2026-01-01T00:00:00+00:00")
    g2 = GenerationRef("g2", published_at="2026-02-01T00:00:00+00:00", supersedes="g1")
    winner = select_generation((g1, g2), cutoff="2026-03-01T00:00:00+00:00",
                               clock="published_at")
    assert winner.generation_id == "g2"
    with pytest.raises(ReadRefusal) as raised:
        select_generation((g1, g2), cutoff="2026-03-01T00:00:00+00:00",
                          clock="published_at", pinned_generation_id="g1")
    assert raised.value.code == "STALE_GENERATION"


def test_a5_current_evidence_names_superseded_generation():
    """ENTRYPOINT: E2 lib.dataos.read_contract.current"""
    g1 = GenerationRef("g1", published_at="2026-01-01T00:00:00+00:00")
    g2 = GenerationRef("g2", published_at="2026-02-01T00:00:00+00:00", supersedes="g1")
    dep = Dependency("dep", profile=TemporalProfile.EVENT,
                     rows=(_gen_row("g1", "101.25"), _gen_row("g2", "202.50")),
                     generations=(g1, g2))
    with pytest.raises(ReadRefusal) as raised:
        current(ReadRequest(mode=ReadMode.CURRENT, contract=_contract()),
                {"dep": dep}, evidence=_evidence("g1"))
    assert raised.value.code == "STALE_GENERATION"


def test_a5_all_generations_superseded_refuses():
    """ENTRYPOINT: E2 lib.dataos.read_contract.current"""
    g1 = GenerationRef("g1", published_at="2026-01-01T00:00:00+00:00", supersedes="g1")
    dep = Dependency("dep", profile=TemporalProfile.EVENT,
                     rows=(_gen_row("g1", "101.25"),), generations=(g1,))
    with pytest.raises(ReadRefusal) as raised:
        current(ReadRequest(mode=ReadMode.CURRENT, contract=_contract()),
                {"dep": dep}, evidence=_evidence("g1"))
    assert raised.value.code == "UNBOUND_DEPENDENCY"


def test_a6_unknown_basket_is_empty_and_labelled(data_root):
    """ENTRYPOINT: E3 engine.basket_membership_pit.members_asof"""
    _seed_suite(data_root, {"ths_a": [_member("SYNTHA.SZ")],
                            "ths_b": [_member("SYNTHB.SZ")]})
    got = pit.members_asof("ths_missing", "2026-07-01", suite=THS)
    assert got["basis"] == "unknown_basket"
    assert got["members"] == []
    assert got["pit"] is False
    assert got["note"] == "no basket-scoped observation"
    # Isolation: a known basket still answers its own members, never a peer's.
    known = pit.members_asof("ths_a", "2026-07-01", suite=THS)
    assert known["members"] == ["SYNTHA.SZ"]
    assert known["pit"] is True


# ===========================================================================
# Q02.02 — receipt-only refusals, disappeared artifacts and A->B->A changes
#          cannot silently resurrect invalid current evidence
# ===========================================================================

@pytest.mark.parametrize("case", ["receipt_only", "tampered", "intact"])
def test_b1_replay_retained_output_refusals(case):
    """ENTRYPOINT: E2 lib.dataos.read_contract.replay

    receipt-only -> NO_RETAINED_OUTPUT; one altered payload byte after the sha
    was taken -> RETAINED_DIGEST_MISMATCH; neither exposes values.
    """
    payload = b'{"rows":[{"symbol":"SYNTH1","close":"101.25"}]}'
    digest = hashlib.sha256(payload).hexdigest()
    if case == "receipt_only":
        retained = RetainedOutput("out-X", None, digest, HEX64)  # receipt only
        with pytest.raises(ReadRefusal) as raised:
            replay(ReadRequest(mode=ReadMode.REPLAY, contract=_contract(),
                               output_id="out-X"), retained)
        assert raised.value.code == "NO_RETAINED_OUTPUT"
    elif case == "tampered":
        broken = payload[:-1] + bytes([payload[-1] ^ 1])
        retained = RetainedOutput("out-X", broken, digest, HEX64)
        with pytest.raises(ReadRefusal) as raised:
            replay(ReadRequest(mode=ReadMode.REPLAY, contract=_contract(),
                               output_id="out-X"), retained)
        assert raised.value.code == "RETAINED_DIGEST_MISMATCH"
    else:  # the intact control: replay serves the exact retained bytes
        result = replay(ReadRequest(mode=ReadMode.REPLAY, contract=_contract(),
                                    output_id="out-X"), _retained(payload))
        assert result.payload == payload
        assert dict(result.values) == {}


@pytest.mark.parametrize("transport", TRANSPORTS)
def test_b2_disappeared_artifact_no_resurrection(transport, tmp_path):
    """ENTRYPOINT: E1a+E1b scripts/data_workspace.py + lib.dataos.web_api.dispatch

    Deleted -> SOURCE_NOT_FOUND; a byte-identical recreation is a NEW source,
    so the old version pin still refuses.
    """
    root = _root_with_csv(tmp_path)
    cfg = _write_cfg(tmp_path / "bindings.json", [("q02", root)])
    v1 = _ok(transport, cfg, READ_PRICES, tmp_path)["source"]["file_version"]
    (root / "prices.csv").unlink()
    _refused(transport, cfg, READ_PRICES, tmp_path, code="SOURCE_NOT_FOUND",
             markers=LEAK_MARKERS)
    (root / "prices.csv").write_bytes(CSV_A_BYTES)  # byte-identical recreation
    _refused(transport, cfg, {**READ_PRICES, "expected_version": v1}, tmp_path,
             code="SOURCE_VERSION_MISMATCH", markers=LEAK_MARKERS)


@pytest.mark.parametrize("transport", TRANSPORTS)
def test_b3_aba_in_place_cannot_restore_version(transport, tmp_path):
    """ENTRYPOINT: E1a+E1b scripts/data_workspace.py + lib.dataos.web_api.dispatch

    A->B->A with the original mtime restored still changes the version:
    ``_version`` hashes st_ctime_ns too, which user space cannot set.
    """
    root = _root_with_csv(tmp_path)
    cfg = _write_cfg(tmp_path / "bindings.json", [("q02", root)])
    path = root / "prices.csv"
    v_a = _ok(transport, cfg, READ_PRICES, tmp_path)["source"]["file_version"]
    stamp = path.stat()
    original = (stamp.st_atime_ns, stamp.st_mtime_ns)
    path.write_bytes(CSV_B_BYTES)   # B
    path.write_bytes(CSV_A_BYTES)   # back to A, byte-identical
    os.utime(path, ns=original)     # restore A's original atime/mtime
    _refused(transport, cfg, {**READ_PRICES, "expected_version": v_a}, tmp_path,
             code="SOURCE_VERSION_MISMATCH", markers=LEAK_MARKERS)
    fresh = _ok(transport, cfg, READ_PRICES, tmp_path)
    assert fresh["source"]["file_version"] != v_a


def test_b4_select_generation_never_resurrects_g1():
    """ENTRYPOINT: E2 lib.dataos.read_contract.select_generation"""
    winner = select_generation(_ledger_aba(), cutoff="2026-04-01T00:00:00+00:00",
                               clock="published_at")
    assert winner.generation_id == "g3"
    with pytest.raises(ReadRefusal) as raised:
        select_generation(_ledger_aba(), cutoff="2026-04-01T00:00:00+00:00",
                          clock="published_at", pinned_generation_id="g1")
    assert raised.value.code == "STALE_GENERATION"


def test_b4_reconstruct_binds_g3_not_g1():
    """ENTRYPOINT: E2 lib.dataos.read_contract.reconstruct"""
    rows = (_gen_row("g1", "101.25"), _gen_row("g2", "202.50"), _gen_row("g3", "101.25"))
    request = ReadRequest(mode=ReadMode.RECONSTRUCT, contract=_contract(),
                          cutoff="2026-04-01T00:00:00+00:00", clock="published_at")
    dep = Dependency("dep", profile=TemporalProfile.EVENT, rows=rows,
                     generations=_ledger_aba())
    result = reconstruct(request, {"dep": dep}, required=("dep",),
                         code_version=CODE_VERSION)
    assert result.evidence["dependency_generation_ids"]["dep"] == "g3"
    assert [row["close"] for row in result.values["dep"]] == ["101.25"]
    assert all(row["generation_id"] == "g3" for row in result.values["dep"])
    pinned = Dependency("dep", profile=TemporalProfile.EVENT, rows=rows,
                        generations=_ledger_aba(), pinned_generation_id="g1")
    with pytest.raises(ReadRefusal) as raised:
        reconstruct(request, {"dep": pinned}, required=("dep",),
                    code_version=CODE_VERSION)
    assert raised.value.code == "STALE_GENERATION"


def test_b5_history_removed_falls_back_flagged(data_root):
    """ENTRYPOINT: E3 engine.basket_membership_pit.members_asof"""
    _seed_suite(data_root, {"ths_a": [_member("SYNTHA.SZ"), _member("SYNTHC.SZ")]})
    inside = pit.members_asof("ths_a", "2026-07-02", suite=THS)
    assert inside["pit"] is True
    pit.history_path(THS).unlink()
    got = pit.members_asof("ths_a", "2026-07-01", suite=THS)  # inside former window
    assert got["pit"] is False
    assert got["basis"] == "current_membership"
    assert got["snapshot_date"] is None
    assert got["source_shape"] is None
    assert got["members"] == ["SYNTHA.SZ", "SYNTHC.SZ"]
    assert got["note"] == ("no PIT history yet — current membership applied "
                           "backward (look-ahead basis)")
    assert pit.coverage(THS) == {"suite": THS, "snapshots": 0, "first": None,
                                 "last": None, "rows": 0}


def test_b5_history_garbage_observed_state(data_root):
    """ENTRYPOINT: E3 engine.basket_membership_pit.members_asof

    FIXED (Q02-F1): the garbage bytes are now answered as
    basis="membership_unreadable" with no members — corruption is never
    answered as absence or as an observation of CURRENT membership.
    """
    _seed_suite(data_root, {"ths_a": [_member("SYNTHA.SZ")]})
    pit.history_path(THS).write_bytes(b"NOT A PARQUET FILE - q02 synthetic garbage")
    got = pit.members_asof("ths_a", "2026-07-01", suite=THS)
    assert got["pit"] is False
    assert got["basis"] == "membership_unreadable"
    assert got["members"] == []
    assert got["snapshot_date"] is None
    assert "no PIT history yet" not in got["note"]
    assert "unreadable" in got["note"]


def test_b5_read_failure_is_not_current_membership(data_root):
    """ENTRYPOINT: E3 engine.basket_membership_pit.members_asof"""
    _seed_suite(data_root, {"ths_a": [_member("SYNTHA.SZ")]})
    pit.history_path(THS).write_bytes(b"NOT A PARQUET FILE - q02 synthetic garbage")
    got = pit.members_asof("ths_a", "2026-07-01", suite=THS)
    assert got["basis"] != "current_membership", got
    assert got["basis"] == "membership_unreadable", got
    assert got["members"] == [], got


def _segment(member: str) -> SourceSegment:
    return SourceSegment(source="synthetic_vendor", basis="synthetic_unadjusted",
                         listing_id=member)


def _served(member: str) -> MemberDisposition:
    return MemberDisposition(member=member, disposition=Disposition.SERVED,
                             segments=(_segment(member),))


def test_b6_missing_member_stays_in_population():
    """ENTRYPOINT: E2 lib.dataos.read_contract.account_coverage"""
    dispositions = [
        _served("M1"), _served("M2"),
        MemberDisposition("M3", Disposition.MISSING,
                          missing_reason=MissingReason.NOT_YET_AVAILABLE),
    ]
    result = account_coverage(_contract(), ("M1", "M2", "M3"), dispositions)
    assert result.requested == 3
    assert "M3" in result.population
    assert sum(result.counts.values()) == 3
    assert result.qualified_fraction == Fraction(2, 3)
    assert result.qualified_fraction < 1
    assert "M3" not in result.qualified
    assert result.summary()["missing"] == {"NOT_YET_AVAILABLE": 1}


def test_b6_duplicate_member_refused():
    """ENTRYPOINT: E2 lib.dataos.read_contract.account_coverage"""
    with pytest.raises(ReadRefusal) as raised:
        account_coverage(_contract(), ("M1", "M1"), [_served("M1")])
    assert raised.value.code == "DUPLICATE_MEMBER"


def test_b6_disposition_outside_population_refused():
    """ENTRYPOINT: E2 lib.dataos.read_contract.account_coverage"""
    with pytest.raises(ReadRefusal) as raised:
        account_coverage(_contract(), ("M1",), [_served("M1"), _served("M9")])
    assert raised.value.code == "COVERAGE_UNRECONCILED"
    with pytest.raises(ReadRefusal) as dropped:  # the account never shrinks
        account_coverage(_contract(), ("M1", "M2"), [_served("M1")])
    assert dropped.value.code == "COVERAGE_UNRECONCILED"


# ===========================================================================
# Q02.03 — authorized-then-guest sequences cannot replay private results
# ===========================================================================

def _private_fixture(tmp_path: Path):
    root = tmp_path / "priv_root"
    root.mkdir()
    (root / "private.csv").write_bytes(
        (CSV_HEADER + "\n2026-01-02,SYNTH-" + PRIVATE_TOKEN + ",401.25\n").encode("utf-8"))
    pub = tmp_path / "pub_root"
    pub.mkdir()
    (pub / "public.csv").write_bytes(CSV_A_BYTES)
    request = {"action": "read", "ref": "priv:private.csv"}
    secrets = (PRIVATE_TOKEN, "401.25", "SYNTH-" + PRIVATE_TOKEN)
    return root, pub, request, secrets


def test_c1_guest_workspace_cannot_replay_private(tmp_path):
    """ENTRYPOINT: E1b lib.dataos.web_workspace.load_workspace_config + lib.dataos.web_api.dispatch"""
    root, pub, request, secrets = _private_fixture(tmp_path)
    auth_cfg = _write_cfg(tmp_path / "auth.json", [("priv", root), ("pub", pub)])
    guest_cfg = _write_cfg(tmp_path / "guest.json", [("pub", pub)])
    state, resp = _dispatch(auth_cfg, request)
    assert state == "ok"
    assert any(PRIVATE_TOKEN in row["symbol"] for row in resp["result"]["rows"])
    # Same Python process, workspace loaded from a config with no priv binding.
    with pytest.raises(web_workspace.WorkspaceError) as raised:
        workspace = web_workspace.load_workspace_config(guest_cfg)
        web_api.dispatch(workspace, request, config_path=guest_cfg)
    assert raised.value.code == "ROOT_NOT_BOUND"
    serialized = json.dumps({"code": raised.value.code, "str": str(raised.value)})
    for secret in secrets:
        assert secret not in serialized


def test_c2_cli_guest_process_isolated(tmp_path):
    """ENTRYPOINT: E1a scripts/data_workspace.py"""
    root, pub, request, secrets = _private_fixture(tmp_path)
    auth_cfg = _write_cfg(tmp_path / "auth.json", [("priv", root), ("pub", pub)])
    guest_cfg = _write_cfg(tmp_path / "guest.json", [("pub", pub)])
    state, resp = _cli(auth_cfg, request, tmp_path)
    assert state == "ok"
    assert any(PRIVATE_TOKEN in row["symbol"] for row in resp["result"]["rows"])
    state, code = _cli(guest_cfg, request, tmp_path, markers=secrets)
    assert (state, code) == ("refused", "ROOT_NOT_BOUND")


def test_c3_no_response_cache_across_roles(tmp_path):
    """ENTRYPOINT: E1b lib.dataos.web_api.dispatch

    authorized read -> guest read -> authorized read pinned to the now-stale
    version after the file changed: the third read must refuse, which proves no
    response was cached by the payload.
    """
    root = _root_with_csv(tmp_path)
    pub = tmp_path / "pub_root"
    pub.mkdir()
    (pub / "public.csv").write_bytes(CSV_A_BYTES)
    auth_cfg = _write_cfg(tmp_path / "bindings.json", [("q02", root), ("pub", pub)])
    guest_cfg = _write_cfg(tmp_path / "guest.json", [("pub", pub)])
    v1 = _ok("dispatch", auth_cfg, READ_PRICES, tmp_path)["source"]["file_version"]
    _refused("dispatch", guest_cfg, READ_PRICES, tmp_path, code="ROOT_NOT_BOUND")
    (root / "prices.csv").write_bytes(CSV_B_BYTES)  # the file changed
    state, code = _dispatch(auth_cfg, {**READ_PRICES, "expected_version": v1})
    assert (state, code) == ("refused", "SOURCE_VERSION_MISMATCH")


def test_c4_replay_wrong_output_id_refused():
    """ENTRYPOINT: E2 lib.dataos.read_contract.replay

    Asked for output_id Y while only X is retained -> NO_RETAINED_OUTPUT.
    """
    retained_x = _retained(b'{"answer":42}', output_id="out-X")
    with pytest.raises(ReadRefusal) as raised:
        replay(ReadRequest(mode=ReadMode.REPLAY, contract=_contract(),
                           output_id="out-Y"), retained_x)
    assert raised.value.code == "NO_RETAINED_OUTPUT"


# ===========================================================================
# Q02.04 — real composition, transport agreement and leak discipline
# ===========================================================================

def _negative_setup(case: str, tmp_path: Path):
    root = _root_with_csv(tmp_path)
    cfg = _write_cfg(tmp_path / "bindings.json", [("q02", root)])
    if case == "version_mismatch":
        return cfg, {**READ_PRICES, "expected_version": "statv1:" + "0" * 64}
    if case == "revoked_alias":
        other = tmp_path / "other_root"
        other.mkdir()
        (other / "x.csv").write_bytes(CSV_A_BYTES)
        _write_cfg(cfg, [("other", other)])
        return cfg, dict(READ_PRICES)
    if case == "disappeared_file":
        (root / "prices.csv").unlink()
        return cfg, dict(READ_PRICES)
    if case == "sensitive_path":
        return cfg, {**READ_PRICES, "ref": "q02:dir/secret_values.csv"}
    if case == "no_colon_ref":
        return cfg, {**READ_PRICES, "ref": "q02prices.csv"}
    if case == "unknown_field":
        return cfg, {**READ_PRICES, "surprise": 1}
    if case == "unknown_action":
        return cfg, {"action": "explode"}
    raise AssertionError(f"unknown negative case {case}")


NEGATIVE_CASES = [
    ("version_mismatch", "SOURCE_VERSION_MISMATCH"),
    ("revoked_alias", "ROOT_NOT_BOUND"),
    ("disappeared_file", "SOURCE_NOT_FOUND"),
    ("sensitive_path", "PATH_REFUSED"),
    ("no_colon_ref", "INVALID_DATA_REF"),
    ("unknown_field", "INVALID_REQUEST_FIELDS"),
    ("unknown_action", "UNKNOWN_ACTION"),
]


@pytest.mark.parametrize("case,expected", NEGATIVE_CASES)
def test_d1_transports_agree_on_refusal_codes(case, expected, tmp_path):
    """ENTRYPOINT: E1a+E1b scripts/data_workspace.py + lib.dataos.web_api.dispatch"""
    cfg, payload = _negative_setup(case, tmp_path)
    for transport in TRANSPORTS:
        _refused(transport, cfg, payload, tmp_path, code=expected,
                 markers=LEAK_MARKERS)


@pytest.mark.parametrize("case,expected", NEGATIVE_CASES[:5])
def test_l1_cli_refusal_envelope_and_leak_discipline(case, expected, tmp_path):
    """ENTRYPOINT: E1a scripts/data_workspace.py

    Every CLI refusal is ONE JSON object with documented error keys only, and
    stdout+stderr carry no host path, no traceback and no fixture value.
    """
    cfg, payload = _negative_setup(case, tmp_path)
    state, code = _cli(cfg, payload, tmp_path, markers=LEAK_MARKERS)
    assert (state, code) == ("refused", expected)


PATH_REFS = [
    ("traversal", "q02:../x", "PATH_REFUSED"),
    ("dot_env", "q02:.env", "PATH_REFUSED"),
    ("git_config", "q02:.git/config", "PATH_REFUSED"),
    ("secret_values", "q02:dir/secret_values.csv", "PATH_REFUSED"),
    ("api_key", "q02:api_key.json", "PATH_REFUSED"),
    ("symlink_out", "q02:link.csv", "PATH_OR_SOURCE_REFUSED"),
    ("hardlink", "q02:hard.csv", "REGULAR_PRIVATE_FILE_REQUIRED"),
    ("no_colon", "prices.csv", "INVALID_DATA_REF"),
    ("unbound_alias", "elsewhere:prices.csv", "ROOT_NOT_BOUND"),
]


@pytest.mark.parametrize("transport", TRANSPORTS)
@pytest.mark.parametrize("name,ref,expected", PATH_REFS)
def test_l2_path_refusals(transport, name, ref, expected, tmp_path):
    """ENTRYPOINT: E1a+E1b scripts/data_workspace.py + lib.dataos.web_api.dispatch"""
    root = _root_with_csv(tmp_path)
    outside = tmp_path / "outside.csv"
    outside.write_bytes(CSV_A_BYTES)
    if name == "symlink_out":
        os.symlink(outside, root / "link.csv")  # inside the root, points outside
    if name == "hardlink":
        os.link(outside, root / "hard.csv")
        assert (root / "hard.csv").stat().st_nlink == 2
    cfg = _write_cfg(tmp_path / "bindings.json", [("q02", root)])
    _refused(transport, cfg, {"action": "read", "ref": ref}, tmp_path,
             code=expected, markers=LEAK_MARKERS)


SHAPE_CASES = [
    ("too_large", "REQUEST_TOO_LARGE"),
    ("unknown_field", "INVALID_REQUEST_FIELDS"),
    ("unknown_action", "UNKNOWN_ACTION"),
]


@pytest.mark.parametrize("transport", TRANSPORTS)
@pytest.mark.parametrize("case,expected", SHAPE_CASES)
def test_l3_request_shape(transport, case, expected, tmp_path):
    """ENTRYPOINT: E1a+E1b scripts/data_workspace.py + lib.dataos.web_api.dispatch"""
    root = _root_with_csv(tmp_path)
    cfg = _write_cfg(tmp_path / "bindings.json", [("q02", root)])
    if case == "too_large":
        payload = {"action": "read", "ref": "q02:" + "a" * 20000}
    elif case == "unknown_field":
        payload = {**READ_PRICES, "surprise": 1}
    else:
        payload = {"action": "explode"}
    _refused(transport, cfg, payload, tmp_path, code=expected, markers=LEAK_MARKERS)


def test_l3_cli_nan_constant_refused(tmp_path):
    """ENTRYPOINT: E1a scripts/data_workspace.py (CLI stdin parse only)"""
    root = _root_with_csv(tmp_path)
    cfg = _write_cfg(tmp_path / "bindings.json", [("q02", root)])
    state, code = _cli(cfg, b'{"action":"read","ref":"q02:prices.csv","limit":NaN}',
                       tmp_path, markers=LEAK_MARKERS)
    assert (state, code) == ("refused", "INVALID_REQUEST_JSON")


@pytest.mark.parametrize("transport", TRANSPORTS)
def test_d2_source_byte_disclosure(transport, tmp_path):
    """ENTRYPOINT: E1a+E1b scripts/data_workspace.py + lib.dataos.web_api.dispatch

    The adapter DISCLOSES that it does not verify source bytes by content hash:
    content_sha256 is None and the version basis names the stat identity.
    """
    root = _root_with_csv(tmp_path)
    cfg = _write_cfg(tmp_path / "bindings.json", [("q02", root)])
    resp = _ok(transport, cfg, READ_PRICES, tmp_path, markers=LEAK_MARKERS)
    assert resp["source"]["content_sha256"] is None
    assert resp["source"]["file_version_basis"] == (
        "device_inode_size_mtime_ctime_not_content_hash")
