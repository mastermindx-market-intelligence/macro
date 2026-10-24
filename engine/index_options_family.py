"""NDX (AM) + NDXP (PM) family admission for the existing Options Hub GEX engine.

This is a source-frame composer, NOT a collector, trading signal, independent
publisher or permission to redistribute ThetaData. All inputs are EOD and their
first-available timestamps are not inferred from their underlying market date.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
import math

import pandas as pd

from engine.exposure_math import MIN_QUOTED_IV

NDX_FAMILY_ROOTS = ("NDX", "NDXP")
_KEY = ("expiration", "strike", "right")
_REQUIRED_G = ("date", "expiration", "strike", "right", "gamma", "underlying_price")
_REQUIRED_OI = ("date", "expiration", "strike", "right", "open_interest")


class FamilySourceUnavailable(ValueError):
    """Not qualified; do not write a family GEX envelope or fill missing as zero."""


@dataclass(frozen=True)
class QualifiedFamilyFrames:
    greeks: pd.DataFrame
    oi: pd.DataFrame
    session: str
    root_contract_counts: dict[str, int]
    shared_strike_expiry_side_keys: int
    spot_ref: float


def _session(text: str) -> date:
    if not isinstance(text, str) or len(text) != 10:
        raise FamilySourceUnavailable("explicit ISO source session required")
    try:
        day = date.fromisoformat(text)
    except ValueError as exc:
        raise FamilySourceUnavailable("invalid source session") from exc
    if day.isoformat() != text:
        raise FamilySourceUnavailable("noncanonical source session")
    return day


def _validated_frame(
    raw: pd.DataFrame, root: str, asof: str, *, is_greeks: bool,
) -> pd.DataFrame:
    family = "greeks" if is_greeks else "oi"
    required = _REQUIRED_G if is_greeks else _REQUIRED_OI
    if not isinstance(raw, pd.DataFrame) or raw.empty:
        raise FamilySourceUnavailable(f"{root}: absent {family} source")
    absent = set(required).difference(raw.columns)
    if absent:
        raise FamilySourceUnavailable(f"{root}: missing {family} fields {sorted(absent)}")
    df = raw.copy()
    if "contract_root" in df.columns:
        if df["contract_root"].isna().any() or not df["contract_root"].eq(root).all():
            raise FamilySourceUnavailable(f"{root}: foreign contract identity")
    if "root" in df.columns:
        if df["root"].isna().any() or not df["root"].eq(root).all():
            raise FamilySourceUnavailable(f"{root}: conflicting root field")
    try:
        df["date"] = pd.to_datetime(df["date"], errors="raise").dt.date.astype(str)
        df["expiration"] = pd.to_datetime(df["expiration"], errors="raise").dt.date.astype(str)
    except (ValueError, TypeError) as exc:
        raise FamilySourceUnavailable(f"{root}: invalid source date") from exc
    if not df["date"].eq(asof).all():
        raise FamilySourceUnavailable(f"{root}: cross-session {family} rows")
    if (df["expiration"] < asof).any():
        raise FamilySourceUnavailable(f"{root}: expired option present")
    df["right"] = df["right"].astype(str).str.upper()
    if not df["right"].isin(("C", "P")).all():
        raise FamilySourceUnavailable(f"{root}: unrecognized option side")
    strike = pd.to_numeric(df["strike"], errors="coerce")
    if not strike.map(lambda n: math.isfinite(n) and n > 0).all():
        raise FamilySourceUnavailable(f"{root}: invalid strike")
    df["strike"] = strike.astype(float)
    if df.duplicated(list(_KEY)).any():
        raise FamilySourceUnavailable(f"{root}: duplicate contract key")
    name = "gamma" if is_greeks else "open_interest"
    amount = pd.to_numeric(df[name], errors="coerce")
    if not amount.map(lambda n: math.isfinite(n) and n >= 0).all():
        raise FamilySourceUnavailable(f"{root}: unknown {name} (not zero)")
    df[name] = amount.astype(float)
    if is_greeks:
        spot = pd.to_numeric(df["underlying_price"], errors="coerce")
        if not spot.map(lambda n: math.isfinite(n) and n > 0).all():
            raise FamilySourceUnavailable(f"{root}: underlying cash/index spot missing")
        df["underlying_price"] = spot.astype(float)
        if "implied_vol" in df.columns:
            iv = pd.to_numeric(df["implied_vol"], errors="coerce")
            if ((iv.notna()) & ((iv < MIN_QUOTED_IV) | (~iv.map(math.isfinite)))).any():
                raise FamilySourceUnavailable(f"{root}: degenerate IV would drop a family contract")
    df["contract_root"] = root
    return df.sort_values(["contract_root", *_KEY]).reset_index(drop=True)


def qualify_ndx_family(
    raw_by_root: Mapping[str, tuple[pd.DataFrame, pd.DataFrame]], asof: str,
) -> QualifiedFamilyFrames:
    """Require both source roots, same session, exact sides and distinct identities.

    This proves internal row-level joins, NOT full ThetaData chain enumeration,
    provider commercial redisplay authorization or a replay vintage.
    """
    _session(asof)
    if set(raw_by_root) != set(NDX_FAMILY_ROOTS):
        raise FamilySourceUnavailable("NDX family requires BOTH NDX and NDXP")
    gframes, oframes, counts = [], [], {}
    keys_by_root: dict[str, set[tuple]] = {}
    root_spots: dict[str, float] = {}
    for root in NDX_FAMILY_ROOTS:
        entry = raw_by_root[root]
        if not isinstance(entry, tuple) or len(entry) != 2:
            raise FamilySourceUnavailable(f"{root}: missing greeks/OI pair")
        greek = _validated_frame(entry[0], root, asof, is_greeks=True)
        oi = _validated_frame(entry[1], root, asof, is_greeks=False)
        gkeys = set(map(tuple, greek[list(_KEY)].itertuples(index=False, name=None)))
        okeys = set(map(tuple, oi[list(_KEY)].itertuples(index=False, name=None)))
        if gkeys != okeys:
            raise FamilySourceUnavailable(f"{root}: greek/OI contract mismatch")
        prices = greek["underlying_price"]
        representative = float(prices.median())
        if ((prices / representative - 1).abs() > 0.0025).any():
            raise FamilySourceUnavailable(f"{root}: inconsistent index spot observations")
        counts[root], keys_by_root[root] = len(greek), gkeys
        root_spots[root] = representative
        gframes.append(greek)
        oframes.append(oi)
    spot = float(pd.Series(root_spots).median())
    if any(abs(p / spot - 1) > 0.0025 for p in root_spots.values()):
        raise FamilySourceUnavailable("NDX and NDXP underlying spot bases differ")
    return QualifiedFamilyFrames(
        greeks=pd.concat(gframes, ignore_index=True),
        oi=pd.concat(oframes, ignore_index=True),
        session=asof,
        root_contract_counts=counts,
        shared_strike_expiry_side_keys=len(keys_by_root["NDX"] & keys_by_root["NDXP"]),
        spot_ref=spot,
    )


def build_ndx_family_gex(
    raw_by_root: Mapping[str, tuple[pd.DataFrame, pd.DataFrame]], asof: str,
) -> dict:
    """Reuse existing GEX arithmetic after root-aware, fail-closed frame admission."""
    from engine.options_hub import compute_gex

    qualified = qualify_ndx_family(raw_by_root, asof)
    result = compute_gex(qualified.greeks, qualified.oi, asof, "NDX")
    if (not result.get("by_strike") or result.get("net_gex_bn") is None or
            result.get("spot_ref") is None):
        raise FamilySourceUnavailable("GEX computation incomplete; refuse family output")
    result["family_source"] = {
        "schema": "mastermind.index_options_family_source.v1",
        "root": "NDX",
        "source_roots": list(NDX_FAMILY_ROOTS),
        "session": qualified.session,
        "spot_ref": qualified.spot_ref,
        "root_contract_counts": qualified.root_contract_counts,
        "shared_strike_expiry_side_keys": qualified.shared_strike_expiry_side_keys,
        "observation_basis": "ThetaData EOD Greeks + reported prior-session OI",
        "coverage": "observed_contract_rows_only",
        "historical_first_available_at": None,
        "complete_chain_receipt": False,
        "redistribution_grant": None,
        "state": "OFFLINE_SOURCE_QUALIFIED_NOT_PUBLISHABLE",
    }
    return result
