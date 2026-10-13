"""Deterministic Gate-S verifier for Q06 comparable-revenue source contract v0.2.

No network, market outcomes, ranks, trades or mutable production state are read.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


HERE = Path(__file__).resolve()
ROOT = HERE.parents[4]
CONTRACT = HERE.with_name("q06_sec_comparable_revenue_source_contract.v0_2.json")
FIXTURE = ROOT / "tests/fixtures/company_intelligence/aapl_fy2026_q3_ex99_1.htm"
RIGHTS = ROOT / "research/licenses/PROPHET_US_SOURCE_RIGHTS_REGISTER_2026-09-23.md"

EXPECTED_FIXTURE_SHA256 = "070abd6a9cdb7070e546d24ffcbc41c65450d939c6f88f189cb18ec711cf5fdb"
EXPECTED_RIGHTS_BLOB = "a9ee6f288bfb2716facd88dcf2c5135ca8125303"
EXPECTED_FIELD_ID = "fpv:36091b7aff3681e59ab527eb3ebeac61a20324195a9f43f4478c4ccbcff1566a"
EXPECTED_ECONOMIC_ID = "econ:50d783276670de14acd15a92317b93649d877c01f7d48961d1c56e5e7c87a656"
WRAPPER_RE = re.compile(
    br'<script type="text/javascript"  src="/_[A-Za-z0-9/_-]+"></script>(?=</body>)'
)


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def git_blob(raw: bytes) -> str:
    return hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest()


def canonical_hash(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return sha256(raw)


def load_contract() -> dict:
    return json.loads(CONTRACT.read_text())


def verify() -> dict:
    contract = load_contract()
    fixture = FIXTURE.read_bytes()
    assert sha256(fixture) == EXPECTED_FIXTURE_SHA256
    assert git_blob(RIGHTS.read_bytes()) == EXPECTED_RIGHTS_BLOB

    economic = dict(contract["economic_identity"])
    economic_id = economic.pop("economic_id")
    assert economic_id == EXPECTED_ECONOMIC_ID
    assert "econ:" + canonical_hash(economic) == economic_id
    expected = (109417 / 94036 - 1) * 100
    assert economic["value_pct"] == expected

    provenance = dict(contract["field_provenance"])
    provenance_id = provenance.pop("field_provenance_id")
    assert provenance_id == EXPECTED_FIELD_ID
    assert "fpv:" + canonical_hash(provenance) == provenance_id

    current = provenance["current_span"]
    prior = provenance["prior_span"]
    current_raw = fixture[current["start"]:current["end"]]
    prior_raw = fixture[prior["start"]:prior["end"]]
    assert current_raw == b"109,417"
    assert prior_raw == b"94,036"
    assert sha256(current_raw) == current["text_sha256"]
    assert sha256(prior_raw) == prior["text_sha256"]
    assert provenance["table"]["title"].encode() in fixture
    assert b"Three Months Ended" in fixture

    witness = contract["normalization"]["current_recheck_2026_09_29"]
    wrapper = witness["wrapper_text"].encode()
    assert sha256(wrapper) == witness["wrapper_sha256"]
    # The SEC response inserts the wrapper after the '<' that starts the frozen
    # closing body tag, so the raw byte delta is wrapper[1:] + b'<'.
    delta = wrapper[1:] + b"<"
    assert len(delta) == witness["wrapper_bytes"]
    offset = witness["insertion_offset"]
    synthetic_raw = fixture[:offset] + delta + fixture[offset:]
    assert len(synthetic_raw) == witness["raw_envelope_bytes"]
    assert sha256(synthetic_raw) == witness["raw_envelope_sha256"]
    normalized, count = WRAPPER_RE.subn(b"", synthetic_raw)
    assert count == 1
    assert normalized == fixture
    assert sha256(normalized) == witness["normalized_sha256"]

    objects = contract["historical_envelope_identities"]["source_objects_oldest_first"]
    assert len(objects) == 10
    assert len({row["fetched_envelope_sha256"] for row in objects}) == 10
    assert all(row["issuer_body_revision_claim"] is False for row in objects)
    assert objects[0]["classification"] == "BASELINE_ENVELOPE_EQUALS_FROZEN_NORMALIZED_BODY"
    assert all(
        row["classification"] == "UNEXPLAINED_SUPPLIED_ENVELOPE_IDENTITY"
        for row in objects[1:]
    )

    assert contract["gate_s"]["state"] == "REPAIRED_PENDING_PARENT_ACCEPTANCE"
    assert contract["gate_e"]["state"] == "NOT_REGISTERED_PREPARATORY_ONLY"
    assert contract["gate_e"]["protected_outcome_read"] is False
    assert contract["gate_e"]["trial_may_start"] is False
    assert contract["downstream"]["d5_adapter_edit_authorized"] is False
    assert contract["downstream"]["packet3_trial_authorized"] is False
    assert contract["downstream"]["rank_change_authorized"] is False
    assert contract["downstream"]["user_entry_authorized"] is False
    assert all(value is False for value in contract["authority"].values())

    return {
        "schema": contract["schema"],
        "economic_id": economic_id,
        "field_provenance_id": provenance_id,
        "feature_value_pct": expected,
        "historical_envelope_identities": len(objects),
        "normalization_witness_raw_sha256": witness["raw_envelope_sha256"],
        "normalization_witness_normalized_sha256": witness["normalized_sha256"],
        "gate_s": contract["gate_s"]["state"],
        "gate_e": contract["gate_e"]["state"],
        "authority_all_false": True,
    }


def main() -> int:
    print(json.dumps(verify(), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
