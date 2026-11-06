"""INTL-GS §14 cross-surface identity (ORCH-5 SPEC_A1 part B).

One qualified JP observation keeps ONE observation_id across the three
International surfaces that can name it: the observation contract itself
(``build_observation``), the dislocation own-history receipt
(``dislocation_own_history``) and the per-market structural summary
(``market_summary``). Fixture helpers are copied from the IM15 suite's
shapes, never imported from a test module.

Scope: International-internal identity is DONE here; Terminal/US identity
unification is DEFERRED to the Terminal/US research and ontology owners.
"""
import hashlib
from datetime import date, timedelta

from engine.intl_global_dislocation import dislocation_own_history
from engine.intl_global_observation import build_observation
from engine.intl_transmission_evidence import market_summary

RIGHTS = {"decision_ref": "chairman:2026-10-09:user-facing-redistribution-confirmed",
          "scope": "intl-index-fx-eod-user-facing-v1"}
INCUMBENT = {"quality": "qualified", "reason": None,
             "decision_ref": "derived-evaluation:sha256:abc"}
EVIDENCE = "saved-parquet:sha256:one|saved-parquet:sha256:two"
COMPUTED_AT = "2026-10-09T20:30:00+00:00"
BASE_END = date(2026, 10, 7)


def _month(k: int) -> date:
    total = BASE_END.year * 12 + BASE_END.month - 1 - k
    return date(total // 12, total % 12 + 1, BASE_END.day)


def _clocks(k: int, *, late: bool = False) -> dict:
    if late:
        stamp = "2026-10-10T15:00:00+00:00"
    else:
        stamp = f"{_month(k) + timedelta(days=2)}T15:00:00+00:00"
    return {
        "observation": {"at": f"{_month(k)}T00:00:00", "precision": "session_date"},
        "source_publication": {"at": stamp, "precision": "exact"},
        "ingestion": {"at": stamp, "precision": "exact"},
        "computation": {"at": stamp, "precision": "exact"},
    }


def _observation(market_id: str = "JP", k: int = 0, *, tag: str = "",
                 late: bool = False) -> dict:
    identity = {
        "universe_id": market_id, "market_id": market_id,
        "index_id": f"^T{market_id}", "fx_id": f"{market_id}FX=X",
        "horizon": "1m", "currency_basis": "usd_unhedged",
        "return_basis": "price",
        "window_start": f"{_month(k + 1)}T00:00:00",
        "window_end": f"{_month(k)}T00:00:00",
        "source_content_sha256": hashlib.sha256(
            f"{market_id}:{k}:{tag}".encode()).hexdigest(),
    }
    return build_observation(
        identity=identity, clocks=_clocks(k, late=late),
        values={"local_pct": -4.0, "fx_pct": -1.0, "usd_pct": -4.96},
        rights=dict(RIGHTS), incumbent=dict(INCUMBENT), evidence_ref=EVIDENCE)


def _references(market_id: str = "JP", count: int = 24, start: int = 1) -> list:
    return [_observation(market_id, k) for k in range(start, start + count)]


def _own_history(subject, history):
    return dislocation_own_history(
        subject, history, kind="own_history_return", computed_at=COMPUTED_AT)


def test_one_observation_id_across_all_three_surfaces():
    obs = _observation("JP", 0)
    history = _references()
    history_ids = {o["observation_id"] for o in history}

    # (1) the observation contract itself
    assert obs["state"] == "qualified"
    surface_one = obs["observation_id"]
    assert surface_one.startswith("obs:sha256:")

    # (2) the dislocation own-history receipt names the same subject id, and
    #     every history id it uses is one of the ids the history was built with
    receipt = _own_history(obs, history)
    assert receipt["subject"]["observation_id"] == surface_one
    used = receipt["references"]["used_observation_ids"]
    assert used, "expected the receipt to actually use reference windows"
    assert set(used) <= history_ids
    assert set(receipt["references"]["subject_block_ids"]) <= history_ids | {
        surface_one}

    # (3) the per-market structural summary lists the same id
    ms = market_summary("JP", edges=[], observations=[obs])
    assert ms["qualified_observations"]["observation_ids"] == [surface_one]


def test_changed_source_content_changes_the_id_on_all_three_surfaces():
    obs = _observation("JP", 0)
    alt = _observation("JP", 0, tag="alt")
    assert (alt["identity"]["source_content_sha256"]
            != obs["identity"]["source_content_sha256"])
    assert alt["observation_id"] != obs["observation_id"]

    receipt_a = _own_history(obs, _references())
    receipt_b = _own_history(alt, _references())
    assert receipt_a["subject"]["observation_id"] == obs["observation_id"]
    assert receipt_b["subject"]["observation_id"] == alt["observation_id"]
    assert (receipt_a["subject"]["observation_id"]
            != receipt_b["subject"]["observation_id"])

    both = market_summary("JP", edges=[], observations=[obs, alt])
    assert both["qualified_observations"]["observation_ids"] == sorted(
        [obs["observation_id"], alt["observation_id"]])


def test_same_identity_with_different_clocks_keeps_the_id_on_all_three():
    obs = _observation("JP", 0)
    replayed = _observation("JP", 0, late=True)
    assert replayed["identity"] == obs["identity"]
    assert replayed["clocks"] != obs["clocks"]
    assert replayed["observation_id"] == obs["observation_id"]

    receipt_a = _own_history(obs, _references())
    receipt_b = _own_history(replayed, _references())
    assert (receipt_a["subject"]["observation_id"]
            == receipt_b["subject"]["observation_id"]
            == obs["observation_id"])

    ms_a = market_summary("JP", edges=[], observations=[obs])
    ms_b = market_summary("JP", edges=[], observations=[replayed])
    assert (ms_a["qualified_observations"]["observation_ids"]
            == ms_b["qualified_observations"]["observation_ids"]
            == [obs["observation_id"]])
