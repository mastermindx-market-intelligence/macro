"""Real B1 compatibility proof for the prospective optional receipt column."""
import json
from hashlib import sha256
from pathlib import Path
import shutil
import pandas as pd
import pytest
from engine import us_candidate_episode_intake as intake
from engine.us_candidate_episode import EpisodeContractError
from engine.us_candidate_episode import canonical_json, load_candidate_episode_store_snapshot
from engine.us_candidate_episode_intake import candidate_source_row
from scripts import reconcile_us_candidate_episodes as writer

FIXTURE_ROOT = Path(__file__).parent / "fixtures/us_candidate_episode/intake"


def test_null_schema_union_retains_real_native_source_key(tmp_path, monkeypatch):
    data = tmp_path / "data"
    reference = data / "reference"
    reference.mkdir(parents=True)
    for name in ("security_master", "vendor_aliases"):
        pd.DataFrame(json.loads((FIXTURE_ROOT / (name + ".json")).read_text())).to_parquet(reference / (name + ".parquet"), index=False)
    turn = data / "us_prophet_rank/episode_inputs/turn_watch/2026-11-27.json"
    turn.parent.mkdir(parents=True)
    shutil.copyfile(FIXTURE_ROOT / "turn_watch.json", turn)
    candidate = data / "us_prophet_rank/candidates/2026-11.parquet"
    candidate.parent.mkdir(parents=True)
    row = {"stamp_date": "2026-11-27", "ticker": "ALFA", "board_definition": "us_prophet_v3", "tier": "curated"}
    pd.DataFrame([row]).to_parquet(candidate, index=False)
    monkeypatch.setattr(writer, "nightly_advance_enabled", lambda: True)
    writer.reconcile(repo_root=tmp_path, nightly=True, replay=False, recorded_at="2026-11-27T18:05:00Z", correction_path=None)
    episode_root = data / "us_prophet_rank/episodes"
    before = load_candidate_episode_store_snapshot(episode_root)
    pd.DataFrame([{**row, "today_selection_row_receipt": None}]).to_parquet(candidate, index=False)
    writer.reconcile(repo_root=tmp_path, nightly=True, replay=False, recorded_at="2026-11-27T18:06:00Z", correction_path=None)
    after = load_candidate_episode_store_snapshot(episode_root)
    assert after.generation.events == before.generation.events
    assert after.generation.suppressions == before.generation.suppressions
    assert after.generation.episodes == before.generation.episodes
    assert candidate_source_row({**row, "today_selection_row_receipt": None}) == row
    # Reverting the reader after schema union is unsafe even with emission off.
    retained_head = (episode_root / "HEAD.json").read_bytes()
    with monkeypatch.context() as legacy:
        legacy.setattr(intake, "candidate_source_row", intake._plain_row)
        with pytest.raises(EpisodeContractError, match="ordinary source key reused"):
            writer.reconcile(repo_root=tmp_path, nightly=True, replay=False, recorded_at="2026-11-27T18:07:00Z", correction_path=None)
    assert (episode_root / "HEAD.json").read_bytes() == retained_head
    # A functional rollback with the compatibility reader retained is safe.
    writer.reconcile(repo_root=tmp_path, nightly=True, replay=False, recorded_at="2026-11-27T18:08:00Z", correction_path=None)
    rolled_back = load_candidate_episode_store_snapshot(episode_root)
    assert rolled_back.generation.events == before.generation.events
    assert rolled_back.generation.suppressions == before.generation.suppressions


def test_candidate_wrapper_preserves_other_nulls_and_malformed_receipt():
    row = {"ticker": "ALFA", "unknown_field": None}
    assert candidate_source_row(row) == row
    assert candidate_source_row({**row, "today_selection_row_receipt": pd.NA}) == row
    assert candidate_source_row({**row, "today_selection_row_receipt": float("nan")}) == row
    assert candidate_source_row({**row, "today_selection_row_receipt": None}) == row
    malformed = {**row, "today_selection_row_receipt": "malformed"}
    assert candidate_source_row(malformed) == malformed
    assert sha256(canonical_json(candidate_source_row(malformed)).encode()).digest() != sha256(canonical_json(row).encode()).digest()

from datetime import datetime as RealDatetime, timezone
from scripts import build_stock_library as producer
from engine import us_context_vector as context_owner


class ReadClock(RealDatetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 11, 27, 18, 8, tzinfo=timezone.utc)


def _native_today(tmp_path, monkeypatch, *, duplicate=False):
    monkeypatch.setattr(producer, "datetime", ReadClock)
    monkeypatch.setattr(writer, "nightly_advance_enabled", lambda: True)
    reference = tmp_path / "data/reference"
    reference.mkdir(parents=True)
    for name in ("security_master", "vendor_aliases"):
        pd.DataFrame(json.loads((FIXTURE_ROOT / (name + ".json")).read_text())).to_parquet(reference / (name + ".parquet"), index=False)
    turn = tmp_path / "data/us_prophet_rank/episode_inputs/turn_watch/2026-11-27.json"
    turn.parent.mkdir(parents=True)
    shutil.copyfile(FIXTURE_ROOT / "turn_watch.json", turn)
    writer.reconcile(repo_root=tmp_path, nightly=True, replay=False,
                     recorded_at="2026-11-27T18:05:00Z", correction_path=None)
    row = {"ticker": "ALFA", "price": 42.0, "featured": True}
    doc = {"as_of": "2026-11-27", "board_definition": "us_prophet_v3",
           "emit": {"pair_id": "1" * 32, "at_utc": "2026-11-27T18:02:00+00:00"},
           "buy": [row, dict(row)] if duplicate else [row]}
    source = tmp_path / "site/factordata/us_standouts.json"
    source.parent.mkdir(parents=True)
    source.write_text(json.dumps(doc, separators=(",", ":")))
    receipts = producer.today_selection_row_receipts(source.read_bytes())
    records = context_owner.build_records({"ALFA": {}}, stamp_date="2026-11-27",
                                         board_definition="us_prophet_v3", is_buyable=lambda _: False,
                                         today_selection_row_receipts=receipts)
    candidate = tmp_path / "data/us_prophet_rank/candidates/2026-11.parquet"
    candidate.parent.mkdir(parents=True)
    pd.DataFrame(records).to_parquet(candidate, index=False)
    return source, candidate


def _read_today(tmp_path, source, **pins):
    binding = producer.today_selection_source_binding(source.read_bytes())
    args = {"expected_source_sha256": binding["source_sha256"], "expected_pair_id": binding["pair_id"],
            "expected_selection_receipt": binding["selection_receipt"]}
    args.update(pins)
    return producer.read_today_candidate_projection(tmp_path, **args)


def test_native_pending_then_ordinary_reread_without_publication_mutation(tmp_path, monkeypatch):
    source, _candidate = _native_today(tmp_path, monkeypatch)
    raw = source.read_bytes()
    pending = _read_today(tmp_path, source)
    assert pending["status"] == "PARTIAL"
    assert pending["candidates"][0]["reason_codes"] == ["CANDIDATE_RECONCILIATION_PENDING"]
    writer.reconcile(repo_root=tmp_path, nightly=True, replay=False,
                     recorded_at="2026-11-27T18:06:00Z", correction_path=None)
    head_before = (tmp_path / "data/us_prophet_rank/episodes/HEAD.json").read_bytes()
    ready = _read_today(tmp_path, source)
    assert ready["status"] == "PARTIAL"
    item = ready["candidates"][0]
    assert item["status"] == "AVAILABLE"
    actual = load_candidate_episode_store_snapshot(tmp_path / "data/us_prophet_rank/episodes")
    candidate = item["candidate_input"]
    assert candidate["candidate_generation_id"] == actual.generation_id
    episode = next(ep for ep in actual.generation.episodes if ep["episode_id"] == candidate["episode_id"])
    assert candidate["security_id"] == episode["security_id"]
    assert candidate["market_session"] == "2026-11-27"
    assert candidate["asof"] == "2026-11-27T18:08:00Z"
    assert "B4_NATIVE_OWNER_READ_UNAVAILABLE" in item["reason_codes"]
    assert item["daily_brief"]["presentation"]["assessment"] is None
    assert source.read_bytes() == raw
    assert (tmp_path / "data/us_prophet_rank/episodes/HEAD.json").read_bytes() == head_before


def test_duplicate_positions_preserved_and_changed_current_row_does_not_inherit_binding(tmp_path, monkeypatch):
    source, _candidate = _native_today(tmp_path, monkeypatch, duplicate=True)
    writer.reconcile(repo_root=tmp_path, nightly=True, replay=False,
                     recorded_at="2026-11-27T18:06:00Z", correction_path=None)
    ready = _read_today(tmp_path, source)
    assert [item["selection_index"] for item in ready["candidates"]] == [0, 1]
    assert all(item["status"] == "AVAILABLE" for item in ready["candidates"])
    old_binding = producer.today_selection_source_binding(source.read_bytes())
    doc = json.loads(source.read_bytes())
    doc["buy"][0]["price"] = 99.0
    source.write_text(json.dumps(doc, separators=(",", ":")))
    stale_shell = _read_today(tmp_path, source, expected_source_sha256=old_binding["source_sha256"])
    assert stale_shell["reason_codes"] == ["SOURCE_BINDING_MISMATCH"]
    corrected = _read_today(tmp_path, source)
    assert corrected["candidates"][0]["reason_codes"] == ["ROW_PROVENANCE_MISMATCH"]
    assert corrected["candidates"][0]["candidate_input"] is None
    assert corrected["candidates"][1]["status"] == "AVAILABLE"
    assert "ALFA" not in producer.today_selection_row_receipts(source.read_bytes())


def test_exact_binding_pins_and_generation_pin_fail_without_retry(tmp_path, monkeypatch):
    source, _candidate = _native_today(tmp_path, monkeypatch)
    assert _read_today(tmp_path, source, expected_pair_id="2" * 32)["reason_codes"] == ["SOURCE_BINDING_MISMATCH"]
    assert _read_today(tmp_path, source, expected_selection_receipt="sha256:" + "0" * 64)["reason_codes"] == ["SELECTION_BINDING_MISMATCH"]
    assert _read_today(tmp_path, source, expected_candidate_generation_id="peg:" + "0" * 64)["reason_codes"] == ["CANDIDATE_GENERATION_MISMATCH"]


def test_source_reader_schema_union_and_unreadable_part_refuse_partial_binding(tmp_path, monkeypatch):
    source, candidate = _native_today(tmp_path, monkeypatch)
    frame = pd.read_parquet(candidate)
    old = {"stamp_date": "2026-11-26", "ticker": "ALFA", "board_definition": "us_prophet_v3"}
    pd.concat([pd.DataFrame([old]), frame], ignore_index=True).to_parquet(candidate, index=False)
    rows, receipts = context_owner.read_today_candidate_source_rows(tmp_path)
    assert "today_selection_row_receipt" not in rows[0]
    assert rows[1]["today_selection_row_receipt"].startswith("sha256:")
    assert receipts[0]["sha256"] == "sha256:" + sha256(candidate.read_bytes()).hexdigest()
    (candidate.parent / "2026-10.parquet").write_bytes(b"corrupt")
    assert _read_today(tmp_path, source)["reason_codes"] == ["CANDIDATE_SNAPSHOT_UNAVAILABLE"]


@pytest.mark.parametrize("race", ["added_part", "deleted_part", "changed_part", "changed_source", "b1_head"])
def test_request_snapshot_race_discards_all_native_inputs(tmp_path, monkeypatch, race):
    source, candidate = _native_today(tmp_path, monkeypatch)
    real = context_owner.read_today_candidate_source_rows
    reads = []

    def captured(root):
        reads.append(root)
        if len(reads) == 2:
            if race == "added_part":
                pd.DataFrame([{"stamp_date": "2026-10-01"}]).to_parquet(candidate.parent / "2026-10.parquet", index=False)
            elif race == "deleted_part":
                candidate.unlink()
            elif race == "changed_part":
                frame = pd.read_parquet(candidate)
                frame["extra_provenance"] = "changed"
                frame.to_parquet(candidate, index=False)
            elif race == "changed_source":
                source.write_bytes(source.read_bytes() + b" ")
            else:
                writer.reconcile(repo_root=tmp_path, nightly=True, replay=False,
                                 recorded_at="2026-11-27T18:07:00Z", correction_path=None)
        return real(root)

    monkeypatch.setattr(context_owner, "read_today_candidate_source_rows", captured)
    result = _read_today(tmp_path, source)
    assert result["status"] == "UNAVAILABLE"
    assert result["candidates"] == []
    assert len(reads) == 2


def test_duplicate_source_records_cannot_attest_a_single_native_candidate(tmp_path, monkeypatch):
    source, candidate = _native_today(tmp_path, monkeypatch)
    frame = pd.read_parquet(candidate)
    pd.concat([frame, frame], ignore_index=True).to_parquet(candidate, index=False)
    result = _read_today(tmp_path, source)
    assert result["candidates"][0]["reason_codes"] == ["CANDIDATE_SOURCE_AMBIGUOUS"]


def test_default_receipt_emission_remains_absent():
    records = context_owner.build_records({"ALFA": {}}, stamp_date="2026-11-27",
                                         board_definition="us_prophet_v3", is_buyable=lambda _: False)
    assert "today_selection_row_receipt" not in records[0]


@pytest.mark.parametrize("clock", [None, "garbage", "2026-11-27T19:00:00+00:00", "2026-11-27T18:02:00"])
def test_original_selection_clock_cannot_be_fabricated_or_renewed(tmp_path, monkeypatch, clock):
    source, _candidate = _native_today(tmp_path, monkeypatch)
    doc = json.loads(source.read_bytes())
    doc["emit"]["at_utc"] = clock
    source.write_text(json.dumps(doc))
    raw = source.read_bytes()
    from engine.us_candidate_episode import canonical_json
    # The receipt helper need not accept a malformed source; use exact wrong-pin
    # placeholders to invoke the actual reader before any native input is issued.
    result = producer.read_today_candidate_projection(tmp_path,
        expected_source_sha256="sha256:" + sha256(raw).hexdigest(),
        expected_pair_id=doc["emit"]["pair_id"], expected_selection_receipt="sha256:" + "0" * 64)
    assert result["status"] == "UNAVAILABLE"
    assert result["reason_codes"] == ["SELECTION_SOURCE_UNAVAILABLE"]


def test_full_buy_non_featured_row_uses_original_producer_receipt(tmp_path, monkeypatch):
    source, candidate = _native_today(tmp_path, monkeypatch)
    doc = json.loads(source.read_bytes())
    doc["buy"][0]["featured"] = False
    source.write_text(json.dumps(doc, separators=(",", ":")))
    receipts = producer.today_selection_row_receipts(source.read_bytes())
    records = context_owner.build_records({"ALFA": {}}, stamp_date="2026-11-27",
        board_definition="us_prophet_v3", is_buyable=lambda _: False,
        today_selection_row_receipts=receipts)
    pd.DataFrame(records).to_parquet(candidate, index=False)
    writer.reconcile(repo_root=tmp_path, nightly=True, replay=False,
        recorded_at="2026-11-27T18:06:00Z", correction_path=None)
    result = _read_today(tmp_path, source)
    assert len(result["candidates"]) == 1
    assert result["candidates"][0]["selection_index"] == 0
    assert result["candidates"][0]["status"] == "AVAILABLE"


def test_changed_native_source_digest_cannot_inherit_old_key_binding(tmp_path, monkeypatch):
    source, candidate = _native_today(tmp_path, monkeypatch)
    writer.reconcile(repo_root=tmp_path, nightly=True, replay=False,
        recorded_at="2026-11-27T18:06:00Z", correction_path=None)
    frame = pd.read_parquet(candidate)
    frame["native_observation_correction"] = "new bytes"
    frame.to_parquet(candidate, index=False)
    result = _read_today(tmp_path, source)
    assert result["candidates"][0]["candidate_input"] is None
    assert result["candidates"][0]["reason_codes"] == ["CANDIDATE_RECONCILIATION_PENDING"]


def test_displayed_receipt_classification_does_not_claim_w3c_capture(tmp_path, monkeypatch):
    source, _ = _native_today(tmp_path, monkeypatch)
    binding = producer.today_selection_source_binding(source.read_bytes())
    material = {key: binding[key] for key in ("source_sha256", "pair_id", "market_session", "ordered_rows")}
    assert binding["selection_receipt"] == "sha256:" + sha256(canonical_json(material).encode()).hexdigest()
    assert binding["schema"] == "prophet.today_selection_source_binding/v1"
    assert binding["receipt_kind"] == "EXACT_DISPLAYED_SOURCE"
    result = _read_today(tmp_path, source)
    assert result["source_binding"]["schema"] == binding["schema"]
    assert result["source_binding"]["receipt_kind"] == binding["receipt_kind"]
    assert result["status"] == "PARTIAL"
