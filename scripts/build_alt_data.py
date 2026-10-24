"""Build the Alternative Data → Signal Intelligence desk.

DETERMINISTIC + emit + render (no LLM key needed here — the Opus brain runs in its own
gated CI step, engine.altdata_brain, then re-runs this to re-render with the fresh read).
Recomputes the weighted alt-data feed, the per-ticker substrate (with influence-graph
affiliations folded in), the falsifiable ledger, the multi-actor influence graph, the
Mastermind emit, and renders the page. Returns 0 on any error so it can never break the
daily build.
"""
from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jinja2 import Environment, FileSystemLoader  # noqa: E402

from datetime import date  # noqa: E402
from engine import (altdata, altdata_alerts, altdata_brain, altdata_emit,  # noqa: E402
                    altdata_ledger, altdata_picks, altdata_signals, desk_grader)
from engine.influence import graph as influence_graph  # noqa: E402
from engine.qledger_ui import chips_for_desks, load_track_record  # noqa: E402
from lib import config  # noqa: E402
from lib.pages import write_page  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
log = logging.getLogger("build_alt_data")


# The card's "Nd vs prior Nd" window. tests/test_altdata_intel.py pins this
# to the collectors' RECENT_D/PRIOR_D and FOA_RECENT_D/FOA_PRIOR_D
# (collectors/sam_gov.py:45-46, collectors/grants_gov.py:34-35) so the label
# is data, not a hardcoded 90 that can silently drift from the producers.
PIPELINE_WINDOW_DAYS = 90


def theme_pipeline_counts(root: Path | None = None) -> dict:
    """Display-only federal pipeline counts per theme basket (W16-B-FOA).

    Reads the two committed per-theme velocity frames —
    ``data/sam_gov/opp_velocity.parquet`` (producer ``collectors/sam_gov.py``,
    RECENT_D/PRIOR_D) and ``data/grants_gov/foa_velocity.parquet`` (producer
    ``collectors/grants_gov.py``, FOA_RECENT_D/FOA_PRIOR_D), each 90d recent vs
    the prior 90d — plus SAM's per-basket as-of sidecar
    ``data/sam_gov/opp_velocity_meta.json``. A missing or unreadable input is an
    empty frame / empty meta (log.warning, never raise). A count absent from one
    frame stays ``None`` — never 0 — so a one-notice blip can't masquerade as a
    surge or a silence. FOA publishes no as-of; none is invented.

    Numbers for the page ONLY: no z, ratio or rank is computed here, and the
    result never feeds altdata_*, emit, picks or the ledger.

    Returns ``rows`` capped at 15 plus ``total`` (the pre-cap count) so the
    card can say honestly when it truncates; ``window_days`` comes from
    ``PIPELINE_WINDOW_DAYS``. Never raise: a non-dict as-of sidecar costs the
    as-of column, a poison count cell costs that cell — never the card.
    """
    import pandas as pd

    root = root or config.ROOT

    def _velocity(rel: str) -> pd.DataFrame:
        path = root / "data" / rel
        try:
            if not path.exists():
                log.warning("pipeline counts: %s missing — treating as empty", path)
                return pd.DataFrame()
            df = pd.read_parquet(path)
        except Exception as e:  # noqa: BLE001 — display-only, never fatal
            log.warning("pipeline counts: %s unreadable (%s) — treating as empty", path, e)
            return pd.DataFrame()
        if not df.empty and "basket_id" not in df.columns:
            df = df.reset_index()   # producers store basket_id as the index
        return df

    sam = _velocity("sam_gov/opp_velocity.parquet")
    foa = _velocity("grants_gov/foa_velocity.parquet")

    def _by_id(df: pd.DataFrame) -> dict:
        if df.empty or "basket_id" not in df.columns:
            return {}
        return {str(b): rec for b, rec in zip(df["basket_id"], df.to_dict("records"))}

    sam_rows, foa_rows = _by_id(sam), _by_id(foa)

    as_of: dict = {}
    try:
        meta_path = root / "data" / "sam_gov" / "opp_velocity_meta.json"
        if meta_path.exists():
            raw_as_of = json.loads(meta_path.read_text()).get("as_of")
            if isinstance(raw_as_of, dict):
                as_of = raw_as_of     # truthy non-dict (list/str/int) would
            else:                     # escape as AttributeError on .get(b)
                log.warning("pipeline counts: SAM as-of meta is %s, not a "
                            "dict — no as-of", type(raw_as_of).__name__)
    except Exception as e:  # noqa: BLE001
        log.warning("pipeline counts: SAM as-of meta unreadable (%s) — no as-of", e)

    def _count(rec: dict | None, col: str) -> int | None:
        v = (rec or {}).get(col)
        try:      # total: NaN/None -> None; "abc"/inf -> None; never fatal
            if v is None or pd.isna(v):
                return None
            return int(v)
        except (TypeError, ValueError, OverflowError):
            return None

    ids = list(dict.fromkeys([*sam_rows, *foa_rows]))   # union, deterministic order
    rows = [{"basket_id": b,
             "sam_recent": _count(sam_rows.get(b), "recent_count"),
             "sam_prior": _count(sam_rows.get(b), "prior_count"),
             "foa_recent": _count(foa_rows.get(b), "recent_count"),
             "foa_prior": _count(foa_rows.get(b), "prior_count"),
             "sam_as_of": as_of.get(b)} for b in ids]
    rows.sort(key=lambda r: (-(max(r["sam_recent"] or 0, r["foa_recent"] or 0)), r["basket_id"]))
    return {"rows": rows[:15], "total": len(rows),
            "window_days": PIPELINE_WINDOW_DAYS}


def main() -> int:
    try:
        feed = altdata.build_feed()
    except Exception as e:  # noqa: BLE001
        log.warning("alt-data feed failed — skipping (additive): %s", e)
        return 0

    alerts, track, influence, picks, brain, mastermind = [], {}, {}, {}, {}, {}
    try:
        # influence-graph affiliations (deterministic) folded into the convergence substrate
        affiliations = {}
        try:
            affiliations = influence_graph.affiliation_details(influence_graph.load_seed())
        except Exception as e:  # noqa: BLE001
            log.warning("influence affiliations skipped (%s)", e)

        by_ticker = altdata_signals.build(feed, affiliations=affiliations)
        altdata_alerts.rebuild(by_ticker)
        alerts = altdata_alerts.recent(days=30)
        picks = altdata_picks.build_picks(feed, by_ticker)
        track = altdata_ledger.rebuild(by_ticker) or {}

        # W4 outcome spine: adapt the just-rebuilt ledgers (alt-data convergence, US board,
        # desks) into shared prediction rows so the pooling / IC-aware layers can read one
        # signal-id→outcome substrate. Adapter, not a duplicate logger; never fatal.
        try:
            from engine import spine
            rep = spine.rebuild_from_adapters()
            log.info("spine rebuilt from adapters: %s", rep)
        except Exception as e:  # noqa: BLE001
            log.warning("spine rebuild skipped (%s)", e)

        # optional gated LLM extractors — grow the graph w/ candidate edges (no-op w/o key)
        for mod, label in (("engine.influence.extract", "influence"),
                           ("engine.trumpflow.extract", "trumpflow")):
            try:
                __import__(mod, fromlist=["run"]).run()
            except Exception as e:  # noqa: BLE001
                log.warning("%s extractor skipped (%s)", label, e)

        # multi-actor influence graph (cross-referenced w/ the live alt-data)
        influence = influence_graph.build_view(by_ticker) or {}

        # the Opus brain read (from its own prior CI step); empty locally / first run
        brain = altdata_brain.load() or {}
        brain_track = altdata_brain.score() or track

        # the actionable, ranked feed for the Mastermind bot
        mastermind = altdata_emit.build_mastermind(by_ticker, brain, influence, picks,
                                                   brain_track or track) or {}
    except Exception as e:  # noqa: BLE001
        log.warning("alt-data signals/graph/emit step failed (non-fatal): %s", e)

    # UNIFIED FORWARD DESK GRADER (5/10/20/30/60/90d) — snapshot today's surfaced set (main
    # board + broken quarantine, ranked), diff for departures, grade matured names. Degrade-safe.
    grader = {}
    try:
        desk_grader.seed_notes()
        sigs = mastermind.get("signals") or []
        broken = mastermind.get("broken_signals") or []
        rows = ([{"ticker": s.get("ticker"), "rank": i + 1, "score": s.get("signal_score"),
                  "lean": 1, "entry_tier": s.get("entry_tier"), "broken": False}
                 for i, s in enumerate(sigs)]
                + [{"ticker": s.get("ticker"), "rank": None, "score": s.get("signal_score"),
                    "lean": 1, "entry_tier": s.get("entry_tier"), "broken": True}
                   for s in broken])
        today = date.today()
        rep = desk_grader.snapshot_desk("alt_data", rows, today)
        grader = desk_grader.compute("alt_data", today)
        log.info("desk_grader (alt_data): +%d snap, %d departed, %d live",
                 rep.get("n_new", 0), rep.get("n_departed", 0), grader.get("n_snapshots_live", 0))
    except Exception as e:  # noqa: BLE001
        log.warning("desk_grader (alt_data) step failed: %s", e)

    site = config.ROOT / "site"
    site.mkdir(exist_ok=True)
    built = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    env = Environment(loader=FileSystemLoader(str(config.ROOT / "templates")), autoescape=True)

    # qledger honesty chips: read the ledger track-record and derive chip state
    # for each desk rendered on this page.  Never fatal — absent ledger → UNGRADED chips.
    qledger_chips: dict = {}
    try:
        tr = load_track_record(config.ROOT)
        qledger_chips = chips_for_desks(["alt_data"], tr)
    except Exception as e:  # noqa: BLE001
        log.debug("qledger chips skipped (%s)", e)

    pipeline_counts: dict = {}
    try:
        pipeline_counts = theme_pipeline_counts()
    except Exception as e:  # noqa: BLE001 — display-only card, never fatal
        log.warning("theme pipeline counts step failed (non-fatal): %s", e)

    try:
        html = env.get_template("alt_data.html.j2").render(
            feed=feed, alerts=alerts, track=track, influence=influence, picks=picks,
            brain=brain, mastermind=mastermind, generated_utc=built,
            qledger_chips=qledger_chips, desk_grader=grader,
            pipeline_counts=pipeline_counts,
            active_section="research", active_page="alt_data",
        )
    except Exception as e:  # noqa: BLE001
        log.warning("alt-data render failed — skipping (additive): %s", e)
        return 0
    write_page(site / "alt_data.html", html)
    n_conv = len(feed.get("signals", {}).get("convergence", []))
    n_sig = len(mastermind.get("signals", []))
    log.info("wrote %s/alt_data.html (%d convergence, %d emitted signals, %d KB)",
             site, n_conv, n_sig, len(html) // 1024)
    return 0


if __name__ == "__main__":
    sys.exit(main())
