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
from copy import deepcopy
from scripts import build_stock_library as producer
from engine import prophet_candidate_state as b3_owner
from engine import us_context_vector as context_owner


class ReadClock(RealDatetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 11, 27, 18, 8, tzinfo=timezone.utc)


class CompletionClock(RealDatetime):
    """Real read shape: one request-start observation, then one completion."""

    _reads = 0

    @classmethod
    def now(cls, tz=None):
        cls._reads += 1
        if cls._reads == 1:
            return cls(2026, 11, 27, 18, 8, 0, tzinfo=timezone.utc)
        return cls(2026, 11, 27, 18, 8, 30, tzinfo=timezone.utc)


def _set_native_clocks(monkeypatch, read_clock=ReadClock):
    """Pin the producer read clock AND the B3 owner assembly clock explicitly."""
    monkeypatch.setattr(producer, "datetime", read_clock)
    monkeypatch.setattr(b3_owner, "_assembly_now", lambda: read_clock.now())


def _native_today(tmp_path, monkeypatch, *, duplicate=False):
    _set_native_clocks(monkeypatch)
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


BETA_IDENTITY = {
    "security_master": {"issuer_id": "ISS:US-XNAS-BETA", "issuer_state": "ACTIVE",
                        "listing_key": "US-XNAS-BETA", "security_id": "SEC:US-XNAS-BETA"},
    "vendor_aliases": {"security_id": "SEC:US-XNAS-BETA", "valid_from": "2020-01-01",
                       "valid_to": None, "vendor": "membership", "vendor_symbol": "BETA"},
}


def _turn_watch_document(session, tickers=("ALFA",), *, reset_date="2026-11-27", reset_low=42.1):
    """Generation-local TURN WATCH source for every requested ticker."""
    document = {"schema": "prophet.candidate_episode_input.turn_watch/v1",
                "anchor_era": "anchor-v1", "selection_era": "anticipation-v1",
                "data_session": session, "known_at": session + "T18:00:00Z",
                "rows": [{"asof": session, "ticker": ticker,
                          "reset": {"reset_low": reset_low, "reset_low_date": reset_date},
                          "triggers": {"dot_1d": {"evaluated": True, "fired": True, "last_date": session}}}
                         for ticker in tickers]}
    document["content_sha256"] = sha256(canonical_json(
        {key: value for key, value in document.items() if key != "content_sha256"}).encode()).hexdigest()
    return document


def _native_today_multi(tmp_path, monkeypatch, *, tickers=("ALFA", "BETA"),
                        final_recorded_at="2026-11-27T18:06:00Z"):
    """Real native store with one source-keyed candidate per requested ticker."""
    _set_native_clocks(monkeypatch)
    monkeypatch.setattr(writer, "nightly_advance_enabled", lambda: True)
    reference = tmp_path / "data/reference"
    reference.mkdir(parents=True)
    for name in ("security_master", "vendor_aliases"):
        rows = json.loads((FIXTURE_ROOT / (name + ".json")).read_text())
        rows.append(BETA_IDENTITY[name])
        pd.DataFrame(rows).to_parquet(reference / (name + ".parquet"), index=False)
    turn = tmp_path / "data/us_prophet_rank/episode_inputs/turn_watch/2026-11-27.json"
    turn.parent.mkdir(parents=True)
    turn.write_text(canonical_json(_turn_watch_document("2026-11-27", tickers)) + "\n")
    writer.reconcile(repo_root=tmp_path, nightly=True, replay=False,
                     recorded_at="2026-11-27T18:05:00Z", correction_path=None)
    doc = {"as_of": "2026-11-27", "board_definition": "us_prophet_v3",
           "emit": {"pair_id": "1" * 32, "at_utc": "2026-11-27T18:02:00+00:00"},
           "buy": [{"ticker": ticker, "price": 42.0, "featured": True} for ticker in tickers]}
    source = tmp_path / "site/factordata/us_standouts.json"
    source.parent.mkdir(parents=True)
    source.write_text(json.dumps(doc, separators=(",", ":")))
    receipts = producer.today_selection_row_receipts(source.read_bytes())
    records = context_owner.build_records({ticker: {} for ticker in tickers},
                                         stamp_date="2026-11-27",
                                         board_definition="us_prophet_v3", is_buyable=lambda _: False,
                                         today_selection_row_receipts=receipts)
    candidate = tmp_path / "data/us_prophet_rank/candidates/2026-11.parquet"
    candidate.parent.mkdir(parents=True)
    pd.DataFrame(records).to_parquet(candidate, index=False)
    writer.reconcile(repo_root=tmp_path, nightly=True, replay=False,
                     recorded_at=final_recorded_at, correction_path=None)
    return source, candidate


def _episode_root(tmp_path):
    return tmp_path / "data/us_prophet_rank/episodes"


def _native_relation(snapshot, source_event_id):
    for event in snapshot.generation.events:
        if event.get("source_event_id") == source_event_id:
            return event
    raise AssertionError(f"no native relation for {source_event_id}")


def _source_key(ticker, session="2026-11-27", board="us_prophet_v3"):
    return f"candidate:{session}:{ticker}:{board}"


def _write_corrections(root, commands):
    path = root / "corrections.jsonl"
    path.write_text("".join(canonical_json(command) + "\n" for command in commands))
    return path


def _counting_owner_factory(monkeypatch):
    """Wrap the real owner factory so the consumer's exact calls are observable."""
    calls = []
    real = b3_owner.build_native_factual_assessment_result

    def counted(snapshot, *, candidate_source_event_id, candidate_source_receipt):
        calls.append({"generation_id": snapshot.generation_id,
                      "candidate_source_event_id": candidate_source_event_id,
                      "candidate_source_receipt": candidate_source_receipt})
        return real(snapshot, candidate_source_event_id=candidate_source_event_id,
                    candidate_source_receipt=candidate_source_receipt)

    monkeypatch.setattr(b3_owner, "build_native_factual_assessment_result", counted)
    return calls


def _genuine_pair(root, source_event_id):
    snapshot = load_candidate_episode_store_snapshot(_episode_root(root))
    relation = _native_relation(snapshot, source_event_id)
    result = b3_owner.build_native_factual_assessment_result(
        snapshot, candidate_source_event_id=source_event_id,
        candidate_source_receipt=relation["source_receipt"])
    return result, snapshot, relation


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
    assert "ASSESSMENT_NATIVE_OWNER_READ_UNAVAILABLE" not in item["reason_codes"]
    presented = item["daily_brief"]["presentation"]["assessment"]
    assert presented["assessment_state"] == "REVIEW_REQUIRED"
    assert item["daily_brief"]["owners"]["assessment"]["state"] == "REVIEW_REQUIRED"
    assert "FUTURE_OWNER_CLOCK" not in item["daily_brief"]["issues"]
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


# ---------------------------------------------------------------------------
# Same-read native factual assessment consumption. Every owner input below comes
# from one genuine `build_native_factual_assessment_result` read over the real
# native store: the consumer only verifies and presents it, never rebuilds it.
# ---------------------------------------------------------------------------


def _ready_candidate(tmp_path, monkeypatch):
    source = _native_today(tmp_path, monkeypatch)[0]
    writer.reconcile(repo_root=tmp_path, nightly=True, replay=False,
                     recorded_at="2026-11-27T18:06:00Z", correction_path=None)
    return _read_today(tmp_path, source)["candidates"][0]


def test_native_assessment_is_bound_from_one_genuine_owner_read(tmp_path, monkeypatch):
    item = _ready_candidate(tmp_path, monkeypatch)
    candidate = item["candidate_input"]
    brief = item["daily_brief"]
    assert item["status"] == "AVAILABLE"
    # The read itself is no longer unavailable; the owners still owed are listed
    # literally and the aggregate stays at most PARTIAL.
    assert item["reason_codes"] == ["PLAN_NATIVE_OWNER_READ_UNAVAILABLE",
                                    "EVIDENCE_NATIVE_OWNER_READ_UNAVAILABLE",
                                    "QUOTE_NATIVE_OWNER_READ_UNAVAILABLE",
                                    "B4_NATIVE_OWNER_READ_UNAVAILABLE"]
    owner = brief["owners"]["assessment"]
    assert owner["owner_ref"] == b3_owner.ASSESSMENT_OWNER_REF
    assert owner["state"] == "REVIEW_REQUIRED"
    assert owner["source_receipt"].startswith("sha256:")
    presented = brief["presentation"]["assessment"]
    assert presented["assessment_state"] == "REVIEW_REQUIRED"
    assert presented["maturity_state"] == "UNESTIMABLE"
    assert presented["model_thesis"] == "UNAVAILABLE"
    assert presented["review_lineage"] == "UNAVAILABLE"
    assert presented["review_ref"] is None
    assert presented["b4_native_owner_read"] == "B4_NATIVE_OWNER_READ_UNAVAILABLE"
    assert presented["source_freshness"] == "NOT_RENEWED_BY_ASOF"
    # The assessment stays one bound owner read of this exact candidate, and no
    # clock moved: request start, owner assembly and completion are all visible
    # separately and none of them is in the future of another.
    assert brief["clocks"]["assessment"] == candidate["asof"]
    assert "FUTURE_OWNER_CLOCK" not in brief["issues"]
    assert "MALFORMED_OWNER_CLOCK" not in brief["issues"]
    identity = ("security_id", "episode_id", "candidate_generation_id", "market_session")
    assert brief["identity"] == {field: candidate[field] for field in identity}


def test_response_aggregate_stays_partial_and_plan_stays_unavailable(tmp_path, monkeypatch):
    source, _candidate = _native_today(tmp_path, monkeypatch)
    writer.reconcile(repo_root=tmp_path, nightly=True, replay=False,
                     recorded_at="2026-11-27T18:06:00Z", correction_path=None)
    result = _read_today(tmp_path, source)
    assert result["status"] == "PARTIAL"
    assert result["reason_codes"] == ["DAILY_BRIEF_OWNER_INPUTS_UNAVAILABLE"]
    item = result["candidates"][0]
    brief = item["daily_brief"]
    assert brief["decision_state"] == "UNAVAILABLE"
    assert brief["authority"]["can_rank"] is False and brief["authority"]["can_trade"] is False
    assert brief["presentation"]["plan"] is None
    assert brief["presentation"]["availability"] is None
    assert brief["presentation"]["quote"]["state"] == "UNAVAILABLE"


def test_owner_factory_is_invoked_once_per_candidate_with_exact_binding(tmp_path, monkeypatch):
    source, _candidate = _native_today(tmp_path, monkeypatch)
    writer.reconcile(repo_root=tmp_path, nightly=True, replay=False,
                     recorded_at="2026-11-27T18:06:00Z", correction_path=None)
    calls = _counting_owner_factory(monkeypatch)
    snapshot = load_candidate_episode_store_snapshot(_episode_root(tmp_path))
    relation = _native_relation(snapshot, _source_key("ALFA"))
    _read_today(tmp_path, source)
    assert len(calls) == 1
    assert calls[0]["generation_id"] == snapshot.generation_id
    assert calls[0]["candidate_source_event_id"] == _source_key("ALFA")
    assert calls[0]["candidate_source_receipt"] == relation["source_receipt"]


def test_native_projection_stays_internal_and_response_shape_is_unchanged(tmp_path, monkeypatch):
    source, _candidate = _native_today(tmp_path, monkeypatch)
    writer.reconcile(repo_root=tmp_path, nightly=True, replay=False,
                     recorded_at="2026-11-27T18:06:00Z", correction_path=None)
    result = _read_today(tmp_path, source)
    item = result["candidates"][0]
    assert set(item) == {"selection_index", "row_receipt", "status", "candidate_input",
                         "daily_brief", "reason_codes", "native_provenance"}
    assert set(result) == {"schema", "status", "source_binding", "candidate_generation_id",
                           "generated_at", "candidates", "reason_codes"}
    snapshot = load_candidate_episode_store_snapshot(_episode_root(tmp_path))
    receipt = _native_relation(snapshot, _source_key("ALFA"))["source_receipt"]
    pair = b3_owner.build_native_factual_assessment_result(
        snapshot, candidate_source_event_id=_source_key("ALFA"), candidate_source_receipt=receipt)
    projection_id = pair.assessment["provenance"]["b3_projection_id"]
    assert projection_id.startswith("pcs:")
    assert projection_id not in json.dumps(result)
    assert pair.projection["projection_id"] not in json.dumps(result)
    assert pair.projection["projection_id"] == pair.assessment["provenance"]["b3_projection_id"]


def test_assessment_owner_failure_leaves_binding_available_without_a_fabricated_receipt(
    tmp_path, monkeypatch
):
    source, _candidate = _native_today(tmp_path, monkeypatch)
    writer.reconcile(repo_root=tmp_path, nightly=True, replay=False,
                     recorded_at="2026-11-27T18:06:00Z", correction_path=None)

    def refused(snapshot, *, candidate_source_event_id, candidate_source_receipt):
        raise b3_owner.CandidateStateContractError("native owner read refused")

    monkeypatch.setattr(b3_owner, "build_native_factual_assessment_result", refused)
    item = _read_today(tmp_path, source)["candidates"][0]
    assert item["status"] == "AVAILABLE"
    assert item["candidate_input"]["episode_id"]
    assert item["candidate_input"]["source_receipt"].startswith("sha256:")
    assert item["reason_codes"][0] == "ASSESSMENT_NATIVE_OWNER_READ_UNAVAILABLE"
    brief = item["daily_brief"]
    assert brief["presentation"]["assessment"] is None
    assert brief["owners"]["assessment"] is None
    assert "OWNER_INPUT_UNAVAILABLE" in brief["issues"]
    assert set(item) == {"selection_index", "row_receipt", "status", "candidate_input",
                         "daily_brief", "reason_codes", "native_provenance"}


def test_consumer_refuses_a_cross_bound_owner_result_per_candidate(tmp_path, monkeypatch):
    source, _candidate = _native_today_multi(tmp_path, monkeypatch)
    calls = []
    real = b3_owner.build_native_factual_assessment_result

    def swapped(snapshot, *, candidate_source_event_id, candidate_source_receipt):
        calls.append(candidate_source_event_id)
        other = (_source_key("BETA") if candidate_source_event_id == _source_key("ALFA")
                 else _source_key("ALFA"))
        relation = _native_relation(snapshot, other)
        return real(snapshot, candidate_source_event_id=other,
                    candidate_source_receipt=relation["source_receipt"])

    monkeypatch.setattr(b3_owner, "build_native_factual_assessment_result", swapped)
    result = _read_today(tmp_path, source)
    assert calls == [_source_key("ALFA"), _source_key("BETA")]
    for item in result["candidates"]:
        assert item["status"] == "AVAILABLE"
        assert item["candidate_input"] is not None
        assert item["reason_codes"][0] == "ASSESSMENT_NATIVE_BINDING_UNAVAILABLE"
        assert item["daily_brief"]["presentation"]["assessment"] is None


def _bound_candidate_and_pair(tmp_path, monkeypatch):
    source, _candidate = _native_today(tmp_path, monkeypatch)
    writer.reconcile(repo_root=tmp_path, nightly=True, replay=False,
                     recorded_at="2026-11-27T18:06:00Z", correction_path=None)
    result, snapshot, relation = _genuine_pair(tmp_path, _source_key("ALFA"))
    assessment, projection = result.verified_pair()
    candidate = {field: assessment[field] for field in (
        "security_id", "episode_id", "candidate_generation_id", "market_session")}
    return candidate, assessment, projection, relation


def test_consumer_refuses_every_per_field_native_mismatch(tmp_path, monkeypatch):
    candidate, assessment, projection, relation = _bound_candidate_and_pair(tmp_path, monkeypatch)
    receipt = relation["source_receipt"]
    key = _source_key("ALFA")

    def mutate(base, path, value):
        forged = deepcopy(base)
        target = forged
        for step in path[:-1]:
            target = target[step]
        target[path[-1]] = value
        return forged

    cases = {
        "security_id": lambda: (mutate(assessment, ["security_id"], "SEC:US-XNAS-BETA"), projection),
        "episode_id": lambda: (mutate(assessment, ["episode_id"], "pe:other"), projection),
        "candidate_generation_id": lambda: (
            mutate(assessment, ["candidate_generation_id"], "peg:" + "b" * 64), projection),
        "market_session": lambda: (mutate(assessment, ["market_session"], "2026-11-28"), projection),
        "owner_ref": lambda: (mutate(assessment, ["owner_ref"], "engine/other.py"), projection),
        "assessment_state": lambda: (
            mutate(assessment, ["summary", "assessment_state"], "CURRENT"), projection),
        "input_binding": lambda: (
            mutate(assessment, ["provenance", "input_binding", "candidate_source_receipt"],
                   "sha256:" + "1" * 64), projection),
        "matched_relation_key": lambda: (
            mutate(assessment, ["provenance", "matched_relation", "relation_source_event_id"],
                   _source_key("BETA")), projection),
        "matched_relation_receipt": lambda: (
            mutate(assessment, ["provenance", "matched_relation", "relation_source_receipt"],
                   "sha256:" + "2" * 64), projection),
        "projection_id": lambda: (assessment, mutate(projection, ["projection_id"], "pcs:" + "3" * 64)),
        "projection_digest": lambda: (
            assessment, mutate(projection, ["rows", 0, "episode_lifecycle", "state"], "RETRACTED")),
        "projection_generation": lambda: (
            assessment, mutate(projection, ["candidate_generation_id"], "peg:" + "c" * 64)),
        "projection_session": lambda: (assessment, mutate(projection, ["market_session"], "2026-11-28")),
        "projection_asof": lambda: (assessment, mutate(projection, ["generated_at"], "2026-11-27T18:09:00Z")),
        "projection_row": lambda: (assessment, mutate(projection, ["rows", 0, "episode_id"], "pe:other")),
    }
    for label, build in cases.items():
        forged_assessment, forged_projection = build()
        try:
            producer._verify_native_assessment_pair(
                forged_assessment, forged_projection, candidate=candidate,
                source_key=key, source_receipt=receipt)
        except producer._NativeAssessmentBindingRefused:
            continue
        raise AssertionError(f"binding check accepted a forged {label}")


def test_consumer_accepts_the_genuine_pair_it_was_handed(tmp_path, monkeypatch):
    candidate, assessment, projection, relation = _bound_candidate_and_pair(tmp_path, monkeypatch)
    producer._verify_native_assessment_pair(
        assessment, projection, candidate=candidate,
        source_key=_source_key("ALFA"), source_receipt=relation["source_receipt"])


def test_drifted_or_reblessed_owner_result_is_never_consumed(tmp_path, monkeypatch):
    source, _candidate = _native_today(tmp_path, monkeypatch)
    writer.reconcile(repo_root=tmp_path, nightly=True, replay=False,
                     recorded_at="2026-11-27T18:06:00Z", correction_path=None)
    genuine = _genuine_pair(tmp_path, _source_key("ALFA"))[0]
    real = b3_owner.build_native_factual_assessment_result

    def drifted():
        snapshot = load_candidate_episode_store_snapshot(_episode_root(tmp_path))
        relation = _native_relation(snapshot, _source_key("ALFA"))
        result = real(snapshot, candidate_source_event_id=_source_key("ALFA"),
                      candidate_source_receipt=relation["source_receipt"])
        result.assessment["asof"] = "2026-11-27T18:09:00Z"
        return result

    def reblessed():
        snapshot = load_candidate_episode_store_snapshot(_episode_root(tmp_path))
        relation = _native_relation(snapshot, _source_key("ALFA"))
        result = real(snapshot, candidate_source_event_id=_source_key("ALFA"),
                      candidate_source_receipt=relation["source_receipt"])
        result.assessment["provenance"]["b3_projection_id"] = "pcs:" + "f" * 64
        result.assessment["source_receipt"] = b3_owner._envelope_receipt(result.assessment)
        return result

    for factory in (drifted, reblessed):
        monkeypatch.setattr(b3_owner, "build_native_factual_assessment_result",
                            lambda snapshot, **kwargs: factory())
        item = _read_today(tmp_path, source)["candidates"][0]
        assert item["status"] == "AVAILABLE"
        assert item["reason_codes"][0] == "ASSESSMENT_NATIVE_OWNER_READ_UNAVAILABLE"
        assert item["daily_brief"]["presentation"]["assessment"] is None
    assert genuine.verified_pair()[0]["state"] == "REVIEW_REQUIRED"


def test_source_session_stays_original_while_opened_session_is_retained(tmp_path, monkeypatch):
    source, _candidate = _native_today_multi(
        tmp_path, monkeypatch, tickers=("ALFA",), final_recorded_at="2026-11-28T22:00:00Z")

    class NextSessionClock(RealDatetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 11, 28, 22, 30, tzinfo=timezone.utc)

    _set_native_clocks(monkeypatch, NextSessionClock)
    doc = json.loads(source.read_text())
    doc["as_of"] = "2026-11-28"
    doc["emit"]["at_utc"] = "2026-11-28T18:02:00+00:00"
    doc["buy"] = [{"ticker": "ALFA", "price": 42.0, "featured": True}]
    source.write_text(json.dumps(doc, separators=(",", ":")))
    receipts = producer.today_selection_row_receipts(source.read_bytes())
    records = context_owner.build_records({"ALFA": {}}, stamp_date="2026-11-28",
                                         board_definition="us_prophet_v3", is_buyable=lambda _: False,
                                         today_selection_row_receipts=receipts)
    candidate_part = tmp_path / "data/us_prophet_rank/candidates/2026-11.parquet"
    pd.DataFrame(records).to_parquet(candidate_part, index=False)
    writer.reconcile(repo_root=tmp_path, nightly=True, replay=False,
                     recorded_at="2026-11-28T22:05:00Z", correction_path=None)
    snapshot = load_candidate_episode_store_snapshot(_episode_root(tmp_path))
    relation = _native_relation(snapshot, _source_key("ALFA", session="2026-11-28"))
    result = _read_today(tmp_path, source)
    item = result["candidates"][0]
    assert item["status"] == "AVAILABLE"
    assert item["candidate_input"]["market_session"] == "2026-11-28"
    assessment_receipt = item["daily_brief"]["owners"]["assessment"]["source_receipt"]
    assert assessment_receipt.startswith("sha256:")
    pair, _snapshot, _relation = _genuine_pair(tmp_path, _source_key("ALFA", session="2026-11-28"))
    # The presented assessment is exactly this source session's owner read.
    assert assessment_receipt == pair.assessment["source_receipt"]
    assert relation["episode_id"] == item["candidate_input"]["episode_id"]
    assert pair.assessment["market_session"] == "2026-11-28"
    assert pair.assessment["provenance"]["episode_opened_session"] == "2026-11-27"
    assert pair.assessment["provenance"]["episode_opened_session"] != pair.assessment["market_session"]
    assert relation["source_event_id"] == _source_key("ALFA", session="2026-11-28")
    assert item["daily_brief"]["identity"]["market_session"] == "2026-11-28"


def test_staggered_native_assembly_after_request_start_composes_at_completion(
    tmp_path, monkeypatch
):
    source, _candidate = _native_today(tmp_path, monkeypatch)
    writer.reconcile(repo_root=tmp_path, nightly=True, replay=False,
                     recorded_at="2026-11-27T18:06:00Z", correction_path=None)
    CompletionClock._reads = 0
    _set_native_clocks(monkeypatch, CompletionClock)
    monkeypatch.setattr(b3_owner, "_assembly_now",
                        lambda: RealDatetime(2026, 11, 27, 18, 8, 15, tzinfo=timezone.utc))
    result = _read_today(tmp_path, source)
    item = result["candidates"][0]
    brief = item["daily_brief"]
    # The owner read genuinely assembled after the request-start observation, so
    # composing against the request clock would have forged a future owner clock.
    assert result["generated_at"] == "2026-11-27T18:08:30Z"
    assert item["candidate_input"]["asof"] == "2026-11-27T18:08:00Z"
    assert brief["clocks"]["assessment"] == "2026-11-27T18:08:15Z"
    assert brief["clocks"]["candidate"] == "2026-11-27T18:08:00Z"
    assert "FUTURE_OWNER_CLOCK" not in brief["issues"]
    assert brief["owners"]["assessment"]["state"] == "REVIEW_REQUIRED"
    assert item["reason_codes"] == ["PLAN_NATIVE_OWNER_READ_UNAVAILABLE",
                                    "EVIDENCE_NATIVE_OWNER_READ_UNAVAILABLE",
                                    "QUOTE_NATIVE_OWNER_READ_UNAVAILABLE",
                                    "B4_NATIVE_OWNER_READ_UNAVAILABLE"]


def test_native_fact_assembled_after_read_completion_is_refused(tmp_path, monkeypatch):
    source, _candidate = _native_today(tmp_path, monkeypatch)
    writer.reconcile(repo_root=tmp_path, nightly=True, replay=False,
                     recorded_at="2026-11-27T18:06:00Z", correction_path=None)
    _set_native_clocks(monkeypatch)
    monkeypatch.setattr(b3_owner, "_assembly_now",
                        lambda: RealDatetime(2026, 11, 27, 19, 0, 0, tzinfo=timezone.utc))
    result = _read_today(tmp_path, source)
    item = result["candidates"][0]
    assert item["status"] == "AVAILABLE"
    assert item["candidate_input"]["episode_id"]
    assert item["reason_codes"][0] == "ASSESSMENT_AFTER_READ_COMPLETION_UNAVAILABLE"
    assert item["reason_codes"][1:] == ["PLAN_NATIVE_OWNER_READ_UNAVAILABLE",
                                        "EVIDENCE_NATIVE_OWNER_READ_UNAVAILABLE",
                                        "QUOTE_NATIVE_OWNER_READ_UNAVAILABLE",
                                        "B4_NATIVE_OWNER_READ_UNAVAILABLE"]
    assert item["daily_brief"]["presentation"]["assessment"] is None
    assert item["daily_brief"]["owners"]["assessment"] is None


def test_completion_clock_never_renews_the_original_request_source_cut(tmp_path, monkeypatch):
    source, _candidate = _native_today(tmp_path, monkeypatch)
    writer.reconcile(repo_root=tmp_path, nightly=True, replay=False,
                     recorded_at="2026-11-27T18:06:00Z", correction_path=None)
    CompletionClock._reads = 0
    _set_native_clocks(monkeypatch, CompletionClock)
    doc = json.loads(source.read_text())
    # Observed after the request-start clock but before read completion: the
    # original request cut must still refuse it, whatever a later clock says.
    doc["emit"]["at_utc"] = "2026-11-27T18:08:20+00:00"
    source.write_text(json.dumps(doc, separators=(",", ":")))
    binding = producer.today_selection_source_binding(source.read_bytes())
    result = producer.read_today_candidate_projection(
        tmp_path, expected_source_sha256=binding["source_sha256"],
        expected_pair_id=binding["pair_id"],
        expected_selection_receipt=binding["selection_receipt"])
    assert result["status"] == "UNAVAILABLE"
    assert result["reason_codes"] == ["SELECTION_SOURCE_UNAVAILABLE"]


def test_completion_clock_never_renews_the_original_generation_cut(tmp_path, monkeypatch):
    source, _candidate = _native_today(tmp_path, monkeypatch)
    # A B1 generation recorded after this request started but before read
    # completion stays a future generation for THIS request.
    writer.reconcile(repo_root=tmp_path, nightly=True, replay=False,
                     recorded_at="2026-11-27T18:08:20Z", correction_path=None)
    CompletionClock._reads = 0
    _set_native_clocks(monkeypatch, CompletionClock)
    binding = producer.today_selection_source_binding(source.read_bytes())
    result = producer.read_today_candidate_projection(
        tmp_path, expected_source_sha256=binding["source_sha256"],
        expected_pair_id=binding["pair_id"],
        expected_selection_receipt=binding["selection_receipt"])
    assert result["status"] == "UNAVAILABLE"
    assert result["reason_codes"] == ["CANDIDATE_CLOCK_UNAVAILABLE"]


def test_source_race_after_owner_reads_still_discards_the_whole_response(tmp_path, monkeypatch):
    source, candidate = _native_today(tmp_path, monkeypatch)
    writer.reconcile(repo_root=tmp_path, nightly=True, replay=False,
                     recorded_at="2026-11-27T18:06:00Z", correction_path=None)
    calls = _counting_owner_factory(monkeypatch)
    real = context_owner.read_today_candidate_source_rows
    reads = []

    def captured(root):
        reads.append(root)
        if len(reads) == 2:
            source.write_bytes(source.read_bytes() + b" ")
        return real(root)

    monkeypatch.setattr(context_owner, "read_today_candidate_source_rows", captured)
    result = _read_today(tmp_path, source)
    assert result["status"] == "UNAVAILABLE"
    assert result["candidates"] == []
    assert len(reads) == 2
    # The owner reads were genuinely gathered first, and still count for nothing
    # once the request's own source snapshot moved under them.
    assert len(calls) == 1
    assert load_candidate_episode_store_snapshot(_episode_root(tmp_path)).generation_id == calls[0]["generation_id"]


def test_response_cannot_alias_or_drift_the_owner_read_it_presented(tmp_path, monkeypatch):
    source, _candidate = _native_today(tmp_path, monkeypatch)
    writer.reconcile(repo_root=tmp_path, nightly=True, replay=False,
                     recorded_at="2026-11-27T18:06:00Z", correction_path=None)
    first = _read_today(tmp_path, source)["candidates"][0]["daily_brief"]
    presented = first["presentation"]["assessment"]
    presented["assessment_state"] = "CURRENT"
    presented["model_thesis"] = "INVENTED"
    second = _read_today(tmp_path, source)["candidates"][0]["daily_brief"]
    assert second["presentation"]["assessment"]["assessment_state"] == "REVIEW_REQUIRED"
    assert second["presentation"]["assessment"]["model_thesis"] == "UNAVAILABLE"
    assert second["owners"]["assessment"] == first["owners"]["assessment"]
    assert second["view_id"] == first["view_id"]


def test_assessment_consumption_changes_no_selection_order_or_source_row(tmp_path, monkeypatch):
    source, candidate_part = _native_today_multi(tmp_path, monkeypatch)
    raw = source.read_bytes()
    before = producer.today_selection_row_receipts(raw)
    result = _read_today(tmp_path, source)
    assert [item["selection_index"] for item in result["candidates"]] == [0, 1]
    for item in result["candidates"]:
        ticker = item["candidate_input"]["display"]["ticker"]
        assert item["row_receipt"] == before[ticker]
        assert item["status"] == "AVAILABLE"
    assert source.read_bytes() == raw
    assert candidate_part.read_bytes() != b""


def test_retracted_relation_refuses_the_candidate_before_any_owner_read(
    tmp_path, monkeypatch
):
    source, _candidate = _native_today(tmp_path, monkeypatch)
    writer.reconcile(repo_root=tmp_path, nightly=True, replay=False,
                     recorded_at="2026-11-27T18:06:00Z", correction_path=None)
    snapshot = load_candidate_episode_store_snapshot(_episode_root(tmp_path))
    relation = _native_relation(snapshot, _source_key("ALFA"))
    calls = _counting_owner_factory(monkeypatch)
    corrections = _write_corrections(tmp_path, [{
        "event_type": "RETRACTED", "episode_id": relation["episode_id"],
        "source_system": "candidate_governance",
        "source_schema": "prophet_candidate_governance/v1",
        "source_event_id": "candidate_retraction:2026-11-27:ALFA:us_prophet_v3",
        "occurred_at": "2026-11-27T18:07:00Z", "known_at": "2026-11-27T18:07:00Z",
        "source_receipt": "sha256:" + "b" * 64, "correction_of": relation["event_id"],
        "payload": {"reason": "duplicate candidate source row"},
    }])
    writer.reconcile(repo_root=tmp_path, nightly=True, replay=False,
                     recorded_at="2026-11-27T18:07:30Z", correction_path=corrections)
    item = _read_today(tmp_path, source)["candidates"][0]
    assert item["status"] == "UNAVAILABLE"
    assert item["reason_codes"] == ["CANDIDATE_SOURCE_RETRACTED"]
    assert item["candidate_input"] is None and item["daily_brief"] is None
    assert calls == []


def test_final_source_guard_refusal_still_reports_completion_clock(tmp_path, monkeypatch):
    """A genuine native assessment discarded by the final guard ends the read."""
    source, _ = _native_today_multi(tmp_path, monkeypatch, tickers=("ALFA",))
    CompletionClock._reads = 0
    _set_native_clocks(monkeypatch, CompletionClock)
    monkeypatch.setattr(b3_owner, "_assembly_now",
                        lambda: RealDatetime(2026, 11, 27, 18, 8, 15, tzinfo=timezone.utc))
    actual = context_owner.read_today_candidate_source_rows
    reads = []

    def race(root):
        reads.append(root)
        if len(reads) == 2:
            source.write_bytes(source.read_bytes() + b" ")
        return actual(root)

    monkeypatch.setattr(context_owner, "read_today_candidate_source_rows", race)
    result = _read_today(tmp_path, source)
    assert len(reads) == 2
    assert result["status"] == "UNAVAILABLE"
    assert result["candidates"] == []
    assert result["reason_codes"] == ["SOURCE_SNAPSHOT_CHANGED"]
    assert result["generated_at"] == "2026-11-27T18:08:30Z"


# ---------------------------------------------------------------------------
# The extracted private native source resolution core. The Today suite above
# stays the full behavior regression proof; these three pin the core contract
# that the fixed Plan source read (scripts/build_prophet.py) now shares — one
# resolver, no second resolution path, and per-row original relation facts
# that never alter the Today-shaped result.
# ---------------------------------------------------------------------------


def test_extracted_native_source_core_reproduces_the_today_read(tmp_path, monkeypatch):
    source, _candidate = _native_today_multi(tmp_path, monkeypatch)
    raw = source.read_bytes()
    binding = producer.today_selection_source_binding(raw)
    doc = json.loads(raw)
    source_rows, _receipts = context_owner.read_today_candidate_source_rows(tmp_path)
    snapshot = load_candidate_episode_store_snapshot(_episode_root(tmp_path))
    details = []
    core_candidates, _core_reads = producer._today_native_source_candidates(
        raw, binding=binding, doc=doc, generation=snapshot.generation, snapshot=snapshot,
        source_rows=source_rows, generated_at="2026-11-27T18:08:00Z",
        relation_details=details)
    read = _read_today(tmp_path, source)
    assert len(details) == len(doc["buy"]) == 2
    assert details[0]["source_event_id"] == _source_key("ALFA")
    assert details[0]["relation"]["event_type"] == "OBSERVED"
    assert details[1]["source_event_id"] == _source_key("BETA")
    # The reader IS this core: identical per-row resolution, no second path.
    assert [(item["selection_index"], item["status"]) for item in core_candidates] == [
        (item["selection_index"], item["status"]) for item in read["candidates"]]
    for core_item, read_item in zip(core_candidates, read["candidates"], strict=True):
        assert core_item["candidate_input"] == read_item["candidate_input"]
        assert core_item["row_receipt"] == read_item["row_receipt"]
        assert core_item["reason_codes"] == read_item["reason_codes"]
        assert core_item["native_provenance"] == read_item["native_provenance"]
    assert details[0]["episode"]["security_id"] == (
        read["candidates"][0]["candidate_input"]["security_id"])


def test_native_source_core_refuses_bytes_outside_the_captured_source(tmp_path, monkeypatch):
    source, _candidate = _native_today(tmp_path, monkeypatch)
    raw = source.read_bytes()
    binding = producer.today_selection_source_binding(raw)
    with pytest.raises(ValueError, match="not the captured source bytes"):
        producer._today_native_source_candidates(
            raw + b" ", binding=binding, doc=json.loads(raw), generation=None,
            snapshot=None, source_rows=[], generated_at="2026-11-27T18:08:00Z")


def test_native_source_core_details_report_a_pending_original_relation(tmp_path, monkeypatch):
    source, _candidate = _native_today(tmp_path, monkeypatch)
    raw = source.read_bytes()
    binding = producer.today_selection_source_binding(raw)
    doc = json.loads(raw)
    source_rows, _receipts = context_owner.read_today_candidate_source_rows(tmp_path)
    snapshot = load_candidate_episode_store_snapshot(_episode_root(tmp_path))
    details = []
    core_candidates, _core_reads = producer._today_native_source_candidates(
        raw, binding=binding, doc=doc, generation=snapshot.generation, snapshot=snapshot,
        source_rows=source_rows, generated_at="2026-11-27T18:08:00Z",
        relation_details=details)
    assert core_candidates[0]["reason_codes"] == ["CANDIDATE_RECONCILIATION_PENDING"]
    # The exact original source key is inspectable before any native relation
    # exists; the relation and episode stay honestly absent, never inferred.
    assert details[0]["source_event_id"] == _source_key("ALFA")
    assert details[0]["relation"] is None
    assert details[0]["episode"] is None
    # The optional detail channel cannot alter the Today-shaped resolution.
    plain_candidates, _plain_reads = producer._today_native_source_candidates(
        raw, binding=binding, doc=doc, generation=snapshot.generation, snapshot=snapshot,
        source_rows=source_rows, generated_at="2026-11-27T18:08:00Z")
    assert plain_candidates == core_candidates
