"""Tests for the VPS premarket owner (A-MOR-2b lane B).

Lane B of MO-A3 A-MOR-2b
(DEC:MARKET-ONTOLOGY-MOR2B-PREMARKET-OWNER-AND-PLACEMENT-2026-09-24,
research/market_intelligence_productization/MARKET_ONTOLOGY_F01_MOR2B_BUILD_PACKET_2026-09-24.md
§3 B1–B6). The lane wraps ``scripts.build_am_edition`` (the SAME producer the
nightly already runs) and adds a VPS-side overlay that is built during the ET
premarket and torn down the moment a newer nightly bake lands. This file pins:

* the three-way decision table — ``expire`` / ``build`` / ``skip`` — with a
  fake clock and a tmp_path fixture tree so the test is hermetic, sparse-safe,
  and never touches the repo's real ``site/`` or ``data/`` trees;
* the served-artifact chmod (``0o644`` so Caddy can read the overlay bytes —
  the live-plane invariant enforced at scripts/vps_live_orchestrator.run:246-
  252, which every sibling lane also fchmods into the served bytes);
* the receipt shape (``decision``, ``generated_at``, ``phase``, the two
  ``*_generated_at`` fields, ``block_states``, and ``error`` ONLY on an error
  path — never silently dropped);
* the atomic-write contract (no partial files visible during a swap);
* the never-raises clause (a degraded box degrades to a structured ``error``
  receipt, never a hard Python traceback) and the public_dir misconfig as the
  single exit-1 case;
* the systemd unit-file shape (``OnCalendar`` is exact, ``ExecStart`` is exact,
  ``Type=oneshot`` and ``WantedBy=timers.target`` are present).

Run: ``python -m pytest tests/test_am_edition_live.py -q``
"""
from __future__ import annotations

import json
import re
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from scripts import am_edition_live
from scripts.am_edition_live import (
    PUBLIC_DIR,
    STATE_DIR,
    _atomic_write_bytes,
    _atomic_write_text,
    _live_dir,
    _norm_iso_clock,
    run,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _fresh_tree(tmp_path: Path, *, tape_asof: str, session_date: str) -> tuple[Path, Path]:
    """Build a minimal site + data tree so build_payload can render the
    overlay. Mirrors tests/test_am_edition_producer.py:_fresh_tree closely
    so the lane's payload surface is the same as the producer's."""
    site = tmp_path / "site"
    data = tmp_path / "data"
    (site / "live").mkdir(parents=True, exist_ok=True)
    (data / "market_state").mkdir(parents=True, exist_ok=True)
    (data / "regime").mkdir(parents=True, exist_ok=True)
    (data / "neuralweb").mkdir(parents=True, exist_ok=True)
    (data / "release_forecast").mkdir(parents=True, exist_ok=True)
    (site / "live" / "quotes.json").write_text(json.dumps({
        "ts": 1, "asof": tape_asof, "source": "yahoo",
        "quotes": {
            "SPY": {"price": 740.0, "prevClose": 739.0, "changePct": 0.14, "basis": "regular"},
        },
        "meta": {},
    }), encoding="utf-8")
    (data / "market_state" / "latest.json").write_text(json.dumps({
        "asof": session_date, "label_en": "Risk-on", "label_zh": "风险偏好",
        "posture_en": "Constructive", "posture_zh": "积极",
        "headline_en": "x", "headline_zh": "x",
    }), encoding="utf-8")
    (data / "regime" / "latest.json").write_text(json.dumps({
        "asof": session_date, "quad_name": "Reflation", "label": "Q2",
    }), encoding="utf-8")
    (data / "neuralweb" / "market_plane.json").write_text(json.dumps({
        "asof": session_date,
        "verdict": {"verdict": "RISK_ON", "score": 75, "label_en": "Risk-on", "label_zh": "风险偏好"},
        "contradiction_count": 0,
        "stale": False,
        "gaps": [],
    }), encoding="utf-8")
    (data / "release_forecast" / "latest.json").write_text(json.dumps({
        "asof": f"{session_date}T10:00:00Z",
        "upcoming": [],
    }), encoding="utf-8")
    (site / "master_brief.json").write_text(json.dumps({
        "generated_at": f"{session_date}T10:00:00Z",
        "state_asof": session_date, "lens": "macro",
    }), encoding="utf-8")
    return site, data


def _write_bake(site: Path, generated_at: str) -> Path:
    """Write a minimal site/am_edition.json with the supplied generated_at."""
    p = site / "am_edition.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"generated_at": generated_at, "schema": "am_edition.v1"}), encoding="utf-8")
    return p


def _write_overlay(public_dir: Path, *, generated_at: str, write_html: bool = True) -> tuple[Path, Path]:
    """Drop the two overlay files into PUBLIC_DIR (the same destination the
    lane writes). Returns (json_path, html_path)."""
    public_dir.mkdir(parents=True, exist_ok=True)
    json_path = public_dir / "am_edition.json"
    html_path = public_dir / "am_edition.html"
    json_path.write_text(json.dumps({"generated_at": generated_at, "schema": "am_edition.v1"}), encoding="utf-8")
    if write_html:
        html_path.write_text("<html>overlay</html>", encoding="utf-8")
    return json_path, html_path


# ET premarket in UTC: 08:0x..14:0x UTC under EDT (UTC-4) maps to
# 04:0x..10:0x ET; under EST (UTC-5) to 03:0x..09:0x ET. The producer's phase
# check resolves `preopen` strictly BEFORE 09:30 ET on an NYSE session date
# (`local < open_local` — see scripts/build_am_edition.py:_session_phase), so
# 09:30 ET on the dot is `open`, not `preopen`. 12:30 UTC = 08:30 EDT /
# 07:30 EST is safely inside the preopen window in both DST regimes.
def _preopen_now(session_date: date) -> datetime:
    """An ET premarket instant — Tuesday 2026-09-22 at 12:30 UTC = 08:30 EDT,
    comfortably inside the preopen window before 09:30 ET."""
    return datetime(session_date.year, session_date.month, session_date.day, 12, 30, tzinfo=timezone.utc)


def _patch_paths(monkeypatch, tmp_path: Path) -> tuple[Path, Path]:
    monkeypatch.setattr(am_edition_live, "PUBLIC_DIR", tmp_path / "public")
    monkeypatch.setattr(am_edition_live, "STATE_DIR", tmp_path / "state")
    return tmp_path / "public", tmp_path / "state"


# ---------------------------------------------------------------------------
# Live-dir ladder (mirror of market_packet.py:86-101)
# ---------------------------------------------------------------------------

def test_live_dir_ladder_respects_MACRO_LIVE_DIR(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("MACRO_LIVE_DIR", str(tmp_path / "live_override"))
    assert _live_dir(tmp_path) == tmp_path / "live_override"


def test_live_dir_ladder_falls_back_to_repo_site_live_when_no_env(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("MACRO_LIVE_DIR", raising=False)
    # /var/lib/macro-live/public/live is the production override; on a dev /
    # CI box that path is not a directory, so the ladder falls through to
    # <root>/site/live per the explicit copy of the market_packet ladder.
    assert _live_dir(tmp_path) == tmp_path / "site" / "live"


def test_atomic_write_text_round_trip(tmp_path: Path) -> None:
    target = tmp_path / "atomic.html"
    _atomic_write_text(target, "<html>v1</html>")
    assert target.read_text(encoding="utf-8") == "<html>v1</html>"


def test_atomic_write_bytes_publishes_only_after_rename(tmp_path: Path) -> None:
    """Temp file + os.replace is the live plane's idiom. A reader that opens
    the target during the swap must see either the old bytes or the new bytes,
    never a half-written file."""
    target = tmp_path / "atomic.json"
    target.write_text('"old"', encoding="utf-8")
    _atomic_write_bytes(target, b'"new"')
    assert target.read_bytes() == b'"new"'
    # No leftover temp file in the same directory.
    leftovers = [p for p in tmp_path.iterdir() if p.name != "atomic.json"]
    assert leftovers == [], f"temp files left behind: {leftovers}"


def test_atomic_write_bytes_chmods_served_artifact_to_644(tmp_path: Path) -> None:
    """BLOCKER §1: a served overlay file under PUBLIC_DIR must be readable by
    Caddy (user ``caddy``). Under umask 022 the default mkstemp creates the
    temp file at 0o600 — root-readable only — and Caddy would never see the
    overlay bytes while the unit reports success. The lane's atomic writer
    chmods the served file to 0o644 BEFORE os.replace, matching the live
    plane's invariant (scripts/vps_live_orchestrator.run:246-252) and every
    sibling served-artifact writer (scripts/entry_radar_live.py:286,
    scripts/prophet_live_evaluator.py:273, scripts/cn_live_evaluator.py:186,
    scripts/close_pass_publish.py:351).

    This is the test that catches the silent-dark class app/deploy/live-setup.sh:133
    records as a 27-day incident: the unit exits 0, the receipt says
    ``decision: build``, and Caddy serves canonical site.served bytes forever.
    """
    target = tmp_path / "public" / "am_edition.json"
    _atomic_write_bytes(target, b'{"ok": true}')
    mode = target.stat().st_mode & 0o777
    assert mode == 0o644, (
        f"served overlay must be 0o644 for Caddy to read it (live-plane "
        f"invariant); got {oct(mode)} — this is the silent-dark class that "
        f"wires 'success' to 'serving the canonical site.served copy' forever"
    )


def test_atomic_write_bytes_chmods_receipt_to_600(tmp_path: Path) -> None:
    """The receipt lives under ``state_dir`` (NOT web-addressable). 0o600 is
    the live plane's default for non-served bytes and what every sibling lane
    uses (scripts/close_pass_publish.py, scripts/entry_radar_live.py)."""
    target = tmp_path / "state" / "last_run.json"
    _atomic_write_bytes(target, b'{"decision":"build"}', mode=0o600)
    mode = target.stat().st_mode & 0o777
    assert mode == 0o600, f"receipt must be 0o600; got {oct(mode)}"


def test_atomic_write_bytes_refuses_when_public_dir_is_absent(
    monkeypatch, tmp_path: Path,
) -> None:
    """MINOR 5: a host without the VPS live plane has no PUBLIC_DIR; the
    sibling pattern (scripts/entry_radar_live.py:266-270) refuses rather than
    silently creates the root. The lane must NOT call mkdir on the live store
    out of nothing."""
    missing = tmp_path / "missing_public"
    monkeypatch.setattr(am_edition_live, "PUBLIC_DIR", missing)
    target = missing / "am_edition.json"
    with pytest.raises(FileNotFoundError):
        _atomic_write_bytes(target, b"{}")
    assert not missing.exists(), (
        "the lane must NOT call mkdir on PUBLIC_DIR out of nothing — the "
        "host without a live plane stays read-only on /var/lib/macro-live"
    )


def test_norm_iso_clock_handles_naive_and_z_suffixed_strings() -> None:
    """MINOR 3: string compare on `generated_at` is fragile when one writer
    stamps ``Z`` and the other stamps naive ISO. Normalize so DST / naive
    inputs cannot mis-order the freshest-wins comparison."""
    # Same instant, three stamps — must all compare equal under string cmp.
    a = _norm_iso_clock("2026-09-22T13:00:00+00:00")
    b = _norm_iso_clock("2026-09-22T13:00:00Z")
    c = _norm_iso_clock("2026-09-22T13:00:00")
    assert a == b == c, f"norm_iso_clock disagrees: a={a} b={b} c={c}"

    # A later instant sorts strictly greater, even when written naively.
    later = _norm_iso_clock("2026-09-22T14:00:00")
    assert later > a


# ---------------------------------------------------------------------------
# Decision table (matrix at exact head)
# ---------------------------------------------------------------------------

def test_decision_build_when_overlay_absent_and_preopen(monkeypatch, tmp_path: Path) -> None:
    """Decision (b): no overlay yet, preopen on a session date -> build."""
    public, state = _patch_paths(monkeypatch, tmp_path)
    site, data = _fresh_tree(tmp_path, tape_asof="2026-09-22T12:30:00+00:00", session_date="2026-09-22")
    _write_bake(site, "2026-09-22T12:30:00+00:00")
    receipt = run(now=_preopen_now(date(2026, 9, 22)), root=tmp_path)
    assert receipt["decision"] == "build"
    assert receipt["phase"] == "preopen"
    assert (public / "am_edition.json").exists()
    # When the test env supports jinja2 + template the html is written too;
    # when it lacks one render_html returns "" and the lane logs but does NOT
    # fail. The JSON write is the binding contract.


def test_receipt_is_persisted_by_main(monkeypatch, tmp_path: Path) -> None:
    """B1 §4: `state_dir/last_run.json` carries the receipt — written at
    0o600 (non-served) by the lane's atomic write helper."""
    public, state = _patch_paths(monkeypatch, tmp_path)
    site, data = _fresh_tree(tmp_path, tape_asof="2026-09-22T12:30:00+00:00", session_date="2026-09-22")
    _write_bake(site, "2026-09-22T12:30:00+00:00")
    receipt = run(now=_preopen_now(date(2026, 9, 22)), root=tmp_path)
    am_edition_live._write_receipt(state, receipt)
    state_blob = json.loads((state / "last_run.json").read_text(encoding="utf-8"))
    assert state_blob["decision"] == "build"
    assert state_blob["phase"] == "preopen"


def test_decision_expire_when_bake_is_newer_than_overlay(monkeypatch, tmp_path: Path) -> None:
    """Decision (a): overlay present AND bake is newer -> expire (both files
    removed). The visitor falls back to the canonical site copy on the next
    request."""
    public, state = _patch_paths(monkeypatch, tmp_path)
    site, data = _fresh_tree(tmp_path, tape_asof="2026-09-22T12:30:00+00:00", session_date="2026-09-22")
    _write_bake(site, "2026-09-22T13:45:00+00:00")  # newer
    json_path, html_path = _write_overlay(public, generated_at="2026-09-22T13:00:00+00:00")
    assert json_path.exists() and html_path.exists()

    receipt = run(now=_preopen_now(date(2026, 9, 22)), root=tmp_path)
    assert receipt["decision"] == "expire"
    assert not json_path.exists()
    assert not html_path.exists()


def test_decision_skip_when_phase_is_not_preopen(monkeypatch, tmp_path: Path) -> None:
    """Decision (c): phase != preopen (here, post-close) -> skip. The overlay
    is left alone — the spec only expires when the bake is newer, so a
    post-close tick with the overlay already current MUST NOT touch the
    overlay files."""
    public, state = _patch_paths(monkeypatch, tmp_path)
    site, data = _fresh_tree(tmp_path, tape_asof="2026-09-22T20:30:00+00:00", session_date="2026-09-22")
    _write_bake(site, "2026-09-22T12:30:00+00:00")  # older than overlay
    json_path, html_path = _write_overlay(public, generated_at="2026-09-22T13:00:00+00:00")
    # 22:00 UTC = 18:00 ET under EDT: well after the 16:00 ET close -> closed.
    closed_now = datetime(2026, 9, 22, 22, 0, tzinfo=timezone.utc)
    receipt = run(now=closed_now, root=tmp_path)
    assert receipt["decision"] == "skip"
    assert receipt["phase"] == "closed"
    # Overlay is preserved — the expire rule fires only on bake-newer.
    assert json_path.exists() and html_path.exists()


def test_decision_skip_on_weekend(monkeypatch, tmp_path: Path) -> None:
    """Decision (c): weekend -> skip. A Saturday at 13:30 UTC is OUTSIDE the
    NYSE session envelope regardless of the UTC wall clock."""
    _patch_paths(monkeypatch, tmp_path)
    site, data = _fresh_tree(tmp_path, tape_asof="2026-09-19T12:30:00+00:00", session_date="2026-09-19")
    _write_bake(site, "2026-09-19T12:30:00+00:00")
    # 2026-09-19 is a Saturday.
    receipt = run(now=datetime(2026, 9, 19, 13, 30, tzinfo=timezone.utc), root=tmp_path)
    assert receipt["decision"] == "skip"
    assert receipt["phase"] == "weekend"


def test_decision_skip_on_nyse_holiday(monkeypatch, tmp_path: Path) -> None:
    """Decision (c): NYSE holiday -> skip. Phase surfaces as 'holiday' so an
    operator reading the receipt can tell why no overlay was built."""
    _patch_paths(monkeypatch, tmp_path)
    site, data = _fresh_tree(tmp_path, tape_asof="2026-01-01T12:30:00+00:00", session_date="2026-01-01")
    _write_bake(site, "2026-01-01T12:30:00+00:00")
    # 2026-01-01 is New Year's Day (NYSE closed).
    receipt = run(now=datetime(2026, 1, 1, 13, 30, tzinfo=timezone.utc), root=tmp_path)
    assert receipt["decision"] == "skip"
    assert receipt["phase"] == "holiday"


def test_freshest_wins_comparison_is_total_under_z_and_naive_stamps(
    monkeypatch, tmp_path: Path,
) -> None:
    """MINOR 3 (red test): a `Z`-suffixed bake stamp versus a naive overlay
    stamp must NEVER mis-order. The producer writes naive ISO
    (``scripts/build_am_edition.py:2158``); the previous code path compared
    strings directly, which failed when either side stamped `Z`. The lane
    normalizes both ends through ``_norm_iso_clock``."""
    public, state = _patch_paths(monkeypatch, tmp_path)
    site, data = _fresh_tree(tmp_path, tape_asof="2026-09-22T12:30:00+00:00", session_date="2026-09-22")
    # Bake stamps with `Z`, overlay stamps naive — both represent 13:00Z vs
    # 12:30Z. String-compare under the Z suffix would mis-order.
    bake_path = site / "am_edition.json"
    bake_path.parent.mkdir(parents=True, exist_ok=True)
    bake_path.write_text(json.dumps({"generated_at": "2026-09-22T13:00:00Z"}), encoding="utf-8")
    overlay = public / "am_edition.json"
    overlay.parent.mkdir(parents=True, exist_ok=True)
    overlay.write_text(json.dumps({"generated_at": "2026-09-22T12:30:00"}), encoding="utf-8")

    preopen = _preopen_now(date(2026, 9, 22))
    receipt = run(now=preopen, root=tmp_path)
    assert receipt["decision"] == "expire", (
        f"bake (13:00Z) is newer than overlay (12:30Z) — must `expire`; "
        f"got decision={receipt['decision']!r} (string-compare on Z+naive "
        f"stamps would have returned a wrong here)"
    )
    assert not overlay.exists(), "expire must remove the overlay file"


# ---------------------------------------------------------------------------
# Receipt shape — exactly the keys the spec promises on every path
# ---------------------------------------------------------------------------

def test_receipt_shape_matches_frozen_contract(monkeypatch, tmp_path: Path) -> None:
    """The receipt dict carries the six spec keys on a SUCCESS path
    (decision, generated_at, phase, bake_generated_at, overlay_generated_at,
    block_states), no extras. A future field that sneaks in here would break
    consumers that pin the shape, so the test pins it byte-for-byte."""
    _patch_paths(monkeypatch, tmp_path)
    site, data = _fresh_tree(tmp_path, tape_asof="2026-09-22T12:30:00+00:00", session_date="2026-09-22")
    _write_bake(site, "2026-09-22T12:30:00+00:00")
    receipt = run(now=_preopen_now(date(2026, 9, 22)), root=tmp_path)

    expected_keys = {
        "decision", "generated_at", "phase",
        "bake_generated_at", "overlay_generated_at",
        "block_states",
    }
    assert set(receipt.keys()) == expected_keys, (
        f"receipt keys drifted: extra={set(receipt) - expected_keys}, "
        f"missing={expected_keys - set(receipt)}"
    )
    assert receipt["decision"] == "build"
    assert receipt["phase"] == "preopen"
    assert receipt["bake_generated_at"] == "2026-09-22T12:30:00+00:00"
    assert receipt["generated_at"] is not None
    assert isinstance(receipt["block_states"], dict)
    # Every legacy block key that the producer emits must surface here.
    for k in (
        "session_clock",
        "tape_since_prior_close",
        "market_state",
        "regime",
        "cross_asset_plane",
        "todays_calendar",
        "prior_close_brief_ref",
        "context_planes",
        "research_watch",
        "owner_links",
    ):
        assert k in receipt["block_states"], f"missing block state for {k}"


def test_error_receipts_keep_the_six_keys_with_an_error_field_added(
    monkeypatch, tmp_path: Path,
) -> None:
    """MINOR 4: error-path receipts must include the SAME six success keys so
    downstream consumers that pin the shape never trip on a degraded run;
    only the `error` field is added. Drive an error by replacing the
    producer's `build_payload` on its module — `run()` re-resolves the name
    on every pass via `from scripts.build_am_edition import …`, so the patched
    binding is observed on the next call."""
    _patch_paths(monkeypatch, tmp_path)
    site, data = _fresh_tree(tmp_path, tape_asof="2026-09-22T12:30:00+00:00", session_date="2026-09-22")
    _write_bake(site, "2026-09-22T12:30:00+00:00")

    def _boom(*_args, **_kwargs):
        raise RuntimeError("simulated producer failure")

    import scripts.build_am_edition as _producer  # noqa: PLC0415
    monkeypatch.setattr(_producer, "build_payload", _boom)

    receipt = run(now=_preopen_now(date(2026, 9, 22)), root=tmp_path)
    base_keys = {
        "decision", "generated_at", "phase",
        "bake_generated_at", "overlay_generated_at",
        "block_states",
    }
    assert set(receipt.keys()) >= base_keys, (
        f"error receipt kept the spec keys: missing={base_keys - set(receipt)}"
    )
    assert receipt["decision"] == "error"
    assert isinstance(receipt.get("error"), str)
    assert receipt["error"].startswith("build_payload_failed:"), (
        "the error key's value must tell the operator WHICH internal stage "
        "tripped (build_payload_failed vs json_write_failed vs html_write_failed)"
    )


# ---------------------------------------------------------------------------
# Never-raises clause — the lane degrades to a structured receipt, never a
# Python traceback that aborts the unit. main() exits 0 except when the box
# is genuinely misconfigured (B1: public_dir unwritable is the one exit-1).
# ---------------------------------------------------------------------------

def test_run_never_raises_on_a_missing_owner_file(monkeypatch, tmp_path: Path) -> None:
    """B6: 'never raises on a missing owner file' — the spec names this
    explicitly. An empty site + data tree degrades to a skip receipt; absent
    blocks / templates trip jinja2 inside build_payload rather than letting
    `run` itself raise."""
    _patch_paths(monkeypatch, tmp_path)
    # Empty tree: no market_state, no regime, no plane, no quotes, no bake.
    (tmp_path / "site").mkdir(parents=True, exist_ok=True)
    (tmp_path / "data").mkdir(parents=True, exist_ok=True)
    receipt = run(now=_preopen_now(date(2026, 9, 22)), root=tmp_path)
    # The decision is one of the canonical three.
    assert receipt["decision"] in {"skip", "build", "error"}, receipt
    # And the structural keys are present even on a degraded run.
    base_keys = {
        "decision", "generated_at", "phase",
        "bake_generated_at", "overlay_generated_at",
        "block_states",
    }
    assert base_keys <= set(receipt.keys()), (
        f"degraded run kept the spec keys: missing={base_keys - set(receipt)}"
    )


def test_main_returns_zero_when_state_dir_is_unwritable(
    monkeypatch, tmp_path: Path,
) -> None:
    """MAJOR 2 / B1: a degraded state_dir is a degraded box but it is NOT the
    spec's exit-1 case (the spec reserves exit 1 for public_dir being un-
    writable — the served file would never land). State_dir is the receipt's
    home; if the receipt cannot land the run still publishes the overlay and
    main() returns 0 so the timer does not page the operator."""
    # State_dir points at a regular file under tmp_path; mkdir inside it
    # raises — that is the "state_dir un-writable" condition the test names.
    blocker = tmp_path / "blocker"
    blocker.write_text("x", encoding="utf-8")
    public = tmp_path / "public"
    public.mkdir()
    monkeypatch.setattr(am_edition_live, "PUBLIC_DIR", public)
    monkeypatch.setattr(am_edition_live, "STATE_DIR", blocker / "subdir")
    site, data = _fresh_tree(tmp_path, tape_asof="2026-09-22T12:30:00+00:00", session_date="2026-09-22")
    _write_bake(site, "2026-09-22T12:30:00+00:00")

    assert am_edition_live.main([]) == 0, (
        "state_dir is NOT the exit-1 trigger; the lane publishes the overlay "
        "and main() exits 0 even when the receipt cannot land"
    )


def test_main_returns_one_only_when_public_dir_is_unwritable(
    monkeypatch, tmp_path: Path,
) -> None:
    """MAJOR 1 (red test on the previous head's always-0 main): the spec's
    single exit-1 case is `public_dir_unwritable` — without that the served
    file would never land, so a degraded box is a hard failure and systemd
    must surface it. Every other failure path stays exit 0 (so the timer
    never pages the operator over a recoverable degradation)."""
    blocker = tmp_path / "blocker"
    blocker.write_text("x", encoding="utf-8")
    monkeypatch.setattr(
        am_edition_live, "PUBLIC_DIR", blocker / "subdir"
    )  # mkdir inside a regular file -> un-writable
    monkeypatch.setattr(am_edition_live, "STATE_DIR", tmp_path / "state")
    assert am_edition_live.main([]) == 1, (
        "main() must exit 1 on a misconfigured public_dir — the served file "
        "could never land, and the timer must surface that hard fail"
    )


def test_main_returns_zero_on_state_dir_write_failure(
    monkeypatch, tmp_path: Path,
) -> None:
    """`_write_receipt` is best-effort — a state_dir that exists but is not
    writable must not flip main() to exit 1 (the lane still publishes the
    overlay; only the receipt is lost). Drive this without monkey-patching
    `_write_receipt` itself (its outer try/except already swallows OSError):
    set STATE_DIR to a path whose parent refuses new entries."""
    public = tmp_path / "public"
    public.mkdir()
    monkeypatch.setattr(am_edition_live, "PUBLIC_DIR", public)
    # STATE_DIR points at `<regular file>/subdir` — mkdir inside a regular
    # file raises NotADirectoryError, which `_write_receipt`'s try/except
    # already handles. main() must still return 0 because the spec only
    # makes public_dir un-writable the exit-1 case.
    blocker = tmp_path / "blocker"
    blocker.write_text("x", encoding="utf-8")
    monkeypatch.setattr(am_edition_live, "STATE_DIR", blocker / "subdir")

    assert am_edition_live.main([]) == 0, (
        "a best-effort receipt write must not escalate main() to exit 1 — "
        "only the public_dir un-writable condition is the spec's exit-1 case"
    )


def test_run_returns_error_receipt_when_public_dir_is_unwritable(
    monkeypatch, tmp_path: Path,
) -> None:
    """MAJOR 1: the spec's exit-1 case is signalled by a receipt whose
    `decision == "error"` and `error` starts with `public_dir_unwritable:` —
    main() keys off that pair, not off any other failure."""
    blocker = tmp_path / "blocker"
    blocker.write_text("x", encoding="utf-8")
    monkeypatch.setattr(am_edition_live, "PUBLIC_DIR", blocker / "subdir")
    monkeypatch.setattr(am_edition_live, "STATE_DIR", tmp_path / "state")
    receipt = run(now=_preopen_now(date(2026, 9, 22)), root=tmp_path)
    assert receipt["decision"] == "error"
    assert receipt["error"].startswith("public_dir_unwritable:") or "public_dir" in receipt["error"]


def test_main_returns_zero_on_uncaught_internal_exception(
    monkeypatch, tmp_path: Path,
) -> None:
    """run() is fail-closed: a bug inside run() must not surface a Python
    traceback out of main(). The lane logs and writes an `error` receipt, then
    returns 0 because the failure is NOT the spec's exit-1 case."""
    monkeypatch.setattr(am_edition_live, "PUBLIC_DIR", tmp_path / "public")
    monkeypatch.setattr(am_edition_live, "STATE_DIR", tmp_path / "state")
    (tmp_path / "public").mkdir()
    (tmp_path / "state").mkdir()

    def _raise(*_a, **_kw):
        raise RuntimeError("simulated bug")

    monkeypatch.setattr(am_edition_live, "run", _raise)
    assert am_edition_live.main([]) == 0


# ---------------------------------------------------------------------------
# Unit-file shape (systemd-analyze verify is unavailable on macOS).
# ---------------------------------------------------------------------------

def test_unit_service_file_keys_match_the_frozen_spec() -> None:
    """The spec pins the .service surface verbatim (B2). Missing or renamed
    keys break `systemd-analyze verify` and the deploy recipe — this test is
    the macOS surrogate for that command."""
    text = (REPO_ROOT / "app" / "deploy" / "macro-am-edition.service").read_text(encoding="utf-8")
    for key in ("Type=oneshot", "WorkingDirectory=/opt/macro",
                "EnvironmentFile=-/etc/macro-live.env",
                "ExecStart=/opt/macro/.venv/bin/python -m scripts.am_edition_live",
                "Nice=10"):
        assert key in text, f"macro-am-edition.service is missing required key: {key!r}"


def test_unit_timer_file_keys_match_the_frozen_spec() -> None:
    """The OnCalendar string is exact — `08..14:07,37:00 UTC` covers the ET
    premarket in BOTH DST regimes; widening it would silently arm the lane
    outside the ET session, narrowing it would miss the open. Either drift
    is a regression this test catches before the VPS sees it."""
    text = (REPO_ROOT / "app" / "deploy" / "macro-am-edition.timer").read_text(encoding="utf-8")
    for needle, label in (
        ("OnCalendar=*-*-* 08..14:07,37:00 UTC", "OnCalendar is exact"),
        ("RandomizedDelaySec=60", "RandomizedDelaySec present"),
        ("Persistent=false", "Persistent=false (spec B2)"),
        ("Unit=macro-am-edition.service", "Unit points at the .service"),
        ("WantedBy=timers.target", "WantedBy=timers.target"),
    ):
        assert needle in text, f"macro-am-edition.timer is missing: {label} ({needle!r})"


def test_update_sh_block_carries_the_four_file_regex() -> None:
    """The CHANGED trigger is exact: it has to fire on the unit pair, the
    lane script, AND the producer (the producer's signature changed between
    rounds). Missing either side of the alternation breaks the self-arming
    contract.

    The grep -E regex in update.sh escapes every `.` (the ``\\.`` token). The
    test reads the SHELL STRING verbatim, so the file contains a literal
    backslash before the dot — Python string `in` matches that byte-for-byte
    and avoids the regex-metachar confusion a pattern-match test would invite.
    """
    text = (REPO_ROOT / "app" / "deploy" / "update.sh").read_text(encoding="utf-8")
    for needle in (
        # The four-file regex (CHANGED-gated self-arm)
        "app/deploy/macro-am-edition\\.(service|timer)",
        "scripts/am_edition_live\\.py",
        "scripts/build_am_edition\\.py",
        # The disarm flag + symmetric stand-down wiring
        "AM_EDITION_LIVE_DISABLE",
        "disable --now",
        # Overlay-removal on stand-down
        "/var/lib/macro-live/public/am_edition.json",
        "/var/lib/macro-live/public/am_edition.html",
    ):
        assert needle in text, f"update.sh AM-edition block is missing: {needle!r}"
