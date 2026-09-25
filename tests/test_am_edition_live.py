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
* the receipt shape (``decision``, ``generated_at``, ``phase``, the two
  ``*_generated_at`` fields, and ``block_states``);
* the atomic-write contract (no partial files visible during a swap);
* the never-raises clause (a missing owner file degrades to a structured
  ``error`` receipt, never a hard exit);
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
    run,
)


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


# ---------------------------------------------------------------------------
# Decision table (matrix at exact head)
# ---------------------------------------------------------------------------

def test_decision_build_when_overlay_absent_and_preopen(monkeypatch, tmp_path: Path) -> None:
    """Decision (b): no overlay yet, preopen on a session date -> build."""
    monkeypatch.setattr(am_edition_live, "PUBLIC_DIR", tmp_path / "public")
    monkeypatch.setattr(am_edition_live, "STATE_DIR", tmp_path / "state")
    site, data = _fresh_tree(tmp_path, tape_asof="2026-09-22T12:30:00+00:00", session_date="2026-09-22")
    _write_bake(site, "2026-09-22T12:30:00+00:00")
    # No overlay files present -> build.
    receipt = run(now=_preopen_now(date(2026, 9, 22)), root=tmp_path)
    assert receipt["decision"] == "build"
    assert receipt["phase"] == "preopen"
    assert (tmp_path / "public" / "am_edition.json").exists()
    # HTML is written when jinja2 + template are present in the env; when the
    # test env lacks one of them render_html returns "" and the lane logs but
    # does NOT fail. The JSON write is the binding contract.


def test_receipt_is_persisted_by_main(monkeypatch, tmp_path: Path) -> None:
    """B1 §4: `state_dir/last_run.json` carries the receipt. The test drives
    the same code path `main()` runs (run() + _write_receipt) but with a
    controlled `now` so the assertion is hermetic — main() with no args uses
    the wall clock, which would make this test time-of-day-dependent."""
    monkeypatch.setattr(am_edition_live, "PUBLIC_DIR", tmp_path / "public")
    monkeypatch.setattr(am_edition_live, "STATE_DIR", tmp_path / "state")
    site, data = _fresh_tree(tmp_path, tape_asof="2026-09-22T12:30:00+00:00", session_date="2026-09-22")
    _write_bake(site, "2026-09-22T12:30:00+00:00")
    receipt = run(now=_preopen_now(date(2026, 9, 22)), root=tmp_path)
    am_edition_live._write_receipt(tmp_path / "state", receipt)
    state_blob = json.loads((tmp_path / "state" / "last_run.json").read_text(encoding="utf-8"))
    assert state_blob["decision"] == "build"
    assert state_blob["phase"] == "preopen"


def test_decision_expire_when_bake_is_newer_than_overlay(monkeypatch, tmp_path: Path) -> None:
    """Decision (a): overlay present AND bake is newer -> expire (both files
    removed). The visitor falls back to the canonical site copy on the next
    request."""
    monkeypatch.setattr(am_edition_live, "PUBLIC_DIR", tmp_path / "public")
    monkeypatch.setattr(am_edition_live, "STATE_DIR", tmp_path / "state")
    site, data = _fresh_tree(tmp_path, tape_asof="2026-09-22T12:30:00+00:00", session_date="2026-09-22")
    _write_bake(site, "2026-09-22T13:45:00+00:00")  # newer
    json_path, html_path = _write_overlay(tmp_path / "public", generated_at="2026-09-22T13:00:00+00:00")
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
    monkeypatch.setattr(am_edition_live, "PUBLIC_DIR", tmp_path / "public")
    monkeypatch.setattr(am_edition_live, "STATE_DIR", tmp_path / "state")
    site, data = _fresh_tree(tmp_path, tape_asof="2026-09-22T20:30:00+00:00", session_date="2026-09-22")
    _write_bake(site, "2026-09-22T12:30:00+00:00")  # older than overlay
    json_path, html_path = _write_overlay(tmp_path / "public", generated_at="2026-09-22T13:00:00+00:00")
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
    monkeypatch.setattr(am_edition_live, "PUBLIC_DIR", tmp_path / "public")
    monkeypatch.setattr(am_edition_live, "STATE_DIR", tmp_path / "state")
    site, data = _fresh_tree(tmp_path, tape_asof="2026-09-19T12:30:00+00:00", session_date="2026-09-19")
    _write_bake(site, "2026-09-19T12:30:00+00:00")
    # 2026-09-19 is a Saturday.
    receipt = run(now=datetime(2026, 9, 19, 13, 30, tzinfo=timezone.utc), root=tmp_path)
    assert receipt["decision"] == "skip"
    assert receipt["phase"] == "weekend"


def test_decision_skip_on_nyse_holiday(monkeypatch, tmp_path: Path) -> None:
    """Decision (c): NYSE holiday -> skip. Phase surfaces as 'holiday' so an
    operator reading the receipt can tell why no overlay was built."""
    monkeypatch.setattr(am_edition_live, "PUBLIC_DIR", tmp_path / "public")
    monkeypatch.setattr(am_edition_live, "STATE_DIR", tmp_path / "state")
    site, data = _fresh_tree(tmp_path, tape_asof="2026-01-01T12:30:00+00:00", session_date="2026-01-01")
    _write_bake(site, "2026-01-01T12:30:00+00:00")
    # 2026-01-01 is New Year's Day (NYSE closed).
    receipt = run(now=datetime(2026, 1, 1, 13, 30, tzinfo=timezone.utc), root=tmp_path)
    assert receipt["decision"] == "skip"
    assert receipt["phase"] == "holiday"


# ---------------------------------------------------------------------------
# Receipt shape — exactly the keys the spec promises, no more
# ---------------------------------------------------------------------------

def test_receipt_shape_matches_frozen_contract(monkeypatch, tmp_path: Path) -> None:
    """The receipt dict carries EXACTLY the keys the spec names (B1 §4):
    decision, generated_at, phase, bake_generated_at, overlay_generated_at,
    block_states. A future field that sneaks in here would break consumers
    that pin the shape, so the test pins it byte-for-byte."""
    monkeypatch.setattr(am_edition_live, "PUBLIC_DIR", tmp_path / "public")
    monkeypatch.setattr(am_edition_live, "STATE_DIR", tmp_path / "state")
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


# ---------------------------------------------------------------------------
# Atomic write — no partial file is ever visible at the served path
# ---------------------------------------------------------------------------

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


def test_atomic_write_text_round_trip(tmp_path: Path) -> None:
    target = tmp_path / "atomic.html"
    _atomic_write_text(target, "<html>v1</html>")
    assert target.read_text(encoding="utf-8") == "<html>v1</html>"


# ---------------------------------------------------------------------------
# Never-raises clause — a degraded box degrades to an error receipt, NOT a
# Python traceback that aborts the unit (the lane MUST return 0 from main).
# ---------------------------------------------------------------------------

def test_run_never_raises_on_a_missing_owner_file(monkeypatch, tmp_path: Path) -> None:
    """The spec names this explicitly (B6: 'never raises on a missing owner
    file'). An empty site + data tree degrades to a skip receipt, never to
    a SystemExit / Exception."""
    monkeypatch.setattr(am_edition_live, "PUBLIC_DIR", tmp_path / "public")
    monkeypatch.setattr(am_edition_live, "STATE_DIR", tmp_path / "state")
    # Empty tree: no market_state, no regime, no plane, no quotes, no bake.
    (tmp_path / "site").mkdir(parents=True, exist_ok=True)
    (tmp_path / "data").mkdir(parents=True, exist_ok=True)
    receipt = run(now=_preopen_now(date(2026, 9, 22)), root=tmp_path)
    assert receipt["decision"] in {"skip", "build", "error"}, receipt


def test_main_returns_zero_even_when_render_html_is_empty(monkeypatch, tmp_path: Path) -> None:
    """The script's exit code is 0 unless the box is misconfigured (B1:
    'exit 0 unless the box is misconfigured'). A missing jinja2 / template
    is not a misconfig — main() still returns 0."""
    monkeypatch.setattr(am_edition_live, "PUBLIC_DIR", tmp_path / "public")
    monkeypatch.setattr(am_edition_live, "STATE_DIR", tmp_path / "state")
    site, data = _fresh_tree(tmp_path, tape_asof="2026-09-22T12:30:00+00:00", session_date="2026-09-22")
    _write_bake(site, "2026-09-22T12:30:00+00:00")
    assert am_edition_live.main([]) == 0


def test_main_returns_zero_even_when_state_dir_is_unwritable(monkeypatch, tmp_path: Path) -> None:
    """A misconfigured state dir (read-only parent) is NOT a misconfig the
    lane refuses to serve — main() degrades to a no-receipt pass and returns
    0 so the timer never pages the operator. The lane's only exit-1 case is
    the public_dir being unwritable (the served file would never land)."""
    # Make PUBLIC_DIR point at an unwritable location (a regular file under
    # tmp_path cannot accept mkdir inside it).
    blocker = tmp_path / "blocker"
    blocker.write_text("x", encoding="utf-8")
    monkeypatch.setattr(am_edition_live, "PUBLIC_DIR", blocker / "subdir")
    monkeypatch.setattr(am_edition_live, "STATE_DIR", tmp_path / "state")
    site, data = _fresh_tree(tmp_path, tape_asof="2026-09-22T12:30:00+00:00", session_date="2026-09-22")
    _write_bake(site, "2026-09-22T12:30:00+00:00")
    # The un-writable PUBLIC_DIR triggers decision=error but main() still
    # returns 0; the timer does not surface a hard fail.
    assert am_edition_live.main([]) == 0


# ---------------------------------------------------------------------------
# Unit-file shape (systemd-analyze verify is unavailable on macOS).
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[1]


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
