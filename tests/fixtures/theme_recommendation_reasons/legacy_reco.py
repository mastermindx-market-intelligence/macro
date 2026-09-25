"""Frozen policy fixture, not a production implementation.
Source: macro@7c6e35163c9f67087ffe174a7ab3810f47ce6a45:engine/theme_scoring.py:_reco.
Only tests execute this independent control.
"""
def _reco(label: str, macro: float, crowd_pen: float, fp: dict,
          mtf: dict | None = None, tape: dict | None = None) -> str:
    below_trend = _long_below_trend(mtf, fp)     # drawdown-control gate (the validated channel)
    extended = _extended(fp, 0.85)               # absolute stretch (non-US) / rs_pctile (US)
    vh_state = ((tape or {}).get("volhole") or {}).get("state")
    if label == "deteriorating":
        return "avoid"
    if label == "fading":
        return "trim"
    if vh_state == "EXPANSION_DOWN":
        return "trim"
    if label == "emerging":
        if below_trend:
            return "hold"
        return "enter" if (macro >= -0.25 and crowd_pen < 0.65) else "hold"
    if label == "dominant":
        if below_trend:
            return "hold"
        if fp.get("ext_abs") is not None:
            # Non-US: leadership itself no longer disqualifies the leader. Per the house rule
            # (crowding only DOWN-SIZES, never fades the dominant theme — narrative_rotation),
            # only a PARABOLIC absolute stretch (ext_abs ≥ EXT_HI) or a macro headwind blocks
            # ACCUMULATE; crowding is shown as a sizing caution, not a veto on the verb.
            return "accumulate" if (not extended and macro >= -0.1) else "hold"
        # US / legacy gate unchanged (rs_pctile + crowding) so the validated page is identical.
        return "accumulate" if (not extended and crowd_pen < 0.6 and macro >= -0.1) else "hold"
    return "hold"
