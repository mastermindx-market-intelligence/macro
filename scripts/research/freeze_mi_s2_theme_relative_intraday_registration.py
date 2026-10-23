#!/usr/bin/env python3
"""Freeze the outcome-blind S2 prospective registration for theme-relative hourly RTH.

Reads only S1 proposal artifacts, git metadata, and incumbent session-policy facts.
Does not read intraday price stores, run collectors, or compute study statistics.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from engine.prophet_entry_policy import (  # noqa: E402
    SESSION_POLICY_ERA,
    _EARLY_CLOSE_DATES,
    _SUPPORTED_SESSION_YEARS,
)
from engine.trial_ledger import TrialLedger  # noqa: E402

S1_MD = (
    ROOT
    / "research/product_intelligence_local_delivery"
    / "S1_THEME_RELATIVE_INTRADAY_HYPOTHESIS_PROPOSAL_2026-10-06.md"
)
S1_JSON = (
    ROOT
    / "research/product_intelligence_local_delivery"
    / "S1_THEME_RELATIVE_INTRADAY_HYPOTHESIS_PROPOSAL_2026-10-06.json"
)
OUT_JSON = (
    ROOT
    / "research/product_intelligence_local_delivery"
    / "S2_THEME_RELATIVE_INTRADAY_PROSPECTIVE_REGISTRATION_2026-10-07.json"
)
OUT_MD = (
    ROOT
    / "research/product_intelligence_local_delivery"
    / "S2_THEME_RELATIVE_INTRADAY_PROSPECTIVE_REGISTRATION_2026-10-07.md"
)
TRIAL_LEDGER = ROOT / "data/trial_ledger.jsonl"

PROGRAM_ID = "MI-S2-TRI-HOURLY-RTH"
FAMILY = "mi_s2_theme_relative_intraday_hourly_rth_prospective"

OWNER_ACCEPTANCE_AT = "2026-10-07T02:46:58Z"
OWNER_ACCEPTANCE_URL = (
    "https://github.com/mastermindx-market-intelligence/macro/pull/8528#issuecomment-6029833181"
)
OWNER_ACCEPTANCE_COMMENT_ID = "6029833181"
S1_REVIEWED_HEAD = "cc56787650d4c791535c43845284647f3f6c3c3b"

# First 11:00 America/New_York decision clock strictly after owner acceptance.
FIRST_ELIGIBLE_DECISION_AT = "2026-10-07T15:00:00+00:00"
FIRST_ELIGIBLE_MARKET_SESSION = "2026-10-07"

FROZEN_PARAMETERS: dict[str, Any] = {
    "study_id": PROGRAM_ID,
    "study_label_en": "Theme-relative intraday descriptive strength on hourly RTH bars.",
    "study_label_zh": "主题相对日内描述性强度（常规交易时段小时线）。",
    "unit_of_independence": "decision_session",
    "bar_convention": {
        "timezone": "America/New_York",
        "vendor_aggregate_t_semantics": "bar_start",
        "vendor_aggregate_t_status": "ASSUMED",
        "vendor_aggregate_t_audit": (
            "S2 interval/alignment audit must confirm from authoritative documentation; "
            "until then registration fails closed on bar-start claims."
        ),
        "full_rth_bar_starts_et": ["10:00", "11:00", "12:00", "13:00", "14:00", "15:00"],
        "excluded_bar_starts_et": ["09:00", "before_09:00", "at_or_after_16:00"],
        "pre_decision_window": "single bar starting 10:00 ET (ends 11:00 ET decision time)",
        "forward_window_k": 5,
        "forward_bar_starts_et": ["11:00", "12:00", "13:00", "14:00", "15:00"],
    },
    "theme_benchmark": {
        "method": "equal_weight_live_pit_theme_members",
        "self_inclusion": "constituent_excluded_from_benchmark",
        "pit_reader": "engine.basket_membership_pit.members_asof(suite='baskets')",
        "pit_required": True,
    },
    "exposure": {
        "trailing_daily_sessions": 63,
        "estimation": "OLS beta vs theme benchmark on daily returns strictly before decision session",
        "application": "beta applied to hourly bar residuals",
    },
    "statistic": {
        "per_session": (
            "cross_sectional_spearman between cumulative pre-decision residual strength "
            "and same-session forward residual strength"
        ),
        "aggregate": "mean across matured valid sessions",
        "null_mean_rho": 0.0,
        "support_rule": "two_sided_95_one_sample_t_interval_excludes_zero",
        "rejection_rule": "same_interval_entirely_within_closed_band",
        "rejection_delta": 0.10,
        "inconclusive_rule": "any other mature result or immature sample",
    },
    "maturity": {
        "n_valid_decision_sessions": 120,
        "session_coverage_floor": 0.80,
        "excluded_sessions_do_not_count_as_rejection": True,
    },
    "data_treatment": {
        "missing_bars": "omit constituent cell",
        "zero_volume": "omit constituent cell",
        "zero_return_positive_volume": "retain observation",
        "stale_identical_close_guard": "pre_decision_only_three_or_more_consecutive",
        "forward_return_value_inspection": "forbidden_for_exclusions",
    },
    "session_policy_binding": {
        "owner": "engine.prophet_entry_policy",
        "supported_session_years": sorted(_SUPPORTED_SESSION_YEARS),
        "early_close_dates": sorted(d.isoformat() for d in _EARLY_CLOSE_DATES),
        "session_policy_era": SESSION_POLICY_ERA,
        "calendar_existence_owner": "lib.nyse_calendar.is_session",
    },
}

AUTHORITY = {
    "research_only": True,
    "can_rank": False,
    "can_gate": False,
    "can_size": False,
    "can_execute": False,
    "can_trade": False,
    "can_alert": False,
    "can_promote": False,
    "outcome_scan_before_registration": "forbidden",
}

NYSE_SOURCE_URL = "https://beta.nyse.com/trade/hours-calendars"
NYSE_SOURCE_NOTE = (
    "Core trading 09:30–16:00 ET; 2027 full holidays and single early close "
    "2027-11-26 verified against NYSE beta hours page at registration time."
)


def _canonical(value: object) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _git_blob_sha(path: Path) -> str:
    out = subprocess.run(
        ["git", "hash-object", str(path)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return out.stdout.strip()


def _base_pin() -> str:
    out = subprocess.run(
        ["git", "rev-parse", "origin/main"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return out.stdout.strip()


def build_registration(*, base_pin: str, frozen_at: str) -> dict[str, Any]:
    s1_md_blob = _git_blob_sha(S1_MD)
    s1_json_blob = _git_blob_sha(S1_JSON)
    params_sha = _sha256_bytes(_canonical(FROZEN_PARAMETERS).encode("utf-8"))
    reg: dict[str, Any] = {
        "schema": "mastermind.mi_s2_prospective_registration.v1",
        "program_id": PROGRAM_ID,
        "family": FAMILY,
        "status": "prospective_accrual_only",
        "frozen_at": frozen_at,
        "base_pin": base_pin,
        "owner_acceptance": {
            "disposition": "OWNER_ACCEPTED / S2_REGISTRATION_AUTHORIZED",
            "accepted_at": OWNER_ACCEPTANCE_AT,
            "github_comment_url": OWNER_ACCEPTANCE_URL,
            "github_comment_id": OWNER_ACCEPTANCE_COMMENT_ID,
            "reviewed_proposal_head": S1_REVIEWED_HEAD,
        },
        "s1_bindings": {
            "markdown_path": str(S1_MD.relative_to(ROOT)),
            "markdown_git_blob": s1_md_blob,
            "json_path": str(S1_JSON.relative_to(ROOT)),
            "json_git_blob": s1_json_blob,
        },
        "formation_boundary": {
            "rule_en": (
                "First formation decision_at strictly after owner acceptance timestamp; "
                "decision clock is 11:00 America/New_York (end of bar starting 10:00 ET)."
            ),
            "rule_zh": (
                "首次形成的 decision_at 必须严格晚于产品负责人接受时间；"
                "决策时刻为美国东部时间 11:00（10:00 起始小时棒的结束）。"
            ),
            "owner_acceptance_at": OWNER_ACCEPTANCE_AT,
            "first_eligible_decision_at": FIRST_ELIGIBLE_DECISION_AT,
            "first_eligible_market_session": FIRST_ELIGIBLE_MARKET_SESSION,
        },
        "frozen_parameters": FROZEN_PARAMETERS,
        "frozen_parameters_sha256": params_sha,
        "trial_accounting": {
            "owner": "engine.trial_ledger.TrialLedger.log_trial",
            "ledger_path": str(TRIAL_LEDGER.relative_to(ROOT)),
            "prospective_configurations": 1,
            "no_threshold_grid": True,
            "no_interim_outcome_reads": True,
        },
        "session_calendar_verification": {
            "source_url": NYSE_SOURCE_URL,
            "verified_on": "2026-10-07",
            "note": NYSE_SOURCE_NOTE,
            "supported_session_years": sorted(_SUPPORTED_SESSION_YEARS),
            "early_close_dates": sorted(d.isoformat() for d in _EARLY_CLOSE_DATES),
        },
        "authority": AUTHORITY,
        "outcome_blind_law": (
            "No forward descriptive scoring, Spearman computation, or outcome scan "
            "may run before this registration is merged."
        ),
    }
    reg["registration_sha256"] = _sha256_bytes(_canonical(reg).encode("utf-8"))
    return reg


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    path.write_text(text, encoding="utf-8")


def _write_md(reg: dict[str, Any]) -> None:
    lines = [
        "# S2 — Theme-relative intraday prospective registration (hourly RTH)",
        "",
        "**OUTCOME-BLIND / PROSPECTIVE / NO RESULT CLAIM**",
        "",
        f"**BASE_PIN:** `{reg['base_pin']}`",
        f"**Frozen at:** `{reg['frozen_at']}`",
        f"**Registration SHA-256:** `{reg['registration_sha256']}`",
        f"**Owner acceptance:** [{OWNER_ACCEPTANCE_URL}]({OWNER_ACCEPTANCE_URL}) "
        f"at `{OWNER_ACCEPTANCE_AT}`",
        "",
        "## Formation boundary",
        "",
        f"- First eligible `decision_at`: `{FIRST_ELIGIBLE_DECISION_AT}` "
        f"(session `{FIRST_ELIGIBLE_MARKET_SESSION}`)",
        "- English rule: " + reg["formation_boundary"]["rule_en"],
        "- 中文规则：" + reg["formation_boundary"]["rule_zh"],
        "",
        "## Frozen parameters (summary)",
        "",
        f"- Maturity **n = {FROZEN_PARAMETERS['maturity']['n_valid_decision_sessions']}** "
        f"valid decision sessions; rejection **δ = "
        f"{FROZEN_PARAMETERS['statistic']['rejection_delta']}**",
        f"- Vendor bar `t` semantics: **{FROZEN_PARAMETERS['bar_convention']['vendor_aggregate_t_status']}** "
        "(interval audit required before promotion)",
        f"- Session years: **{sorted(_SUPPORTED_SESSION_YEARS)}**; early closes: "
        f"**{sorted(d.isoformat() for d in _EARLY_CLOSE_DATES)}**",
        "",
        "## Authority",
        "",
        "Research-only. All `authority` flags are false. No rank, gate, size, capital, or trading authority.",
        "",
        "## S1 bindings",
        "",
        f"- `{reg['s1_bindings']['markdown_path']}` blob `{reg['s1_bindings']['markdown_git_blob']}`",
        f"- `{reg['s1_bindings']['json_path']}` blob `{reg['s1_bindings']['json_git_blob']}`",
        "",
        "## Calendar verification",
        "",
        f"- Source: {NYSE_SOURCE_URL}",
        f"- {NYSE_SOURCE_NOTE}",
        "",
    ]
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


def trial_config(reg: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": PROGRAM_ID,
        "family": FAMILY,
        "design": FROZEN_PARAMETERS["study_label_en"],
        "frozen_parameters_sha256": reg["frozen_parameters_sha256"],
        "registration_sha256": reg["registration_sha256"],
        "owner_acceptance_at": OWNER_ACCEPTANCE_AT,
        "first_eligible_decision_at": FIRST_ELIGIBLE_DECISION_AT,
        "maturity_n": FROZEN_PARAMETERS["maturity"]["n_valid_decision_sessions"],
        "rejection_delta": FROZEN_PARAMETERS["statistic"]["rejection_delta"],
        "s1_json_blob": reg["s1_bindings"]["json_git_blob"],
        "base_pin": reg["base_pin"],
        "registered_at": reg["frozen_at"],
    }


def freeze(*, register_trial: bool, ledger_path: Path | None = None) -> dict[str, Any]:
    frozen_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )
    base_pin = _base_pin()
    reg = build_registration(base_pin=base_pin, frozen_at=frozen_at)
    _write_json(OUT_JSON, reg)
    _write_md(reg)

    if register_trial:
        path = ledger_path or TRIAL_LEDGER
        ledger = TrialLedger(path=path, family=FAMILY)
        cfg = trial_config(reg)
        ledger.log_trial(
            cfg,
            info_cutoff=FIRST_ELIGIBLE_MARKET_SESSION,
            source=PROGRAM_ID,
            note=(
                "Prospective-only MI-S2 theme-relative hourly RTH registration. "
                "Historical intraday outcomes cannot enter before merge."
            ),
        )
        ledger.log_declared_budget(
            1,
            reason=(
                "one exact frozen hypothesis configuration; no threshold, horizon, "
                "or outcome grid"
            ),
        )

    print(f"base_pin={base_pin}")
    print(f"registration_sha256={reg['registration_sha256']}")
    print(f"frozen_parameters_sha256={reg['frozen_parameters_sha256']}")
    print(f"family={FAMILY}")
    print(f"first_eligible_decision_at={FIRST_ELIGIBLE_DECISION_AT}")
    return reg


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--register-trial",
        action="store_true",
        help="Append the single prospective trial to data/trial_ledger.jsonl.",
    )
    parser.add_argument(
        "--ledger-path",
        type=Path,
        default=None,
        help="Override ledger path (tests only).",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    freeze(register_trial=args.register_trial, ledger_path=args.ledger_path)
