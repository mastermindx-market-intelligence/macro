"""Pure retrospective gap reading of the incumbent native divergence leg.

No source reads, new expectation rule, coverage inference, graph/member/security
qualification, publication or financial powers. A source hash proves consistency,
not authentication. The sparse ledger can witness a target; it cannot prove its
absence, failure, expiry, contradiction or an independent episode count.
"""
from __future__ import annotations

import copy
import datetime as dt
import re

from engine import foresight_divergence as owner
from engine.theme_graph import theme_state_production as production

SCHEMA = "gmi.theme_divergence_gap/v1"
SOURCE_PATH = "data/foresight/divergence_log.jsonl"


def unavailable(*, subject_id, effective_at, known_at, use_at, reason):
    return {"schema": SCHEMA, "status": "UNAVAILABLE", "reason_codes": [reason],
        "subject_id": subject_id, "query": {"effective_at": effective_at, "known_at": known_at},
        "use_at": use_at, "state_ref": None, "input_refs": {}, "source_observed_at": None,
        "owner_method": {"owner": "engine.foresight_divergence", "predicate": "catchup_observed",
            "expected_condition": "same native theme quadrant == confirmed",
            "lag_calendar_days": owner.CATCHUP_DAYS, "method_class": "PROVISIONAL_NATIVE_INSTRUMENT"},
        "flag": None, "targets": [], "window": None, "coverage": None, "source_purpose": None,
        "limits": {"causal_transmission": "NOT_ESTABLISHED", "calibrated_prediction": "NOT_ESTABLISHED",
            "historical_availability": "UNPROVEN", "current_eligibility": "NOT_QUALIFIED",
            "source_authentication": "NOT_ESTABLISHED_BY_HASH",
            "invalidators": "NOT_DECLARED_BY_NATIVE_OWNER",
            "episode_independence": "NOT_ESTABLISHED; observations include weekly heartbeats",
            "member_identity": "NATIVE_SYMBOL_SNAPSHOT_ONLY; no security/issuer qualification",
            "source_population": "SPARSE_OWNER_HISTORY; no daily completeness claim"},
        "public_display_allowed": False, "materialization_allowed": False,
        "authority_caps": copy.deepcopy(production.FLAGS)}


def _day(value):
    if type(value) is not str or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError("native observation date required")
    return dt.date.fromisoformat(value)


def _observation(record, *, cutoff, source_observed_at):
    row = record["value"]
    day = _day(row.get("asof"))
    recorded = production._instant(row.get("ts"))
    if recorded.date() < day or recorded > cutoff or recorded > source_observed_at:
        raise ValueError("native append clock unproven")
    if "recorded_at" in row and row["recorded_at"] != row["ts"]:
        raise ValueError("native recorded clock alias conflict")
    members = row.get("members")
    if (type(members) is not list or not members or any(type(m) is not str or not m for m in members)
            or len(members) != len(set(members))):
        raise ValueError("native member snapshot unavailable")
    counts = [row.get("n_narrative_legs_live"), row.get("n_money_legs_live")]
    if any(type(count) is not int or count < 1 for count in counts):
        raise ValueError("native live axes unavailable")
    # Exact native snapshots, not current config or a canonical identity join.
    return {"record_id": record["record_id"], "source_position": record["source_position"],
        "asof": row["asof"], "recorded_at": row["ts"], "row_type": row.get("row_type"),
        "quadrant": row.get("quadrant"), "members": copy.deepcopy(members),
        "members_sha256": production.canonical_sha256(members),
        "n_narrative_legs_live": counts[0], "n_money_legs_live": counts[1]}


def compose_divergence_gap(leg, *, subject_id, flag_asof, effective_at, known_at, use_at,
                           state_ref=None, input_refs=None):
    """Read the exact existing ThemeState leg, preserving its unqualified ceiling.

    The native flag key is (theme, asof); duplicate/conflicting history refuses.
    observed catch-up means the incumbent predicate is witnessed in retained
    owner rows. No-target remains insufficient coverage even after 60 days.
    """
    answer = unavailable(subject_id=subject_id, effective_at=effective_at, known_at=known_at,
                         use_at=use_at, reason="NATIVE_HISTORY_UNAVAILABLE")
    query = answer["query"]
    try:
        effective, flag_day = _day(effective_at), _day(flag_asof)
        cutoff, use = production._instant(known_at), production._instant(use_at)
        observed = production._instant(leg["observed_at"])
        if cutoff > use or observed > cutoff or flag_day > effective or effective > observed.date():
            raise ValueError("source/query/use chronology")
        if (not isinstance(subject_id, str) or not subject_id.startswith("theme:")
                or leg["source_ref"]["path"] != SOURCE_PATH
                or not re.fullmatch(r"[a-f0-9]{64}", leg["source_ref"]["sha256"] or "")
                or leg["scope"]["status"] != "EXACT_OWNER_SCOPE"
                or leg["scope"]["selectors"] != [subject_id.removeprefix("theme:")]):
            raise ValueError("native source/theme scope")
        production._validate_records(leg, name="divergence_log", query=query)
        production._validate_qualification(leg, subject_id=subject_id, query=query)
        if leg["conflicts"]:
            answer["reason_codes"] = ["NATIVE_HISTORY_CONFLICT"]
            return answer
        records = leg["records"]
        if any(r["native_key"] != subject_id.removeprefix("theme:") for r in records):
            raise ValueError("foreign native theme")
        flags = [r for r in records if r["value"].get("asof") == flag_asof
                 and r["value"].get("row_type") in (None, "observation")
                 and r["value"].get("quadrant") == "hidden-opportunity"]
        if len(flags) != 1:
            answer["reason_codes"] = ["EXACT_NATIVE_FLAG_UNAVAILABLE"]
            return answer
        flag = flags[0]
        if not flag["usable_at_query"]:
            raise ValueError("flag native clock use refused")
        initial = _observation(flag, cutoff=cutoff, source_observed_at=observed)
        targets, unproven_targets = [], 0
        for record in records:
            row = record["value"]
            # Do not let an unrelated malformed row acquire a financial meaning.
            if row.get("quadrant") != "confirmed":
                continue
            try:
                target_day = _day(row.get("asof"))
                if target_day > effective or not owner.catchup_observed(flag_asof, [row]):
                    continue
                if not record["usable_at_query"]:
                    raise ValueError("target native clock use refused")
                target = _observation(record, cutoff=cutoff, source_observed_at=observed)
                if production._instant(target["recorded_at"]) < production._instant(initial["recorded_at"]):
                    raise ValueError("target append precedes flag")
                target["cohort_change"] = {
                    "same_member_set": set(target["members"]) == set(initial["members"]),
                    "added_count": len(set(target["members"]) - set(initial["members"])),
                    "removed_count": len(set(initial["members"]) - set(target["members"])),
                    "narrative_leg_delta": target["n_narrative_legs_live"] - initial["n_narrative_legs_live"],
                    "money_leg_delta": target["n_money_legs_live"] - initial["n_money_legs_live"]}
                targets.append(target)
            except (ValueError, TypeError):
                unproven_targets += 1
        rights = leg["qualification"]["rights"]
        registry_sha = (rights.get("native_read") or {}).get("registry_sha256")
        if (rights["status"] != "UNAVAILABLE" or rights["purpose"] != "research_internal"
                or registry_sha is not None and (type(registry_sha) is not str
                    or not re.fullmatch(r"[a-f0-9]{64}", registry_sha))):
            raise ValueError("source purpose disposition")
        refs = input_refs or {"divergence_log": leg["source_ref"]}
        closed_refs = {}
        paths = {"divergence_log": SOURCE_PATH, "theme_crosswalk": "config/theme_crosswalk.yml",
                 "rights_registry": "config/theme_sources.yml"}
        for name in ("divergence_log", "theme_crosswalk", "rights_registry"):
            if name in refs:
                ref = refs[name]
                if (ref["path"] != paths[name] or ref["availability"] not in ("AVAILABLE", "UNAVAILABLE")
                        or ref["sha256"] is not None and not re.fullmatch(r"[a-f0-9]{64}", ref["sha256"])):
                    raise ValueError("source reference shape")
                if (name == "divergence_log" and ref["sha256"] != leg["source_ref"]["sha256"]
                        or name == "rights_registry" and ref["sha256"] != registry_sha):
                    raise ValueError("source reference binding")
                closed_refs[name] = {k: ref[k] for k in ("path", "sha256", "availability")}
        if state_ref is not None and (set(state_ref) != {"schema", "generation_id", "state_sha256"}
                or state_ref["schema"] != production.SCHEMA
                or state_ref["generation_id"] != production.GENERATION_PREFIX + state_ref["state_sha256"][:20]
                or not re.fullmatch(r"[a-f0-9]{64}", state_ref["state_sha256"])):
            raise ValueError("state reference shape")
        elapsed = (effective - flag_day).days
        answer.update(status="OBSERVED_CATCHUP" if targets else "INSUFFICIENT_COVERAGE",
            reason_codes=[] if targets else ["SPARSE_HISTORY_DOES_NOT_ESTABLISH_NON_CATCHUP"],
            state_ref=copy.deepcopy(state_ref),
            input_refs=closed_refs,
            source_observed_at=leg["observed_at"], flag=initial, targets=targets,
            window={"start_exclusive": flag_asof,
                "end_inclusive": (flag_day + dt.timedelta(days=owner.CATCHUP_DAYS)).isoformat(),
                "elapsed_calendar_days": elapsed, "owner_window_elapsed": elapsed >= owner.CATCHUP_DAYS},
            coverage={"retained_subject_records": len(records), "eligible_target_records": len(targets),
                "unproven_target_records": unproven_targets, "completeness": "UNPROVEN",
                "negative_inference_allowed": False},
            source_purpose={"purpose": "research_internal", "rights": {
                k: rights[k] for k in ("status", "family", "purpose", "null_reason")},
                "registry_sha256": registry_sha,
                "source_qualification": leg["qualification"]["status"], "public_grant": "NOT_ESTABLISHED"})
    except (KeyError, ValueError, TypeError):
        answer["reason_codes"] = ["NATIVE_HISTORY_BINDING_OR_CLOCK_UNPROVEN"]
    return answer
