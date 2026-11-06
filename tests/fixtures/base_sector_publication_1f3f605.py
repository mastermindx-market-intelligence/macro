"""Original builder publication block at 1f3f605, with controlled input/clock scaffold."""
from copy import deepcopy
from datetime import timezone
import logging
log = logging.getLogger(__name__)
_SC_PAYLOAD_URL = 'premiumdata/sector_central.json'

class _Clock:
    def __init__(self, value): self.value = value
    def now(self, tz): return self.value

def complete_original(data, *, _flows_status, _si_status, _ab_status, _bk_status,
                      _grader_status, _payload_written, _sc_locked, built_at):
    data = deepcopy(data)
    datetime = _Clock(built_at)
    # ── SIC-D-B13: crowding-input activation disclosure ───────────────────────
    # The basket crowding cap went live with score version 2 (member id resolved via
    # `ticker`). The publication record says WHAT the crowding input actually resolved
    # this build and WHEN the first version-2 call was logged — pure .get() reads off
    # data already in hand (engine meta + the scorecard above), so this can never
    # raise and never changes a value the builder used.
    _meta = data.get("meta") or {}
    _mc = _meta.get("membership_coverage") or {}
    _n_baskets = _meta.get("n_baskets") or 0
    _n_unres = _mc.get("n_crowding_unresolved") or 0
    _n_res = max(_n_baskets - _n_unres, 0)
    if _n_baskets > 0 and _n_unres == 0:
        _crowd_status = "resolved"
    elif _n_res == 0:
        _crowd_status = "no_members_resolved"
    else:
        _crowd_status = "partial"
    _grader_out = data.get("grader") or {}
    _first_active = ((_grader_out.get("score_version_segments") or {})
                     .get("2") or {}).get("first_date")
    _crowding_input = {
        "status": _crowd_status,
        "score_version": _meta.get("conviction_score_version"),
        "first_active_session": _first_active,
        "n_baskets": _n_baskets,
        "n_baskets_resolved": _n_res,
    }
    if _first_active is None:
        # an off-lane render never logs (COLLECT_LANE gate), so "not yet" is the
        # normal state on every non-nightly build. RB13 F2: a scorecard that says
        # available=False carries its own reason ("no calls logged yet", "empty",
        # "unreadable: ...") and that reason is propagated verbatim; "grader
        # unavailable" is reserved for the exception shape (no scorecard at all
        # because grade() raised above).
        if _grader_out.get("available") is False:
            _note = _grader_out.get("note")
            _crowding_input["first_active_note"] = (
                str(_note) if _note else "grader unavailable")
        elif "available" not in _grader_out:
            _crowding_input["first_active_note"] = "grader unavailable"
        else:
            _crowding_input["first_active_note"] = "no version-2 call logged yet"

    # ── PUBLICATION RECORD (B10, masterplan §6.1) ────────────────────────────
    # The free artifacts are written HERE — after the secondary reads and the tier
    # split, before the render — so they can carry a typed record of what this
    # build actually consumed: one status per secondary source with the failure
    # MODE preserved, the generation it was built from, and the correction
    # contract. Values the builder used are unchanged; only the record is new.
    data["publication"] = {
        "schema": "sector_central.publication.v1",
        "as_of": data.get("as_of"),
        "built_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "secondary_sources": {
            "flows_html": _flows_status,
            "si_handoff": _si_status,
            "action_board": _ab_status,
            "baskets": _bk_status,
            "grader": _grader_status,
        },
        "premium_payload": {
            "path": _SC_PAYLOAD_URL,
            "written": _payload_written,
            # row count, not lane-group count: _sc_locked is one entry per lane with
            # withheld rows, and write_payload's own log line counts the rows
            "withheld_rows": sum(len(_L["rows"]) for _L in _sc_locked),
        },
        "history_mode": "observed_at_build",
        "correction_contract": {
            "status": "none_native",
            "basis": "no native correction or revision field in Central inputs "
                     "(capability row R3A-92)",
        },
        # SIC-D-B13: the crowding-input activation disclosure (see the block above).
        "crowding_input": _crowding_input,
    }
    # ── SOURCE-BOUND RESEARCH HANDOFF (B09, masterplan §5) ────────────────────
    # Every selectable group row (data["sectors"] / data["baskets"]) carries a
    # handoff a Dossier or Research receiver can bind to without guessing:
    # subject/kind, an immutable per-row snapshot digest, the source/generation/
    # clock, the evidence mode and the return context — with explicit
    # not_supplied where the native source states no relationship. Attached
    # AFTER the publication record (the generation is copied from it) and
    # BEFORE the free writes so both free artifacts carry it. Additive and
    # fail-soft both per row and as a whole: the build continues exactly as
    # before either way. engine.sector_research_handoff is import-light.
    try:
        from engine.sector_research_handoff import attach_handoffs
        _rh = attach_handoffs(data)
        data["publication"]["research_handoff"] = {
            "version": 1, "rows": _rh["rows"], "unavailable": _rh["unavailable"]}
    except Exception as e:  # noqa: BLE001 — additive, never fatal
        log.warning("sector_central: research handoff step failed (%s)", e)
        data["publication"]["research_handoff"] = {"status": "error"}
    return data
