"""Tests for the prospective US Turn Watch universe v2 — selection era anticipation-v2-2026-10-19.

These tests cover the contract file itself (config/us_turn_watch_universe.v2.json), the
active-selection-era dispatcher, and the wiring that lets WM and other liquid names from
the canonical outcome-independent US membership roster reach the engine after v1's
selection-era is past.  All behavioural assertions run on synthetic data — the live
price store, calendar and macro data dirs are never read.

Frozen contract law (echoed from the plan):
  * config/us_turn_watch_universe.v1.json stays byte-identical.
  * config/us_turn_watch_universe.v2.json carries its own schema, era, source commit,
    source tree, store blob SHA1, membership digest and exclusion list.
  * Selection era activates only when an actual completed session >= 2026-10-19 lands;
    a missing/tampered v2 contract after that activation FAILS CLOSED — the engine
    never falls back to v1 or to raw-directory enumeration.
  * Before activation, v1 remains the active contract and its results stay byte-stable.
"""
from __future__ import annotations

import hashlib
import inspect
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pytest

from engine import us_turn_watch as TW


_REPO = Path(TW.__file__).resolve().parents[1]
_V2_PATH = _REPO / "config" / "us_turn_watch_universe.v2.json"
_V1_PATH = _REPO / "config" / "us_turn_watch_universe.v1.json"
_V1_DIGEST = "9f9daa60db10bce3edc65a8d4b8e02e79ee327c962bec46d2973d32791752282"
_V2_ACTIVATION = "2026-10-19"


def _write_v2_contract(target_root: Path, *, overrides: dict | None = None,
                       source_payload: dict | None = None) -> Path:
    """Write a v2 contract at ``target_root/config/us_turn_watch_universe.v2.json``.

    The engine resolves the contract under ``data_root.parent/config`` so callers
    pass the directory whose ``data`` subdirectory will be used as ``data_root``.
    Passing the repo root's ``data`` subdirectory as ``target_root`` writes the
    contract where the production loader looks for it.
    """
    base = source_payload if source_payload is not None else json.loads(
        _V2_PATH.read_text(encoding="utf-8")
    )
    if overrides:
        for key, value in overrides.items():
            if isinstance(value, dict) and isinstance(base.get(key), dict):
                base[key] = {**base[key], **value}
            else:
                base[key] = value
    out = target_root / "config" / "us_turn_watch_universe.v2.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(base, indent=2), encoding="utf-8")
    return out





# ─────────────────────────────────────────────────────────────────────────────
# (1) Constants and frozen v1 contract are pinned
# ─────────────────────────────────────────────────────────────────────────────


def test_v2_constants_are_pinned():
    assert TW.UNIVERSE_CONTRACT_SCHEMA_V2 == "us_turn_watch_universe.v2"
    assert TW.UNIVERSE_CONTRACT_REL_V2 == Path("config/us_turn_watch_universe.v2.json")
    assert TW.SELECTION_ERA_V2 == "anticipation-v2-2026-10-19"
    assert TW.SELECTION_ERA == "anticipation-v1-2026-08-08"
    assert TW.UNIVERSE_CONTRACT_SCHEMA == "us_turn_watch_universe.v1"


def test_v1_frozen_contract_is_byte_stable():
    """v1 contract stays byte-identical; its selection_era is NEVER replaced by v2."""
    raw = _V1_PATH.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    # Whole-file SHA from frozen base 047ab5a950e59f4bdca180129a4dd84086a6d064.
    assert digest == "645dc6274aaa7606734d6f9f77168425fea21556737996ef0664b2c9a122e4eb"
    payload = json.loads(raw)
    assert payload["schema"] == "us_turn_watch_universe.v1"
    assert payload["selection_era"] == "anticipation-v1-2026-08-08"
    assert payload["tickers_sha256"] == _V1_DIGEST
    assert payload["population_count"] == 697


def test_v2_loader_constants_resolve_to_existing_paths():
    """`_v2_universe_contract_path` mirrors v1's path shape under the same data_root."""
    fake_root = Path("/tmp/does_not_exist/data")
    p = TW._v2_universe_contract_path(fake_root)
    assert p.name == "us_turn_watch_universe.v2.json"
    assert p.parent.name == "config"


# ─────────────────────────────────────────────────────────────────────────────
# (2) v2 contract authenticity, WM/KO membership proof and exclusion shape
# ─────────────────────────────────────────────────────────────────────────────


def test_v2_contract_loads_and_authenticates():
    contract = TW.universe_contract_v2(_REPO / "data")
    assert contract is not None
    assert contract["schema"] == "us_turn_watch_universe.v2"
    assert contract["selection_era"] == TW.SELECTION_ERA_V2
    assert contract["population_count"] == len(contract["tickers"])
    assert contract["tickers_sha256"] == (
        hashlib.sha256(("\n".join(contract["tickers"]) + "\n").encode("utf-8")).hexdigest()
    )


def test_v2_contract_contains_wm_and_ko_with_membership_proof():
    contract = TW.universe_contract_v2(_REPO / "data")
    assert contract is not None
    assert "WM" in contract["tickers"], "WM must be in the v2 outcome-independent roster"
    assert "KO" in contract["tickers"], "KO must remain in v2 (it was in v1 too)"
    proof = contract.get("membership_proof") or {}
    assert "WM" in proof and "KO" in proof
    wm, ko = proof["WM"], proof["KO"]
    for row in (wm, ko):
        assert row["security_id"].startswith("SEC:US-")
        assert row["issuer_state"] == "RESOLVED"
        assert row["mic"] in {"XNYS", "XNAS", "XASE", "ARCX", "BATS"}
        assert row["ticker"] in {"WM", "KO"}


def test_v2_excludes_index_fx_futures_and_crypto_store_files():
    contract = TW.universe_contract_v2(_REPO / "data")
    assert contract is not None
    for t in contract["tickers"]:
        assert not t.startswith("_"), f"{t!r} slipped past skip_prefixes"
        assert not t.endswith(("-USD", "-EUR", "-GBP", "_X", "_F")), f"{t!r} slipped past skip_suffixes"
        assert not any(c in t for c in (".", "=", "^")), f"{t!r} slipped past skip_chars"


def test_v2_filters_match_v1_filters():
    contract = TW.universe_contract_v2(_REPO / "data")
    assert contract is not None
    assert contract["filters"] == {
        "skip_prefixes": ["_"],
        "skip_chars": [".", "=", "^"],
        "skip_suffixes": ["-USD", "-EUR", "-GBP", "_X", "_F"],
    }


def test_v2_contract_carries_full_source_receipt():
    contract = TW.universe_contract_v2(_REPO / "data")
    assert contract is not None
    src = contract["source"]
    assert src["repository"] == "mastermindx-market-intelligence/macro"
    assert src["commit"] == "1d20bdebb10b30e1924cfcf18c689440c2059d7c"
    assert src["tree"] == "81587d77e5e6e0e72b55f203331f0f504f7fdc92"
    assert src["store_blob_sha1"] == "452fe313fa8d1904539128edbc8fb2fdd7d861d1"
    assert "outcome-independent" in src["membership_basis"].lower()
    # v1 reference is preserved so a consumer can disambiguate era bindings.
    v1ref = src["v1_reference"]
    assert v1ref["selection_era"] == "anticipation-v1-2026-08-08"
    assert v1ref["tickers_sha256"] == _V1_DIGEST


def test_v2_tampered_tickers_sha_fails_closed(tmp_path, capsys):
    _write_v2_contract(tmp_path, overrides={"tickers_sha256": "0" * 64})
    assert TW.universe_contract_v2(tmp_path / "data") is None
    assert "ticker digest mismatch" in capsys.readouterr().out


def test_v2_wrong_schema_fails_closed(tmp_path, capsys):
    _write_v2_contract(tmp_path, overrides={"schema": "us_turn_watch_universe.bogus"})
    assert TW.universe_contract_v2(tmp_path / "data") is None
    assert "contract shape/era invalid" in capsys.readouterr().out


def test_v2_wrong_era_fails_closed(tmp_path, capsys):
    _write_v2_contract(tmp_path, overrides={"selection_era": TW.SELECTION_ERA})
    assert TW.universe_contract_v2(tmp_path / "data") is None
    assert "contract shape/era invalid" in capsys.readouterr().out


def test_v2_missing_contract_returns_none_and_warns(tmp_path, capsys):
    assert TW.universe_contract_v2(tmp_path / "data") is None
    assert "contract unavailable" in capsys.readouterr().out


# ─────────────────────────────────────────────────────────────────────────────
# (3) Active-selection-era dispatcher
# ─────────────────────────────────────────────────────────────────────────────


def test_active_selection_era_returns_v1_before_activation_date(monkeypatch):
    # Pretend the most recent completed session is the day before v2 activation.
    monkeypatch.setattr(TW, "_completed_session",
                        lambda now_utc=None: pd.Timestamp("2026-10-16").date())
    assert TW.active_selection_era(_REPO / "data") == TW.SELECTION_ERA


def test_active_selection_era_returns_v2_on_activation_date(monkeypatch):
    monkeypatch.setattr(TW, "_completed_session",
                        lambda now_utc=None: pd.Timestamp(_V2_ACTIVATION).date())
    assert TW.active_selection_era(_REPO / "data") == TW.SELECTION_ERA_V2


def test_active_selection_era_returns_v2_after_activation_date(monkeypatch):
    monkeypatch.setattr(TW, "_completed_session",
                        lambda now_utc=None: pd.Timestamp("2026-10-23").date())
    assert TW.active_selection_era(_REPO / "data") == TW.SELECTION_ERA_V2


def test_active_selection_era_returns_none_when_v2_required_but_missing(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(TW, "_completed_session", lambda now_utc=None: pd.Timestamp("2026-10-23").date())
    assert TW.active_selection_era(tmp_path / "data") is None
    assert "v2 contract required" in capsys.readouterr().out


def test_active_selection_era_returns_none_when_v2_required_but_tampered(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(TW, "_completed_session",
                        lambda now_utc=None: pd.Timestamp("2026-10-23").date())
    # Write the tampered contract into the tmp_path sandbox so the in-repo contract
    # stays untouched and the loader resolves the tmp_path contract via data_root.parent.
    _write_v2_contract(tmp_path, overrides={"tickers_sha256": "0" * 64})
    assert TW.active_selection_era(tmp_path / "data") is None
    assert "v2 contract required" in capsys.readouterr().out


# ─────────────────────────────────────────────────────────────────────────────
# (4) Active dispatcher results shape — `universe` and `universe_contract_for_active`
# ─────────────────────────────────────────────────────────────────────────────


def test_universe_contract_for_active_returns_v1_when_v1_active(monkeypatch):
    monkeypatch.setattr(TW, "_completed_session",
                        lambda now_utc=None: pd.Timestamp("2026-10-16").date())
    contract = TW.universe_contract_for_active(_REPO / "data")
    assert contract["schema"] == "us_turn_watch_universe.v1"
    assert contract["selection_era"] == TW.SELECTION_ERA


def test_universe_contract_for_active_returns_v2_when_v2_active(monkeypatch):
    monkeypatch.setattr(TW, "_completed_session",
                        lambda now_utc=None: pd.Timestamp("2026-10-23").date())
    contract = TW.universe_contract_for_active(_REPO / "data")
    assert contract["schema"] == "us_turn_watch_universe.v2"
    assert contract["selection_era"] == TW.SELECTION_ERA_V2


def test_universe_contract_for_active_returns_v1_tickers_when_v1_active(monkeypatch):
    """`universe_contract_for_active` is the contract-level dispatcher — independent of the
    price store layout.  It returns the contract's own ticker list under the active era."""
    monkeypatch.setattr(TW, "_completed_session",
                        lambda now_utc=None: pd.Timestamp("2026-10-16").date())
    contract = TW.universe_contract_for_active(_REPO / "data")
    assert contract is not None
    assert "KO" in contract["tickers"]
    assert "WM" not in contract["tickers"]


def test_universe_contract_for_active_returns_v2_tickers_when_v2_active(monkeypatch):
    monkeypatch.setattr(TW, "_completed_session",
                        lambda now_utc=None: pd.Timestamp("2026-10-23").date())
    contract = TW.universe_contract_for_active(_REPO / "data")
    assert contract is not None
    assert contract["selection_era"] == TW.SELECTION_ERA_V2
    assert "KO" in contract["tickers"]
    assert "WM" in contract["tickers"]


def test_v2_universe_does_not_enumerate_raw_price_directory(monkeypatch, tmp_path):
    """v2 universe MUST be source-traceable to its contract, never to the price store."""
    monkeypatch.setattr(TW, "_completed_session",
                        lambda now_utc=None: pd.Timestamp("2026-10-23").date())
    fake_root = tmp_path / "data"
    yahoo = fake_root / TW.DECK_STORE
    yahoo.mkdir(parents=True)
    # These two names are NOT in the v2 contract we're about to write.
    for stem in ("NOT_IN_V2", "ALSO_NOT_IN_V2"):
        (yahoo / f"{stem}.parquet").write_bytes(b"")
    # No contract alongside this fixture, so v2 is missing → contract returns None.
    assert TW.universe_contract_for_active(fake_root) is None
    # Build a tiny contract whose tickers are exactly ["A","B"] — written
    # under tmp_path/config so the engine's ``data_root.parent/config``
    # resolution finds it.
    tickers = ["A", "B"]
    digest = hashlib.sha256(("\n".join(tickers) + "\n").encode("utf-8")).hexdigest()
    doc = {
        "schema": "us_turn_watch_universe.v2",
        "selection_era": TW.SELECTION_ERA_V2,
        "population_count": len(tickers),
        "snapshot": {"graded_min_bars_200": len(tickers), "graded_min_bars_260": len(tickers)},
        "tickers_sha256": digest,
        "tickers": tickers,
        "filters": {"skip_prefixes": ["_"], "skip_chars": [".", "=", "^"],
                    "skip_suffixes": ["-USD", "-EUR", "-GBP", "_X", "_F"]},
        "freshness": {"reference": "lib.nyse_calendar.expected_last_session",
                      "max_completed_session_lag": 0},
        "source": {"commit": "1d20bdebb10b30e1924cfcf18c689440c2059d7c",
                   "tree": "81587d77e5e6e0e72b55f203331f0f504f7fdc92"},
    }
    out = tmp_path / "config" / "us_turn_watch_universe.v2.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc), encoding="utf-8")
    # Add a price file whose stem is in the contract to make sure the contract is honoured.
    (yahoo / "A.parquet").write_bytes(b"")
    assert TW.universe(fake_root, selected_contract=TW.universe_contract_for_active(fake_root)) == ["A", "B"]
    # A price file whose stem is NOT in the contract must NOT widen the universe.
    assert "NOT_IN_V2" not in TW.universe(fake_root, selected_contract=TW.universe_contract_for_active(fake_root))
    assert "ALSO_NOT_IN_V2" not in TW.universe(fake_root, selected_contract=TW.universe_contract_for_active(fake_root))


def test_source_contract_status_discloses_active_selection_era(monkeypatch, tmp_path):
    """`source_contract_status` returns the active era — never the wrong one."""
    monkeypatch.setattr(TW, "_completed_session",
                        lambda now_utc=None: pd.Timestamp(_V2_ACTIVATION).date())
    # Copy the in-repo v2 contract alongside the tmp_path data dir so the loader
    # resolves ``data_root.parent/config`` to a real v2 contract.
    import shutil
    (tmp_path / "data" / TW.DECK_STORE).mkdir(parents=True)
    target_config = tmp_path / "config"
    target_config.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(_V2_PATH, target_config / "us_turn_watch_universe.v2.json")
    status = TW.source_contract_status(
        tmp_path / "data", members=[], closes={}, missing_store=[],
        benchmark=None, min_bars=TW.MIN_BARS,
        selected_contract=TW.universe_contract_for_active(tmp_path / "data"),
    )
    assert status["selection_era"] == TW.SELECTION_ERA_V2
    assert status["pass"] is False


# ─────────────────────────────────────────────────────────────────────────────
# (5) v1 path stays byte-compatible
# ─────────────────────────────────────────────────────────────────────────────


def test_v1_path_under_active_v1_returns_exact_v1_contract(monkeypatch, tmp_path):
    """The pre-existing v1 loader MUST keep returning the same bytes as before."""
    monkeypatch.setattr(TW, "_completed_session",
                        lambda now_utc=None: pd.Timestamp("2026-10-16").date())
    # The committed v1 contract is what the engine should serve.
    repo_v1 = TW.universe_contract(_REPO / "data")
    assert repo_v1["schema"] == "us_turn_watch_universe.v1"
    assert repo_v1["selection_era"] == "anticipation-v1-2026-08-08"
    assert repo_v1["tickers_sha256"] == _V1_DIGEST


def test_build_turn_watch_script_is_not_touched_by_v2_work():
    """Forbidden — the plan forbids modifying scripts/build_turn_watch.py.

    Pin the file's bytes identity so any future mutation is flagged.
    """
    builder = _REPO / "scripts" / "build_turn_watch.py"
    assert builder.exists(), "incumbent sidecar/intake writer must remain"
    src = builder.read_text(encoding="utf-8")
    # The incumbent references the v1 contract path; v2 references must NOT appear.
    assert "config/us_turn_watch_universe.v1.json" in src
    assert "site/turn_watch/turn_watch.json" in src
    # v2 must NOT have leaked into the incumbent.
    assert "us_turn_watch_universe.v2" not in src
    assert "anticipation-v2" not in src
    assert "anticipation-v2-2026-10-19" not in src

@pytest.mark.parametrize("floor", [None, 0, True, 1929, "1845"])
def test_v2_unmeasured_or_invalid_grading_floor_fails_closed(tmp_path, floor):
    _write_v2_contract(tmp_path, overrides={"snapshot": {"graded_min_bars_200": floor}})
    assert TW.universe_contract_v2(tmp_path / "data") is None


def test_v2_transition_and_actual_exclusions_are_disclosed():
    old = json.loads(_V1_PATH.read_text())
    new = json.loads(_V2_PATH.read_text())
    transition = new["source"]["v1_reference"]["transition"]
    removed = sorted(set(old["tickers"]) - set(new["tickers"]))
    assert [row["ticker"] for row in transition["removed"]] == removed
    assert transition["removed_count"] == len(removed) == 177
    assert transition["retained_count"] + transition["added_count"] == len(new["tickers"])
    assert [row["ticker"] for row in new["exclusions"]] == ["BF.B", "BRK.B", "MOG.A"]
    assert all(row["reason"] == "skip_chars" for row in new["exclusions"])
    assert new["snapshot"]["data_session"] < new["activation_not_before_session"]
