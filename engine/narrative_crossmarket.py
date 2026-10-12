"""Cross-country narrative cross-reference — DISPLAY-ONLY, heavily gated.

The question the user asked: "is a narrative heating up in one market while still emerging in
another — an early-detection / cross-market read?" The honest research verdict was BUILD-LIMITED:
the phenomenon is real (a theme that leads in one market often shows up in another) but it is
NOT tradeable as a lead-lag signal — cross-market thematic momentum is broadly CONTEMPORANEOUS
(~94% same-period), dies past trading costs, and thematic ETFs bleed. So this engine produces a
DISPLAY-ONLY cross-reference chip, never a scored signal and never an axis, with three hard gates
that encode the user's own caveats:

  1. REGION-SPECIFICITY EXCLUSION. Only genuinely cross-applicable, globally-traded themes are in
     the canon crosswalk (semis, software/AI, defense, robotics, gold, base metals, energy,
     autos/EV, pharma, nuclear, luxury). Region-specific themes — banks, insurers, housing/REITs,
     utilities, telecom, gaming, baijiu, SOE value, the regional sleeves — are deliberately absent,
     so they never get a chip. Domestic credit/rates/regulation don't transfer.
  2. MACRO-REGIME ALIGNMENT. Each market's macro Quad is read; a cross-reference between two
     markets in DIFFERENT regimes is flagged (regime_caveat) so the same theme in a different
     regime isn't read as the same trade.
  3. CO-LISTING / FX caveats. China↔Hong Kong links are flagged (co_listed) because A/H names are
     largely the same companies; a standing FX / market-access caveat rides in the disclaimer.

The output is a per-(region, theme) map of "the same narrative elsewhere" — the other markets'
analog theme with its live score/label, so a user can spot a narrative that is already hot
abroad. Pure read; nothing here feeds a score or an allocation.
"""
from __future__ import annotations

import hashlib
import json
import logging
import math
from datetime import date, datetime, timezone
from pathlib import Path

from lib import cn_calendar, config, nyse_calendar

log = logging.getLogger(__name__)

# Canonical cross-market themes → the analog basket ids in each market. ONLY globally-traded,
# cross-applicable narratives belong here (gate 1: region-specificity exclusion). Curated by hand
# against each market's membership.json.
CANON: dict[str, dict] = {
    "semiconductors": {"en": "Semiconductors", "zh": "半导体",
                       "regions": {"us": ["ai_semiconductors", "semicap_equipment"],
                                   "china": ["cn_semis", "cn_ai_compute"],
                                   "intl": ["intl_semis", "intl_tech_hw"]}},
    "software_ai":    {"en": "Software & AI", "zh": "软件与AI",
                       "regions": {"us": ["ai_software", "non_ai_software"],
                                   "china": ["cn_software"], "canada": ["ca_tech"],
                                   "intl": ["intl_software"]}},
    "defense":        {"en": "Defense & Aerospace", "zh": "国防与航空航天",
                       "regions": {"us": ["defense"], "china": ["cn_defense"], "intl": ["intl_defense"]}},
    "robotics":       {"en": "Robotics & Automation", "zh": "机器人与自动化",
                       "regions": {"us": ["robotics_automation"], "china": ["cn_robotics"],
                                   "intl": ["intl_automation"]}},
    "gold":           {"en": "Gold Miners", "zh": "黄金矿业",
                       "regions": {"us": ["gold_miners"], "china": ["cn_gold"],
                                   "canada": ["ca_gold"]}},
    "base_metals":    {"en": "Base Metals & Mining", "zh": "基本金属与矿业",
                       "regions": {"china": ["cn_metals"], "hk": ["hk_materials"],
                                   "canada": ["ca_base_metals"], "intl": ["intl_mining"]}},
    "energy":         {"en": "Energy (Oil & Gas)", "zh": "能源(油气)",
                       "regions": {"us": ["energy_complex"], "hk": ["hk_energy"],
                                   "canada": ["ca_oil_gas"], "intl": ["intl_energy"]}},
    "autos_ev":       {"en": "Autos & EV", "zh": "汽车与电动车",
                       "regions": {"china": ["cn_autos", "cn_battery"], "hk": ["hk_ev"],
                                   "intl": ["intl_autos"]}},
    "pharma":         {"en": "Pharma & Biotech", "zh": "制药与生物科技",
                       "regions": {"china": ["cn_pharma_cxo", "cn_med_devices"], "hk": ["hk_biotech"],
                                   "intl": ["intl_pharma"]}},
    "nuclear":        {"en": "Nuclear & Uranium", "zh": "核能与铀",
                       "regions": {"us": ["nuclear_power"], "canada": ["ca_uranium"]}},
    "luxury":         {"en": "Luxury & Consumer Brands", "zh": "奢侈品与消费品牌",
                       "regions": {"hk": ["hk_consumer"], "intl": ["intl_luxury"]}},
}

REGION_META: dict[str, dict] = {
    "us":     {"flag": "🇺🇸", "en": "US", "zh": "美国", "dir": "basket"},
    "china":  {"flag": "🇨🇳", "en": "China", "zh": "中国", "dir": "basket_china"},
    "hk":     {"flag": "🇭🇰", "en": "Hong Kong", "zh": "香港", "dir": "basket_hk"},
    "canada": {"flag": "🇨🇦", "en": "Canada", "zh": "加拿大", "dir": "basket_canada"},
    "intl":   {"flag": "🌍", "en": "International", "zh": "国际", "dir": "basket_intl"},
}

# site/<dir>/baskets.json carrying each market's theme_intel
_BASKETS_DATA = {"us": "basketdata", "china": "chinabasketdata", "hk": "hkbasketdata",
                 "canada": "canadabasketdata", "intl": "intlbasketdata"}


def _load_themes(site, region: str) -> dict:
    """region's {bid: slim theme} from site/<dir>/baskets.json (theme_intel). {} on miss."""
    p = site / _BASKETS_DATA[region] / "baskets.json"
    if not p.exists():
        return {}
    try:
        ti = (json.loads(p.read_text()).get("theme_intel") or {})
    except Exception:  # noqa: BLE001
        return {}
    out = {}
    for t in ti.get("themes", []):
        out[t["id"]] = {
            "name": t.get("name"), "name_zh": t.get("name_zh", t.get("name")),
            "score": t.get("score"), "label": t.get("label"), "reco": t.get("reco"),
            "rel20": (t.get("perf") or {}).get("20d", {}).get("rel"),
            "accel": t.get("accel_z"),
        }
    return out


def _quad(region: str) -> str | None:
    """The market's macro Quad (regime) for the alignment gate. US → data/regime; others →
    data/<region>_regime. Intl has no single regime snapshot → None (never claims alignment)."""
    grp = "regime" if region == "us" else f"{region}_regime"
    p = config.data_dir() / grp / "latest.json"
    if not p.exists():
        return None
    try:
        q = json.loads(p.read_text()).get("quad")
        return str(q) if q else None
    except Exception:  # noqa: BLE001
        return None


def compute_crossmarket(site=None) -> dict:
    """Build the per-(region, theme) 'same narrative elsewhere' map. Display-only, gated."""
    site = Path(site) if site is not None else config.site_dir()
    themes = {r: _load_themes(site, r) for r in REGION_META}
    quads = {r: _quad(r) for r in REGION_META}

    links: dict[str, dict] = {r: {} for r in REGION_META}
    for canon, spec in CANON.items():
        present = []
        for region, bids in spec["regions"].items():
            for bid in bids:
                t = themes.get(region, {}).get(bid)
                if t and t.get("score") is not None:
                    present.append({"region": region, "bid": bid, **t})
        if len(present) < 2:                          # need ≥2 markets for a cross-reference
            continue
        for e in present:
            others = []
            for o in present:
                if o["region"] == e["region"]:
                    continue
                qe, qo = quads.get(e["region"]), quads.get(o["region"])
                others.append({
                    "region": o["region"], "bid": o["bid"], "name": o["name"], "name_zh": o["name_zh"],
                    "score": o["score"], "label": o["label"], "reco": o["reco"],
                    "rel20": o["rel20"], "accel": o["accel"],
                    "regime_caveat": bool(qe and qo and qe != qo),   # gate 2
                    "co_listed": ({e["region"], o["region"]} == {"china", "hk"}),  # gate 3
                })
            if not others:
                continue
            others.sort(key=lambda x: -(x["score"] or 0))
            # "heating up elsewhere": a clearly-stronger, confirmed/emerging analog in another market
            hotter = [o for o in others if (o["score"] or 0) >= (e["score"] or 0) + 8
                      and o["label"] in ("dominant", "emerging") and not o["regime_caveat"]]
            links[e["region"]][e["bid"]] = {
                "canon": canon, "canon_en": spec["en"], "canon_zh": spec["zh"],
                "others": others,
                "hotter_elsewhere": list(dict.fromkeys(o["region"] for o in hotter)),  # unique, ordered
            }

    return {
        "as_of": _as_of(site),
        "regions": REGION_META, "quads": quads, "links": links,
        # Separate source-bound observations, never a replacement for link/rank semantics.
        "china_us_context": compute_china_us_context(site),
        "disclaimer": {
            "en": ("Display-only narrative cross-reference — NOT a validated signal and never scored. "
                   "It flags when the SAME globally-traded theme is also scoring well in another "
                   "market (useful to spot a narrative early), but cross-market thematic momentum is "
                   "broadly contemporaneous — no reliable lead-lag, and it dies past trading costs. "
                   "Region-specific themes (banks, housing, utilities, telecom, gaming) are excluded. "
                   "⚠ = the two markets are in different macro regimes; ⇄ = co-listed A/H names "
                   "(China↔HK). Cross-border investing also carries FX and market-access frictions."),
            "zh": ("仅展示的叙事交叉参考 — 并非经验证的信号，从不计分。当同一全球性主题在另一市场也"
                   "表现强劲时给出提示（有助于尽早发现叙事），但跨市场主题动量大体同期 — 无可靠领先滞后，"
                   "且在交易成本后消失。区域特定主题（银行、住房、公用事业、电信、博彩）已排除。"
                   "⚠＝两市场处于不同宏观周期；⇄＝A/H 同源股票（中国↔香港）。跨境投资还涉及汇率与市场准入摩擦。"),
        },
    }


def _as_of(site) -> str | None:
    for r in ("us", "china", "intl"):
        p = site / _BASKETS_DATA[r] / "baskets.json"
        if p.exists():
            try:
                a = (json.loads(p.read_text()).get("theme_intel") or {}).get("as_of")
                if a:
                    return a
            except Exception:  # noqa: BLE001
                pass
    return None


# The China intelligence consumer reuses CANON, not a second ontology or ranker.
# A current observation receipt is not proof of historical publication availability.
CHINA_US_CONTEXT_SCHEMA = "narrative_crossmarket.china_us_context.v1"
CONTEXT_AUTHORITY = {
    "is_context_only": True, "may_rank": False, "may_gate": False,
    "may_size": False, "may_escalate": False, "may_trade": False,
}


def _context_utc(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("cross-market observation clocks require an explicit timezone")
    return value.astimezone(timezone.utc)


def _context_number(value):
    if isinstance(value, bool) or not isinstance(value, (float, int)):
        return None
    try:
        return value if math.isfinite(value) else None
    except (ValueError, OverflowError):
        return None


def _context_dict(value) -> dict:
    return value if isinstance(value, dict) else {}


def _context_theme(row: dict) -> dict:
    """Retain local producer judgments; never infer buyability from foreign strength."""
    score = _context_number(row.get("score"))
    if score is not None and not 0 <= score <= 100:
        score = None
    label = row.get("label") if isinstance(row.get("label"), str) else None
    reco = row.get("reco") if isinstance(row.get("reco"), str) else None
    positive_label, positive_reco = label in {"dominant", "emerging"}, reco in {"enter", "accumulate"}
    negative_label, negative_reco = label in {"fading", "deteriorating"}, reco in {"trim", "avoid"}
    if score is None:
        stance = "unconfirmed"
    elif (positive_label and negative_reco) or (negative_label and positive_reco):
        stance = "conflicting"
    elif negative_label or negative_reco:
        stance = "defensive"
    elif positive_label and positive_reco:
        stance = "constructive"
    else:
        stance = "unconfirmed"
    perf = _context_dict(row.get("perf"))
    texture = _context_dict(_context_dict(row.get("textures")).get("clean_entry"))
    flag = texture.get("flag")
    return {
        "id": row["id"],
        "name": row.get("name") if isinstance(row.get("name"), str) else row["id"],
        "score": score, "label": label, "reco": reco, "stance": stance,
        "clean_entry": flag if isinstance(flag, bool) else None,
        "rel5": _context_number(_context_dict(perf.get("5d")).get("rel")),
        "rel20": _context_number(_context_dict(perf.get("20d")).get("rel")),
        "accel_z": _context_number(row.get("accel_z")),
    }


def _context_market(site: Path, region: str, observed: datetime, cutoff: datetime) -> tuple[dict, dict]:
    """One byte-bound live read, checked against the existing exchange calendar.

    Date-only daily artifacts cannot prove historical availability. Never use a
    filesystem mtime or today's contents to fill a past decision's information set.
    Session finalization buffers deliberately follow the existing calendar owner.
    """
    calendar = nyse_calendar if region == "us" else cn_calendar
    expected = calendar.expected_last_session(cutoff)
    relpath = f"{_BASKETS_DATA[region]}/baskets.json"
    receipt = {
        "path": f"site/{relpath}", "sha256": None, "observation_session": None,
        "expected_session": expected.isoformat(), "observed_at_utc": observed.isoformat(),
        "status": "MISSING", "availability_basis": "current_read_only",
    }
    if observed > cutoff:
        receipt["status"] = "OBSERVED_AFTER_CUTOFF"
        return {}, receipt
    if cutoff > observed:
        receipt["status"] = "FUTURE_CUTOFF"
        return {}, receipt
    try:
        raw = (site / relpath).read_bytes()
    except FileNotFoundError:
        return {}, receipt
    except OSError:
        receipt["status"] = "UNREADABLE"
        return {}, receipt
    receipt["sha256"] = hashlib.sha256(raw).hexdigest()
    try:
        payload = json.loads(raw)
    except (ValueError, UnicodeDecodeError):
        receipt["status"] = "INVALID_SOURCE"
        return {}, receipt
    ti = _context_dict(payload).get("theme_intel")
    if not isinstance(ti, dict) or not isinstance(ti.get("themes"), list):
        receipt["status"] = "INVALID_SOURCE"
        return {}, receipt
    as_of = ti.get("as_of")
    try:
        if not isinstance(as_of, str) or len(as_of) != 10:
            raise ValueError("daily observation identity required")
        session = date.fromisoformat(as_of)
    except ValueError:
        receipt["status"] = "INVALID_SESSION"
        return {}, receipt
    receipt["observation_session"] = as_of
    if not calendar.is_session(session):
        receipt["status"] = "NON_SESSION"
        return {}, receipt
    if session > expected:
        receipt["status"] = "UNSETTLED_SESSION"
        return {}, receipt
    if session < expected or ti.get("stale") is True:
        receipt["status"] = "STALE"
        return {}, receipt
    rows = {}
    for row in ti["themes"]:
        if not isinstance(row, dict) or not isinstance(row.get("id"), str) or not row["id"].strip():
            receipt["status"] = "INVALID_SOURCE"
            return {}, receipt
        bid = row["id"]
        if bid in rows:
            receipt["status"] = "DUPLICATE_ID"
            return {}, receipt
        rows[bid] = _context_theme(row)
    receipt["status"] = "CURRENT"
    receipt["theme_count"] = len(rows)
    return rows, receipt


def compute_china_us_context(site=None, *, observed_at: datetime | None = None,
                             decision_at: datetime | None = None) -> dict:
    """Source-bound US theme context for the existing China intelligence surface.

    These are separate upstream observations, NOT a scored transmission factor.
    An upstream constructive stance survives absence of a fresh clean-entry flag;
    Chinese defensive/conflicting evidence remains explicit. Nothing here alters
    Buy Now admission, stock eligibility, orders, sizing, or the thesis ledger.
    Clock injection is for deterministic caller/tests, not an archive substitute.
    """
    site = Path(site) if site is not None else config.site_dir()
    observed = _context_utc(observed_at if observed_at is not None else datetime.now(timezone.utc))
    cutoff = _context_utc(decision_at if decision_at is not None else observed)
    us, us_receipt = _context_market(site, "us", observed, cutoff)
    china, cn_receipt = _context_market(site, "china", observed, cutoff)
    result = {
        "schema": CHINA_US_CONTEXT_SCHEMA, **CONTEXT_AUTHORITY,
        "status": "UNAVAILABLE", "decision_at_utc": cutoff.isoformat(),
        "observed_at_utc": observed.isoformat(),
        "sources": {"us": us_receipt, "china": cn_receipt}, "themes": {},
        "crosswalk_sha256": hashlib.sha256(json.dumps(CANON, sort_keys=True).encode()).hexdigest(),
        "validated_lead_lag": False, "historical_availability_proven": False,
        "notes": [
            "US and China observations are not a forecast that China must follow.",
            "Theme analogs do not establish a company-level exposure or entry permission.",
            "A current read is not a point-in-time archive; historical replay requires its existing owner.",
        ],
    }
    if any(r["status"] != "CURRENT" for r in result["sources"].values()):
        return result
    for canon, spec in CANON.items():
        regions = spec["regions"]
        if not regions.get("us") or not regions.get("china"):
            continue
        analogs = [us[bid] for bid in dict.fromkeys(regions["us"]) if bid in us]
        for bid in dict.fromkeys(regions["china"]):
            local = china.get(bid)
            if local is None:
                continue
            state = _context_state(local, analogs)
            result["themes"][bid] = {
                **CONTEXT_AUTHORITY, "local": local, "us_analogs": analogs,
                "observation_state": state,
                "relationship": {"kind": "theme_analog", "canon": canon, "exact_member_link": False},
                "foreign_scores_comparable": False, "requires_local_confirmation": True,
            }
    result["status"] = "CURRENT" if result["themes"] else "NO_MAPPED_CONTEXT"
    return result


def _context_state(local: dict, analogs: list[dict]) -> str:
    if not analogs:
        return "US_SOURCE_UNAVAILABLE"
    positive = any(t["stance"] == "constructive" for t in analogs)
    conflicting = any(t["stance"] == "conflicting" for t in analogs)
    defensive = any(t["stance"] == "defensive" for t in analogs)
    if conflicting or (positive and defensive):
        return "MIXED_US_EVIDENCE"
    if not positive:
        return "NO_CONFIRMED_US_STRENGTH"
    suffix = {"constructive": "CONFIRMING", "unconfirmed": "UNCONFIRMED",
              "defensive": "DEFENSIVE", "conflicting": "CONFLICTING"}[local["stance"]]
    return f"US_STRENGTH_LOCAL_{suffix}"


_CONTEXT_SENTENCES = {
    "US_STRENGTH_LOCAL_CONFIRMING": "U.S. strength with a constructive China theme read",
    "US_STRENGTH_LOCAL_UNCONFIRMED": "U.S. strength; Chinese confirmation is not established",
    "US_STRENGTH_LOCAL_DEFENSIVE": "U.S. strength conflicts with a defensive China theme read",
    "US_STRENGTH_LOCAL_CONFLICTING": "U.S. strength; Chinese inputs disagree",
    "MIXED_US_EVIDENCE": "U.S. analogs disagree; do not treat them as uniform confirmation",
    "NO_CONFIRMED_US_STRENGTH": "no confirmed constructive U.S. analog in this observation",
    "US_SOURCE_UNAVAILABLE": "the mapped U.S. observation is unavailable",
}


def _context_projection_row(raw: dict) -> dict:
    return _context_theme({**raw,
        "perf": {"5d": {"rel": raw.get("rel5")}, "20d": {"rel": raw.get("rel20")}},
        "textures": {"clean_entry": {"flag": raw.get("clean_entry")}}})


def context_for_briefing(payload, *, site=None, observed_at: datetime | None = None) -> dict | None:
    """Consume the published observation without trusting its cached health or prose.

    This is the existing producer's projection adapter, not another score or state store.
    Recheck sessions at consumption and reconstruct qualitative text from source fields.
    """
    if payload is None:
        return None  # legacy artifact; do not fabricate an observed foreign desk
    now = _context_utc(observed_at if observed_at is not None else datetime.now(timezone.utc))
    def unavailable(reason):
        return {"schema": CHINA_US_CONTEXT_SCHEMA, **CONTEXT_AUTHORITY,
                "status": "UNAVAILABLE", "reason": reason, "themes": {},
                "validated_lead_lag": False, "historical_availability_proven": False}
    def authority_ok(row):
        return isinstance(row, dict) and all(row.get(k) is v for k, v in CONTEXT_AUTHORITY.items())
    if not authority_ok(payload) or payload.get("schema") != CHINA_US_CONTEXT_SCHEMA:
        return unavailable("INVALID_CONTEXT_CONTRACT")
    if payload.get("status") not in {"CURRENT", "NO_MAPPED_CONTEXT"}:
        return unavailable("PRODUCER_CONTEXT_UNAVAILABLE")
    crosswalk = hashlib.sha256(json.dumps(CANON, sort_keys=True).encode()).hexdigest()
    if payload.get("crosswalk_sha256") != crosswalk:
        return unavailable("CROSSWALK_CHANGED")
    try:
        producer_time = _context_utc(datetime.fromisoformat(payload["observed_at_utc"]))
        decision_time = _context_utc(datetime.fromisoformat(payload["decision_at_utc"]))
        if producer_time > now or decision_time != producer_time:
            return unavailable("INVALID_OBSERVATION_RECEIPT")
        sources = {}
        for region, calendar in (("us", nyse_calendar), ("china", cn_calendar)):
            receipt = payload["sources"][region]
            expected = calendar.expected_last_session(now).isoformat()
            if receipt.get("status") != "CURRENT" or receipt.get("observation_session") != expected:
                return unavailable("SOURCE_SESSION_NO_LONGER_CURRENT")
            if _context_utc(datetime.fromisoformat(receipt["observed_at_utc"])) != producer_time:
                return unavailable("INVALID_OBSERVATION_RECEIPT")
            if (receipt.get("path") != f"site/{_BASKETS_DATA[region]}/baskets.json"
                    or receipt.get("expected_session") != expected
                    or calendar.expected_last_session(producer_time).isoformat() != expected):
                return unavailable("INVALID_OBSERVATION_RECEIPT")
            digest = receipt["sha256"]
            if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
                return unavailable("INVALID_OBSERVATION_RECEIPT")
            sources[region] = {k: receipt[k] for k in (
                "path", "sha256", "observation_session", "expected_session", "observed_at_utc", "status")}
        themes = payload["themes"]
        if not isinstance(themes, dict):
            return unavailable("INVALID_THEME_ROWS")
        allowed = {bid: (canon, spec) for canon, spec in CANON.items()
                   if spec["regions"].get("us") for bid in spec["regions"].get("china", [])}
        if not set(themes).issubset(allowed):
            return unavailable("UNMAPPED_THEME_IDENTITY")
        # A same-session source correction must invalidate cached context too.
        # Reuse the owner producer: one reader/normalizer, no second truth store.
        latest = compute_china_us_context(site, observed_at=now)
        if latest["status"] not in {"CURRENT", "NO_MAPPED_CONTEXT"}:
            return unavailable("SOURCE_CONTENT_UNAVAILABLE")
        if any(latest["sources"][r]["sha256"] != sources[r]["sha256"] for r in sources):
            return unavailable("SOURCE_CONTENT_CHANGED")
        if set(themes) != set(latest["themes"]):
            return unavailable("SOURCE_COVERAGE_MISMATCH")
        out, lines = {}, []
        for bid, row in themes.items():
            canon, spec = allowed[bid]
            if not authority_ok(row) or row["local"]["id"] != bid:
                return unavailable("INVALID_THEME_CONTRACT")
            local = _context_projection_row(row["local"])
            raw_analogs = row["us_analogs"]
            if not isinstance(raw_analogs, list):
                return unavailable("INVALID_THEME_CONTRACT")
            ids = [a["id"] for a in raw_analogs]
            if len(ids) != len(set(ids)) or not set(ids).issubset(spec["regions"]["us"]):
                return unavailable("UNMAPPED_ANALOG_IDENTITY")
            analogs = [_context_projection_row(a) for a in raw_analogs]
            bound = latest["themes"][bid]
            expected_analogs = {a["id"]: a for a in bound["us_analogs"]}
            if set(ids) != set(expected_analogs):
                return unavailable("SOURCE_COVERAGE_MISMATCH")
            if local != bound["local"] or any(a != expected_analogs[a["id"]] for a in analogs):
                return unavailable("SOURCE_ROW_MISMATCH")
            state = _context_state(local, analogs)
            out[bid] = {**CONTEXT_AUTHORITY, "local": local, "us_analogs": analogs,
                        "observation_state": state, "requires_local_confirmation": True,
                        "foreign_scores_comparable": False,
                        "relationship": {"kind": "theme_analog", "canon": canon, "exact_member_link": False}}
            timing = {True: "fresh-entry texture confirmed", False: "fresh-entry texture not confirmed",
                      None: "entry texture unavailable"}[local["clean_entry"]]
            lines.append(f"{bid}: {_CONTEXT_SENTENCES[state]}; {timing}.")
    except (KeyError, TypeError, ValueError, AttributeError, OverflowError):
        return unavailable("INVALID_OBSERVATION_RECEIPT")
    return {"schema": CHINA_US_CONTEXT_SCHEMA, **CONTEXT_AUTHORITY,
            "status": "CURRENT" if out else "NO_MAPPED_CONTEXT", "themes": out, "sources": sources,
            "observed_at_utc": producer_time.isoformat(), "consumed_at_utc": now.isoformat(),
            "source_content_verified": True,
            "validated_lead_lag": False, "historical_availability_proven": False,
            "summary": ("US–CHINA THEME CONTEXT (observations, not a forecast): " + " ".join(lines) +
                " Absence of a fresh-entry texture does not establish thesis deterioration or a pullback requirement."
                " Theme context does not grant individual-stock entry, ranking, sizing or trade permission.") if out else None}
