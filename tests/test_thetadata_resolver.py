"""WP-RESOLVER — canonical ThetaData store resolver tests (CI-safe, hermetic).

Covers engine.thetadata_store.resolve_thetadata_store:
  - env tier resolves (source=env) when the path has store content
  - env set-but-missing warns loudly and falls through
  - empty-stub dirs (exist, but no eod/oi/greeks subdirs) do NOT resolve —
    that is the exact shape of the options_witness 0/18 incident
  - required=True raises RuntimeError naming every path tried + the purpose
  - store_root() back-compat wrapper still returns a Path

Plus the incident regression shape for engine.theme_options_witness:
  - _theta_store() delegates to the canonical resolver (per-module hardcoded
    fallback chain removed)
  - build() with NO resolvable store leaves a fresh committed real artifact
    untouched (keep-last-real) instead of clobbering it with an all-suppressed
    output.

All machine-specific tiers (env / data_dir / ops-wt) are monkeypatched to
tmp_path so these tests never touch a real store.
"""
from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import lib.config as libconfig  # noqa: E402
from engine import thetadata_store as tds  # noqa: E402


# --------------------------------------------------------------------------- #
# helpers                                                                       #
# --------------------------------------------------------------------------- #

def _mk_store(p: Path, tiers=("eod",), roots=("AAPL",)) -> Path:
    """Create a store that passes the content check — the REAL layout,
    ``{store}/{tier}/{ROOT}/{YEAR}.parquet``.

    AD-1T2b: this helper used to create bare tier DIRECTORIES only, which modelled
    a store shape that cannot exist in production with data in it, and which the
    resolver now correctly refuses (a drained store is not a store). Building one
    real root keeps every precedence assertion below testing precedence — against
    a store that could actually exist — instead of testing the old hole.
    """
    for t in tiers:
        for r in roots:
            d = p / t / r
            d.mkdir(parents=True, exist_ok=True)
            (d / "2026.parquet").write_bytes(b"")
    return p


def _mk_drained_store(p: Path, tiers=("eod", "oi", "greeks")) -> Path:
    """The AD-1T2b shape observed on the store-bearing M1 on 2026-09-29: every
    tier directory present, not one root inside any of them."""
    for t in tiers:
        (p / t).mkdir(parents=True, exist_ok=True)
    return p


@pytest.fixture()
def isolated_chain(tmp_path, monkeypatch):
    """Point every resolver tier at tmp_path so nothing machine-specific leaks in.

    Returns the (empty, non-existent) data_dir-tier store path; individual tests
    create content where they need it.
    """
    repo_data = tmp_path / "repo_data"
    repo_data.mkdir()
    monkeypatch.setattr(libconfig, "data_dir", lambda: repo_data)
    monkeypatch.setattr(tds, "_OPS_WT_STORE", tmp_path / "no_ops_wt")
    monkeypatch.delenv("THETADATA_STORE", raising=False)
    return repo_data / "thetadata_eod"


# --------------------------------------------------------------------------- #
# resolve_thetadata_store                                                       #
# --------------------------------------------------------------------------- #

class TestResolveChain:
    def test_env_valid_store_resolves_source_env(self, tmp_path, monkeypatch,
                                                 isolated_chain, caplog):
        env_store = _mk_store(tmp_path / "env_store", tiers=("eod", "oi"))
        monkeypatch.setenv("THETADATA_STORE", str(env_store))
        with caplog.at_level(logging.INFO, logger="engine.thetadata_store"):
            result = tds.resolve_thetadata_store(purpose="unit-test")
        assert result == env_store
        assert any("source=env" in r.message for r in caplog.records), \
            "resolver must log the resolution source (env)"
        assert any("unit-test" in r.message for r in caplog.records), \
            "resolver must log the purpose"

    def test_env_missing_warns_and_falls_through(self, tmp_path, monkeypatch,
                                                 isolated_chain, caplog):
        monkeypatch.setenv("THETADATA_STORE", str(tmp_path / "does_not_exist"))
        data_store = _mk_store(isolated_chain, tiers=("oi",))
        with caplog.at_level(logging.INFO, logger="engine.thetadata_store"):
            result = tds.resolve_thetadata_store(purpose="unit-test")
        assert result == data_store, "must fall through to the data_dir tier"
        warned = [r for r in caplog.records if r.levelno >= logging.WARNING]
        assert any("does not exist" in r.message for r in warned), \
            "set-but-missing THETADATA_STORE must warn loudly"
        assert any("source=data_dir" in r.message for r in caplog.records)

    def test_empty_stub_does_not_resolve(self, tmp_path, monkeypatch,
                                         isolated_chain, caplog):
        """The incident shape: a dir that EXISTS but holds no eod/oi/greeks."""
        stub = tmp_path / "stub_store"
        stub.mkdir()
        (stub / "random_file.txt").write_text("not a store")
        monkeypatch.setenv("THETADATA_STORE", str(stub))
        with caplog.at_level(logging.INFO, logger="engine.thetadata_store"):
            result = tds.resolve_thetadata_store(purpose="unit-test")
        assert result is None, "an empty stub dir must NOT resolve"
        warned = [r for r in caplog.records if r.levelno >= logging.WARNING]
        assert any("empty stub" in r.message for r in warned)

    def test_ops_wt_tier_resolves_last(self, tmp_path, monkeypatch,
                                       isolated_chain, caplog):
        ops = _mk_store(tmp_path / "ops_wt_store", tiers=("greeks",))
        monkeypatch.setattr(tds, "_OPS_WT_STORE", ops)
        with caplog.at_level(logging.INFO, logger="engine.thetadata_store"):
            result = tds.resolve_thetadata_store(purpose="unit-test")
        assert result == ops
        assert any("source=ops-wt" in r.message for r in caplog.records)

    def test_env_beats_data_dir_and_ops_wt(self, tmp_path, monkeypatch,
                                           isolated_chain):
        env_store = _mk_store(tmp_path / "env_store")
        _mk_store(isolated_chain)
        ops = _mk_store(tmp_path / "ops_wt_store")
        monkeypatch.setattr(tds, "_OPS_WT_STORE", ops)
        monkeypatch.setenv("THETADATA_STORE", str(env_store))
        assert tds.resolve_thetadata_store() == env_store

    def test_nothing_resolves_returns_none(self, isolated_chain, caplog):
        with caplog.at_level(logging.ERROR, logger="engine.thetadata_store"):
            assert tds.resolve_thetadata_store(purpose="unit-test") is None
        assert any("NONE" in r.message for r in caplog.records), \
            "total resolution failure must log loudly"

    def test_required_true_raises_naming_tried_paths(self, tmp_path, monkeypatch,
                                                     isolated_chain):
        env_path = tmp_path / "missing_env_store"
        monkeypatch.setenv("THETADATA_STORE", str(env_path))
        with pytest.raises(RuntimeError) as exc:
            tds.resolve_thetadata_store(required=True, purpose="unit-test-required")
        msg = str(exc.value)
        assert "unit-test-required" in msg, "message must name the purpose"
        assert str(env_path) in msg, "message must name the env path tried"
        assert str(isolated_chain) in msg, "message must name the data_dir path tried"
        assert str(tmp_path / "no_ops_wt") in msg, "message must name the ops-wt path tried"


# --------------------------------------------------------------------------- #
# store_root back-compat                                                        #
# --------------------------------------------------------------------------- #

class TestStoreRootBackCompat:
    def test_store_root_still_returns_path_when_missing(self, tmp_path,
                                                        monkeypatch):
        missing = tmp_path / "not_there"
        monkeypatch.setenv("THETADATA_STORE", str(missing))
        result = tds.store_root()
        assert isinstance(result, Path)
        assert result == missing, "back-compat: env value is returned even when missing"

    def test_store_root_override_wins(self, tmp_path, monkeypatch):
        monkeypatch.setenv("THETADATA_STORE", str(tmp_path / "env_store"))
        explicit = tmp_path / "explicit"
        assert tds.store_root(override=explicit) == explicit

    def test_store_root_warns_once_on_missing(self, tmp_path, monkeypatch, caplog):
        missing = tmp_path / "warn_once_store"
        monkeypatch.setenv("THETADATA_STORE", str(missing))
        tds._WARNED_MISSING_ROOTS.discard(str(missing))
        with caplog.at_level(logging.WARNING, logger="engine.thetadata_store"):
            tds.store_root()
            tds.store_root()
        hits = [r for r in caplog.records if str(missing) in r.message]
        assert len(hits) == 1, "missing-root warning must fire once per path, not per read"


# --------------------------------------------------------------------------- #
# theme_options_witness regression (0/18 all-suppressed incident shape)         #
# --------------------------------------------------------------------------- #

class TestWitnessIncidentRegression:
    def test_theta_store_delegates_to_canonical_resolver(self, tmp_path,
                                                         monkeypatch):
        from engine import theme_options_witness as mod
        sentinel = _mk_store(tmp_path / "sentinel_store", tiers=("oi",))
        calls = {}

        def fake_resolver(required=False, purpose=""):
            calls["required"] = required
            calls["purpose"] = purpose
            return sentinel

        monkeypatch.setattr(tds, "resolve_thetadata_store", fake_resolver)
        assert mod._theta_store() == sentinel
        assert calls["required"] is False
        assert "theme_options_witness" in calls["purpose"]

    def test_module_has_no_hardcoded_ops_wt_path(self):
        """The ops-wt path must live in ONE place (engine/thetadata_store)."""
        from engine import theme_options_witness as mod
        assert not hasattr(mod, "_MAIN_CHECKOUT_THETA")
        src = Path(mod.__file__).read_text(encoding="utf-8")
        assert "theta-ops-wt" not in src.replace(
            "engine.thetadata_store", ""), \
            "per-module hardcoded ops-wt fallback must be gone"

    def test_build_keeps_fresh_real_artifact_when_nothing_resolves(
            self, tmp_path, monkeypatch, isolated_chain):
        """End-to-end through the canonical resolver: NO tier resolves →
        _theta_store() is None → build() must leave the committed real
        artifact byte-identical (keep-last-real), never overwrite it with an
        all-suppressed output."""
        from engine import theme_options_witness as mod

        nw_out = tmp_path / "nw_out.json"
        site_out = tmp_path / "site_out.json"
        monkeypatch.setattr(mod, "_NW_OUT", nw_out)
        monkeypatch.setattr(mod, "_SITE_OUT", site_out)

        gen = datetime.now(tz=timezone.utc).isoformat()
        real = {
            "schema": "theme_options_witness.v1",
            "generated_at": gen,
            "coverage_stats": {"store_present": True, "n_themes": 18,
                               "n_themes_any_coverage": 18},
            "themes": {"T1": {"leg_a_call_oi_hhi": {"coverage_count": 5}}},
        }
        nw_out.write_text(json.dumps(real))
        site_out.write_text(json.dumps(real))
        before_nw = nw_out.read_text()
        before_site = site_out.read_text()

        # sanity: with every tier isolated to tmp, nothing resolves
        assert mod._theta_store() is None

        mod.build()

        assert nw_out.read_text() == before_nw, \
            "store-absent build must NOT clobber a fresh real NW artifact"
        assert site_out.read_text() == before_site, \
            "store-absent build must NOT clobber a fresh real site artifact"


class TestDrainedStoreIsNotAStore:
    """AD-1T2b — a store whose tier directories are all present but hold zero roots
    resolves to NOTHING. Observed live on the M1 (m1studio) 2026-09-29 beside a
    _manifest.json still reading `"status": "healthy", "complete_t1_roots": 372`.

    The old predicate admitted it, and the options-intel producer then published a
    blank DEGRADED/MIXED_VINTAGE brief over the last good one and exited 0.
    """

    def test_drained_store_does_not_resolve(self, tmp_path, monkeypatch, isolated_chain):
        drained = _mk_drained_store(tmp_path / "drained")
        monkeypatch.setenv("THETADATA_STORE", str(drained))
        assert tds._has_store_content(drained) is False
        assert tds._drained_store(drained) is True
        assert tds.resolve_thetadata_store() is None

    def test_drained_store_raises_under_required(self, tmp_path, monkeypatch,
                                                 isolated_chain):
        drained = _mk_drained_store(tmp_path / "drained")
        monkeypatch.setenv("THETADATA_STORE", str(drained))
        with pytest.raises(RuntimeError, match="drained"):
            tds.resolve_thetadata_store(required=True, purpose="ad1t2b")

    def test_a_drained_candidate_falls_through_to_a_real_one(self, tmp_path,
                                                             monkeypatch,
                                                             isolated_chain):
        """Precedence is by CONTENT, not position: a drained higher-priority
        candidate must not shadow a real store further down the chain."""
        drained = _mk_drained_store(tmp_path / "drained_env")
        real = _mk_store(tmp_path / "real_ops_wt")
        monkeypatch.setenv("THETADATA_STORE", str(drained))
        monkeypatch.setattr(tds, "_OPS_WT_STORE", real)
        assert tds.resolve_thetadata_store(purpose="ad1t2b") == real

    def test_one_real_root_is_thinness_and_still_resolves(self, tmp_path,
                                                         monkeypatch,
                                                         isolated_chain):
        """The over-tightening guard: thin-but-real data is a legitimate
        NO_SIGNAL/INSUFFICIENT_COVERAGE publish, never infrastructure failure."""
        thin = _mk_store(tmp_path / "thin", tiers=("eod",), roots=("AAPL",))
        monkeypatch.setenv("THETADATA_STORE", str(thin))
        assert tds.resolve_thetadata_store(purpose="ad1t2b") == thin

    def test_a_stray_file_in_a_tier_is_not_a_root(self, tmp_path, monkeypatch,
                                                  isolated_chain):
        """`.DS_Store` / lock files must not revive the false positive."""
        d = _mk_drained_store(tmp_path / "stray")
        (d / "eod" / ".DS_Store").write_text("")
        (d / "_writer.lock").write_text("")
        monkeypatch.setenv("THETADATA_STORE", str(d))
        assert tds.resolve_thetadata_store() is None


class TestUnreadableIsNeverDrained:
    """AD-1T2b regression guard — the tightening must fail OPEN.

    Deciding "does this store hold data" needs a readdir, and on the ops host the
    three tier dirs are SYMLINKS onto an external volume
    (scripts/publish_r2.py::_walk_files). Listing them is exactly the operation
    that is denied or hangs under launchd — which is why
    scripts/build_options_hub_nightly.py::preflight_store bounds it in a daemon
    thread and exits 4 on timeout. That guard runs AFTER resolution, so an
    unbounded or fail-CLOSED readdir inside the resolver would sit in front of
    the only protection against it, in the one function every consumer calls, and
    would report an INTACT store as missing across every nightly lane.

    So: only a PROVABLY drained store may be refused. Denied, blocked, errored or
    probe-disabled must all resolve exactly as they did before this check existed.
    """

    def test_a_denied_tier_still_resolves_and_is_not_called_drained(self, tmp_path):
        store = _mk_store(tmp_path / "store", tiers=("eod",), roots=("SPY",))
        (store / "eod").chmod(0o000)
        try:
            assert tds._classify_store(store) == tds._UNKNOWN
            # The whole point: PRESENT, not drained.
            assert tds._has_store_content(store) is True
            assert tds._drained_store(store) is False
        finally:
            (store / "eod").chmod(0o755)

    def test_a_denied_tier_resolves_through_the_public_resolver(
            self, tmp_path, monkeypatch):
        store = _mk_store(tmp_path / "store", tiers=("eod",), roots=("SPY",))
        (store / "eod").chmod(0o000)
        monkeypatch.setenv("THETADATA_STORE", str(store))
        try:
            assert tds.resolve_thetadata_store(purpose="t") == store
            # required=True must NOT raise on an unreadable store — that is the
            # false RED this guard exists to prevent.
            assert tds.resolve_thetadata_store(required=True, purpose="t") == store
        finally:
            (store / "eod").chmod(0o755)

    def test_a_blocked_listing_is_bounded_and_resolves(self, tmp_path, monkeypatch):
        """A hung readdir must not wedge the resolver, and must not read as empty."""
        store = _mk_drained_store(tmp_path / "store")
        monkeypatch.setattr(tds, "_STORE_PROBE_S", 0.1)

        real_iterdir = Path.iterdir

        def _slow(self):
            if self.name in tds._STORE_TIERS:
                import time
                time.sleep(5)
            return real_iterdir(self)

        monkeypatch.setattr(Path, "iterdir", _slow)
        import time as _t
        t0 = _t.monotonic()
        verdict = tds._classify_store(store)
        elapsed = _t.monotonic() - t0
        assert verdict == tds._UNKNOWN
        assert elapsed < 3, f"probe was not bounded: {elapsed:.1f}s"
        assert tds._has_store_content(store) is True

    def test_probe_disabled_never_claims_emptiness(self, tmp_path, monkeypatch):
        store = _mk_drained_store(tmp_path / "store")
        assert tds._classify_store(store) == tds._DRAINED     # control
        monkeypatch.setattr(tds, "_STORE_PROBE_S", 0)
        assert tds._classify_store(store) == tds._UNKNOWN
        assert tds._has_store_content(store) is True

    def test_a_stub_with_no_tiers_needs_no_readdir(self, tmp_path, monkeypatch):
        """The stub case must stay stat-only — it predates this check."""
        stub = tmp_path / "stub"
        stub.mkdir()
        called = []
        real_iterdir = Path.iterdir
        monkeypatch.setattr(
            Path, "iterdir",
            lambda self: (called.append(self), real_iterdir(self))[1])
        assert tds._classify_store(stub) == tds._NO_TIERS
        assert called == [], f"stub classification performed a readdir: {called}"


class TestDrainedFactReachesTheSurfacedMessage:
    """AD-1T2b — scripts/build_options_intel_brief.py captures the resolver's
    records and publishes splitlines()[-1] as its CI annotation, so a diagnostic
    emitted mid-loop never reaches the operator. The terminal line must carry it.
    """

    def test_terminal_none_line_names_the_drained_candidate(
            self, tmp_path, monkeypatch, caplog):
        drained = _mk_drained_store(tmp_path / "drained")
        monkeypatch.setenv("THETADATA_STORE", str(drained))
        with caplog.at_level(logging.ERROR, logger=tds.log.name):
            assert tds.resolve_thetadata_store(purpose="t") is None
        last = [r.getMessage() for r in caplog.records
                if r.levelno >= logging.ERROR][-1]
        assert "resolved store=NONE" in last
        assert "DRAINED" in last, f"drained fact absent from the surfaced line: {last}"
        assert str(drained) in last

    def test_required_error_names_the_drained_candidate_and_the_refill_writer(
            self, tmp_path, monkeypatch):
        drained = _mk_drained_store(tmp_path / "drained")
        monkeypatch.setenv("THETADATA_STORE", str(drained))
        with pytest.raises(RuntimeError) as ei:
            tds.resolve_thetadata_store(required=True, purpose="t")
        msg = str(ei.value)
        assert "DRAINED" in msg and str(drained) in msg
        assert "backfill_thetadata_eod" in msg


class TestDrainedCandidatesDisambiguateNone:
    """AD-1T2b — `resolve_thetadata_store() is None` stopped meaning one thing.

    Before, None meant "no store anywhere" and writers treated it as a
    fresh-install permit. After the drained-store refusal it ALSO means "the
    canonical store exists but is empty", and a writer that cannot tell them
    apart will mint a SECOND store beside the drained one —
    scripts/backfill_thetadata_eod.py's second-store guard (AD-1T1 §D/RF3)
    depends on this helper to keep working.
    """

    def test_fresh_install_reports_no_drained_candidates(self, tmp_path, monkeypatch):
        monkeypatch.setenv("THETADATA_STORE", str(tmp_path / "nope"))
        monkeypatch.setattr(tds, "_OPS_WT_STORE", tmp_path / "also-nope")
        monkeypatch.setattr(libconfig, "data_dir", lambda: tmp_path / "none")
        assert tds.drained_store_candidates() == []

    def test_a_drained_canonical_store_is_reported(self, tmp_path, monkeypatch):
        drained = _mk_drained_store(tmp_path / "drained")
        monkeypatch.setenv("THETADATA_STORE", str(drained))
        monkeypatch.setattr(tds, "_OPS_WT_STORE", tmp_path / "nope")
        monkeypatch.setattr(libconfig, "data_dir", lambda: tmp_path / "none")
        assert tds.resolve_thetadata_store(purpose="t") is None   # the ambiguity
        assert tds.drained_store_candidates() == [drained]        # resolved by this

    def test_a_real_store_is_not_reported_drained(self, tmp_path, monkeypatch):
        real = _mk_store(tmp_path / "real", tiers=("eod",), roots=("SPY",))
        monkeypatch.setenv("THETADATA_STORE", str(real))
        monkeypatch.setattr(tds, "_OPS_WT_STORE", tmp_path / "nope")
        monkeypatch.setattr(libconfig, "data_dir", lambda: tmp_path / "none")
        assert tds.drained_store_candidates() == []

    def test_an_unreadable_store_is_not_reported_drained(self, tmp_path, monkeypatch):
        """Fail open here too — refusing a backfill because a store could not be
        listed would block the one writer that can repair a real drain."""
        store = _mk_store(tmp_path / "store", tiers=("eod",), roots=("SPY",))
        (store / "eod").chmod(0o000)
        monkeypatch.setenv("THETADATA_STORE", str(store))
        monkeypatch.setattr(tds, "_OPS_WT_STORE", tmp_path / "nope")
        monkeypatch.setattr(libconfig, "data_dir", lambda: tmp_path / "none")
        try:
            assert tds.drained_store_candidates() == []
        finally:
            (store / "eod").chmod(0o755)

    def test_backfill_actually_consults_the_helper(self):
        """The guard is only real if the writer wires it in (a helper nobody
        calls is the same defect as no helper)."""
        src = Path("scripts/backfill_thetadata_eod.py").read_text()
        assert "drained_store_candidates" in src, \
            "backfill no longer consults drained_store_candidates() — its " \
            "second-store guard is bypassable through the fresh-install path"
        assert "refusing to mint a second T1 store" in src
