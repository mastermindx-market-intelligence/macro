"""LR-T16 / RC-R14 — replay-isolation fence for the US rotation builder (full module).

A scratch/replay run of scripts/build_rotation_events.py must be provably effect-free
on the configured data root AND the live site tree: with --art-dir set and no site
override, the published JSON lands under art_dir/"site" and every store write (alert
store, lifecycle state, lane-gated ledger) lands under art_dir — never production.

These are REAL-module tests: no mocks of rotation_events.run_nightly; the builder runs
end-to-end over the incumbent synthetic legs from tests/test_rotation_events, against
temp roots with sentinel files that must stay byte-identical. Network-free.
"""
from __future__ import annotations

import copy
import hashlib
import json

import pytest

from engine import rotation_events
from engine import subsector_rotation_alerts as sra
from scripts import build_rotation_events as builder
from tests.test_rotation_events import _aligned_pair, _sectors

GEN_UTC = "2026-10-04 04:30 UTC"


def _fingerprint(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob("*")) if p.is_file()}


def _seed(root, rel, obj) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj) + "\n")


@pytest.fixture
def iso(tmp_path, monkeypatch):
    """Synthetic isolation rig: real modules, temp data root + temp repo root.

    Seeds a sentinel at every path a build may write, captures the real config load
    BEFORE patching, then repoints lib.config at the temp roots and arms the ledger
    (COLLECT_LANE=nightly) so the run takes its maximum write surface.
    """
    configured = tmp_path / "configured-data"
    repo = tmp_path / "repo"
    _seed(configured, "subsector_rotation/alerts.jsonl", {"sentinel": "alerts"})
    _seed(configured, "rotation_events/state.json", {"sentinel": "state"})
    _seed(configured, "rotation_events/events.jsonl", {"sentinel": "ledger"})
    _seed(repo, "site/marketdata/rotation_events.json", {"sentinel": "rotation_events"})
    _seed(repo, "site/marketdata/sector_fragmentation.json",
          {"sentinel": "sector_fragmentation"})

    real_cfg = builder.config.load()  # capture BEFORE any patching
    monkeypatch.setattr(builder.config, "ROOT", repo)
    monkeypatch.setattr(builder.config, "load", lambda: real_cfg)
    monkeypatch.setattr(builder.config, "data_dir", lambda: configured)
    # sra.config IS lib.config (same module object) — belt-and-braces per the lane spec.
    monkeypatch.setattr(sra.config, "data_dir", lambda: configured)
    monkeypatch.setattr(builder.sector_legs, "load_registry", lambda: {})
    monkeypatch.setattr(builder.sector_legs, "sector_closes",
                        lambda _r: _sectors(*_aligned_pair()))
    monkeypatch.setenv("COLLECT_LANE", "nightly")
    return configured, repo, tmp_path


def test_scratch_build_full_module_effect_fence(iso):
    """A39: build(art_dir=...) and the CLI --art-dir path publish under art_dir/"site"
    and write every store under art_dir; the configured data root and the live site
    tree stay byte-identical (sentinels intact)."""
    configured, repo, tmp_path = iso
    scratch1, scratch2 = tmp_path / "scratch-1", tmp_path / "scratch-2"
    before = {root: _fingerprint(root) for root in (configured, repo)}

    builder.build(art_dir=scratch1, generated_utc=GEN_UTC)  # no site argument
    builder.main(["--art-dir", str(scratch2)])              # the CLI path

    assert _fingerprint(configured) == before[configured]
    assert _fingerprint(repo) == before[repo]

    for scratch in (scratch1, scratch2):
        pub = scratch / "site" / "marketdata" / "rotation_events.json"
        assert pub.exists()
        payload = json.loads(pub.read_text())
        assert "xlk:memory->mag7" in payload["created_tonight"]
        alerts_p = scratch / "subsector_rotation" / "alerts.jsonl"
        assert alerts_p.exists()
        assert any(a["asset"] == "xlk:memory->mag7"
                   for a in sra.load_events(data_root=scratch))
        assert (scratch / "site" / "marketdata" / "sector_fragmentation.json").exists()

    ledger_p = scratch1 / "rotation_events" / "events.jsonl"
    assert ledger_p.exists()  # COLLECT_LANE=nightly armed → maximum write surface, in scratch
    rows = [json.loads(ln) for ln in ledger_p.read_text().splitlines() if ln.strip()]
    assert any(r["event"] == "created" and r["id"] == "xlk:memory->mag7" for r in rows)


def test_live_defaults_unchanged_without_art_dir(iso):
    """No art_dir, no site → the production defaults are unchanged: the live site file
    IS rewritten with the created event, and the alert store at config.data_dir()
    merges the new alert while keeping the in-window (KEEP_DAYS) sentinel alert."""
    configured, repo, tmp_path = iso

    # Dry first call (throwaway root) to learn the real synthetic alert ts, so the
    # sentinel's ts sits inside sra.KEEP_DAYS of the new alert and survives the prune.
    dry = rotation_events.run_nightly(_sectors(*_aligned_pair()), tmp_path / "dry",
                                      generated_utc=GEN_UTC)
    dry_alerts = rotation_events.to_alerts(dry)
    assert dry_alerts
    sentinel_alert = {"id": "sentinel:legacy-handoff", "ts": dry_alerts[0]["ts"],
                      "source": "rotation", "asset": "SENTINEL",
                      "type": "rotation_event", "severity": "minor"}
    (configured / "subsector_rotation" / "alerts.jsonl").write_text(
        json.dumps(sentinel_alert) + "\n")

    live_site = repo / "site" / "marketdata" / "rotation_events.json"
    sentinel_bytes = live_site.read_bytes()

    builder.build(generated_utc=GEN_UTC)  # no art_dir, no site

    assert live_site.read_bytes() != sentinel_bytes  # sentinel gone — live file rewritten
    payload = json.loads(live_site.read_text())
    assert "xlk:memory->mag7" in payload["created_tonight"]

    ids = {a["id"] for a in sra.load_events(data_root=configured)}
    assert "sentinel:legacy-handoff" in ids
    assert any(i.startswith("rotation:us:rotation_event:xlk:memory->mag7") for i in ids)


def test_alert_projection_invariant_to_display_only_context(tmp_path):
    """A40: to_alerts is a projection of the created events only — display-only context
    (top-level early_context / meta.rs_history, per-event reconstructed rs_history)
    never leaks into the alert projection."""
    payload = rotation_events.run_nightly(_sectors(*_aligned_pair()), tmp_path / "d",
                                          generated_utc=GEN_UTC)
    base = rotation_events.to_alerts(payload)
    assert base

    decorated = copy.deepcopy(payload)
    decorated["early_context"] = {"schema": "rotation_early_context/v1",
                                  "state": "early", "display_only": True}
    decorated["meta"] = {"rs_history": {"mode": "reconstructed_price_history",
                                        "naturally_observed": False}}
    for ev in decorated.get("active", []):
        ev["rs_history"] = [{"date": "2026-10-02", "rs_21d": 1.0, "rs_63d": 2.0}]

    assert (json.dumps(rotation_events.to_alerts(decorated), sort_keys=True)
            == json.dumps(base, sort_keys=True))
