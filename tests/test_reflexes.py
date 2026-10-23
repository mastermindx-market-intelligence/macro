"""Neural Web W6a — Reflex registry + firings ledgers + triage push spine.

Tests guard:
  1. Registry validation (reflexes.yml loaded, names unique, paths match
     convention, claim_family prefix 'reflex.').
  2. record_firing: appends a valid single-line JSON to firings.jsonl.
  3. load_firings: round-trip read.
  4. adapt_reflexes: mapping to spine-index rows with ungraded honesty.
  5. push_priority_alerts: threshold filter, dedup window, disabled-by-default
     no-op, dispatch calls mocked.
  6. Staging-glob assertions for the two migrated lanes (intraday-fastpath +
     commodity-sentinel) — data/reflexes/ is covered in their commit steps.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest import mock

import pytest
import yaml

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"


def _worktree_root() -> Path:
    """Return the worktree root (repo root one level above tests/)."""
    return ROOT


# ---------------------------------------------------------------------------
# 1. Registry validation
# ---------------------------------------------------------------------------

class TestReflexRegistry:
    def test_reflexes_yml_exists(self):
        assert (ROOT / "config" / "reflexes.yml").exists(), (
            "config/reflexes.yml must exist (W6a deliverable)"
        )

    def test_registry_loads_without_error(self):
        from engine.neuralweb.reflexes import load_registry, invalidate_cache
        invalidate_cache()
        reg = load_registry(ROOT)
        assert isinstance(reg, dict)
        assert len(reg) >= 2, "at least 2 reflexes registered"

    def test_all_names_unique(self):
        raw = yaml.safe_load((ROOT / "config" / "reflexes.yml").read_text())
        names = list((raw.get("reflexes") or {}).keys())
        assert len(names) == len(set(names)), f"duplicate reflex names: {names}"

    def test_firings_paths_match_convention(self):
        raw = yaml.safe_load((ROOT / "config" / "reflexes.yml").read_text())
        pattern = re.compile(r"^data/reflexes/([^/]+)/firings\.jsonl$")
        for name, entry in (raw.get("reflexes") or {}).items():
            fj = entry.get("firings_jsonl")
            if fj is None:
                continue
            m = pattern.match(str(fj))
            assert m, (
                f"{name}: firings_jsonl {fj!r} does not match "
                f"data/reflexes/<name>/firings.jsonl"
            )
            assert m.group(1) == name, (
                f"{name}: firings_jsonl path names wrong reflex ({m.group(1)!r})"
            )

    def test_claim_family_prefix(self):
        raw = yaml.safe_load((ROOT / "config" / "reflexes.yml").read_text())
        for name, entry in (raw.get("reflexes") or {}).items():
            cf = entry.get("claim_family")
            if cf is None:
                continue
            assert str(cf).startswith("reflex."), (
                f"{name}: claim_family {cf!r} must start with 'reflex.'"
            )

    def test_mirroring_reflexes_have_firings_jsonl(self):
        """Reflexes marked migration_status=mirroring MUST have a firings_jsonl path."""
        raw = yaml.safe_load((ROOT / "config" / "reflexes.yml").read_text())
        for name, entry in (raw.get("reflexes") or {}).items():
            if entry.get("migration_status") == "mirroring":
                assert entry.get("firings_jsonl") is not None, (
                    f"{name}: migration_status=mirroring requires firings_jsonl"
                )

    def test_meta_block_present(self):
        raw = yaml.safe_load((ROOT / "config" / "reflexes.yml").read_text())
        meta = raw.get("meta") or {}
        assert meta.get("schema_version") == 1
        assert "ledger_law" in meta
        assert "push_tier_law" in meta

    def test_regime_selfheal_is_mirroring(self):
        raw = yaml.safe_load((ROOT / "config" / "reflexes.yml").read_text())
        reflexes = raw.get("reflexes") or {}
        assert "regime_stale_selfheal" in reflexes, "regime_stale_selfheal must be registered"
        assert reflexes["regime_stale_selfheal"]["migration_status"] == "mirroring"

    def test_commodity_shock_is_mirroring(self):
        raw = yaml.safe_load((ROOT / "config" / "reflexes.yml").read_text())
        reflexes = raw.get("reflexes") or {}
        assert "commodity_shock" in reflexes, "commodity_shock must be registered"
        assert reflexes["commodity_shock"]["migration_status"] == "mirroring"

    def test_graded_true_names_an_implementing_grader(self):
        """`graded: true` is a promise the repo must keep — name the grader.

        Defect (W3 review, PR #5679, reviewer R3): commodity_shock declared
        graded: true with a note promising "Graded at 1d/5d horizon vs commodity
        ETF bench" while NO grader implemented it anywhere.  Its firings accrue
        nightly and adapt_reflexes() folds every one of them with
        outcome_graded=False, so the registry advertised a forward meter that was
        never running.  Two siblings (btc_flash_crash, shock_deescalation) carried
        the same false declaration and were corrected in the same PR.

        WHAT THIS PINS: a graded: true entry must name an implementing file in
        `grader:` and that file must exist.  WHAT IT DOES NOT PROVE: that the
        named grader is wired into a lane, or that it actually reads this
        reflex's firings — grade_qledger.py, for instance, grades whitehouse
        claims generically and never names the reflex.  The cheap half of the
        defect (a promise with no file behind it at all) is what closes here.
        """
        raw = yaml.safe_load((ROOT / "config" / "reflexes.yml").read_text())
        offenders: list[str] = []
        for name, entry in (raw.get("reflexes") or {}).items():
            if not entry.get("graded"):
                continue
            grader = entry.get("grader")
            if not grader:
                offenders.append(
                    f"{name}: graded: true but no `grader:` key — either name the "
                    f"file that grades it or set graded: false"
                )
            elif not (ROOT / str(grader)).exists():
                offenders.append(f"{name}: grader {grader!r} does not exist")
        assert not offenders, (
            "reflexes.yml declares grading it does not implement:\n"
            + "\n".join(f"  - {o}" for o in offenders)
        )

    def test_commodity_shock_grading_declaration_is_truthful(self):
        """The specific regression: commodity_shock must not re-acquire a
        graded: true it cannot back.  Flipping it back is legal ONLY in a PR
        that also ships the grader (which this guard then requires to exist)."""
        raw = yaml.safe_load((ROOT / "config" / "reflexes.yml").read_text())
        entry = (raw.get("reflexes") or {})["commodity_shock"]
        if entry.get("graded"):
            grader = ROOT / str(entry.get("grader") or "")
            assert entry.get("grader") and grader.exists(), (
                "commodity_shock re-declared graded: true with no grader behind "
                "it — this is the exact W3 review defect (PR #5679, R3)"
            )
        else:
            assert entry.get("graded_note"), (
                "an ungraded shadow reflex must still say what happens to its "
                "firings — nulls printed, not hidden"
            )

    def test_whitehouse_is_registered_not_mirroring(self):
        """Whitehouse is sacred — must be registered only, NOT mirroring in W6a."""
        raw = yaml.safe_load((ROOT / "config" / "reflexes.yml").read_text())
        reflexes = raw.get("reflexes") or {}
        assert "whitehouse_alert" in reflexes
        assert reflexes["whitehouse_alert"]["migration_status"] == "registered", (
            "whitehouse_alert must be 'registered', NOT 'mirroring', in W6a "
            "(whitehouse single-writer contract is SACRED — untouched until W6b)"
        )


# ---------------------------------------------------------------------------
# 2. record_firing: append + single-line JSON
# ---------------------------------------------------------------------------

class TestRecordFiring:
    def test_appends_one_json_line(self, tmp_path):
        from engine.neuralweb.reflexes import record_firing
        rec = record_firing("test_reflex", {
            "ts": "2026-07-04T12:00:00+00:00",
            "trigger_type": "staleness_check",
            "trigger_key": "test:key:1",
            "action_taken": "test_action",
            "scope_type": "macro",
            "scope_key": "regime",
            "direction": 0,
            "horizon_d": None,
            "asof": "2026-07-04",
        }, root=tmp_path)
        fj = tmp_path / "data" / "reflexes" / "test_reflex" / "firings.jsonl"
        assert fj.exists(), "firings.jsonl must be created"
        lines = [l for l in fj.read_text().splitlines() if l.strip()]
        assert len(lines) == 1, f"expected 1 line, got {len(lines)}"
        parsed = json.loads(lines[0])
        assert parsed["reflex"] == "test_reflex"
        assert parsed["claim_family"] == "reflex.test_reflex"
        assert parsed["is_context_only"] is True
        assert parsed["desk"] == "reflex"
        assert "claim_id" in parsed

    def test_appends_multiple_firings_as_separate_lines(self, tmp_path):
        from engine.neuralweb.reflexes import record_firing
        for i in range(3):
            record_firing("multi_test", {
                "ts": f"2026-07-04T12:0{i}:00+00:00",
                "trigger_type": "price_state_machine",
                "trigger_key": f"key:{i}",
                "action_taken": "append_events",
                "asof": "2026-07-04",
            }, root=tmp_path)
        fj = tmp_path / "data" / "reflexes" / "multi_test" / "firings.jsonl"
        lines = [l for l in fj.read_text().splitlines() if l.strip()]
        assert len(lines) == 3, f"expected 3 lines, got {len(lines)}"
        for line in lines:
            json.loads(line)  # each line must be valid JSON

    def test_each_line_is_single_json_object(self, tmp_path):
        """No multiline JSON — each line must parse independently."""
        from engine.neuralweb.reflexes import record_firing
        record_firing("single_line_test", {
            "ts": "2026-07-04T00:00:00+00:00",
            "trigger_type": "staleness_check",
            "trigger_key": "k",
            "action_taken": "a",
            "asof": "2026-07-04",
            "extra": {"nested": {"deep": [1, 2, 3]}},
        }, root=tmp_path)
        fj = tmp_path / "data" / "reflexes" / "single_line_test" / "firings.jsonl"
        content = fj.read_text()
        assert "\n" not in content.strip(), (
            "firing record must be a single line (no embedded newlines)"
        )
        assert content.strip().startswith("{"), "must be a JSON object"

    def test_returns_record_with_expected_keys(self, tmp_path):
        from engine.neuralweb.reflexes import record_firing
        rec = record_firing("key_test", {
            "ts": "2026-07-04T12:00:00+00:00",
            "trigger_key": "k",
            "asof": "2026-07-04",
        }, root=tmp_path)
        assert "claim_id" in rec
        assert "reflex" in rec
        assert "claim_family" in rec
        assert rec["is_context_only"] is True

    def test_nonexistent_parent_dir_is_created(self, tmp_path):
        """record_firing must create data/reflexes/<name>/ if absent."""
        from engine.neuralweb.reflexes import record_firing
        record_firing("fresh_reflex", {
            "ts": "2026-07-04T00:00:00Z",
            "trigger_key": "k",
            "asof": "2026-07-04",
        }, root=tmp_path)
        assert (tmp_path / "data" / "reflexes" / "fresh_reflex" / "firings.jsonl").exists()


    @pytest.mark.parametrize("key,value", [
        ("claim_id", "caller_invented"), ("reflex", "different_reflex"),
        ("claim_family", "claimed.alpha"), ("desk", "execution"),
        ("is_context_only", False), ("is_context_only", None),
        ("is_context_only", 0), ("is_context_only", "false"),
    ])
    def test_producer_owned_fields_cannot_be_overridden(self, tmp_path, key, value):
        from engine.neuralweb.reflexes import record_firing, load_firings
        import hashlib
        payload = {"ts": "2026-09-28T17:30:00Z", "trigger_key": "synthetic-only",
                   "trigger_type": "test", "action_taken": "NONE", key: value}
        before = json.dumps(payload, sort_keys=True)
        rec = record_firing("test_reflex", payload, root=tmp_path)
        expected_id = hashlib.sha256(b"test_reflex:2026-09-28T17:30:00Z:synthetic-only").hexdigest()[:16]
        owned = {"claim_id": expected_id, "reflex": "test_reflex",
                 "claim_family": "reflex.test_reflex", "desk": "reflex", "is_context_only": True}
        for field, expected in owned.items():
            assert rec[field] == expected
            assert type(rec[field]) is type(expected)
        assert load_firings("test_reflex", root=tmp_path) == [rec]
        assert json.dumps(payload, sort_keys=True) == before

    def test_all_reserved_overrides_preserve_identity_and_context(self, tmp_path):
        from engine.neuralweb.reflexes import record_firing
        payload = {"ts": "2026-09-28T17:30:00Z", "trigger_key": "k", "extra": {"observation": 0}}
        ordinary = record_firing("test_reflex", payload, root=tmp_path)
        conflicting = dict(payload, claim_id="wrong", reflex="wrong", claim_family="wrong",
                           desk="wrong", is_context_only=False)
        repaired = record_firing("test_reflex", conflicting, root=tmp_path)
        assert repaired == ordinary
        assert repaired["is_context_only"] is True

    def test_ordinary_payload_serialization_is_byte_preserved(self, tmp_path):
        from engine.neuralweb.reflexes import record_firing
        import hashlib
        payload = {"ts": "2026-09-28T17:30:00Z", "trigger_key": "k",
                   "scope_type": "entity", "scope_key": "SYNTHETIC", "direction": -1,
                   "horizon_d": 5, "extra": {"zero": 0, "missing": None}}
        expected = {"claim_id": hashlib.sha256(b"test_reflex:2026-09-28T17:30:00Z:k").hexdigest()[:16],
                    "reflex": "test_reflex", "claim_family": "reflex.test_reflex",
                    "desk": "reflex", "is_context_only": True, **payload}
        expected.setdefault("asof", "2026-09-28")
        rec = record_firing("test_reflex", payload, root=tmp_path)
        assert rec == expected
        path = tmp_path / "data/reflexes/test_reflex/firings.jsonl"
        assert path.read_bytes() == (json.dumps(expected, default=str) + "\n").encode()

    def test_matching_owner_metadata_is_compatible(self, tmp_path):
        from engine.neuralweb.reflexes import record_firing
        payload = {"ts": "2026-09-28T17:30:00Z", "trigger_key": "k", "is_context_only": True}
        first = record_firing("test_reflex", payload, root=tmp_path)
        second = record_firing("test_reflex", dict(first), root=tmp_path)
        assert first == second

    def test_write_failure_still_returns_canonical_metadata(self, tmp_path):
        from engine.neuralweb.reflexes import record_firing
        with mock.patch("builtins.open", side_effect=OSError("synthetic write failure")):
            rec = record_firing("test_reflex", {"ts": "2026-09-28T17:30:00Z",
                "trigger_key": "k", "is_context_only": False, "reflex": "wrong"}, root=tmp_path)
        assert rec["reflex"] == "test_reflex"
        assert rec["is_context_only"] is True
        assert "_write_error" in rec


# ---------------------------------------------------------------------------
# 3. load_firings: round-trip
# ---------------------------------------------------------------------------

class TestLoadFirings:
    def test_returns_empty_list_when_file_absent(self, tmp_path):
        from engine.neuralweb.reflexes import load_firings
        result = load_firings("nonexistent", root=tmp_path)
        assert result == []

    def test_round_trip(self, tmp_path):
        from engine.neuralweb.reflexes import record_firing, load_firings
        payload = {
            "ts": "2026-07-04T15:30:00+00:00",
            "trigger_type": "staleness_check",
            "trigger_key": "regime:2026-07-03:store:2026-07-04",
            "action_taken": "rerun_engine",
            "scope_type": "macro",
            "scope_key": "regime",
            "direction": 0,
            "horizon_d": None,
            "asof": "2026-07-04",
        }
        record_firing("round_trip", payload, root=tmp_path)
        loaded = load_firings("round_trip", root=tmp_path)
        assert len(loaded) == 1
        assert loaded[0]["reflex"] == "round_trip"
        assert loaded[0]["claim_family"] == "reflex.round_trip"
        assert loaded[0]["trigger_key"] == payload["trigger_key"]

    def test_skips_malformed_lines_without_crash(self, tmp_path):
        from engine.neuralweb.reflexes import record_firing, load_firings
        record_firing("partial_test", {"ts": "2026-07-04T00:00:00Z",
                                        "trigger_key": "k", "asof": "2026-07-04"},
                      root=tmp_path)
        fj = tmp_path / "data" / "reflexes" / "partial_test" / "firings.jsonl"
        with open(fj, "a") as f:
            f.write("INVALID JSON LINE\n")
        record_firing("partial_test", {"ts": "2026-07-04T01:00:00Z",
                                        "trigger_key": "k2", "asof": "2026-07-04"},
                      root=tmp_path)
        loaded = load_firings("partial_test", root=tmp_path)
        assert len(loaded) == 2, (
            f"should load 2 valid records, skipping the malformed line; got {len(loaded)}"
        )


# ---------------------------------------------------------------------------
# 4. adapt_reflexes: spine index mapping
# ---------------------------------------------------------------------------

class TestAdaptReflexes:
    def _make_firing(self, name: str, direction: int = -1) -> dict:
        return {
            "claim_id": f"abc{name}",
            "reflex": name,
            "claim_family": f"reflex.{name}",
            "ts": "2026-07-04T12:00:00+00:00",
            "trigger_type": "price_state_machine",
            "trigger_key": f"{name}:key",
            "action_taken": "append_events",
            "desk": "reflex",
            "asof": "2026-07-04",
            "scope_type": "macro",
            "scope_key": "gold",
            "direction": direction,
            "horizon_d": 1,
            "is_context_only": True,
        }

    def test_adapt_reflexes_empty_when_no_files(self, tmp_path):
        from engine.neuralweb.query import adapt_reflexes
        df, gaps = adapt_reflexes(root=tmp_path)
        assert df.empty or len(df) == 0

    def test_adapt_reflexes_maps_to_correct_ledger(self, tmp_path):
        from engine.neuralweb.reflexes import record_firing
        from engine.neuralweb.query import adapt_reflexes
        firing = self._make_firing("commodity_shock", direction=-1)
        record_firing("commodity_shock", firing, root=tmp_path)
        df, gaps = adapt_reflexes(root=tmp_path)
        assert len(df) >= 1
        row = df[df["engine"] == "reflex.commodity_shock"].iloc[0]
        assert row["ledger"] == "reflexes"
        assert row["engine"] == "reflex.commodity_shock"
        assert str(row["as_of"]) == "2026-07-04"

    def test_adapt_reflexes_outcome_graded_is_false(self, tmp_path):
        """UNGRADED HONESTY: outcome_graded must be False for all reflex rows."""
        from engine.neuralweb.reflexes import record_firing
        from engine.neuralweb.query import adapt_reflexes
        record_firing("ungraded_test", {
            "ts": "2026-07-04T00:00:00Z",
            "trigger_key": "k",
            "direction": -1,
            "asof": "2026-07-04",
            "scope_type": "macro",
        }, root=tmp_path)
        df, _ = adapt_reflexes(root=tmp_path)
        reflex_rows = df[df["ledger"] == "reflexes"]
        assert len(reflex_rows) >= 1
        assert reflex_rows["outcome_graded"].fillna(False).all() == False, (
            "UNGRADED HONESTY VIOLATION: outcome_graded must be False for all "
            "reflex firings — grading is future work, no fabrication allowed"
        )

    def test_adapt_reflexes_graded_at_is_null(self, tmp_path):
        """No graded_at timestamp should be fabricated for ungraded rows."""
        from engine.neuralweb.reflexes import record_firing
        from engine.neuralweb.query import adapt_reflexes
        record_firing("graded_at_test", {
            "ts": "2026-07-04T00:00:00Z",
            "trigger_key": "k",
            "asof": "2026-07-04",
        }, root=tmp_path)
        df, _ = adapt_reflexes(root=tmp_path)
        reflex_rows = df[df["ledger"] == "reflexes"]
        assert reflex_rows["graded_at"].isna().all(), (
            "graded_at must be null for ungraded reflex firings"
        )

    def test_adapt_reflexes_direction_preserved(self, tmp_path):
        from engine.neuralweb.reflexes import record_firing
        from engine.neuralweb.query import adapt_reflexes
        record_firing("dir_test", {
            "ts": "2026-07-04T00:00:00Z",
            "trigger_key": "k",
            "direction": -1,
            "asof": "2026-07-04",
            "scope_type": "macro",
        }, root=tmp_path)
        df, _ = adapt_reflexes(root=tmp_path)
        row = df[df["engine"] == "reflex.dir_test"].iloc[0]
        assert int(row["direction"]) == -1

    def test_adapt_reflexes_scope_type_normalised(self, tmp_path):
        """Invalid scope_type is normalised to 'macro'."""
        from engine.neuralweb.reflexes import record_firing
        from engine.neuralweb.query import adapt_reflexes
        record_firing("scope_test", {
            "ts": "2026-07-04T00:00:00Z",
            "trigger_key": "k",
            "scope_type": "INVALID_SCOPE",
            "asof": "2026-07-04",
        }, root=tmp_path)
        df, _ = adapt_reflexes(root=tmp_path)
        row = df[df["engine"] == "reflex.scope_test"].iloc[0]
        assert row["scope_type"] == "macro"

    def test_adapt_reflexes_size_binding_is_false(self, tmp_path):
        """Reflex rows are never real-money sized (Article 2)."""
        from engine.neuralweb.reflexes import record_firing
        from engine.neuralweb.query import adapt_reflexes
        record_firing("sizing_test", {"ts": "2026-07-04T00:00:00Z",
                                       "trigger_key": "k", "asof": "2026-07-04"},
                      root=tmp_path)
        df, _ = adapt_reflexes(root=tmp_path)
        reflex_rows = df[df["ledger"] == "reflexes"]
        assert not reflex_rows["size_binding"].fillna(False).any(), (
            "size_binding must be False for all reflex rows (Article-2 perimeter)"
        )


# ---------------------------------------------------------------------------
# 5. push_priority_alerts: threshold, dedup, disabled no-op, dispatch mocked
# ---------------------------------------------------------------------------

class TestPushPriorityAlerts:
    def _mock_config(self, enabled: bool = False, threshold: int = 60):
        return {
            "notify": {
                "telegram": {"enabled": True},
                "discord": {"enabled": False},
                "site_url": "https://example.com",
            },
            "alert_push": {"enabled": enabled, "threshold": threshold, "window_hours": 6},
        }

    def _sample_alert(self, priority: int = 70, source: str = "macro",
                      type_: str = "ebp_widening") -> dict:
        return {
            "source": source,
            "type": type_,
            "asset": "macro",
            "headline": "Test alert",
            "detail": "detail",
            "priority": priority,
            "tier": "act",
            "severity": "critical",
            "age_days": 1,
            "action": "high-conviction",
            "action_zh": "高信念",
            "source_label": "Macro",
            "source_label_zh": "宏观",
            "source_icon": "📊",
            "link": "macro.html#test",
            "validation": {"backtested": False},
            "cross_asset_tag": "neutral",
        }

    def test_disabled_by_default_returns_empty(self):
        """With alert_push.enabled=false, push_priority_alerts is a no-op."""
        from engine import alert_triage as at
        with mock.patch("lib.config.load", return_value=self._mock_config(enabled=False)):
            result = at.push_priority_alerts()
        assert result == [], (
            "push_priority_alerts must be a pure no-op when alert_push.enabled=false"
        )

    def test_threshold_filter(self, tmp_path):
        """Alerts below threshold are not dispatched."""
        from engine import alert_triage as at
        low = self._sample_alert(priority=40)
        high = self._sample_alert(priority=75)
        dedup = tmp_path / "push_sent.jsonl"

        with mock.patch("lib.config.load", return_value=self._mock_config(enabled=True)):
            with mock.patch.object(at, "build_triage",
                                   return_value={"alerts": [low, high]}):
                with mock.patch("scripts.notify.send_telegram", return_value=True) as tg:
                    with mock.patch("scripts.notify.send_discord", return_value=False):
                        result = at.push_priority_alerts(
                            threshold=60, _dedup_store=dedup)

        assert len(result) == 1, (
            f"only the high-priority alert should be dispatched; got {len(result)}"
        )
        assert result[0]["priority"] == 75

    def test_dedup_window_suppresses_repeat(self, tmp_path):
        """Same (source, type, asset) within window_hours is not re-dispatched."""
        from engine import alert_triage as at
        alert = self._sample_alert(priority=80)
        dedup = tmp_path / "push_sent.jsonl"

        with mock.patch("lib.config.load", return_value=self._mock_config(enabled=True)):
            with mock.patch.object(at, "build_triage",
                                   return_value={"alerts": [alert]}):
                with mock.patch("scripts.notify.send_telegram", return_value=True):
                    with mock.patch("scripts.notify.send_discord", return_value=False):
                        # First dispatch
                        r1 = at.push_priority_alerts(threshold=60, _dedup_store=dedup)
                        # Second dispatch — same alert, same window
                        r2 = at.push_priority_alerts(threshold=60, _dedup_store=dedup)

        assert len(r1) == 1, "first call should dispatch"
        assert len(r2) == 0, "second call within dedup window should be silent"

    def test_push_suppress_list_never_dispatches(self, tmp_path):
        """rotation/entered_book is on the suppress list and must never push."""
        from engine import alert_triage as at
        suppressed = self._sample_alert(priority=90, source="rotation",
                                        type_="entered_book")
        dedup = tmp_path / "push_sent.jsonl"

        with mock.patch("lib.config.load", return_value=self._mock_config(enabled=True)):
            with mock.patch.object(at, "build_triage",
                                   return_value={"alerts": [suppressed]}):
                with mock.patch("scripts.notify.send_telegram", return_value=True):
                    with mock.patch("scripts.notify.send_discord", return_value=False):
                        result = at.push_priority_alerts(threshold=60, _dedup_store=dedup)

        assert len(result) == 0, (
            "rotation/entered_book must never be dispatched (documented-null IC, "
            "Article-2 explicit floor exception)"
        )

    def test_dispatch_calls_notify_functions(self, tmp_path):
        """When enabled + above threshold, send_telegram is called."""
        from engine import alert_triage as at
        alert = self._sample_alert(priority=80)
        dedup = tmp_path / "push_sent.jsonl"

        with mock.patch("lib.config.load", return_value=self._mock_config(enabled=True)):
            with mock.patch.object(at, "build_triage",
                                   return_value={"alerts": [alert]}):
                with mock.patch("scripts.notify.send_telegram", return_value=True) as tg:
                    with mock.patch("scripts.notify.send_discord", return_value=False) as dc:
                        result = at.push_priority_alerts(threshold=60, _dedup_store=dedup)

        tg.assert_called_once()
        assert len(result) == 1

    def test_dedup_store_is_appended_after_dispatch(self, tmp_path):
        """push_sent.jsonl receives an entry after a successful dispatch."""
        from engine import alert_triage as at
        alert = self._sample_alert(priority=80)
        dedup = tmp_path / "push_sent.jsonl"

        with mock.patch("lib.config.load", return_value=self._mock_config(enabled=True)):
            with mock.patch.object(at, "build_triage",
                                   return_value={"alerts": [alert]}):
                with mock.patch("scripts.notify.send_telegram", return_value=True):
                    with mock.patch("scripts.notify.send_discord", return_value=False):
                        at.push_priority_alerts(threshold=60, _dedup_store=dedup)

        assert dedup.exists(), "push_sent.jsonl must exist after dispatch"
        lines = [l for l in dedup.read_text().splitlines() if l.strip()]
        assert len(lines) == 1, "one dedup entry per dispatch"
        rec = json.loads(lines[0])
        assert "sent_at" in rec
        assert rec["source"] == alert["source"]

    def test_no_dispatch_when_no_channels_available(self, tmp_path):
        """When both channels fail, no dedup entry is written."""
        from engine import alert_triage as at
        alert = self._sample_alert(priority=80)
        dedup = tmp_path / "push_sent.jsonl"

        with mock.patch("lib.config.load", return_value=self._mock_config(enabled=True)):
            with mock.patch.object(at, "build_triage",
                                   return_value={"alerts": [alert]}):
                with mock.patch("scripts.notify.send_telegram", return_value=False):
                    with mock.patch("scripts.notify.send_discord", return_value=False):
                        result = at.push_priority_alerts(threshold=60, _dedup_store=dedup)

        assert result == [], "no dispatch when channels unavailable"
        assert not dedup.exists() or dedup.read_text().strip() == "", (
            "push_sent.jsonl must not be written when no channel succeeded"
        )


# ---------------------------------------------------------------------------
# 6. Staging-glob assertions for the two migrated lanes
# ---------------------------------------------------------------------------

def _commit_step_bodies(wf_name: str) -> list[str]:
    """Return the 'run' bodies of commit steps in the given workflow."""
    wf_path = WORKFLOWS / wf_name
    doc = yaml.safe_load(wf_path.read_text())
    bodies = []
    for job in (doc.get("jobs") or {}).values():
        runs = [s.get("run", "") for s in job.get("steps", []) if s.get("run")]
        bodies += [r for r in runs if "git add" in r and ("git commit" in r or "git push" in r)]
    return bodies


class TestStagingGlobs:
    def test_intraday_fastpath_stages_reflexes_dir(self):
        """intraday-fastpath commit step must stage data/reflexes/ so a
        regime_stale_selfheal firing is never left as unstaged tracked change."""
        bodies = _commit_step_bodies("intraday-fastpath.yml")
        assert bodies, "no commit step found in intraday-fastpath.yml"
        staged_all = " ".join(
            add
            for body in bodies
            for add in re.findall(r"git add ([^\n]+)", body)
        )
        assert "data/reflexes" in staged_all, (
            "intraday-fastpath.yml commit step must stage data/reflexes/ "
            "(W6a SENTINEL STAGING LAW: regime_stale_selfheal writes there)"
        )

    def test_commodity_sentinel_stages_reflexes_dir(self):
        """commodity-sentinel commit step must stage data/reflexes/ so a
        commodity_shock firing is never left as unstaged tracked change."""
        bodies = _commit_step_bodies("commodity-sentinel.yml")
        assert bodies, "no commit step found in commodity-sentinel.yml"
        staged_all = " ".join(
            add
            for body in bodies
            for add in re.findall(r"git add ([^\n]+)", body)
        )
        assert "data/reflexes" in staged_all, (
            "commodity-sentinel.yml commit step must stage data/reflexes/ "
            "(W6a SENTINEL STAGING LAW: commodity_shock writes there)"
        )

    def test_intraday_fastpath_still_stages_regime_artifacts(self):
        """Sanity: intraday-fastpath must still stage the original regime artifacts."""
        bodies = _commit_step_bodies("intraday-fastpath.yml")
        staged_all = " ".join(
            add
            for body in bodies
            for add in re.findall(r"git add ([^\n]+)", body)
        )
        assert "data/regime" in staged_all, (
            "intraday-fastpath.yml must still stage data/regime/latest.json"
        )

    def test_commodity_sentinel_still_stages_commodity_artifacts(self):
        """Sanity: commodity-sentinel must still stage data/commodity/."""
        bodies = _commit_step_bodies("commodity-sentinel.yml")
        staged_all = " ".join(
            add
            for body in bodies
            for add in re.findall(r"git add ([^\n]+)", body)
        )
        assert "data/commodity" in staged_all, (
            "commodity-sentinel.yml must still stage data/commodity"
        )


class TestRegistryRootIsolation:
    """The existing one-entry cache must be bound to its actual registry path."""

    @pytest.fixture(autouse=True)
    def clear_registry_cache(self):
        from engine.neuralweb import reflexes
        reflexes.invalidate_cache()
        yield
        reflexes.invalidate_cache()

    @staticmethod
    def registry(root, name):
        directory = root / "config"
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / "reflexes.yml"
        path.write_text("reflexes:\n  " + name + ":\n    claim_family: reflex." + name + "\n")
        return path

    def test_second_root_does_not_receive_first_roots_rules(self, tmp_path):
        from engine.neuralweb.reflexes import load_registry
        a, b = tmp_path / "a", tmp_path / "b"
        self.registry(a, "rule_a"); self.registry(b, "rule_b")
        assert set(load_registry(a)) == {"rule_a"}
        assert set(load_registry(b)) == {"rule_b"}
        assert set(load_registry(a)) == {"rule_a"}

    def test_missing_second_registry_is_not_hidden_by_cache(self, tmp_path):
        from engine.neuralweb.reflexes import load_registry
        a, missing = tmp_path / "a", tmp_path / "missing"
        self.registry(a, "rule_a"); load_registry(a)
        with pytest.raises(FileNotFoundError):
            load_registry(missing)
        assert set(load_registry(a)) == {"rule_a"}

    def test_invalid_second_registry_is_not_hidden_by_cache(self, tmp_path):
        from engine.neuralweb.reflexes import load_registry
        a, b = tmp_path / "a", tmp_path / "b"
        self.registry(a, "rule_a")
        path = self.registry(b, "rule_b")
        path.write_text("reflexes:\n  rule_b:\n    claim_family: not_a_reflex\n")
        load_registry(a)
        with pytest.raises(ValueError, match="claim_family"):
            load_registry(b)
        assert set(load_registry(a)) == {"rule_a"}

    def test_force_refresh_still_refreshes_only_requested_root(self, tmp_path):
        from engine.neuralweb.reflexes import load_registry
        a, b = tmp_path / "a", tmp_path / "b"
        self.registry(a, "rule_a"); self.registry(b, "rule_b")
        load_registry(a)
        assert set(load_registry(b, force=True)) == {"rule_b"}
        assert set(load_registry(a)) == {"rule_a"}

    def test_same_root_preserves_existing_explicit_refresh_contract(self, tmp_path):
        from engine.neuralweb.reflexes import load_registry
        a = tmp_path / "a"; self.registry(a, "old_rule")
        load_registry(a); self.registry(a, "new_rule")
        assert set(load_registry(a)) == {"old_rule"}
        assert set(load_registry(a, force=True)) == {"new_rule"}

    def test_invalidate_clears_cache_identity_and_data(self, tmp_path):
        from engine.neuralweb.reflexes import load_registry, invalidate_cache
        a = tmp_path / "a"; self.registry(a, "old_rule")
        load_registry(a); self.registry(a, "new_rule"); invalidate_cache()
        assert set(load_registry(a)) == {"new_rule"}

    def test_relative_path_follows_current_root_not_previous_cwd(self, tmp_path, monkeypatch):
        from engine.neuralweb.reflexes import load_registry
        a, b = tmp_path / "a", tmp_path / "b"
        self.registry(a, "rule_a"); self.registry(b, "rule_b")
        monkeypatch.chdir(a); assert set(load_registry(Path("."))) == {"rule_a"}
        monkeypatch.chdir(b); assert set(load_registry(Path("."))) == {"rule_b"}

    def test_default_and_explicit_root_use_the_same_identity_rule(self, tmp_path, monkeypatch):
        from engine.neuralweb import reflexes
        a, b = tmp_path / "a", tmp_path / "b"
        pa = self.registry(a, "rule_a"); self.registry(b, "rule_b")
        resolver = reflexes._registry_path
        monkeypatch.setattr(reflexes, "_registry_path", lambda root=None: pa if root is None else resolver(root))
        assert set(reflexes.load_registry()) == {"rule_a"}
        assert set(reflexes.load_registry(b)) == {"rule_b"}
        assert set(reflexes.load_registry()) == {"rule_a"}

    def test_symlink_retarget_changes_registry_identity(self, tmp_path):
        from engine.neuralweb.reflexes import load_registry
        a, b = tmp_path / "a", tmp_path / "b"
        self.registry(a, "rule_a"); self.registry(b, "rule_b")
        alias = tmp_path / "alias"; alias.symlink_to(a, target_is_directory=True)
        assert set(load_registry(alias)) == {"rule_a"}
        alias.unlink(); alias.symlink_to(b, target_is_directory=True)
        assert set(load_registry(alias)) == {"rule_b"}

    def test_canonical_alias_reuses_same_cache_without_extra_file_read(self, tmp_path, monkeypatch):
        from engine.neuralweb import reflexes
        a = tmp_path / "a"; self.registry(a, "rule_a")
        alias = tmp_path / "alias"; alias.symlink_to(a, target_is_directory=True)
        first = reflexes.load_registry(a)
        with mock.patch.object(Path, "read_text", side_effect=AssertionError("unnecessary reread")):
            assert reflexes.load_registry(alias) == first

    def test_concurrent_distinct_roots_keep_their_own_rules(self, tmp_path):
        from concurrent.futures import ThreadPoolExecutor
        from engine.neuralweb.reflexes import load_registry
        roots = [tmp_path / ("root_" + str(i)) for i in range(4)]
        for i, root in enumerate(roots):
            self.registry(root, "rule_" + str(i))
        def read_one(i):
            return i, set(load_registry(roots[i]))
        schedule = [i % len(roots) for i in range(160)]
        with ThreadPoolExecutor(max_workers=4) as pool:
            for i, rules in pool.map(read_one, schedule):
                assert rules == {"rule_" + str(i)}
