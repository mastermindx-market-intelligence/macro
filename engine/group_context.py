"""Group (rotation) context for the US Buy Board 2.0 shadow build.

Maps each name → its sector / subsector / theme memberships → the leadership
states those cycle pages ALREADY publish, and fuses them into a single
leadership score ∈ [-1, +1] plus display chips and a ``surfaced_by`` list.

WHY this module exists (W6-US §2, "borrow strength from the hierarchy level
where edge exists"): name-level cross-sectional selection IC ≈ 0, but the
GROUP-level rotation engines are validated / forward-tracked (sector_central is
a gated-confluence merge of 4 engines; subsectors LAS Running/Coiling carries a
forward track record; subsector_rotation is an RRG read). The board therefore
borrows conviction from the group. The leadership score is used ONLY for
(a) ordering and (b) edge-floor MODULATION — **never** as a hard gate. The
standing caution is the China falsification: hard-gating a name by its group's
state HURT A-share reversal (research/china-subsector-gate-falsified). Group
state modulates the bar; it never slams the door.

DEFENSIVE COUPLING (mandatory). Every rotation artifact this module reads is
pending its OWN improvement session. A missing file, a missing field, or a
schema change MUST degrade to neutral (score 0, empty chips) with a freshness /
``degraded`` flag on the passport — it must NEVER crash the board build. The
reader contract (artifact path + the minimal fields we depend on) is versioned
in ``READER_CONTRACT`` in ONE place so the coupling is auditable; when a cycle
page changes shape, update the contract here, not scattered call sites.
"""
from __future__ import annotations

import copy
import json
import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from engine import signal_gate

try:  # keep importable even if lib.config is unavailable in an odd harness
    from lib import config

    _ROOT = config.ROOT
except Exception:  # noqa: BLE001
    _ROOT = Path(__file__).resolve().parent.parent

log = logging.getLogger("group_context")

ENTRY_CONTEXT_SCHEMA = "mastermind.entry_context.v1"
ENTRY_CONTEXT_STALE_DAYS = 4
STANDOUTS_REF = "site/factordata/us_standouts.json"
RADAR_REF = "site/live/entry_radar.json"
CONFLUENCE_REF = "site/marketdata/subsector_confluence.json"
AUTHORITY_BLOCK: dict[str, bool] = {
    "may_rank": False,
    "may_gate": False,
    "may_size": False,
    "may_escalate": False,
    "may_trade": False,
}
ENTRY_CONTEXT_PERMISSIONS: dict[str, bool] = {
    "may_describe": True,
    "may_link": True,
    **AUTHORITY_BLOCK,
}
_ENTRY_LANES = ("buy", "watch", "leaders", "ran", "laggards", "candidate_pool")
_ENTRY_ID_KEYS = ("source_setup_id", "setup_id", "candidate_id", "entry_id")
_ENTRY_EXPIRY_KEYS = ("expires_at", "valid_until", "ttl_until", "expiry")

# --------------------------------------------------------------------------- #
#  READER CONTRACT — the ONE place the coupling to the cycle pages is declared. #
#  Each entry: the artifact path (relative to site/) + the minimal fields we    #
#  read. If a cycle page renames/moves these, update HERE (and the reader).     #
#  Version bump = contract changed; the passport carries it so a stale reader   #
#  against a new artifact is visible downstream.                                #
# --------------------------------------------------------------------------- #
READER_CONTRACT = {
    "version": 3,
    "sources": {
        "sector_central": {
            "path": "site/sectordata/sector_central.json",
            "join": "row.sector (GICS name) → sectors[].name",
            "fields": ["as_of", "sectors[].name", "sectors[].conviction.score",
                       "sectors[].conviction.dir", "sectors[].forward.trend_pass",
                       "sectors[].cycle.pos", "sectors[].heat.heat_1M"],
            "weight": 0.45,   # always-present leadership backbone (covers every sector)
        },
        "subsector_confluence": {
            "path": "site/marketdata/subsector_confluence.json",
            "join": "row.ticker → subsectors[].members[].ticker",
            "fields": ["as_of", "weighting", "generated_utc",
                       "subsectors[].key", "subsectors[].label",
                       "subsectors[].class", "subsectors[].entry.tier",
                       "subsectors[].entry.buyable", "subsectors[].regime.state",
                       "subsectors[].members[].ticker",
                       "subsectors[].members[].stock_tier",
                       "subsectors[].members[].stock_eligible",
                       "subsectors[].members[].stock_buyable",
                       "subsectors[].members[].stock_reason"],
            "weight": 0.25,
        },
        "index_leadership": {
            "path": "site/marketdata/index_leadership.json",
            "join": "subsector key (via confluence) → tabs[*].rising[]/coiling[].key",
            "fields": ["as_of", "tabs[*].rising[].key", "tabs[*].coiling[].key",
                       "tabs[*].las", "tabs[*].quadrant", "rising_star.label"],
            "weight": 0.10,   # LAS Running/Coiling — forward-tracked, so a real chip
        },
        "subsector_rotation": {
            "path": "site/marketdata/subsector_rotation.json",
            "join": "row.ticker → subsectors[].members[].t",
            "fields": ["asof", "subsectors[].quadrant", "subsectors[].rs_mom",
                       "subsectors[].emerging_score", "subsectors[].members[].t"],
            "weight": 0.10,
        },
        "baskets": {
            "path": "site/basketdata/baskets.json",
            "join": "row.ticker → baskets[].members[].symbol; theme via theme_intel",
            "fields": ["as_of", "baskets[].id", "baskets[].members[].symbol",
                       "theme_intel.themes[].id", "theme_intel.themes[].score",
                       "theme_intel.themes[].label", "theme_intel.themes[].reco"],
            "weight": 0.10,
        },
    },
    "entry_context": {
        "schema": ENTRY_CONTEXT_SCHEMA,
        "mode": "owner_artifact_rebuild",
        "sources": [
            "site/factordata/us_standouts.json",
            "site/live/entry_radar.json",
            "site/marketdata/subsector_confluence.json",
        ],
        "authority": "context_only",
    },
}

# GICS naming differs between artifacts (standouts "Information Technology" vs
# sector_central "Technology"; "Communication Services" absent from standouts).
# Normalise on the way in so the sector join is not silently dropped.
_SECTOR_ALIASES = {
    "information technology": "technology",
    "info tech": "technology",
    "healthcare": "health care",
    "comm services": "communication services",
    "communications": "communication services",
    "consumer disc": "consumer discretionary",
    "consumer staple": "consumer staples",
}

# RRG / confluence quadrant → a signed leadership contribution in [-1, +1].
_QUADRANT_SCORE = {
    "leading": 1.0,
    "improving": 0.4,
    "weakening": -0.3,
    "lagging": -1.0,
}
# subsector confluence `class` → contribution.
_CLASS_SCORE = {
    "entry_now": 0.8,
    "forming": 0.3,
    "headwind": -0.6,
}
# subsector regime `state` → a modest tilt (EXTENDED is late, not leadership).
_REGIME_TILT = {
    "TAILWIND": 0.3, "SETUP": 0.2, "MIXED": 0.0,
    "EXTENDED": -0.1, "HEADWIND": -0.5, "AVOID": -0.5,
}


def _norm_sector(s: str | None) -> str:
    if not s:
        return ""
    k = s.strip().lower()
    return _SECTOR_ALIASES.get(k, k)


def _safe_load(path: Path) -> tuple[dict | None, str | None]:
    """Load a JSON artifact tolerantly. Returns (data, error). Never raises."""
    try:
        if not path.exists():
            return None, "missing"
        return json.loads(path.read_text()), None
    except Exception as e:  # noqa: BLE001
        return None, f"read_error:{type(e).__name__}"


def _artifact_age_days(as_of: Any) -> int | None:
    """Trading-ish staleness of an artifact's as_of date vs today (calendar days)."""
    if not as_of:
        return None
    try:
        d = datetime.fromisoformat(str(as_of)[:10]).date()
        return (date.today() - d).days
    except Exception:  # noqa: BLE001
        return None


@dataclass
class _Source:
    """A loaded rotation source with its coverage/freshness passport."""

    key: str
    data: dict | None
    error: str | None
    as_of: Any = None
    age_days: int | None = None
    degraded: bool = False

    def __post_init__(self) -> None:
        self.degraded = self.data is None or self.error is not None


class GroupContext:
    """Loads the rotation artifacts ONCE and resolves per-name context.

    Construct once per board build (cheap: five small JSON reads), then call
    :meth:`for_name` per ticker. All lookups are membership joins on already
    committed artifacts — no price math, no recompute — so the whole pass is
    well under the runtime budget.
    """

    STALE_DAYS = 4  # a rotation read older than this is flagged (weekend-tolerant)

    def __init__(self, site: Path | None = None) -> None:
        if site is None:
            base = _ROOT
        else:
            explicit = Path(site)
            base = explicit.parent if explicit.name == "site" else explicit
        self._root = base
        self._entry_source = EntryContextSource.from_site(self._root / "site")
        self._sources: dict[str, _Source] = {}
        self._sector_by_name: dict[str, dict] = {}
        self._sub_by_ticker: dict[str, list[dict]] = {}
        self._subkey_lead: dict[str, dict] = {}   # subsector key → {running, coiling, tab, las}
        self._rot_by_ticker: dict[str, list[dict]] = {}
        self._basket_by_ticker: dict[str, list[str]] = {}
        self._theme_by_basket: dict[str, dict] = {}
        self._load_all()

    # ---- loading ---------------------------------------------------------- #
    def _load_all(self) -> None:
        for key, spec in READER_CONTRACT["sources"].items():
            data, err = _safe_load(self._root / spec["path"])
            as_of = None
            if isinstance(data, dict):
                as_of = data.get("as_of") or data.get("asof") or data.get("generated_utc")
            src = _Source(key=key, data=data, error=err, as_of=as_of,
                          age_days=_artifact_age_days(as_of))
            if src.age_days is not None and src.age_days > self.STALE_DAYS:
                src.degraded = True  # present but stale → treat as degraded for passport
            self._sources[key] = src
            if not src.degraded and isinstance(data, dict):
                try:
                    getattr(self, f"_index_{key}")(data)
                except Exception as e:  # noqa: BLE001  never let one bad shape break the rest
                    log.warning("group_context: indexing %s failed (%s) — degrading", key, e)
                    src.degraded = True

    def _index_sector_central(self, data: dict) -> None:
        for s in data.get("sectors", []) or []:
            nm = _norm_sector(s.get("name"))
            if nm:
                self._sector_by_name[nm] = s

    def _index_subsector_confluence(self, data: dict) -> None:
        for raw_group in data.get("subsectors", []) or []:
            if not isinstance(raw_group, dict):
                continue
            group = dict(raw_group)
            group.setdefault("as_of", data.get("as_of"))
            group.setdefault("weighting", data.get("weighting"))
            group.setdefault("generated_utc", data.get("generated_utc"))
            group.setdefault("market", "US")
            group.setdefault("timeframe", "1D")
            group.setdefault("session", "EOD")
            group.setdefault("horizon", "daily")
            for member in group.get("members", []) or []:
                if not isinstance(member, dict):
                    continue
                ticker = member.get("ticker")
                if ticker:
                    self._sub_by_ticker.setdefault(ticker.upper(), []).append(group)

    def _index_index_leadership(self, data: dict) -> None:
        tabs = data.get("tabs") or {}
        if not isinstance(tabs, dict):
            return
        for tab_name, tab in tabs.items():
            if not isinstance(tab, dict):
                continue
            las = tab.get("las")
            for row in tab.get("rising", []) or []:
                k = row.get("key")
                if k:
                    self._subkey_lead.setdefault(k, {}).update(
                        running=True, tab=tab_name, las=las,
                        quadrant=row.get("quadrant"))
            for row in tab.get("coiling", []) or []:
                k = row.get("key")
                if k:
                    self._subkey_lead.setdefault(k, {}).setdefault("coiling", True)
                    self._subkey_lead[k].setdefault("tab", tab_name)

    def _index_subsector_rotation(self, data: dict) -> None:
        for s in data.get("subsectors", []) or []:
            for m in s.get("members", []) or []:
                t = m.get("t") or m.get("ticker")
                if t:
                    self._rot_by_ticker.setdefault(t.upper(), []).append(s)

    def _index_baskets(self, data: dict) -> None:
        for b in data.get("baskets", []) or []:
            bid = b.get("id")
            for m in b.get("members", []) or []:
                sym = m.get("symbol") or m.get("ticker")
                if sym and bid:
                    self._basket_by_ticker.setdefault(sym.upper(), []).append(bid)
        ti = data.get("theme_intel") or {}
        for th in (ti.get("themes") or []):
            tid = th.get("id")
            if tid:
                self._theme_by_basket[tid] = th

    # ---- passport --------------------------------------------------------- #
    def source_passport(self) -> dict:
        """One record per source: found / degraded / stale + age. For the board's
        rotation-artifact coverage report and the per-lane passport summary."""
        out = {}
        for key, src in self._sources.items():
            out[key] = {
                "found": src.data is not None,
                "degraded": bool(src.degraded),
                "reason": src.error,
                "as_of": src.as_of,
                "age_days": src.age_days,
                "stale": bool(src.age_days is not None and src.age_days > self.STALE_DAYS),
            }
        return out

    def contract_version(self) -> int:
        return int(READER_CONTRACT["version"])

    def entry_context_contract(self) -> dict:
        """The additive, authority-inert member-routing contract used by Board V2."""
        return self._entry_source.contract()

    def _entry_context_for_member(self, ticker: str, group: dict, member: dict) -> dict:
        eligibility_raw = member.get("stock_eligible")
        member_gate = {
            "tier_cascade": member.get("stock_tier"),
            "weight": member.get("stock_weight"),
            "ticks": member.get("stock_ticks"),
            "bars_to_cross": member.get("stock_bars_to_cross"),
            "state": member.get("stock_state"),
            "reason": member.get("stock_reason"),
            "eligible": (None if eligibility_raw is None else bool(eligibility_raw)),
        }
        relationship = member.get("relationship_kind")
        if not relationship:
            relationship = "PROXY" if member.get("proxy") else "DIRECT_MEMBER"
        group_key = str(group.get("key") or "")
        return self._entry_source.for_member(
            ticker=ticker,
            member_gate=member_gate,
            member_buyable=bool(member.get("stock_buyable")),
            member_eligible=(None if eligibility_raw is None else bool(eligibility_raw)),
            group=group,
            stock_route=f"stock.html#{ticker}",
            group_route=f"subsector/{group_key}.html" if group_key else "subsectors.html",
            relationship_kind=str(relationship),
        )

    # ---- per-name resolution --------------------------------------------- #
    def for_name(self, ticker: str, sector: str | None = None) -> dict:
        """Resolve rotation context for one name.

        Returns a dict:
          leadership : float in [-1, +1]  (0 = neutral / no coverage)
          chips      : list[{label, tone}]  display chips (running, leading, entry-now, ...)
          surfaced_by: list[str]   which rotation surface flagged this name
          components : dict         per-source signed contributions (audit)
          passport   : {frame, freshness, degraded, coverage}  honesty metadata
        Every path degrades to neutral rather than raising.
        """
        tkr = (ticker or "").upper()
        comps: dict[str, float | None] = {}
        weights: dict[str, float] = {}
        chips: list[dict] = []
        surfaced: list[str] = []
        degraded_sources: list[str] = []
        covered = 0

        specs = READER_CONTRACT["sources"]

        # 1) SECTOR CENTRAL — always-present backbone (join on GICS sector name)
        sc = self._sources.get("sector_central")
        sec_row = None
        if sc and not sc.degraded:
            sec_row = self._sector_by_name.get(_norm_sector(sector))
        if sec_row is not None:
            score = _clip_score((sec_row.get("conviction") or {}).get("score"), 0, 100)
            trend_pass = bool((sec_row.get("forward") or {}).get("trend_pass"))
            # conviction 0..100 → -1..+1, nudged by the forward trend gate
            contrib = (score - 50) / 50.0 if score is not None else 0.0
            if not trend_pass:
                contrib = min(contrib, 0.0) - 0.15   # a closed sector trend-gate is a drag
            comps["sector_central"] = round(contrib, 3)
            weights["sector_central"] = specs["sector_central"]["weight"]
            covered += 1
            label = (sec_row.get("conviction") or {}).get("label_en") or "Sector"
            chips.append({"label": f"Sector: {label}",
                          "tone": _tone(contrib), "src": "sector_central"})
        elif sc and sc.degraded:
            degraded_sources.append("sector_central")

        # 2) SUBSECTOR CONFLUENCE — class + entry tier + regime state (join on ticker)
        sub_row = _best_subsector(self._sub_by_ticker.get(tkr))
        sub_key = None
        entry_context = self._entry_source.for_member(
            ticker=tkr,
            member_gate={},
            member_buyable=False,
            group={"source_ref": CONFLUENCE_REF},
            stock_route=f"stock.html#{tkr}",
            group_route="subsectors.html",
            relationship_kind="UNKNOWN",
        )
        conf_src = self._sources.get("subsector_confluence")
        if sub_row is not None:
            sub_key = sub_row.get("key")
            for member in sub_row.get("members", []) or []:
                if not isinstance(member, dict):
                    continue
                if str(member.get("ticker") or "").upper() == tkr:
                    # Rebuild from the current owner fields. Embedded context is not
                    # trusted as authority because an older/foreign producer could
                    # otherwise smuggle rank/gate/trade permissions into this reader.
                    entry_context = self._entry_context_for_member(tkr, sub_row, member)
                    break
            cls = sub_row.get("class")
            reg = ((sub_row.get("regime") or {}).get("state") or "").upper()
            contrib = _CLASS_SCORE.get(cls, 0.0) + _REGIME_TILT.get(reg, 0.0)
            contrib = max(-1.0, min(1.0, contrib))
            comps["subsector_confluence"] = round(contrib, 3)
            weights["subsector_confluence"] = specs["subsector_confluence"]["weight"]
            covered += 1
            if cls == "entry_now":
                chips.append({"label": f"Subsector ENTRY-NOW: {sub_row.get('label')}",
                              "tone": "pos", "src": "subsectors"})
                surfaced.append(f"subsectors:entry_now:{sub_row.get('label')}")
            elif cls == "headwind":
                chips.append({"label": f"Subsector headwind: {sub_row.get('label')}",
                              "tone": "neg", "src": "subsectors"})
        elif conf_src and conf_src.degraded:
            degraded_sources.append("subsector_confluence")

        # 3) INDEX LEADERSHIP — LAS Running / Coiling (join subsector key)
        lead_src = self._sources.get("index_leadership")
        if sub_key and lead_src and not lead_src.degraded:
            lead = self._subkey_lead.get(sub_key)
            if lead:
                if lead.get("running"):
                    comps["index_leadership"] = 0.7
                    weights["index_leadership"] = specs["index_leadership"]["weight"]
                    covered += 1
                    chips.append({"label": "LAS Running", "tone": "pos",
                                  "src": "subsectors_lead"})
                    surfaced.append(f"subsectors_running:{sub_key}")
                elif lead.get("coiling"):
                    comps["index_leadership"] = 0.3
                    weights["index_leadership"] = specs["index_leadership"]["weight"]
                    covered += 1
                    chips.append({"label": "LAS Coiling", "tone": "warm",
                                  "src": "subsectors_lead"})
                    surfaced.append(f"subsectors_coiling:{sub_key}")
        elif lead_src and lead_src.degraded:
            degraded_sources.append("index_leadership")

        # 4) SUBSECTOR ROTATION (RRG) — quadrant + rs_mom (join on ticker)
        rot_row = _best_rotation(self._rot_by_ticker.get(tkr))
        rot_src = self._sources.get("subsector_rotation")
        if rot_row is not None:
            quad = (rot_row.get("quadrant") or "").lower()
            contrib = _QUADRANT_SCORE.get(quad, 0.0)
            # rs_mom sign refines a borderline quadrant
            rs_mom = rot_row.get("rs_mom")
            if isinstance(rs_mom, (int, float)) and abs(contrib) < 0.5:
                contrib += 0.1 if rs_mom > 0 else -0.1
            contrib = max(-1.0, min(1.0, contrib))
            comps["subsector_rotation"] = round(contrib, 3)
            weights["subsector_rotation"] = specs["subsector_rotation"]["weight"]
            covered += 1
            if quad in ("leading", "improving"):
                chips.append({"label": f"RRG {quad.title()}", "tone": "pos",
                              "src": "rotation"})
                if quad == "leading":
                    surfaced.append(f"rotation_leading:{rot_row.get('key')}")
            elif quad in ("lagging", "weakening"):
                chips.append({"label": f"RRG {quad.title()}", "tone": "neg",
                              "src": "rotation"})
        elif rot_src and rot_src.degraded:
            degraded_sources.append("subsector_rotation")

        # 5) BASKETS / THEMES — theme leadership (join on ticker → basket → theme)
        bk_src = self._sources.get("baskets")
        basket_ids = self._basket_by_ticker.get(tkr) or []
        if basket_ids and bk_src and not bk_src.degraded:
            best_theme, best_score = None, None
            for bid in basket_ids:
                th = self._theme_by_basket.get(bid)
                if th and isinstance(th.get("score"), (int, float)):
                    if best_score is None or th["score"] > best_score:
                        best_score, best_theme = th["score"], th
            if best_theme is not None:
                contrib = (best_score - 50) / 50.0
                comps["baskets"] = round(max(-1.0, min(1.0, contrib)), 3)
                weights["baskets"] = specs["baskets"]["weight"]
                covered += 1
                lbl = best_theme.get("label_en") or best_theme.get("label") or "theme"
                chips.append({"label": f"Theme: {lbl}", "tone": _tone(contrib),
                              "src": "baskets"})
                if (best_theme.get("reco_en") or best_theme.get("reco") or "").lower() in (
                        "buy", "accumulate", "add"):
                    surfaced.append(f"baskets_buy:{best_theme.get('id')}")
            elif basket_ids:
                # in a basket but the theme desk had no read → mild membership credit
                comps["baskets"] = 0.0
                weights["baskets"] = specs["baskets"]["weight"]
                covered += 1
        elif bk_src and bk_src.degraded:
            degraded_sources.append("baskets")

        # ---- fuse (weighted mean of PRESENT sources; absent = not diluted) ---
        leadership = _weighted_mean(comps, weights)

        # de-dup chips/surfaced while preserving order
        chips = _dedup(chips, key=lambda c: (c["label"], c["tone"]))
        surfaced = list(dict.fromkeys(surfaced))

        # freshest as_of across the sources that actually contributed
        contrib_ages = [self._sources[k].age_days for k in comps
                        if self._sources.get(k) and self._sources[k].age_days is not None]
        freshness = max(contrib_ages) if contrib_ages else None

        passport = {
            "basis": "rotation-artifacts",
            "frame": "group",
            "freshness": freshness,           # calendar days of the oldest contributing source
            "n": covered,                     # how many of the 5 sources covered this name
            "coverage": round(covered / 5.0, 2),
            "degraded": degraded_sources,     # sources that were missing/stale for THIS build
            "contract_version": READER_CONTRACT["version"],
        }
        return {
            "leadership": round(leadership, 3),
            "state": _state_word(leadership),
            "chips": chips,
            "surfaced_by": surfaced,
            "components": comps,
            "passport": passport,
            "entry_context": entry_context,
        }


# --------------------------------------------------------------------------- #
#  helpers                                                                      #
# --------------------------------------------------------------------------- #
def _clip_score(v: Any, lo: float, hi: float) -> float | None:
    if not isinstance(v, (int, float)):
        return None
    return max(lo, min(hi, float(v)))


def _weighted_mean(comps: dict[str, float | None], weights: dict[str, float]) -> float:
    num = den = 0.0
    for k, v in comps.items():
        if v is None:
            continue
        w = weights.get(k, 0.0)
        num += w * v
        den += w
    if den <= 0:
        return 0.0
    return max(-1.0, min(1.0, num / den))


def _tone(contrib: float) -> str:
    if contrib >= 0.25:
        return "pos"
    if contrib <= -0.25:
        return "neg"
    return "neutral"


def _state_word(x: float) -> str:
    if x >= 0.45:
        return "leading"
    if x >= 0.15:
        return "improving"
    if x <= -0.45:
        return "washed_out"
    if x <= -0.15:
        return "lagging"
    return "neutral"


def _best_subsector(rows: list[dict] | None) -> dict | None:
    """A name can belong to several sub-industries; prefer the strongest class."""
    if not rows:
        return None
    order = {"entry_now": 0, "forming": 1, "headwind": 3}
    return sorted(rows, key=lambda s: order.get(s.get("class"), 2))[0]


def _best_rotation(rows: list[dict] | None) -> dict | None:
    if not rows:
        return None
    order = {"leading": 0, "improving": 1, "weakening": 2, "lagging": 3}
    return sorted(rows, key=lambda s: order.get((s.get("quadrant") or "").lower(), 2))[0]


def _dedup(items: list, key) -> list:
    seen, out = set(), []
    for it in items:
        k = key(it)
        if k not in seen:
            seen.add(k)
            out.append(it)
    return out


# The entry adapter is intentionally colocated with the incumbent group consumer:
# one reader, one contract, no parallel intake or publication plane.

@dataclass(frozen=True, slots=True)
class _EntrySourceRow:
    row: dict[str, Any]
    lane: str
    index: int
    ref: str


class EntryContextSource:
    """Tolerant adapter over stock-setup and Live Entry Radar artifacts."""

    def __init__(self, *, standouts: Mapping[str, Any] | None,
                 radar: Mapping[str, Any] | None, now: date,
                 standouts_error: str | None = None,
                 radar_error: str | None = None) -> None:
        self._standouts = dict(standouts) if isinstance(standouts, Mapping) else None
        self._radar = dict(radar) if isinstance(radar, Mapping) else None
        self._now = now
        self._standouts_error = standouts_error
        self._radar_error = radar_error
        standouts_doc = self._standouts or {}
        radar_doc = self._radar or {}
        radar_pack = (radar_doc.get("pack")
                      if isinstance(radar_doc.get("pack"), Mapping) else {})
        self._standouts_observed_at = _first(standouts_doc, "as_of", "asof")
        self._standouts_available_at = _first(standouts_doc, "available_at")
        self._standouts_computed_at = _first(standouts_doc, "generated_utc", "computed_at")
        self._standouts_published_at = _first(standouts_doc, "published_at")
        self._standouts_as_of = _first(
            {
                "observation": self._standouts_observed_at,
                "availability": self._standouts_available_at,
                "computation": self._standouts_computed_at,
                "publication": self._standouts_published_at,
            },
            "observation", "availability", "computation", "publication",
        )
        self._radar_observed_at = (_first(radar_doc, "session")
                                   or _first(radar_pack, "as_of"))
        self._radar_available_at = _first(radar_doc, "available_at")
        self._radar_computed_at = _first(radar_doc, "asof", "generated_utc", "computed_at")
        self._radar_published_at = _first(radar_doc, "published_at")
        self._radar_as_of = _first(
            {
                "computation": self._radar_computed_at,
                "observation": self._radar_observed_at,
                "availability": self._radar_available_at,
                "publication": self._radar_published_at,
            },
            "computation", "observation", "availability", "publication",
        )
        self._standouts_age = _age_days(self._standouts_as_of, now)
        self._radar_age = _age_days(self._radar_as_of, now)
        self._stock_rows = self._index_stock_rows()
        self._radar_rows = self._index_radar_rows()

    @classmethod
    def from_documents(cls, *, standouts: Mapping[str, Any] | None,
                       radar: Mapping[str, Any] | None,
                       now: date | datetime | None = None) -> "EntryContextSource":
        return cls(standouts=standouts, radar=radar, now=_as_date(now))

    @classmethod
    def from_site(cls, site: Path, *,
                  now: date | datetime | None = None) -> "EntryContextSource":
        site = Path(site)
        standouts, standouts_error = _read_json(
            site / "factordata" / "us_standouts.json")
        radar, radar_error = _read_json(site / "live" / "entry_radar.json")
        return cls(standouts=standouts, radar=radar, now=_as_date(now),
                   standouts_error=standouts_error, radar_error=radar_error)

    def contract(self) -> dict[str, Any]:
        """Versioned consumer receipt; never a signal or ThemeState producer."""
        return {
            "schema": ENTRY_CONTEXT_SCHEMA,
            "context_only": True,
            "permissions": dict(ENTRY_CONTEXT_PERMISSIONS),
            "authority": dict(AUTHORITY_BLOCK),
            "unattached_member_semantics": {
                "state": "DESCRIPTIVE_ONLY",
                "reason": "no_current_stock_setup_record_and_member_gate_not_qualified",
                "absence_scope": STANDOUTS_REF,
                "global_absence": False,
            },
            "sources": {
                "stock_setup": self._artifact_status(
                    self._standouts, STANDOUTS_REF, self._standouts_as_of,
                    self._standouts_age, self._standouts_error),
                "live_entry_radar": self._artifact_status(
                    self._radar, RADAR_REF, self._radar_as_of,
                    self._radar_age, self._radar_error),
            },
        }

    def for_member(self, *, ticker: str,
                   member_gate: Mapping[str, Any] | None,
                   member_buyable: bool, group: Mapping[str, Any],
                   stock_route: str, group_route: str,
                   relationship_kind: str = "DIRECT_MEMBER",
                   member_eligible: bool | None = None) -> dict[str, Any]:
        symbol = str(ticker or "").upper()
        relationship = _relationship_kind(relationship_kind)
        gate = dict(member_gate or {})
        group = dict(group or {})
        src = self._stock_rows.get(symbol)
        availability = self._setup_availability(src)
        setup_signal = dict((src.row.get("signal") or {})) if src else {}
        entry_signal = dict((src.row.get("entry_signal") or {})) if src else {}
        expiry = self._expiry(src, availability, setup_signal, entry_signal)
        setup_q = self._setup_qualification(
            src, availability, setup_signal, expiry["state"])
        member_q = "QUALIFIED" if member_buyable else "NOT_QUALIFIED"
        eligibility_raw = (gate.get("eligible")
                           if member_eligible is None else member_eligible)
        member_eligibility = (
            "UNKNOWN" if eligibility_raw is None
            else "QUALIFIED" if bool(eligibility_raw)
            else "NOT_QUALIFIED"
        )
        confirmation = _confirmation(
            setup_signal, entry_signal, expiry["state"], setup_q)
        group_entry = dict(group.get("entry") or {})
        group_regime = dict(group.get("regime") or {})
        group_state = str(group_regime.get("state") or "UNKNOWN").upper()
        headwind = bool(group_regime.get("headwind"))
        extended = group_state == "EXTENDED"
        group_confirmation = _confirmation(
            group_entry, {}, "ACTIVE",
            "QUALIFIED" if group_entry.get("buyable") else "UNKNOWN")
        levels = {
            "trigger": (_first(entry_signal, "trigger")
                        or _first(entry_signal.get("timing") or {}, "next_trigger")),
            "zone": copy.deepcopy(entry_signal.get("buy_zone")),
            "invalidation": _first(entry_signal, "invalidation", "stop"),
            "chase_above": entry_signal.get("chase_above"),
        }
        routing = _routing_state(
            member_q=member_q, setup_q=setup_q,
            availability=availability, expiry_state=expiry["state"],
            confirmation=confirmation, headwind=headwind, extended=extended,
            relationship=relationship)
        setup_id = _explicit(src.row if src else {}, _ENTRY_ID_KEYS)
        stock_setup = {
            "availability": availability,
            "scope": STANDOUTS_REF,
            "global_absence": False if availability == "NOT_IN_SNAPSHOT" else None,
            "source_lane": src.lane if src else None,
            "source_ref": src.ref if src else STANDOUTS_REF,
            "source_setup_id": setup_id,
            "source_setup_id_reason": (
                None if setup_id is not None else
                "owner_record_has_no_id" if src else "owner_record_not_in_snapshot"),
            "as_of": self._standouts_as_of,
            "age_days": self._standouts_age,
            "status": entry_signal.get("status") if src else None,
            "tier": setup_signal.get("tier_cascade") if src else None,
            "reason": setup_signal.get("reason") if src else None,
        }
        return {
            "schema": ENTRY_CONTEXT_SCHEMA,
            "context_only": True,
            "instrument": {
                "id": symbol,
                "kind": {
                    "DIRECT_MEMBER": "DIRECT_INSTRUMENT",
                    "PROXY": "PROXY_INSTRUMENT",
                }.get(relationship, "UNKNOWN_INSTRUMENT"),
                "market": "US",
            },
            "relationship": {
                "kind": relationship,
                "availability": ("AVAILABLE" if group.get("key")
                                 else "NOT_IN_SNAPSHOT"),
                "absence_scope": group.get("source_ref") or CONFLUENCE_REF,
                "global_absence": False if not group.get("key") else None,
                "group_id": group.get("key"),
                "group_kind": group.get("kind"),
                "group_label": group.get("label"),
            },
            "observation": {
                "market": group.get("market") or "US",
                "timeframe": group.get("timeframe") or "1D",
                "session": group.get("session") or "EOD",
                "horizon": group.get("horizon") or "daily",
                "weighting": group.get("weighting"),
            },
            "qualification": {
                "member_eligibility": member_eligibility,
                "member_gate": member_q,
                "stock_setup": setup_q,
                "member_tier": gate.get("tier_cascade"),
                "member_reason": gate.get("reason"),
                "basis": "member_signal_gate_and_existing_stock_setup",
                "inherited_from_group": False,
            },
            "confirmation": {
                "state": confirmation,
                "group_state": group_confirmation,
                "basis": "owner_fields_only",
            },
            "group_context": {
                "entry_tier": group_entry.get("tier"),
                "entry_buyable": bool(group_entry.get("buyable")),
                "regime_state": group_state,
                "headwind": headwind,
                "extended": extended,
                "as_of": group.get("as_of"),
            },
            "stock_setup": stock_setup,
            "lineage": self._lineage(src),
            "levels": levels,
            "expiry": expiry,
            "prophet": self._prophet(src),
            "live_entry_radar": self._radar_context(symbol),
            "clocks": {
                "stock_setup": _clock_set(
                    observation=self._standouts_observed_at,
                    availability=self._standouts_available_at,
                    computation=self._standouts_computed_at,
                    publication=self._standouts_published_at,
                    owner="artifact",
                ),
                "group": _clock_set(
                    observation=group.get("as_of"),
                    availability=group.get("available_at"),
                    computation=group.get("generated_utc") or group.get("computed_at"),
                    publication=group.get("published_at"),
                    owner="record",
                ),
                "live_entry_radar": _clock_set(
                    observation=self._radar_observed_at,
                    availability=self._radar_available_at,
                    computation=self._radar_computed_at,
                    publication=self._radar_published_at,
                    owner="artifact",
                ),
            },
            "routes": {"instrument": stock_route, "group": group_route},
            "routing": routing,
            "permissions": dict(ENTRY_CONTEXT_PERMISSIONS),
            "authority": dict(AUTHORITY_BLOCK),
        }

    def _index_stock_rows(self) -> dict[str, _EntrySourceRow]:
        out: dict[str, _EntrySourceRow] = {}
        if self._standouts is None:
            return out
        for lane in _ENTRY_LANES:
            rows = self._standouts.get(lane)
            if not isinstance(rows, list):
                continue
            for index, row in enumerate(rows):
                if not isinstance(row, Mapping):
                    continue
                ticker = str(row.get("ticker") or "").upper()
                if ticker and ticker not in out:
                    out[ticker] = _EntrySourceRow(
                        dict(row), lane, index,
                        f"{STANDOUTS_REF}#/{lane}/{index}")
        return out

    def _index_radar_rows(self) -> dict[str, dict[str, Any]]:
        out: dict[str, dict[str, Any]] = {}
        if self._radar is None:
            return out
        for row in self._radar.get("names") or []:
            if not isinstance(row, Mapping):
                continue
            ticker = str(row.get("ticker") or "").upper()
            if ticker:
                out[ticker] = dict(row)
        return out

    def _setup_availability(self, src: _EntrySourceRow | None) -> str:
        if self._standouts is None:
            return "UNAVAILABLE"
        if src is None:
            return "NOT_IN_SNAPSHOT"
        if self._standouts_age is not None and self._standouts_age > ENTRY_CONTEXT_STALE_DAYS:
            return "STALE"
        return "AVAILABLE"

    def _expiry(self, src: _EntrySourceRow | None, availability: str,
                signal: Mapping[str, Any],
                entry_signal: Mapping[str, Any]) -> dict[str, Any]:
        expires_at = None
        if src is not None:
            expires_at = _explicit(src.row, _ENTRY_EXPIRY_KEYS)
            expires_at = expires_at or _explicit(signal, _ENTRY_EXPIRY_KEYS)
            expires_at = expires_at or _explicit(entry_signal, _ENTRY_EXPIRY_KEYS)
        expired = _expired_by_owner(signal, entry_signal, expires_at, self._now)
        if expired:
            state = "EXPIRED"
        elif availability == "STALE":
            state = "STALE"
        elif src is not None and signal_gate.is_buyable(dict(signal)):
            state = "ACTIVE"
        else:
            state = "UNKNOWN"
        return {
            "state": state,
            "expires_at": expires_at,
            "expires_at_reason": (
                None if expires_at is not None
                else "owner_record_has_no_absolute_expiry"),
            "freshness_basis": {
                "ticks": signal.get("ticks"),
                "fresh_bars": signal.get("fresh_bars"),
                "fresh_bars_knowable": signal.get("fresh_bars_knowable"),
                "near_miss_reason": signal.get("near_miss_reason"),
            },
        }

    @staticmethod
    def _setup_qualification(src: _EntrySourceRow | None, availability: str,
                             signal: Mapping[str, Any], expiry_state: str) -> str:
        if src is None or availability in {"UNAVAILABLE", "NOT_IN_SNAPSHOT"}:
            return "UNKNOWN"
        if expiry_state == "EXPIRED":
            return "EXPIRED"
        if availability == "STALE":
            return "STALE"
        return ("QUALIFIED" if signal_gate.is_buyable(dict(signal))
                else "NOT_QUALIFIED")

    @staticmethod
    def _lineage(src: _EntrySourceRow | None) -> dict[str, Any]:
        if src is None:
            return {
                "state": "UNAVAILABLE",
                "source_revision": None,
                "correction_of": None,
                "supersedes": None,
                "source_content_sha256": None,
                "reason": "owner_record_not_in_snapshot",
            }
        row = src.row
        source_revision = _first(row, "revision_seq", "revision")
        correction_of = _first(row, "correction_of")
        supersedes = _first(row, "supersedes")
        source_hash = _first(row, "content_sha256", "source_receipt")
        present = any(value is not None for value in (
            source_revision, correction_of, supersedes, source_hash))
        return {
            "state": "AVAILABLE" if present else "UNAVAILABLE",
            "source_revision": source_revision,
            "correction_of": correction_of,
            "supersedes": supersedes,
            "source_content_sha256": source_hash,
            "reason": None if present else "owner_record_has_no_correction_lineage",
        }

    def _prophet(self, src: _EntrySourceRow | None) -> dict[str, Any]:
        row = dict((src.row.get("prophet") or {})) if src else {}
        return {
            "availability": "AVAILABLE" if row else "UNAVAILABLE",
            "version": row.get("version"),
            "score": row.get("score"),
            "score_kind": row.get("score_kind"),
            "score_authority": row.get("score_authority"),
            "source_ref": src.ref if src and row else None,
            "context_only": True,
        }

    def _radar_context(self, ticker: str) -> dict[str, Any]:
        row = self._radar_rows.get(ticker)
        availability = (
            "UNAVAILABLE" if self._radar is None
            else "STALE" if (
                self._radar_age is not None
                and self._radar_age > ENTRY_CONTEXT_STALE_DAYS
            )
            else "NOT_DETECTED" if row is None
            else "AVAILABLE")
        episodes: list[str] = []
        if row:
            for item in row.get("research_priority") or []:
                if isinstance(item, Mapping) and item.get("episode_id"):
                    episodes.append(str(item["episode_id"]))
        return {
            "availability": availability,
            "scope": RADAR_REF,
            "as_of": self._radar_as_of,
            "state": row.get("state") if row else None,
            "reasons": list(row.get("reasons") or []) if row else [],
            "episode_refs": episodes,
            "context_only": True,
        }

    @staticmethod
    def _artifact_status(doc: Mapping[str, Any] | None, ref: str,
                         as_of: Any, age_days: int | None,
                         error: str | None) -> dict[str, Any]:
        if doc is None:
            state = "UNAVAILABLE"
        elif age_days is not None and age_days > ENTRY_CONTEXT_STALE_DAYS:
            state = "STALE"
        else:
            state = "AVAILABLE"
        return {
            "state": state,
            "ref": ref,
            "as_of": as_of,
            "age_days": age_days,
            "error": error,
        }


def _relationship_kind(value: Any) -> str:
    normalized = str(value or "").strip().upper()
    if normalized in {"DIRECT_MEMBER", "PROXY"}:
        return normalized
    return "UNKNOWN"


def _clock(value: Any, *, reason: str) -> dict[str, Any]:
    return {"value": value, "reason": None if value is not None else reason}


def _clock_set(*, observation: Any, availability: Any, computation: Any,
               publication: Any, owner: str) -> dict[str, Any]:
    prefix = f"owner_{owner}_has_no"
    return {
        "observation": _clock(
            observation, reason=f"{prefix}_observation_clock"),
        "availability": _clock(
            availability, reason=f"{prefix}_availability_clock"),
        "computation": _clock(
            computation, reason=f"{prefix}_computation_clock"),
        "publication": _clock(
            publication, reason=f"{prefix}_publication_clock"),
    }


def _routing_state(*, member_q: str, setup_q: str, availability: str,
                   expiry_state: str, confirmation: str,
                   headwind: bool, extended: bool,
                   relationship: str) -> dict[str, Any]:
    if expiry_state == "EXPIRED" or setup_q == "EXPIRED":
        state = "EXPIRED"
    elif availability == "STALE" or setup_q == "STALE":
        state = "DESCRIPTIVE_ONLY_SETUP_STALE"
    elif availability in {"UNAVAILABLE", "NOT_IN_SNAPSHOT"}:
        state = "DESCRIPTIVE_ONLY_SETUP_UNAVAILABLE"
    elif member_q != "QUALIFIED":
        state = "DESCRIPTIVE_ONLY_MEMBER_INELIGIBLE"
    elif setup_q != "QUALIFIED":
        state = "DESCRIPTIVE_ONLY_SETUP_INELIGIBLE"
    elif relationship == "PROXY":
        state = "DESCRIPTIVE_ONLY_PROXY"
    elif relationship != "DIRECT_MEMBER":
        state = "DESCRIPTIVE_ONLY_RELATIONSHIP_UNKNOWN"
    elif headwind:
        state = "QUALIFIED_GROUP_HEADWIND"
    elif confirmation == "PENDING" and extended:
        state = "QUALIFIED_PENDING_CONFIRMATION_EXTENDED"
    elif confirmation == "PENDING":
        state = "QUALIFIED_PENDING_CONFIRMATION"
    elif extended:
        state = "QUALIFIED_GROUP_EXTENDED"
    else:
        state = "QUALIFIED"
    buy_states = {
        "QUALIFIED",
        "QUALIFIED_PENDING_CONFIRMATION",
        "QUALIFIED_PENDING_CONFIRMATION_EXTENDED",
        "QUALIFIED_GROUP_EXTENDED",
    }
    return {
        "state": state,
        "may_navigate": True,
        "may_present_as_qualified_setup": state in buy_states,
        "may_present_as_headwind_warning": state == "QUALIFIED_GROUP_HEADWIND",
        "rank_effect": "NONE",
        "size_effect": "NONE",
    }


def _confirmation(signal: Mapping[str, Any], entry_signal: Mapping[str, Any],
                  expiry_state: str, qualification: str) -> str:
    if expiry_state == "EXPIRED" or qualification == "EXPIRED":
        return "EXPIRED"
    if qualification == "STALE":
        return "STALE"
    if qualification == "NOT_QUALIFIED":
        return "NOT_APPLICABLE"
    if qualification != "QUALIFIED":
        return "UNKNOWN"
    last = signal.get("last") if isinstance(signal.get("last"), Mapping) else {}
    if last.get("confirmed_date"):
        return "CONFIRMED"
    pending = (
        str(signal.get("sub") or "").lower() == "pending"
        or str(last.get("quality") or "").lower() == "pending"
        or bool(signal.get("provisional"))
        or bool(signal.get("tier_observation_provisional"))
        or str(entry_signal.get("status") or "")
        in {"await_confluence", "buy_soon", "watch"}
        or "pending confirmation" in str(signal.get("reason") or "").lower()
        or "confirmation pending" in str(signal.get("reason") or "").lower()
    )
    if pending:
        return "PENDING"
    return "UNCONFIRMED"


def _expired_by_owner(signal: Mapping[str, Any],
                      entry_signal: Mapping[str, Any],
                      expires_at: Any, now: date) -> bool:
    if str(signal.get("near_miss_reason") or "") == "freshness_expired":
        return True
    reason = str(signal.get("reason") or "").lower()
    if "no longer a fresh entry" in reason or "expired" in reason:
        return True
    if str(entry_signal.get("status") or "").lower() == "expired":
        return True
    expiry_date = _parse_date(expires_at)
    return bool(expiry_date is not None and expiry_date < now)


def _explicit(row: Mapping[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        value = row.get(key)
        if value is None:
            continue
        if isinstance(value, Mapping):
            nested = _first(value, "at", "date", "value", "expires_at")
            if nested is not None:
                return nested
        else:
            return value
    return None


def _first(row: Mapping[str, Any], *keys: str) -> Any:
    if not isinstance(row, Mapping):
        return None
    for key in keys:
        value = row.get(key)
        if value is not None:
            return value
    return None


def _read_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        if not path.is_file():
            return None, "missing"
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, Mapping):
            return None, "invalid_root"
        return dict(raw), None
    except (OSError, ValueError, TypeError) as exc:
        return None, f"read_error:{type(exc).__name__}"


def _as_date(value: date | datetime | None) -> date:
    if value is None:
        return datetime.now(timezone.utc).date()
    if isinstance(value, datetime):
        return value.date()
    return value


def _parse_date(value: Any) -> date | None:
    if value is None:
        return None
    try:
        return datetime.fromisoformat(str(value)[:10]).date()
    except (TypeError, ValueError):
        return None


def _age_days(value: Any, now: date) -> int | None:
    parsed = _parse_date(value)
    if parsed is None:
        return None
    return (now - parsed).days



__all__ = [
    "AUTHORITY_BLOCK",
    "ENTRY_CONTEXT_PERMISSIONS",
    "ENTRY_CONTEXT_SCHEMA",
    "EntryContextSource",
    "GroupContext",
    "READER_CONTRACT",
]
