"""tests/test_canada_canonical_board.py — CA-TRUTH: one canonical Canada Prophet
board per session (masterplan §5.0).

Regression coverage for the production defect: scripts/build_canada_library.py
built the Canada board with Branch-B ripe-list ordering inside
compute_canada_standouts() (stamping branch='B', rank_basis=
'momentum_screen_accruing', per-row board_pos), but the old main() then re-sorted
wide["buy"] with an obsolete composite key (_combine_key) and entry_open_first()
BEFORE writing site/factordata/canada_standouts.json — so the artifact's row order
silently contradicted its own board_pos stamps and its declared branch/rank_basis,
and diverged from the separately-recomputed page object in build_canada.py.

The fix: build_canada_library._build_canonical_board() is the ONE place the board
is built — Branch-B order (compute_canada_standouts -> _branch_b_order), enriched
in place (order-neutral), stamped with board-level authority fields, and NO sort
of any kind runs after it. main() writes and returns the exact same object;
build_canada.py renders that object verbatim (no second compute_canada_standouts
pass); scripts/build_canada._canada_board_ledger() logs it in that same order,
stamping board_definition on every row.

Tests import the REAL functions under test (compute_canada_standouts,
_build_canonical_board, _branch_b_order, _canada_board_ledger,
engine.board_ledger.append_board) — no mirrored logic — per the house convention
(tests/test_us_standouts_cascade_gate.py).
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import engine.board_ledger as bl  # noqa: E402
from engine.setups import entry_open_first as _old_entry_open_first  # noqa: E402
from lib import config as lib_config  # noqa: E402
from scripts import build_canada_library as bcal  # noqa: E402
from scripts import build_canada as bca  # noqa: E402


# ---------------------------------------------------------------------------
# Shared synthetic fixture: 3 buy rows engineered so the OLD composite key
# (_combine_key: align_tier=='aligned' group first, then setup-score percentile)
# and the OLD entry_open_first (buy_now + composite_z>0 floats to top, then by
# conviction score) BOTH disagree with the Branch-B order (group=entry_open
# before setting_up, then alpha desc within group).
#
#   Branch-B canonical order:      B.TO, C.TO, A.TO   (entry_open by alpha desc, then setting_up)
#   OLD entry_open_first order:    B.TO, A.TO, C.TO   (buy_now floats up, then conviction score desc)
#   OLD _combine_key order:        A.TO, C.TO, B.TO   (aligned group first, then setup-score desc)
# ---------------------------------------------------------------------------

def _base_buy_rows():
    """The 3 buy-admissible candidates only (A/B/C) — the fixture the Branch-B /
    OLD-order comparisons in test_canada_no_second_sort_after_branch_b reason
    about apples-to-apples (no watch-only rows mixed in)."""
    return [
        (0.9, {"ticker": "A.TO", "name": "Alpha Bank", "alpha": 0.6, "factor_z": 0.0,
              "setup": 0.9,
              "entry_signal": {"status": "wait_pullback"},
              "conviction": {"score": 90, "composite_z": 1.0}}),
        (0.2, {"ticker": "B.TO", "name": "Bravo Energy", "alpha": 2.0, "factor_z": 0.0,
              "setup": 0.2,
              "entry_signal": {"status": "buy_now"},
              "conviction": {"score": 40, "composite_z": 0.3}}),
        (0.5, {"ticker": "C.TO", "name": "Charlie Metals", "alpha": 1.0, "factor_z": 0.0,
              "setup": 0.5,
              "entry_signal": {"status": "partial"},
              "conviction": {"score": 70, "composite_z": 0.6}}),
    ]


def _synthetic_cand_and_maps():
    # + one strong-but-blocked candidate (W.TO): alpha clears BUY_MIN (0.5) but has
    # no align_map entry (not aligned, not near) -> alignment_gate drops it from
    # buy, and _build_watch's own admission criteria (alpha>=BUY_MIN, not aligned/
    # near) picks it up for real, so ledger tests can route through the REAL
    # _build_watch() output instead of hand-injecting board["watch"].
    cand = _base_buy_rows() + [
        (0.1, {"ticker": "W.TO", "name": "Watch Co", "alpha": 0.9, "factor_z": 0.0,
              "setup": 0.1, "conviction": {"score": 55, "verdict": "v", "verdict_zh": "v"}}),
    ]
    align_map = {
        "A.TO": {"aligned": True, "score": 0.8},
        "B.TO": {"aligned": False, "near": True, "score": 0.4},
        "C.TO": {"aligned": True, "score": 0.8},
        # W.TO deliberately absent -> not aligned, not near -> excluded from buy,
        # eligible for watch.
    }
    profiles = {t: r.get("conviction") for _s, r in cand for t in [r["ticker"]]}
    sig_verdict: dict = {}   # empty -> signal_gate.compact(None) on every row
    entry_sig: dict = {}
    risk_sig: dict = {}
    return cand, align_map, profiles, sig_verdict, entry_sig, risk_sig


@pytest.fixture(autouse=True)
def _hermetic_breadth_and_data_dir(tmp_path, monkeypatch):
    """compute_canada_standouts() reads _breadth_panel() (closes/sector/name) and
    lib.config.data_dir() (W8-G board-ledger first-seen lookup). Neither must touch
    real repo data in this sparse checkout — mirrors
    test_w8g_ca_days_since_signal_builder_enrichment's mocking pattern."""
    monkeypatch.setattr(bcal, "_breadth_panel",
                        lambda: (pd.DataFrame(), {}, {}))
    monkeypatch.setattr(lib_config, "data_dir", lambda: tmp_path)


def _no_real_track_ledger_write(monkeypatch):
    """_canada_board_ledger's TRD-popup step (build_canada.py) writes
    ca_track_ledger.json to the REAL site dir (engine.track_ledger.atomic_write) as
    a best-effort side step, independent of the board_ledger parquet store this
    file otherwise redirects to tmp_path. Neutralize it so hermetic tests never
    touch the real site/ tree (MM_DATA_GUARD)."""
    import engine.track_ledger as _tl
    monkeypatch.setattr(_tl, "atomic_write", lambda *_a, **_k: None)


def _build_board(overlay=None):
    cand, align_map, profiles, sig_verdict, entry_sig, risk_sig = _synthetic_cand_and_maps()
    eligible = sum(1 for _s, r in cand
                   if (align_map.get(r.get("ticker")) or {}).get("aligned"))
    return bcal._build_canonical_board(
        cand, as_of="2026-07-10", align_map=align_map, sig_verdict=sig_verdict,
        profiles=profiles, entry_sig=entry_sig, risk_sig=risk_sig,
        eligible=eligible, disp_regime=None, overlay=overlay)


# ---------------------------------------------------------------------------
# 1. Single source of truth
# ---------------------------------------------------------------------------

def test_canada_canonical_board_is_single_source_of_truth(tmp_path):
    """The object _build_canonical_board() returns IS the object main() writes to
    canada_standouts.json — EXECUTED via the real _write_canada_standouts() (the
    one write site main() calls), not a source-text pattern match. Byte-for-byte:
    what lands on disk must equal json.dumps() of the object main() returns."""
    board = _build_board()
    bcal._write_canada_standouts(board, tmp_path)
    written_path = tmp_path / "factordata" / "canada_standouts.json"
    assert written_path.exists()
    written = json.loads(written_path.read_text())
    expected = json.loads(json.dumps(board, separators=(",", ":"), default=str))
    assert written == expected, (
        "the bytes _write_canada_standouts() puts on disk must equal the returned "
        "board — a swapped/rebuilt copy at the write call site would diverge here"
    )
    assert [r["ticker"] for r in written["buy"]] == [r["ticker"] for r in board["buy"]]

    # narrow structural check for the ONE fact the executed test above cannot see:
    # that main() actually calls the (now proven byte-faithful) writer with the
    # unmodified `board` variable, not a mutated copy assembled at the call site
    # (mutation-kill target c — e.g. `_write_canada_standouts({**board, "buy":
    # swapped}, site)` would no longer match this exact call expression).
    src = Path(bcal.__file__).read_text()
    main_body = src.split("\ndef main(", 1)[1].split('\nif __name__', 1)[0]
    assert "_write_canada_standouts(board, site)" in main_body, (
        "main() must call _write_canada_standouts with the exact unmodified "
        "`board` object it returns"
    )
    assert main_body.rstrip().endswith("return board"), (
        "main() must return the canonical `board` object (CA-TRUTH), not a "
        "re-derived or renamed one"
    )


# ---------------------------------------------------------------------------
# 2. Artifact / page order parity
# ---------------------------------------------------------------------------

def test_canada_artifact_page_order_parity():
    """The written artifact's row order == board_pos order == the object
    build_canada.py renders (main()'s returned board, verbatim)."""
    board = _build_board()
    tickers = [r["ticker"] for r in board["buy"]]
    board_pos_order = [r["ticker"] for r in sorted(board["buy"], key=lambda r: r["board_pos"])]
    assert tickers == board_pos_order == ["B.TO", "C.TO", "A.TO"]

    # build_canada.py must render main()'s return value verbatim.
    src = Path(bca.__file__).read_text()
    assert 'setups = build_canada_library.main(alpha=alpha, overlay=' in src


def test_canada_page_render_has_no_rederive_or_resort_tokens():
    """scripts/build_canada.py must contain NEITHER of the two realistic forms of
    mutation (f) — a page-level re-derive/re-sort of the canonical board:
      (i)  a second compute_canada_standouts() recompute of the page object
           (the ORIGINAL defect: build_canada.py used to run this AFTER
           build_canada_library.main() already wrote+returned the canonical
           board, so the page could silently diverge from the artifact);
      (ii) an entry_open_first()-style re-sort of vm["setups"]["buy"] (the OLD
           page-facing composite/open-entry order this PR retired).

    Both the recompute call AND its import were deleted outright, so BOTH tokens
    are expected to be entirely absent from this file's source — confirmed by
    direct read before writing this test (grep for both names returned nothing).
    If either legitimately reappears for an unrelated reason in the future, scope
    this assert to exclude that specific site rather than deleting it wholesale.

    A THIRD, unnamed form — a novel raw `sorted()`/`.sort()` re-rank that reads
    neither name — is NOT caught by this or any test here at reasonable cost; the
    guard for that residual is the in-code CA-TRUTH comment at the `vm["setups"]
    = setups` assignment site (scripts/build_canada.py) plus the owed-session
    digest receipt (execution packet §17), not an automated assertion."""
    src = Path(bca.__file__).read_text()
    assert "compute_canada_standouts" not in src, (
        "build_canada.py must not re-derive the board via a second "
        "compute_canada_standouts() pass — it renders build_canada_library."
        "main()'s return value verbatim (CA-TRUTH); mutation-kill form (f-i)"
    )
    assert "entry_open_first" not in src, (
        "build_canada.py must not re-sort vm['setups']['buy'] with "
        "entry_open_first() (or any named re-rank) after main() returns the "
        "canonical board; mutation-kill form (f-ii)"
    )


# ---------------------------------------------------------------------------
# 3. Ledger order matches the canonical board
# ---------------------------------------------------------------------------

def test_canada_ledger_order_matches_canonical_board(tmp_path, monkeypatch):
    monkeypatch.setattr(bl, "_store_path", lambda m: tmp_path / f"{m.lower()}_board.parquet")
    monkeypatch.setenv("COLLECT_LANE", "nightly")
    _no_real_track_ledger_write(monkeypatch)

    # board["watch"] comes from the REAL _build_watch() output (fixture's W.TO
    # candidate), not a hand-injected list — routes this test through production
    # code end to end.
    board = _build_board()
    assert [w["ticker"] for w in board["watch"]] == ["W.TO"], (
        f"fixture must produce exactly one real watch row; got {board['watch']}"
    )
    latest = {"date": "2026-07-10"}

    bca._canada_board_ledger(board, latest)

    df = pd.read_parquet(tmp_path / "ca_board.parquet").sort_values("board_pos")
    n_buy = len(board["buy"])
    assert df["ticker"].tolist() == ["B.TO", "C.TO", "A.TO", "W.TO"]
    assert df["board_pos"].tolist() == [1, 2, 3, 4]
    assert (df["group"].tolist()[:n_buy] ==
            [r["group"] for r in board["buy"]])
    assert df.iloc[n_buy]["group"] == "watch"
    assert len(df) == n_buy + 1


# ---------------------------------------------------------------------------
# 4. No second sort after Branch-B
# ---------------------------------------------------------------------------

def test_canada_no_second_sort_after_branch_b():
    """Synthetic board where the OLD composite key AND the OLD entry_open_first
    would BOTH re-rank differently from Branch-B (see fixture docstring above).
    The canonical board must stay exactly Branch-B ordered."""
    board = _build_board()
    branch_b_order = [r["ticker"] for r in bcal._branch_b_order(
        [dict(r) for r in
         [{"ticker": "A.TO", "alpha": 0.6, "entry_signal": {"status": "wait_pullback"}},
          {"ticker": "B.TO", "alpha": 2.0, "entry_signal": {"status": "buy_now"}},
          {"ticker": "C.TO", "alpha": 1.0, "entry_signal": {"status": "partial"}}]],
        overlay={})]
    assert [r["ticker"] for r in board["buy"]] == branch_b_order == ["B.TO", "C.TO", "A.TO"]

    # the OLD order (computed independently here, NOT applied) proves the fixture
    # has teeth: it would have produced a DIFFERENT order than Branch-B. Scoped to
    # the buy-admissible A/B/C rows only (apples-to-apples with board["buy"]).
    old_order = [r["ticker"] for r in
                _old_entry_open_first([dict(r) for _s, r in _base_buy_rows()])]
    assert old_order != [r["ticker"] for r in board["buy"]], (
        "fixture must be engineered so the old open-entry-first re-sort disagrees "
        "with Branch-B"
    )

    src = Path(bcal.__file__).read_text()
    assert "_combine_key" not in src, (
        "the obsolete composite re-rank (_combine_key) must be fully removed from "
        "scripts/build_canada_library.py, not just unused"
    )
    assert "entry_open_first" not in src, (
        "entry_open_first must not be called anywhere in the CA board build path"
    )


# ---------------------------------------------------------------------------
# 5. Board-level authority stamps
# ---------------------------------------------------------------------------

def test_canada_official_pick_authority_false_under_branch_b():
    board = _build_board()
    assert board["board_definition"] == bcal.CA_BOARD_DEFINITION == "ca_prophet_branch_b_v1"
    assert board["authority"] == bcal.CA_BOARD_AUTHORITY == "screen"
    assert board["selection_status"] == "accruing"
    assert board["official_pick_authority"] is False


def test_canada_legacy_buy_key_is_projection_not_authority():
    board = _build_board()
    assert board["legacy_buy_key_semantics"] == "ripe_list_screen"
    assert board["official_pick_authority"] is False


# ---------------------------------------------------------------------------
# 6. board_definition stamped on every current-board ledger row
# ---------------------------------------------------------------------------

def test_canada_current_rows_stamp_board_definition(tmp_path, monkeypatch):
    monkeypatch.setattr(bl, "_store_path", lambda m: tmp_path / f"{m.lower()}_board.parquet")
    monkeypatch.setenv("COLLECT_LANE", "nightly")
    _no_real_track_ledger_write(monkeypatch)

    board = _build_board()   # board["watch"] is the REAL _build_watch() output
    latest = {"date": "2026-07-10"}

    bca._canada_board_ledger(board, latest)

    df = pd.read_parquet(tmp_path / "ca_board.parquet")
    assert (df["board_definition"] == bcal.CA_BOARD_DEFINITION).all(), (
        f"every CA board ledger row must stamp board_definition; got "
        f"{df['board_definition'].tolist()}"
    )


# ---------------------------------------------------------------------------
# 7. Legacy (unstamped) rows are never retroactively stamped / overwritten
# ---------------------------------------------------------------------------

def test_canada_legacy_rows_remain_unstamped(tmp_path, monkeypatch):
    """append_board's keep-FIRST semantics (engine/board_ledger.py, untouched here):
    a pre-existing legacy row (board_definition=None) keeps None after a LATER
    stamped append, and a same-(date,ticker) re-append can never overwrite the
    incumbent row — CA appends are lane-gated on nightly_advance_enabled()
    (tests/test_board_ledger.py pattern)."""
    monkeypatch.setattr(bl, "_store_path", lambda m: tmp_path / f"{m.lower()}_board.parquet")
    monkeypatch.setenv("COLLECT_LANE", "nightly")

    # day 1: legacy (unstamped) row
    n1 = bl.append_board(
        [{"ticker": "SHOP.TO", "group": "entry_open", "edge_z": 1.0}],
        market="CA", asof="2026-07-01")
    assert n1 == 1

    # day 2: a NEW stamped row for a different ticker
    n2 = bl.append_board(
        [{"ticker": "RY.TO", "group": "entry_open", "edge_z": 0.8,
          "board_definition": bcal.CA_BOARD_DEFINITION}],
        market="CA", asof="2026-07-02")
    assert n2 == 2

    df = pd.read_parquet(tmp_path / "ca_board.parquet")
    legacy_row = df[df["ticker"] == "SHOP.TO"].iloc[0]
    assert pd.isna(legacy_row["board_definition"]), (
        "a legacy row must NOT be retroactively stamped by a later append"
    )
    stamped_row = df[df["ticker"] == "RY.TO"].iloc[0]
    assert stamped_row["board_definition"] == bcal.CA_BOARD_DEFINITION

    # re-append the SAME (date, ticker) with a DIFFERENT (stamped) payload — keep-
    # FIRST means the incumbent (unstamped, edge_z=1.0) value wins, never overwritten
    n3 = bl.append_board(
        [{"ticker": "SHOP.TO", "group": "watch", "edge_z": 9.9,
          "board_definition": bcal.CA_BOARD_DEFINITION}],
        market="CA", asof="2026-07-01")
    assert n3 == 2   # still 2 rows — no duplicate added
    df2 = pd.read_parquet(tmp_path / "ca_board.parquet")
    row2 = df2[df2["ticker"] == "SHOP.TO"].iloc[0]
    assert row2["group"] == "entry_open"          # original value, NOT "watch"
    assert abs(float(row2["edge_z"]) - 1.0) < 1e-9  # original value, NOT 9.9
    assert pd.isna(row2["board_definition"]), (
        "keep-FIRST must not let a later re-append stamp board_definition onto an "
        "already-written legacy row"
    )


# ---------------------------------------------------------------------------
# 8. Laggards strip keeps the PAGE's historical count (n_lag=6, not the
#    canada_setups.json artifact's n_lag=12) — templates/canada.html.j2 renders
#    setups.laggards UNSLICED, so an n_lag drift back to 12 silently doubles the
#    user-visible "Weakest screen (laggards)" strip (review finding, PR #5926).
# ---------------------------------------------------------------------------

def _cand_with_many_laggards():
    """14 distinct laggard candidates (alpha well under LAG_MAX=-0.3) — more than
    both the fixed n_lag=6 ceiling AND the old n_lag=12 one, so a regression back
    to 12 is caught (14 candidates -> 12 laggards under the old value, still >6)."""
    cand, align_map, profiles, sig_verdict, entry_sig, risk_sig = _synthetic_cand_and_maps()
    for i in range(14):
        t = f"L{i:02d}.TO"
        cand.append((0.0, {"ticker": t, "name": f"Laggard {i} Corp",
                           "alpha": -1.0 - i * 0.1, "factor_z": 0.0,
                           "setup": 0.0}))
    return cand, align_map, profiles, sig_verdict, entry_sig, risk_sig


def test_canada_laggards_strip_capped_at_six():
    """The canonical board's laggards strip must stay at the page's historical
    n_lag=6 ceiling, even when far more than 6 (or 12) laggard candidates exist —
    a regression to n_lag=12 (or any drift) is caught here."""
    cand, align_map, profiles, sig_verdict, entry_sig, risk_sig = _cand_with_many_laggards()
    eligible = sum(1 for _s, r in cand
                   if (align_map.get(r.get("ticker")) or {}).get("aligned"))
    board = bcal._build_canonical_board(
        cand, as_of="2026-07-10", align_map=align_map, sig_verdict=sig_verdict,
        profiles=profiles, entry_sig=entry_sig, risk_sig=risk_sig,
        eligible=eligible, disp_regime=None, overlay=None)
    assert len(board["laggards"]) <= 6, (
        f"laggards strip must stay <= 6 (page's historical n_lag); got "
        f"{len(board['laggards'])} from 14 candidates — n_lag drifted"
    )
    assert len(board["laggards"]) == 6, (
        "with 14 laggard-eligible candidates the strip should fill to exactly 6"
    )


# ---------------------------------------------------------------------------
# 9. Standalone-lane overlay fallback (review finding F2, PR #5926): a lane that
# runs `python -m scripts.build_canada_library` directly (weekly.yml:219
# unconditionally; engine-render.yml:637 scope=all; daily.yml/render.yml
# failure-path nets) never threads a fresh `overlay` through main(). Without a
# fallback that lane would stamp oil_tailwind/lead_en/lead_zh with overlay={}
# (oil regime always OFF) — a schema_item_fields divergence tracking the CI lane
# instead of the actual oil regime. build_canada_library._last_rendered_overlay()
# resolves the LAST-RENDERED overlay from data/canada_regime/latest.json — the
# same file engine.canada_run.run() writes on every build_canada.py render
# (engine/canada_run.py:76-79: `"overlay": canada_overlay.snapshot(asof)`, shaped
# with a top-level "factors" list exactly as _oil_regime_on expects) and the same
# file current_liquidity() already reads for `liquidity_overlay`
# (scripts/build_canada_library.py:114-126, pre-existing precedent).
# ---------------------------------------------------------------------------

def test_last_rendered_overlay_resolves_from_persisted_regime_file(tmp_path, monkeypatch):
    monkeypatch.setattr(lib_config, "data_dir", lambda: tmp_path)
    regime_dir = tmp_path / "canada_regime"
    regime_dir.mkdir(parents=True)
    overlay_payload = {"score": 1.1, "state": "Risk-on",
                       "factors": [{"key": "oil", "risk": "on", "z": 1.5}]}
    (regime_dir / "latest.json").write_text(json.dumps(
        {"date": "2026-07-10", "overlay": overlay_payload}))
    resolved = bcal._last_rendered_overlay()
    assert resolved == overlay_payload
    # and it is actually USABLE by _oil_regime_on (the shape claim, not just the
    # round-trip) — the whole point of resolving it at all.
    assert bcal._oil_regime_on(resolved) is True


def test_last_rendered_overlay_absent_store_is_empty_not_fatal(tmp_path, monkeypatch):
    """No canada_regime/latest.json yet (fresh checkout, first-ever run) — must
    degrade to {} silently, never raise."""
    monkeypatch.setattr(lib_config, "data_dir", lambda: tmp_path)
    assert bcal._last_rendered_overlay() == {}


def test_last_rendered_overlay_malformed_file_is_empty_not_fatal(tmp_path, monkeypatch):
    monkeypatch.setattr(lib_config, "data_dir", lambda: tmp_path)
    regime_dir = tmp_path / "canada_regime"
    regime_dir.mkdir(parents=True)
    (regime_dir / "latest.json").write_text("{not valid json")
    assert bcal._last_rendered_overlay() == {}


def test_last_rendered_overlay_non_dict_overlay_key_is_empty_not_fatal(tmp_path, monkeypatch):
    """A stray/legacy `overlay: null` (or any non-dict) must degrade to {}, not
    propagate a type that breaks _oil_regime_on's `.get("factors")`."""
    monkeypatch.setattr(lib_config, "data_dir", lambda: tmp_path)
    regime_dir = tmp_path / "canada_regime"
    regime_dir.mkdir(parents=True)
    (regime_dir / "latest.json").write_text(json.dumps({"date": "2026-07-10", "overlay": None}))
    assert bcal._last_rendered_overlay() == {}


def test_main_wires_overlay_none_to_the_persisted_fallback():
    """The full standalone-lane call (main(alpha=..., overlay=None), as weekly.yml/
    engine-render.yml scope=all/daily.yml+render.yml failure-path nets invoke it)
    needs live data-store access this sparse checkout does not have — no precedent
    in this repo's test suite for driving any market builder's main() end-to-end
    (tests/test_us_standouts_cascade_gate.py and siblings all test the underlying
    REAL functions instead). This is the narrow, load-bearing structural check for
    the 2-line wiring the behavioral tests above cannot reach: main() must resolve
    overlay via _last_rendered_overlay() precisely when overlay is None."""
    src = Path(bcal.__file__).read_text()
    main_body = src.split("\ndef main(", 1)[1].split('\nif __name__', 1)[0]
    assert "if overlay is None:" in main_body
    assert "overlay = _last_rendered_overlay()" in main_body


# --- CA-DISCOVERY-SHADOW: broaden research recall without changing the board ---
def _ca_disc_fixture(n=215):
    cand, align, entry = [], {}, {}
    for i in range(n):
        ticker = f"C{i:03d}.TO"
        cand.append((float(n - i), {
            "ticker": ticker, "alpha": float(i) / 10,
            "board_pos": i + 1, "featured": i < 5, "group": "hostile-extra",
        }))
        if i % 3 == 0:
            align[ticker] = {"aligned": True}
        elif i % 3 == 1:
            align[ticker] = {"near": True}
        status = ("buy_now", "await_confluence", "extended", "blocked", None)[i % 5]
        if status is not None:
            entry[ticker] = {"status": status}
    return cand, align, entry


def test_ca_discovery_is_uncapped_and_carries_no_rank_or_score():
    from engine import canada_discovery_challenger as cadc
    cand, align, entry = _ca_disc_fixture()
    rows = cadc.build_candidates(cadc.freeze_evidence(cand, align, entry), "2026-09-16")
    assert len(rows) == 215
    assert len({r["security_ref_raw"] for r in rows}) == 215
    forbidden = {"alpha", "score", "rank", "board_pos", "featured", "group"}
    assert all(not (forbidden & set(r)) for r in rows)
    assert rows[0]["candidate_origin"] == "scored_screen+alignment_aligned"


def test_ca_discovery_availability_reuses_owner_entry_status_without_upgrading_it():
    from engine import canada_discovery_challenger as cadc
    statuses = {
        "OPEN.TO": "partial",
        "PULL.TO": "wait_pullback",
        "RAN.TO": "extended",
        "BLOCK.TO": "avoid",
        "WAIT.TO": "buy_soon",
    }
    cand = [(1.0, {"ticker": t}) for t in [*statuses, "MISS.TO"]]
    entry = {t: {"status": s} for t, s in statuses.items()}
    align = {t: {"aligned": True} for t in statuses}
    rows = {r["security_ref_raw"]: r for r in
            cadc.build_candidates(cadc.freeze_evidence(cand, align, entry), "2026-09-16")}
    assert rows["OPEN.TO"]["availability_status"] == cadc.ENTRY_OPEN
    assert rows["PULL.TO"]["availability_status"] == cadc.WAIT_PULLBACK
    assert rows["RAN.TO"]["availability_status"] == cadc.RAN_DONT_CHASE
    assert rows["BLOCK.TO"]["availability_status"] == cadc.BLOCKED
    assert rows["WAIT.TO"]["availability_status"] == cadc.WAIT_CONFLUENCE
    assert rows["MISS.TO"]["availability_status"] == cadc.UNAVAILABLE_DATA


def test_ca_discovery_never_calls_unaligned_timing_open_an_open_entry():
    from engine import canada_discovery_challenger as cadc
    cand = [(1.0, {"ticker": "BLOCKED.TO"})]
    entry = {"BLOCKED.TO": {"status": "partial"}}
    row = cadc.build_candidates(
        cadc.freeze_evidence(cand, {}, entry), "2026-09-16"
    )[0]
    assert row["availability_status"] == cadc.WAIT_CONFLUENCE
    assert row["availability_source"] == "alignment_blocked+entry_signal:partial"


def test_ca_discovery_does_not_mutate_or_read_published_board_fields():
    import copy
    from engine import canada_discovery_challenger as cadc
    cand, align, entry = _ca_disc_fixture(9)
    before = copy.deepcopy(cand)
    rows_a = cadc.build_candidates(cadc.freeze_evidence(cand, align, entry), "2026-09-16")
    for _score, row in cand:
        row["board_pos"] = 999
        row["featured"] = not bool(row["featured"])
        row["group"] = "changed"
    rows_b = cadc.build_candidates(cadc.freeze_evidence(cand, align, entry), "2026-09-16")
    assert rows_a == rows_b
    assert before != cand  # hostile extras really changed; output did not


def test_ca_discovery_registration_is_after_artifact_persist_and_before_return():
    from pathlib import Path
    source = (Path(__file__).resolve().parents[1] / "scripts" / "build_canada_library.py").read_text()
    persist = source.index("_write_canada_standouts(board, site)")
    register = source.index("_register_ca_shadow_challengers(", persist)
    return_board = source.index("    return board", register)
    assert persist < register < return_board

    helper = source.index("def _register_ca_shadow_challengers(")
    helper_end = source.index("\ndef _build_canonical_board", helper)
    block = source[helper:helper_end]
    assert "canada_discovery_challenger.freeze_population_contract" in block
    assert "populations.prealignment_research" in block
    assert "canada_discovery_challenger.build_candidates" in block


def test_ca_discovery_persists_only_zero_authority_lane_b_rows(tmp_path, monkeypatch):
    import pandas as pd
    from engine import board_shadow as bs
    from engine import canada_discovery_challenger as cadc
    from lib import config
    monkeypatch.setattr(config, "data_dir", lambda: tmp_path)
    monkeypatch.setenv("COLLECT_LANE", "nightly")
    monkeypatch.delenv("CN_LANE", raising=False)
    monkeypatch.setattr(bs, "_read_incumbent_positions", lambda *_a, **_k: {})
    bs.CHALLENGER_REGISTRY.clear()
    cand, align, entry = _ca_disc_fixture(12)
    frozen = cadc.freeze_evidence(cand, align, entry)
    try:
        bs.register_challenger("CA", cadc.DEFINITION,
                               discovery_fn=lambda asof: cadc.build_candidates(frozen, asof))
        receipt = bs.write_shadow([], market="CA", asof="2026-09-18")
        assert receipt["written"] == 12
        stored = pd.read_parquet(tmp_path / "prophet_shadow" / "ca_discovery.parquet")
        assert len(stored) == 12
        assert not stored["published_authority"].fillna(False).astype(bool).any()
        assert not stored["visible_to_user"].fillna(False).astype(bool).any()
    finally:
        bs.CHALLENGER_REGISTRY.clear()

# --- CA-NATIVE-INTEL / CA-RANK-RACE: typed ACCRUING family, zero authority ---
def test_ca_native_authority_types_are_explicit_and_non_fused():
    from engine import canada_native_intelligence as cni

    assert cni.RESIDUAL_MOMENTUM_STATUS == "ACCRUING"
    assert cni.RESIDUAL_MOMENTUM_AUTHORITY == "name_intelligence_shadow"
    assert cni.RESIDUAL_MOMENTUM_DEFINITION == "ca_residual_momentum_rank_v1"
    assert cni.C1_OIL_STATUS == "ACCRUING"
    assert cni.C1_OIL_AUTHORITY == "sector_context_only"
    assert cni.ANTICIPATION_US_GATE_DISPOSITION == "SCREEN_SHADOW"
    assert not hasattr(cni, "master_score")
    assert not hasattr(cni, "composite_score")


def test_ca_residual_ranker_scores_only_incumbent_calls_and_keeps_missing_null():
    from engine import canada_native_intelligence as cni

    calls = [
        {"ticker": "A.TO", "edge_z": 1.4},
        {"ticker": "B.TO", "edge_z": 0.2},
        {"ticker": "MISS.TO", "edge_z": None},
        {"ticker": "NAN.TO", "edge_z": float("nan")},
    ]
    out = cni.rank_residual_calls(calls)
    assert set(out) == {"A.TO", "B.TO", "MISS.TO", "NAN.TO"}
    assert out["A.TO"]["score_raw"] > out["B.TO"]["score_raw"]
    assert out["A.TO"]["score_conservative"] is None
    assert out["B.TO"]["score_conservative"] is None
    assert out["MISS.TO"] == {
        "score_raw": None,
        "score_conservative": None,
    }
    assert out["NAN.TO"] == {
        "score_raw": None,
        "score_conservative": None,
    }


def test_ca_residual_ranker_dedupes_incumbent_identity_without_originating_names():
    from engine import canada_native_intelligence as cni

    calls = [
        {"ticker": "A.TO", "edge_z": 0.4},
        {"ticker": "A.TO", "edge_z": 9.9},
        {"ticker": "B.TO", "edge_z": -0.2},
        {"ticker": None, "edge_z": 1.0},
    ]
    out = cni.rank_residual_calls(calls)
    assert list(out) == ["A.TO", "B.TO"]
    assert out["A.TO"]["score_raw"] == pytest.approx(0.4)
    assert out["B.TO"]["score_raw"] == pytest.approx(-0.2)


def test_ca_residual_ranker_persists_same_population_in_existing_lane_a(
    tmp_path, monkeypatch,
):
    import pandas as pd
    from engine import board_shadow as bs
    from engine import canada_native_intelligence as cni
    from lib import config

    monkeypatch.setattr(config, "data_dir", lambda: tmp_path)
    monkeypatch.setenv("COLLECT_LANE", "nightly")
    monkeypatch.delenv("CN_LANE", raising=False)
    monkeypatch.setattr(
        bs, "_read_incumbent_positions",
        lambda *_a, **_k: {"A.TO": 1, "B.TO": 2, "MISS.TO": 3},
    )
    bs.CHALLENGER_REGISTRY.clear()
    calls = [
        {"ticker": "A.TO", "edge_z": 1.2, "board_definition": "ca_prophet_branch_b_v1"},
        {"ticker": "B.TO", "edge_z": 0.3, "board_definition": "ca_prophet_branch_b_v1"},
        {"ticker": "MISS.TO", "edge_z": None, "board_definition": "ca_prophet_branch_b_v1"},
    ]
    try:
        bs.register_challenger(
            "CA", cni.RESIDUAL_MOMENTUM_DEFINITION,
            rank_fn=cni.rank_residual_calls,
        )
        receipt = bs.write_shadow(calls, market="CA", asof="2026-09-18")
        assert receipt["written"] == 3
        stored = pd.read_parquet(tmp_path / "prophet_shadow" / "ca_rank_pairs.parquet")
        assert set(stored["ticker"]) == {"A.TO", "B.TO", "MISS.TO"}
        assert set(stored["challenger_definition"]) == {
            cni.RESIDUAL_MOMENTUM_DEFINITION
        }
        assert set(stored["population_n"]) == {3}
        assert stored["challenger_offlist_n"].max() == 0
        by = stored.set_index("ticker")
        assert int(by.loc["A.TO", "challenger_rank"]) == 1
        assert int(by.loc["B.TO", "challenger_rank"]) == 2
        assert pd.isna(by.loc["MISS.TO", "challenger_rank"])
        assert stored["challenger_score_conservative"].isna().all()
    finally:
        bs.CHALLENGER_REGISTRY.clear()


def test_ca_builder_registers_native_rank_race_after_publication():
    from pathlib import Path

    source = (
        Path(__file__).resolve().parents[1] / "scripts" / "build_canada_library.py"
    ).read_text()
    persist = source.index("_write_canada_standouts(board, site)")
    register = source.index("_register_ca_shadow_challengers(", persist)
    return_board = source.index("    return board", register)
    assert persist < register < return_board

    helper = source.index("def _register_ca_shadow_challengers(")
    helper_end = source.index("\ndef _build_canonical_board", helper)
    block = source[helper:helper_end]
    assert "canada_native_intelligence.RESIDUAL_MOMENTUM_DEFINITION" in block
    assert "canada_discovery_challenger.DEFINITION" in block



def test_ca_population_contract_separates_immutable_official_and_research():
    from dataclasses import FrozenInstanceError
    from engine import canada_discovery_challenger as cadc

    cand = [
        (3.0, {"ticker": "A.TO", "score": 99}),
        (2.0, {"ticker": "B.V", "score": 88}),
        (1.0, {"ticker": "C.TO", "score": 77}),
    ]
    board = {
        "buy": [{"ticker": "A.TO", "group": "entry_open", "board_pos": 1}],
        "watch": [{"ticker": "B.V", "watch_reason": "knife"}],
    }
    contract = cadc.freeze_population_contract(
        official_board=board,
        candidates=cand,
        align_map={"A.TO": {"aligned": True}, "B.V": {"near": True}},
        entry_signals={"A.TO": {"status": "buy_now"}},
    )

    assert contract.official_screen.status == cadc.PopulationStatus.OBSERVED
    assert [(m.ticker, m.lane, m.owner_group) for m in contract.official_screen.members] == [
        ("A.TO", "buy", "entry_open"),
        ("B.V", "watch", "watch"),
    ]
    assert contract.prealignment_research.status == cadc.PopulationStatus.OBSERVED
    assert [m.ticker for m in contract.prealignment_research.members] == [
        "A.TO", "B.V", "C.TO",
    ]

    # The contract is a snapshot, not an alias to producer rows.
    board["buy"][0]["ticker"] = "MUTATED.TO"
    cand[0][1]["ticker"] = "MUTATED-RESEARCH.TO"
    assert contract.official_screen.members[0].ticker == "A.TO"
    assert contract.prealignment_research.members[0].ticker == "A.TO"
    with pytest.raises(FrozenInstanceError):
        contract.official_screen.status = cadc.PopulationStatus.UNAVAILABLE


def test_ca_population_contract_distinguishes_zero_from_unavailable_and_watch_only():
    from engine import canada_discovery_challenger as cadc

    unavailable = cadc.freeze_population_contract(
        official_board=None, candidates=None, align_map=None, entry_signals=None,
    )
    assert unavailable.official_screen.status == cadc.PopulationStatus.UNAVAILABLE
    assert unavailable.prealignment_research.status == cadc.PopulationStatus.UNAVAILABLE

    observed_zero = cadc.freeze_population_contract(
        official_board={"buy": [], "watch": []},
        candidates=[], align_map={}, entry_signals={},
    )
    assert observed_zero.official_screen.status == cadc.PopulationStatus.OBSERVED_ZERO
    assert observed_zero.prealignment_research.status == cadc.PopulationStatus.OBSERVED_ZERO

    watch_only = cadc.freeze_population_contract(
        official_board={"buy": [], "watch": [{"ticker": "WATCH.V"}]},
        candidates=[(1.0, {"ticker": "WATCH.V"})],
        align_map={}, entry_signals={},
    )
    assert watch_only.official_screen.status == cadc.PopulationStatus.OBSERVED
    assert [(m.ticker, m.lane) for m in watch_only.official_screen.members] == [
        ("WATCH.V", "watch"),
    ]


def test_ca_population_contract_refuses_official_identity_absent_from_research():
    from engine import canada_discovery_challenger as cadc

    with pytest.raises(ValueError, match="absent from pre-alignment research"):
        cadc.freeze_population_contract(
            official_board={"buy": [{"ticker": "OFFLIST.TO"}], "watch": []},
            candidates=[(1.0, {"ticker": "A.TO"})],
            align_map={}, entry_signals={},
        )


def test_ca_research_population_keeps_valid_zero_distinct_and_refuses_unknown_session():
    from engine import canada_discovery_challenger as cadc

    unavailable = cadc.freeze_research_population(None, None, None)
    with pytest.raises(cadc.ResearchPopulationUnavailable):
        cadc.build_candidates(unavailable, "2026-09-18")

    observed_zero = cadc.freeze_research_population([], {}, {})
    assert observed_zero.status == cadc.PopulationStatus.OBSERVED_ZERO
    assert cadc.build_candidates(observed_zero, "2026-09-18") == []

    observed = cadc.freeze_research_population(
        [(1.0, {"ticker": "RAW.V"})], {}, {},
    )
    for invalid_asof in (None, "", "None", "2026-09-18T00:00:00"):
        with pytest.raises(ValueError, match="source session"):
            cadc.build_candidates(observed, invalid_asof)


def test_ca_builder_registers_discovery_from_typed_population_contract():
    source = (
        Path(__file__).resolve().parents[1] / "scripts" / "build_canada_library.py"
    ).read_text()
    helper = source.index("def _register_ca_shadow_challengers(")
    helper_end = source.index("\ndef _build_canonical_board", helper)
    block = source[helper:helper_end]

    assert "freeze_population_contract(" in block
    assert ".prealignment_research" in block
    assert "freeze_evidence(" not in block


def test_ca_inherited_us_gate_dispositions_are_closed_and_immutable():
    from engine import canada_native_intelligence as cni

    assert {item.value for item in cni.InheritedGateDisposition} == {
        "STRUCTURAL_COMMON", "MARKET_VALIDATED", "SCREEN_SHADOW", "RETIRE",
    }
    assert dict(cni.INHERITED_US_GATE_DISPOSITIONS) == {
        cni.ANTICIPATION_PROFILE_CONTEXT_USE: cni.InheritedGateDisposition.SCREEN_SHADOW,
        cni.ANTICIPATION_POTENTIAL_SCORE_USE: cni.InheritedGateDisposition.SCREEN_SHADOW,
    }
    for use in cni.INHERITED_US_GATE_DISPOSITIONS:
        assert cni.require_inherited_gate_disposition(
            use, cni.InheritedGateDisposition.SCREEN_SHADOW,
        ) is cni.InheritedGateDisposition.SCREEN_SHADOW
    with pytest.raises(TypeError):
        cni.INHERITED_US_GATE_DISPOSITIONS["new-use"] = (
            cni.InheritedGateDisposition.MARKET_VALIDATED
        )
    with pytest.raises(KeyError, match="unclassified inherited US gate use"):
        cni.require_inherited_gate_disposition(
            "unknown-use", cni.InheritedGateDisposition.SCREEN_SHADOW,
        )
    with pytest.raises(ValueError, match="expected MARKET_VALIDATED"):
        cni.require_inherited_gate_disposition(
            cni.ANTICIPATION_PROFILE_CONTEXT_USE,
            cni.InheritedGateDisposition.MARKET_VALIDATED,
        )


def test_ca_builder_binds_actual_anticipation_uses_before_consumption():
    source = (
        Path(__file__).resolve().parents[1] / "scripts" / "build_canada_library.py"
    ).read_text()

    profile_audit = source.index(
        "ca_native_intelligence.ANTICIPATION_PROFILE_CONTEXT_USE"
    )
    gate_load = source.index('_load_gate("US")')
    potential_audit = source.index(
        "ca_native_intelligence.ANTICIPATION_POTENTIAL_SCORE_USE"
    )
    potential_call = source.index("name_score.potential_score(")
    candidate_freeze = source.index("cand.append(sc)")
    anticipation_write = source.index('rec["anticipation"] = _ant')
    entry_read = source.index("entry_signal.assess")

    assert source.count("require_inherited_gate_disposition(") == 2
    assert profile_audit < gate_load
    assert potential_audit < potential_call
    assert candidate_freeze < anticipation_write
    assert entry_read < potential_call


def test_ca_official_population_requires_both_computed_lanes_for_zero():
    from engine import canada_discovery_challenger as cadc

    missing_watch = cadc.freeze_official_screen({"buy": []})
    null_buy = cadc.freeze_official_screen({"buy": None, "watch": []})
    partial_watch = cadc.freeze_official_screen({
        "buy": None,
        "watch": [{"ticker": "WATCH.TO"}],
    })

    assert missing_watch == cadc.OfficialScreenPopulation(
        cadc.PopulationStatus.UNAVAILABLE, (),
    )
    assert null_buy == cadc.OfficialScreenPopulation(
        cadc.PopulationStatus.UNAVAILABLE, (),
    )
    assert partial_watch == cadc.OfficialScreenPopulation(
        cadc.PopulationStatus.UNAVAILABLE, (),
    )

    explicit_zero = cadc.freeze_official_screen({"buy": [], "watch": []})
    assert explicit_zero.status == cadc.PopulationStatus.OBSERVED_ZERO


def test_ca_discovery_contract_failure_does_not_disable_native_rank_race(monkeypatch):
    from engine import board_shadow as bs
    from engine import canada_discovery_challenger as cadc
    from engine import canada_native_intelligence as cni
    from scripts import build_canada_library as bcal

    registrations = []

    def record_register(market, definition, **kwargs):
        registrations.append((market, definition, tuple(sorted(kwargs))))

    monkeypatch.setattr(bs, "register_challenger", record_register)
    monkeypatch.setattr(
        cadc, "freeze_population_contract",
        lambda **_kwargs: (_ for _ in ()).throw(ValueError("discovery unavailable")),
    )

    bcal._register_ca_shadow_challengers(
        board={"buy": [], "watch": []},
        candidates=[],
        align_map={},
        entry_signals={},
    )

    assert registrations == [
        ("CA", cni.RESIDUAL_MOMENTUM_DEFINITION, ("rank_fn",)),
    ]
