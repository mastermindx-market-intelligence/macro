"""Episode-aware evidence and authority contract tests for international Risk Radar."""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from engine import risk_radar_intl_audit as audit


def _graded_row(asof: str, state: str, hit: bool, *, alert: bool | None = None) -> dict:
    is_alert = state in audit.ALERT_STATES if alert is None else alert
    if is_alert:
        outcome = "true_positive" if hit else "false_positive"
    elif state in ("watch", "caution"):
        outcome = "tp_watch" if hit else "tn_watch"
    else:
        outcome = "calm_dd" if hit else "calm_quiet"
    dd = -0.06 if hit else 0.0
    return {
        "asof": asof,
        "market": "cn",
        "state": state,
        "alert": is_alert,
        "dominant_scare": "synthetic",
        "graded": {
            "outcome": outcome,
            "any_dd5_within_h21": hit,
            "fwd_dd": {"h5": dd, "h10": dd, "h21": dd},
        },
    }


def _write_rows(tmp_path: Path, market: str, rows: list[dict]) -> Path:
    path = tmp_path / "data" / "risk_radar_intl" / f"{market}_forward_log.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n")
    return path


def test_documented_total_and_loud_floors_do_not_map_to_shared_n_and_hits(tmp_path: Path) -> None:
    """The adapter must name the preserved 30-loud legacy fence explicitly.

    Current code prechecks 30 total / 8 loud, then sends n=8 to a shared min_n=30
    gate. That is conservative, but its reason exposes an unexplained generic n rather
    than the real contract. The repaired scorecard must make both row and episode gates
    explicit while keeping authority false.
    """
    start = date(2026, 8, 1)
    rows = [
        _graded_row(
            (start + timedelta(days=i)).isoformat(),
            "risk-off" if i < 8 else "calm",
            hit=i < 8,
        )
        for i in range(30)
    ]
    _write_rows(tmp_path, "cn", rows)

    score = audit.scorecard("cn", root=str(tmp_path), log_governance=False)

    assert score["authority_contract"] == "risk_radar_intl.authority.v2"
    assert score["n_total_graded_rows"] == 30
    assert score["n_loud_rows"] == 8
    assert score["row_gate_granted"] is False
    assert score["episode_gate_granted"] is False
    assert score["can_force"] is False
    assert score["row_gate_reason"] == (
        "legacy-row-gate-refused: n_alert_rows=8 < legacy_min_alert_rows=30"
    )
    assert "legacy-row-gate-refused" in score["grant_reason"]


def _daily_rows(states_and_hits: list[tuple[str, bool]], *, start: date = date(2026, 1, 1)) -> list[dict]:
    return [
        _graded_row((start + timedelta(days=i)).isoformat(), state, hit)
        for i, (state, hit) in enumerate(states_and_hits)
    ]


def test_persistent_loud_rows_collapse_to_one_episode() -> None:
    from engine.risk_radar_intl_evidence import derive_evidence

    metrics = derive_evidence(_daily_rows([("risk-off", True)] * 10))

    assert metrics["n_loud_rows"] == 10
    assert metrics["n_loud_episodes"] == 1
    assert metrics["n_episode_hits"] == 1
    assert metrics["loud_episode_anchors"] == ["2026-01-01"]


def test_alternating_rows_do_not_rearm_before_21_quiet_observations() -> None:
    from engine.risk_radar_intl_evidence import derive_evidence

    sequence = []
    for _ in range(15):
        sequence.extend((("risk-off", False), ("calm", False)))
    metrics = derive_evidence(_daily_rows(sequence))

    assert metrics["n_loud_rows"] == 15
    assert metrics["n_loud_episodes"] == 1
    assert metrics["loud_episode_anchors"] == ["2026-01-01"]


def test_repeated_hits_in_one_episode_count_once_from_anchor() -> None:
    from engine.risk_radar_intl_evidence import derive_evidence

    metrics = derive_evidence(
        _daily_rows([
            ("risk-off", False),
            ("risk-off", True),
            ("elevated", True),
            ("risk-off", True),
        ])
    )

    assert metrics["n_row_hits"] == 3
    assert metrics["n_loud_episodes"] == 1
    assert metrics["n_episode_hits"] == 0
    assert metrics["episode_precision"] == 0.0


def test_twenty_one_quiet_rows_rearm_a_genuinely_separated_episode() -> None:
    from engine.risk_radar_intl_evidence import derive_evidence

    sequence = [("risk-off", True)] + [("calm", False)] * 21 + [("elevated", True)]
    metrics = derive_evidence(_daily_rows(sequence))

    assert metrics["n_loud_episodes"] == 2
    assert metrics["n_episode_hits"] == 2
    assert metrics["loud_episode_anchors"] == ["2026-01-01", "2026-01-23"]


def test_unmatured_anchor_is_reported_but_not_counted() -> None:
    from engine.risk_radar_intl_evidence import derive_evidence

    row = _graded_row("2026-09-03", "risk-off", True)
    row["graded"] = None
    metrics = derive_evidence([row])

    assert metrics["n_loud_rows"] == 0
    assert metrics["n_loud_episodes"] == 0
    assert metrics["n_unmatured_loud_episodes"] == 1
    assert metrics["unmatured_loud_episode_anchors"] == ["2026-09-03"]


def test_independent_windows_are_twenty_one_canonical_observations_apart() -> None:
    from engine.risk_radar_intl_evidence import derive_evidence

    metrics = derive_evidence(_daily_rows([("calm", False)] * 43))

    assert metrics["n_independent_episodes"] == 3
    assert metrics["independent_episode_anchors"] == [
        "2026-01-01",
        "2026-01-22",
        "2026-02-12",
    ]


def _episode_view(metrics: dict) -> dict:
    """Exclude the intentionally raw/file-order legacy compatibility inputs."""
    return {
        key: value
        for key, value in metrics.items()
        if not key.startswith("legacy_")
    }


def test_episode_replay_is_deterministic() -> None:
    from engine.risk_radar_intl_evidence import derive_evidence

    rows = _daily_rows(
        [("risk-off", True)] + [("calm", False)] * 21 + [("risk-off", False)]
    )

    forward = derive_evidence(rows)
    reversed_input = derive_evidence(list(reversed(rows)))

    assert _episode_view(forward) == _episode_view(reversed_input)
    assert forward["legacy_row_evidence_asof"] == "2026-01-23"
    assert reversed_input["legacy_row_evidence_asof"] == "2026-01-01"


AUTHORITY_NOW = datetime(2026, 9, 23, tzinfo=timezone.utc)


def _strong_authority_metrics(**overrides: object) -> dict:
    metrics = {
        "n_total_graded_rows": 100,
        "n_loud_rows": 40,
        "n_row_hits": 35,
        "row_base_rate_dd5_h21": 0.10,
        "row_evidence_asof": "2026-09-01",
        "n_independent_episodes": 40,
        "n_loud_episodes": 20,
        "n_episode_hits": 18,
        "episode_base_rate_upper_90": 0.15,
        "episode_evidence_asof": "2026-09-01",
    }
    metrics.update(overrides)
    return metrics


def test_authority_contract_grants_only_when_both_gates_clear() -> None:
    result = audit._evaluate_authority_contract(
        _strong_authority_metrics(), now=AUTHORITY_NOW
    )

    assert result["row_gate_granted"] is True
    assert result["episode_gate_granted"] is True
    assert result["can_force"] is True
    assert result["grant_reason"] == (
        "granted: legacy row gate and episode gate cleared"
    )


def test_authority_contract_preserves_legacy_thirty_loud_row_fence() -> None:
    result = audit._evaluate_authority_contract(
        _strong_authority_metrics(n_loud_rows=8, n_row_hits=8),
        now=AUTHORITY_NOW,
    )

    assert result["row_gate_granted"] is False
    assert result["can_force"] is False
    assert result["row_gate_reason"] == (
        "legacy-row-gate-refused: n_alert_rows=8 < legacy_min_alert_rows=30"
    )


def test_authority_contract_refuses_tiny_independent_episode_n() -> None:
    result = audit._evaluate_authority_contract(
        _strong_authority_metrics(n_independent_episodes=29),
        now=AUTHORITY_NOW,
    )

    assert result["row_gate_granted"] is True
    assert result["episode_gate_granted"] is False
    assert result["can_force"] is False
    assert result["episode_gate_reason"] == (
        "episode-gate-refused: n_independent_episodes=29 < min_independent_episodes=30"
    )


def test_authority_contract_refuses_stale_episode_evidence() -> None:
    result = audit._evaluate_authority_contract(
        _strong_authority_metrics(episode_evidence_asof="2026-01-01"),
        now=AUTHORITY_NOW,
    )

    assert result["row_gate_granted"] is True
    assert result["episode_gate_granted"] is False
    assert result["can_force"] is False
    assert "stale-evidence" in result["episode_gate_reason"]


def test_authority_contract_refuses_no_alerts() -> None:
    result = audit._evaluate_authority_contract(
        _strong_authority_metrics(
            n_loud_rows=0,
            n_row_hits=0,
            n_loud_episodes=0,
            n_episode_hits=0,
            episode_evidence_asof=None,
        ),
        now=AUTHORITY_NOW,
    )

    assert result["row_gate_granted"] is False
    assert result["episode_gate_granted"] is False
    assert result["can_force"] is False
    assert result["row_gate_reason"] == (
        "row-accrual-refused: legacy_n_alert_rows=0 < min_alert_rows=8"
    )


def test_zero_observed_base_keeps_positive_upper_bound() -> None:
    from engine.risk_radar_intl_evidence import derive_evidence

    metrics = derive_evidence(_daily_rows([("calm", False)] * 610))

    assert metrics["n_independent_episodes"] == 30
    assert metrics["episode_base_rate_dd5_h21"] == 0.0
    assert metrics["episode_base_rate_upper_90"] is not None
    assert 0.0 < metrics["episode_base_rate_upper_90"] < 0.10


def test_all_hits_cannot_bypass_independent_episode_floor() -> None:
    result = audit._evaluate_authority_contract(
        _strong_authority_metrics(
            n_independent_episodes=1,
            n_loud_episodes=20,
            n_episode_hits=20,
            episode_base_rate_upper_90=1.0,
        ),
        now=AUTHORITY_NOW,
    )

    assert result["episode_gate_granted"] is False
    assert result["can_force"] is False


def test_new_authority_never_grants_when_legacy_row_gate_refuses() -> None:
    for n_total in (29, 30, 100):
        for n_loud in (7, 8, 29, 30, 40):
            for row_hits in (0, 7, 8, min(30, n_loud)):
                if row_hits > n_loud:
                    continue
                for n_independent in (0, 29, 30, 40):
                    for n_loud_episodes in (0, 7, 8, 20):
                        for episode_hits in (0, 7, min(8, n_loud_episodes), min(18, n_loud_episodes)):
                            if episode_hits > n_loud_episodes:
                                continue
                            result = audit._evaluate_authority_contract(
                                _strong_authority_metrics(
                                    n_total_graded_rows=n_total,
                                    n_loud_rows=n_loud,
                                    n_row_hits=row_hits,
                                    n_independent_episodes=n_independent,
                                    n_loud_episodes=n_loud_episodes,
                                    n_episode_hits=episode_hits,
                                ),
                                now=AUTHORITY_NOW,
                            )
                            assert not result["can_force"] or result["row_gate_granted"]


def test_incomplete_grade_dicts_cannot_manufacture_authority(tmp_path: Path) -> None:
    from engine.risk_radar_intl_evidence import derive_evidence

    start = date(2024, 12, 1)
    rows: list[dict] = []
    offset = 0
    for _ in range(29):
        rows.append(
            _graded_row(
                (start + timedelta(days=offset)).isoformat(),
                "risk-off",
                True,
            )
        )
        offset += 1
        for _ in range(21):
            incomplete = _graded_row(
                (start + timedelta(days=offset)).isoformat(),
                "calm",
                False,
            )
            incomplete["graded"] = {}
            rows.append(incomplete)
            offset += 1

    incomplete_loud = _graded_row(
        (start + timedelta(days=offset)).isoformat(),
        "risk-off",
        False,
    )
    incomplete_loud["graded"] = {}
    rows.append(incomplete_loud)
    _write_rows(tmp_path, "cn", rows)

    metrics = derive_evidence(rows)
    authority = audit._evaluate_authority_contract(metrics, now=AUTHORITY_NOW)
    score = audit.scorecard("cn", root=str(tmp_path), log_governance=False)

    assert metrics["legacy_n_total_graded_rows"] == 29
    assert metrics["legacy_n_alert_rows"] == 29
    assert metrics["n_total_graded_rows"] == 29
    assert metrics["n_loud_rows"] == 29
    assert authority["row_gate_granted"] is False
    assert authority["episode_gate_granted"] is False
    assert authority["can_force"] is False
    assert score["n_graded"] == 29
    assert score["can_force"] is False



def test_nonempty_incomplete_grades_cannot_dilute_episode_base_into_authority(
    tmp_path: Path,
) -> None:
    """Rows lacking the binary authority outcome are not independent base trials.

    The raw legacy fence may still see the historical truthy grade payload, but
    the episode gate must not turn incomplete calm payloads into zero-hit base
    observations that manufacture lift.
    """
    from engine.risk_radar_intl_evidence import derive_evidence

    start = date(2024, 12, 1)
    rows: list[dict] = []
    offset = 0
    for _ in range(30):
        rows.append(
            _graded_row(
                (start + timedelta(days=offset)).isoformat(),
                "risk-off",
                True,
            )
        )
        offset += 1
        for _ in range(21):
            incomplete = _graded_row(
                (start + timedelta(days=offset)).isoformat(),
                "calm",
                False,
            )
            incomplete["graded"] = {"outcome": "calm_quiet"}
            rows.append(incomplete)
            offset += 1

    _write_rows(tmp_path, "cn", rows)
    metrics = derive_evidence(rows)
    authority = audit._evaluate_authority_contract(metrics, now=AUTHORITY_NOW)

    assert metrics["legacy_n_total_graded_rows"] == 660
    assert metrics["legacy_n_alert_rows"] == 30
    assert metrics["legacy_n_incomplete_authority_rows"] == 630
    assert metrics["n_total_graded_rows"] == 30
    assert metrics["n_loud_rows"] == 30
    assert metrics["n_independent_episodes"] == 30
    assert metrics["n_independent_episode_hits"] == 30
    assert metrics["n_loud_episodes"] == 30
    assert metrics["n_episode_hits"] == 30
    assert authority["row_gate_granted"] is False
    assert authority["row_gate_reason"] == (
        "legacy-row-gate-refused: incomplete-authority-outcomes=630"
    )
    assert authority["episode_gate_granted"] is False
    assert authority["can_force"] is False

def test_legacy_row_grant_is_revoked_when_episode_gate_is_weak() -> None:
    result = audit._evaluate_authority_contract(
        _strong_authority_metrics(
            n_independent_episodes=2,
            n_loud_episodes=1,
            n_episode_hits=1,
        ),
        now=AUTHORITY_NOW,
    )

    assert result["row_gate_granted"] is True
    assert result["episode_gate_granted"] is False
    assert result["can_force"] is False


def test_calendar_fallback_rearms_after_observed_quiet_and_42_days() -> None:
    from engine.risk_radar_intl_evidence import derive_evidence

    rows = [
        _graded_row("2026-01-01", "risk-off", True),
        _graded_row("2026-01-10", "calm", False),
        _graded_row("2026-02-12", "risk-off", False),
    ]
    metrics = derive_evidence(rows)

    assert metrics["n_loud_episodes"] == 2
    assert metrics["loud_episode_anchors"] == ["2026-01-01", "2026-02-12"]


def test_calendar_gap_without_observed_quiet_does_not_rearm() -> None:
    from engine.risk_radar_intl_evidence import derive_evidence

    rows = [
        _graded_row("2026-01-01", "risk-off", True),
        _graded_row("2026-03-01", "risk-off", False),
    ]
    metrics = derive_evidence(rows)

    assert metrics["n_loud_episodes"] == 1
    assert metrics["loud_episode_anchors"] == ["2026-01-01"]


def test_calendar_fallback_selects_independent_windows_in_sparse_log() -> None:
    from engine.risk_radar_intl_evidence import derive_evidence

    rows = [
        _graded_row("2026-01-01", "calm", False),
        _graded_row("2026-02-12", "calm", False),
    ]
    metrics = derive_evidence(rows)

    assert metrics["n_independent_episodes"] == 2
    assert metrics["independent_episode_anchors"] == ["2026-01-01", "2026-02-12"]


def test_current_cn_hk_ca_ledgers_replay_without_mutation() -> None:
    from engine.risk_radar_intl_evidence import derive_evidence

    repo_root = Path(__file__).resolve().parents[1]
    expected = {
        "cn": {
            "n_total_graded_rows": 16,
            "n_loud_rows": 5,
            "n_row_hits": 2,
            "n_independent_episodes": 2,
            "n_loud_episodes": 1,
            "n_episode_hits": 1,
            "n_unmatured_loud_episodes": 1,
            "independent_episode_anchors": ["2026-06-26", "2026-08-20"],
            "loud_episode_anchors": ["2026-07-10"],
            "unmatured_loud_episode_anchors": ["2026-09-03"],
        },
        "hk": {
            "n_total_graded_rows": 15,
            "n_loud_rows": 3,
            "n_row_hits": 0,
            "n_independent_episodes": 2,
            "n_loud_episodes": 1,
            "n_episode_hits": 0,
            "n_unmatured_loud_episodes": 0,
            "independent_episode_anchors": ["2026-06-26", "2026-08-20"],
            "loud_episode_anchors": ["2026-07-14"],
            "unmatured_loud_episode_anchors": [],
        },
        "ca": {
            "n_total_graded_rows": 27,
            "n_loud_rows": 0,
            "n_row_hits": 0,
            "n_independent_episodes": 2,
            "n_loud_episodes": 0,
            "n_episode_hits": 0,
            "n_unmatured_loud_episodes": 0,
            "independent_episode_anchors": ["2026-06-26", "2026-08-07"],
            "loud_episode_anchors": [],
            "unmatured_loud_episode_anchors": [],
        },
    }

    for market, expected_metrics in expected.items():
        path = repo_root / "data" / "risk_radar_intl" / f"{market}_forward_log.jsonl"
        before = hashlib.sha256(path.read_bytes()).hexdigest()
        rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
        first = derive_evidence(rows)
        second = derive_evidence(list(reversed(rows)))
        score = audit.scorecard(market, root=str(repo_root), log_governance=False)
        after = hashlib.sha256(path.read_bytes()).hexdigest()

        assert _episode_view(first) == _episode_view(second)
        last_graded_asof = [
            row["asof"] for row in rows if isinstance(row.get("graded"), dict)
        ][-1]
        assert first["legacy_row_evidence_asof"] == last_graded_asof
        for key, value in expected_metrics.items():
            assert first[key] == value, (market, key, first[key], value)
        assert score["can_force"] is False
        assert score["row_gate_granted"] is False
        assert score["episode_gate_granted"] is False
        assert before == after


def test_current_september_like_streak_is_one_unmatured_episode() -> None:
    from engine.risk_radar_intl_evidence import derive_evidence

    rows = []
    for index, asof in enumerate(
        (
            "2026-09-03",
            "2026-09-04",
            "2026-09-07",
            "2026-09-09",
            "2026-09-10",
            "2026-09-11",
            "2026-09-14",
            "2026-09-15",
            "2026-09-16",
            "2026-09-18",
            "2026-09-21",
            "2026-09-22",
            "2026-09-23",
        )
    ):
        row = _graded_row(asof, "risk-off" if index != 1 else "elevated", False)
        row["graded"] = None
        rows.append(row)

    metrics = derive_evidence(rows)

    assert metrics["n_loud_rows"] == 0
    assert metrics["n_loud_episodes"] == 0
    assert metrics["n_unmatured_loud_episodes"] == 1
    assert metrics["unmatured_loud_episode_anchors"] == ["2026-09-03"]


def test_invalid_and_duplicate_rows_cannot_inflate_evidence() -> None:
    from engine.risk_radar_intl_evidence import derive_evidence

    valid = _graded_row("2026-01-01", "calm", False)
    duplicate = _graded_row("2026-01-01", "risk-off", True)
    invalid_date = _graded_row("not-a-date", "risk-off", True)
    missing_date = _graded_row("2026-01-02", "risk-off", True)
    missing_date.pop("asof")

    metrics = derive_evidence([valid, duplicate, invalid_date, missing_date])

    assert metrics["n_total_graded_rows"] == 1
    assert metrics["n_loud_rows"] == 0
    assert metrics["n_independent_episodes"] == 1
    assert metrics["independent_episode_anchors"] == ["2026-01-01"]


def test_malformed_iso_suffix_is_not_canonical_evidence() -> None:
    from engine.risk_radar_intl_evidence import derive_evidence

    valid = _graded_row("2026-01-01", "calm", False)
    malformed = _graded_row("2026-02-12junk", "risk-off", True)

    metrics = derive_evidence([valid, malformed])

    assert metrics["legacy_n_total_graded_rows"] == 2
    assert metrics["n_total_graded_rows"] == 1
    assert metrics["n_loud_rows"] == 0
    assert metrics["n_independent_episodes"] == 1
    assert metrics["independent_episode_anchors"] == ["2026-01-01"]
    assert metrics["n_loud_episodes"] == 0


def test_malformed_suffix_authority_dates_fail_closed() -> None:
    malformed_legacy = audit._evaluate_authority_contract(
        _strong_authority_metrics(
            legacy_row_evidence_asof="2026-09-01junk",
        ),
        now=AUTHORITY_NOW,
    )
    malformed_canonical = audit._evaluate_authority_contract(
        _strong_authority_metrics(
            legacy_row_evidence_asof="2026-09-01",
            row_evidence_asof="2026-09-01junk",
            episode_evidence_asof="2026-09-01",
        ),
        now=AUTHORITY_NOW,
    )

    assert malformed_legacy["row_gate_granted"] is False
    assert malformed_legacy["can_force"] is False
    assert malformed_legacy["row_gate_reason"] == (
        "legacy-row-gate-refused: invalid-row-evidence-asof='2026-09-01junk'"
    )
    assert malformed_canonical["row_gate_granted"] is True
    assert malformed_canonical["episode_gate_granted"] is False
    assert malformed_canonical["can_force"] is False
    assert malformed_canonical["episode_gate_reason"] == (
        "episode-gate-refused: invalid-canonical-row-evidence-asof="
        "'2026-09-01junk'"
    )


def test_future_canonical_rows_cannot_hide_behind_past_episode_asof() -> None:
    result = audit._evaluate_authority_contract(
        _strong_authority_metrics(
            legacy_n_total_graded_rows=100,
            legacy_n_alert_rows=40,
            legacy_n_alert_hits=35,
            legacy_row_base_rate_dd5_h21=0.10,
            legacy_row_evidence_asof="2026-09-01",
            row_evidence_asof="2026-09-24",
            independent_evidence_asof="2026-09-24",
            loud_episode_evidence_asof="2026-09-01",
            episode_evidence_asof="2026-09-01",
        ),
        now=AUTHORITY_NOW,
    )

    assert result["row_gate_granted"] is True
    assert result["episode_gate_granted"] is False
    assert result["can_force"] is False
    assert result["episode_gate_reason"] == (
        "episode-gate-refused: future-canonical-row-evidence-asof=2026-09-24 "
        "> now=2026-09-23"
    )


def test_invalid_authority_evidence_dates_fail_closed() -> None:
    result = audit._evaluate_authority_contract(
        _strong_authority_metrics(
            row_evidence_asof="not-a-date",
            episode_evidence_asof="also-not-a-date",
        ),
        now=AUTHORITY_NOW,
    )

    assert result["row_gate_granted"] is False
    assert result["episode_gate_granted"] is False
    assert result["can_force"] is False
    assert result["row_gate_reason"] == (
        "legacy-row-gate-refused: invalid-row-evidence-asof='not-a-date'"
    )


def test_episode_loud_state_does_not_expand_legacy_alert_denominator() -> None:
    from engine.risk_radar_intl_evidence import derive_evidence

    row = _graded_row("2026-01-01", "risk-off", True, alert=False)
    metrics = derive_evidence([row])

    assert metrics["n_loud_rows"] == 0
    assert metrics["n_row_hits"] == 0
    assert metrics["n_loud_episodes"] == 1
    assert metrics["n_episode_hits"] == 1


def test_raw_legacy_metrics_fence_clean_episode_metrics() -> None:
    result = audit._evaluate_authority_contract(
        _strong_authority_metrics(
            legacy_n_total_graded_rows=100,
            legacy_n_alert_rows=8,
            legacy_n_alert_hits=8,
            legacy_row_base_rate_dd5_h21=0.80,
            legacy_row_evidence_asof="2026-09-01",
        ),
        now=AUTHORITY_NOW,
    )

    assert result["row_gate_granted"] is False
    assert result["episode_gate_granted"] is True
    assert result["can_force"] is False
    assert result["row_gate_reason"] == (
        "legacy-row-gate-refused: n_alert_rows=8 < legacy_min_alert_rows=30"
    )


def test_future_dated_evidence_fails_closed_for_both_gates() -> None:
    result = audit._evaluate_authority_contract(
        _strong_authority_metrics(
            row_evidence_asof="2026-09-24",
            episode_evidence_asof="2026-09-24",
            legacy_row_evidence_asof="2026-09-24",
        ),
        now=AUTHORITY_NOW,
    )

    assert result["row_gate_granted"] is False
    assert result["episode_gate_granted"] is False
    assert result["can_force"] is False
    assert result["row_gate_reason"] == (
        "legacy-row-gate-refused: future-row-evidence-asof=2026-09-24 "
        "> now=2026-09-23"
    )
    assert result["episode_gate_reason"] == (
        "episode-gate-refused: future-episode-evidence-asof=2026-09-24 "
        "> now=2026-09-23"
    )
