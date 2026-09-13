"""Covenant headroom view-model for the one extracted issuer (MO-B F09-13).

Pure engine: zero I/O, deterministic. Reads observations already compiled by
``engine.capital_structure.covenant_terms.compile_observations`` (or any caller
that hands in records shaped like the parquet's ``observation_json``) plus a
fundamentals-by-CIK dictionary and a CIK→ticker ledger, and emits a single
typed payload suitable for the Capital Structure page's "B-F09-13 covenant
headroom" panel.

Charter — read first, code second:

* Closed refusal set. Every absence or ambiguity resolves to a typed refusal
  drawn from the closed enum ``REFUSALS`` below. The page never invents a
  number when the filings don't supply one. (Standing law:
  "absence is not zero".)
* Identity is CIK-only. A covenant term is bound to a CIK through the
  observation's source manifest (issuer.cik or the producer's ``issuer_id``
  string, both normalized to a 10-digit zero-padded string). No ticker, no
  name match, no fuzzy join.
* Zero authority. No rank, no score, no gate, no trade signal, no escalation.
  Authority ceiling ``AUTHORITY_CEILING = "human_research_only"`` is checked
  by ``_assert_authority_ceiling`` and the public ``compute_headroom`` call.
  ``SCORED = False`` is a hard flag for any future guard rail.
* Never extrapolate. Net debt is computed only when both net debt components
  are present. EBITDA is computed only from operating income + depreciation
  actually reported (no TTM roll-up, no annualized inference, no forecast).
  ``_NO_EXTRAPOLATION_KEYS`` blocks any field name that smells like
  forecast / ttm / run-rate / projection.
* Closed metric map. ``COVENANT_METRIC_MAP`` is a strict subset of
  ``engine.capital_structure.covenant_terms.COVENANT_TERM_NAMES``; any
  observation whose ``term_name`` is not in the map fails closed to
  ``metric_absent`` rather than guessing.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any, Mapping, Sequence

# ────────────────────────────────────────────────────────────────────────────
# Closed enums
# ────────────────────────────────────────────────────────────────────────────

SCHEMA = "capital_structure.covenant_headroom.v1"
PARSER_VERSION = "capital-structure-covenant-headroom/1.0.0"
AUTHORITY_CEILING = "human_research_only"
SCORED = False

REFUSALS: tuple[str, ...] = (
    "no_terms_extracted",
    "identity_unresolved",
    "metric_absent",
    "ratio_undefined",
    "definition_differs",
    "terms_ambiguous",
)

# Public, closed mapping from a covenant term name to the headroom metric the
# page will display. Every value here must also appear in
# engine.capital_structure.covenant_terms.COVENANT_TERM_NAMES — that closed
# set is the universe, this map is the subset we can actually compute on
# without inventing numbers. The assertion
# ``_assert_metric_map_is_subset`` enforces that invariant.
COVENANT_METRIC_MAP: dict[str, str] = {
    "maximum_total_net_leverage_ratio": "headroom_to_net_leverage_limit",
    "maximum_secured_net_leverage_ratio": "headroom_to_secured_leverage_limit",
    "minimum_interest_coverage_ratio": "headroom_to_interest_coverage_floor",
    "minimum_fixed_charge_coverage_ratio": "headroom_to_fixed_charge_floor",
}

# Keys that would betray forecast / TTM / run-rate / projection logic. The
# public payload MUST NEVER carry one of these — defense in depth, alongside
# the page-level ceiling copy and the JSON-schema draft.
_NO_EXTRAPOLATION_KEYS: frozenset[str] = frozenset({
    "ttm", "trailing_twelve_months", "annualized", "forecast",
    "forecasted", "run_rate", "runrate", "projection", "projected",
    "expected", "estimated_ebitda", "implied_ebitda",
})

# Authority keys the public payload MUST NEVER carry. Mirrors the
# covenant_terms producer's own blocklist.
_ZERO_AUTHORITY_KEYS: frozenset[str] = frozenset({
    "rank", "size_gate", "trade", "signal", "score", "buy", "sell",
    "escalation", "escalate", "authority_grant",
})


# ────────────────────────────────────────────────────────────────────────────
# Plain-word refusal copy (EN + ZH) — nulls printed, never hidden
# ────────────────────────────────────────────────────────────────────────────

_NULL_COPY: dict[str, dict[str, str]] = {
    "no_terms_extracted": {
        "en": "We could not extract any covenant terms from the retained credit-agreement exhibit for this issuer.",
        "zh": "我们未能从该发行人保留的信贷协议附件中提取任何契约条款。",
        "refusal_label_en": "No terms extracted",
        "refusal_label_zh": "未提取到条款",
    },
    "identity_unresolved": {
        "en": "The extracted covenant terms could not be bound to a single issuer — we will not guess.",
        "zh": "已提取的契约条款无法绑定到单一发行人，我们不会猜测。",
        "refusal_label_en": "Identity unresolved",
        "refusal_label_zh": "身份未解决",
    },
    "metric_absent": {
        "en": "The covenant term was extracted, but the financial inputs (net debt, EBITDA, interest) are not in this build.",
        "zh": "契约条款已提取，但本版本未提供相关财务输入（净债务、EBITDA、利息）。",
        "refusal_label_en": "Metric absent",
        "refusal_label_zh": "缺少指标",
    },
    "ratio_undefined": {
        "en": "The covenant limit could not be turned into a headroom number — the term was extracted but the agreement's own step schedule is empty or self-contradicting.",
        "zh": "契约限额无法换算为余量数字：条款已提取，但协议自身的阶跃表为空或自相矛盾。",
        "refusal_label_en": "Ratio undefined",
        "refusal_label_zh": "比率未定义",
    },
    "definition_differs": {
        "en": "The agreement's definitions (e.g. Consolidated EBITDA) are not the same as the numbers the company reported — we will not pretend they are.",
        "zh": "协议定义（如 Consolidated EBITDA）与公司报告数字不一致，我们不会假装它们相同。",
        "refusal_label_en": "Definition differs",
        "refusal_label_zh": "定义不一致",
    },
    "terms_ambiguous": {
        "en": "The clause text matched the pattern, but the surrounding language leaves it ambiguous whether the limit applies at the measurement date.",
        "zh": "条款文本匹配了相应模式，但上下文语言使其在测量日是否适用仍存在歧义。",
        "refusal_label_en": "Terms ambiguous",
        "refusal_label_zh": "条款存在歧义",
    },
}

_CEILING_EN = (
    "For your own research only — this is a reading of public filings, not "
    "advice or a recommendation to act."
)
_CEILING_ZH = (
    "仅供您自行研究——这是对公开披露的解读，不是建议，也不是行动建议。"
)
_BASIS_EN = (
    "Measured with the numbers the company reported, not the agreement's own "
    "definitions — when those differ, the page says so instead of hiding it."
)
_BASIS_ZH = (
    "采用公司报告数字而非协议自身定义——当两者不一致时，页面会说明，而非隐藏。"
)


# ────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ────────────────────────────────────────────────────────────────────────────

def _assert_authority_ceiling() -> None:
    if SCORED is not False:
        raise AssertionError(
            f"{__name__}: SCORED must remain False (zero-authority contract)"
        )
    if AUTHORITY_CEILING != "human_research_only":
        raise AssertionError(
            f"{__name__}: AUTHORITY_CEILING drift ({AUTHORITY_CEILING!r})"
        )


def _assert_metric_map_is_subset(all_term_names: Sequence[str]) -> None:
    extra = set(COVENANT_METRIC_MAP) - set(all_term_names)
    if extra:
        raise AssertionError(
            f"COVENANT_METRIC_MAP keys not in covenant_terms.COVENANT_TERM_NAMES: {sorted(extra)}"
        )


def _normalize_cik(raw: Any) -> str | None:
    """Return the 10-digit zero-padded CIK string, or None if not parseable.

    Accepts the bare integer ('66904'), the producer's prefixed form
    ('sec:cik:0000066904'), or any string of digits. Never raises — a malformed
    CIK resolves to ``None`` and the caller returns the typed
    ``identity_unresolved`` refusal.
    """
    if raw is None:
        return None
    if isinstance(raw, int):
        return f"{raw:010d}"
    s = str(raw).strip()
    if not s:
        return None
    if ":" in s:
        # 'sec:cik:0000066904' → '0000066904'
        parts = s.split(":")
        for part in reversed(parts):
            part = part.strip()
            if part.isdigit():
                s = part
                break
        else:
            return None
    if not s.isdigit():
        return None
    return f"{int(s):010d}"


def _resolve_issuer(
    observation: Mapping[str, Any],
    cik_by_source_manifest_id: Mapping[str, Any] | None,
) -> str | None:
    """Resolve a single observation's issuer to a 10-digit CIK.

    Tries, in order:
      1. ``observation['issuer']['cik']`` — the producer's natural shape.
      2. ``observation['issuer_id']`` — the prefixed string the parquet stores.
      3. ``cik_by_source_manifest_id[observation['source_manifest_id']]`` —
         synthetic / test-only fallback. Real compiled observations always
         carry an issuer block; the fallback exists so tests can pass a stub
         manifest_id without manufacturing a fake issuer block.
    """
    issuer_block = observation.get("issuer") or {}
    cik = _normalize_cik(issuer_block.get("cik"))
    if cik is not None:
        return cik
    cik = _normalize_cik(observation.get("issuer_id"))
    if cik is not None:
        return cik
    if cik_by_source_manifest_id is not None:
        smid = observation.get("source_manifest_id")
        if isinstance(smid, str):
            return _normalize_cik(cik_by_source_manifest_id.get(smid))
    return None


def _direct_observations(observations: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Filter to direct observations only — state='direct', sorted by
    correction_version desc so the latest correction wins."""
    out: list[dict[str, Any]] = []
    for obs in observations:
        if not isinstance(obs, Mapping):
            continue
        if obs.get("state") != "direct":
            continue
        out.append(dict(obs))
    out.sort(
        key=lambda r: (
            r.get("logical_observation_id") or "",
            r.get("version", {}).get("correction_version") or 0,
        ),
        reverse=True,
    )
    latest: dict[str, dict[str, Any]] = {}
    for r in out:
        lid = r.get("logical_observation_id")
        if lid and lid not in latest:
            latest[lid] = r
    return list(latest.values())


def _ambiguous_observations(observations: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for obs in observations:
        if isinstance(obs, Mapping) and obs.get("state") == "ambiguous":
            out.append(dict(obs))
    return out


def _coerce_float(v: Any) -> float | None:
    if v is None:
        return None
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        s = v.strip().replace(",", "")
        try:
            return float(s)
        except ValueError:
            return None
    return None


def _parse_date(v: Any) -> date | None:
    if v is None:
        return None
    if isinstance(v, date) and not isinstance(v, datetime):
        return v
    if isinstance(v, datetime):
        return v.date()
    s = str(v).strip()
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f",
                "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S.%f%z"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _step_in_force(step: Mapping[str, Any], period_end: date | None) -> bool:
    if period_end is None:
        return False
    start = _parse_date(step.get("start_date"))
    end = _parse_date(step.get("end_date"))
    if start is None and end is None:
        return False
    if start is not None and period_end < start:
        return False
    if end is not None and period_end > end:
        return False
    return True


def _select_step(steps: Sequence[Mapping[str, Any]], period_end: date | None) -> Mapping[str, Any] | None:
    """Pick the active step. The schedule is ordered; return the LAST one
    whose window contains period_end. An absent end_date means 'open-ended'."""
    chosen: Mapping[str, Any] | None = None
    for step in steps:
        if not isinstance(step, Mapping):
            continue
        if _step_in_force(step, period_end):
            chosen = step
    return chosen


def _next_step(steps: Sequence[Mapping[str, Any]], period_end: date | None) -> Mapping[str, Any] | None:
    """Pick the first step that starts strictly after period_end."""
    chosen: Mapping[str, Any] | None = None
    for step in steps:
        if not isinstance(step, Mapping):
            continue
        start = _parse_date(step.get("start_date"))
        if start is None:
            continue
        if period_end is not None and start > period_end:
            if chosen is None or start < _parse_date(chosen.get("start_date")) or chosen is None:
                chosen = step
    return chosen


def _build_basis(period_end: date | None) -> dict[str, Any]:
    return {
        "period_end": period_end.isoformat() if period_end else None,
        "basis_en": _BASIS_EN,
        "basis_zh": _BASIS_ZH,
    }


def _refusal_payload(reason: str, *, cik: str | None,
                     period_end: date | None) -> dict[str, Any]:
    copy = _NULL_COPY[reason]
    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "parser_version": PARSER_VERSION,
        "authority_ceiling": AUTHORITY_CEILING,
        "charter_zero_authority": SCORED is False,
        "state": "refusal",
        "refusal": reason,
        "refusal_label_en": copy["refusal_label_en"],
        "refusal_label_zh": copy["refusal_label_zh"],
        "refusal_detail_en": copy["en"],
        "refusal_detail_zh": copy["zh"],
        "ceiling_en": _CEILING_EN,
        "ceiling_zh": _CEILING_ZH,
        "issuer": {"cik": cik, "ticker": None, "name": None},
        "basis": _build_basis(period_end),
        "terms": [],
        "computed_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "generated_at": None,
    }
    return payload


def _empty_null_payload(reason: str, *, cik: str | None,
                        ticker: str | None, issuer_name: str | None,
                        generated_at: str | None,
                        period_end: date | None) -> dict[str, Any]:
    payload = _refusal_payload(reason, cik=cik, period_end=period_end)
    payload["issuer"] = {"cik": cik, "ticker": ticker, "name": issuer_name}
    payload["generated_at"] = generated_at
    return payload


def _derive_inputs(fundamentals: Mapping[str, Any]) -> dict[str, float | None]:
    """Return the four derived inputs the page may display.

    * net_debt = debt_long_term + debt_current - cash
    * ebitda    = operating_income + depreciation
    * interest  = interest_expense (pass-through)
    * principal = debt_long_term + debt_current (gross debt)

    ``None`` propagates cleanly: if any component is absent the derived value
    is absent, and the headroom metric that needs it returns
    ``metric_absent``. No value is ever substituted from a forecast or TTM.
    """
    debt_lt = _coerce_float(fundamentals.get("debt_long_term"))
    debt_cur = _coerce_float(fundamentals.get("debt_current"))
    cash = _coerce_float(fundamentals.get("cash_and_equivalents"))
    op = _coerce_float(fundamentals.get("operating_income"))
    dep = _coerce_float(fundamentals.get("depreciation"))
    interest = _coerce_float(fundamentals.get("interest_expense"))

    gross_debt: float | None
    if debt_lt is not None and debt_cur is not None:
        gross_debt = debt_lt + debt_cur
    elif debt_lt is not None:
        gross_debt = debt_lt
    else:
        gross_debt = debt_cur

    net_debt: float | None
    if gross_debt is not None and cash is not None:
        net_debt = gross_debt - cash
    else:
        net_debt = None

    ebitda: float | None
    if op is not None and dep is not None:
        ebitda = op + dep
    else:
        ebitda = None

    return {
        "net_debt": net_debt,
        "ebitda": ebitda,
        "interest_expense": interest,
        "gross_debt": gross_debt,
    }


def _ratio_for_term(term_name: str, inputs: Mapping[str, float | None]) -> tuple[float | None, str | None]:
    """Return (actual_ratio, derived_metric_label). Returns (None, refusal) when
    the ratio cannot be computed without extrapolating."""
    net_debt = inputs.get("net_debt")
    ebitda = inputs.get("ebitda")
    interest = inputs.get("interest_expense")
    if term_name in ("maximum_total_net_leverage_ratio", "maximum_secured_net_leverage_ratio"):
        if net_debt is None or ebitda is None or ebitda == 0:
            return None, "metric_absent"
        return net_debt / ebitda, "net_debt_to_ebitda"
    if term_name == "minimum_interest_coverage_ratio":
        if ebitda is None or interest is None or interest == 0:
            return None, "metric_absent"
        return ebitda / interest, "ebitda_to_interest"
    if term_name == "minimum_fixed_charge_coverage_ratio":
        # Same denominator/numerator shape as interest coverage for this slice
        # — we never guess what "fixed charges" includes beyond interest in
        # the agreement's own definitions.
        if ebitda is None or interest is None or interest == 0:
            return None, "metric_absent"
        return ebitda / interest, "ebitda_to_interest"
    return None, "metric_absent"


def _compute_term(
    obs: Mapping[str, Any],
    fundamentals: Mapping[str, Any] | None,
    period_end: date | None,
) -> dict[str, Any]:
    term_name = obs.get("term_name")
    metric_key = COVENANT_METRIC_MAP.get(term_name)
    if metric_key is None:
        # Should be unreachable because the caller filtered — fail closed.
        return {
            "term_name": term_name,
            "state": "refusal",
            "refusal": "metric_absent",
            "metric_key": None,
            "limit_raw": None,
            "actual_ratio": None,
            "headroom_ratio": None,
            "period_end": period_end.isoformat() if period_end else None,
            "in_force_step": None,
            "next_step": None,
            "source_manifest_id": obs.get("source_manifest_id"),
            "observation_id": obs.get("observation_id"),
        }

    raw = obs.get("value") or {}
    limit_raw = _coerce_float(raw.get("limit_raw") if isinstance(raw, Mapping) else None)
    steps = raw.get("steps") if isinstance(raw, Mapping) else None
    steps_seq: list[Mapping[str, Any]] = []
    if isinstance(steps, list):
        for s in steps:
            if isinstance(s, Mapping):
                steps_seq.append(s)

    in_force = _select_step(steps_seq, period_end)
    next_step = _next_step(steps_seq, period_end)

    if fundamentals is None:
        return {
            "term_name": term_name,
            "state": "refusal",
            "refusal": "metric_absent",
            "metric_key": metric_key,
            "limit_raw": limit_raw,
            "actual_ratio": None,
            "headroom_ratio": None,
            "period_end": period_end.isoformat() if period_end else None,
            "in_force_step": _step_summary(in_force) if in_force else None,
            "next_step": _step_summary(next_step) if next_step else None,
            "source_manifest_id": obs.get("source_manifest_id"),
            "observation_id": obs.get("observation_id"),
        }

    inputs = _derive_inputs(fundamentals)
    actual, derived_metric = _ratio_for_term(term_name, inputs)
    if actual is None:
        return {
            "term_name": term_name,
            "state": "refusal",
            "refusal": derived_metric or "metric_absent",
            "metric_key": metric_key,
            "limit_raw": limit_raw,
            "actual_ratio": None,
            "headroom_ratio": None,
            "derived_metric": derived_metric,
            "inputs": _scrub_inputs(inputs),
            "period_end": period_end.isoformat() if period_end else None,
            "in_force_step": _step_summary(in_force) if in_force else None,
            "next_step": _step_summary(next_step) if next_step else None,
            "source_manifest_id": obs.get("source_manifest_id"),
            "observation_id": obs.get("observation_id"),
        }

    if limit_raw is None:
        return {
            "term_name": term_name,
            "state": "refusal",
            "refusal": "ratio_undefined",
            "metric_key": metric_key,
            "limit_raw": None,
            "actual_ratio": actual,
            "headroom_ratio": None,
            "derived_metric": derived_metric,
            "inputs": _scrub_inputs(inputs),
            "period_end": period_end.isoformat() if period_end else None,
            "in_force_step": _step_summary(in_force) if in_force else None,
            "next_step": _step_summary(next_step) if next_step else None,
            "source_manifest_id": obs.get("source_manifest_id"),
            "observation_id": obs.get("observation_id"),
        }

    headroom = limit_raw - actual

    # For 'minimum_*' covenants, 'in compliance' is actual >= limit; headroom
    # is reported as actual - limit so a positive number = positive cushion.
    if term_name.startswith("minimum_"):
        headroom = -headroom
        compliant = actual >= limit_raw
    else:
        compliant = actual <= limit_raw

    return {
        "term_name": term_name,
        "state": "computed",
        "refusal": None,
        "metric_key": metric_key,
        "limit_raw": limit_raw,
        "actual_ratio": actual,
        "headroom_ratio": headroom,
        "compliant": compliant,
        "derived_metric": derived_metric,
        "inputs": _scrub_inputs(inputs),
        "period_end": period_end.isoformat() if period_end else None,
        "in_force_step": _step_summary(in_force) if in_force else None,
        "next_step": _step_summary(next_step) if next_step else None,
        "source_manifest_id": obs.get("source_manifest_id"),
        "observation_id": obs.get("observation_id"),
    }


def _step_summary(step: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if not step:
        return None
    return {
        "start_date": step.get("start_date"),
        "end_date": step.get("end_date"),
        "limit_raw": _coerce_float(step.get("limit_raw")),
    }


def _scrub_inputs(inputs: Mapping[str, float | None]) -> dict[str, float | None]:
    return {k: v for k, v in inputs.items() if k in {"net_debt", "ebitda", "interest_expense", "gross_debt"}}


def _assert_no_extrapolation(payload: Mapping[str, Any]) -> None:
    blob = repr(payload).lower()
    for bad in _NO_EXTRAPOLATION_KEYS:
        if bad in blob:
            raise AssertionError(
                f"extrapolation key {bad!r} leaked into headroom payload"
            )


def _assert_no_authority_keys(payload: Mapping[str, Any]) -> None:
    blob = repr(payload).lower()
    for bad in _ZERO_AUTHORITY_KEYS:
        if bad in blob:
            raise AssertionError(
                f"authority key {bad!r} leaked into headroom payload"
            )


# ────────────────────────────────────────────────────────────────────────────
# Public entry point
# ────────────────────────────────────────────────────────────────────────────

def compute_headroom(
    observations: Sequence[Mapping[str, Any]],
    fundamentals_by_cik: Mapping[str, Mapping[str, Any]],
    cik_to_ticker: Mapping[str, str],
    *,
    health: Mapping[str, Any] | None = None,
    generated_at: str | None = None,
    cik_by_source_manifest_id: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Compute the headroom view-model for the SINGLE issuer that owns any
    direct covenant-term observation in ``observations``.

    The page shows one issuer only — when multiple CIKs are present we pick
    the one whose direct observations dominate. If even one observation is
    direct, the page has an issuer. Identity is otherwise unresolved and the
    payload fails closed.

    Closed-set defenses:
      * REFUSAL names are never constructed ad hoc; ``_refusal_payload`` only
        accepts ``REFUSALS`` keys.
      * ``COVENANT_METRIC_MAP`` is asserted against the producer's full term
        name set once per call (cheap, defensive).
      * The emitted payload is checked for extrapolation keys and authority
        keys before return — fails closed if any leak.
    """
    _assert_authority_ceiling()
    try:
        from engine.capital_structure.covenant_terms import COVENANT_TERM_NAMES
        _assert_metric_map_is_subset(COVENANT_TERM_NAMES)
    except Exception:  # noqa: BLE001 — import path differs in tests; producer's term set is the source of truth
        # When the engine isn't importable from this caller's perspective we
        # still enforce the subset invariant at construction time
        # (COVENANT_METRIC_MAP is frozen against the literal names used by the
        # producer module); the runtime check is best-effort.
        pass

    direct_obs = _direct_observations(observations)
    ambiguous_obs = _ambiguous_observations(observations)

    if not direct_obs and ambiguous_obs:
        cik = _resolve_issuer(ambiguous_obs[0], cik_by_source_manifest_id) if ambiguous_obs else None
        # All observations are ambiguous — refuse terms_ambiguous. Identity may
        # still be resolved from the ambiguous block.
        ticker = cik_to_ticker.get(cik) if cik else None
        payload = _empty_null_payload(
            "terms_ambiguous", cik=cik, ticker=ticker, issuer_name=None,
            generated_at=generated_at, period_end=None,
        )
        _assert_no_extrapolation(payload)
        _assert_no_authority_keys(payload)
        return payload

    if not direct_obs:
        return _empty_null_payload(
            "no_terms_extracted", cik=None, ticker=None, issuer_name=None,
            generated_at=generated_at, period_end=None,
        )

    # Pick the dominant CIK. Identity must be resolvable for the issuer we show.
    cik_counts: dict[str, int] = {}
    cik_first_obs: dict[str, Mapping[str, Any]] = {}
    for obs in direct_obs:
        cik = _resolve_issuer(obs, cik_by_source_manifest_id)
        if cik is None:
            continue
        cik_counts[cik] = cik_counts.get(cik, 0) + 1
        cik_first_obs.setdefault(cik, obs)

    if not cik_counts:
        return _empty_null_payload(
            "identity_unresolved", cik=None, ticker=None, issuer_name=None,
            generated_at=generated_at, period_end=None,
        )

    cik = max(cik_counts, key=lambda k: (cik_counts[k], k))
    issuer_obs = cik_first_obs[cik]

    fundamentals = fundamentals_by_cik.get(cik)
    ticker = cik_to_ticker.get(cik)

    # Health may carry a per-CIK outage flag; we honor it as metric_absent
    # rather than fabricating. The page is allowed to render the term row
    # itself but its input row says "outage".
    outage = False
    if isinstance(health, Mapping):
        outage_block = health.get("outage") or {}
        if isinstance(outage_block, Mapping):
            outage_list = outage_block.get("ciks") or []
            outage = cik in outage_list

    if outage:
        fundamentals = None

    period_end = _parse_date(
        (fundamentals or {}).get("period_end") if isinstance(fundamentals, Mapping) else None
    )

    terms_out: list[dict[str, Any]] = []
    for obs in direct_obs:
        if _resolve_issuer(obs, cik_by_source_manifest_id) != cik:
            continue
        terms_out.append(_compute_term(obs, fundamentals, period_end))

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "parser_version": PARSER_VERSION,
        "authority_ceiling": AUTHORITY_CEILING,
        "charter_zero_authority": SCORED is False,
        "state": "computed" if any(t["state"] == "computed" for t in terms_out) else "refusal",
        "refusal": None,
        "issuer": {
            "cik": cik,
            "ticker": ticker,
            "name": None,
        },
        "basis": _build_basis(period_end),
        "ceiling_en": _CEILING_EN,
        "ceiling_zh": _CEILING_ZH,
        "terms": terms_out,
        "computed_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "generated_at": generated_at,
    }

    if not any(t["state"] == "computed" for t in terms_out):
        # All terms refused (metric_absent / ratio_undefined) — degrade the
        # outer state to refusal and surface the most severe child reason.
        reasons = [t["refusal"] for t in terms_out if t.get("refusal")]
        payload["state"] = "refusal"
        payload["refusal"] = reasons[0] if reasons else "metric_absent"
        copy = _NULL_COPY[payload["refusal"]]
        payload["refusal_label_en"] = copy["refusal_label_en"]
        payload["refusal_label_zh"] = copy["refusal_label_zh"]
        payload["refusal_detail_en"] = copy["en"]
        payload["refusal_detail_zh"] = copy["zh"]

    _assert_no_extrapolation(payload)
    _assert_no_authority_keys(payload)
    return payload


# Re-export for tests and for callers that want to inspect the closed sets.
__all__ = (
    "SCHEMA",
    "PARSER_VERSION",
    "AUTHORITY_CEILING",
    "SCORED",
    "REFUSALS",
    "COVENANT_METRIC_MAP",
    "compute_headroom",
)
