"""scripts/build_cn_live_pack.py — CN armed-pack driver (CN-PR-1, spec §4).

Runs AFTER the china library rebuild in asia-close (wired in CN-PR-2). Advisory:
``continue-on-error: true`` — a miss is ``stale_pack`` on the next session, never
a red settlement.

    python -m scripts.build_cn_live_pack [--publish] [--out PATH] [--now ISO]
                                         [--limit N]

Universe = ``build_china_library.universe()`` minus Sector ETF / Index, gated by
a strict, complete ``stock_tradability_ok`` map (a missing key refuses the build
— the pack never fails open on tradability). Probe uses the CN calendar and
the per-class daily-limit band. T2 latch is loaded read-only.

FAIL-CLOSED ON PARITY (G0.1 inherited): unpublished / mismatched edges are
withheld per name, never silently shipped.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_CODE_ROOT = str(Path(__file__).resolve().parent.parent)
sys.path.insert(0, _CODE_ROOT)

from engine import china_liquidity  # noqa: E402
from engine.prophet_live import cn_pack as CP  # noqa: E402
from engine.prophet_live import r2io  # noqa: E402
from engine.prophet_live import armed_pack as AP  # noqa: E402

log = logging.getLogger("build_cn_live_pack")


def _now(raw: str | None) -> datetime | None:
    if not raw:
        return None
    t = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    return t if t.tzinfo else t.replace(tzinfo=timezone.utc)


def load_frozen(root: Path,
                *, receipt_out: dict[str, Any] | None = None) -> dict[str, dict[str, Any]]:
    """Nightly board rows keyed by ticker. Missing file → empty (fail-open).

    ``receipt_out``, when given, is filled with the board's source identity for
    the pack stamp: ``path`` (repo-relative), ``as_of``, ``sha256`` of the file
    bytes read here, plus the ``project_primary_board`` receipt — or a single
    ``reason`` (``no_board`` / ``refused:<why>``) when no board was loaded. The
    file is read once as bytes and hashed from that same read; it is never
    re-read or re-parsed a second way.
    """
    for rel in ("site/factordata/china_standouts.json",
                "site/china_standouts.json", "data/china_standouts.json"):
        p = root / rel
        if not p.is_file():
            continue
        try:
            raw = p.read_bytes()
            doc = json.loads(raw.decode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            print(f"::warning title=cn-live-pack::frozen board {p} unreadable ({exc})",
                  flush=True)
            continue
        if isinstance(doc, dict) and any(isinstance(doc.get(k), list)
                                         for k in CP.PRIMARY_BOARD_ARRAYS):
            rows, receipt = CP.project_primary_board(doc)
            if receipt.get("refused"):
                print(f"::warning title=cn-live-pack::frozen board {p} "
                      f"refused ({receipt['refused']})", flush=True)
                if receipt_out is not None:
                    receipt_out["reason"] = f"refused:{receipt['refused']}"
                return {}
            print(f"::notice title=cn-live-pack::frozen board {p} "
                  f"as_of={receipt['as_of']} primary={receipt['primary_rows']} "
                  f"projected={receipt['projected']} "
                  f"excluded={receipt['excluded']}", flush=True)
            if receipt_out is not None:
                receipt_out.update(receipt)
                receipt_out["path"] = rel
                receipt_out["sha256"] = hashlib.sha256(raw).hexdigest()
            return rows
        out: dict[str, dict[str, Any]] = {}
        lanes = doc.get("lanes") if isinstance(doc, dict) else None
        if isinstance(lanes, dict):
            for lane, rows in lanes.items():
                if not isinstance(rows, list):
                    continue
                for row in rows:
                    if not isinstance(row, dict):
                        continue
                    tkr = str(row.get("ticker") or row.get("symbol") or "")
                    if not tkr:
                        continue
                    blob = dict(row)
                    blob.setdefault("lane", lane)
                    out[tkr] = blob
        elif isinstance(doc, dict):
            for tkr, row in (doc.get("names") or doc.get("rows") or {}).items():
                if isinstance(row, dict):
                    out[str(tkr)] = row
        if out:
            if receipt_out is not None:
                ao = doc.get("as_of") if isinstance(doc, dict) else None
                receipt_out["path"] = rel
                receipt_out["as_of"] = ao if isinstance(ao, str) else None
                receipt_out["sha256"] = hashlib.sha256(raw).hexdigest()
            return out
    if receipt_out is not None:
        receipt_out["reason"] = "no_board"
    return {}


def tradability_map(tickers, *, meta: dict, liq_by: dict) -> dict[str, bool]:
    """Strict Boolean tradability for every ticker — the nightly predicate.

    ``stock_tradability_ok`` returns a REJECTION reason (``st`` / ``mcap`` /
    ``adv``) or ``None`` for a pass, so the map value is ``... is None`` —
    passing the raw result would INVERT the gate. Same argument sourcing as the
    nightly board's ``_tradability_ok`` wrapper; unknown cap / ADV pass through
    (nightly semantics, unchanged).
    """
    from scripts.build_china_library import stock_tradability_ok  # noqa: PLC0415

    st_flag_by = meta["st_flag_by"]
    name_zh_by = meta["name_zh_by"]
    mktcap_by = meta["mktcap_by"]
    return {
        t: stock_tradability_ok(
            t,
            st_flag=st_flag_by.get(t, False),
            name_zh=name_zh_by.get(t),
            mktcap=mktcap_by.get(t),
            adv_yi=(liq_by.get(t) or {}).get("adv_yi"),
        ) is None
        for t in tickers
    }


def build(*, root: Path | None = None, cfg: dict[str, Any] | None = None,
          now: datetime | None = None, limit: int | None = None,
          series: dict[str, Any] | None = None,
          gate_fn=None, frozen: dict[str, dict[str, Any]] | None = None,
          tradable: dict[str, bool] | None = None,
          universe_rows: list[tuple] | None = None) -> dict[str, Any]:
    """Assemble the CN armed pack. ``series`` injects a test universe."""
    from lib import cn_calendar  # noqa: PLC0415

    t0 = time.time()
    c = CP.pack_cfg(cfg)
    root = root or Path(_CODE_ROOT)
    skipped: dict[str, int] = {}

    if series is None:
        from scripts.build_china_library import universe  # noqa: PLC0415
        rows = universe_rows if universe_rows is not None else \
            CP.filter_universe(universe())
        if tradable is not None:
            # STRICT COVERAGE (P1): the map must answer for every universe row.
            # BASE failed OPEN (``.get(t, True)``) and shipped an actual ST name;
            # a missing key — or an empty map over a non-empty universe — is the
            # same refusal: incomplete metadata preparation must publish nothing
            # (main turns the raise into ``::error`` + rc 1).
            missing = [r[0] for r in rows if r[0] not in tradable]
            if missing:
                raise RuntimeError(
                    f"tradability map missing {len(missing)}/{len(rows)} universe "
                    f"tickers — refusing to build (first five: {', '.join(missing[:5])})")
            rows = [r for r in rows if tradable[r[0]]]
        series = {}
        for row in rows:
            tkr, close = row[0], row[1]
            s = AP.clean_closes(close)
            if s is None or len(s) < 2:
                skipped["no_series"] = skipped.get("no_series", 0) + 1
                continue
            series[tkr] = s
    else:
        series = {t: AP.clean_closes(s) for t, s in series.items()}
        series = {t: s for t, s in series.items() if s is not None and len(s) >= 2}

    if limit:
        series = dict(list(series.items())[: int(limit)])

    tip = AP.as_of_date(series.values())
    g = gate_fn or CP.make_cn_gate()
    board: dict[str, Any] = {}
    if frozen is None:
        frozen = load_frozen(root, receipt_out=board)
    else:
        board["reason"] = "injected"

    recs: dict[str, dict[str, Any]] = {}
    probes: dict[str, dict[str, Any]] = {}
    gate_calls = 0
    max_lag = int(c.get("max_lag_sessions") or 2)
    import pandas as pd  # noqa: PLC0415
    for tkr, s in series.items():
        lag = AP.session_lag(str(pd.Timestamp(s.index[-1]).date()), tip,
                             calendar=cn_calendar)
        if lag > max_lag:
            recs[tkr] = AP.stale_record(tkr, s, lag)
            skipped["stale_series"] = skipped.get("stale_series", 0) + 1
            continue
        rec = CP.centre_record(tkr, s, cfg=c, gate_fn=g)
        recs[tkr] = rec
        gate_calls += int(rec.get("gate_calls") or 0)
        if rec.get("skip"):
            skipped[rec["skip"]] = skipped.get(rec["skip"], 0) + 1

    wanted = [t for t, r in recs.items() if r.get("wants_probe")]
    wanted.sort(key=lambda t: AP.probe_priority(recs[t]))
    cap = int(c.get("max_probe") or 180)
    to_probe = wanted[:cap]
    if len(wanted) > cap:
        skipped["probe_cap"] = len(wanted) - cap
        for t in wanted[cap:]:
            recs[t]["skip"] = "probe_cap"
            recs[t]["wants_probe"] = False

    for tkr in to_probe:
        r = CP.probe_name(tkr, series[tkr], recs[tkr], cfg=c, gate_fn=g)
        probes[tkr] = r
        gate_calls += int(r.get("gate_calls") or 0)
        if r.get("irregular"):
            skipped["irregular"] = skipped.get("irregular", 0) + 1

    names = {t: AP.name_entry(r, probes.get(t)) for t, r in recs.items()}
    checks = {t: AP.edge_checks(e, probes.get(t)) for t, e in names.items()}
    checks = {t: v for t, v in checks.items() if v}
    edges = 0
    mismatched: set[str] = set()
    verified: set[str] = set()
    bad: list[str] = []
    for tkr, chk in checks.items():
        lines, n = CP.verify_edges(tkr, series[tkr], chk, gate_fn=g)
        edges += n
        gate_calls += n
        verified.add(tkr)
        if lines:
            bad.extend(lines)
            mismatched.add(tkr)

    def _withhold(tickers: set[str], reason: str) -> None:
        tickers = {t for t in tickers if t in recs}
        if not tickers:
            return
        for t in tickers:
            probes.pop(t, None)
            recs[t]["skip"] = reason
            recs[t]["wants_probe"] = False
        skipped[reason] = skipped.get(reason, 0) + len(tickers)

    _withhold(set(checks) - verified, "unverified")
    _withhold(mismatched, "edge_mismatch")
    names = {t: AP.name_entry(r, probes.get(t)) for t, r in recs.items()}
    mem_bad = AP.membership_mismatches(names)
    if mem_bad:
        bad.extend(mem_bad.values())
        _withhold(set(mem_bad), "membership_mismatch")
        names = {t: AP.name_entry(r, probes.get(t)) for t, r in recs.items()}

    payload = CP.assemble(
        names, as_of=tip or "", cfg=c, universe_n=len(series),
        wanted_n=len(wanted), gate_calls=gate_calls,
        build_seconds=time.time() - t0, skipped=skipped,
        edges_checked=edges, frozen=frozen, now=now,
    )
    payload["meta"]["edge_mismatches"] = bad
    # Identity stamps (archive spec §1-§2): the session this pack is armed FOR,
    # off the same CN calendar the lag gate uses, and the board it froze from.
    # A tipless (empty-universe) pack gets no intended_session, and the publish
    # helper then refuses to replace the current key rather than archive under
    # a fabricated session.
    if tip:
        payload["meta"]["intended_session"] = AP.next_session_stamp(
            tip, cn_calendar).date().isoformat()
    if "reason" in board:
        payload["meta"]["source_board"] = {"path": None, "reason": board["reason"]}
    else:
        payload["meta"]["source_board"] = {
            "path": board.get("path"), "as_of": board.get("as_of"),
            "sha256": board.get("sha256"),
        }
    print(f"cn-live pack: universe={len(series)} probed={payload['meta']['probed_n']} "
          f"armed={payload['meta']['armed_n']} tip={tip} "
          f"{payload['meta']['build_seconds']}s", flush=True)
    return payload


def pack_digest(payload: dict[str, Any]) -> str:
    """sha256 over the canonical payload with ``meta.pack_sha256`` absent.

    Canonical = ``sort_keys`` + compact separators + ``allow_nan=False``: the
    same bytes on every host, so the archive key addresses content, not the
    build that produced it. A verifier recomputes exactly this after removing
    that one field — nothing else may be dropped or reordered.
    """
    scrub = dict(payload)
    meta = dict(payload.get("meta") or {})
    meta.pop("pack_sha256", None)
    scrub["meta"] = meta
    return hashlib.sha256(json.dumps(
        scrub, allow_nan=False, sort_keys=True,
        separators=(",", ":")).encode()).hexdigest()


def publish_with_archive(payload: dict[str, Any], *, put=r2io.put_json) -> bool:
    """Archive the pack content-addressed, THEN replace the current key (F7).

    The current key is a single slot each roll overwrites; the archived N-1
    object is the authority for first-event identity and frozen score/rank. So
    the archive put goes FIRST and a False from it refuses the current-key
    replace — a roll that cannot preserve N-1 must not erase it. Both puts
    receive the identical payload object, stamped with its own digest. Identical
    content re-published lands on the same archive key (no timestamp enters the
    digest), so retries and re-runs cannot fork two authorities per session.
    """
    meta = payload.setdefault("meta", {})
    session = str(meta.get("intended_session") or "")
    if not session:
        print("::error title=cn-live-pack::pack archive refused - no "
              "intended_session - current key NOT replaced", flush=True)
        return False
    digest = pack_digest(payload)
    meta["pack_sha256"] = digest
    if not put(r2io.pack_archive_key(session, digest), payload):
        print("::error title=cn-live-pack::pack archive write failed - "
              "current key NOT replaced", flush=True)
        return False
    if not put(r2io.CN_PACK_KEY, payload):
        print("::warning title=cn-live-pack::R2 publish failed — pack stays local",
              flush=True)
        return False
    return True


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--publish", action="store_true")
    p.add_argument("--out", default=None)
    p.add_argument("--now", default=None)
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--root", default=_CODE_ROOT)
    args = p.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s",
                        stream=sys.stderr)
    try:
        cfg = None
        try:
            from lib import config  # noqa: PLC0415
            cfg = config.load()
        except Exception as exc:  # noqa: BLE001
            print(f"::warning title=cn-live-pack::config.yml unreadable ({exc})",
                  flush=True)
        # Tradability gate (P1): the SAME predicate + metadata owner the nightly
        # board applies, mapped strictly over the pack's stock universe. Missing
        # metadata values keep the nightly pass-through semantics; what is refused
        # is an incomplete MAP, never a silent fail-open.
        from scripts.build_china_library import (  # noqa: PLC0415
            load_tradability_metadata, stock_tradability_ok, universe)
        rows = CP.filter_universe(universe())
        tickers = [r[0] for r in rows]
        meta = load_tradability_metadata()
        liq_by = china_liquidity.liquidity_map(tickers)
        tradable = tradability_map(tickers, meta=meta, liq_by=liq_by)
        assert set(tradable) == set(tickers), "tradability map lost tickers"
        assert all(isinstance(v, bool) for v in tradable.values()), \
            "tradability map values must be bool"
        payload = build(root=Path(args.root), cfg=cfg, now=_now(args.now),
                        limit=args.limit, tradable=tradable, universe_rows=rows)
        # Receipt: why each dropped name was dropped, from the map's reasons.
        drop = {"st": 0, "mcap": 0, "adv": 0}
        for t, ok in tradable.items():
            if ok:
                continue
            reason = stock_tradability_ok(
                t,
                st_flag=meta["st_flag_by"].get(t, False),
                name_zh=meta["name_zh_by"].get(t),
                mktcap=meta["mktcap_by"].get(t),
                adv_yi=(liq_by.get(t) or {}).get("adv_yi"),
            )
            if reason:
                drop[reason] += 1
        payload["meta"]["tradability"] = {
            "universe": len(tradable),
            "pass": sum(1 for v in tradable.values() if v),
            "drop": drop,
        }
    except Exception as exc:  # noqa: BLE001
        print(f"::error title=cn-live-pack::{exc}", flush=True)
        return 1
    if args.out:
        Path(args.out).write_text(json.dumps(payload, allow_nan=False, indent=2),
                                  encoding="utf-8")
    if args.publish:
        # Archive-first (F7): rc 1 when the archive (or publish) failed — the
        # Asia-close step runs this lane continue-on-error, so the honest exit
        # code costs nothing and the failure stays visible in the annotation.
        if not publish_with_archive(payload):
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
