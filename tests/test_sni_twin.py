"""test_sni_twin.py — A08/A15/A16/A05/A07/A17 refusals for the twin record draft."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "research/single_name_intelligence/twin"))

from sni_twin import (  # noqa: E402
    OwnerRegistry,
    TwinRefused,
    TwinStore,
    canonical_json,
    history,
    latest,
    make_record,
    sha256_text,
    verify_chain,
    view_as_of,
)

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "research/single_name_intelligence/twin/sni_twin.py"
DOC_PATH = ROOT / "research/single_name_intelligence/twin/TWIN_SCHEMA_DRAFT.md"
SCHEMA_PATH = ROOT / "contracts/single_name_intelligence/twin_record.v1.schema.json"

TWIN_KEY = "synth.twin.earnings-q"
OWNER_KEY = "earnings.owner"
BLOCKED_KEY = "blocked.owner"

REFUSAL_CODES = (
    "UNKNOWN_OWNER",
    "OWNER_NOT_ALLOWED",
    "DIGEST_MISMATCH",
    "CLOCK_ORDER",
    "PERIOD_ORDER",
    "CORRECTION_REASON_REQUIRED",
    "AUTHORITY_KEY_IN_PAYLOAD",
    "AUTHORITY_FLAG_TRUE",
)


def _registry():
    return OwnerRegistry({
        OWNER_KEY: {"allowed": True},
        BLOCKED_KEY: {"allowed": False},
    })


def _payload(metric="synthetic_placeholder"):
    return {"family": "earnings", "metric": metric, "note": "synthetic"}


def _digest(payload):
    return sha256_text(canonical_json(payload))


def _clocks(known, published, start="2025-04-01", end="2025-06-30"):
    return {
        "economic_period": {"kind": "period", "start": start, "end": end},
        "owner_known_at_utc": known,
        "sni_published_at_utc": published,
    }


def _record(payload=None, clocks=None, prev=None, correction_reason=None, owner_key=OWNER_KEY,
            owner_digest=None):
    payload = payload if payload is not None else _payload()
    clocks = clocks if clocks is not None else _clocks(
        "2025-08-14T12:00:00Z", "2025-08-14T16:00:00Z"
    )
    digest = owner_digest if owner_digest is not None else _digest(payload)
    return make_record(
        twin_key=TWIN_KEY,
        owner_key=owner_key,
        payload=payload,
        owner_digest=digest,
        clocks=clocks,
        registry=_registry(),
        prev=prev,
        correction_reason=correction_reason,
    )


def test_a15_unknown_owner_refused():
    payload = _payload()
    with pytest.raises(TwinRefused) as caught:
        make_record(
            twin_key=TWIN_KEY,
            owner_key="missing.owner",
            payload=payload,
            owner_digest=_digest(payload),
            clocks=_clocks("2025-08-14T12:00:00Z", "2025-08-14T16:00:00Z"),
            registry=_registry(),
        )
    assert caught.value.code == "UNKNOWN_OWNER"


def test_a15_digest_mismatch_refused():
    with pytest.raises(TwinRefused) as caught:
        make_record(
            twin_key=TWIN_KEY,
            owner_key=OWNER_KEY,
            payload=_payload(),
            owner_digest="0" * 64,
            clocks=_clocks("2025-08-14T12:00:00Z", "2025-08-14T16:00:00Z"),
            registry=_registry(),
        )
    assert caught.value.code == "DIGEST_MISMATCH"


def test_a15_owner_not_allowed_refused():
    payload = _payload()
    with pytest.raises(TwinRefused) as caught:
        make_record(
            twin_key=TWIN_KEY,
            owner_key=BLOCKED_KEY,
            payload=payload,
            owner_digest=_digest(payload),
            clocks=_clocks("2025-08-14T12:00:00Z", "2025-08-14T16:00:00Z"),
            registry=_registry(),
        )
    assert caught.value.code == "OWNER_NOT_ALLOWED"


def test_a15_allowed_owner_admitted():
    rec = _record()
    assert rec["generation"] == 1
    assert rec["supersedes"] is None
    assert rec["owner_key"] == OWNER_KEY
    assert rec["owner_digest"] == _digest(rec["payload"])
    for name in (
        "rank_authority", "gate_authority", "size_authority",
        "signal_authority", "escalation_authority", "trade_authority",
    ):
        assert rec["authority_flags"][name] is False


def test_a08_owner_known_after_published_refused():
    with pytest.raises(TwinRefused) as caught:
        _record(clocks=_clocks("2025-08-14T18:00:00Z", "2025-08-14T16:00:00Z"))
    assert caught.value.code == "CLOCK_ORDER"


def test_a08_equal_clocks_allowed():
    rec = _record(clocks=_clocks("2025-08-14T16:00:00Z", "2025-08-14T16:00:00Z"))
    assert rec["generation"] == 1
    assert rec["clocks"]["owner_known_at_utc"] == rec["clocks"]["sni_published_at_utc"]


def test_a08_period_end_before_start_refused():
    with pytest.raises(TwinRefused) as caught:
        _record(clocks=_clocks(
            "2025-08-14T12:00:00Z", "2025-08-14T16:00:00Z",
            start="2025-06-30", end="2025-04-01",
        ))
    assert caught.value.code == "PERIOD_ORDER"


def test_a16_correction_supersedes_and_bytes_unchanged(tmp_path):
    store_path = tmp_path / "twin.jsonl"
    store = TwinStore(store_path)
    gen1 = _record()
    status, _ = store.write_with_ack(gen1)
    assert status == "ACKED"
    before = store_path.read_bytes()
    line1 = before.splitlines()[0]

    gen2_payload = _payload("synthetic_restatement")
    gen2 = _record(
        payload=gen2_payload,
        clocks=_clocks("2025-08-16T08:00:00Z", "2025-08-16T09:00:00Z"),
        prev=gen1,
        correction_reason="synthetic restatement of the same economic period",
    )
    assert gen2["generation"] == 2
    assert gen2["supersedes"] == gen1["record_id"]
    assert gen2["clocks"]["economic_period"] == gen1["clocks"]["economic_period"]
    status, _ = store.write_with_ack(gen2)
    assert status == "ACKED"
    after = store_path.read_bytes()
    assert after.splitlines()[0] == line1
    assert verify_chain(store_path) == []


def test_a16_correction_without_reason_refused():
    gen1 = _record()
    with pytest.raises(TwinRefused) as caught:
        _record(prev=gen1, correction_reason=None)
    assert caught.value.code == "CORRECTION_REASON_REQUIRED"


def test_a05_two_corrections_chain(tmp_path):
    store_path = tmp_path / "twin.jsonl"
    store = TwinStore(store_path)
    gen1 = _record()
    store.write_with_ack(gen1)
    gen2 = _record(
        payload=_payload("synthetic_restatement"),
        clocks=_clocks("2025-08-16T08:00:00Z", "2025-08-16T09:00:00Z"),
        prev=gen1,
        correction_reason="first synthetic restatement",
    )
    store.write_with_ack(gen2)
    gen3 = _record(
        payload=_payload("synthetic_second_restatement"),
        clocks=_clocks("2025-08-18T08:00:00Z", "2025-08-18T10:00:00Z"),
        prev=gen2,
        correction_reason="second synthetic restatement",
    )
    store.write_with_ack(gen3)
    rows = history(store_path, TWIN_KEY)
    assert len(rows) == 3
    assert [row["generation"] for row in rows] == [1, 2, 3]
    assert rows[1]["supersedes"] == gen1["record_id"]
    assert rows[2]["supersedes"] == gen2["record_id"]
    tip = latest(store_path, TWIN_KEY)
    assert tip["generation"] == 3
    assert tip["record_id"] == gen3["record_id"]
    assert verify_chain(store_path) == []


def test_a07_view_as_of_then_known(tmp_path):
    store_path = tmp_path / "twin.jsonl"
    store = TwinStore(store_path)
    gen1 = _record(clocks=_clocks("2025-08-14T12:00:00Z", "2025-08-14T16:00:00Z"))
    store.write_with_ack(gen1)
    gen2 = _record(
        payload=_payload("synthetic_restatement"),
        clocks=_clocks("2025-08-16T08:00:00Z", "2025-08-16T09:00:00Z"),
        prev=gen1,
        correction_reason="synthetic restatement",
    )
    store.write_with_ack(gen2)

    between = view_as_of(store_path, TWIN_KEY, "2025-08-15T12:00:00Z")
    assert between is not None
    assert between["generation"] == 1
    assert between["record_id"] == gen1["record_id"]

    after = view_as_of(store_path, TWIN_KEY, "2025-08-16T12:00:00Z")
    assert after is not None
    assert after["generation"] == 2
    assert after["record_id"] == gen2["record_id"]

    before = view_as_of(store_path, TWIN_KEY, "2025-08-01T00:00:00Z")
    assert before is None


def test_a17_effect_unknown_reconcile_present(tmp_path):
    store_path = tmp_path / "twin.jsonl"
    store = TwinStore(store_path)

    def boom():
        raise IOError("simulated crash after write")

    store._after_write_hook = boom
    rec = _record()
    status, row_hash = store.write_with_ack(rec)
    assert status == "EFFECT_UNKNOWN"
    assert row_hash is None
    assert store.reconcile(rec["record_id"]) == "PRESENT"
    assert verify_chain(store_path) == []


def test_tamper_middle_line_hash_violation(tmp_path):
    store_path = tmp_path / "twin.jsonl"
    store = TwinStore(store_path)
    gen1 = _record()
    store.write_with_ack(gen1)
    gen2 = _record(
        payload=_payload("synthetic_restatement"),
        clocks=_clocks("2025-08-16T08:00:00Z", "2025-08-16T09:00:00Z"),
        prev=gen1,
        correction_reason="first synthetic restatement",
    )
    store.write_with_ack(gen2)
    gen3 = _record(
        payload=_payload("synthetic_second_restatement"),
        clocks=_clocks("2025-08-18T08:00:00Z", "2025-08-18T10:00:00Z"),
        prev=gen2,
        correction_reason="second synthetic restatement",
    )
    store.write_with_ack(gen3)

    lines = store_path.read_text(encoding="utf-8").splitlines()
    middle = json.loads(lines[1])
    middle["payload"]["metric"] = "tampered"
    lines[1] = json.dumps(middle, sort_keys=True, separators=(",", ":"))
    store_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    violations = verify_chain(store_path)
    assert any("hash" in item.lower() for item in violations)


def test_authority_key_in_payload_refused():
    payload = _payload()
    payload["rank_authority"] = False
    with pytest.raises(TwinRefused) as caught:
        _record(payload=payload)
    assert caught.value.code == "AUTHORITY_KEY_IN_PAYLOAD"


def test_authority_flag_true_refused(tmp_path):
    rec = _record()
    rec["authority_flags"]["trade_authority"] = True
    store = TwinStore(tmp_path / "twin.jsonl")
    with pytest.raises(TwinRefused) as caught:
        store.append(rec)
    assert caught.value.code == "AUTHORITY_FLAG_TRUE"


def test_schema_validation_if_jsonschema(tmp_path):
    jsonschema = pytest.importorskip("jsonschema")
    store_path = tmp_path / "twin.jsonl"
    store = TwinStore(store_path)
    rec = _record()
    status, _ = store.write_with_ack(rec)
    assert status == "ACKED"
    stored = json.loads(store_path.read_text(encoding="utf-8").splitlines()[0])
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.validate(stored, schema, format_checker=jsonschema.FormatChecker())


def test_refusal_codes_in_doc_match_module():
    module_text = MODULE_PATH.read_text(encoding="utf-8")
    doc_text = DOC_PATH.read_text(encoding="utf-8")
    first_para = doc_text.split("\n\n", 1)[1] if "\n\n" in doc_text else doc_text
    assert "R1-gated DRAFT" in first_para.split("\n\n")[0]
    for code in REFUSAL_CODES:
        assert code in module_text
        assert code in doc_text
