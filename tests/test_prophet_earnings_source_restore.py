"""tests/test_prophet_earnings_source_restore.py — the Prophet earnings arm is fed again.

THE DEFECT THIS FILE PINS (production starvation, observed 2026-09-17).

``engine/prophet_stage_inputs.py`` resolved the Prophet hold-leash's earnings evidence
from exactly ONE path: ``data/stage_analysis/backfill/earnings_calls.parquet``. That file
is gitignored, was never committed, and had no fetch/publish pair, so on every CI and
deploy host it was absent. The EC join returned an empty table, every lookup answered
``None``, and the promoted Stage hold-tilt could not become eligible — the arm has been
inert since it shipped (``tests/test_prophet_earnings_split_brain.py`` documents that).

Two independent causes had to be repaired, and this file holds both down.

1. RESOLUTION. The SAME native EquityDesk table already reaches CI and deploy as
   ``data/earnings_calls/history.parquet`` — published as an immutable generation by
   ``scripts/publish_earnings_r2.py`` and restored by ``scripts/fetch_earnings_scores.py``
   against ``earnings_calls/manifest.json``. ``engine/earnings_qual.py`` has read that
   exact store, at the tier name ``r2_history``, since SGA W4. Prophet was the only
   EquityDesk consumer that did not know the address. It now walks the same native ladder.

2. ORDERING. ``fetch_earnings_scores`` already ran on the nightly runner — but inside
   ``cl_stage``, ~840 YAML lines BELOW the Prophet step, in the same ``engine`` job. Even
   a perfectly published store arrived after the night's plans were written. A read-only
   hydration step now runs before origination.

WHAT MUST NOT MOVE, and is asserted here rather than assumed:
  * the native ~-10..30 ``earnings_call_sent`` scale and ``EC_SENT_GATE = 24``;
  * the point-in-time rule (most recent call STRICTLY before the entry date);
  * fail-open on absence — and the honest disclosure of it;
  * the ladder admits NATIVE stores only, never the projected cold-start tiers, and
    never this repo's own -1..1 ``data/earnings_calls/scores.parquet``;
  * no new transport, registry, database or lifecycle plane exists — the repair reuses
    the earnings R2 plane and its one contract validator.

Run: python3 -m pytest tests/test_prophet_earnings_source_restore.py -q
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pandas as pd
import pytest

_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

import engine.prophet_stage_inputs as psi  # noqa: E402
import engine.prophet_bridge as pb  # noqa: E402
import engine.prophet_stage_shadow as pss  # noqa: E402
from engine import earnings_qual  # noqa: E402
from scripts import fetch_earnings_scores as fes  # noqa: E402
from scripts.publish_earnings_r2 import _synth_manifest  # noqa: E402

# Native desk-scale readings. 30 is the documented ceiling; 24 is the gate; 12 is the
# documented neutral midpoint. Nothing here is on any other scale — that is the point.
EC_STRONG = 30.0
EC_AT_GATE = 24.0
EC_BELOW_GATE = 23.0


# --------------------------------------------------------------------------- #
# Fixtures — real parquet files at the real addresses, read by the real loader. #
# --------------------------------------------------------------------------- #
def _ec_frame(rows: list[tuple[str, str, float]]) -> pd.DataFrame:
    """The EquityDesk native numeric shape, with the columns the join reads."""
    return pd.DataFrame({
        "document_ticker": [r[0] for r in rows],
        "call_date": pd.to_datetime([r[1] for r in rows]),
        "earnings_call_sent": [r[2] for r in rows],
    })


def write_legacy_backfill(data_root: Path, rows) -> Path:
    """The local-only EquityDesk import — the tier that never ships."""
    p = data_root / "stage_analysis" / "backfill" / "earnings_calls.parquet"
    p.parent.mkdir(parents=True, exist_ok=True)
    _ec_frame(rows).to_parquet(p, index=False)
    return p


def write_r2_history(data_root: Path, rows, *, manifest: bool = True) -> Path:
    """The store a CI/deploy host holds after scripts/fetch_earnings_scores.py runs.

    The manifest is built by the REAL producer helper (``publish_earnings_r2._synth_manifest``)
    so the fixture cannot drift from the contract the fetcher and the validator enforce.
    """
    d = data_root / "earnings_calls"
    d.mkdir(parents=True, exist_ok=True)
    history = d / "history.parquet"
    _ec_frame(rows).to_parquet(history, index=False)
    scores = d / "scores.parquet"
    if not scores.exists():
        # The generation always carries a scores block; its content is irrelevant here.
        pd.DataFrame({"ticker": ["SPY"], "sentiment": [0.0]}).to_parquet(scores, index=False)
    if manifest:
        (d / "manifest.json").write_text(
            json.dumps(_synth_manifest(scores, history), indent=2, default=str) + "\n",
            encoding="utf-8",
        )
    return history


@pytest.fixture()
def data_root(tmp_path, monkeypatch) -> Path:
    """An isolated data root that ``lib.config.data_dir()`` resolves to."""
    root = tmp_path / "data"
    root.mkdir(parents=True, exist_ok=True)
    from lib import config
    monkeypatch.setattr(config, "data_dir", lambda: root)
    return root


# --------------------------------------------------------------------------- #
# 1. RED reproduction — the production starvation, and its repair.              #
# --------------------------------------------------------------------------- #
def test_red_a_ci_host_holding_the_governed_table_used_to_resolve_nothing(data_root):
    """THE REPRODUCTION. A host in the exact state ``fetch_earnings_scores`` leaves —
    the governed EquityDesk table present at ``data/earnings_calls/history.parquet`` with
    its generation manifest, and the never-published legacy path absent — is the state of
    every nightly runner. Before the repair this resolved ``unavailable`` and every
    earnings lookup answered ``None``: the starvation the 2026-09-17 logs report.

    It must now resolve the governed table, at its own tier, with real readings.
    """
    write_r2_history(data_root, [("MSFT", "2026-06-01", EC_STRONG)])
    assert not (data_root / "stage_analysis" / "backfill" / "earnings_calls.parquet").exists()

    record = psi.resolve_ec_source()
    assert record["state"] == psi.EC_SOURCE_AVAILABLE, (
        "a CI host holding the governed earnings table still reports no source — "
        "this is the production starvation")
    assert record["tier"] == psi.EC_TIER_R2_HISTORY
    assert record["reason"] is None

    table, loaded = psi.load_ec_table_with_source()
    assert loaded["state"] == psi.EC_SOURCE_AVAILABLE
    assert loaded["tier"] == psi.EC_TIER_R2_HISTORY
    assert loaded["rows"] == 1 == len(table)

    ec = psi.ec_sent_at_entry(psi.ec_index(table), "MSFT", "2026-07-02")
    assert ec == EC_STRONG, "the cohort still receives a null earnings observation"


def test_red_the_hold_tilt_can_become_eligible_on_a_hydrated_host(data_root, monkeypatch):
    """End to end through the REAL origination path.

    Before the repair every plan on every deploy host carried
    ``ec_source_state=unavailable`` and ``leash=1.0``; the promoted 45->56 hold horizon
    was unreachable in production. With the governed table present the arm fires — and
    fires at its ratified numbers, not new ones.
    """
    write_r2_history(data_root, [("MSFT", "2026-06-01", EC_STRONG),
                                 ("AAPL", "2026-06-02", EC_STRONG)])
    plans = _originate(data_root, monkeypatch, stage2=True)

    assert plans, "fixture produced no plans"
    for plan in plans:
        block = plan["stage_tilt"]
        assert block["ec_source_state"] == psi.EC_SOURCE_AVAILABLE
        assert block["ec_source_tier"] == psi.EC_TIER_R2_HISTORY
        assert block["ec_sent"] == EC_STRONG
        assert block["eligible"] is True
        assert block["leash"] == pb.STAGE_TILT_LEASH == 1.25
    assert {p["horizon_days"] for p in plans} == {56}


def test_red_the_forward_shadow_cohort_is_no_longer_empty_by_source_absence(
        tmp_path, data_root, monkeypatch):
    """The shadow that ARMS the leash's auto-demote clause could never accrue a
    Stage-2 n earnings cohort, because its join had no source. It does now."""
    write_r2_history(data_root, [("AAA", "2026-06-01", EC_STRONG)])
    monkeypatch.delenv("COLLECT_LANE", raising=False)
    site_root = tmp_path / "site"
    (site_root / "prophet" / "plans").mkdir(parents=True)

    result = pss.tag_entries(root=tmp_path / "shadow", site_root=site_root)
    assert result["ec_source"]["state"] == psi.EC_SOURCE_AVAILABLE
    assert result["ec_source"]["tier"] == psi.EC_TIER_R2_HISTORY

    summary_source = psi.resolve_ec_source()
    assert summary_source["state"] == psi.EC_SOURCE_AVAILABLE


# --------------------------------------------------------------------------- #
# 2. Source identity, scale and the correction/PIT contract.                    #
# --------------------------------------------------------------------------- #
def test_native_scale_and_gate_are_byte_identical_to_the_promoted_construction():
    """The promoted arm's numbers. A restore that moved any of these would be a
    re-scaling of a promoted construction, not a repair."""
    assert psi.EC_SENT_GATE == 24
    assert psi.EC_SENT_NATIVE_MIN == -10
    assert psi.EC_SENT_NATIVE_MAX == 30
    assert pb.STAGE_TILT_LEASH == 1.25
    assert pb.HORIZON_DAYS_DEFAULT == 45
    assert round(pb.HORIZON_DAYS_DEFAULT * pb.STAGE_TILT_LEASH) == 56


@pytest.mark.parametrize("tier_writer", [write_r2_history, write_legacy_backfill])
def test_a_foreign_scale_is_rejected_from_every_tier(data_root, tier_writer):
    """A 0-100 gauge value and a -1..1 sentiment value are BOTH outside the native
    desk range and must be nulled on whichever tier they arrive on. The gate can never
    be reached by a foreign scale merely because the store moved address."""
    tier_writer(data_root, [("HI", "2026-06-01", 90.0),     # 0-100 gauge
                            ("LO", "2026-06-02", 0.8),      # -1..1 sentiment: in-range
                            ("NEG", "2026-06-03", -40.0),   # below the native floor
                            ("OK", "2026-06-04", EC_AT_GATE)])
    table, record = psi.load_ec_table_with_source()
    assert record["state"] == psi.EC_SOURCE_AVAILABLE
    idx = psi.ec_index(table)

    assert psi.ec_sent_at_entry(idx, "HI", "2026-07-01") is None
    assert psi.ec_sent_at_entry(idx, "NEG", "2026-07-01") is None
    # 0.8 IS inside the native range; it is simply a very weak desk reading, far below
    # the gate. Nulling it would be a second, invented rule.
    assert psi.ec_sent_at_entry(idx, "LO", "2026-07-01") == 0.8
    assert psi.ec_sent_at_entry(idx, "OK", "2026-07-01") == EC_AT_GATE


def test_the_native_clamp_is_applied_at_THE_FRAME_not_only_at_the_lookup(data_root):
    """BOTH guards must stay load-bearing.

    An out-of-native value is rejected twice: ``_normalise_ec_frame`` nulls it when the
    table is built, and ``_reject_out_of_native_ec_sent`` nulls it again at lookup. That
    redundancy means a test which only checks ``ec_sent_at_entry`` would stay green if
    the frame-level clamp were deleted — and the loaded TABLE would then carry foreign
    values for anything that reads it directly. This asserts the frame itself.
    """
    write_r2_history(data_root, [("HI", "2026-06-01", 90.0),
                                 ("NEG", "2026-06-02", -40.0),
                                 ("OK", "2026-06-03", EC_AT_GATE)])
    table, _record = psi.load_ec_table_with_source()
    by_ticker = table.set_index("ticker")["earnings_call_sent"]

    assert pd.isna(by_ticker["HI"]), "the frame-level native clamp was removed"
    assert pd.isna(by_ticker["NEG"]), "the frame-level native clamp was removed"
    assert by_ticker["OK"] == EC_AT_GATE
    live = table["earnings_call_sent"].dropna()
    assert live.between(psi.EC_SENT_NATIVE_MIN, psi.EC_SENT_NATIVE_MAX).all()


def test_the_generation_manifest_is_read_from_beside_the_payload_only(data_root):
    """The transported store is judged by ITS OWN sibling manifest.

    ``engine.earnings_qual``'s validator falls back to a repo-layout guess
    (``<root>/data/earnings_calls/manifest.json``) when no sibling exists, and
    ``lib.config.data_dir()`` is configurable — only conventionally named ``data``. Under
    a data root that guess cannot reconstruct, the fallback would judge this payload
    against a different generation's commit marker. Here the data root is NOT named
    ``data`` and a conflicting manifest sits where the guess would look; the store must
    still be accepted on its own terms.
    """
    from lib import config

    odd_root = data_root.parent / "not_named_data"
    (odd_root / "earnings_calls").mkdir(parents=True)
    write_r2_history(odd_root, [("MSFT", "2026-06-01", EC_STRONG)], manifest=False)

    # A foreign manifest exactly where the repo-layout fallback would look.
    decoy = data_root.parent / "data" / "earnings_calls"
    decoy.mkdir(parents=True, exist_ok=True)
    (decoy / "manifest.json").write_text(json.dumps({
        "schema": "earnings_intelligence_manifest.v3",
        "generation_id": "deadbeefdeadbeefdeadbeef",
        "scores": {"md5": "0" * 32, "rows": 1, "tickers": 1,
                   "key": "earnings_calls/generations/x/scores.parquet"},
        "history": {"md5": "0" * 32, "rows": 999, "tickers": 999,
                    "key": "earnings_calls/generations/x/history.parquet"},
    }), encoding="utf-8")

    config.data_dir = lambda: odd_root  # noqa: E731 - monkeypatched by the fixture's scope
    ok, why = psi._validate_transport(
        pd.DataFrame(), odd_root / "earnings_calls" / "history.parquet")
    assert (ok, why) == (None, "manifest_absent"), (
        "a payload with no sibling manifest was judged against a foreign one")

    _table, record = psi.load_ec_table_with_source()
    assert record["state"] == psi.EC_SOURCE_AVAILABLE
    assert record["tier"] == psi.EC_TIER_R2_HISTORY


def test_the_gate_edge_is_unchanged_on_the_restored_tier(data_root, monkeypatch):
    """At the gate tilts; one point below does not. The restored tier must not shift
    the boundary by so much as a rounding."""
    write_r2_history(data_root, [("MSFT", "2026-06-01", EC_AT_GATE),
                                 ("AAPL", "2026-06-01", EC_BELOW_GATE)])
    plans = {p["asset"]: p for p in _originate(data_root, monkeypatch, stage2=True)}
    assert plans["MSFT"]["horizon_days"] == 56
    assert plans["AAPL"]["horizon_days"] == 45
    assert plans["AAPL"]["stage_tilt"]["ec_sent"] == EC_BELOW_GATE
    assert plans["AAPL"]["stage_tilt"]["eligible"] is False


def test_point_in_time_and_correction_selection_are_identical_across_tiers(data_root):
    """The SAME rows, read from the R2 tier and from the legacy tier, produce the SAME
    readings: most recent call STRICTLY before the entry date, later call ignored, a
    same-day call not usable. The restore moved the address, never the rule.

    This is also the correction contract: the natural key and its correction clock
    (``max(updated_at)``) are resolved upstream by ``scripts/import_equitydesk_full.py``
    before either store is written, so both stores carry one row per corrected call and
    this layer's only time rule stays ``call_date < entry_date``.
    """
    rows = [("AAA", "2026-05-01", 10.0),   # older
            ("AAA", "2026-06-01", EC_STRONG),  # most recent PRIOR
            ("AAA", "2026-07-02", 29.0),   # same day as entry — not usable
            ("AAA", "2026-08-01", 28.0)]   # after entry — not usable

    r2_root = data_root
    write_r2_history(r2_root, rows)
    r2_table, r2_rec = psi.load_ec_table_with_source()

    legacy_only = data_root.parent / "legacy_data"
    legacy_only.mkdir(parents=True, exist_ok=True)
    write_legacy_backfill(legacy_only, rows)
    legacy_path = legacy_only / "stage_analysis" / "backfill" / "earnings_calls.parquet"
    legacy_table, legacy_rec = psi.load_ec_table_with_source(legacy_path)

    assert r2_rec["tier"] == psi.EC_TIER_R2_HISTORY
    assert legacy_rec["tier"] == psi.EC_TIER_EXPLICIT

    for table in (r2_table, legacy_table):
        idx = psi.ec_index(table)
        assert psi.ec_sent_at_entry(idx, "AAA", "2026-07-02") == EC_STRONG
        assert psi.ec_sent_at_entry(idx, "AAA", "2026-05-15") == 10.0
        assert psi.ec_sent_at_entry(idx, "AAA", "2026-04-01") is None
    pd.testing.assert_frame_equal(r2_table, legacy_table)


def test_the_repaired_ladder_never_reaches_the_minus_one_to_one_scores_artifact(data_root):
    """``data/earnings_calls/scores.parquet`` is a SIBLING of the restored store, in the
    very same directory, carrying a -1..1 ``sentiment``. Putting the governed history
    next to it must not make it reachable — that would be the exact re-scaling of a
    promoted construction the ticket forbids."""
    d = data_root / "earnings_calls"
    d.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"ticker": ["MSFT"], "sentiment": [0.9],
                  "call_date": pd.to_datetime(["2026-06-01"])}).to_parquet(
        d / "scores.parquet", index=False)

    for _tier, path, _transported in psi.ec_source_candidates():
        assert path.name != "scores.parquet"
        assert "earnings_calls/scores.parquet" not in path.as_posix()
    assert psi.resolve_ec_source()["state"] == psi.EC_SOURCE_UNAVAILABLE


def test_the_projected_cold_start_tiers_are_not_admitted(data_root):
    """engine.earnings_qual also falls back to ``equitydesk_overview.parquet`` and
    ``earnings_seed.parquet``. Those are PROJECTIONS — ``_normalise_earnings_source``
    reverse-calibrates a -1..1 score with ``sent * 18 + 12`` — so they are a different
    construction, not the same evidence at another address. A promoted gate may not
    start reading a synthesized value."""
    backfill = data_root / "stage_analysis" / "backfill"
    backfill.mkdir(parents=True, exist_ok=True)
    for name in ("equitydesk_overview.parquet", "earnings_seed.parquet"):
        pd.DataFrame({"ticker": ["MSFT"], "sentiment": [0.9],
                      "call_date": pd.to_datetime(["2026-06-01"])}).to_parquet(
            backfill / name, index=False)

    admitted = {path.name for _t, path, _v in psi.ec_source_candidates()}
    assert admitted == {"history.parquet", "earnings_calls.parquet"}
    assert psi.resolve_ec_source()["state"] == psi.EC_SOURCE_UNAVAILABLE


# --------------------------------------------------------------------------- #
# 3. Host-with-source / host-without-source / malformed / stale.                #
# --------------------------------------------------------------------------- #
def test_host_without_any_source_fails_open_and_discloses(data_root, monkeypatch):
    """The deploy host as it stands today. Empty table, null readings, leash 1.0, and a
    reason that names BOTH addresses so the reader knows what is missing."""
    table, record = psi.load_ec_table_with_source()
    assert table.empty and record["rows"] == 0
    assert record["state"] == psi.EC_SOURCE_UNAVAILABLE
    assert record["tier"] is None
    assert "history.parquet" in record["reason"]
    assert "earnings_calls.parquet" in record["reason"]
    assert record["path"].endswith("stage_analysis/backfill/earnings_calls.parquet")

    plans = _originate(data_root, monkeypatch, stage2=True)
    for plan in plans:
        block = plan["stage_tilt"]
        assert block["ec_source_state"] == psi.EC_SOURCE_UNAVAILABLE
        assert block["ec_source_tier"] is None
        assert block["ec_sent"] is None
        assert block["leash"] == 1.0
    assert {p["horizon_days"] for p in plans} == {45}


def test_host_with_only_the_legacy_source_still_reads_it(data_root):
    """The importing workstation. The legacy tier is not retired by the restore."""
    write_legacy_backfill(data_root, [("MSFT", "2026-06-01", EC_STRONG)])
    table, record = psi.load_ec_table_with_source()
    assert record["state"] == psi.EC_SOURCE_AVAILABLE
    assert record["tier"] == psi.EC_TIER_LEGACY
    assert record["generation"] is None
    assert psi.ec_sent_at_entry(psi.ec_index(table), "MSFT", "2026-07-02") == EC_STRONG


def test_a_malformed_transported_store_is_rejected_and_the_next_tier_answers(data_root):
    """A truncated / non-parquet download must never be read as evidence, and must not
    take the whole join down with it: the ladder falls through to the legacy store."""
    d = data_root / "earnings_calls"
    d.mkdir(parents=True, exist_ok=True)
    (d / "history.parquet").write_text("not a parquet")
    write_legacy_backfill(data_root, [("MSFT", "2026-06-01", EC_AT_GATE)])

    table, record = psi.load_ec_table_with_source()
    assert record["state"] == psi.EC_SOURCE_AVAILABLE
    assert record["tier"] == psi.EC_TIER_LEGACY
    assert [r["tier"] for r in record["rejected"]] == [psi.EC_TIER_R2_HISTORY]
    assert "unreadable" in record["rejected"][0]["reason"]
    assert psi.ec_sent_at_entry(psi.ec_index(table), "MSFT", "2026-07-02") == EC_AT_GATE


def test_a_malformed_store_with_no_fallback_is_an_honest_unavailable(data_root):
    """And with nothing behind it, a malformed store is unavailable WITH ITS REASON —
    never silently identical to a host that simply has no earnings data."""
    d = data_root / "earnings_calls"
    d.mkdir(parents=True, exist_ok=True)
    (d / "history.parquet").write_text("not a parquet")

    table, record = psi.load_ec_table_with_source()
    assert table.empty
    assert record["state"] == psi.EC_SOURCE_UNAVAILABLE
    assert "unreadable" in record["reason"]
    assert record["reason"] != psi.EC_ABSENT_REASON, (
        "a corrupt source and an absent source must not produce the same disclosure")


def test_a_stale_generation_manifest_rejects_the_transported_store(data_root):
    """THE STALE-SOURCE CASE. The manifest is the generation's commit marker. If the
    payload beside it is not the payload it commits to — a partially-replaced file, a
    rolled-back promote, a hand-edited store — the transported tier is rejected by name
    and the ladder falls through. The contract is the fetcher's own, not a second copy."""
    write_r2_history(data_root, [("MSFT", "2026-06-01", EC_STRONG)])
    # Replace the payload WITHOUT refreshing the manifest: md5/rows now disagree.
    _ec_frame([("MSFT", "2026-06-01", EC_STRONG),
               ("AAPL", "2026-06-02", EC_STRONG)]).to_parquet(
        data_root / "earnings_calls" / "history.parquet", index=False)
    write_legacy_backfill(data_root, [("MSFT", "2026-06-01", EC_BELOW_GATE)])

    table, record = psi.load_ec_table_with_source()
    assert record["tier"] == psi.EC_TIER_LEGACY, (
        "a store that does not match its generation manifest was used as evidence")
    assert [r["tier"] for r in record["rejected"]] == [psi.EC_TIER_R2_HISTORY]
    assert "rejected" in record["rejected"][0]["reason"]
    assert psi.ec_sent_at_entry(psi.ec_index(table), "MSFT", "2026-07-02") == EC_BELOW_GATE


def test_an_unsupported_manifest_schema_rejects_the_transported_store(data_root):
    """A future or foreign manifest schema is a refusal, not a shrug."""
    write_r2_history(data_root, [("MSFT", "2026-06-01", EC_STRONG)])
    manifest_path = data_root / "earnings_calls" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["schema"] = "earnings_intelligence_manifest.v99"
    manifest_path.write_text(json.dumps(manifest, default=str), encoding="utf-8")

    _table, record = psi.load_ec_table_with_source()
    assert record["state"] == psi.EC_SOURCE_UNAVAILABLE
    assert "manifest_schema_unsupported" in record["reason"]


def test_a_hand_placed_store_with_no_manifest_is_accepted_like_earnings_qual(data_root):
    """A store with no manifest beside it is a local/fixture file. engine.earnings_qual
    accepts that case; this module must not invent a stricter unilateral rule, or a
    developer's local copy would behave differently in the two consumers."""
    write_r2_history(data_root, [("MSFT", "2026-06-01", EC_STRONG)], manifest=False)
    _table, record = psi.load_ec_table_with_source()
    assert record["state"] == psi.EC_SOURCE_AVAILABLE
    assert record["tier"] == psi.EC_TIER_R2_HISTORY


def test_a_store_missing_a_governed_column_is_unreadable_not_partial(data_root):
    """A store without ``earnings_call_sent`` is not "the same table with nulls" — it is
    not this evidence at all, and must be rejected rather than silently answering None
    for every name."""
    d = data_root / "earnings_calls"
    d.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"document_ticker": ["MSFT"],
                  "call_date": pd.to_datetime(["2026-06-01"])}).to_parquet(
        d / "history.parquet", index=False)
    _table, record = psi.load_ec_table_with_source()
    assert record["state"] == psi.EC_SOURCE_UNAVAILABLE
    assert "unreadable" in record["reason"]


# --------------------------------------------------------------------------- #
# 4. Deploy-host proof — the REAL fetch shim, then the REAL origination.        #
# --------------------------------------------------------------------------- #
class _FakeR2:
    """A local-directory stand-in for the R2 bucket.

    Only the two read verbs ``scripts/fetch_earnings_scores.py`` uses are implemented —
    which is itself part of the proof that the restore path is read-only.
    """

    def __init__(self, store: Path):
        self.store = store
        self.reads: list[str] = []

    def get_object(self, Bucket: str, Key: str):  # noqa: N803 - boto3 signature
        self.reads.append(Key)
        body = (self.store / Key).read_bytes()
        return {"Body": type("B", (), {"read": staticmethod(lambda: body)})()}

    def download_file(self, bucket: str, key: str, target: str):
        self.reads.append(key)
        shutil.copyfile(self.store / key, target)


def _publish_generation_into(store: Path, rows) -> dict:
    """Lay out an immutable generation exactly as publish_earnings_r2 keys it."""
    staging = store / "_staging"
    staging.mkdir(parents=True, exist_ok=True)
    history = staging / "history.parquet"
    scores = staging / "scores.parquet"
    _ec_frame(rows).to_parquet(history, index=False)
    pd.DataFrame({"ticker": ["SPY"], "sentiment": [0.0]}).to_parquet(scores, index=False)
    manifest = _synth_manifest(scores, history)
    for name, filename in (("scores", "scores.parquet"), ("history", "history.parquet")):
        key = manifest[name]["key"]
        dest = store / key
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(staging / filename, dest)
    marker = store / "earnings_calls" / "manifest.json"
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(json.dumps(manifest, default=str), encoding="utf-8")
    return manifest


def test_deploy_host_hydrates_through_the_real_shim_then_prophet_sees_the_cohort(
        tmp_path, data_root, monkeypatch):
    """FAITHFUL DEPLOY-HOST PROOF.

    A bare host (no earnings data anywhere) runs the REAL
    ``scripts.fetch_earnings_scores.fetch`` against a bucket laid out exactly as
    ``publish_earnings_r2`` keys it — immutable generation objects plus the mutable
    manifest commit marker — with only the S3 client replaced by a local-directory
    stand-in. The shim's own manifest contract, md5/bytes/rows/tickers validation and
    atomic promote all run unmodified.

    Then the REAL Prophet origination runs against the hydrated root. This is the
    production sequence the nightly now performs: hydrate, then originate.
    """
    bucket_store = tmp_path / "r2"
    manifest = _publish_generation_into(bucket_store, [("MSFT", "2026-06-01", EC_STRONG),
                                                       ("AAPL", "2026-06-02", EC_STRONG)])
    fake = _FakeR2(bucket_store)
    monkeypatch.setattr(fes, "_client", lambda: fake)
    monkeypatch.setenv("R2_BUCKET", "macro-test")

    # Before hydration the host is starved — the state every runner was in.
    assert psi.resolve_ec_source()["state"] == psi.EC_SOURCE_UNAVAILABLE

    assert fes.fetch(data_dir=data_root) == 0
    assert (data_root / "earnings_calls" / "history.parquet").exists()
    assert (data_root / "earnings_calls" / "manifest.json").exists()

    # It came down the generation keys, and nothing was written back.
    assert manifest["history"]["key"] in fake.reads
    assert all(not k.endswith("_staging") for k in fake.reads)

    record = psi.resolve_ec_source()
    assert record["state"] == psi.EC_SOURCE_AVAILABLE
    assert record["tier"] == psi.EC_TIER_R2_HISTORY
    assert record["generation"]["generation_id"] == manifest["generation_id"]
    # The vintage must actually be disclosed, not silently null: publish_earnings_r2
    # stamps the publish time under "built", so reading only "generated_at" reports None
    # for every real generation.
    assert record["generation"]["published_at"] == manifest["built"]

    plans = _originate(data_root, monkeypatch, stage2=True)
    assert plans
    for plan in plans:
        assert plan["stage_tilt"]["ec_source_state"] == psi.EC_SOURCE_AVAILABLE
        assert plan["stage_tilt"]["ec_sent"] == EC_STRONG
    assert {p["horizon_days"] for p in plans} == {56}


def test_the_nightly_hydrates_before_prophet_originates():
    """THE ORDERING HALF OF THE DEFECT. The restore is worthless if the store lands
    after the plans are written, which is exactly what used to happen: the only
    hydration call sat ~840 lines below the Prophet step in the same job."""
    import yaml

    workflow = yaml.safe_load((_REPO / ".github/workflows/daily.yml").read_text())
    steps = workflow["jobs"]["engine"]["steps"]
    names = [str(s.get("name") or "") for s in steps]

    hydrate = [i for i, n in enumerate(names) if "Restore EquityDesk earnings history" in n]
    prophet = [i for i, n in enumerate(names) if n.startswith("Prophet nightly")]
    assert len(hydrate) == 1 and len(prophet) == 1
    assert hydrate[0] < prophet[0], (
        "the earnings store is hydrated AFTER Prophet originates — the cohort is starved")

    step = steps[hydrate[0]]
    assert "scripts.fetch_earnings_scores" in step["run"]
    # The generation step must still carry no R2 credentials: this restore is read-only
    # and must not widen Prophet's publish authority.
    assert not (steps[prophet[0]].get("env") or {}).keys() & {
        "R2_ENDPOINT", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_BUCKET"}


# --------------------------------------------------------------------------- #
# 5. The fetch/publish pair now closes: producer -> transport -> consumer.       #
# --------------------------------------------------------------------------- #
def _run_importer(root: Path):
    """Run the real EquityDesk importer against the committed mini fixture, fully
    contained inside ``root``. Mirrors tests/test_import_equitydesk.py's harness."""
    import importlib

    import scripts.import_equitydesk_full as imp
    importlib.reload(imp)
    imp._REPO_ROOT = root
    imp.BACKFILL_SRC = Path(__file__).parent / "fixtures" / "ed_mini"
    imp.SEED_DIR = root / "seed"
    imp.MANIFEST_PATH = imp.SEED_DIR / "_manifest.json"
    imp.EARNINGS_RECONCILIATION_PATH = (
        root / "data" / "quality" / "earnings_import_reconciliation.json")
    imp.main()
    return imp


def test_the_importer_stages_the_frame_at_the_transport_address(tmp_path):
    """THE PUBLISH HALF. The import used to write the numeric archive ONLY to the
    workstation seed, which has no publisher — which is why the artifact never had a
    fetch/publish pair and never reached a single CI or deploy host. It now also stages
    the identical frame at the address the existing publisher already ships.
    """
    root = tmp_path / "repo"
    root.mkdir()
    imp = _run_importer(root)

    seed = root / "seed" / "earnings_calls.parquet"
    staged = imp.transport_earnings_history_path()
    assert seed.exists(), "fixture import produced no seed"
    assert staged == root / "data" / "earnings_calls" / "history.parquet"
    assert staged.exists(), (
        "the import still leaves nothing at the transport address — the artifact has no "
        "fetch/publish pair and every CI host stays starved")

    # The SAME evidence, not a re-derivation: identical frames, identical native columns.
    pd.testing.assert_frame_equal(pd.read_parquet(seed), pd.read_parquet(staged))
    cols = set(pd.read_parquet(staged).columns)
    assert {"document_ticker", "call_date", "earnings_call_sent"} <= cols


def test_the_staged_frame_is_readable_by_the_prophet_ladder(tmp_path, monkeypatch):
    """And what it stages is exactly what the restored ladder reads: the staged file,
    moved to a data root, answers as the r2_history tier on the native scale."""
    root = tmp_path / "repo"
    root.mkdir()
    imp = _run_importer(root)
    staged = imp.transport_earnings_history_path()

    data = tmp_path / "data"
    (data / "earnings_calls").mkdir(parents=True)
    shutil.copyfile(staged, data / "earnings_calls" / "history.parquet")
    from lib import config
    monkeypatch.setattr(config, "data_dir", lambda: data)

    table, record = psi.load_ec_table_with_source()
    assert record["state"] == psi.EC_SOURCE_AVAILABLE
    assert record["tier"] == psi.EC_TIER_R2_HISTORY
    assert record["rows"] > 0

    # The mini fixture's AAPL call is 26 on the native desk scale — above the gate.
    sent = psi.ec_sent_at_entry(psi.ec_index(table), "AAPL", "2026-07-02")
    assert sent == 26.0
    assert psi.EC_SENT_NATIVE_MIN <= sent <= psi.EC_SENT_NATIVE_MAX
    assert sent >= psi.EC_SENT_GATE


def test_the_importer_writes_nothing_outside_the_root_it_was_given(tmp_path):
    """REGRESSION GUARD. The transport path must resolve at CALL time from _REPO_ROOT.
    A module-level constant frozen at import kept pointing at the real checkout, so a
    test run wrote a fixture-sized parquet into it — and stayed invisible, because
    data/earnings_calls/ is gitignored. Anything the importer writes must land under the
    root it was handed."""
    import scripts.import_equitydesk_full as imp

    root = tmp_path / "repo"
    root.mkdir()
    real_transport = _REPO / "data" / "earnings_calls" / "history.parquet"
    existed_before = real_transport.exists()

    imp = _run_importer(root)
    assert imp.transport_earnings_history_path().is_relative_to(root)
    assert real_transport.exists() is existed_before, (
        "the importer wrote into the real checkout while running against a tmp root")


def test_publishing_and_restoring_use_the_address_the_importer_stages(tmp_path):
    """One address, agreed by all four parties: importer stages it, publisher ships it,
    fetcher restores it, Prophet reads it. That agreement is what makes this a restored
    pair rather than four opinions."""
    import scripts.import_equitydesk_full as imp
    from scripts import publish_earnings_r2 as pub

    staged = imp.transport_earnings_history_path().name
    assert staged == "history.parquet"
    assert staged in pub._EARNINGS_FILES
    assert staged in fes._EARNINGS_FILES
    transported = [parts for _t, parts, v in psi.EC_SOURCE_TIERS if v]
    assert transported == [("earnings_calls", staged)]


# --------------------------------------------------------------------------- #
# 6. No duplicate data or control plane was created.                            #
# --------------------------------------------------------------------------- #
def test_the_restore_reuses_the_existing_earnings_r2_plane_only():
    """The addresses this module resolves are the addresses the EXISTING publisher
    writes and the EXISTING fetcher restores — not a new key family, bucket or prefix."""
    from scripts import publish_earnings_r2 as pub

    assert pub._R2_PREFIX == fes._R2_PREFIX == "earnings_calls"
    assert "history.parquet" in pub._EARNINGS_FILES
    assert "history.parquet" in fes._EARNINGS_FILES

    transported = [parts for _t, parts, v in psi.EC_SOURCE_TIERS if v]
    assert transported == [("earnings_calls", "history.parquet")], (
        "the transported tier must be the file the existing fetcher already writes")


def test_no_second_transport_client_or_registry_was_introduced():
    """``prophet_stage_inputs`` must not grow its own object-store client, credentials,
    bucket name or registry. It resolves paths on the local filesystem; the ONE transport
    is the earnings R2 pair."""
    source = (_REPO / "engine" / "prophet_stage_inputs.py").read_text(encoding="utf-8")
    for forbidden in ("boto3", "R2_ENDPOINT", "R2_BUCKET", "R2_ACCESS_KEY_ID",
                      "endpoint_url", "download_file", "get_object", "sqlite3",
                      "psycopg", "requests.", "urlopen"):
        assert forbidden not in source, f"{forbidden} appeared in the inputs module"

    reporter = (_REPO / "scripts" / "report_prophet_earnings_source.py").read_text(
        encoding="utf-8")
    for forbidden in ("boto3", "download_file", "to_parquet", "R2_SECRET_ACCESS_KEY"):
        assert forbidden not in reporter, f"the reporter is not read-only: {forbidden}"


def test_there_is_exactly_one_transport_contract_validator():
    """Prophet validates the transported store with engine.earnings_qual's OWN validator,
    so the two consumers can never disagree about whether a generation is intact."""
    assert psi._validate_transport.__module__ == "engine.prophet_stage_inputs"
    assert earnings_qual.validate_transport_frame(
        pd.DataFrame(), Path("/nonexistent/data/earnings_calls/history.parquet"),
        "history", root=Path("/nonexistent"),
    ) == (None, "manifest_absent")

    source = (_REPO / "engine" / "prophet_stage_inputs.py").read_text(encoding="utf-8")
    assert "earnings_qual.validate_transport_frame" in source
    # and no local re-implementation of the contract
    assert "earnings_intelligence_manifest" not in source


def test_prophet_tiers_are_the_native_prefix_of_the_earnings_qual_ladder():
    """ONE ladder, one order. engine.earnings_qual's ladder is the canonical ordering of
    EquityDesk stores; Prophet takes its NATIVE prefix — same tier names, same order, the
    projected cold-start tiers dropped. If either side is reordered this goes red."""
    eq_ladder = earnings_qual._backfill_earnings_candidates(_REPO)
    eq_names = [name for name, _p in eq_ladder]
    psi_names = [tier for tier, _parts, _v in psi.EC_SOURCE_TIERS]

    assert eq_names[:2] == psi_names == ["r2_history", "legacy_full_history"]
    assert eq_names[2:] == ["committed_overview_fallback", "committed_score_seed_fallback"]

    eq_rel = [p.relative_to(_REPO / "data").as_posix() for _n, p in eq_ladder[:2]]
    psi_rel = ["/".join(parts) for _t, parts, _v in psi.EC_SOURCE_TIERS]
    assert eq_rel == psi_rel, "the two consumers resolve different files for the same tier"


def test_the_disclosure_still_never_enters_the_eligibility_test(data_root):
    """``ec_source_tier`` joins ``ec_source_state`` as DISCLOSURE. Neither may move the
    leash — only stage, the gate and the ratified conjunction do."""
    from tests.test_prophet_stage_tilt import _tilt_inputs

    base = _tilt_inputs()
    horizon, block = pb._compute_stage_tilt("AAA", "2026-07-01", base)
    assert horizon == 56 and block["leash"] == pb.STAGE_TILT_LEASH

    for tier in (psi.EC_TIER_R2_HISTORY, psi.EC_TIER_LEGACY, None):
        ti = dict(base)
        ti["ec_source"] = {**(base.get("ec_source") or {}), "tier": tier}
        h, b = pb._compute_stage_tilt("AAA", "2026-07-01", ti)
        assert h == horizon and b["leash"] == block["leash"] and b["eligible"] is True
        assert b["ec_source_tier"] == tier


# --------------------------------------------------------------------------- #
# Shared origination driver.                                                    #
# --------------------------------------------------------------------------- #
def _originate(data_root: Path, monkeypatch, *, stage2: bool) -> list[dict]:
    """Run the real ``pb.originate_plans`` against ``data_root``.

    Only the Weinstein stage lookup and the price loader are substituted — the stage arm
    is not what these tests exercise, and the earnings arm stays fully real end to end.
    """
    (data_root / "regime").mkdir(parents=True, exist_ok=True)
    (data_root / "regime" / "latest.json").write_text(json.dumps({
        "risk_radar": {"context_gate": {"spy_below_200dma": False}, "state": "caution"}
    }))
    if stage2:
        monkeypatch.setattr(psi, "stage_at_entry",
                            lambda close, vol, bench, entry_date: (2, 5, 100))
        monkeypatch.setattr(psi, "load_ticker_prices", lambda ticker, root: (
            pd.Series(range(400), dtype=float,
                      index=pd.bdate_range("2020-01-01", periods=400)) + 100.0, None))

    work = data_root.parent / "work"
    work.mkdir(parents=True, exist_ok=True)
    board = work / "us_standouts.json"
    board.write_text(json.dumps({
        "as_of": "2026-07-02",
        "staleness": {"price_through": "2026-07-02", "delayed": False, "unknown": False,
                      "basis": "panel_majority",
                      "inputs": {"panel": {"mixed_vintage": False}}},
        "gate_go": False,
        "buy": [_buy("MSFT", 80, 420.0), _buy("AAPL", 70, 150.0)],
    }))
    return pb.originate_plans(board, asof="2026-07-02", existing_ids=set(),
                              thetadata_store=None)


def _buy(ticker: str, score: int, spot: float) -> dict:
    return {
        "ticker": ticker, "dir": "up", "state": "TURN SIGNALED",
        "conviction": {"score": score, "band": "neutral", "drivers": ["momentum"],
                       "cautions": ["macro risk"], "trust_tier": {"en": "tier-2"}},
        "entry_signal": {"act_level": 3, "status": "partial", "spot": spot,
                         "stop": spot * 0.95, "chase_above": spot * 1.05,
                         "atr_pct": 2.0, "entry_grade": "solid",
                         "horizon": {"d21": 0.5}},
        "hold": {"state": "HOLD", "anchor": "2026-07-02", "invalidation": spot * 0.90},
        "coiled": {"coiled": False, "star": False},
        "signal": {"above200": True, "weekly_bull": True},
    }
