"""IM18 engine-half contract checks: point-in-time replay over the IM12/IM15 chains.

Fixtures copy the incumbent helpers of tests/test_intl_global_dislocation.py
(they are never imported from it): build_observation stays the qualification
authority, and every archive below is assembled from qualified records unless a
test explicitly says otherwise.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import random
from copy import deepcopy
from datetime import date

import pytest

from engine.intl_global_dislocation import DECLARED_NOT_IMPLEMENTED, KINDS
from engine.intl_global_observation import build_observation, observation_id
from engine.intl_global_replay import (
    CONTRACT_VERSION,
    INTERPRETATION_LIMITS,
    LIMITATIONS,
    ReplayError,
    archive_diagnostics,
    as_known_at,
    normalise_instant,
    replay,
    replay_step,
    slot_key,
    universe_at,
    visible_at,
)
from engine.intl_transmission_evidence import forbidden_keys, scan_causal_language

RIGHTS = {"decision_ref": "chairman:2026-10-09:user-facing-redistribution-confirmed",
          "scope": "intl-index-fx-eod-user-facing-v1"}
INCUMBENT = {"quality": "qualified", "reason": None,
             "decision_ref": "derived-evaluation:sha256:abc"}
EVIDENCE = "saved-parquet:sha256:one|saved-parquet:sha256:two"

BASE_END = date(2026, 10, 7)
PUB_EARLY = "2026-10-08T03:00:00+00:00"
INGEST_EARLY = "2026-10-08T06:00:00+00:00"
SUBJECT_V2_INGEST = "2026-10-09T12:00:00+00:00"
LATE_INGEST = "2026-10-09T18:00:00+00:00"
POST_NOW_INGEST = "2026-10-12T00:00:00+00:00"
RAIL = ("2026-10-08T12:00:00Z", "2026-10-09T00:00:00+00:00", "2026-10-09T12:00:00")
NOW = "2026-10-11T00:00:00Z"

STEP_KEYS = {"contract_version", "step_id", "step_at", "subject_slot", "kind",
             "state", "withheld_reasons", "roster_digest", "visible_count",
             "superseded", "receipt", "clocks", "lag", "dependency_id", "consumes"}
REPLAY_KEYS = {"contract_version", "subject_slot", "kind", "now_at", "rail", "now",
               "at_step_vs_now", "archive_diagnostics", "limitations",
               "interpretation_limits"}
ROW_KEYS = {"question", "at_step", "now", "changed", "correction_note"}
HEX64 = set("0123456789abcdef")
UTC = dt.timezone.utc


def _canonical(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def _instant(text: str) -> dt.datetime:
    return dt.datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(UTC)


def _month(k: int) -> date:
    """Window endpoint E(k): BASE_END shifted back k months (day 7 always)."""
    total = BASE_END.year * 12 + BASE_END.month - 1 - k
    return date(total // 12, total % 12 + 1, BASE_END.day)


def _offset(market_id: str) -> int:
    return (ord(market_id[0]) + ord(market_id[-1])) % 7


def _local_value(market_id: str, k: int, shift: float = 0.0) -> float:
    return ((7 * k + _offset(market_id)) % 13 - 6) * 0.8 + shift


def _fx_value(market_id: str, k: int) -> float:
    return ((5 * k + _offset(market_id)) % 7 - 3) * 0.5


def _identity(market_id: str = "JP", k: int = 0, *, tag: str = "", **overrides) -> dict:
    identity = {
        "universe_id": market_id, "market_id": market_id,
        "index_id": f"^T{market_id}", "fx_id": f"{market_id}FX=X",
        "horizon": "1m", "currency_basis": "usd_unhedged", "return_basis": "price",
        "window_start": f"{_month(k + 1)}T00:00:00",
        "window_end": f"{_month(k)}T00:00:00",
        "source_content_sha256": hashlib.sha256(
            f"{market_id}:{k}:{tag}".encode()).hexdigest(),
    }
    identity.update(overrides)
    return identity


def _clocks(k: int, *, ingested: str = INGEST_EARLY,
            ingestion_precision: str = "exact",
            published: str = PUB_EARLY,
            publication_precision: str = "exact",
            omit_publication: bool = False) -> dict:
    clocks = {
        "observation": {"at": f"{_month(k)}T00:00:00", "precision": "session_date"},
        "ingestion": {"at": ingested, "precision": ingestion_precision},
        "computation": {"at": ingested, "precision": "exact"},
    }
    if not omit_publication:
        clocks["source_publication"] = {"at": published,
                                        "precision": publication_precision}
    return clocks


def _observation(market_id: str = "JP", k: int = 0, *, tag: str = "",
                 shift: float = 0.0, ingested: str = INGEST_EARLY,
                 ingestion_precision: str = "exact", published: str = PUB_EARLY,
                 publication_precision: str = "exact", horizon: str = "1m",
                 omit_publication: bool = False) -> dict:
    local_pct = _local_value(market_id, k, shift)
    fx_pct = _fx_value(market_id, k)
    usd_pct = ((1.0 + local_pct / 100.0) * (1.0 + fx_pct / 100.0) - 1.0) * 100.0
    return build_observation(
        identity=_identity(market_id, k, tag=tag, horizon=horizon),
        clocks=_clocks(k, ingested=ingested,
                       ingestion_precision=ingestion_precision,
                       published=published,
                       publication_precision=publication_precision,
                       omit_publication=omit_publication),
        values={"local_pct": local_pct, "usd_pct": usd_pct, "fx_pct": fx_pct},
        rights=dict(RIGHTS), incumbent=dict(INCUMBENT), evidence_ref=EVIDENCE)


def _foreign_observation(market_id: str, k: int = 0, *, tag: str = "",
                         shift: float = 0.0, ingested: str = INGEST_EARLY,
                         published: str = PUB_EARLY) -> dict:
    """A qualified record for a market outside the legacy seven.

    build_observation only admits the legacy seven markets, but the universe of
    a replay is caller-supplied: shape the record by hand so a later-added
    constituent can sit in the archive before the universe knows it.
    """
    record = _observation("KR", k, tag=tag, shift=shift, ingested=ingested,
                          published=published)
    identity = _identity(market_id, k, tag=tag)
    record["identity"] = identity
    record["observation_id"] = observation_id(identity)
    return record


def _references(count: int = 24, start: int = 1) -> list[dict]:
    return [_observation("JP", k) for k in range(start, start + count)]


def _subject_v1() -> dict:
    return _observation("JP", 0, tag="v1", shift=44.8)


def _subject_v2() -> dict:
    return _observation("JP", 0, tag="v2", shift=-44.8,
                        ingested=SUBJECT_V2_INGEST,
                        published="2026-10-09T09:00:00+00:00")


def _archive(*extra: dict) -> list[dict]:
    """References first, the correction before the original: nothing about the
    archive's order may matter to a step."""
    return _references() + [_subject_v2(), _subject_v1(), *extra]


def _ids() -> dict:
    return {"v1": _subject_v1()["observation_id"],
            "v2": _subject_v2()["observation_id"]}


def _replay(archive=None, **overrides):
    payload = {"steps_at": list(RAIL), "subject_slot": slot_key(_subject_v1()),
               "kind": "own_history_return", "now_at": NOW,
               "archive": _archive() if archive is None else archive}
    payload.update(overrides)
    return replay(**payload)


def _peer_archive(markets=("KR", "TW", "IN", "AU", "GB", "EZ"),
                  shifts=(0.0, 0.7, 1.9, -1.3, -2.2, 2.6),
                  k: int = 0, ingested: str = INGEST_EARLY,
                  published: str = PUB_EARLY) -> list[dict]:
    """A same-window cross-section; k/ingested let older steps replay it."""
    return ([_observation("JP", k, tag="p", shift=3.3, ingested=ingested,
                          published=published)] +
            [_observation(market, k, tag="p", shift=shift, ingested=ingested,
                          published=published) for market, shift
             in zip(markets, shifts)])


def _asia_europe_universe() -> dict:
    return {"jurisdictions": {
        **{market: {"region": "asia_pacific"}
           for market in ("JP", "KR", "TW", "IN", "AU")},
        "GB": {"region": "europe"}, "EZ": {"region": "europe"}}}


# 1 vocabulary -------------------------------------------------------------------


def test_module_vocabulary_is_frozen():
    assert CONTRACT_VERSION == "intl-global-replay-v1"
    assert isinstance(ReplayError("x"), ValueError)
    assert LIMITATIONS == ("source_vintage_unavailable:dollar_credit",)
    joined = " ".join(INTERPRETATION_LIMITS)
    assert "Each step shows what the archive held at that instant." in joined
    assert ("A row withheld at a step stays withheld; replay never fills it "
            "from later data.") in joined
    for sentence in INTERPRETATION_LIMITS:
        assert isinstance(sentence, str) and sentence.endswith(".")


def test_instant_normalisation_rules():
    assert normalise_instant("2026-10-08T12:00:00Z") == "2026-10-08T12:00:00Z"
    assert normalise_instant("2026-10-08T12:00:00+00:00") == "2026-10-08T12:00:00Z"
    assert normalise_instant("2026-10-08 12:00:00") == "2026-10-08T12:00:00Z"
    assert normalise_instant("2026-10-08T07:00:00+05:00") == "2026-10-08T02:00:00Z"
    assert normalise_instant("garbage") is None
    assert normalise_instant(None) is None
    result = _replay()
    for step in [result["now"], *result["rail"]]:
        assert step["step_at"].endswith("Z")
        assert step["step_at"] == normalise_instant(step["step_at"])
    assert result["now_at"] == "2026-10-11T00:00:00Z"


# 2 clock rules --------------------------------------------------------------------


def test_visible_at_uses_only_the_ingestion_clock():
    exact = _observation("JP", 0, ingested="2026-10-08T06:00:00+00:00")
    moment = dt.datetime(2026, 10, 8, 6, 0, 0, tzinfo=UTC)
    assert visible_at(exact, moment) is True                     # at == instant
    assert visible_at(exact, moment - dt.timedelta(seconds=1)) is False
    upper = _observation("JP", 0, ingested="2026-10-08T06:00:00+00:00",
                         ingestion_precision="upper_bound")
    assert visible_at(upper, moment) is True
    session = _observation("JP", 0, ingested="2026-10-07T15:30:00+00:00",
                           ingestion_precision="session_date")
    assert visible_at(session, dt.datetime(2026, 10, 7, 23, 59, 59,
                                           tzinfo=UTC)) is False
    assert visible_at(session, dt.datetime(2026, 10, 8, 0, 0, 0,
                                           tzinfo=UTC)) is True
    unknown_precision = _observation("JP", 0, ingested="2026-10-08T06:00:00+00:00",
                                     ingestion_precision="quarterly")
    assert visible_at(unknown_precision, moment) is False
    broken = _observation("JP", 0, ingested="not-a-clock")
    assert visible_at(broken, moment) is False
    stripped = _observation("JP", 0)
    del stripped["clocks"]["ingestion"]
    assert visible_at(stripped, moment) is False


def test_slot_key_ignores_only_the_source_hash():
    v1, v2 = _subject_v1(), _subject_v2()
    assert slot_key(v1) == slot_key(v2)                    # a correction, one slot
    assert slot_key(v1).startswith("slot:sha256:")
    assert set(slot_key(v1)[len("slot:sha256:"):]) <= HEX64
    assert len(slot_key(v1)) == len("slot:sha256:") + 64
    assert slot_key(v1) != slot_key(_observation("JP", 0, tag="v1", horizon="3m"))
    assert slot_key(v1) != slot_key(_observation("KR", 0, tag="v1"))


def test_archive_diagnostics_is_a_whole_archive_view():
    late_precision = _observation("JP", 30, ingested="2026-10-08T06:00:00+00:00",
                                  ingestion_precision="quarterly")
    no_ingestion = _observation("JP", 31, ingested="2026-10-08T06:00:00+00:00")
    del no_ingestion["clocks"]["ingestion"]
    invisible_but_clocked = _observation("JP", 32, ingested=POST_NOW_INGEST)
    archive = _archive(late_precision, no_ingestion, invisible_but_clocked)
    diagnostics = archive_diagnostics(archive)
    assert diagnostics["observation_count"] == len(archive)
    assert diagnostics["clock_missing"] == sorted(
        [late_precision["observation_id"], no_ingestion["observation_id"]])


# 3 as-known-at ---------------------------------------------------------------------


def test_observation_id_conflict_and_identical_duplicates():
    twin = _subject_v1()
    known = as_known_at([twin, deepcopy(twin)], NOW)
    assert [record["observation_id"] for record in known["visible"]] == \
        [twin["observation_id"]]
    assert known["superseded"] == []
    conflict = _subject_v1()
    conflict["clocks"]["ingestion"]["at"] = LATE_INGEST
    with pytest.raises(ReplayError, match="observation_id_conflict"):
        as_known_at([_subject_v1(), conflict], NOW)


def test_as_known_at_supersession_and_ordering():
    archive, ids = _archive_with_ids()
    before = as_known_at(archive, RAIL[1])
    assert ids["v2"] not in {record["observation_id"]
                             for record in before["visible"]}
    assert before["superseded"] == []       # v2 is simply absent, not superseded
    at_correction = as_known_at(archive, RAIL[2])
    assert {record["observation_id"]
            for record in at_correction["visible"]} == (
        {ids["v2"]} |                              # v1 lost the slot: superseded
        {record["observation_id"] for record in _references()})
    assert at_correction["superseded"] == [
        {"observation_id": ids["v1"], "superseded_by": ids["v2"]}]
    keys = [(slot_key(record), record["observation_id"])
            for record in at_correction["visible"]]
    assert keys == sorted(keys)
    assert at_correction["instant"] == "2026-10-09T12:00:00Z"


def _archive_with_ids() -> tuple[list[dict], dict]:
    return _archive(), _ids()


def test_supersession_tie_ascending_observation_id_wins_both_orders():
    """F1: an exact _visible_from tie goes to the ascending observation_id."""
    first = _observation("JP", 0, tag="tieA")
    second = _observation("JP", 0, tag="tieB")     # same slot, same instant
    assert slot_key(first) == slot_key(second)
    assert first["observation_id"] != second["observation_id"]
    assert (first["clocks"]["ingestion"]["at"]
            == second["clocks"]["ingestion"]["at"])
    winner_id = min(first["observation_id"], second["observation_id"])
    loser_id = max(first["observation_id"], second["observation_id"])
    for archive in ([first, second], [second, first]):
        known = as_known_at(archive, NOW)
        same_slot = [record for record in known["visible"]
                     if slot_key(record) == slot_key(first)]
        assert [record["observation_id"] for record in same_slot] == [winner_id]
        assert known["superseded"] == [
            {"observation_id": loser_id, "superseded_by": winner_id}]


def test_superseded_entries_sorted_by_observation_id():
    """F2: two slots superseding at once — the list is ordered by observation_id."""
    jp_a, jp_b = _observation("JP", 0, tag="p1"), _observation("JP", 0, tag="p2")
    kr_a, kr_b = _observation("KR", 0, tag="q1"), _observation("KR", 0, tag="q2")
    assert slot_key(jp_a) == slot_key(jp_b) != slot_key(kr_a) == slot_key(kr_b)
    jp_winner, jp_loser = (min(jp_a["observation_id"], jp_b["observation_id"]),
                           max(jp_a["observation_id"], jp_b["observation_id"]))
    kr_winner, kr_loser = (min(kr_a["observation_id"], kr_b["observation_id"]),
                           max(kr_a["observation_id"], kr_b["observation_id"]))
    entries = [{"observation_id": jp_loser, "superseded_by": jp_winner},
               {"observation_id": kr_loser, "superseded_by": kr_winner}]
    # The fixture must order differently under the two sort keys, or it could
    # not tell a superseded_by-sorted list from the contract's order.
    assert (sorted(entries, key=lambda entry: entry["observation_id"])
            != sorted(entries, key=lambda entry: entry["superseded_by"]))
    known = as_known_at([jp_a, jp_b, kr_a, kr_b], NOW)
    assert len(known["superseded"]) == 2
    assert known["superseded"] == sorted(
        entries, key=lambda entry: entry["observation_id"])


# 4 the contract's T1..T5 -------------------------------------------------------------


def test_t1_future_revision_invisible_then_visible():
    archive, ids = _archive_with_ids()
    result = _replay(archive)
    step1, step3 = result["rail"][0], result["rail"][2]
    assert step1["state"] == "computed"
    assert step1["receipt"]["subject"]["observation_id"] == ids["v1"]
    assert ids["v2"] not in step1["consumes"]
    assert step1["superseded"] == []
    # Nothing about the invisible correction may enter the step, not even as a
    # count: the receipt must have been fed the visible set, not the archive.
    references = step1["receipt"]["references"]
    assert references["offered"] == 24
    assert references["excluded_by_reason"]["not_point_in_time"] == 0
    assert ids["v2"] not in references["used_observation_ids"]
    # RAIL[2] is exactly the correction's ingestion instant: at == instant is visible.
    assert step3["receipt"]["subject"]["observation_id"] == ids["v2"]
    assert step3["superseded"] == [
        {"observation_id": ids["v1"], "superseded_by": ids["v2"]}]
    assert result["now"]["receipt"]["subject"]["observation_id"] == ids["v2"]
    assert step1["receipt"]["evidence"]["direction"] == "above"
    assert result["now"]["receipt"]["evidence"]["direction"] == "below"
    row = result["at_step_vs_now"][0]["rows"][0]
    assert row["question"] == "Q1" and row["changed"] is True


def test_t2_late_acquired_data_leaves_earlier_steps_identical():
    late = _observation("JP", 25, ingested=LATE_INGEST,
                        published="2026-10-09T15:00:00+00:00")
    without = _replay()
    with_late = _replay(_archive(late))
    for before, after in zip(without["rail"], with_late["rail"]):
        assert _canonical(before) == _canonical(after)
    # The now step does see the 25th window; the comparison cells are summaries
    # and may stay stable, so the proof lives in the step's own receipt.
    assert late["observation_id"] not in without["now"]["consumes"]
    assert late["observation_id"] in with_late["now"]["consumes"]
    assert with_late["now"]["receipt"]["references"]["used"] == 25
    assert without["now"]["receipt"]["references"]["used"] == 24


def test_t3_surviving_constituents_use_the_step_time_universe():
    u1 = _asia_europe_universe()
    u2 = deepcopy(u1)
    u2["jurisdictions"]["BR"] = {"region": "asia_pacific"}   # constituent added later
    versions = [{"effective_from": "2026-01-01", "universe": u1},
                {"effective_from": "2026-06-01T00:00:00Z", "universe": u2}]
    assert universe_at(versions, "2025-12-31T23:59:59Z") is None   # never a fallback
    assert universe_at(versions, "2026-01-01T00:00:00Z") == u1     # at == effective
    assert universe_at(versions, "2026-05-01T00:00:00Z") == u1
    assert universe_at(versions, "2026-07-01T00:00:00Z") == u2
    assert universe_at([], NOW) is None

    br = _foreign_observation("BR", k=10, tag="br", shift=1.1,
                              ingested="2026-02-01T06:00:00+00:00",
                              published="2026-02-01T03:00:00+00:00")
    archive = _peer_archive(k=10, ingested="2026-02-01T06:00:00+00:00",
                            published="2026-02-01T03:00:00+00:00") + [br]
    early = replay_step(archive, step_at="2026-05-01T00:00:00Z",
                        subject_slot=slot_key(archive[0]),
                        kind="peer_divergence_return", universe_versions=versions)
    later = replay_step(archive, step_at="2026-07-01T00:00:00Z",
                        subject_slot=slot_key(archive[0]),
                        kind="peer_divergence_return", universe_versions=versions)
    assert early["state"] == later["state"] == "computed"
    assert br["observation_id"] not in \
        early["receipt"]["references"]["used_observation_ids"]
    assert br["observation_id"] in \
        later["receipt"]["references"]["used_observation_ids"]
    assert early["receipt"]["references"]["excluded_by_reason"][
        "outside_peer_group"] == 3
    assert later["receipt"]["references"]["excluded_by_reason"][
        "outside_peer_group"] == 2


def test_t4_later_classification_cannot_change_the_step_time_peer_set():
    u1 = _asia_europe_universe()
    u2 = deepcopy(u1)
    u2["jurisdictions"]["GB"] = {"region": "asia_pacific"}    # reclassified later
    versions = [{"effective_from": "2026-01-01", "universe": u1},
                {"effective_from": "2026-06-01", "universe": u2}]
    archive = _peer_archive(k=10, ingested="2026-02-01T06:00:00+00:00",
                            published="2026-02-01T03:00:00+00:00")
    subject_slot = slot_key(archive[0])
    gb_id = archive[-2]["observation_id"]
    before = replay_step(archive, step_at="2026-05-01T00:00:00Z",
                         subject_slot=subject_slot,
                         kind="peer_divergence_return", universe_versions=versions)
    after = replay_step(archive, step_at="2026-07-01T00:00:00Z",
                        subject_slot=subject_slot,
                        kind="peer_divergence_return", universe_versions=versions)
    assert gb_id not in before["receipt"]["references"]["used_observation_ids"]
    assert gb_id in after["receipt"]["references"]["used_observation_ids"]
    assert before["receipt"]["references"]["used"] == 4
    assert after["receipt"]["references"]["used"] == 5


def test_t5_replay_is_never_improved_by_order_or_post_now_data():
    archive, _ = _archive_with_ids()
    first = _replay(archive)
    again = _replay(deepcopy(archive))
    assert _canonical(first) == _canonical(again)
    shuffled = list(archive)
    random.Random(20261031).shuffle(shuffled)
    assert _canonical(_replay(shuffled)["rail"]) == _canonical(first["rail"])
    assert _canonical(_replay(shuffled)["now"]) == _canonical(first["now"])
    post_now = _observation("JP", 26, ingested=POST_NOW_INGEST,
                            published="2026-10-11T06:00:00+00:00")
    grown = _replay(_archive(post_now))
    assert _canonical(grown["rail"]) == _canonical(first["rail"])
    assert _canonical(grown["now"]) == _canonical(first["now"])
    assert _canonical(grown["at_step_vs_now"]) == _canonical(first["at_step_vs_now"])
    assert grown["archive_diagnostics"]["observation_count"] == \
        first["archive_diagnostics"]["observation_count"] + 1


# 5 withheld paths ---------------------------------------------------------------------


def test_withheld_subject_not_visible_step_shape():
    late_subject = _observation("KR", 0, tag="late-subject", ingested=LATE_INGEST)
    archive = _references() + [late_subject]
    step = replay_step(archive, step_at="2026-10-08T12:00:00Z",
                       subject_slot=slot_key(late_subject),
                       kind="own_history_return")
    assert set(step) == STEP_KEYS
    assert step["state"] == "withheld"
    assert step["withheld_reasons"] == ["subject_not_visible"]
    assert step["receipt"] is None and step["clocks"] is None
    assert step["visible_count"] == 24
    assert step["consumes"] == []
    assert step["lag"] == {"source_to_ingestion_seconds": None,
                           "lag_withheld_reason": "subject_not_visible"}
    assert step["dependency_id"] == step["step_id"]
    assert step["roster_digest"].startswith("roster:sha256:")


def test_withheld_universe_unavailable_paths():
    archive = [_observation("JP", 0, tag="p", shift=3.3)]
    nothing = replay_step(archive, step_at="2026-10-08T12:00:00Z",
                          subject_slot=slot_key(archive[0]),
                          kind="peer_divergence_return")
    assert nothing["state"] == "withheld"
    assert nothing["withheld_reasons"] == ["universe_unavailable"]
    assert nothing["receipt"] is None
    future_only = [{"effective_from": "2026-12-01",
                    "universe": {"jurisdictions": {}}}]
    pending = replay_step(archive, step_at="2026-10-08T12:00:00Z",
                          subject_slot=slot_key(archive[0]),
                          kind="peer_divergence_return",
                          universe_versions=future_only)
    assert pending["withheld_reasons"] == ["universe_unavailable"]
    later = replay_step(archive, step_at="2026-12-02T00:00:00Z",
                        subject_slot=slot_key(archive[0]),
                        kind="peer_divergence_return",
                        universe_versions=future_only)
    assert later["state"] == "computed"


# 6 rail validation ----------------------------------------------------------------------


def test_rail_validation_closes_the_ladder():
    archive, _ = _archive_with_ids()
    subject_slot = slot_key(_subject_v1())

    def _rail(steps_at, now_at=NOW):
        return replay(archive, steps_at=steps_at, subject_slot=subject_slot,
                      kind="own_history_return", now_at=now_at)

    with pytest.raises(ReplayError, match="rail"):
        _rail([])
    sixty_one = [f"2026-10-{8 + i // 24:02d}T{i % 24:02d}:00:00Z"
                 for i in range(61)]
    with pytest.raises(ReplayError, match="rail"):
        _rail(sixty_one, now_at="2026-11-30T00:00:00Z")
    with pytest.raises(ReplayError, match="rail"):     # equal after normalisation
        _rail(["2026-10-08T12:00:00Z", "2026-10-08T12:00:00+00:00"])
    with pytest.raises(ReplayError, match="rail"):     # decreasing
        _rail(["2026-10-09T00:00:00Z", "2026-10-08T12:00:00Z"])
    with pytest.raises(ReplayError, match="rail"):     # a step beyond now_at
        _rail([NOW], now_at="2026-10-10T00:00:00Z")
    with pytest.raises(ReplayError, match="rail"):     # unparseable entry
        _rail(["not-a-clock"])
    sixty = [f"2026-10-{8 + i // 24:02d}T{i % 24:02d}:00:00Z" for i in range(60)]
    ok = _rail(sixty, now_at="2026-10-12T00:00:00Z")
    assert len(ok["rail"]) == 60


# 7 lag precision rules --------------------------------------------------------------------


def test_lag_precision_rules():
    archive, _ = _archive_with_ids()
    exact = replay_step(archive, step_at=RAIL[0],
                        subject_slot=slot_key(_subject_v1()),
                        kind="own_history_return")
    assert exact["lag"] == {"source_to_ingestion_seconds": 3 * 3600,
                            "lag_withheld_reason": None}
    imprecise_ingestion = _observation("JP", 0, tag="lag1",
                                       ingestion_precision="upper_bound")
    step = replay_step(_references() + [imprecise_ingestion], step_at=RAIL[0],
                       subject_slot=slot_key(imprecise_ingestion),
                       kind="own_history_return")
    assert step["lag"] == {"source_to_ingestion_seconds": None,
                           "lag_withheld_reason": "clock_imprecise"}
    imprecise_publication = _observation("JP", 0, tag="lag2",
                                         publication_precision="session_date",
                                         published="2026-10-08T00:00:00")
    step = replay_step(_references() + [imprecise_publication], step_at=RAIL[0],
                       subject_slot=slot_key(imprecise_publication),
                       kind="own_history_return")
    assert step["lag"]["lag_withheld_reason"] == "clock_imprecise"
    no_publication = _observation("JP", 0, tag="lag3", omit_publication=True)
    assert no_publication["state"] == "abstain"          # visible but unqualified
    step = replay_step(_references() + [no_publication], step_at=RAIL[0],
                       subject_slot=slot_key(no_publication),
                       kind="own_history_return")
    assert step["state"] == "computed"
    assert step["receipt"]["state"] == "abstain"
    assert step["lag"] == {"source_to_ingestion_seconds": None,
                           "lag_withheld_reason": "clock_missing"}
    step = replay_step(_archive(), step_at="2026-10-07T00:00:00Z",
                       subject_slot=slot_key(_subject_v1()),
                       kind="own_history_return")
    assert step["lag"]["lag_withheld_reason"] == "subject_not_visible"


# 8 purity, mutation and scans ---------------------------------------------------------------


def test_no_input_mutation():
    archive, _ = _archive_with_ids()
    frozen_archive = deepcopy(archive)
    versions = [{"effective_from": "2026-01-01",
                 "universe": {"jurisdictions": {"JP": {"region": "asia_pacific"}}}}]
    frozen_versions = deepcopy(versions)
    replay(archive, steps_at=list(RAIL), subject_slot=slot_key(_subject_v1()),
           kind="peer_divergence_return", now_at=NOW, universe_versions=versions)
    replay(archive, steps_at=list(RAIL), subject_slot=slot_key(_subject_v1()),
           kind="own_history_return", now_at=NOW)
    assert _canonical(archive) == _canonical(frozen_archive)
    assert _canonical(versions) == _canonical(frozen_versions)


def test_step_is_a_pure_function_of_the_visible_set():
    archive, _ = _archive_with_ids()
    invisible_extra = _observation("JP", 27, ingested=POST_NOW_INGEST,
                                   published="2026-10-11T06:00:00+00:00")
    base = replay_step(archive, step_at=RAIL[0],
                       subject_slot=slot_key(_subject_v1()),
                       kind="own_history_return")
    twin = replay_step(archive + [invisible_extra, deepcopy(invisible_extra)],
                       step_at="2026-10-08T12:00:00+00:00",
                       subject_slot=slot_key(_subject_v1()),
                       kind="own_history_return")
    assert _canonical(base) == _canonical(twin)


def test_outputs_scan_clean_of_causal_language_and_forbidden_keys():
    archive, _ = _archive_with_ids()
    computed = _replay(archive)
    withheld = replay(archive, steps_at=["2026-10-07T00:00:00Z"],
                      subject_slot=slot_key(_subject_v1()),
                      kind="own_history_return", now_at=NOW)
    for document in (computed, withheld):
        assert scan_causal_language(document) == []
        assert forbidden_keys(document) == []


# 9 output shape ------------------------------------------------------------------------------


def test_step_output_keys_and_id_grammar():
    archive, _ = _archive_with_ids()
    step = replay_step(archive, step_at=RAIL[0],
                       subject_slot=slot_key(_subject_v1()),
                       kind="own_history_return")
    assert set(step) == STEP_KEYS
    assert step["contract_version"] == CONTRACT_VERSION
    assert step["state"] == "computed" and step["withheld_reasons"] == []
    assert step["clocks"] is step["receipt"]["clocks"]
    assert step["visible_count"] == 25
    assert step["dependency_id"] == step["receipt"]["dislocation_id"]
    assert step["step_id"].startswith("rstep:sha256:")
    assert len(step["step_id"]) == len("rstep:sha256:") + 64
    assert set(step["step_id"][len("rstep:sha256:"):]) <= HEX64
    subject_id = step["receipt"]["subject"]["observation_id"]
    assert step["consumes"] == sorted(
        {subject_id} |
        set(step["receipt"]["references"]["used_observation_ids"]) |
        set(step["receipt"]["references"]["subject_block_ids"]))
    expected_roster = "roster:sha256:" + hashlib.sha256(_canonical(
        sorted(record["observation_id"] for record in as_known_at(
            archive, RAIL[0])["visible"])).encode()).hexdigest()
    assert step["roster_digest"] == expected_roster


def test_step_id_hashes_the_seven_named_fields():
    """F3: step_id is the digest of exactly the contract's payload, computed
    and withheld alike (mirroring the roster_digest exact-formula assert)."""
    archive, _ = _archive_with_ids()
    subject_slot = slot_key(_subject_v1())
    computed = replay_step(archive, step_at=RAIL[0],
                           subject_slot=subject_slot,
                           kind="own_history_return")
    withheld = replay_step(archive, step_at="2026-10-07T00:00:00Z",
                           subject_slot=subject_slot,
                           kind="own_history_return")
    assert computed["state"] == "computed"
    assert withheld["state"] == "withheld" and withheld["receipt"] is None
    for step in (computed, withheld):
        expected = "rstep:sha256:" + hashlib.sha256(_canonical({
            "contract_version": CONTRACT_VERSION,
            "step_at": step["step_at"],
            "subject_slot": step["subject_slot"],
            "kind": step["kind"],
            "roster_digest": step["roster_digest"],
            "dislocation_id": (step["receipt"]["dislocation_id"]
                               if step["receipt"] is not None else None),
            "state": step["state"]}).encode()).hexdigest()
        assert step["step_id"] == expected


def test_replay_output_shape_and_at_step_vs_now_rows():
    archive, _ = _archive_with_ids()
    subject_slot = slot_key(_subject_v1())
    result = replay(archive, steps_at=list(RAIL), subject_slot=subject_slot,
                    kind="own_history_return", now_at=NOW)
    assert set(result) == REPLAY_KEYS
    assert result["contract_version"] == CONTRACT_VERSION
    assert result["subject_slot"] == subject_slot
    assert result["kind"] == "own_history_return"
    assert result["limitations"] == ["source_vintage_unavailable:dollar_credit"]
    assert [entry["step_id"] for entry in result["at_step_vs_now"]] == \
        [step["step_id"] for step in result["rail"]]
    now_again = replay_step(archive, step_at=NOW, subject_slot=subject_slot,
                            kind="own_history_return")
    assert _canonical(result["now"]) == _canonical(now_again)
    fixed = {"Q3": "credit_funding_unadmitted", "Q4": "transmission_unadmitted",
             "Q5": "us_corroboration_unadmitted", "Q6": "thesis_unadmitted"}
    for entry in result["at_step_vs_now"]:
        assert [row["question"] for row in entry["rows"]] == \
            ["Q1", "Q2", "Q3", "Q4", "Q5", "Q6"]
        for row in entry["rows"]:
            assert set(row) == ROW_KEYS
            assert row["correction_note"] is None
        for question, reason in fixed.items():
            row = entry["rows"][int(question[1]) - 1]
            assert row["at_step"] == {"state": "withheld", "reason": reason}
            assert row["now"] == {"state": "withheld", "reason": reason}
            assert row["changed"] is False

    # A peer step withheld at the rail but computed at now: the Q1 cell carries
    # the step's own withheld reason, and the comparison marks it changed.
    u_late = [{"effective_from": "2026-10-09T18:00:00Z",
               "universe": {"jurisdictions": {
                   market: {"region": "asia_pacific"}
                   for market in ("JP", "KR", "TW", "IN", "AU")}}}]
    peer_archive = _peer_archive(("KR", "TW", "IN", "AU"),
                                 (0.0, 0.7, 1.9, -1.3))
    peer = replay(peer_archive, steps_at=list(RAIL),
                  subject_slot=slot_key(peer_archive[0]),
                  kind="peer_divergence_return", now_at=NOW,
                  universe_versions=u_late)
    q1 = peer["at_step_vs_now"][2]["rows"][0]
    assert q1["at_step"] == {"state": "withheld",
                             "reason": "universe_unavailable"}
    assert q1["now"]["state"] in ("qualified", "abstain")
    assert q1["changed"] is True
    q2_now = peer["at_step_vs_now"][0]["rows"][1]["now"]
    assert set(q2_now) == {"state", "decomposition", "peer_attention"}
    assert q2_now["peer_attention"] is not None
    own_q2 = result["at_step_vs_now"][0]["rows"][1]["at_step"]
    assert own_q2["peer_attention"] is None


def test_kind_validation_closes_the_ladder():
    archive, _ = _archive_with_ids()
    with pytest.raises(ReplayError, match="kind"):
        replay_step(archive, step_at=RAIL[0], subject_slot=slot_key(_subject_v1()),
                    kind="no_such_kind")
    for kind in DECLARED_NOT_IMPLEMENTED:
        with pytest.raises(ReplayError, match="kind"):
            replay_step(archive, step_at=RAIL[0],
                        subject_slot=slot_key(_subject_v1()), kind=kind)
    with pytest.raises(ReplayError, match="kind"):
        replay(archive, steps_at=list(RAIL), subject_slot=slot_key(_subject_v1()),
               kind="factor_residual", now_at=NOW)
    assert "own_history_return" in KINDS


def test_universe_versions_duplicates_and_malformed_entries():
    versions = [{"effective_from": "2026-06-01", "universe": {"jurisdictions": {}}},
                {"effective_from": "2026-06-01T00:00:00Z",
                 "universe": {"jurisdictions": {}}}]
    with pytest.raises(ReplayError, match="universe_versions"):
        universe_at(versions, NOW)
    mixed = [{"effective_from": "garbage", "universe": {"jurisdictions": {}}},
             {"effective_from": "2026-01-01",
              "universe": {"jurisdictions": {"JP": {}}}},
             {"universe": {"jurisdictions": {}}}]
    assert universe_at(mixed, NOW) == {"jurisdictions": {"JP": {}}}


def test_volatility_step_consumes_subject_block_ids():
    predecessors = [_observation("JP", 1), _observation("JP", 2)]
    archive = ([_observation("JP", 0, tag="vol")] + predecessors +
               [_observation("JP", k) for k in range(3, 27)])
    step = replay_step(archive, step_at=RAIL[0],
                       subject_slot=slot_key(archive[0]),
                       kind="own_history_volatility")
    assert step["state"] == "computed"
    assert step["receipt"]["state"] == "abstain"         # 8 blocks < 20 references
    block_ids = set(step["receipt"]["references"]["subject_block_ids"])
    assert {record["observation_id"] for record in predecessors} <= block_ids
    assert block_ids <= set(step["consumes"])
    assert archive[0]["observation_id"] in step["consumes"]


def test_every_step_computes_at_its_own_instant():
    result = _replay()
    for step in result["rail"]:
        assert step["receipt"]["clocks"]["computation"]["at"] == step["step_at"]
        assert step["receipt"]["clocks"]["computation"]["at"] != result["now_at"]
    assert result["now"]["receipt"]["clocks"]["computation"]["at"] == result["now_at"]
