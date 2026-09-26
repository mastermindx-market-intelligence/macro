"""Build the subsector-rotation feed.

Reads the committed Finviz themes snapshot (``data/themes_heatmap/*.json``,
refreshed by ``scripts/fetch_finviz_themes.py``) and writes
``site/marketdata/subsector_rotation.json`` consumed by
``site/subsector_rotation.html``. Offline-safe — the snapshot is the source.

    python -m scripts.build_subsector_rotation
"""
from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine import subsector_rotation as sr  # noqa: E402
from lib import config  # noqa: E402
from lib.nyse_calendar import expected_last_session, is_session  # noqa: E402

log = logging.getLogger("build_subsector_rotation")

# Bounded Lane C first vertical. Semiconductors is already consumed by the
# ai_semiconductors, memory_storage and semicap_equipment ThemeState rows. Other
# source-native cohorts (servers, storage and telecom infrastructure) remain
# measured coverage evidence until the incumbent identity/ontology owner maps them.
CLOSED_SESSION_PARENT_KEYS = frozenset({"Semiconductors"})


def _data(*parts: str) -> Path:
    return config.data_dir().joinpath(*parts)



def _completed_session_asof(
    market_bars,
    requested_asof: str | None,
    *,
    now_utc: datetime | None = None,
) -> str | None:
    """Resolve the latest owner bar the canonical NYSE clock considers completed.

    ``lib.nyse_calendar`` owns holidays, one-off closures and the 17:00 ET
    close-plus-settle boundary. Requested dates and future owner bars are capped;
    no calendar-day filling is performed.
    """
    if market_bars is None:
        return None
    if isinstance(market_bars, pd.Series):
        close = market_bars
    elif isinstance(market_bars, pd.DataFrame) and "close" in market_bars:
        close = market_bars["close"]
    else:
        return None
    close = pd.to_numeric(close, errors="coerce").dropna()
    if close.empty:
        return None
    idx = pd.DatetimeIndex(close.index)
    if idx.tz is not None:
        idx = idx.tz_localize(None)
    idx = pd.DatetimeIndex(idx.normalize()).drop_duplicates().sort_values()
    idx = pd.DatetimeIndex([stamp for stamp in idx if is_session(stamp.date())])
    if idx.empty:
        return None

    completed = pd.Timestamp(expected_last_session(now_utc)).normalize()
    requested = pd.Timestamp(requested_asof).normalize() if requested_asof else completed
    target = min(requested, completed, idx[-1])
    eligible = idx[idx <= target]
    return eligible[-1].date().isoformat() if len(eligible) else None


def _build_closed_session_leadership(
    tree: list,
    *,
    requested_asof: str | None,
    now_utc: datetime | None = None,
    loader=None,
    parent_keys: set[str] | frozenset[str] = CLOSED_SESSION_PARENT_KEYS,
) -> dict:
    """Load only the bounded owner tapes and compute the pure Lane C observation."""
    if loader is None:
        from engine import basket_index
        loader = basket_index._load_member_ohlcv

    market = loader("SPY")
    completed_asof = _completed_session_asof(market, requested_asof, now_utc=now_utc)
    if completed_asof is None:
        return _unavailable_closed_session_leadership(
            requested_asof=requested_asof,
            reason="NO_COMPLETED_SESSION",
            requested_themes=parent_keys,
        )
    selected = [
        th for th in tree
        if str(th.get("theme") or th.get("key") or "").strip() in set(parent_keys)
    ]
    tickers = sorted({
        str(t).strip().upper()
        for th in selected for sub in (th.get("subsectors") or [])
        for t in (sub.get("members") or []) if str(t).strip()
    })
    frames = {}
    for ticker in tickers:
        frame = loader(ticker)
        if frame is not None:
            frames[ticker] = frame
    result = sr.compute_closed_session_leadership(
        selected, frames, market, asof=completed_asof, parent_keys=set(parent_keys)
    )
    result["requested_themes"] = sorted(set(parent_keys))
    return result


def _attach_closed_session_leadership(payload: dict, observation: dict) -> None:
    """Attach measurements to existing theme rows; create no new state producer."""
    by_theme = observation.get("themes") or {}
    for row in payload.get("themes") or []:
        block = by_theme.get(row.get("theme"))
        if block is not None:
            row["leadership_observation"] = block
    meta = {k: v for k, v in observation.items() if k != "themes"}
    meta["covered_themes"] = sorted(by_theme)
    payload["closed_session_leadership"] = meta


def _unavailable_closed_session_leadership(
    *,
    requested_asof: str | None,
    reason: str,
    requested_themes: set[str] | frozenset[str] | None = None,
) -> dict:
    """Visible fail-closed receipt for an unavailable owner-input path."""
    block = sr.compute_closed_session_leadership(
        [], {}, None, asof=requested_asof, parent_keys=set()
    )
    block["requested_asof"] = requested_asof
    block["requested_themes"] = sorted(set(requested_themes or ()))
    block["reason_codes"] = [reason]
    return block


def _stamp_closed_session_metadata(
    observation: dict, *, input_snapshot_asof: str | None, computed_utc: str
) -> None:
    """Add local clocks and source references without claiming Lane A's shared schema."""
    observation["clocks"] = {
        "observation_session": observation.get("asof"),
        "input_snapshot_asof": input_snapshot_asof,
        "computation_utc": computed_utc,
    }
    observation["source_records"] = [
        "data/themes_heatmap/themes_tree.json",
        "engine.basket_index._load_member_ohlcv",
        "lib.nyse_calendar.expected_last_session",
        "lib.nyse_calendar.is_session",
        "SPY",
    ]
    receipt = {
        "schema": observation.get("schema"),
        "benchmark": observation.get("benchmark"),
        "windows_sessions": observation.get("windows_sessions"),
        "basis": observation.get("basis"),
        "permissions": observation.get("permissions"),
        "is_context_only": observation.get("is_context_only"),
        "is_forecast": observation.get("is_forecast"),
        "bar_status": observation.get("bar_status"),
        "clocks": dict(observation["clocks"]),
        "source_records": list(observation["source_records"]),
    }
    for block in (observation.get("themes") or {}).values():
        block["measurement_receipt"] = {
            **receipt,
            "basis": dict(receipt.get("basis") or {}),
            "permissions": dict(receipt.get("permissions") or {}),
            "clocks": dict(receipt["clocks"]),
            "source_records": list(receipt["source_records"]),
        }

def _inject_megacap_node(tree: list, snap: dict) -> None:
    """RC-R4 (Rotation Command): the mega-cap generals cohort has no Finviz group, so
    the 06-25 rotate-IN had no home in this taxonomy — semis' breakdown ranked 255-268
    while the Mag-7 bid could only surface via adjacent proxies. Inject ONE synthetic
    node whose perf comes from the local equal-weight Mag-7 composite (members from
    data/baskets/membership.json — never re-curated here). Quadrant math unchanged;
    the node rides the same cross-sectional metrics as every Finviz group. In-memory
    only; the committed snapshot files are not touched. Degrade-safe."""
    from engine import sector_legs
    members = (sector_legs.load_membership().get("mag7") or {}).get("members") or []
    tickers = [m["ticker"] for m in members if m.get("ticker")]
    if not tickers:
        raise ValueError("mag7 membership empty")
    close, meta = sector_legs._ew_close(tickers)
    if close is None:
        raise ValueError(f"mag7 composite unavailable ({meta})")
    perf = sr.perf_from_close(close, asof=snap.get("asof") or None)
    if not perf:
        raise ValueError("mag7 composite too thin for horizon returns")
    tree.append({"theme": "Mega-Cap", "key": "megacap", "subsectors": [
        {"key": "megacapgenerals", "name": "Mag 7 Generals",
         "description": "Local equal-weight Mag-7 composite (Rotation Command RC-R4) — "
                        "our own store, not a Finviz group",
         "members": tickers}]})
    snap.setdefault("subsector_perf", {})["megacapgenerals"] = perf


def _load_history(limit: int = 40) -> list[dict]:
    """Tail of the append-only PIT archive (``subsector_perf_history.jsonl``).

    Feeds the turn engine's realised volatility, cross-session confirmation and rotation
    tails. Missing or malformed → an empty list; the turn read then runs on today alone and
    every node stays ``vol_cold`` (armable, never confirmable), which is the honest degrade.
    """
    p = _data("themes_heatmap", "subsector_perf_history.jsonl")
    if not p.exists():
        log.warning("subsector_perf_history.jsonl missing — turn read runs cold")
        return []
    rows = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        if r.get("asof") and (r.get("subsectors") or {}):
            rows.append(r)
    return rows[-limit:]


def _sector_history(yahoo_dir: Path, sessions: int = 40) -> list[dict]:
    """Synthesise archive-shaped rows for the 11 SPDR sector ETFs from local parquets.

    The sector cross-section has real daily prices, so its history is *computed* as-of each
    of the last N sessions rather than read from the Finviz archive — the same
    ``perf_from_close`` the synthetic Mag-7 node uses, walked backwards. That gives the
    sector turn read a genuine volatility estimate and real confirmation counts on the very
    first run.
    """
    import pandas as pd

    closes: dict[str, "pd.Series"] = {}
    for ticker, _n, _zh in sr.SECTOR_ETFS:
        p = yahoo_dir / f"{ticker}.parquet"
        if not p.exists():
            continue
        try:
            s = pd.read_parquet(p, columns=["close"])["close"].sort_index().dropna()
            if len(s) >= 260:
                closes[ticker] = s
        except Exception as e:  # noqa: BLE001
            log.warning("sector history read failed for %s: %s", ticker, e)
    if not closes:
        return []
    # Session calendar = the union of dates, so a ticker with a short gap still lines up.
    cal = sorted(set().union(*[set(s.index) for s in closes.values()]))[-sessions:]
    rows = []
    for day in cal:
        asof = pd.Timestamp(day).strftime("%Y-%m-%d")
        per = {}
        for ticker, s in closes.items():
            perf = sr.perf_from_close(s, asof=asof)
            if perf:
                per[ticker] = perf
        if per:
            rows.append({"asof": asof, "subsectors": per})
    return rows


def _append_jsonl_dedup(path: Path, rows: list[dict], id_of) -> int:
    """Append rows whose id is not already in the file. APPEND-ONLY — never rewrites.

    Rotation Command RC-R2's law: a marker, once written, may be superseded by a later row
    but never re-dated or deleted, or every ledger downstream becomes unfalsifiable. A
    re-run of the same session is therefore a no-op rather than a rewrite.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    seen = set()
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                seen.add(id_of(json.loads(line)))
            except Exception:  # noqa: BLE001
                continue
    fresh = [r for r in rows if id_of(r) not in seen]
    if fresh:
        with path.open("a") as fh:
            for r in fresh:
                fh.write(json.dumps(r, separators=(",", ":"), ensure_ascii=False) + "\n")
    return len(fresh)


_BUCKETS = ("turned_up", "bottoming", "turned_down", "topping")


def _bucket_view(summary: dict | None) -> dict:
    """Just the buckets + counts from a turn summary (keys only, no duplicated rows)."""
    s = summary or {}
    return {k: s.get(k) for k in (*_BUCKETS, "counts")}


def _write_turn_artifacts(site: Path, payload: dict) -> None:
    """``site/marketdata/subsector_turns.json`` + the PIT turn/nomination ledgers.

    The artifact is the desk's turn lane AND the rotation-universe **nomination** feed.
    ``config/rotation_universe.json`` stays frozen: it is pre-registered under
    ``research/ROTATION_UNIVERSE_EXTENSION_PREREG.md`` (registered 2026-07-18, registry hash
    in the doc) and adding series to a pre-registered detector universe would void its
    accrual clock. Nominations accrue their own census here instead, so a future extension
    can adopt a candidate that already has history on the board.
    """
    asof = payload.get("asof") or ""
    tn = payload.get("turn") or {}
    rows_by_key = {s["key"]: s for s in payload.get("subsectors") or []}

    def _slim(k: str) -> dict:
        s = rows_by_key.get(k) or {}
        return {"key": k, "name": s.get("name"), "name_zh": s.get("name_zh"),
                "theme": s.get("theme"), "theme_zh": s.get("theme_zh"),
                "n_members": s.get("n_members"),
                "state": s.get("turn_state"), "since": s.get("turn_since"),
                "label": s.get("turn_label"), "label_zh": s.get("turn_label_zh"),
                "say": s.get("turn_say"), "say_zh": s.get("turn_say_zh"),
                "score": s.get("turn_score"),
                "bottom_score": s.get("bottom_score"), "top_score": s.get("top_score"),
                "persist_up": s.get("persist_up"), "persist_dn": s.get("persist_dn"),
                "legs_up": s.get("legs_up"), "legs_dn": s.get("legs_dn"),
                "breadth": s.get("breadth"),
                "pos_in_range": s.get("pos_in_range"),
                "dd_from_peak": s.get("dd_from_peak"),
                "up_from_trough": s.get("up_from_trough"),
                "rs_pos_in_range": s.get("rs_pos_in_range"),
                "rs_dd_from_peak": s.get("rs_dd_from_peak"),
                "pace": s.get("pace"), "pace_rel": s.get("pace_rel"),
                "rank_v2": s.get("rank_v2"), "rank_score_v2": s.get("rank_score_v2"),
                "perf": s.get("perf")}

    buckets = {b: [_slim(k) for k in (tn.get(b) or [])] for b in _BUCKETS}
    noms = tn.get("nominations") or []
    artifact = {
        "schema": tn.get("schema") or "subsector_rotation.turn.v1",
        "asof": asof, "generated_utc": payload.get("generated_utc"),
        "n_sessions": tn.get("n_sessions"), "warm": tn.get("warm"),
        "counts": tn.get("counts"), "params": tn.get("params"),
        "leg_weights": tn.get("leg_weights"), "market": tn.get("market"),
        "is_context_only": True,
        "universe_note": ("Nominations are candidates raised by this desk's turn read. The "
                          "pre-registered rotation-events universe (config/rotation_universe.json, "
                          "frozen 2026-07-18) is NOT modified by them."),
        "universe_note_zh": ("提名为本轮动台转向研判提出的候选，并不修改已预注册的轮动事件"
                             "标的池（config/rotation_universe.json，2026-07-18 冻结）。"),
        **buckets,
        "nominations": noms,
        "themes": _bucket_view(payload.get("turn_themes")),
        "sectors": _bucket_view(payload.get("turn_sectors")),
    }
    outdir = site / "marketdata"
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "subsector_turns.json").write_text(
        json.dumps(artifact, separators=(",", ":"), ensure_ascii=False))

    if not asof:
        return
    # PIT ledgers — one row per CONFIRMED turn and per nomination, append-only.
    turn_rows = [{"date": asof, "key": r["key"], "name": r.get("name"),
                  "theme": r.get("theme"), "state": r.get("state"),
                  "since": r.get("since"), "score": r.get("score"),
                  "n_members": r.get("n_members"),
                  "breadth": (r.get("breadth") or {}).get("turn_up" if r.get("state") == "turn_up"
                                                          else "turn_dn"),
                  "dd_from_peak": r.get("dd_from_peak"),
                  "up_from_trough": r.get("up_from_trough")}
                 for b in ("turned_up", "turned_down") for r in buckets[b]]
    n_t = _append_jsonl_dedup(_data("subsector_rotation", "turns.jsonl"), turn_rows,
                              lambda r: f"{r.get('date')}|{r.get('key')}|{r.get('state')}")
    nom_rows = [{"date": asof, "theme": n.get("theme"),
                 "donor": (n.get("donor") or {}).get("key"),
                 "receiver": (n.get("receiver") or {}).get("key"),
                 "confidence": n.get("confidence"),
                 "both_confirmed": n.get("both_confirmed")} for n in noms]
    n_n = _append_jsonl_dedup(_data("subsector_rotation", "universe_nominations.jsonl"),
                              nom_rows,
                              lambda r: f"{r.get('date')}|{r.get('donor')}|{r.get('receiver')}")
    log.info("turn ledgers: +%d turns, +%d nominations (append-only)", n_t, n_n)


def build(site: Path | None = None, *, generated_utc: str | None = None) -> dict:
    site = site or (config.ROOT / config.load()["storage"]["site_dir"])
    tree = json.loads(_data("themes_heatmap", "themes_tree.json").read_text())
    snap = json.loads(_data("themes_heatmap", "perf_snapshot.json").read_text())

    # RC-R4: synthetic mega-cap node (additive, never fatal — a failed injection
    # leaves the desk exactly as it was before Rotation Command).
    try:
        _inject_megacap_node(tree, snap)
    except Exception as e:  # noqa: BLE001
        log.warning("mega-cap node injection failed: %s", e)

    generated_utc = generated_utc or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    payload = sr.compute_rotation(
        tree,
        snap.get("subsector_perf") or {},
        snap.get("member_perf") or {},
        generated_utc=generated_utc,
        asof=snap.get("asof") or "",
        history=_load_history(),
    )

    # Lane C closed-session leadership/reacceleration observation. It consumes
    # existing owner tapes, stays descriptive/shadow, and never changes incumbent
    # ranking, turn, alert or trading-policy fields. Failure remains visible.
    try:
        leadership = _build_closed_session_leadership(
            tree, requested_asof=snap.get("asof") or None
        )
    except Exception as e:  # noqa: BLE001 — additive, never fatal
        log.warning("closed-session leadership failed: %s", e)
        leadership = _unavailable_closed_session_leadership(
            requested_asof=snap.get("asof") or None,
            reason="OWNER_INPUT_LOAD_FAILED",
            requested_themes=CLOSED_SESSION_PARENT_KEYS,
        )
    _stamp_closed_session_metadata(
        leadership, input_snapshot_asof=snap.get("asof") or None,
        computed_utc=generated_utc,
    )
    _attach_closed_session_leadership(payload, leadership)
    log.info(
        "closed-session leadership: status=%s asof=%s themes=%s",
        leadership.get("status"), leadership.get("asof"),
        ",".join(sorted((leadership.get("themes") or {}).keys())),
    )
    tn = payload.get("turn") or {}
    if tn.get("counts"):
        log.info("turn read: %d sessions (warm=%s) — up %d/%d, down %d/%d, %d nominations",
                 tn.get("n_sessions") or 0, tn.get("warm"),
                 tn["counts"].get("turn_up", 0), tn["counts"].get("bottoming", 0),
                 tn["counts"].get("turn_down", 0), tn["counts"].get("topping", 0),
                 len(tn.get("nominations") or []))
    else:
        log.warning("turn read produced no states — desk falls back to the incumbent read")

    # Forward TRACK-RECORD (additive, degrade-safe): log today's calls with their
    # FROZEN member baskets, then grade every matured past call. The read becomes
    # falsifiable — context-only, never sizes; verdict stays 'accruing' for months.
    try:
        from engine import subsector_track_record as strk
        member_map = {sub.get("key"): (sub.get("members") or [])
                      for th in tree for sub in th.get("subsectors", [])}
        asof_date = snap.get("asof") or datetime.now(timezone.utc).date().isoformat()
        n_logged = strk.snapshot(payload, member_map, today=asof_date)
        tr = strk.compute(today=asof_date)
        # PUBLISH GUARD (2026-08-03 experiments audit): the note is the only sentence from
        # this ledger a reader sees, and it rides a runtime JSON fetch that the BC-2 claim
        # gate structurally cannot scan. Audit it against its OWN disclosed numbers before it
        # leaves the builder; an unbacked note is withdrawn to the honest 'measuring' copy
        # rather than shipped. compute() cannot currently produce one — this fires only if a
        # future gate change re-opens the hole, which is exactly when nobody is looking.
        viol = strk.withdraw_unbacked_note(tr)
        if viol:
            print("::error title=subsector_rotation::track-record note was not backed by its "
                  f"own numbers and has been withdrawn — {viol}", flush=True)
        payload["track_record"] = tr
        _data("subsector_rotation", "track_record.json").write_text(json.dumps(tr, indent=2))
        log.info("track record: +%d snapshots, %d days logged, verdict=%s",
                 n_logged, tr.get("n_days"), tr.get("verdict"))
    except Exception as e:  # noqa: BLE001 — additive, never fatal
        log.warning("track record failed: %s", e)

    # Sector ETF cross-section (additive — degrade-safe).
    try:
        sector_perf = sr.compute_sector_etf_perf(_data("yahoo"))
        if sector_perf:
            sector_metrics = sr._rotation_metrics(sector_perf)
            sectors_array = sr.build_sectors_array(sector_metrics)
            # Sector turn read off REAL daily prices (see _sector_history).
            payload["turn_sectors"] = sr.attach_turn(
                sectors_array, sector_perf,
                history=_sector_history(_data("yahoo")),
                asof=payload.get("asof"), min_members=1)
            payload["sectors"] = sectors_array
            payload["n_sectors"] = len(sectors_array)
            st_counts = (payload["turn_sectors"] or {}).get("counts") or {}
            log.info("sector ETFs: %d rows, quadrants=%s, turn=%s",
                     len(sectors_array),
                     {s["quadrant"] for s in sectors_array},
                     {k: v for k, v in st_counts.items() if v})
        else:
            log.warning("sector ETF perf empty — omitting sectors from payload")
    except Exception as e:  # noqa: BLE001 — additive, never fatal
        log.warning("sector ETF build failed: %s", e)

    # Turn artifact + append-only PIT ledger (additive, degrade-safe).
    try:
        _write_turn_artifacts(site, payload)
    except Exception as e:  # noqa: BLE001 — additive, never fatal
        log.warning("turn artifacts failed: %s", e)

    # Sector Intelligence consolidation (2026-08): on the US SURFACE "Themes" means the 47
    # curated baskets (rendered by the merged page's own map), so the Finviz-taxonomy themes
    # UNIT is hidden in the UI — flag-driven, because the themes ARRAY itself stays a data
    # product (engine/neuralweb/thematic_state.py reads it for quadrant rollups). The shared
    # renderer hides the toggle when themes_unit is false; China's feed (no flag) keeps its
    # THS-concept themes unit. Turn ledgers/turn_themes artifacts unaffected.
    payload["themes_unit"] = False

    outdir = site / "marketdata"
    outdir.mkdir(parents=True, exist_ok=True)
    out = outdir / "subsector_rotation.json"
    out.write_text(json.dumps(payload, separators=(",", ":"), ensure_ascii=False))
    log.info("wrote %s — %d subsectors, %d themes (themes unit hidden; emerging: %s)",
             out, payload["n_subsectors"], payload["n_themes"],
             ", ".join(payload["highlights"]["emerging"][:4]))

    # Change-detection alerts: ping when a subsector rotates in/out (additive).
    try:
        from engine import subsector_rotation_alerts
        fired = subsector_rotation_alerts.rebuild(payload)
        if fired:
            log.info("rotation alerts: %d fired (%s)", len(fired),
                     ", ".join(e["asset"] for e in fired[:5]))
    except Exception as e:  # noqa: BLE001 — additive, never fatal
        log.warning("rotation alerts failed: %s", e)
    return payload


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    build()
    return 0


if __name__ == "__main__":
    sys.exit(main())
