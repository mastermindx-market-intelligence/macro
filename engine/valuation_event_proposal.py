"""F07 — typed, non-automatic AssumptionChange proposals from source-grounded events.

Frozen spec: research/F07_EVENT_ASSUMPTION_PROPOSAL_CONTRACT_V1.md

Pure: no network, no clock, no IO of its own. Callers pass already-read event
records and an already-built ``valuation_scenario_controls.v1`` blob.

FIRST PRINCIPLE (binding). An event is EVIDENCE; an assumption is a MODEL INPUT.
A filing does not authorize an arbitrary delta. Therefore no number may enter a
proposal that the valuation model has not already published: the event supplies
at most a DIRECTION, and every magnitude comes from the B-F07-1 frozen preset
triple (``engine.valuation_scenario.SCENARIOS``). ``magnitude_source`` is
``"model_preset"`` or nothing — ``"event"`` is unrepresentable by construction.

This module does NOT replace engine/valuation_event_bridge.py (B-F07-3, merged).
That closed class->target map is imported and reused as the DIRECTION_ONLY path.
What is added here is the part a class map cannot carry: event identity, source
refs, a typed abstention with a stated reason, the rights gate, the double-count
law, and read-only consumption by the existing scenario math.

Forbidden by construction: no probability, no confidence, no consensus figure,
no price target, no rating, no LLM-authored number, no automatic application to
any baseline. Authority is research_display_only / shadow.
"""
from __future__ import annotations

import logging
import re as _re

from engine import valuation_event_bridge as _veb
from engine.valuation_scenario import SCENARIOS

log = logging.getLogger(__name__)

SCHEMA = "assumption_change_proposal.v1"
SCENARIO_SCHEMA = "assumption_change_scenario.v1"
MODEL_VERSION = "valuation_scenario.v1"
TIER = "research_display_only"

STATUS_PROPOSED = "PROPOSED"
STATUS_INSUFFICIENT = "INSUFFICIENT"

# --- evidence classes -------------------------------------------------------
EV_MANAGEMENT_FORECAST_CHANGE = "MANAGEMENT_FORECAST_CHANGE"
EV_REPORTED_RESULT = "REPORTED_RESULT"
EV_CORPORATE_ACTION_CLASS = "CORPORATE_ACTION_CLASS"
EV_NONE = "NONE"

# --- mapping methods --------------------------------------------------------
MAP_DIRECTION_TO_MODEL_PRESET = "DIRECTION_TO_MODEL_PRESET"
MAP_DIRECTION_ONLY = "DIRECTION_ONLY"
MAP_NONE = "NONE"

MAGNITUDE_SOURCE_MODEL_PRESET = "model_preset"

# --- abstention reasons, most-structural first (order is the tie-break) -----
R_READER_UNAVAILABLE = "reader_unavailable"
R_NO_EVENT = "no_event"
R_ALREADY_IN_REPORTED_BASE = "already_in_reported_base"
R_SUPERSEDED_BY_BASE = "superseded_by_base"
R_PAYLOAD_NOT_LICENSED = "payload_not_licensed"
R_NO_SOURCE_REF = "no_source_ref"
R_EVENT_CLASS_UNMAPPED = "event_class_unmapped"
R_NO_LAWFUL_CONTROL_MAPPING = "no_lawful_control_mapping"
R_REPORTED_RESULT_NOT_AN_ASSUMPTION = "reported_result_not_an_assumption"
R_EVENT_NOT_YET_OBSERVABLE = "event_not_yet_observable"
R_MODEL_VERSION_MISMATCH = "model_version_mismatch"

_REASON_ORDER = (
    R_READER_UNAVAILABLE,
    R_NO_EVENT,
    R_EVENT_NOT_YET_OBSERVABLE,
    R_MODEL_VERSION_MISMATCH,
    R_ALREADY_IN_REPORTED_BASE,
    R_SUPERSEDED_BY_BASE,
    R_REPORTED_RESULT_NOT_AN_ASSUMPTION,
    R_PAYLOAD_NOT_LICENSED,
    R_NO_SOURCE_REF,
    R_EVENT_CLASS_UNMAPPED,
    R_NO_LAWFUL_CONTROL_MAPPING,
)

# The three B-F07-2 controls, and their position in a SCENARIOS row.
_ASSUMPTION_SLOT = {
    "sales_growth_pct": 1,
    "margin_delta_pp": 2,
    "earnings_multiple": 3,
}
# B-F07-3 target word -> B-F07-2 control key.
_TARGET_TO_ASSUMPTION = {
    _veb.GROWTH: "sales_growth_pct",
    _veb.MARGIN: "margin_delta_pp",
    _veb.MULTIPLE: "earnings_multiple",
}
# Direction -> the model's own adjacent published scenario. Never an invented point.
_DIRECTION_PRESET = {"up": "upbeat", "down": "cautious"}

_PRESETS = {row[0]: row for row in SCENARIOS}


def _preset_value(preset_key: str, assumption_name: str):
    """The model's already-published value for one input in one preset."""
    row = _PRESETS.get(preset_key)
    slot = _ASSUMPTION_SLOT.get(assumption_name)
    if row is None or slot is None:
        return None
    return row[slot]


def _primary_reason(reasons):
    for candidate in _REASON_ORDER:
        if candidate in reasons:
            return candidate
    return None


def _as_date(value) -> str | None:
    """Leading YYYY-MM-DD of an ISO timestamp or date. None when unusable."""
    if value is None:
        return None
    text = str(value).strip()
    if len(text) < 10:
        return None
    head = text[:10]
    if head[4] != "-" or head[7] != "-":
        return None
    if not (head[:4].isdigit() and head[5:7].isdigit() and head[8:10].isdigit()):
        return None
    return head


# ---------------------------------------------------------------------------
# Rights gate. DEC:F07-VALUATION-SOURCE-IS-SEC-COMPANYFACTS-V1 restricts V1
# inputs to SEC companyfacts and forbids consensus estimates, price targets and
# analyst ratings. The gate reads the PAYLOAD, not the event class, so a
# consensus figure cannot enter through a differently-labelled event.
# ---------------------------------------------------------------------------
_CONSENSUS_MARKERS = (
    "est", "estimate", "estimates", "consensus", "surprise", "whisper",
    "price target", "analyst", "analysts", "rating", "ratings",
    "upgrade", "downgrade", "beat", "misses", "street",
)
# Word-boundary matched: a substring test would refuse "invest" for containing
# "est", and a false refusal is as dishonest as a false number.
_CONSENSUS_RE = _re.compile(
    r"\b(?:" + "|".join(_re.escape(m) for m in _CONSENSUS_MARKERS) + r")\b"
)


def _payload_text(event: dict) -> str:
    # Every field a figure could ride in on — including ``phrase``, which is the
    # only text a guidance hit carries.
    parts = [
        str(event.get("title") or ""),
        str(event.get("phrase") or ""),
        str(event.get("summary") or ""),
    ]
    facts = event.get("facts")
    if isinstance(facts, (list, tuple)):
        parts.extend(str(f) for f in facts)
    elif facts:
        parts.append(str(facts))
    return " ".join(parts).lower()


def carries_unlicensed_payload(event: dict) -> bool:
    """True when the event's own payload is consensus-derived.

    Rights refusal, not a data gap: the figure may be real and still be one the
    product has no licence to use as a valuation input.
    """
    return bool(_CONSENSUS_RE.search(_payload_text(event)))


def _source_refs_from_chronicle(event: dict) -> list[dict]:
    """Verifiable refs only. A null link is not a ref."""
    links = event.get("links") if isinstance(event.get("links"), dict) else {}
    url = links.get("source") or links.get("receipt") or None
    source_ref = event.get("source_ref")
    if not url and not source_ref:
        return []
    ref = {
        "kind": "chronicle_event",
        "form": None,
        "cik": None,
        "file_date": _as_date(event.get("ts") or event.get("date")),
        "phrase": None,
        "url": str(url) if url else None,
        "ref": str(source_ref) if source_ref else None,
    }
    # A bare internal correlation key with no resolvable document is not a
    # source the user can open; it does not satisfy invariant 6 on its own.
    if not ref["url"]:
        return []
    return [ref]


def _edgar_document_url(cik: object, hit_id: object) -> str | None:
    """Direct EDGAR URL for the exact filed document the phrase was read from.

    collectors/edgar_guidance.py mints ``id`` as ``<accession>:<document>``, so
    the user can be sent to the filing itself rather than to a search page. Any
    departure from that shape returns None rather than a guessed link.
    """
    if not cik or not hit_id:
        return None
    raw = str(hit_id)
    if ":" not in raw:
        return None
    accession, _, document = raw.partition(":")
    accession_plain = accession.replace("-", "")
    if not accession_plain.isdigit() or not document:
        return None
    cik_int = str(cik).lstrip("0") or "0"
    if not cik_int.isdigit():
        return None
    return (
        f"https://www.sec.gov/Archives/edgar/data/{cik_int}/"
        f"{accession_plain}/{document}"
    )


def _source_refs_from_guidance(hit: dict) -> list[dict]:
    cik = hit.get("cik")
    form = hit.get("form")
    file_date = _as_date(hit.get("file_date"))
    if not (cik and form and file_date):
        return []
    url = _edgar_document_url(cik, hit.get("id"))
    if not url:
        return []
    return [{
        "kind": "sec_filing",
        "form": str(form),
        "cik": str(cik),
        "file_date": file_date,
        "phrase": str(hit.get("phrase") or "") or None,
        "url": url,
        "ref": str(hit.get("id") or "") or None,
    }]


def _base_facts(controls_blob: dict) -> tuple[str | None, str | None, dict]:
    """(ticker, base_period_end, server_default) from a controls blob."""
    if not isinstance(controls_blob, dict):
        return None, None, {}
    ticker = controls_blob.get("ticker") or None
    period_end = _as_date(controls_blob.get("period_end"))
    default = controls_blob.get("server_default")
    return ticker, period_end, default if isinstance(default, dict) else {}


def _build(
    *,
    ticker,
    base_period_end,
    server_default,
    event_id,
    event_class,
    event_class_en,
    event_class_zh,
    observed_at,
    source_refs,
    evidence_class,
    assumption_name,
    direction,
    horizon,
    rationale_en,
    rationale_zh,
    uncertainty,
    what_would_change_this,
    reasons,
):
    """Assemble one proposal and enforce every contract invariant before return."""
    reasons = set(reasons or ())

    # Invariant 3 — a reported result is a FACT owned by the financial-fact
    # owner (SEC companyfacts), never an assumption. It can never be PROPOSED.
    if evidence_class == EV_REPORTED_RESULT:
        reasons.add(R_REPORTED_RESULT_NOT_AN_ASSUMPTION)

    # Invariant 6 — a proposal the user cannot verify is not a proposal.
    if not source_refs:
        reasons.add(R_NO_SOURCE_REF)

    if assumption_name is None:
        reasons.add(R_EVENT_CLASS_UNMAPPED)
    elif assumption_name not in _ASSUMPTION_SLOT:
        reasons.add(R_NO_LAWFUL_CONTROL_MAPPING)

    baseline_value = None
    proposed_value = None
    magnitude_source = None
    mapping_method = MAP_NONE

    if not reasons and direction in _DIRECTION_PRESET:
        baseline_value = server_default.get(assumption_name)
        candidate = _preset_value(_DIRECTION_PRESET[direction], assumption_name)
        if baseline_value is not None and candidate is not None:
            # The magnitude is the model's own adjacent published scenario.
            # The event chose the DIRECTION; B-F07-1 chose the NUMBER.
            proposed_value = candidate
            magnitude_source = MAGNITUDE_SOURCE_MODEL_PRESET
            mapping_method = MAP_DIRECTION_TO_MODEL_PRESET
        else:
            mapping_method = MAP_DIRECTION_ONLY
    elif not reasons:
        mapping_method = MAP_DIRECTION_ONLY

    status = STATUS_INSUFFICIENT if reasons else STATUS_PROPOSED
    if status == STATUS_INSUFFICIENT:
        # Invariant 2 — an abstention never carries a number.
        proposed_value = None
        magnitude_source = None
        mapping_method = MAP_NONE

    # Invariant 1 — a number exists only if it is a published preset value.
    if proposed_value is not None:
        assert magnitude_source == MAGNITUDE_SOURCE_MODEL_PRESET
        assert proposed_value in {
            _preset_value(k, assumption_name) for k in _PRESETS
        }, "proposed_value is not a published V1 preset value"

    return {
        "schema": SCHEMA,
        "status": status,
        "tier": TIER,
        "ticker": ticker,
        "model_version": MODEL_VERSION,
        "base_period_end": base_period_end,
        "event": {
            "event_id": event_id,
            "event_class": event_class,
            "event_class_en": event_class_en,
            "event_class_zh": event_class_zh,
            "observed_at": observed_at,
            "source_refs": list(source_refs or ()),
        },
        "evidence_class": evidence_class,
        "mapping_method": mapping_method,
        "assumption_name": assumption_name if status == STATUS_PROPOSED else None,
        "direction": direction if status == STATUS_PROPOSED else None,
        "baseline_value": baseline_value,
        "proposed_value": proposed_value,
        "magnitude_source": magnitude_source,
        "horizon": horizon,
        "rationale_en": rationale_en,
        "rationale_zh": rationale_zh,
        "uncertainty": uncertainty,
        # Named for what it says, not for the internal term: refutation
        # vocabulary ("falsifier") is never front-facing, and this blob is
        # serialized into the page (DESIGN_DOCTRINE Law 2, operator 2026-07-27).
        "what_would_change_this": what_would_change_this,
        "abstain_reason": _primary_reason(reasons),
        "abstain_reasons": [r for r in _REASON_ORDER if r in reasons],
    }


def _point_in_time_reasons(
    observed_at: str | None,
    base_period_end: str | None,
    as_of: str | None = None,
) -> set:
    """Double-count / look-ahead law, both directions.

    Backward: an event dated on or before the base's period end is already
    inside the reported fundamentals the valuation stands on; proposing it
    again would count it twice.

    Forward: an event dated after ``as_of`` has not happened yet as far as this
    build knows — a scheduled earnings date is a calendar entry, not evidence —
    so it may not propose anything. ``as_of`` is supplied by the caller; this
    module never reads a clock.
    """
    reasons = set()
    obs = _as_date(observed_at)
    if obs is None:
        return {R_NO_SOURCE_REF}
    ceiling = _as_date(as_of)
    if ceiling and obs > ceiling:
        reasons.add(R_EVENT_NOT_YET_OBSERVABLE)
    if base_period_end and obs <= base_period_end:
        reasons.add(R_ALREADY_IN_REPORTED_BASE)
    return reasons


def propose_from_chronicle_event(
    event: object, controls_blob: object, as_of: object = None
) -> dict | None:
    """Typed proposal (or typed abstention) for one chronicle event record."""
    if not isinstance(controls_blob, dict):
        return None
    ticker, base_period_end, server_default = _base_facts(controls_blob)
    if not isinstance(event, dict):
        return _build(
            ticker=ticker, base_period_end=base_period_end,
            server_default=server_default, event_id=None, event_class=None,
            event_class_en=None, event_class_zh=None, observed_at=None,
            source_refs=[], evidence_class=EV_NONE, assumption_name=None,
            direction=None, horizon=None,
            # Same sentence the panel has always shown for this case. The copy
            # lives here so the engine and the template cannot drift apart.
            rationale_en="No filing on file yet for this company.",
            rationale_zh="该公司暂无备案。",
            uncertainty="No event, so no assumption is proposed.",
            what_would_change_this="A classified, source-linked event arriving for this issuer.",
            reasons={R_NO_EVENT},
        )

    kind = str(event.get("kind") or "").strip()
    observed_at = _as_date(event.get("ts") or event.get("date"))
    reasons = _point_in_time_reasons(observed_at, base_period_end, as_of)

    if carries_unlicensed_payload(event):
        reasons.add(R_PAYLOAD_NOT_LICENSED)

    if kind == "earnings":
        evidence_class = EV_REPORTED_RESULT
        bridged = None
    else:
        bridged = _veb.bridge_for_issuer(kind)
        evidence_class = EV_CORPORATE_ACTION_CLASS if bridged else EV_NONE

    assumption_name = None
    direction = None
    if bridged:
        assumption_name = _TARGET_TO_ASSUMPTION.get(bridged.get("target"))
        word = str(bridged.get("direction_word") or "").lower()
        direction = "up" if "lift" in word else "down" if "press" in word else None

    if kind == "earnings":
        rationale_en = (
            "A reported quarterly result is a fact, not a forecast. Its figures "
            "belong to the reported fundamentals this valuation already stands on, "
            "so it does not move an assumption on its own."
        )
        rationale_zh = "已公布的季度业绩属于事实，而非预测，不会单独改变估值假设。"
        uncertainty = (
            "The only forward-looking figure attached to this record is measured "
            "against analyst estimates, which this product has no licence to use."
        )
    else:
        rationale_en = (
            f"A {(bridged or {}).get('event_class_en') or kind or 'classified'} event "
            "argues this input moves, but the filing states no figure for it."
        )
        rationale_zh = "该事件提示此项假设可能变动，但文件本身未给出具体数值。"
        uncertainty = (
            "The event class gives a direction only. The size of any change is not "
            "stated by the source."
        )

    return _build(
        ticker=ticker, base_period_end=base_period_end,
        server_default=server_default,
        event_id=str(event.get("id") or "") or None,
        event_class=kind or None,
        event_class_en=(bridged or {}).get("event_class_en") or kind or None,
        event_class_zh=(bridged or {}).get("event_class_zh") or kind or None,
        observed_at=observed_at,
        source_refs=_source_refs_from_chronicle(event),
        evidence_class=evidence_class,
        assumption_name=assumption_name,
        direction=direction,
        horizon=None,
        rationale_en=rationale_en,
        rationale_zh=rationale_zh,
        uncertainty=uncertainty,
        what_would_change_this=(
            "The same issuer filing a document that states a figure for this input, "
            "or the reported base advancing past this event."
        ),
        reasons=reasons,
    )


_GUIDANCE_DIRECTION = {"raise": "up", "cut": "down"}


def propose_from_guidance_hit(
    hit: object, controls_blob: object, as_of: object = None
) -> dict | None:
    """Typed proposal for one collectors/edgar_guidance.py 8-K directional hit.

    This is the rights-clean path: the source is an SEC filing, the signal is an
    explicit management forecast change, and the payload is a PHRASE, never a
    consensus figure. The phrase gives direction; the number stays the model's.
    """
    if not isinstance(controls_blob, dict) or not isinstance(hit, dict):
        return None
    ticker, base_period_end, server_default = _base_facts(controls_blob)
    observed_at = _as_date(hit.get("file_date"))
    reasons = _point_in_time_reasons(observed_at, base_period_end, as_of)

    if carries_unlicensed_payload(hit):
        reasons.add(R_PAYLOAD_NOT_LICENSED)

    direction = _GUIDANCE_DIRECTION.get(str(hit.get("direction") or "").strip().lower())
    if direction is None:
        reasons.add(R_EVENT_CLASS_UNMAPPED)

    phrase = str(hit.get("phrase") or "").strip()
    horizon = "full year" if "full-year" in phrase or "full year" in phrase else "the period management guided"

    return _build(
        ticker=ticker, base_period_end=base_period_end,
        server_default=server_default,
        event_id=str(hit.get("id") or "") or None,
        event_class="guidance_change",
        event_class_en="Guidance change", event_class_zh="业绩指引变动",
        observed_at=observed_at,
        source_refs=_source_refs_from_guidance(hit),
        evidence_class=EV_MANAGEMENT_FORECAST_CHANGE,
        assumption_name="sales_growth_pct",
        direction=direction,
        horizon=horizon,
        rationale_en=(
            f"Management told the SEC “{phrase}”. That is a change to the "
            "company's own outlook, so the growth input is the one it argues about."
            if phrase else
            "Management filed a change to its own outlook, so the growth input is "
            "the one it argues about."
        ),
        rationale_zh="管理层已向 SEC 提交了自身业绩展望的变动，因此涉及的是增长假设。",
        uncertainty=(
            "The filing states a direction, not a size. The figure shown is this "
            "model's own published scenario in that direction — not a number the "
            "company gave. Phrase matching also has no negation handling."
        ),
        what_would_change_this=(
            "The same phrase read in context reversing its direction, or a later "
            "filing withdrawing the change."
        ),
        reasons=reasons,
    )


def evaluate_proposal(controls_blob: object, proposal: object) -> dict | None:
    """Shadow, read-only: baseline valuation vs the proposed-event scenario.

    Calls the EXISTING ``valuation_assumptions.per_share_at`` — this module
    implements no valuation math of its own, and writes nothing back. An
    abstention is carried through as a refusal, never as a silent zero.
    """
    if not isinstance(controls_blob, dict) or not isinstance(proposal, dict):
        return None
    # Local import: valuation_assumptions is the consumer side of this module.
    from engine.valuation_assumptions import per_share_at

    inputs = controls_blob.get("inputs")
    default = controls_blob.get("server_default")
    if not isinstance(inputs, dict) or not isinstance(default, dict):
        return None

    ni = inputs.get("net_income")
    revenue = inputs.get("revenue")
    shares = inputs.get("shares")
    baseline_ps = default.get("per_share")

    applied = {
        "sales_growth_pct": default.get("sales_growth_pct"),
        "margin_delta_pp": default.get("margin_delta_pp"),
        "earnings_multiple": default.get("earnings_multiple"),
    }

    name = proposal.get("assumption_name")
    proposed_value = proposal.get("proposed_value")
    refused = proposal.get("status") != STATUS_PROPOSED or proposed_value is None

    # Binding checks for a proposal that was stored and replayed later. A
    # proposal is only meaningful against the exact model and base it was made
    # against; evaluating it against a different one would silently rewrite
    # history, and re-applying an event the newer base has since absorbed would
    # double-count it.
    binding_reason = None
    blob_period_end = _as_date(controls_blob.get("period_end"))
    prop_period_end = _as_date(proposal.get("base_period_end"))
    if proposal.get("model_version") != MODEL_VERSION:
        binding_reason = R_MODEL_VERSION_MISMATCH
    elif prop_period_end and blob_period_end and prop_period_end != blob_period_end:
        binding_reason = R_SUPERSEDED_BY_BASE
    if binding_reason:
        refused = True

    proposed_ps = None
    if not refused and name in applied:
        shadow = dict(applied)
        shadow[name] = proposed_value
        proposed_ps = per_share_at(
            ni, revenue, shares,
            shadow["sales_growth_pct"],
            shadow["margin_delta_pp"],
            shadow["earnings_multiple"],
        )

    delta = None
    if baseline_ps is not None and proposed_ps is not None:
        delta = round((proposed_ps - baseline_ps) * 100) / 100.0

    return {
        "schema": SCENARIO_SCHEMA,
        "tier": TIER,
        "applied": False,           # a proposal is NEVER applied to the baseline
        "ticker": proposal.get("ticker"),
        "model_version": MODEL_VERSION,
        "base_period_end": proposal.get("base_period_end"),
        "baseline": {"assumptions": dict(applied), "per_share": baseline_ps},
        "proposed": None if refused else {
            "assumptions": {**applied, name: proposed_value},
            "per_share": proposed_ps,
        },
        "changed_assumptions": [] if refused else [name],
        "unchanged_assumptions": (
            sorted(applied) if refused else sorted(k for k in applied if k != name)
        ),
        "per_share_delta": delta,
        "magnitude_source": proposal.get("magnitude_source"),
        "source_refs": (proposal.get("event") or {}).get("source_refs") or [],
        "refused": refused,
        "abstain_reason": binding_reason or proposal.get("abstain_reason"),
        "abstain_reasons": (
            [binding_reason] if binding_reason else (proposal.get("abstain_reasons") or [])
        ),
    }


def best_proposal(
    controls_blob: object,
    chronicle_events: object = (),
    guidance_hits: object = (),
    as_of: object = None,
) -> dict | None:
    """Pick one proposal for the issuer panel.

    A rights-clean management forecast change outranks a chronicle record. When
    nothing lawful is available the most informative ABSTENTION is returned —
    the panel says why, rather than showing nothing.
    """
    if not isinstance(controls_blob, dict):
        return None
    candidates = []
    for hit in (guidance_hits or ()):
        p = propose_from_guidance_hit(hit, controls_blob, as_of)
        if p:
            candidates.append(p)
    for event in (chronicle_events or ()):
        p = propose_from_chronicle_event(event, controls_blob, as_of)
        if p:
            candidates.append(p)
    if not candidates:
        return propose_from_chronicle_event(None, controls_blob)

    proposed = [p for p in candidates if p.get("status") == STATUS_PROPOSED]
    if proposed:
        return max(proposed, key=lambda p: (p.get("event") or {}).get("observed_at") or "")
    return max(candidates, key=lambda p: (p.get("event") or {}).get("observed_at") or "")


def proposal_reader_unavailable(controls_blob: object) -> dict | None:
    """Typed abstention for "the event reader itself failed".

    Distinct from ``no_event`` on purpose: a broken reader and an issuer with
    no events are different facts, and collapsing them is how a silent
    degradation reads on screen as a confident "nothing on file".
    """
    if not isinstance(controls_blob, dict):
        return None
    ticker, base_period_end, server_default = _base_facts(controls_blob)
    return _build(
        ticker=ticker, base_period_end=base_period_end,
        server_default=server_default, event_id=None, event_class=None,
        event_class_en=None, event_class_zh=None, observed_at=None,
        source_refs=[], evidence_class=EV_NONE, assumption_name=None,
        direction=None, horizon=None,
        rationale_en="The event record for this company could not be read just now.",
        rationale_zh="暂时无法读取该公司的事件记录。",
        uncertainty="This is a reading problem, not a statement about the company.",
        what_would_change_this="The event reader returning records for this issuer again.",
        reasons={R_READER_UNAVAILABLE},
    )
