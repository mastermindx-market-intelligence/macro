"""Hermetic tests for the bounded Macro/Caddy publication transaction.

Every scenario uses the real private journal files on disk (pytest tmp_path)
and injected fakes for the Caddy admin API, the autosave reader and the
source-baseline installer.  No network, host, daemon or credential access.
"""

from __future__ import annotations

import copy
import json
import os
import stat
from base64 import b64encode
from collections import deque
from pathlib import Path

import pytest

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app/deploy"))
import macro_caddy_publication as mcp


# ---------------------------------------------------------------------------
# fixtures / fakes
# ---------------------------------------------------------------------------

def make_cfg(tag: str) -> dict:
    return {
        "admin": {"listen": "localhost:2019"},
        "apps": {
            "http": {
                "servers": {
                    "srv0": {
                        "listen": [":443"],
                        "routes": [{"id": "route-%s" % tag, "handle": [{"handler": "static"}]}],
                    }
                }
            }
        },
    }


CFG_A = make_cfg("alpha")
CFG_B = make_cfg("beta")
CFG_C = make_cfg("gamma")
CFG_MIXED = {
    "admin": {"listen": "localhost:2019"},
    "apps": {"http": {"servers": {"srv0": {"listen": [":443"], "routes": []}}}},
}

ET_A = '"alpha-etag-1"'
ET_B = '"beta-etag-1"'
ET_C = '"gamma-etag-1"'

SRC_A = b"# managed baseline alpha\nexample.com {\n  respond \"alpha\" 200\n}\n"
SRC_B = b"# managed baseline beta\nexample.com {\n  respond \"beta\" 200\n}\n"
SRC_C = b"# managed baseline gamma\nexample.com {\n  respond \"gamma\" 200\n}\n"


class FakeApi:
    """In-memory Caddy admin API adapter with scripted write outcomes.

    Script items: an ``int`` HTTP status, an ``Exception`` instance to raise,
    or a zero-arg callable run in place (may mutate the fake server first).
    """

    def __init__(self, config, etag, journal_dir: Path = None, autosave=None):
        self._config = copy.deepcopy(config)
        self._etag = etag
        self.journal_dir = journal_dir
        self.autosave = autosave            # server-side persistence of the config
        self.read_script = deque()          # optional (config, etag) overrides
        self.write_script = deque()
        self.reads = 0
        self.writes = []                    # (candidate, etag, journal names at write)
        self.applied_after_write = False

    # -- injected surface ---------------------------------------------------
    def read(self):
        self.reads += 1
        if self.read_script:
            config, etag = self.read_script.popleft()
            return copy.deepcopy(config), etag
        return copy.deepcopy(self._config), self._etag

    def write(self, candidate, etag):
        names = None
        if self.journal_dir is not None and self.journal_dir.is_dir():
            names = sorted(p.name[:10] for p in self.journal_dir.iterdir())
        self.writes.append((copy.deepcopy(candidate), etag, names))
        if not self.write_script:
            # Default: a healthy server applies the candidate and answers 200.
            import hashlib
            digest = hashlib.sha256(
                json.dumps(candidate, sort_keys=True).encode("utf-8")).hexdigest()[:12]
            self.apply(candidate, '"post-%s"' % digest)
            return 200
        item = self.write_script.popleft()
        if callable(item):
            item()
            return 200
        if isinstance(item, Exception):
            raise item
        return item

    # -- server-side simulation helpers -------------------------------------
    def apply(self, config, etag):
        """Simulate the server applying a configuration (and persisting it)."""
        self._config = copy.deepcopy(config)
        self._etag = etag
        self.applied_after_write = True
        if self.autosave is not None:
            self.autosave.value = copy.deepcopy(config)


class Autosave:
    """Native autosave reader over a mutable JSON document."""

    def __init__(self, value):
        self.value = copy.deepcopy(value)
        self.reads = 0

    def __call__(self):
        self.reads += 1
        if isinstance(self.value, Exception):
            raise self.value
        return copy.deepcopy(self.value)


class Installer:
    """Caller-provided exact source-baseline installer."""

    def __init__(self, failures: int = 0):
        self.failures = failures
        self.calls = []

    def __call__(self, old, new):
        self.calls.append((bytes(old), bytes(new)))
        if len(self.calls) <= self.failures:
            raise RuntimeError("simulated source installer failure")


@pytest.fixture
def journal_dir(tmp_path):
    return tmp_path / "macro-caddy-publication"


@pytest.fixture
def world(journal_dir):
    """A consistent pre-publication world: API and autosave at A."""

    class World:
        pass

    w = World()
    w.autosave = Autosave(CFG_A)
    w.api = FakeApi(CFG_A, ET_A, journal_dir, autosave=w.autosave)
    w.installer = Installer()
    w.journal_dir = journal_dir
    return w


def publish(world, *, preimage=CFG_A, candidate=CFG_B, before=SRC_A, after=SRC_B, **overrides):
    call = dict(
        state_dir=world.journal_dir,
        api=world.api,
        expected_preimage=preimage,
        candidate=candidate,
        source_before=before,
        source_after=after,
        read_autosave=world.autosave,
        install_source=world.installer,
    )
    call.update(overrides)
    return mcp.publish(**call)


def journal_names(journal_dir: Path):
    return sorted(p.name for p in journal_dir.iterdir()) if journal_dir.is_dir() else []


def lost_response(api, autosave, *, applied_config=None, applied_etag=None):
    """Script one write that applies server-side and then loses its response."""
    def _apply_then_lose():
        if applied_config is not None:
            api.apply(applied_config, applied_etag)
        raise TimeoutError("simulated lost response")
    api.write_script.append(_apply_then_lose)


def op_id_for(preimage, candidate, before, after):
    return mcp._op_id(
        mcp._validate_doc(preimage)[0],
        mcp._validate_doc(candidate)[0],
        mcp._sha256_hex(before),
        mcp._sha256_hex(after),
    )


# ---------------------------------------------------------------------------
# ordinary successful publications
# ---------------------------------------------------------------------------

def test_publish_two_ordinary_source_updates(world):
    first = publish(world)
    assert first["status"] == "published"
    assert first["published"] is True
    assert first["effect_state"] == "applied_verified"
    assert first["write_http_status"] == 200
    assert first["installed_source"] is True
    assert first["receipt_written"] is True
    assert first["pending"] is False
    assert world.api._config == CFG_B
    assert world.autosave.value == CFG_B
    assert world.installer.calls == [(SRC_A, SRC_B)]

    # A durable committed receipt permits the ordinary B->C update, using B as
    # both the source baseline and the current full preimage.
    world.autosave.value = CFG_B
    second = publish(world, preimage=CFG_B, candidate=CFG_C, before=SRC_B, after=SRC_C)
    assert second["status"] == "published"
    assert second["op_id"] != first["op_id"]
    assert world.api._config == CFG_C
    assert world.installer.calls == [(SRC_A, SRC_B), (SRC_B, SRC_C)]
    assert world.api.writes[1][0] == CFG_C
    assert len(world.api.writes) == 2


def test_publish_exact_side_effect_order(world, monkeypatch):
    events = []

    real_read = world.api.read

    def counting_read():
        events.append("read")
        return real_read()

    world.api.read = counting_read

    real_write = world.api.write

    def counting_write(candidate, etag):
        events.append("write")
        return real_write(candidate, etag)

    world.api.write = counting_write

    real_autosave = world.autosave

    def counting_autosave():
        events.append("autosave")
        return real_autosave()

    world.autosave = counting_autosave

    real_install = world.installer

    def counting_install(old, new):
        events.append("install")
        return real_install(old, new)

    counting_install.calls = real_install.calls
    world.installer = counting_install

    real_journal_write = mcp._write_journal_file

    def counting_journal_write(path, payload):
        name = Path(path).name
        events.append("intent-write" if name.startswith("intent-") else "receipt-write")
        return real_journal_write(path, payload)

    monkeypatch.setattr(mcp, "_write_journal_file", counting_journal_write)

    result = publish(world)

    assert result["status"] == "published"
    # Qualify (read, autosave), re-check (read), persist intent, ONE conditional
    # write, verify (read, autosave), install source, commit receipt.
    assert events == [
        "read", "autosave", "read", "intent-write", "write",
        "read", "autosave", "install", "receipt-write",
    ]
    # The intent was already durable when the sole conditional write happened,
    # and no closure existed yet.
    candidate, etag, names = world.api.writes[0]
    assert candidate == CFG_B and etag == ET_A
    assert [n for n in names if n.startswith("intent-")] != []
    assert [n for n in names if n.startswith("receipt-")] == []
    assert world.installer.calls == [(SRC_A, SRC_B)]


# ---------------------------------------------------------------------------
# refusals before any conditional write (proven no-effect)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("bad_etag", [None, "", "etag-without-quotes", '"has\r\ncontrol"', 12345])
def test_missing_or_malformed_etag_refused(world, bad_etag):
    world.api.read_script.append((copy.deepcopy(CFG_A), bad_etag))
    result = publish(world)
    assert result["status"] == "refused"
    assert result["effect_state"] == "none_proven"
    assert result["write_attempted"] is False
    assert result["errors"][0]["code"] == "etag_missing_or_invalid"
    assert world.api.writes == []
    assert world.installer.calls == []
    assert journal_names(world.journal_dir) == []


def test_stale_etag_between_reads_refused(world):
    world.api.read_script.append((copy.deepcopy(CFG_A), ET_A))
    world.api.read_script.append((copy.deepcopy(CFG_A), '"alpha-etag-2"'))
    result = publish(world)
    assert result["status"] == "refused"
    assert result["errors"][0]["code"] == "etag_stale"
    assert result["write_attempted"] is False
    assert world.api.writes == []
    assert journal_names(world.journal_dir) == []


def test_full_preimage_drift_refused(world):
    world.api.read_script.append((copy.deepcopy(CFG_C), ET_C))
    result = publish(world)
    assert result["status"] == "refused"
    assert result["errors"][0]["code"] == "preimage_drift"
    assert result["write_attempted"] is False
    assert world.api.writes == []
    assert journal_names(world.journal_dir) == []


@pytest.mark.parametrize(
    "second_read",
    [
        (make_cfg("other-host"), '"other-host-etag"'),   # host update: config+etag
        (make_cfg("other-host"), ET_A),                  # config changed, etag unchanged
    ],
)
def test_concurrent_unrelated_host_update_before_post_refused(world, second_read):
    world.api.read_script.append((copy.deepcopy(CFG_A), ET_A))
    world.api.read_script.append(copy.deepcopy(second_read))
    result = publish(world)
    assert result["status"] == "refused"
    assert result["errors"][0]["code"] in ("etag_stale", "preimage_drift_concurrent")
    assert result["write_attempted"] is False
    assert world.api.writes == []
    assert journal_names(world.journal_dir) == []


def test_wrong_autosave_before_post_refused(world):
    world.autosave.value = CFG_C
    result = publish(world)
    assert result["status"] == "refused"
    assert result["errors"][0]["code"] == "autosave_preimage_mismatch"
    assert result["write_attempted"] is False
    assert world.api.writes == []
    assert journal_names(world.journal_dir) == []


def test_api_read_failure_refused(world):
    def broken_read():
        raise ConnectionError("admin API unreachable")

    world.api.read = broken_read
    result = publish(world)
    assert result["status"] == "refused"
    assert result["errors"][0]["code"] == "api_read_failed"
    assert result["effect_state"] == "none_proven"
    assert world.api.writes == []
    assert journal_names(world.journal_dir) == []


# ---------------------------------------------------------------------------
# uncertain effect: pending intent retained, second write blocked
# ---------------------------------------------------------------------------

def test_network_timeout_with_api_equal_preimage_holds_and_blocks(world):
    world.api.write_script.append(TimeoutError("simulated network timeout"))
    result = publish(world)
    assert result["status"] == "held_pending"
    assert result["pending"] is True
    assert result["effect_state"] == "uncertain"
    assert result["write_attempted"] is True
    assert len(world.api.writes) == 1
    assert world.installer.calls == []
    names = journal_names(world.journal_dir)
    assert len([n for n in names if n.startswith("intent-")]) == 1
    assert [n for n in names if n.startswith("receipt-")] == []

    # Even though the API still equals the preimage (looks like nothing
    # happened), no in-flight effect can be proven: no second POST is allowed.
    again = publish(world)
    assert again["status"] == "held_pending"
    assert again["errors"][0]["code"] == "reconcile_api_diverged"
    assert len(world.api.writes) == 1
    assert world.installer.calls == []
    status = mcp.journal_status(world.journal_dir)
    assert status["ok"] is True and len(status["pending_op_ids"]) == 1


def test_timeout_after_apply_then_readonly_reconcile_completes(world):
    lost_response(world.api, world.autosave, applied_config=CFG_B, applied_etag=ET_B)
    first = publish(world)
    assert first["status"] == "held_pending"
    assert first["effect_state"] == "uncertain"

    # The updater's own autosave caught up with what the server had applied.
    world.autosave.value = CFG_B

    pending_op = op_id_for(CFG_A, CFG_B, SRC_A, SRC_B)
    second = publish(world)
    assert second["status"] == "reconciled"
    assert second["op_id"] == pending_op
    assert second["write_attempted"] is False       # read-only reconciliation
    assert second["effect_state"] == "applied_verified"
    assert second["receipt_written"] is True
    assert len(world.api.writes) == 1               # never a second POST
    assert world.installer.calls == [(SRC_A, SRC_B)]  # original captured bytes

    receipt = mcp._load_journal_record(
        world.journal_dir / ("receipt-%s.json" % pending_op))[0]
    intent = mcp._load_journal_record(
        world.journal_dir / ("intent-%s.json" % pending_op))[0]
    assert receipt["closure"] == "committed"
    assert receipt["reconciled"] is True
    assert receipt["intent_ino"] == os.stat(
        world.journal_dir / ("intent-%s.json" % pending_op)).st_ino
    assert intent["op_id"] == receipt["op_id"]
    assert intent["candidate_digest"] == mcp._validate_doc(CFG_B)[0]
    status = mcp.journal_status(world.journal_dir)
    assert status["pending_op_ids"] == []


def test_write_5xx_holds_pending_and_blocks(world):
    world.api.write_script.append(503)
    result = publish(world)
    assert result["status"] == "held_pending"
    assert result["effect_state"] == "uncertain"
    assert result["write_http_status"] == 503
    assert len(world.api.writes) == 1

    again = publish(world)
    assert again["status"] == "held_pending"
    assert len(world.api.writes) == 1


def test_write_412_is_proven_pre_effect_refusal_then_fresh_publication(world):
    world.api.write_script.append(412)
    result = publish(world)
    assert result["status"] == "refused"
    assert result["effect_state"] == "none_proven"
    assert result["write_http_status"] == 412
    assert result["receipt_written"] is True
    assert result["pending"] is False
    assert world.installer.calls == []
    status = mcp.journal_status(world.journal_dir)
    assert status["pending_op_ids"] == []

    # A proven pre-effect refusal does not brick the owner: a fresh, different
    # operation may publish normally.
    other_candidate = make_cfg("beta-2")

    def _apply_and_succeed():
        world.api.apply(other_candidate, ET_B)

    world.api.write_script.append(_apply_and_succeed)
    second = publish(world, candidate=other_candidate)
    assert second["status"] == "published"
    assert len(world.api.writes) == 2


def test_mixed_candidate_readback_holds_pending(world):
    def _apply_mixed():
        world.api.apply(CFG_MIXED, '"mixed-etag"')  # autosave follows the server

    world.api.write_script.append(_apply_mixed)
    world.api.write_script.append(200)
    result = publish(world)
    assert result["status"] == "held_pending"
    assert result["errors"][0]["code"] == "readback_mismatch"
    assert result["effect_state"] == "uncertain"
    assert result["write_http_status"] == 200
    assert world.installer.calls == []
    assert mcp.journal_status(world.journal_dir)["pending_op_ids"] != []

    # Diverged states stay held; still no second POST.
    again = publish(world)
    assert again["status"] == "held_pending"
    assert len(world.api.writes) == 1
    assert world.installer.calls == []


def test_autosave_not_candidate_after_200_holds_then_reconciles(world):
    def _apply_b_with_lagging_autosave():
        world.api.apply(CFG_B, ET_B)
        world.autosave.value = copy.deepcopy(CFG_A)  # autosave lagged behind

    world.api.write_script.append(_apply_b_with_lagging_autosave)
    world.api.write_script.append(200)
    result = publish(world)          # 200 returned, but the autosave is stale
    assert result["status"] == "held_pending"
    assert result["errors"][0]["code"] == "autosave_candidate_mismatch"
    assert result["installed_source"] is False
    assert world.installer.calls == []

    # Once the autosave catches up, the same operation finishes read-only.
    world.autosave.value = CFG_B
    again = publish(world)
    assert again["status"] == "reconciled"
    assert again["write_attempted"] is False
    assert len(world.api.writes) == 1
    assert world.installer.calls == [(SRC_A, SRC_B)]


# ---------------------------------------------------------------------------
# source installer failures
# ---------------------------------------------------------------------------

def test_source_install_failure_retains_pending_and_never_replays_api(world):
    def _apply_b():
        world.api.apply(CFG_B, ET_B)

    world.api.write_script.append(_apply_b)
    world.api.write_script.append(200)
    world.installer = Installer(failures=1)

    # Server applied (autosave followed), API readback and autosave match the
    # candidate, but the source installer fails.
    first = publish(world)
    assert first["status"] == "held_pending"
    assert first["errors"][0]["code"] == "install_source_failed"
    assert first["installed_source"] is False
    assert mcp.journal_status(world.journal_dir)["pending_op_ids"] != []

    # Retried reconciliation installs the captured source but never re-POSTs.
    world.installer.failures = 0
    second = publish(world)
    assert second["status"] == "reconciled"
    assert len(world.api.writes) == 1
    assert world.installer.calls == [(SRC_A, SRC_B), (SRC_A, SRC_B)]
    assert mcp.journal_status(world.journal_dir)["pending_op_ids"] == []


# ---------------------------------------------------------------------------
# pending B presented with C
# ---------------------------------------------------------------------------

def test_pending_b_presented_with_c_reconciles_prior_b_only(world):
    lost_response(world.api, world.autosave, applied_config=CFG_B, applied_etag=ET_B)
    pending = publish(world)
    assert pending["status"] == "held_pending"
    world.autosave.value = CFG_B

    pending_op = op_id_for(CFG_A, CFG_B, SRC_A, SRC_B)
    # A later call arrives with a NEW candidate C while B is still pending.
    result = publish(world, preimage=CFG_B, candidate=CFG_C, before=SRC_B, after=SRC_C)
    assert result["status"] == "reconciled_prior"
    assert result["op_id"] == pending_op
    assert result["reconciled_prior"] is True
    assert result["requested_op_id"] != pending_op
    assert result["write_attempted"] is False
    # Only B was ever POSTed, and only B's captured source bytes installed:
    # C was never adopted as B.
    assert len(world.api.writes) == 1
    assert world.api.writes[0][0] == CFG_B
    assert world.installer.calls == [(SRC_A, SRC_B)]
    assert mcp.journal_status(world.journal_dir)["pending_op_ids"] == []

    # Now the ordinary B->C publication can proceed normally.
    third = publish(world, preimage=CFG_B, candidate=CFG_C, before=SRC_B, after=SRC_C)
    assert third["status"] == "published"
    assert world.api.writes[1][0] == CFG_C
    assert world.installer.calls[-1] == (SRC_B, SRC_C)


def test_pending_b_presented_with_c_when_diverged_stays_held(world):
    world.api.write_script.append(TimeoutError("simulated lost response"))
    first = publish(world)
    assert first["status"] == "held_pending"
    # The API still equals preimage A: B did not (provably) land.

    result = publish(world, preimage=CFG_B, candidate=CFG_C, before=SRC_B, after=SRC_C)
    assert result["status"] == "held_pending"
    assert result["errors"][0]["code"] == "reconcile_api_diverged"
    assert result["op_id"] == op_id_for(CFG_A, CFG_B, SRC_A, SRC_B)
    assert len(world.api.writes) == 1
    assert world.installer.calls == []
    assert len(mcp.journal_status(world.journal_dir)["pending_op_ids"]) == 1

    # Re-presenting B is also held, and still never re-POSTs.
    again = publish(world)
    assert again["status"] == "held_pending"
    assert len(world.api.writes) == 1


def test_no_hidden_write_retry_across_repeated_calls(world):
    world.api.write_script.append(TimeoutError("simulated lost response"))
    assert publish(world)["status"] == "held_pending"
    for _ in range(4):
        assert publish(world)["status"] == "held_pending"
    assert len(world.api.writes) == 1
    assert world.installer.calls == []


# ---------------------------------------------------------------------------
# journal custody: corruption, symlinks, tampering
# ---------------------------------------------------------------------------

def _pending_intent_path(world):
    names = [n for n in journal_names(world.journal_dir) if n.startswith("intent-")]
    assert len(names) == 1
    return world.journal_dir / names[0]


def test_corrupted_intent_fails_closed(world):
    world.api.write_script.append(TimeoutError("simulated lost response"))
    assert publish(world)["status"] == "held_pending"
    intent_path = _pending_intent_path(world)
    intent_path.write_bytes(intent_path.read_bytes() + b"}")  # tamper

    result = publish(world)
    assert result["status"] == "refused"
    codes = [e["code"] for e in result["errors"]]
    assert "journal_corrupt" in codes
    assert len(world.api.writes) == 1
    assert world.installer.calls == []
    assert mcp.journal_status(world.journal_dir)["ok"] is False


def test_symlinked_intent_fails_closed(world, tmp_path):
    world.api.write_script.append(TimeoutError("simulated lost response"))
    assert publish(world)["status"] == "held_pending"
    intent_path = _pending_intent_path(world)
    data = intent_path.read_bytes()
    decoy = tmp_path / "decoy-copy.json"
    decoy.write_bytes(data)
    intent_path.unlink()
    intent_path.symlink_to(decoy)

    result = publish(world)
    assert result["status"] == "refused"
    codes = [e["code"] for e in result["errors"]]
    assert "journal_symlink" in codes
    assert len(world.api.writes) == 1
    assert world.installer.calls == []


def test_symlinked_state_dir_refused(world, tmp_path):
    link = tmp_path / "aliased-journal"
    world.api.write_script.append(TimeoutError("simulated lost response"))
    assert publish(world)["status"] == "held_pending"
    link.symlink_to(world.journal_dir)

    result = mcp.publish(
        state_dir=link,
        api=world.api,
        expected_preimage=CFG_B,
        candidate=CFG_C,
        source_before=SRC_B,
        source_after=SRC_C,
        read_autosave=world.autosave,
        install_source=world.installer,
    )
    assert result["status"] == "refused"
    assert result["errors"][0]["code"] == "state_dir_symlink"
    assert len(world.api.writes) == 1


def test_changed_source_bytes_fail_closed(world):
    world.api.write_script.append(TimeoutError("simulated lost response"))
    assert publish(world)["status"] == "held_pending"
    intent_path = _pending_intent_path(world)
    record = json.loads(intent_path.read_bytes().decode("utf-8"))
    record["source_after_b64"] = "Km1hbmlwdWxhdGVkKg=="  # b"*manipulated*"
    intent_path.write_bytes(json.dumps(record).encode("utf-8"))

    result = publish(world)
    assert result["status"] == "refused"
    assert result["errors"][0]["code"] == "journal_corrupt"
    assert world.installer.calls == []
    assert len(world.api.writes) == 1


def test_tampered_source_with_reforged_integrity_holds(world):
    world.api.write_script.append(TimeoutError("simulated lost response"))
    assert publish(world)["status"] == "held_pending"
    intent_path = _pending_intent_path(world)
    record = json.loads(intent_path.read_bytes().decode("utf-8"))
    record["source_after_b64"] = b64encode(b"# forged baseline\n").decode("ascii")
    record.pop("integrity")
    record["integrity"] = mcp._record_integrity(record)
    intent_path.write_bytes(json.dumps(record).encode("utf-8"))

    # The record now looks internally consistent, but the captured source
    # digest no longer matches its own recorded binding: hold, never install.
    result = publish(world)
    assert result["status"] == "held_pending"
    assert result["errors"][0]["code"] == "journal_captured_bytes_invalid"
    assert result["effect_state"] == "uncertain"
    assert world.installer.calls == []
    assert len(world.api.writes) == 1


# ---------------------------------------------------------------------------
# custody properties, idempotence, argument validation
# ---------------------------------------------------------------------------

def test_journal_custody_properties_and_idempotent_recall(world):
    result = publish(world)
    assert result["status"] == "published"
    op = result["op_id"]
    intent_path = world.journal_dir / ("intent-%s.json" % op)
    receipt_path = world.journal_dir / ("receipt-%s.json" % op)
    for path in (intent_path, receipt_path):
        st = os.lstat(path)
        assert stat.S_ISREG(st.st_mode)
        assert stat.S_IMODE(st.st_mode) == 0o600
        assert st.st_nlink == 1
        assert st.st_uid == os.getuid()

    # Exclusive immutable records: the module never rewrites them, and a
    # recall of the same operation returns the durable receipt evidence.
    before_stat = intent_path.stat()
    recall = publish(world)
    assert recall["status"] == "already_published"
    assert recall["published"] is True
    assert recall["op_id"] == op
    assert recall["closure"] == "committed"
    assert len(world.api.writes) == 1
    # Current baseline is reverified through the idempotent caller, rather than
    # promoted from a historical receipt without a live source check.
    assert world.installer.calls == [(SRC_A, SRC_B), (SRC_A, SRC_B)]
    assert intent_path.stat().st_ino == before_stat.st_ino


@pytest.mark.parametrize(
    "kwargs, code",
    [
        ({"candidate": [1, 2, 3]}, "invalid_structure"),
        ({"expected_preimage": {"nan": float("nan")}}, "invalid_structure"),
        ({"source_before": "not-bytes"}, "invalid_source_bytes"),
        ({"source_after": b"x" * (mcp.MAX_SOURCE_BYTES + 1)}, "source_oversized"),
    ],
)
def test_invalid_arguments_refused(world, kwargs, code):
    call_kwargs = dict(preimage=CFG_A, candidate=CFG_B, before=SRC_A, after=SRC_B)
    call_kwargs.update(kwargs)
    result = publish(world, **call_kwargs)
    assert result["status"] == "refused"
    assert result["errors"][0]["code"] == code
    assert result["write_attempted"] is False
    assert world.api.writes == []
    assert not world.journal_dir.exists()


def test_non_dict_api_config_is_invalid_structure(world):
    world.api.read_script.append((["not", "an", "object"], ET_A))
    result = publish(world)
    assert result["status"] == "refused"
    assert result["errors"][0]["code"] == "api_invalid_structure"
    assert world.api.writes == []


def test_journal_status_does_not_create_journal(world, tmp_path):
    missing = tmp_path / "not-created-yet"
    status = mcp.journal_status(missing)
    assert status["ok"] is True
    assert status["pending_op_ids"] == []
    assert not missing.exists()


def test_state_dir_not_private_refused(world, tmp_path):
    loose = tmp_path / "loose-journal"
    old_umask = os.umask(0o022)
    try:
        os.mkdir(loose, 0o755)
    finally:
        os.umask(old_umask)
    result = mcp.publish(
        state_dir=loose,
        api=world.api,
        expected_preimage=CFG_A,
        candidate=CFG_B,
        source_before=SRC_A,
        source_after=SRC_B,
        read_autosave=world.autosave,
        install_source=world.installer,
    )
    assert result["status"] == "refused"
    assert result["errors"][0]["code"] == "state_dir_not_private"
    assert world.api.writes == []


def test_actual_caddy_full_config_etag_with_path_space_is_preserved(world):
    native_etag = '"/config/ 9a6898e094be700c"'
    world.api._etag = native_etag
    result = publish(world)
    assert result["status"] == "published", result
    assert world.api.writes[0][1] == native_etag


def test_recalling_proven_412_never_claims_adopted_or_installed(world):
    world.api.write_script.append(412)
    first = publish(world)
    assert first["status"] == "refused"
    second = publish(world)
    assert second["status"] == "refused", second
    assert second["published"] is False
    assert second["installed_source"] is False
    assert second["effect_state"] == "none_proven"
    assert len(world.api.writes) == 1
    assert world.installer.calls == []


def _replace_intent_inode(journal):
    path = next(journal.glob('intent-*.json'))
    replacement = path.with_name('replacement.tmp')
    replacement.write_bytes(path.read_bytes())
    replacement.chmod(0o600)
    replacement.replace(path)


def test_intent_inode_change_before_post_refuses_without_write(world, monkeypatch):
    original = mcp._write_journal_file
    def changed(path, raw):
        result = original(path, raw)
        if path.name.startswith('intent-'):
            _replace_intent_inode(path.parent)
        return result
    monkeypatch.setattr(mcp, '_write_journal_file', changed)
    result = publish(world)
    assert result['status'] == 'held_pending'
    assert result['published'] is False and result['write_attempted'] is False
    assert world.api.writes == [] and world.installer.calls == []


def test_directory_replacement_after_intent_refuses_before_post(world, monkeypatch):
    original = mcp._write_journal_file
    def changed(path, raw):
        result = original(path, raw)
        if path.name.startswith('intent-'):
            retained = path.parent.with_name('retained-original-journal')
            path.parent.rename(retained)
            path.parent.mkdir(mode=0o700)
        return result
    monkeypatch.setattr(mcp, '_write_journal_file', changed)
    result = publish(world)
    assert result['status'] == 'held_pending'
    assert world.api.writes == [] and world.installer.calls == []
    assert list(world.journal_dir.with_name('retained-original-journal').glob('intent-*'))


def test_intent_substitution_during_readback_prevents_source_install(world):
    def autosave_with_replacement():
        value = world.autosave()
        if list(world.journal_dir.glob('intent-*')):
            _replace_intent_inode(world.journal_dir)
        return value
    result = publish(world, read_autosave=autosave_with_replacement)
    assert result['status'] == 'held_pending'
    assert len(world.api.writes) == 1 and world.installer.calls == []
    assert not list(world.journal_dir.glob('receipt-*'))


def test_installer_intent_substitution_cannot_close_receipt(world):
    def install_then_replace(before, after):
        world.installer(before, after)
        _replace_intent_inode(world.journal_dir)
    result = publish(world, install_source=install_then_replace)
    assert result['status'] == 'held_pending' and result['installed_source'] is True
    assert len(world.api.writes) == 1
    assert not list(world.journal_dir.glob('receipt-*'))


def test_normal_rollback_then_reapply_has_new_closed_predecessor_identity(world):
    import hashlib
    installed = [SRC_A]
    def install(before, after):
        assert installed[0] in (before, after)
        installed[0] = after
    original_etag = world.api._etag
    first = publish(world, install_source=install)
    first_intent = world.journal_dir / ('intent-' + first['op_id'] + '.json')
    original_bytes = first_intent.read_bytes()
    second = publish(world, preimage=CFG_B, candidate=CFG_A,
                     before=SRC_B, after=SRC_A, install_source=install)
    assert second['status'] == 'published'
    assert world.api._config == CFG_A and installed[0] == SRC_A
    # Caddy's content-addressed version may return to the exact initial ETag.
    world.api._etag = original_etag
    third = publish(world, install_source=install)
    assert [first['status'], second['status'], third['status']] == ['published'] * 3
    assert len({first['op_id'], second['op_id'], third['op_id']}) == 3
    assert len(world.api.writes) == 3
    assert world.api._config == world.autosave.value == CFG_B
    assert installed[0] == SRC_B
    assert first_intent.read_bytes() == original_bytes
    tip_intent = json.loads((world.journal_dir / ('intent-' + third['op_id'] + '.json')).read_text())
    assert tip_intent['predecessor'] == second['op_id']
    assert mcp.journal_status(world.journal_dir)['pending_op_ids'] == []


def test_historical_receipt_with_noncurrent_api_cannot_claim_success(world):
    first = publish(world)
    assert first['status'] == 'published'
    world.api.apply(CFG_A, ET_A)
    count = len(world.installer.calls)
    again = publish(world)
    assert again['status'] == 'refused' and again['published'] is False
    assert again['installed_source'] is False
    assert len(world.api.writes) == 1 and len(world.installer.calls) == count


@pytest.mark.parametrize('apply_rollback', [True, False])
def test_pending_rollback_blocks_new_generation_for_repeated_prior_content(world, apply_rollback):
    first = publish(world)
    lost_response(world.api, world.autosave,
                  applied_config=CFG_A if apply_rollback else None,
                  applied_etag=ET_A if apply_rollback else None)
    rollback = publish(world, preimage=CFG_B, candidate=CFG_A, before=SRC_B, after=SRC_A)
    assert rollback['status'] == 'held_pending'
    reapply = publish(world)
    assert len(world.api.writes) == 2
    if apply_rollback:
        assert reapply['status'] == 'reconciled_prior'
        assert reapply['op_id'] == rollback['op_id']
        assert world.installer.calls[-1] == (SRC_B, SRC_A)
        final = publish(world)
        assert final['status'] == 'published' and len(world.api.writes) == 3
        assert final['op_id'] != first['op_id']
        assert world.api._config == CFG_B
    else:
        assert reapply['status'] == 'held_pending'
        assert reapply['op_id'] == rollback['op_id']
        assert mcp.journal_status(world.journal_dir)['pending_op_ids'] == [rollback['op_id']]
