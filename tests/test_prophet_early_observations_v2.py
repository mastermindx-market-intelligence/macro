"""Tests for the prospective per-query source-bound coverage extension of B03.

Task B extends `engine.prophet_early_observations` and `app.prophet_observations` so
each row carries typed source-bound coverage (NOT_IN_UNIVERSE / IN_UNIVERSE_NO_RECORDED_TRIGGER
/ UNAVAILABLE) and source timing context (asof, close, reset/off_reset_low_pct, native
slow-tier facts).  These tests pin the new fields, the failure behaviour and the
invariants the existing B03 contract already enforces.

Frozen contract law:
  * Literal ``buy/alert/entry_open/rank/size/episode_write`` stay FALSE for every row.
  * Existing B1 IDs / receipt semantics, auth-before-read, private/no-store framing,
    snapshot pagination, query validation, latest corrupt / future-data handling are
    preserved unchanged.
  * The new coverage slots are EXTENSIONS, never overrides of the existing fields.
  * WM (in v2 only) and KO (in both) carry the right typed coverage against the
    active universe contract.
"""
from __future__ import annotations

import importlib
import importlib.util
import json
from copy import deepcopy
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from engine.us_candidate_episode_intake import load_identity_spine
from scripts.build_turn_watch import write_candidate_episode_input


@pytest.fixture
def api():
    assert importlib.util.find_spec("engine.prophet_early_observations"), "B03 read model is absent"
    return importlib.import_module("engine.prophet_early_observations")


def _row_template(ticker: str, *, fired: bool, blocking, session: str,
                  close: float, asof: str | None = None,
                  reset_low: float = 245.96, reset_low_date: str = "2026-09-16",
                  off_reset_low_pct: float = 0.62,
                  slow_tier_extra: dict | None = None) -> dict:
    """A row that includes the new source-bound coverage context."""
    slow = {"evaluated": True, "eligible": fired is False,
           "blocking": blocking,
           "tier": None if fired else None,
           "bars_to_cross_3d": None,
           "above_200dma": True,
           "null_legs": {}}
    if slow_tier_extra:
        slow.update(slow_tier_extra)
    row = {"ticker": ticker, "asof": asof or session, "close": close,
           "triggers_fired": ["pre_confluence_2d"] if fired else [],
           "triggers": {"pre_confluence_2d": {
               "fired": fired, "evaluated": True,
               "last_date": session if fired else None}},
           "slow_tier": slow,
           "reset": {"reset_low": reset_low, "reset_low_date": reset_low_date,
                     "off_reset_low_pct": off_reset_low_pct}}
    return row


def seed_with_universe(tmp_path, *, tickers=("AMZN",), session="2026-10-08",
                       universe_path: Path | None = None):
    """Seed a B03 source with the new source-bound coverage context.

    ``universe_path`` is the file containing the active universe contract.  When None,
    no universe is provided and coverage is forced into UNAVAILABLE.
    """
    data = tmp_path / "data"
    ref = data / "reference"
    ref.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([{"security_id": f"SEC:US-XNAS-{t}", "issuer_id": f"ISS:US-XNAS-{t}",
                   "issuer_state": "ACTIVE", "listing_key": f"US-XNAS-{t}"}
                  for t in tickers]).to_parquet(ref / "security_master.parquet", index=False)
    pd.DataFrame([{"vendor": "membership", "vendor_symbol": t,
                   "security_id": f"SEC:US-XNAS-{t}", "valid_from": date(2020, 1, 1),
                   "valid_to": None} for t in tickers]).to_parquet(ref / "vendor_aliases.parquet", index=False)
    rows = [_row_template(t, fired=True, blocking=["macd_below_signal"],
                          session=session, close=246.5,
                          off_reset_low_pct=0.21 + 0.01 * i)
            for i, t in enumerate(tickers)]
    artifact = {"schema": "us_turn_watch.v1", "data_session": session,
                "selection_era": "anticipation-v1", "anchor_era": "anchor-v1",
                "triggers": {"pre_confluence_2d": {"en": "Pre-confluence 2D"}},
                "deck": rows[:40],
                "beyond_cap": [{"ticker": r["ticker"]} for r in rows[40:]],
                "coverage": {"triggered": len(rows), "deck": min(40, len(rows)),
                             "beyond_cap": max(0, len(rows) - 40)}}
    version = 2 if session >= "2026-10-19" else 1
    manifest = json.loads((_repo_v2_universe() if version == 2 else _repo_v1_universe()).read_text())
    artifact["selection_era"] = manifest["selection_era"]
    contract = {key: manifest[key] for key in
                ("universe_id", "selection_era", "population_count", "tickers_sha256")}
    contract.update({"schema": "us_turn_watch.source_contract.v1", "pass": True,
                     "selected_count": manifest["population_count"], "universe_limit": None,
                     "missing_store_count": 0, "modal_session": session, "freshness_ok": True})
    artifact["coverage"]["source_contract"] = contract
    path = write_candidate_episode_input(artifact, rows, data)
    from engine.us_turn_watch import write_artifact
    write_artifact(artifact, tmp_path / "site")
    # Optionally copy an active universe contract beside the source.
    if universe_path is not None and universe_path.exists():
        import shutil
        target = tmp_path / "config" / universe_path.name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(universe_path, target)
    return path, load_identity_spine(data), rows, artifact


def _repo_v2_universe() -> Path:
    import engine.us_turn_watch as _tw
    return Path(_tw.__file__).resolve().parents[1] / "config" / "us_turn_watch_universe.v2.json"


def _repo_v1_universe() -> Path:
    return _REPO_V1_PATH


_REPO_V1_PATH = Path(
    importlib.import_module("engine.us_turn_watch").__file__
).resolve().parents[1] / "config" / "us_turn_watch_universe.v1.json"


# ─────────────────────────────────────────────────────────────────────────────
# (1) Coverage contract — typed slot names, schema-stable
# ─────────────────────────────────────────────────────────────────────────────


def test_source_coverage_state_constants_are_pinned(api):
    """Every coverage slot is one of these three literals, no None hiding an in-between."""
    assert api.SOURCE_COVERAGE_NOT_IN_UNIVERSE == "NOT_IN_UNIVERSE"
    assert api.SOURCE_COVERAGE_IN_UNIVERSE_NO_RECORDED_TRIGGER == "IN_UNIVERSE_NO_RECORDED_TRIGGER"
    assert api.SOURCE_COVERAGE_UNAVAILABLE == "UNAVAILABLE"
    assert api.SOURCE_COVERAGE_VERIFIED == "VERIFIED_SOURCE_PARTITION"


def test_load_observations_accepts_an_active_universe_contract(api, tmp_path):
    """The loader accepts an explicit active-universe contract for era-aware coverage."""
    source, spine, _, _ = seed_with_universe(tmp_path, tickers=("AMZN",), session="2026-10-08")
    contract = json.loads(_repo_v1_universe().read_text())
    projection = api.load_observations(
        source, spine=spine, reference_session="2026-10-08",
        public_artifact_path=tmp_path / "site/turn_watch/turn_watch.json",
        active_universe=contract,
    )
    assert projection["status"] == "CURRENT_SESSION"
    assert projection["coverage"]["state"] == api.SOURCE_COVERAGE_VERIFIED
    assert projection["universe_coverage"]["state"] == api.SOURCE_COVERAGE_VERIFIED


def test_load_observations_without_universe_is_typed_unavailable(api, tmp_path):
    """A missing active universe contract is reported as UNAVAILABLE — not silently absent."""
    source, spine, _, _ = seed_with_universe(tmp_path, tickers=("AMZN",), session="2026-10-08")
    projection = api.load_observations(
        source, spine=spine, reference_session="2026-10-08",
        public_artifact_path=tmp_path / "site/turn_watch/turn_watch.json",
    )
    assert projection["universe_coverage"]["state"] == api.SOURCE_COVERAGE_UNAVAILABLE
    assert "ACTIVE_UNIVERSE_UNAVAILABLE" in projection["universe_coverage"]["reason"]


def test_universe_coverage_publication_mismatch_fails_closed(api, tmp_path, monkeypatch):
    """A publication proof hash mismatch is reported as UNAVAILABLE — not silently 'ok'."""
    source, spine, _, _ = seed_with_universe(tmp_path, tickers=("AMZN",), session="2026-10-08")
    contract = json.loads(_repo_v1_universe().read_text())
    contract["tickers_sha256"] = "0" * 64
    projection = api.load_observations(
        source, spine=spine, reference_session="2026-10-08",
        public_artifact_path=tmp_path / "site/turn_watch/turn_watch.json",
        active_universe=contract,
    )
    assert projection["universe_coverage"]["state"] == api.SOURCE_COVERAGE_UNAVAILABLE


# ─────────────────────────────────────────────────────────────────────────────
# (2) Per-row coverage semantics for the WM/KO cases
# ─────────────────────────────────────────────────────────────────────────────


def test_ko_against_v1_universe_is_in_universe_no_recorded_trigger(api, tmp_path):
    source, spine, _, _ = seed_with_universe(tmp_path)
    projection = api.load_observations(source, spine=spine, reference_session="2026-10-08",
        public_artifact_path=tmp_path / "site/turn_watch/turn_watch.json",
        active_universe=json.loads(_repo_v1_universe().read_text()))
    page = api.query_observations(projection, ticker="KO")
    assert page["counts"]["matched"] == 0 and page["rows"] == []
    assert page["subject_coverage"] == {"ticker": "KO",
        "state": api.SOURCE_COVERAGE_IN_UNIVERSE_NO_RECORDED_TRIGGER, "reason": None}


def test_wm_against_v1_universe_is_not_in_universe(api, tmp_path):
    source, spine, _, _ = seed_with_universe(tmp_path)
    projection = api.load_observations(source, spine=spine, reference_session="2026-10-08",
        public_artifact_path=tmp_path / "site/turn_watch/turn_watch.json",
        active_universe=json.loads(_repo_v1_universe().read_text()))
    page = api.query_observations(projection, ticker="WM")
    assert page["rows"] == [] and page["counts"]["matched"] == 0
    assert page["subject_coverage"]["state"] == api.SOURCE_COVERAGE_NOT_IN_UNIVERSE


def test_wm_against_v2_universe_is_in_universe_no_recorded_trigger(api, tmp_path):
    source, spine, _, _ = seed_with_universe(tmp_path, session="2026-10-19")
    projection = api.load_observations(source, spine=spine, reference_session="2026-10-19",
        public_artifact_path=tmp_path / "site/turn_watch/turn_watch.json",
        active_universe=json.loads(_repo_v2_universe().read_text()))
    page = api.query_observations(projection, ticker="WM")
    assert page["rows"] == [] and page["counts"]["matched"] == 0
    assert page["subject_coverage"]["state"] == api.SOURCE_COVERAGE_IN_UNIVERSE_NO_RECORDED_TRIGGER


# ─────────────────────────────────────────────────────────────────────────────
# (3) Source timing context (asof, close, reset, slow-tier facts)
# ─────────────────────────────────────────────────────────────────────────────


def test_row_payload_carries_source_timing_context(api, tmp_path):
    """The new per-row timing context is surfaced verbatim, never substituted for fresh."""
    source, spine, _, _ = seed_with_universe(tmp_path, tickers=("AMZN",), session="2026-10-08")
    contract = json.loads(_repo_v1_universe().read_text())
    projection = api.load_observations(
        source, spine=spine, reference_session="2026-10-08",
        public_artifact_path=tmp_path / "site/turn_watch/turn_watch.json",
        active_universe=contract,
    )
    page = api.query_observations(projection, ticker="AMZN")
    row = page["rows"][0]
    assert row["source_timing"]["asof"] == "2026-10-08"
    assert row["source_timing"]["close"] == 246.5
    assert row["source_timing"]["reset_low"] == 245.96
    assert row["source_timing"]["reset_low_date"] == "2026-09-16"
    assert row["source_timing"]["off_reset_low_pct"] == pytest.approx(0.21)
    # Native slow-tier facts are surfaced without recomputation.
    assert row["source_timing"]["slow_tier_eligible"] is False
    assert row["source_timing"]["slow_tier_tier"] is None
    assert row["source_timing"]["slow_tier_blocking"] == ["macd_below_signal"]


def test_stale_row_asof_cannot_inherit_fresh_root_clock(api, tmp_path):
    """A prior-session observation row carries its OWN asof — never the query reference."""
    source, spine, _, _ = seed_with_universe(tmp_path, tickers=("AMZN",), session="2026-10-06")
    contract = json.loads(_repo_v1_universe().read_text())
    projection = api.load_observations(
        source, spine=spine, reference_session="2026-10-08",
        public_artifact_path=tmp_path / "site/turn_watch/turn_watch.json",
        active_universe=contract,
    )
    assert projection["status"] == "RETAINED_PREVIOUS_SESSION"
    page = api.query_observations(projection, ticker="AMZN")
    row = page["rows"][0]
    assert row["source_timing"]["asof"] == "2026-10-06"  # never "2026-10-08"
    assert projection["clocks"]["source_session"] == "2026-10-06"


def test_future_session_source_is_rejected(api, tmp_path):
    """A source dated AFTER the query reference never becomes the current session."""
    source, spine, _, _ = seed_with_universe(tmp_path, tickers=("AMZN",), session="2026-10-15")
    contract = json.loads(_repo_v1_universe().read_text())
    projection = api.load_observations(
        source, spine=spine, reference_session="2026-10-08",
        public_artifact_path=tmp_path / "site/turn_watch/turn_watch.json",
        active_universe=contract,
    )
    assert projection["status"] == "UNAVAILABLE"
    assert projection["reason"] in ("SOURCE_MALFORMED", "SOURCE_AHEAD_OF_REFERENCE")


# ─────────────────────────────────────────────────────────────────────────────
# (4) Frozen B03 invariants
# ─────────────────────────────────────────────────────────────────────────────


def test_authority_remains_all_false_for_every_row(api, tmp_path):
    """The literal B1 IDs and BUY/ALERT/ENTRY authority stay FALSE on the extended rows."""
    source, spine, _, _ = seed_with_universe(tmp_path, tickers=("AMZN",), session="2026-10-08")
    contract = json.loads(_repo_v1_universe().read_text())
    projection = api.load_observations(
        source, spine=spine, reference_session="2026-10-08",
        public_artifact_path=tmp_path / "site/turn_watch/turn_watch.json",
        active_universe=contract,
    )
    page = api.query_observations(projection, ticker="AMZN")
    for row in page["rows"]:
        for v in row["authority"].values():
            assert v is False


def test_auth_before_read_still_required(api, tmp_path):
    """`query_observations` still rejects malformed queries without any source read."""
    with pytest.raises(api.ObservationQueryError):
        api.query_observations({"status": "CURRENT_SESSION", "rows": [], "coverage": {"state": "OK"},
                                "snapshot_id": "early:00"}, ticker="WM", security_id="bad@id")


def test_snapshot_invalidation_still_pins_pagination(api, tmp_path):
    """A changed receipt invalidates pagination even when the row shape is identical."""
    source, spine, rows, artifact = seed_with_universe(tmp_path, tickers=("AMZN",), session="2026-10-08")
    contract = json.loads(_repo_v1_universe().read_text())
    first = api.load_observations(
        source, spine=spine, reference_session="2026-10-08",
        public_artifact_path=tmp_path / "site/turn_watch/turn_watch.json",
        active_universe=contract,
    )
    old = first["snapshot_id"]
    rows[0]["reset"]["reset_low"] = 246.0
    write_candidate_episode_input(artifact, rows, tmp_path / "data")
    from engine.us_turn_watch import write_artifact
    write_artifact(artifact, tmp_path / "site")
    # Re-load so the projection's snapshot_id reflects the new source bytes.
    changed = api.load_observations(
        source, spine=spine, reference_session="2026-10-08",
        public_artifact_path=tmp_path / "site/turn_watch/turn_watch.json",
        active_universe=contract,
    )
    assert changed["snapshot_id"] != old
    with pytest.raises(api.ObservationQueryError):
        api.query_observations(changed, ticker="AMZN", expected_snapshot=old)


def test_latest_corrupt_sidecar_fails_closed(api, tmp_path):
    """A tampered content_sha invalidates the projection; coverage is UNAVAILABLE."""
    source, spine, _, _ = seed_with_universe(tmp_path, tickers=("AMZN",), session="2026-10-08")
    doc = json.loads(source.read_text())
    doc["rows"] = [{"ticker": "FORGED"}]
    source.write_text(json.dumps(doc))
    contract = json.loads(_repo_v1_universe().read_text())
    projection = api.load_observations(
        source, spine=spine, reference_session="2026-10-08",
        public_artifact_path=tmp_path / "site/turn_watch/turn_watch.json",
        active_universe=contract,
    )
    assert projection["status"] == "UNAVAILABLE"
    assert projection["universe_coverage"]["state"] == api.SOURCE_COVERAGE_UNAVAILABLE


def test_public_partition_mismatch_marks_unavailable(api, tmp_path):
    """Manifest integrity alone cannot certify the source artifact's membership."""
    source, spine, _, _ = seed_with_universe(tmp_path)
    (tmp_path / "site/turn_watch/turn_watch.json").write_text("{}")
    projection = api.load_observations(source, spine=spine, reference_session="2026-10-08",
        public_artifact_path=tmp_path / "site/turn_watch/turn_watch.json",
        active_universe=json.loads(_repo_v1_universe().read_text()))
    assert projection["coverage"]["state"] == api.SOURCE_COVERAGE_UNAVAILABLE
    assert projection["universe_coverage"]["state"] == api.SOURCE_COVERAGE_UNAVAILABLE


# ─────────────────────────────────────────────────────────────────────────────
# (5) API integration in app.prophet_observations (no extra imports at module top)
# ─────────────────────────────────────────────────────────────────────────────


def test_app_observations_loads_active_universe_from_engine(monkeypatch, tmp_path):
    """The app layer threads the active universe contract through the loader."""
    import app.prophet_observations as app_obs
    import engine.prophet_early_observations as epo
    source, spine, _, _ = seed_with_universe(tmp_path, tickers=("AMZN",), session="2026-10-08")
    monkeypatch.setattr(app_obs, "_DATA_ROOT", tmp_path / "data")
    monkeypatch.setattr(app_obs, "expected_last_session", lambda: date(2026, 10, 8))
    captured = {}
    real_load = epo.load_observations
    def fake_load(p, **kw):
        captured["active_universe"] = kw.get("active_universe")
        captured["reference_session"] = kw.get("reference_session")
        return real_load(p, **kw)
    monkeypatch.setattr(epo, "load_observations", fake_load)
    monkeypatch.setattr(app_obs, "_read_active_universe",
                        lambda root, source_session: json.loads(_repo_v1_universe().read_text()))
    app_obs.read_current_observations()
    assert captured["reference_session"] == "2026-10-08"
    assert captured["active_universe"] is not None
    assert captured["active_universe"]["selection_era"] == "anticipation-v1-2026-08-08"