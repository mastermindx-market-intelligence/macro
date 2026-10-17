"""scripts/run_watchlist_sentinel.py — Nightly runner for Watchlist Buy-Zone Sentinel.

Codex docket B6: connects operator Supabase watchlist → buy-zone enter-detection →
alert center + Discord dispatch.

Design invariants (house laws)
-------------------------------
- ONE Supabase REST call per nightly run (render budget law).
- Fail-soft on every external dependency: missing creds / table / network → log one
  line, emit nothing, exit 0.  The nightly must never crash on this step.
- Fail-soft is NOT the same as fail-quiet, and an untrustworthy read is NOT an empty
  watchlist.  _fetch_operator_watchlist() returns a typed WatchlistRead, and only an
  AUTHORITATIVE read (available=True) may advance durable state.  An unavailable read
  preserves cooldown + previous-states EXACTLY and stamps a `source` envelope so the
  night is visible rather than silently indistinguishable from "nothing watched".
- No LLM calls anywhere.  All state is read from deterministic engine artifacts.
- Nightly is the sole advancer of forward stores: cooldown + prev-states are only
  written in this script (nightly path).  Same-day re-renders carry forward the
  existing state (idempotent: as_of == today → skip write).
- Privacy: v1 reads the OPERATOR account watchlist only (SUPABASE_OPERATOR_USER_ID
  is REQUIRED).  No other users' rows are logged or enumerated.
- Discord: uses DISCORD_WEBHOOK_WATCHLIST if set; falls back to DISCORD_WEBHOOK_URL.
  The webhook selection is logged once at startup.

Supabase schema (live, verified 2026-07-07)
-------------------------------------------
  watchlists       : {id, user_id, name, position, created_at}  — one row per list container
  watchlist_symbols: {id, watchlist_id, symbol, section, position, created_at}  — one row per ticker

The fetch uses ONE embedded PostgREST call:
  GET /rest/v1/watchlists?select=id,user_id,watchlist_symbols(symbol)&user_id=eq.{uid}
This flattens all symbols across the operator's lists in a single round-trip.

State files (committed JSON, advanced nightly)
----------------------------------------------
  data/alerts/watchlist_sentinel_states.json
      Per-ticker state snapshots for the PREVIOUS nightly run.  Shape:
      {"as_of": "YYYY-MM-DD", "states": {ticker: {entry_status, gate_eligible,
        gate_tier, in_blackout, extension_grade}},
       "source": {"status": "ok"|"unavailable", "state": <WatchlistRead.state>,
        "reason": "<slug>", "checked": "YYYY-MM-DD", "watched_count": N}}

      `as_of` is the last night the sentinel AUTHORITATIVELY evaluated; `source.checked`
      is the last night it TRIED.  They differ exactly when the watchlist source was
      unavailable — which is how a reader tells "nothing watched" (status ok,
      watched_count 0, checked == as_of == today) from "watchlist source unavailable"
      (status unavailable, checked == today, as_of stale).

  data/alerts/watchlist_sentinel_cooldown.json
      Cooldown map.  Shape: {"as_of": "YYYY-MM-DD", "cooldown": {ticker: {...}}}

  data/alerts/watchlist_alerts.jsonl
      Append-only log of fired alerts, read by alert_triage.py.
      One JSON object per line:
      {"ts": "<ISO>", "source": "watchlist", "type": "buy_zone_enter",
       "asset": "<TICKER>", "severity": "info", "edge": "", "edge_zh": "",
       "detail": "<plain message>", "headline": "<plain message>",
       "ticker": "<TICKER>", ...}

Usage
-----
    python -m scripts.run_watchlist_sentinel [--dry-run] [--date YYYY-MM-DD]
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lib import config  # noqa: E402
from engine import earnings_blackout as _eb  # noqa: E402
from engine.watchlist_sentinel import (  # noqa: E402
    run_sentinel,
    update_cooldown,
    format_discord_message,
)
from scripts.check_signal_gate_coherence import (  # noqa: E402 — one shared predicate
    incoherent_tickers, stale_side)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("watchlist_sentinel")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_ALERTS_DIR = config.data_dir() / "alerts"
_STATES_PATH = _ALERTS_DIR / "watchlist_sentinel_states.json"
_COOLDOWN_PATH = _ALERTS_DIR / "watchlist_sentinel_cooldown.json"
_ALERTS_JSONL = _ALERTS_DIR / "watchlist_alerts.jsonl"

# ---------------------------------------------------------------------------
# Supabase watchlist fetch
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class WatchlistRead:
    """The result of ONE attempt to read the operator's watchlist.

    An empty list is not one fact but two, and the runner used to be unable to tell them apart:
    "the operator watches nothing" and "we could not find out" both arrived as []. Only the first
    licenses advancing durable Sentinel state; the second must leave it alone, because a single
    night of Supabase trouble would otherwise erase live cooldowns and move the enter-detection
    baseline past a night that was never evaluated.

    Three states, and every caller must branch on `available` BEFORE looking at `tickers`:

        available=True,  tickers=(...)  -> READ_OK           (authoritative, non-empty)
        available=True,  tickers=()     -> READ_OK_ZERO      (authoritative empty; may advance)
        available=False, tickers=()     -> READ_UNAVAILABLE  (preserve everything)

    The slugs are the house vocabulary for exactly this distinction, already used by the alert
    feeds in engine/alert_triage.py ("read succeeded, legitimately nothing to say" vs
    "read/parse failed — we do NOT know what it holds"). They are mirrored here rather than
    imported so the nightly runner does not pull that module in for three strings;
    tests/test_watchlist_sentinel_source_truth.py pins them equal so they cannot drift.

    `reason` is a short stable slug for the unavailable case ("no_service_key", "http_500",
    "request_failed", "malformed_payload", ...) — it is what the operator sees in the nightly
    annotation and what lands in the states file's `source` envelope.
    """

    available: bool
    tickers: tuple[str, ...] = ()
    reason: str = ""

    READ_OK = "ok"
    READ_OK_ZERO = "ok_zero_events"
    READ_UNAVAILABLE = "unavailable"

    @classmethod
    def ok(cls, tickers) -> "WatchlistRead":
        return cls(True, tuple(tickers), "")

    @classmethod
    def unavailable(cls, reason: str) -> "WatchlistRead":
        return cls(False, (), reason)

    @property
    def state(self) -> str:
        if not self.available:
            return self.READ_UNAVAILABLE
        return self.READ_OK if self.tickers else self.READ_OK_ZERO


def _fetch_operator_watchlist() -> WatchlistRead:
    """Fetch the operator's watchlist tickers from Supabase as a typed, truthful read.

    Returns WatchlistRead.ok(sorted unique upper-cased tickers) only when the read actually
    succeeded — including the honest empty case, where the operator has a Supabase row and simply
    watches nothing. EVERY other outcome (no config, no credentials, no operator identity, a
    non-200, a transport failure, a payload that is not the shape we asked for) is
    WatchlistRead.unavailable(reason): we did not learn the watchlist, and the caller must not
    pretend we did.

    Requires env vars:
      SUPABASE_SERVICE_KEY (or SUPABASE_SERVICE_ROLE_KEY)  — service_role key
      SUPABASE_OPERATOR_USER_ID                             — operator's auth.users UUID
                                                              (REQUIRED; absent → unavailable)

    Uses ONE embedded PostgREST call that joins watchlists → watchlist_symbols:
      GET /rest/v1/watchlists?select=id,user_id,watchlist_symbols(symbol)
          &user_id=eq.{operator_uid}

    Live schema (verified 2026-07-07):
      watchlists        : id, user_id, name, position, created_at
      watchlist_symbols : id, watchlist_id, symbol, section, position, created_at
    """
    # --- Resolve Supabase URL from config (public, no secret) ----------
    sup_cfg = (config.load().get("watchlist", {}).get("supabase") or {})
    base_url: str | None = sup_cfg.get("url")
    if not base_url:
        log.info("watchlist_sentinel: no Supabase URL in config — watchlist unknown")
        return WatchlistRead.unavailable("no_config_url")

    # --- Service key (required for server-side table read bypassing RLS) ---
    service_key = (
        config.secret("SUPABASE_SERVICE_KEY")
        or config.secret("SUPABASE_SERVICE_ROLE_KEY")
    )
    if not service_key:
        log.info(
            "watchlist_sentinel: SUPABASE_SERVICE_KEY not set — watchlist unknown"
        )
        return WatchlistRead.unavailable("no_service_key")

    # --- Operator UUID is REQUIRED (multiple accounts exist; do not read other users' lists) ---
    operator_uid: str | None = config.secret("SUPABASE_OPERATOR_USER_ID")
    if not operator_uid:
        log.info("watchlist_sentinel: operator UUID not set — watchlist unknown")
        return WatchlistRead.unavailable("no_operator_id")

    # --- ONE embedded PostgREST call: watchlists + nested watchlist_symbols ---
    rest_url = base_url.rstrip("/") + "/rest/v1/watchlists"
    headers = {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
        "Accept": "application/json",
    }
    params: dict[str, str] = {
        "select": "id,user_id,watchlist_symbols(symbol)",
        "user_id": f"eq.{operator_uid}",
    }

    try:
        r = requests.get(rest_url, headers=headers, params=params, timeout=20)
        if r.status_code != 200:
            log.info(
                "watchlist_sentinel: Supabase returned %d — watchlist unknown (%s)",
                r.status_code,
                r.text[:200],
            )
            return WatchlistRead.unavailable(f"http_{r.status_code}")
        rows = r.json()
    except Exception as exc:  # noqa: BLE001
        log.info("watchlist_sentinel: Supabase request failed — watchlist unknown (%s)", exc)
        return WatchlistRead.unavailable("request_failed")

    # A payload that is not the shape we asked for is a FAILED read, not an empty watchlist.
    # PostgREST reports errors as a JSON object, and the old code walked that object's keys as if
    # they were rows — raising AttributeError out of the nightly step.
    if not isinstance(rows, list):
        log.info("watchlist_sentinel: Supabase payload was %s, not a list — watchlist unknown",
                 type(rows).__name__)
        return WatchlistRead.unavailable("malformed_payload")

    if not rows:
        log.info("watchlist_sentinel: no watchlist rows found — operator watches nothing")
        return WatchlistRead.ok(())

    dict_rows = [row for row in rows if isinstance(row, dict)]
    if not dict_rows:
        log.info("watchlist_sentinel: no usable row objects in payload — watchlist unknown")
        return WatchlistRead.unavailable("malformed_payload")

    # Privacy: log counts only, never UIDs or symbols individually.
    log.info("watchlist_sentinel: fetched %d watchlist container(s)", len(dict_rows))

    # Flatten symbols from all the operator's list containers, dedupe, sort.
    seen: set[str] = set()
    tickers: list[str] = []
    entries_seen = 0          # symbol ROWS the payload actually carried
    for row in dict_rows:
        symbols = row.get("watchlist_symbols") or []
        if not isinstance(symbols, list):
            # The embedded select asks for a list; anything else means the shape changed under us.
            log.info("watchlist_sentinel: watchlist_symbols was %s, not a list — watchlist unknown",
                     type(symbols).__name__)
            return WatchlistRead.unavailable("malformed_payload")
        for entry in symbols:
            entries_seen += 1
            if not isinstance(entry, dict):
                continue
            raw = (entry.get("symbol") or "").strip().upper()
            if raw and raw not in seen:
                seen.add(raw)
                tickers.append(raw)

    # Symbol rows that yield NO usable ticker are not an empty watchlist — they are a read whose
    # shape we no longer understand. A `symbol` column renamed out from under this query would
    # otherwise arrive as an authoritative empty and wipe the cooldown, which is the original
    # defect in a narrower disguise. Zero ENTRIES is different, and stays honestly empty: that is
    # a real container the operator has simply not put anything in.
    if entries_seen and not tickers:
        log.info("watchlist_sentinel: %d symbol row(s) yielded no usable ticker — watchlist unknown",
                 entries_seen)
        return WatchlistRead.unavailable("no_usable_symbols")

    tickers.sort()
    log.info("watchlist_sentinel: %d unique ticker(s) in operator watchlist", len(tickers))
    return WatchlistRead.ok(tickers)


# ---------------------------------------------------------------------------
# Per-ticker state assembly
# ---------------------------------------------------------------------------

def _load_per_ticker_states(today_str: str) -> dict[str, dict]:
    """Build per-ticker state dicts from committed nightly artifacts.

    Sources (no new network calls):
    - site/factordata/us_standouts.json: entry_signal.status per ticker
    - site/factordata/signal_gate.json: eligible, tier_cascade per ticker
    - earnings_blackout.assess(): called per ticker (module reads local store)

    Returns {ticker: state_dict} for ALL tickers found in artifacts.
    """
    site_fd = ROOT / "site" / "factordata"
    states: dict[str, dict] = {}

    # --- 1. signal_gate.json -----------------------------------------------
    sg_path = site_fd / "signal_gate.json"
    sg_data: dict = {}
    gate_verdicts: dict[str, dict] = {}
    if sg_path.exists():
        try:
            sg_data = json.loads(sg_path.read_text())
            gate_verdicts = sg_data.get("verdicts") or {}
        except Exception as exc:  # noqa: BLE001
            log.info("watchlist_sentinel: could not read signal_gate.json (%s)", exc)

    # --- 2. us_standouts.json ----------------------------------------------
    us_path = site_fd / "us_standouts.json"
    us_data: dict = {}
    entry_by_ticker: dict[str, dict] = {}
    row_signal_by_ticker: dict[str, dict] = {}
    if us_path.exists():
        try:
            us_data = json.loads(us_path.read_text())
            for bucket in ("buy", "watch", "laggards"):
                for row in us_data.get(bucket) or []:
                    ticker = row.get("ticker")
                    if not ticker:
                        continue
                    es = row.get("entry_signal") or {}
                    sig = row.get("signal") or {}
                    entry_by_ticker[ticker] = {
                        "entry_status": es.get("status"),
                        "gate_eligible_row": sig.get("eligible"),
                        "gate_tier_row": sig.get("tier_cascade"),
                    }
                    row_signal_by_ticker[ticker] = sig
        except Exception as exc:  # noqa: BLE001
            log.info("watchlist_sentinel: could not read us_standouts.json (%s)", exc)

    # --- 2b. pair coherence (#5490) ----------------------------------------
    # The gate is preferred below because it is more granular — and it is also the side
    # that can silently go stale: build_stock_library writes both artifacts, but only the
    # gate write is guarded (`if sig_verdict:`), so a `scope=all` re-render can advance the
    # board's embedded `signal` blobs and leave the gate behind wearing the same `as_of`
    # (the DATA date, not the write time). For any ticker where the two disagree the gate
    # loses its preference and the ROW values are used instead. Same predicate the CI guard
    # and the render-lane self-check use, so no two surfaces can flag different names.
    incoherent: dict[str, list[str]] = {}
    try:
        incoherent = incoherent_tickers(us_data, sg_data)
        if incoherent:
            _names = sorted(incoherent)
            _side = stale_side(us_data, sg_data)
            _tail = f"; emit stamps name the {_side} side as the stale one" if _side else ""
            # Bare print at line start with flush=True — house law (CLAUDE.md §GitHub
            # annotations): this module's logger prefixes every record, so a logged
            # "::warning" is dropped silently by GitHub.
            print(f"::warning title=signal-gate-coherence::"
                  f"{len(_names)} ticker(s) disagree between signal_gate.json and the "
                  f"board's embedded signal blob ({', '.join(_names[:8])}) — sentinel "
                  f"reads the board row for them, not the gate{_tail}", flush=True)
    except Exception as exc:  # noqa: BLE001 — coherence is advisory, never fatal here
        log.info("watchlist_sentinel: coherence check skipped (%s)", exc)

    # --- Merge sources per ticker ------------------------------------------
    all_tickers = set(gate_verdicts.keys()) | set(entry_by_ticker.keys())
    for ticker in all_tickers:
        gv = gate_verdicts.get(ticker) or {}
        er = entry_by_ticker.get(ticker) or {}

        if ticker in incoherent:
            # The gate disagrees with the board for this name — do not trust it.
            row_sig = row_signal_by_ticker.get(ticker) or {}
            gate_eligible = er.get("gate_eligible_row", row_sig.get("eligible"))
            gate_tier = er.get("gate_tier_row", row_sig.get("tier_cascade"))
        else:
            # Prefer signal_gate.json for gate fields (it is more granular)
            gate_eligible = gv.get("eligible") if gv else er.get("gate_eligible_row")
            gate_tier = gv.get("tier_cascade") if gv else er.get("gate_tier_row")

        entry_status: str | None = er.get("entry_status")

        # Derive extension_grade from entry_status (entry_signal already encodes it)
        ext_grade: str | None = None
        if entry_status in {"extended", "topping"}:
            ext_grade = "stretched"  # conservative label — both states are extension vetos

        states[ticker] = {
            "entry_status": entry_status,
            "gate_eligible": gate_eligible,
            "gate_tier": gate_tier,
            "in_blackout": None,  # filled below
            "extension_grade": ext_grade,
            "as_of": today_str,
        }

    # --- 3. earnings_blackout per ticker (local store read) ----------------
    # We call assess() only for tickers where the state was assembled above.
    # The module is fail-open on missing store — no crash risk.
    eb_stale_info = _eb.store_staleness()
    if eb_stale_info.get("stale", True):
        log.info(
            "watchlist_sentinel: earnings_blackout store stale (age=%s) — in_blackout=False",
            eb_stale_info.get("as_of_age_td"),
        )
        for t in states:
            states[t]["in_blackout"] = False
    else:
        for t in states:
            try:
                ev = _eb.assess(t)
                states[t]["in_blackout"] = bool(ev.get("in_blackout", False))
            except Exception as exc:  # noqa: BLE001
                states[t]["in_blackout"] = False
                log.debug("watchlist_sentinel: eb.assess(%s) failed (%s)", t, exc)

    return states


# ---------------------------------------------------------------------------
# Committed state persistence
# ---------------------------------------------------------------------------

def _load_prev_states() -> dict[str, dict]:
    if not _STATES_PATH.exists():
        return {}
    try:
        d = json.loads(_STATES_PATH.read_text())
        return d.get("states") or {}
    except Exception as exc:  # noqa: BLE001
        log.debug("watchlist_sentinel: could not load prev states (%s)", exc)
        return {}


def _load_cooldown() -> dict[str, dict]:
    if not _COOLDOWN_PATH.exists():
        return {}
    try:
        d = json.loads(_COOLDOWN_PATH.read_text())
        return d.get("cooldown") or {}
    except Exception as exc:  # noqa: BLE001
        log.debug("watchlist_sentinel: could not load cooldown (%s)", exc)
        return {}


def _source_envelope(read: WatchlistRead, today_str: str) -> dict:
    """Tonight's watchlist-source health, as stamped into the states file.

    This is what lets a reader tell "nothing watched" from "watchlist source unavailable" —
    the two cases that used to be indistinguishable once both had produced an empty list.
    `checked` is always tonight; `as_of` beside it still means the last AUTHORITATIVE night, so
    an unavailable night shows a today `checked` next to a stale `as_of`.
    """
    return {
        "status": "ok" if read.available else "unavailable",
        "state": read.state,
        "reason": read.reason,
        "checked": today_str,
        "watched_count": len(read.tickers),
    }


def _save_states(today_str: str, states: dict[str, dict], dry_run: bool,
                 read: WatchlistRead | None = None) -> None:
    if dry_run:
        return
    _ALERTS_DIR.mkdir(parents=True, exist_ok=True)
    payload: dict = {"as_of": today_str, "states": states}
    if read is not None:
        payload["source"] = _source_envelope(read, today_str)
    _STATES_PATH.write_text(json.dumps(payload, separators=(",", ":")))


def _record_unavailable_source(today_str: str, read: WatchlistRead, dry_run: bool) -> None:
    """Stamp the failed read onto the EXISTING states file without advancing anything.

    Deliberately NOT a second store (there is exactly one Sentinel state store and this keeps it
    that way): `as_of` and `states` are rewritten byte-for-byte from what the last authoritative
    night left, and only the `source` envelope moves. Preserving `as_of` is load-bearing twice
    over — it keeps _load_prev_states() pointing at the last night we actually evaluated, and it
    keeps _is_same_day_rerender() False so a later run tonight retries the fetch instead of
    skipping as though tonight were already done.
    """
    if dry_run:
        return
    existing: dict = {}
    if _STATES_PATH.exists():
        try:
            loaded = json.loads(_STATES_PATH.read_text())
        except Exception as exc:  # noqa: BLE001
            # The file is there but we cannot read it. REFUSE to write: rewriting it with only a
            # health stamp would turn a read problem into the exact data loss this whole change
            # exists to prevent, and would destroy bytes a human might still recover. The stamp is
            # a nicety; the state is the point.
            log.warning("watchlist_sentinel: states file unreadable (%s) — not stamping source, "
                        "leaving the file untouched", exc)
            return
        if isinstance(loaded, dict):
            existing = loaded
        else:
            log.warning("watchlist_sentinel: states file holds %s, not an object — not stamping "
                        "source, leaving the file untouched", type(loaded).__name__)
            return
    existing["source"] = _source_envelope(read, today_str)
    _ALERTS_DIR.mkdir(parents=True, exist_ok=True)
    _STATES_PATH.write_text(json.dumps(existing, separators=(",", ":")))


def _save_cooldown(today_str: str, cooldown: dict[str, dict], dry_run: bool) -> None:
    if dry_run:
        return
    _ALERTS_DIR.mkdir(parents=True, exist_ok=True)
    _COOLDOWN_PATH.write_text(
        json.dumps({"as_of": today_str, "cooldown": cooldown}, separators=(",", ":"))
    )


# ---------------------------------------------------------------------------
# Alert JSONL — alert_triage reads this
# ---------------------------------------------------------------------------

def _append_alert_jsonl(alerts: list[dict], today_str: str, dry_run: bool) -> None:
    """Append fired alerts to the watchlist_alerts.jsonl feed.

    Format mirrors the bonds/forex/commodity JSONL that alert_triage._jsonl_raw()
    reads.  Required keys: ts, source, type, asset, severity, edge, edge_zh,
    detail, headline.
    """
    if not alerts or dry_run:
        return
    _ALERTS_DIR.mkdir(parents=True, exist_ok=True)
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines = []
    for a in alerts:
        ticker = a.get("ticker", "")
        headline = format_discord_message(a)
        reasons = "; ".join(a.get("reasons") or [])
        record = {
            "ts": now_iso,
            "source": "watchlist",
            "type": "buy_zone_enter",
            "asset": ticker,
            "severity": "info",
            "edge": "",
            "edge_zh": "",
            "detail": reasons,
            "headline": headline,
            "headline_zh": headline,
            "anchor": "",
            # Carry sentinel fields through for the admin capture tab
            "entry_status": a.get("entry_status"),
            "gate_tier": a.get("gate_tier"),
            "in_blackout": a.get("in_blackout"),
            "extension_grade": a.get("extension_grade"),
            "as_of": today_str,
        }
        lines.append(json.dumps(record, separators=(",", ":")))
    with open(_ALERTS_JSONL, "a") as fh:
        fh.write("\n".join(lines) + "\n")
    log.info("watchlist_sentinel: appended %d row(s) to watchlist_alerts.jsonl", len(lines))


# ---------------------------------------------------------------------------
# Discord dispatch
# ---------------------------------------------------------------------------

def _send_discord_watchlist(msg: str, dry_run: bool) -> bool:
    """Send one message to the watchlist Discord channel.

    Webhook priority: DISCORD_WEBHOOK_WATCHLIST → DISCORD_WEBHOOK_URL.
    Returns True on success, False on skip or failure.
    """
    url = config.secret("DISCORD_WEBHOOK_WATCHLIST") or config.secret("DISCORD_WEBHOOK_URL")
    if not url:
        log.info("watchlist_sentinel: no Discord webhook configured — skipping dispatch")
        return False
    if dry_run:
        print("[DRY-RUN] Discord message:")
        print(msg)
        return True
    try:
        r = requests.post(url, json={"content": msg[:1990]}, timeout=30)
        if r.status_code not in (200, 204):
            log.warning(
                "watchlist_sentinel: Discord dispatch failed (%d: %s)",
                r.status_code,
                r.text[:200],
            )
            return False
        log.info("watchlist_sentinel: Discord dispatch OK")
        return True
    except Exception as exc:  # noqa: BLE001
        log.warning("watchlist_sentinel: Discord dispatch error (%s)", exc)
        return False


# ---------------------------------------------------------------------------
# Idempotence guard
# ---------------------------------------------------------------------------

def _is_same_day_rerender(today_str: str) -> bool:
    """Return True when both state stores already hold today's date."""
    try:
        s = json.loads(_STATES_PATH.read_text()) if _STATES_PATH.exists() else {}
        c = json.loads(_COOLDOWN_PATH.read_text()) if _COOLDOWN_PATH.exists() else {}
        return (
            s.get("as_of") == today_str
            and c.get("as_of") == today_str
        )
    except Exception:  # noqa: BLE001
        return False


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description="Watchlist buy-zone sentinel")
    ap.add_argument("--dry-run", action="store_true", help="Print without sending or writing")
    ap.add_argument("--date", default=None, help="Override date (YYYY-MM-DD)")
    args = ap.parse_args()

    today_str = args.date or date.today().isoformat()
    dry_run: bool = args.dry_run

    log.info("watchlist_sentinel: running for %s (dry_run=%s)", today_str, dry_run)

    # --- Idempotence: skip writes (but still log) on same-day re-render --------
    same_day = _is_same_day_rerender(today_str)
    if same_day:
        log.info(
            "watchlist_sentinel: same-day re-render (as_of=%s) — "
            "state files already current; no new alerts emitted",
            today_str,
        )
        return 0

    # --- Step 1: fetch operator watchlist (one Supabase call) ------------------
    read = _fetch_operator_watchlist()

    if not read.available:
        # We did not learn the watchlist, so nothing downstream is knowable. Durable state is
        # PRESERVED EXACTLY — no states write, no cooldown write. Advancing here is what a single
        # bad night used to cost: the cooldown map was overwritten with {} (erasing every live
        # suppression, so a ticker that alerted two nights ago could alert again immediately) and
        # the previous-state snapshot jumped to today, stepping the enter-detection baseline past
        # a transition that was never evaluated and could never fire.
        print(
            f"::warning title=watchlist-sentinel-source-unavailable::watchlist source "
            f"unavailable ({read.reason}) for {today_str} — cooldown and previous-state "
            f"preserved; no tickers evaluated tonight",
            flush=True,
        )
        log.warning(
            "watchlist_sentinel: watchlist source unavailable (%s) — durable state preserved, "
            "no alerts evaluated", read.reason,
        )
        _record_unavailable_source(today_str, read, dry_run)
        return 0

    watched = list(read.tickers)
    if not watched:
        # Authoritative empty: the operator genuinely watches nothing. This DOES advance — an
        # empty cooldown is the correct answer when there is nothing to cool down, and
        # update_cooldown() would return {} for an empty watchlist anyway.
        log.info("watchlist_sentinel: watchlist is authoritatively empty — advancing state")
        today_states = _load_per_ticker_states(today_str)
        _save_states(today_str, today_states, dry_run, read)
        _save_cooldown(today_str, {}, dry_run)
        return 0

    # --- Step 2: build today's per-ticker states from committed artifacts ------
    today_states = _load_per_ticker_states(today_str)

    # --- Step 3: load yesterday's states and cooldown --------------------------
    yesterday_states = _load_prev_states()
    cooldown = _load_cooldown()

    # --- Step 4: run sentinel --------------------------------------------------
    alerts = run_sentinel(
        watched_tickers=watched,
        today_states=today_states,
        yesterday_states=yesterday_states,
        cooldown=cooldown,
        today_str=today_str,
    )

    # --- Step 5: update cooldown and save state files (nightly advance) --------
    new_cooldown = update_cooldown(
        cooldown=cooldown,
        watched_tickers=watched,
        today_states=today_states,
        newly_alerted=alerts,
        today_str=today_str,
    )
    _save_states(today_str, today_states, dry_run, read)
    _save_cooldown(today_str, new_cooldown, dry_run)

    # --- Step 6: write alert JSONL (alert_triage reads this) ------------------
    _append_alert_jsonl(alerts, today_str, dry_run)

    # --- Step 7: dispatch to Discord ------------------------------------------
    dispatched = 0
    for a in alerts:
        msg = format_discord_message(a)
        if _send_discord_watchlist(msg, dry_run):
            dispatched += 1

    log.info(
        "watchlist_sentinel: %d alert(s) fired, %d dispatched to Discord",
        len(alerts),
        dispatched,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
