"""engine.neuralweb.theme_thesis — TIL W1 (PR-C) Theme Thesis Ledger.

Loads config/theme_thesis_registry.yml, evaluates machine-checkable falsifiers
against current artifacts, appends versioned records to
data/neuralweb/theme_thesis_ledger.jsonl (append-only; only on content-hash
change), and writes a site projection to site/neuralwebdata/theme_thesis.json.

Public API
----------
run_stage(root: Path) -> None
    Called by scripts/build_thematic_state.py optional-stage dispatcher.
    Never raises fatally. Always exits cleanly.

Schema:
    Ledger records  — neuralweb.theme_thesis.v1
    Site projection — neuralweb.theme_thesis.v1

Authority
---------
    is_context_only=True; may_rank=may_gate=may_size=may_escalate=False.
    Display/shadow tier only per TIL house law.

Falsifier states (mirroring falsifier_tripwires.py semantics)
-------------------------------
    ARMED        — check spec present; condition has NOT fired
    FIRED        — condition expression fired (latched; un-fire = thesis_id bump)
    DATA_MISSING — source artifact absent or field missing
    QUALITATIVE  — no machine-checkable spec; human review required
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import tempfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import yaml

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Schema / authority constants
# ---------------------------------------------------------------------------

SCHEMA = "neuralweb.theme_thesis.v1"

AUTHORITY_BLOCK: dict[str, Any] = {
    "is_context_only": True,
    "may_rank": False,
    "may_gate": False,
    "may_size": False,
    "may_escalate": False,
    "display_only": True,
    "not_a_signal": True,
    "tier": "shadow",
    "forbidden_uses": [
        "ranking",
        "sizing",
        "alert_escalation",
        "board_ordering",
        "mastermind_arming",
        "scored_path",
    ],
}

# ---------------------------------------------------------------------------
# Paths (relative to repo root)
# ---------------------------------------------------------------------------

_REGISTRY_PATH = "config/theme_thesis_registry.yml"
_FORESIGHT_PATH = "site/basketdata/foresight_cascade.json"
_FORESIGHT_HISTORY_PATH = "data/foresight/log.jsonl"
_THEME_STATE_PATH = "data/neuralweb/theme_state.json"

_LEDGER_OUT = "data/neuralweb/theme_thesis_ledger.jsonl"
_SITE_OUT = "site/neuralwebdata/theme_thesis.json"

# ---------------------------------------------------------------------------
# Falsifier state vocabulary
# ---------------------------------------------------------------------------

STATE_ARMED = "ARMED"
STATE_FIRED = "FIRED"
STATE_DATA_MISSING = "DATA_MISSING"
STATE_QUALITATIVE = "QUALITATIVE"


# ---------------------------------------------------------------------------
# Source artifact loaders (tolerant — missing → None)
# ---------------------------------------------------------------------------

def _load_json(root: Path, rel_path: str) -> dict | list | None:
    """Load a JSON artifact. Returns None on any failure."""
    p = root / rel_path
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        log.warning("could not read %s: %s", p, exc)
        return None


def _load_jsonl(root: Path, rel_path: str) -> list[dict]:
    """Load a JSONL artifact, dropping malformed/non-object rows."""
    path = root / rel_path
    if not path.exists():
        return []
    rows: list[dict] = []
    try:
        with path.open(encoding="utf-8") as fh:
            for lineno, raw in enumerate(fh, 1):
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    row = json.loads(raw)
                except json.JSONDecodeError as exc:
                    log.warning("could not read %s line %d: %s", path, lineno, exc)
                    continue
                if isinstance(row, dict):
                    rows.append(row)
    except Exception as exc:  # noqa: BLE001
        log.warning("could not read %s: %s", path, exc)
        return []
    return rows


def _parse_observation_date(value: Any) -> date | None:
    """Parse a YYYY-MM-DD observation date; never infer one from build time."""
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return date.fromisoformat(value.strip()[:10])
    except ValueError:
        return None


def _parse_observation_ts(value: Any, fallback: date, ordinal: int) -> tuple[datetime, int]:
    """Return a stable ordering key for same-date correction selection."""
    if isinstance(value, str) and value.strip():
        try:
            parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc), ordinal
        except ValueError:
            pass
    return datetime.combine(fallback, datetime.min.time(), tzinfo=timezone.utc), ordinal


def _strip_stage(value: Any) -> str:
    """Normalize 'PRECIPICE (text)' and comparable enum suffixes."""
    if not isinstance(value, str) or not value.strip():
        return "WATCH"
    return value.split("(", 1)[0].strip().upper()


def _canonical_foresight_history(
    rows: list[dict],
    theme_id: str,
    *,
    evaluation_as_of: str | None,
    window_d: int | None,
) -> tuple[list[dict], int]:
    """Return latest correction per distinct observation date, oldest first.

    The producer tape is the observation authority. Re-rendering a page does not
    create another print. Multiple rows for one ``asof`` are corrections; only
    the latest ``ts`` survives and the superseded count is disclosed.
    """
    evaluation_date = _parse_observation_date(evaluation_as_of)
    by_date: dict[date, tuple[tuple[int, datetime, int], dict]] = {}
    corrections_superseded = 0
    for ordinal, row in enumerate(rows):
        if row.get("theme") != theme_id:
            continue
        observed = _parse_observation_date(row.get("asof") or row.get("as_of"))
        if observed is None:
            continue
        if evaluation_date is not None and observed > evaluation_date:
            continue
        rank = (int(bool(row.get("_current_projection"))), *_parse_observation_ts(row.get("ts"), observed, ordinal))
        previous = by_date.get(observed)
        if previous is not None:
            corrections_superseded += 1
        if previous is None or rank > previous[0]:
            canonical = dict(row)
            canonical["asof"] = observed.isoformat()
            by_date[observed] = (rank, canonical)

    selected = [by_date[d][1] for d in sorted(by_date)]
    if evaluation_date is not None and window_d is not None:
        cutoff = evaluation_date - timedelta(days=max(0, int(window_d)))
        selected = [
            row for row in selected
            if (_parse_observation_date(row.get("asof")) or date.min) >= cutoff
        ]
    return selected, corrections_superseded


def _load_foresight_index(root: Path) -> dict[str, dict]:
    """Return {theme_id: theme_dict} from foresight_cascade.json, or {}."""
    data = _load_json(root, _FORESIGHT_PATH)
    if not isinstance(data, dict):
        return {}
    themes = data.get("themes", [])
    if not isinstance(themes, list):
        return {}
    return {t.get("theme", ""): t for t in themes if isinstance(t, dict) and t.get("theme")}


def _load_theme_state_index(root: Path) -> dict[str, dict]:
    """Return {theme_id: theme_dict} from theme_state.json, or {}."""
    data = _load_json(root, _THEME_STATE_PATH)
    if not isinstance(data, dict):
        return {}
    themes = data.get("themes", [])
    if not isinstance(themes, list):
        return {}
    return {t.get("theme_id", ""): t for t in themes if isinstance(t, dict) and t.get("theme_id")}


# ---------------------------------------------------------------------------
# Falsifier evaluator
# ---------------------------------------------------------------------------

def _eval_falsifier(
    f: dict,
    foresight: dict[str, dict],
    theme_state: dict[str, dict],
    theme_id: str,
    foresight_history: list[dict] | None = None,
    evaluation_as_of: str | None = None,
) -> dict:
    """Evaluate one falsifier spec. Returns a result dict with state + detail."""
    fid = f.get("id", "unknown")
    rule_en = f.get("rule_en", "")
    check = f.get("check")
    qualitative = bool(f.get("qualitative", False))

    if qualitative or check is None:
        return {
            "id": fid,
            "rule_en": rule_en,
            "state": STATE_QUALITATIVE,
            "fired": False,
            "detail": "no machine-checkable spec; human review required",
        }

    # Resolve source artifact
    source = check.get("source_artifact", "")
    field = check.get("field", "")
    op = check.get("op", "")
    threshold = check.get("threshold")
    kind = check.get("kind", "threshold")
    history = foresight_history or []
    window_d = check.get("window_d")
    if kind in {"consecutive_threshold", "stage_regression"} \
            and _parse_observation_date(evaluation_as_of) is None:
        return {
            "id": fid,
            "rule_en": rule_en,
            "state": STATE_DATA_MISSING,
            "fired": False,
            "reason_code": "OBSERVATION_CLOCK_MISSING",
            "detail": "history-sensitive check requires a dated producer snapshot",
        }

    # Choose artifact index
    if "foresight_cascade" in source:
        theme_dict = foresight.get(theme_id, {})
    elif "theme_state" in source:
        theme_dict = theme_state.get(theme_id, {})
    else:
        return {
            "id": fid,
            "rule_en": rule_en,
            "state": STATE_DATA_MISSING,
            "fired": False,
            "detail": f"unknown source artifact: {source!r}",
        }

    if not theme_dict:
        return {
            "id": fid,
            "rule_en": rule_en,
            "state": STATE_DATA_MISSING,
            "fired": False,
            "detail": f"theme {theme_id!r} absent from {source!r}",
        }

    if kind == "consecutive_threshold":
        needed = max(2, int(check.get("consecutive_prints", 2)))
        canonical, corrections = _canonical_foresight_history(
            [*history, {**theme_dict, "theme": theme_id, "asof": evaluation_as_of, "_current_projection": True}],
            theme_id,
            evaluation_as_of=evaluation_as_of,
            window_d=window_d,
        )
        if len(canonical) < needed:
            return {
                "id": fid,
                "rule_en": rule_en,
                "state": STATE_DATA_MISSING,
                "fired": False,
                "reason_code": "INSUFFICIENT_DISTINCT_HISTORY",
                "detail": (
                    f"requires {needed} distinct dated observations; "
                    f"found {len(canonical)} within window"
                ),
                "evidence": {
                    "source_artifact": _FORESIGHT_HISTORY_PATH,
                    "observations": [row.get("asof") for row in canonical],
                    "corrections_superseded": corrections,
                },
            }

        observations: list[dict[str, Any]] = []
        verdicts: list[bool] = []
        for row in canonical[-needed:]:
            value = row.get(field)
            verdict = _apply_op(value, op, threshold)
            if verdict is None:
                return {
                    "id": fid,
                    "rule_en": rule_en,
                    "state": STATE_DATA_MISSING,
                    "fired": False,
                    "reason_code": "HISTORY_FIELD_MISSING_OR_INCOMPATIBLE",
                    "detail": f"history field {field!r} missing or incompatible",
                    "evidence": {
                        "source_artifact": _FORESIGHT_HISTORY_PATH,
                        "observations": observations,
                        "corrections_superseded": corrections,
                    },
                }
            observations.append({
                "as_of": row.get("asof"),
                "value": value,
                "condition_met": verdict,
            })
            verdicts.append(verdict)
        fired = all(verdicts)
        return {
            "id": fid,
            "rule_en": rule_en,
            "state": STATE_FIRED if fired else STATE_ARMED,
            "fired": fired,
            "reason_code": (
                "CONSECUTIVE_THRESHOLD_MET" if fired
                else "CONSECUTIVE_THRESHOLD_NOT_MET"
            ),
            "detail": (
                f"{needed} distinct dated observations checked: "
                f"{field!r} {op} {threshold!r}"
            ),
            "evidence": {
                "source_artifact": _FORESIGHT_HISTORY_PATH,
                "observations": observations,
                "corrections_superseded": corrections,
            },
        }

    if kind == "stage_regression":
        raw_current_stage = theme_dict.get(field)
        if not isinstance(raw_current_stage, str) or not raw_current_stage.strip():
            return {
                "id": fid,
                "rule_en": rule_en,
                "state": STATE_DATA_MISSING,
                "fired": False,
                "reason_code": "CURRENT_STAGE_MISSING",
                "detail": f"current stage field {field!r} is null/missing in source",
            }
        current_stage = _strip_stage(raw_current_stage)
        targets = {_strip_stage(v) for v in (threshold or [])}
        if current_stage not in targets:
            return {
                "id": fid,
                "rule_en": rule_en,
                "state": STATE_ARMED,
                "fired": False,
                "reason_code": "TARGET_STAGE_NOT_PRESENT",
                "detail": f"current stage {current_stage!r} is not a regression target",
            }

        canonical, corrections = _canonical_foresight_history(
            history,
            theme_id,
            evaluation_as_of=evaluation_as_of,
            window_d=window_d,
        )
        evaluation_date = _parse_observation_date(evaluation_as_of)
        prior_rows = [
            row for row in canonical
            if evaluation_date is not None
            and (_parse_observation_date(row.get("asof")) or date.max) < evaluation_date
        ]
        if not prior_rows:
            return {
                "id": fid,
                "rule_en": rule_en,
                "state": STATE_DATA_MISSING,
                "fired": False,
                "reason_code": "PRIOR_DISTINCT_OBSERVATION_MISSING",
                "detail": "no prior distinct dated observation proves a transition",
                "evidence": {"corrections_superseded": corrections},
            }

        prior = None
        prior_stage = None
        for row in reversed(prior_rows):
            raw_prior_stage = row.get("stage")
            if not isinstance(raw_prior_stage, str) or not raw_prior_stage.strip():
                return {
                    "id": fid,
                    "rule_en": rule_en,
                    "state": STATE_DATA_MISSING,
                    "fired": False,
                    "reason_code": "PRIOR_STAGE_MISSING",
                    "detail": (
                        "historical predecessor stage is null/missing in source; "
                        "transition evidence cannot be inferred"
                    ),
                    "evidence": {
                        "prior_as_of": row.get("asof"),
                        "prior_stage": None,
                        "current_stage": current_stage,
                        "corrections_superseded": corrections,
                    },
                }
            normalized_prior_stage = _strip_stage(raw_prior_stage)
            if normalized_prior_stage != current_stage:
                prior = row
                prior_stage = normalized_prior_stage
                break
        if prior is None:
            return {
                "id": fid,
                "rule_en": rule_en,
                "state": STATE_DATA_MISSING,
                "fired": False,
                "reason_code": "PRIOR_DISTINCT_OBSERVATION_MISSING",
                "detail": "no predecessor to the current stage run was found",
                "evidence": {"corrections_superseded": corrections},
            }
        allowed_source = (
            check.get("watch_prior_stage_in")
            if current_stage == "WATCH" and check.get("watch_prior_stage_in") is not None
            else check.get("prior_stage_in")
        ) or []
        allowed_prior = {_strip_stage(v) for v in allowed_source}
        if allowed_prior and prior_stage not in allowed_prior:
            return {
                "id": fid,
                "rule_en": rule_en,
                "state": STATE_ARMED,
                "fired": False,
                "reason_code": "REQUIRED_PREDECESSOR_NOT_PRESENT",
                "detail": (
                    f"latest prior stage {prior_stage!r} at {prior.get('asof')} "
                    f"is not in {sorted(allowed_prior)!r}"
                ),
            }

        if current_stage == "WATCH":
            deterioration_field = check.get("watch_deterioration_field")
            if not deterioration_field:
                return {
                    "id": fid,
                    "rule_en": rule_en,
                    "state": STATE_DATA_MISSING,
                    "fired": False,
                    "reason_code": "WATCH_DETERIORATION_SPEC_MISSING",
                    "detail": "WATCH regression requires an independent deterioration field",
                }
            deterioration_value = theme_dict.get(deterioration_field)
            if not isinstance(deterioration_value, str) or not deterioration_value.strip():
                return {
                    "id": fid,
                    "rule_en": rule_en,
                    "state": STATE_DATA_MISSING,
                    "fired": False,
                    "reason_code": "WATCH_DETERIORATION_FIELD_MISSING",
                    "detail": (
                        f"independent deterioration field {deterioration_field!r} "
                        "is null/missing in source"
                    ),
                    "evidence": {
                        "prior_as_of": prior.get("asof"),
                        "prior_stage": prior_stage,
                        "current_stage": current_stage,
                        "deterioration_field": deterioration_field,
                        "deterioration_value": None,
                        "corrections_superseded": corrections,
                    },
                }
            allowed_values = {
                _strip_stage(v) for v in check.get("watch_deterioration_in", [])
            }
            if _strip_stage(deterioration_value) not in allowed_values:
                return {
                    "id": fid,
                    "rule_en": rule_en,
                    "state": STATE_ARMED,
                    "fired": False,
                    "reason_code": "WATCH_WITHOUT_INDEPENDENT_DETERIORATION",
                    "detail": (
                        "WATCH means scarcity was not confirmed; no separately "
                        "evidenced deterioration was present"
                    ),
                    "evidence": {
                        "prior_as_of": prior.get("asof"),
                        "prior_stage": prior_stage,
                        "current_stage": current_stage,
                        "deterioration_field": deterioration_field,
                        "deterioration_value": deterioration_value,
                        "corrections_superseded": corrections,
                    },
                }

        return {
            "id": fid,
            "rule_en": rule_en,
            "state": STATE_FIRED,
            "fired": True,
            "reason_code": "STAGE_REGRESSION_WITH_ECONOMIC_DETERIORATION",
            "detail": (
                f"distinct transition {prior_stage} ({prior.get('asof')}) "
                f"→ {current_stage} ({evaluation_as_of})"
            ),
            "evidence": {
                "prior_as_of": prior.get("asof"),
                "prior_stage": prior_stage,
                "current_as_of": evaluation_as_of,
                "current_stage": current_stage,
                "corrections_superseded": corrections,
            },
        }

    # Resolve field value (op-aware wildcard aggregation)
    value = _resolve_field(theme_dict, field, op)

    if value is None:
        return {
            "id": fid,
            "rule_en": rule_en,
            "state": STATE_DATA_MISSING,
            "fired": False,
            "detail": f"field {field!r} is null/missing in source",
        }

    # Evaluate condition
    fired = _apply_op(value, op, threshold)
    if fired is None:
        return {
            "id": fid,
            "rule_en": rule_en,
            "state": STATE_DATA_MISSING,
            "fired": False,
            "detail": f"unsupported op {op!r} or incompatible value type",
        }

    return {
        "id": fid,
        "rule_en": rule_en,
        "state": STATE_FIRED if fired else STATE_ARMED,
        "fired": fired,
        "detail": f"{kind} check: {field!r} {op} {threshold!r} → value={value!r}",
    }


def _resolve_field(theme_dict: dict, field: str, op: str | None = None) -> Any:
    """Resolve a dot-path or wildcard field from a theme dict.

    Supports:
      - simple key: "revision_breadth"
      - wildcard list scan: "basket_intel[*].crowding" → op-aware worst-case
        aggregation: an "any member breaches" semantic requires min() for
        lt/lte checks (fires if the LOWEST value breaches) and max() for
        gt/gte checks (fires if the HIGHEST value breaches). A fixed max()
        would silently never fire lt-checks unless the strongest member
        weakened — the exact silent-failure a falsifier must not have.

    Returns None if the field is absent or all values are None.
    """
    if "[*]." in field:
        # e.g. "basket_intel[*].crowding"
        parts = field.split("[*].")
        list_key = parts[0]
        sub_key = parts[1] if len(parts) > 1 else ""
        lst = theme_dict.get(list_key, [])
        if not isinstance(lst, list):
            return None
        values = [
            item.get(sub_key)
            for item in lst
            if isinstance(item, dict) and item.get(sub_key) is not None
        ]
        if not values:
            return None
        # Op-aware worst case: lt/lte → min (any value below), gt/gte → max.
        agg = min if op in ("lt", "lte") else max
        try:
            return agg(float(v) for v in values)
        except (TypeError, ValueError):
            return None
    else:
        # Simple field
        val = theme_dict.get(field)
        # Attempt numeric cast for comparison
        if val is None:
            return None
        return val


def _apply_op(value: Any, op: str, threshold: Any) -> bool | None:
    """Apply comparison operator. Returns bool or None on failure."""
    if op == "lt":
        try:
            return float(value) < float(threshold)
        except (TypeError, ValueError):
            return None
    elif op == "gt":
        try:
            return float(value) > float(threshold)
        except (TypeError, ValueError):
            return None
    elif op == "lte":
        try:
            return float(value) <= float(threshold)
        except (TypeError, ValueError):
            return None
    elif op == "gte":
        try:
            return float(value) >= float(threshold)
        except (TypeError, ValueError):
            return None
    elif op == "in":
        if not isinstance(threshold, list):
            return None
        # Stage field: check if value string starts with any threshold entry
        if isinstance(value, str):
            return any(value.startswith(t) for t in threshold)
        return value in threshold
    elif op == "eq":
        return value == threshold
    else:
        return None


# ---------------------------------------------------------------------------
# Registry loader and validator
# ---------------------------------------------------------------------------

def _load_registry(root: Path) -> list[dict]:
    """Load config/theme_thesis_registry.yml. Returns [] on failure."""
    p = root / _REGISTRY_PATH
    if not p.exists():
        log.warning("theme_thesis_registry.yml not found at %s", p)
        return []
    try:
        with p.open(encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        if not isinstance(data, dict):
            log.warning("theme_thesis_registry.yml did not parse as dict")
            return []
        theses = data.get("theses", [])
        if not isinstance(theses, list):
            return []
        return theses
    except Exception as exc:  # noqa: BLE001
        log.warning("could not load theme_thesis_registry.yml: %s", exc)
        return []


def _validate_thesis(t: dict) -> list[str]:
    """Return list of schema errors for one thesis dict."""
    errors: list[str] = []
    required = [
        "thesis_id", "theme_id", "status",
        "variant_perception_en", "variant_perception_zh",
        "mechanism_en", "mechanism_zh",
        "driver", "winner_classes", "loser_classes", "falsifiers",
    ]
    for field in required:
        if field not in t:
            errors.append(f"missing required field: {field!r}")

    # Class-level guard — no per-ticker thesis text fields
    forbidden_keys = {"ticker", "tickers", "stock", "symbol", "isin", "cusip"}
    for key in t:
        if key.lower() in forbidden_keys:
            errors.append(f"forbidden per-ticker field: {key!r} (R-TIL-1 fence)")

    # winner_classes and loser_classes must be lists of dicts with class+why
    for cls_field in ("winner_classes", "loser_classes"):
        lst = t.get(cls_field, [])
        if not isinstance(lst, list):
            errors.append(f"{cls_field!r} must be a list")
            continue
        for i, item in enumerate(lst):
            if not isinstance(item, dict):
                errors.append(f"{cls_field}[{i}] must be a dict")
            elif "class" not in item or "why" not in item:
                errors.append(f"{cls_field}[{i}] missing 'class' or 'why'")

    # falsifiers must be a list
    if "falsifiers" not in t:
        pass  # already caught above
    else:
        if not isinstance(t.get("falsifiers"), list):
            errors.append("'falsifiers' must be a list")

    return errors


# ---------------------------------------------------------------------------
# Content hash
# ---------------------------------------------------------------------------

def _content_hash(obj: dict) -> str:
    """Stable SHA-256 hash of JSON-serialised obj (sort_keys=True)."""
    text = json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Ledger read/append helpers
# ---------------------------------------------------------------------------

def _read_ledger(path: Path) -> list[dict]:
    """Read all JSONL lines from the ledger. Returns [] on missing/corrupt."""
    if not path.exists():
        return []
    rows = []
    with path.open(encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                log.warning("ledger line %d corrupt: %s", lineno, exc)
    return rows


def _last_record_per_theme(rows: list[dict]) -> dict[str, dict]:
    """Return the last ledger record keyed by thesis_id."""
    latest: dict[str, dict] = {}
    for row in rows:
        tid = row.get("thesis_id")
        if tid:
            latest[tid] = row
    return latest


def _atomic_write_jsonl_append(path: Path, new_rows: list[dict]) -> None:
    """Append new_rows to the JSONL ledger atomically (read + rewrite)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = _read_ledger(path)
    all_rows = existing + new_rows
    # Write to tmp then rename (atomic on POSIX)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".tmp_{path.name}_",
        suffix=".jsonl",
        delete=False,
    ) as tf:
        for row in all_rows:
            tf.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
        tmp = Path(tf.name)
    tmp.replace(path)


def _atomic_write_json(path: Path, payload: dict) -> None:
    """Atomically write JSON to path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=2, default=str)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".tmp_{path.name}_",
        suffix=".json",
        delete=False,
    ) as tf:
        tf.write(text)
        tmp = Path(tf.name)
    tmp.replace(path)


# ---------------------------------------------------------------------------
# Core compile function
# ---------------------------------------------------------------------------

def compile_thesis_record(
    thesis: dict,
    foresight: dict[str, dict],
    theme_state: dict[str, dict],
    as_of: str,
    prev_record: dict | None = None,
    foresight_history: list[dict] | None = None,
    evaluation_as_of: str | None = None,
) -> dict | None:
    """Compile a ledger record for one thesis.

    Returns the new record dict if content changed vs prev_record,
    or None if content hash is unchanged (idempotent).
    """
    theme_id = thesis.get("theme_id", "")
    thesis_id = thesis.get("thesis_id", "")

    # Evaluate all falsifiers
    falsifier_results = []
    falsifiers = thesis.get("falsifiers", [])
    for f in falsifiers:
        result = _eval_falsifier(
            f,
            foresight,
            theme_state,
            theme_id,
            foresight_history=foresight_history,
            evaluation_as_of=evaluation_as_of,
        )
        falsifier_results.append(result)

    # Summary counts
    n_fired = sum(1 for r in falsifier_results if r["state"] == STATE_FIRED)
    n_armed = sum(1 for r in falsifier_results if r["state"] == STATE_ARMED)
    n_data_missing = sum(1 for r in falsifier_results if r["state"] == STATE_DATA_MISSING)
    n_qualitative = sum(1 for r in falsifier_results if r["state"] == STATE_QUALITATIVE)

    # Build the content (without ledger-metadata fields for hashing)
    content = {
        "thesis_id": thesis_id,
        "theme_id": theme_id,
        "status": thesis.get("status", "active"),
        "variant_perception_en": thesis.get("variant_perception_en", ""),
        "variant_perception_zh": thesis.get("variant_perception_zh", ""),
        "mechanism_en": thesis.get("mechanism_en", ""),
        "mechanism_zh": thesis.get("mechanism_zh", ""),
        "driver": thesis.get("driver", {}),
        "winner_classes": thesis.get("winner_classes", []),
        "loser_classes": thesis.get("loser_classes", []),
        "evidence_refs": thesis.get("evidence_refs", []),
        "falsifiers": falsifier_results,
        "falsifier_summary": {
            "n_fired": n_fired,
            "n_armed": n_armed,
            "n_data_missing": n_data_missing,
            "n_qualitative": n_qualitative,
            "any_fired": n_fired > 0,
        },
    }

    new_hash = _content_hash(content)

    # Check if content changed vs previous record
    if prev_record is not None:
        prev_hash = prev_record.get("content_hash", "")
        if prev_hash == new_hash:
            return None  # No change — skip append

    # Build the full ledger record (includes metadata + provenance)
    prev_hash_ref = prev_record.get("content_hash") if prev_record else None
    record = {
        "schema": SCHEMA,
        "as_of": as_of,
        "thesis_id": thesis_id,
        "content_hash": new_hash,
        "prev_content_hash": prev_hash_ref,
        "authority": AUTHORITY_BLOCK,
        **content,
    }

    return record


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run_stage(root: Path) -> None:
    """Run the W1 theme thesis ledger build stage.

    Called by scripts/build_thematic_state.py.
    Never raises fatally. Always completes.
    """
    as_of = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
    stale_legs: list[str] = []

    # ── Load registry ─────────────────────────────────────────────────────
    theses = _load_registry(root)
    if not theses:
        log.warning("theme_thesis: no theses loaded from registry — skipping")
        stale_legs.append("registry absent or empty")
        _write_null_site(root, as_of, stale_legs)
        return

    # ── Load source artifacts ─────────────────────────────────────────────
    foresight = _load_foresight_index(root)
    foresight_payload = _load_json(root, _FORESIGHT_PATH)
    foresight_as_of = (
        (foresight_payload.get("asof") or foresight_payload.get("as_of"))
        if isinstance(foresight_payload, dict) else None
    )
    if not foresight:
        stale_legs.append(_FORESIGHT_PATH)

    foresight_history = _load_jsonl(root, _FORESIGHT_HISTORY_PATH)
    if not foresight_history:
        stale_legs.append(_FORESIGHT_HISTORY_PATH)

    theme_state_index = _load_theme_state_index(root)
    if not theme_state_index:
        stale_legs.append(_THEME_STATE_PATH)

    # ── Load existing ledger ──────────────────────────────────────────────
    ledger_path = root / _LEDGER_OUT
    existing_rows = _read_ledger(ledger_path)
    prev_by_thesis = _last_record_per_theme(existing_rows)

    # ── Compile records ───────────────────────────────────────────────────
    new_rows: list[dict] = []
    compiled_records: list[dict] = []  # latest record per thesis (for site)

    for thesis in theses:
        thesis_id = thesis.get("thesis_id", "")
        if not thesis_id:
            log.warning("theme_thesis: thesis missing thesis_id — skipped")
            continue

        # Validate schema
        errors = _validate_thesis(thesis)
        if errors:
            log.warning("theme_thesis: thesis %s has errors: %s", thesis_id, errors)
            stale_legs.append(f"schema_errors:{thesis_id}")
            continue

        prev = prev_by_thesis.get(thesis_id)

        try:
            record = compile_thesis_record(
                thesis=thesis,
                foresight=foresight,
                theme_state=theme_state_index,
                as_of=as_of,
                prev_record=prev,
                foresight_history=foresight_history,
                evaluation_as_of=foresight_as_of,
            )
        except Exception as exc:  # noqa: BLE001
            log.warning("theme_thesis: compile failed for %s: %s", thesis_id, exc)
            stale_legs.append(f"compile_error:{thesis_id}")
            record = None

        if record is not None:
            new_rows.append(record)
            compiled_records.append(record)
        else:
            # Content unchanged — use prev for site projection
            if prev:
                compiled_records.append(prev)

    # ── Append to ledger (append-only) ────────────────────────────────────
    if new_rows:
        try:
            _atomic_write_jsonl_append(ledger_path, new_rows)
            log.info("theme_thesis: appended %d records to ledger", len(new_rows))
        except Exception as exc:  # noqa: BLE001
            log.error("theme_thesis: ledger write failed: %s", exc)
            stale_legs.append(f"ledger_write_error: {exc}")
    else:
        log.info("theme_thesis: no content changes — ledger unchanged")

    # ── Write sidecar for ledger ──────────────────────────────────────────
    try:
        from engine.neuralweb.envelope import write_sidecar
        write_sidecar(ledger_path, artifact_id="theme-thesis-ledger")
    except Exception as exc:  # noqa: BLE001
        log.warning("theme_thesis: ledger sidecar write failed: %s", exc)

    # ── Build and write site projection ──────────────────────────────────
    # n_falsifier_fired counts FALSIFIERS fired (not theses) — must equal the
    # length of any fired-falsifier list a consumer derives (W5 review finding).
    n_fired = sum(
        int(r.get("falsifier_summary", {}).get("n_fired", 0))
        for r in compiled_records
    )
    n_theses_with_fired = sum(
        1 for r in compiled_records
        if r.get("falsifier_summary", {}).get("any_fired", False)
    )
    n_ok = len(compiled_records) - n_theses_with_fired

    site_payload: dict[str, Any] = {
        "schema": SCHEMA,
        "as_of": as_of,
        "generated_at": datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "authority": AUTHORITY_BLOCK,
        "n_theses": len(compiled_records),
        "n_falsifier_fired": n_fired,
        "n_theses_with_fired": n_theses_with_fired,
        "n_ok": n_ok,
        "stale_legs": stale_legs,
        "theses": compiled_records,
    }

    try:
        from engine.neuralweb.envelope import stamp
        site_payload = stamp(site_payload, artifact_id="site-theme-thesis")
    except Exception as exc:  # noqa: BLE001
        log.warning("theme_thesis: site envelope stamp failed: %s", exc)

    site_path = root / _SITE_OUT
    try:
        _atomic_write_json(site_path, site_payload)
        log.info("theme_thesis: wrote site projection to %s", site_path)
    except Exception as exc:  # noqa: BLE001
        log.error("theme_thesis: site write failed: %s", exc)

    print(
        f"[theme_thesis] theses={len(compiled_records)} new_ledger_rows={len(new_rows)} "
        f"falsifier_fired={n_fired} stale_legs={len(stale_legs)}",
        flush=True,
    )


def _write_null_site(root: Path, as_of: str, stale_legs: list[str]) -> None:
    """Write a minimal null-state site projection when registry is absent."""
    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "as_of": as_of,
        "generated_at": datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "authority": AUTHORITY_BLOCK,
        "n_theses": 0,
        "n_falsifier_fired": 0,
        "n_ok": 0,
        "stale_legs": stale_legs,
        "theses": [],
    }
    try:
        from engine.neuralweb.envelope import stamp
        payload = stamp(payload, artifact_id="site-theme-thesis")
    except Exception as exc:  # noqa: BLE001
        log.warning("theme_thesis null site: envelope stamp failed: %s", exc)

    site_path = root / _SITE_OUT
    try:
        _atomic_write_json(site_path, payload)
    except Exception as exc:  # noqa: BLE001
        log.warning("theme_thesis null site: write failed: %s", exc)
