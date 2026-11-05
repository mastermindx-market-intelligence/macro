"""Build the Fed & Policy Watch page -> site/policy_watch.html.

A realpolitik, interest-driven intelligence layer on the Fed and the Administration.
Reads a curated, source-grounded substrate (data/policy/intel.json) and renders:
  - the coordinated-regime thesis + market-relevant narrative-vs-revealed divergence,
  - the Fed under Warsh (profile + 5 reform task forces as dated, falsifiable items),
  - the Administration's grand strategy (verified levers + clearly-labeled priors),
  - a capital-rotation map (targeted vs starved, mechanism + proxy tickers),
  - an ACCOUNTABLE falsifiable-prediction ledger (each with a check-by date + status),
  - a monitor list of highest-signal sources, plus sources & honest caveats.

Everything is display-only / context-only and labels FACT vs INFERENCE vs PRIOR. The
prediction ledger is the accountability spine: outcomes get scored over time so the
qualitative layer earns (or loses) a track record instead of being vibes.

Additive — if intel.json is missing the page is skipped, never breaking the build.

Usage: python -m scripts.build_policy_watch
"""
from __future__ import annotations

import json
import logging
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from jinja2 import Environment, FileSystemLoader

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib import config  # noqa: E402
from lib.pages import write_page  # noqa: E402
from engine.policy_watch_current import build_current  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("build_policy_watch")


def brief(text: object, limit: int = 160) -> str:
    """Return one readable sentence for the glance layer.

    The policy substrate intentionally keeps full research notes.  The public
    page should not dump those notes into every card, so this helper preserves
    the first complete thought and applies a word-safe cap when that thought is
    still too long.  Full records remain available in the closed detail layer.
    """
    value = re.sub(r"\s+", " ", str(text or "")).strip()
    if not value or len(value) <= limit:
        return value
    sentence = re.split(r"(?<=[.!?。！？])\s*", value, maxsplit=1)[0].strip()
    candidate = sentence if 24 <= len(sentence) <= limit else value[: limit + 1]
    if len(candidate) <= limit:
        return candidate
    clipped = candidate[:limit].rstrip()
    if " " in clipped and not re.search(r"[\u3400-\u9fff]", clipped):
        clipped = clipped.rsplit(" ", 1)[0]
    return clipped.rstrip(" ,;:，；：") + "…"


def source_label(url: object) -> str:
    """Turn a source URL into a short publisher label."""
    host = urlparse(str(url or "")).netloc.lower().split(":", 1)[0]
    host = host.removeprefix("www.")
    known = {
        "federalreserve.gov": "Federal Reserve",
        "home.treasury.gov": "U.S. Treasury",
        "treasury.gov": "U.S. Treasury",
        "whitehouse.gov": "White House",
        "energy.gov": "Energy Department",
        "sec.gov": "SEC",
        "nato.int": "NATO",
        "congress.gov": "Congress",
        "supremecourt.gov": "Supreme Court",
        "cmegroup.com": "CME Group",
        "gov.uk": "GOV.UK", "www.gov.uk": "GOV.UK",
    }
    if host in known:
        return known[host]
    return host or "Source"


def _uk_labels(iso: object, *, with_time: bool = False) -> tuple[str, str]:
    """EN/ZH display labels for an ISO instant. Returns (\'\', \'\') when unparseable."""
    raw = str(iso or "").strip()
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return "", ""
    en = dt.strftime("%b %-d, %Y")
    zh = f"{dt.year}\u5e74{dt.month}\u6708{dt.day}\u65e5"
    if with_time:
        en += dt.strftime(" %H:%M UTC")
        zh += dt.strftime(" %H:%M UTC")
    return en, zh


# Must match engine.uk_policy_brain._STATES — pinned by test_view_states_match_engine.
_UK_VIEW_STATES = frozenset({"ok", "no_new", "source_outage", "stale", "gate_off", "model_unavailable"})
_UK_VIEW_STANCES = frozenset({"supportive", "restrictive", "mixed", "routine"})


def _uk_doc_version_labels(raw: object) -> tuple[str | None, str | None]:
    """Plain-word document-update labels. Raw content_id@iso never reaches the page."""
    s = str(raw or "").strip()
    if not s:
        return None, None
    ts = s.split("@", 1)[-1] if "@" in s else s
    en, zh = _uk_labels(ts)
    if not en:
        return None, None
    return f"Updated {en}", f"更新于{zh}"


def _uk_desk_view(raw: dict | None) -> dict:
    """Always returns a renderable view. Absent artifact -> the gate-off state.

    Every branch here is on a TYPED value (state / stance / None), never on a
    formatted display string: a formatted label can be an em dash (truthy) or
    \'0\' (falsey) and would decide the wrong way.
    Unknown states collapse to gate_off. Unknown or missing stance stays None —
    never a fabricated 'routine' the model did not produce.
    """
    if not isinstance(raw, dict):
        return {"state": "gate_off", "stance": None,
                "jurisdiction_en": "United Kingdom", "jurisdiction_zh": "\u82f1\u56fd",
                "body_en": "HM Treasury", "body_zh": "\u82f1\u56fd\u8d22\u653f\u90e8",
                "source_label": "GOV.UK", "headline": None,
                "doc_version_en": None, "doc_version_zh": None}
    view = dict(raw)
    view.pop("raw_text", None)
    state = view.get("state")
    view["state"] = state if state in _UK_VIEW_STATES else "gate_off"
    stance = view.get("stance")
    view["stance"] = stance if stance in _UK_VIEW_STANCES else None
    view["published_label_en"], view["published_label_zh"] = _uk_labels(view.get("published_iso"))
    view["known_at_label_en"], view["known_at_label_zh"] = _uk_labels(view.get("known_at_iso"), with_time=True)
    view["doc_version_en"], view["doc_version_zh"] = _uk_doc_version_labels(view.get("doc_version"))
    return view


def _verified_labels(as_of: object) -> tuple[str, str]:
    raw = str(as_of or "").strip()
    try:
        parsed = datetime.strptime(raw, "%Y-%m-%d")
    except ValueError:
        return raw, raw
    return parsed.strftime("%b %-d, %Y"), f"{parsed.year}年{parsed.month}月{parsed.day}日"


def _analysis_snapshot_labels(raw: object) -> tuple[str | None, str, str]:
    """Return a typed desk snapshot date and bilingual labels, or fail closed.

    `state_asof` is the authority for the analysis snapshot. Generated/build times,
    the historical intel vintage, and future review dates are deliberately not
    accepted as substitutes.
    """
    if not isinstance(raw, str):
        return None, "", ""
    value = raw
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return None, "", ""
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return None, "", ""
    en, zh = format_lifecycle_date(value, "day")
    return value, en, zh


_MONTH_FULL = (
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
)
_MONTH_ABBR = (
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
)
_STOP_EN = {"proposed": "Proposed", "passed": "Passed", "in_force": "In force", "enforced": "Enforced"}
_STOP_ZH = {"proposed": "提出", "passed": "通过", "in_force": "生效", "enforced": "执行"}


def format_lifecycle_date(raw: object, precision: str = "day") -> tuple[str, str]:
    """Plain EN/ZH lifecycle date. Day → 'May 1, 2026' / '2026年5月1日';
    month → 'Nov 2025' / '2025年11月'; undated → 'date not published' /
    '日期未公布'. Locale-free; ISO stays only in data-*."""
    if precision == "undated":
        return "date not published", "日期未公布"
    text = str(raw or "").strip()[:10]
    if not text:
        return "", ""
    try:
        parsed = datetime.strptime(text, "%Y-%m-%d")
    except ValueError:
        return text, text
    month_i = parsed.month - 1
    if precision == "month":
        return f"{_MONTH_ABBR[month_i]} {parsed.year}", f"{parsed.year}年{parsed.month}月"
    return (
        f"{_MONTH_FULL[month_i]} {parsed.day}, {parsed.year}",
        f"{parsed.year}年{parsed.month}月{parsed.day}日",
    )


def decorate_lifecycle_view(lifecycle: dict | None) -> dict | None:
    """Attach EN/ZH plain dates and the section-level shared-gap line."""
    if not isinstance(lifecycle, dict):
        return lifecycle
    items = [dict(it) for it in (lifecycle.get("items") or [])]
    as_of_prec = lifecycle.get("as_of_precision") or "day"
    if not lifecycle.get("as_of_precision") and lifecycle.get("as_of"):
        for it in items:
            ka = str(it.get("known_at") or "")[:10]
            sa = str(it.get("state_asof") or "")[:10]
            if ka == lifecycle["as_of"] or sa == lifecycle["as_of"]:
                as_of_prec = it.get("date_precision") or "day"
                break
    as_of_en, as_of_zh = format_lifecycle_date(lifecycle.get("as_of"), as_of_prec)
    intel_en, intel_zh = format_lifecycle_date(lifecycle.get("intel_as_of"), "day")
    decorated = []
    for it in items:
        prec = it.get("date_precision") or "day"
        en, zh = format_lifecycle_date(it.get("state_asof"), prec)
        it["state_asof_en"] = en
        it["state_asof_zh"] = zh
        decorated.append(it)
    gap_tuples = [tuple(it.get("gaps") or []) for it in decorated]
    shared = None
    if decorated and len(set(gap_tuples)) == 1 and gap_tuples[0]:
        shared = list(gap_tuples[0])
    shared_en = ", ".join(_STOP_EN.get(g, g) for g in shared) if shared else ""
    shared_zh = "、".join(_STOP_ZH.get(g, g) for g in shared) if shared else ""
    out = dict(lifecycle)
    out["items"] = decorated
    out["as_of_en"] = as_of_en
    out["as_of_zh"] = as_of_zh
    out["as_of_precision"] = as_of_prec
    out["intel_as_of_en"] = intel_en
    out["intel_as_of_zh"] = intel_zh
    out["shared_gap_set"] = shared
    out["shared_gap_en"] = shared_en
    out["shared_gap_zh"] = shared_zh
    return out


def _featured_predictions(preds: list[dict], dates: object, limit: int = 6) -> list[dict]:
    """Lead with overdue calls, then the most recently reviewed outcomes."""
    date_rows = (dates or {}).get("predictions", {}) if isinstance(dates, dict) else {}

    def decorated(pred: dict) -> dict:
        date_row = date_rows.get(pred.get("id"), {}) or {}
        return {**pred, "needs_review": bool(date_row.get("overdue"))}

    rows = [decorated(pred) for pred in preds]

    def rank(pred: dict) -> tuple[int, int, str, str]:
        if pred["needs_review"]:
            bucket = 0
            reviewed_key = 0
        elif pred.get("reviewed_on"):
            bucket = 1
            try:
                reviewed_key = -int(str(pred["reviewed_on"]).replace("-", ""))
            except ValueError:
                reviewed_key = 0
        elif pred.get("status") == "open":
            bucket = 2
            reviewed_key = 0
        else:
            bucket = 3
            reviewed_key = 0
        return bucket, reviewed_key, str(pred.get("check_by") or "9999-12-31"), str(pred.get("id") or "")

    return sorted(rows, key=rank)[:limit]


def _empty_intel() -> dict:
    return {
        "as_of": "",
        "predictions": [],
        "fed": {"task_forces": []},
        "administration": {"verified_levers": [], "theaters": []},
        "rotation": {"targeted": [], "starved": []},
        "sources": [],
    }


def _current_usable(current: dict | None) -> bool:
    if not isinstance(current, dict):
        return False
    if current.get("problem"):
        return True
    cal = current.get("calendar") or {}
    if cal.get("meetings") or cal.get("state") in {"schedule_needs_updating", "error"}:
        return True
    news = current.get("headlines") or {}
    if news.get("items") or news.get("state") in {
        "invalid_newest", "missing", "last_good", "source_outage", "stale", "no_new", "empty", "error",
    }:
        return True
    stmt = current.get("statement") or {}
    return stmt.get("state") in {"recorded", "awaiting_statement", "unavailable"}


def main() -> int:
    site = config.ROOT / "site"
    site.mkdir(exist_ok=True)
    intel_path = config.data_dir() / "policy" / "intel.json"
    if not intel_path.exists():
        # fall back to a repo-tracked copy if the data dir isn't seeded
        alt = config.ROOT / "data" / "policy" / "intel.json"
        intel_path = alt if alt.exists() else intel_path
    background_unavailable = False
    try:
        current = build_current(config.ROOT)
    except Exception as e:  # noqa: BLE001
        log.warning("policy_watch_current failed: %s", e)
        current = {
            "schema": "policy_watch_current.v1",
            "calendar": {"state": "error", "meetings": [], "calendar_url":
                         "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"},
            "headlines": {"state": "error", "items": []},
            "statement": {"state": "none"},
            "comparison": {"state": "unavailable"},
            "build_time_is_not_evidence": True,
            "problem": (
                "Official calendar/statement composer failed; older HTML was not skipped. "
                f"({type(e).__name__})"
            ),
        }
    if not intel_path.exists():
        if not _current_usable(current):
            log.warning("policy intel.json missing (%s) — skipping (additive)", intel_path)
            return 0
        log.info("policy intel.json missing — rendering current-source page without background research")
        intel = _empty_intel()
    else:
        try:
            raw = intel_path.read_text(encoding="utf-8")
            loaded = json.loads(raw)
            if not isinstance(loaded, dict):
                raise ValueError("intel root must be an object")
            intel = loaded
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as e:
            log.warning("policy intel.json unreadable (%s): %s", intel_path, e)
            if not _current_usable(current):
                log.warning("policy intel.json bad and current unusable — skipping")
                return 0
            background_unavailable = True
            intel = _empty_intel()

    preds = intel.get("predictions", [])
    counts = {
        "total": len(preds),
        "open": sum(1 for p in preds if p.get("status") == "open"),
        "hit": sum(1 for p in preds if p.get("status") == "hit"),
        "miss": sum(1 for p in preds if p.get("status") == "miss"),
        "void": sum(1 for p in preds if p.get("status") == "void"),
        "policy_action": sum(1 for p in preds if p.get("tier") == "policy-action"),
        "market_outcome": sum(1 for p in preds if p.get("tier") == "market-outcome"),
    }
    resolved = counts["hit"] + counts["miss"]
    counts["hit_rate"] = (counts["hit"] / resolved) if resolved else None

    # the LLM intent desk output (generated in CI by engine.policy_intent_desk; absent
    # locally -> the section simply hides). Drop raw_text defensively.
    desk = None
    try:
        dj = json.loads((site / "policy_intent.json").read_text())
        desk = {k: v for k, v in dj.items() if k != "raw_text"}
    except Exception:  # noqa: BLE001
        desk = None
    analysis_asof_iso, analysis_asof_en, analysis_asof_zh = _analysis_snapshot_labels(
        desk.get("state_asof") if isinstance(desk, dict) else None
    )

    # explicit Fed reaction-function read (display-only) from the regime latest.json
    # UK policy desk -- engine.uk_policy_brain writes site/uk_policy.json in CI.
    # Absent locally -> the panel renders its gate-off state, never a blank.
    uk_raw = None
    try:
        uk_raw = json.loads((site / "uk_policy.json").read_text())
    except Exception:  # noqa: BLE001
        uk_raw = None
    uk_desk = _uk_desk_view(uk_raw)

    fed_stance = None
    fed_hist = {}
    try:
        from engine import fed_stance as _fs
        latest = json.loads((config.data_dir() / "regime" / "latest.json").read_text())
        fed_stance = _fs.snapshot(latest)
        fed_hist = _fs.history_summary()    # PRIOR streak (today's stance is in the panel)
        _fs.append_history(fed_stance)      # record today for the timeline
    except Exception as e:  # noqa: BLE001
        log.warning("fed_stance skipped: %s", e)

    # rotation realized-check — grade each targeted theme's proxies vs SPY (coincident),
    # accrue it forward (idempotent per day) + read back a per-theme trailing hit-rate.
    rot = None
    rot_hist = {}
    try:
        from engine import policy_rotation_check as _rotc
        rot = _rotc.check(intel)
        rot_hist = _rotc.history_summary()   # PRIOR accrued reads (today's verdict is in the chip)
        _rotc.append_history(rot)            # then record today for future reads
    except Exception as e:  # noqa: BLE001
        log.warning("rotation check skipped: %s", e)

    # live dating: intel staleness + task-force countdowns + overdue-prediction flags
    dates = None
    try:
        from engine import policy_dates as _pd
        dates = _pd.annotate(intel)
    except Exception as e:  # noqa: BLE001
        log.warning("policy dates skipped: %s", e)

    # catalyst spine — stamp each dated event with a live days-to / past flag so the
    # forward calendar counts down on the page (additive; absent block -> section hides)
    catalysts = None
    try:
        cat = intel.get("catalysts")
        if cat and cat.get("spine"):
            from datetime import date as _date
            # the spine is an all-ET calendar (8:30am prints, 2pm decisions) — count down
            # against the US/Eastern date so it doesn't roll over after ~8pm ET (UTC midnight)
            try:
                from zoneinfo import ZoneInfo
                today = datetime.now(ZoneInfo("America/New_York")).date()
            except Exception:  # noqa: BLE001 — fall back to UTC if tz db is unavailable
                today = datetime.now(timezone.utc).date()
            rows = []
            for ev in cat["spine"]:
                try:
                    d = _date.fromisoformat(ev.get("date", ""))
                    days_to = (d - today).days
                except Exception:  # noqa: BLE001
                    days_to = None
                rows.append({**ev, "days_to": days_to,
                             "past": days_to is not None and days_to < 0})
            catalysts = {**cat, "spine": rows}
    except Exception as e:  # noqa: BLE001
        log.warning("catalyst spine skipped: %s", e)

    # unified accountability scorecard (predictions / rotation / stance / freshness) +
    # the sharpest divergence (a targeted theme that is actually lagging worst).
    scorecard = None
    try:
        from engine import policy_summary as _psum
        scorecard = _psum.summarize(counts, rot, fed_hist, dates)
    except Exception as e:  # noqa: BLE001
        log.warning("scorecard skipped: %s", e)

    # deterministic policy lifecycle (no LLM) — owner: engine.policy_intent_desk
    lifecycle = None
    try:
        from engine import policy_intent_desk as _pid
        _pid.ingest_lifecycle(config.ROOT)      # nightly-gated, idempotent
        lifecycle = decorate_lifecycle_view(_pid.lifecycle_view(config.ROOT))
    except Exception as e:  # noqa: BLE001
        log.warning("policy lifecycle skipped: %s", e)

    verified_en, verified_zh = _verified_labels(intel.get("as_of"))
    source_links = [{"url": url, "label": source_label(url)} for url in intel.get("sources", [])]
    featured_predictions = _featured_predictions(preds, dates)
    built = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    env = Environment(loader=FileSystemLoader(str(config.ROOT / "templates")), autoescape=True)
    html = env.get_template("policy_watch.html.j2").render(
        intel=intel, counts=counts, desk=desk, fed_stance=fed_stance, fed_hist=fed_hist,
        rot=rot, rot_hist=rot_hist, dates=dates, catalysts=catalysts, scorecard=scorecard,
        generated_utc=built, verified_en=verified_en, verified_zh=verified_zh,
        source_links=source_links, featured_predictions=featured_predictions, brief=brief,
        uk_desk=uk_desk,
        active_section="research", active_page="policy_watch",
        lifecycle=lifecycle, current=current,
        analysis_asof_iso=analysis_asof_iso,
        analysis_asof_en=analysis_asof_en,
        analysis_asof_zh=analysis_asof_zh,
        background_unavailable=background_unavailable,
    )
    # Jinja's language branches leave indentation on otherwise-empty lines.
    # Normalize it here so the committed artifact stays diff-clean after every build.
    html = re.sub(r"[ \t]+(?=\n)", "", html)
    write_page(site / "policy_watch.html", html)
    log.info("wrote %s/policy_watch.html (%d preds, %d task forces, %d KB)",
             site, counts["total"], len(intel.get("fed", {}).get("task_forces", [])), len(html) // 1024)
    return 0


if __name__ == "__main__":
    sys.exit(main())
