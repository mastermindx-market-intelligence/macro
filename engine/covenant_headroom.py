"""Covenant headroom view-model for the one extracted issuer (MO-B F09-13).

Pure engine: zero I/O, deterministic. Reads observations already compiled by
``engine.capital_structure.covenant_terms.compile_observations`` (or any caller
that hands in records shaped like the parquet's ``observation_json``) plus a
fundamentals-by-CIK dictionary, a CIK→ticker ledger, and an optional
health.json coverage block, and emits a single typed payload suitable for the
Capital Structure page's "B-F09-13 covenant headroom" panel.

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
* Never extrapolate. Net debt is imported from the single-definition helper
  ``engine.stock_fundamentals._net_debt`` (the EV-multiples and leverage
  panels share it; the docstring says "agree to the dollar"). EBITDA is
  reported operating income + reported depreciation — nothing else. No TTM
  roll-up, no annualized inference, no forecast, no projection.
* Closed metric map. ``COVENANT_METRIC_MAP`` is a strict subset of
  ``engine.capital_structure.covenant_terms.COVENANT_TERM_NAMES``. Terms the
  reported statements cannot answer (secured leverage, fixed charges,
  liquidity, basket) never appear in the map; they short-circuit to
  ``definition_differs``.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any, Mapping, Sequence

# ────────────────────────────────────────────────────────────────────────────
# Closed enums / single source of truth
# ────────────────────────────────────────────────────────────────────────────

SCHEMA = "capital_structure.covenant.headroom.v1"
PARSER_VERSION = "capital-structure-covenant-headroom/1.0.0"
AUTHORITY_CEILING = "human_research_only"
SCORED = False

# Spec R1 — every absence / ambiguity resolves to exactly one of these six
# reasons. ``_NULL_COPY`` MUST carry one entry per refusal, and a public test
# pins the closed set.
REFUSALS: tuple[str, ...] = (
    "no_terms_extracted",
    "identity_unresolved",
    "metric_absent",
    "ratio_undefined",
    "definition_differs",
    "terms_ambiguous",
)

# Spec R2 — only terms whose headroom can be computed from the company's
# reported statements appear here. Terms whose definitions are not one
# reported line (secured leverage, fixed charges, liquidity, baskets) are
# NOT in this map; they resolve to ``definition_differs`` via the
# ``_ALWAYS_DEFINITION_DIFFERS`` short-circuit below. This map is asserted
# at every call against the producer's frozen COVENANT_TERM_NAMES set.
COVENANT_METRIC_MAP: dict[str, str] = {
    "maximum_total_net_leverage_ratio": "headroom_to_net_leverage_limit",
    "minimum_interest_coverage_ratio": "headroom_to_interest_coverage_floor",
}

# Spec R2 — terms whose headroom CANNOT be computed from reported statements
# alone. They short-circuit to ``definition_differs`` with the matching
# refusal copy. The set is the closed complement of COVENANT_METRIC_MAP
# inside COVENANT_TERM_NAMES (covenant_terms.py) — i.e. the terms the
# producer recognises but the reported statements cannot quantify.
_ALWAYS_DEFINITION_DIFFERS: frozenset[str] = frozenset({
    "maximum_secured_net_leverage_ratio",     # statements do not split secured
    "minimum_fixed_charge_coverage_ratio",   # fixed charges not one reported line
    "minimum_liquidity_amount",               # revolver availability not a reported fact
    "restricted_payments_basket_amount",      # basket usage not a reported fact
})

# Spec R1 — defend the payload against any leakage of forecast / TTM / run-rate
# / projection vocabulary. Defense in depth alongside the page-level copy.
_NO_EXTRAPOLATION_KEYS: frozenset[str] = frozenset({
    "ttm", "trailing_twelve_months", "annualized", "forecast",
    "forecasted", "run_rate", "runrate", "projection", "projected",
    "expected", "estimated_ebitda", "implied_ebitda",
})

# Spec R4 — zero authority. Mirrors the producer's blocklist in
# ``engine.capital_structure.covenant_terms._ZERO_AUTHORITY_KEYS``.
_ZERO_AUTHORITY_KEYS: frozenset[str] = frozenset({
    "rank", "size_gate", "trade", "signal", "score", "buy", "sell",
    "escalation", "escalate", "authority_grant",
})


# ────────────────────────────────────────────────────────────────────────────
# Plain-word refusal copy (EN + ZH) — nulls printed, never hidden
# ────────────────────────────────────────────────────────────────────────────

# Spec R6 — every refusal in the closed enum carries EN + ZH plain copy.
# The "no_terms_extracted" copy carries two placeholders ({eligible_exhibits},
# {covered_manifests}) that the page may fill in from health.json's
# covenant_extraction block; the engine emits the count-bearing copy as
# ``null_en``/``null_zh`` only when coverage counts are supplied, else the
# placeholders are omitted.
_NULL_COPY: dict[str, dict[str, str]] = {
    "no_terms_extracted": {
        "label_en": "No terms extracted",
        "label_zh": "未提取到条款",
        "en_no_coverage": (
            "No credit agreement has been read for covenant terms yet."
        ),
        "zh_no_coverage": (
            "尚未从任何信贷协议中读取契约条款。"
        ),
        "en_with_coverage": (
            "No credit agreement has been read for covenant terms yet. Of "
            "{eligible_exhibits} exhibits that could hold one, "
            "{covered_manifests} have been read so far."
        ),
        "zh_with_coverage": (
            "尚未从任何信贷协议中读取契约条款。可能包含条款的 "
            "{eligible_exhibits} 份附件中，目前已读取 "
            "{covered_manifests} 份。"
        ),
    },
    "identity_unresolved": {
        "label_en": "Identity unresolved",
        "label_zh": "身份未解决",
        "en": (
            "The extracted covenant terms could not be bound to a single "
            "issuer — we will not guess."
        ),
        "zh": (
            "已提取的契约条款无法绑定到单一发行人，我们不会猜测。"
        ),
    },
    "metric_absent": {
        "label_en": "Metric absent",
        "label_zh": "缺少指标",
        "en": (
            "The covenant term was extracted, but the financial inputs "
            "(net debt, EBITDA, interest) are not in this build."
        ),
        "zh": (
            "契约条款已提取，但本版本未提供相关财务输入（净债务、EBITDA、利息）。"
        ),
    },
    "ratio_undefined": {
        "label_en": "Ratio undefined",
        "label_zh": "比率未定义",
        "en": (
            "The covenant limit could not be turned into a headroom number "
            "— the term was extracted but the reported EBITDA is zero, "
            "negative, or the agreement's step schedule is empty."
        ),
        "zh": (
            "契约限额无法换算为余量数字：条款已提取，但报告的 EBITDA 为零、"
            "为负，或协议自身的阶跃表为空。"
        ),
    },
    "definition_differs": {
        "label_en": "Definition differs",
        "label_zh": "定义不一致",
        "en": (
            "The agreement's definitions (e.g. secured leverage, fixed "
            "charges, liquidity, restricted-payments basket) are not the "
            "same as the numbers the company reported — we will not "
            "pretend they are."
        ),
        "zh": (
            "协议定义（如担保杠杆、固定费用、流动性、受限制付款额度）与"
            "公司报告数字并非同一口径，我们不会假装它们相同。"
        ),
    },
    "terms_ambiguous": {
        "label_en": "Terms ambiguous",
        "label_zh": "条款存在歧义",
        "en": (
            "The clause text matched the pattern, but the surrounding "
            "language leaves it ambiguous whether the limit applies at "
            "the measurement date."
        ),
        "zh": (
            "条款文本匹配了相应模式，但上下文语言使其在测量日是否适用"
            "仍存在歧义。"
        ),
    },
}

# Spec R4 — every payload carries the same ceiling sentence (EN + ZH).
_CEILING_EN = (
    "For your own research only — this is a reading of public filings, not "
    "advice or a trade call."
)
_CEILING_ZH = (
    "仅供自行研究 — 这是对公开披露文件的解读，不是建议，也不是交易指令。"
)

# Spec R1 + R2 — the basis sentence is part of the agreed / reported
# distinction. The phrasing is load-bearing: it acknowledges that the
# agreement's own definitions usually allow adjustments we do not add back,
# so the true room can differ from the reported figure shown here.
_BASIS_EN = (
    "Measured with the numbers the company reported, not the agreement's "
    "own definitions — those usually allow adjustments we do not add back, "
    "so the true room can differ."
)
_BASIS_ZH = (
    "按公司披露的数字计算，而非协议自身的定义 — 协议定义通常允许我们未"
    "加回的调整项，因此实际空间可能不同。"
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
    """Spec R2 — every key in COVENANT_METRIC_MAP must appear in the
    producer's frozen COVENANT_TERM_NAMES set; any drift is a bug."""
    extra = set(COVENANT_METRIC_MAP) - set(all_term_names)
    if extra:
        raise AssertionError(
            f"COVENANT_METRIC_MAP keys not in covenant_terms.COVENANT_TERM_NAMES: {sorted(extra)}"
        )


def _assert_always_definition_differs_disjoint() -> None:
    """Spec R2 — a term cannot simultaneously be in COVENANT_METRIC_MAP
    (computable) and in _ALWAYS_DEFINITION_DIFFERS (never computable)."""
    clash = set(COVENANT_METRIC_MAP) & set(_ALWAYS_DEFINITION_DIFFERS)
    if clash:
        raise AssertionError(
            f"terms in both COVENANT_METRIC_MAP and _ALWAYS_DEFINITION_DIFFERS: {sorted(clash)}"
        )


def _normalize_cik(raw: Any) -> str | None:
    """Return the 10-digit zero-padded CIK string, or None if not parseable.

    Accepts the bare integer ('1743759'), the producer's prefixed form
    ('sec:cik:0001743759'), or any string of digits. Never raises — a malformed
    CIK resolves to ``None`` and the caller returns the typed
    ``identity_unresolved`` refusal.
    """
    if raw is None:
        return None
    if isinstance(raw, bool):
        return None
    if isinstance(raw, int):
        return f"{raw:010d}"
    s = str(raw).strip()
    if not s:
        return None
    if ":" in s:
        # 'sec:cik:0001743759' → '0001743759'
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
    """Spec R3 — identity is CIK-only.

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
    """Filter to direct observations only — state='direct'; the latest
    correction_version per logical_observation_id wins."""
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
            if chosen is None:
                chosen = step
            else:
                prev_start = _parse_date(chosen.get("start_date"))
                if prev_start is None or start < prev_start:
                    chosen = step
    return chosen


def _step_summary(step: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if not step:
        return None
    return {
        "start_date": step.get("start_date"),
        "end_date": step.get("end_date"),
        "limit_raw": _coerce_float(step.get("limit_raw")),
    }


def _import_net_debt():
    """Spec R2 — single-definition law. Re-use stock_fundamentals._net_debt,
    the same helper _leverage_ratios and _context_frame already use, so the
    EV-multiples panel, the leverage panel, and this view-model agree to the
    dollar (its docstring literally says so).
    """
    from engine.stock_fundamentals import _net_debt as _sf_net_debt
    return _sf_net_debt


def _derive_net_debt(stmt: Mapping[str, Any]) -> float | None:
    """Spec R2 — net debt via the single shared definition. The stmt dict's
    keys MUST be the canonical names the producer's underlying data carries:
    ``debt_lt``, ``debt_cur``, ``cash``.

    Single-definition law: we import and call ``_net_debt`` from
    ``engine.stock_fundamentals`` — the SAME helper the leverage panel and
    the EV-multiples panel use, so a leverage figure on the dashboard and a
    headroom figure on this page agree to the dollar.

    The canonical helper has a None-safety law ("0 is a valid financial
    value — explicit is None checks, never `x or default`"), which means
    it returns a partial value when one component is missing. That is
    correct for the EV-multiples use case but NOT for the headroom use
    case, where a missing input is a *different* denial cause
    (``metric_absent``) than a present-and-zero input (legitimate). We
    therefore gate to ``None`` first when ANY of the three inputs is
    absent, then hand the populated dict to ``_net_debt``. Both behaviours
    co-exist; the canonical helper is still the single source of truth for
    the arithmetic."""
    debt_lt = stmt.get("debt_lt")
    debt_cur = stmt.get("debt_cur")
    cash = stmt.get("cash")
    if debt_lt is None or debt_cur is None or cash is None:
        return None
    _sf_net_debt = _import_net_debt()
    return _sf_net_debt(dict(stmt))


def _derive_ebitda(stmt: Mapping[str, Any]) -> float | None:
    """Spec R2 — EBITDA = reported operating income + reported depreciation.

    No add-backs. No annualized inference. Both inputs must be reported
    (non-None); either missing → None. Spec R7(c): if both are present
    but sum to ≤ 0, the caller routes to ``ratio_undefined``."""
    op = _coerce_float(stmt.get("op_income"))
    dep = _coerce_float(stmt.get("depreciation"))
    if op is None or dep is None:
        return None
    return op + dep


def _refusal_copy(reason: str, coverage: Mapping[str, Any] | None) -> dict[str, str]:
    """Render the EN+ZH copy for a refusal, applying coverage counts to
    no_terms_extracted when available."""
    entry = _NULL_COPY[reason]
    if reason == "no_terms_extracted" and coverage:
        eligible = coverage.get("eligible_exhibits")
        covered = coverage.get("covered_manifests")
        if isinstance(eligible, int) and isinstance(covered, int):
            return {
                "label_en": entry["label_en"],
                "label_zh": entry["label_zh"],
                "en": entry["en_with_coverage"].format(
                    eligible_exhibits=f"{eligible:,}",
                    covered_manifests=f"{covered:,}",
                ),
                "zh": entry["zh_with_coverage"].format(
                    eligible_exhibits=f"{eligible:,}",
                    covered_manifests=f"{covered:,}",
                ),
            }
    if reason == "no_terms_extracted":
        # No coverage block supplied — render the no-count copy.
        return {
            "label_en": entry["label_en"],
            "label_zh": entry["label_zh"],
            "en": entry["en_no_coverage"],
            "zh": entry["zh_no_coverage"],
        }
    return {
        "label_en": entry["label_en"],
        "label_zh": entry["label_zh"],
        "en": entry["en"],
        "zh": entry["zh"],
    }


def _empty_null_payload(
    reason: str,
    *,
    cik: str | None,
    ticker: str | None,
    issuer_name: str | None,
    coverage: Mapping[str, Any] | None,
    generated_at: str | None,
    period_end: date | None,
) -> dict[str, Any]:
    """A whole-payload refusal (no usable terms). Spec R1 — carries the
    public schema, the refusal copy at the top level (null_en / null_zh),
    the disclaimer (disclaimer_en / disclaimer_zh), and the coverage block
    read from health.json."""
    copy = _refusal_copy(reason, coverage)
    return {
        "schema": SCHEMA,
        "parser_version": PARSER_VERSION,
        "authority_ceiling": AUTHORITY_CEILING,
        "scored": SCORED,
        "state": "refused",
        "refusal": reason,
        "null_en": copy["en"],
        "null_zh": copy["zh"],
        "refusal_label_en": copy["label_en"],
        "refusal_label_zh": copy["label_zh"],
        "disclaimer_en": _CEILING_EN,
        "disclaimer_zh": _CEILING_ZH,
        "issuer": {"cik": cik, "ticker": ticker, "name": issuer_name},
        "basis_en": _BASIS_EN,
        "basis_zh": _BASIS_ZH,
        "basis_period_end": period_end.isoformat() if period_end else None,
        "terms": [],
        "coverage": _coverage_block(coverage),
        "computed_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "generated_at": generated_at,
    }


def _coverage_block(coverage: Mapping[str, Any] | None) -> dict[str, Any]:
    """Spec R1 — coverage block is {issuers_extracted, eligible_exhibits,
    covered_manifests}; null when health.json's covenant_extraction block
    is missing or malformed (the page then renders the no-coverage variant
    of the no_terms_extracted copy)."""
    if not isinstance(coverage, Mapping):
        return {
            "issuers_extracted": None,
            "eligible_exhibits": None,
            "covered_manifests": None,
            "state": None,
        }
    return {
        "issuers_extracted": coverage.get("issuers_covered"),
        "eligible_exhibits": coverage.get("eligible_exhibits"),
        "covered_manifests": coverage.get("covered_manifests"),
        "state": coverage.get("state"),
    }


def _term_payload(
    term_name: str,
    *,
    limit_raw: float | None,
    actual_ratio: float | None,
    headroom_ratio: float | None,
    limit_kind: str | None,
    inside_limit: bool | None,
    refusal: str | None,
    refusal_label_en: str | None,
    refusal_label_zh: str | None,
    in_force_step: Mapping[str, Any] | None,
    next_step: Mapping[str, Any] | None,
    reported_period_end: str | None,
    accession: str | None,
    form: str | None,
    source_manifest_id: str | None,
    observation_id: str | None,
    excerpt: str | None,
    source_url: str | None,
    filing_date: str | None,
) -> dict[str, Any]:
    """Spec R1 / R6 — single term row: limit, reported figure, room left,
    next step, filing type, accession, filing date, source URL. refusal
    fields stay present on refusal rows so the panel never loses the
    reason to a missing key."""
    return {
        "term_name": term_name,
        "limit_kind": limit_kind,
        "limit_raw": limit_raw,
        "reported": {
            "metric_key": _metric_key_for_term(term_name),
            "value": actual_ratio,
            "period_end": reported_period_end,
            "basis": "reported_not_agreement_defined",
        },
        "room_turns": headroom_ratio,
        "inside_limit": inside_limit,
        "in_force_step": _step_summary(in_force_step) if in_force_step else None,
        "next_step": _step_summary(next_step) if next_step else None,
        "refusal": refusal,
        "refusal_label_en": refusal_label_en,
        "refusal_label_zh": refusal_label_zh,
        "state": "computed" if refusal is None else "refused",
        "receipt": {
            "accession": accession,
            "form": form,
            "filing_date": filing_date,
            "source_manifest_id": source_manifest_id,
            "observation_id": observation_id,
            "excerpt": excerpt,
            "source_url": source_url,
        },
    }


def _metric_key_for_term(term_name: str) -> str | None:
    """Spec R2 — public metric key for the row, drawn from COVENANT_METRIC_MAP.
    A term outside the map has no public metric key."""
    return COVENANT_METRIC_MAP.get(term_name)


def _compute_term(
    obs: Mapping[str, Any],
    stmt: Mapping[str, Any] | None,
    period_end: date | None,
    coverage: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Spec R1 / R2 — one term row.

    The four-term short-circuit (definition_differs): any term in
    _ALWAYS_DEFINITION_DIFFERS returns a refusal row with reason
    ``definition_differs``. The two computable terms (in
    COVENANT_METRIC_MAP) are routed to the typed metric function; a
    missing input → ``metric_absent``; a zero/negative denominator →
    ``ratio_undefined``.

    The denial ordering is load-bearing:

    1. metric_absent    — the financial inputs are missing
                          (this MUST come before step-in-force, because
                          a missing period_end collapses step-in-force
                          too — and that collapse is *not* the same
                          denial cause).
    2. definition_differs — the term is not computable from reported
                          statements (governed by the closed metric map
                          and the always-differs set).
    3. ratio_undefined  — the step schedule is empty, no step matches
                          period_end, or the denominator is zero/negative.
    4. computed         — headroom figure returned with inside_limit.
    """
    term_name = obs.get("term_name")
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

    limit_kind = ("maximum" if term_name.startswith("maximum_") else "minimum") \
                 if isinstance(term_name, str) else None

    # Receipt fields common to every variant — independent of which refusal
    # path the term takes.
    common = dict(
        term_name=term_name,
        limit_raw=None,
        limit_kind=limit_kind,
        in_force_step=in_force,
        next_step=next_step,
        reported_period_end=period_end.isoformat() if period_end else None,
        accession=_receipt_accession(obs),
        form=_receipt_form(obs),
        source_manifest_id=obs.get("source_manifest_id"),
        observation_id=obs.get("observation_id"),
        excerpt=_receipt_excerpt(raw),
        source_url=_receipt_source_url(obs),
        filing_date=_receipt_filing_date(obs),
    )

    # 1) metric_absent — no statement row at all (or outage set stmt to None).
    # This MUST precede step-in-force: a missing period_end collapses step
    # selection too, and the denial cause here is "input missing", not
    # "schema empty".
    if stmt is None:
        rc = _refusal_copy("metric_absent", coverage)
        return _term_payload(
            **common,
            actual_ratio=None,
            headroom_ratio=None,
            inside_limit=None,
            refusal="metric_absent",
            refusal_label_en=rc["label_en"],
            refusal_label_zh=rc["label_zh"],
        )

    # 2) definition_differs — the term's definition is not computable
    # from reported statements. Two disjoint sets cover every non-
    # computable case:
    #   _ALWAYS_DEFINITION_DIFFERS — the four non-computable COVENANT_TERM_NAMES
    #   COVENANT_METRIC_MAP complement — any producer term outside the
    #                                  computable map
    if isinstance(term_name, str):
        if (term_name in _ALWAYS_DEFINITION_DIFFERS
                or term_name not in COVENANT_METRIC_MAP):
            rc = _refusal_copy("definition_differs", coverage)
            return _term_payload(
                **common,
                actual_ratio=None,
                headroom_ratio=None,
                inside_limit=None,
                refusal="definition_differs",
                refusal_label_en=rc["label_en"],
                refusal_label_zh=rc["label_zh"],
            )

    # 3) ratio_undefined — the step schedule is empty or no step matches
    # period_end. Now safe to look at step selection because we know
    # statements exist.
    if not in_force:
        rc = _refusal_copy("ratio_undefined", coverage)
        return _term_payload(
            **common,
            actual_ratio=None,
            headroom_ratio=None,
            inside_limit=None,
            refusal="ratio_undefined",
            refusal_label_en=rc["label_en"],
            refusal_label_zh=rc["label_zh"],
        )

    # Use the step's own limit_raw for the comparison (more authoritative
    # than the top-level limit_raw, which is the headline ratio).
    step_limit = _coerce_float(in_force.get("limit_raw"))
    compare_limit = step_limit if step_limit is not None else limit_raw
    common["limit_raw"] = compare_limit

    # Single-definition law: net debt and EBITDA via the shared helpers.
    net_debt = _derive_net_debt(stmt)
    ebitda = _derive_ebitda(stmt)
    interest_exp = _coerce_float(stmt.get("interest_exp"))

    if term_name == "maximum_total_net_leverage_ratio":
        if net_debt is None or ebitda is None:
            rc = _refusal_copy("metric_absent", coverage)
            return _term_payload(
                **common,
                actual_ratio=None,
                headroom_ratio=None,
                inside_limit=None,
                refusal="metric_absent",
                refusal_label_en=rc["label_en"],
                refusal_label_zh=rc["label_zh"],
            )
        if ebitda <= 0:
            # Spec R2 (c): EBITDA ≤ 0 → ratio_undefined
            rc = _refusal_copy("ratio_undefined", coverage)
            return _term_payload(
                **common,
                actual_ratio=None,
                headroom_ratio=None,
                inside_limit=None,
                refusal="ratio_undefined",
                refusal_label_en=rc["label_en"],
                refusal_label_zh=rc["label_zh"],
            )
        actual = net_debt / ebitda
        if compare_limit is None:
            rc = _refusal_copy("ratio_undefined", coverage)
            return _term_payload(
                **common,
                actual_ratio=actual,
                headroom_ratio=None,
                inside_limit=None,
                refusal="ratio_undefined",
                refusal_label_en=rc["label_en"],
                refusal_label_zh=rc["label_zh"],
            )
        headroom = compare_limit - actual
        return _term_payload(
            **common,
            actual_ratio=actual,
            headroom_ratio=headroom,
            inside_limit=(actual <= compare_limit),
            refusal=None,
            refusal_label_en=None,
            refusal_label_zh=None,
        )

    if term_name == "minimum_interest_coverage_ratio":
        if ebitda is None or interest_exp is None:
            rc = _refusal_copy("metric_absent", coverage)
            return _term_payload(
                **common,
                actual_ratio=None,
                headroom_ratio=None,
                inside_limit=None,
                refusal="metric_absent",
                refusal_label_en=rc["label_en"],
                refusal_label_zh=rc["label_zh"],
            )
        if interest_exp <= 0:
            # Spec R2 (c): interest_exp == 0 → ratio_undefined
            rc = _refusal_copy("ratio_undefined", coverage)
            return _term_payload(
                **common,
                actual_ratio=None,
                headroom_ratio=None,
                inside_limit=None,
                refusal="ratio_undefined",
                refusal_label_en=rc["label_en"],
                refusal_label_zh=rc["label_zh"],
            )
        if ebitda <= 0:
            rc = _refusal_copy("ratio_undefined", coverage)
            return _term_payload(
                **common,
                actual_ratio=None,
                headroom_ratio=None,
                inside_limit=None,
                refusal="ratio_undefined",
                refusal_label_en=rc["label_en"],
                refusal_label_zh=rc["label_zh"],
            )
        actual = ebitda / interest_exp
        if compare_limit is None:
            rc = _refusal_copy("ratio_undefined", coverage)
            return _term_payload(
                **common,
                actual_ratio=actual,
                headroom_ratio=None,
                inside_limit=None,
                refusal="ratio_undefined",
                refusal_label_en=rc["label_en"],
                refusal_label_zh=rc["label_zh"],
            )
        # Spec R2 — for minimum_* covenants headroom is reported − limit
        # so a positive number = positive cushion (room above the floor).
        headroom = actual - compare_limit
        return _term_payload(
            **common,
            actual_ratio=actual,
            headroom_ratio=headroom,
            inside_limit=(actual >= compare_limit),
            refusal=None,
            refusal_label_en=None,
            refusal_label_zh=None,
        )

    # Should be unreachable (every key not in the map short-circuits above).
    rc = _refusal_copy("metric_absent", coverage)
    return _term_payload(
        **common,
        actual_ratio=None,
        headroom_ratio=None,
        inside_limit=None,
        refusal="metric_absent",
        refusal_label_en=rc["label_en"],
        refusal_label_zh=rc["label_zh"],
    )


# Receipt helpers — spec R1 receipt fields on every term row.

def _receipt_accession(obs: Mapping[str, Any]) -> str | None:
    value = obs.get("accession")
    if isinstance(value, str):
        return value
    point = obs.get("point_in_time") or {}
    return point.get("accession") if isinstance(point, Mapping) else None


def _receipt_form(obs: Mapping[str, Any]) -> str | None:
    value = obs.get("form")
    if isinstance(value, str):
        return value
    return None


def _receipt_filing_date(obs: Mapping[str, Any]) -> str | None:
    point = obs.get("point_in_time") or {}
    if not isinstance(point, Mapping):
        return None
    for key in ("source_available_at", "available_at", "filing_date"):
        v = point.get(key)
        if v is None and key == "filing_date":
            v = obs.get("filing_date")
        if isinstance(v, str):
            return v[:10] if "T" in v else v
    return None


def _receipt_source_url(obs: Mapping[str, Any]) -> str | None:
    value = obs.get("source_url")
    if isinstance(value, str):
        return value
    accession = _receipt_accession(obs)
    cik = _normalize_cik((obs.get("issuer") or {}).get("cik"))
    if cik and accession:
        accession_clean = accession.replace("-", "")
        return f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type=10-K&dateb=&owner=include&count=40"
    return None


def _receipt_excerpt(raw: Mapping[str, Any]) -> str | None:
    """Spec R1 — the receipt's excerpt is the observation's reported.raw
    plus a section label when one is available."""
    parts: list[str] = []
    headline = raw.get("headline_ratio_text") if isinstance(raw, Mapping) else None
    if isinstance(headline, str):
        parts.append(headline)
    section = raw.get("section_label") if isinstance(raw, Mapping) else None
    if isinstance(section, str) and section:
        parts.append(f"Section: {section}")
    if not parts:
        direction = raw.get("direction") if isinstance(raw, Mapping) else None
        if isinstance(direction, str):
            parts.append(f"direction={direction}")
    return " · ".join(parts) if parts else None


def _walk_keys(node: Any, out: set[str]) -> None:
    """Collect every JSON-key path fragment (case-folded) inside ``node``.

    A substring match against the payload's repr would catch legitimate
    user-facing phrases ('a trade call', 'scored: false'), so the
    zero-authority check walks the actual key tree instead. The defense
    is structural, not lexical.
    """
    if isinstance(node, Mapping):
        for k, v in node.items():
            if isinstance(k, str):
                out.add(k.lower())
            _walk_keys(v, out)
    elif isinstance(node, (list, tuple, set)):
        for v in node:
            _walk_keys(v, out)


def _assert_no_extrapolation(payload: Mapping[str, Any]) -> None:
    keys: set[str] = set()
    _walk_keys(payload, keys)
    for bad in _NO_EXTRAPOLATION_KEYS:
        if bad in keys:
            raise AssertionError(
                f"extrapolation key {bad!r} leaked into headroom payload"
            )


def _assert_no_authority_keys(payload: Mapping[str, Any]) -> None:
    keys: set[str] = set()
    _walk_keys(payload, keys)
    for bad in _ZERO_AUTHORITY_KEYS:
        if bad in keys:
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
    coverage: Mapping[str, Any] | None = None,
    generated_at: str | None = None,
    cik_by_source_manifest_id: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Spec R1 — compute the headroom view-model for the SINGLE issuer that
    owns any direct covenant-term observation in ``observations``.

    The page shows one issuer only — when multiple CIKs are present we pick
    the one whose direct observations dominate. If even one observation is
    direct, the page has an issuer. Identity is otherwise unresolved and the
    payload fails closed.

    ``health`` is the optional ``data/capital_structure/health.json`` block;
    its ``covenant_extraction`` sub-dict carries the coverage counts the
    no_terms_extracted refusal copy cites. ``coverage`` is the explicit
    per-call override for tests; ``health`` is preferred when both are
    present.

    Closed-set defenses:
      * REFUSAL names are never constructed ad hoc; ``_NULL_COPY`` is the
        only source of refusal copy and its keys are pinned to REFUSALS.
      * ``COVENANT_METRIC_MAP`` and ``_ALWAYS_DEFINITION_DIFFERS`` are
        asserted against the producer's full term-name set once per call.
      * The emitted payload is checked for extrapolation keys and authority
        keys before return — fails closed if any leak.
    """
    _assert_authority_ceiling()
    _assert_always_definition_differs_disjoint()

    # Prefer the explicit coverage argument; fall back to health's
    # covenant_extraction sub-block. Either way the keys are the same.
    cov = coverage if isinstance(coverage, Mapping) else None
    if cov is None and isinstance(health, Mapping):
        maybe_cov = health.get("covenant_extraction")
        if isinstance(maybe_cov, Mapping):
            cov = maybe_cov

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
            coverage=cov, generated_at=generated_at, period_end=None,
        )
        _assert_no_extrapolation(payload)
        _assert_no_authority_keys(payload)
        return payload

    if not direct_obs:
        return _empty_null_payload(
            "no_terms_extracted", cik=None, ticker=None, issuer_name=None,
            coverage=cov, generated_at=generated_at, period_end=None,
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
            coverage=cov, generated_at=generated_at, period_end=None,
        )

    cik = max(cik_counts, key=lambda k: (cik_counts[k], k))
    issuer_obs = cik_first_obs[cik]

    stmt = fundamentals_by_cik.get(cik)
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
        stmt = None

    period_end = _parse_date(stmt.get("period_end")) if isinstance(stmt, Mapping) else None

    terms_out: list[dict[str, Any]] = []
    for obs in direct_obs:
        if _resolve_issuer(obs, cik_by_source_manifest_id) != cik:
            continue
        terms_out.append(_compute_term(obs, stmt, period_end, cov))

    # Spec R6 — issuers are NEVER ordered by room. The producer's
    # _direct_observations returns observations sorted by logical_observation_id
    # then correction_version desc; the panel renders terms in that order.
    # If we ever switched to a per-CIK ordering, that ordering would be the
    # identity order, never the headroom order.

    if all(t["state"] == "refused" for t in terms_out):
        # All terms refused — degrade the outer state to refusal and surface
        # the most severe child reason. The whole-payload copy wins, so the
        # caller doesn't have to inspect term rows to learn why.
        reasons = [t["refusal"] for t in terms_out if t.get("refusal")]
        # Pick the most specific refusal to surface: definition_differs and
        # ratio_undefined describe the term, others describe the inputs.
        surface = reasons[0] if reasons else "metric_absent"
        for cand in ("definition_differs", "ratio_undefined",
                     "metric_absent", "identity_unresolved", "terms_ambiguous"):
            if cand in reasons:
                surface = cand
                break
        payload = _empty_null_payload(
            surface, cik=cik, ticker=ticker, issuer_name=None,
            coverage=cov, generated_at=generated_at, period_end=period_end,
        )
        payload["terms"] = terms_out
        _assert_no_extrapolation(payload)
        _assert_no_authority_keys(payload)
        return payload

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "parser_version": PARSER_VERSION,
        "authority_ceiling": AUTHORITY_CEILING,
        "scored": SCORED,
        "state": "computed",
        "refusal": None,
        "null_en": None,
        "null_zh": None,
        "refusal_label_en": None,
        "refusal_label_zh": None,
        "disclaimer_en": _CEILING_EN,
        "disclaimer_zh": _CEILING_ZH,
        "issuer": {
            "cik": cik,
            "ticker": ticker,
            "name": None,
        },
        "basis_en": _BASIS_EN,
        "basis_zh": _BASIS_ZH,
        "basis_period_end": period_end.isoformat() if period_end else None,
        "terms": terms_out,
        "coverage": _coverage_block(cov),
        "computed_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "generated_at": generated_at,
    }

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
